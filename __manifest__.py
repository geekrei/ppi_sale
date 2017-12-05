# -*- coding: utf-8 -*-
{
    'name': "ppi_sale",

    'summary': """
       Philmetal Customizations
       """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Capstone Solutions Inc.",
    'website': "http://www.capstone.ph",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'custom',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_management', 'sale', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/sales_team_security.xml',
        'data/ir_sequence_data.xml',
        'views/ppi_sale_estimate_view.xml',
        'views/crm_lead_view.xml',
        'views/sale_order_view.xml',
        'views/product_view.xml',
        'views/mrp_view.xml',
        'report/report_ppi_sale_estimate.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}