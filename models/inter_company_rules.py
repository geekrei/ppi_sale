from odoo import models, fields, api, _
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

class IntercompanyPurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	@api.one
	def inter_company_create_sale_order(self, company):
		_logger.info('SUITEO1')

		self = self.with_context(force_company=company.id)
		SaleOrder = self.env['sale.order']

		# find user for creating and validation SO/PO from partner company
		intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
		if not intercompany_uid:
			raise Warning(_('Provide at least one user for inter company relation for % ') % company.name)
		# check intercompany user access rights
		if not SaleOrder.sudo(intercompany_uid).check_access_rights('create', raise_exception=False):
			raise Warning(_("Inter company user of company %s doesn't have enough access rights") % company.name)

		# check pricelist currency should be same with SO/PO document
		company_partner = self.company_id.partner_id.sudo(intercompany_uid)

		# company_partner = self.partner_id.sudo(intercompany_uid)
		# if self.currency_id.id != company_partner.property_product_pricelist.currency_id.id:
		# 	raise Warning(_('You cannot create SO from PO because sale price list currency is different than purchase price list currency.'))

		# create the SO and generate its lines from the PO lines
		SaleOrderLine = self.env['sale.order.line']
		# read it as sudo, because inter-compagny user can not have the access right on PO
		sale_order_data = self.sudo()._prepare_sale_order_data(self.name, company_partner, company, self.dest_address_id and self.dest_address_id.id or False)
		sale_order = SaleOrder.sudo(intercompany_uid).create(sale_order_data[0])
		# lines are browse as sudo to access all data required to be copied on SO line (mainly for company dependent field like taxes)
		for line in self.order_line.sudo():
			so_line_vals = self._prepare_sale_order_line_data(line, company, sale_order.id)
			SaleOrderLine.sudo(intercompany_uid).create(so_line_vals)

		# write vendor reference field on PO
		if not self.partner_ref:
			self.partner_ref = sale_order.name

		#Validation of sales order
		if company.auto_validation:
			sale_order.sudo(intercompany_uid).action_confirm()

	@api.one
	def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
		team_id = self.env['crm.team'].sudo().search([('company_id', '=', company.id)], limit=1)
		partner_addr = partner.sudo().address_get(['invoice', 'delivery', 'contact'])
		warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False
		if not warehouse:
			raise Warning(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies' % (company.name)))
		return {
			'name': self.env['ir.sequence'].sudo().next_by_code('sale.order') or '/',
			'company_id': company.id,
			'warehouse_id': warehouse.id,
			'client_order_ref': name,
			'partner_id': partner.id,
			'pricelist_id': partner.property_product_pricelist.id,
			'partner_invoice_id': partner_addr['invoice'],
			'date_order': self.date_order,
			'fiscal_position_id': partner.property_account_position_id.id,
			'team_id': team_id.id or False,
			'user_id': False,
			'auto_generated': True,
			'auto_purchase_order_id': self.id,
			'partner_shipping_id': direct_delivery_address or partner_addr['delivery']
		}

class IntercompanySaleOrder(models.Model):
	_inherit = 'sale.order'

	@api.multi
	def action_confirm(self):
		_logger.info('BERNA99')

		""" Generate inter company purchase order based on conditions """
		res = super(IntercompanySaleOrder, self).action_confirm()
		for order in self:
			if not order.company_id: # if company_id not found, return to normal behavior
				continue
			# if company allow to create a Purchase Order from Sales Order, then do it !
			company = self.env['res.company']._find_company_from_partner(order.partner_id.id)
			if company and company.po_from_so and (not order.auto_generated):
				order.inter_company_create_purchase_order(company)
				# _logger.info(order.confirmation_date)
				# UPDATE PO DATE AND SET IT TO DATE OF CONFIRMATION
				purchase_order = self.env['purchase.order'].sudo().search([('origin', '=', order.name)], limit=1)
				_logger.info(purchase_order)
				if purchase_order:
					purchase_order.write({'date_order': order.confirmation_date})
		return res
