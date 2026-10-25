# -*- coding: utf-8 -*-
"""Tests for the provider contract and the retry path"""

# pylint: disable=invalid-name,missing-docstring,no-self-use,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from unittest import mock

from resources.lib import kodiutils
from resources.lib.modules import addon as addon_module
from resources.lib.modules.addon import Addon

ADDON_ID = 'plugin.video.example'
ADDON_PATH = '/storage/.kodi/addons/plugin.video.example'
CHANNELS_URI = 'plugin://plugin.video.example/?action=channels'


def make_addon(channels_uri=CHANNELS_URI, epg_uri='plugin://plugin.video.example/?action=epg'):
    """Build an Addon without touching Kodi."""
    with mock.patch.object(kodiutils, 'get_addon', return_value=mock.Mock()), \
            mock.patch.object(kodiutils, 'addon_path', return_value=ADDON_PATH):
        return Addon(ADDON_ID, mock.Mock(), channels_uri, epg_uri)


class TestGetChannels(unittest.TestCase):
    """get_channels() contract"""

    def setUp(self):
        self.addon = make_addon()

    def get_channels(self, data):
        with mock.patch.object(Addon, '_get_data_from_addon', return_value=data), \
                mock.patch.object(kodiutils, 'addon_name', return_value='Example'), \
                mock.patch.object(kodiutils, 'addon_icon', return_value='icon.png'):
            return self.addon.get_channels()

    def test_skips_incomplete_channels(self):
        """A stream without a name or without an url is skipped, not written."""
        channels = self.get_channels({
            'streams': [
                {'name': 'A', 'stream': 'http://a'},
                {'name': 'B'},
                {'stream': 'http://c'},
            ],
        })

        self.assertEqual([channel['name'] for channel in channels], ['A'])

    def test_makes_the_logo_absolute(self):
        """A relative logo is resolved against the add-on path."""
        channels = self.get_channels({
            'streams': [
                {'name': 'A', 'stream': 'http://a', 'logo': 'resources/logo.png'},
                {'name': 'B', 'stream': 'http://b'},
                {'name': 'C', 'stream': 'http://c', 'logo': 'https://cdn/logo.png'},
            ],
        })

        self.assertEqual(channels[0]['logo'], ADDON_PATH + '/resources/logo.png')
        self.assertEqual(channels[1]['logo'], 'icon.png')
        self.assertEqual(channels[2]['logo'], 'https://cdn/logo.png')

    def test_rejects_an_unsupported_version(self):
        """A newer JSON-STREAMS version is ignored instead of half-parsed."""
        self.assertEqual(self.get_channels({'version': 2, 'streams': [{'name': 'A', 'stream': 'http://a'}]}), [])

    def test_normalises_the_group(self):
        """A ';' separated group and a list give the same set."""
        from_string = self.get_channels({'streams': [{'name': 'A', 'stream': 'http://a', 'group': 'news;sport'}]})
        from_list = self.get_channels({'streams': [{'name': 'A', 'stream': 'http://a', 'group': ['news', 'sport']}]})

        self.assertEqual(from_string[0]['group'], {'news', 'sport', 'Example'})
        self.assertEqual(from_list[0]['group'], {'news', 'sport', 'Example'})

    def test_returns_raw_m3u(self):
        """A raw M3U playlist is passed through without its header."""
        playlist = '#EXTM3U\n#EXTINF:-1 tvg-id="a",A\nhttp://a\n'

        self.assertEqual(self.get_channels(playlist), '#EXTINF:-1 tvg-id="a",A\nhttp://a\n')

    def test_returns_nothing_without_a_uri(self):
        """A provider without a channels URI reports no channels."""
        addon = make_addon(channels_uri='')

        self.assertEqual(addon.get_channels(), [])


class TestGetEpg(unittest.TestCase):
    """get_epg() contract"""

    def setUp(self):
        self.addon = make_addon()

    def get_epg(self, data):
        with mock.patch.object(Addon, '_get_data_from_addon', return_value=data):
            return self.addon.get_epg()

    def test_rejects_invalid_raw_xmltv(self):
        """An HTML error page from a provider does not break the guide."""
        self.assertEqual(self.get_epg('<html><body>error</body></html>'), {})

    def test_rejects_an_unsupported_version(self):
        """A newer JSON-EPG version is ignored."""
        self.assertEqual(self.get_epg({'version': 2, 'epg': {'chan': []}}), {})

    def test_rejects_an_empty_guide(self):
        """An EPG without programs is ignored."""
        self.assertEqual(self.get_epg({'epg': {}}), {})

    def test_keeps_the_programs(self):
        """A valid JSON-EPG payload is returned as-is."""
        programs = {'chan': [{'start': '2026-10-25T20:00:00+01:00', 'title': 'Show'}]}

        self.assertEqual(self.get_epg({'epg': programs}), programs)


class TestRetry(unittest.TestCase):
    """The retry added for cold providers"""

    def setUp(self):
        self.addon = make_addon()
        self.sock = mock.Mock()
        self.sock.getsockname.return_value = ('127.0.0.1', 4321)

    def call(self, replies):
        with mock.patch.object(Addon, '_prepare_for_data', return_value=self.sock), \
                mock.patch.object(Addon, '_wait_for_data', side_effect=replies) as wait, \
                mock.patch.object(kodiutils, 'execute_builtin') as execute, \
                mock.patch.object(addon_module.time, 'sleep'):
            data = self.addon._get_data_from_addon(CHANNELS_URI)
            return data, wait.call_count, execute.call_count

    def test_recovers_after_a_timeout(self):
        """A cold add-on that misses the first timeout is asked a second time."""
        data, waits, executes = self.call([Exception('Timeout waiting for reply'), '{"streams": []}'])

        self.assertEqual(data, {'streams': []})
        self.assertEqual(waits, 2)
        self.assertEqual(executes, 2)

    def test_raises_the_last_error(self):
        """Two failures in a row propagate the second error."""
        with self.assertRaises(Exception) as context:
            self.call([Exception('first'), Exception('second')])

        self.assertIn('second', str(context.exception))

    def test_rejects_other_schemes(self):
        """Only plugin:// URIs are supported."""
        with self.assertRaises(NotImplementedError):
            self.addon._get_data_from_addon('http://provider/channels')


if __name__ == '__main__':
    unittest.main()
