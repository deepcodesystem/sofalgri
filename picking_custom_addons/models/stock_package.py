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
        # On n'archive que des colis vides, pour ne pas masquer du stock réel
        if 'active' in vals and not vals['active']:
            not_empty = self.filtered('quant_ids')
            if not_empty:
                raise UserError(_(
                    "Impossible d'archiver des colis qui contiennent encore du stock : %s",
                    ", ".join(not_empty.mapped('display_name'))
                ))
        return super().write(vals)