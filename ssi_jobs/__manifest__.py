# -*- coding: utf-8 -*-

#################################################################################
# Systems Services, Inc.
# Desc: To extend maintenance module to add fields to equipment
#################################################################################

{
    'name': 'Jobs',
    'summary': "Adds jobs module to Odoo.",
    'version': '1.0.1',
    'category': 'SSI',
    'author': 'Systems Services, Inc. '
              'Chad Thompson ',
    'website': 'https://ssibtr.com',
    "depends":  [
        'base',
        'account',
        'base',
        'mrp',
        'mrp_workorder',
        'quality',
        'quality_mrp',
        'product',
        'purchase',
        'sale',
        'sale_margin',
        'stock',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/add_default_job_stages.xml',
        'views/jobs.xml',
        'views/wo.xml',
        'views/ssi_mrp_production.xml',
        'views/ssi_account_invoice.xml',
        'views/ssi_sale_order.xml',
        'views/ssi_purchase_order.xml',
        'views/ssi_stock.xml',
        'views/ssi_crm.xml',
        'views/ssi_product.xml',
        'views/ssi_job_board.xml',
        'views/ssi_quality.xml',
        'report/ssi_job_cost_report.xml',
        'report/ssi_picking.xml',
        'report/ssi_report_templates.xml',
        # 'views/assets.xml',
        'data/schedule_action.xml',
    ],
    'installable': True,
    'application': True,
}
