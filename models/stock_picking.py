from odoo import models, fields, api, _ 

from odoo.addons import decimal_precision as dp
from odoo.addons.procurement.models import procurement
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from datetime import datetime
from dateutil import relativedelta
import time

import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
	_inherit = 'stock.picking'

	repair_id = fields.Many2one('mrp.repair', 'Repair Order')
	location_id = fields.Many2one('stock.location', "Source Location Zone",
		default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_src_id,
		readonly=True, required=True,
		states={'draft': [('readonly', False)], 'waiting': [('readonly', False)], 'confirmed': [('readonly', False)], 'partially_available': [('readonly', False)], 'assigned': [('readonly', False)]})
	location_dest_id = fields.Many2one('stock.location', "Destination Location Zone",
		default=lambda self: self.env['stock.picking.type'].browse(self._context.get('default_picking_type_id')).default_location_dest_id,
		readonly=True, required=True,
		states={'draft': [('readonly', False)], 'waiting': [('readonly', False)], 'confirmed': [('readonly', False)], 'partially_available': [('readonly', False)], 'assigned': [('readonly', False)]})

	# NEW FIELDS
	show_country_origin = fields.Boolean(default=False, string='Show Country of Origin', help='If check, country of origin of products will be displayed in report')

	@api.multi
	def update_move_location(self):
		location_id = self.location_id
		location_dest_id = self.location_dest_id
		if self.move_lines:
			for move in self.move_lines:
				move.write({'location_id': location_id.id, 'location_dest_id': location_dest_id.id})

		if self.pack_operation_ids:
			for pack in self.pack_operation_ids:
				pack.write({'location_id': location_id.id, 'location_dest_id': location_dest_id.id})

		if self.pack_operation_product_ids:
			for pack in self.pack_operation_product_ids:
				pack.write({'location_id': location_id.id, 'location_dest_id': location_dest_id.id})

		if self.pack_operation_pack_ids:
			for pack in self.pack_operation_pack_ids:
				pack.write({'location_id': location_id.id, 'location_dest_id': location_dest_id.id})

	@api.one
	@api.depends('pack_operation_ids')
	def _compute_bulk_weight(self):
		weight = 0.0
		for packop in self.pack_operation_ids:
			if packop.product_id and not packop.result_package_id:
				if packop.product_id.uom_id != packop.product_id.uom_po_id:
					factor = 0
					if packop.product_uom_id.uom_type == 'bigger':
						factor = packop.product_uom_id.factor

					if packop.product_uom_id.uom_type == 'reference':
						factor = packop.product_id.uom_id.factor / packop.product_id.uom_po_id.factor_inv

					new_weight = (packop.product_qty * factor * packop.product_id.weight)
					weight += new_weight
				else:
					weight += packop.product_uom_id._compute_quantity(packop.product_qty, packop.product_id.uom_id) * packop.product_id.weight
		self.weight_bulk = weight

	# DEV TOOL
	def button_compute_weight(self):
		for move in self.move_lines:
			move._cal_move_weight()
		self._cal_weight()
		self._compute_bulk_weight()
		self._compute_shipping_weight()

	# DEV TOOL TO FIX WAITING ANOTHER MOVE ISSUE:
	@api.multi
	def button_reserve_waiting_move(self):
		for picking in self:
			# CHECK IF ANY WORKORDER IS NOT YET DONE
			# if any(workorder.state == 'progress' for workorder in self.mapped('workorder_ids')):
			for move in picking.move_lines:
				if move.state == 'waiting':
					# Remove Procurement Link
					procurement = move.procurement_id
					procurement.write({'sale_line_id':False})
					procurement.write({'state':'cancel'})
					move.write({'state':'confirmed'})

				# TRY TO RESERVE QUANTS
				if move.state == 'confirmed':
					main_domain = {}
					main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]
					Quant = self.env['stock.quant']
					qty_already_assigned = move.reserved_availability
					qty = move.product_qty - qty_already_assigned
					quants = Quant.quants_get_preferred_domain(qty, move, domain=main_domain[move.id], preferred_domain_list=[])
					Quant.quants_reserve(quants, move)
