# Sofalgri — Journal des interventions

Format d'une entrée : date · demande · ce qui a été fait · base(s) concernée(s) · modules/modèles touchés · commit éventuel.
Les entrées les plus récentes en haut.

---

## 2026-10-30 · Facture pro forma depuis la commande de vente
- Demande : mettre en place la facture pro forma, sur le modèle `proformat.pdf` (identique au modèle de la facture transitaire, avec la colonne PRIX UNITAIRE). Choix de l'utilisateur : même mise en page, imprimée depuis la commande de vente ; prix unitaire et montants **fictifs** (saisis), pas les prix réels.
- Fait : `product_packaging_unit_price` 18.0.6.8.0 :
  - rapport « Facture pro forma » (menu Imprimer de la commande de vente), titre « FACTURE PROFORMA N° : <commande> », une ligne par produit avec un **prix unitaire fictif** : champ « Prix unitaire pro forma » (`proforma_unit_price`) sur la commande, montant = prix fictif × poids net, total et somme en lettres déduits ; les prix réels ne sont jamais imprimés ; impression refusée si le prix fictif est vide (18.0.6.8.1 : contrôle dans `ir.actions.report._render`, avant le rendu, pour afficher un simple avertissement au lieu d'une erreur serveur QWeb) ; date de la commande, ville de l'entrepôt de la commande, incoterm et lieu, matricule, adresse de livraison, banque de la société, conditions de paiement ;
  - mise en page commune `report_export_document_body` utilisée par la facture transitaire (sans prix unitaire) et la pro forma ; calculs communs dans `models/export_report.py` (`group_export_lines`, `shipping_summary`), utilisés par `account.move` et `sale.order` ;
  - champ `gross_weight` « Poids brut total (kg) » sur la commande (défaut 24 250, sous le matricule), reporté sur la facture à la facturation.
- Bases : aucune requête.
- Modules/modèles : `product_packaging_unit_price` · `sale.order`, `account.move`, rapports facture transitaire et pro forma.
- Commit : `e30983b` sur `feat/facture-proforma` (poussé) ; correctif de l'avertissement en 18.0.6.8.1.
- Déploiement : nouveaux champs stockés sur `sale.order` (`gross_weight`, `proforma_unit_price`) → mise à jour en ligne de commande sur **les deux bases** avant redémarrage.

## 2026-10-30 · Facture : poids brut en saisie libre (défaut 24 250 kg)
- Demande : le poids brut des factures client doit être saisi librement, avec 24 250 kg par défaut (au lieu du calcul net + tares).
- Fait : `product_packaging_unit_price` 18.0.6.7.0 : champ `gross_weight` « Poids brut total (kg) » sur `account.move` (défaut 24 250, non copié), dans le formulaire de la facture client sous le matricule ; imprimé tel quel sur la facture client et la facture transitaire (le calcul par tares est retiré des deux rapports). Le champ « Poids du colis vide » des conditionnements n'est plus utilisé (conservé).
- À noter : à l'installation, les factures existantes reçoivent la valeur par défaut 24 250.
- Bases : aucune requête.
- Modules/modèles : `product_packaging_unit_price` · `account.move`, rapports facture et facture transitaire.
- Commit : `6acf633` sur `feat/poids-brut-saisi`. **Validé en TEST** ; PR deepcodesystem/sofalgri#16 **fusionnée** dans `18.0` (`1c5e020`).
- Déploiement : nouveau champ stocké sur `account.move` → mise à jour en ligne de commande sur **les deux bases** avant redémarrage.

## 2026-10-30 · Liste des OF : colonnes « Vrac consommé » (avec total) et « Frigo »
- Demande (client) : afficher dans la liste des OF la quantité du composant (vrac « Avocats pour export »), puis aussi le frigo. Choix de l'utilisateur : avec total en bas de liste (champ stocké).
- Frigo : `mrp_production_storage` 18.0.1.2.2 : colonne « Frigo de stockage » (`storage_location_id`, champ existant, lecture seule car la liste est en édition multiple) dans la liste des OF.
- Fait : `mrp_component_lot_check` 18.0.1.2.0 : champ calculé stocké `component_lot_qty` « Vrac consommé » sur `mrp.production` (somme des quantités des mouvements de composants suivis par lot, hors annulés ; prévu/réservé tant que l'OF n'est pas terminé), agrégé en somme ; colonne ajoutée après l'unité dans la liste des OF (`mrp.mrp_production_tree_view`), avec total, triable et groupable. Calculé pour tous les OF existants à la mise à jour.
- Bases : lecture seule TEST (vue liste des OF).
- Modules/modèles : `mrp_component_lot_check`, `mrp_production_storage` · `mrp.production` (liste).
- Commit : `fd3460b` et `22c2ffe` sur `feat/vrac-consomme-liste-of`. **Validé en TEST** ; PR deepcodesystem/sofalgri#15 **fusionnée** dans `18.0` (`ed9c6c9`).
- Déploiement : nouveau champ stocké sur `mrp.production` → mise à jour en ligne de commande sur **les deux bases** avant redémarrage.

## 2026-10-30 · OF : poids réel de vrac obligatoire dans le popup des lots
- Demande : l'opérateur a laissé la quantité de vrac de la nomenclature (880 kg) au lieu du poids réel (897 kg calibre 24, 904 kg calibre 22) ; corriger et éviter que ça se reproduise.
- Constat (PROD, lecture seule) : WH/MOF/03914 (calibre 24) = E001 771 + E002 109 ; WH/MOF/03915 (calibre 22) = E002 704 + E003 176 ; lot `001FE29102026` ; E001 et E002 vides, E003 632 kg entièrement réservés par un autre OF. Correction indiquée à l'utilisateur (en PROD, par lui) : déverrouiller chaque OF, +17 kg et +24 kg sur E003, reverrouiller ; puis vérifier les palettes de l'OF qui réservait E003.
- Fait : `mrp_component_lot_check` 18.0.1.1.0 : dans le popup « Vérifier les lots des composants », champ « Poids réel consommé » obligatoire (OF avec un seul composant suivi par lot), « Poids prévu (nomenclature) » affiché ; la saisie reporte l'écart sur la dernière palette ; la validation refuse si le total des palettes diffère du poids réel ; les mouvements du vrac passent en consommation manuelle (`picked`, `manual_consumption`) pour qu'Odoo ne les recalcule pas d'après la nomenclature ; poids réel et prévu tracés dans le fil de l'OF.
- Bases : lecture seule PROD (mouvements et lignes des OF 03914 / 03915, quants des palettes E001–E003).
- Modules/modèles : `mrp_component_lot_check` · `mrp.component.lot.wizard`.
- Commit : `9a40a8b` sur `feat/poids-reel-vrac`. **Validé en TEST** ; PR deepcodesystem/sofalgri#14 **fusionnée** dans `18.0` (`b38c520`) ; module mis à jour sur les deux bases par l'utilisateur.
- Déploiement : nouveau champ stocké sur le modèle du popup → règle du serveur partagé (mise à jour en ligne de commande sur les deux bases avant redémarrage).

## 2026-10-30 · Étiquette palette de sortie : pied supprimé
- Demande : retirer du bas de l'étiquette palette des OF la référence de l'OF (« OF WH/MOF/03914 ») et « Imprimé le … par <utilisateur> ».
- Fait : `mrp_production_storage` 18.0.1.2.1 : pied de l'étiquette `report_production_pallet` supprimé (et son style). L'étiquette de réception (`picking_custom_addons`) garde son pied (caisse, palette, impression).
- Bases : aucune requête.
- Modules/modèles : `mrp_production_storage` · rapport `report_production_pallet`.
- Commit : `9a59857` sur `fix/etiquette-palette-sans-pied`. **Validé en TEST** ; PR deepcodesystem/sofalgri#13 **fusionnée** dans `18.0` (`c5c44b2`).

## 2026-10-30 · Facture transitaire (sans prix unitaire)
- Demande : mettre en place une facture destinée au transitaire, sur le modèle `Facture N 802025 WESTFALIA FRUIT GMBH TR.pdf`, sans prix unitaire (confidentialité).
- Modèle : une ligne regroupée « Fruit Avocat HASS » / « CAL 12-32 » / colis / « CAISSES EN CARTON 4 KGS & CAISSES EN PLASTIQUE 10 KGS » / poids net / prix moyen / montant ; somme en lettres ; GGN ; poids brut et net, palettes, colis ; incoterm, matricule, lieu de destination ; règlement et banque.
- Choix de l'utilisateur : montants gardés (ligne, total, somme en lettres), une ligne par produit, ville = ville de l'adresse de l'entrepôt (TEST : contact « HIPECA », Larache), pas de signature / cachet (futur module dédié pour tous les rapports).
- Fait : `product_packaging_unit_price` 18.0.6.6.0 : rapport « Facture transitaire » (menu Imprimer de la facture, layout externe de la société), sans colonne prix unitaire ; méthodes `account.move` sans champ stocké : `_get_forwarder_lines` (regroupement par désignation = description de vente + variété, plage de calibres « CAL min-max », colis, emballages distincts joints par « & », poids net, montant), `_get_shipping_summary` (colis, palettes 220 / 100, poids net et brut, mêmes règles que la facture client), `_get_forwarder_city`, `_get_amount_untaxed_words_fr`. Facture client inchangée.
- Bases : lecture seule TEST (entrepôt et son adresse, variantes calibrées : `calibre` numérique, `product_variety` « HASS », description de vente « AVOCAT »).
- Modules/modèles : `product_packaging_unit_price` · `account.move`, rapport `report_forwarder_invoice`.
- Commit : `696cdc6` sur `feat/facture-transitaire`. **Validé en TEST** ; PR deepcodesystem/sofalgri#12 **fusionnée** dans `18.0` (`7e57456`).
- Déploiement : aucun nouveau champ stocké, mise à jour normale du module (pas de risque pour la PROD au redémarrage).

## 2026-10-30 · Incident : PROD en erreur après bascule du serveur sur la branche
- Symptôme : mise à jour de `product_packaging_unit_price` 18.0.6.5.0 en TEST impossible (`column res_company.pallet_weight does not exist`) ; la **PROD était aussi en erreur** (même message, vérifié par lecture MCP).
- Cause : TEST et PROD partagent le **même service Odoo et le même dossier d'addons**. Après `git pull` de la branche et redémarrage, les deux bases chargent un code qui déclare des colonnes encore absentes ; `res.company` étant lue partout (et par le bouton de mise à jour lui-même), tout échoue.
- Rétablissement (utilisateur) : serveur remis sur `18.0`, redémarrage ; PROD vérifiée OK (lecture `res.company`).
- Correction : `product_packaging_unit_price` 18.0.6.5.1 : suppression du champ société ; poids d'une palette = champ natif « Poids » (`base_weight`) du type de colis du conditionnement (« Palettes de Livraison »).
- **Règle de déploiement (serveur partagé)** : toute branche qui ajoute un champ stocké sur un modèle utilisé en PROD (ici `product.packaging.empty_weight`) doit être suivie, **avant le redémarrage**, d'une mise à jour en ligne de commande du module sur **les deux bases** (`-u <module> --stop-after-init`). À terme : un service Odoo séparé pour TEST.

## 2026-10-30 · Facture : poids brut total calculé
- Demande : le « Poids Brut Total » du pied de facture était écrit en dur (`24 250,00`) ; le calculer.
- Choix de l'utilisateur : poids net + tares (colis vides + palettes), tares saisies par l'utilisateur.
- Fait : `product_packaging_unit_price` 18.0.6.5.0 : champ « Poids du colis vide (kg) » (`empty_weight`) sur le conditionnement (formulaire et liste) ; pied de facture : poids brut = poids net total + Σ(nb colis × poids du colis vide) + nb palettes (calcul 220 / 100 existant) × poids d'une palette. (Version 18.0.6.5.0 : poids palette sur la société, retiré en 18.0.6.5.1 au profit du « Poids » natif du type de colis, voir l'incident.)
- À faire après mise à jour : renseigner le poids du colis vide de chaque conditionnement et le « Poids » du type de colis « Palettes de Livraison » (sinon le poids brut = poids net).
- Bases : lecture seule TEST (vue formulaire société).
- Modules/modèles : `product_packaging_unit_price` · `product.packaging`, `res.company`, rapport facture.
- Commit : branche `fix/facture-colonne-emballage` (non committé, non testé dans Odoo).

