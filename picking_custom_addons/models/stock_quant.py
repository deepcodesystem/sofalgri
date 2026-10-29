# -*- coding: utf-8 -*-
from odoo import models, fields

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    crate_quantity = fields.Float(
        string="Quantité de Caisses",
        related='package_id.crate_quantity',
        store=True, # store=True est essentiel pour pouvoir grouper et filtrer
        readonly=True
    )
    tare = fields.Float(
        string="Tare",
        digits='Stock Weight',
        help="Somme des tares accumulées pour ce colis."
    )

    def _get_removal_strategy_order(self, removal_strategy):
        # FIFO : les palettes d'une même réception ont la même date d'entrée ;
        # on les départage par n° de palette (E001 avant E002) plutôt que par id du quant,
        # attribué dans l'ordre inverse des palettes à la validation
        if removal_strategy == 'fifo':
            return 'in_date ASC, package_id ASC, id'
        return super()._get_removal_strategy_order(removal_strategy)