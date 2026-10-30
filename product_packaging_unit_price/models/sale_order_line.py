# -*- coding: utf-8 -*-
from odoo import models, fields, api

from .export_report import colis_per_pallet, group_export_lines, shipping_summary

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_truck_number = fields.Char(string='Matricule', help='Mettez le matricule de Camion de Livraison')
    gross_weight = fields.Float(
        string='Poids brut total (kg)',
        digits='Stock Weight',
        default=24250.0,
        copy=False,
        help="Poids brut imprimé sur la facture pro forma, reporté sur la facture (saisie libre).",
    )
    proforma_unit_price = fields.Float(
        string='Prix unitaire pro forma',
        digits='Product Price',
        copy=False,
        help="Prix unitaire fictif (par unité de vente, ex. €/kg) imprimé sur la facture pro forma ; "
             "le montant et le total de la pro forma en sont déduits. Les prix réels ne sont pas imprimés.",
    )

    # --- Facture pro forma : méthodes de rapport (calculs communs dans export_report.py) ---

    def _get_product_order_lines(self):
        return self.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)

    def _get_export_lines(self):
        """ Lignes regroupées avec le prix FICTIF : montant = prix pro forma × poids net. """
        self.ensure_one()
        # Prix fictif obligatoire : contrôlé avant le rendu (ir_actions_report.py)
        lines = group_export_lines(self._get_product_order_lines(), 'product_uom_qty', 'product_uom')
        for line in lines:
            line['unit_price'] = self.proforma_unit_price
            line['amount'] = self.currency_id.round(self.proforma_unit_price * line['quantity'])
        return lines

    def _get_proforma_amount(self):
        self.ensure_one()
        return sum(line['amount'] for line in self._get_export_lines())

    def _get_proforma_amount_words_fr(self):
        return self.currency_id.with_context(lang='fr_FR').amount_to_text(self._get_proforma_amount())

    def _get_shipping_summary(self):
        self.ensure_one()
        return shipping_summary(self._get_product_order_lines(), 'product_uom_qty', self.gross_weight)

    def _get_export_city(self):
        """ Ville de l'entrepôt d'expédition (« A Larache, le … »). """
        self.ensure_one()
        warehouse = self.warehouse_id \
            or self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        return warehouse.partner_id.city or self.company_id.city or ''

    def _prepare_invoice(self):
        """
        Surcharge de la méthode standard pour y ajouter notre champ personnalisé.
        """
        # 1. Appeler la méthode originale pour récupérer toutes les valeurs standards
        invoice_vals = super(SaleOrder, self)._prepare_invoice()

        # 2. Ajouter notre champ personnalisé au dictionnaire de valeurs
        #    La clé du dictionnaire doit correspondre au nom technique du champ
        #    dans le modèle account.move.
        if self.delivery_truck_number:
            invoice_vals['delivery_truck_number'] = self.delivery_truck_number
        invoice_vals['gross_weight'] = self.gross_weight

        # 3. Retourner le dictionnaire modifié
        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_unit_package = fields.Float(
        string='Prix Unitaire/Colis',
        digits='Product Price',
    )
    pallet_qty = fields.Integer(
        string='Palettes',
        help="Nombre de palettes : le nombre de colis en est déduit (palettes × colis par palette du "
             "conditionnement), puis la quantité en kg.",
    )

    @api.onchange('pallet_qty', 'product_packaging_id')
    def _onchange_pallet_qty(self):
        """ Palettes → colis ; les kg suivent par le calcul natif (colis × contenance du conditionnement).
        Une saisie manuelle des colis ne recalcule pas les palettes. """
        if self.pallet_qty and self.product_packaging_id:
            self.product_packaging_qty = self.pallet_qty * colis_per_pallet(self.product_packaging_id)

    # ... (vos méthodes @api.onchange restent inchangées, elles sont correctes) ...
    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        """
        Au changement de conditionnement, on récupère le prix par défaut
        défini sur la fiche du conditionnement.
        """
        if self.product_packaging_id:
            # Récupérer le prix depuis le modèle product.packaging
            self.price_unit_package = self.product_packaging_id.unit_price_package
            # Mettre à jour le prix unitaire standard en conséquence
            if self.product_packaging_id.qty > 0:
                self.price_unit = self.product_packaging_id.unit_price_package / self.product_packaging_id.qty

    @api.onchange('price_unit_package')
    def _onchange_price_unit_package(self):
        """
        Si l'utilisateur modifie le prix par colis,
        on recalcule le prix unitaire standard.
        """
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            new_price_unit = self.price_unit_package / self.product_packaging_id.qty
            # Vérification pour éviter une boucle infinie de onchange
            if self.price_unit != new_price_unit:
                self.price_unit = new_price_unit

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        """
        Si l'utilisateur modifie le prix unitaire standard,
        on recalcule le prix par colis.
        """
        if self.product_packaging_id and self.product_packaging_id.qty > 0:
            new_price_unit_package = self.price_unit * self.product_packaging_id.qty
            # Vérification pour éviter une boucle infinie de onchange
            if self.price_unit_package != new_price_unit_package:
                self.price_unit_package = new_price_unit_package

    # --- MODIFICATION PRINCIPALE CI-DESSOUS ---
    def _prepare_invoice_line(self, **optional_values):
        """
        Surcharge de la méthode pour propager TOUS nos champs
        de la ligne de commande vers la ligne de facture.
        """
        # On appelle la méthode originale pour récupérer les valeurs par défaut
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)

        # On ajoute nos champs personnalisés
        res.update({
            'price_unit_package': self.price_unit_package,
            'product_packaging_id': self.product_packaging_id.id,
            'product_packaging_qty': self.product_packaging_qty,
        })
        return res