## 2026-10-30 · Facture : colonne « Emballage » vide
- Demande : à l'impression de la facture, la colonne Emballage des lignes est vide.
- Cause (TEST, facture F2026/068) : les lignes ont bien un conditionnement (ex. « PLASTIQUE 420G 10KG GOLD FRUTAS ») mais le rapport n'affichait que sa « Description de vente » (`description_sale`), vide sur la plupart des conditionnements (seuls « CARTON 4KG » / « PLASTIQUE 10KG » du modèle 84 l'ont).
- Fait : `product_packaging_unit_price` 18.0.6.4.0 : colonne Emballage = description de vente, à défaut nom du conditionnement. Au passage : la cellule Calibre n'est affichée que si l'en-tête l'est (colonnes décalées sur une facture sans calibre), et la ligne de totaux s'adapte.
- Bases : lecture seule TEST (facture F2026/068 et ses lignes).
- Modules/modèles : `product_packaging_unit_price` · rapport facture (`report_invoice_document_inherit_packaging_replace`).
- Commit : `e1cf98c` sur `fix/facture-colonne-emballage` (poussé). Validé par l'utilisateur.

## 2026-10-30 · OF : même numéro de lot pour tous les calibres de la journée
- Demande : avant, un même numéro de lot servait à plusieurs calibres ; maintenant il faut un lot par calibre.
- Constat (TEST) : un lot est toujours propre à un article ; avant, le numéro de session était **saisi à la main** pour chaque calibre (ex. `0044S01032026` existe 5 fois : calibres 16, 18, 30, 32, LIDL 20, créés par Btissam le 01/03). Le 30/10, le bouton « Générer » a été utilisé : il tire un nouveau numéro de la séquence `stock.lot.serial` à chaque clic (`0001S30102026` cal. 16, `0002S30102026` cal. 16 resté vide, `0003S30102026` cal. 14). Aucun code cassé.
- Fait : `custom_lot_sequences` 18.0.2.3.0 : « Générer » reprend le nom du dernier lot produit créé aujourd'hui (fuseau de l'utilisateur) sur un autre OF du même type d'opération : crée le lot de ce nom pour l'article, ou reprend celui qui existe déjà pour ce calibre ; sans lot du jour, comportement natif (séquence). Bouton « Nouveau lot » à côté (contexte `new_day_lot`) pour démarrer une nouvelle session avec le numéro suivant.
- Bases : lecture seule TEST (lots `0044S01032026` et du 30/10, vue OF).
- Modules/modèles : `custom_lot_sequences` · `mrp.production`.
- Commit : `c1d2496` sur `feat/lot-du-jour-of`. **Validé en TEST** par l'utilisateur (calibre 22 : lot `0001S30102026` repris du calibre 16, WH/MOF/03917).

