# -*- coding: utf-8 -*-
"""Tests for IPTV Simple"""

# pylint: disable=invalid-name,missing-docstring,no-self-use,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import tempfile
import unittest
from unittest import mock

from resources.lib import kodiutils
from resources.lib.modules.iptvsimple import IptvSimple

SLEEP = 'resources.lib.modules.iptvsimple.time.sleep'


def rpc_recorder(pvr_states):
    """Return a (calls, fake jsonrpc) pair that records the JSON-RPC calls.

    ``pvr_states`` is the sequence returned for PVR.GetProperties. A value of
    None is answered with the error the PVR manager sends while it is stopped.
    """
    calls = []
    states = iter(pvr_states)

    def fake_jsonrpc(**kwargs):
        method = kwargs.get('method')
        params = kwargs.get('params') or {}
        calls.append((method, params.get('enabled')))
        if method == 'PVR.GetProperties':
            try:
                state = next(states)
            except StopIteration:
                state = False
            if state is None:
                return {'error': {'code': -32100, 'message': 'Failed to execute method.'}}
            return {'result': {'available': state}}
        return {'result': 'OK'}

    return calls, fake_jsonrpc


def touch(path):
    """Create an empty file."""
    with open(path, 'w', encoding='utf-8'):
        pass


def flags(calls, method):
    """Return the enabled flags recorded for a method."""
    return [enabled for name, enabled in calls if name == method]


class IptvSimpleTest(unittest.TestCase):
    """IPTV Simple Tests"""

    def setUp(self):
        IptvSimple.restart_required = False
        IptvSimple.verify_at = None

    def test_restart_postponed_while_playing(self):
        """A forced restart must not stop a playback in progress."""
        calls, fake_rpc = rpc_recorder([])
        with mock.patch.object(kodiutils, 'get_cond_visibility', side_effect=lambda condition: condition == 'Pvr.IsPlayingTv'), \
                mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            self.assertFalse(IptvSimple.restart(force=True))

        self.assertTrue(IptvSimple.restart_required)
        self.assertEqual(calls, [])

    def test_restart_postponed_while_video_plays(self):
        """Player.HasVideo also postpones the restart."""
        calls, fake_rpc = rpc_recorder([])
        with mock.patch.object(kodiutils, 'get_cond_visibility', side_effect=lambda condition: condition == 'Player.HasVideo'), \
                mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            self.assertFalse(IptvSimple.restart())

        self.assertTrue(IptvSimple.restart_required)
        self.assertEqual(calls, [])

    def test_restart_waits_for_pvr_stop(self):
        """The add-on is re-enabled only after the PVR reports it stopped."""
        calls, fake_rpc = rpc_recorder([True, True, False])
        with mock.patch.object(kodiutils, 'get_cond_visibility', return_value=False), \
                mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            self.assertTrue(IptvSimple.restart(force=True))

        self.assertEqual(
            [name for name, _ in calls],
            [
                'Addons.SetAddonEnabled',
                'PVR.GetProperties',
                'PVR.GetProperties',
                'PVR.GetProperties',
                'Addons.SetAddonEnabled',
            ],
        )
        self.assertEqual(flags(calls, 'Addons.SetAddonEnabled'), [False, True])
        self.assertIsNotNone(IptvSimple.verify_at)
        self.assertFalse(IptvSimple.restart_required)

    def test_restart_aborts_when_pvr_never_stops(self):
        """When the PVR never stops, the add-on is left disabled and retried."""
        calls, fake_rpc = rpc_recorder([True] * 500)
        with mock.patch.object(kodiutils, 'get_cond_visibility', return_value=False), \
                mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            self.assertFalse(IptvSimple.restart(force=True))

        self.assertEqual(flags(calls, 'Addons.SetAddonEnabled'), [False])
        self.assertTrue(IptvSimple.restart_required)
        self.assertIsNone(IptvSimple.verify_at)

    def test_restart_treats_pvr_error_as_stopped(self):
        """The -32100 error the PVR manager returns while stopped counts as stopped."""
        calls, fake_rpc = rpc_recorder([None])
        with mock.patch.object(kodiutils, 'get_cond_visibility', return_value=False), \
                mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            self.assertTrue(IptvSimple.restart(force=True))

        self.assertEqual(flags(calls, 'Addons.SetAddonEnabled'), [False, True])

    def test_check_started_retries_when_pvr_is_down(self):
        """After the grace delay, an unavailable PVR schedules another restart."""
        IptvSimple.verify_at = 0
        _, fake_rpc = rpc_recorder([False])
        with mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            IptvSimple.check_started()

        self.assertTrue(IptvSimple.restart_required)
        self.assertIsNone(IptvSimple.verify_at)

    def test_check_started_keeps_restart_when_pvr_is_up(self):
        """A running PVR clears the verification without scheduling anything."""
        IptvSimple.verify_at = 0
        _, fake_rpc = rpc_recorder([True])
        with mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            IptvSimple.check_started()

        self.assertFalse(IptvSimple.restart_required)
        self.assertIsNone(IptvSimple.verify_at)

    def test_check_started_does_nothing_before_the_grace_delay(self):
        """No PVR query happens before the grace delay expires."""
        IptvSimple.verify_at = 10 ** 12
        calls, fake_rpc = rpc_recorder([])
        with mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            IptvSimple.check_started()

        self.assertEqual(calls, [])
        self.assertFalse(IptvSimple.restart_required)


