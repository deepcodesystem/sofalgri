# -*- coding: utf-8 -*-
from markupsafe import Markup, escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpComponentLotWizard(models.TransientModel):
    _name = 'mrp.component.lot.wizard'
    _description = "Vérification des lots composants d'un OF"

    production_id = fields.Many2one('mrp.production', string="Ordre de fabrication", required=True, readonly=True)
    product_id = fields.Many2one(related='production_id.product_id', string="Produit fini")
    allowed_move_ids = fields.Many2many('stock.move', compute='_compute_allowed_move_ids')
    default_move_id = fields.Many2one('stock.move', compute='_compute_allowed_move_ids')
    line_ids = fields.One2many('mrp.component.lot.wizard.line', 'wizard_id', string="Palettes consommées")

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

    def action_validate(self):
        self.ensure_one()
        production = self.production_id
        moves = production._get_lot_tracked_raw_moves()

        for line in self.line_ids:
            if not line.lot_id:
                raise UserError(_("Indiquez le lot de chaque palette (%s).") % line.product_id.display_name)
            if line.quantity <= 0:
                raise UserError(_("La quantité doit être positive (lot %s).") % line.lot_id.name)
            if line.package_id and line.lot_id not in line.package_id.quant_ids.lot_id:
                raise UserError(_("Le lot %s n'est pas sur la palette %s.") % (line.lot_id.name, line.package_id.name))

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
                if changes:
                    line.move_line_id.write(changes)
            else:
                vals.update({
                    'move_id': line.move_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.move_id.product_uom.id,
                    'location_id': line.move_id.location_id.id,
                    'location_dest_id': line.move_id.location_dest_id.id,
                })
                self.env['stock.move.line'].create(vals)
        moves._recompute_state()

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
        return Markup("%s<ul>%s</ul>") % (escape(_("Lots des composants vérifiés :")), items)


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
        domain="[('quant_ids.product_id', '=', product_id), ('quant_ids.location_id', 'child_of', location_id), "
               "('quant_ids.quantity', '>', 0)]",
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string="Lot",
        domain="[('product_id', '=', product_id), ('quant_ids.location_id', 'child_of', location_id), "
               "('quant_ids.quantity', '>', 0)]",
    )
    quantity = fields.Float(string="Quantité", digits='Product Unit of Measure')

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
