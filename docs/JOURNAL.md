# Sofalgri — Journal des interventions

Format d'une entrée : date · demande · ce qui a été fait · base(s) concernée(s) · modules/modèles touchés · commit éventuel.
Les entrées les plus récentes en haut.

---

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
