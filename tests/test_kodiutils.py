# -*- coding: utf-8 -*-
"""Tests for the settings access layer (Kodi 22 typed API)"""

# pylint: disable=invalid-name,missing-docstring,no-self-use,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
from unittest import mock

from resources.lib import kodiutils

INVALID_TYPE = RuntimeError('Invalid setting type "string" for "last_refreshed"')


class IntegerSettingsTest(unittest.TestCase):
    """Integer settings must work on Kodi 22 and on older releases"""

    def test_prefers_the_typed_api(self):
        """Kodi 22: the typed getter is used and the string read never happens."""
        settings = mock.Mock()
        settings.getInt.return_value = 42
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', side_effect=INVALID_TYPE) as legacy:
            self.assertEqual(kodiutils.get_setting_int('last_refreshed', 0), 42)
        legacy.assert_not_called()

    def test_falls_back_to_the_legacy_api(self):
        """A string-typed setting (select) raises on the typed getter; int() still works."""
        settings = mock.Mock()
        settings.getInt.side_effect = INVALID_TYPE
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', return_value='24'):
            self.assertEqual(kodiutils.get_setting_int('refresh_interval', 24), 24)

    def test_set_uses_the_typed_api(self):
        """The setter writes an integer when Kodi accepts it."""
        with mock.patch.object(kodiutils.ADDON, 'setSettingInt', return_value=True) as typed, \
                mock.patch.object(kodiutils.ADDON, 'setSetting') as legacy:
            kodiutils.set_setting_int('last_refreshed', 1700000000)
        typed.assert_called_once_with('last_refreshed', 1700000000)
        legacy.assert_not_called()

    def test_set_falls_back_when_the_type_is_invalid(self):
        """Kodi 22 raises on setSettingInt for an untyped setting: write the string."""
        with mock.patch.object(kodiutils.ADDON, 'setSettingInt', side_effect=INVALID_TYPE), \
                mock.patch.object(kodiutils.ADDON, 'setSetting') as legacy:
            kodiutils.set_setting_int('last_refreshed', 1700000000)
        legacy.assert_called_once_with('last_refreshed', '1700000000')

    def test_prefers_a_non_zero_legacy_value_over_a_zero(self):
        """A Kodi that reads a select as 0 must not turn 24 h into 0."""
        settings = mock.Mock()
        settings.getInt.return_value = 0
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', return_value='24'):
            self.assertEqual(kodiutils.get_setting_int('refresh_interval', 24), 24)

    def test_keeps_a_legitimate_zero(self):
        """A never-refreshed setting stays 0 instead of being replaced by nothing."""
        settings = mock.Mock()
        settings.getInt.return_value = 0
        with mock.patch.object(kodiutils.ADDON, 'getSettings', return_value=settings), \
                mock.patch.object(kodiutils.ADDON, 'getSetting', return_value='0'):
            self.assertEqual(kodiutils.get_setting_int('last_refreshed', 0), 0)


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
