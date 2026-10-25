# -*- coding: utf-8 -*-
"""Addon Module"""

from __future__ import absolute_import, division, unicode_literals

import sys
import codecs
import json
import logging
import os
import socket
import time

from resources.lib import kodiutils
from resources.lib.modules import state as state_module
from resources.lib.modules import xmltv
from resources.lib.modules.iptvsimple import IptvSimple

_LOGGER = logging.getLogger(__name__)

CHANNELS_VERSION = 1
EPG_VERSION = 1

# A provider that accepts the connection but never sends anything must not block
# the whole refresh (see docs/02-correctifs.md, F-05).
READ_TIMEOUT = 120
MAX_REPLY_SIZE = 64 * 1024 * 1024


def update_qs(url, **params):
    """Add or update a URL query string"""
    try:  # Python 3
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
    except ImportError:  # Python 2
        from urllib import urlencode

        from urlparse import parse_qsl, urlparse, urlunparse
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)


def count_channels(channels):
    """Count the channels of a provider payload (JSON list or raw M3U)."""
    if isinstance(channels, str):
        return channels.count('#EXTINF')
    if not channels:
        return 0
    return len(channels)


def count_programs(epg):
    """Count the programs of a provider payload without materializing it."""
    if isinstance(epg, xmltv.RawXmltv):
        return epg.count('<programme')
    if isinstance(epg, dict):
        return sum(len(items) for items in epg.values())
    if isinstance(epg, (list, tuple)):
        return len(epg)
    return 0


