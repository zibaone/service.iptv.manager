# 04 — Roadmap, releases et déploiement

## 0. État au 25/10/2026 (soir)

Lot 0 livré (`b13b47d`). Trois correctifs du lot 1 livrés en avance : F-01 (`e45e2d7`),
F-05 (`5938c20`), F-06 (`1c9ce2e`). Restent F-02, F-03 et F-04 avant la 0.2.8, puis la
vérification sur box et la mise à jour du pin HavenOS.

## 1. Vue d'ensemble

| Lot | Version | Contenu | Critère de sortie |
|---|---|---|---|
| **0** | `0.2.7` (inchangée) | Documentation, assainissement du dépôt, tags manquants | Tests verts, `addon.xml` installable tel quel, CI qui ne soumet plus au dépôt officiel. |
| **1** | `0.2.8` | `F-01` restart sûr, `F-02` écriture anti-régression, `F-03` reprise après échec, `F-04` setup vérifié | Sur une box : refresh pendant lecture → aucun restart ; refresh sans lecture → PVR `Started`, 5 143 chaînes ; fournisseur coupé → playlist précédente conservée. |
| **2** | `0.2.9` | `F-05` socket robuste, `F-06` XMLTV sans double copie, `F-07` boot différé, `F-08` diagnostic | Pas d'erreur de décodage sur payload accentué ; mémoire stable sur un EPG de ~93 Mo ; état `state.json` lisible. |
| **3** | `0.3.0` | `F-10` catchup configurable, refresh d'un fournisseur (#95), format `settings.xml` (#11) | Réglages visibles et testés dans les trois modes catchup. |
| **4** | décision | Sources externes (#67) | **Non planifié** : rejeté par la charte. |

Chaque lot se termine par une release taguée et vérifiée sur les deux boxes
avant de passer au suivant. Aucun lot ne démarre sans les tests du précédent au
vert.

## 2. Détail des lots

### Lot 0 — socle propre

1. `F-09` : `addon.xml` en `xbmc.python 3.0.0` ; `Makefile`, `addon-check.yml`
   et `ci.yml` alignés sur Kodi 21/22 et Python 3.11/3.12.
2. `release.yml` : retirer l'étape `xbmc/action-kodi-addon-submitter` (soumission
   au dépôt officiel), garder la construction et l'attachement du zip.
3. Tags manquants : `git tag -a v0.2.7 d107225 -m "0.2.7"` (et `v0.2.6`
   sur `a1bbc8d` si l'on veut l'historique complet), puis `git push --tags`.
4. `README.md` : badges du fork, suppression des liens de statut de l'amont.
5. `CHANGELOG.md` : ajouter une section « 0.2.8 » vide en tête, prête à remplir.

Aucun changement de comportement dans ce lot ; c'est volontaire, pour isoler la
release de référence.

### Lot 1 — fiabilité (0.2.8)

Ordre de commit conseillé, un correctif par commit :

1. `fix(iptvsimple): wait for the PVR to stop before re-enabling it` — F-01,
   avec `_wait_for_pvr_stopped()` et la garde de lecture.
2. `fix(iptvsimple): use the safe restart path in setup()` — F-01 (dernière
   partie), suppression du `_deactivate()` suivi d'un `_activate()` immédiat.
3. `fix(addon): keep the previous playlist when a provider fails` — F-02,
   fichier d'état + validation de complétude.
4. `fix(service): only mark a refresh as done when it succeeded` — F-03,
   `retry_after` et backoff.
5. `fix(iptvsimple): verify IPTV Simple settings after setup()` — F-04,
   relecture, absence de PVR, instances multiples.
6. `chore(release): 0.2.8` — versions, `news`, `CHANGELOG`, tests.

Tests attendus dans ce lot : une dizaine de nouveaux cas (voir `05-tests-et-verification.md`), dont les quatre du restart sûr.

### Lot 2 — robustesse (0.2.9)

1. `fix(addon): decode provider payloads incrementally` — F-05.
2. `fix(addon): bound socket reads with a data timeout` — F-05.
3. `perf(addon): stream raw XMLTV without copying it` — F-06.
4. `fix(service): defer the first refresh and skip it during playback` — F-07.
5. `feat(addon): write a run summary in state.json` — F-08.
6. `chore(release): 0.2.9`.

### Lot 3 — fonctionnalités utiles (0.3.0)

1. `feat(addon): allow refreshing a single provider` — #95 ; sert aussi de
   mécanisme de réparation manuelle.
2. `feat(iptvsimple): make the catchup attribute configurable` — F-10.
3. `chore(settings): migrate to the new settings.xml format` — #11, si le test
   de non-régression des réglages passe.
4. `chore(release): 0.3.0`.

## 3. Procédure de release

À exécuter dans l'ordre, sans sauter d'étape :

