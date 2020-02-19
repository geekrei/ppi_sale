from odoo import models, fields, api, _ 

import logging
_logger = logging.getLogger(__name__)

class SaleRental(models.Model):
	_inherit = 'sale.rental'

	lot_ids = fields.Many2many('stock.production.lot', string='Serial Numbers', compute='_get_lots')

	@api.one
	@api.depends('out_move_id')
	def _get_lots(self):
		for lot in self.out_move_id.lot_ids:
			self.lot_ids = lot

	@api.one
	@api.depends('start_order_line_id', 'start_order_line_id.procurement_ids')
	def _compute_procurement_and_move(self):
		procurement = False
		in_move = False
		out_move = False
		sell_procurement = False
		sell_move = False
		state = False
		if (
				self.start_order_line_id and
				self.start_order_line_id.procurement_ids):

			procurement = self.start_order_line_id.procurement_ids[0]
			if procurement.move_ids:
				for move in procurement.move_ids:
					# if move.move_dest_id:
					# USE PICKING TYPE TO FILTER INCOMING AND OUTGOING MOVES
					if move.picking_type_id.code == "outgoing":
						out_move = move
						_logger.info("OUT")
					if move.picking_type_id.code == "incoming":
						in_move = move
						_logger.info("IN")
			if (
					self.sell_order_line_ids and
					self.sell_order_line_ids[0].procurement_ids):
				sell_procurement =\
					self.sell_order_line_ids[0].procurement_ids[0]
				if sell_procurement.move_ids:
					sell_move = sell_procurement.move_ids[0]
			state = 'ordered'
			if out_move and in_move:
				if out_move.state == 'done':
					state = 'out'
				if out_move.state == 'done' and in_move.state == 'done':
					state = 'in'
				if (
						out_move.state == 'done' and
						in_move.state == 'cancel' and
						sell_procurement):
					state = 'sell_progress'
					if sell_move and sell_move.state == 'done':
						state = 'sold'

		self.procurement_id = procurement
		self.in_move_id = in_move
		self.out_move_id = out_move
		self.state = state
		self.sell_procurement_id = sell_procurement
		self.sell_move_id = sell_move

	def button_compute_procurement_and_move(self):
		self._compute_procurement_and_move()