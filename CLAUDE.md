# Sofalgri — addons Odoo 18.0

## Contexte
- Client : **Sofalgri Export**, exportateur d'avocats (achat vrac → calibrage en OF → frigo → export).
- Odoo 18.0 sur VPS, localisation `l10n_ma`. Addons custom : `/opt/GetapERP/extra-addons/GetapPRO/sofalgri`.
- Ce dépôt (github.com/deepcodesystem/sofalgri, branche `18.0`) contient les modules custom.
- Accès aux données par MCP (`odoo_mcp_manager`, ORM uniquement, pas de serveur ni de fichiers).
- Réponses en français. Avant de proposer un module, vérifier qu'un module installé ne couvre pas déjà le besoin.

Références (à lire) :
@docs/CONTEXTE.md
@docs/JOURNAL.md

## Règles de sécurité MCP
| Serveur MCP | Base | Usage |
|---|---|---|
| `odoo-test` | **TEST** `sofalgri-test` | base par défaut, lecture et écriture (avec accord) |
| `odoo-ai-hub` | **PROD** `sofalgri` | **lecture seule** |

- Toujours utiliser TEST par défaut.
- **Toujours annoncer la base** (TEST ou PROD) de chaque requête, dans la réponse.
- Écriture (create / update / delete / unlink) : d'abord en TEST, montrer ce qui va changer, attendre l'accord.
- **PROD : aucune écriture sans le « OK prod » explicite** de l'utilisateur, donné après validation en TEST. Un accord vaut pour une seule opération.
- `analyze_records` et `ask_ai` envoient des données à un fournisseur IA tiers : ne pas les utiliser sans demande.
- Ne jamais afficher ni committer les jetons d'accès (`.mcp.json` est ignoré par Git).

## Conventions Odoo 18
- Vues `<list>` (jamais `<tree>`), pas d'`attrs` ni `states` : `invisible` / `readonly` / `required` en expressions Python.
- Droits d'accès dans `security/ir.model.access.csv` pour tout nouveau modèle.
- Manifest : `version` au format `18.0.x.y.z`, `author` = `GetapPRO`, `license` renseignée.
- **Incrémenter la version du manifest à chaque modification** du module.
- Déclarer dans `depends` tout module dont on utilise un champ, un modèle ou un xmlid.

## Workflow Git
- Une branche par demande, depuis `18.0` (`feat/…`, `fix/…`, `chore/…`).
- Commits clairs et atomiques, message en français, préfixés par le module (`picking_custom_addons: …`).
- Committer seulement avec l'accord de l'utilisateur ; **jamais de `git push` sans son accord**.
- Le déploiement sur le VPS est fait par l'utilisateur, jamais par Claude.

## Journal
Après chaque tâche significative, ajouter une entrée **en haut** de `docs/JOURNAL.md`
(date · demande · ce qui a été fait · base(s) · modules/modèles touchés · commit),
et mettre à jour `docs/CONTEXTE.md` si l'environnement ou les modules ont changé.
