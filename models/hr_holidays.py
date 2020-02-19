# -*- coding: utf-8 -*-
from odoo import models, fields, api

from datetime import datetime

class Holidays(models.Model):
	_inherit = 'hr.holidays'

	state = fields.Selection(default='draft')
	# current_year_start = fields.Datetime(compute='get_current_year')
	# current_year_end = fields.Datetime(compute='get_current_year')
	# this_year = fields.Boolean(default=False, compute='get_this_year')

	# @api.multi
	# def get_current_year(self):
	# 	for holiday in self:
	# 		holiday.current_year_start = datetime.now().date().replace(month=1, day=1)
	# 		holiday.current_year_end = datetime.now().date().replace(month=12, day=31)

	# @api.multi
	# def get_this_year(self):
	# 	for holiday in self:
	# 		if holiday.date_from >= holiday.current_year_start and holiday.date_from <= holiday.current_year_end:
	# 			holiday.this_year = True

	@api.multi
	def add_follower(self, employee_id):
		user_ids = []
		employee = self.env['hr.employee'].browse(employee_id)
		if employee.user_id:
			user_ids.append(employee.user_id.id)
		if employee.parent_id and employee.parent_id.user_id:
			user_ids.append(employee.parent_id.user_id.id)
		self.message_subscribe_users(user_ids=user_ids)