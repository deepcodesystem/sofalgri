from odoo import fields, models

EXPORT_STATUS = [
    ('in_transit', "En transit"),
    ('arrived', "Arrivé"),
]


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    export_carrier_id = fields.Many2one('res.partner', string="Transporteur")
    export_gps = fields.Char(string="GPS")
    export_type = fields.Char(string="TY")
    export_status = fields.Selection(EXPORT_STATUS, string="Statut")
    export_arrival_date = fields.Date(string="Date d'arrivée")
