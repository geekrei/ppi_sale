from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class MrpEco(models.Model):
	_inherit = "mrp.eco"

	product_id = fields.Integer(compute='set_product_id')

	@api.depends('product_tmpl_id')
	def set_product_id(self):
		self.product_id = self.product_tmpl_id.id

	# OVERRIDE TO ADD NOTIFICATION
	@api.multi
	def approve(self):
		for eco in self:
			for approval in eco.approval_ids.filtered(lambda app: app.template_stage_id == self.stage_id and app.approval_template_id.approval_type in ('mandatory', 'optional')):
				if self.env.user in approval.approval_template_id.user_ids:
					approval.write({
						'status': 'approved',
						'user_id': self.env.uid
					})
					# POST MESSAGE
					message = _('ECO APPROVED')
					# partner_ids = eco.message_follower_ids
					partner_ids = [eco.user_id.partner_id]
					eco.message_post(body=message, partner_ids=partner_ids, subtype='mt_comment')

	# OVERRIDE TO ADD NOTIFICATION
	@api.multi
	def reject(self):
		for eco in self:
			for approval in eco.approval_ids.filtered(lambda app: app.template_stage_id == self.stage_id and app.approval_template_id.approval_type in ('mandatory', 'optional')):
				if self.env.user in approval.approval_template_id.user_ids:
					approval.write({
						'status': 'rejected',
						'user_id': self.env.uid
					})
					# POST MESSAGE
					message = _('ECO REJECTED')
					# partner_ids = eco.message_follower_ids
					partner_ids = [eco.user_id.partner_id]
					eco.message_post(body=message, partner_ids=partner_ids, subtype='mt_comment')

	# OVERRIDE TO ADD NOTIFICATION TO APPROVERS
	@api.multi
	def _create_approvals(self):
		result = super(MrpEco, self)._create_approvals()
		for eco in self:
			_logger.info("BUMALIK")
			for approval in eco.approval_ids:
				message = _('ECO FOR APPROVAL')
				partner_ids = approval.mapped('required_user_ids').mapped('partner_id').ids
				_logger.info(partner_ids)
				eco.message_post(body=message, partner_ids=partner_ids, subtype='mt_comment')
