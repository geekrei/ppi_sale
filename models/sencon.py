from odoo import models, fields

class SenconPaymentVia(models.Model):
	_name = 'sencon.payment.via'

	name = fields.Char()
	default = fields.Boolean(string='Set as Default')