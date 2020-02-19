from odoo import api, fields, models, _

class TagMultiplePartner(models.Model):
	_name = 'tag.multiple.partner'

	tags_to_add_ids = fields.Many2many('res.partner.category', 'tag_add_partner_rel', 'tag_add_id', 'tag_id', string='Tags to Add')
	tags_to_remove_ids = fields.Many2many('res.partner.category', 'tag_remove_partner_rel', 'tag_remove_id', 'tag_id', string='Tags to Remove')