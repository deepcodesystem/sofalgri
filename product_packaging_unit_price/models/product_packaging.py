# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
    _description = 'Prix de Vente par Conditionnement'

    # Le champ 'qty' existe déjà dans le modèle de base 'product.packaging'
    # et représente la quantité de produit dans ce conditionnement.

    unit_price_package = fields.Float(
        string='Prix de Vente du Conditionnement',
        compute='_compute_packaging_prices',
        store=True,
        readonly=False,
        digits='Product Price',
        help="Prix de vente calculé pour ce conditionnement (Prix de Vente du Produit * Quantité). Peut être modifié manuellement.",
    )
    standard_price_package = fields.Float(
        string='Coût du Conditionnement',
        compute='_compute_packaging_prices',
        store=True,
        readonly=False,
        digits='Product Price',
        help="Coût calculé pour ce conditionnement (Coût du Produit * Quantité). Peut être modifié manuellement.",
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        related='product_id.currency_id', # Utiliser 'related' est plus direct
        store=True,
    )

    # Un champs supplémentaire pour le rapport de facture
    description_sale = fields.Char(
        string='Sale Description',
        help = 'Mettez la description qui sera affiché sur la facture.'
    )

    # Saisie des commandes en palettes et nombre de palettes des factures
    pallet_packaging_qty = fields.Integer(
        string='Colis par palette',
        help="Nombre de colis de ce conditionnement sur une palette (ex. 220 cartons 4 kg, 100 caisses "
             "plastique 10 kg). Sert à calculer les colis depuis le nombre de palettes de la commande "
             "et le nombre de palettes des factures.",
    )

    # Tare d'un colis pour le poids brut de la facture
    empty_weight = fields.Float(
        string='Poids du colis vide (kg)',
        digits='Stock Weight',
        help="Poids de l'emballage vide (carton, caisse). Poids brut de la facture = "
             "poids net + nb colis × poids du colis vide + nb palettes × poids d'une palette.",
    )

    @api.depends('qty', 'product_id.list_price', 'product_id.standard_price')
    def _compute_packaging_prices(self):
        """
        Calcule automatiquement le coût et le prix de vente
        d'un conditionnement en se basant sur les prix du produit
        et la quantité contenue dans le conditionnement.
        """
        for packaging in self:
            if packaging.product_id and packaging.qty > 0:
                packaging.standard_price_package = packaging.product_id.standard_price * packaging.qty
                packaging.unit_price_package = packaging.product_id.list_price * packaging.qty
            else:
                # Si pas de produit ou de quantité, les prix sont à zéro
                packaging.standard_price_package = 0.0
                packaging.unit_price_package = 0.0