class FakeAddon:
    """A minimal xbmcaddon.Addon that remembers what it accepts."""

    def __init__(self, profile, apply=True):
        self.profile = profile
        self.apply = apply
        self.settings = {}
        self.written = []

    def setSetting(self, key, value):  # pylint: disable=invalid-name
        """Record a write, and keep it when Kodi would."""
        self.written.append((key, value))
        if self.apply:
            self.settings[key] = value

    def getSetting(self, key):  # pylint: disable=invalid-name
        """Return what was kept."""
        return self.settings.get(key, '')

    def getAddonInfo(self, key):  # pylint: disable=invalid-name
        """Return the profile the caller asked for."""
        return self.profile if key == 'profile' else ''


class SetupTest(unittest.TestCase):
    """Configuring IPTV Simple without breaking a working install"""

    def setUp(self):
        IptvSimple.restart_required = False
        IptvSimple.verify_at = None

    def run_setup(self, addon, profile, explicit=False):
        """Run setup against a fake add-on and a temporary profile."""
        translate = mock.patch('resources.lib.modules.iptvsimple.xbmcvfs.translatePath',
                               side_effect=lambda path: path)
        with mock.patch.object(kodiutils, 'get_addon', return_value=addon), \
                mock.patch.object(kodiutils, 'addon_profile', return_value=profile + os.sep), \
                translate, \
                mock.patch.object(IptvSimple, 'restart', return_value=True):
            return IptvSimple.setup(explicit=explicit)

    def test_setup_without_pvr_returns_false(self):
        """A box without the PVR add-on is left alone: no exception, no write."""
        with mock.patch.object(kodiutils, 'get_addon', side_effect=RuntimeError('Unknown addon id')), \
                mock.patch.object(kodiutils, 'execute_builtin') as builtin:
            with self.assertLogs('resources.lib.modules.iptvsimple', level='WARNING'):
                self.assertFalse(IptvSimple.setup())

        builtin.assert_not_called()

    def test_setup_is_read_back(self):
        """The paths are read back; a setting that did not stick fails the setup."""
        with tempfile.TemporaryDirectory() as profile:
            touch(os.path.join(profile, 'playlist.m3u8'))
            addon = FakeAddon(profile)

            self.assertTrue(self.run_setup(addon, profile))

            expected = os.path.join(profile, 'playlist.m3u8')
            self.assertEqual(addon.getSetting('m3uPath'), expected)

        with tempfile.TemporaryDirectory() as profile:
            touch(os.path.join(profile, 'playlist.m3u8'))
            addon = FakeAddon(profile, apply=False)

            with self.assertLogs('resources.lib.modules.iptvsimple', level='WARNING') as logs:
                self.assertFalse(self.run_setup(addon, profile))

        self.assertIn('did not keep', '\n'.join(logs.output))

    def test_setup_survives_a_refused_setting(self):
        """A setting Kodi 22 refuses fails the setup, it does not raise."""
        addon = mock.Mock()
        addon.setSetting.side_effect = RuntimeError('Invalid setting type')

        with tempfile.TemporaryDirectory() as profile:
            with self.assertLogs('resources.lib.modules.iptvsimple', level='WARNING'):
                self.assertFalse(self.run_setup(addon, profile))

    def test_automatic_setup_leaves_user_choices(self):
        """The startup setup only writes the playlist and guide paths."""
        with tempfile.TemporaryDirectory() as profile:
            addon = FakeAddon(profile)

            self.assertTrue(self.run_setup(addon, profile))

            self.assertEqual(
                sorted(key for key, _ in addon.written),
                ['epgPath', 'epgPathType', 'm3uPath', 'm3uPathType'],
            )

        with tempfile.TemporaryDirectory() as profile:
            addon = FakeAddon(profile)

            self.assertTrue(self.run_setup(addon, profile, explicit=True))

            keys = {key for key, _ in addon.written}
            self.assertIn('catchupEnabled', keys)
            self.assertIn('epgCache', keys)

    def test_setup_with_two_instances(self):
        """Only the instance that already uses our playlist is updated."""
        with tempfile.TemporaryDirectory() as profile:
            playlist = os.path.join(profile, 'playlist.m3u8')
            touch(playlist)
            ours = (
                '<settings version="2">\n'
                '    <setting id="m3uPathType">0</setting>\n'
                '    <setting id="m3uPath">%s</setting>\n'
                '    <setting id="epgPathType">0</setting>\n'
                '    <setting id="epgPath">/old/epg.xml</setting>\n'
                '    <setting id="catchupEnabled">false</setting>\n'
                '</settings>\n'
            ) % playlist
            other = (
                '<settings version="2">\n'
                '    <setting id="m3uPath">/other/playlist.m3u8</setting>\n'
                '</settings>\n'
            )
            with open(os.path.join(profile, 'instance-settings-1.xml'), 'w', encoding='utf-8') as handle:
                handle.write(ours)
            with open(os.path.join(profile, 'instance-settings-2.xml'), 'w', encoding='utf-8') as handle:
                handle.write(other)

            addon = FakeAddon(profile)
            with self.assertLogs('resources.lib.modules.iptvsimple', level='INFO') as logs:
                self.assertTrue(self.run_setup(addon, profile))

            with open(os.path.join(profile, 'instance-settings-1.xml'), encoding='utf-8') as handle:
                updated = handle.read()
            with open(os.path.join(profile, 'instance-settings-2.xml'), encoding='utf-8') as handle:
                untouched = handle.read()

        self.assertIn('instance-settings-1.xml', '\n'.join(logs.output))
        self.assertIn('<setting id="epgPath">%s</setting>' % os.path.join(profile, 'epg.xml'), updated)
        self.assertIn('<setting id="catchupEnabled">false</setting>', updated)
        self.assertEqual(untouched, other)

    def test_setup_uses_the_safe_restart_path(self):
        """setup() never re-enables IPTV Simple without waiting for the PVR."""
        calls, fake_rpc = rpc_recorder([True, False])
        with tempfile.TemporaryDirectory() as profile:
            touch(os.path.join(profile, 'playlist.m3u8'))
            addon = FakeAddon(profile)
            with mock.patch.object(kodiutils, 'get_addon', return_value=addon), \
                    mock.patch.object(kodiutils, 'addon_profile', return_value=profile + os.sep), \
                    mock.patch('resources.lib.modules.iptvsimple.xbmcvfs.translatePath', side_effect=lambda path: path), \
                    mock.patch.object(kodiutils, 'get_cond_visibility', return_value=False), \
                    mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                    mock.patch(SLEEP):
                self.assertTrue(IptvSimple.setup())

        methods = [name for name, _ in calls]
        disable_index = methods.index('Addons.SetAddonEnabled')
        enable_index = len(methods) - 1 - methods[::-1].index('Addons.SetAddonEnabled')
        self.assertIn('PVR.GetProperties', methods[disable_index:enable_index])

    def test_setup_without_a_playlist_waits_for_the_first_refresh(self):
        """Before the first refresh there is nothing to load: no restart yet."""
        with tempfile.TemporaryDirectory() as profile:
            addon = FakeAddon(profile)
            with mock.patch.object(kodiutils, 'get_addon', return_value=addon), \
                    mock.patch.object(kodiutils, 'addon_profile', return_value=profile + os.sep), \
                    mock.patch('resources.lib.modules.iptvsimple.xbmcvfs.translatePath', side_effect=lambda path: path), \
                    mock.patch.object(IptvSimple, 'restart') as restart:
                self.assertTrue(IptvSimple.setup())

        restart.assert_not_called()
        self.assertTrue(IptvSimple.restart_required)

    def test_is_configured_accepts_special_paths(self):
        """special:// paths and a missing catchupEnabled still count as configured."""
        profile = '/profile/'
        special = 'special://profile/addon_data/service.iptv.manager/'
        addon = mock.Mock()
        addon.getSetting.side_effect = lambda key: {
            'm3uPathType': '0',
            'm3uPath': special + 'playlist.m3u8',
            'epgPathType': '0',
            'epgPath': special + 'epg.xml',
        }.get(key, '')

        with mock.patch.object(kodiutils, 'get_addon', return_value=addon), \
                mock.patch.object(kodiutils, 'addon_profile', return_value=profile), \
                mock.patch('resources.lib.modules.iptvsimple.xbmcvfs.translatePath',
                           side_effect=lambda path: path.replace(special, profile)):
            self.assertTrue(IptvSimple.is_configured())

    def test_is_configured_rejects_another_addon(self):
        """Another add-on's playlist is not our configuration."""
        addon = mock.Mock()
        addon.getSetting.side_effect = lambda key: {
            'm3uPathType': '0',
            'm3uPath': '/other/playlist.m3u8',
            'epgPathType': '0',
            'epgPath': '/other/epg.xml',
        }.get(key, '')

        with mock.patch.object(kodiutils, 'get_addon', return_value=addon), \
                mock.patch.object(kodiutils, 'addon_profile', return_value='/profile/'), \
                mock.patch('resources.lib.modules.iptvsimple.xbmcvfs.translatePath', side_effect=lambda path: path):
            self.assertFalse(IptvSimple.is_configured())


