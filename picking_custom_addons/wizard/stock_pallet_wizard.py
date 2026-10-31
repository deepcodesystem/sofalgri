# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPalletWizard(models.TransientModel):
    _name = 'stock.pallet.wizard'
    _description = 'Ajout d\'une palette pesée sur une réception'

    picking_id = fields.Many2one('stock.picking', string="Réception", required=True, readonly=True)
    picking_location_dest_id = fields.Many2one(related='picking_id.location_dest_id')
    allowed_product_ids = fields.Many2many('product.product', compute='_compute_allowed_product_ids')
    product_id = fields.Many2one(
        'product.product',
        string="Article",
        required=True,
        domain="[('id', 'in', allowed_product_ids)]",
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string="Emplacement de destination",
        required=True,
        domain="[('id', 'child_of', picking_location_dest_id)]",
    )

    result_package_id = fields.Many2one(
        'stock.quant.package',
        string="N° de palette",
        domain="[('quant_ids', '=', False)]",
        help="Colis de destination de la palette. Laisser vide pour créer automatiquement "
             "la palette suivante (E001, E002...).",
    )

    # --- Mêmes champs que sur la ligne de mouvement ---
    net_weight = fields.Float(string="Poids Brut", digits='Stock Weight', help="Poids brut total mesuré sur la balance.")
    crate_product_id = fields.Many2one(
        'product.product',
        string='Colis',
        domain="[('categ_id.name', '=', 'Colis')]",
    )
    crate_weight = fields.Float(string="Poids Caisse", related='crate_product_id.weight', digits='Stock Weight')
    crate_quantity = fields.Float(string="Quantité Colis")
    pallet_weight = fields.Float(string="Poids Palette", digits='Stock Weight', default=17.0)
    tare = fields.Float(string="Poids Tare", digits='Stock Weight', compute='_compute_weights')
    quantity = fields.Float(string="Poids Net", digits='Stock Weight', compute='_compute_weights')

    @api.model
    def default_get(self, fields_list):
        """ Pré-remplit l'article (s'il est seul) et reprend la caisse, la palette
        et l'emplacement de la dernière palette saisie sur la réception. """
        res = super().default_get(fields_list)
        picking = self.env['stock.picking'].browse(res.get('picking_id') or self.env.context.get('default_picking_id'))
        if not picking:
            return res

        products = picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')).product_id
        if len(products) == 1:
            res['product_id'] = products.id

        last_line = picking.move_line_ids.filtered(lambda l: l.net_weight > 0).sorted('id')[-1:]
        if last_line:
            res.update({
                'crate_product_id': last_line.crate_product_id.id,
                'pallet_weight': last_line.pallet_weight,
                'location_dest_id': last_line.location_dest_id.id,
            })
        else:
            res['location_dest_id'] = self._get_putaway_location(picking, products if len(products) == 1 else None).id
            crate = self.env['product.product'].search([('categ_id.name', '=', 'Colis')], limit=1)
            if crate:
                res['crate_product_id'] = crate.id
        return res

    @api.model
    def _get_putaway_location(self, picking, product, quantity=0):
        """ Emplacement donné par la stratégie de rangement à partir de la destination
        de la réception (ex. Avocats pour export : ST/Stock → Zone de réception). """
        location = picking.location_dest_id
        if not product:
            return location
        return location._get_putaway_strategy(product, quantity=quantity)

    @api.onchange('product_id')
    def _onchange_product_id_putaway(self):
        # Seulement si l'emplacement n'a pas été choisi (vide ou destination de la réception)
        if self.product_id and self.picking_id and self.location_dest_id in (
                self.env['stock.location'], self.picking_id.location_dest_id):
            self.location_dest_id = self._get_putaway_location(self.picking_id, self.product_id)

    @api.depends('picking_id')
    def _compute_allowed_product_ids(self):
        for wizard in self:
            wizard.allowed_product_ids = wizard.picking_id.move_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
            ).product_id

    @api.depends('net_weight', 'pallet_weight', 'crate_quantity', 'crate_weight')
    def _compute_weights(self):
        for wizard in self:
            wizard.tare = wizard.pallet_weight + (wizard.crate_quantity * wizard.crate_weight)
            wizard.quantity = max(wizard.net_weight - wizard.tare, 0.0)

    def _create_reception_package(self):
        """ Palette d'entrée numérotée E001, E002... avec le type « Palettes de réception »
        (le type choisit le modèle d'étiquette de sofalgri_package_reports). """
        package_type = self.env['stock.package.type'].search([('name', '=', 'Palettes de réception')], limit=1)
        return self.env['stock.quant.package'].create({
            'name': self.env['ir.sequence'].next_by_code('stock.quant.package.reception'),
            'package_type_id': package_type.id,
        })

    def action_add_and_print(self):
        """ Crée la ligne de la palette sur la réception puis imprime son étiquette.
        Le lot est attribué à l'impression (custom_lot_sequences). """
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError(_("Le poids brut doit être supérieur à la tare (%s).") % self.tare)

        move = self.picking_id.move_ids.filtered(
            lambda m: m.product_id == self.product_id and m.state not in ('done', 'cancel')
        )[:1]
        if not move:
            raise UserError(_("L'article %s n'est pas prévu sur cette réception.") % self.product_id.display_name)

        if not self.result_package_id:
            self.result_package_id = self._create_reception_package()

        # Emplacement laissé sur la destination de la réception : on applique la
        # stratégie de rangement, comme Odoo le fait pour une ligne créée à la validation
        location = self.location_dest_id
        if location == self.picking_id.location_dest_id:
            location = self._get_putaway_location(self.picking_id, self.product_id, self.quantity)

        vals = {
            'location_dest_id': location.id,
            'result_package_id': self.result_package_id.id,
            'quantity': self.quantity,
            'picked': True,
            'net_weight': self.net_weight,
            'crate_product_id': self.crate_product_id.id,
            'crate_quantity': self.crate_quantity,
            'pallet_weight': self.pallet_weight,
        }

        # Ligne réservée automatiquement par Odoo (pas encore pesée) : on la réutilise,
        # comme le faisait la saisie manuelle de la première palette
        line = move.move_line_ids.filtered(
            lambda l: not l.net_weight and not l.lot_name and not l.lot_id and not l.picked
        )[:1]
        if line:
            line.write(vals)
        else:
            vals.update({
                'move_id': move.id,
                'picking_id': self.picking_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': move.product_uom.id,
                'location_id': move.location_id.id,
            })
            line = self.env['stock.move.line'].create(vals)

        action = line.action_print_package_report()
        action['close_on_report_download'] = True
        return action
