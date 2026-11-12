from odoo import api, fields, models

from .operator_cash_report import MOVEMENT_TYPES


class OperatorCashStatement(models.TransientModel):
    _name = 'sofalgri.operator.cash.statement'
    _description = "Caisse de l'opérateur par période"

    def _default_date_from(self):
        return self.env.company.season_start_date

    date_from = fields.Date(string="Du", default=_default_date_from)
    date_to = fields.Date(string="Au", default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string="Société", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    opening_balance = fields.Monetary(
        string="Reste au début de la période", compute='_compute_statement',
        help="Espèces remises et encaissées avant la période, moins les paiements en espèces avant la période.")
    amount_deposit = fields.Monetary(string="Remises d'espèces", compute='_compute_statement')
    amount_collection = fields.Monetary(string="Encaissements clients (ventes locales)", compute='_compute_statement')
    amount_received = fields.Monetary(string="Total reçu", compute='_compute_statement')

    amount_avocado = fields.Monetary(string="Paiements d'avocats", compute='_compute_statement')
    amount_fees = fields.Monetary(
        string="Paiements de frais", compute='_compute_statement',
        help="Lignes des factures payées dont l'article est de catégorie « Dépenses » "
             "(chargement, transport, SAMSSAR…).")
    amount_other_purchase = fields.Monetary(string="Paiements d'autres achats", compute='_compute_statement')
    amount_unreconciled = fields.Monetary(
        string="Paiements non rapprochés", compute='_compute_statement',
        help="Paiements en espèces à un fournisseur pas encore rapprochés d'une facture (avances).")
    amount_other_payment = fields.Monetary(
        string="Autres mouvements (net)", compute='_compute_statement',
        help="Remboursements de fournisseurs et paiements en espèces à des clients : reçu moins payé.")
    amount_spent = fields.Monetary(string="Total dépensé", compute='_compute_statement')

    amount_period = fields.Monetary(string="Variation de la période", compute='_compute_statement')
    closing_balance = fields.Monetary(
        string="Reste en espèces chez l'opérateur", compute='_compute_statement',
        help="Reste au début de la période + reçu − dépensé. Négatif : plus de paiements saisis que d'espèces remises.")

    def _get_period_domain(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        return domain

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_statement(self):
        report = self.env['sofalgri.operator.cash.report']
        for statement in self:
            amounts = dict.fromkeys([key for key, _label in MOVEMENT_TYPES], 0.0)
            opening = 0.0
            if statement.company_id:
                for movement_type, amount in report._read_group(
                        statement._get_period_domain(), ['movement_type'], ['amount:sum']):
                    amounts[movement_type] = amount or 0.0
                if statement.date_from:
                    opening = report._read_group(
                        [('company_id', '=', statement.company_id.id), ('date', '<', statement.date_from)],
                        [], ['amount:sum'])[0][0] or 0.0

            statement.opening_balance = opening
            statement.amount_deposit = amounts['deposit']
            statement.amount_collection = amounts['collection']
            statement.amount_received = amounts['deposit'] + amounts['collection']
            # Dans le détail les dépenses sont négatives : affichées ici en positif.
            statement.amount_avocado = -amounts['avocado']
            statement.amount_fees = -amounts['fees']
            statement.amount_other_purchase = -amounts['other_purchase']
            statement.amount_unreconciled = -amounts['unreconciled']
            statement.amount_other_payment = amounts['other_payment']
            statement.amount_spent = -(
                amounts['avocado'] + amounts['fees'] + amounts['other_purchase'] + amounts['unreconciled'])
            period = sum(amounts.values())
            statement.amount_period = period
            statement.closing_balance = opening + period

    def action_open_details(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sofalgri_operator_cash.action_operator_cash_report')
        action['domain'] = self._get_period_domain()
        action['context'] = {
            'search_default_group_type': 1,
            'pivot_row_groupby': ['movement_type'],
            'pivot_column_groupby': ['date:month'],
            'pivot_measures': ['amount'],
        }
        return action
