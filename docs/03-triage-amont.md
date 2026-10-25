# 03 — Triage de l'amont (issues et pull requests)

Relevé du **25/10/2026** sur `add-ons/service.iptv.manager` (dépôt archivé) :
31 issues ouvertes, 54 pull requests dont 4 non mergées. Ce document fixe ce
qu'on retient, ce qu'on ignore, et pourquoi. La colonne « Suite » renvoie aux
fiches de `02-correctifs.md`.

## 1. Issues et pull requests retenues (notre chemin critique)

| # | Titre | Verdict | Suite |
|---|---|---|---|
| #84 | postponing iptv simple restart | **À corriger** : c'est notre incident « PVR Stoppé ». Le report ne couvre que TV/radio en direct, pas la lecture d'un enregistrement, et le restart ne vérifie pas l'arrêt. | F-01 |
| #89 | Refreshing channels and guide while viewing OTA recordings and Pluto.TV causes playback to stop | **À corriger** : même cause que #84, avec en plus le refresh qui ne devrait pas démarrer pendant une lecture. | F-01, F-07 |
| #88 | TV channels and guide not displayed just after launching Kodi | **À corriger** : au démarrage à froid, les fournisseurs ne sont pas prêts et le premier refresh échoue ou produit une playlist partielle. | F-07, F-02 |
| #82 | Refresh..... (19 commentaires) | **À corriger** : le refresh échoue sans reprise ; `last_refreshed` est avancé même en échec, donc plus aucune tentative pendant 24 h. | F-02, F-03 |
| #94 | No channels, empty guide | **À corriger** : une passe sans fournisseur valide écrase la playlist par un fichier vide. | F-02 |
| #118 | error unable to load playlist file | **À corriger** : même famille ; vérifier le chemin réel et l'instance configurée, ne pas écrire un fichier inexploitable. | F-02, F-04 |
| #107 | Autoconfigure IPTV Simple Client fails (23 commentaires) | **Partiellement à corriger** : l'auto-configuration annonce un succès sans relire les réglages. On garde l'auto-setup, mais vérifié. | F-04 |
| #116 | Autoconfiguration creates m3u file successfully, but don't set it automatically | **À corriger** : relire `m3uPath`/`epgPath` après écriture ; c'est exactement le défaut de `setup()`. | F-04 |
| #106 | IPTV Simple multiple instances? | **À traiter a minima** : ne pas écraser une autre instance ; documenter le comportement si plusieurs instances existent. | F-04 |
| #102 | IPTV manager install without any PVR or backend crashes Kodi | **À traiter** : aucun crash si `pvr.iptvsimple` est absent. | F-04 |
| #117 | Unable to install on COREELEC — dependency on xbmc.python 2.26.0 | **À corriger** : déclarer `xbmc.python 3.0.0` dans le dépôt, pas seulement via le `postPatch` HavenOS. | F-09 |
| #90 | Channels order not kept | **À ne pas casser** : notre numérotation dépend de l'ordre d'insertion des fournisseurs. Aucun tri ne doit être introduit. | — |
| #95 | Add params for refresh | **Retenu comme fonctionnalité** : refresh d'un seul fournisseur, base d'un refresh rapide et sûr. | Lot 3 |
| #92 (PR) | Improvements — « passive refresh switch » + `last_refreshed` en propriété de fenêtre | **Idée reprise, implémentation non** : un état persisté sur disque, pas une propriété de fenêtre qui disparaît au redémarrage. | F-03 |
| #11 (PR) | Use new settings.xml format | **Retenu plus tard** : gratuit si on ne cible que Kodi 21/22, mais sans effet sur nos incidents. | Lot 3 |

## 2. Issues écartées

| # | Titre | Raison |
|---|---|---|
| #43 | Merge channels from different addons | Nos fournisseurs sont disjoints et regroupés par addon. Aucun besoin. |
| #63 | Actively promote IPTV Manager | Documentation amont, dépôt archivé. |
| #76 | Show group(s) in the channel listing description | Cosmétique PVR, hors périmètre. |
| #87 | version « 0.2.3+matrix.1 » error | Obsolète (versions 0.2.6/0.2.7 du fork). |
| #96 | Locast down | Service disparu. |
| #98 | Simple Client occupied | Pas de reproduction ; à réexaminer seulement si un journal montre autre chose que le défaut de restart (#84). |
| #99 | trouble staying active/functioning | Pas de reproduction ni de trace exploitable. |
| #100 | How exit to deferred mode | Question d'utilisateur sur le timeshift, pas un défaut de l'addon. |
| #101 | Default directory for playlist and epg | Comportement voulu : le profil de l'addon. |
| #104 | SONY Crackle support | Addon tiers, hors périmètre. |
| #108 | VRT Radio Guide empty | Défaut du fournisseur (EPG), pas du gestionnaire. |
| #114 | RTL-TVI / PLUGRTL / CLUBRTL empty | Défaut du fournisseur, pas du gestionnaire. |
| #115 | IPTV Simple Client integration broken | Trop vague sans journal ; rouverte si un cas concret se présente. |
| #119 | VOD not working + VPN feature request | Hors périmètre (VOD/VPN). |
| #120–#123 | Messages publicitaires (divorce, MSP) | Spam. Aucun traitement. |

## 3. Pull requests non mergées

| PR | Auteur / état | Contenu | Verdict |
|---|---|---|---|
| #11 | ouvert, 2020 | Nouveau format `settings.xml` | Reprendre au lot 3, sans urgence. |
| #67 | ouvert, 2021 | Sources externes m3u/XMLTV + gzip/bzip2 | **Rejeté** : nos fournisseurs publient déjà via socket ; surface de maintenance et de sécurité inutile. |
| #92 | fermé sans merge, 2021 | Switch de refresh passif, `last_refreshed` en propriété de fenêtre | Idée retenue, forme rejetée (état sur disque). |
| #93 | fermé sans merge, 2021 | Ordonnancement par addon | **Rejeté** : complexité disproportionnée pour six fournisseurs. |
| #110 | fermé sans merge, 2023 | Bump « update for matrix » | Sans objet, on est au-delà. |

## 4. PR mergées qui nous concernent

| PR | Contenu | Conséquence pour nous |
|---|---|---|
| #86 (2021) | « Use debug logging for postpone message » | Le message de report est en debug : c'est pour cela que nos journaux ne montrent pas le report. Le futur F-01 devra logguer le report en `info` au moins une fois. |
| #109 (2023) | « Fix for Configure IPTV automatically » | Dernier correctif d'auto-configuration de l'amont ; insuffisant (#107/#116 restent ouverts). |
| #113 (2023) | Suppression du support Python 2 / Leia | Base de notre fork (`382c90d`). |

## 5. Règle de tri pour la suite

Une issue amont n'entre dans le backlog que si elle remplit **deux** conditions :

1. elle décrit un défaut qu'on peut relier à un incident constaté sur
   l'appliance, ou à une fonction dont dépendent nos addons ;
2. elle peut être corrigée sans changer l'architecture de l'addon.

Les propositions de fonctionnalités (sources externes, fusion de chaînes,
ordonnancement) restent dehors, même si elles sont bien écrites : ce fork n'a
pas de mainteneur pour les porter.
