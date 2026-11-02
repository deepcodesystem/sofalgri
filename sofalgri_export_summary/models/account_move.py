from odoo import api, fields, models

from .stock_picking import EXPORT_STATUS


class AccountMove(models.Model):
    _inherit = 'account.move'

    export_current_season = fields.Boolean(
        string="Saison en cours", compute='_compute_export_current_season', search='_search_export_current_season')

    export_station = fields.Char(string="Station", compute='_compute_export_shipping')
    export_gps = fields.Char(string="GPS", compute='_compute_export_shipping')
    export_truck = fields.Char(string="Camion", compute='_compute_export_shipping')
    export_load_date = fields.Date(string="Date de chargement", compute='_compute_export_shipping')
    export_type = fields.Char(string="TY", compute='_compute_export_shipping')
    export_carrier = fields.Char(string="Transporteur", compute='_compute_export_shipping')
    export_plate = fields.Char(string="Matricule", compute='_compute_export_shipping')
    export_status = fields.Selection(EXPORT_STATUS, string="Statut", compute='_compute_export_shipping')
    export_arrival_date = fields.Date(string="Date d'arrivée", compute='_compute_export_shipping')

    export_net_weight = fields.Float(string="Poids net (kg)", compute='_compute_export_net_weight')
    export_invoice_rate = fields.Float(string="Cours facture", digits=(12, 3), compute='_compute_export_invoice_rate')

    export_claim = fields.Char(string="Claim", compute='_compute_export_claim')
    export_claim_amount = fields.Monetary(string="Montant claim", compute='_compute_export_claim')

    export_payment1_amount = fields.Monetary(string="Paiement 1", compute='_compute_export_payments')
    export_payment1_date = fields.Date(string="Date P1", compute='_compute_export_payments')
    export_payment1_rate = fields.Float(string="Cours P1", digits=(12, 3), compute='_compute_export_payments')
    export_payment2_amount = fields.Monetary(string="Paiement 2", compute='_compute_export_payments')
    export_payment2_date = fields.Date(string="Date P2", compute='_compute_export_payments')
    export_payment2_rate = fields.Float(string="Cours P2", digits=(12, 3), compute='_compute_export_payments')
    export_payment3_amount = fields.Monetary(string="Paiement 3", compute='_compute_export_payments')
    export_payment3_date = fields.Date(string="Date P3", compute='_compute_export_payments')
    export_payment3_rate = fields.Float(string="Cours P3", digits=(12, 3), compute='_compute_export_payments')

    @api.depends('invoice_date')
    @api.depends_context('company')
    def _compute_export_current_season(self):
        start = self.env.company.season_start_date
        for move in self:
            move.export_current_season = bool(move.invoice_date and (not start or move.invoice_date >= start))

    def _search_export_current_season(self, operator, value):
        start = self.env.company.season_start_date
        if (operator == '=') == bool(value):
            return [('invoice_date', '>=', start)] if start else []
        return ['|', ('invoice_date', '=', False), ('invoice_date', '<', start)] if start else [('id', '=', 0)]

    def _get_export_picking(self):
        """ Première livraison validée de la commande à l'origine de la facture. """
        self.ensure_one()
        pickings = self.sudo().invoice_line_ids.sale_line_ids.order_id.picking_ids
        return pickings.filtered(
            lambda picking: picking.picking_type_code == 'outgoing' and picking.state == 'done'
        ).sorted('date_done')[:1]

    @api.depends('invoice_line_ids.sale_line_ids', 'delivery_truck_number')
    def _compute_export_shipping(self):
        for move in self:
            picking = move._get_export_picking()
            move.export_station = picking.picking_type_id.warehouse_id.partner_id.name
            move.export_gps = picking.export_gps
            move.export_truck = picking.truck_reference
            move.export_load_date = picking.date_done and fields.Datetime.context_timestamp(move, picking.date_done).date()
            move.export_type = picking.export_type
            move.export_carrier = picking.carrier_id.partner_id.name
            move.export_plate = move.delivery_truck_number or picking.matricule
            move.export_status = picking.export_status
            move.export_arrival_date = picking.export_arrival_date

    @api.depends('invoice_line_ids.quantity', 'invoice_line_ids.product_uom_id')
    def _compute_export_net_weight(self):
        weight_category = self.env.ref('uom.product_uom_categ_kgm')
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda line: line.product_uom_id.category_id == weight_category)
            move.export_net_weight = sum(lines.mapped('quantity'))

    @api.depends('invoice_currency_rate')
    def _compute_export_invoice_rate(self):
        for move in self:
            move.export_invoice_rate = 1 / move.invoice_currency_rate if move.invoice_currency_rate else 0.0

    @api.depends('reversal_move_ids.state', 'reversal_move_ids.amount_total')
    def _compute_export_claim(self):
        for move in self:
            refunds = move.reversal_move_ids.filtered(
                lambda refund: refund.move_type == 'out_refund' and refund.state == 'posted')
            move.export_claim = "CLAIM" if refunds else "NO CLAIM"
            move.export_claim_amount = -sum(refunds.mapped('amount_total'))

    @api.depends('line_ids.matched_credit_ids')
    def _compute_export_payments(self):
        for move in self:
            receivable_lines = move.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
            partials = receivable_lines.matched_credit_ids.filtered(
                lambda partial: partial.credit_move_id.move_id.move_type != 'out_refund'
            ).sorted(lambda partial: (partial.max_date, partial.id))
            # Au-delà de trois paiements, les suivants sont cumulés avec le troisième.
            for index, group in enumerate((partials[:1], partials[1:2], partials[2:]), start=1):
                amount = sum(group.mapped('debit_amount_currency'))
                move[f'export_payment{index}_amount'] = amount
                move[f'export_payment{index}_date'] = group[-1:].max_date
                move[f'export_payment{index}_rate'] = sum(group.mapped('amount')) / amount if amount else 0.0
