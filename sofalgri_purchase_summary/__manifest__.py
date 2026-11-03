# -*- coding: utf-8 -*-
{
    'name': "Achats d'avocats",
    'version': '18.0.1.2.0',
    'category': 'Inventory/Purchase',
    'summary': "Écran de suivi des achats d'avocats : quantités commandées et reçues, montants et paiements",
    'description': """
        Une ligne par commande d'achat de matière première : quantités commandée et reçue, variation,
        quantités calibrée et non calibrée d'après les lots de la commande, montant des avocats (facturé, à défaut commandé), frais, total à payer, payé, reste et statut de paiement.
        Filtres sur la saison et les dates, totaux par fournisseur.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'purchase_stock',
        'account',
        'purchase_advance_payment',
        'sofalgri_export_summary',
        'synconics_bi_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_summary_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
