# -*- coding: utf-8 -*-
from odoo import api, fields, tools, models, _
from openerp.exceptions import ValidationError, UserError
from odoo.tools import config
import hashlib
import os

import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	# INHERIT
	hs_code = fields.Char(string='HS Code SLU', compute='_compute_default_hs_code', inverse='_set_default_hs_code', store=True, track_visibility='onchange')
	track_service = fields.Selection(selection_add=[
		('repair', 'Create a repair order')
	], track_visibility='onchange')
	landed_cost_ok = fields.Boolean(default=True, track_visibility='onchange')
	split_method = fields.Selection(default='by_current_cost_price', track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE
	name = fields.Char(track_visibility='onchange')
	description = fields.Text(track_visibility='onchange')
	description_purchase = fields.Text(track_visibility='onchange')
	description_sale = fields.Text(track_visibility='onchange')
	type = fields.Selection([
		('consu', _('Consumable')),
		('service', _('Service')),
		('product', 'Stockable Product'),
	], track_visibility='onchange')
	rental = fields.Boolean(track_visibility='onchange')
	categ_id = fields.Many2one('product.category', track_visibility='onchange')
	currency_id = fields.Many2one('res.currency', track_visibility='onchange')
	price = fields.Float(track_visibility='onchange')
	list_price = fields.Float(track_visibility='onchange')
	lst_price = fields.Float(track_visibility='onchange')
	sale_ok = fields.Boolean(track_visibility='onchange')
	purchase_ok = fields.Boolean(track_visibility='onchange')
	uom_id = fields.Many2one('product.uom', track_visibility='onchange')
	uom_po_id = fields.Many2one('product.uom', track_visibility='onchange')
	company_id = fields.Many2one('res.company', track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // STOCK FIELDS
	tracking = fields.Selection(track_visibility='onchange')
	description_picking = fields.Text(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // PURCHASE REQUISITION FIELDS
	purchase_requisition = fields.Selection(track_visibility='onchange')
	purchase_line_warn = fields.Selection(track_visibility='onchange')
	purchase_line_warn_msg = fields.Text(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // SALES FIELDS
	invoice_policy = fields.Selection(track_visibility='onchange')
	sale_line_warn = fields.Selection(track_visibility='onchange')
	sale_line_warn_msg = fields.Text(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // STOCK LANDED COST FIELDS
	landed_cost_ok = fields.Boolean(track_visibility='onchange')
	split_method = fields.Selection(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // STOCK ACCOUNT FIELDS
	property_valuation = fields.Selection(track_visibility='onchange')
	property_stock_account_input = fields.Many2one(track_visibility='onchange')
	property_stock_account_output = fields.Many2one(track_visibility='onchange')
	property_cost_method = fields.Selection(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // ACCOUNT ASSET FIELDS
	asset_category_id = fields.Many2one(track_visibility='onchange')
	deferred_revenue_category_id = fields.Many2one(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // ACCOUNT FIELDS
	property_account_income_id = fields.Many2one(track_visibility='onchange')
	property_account_expense_id = fields.Many2one(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // PURCHASE FIELDS
	property_account_creditor_price_difference = fields.Many2one(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // HR EXPENSE FIELDS
	can_be_expensed = fields.Boolean(track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE // INNOSEN FIELDS
	tariff_code = fields.Char(track_visibility='onchange')
	calibration_period = fields.Integer(track_visibility='onchange')
	underlicense = fields.Boolean(track_visibility='onchange')

	# company_id = fields.Many2one(company_dependent=True)

	# NEW FIELDS
	country_origin = fields.Many2one('res.country', string='Country of Origin', compute='_compute_default_country_origin', inverse='_set_default_country_origin', store=True)
	bomline_ids = fields.Many2many('mrp.bom.line', string='BOM Lines', compute='_compute_bomline_ids')
	compliance_rohs = fields.Boolean(string='ROHS Compliance', compute='_compute_default_compliance', inverse='_set_default_compliance', store=True)
	compliance_ce = fields.Boolean(string='CE Compliance', compute='_compute_default_compliance', inverse='_set_default_compliance', store=True)


	@api.multi
	def _compute_currency_id(self):
		try:
			currency = False
			base_currency = self.env['res.currency'].sudo().search([('base','=',True)], limit=1)
			currency = base_currency
			if not base_currency:
				main_company = self.sudo().env.ref('base.main_company')
				currency = main_company.currency_id
		except ValueError:
			currency = False
			main_company = self.env['res.company'].sudo().search([], limit=1, order="id")
			currency = main_company.currency_id

		for template in self:
			template.currency_id = template.company_id.sudo().currency_id.id or currency.id

	# HS CODE IN PRODUCT TEMPLATE
	@api.depends('product_variant_ids', 'product_variant_ids.hs_code')
	def _compute_default_hs_code(self):
		unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
		for template in unique_variants:
			template.hs_code = template.product_variant_ids.hs_code
		for template in (self - unique_variants):
			template.hs_code = ''

	@api.one
	def _set_default_hs_code(self):
		if len(self.product_variant_ids) == 1:
			self.product_variant_ids.hs_code = self.hs_code

	# COUNTRY OF ORIGIN IN PRODUCT TEMPLATE
	@api.depends('product_variant_ids', 'product_variant_ids.country_origin')
	def _compute_default_country_origin(self):
		unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
		for template in unique_variants:
			template.country_origin = template.product_variant_ids.country_origin
		for template in (self - unique_variants):
			template.country_origin = False

	@api.one
	def _set_default_country_origin(self):
		if len(self.product_variant_ids) == 1:
			self.product_variant_ids.compliance_rohs = self.compliance_rohs
			self.product_variant_ids.compliance_ce = self.compliance_ce

	@api.depends('product_variant_ids', 'product_variant_ids.compliance_rohs', 'product_variant_ids.compliance_ce')
	def _compute_default_compliance(self):
		unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
		for template in unique_variants:
			template.compliance_rohs = template.product_variant_ids.compliance_rohs
			template.compliance_ce = template.product_variant_ids.compliance_ce
		for template in (self - unique_variants):
			template.compliance_rohs = False
			template.compliance_ce = False

	@api.one
	def _set_default_compliance(self):
		if len(self.product_variant_ids) == 1:
			self.product_variant_ids.country_origin = self.country_origin

	@api.model
	def create(self, values):
		result = super(ProductTemplate, self).create(values)

		# SET DEFAULT PROPERTY FIELDS/ACCOUNTS FOR ALL COMPANIES
		self.update_product_company_property_defaults(result.id)

		return result

	def update_product_company_property_defaults(self, product_id):
		_logger.info('HCEW')
		
		product = self.env['product.template'].browse(product_id)

		product.sudo().write({
			'landed_cost_ok': True,
			'split_method': 'by_current_cost_price',
		})
		
		company_ids = self.env['res.company'].search([])
		for company in company_ids:
			# PRICE DIFFERENCE ACCOUNT
			price_difference = False
			price_difference_account = self.env['account.account'].search([('name','ilike','Stock Price Variance'),('company_id','=',company.id)], limit=1)
			if price_difference_account:
				price_difference = price_difference_account

			# EXPENSE ACCOUNT 
			expense = False
			expense_account = self.env['account.account'].search([('name','ilike','Stock Interim Account (CLEARING)'),('company_id','=',company.id)], limit=1)
			if expense_account:
				expense = expense_account

			# STOCK INPUT ACCOUNT
			stock_input = False
			stock_input_account = self.env['account.account'].search([('name','ilike','Stock Interim Account (CLEARING)'),('company_id','=',company.id)], limit=1)
			if stock_input_account:
				stock_input = stock_input_account

			# STOCK OUTPUT ACCOUNT
			stock_output = False

			is_wip = False

			if 'Raw Materials' in product.categ_id.name:
				is_wip = True

			if 'Manufacturing Supplies' in product.categ_id.name:
				is_wip = True

			if is_wip == False:
				stock_output_account = self.env['account.account'].search([('name','ilike','Cost of Goods Sold'),('company_id','=',company.id)], limit=1)
				if stock_output_account:
					stock_output = stock_output_account

			if is_wip == True:
				stock_output_account = self.env['account.account'].search([('name','ilike','Work In Process - Production'),('company_id','=',company.id)], limit=1)
				if stock_output_account:
					stock_output = stock_output_account

			product.with_context(force_company=company.id).sudo().write({
				'property_cost_method': 'real',
				'property_valuation': 'real_time',
				'property_account_creditor_price_difference': price_difference,
				'property_account_expense_id': expense,
				'property_stock_account_input': stock_input,
				'property_stock_account_output': stock_output,

			})

	def button_update_product_company_property_defaults(self):
		self.update_product_company_property_defaults(self.id)

	@api.one
	def _compute_bomline_ids(self):
		product_ids = self.mapped('product_variant_ids').ids
		bomline_ids = self.env['mrp.bom.line'].search([('product_id','in',product_ids)]).ids
		self.bomline_ids = bomline_ids


class ProductProduct(models.Model):
	_inherit = 'product.product'

	hs_code = fields.Char(string='HS Code SLU', track_visibility='onchange')

	# EXTEND TO ADD TRACKING ON CHANGE
	standard_price = fields.Float(track_visibility='onchange')
	active = fields.Boolean(track_visibility='onchange')
	barcode = fields.Char(track_visibility='onchange')
	default_code = fields.Char(track_visibility='onchange')
	volume = fields.Float(track_visibility='onchange')
	weight = fields.Float(track_visibility='onchange')
	# tariff_code = fields.Char(track_visibility='onchange')

	# NEW FIELDS
	country_origin = fields.Many2one('res.country', string='Country of Origin', track_visibility='onchange')
	compliance_rohs = fields.Boolean(string='ROHS Compliance', track_visibility='onchange')
	compliance_ce = fields.Boolean(string='CE Compliance', track_visibility='onchange')

	@api.multi
	def action_view_bomlines(self):
		product_ids = self.mapped('product_variant_ids').ids
		action = self.env.ref('innosen.action_product_allits_boms').read()[0]
		action['domain'] = [('product_id', 'in', product_ids)]
		action['context'] = {}
		return action

	def update_product_company_property_defaults(self, product_id):
		_logger.info('HCEW')
		
		product = self.env['product.product'].browse(product_id)

		product.sudo().write({
			'landed_cost_ok': True,
			'split_method': 'by_current_cost_price',
		})
		
		company_ids = self.env['res.company'].search([])
		for company in company_ids:
			# PRICE DIFFERENCE ACCOUNT
			price_difference = False
			price_difference_account = self.env['account.account'].search([('name','ilike','Stock Price Variance'),('company_id','=',company.id)], limit=1)
			if price_difference_account:
				price_difference = price_difference_account

			# EXPENSE ACCOUNT 
			expense = False
			expense_account = self.env['account.account'].search([('name','ilike','Stock Interim Account (CLEARING)'),('company_id','=',company.id)], limit=1)
			if expense_account:
				expense = expense_account

			# STOCK INPUT ACCOUNT
			stock_input = False
			stock_input_account = self.env['account.account'].search([('name','ilike','Stock Interim Account (CLEARING)'),('company_id','=',company.id)], limit=1)
			if stock_input_account:
				stock_input = stock_input_account

			# STOCK OUTPUT ACCOUNT
			stock_output = False
			
			is_wip = False

			if 'Raw Materials' in product.categ_id.name:
				is_wip = True

			if 'Manufacturing Supplies' in product.categ_id.name:
				is_wip = True

			if is_wip == False:
				stock_output_account = self.env['account.account'].search([('name','ilike','Cost of Goods Sold'),('company_id','=',company.id)], limit=1)
				if stock_output_account:
					stock_output = stock_output_account

			if is_wip == True:
				stock_output_account = self.env['account.account'].search([('name','ilike','Work In Process - Production'),('company_id','=',company.id)], limit=1)
				if stock_output_account:
					stock_output = stock_output_account

			product.with_context(force_company=company.id).sudo().write({
				'property_cost_method': 'real',
				'property_valuation': 'real_time',
				'property_account_creditor_price_difference': price_difference,
				'property_account_expense_id': expense,
				'property_stock_account_input': stock_input,
				'property_stock_account_output': stock_output,

			})

	def button_update_product_company_property_defaults(self):
		self.update_product_company_property_defaults(self.id)

	def post_route_changes(self, current_routes, new_routes):		
		current_routes_name = ""
		get_current_routes = self.env['stock.location.route'].search([('id','in',current_routes)])
		for route in get_current_routes:
			current_routes_name += route.name + ", "


		new_routes_name = ""
		get_new_routes = self.env['stock.location.route'].search([('id','in',new_routes)])
		for route in get_new_routes:
			new_routes_name += route.name + ", "

		message = _('<ul class="o_mail_thread_message_tracking"><li>Routes: %s &#8594; %s</li></ul>') % (current_routes_name, new_routes_name)
		self.message_post(body=message)

	@api.multi
	def write(self, values):
		for record in self:
			current_routes = record.route_ids
			new_routes = values.get('route_ids')

			if new_routes:
				record.post_route_changes(current_routes.ids, new_routes[0][2])

		result = super(ProductProduct, self).write(values)

		return result


# FIX FOR SERVER ERROR NO ATTRIBUTE _storage, _compute_checksum, _index
class ProductSpec(models.Model):
	_inherit = 'product.spec'

	mimetype = fields.Char('Mime Type', readonly=True)

	@api.model
	def _storage(self):
		return self.env['ir.config_parameter'].sudo().get_param('ir_attachment.location', 'file')

	@api.model
	def _filestore(self):
		return config.filestore(self._cr.dbname)

	def _compute_checksum(self, bin_data):
		""" compute the checksum for the given datas
			:param bin_data : datas in its binary form
		"""
		# an empty file has a checksum too (for caching)
		return hashlib.sha1(bin_data or '').hexdigest()

	def _mark_for_gc(self, fname):
		""" Add ``fname`` in a checklist for the filestore garbage collection. """
		# we use a spooldir: add an empty file in the subdirectory 'checklist'
		full_path = os.path.join(self._full_path('checklist'), fname)
		if not os.path.exists(full_path):
			dirname = os.path.dirname(full_path)
			if not os.path.isdir(dirname):
				with tools.ignore(OSError):
					os.makedirs(dirname)
			open(full_path, 'ab').close()

	@api.model
	def _index(self, bin_data, datas_fname, file_type):
		""" compute the index content of the given filename, or binary data.
			This is a python implementation of the unix command 'strings'.
			:param bin_data : datas in binary form
			:return index_content : string containing all the printable character of the binary data
		"""
		index_content = False
		if file_type:
			index_content = file_type.split('/')[0]
			if index_content == 'text': # compute index_content only for text type
				words = re.findall("[^\x00-\x1F\x7F-\xFF]{4,}", bin_data)
				index_content = ustr("\n".join(words))
		return index_content

	def _inverse_datas(self):
		location = self._storage()
		for attach in self:
			# compute the fields that depend on datas
			value = attach.datas
			bin_data = value and value.decode('base64') or ''
			vals = {
				'file_size': len(bin_data),
				'checksum': self._compute_checksum(bin_data),
				'index_content': self._index(bin_data, attach.datas_fname, attach.mimetype),
				'store_fname': False,
				'db_datas': value,
			}
			if value and location != 'db':
				# save it to the filestore
				vals['store_fname'] = self._file_write(value, vals['checksum'])
				vals['db_datas'] = False

			# take current location in filestore to possibly garbage-collect it
			fname = attach.store_fname
			# write as superuser, as user probably does not have write access
			super(ProductSpec, attach.sudo()).write(vals)
			if fname:
				self._file_delete(fname)

# FOR CONVERISON OF UOM ERROR
class ProductUoM(models.Model):
	_inherit = 'product.uom'

	@api.multi
	def _compute_quantity(self, qty, to_unit, product_id=False, round=True, rounding_method='UP'):
		if not self:
			return qty
		self.ensure_one()
		if self.category_id.id != to_unit.category_id.id:
			if self._context.get('raise-exception', True):
				if not product_id:
					raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (self.name, to_unit.name))
				else:
					raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!. Product: %s') % (self.name, to_unit.name, product_id.name))
			else:
				return qty
		amount = qty / self.factor
		if to_unit:
			amount = amount * to_unit.factor
			if round:
				amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
		return amount