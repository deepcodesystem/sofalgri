from odoo import fields, models


class ExportTariff(models.Model):
    _name = 'sofalgri.export.tariff'
    _description = "Tarif négocié d'export"
    _order = 'cost_type, sequence, name, id'

    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    name = fields.Char(string="Destination ou libellé", required=True)
    cost_type = fields.Selection([
        ('transport', "Transport international (dh par camion)"),
        ('forwarder', "Transitaire (dh par camion)"),
        ('station', "Station (dh par kg exporté)"),
    ], string="Type", required=True, default='transport')
    amount = fields.Float(string="Tarif (dh)", digits=(16, 2), required=True)

    def _get_amount(self, cost_type):
        """ Tarif en vigueur pour le transitaire ou la station (0 si aucun tarif actif). """
        tariff = self.sudo().search([('cost_type', '=', cost_type)], limit=1)
        return tariff.amount
