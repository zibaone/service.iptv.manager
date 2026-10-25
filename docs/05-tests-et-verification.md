# 05 — Tests et vérification

## 1. Lancer les tests

Le harnais utilise `sakee` (stubs Kodi) et des addons factices qui parlent
réellement le protocole socket. **Le dossier doit s'appeler
`service.iptv.manager`** : `sakee` déduit l'identifiant de l'addon du nom du
dossier.

```sh
nix develop --command bash -c 'export KODI_HOME="$PWD/tests/home" KODI_INTERACTIVE=0; pytest -q tests'
```

État de référence au 25/10/2026 : **4 tests passés en 22 s**.

```sh
nix flake check    # même chose dans une dérivation Nix
make check         # pylint + vérification des traductions
```

## 2. Ce qui est déjà couvert

| Test | Fichier | Couverture réelle |
|---|---|---|
| `test_setup` | `tests/test_iptvsimple.py` | Appelle `IptvSimple.setup()` avec les stubs ; vérifie seulement que l'appel rend `True`. |
| `test_restart` | `tests/test_iptvsimple.py` | Appelle `restart(force=True)` et vérifie que `restart_required` retombe à `False`. **Ne vérifie ni le délai, ni l'état du PVR, ni le report en lecture.** |
| `test_service` | `tests/test_service.py` | Démarre la boucle du service 5 s et vérifie qu'elle s'arrête. |
| `test_refresh` | `tests/test_integration.py` | Fait un refresh complet avec trois addons factices (`tests/home/addons/plugin.video.example*`), valide le M3U, valide l'EPG contre `tests/xmltv.dtd`, teste la lecture depuis le guide. **C'est le test le plus utile : il exerce le vrai socket.** |

Les addons factices envoient leurs données par socket (`plugin.py`, méthode
`via_socket`), ce qui permet de tester les cas réseau sans mock lourd.

## 3. Régressions à écrire

Chaque test doit échouer sur le code actuel, puis passer avec le correctif.

### Pour F-01 (restart sûr)

| Nom proposé | Scénario | Assertions |
|---|---|---|
| `test_restart_postponed_while_playing` | `xbmc.getCondVisibility` renvoie vrai pour `Pvr.IsPlayingTv` (puis pour `Player.HasVideo`) | `restart_required` reste vrai ; aucun `SetAddonEnabled` émis (espionner `kodiutils.jsonrpc`). |
| `test_restart_waits_for_pvr_stop` | Séquence JSON-RPC simulée : `available=true`, puis `false` après 2 s, puis `true` après réactivation | L'ordre des appels est `disable → attente → enable` ; l'activation n'a lieu qu'après le passage à `false`. Utiliser un faux temps (monkeypatch de `time.sleep`) pour un test instantané. |
| `test_restart_aborts_when_pvr_never_stops` | `available` reste vrai | Pas d'activation ; `restart_required` vrai ; un message d'avertissement est loggué. |
| `test_setup_does_not_toggle_without_wait` | Appel de `setup()` | Aucune paire disable/enable sans attente vérifiée ; le chemin de restart sûr est utilisé. |

### Pour F-02 / F-03 (écriture et reprise)

| Nom proposé | Scénario | Assertions |
|---|---|---|
| `test_degraded_run_keeps_previous_files` | Premier refresh complet, puis un addon factice qui échoue (`Skipping`/timeout) | `playlist.m3u8` et `epg.xml` inchangés (md5 identiques), `state.json` marque la passe `partial`, `last_refreshed` inchangé. |
| `test_all_providers_failing_writes_nothing` | Tous les addons échouent au premier lancement | Aucun fichier créé ; `state.json` marque `failed`. |
| `test_refresh_retry_after_failure` | Échec puis `retry_after` dans le futur | Le service ne relance pas avant l'échéance ; après l'échéance, il relance. |

### Pour F-04 (setup et instances)

| Nom proposé | Scénario | Assertions |
|---|---|---|
| `test_setup_without_pvr_returns_false` | `pvr.iptvsimple` absent de `tests/home/addons` | Retour `False`, aucune exception. |
| `test_setup_is_read_back` | Après `setup()` | `m3uPath`/`epgPath` relus et égaux au chemin attendu ; `playlist.m3u8` existe. |
| `test_setup_with_two_instances` | Deux fichiers `instance-settings-*.xml` | Comportement documenté : l'instance qui pointe déjà vers `playlist.m3u8` est conservée, l'autre n'est pas modifiée. |

### Pour F-05 (socket)

