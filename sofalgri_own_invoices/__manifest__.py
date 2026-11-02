# -*- coding: utf-8 -*-
{
    'name': 'Facturation : mes factures uniquement',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': "Groupe d'utilisateurs : créer, valider et payer ses propres factures, sans voir les autres",
    'description': """
        Le groupe « Mes factures uniquement » hérite des droits de facturation, limités par des règles
        globales aux factures et aux paiements créés par l'utilisateur. Il remplace le menu Facturation
        (tableau de bord et rapports) par un menu « Mes factures ».
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['account'],
    'data': [
        'security/own_invoices_security.xml',
        'views/own_invoices_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
