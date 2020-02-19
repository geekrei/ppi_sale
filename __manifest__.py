# -*- coding: utf-8 -*-
{
    'name': "innosen_custom",

    'summary': """
       Innosen Customizations
       """,

    'description': """
        Customizations
            - List products in all subcategories
            - Tag Multiple Partners
            - Custom Reports
                - Invoice
                - Shipping Invoice
                - Pro Forma Invoice
                - Delivery Slip
                - Picking Operations
                - Purchase Order
                - Purchase Quotation
                - Sale/Purchase Journal (Excel Format)
                - Picking Lot/Serial Barcode
                - Production Lot/Serial Barcode 
            - Quotation Pay
            - Repair Order
            - Sencon Payment Via
            - Link Invoice to Purchase and Sale
            - Dev Utility: Reset Manufacturing Order
            - Dev Utility: Update Moves with Status Waiting (For Another Move) in Manufacturing Order
            - Populate REFERENCE field of account.nove if generated from MO
            - Generate repair order on sale confirmation for services with tracking: Create Repair Order
            - Unique Serial Number: Add exemption to migrated serial numbers
            - Picking: Allow location change to all states except DONE and CANCELLED; Functionality to update move locations
            - Adds custom filter to calendar view in Leaves
            - Hide buttons in product views
            - Journal Entry Recompute Partner
            - Calendar Invitation Force Send
            - Holidays, Leaves and Timesheet Integration
            - View Access to Customer and Vendor Payments by Billing
            - Timesheet Validation
    """,

    'author': "OmniTechnical Global Solutions, Inc.",
    'website': "www.omnitechnical.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'custom',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 'base_vat', 'contacts',
        'product', 'mail',
        'account', 'account_analytic_default', 'account_asset', 'account_reports',
        'mrp', 'mrp_repair', 'mrp_plm',
        'stock', 'stock_picking_wave', 'stock_account', 'stock_landed_costs', 'report_intrastat', 'delivery', 'stock_barcode',
        'currency_rate_live', 
        'purchase', 'purchase_requisition',
        'sale_order_dates', 'sale_timesheet', 
        'sale_rental',
        'project',
        'hr_holidays', 'hr_public_holidays', 'hr_payroll', 'hr_expense',
        'product_datasheet',
        'inter_company_rules'],

    # always loaded
    'data': [
        'security/innosen_security.xml',
        'security/ir.model.access.csv',
        'data/report_paperformat_data.xml',
        'data/mail_templates.xml',
        'data/remove_action_bindings_data.xml',
        'data/cron_invoice_due.xml',
        'views/layout_templates.xml',
        'views/ir_attachment_views.xml',
        'views/ir_actions_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/mail_view.xml',
        'views/account_type.xml',
        'views/product_view.xml',
        'views/account_payment_views.xml',
        'views/account_invoice_view.xml',
        'views/account_config_setting_view.xml',
        'views/currency_rate_live_views.xml',
        'views/account_move_views.xml',
        'views/mrp_repair_view.xml',
        'views/mrp_plm_views.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
        'views/mrp_workorder_views.xml',
        'views/mrp_production_views.xml',
        'views/stock_production_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_account_views.xml',
        'views/stock_pack_operation_views.xml',
        'views/stock_landed_costs_view.xml',
        'views/hr_holidays_views.xml',
        'views/sale_rental_views.xml',
        'views/hr_timesheet_views.xml',
        'views/hr_payslip_views.xml',
        'report/report_invoice.xml',
        'report/report_invoice_shipping_ph.xml',
        'report/report_invoice_proforma.xml',
        'report/report_invoice_proforma_shipping.xml',
        'report/report_deliveryslip.xml',
        'report/report_stockpicking_operations.xml',
        'report/report_stockpicking_barcodes.xml',
        'report/report_saleorder.xml',
        'report/report_purchaseorder.xml',
        'report/report_purchasequotation.xml',
        'report/report_intrastat_report_view.xml',
        'report/report_payslip.xml',
        'report/report_payslip_details.xml',
        'report/report_production_barcodes.xml',
        'report/report.xml',
        'wizard/tag_multiple_partners_view.xml',
        'wizard/link_invcoice_purchase_view.xml',
        'wizard/link_invcoice_sale_view.xml',
        'wizard/quoatation_pay_view.xml',
        'wizard/account_report_print_journal_view.xml',
        'wizard/partner_pricelist_update_view.xml',
        # 'wizard/link_stock_sale_view.xml',
    ],
    'qweb': [
        'static/src/xml/stock_barcode.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}