# -*- coding: utf-8 -*-
import logging
from datetime import date
from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _assign_receipt_lot_names(self, move_lines=None):
        """
        Attribue un nom de lot <séquence><Réf fournisseur><JJMMAAAA> aux lignes d'une réception.
        Un seul lot par produit et par réception : si une autre ligne du même produit
        a déjà un lot (ex. étiquette déjà imprimée), on le réutilise.
        Appelée à l'impression de l'étiquette palette et à la validation du transfert.
        """
        self.ensure_one()
        if self.picking_type_code != 'incoming':
            return

        if move_lines is None:
            move_lines = self.move_line_ids
        lines_to_process = move_lines.filtered(
            lambda ml: ml.product_id.tracking == 'lot' and not ml.lot_name and not ml.lot_id
        )
        if not lines_to_process:
            return

        if not self.partner_id or not self.partner_id.ref:
            _logger.error("Lot generation failed: Partner %s has no internal reference.", self.partner_id.name)
            raise UserError(
                _("Le fournisseur '%s' doit avoir une référence interne (champ Réf) pour générer le numéro de lot.") % (
                    self.partner_id.name))

        for product in lines_to_process.product_id:
            lines_for_this_product = lines_to_process.filtered(lambda l: l.product_id == product)

            # Lot déjà attribué à une autre palette du même produit dans cette réception
            existing_line = (self.move_line_ids - lines_to_process).filtered(
                lambda l: l.product_id == product and (l.lot_name or l.lot_id)
            )[:1]
            lot_name = existing_line.lot_name or existing_line.lot_id.name

            if not lot_name:
                sequence = self.env['ir.sequence'].next_by_code('lot.receipt.sequence') or '00'
                today_str = date.today().strftime('%d%m%Y')
                lot_name = f"{sequence}{self.partner_id.ref}{today_str}"
                _logger.info("Generated lot name '%s' for Product: %s", lot_name, product.display_name)

            lines_for_this_product.write({'lot_name': lot_name})
            _logger.info("Assigned lot '%s' to %d line(s) for this product.", lot_name, len(lines_for_this_product))

    def button_validate(self):
        # Gestion des réceptions (incoming) : lots des lignes qui n'en ont pas encore
        for picking in self.filtered(lambda p: p.picking_type_code == 'incoming'):
            _logger.info("-> Intercepting button_validate on picking ID %s", picking.id)
            picking._assign_receipt_lot_names(picking.move_line_ids.filtered(lambda ml: ml.quantity > 0))

        # Note: Les lots des OF sont générés par la séquence native stock.lot.serial (bouton « Générer »)

        return super(StockPicking, self).button_validate()
