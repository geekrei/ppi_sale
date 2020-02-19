# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.depends('product_id', 'product_uom_qty', 'product_uom')
	def _cal_move_weight(self):
		_logger.info('HELLOQ')
		for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
			new_weight = 0
			if move.product_id.uom_id != move.product_id.uom_po_id:
				factor = 0
				if move.product_uom.uom_type == 'bigger':
					factor = move.product_uom.factor
					_logger.info('BIGGER')
					_logger.info(factor)

				if move.product_uom.uom_type == 'reference':
					factor = move.product_id.uom_id.factor / move.product_id.uom_po_id.factor_inv
					_logger.info('REFERENCE')
					_logger.info(factor)
					_logger.info(move.product_id.uom_id.factor)
					_logger.info(move.product_id.uom_po_id.factor)

				# new_weight = (move.product_qty * move.product_uom.factor * move.product_id.weight)
				new_weight = (move.product_qty * factor * move.product_id.weight)
			else:
				new_weight = (move.product_qty * move.product_id.weight)
			
			_logger.info('BLAH!')
			_logger.info(new_weight)
			move.weight = new_weight
