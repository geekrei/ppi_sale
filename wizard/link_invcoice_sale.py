from odoo import models, fields, api

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class LinkInvoiceSale(models.TransientModel):
	_name = 'link.invoice.sale'

	def _default_sale(self):
		return self.env['sale.order'].browse(self._context.get('active_id'))

	sale_id = fields.Many2one('sale.order', string='Sale', default=_default_sale)
	invoice_ids = fields.Many2many('account.invoice', string='Invoice')

	# @api.multi
	def apply(self):
		# self.sale_id.invoice_ids |= self.invoice_ids
		# return {}

		if not self.invoice_ids:
			raise UserError("You must select at least one invoice to link to this sale order.")
		
		for invoice in self.invoice_ids:
			# Check if invoice originated from sale		
			if invoice.origin != self.sale_id.name:
				raise UserError("You must link invoice originating from sale. Invoice source document must be the sale name.")
			if invoice.partner_id != self.sale_id.partner_id:
				raise UserError("Invoice and sale vendor must be the same.")
				
			for invoice_lines in invoice.invoice_line_ids:
				for order_lines in self.sale_id.order_line:

					_logger.warning('KALBO')

					_logger.warning(invoice_lines.product_id)
					_logger.warning(order_lines.product_id)

					_logger.warning(invoice_lines.quantity)
					_logger.warning(order_lines.product_qty)

					_logger.warning(invoice_lines.price_subtotal)
					_logger.warning(order_lines.price_subtotal)
					# Check if line items match
					if invoice_lines.product_id == order_lines.product_id and invoice_lines.quantity == order_lines.product_qty and invoice_lines.price_subtotal == order_lines.price_subtotal:
						# raise UserError("Invoice and sale line items does not match.")
						# Set invoice line per order line of sale
						_logger.warning('MATCHED')
						order_lines.write({'invoice_lines': [(4,invoice_lines.id)]})