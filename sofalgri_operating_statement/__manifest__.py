# -*- coding: utf-8 -*-
{
    'name': "Compte d'exploitation",
    'version': '18.0.1.1.0',
    'category': 'Accounting/Accounting',
    'summary': "Compte d'exploitation par période : ventes, achats d'avocats, frais, emballages, variation de stock, marge et coût de revient au kg",
    'description': """
        Écran « Compte d'exploitation » (BI Dashboard) pour une période choisie (par défaut la saison en cours) :
        ventes export, locales et de déchets, achat d'avocats, récolte et chargement, transport ferme, emballages consommés par les OF,
        station, transitaire, transport international, autres frais, variation du stock d'avocats ; marge, coût de revient et prix au kg.
        Chaque article de frais ou de déchets est classé par le champ « Rubrique du compte d'exploitation » de sa fiche.
        Détail ligne à ligne en tableau croisé (source des graphiques du tableau de bord).
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'account',
        'purchase_stock',
        'stock_account',
        'sofalgri_export_summary',
        'synconics_bi_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/operating_report_views.xml',
        'data/export_tariff_data.xml',
        'views/operating_statement_views.xml',
        'views/export_tariff_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
