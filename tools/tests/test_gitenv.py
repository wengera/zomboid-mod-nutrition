import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import gitenv
import test_claims_check as tcc


def _head(d):
    r = subprocess.run(["git", "-C", d, "rev-parse", "--verify", "-q", "HEAD"], capture_output=True, text=True,
                       env=gitenv.scrubbed_env())
    return r.stdout.strip()


def test_a_commit_lands_in_its_own_directory_with_git_dir_set(monkeypatch):
    with tempfile.TemporaryDirectory() as other, tempfile.TemporaryDirectory() as mine:
        tcc._git(other, "init", "-q")
        open(os.path.join(other, "a"), "w").write("a")
        tcc._git(other, "add", "a")
        tcc._git(other, "commit", "-q", "-m", "first")
        before = _head(other)
        monkeypatch.setenv("GIT_DIR", os.path.join(other, ".git"))
        tcc._git(mine, "init", "-q")
        open(os.path.join(mine, "b"), "w").write("b")
        tcc._git(mine, "add", "b")
        tcc._git(mine, "commit", "-q", "-m", "second")
        assert _head(mine) and _head(mine) != before
        assert _head(other) == before
