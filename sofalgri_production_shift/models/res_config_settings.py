# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    production_shift_partner_ids = fields.Many2many(
        related='company_id.production_shift_partner_ids',
        readonly=False,
    )
