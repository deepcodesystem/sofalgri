# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    pallet_weight = fields.Float(
        string="Poids d'une palette (kg)",
        digits='Stock Weight',
        help="Poids d'une palette vide, ajouté au poids brut de la facture pour chaque palette.",
    )
