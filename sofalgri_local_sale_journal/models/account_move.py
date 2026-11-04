# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id', 'fiscal_position_id')
    def _onchange_local_sale_journal(self):
        """Facture créée à la main : journal selon la position, tant qu'elle n'a jamais été validée."""
        if not self.partner_id or self.state != 'draft' or self.posted_before or not self.is_sale_document():
            return
        journal = self.env['account.journal']._get_sale_journal_for_position(
            self.company_id, self.fiscal_position_id)
        if journal and journal != self.journal_id:
            self.journal_id = journal

    def _check_local_sale_journal(self):
        Journal = self.env['account.journal']
        for move in self.filtered(lambda m: m.is_sale_document()):
            if not Journal._get_sale_journal_for_position(move.company_id, move.fiscal_position_id):
                continue
            is_export = move.fiscal_position_id._is_export_position()
            client = move.partner_id.display_name
            if move.journal_id.is_local_sale:
                if is_export:
                    raise UserError(_(
                        "Facture de %(client)s : la position fiscale %(position)s est une position d'export, "
                        "la facture ne peut pas aller dans le journal %(journal)s.",
                        client=client, position=move.fiscal_position_id.display_name,
                        journal=move.journal_id.display_name,
                    ))
                if move.currency_id != move.company_id.currency_id:
                    raise UserError(_(
                        "Facture de %(client)s en %(currency)s : une vente locale doit être en %(company_currency)s. "
                        "S'il s'agit d'un export, renseignez la position fiscale d'export.",
                        client=client, currency=move.currency_id.name,
                        company_currency=move.company_id.currency_id.name,
                    ))
            elif not is_export:
                raise UserError(_(
                    "Facture de %(client)s sans position fiscale d'export : elle ne peut pas aller dans le "
                    "journal %(journal)s. Pour un export, renseignez la position fiscale ; pour une vente "
                    "locale, choisissez le journal des ventes locales.",
                    client=client, journal=move.journal_id.display_name,
                ))

    def _post(self, soft=True):
        # Avant l'appel natif : aucun numéro n'est attribué à une facture refusée.
        self._check_local_sale_journal()
        return super()._post(soft=soft)
