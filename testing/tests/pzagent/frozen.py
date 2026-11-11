"""Plan 35 Task 8 (the deletion; the reflex owns contact): the tests whose pins a build before the deletion held, re-run
on a `git archive` of that build (CLAUDE.md § 5: a replay or seam broken at HEAD by a later change is frozen on a
`git archive` of the last build whose pins it held, as `test_replay_decisions.R2_FROZEN` freezes the sixth golden's).

The deletion made the engagement the only behaviour (every melee carries `work`; the dispatch meets the pile, the
corner, the door fight and the doorway stand; the `unreachable` flee is lifted in contact) and removed the switches a
seam set off (DRAG_GUARD_FIGHT, SIDE_CLEAR, STRUNG_HOLD, the leave's first-line shove), so a replay of a live ring that
announces `melee` (F17, F18, the trials) or a seam onto Plan 33's and Plan 34's goldens no longer reproduces what its
test pinned. Each such test keeps its name and its docstring in its own file, and its body runs the archived copy of
itself (`frozen`): one child pytest a test file, its frozen nodes together, cached for the session.

T8_FROZEN, the last build whose pins they held: `91062036` (`Plan 35 Task 4: proof round 2 rows`), the head this
task's branch started from."""
import functools
import importlib.util
import io
import os
import subprocess
import sys
import tarfile
import tempfile

import pytest

T8_FROZEN = "91062036"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BASE = ("pytest.ini", "data", "testing/agent", "testing/PZAgent", "testing/tests/conftest.py",
        "testing/tests/slow_tests.txt", "testing/tests/pzagent")


def _scrubbed_env():
    """`tools/tests/gitenv.scrubbed_env` (CLAUDE.md § 6 scratch copies: no GIT_* variable aims git, or the archived
    child, at the real repository), loaded by path."""
    spec = importlib.util.spec_from_file_location("gitenv", os.path.join(REPO, "tools", "tests", "gitenv.py"))
    gitenv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gitenv)
    return gitenv.scrubbed_env()


@functools.lru_cache(maxsize=None)
def _run(test_file, funcs, extra):
    """(returncode, output) of the frozen functions `funcs` of `test_file` (its path under the repository) run in one
    child pytest on a `git archive` of T8_FROZEN holding BASE and `extra` (the artifacts the tests read); skipped where
    git or the commit is not reachable (a source export with no history)."""
    try:
        blob = subprocess.run(["git", "-C", REPO, "archive", "--format=tar", T8_FROZEN] + list(BASE) + list(extra),
                              capture_output=True, check=True, env=_scrubbed_env()).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip("no git archive of %s: %s" % (T8_FROZEN, e))
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
            tf.extractall(tmp, filter="data")
        nodes = ["%s::%s" % (test_file, f) for f in funcs]
        env = dict(_scrubbed_env(), PYTHONDONTWRITEBYTECODE="1")
        runs = runs_root()
        if runs is not None:
            env["PZT_RUNS"] = runs   # the trials' replays read this machine's `testing/runs/` (per-machine)
        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider", "-p", "no:xdist"]
                             + nodes, cwd=tmp, capture_output=True, text=True, env=env)
    return run.returncode, run.stdout[-20000:] + run.stderr[-4000:]


def runs_root():
    """This machine's trial runs folder: `$PZT_RUNS`, else the first `testing/runs/` in this tree or a tree it sits in
    (a worktree lives inside the main checkout), else None."""
    if os.environ.get("PZT_RUNS"):
        return os.environ["PZT_RUNS"]
    p = REPO
    while True:
        if os.path.isdir(os.path.join(p, "testing", "runs")):
            return os.path.join(p, "testing", "runs")
        if os.path.dirname(p) == p:
            return None
        p = os.path.dirname(p)


def frozen(request, funcs, extra=()):
    """Asserts the running test (`request.node`, its parameter id included) passed on T8_FROZEN's archive, run with the
    file's other frozen functions `funcs` (one child pytest a file)."""
    test_file = os.path.relpath(str(request.node.fspath), REPO).replace(os.sep, "/")
    rc, out = _run(test_file, tuple(funcs), tuple(extra))
    assert "PASSED %s::%s" % (test_file, request.node.name) in out, out
