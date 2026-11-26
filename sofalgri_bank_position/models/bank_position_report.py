from odoo import fields, models, tools

MOVEMENT_TYPES = [
    ('collection', "Encaissement client"),
    ('cash_transfer', "Versement d'espèces de la caisse"),
    ('supplier_payment', "Paiement de facture d'achat"),
    ('cash_deposit', "Remise d'espèces vers la caisse"),
    ('other_payment', "Autre paiement"),
    ('other_entry', "Autre écriture"),
]


class BankPositionReport(models.Model):
    """Mouvements d'un compte bancaire.

    Montant signé : positif pour une entrée sur le compte, négatif pour une sortie.
    La somme sur un journal est le solde du compte d'après Odoo.

    Les paiements sont lus sur `account.payment` (journal de banque) et non sur le compte de la banque :
    dans Odoo 18 ils passent par un compte d'attente (paiements entrants / sortants en suspens),
    commun à plusieurs journaux, tant qu'ils ne sont pas rapprochés d'un relevé.
    """
    _name = 'sofalgri.bank.position.report'
    _description = "Mouvements du compte bancaire"
    _auto = False
    _order = 'date desc, id desc'
    _depends = {
        'account.payment': [
            'state', 'journal_id', 'payment_type', 'partner_type', 'amount', 'date', 'name',
            'partner_id', 'move_id', 'company_id', 'memo',
        ],
        'account.move': ['state', 'move_type', 'date', 'name', 'ref'],
        'account.move.line': ['move_id', 'account_id', 'balance', 'partner_id', 'name', 'date', 'company_id'],
        'account.partial.reconcile': ['debit_move_id', 'credit_move_id'],
        'account.journal': ['type', 'default_account_id', 'company_id'],
        'account.cash.deposit': ['state', 'bank_journal_id', 'move_id', 'name', 'notes', 'company_id'],
        'sofalgri.cash.transfer': [
            'state', 'date', 'company_id', 'bank_journal_id', 'amount', 'name', 'ref', 'move_id',
        ],
    }

    date = fields.Date(string="Date", readonly=True)
    company_id = fields.Many2one('res.company', string="Société", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Devise", readonly=True)
    journal_id = fields.Many2one('account.journal', string="Compte bancaire", readonly=True)
    movement_type = fields.Selection(MOVEMENT_TYPES, string="Type", readonly=True)
    direction = fields.Selection([
        ('in', "Entrée"),
        ('out', "Sortie"),
    ], string="Sens", readonly=True)
    reference = fields.Char(string="Référence", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partenaire", readonly=True)
    payment_id = fields.Many2one('account.payment', string="Paiement", readonly=True)
    invoice_id = fields.Many2one('account.move', string="Facture", readonly=True)
    cash_transfer_id = fields.Many2one('sofalgri.cash.transfer', string="Versement d'espèces", readonly=True)
    cash_deposit_id = fields.Many2one('account.cash.deposit', string="Remise d'espèces", readonly=True)
    move_id = fields.Many2one('account.move', string="Écriture", readonly=True)
    notes = fields.Char(string="Libellé", readonly=True)
    amount = fields.Monetary(string="Montant", readonly=True)
    amount_in = fields.Monetary(string="Entrée", readonly=True)
    amount_out = fields.Monetary(string="Sortie", readonly=True)

    def action_open_source(self):
        self.ensure_one()
        record = (self.invoice_id or self.payment_id or self.cash_transfer_id
                  or self.cash_deposit_id or self.move_id)
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
                WITH bank_payments AS (
                    SELECT payment.id,
                           payment.date,
                           payment.company_id,
                           payment.journal_id,
                           payment.partner_id,
                           payment.name,
                           payment.memo,
                           payment.payment_type,
                           payment.partner_type,
                           payment.amount,
                           payment.move_id
                    FROM account_payment payment
                    JOIN account_journal journal ON journal.id = payment.journal_id
                    LEFT JOIN account_move payment_move ON payment_move.id = payment.move_id
                    WHERE journal.type = 'bank'
                      AND payment.state IN ('in_process', 'paid')
                      AND (payment_move.id IS NULL OR payment_move.state = 'posted')
                ),
                -- Facture (client ou fournisseur) rapprochée du paiement : la première, pour le lien.
                payment_invoices AS (
                    SELECT payment.id AS payment_id,
                           MIN(invoice.id) AS invoice_id
                    FROM bank_payments payment
                    JOIN account_move_line payment_line ON payment_line.move_id = payment.move_id
                    JOIN account_account counterpart ON counterpart.id = payment_line.account_id
                    JOIN account_partial_reconcile partial
                         ON payment_line.id IN (partial.debit_move_id, partial.credit_move_id)
                    JOIN account_move_line invoice_line
                         ON invoice_line.id = CASE WHEN partial.debit_move_id = payment_line.id
                                                   THEN partial.credit_move_id
                                                   ELSE partial.debit_move_id END
                    JOIN account_move invoice ON invoice.id = invoice_line.move_id
                    WHERE counterpart.account_type IN ('asset_receivable', 'liability_payable')
                      AND invoice.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
                    GROUP BY payment.id
                ),
                movements AS (
                    -- Paiements saisis sur le journal de banque.
                    SELECT payment.date, payment.company_id, payment.journal_id,
                           CASE
                               WHEN payment.payment_type = 'inbound' AND payment.partner_type = 'customer'
                                   THEN 'collection'
                               WHEN payment.payment_type = 'outbound' AND payment.partner_type = 'supplier'
                                   THEN 'supplier_payment'
                               ELSE 'other_payment'
                           END AS movement_type,
                           payment.name AS reference, payment.partner_id,
                           payment.id AS payment_id, invoices.invoice_id,
                           NULL::integer AS cash_transfer_id, NULL::integer AS cash_deposit_id,
                           payment.move_id,
                           LEFT(payment.memo, 200) AS notes,
                           CASE WHEN payment.payment_type = 'inbound' THEN payment.amount
                                ELSE -payment.amount END AS amount
                    FROM bank_payments payment
                    LEFT JOIN payment_invoices invoices ON invoices.payment_id = payment.id

                    UNION ALL
                    -- Espèces de la caisse versées sur le compte (sofalgri_cash_transfer).
                    SELECT transfer.date, transfer.company_id, transfer.bank_journal_id, 'cash_transfer',
                           transfer.name, NULL,
                           NULL, NULL, transfer.id, NULL, transfer.move_id,
                           LEFT(transfer.ref, 200),
                           transfer.amount
                    FROM sofalgri_cash_transfer transfer
                    JOIN account_journal journal ON journal.id = transfer.bank_journal_id
                    WHERE transfer.state = 'posted'
                      AND journal.type = 'bank'

                    UNION ALL
                    -- Remises d'espèces vers la caisse prises sur le compte (compte bancaire de la remise) :
                    -- montant lu sur la ligne de caisse de l'écriture de la remise.
                    SELECT deposit_move.date, deposit.company_id, deposit.bank_journal_id, 'cash_deposit',
                           deposit.name, NULL,
                           NULL, NULL, NULL, deposit.id, deposit.move_id,
                           LEFT(deposit.notes, 200),
                           -ABS(SUM(cash_line.balance))
                    FROM account_cash_deposit deposit
                    JOIN account_journal journal ON journal.id = deposit.bank_journal_id
                    JOIN account_move deposit_move ON deposit_move.id = deposit.move_id
                    JOIN account_move_line cash_line ON cash_line.move_id = deposit_move.id
                    JOIN account_account cash_account ON cash_account.id = cash_line.account_id
                    WHERE deposit.state = 'done'
                      AND deposit_move.state = 'posted'
                      AND journal.type = 'bank'
                      AND cash_account.account_type = 'asset_cash'
                    GROUP BY deposit.id, deposit_move.date, deposit.company_id, deposit.bank_journal_id,
                             deposit.name, deposit.move_id, deposit.notes

                    UNION ALL
                    -- Autres écritures sur le compte de la banque (frais, opérations diverses),
                    -- hors paiements et versements d'espèces déjà comptés.
                    SELECT line.date, line.company_id, journal.id, 'other_entry',
                           move.name, line.partner_id,
                           NULL, NULL, NULL, NULL, move.id,
                           LEFT(COALESCE(line.name, move.ref), 200),
                           line.balance
                    FROM account_move_line line
                    JOIN account_move move ON move.id = line.move_id
                    JOIN account_journal journal
                         ON journal.default_account_id = line.account_id
                        AND journal.company_id = line.company_id
                        AND journal.type = 'bank'
                    WHERE move.state = 'posted'
                      AND NOT EXISTS (SELECT 1 FROM bank_payments payment WHERE payment.move_id = move.id)
                      AND NOT EXISTS (SELECT 1 FROM sofalgri_cash_transfer transfer
                                      WHERE transfer.move_id = move.id)
                )
                SELECT ROW_NUMBER() OVER (ORDER BY movement.date, movement.journal_id, movement.movement_type,
                                                   movement.payment_id, movement.cash_transfer_id,
                                                   movement.cash_deposit_id, movement.move_id) AS id,
                       movement.date,
                       movement.company_id,
                       company.currency_id,
                       movement.journal_id,
                       movement.movement_type,
                       CASE WHEN movement.amount >= 0 THEN 'in' ELSE 'out' END AS direction,
                       movement.reference,
                       movement.partner_id,
                       movement.payment_id,
                       movement.invoice_id,
                       movement.cash_transfer_id,
                       movement.cash_deposit_id,
                       movement.move_id,
                       movement.notes,
                       ROUND(movement.amount::numeric, 2) AS amount,
                       ROUND(GREATEST(movement.amount, 0)::numeric, 2) AS amount_in,
                       ROUND(GREATEST(-movement.amount, 0)::numeric, 2) AS amount_out
                FROM movements movement
                JOIN res_company company ON company.id = movement.company_id
            )
        """)
