# -*- coding: utf-8 -*-
{
    'name': 'Vérification des lots composants des OF',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Popup de vérification des palettes et lots consommés par un ordre de fabrication',
    'description': """
        Traçabilité du calibrage : à la confirmation d'un OF, affiche les palettes et lots
        réservés pour les composants suivis par lot et permet de les corriger.
        « Produire » rouvre le popup tant que les lots n'ont pas été validés.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mrp_component_lot_wizard_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
