from odoo import models, fields, api, exceptions, _
from odoo.tools import float_compare

import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.depends('state', 'product_uom_qty', 'reserved_availability')
	def _qty_available(self):
		for move in self:
			# For consumables, state is available so availability = qty to do
			if move.state in ['assigned','done']:
				move.quantity_available = move.product_uom_qty
			elif move.product_id.uom_id and move.product_uom:
				move.quantity_available = move.product_id.uom_id._compute_quantity(move.reserved_availability, move.product_uom, move.product_id.name)

class StockMoveLots(models.Model):
	_inherit = 'stock.move.lots'

	@api.one
	@api.constrains('lot_id', 'quantity_done')
	def _check_lot_id(self):
		if self.move_id.product_id.tracking == 'serial':
			lots = set([])
			for move_lot in self.move_id.active_move_lot_ids.filtered(lambda r: not r.lot_produced_id and r.lot_id):
				if move_lot.lot_id in lots:
					raise exceptions.UserError(_('You cannot use the same serial number in two different lines.'))
				if float_compare(move_lot.quantity_done, 1.0, precision_rounding=move_lot.product_id.uom_id.rounding) == 1:
					raise exceptions.UserError(_('You can only produce 1.0 %s for products with unique serial number. Product: %s') % (move_lot.product_id.uom_id.name,move_lot.product_id.name))
				lots.add(move_lot.lot_id)