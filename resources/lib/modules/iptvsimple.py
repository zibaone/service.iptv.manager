# -*- coding: utf-8 -*-
"""IPTV Simple Module"""

from __future__ import absolute_import, division, unicode_literals

import logging
import os
import time
from xml.etree import ElementTree

import glob

import xbmcvfs

import dateutil.parser
import dateutil.tz

from resources.lib import kodiutils
from resources.lib.modules.xmltv import RawXmltv

_LOGGER = logging.getLogger(__name__)

IPTV_SIMPLE_ID = 'pvr.iptvsimple'
IPTV_SIMPLE_PLAYLIST = 'playlist.m3u8'
IPTV_SIMPLE_EPG = 'epg.xml'

# Kodi 22 stops the PVR manager asynchronously: disabling and re-enabling IPTV
# Simple too early leaves the PVR client stopped. Poll the PVR state instead of
# guessing with a fixed delay (see docs/02-correctifs.md, F-01).
PVR_STOP_TIMEOUT = 60
PVR_STOP_MARGIN = 2
PVR_START_GRACE = 30

# A restart that does not take must not turn into a churn: on the Magicsee N5
# the PVR manager needed up to 90 s to come back, and the old "one check at
# +30 s, then restart again" loop ran 314 disable/enable cycles in three hours
# (measured 2026-11-02). Wait a few checks, then back off, then stop.
PVR_START_CHECKS = 3
RESTART_BACKOFF = (15 * 60, 60 * 60)
RESTART_MAX_FAILURES = 3

PLAYING_CONDITIONS = (
    'Pvr.IsPlayingTv',
    'Pvr.IsPlayingRadio',
    'Player.HasVideo',
    'PVR.IsRecording',
)

# Catchup added to the generated playlist (docs/02, F-10):
# - all: every channel gets `catchup="vod"`, the historical behaviour;
# - declared: only a channel whose provider announced a catchup-source;
# - none: never.
CATCHUP_ALL = 'all'
CATCHUP_DECLARED = 'declared'
CATCHUP_NONE = 'none'
CATCHUP_MODES = (CATCHUP_ALL, CATCHUP_DECLARED, CATCHUP_NONE)


