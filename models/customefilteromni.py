# # -*- coding: utf-8 -*-
# from odoo import models, fields, api,

# import datetime

# class currentdate(models.Model):
# # _name = current_date.omni
# 	_inherit = 'hr.holidays'

# 	current_year = fields.Char(compute='get_current_year')

# 	def get_current_year(self):

# 		 now = datetime.datetime.now()
# 		 self.current_year = now.year