from odoo import models, fields, api

class ResPartner(models.Model):
	_inherit = 'res.partner.bank'
	# OVERRIDE TO REMOVE DOMAIN
	partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', index=True, domain=[])

	# SET ACCOUNT HOLDER INFO
	@api.onchange('partner_id')
	def set_account_holder_info(self):
		self.city = self.partner_id.city
		self.country_id = self.partner_id.country_id
		self.owner_name = self.partner_id.name
		self.state_id = self.partner_id.state_id
		self.street = self.partner_id.street
		self.zip = self.partner_id.zip

	city = fields.Char()
	country_id = fields.Many2one('res.country', string="Country")
	iban = fields.Char(string="IBAN")
	name = fields.Char(string="Bank Account")
	owner_name = fields.Char(string="Account Owner Name")
	state_id = fields.Many2one('res.country.state', string="Fed. State")
	street = fields.Char()
	zip = fields.Char()