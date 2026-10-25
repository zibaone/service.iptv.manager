# -*- coding: utf-8 -*-
"""Per-provider state, used to refuse writing a degraded collection."""

from __future__ import absolute_import, division, unicode_literals

import json
import logging
import os

_LOGGER = logging.getLogger(__name__)

STATE_FILE = 'providers_state.json'
MAX_FAILURES = 3

STATUS_OK = 'ok'
STATUS_PARTIAL = 'partial'
STATUS_DEGRADED = 'degraded'
STATUS_FAILED = 'failed'


def load(output_dir):
    """Read the previous state, or an empty dict when there is none."""
    try:
        with open(os.path.join(output_dir, STATE_FILE), 'r', encoding='utf-8') as fdesc:
            data = json.load(fdesc)
    except (IOError, OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(output_dir, state):
    """Write the state atomically, so a reader never sees a partial file."""
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    path = os.path.join(output_dir, STATE_FILE)
    with open(path + '.tmp', 'w', encoding='utf-8') as fdesc:
        json.dump(state, fdesc, indent=2, sort_keys=True)
        fdesc.write('\n')
    os.replace(path + '.tmp', path)


def evaluate(results, previous):
    """Decide whether a pass may replace the playlist and the guide.

    ``results`` is a list of dicts with ``addon_id``, ``channels`` and
    ``programs`` counts. ``previous`` is the state read before the pass.
    Returns ``(status, new_state, may_write)``.
    """
    new_state = {}
    may_write = True
    any_data = False
    any_problem = False

    for result in results:
        addon_id = result['addon_id']
        channels = result.get('channels') or 0
        programs = result.get('programs') or 0
        old = previous.get(addon_id) or {}
        failures = old.get('failures') or 0

        dropped = (old.get('channels') or 0) > 0 and channels == 0
        dropped = dropped or ((old.get('programs') or 0) > 0 and programs == 0)

        accepted = False
        if dropped:
            failures += 1
            if failures >= MAX_FAILURES:
                # Three passes in a row: the provider really lost its channels,
                # stop believing the old state (docs/02, F-02 risk).
                _LOGGER.warning('Provider %s lost its channels or guide for the %dth time; '
                                'accepting the decrease', addon_id, failures)
                failures = 0
                accepted = True
            else:
                may_write = False
                _LOGGER.warning('Provider %s lost its channels or guide (%d consecutive failures)',
                                addon_id, failures)
        elif channels or programs:
            failures = 0

        new_state[addon_id] = {
            'channels': channels,
            'programs': programs,
            'failures': failures,
        }
        if channels or programs:
            any_data = True
        if (dropped and not accepted) or not channels and not programs:
            any_problem = True

    if not any_data:
        status = STATUS_FAILED
        may_write = False
    elif not may_write:
        status = STATUS_DEGRADED
    elif any_problem:
        status = STATUS_PARTIAL
    else:
        status = STATUS_OK

    return status, new_state, may_write
