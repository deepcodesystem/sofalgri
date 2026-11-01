# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    _description = 'Add fields for detailed weight calculation'

    # --- Champs existants pour le calcul final ---
    net_weight = fields.Float(
        string="Poids Brut",
        digits='Stock Weight',
        help="Poids brut total mesuré sur la balance."
    )
    tare = fields.Float(
        string="Poids Tare",
        digits='Stock Weight',
        readonly=True,
        compute='_compute_tare',
        store=True,
        help="Poids total à vide (palette + caisses)."
    )

    # --- Nouveaux champs pour le calcul de la tare ---
    pallet_weight = fields.Float(
        string="Poids Palette",
        digits='Stock Weight',
        default=17.0,
        help="Poids de la palette vide."
    )
    crate_product_id = fields.Many2one(
        'product.product',
        string='Colis',
        domain="[('categ_id.name', '=', 'Colis')]",  # <-- DOMAIN AJOUTÉ ICI
        options="{'no_create': True, 'no_create_edit':True}",
        help="Sélectionnez le type de caisse utilisé (doit être un article avec un poids défini)."
    )

    # --- CHAMP AMÉLIORÉ ---
    # On remplace l'ancien champ Float et sa méthode onchange par un champ related.
    # C'est plus simple, plus rapide et plus fiable.
    crate_weight = fields.Float(
        string="Poids Caisse",
        related='crate_product_id.weight',  # <-- LA MAGIE EST ICI
        store=True,  # Important pour que le champ 'tare' puisse dépendre de lui
        readonly=True,
        digits='Stock Weight',
        help="Poids d'une seule caisse vide. Rempli automatiquement à la sélection de l'article caisse."
    )

    crate_quantity = fields.Float(
        string="Quantité Colis",
        default=0.0,
        help="Nombre total de caisses sur la palette."
    )

    # --- MÉTHODE ONCHANGE SUPPRIMÉE ---
    # La méthode _onchange_crate_product_id n'est plus nécessaire !

    @api.depends('pallet_weight', 'crate_quantity', 'crate_weight')
    def _compute_tare(self):
        """
        Calcule le poids total de la tare.
        Cette méthode fonctionne maintenant parfaitement car elle dépend de crate_weight
        qui est maintenant un champ 'related' et 'stored'.
        """
        for line in self:
            line.tare = line.pallet_weight + (line.crate_quantity * line.crate_weight)

    @api.onchange('net_weight', 'tare')
    def _onchange_weight_to_quantity(self):
        """
        Calcule la quantité finale (qty_done) à partir du poids SI le poids net est saisi.
        Sinon, elle ne fait rien pour préserver le comportement standard d'Odoo.
        """
        # On ne lance le calcul que si l'utilisateur a saisi un poids net.
        if self.net_weight > 0:
            if self.net_weight > self.tare:
                self.quantity = self.net_weight - self.tare
            else:
                self.quantity = 0.0
        # Si self.net_weight est 0, on ne met pas de "else".
        # En ne faisant rien, on laisse la valeur par défaut d'Odoo (la quantité demandée)
        # ou la valeur saisie manuellement par l'utilisateur.
        return


    def _action_done(self):
        """
        On hérite de la méthode pour copier les informations de la ligne (caisses, poids)
        vers le colis de destination.
        Les poids sont accumulés pour gérer plusieurs ajouts au même colis.
        """
        res = super(StockMoveLine, self)._action_done()

        for line in self:
            # On vérifie si un colis de destination est défini
            if line.result_package_id:
                package = line.result_package_id

                # La palette ne pèse qu'une fois, même avec plusieurs lignes sur le même colis (palette mixte)
                line_tare = line.tare - line.pallet_weight if package.tare else line.tare

                # Préparation des valeurs à écrire
                vals_to_write = {
                    # On ACCUMULE le poids net du produit (net_weight)
                    'shipping_weight': package.shipping_weight + line.net_weight,
                    # On ACCUMULE le poids de la tare
                    'tare': package.tare + line_tare,
                    'packaging_datetime': fields.Datetime.now(),
                }

                # Pour la quantité de caisses, la dernière opération "gagne", ce qui est logique
                if line.crate_quantity > 0:
                    vals_to_write['crate_quantity'] = line.crate_quantity

                # On écrit toutes les valeurs en une seule fois pour la performance
                package.write(vals_to_write)

        return res

    def action_print_package_report(self):
       return self.env.ref('picking_custom_addons.action_report_package').report_action(self)
