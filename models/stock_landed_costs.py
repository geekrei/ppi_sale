from odoo import models, fields, api, _ 

# FIX SEQUENCE OF LANDED COST
class LandedCost(models.Model):
	_inherit = 'stock.landed.cost'

	name = fields.Char('Name', default=lambda self: _('New'), copy=False, readonly=True, track_visibility='always')

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('stock.landed.cost') or _('New')
		result = super(LandedCost, self).create(vals)
		return result

class LandedCostLine(models.Model):
	_inherit = 'stock.landed.cost.lines'

	partner_id = fields.Many2one('res.partner', string="Partner")

class AdjustmentLines(models.Model):
	_inherit = 'stock.valuation.adjustment.lines'

	def _create_account_move_line(self, move, credit_account_id, debit_account_id, qty_out, already_out_account_id):
		"""
		Generate the account.move.line values to track the landed cost.
		Afterwards, for the goods that are already out of stock, we should create the out moves
		"""
		AccountMoveLine = self.env['account.move.line'].with_context(check_move_validity=False, recompute=False)

		base_line = {
			'name': self.name,
			'move_id': move.id,
			'product_id': self.product_id.id,
			'quantity': self.quantity,
			'partner_id': self.cost_line_id.partner_id.id,
		}
		debit_line = dict(base_line, account_id=debit_account_id)
		credit_line = dict(base_line, account_id=credit_account_id)
		diff = self.additional_landed_cost
		if diff > 0:
			debit_line['debit'] = diff
			credit_line['credit'] = diff
		else:
			# negative cost, reverse the entry
			debit_line['credit'] = -diff
			credit_line['debit'] = -diff
		AccountMoveLine.create(debit_line)
		AccountMoveLine.create(credit_line)

		# Create account move lines for quants already out of stock
		if qty_out > 0:
			debit_line = dict(base_line,
							  name=(self.name + ": " + str(qty_out) + _(' already out')),
							  quantity=qty_out,
							  account_id=already_out_account_id)
			credit_line = dict(base_line,
							   name=(self.name + ": " + str(qty_out) + _(' already out')),
							   quantity=qty_out,
							   account_id=debit_account_id)
			diff = diff * qty_out / self.quantity
			if diff > 0:
				debit_line['debit'] = diff
				credit_line['credit'] = diff
			else:
				# negative cost, reverse the entry
				debit_line['credit'] = -diff
				credit_line['debit'] = -diff
			AccountMoveLine.create(debit_line)
			AccountMoveLine.create(credit_line)

			# TDE FIXME: oh dear
			if self.env.user.company_id.anglo_saxon_accounting:
				debit_line = dict(base_line,
								  name=(self.name + ": " + str(qty_out) + _(' already out')),
								  quantity=qty_out,
								  account_id=credit_account_id)
				credit_line = dict(base_line,
								   name=(self.name + ": " + str(qty_out) + _(' already out')),
								   quantity=qty_out,
								   account_id=already_out_account_id)

				if diff > 0:
					debit_line['debit'] = diff
					credit_line['credit'] = diff
				else:
					# negative cost, reverse the entry
					debit_line['credit'] = -diff
					credit_line['debit'] = -diff
				AccountMoveLine.create(debit_line)
				AccountMoveLine.create(credit_line)

		return True