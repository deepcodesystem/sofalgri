from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    season_start_date = fields.Date(string="Début de saison")
