from odoo import api, fields, models, _

class TagMultiplePartners(models.Model):
	_name = 'tag.multiple.partners'

	tags_to_add_ids = fields.Many2many('res.partner.category', 'tag_add_partner_rel', 'tag_add_id', 'tag_id', string='Tags to Add')
	tags_to_remove_ids = fields.Many2many('res.partner.category', 'tag_remove_partner_rel', 'tag_remove_id', 'tag_id', string='Tags to Remove')

	def apply(self):
		for contact in self:
			tags_to_add_ids = [(4,0,self.tags_to_add_ids.ids)]
			contact.write({'category_id': tags_to_add_ids})