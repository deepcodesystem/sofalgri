# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class StockLot(models.Model):
    _inherit = 'stock.lot'

    active = fields.Boolean(
        string="Actif",
        default=True,
        help="Décocher pour archiver le lot (le masquer sans le supprimer)."
    )

    def write(self, vals):
        # On n'archive pas un lot encore en stock chez nous ; un lot livré
        # garde ses quants chez le client (emplacement non interne) et reste archivable
        if 'active' in vals and not vals['active']:
            in_stock = self.filtered(lambda l: l.quant_ids.filtered(
                lambda q: q.location_id.usage in ('internal', 'transit') and q.quantity))
            if in_stock:
                names = in_stock.mapped('display_name')
                raise UserError(_(
                    "Impossible d'archiver %(count)s lot(s) encore en stock : %(names)s%(more)s",
                    count=len(names),
                    names=", ".join(names[:20]),
                    more=" …" if len(names) > 20 else "",
                ))
        return super().write(vals)
