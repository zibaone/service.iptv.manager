# 02 — Backlog des correctifs

Les numéros de ligne cités correspondent à `d107225d` (version 0.2.7), l'état d'avant la passe du 25/10/2026 ; les fichiers touchés depuis ont bougé.
Chaque fiche suit le même plan : symptôme, cause, emplacement, correctif, tests,
critère d'acceptation, risque. Le statut indique ce qui est déjà fait dans le
fork.

## État après la passe du 25/10/2026

Livré dans cette passe, tests verts (42) et pylint propre :

- `efff4c7`, `70057c6`, `569e401` — documentation du fork, statuts, tests du
  contrat fournisseur et du chemin de retry ;
- `b13b47d` — cibles Kodi 21/22, CI, release sans soumission officielle (F-09) ;
- `e45e2d7` — restart sûr, `setup()` protégé, vérification différée (F-01) ;
- `5938c20` — décodage incrémental et lecture bornée (F-05) ;
- `1c9ce2e` — XMLTV brut en flux (F-06) ;
- `7505b0e` — fichiers de développement hors du zip de release ;
- `33520e2` — diagnostic Kodi 22 (`07`), décision `tv_common` (`06`), fiche F-11 ;
- `8ed7430` — réglages typés, `last_refreshed` déclaré entier (F-11) ;
- `e5ca547` — boucle du service qui survit à une passe en échec (F-11) ;
- `c19900d` — release 0.2.8 : version, `news`, `CHANGELOG` ;
- `d7bbdc8` — écriture refusée sur une passe dégradée (F-02) ;
- `e4f0e39` — reprise avec backoff après une passe incomplète (F-03) ;
- `9c67c48` — setup vérifié, instances préservées (F-04) ;
- `266512e` — release 0.2.9 (branche `release/0.2.9`, depuis `d050d2f`) ;
- `579c300` — release 0.2.10 (sur `master`).

Deux constats du même soir ont ajouté deux documents :

- `06-tv-common.md` — décision de ne pas dépendre de `script.module.tv_common` ;
- `07-incident-kodi22-service.md` — diagnostic de l'arrêt du service sur Kodi 22,
  qui devient le correctif `F-11`.

`F-11` est livré et la 0.2.8 est construite, taguée localement, pas publiée :
elle contient `F-01`, `F-05`, `F-06` et `F-11`. `F-02` et `F-03` (0.2.9) puis
`F-04` (0.2.10) sont livrés dans `master`, mais leurs releases ne sont pas
construites, pour que chaque version couvre un seul mode de panne. Prochaine
étape : vérifier la 0.2.8 sur une box Kodi 22
(`07-incident-kodi22-service.md` §6), puis construire 0.2.9 et 0.2.10. Les
raisons de cet ordre sont en `04-roadmap.md` §1.

## État après la passe du 26/10/2026 (mesure sur box Kodi 21)

La 0.2.10 a tourné sur l'Orange Pi Zero 3 (`kodi-21.3`, cinq fournisseurs,
`pvr.iptvsimple` 21.10.2). La passe complète fonctionne — 569 chaînes, guide
réécrit, `providers_state.json` créé, restart d'IPTV Simple vérifié à +30 s —
mais trois défauts de terrain sont apparus, corrigés en 0.2.11 (`d7a5fc9`) :

- `F-12` — un fournisseur installé sans identifiants (xtream) rend zéro chaîne
  et zéro guide à chaque passe : `state.evaluate()` le comptait comme un
  problème, donc **toutes** les passes restaient `partial`, `last_refreshed`
  n'avançait jamais et le service relançait une passe toutes les 15 min, 1 h
  puis 6 h, avec un restart du PVR à chaque fois.
- `F-13` — une collection réécrite à l'identique déclenchait quand même le
  restart d'IPTV Simple (mesuré : `epg.xml` md5 inchangé, PVR arrêté/relancé).
