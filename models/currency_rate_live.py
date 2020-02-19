from odoo import api, fields, models, _ 
from odoo.addons.web.controllers.main import xml2json_from_elementtree
from odoo.exceptions import UserError

from datetime import datetime, timedelta, date
from lxml import etree
import json
from dateutil.relativedelta import relativedelta
import requests
import urllib

import logging
_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
	_inherit = 'res.currency'

	base = fields.Boolean(default=False)

	@api.multi
	def update_rate(self):
		CurrencyRate = self.env['res.currency.rate']
		for currency in self:
			# Get Latest Rate
			latest_rate = self.env['res.currency.rate'].search([('currency_id', '=', currency.id)], order='name desc', limit=1)
			start_date = datetime(date.today().year, 1, 1)
			end_date = datetime.strptime(latest_rate.name, '%Y-%m-%d %H:%M:%S')

			# List dates to check
			total_days = (end_date - start_date).days + 1 #inclusive 5 days
			for day_number in range(total_days):
				current_date = (start_date + timedelta(days=day_number))

				rates = self.env['res.currency.rate'].search(['&',('currency_id', '=', currency.id),('name', '=', current_date.strftime("%Y-%m-%d %H:%M:%S"))])

				if not rates:
					# Get last rate
					last_rate = self.env['res.currency.rate'].search(['&',('currency_id', '=', currency.id),('name', '<', current_date.strftime("%Y-%m-%d %H:%M:%S"))], order='name desc', limit=1)
					_logger.info('NO RATE:' + str(current_date))
					_logger.info('LAST RATE' + str(last_rate.name))
					if last_rate:
						# Create rate from last rate
						_logger.info('RATE CREATED')
						vals = {
							'currency_id': currency.id,
							'rate': last_rate.rate,
							'name': current_date,
							'company_id': False,
						}
						CurrencyRate.create(vals)


class ResCompany(models.Model):
	_inherit = 'res.company'

	def _update_currency_ecb(self):
		''' This method is used to update the currencies by using ECB service provider.
			Rates are given against EURO
		'''
		Currency = self.env['res.currency']
		CurrencyRate = self.env['res.currency.rate']

		currencies = Currency.search([])
		currencies = [x.name for x in currencies]
		request_url = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
		try:
			parse_url = requests.request('GET', request_url)
		except:
			#connection error, the request wasn't successful
			return False
		xmlstr = etree.fromstring(parse_url.content)
		data = xml2json_from_elementtree(xmlstr)
		node = data['children'][2]['children'][0]
		currency_node = [(x['attrs']['currency'], x['attrs']['rate']) for x in node['children'] if x['attrs']['currency'] in currencies]

		ecb_ns = {
			'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
			'def': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'
		}

		rate_date = xmlstr.xpath('/gesmes:Envelope/def:Cube/def:Cube/@time', namespaces=ecb_ns)[0]
		rate_date_datetime = datetime.strptime(rate_date, '%Y-%m-%d')

		_logger.info('SWASK')
		_logger.info(rate_date_datetime)

		for company in self:
			base_currency_rate = 1
			# multi = company.multi_company_currency_enable
			if company.currency_id.name != 'EUR':
				#find today's rate for the base currency
				base_currency = company.currency_id.name
				base_currency_rates = [(x['attrs']['currency'], x['attrs']['rate']) for x in node['children'] if x['attrs']['currency'] == base_currency]
				base_currency_rate = len(base_currency_rates) and base_currency_rates[0][1] or 1
				currency_node += [('EUR', '1.0000')]

			for currency_code, rate in currency_node:
				rate = float(rate) / float(base_currency_rate)
				currency = Currency.search([('name', '=', currency_code)], limit=1)
				if currency:

					# IF RATE DOES NOT CHANGE BECAUSE THERE NO RATE FROM ECB, CREATE RATE FROM PREVIOUS RATE
					# CALCULATE DATE
					latest_rate = self.env['res.currency.rate'].search(['&',('currency_id', '=', currency.id),('name', '=', rate_date_datetime.strftime("%Y-%m-%d %H:%M:%S"))], order='name desc', limit=1)

					if latest_rate:
						rate_date_datetime = (rate_date_datetime + timedelta(days=1))
						# CHECK ANOTHER RATE
						latest_rate_2 = self.env['res.currency.rate'].search(['&',('currency_id', '=', currency.id),('name', '=', rate_date_datetime.strftime("%Y-%m-%d %H:%M:%S"))], order='name desc', limit=1)
						if latest_rate_2:
							rate_date_datetime = (rate_date_datetime + timedelta(days=1))

					vals = {
						'currency_id': currency.id,
						'rate': rate,
						'name': rate_date_datetime,
						'company_id': False,
					}
					
					CurrencyRate.create(vals)
		return True