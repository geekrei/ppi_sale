from odoo import models, fields, api

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class LinkInvoicePurchase(models.TransientModel):
	_name = 'link.invoice.purchase'

	def _default_purchase(self):
		return self.env['purchase.order'].browse(self._context.get('active_id'))

	purchase_id = fields.Many2one('purchase.order', string='Purchase', default=_default_purchase)
	invoice_ids = fields.Many2many('account.invoice', string='Invoice')

	# @api.multi
	def apply(self):
		# self.purchase_id.invoice_ids |= self.invoice_ids
		# return {}

		if not self.invoice_ids:
			raise UserError("You must select at least one invoice to link to this purchase order.")
		
		for invoice in self.invoice_ids:
			# Check if invoice originated from purchase		
			if invoice.origin != self.purchase_id.name:
				raise UserError("You must link invoice originating from purchase. Invoice source document must be the purchase name.")
			if invoice.partner_id != self.purchase_id.partner_id:
				raise UserError("Invoice and purchase vendor must be the same.")
				
			for invoice_lines in invoice.invoice_line_ids:
				for order_lines in self.purchase_id.order_line:

					_logger.warning('KALBO')

					_logger.warning(invoice_lines.product_id)
					_logger.warning(order_lines.product_id)

					_logger.warning(invoice_lines.quantity)
					_logger.warning(order_lines.product_qty)

					_logger.warning(invoice_lines.price_subtotal)
					_logger.warning(order_lines.price_subtotal)
					# Check if line items match
					if invoice_lines.product_id == order_lines.product_id and invoice_lines.quantity == order_lines.product_qty and invoice_lines.price_subtotal == order_lines.price_subtotal:
						# raise UserError("Invoice and purchase line items does not match.")
						# Set invoice line per order line of purchase
						_logger.warning('MATCHED')
						order_lines.write({'invoice_lines': [(4,invoice_lines.id)]})