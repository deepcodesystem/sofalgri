# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render(self, report_ref, res_ids, data=None):
        # Pro forma : contrôle AVANT le rendu, pour afficher un simple avertissement
        # (une erreur levée pendant le rendu QWeb s'affiche comme une erreur serveur)
        report = self._get_report(report_ref)
        if report.report_name == 'product_packaging_unit_price.report_proforma_invoice':
            missing = self.env['sale.order'].browse(res_ids).filtered(lambda o: not o.proforma_unit_price)
            if missing:
                raise UserError(_("Renseignez le « Prix unitaire pro forma » avant d'imprimer la facture pro forma : %s",
                                  ', '.join(missing.mapped('name'))))
        return super()._render(report_ref, res_ids, data=data)
