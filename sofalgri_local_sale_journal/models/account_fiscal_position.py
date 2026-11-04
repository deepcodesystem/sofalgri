# -*- coding: utf-8 -*-
from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _is_export_position(self):
        """Position d'export : nom contenant « Export », comme la Synthèse des exports."""
        return any('export' in (position.sudo().name or '').lower() for position in self)
