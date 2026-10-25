# Changelog

## v0.2.9 (2026-10-26)

HavenOS fork, data-integrity pass:

- Record per-provider channel and program counts in `providers_state.json`,
  written atomically; a missing or corrupt file means first boot.
- Refuse to replace a good `playlist.m3u8` or `epg.xml` with a degraded pass:
  the files keep their previous content and `last_refreshed` does not move.
- Accept a real decrease after three consecutive identical losses; a pass with
  no data at all never writes an empty playlist.
- Retry an incomplete pass with a backoff of 15 minutes, then 1 hour, then
  6 hours; a complete pass clears it. The service loop consults it before the
  refresh interval.
- Count the programs of a raw XMLTV payload without copying it.
- 65 unit tests, `pylint` clean, 82 % coverage.

## v0.2.8 (2026-10-26)

HavenOS fork, reliability pass:

- Wait for the PVR manager to report the client stopped before re-enabling IPTV
  Simple; postpone the restart while TV, radio, video or a recording is in
  progress, even when the restart is forced.
- Check 30 seconds after a restart that IPTV Simple came back, and retry
  otherwise.
- Read and write numeric settings through the typed API, with a legacy fallback;
  `last_refreshed` is declared as an integer. This fixes
  `EXCEPTION: Invalid setting type` on Kodi 22, which stopped the service.
- Keep the background service alive when a pass raises.
- Decode provider payloads with an incremental UTF-8 decoder, and bound the
  read (120 s, 64 MiB).
- Stream raw XMLTV instead of copying it; an invalid payload is logged and
  skipped instead of breaking the refresh.
- Target Kodi 21/22 only (`xbmc.python 3.0.0`), run CI on Python 3.11/3.12, and
  stop submitting releases to the official Kodi repository.
- 52 unit tests, `pylint` clean, 80 % coverage.

## v0.2.7 (2026-10-25)

- Configure PVR IPTV Simple automatically on first run when it does not point
  to IPTV Manager's `playlist.m3u8` / `epg.xml` yet.

## v0.2.6 (2026-10-25)

HavenOS fork, minimal scope:

- Wait 8 seconds before re-enabling PVR IPTV Simple (Kodi 22 needs more than 1 s).
- Retry a provider once when it misses the initial 30-second socket timeout.
- Replace `playlist.m3u8` and `epg.xml` with `os.replace()` so readers never see
  a missing file during a refresh.

## [v0.2.3](https://github.com/add-ons/service.iptv.manager/tree/v0.2.3) (2021-02-04)

