from odoo import models, fields, api, _ 

import logging
_logger = logging.getLogger(__name__)

class CalendarAttendee(models.Model):
	_inherit = 'calendar.attendee'

	@api.multi
	def _send_mail_to_attendees(self, template_xmlid, force_send=False):

		force_send = True

		result = super(CalendarAttendee, self)._send_mail_to_attendees(template_xmlid, force_send)
		return result