- `F-11` — `type="integer"` n'existe pas dans le format de réglages que Kodi 21
  parse encore : le réglage n'était pas créé (`failed to parse old setting
  definition` à chaque démarrage) et l'API typée levait `Invalid setting type`
  sur le `select` `refresh_interval` à chaque tour de boucle. L'ordre est
  inversé (chaîne d'abord, typée en repli) et `last_refreshed` repasse en
  `type="text"` caché.

Tests : 78 unitaires verts, pylint 10.00/10.

## Tableau de synthèse

| ID | Priorité | Statut au 25/10/2026 | Version cible |
|---|---|---|---|
| F-01 | P0 | **Corrigé** (`e45e2d7`) — vérification sur box à faire | 0.2.8 |
| F-05 | P1 | **Corrigé** (`5938c20`) | 0.2.8 |
| F-06 | P1 | **Corrigé** (`1c9ce2e`) | 0.2.8 |
| F-09 | P1 | **Corrigé** (`b13b47d`) — tags `v0.2.6`/`v0.2.7` créés localement, à pousser | 0.2.8 |
| F-11 | P0 | **Corrigé** (`8ed7430`, `e5ca547`) — **amendé le 26/10** (`d7a5fc9`) après mesure sur Kodi 21 | 0.2.8 / 0.2.11 |
| F-02 | P0 | **Corrigé** (`d7bbdc8`), publié en 0.2.9 | 0.2.9 |
| F-03 | P0 | **Corrigé** (`e4f0e39`), publié en 0.2.9 | 0.2.9 |
| F-04 | P0/P1 | **Corrigé** (`9c67c48`), publié en 0.2.10 | 0.2.10 |
| F-12 | P0 | **Corrigé** (`d7a5fc9`) — mesuré sur Zero 3 | 0.2.11 |
| F-13 | P0 | **Corrigé** (`d7a5fc9`) — mesuré sur Zero 3 | 0.2.11 |
| F-07 | P1 | Non commencé | 0.3.0 |
| F-08 | P1 | Non commencé | 0.3.0 |
| F-10 | P2 | Non commencé | 0.3.0 |

---

## F-01 — Restart d'IPTV Simple sûr (P0)

**Symptôme.** Après un refresh, le PVR reste à l'arrêt : `PVR.GetChannelGroups`
renvoie 0 groupe et `-32100`, le journal montre « Destroying PVR client →
Stopping → Stopped → Recreating » **sans** « Started ». Constaté sur les deux
boxes en octobre 2026. Même famille que les issues amont #84 et #89 (le refresh
coupe une lecture en cours).

**Cause.** `restart()` fait `disable → sleep(1) → enable`. Sur Kodi 22, l'arrêt
du gestionnaire PVR prend plusieurs minutes ; la réactivation arrive pendant
l'arrêt et le PVR reste stoppé. Le fork a porté l'attente à 8 s (`RESTART_DELAY`,
`iptvsimple.py:28`), ce qui réduit la fenêtre sans la fermer. Deux défauts
subsistent :

1. `addon.py:98` appelle `restart(True)` lors d'un refresh manuel : `force`
   contourne la garde de lecture, donc un refresh pendant une lecture coupe la
   lecture.
2. La garde ne teste que `Pvr.IsPlayingTv` et `Pvr.IsPlayingRadio`
   (`iptvsimple.py:108`) : elle ignore la lecture d'une vidéo, d'un replay ou
   d'un enregistrement.
3. `setup()` fait `_deactivate()` (ligne 54) puis `_activate()` (ligne 75)
   **sans aucune attente** : la configuration automatique du premier démarrage
   peut laisser le PVR stoppé.

**Correctif.**

1. Garde de lecture élargie : `Pvr.IsPlayingTv`, `Pvr.IsPlayingRadio`,
   `Player.HasVideo`, `PVR.IsRecording` (vérifier le nom exact de la condition
   sur Kodi 22). Si vraie → `restart_required = True`, log en `info` (l'amont
   loggue en debug depuis #86, ce qui nous a masqué le report), sortie.
2. `force` ne contourne plus la garde : il ne sert qu'à ignorer un report déjà
   planifié, jamais une lecture en cours.
3. `_wait_for_pvr_stopped(timeout=60)` : boucle de 1 s sur `PVR.GetProperties`
   (`available`). Traiter `-32100` comme « pas encore arrêté », pas comme une
   erreur. Dès que `available` est faux, attendre une marge de 2 s.
4. Après `_activate()`, attendre `available=true` (plafond 60 s). Sinon
   `restart_required = True` : la boucle du service (30 s) réessaiera.
5. `setup()` réutilise le même mécanisme ; plus aucune paire disable/enable
   immédiate.
6. `RESTART_DELAY` disparaît ou devient la marge minimale après détection de
   l'arrêt.

**Tests.** `test_restart_postponed_while_playing`,
`test_restart_waits_for_pvr_stop`, `test_restart_aborts_when_pvr_never_stops`,
`test_setup_does_not_toggle_without_wait` (voir `05-tests-et-verification.md`).

**Acceptation.** Sur box : refresh pendant la lecture d'une chaîne → aucun
restart, log de report, lecture intacte ; à l'arrêt de la lecture, un seul
restart, `available=true`, 124 groupes, 5 143 chaînes. Refresh hors lecture →
PVR `Started`, aucun `Stopped` sans `Started` dans le journal.

**Risque.** Si `PVR.GetProperties` reste indisponible pendant l'arrêt (déjà
observé : `-32100`), une implémentation naïve conclut à l'échec et n'active
jamais. D'où la règle « `-32100` = en cours », et le retry par la boucle du
service.

---

## F-02 — Écriture anti-régression (P0)

**Symptôme.** Après un démarrage à froid, la playlist ne contient que 391
chaînes au lieu de 5 143 : le fournisseur principal, encore froid, a dépassé le
timeout et sa contribution manque. Issues amont #82, #94, #118 : chaînes ou
guide vides après un refresh.

**Cause.** `Addon.refresh()` écrit systématiquement ce qu'il a collecté
(`addon.py:88-93`). Un fournisseur en échec renvoie `[]` ou `{}`
(`addon.py:141-143` et `:198-200`) et la passe remplace un fichier complet par un
fichier incomplet. `os.replace()` (`iptvsimple.py:177` et `:226`) rend le
remplacement atomique, mais n'empêche pas d'écrire un contenu partiel.

**Correctif.**

1. Après collecte, vérifier chaque fournisseur : chaînes non vides, EPG non vide,
   nombre de `#EXTINF` par bloc `## <fournisseur>`.
