# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    production_shift_partner_ids = fields.Many2many(
        'res.partner',
        'res_company_production_shift_partner_rel',
        'company_id', 'partner_id',
        string="Destinataires du rapport de shift",
        help="Contacts qui reçoivent par email le rapport des palettes produites à la fin de chaque shift.",
    )
