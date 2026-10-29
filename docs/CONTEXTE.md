# Sofalgri — Contexte de l'instance Odoo

_Dernière mise à jour : 29/10/2026_

## Environnement

| Élément | Valeur |
|---|---|
| Version | Odoo 18.0 (Community probablement : compta via Odoo Mates + OCA, à confirmer) |
| Hébergement | VPS (hostname `sofalgri`) |
| Addons custom (serveur) | `/opt/GetapERP/extra-addons/GetapPRO/sofalgri` |
| Dépôt Git | github.com/deepcodesystem/sofalgri |
| Bases | **PROD** : `sofalgri`  ·  **TEST** : `sofalgri-test` |
| Accès Claude | MCP Odoo (module `odoo_mcp_manager`, Cybrosys) : accès aux **données** via l'ORM, pas au serveur ni aux fichiers |
| Sauvegardes | module `auto_database_backup` (Cybrosys) installé |
| Localisation | `l10n_ma` (Maroc) |

État au 29/10/2026 : **166 modules installés, listes identiques en PROD et TEST** (mêmes modules, mêmes versions).

## Modules custom (dépôt sofalgri)

| Module | Rôle | Version | Dépend de | Installé |
|---|---|---|---|---|
| `custom_lot_sequences` | Numéros de lot personnalisés (réceptions, OF) | 18.0.2.1.1 | stock, mrp | ✅ |
| `delivery_carrier_custom` | Personnalisations des modes de livraison | 18.0.1.0.0 | delivery, stock_delivery | ✅ |
| `package_packaging` | Affiche le conditionnement produit dans les colis | 18.0.1.0.0 | stock, product | ❌ |
| `picking_custom_addons` | Personnalisations des transferts de stock | 18.0.4.3.0 | stock, product | ✅ |
| `product_packaging_unit_price` | Prix unitaire par conditionnement (ventes et factures) | 18.0.6.3.0 | base, stock, sale_stock, sale_management, account | ✅ |
| `purchase_order_workflow` | Achat : facture fournisseur et paiement en espèces automatiques | 1.0 | purchase, account | ✅ |
| `sale_advance_payment` | Acomptes sur commandes de vente | 18.0.1.1.0 | sale_management, account | ✅ |
| `sale_order_template_custom` | Champs manquants sur les modèles de devis | 18.0.0.1 | sale_management | ✅ |
| `sales_margin` | Calcul de marges | 18.0.0.1 | sale_management, account | ❌ |
| `sofalgri_package_reports` | Rapports de colis (réception, remise en stock) | 18.0.8.4.0 | base, stock, purchase, product, picking_custom_addons, stock_move_packaging_qty | ✅ |

Dépendances inter-modules à respecter :
- `sofalgri_package_reports` → `picking_custom_addons` (custom) + `stock_move_packaging_qty` (OCA)

## Modules tiers par domaine

**Comptabilité** : `l10n_ma`, Odoo Mates (`om_account_asset`, `om_account_budget`, `om_fiscal_year`, `om_recurring_payments`), OCA rapprochement et relevés (`account_reconcile_oca`, `account_reconcile_model_oca`, `account_statement_base`, `account_statement_import_file`, `account_statement_import_file_reconcile_oca`), `account_cash_deposit`, `currency_rate_update`.

**Stock et conditionnement** (cœur des personnalisations) : `stock_move_packaging_qty`, `stock_packaging_calculator`, `product_packaging_calculator`, `stock_picking_back2draft`, `stock_picking_batch`, `stock_lot_production_date`, `stock_warehouse_calendar`, `stock_landed_costs`, `product_expiry`.

**Production** : `mrp`, `mrp_lot_number_propagation`, `mrp_lot_production_date`, `mrp_mass_production_order`, `mrp_production_back_to_draft`, `mrp_tag`, `mrp_bom_component_menu`, `mrp_warehouse_calendar`, `mrp_landed_costs`, `mrp_product_expiry`, `mrp_product_kanban` (Cybrosys).

**Ventes et achats** : `sale_management`, `sale_margin` (natif), `sale_stock_margin`, `purchase_advance_payment`, `sale_order_line_menu`, `purchase_order_line_menu`, `sale_partner_incoterm`, `delivery_carrier_partner`, `product_brand`, `edit_order_date` (Cybrosys), `sale_pdf_quote_builder`.

**RH et flotte** : `hr`, `hr_attendance`, `hr_holidays`, `hr_contract`, `hr_expense`, `hr_recruitment`, `hr_skills`, `fleet`, `stock_fleet`.

**Technique et UX** : `odoo_mcp_manager`, `auto_database_backup`, `password_security`, `auth_totp`, `impersonate_login`, `web_responsive`, `web_refresher`, `web_notify`, `web_json_editor`, `spreadsheet_oca` + tableaux de bord OCA.

## Points d'attention

