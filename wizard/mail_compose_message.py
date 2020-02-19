from odoo import models, fields, api

class MailComposer(models.TransienModel):
	_inherit = 'mail.compose.message'

	template_id = fields.Many2one('mail.template', 'Use template', index=True, domain="[('model', '=', model)]")