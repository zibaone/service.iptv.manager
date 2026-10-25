# Documentation du fork — index

Ce dossier décrit la maintenance du fork `zibaone/service.iptv.manager`.
Il ne documente pas l'amont : pour le fonctionnement général de l'addon, voir le
`README.md` et le wiki du dépôt `add-ons/service.iptv.manager` (archivé).

## État au 25/10/2026

- Branche `master` : version **0.2.8**, quinze commits au-dessus du pin `d107225`.
- Base amont `382c90d` (« Remove python 2.7 / Leia support »), puis trois commits
  du fork (`a1bbc8d` restart et timeout, `6ebd19c` shell Nix, `d107225` auto-setup),
  puis la passe du 25/10 : `efff4c7` (docs), `b13b47d` (cibles Kodi 21/22),
  `e45e2d7` (restart sûr), `5938c20` (socket), `1c9ce2e` (XMLTV en flux),
  `70057c6` et `569e401` (statuts et tests), `7505b0e` (zip sans fichiers de dev),
  `33520e2` (diagnostic Kodi 22 et décision `tv_common`), `8ed7430` et `e5ca547`
  (réglages typés et service résilient, F-11), `c19900d` (release 0.2.8),
  `d7bbdc8` (écriture anti-régression, F-02), `e4f0e39` (reprise avec backoff, F-03).
- Tests : `nix develop --command pytest -q tests` → **65 passés** (10 s), couverture 82 %.
- `F-11` livré : plus d'arrêt du service sur Kodi 22. `F-02` et `F-03` livrés
  dans `master` (plus de playlist écrasée, reprise dans le quart d'heure) et
  prévus pour la 0.2.9.
- 0.2.8 (F-01, F-05, F-06, F-11) construite et taguée localement (`v0.2.8`), zip
  relu ; **rien n'est poussé ni publié**.
- Prochaine étape : vérifier la 0.2.8 sur une box Kodi 22, puis `F-04` (0.2.10).

## Plan de lecture

| Document | Contenu |
|---|---|
| [`01-charte.md`](01-charte.md) | Périmètre, règles de maintenance, contrat d'interopérabilité, distribution, GPL, décisions déjà prises. |
| [`02-correctifs.md`](02-correctifs.md) | Backlog technique : une fiche par correctif (symptôme, cause, code, test, critère d'acceptation, statut). |
| [`03-triage-amont.md`](03-triage-amont.md) | Les 31 issues ouvertes et les 4 PR non mergées de l'amont, avec le verdict retenu pour chacune. |
| [`04-roadmap.md`](04-roadmap.md) | Lots de travail, versions, critères de sortie, publication, mise à jour du pin HavenOS, déploiement sur les boxes. |
| [`05-tests-et-verification.md`](05-tests-et-verification.md) | Comment lancer les tests, ce qui existe, les régressions à écrire, le protocole de vérification sur box. |
| [`06-tv-common.md`](06-tv-common.md) | Faut-il dépendre de `script.module.tv_common` ? Recouvrement mesuré, avantages, inconvénients, décision. |
| [`07-incident-kodi22-service.md`](07-incident-kodi22-service.md) | Le service s'arrête sur Kodi 22 (`Invalid setting type`) : preuve, mécanisme, correctif `F-11`, vérification sur box. |

## Conventions du dépôt

- Prose (documents, commentaires de conception) en français ; messages de log,
  identifiants et code en anglais.
- Un correctif = un commit + au moins un test qui échoue sans lui.
- Pas de nouvelle dépendance Python sans justification écrite dans
  `02-correctifs.md` ou `06-tv-common.md`.
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
