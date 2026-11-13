# -*- coding: utf-8 -*-
{
    'name': "Caisse de l'opérateur",
    'version': '18.0.1.1.0',
    'category': 'Accounting/Accounting',
    'summary': "Espèces remises à l'opérateur des achats, dépensées et restant à justifier",
    'description': """
        Écran par période (par défaut depuis le début de la saison) : espèces remises à l'opérateur
        (remises d'espèces validées), encaissements en espèces des clients (ventes locales), paiements en
        espèces répartis entre avocats, frais et autres achats d'après les factures payées, paiements pas
        encore rapprochés d'une facture, et reste en espèces chez l'opérateur.
        Les versements d'espèces en banque (sofalgri_cash_transfer) sont déduits des encaissements clients.
        Détail ligne à ligne, en liste et en tableau croisé.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'account',
        'purchase',
        'account_cash_deposit',
        'purchase_advance_payment',
        'sofalgri_export_summary',
        'sofalgri_purchase_summary',
        'sofalgri_cash_transfer',
        'synconics_bi_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/operator_cash_report_views.xml',
        'views/operator_cash_statement_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
