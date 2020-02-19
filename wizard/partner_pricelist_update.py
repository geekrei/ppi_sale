from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class PartnerPricelistUpdate(models.TransientModel):
	_name = 'partner.pricelist.update'

	parent_ids = fields.Many2many('res.partner', string='Partners', required=True, default=None)

	# tags_to_add_ids = fields.Many2many(comodel_name='res.partner.category', relation='tag_add_partner_categ_rel', column1='tag_multiple_partners_id', column2='res_partner_category_id', string='Tags to Add')
	# tags_to_remove_ids = fields.Many2many(comodel_name='res.partner.category', relation='tag_remove_partner_categ_rel', column1='tag_multiple_partners_id', column2='res_partner_category_id', string='Tags to Remove')

	@api.multi
	def apply(self):
		for parent in self.parent_ids:
			pricelist_id = parent.property_product_pricelist
			for child in parent.child_ids:
				child.update_pricelist_all(pricelist_id)