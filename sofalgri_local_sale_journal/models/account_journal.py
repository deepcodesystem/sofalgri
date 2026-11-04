# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_local_sale = fields.Boolean(
        string="Journal des ventes locales",
        copy=False,
        help="Reçoit les factures sans position fiscale d'export. Tant qu'aucun journal n'est coché, "
             "le choix automatique et le contrôle à la validation sont inactifs.",
    )

    @api.constrains('is_local_sale', 'type', 'company_id')
    def _check_is_local_sale(self):
        for journal in self.filtered('is_local_sale'):
            if journal.type != 'sale':
                raise ValidationError(_("Le journal des ventes locales doit être un journal de vente."))
            if self.search_count([
                ('id', '!=', journal.id),
                ('is_local_sale', '=', True),
                ('company_id', '=', journal.company_id.id),
            ]):
                raise ValidationError(_("Un seul journal des ventes locales est possible par société."))

    @api.model
    def _get_sale_journal_for_position(self, company, fiscal_position):
        """Journal de vente attendu ; vide si aucun journal local n'est coché (module inactif)."""
        Journal = self.sudo()
        domain = [*self._check_company_domain(company), ('type', '=', 'sale')]
        local_journal = Journal.search([*domain, ('is_local_sale', '=', True)], limit=1)
        if not local_journal:
            return self.browse()
        if fiscal_position._is_export_position():
            return Journal.search([*domain, ('is_local_sale', '=', False)], limit=1).sudo(False)
        return local_journal.sudo(False)
