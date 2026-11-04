# -*- coding: utf-8 -*-
{
    'name': 'Ventes : journal des ventes locales',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': "Choisit le journal de vente selon la position fiscale et refuse une facture dans le mauvais journal",
    'description': """
        Une facture avec une position fiscale d'export va dans le journal d'export, les autres dans le
        journal coché « Journal des ventes locales ». La validation est refusée en cas d'incohérence,
        avant l'attribution du numéro. Sans journal coché, le module n'a aucun effet.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': ['account', 'sale'],
    'data': [
        'views/account_journal_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
