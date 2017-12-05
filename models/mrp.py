from odoo import models, fields, api

class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	state = fields.Selection([
		('confirmed', 'Confirmed'),
		('approved', 'Approved'),
		('planned', 'Planned'),
		('progress', 'In Progress'),
		('done', 'Done'),
		('cancel', 'Cancelled')
	])

	@api.multi
	def action_approve(self):
		self.write({'state': 'approved'})