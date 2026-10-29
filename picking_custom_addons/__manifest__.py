# -*- coding: utf-8 -*-
{
    'name': 'Picking Custom Addons',
    'version': '18.0.4.5.0',
    'category': 'Inventory',
    'summary': 'Module personalisé pour Sofalgri',
    'description': """
        Ce module ajoute les fonctionnalités manquantes dans le système pour le processus de Sofalgri
    """,
    'depends': ['stock', 'product'],
    'data': [
        'reports/report_actions.xml',
        'reports/package_report_templates.xml',
        'views/stock_move_line_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_package_views.xml',
        'views/stock_lot_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