class Addon:
    """Helper class for Addon communication"""

    def __init__(self, addon_id, addon_obj, channels_uri, epg_uri):
        self.addon_id = addon_id
        self.addon_obj = addon_obj
        self.channels_uri = channels_uri
        self.epg_uri = epg_uri

        addon = kodiutils.get_addon(addon_id)
        self.addon_path = kodiutils.addon_path(addon)

    @classmethod
    def refresh(cls, show_progress=False):
        """Update channels and EPG data"""
        channels = []
        epg = []
        results = []

        if show_progress:
            progress = kodiutils.progress(message=kodiutils.localize(30703))  # Detecting IPTV add-ons...
        else:
            progress = None

        addons = cls.detect_iptv_addons()
        for index, addon in enumerate(addons):
            _LOGGER.info('Updating IPTV data for %s...', addon.addon_id)

            if progress:
                # Fetching channels and guide of {addon}...
                progress.update(int(100 * index / len(addons)),
                                kodiutils.localize(30704).format(addon=kodiutils.addon_name(addon.addon_obj)))

            # Fetch channels
            provider_channels = addon.get_channels()
            channels.append(dict(
                addon_id=addon.addon_id,
                addon_name=kodiutils.addon_name(addon.addon_obj),
                channels=provider_channels,
            ))

            if progress and progress.iscanceled():
                progress.close()
                return

            # Fetch EPG
            provider_epg = addon.get_epg()
            epg.append(provider_epg)
            results.append(dict(
                addon_id=addon.addon_id,
                channels=count_channels(provider_channels),
                programs=count_programs(provider_epg),
            ))

            if progress and progress.iscanceled():
                progress.close()
                return

        # Refuse to replace good files with a degraded collection (docs/02, F-02).
        output_dir = kodiutils.addon_profile()
        now = int(time.time())
        previous = state_module.load(output_dir)
        status, new_state, may_write = state_module.evaluate(results, previous)
        new_state[state_module.META_KEY] = state_module.record(previous, status, now)
        state_module.save(output_dir, new_state)

        if not may_write:
            _LOGGER.warning('Pass is %s: keeping the previous playlist and guide', status)
            if show_progress:
                progress.close()
            return

        # Write files
        if show_progress:
            progress.update(100, kodiutils.localize(30705))

        IptvSimple.write_playlist(channels)
        IptvSimple.write_epg(epg, channels)

        if kodiutils.get_setting_bool('iptv_simple_restart'):
            if show_progress:
                # Restart now.
                IptvSimple.restart(True)
            else:
                # Try to restart now. We will schedule it if the user is watching TV.
                IptvSimple.restart(False)

        # Only a complete pass proves that the files are good.
        if status == state_module.STATUS_OK:
            kodiutils.set_setting_int('last_refreshed', int(time.time()))
        else:
            _LOGGER.info('Pass is %s: last_refreshed not advanced', status)

        if show_progress:
            progress.close()

    @staticmethod
    def detect_iptv_addons():
        """Find add-ons that provide IPTV channel data"""
        result = kodiutils.jsonrpc(method="Addons.GetAddons",
                                   params={'installed': True, 'enabled': True, 'type': 'xbmc.python.pluginsource'})

        addons = []
        for row in result['result'].get('addons', []):
            addon = kodiutils.get_addon(row['addonid'])

            # Check if add-on supports IPTV Manager
            if addon.getSetting('iptv.enabled') != 'true':
                continue

            addons.append(Addon(
                addon_id=row['addonid'],
                addon_obj=addon,
                channels_uri=addon.getSetting('iptv.channels_uri'),
                epg_uri=addon.getSetting('iptv.epg_uri'),
            ))

        return addons

    def get_channels(self):
        """Get channel data from this add-on"""
        _LOGGER.info('Requesting channels from %s...', self.channels_uri)
        if not self.channels_uri:
            return []

        try:
            data = self._get_data_from_addon(self.channels_uri)
            _LOGGER.debug(data)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Something went wrong while calling %s: %s', self.addon_id, exc)
            return []

        # Return M3U8-format as-is without headers
        if not isinstance(data, dict):
            return data.replace('#EXTM3U\n', '')

        # JSON-STREAMS format
        if data.get('version', 1) > CHANNELS_VERSION:
            _LOGGER.warning('Skipping %s since it uses an unsupported version: %d', self.channels_uri,
                            data.get('version'))
            return []

        channels = []
        for channel in data.get('streams', []):
            # Check for required fields
            if not channel.get('name') or not channel.get('stream'):
                _LOGGER.warning('Skipping channel since it is incomplete: %s', channel)
                continue

            # Fix logo path to be absolute
            if not channel.get('logo'):
                channel['logo'] = kodiutils.addon_icon(self.addon_obj)
            elif not channel.get('logo').startswith(('http://', 'https://', 'special://', 'resource://', '/')):
                channel['logo'] = os.path.join(self.addon_path, channel.get('logo'))

            # Ensure group is a set
            if not channel.get('group'):
                channel['group'] = set()
            # Accept string values (backward compatible)
            elif isinstance(channel.get('group'), (bytes, str)):
                channel['group'] = set(channel.get('group').split(';'))
            # Accept string values (backward compatible, py2 version)
            elif sys.version_info.major == 2 and isinstance(channel.get('group'), unicode): # noqa: F821; pylint: disable=undefined-variable
                channel['group'] = set(channel.get('group').split(';'))
            elif isinstance(channel.get('group'), list):
                channel['group'] = set(list(channel.get('group')))
            else:
                _LOGGER.warning('Channel group is not a list: %s', channel)
                channel['group'] = set()
            # Add add-on name as group, if not already
            channel['group'].add(kodiutils.addon_name(self.addon_obj))

            channels.append(channel)

        return channels

    def get_epg(self):  # pylint: disable=too-many-return-statements
        """Get epg data from this add-on"""
        if not self.epg_uri:
            return {}

        _LOGGER.info('Requesting epg from %s...', self.epg_uri)
        try:
            data = self._get_data_from_addon(self.epg_uri)
            _LOGGER.debug(data)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Something went wrong while calling %s: %s', self.addon_id, exc)
            return {}

        # Return XMLTV-format as-is without headers and footers
        if not isinstance(data, dict):
            try:
                return xmltv.parse(data)
            except ValueError as exc:
                _LOGGER.error('Invalid XMLTV from %s: %s', self.addon_id, exc)
                return {}

        # JSON-EPG format
        if data.get('version', 1) > EPG_VERSION:
            _LOGGER.warning('Skipping EPG from %s since it uses an unsupported version: %d', self.epg_uri,
                            data.get('version'))
            return {}

        # Check for required fields
        if not data.get('epg'):
            _LOGGER.warning('Skipping EPG from %s since it is incomplete', self.epg_uri)
            return {}

        return data['epg']

    def _get_data_from_addon(self, uri):
        """Request data from the specified URI"""
        # Plugin path
        if uri.startswith('plugin://'):
            last_exc = None

            # A cold add-on can take longer than the first timeout to start and
            # answer. Retry once; the socket is closed by _wait_for_data().
            for attempt in range(2):
                sock = self._prepare_for_data()
                request_uri = update_qs(uri, port=sock.getsockname()[1])

                _LOGGER.info('Executing RunPlugin(%s)...', request_uri)
                kodiutils.execute_builtin('RunPlugin', request_uri)

                try:
                    return json.loads(self._wait_for_data(sock))
                except Exception as exc:  # pylint: disable=broad-except
                    last_exc = exc
                    if attempt == 0:
                        _LOGGER.warning('No reply from %s: %s; retrying once', uri, exc)
                        time.sleep(1)

            raise last_exc

        # Currently, only plugin:// uris are supported
        raise NotImplementedError

    @staticmethod
    def _prepare_for_data():
        """Prepare ourselves so we can receive data"""
        # Bind on localhost on a free port above 1024
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))

        _LOGGER.debug('Bound on port %s...', sock.getsockname()[1])

        # Listen for one connection
        sock.listen(1)
        return sock

    def _wait_for_data(self, sock, timeout=30):
        """Wait for data to arrive on the socket"""
        # Set a connection timeout
        # The remote and should connect back as soon as possible so we know that the request is being processed
        sock.settimeout(timeout)

        conn = None
        try:
            _LOGGER.debug('Waiting for a connection from %s on port %s...', self.addon_id, sock.getsockname()[1])

            # Accept one client
            conn, addr = sock.accept()
            _LOGGER.debug('Connected to %s:%s! Waiting for result...', addr[0], addr[1])

            # A provider may connect and then say nothing: bound the read.
            conn.settimeout(READ_TIMEOUT)

            # Read until the remote end closes the connection. Decode with a
            # streaming decoder: a UTF-8 character can span two recv() calls.
            decoder = codecs.getincrementaldecoder('utf-8')()
            chunks = []
            size = 0
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_REPLY_SIZE:
                    raise Exception('Reply from %s is larger than %d bytes' % (self.addon_id, MAX_REPLY_SIZE))
                chunks.append(decoder.decode(chunk))

            chunks.append(decoder.decode(b'', True))
            buf = ''.join(chunks)
            _LOGGER.debug('Received %d bytes from %s', size, self.addon_id)

            if not buf:
                # We got an empty reply, this means that something didn't go according to plan
                raise Exception('Something went wrong in %s' % self.addon_id)

            return buf

        except socket.timeout:
            raise Exception('Timeout waiting for reply on port %s' % sock.getsockname()[1])

        finally:
            if conn is not None:
                conn.close()

            # Close our socket
            _LOGGER.debug('Closing socket on port %s', sock.getsockname()[1])
            sock.close()
