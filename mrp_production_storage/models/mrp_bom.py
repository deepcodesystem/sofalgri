# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.tools import float_compare


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    packaging_unit_qty = fields.Float(
        string="Poids par colis",
        digits='Product Unit of Measure',
        help="Contenance du colis produit par cette nomenclature (ex. 4 pour les cartons de 4 kg, "
             "10 pour les caisses plastique de 10 kg). Sur l'OF, le conditionnement de l'article "
             "ayant cette contenance est sélectionné automatiquement.",
    )

    def _get_product_packaging(self, product):
        """ Conditionnement de l'article correspondant au poids par colis de la nomenclature. """
        self.ensure_one()
        if not self.packaging_unit_qty or not product:
            return self.env['product.packaging']
        return product.packaging_ids.filtered(
            lambda p: float_compare(p.qty, self.packaging_unit_qty, precision_digits=3) == 0
        ).sorted('sequence')[:1]
