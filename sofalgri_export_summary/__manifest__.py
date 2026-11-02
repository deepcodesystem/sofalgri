# -*- coding: utf-8 -*-
{
    'name': 'Synthèse des exports',
    'version': '18.0.1.0.1',
    'category': 'Sales/Sales',
    'summary': "Écran de suivi des exports : une ligne par facture client, avec filtre sur la saison et les dates",
    'description': """
        Liste des factures clients validées : station, poids net, GPS, camion, client, chargement, transporteur,
        matricule, statut, arrivée, prix, claim (avoirs), cours et paiements (trois au plus).
        GPS, TY, statut et date d'arrivée sont saisis sur la livraison, onglet « Expédition ».
        Le début de saison est saisi sur la fiche société.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'account',
        'sale_stock',
        'delivery_carrier_custom',
        'delivery_carrier_partner',
        'product_packaging_unit_price',
        'sofalgri_packing_list',
        'synconics_bi_dashboard',
    ],
    'data': [
        'views/res_company_views.xml',
        'views/stock_picking_views.xml',
        'views/export_summary_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
