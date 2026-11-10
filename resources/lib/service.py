# -*- coding: utf-8 -*-
"""Background service code"""

from __future__ import absolute_import, division, unicode_literals

import logging
import time

from xbmc import Monitor

from resources.lib import kodilogging, kodiutils
from resources.lib.modules import state
from resources.lib.modules.addon import Addon
from resources.lib.modules.iptvsimple import IptvSimple

_LOGGER = logging.getLogger(__name__)

# Kodi keeps loading the PVR and the providers for a while after a cold boot:
# a refresh started too early sees half a channel list (upstream issue #88).
# Give it time to settle before the first pass.
FIRST_REFRESH_DELAY = 20

# A playback in progress must not be cut by a refresh (upstream issue #89).
# The pass is postponed and retried on this interval.
REFRESH_RETRY_DELAY = 60

PLAYING_CONDITIONS = (
    'Player.HasVideo',
    'Pvr.IsPlayingTv',
    'Pvr.IsPlayingRadio',
    'Pvr.IsPlayingRecording',
)


class BackgroundService(Monitor):
    """Background service code"""

    def __init__(self):
        Monitor.__init__(self)
        self._restart_required = False
        self._started_at = time.time()
        # Set when a refresh is due but Kodi is playing something; the pass runs
        # once the playback stops, at most one attempt per REFRESH_RETRY_DELAY.
        self.refresh_pending = False
        self._refresh_retry_at = 0.0

    def run(self):
        """Background loop for maintenance tasks"""
        _LOGGER.debug('Service started')

        # On a fresh install IPTV Simple has no playlist/EPG configured. The
        # add-on setup is normally triggered by a button in the settings; do it
        # automatically so an appliance works after its first boot.
        if not IptvSimple.is_configured():
            _LOGGER.info('IPTV Simple is not configured for IPTV Manager; configuring it')
            if not IptvSimple.setup():
                _LOGGER.warning('Could not configure IPTV Simple automatically')

        # Service loop
        while not self.abortRequested():
            try:
                # Check if we need to do an update
                self._refresh_pass()

                # Check if IPTV Simple needs to be restarted
                if IptvSimple.verify_at is not None:
                    IptvSimple.check_started()

                if IptvSimple.restart_required:
                    IptvSimple.restart()
            except Exception:  # pylint: disable=broad-except
                # A failed pass must never end the service. On Kodi 22 an
                # unwritable setting used to raise here and stop the loop (F-11).
                _LOGGER.exception('Unhandled error during a pass; the service continues')

            # Stop when abort requested
            if self.waitForAbort(30):
                break

        _LOGGER.debug('Service stopped')

    def _refresh_pass(self):
        """Run one refresh pass, unless Kodi is busy or the next retry is not due.

        Returns True when a refresh was attempted. The first pass waits for
        Kodi to settle, and a pass never starts while a playback is running:
        IPTV Simple would be restarted under the player (F-01, F-07).
        """
        now = time.time()

        if now < self._started_at + FIRST_REFRESH_DELAY:
            _LOGGER.debug('Kodi is still settling; the first refresh waits %d seconds', FIRST_REFRESH_DELAY)
            return False

        if self.refresh_pending and now < self._refresh_retry_at:
            _LOGGER.debug('Refresh still pending; next attempt in %d seconds',
                          int(self._refresh_retry_at - now))
            return False

        if not self._is_refresh_required(now):
            return False

        if self._is_playing():
            self.refresh_pending = True
            self._refresh_retry_at = now + REFRESH_RETRY_DELAY
            _LOGGER.info('Refresh postponed since Kodi is playing; retrying in %d seconds',
                         REFRESH_RETRY_DELAY)
            return False

        Addon.refresh()
        self.refresh_pending = False
        self._refresh_retry_at = 0.0
        return True

    @staticmethod
    def _is_playing():
        """Return True when Kodi is playing TV, radio, a recording or a video."""
        for condition in PLAYING_CONDITIONS:
            if kodiutils.get_cond_visibility(condition):
                return True
        return False

    @staticmethod
    def _is_refresh_required(now=None):
        """Returns if we should trigger an update based on the settings."""
        now = time.time() if now is None else now

        # A failed pass sets the next attempt: never retry before it, and never
        # hammer a provider (docs/02, F-03).
        meta = state.load(kodiutils.addon_profile()).get(state.META_KEY) or {}
        retry_after = meta.get('retry_after') or 0
        if retry_after:
            return now >= retry_after

        refresh_interval = kodiutils.get_setting_int('refresh_interval', 24) * 3600
        last_refreshed = kodiutils.get_setting_int('last_refreshed', 0)
        return (last_refreshed + refresh_interval) <= now


def run():
    """Run the BackgroundService"""
    kodilogging.config()
    BackgroundService().run()
