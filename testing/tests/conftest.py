"""Task 26: the `slow` marker (registered in pytest.ini) applied from slow_tests.txt beside this file, so a test file
is never edited to carry it. `pytest -m "not slow"` is the inner loop; the full run is the gate."""
import os

import pytest

_LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slow_tests.txt")


def _entries():
    with open(_LIST, encoding="utf-8") as f:
        return tuple(s for s in (ln.strip() for ln in f) if s and not s.startswith("#"))


def pytest_collection_modifyitems(config, items):
    entries = _entries()
    for item in items:
        nid = item.nodeid
        if any(nid == e or nid.startswith(e + "::") or nid.startswith(e + "[") for e in entries):
            item.add_marker(pytest.mark.slow)
