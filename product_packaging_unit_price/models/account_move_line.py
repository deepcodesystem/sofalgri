# Contenu de models/account_move_line.py (version corrigée et simplifiée)

# -*- coding: utf-8 -*-
from odoo import models, fields, api

from .export_report import group_export_lines, shipping_summary

class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_truck_number = fields.Char(string='Matricule', help='Mettez le matricule de Camion de Livraison')
    gross_weight = fields.Float(
        string='Poids brut total (kg)',
        digits='Stock Weight',
        default=24250.0,
        copy=False,
        help="Poids brut imprimé sur la facture client et la facture transitaire (saisie libre).",
    )

    # --- Facture transitaire : méthodes de rapport (calculs communs dans export_report.py) ---

    def _get_product_invoice_lines(self):
        return self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')

    def _get_forwarder_lines(self):
        self.ensure_one()
        return group_export_lines(self._get_product_invoice_lines(), 'quantity', 'product_uom_id')

    def _get_shipping_summary(self):
        self.ensure_one()
        return shipping_summary(self._get_product_invoice_lines(), 'quantity', self.gross_weight)

    def _get_forwarder_city(self):
        """ Ville de l'entrepôt d'expédition (« A Larache, le … »). """
        self.ensure_one()
        warehouse = self.invoice_line_ids.sale_line_ids.order_id.warehouse_id[:1] \
            or self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        return warehouse.partner_id.city or self.company_id.city or ''

    def _get_amount_untaxed_words_fr(self):
        return self.currency_id.with_context(lang='fr_FR').amount_to_text(self.amount_untaxed)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_unit_package = fields.Float(
        string='Prix Unitaire (Colis)',
        digits='Product Price',
    )

    # On redéfinit les champs sans 'compute' pour qu'ils puissent recevoir
    # les valeurs transmises par le bon de commande.
    product_packaging_id = fields.Many2one(
        comodel_name='product.packaging',
        string="Packaging",
        domain="[('sales', '=', True), ('product_id','=',product_id)]",
        check_company=True)

    product_packaging_qty = fields.Float(
        string="Packaging Quantity")

    # --- MODIFICATION PRINCIPALE CI-DESSOUS ---
    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        """
        Au changement de conditionnement sur une facture.
        """
        # Si la ligne de facture provient d'un bon de commande, on ne fait rien.
        # On fait confiance aux valeurs déjà transmises pour ne pas écraser le prix.
        if self.sale_line_ids:
            return

        # Si on est sur une facture manuelle, on applique la logique d'aide à la saisie.
        if self.product_packaging_id:
            self.price_unit_package = self.product_packaging_id.unit_price_package
            if self.product_packaging_id.qty > 0:
                self.price_unit = self.product_packaging_id.unit_price_package / self.product_packaging_id.qty
        else:
            self.price_unit_package = 0.0

    @api.onchange('price_unit_package')
    def _onchange_price_unit_package(self):
        """
        Recalcule le prix unitaire si le prix par colis est modifié.
        """
        # On ajoute une condition pour ne rien faire si le packaging n'est pas défini
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            new_price_unit = self.price_unit_package / self.product_packaging_id.qty
            if self.price_unit != new_price_unit:
                self.price_unit = new_price_unit

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        """
        Recalcule le prix par colis si le prix unitaire est modifié.
        """
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            new_price_unit_package = self.price_unit * self.product_packaging_id.qty
            if self.price_unit_package != new_price_unit_package:
                self.price_unit_package = new_price_unit_package