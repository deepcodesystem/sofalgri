from odoo import api, fields, models, tools


class PurchaseSummaryReport(models.Model):
    _name = 'sofalgri.purchase.summary.report'
    _description = "Achats d'avocats par commande"
    _auto = False
    _rec_name = 'order_id'
    _order = 'date_order desc, id desc'
    _depends = {
        'purchase.order': ['name', 'state', 'partner_id', 'date_order', 'company_id'],
        'purchase.order.line': ['order_id', 'product_id', 'product_qty', 'qty_received', 'price_subtotal'],
        'account.move': ['state', 'move_type', 'amount_total', 'amount_residual'],
        'account.move.line': ['move_id', 'purchase_line_id', 'balance', 'amount_residual', 'account_id'],
        'account.payment': ['purchase_id', 'move_id'],
    }

    order_id = fields.Many2one('purchase.order', string="Commande", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Fournisseur", readonly=True)
    date_order = fields.Datetime(string="Date", readonly=True)
    company_id = fields.Many2one('res.company', string="Société", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Devise", readonly=True)

    qty_ordered = fields.Float(string="Qté commandée (kg)", readonly=True)
    qty_received = fields.Float(string="Qté reçue (kg)", readonly=True)
    qty_variation = fields.Float(string="Variation (kg)", readonly=True)
    variation_percent = fields.Float(string="Variation (%)", digits=(12, 2), readonly=True, aggregator=None)

    amount_avocado = fields.Monetary(string="Montant avocats", readonly=True)
    amount_fees = fields.Monetary(string="Frais", readonly=True)
    amount_due = fields.Monetary(string="Total à payer", readonly=True)
    amount_paid = fields.Monetary(string="Payé", readonly=True)
    amount_residual = fields.Monetary(string="Reste à payer", readonly=True)
    payment_status = fields.Selection([
        ('not_paid', "Non payé"),
        ('partial', "Partiel"),
        ('paid', "Payé"),
    ], string="Statut", readonly=True)

    current_season = fields.Boolean(
        string="Saison en cours", compute='_compute_current_season', search='_search_current_season')

    @api.depends('date_order')
    @api.depends_context('company')
    def _compute_current_season(self):
        start = self.env.company.season_start_date
        for report in self:
            report.current_season = not start or report.date_order.date() >= start

    def _search_current_season(self, operator, value):
        start = self.env.company.season_start_date
        if (operator == '=') == bool(value):
            return [('date_order', '>=', start)] if start else []
        return [('date_order', '<', start)] if start else [('id', '=', 0)]

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH order_amounts AS (
                    SELECT line.order_id,
                           SUM(line.product_qty) FILTER (WHERE category.complete_name ILIKE '%Matière Première%') AS qty_ordered,
                           SUM(line.qty_received) FILTER (WHERE category.complete_name ILIKE '%Matière Première%') AS qty_received,
                           SUM(line.qty_received * line.price_subtotal / NULLIF(line.product_qty, 0))
                               FILTER (WHERE category.complete_name ILIKE '%Matière Première%') AS amount_avocado,
                           SUM(line.price_subtotal) FILTER (WHERE category.complete_name NOT ILIKE '%Matière Première%') AS amount_fees
                    FROM purchase_order_line line
                    JOIN product_product product ON product.id = line.product_id
                    JOIN product_template template ON template.id = product.product_tmpl_id
                    JOIN product_category category ON category.id = template.categ_id
                    GROUP BY line.order_id
                ),
                -- Part payée de chaque facture, au prorata de ce qu'elle facture sur la commande.
                bill_payments AS (
                    SELECT po_line.order_id,
                           SUM(bill_line.balance * (bill.amount_total - bill.amount_residual)
                               / NULLIF(bill.amount_total, 0)) AS amount
                    FROM account_move_line bill_line
                    JOIN account_move bill ON bill.id = bill_line.move_id
                    JOIN purchase_order_line po_line ON po_line.id = bill_line.purchase_line_id
                    WHERE bill.state = 'posted'
                      AND bill.move_type IN ('in_invoice', 'in_refund')
                    GROUP BY po_line.order_id
                ),
                -- Avances sur commande, pour la part pas encore rapprochée d'une facture.
                advance_payments AS (
                    SELECT payment.purchase_id AS order_id,
                           SUM(payment_line.amount_residual) AS amount
                    FROM account_payment payment
                    JOIN account_move payment_move ON payment_move.id = payment.move_id
                    JOIN account_move_line payment_line ON payment_line.move_id = payment_move.id
                    JOIN account_account account ON account.id = payment_line.account_id
                    WHERE payment.purchase_id IS NOT NULL
                      AND payment_move.state = 'posted'
                      AND account.account_type = 'liability_payable'
                    GROUP BY payment.purchase_id
                ),
                totals AS (
                    SELECT po.id,
                           po.partner_id,
                           po.date_order,
                           po.company_id,
                           company.currency_id,
                           amounts.qty_ordered,
                           amounts.qty_received,
                           ROUND(COALESCE(amounts.amount_avocado, 0)::numeric, 2) AS amount_avocado,
                           ROUND(COALESCE(amounts.amount_fees, 0)::numeric, 2) AS amount_fees,
                           ROUND((COALESCE(bills.amount, 0) + COALESCE(advances.amount, 0))::numeric, 2) AS amount_paid
                    FROM purchase_order po
                    JOIN res_company company ON company.id = po.company_id
                    JOIN order_amounts amounts ON amounts.order_id = po.id
                    LEFT JOIN bill_payments bills ON bills.order_id = po.id
                    LEFT JOIN advance_payments advances ON advances.order_id = po.id
                    WHERE po.state IN ('purchase', 'done')
                      AND amounts.qty_ordered IS NOT NULL
                )
                SELECT id,
                       id AS order_id,
                       partner_id,
                       date_order,
                       company_id,
                       currency_id,
                       qty_ordered,
                       qty_received,
                       qty_received - qty_ordered AS qty_variation,
                       100 * (qty_received - qty_ordered) / NULLIF(qty_ordered, 0) AS variation_percent,
                       amount_avocado,
                       amount_fees,
                       amount_avocado + amount_fees AS amount_due,
                       amount_paid,
                       amount_avocado + amount_fees - amount_paid AS amount_residual,
                       CASE
                           WHEN amount_paid <= 0 THEN 'not_paid'
                           WHEN amount_paid < amount_avocado + amount_fees THEN 'partial'
                           ELSE 'paid'
                       END AS payment_status
                FROM totals
            )
        """)