[Full Changelog](https://github.com/add-ons/service.iptv.manager/compare/v0.2.2...v0.2.3)

**Implemented enhancements:**

- Make JSON-STREAMS group a list [\#77](https://github.com/add-ons/service.iptv.manager/pull/77) ([dagwieers](https://github.com/dagwieers))
- Fix logging for Kodi Matrix, allow to install script.kodi.loguploader from the settings [\#75](https://github.com/add-ons/service.iptv.manager/pull/75) ([michaelarnauts](https://github.com/michaelarnauts))
- Add support for resource:// logos [\#74](https://github.com/add-ons/service.iptv.manager/pull/74) ([dagwieers](https://github.com/dagwieers))
- Allow to process raw M3U8 or XMLTV data [\#69](https://github.com/add-ons/service.iptv.manager/pull/69) ([michaelarnauts](https://github.com/michaelarnauts))
- Add support for \#KODIPROP [\#68](https://github.com/add-ons/service.iptv.manager/pull/68) ([michaelarnauts](https://github.com/michaelarnauts))

**Fixed bugs:**

- Fix empty space in start and stop fields when no timezone was specified [\#70](https://github.com/add-ons/service.iptv.manager/pull/70) ([michaelarnauts](https://github.com/michaelarnauts))

**Merged pull requests:**

- Fix/improve the add-on description and summary [\#73](https://github.com/add-ons/service.iptv.manager/pull/73) ([dagwieers](https://github.com/dagwieers))
- Make use of git archive [\#72](https://github.com/add-ons/service.iptv.manager/pull/72) ([dagwieers](https://github.com/dagwieers))
- Verify xmltv output against the xmltv.dtd [\#71](https://github.com/add-ons/service.iptv.manager/pull/71) ([michaelarnauts](https://github.com/michaelarnauts))
- Testing improvements [\#66](https://github.com/add-ons/service.iptv.manager/pull/66) ([michaelarnauts](https://github.com/michaelarnauts))
- Add Romanian strings. [\#65](https://github.com/add-ons/service.iptv.manager/pull/65) ([tmihai20](https://github.com/tmihai20))
- Initial greek translation for IPTV Manager [\#62](https://github.com/add-ons/service.iptv.manager/pull/62) ([Twilight0](https://github.com/Twilight0))
- Add hungarian language translation [\#59](https://github.com/add-ons/service.iptv.manager/pull/59) ([takraj](https://github.com/takraj))
- Improve tests and run tests on Windows [\#58](https://github.com/add-ons/service.iptv.manager/pull/58) ([michaelarnauts](https://github.com/michaelarnauts))

## [v0.2.2](https://github.com/add-ons/service.iptv.manager/tree/v0.2.2) (2020-12-07)

[Full Changelog](https://github.com/add-ons/service.iptv.manager/compare/v0.2.1...v0.2.2)

**Implemented enhancements:**

- Allow passing credits with the EPG data [\#54](https://github.com/add-ons/service.iptv.manager/pull/54) ([michaelarnauts](https://github.com/michaelarnauts))

**Fixed bugs:**

- Rollback pvr.iptvsimple to 3.8.8 [\#57](https://github.com/add-ons/service.iptv.manager/pull/57) ([MPParsley](https://github.com/MPParsley))

**Merged pull requests:**

- Run tests on Python 3.9 [\#55](https://github.com/add-ons/service.iptv.manager/pull/55) ([michaelarnauts](https://github.com/michaelarnauts))

## [v0.2.1](https://github.com/add-ons/service.iptv.manager/tree/v0.2.1) (2020-11-03)

[Full Changelog](https://github.com/add-ons/service.iptv.manager/compare/v0.2.0...v0.2.1)

**Implemented enhancements:**

- Cleanup code by removing play by airdate [\#49](https://github.com/add-ons/service.iptv.manager/pull/49) ([michaelarnauts](https://github.com/michaelarnauts))

**Fixed bugs:**

- Don't throw an error when no addons are installed [\#51](https://github.com/add-ons/service.iptv.manager/pull/51) ([michaelarnauts](https://github.com/michaelarnauts))

**Merged pull requests:**

- Add a release workflow [\#45](https://github.com/add-ons/service.iptv.manager/pull/45) ([dagwieers](https://github.com/dagwieers))

## [v0.2.0](https://github.com/add-ons/service.iptv.manager/tree/v0.2.0) (2020-10-09)

[Full Changelog](https://github.com/add-ons/service.iptv.manager/compare/v0.1.0...v0.2.0)

**Implemented enhancements:**

- Support more than one genre for an episode [\#39](https://github.com/add-ons/service.iptv.manager/pull/39) ([dagwieers](https://github.com/dagwieers))

**Merged pull requests:**

- Fix pylint issues on Python 3 [\#46](https://github.com/add-ons/service.iptv.manager/pull/46) ([dagwieers](https://github.com/dagwieers))
- Add dependency to 'PVR IPTV Simple Client' [\#42](https://github.com/add-ons/service.iptv.manager/pull/42) ([piejanssens](https://github.com/piejanssens))
- Add russian translation [\#37](https://github.com/add-ons/service.iptv.manager/pull/37) ([vlmaksime](https://github.com/vlmaksime))

## [v0.1.0](https://github.com/add-ons/service.iptv.manager/tree/v0.1.0) (2020-06-19)

[Full Changelog](https://github.com/add-ons/service.iptv.manager/compare/763657b57145c1e28a3b52923488ce427b1694ca...v0.1.0)

**Implemented enhancements:**

- Use direct URI to play programs from the EPG in Kodi 18 [\#34](https://github.com/add-ons/service.iptv.manager/pull/34) ([michaelarnauts](https://github.com/michaelarnauts))
- Support start and stop timestamps in vod [\#33](https://github.com/add-ons/service.iptv.manager/pull/33) ([mediaminister](https://github.com/mediaminister))
- Implement genre [\#31](https://github.com/add-ons/service.iptv.manager/pull/31) ([michaelarnauts](https://github.com/michaelarnauts))
- Add support for Kodi Matrix [\#27](https://github.com/add-ons/service.iptv.manager/pull/27) ([michaelarnauts](https://github.com/michaelarnauts))
- Create a new icon [\#22](https://github.com/add-ons/service.iptv.manager/pull/22) ([piejanssens](https://github.com/piejanssens))
- Add an entry to "Program add-ons" [\#20](https://github.com/add-ons/service.iptv.manager/pull/20) ([michaelarnauts](https://github.com/michaelarnauts))
- Allow playing on demand items from the PVR Guide [\#19](https://github.com/add-ons/service.iptv.manager/pull/19) ([michaelarnauts](https://github.com/michaelarnauts))
- Implement refreshing logic [\#9](https://github.com/add-ons/service.iptv.manager/pull/9) ([michaelarnauts](https://github.com/michaelarnauts))
- Add port to given URI [\#5](https://github.com/add-ons/service.iptv.manager/pull/5) ([dagwieers](https://github.com/dagwieers))
- Assorted fixes [\#4](https://github.com/add-ons/service.iptv.manager/pull/4) ([dagwieers](https://github.com/dagwieers))
- Implement socket callback [\#3](https://github.com/add-ons/service.iptv.manager/pull/3) ([michaelarnauts](https://github.com/michaelarnauts))

**Fixed bugs:**

- Bugfix: ContextMenu.Play Format uri string if there is a duration present. [\#32](https://github.com/add-ons/service.iptv.manager/pull/32) ([MarcelRoozekrans](https://github.com/MarcelRoozekrans))
- Various fixes or cleanups [\#26](https://github.com/add-ons/service.iptv.manager/pull/26) ([michaelarnauts](https://github.com/michaelarnauts))
- Various fixes [\#25](https://github.com/add-ons/service.iptv.manager/pull/25) ([michaelarnauts](https://github.com/michaelarnauts))
- Properly encode XML values [\#18](https://github.com/add-ons/service.iptv.manager/pull/18) ([michaelarnauts](https://github.com/michaelarnauts))
- Fix WindowsError: \[Error 183\] Can't create a file that already exists [\#16](https://github.com/add-ons/service.iptv.manager/pull/16) ([GianniDPC](https://github.com/GianniDPC))

**Merged pull requests:**

- Explicitly set no timeout while waiting for data [\#24](https://github.com/add-ons/service.iptv.manager/pull/24) ([michaelarnauts](https://github.com/michaelarnauts))
- Update documentation [\#12](https://github.com/add-ons/service.iptv.manager/pull/12) ([michaelarnauts](https://github.com/michaelarnauts))
- Add integration test [\#10](https://github.com/add-ons/service.iptv.manager/pull/10) ([michaelarnauts](https://github.com/michaelarnauts))
- Add CI flows [\#8](https://github.com/add-ons/service.iptv.manager/pull/8) ([michaelarnauts](https://github.com/michaelarnauts))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
