# -*- coding: utf-8 -*-
{
    'name': "Ventes locales et paiements",
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': "Factures de ventes locales avec les montants payés en espèces et par virement",
    'description': """
        Écran « BI Dashboard > Ventes > Ventes locales et paiements » : une ligne par facture ou avoir
        du journal des ventes locales (client, kg, montant, payé en espèces, payé par virement, autre
        règlement, reste à payer), plus une ligne par encaissement d'un client local pas encore
        rapproché d'une facture. Filtres saison, dates, client ; totaux ; tableau croisé client × mois.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'account',
        'sofalgri_local_sale_journal',
        'sofalgri_export_summary',
        'synconics_bi_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/local_sale_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