2. Écrire un état de référence dans le profil de l'addon
   (`providers_state.json`) : pour chaque `addon_id`, nombre de canaux, nombre de
   programmes EPG, horodatage de la dernière passe réussie.
3. Politique : si un fournisseur qui avait N > 0 canaux renvoie 0 → passe
   **dégradée**. Ne pas remplacer `playlist.m3u8` ni `epg.xml`, ne pas avancer
   `last_refreshed`, écrire l'état, logguer, notification non bloquante,
   planifier un retry.
4. Premier démarrage (aucun état) : écrire ce qui existe, mais marquer la passe
   `partial` si un fournisseur a échoué, pour que le retry s'applique.
5. Si tous les fournisseurs échouent : ne rien écrire.

**Tests.** `test_degraded_run_keeps_previous_files`,
`test_all_providers_failing_writes_nothing`.

**Acceptation.** Fournisseur coupé après une passe réussie → fichiers inchangés
(md5 identiques), `state.json` en `partial`, reprise automatique ensuite. Aucun
utilisateur ne perd ses chaînes à cause d'une passe ratée.

**Fichier d'état.** `providers_state.json`, dans le profil de l'addon :
`{"<addon_id>": {"channels": n, "programs": n, "failures": n}, "_meta":
{"last_attempt": ts, "failures": n, "retry_after": ts}}`. Écriture atomique
(`.tmp` puis `os.replace`). Un fichier absent ou corrompu équivaut à un premier
démarrage. Les compteurs de programmes d'un XMLTV brut sont pris par
`RawXmltv.count()`, sans matérialiser le document.

