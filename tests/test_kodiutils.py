# -*- coding: utf-8 -*-
"""Tests for the settings access layer (Kodi 22 typed API)"""

# pylint: disable=invalid-name,missing-docstring,no-self-use,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from unittest import mock

from resources.lib import kodiutils

INVALID_TYPE = RuntimeError('Invalid setting type "string" for "last_refreshed"')


class IntegerSettingsTest(unittest.TestCase):
    """Integer settings must work on Kodi 21 and on Kodi 22"""

    def test_reads_the_string_api_first(self):
        """Kodi 21: a select is a string; the typed getter must not be called.

        The typed getter raised "Invalid setting type" on a select and Kodi
        logged the exception on every service tick (Zero 3, 2026-10-26).
        """
        settings = mock.Mock()
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', return_value='24'):
            self.assertEqual(kodiutils.get_setting_int('refresh_interval', 24), 24)
        settings.getInt.assert_not_called()

    def test_falls_back_to_the_typed_api(self):
        """Kodi 22 refuses the string read of an integer setting: use the typed getter."""
        settings = mock.Mock()
        settings.getInt.return_value = 42
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', side_effect=INVALID_TYPE):
            self.assertEqual(kodiutils.get_setting_int('last_refreshed', 0), 42)
        settings.getInt.assert_called_once_with('last_refreshed')

    def test_keeps_a_legitimate_zero(self):
        """A never-refreshed setting stays 0 instead of being replaced by nothing."""
        settings = mock.Mock()
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', return_value='0'):
            self.assertEqual(kodiutils.get_setting_int('last_refreshed', 0), 0)
        settings.getInt.assert_not_called()

    def test_missing_setting_returns_the_default(self):
        """An empty value and a refused typed read fall back to the caller default."""
        settings = mock.Mock()
        settings.getInt.side_effect = INVALID_TYPE
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', return_value=''):
            self.assertEqual(kodiutils.get_setting_int('refresh_interval', 24), 24)

    def test_set_writes_the_string_first(self):
        """Kodi 21: the string writer is used and setSettingInt is never called."""
        with mock.patch.object(kodiutils.ADDON, 'setSettingInt') as typed, \
                mock.patch.object(kodiutils.ADDON, 'setSetting', return_value=True) as legacy:
            kodiutils.set_setting_int('last_refreshed', 1700000000)
        legacy.assert_called_once_with('last_refreshed', '1700000000')
        typed.assert_not_called()

    def test_set_falls_back_to_the_typed_writer(self):
        """Kodi 22 raises on the string writer for an integer setting: use the typed one."""
        with mock.patch.object(kodiutils.ADDON, 'setSettingInt', return_value=True) as typed, \
                mock.patch.object(kodiutils.ADDON, 'setSetting', side_effect=INVALID_TYPE):
            kodiutils.set_setting_int('last_refreshed', 1700000000)
        typed.assert_called_once_with('last_refreshed', 1700000000)

    def test_set_never_raises_when_both_writers_fail(self):
        """A setting that cannot be written must not stop the caller."""
        with mock.patch.object(kodiutils.ADDON, 'setSettingInt', side_effect=INVALID_TYPE), \
                mock.patch.object(kodiutils.ADDON, 'setSetting', side_effect=INVALID_TYPE):
            self.assertIsNone(kodiutils.set_setting_int('last_refreshed', 1700000000))


class BooleanSettingsTest(unittest.TestCase):
    """Booleans keep the legacy order: a schema-less bool logs an error on getBool"""

    def test_reads_the_legacy_api_first(self):
        """A stored 'true' is read without touching the typed getter."""
        settings = mock.Mock()
        with mock.patch.object(kodiutils.ADDON, 'getSetting', return_value='true'), \
                mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings):
            self.assertTrue(kodiutils.get_setting_bool('iptv_simple_restart'))
        settings.getBool.assert_not_called()

    def test_falls_back_to_the_typed_api(self):
        """When the string read is refused, the typed getter returns the schema value."""
        settings = mock.Mock()
        settings.getBool.return_value = True
        with mock.patch.object(kodiutils.ADDON, 'getSetting', side_effect=INVALID_TYPE), \
                mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings):
            self.assertTrue(kodiutils.get_setting_bool('iptv_simple_restart'))


if __name__ == '__main__':
    unittest.main()
