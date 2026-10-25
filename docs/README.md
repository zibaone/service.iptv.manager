# Documentation du fork — index

Ce dossier décrit la maintenance du fork `zibaone/service.iptv.manager`.
Il ne documente pas l'amont : pour le fonctionnement général de l'addon, voir le
`README.md` et le wiki du dépôt `add-ons/service.iptv.manager` (archivé).

## État au 25/10/2026

- Branche `master` : `d107225d`, version **0.2.7**.
- Trois commits au-dessus de l'amont `382c90d` (« Remove python 2.7 / Leia support ») :
  - `a1bbc8d` — restart IPTV Simple à 8 s, timeout de socket à 30 s avec un retry,
    remplacement atomique de `playlist.m3u8` / `epg.xml` ;
  - `6ebd19c` — shell de test Nix reproductible (`flake.nix`) ;
  - `d107225` — configuration automatique d'IPTV Simple au premier démarrage.
  - puis la passe du 25/10 : `efff4c7` (docs), `b13b47d` (cibles Kodi 21/22), `e45e2d7` (restart sûr),
    `5938c20` (socket), `1c9ce2e` (XMLTV en flux). Voir `02-correctifs.md`.
- Tests : `nix develop --command pytest -q tests` → **24 passés** (10 s) le 25/10/2026, après la passe de correctifs.
- Aucun tag depuis `v0.2.4` : les versions 0.2.6 et 0.2.7 ne sont pas taguées.

## Plan de lecture

| Document | Contenu |
|---|---|
| [`01-charte.md`](01-charte.md) | Périmètre, règles de maintenance, contrat d'interopérabilité, distribution, GPL, décisions déjà prises. |
| [`02-correctifs.md`](02-correctifs.md) | Backlog technique : une fiche par correctif (symptôme, cause, code, test, critère d'acceptation, statut). |
| [`03-triage-amont.md`](03-triage-amont.md) | Les 31 issues ouvertes et les 4 PR non mergées de l'amont, avec le verdict retenu pour chacune. |
| [`04-roadmap.md`](04-roadmap.md) | Lots de travail, versions, critères de sortie, publication, mise à jour du pin HavenOS, déploiement sur les boxes. |
| [`05-tests-et-verification.md`](05-tests-et-verification.md) | Comment lancer les tests, ce qui existe, les régressions à écrire, le protocole de vérification sur box. |

## Conventions du dépôt

- Prose (documents, commentaires de conception) en français ; messages de log,
  identifiants et code en anglais.
- Un correctif = un commit + au moins un test qui échoue sans lui.
- Pas de nouvelle dépendance Python sans justification écrite dans
  `02-correctifs.md`.
- Aucune adresse de box, aucun nom de machine, aucun domaine de fournisseur ni
  identifiant dans les fichiers du dépôt : ce fork est public.

## Commandes utiles

```sh
# Tests (le dossier doit s'appeler service.iptv.manager : sakee utilise son nom)
nix develop --command bash -c 'export KODI_HOME="$PWD/tests/home" KODI_INTERACTIVE=0; pytest -q tests'

# Vérification reproductible (même chose, dans un build Nix)
nix flake check

# Contrôles de style hérités de l'amont
make check   # pylint + traductions
```