**Risque.** Un fournisseur légitimement vidé (chaînes retirées) reste bloqué
en « dégradé ». Sortie : trois échecs consécutifs acceptent la baisse (le
compteur retombe à zéro), et une passe sans aucune donnée n'écrit jamais une
playlist vide.

---

## F-03 — `last_refreshed` et reprise après échec (P0)

**Symptôme.** Après un refresh raté, plus aucune tentative pendant 24 h.
L'issue #82 décrit exactement cela : « le lendemain, tout disparaît ».

**Cause.** `addon.py:104` écrit `last_refreshed` sans condition, même si la passe
est vide ou partielle. `service.py:45-50` calcule l'échéance à partir de cette
valeur.

**Correctif.**

1. N'écrire `last_refreshed` qu'après une passe complète.
2. Sinon écrire `last_attempt` et `retry_after` (backoff 15 min, 1 h, 6 h ;
   plafond 6 h).
3. La boucle du service consulte `retry_after` en plus de `refresh_interval`.
4. `state.json` (F-08) expose ces valeurs pour le diagnostic.

**Tests.** `test_refresh_retry_after_failure`.

**Acceptation.** Panne fournisseur → l'addon réessaie seul dans le quart
d'heure, sans redémarrage de Kodi, et reprend le rythme normal après succès.

**Risque.** Un retry trop agressif peut marteler un fournisseur fragile ; le
backoff et le plafond de 6 h sont là pour cela. Ne jamais dépasser un essai par
15 minutes.

---

## F-04 — Setup d'IPTV Simple vérifié (P0/P1)

**Symptôme.** Issues #107 et #116 : l'auto-configuration annonce un succès mais
IPTV Simple ne pointe pas vers la playlist. Issue #102 : installation sans PVR,
Kodi plante. Issue #106 : instances multiples.

**Cause.**

1. `setup()` (`iptvsimple.py:40-85`) écrit les réglages sans les relire : aucune
   vérification que `m3uPath` pointe bien vers le fichier généré.
2. Les réglages sont forcés à chaque appel (`epgCache`, `epgTimeShift`,
   `catchupEnabled`, `allChannelsCatchupMode`) : l'auto-setup du démarrage peut
   écraser un choix utilisateur.
3. Les instances multiples sont traitées en **recopiant** `settings.xml` sur
   tous les `*.xml` du profil d'IPTV Simple (lignes 77-83) : la configuration
   d'une deuxième instance est écrasée par celle de la première.
4. `is_configured()` (`:88-103`) ne lit que l'instance par défaut et compare des
   chaînes exactes.
5. Aucune garde si `pvr.iptvsimple` est absent.

**Correctif.**

1. Relire après écriture : `m3uPathType`, `m3uPath`, `epgPathType`, `epgPath`,
   et vérifier que `playlist.m3u8` existe. Si la relecture échoue → `False` +
   log en `warning`.
2. Vérifier la présence de `pvr.iptvsimple` avant tout appel ; si absent, sortir
   proprement (`False`), sans exception.
3. Auto-setup : ne toucher qu'aux chemins `m3u`/`EPG`. Réserver les réglages
   catchup et `epgCache` au setup explicite (bouton des réglages).
4. Instances : recenser `instance-settings-*.xml`. Configurer l'instance qui
   référence déjà `playlist.m3u8` ; si aucune ne le fait, configurer l'instance
   par défaut et **ne pas** recopier sur les autres. Journaliser la liste des
   instances trouvées.
5. `is_configured()` tolère les chemins traduits (`special://`) et ne dépend plus
   de `catchupEnabled` pour décider que la configuration est bonne.

**Tests.** `test_setup_without_pvr_returns_false`, `test_setup_is_read_back`,
`test_setup_with_two_instances`.

**Acceptation.** Installation neuve → chaînes présentes après le premier
démarrage. Installation déjà configurée → aucun réglage utilisateur modifié,
aucune autre instance écrasée.

