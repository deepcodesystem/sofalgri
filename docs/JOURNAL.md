# Sofalgri — Journal des interventions

Format d'une entrée : date · demande · ce qui a été fait · base(s) concernée(s) · modules/modèles touchés · commit éventuel.
Les entrées les plus récentes en haut.

---

## 2026-11-02 · BI Dashboard : tableau des palettes en frigo par calibre
- Demande : mettre en place avec `synconics_bi_dashboard` (OPL-1, 18.0.1.0.3, installé en TEST et en PROD) les tableaux du client ; premier modèle voulu : palettes en frigo, calibres 12 à 32 en lignes, conditionnements en colonnes.
- Constats : le module ne regroupe que sur des champs stockés de la source et sa liste groupée n'a qu'un regroupement (pas de tableau croisé) ; un graphique par article coupe le libellé avant la marque et le calibre (`dashboard.chart` : camembert id 1, liste id 2, créés pour essai dans « My Dashboard », TEST). Après le passage du graphique 1 en camembert, thème passé de « animated » à « frozen » et dernier modificateur « Public user », causes non établies.
- Fait : nouveau module `sofalgri_stock_calibre_report` 18.0.1.0.0 : vue SQL `sofalgri.stock.calibre.report` (une ligne par calibre, palettes distinctes dans les emplacements internes `…/Frigo …`, par nom de conditionnement ; `PLASTIQUE…` de 10 kg regroupés ; autre conditionnement ou aucun dans « Autres »). Colonnes fixes : un nouveau conditionnement demande une modification. Lecture réservée au groupe Utilisateur stock.
- Attendu en TEST (stock du 02/11) : calibre 16 : Lidl 2 ; 18 : Gold 1, Lidl 8 ; 20 : Gold 2, Lidl 9 ; 22 : Gold 9, Lidl 12 ; 24 : Gold 6, Lidl 1 ; 50 palettes au total.
- Bases : TEST (écritures : graphiques d'essai, avec accord) ; PROD (lecture seule : quants des frigos, module installé). TEST recréée le 02/11 à 20 h 02.
- Modules/modèles : `sofalgri_stock_calibre_report` · `sofalgri.stock.calibre.report`, `dashboard.chart`.
- Commit : aucun, branche `feat/tableau-palettes-calibre`. Non installé, vue SQL et affichage non testés.
- Déploiement : nouveau module, à installer (liste des applications à mettre à jour) ; non chargé dans une base où il n'est pas installé, donc sans risque pour la PROD pendant le test.

## 2026-11-02 · Analyse des stocks négatifs restants en PROD
- Demande : trouver la cause des négatifs restants (vrac, emballages), proposer leur correction, contrôler la valorisation des corrections du 02/11. Sans écriture en PROD.
- Vrac, `WH/MOF/03971` (01/11 à 23:12) : hypothèse confirmée, lignes ajoutées dans le popup avec l'emplacement de l'OF, corrigé par la PR deepcodesystem/sofalgri#26 (installée en PROD). E038, E042 à E047 (−416 kg dans `ST/Stock`) compensent exactement +416 kg en `Zone de réception` : transfert interne, sans impact de valeur. E067 (−468 kg) : les 777 kg restés en `Zone de réception` ont été consommés par `03972`, les OF suivants sont décalés et le stock des palettes en cours (E085, E086) est trop haut : ajustement après pesée. Traçabilité de `03972` à `03989` décalée d'environ 468 kg.
- Vrac en `Zone de réception` : E003 (−24 kg, correction du 30/10), E072 (−8 kg, écart de poids réel reporté sur la dernière palette, très probable). Ajustement avec le comptage ci-dessus (écart à retirer : 500 kg, ou 916 kg si les 416 kg n'existaient pas physiquement).
- Emballages : Chapaux Palette et Rub ne sortent pas de `ST/Stock` à cause des règles de rangement (correctes) : ils n'ont plus de stock à réserver, la ligne reste alors sur la source de l'OF. Chaque OF ajoute −6 Chapaux et −0,01 Rub. Cercleuse : `03914` validé 11 min avant la réception ; transfert de 1 unité.
- **Chapaux Palette, erreur d'unité probable** : `P-20260129-0255` / `ST/IN/00745` : 10 « Units » à 225 MAD, alors que 225 MAD est le prix d'une boîte de 1 000 (`P-20250131-0022` ; coût de 0,23 MAD à l'inventaire du 02/07). À confirmer sur le BL ou la facture NETPAK. Coût moyen passé à 225 MAD : environ 98 450 MAD de surcoût dans les calibrés (1 350 MAD par OF). Corriger le coût **avant** l'ajustement de stock ; réévaluation des calibrés à décider avec la comptabilité.
- Valorisation du 02/11 : articles en `manual_periodic`, donc aucune écriture comptable, seulement des couches. `ST/INT/00010` : aucune couche, normal. `UB/00149` : −756,69 MAD de valeur de stock (678,53 de coût de l'OF non rendu, probablement l'ordre de travail ; 78,16 d'écart de coût moyen) ; pas de correction proposée.
- Noms : Chapaux Palette = « Chappe », Cercleuse manuelle = « Chapeau de Palette », Rub = « Ruban de Cerclage », Avocats pour export = « AVOCAT HASS NON CALIBRÉ » à l'écran en français (le MCP lit les noms anglais).
- **Validé en TEST** (corrections par l'utilisateur, base redupliquée le 02/11) : plus aucun négatif interne ; Chappe : coût 0,225 MAD d'abord (aucune couche tant que la quantité est négative), puis ajustement : compensation de +96 205,95 MAD, valeur 2 151,45 MAD pour 9 562 unités ; vrac : quantité inchangée, −209,30 MAD. OF de contrôle `WH/MOF/03991` (TEST) : ligne ajoutée (E090) et réservations aux bons emplacements, Chappe valorisée 1,35 MAD au lieu de 1 350 MAD par OF.
- À retenir pour les transferts : forcer « Vers » (les règles de rangement peuvent le changer) ; choisir le colis de destination dans la liste, jamais « Créer » (doublon E042 créé en TEST, rattrapé par un transfert `ST/Stock` → `ST/Stock`).
- PROD (par l'utilisateur) : Chapeau de Palette transféré (`ST/INT/00011`), Chappe et Ruban corrigés et ajustés (9 562 et 5, comptages réels selon l'utilisateur), 416 kg transférés (`ST/INT/00012`), E067, E003, E072 soldés et 500 kg retirés d'E086 (−123) et E087 (−377) le 02/11 à 17:19, **sans pesée** (hypothèse que les 416 kg existaient physiquement), −209,30 MAD. Lecture PROD : plus aucun négatif interne. `WH/MOF/03991` en PROD est un autre OF que celui de TEST. Les 10 boîtes NETPAK sont confirmées par l'utilisateur. **Reste** : hypothèse des 416 kg non vérifiée (contrôle des palettes difficile) : écart possible d'environ 416 kg, soit environ 7 300 MAD, à solder au prochain inventaire physique du vrac ; réévaluation des calibrés (environ 98 450 MAD) non validée par la comptabilité. Détail : note `negatifs-prod-analyse.md` de la session.
- Bases : lecture seule PROD (quants, lignes de mouvement, couches de valorisation, achats, nomenclatures, articles, règles de rangement, modules) ; lecture seule TEST (emballages, mêmes négatifs).
- Modules/modèles : aucun code · `stock.quant`, `stock.move.line`, `stock.valuation.layer`, `purchase.order.line`.
- Commit : sur `chore/journal-negatifs-prod` (journal seul, aucun code).

## 2026-11-02 · Déconstruction par palette et emplacement réel dans le popup des lots
- Demande : simplifier la déconstruction d'une palette pour la refaire sous une autre marque (voir la palette S040 : la quantité déconstruite restait sur la palette).
- Causes : le natif propose l'emplacement de l'OF (`ST/Stock`) et sa ligne de déconstruction ne porte aucun colis. Dans le popup des lots, une ligne ajoutée prenait l'emplacement de l'OF (`ST/Stock`) au lieu de celui du stock : stock négatif dans `ST/Stock` (`004FE` en PROD, très probablement aussi les négatifs du 01/11 à 23:12, non relu).
- Fait :
  - `mrp_production_storage` 18.0.1.4.0 : champ « Palette » (`package_id`, stocké) sur `mrp.unbuild`, rempli d'après l'OF si la palette contient encore son lot ; le frigo suit la palette ; la ligne de déconstruction sort de cette palette (`_prepare_finished_move_line_vals`), palette mixte comprise ; refus si le disponible de la palette est insuffisant. Vide : comportement natif. Étiquette palette : la quantité déconstruite est retirée (`_get_pallet_label_data`).
  - `mrp_component_lot_check` 18.0.1.4.0 : ligne ajoutée, ou dont le lot ou la palette change, placée sur l'emplacement réel du stock (`_get_source_location`) ; refus si ce lot n'a pas de stock sur cette palette ou hors palette.
- Correctif (18.0.1.4.1) : quantité du popup de déconstruction préremplie avec le contenu de la palette (le natif proposait 1). Après un refus, le popup est figé et le brouillon reste : le fermer et supprimer le brouillon.
- Test TEST (`WH/MOF/03945`, `UB/00152`) : palette S032 et Frigo 01 proposés, refus à 1 000 kg, 880 kg sortis de S032 sans stock négatif, vrac rendu en `Zone de réception` sans palette. Nouvel OF `WH/MOF/03989` : vrac consommé en `Zone de réception`, sans négatif. Palette mixte S072 (`UB/00153`) : seul le calibre 22 sorti. Étiquette de S072 confirmée par l'utilisateur. **Validé en TEST.**
- Limite : le vrac rendu revient toujours sans palette, en `Zone de réception` par la stratégie de rangement.
- Bases : lecture seule TEST (vues de `mrp.unbuild`, modules « unbuild » : aucun installé).
- Modules/modèles : `mrp_production_storage`, `mrp_component_lot_check` · `mrp.unbuild`, `mrp.production`, `mrp.component.lot.wizard.line`.
- Commit : `e5156e4`, `8a8803b` et `506bbd1` sur `feat/deconstruction-palette` ; PR deepcodesystem/sofalgri#26.
- Déploiement : nouveau champ stocké sur `mrp.unbuild` → mise à jour en ligne de commande de `mrp_production_storage` sur **les deux bases** avant redémarrage ; `mrp_component_lot_check` : mise à jour normale.

## 2026-11-02 · Déconstruction d'un OF : palette S040 restée à 2 lignes
- Demande : après la déconstruction de `WH/MOF/03953` et la production de `WH/MOF/03987` sur la même palette, S040 affiche 2 lignes : la quantité déconstruite y est restée.
- Cause (PROD, lecture seule) : `UB/00149` a sorti les 880 kg du lot `0003S01112026` de `ST/Stock`, sans palette : −880 kg dans `ST/Stock`, S040 inchangée. Le vrac rendu (880 kg de `005FE29102026`) est revenu sans palette en `Zone de réception` ; le nouvel OF a consommé `004FE29102026` depuis `ST/Stock` (−880 kg). La déconstruction ne propose pas de palette (comportement natif supposé, code non vérifié).
- Fait (TEST, où le cas existait déjà avec `UB/00150`) : transfert interne `ST/INT/00010` Frigo 01 / S040 → `ST/Stock`, sans palette de destination, et ligne de vrac de l'OF déplacée en `Zone de réception` (changement de lot essayé puis annulé). Écritures par le MCP ; une modification de ligne sans sa quantité a laissé 880 kg réservés sur S011, remis à 0 directement sur le quant.
- Fait (PROD, par l'utilisateur) : mêmes corrections, vrac sur `005FE29102026`. Vérifié en lecture : S040 ne contient plus que le LIDL (880 kg), les quants `0003S01112026` et vrac concernés sont à 0, aucune réservation restante sur le calibre 24 en Frigo 01.
- À noter : à « Marquer comme à faire », Odoo réserve d'office une autre palette (S011 en TEST) : la remplacer avant de valider. Pour déconstruire : sortir d'abord la quantité de la palette, puis déconstruire avec le frigo comme source.
- Restent ouverts : autres stocks négatifs (vrac E038, E042 à E047 et E067 dans `ST/Stock`, E003 et E072 en `Zone de réception`, emballages dans `ST/Stock`, dont Chapeaux Palette −422) ; écritures de valorisation des corrections non contrôlées.
- Bases : PROD (lecture seule pour Claude) ; TEST (écritures avec accord).
- Modules/modèles : aucun code · `stock.quant`, `stock.move.line`, `mrp.unbuild`.
- Commit : `ee2f838` sur `chore/journal-deconstruction-s040` (journal seul) ; PR deepcodesystem/sofalgri#25 **fusionnée** dans `18.0` (`0c92fd4`).

## 2026-11-01 · Signature et cachet sur les factures
- Demande : ajouter une signature aux factures préparées (client, transitaire, pro forma).
- Choix de l'utilisateur : une image unique (signature + cachet) ; module dédié, réutilisable pour d'autres rapports.
- Constat (TEST, lecture seule) : pas de champ de signature natif sur `account.move` ni `res.company`, ni dans le modèle natif de la facture. Le bloc natif `payment_term` (conditions, QR code) est retiré par le pied recréé de `product_packaging_unit_price` : ancrage sur `custom_footer`, dernier bloc de la page.
- Fait : nouveau module `sofalgri_report_signature` 18.0.1.0.0 : champ `report_signature_image` « Signature et cachet » sur `res.company` (onglet « Rapports » de la fiche société, image limitée à 1024 px) ; bloc `report_signature_block` en bas à droite, non coupé entre deux pages, sur la facture client et sur la mise en page commune transitaire / pro forma. Sans image, documents inchangés.
- Bases : lecture seule TEST (champs de signature, modèle `account.report_invoice_document`, formulaire société).
- Modules/modèles : `sofalgri_report_signature` · `res.company`, rapports facture, facture transitaire, pro forma.
- Commit : `2932fde` sur `feat/signature-factures`. **Validé en TEST** par l'utilisateur ; PR deepcodesystem/sofalgri#24.
- Correctif (18.0.1.0.1) : sur la facture F2026/069 (test), la signature passait seule sur une page 2 vide. Facture client : signature dans la colonne droite du pied, sous les totaux. Transitaire et pro forma, par précaution : à droite des coordonnées bancaires. Commit `4854649`.
- Déploiement : nouveau module, à installer (liste des applications à mettre à jour) ; image stockée en pièce jointe, donc aucune colonne ajoutée sur `res_company`. Puis charger l'image sur la fiche société.

## 2026-11-01 · OF : alerte si le poids réel de vrac semble être le poids brut
- Demande : éviter que les opérateurs saisissent le poids brut au lieu du poids net dans le popup des lots.
- Constat (PROD, lecture seule) : OF `WH/MOF/03946` à `03952` saisis en brut, corrigés à la main par l'utilisateur le 01/11 (−77 kg chacun, 539 kg au total). Les quantités ont bien été remises en stock : 123 kg ont comblé le négatif de E038 et E047, et 416 kg restent disponibles (E038 6, E042 à E046 77 chacune, E047 25). Date d'entrée de ces quants = date de la correction, donc proposés en dernier par le FIFO ; à consommer en les choisissant dans le popup si ces palettes sont physiquement vides. E003 reste à −24 kg depuis la correction du 30/10 (832 kg consommés pour 808 kg reçus), à solder par un ajustement d'inventaire. Corrections de stock laissées à l'utilisateur.
- Fait : `mrp_component_lot_check` 18.0.1.3.0 : au-delà de 5 % d'écart avec la nomenclature (`WEIGHT_GAP_ALERT_PERCENT`, à la hausse ou à la baisse), bandeau rouge dans le popup et demande de confirmation à la validation (« bien le poids NET, sans caisses ni palette ? ») ; confirmation tracée dans le fil de l'OF. Non bloquant après confirmation. Mention « NET » ajoutée au message d'en-tête.
- Bases : lecture seule PROD (quants du vrac en Zone de réception, lignes de consommation et de réception depuis le 29/10, messages des OF).
- Modules/modèles : `mrp_component_lot_check` · `mrp.component.lot.wizard`.
- Commit : `f554c83` sur `feat/alerte-poids-reel-of` ; PR deepcodesystem/sofalgri#23. **Validé en TEST** par l'utilisateur.
- Déploiement : aucun champ stocké ajouté, mise à jour normale du module.

## 2026-11-01 · OF : palette mixte (plusieurs calibres sur une palette)
- Demande : produire une palette contenant plusieurs calibres avec un OF par calibre (ex. calibre 14 puis calibre 16) ; la palette du premier OF n'était plus proposée sur le deuxième.
- Cause : le champ « N° de palette » de l'OF ne proposait que les colis vides (`quant_ids = False`).
- Choix de l'utilisateur : une étiquette récapitulative de la palette, plutôt qu'une étiquette par calibre.
- Fait :
  - `mrp_production_storage` 18.0.1.3.0 : le champ propose les palettes vides et les palettes `S…` présentes dans le frigo de l'OF ; « Produire » refuse une palette située ailleurs que dans ce frigo ; l'étiquette palette reprend tous les OF non annulés de la palette (`_get_pallet_label_data`) : une ligne par calibre, conditionnement et lot, total colis, calibres, poids net total, badge « Export - Mixte ». Étiquette inchangée pour une palette à un seul calibre.
  - `picking_custom_addons` 18.0.4.11.2 : le poids de la palette n'est compté qu'une fois dans la tare du colis, même avec plusieurs lignes sur le même colis.
- À noter : l'étiquette n'est complète qu'une fois tous les OF de la palette créés : la réimprimer depuis le dernier OF. Son contenu vient des OF, pas du stock : elle ne reflète pas une sortie ultérieure.
- Bases : lecture seule TEST (OF `WH/MOF/03914` à `03921`, ligne de production).
- Modules/modèles : `mrp_production_storage`, `picking_custom_addons` · `mrp.production`, `stock.move.line`, rapport `report_production_pallet`.
- Commit : `07e9cb3` et `5bda78e` sur `feat/palette-mixte-of`. **Validé en TEST** par l'utilisateur ; PR deepcodesystem/sofalgri#22 **fusionnée** dans `18.0` (`a00f292`).
- Déploiement : aucun champ stocké ajouté, mise à jour normale des deux modules.

## 2026-10-31 · Liste de colisage (packing list) depuis le bon de livraison
- Demande : mettre en place la liste de colisage sur le modèle client `Packing List SOFALGRI EXPORT - TRUCK 13 - GEORGES HELFER - 7650-011.xlsx` (24 colonnes, une ligne par palette × calibre, palettes mixtes sur plusieurs lignes avec « Pallet quantity » sur la première).
- Choix de l'utilisateur : depuis le bon de livraison ; Excel et PDF ; informations d'expédition saisies sur la livraison ; Packhouse / Grower Code sur l'entrepôt, Bio / Conventionnel sur l'article, pays = pays d'origine de l'article.
- Fait : nouveau module `sofalgri_packing_list` 18.0.1.0.0 (dépend de `stock`, `sale_stock`, `account`, `delivery_carrier_custom`, `sofalgri_package_reports`) :
  - `stock.picking` : onglet « Expédition » (livraisons) : référence camion, navire, n° conteneur (pré-rempli avec le matricule), ETD, ETA, port de destination, emplacements Temp Tale et absorbeur d'éthylène ; bouton « Liste de colisage (Excel) » ; rapport PDF « Liste de colisage » (menu Imprimer, A4 paysage, ligne de total colis / palettes) ;
  - lignes communes `_get_packing_list_rows` : regroupement des lignes de mouvement par palette (`result_package_id` ou `package_id`) × article × conditionnement ; variété, conditionnement (description de vente ou nom), poids du colis, calibre, classe, pays d'origine, nb de colis (`product_packaging_qty`, à défaut kg ÷ contenance), GGN (article, à défaut société), date de conditionnement (date de production du lot) ; tri par calibre puis palette ; référence fournisseur = factures validées de la commande, à défaut la commande ; titre « PACKING LIST <société> - <référence camion> <client> » ;
  - Excel généré avec `xlsxwriter` (fourni avec Odoo, pas de module OCA) : titre fusionné C2:X4, en-tête ligne 6, données à partir de la ligne 7, dates au format JJ/MM/AAAA ; téléchargé via une pièce jointe de la livraison ;
  - `stock.warehouse` : `packhouse_name`, `grower_code` ; `product.template` : `cultivation_mode` (CONVENTIONAL par défaut).
- Bases : lecture seule TEST (lignes de livraisons validées : palette, lot, conditionnement, nb de colis ; modules installés).
- Modules/modèles : `sofalgri_packing_list` · `stock.picking`, `stock.warehouse`, `product.template`.
- Commit : `7f4f0e4` sur `feat/liste-colisage` (poussé).
- Correctif (18.0.1.0.1) : erreur à l'impression (`TypeError: 'function' object is not iterable`) : sur `product.product`, la sélection héritée de `cultivation_mode` n'est pas une liste ; libellés tirés d'une table fixe `CULTIVATION_LABELS`.
- Déploiement : nouveau module, à installer (liste des applications à mettre à jour) ; non chargé dans une base où il n'est pas installé, donc sans risque pour la PROD pendant le test. Puis renseigner Packhouse (ex. ELAKHALPORT) et Grower Code (ex. SOFALGRI) sur l'entrepôt.

## 2026-10-31 · Réception vrac : stratégie de rangement ignorée par l'assistant palette
- Demande : en PROD, les « AVOCAT HASS NON CALIBRÉ » réceptionnés vont dans `ST/Stock` et non dans `ST/Stock/Zone de réception`, malgré la stratégie de rangement.
- Constat (PROD, lecture seule) : règle de rangement n° 6 correcte (Avocats pour export, `ST/Stock` → `Zone de réception`). Réceptions du 29/10 (ST/IN/00750 à 00754, lignes créées à la validation) : palettes en Zone de réception. Réceptions du 31/10 (ST/IN/00759 à 00762, palettes E058 à E097 saisies avec l'assistant « Ajouter une palette ») : palettes dans `ST/Stock`. Cause : l'assistant pré-remplit l'emplacement avec la destination de la réception (`ST/Stock`), l'impose sur la ligne (pas de rangement calculé) et le reprend pour les palettes suivantes. Ces palettes ne sont pas proposées aux OF (qui consomment dans Zone de réception) : transfert interne à faire par l'utilisateur.
- Fait : `picking_custom_addons` 18.0.4.11.1 : emplacement par défaut de l'assistant = stratégie de rangement appliquée à la destination de la réception pour l'article (et au changement d'article, si l'emplacement n'a pas été choisi) ; à la création de la ligne, si l'emplacement est resté sur la destination de la réception, la stratégie de rangement est appliquée ; un autre emplacement choisi (ex. frigo) est respecté.
- Bases : lecture seule PROD (règles de rangement, mouvements et lignes des réceptions du 29 au 31/10).
- Modules/modèles : `picking_custom_addons` · `stock.pallet.wizard`.
- Commit : `714fa6f` sur `fix/rangement-assistant-palette` ; PR deepcodesystem/sofalgri#20 **fusionnée** dans `18.0` (`b9ed312`).
- Déploiement : aucun champ ajouté, mise à jour normale du module.

## 2026-10-30 · Commande de vente : saisie en palettes
- Demande : simplifier la saisie des commandes en indiquant le nombre de palettes, d'où le nombre de colis (ex. 2 palettes de cartons 4 kg → 440 colis), puis les kg.
- Choix de l'utilisateur : colis par palette sur le conditionnement (220 carton 4 kg, 100 plastique 10 kg) ; palettes entières ; une saisie manuelle des colis ne recalcule pas les palettes ; factures calculées avec la même donnée.
- Fait : `product_packaging_unit_price` 18.0.6.10.0 :
  - `product.packaging.pallet_packaging_qty` « Colis par palette » (formulaire et liste), rempli à la migration (`migrations/18.0.6.10.0/post-migrate.py` : 100 si le nom contient « PLASTIQUE », sinon 220, seulement si vide) ;
  - `sale.order.line.pallet_qty` « Palettes » : `onchange` palettes / conditionnement → colis = palettes × colis par palette ; les kg suivent par le calcul natif ;
  - nombre de palettes des factures (client, transitaire, pro forma) : `colis_per_pallet` (donnée du conditionnement, à défaut l'ancienne règle) dans `export_report.shipping_summary`, colis regroupés par taille de palette et arrondis au supérieur ; calcul inline « PLASTIQUE » retiré de la facture client.
- Bases : lecture seule TEST (ligne de commande C-00210 : CARTON 4KG, 220 colis, 880 kg, 14,50 €/colis).
- Modules/modèles : `product_packaging_unit_price` · `product.packaging`, `sale.order.line`, rapports factures.
- Commit : `40a45f2` sur `feat/commande-palettes`. Validé en TEST par l'utilisateur.
- Affichage (18.0.6.10.1) : colonnes des lignes de commande réordonnées juste après la description : Palettes → Conditionnement (type de colis) → Nb colis → Prix/colis, puis quantité en kg et prix au kg (`position="move"` sur les champs natifs `product_packaging_id` / `product_packaging_qty`).
- Déploiement : nouveaux champs stockés sur `product.packaging` et `sale.order.line` → mise à jour en ligne de commande sur **les deux bases** avant redémarrage (exécute aussi la migration).
- PR deepcodesystem/sofalgri#19 **fusionnée** dans `18.0`.
- Correctif (18.0.6.10.2) : en saisissant les palettes, le conditionnement basculait sur la caisse plastique 10 kg et ne pouvait plus être changé : le calcul natif `sale.order.line._compute_product_packaging_id` suggère le plus gros conditionnement qui divise les kg (1 760 kg = 176 × 10 kg), puis l'onchange recalculait les colis sur cette base. Surcharge : le conditionnement choisi est conservé (vidé seulement s'il n'appartient pas au produit), plus de suggestion automatique.

## 2026-10-30 · Note interne du client sur les factures (client, transitaire, pro forma)
- Demande : une information propre à un client, saisie en note interne sur sa fiche, doit apparaître juste sous le client et son adresse sur la facture client, la facture transitaire et la pro forma.
- Fait : `product_packaging_unit_price` 18.0.6.9.0 : sous-template `report_partner_note` (note interne `comment` du client, à défaut celle de sa société ; rien si vide, via `is_html_empty`) ; appelé dans les trois variantes du bloc adresse de la facture client (`address_not_same_as_shipping`, `address_same_as_shipping`, `no_shipping`) et sous le bloc client de la mise en page commune transitaire / pro forma. Mise en forme de la note conservée (HTML).
- Bases : lecture seule TEST (vue `account.report_invoice_document`).
- Modules/modèles : `product_packaging_unit_price` · rapports facture, facture transitaire, pro forma.
- Commit : `a736859` sur `feat/note-client-factures`. **Validé en TEST** ; PR deepcodesystem/sofalgri#18 **fusionnée** dans `18.0` (`21989cc`).
- Déploiement : aucun champ ajouté, mise à jour normale du module.

## 2026-10-30 · Facture pro forma depuis la commande de vente
- Demande : mettre en place la facture pro forma, sur le modèle `proformat.pdf` (identique au modèle de la facture transitaire, avec la colonne PRIX UNITAIRE). Choix de l'utilisateur : même mise en page, imprimée depuis la commande de vente ; prix unitaire et montants **fictifs** (saisis), pas les prix réels.
- Fait : `product_packaging_unit_price` 18.0.6.8.0 :
  - rapport « Facture pro forma » (menu Imprimer de la commande de vente), titre « FACTURE PROFORMA N° : <commande> », une ligne par produit avec un **prix unitaire fictif** : champ « Prix unitaire pro forma » (`proforma_unit_price`) sur la commande, montant = prix fictif × poids net, total et somme en lettres déduits ; les prix réels ne sont jamais imprimés ; impression refusée si le prix fictif est vide (18.0.6.8.1 : contrôle dans `ir.actions.report._render`, avant le rendu, pour afficher un simple avertissement au lieu d'une erreur serveur QWeb) ; date de la commande, ville de l'entrepôt de la commande, incoterm et lieu, matricule, adresse de livraison, banque de la société, conditions de paiement ;
  - mise en page commune `report_export_document_body` utilisée par la facture transitaire (sans prix unitaire) et la pro forma ; calculs communs dans `models/export_report.py` (`group_export_lines`, `shipping_summary`), utilisés par `account.move` et `sale.order` ;
  - champ `gross_weight` « Poids brut total (kg) » sur la commande (défaut 24 250, sous le matricule), reporté sur la facture à la facturation.
- Bases : aucune requête.
- Modules/modèles : `product_packaging_unit_price` · `sale.order`, `account.move`, rapports facture transitaire et pro forma.
- Commit : `e30983b` et `56d0d4d` sur `feat/facture-proforma`. **Validé en TEST** ; PR deepcodesystem/sofalgri#17 **fusionnée** dans `18.0` (`943f1f9`) ; bases mises à jour par l'utilisateur.
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
