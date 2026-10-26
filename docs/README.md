# Documentation du fork — index

Ce dossier décrit la maintenance du fork `zibaone/service.iptv.manager`.
Il ne documente pas l'amont : pour le fonctionnement général de l'addon, voir le
`README.md` et le wiki du dépôt `add-ons/service.iptv.manager` (archivé).

## État au 26/10/2026

- Branche `master` : version **0.2.11**, vingt-deux commits au-dessus du pin
  `d107225`, tout poussé (tags `v0.2.6` → `v0.2.11`).
- Base amont `382c90d` (« Remove python 2.7 / Leia support »), puis trois commits
  du fork (`a1bbc8d` restart et timeout, `6ebd19c` shell Nix, `d107225` auto-setup),
  puis la passe du 25/10 : `efff4c7` (docs), `b13b47d` (cibles Kodi 21/22),
  `e45e2d7` (restart sûr), `5938c20` (socket), `1c9ce2e` (XMLTV en flux),
  `70057c6` et `569e401` (statuts et tests), `7505b0e` (zip sans fichiers de dev),
  `33520e2` (diagnostic Kodi 22 et décision `tv_common`), `8ed7430` et `e5ca547`
  (réglages typés et service résilient, F-11), `c19900d` (release 0.2.8),
  `d7bbdc8` (écriture anti-régression, F-02), `e4f0e39` (reprise avec backoff,
  F-03), `9c67c48` (setup vérifié et instances préservées, F-04), `266512e`
  (release 0.2.9), `579c300` (release 0.2.10), puis la passe de terrain du
  26/10 : `d7a5fc9` (F-12 fournisseur dormant, F-13 réécriture et restart
  seulement si le contenu change, F-11 amendé pour Kodi 21) et `02bfd70`
  (release 0.2.11).
- Tests : `nix develop --command pytest -q tests` → **78 passés** (8 s),
  `pylint` 10/10 ; couverture non remesurée le 26/10 (le run `--cov` du harnais
  se bloque), dernière mesure connue 82 % à 72 tests.
- `F-01`, `F-02`, `F-03`, `F-04`, `F-05`, `F-06`, `F-09`, `F-11` (amendé),
  `F-12` et `F-13` livrés : plus d'arrêt du service sur Kodi 22, plus de
  playlist écrasée par une passe incomplète, reprise dans le quart d'heure,
  setup relu et instances préservées, fournisseur dormant neutre, PVR relancé
  seulement si le contenu change, réglages lisibles sur Kodi 21 comme sur 22.
- Zips 0.2.8 → 0.2.11 construits localement (`git archive`, mêmes exclusions
  `.gitattributes`) et déposés dans `tv-addons/external/service.iptv.manager/`
  avec leur md5 : 0.2.8 (F-01, F-05, F-06, F-11), 0.2.9 (F-02, F-03), 0.2.10
  (F-04) et 0.2.11, cette dernière étant la version déployée sur la Zero 3.
- Vérifié sur la Zero 3 (Kodi 21.3) le 26/10 : addon `v0.2.11`, zéro
  `Invalid setting type`, `last_refreshed` écrit, `_meta.failures: 0` /
  `retry_after: 0`, EPG identique laissé intact, PVR 569 chaînes / 45 groupes.
- Prochaine étape : vérifier la 0.2.11 sur une box **Kodi 22**
  (`07-incident-kodi22-service.md` §6).

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
