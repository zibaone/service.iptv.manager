# 01 — Charte de maintenance du fork

## 1. Objet

`service.iptv.manager` agrège les chaînes et l'EPG de plusieurs addons vidéo
(protocole socket JSON-STREAMS / JSON-EPG), écrit `playlist.m3u8` et `epg.xml`,
puis fait recharger ces fichiers par `pvr.iptvsimple`.

L'amont `add-ons/service.iptv.manager` est archivé depuis décembre 2023. Ce fork
existe pour une seule raison : **rendre l'addon fiable sur une appliance Kodi 21/22
qui redémarre souvent et dont les fournisseurs sont parfois froids ou en panne**.
Ce n'est pas un fork de fonctionnalités.

## 2. Identité de l'addon

| Élément | Valeur | Commentaire |
|---|---|---|
| `id` | `service.iptv.manager` | Conservé : les addons fournisseurs et la configuration existante le référencent. |
| `name` | `IPTV Manager` | Conservé. |
| Licence | `GPL-3.0-only` | Conservée, avec attribution des auteurs d'origine. |
| Version | `0.2.7` | Schéma `0.2.x` ; l'amont s'arrête à `0.2.5+matrix.1`, donc toute version `0.2.6` ou supérieure est prioritaire pour Kodi. |
| Branche de référence | `master` | Seule branche maintenue. |

## 3. Cibles techniques

- Kodi **21 et 22** (les deux boxes de l'appliance tournent sur Kodi 22).
- Python 3 uniquement. Le code Python 2 de l'amont n'est pas maintenu.
- `addon.xml` doit déclarer `<import addon="xbmc.python" version="3.0.0"/>`.
  **État actuel non conforme** : le fichier déclare encore `2.26.0` ; le paquet
  Nix de HavenOS corrige la valeur avec `postPatch`. Cette correction doit être
  faite dans le dépôt (voir `F-09`), pour que le zip publié soit installable tel
  quel.
- Dépendances conservées : `script.module.dateutil`, `pvr.iptvsimple`.
  Aucune dépendance nouvelle sans décision écrite ici.

## 4. Contrat d'interopérabilité à ne jamais casser

Les addons fournisseurs du dépôt `tv-addons` dépendent des points suivants.
Toute évolution doit les préserver, et un test doit le vérifier.

1. **Socket local, une connexion par requête** : l'addon gestionnaire ouvre un
   socket sur `localhost`, passe `?port=<n>` dans l'URI `plugin://`, lance
   `RunPlugin`, puis lit jusqu'à la fermeture de la connexion.
2. **JSON-STREAMS v1** : `{"version": 1, "streams": [...]}` avec `name` et
   `stream` obligatoires ; `group` accepté en liste ou en chaîne séparée par `;`.
3. **JSON-EPG v1** : `{"version": 1, "epg": {...}}`, ou **XMLTV brut** accepté
   tel quel (le gestionnaire retire l'enveloppe `<tv>`).
4. **M3U brut accepté tel quel** : un fournisseur peut renvoyer une playlist
   complète ; le gestionnaire la recopie sans la réécrire (seul l'en-tête
   `#EXTM3U` est retiré). C'est ce qui transporte aujourd'hui
   `catchup-source`, le marqueur `src=epg` et les attributs de replay.
5. **Marqueurs de fournisseur** : chaque bloc commence par `## <addon_name>`
   dans `playlist.m3u8`. Ils servent au diagnostic et à la vérification de
   complétude ; ne pas les supprimer.
6. **Encodage** : les payloads JSON doivent rester lisibles en ASCII ou en UTF-8
   valide ; le lecteur socket doit être incrémental (voir `F-05`).

## 5. Règles de maintenance

- **Diff minimal** : corriger la cause, pas refondre le module. Pas de
  réorganisation de fichiers sans nécessité démontrée.
- **Un correctif = un commit + un test de régression** qui échoue avant.
- **Le style Kodi d'origine est conservé** (`from __future__ import ...`,
  docstrings, `_LOGGER`), même s'il paraît daté : cela réduit les conflits avec
  l'amont et les outils de l'écosystème.
- **Logs en anglais**, messages techniques en anglais ; documentation en
  français.
- **Aucune donnée d'infrastructure** dans le dépôt (adresse de box, nom de
  machine, domaine de fournisseur, identifiants) : le fork est public.