1. **Deux modules du dépôt non installés** : `package_packaging` et `sales_margin`. À clarifier : abandonnés, en cours, ou remplacés ? `sales_margin` semble faire doublon avec `sale_margin` natif.
2. **Manifests à corriger** : `delivery_carrier_custom`, `picking_custom_addons` et `purchase_order_workflow` déclarent l'auteur « Odoo S.A. ». `purchase_order_workflow` a une version `1.0` au lieu de `18.0.x.y.z`.
3. **Auteurs variés** sur le custom (GetapPRO, WAHBI ACHRAF, Odoo S.A.) : vérifier l'origine de `custom_lot_sequences`.
4. **Base TEST alignée sur PROD** au 29/10/2026 : la vérifier de nouveau avant tout test important.

## Analyse du code (29/10/2026)

### Modèles hérités et champs clés

| Module | Modèle | Champs / comportement ajoutés |
|---|---|---|
| `custom_lot_sequences` | `stock.picking` | `button_validate` : sur une **réception**, génère un lot par produit `<séquence lot.receipt.sequence><partner.ref><JJMMAAAA>` ; bloque si le fournisseur n'a pas de **Réf** |
| `delivery_carrier_custom` | `delivery.carrier`, `stock.picking` | `driver_id` (chauffeur, res.partner), `matricule` (véhicule) |
| `picking_custom_addons` | `stock.move.line` | `net_weight` (libellé « Poids Brut »), `pallet_weight` (déf. 17), `crate_product_id` (article de catégorie **« Colis »**), `crate_weight` (related poids article), `crate_quantity`, `tare` = palette + nb caisses × poids caisse ; onchange : `quantity` = brut − tare ; à la validation, cumule poids/tare/nb caisses sur le colis de destination |
| | `stock.move` | `total_net_weight`, `total_tare` (sommes des lignes) |
| | `stock.quant.package` | `crate_quantity`, `tare`, `packaging_datetime` (remplace `pack_date` dans le formulaire) |
| | `stock.quant` | `crate_quantity` (related colis), `tare` |
| | rapport | « Étiquette de colis » (`stock.move.line`, A5) |
| `product_packaging_unit_price` | `product.packaging` | `unit_price_package`, `standard_price_package` (= prix produit × qté, modifiables), `description_sale` |
| | `sale.order.line`, `account.move.line` | `price_unit_package` ↔ `price_unit` synchronisés par onchange ; conditionnement propagé à la facture |
| | `sale.order`, `account.move` | `delivery_truck_number` (matricule camion, propagé à la facture) |
| | `res.partner` / `res.partner.bank` | `eori_number`, `tax_code`, `btw_identification`, `gln` / `code_swift`, `iban` |
| | rapport | **Remplace le tableau et le pied de la facture** : calibre, nb colis, emballage, poids net, prix/colis, nb palettes (220 colis/palette, 100 si emballage contient « PLASTIQUE »), GGN |
| `purchase_order_workflow` | `purchase.order` | `action_create_invoice` : date facture = date de confirmation, **facture validée** puis **paiement espèces** (1er journal `cash`) automatiquement |
| `sale_advance_payment` | `sale.order`, `account.payment` | Acomptes clients (fork du module OCA/ForgeFlow) : `account_payment_ids`, `amount_residual`, `advance_payment_status` ; assistant `account.voucher.wizard.sale` |
| `sale_order_template_custom` | `sale.order.template.line` | `product_packaging_id`, `product_packaging_qty`, reportés sur la ligne de devis |
| `sofalgri_package_reports` | `product.template` / `product.product` | `product_variety`, `product_classify` (classe 1/2), `global_gap` / `calibre` |
| | `res.company` / `stock.warehouse` | `number_export`, `number_ggn`, `number_onsa`, `coc_export` / `number_station`, `coc_station` |
| | `stock.quant` | `product_packaging_id`, `product_packaging_qty` (calculés depuis la dernière ligne de mouvement du colis) |
| | rapports | « Etiquette Palette » (colis et transfert, A5 paysage) : modèle choisi selon le **type de colis** nommé exactement « Palettes de réception » ou « Palettes de Livraison » |

### Constats techniques

- **Lots d'OF non gérés par le code actif** : la génération du lot produit fini (`<4 premiers caractères du lot composant>S<JJMMAAAA>`) est dans `stock_picking_old.py`, **non importé**. Le commentaire du code actif renvoie pourtant à `MrpProduction.button_mark_done()`. À vérifier : qui nomme les lots d'OF aujourd'hui (OCA `mrp_lot_number_propagation` ?). Fichiers morts : `stock_picking_old.py`, `stock_picking.py.old`.
- **Dépendances cachées** :
  - `picking_custom_addons` référence `sofalgri_package_reports.paperformat_a5_label` alors que c'est `sofalgri_package_reports` qui dépend de `picking_custom_addons` → dépendance circulaire ; une installation sur base vierge échouerait.
  - Le rapport facture de `product_packaging_unit_price` utilise `calibre` et `number_ggn` (définis dans `sofalgri_package_reports`) sans en dépendre.
  - Le rapport de `picking_custom_addons` utilise `product_variety` (même cas).
