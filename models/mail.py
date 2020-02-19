from odoo import _, api, fields, models, SUPERUSER_ID, tools

import logging
_logger = logging.getLogger(__name__)

# DEVELOPMENT TOOL ONLY / UNCOMMENT IF NECCESSARY
class MailMessage(models.Model):
	_inherit = 'mail.message'

	email_to = fields.Char(string='Email To', compute='get_email_to')

	# OVERRIDE
	body = fields.Html('Contents', default='', sanitize_style=False, strip_classes=False)

	# Get Email To / Document Followers
	@api.multi
	def get_email_to(self):
		for record in self:
			email_to = ''
			res_model = record.model

			if res_model:
				res_record = self.env[res_model].search_read([('id', '=', record.res_id)], ['message_follower_ids'])
				if res_record:
					for res_data in res_record:
						_logger.info(res_data['message_follower_ids'])
						followers = res_data['message_follower_ids']
						for follower_id in followers:
							follower_data = self.env['mail.followers'].browse(follower_id)
							if follower_data and follower_data.partner_id != record.author_id:
								if follower_data.partner_id.email:
									email_to += follower_data.partner_id.email + ", "
			record.email_to = email_to

class MailTemplate(models.Model):
	_inherit = 'mail.template'

	use_default = fields.Boolean(string='Use Default', help='Check to set default template to the applicable model.')


class MailComposer(models.TransientModel):
	_inherit = 'mail.compose.message'

	@api.model
	def default_get(self, fields):
		result = super(MailComposer, self).default_get(fields)

		# SET TEMPLATE TO FALSE TO REMOVE TEMPLATE ERROR FROM INNOSEN MODULE
		result['template_id'] = False
		# CHECK IF THERE IS A DEFAULT MAIL TEMPLATE FOR THE CURRENT ACTUVE MODEL
		template_id = self.env['mail.template'].search([('model_id', '=', result.get('model', self._context.get('active_model'))),('use_default','=',True)], limit=1)
		if template_id:
			result['template_id'] = template_id.id

		# v6.1 compatibility mode
		result['composition_mode'] = result.get('composition_mode', self._context.get('mail.compose.message.mode', 'comment'))
		result['model'] = result.get('model', self._context.get('active_model'))
		result['res_id'] = result.get('res_id', self._context.get('active_id'))
		result['parent_id'] = result.get('parent_id', self._context.get('message_id'))
		if 'no_auto_thread' not in result and (result['model'] not in self.env or not hasattr(self.env[result['model']], 'message_post')):
			result['no_auto_thread'] = True

		# default values according to composition mode - NOTE: reply is deprecated, fall back on comment
		if result['composition_mode'] == 'reply':
			result['composition_mode'] = 'comment'
		vals = {}
		if 'active_domain' in self._context:  # not context.get() because we want to keep global [] domains
			vals['use_active_domain'] = True
			vals['active_domain'] = '%s' % self._context.get('active_domain')
		if result['composition_mode'] == 'comment':
			vals.update(self.get_record_data(result))

		for field in vals:
			if field in fields:
				result[field] = vals[field]

		# TDE HACK: as mailboxes used default_model='res.users' and default_res_id=uid
		# (because of lack of an accessible pid), creating a message on its own
		# profile may crash (res_users does not allow writing on it)
		# Posting on its own profile works (res_users redirect to res_partner)
		# but when creating the mail.message to create the mail.compose.message
		# access rights issues may rise
		# We therefore directly change the model and res_id
		if result['model'] == 'res.users' and result['res_id'] == self._uid:
			result['model'] = 'res.partner'
			result['res_id'] = self.env.user.partner_id.id

		if fields is not None:
			[result.pop(field, None) for field in result.keys() if field not in fields]
		return result

	@api.multi
	def render_message(self, res_ids):
		"""Generate template-based values of wizard, for the document records given
		by res_ids. This method is meant to be inherited by email_template that
		will produce a more complete dictionary, using Jinja2 templates.

		Each template is generated for all res_ids, allowing to parse the template
		once, and render it multiple times. This is useful for mass mailing where
		template rendering represent a significant part of the process.

		Default recipients are also computed, based on mail_thread method
		message_get_default_recipients. This allows to ensure a mass mailing has
		always some recipients specified.

		:param browse wizard: current mail.compose.message browse record
		:param list res_ids: list of record ids

		:return dict results: for each res_id, the generated template values for
							  subject, body, email_from and reply_to
		"""
		self.ensure_one()
		multi_mode = True
		if isinstance(res_ids, (int, long)):
			multi_mode = False
			res_ids = [res_ids]

		subjects = self.render_template(self.subject, self.model, res_ids)
		bodies = self.render_template(self.body, self.model, res_ids, post_process=True)
		emails_from = self.render_template(self.email_from, self.model, res_ids)
		replies_to = self.render_template(self.reply_to, self.model, res_ids)
		default_recipients = {}
		if not self.partner_ids:
			default_recipients = self.env['mail.thread'].message_get_default_recipients(res_model=self.model, res_ids=res_ids)
		results = dict.fromkeys(res_ids, False)
		for res_id in res_ids:
			results[res_id] = {
				'subject': subjects[res_id],
				'body': bodies[res_id],
				'email_from': emails_from[res_id],
				'reply_to': replies_to[res_id],
			}
			results[res_id].update(default_recipients.get(res_id, dict()))

		# generate template-based values
		if self.template_id:
			template_values = self.generate_email_for_composer(
				self.template_id.id, res_ids,
				fields=['email_to', 'partner_to', 'email_cc', 'attachment_ids', 'mail_server_id'])
		else:
			template_values = {}

		for res_id in res_ids:
			if template_values.get(res_id):
				# recipients are managed by the template
				try:
					results[res_id].pop('partner_ids')
					results[res_id].pop('email_to')
					results[res_id].pop('email_cc')
				except Exception as e:
					_logger.error(e.message)
				# remove attachments from template values as they should not be rendered
				template_values[res_id].pop('attachment_ids', None)
			else:
				template_values[res_id] = dict()
			# update template values by composer values
			template_values[res_id].update(results[res_id])

		return multi_mode and template_values or template_values[res_ids[0]]

class MailThread(models.AbstractModel):
	_inherit = 'mail.thread'

	@api.multi
	def _message_auto_subscribe_notify(self, partner_ids):
		""" Notify newly subscribed followers of the last posted message.
			:param partner_ids : the list of partner to add as needaction partner of the last message
								 (This excludes the current partner)
		"""
		if not partner_ids:
			return

		if self.env.context.get('mail_auto_subscribe_no_notify'):
			return

		# send the email only to the current record and not all the ids matching active_domain !
		# by default, send_mail for mass_mail use the active_domain instead of active_ids.
		if 'active_domain' in self.env.context:
			ctx = dict(self.env.context)
			ctx.pop('active_domain')
			self = self.with_context(ctx)

		# for record in self:
		# 	record.message_post_with_view(
		# 		'mail.message_user_assigned',
		# 		composition_mode='mass_mail',
		# 		partner_ids=[(4, pid) for pid in partner_ids],
		# 		auto_delete=True,
		# 		auto_delete_message=True,
		# 		parent_id=False, # override accidental context defaults
		# 		subtype_id=self.env.ref('mail.mt_note').id)
