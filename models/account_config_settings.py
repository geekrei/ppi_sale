from odoo import models, fields, api

class AccountConfigSettings(models.TransientModel):
	_inherit = 'account.config.settings'

	@api.one
	@api.depends('company_id')
	def _get_purchase_journal_id(self):
		self.default_purchase_journal = self.company_id.default_purchase_journal

	@api.one
	def _set_purchase_journal_id(self):
		if self.default_purchase_journal != self.company_id.default_purchase_journal:
			self.company_id.default_purchase_journal = self.default_purchase_journal

	# @api.one
	# @api.depends('company_id')
	# def _get_purchase_refund_journal_id(self):
	# 	self.default_purchase_refund_journal = self.company_id.default_purchase_refund_journal

	# @api.one
	# def _set_purchase_refund_journal_id(self):
	# 	if self.default_purchase_refund_journal != self.company_id.default_purchase_refund_journal:
	# 		self.company_id.default_purchase_refund_journal = self.default_purchase_refund_journal

	default_purchase_journal = fields.Many2one('account.journal', string='Default Purchase Journal', domain="[('company_id', '=', company_id),('type', '=', 'purchase')]", compute='_get_purchase_journal_id', inverse='_set_purchase_journal_id')
	# default_purchase_refund_journal = fields.Many2one('account.journal', string='Default Purchase Refund Journal', domain="[('company_id', '=', company_id),('type', '=', 'purchase')]", compute='_get_purchase_refund_journal_id', inverse='_set_purchase_refund_journal_id')

