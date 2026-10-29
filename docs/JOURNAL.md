# Sofalgri — Journal des interventions

Format d'une entrée : date · demande · ce qui a été fait · base(s) concernée(s) · modules/modèles touchés · commit éventuel.
Les entrées les plus récentes en haut.

---

## 2026-10-29 · Archivage des colis : correction pour les colis livrés
- Demande : erreur « Impossible d'archiver des colis qui contiennent encore du stock » sur des centaines de colis, après installation en TEST.
- Cause : un colis livré garde ses quants sur `Partenaires/Clients` ; la règle bloquait tout colis ayant des quants.
- Fait : seul le stock en emplacement interne ou de transit bloque l'archivage ; message limité à 20 colis ; filtre « Vides » remplacé par « Hors stock » ; version 18.0.4.4.1.
- Bases : lecture seule TEST (quants des colis).
- Modules/modèles : `picking_custom_addons` · `stock.quant.package`.
- Commit : `b32a9a2` sur `feat/archivage-colis` (poussé).
- **Validé en TEST** par l'utilisateur (archivage en masse « Hors stock » sans erreur). PR vers `18.0` : deepcodesystem/sofalgri#2. PROD : non déployé.

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