## 2026-10-29 · OF : conditionnement choisi selon la nomenclature
- Demande : sélectionner automatiquement le conditionnement de l'OF selon la nomenclature choisie (caisse carton 4 kg ou caisse plastique 10 kg).
- Constat (TEST) : chaque variante calibrée a un conditionnement de 4 kg (« CARTON 4KG … ») et un de 10 kg (« PLASTIQUE … 10KG … »), parfois des conditionnements parasites à 1 kg (« 2640 », « 3436 », « pl ») ; nomenclatures 4 kg (880 kg) : ids 7, 8, 12, 16, et 15 « déchets ferme » ; 10 kg (1000 kg) : ids 9, 10, 13, 17 ; « Déchets usines » (11) sans conditionnement.
- Fait : `mrp_production_storage` 18.0.1.2.0 : champ « Poids par colis » (`packaging_unit_qty`) sur la nomenclature (formulaire, après la référence) ; sur l'OF, `product_packaging_id` devient calculé (stocké, modifiable) d'après la nomenclature et l'article : conditionnement de l'article dont la contenance est égale au poids par colis (le premier par séquence) ; sans correspondance, le choix de l'opérateur est conservé s'il concerne l'article.
- À faire après mise à jour : renseigner « Poids par colis » sur les nomenclatures (4 ou 10).
- Bases : lecture seule TEST (conditionnements des variantes calibrées, nomenclatures, vue formulaire nomenclature).
- Modules/modèles : `mrp_production_storage` · `mrp.bom`, `mrp.production`.
- Commit : branche `feat/conditionnement-auto-nomenclature` (non committé, non testé dans Odoo).

