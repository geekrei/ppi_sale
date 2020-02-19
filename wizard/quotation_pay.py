from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class QuotationPay(models.TransientModel):
	_name = 'quotation.pay'
	_deescription = 'Wizard to record payment on quotation'

	account_id = fields.Many2one('account.account', string='Account')
	amount = fields.Float(string='Total')
	currency_id = fields.Many2one('res.currency', string='Currency')
	date = fields.Date(default=fields.Date.today())
	journal_id = fields.Many2one('account.journal', string='Journal')
	name = fields.Char(string='Memo')
	partner_id = fields.Many2one('res.partner', string='Customer')
	# period_id = fields.Many2one('account.period', string='Period')
	reference = fields.Char(string='Ref #')
	payment_method_id = fields.Many2one('account.payment.method', string='Payment Method')

	@api.model
	def default_get(self, fields):
		rec = super(QuotationPay, self).default_get(fields)
		active_id = self._context.get('active_id')

		# Check for selected invoices ids
		if not active_id:
			raise UserError(_("Programmation error: wizard action executed without active_ids in context."))

		payment_method = self.env['account.payment.method'].search(['&',('payment_type', '=', 'inbound'), ('code', '=', 'manual')], limit=1)

		sales = self.env['sale.order'].browse(active_id)

		rec.update({
			'amount': abs(sales.amount_total),
			'currency_id': sales.currency_id.id,
			'partner_id': sales.partner_id.id,
			'reference': sales.name,
			'name': 'Deposit on ' + str(sales.name),
			'payment_method_id': payment_method.id,
		})
		return rec


	def pay(self):
		payment = self.env['account.payment']
		payment.create({
			'name': self.name,
			'date': self.date,
			'amount': self.amount,
			'reference': self.reference,
			'account_id': self.account_id.id,
			'currency_id': self.currency_id.id,
			'journal_id': self.journal_id.id,
			'partner_id': self.partner_id.id,
			'payment_method_id': self.payment_method_id.id,
			'payment_type': 'inbound',
		})
		# return True