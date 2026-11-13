# -*- coding: utf-8 -*-
{
    'name': "Versements d'espèces en banque",
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': "Verser les espèces d'une caisse sur un compte bancaire (écriture caisse → banque)",
    'description': """
        Versement d'espèces : date, caisse (par défaut Cash), compte bancaire (journaux cochés
        « Reçoit les versements d'espèces »), montant, référence. À la validation, écriture dans le
        journal de banque : débit du compte de la banque, crédit du compte de la caisse.
        Menu « Mes factures > Versements d'espèces » pour le groupe « Mes factures uniquement »
        (chacun ne voit que ses versements), et « Facturation > Comptabilité > Versements d'espèces »
        pour les comptables.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'account',
        'mail',
        'sofalgri_own_invoices',
    ],
    'data': [
        'security/cash_transfer_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_journal_views.xml',
        'views/cash_transfer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
