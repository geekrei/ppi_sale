from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	repair_id = fields.Many2one('mrp.repair', 'Repair Order')
	partner_bank_id = fields.Many2one('res.partner.bank', string='Bank Account')

	user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange')

	# OVERRIDE TO NOT INCLUDE CONFIRMATION DATE IN DUPLICATE/COPY OF RECORD
	confirmation_date = fields.Datetime(string='Confirmation Date', readonly=True, index=True, help="Date on which the sale order is confirmed.", oldname="date_confirm", copy=False)

	# NEW FIELD / CUSTOM
	po_ref = fields.Char(string='P.O. Reference', compute='get_po', help='This is the reference number of PO generated from this SO')
	# show_country_origin = fields.Boolean(default=False, string='Show Country of Origin', help='If check, country of origin of products will be displayed in report.')
	delivery_status = fields.Selection([
		('no_delivery', 'No Delivery'),
		('waiting', 'Waiting'),
		('to_deliver', 'To Deliver'),
		('partial', 'Partially Delivered'),
		('delivered', 'Delivered'),
		('cancel', 'Cancelled'),
		], string='Delivery Status', compute='_get_delivered', copy=False, index=True, readonly=True, store=True)
	is_delivered_manual_override = fields.Boolean(string='Override Deliverd Status', help="Override computation of delivery and set delivered status to DELIVERED")

	# Get Email To / Document Followers
	@api.multi
	def get_po(self):
		for record in self:
			po_ref = ''
			purchase_order = self.env['purchase.order'].search([('origin', '=', record.name)], limit=1)
			if purchase_order:
				po_ref = purchase_order.name

			record.po_ref = po_ref

	# SET SALESPERSON
	@api.onchange('company_id')
	def set_salesperson(self):
		if self.company_id.default_salesperson:
			self.user_id = self.company_id.default_salesperson
		else:
			self.user_id = self.env.user
	
	@api.multi
	def action_confirm(self):
		create_repair = False
		if any(line.product_id.track_service == 'repair' for line in self.mapped('order_line')):
			if not any(line.product_id.type == 'product' for line in self.mapped('order_line')):
				raise UserError(_('One of the line item product track service is set to create repair order. However, no product in the line item can be repaired.'))
			create_repair = True

		for order in self:

			to_repair = {}
			for line in order.order_line:
				if line.product_id.type == 'product':
					to_repair = line 

			if create_repair == True and to_repair:
				location = False
				
				# warehouse = self.env.ref('stock.warehouse0', raise_if_not_found=False)
				# if warehouse:
				# 	location = warehouse.lot_stock_id.id

				warehouse = order.warehouse_id
				if warehouse:
					location = warehouse.lot_stock_id.id

				repair_order = self.env['mrp.repair'].create({
					'product_id': to_repair.product_id.id,
					'product_qty': to_repair.product_uom_qty,
					'product_uom': to_repair.product_uom.id,
					'partner_id': order.partner_id.id,
					'location_id': location,
					'location_dest_id': location,
					'sale_id': order.id,
					# 'reference': order.client_order_ref,
				})

				if repair_order:
					order.write({'repair_id': repair_order.id})

		result = super(SaleOrder, self).action_confirm()
		return result

	@api.multi
	@api.onchange('partner_id')
	def onchange_partner_id(self):
		"""
		Update the following fields when the partner is changed:
		- Pricelist
		- Payment terms
		- Invoice address
		- Delivery address
		"""
		if not self.partner_id:
			self.update({
				'partner_invoice_id': False,
				'partner_shipping_id': False,
				'payment_term_id': False,
				'fiscal_position_id': False,
			})
			return

		addr = self.partner_id.address_get(['delivery', 'invoice'])
		values = {
			'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
			'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
			'partner_invoice_id': addr['invoice'],
			'partner_shipping_id': addr['delivery'],
			'user_id': self.partner_id.user_id.id or self.env.uid
		}
		if self.env['ir.config_parameter'].sudo().get_param('sale.use_sale_note') and self.env.user.company_id.sale_note:
			values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

		if self.partner_id.team_id:
			values['team_id'] = self.partner_id.team_id.id

		# [NEW] CHECK IF NO DEFAULT PAYMENT FOR PARTNER, SET DEFAULT PAYMENT TERM
		if not self.partner_id.property_payment_term_id:
			default_payment_term = self.env['account.payment.term'].search([('default','=',True)], limit=1)
			values['payment_term_id'] = default_payment_term.id

		self.update(values)

	# @api.multi
	# def action_view_repair(self):
	# 	action = self.env.ref('mrp_repair.action_repair_order_tree').read()[0]
	# 	if self.repair_id:
	# 		action['views'] = [(self.env.ref('mrp_repair.action_repair_order_tree').id, 'form')]
	# 		action['res_id'] = self.repair_id.id
	# 	else:
	# 		action = {'type': 'ir.actions.act_window_close'}
	# 	return action

	@api.depends('confirmation_date', 'order_line.customer_lead')
	def _compute_commitment_date(self):
		"""Compute the commitment date"""
		for order in self:
			if order.confirmation_date:
				dates_list = []
				order_datetime = fields.Datetime.from_string(order.confirmation_date)
				
				for line in order.order_line.filtered(lambda x: x.state != 'cancel'):
					dt = order_datetime + timedelta(days=line.customer_lead or 0.0)
					dates_list.append(dt)
				if dates_list:
					commit_date = min(dates_list) if order.picking_policy == 'direct' else max(dates_list)
					order.commitment_date = fields.Datetime.to_string(commit_date)

	# OVERRIDE CREATE TO SET PAYMENT TERM FOR SO GENERATED FROM PO
	@api.model
	def create(self, values):
		payment_term = values.get('payment_term_id')
		partner_id = values.get('partner_id')

		if not values.get('payment_term_id'):
			partner = self.env['res.partner'].browse(partner_id)
			payment_term = partner.property_payment_term_id and partner.property_payment_term_id.id or False
			if not payment_term:
				default_payment_term = self.env['account.payment.term'].search([('default','=',True)], limit=1)
				payment_term = default_payment_term.id

		values['payment_term_id'] = payment_term
		
		result = super(SaleOrder, self).create(values)

		return result

	# NEW FUNCTION : RECOMPUTE DELIVERY TO ADDRESS ISSUE WHERE DELIVERED QTY IS NOT UPDATED IF ORIGINAL MOVE IS CANCELLED
	@api.multi
	def action_compute_delivery(self):
		for record in self:
			# _logger.info('CHILLAZ')
			# # UPDATE MOVES OF PICKING TO SET PROCUREMENT
			# for picking in record.picking_ids.filtered(lambda r: r.state == 'cancel'):
			# 	_logger.info(picking)

			# # UPDATE MOVES OF PICKING TO SET PROCUREMENT
			_logger.info('KRKL')
			# UPDATE PICKING
			if not record.picking_ids:
				picking_ids = self.env['stock.picking'].search([('group_id', '=', record.procurement_group_id.id)]) if record.procurement_group_id else []
				_logger.info(picking_ids)
				record.picking_ids = picking_ids
				record.delivery_count = len(record.picking_ids)
			for picking in record.picking_ids.filtered(lambda r: r.state == 'done'):
				for move in picking.move_lines:
					if not move.procurement_id:
						for line in record.order_line:
							if move.product_id == line.product_id and move.product_uom == line.product_uom and move.state == 'done':
								# SEARCH FOR CANCELLED PROCUREMENT
								# procurement_id = False

								procurement_id = self.env['procurement.order'].search([('group_id', '=', record.procurement_group_id.id),('product_id', '=', line.product_id.id),('product_qty', '=', line.product_qty),('product_uom', '=', line.product_uom.id)], limit=1)

								
								# Try to create new procurement order if no existing procurement can be used.
								# if not procurement_id:
								# 	procurement_new_id = self.env['procurement.order'].create({
								# 		'name': move.name,
								# 		'product_id': move.product_id.id,
								# 		'product_qty': move.qty_done,
								# 		'date_planned': picking.min_date,
								# 		'priority': picking.priority,
								# 		'warehouse_id': record.warehouse_id.id,
								# 		'location_id': picking.location_dest_id.id,
								# 		'origin': record.name,
								# 		'group_id': record.procurement_group_id.id,
								# 		'rule_id': move.rule_id.id,
								# 		'partner_dest_id': record.partner_shipping_id.id,
								# 		'company_id': picking.company_id.id,
								# 	})
								# 	procurement_id = procurement_new_id
								# 	_logger.info('EXISTING PROCUREMENT')
								
								_logger.info(procurement_id)
								if procurement_id:
									if procurement_id == 'cancel':
										procurement_id.write({'state': 'done'})
									move.write({'procurement_id': procurement_id.id, 'group_id': procurement_id.group_id.id})
									# UPDATE PROCUREMENTS IN ORDER LINES
									line.write({'procurement_ids': [(4,procurement_id.id)]})
					else:
						for line in record.order_line:
							if not line.procurement_ids:
								if move.product_id == line.product_id and move.product_uom == line.product_uom and move.state == 'done':
									# UPDATE PROCUREMENTS IN ORDER LINES
									line.write({'procurement_ids': [(4,move.procurement_id.id)]})

			# UPDATE QTY
			for line in record.order_line:
				line.qty_delivered = line._get_delivered_qty()

	@api.multi
	def action_unlock(self):
		self.write({'state': 'sale'})

	@api.model
	def _get_rental_date_planned(self, line):
		return line.start_date

	@api.model
	def _prepare_order_line_procurement(
			self, order, line, group_id=False):
		res = super(SaleOrder, self)._prepare_order_line_procurement(
			order, line, group_id=group_id)
		if (
				line.product_id.rented_product_id and
				line.rental_type == 'new_rental'):
			res.update({
				'product_id': line.product_id.rented_product_id.id,
				'product_qty': line.rental_qty,
				'product_uos_qty': line.rental_qty,
				'product_uom': line.product_id.rented_product_id.uom_id.id,
				'product_uos': line.product_id.rented_product_id.uom_id.id,
				'location_id':
				order.warehouse_id.rental_out_location_id.id,
				'route_ids':
				[(6, 0, [line.order_id.warehouse_id.rental_route_id.id])],
				'date_planned': self._get_rental_date_planned(line),
				})
		elif line.sell_rental_id:
			res['route_ids'] = [(6, 0, [
				line.order_id.warehouse_id.sell_rented_product_route_id.id])]
		return res

	@api.depends('state','order_line.qty_delivered','order_line.delivery_status','is_delivered_manual_override')
	@api.one
	def _get_delivered(self):
		if self.is_delivered_manual_override:
			delivery_status = 'delivered'
		else:
			if not self.order_line or self.state in ['draft','sent']:
				delivery_status = 'no_delivery'
			elif any(move.state in ['draft','waiting','confirmed'] for move in self.mapped('order_line').filtered(lambda r: r.product_id.type != 'service').mapped('procurement_ids').mapped('move_ids')):
				delivery_status = 'waiting'

			elif any(move.state == 'assigned' for move in self.mapped('order_line').filtered(lambda r: r.product_id.type != 'service').mapped('procurement_ids').mapped('move_ids')):
				delivery_status = 'to_deliver'

			elif any(line.qty_delivered >= line.product_uom_qty for line in self.mapped('order_line').filtered(lambda r: r.product_id.type != 'service')) and not all(line.qty_delivered >= line.product_uom_qty for line in self.mapped('order_line').filtered(lambda r: r.product_id.type != 'service')):
				delivery_status = 'partial'

			elif all(move.state == 'cancel' for move in self.mapped('order_line').filtered(lambda r: r.product_id.type != 'service').mapped('procurement_ids').mapped('move_ids')):
				delivery_status = 'cancel'

			elif all(line.qty_delivered >= line.product_uom_qty for line in self.mapped('order_line').filtered(lambda r: r.product_id.type != 'service')):
				delivery_status = 'delivered'
			else:
				delivery_status = 'no_delivery'

		self.update({
			'delivery_status': delivery_status
		})

	@api.multi
	def _compute_delivered(self):
		for order in self:
			order._get_delivered()


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	delivery_status = fields.Selection([
		('no_delivery', 'No Delivery'),
		('waiting', 'Waiting'),
		('to_deliver', 'To Deliver'),
		('partial', 'Partially Delivered'),
		('delivered', 'Delivered'),
		('cancel', 'Cancelled'),
		], string='Delivery Status', compute='_get_delivered', copy=False, index=True, readonly=True, store=True)

	@api.depends('order_id.state','qty_delivered','procurement_ids.move_ids','procurement_ids.move_ids.state')
	@api.one
	def _get_delivered(self):
		# for order in self:
		# move_ids = self.procurement_ids.move_ids
		# delivery_status = 'no_delivery'		

		_logger.info("HELLO")
		# _logger.info(move_ids)
		_logger.info(self.name)
		if self.procurement_ids.move_ids:
			
			if any(move.state in ['draft','waiting','confirmed'] for move in self.mapped('procurement_ids').mapped('move_ids')):
				# delivery_status = 'waiting'
				self.delivery_status = 'waiting'

			elif any(move.state in ['partially_assigned','assigned'] for move in self.mapped('procurement_ids').mapped('move_ids')):
				# delivery_status = 'to_deliver'
				self.delivery_status = 'to_deliver'

			elif all(move.state == 'cancel' for move in self.mapped('procurement_ids').mapped('move_ids')):
				# delivery_status = 'cancel'
				self.delivery_status = 'cancel'

			elif all(line.qty_delivered >= line.product_uom_qty for line in self.filtered(lambda r: r.product_id.type != 'service')):
				# delivery_status = 'delivered'
				self.delivery_status = 'delivered'
		else:
			self.delivery_status = 'no_delivery'

	def get_serial_numbers(self, line):
		serialnos={}

		pickings = line.mapped('order_id').mapped('picking_ids')
		serial_numbers = set(pickings.mapped('move_lines').mapped('quant_ids').mapped('lot_id'))

		# return serialnos
		for n in serial_numbers:
			if serialnos.has_key(n.product_id.id):
				serialnos[n.product_id.id].append(n.name)
			else:
				serialnos[n.product_id.id]=[n.name]
		# we have the serial numbers let us now allocate per line
		serialnosperline={}
		serial = ''
		# for line in o.invoice_line_ids:
			#product=line.product_id.rented_product_id if line.product_id.rented_product_id else line.product_id
		product = line.product_id
		if serialnos.has_key(product.id):
			lengte=len(serialnos[product.id])
			order=', '.join(serialnos[product.id][:(int(line.quantity) if int(line.quantity)<lengte else lengte)])
			serialnos[product.id]=serialnos[product.id][(int(line.quantity) if int(line.quantity)<=lengte else lengte):]
			serialnosperline[line.id]=order
			serial = order
		else:
			serialnosperline[line.id] = ''
			serial = ''
			
		return serial

	@api.multi
	def _prepare_order_line_procurement(self, group_id=False):
		vals = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
		# date_planned = datetime.strptime(self.order_id.confirmation_date, DEFAULT_SERVER_DATETIME_FORMAT)\
		# 	+ timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
		date_planned = datetime.strptime(self.order_id.commitment_date, DEFAULT_SERVER_DATETIME_FORMAT)
		vals.update({
			'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
			'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
			'route_ids': self.route_id and [(4, self.route_id.id)] or [],
			'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id.id or False,
			'partner_dest_id': self.order_id.partner_shipping_id.id,
			'sale_line_id': self.id,
		})
		return vals

	@api.multi
	def _get_delivered_qty(self):
		"""Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements
		"""
		self.ensure_one()
		if self.product_id.rented_product_id:
			return 0.0
		return super(SaleOrderLine, self)._get_delivered_qty()