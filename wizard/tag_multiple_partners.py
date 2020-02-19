from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class TagMultiplePartners(models.TransientModel):
	_name = 'tag.multiple.partners'
	# relation='sellers_project_rel', comodel_name='res.partner',column1='partner_id', column2='project_id'
	tags_to_add_ids = fields.Many2many(comodel_name='res.partner.category', relation='tag_add_partner_categ_rel', column1='tag_multiple_partners_id', column2='res_partner_category_id', string='Tags to Add')
	tags_to_remove_ids = fields.Many2many(comodel_name='res.partner.category', relation='tag_remove_partner_categ_rel', column1='tag_multiple_partners_id', column2='res_partner_category_id', string='Tags to Remove')

	@api.multi
	def apply(self):
		self.ensure_one()
		context = self._context or {}
		if context.get('active_ids', False):
			partner_ids = self.env['res.partner'].browse(context['active_ids'])
			tags_to_add_ids = self.env['res.partner.category'].browse(self.tags_to_add_ids.ids)
			tags_to_remove_ids = self.env['res.partner.category'].browse(self.tags_to_remove_ids.ids)
			for partner in partner_ids:
				tag_ids = partner.category_id
				new_add_tags = partner.category_id
				new_remove_tags = partner.category_id
				if tags_to_add_ids:
					for tag in tags_to_add_ids:
						partner.with_context(wizard=True).write({'category_id': [(4,tag.id)]})
					new_add_tags |= tags_to_add_ids
					partner.post_tag_changes(tag_ids.ids,new_add_tags.ids)

				if tags_to_remove_ids:
					for tag in tags_to_remove_ids:
						partner.with_context(wizard=True).write({'category_id': [(3,tag.id)]})
					new_remove_tags -= tags_to_remove_ids
					partner.post_tag_changes(tag_ids.ids,new_remove_tags.ids)
		else:
			raise UserError("You must select at least one contact.")