# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

# Au-delà de cet écart avec la nomenclature, le poids réel saisi est probablement le poids brut
# (constaté : 880 à 906 kg pour 880 prévus en poids net, environ 960 kg en poids brut)
WEIGHT_GAP_ALERT_PERCENT = 5.0


class MrpComponentLotWizard(models.TransientModel):
    _name = 'mrp.component.lot.wizard'
    _description = "Vérification des lots composants d'un OF"

    production_id = fields.Many2one('mrp.production', string="Ordre de fabrication", required=True, readonly=True)
    product_id = fields.Many2one(related='production_id.product_id', string="Produit fini")
    allowed_move_ids = fields.Many2many('stock.move', compute='_compute_allowed_move_ids')
    default_move_id = fields.Many2one('stock.move', compute='_compute_allowed_move_ids')
    line_ids = fields.One2many('mrp.component.lot.wizard.line', 'wizard_id', string="Palettes consommées")

    # Poids réel du vrac : saisie obligatoire quand l'OF n'a qu'un composant suivi par lot
    tracked_move_count = fields.Integer(compute='_compute_allowed_move_ids')
    expected_qty = fields.Float(
        string="Poids prévu (nomenclature)",
        compute='_compute_allowed_move_ids',
        digits='Product Unit of Measure',
    )
    actual_qty = fields.Float(
        string="Poids réel consommé",
        digits='Product Unit of Measure',
        help="Poids net réellement mis au calibrage. L'écart avec la nomenclature est reporté sur la dernière palette, dans la limite de son stock.",
    )
    weight_warning = fields.Char(compute='_compute_weight_warning')

    # Choix des lots d'un jour précis, hors FIFO
    lot_date = fields.Date(
        string="Date du lot",
        help="Propose les palettes des lots de cette date et limite les listes à ces lots. "
             "Vider la date garde les lignes et rouvre les listes, pour compléter avec une autre palette.",
    )
    allowed_package_ids = fields.Many2many('stock.quant.package', compute='_compute_allowed_stock')
    allowed_lot_ids = fields.Many2many('stock.lot', compute='_compute_allowed_stock')

    @api.model
    def default_get(self, fields_list):
        """ Une ligne par palette / lot réservé sur les composants suivis par lot. """
        res = super().default_get(fields_list)
        production = self.env['mrp.production'].browse(res.get('production_id'))
        if production and 'line_ids' in fields_list:
            res['line_ids'] = [
                fields.Command.create({
                    'move_id': ml.move_id.id,
                    'move_line_id': ml.id,
                    'package_id': ml.package_id.id,
                    'lot_id': ml.lot_id.id,
                    'quantity': ml.quantity,
                })
                for ml in production._get_lot_tracked_raw_moves().move_line_ids
            ]
        return res

    @api.depends('production_id')
    def _compute_allowed_move_ids(self):
        for wizard in self:
            moves = wizard.production_id._get_lot_tracked_raw_moves()
            wizard.allowed_move_ids = moves
            wizard.default_move_id = moves[:1]
            wizard.tracked_move_count = len(moves)
            wizard.expected_qty = sum(moves.mapped('product_uom_qty'))

    def _get_available_quants(self):
        """ Stock des composants suivis par lot, limité à la date choisie. Cette date est celle du nom
        du lot (…JJMMAAAA), imprimée sur l'étiquette : la date d'entrée peut différer (nuit, correction). """
        self.ensure_one()
        moves = self.production_id._get_lot_tracked_raw_moves()
        quants = self.env['stock.quant'].search([
            ('product_id', 'in', moves.product_id.ids),
            ('location_id', 'child_of', moves.location_id.ids),
            ('lot_id', '!=', False),
            ('quantity', '>', 0),
        ])
        if self.lot_date:
            suffix = self.lot_date.strftime('%d%m%Y')
            quants = quants.filtered(lambda q: q.lot_id.name.endswith(suffix))
        return quants

    @api.depends('production_id', 'lot_date')
    def _compute_allowed_stock(self):
        for wizard in self:
            quants = wizard._get_available_quants()
            wizard.allowed_package_ids = quants.package_id
            wizard.allowed_lot_ids = quants.lot_id

    @api.depends('actual_qty', 'expected_qty', 'tracked_move_count')
    def _compute_weight_warning(self):
        for wizard in self:
            wizard.weight_warning = False
            if wizard.tracked_move_count != 1 or not wizard.actual_qty or not wizard.expected_qty:
                continue
            gap = (wizard.actual_qty - wizard.expected_qty) / wizard.expected_qty * 100
            if abs(gap) > WEIGHT_GAP_ALERT_PERCENT:
                wizard.weight_warning = _(
                    "Poids réel de %(actual)s pour %(expected)s prévus (%(gap)s). "
                    "Vérifiez qu'il s'agit bien du poids NET, sans caisses ni palette.",
                    actual='%g' % wizard.actual_qty,
                    expected='%g' % wizard.expected_qty,
                    gap='%+.1f %%' % gap,
                )

    @api.onchange('actual_qty')
    def _onchange_actual_qty(self):
        """ L'écart entre le poids réel et le total des palettes est reporté sur la dernière palette,
        dans la limite de son stock (l'opérateur peut ensuite répartir autrement). """
        if self.tracked_move_count != 1 or not self.actual_qty or not self.line_ids:
            return
        # Lots choisis par date : on reprend les palettes pour couvrir le nouveau poids
        if self.lot_date:
            return self._onchange_lot_date()
        last_line = self.line_ids[-1]
        diff = self.actual_qty - sum(self.line_ids.mapped('quantity'))
        if diff > 0 and last_line.lot_id:
            room = max(last_line._get_stock_qty() - last_line._get_requested_qty(), 0.0)
            missing_qty = diff - room
            if float_compare(missing_qty, 0, precision_rounding=last_line.move_id.product_uom.rounding) > 0:
                last_line.quantity += room
                return {'warning': {
                    'title': _("Poids réel"),
                    'message': _("La palette %(package)s ne couvre pas tout : il manque %(qty)s. "
                                 "Ajoutez une autre palette.",
                                 package=last_line.package_id.name or _("hors palette"),
                                 qty='%g' % missing_qty),
                }}
        if last_line.quantity + diff > 0:
            last_line.quantity += diff

    def _prepare_lot_date_lines(self):
        """ Palettes des lots de la date choisie, les plus anciennes d'abord, jusqu'à couvrir chaque composant.
        Retourne les lignes à créer et la quantité restant à couvrir. """
        moves = self.production_id._get_lot_tracked_raw_moves()
        quants = self._get_available_quants()
        lines = []
        missing_qty = 0.0
        for move in moves:
            rounding = move.product_uom.rounding
            remaining = self.actual_qty if len(moves) == 1 and self.actual_qty else move.product_uom_qty
            move_quants = quants.filtered(lambda q: q.product_id == move.product_id)
            for quant in move_quants.sorted(lambda q: (q.in_date, q.package_id.name or '')):
                # Ce que cet OF réserve déjà sur ce stock sera libéré à la validation
                own_qty = sum(move.move_line_ids.filtered(
                    lambda ml: ml.lot_id == quant.lot_id
                    and ml.package_id == quant.package_id
                    and ml.location_id == quant.location_id
                ).mapped('quantity'))
                qty = min(quant.quantity - quant.reserved_quantity + own_qty, remaining)
                if float_compare(qty, 0, precision_rounding=rounding) <= 0:
                    continue
                lines.append(fields.Command.create({
                    'move_id': move._origin.id,
                    'package_id': quant.package_id.id,
                    'lot_id': quant.lot_id.id,
                    'quantity': qty,
                }))
                remaining -= qty
                if float_is_zero(remaining, precision_rounding=rounding):
                    break
            missing_qty += max(remaining, 0.0)
        return lines, missing_qty

    @api.onchange('lot_date')
    def _onchange_lot_date(self):
        """ Remplace les palettes proposées par le FIFO. Date vidée : les lignes restent. """
        if not self.lot_date:
            return
        date_label = self.lot_date.strftime('%d/%m/%Y')
        lines, missing_qty = self._prepare_lot_date_lines()
        if not lines:
            self.lot_date = False
            return {'warning': {
                'title': _("Date du lot"),
                'message': _("Aucune palette disponible pour les lots du %s.", date_label),
            }}
        self.line_ids = [fields.Command.clear()] + lines
        if missing_qty > 0:
            return {'warning': {
                'title': _("Date du lot"),
                'message': _("Les palettes du %(date)s ne couvrent pas tout : il manque %(qty)s. "
                             "Videz la date pour compléter avec une autre palette.",
                             date=date_label, qty='%g' % missing_qty),
            }}

    def action_validate(self):
        self.ensure_one()
        production = self.production_id
        moves = production._get_lot_tracked_raw_moves()

        if len(moves) == 1:
            rounding = moves.product_uom.rounding
            if float_is_zero(self.actual_qty, precision_rounding=rounding):
                raise UserError(_("Saisissez le poids réel de %s consommé (prévu : %s %s).",
                                  moves.product_id.display_name, '%g' % self.expected_qty, moves.product_uom.name))
            total = sum(self.line_ids.mapped('quantity'))
            if float_compare(total, self.actual_qty, precision_rounding=rounding) != 0:
                raise UserError(_("Le total des palettes (%(total)s) ne correspond pas au poids réel (%(actual)s) : "
                                  "ajustez la quantité des palettes.",
                                  total='%g' % total, actual='%g' % self.actual_qty))

        for line in self.line_ids:
            if not line.lot_id:
                raise UserError(_("Indiquez le lot de chaque palette (%s).") % line.product_id.display_name)
            if line.quantity <= 0:
                raise UserError(_("La quantité doit être positive (lot %s).") % line.lot_id.name)
            if line.package_id and line.lot_id not in line.package_id.quant_ids.lot_id:
                raise UserError(_("Le lot %s n'est pas sur la palette %s.") % (line.lot_id.name, line.package_id.name))
            requested_qty = line._get_requested_qty()
            stock_qty = line._get_stock_qty()
            if float_compare(requested_qty, stock_qty, precision_rounding=line.move_id.product_uom.rounding) > 0:
                raise UserError(_("La palette %(package)s (lot %(lot)s) contient %(stock)s pour %(requested)s demandés : "
                                  "ajoutez une autre palette, ou corrigez d'abord son stock si le poids est juste.",
                                  package=line.package_id.name or _("hors palette"),
                                  lot=line.lot_id.name,
                                  stock='%g' % stock_qty,
                                  requested='%g' % requested_qty))

        # Palettes retirées par l'opérateur : on libère leur réservation
        (moves.move_line_ids - self.line_ids.move_line_id).unlink()

        for line in self.line_ids:
            vals = {
                'lot_id': line.lot_id.id,
                'package_id': line.package_id.id,
                'quantity': line.quantity,
            }
            if line.move_line_id:
                changes = {
                    key: value for key, value in vals.items()
                    if (line.move_line_id[key].id if key != 'quantity' else line.move_line_id[key]) != value
                }
                # Lot ou palette changés : la ligne suit leur emplacement réel
                if {'lot_id', 'package_id'} & set(changes):
                    changes['location_id'] = line._get_source_location().id
                if changes:
                    line.move_line_id.write(changes)
            else:
                vals.update({
                    'move_id': line.move_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.move_id.product_uom.id,
                    'location_id': line._get_source_location().id,
                    'location_dest_id': line.move_id.location_dest_id.id,
                })
                self.env['stock.move.line'].create(vals)
        moves._recompute_state()
        # Quantités saisies = consommation réelle : Odoo ne doit plus les recalculer d'après la nomenclature
        moves.write({'picked': True, 'manual_consumption': True})

        production.component_lots_checked = True
        production.message_post(body=self._get_check_message())

        if self.env.context.get('continue_mark_done'):
            return production.with_context(continue_mark_done=False).button_mark_done()
        return {'type': 'ir.actions.act_window_close'}

    def _get_check_message(self):
        items = Markup().join(
            Markup("<li>%s : palette %s, lot <b>%s</b>, %s %s</li>") % (
                line.product_id.display_name,
                line.package_id.name or '-',
                line.lot_id.name,
                '%g' % line.quantity,
                line.move_id.product_uom.name,
            )
            for line in self.line_ids
        )
        weight = Markup()
        if self.tracked_move_count == 1 and self.actual_qty:
            weight = Markup("<p>%s</p>") % _("Poids réel consommé : %(actual)s (nomenclature : %(expected)s).",
                                             actual='%g' % self.actual_qty, expected='%g' % self.expected_qty)
            if self.weight_warning:
                weight += Markup("<p><b>%s</b></p>") % _("Écart inhabituel confirmé par l'opérateur.")
        if self.lot_date:
            weight += Markup("<p><b>%s</b></p>") % _("Lots du %s choisis par l'opérateur, hors FIFO.",
                                                     self.lot_date.strftime('%d/%m/%Y'))
        return Markup("%s<ul>%s</ul>%s") % (escape(_("Lots des composants vérifiés :")), items, weight)


