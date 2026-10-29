# -*- coding: utf-8 -*-
from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def action_print_package_report(self):
        """
        Sur une réception, le lot doit figurer sur l'étiquette palette avant la validation :
        on l'attribue à la première impression.
        """
        for picking in self.picking_id:
            picking._assign_receipt_lot_names(self.filtered(lambda l: l.picking_id == picking))
        return super(StockMoveLine, self).action_print_package_report()
