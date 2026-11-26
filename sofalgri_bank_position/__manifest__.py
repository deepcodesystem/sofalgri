# -*- coding: utf-8 -*-
{
    'name': "Situation du compte bancaire",
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': "Entrées et sorties d'un compte bancaire (ex. CDM ADIL) par période",
    'description': """
        Écran par période et par compte bancaire (par défaut le journal coché « Reçoit les versements
        d'espèces », depuis le début de la saison) : solde au début, entrées (encaissements des clients,
        surtout ventes locales ; versements d'espèces de la caisse), sorties (paiements de factures
        d'achat ; remises d'espèces vers la caisse), autres écritures du compte, solde à la fin.
        Détail ligne à ligne, en liste et en tableau croisé.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'account',
        'account_cash_deposit',
        'sofalgri_cash_transfer',
        'sofalgri_export_summary',
        'sofalgri_operating_statement',
        'synconics_bi_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/bank_position_report_views.xml',
        'views/bank_position_statement_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
