from odoo import api, fields, models, tools

INCOME_RUBRICS = [
    ('sale_export', "Ventes export"),
    ('sale_local', "Ventes locales"),
    ('sale_waste', "Ventes de déchets"),
    ('sale_other', "Autres produits"),
]
COST_RUBRICS = [
    ('avocado', "Achat d'avocats"),
    ('waste_purchase', "Achat de déchets fermes"),
    ('harvest', "Récolte et chargement"),
    ('farm_transport', "Transport ferme → station"),
    ('packaging', "Emballages consommés"),
    ('station', "Prestation station"),
    ('forwarder', "Transitaire"),
    ('export_transport', "Transport international"),
    ('other_cost', "Autres frais"),
    ('stock_variation', "Variation du stock d'avocats"),
]
# Articles lus sur les commandes d'achat et les factures fournisseurs (les emballages viennent des OF ;
# les déchets achetés aux fermes vont en « Achat de déchets fermes »).
PURCHASE_RUBRICS = ("('avocado', 'waste', 'harvest', 'farm_transport', 'station', 'forwarder', "
                    "'export_transport', 'other_cost')")
# Transport, transitaire et station : le coût vient des prix négociés saisis sur la facture d'export ;
# les factures de ces fournisseurs, reçues plus tard, ne servent qu'au contrôle (pas de double comptage).
CONTROL_RUBRICS = [('supplier_billed', "Facturé par les fournisseurs (contrôle)")]
PURCHASE_RUBRIC_SQL = ("CASE WHEN info.rubric = 'waste' THEN 'waste_purchase' "
                       "WHEN info.rubric IN ('station', 'forwarder', 'export_transport') THEN 'supplier_billed' "
                       "ELSE info.rubric END")
PURCHASE_KG_RUBRICS = "('avocado', 'waste')"