class IptvSimple:
    """Helper class to setup IPTV Simple"""

    restart_required = False
    verify_at = None

    # Restart bookkeeping: checks already spent on the current start, failed
    # restart cycles, and the earliest time of the next attempt (0 = now).
    _start_checks = 0
    _failures = 0
    _retry_after = 0.0

    def __init__(self):
        """Init"""

    @classmethod
    def setup(cls, explicit=False):
        """Setup IPTV Simple.

        The automatic setup at startup only writes the playlist and guide
        paths, so a user choice (catchup, cache, logo) survives. The explicit
        setup, from the settings button, may write everything (docs/02, F-04).
        """
        addon = cls._get_addon()
        if addon is None:
            # Installing a PVR client at boot is out of scope: a box without
            # IPTV Simple is left alone instead of raising (docs/02, F-04).
            _LOGGER.warning('IPTV Simple is not installed; cannot configure it')
            return False

        try:
            # Activate IPTV Simple so we can get the addon to be able to configure it
            cls._activate()
            addon = kodiutils.get_addon(IPTV_SIMPLE_ID)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning('Could not setup IPTV Simple: %s', str(exc))
            return False

        output_dir = kodiutils.addon_profile()
        paths = cls._paths(output_dir)

        try:
            for key, value in paths.items():
                addon.setSetting(key, value)

            if explicit:
                addon.setSetting('epgCache', 'true')
                addon.setSetting('epgTimeShift', '0')

                addon.setSetting('logoPathType', '0')  # Local path
                addon.setSetting('logoPath', '/')

                addon.setSetting('catchupEnabled', 'true')
                addon.setSetting('allChannelsCatchupMode', '1')
                addon.setSetting('catchupOnlyOnFinishedProgrammes', 'false')
        except Exception as exc:  # pylint: disable=broad-except
            # Kodi 22 raises on a setting whose type it refuses; configuring the
            # PVR must never take the service down (docs/02, F-04 and F-11).
            _LOGGER.warning('Could not write the IPTV Simple settings: %s', str(exc))
            return False

        # A write IPTV Simple did not keep is a failed setup: do not restart it
        # against paths it does not use (docs/02, F-04).
        if not cls._settings_kept(addon, paths):
            return False

        cls._configure_instances(addon, output_dir)

        playlist = os.path.join(output_dir, IPTV_SIMPLE_PLAYLIST)
        if os.path.isfile(playlist):
            # Apply the settings through the safe restart path: Kodi 22 needs
            # the PVR manager to stop before IPTV Simple is re-enabled.
            if not cls.restart(force=True):
                _LOGGER.info('IPTV Simple is configured; its restart is postponed or pending')
        else:
            # Nothing to load yet: the first refresh writes the playlist and
            # restarts IPTV Simple itself.
            cls.restart_required = True
            _LOGGER.info('IPTV Simple is configured; its restart waits for the first playlist')

        return True

    @classmethod
    def is_configured(cls):
        """Return True when IPTV Simple already points to our generated files."""
        try:
            addon = kodiutils.get_addon(IPTV_SIMPLE_ID)
            output_dir = kodiutils.addon_profile()

            for key, value in cls._paths(output_dir).items():
                kept = addon.getSetting(key)
                if key.endswith('PathType'):
                    if kept != value:
                        return False
                elif not cls._same_path(kept, value):
                    return False

            # Kodi 20+ runs IPTV Simple through a PVR *instance*: the add-on's
            # own settings.xml is not what the client reads. A box whose
            # instance points nowhere is not configured, even when the legacy
            # values are right — otherwise setup() never runs on it (F-04,
            # measured on the Magicsee N5: legacy paths good, instance empty,
            # client stuck in CONNECTING and no channels).
            return cls._instances_configured(addon, output_dir)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug('Could not read IPTV Simple settings', exc_info=True)
            return False

    @staticmethod
    def _instance_files(addon):
        """Return the PVR instance settings files, sorted by instance id."""
        try:
            profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
            return sorted(glob.glob(os.path.join(profile_dir, 'instance-settings*.xml')))
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug('Could not read the IPTV Simple profile', exc_info=True)
            return []

    @staticmethod
    def _read_instance(path):
        """Return the text of one instance settings file, or None on error."""
        try:
            with open(path, 'r', encoding='utf-8') as fdesc:
                return fdesc.read()
        except OSError:
            _LOGGER.warning('Could not read IPTV Simple instance %s', os.path.basename(path), exc_info=True)
            return None

    @staticmethod
    def _instance_values(content):
        """Return the ``id -> text`` settings of one instance file."""
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return None
        return dict((element.get('id'), element.text or '') for element in root.findall('setting'))

    @classmethod
    def _instance_has_source(cls, content):
        """Return True when the instance points somewhere, ours or not.

        A setting Kodi created with ``default="true"`` has no text: the client
        falls back to its own default (M3U path type 1, remote URL). An empty
        remote URL is therefore no source at all, which is exactly the state
        that leaves IPTV Simple stuck in CONNECTING.
        """
        values = cls._instance_values(content)
        if values is None:
            return True  # Unreadable: leave the file alone
        if values.get('m3uPathType', '1') == '0':
            return bool((values.get('m3uPath') or '').strip())
        return bool((values.get('m3uUrl') or '').strip())

    @classmethod
    def _instances_configured(cls, addon, output_dir):
        """Return True when the PVR instances can load, or already use us."""
        instances = cls._instance_files(addon)
        if not instances:
            # No instance yet: the legacy settings are all there is to judge.
            return True

        playlist = os.path.join(output_dir, IPTV_SIMPLE_PLAYLIST)
        for path in instances:
            content = cls._read_instance(path)
            if content is None:
                continue
            if playlist in content:
                return True
            # An instance the user pointed at another source is a working
            # install: do not fight it on every start (F-04).
            if cls._instance_has_source(content):
                return True
        return False

    @staticmethod
    def _get_addon():
        """Return the IPTV Simple add-on, or None when it is not installed."""
        try:
            return kodiutils.get_addon(IPTV_SIMPLE_ID)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug('IPTV Simple is not available', exc_info=True)
            return None

    @staticmethod
    def _paths(output_dir):
        """Return the settings that make IPTV Simple read our generated files."""
        return {
            'm3uPathType': '0',  # Local path
            'm3uPath': os.path.join(output_dir, IPTV_SIMPLE_PLAYLIST),
            'epgPathType': '0',  # Local path
            'epgPath': os.path.join(output_dir, IPTV_SIMPLE_EPG),
        }

    @classmethod
    def _settings_kept(cls, addon, paths):
        """Read the settings back: a value Kodi refused is a failed setup."""
        for key, value in paths.items():
            try:
                kept = addon.getSetting(key)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.warning('Could not read back %s from IPTV Simple', key, exc_info=True)
                return False

            if key.endswith('PathType'):
                matches = kept == value
            else:
                matches = cls._same_path(kept, value)

            if not matches:
                _LOGGER.warning('IPTV Simple did not keep %s (got %r, expected %r)', key, kept, value)
                return False
        return True

    @staticmethod
    def _same_path(left, right):
        """Compare two paths, accepting special:// and translated forms."""
        def normalize(value):
            value = (value or '').strip().replace('\\', '/')
            try:
                value = xbmcvfs.translatePath(value)
            except Exception:  # pylint: disable=broad-except
                pass
            return os.path.normpath(value)

        return normalize(left) == normalize(right)

    @classmethod
    def _configure_instances(cls, addon, output_dir):
        """Update the instance IPTV Simple actually reads.

        Kodi 20+ keeps one settings file per PVR instance. Only the four paths
        are written: an instance the user configured keeps its own choices
        (docs/02, F-04).

        Which instance:
        - the ones that already reference our playlist;
        - when none does, the default instance (``instance-settings-1.xml``) if
          it has no source at all. A migrated profile can leave it on "remote
          URL" with an empty URL: the client then stays in CONNECTING, the PVR
          manager never starts and no channel appears. The blanket copy of
          ``settings.xml`` is still not the answer: an instance pointed at a
          user's own source is left untouched.
        """
        instances = cls._instance_files(addon)
        _LOGGER.info('IPTV Simple instance settings found: %s',
                     ', '.join(os.path.basename(path) for path in instances) or 'none')
        if not instances:
            # Activation creates the instance file; nothing to patch this pass.
            _LOGGER.warning('No IPTV Simple instance settings yet; the paths will be applied on the next start')
            return

        playlist = os.path.join(output_dir, IPTV_SIMPLE_PLAYLIST)
        ours = []
        empty = []
        for path in instances:
            content = cls._read_instance(path)
            if content is None:
                continue
            if playlist in content:
                ours.append(path)
            elif not cls._instance_has_source(content):
                empty.append(path)

        targets = ours
        if not targets:
            default = [path for path in empty if os.path.basename(path) == 'instance-settings-1.xml']
            if default:
                targets = default
            else:
                _LOGGER.warning('IPTV Simple has no instance on our playlist and its default instance '
                                'is configured elsewhere; leaving it alone')

        for path in targets:
            try:
                if cls._apply_instance_paths(path, output_dir):
                    _LOGGER.info('Updated IPTV Simple instance %s', os.path.basename(path))
            except Exception:  # pylint: disable=broad-except
                _LOGGER.warning('Could not update IPTV Simple instance %s',
                                os.path.basename(path), exc_info=True)

    @classmethod
    def _apply_instance_paths(cls, path, output_dir):
        """Rewrite the path settings of one instance file, atomically."""
        values = cls._paths(output_dir)
        tree = ElementTree.parse(path)
        root = tree.getroot()
        existing = dict((element.get('id'), element) for element in root.findall('setting'))

        changed = False
        for key, value in values.items():
            element = existing.get(key)
            if element is None:
                element = ElementTree.SubElement(root, 'setting', {'id': key})
                changed = True
            if (element.text or '') != value:
                element.text = value
                # A value written by Kodi carries no `default` attribute; keep
                # the file consistent so a settings migration cannot read our
                # path as "still the default".
                element.attrib.pop('default', None)
                changed = True

        if not changed:
            return False

        temp = path + '.tmp'
        tree.write(temp, encoding='utf-8', xml_declaration=False)
        os.replace(temp, path)
        return True


    @classmethod
    def restart(cls, force=False):
        """Restart IPTV Simple without leaving the PVR manager stopped.

        ``force`` no longer bypasses the playback guard: a restart during
        playback stops the playback (upstream issues #84 and #89).
        """
        _LOGGER.debug('Restart of IPTV Simple requested (force=%s)', force)

        # A failed cycle schedules the next attempt; the service loop calls us
        # every 30 s, so honour the deadline instead of restarting again.
        if not force and time.time() < cls._retry_after:
            cls.restart_required = True
            return False

        if cls._is_playing():
            cls.restart_required = True
            _LOGGER.info('Postponing restart of Simple IPTV since it is currently in use')
            return False

        cls.restart_required = False
        cls.verify_at = None
        cls._start_checks = 0

        cls._deactivate()

        if not cls._wait_for_pvr_stopped():
            _LOGGER.warning('IPTV Simple did not stop within %d seconds; not re-enabling it yet',
                            PVR_STOP_TIMEOUT)
            cls.restart_required = True
            return False

        # Give the PVR manager a moment once the client has disappeared.
        time.sleep(PVR_STOP_MARGIN)

        cls._activate()
        cls.verify_at = time.time() + PVR_START_GRACE
        _LOGGER.debug('IPTV Simple re-enabled; checking that it starts in %d seconds', PVR_START_GRACE)
        return True

    @classmethod
    def check_started(cls):
        """Check that IPTV Simple came back after a restart, and retry if not.

        One unavailable reading is not a failure: the PVR manager legitimately
        reports `available: false` while it loads the playlist (measured: up to
        90 s on the N5 with 570 channels). Several checks are allowed before the
        restart is declared failed, and a failed restart backs off before the
        next cycle (and gives up after RESTART_MAX_FAILURES).
        """
        if cls.verify_at is None or time.time() < cls.verify_at:
            return

        if cls._pvr_available() is True:
            cls.verify_at = None
            cls._start_checks = 0
            cls._failures = 0
            cls._retry_after = 0.0
            _LOGGER.debug('IPTV Simple is running again')
            return

        cls._start_checks += 1
        if cls._start_checks < PVR_START_CHECKS:
            cls.verify_at = time.time() + PVR_START_GRACE
            _LOGGER.info('IPTV Simple is not up yet (check %d/%d); waiting %d s more',
                         cls._start_checks, PVR_START_CHECKS, PVR_START_GRACE)
            return

        cls.verify_at = None
        cls._failed_restart()

    @classmethod
    def _failed_restart(cls):
        """Record a failed restart: back off, then give up after a few cycles."""
        cls._start_checks = 0
        cls._failures += 1

        if cls._failures >= RESTART_MAX_FAILURES:
            # Leave the add-on enabled and stop poking the PVR manager: a
            # disable/enable loop cannot fix a client that refuses to start, and
            # it destroys the channel list every 30 s while it tries.
            _LOGGER.error('IPTV Simple did not start after %d restarts; leaving it enabled. '
                          'A Kodi restart is required to recover the PVR client', cls._failures)
            cls.restart_required = False
            cls._retry_after = 0.0
            return

        delay = RESTART_BACKOFF[min(cls._failures - 1, len(RESTART_BACKOFF) - 1)]
        cls._retry_after = time.time() + delay
        cls.restart_required = True
        _LOGGER.warning('IPTV Simple did not start after a restart; next attempt in %d s', delay)

    @staticmethod
    def _is_playing():
        """Return True when Kodi is playing TV, radio, video or a recording."""
        for condition in PLAYING_CONDITIONS:
            if kodiutils.get_cond_visibility(condition):
                return True
        return False

    @staticmethod
    def _pvr_available():
        """Return True/False when the PVR state is known, None when it is not."""
        try:
            result = kodiutils.jsonrpc(method='PVR.GetProperties', params={'properties': ['available']})
        except Exception:  # pylint: disable=broad-except
            _LOGGER.debug('Could not read the PVR state', exc_info=True)
            return None

        if not isinstance(result, dict):
            return None
        if result.get('error'):
            # The PVR manager answers with an error while it is stopped.
            return False
        payload = result.get('result')
        if not isinstance(payload, dict):
            return None
        return payload.get('available')

    @classmethod
    def _wait_for_pvr_stopped(cls, timeout=PVR_STOP_TIMEOUT):
        """Wait until the PVR manager no longer reports an available client."""
        for _ in range(timeout):
            if cls._pvr_available() is not True:
                return True
            time.sleep(1)
        return False

    @staticmethod
    def _activate():
        """Activate IPTV Simple"""
        kodiutils.jsonrpc(method="Addons.SetAddonEnabled", params={"addonid": IPTV_SIMPLE_ID, "enabled": True})

    @staticmethod
    def _deactivate():
        """Deactivate IPTV Simple"""
        kodiutils.jsonrpc(method="Addons.SetAddonEnabled", params={"addonid": IPTV_SIMPLE_ID, "enabled": False})

    @staticmethod
    def _catchup_mode():
        """Return the configured catchup mode, defaulting to the historical one."""
        mode = kodiutils.get_setting('catchup_mode', CATCHUP_ALL) or CATCHUP_ALL
        if mode not in CATCHUP_MODES:
            _LOGGER.warning('Unknown catchup_mode %r; using %s', mode, CATCHUP_ALL)
            return CATCHUP_ALL
        return mode

    @staticmethod
    def _catchup_attribute(channel, mode):
        """Return the catchup attribute to add to one channel, if any.

        ``declared`` only marks a channel whose provider announced a
        ``catchup-source``. A raw M3U block is copied verbatim and keeps its
        own attributes, so this only applies to JSON-STREAMS channels.
        """
        if mode == CATCHUP_NONE:
            return ''
        if mode == CATCHUP_DECLARED and not channel.get('catchup-source'):
            return ''
        return ' catchup="vod"'

    @classmethod
    def write_playlist(cls, channels):
        """Write playlist data, and return True when the file changed"""
        output_dir = kodiutils.addon_profile()
        catchup_mode = cls._catchup_mode()

        # Make sure our output dir exists
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        # Write playlist for IPTV Simple
        playlist_path = os.path.join(output_dir, IPTV_SIMPLE_PLAYLIST)

        with open(playlist_path + '.tmp', 'wb') as fdesc:
            m3u8_data = '#EXTM3U\n'

            for addon in channels:
                m3u8_data += '## {addon_name}\n'.format(**addon)

                # RAW M3U8 data
                if not isinstance(addon['channels'], list):
                    m3u8_data += addon['channels']
                    continue

                # JSON-STREAMS format
                for channel in addon['channels']:
                    m3u8_data += '#EXTINF:-1 tvg-name="{name}"'.format(**channel)
                    if channel.get('id'):
                        m3u8_data += ' tvg-id="{id}"'.format(**channel)
                    if channel.get('logo'):
                        m3u8_data += ' tvg-logo="{logo}"'.format(**channel)
                    if channel.get('preset'):
                        m3u8_data += ' tvg-chno="{preset}"'.format(**channel)
                    if channel.get('group'):
                        m3u8_data += ' group-title="{groups}"'.format(groups=';'.join(channel.get('group')))
                    if channel.get('radio'):
                        m3u8_data += ' radio="true"'
                    m3u8_data += cls._catchup_attribute(channel, catchup_mode)
                    m3u8_data += ',{name}\n'.format(**channel)
                    if channel.get('kodiprops'):
                        for key, value in channel.get('kodiprops').items():
                            m3u8_data += '#KODIPROP:{key}={value}\n'.format(key=key, value=value)
                    m3u8_data += '{stream}\n\n'.format(**channel)

            fdesc.write(m3u8_data.encode('utf-8'))

        # Move new file to the right place. os.replace() is atomic: readers
        # never see a missing playlist during a refresh.
        return cls._replace_if_changed(playlist_path)

    @staticmethod
    def _same_content(path, tmp_path):
        """Return True when the pending file holds exactly the current bytes."""
        try:
            if os.path.getsize(path) != os.path.getsize(tmp_path):
                return False
            with open(path, 'rb') as current, open(tmp_path, 'rb') as pending:
                while True:
                    left = current.read(65536)
                    if left != pending.read(65536):
                        return False
                    if not left:
                        return True
        except OSError:
            return False

    @classmethod
    def _replace_if_changed(cls, path):
        """Replace ``path`` with ``path.tmp``, unless the content is identical.

        Returns True when the file changed. A pass that brings nothing new
        keeps the existing files untouched, which lets the caller skip the
        IPTV Simple restart: an unchanged collection used to cost a PVR stop
        and start on every pass (Zero 3, 2026-10-26).
        """
        tmp_path = path + '.tmp'
        if cls._same_content(path, tmp_path):
            os.remove(tmp_path)
            return False

        # os.replace() is atomic: readers never see a missing file.
        os.replace(tmp_path, path)
        return True

    @classmethod
    def write_epg(cls, epg_list, channels):
        """Write EPG data, and return True when the file changed"""
        output_dir = kodiutils.addon_profile()

        # Make sure our output dir exists
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        epg_path = os.path.join(output_dir, IPTV_SIMPLE_EPG)

        # Write XML file by hand
        # The reason for this is that it takes less memory to write the file line by line then to construct an
        # XML object in memory and writing that in one go.
        # We can't depend on lxml.etree.xmlfile, since that's not available as a Kodi module
        with open(epg_path + '.tmp', 'wb') as fdesc:
            fdesc.write('<?xml version="1.0" encoding="UTF-8"?>\n'.encode('utf-8'))
            fdesc.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'.encode('utf-8'))
            fdesc.write('<tv>\n'.encode('utf-8'))

            # Write channel info
            for addon in channels:
                for channel in addon.get('channels'):
                    if isinstance(channel, dict) and channel.get('id'):
                        fdesc.write('<channel id="{id}">\n'.format(id=cls._xml_encode(channel.get('id'))).encode('utf-8'))
                        fdesc.write(' <display-name>{name}</display-name>\n'.format(name=cls._xml_encode(channel.get('name'))).encode('utf-8'))
                        if channel.get('logo'):
                            fdesc.write(' <icon src="{logo}"/>\n'.format(logo=cls._xml_encode(channel.get('logo'))).encode('utf-8'))
                        fdesc.write('</channel>\n'.encode('utf-8'))

            for epg in epg_list:
                # RAW XMLTV data, streamed so the guide is not copied in memory
                if isinstance(epg, RawXmltv):
                    for chunk in epg.iter_chunks():
                        fdesc.write(chunk.encode('utf-8'))
                    fdesc.write('\n'.encode('utf-8'))
                    continue

                if not isinstance(epg, dict):
                    fdesc.write(epg.encode('utf-8'))
                    fdesc.write('\n'.encode('utf-8'))
                    continue

                # Write program info
                for _, key in enumerate(epg):
                    for item in epg[key]:
                        program = cls._construct_epg_program_xml(item, key)
                        fdesc.write(program.encode('utf-8'))

            fdesc.write('</tv>\n'.encode('utf-8'))

        # Move new file to the right place. os.replace() is atomic: readers
        # never see a missing EPG during a refresh.
        return cls._replace_if_changed(epg_path)

    @classmethod
    def _construct_epg_program_xml(cls, item, channel):
        """ Generate the XML for the EPG of a program. """
        try:
            start = dateutil.parser.parse(item.get('start')).strftime('%Y%m%d%H%M%S %z').rstrip()
            stop = dateutil.parser.parse(item.get('stop')).strftime('%Y%m%d%H%M%S %z').rstrip()
            title = item.get('title', '')

            # Add an icon ourselves in Kodi 18
            if kodiutils.kodi_version_major() < 19 and item.get('stream'):
                # We use a clever way to hide the direct URI in the label so Kodi 18 can access the it
                title = '%s [COLOR green]•[/COLOR][COLOR vod="%s"][/COLOR]' % (
                    title, item.get('stream')
                )

            program = '<programme start="{start}" stop="{stop}" channel="{channel}"{vod}>\n'.format(
                start=start,
                stop=stop,
                channel=cls._xml_encode(channel),
                vod=' catchup-id="%s"' % cls._xml_encode(item.get('stream')) if item.get('stream') else '')

            program += ' <title>{title}</title>\n'.format(
                title=cls._xml_encode(title))

            if item.get('subtitle'):
                program += ' <sub-title>{subtitle}</sub-title>\n'.format(
                    subtitle=cls._xml_encode(item.get('subtitle')))

            if item.get('description'):
                program += ' <desc>{description}</desc>\n'.format(
                    description=cls._xml_encode(item.get('description')))

            if item.get('credits'):
                program += ' <credits>\n'
                for credit in item.get('credits'):
                    # IPTV Simple only supports `actor`, `director` and `writer`, so we need to narrow the options down.
                    # actor -> actor (with optional role)
                    # director -> director
                    # writer -> writer
                    # adapter -> writer
                    # producer -> director
                    # composer -> writer
                    # editor -> writer
                    # presenter -> actor
                    # commentator -> actor
                    # guest -> actor

                    if credit.get('type') == 'actor':
                        if credit.get('role'):
                            program += '  <actor role="{role}">{name}</actor>\n'.format(role=cls._xml_encode(credit.get('role')),
                                                                                        name=cls._xml_encode(credit.get('name')))
                        else:
                            program += '  <actor>{name}</actor>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'director':
                        program += '  <director>{name}</director>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'writer':
                        program += '  <writer>{name}</writer>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'adapter':
                        program += '  <writer>{name}</writer>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'producer':
                        program += '  <director>{name}</director>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'composer':
                        program += '  <writer>{name}</writer>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'editor':
                        program += '  <writer>{name}</writer>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'presenter':
                        program += '  <actor>{name}</actor>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'commentator':
                        program += '  <actor>{name}</actor>\n'.format(name=cls._xml_encode(credit.get('name')))
                    elif credit.get('type') == 'guest':
                        program += '  <actor>{name}</actor>\n'.format(name=cls._xml_encode(credit.get('name')))

                program += ' </credits>\n'

            if item.get('date'):
                program += ' <date>{date}</date>\n'.format(
                    date=cls._xml_encode(item.get('date')))

            if item.get('genre'):
                if isinstance(item.get('genre'), list):
                    for genre in item.get('genre'):
                        program += ' <category>{genre}</category>\n'.format(
                            genre=cls._xml_encode(genre))
                else:
                    program += ' <category>{genre}</category>\n'.format(
                        genre=cls._xml_encode(item.get('genre')))

            if item.get('image'):
                program += ' <icon src="{image}"/>\n'.format(
                    image=cls._xml_encode(item.get('image')))

            if item.get('episode'):
                program += ' <episode-num system="onscreen">{episode}</episode-num>\n'.format(
                    episode=cls._xml_encode(item.get('episode')))

            program += '</programme>\n'
            return program

        except Exception as exc:  # pylint: disable=broad-except
            # When we encounter an error, log an error, but don't error out for the other programs
            _LOGGER.error('Could not parse item: %s', item)
            _LOGGER.exception(exc)
            return ''

    @staticmethod
    def _xml_encode(value):
        """Quick and dirty encoding for XML values"""
        if value is None:
            return ''
        return value \
            .replace('&', '&amp;') \
            .replace('<', '&lt;') \
            .replace('>', '&gt;') \
            .replace('"', '&quot;')
