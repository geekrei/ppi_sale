from odoo import models, fields, api, _ 
from datetime import datetime, timedelta
from openerp.exceptions import UserError
import pytz

import logging
_logger = logging.getLogger(__name__)

class ProjectTask(models.Model):
	_inherit = 'project.task'

	timesheet_validate_ids = fields.One2many('account.analytic.line.validate', 'task_id', 'Timesheets For Validation')

class AccountAnalyticLineValidate(models.Model):
	_name = 'account.analytic.line.validate'
	_description = 'Timesheets Validation'
	_inherit = ['mail.thread']

	@api.model
	def _default_user(self):
		return self.env.context.get('user_id', self.env.user.id)

	name = fields.Char('Description')
	date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
	# amount = fields.Monetary('Amount', required=True, default=0.0)
	unit_amount = fields.Float('Quantity', default=0.0)
	# account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True)
	partner_id = fields.Many2one('res.partner', string='Partner')
	user_id = fields.Many2one('res.users', string='User', default=_default_user)

	tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True)

	# company_id = fields.Many2one(related='account_id.company_id', string='Company', store=True, readonly=True)
	# currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

	task_id = fields.Many2one('project.task', 'Task')
	project_id = fields.Many2one('project.project', 'Project', domain=[('allow_timesheets', '=', True)])

	manager_id = fields.Many2one('hr.employee', string='Manager')
	related_timesheet_id = fields.Many2one('account.analytic.line', string='Related Timesheet')

	state = fields.Selection([
		('draft', 'Draft'),
		('confirm', 'Submitted'),
		('validate', 'Validated'),
		('reject', 'Rejected')
		], default='draft', string='Status')

	def confirm(self):
		self.add_follower()
		if not self.manager_id:
			raise UserError("Employee User have no manager assigned.")
		message = _("Timesheet validation have been submitted: <a href=# data-oe-model=account.analytic.line.validate data-oe-id=%d>%s</a>") % (self.id, self.name)
		partner_ids = self.message_follower_ids
		self.message_post(body=message, partner_ids=partner_ids, subtype='mt_comment')
		self.write({'state':'confirm'})

	def validate(self):
		user = self.env['res.users'].browse(self.env.uid)
		if user.id == self.manager_id.user_id.id:
			analytic_line = self.env['account.analytic.line'].create({
				'project_id': self.project_id.id,
				'date': self.date,
				'task_id': self.task_id.id,
				'unit_amount': self.unit_amount,
				'name': self.name,
				'timesheet_validate_id': self.id,
				'user_id': self.user_id.id,
			})
			if analytic_line:
				self.write({'state':'validate', 'related_timesheet_id': analytic_line.id})
		else:
			raise UserError("You are not allowed to validate this timesheet!")

	def reject(self):
		user = self.env['res.users'].browse(self.env.uid)
		if user.id == self.manager_id.user_id.id:
			self.write({'state':'reject'})
		else:
			raise UserError("You are not allowed to reject this timesheet!")

	@api.multi
	def add_follower(self):
		user_ids = []
		employee = self.env['hr.employee'].search([('id','in',self.env.user.employee_ids.ids)], limit=1)
		if employee.parent_id and employee.parent_id.user_id:
			user_ids.append(employee.parent_id.user_id.id)
			self.write({'manager_id': employee.parent_id.id})
		self.message_subscribe_users(user_ids=user_ids)


