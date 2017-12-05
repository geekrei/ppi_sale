from odoo import models, fields, api, _ 

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	rfe_id = fields.Many2one('ppi.sale.estimate', 'Estimate')

	state = fields.Selection([
		('draft', 'Quotation'),
		('sent', 'Quotation Sent'),
		('validate1', '1st Validation'),
		('validate2', '2nd Validation'),
		('validate3', 'Final Validation'),
		('sale', 'Sales Order'),
		('done', 'Locked'),
		('cancel', 'Cancelled'),
	])

	# quote_state = fields.Selection([
	# 	('validate1', 'Technical Supervisor'),
	# 	('validate2', 'Sales Manager'),
	# 	('validate3', 'Final Validation'),
	# ], string='Quotation State')

	validate_sale_head = fields.Boolean(default=False)
	validate_president = fields.Boolean(default=False)

	@api.multi
	def action_validate1(self):
		self.write({'state': 'validate1'})

	@api.multi
	def action_validate2(self):
		for record in self:
			if record.amount_total <= 2000000.00:
				record.write({'state': 'validate3'})

			if record.amount_total >= 2000000.00 and record.amount_total <= 5000000.00:
				record.write({'state': 'validate2'})
				record.write({'validate_sale_head': True})

			if record.amount_total >= 5000000.00:
				record.write({'state': 'validate2'})
				record.write({'validate_president': True})

	@api.multi
	def action_validate3(self):
		self.write({'state': 'validate3'})

	@api.multi
	def action_validate_sale_head(self):
		self.write({'state': 'validate3', 'validate_sale_head': False})

	@api.multi
	def action_validate_president(self):
		self.write({'state': 'validate3', 'validate_president': False})

	@api.multi
	def action_confirm(self):
		for order in self:
			for line in order.order_line:
				line._update_bom_qty()

		res = super(SaleOrder, self).action_confirm()
		return res


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	# NEW FIELDS
	thickness = fields.Float()
	bmt = fields.Float(string='BMT')
	nom_width = fields.Float(digits=(12,3))
	feed_coil = fields.Float()
	m_length = fields.Float(string='Length', digits=(12,3))
	coating_mass = fields.Integer()
	color = fields.Selection([('brown','B. Brown'),('red','S. Red'),('blue','P. Blue')])
	fh_cq = fields.Selection([('fh','FH'),('cq','CQ')], string='FH/CQ')
	wt = fields.Float(compute='_compute_wt', store=True, digits=(12,4)) # Compute Field
	wt_per_qty = fields.Float(compute='_compute_wt', store=True, digits=(12,4)) # Compute Field
	price_lm = fields.Float(string='Price/LM')
	p_mt = fields.Float(string='P/Mt', compute='_compute_p_mt', readonly=True, store=True) # Compute Field
	lm_mt = fields.Float(string='LM/Mt', compute='_compute_lm_mt', store=True, help='Yield', digits=(12,3)) # Compute Field

	# OVERRIDE FIELDS
	price_unit = fields.Float(compute='_compute_price_unit', store=True)

	# OVERRIDE FUNCTIONS
	# @api.multi
	# @api.onchange('product_id')
	# def product_id_change(self):
	# 	res = super(SaleOrderLine, self).product_id_change()

	# 	vals = {}

	# 	vals['thickness'] = self.product_id.thickness
	# 	vals['bmt'] = self.product_id.bmt
	# 	vals['nom_width'] = self.product_id.nom_width
	# 	vals['feed_coil'] = self.product_id.feed_coil
	# 	vals['m_length'] = self.product_id.m_length
	# 	vals['coating_mass'] = self.product_id.coating_mass
	# 	vals['color'] = self.product_id.color
	# 	vals['fh_cq'] = self.product_id.fh_cq
	# 	vals['price_lm'] = self.product_id.price_lm

	# 	self.update(vals)
	# 	return res

	# NEW FUNCTIONS
	@api.depends('price_lm','m_length')
	def _compute_price_unit(self):
		for line in self:
			line.price_unit = line.price_lm * line.m_length

	@api.depends('price_subtotal','wt')
	def _compute_p_mt(self):
		for line in self:
			if line.wt > 0:
				line.p_mt = line.price_subtotal / line.wt

	# COMPUTE YIELD
	@api.depends('bmt','feed_coil', 'coating_mass')
	def _compute_lm_mt(self):
		for line in self:
			if line.bmt and line.feed_coil and line.coating_mass:
				line.lm_mt = (1000000/((line.bmt * line.feed_coil * 7850) + (line.feed_coil * line.coating_mass) + (line.feed_coil * 53)))
				# 1000000 / (bmt * feed_coil * 7850) + (feed_coil * coating_mass) + (feed_coil * 53)

	# COMPUTE WEIGHT
	@api.depends('m_length','product_uom_qty', 'lm_mt')
	def _compute_wt(self):
		for line in self:
			if line.m_length and line.product_uom_qty and line.lm_mt:
				line.wt = ((line.m_length * line.product_uom_qty) / line.lm_mt)
				line.wt_per_qty = ((line.m_length * 1) / line.lm_mt)
				# ((length * qty)/yield)

	# @api.multi
	# def _get_bom_component_qty(self, bom):
	# 	product_bom_qty = self.wt_per_qty
	# 	bom_quantity = self.product_uom._compute_quantity(self.product_uom_qty, bom.product_uom_id)
	# 	boms, lines = bom.explode(self.product_id, bom_quantity)
	# 	components = {}
	# 	for line, line_data in lines:
	# 		product = line.product_id.id
	# 		uom = line.product_uom_id
	# 		# qty = line.product_qty
	# 		qty = product_bom_qty # Computed Wt per quantity
	# 		if components.get(product, False):
	# 			if uom.id != components[product]['uom']:
	# 				from_uom = uom
	# 				to_uom = self.env['product.uom'].browse(components[product]['uom'])
	# 				qty = from_uom._compute_quantity(qty, to_uom)
	# 			components[product]['qty'] += qty
	# 		else:
	# 			# To be in the uom reference of the product
	# 			to_uom = self.env['product.product'].browse(product).uom_id
	# 			if uom.id != to_uom.id:
	# 				from_uom = uom
	# 				qty = from_uom._compute_quantity(qty, to_uom)
	# 			components[product] = {'qty': qty, 'uom': to_uom.id}
	# 	return components

	@api.multi
	def _update_bom_qty(self):
		bom_line = self.env['mrp.bom.line']
		for record in self:
			product_bom_qty = record.wt_per_qty
			if record.product_id.bom_ids:
				for bom in record.product_id.bom_ids:
					# bom_line.search([('id',)])
					for line in bom.bom_line_ids:
						line.write({'product_qty': product_bom_qty})
		return True