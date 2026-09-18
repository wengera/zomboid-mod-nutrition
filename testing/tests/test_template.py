"""The driver template's no-boot dry run: no game, and nothing left behind.

`_template.py` under `PZT_TEMPLATE_DRY_RUN=1` starts no server and no client, so this test needs
no java -- but it does need a profile, and `profile.load` resolves the profile's fixture RECORD
itself (`pzt/profile.py:260` -> `pzt/fixture.py:65-67`, SystemExit when the fixture has no
`cache/` blob). Those caches are gitignored per-machine blobs, so on a fresh clone there is no
profile to load and nothing to dry-run: the test gates on the blob and skips itself elsewhere,
the same convention `test_profile.py` states in its own docstring.
"""
import json, os, subprocess, sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(REPO, "testing", "experiments", "_template.py")
RUNS = os.path.join(REPO, "testing", "runs")
BLOB = os.path.join(REPO, "testing", "fixtures", "default", "cache", "server")

pytestmark = pytest.mark.skipif(
    not os.path.isdir(BLOB),
    reason=f"no fixture blob on this machine ({BLOB}); `pzt provision --name default` builds it")


def template_run_dirs():
    """The run directories a dry run would create if it were not gated."""
    try:
        return {d for d in os.listdir(RUNS) if d.startswith("template-")}
    except OSError:                      # testing/runs/ need not exist yet
        return set()


def test_template_dry_run_prints_provenance_and_boots_nothing():
    before = template_run_dirs()
    env = dict(os.environ, PZT_TEMPLATE_DRY_RUN="1")
    r = subprocess.run([sys.executable, TEMPLATE], capture_output=True, text=True, env=env, cwd=REPO, timeout=120)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    for key in ("run_id", "session", "profile", "commit", "harness_lua_commit", "harness_lua_dirty",
                "doctor_clean", "acceptance_run", "phases", "dry_run"):
        assert key in out, key
    assert out["dry_run"] is True and out["phases"] == {} and out["doctor_clean"] is None
    # A dry run boots nothing, so it writes nothing: no run directory is created, and the run_id
    # says as much rather than carrying a timestamp that nothing on disk corresponds to.
    assert out["run_id"] == "template-dry-run"
    assert template_run_dirs() == before, "the dry run created a run directory"
