# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

class StockPackageType(models.Model):
    _inherit = 'stock.package.type'
    # Vous pouvez ajouter des infos par défaut ici si besoin plus tard
    pass

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    crate_quantity = fields.Float(
        string="Quantité de Caisses",
        help="Nombre total de caisses sur ce colis/cette palette."
    )
    tare = fields.Float(
        string="Tare",
        digits='Stock Weight',
        help="Somme des tares accumulées pour ce colis."
    )
    packaging_datetime = fields.Datetime(
        string="Date et Heure de Colisage",
        copy=False,  # On ne copie pas cette valeur si le colis est dupliqué
        help="Date et heure exactes de la dernière opération de colisage."
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
        help="Décocher pour archiver le colis (le masquer sans le supprimer)."
    )

    def write(self, vals):
        # On n'archive pas un colis encore en stock chez nous ; un colis livré
        # garde ses quants chez le client (emplacement non interne) et reste archivable
        if 'active' in vals and not vals['active']:
            in_stock = self.filtered(lambda p: p.quant_ids.filtered(
                lambda q: q.location_id.usage in ('internal', 'transit')))
            if in_stock:
                names = in_stock.mapped('display_name')
                raise UserError(_(
                    "Impossible d'archiver %(count)s colis encore en stock : %(names)s%(more)s",
                    count=len(names),
                    names=", ".join(names[:20]),
                    more=" …" if len(names) > 20 else "",
                ))
        return super().write(vals)