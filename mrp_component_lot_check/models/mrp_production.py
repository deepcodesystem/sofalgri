# -*- coding: utf-8 -*-
from odoo import models, fields, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    component_lots_checked = fields.Boolean(
        string="Lots composants vérifiés",
        copy=False,
        help="Les palettes et lots des composants suivis par lot ont été vérifiés par l'opérateur.",
    )

    def _get_lot_tracked_raw_moves(self):
        return self.move_raw_ids.filtered(
            lambda m: m.has_tracking == 'lot' and m.state not in ('done', 'cancel')
        )

    def action_open_component_lot_wizard(self):
        self.ensure_one()
        return {
            'name': _("Vérifier les lots des composants"),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.component.lot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, default_production_id=self.id),
        }

    def action_confirm_check_lots(self):
        """ Bouton « Confirmer » : confirme (et réserve) puis affiche les lots retenus. """
        res = self.action_confirm()
        if len(self) == 1 and self._get_lot_tracked_raw_moves():
            return self.action_open_component_lot_wizard()
        return res

    def button_mark_done(self):
        # Traçabilité : pas de production sans vérification des lots composants
        if (
            len(self) == 1
            and not self.env.context.get('skip_component_lot_check')
            and not self.component_lots_checked
            and self._get_lot_tracked_raw_moves()
        ):
            return self.with_context(continue_mark_done=True).action_open_component_lot_wizard()
        return super().button_mark_done()
