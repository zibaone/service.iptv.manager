# -*- coding: utf-8 -*-
"""Tests for IPTV Simple"""

# pylint: disable=invalid-name,missing-docstring,no-self-use

from __future__ import absolute_import, division, print_function, unicode_literals

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


def flags(calls, method):
    """Return the enabled flags recorded for a method."""
    return [enabled for name, enabled in calls if name == method]


class IptvSimpleTest(unittest.TestCase):
    """IPTV Simple Tests"""

    def setUp(self):
        IptvSimple.restart_required = False
        IptvSimple.verify_at = None

    def test_setup(self):
        """Test the setup of IPTV Simple (this will be mocked)"""
        self.assertTrue(IptvSimple.setup())

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

    def test_setup_uses_the_safe_restart_path(self):
        """setup() never re-enables IPTV Simple without waiting for the PVR."""
        calls, fake_rpc = rpc_recorder([True, False])
        with mock.patch.object(kodiutils, 'get_cond_visibility', return_value=False), \
                mock.patch.object(kodiutils, 'jsonrpc', side_effect=fake_rpc), \
                mock.patch(SLEEP):
            self.assertTrue(IptvSimple.setup())

        methods = [name for name, _ in calls]
        disable_index = methods.index('Addons.SetAddonEnabled')
        enable_index = len(methods) - 1 - methods[::-1].index('Addons.SetAddonEnabled')
        self.assertIn('PVR.GetProperties', methods[disable_index:enable_index])


if __name__ == '__main__':
    unittest.main()
