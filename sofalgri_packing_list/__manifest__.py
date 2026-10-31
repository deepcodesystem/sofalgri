# -*- coding: utf-8 -*-
{
    'name': 'Liste de colisage (packing list)',
    'version': '18.0.1.0.1',
    'category': 'Inventory/Delivery',
    'summary': "Liste de colisage export depuis le bon de livraison (Excel et PDF)",
    'description': """
        Liste de colisage sur le modèle client : une ligne par palette et par calibre
        (variété, conditionnement, poids du colis, calibre, classe, origine, nb de colis,
        n° de palette, GGN, date de conditionnement), avec les informations d'expédition
        (navire, conteneur, ETD, ETA, port de destination...) saisies sur la livraison.
        Export Excel (.xlsx) et rapport PDF.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['stock', 'sale_stock', 'account', 'delivery_carrier_custom', 'sofalgri_package_reports'],
    'data': [
        'reports/packing_list_report.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