**Livré (`9c67c48`).** `setup(explicit=False)` : présence vérifiée avant tout
appel (plus d'`InstallAddon` au démarrage), seuls les quatre chemins écrits en
automatique, relecture immédiate avec `_same_path()` et échec en `warning` si
Kodi n'a pas gardé la valeur. Les instances sont lues avec `ElementTree` :
seules celles qui contiennent déjà notre `playlist.m3u8` sont modifiées, et
seulement pour les quatre chemins, par `.tmp` + `os.replace()`. Sans playlist,
`setup()` ne redémarre pas IPTV Simple : `restart_required` est posé et le
premier refresh s'en charge. Un `setSetting` qui lève (Kodi 22) retourne `False`
sans exception. `is_configured()` tolère `special://` et ne regarde plus
`catchupEnabled`.

**Risque.** La détection d'instance dépend du format de fichier de Kodi 20+ ;
tester sur les deux boxes avant de considérer le correctif livré.

---

## F-05 — Socket robuste (P1)

**Symptôme.** Deux défauts distincts :

1. `buf += chunk.decode()` (`addon.py:282`) décode chaque `recv(4096)`
   indépendamment : un caractère UTF-8 à cheval sur deux paquets lève
   `UnicodeDecodeError`. Nos payloads contiennent des accents et pèsent ~1,3 Mo.
2. Après `accept`, `conn.settimeout(None)` (`addon.py:268`) : un fournisseur qui
   se connecte puis n'envoie rien bloque tout le refresh indéfiniment.

**Correctif.**

1. Décodeur incrémental (`codecs.getincrementaldecoder('utf-8')`), accumulation
   en `bytes`, décodage final contrôlé.
2. Timeout de lecture (par exemple 120 s) et taille maximale (par exemple
   64 Mo) ; au dépassement, fermer et traiter comme un échec fournisseur.
3. Logguer le nombre d'octets reçus et la durée, sans jamais afficher l'URL
   complète (elle peut contenir des identifiants pour certains fournisseurs).
4. Documenter le comportement du retry : chaque tentative ouvre un nouveau
   socket, donc le premier `RunPlugin` échoue en « Connection refused » côté
   fournisseur (bénin, déjà observé dans les journaux).

**Tests.** `test_payload_utf8_split_across_chunks`,
`test_provider_connects_then_stalls`, `test_provider_payload_too_large`.

**Acceptation.** Tests verts ; sur box, aucun `UnicodeDecodeError` ; un
fournisseur muet ne bloque plus le refresh au-delà du délai.

---

## F-06 — XMLTV sans double copie (P1)

**Symptôme.** Le XMLTV brut du fournisseur principal pèse ~93 Mo.
`re.search(r'<tv[^>]*>(.*)</tv>', data, flags=re.DOTALL)` (`addon.py:204`)
matérialise le document entier, puis une copie du groupe : pic mémoire proche du
double, sur des boxes à 1–2 Go.

**Correctif.** Localiser `<tv` et `</tv>` avec `find`/`rfind`, puis écrire la
tranche en flux vers le fichier cible (ou retourner un itérateur). Pas de regex,
pas de `.group()`. Si l'enveloppe est absente → erreur fournisseur explicite.

**Tests.** `test_raw_xmltv_small`, `test_raw_xmltv_memory` (mesure
`tracemalloc`).

**Acceptation.** Pic mémoire < ~1,2 × la taille du fichier ; XMLTV invalide
refusé proprement.

---

## F-07 — Premier refresh différé, hors lecture (P1)

**Symptôme.** Issues #88 (chaînes absentes juste après un démarrage à froid) et
#89 (le refresh coupe une lecture en cours).

**Correctif.** Au démarrage du service : attendre que Kodi soit stable (par
exemple 20 s, ou `System.IdleTime`), ne pas lancer de refresh si
`Player.HasVideo` ou `Pvr.IsPlaying*`. Dans ce cas poser `refresh_pending` et
réessayer toutes les 60 s. Le restart d'IPTV Simple reste interdit pendant une
lecture (F-01).

**Tests.** `test_first_refresh_deferred_while_playing`.

**Acceptation.** Démarrage box en lecture → aucun refresh ni restart ; à
l'arrêt, refresh normal et playlist complète.

---

## F-08 — Diagnostic et notification (P1)

**Correctif.** Fichier `state.json` dans le profil, écrit à chaque passe :
horodatage, durée, fournisseurs détectés, canaux et programmes par fournisseur,
résultat (`ok`, `partial`, `failed`), raison, `last_refreshed`, `retry_after`.
Notification non bloquante en cas de passe partielle ou d'échec, texte court.
Résumé d'une ligne dans le journal.

**Tests.** Contenu de `state.json` après passe `ok` et après échec.

**Acceptation.** Le diagnostic d'une panne ne demande plus de fouiller
`kodi.log` à l'aveugle.

---

## F-09 — Assainissement du dépôt, de la CI et des tags (P1)

**Constat.**

- `addon.xml:4` déclare encore `xbmc.python 2.26.0` ; c'est le `postPatch` du
  paquet HavenOS qui le réécrit en `3.0.0`. Le zip du dépôt n'est donc pas
  installable tel quel sur Kodi 21/22.
- `Makefile` : `KODI_PYTHON_ABIS := 3.0.0 2.26.0` et
  `kodi-addon-checker --branch=leia`.
- `.github/workflows/ci.yml` : Python 3.7/3.8/3.9.
- `.github/workflows/addon-check.yml` : `kodi-version: [ matrix ]`.
- `.github/workflows/release.yml` : construit des zips `leia`/`+matrix` et
  soumet au dépôt officiel Kodi (`xbmc/action-kodi-addon-submitter`) — à retirer
  pour un fork.
- Aucun tag `v0.2.6` ni `v0.2.7`.

**Correctif.** Déclarer `xbmc.python 3.0.0` dans `addon.xml` ; aligner Makefile,
CI et addon-checker sur Kodi 21/22 et Python 3.11/3.12 ; supprimer l'étape de
soumission officielle ; créer les tags manquants ; remplacer les badges de
l'amont dans le `README.md`.

**Acceptation.** Zip installable sans `postPatch` ; CI verte ; tag `vX.Y.Z`
correspondant exactement au commit livré.

---

## F-10 — Réglage du catchup (P2)

**Constat.** `catchup="vod"` est ajouté à chaque chaîne
(`iptvsimple.py:167`). Nécessaire pour nos fournisseurs principaux,
discutable pour les fournisseurs qui n'ont pas d'archive : le guide propose alors
un replay qui échoue.

**Correctif.** Réglage `catchup_mode` : `all` (défaut, comportement actuel),
`declared` (n'ajoute l'attribut que si le fournisseur a fourni un
`catchup-source` dans son M3U brut), `none`.

**Tests.** Playlist générée dans les trois modes.

---

## F-11 — Réglages typés et service qui survit à une passe en échec (P0)

**À faire avant F-02 et F-03.** Ces deux correctifs réécrivent `last_refreshed`.
Les construire sur un setter qui arrête le service sur Kodi 22 donnerait des
tests verts en local et une panne sur la box, parce que les stubs de test ne
reproduisent pas la validation de type de Kodi.

**Symptôme.** Sur Kodi 22, le service s'arrête après un refresh :
`EXCEPTION: Invalid setting type` dans le journal, puis plus aucune passe
jusqu'au démarrage suivant. Preuve et mécanisme complet en
`07-incident-kodi22-service.md`.

**Cause.**

1. `resources/settings.xml:4` déclare `<setting id="last_refreshed"
   visible="false"/>` sans `type`.
2. `modules/addon.py:110` écrit par `kodiutils.set_setting_int`.
3. `kodiutils.set_setting_int` (`:195-200`) n'attrape que `AttributeError` et
   `TypeError`.
4. Sur Kodi 22, `setSettingInt` valide le type du schéma et lève
   `RuntimeError("Invalid setting type")`.
5. `service.py` appelle `Addon.refresh()` dans sa boucle sans `try` : l'exception
   sort de la boucle et le service se termine.

**Correctif.**

1. Déclarer `last_refreshed` en `type="integer"` dans `resources/settings.xml`.
2. Lire par l'API typée d'abord : `ADDON.getSettings().getInt(key)` pour un
   entier, `getBool(key)` pour un booléen ; repli sur `ADDON.getSetting(key)`
   quand `getSettings()` n'existe pas.
3. Garder l'ordre legacy pour les booléens non déclarés au schéma : la lecture
   chaîne est silencieuse, `getBool` logge une erreur (leçon du 06/10).
4. Setters : attraper `RuntimeError` en plus de `AttributeError` et `TypeError`,
   puis écrire par l'API chaîne en repli. Si les deux écritures échouent,
   logguer en `warning` et rendre la main sans exception : l'écriture d'un
   réglage ne doit jamais arrêter l'appelant.
5. `service.py` : envelopper `Addon.refresh()` et `IptvSimple.restart()` dans un
   `try/except Exception`, logguer, et continuer la boucle. Une passe en échec
   ne doit jamais arrêter le service.

**Tests.** `test_get_setting_int_prefers_typed_api`,
`test_get_setting_int_falls_back_on_legacy`,
`test_set_setting_int_falls_back_when_type_is_invalid`,
`test_bool_read_keeps_legacy_order`,
`test_service_survives_a_failed_refresh`. Le premier rejoue exactement
`RuntimeError("Invalid setting type")`.

**Acceptation.** Sur une box Kodi 22 : aucune occurrence de
`Invalid setting type` sur une fenêtre couvrant une passe, `last_refreshed` relu
supérieur à zéro, service toujours actif au tour suivant, PVR intact.

**Risque.** Un repli trop large masquerait une vraie erreur de schéma. Le repli
doit logguer en `debug`, et seulement pour `RuntimeError`, `AttributeError` et
`TypeError`.

### Amendement du 26/10/2026 — l'ordre « typé d'abord » ne tient pas sur Kodi 21

Mesuré sur la Zero 3 (`kodi-21.3`). `resources/settings.xml` est au format
hérité (`<settings>` sans `version`), que Kodi 21 parse avec
`CAddonSettings::InitializeFromOldSetting*`
(`xbmc/addons/settings/AddonSettings.cpp`, branche `Omega`). Ce parseur ne
connaît pas `integer` : `last_refreshed` n'était pas créé et Kodi loguait
`failed to parse old setting definition for "last_refreshed" of type "integer"`
à chaque démarrage. Un `select` sans `lvalues` devient une **chaîne**
(`InitializeFromOldSettingSelect`), donc `getInt()` levait
`EXCEPTION: Invalid setting type "integer" for "refresh_interval"` — Kodi logue
l'exception avant de la lever — à chaque tour de boucle (deux lignes / 30 s).

Conséquence : sur Kodi 21 `last_refreshed` n'était jamais écrit (une passe saine
aurait donc rafraîchi toutes les 30 s) et le journal se remplissait d'erreurs.

