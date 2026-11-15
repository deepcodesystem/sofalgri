# -*- coding: utf-8 -*-
{
    'name': "Shifts de production",
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': "Démarrer et terminer le shift depuis la liste des OF, rapport des palettes produites envoyé par email",
    'description': """
        Un seul shift ouvert à la fois pour la station.
        Boutons « Démarrer le shift » et « Terminer le shift » en haut de la liste des ordres de fabrication.
        « Produire » est refusé tant qu'aucun shift n'est ouvert.
        À la fin du shift : rapport des palettes produites (tous les OF terminés pendant le shift),
        envoyé par email aux destinataires choisis dans la configuration de la Fabrication,
        avec le rapport PDF en pièce jointe.
    """,
    'author': 'GetapPRO',
    'website': 'https://www.getap.pro',
    'depends': [
        'mrp',
        'mail',
        'mrp_production_storage',
        'mrp_component_lot_check',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'reports/production_shift_report.xml',
        'views/production_shift_views.xml',
        'views/mrp_production_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
