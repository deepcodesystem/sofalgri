from odoo import api, fields, models

from .operating_report import CONTROL_RUBRICS, COST_RUBRICS, INCOME_RUBRICS

# Rubriques sans montant à signaler : frais pas encore saisis dans Odoo.
EXPECTED_COST_RUBRICS = ['harvest', 'farm_transport', 'packaging', 'station', 'forwarder', 'export_transport']


class OperatingStatement(models.TransientModel):
    _name = 'sofalgri.operating.statement'
    _description = "Compte d'exploitation par période"

    def _default_date_from(self):
        return self.env.company.season_start_date

    date_from = fields.Date(string="Du", default=_default_date_from)
    date_to = fields.Date(string="Au", default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string="Société", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    # Produits
    amount_sale_export = fields.Monetary(string="Ventes export", compute='_compute_statement')
    amount_sale_local = fields.Monetary(string="Ventes locales", compute='_compute_statement')
    amount_sale_waste = fields.Monetary(string="Ventes de déchets", compute='_compute_statement')
    amount_sale_other = fields.Monetary(string="Autres produits", compute='_compute_statement')
    amount_income = fields.Monetary(string="Total produits", compute='_compute_statement')
    qty_sale_export = fields.Float(string="Kg vendus à l'export", compute='_compute_statement')
    qty_sale_local = fields.Float(string="Kg vendus en local", compute='_compute_statement')
    qty_sale_waste = fields.Float(string="Kg de déchets vendus", compute='_compute_statement')
    qty_sold = fields.Float(string="Kg vendus (export + local)", compute='_compute_statement')

    # Charges (montants positifs)
    amount_avocado = fields.Monetary(string="Achat d'avocats", compute='_compute_statement')
    amount_waste_purchase = fields.Monetary(string="Achat de déchets fermes", compute='_compute_statement')
    amount_harvest = fields.Monetary(string="Récolte et chargement", compute='_compute_statement')
    amount_farm_transport = fields.Monetary(string="Transport ferme → station", compute='_compute_statement')
    amount_packaging = fields.Monetary(string="Emballages consommés", compute='_compute_statement')
    amount_station = fields.Monetary(string="Prestation station", compute='_compute_statement')
    amount_forwarder = fields.Monetary(string="Transitaire", compute='_compute_statement')
    amount_export_transport = fields.Monetary(string="Transport international", compute='_compute_statement')
    amount_other_cost = fields.Monetary(string="Autres frais", compute='_compute_statement')
    amount_stock_variation = fields.Monetary(
        string="Variation du stock d'avocats", compute='_compute_statement',
        help="Valeur du stock d'avocats (vrac, calibrés, déchets) en début de période moins en fin de période. "
             "Négatif : le stock a augmenté, une partie des achats et des emballages n'est pas encore vendue.")
    amount_cost = fields.Monetary(string="Total charges", compute='_compute_statement')
    qty_avocado = fields.Float(string="Kg d'avocats reçus", compute='_compute_statement')
    qty_waste_purchase = fields.Float(string="Kg de déchets fermes reçus", compute='_compute_statement')

    # Résultat et indicateurs
    amount_margin = fields.Monetary(string="Marge", compute='_compute_statement')
    margin_percent = fields.Float(string="Marge (% des produits)", digits=(12, 2), compute='_compute_statement')
    margin_per_kg = fields.Float(string="Marge par kg vendu", digits=(12, 2), compute='_compute_statement')
    cost_per_kg = fields.Float(string="Coût de revient par kg vendu", digits=(12, 2), compute='_compute_statement')
    cost_per_kg_net = fields.Float(
        string="Coût de revient net des déchets par kg vendu", digits=(12, 2), compute='_compute_statement')
    export_price_per_kg = fields.Float(string="Prix moyen export par kg", digits=(12, 2), compute='_compute_statement')
    local_price_per_kg = fields.Float(string="Prix moyen local par kg", digits=(12, 2), compute='_compute_statement')
    avocado_price_per_kg = fields.Float(
        string="Prix moyen d'achat par kg reçu", digits=(12, 2), compute='_compute_statement')
    missing_rubrics = fields.Char(string="Rubriques sans montant", compute='_compute_statement')

    # Contrôle des prix négociés
    amount_negotiated = fields.Monetary(string="Prix négociés (transport, transitaire, station)", compute='_compute_statement')
    amount_supplier_billed = fields.Monetary(string="Facturé par les fournisseurs", compute='_compute_statement')
    amount_supplier_gap = fields.Monetary(
        string="Reste à recevoir ou écart", compute='_compute_statement',
        help="Prix négociés moins factures reçues. Hors marge.")
    missing_destination_count = fields.Integer(string="Factures d'export sans destination", compute='_compute_statement')

    def _get_domain(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        return domain

    def _get_missing_destination_domain(self):
        return self._get_domain() + [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('fiscal_position_id.name', 'ilike', 'Export'),
            ('export_destination_id', '=', False),
            ('export_transport_cost', '=', 0),
        ]

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_statement(self):
        report = self.env['sofalgri.operating.report']
        labels = dict(COST_RUBRICS)
        for statement in self:
            amounts = {rubric: 0.0 for rubric, _label in INCOME_RUBRICS + COST_RUBRICS + CONTROL_RUBRICS}
            control_amount = 0.0
            quantities = dict.fromkeys(amounts, 0.0)
            if statement.company_id:
                for rubric, amount, quantity, control in report._read_group(
                        statement._get_domain(), ['rubric'], ['amount:sum', 'quantity:sum', 'control_amount:sum']):
                    control_amount += control or 0.0
                    amounts[rubric] = amount or 0.0
                    quantities[rubric] = quantity or 0.0

            negotiated = -(amounts['export_transport'] + amounts['forwarder'] + amounts['station'])
            statement.amount_negotiated = negotiated
            statement.amount_supplier_billed = control_amount
            statement.amount_supplier_gap = negotiated - control_amount
            statement.missing_destination_count = self.env['account.move'].search_count(
                statement._get_missing_destination_domain()) if statement.company_id else 0

            statement.amount_sale_export = amounts['sale_export']
            statement.amount_sale_local = amounts['sale_local']
            statement.amount_sale_waste = amounts['sale_waste']
            statement.amount_sale_other = amounts['sale_other']
            statement.qty_sale_export = quantities['sale_export']
            statement.qty_sale_local = quantities['sale_local']
            statement.qty_sale_waste = quantities['sale_waste']
            income = sum(amounts[rubric] for rubric, _label in INCOME_RUBRICS)
            qty_sold = quantities['sale_export'] + quantities['sale_local']
            statement.amount_income = income
            statement.qty_sold = qty_sold

            # Dans le détail, les charges sont négatives (effet sur le résultat).
            statement.amount_avocado = -amounts['avocado']
            statement.amount_waste_purchase = -amounts['waste_purchase']
            statement.amount_harvest = -amounts['harvest']
            statement.amount_farm_transport = -amounts['farm_transport']
            statement.amount_packaging = -amounts['packaging']
            statement.amount_station = -amounts['station']
            statement.amount_forwarder = -amounts['forwarder']
            statement.amount_export_transport = -amounts['export_transport']
            statement.amount_other_cost = -amounts['other_cost']
            statement.amount_stock_variation = -amounts['stock_variation']
            statement.qty_avocado = quantities['avocado']
            statement.qty_waste_purchase = quantities['waste_purchase']
            cost = -sum(amounts[rubric] for rubric, _label in COST_RUBRICS)
            statement.amount_cost = cost

            margin = income - cost
            statement.amount_margin = margin
            statement.margin_percent = 100 * margin / income if income else 0.0
            statement.margin_per_kg = margin / qty_sold if qty_sold else 0.0
            statement.cost_per_kg = cost / qty_sold if qty_sold else 0.0
            statement.cost_per_kg_net = (cost - amounts['sale_waste']) / qty_sold if qty_sold else 0.0
            statement.export_price_per_kg = (
                amounts['sale_export'] / quantities['sale_export'] if quantities['sale_export'] else 0.0)
            statement.local_price_per_kg = (
                amounts['sale_local'] / quantities['sale_local'] if quantities['sale_local'] else 0.0)
            statement.avocado_price_per_kg = (
                -amounts['avocado'] / quantities['avocado'] if quantities['avocado'] else 0.0)
            statement.missing_rubrics = ", ".join(
                labels[rubric] for rubric in EXPECTED_COST_RUBRICS if not amounts[rubric]) or False

    def action_open_details(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sofalgri_operating_statement.action_operating_report')
        action['domain'] = self._get_domain()
        action['context'] = {
            'pivot_row_groupby': ['section', 'rubric'],
            'pivot_column_groupby': ['date:month'],
            'pivot_measures': ['amount'],
        }
        return action
