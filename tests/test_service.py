# -*- coding: utf-8 -*-
""" Tests for background service """

# pylint: disable=invalid-name,missing-docstring,protected-access,cell-var-from-loop

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import pytest

from resources.lib import kodiutils
from resources.lib.modules import state
from resources.lib.modules.iptvsimple import IptvSimple
from resources.lib.service import FIRST_REFRESH_DELAY, REFRESH_RETRY_DELAY, BackgroundService


@unittest.skipIf(sys.platform.startswith("win"), 'Skipping on Windows.')
class TestService(unittest.TestCase):
    """ Tests for the background service """

    def test_service_survives_a_failed_refresh(self):
        """A refresh that raises must not stop the loop (Kodi 22 Invalid setting type)."""
        service = BackgroundService()
        service._started_at = 0
        with mock.patch.object(BackgroundService, 'abortRequested', return_value=False), \
                mock.patch.object(BackgroundService, 'waitForAbort', return_value=True), \
                mock.patch.object(BackgroundService, '_is_refresh_required', return_value=True), \
                mock.patch.object(BackgroundService, '_is_playing', return_value=False), \
                mock.patch.object(IptvSimple, 'is_configured', return_value=True), \
                mock.patch('resources.lib.service.Addon.refresh',
                           side_effect=RuntimeError('Invalid setting type')) as refresh:
            with self.assertLogs('resources.lib.service', level='ERROR'):
                service.run()

        self.assertEqual(refresh.call_count, 1)

    def test_first_refresh_waits_for_kodi_to_settle(self):
        """A cold start must not refresh while the PVR and the providers load (issue #88)."""
        service = BackgroundService()
        service._started_at = 1000
        with mock.patch.object(BackgroundService, '_is_refresh_required', return_value=True), \
                mock.patch.object(BackgroundService, '_is_playing', return_value=False), \
                mock.patch('resources.lib.service.time.time',
                           return_value=1000 + FIRST_REFRESH_DELAY - 1), \
                mock.patch('resources.lib.service.Addon.refresh') as refresh:
            self.assertFalse(service._refresh_pass())

        refresh.assert_not_called()

    def test_first_refresh_deferred_while_playing(self):
        """A playback in progress must not be cut by the first refresh (issues #88/#89)."""
        service = BackgroundService()
        service._started_at = 0
        now = 1800000000

        with mock.patch.object(BackgroundService, '_is_refresh_required', return_value=True), \
                mock.patch.object(BackgroundService, '_is_playing', return_value=True), \
                mock.patch('resources.lib.service.time.time', return_value=now), \
                mock.patch('resources.lib.service.Addon.refresh') as refresh, \
                mock.patch('resources.lib.service.IptvSimple.restart') as restart:
            self.assertFalse(service._refresh_pass())

            self.assertTrue(service.refresh_pending)
            refresh.assert_not_called()
            restart.assert_not_called()

            # Still deferred before the retry delay, even once the playback stopped.
            with mock.patch.object(BackgroundService, '_is_playing', return_value=False), \
                    mock.patch('resources.lib.service.time.time',
                               return_value=now + REFRESH_RETRY_DELAY - 1):
                self.assertFalse(service._refresh_pass())
            refresh.assert_not_called()

            # Playback is over and the delay elapsed: the pass runs.
            with mock.patch.object(BackgroundService, '_is_playing', return_value=False), \
                    mock.patch('resources.lib.service.time.time',
                               return_value=now + REFRESH_RETRY_DELAY):
                self.assertTrue(service._refresh_pass())

        refresh.assert_called_once()
        self.assertFalse(service.refresh_pending)

    def test_refresh_deferred_while_watching_tv(self):
        """Pvr.IsPlayingTv also postpones the refresh, not only Player.HasVideo."""
        service = BackgroundService()
        service._started_at = 0

        def playing(condition):
            return condition == 'Pvr.IsPlayingTv'

        with mock.patch.object(BackgroundService, '_is_refresh_required', return_value=True), \
                mock.patch.object(kodiutils, 'get_cond_visibility', side_effect=playing), \
                mock.patch('resources.lib.service.time.time', return_value=1800000000), \
                mock.patch('resources.lib.service.Addon.refresh') as refresh:
            self.assertFalse(service._refresh_pass())

        self.assertTrue(service.refresh_pending)
        refresh.assert_not_called()

    def test_is_refresh_required_waits_for_retry_after(self):
        """A failed pass sets the next attempt: the loop must not run before it."""
        now = 1800000000
        with tempfile.TemporaryDirectory() as profile:
            with mock.patch.object(kodiutils, 'addon_profile', return_value=profile + os.sep):
                state.save(profile + os.sep, {'_meta': {'retry_after': now + 60}})
                with mock.patch('resources.lib.service.time.time', return_value=now):
                    self.assertFalse(BackgroundService._is_refresh_required())
                with mock.patch('resources.lib.service.time.time', return_value=now + 61):
                    self.assertTrue(BackgroundService._is_refresh_required())

    @staticmethod
    def test_is_refresh_required():
        """ The refresh is due only once the configured interval has passed. """
        now = 1800000000
        cases = [
            (24, now, False),               # refreshed just now
            (24, now - 23 * 3600, False),   # 23 h ago, interval is 24 h
            (24, now - 25 * 3600, True),    # 25 h ago
            (0, now, True),                 # interval disabled: always due
            (24, 0, True),                  # never refreshed
        ]

        for interval, last_refreshed, expected in cases:
            settings = {'refresh_interval': interval, 'last_refreshed': last_refreshed}
            with mock.patch.object(kodiutils, 'get_setting_int',
                                   side_effect=lambda key, default=0, values=settings: values.get(key, default)), \
                    mock.patch('resources.lib.service.state.load', return_value={}), \
                    mock.patch('resources.lib.service.time.time', return_value=now):
                assert BackgroundService._is_refresh_required() is expected, (interval, last_refreshed)

    @staticmethod
    @pytest.mark.timeout(timeout=10, method='thread')
    def test_service():
        """ Run the background service for 5 seconds. It will raise an error when it doesn't stop after 10 seconds. """

        def terminate_service(seconds=5):
            """ Sleep a bit, and send us a SIGINT signal. """
            time.sleep(seconds)
            os.kill(os.getpid(), signal.SIGINT)

        threading.Thread(target=terminate_service).start()

        service = BackgroundService()
        service.run()


if __name__ == '__main__':
    unittest.main()
