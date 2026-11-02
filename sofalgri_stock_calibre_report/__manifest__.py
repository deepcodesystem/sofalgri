# -*- coding: utf-8 -*-
{
    'name': 'Stock frigo : palettes par calibre',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': "Nombre de palettes en frigo par calibre et par conditionnement, pour les tableaux de bord",
    'description': """
        Vue de données (une ligne par calibre, une colonne par conditionnement) utilisée comme source
        d'un tableau de BI Dashboard : Carton 4 kg Gold Frutas, Sofina, Lidl, Générique, Caisse plastique 10 kg.
        Les palettes d'un autre conditionnement ou sans conditionnement sont comptées dans « Autres ».
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['stock', 'sofalgri_package_reports'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
