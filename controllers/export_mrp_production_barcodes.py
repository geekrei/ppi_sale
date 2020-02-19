# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import deque
import json

from odoo import http
from odoo.http import request
from odoo.tools import ustr
from odoo.tools.misc import xlwt
# from xlsxwriter.workbook import Workbook

from datetime import datetime
from datetime import date
import ast

from PIL import Image
from StringIO import StringIO
from io import BytesIO
from reportlab.graphics.barcode import createBarcodeDrawing

import logging
_logger = logging.getLogger(__name__)


class MrpProductionBarcodes(http.Controller):

	@http.route('/web/export_xls/mrp_production_barcodes', type='http', auth="user")
	def export_xls(self, production_id, **kw):
		filename = 'Production_Barcodes.xls'
		workbook = xlwt.Workbook()
		worksheet = workbook.add_sheet('Production Barcodes')

		production_data = request.env['mrp.production'].sudo().search([('id','=',production_id)])


		# STYLES
		
		# style_table_row = xlwt.easyxf("font: name Calibri;align: horiz left, wrap no;borders: top thin, bottom thin, right thin;")
		# worksheet.col(0).width = 256*20

		# TABLE HEADER
		# worksheet.write(0, 0, 'CITY', style_table_header_bold) # HEADER
		
		row_count = 0

		for production in production_data:
			# filename += production.name
			for move in production.move_finished_ids:
				for lot in move.active_move_lot_ids:
					# BARCODE IMAGE
					# worksheet.row(row_count).height = 256*20
					
					# barcode = request.env['report'].barcode('Code128', lot.lot_id.name, width=600, height=100, humanreadable=0)
					# barcode_response = request.make_response(barcode, headers=[('Content-Type', 'image/png')])
					# if barcode_response.status_code == 200:
					# 	img = Image.open(StringIO(barcode_response.data))
					# 	image_parts = img.split()
					# 	r = image_parts[0]
					# 	g = image_parts[1]
					# 	b = image_parts[2]
					# 	img = Image.merge("RGB", (r, g, b))
					# 	fo = BytesIO()
					# 	img.save(fo, format='bmp')
					# 	worksheet.insert_bitmap_data(fo.getvalue(),row_count,0)
					# 	img.close()

					# 	row_count +=8
					# BARCODE IMAGE
					worksheet.write(row_count, 0, lot.lot_id.name)
					row_count +=1


		response = request.make_response(None,
			headers=[('Content-Type', 'application/vnd.ms-excel'),
					('Content-Disposition', 'attachment; filename=%s;'%(filename)
					)])

		workbook.save(response.stream)
		# workbook.close()

		return response