- **Pas de redémarrage Kodi** pour déployer : l'addon est un service, il se
  recharge par `Addons.SetAddonEnabled`.

## 6. Distribution et conformité GPL

- Le fork est **public** et le restera : c'est la contrepartie GPL de la
  distribution du binaire (zip) à des tiers.
- Les zips de version sont produits par le `Makefile` (`make zip release=1`) ou
  par le workflow de release, puis publiés comme *assets* GitHub. Un tag annoté
  `vX.Y.Z` doit correspondre exactement au commit livré.
- **La soumission automatique au dépôt officiel Kodi doit être neutralisée** :
  le workflow hérité de l'amont tente de publier dans `xbmc/repo-scripts`, ce
  qui n'a pas de sens pour un fork (voir `F-09`).
- Pour l'appliance, deux canaux de distribution coexistent :
  1. **HavenOS** : `pkgs/iptv-manager/default.nix` épingle un `rev` et un
     `hash` (`fetchFromGitHub`). Toute nouvelle version exige la mise à jour de
     ces deux valeurs (procédure en `04-roadmap.md`).
  2. **Dépôt d'artefacts Kodi** : si les boxes doivent se mettre à jour sans
     réinstallation, le zip doit être ajouté au dépôt d'artefacts utilisé par
     les boxes, avec l'entrée `addons.xml` correspondante.

## 7. Décisions déjà prises

| # | Décision | Portée |
|---|---|---|
| D1 | Pas de refonte : on corrige les fonctions existantes. | Tout le fork |
| D2 | `os.replace()` pour les fichiers finaux (au lieu de `remove` + `rename`). | `iptvsimple.py:177`, `:226` |
| D3 | Timeout de socket porté à 30 s, avec un retry. | `addon.py:260` et boucle `_get_data_from_addon` |
| D4 | Attente de 8 s avant réactivation d'IPTV Simple (au lieu de 1 s). | `iptvsimple.py:28` |
| D5 | Configuration automatique d'IPTV Simple au démarrage si non configuré. | `service.py`, `iptvsimple.py:88` |
| D6 | Interface et identifiant conservés ; aucune nouvelle dépendance. | `addon.xml` |

Les décisions D3, D4 et D5 sont **provisoires** : elles corrigent le symptôme,
pas encore la cause. Elles seront remplacées par les correctifs `F-01` et
`F-04` (voir `02-correctifs.md`).

## 8. Ce que ce fork refuse explicitement

- Les fonctionnalités hors besoin de l'appliance : fusion de chaînes entre
  addons (issue #43), sources externes m3u/XMLTV (PR #67), ordonnancement par
  addon (PR #93), VOD ou VPN (issue #119).
- Le support de Kodi 18/19 et de Python 2.
- Les contributions upstream : le dépôt amont est archivé, aucune PR n'y est
  possible. Les références aux issues amont servent uniquement de mémoire du
  défaut.

## 9. Points à trancher (propriétaire du fork)

| # | Question | Recommandation |
|---|---|---|
| Q1 | Attente fixe de 8 s ou attente vérifiée de l'arrêt du PVR ? | Attente vérifiée, avec plafond et repli (F-01). |
| Q2 | En cas de passe dégradée (un fournisseur manquant) : conserver l'ancienne playlist ou écrire la nouvelle partielle ? | Conserver l'ancienne et réessayer (F-02). |
| Q3 | Réactiver `iptv_simple_restart=true` sur les boxes après F-01 ? | Oui, mais seulement après vérification sur une box, lecteur actif puis inactif. |
| Q4 | Publier le zip dans le dépôt d'artefacts des boxes, ou rester sur le pin HavenOS ? | Les deux : le pin pour l'image, le dépôt pour la mise à jour sans réinstallation. |
| Q5 | Garder le `postPatch` HavenOS qui réécrit `xbmc.python` ? | Non, une fois `F-09` livré : le dépôt doit être correct par lui-même. |
