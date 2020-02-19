from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPickingWave(models.Model):
	_inherit = "stock.picking.wave"

	@api.multi
	def print_picking(self):
		pickings = []
		for pick in self.picking_ids:
			if pick.pack_operation_product_ids:
				if any(pack.qty_done_uom_ordered != 0 for pack in pick.pack_operation_product_ids):
					pickings.append(pick.id)
			else:
				if any(move.quantity_done != 0 for move in pick.move_lines):
					pickings.append(pick.id)

		if not pickings:
			raise UserError(_('Nothing to print.'))
		return self.env["report"].with_context(active_ids=pickings, active_model='stock.picking').get_action([], 'stock.report_deliveryslip')