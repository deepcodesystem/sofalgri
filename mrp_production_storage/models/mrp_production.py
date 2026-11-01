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
        compute='_compute_product_packaging_id',
        store=True,
        readonly=False,
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
    result_package_id = fields.Many2one(
        'stock.quant.package',
        string="N° de palette",
        domain="['|', ('quant_ids', '=', False), '&', ('name', '=like', 'S%'), ('location_id', '=', storage_location_id)]",
        copy=False,
        tracking=True,
        help="Palette de sortie du produit fini. Laisser vide pour créer automatiquement "
             "la palette suivante (S001, S002...) à l'impression de l'étiquette ou à la production. "
             "Palette mixte : choisir une palette S déjà présente dans le frigo de stockage.",
    )

    @api.depends('bom_id', 'product_id')
    def _compute_product_packaging_id(self):
        """ Nomenclature carton 4 kg ou plastique 10 kg -> conditionnement correspondant de l'article.
        Sans correspondance, on garde le choix de l'opérateur s'il concerne bien cet article. """
        for production in self:
            packaging = production.bom_id._get_product_packaging(production.product_id) if production.bom_id else False
            if packaging:
                production.product_packaging_id = packaging
            elif production.product_packaging_id.product_id != production.product_id:
                production.product_packaging_id = False
            else:
                production.product_packaging_id = production.product_packaging_id

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
            if production.result_package_id:
                moves.move_line_ids.filtered(lambda ml: ml.state != 'done').write({
                    'result_package_id': production.result_package_id.id,
                })
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
        if {'storage_location_id', 'product_packaging_id', 'result_package_id'} & set(vals):
            self._apply_storage_to_finished_moves()
        return res

    def _create_pallet_package(self):
        """ Palette de sortie numérotée par la séquence native des colis (S001, S002...),
        avec le type du conditionnement (« Palettes de Livraison »). """
        self.ensure_one()
        package_type = self.product_packaging_id.package_type_id or self.env['stock.package.type'].search(
            [('name', '=', 'Palettes de Livraison')], limit=1)
        return self.env['stock.quant.package'].create({'package_type_id': package_type.id})

    def action_print_pallet_label(self):
        self.ensure_one()
        if self.product_tracking in ('lot', 'serial') and not self.lot_producing_id:
            raise UserError(_("Indiquez le lot produit avant d'imprimer l'étiquette palette."))
        if not self.result_package_id and self.state not in ('done', 'cancel'):
            self.result_package_id = self._create_pallet_package()
        return self.env.ref('mrp_production_storage.action_report_production_pallet').report_action(self)

    def _get_pallet_label_data(self):
        """ Contenu de la palette pour l'étiquette : tous les OF non annulés de cette palette,
        une ligne par calibre, conditionnement et lot (palette mixte : plusieurs lignes). """
        self.ensure_one()
        productions = self
        if self.result_package_id:
            productions |= self.search([
                ('result_package_id', '=', self.result_package_id.id),
                ('state', '!=', 'cancel'),
            ])
        groups = {}
        for production in productions:
            product = production.product_id
            packaging = production.product_packaging_id
            lot = production.lot_producing_id
            line = groups.setdefault((product.id, packaging.id, lot.id), {
                # Champ de sofalgri_package_reports, affiché s'il existe
                'calibre': 'calibre' in product._fields and product.calibre or '',
                'product': product,
                'packaging': packaging,
                'lot_name': lot.name or '',
                'boxes': 0.0,
                'qty': 0.0,
            })
            line['boxes'] += production.product_packaging_qty
            line['qty'] += production.qty_producing or production.product_qty

        def sort_key(line):
            calibre = str(line['calibre'])
            return (int(calibre) if calibre.isdigit() else 999, calibre)
        lines = sorted(groups.values(), key=sort_key)
        lot_names = list(dict.fromkeys(line['lot_name'] for line in lines if line['lot_name']))
        return {
            'lines': lines,
            'mixed': len(lines) > 1,
            'lot_names': lot_names,
            'calibres': ' + '.join(dict.fromkeys(str(line['calibre']) for line in lines if line['calibre'])),
            'product_name': ', '.join(dict.fromkeys(line['product'].product_tmpl_id.name.strip() for line in lines)),
            'boxes': sum(line['boxes'] for line in lines),
            'qty': sum(line['qty'] for line in lines),
        }

    def _post_inventory(self, cancel_backorder=False):
        # Les lignes du produit fini existent à ce stade : on y reporte palette et frigo avant validation
        self._apply_storage_to_finished_moves()
        return super()._post_inventory(cancel_backorder=cancel_backorder)

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
            # Palette mixte : tous les calibres d'une palette sont au même endroit
            package_location = production.result_package_id.location_id
            if package_location and package_location != production.storage_location_id:
                raise UserError(_("%(of)s : la palette %(pallet)s se trouve dans %(location)s, "
                                  "pas dans le frigo de stockage %(storage)s.",
                                  of=production.name, pallet=production.result_package_id.name,
                                  location=package_location.display_name,
                                  storage=production.storage_location_id.display_name))
            if not production.result_package_id:
                production.result_package_id = production._create_pallet_package()
        self._apply_storage_to_finished_moves()
        return super().button_mark_done()