class ProgramXmlTest(unittest.TestCase):
    """XML generation for one program"""

    ITEM = {
        'start': '2026-10-25T20:00:00+01:00',
        'stop': '2026-10-25T21:00:00+01:00',
        'title': 'Tom & Jerry <3 "x"',
        'description': 'A <b>bold</b> move & more',
    }

    def test_escapes_xml_values(self):
        """Ampersands, angle brackets and quotes cannot break the guide."""
        program = IptvSimple._construct_epg_program_xml(self.ITEM, 'chan&1')

        self.assertIn('channel="chan&amp;1"', program)
        self.assertIn('<title>Tom &amp; Jerry &lt;3 &quot;x&quot;</title>', program)
        self.assertIn('<desc>A &lt;b&gt;bold&lt;/b&gt; move &amp; more</desc>', program)

    def test_formats_the_dates_for_xmltv(self):
        """Dates are written in the XMLTV form, with the timezone offset."""
        program = IptvSimple._construct_epg_program_xml(self.ITEM, 'chan')

        self.assertIn('start="20261025200000 +0100"', program)
        self.assertIn('stop="20261025210000 +0100"', program)

    def test_accepts_a_list_of_genres(self):
        """A genre list becomes one category per entry."""
        item = dict(self.ITEM, genre=['news', 'sport'])

        program = IptvSimple._construct_epg_program_xml(item, 'chan')

        self.assertIn('<category>news</category>', program)
        self.assertIn('<category>sport</category>', program)

    def test_a_bad_program_does_not_break_the_others(self):
        """An unparseable program is skipped, the next ones are written."""
        bad = {'start': 'not-a-date', 'stop': 'not-a-date', 'title': 'Broken'}
        good = dict(self.ITEM, title='Good show')

        with tempfile.TemporaryDirectory() as output_dir:
            with mock.patch.object(kodiutils, 'addon_profile', return_value=output_dir + os.sep):
                IptvSimple.write_epg([{'chan': [bad, good]}], [])

            with open(os.path.join(output_dir, 'epg.xml'), 'rb') as handle:
                content = handle.read().decode('utf-8')

        self.assertNotIn('Broken', content)
        self.assertEqual(content.count('<programme '), 1)
        self.assertIn('<title>Good show</title>', content)


if __name__ == '__main__':
    unittest.main()
