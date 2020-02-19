from odoo import models, fields, api
from collections import defaultdict

import logging
_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
	_inherit = 'stock.quant'

	def _create_account_move_line(self, move, credit_account_id, debit_account_id, journal_id):
		move_status = self.env['ir.values'].get_default('stock.config.settings', 'group_account_move_status')

		# group quants by cost
		quant_cost_qty = defaultdict(lambda: 0.0)
		for quant in self:
			quant_cost_qty[quant.cost] += quant.qty

		AccountMove = self.env['account.move']
		for cost, qty in quant_cost_qty.iteritems():
			move_lines = move._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
			if move_lines:
				date = self._context.get('force_period_date', fields.Date.context_today(self))
				new_account_move = AccountMove.create({
					'journal_id': journal_id,
					'line_ids': move_lines,
					'date': date,
					'ref': move.picking_id.name})

				if move_status == 'post':
					new_account_move.post()

				if not new_account_move.ref:
					new_account_move.write({'ref': move.origin})