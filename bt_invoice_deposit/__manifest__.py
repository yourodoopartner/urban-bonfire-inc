# -*- coding: utf-8 -*-
{
    'name': 'Invoice Deposit',
    'version': '13.0.1.0',
    'category': 'Accounting',
    'description': u"""
This module is for invoice deposit management.
""",
    'author': 'Urban Bonfire Inc.',
    'depends': [
        'account_payment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/collect_deposit_views.xml',
        'views/account_data.xml',
        'views/payment_deposit_view.xml',
        'views/account_views.xml',
        'views/account_portal_templates.xml',
    ],
    'application': False,
    'license': 'OPL-1',
}
