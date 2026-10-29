# Sofalgri — Journal des interventions

Format d'une entrée : date · demande · ce qui a été fait · base(s) concernée(s) · modules/modèles touchés · commit éventuel.
Les entrées les plus récentes en haut.

---

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
