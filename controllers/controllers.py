# -*- coding: utf-8 -*-
from odoo import http

# class MedicalVisit(http.Controller):
#     @http.route('/medical_visit/medical_visit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/medical_visit/medical_visit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('medical_visit.listing', {
#             'root': '/medical_visit/medical_visit',
#             'objects': http.request.env['medical_visit.medical_visit'].search([]),
#         })

#     @http.route('/medical_visit/medical_visit/objects/<model("medical_visit.medical_visit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('medical_visit.object', {
#             'object': obj
#         })