## 2026-10-29 · Déploiement en PROD
- PR deepcodesystem/sofalgri#7 (FIFO par n° de palette) **fusionnée** dans `18.0` (`e76637a`).
- PROD mise à jour par l'utilisateur : `18.0` à jour (PR #5 à #7), modules `custom_lot_sequences` 18.0.2.2.0, `picking_custom_addons` 18.0.4.11.0, `mrp_component_lot_check` 18.0.1.0.1, `mrp_production_storage` 18.0.1.1.0 ; fabrication en 1 étape configurée.
- Bases : aucune requête.

## 2026-10-29 · FIFO : palettes d'une même réception proposées dans l'ordre inverse
- Demande : l'OF propose E005 puis E004 au lieu de E001 puis E002, alors que le FIFO est paramétré.
- Cause (TEST) : E001 à E005 viennent de la même réception validée en une fois (même `in_date` 29/10 22:24:02, même lot `001FA29102026`). À date égale, le FIFO natif départage par id du quant (`in_date ASC, id`) ; or la validation traite les lignes dans l'ordre `result_package_id desc`, donc E005 reçoit le plus petit id (E004 → 18640 … E001 → 18643). Le FIFO entre réceptions est correct.
- Fait : `picking_custom_addons` 18.0.4.11.0 : `stock.quant._get_removal_strategy_order` → FIFO = `in_date ASC, package_id ASC, id` (tri des colis par nom).
- Bases : lecture seule TEST (colis E001–E005, quants).
- Modules/modèles : `picking_custom_addons` · `stock.quant`.
- Commit : `347e7af` sur `fix/fifo-ordre-palettes`. **Validé en TEST** ; PR #7 fusionnée.

## 2026-10-29 · Doubles emplacements des emballages (ST/Stock et Zone de réception)
- Constat (TEST et PROD, lecture seule) : 7 articles d'emballage avec du stock dans `ST/Stock` (inventaire du 02/07/2026 par l'administrateur), alors que les réceptions arrivent dans `Zone de réception` et que les OF ne consommaient que là.
- Fait par l'utilisateur (TEST et PROD) : regroupement et configuration (emplacements, fabrication en 1 étape). Aucun code.

