from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_export_invoice = fields.Boolean(string="Facture d'export", compute='_compute_is_export_invoice')
    export_destination_id = fields.Many2one(
        'sofalgri.export.tariff', string="Destination", copy=False,
        domain="[('cost_type', '=', 'transport')]",
        help="Propose le transport international d'après les tarifs négociés.")
    export_transport_cost = fields.Monetary(
        string="Transport international", currency_field='company_currency_id',
        compute='_compute_export_transport_cost', store=True, readonly=False, copy=False)
    export_forwarder_cost = fields.Monetary(
        string="Transitaire", currency_field='company_currency_id',
        compute='_compute_export_forwarder_cost', store=True, readonly=False, copy=False)
    export_station_cost = fields.Monetary(
        string="Prestation station", currency_field='company_currency_id',
        compute='_compute_export_station_cost', store=True, readonly=False, copy=False)

    # Coût par camion (saison en cours, écran Synthèse des exports)
    export_goods_cost = fields.Monetary(
        string="Fruit et emballage", currency_field='company_currency_id', compute='_compute_export_truck_cost',
        help="Valeur en stock des avocats livrés : vrac et emballages consommés par les OF, au coût moyen d'Odoo.")
    export_approach_cost = fields.Monetary(
        string="Frais d'approche", currency_field='company_currency_id', compute='_compute_export_truck_cost',
        help="Récolte, chargement, transport ferme et autres frais de la saison, par kg reçu, × kg de la facture.")
    export_total_cost = fields.Monetary(
        string="Coût total", currency_field='company_currency_id', compute='_compute_export_truck_cost')
    export_cost_per_kg = fields.Float(string="Coût / kg", digits=(12, 2), compute='_compute_export_truck_cost')
    export_margin = fields.Monetary(
        string="Marge", currency_field='company_currency_id', compute='_compute_export_truck_cost',
        help="Facture hors taxes en dirhams, avoirs déduits, moins le coût total.")
    export_margin_percent = fields.Float(string="Marge (%)", digits=(12, 2), compute='_compute_export_truck_cost')

    @api.depends('move_type', 'fiscal_position_id')
    def _compute_is_export_invoice(self):
        for move in self:
            move.is_export_invoice = (
                move.move_type == 'out_invoice'
                and 'export' in (move.fiscal_position_id.name or '').lower()
            )

    def _is_export_cost_applicable(self):
        """ Coûts proposés sur les factures d'export de la saison en cours seulement. """
        self.ensure_one()
        start = self.company_id.season_start_date
        invoice_date = self.invoice_date or self.date
        return self.is_export_invoice and (not start or (invoice_date and invoice_date >= start))

    def _get_export_approach_rate(self):
        """ Frais d'approche de la saison par kg d'avocats reçu. """
        self.ensure_one()
        report = self.env['sofalgri.operating.report'].sudo()
        domain = [('company_id', '=', self.company_id.id)]
        if self.company_id.season_start_date:
            domain.append(('date', '>=', self.company_id.season_start_date))
        fees = report._read_group(
            domain + [('rubric', 'in', ['harvest', 'farm_transport', 'other_cost'])], [], ['amount:sum'])[0][0]
        kilos = report._read_group(domain + [('rubric', '=', 'avocado')], [], ['quantity:sum'])[0][0]
        return -(fees or 0.0) / kilos if kilos else 0.0

    @api.depends('invoice_line_ids.sale_line_ids', 'invoice_line_ids.quantity', 'amount_untaxed_signed',
                 'reversal_move_ids.state', 'reversal_move_ids.amount_untaxed_signed',
                 'export_transport_cost', 'export_forwarder_cost', 'export_station_cost')
    def _compute_export_truck_cost(self):
        rates = {}
        for move in self:
            values = dict.fromkeys((
                'export_goods_cost', 'export_approach_cost', 'export_total_cost',
                'export_cost_per_kg', 'export_margin', 'export_margin_percent'), 0.0)
            if move._is_export_cost_applicable():
                if move.company_id not in rates:
                    rates[move.company_id] = move._get_export_approach_rate()
                stock_moves = move.sudo().invoice_line_ids.sale_line_ids.move_ids.filtered(
                    lambda stock_move: stock_move.state == 'done')
                goods = -sum(stock_moves.stock_valuation_layer_ids.mapped('value'))
                approach = move.export_net_weight * rates[move.company_id]
                total = (goods + approach + move.export_transport_cost
                         + move.export_forwarder_cost + move.export_station_cost)
                refunds = move.reversal_move_ids.filtered(
                    lambda refund: refund.move_type == 'out_refund' and refund.state == 'posted')
                revenue = move.amount_untaxed_signed + sum(refunds.mapped('amount_untaxed_signed'))
                values.update({
                    'export_goods_cost': goods,
                    'export_approach_cost': approach,
                    'export_total_cost': total,
                    'export_cost_per_kg': total / move.export_net_weight if move.export_net_weight else 0.0,
                    'export_margin': revenue - total,
                    'export_margin_percent': 100 * (revenue - total) / revenue if revenue else 0.0,
                })
            move.update(values)

    @api.depends('export_destination_id')
    def _compute_export_transport_cost(self):
        for move in self:
            move.export_transport_cost = move.export_destination_id.amount

    @api.depends('move_type', 'fiscal_position_id', 'date', 'invoice_date')
    def _compute_export_forwarder_cost(self):
        tariff = self.env['sofalgri.export.tariff']._get_amount('forwarder')
        for move in self:
            move.export_forwarder_cost = tariff if move._is_export_cost_applicable() else 0.0

    @api.depends('move_type', 'fiscal_position_id', 'date', 'invoice_date',
                 'invoice_line_ids.quantity', 'invoice_line_ids.product_id')
    def _compute_export_station_cost(self):
        rate = self.env['sofalgri.export.tariff']._get_amount('station')
        for move in self:
            if not move._is_export_cost_applicable():
                move.export_station_cost = 0.0
                continue
            lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == 'product' and line.product_id.is_storable)
            move.export_station_cost = sum(lines.mapped('quantity')) * rate
