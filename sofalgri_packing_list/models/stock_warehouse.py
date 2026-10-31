# -*- coding: utf-8 -*-
from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    packhouse_name = fields.Char(
        string="Station de conditionnement (Packhouse)",
        help="Colonne « Supplier Packhouse » de la liste de colisage (ex. ELAKHALPORT).",
    )
    grower_code = fields.Char(
        string="Code producteur (Grower Code)",
        help="Colonne « Grower Code » de la liste de colisage (ex. SOFALGRI).",
    )
