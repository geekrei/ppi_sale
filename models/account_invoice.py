from odoo import api, fields, models, _

from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

# mapping invoice type to journal type
TYPE2JOURNAL = {
	'out_invoice': 'sale',
	'in_invoice': 'purchase',
	'out_refund': 'sale',
	'in_refund': 'purchase',
}

class AccountInvoice(models.Model):
	_inherit = 'account.invoice'

	@api.model
	def _default_ship_by(self):
		return self.company_id.partner_id

	# OVERRIDE FUNCTION TO SET DEFAULT VALUES IN JOURNAL (PURCHASE)
	@api.model
	def _default_journal(self):
		if self._context.get('default_journal_id', False):
			return self.env['account.journal'].browse(self._context.get('default_journal_id'))
		inv_type = self._context.get('type', 'out_invoice')
		inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
		company_id = self._context.get('company_id', self.env.user.company_id.id)
		inv_type_default = self._context.get('type')
		company_data = self.env['res.company'].search([('id','=',company_id)])
		
		if inv_type_default == 'in_invoice' and company_data.default_purchase_journal:
			return self.env['account.journal'].browse(company_data.default_purchase_journal.id)
		# if inv_type_default == 'in_refund' and company_data.default_purchase_refund_journal:
		# 	return self.env['account.journal'].browse(company_data.default_purchase_refund_journal.id)
		
		domain = [
			('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
			('company_id', '=', company_id),
		]
		return self.env['account.journal'].search(domain, limit=1)

	intrastat_country_id = fields.Many2one('res.country', string='Intrastat Country')
	payment_via_id = fields.Many2one('sencon.payment.via', string='Payment Via', default=lambda self: self.env['sencon.payment.via'].search([('default', '=', True)], limit=1))
	partner_shipping_by_id = fields.Many2one('res.partner', string='Ship By')
	journal_id = fields.Many2one(default=_default_journal)

	# NEW FIELDS
	show_country_origin = fields.Boolean(default=False, string='Show Country of Origin', help='If check, country of origin of products will be displayed in report.')
	related_delivery_ref = fields.Char(string='Related Picking', help='Specify delivery order ref for correct fetching of lot/serial number used. This is helpful if there are multiple deliveries and invoices involved.')

	def get_customer_ref(self):
		sale_order = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)
		return sale_order.client_order_ref

	@api.onchange('company_id')
	def _onchange_company_id(self):
		self.partner_shipping_by_id = self.company_id.partner_id
		if "INNOSEN LTD" in self.company_id.name:
			company_id = self.env['res.company'].search([('name','like','INNOSEN INC')], limit=1)
			self.partner_shipping_by_id = company_id.partner_id

	# @api.multi
	# def _compute_picking(self):
	# 	for record in self:
	# 		if record.type == 'out_invoice' or record.type == 'out_refund':
	# 			sale_order = self.env['sale.order'].sudo().search([('name','=',record.origin)], limit=1)
	# 			if sale_order:
	# 				pickings = sale_order.picking_ids
	# 				for pick in pickings:
	# 					if any(pick)

	def alert_bill_due(self, days):
		_logger.info("DUEEEEE")
		target_date = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
		_logger.info(target_date)
		invoice_due = self.search([('date_due','=',target_date),('type','=','in_invoice'),('state','=','open')],order='number')
		_logger.info(invoice_due)
		if invoice_due:
			# mail_message = self.env['mail.message']    
			# sub_type_id=self.env['ir.model.data'].get_object_reference('innosen_custom','vendo_bill__due_notification')[1]
			# user = self.env.user

			mail_to_send = self.env['mail.mail']
			notification_template = self.env.ref('innosen_custom.vendor_bill_due_notification')
			user = self.env.user
			
			for invoice in invoice_due:
				_logger.info("HUIHIU")
				_logger.info(invoice)
				# subject=_("Vendor Bill Due Notification for Bill  %s") % invoice.number
				# body=_("Vendor Bill %s is due in %s days for supplier %s \n" % (invoice.number,days,invoice.partner_id.name))
				# # send message (one message per client) 
				# send_to = [invoice.create_uid.partner_id.id]

				# mail_values = {
				# 'subject': subject,
				# 'body': body,
				# 'message_type': 'email',
				# 'partner_ids':  [(6,0,send_to)], 
				# 		'subtype_id':sub_type_id,
				# 	}

				# mail_message.create(mail_values)
				notification_template.send_mail(invoice.id, force_send=True)

		return True


class AccountInvoiceLine(models.Model):
	_inherit = 'account.invoice.line'

	notes = fields.Text(string='Notes')

	def get_serial_numbers(self, line):
		serialnos={}

		pickings = line.sudo().mapped('sale_line_ids').mapped('order_id').mapped('picking_ids').filtered(lambda picking: picking.group_id.name == self.origin)
		# move_lines = pickings.sudo().mapped('move_lines')
		# MOVE LINES FILTERED RETURNS
		move_lines = pickings.sudo().mapped('move_lines').filtered(lambda move: not move.returned_move_ids)

		matched_qty = False
		matched_qty_serial = ''
		for move in move_lines:
			if move.product_uom_qty == line.quantity and move.product_id == line.product_id:
				matched_qty = True
				if matched_qty == True:
					for quant in move.quant_ids:
						# Check if lot is in matched serial already
						if quant.lot_id:
							if not quant.lot_id.name in matched_qty_serial:
								if matched_qty_serial:
									matched_qty_serial += ', '
								matched_qty_serial += quant.lot_id.name

		# if matched_qty == True and matched_qty_serial:
		return matched_qty_serial


		# # return serialnos
		# for n in serial_numbers:
		# 	if serialnos.has_key(n.product_id.id):
		# 		serialnos[n.product_id.id].append(n.name)
		# 	else:
		# 		serialnos[n.product_id.id]=[n.name]
		# # we have the serial numbers let us now allocate per line
		# serialnosperline={}
		# serial = ''
		# # for line in o.invoice_line_ids:
		# 	#product=line.product_id.rented_product_id if line.product_id.rented_product_id else line.product_id
		# product = line.product_id
		# if serialnos.has_key(product.id):
		# 	lengte=len(serialnos[product.id])
		# 	order=', '.join(serialnos[product.id][:(int(line.quantity) if int(line.quantity)<lengte else lengte)])
		# 	serialnos[product.id]=serialnos[product.id][(int(line.quantity) if int(line.quantity)<=lengte else lengte):]
		# 	serialnosperline[line.id]=order
		# 	serial = order
		# else:
		# 	serialnosperline[line.id] = '-'
		# 	serial = '-'
			
		# return serial
