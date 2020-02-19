from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class MRPWorkorder(models.Model):
	_inherit = 'mrp.workorder'

	@api.model
	def create(self, values):
		if values.get('production_id'):
			# Create production lot from MO
			production_id = self.env['mrp.production'].browse(values.get('production_id'))
			lot_id = self.env['stock.production.lot'].search([('name', '=', production_id.name)])
			_logger.info(lot_id)
			values['final_lot_id'] = lot_id.id
			values['qty_producing'] = production_id.product_qty
		result = super(MRPWorkorder, self).create(values)
		return result

	def check_stock(self):
		for move in self.production_id.move_raw_ids:
			if move.state != 'done' and move.quantity_available < move.product_uom_qty:
				raise UserError(_('Cannot start work order. Some components are not available.'))

	@api.multi
	def button_start(self):
		self.check_stock()
		result = super(MRPWorkorder, self).button_start()
		return result

	@api.multi
	def button_stop(self):
		return self.write({'state': 'pending'})

	@api.multi
	def button_compute_moves(self):
		for moves in self.active_move_lot_ids:
			moves.unlink()

		# Create new active moves
		for workorder in self:
			workorder._generate_lot_ids()