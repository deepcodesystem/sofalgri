# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpUnbuild(models.Model):
    _inherit = 'mrp.unbuild'

    package_id = fields.Many2one(
        'stock.quant.package',
        string="Palette",
        domain="[('quant_ids.product_id', '=', product_id), ('quant_ids.lot_id', '=?', lot_id), "
               "('quant_ids.quantity', '>', 0)]",
        compute='_compute_package_id',
        store=True,
        readonly=False,
        check_company=True,
        tracking=True,
        help="Palette d'où sort la quantité déconstruite. Remplie d'après l'OF ; le frigo suit la palette. "
             "Sur une palette mixte, seul le lot de l'OF est retiré.",
    )

    @api.depends('mo_id')
    def _compute_package_id(self):
        for order in self:
            # Déconstructions déjà faites : on ne réécrit pas l'historique à l'installation
            if order.mo_id and order.state != 'done':
                order.package_id = order.mo_id._get_unbuild_quants().package_id
            else:
                order.package_id = order.package_id

    @api.onchange('package_id')
    def _onchange_package_id(self):
        location = self._get_package_quants().location_id[:1]
        if location:
            self.location_id = location

    def _get_package_quants(self):
        self.ensure_one()
        if not self.package_id:
            return self.env['stock.quant']
        return self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', '=', self.lot_id.id),
            ('package_id', '=', self.package_id.id),
            ('location_id.usage', '=', 'internal'),
            ('quantity', '>', 0),
        ], order='quantity desc')

    def action_validate(self):
        self.ensure_one()
        if not self.package_id:
            return super().action_validate()
        # Le contrôle natif ne regarde que le stock hors colis : on contrôle la palette, sans stock négatif possible
        quants = self._get_package_quants()
        location = quants.location_id[:1]
        available_qty = sum(quants.filtered(lambda q: q.location_id == location).mapped('available_quantity'))
        unbuild_qty = self.product_uom_id._compute_quantity(self.product_qty, self.product_id.uom_id)
        if float_compare(available_qty, unbuild_qty, precision_rounding=self.product_id.uom_id.rounding) < 0:
            raise UserError(_(
                "La palette %(pallet)s n'a que %(available)s %(uom)s disponibles du lot %(lot)s "
                "(à déconstruire : %(qty)s %(uom)s).",
                pallet=self.package_id.name,
                available='%g' % available_qty,
                lot=self.lot_id.name or '-',
                qty='%g' % unbuild_qty,
                uom=self.product_id.uom_id.name,
            ))
        if self.location_id != location:
            self.location_id = location
        return self.action_unbuild()

    def _prepare_finished_move_line_vals(self, finished_move):
        vals = super()._prepare_finished_move_line_vals(finished_move)
        if self.package_id:
            vals['package_id'] = self.package_id.id
        return vals
