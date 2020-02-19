from odoo import models, fields, api, _ 

import logging
_logger = logging.getLogger(__name__)

class PackOperation(models.Model):
	_inherit = "stock.pack.operation"

	note = fields.Text(string='Notes')


	# // DIABLED UNTIL FILTER CONDTION OF SERIAL IS STABILIZED
	@api.one
	def _get_instock_serial(self):
		product_id = self.product_id

		instock_ids = []

		lot_ids = self.env['stock.production.lot'].sudo().search([('product_id', '=', product_id.id)])
		if lot_ids:
			for lot in lot_ids:
				# SET INSTOCK TO FALSE ALL QUANTS OF PRODUCT
				lot.sudo().write({'instock': False})

				# quant_ids = False
				# DELIVERY ORDER
				if self.picking_id.picking_type_id.code == "outgoing":
					_logger.info("OUTGOING")
					quant_ids = lot.quant_ids.sudo().filtered(lambda quant: quant.product_id == product_id and quant.location_id.usage == 'internal' and quant.location_id == self.location_id)
					if quant_ids:
						for quant in quant_ids:
							if quant.qty > 0:
								instock_ids.append(lot.id)
								lot.sudo().write({'instock': True})
							else:
								lot.sudo().write({'instock': False})

				# INTERNAL TRANSFER
				if self.picking_id.picking_type_id.code == "internal":
					_logger.info("INTERNAL")
					quant_ids = lot.quant_ids.sudo().filtered(lambda quant: quant.product_id == product_id and quant.location_id.usage in ['internal','inventory'] and quant.location_id == self.location_id)
					if quant_ids:
						for quant in quant_ids:
							if quant.qty > 0:
								instock_ids.append(lot.id)
								lot.sudo().write({'instock': True})
							else:
								lot.sudo().write({'instock': False})

				# DROPSHIP AND RECEIPT
				if self.picking_id.picking_type_id.code == "incoming":
					_logger.info("INCOMING")

					if 'dropship' in self.picking_id.picking_type_id.name.lower():
						_logger.info("DROPSHIP")
						quant_ids = lot.quant_ids.sudo().filtered(lambda quant: quant.product_id == product_id)

						has_customer_loc = False

						if quant_ids:
							for quant in quant_ids:
								if quant.qty > 0 and quant.company_id != self.picking_id.company_id and quant.location_id.usage == 'customer':
									instock_ids.append(lot.id)
									has_customer_loc = True

						if has_customer_loc:
							lot.sudo().write({'instock': True})
						else:
							lot.sudo().write({'instock': False})
					else:
						_logger.info("RECEIPT")
						# quant_ids = lot.quant_ids.sudo().filtered(lambda quant: quant.product_id == product_id and quant.location_id == self.location_id)
						quant_ids = lot.quant_ids.sudo().filtered(lambda quant: quant.product_id == product_id)

						has_vendor_loc = False

						# IF SUPPLIER SOURCE, ALSO CHECK CUSTOMER LOCATION
						if quant_ids and self.location_id.usage == 'supplier':
							for quant in quant_ids:
								if quant.qty > 0 and quant.location_id.usage in ['supplier','customer']:
									instock_ids.append(lot.id)
									has_vendor_loc = True
						else:
							for quant in quant_ids:
								if quant.qty > 0 and quant.location_id == self.location_id:
									instock_ids.append(lot.id)
									has_vendor_loc = True

						if has_vendor_loc:
							lot.sudo().write({'instock': True})
						else:
							lot.sudo().write({'instock': False})

		# return instock_ids

	@api.multi
	def action_split_lots(self):
		get_lots = self._get_instock_serial()
		# _logger.info("HELLOWWW")
		# _logger.info(get_lots)
		
		action_ctx = dict(self.env.context)
		# _logger.info(self.env.context)

		# If it's a returned stock move, we do not want to create a lot
		returned_move = self.linked_move_operation_ids.mapped('move_id').mapped('origin_returned_move_id')
		picking_type = self.picking_id.picking_type_id
		action_ctx.update({
			'serial': self.product_id.tracking == 'serial',
			'product_id': self.product_id.id,
			'only_create': picking_type.use_create_lots and not picking_type.use_existing_lots and not returned_move,
			'create_lots': picking_type.use_create_lots,
			'state_done': self.picking_id.state == 'done',
			'show_reserved': any([lot for lot in self.pack_lot_ids if lot.qty_todo > 0.0]),
			# 'lot_ids': get_lots,
		})
			
		view_id = self.env.ref('stock.view_pack_operation_lot_form').id
		return {
			'name': _('Lot/Serial Number Details'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.pack.operation',
			'views': [(view_id, 'form')],
			'view_id': view_id,
			'target': 'new',
			'res_id': self.ids[0],
			'context': action_ctx}
	split_lot = action_split_lots
	# // DIABLED UNTIL FILTER CONDTION OF SERIAL IS STABILIZED