- **`package_packaging` est un doublon** de la partie `stock.quant` + vues de `sofalgri_package_reports` (même code, mêmes champs).
- **Fichiers `.pyc` versionnés** dans Git (`__pycache__/`), dont un `stock_quant_package.cpython-311.pyc` sans source.
- `purchase_order_workflow` : aucun contrôle si le journal espèces est absent (sortie silencieuse) ; facture validée sans relecture.

## Données (lecture MCP du 29/10/2026, PROD et TEST identiques)

**Entrepôt** : un seul, « Entrepôt de la Station » (`ST`, n° station 102696), réception en 1 étape, livraison directe, fabrication en 3 étapes (`pbm_sam` : prélèvement → fabrication → stockage produits finis).

**Emplacements internes** : `ST/Stock` et ses enfants **`Frigo 01` à `Frigo 04`**, `Zone de réception`, `Zone Emballages`, `Zone de stockage déchets` ; plus `ST/Pré-fabrication` et `ST/Post-fabrication`.

**Catégories de produits** : Tous / Avocats Calibrés à Vendre, Matière Première, Emballages (14 articles), Colis (1 article, utilisé pour la tare), Produits Déchets, Semi-fini (vide), Dépenses, Réceptionner ; et « Livraison » (racine, 8 articles).

**Nomenclatures de calibrage** (10, toutes en kg) :
- 3 modèles « AVOCAT HASS CALIBRÉS » (tmpl 49, 50, 84 — le 84 a une espace finale) + « AVOCAT HASS CALIBRÉS - LIDL » (97) ; variantes par attribut **Calibre 12 à 32**.
- Par modèle, une BoM **Caisse Carton 4KG** (880 kg) et une **Caisse Plastique 10KG** (1000 kg) ; une variante « déchets ferme » (tmpl 84).
- BoM « Déchets usines » (1 kg, type d'opération « Stocker les produits déchets »).
- `lot_number_propagation` désactivé sur toutes les BoM.

**Volumes** : 10 BoM ; **0 OF** sur les 30 derniers jours ; **1 794 lots** (561 vrac « Avocats pour export », 1 132 calibrés, 101 déchets).
Lots créés surtout de nov. 2025 à fév. 2026 ; derniers lots d'OF le 01/03/2026 ; dernières réceptions vrac le 19/06/2026 → **hors saison actuellement**.

**Nommage des lots constaté** :
- Réception vrac : `<séq><Réf fournisseur><JJMMAAAA>` (ex. `570BA19062026`) → conforme au code actif.
- OF (calibrés, déchets) : `<4 car.>S<JJMMAAAA>` (ex. `0044S01032026`) → format du code **absent du dépôt** (`stock_picking_old.py` non importé). Le code déployé sur le VPS diffère probablement de Git : **à vérifier avant la prochaine saison**.

**MCP** : TEST et PROD utilisent le **même jeton** ; la lecture seule PROD n'est donc garantie que par les règles côté Claude (`.claude/settings.json`), pas par le serveur.

## Métier Sofalgri

**Sofalgri Export** exporte des **avocats** à l'international.

### Flux principal

```
Achat avocats en vrac ──► Calibrage ──► Stockage en frigo ──► Livraison clients export
   (purchase)          (mrp : OF + BoM)     (stock, lots)      (sale, delivery, incoterms)
```

1. **Achat en vrac** : réception des avocats non calibrés auprès des fournisseurs.
2. **Calibrage** : géré comme de la **fabrication**. Un ordre de fabrication consomme le vrac et produit des avocats calibrés et conditionnés selon une nomenclature.
3. **Stockage en frigo** : conservation des produits calibrés, suivis par lot.
4. **Livraison** : expédition vers les clients à l'international.

### Lien probable avec les modules (à confirmer au fil des demandes)

| Étape | Modules concernés |
|---|---|
| Achat vrac | `purchase`, `purchase_order_workflow` (facture + paiement espèces auto), `purchase_advance_payment`, `custom_lot_sequences` (lots de réception) |
| Calibrage | `mrp`, `custom_lot_sequences` (lots d'OF), `mrp_lot_number_propagation`, `mrp_lot_production_date`, `mrp_mass_production_order` |
| Stockage frigo | `stock`, `product_expiry`, `stock_lot_production_date`, `picking_custom_addons`, `sofalgri_package_reports` |
| Conditionnement | `product_packaging_unit_price`, `stock_move_packaging_qty`, `stock_packaging_calculator` |
| Vente / export | `sale_management`, `sale_advance_payment`, `sale_partner_incoterm`, `delivery_carrier_custom`, `delivery_carrier_partner` |

_À préciser si utile : calibres et catégories produits, types de conditionnement (cartons, palettes), entrepôts/frigos, rôles des utilisateurs clés._
