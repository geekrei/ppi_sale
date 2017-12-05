from odoo import models, fields, api, _

class PPISaleEstimate(models.Model):
	_name = 'ppi.sale.estimate'
	_description = 'Request for Estimate'
	_inherit = ['mail.thread']
	_order = "id desc"

	name = fields.Char(string='RFE No', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))

	customer_id = fields.Many2one('res.partner', 'Customer/Contractor', required=True)
	mailing_address = fields.Text('Complete Mailing Address')
	project_title = fields.Char('Project Title', required=True)
	jobsite_address = fields.Text('Complete Jobsite Address')

	product_id = fields.Many2one('product.product', 'Product Profile(s)', required=True)
	panel_thickness = fields.Float('Thickness for Panel')
	bended_thickness = fields.Float('Thickness for Bended')

	stainless_application_thickness = fields.Text('If project requires STAINLESS, specify application (bended) and thickness')
	
	insulation_specification = fields.Text('If project requires INSULATION, specify complete specification')
	insulation_over_the_purlin_laying = fields.Boolean('Over the Purlin Laying')
	insulation_under_the_purlin_laying = fields.Boolean('Under the Purlin Laying')
	insulation_fiberglass_density = fields.Char('For fiberglass insulation, indicate density')

	skylight_specification = fields.Text('If project requires SKYLIGHT specify complete specification')
	special_coating_requirement = fields.Text('Specify if special coating requirement')

	price_panel = fields.Float('Panel: Cost per metric ton or cost per meter or discount rate')
	price_bended = fields.Float('Bended: Cost per metric ton or cost per meter or discount rate')
	price_stainless = fields.Float('Stainless: Cost per metric pr cost per meter or discount rate')
	insulation_dicount_rate = fields.Float('Insulation: Discount Rate')
	hardware_discount_rate = fields.Float('Hardware: Discount Rate')
	labor_discount_rate = fields.Float('Labor: Discount Rate per Work Scope')

	other_requirements = fields.Text('Other Requirements')

	filed_by = fields.Many2one('res.partner', 'Filed By')
	filed_date = fields.Datetime('Filed Date')
	approved_by = fields.Many2one('res.partner', 'Approved By')

	state = fields.Selection([
		('draft', 'Draft'),
		('confirm', 'Confirmed'),
		('validate', 'Validated'),
		('quote', 'Sales Quote'),
		('cancel', 'Canceled'),
		], default='draft')

	@api.model
	def create(self, values):
		if values.get('name', 'New') == 'New':
			values['name'] = self.env['ir.sequence'].next_by_code('ppi_sale.estimate') or 'New'

		result = super(PPISaleEstimate, self).create(values)
	
		return result

	@api.multi
	def confirm_estimate(self):
		self.write({'state': 'confirm'})

	@api.multi
	def validate_estimate(self):
		self.write({'state': 'validate'})

	@api.multi
	def cancel_estimate(self):
		self.write({'state': 'cancel'})

	@api.multi
	def action_create_sales_quote(self):
		for record in self:
			sale_quote = self.env['sale.order'].create({
				'partner_id': record.customer_id.id,
			})
			if sale_quote:
				sale_quote_line = self.env['sale.order.line'].create({
					'order_id': sale_quote.id,
					'rfe_id': record.id,
					'product_id': record.product_id.id,
					'thickness': record.panel_thickness,
				})
			record.write({'state':'quote'})
			return True