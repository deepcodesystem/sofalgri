# -*- coding: utf-8 -*-
{
    'name': 'Rapports : signature et cachet',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': "Image de la signature et du cachet de la société, imprimée sur les factures",
    'description': """
        L'image est chargée sur la fiche société (onglet « Rapports ») et imprimée en bas à droite
        de la facture client, de la facture transitaire et de la facture pro forma.
        Sans image, les documents restent inchangés.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['account', 'product_packaging_unit_price'],
    'data': [
        'reports/report_signature_templates.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
