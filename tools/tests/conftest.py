"""Task 26: the `slow` marker (registered in pytest.ini) applied from slow_tests.txt beside this file, so a test file
is never edited to carry it. `pytest -m "not slow"` is the inner loop; the full run is the gate."""
import os

import pytest

_LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slow_tests.txt")


def _entries():
    with open(_LIST, encoding="utf-8") as f:
        return tuple(s for s in (ln.strip() for ln in f) if s and not s.startswith("#"))


def _xdist_group(nid):
    """The pytest-xdist group under `--dist loadgroup` (CLAUDE.md section 3, the parallel gate): a file's tests share one
    worker (the `loadfile` affinity), so module-level state and a file's tmp paths never race another worker."""
    return nid.split("::", 1)[0].replace("\\", "/")


def pytest_collection_modifyitems(config, items):
    entries = _entries()
    for item in items:
        nid = item.nodeid
        if any(nid == e or nid.startswith(e + "::") or nid.startswith(e + "[") for e in entries):
            item.add_marker(pytest.mark.slow)
        if nid.replace("\\", "/").startswith("tools/tests/") and item.get_closest_marker("xdist_group") is None:
            item.add_marker(pytest.mark.xdist_group(name=_xdist_group(nid)))   # this directory's items only: both conftests' hooks see every item
