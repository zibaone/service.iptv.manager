# -*- coding: utf-8 -*-
"""Tests for the persistent provider state"""

# pylint: disable=invalid-name,missing-docstring,no-self-use

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import tempfile
import unittest

from resources.lib.modules import state


class StateFileTest(unittest.TestCase):
    """Reading the state file never raises"""

    def test_missing_file_is_an_empty_state(self):
        """A first boot has no state file."""
        with tempfile.TemporaryDirectory() as output_dir:
            self.assertEqual(state.load(output_dir + os.sep), {})

    def test_corrupt_file_is_ignored(self):
        """A truncated JSON file must not break a refresh."""
        with tempfile.TemporaryDirectory() as output_dir:
            with open(os.path.join(output_dir, state.STATE_FILE), 'w', encoding='utf-8') as handle:
                handle.write('{"a": ')
            self.assertEqual(state.load(output_dir + os.sep), {})

    def test_a_list_is_not_a_state(self):
        """An unexpected JSON shape is ignored."""
        with tempfile.TemporaryDirectory() as output_dir:
            with open(os.path.join(output_dir, state.STATE_FILE), 'w', encoding='utf-8') as handle:
                handle.write('[]')
            self.assertEqual(state.load(output_dir + os.sep), {})


if __name__ == '__main__':
    unittest.main()
