# -*- coding: utf-8 -*-
from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _visible_menu_ids(self, debug=False):
        # Le tableau de bord et les rapports du menu Facturation affichent des totaux :
        # le groupe a son propre menu. Nouvel ensemble : celui du parent est en cache.
        visible = super()._visible_menu_ids(debug)
        if self.env.user.has_group('sofalgri_own_invoices.group_own_invoices'):
            menu = self.env.ref('account.menu_finance', raise_if_not_found=False)
            if menu:
                visible = visible - {menu.id}
        return visible
