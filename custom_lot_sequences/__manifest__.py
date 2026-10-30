# -*- coding: utf-8 -*-
{
    'name': 'Custom Lot Sequences',
    'version': '18.0.2.3.0',
    'summary': 'Generate custom lot numbers for receipts and manufacturing orders.',
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'license': 'LGPL-3',
    'depends': ['stock', 'mrp', 'picking_custom_addons'],
    'data': [
        'data/ir_sequence_data.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
}