# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Image stockée en pièce jointe : pas de colonne ajoutée sur res_company
    report_signature_image = fields.Image(
        string="Signature et cachet",
        max_width=1024,
        max_height=1024,
        help="Image imprimée en bas à droite des factures (PNG à fond transparent de préférence).",
    )
