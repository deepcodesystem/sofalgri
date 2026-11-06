from odoo import fields, models

PRODUCT_RUBRICS = [
    ('avocado', "Achat d'avocats"),
    ('harvest', "Récolte et chargement"),
    ('farm_transport', "Transport ferme → station"),
    ('packaging', "Emballage"),
    ('station', "Prestation station"),
    ('forwarder', "Transitaire"),
    ('export_transport', "Transport international"),
    ('other_cost', "Autres frais"),
    ('waste', "Vente de déchets"),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    operating_rubric = fields.Selection(
        PRODUCT_RUBRICS,
        string="Rubrique du compte d'exploitation",
        help="Ligne du compte d'exploitation où l'article est compté.\n"
             "Frais : lignes de commandes d'achat et de factures fournisseurs.\n"
             "Emballage : consommation par les OF.\n"
             "Vente de déchets : ventes en « Ventes de déchets », achats en « Achat de déchets fermes ».\n"
             "Vide : d'après la catégorie : « Matière Première » = achat d'avocats, « Emballages » = emballage, "
             "« Produits Déchets » = vente de déchets, « Dépenses » = autres frais, "
             "« Livraison » = transport international ; sinon l'article n'est pas compté dans les charges.",
    )
