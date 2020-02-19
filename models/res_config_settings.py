from odoo import models, fields, api, _

class StockConfigSettings(models.TransientModel):
	_inherit = 'stock.config.settings'

	# group_account_move_status = fields.Boolean(string="Status of Accounting Entries", implied_group='stock_account.group_inventory_valuation', help="""Option to post entries automatically or not.""")
	group_account_move_status = fields.Selection([
		('draft', 'Set to draft'),
		('post', 'Set to posted')], default='draft',
		string="Status of Accounting Entries",
		help="Option to post entries automatically or not.")

	@api.multi
	def set_group_account_move_status_defaults(self):
		return self.env['ir.values'].sudo().set_default('stock.config.settings', 'group_account_move_status', self.group_account_move_status)


# class SaleConfigSettings(models.TransientModel):
# 	_inherit = 'sale.config.settings'

# 	default_salesperson = fields.Many2one(related='company_id.default_salesperson', string="Default Salesperson")