from odoo import models, fields, api 

class IrAttachment(models.Model):
	_inherit = 'ir.attachment'

	is_updated = fields.Boolean(default=False, string='Is Updated?')