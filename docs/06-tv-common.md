# 06 — Dépendre de `script.module.tv_common` ?

## 1. Question et verdict

Faut-il que `service.iptv.manager` importe `script.module.tv_common`, la
bibliothèque partagée des addons TV du dépôt `tv-addons` ?

**Verdict : non pour une dépendance runtime. Oui pour deux emprunts ciblés.**

Le recouvrement réel est d'environ 150 lignes de glu Kodi, et les règles de ces
deux morceaux de code ne sont pas identiques. Le service doit rester installable
seul : c'est lui qui fournit les chaînes et le guide, il ne peut pas dépendre
d'une bibliothèque écrite pour les addons de contenu.

## 2. Ce que contient la bibliothèque

| Élément | Valeur |
|---|---|
| Taille | 3 575 lignes, 21 modules |
| Licence | MIT |
| Dépendances déclarées | `script.module.requests` 2.25.0, `script.module.inputstreamhelper` 0.6.1 |
| Rôle | provider abstrait, gestionnaires stream/catchup, client IPTV Manager, réglages typés, cache, sources, interface, téléchargement, réparation TS |

Point important : `managers/iptv_manager.py` est le **côté émetteur** du
protocole. Il ouvre une connexion vers `127.0.0.1:<port>` et envoie le JSON.
Notre `resources/lib/modules/addon.py` est le **côté récepteur** : il écoute,
lit et analyse. Les deux côtés ne partagent pas du code, ils partagent un
contrat.

## 3. Recouvrement réel, bloc par bloc

| Bloc | Où | Verdict |
|---|---|---|
| Lecture et écriture de réglages typés | `tv_common/utils/kodi.py:44-105` et `kodiutils.py:129-209` | **Seul bloc qui compte.** Leur version lit par `addon.getSettings().getInt()` avec repli legacy ; c'est le correctif Kodi 22. La nôtre lit encore par l'API chaîne. |
| `jsonrpc`, `execute_builtin`, `get_addon`, chemins d'addon | `kodiutils.py:242-296` | Recouvrement de forme seulement. Leur `jsonrpc` rend du JSON brut, le nôtre lève et journalise. Gain nul. |
| `_xml_encode` | `iptvsimple.py:416-425` | Dix lignes. Les copier coûte moins cher que dépendre. |
| `localize` | `kodiutils.py:121-126` (`SafeDict`) et `utils/kodi.py` (`Formatter().vformat`) | Le nôtre tolère les clés manquantes. Pas d'alignement souhaitable. |
| `via_socket` et `IPTVManager` | `tv_common/managers/iptv_manager.py` | C'est l'autre côté du protocole. Rien à factoriser en code : c'est un contrat à tester. |
| HTTP avec backoff, cache JSON, `sources.xml`, TS timeline, téléchargement, interface | tout le reste de `tv_common` | Le service ne fait aucun HTTP, n'a pas d'interface et écrit ses fichiers par `os.replace`. Aucun usage. |

## 4. Avantages d'une dépendance

- Un seul endroit pour les pièges Kodi. Le getter typé Kodi 22 existe déjà et
  il est éprouvé sur les deux boxes.
- Environ 150 lignes de duplication en moins, et une politique de réglages et de
  logs homogène entre les addons de contenu et le service.

## 5. Inconvénients, par gravité

1. **Chaîne de dépendances sur un service.** `import tv_common` charge
   `managers/__init__.py`, qui charge `stream_manager.py`, qui fait
   `import inputstreamhelper` au niveau module (`stream_manager.py:6`). Si un
   maillon manque, Kodi refuse de démarrer le service : plus de guide, plus de
   restart du PVR, aucune erreur visible pour l'utilisateur. Aujourd'hui le
   service est autonome, c'est ce qui le rend réparable.
2. **Couplage de versions.** Les addons de contenu exigent déjà 0.4.2 et 0.4.9,
   et la box de test a 0.4.9 installé. Ajouter un quatrième consommateur épinglé
   crée un scénario où une mise à jour de `tv_common` casse le service, ou
   l'inverse.
3. **Identité d'addon implicite.** `utils/kodi.py:11` fait
   `ADDON = xbmcaddon.Addon()` à l'import. Le module suppose être chargé par un
   `plugin.video.*`. Dans un service, l'addon courant devient implicite : cela
   fonctionne, mais c'est un couplage qui produit un défaut six mois plus tard.
4. **Rythme de la bibliothèque.** `tv_common` est passée de 0.4.6 à 0.4.10 en
   quelques semaines (TS timeline, téléchargeur, sources). Le service hériterait
   de ce mouvement sans en utiliser une ligne.
5. **Licence.** Le MIT est absorbable par le GPL-3.0, donc rien ne bloque
   légalement. Mais dès que du code du service entrerait dans `tv_common`,
   celui-ci devrait passer en GPL. La direction doit rester à sens unique.
6. **Tests.** Les 42 tests tournent avec `sakee` seul. Il faudrait simuler
   `tv_common`, `requests` et `inputstreamhelper`, et la CI devrait disposer du
   zip, qui n'est pas sur PyPI.

## 6. Ce qu'on emprunte quand même

1. **Le motif de lecture typée**, porté dans `kodiutils.py` (correctif `F-11`,
   voir `02-correctifs.md` et `07-incident-kodi22-service.md`). Trente lignes,
   pas une dépendance.
2. **`_xml_encode`** reste local : dix lignes, aucune évolution à suivre.
3. **Les fixtures de contrat** : un jeu de payloads de référence (M3U brut,
   JSON-STREAMS, JSON-EPG, XMLTV en UTF-8) exécuté des deux côtés. C'est là que
   les incidents réels sont nés — playlist tronquée, encodage, en-tête
   `## <fournisseur>`. À écrire après `F-02`, quand l'écriture sera stabilisée.

## 7. Règle pour la suite

Si un besoin runtime partagé apparaît, créer un `script.module.iptv.protocol`
séparé : licence MIT, zéro dépendance, environ soixante lignes (versions du
protocole, en-tête de fournisseur, cadrage socket). Il appartiendrait au fork.
Ne pas faire entrer le service dans la dépendance d'une bibliothèque de plugins.

## 8. Critères de réexamen

La décision sera revue si l'une de ces conditions est remplie :

- `tv_common` devient importable sans `inputstreamhelper` ni `requests` sur le
  chemin d'import ;
- le service a réellement besoin d'appels HTTP avec backoff et user-agent ;
- trois blocs de plus de cent lignes se retrouvent dupliqués entre le service et
  la bibliothèque.

Tant qu'aucune ne l'est, la décision tient.
