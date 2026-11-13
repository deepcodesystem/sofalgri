from odoo import api, fields, models, tools

LINE_KINDS = [
    ('invoice', "Facture"),
    ('refund', "Avoir"),
    ('advance', "Paiement non rapproché"),
]

PAYMENT_STATES = [
    ('not_paid', "Non payée"),
    ('in_payment', "En paiement"),
    ('paid', "Payée"),
    ('partial', "Partiellement payée"),
    ('reversed', "Extournée"),
    ('blocked', "Bloquée"),
    ('invoicing_legacy', "Historique"),
]


class LocalSaleReport(models.Model):
    """Ventes locales et leurs paiements.

    Une ligne par facture ou avoir validé d'un journal de vente coché « Journal des ventes locales »,
    et une ligne par encaissement d'un client local dont une partie n'est rapprochée d'aucune facture.

    Montants en devise de la société, signés (avoir négatif). Le payé est réparti d'après le journal
    de l'écriture rapprochée : caisse = espèces, banque = virement, autre (avoir, opération diverse).
    Ligne « Paiement non rapproché » : la part libre de l'encaissement en espèces ou virement, et le
    même montant en négatif dans le reste à payer, pour que le total du reste soit le solde net du client.
    """
    _name = 'sofalgri.local.sale.report'
    _description = "Ventes locales et paiements"
    _auto = False
    _order = 'date desc, id desc'
    _depends = {
        'account.move': [
            'state', 'move_type', 'journal_id', 'invoice_date', 'date', 'name', 'commercial_partner_id',
            'amount_total_signed', 'amount_residual_signed', 'payment_state', 'fiscal_position_id',
            'company_id',
        ],
        'account.move.line': ['move_id', 'account_id', 'display_type', 'quantity', 'amount_residual'],
        'account.partial.reconcile': ['debit_move_id', 'credit_move_id', 'amount'],
        'account.payment': ['state', 'journal_id', 'payment_type', 'partner_type', 'partner_id', 'move_id', 'name'],
        'account.journal': ['type', 'is_local_sale'],
    }

    date = fields.Date(string="Date", readonly=True)
    company_id = fields.Many2one('res.company', string="Société", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Devise", readonly=True)
    line_kind = fields.Selection(LINE_KINDS, string="Type", readonly=True)
    reference = fields.Char(string="Référence", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Client", readonly=True)
    move_id = fields.Many2one('account.move', string="Facture", readonly=True)
    payment_id = fields.Many2one('account.payment', string="Paiement", readonly=True)
    payment_journal_id = fields.Many2one('account.journal', string="Journal du paiement", readonly=True)
    payment_state = fields.Selection(PAYMENT_STATES, string="État du paiement", readonly=True)
    quantity = fields.Float(string="Quantité (kg)", readonly=True)
    amount_total = fields.Monetary(string="Montant facturé", readonly=True)
    paid_cash = fields.Monetary(string="Payé en espèces", readonly=True)
    paid_bank = fields.Monetary(string="Payé par virement", readonly=True)
    paid_other = fields.Monetary(string="Autre règlement", readonly=True)
    amount_residual = fields.Monetary(string="Reste à payer", readonly=True)
    last_payment_date = fields.Date(string="Dernier paiement", readonly=True)

    current_season = fields.Boolean(
        string="Saison en cours", compute='_compute_current_season', search='_search_current_season')

    @api.depends('date')
    @api.depends_context('company')
    def _compute_current_season(self):
        start = self.env.company.season_start_date
        for line in self:
            line.current_season = bool(line.date and (not start or line.date >= start))

    def _search_current_season(self, operator, value):
        start = self.env.company.season_start_date
        if (operator == '=') == bool(value):
            return [('date', '>=', start)] if start else []
        return [('date', '<', start)] if start else [('id', '=', 0)]

    def action_open_source(self):
        self.ensure_one()
        record = self.move_id or self.payment_id
        return {
            'type': 'ir.actions.act_window',
            'res_model': record._name,
            'res_id': record.id,
            'view_mode': 'form',
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH local_moves AS (
                    SELECT move.id,
                           move.company_id,
                           COALESCE(move.invoice_date, move.date) AS date,
                           move.name,
                           move.move_type,
                           move.commercial_partner_id,
                           move.payment_state,
                           move.amount_total_signed,
                           move.amount_residual_signed
                    FROM account_move move
                    JOIN account_journal journal ON journal.id = move.journal_id
                    WHERE journal.is_local_sale
                      AND move.state = 'posted'
                      AND move.move_type IN ('out_invoice', 'out_refund')
                ),
                quantities AS (
                    SELECT line.move_id,
                           SUM(CASE WHEN local_move.move_type = 'out_refund' THEN -line.quantity
                                    ELSE line.quantity END) AS quantity
                    FROM account_move_line line
                    JOIN local_moves local_move ON local_move.id = line.move_id
                    WHERE line.display_type = 'product'
                    GROUP BY line.move_id
                ),
                -- Lignes client (compte à recevoir) des factures locales.
                receivable_lines AS (
                    SELECT line.id, line.move_id
                    FROM account_move_line line
                    JOIN local_moves local_move ON local_move.id = line.move_id
                    JOIN account_account account ON account.id = line.account_id
                    WHERE account.account_type = 'asset_receivable'
                ),
                -- Rapprochements : + quand la ligne de la facture est au débit, - quand elle est au crédit (avoir).
                reconciles AS (
                    SELECT receivable.move_id,
                           partial.amount AS amount,
                           partial.credit_move_id AS counterpart_line_id
                    FROM receivable_lines receivable
                    JOIN account_partial_reconcile partial ON partial.debit_move_id = receivable.id
                    UNION ALL
                    SELECT receivable.move_id,
                           -partial.amount,
                           partial.debit_move_id
                    FROM receivable_lines receivable
                    JOIN account_partial_reconcile partial ON partial.credit_move_id = receivable.id
                ),
                paid AS (
                    SELECT reconcile.move_id,
                           SUM(CASE WHEN journal.type = 'cash' THEN reconcile.amount ELSE 0 END) AS paid_cash,
                           SUM(CASE WHEN journal.type = 'bank' THEN reconcile.amount ELSE 0 END) AS paid_bank,
                           MAX(CASE WHEN journal.type IN ('cash', 'bank') THEN counterpart_move.date END)
                               AS last_payment_date
                    FROM reconciles reconcile
                    JOIN account_move_line counterpart ON counterpart.id = reconcile.counterpart_line_id
                    JOIN account_move counterpart_move ON counterpart_move.id = counterpart.move_id
                    JOIN account_journal journal ON journal.id = counterpart_move.journal_id
                    GROUP BY reconcile.move_id
                ),
                -- Clients ayant une facture d'export : leurs encaissements ne sont pas des ventes locales.
                export_partners AS (
                    SELECT DISTINCT move.commercial_partner_id
                    FROM account_move move
                    JOIN account_fiscal_position position ON position.id = move.fiscal_position_id
                    WHERE move.state = 'posted'
                      AND move.move_type IN ('out_invoice', 'out_refund')
                      AND position.name::text ILIKE '%Export%'
                ),
                -- Encaissements clients en espèces ou par banque, part non rapprochée.
                advances AS (
                    SELECT payment.id AS payment_id,
                           payment_move.company_id,
                           payment_move.date,
                           payment.name,
                           payment.journal_id,
                           journal.type AS journal_type,
                           partner.commercial_partner_id,
                           SUM(-line.amount_residual) AS amount
                    FROM account_payment payment
                    JOIN account_move payment_move ON payment_move.id = payment.move_id
                    JOIN account_journal journal ON journal.id = payment.journal_id
                    JOIN res_partner partner ON partner.id = payment.partner_id
                    JOIN account_move_line line ON line.move_id = payment_move.id
                    JOIN account_account account ON account.id = line.account_id
                    WHERE payment.partner_type = 'customer'
                      AND payment.payment_type = 'inbound'
                      AND payment.state IN ('in_process', 'paid')
                      AND payment_move.state = 'posted'
                      AND journal.type IN ('cash', 'bank')
                      AND account.account_type = 'asset_receivable'
                      AND partner.commercial_partner_id NOT IN (
                          SELECT commercial_partner_id FROM export_partners
                          WHERE commercial_partner_id IS NOT NULL)
                    GROUP BY payment.id, payment_move.company_id, payment_move.date, payment.name,
                             payment.journal_id, journal.type, partner.commercial_partner_id
                ),
                report_lines AS (
                    SELECT local_move.date,
                           local_move.company_id,
                           CASE WHEN local_move.move_type = 'out_refund' THEN 'refund' ELSE 'invoice' END AS line_kind,
                           local_move.name AS reference,
                           local_move.commercial_partner_id AS partner_id,
                           local_move.id AS move_id,
                           NULL::integer AS payment_id,
                           NULL::integer AS payment_journal_id,
                           local_move.payment_state,
                           COALESCE(quantity.quantity, 0) AS quantity,
                           local_move.amount_total_signed AS amount_total,
                           COALESCE(paid.paid_cash, 0) AS paid_cash,
                           COALESCE(paid.paid_bank, 0) AS paid_bank,
                           local_move.amount_total_signed - local_move.amount_residual_signed
                               - COALESCE(paid.paid_cash, 0) - COALESCE(paid.paid_bank, 0) AS paid_other,
                           local_move.amount_residual_signed AS amount_residual,
                           paid.last_payment_date
                    FROM local_moves local_move
                    LEFT JOIN quantities quantity ON quantity.move_id = local_move.id
                    LEFT JOIN paid ON paid.move_id = local_move.id

                    UNION ALL
                    SELECT advance.date,
                           advance.company_id,
                           'advance',
                           advance.name,
                           advance.commercial_partner_id,
                           NULL,
                           advance.payment_id,
                           advance.journal_id,
                           NULL,
                           0,
                           0,
                           CASE WHEN advance.journal_type = 'cash' THEN advance.amount ELSE 0 END,
                           CASE WHEN advance.journal_type = 'bank' THEN advance.amount ELSE 0 END,
                           0,
                           -advance.amount,
                           advance.date
                    FROM advances advance
                    WHERE ROUND(advance.amount::numeric, 2) <> 0
                )
                SELECT ROW_NUMBER() OVER (ORDER BY report_line.date, report_line.line_kind,
                                                   report_line.move_id, report_line.payment_id) AS id,
                       report_line.date,
                       report_line.company_id,
                       company.currency_id,
                       report_line.line_kind,
                       report_line.reference,
                       report_line.partner_id,
                       report_line.move_id,
                       report_line.payment_id,
                       report_line.payment_journal_id,
                       report_line.payment_state,
                       report_line.quantity,
                       ROUND(report_line.amount_total::numeric, 2) AS amount_total,
                       ROUND(report_line.paid_cash::numeric, 2) AS paid_cash,
                       ROUND(report_line.paid_bank::numeric, 2) AS paid_bank,
                       ROUND(report_line.paid_other::numeric, 2) AS paid_other,
                       ROUND(report_line.amount_residual::numeric, 2) AS amount_residual,
                       report_line.last_payment_date
                FROM report_lines report_line
                JOIN res_company company ON company.id = report_line.company_id
            )
        """)