```sh
# 1. Vérifications
nix develop --command bash -c 'export KODI_HOME="$PWD/tests/home" KODI_INTERACTIVE=0; pytest -q tests'
nix flake check
make check                     # pylint + traductions
git status --short             # doit être vide

# 2. Version
#    addon.xml : version="X.Y.Z" + bloc <news>
#    CHANGELOG.md : section datée
#    commit : chore(release): X.Y.Z

# 3. Tag et publication
git tag -a vX.Y.Z -m "X.Y.Z"
git push origin master
git push origin vX.Y.Z
```

Le workflow de release construit `service.iptv.manager-X.Y.Z.zip` et l'attache au
tag. **Vérifier l'asset après publication** : `unzip -p <zip> addon.xml | grep
version` doit afficher la bonne version, et le zip ne doit contenir ni `tests/`,
ni `flake.nix`, ni `.github/`.

## 4. Mise à jour du pin HavenOS

Le paquet vit dans `pkgs/iptv-manager/default.nix` du dépôt HavenOS. Il épingle
aujourd'hui :

```nix
version = "0.2.7";
rev = "d107225df2ee2a6fe7235b3f7f82c6477194becd";
hash = "sha256-/OFl6qpBOC1rA85edeZxtvWSiIY5lrD5laJPyUWqcTI=";
```

Procédure pour une nouvelle version :

```sh
# 1. Récupérer le commit exact livré
git -C service.iptv.manager rev-parse vX.Y.Z^{commit}

# 2. Calculer le hash de l'archive décompressée (format SRI attendu par fetchFromGitHub)
nix store prefetch-file --json --unpack \
  "https://github.com/zibaone/service.iptv.manager/archive/<commit>.tar.gz" \
  | jq -r .hash

# 3. Mettre à jour version, rev et hash dans default.nix
# 4. Retirer le bloc postPatch qui réécrit xbmc.python quand F-09 est livré
#    (garder la suppression des fichiers de développement)
# 5. Vérifier
nix build .#iptv-manager   # ou la dérivation qui l'inclut
```

Le `postPatch` actuel réécrit `xbmc.python 2.26.0` en `3.0.0`. Tant que `F-09`
n'est pas livré, il reste nécessaire. Après `F-09`, il doit être supprimé : une
image ne doit pas dépendre d'un correctif de fichier pour être installable.

## 5. Déploiement sur les boxes

Préalable : **ne jamais redémarrer Kodi sur la box de travail sans accord
explicite**. Aucune étape ci-dessous n'exige un redémarrage.

1. **Sauvegarde** : `tar czf /storage/backup/iptv-manager-<version>-<date>.tgz`
   du dossier `/storage/.kodi/addons/service.iptv.manager` et de son
   `addon_data/service.iptv.manager/settings.xml`.
2. **Installation** : par le dépôt d'artefacts (mise à jour normale), ou copie
   du zip puis installation depuis Kodi. Vérifier ensuite
   `Addons.GetAddonDetails` → `version` attendue.
3. **Composition de la playlist** : après le premier refresh, vérifier
   `#EXTINF` (attendu 5 143) et la présence des six marqueurs `## <fournisseur>`
   dans `playlist.m3u8`.
4. **PVR** : `PVR.GetChannelGroups` doit renvoyer 124 groupes et
   `PVR.GetProperties` → `available=true`. Le journal ne doit plus contenir
   `PVR Manager: Stopped` sans `Started` derrière.
5. **Restart pendant lecture** : lancer une chaîne, déclencher un refresh ; le
   restart doit être **reporté** (log explicite), la lecture continuer, puis le
   restart se faire une seule fois après l'arrêt.
6. **Réactivation du restart automatique** : une fois les points 4 et 5 validés,
   remettre `iptv_simple_restart=true` dans les réglages du gestionnaire (c'était
   notre filet de sécurité) et refaire un cycle complet.

## 6. Risques et rollback

| Risque | Mitigation |
|---|---|
| Le fork casse la génération de playlist pour un fournisseur | Test d'intégration sur les six fournisseurs ; en cas de doute, `catchup_mode=declared` et retour au M3U brut. |
| La mise à jour automatique installe une version fautive | Tag + asset vérifiés avant de pousser le dépôt d'artefacts ; sauvegarde tgz avant chaque déploiement ; `UPDATE_RULES` permet de revenir en arrière. |
| Le nouveau restart ne redémarre jamais | `restart_required` doit être visible dans `state.json` (F-08) et loggué en info ; action manuelle de secours : reload de `pvr.iptvsimple` avec attente de 8 s. |
| Mémoire insuffisante sur l'EPG | F-06 avant de toucher au fournisseur principal ; mesurer avec `tracemalloc` dans les tests. |

## 7. Décisions en attente

Reprises de `01-charte.md` (§9) : Q1 (attente vérifiée), Q2 (conservation en
cas de passe dégradée), Q3 (réactivation du restart automatique), Q4 (canal de
distribution), Q5 (suppression du `postPatch`). Elles doivent être tranchées
avant le lot 1 pour Q1/Q2, avant la release 0.2.8 pour Q3/Q5.
