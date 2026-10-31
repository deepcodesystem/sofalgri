# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    cultivation_mode = fields.Selection(
        [('conventional', 'CONVENTIONAL'), ('organic', 'ORGANIC')],
        string="Mode de culture",
        default='conventional',
        help="Colonne « Organic / Conventional » de la liste de colisage.",
    )
