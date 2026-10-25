# -*- coding: utf-8 -*-
"""Tests for the provider socket reader"""

# pylint: disable=invalid-name,missing-docstring,no-self-use

from __future__ import absolute_import, division, print_function, unicode_literals

import socket
import types
import unittest
from unittest import mock

from resources.lib.modules import addon as addon_module
from resources.lib.modules.addon import Addon


class FakeConnection:
    """Minimal stand-in for a connected socket."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.timeout = None
        self.closed = False

    def settimeout(self, value):
        self.timeout = value

    def recv(self, size):
        if not self.chunks:
            return b''
        item = self.chunks.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        self.closed = True


class FakeSocket:
    """Minimal stand-in for a listening socket."""

    def __init__(self, conn=None, accept_error=None):
        self.conn = conn
        self.accept_error = accept_error
        self.timeout = None
        self.closed = False

    def settimeout(self, value):
        self.timeout = value

    def accept(self):
        if self.accept_error:
            raise self.accept_error
        return self.conn, ('127.0.0.1', 12345)

    def getsockname(self):
        return ('127.0.0.1', 4321)

    def close(self):
        self.closed = True


class AddonSocketTest(unittest.TestCase):
    """Socket reader tests"""

    def setUp(self):
        self.addon = types.SimpleNamespace(addon_id='plugin.video.example')

    def read(self, sock):
        return Addon._wait_for_data(self.addon, sock)

    def test_payload_utf8_split_across_chunks(self):
        """A UTF-8 character split across two recv() calls is decoded correctly."""
        payload = '{"name": "één"}'
        data = payload.encode('utf-8')
        split = data.index(b'\xc3') + 1  # cut in the middle of the two-byte é
        conn = FakeConnection([data[:split], data[split:]])
        sock = FakeSocket(conn)

        self.assertEqual(self.read(sock), payload)
        self.assertEqual(conn.timeout, addon_module.READ_TIMEOUT)
        self.assertTrue(conn.closed)
        self.assertTrue(sock.closed)

    def test_provider_connects_then_stalls(self):
        """A provider that connects and sends nothing fails within the read timeout."""
        conn = FakeConnection([socket.timeout()])
        sock = FakeSocket(conn)

        with self.assertRaises(Exception) as context:
            self.read(sock)

        self.assertIn('Timeout waiting for reply', str(context.exception))
        self.assertTrue(conn.closed)
        self.assertTrue(sock.closed)

    def test_accept_timeout(self):
        """A provider that never connects fails with the accept timeout."""
        sock = FakeSocket(accept_error=socket.timeout())

        with self.assertRaises(Exception) as context:
            self.read(sock)

        self.assertIn('Timeout waiting for reply', str(context.exception))
        self.assertTrue(sock.closed)

    def test_reply_too_large(self):
        """An oversized reply is refused instead of being buffered."""
        conn = FakeConnection([b'0123456789', b'abcdefghij'])
        sock = FakeSocket(conn)

        with mock.patch.object(addon_module, 'MAX_REPLY_SIZE', 10):
            with self.assertRaises(Exception) as context:
                self.read(sock)

        self.assertIn('larger than', str(context.exception))
        self.assertTrue(conn.closed)

    def test_empty_reply(self):
        """An empty reply is reported as an error."""
        conn = FakeConnection([])
        sock = FakeSocket(conn)

        with self.assertRaises(Exception) as context:
            self.read(sock)

        self.assertIn('Something went wrong', str(context.exception))


if __name__ == '__main__':
    unittest.main()
