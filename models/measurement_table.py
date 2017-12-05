from odoo import models, fields, api, _

class MeasurementLength(models.Model):
	_name = 'measurement.length'

	name = fields.Float()

class MeasurementWidth(models.Model):
	_name = 'measurement.width'

	name = fields.Float()

class MeasurementBmt(models.Model):
	_name = 'measurement.bmt'

	name = fields.Float()