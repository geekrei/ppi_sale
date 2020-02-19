from odoo import models, fields, api, _ 

import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	user_id = fields.Many2one('res.users', string='Assigned To', index=True, track_visibility='onchange')

	# OVERRIDE CREATE TO SET PAYMENT TERM FOR SO GENERATED FROM PO
	@api.model
	def create(self, values):
		_logger.info("YSHSHSH")
		auto_generated = values.get('auto_generated')
		company_id = values.get('company_id')
		default_purchase_user = self.env.user

		if auto_generated and company_id:
			company_data = self.env['res.company'].search([('id','=',company_id)], limit=1)
			default_purchase_user = company_data.default_purchase_user

		values['user_id'] = default_purchase_user.id

		result = super(PurchaseOrder, self).create(values)

		if result and auto_generated and default_purchase_user:
			message = _("You have been assigned to this purchase order: <a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>") % (result.id, result.name)
			partner_ids = result.message_follower_ids
			_logger.info(partner_ids)
			_logger.info(message)
			result.message_post(body=message, partner_ids=partner_ids, subtype='mt_comment')
			# _logger.info(test)

		return result