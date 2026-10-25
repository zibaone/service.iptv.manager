# -*- coding: utf-8 -*-
"""Refusing to replace good files with a degraded collection"""

# pylint: disable=invalid-name,missing-docstring,no-self-use,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import tempfile
import unittest
from unittest import mock

from resources.lib.modules.addon import Addon
from resources.lib.modules.iptvsimple import IptvSimple

PROFILE = None


class FakeProvider:
    """A provider that returns what the test decides."""

    def __init__(self, addon_id, channels, epg):
        self.addon_id = addon_id
        self.addon_obj = mock.Mock()
        self.channels_uri = 'plugin://%s/channels' % addon_id
        self.epg_uri = 'plugin://%s/epg' % addon_id
        self.channels = channels
        self.epg = epg

    def get_channels(self):
        return self.channels

    def get_epg(self):
        return self.epg


def write_state(providers):
    """Write a previous providers_state.json in the profile."""
    with open(os.path.join(PROFILE, 'providers_state.json'), 'w', encoding='utf-8') as handle:
        json.dump(providers, handle)


def read_state():
    with open(os.path.join(PROFILE, 'providers_state.json'), 'r', encoding='utf-8') as handle:
        return json.load(handle)


class RefreshGuardTest(unittest.TestCase):
    """A pass that loses a provider must not overwrite the playlist"""

    def setUp(self):
        global PROFILE  # pylint: disable=global-statement
        self.tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        PROFILE = self.tempdir.name + os.sep

        self.providers = []
        self.write_playlist = mock.Mock()
        self.write_epg = mock.Mock()
        self.set_setting = mock.Mock()

    def tearDown(self):
        self.tempdir.cleanup()

    def refresh(self, providers):
        with mock.patch.object(Addon, 'detect_iptv_addons', return_value=providers), \
                mock.patch.object(IptvSimple, 'write_playlist', self.write_playlist), \
                mock.patch.object(IptvSimple, 'write_epg', self.write_epg), \
                mock.patch('resources.lib.modules.addon.kodiutils.addon_profile', return_value=PROFILE), \
                mock.patch('resources.lib.modules.addon.kodiutils.addon_name', return_value='Provider'), \
                mock.patch('resources.lib.modules.addon.kodiutils.get_setting_bool', return_value=False), \
                mock.patch('resources.lib.modules.addon.kodiutils.set_setting_int', self.set_setting):
            Addon.refresh()

    def test_degraded_pass_keeps_the_previous_files(self):
        """A provider that returned 3 channels and now returns none blocks the write."""
        write_state({'a': {'channels': 3, 'programs': 4, 'failures': 0}})
        provider = FakeProvider('a', [], {})

        self.refresh([provider])

        self.write_playlist.assert_not_called()
        self.write_epg.assert_not_called()
        self.set_setting.assert_not_called()
        state = read_state()
        self.assertEqual(state['a']['channels'], 0)
        self.assertEqual(state['a']['failures'], 1)

    def test_all_providers_failing_writes_nothing(self):
        """A first boot where every provider fails must not create empty files."""
        self.refresh([FakeProvider('a', [], {}), FakeProvider('b', [], {})])

        self.write_playlist.assert_not_called()
        self.write_epg.assert_not_called()
        self.set_setting.assert_not_called()
        self.assertEqual(read_state()['a']['failures'], 0)
        self.assertEqual(read_state()['b']['failures'], 0)

    def test_complete_pass_writes_and_advances_the_date(self):
        """Every provider answered: files are written and last_refreshed moves."""
        providers = [
            FakeProvider('a', [{'name': 'A', 'stream': 'http://a'}], {'a': [{'title': 'T'}]}),
            FakeProvider('b', [{'name': 'B', 'stream': 'http://b'}], {'b': [{'title': 'T'}]}),
        ]

        self.refresh(providers)

        self.assertEqual(self.write_playlist.call_count, 1)
        self.assertEqual(self.write_epg.call_count, 1)
        self.set_setting.assert_called_once()

    def test_partial_first_pass_writes_but_does_not_advance_the_date(self):
        """One provider answered on a first boot: write, but keep a retry coming."""
        providers = [
            FakeProvider('a', [{'name': 'A', 'stream': 'http://a'}], {'a': [{'title': 'T'}]}),
            FakeProvider('b', [], {}),
        ]

        self.refresh(providers)

        self.assertEqual(self.write_playlist.call_count, 1)
        self.set_setting.assert_not_called()

    def test_three_consecutive_failures_accept_the_decrease(self):
        """After three passes, a provider that really lost its channels is believed."""
        write_state({
            'a': {'channels': 3, 'programs': 4, 'failures': 2},
            'b': {'channels': 2, 'programs': 2, 'failures': 0},
        })
        providers = [
            FakeProvider('a', [], {}),
            FakeProvider('b', [{'name': 'B', 'stream': 'http://b'}], {'b': [{'title': 'T'}]}),
        ]

        self.refresh(providers)

        self.assertEqual(self.write_playlist.call_count, 1)
        state = read_state()
        self.assertEqual(state['a']['channels'], 0)
        self.assertEqual(state['a']['failures'], 0)
        self.assertEqual(state['b']['channels'], 1)

    def test_failed_pass_schedules_a_retry(self):
        """A degraded pass records the attempt and the next allowed time."""
        write_state({'a': {'channels': 3, 'programs': 4, 'failures': 0}})
        now = 1800000000

        with mock.patch('resources.lib.modules.addon.time.time', return_value=now):
            self.refresh([FakeProvider('a', [], {})])

        meta = read_state()['_meta']
        self.assertEqual(meta['last_attempt'], now)
        self.assertEqual(meta['failures'], 1)
        self.assertEqual(meta['retry_after'], now + 15 * 60)

    def test_second_failure_backs_off_to_one_hour(self):
        """Two failures in a row wait an hour before the next attempt."""
        now = 1800000000
        write_state({
            'a': {'channels': 3, 'programs': 4, 'failures': 0},
            '_meta': {'last_attempt': now - 900, 'failures': 1, 'retry_after': now},
        })

        with mock.patch('resources.lib.modules.addon.time.time', return_value=now):
            self.refresh([FakeProvider('a', [], {})])

        meta = read_state()['_meta']
        self.assertEqual(meta['failures'], 2)
        self.assertEqual(meta['retry_after'], now + 60 * 60)

    def test_success_clears_the_retry(self):
        """A complete pass removes the backoff and the previous failure count."""
        now = 1800000000
        write_state({
            'a': {'channels': 1, 'programs': 1, 'failures': 2},
            '_meta': {'last_attempt': now - 900, 'failures': 2, 'retry_after': now},
        })
        provider = FakeProvider('a', [{'name': 'A', 'stream': 'http://a'}], {'a': [{'title': 'T'}]})

        with mock.patch('resources.lib.modules.addon.time.time', return_value=now):
            self.refresh([provider])

        meta = read_state()['_meta']
        self.assertEqual(meta['failures'], 0)
        self.assertEqual(meta['retry_after'], 0)
        self.assertEqual(meta['last_attempt'], now)


if __name__ == '__main__':
    unittest.main()