| Nom proposé | Scénario | Assertions |
|---|---|---|
| `test_payload_utf8_split_across_chunks` | Un addon factice envoie un JSON contenant `é` et coupe l'envoi pour que l'octet de continuation tombe sur une frontière de 4 096 octets | Aucune `UnicodeDecodeError` ; les chaînes sont identiques. |
| `test_provider_connects_then_stalls` | Addon factice qui se connecte et n'envoie rien | Échec dans le délai de lecture (par exemple 2 s en test), socket fermé, pas de blocage du refresh. |
| `test_provider_payload_too_large` | Payload au-delà de la limite | Échec propre, message explicite. |

### Pour F-06 (XMLTV)

| Nom proposé | Scénario | Assertions |
|---|---|---|
| `test_raw_xmltv_small` | XMLTV brut de quelques kilo-octets | Contenu écrit identique à l'entrée (sans l'enveloppe `<tv>`). |
| `test_raw_xmltv_memory` | XMLTV de 10 Mo généré | `tracemalloc` : pic mémoire inférieur à ~1,2 × la taille du fichier (pas de double copie). |

### Pour F-07 (démarrage)

| Nom proposé | Scénario | Assertions |
|---|---|---|
| `test_first_refresh_deferred_while_playing` | Lecture active au démarrage du service | Aucun refresh ; `refresh_pending` vrai ; refresh après l'arrêt. |

## 4. Outils de test à ajouter

1. **Addons factices supplémentaires** dans `tests/home/addons/` :
   - `plugin.video.example.slow` — attend 15 s avant de se connecter (teste le
     timeout de 30 s et le retry) ;
   - `plugin.video.example.silent` — se connecte et n'envoie rien ;
   - `plugin.video.example.split` — envoie un JSON accentué en deux paquets
     coupés au milieu d'un caractère ;
   - `plugin.video.example.failing` — ne se connecte jamais.
2. **Espion JSON-RPC** : dans les tests, remplacer `kodiutils.jsonrpc` par une
   fonction qui enregistre les appels et renvoie des réponses programmées. C'est
   la base de `test_restart_waits_for_pvr_stop`.
3. **Faux temps** : `monkeypatch` de `time.sleep` et de `time.time` pour que les
   attentes (8 s, 60 s) ne rallongent pas la suite. Aucun test ne doit durer plus
   de 10 s.

## 5. Vérification sur box (E2E)

À faire sur **une box à la fois**, jamais pendant un enregistrement, et sans
redémarrer Kodi sans accord.

### Préparation

1. `Player.GetActivePlayers` doit renvoyer `[]`.
2. Sauvegarde du dossier de l'addon et de son `addon_data` (voir
   `04-roadmap.md`, §5).
3. Noter l'état de départ : version installée, `PVR.GetChannelGroups` (attendu
   124), `PVR.GetProperties` (`available`).

### Contrôles après déploiement

| Contrôle | Commande / preuve | Attendu |
|---|---|---|
| Version | `Addons.GetAddonDetails` sur `service.iptv.manager` | version du tag |
| Composition | `#EXTINF` dans `playlist.m3u8` et marqueurs `## ` | 5 143 chaînes, six fournisseurs |
| PVR | `PVR.GetChannelGroups`, `PVR.GetProperties` | 124 groupes, `available=true` |
| Journal | `grep -E "PVR Manager|Submitted|Starting"` | aucun `Stopped` sans `Started` |
| Restart en lecture | lancer une chaîne, forcer un refresh | log de report, lecture intacte |
| Restart hors lecture | arrêter la lecture, attendre la boucle | un seul restart, PVR `Started` |
| Panne fournisseur simulée | renommer temporairement le dossier d'un addon fournisseur | playlist précédente conservée, `state.json` en `partial` |

### Preuves à conserver

- sortie de `PVR.GetChannelGroups` et `PVR.GetProperties` avant/après ;
- extrait de journal autour du restart (horodatages) ;
- `playlist.m3u8` : nombre de `#EXTINF` et liste des `## ` ;
- `state.json` de la dernière passe.

Ces preuves vont dans le compte rendu de déploiement, pas dans le dépôt.

## 6. Intégration continue

| Workflow | Cible |
|---|---|
| `ci.yml` | Python 3.11 et 3.12, `pytest -q tests`, `pylint` |
| `addon-check.yml` | `kodi-addon-checker` sur la version Kodi réellement ciblée (21 puis 22) |
| `release.yml` | construction du zip et attachement au tag ; **aucune soumission au dépôt officiel** |

Le `flake.nix` du dépôt reste la source de vérité pour l'environnement de test :
la CI doit l'utiliser (`nix flake check`) plutôt que de réinstaller les
dépendances à la main.
