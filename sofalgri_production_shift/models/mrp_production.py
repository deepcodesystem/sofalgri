# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_start_production_shift(self):
        # Bouton de la liste des OF, utilisable sans sélection
        return self.env['sofalgri.production.shift'].action_start_shift()

    def action_end_production_shift(self):
        return self.env['sofalgri.production.shift'].action_end_open_shift()

    def button_mark_done(self):
        # Pas de production hors shift : le rapport du shift doit couvrir toutes les palettes
        if not self.env.context.get('skip_production_shift_check'):
            Shift = self.env['sofalgri.production.shift'].sudo()
            for company in self.company_id or self.env.company:
                if not Shift._get_open_shift(company):
                    raise UserError(_("Aucun shift en cours : cliquez sur « Démarrer le shift » "
                                      "dans la liste des ordres de fabrication avant de produire."))
        return super().button_mark_done()
