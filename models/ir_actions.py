from odoo import models, fields, api, _ 

class ServerActions(models.Model):
	_inherit = 'ir.actions.server'

	force_send = fields.Boolean(string='Force Send', default=False)

	@api.model
	def run_action_email(self, action, eval_context=None):
		force_send = self.force_send
		# TDE CLEANME: when going to new api with server action, remove action
		if not action.template_id or not self._context.get('active_id'):
			return False
		action.template_id.send_mail(self._context.get('active_id'), force_send=force_send, raise_exception=False)
		return False