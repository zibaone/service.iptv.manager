# -*- coding: utf-8 -*-
"""Tests for raw XMLTV handling"""

# pylint: disable=invalid-name,missing-docstring,no-self-use

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import tempfile
import tracemalloc
import unittest
from unittest import mock

from resources.lib import kodiutils
from resources.lib.modules import xmltv
from resources.lib.modules.iptvsimple import IptvSimple
from resources.lib.modules.xmltv import RawXmltv


class XmltvTest(unittest.TestCase):
    """Raw XMLTV tests"""

    def test_parse_extracts_the_tv_content(self):
        """Only the content of the <tv> element is kept."""
        document = '<?xml version="1.0"?>\n<tv generator-info-name="test">\n<programme start="1" stop="2" channel="c" />\n</tv>\n'
        parsed = xmltv.parse(document)

        self.assertIsInstance(parsed, RawXmltv)
        self.assertEqual(''.join(parsed.iter_chunks()), '\n<programme start="1" stop="2" channel="c" />\n')

    def test_parse_handles_attributes_on_tv(self):
        """Attributes of the <tv> element are not part of the content."""
        parsed = xmltv.parse('<tv date="2026-10-25"><channel id="a" /></tv>')

        self.assertEqual(''.join(parsed.iter_chunks()), '<channel id="a" />')

    def test_parse_rejects_missing_tv(self):
        """A payload without <tv> is refused."""
        with self.assertRaises(ValueError):
            xmltv.parse('<not-xmltv />')

    def test_parse_rejects_unterminated_tv(self):
        """A payload without </tv> is refused."""
        with self.assertRaises(ValueError):
            xmltv.parse('<tv><channel id="a" />')

    def test_parse_rejects_non_text(self):
        """A bytes payload is refused instead of being decoded silently."""
        with self.assertRaises(ValueError):
            xmltv.parse(b'<tv></tv>')

    def test_chunks_do_not_copy_the_payload(self):
        """Reading the payload chunk by chunk does not allocate a second copy."""
        programs = '<programme start="1" stop="2" channel="c" />\n' * 100000
        document = '<tv>' + programs + '</tv>'

        tracemalloc.start()
        parsed = xmltv.parse(document)
        with tempfile.TemporaryFile() as handle:
            for chunk in parsed.iter_chunks():
                handle.write(chunk.encode('utf-8'))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.assertEqual(len(parsed), len(programs))
        self.assertLess(peak, 1024 * 1024, 'the XMLTV payload was copied in memory')

    def test_count_handles_a_needle_on_a_chunk_boundary(self):
        """Counting programs must not miss one that straddles two chunks."""
        filler = 'x' * (xmltv.DEFAULT_CHUNK_SIZE - 5)
        document = '<tv>' + filler + '<programme start="1" stop="2" channel="c" />' + filler + '</tv>'

        parsed = xmltv.parse(document)

        self.assertEqual(parsed.count('<programme'), 1)
        self.assertEqual(parsed.count('<programme start='), 1)

    def test_write_epg_streams_raw_xmltv(self):
        """write_epg() writes a RawXmltv payload as-is."""
        programs = '<programme start="1" stop="2" channel="c"><title>Show</title></programme>'
        with tempfile.TemporaryDirectory() as output_dir:
            with mock.patch.object(kodiutils, 'addon_profile', return_value=output_dir + os.sep):
                IptvSimple.write_epg([xmltv.parse('<tv>' + programs + '</tv>')], [])

            with open(os.path.join(output_dir, 'epg.xml'), 'rb') as handle:
                content = handle.read()

        self.assertIn(programs.encode('utf-8'), content)
        self.assertTrue(content.startswith(b'<?xml version="1.0" encoding="UTF-8"?>'))
        self.assertTrue(content.rstrip().endswith(b'</tv>'))


if __name__ == '__main__':
    unittest.main()
