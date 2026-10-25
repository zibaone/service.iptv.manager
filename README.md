[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-yellow.svg)](https://opensource.org/licenses/GPL-3.0)
[![Release](https://img.shields.io/github/v/release/zibaone/service.iptv.manager)](https://github.com/zibaone/service.iptv.manager/releases)

# IPTV Manager
This Service Add-on allows supported IPTV Add-ons to integrates their Live TV and Radio Channels in the Kodi TV integration.

> **HavenOS fork.** Upstream was archived in December 2023. This fork only
> carries appliance fixes: automatic IPTV Simple setup on first run, a safe
> IPTV Simple restart on Kodi 22, one retry when a provider misses the socket
> timeout, and atomic playlist/EPG replacement. No feature work is planned
> here.
>
> Maintenance plan, fix backlog, upstream triage and test protocol live in
> [`docs/`](docs/README.md). Read `docs/01-charte.md` before changing anything.

IPTV Manager will periodically poll those Add-ons for Channels and EPG data, and generate a new M3U playlist and
XMLTV file that the Kodi PVR Addon [IPTV Simple](https://github.com/kodi-pvr/pvr.iptvsimple) can use. IPTV Manager
doesn't require a backend like TVHeadend since it handles all the streams inside Kodi. This is also the only way 
(that we know of) to play DRM protected streams with the Kodi TV integration.

More information and documentation for developers can be found on our [Wiki page](https://github.com/add-ons/service.iptv.manager/wiki).

## Features
* Integrates Live TV Channels with EPG data in Kodi from supported IPTV Add-ons
* Allows playback of past and future programs directly from the EPG

## Screenshots
<table>
  <tr>
    <td><img src="resources/screenshot01.jpg" width=270></td>
    <td><img src="resources/screenshot02.jpg" width=270></td>
    <td><img src="resources/screenshot03.jpg" width=270></td>
  </tr>
  <tr>
    <td><img src="resources/screenshot04.png" width=270></td>
    <td><img src="resources/screenshot05.png" width=270></td>
    <td><img src="resources/screenshot06.png" width=270></td>
  </tr>
</table>

Skin: [Arctic: Zephyr 2](https://forum.kodi.tv/showthread.php?tid=339791)
