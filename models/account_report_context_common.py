from odoo import models, fields, api, _ 

try:
	from odoo.tools.misc import xlsxwriter
except ImportError:
	# TODO saas-17: remove the try/except to directly import from misc
	import xlsxwriter

import StringIO
import logging

_logger = logging.getLogger(__name__)

class AccountReportContextCommon(models.TransientModel):
	_inherit = "account.report.context.common"

	# Fix error when exporting (EXCEL) financial reports such as balance sheet and Profit and Loss. 
	# Cause: bug in version 10 if column header is number. Triggered if there's comparison in years. Enabling comparison will have column headers in format: 2018, 2017, 20161, 2015
	# Fix: Convert column header first to string before using replace
	def get_xlsx(self, response):
		output = StringIO.StringIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		report_id = self.get_report_obj()
		sheet = workbook.add_worksheet(report_id.get_title())

		def_style = workbook.add_format({'font_name': 'Arial'})
		title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
		level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
		level_0_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
		level_0_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
		level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
		level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
		level_1_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
		level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
		level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
		level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
		level_3_style = def_style
		level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
		level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
		domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
		domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
		domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
		upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

		num_style = workbook.add_format({'font_name': 'Arial','num_format': '"R" #,##0.00'})

		sheet.set_column(0, 0, 15) #  Set the first column width to 15

		sheet.write(0, 0, '', title_style)

		y_offset = 0
		if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
			sheet.write(y_offset, 0, '', title_style)
			sheet.write(y_offset, 1, '', title_style)
			x = 2
			for column in self.with_context(is_xls=True).get_special_date_line_names():
				sheet.write(y_offset, x, column, title_style)
				sheet.write(y_offset, x+1, '', title_style)
				x += 2
			sheet.write(y_offset, x, '', title_style)
			y_offset += 1

		x = 1
		# separate_symbol = False # // FOR SYSMBOL COLUMN
		for column in self.with_context(is_xls=True).get_columns_names():
			# column_lines += 1
			sheet.write(y_offset, x, str(column).replace('<br/>', ' ').replace('&nbsp;',' '), title_style)

			#  // FOR SYSMBOL COLUMN
			# if self.get_report_obj().get_name() == 'general_ledger' and str(column) == 'Currency':
			# 	x += 1
			# 	sheet.write(y_offset, x, 'Symbol ', title_style)
			# 	column_lines += 1
			x += 1
		y_offset += 1

		lines = report_id.with_context(no_format=True, print_mode=True).get_lines(self)
		currency = self.env['res.currency'].sudo().search([])
		# _logger.info("SWISSH")
		# _logger.info(lines)

		if lines:
			max_width = max([len(l['columns']) for l in lines])

		for y in range(0, len(lines)):
			if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
				for x in range(0, len(lines[y]['columns']) + 1):
					sheet.write(y + y_offset, x, None, upper_line_style)
				y_offset += 1
				style_left = level_0_style_left
				style_right = level_0_style_right
				style = level_0_style
			elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
				for x in range(0, len(lines[y]['columns']) + 1):
					sheet.write(y + y_offset, x, None, upper_line_style)
				y_offset += 1
				style_left = level_1_style_left
				style_right = level_1_style_right
				style = level_1_style
			elif lines[y].get('level') == 2:
				style_left = level_2_style_left
				style_right = level_2_style_right
				style = level_2_style
			elif lines[y].get('level') == 3:
				style_left = level_3_style_left
				style_right = level_3_style_right
				style = level_3_style
			elif lines[y].get('type') != 'line':
				style_left = domain_style_left
				style_right = domain_style_right
				style = domain_style
			else:
				style = def_style
				style_left = def_style
				style_right = def_style
			sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
			for x in xrange(1, max_width - len(lines[y]['columns']) + 1):
				sheet.write(y + y_offset, x, None, style)

			for x in xrange(1, len(lines[y]['columns']) + 1):
				is_curr_column = False

				if self.get_report_obj().get_name() == 'general_ledger' and x == 4:
					is_curr_column = True

				if isinstance(lines[y]['columns'][x - 1], tuple):
					lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
				if x < len(lines[y]['columns']):
					line_value = lines[y]['columns'][x - 1]

					
					if is_curr_column:
						line_value = str(line_value)
						new_curr = ''
						for curr in currency:
							if curr.symbol in line_value:
								line_value = line_value.replace(curr.symbol, ' ').replace(',', '').replace(' ', '')
								new_curr = curr.symbol

						# FURTHER CHECKING OF SYMBOL
						if 'US' in line_value:
							line_value =  line_value.replace('US', ' ').replace(',', '').replace(' ', '')
							new_curr = 'US'

						if '$' in line_value:
							line_value =  line_value.replace('$', ' ').replace(',', '').replace(' ', '')
							new_curr = '$'

						if line_value:
							line_value = float(line_value)
							curr_format = '"%s" #,##0.00' % new_curr
							num_style = workbook.add_format({'font_name': 'Arial','num_format': curr_format})
							style = num_style

					sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, line_value, style)


				else:
					line_value = lines[y]['columns'][x - 1]
					if is_curr_column:
						line_value = str(line_value)
						new_curr = ''
						for curr in currency:
							if curr.symbol in line_value:
								line_value = line_value.replace(curr.symbol, ' ').replace(',', '').replace(' ', '')
								new_curr = curr.symbol

						# FURTHER CHECKING OF SYMBOL
						if 'US' in line_value:
							line_value =  line_value.replace('US', ' ').replace(',', '').replace(' ', '')
							new_curr = 'US'
						if '$' in line_value:
							line_value =  line_value.replace('$', ' ').replace(',', '').replace(' ', '')
							new_curr = '$'

						if line_value:
							line_value = float(line_value)
							curr_format = '"%s" #,##0.00' % new_curr
							num_style = workbook.add_format({'font_name': 'Arial','num_format': curr_format})
							style = num_style

					sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, line_value, style_right)

			if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
				for x in xrange(0, len(lines[0]['columns']) + 1):
					sheet.write(y + 1 + y_offset, x, None, upper_line_style)
				y_offset += 1
		if lines:
			for x in xrange(0, max_width+1):
				sheet.write(len(lines) + y_offset, x, None, upper_line_style)

		workbook.close()
		output.seek(0)
		response.stream.write(output.read())
		output.close()