# -*- coding: utf-8 -*-
"""Helpers for raw XMLTV payloads."""

from __future__ import absolute_import, division, unicode_literals

DEFAULT_CHUNK_SIZE = 64 * 1024


class RawXmltv:
    """A raw XMLTV payload kept as a slice of the original text.

    The programs are not copied: write_epg() streams the slice in small chunks,
    so a 90 MB guide does not double in memory (see docs/02-correctifs.md, F-06).
    """

    def __init__(self, data, start, end):
        self._data = data
        self._start = start
        self._end = end

    def __len__(self):
        return self._end - self._start

    def __repr__(self):
        return '<RawXmltv %d chars>' % len(self)

    def iter_chunks(self, size=DEFAULT_CHUNK_SIZE):
        """Yield the inner XML in chunks of at most ``size`` characters."""
        position = self._start
        while position < self._end:
            stop = min(position + size, self._end)
            yield self._data[position:stop]
            position = stop

    def count(self, needle):
        """Count the occurrences of ``needle`` without copying the payload."""
        if not needle:
            return 0
        if len(needle) == 1:
            return sum(chunk.count(needle) for chunk in self.iter_chunks())

        total = 0
        carry = ''
        overlap = len(needle) - 1
        for chunk in self.iter_chunks():
            text = carry + chunk
            total += text.count(needle)
            carry = text[-overlap:]
        return total


def parse(data):
    """Return a RawXmltv for the content of a <tv> element.

    Raises ValueError when the payload is not a usable XMLTV document.
    """
    if not isinstance(data, str):
        raise ValueError('raw XMLTV payload is not text')

    start = data.find('<tv')
    if start < 0:
        raise ValueError('raw XMLTV payload has no <tv> element')

    opening_end = data.find('>', start)
    if opening_end < 0:
        raise ValueError('raw XMLTV payload has an unterminated <tv> element')

    closing_start = data.rfind('</tv>')
    if closing_start < opening_end:
        raise ValueError('raw XMLTV payload has no </tv> element')

    return RawXmltv(data, opening_end + 1, closing_start)
