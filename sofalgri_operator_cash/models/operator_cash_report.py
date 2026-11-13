from odoo import fields, models, tools

MOVEMENT_TYPES = [
    ('deposit', "Remise d'espèces"),
    ('collection', "Encaissement client (ventes locales)"),
    ('avocado', "Paiement d'avocats"),
    ('fees', "Paiement de frais"),
    ('other_purchase', "Paiement d'autres achats"),
    ('unreconciled', "Paiement non rapproché d'une facture"),
    ('other_payment', "Autre mouvement"),
]


class OperatorCashReport(models.Model):
    """Mouvements de la caisse de l'opérateur des achats.

    Montant signé : positif quand l'opérateur reçoit des espèces (remise, encaissement d'un client),
    négatif quand il les dépense (paiement en espèces). La somme est le reste en espèces chez l'opérateur.
    """
    _name = 'sofalgri.operator.cash.report'
    _description = "Mouvements de la caisse de l'opérateur"
    _auto = False
    _order = 'date desc, id desc'
    _depends = {
        'account.cash.deposit': ['state', 'operation_type', 'move_id', 'name', 'company_id'],
        'account.payment': [
            'state', 'journal_id', 'payment_type', 'partner_type', 'amount', 'date', 'name',
            'partner_id', 'move_id', 'company_id', 'purchase_id',
        ],
        'account.move': ['state', 'move_type', 'date'],
        'account.move.line': ['move_id', 'account_id', 'balance', 'display_type', 'product_id', 'purchase_line_id'],
        'account.partial.reconcile': ['debit_move_id', 'credit_move_id', 'amount'],
        'purchase.order.line': ['order_id'],
        'sofalgri.cash.transfer': ['state', 'date', 'cash_journal_id', 'bank_journal_id', 'amount', 'name'],
    }

    date = fields.Date(string="Date", readonly=True)
    company_id = fields.Many2one('res.company', string="Société", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Devise", readonly=True)
    movement_type = fields.Selection(MOVEMENT_TYPES, string="Type", readonly=True)
    direction = fields.Selection([
        ('in', "Reçu par l'opérateur"),
        ('out', "Dépensé par l'opérateur"),
    ], string="Sens", readonly=True)
    reference = fields.Char(string="Référence", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partenaire", readonly=True)
    cash_deposit_id = fields.Many2one('account.cash.deposit', string="Remise d'espèces", readonly=True)
    payment_id = fields.Many2one('account.payment', string="Paiement", readonly=True)
    bill_id = fields.Many2one('account.move', string="Facture payée", readonly=True)
    purchase_id = fields.Many2one('purchase.order', string="Commande d'achat", readonly=True)
    notes = fields.Char(string="Notes", readonly=True)
    amount = fields.Monetary(string="Montant", readonly=True)
    amount_in = fields.Monetary(string="Reçu", readonly=True)
    amount_out = fields.Monetary(string="Dépensé", readonly=True)

    def action_open_source(self):
        self.ensure_one()
        record = self.cash_deposit_id or self.bill_id or self.payment_id
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
                WITH deposits AS (
                    -- Espèces sorties de la caisse vers l'opérateur : montant lu sur l'écriture de la remise.
                    SELECT deposit.id AS cash_deposit_id,
                           deposit_move.date,
                           deposit.company_id,
                           deposit.name AS reference,
                           LEFT(deposit.notes, 200) AS notes,
                           SUM(-cash_line.balance) AS amount
                    FROM account_cash_deposit deposit
                    JOIN account_move deposit_move ON deposit_move.id = deposit.move_id
                    JOIN account_move_line cash_line ON cash_line.move_id = deposit_move.id
                    JOIN account_account cash_account ON cash_account.id = cash_line.account_id
                    WHERE deposit.state = 'done'
                      AND deposit.operation_type = 'deposit'
                      AND deposit_move.state = 'posted'
                      AND cash_account.account_type = 'asset_cash'
                    GROUP BY deposit.id, deposit_move.date, deposit.company_id, deposit.name, deposit.notes
                ),
                cash_payments AS (
                    SELECT payment.id,
                           payment.date,
                           payment.company_id,
                           payment.partner_id,
                           payment.name,
                           payment.payment_type,
                           payment.partner_type,
                           payment.amount,
                           payment.move_id,
                           payment.purchase_id
                    FROM account_payment payment
                    JOIN account_journal journal ON journal.id = payment.journal_id
                    LEFT JOIN account_move payment_move ON payment_move.id = payment.move_id
                    WHERE journal.type = 'cash'
                      AND payment.state IN ('in_process', 'paid')
                      AND (payment_move.id IS NULL OR payment_move.state = 'posted')
                ),
                -- Part de chaque paiement fournisseur rapprochée d'une facture.
                bill_reconciles AS (
                    SELECT payment.id AS payment_id,
                           bill.id AS bill_id,
                           SUM(partial.amount) AS amount
                    FROM cash_payments payment
                    JOIN account_move_line payment_line ON payment_line.move_id = payment.move_id
                    JOIN account_account payable ON payable.id = payment_line.account_id
                    JOIN account_partial_reconcile partial ON partial.debit_move_id = payment_line.id
                    JOIN account_move_line bill_line ON bill_line.id = partial.credit_move_id
                    JOIN account_move bill ON bill.id = bill_line.move_id
                    WHERE payment.payment_type = 'outbound'
                      AND payable.account_type = 'liability_payable'
                      AND bill.move_type = 'in_invoice'
                    GROUP BY payment.id, bill.id
                ),
                -- Répartition de chaque facture d'après la catégorie des articles de ses lignes.
                bill_kinds AS (
                    SELECT line.move_id AS bill_id,
                           CASE
                               WHEN category.complete_name ILIKE '%Matière Première%' THEN 'avocado'
                               WHEN category.complete_name ILIKE '%Dépenses%' THEN 'fees'
                               ELSE 'other_purchase'
                           END AS kind,
                           SUM(line.balance) AS amount,
                           MIN(po_line.order_id) AS purchase_id
                    FROM account_move_line line
                    LEFT JOIN product_product product ON product.id = line.product_id
                    LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                    LEFT JOIN product_category category ON category.id = template.categ_id
                    LEFT JOIN purchase_order_line po_line ON po_line.id = line.purchase_line_id
                    WHERE line.display_type = 'product'
                      AND line.move_id IN (SELECT bill_id FROM bill_reconciles)
                    GROUP BY 1, 2
                ),
                bill_totals AS (
                    SELECT bill_id, SUM(amount) AS amount, MIN(purchase_id) AS purchase_id
                    FROM bill_kinds
                    GROUP BY bill_id
                ),
                paid_bills AS (
                    SELECT reconcile.payment_id,
                           reconcile.bill_id,
                           COALESCE(kinds.kind, 'other_purchase') AS kind,
                           COALESCE(kinds.purchase_id, totals.purchase_id) AS purchase_id,
                           CASE
                               WHEN kinds.bill_id IS NULL OR totals.amount = 0 THEN reconcile.amount
                               ELSE reconcile.amount * kinds.amount / totals.amount
                           END AS amount
                    FROM bill_reconciles reconcile
                    LEFT JOIN bill_totals totals ON totals.bill_id = reconcile.bill_id
                    LEFT JOIN bill_kinds kinds ON kinds.bill_id = reconcile.bill_id AND totals.amount <> 0
                ),
                payment_reconciled AS (
                    SELECT payment_id, SUM(amount) AS amount
                    FROM bill_reconciles
                    GROUP BY payment_id
                ),
                movements AS (
                    SELECT deposit.date, deposit.company_id, 'deposit' AS movement_type,
                           deposit.reference, NULL::integer AS partner_id,
                           deposit.cash_deposit_id, NULL::integer AS payment_id,
                           NULL::integer AS bill_id, NULL::integer AS purchase_id,
                           deposit.notes, deposit.amount
                    FROM deposits deposit

                    UNION ALL
                    -- Encaissements en espèces (clients : ventes locales ; autres : remboursements).
                    SELECT payment.date, payment.company_id,
                           CASE WHEN payment.partner_type = 'customer' THEN 'collection' ELSE 'other_payment' END,
                           payment.name, payment.partner_id,
                           NULL, payment.id, NULL, payment.purchase_id,
                           NULL, payment.amount
                    FROM cash_payments payment
                    WHERE payment.payment_type = 'inbound'

                    UNION ALL
                    -- Espèces des clients versées en banque : déduites des encaissements.
                    SELECT transfer.date, transfer.company_id, 'collection',
                           transfer.name, NULL,
                           NULL, NULL, NULL, NULL,
                           'Versement en banque : ' || COALESCE(bank_journal.code, ''),
                           -transfer.amount
                    FROM sofalgri_cash_transfer transfer
                    JOIN account_journal cash_journal ON cash_journal.id = transfer.cash_journal_id
                    LEFT JOIN account_journal bank_journal ON bank_journal.id = transfer.bank_journal_id
                    WHERE transfer.state = 'posted'
                      AND cash_journal.type = 'cash'

                    UNION ALL
                    -- Paiements en espèces rapprochés de factures fournisseurs, répartis par catégorie.
                    SELECT payment.date, payment.company_id, paid.kind,
                           payment.name, payment.partner_id,
                           NULL, payment.id, paid.bill_id, COALESCE(paid.purchase_id, payment.purchase_id),
                           NULL, -paid.amount
                    FROM paid_bills paid
                    JOIN cash_payments payment ON payment.id = paid.payment_id

                    UNION ALL
                    -- Reste des paiements sortants : avance pas encore rapprochée, ou paiement à un client.
                    SELECT payment.date, payment.company_id,
                           CASE WHEN payment.partner_type = 'supplier' THEN 'unreconciled' ELSE 'other_payment' END,
                           payment.name, payment.partner_id,
                           NULL, payment.id, NULL, payment.purchase_id,
                           NULL, -(payment.amount - COALESCE(reconciled.amount, 0))
                    FROM cash_payments payment
                    LEFT JOIN payment_reconciled reconciled ON reconciled.payment_id = payment.id
                    WHERE payment.payment_type = 'outbound'
                      AND ROUND((payment.amount - COALESCE(reconciled.amount, 0))::numeric, 2) <> 0
                )
                SELECT ROW_NUMBER() OVER (ORDER BY movement.date, movement.movement_type,
                                                   movement.cash_deposit_id, movement.payment_id,
                                                   movement.bill_id) AS id,
                       movement.date,
                       movement.company_id,
                       company.currency_id,
                       movement.movement_type,
                       CASE WHEN movement.amount >= 0 THEN 'in' ELSE 'out' END AS direction,
                       movement.reference,
                       movement.partner_id,
                       movement.cash_deposit_id,
                       movement.payment_id,
                       movement.bill_id,
                       movement.purchase_id,
                       movement.notes,
                       ROUND(movement.amount::numeric, 2) AS amount,
                       ROUND(GREATEST(movement.amount, 0)::numeric, 2) AS amount_in,
                       ROUND(GREATEST(-movement.amount, 0)::numeric, 2) AS amount_out
                FROM movements movement
                JOIN res_company company ON company.id = movement.company_id
            )
        """)
