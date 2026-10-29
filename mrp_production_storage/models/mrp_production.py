# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_packaging_id = fields.Many2one(
        'product.packaging',
        string="Conditionnement",
        domain="[('product_id', '=', product_id)]",
        check_company=True,
        copy=False,
        tracking=True,
    )
    product_packaging_qty = fields.Float(
        string="Quantité de conditionnement",
        compute='_compute_product_packaging_qty',
        store=True,
        readonly=False,
        copy=False,
        tracking=True,
        help="Nombre de conditionnements produits (ex. cartons). "
             "Modifier ce nombre ajuste la quantité à produire.",
    )
    storage_parent_location_id = fields.Many2one(related='warehouse_id.lot_stock_id')
    storage_location_id = fields.Many2one(
        'stock.location',
        string="Frigo de stockage",
        domain="[('usage', '=', 'internal'), ('id', 'child_of', storage_parent_location_id)]",
        check_company=True,
        copy=False,
        tracking=True,
    )

    @api.depends('product_packaging_id', 'product_qty', 'product_uom_id')
    def _compute_product_packaging_qty(self):
        for production in self:
            packaging = production.product_packaging_id
            if not packaging or not packaging.qty:
                production.product_packaging_qty = 0.0
                continue
            qty = production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id)
            production.product_packaging_qty = float_round(qty / packaging.qty, precision_rounding=1.0)

    @api.onchange('product_packaging_qty')
    def _onchange_product_packaging_qty(self):
        """ Nombre de cartons réellement produits -> quantité produite (ex. 218 x 4 kg). """
        packaging = self.product_packaging_id
        if not packaging or not self.product_packaging_qty or self.state in ('draft', 'done', 'cancel'):
            return
        qty = self.product_id.uom_id._compute_quantity(self.product_packaging_qty * packaging.qty, self.product_uom_id)
        self.qty_producing = qty

    @api.onchange('storage_location_id')
    def _onchange_storage_location_id(self):
        if self.storage_location_id and self.state == 'draft':
            self.location_dest_id = self.storage_location_id

    def _get_storage_finished_moves(self):
        return self.move_finished_ids.filtered(
            lambda m: m.product_id == self.product_id and m.state not in ('done', 'cancel')
        )

    def _apply_storage_to_finished_moves(self):
        """ Reporte le frigo et le conditionnement sur le mouvement du produit fini,
        comme le faisait le transfert « Stocker les produits finis ». """
        for production in self.filtered(lambda p: p.state not in ('done', 'cancel')):
            moves = production._get_storage_finished_moves()
            vals = {}
            if production.storage_location_id:
                vals['location_dest_id'] = production.storage_location_id.id
                if production.state == 'draft' and production.location_dest_id != production.storage_location_id:
                    production.location_dest_id = production.storage_location_id
            if production.product_packaging_id:
                vals['product_packaging_id'] = production.product_packaging_id.id
            # Fabrication encore en plusieurs étapes : le transfert de stockage suit, on ne détourne pas le produit
            chained_moves = moves.filtered('move_dest_ids')
            if chained_moves:
                chained_moves.write({k: v for k, v in vals.items() if k != 'location_dest_id'})
                moves -= chained_moves
            if vals:
                moves.write(vals)
            if production.storage_location_id:
                moves.move_line_ids.filtered(lambda ml: ml.state != 'done').write({
                    'location_dest_id': production.storage_location_id.id,
                })

    @api.model_create_multi
    def create(self, vals_list):
        productions = super().create(vals_list)
        productions._apply_storage_to_finished_moves()
        return productions

    def write(self, vals):
        res = super().write(vals)
        if {'storage_location_id', 'product_packaging_id'} & set(vals):
            self._apply_storage_to_finished_moves()
        return res

    def button_mark_done(self):
        # Les produits conditionnés (avocats calibrés) doivent avoir leur conditionnement et leur frigo
        for production in self.filtered(lambda p: p.product_id.packaging_ids):
            missing = []
            if not production.product_packaging_id:
                missing.append(_("le conditionnement"))
            if not production.storage_location_id:
                missing.append(_("le frigo de stockage"))
            if missing:
                raise UserError(_("%(of)s : indiquez %(fields)s avant de produire.",
                                  of=production.name, fields=_(" et ").join(missing)))
        self._apply_storage_to_finished_moves()
        return super().button_mark_done()
