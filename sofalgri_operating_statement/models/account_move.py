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
