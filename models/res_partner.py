from odoo import models, fields, api, _
# from odoo.addons.base_vat.models.res_partner import _ref_vat
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class Partner(models.Model):
	_inherit = 'res.partner'

	# EXTEND TO ADD TRACKING
	name = fields.Char(index=True, track_visibility='onchange')
	active = fields.Boolean(default=True, track_visibility='onchange')
	email = fields.Char(track_visibility='onchange')
	phone = fields.Char(track_visibility='onchange')
	function = fields.Char(string='Job Position', track_visibility='onchange')

	# @api.constrains("vat")
	# def check_vat(self):
	# 	if self.env.user.company_id.vat_check_vies:
	# 		# force full VIES online check
	# 		check_func = self.vies_vat_check
	# 	else:
	# 		# quick and partial off-line checksum validation
	# 		check_func = self.simple_vat_check
	# 	for partner in self:
	# 		if not partner.vat:
	# 			continue

	# 		if self.env.ref('base.ph').id==partner.country_id.id:
	# 			vat_country, vat_number = 'ph', partner.vat
	# 		elif self.env.ref('base.no').id==partner.country_id.id:
	# 			vat_country, vat_number = 'no', partner.vat
	# 			continue
	# 		else:
	# 			vat_country, vat_number = self._split_vat(partner.vat)    
	# 		if not check_func(vat_country, vat_number):
	# 			_logger.info("Importing VAT Number [%s] is not valid !" % vat_number)
	# 			msg = partner._construct_constraint_msg()
	# 			raise ValidationError(msg)

	def check_vat_ph(self, vat):
		# number of digits must be 12
		if len(filter(lambda x: x.isdigit(), vat))==12:
			return True
		return False

	# Allow phillipines TIN number not to be preceded by PH
	@api.constrains("vat")
	def check_vat(self):
		if self.env.user.company_id.vat_check_vies:
			# force full VIES online check
			check_func = self.vies_vat_check
		else:
			# quick and partial off-line checksum validation
			check_func = self.simple_vat_check
		for partner in self:
			if not partner.vat:
				continue

			if not partner.parent_id and self.env.ref('base.ph').id==partner.country_id.id:    
				vat_country, vat_number = 'ph', partner.vat
			# ADDED CONDITION FOR ASSIGNING OF PARENT COMPANY DURING EDIT WHILE CONTACT HAVE NO COUNTRY DEFINED
			elif partner.parent_id and self.env.ref('base.ph').id==partner.parent_id.country_id.id:    
				vat_country, vat_number = 'ph', partner.vat
			else:
				vat_country, vat_number = self._split_vat(partner.vat)    
			if not check_func(vat_country, vat_number):
				_logger.info("Importing VAT Number [%s] is not valid !" % vat_number)
				msg = partner._construct_constraint_msg()
				raise ValidationError(msg)

	def check_vat_no(self, vat):
		'''
		Check Norway VAT number.See http://www.brreg.no/english/coordination/number.html
		'''
		if vat.endswith('MVA'):
			vat = vat[:len(vat)-3]
		return super(Partner,self).check_vat_no(vat)

	# FOR CONTACT PRICELIST/SHARED
	def update_pricelist(self, pricelist_id):
		property_product_pricelist = self.env['product.pricelist'].browse(pricelist_id)
		other_company = self.env['res.company'].sudo().search([('id','!=',self.env.user.company_id.id)])
		for company in other_company:			
			self.env['ir.property'].with_context(force_company=company.id).sudo().set_multi(
				'property_product_pricelist',
				self._name,
				{self.id: property_product_pricelist.id},
				default_value=property_product_pricelist.id
			)

	def update_pricelist_all(self, pricelist_id):
		property_product_pricelist = self.env['product.pricelist'].browse(pricelist_id)
		other_company = self.env['res.company'].sudo().search([('name','ilike','')])
		for company in other_company:			
			self.env['ir.property'].with_context(force_company=company.id).sudo().set_multi(
				'property_product_pricelist',
				self._name,
				{self.id: property_product_pricelist.id},
				default_value=property_product_pricelist.id
			)

	# REMOVE TAGS FROM OLD PARENT
	def remove_tag(self, tags):
		for partner in self:
			for tag in tags:
				partner.write({'category_id': [(3,tag.id)]})

	# POST MESSAGE MANUALLY BECAUSE TRACK_VISIBILITY DOES NOT WORK FOR FIELD TYPE MANY2MANY
	def post_tag_changes(self, current_tags, new_tags):		
		current_tags_name = ""
		get_current_tags = self.env['res.partner.category'].search([('id','in',current_tags)])
		for tag in get_current_tags:
			current_tags_name += tag.name + ", "


		new_tags_name = ""
		get_new_tags = self.env['res.partner.category'].search([('id','in',new_tags)])
		for tag in get_new_tags:
			new_tags_name += tag.name + ", "

		message = _('<ul class="o_mail_thread_message_tracking"><li>Tags: %s &#8594; %s</li></ul>') % (current_tags_name, new_tags_name)
		self.message_post(body=message)

	@api.model
	def create(self, values):
		# ADD TAGS FROM PARENT
		tag_ids = []

		parent = values.get('parent_id')
		child_ids = values.get('child_ids')

		# ON CREATE OF CONTACT WITH PARENT
		if parent:
			# APPEND TAG OF CHILD
			if values.get('category_id'):
				child_tags = values.get('category_id')[0][2]
				for tag in child_tags:
					tag_ids.append(tag)

			# APPEND TAG OF PARENT
			parent_id = self.env['res.partner'].browse(parent)
			if parent_id.category_id:
				for tag in parent_id.category_id:
					tag_ids.append(tag.id)
			if values.get('parent_category_id'):
				for tag in values.get('parent_category_id'):
					tag_ids.append(tag)

			# UPDATE TAG
			if tag_ids:
				values['category_id'] = [(4,tag_ids)]

		# ON CREATE OF PARENT AND CHILDS
		if not parent and child_ids:
			if values.get('category_id'):
				parent_tags = values.get('category_id')[0][2]
				for tag in parent_tags:
					tag_ids.append(tag)
			if tag_ids:
				child_count = 0
				for child in child_ids:
					values['child_ids'][child_count][2]['parent_category_id'] = tag_ids	
					child_count += 1

		result = super(Partner, self).create(values)

		return result


	@api.multi
	def write(self, values):
		# ADD TAGS FROM PARENT
		for record in self:
			is_wizard = self._context.get('wizard')
			current_tags = record.category_id

			new_tags = []
			if values.get('category_id'):
				child_tags = values.get('category_id')
				if not is_wizard:
					child_tags = values.get('category_id')[0][2]
				for tag in child_tags:
					new_tags.append(tag)

			parent_new = values.get('parent_id')
			partner_old = record.parent_id.id

			tags = False
			if parent_new:
				if partner_old and parent_new != partner_old:
					tags = record.parent_id.mapped('category_id')

				parent_new_id = self.env['res.partner'].browse(parent_new)
				tag_ids = parent_new_id.mapped('category_id')
				if tag_ids:
					for tag in tag_ids:
						new_tags.append(tag.id)
					values['category_id'] = [(4,new_tags)]				

			# REMOVE TAGS FROM OLD PARENT
			if partner_old and tags:
				record.remove_tag(tags)

			# POST MESSAGE MANUALLY BECAUSE TRACK_VISIBILITY DOES NOT WORK FOR FIELD TYPE MANY2MANY
			if new_tags and not is_wizard:
				record.post_tag_changes(current_tags.ids, new_tags)

		result = super(Partner, self).write(values)

		return result

	# @api.onchange('partner_id')
	# def _onchange_partner_id(self):
	# 	new_tags = []
	# 	tag_ids = self.partner_id.mapped('category_id')
	# 	_logger.info("TESSSST")
	# 	_logger.info(tag_ids)
	# 	if tag_ids:
	# 		for tag in tag_ids:
	# 			new_tags.append(tag.id)
	# 		self.category_id = [(4,new_tags)]

	@api.one
	def _inverse_product_pricelist(self):
		pls = self.env['product.pricelist'].search(
			[('country_group_ids.country_ids.code', '=', self.country_id and self.country_id.code or False)],
			limit=1
		)
		default_for_country = pls and pls[0]
		actual = self.env['ir.property'].get('property_product_pricelist', 'res.partner', 'res.partner,%s' % self.id)

		# update at each change country, and so erase old pricelist
		if self.property_product_pricelist or (actual and default_for_country and default_for_country.id != actual.id):
			# keep the company of the current user before sudo
			self.env['ir.property'].with_context(force_company=self.env.user.company_id.id).sudo().set_multi(
				'property_product_pricelist',
				self._name,
				{self.id: self.property_product_pricelist or default_for_country.id},
				default_value=default_for_country.id
			)

		# UPDATE PRICELIST OF ALL COMPANIES
		self.update_pricelist(self.property_product_pricelist)