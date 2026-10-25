# 07 — Le service s'arrête sur Kodi 22 (`Invalid setting type`)

## 1. Résumé

Sur Kodi 22, l'écriture de `last_refreshed` par `setSettingInt`, sur un réglage
déclaré sans type, lève `RuntimeError`. L'exception remonte jusqu'à la boucle du
service, qui n'a aucune garde : le service s'arrête et ne rafraîchit plus rien
jusqu'au démarrage suivant de Kodi.

## 2. Preuve

Box de l'appliance, Kodi **22.0-RC1** (21.90.901), `service.iptv.manager`
**0.2.5+matrix.1** (la version amont, pas encore le fork). Journal du 25/10/2026 :

```
13:02:09 T:1126 [service.iptv.manager] [resources.lib.modules.addon] Updating IPTV data for plugin.…
13:03:34 T:1126 [service.iptv.manager] [resources.lib.modules.addon] Updating IPTV data for plugin.…
13:07:09 T:1126 error <general>: EXCEPTION: Invalid setting type
```

Trois observations :

- le numéro de fil est le même avant et après : c'est le fil du service ;
- après 13:07:09, le journal ne contient plus aucune ligne `Updating IPTV data` ;
- le PVR ne recharge son guide qu'au démarrage suivant (21:58), pas après une
  passe du service.

## 3. Mécanisme

1. `resources/settings.xml:4` déclare
   `<setting id="last_refreshed" visible="false"/>`, sans attribut `type`.
2. `resources/lib/modules/addon.py:110` appelle
   `kodiutils.set_setting_int('last_refreshed', int(time.time()))`.
3. `resources/lib/kodiutils.py:195-200` n'attrape que `AttributeError` et
   `TypeError`.
4. Sur Kodi 22, `setSettingInt` valide le type déclaré par le schéma et lève
   `RuntimeError("Invalid setting type")`.
5. `resources/lib/service.py` appelle `Addon.refresh()` dans la boucle, sans
   `try` : l'exception sort de la boucle et le service se termine.

Deux conséquences en cascade :

- `last_refreshed` n'est jamais écrit, donc à chaque démarrage
  `_is_refresh_required()` renvoie vrai immédiatement et une passe complète est
  relancée ;
- toute passe qui atteint l'écriture arrête le service, donc les passes
  suivantes n'ont plus lieu.

## 4. Pourquoi les tests ne l'ont pas vu

`sakee` implémente `setSettingInt` sans validation de type. L'appel réussit en
test et échoue sur Kodi 22. Un test ne peut attraper ce défaut qu'en simulant
explicitement l'exception levée par Kodi. C'est la raison pour laquelle `F-11`
doit passer avant `F-02` et `F-03` : ces deux correctifs réécrivent
`last_refreshed`, et leurs tests seraient verts en local pour la même raison.

## 5. Correctif

Le correctif est la fiche `F-11` de `02-correctifs.md` :

1. déclarer `last_refreshed` en `type="integer"` ;
2. lire par l'API typée (`getSettings().getInt`/`getBool`) avec repli legacy ;
3. garder l'ordre legacy pour les booléens non déclarés au schéma ;
4. écrire par l'API typée, avec repli chaîne si Kodi refuse le type ;
5. envelopper `Addon.refresh()` et `IptvSimple.restart()` dans un `try/except`
   dans la boucle du service.

## 6. Vérification sur box

Après déploiement, sans redémarrer Kodi sans accord préalable :

1. `grep -c 'Invalid setting type' /storage/.kodi/temp/kodi.log` doit renvoyer 0
   sur une fenêtre couvrant au moins une passe.
2. La valeur `last_refreshed` du profil doit être supérieure à zéro et ne plus
   changer à chaque tour de boucle.
3. Le journal doit montrer une ligne `Updating IPTV data` par fournisseur et par
   passe, pas une rafale toutes les trente secondes.
4. Le service doit toujours répondre au tour suivant : nouvelle passe à
   l'échéance, pas d'arrêt silencieux.

## 7. Ce qui reste ouvert

- **Déclencheur exact à 13:07.** La passe précédente se termine à 13:03:34 et
  l'exception arrive quatre minutes plus tard. L'hypothèse est qu'une passe
  intermédiaire a échoué côté fournisseur puis atteint l'écriture. À confirmer
  en niveau debug après `F-11`, sans changer le correctif : la garde de la
  boucle couvre tous les cas.
- **Le fork 0.2.7 contient le même code.** Tant que `F-11` n'est pas livré, le
  fork n'est pas immunisé ; il n'a simplement pas encore été déployé sur cette
  box.