## 2026-10-29 · OF : n° de palette S et étiquette palette produit fini
- Demande : sur l'OF, une étiquette colis avec un numéro de palette, comme pour la réception.
- Fait : `mrp_production_storage` 18.0.1.1.0 : champ « N° de palette » (`result_package_id`, colis vides ; vide → palette créée par la séquence native S001… avec le type du conditionnement, à défaut « Palettes de Livraison ») ; bouton « Étiquette palette » (exige le lot produit, crée la palette si besoin) ; à « Produire », palette créée si absente et reportée avec le frigo sur les lignes du produit fini (`_post_inventory`). Nouvelle étiquette A5 paysage sur `mrp.production`, même présentation que la réception : n° de palette et lot avec codes-barres, produit, variété, calibre, conditionnement, marque, date, nb colis, poids par colis, frigo, poids net. Bouton ancré sur l'en-tête (le bouton `action_confirm` est renommé par `mrp_component_lot_check`).
- Bases : aucune requête (champs `calibre` / `product_variety` lus dans le dépôt).
- Modules/modèles : `mrp_production_storage` · `mrp.production`, rapport `report_production_pallet`.
- Commit : `e1589bc`. **Validé en TEST** ; PR deepcodesystem/sofalgri#6 (`mrp_component_lot_check` + `mrp_production_storage`) **fusionnée** dans `18.0` (`eaa22bb`). Configuration (1 étape) faite par l'utilisateur en TEST et en PROD.

## 2026-10-29 · OF : champs conditionnement et frigo introuvables
- Demande : les champs conditionnement et frigo n'apparaissent pas sur le formulaire de l'OF (module installé en TEST).
- Cause : dans Odoo 18, `bom_id` est dans une `div class="o_row"` (`bom_div`) ; les champs insérés après lui se retrouvaient sur la même ligne, sans libellé. Même défaut pour « Lots composants vérifiés ».
- Fait : insertion après `//div[@name='bom_div']` dans les deux modules ; `mrp_production_storage` et `mrp_component_lot_check` en 18.0.1.0.1.
- Bases : lecture seule TEST (modules installés, vue formulaire OF).
- Commit : `7fc5f0b` sur `feat/of-verification-lots` (poussé). Validé par l'utilisateur (« édition beaucoup plus simple »).

