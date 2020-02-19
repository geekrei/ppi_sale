from odoo import models, fields, api, _
from odoo.exceptions import UserError

from datetime import datetime, timedelta

from urllib import urlencode
from urlparse import urljoin

import logging
_logger = logging.getLogger(__name__)

class ProductionLot(models.Model):
	_inherit = 'stock.production.lot'

	is_migrated = fields.Boolean(string='Is Migrated?', default=False)
	pre_lot = fields.Char(string='Pre Lot', default='0', help='Use to redefine serial number uniquness for the sake of migrated serail numbers.')

	instock = fields.Boolean(string='In Stock?', default=False) # // DIABLED UNTIL FILTER CONDTION OF SERIAL IS STABILIZED

	# _sql_constraints = [
	# 	('name_ref_uniq', 'unique (name, product_id, pre_lot)', 'The combination of serial number and product must be unique !')
	# ]

	# FROM OLD INNOSEN MODULE
	def alert_calibration(self,days):

		def make_link(model,id,linktext):
			if not id:
				return ''
			base_url = self.env['ir.config_parameter'].get_param('web.base.url')
			query = {'db': self.env.cr.dbname}
			fragment = {
				'model': model,
				'id': id,
			}
			url = urljoin(base_url, "?%s#%s" % (urlencode(query), urlencode(fragment)))
			return """<a href="%s">%s</a>""" % (url,linktext)
		
		

		""" Issues a reminder for serial numbers due for calibration exactly x number of days from now"  
			To be called by the scheduler on a daily basis. 
			Only notified about lots of 'own' clients. 
			Each client MUST be assigned to sales person. Otherwise notification goes to user in whose name the scheduled task is run"""
		targetdate = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
		# this results in perpetual loop of parse method in osv/expression.py
		# lotsdue=self.search(cr,uid,[('calibration_due_on','=',targetdate)],order='client_id')
		# so we counterintuitively write like this :
		lotsdue = self.search([('calibration_due_on','=',targetdate),('client_id','!=',False)],order='client_id')
		
		if lotsdue:
			mail_message = self.env['mail.message']    
			subtypeid=self.env['ir.model.data'].get_object_reference('innosen','calibration_note')[1]
			user = self.env.user
			body=''   
			cnt=1
			for lot in lotsdue:
				# make body
				solnk=False
				dolnk=False
				client=lot.client_id
				for move in lot.mapped('quant_ids').mapped('history_ids'):
					#~ if move.sale_line_id:
						#~ if move.sale_line_id.order_id and not solnk:
							#~ solnk=make_link('sale.order',move.sale_line_id.order_id.id, move.sale_line_id.order_id.name)
						#~ if move.picking_id and move.picking_id.type=='out' and not dolnk:
							#~ dolnk=make_link('stock.picking',move.picking_id.id,move.picking_id.name)
					if move.picking_id and move.picking_id.picking_type_id.code=='outgoing':
						solnk=make_link('sale.order',move.picking_id.sale_id.id, move.picking_id.sale_id.name)
						dolnk=make_link('stock.picking',move.picking_id.id,move.picking_id.name)

				clientlnk=make_link('res.partner',client.id, client.name)
				lotlink=make_link('stock.production.lot',lot.id,"Serial Nr %s" % lot.name)
				body=body+'%s, (%s, %s)\n' % (lotlink, solnk if solnk else '?', dolnk if dolnk else '?')

				if cnt==len(lotsdue) or lotsdue[cnt].client_id<>client:
					# wrap body in message
					clientlnk=make_link('res.partner',client.id, client.name)
					subject=_("Calibration Due Notification for Client  %s") % client.name
					body=_("Calibration is due in %d days for the following serial numbers (sales order, delivery order):\n" % days)+body
					body=body+_("\nPlease notify client % s") % clientlnk
					# send message (one message per client) 
					# send_to = [client.user_id.partner_id.id if client.user_id and client.user_id.partner_id else user.partner_id.id]

					send_to = []
					if client.user_id:
						if client.user_id.partner_id:
							send_to.append(client.user_id.partner_id.id)
					elif not client.user_id:
						if client.parent_id and client.parent_id.user_id:
							if client.parent_id.user_id.partner_id:
								send_to.append(client.parent_id.user_id.partner_id.id)
					else:
						send_to.append(user.partner_id.id)

					# _logger.info("YOW")
					# _logger.info(send_to)

					mail_values = {
						'subject': subject,
						'body': body,
						'message_type': 'notification',
						'partner_ids':  [(6,0,send_to)], 
						'subtype_id':subtypeid,
					}

					mail_message.create(mail_values)

					# reset
					body=''
				cnt+=1
		return