class AccountAnalyticLine(models.Model):
	_inherit = 'account.analytic.line'

	timesheet_validate_id = fields.Many2one('account.analytic.line.validate', string='Timesheet Validated')

	def create_analytic_validate(self, project_id, date, task_id, unit_amount, name):
		analytic_line_validate = self.env['account.analytic.line.validate'].create({
			'project_id': project_id,
			'date': date,
			'task_id': task_id,
			'unit_amount': unit_amount,
			'name': name,
		})
		return analytic_line_validate

	
	@api.model
	def create(self, vals):
		if vals.get('date') and not vals.get('timesheet_validate_id'):
			user = self.env['res.users'].browse(self.env.uid)
			tz = pytz.timezone('UTC')
			if user.tz:
				tz = pytz.timezone(user.tz)
			
			date = datetime.strptime(vals.get('date'), '%Y-%m-%d')
			
			leave_ids = self.env['hr.holidays'].search([('employee_id','in',self.env.user.employee_ids.ids),('state','=','validate')])
			for leave in leave_ids:
				date_from_datetime = leave.date_from
				date_to_datetime = leave.date_to

				if date_from_datetime and date_to_datetime:
					date_from_date = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S')
					date_to_date = datetime.strptime(leave.date_to, '%Y-%m-%d %H:%M:%S')
					tz_date_from_date = pytz.utc.localize(date_from_date).astimezone(tz)
					tz_date_to_date = pytz.utc.localize(date_to_date).astimezone(tz)

					if date.date() >= tz_date_from_date.date() and date.date() <= tz_date_to_date.date():
						if leave.number_of_days_temp < 1:
							# date = datetime.strptime(vals.get('date'), '%Y-%m-%d')
							# date_tz = pytz.utc.localize(date).astimezone(tz)
							# if tz_date_from_date <= date_tz and tz_date_to_date >= date_tz:
							# Create timesheet for approval

							# project = self.env['project.project'].browse(vals.get('project_id'))
							# analytic_line_validate = self.env['account.analytic.line.validate'].create({
							# 	'project_id': vals.get('project_id'),
							# 	'date': vals.get('date'),
							# 	'task_id': vals.get('task_id'),
							# 	'unit_amount': vals.get('unit_amount'),
							# 	'name': vals.get('name'),
							# 	'account_id': project.analytic_account_id.id,
							# })

							# analytic_line_validate = self.sudo().create_analytic_validate(vals.get('project_id'), vals.get('date'), vals.get('task_id'), vals.get('unit_amount'), vals.get('name'))


							# self._call_wizard(analytic_line_validate)

							# return {
							# 	'name': _('Timesheet for Validation'),
							# 	'view_type': 'form',
							# 	'view_mode': 'form,tree',
							# 	'res_model': 'account.analytic.line.validate',
							# 	'res_id': analytic_line_validate.id,
							# 	'type': 'ir.actions.act_window',
							# 	# 'context': ctx,
							# 	'target': 'new',
							# }
							# _logger.info(analytic_line_validate)
							# if analytic_line_validate:
							# raise UserError("You have a registered half day leave on this date. A timesheet for validation have been submitted to your manager. Once validated, your timesheet will be registered. You can also create a timesheet for validation here: Timesheets -> My Timesheets For Validation")
								
							# else:
							raise UserError(_("You cannot enter a timesheet on this date. You have a registered half day leave on this date. To create a timesheet for this date, it should be validated first. Go to Timesheets -> My Timesheets For Validation to create one and submit it to your manager. You can also create timesheet validation task forms using the TIMESHEET VALIDATION tab."))
						else:
							raise UserError(_("You cannot enter a timesheet on this date. You have a registered leave on this date."))
					
			# Check for public holidays
			holiday_ids = self.env['hr.holidays.public.line'].search([('date','=',date)])
			for holiday in holiday_ids:
				if holiday.date:
					holiday_date = datetime.strptime(holiday.date, '%Y-%m-%d')
				
					if holiday_date.date() == date.date():
						raise UserError(_("You cannot enter a timesheet on this date. This date is a public holiday."))


		return super(AccountAnalyticLine, self).create(vals)


	@api.multi
	def write(self, vals):
		# if vals.get('timesheet_validate_id'):
		# 	raise UserError("You are not allowed to modify timesheet with related validation!")
		if vals.get('date') and not vals.get('timesheet_validate_id'):
			user = self.env['res.users'].browse(self.env.uid)
			tz = pytz.timezone('UTC')
			if user.tz:
				tz = pytz.timezone(user.tz)
			
			date = datetime.strptime(vals.get('date'), '%Y-%m-%d')
			
			leave_ids = self.env['hr.holidays'].search([('employee_id','in',self.env.user.employee_ids.ids),('state','=','validate')])
			for leave in leave_ids:
				date_from_datetime = leave.date_from
				date_to_datetime = leave.date_to

				if date_from_datetime and date_to_datetime:
					date_from_date = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S')
					date_to_date = datetime.strptime(leave.date_to, '%Y-%m-%d %H:%M:%S')
					tz_date_from_date = pytz.utc.localize(date_from_date).astimezone(tz)
					tz_date_to_date = pytz.utc.localize(date_to_date).astimezone(tz)

					# raise UserError(_("You cannot enter a timesheet on this date. You have a registered leave on this date."))

					if date.date() >= tz_date_from_date.date() and date.date() <= tz_date_to_date.date():
						if leave.number_of_days_temp < 1:
							# date = datetime.strptime(vals.get('date'), '%Y-%m-%d')
							# date_tz = pytz.utc.localize(date).astimezone(tz)
							# if tz_date_from_date <= date_tz and tz_date_to_date >= date_tz:
							# Create timesheet for approval

							# project = self.env['project.project'].browse(vals.get('project_id'))
							# analytic_line_validate = self.env['account.analytic.line.validate'].create({
							# 	'project_id': vals.get('project_id'),
							# 	'date': vals.get('date'),
							# 	'task_id': vals.get('task_id'),
							# 	'unit_amount': vals.get('unit_amount'),
							# 	'name': vals.get('name'),
							# 	'account_id': project.analytic_account_id.id,
							# })

							# analytic_line_validate = self.sudo().create_analytic_validate(vals.get('project_id'), vals.get('date'), vals.get('task_id'), vals.get('unit_amount'), vals.get('name'))


							# self._call_wizard(analytic_line_validate)

							# return {
							# 	'name': _('Timesheet for Validation'),
							# 	'view_type': 'form',
							# 	'view_mode': 'form,tree',
							# 	'res_model': 'account.analytic.line.validate',
							# 	'res_id': analytic_line_validate.id,
							# 	'type': 'ir.actions.act_window',
							# 	# 'context': ctx,
							# 	'target': 'new',
							# }
							# _logger.info(analytic_line_validate)
							# if analytic_line_validate:
							# 	raise UserError("You have a registered half day leave on this date. A timesheet for validation have been submitted to your manager. Once validated, your timesheet will be registered. You can also create a timesheet for validation here: Timesheets -> My Timesheets For Validation")
								
							# else:
							# 	raise UserError(_("You cannot enter a timesheet on this date. You have a registered half day leave on this date. To create a timesheet for this date, it should be validated first. Go to Timesheets -> My Timesheets For Validation to create one and submit it to your manager."))
							raise UserError(_("You cannot enter a timesheet on this date. You have a registered half day leave on this date. To create a timesheet for this date, it should be validated first. Go to Timesheets -> My Timesheets For Validation to create one and submit it to your manager. You can also create timesheet validation task forms using the TIMESHEET VALIDATION tab."))
						else:
							raise UserError(_("You cannot enter a timesheet on this date. You have a registered leave on this date."))
					
			# Check for public holidays
			holiday_ids = self.env['hr.holidays.public.line'].search([('date','=',date)])
			for holiday in holiday_ids:
				if holiday.date:
					holiday_date = datetime.strptime(holiday.date, '%Y-%m-%d')
				
					if holiday_date.date() == date.date():
						raise UserError(_("You cannot enter a timesheet on this date. This date is a public holiday."))
		
		return super(AccountAnalyticLine, self).write(vals)
