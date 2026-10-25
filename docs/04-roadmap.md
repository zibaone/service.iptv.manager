# 04 — Roadmap, releases et déploiement

## 0. État au 25/10/2026 (soir)

Quinze commits au-dessus de `d107225` : documentation (`efff4c7`, `70057c6`,
`569e401`, `33520e2`, `76170c5`), cibles Kodi 21/22 (`b13b47d`), F-01
(`e45e2d7`), F-05 (`5938c20`), F-06 (`1c9ce2e`), zip sans fichiers de
développement (`7505b0e`), F-11 (`8ed7430`, `e5ca547`), release 0.2.8
(`c19900d`), F-02 (`d7bbdc8`), F-03 (`e4f0e39`). 65 tests verts, `pylint` 10/10,
couverture 82 %.

Le même soir, deux constats ont changé le plan :

- sur Kodi 22, le service s'arrête à l'écriture de `last_refreshed`
  (`07-incident-kodi22-service.md`) : c'est `F-11`, prioritaire sur tout le
  reste ;
- dépendre de `script.module.tv_common` est écarté (`06-tv-common.md`) : on
  emprunte le motif de lecture typée, rien de plus.

Le lot 1 est donc scindé en trois releases. Une release par mode de panne, pour
que la vérification sur box désigne un seul coupable.

La 0.2.8 est construite : version et `news` dans `addon.xml`, section datée du
`CHANGELOG`, zip relu (43 fichiers, version 0.2.8, sans `tests/`, `docs/`,
`flake.nix` ni `.github/`), tag `v0.2.8` créé localement. Rien n'est poussé ni
publié. `F-02` et `F-03` sont livrés dans `master` et partiront en 0.2.9, après
la vérification de la 0.2.8 sur une box Kodi 22 avec le protocole de
`07-incident-kodi22-service.md` §6.

## 1. Vue d'ensemble

| Lot | Version | Contenu | Critère de sortie |
|---|---|---|---|
| **0** | `0.2.7` | Documentation, assainissement du dépôt, tags | **Fait** : `addon.xml` installable tel quel, CI qui ne soumet plus au dépôt officiel, tags `v0.2.6` et `v0.2.7` créés. |
| **1a** | `0.2.8` | **Fait, tagué** — `F-01`, `F-05`, `F-06`, `F-11` réglages typés et service résilient | Sur une box Kodi 22 : aucune occurrence de `Invalid setting type`, `last_refreshed` écrit, service toujours actif au tour suivant, PVR `Started`. |
| **1b** | `0.2.9` | **Fait dans `master`** — `F-02` écriture anti-régression, `F-03` reprise avec backoff : ils partagent le même fichier d'état et la même fonction `refresh()` | Fournisseur coupé : `playlist.m3u8` et `epg.xml` inchangés (md5 identiques), retry dans le quart d'heure, reprise normale ensuite. |
| **1c** | `0.2.10` | `F-04` setup vérifié | Installation neuve : chaînes présentes ; installation déjà configurée : aucun réglage ni aucune instance écrasés. |
| **2** | `0.3.0` | `F-07` boot différé, `F-08` diagnostic, `F-10` catchup, refresh d'un fournisseur (#95), format `settings.xml` (#11) | `state.json` lisible, catchup dans les trois modes, refresh d'un seul fournisseur. |
| **3** | décision | Sources externes (#67) | **Non planifié** : rejeté par la charte. |

Chaque lot se termine par une release taguée et vérifiée sur les boxes avant de
passer au suivant. Aucun lot ne démarre sans les tests du précédent au vert.

## 2. Détail des lots

### Lot 0 — socle propre (fait)

1. `F-09` : `addon.xml` en `xbmc.python 3.0.0` ; `Makefile`, `addon-check.yml`
   et `ci.yml` alignés sur Kodi 21/22 et Python 3.11/3.12.
2. `release.yml` : plus de soumission au dépôt officiel, seulement la release
   GitHub et l'attachement du zip.
3. Tags `v0.2.6` et `v0.2.7` créés localement, à pousser avec la branche.
4. `README.md` : badges du fork.
5. Zip de release : ni `tests/`, ni `flake.nix`, ni `.github/`.

### Lot 1a — arrêt du service et réglages (0.2.8)

Ordre de commit :

1. `fix(kodiutils): read and write settings through the typed API` — `F-11`,
   avec le repli legacy et le test qui rejoue `RuntimeError("Invalid setting
   type")`.
2. `fix(service): keep the loop alive when a pass fails` — `F-11`, garde
   `try/except` autour de `Addon.refresh()` et `IptvSimple.restart()`.
3. `chore(settings): declare last_refreshed as an integer` — schéma.
4. `chore(release): 0.2.8`.

`F-01`, `F-05` et `F-06` sont déjà dans `master` et partent avec cette release.

### Lot 1b — intégrité des fichiers (0.2.9, fait dans `master`)

1. `feat(addon): track per-provider results` — `F-02`, état de référence.
2. `fix(addon): keep the previous files on a degraded pass` — `F-02`.
3. `fix(service): only mark a refresh as done when it succeeded` — `F-03`,
   `retry_after` et backoff 15 min / 1 h / 6 h.
4. `chore(release): 0.2.9`.

### Lot 1c — configuration d'IPTV Simple (0.2.10)

1. `fix(iptvsimple): verify the settings after setup()` — `F-04`.
2. `fix(iptvsimple): configure one instance and leave the others alone` — `F-04`.
3. `fix(iptvsimple): return False when pvr.iptvsimple is missing` — `F-04`.
4. `chore(release): 0.2.10`.

### Lot 2 — diagnostic et fonctionnalités utiles (0.3.0)

1. `fix(service): defer the first refresh and skip it during playback` — `F-07`.
2. `feat(addon): write a run summary in state.json` — `F-08`.
3. `feat(iptvsimple): make the catchup attribute configurable` — `F-10`.
4. `feat(addon): allow refreshing a single provider` — #95.
5. `chore(settings): migrate to the new settings.xml format` — #11, si le test
   de non-régression des réglages passe.
6. `chore(release): 0.3.0`.

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
