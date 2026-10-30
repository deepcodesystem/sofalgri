# Contenu de models/account_move_line.py (version corrigée et simplifiée)

# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_truck_number = fields.Char(string='Matricule', help='Mettez le matricule de Camion de Livraison')

    # --- Facture transitaire : méthodes de rapport (aucun champ stocké) ---

    def _get_product_invoice_lines(self):
        return self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')

    @staticmethod
    def _get_packaging_label(packaging):
        return packaging.description_sale or packaging.name or ''

    def _get_forwarder_lines(self):
        """ Lignes de la facture transitaire : une par désignation (ex. « AVOCAT HASS »),
        avec plage de calibres, colis, types d'emballage, poids net et montant. """
        self.ensure_one()
        groups = {}
        for line in self._get_product_invoice_lines():
            product = line.product_id
            designation = product.description_sale or product.product_tmpl_id.name or line.name or ''
            variety = 'product_variety' in product._fields and product.product_variety
            if variety and variety.upper() not in designation.upper():
                designation = f"{designation} {variety}"
            group = groups.setdefault(designation, {
                'designation': designation,
                'calibres': [],
                'packaging_qty': 0.0,
                'packagings': [],
                'quantity': 0.0,
                'uom': line.product_uom_id.name,
                'amount': 0.0,
            })
            calibre = 'calibre' in product._fields and product.calibre
            if calibre and calibre not in group['calibres']:
                group['calibres'].append(calibre)
            label = self._get_packaging_label(line.product_packaging_id)
            if label and label not in group['packagings']:
                group['packagings'].append(label)
            group['packaging_qty'] += line.product_packaging_qty
            group['quantity'] += line.quantity
            group['amount'] += line.price_subtotal

        for group in groups.values():
            calibres = group['calibres']
            numbers = sorted(int(c) for c in calibres if c.strip().isdigit())
            if numbers and len(numbers) == len(calibres):
                group['calibre'] = f"CAL {numbers[0]}" if numbers[0] == numbers[-1] else f"CAL {numbers[0]}-{numbers[-1]}"
            else:
                group['calibre'] = ', '.join(calibres)
            group['packaging'] = ' & '.join(group['packagings'])
        return list(groups.values())

    def _get_shipping_summary(self):
        """ Colis, palettes et poids, mêmes règles que le pied de la facture client :
        220 colis par palette, 100 si l'emballage contient « PLASTIQUE » ;
        poids brut = net + colis × poids du colis vide + palettes × poids du type de colis. """
        self.ensure_one()
        lines = self._get_product_invoice_lines()
        packages_220 = packages_100 = 0.0
        for line in lines:
            if line.product_packaging_id and 'PLASTIQUE' in (line.product_packaging_id.name or '').upper():
                packages_100 += line.product_packaging_qty
            else:
                packages_220 += line.product_packaging_qty
        pallets = (int((packages_220 + 219) // 220) if packages_220 > 0 else 0) \
            + (int((packages_100 + 99) // 100) if packages_100 > 0 else 0)
        net_weight = sum(lines.mapped('quantity'))
        crates_tare = sum(l.product_packaging_qty * l.product_packaging_id.empty_weight for l in lines)
        pallet_weight = lines.product_packaging_id.package_type_id[:1].base_weight
        return {
            'packages': sum(lines.mapped('product_packaging_qty')),
            'pallets': pallets,
            'net_weight': net_weight,
            'gross_weight': net_weight + crates_tare + pallets * pallet_weight,
        }

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