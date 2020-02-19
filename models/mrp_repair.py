from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

class MrpRepair(models.Model):
	_inherit = 'mrp.repair'

	deliver_bool = fields.Boolean(string='Deliver', default=True, help="Check this box if you want to manage the delivery once the product is repaired and create a picking with selected product.", states={'confirmed':[('readonly',True)]})
	picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True, copy=False)
	sale_id = fields.Many2one('sale.order', 'Sale Order', copy=False)
	reference = fields.Char()

	@api.onchange('lot_id')
	def onchange_lot_id(self):
		move_obj = self.env['stock.move']
		move_ids = self.lot_id.mapped('quant_ids').mapped('history_ids')

		lst_move = False

		for move in move_ids:
			if move.move_dest_id and move.move_dest_id.state == 'done':
				lst_move = move.move_dest_id
			else:
				if move.state == 'done':
					lst_move = move

		if lst_move != False:
			limit = datetime.strptime(lst_move.date_expected, '%Y-%m-%d %H:%M:%S') + relativedelta(months=int(self.product_id.warranty))
			self.partner_id = lst_move.partner_id.id
			self.guarantee_limit = limit.strftime('%Y-%m-%d')
			self.location_id = lst_move.location_dest_id.id
			self.location_dest_id = lst_move.location_dest_id.id
			# self.lot_id = move.lot_id.id

	def create_transfer_order(self):
		partner_id = self.partner_id
		product_id = self.product_id
		product_uom = self.product_uom
		product_qty = self.product_qty
		current_location_id = self.location_id
		location_dest_id = self.location_dest_id
		# name = self.name
		lot_id = self.lot_id
		sale_id = self.sale_id
		note = self.quotation_notes

		# if self.reference:
			# name = self.reference

		# scheduled_date = self.set_transfer_scheduled_date(datetime.now(), 5)

		
		_logger.info(product_qty)
		
		# warehouse_id = self.env['stock.warehouse'].search([('lot_stock_id', '=', current_location_id.id)])
		warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
		picking_type_id = self.env['stock.picking.type'].search(['&',('warehouse_id', '=', warehouse_id.id),('name','=','Delivery Orders')], limit=1)

		picking = self.env['stock.picking'].create({
			'picking_type_id' : picking_type_id.id, 
			'partner_id' : partner_id.id,
			'location_id' : current_location_id.id,
			'location_dest_id' : location_dest_id.id,
			# 'min_date': scheduled_date,
			'note': note,
			'repair_id': self.id,
			'origin' : sale_id.name,
			'move_lines' : [(0, 0, {
				'product_id' : product_id.id,
				'product_uom' : product_uom.id,
				'product_uom_qty' : product_qty,
				'name': '[' + str(product_id.default_code) + '] ' + product_id.name,
				'origin' : sale_id.name,
				'restrict_lot_id': lot_id.id
			})]
		})
		return picking

	@api.multi
	def action_repair_done(self):
		_logger.info("BUANG")
		if self.filtered(lambda repair: not repair.repaired):
			raise UserError(_("Repair must be repaired in order to make the product moves."))
		res = {}
		Move = self.env['stock.move']
		for repair in self:

			moves = self.env['stock.move']
			for operation in repair.operations:
				move = Move.create({
					'name': operation.name,
					'product_id': operation.product_id.id,
					'restrict_lot_id': operation.lot_id.id,
					'product_uom_qty': operation.product_uom_qty,
					'product_uom': operation.product_uom.id,
					'partner_id': repair.address_id.id,
					'location_id': operation.location_id.id,
					'location_dest_id': operation.location_dest_id.id,
					'origin': repair.name,
				})
				moves |= move
				operation.write({'move_id': move.id, 'state': 'done'})
			move = Move.create({
				'name': repair.name,
				'product_id': repair.product_id.id,
				'product_uom': repair.product_uom.id or repair.product_id.uom_id.id,
				'product_uom_qty': repair.product_qty,
				'partner_id': repair.address_id.id,
				'location_id': repair.location_id.id,
				'location_dest_id': repair.location_dest_id.id,
				'restrict_lot_id': repair.lot_id.id,
				'origin': repair.name,			})
			moves |= move
			moves.action_done()
			res[repair.id] = move.id

			if repair.deliver_bool:
				picking = repair.create_transfer_order()
				_logger.info(picking)
				picking.action_confirm()
				picking.action_assign()
				repair.write({'picking_id': picking.id})

		return res