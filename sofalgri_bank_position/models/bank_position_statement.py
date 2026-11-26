from odoo import api, fields, models


class BankPositionStatement(models.TransientModel):
    _name = 'sofalgri.bank.position.statement'
    _description = "Situation du compte bancaire par période"

    def _default_date_from(self):
        return self.env.company.season_start_date

    def _default_journal(self):
        Journal = self.env['account.journal']
        domain = [('type', '=', 'bank'), ('company_id', '=', self.env.company.id)]
        return (Journal.search(domain + [('cash_transfer_target', '=', True)], limit=1)
                or Journal.search(domain, limit=1))

    journal_id = fields.Many2one(
        'account.journal', string="Compte bancaire", required=True, default=_default_journal,
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]")
    date_from = fields.Date(string="Du", default=_default_date_from)
    date_to = fields.Date(string="Au", default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string="Société", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    opening_balance = fields.Monetary(
        string="Solde au début de la période", compute='_compute_statement',
        help="Entrées moins sorties du compte avant la période.")
    amount_collection = fields.Monetary(
        string="Encaissements clients", compute='_compute_statement',
        help="Paiements des clients reçus sur ce journal (surtout les ventes locales).")
    amount_cash_transfer = fields.Monetary(
        string="Versements d'espèces de la caisse", compute='_compute_statement',
        help="Versements d'espèces validés vers ce compte.")
    amount_other_in = fields.Monetary(
        string="Autres entrées", compute='_compute_statement',
        help="Autres paiements reçus et autres écritures au débit du compte de la banque.")
    amount_in = fields.Monetary(string="Total des entrées", compute='_compute_statement')

    amount_supplier_payment = fields.Monetary(
        string="Paiements de factures d'achat", compute='_compute_statement',
        help="Paiements aux fournisseurs saisis sur ce journal.")
    amount_cash_deposit = fields.Monetary(
        string="Remises d'espèces vers la caisse", compute='_compute_statement',
        help="Remises d'espèces validées dont le compte bancaire est ce journal.")
    amount_other_out = fields.Monetary(
        string="Autres sorties", compute='_compute_statement',
        help="Autres paiements émis et autres écritures au crédit du compte de la banque (frais…).")
    amount_out = fields.Monetary(string="Total des sorties", compute='_compute_statement')

    amount_period = fields.Monetary(string="Variation de la période", compute='_compute_statement')
    closing_balance = fields.Monetary(
        string="Solde à la fin de la période", compute='_compute_statement',
        help="Solde au début + entrées − sorties, d'après Odoo. À comparer au relevé de la banque.")

    def _get_period_domain(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), ('journal_id', '=', self.journal_id.id)]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        return domain

    @api.depends('journal_id', 'date_from', 'date_to', 'company_id')
    def _compute_statement(self):
        report = self.env['sofalgri.bank.position.report']
        for statement in self:
            amounts = {}
            opening = 0.0
            if statement.company_id and statement.journal_id:
                for movement_type, direction, amount in report._read_group(
                        statement._get_period_domain(), ['movement_type', 'direction'], ['amount:sum']):
                    amounts[(movement_type, direction)] = amount or 0.0
                if statement.date_from:
                    opening = report._read_group(
                        [('company_id', '=', statement.company_id.id),
                         ('journal_id', '=', statement.journal_id.id),
                         ('date', '<', statement.date_from)],
                        [], ['amount:sum'])[0][0] or 0.0

            def net(movement_type):
                return amounts.get((movement_type, 'in'), 0.0) + amounts.get((movement_type, 'out'), 0.0)

            def others(direction):
                return (amounts.get(('other_payment', direction), 0.0)
                        + amounts.get(('other_entry', direction), 0.0))

            # Entrées : montants positifs (une extourne éventuelle est déduite).
            statement.amount_collection = net('collection')
            statement.amount_cash_transfer = net('cash_transfer')
            statement.amount_other_in = others('in')
            statement.amount_in = (statement.amount_collection + statement.amount_cash_transfer
                                   + statement.amount_other_in)
            # Sorties : négatives dans le détail, affichées ici en positif.
            statement.amount_supplier_payment = -net('supplier_payment')
            statement.amount_cash_deposit = -net('cash_deposit')
            statement.amount_other_out = -others('out')
            statement.amount_out = (statement.amount_supplier_payment + statement.amount_cash_deposit
                                    + statement.amount_other_out)
            statement.amount_period = statement.amount_in - statement.amount_out
            statement.opening_balance = opening
            statement.closing_balance = opening + statement.amount_period

    def action_open_details(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sofalgri_bank_position.action_bank_position_report')
        action['domain'] = self._get_period_domain()
        action['context'] = {
            'search_default_group_type': 1,
            'pivot_row_groupby': ['movement_type'],
            'pivot_column_groupby': ['date:month'],
            'pivot_measures': ['amount'],
        }
        return action