**Correctif (0.2.11).** `last_refreshed` repasse en `type="text" visible="false"`
(un type que les deux parseurs connaissent) ; `get_setting_int` et
`set_setting_int` lisent puis écrivent d'abord en chaîne, et n'appellent l'API
typée qu'en repli (Kodi 22 refuse la lecture chaîne d'un entier). Les booléens
gardent l'ordre hérité. Tests : `test_reads_the_string_api_first`,
`test_falls_back_to_the_typed_api`, `test_set_writes_the_string_first`,
`test_set_falls_back_to_the_typed_writer`, `test_missing_setting_returns_the_default`.

**Acceptation sur Kodi 22** (reste à faire) : aucune ligne
`Invalid setting type` sur une fenêtre couvrant une passe saine, et
`last_refreshed` avance.

## F-12 — Un fournisseur qui n'a jamais rien publié ne bloque pas le statut (P0)

**Symptôme.** Sur la Zero 3, chaque passe finit `Pass is partial: last_refreshed
not advanced`, `_meta.failures` s'incrémente et le service relance une passe
15 min, 1 h puis 6 h plus tard, avec arrêt/relance du PVR à chaque fois. Le
`playlist.m3u8` est réécrit à l'identique et le guide ne bouge pas : la boucle
ne produit rien.

