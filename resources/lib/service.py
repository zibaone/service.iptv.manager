# -*- coding: utf-8 -*-
"""Background service code"""

from __future__ import absolute_import, division, unicode_literals

import logging
import time

from xbmc import Monitor

from resources.lib import kodilogging, kodiutils
from resources.lib.modules.addon import Addon
from resources.lib.modules.iptvsimple import IptvSimple

_LOGGER = logging.getLogger(__name__)


class BackgroundService(Monitor):
    """Background service code"""

    def __init__(self):
        Monitor.__init__(self)
        self._restart_required = False

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
                if self._is_refresh_required():
                    Addon.refresh()

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

    @staticmethod
    def _is_refresh_required():
        """Returns if we should trigger an update based on the settings."""
        refresh_interval = kodiutils.get_setting_int('refresh_interval', 24) * 3600
        last_refreshed = kodiutils.get_setting_int('last_refreshed', 0)
        return (last_refreshed + refresh_interval) <= time.time()


def run():
    """Run the BackgroundService"""
    kodilogging.config()
    BackgroundService().run()
