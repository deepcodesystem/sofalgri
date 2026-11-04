# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        # Un journal choisi sur la commande est conservé ; le contrôle à la validation reste actif.
        if not self.journal_id:
            fiscal_position = self.env['account.fiscal.position'].browse(values.get('fiscal_position_id') or [])
            journal = self.env['account.journal']._get_sale_journal_for_position(self.company_id, fiscal_position)
            if journal:
                values['journal_id'] = journal.id
        return values
