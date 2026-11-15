# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError

SHIFT_BUTTONS = ('action_start_production_shift', 'action_end_production_shift')


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _has_open_production_shift(self):
        return bool(self.env['sofalgri.production.shift'].sudo()._get_open_shift())

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        # La liste diffère selon qu'un shift est en cours : une version en cache pour chaque cas
        key = super()._get_view_cache_key(view_id, view_type, **options)
        if view_type == 'list':
            key += (self._has_open_production_shift(),)
        return key

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """ Liste des OF : « Démarrer le shift » seul sans shift en cours, « Terminer le shift » seul sinon. """
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'list':
            hidden = SHIFT_BUTTONS[0] if self._has_open_production_shift() else SHIFT_BUTTONS[1]
            for node in arch.xpath("//header/button[@name='%s']" % hidden):
                node.getparent().remove(node)
        return arch, view

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
