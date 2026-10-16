"""The rebuild marker's skip (Plan 15 ruling): while docs/mod-guide/REBUILD_PENDING exists, a test module's
MOD_BUILD_TESTS, and every test taking the `kh` kernel host there, skip with the marker's text. The marker is read
through tools/mod_guide_data.py's rebuild_pending; removing it runs them again.
"""
import os
import sys

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import mod_guide_data  # noqa: E402


def mod_build_skip(item, reason):
    """Whether item is a mod-build test of a module that names MOD_BUILD_TESTS; marks it skipped with reason if so."""
    names = getattr(getattr(item, "module", None), "MOD_BUILD_TESTS", None)
    if names is None:
        return False
    fn = getattr(item, "originalname", None) or item.name.split("[")[0]
    if fn not in names and "kh" not in getattr(item, "fixturenames", ()):
        return False
    item.add_marker(pytest.mark.skip(reason="%s: %s" % (mod_guide_data.PENDING_REL, reason)))
    return True


def pytest_collection_modifyitems(config, items):
    reason = mod_guide_data.rebuild_pending()
    if reason is None:
        return
    for item in items:
        mod_build_skip(item, reason)
