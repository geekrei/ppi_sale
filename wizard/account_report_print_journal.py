# -*- coding: utf-8 -*-
from odoo import fields, models

import logging
_logger = logging.getLogger(__name__)

class AccountPrintJournal(models.TransientModel):
	_inherit = "account.print.journal"

	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
	report_format = fields.Selection([('pdf', 'PDF'), ('xls', 'Excel'),], 'Report Format', default='pdf')
	journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=None)

	def _print_report(self, data):
		data = self.pre_print_report(data)
		data['form'].update({'sort_selection': self.sort_selection})

		if self.report_format == 'pdf':
			return self.env['report'].with_context(landscape=True).get_action(self, 'account.report_journal', data=data)

		if self.report_format == 'xls':
			filename = 'Sales_Purchase_Journal.xls'
			company_id = data['form'].get('company_id')
			target_move = data['form'].get('target_move')
			sort_selection = data['form'].get('sort_selection')
			amount_currency = data['form'].get('amount_currency')
			date_from = data['form'].get('date_from')
			date_to = data['form'].get('date_to')
			journal_ids = data['form'].get('journal_ids')
			
			return {
				'type' : 'ir.actions.act_url',
				'url': '/web/export_xls/sale_purchase_journal?filename=%s&company_id=%s&target_move=%s&sort_selection=%s&amount_currency=%s&date_from=%s&date_to=%s&journal_ids=%s'%(filename,company_id,target_move,sort_selection,amount_currency,date_from,date_to,journal_ids),
				'target': 'self',
			}