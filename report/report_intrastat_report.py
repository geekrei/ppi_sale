from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists
import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

class ReportIntrastat(models.Model):
	_name = "report.intrastat"
	_description = "Intrastat report"
	_auto = False

	name = fields.Char(string='Year', readonly=True)
	month = fields.Selection([
		('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
		('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'),
		('09', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')],
		readonly=True)
	supply_units = fields.Float(string='Supply Units', readonly=True)
	ref = fields.Char(string='Source document', readonly=True)
	code = fields.Char(string='Country code', readonly=True) # country is now code
	hs_code = fields.Char('HS Code', readonly=True)
	intrastat_id = fields.Many2one('report.intrastat.code', string='Intrastat code', readonly=True)
	weight = fields.Float(string='Weight', readonly=True)
	value = fields.Float(string='Value', readonly=True, digits=0)           
	euro_value = fields.Float('Euro value',readonly=True, digits_compute=dp.get_precision('Account'))
	type = fields.Selection([('import', 'Import'), ('export', 'Export')], string='Type')
	currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
	province = fields.Char('Province')
	delivery_term = fields.Char('Delivery Term')
	type_transaction = fields.Integer('Nature Transaction')
	transport_method = fields.Integer('Transport Method')
	stat_regime = fields.Integer('Statistical Regime')
	company_id = fields.Many2one('res.company', string="Company", readonly=True)

	def init(self):
		drop_view_if_exists(self.env.cr, self._table)
		self.env.cr.execute("""CREATE or REPLACE VIEW report_intrastat as (
			WITH currency_rate (currency_id, rate, date_start, date_end) AS (
				SELECT r.currency_id, r.rate, r.name AS date_start,
					(SELECT name FROM res_currency_rate r2
					 WHERE r2.name > r.name AND
						   r2.currency_id = r.currency_id
					 ORDER BY r2.name ASC
					 LIMIT 1) AS date_end
				FROM res_currency_rate r
				), shipcost (lineid, shippingcost) AS (
					select id, case when shipcost>0 then shipcost else 0.0 end as sc  from account_invoice_line lin left join
					(select mostexpensive.invid, lineid, shipcost from (
					(select distinct on (i.id) i.id as invid, l.id as lineid, l.price_unit from account_invoice i join account_invoice_line l on (i.id=l.invoice_id)
					join product_product p on (l.product_id=p.id) join product_template t on (p.product_tmpl_id=t.id)
					where t.categ_id<>162
					order by i.id,  l.id, l.price_unit desc) as mostexpensive
					join
					(select i.id as invid,sum(l.price_subtotal) as shipcost from account_invoice i join account_invoice_line l on (i.id=l.invoice_id)
					join product_product p on (l.product_id=p.id) join product_template t on (p.product_tmpl_id=t.id)
					where t.categ_id=162
					group by i.id) as shipcost on (mostexpensive.invid=shipcost.invid))) as me on (lin.id=me.lineid)
					order by id
				)
				select
					to_char(inv.date_invoice, 'YYYY') as name,
					to_char(inv.date_invoice, 'MM') as month,
					min(inv_line.id) as id,
					pt.hs_code as hs_code,                    
					intrastat.id as intrastat_id,
					inv_country.name as code,
					sum(case when inv_line.price_unit is not null
							then inv_line.price_unit * (1-inv_line.discount/100.0) * inv_line.quantity + shipcost.shippingcost
							else 0
						end) as value,
					sum(
						case when uom.category_id != puom.category_id then (pt.weight * inv_line.quantity)
						when pt.uom_id != pt.uom_po_id and uom.uom_type = 'bigger' then (inv_line.quantity * pt.weight)
						when pt.uom_id != pt.uom_po_id and uom.uom_type = 'reference' then (inv_line.quantity * (puom.factor * po_uom.factor) * pt.weight)
						else (pt.weight * inv_line.quantity * uom.factor) end
					) as weight,
					sum(
						case when uom.category_id != puom.category_id then inv_line.quantity
						else (inv_line.quantity * uom.factor) end
					) as supply_units,

					inv.currency_id as currency_id,
					inv.number as ref,
					case when inv.type in ('out_invoice','in_refund')
						then 'export'
						else 'import'
						end as type,
					'Barcelona' as province,
					'FCA' as delivery_term,
					11 as type_transaction,
					4 as transport_method,
					2 as stat_regime,
					sum(case when inv_line.price_unit is not null
							then (inv_line.price_unit * (1-inv_line.discount/100.0) * inv_line.quantity + shipcost.shippingcost)/ cr.rate
							else 0
						end) as euro_value,
					inv.company_id as company_id                
				from
					account_invoice inv
					left join account_invoice_line inv_line on inv_line.invoice_id=inv.id
					join shipcost on inv_line.id=shipcost.lineid
					left join (product_template pt
						left join product_product pp on (pp.product_tmpl_id = pt.id))
					on (inv_line.product_id = pp.id)
					left join product_uom uom on uom.id=inv_line.uom_id
					left join product_uom puom on puom.id = pt.uom_id
					left join product_uom po_uom on po_uom.id = pt.uom_po_id
					left join report_intrastat_code intrastat on pt.intrastat_id = intrastat.id
					left join res_country inv_country on inv_country.id = inv.intrastat_country_id
					JOIN currency_rate cr ON
						(cr.currency_id = inv.currency_id AND
						cr.date_start <= COALESCE(inv.date_invoice, NOW()) AND
						(cr.date_end IS NULL OR cr.date_end > COALESCE(inv.date_invoice, NOW())))
				where
					inv.state in ('open','paid')
					and inv_line.product_id is not null
					and inv_line.price_subtotal<>0
					and inv_country.code<>'ES'
					and inv_country.intrastat=true
					and pt.type<>'service'
				group by to_char(inv.date_invoice, 'YYYY'), to_char(inv.date_invoice, 'MM'),intrastat.id,inv.type,pt.hs_code, pt.intrastat_id, inv_country.name,inv.number, inv.currency_id, inv.company_id
		)""")