**Cause.** `plugin.video.xtream` est installé sans identifiants (aucun
`addon_data/plugin.video.xtream/settings.xml`), et son réglage
`iptv.enabled` vaut `true` par défaut dès que `service.iptv.manager` est
installé. Il répond donc zéro chaîne et zéro guide à chaque passe.
`state.evaluate()` marquait `any_problem` pour tout fournisseur vide
(`not channels and not programs`), même sans historique : la passe restait
`partial` pour toujours.

**Emplacement.** `resources/lib/modules/state.py`, `evaluate()`.

**Correctif.** Un fournisseur vide n'est un problème que s'il avait déjà publié
des données (cas déjà couvert par la règle des trois passes sur `dropped`). Un
fournisseur dormant — installé sans compte, ou fonctionnalité désactivée côté
fournisseur — est neutre.

**Tests.** `test_empty_provider_on_a_first_pass_does_not_block_the_status`,
`test_a_provider_that_never_had_data_stays_neutral`,
`test_degraded_pass_keeps_the_previous_files` (non-régression),
`test_three_consecutive_failures_accept_the_decrease` (non-régression).

**Acceptation.** Sur la Zero 3 : `providers_state.json` porte
`"plugin.video.xtream": {"channels": 0, "programs": 0, "failures": 0}`,
`_meta.retry_after` vaut 0, `last_refreshed` avance et aucune passe ne repart
avant l'intervalle de 24 h.

