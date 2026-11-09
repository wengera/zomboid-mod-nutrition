"""Task 26: the `slow` marker (registered in pytest.ini) applied from slow_tests.txt beside this file, so a test file
is never edited to carry it. `pytest -m "not slow"` is the inner loop; the full run is the gate."""
import os

import pytest

_LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slow_tests.txt")


def _entries():
    with open(_LIST, encoding="utf-8") as f:
        return tuple(s for s in (ln.strip() for ln in f) if s and not s.startswith("#"))


def _xdist_group(nid):
    """The pytest-xdist group a test runs in under `--dist loadgroup` (CLAUDE.md section 3, the parallel gate): every test
    of `testing/tests/kernel/` in one group, since its coverage gate `test_zz_coverage.py` reads the line hits of the whole
    kernel session from one process; every other file its own group, so a file's tests share one worker (the `loadfile`
    affinity that keeps module-level state and tmp files apart)."""
    path = nid.split("::", 1)[0].replace("\\", "/")
    if "/kernel/" in path or path.startswith("kernel/"):
        return "kernel"
    return path


def pytest_collection_modifyitems(config, items):
    entries = _entries()
    for item in items:
        nid = item.nodeid
        if any(nid == e or nid.startswith(e + "::") or nid.startswith(e + "[") for e in entries):
            item.add_marker(pytest.mark.slow)
        if nid.replace("\\", "/").startswith("testing/tests/") and item.get_closest_marker("xdist_group") is None:
            item.add_marker(pytest.mark.xdist_group(name=_xdist_group(nid)))   # this directory's items only: both conftests' hooks see every item