class MrpComponentLotWizardLine(models.TransientModel):
    _name = 'mrp.component.lot.wizard.line'
    _description = "Palette consommée par un OF"

    wizard_id = fields.Many2one('mrp.component.lot.wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one(
        'stock.move',
        string="Composant",
        required=True,
        domain="[('id', 'in', parent.allowed_move_ids)]",
    )
    move_line_id = fields.Many2one('stock.move.line')
    product_id = fields.Many2one(related='move_id.product_id')
    location_id = fields.Many2one(related='move_id.location_id')
    package_id = fields.Many2one(
        'stock.quant.package',
        string="Palette",
        domain="[('quant_ids.product_id', '=', product_id), ('id', 'in', parent.allowed_package_ids)]",
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string="Lot",
        domain="[('product_id', '=', product_id), ('id', 'in', parent.allowed_lot_ids)]",
    )
    quantity = fields.Float(string="Quantité", digits='Product Unit of Measure')

    def _get_stock_quants(self):
        self.ensure_one()
        return self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', '=', self.lot_id.id),
            ('package_id', '=', self.package_id.id),
            ('location_id', 'child_of', self.location_id.id),
            ('quantity', '>', 0),
        ], order='quantity desc')

    def _get_stock_qty(self):
        """ Stock réel du lot sur la palette, réservations comprises. """
        return sum(self._get_stock_quants().mapped('quantity'))

    def _get_requested_qty(self):
        """ Quantité demandée sur ce lot et cette palette, toutes lignes du popup confondues. """
        self.ensure_one()
        return sum(self.wizard_id.line_ids.filtered(
            lambda line: line.lot_id == self.lot_id and line.package_id == self.package_id
        ).mapped('quantity'))

    def _get_source_location(self):
        """ Emplacement réel du lot et de la palette : l'OF prend dans ST/Stock, mais le stock est dans
        un sous-emplacement. Consommer sur ST/Stock y créerait un stock négatif. """
        self.ensure_one()
        quant = self._get_stock_quants()[:1]
        if not quant:
            raise UserError(_("Le lot %(lot)s n'a pas de stock %(where)s : choisissez la palette qui le contient.",
                              lot=self.lot_id.name,
                              where=self.package_id.name or _("hors palette")))
        return quant.location_id

    @api.onchange('package_id')
    def _onchange_package_id(self):
        """ Le choix de la palette remplit le lot (et la quantité si elle est vide). """
        quants = self.package_id.quant_ids.filtered(
            lambda q: q.product_id == self.product_id and q.quantity > 0
        )
        if len(quants.lot_id) == 1:
            self.lot_id = quants.lot_id
        if self.package_id and not self.quantity:
            self.quantity = sum(quants.mapped('quantity'))

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        """ Le choix du lot met à jour la palette : celle du lot s'il n'en a qu'une, sinon à choisir. """
        if not self.lot_id or self.lot_id in self.package_id.quant_ids.lot_id:
            return
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', '=', self.lot_id.id),
            ('location_id', 'child_of', self.location_id.id),
            ('quantity', '>', 0),
        ])
        on_one_package = len(quants.package_id) == 1 and all(quant.package_id for quant in quants)
        self.package_id = quants.package_id if on_one_package else False
