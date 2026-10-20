"""Run a frozen test on a `git archive` of the build it was recorded on (CLAUDE.md § 5: a replay broken at HEAD by a
later mod change is never patched; it re-runs on the build its reading names).

run(tmp, commit, nodeid, extra) extracts `mod`, `tools`, `testing/tests`, `testing/experiments` and the `extra` paths (an artifact folder)
at `commit` into `tmp` and runs pytest on `nodeid` (one node id, or a list of them run in one child) there in a child
process; it returns (returncode, output). It skips when git or the commit is not reachable (a source export with no
history)."""
import io
import os
import subprocess
import sys
import tarfile

import pytest

from .server_host import REPO


def run(tmp, commit, nodeid, extra=()):
    try:
        blob = subprocess.run(["git", "-C", REPO, "archive", "--format=tar", commit, "mod", "tools", "testing/tests", "testing/experiments",
                               *extra], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip("no git archive of %s: %s" % (commit, e))
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        tf.extractall(str(tmp), filter="data")
    nodes = [nodeid] if isinstance(nodeid, str) else list(nodeid)
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *nodes], cwd=str(tmp),
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return p.returncode, p.stdout[-3000:] + p.stderr[-2000:]
