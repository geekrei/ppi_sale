from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
	_inherit = 'stock.quant'

	@api.multi
	def _get_latest_move(self):
		latest_move = self.history_ids
		if self.history_ids:
			latest_move = self.history_ids[0]
			for move in self.history_ids:
				if move.date > latest_move.date:
					latest_move = move

		return latest_move