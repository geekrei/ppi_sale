from odoo import models, fields, api, _ 

class CrmLead(models.Model):
	_inherit = 'crm.lead'

	rfe_id = fields.Many2one('ppi.sale.estimate', 'Estimate')