**Risque.** Une panne fugace d'un fournisseur lors de la toute première passe
n'est plus signalée par un retry rapproché : le prochain passage a lieu à
l'intervalle normal. Assumé : sans historique, « vide » et « en panne » sont
indiscernables.

## F-13 — Une collection inchangée ne relance pas IPTV Simple (P0)

**Symptôme.** Le PVR est arrêté et relancé à chaque passe alors que ni la
playlist ni le guide n'ont changé (`epg.xml` md5 identique avant/après,
`playlist.m3u8` réécrit à l'identique).

**Cause.** `Addon.refresh()` appelait `IptvSimple.restart()` dès que la passe
avait le droit d'écrire, sans regarder si les fichiers produits différaient des
précédents.

**Emplacement.** `resources/lib/modules/iptvsimple.py`
(`write_playlist`, `write_epg`) et `resources/lib/modules/addon.py` (`refresh`).

**Correctif.** Les deux écritures rendent `True` seulement quand le contenu
diffère : `_replace_if_changed()` compare le fichier temporaire au fichier en
place (taille puis blocs de 64 Kio), supprime le temporaire et laisse le
fichier intact (mtime inchangé) s'ils sont identiques. `refresh()` ne relance
IPTV Simple que si l'un des deux a changé.

**Tests.** `test_identical_playlist_is_kept`, `test_changed_playlist_is_replaced`,
`test_identical_epg_is_kept`, `test_unchanged_files_do_not_restart_iptv_simple`,
`test_a_changed_playlist_restarts_iptv_simple`.

**Acceptation.** Sur la Zero 3 : une passe qui ne change rien laisse
`playlist.m3u8`/`epg.xml` intacts, logue `Playlist and guide unchanged; IPTV
Simple is left running` et le PVR ne s'arrête pas.

**Risque.** Un redémarrage volontaire d'IPTV Simple n'est plus obtenu par une
passe forcée sans changement ; il reste disponible par le réglage de l'addon
(`Addons.SetAddonEnabled`) ou un redémarrage de Kodi.