## 2026-10-29 · OF : conditionnement et frigo sur l'OF (suppression du transfert de stockage)
- Demande : se passer du transfert « Stocker les produits finis » créé après chaque OF, qui sert seulement à saisir le conditionnement, sa quantité et le frigo.
- Constat (TEST) : entrepôt en fabrication 3 étapes ; l'étape de prélèvement n'est déjà plus utilisée (« Fabrication » prend dans `Zone de réception`) ; le transfert SFP (`Post-fabrication` → `Frigo 0X`) est validé ~1 min après l'OF, avec seulement conditionnement (ex. « CARTON 4KG GOLD FRUTAS », 220) et frigo. Conditionnements définis par variante (4 kg carton, 10 kg plastique, type « Palettes de Livraison »).
- Fait : nouveau module `mrp_production_storage` 18.0.1.0.0 : champs « Conditionnement », « Quantité de conditionnement » (calculée kg ÷ conditionnement, modifiable ; si modifiée sur un OF confirmé, ajuste la quantité à produire) et « Frigo de stockage » (emplacements internes sous `ST/Stock`) sur l'OF, suivis dans le fil ; reportés sur le mouvement du produit fini (frigo seulement s'il n'est pas chaîné à un transfert de stockage) ; « Produire » exige conditionnement et frigo pour les produits ayant des conditionnements.
- Configuration à faire ensuite (TEST puis PROD, par l'utilisateur ou avec accord) : valider les transferts SFP en attente, passer l'entrepôt en fabrication **1 étape**, puis vérifier que l'opération « Fabrication » garde `Zone de réception` comme emplacement source.
- Bases : lecture seule TEST (types d'opération, transfert SFP, conditionnements, vue OF).
- Modules/modèles : `mrp_production_storage` · `mrp.production`.
- Commit : `10e84fe` sur `feat/of-verification-lots` (poussé). Installé en TEST par l'utilisateur.

## 2026-10-29 · Vérification des lots composants à la confirmation des OF
- Demande : à la confirmation d'un OF de calibrage, afficher le lot du vrac « Avocats pour export » utilisé et pouvoir le changer : les opérateurs ne vérifient pas le lot, la traçabilité est impossible.
- Constat (TEST) : l'OF consomme directement depuis `ST/Stock/Zone de réception` (pas de prélèvement) ; à la confirmation, Odoo réserve automatiquement palettes et lots (les plus anciens d'abord) ; l'OF est créé, confirmé et produit en moins d'une minute (ex. WH/MOF/03664 : palettes `001` et `014`, lots 500LA… et 5019A…).
- Fait : nouveau module `mrp_component_lot_check` 18.0.1.0.0. Le bouton « Confirmer » confirme puis ouvre le popup « Vérifier les lots des composants » : une ligne par palette réservée (composant, palette, lot, quantité), modifiable ; choisir une palette remplit le lot ; lignes ajoutables et supprimables. « Valider les lots » met à jour les réservations, coche « Lots composants vérifiés » et écrit le détail dans le fil de l'OF. « Produire » rouvre le popup tant que les lots ne sont pas validés, puis enchaîne la production. Bouton « Lots composants » pour rouvrir le popup.
- Bases : lecture seule TEST (OF, mouvements et lignes de composants, vue formulaire OF).
- Modules/modèles : `mrp_component_lot_check` · `mrp.production`, `mrp.component.lot.wizard(.line)`.
- Commit : `df2b0ad` sur `feat/of-verification-lots` (poussé). **Validé en TEST** par l'utilisateur.
- À surveiller : un OF terminé par un autre module (ex. production en masse) sur un seul OF non vérifié serait arrêté par le popup ; contexte `skip_component_lot_check` prévu pour le contourner.

## 2026-10-29 · Nouveau design de l'étiquette palette
- Demande : refaire l'étiquette palette (« Étiquette de colis ») avec un design plus professionnel, avant la PR.
- Fait : `picking_custom_addons` 18.0.4.10.0 : modèle refait en A5 paysage (cadre, en-tête société + station + GGN + badge « Réception », n° de palette et n° de lot en grand avec codes-barres Code128, produit / variété / date, fournisseur / référence / emplacement, bandeau de pesée nb colis · brut · tare · **net** en négatif, pied avec caisse, palette, date et auteur de l'impression). Mise en page en tableaux (wkhtmltopdf). Champs de `sofalgri_package_reports` (variété, station, GGN) affichés seulement s'ils existent. Format papier propre au module (`paperformat_pallet_label`, marges 6 mm) : supprime la dépendance circulaire vers `sofalgri_package_reports.paperformat_a5_label`. Nom du PDF : « Palette - <n° de palette> ».
- Bases : aucune requête.
- Modules/modèles : `picking_custom_addons` · rapport `report_package_template`, `report.paperformat`.
- Commit : `c283bf5` sur `feat/lot-reception-avant-validation`. PR deepcodesystem/sofalgri#5 (lot à l'impression, assistant palette, numérotation E/S, étiquette) **fusionnée** dans `18.0` (`f81976a`) ; modules mis à jour par l'utilisateur.

## 2026-10-29 · Numérotation automatique des palettes (E entrée / S sortie)
- Demande : numéroter automatiquement les palettes, en distinguant les palettes de réception (E001…) et de sortie (S001…) ; les palettes de sortie sont créées en fin de calibrage (OF). Format choisi : 3 chiffres, compteur continu.
- Constat (TEST) : palettes nommées à la main avec des doublons (plusieurs « 001 », dont un colis réutilisé toute la saison avec 170 820 kg cumulés) ; séquence native des colis `stock.seq_quant_package` réglée sur `PAL` (5 numéros utilisés) ; types de colis « Palettes de réception » et « Palettes de Livraison » existants.
- Fait : `picking_custom_addons` 18.0.4.9.0 : séquence `stock.quant.package.reception` (E, 3 chiffres) ; dans l'assistant palette, le n° de palette devient facultatif : vide → création de la palette E suivante, type « Palettes de réception » ; curseur sur le poids brut. Séquence native des colis passée en préfixe S, 3 chiffres (compteur conservé), réappliqué à chaque mise à jour du module.
- Bases : lecture seule TEST (types de colis, séquences, colis).
- Modules/modèles : `picking_custom_addons` · `ir.sequence`, `stock.pallet.wizard`.
- Commit : `e9228ac` sur `feat/lot-reception-avant-validation` (poussé).
- Limites : un colis créé en tapant un nom (création rapide) garde ce nom ; seuls « Mettre en colis » et la création sans nom utilisent S. Le type « Palettes de Livraison » n'est pas posé automatiquement sur les palettes S.

## 2026-10-29 · Assistant palette : n° de palette et saisie regroupée
- Demande : ajouter le colis de destination (n° de palette, saisi à la main pour l'instant) et regrouper les champs à saisir par le réceptionniste.
- Fait : champ obligatoire « N° de palette » (`result_package_id`, colis vides uniquement, création rapide en tapant un nouveau numéro), reporté sur la ligne ; formulaire réorganisé : bloc « Pesée de la palette » en tête (n° de palette avec le curseur, poids brut, quantité colis, tare et poids net), bloc « Paramètres » en dessous (article, emplacement, caisse, poids palette). Version 18.0.4.8.0.
- Bases : aucune requête.
- Modules/modèles : `picking_custom_addons` · `stock.pallet.wizard`.
- Commit : `d224f79` sur `feat/lot-reception-avant-validation` (poussé).
- Suite : numérotation automatique des palettes (entrée suivante).

## 2026-10-29 · Assistant « Ajouter une palette » sur les réceptions
- Demande : retour du test en TEST : le lot est bien attribué, mais le bouton d'impression de la ligne affiche « Veuillez d'abord enregistrer vos changements » ; il faut enregistrer, rouvrir le popup « Opérations détaillées », puis imprimer.
- Cause : ce popup est ouvert depuis la réception ; une nouvelle ligne n'existe que dans le navigateur tant que la réception n'est pas enregistrée, donc aucun bouton serveur (impression ou génération de lot) ne peut agir dessus.
- Fait : `picking_custom_addons` 18.0.4.7.0 : assistant `stock.pallet.wizard` ouvert par le bouton « Ajouter une palette » en haut de la réception (réceptions prêtes ou en attente). Saisie : article (pré-rempli s'il est seul), emplacement, poids brut, caisse, nb caisses, poids palette ; tare et poids net calculés. « Ajouter et imprimer » crée la ligne (ou complète la ligne réservée par Odoo encore vide), puis imprime l'étiquette ; le lot est attribué par `custom_lot_sequences` et le popup se ferme. Caisse, palette et emplacement repris de la palette précédente. Ajout de `security/ir.model.access.csv` (groupe Utilisateur stock).
- Bases : lecture seule TEST (lignes de réceptions validées : pas de colis de destination, caisse « Caisse de Réception » 3 kg).
- Modules/modèles : `picking_custom_addons` · `stock.pallet.wizard`, vue formulaire `stock.picking`.
- Commit : `d89015b` sur `feat/lot-reception-avant-validation` (poussé). Idée validée par l'utilisateur, à affiner (entrée suivante).

## 2026-10-29 · Lot de réception disponible à l'impression de l'étiquette palette
- Demande : à la réception vrac, l'étiquette de chaque palette doit porter le n° de lot avant la validation du transfert ; le lot n'était généré qu'à la validation.
- Cause : le nom de lot n'était écrit dans `lot_name` qu'au `button_validate` ; de plus le type « Réceptions » crée les lots par nom (`use_create_lots`), donc `lot_id` reste vide jusqu'à la validation alors que l'étiquette affichait `lot_id.name`.
- Fait : `custom_lot_sequences` 18.0.2.2.0 : méthode `_assign_receipt_lot_names` (un lot par produit et par réception, réutilise le lot déjà attribué à une autre palette), appelée au clic « Imprimer l'étiquette » et à la validation ; dépend désormais de `picking_custom_addons` ; auteur GetapPRO, licence LGPL-3. `picking_custom_addons` 18.0.4.6.0 : l'étiquette affiche `lot_id.name` ou à défaut `lot_name` (texte et QR code). La date du lot devient celle de la première impression.
- Bases : lecture seule TEST (type d'opération « Réceptions »).
- Modules/modèles : `custom_lot_sequences` · `stock.picking`, `stock.move.line` ; `picking_custom_addons` · rapport « Étiquette de colis ».
- Commits : `f508223` et `2376927` sur `feat/lot-reception-avant-validation` (poussée). Testé en TEST par l'utilisateur : lot correct, mais impression bloquée tant que la réception n'est pas enregistrée (voir l'entrée « Assistant Ajouter une palette »).

## 2026-10-29 · Archivage des lots de l'ancienne saison
- Demande : pouvoir archiver les lots et numéros de série de l'ancienne saison, comme les colis.
- Constat (TEST) : `stock.lot` n'a pas de champ `active` ; la recherche native offre déjà les filtres « En stock » et « Date de création » (choix de la saison).
- Fait : champ `active` sur `stock.lot` (actions Archiver / Désarchiver) ; archivage refusé si le lot a encore une quantité en emplacement interne ou de transit (message limité à 20 lots) ; bandeau « Archivé » ; filtres « Hors stock » et « Archivés » ; version 18.0.4.5.0.
- Bases : lecture seule TEST (champs et vues de `stock.lot`).
- Modules/modèles : `picking_custom_addons` · `stock.lot`.
- Commit : `104eb4f` sur `feat/archivage-lots` (poussé).
- **Validé en TEST** par l'utilisateur. PR deepcodesystem/sofalgri#3 **fusionnée** dans `18.0` (`559db2f`). PROD : non déployé.

## 2026-10-29 · Date fausse dans les numéros de lot générés sur les OF
- Demande : la date du numéro de lot généré sur un OF n'est pas bonne.
- Cause : aucun code du dépôt. Le bouton « Générer » du lot sur l'OF utilise la séquence native `stock.lot.serial` (`stock.sequence_production_lots`), configurée avec le suffixe `S%(range_year)s%(range_month)s%(day)s` et des plages de dates. `range_year` / `range_month` valent la date de **début de la plage** (01/01/2026 pour la plage 2026), d'où un mois figé et un ordre AAAAMMJJ au lieu de JJMMAAAA. Ex. TEST : lot `0012S20260129` généré le 29/10/2026 (mois 01 au lieu de 10) ; `0005S20260114` généré le 13/02/2026 à 23 h 25 UTC.
- Autres constats : les lots `00xxS<JJMMAAAA>` (ex. `0043S24022026` sur un OF du 25/02) sont saisis à la main par session de calibrage ; `stock_picking_old.py` (non importé) ne produit aucun lot actuel. Rien n'indique que le code du VPS diffère du dépôt pour cette fonction.
- Fait : correctif `custom_lot_sequences` (fichier de données qui fixe le suffixe à `S%(day)s%(month)s%(year)s`, remplissage 4), version 18.0.2.2.0.
- Bases : lecture seule TEST (OF, lots, séquences, plages de dates).
- Modules/modèles : `custom_lot_sequences` · `ir.sequence`.
- Commit : `6482f7f` sur `fix/date-lot-of` (worktree `E:\Claude\Sofalgri\sofalgri-fix-date-lot`), non poussé, non testé dans Odoo.
- Suite : l'utilisateur a préféré corriger le suffixe dans Paramètres > Technique > Séquences ; la branche `fix/date-lot-of` n'est pas utilisée.

## 2026-10-29 · Archivage des colis : correction pour les colis livrés
- Demande : erreur « Impossible d'archiver des colis qui contiennent encore du stock » sur des centaines de colis, après installation en TEST.
- Cause : un colis livré garde ses quants sur `Partenaires/Clients` ; la règle bloquait tout colis ayant des quants.
- Fait : seul le stock en emplacement interne ou de transit bloque l'archivage ; message limité à 20 colis ; filtre « Vides » remplacé par « Hors stock » ; version 18.0.4.4.1.
- Bases : lecture seule TEST (quants des colis).
- Modules/modèles : `picking_custom_addons` · `stock.quant.package`.
- Commit : `b32a9a2` sur `feat/archivage-colis` (poussé).
- **Validé en TEST** par l'utilisateur (archivage en masse « Hors stock » sans erreur). PR deepcodesystem/sofalgri#2 **fusionnée** dans `18.0` (`29958a9`). PROD : non déployé.

## 2026-10-29 · Archivage des colis
- Demande : pouvoir archiver ou supprimer des colis (`stock.quant.package`) ; aucune action disponible.
- Constat : le modèle natif n'a pas de champ `active` (pas d'archivage) ; la suppression est bloquée dès qu'un colis a des mouvements. En TEST, la plupart des colis sont vides et sans emplacement.
- Fait : champ `active` sur `stock.quant.package` (actions Archiver / Désarchiver) ; archivage refusé si le colis contient du stock ; bandeau « Archivé » et filtres « Vides » / « Archivés » ; version 18.0.4.4.0.
- Bases : lecture seule TEST (colis, vues natives). Module à mettre à jour sur TEST, puis PROD (déploiement par l'utilisateur).
- Modules/modèles : `picking_custom_addons` · `stock.quant.package`.
- Commit : `5a8b485` sur la branche `feat/archivage-colis` (non poussée, non testée dans Odoo).

## 2026-10-29 · Configuration Claude Code du dépôt
- Demande : configurer le dépôt comme projet Claude Code.
- Fait : `CLAUDE.md` (contexte, règles MCP TEST/PROD, conventions Odoo 18, workflow Git, journal) ; CONTEXTE.md et JOURNAL.md déplacés dans `docs/` ; analyse du code et des données ajoutée à `docs/CONTEXTE.md` ; `.mcp.json` copié et ignoré par Git ; `.claude/settings.json` (lecture MCP autorisée, écritures, `analyze_records`, `ask_ai` et `git push` sur demande).
- Bases : lecture seule TEST et PROD (BoM, OF 30 j, lots, entrepôts, emplacements, catégories) : volumes identiques.
- Constats : lots d'OF générés par un code absent du dépôt ; `package_packaging` doublon de `sofalgri_package_reports` ; `sales_margin` en conflit avec `sale_margin` ; dépendances cachées entre modules.
- Commit : branche `chore/claude-setup` (non poussée).

## 2026-10-29 · Mise en place du projet Claude
- Création du projet Sofalgri avec les instructions, CONTEXTE.md et JOURNAL.md.
- Connexion MCP (`odoo_mcp_manager`) aux bases `sofalgri` (PROD) et `sofalgri-test` (TEST).
- Inventaire : 166 modules installés, identiques en PROD et TEST ; 10 modules dans le dépôt custom, dont 8 installés.
- Points ouverts : statut de `package_packaging` et `sales_margin` ; correction des auteurs et de la version dans les manifests (voir CONTEXTE.md).
