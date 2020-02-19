from odoo import models, fields, api, _ 

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
		""" Returns values common to both move lines (except for debit, credit and amount_currency which are reversed)
		"""
		return {
			'partner_id': self.payment_type in ('inbound', 'outbound') and self.partner_id.id or False,
			'invoice_id': invoice_id and invoice_id.id or False,
			'move_id': move_id,
			'debit': debit,
			'credit': credit,
			'amount_currency': amount_currency or False,
		}


class AccountPaymentTerm(models.Model):
	_inherit = 'account.payment.term'

	default = fields.Boolean()