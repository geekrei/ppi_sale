from odoo import models, fields, api, _ 
from odoo.tools import float_is_zero, float_compare

import logging
_logger = logging.getLogger(__name__)

class HRPayslip(models.Model):
	_name = 'hr.payslip'
	_inherit = ['hr.payslip','mail.thread']

	@api.multi
	def action_payslip_done(self):
		_logger.info("EOPSEO")
		precision = self.env['decimal.precision'].precision_get('Payroll')
		currobj= self.env['res.currency']

		for payslip in self:
			payslip.compute_sheet()
			companycurrency = payslip.employee_id.company_id.currency_id  # JV
			slipcurrency = payslip.struct_id.currency_id if payslip.struct_id.currency_id else companycurrency  # JV
			exchange = True if companycurrency != slipcurrency else False  # JV
			line_ids = []
			debit_sum = 0.0
			credit_sum = 0.0
			date = payslip.date or payslip.date_to

			default_partner_id = payslip.employee_id.address_home_id.id #JV
			name = _('Payslip of %s') % (payslip.employee_id.name)
			move_dict = {
				'narration': name,
				'ref': payslip.number,
				'journal_id': payslip.journal_id.id,
				'date': date,
			}
			for line in payslip.details_by_salary_rule_category:
				#amount = slip.credit_note and -line.total or line.total #JV
				adjamt = -line.total if line.total<0 else line.total # JV adjust to allow negative signs
				exchamt = payslip.credit_note and -adjamt or adjamt # JV adjust for credit note
				if exchange:
					amount = currobj.with_context(date=date)._compute(slipcurrency,companycurrency,exchamt) #JV
				else: #JV
					amount = exchamt               #JV 
				if float_is_zero(amount, precision_digits=precision):
					continue
				debit_account_id = line.salary_rule_id.account_debit.id
				credit_account_id = line.salary_rule_id.account_credit.id

				if debit_account_id:
					debit_line = (0, 0, {
						'name': line.name,
						'partner_id': line._get_partner_id(credit_account=False),
						'account_id': debit_account_id,
						'journal_id': payslip.journal_id.id,
						'date': date,
						'debit': amount > 0.0 and amount or 0.0,
						'credit': amount < 0.0 and -amount or 0.0,
						'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
						'tax_line_id': line.salary_rule_id.account_tax_id.id,
					})
					#JV only append entries to employee so to be sure that an employee entry is the first in the list of move
					#line_ids.append(debit_line) #JV
					if debit_line[2]['partner_id']==default_partner_id:  #JV
						line_ids.append(debit_line)  #JV
					else:  #JV
						line_ids.insert(0,debit_line)  #JV                      
					debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

				if credit_account_id:
					credit_line = (0, 0, {
						'name': line.name,
						'partner_id': line._get_partner_id(credit_account=True),
						'account_id': credit_account_id,
						'journal_id': payslip.journal_id.id,
						'date': date,
						'debit': amount < 0.0 and -amount or 0.0,
						'credit': amount > 0.0 and amount or 0.0,
						'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
						'tax_line_id': line.salary_rule_id.account_tax_id.id,
					})
					#JV only append entries to employee so to be sure that an employee entry is the first in the list of move
					# line_ids.append(credit_line) #JV
					if credit_line[2]['partner_id']==default_partner_id: #JV
						line_ids.append(credit_line) #JV
					else: #JV
						line_ids.insert(0,credit_line) #JV                    

					credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

			if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
				acc_id = payslip.journal_id.default_credit_account_id.id
				if not acc_id:
					raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (payslip.journal_id.name))
				adjust_credit = (0, 0, {
					'name': _('Adjustment Entry'),
					'partner_id': False,
					'account_id': acc_id,
					'journal_id': payslip.journal_id.id,
					'date': date,
					'debit': 0.0,
					'credit': debit_sum - credit_sum,
				})
				# JV change here prepend instead of append because last item becomes first in move entry list
				#line_ids.append(adjust_credit) #JV
				line_ids.insert(0,adjust_credit)  #JV             

			elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
				acc_id = payslip.journal_id.default_debit_account_id.id
				if not acc_id:
					raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (payslip.journal_id.name))
				adjust_debit = (0, 0, {
					'name': _('Adjustment Entry'),
					'partner_id': False,
					'account_id': acc_id,
					'journal_id': payslip.journal_id.id,
					'date': date,
					'debit': credit_sum - debit_sum,
					'credit': 0.0,
				})
				# JV change here prepend instead of append because last item becomes first in move entry list
				# line_ids.append(adjust_debit) #JV
				line_ids.insert(0,adjust_debit)  #JV
			move_dict['line_ids'] = line_ids
			move = self.env['account.move'].create(move_dict)
			payslip.write({'move_id': move.id, 'date': date})
			move.post()
		
			# FROM PHILPAY FOR LOANS SINCE WE OVERRIDE THE CONFIRM FUNCTION
			for payslip_detail in payslip.details_by_salary_rule_category:
				if payslip_detail.salary_rule_id.is_loan_rule == True:
					loan_obj = self.env['hr.employee.loans'].search([('id', '=', payslip_detail.loan_payment_tempo_id.id)])
					if loan_obj:
						write_list = {}
						write_list = {'no_of_payments': loan_obj.no_of_payments -1}
						if loan_obj.no_of_payments -1 <=0:
							write_list['state'] = 'paid'
						loan_obj.write(write_list)

		return self.write({'state': 'done'})