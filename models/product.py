from odoo import models, fields, api, _ 

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	# NEW FIELDS
	thickness = fields.Float()
	bmt = fields.Float(string='BMT')
	nom_width = fields.Float(digits=(12,3))
	feed_coil = fields.Float()
	m_length = fields.Float(string='Length', digits=(12,3))
	coating_mass = fields.Integer()
	color = fields.Selection([('brown','B. Brown'),('red','S. Red'),('blue','P. Blue')])
	fh_cq = fields.Selection([('fh','FH'),('cq','CQ')], string='FH/CQ')
	price_lm = fields.Float(string='Price/LM')

	@api.onchange('price_lm','m_length')
	def _set_list_price(self):
		for line in self:
			line.list_price = line.price_lm * line.m_length