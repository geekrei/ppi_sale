# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
	_inherit = 'res.company'

	default_salesperson = fields.Many2one('res.users', string='Default Salesperson')
	default_purchase_user = fields.Many2one('res.users', string='Default Purchase Responsible')
	default_purchase_journal = fields.Many2one('account.journal', string='Default Purchase Journal', domain="[('company_id', '=', id),('type', '=', 'purchase')]")
	# default_purchase_refund_journal = fields.Many2one('account.journal', string='Default Purchase Refund Journal', domain="[('company_id', '=', id),('type', '=', 'purchase')]")

