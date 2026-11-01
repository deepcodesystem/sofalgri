# -*- coding: utf-8 -*-
{
    'name': 'OF : conditionnement et frigo de stockage',
    'version': '18.0.1.3.0',
    'category': 'Manufacturing',
    'summary': "Conditionnement, quantité et frigo saisis sur l'OF (fabrication en 1 étape)",
    'description': """
        Remplace le transfert « Stocker les produits finis » : le conditionnement, sa quantité
        et le frigo de stockage sont saisis sur l'ordre de fabrication et reportés sur le
        mouvement du produit fini. À utiliser avec la fabrication en 1 étape de l'entrepôt.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['mrp'],
    'data': [
        'reports/production_pallet_report.xml',
        'views/mrp_production_views.xml',
        'views/mrp_bom_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
