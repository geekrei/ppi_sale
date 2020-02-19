from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
	_inherit = 'account.move'

	def find_between(self, string, first, last):
		try:
			start = string.index(first) + len(first)
			end = string.index(last, start)
			return string[start:end]
		except ValueError:
			return ""

	@api.multi
	def update_ref(self):
		for move in self:
			_logger.info('FILPI')
			ref = move.ref

			# new_ref = ''
			# if 'MO/' in value[2].get('name'):
			# 	new_ref = ref
				
			# if '(MO/' in value[2].get('name'):
			# 	string = value[2].get('name')
			# 	ref = self.find_between(string,'(',')')

			if 'MO/' in ref:
				# ref = self.find_between(ref, '; MO/', '')
				# _logger.info(ref)
				start = ref.index('MO/') + len('MO/')
				end = start + 5
				new_start = start - 3

				# _logger.info(start)
				# _logger.info(end)
				# _logger.info(ref[new_start:end])

				new_ref = ref[new_start:end]
				move.write({'ref': new_ref})

		# else:
		# 	ref = self.find_between(ref, 'MO/', ';')
		# 	_logger.info(ref)
		# if ';' in ref:
		# 	ref = self.find_between(ref, 'MO/', ';')

	# @api.model
	# def create(self, values):
	# 	ref = values.get('ref')

	# 	if not values.get('ref'):
	# 		if values.get('line_ids'):
	# 			for value in values.get('line_ids'):
	# 				if 'MO/' in value[2].get('name'):
	# 					ref = value[2].get('name')
	# 				if '(MO/' in value[2].get('name'):
	# 					string = value[2].get('name')
	# 					ref = self.find_between(string,'(',')')
		
	# 	result = super(AccountMove, self).create(values)
		
	# 	# TRY TO UPDATE REF
	# 	account_move = self.env['account.move'].browse(result.id)
	# 	if not account_move.ref:
	# 		account_move.write({'ref': ref})

	# 	return result

	# RECOMPUTE PARTNER ON JOURNAL ENTRY
	# USE PARTNER OF FIRST LINE ITEM
	@api.multi
	@api.depends('line_ids.partner_id')
	def _compute_partner_id(self):
		for move in self:
			partner = move.line_ids.mapped('partner_id')
			if partner:
				move.partner_id = partner[0].id
			else:
				move.partner_id = False

	def action_update_partner(self):
		self._compute_partner_id()

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	def action_compute_residual(self):
		self._amount_residual()