from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class MrpUnbuild(models.Model):
	_inherit = 'mrp.unbuild'

	@api.multi
	def action_unbuild(self):
		_logger.info('BATIK')
		self.ensure_one()
		if self.product_id.tracking != 'none' and not self.lot_id.id:
			raise UserError(_('Should have a lot for the finished product'))

		consume_move = self._generate_consume_moves()[0]
		produce_moves = self._generate_produce_moves()

		_logger.info(consume_move)
		_logger.info(produce_moves)

		# Search quants that passed production order
		qty = self.product_qty  # Convert to qty on product UoM
		if self.mo_id:
			finished_moves = self.mo_id.move_finished_ids.filtered(lambda move: move.product_id == self.mo_id.product_id)
			domain = [('qty', '>', 0), ('history_ids', 'in', finished_moves.ids)]
		else:
			domain = [('qty', '>', 0)]
		quants = self.env['stock.quant'].quants_get_preferred_domain(
			qty, consume_move,
			domain=domain,
			preferred_domain_list=[],
			lot_id=self.lot_id.id)
		self.env['stock.quant'].quants_reserve(quants, consume_move)

		if consume_move.has_tracking != 'none':
			if not quants[0][0]:
				raise UserError(_("You don't have in the stock the lot %s.") % (self.lot_id.name,))
			self.env['stock.move.lots'].create({
				'move_id': consume_move.id,
				'lot_id': self.lot_id.id,
				'quantity_done': consume_move.product_uom_qty,
				'quantity': consume_move.product_uom_qty})
		else:
			consume_move.quantity_done = consume_move.product_uom_qty
		consume_move.move_validate()
		# original_quants = consume_move.quant_ids.mapped('consumed_quant_ids')
		original_quants = self.mo_id.move_raw_ids.mapped('quant_ids')

		_logger.info(consume_move.quant_ids)
		_logger.info(original_quants)

		for produce_move in produce_moves:
			if produce_move.has_tracking != 'none':
				original = original_quants.filtered(lambda quant: quant.product_id == produce_move.product_id)
				if not original:
					raise UserError(_("You don't have in the stock the required lot/serial number for %s .") % (produce_move.product_id.name,))
				quantity_todo = produce_move.product_qty
				for quant in original:
					if quantity_todo <= 0:
						break
					move_quantity = min(quantity_todo, quant.qty)
					self.env['stock.move.lots'].create({
						'move_id': produce_move.id,
						'lot_id': quant.lot_id.id,
						'quantity_done': produce_move.product_id.uom_id._compute_quantity(move_quantity, produce_move.product_uom),
						'quantity': produce_move.product_id.uom_id._compute_quantity(move_quantity, produce_move.product_uom),
					})
					quantity_todo -= move_quantity
			else:
				produce_move.quantity_done = produce_move.product_uom_qty
		produce_moves.move_validate()
		produced_quant_ids = produce_moves.mapped('quant_ids').filtered(lambda quant: quant.qty > 0)
		consume_move.quant_ids.sudo().write({'produced_quant_ids': [(6, 0, produced_quant_ids.ids)]})

		return self.write({'state': 'done'})