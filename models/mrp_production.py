from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class MRPProduction(models.Model):
	_inherit = 'mrp.production'

	@api.multi
	def button_plan(self):
		# Create LOT for MO
		lot_id = self.env['stock.production.lot'].search([('name', '=', self.name)])
		if not lot_id:
			new_lot = self.env['stock.production.lot'].create({
				'name': self.name,
				'product_id': self.product_id.id,
				'product_qty': self.product_qty,
			})
		result = super(MRPProduction, self).button_plan()
		return result

	# INHERIT TI CHECK PRODUCT AVAILABILITY BEFORE POSTING
	@api.multi
	def post_inventory(self):
		for order in self:
			for move in order.move_raw_ids:
				if move.state != 'done':
					if move.quantity_available < move.product_uom_qty:
						raise UserError(_('Cannot post to inventory. Some components are not available.'))

		result = super(MRPProduction, self).post_inventory()
		return result

	@api.multi
	def reset_order(self):
		for production in self:
			_logger.info('LALAND')
			# CHECK IF ANY WORKORDER IS NOT YET DONE
			# if any(workorder.state == 'progress' for workorder in self.mapped('workorder_ids')):
			for raw in production.move_raw_ids:
				if raw.state in ['assigned','done']:
					_logger.info("")
					for quant in raw.quant_ids:
						# Return to stock location
						self._cr.execute("""SELECT move_id FROM stock_quant_move_rel WHERE quant_id = %s""", (quant.id,))
						res = self._cr.fetchall()
						
						# quant.sudo().copy(default={'location_id': production.location_src_id.id, 'reservation_id': False, 'history_ids': [(4, x[0]) for x in res]})
						move_id = 0
						for record in res:
							move_record = self.env['stock.move'].browse(record)
							for move in move_record:
								if quant.qty < move.product_uom_qty:
									move_id = move.id

						quant.sudo().copy(default={'location_id': production.location_src_id.id, 'reservation_id': False, 'history_ids': [(4, move_id)]})

						# DELETE RELATIONS AND OLD QUANT
						# self._cr.execute("DELETE FROM stock_quant_move_rel WHERE quant_id = %s", (quant.id,))
						# self._cr.execute("DELETE FROM stock_quant WHERE id = %s", (quant.id,))
						self._cr.execute("DELETE FROM stock_quant WHERE id = %s", (quant.id,))
					
					raw.write({'state':'draft', 'quantity_done': 0, 'partially_available': False})

				elif raw.state in ['waiting','confirmed','cancel']:
					raw.write({'state':'draft'})

				# elif raw.state == 'assigned':
				# 	raw.do_unreserve()
				# 	raw.write({'state':'draft'})

				raw.unlink()
				
			# MOVE OF FINISH PRODUCT
			for move in production.move_finished_ids:
				if move.state == 'done':
					for quant in move.quant_ids:
						self._cr.execute("DELETE FROM stock_quant WHERE id = %s", (quant.id,))
					move.write({'state':'draft'})

				elif move.state in ['waiting','confirmed','assigned']:
					move.write({'state':'draft'})
				
				move.unlink()

			if not production.move_raw_ids and not production.move_finished_ids:
				production._generate_moves()

			if production.state == 'done':
				production.write({'state':'progress'})

			# REGENERATE WORK ORDERS
			if production.workorder_ids:
				for workorder in production.workorder_ids:
					workorder.unlink()

			quantity = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
			boms, lines = production.bom_id.explode(production.product_id, quantity, picking_type=production.bom_id.picking_type_id)
			production._generate_workorders(boms)

		# NEW
		# for production in self:
		# 	# consume_move = self._generate_consume_moves()[0]
		# 	# produce_moves = self._generate_produce_moves()

		# 	finished_moves = production.move_finished_ids.filtered(lambda move: move.product_id == production.product_id)
		# 	domain = [('qty', '>', 0), ('history_ids', 'in', finished_moves.ids)]pla

	@api.multi
	def update_waiting(self):
		for production in self:
			# CHECK IF ANY WORKORDER IS NOT YET DONE
			# if any(workorder.state == 'progress' for workorder in self.mapped('workorder_ids')):
			for move in production.move_raw_ids:
				if move.state == 'waiting':
					move.write({'state':'confirmed'})

				if move.quantity_done == move.product_uom_qty:
					move.write({'state':'done'})

				if move.state == 'confirmed':
					main_domain = {}
					main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]
					Quant = self.env['stock.quant']
					qty_already_assigned = move.reserved_availability
					qty = move.product_qty - qty_already_assigned
					quants = Quant.quants_get_preferred_domain(qty, move, domain=main_domain[move.id], preferred_domain_list=[])
					Quant.quants_reserve(quants, move)

	# PRINT PRODUCTION BARCODES IN EXCEL
	def print_production_barcodes(self):
		return {
			'type' : 'ir.actions.act_url',
			'url': '/web/export_xls/mrp_production_barcodes?production_id=%s'%(self.id),
			'target': 'new',
		}	