class OperatingReport(models.Model):
    _name = 'sofalgri.operating.report'
    _description = "Compte d'exploitation : détail"
    _auto = False
    _order = 'date desc, id desc'
    _depends = {
        'product.template': ['operating_rubric', 'categ_id'],
        'product.category': ['complete_name'],
        'account.move': ['state', 'move_type', 'date', 'partner_id', 'fiscal_position_id', 'company_id',
                         'export_transport_cost', 'export_forwarder_cost', 'export_station_cost'],
        'account.move.line': ['move_id', 'product_id', 'display_type', 'balance', 'quantity', 'purchase_line_id'],
        'purchase.order': ['state', 'date_order', 'partner_id', 'company_id'],
        'purchase.order.line': ['order_id', 'product_id', 'price_subtotal', 'qty_received'],
        'stock.valuation.layer': ['value', 'product_id', 'stock_move_id', 'create_date', 'company_id'],
        'stock.move': ['location_id', 'location_dest_id'],
    }

    date = fields.Date(string="Date", readonly=True)
    company_id = fields.Many2one('res.company', string="Société", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Devise", readonly=True)
    section = fields.Selection(
        [('income', "Produits"), ('cost', "Charges"), ('control', "Contrôle")], string="Section", readonly=True)
    rubric = fields.Selection(INCOME_RUBRICS + COST_RUBRICS + CONTROL_RUBRICS, string="Rubrique", readonly=True)
    product_id = fields.Many2one('product.product', string="Article", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partenaire", readonly=True)
    account_move_id = fields.Many2one('account.move', string="Facture", readonly=True)
    purchase_order_id = fields.Many2one('purchase.order', string="Commande d'achat", readonly=True)
    amount = fields.Monetary(
        string="Montant", readonly=True,
        help="Produits en positif, charges en négatif : le total est la marge.")
    control_amount = fields.Monetary(
        string="Facturé par les fournisseurs", readonly=True,
        help="Factures de transport international, de transitaire et de station : contrôle, hors marge.")
    quantity = fields.Float(
        string="Quantité (kg)", readonly=True,
        help="Kg facturés pour les ventes, kg reçus pour les achats d'avocats et de déchets fermes ; "
             "vide pour les autres rubriques.")

    current_season = fields.Boolean(
        string="Saison en cours", compute='_compute_current_season', search='_search_current_season')

    @api.depends('date')
    @api.depends_context('company')
    def _compute_current_season(self):
        start = self.env.company.season_start_date
        for line in self:
            line.current_season = not start or (line.date and line.date >= start)

    def _search_current_season(self, operator, value):
        start = self.env.company.season_start_date
        if (operator == '=') == bool(value):
            return [('date', '>=', start)] if start else []
        return [('date', '<', start)] if start else [('id', '=', 0)]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH product_info AS (
                    SELECT product.id AS product_id,
                           COALESCE(template.operating_rubric,
                                    CASE WHEN category.complete_name ILIKE '%Matière Première%' THEN 'avocado'
                                         WHEN category.complete_name ILIKE '%Emballage%' THEN 'packaging'
                                         WHEN category.complete_name ILIKE '%Déchet%' THEN 'waste'
                                         WHEN category.complete_name ILIKE '%Dépenses%' THEN 'other_cost'
                                         WHEN category.complete_name ILIKE 'Livraison%' THEN 'export_transport'
                                    END) AS rubric,
                           (category.complete_name ILIKE '%Matière Première%'
                            OR category.complete_name ILIKE '%Avocats Calibr%') AS is_avocado,
                           (category.complete_name ILIKE '%Matière Première%'
                            OR category.complete_name ILIKE '%Avocats Calibr%'
                            OR category.complete_name ILIKE '%Déchet%'
                            OR template.operating_rubric IN ('avocado', 'waste')) AS is_avocado_stock
                    FROM product_product product
                    JOIN product_template template ON template.id = product.product_tmpl_id
                    JOIN product_category category ON category.id = template.categ_id
                ),
                -- Factures et avoirs clients : déchets d'après la rubrique, avocats export ou local
                -- d'après la position fiscale (comme la Synthèse des exports), le reste en autres produits.
                sales AS (
                    SELECT move.date, move.company_id, line.product_id, move.partner_id,
                           move.id AS account_move_id, NULL::integer AS purchase_order_id,
                           CASE WHEN info.rubric = 'waste' THEN 'sale_waste'
                                WHEN info.is_avocado AND fiscal_position.name::text ILIKE '%Export%' THEN 'sale_export'
                                WHEN info.is_avocado THEN 'sale_local'
                                ELSE 'sale_other'
                           END AS rubric,
                           -line.balance AS amount,
                           CASE WHEN move.move_type = 'out_refund' THEN -line.quantity ELSE line.quantity END AS quantity
                    FROM account_move_line line
                    JOIN account_move move ON move.id = line.move_id
                    JOIN product_info info ON info.product_id = line.product_id
                    LEFT JOIN account_fiscal_position fiscal_position ON fiscal_position.id = move.fiscal_position_id
                    WHERE move.state = 'posted'
                      AND move.move_type IN ('out_invoice', 'out_refund')
                      AND line.display_type = 'product'
                ),
                billed_lines AS (
                    SELECT bill_line.purchase_line_id, SUM(bill_line.balance) AS amount
                    FROM account_move_line bill_line
                    JOIN account_move bill ON bill.id = bill_line.move_id
                    WHERE bill.state = 'posted'
                      AND bill.move_type IN ('in_invoice', 'in_refund')
                      AND bill_line.purchase_line_id IS NOT NULL
                    GROUP BY bill_line.purchase_line_id
                ),
                -- Lignes de commandes d'achat : montant facturé, à défaut montant commandé
                -- (même règle que l'écran Achats d'avocats).
                purchases AS (
                    SELECT po.date_order::date AS date, po.company_id, line.product_id, po.partner_id,
                           NULL::integer AS account_move_id, po.id AS purchase_order_id,
                           {PURCHASE_RUBRIC_SQL} AS rubric,
                           -COALESCE(billed.amount, line.price_subtotal) AS amount,
                           CASE WHEN info.rubric IN {PURCHASE_KG_RUBRICS} THEN line.qty_received ELSE 0 END AS quantity
                    FROM purchase_order_line line
                    JOIN purchase_order po ON po.id = line.order_id
                    JOIN product_info info ON info.product_id = line.product_id
                    LEFT JOIN billed_lines billed ON billed.purchase_line_id = line.id
                    WHERE po.state IN ('purchase', 'done')
                      AND info.rubric IN {PURCHASE_RUBRICS}
                ),
                -- Factures fournisseurs sans commande d'achat (les autres sont déjà comptées par la commande).
                bills AS (
                    SELECT move.date, move.company_id, line.product_id, move.partner_id,
                           move.id AS account_move_id, NULL::integer AS purchase_order_id,
                           {PURCHASE_RUBRIC_SQL} AS rubric,
                           -line.balance AS amount,
                           CASE WHEN info.rubric NOT IN {PURCHASE_KG_RUBRICS} THEN 0
                                WHEN move.move_type = 'in_refund' THEN -line.quantity
                                ELSE line.quantity
                           END AS quantity
                    FROM account_move_line line
                    JOIN account_move move ON move.id = line.move_id
                    JOIN product_info info ON info.product_id = line.product_id
                    WHERE move.state = 'posted'
                      AND move.move_type IN ('in_invoice', 'in_refund')
                      AND line.display_type = 'product'
                      AND line.purchase_line_id IS NULL
                      AND info.rubric IN {PURCHASE_RUBRICS}
                ),
                -- Prix négociés saisis sur les factures d'export.
                export_costs AS (
                    SELECT move.date, move.company_id, NULL::integer AS product_id, move.partner_id,
                           move.id AS account_move_id, NULL::integer AS purchase_order_id,
                           cost.rubric,
                           -cost.amount AS amount,
                           0 AS quantity
                    FROM account_move move
                    CROSS JOIN LATERAL (VALUES
                        ('export_transport', move.export_transport_cost),
                        ('forwarder', move.export_forwarder_cost),
                        ('station', move.export_station_cost)
                    ) AS cost(rubric, amount)
                    WHERE move.state = 'posted'
                      AND move.move_type = 'out_invoice'
                      AND COALESCE(cost.amount, 0) <> 0
                ),
                -- Emballages consommés par les OF, moins ce que les déconstructions ont rendu.
                packaging AS (
                    SELECT layer.create_date::date AS date, layer.company_id, layer.product_id,
                           NULL::integer AS partner_id, NULL::integer AS account_move_id,
                           NULL::integer AS purchase_order_id,
                           'packaging' AS rubric,
                           layer.value AS amount,
                           0 AS quantity
                    FROM stock_valuation_layer layer
                    JOIN stock_move stock_move ON stock_move.id = layer.stock_move_id
                    JOIN stock_location src_location ON src_location.id = stock_move.location_id
                    JOIN stock_location dest_location ON dest_location.id = stock_move.location_dest_id
                    JOIN product_info info ON info.product_id = layer.product_id
                    WHERE info.rubric = 'packaging'
                      AND (src_location.usage = 'production') <> (dest_location.usage = 'production')
                ),
                -- Variation de la valeur du stock d'avocats (vrac, calibrés, déchets) : une hausse
                -- du stock réduit les charges, une baisse les augmente.
                stock_variation AS (
                    SELECT layer.create_date::date AS date, layer.company_id, layer.product_id,
                           NULL::integer AS partner_id, NULL::integer AS account_move_id,
                           NULL::integer AS purchase_order_id,
                           'stock_variation' AS rubric,
                           layer.value AS amount,
                           0 AS quantity
                    FROM stock_valuation_layer layer
                    JOIN product_info info ON info.product_id = layer.product_id
                    WHERE info.is_avocado_stock
                ),
                all_lines AS (
                    SELECT * FROM sales
                    UNION ALL SELECT * FROM purchases
                    UNION ALL SELECT * FROM bills
                    UNION ALL SELECT * FROM export_costs
                    UNION ALL SELECT * FROM packaging
                    UNION ALL SELECT * FROM stock_variation
                )
                SELECT ROW_NUMBER() OVER (ORDER BY all_lines.date, all_lines.rubric, all_lines.product_id) AS id,
                       all_lines.date,
                       all_lines.company_id,
                       company.currency_id,
                       CASE WHEN all_lines.rubric LIKE 'sale_%' THEN 'income'
                            WHEN all_lines.rubric = 'supplier_billed' THEN 'control'
                            ELSE 'cost'
                       END AS section,
                       all_lines.rubric,
                       all_lines.product_id,
                       all_lines.partner_id,
                       all_lines.account_move_id,
                       all_lines.purchase_order_id,
                       CASE WHEN all_lines.rubric = 'supplier_billed' THEN 0
                            ELSE ROUND(all_lines.amount::numeric, 2)
                       END AS amount,
                       CASE WHEN all_lines.rubric = 'supplier_billed' THEN ROUND(-all_lines.amount::numeric, 2)
                            ELSE 0
                       END AS control_amount,
                       all_lines.quantity
                FROM all_lines
                JOIN res_company company ON company.id = all_lines.company_id
            )
        """)
