"""tools/trial_snapshot.py: a commit's tree, the working tree with its diff, the stamp, the reuse and the launch line.
Every git call runs under gitenv.scrubbed_env in a repository the test makes."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
import gitenv  # noqa: E402
import trial_snapshot as ts  # noqa: E402


def git(d, *args):
    r = subprocess.run(["git", "-C", d, *args], capture_output=True, env=gitenv.scrubbed_env())
    assert r.returncode == 0, r.stderr
    return r.stdout.decode().strip()


def make_repo(d):
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@example.invalid")
    git(d, "config", "user.name", "t")
    git(d, "config", "core.autocrlf", "false")
    os.makedirs(os.path.join(d, "testing", "agent", "drivers"))
    for rel, text in (("a.txt", "alpha\n"), ("testing/agent/drivers/x_trial.py", "print(1)\n"), ("sub/b.txt", "bee\n")):
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", newline="\n") as f:
            f.write(text)
    git(d, "add", "a.txt", "testing/agent/drivers/x_trial.py", "sub/b.txt")
    git(d, "commit", "-q", "-m", "first")
    return git(d, "rev-parse", "HEAD")


def listing(d):
    out = []
    for base, _dirs, files in os.walk(d):
        for f in files:
            out.append(os.path.relpath(os.path.join(base, f), d).replace(os.sep, "/"))
    return sorted(out)


def test_a_clean_commit_tree_matches_git_archive():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        sha = make_repo(repo)
        tree, stamp, reused, left = ts.build(repo, "HEAD", root)
        assert tree == os.path.join(root, sha) and not reused and left == 0
        names = git(repo, "ls-tree", "-r", "--name-only", sha).split("\n")
        assert [n for n in listing(tree) if n != ts.STAMP] == sorted(names)
        assert not os.path.exists(os.path.join(tree, ".git"))
        for n in names:
            assert open(os.path.join(tree, n), "rb").read() == open(os.path.join(repo, n), "rb").read()
        assert stamp["commit"] == sha and stamp["dirty"] is False and stamp["diff_sha256"] is None
        with open(os.path.join(tree, ts.STAMP)) as f:
            assert json.load(f) == stamp


def test_a_dirty_tree_stamp_carries_the_diff_hash_and_the_tree_the_edit():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        sha = make_repo(repo)
        with open(os.path.join(repo, "a.txt"), "w", newline="\n") as f:
            f.write("alpha\nedited\n")
        with open(os.path.join(repo, "scratch.txt"), "w") as f:
            f.write("untracked")
        diff = subprocess.run(["git", "-C", repo, "diff", "HEAD", "--binary"], capture_output=True,
                              env=gitenv.scrubbed_env()).stdout
        digest = hashlib.sha256(diff).hexdigest()
        tree, stamp, reused, left = ts.build(repo, ts.WORKTREE, root)
        assert os.path.basename(tree) == "%s-dirty-%s" % (sha, digest[:12])
        assert stamp["commit"] == sha and stamp["dirty"] is True and stamp["diff_sha256"] == digest
        assert open(os.path.join(tree, "a.txt")).read() == "alpha\nedited\n"
        assert open(os.path.join(tree, ts.DIFF), "rb").read() == diff
        assert not os.path.exists(os.path.join(tree, "scratch.txt")) and left == 1
        assert stamp["untracked_left_out"] == 1
        # the commit's own clean tree is not touched by it
        assert git(repo, "show", "HEAD:a.txt") == "alpha"


def test_a_clean_commits_stamp_says_no_untracked_file_was_left_out():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        _tree, stamp, _r, _l = ts.build(repo, "HEAD", root)
        assert stamp["untracked_left_out"] == 0


def test_a_reused_dirty_tree_keeps_the_untracked_marker_in_the_summary(capsys):
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        with open(os.path.join(repo, "a.txt"), "w", newline="\n") as f:
            f.write("alpha\nedited\n")
        with open(os.path.join(repo, "new_variant.py"), "w") as f:
            f.write("x = 1\n")
        assert ts.main([ts.WORKTREE, "--root", root, "--repo", repo]) == 0
        assert "untracked_left_out: 1" in capsys.readouterr().out
        os.remove(os.path.join(repo, "new_variant.py"))  # the count is now 0, the tree's stamp still says 1
        assert ts.main([ts.WORKTREE, "--root", root, "--repo", repo]) == 0
        out = capsys.readouterr().out
        assert "(reused)" in out and "untracked_left_out: 1" in out


def test_the_diff_survives_a_users_diff_prefix_config():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        git(repo, "config", "diff.noprefix", "true")
        git(repo, "config", "diff.mnemonicPrefix", "true")
        with open(os.path.join(repo, "a.txt"), "w", newline="\n") as f:
            f.write("alpha\nedited\n")
        tree, stamp, _r, _l = ts.build(repo, ts.WORKTREE, root)
        assert stamp["dirty"] is True
        assert open(os.path.join(tree, "a.txt")).read() == "alpha\nedited\n"


def test_a_worktree_with_no_edits_is_the_clean_commits_tree():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        sha = make_repo(repo)
        tree, stamp, _r, _l = ts.build(repo, ts.WORKTREE, root)
        assert tree == os.path.join(root, sha) and stamp["dirty"] is False


def test_a_second_call_reuses_the_tree():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        sha = make_repo(repo)
        tree, first, reused1, _l = ts.build(repo, sha, root)
        marker = os.path.join(tree, "kept.txt")
        open(marker, "w").write("x")
        time.sleep(1.1)
        tree2, second, reused2, _l = ts.build(repo, "HEAD", root)
        assert tree2 == tree and not reused1 and reused2
        assert second["made_at"] == first["made_at"] and os.path.exists(marker)


def test_a_failed_build_leaves_no_tree(monkeypatch):
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        sha = make_repo(repo)

        def boom(*_a):
            raise ts.SnapshotError("apply failed")
        with open(os.path.join(repo, "a.txt"), "w") as f:
            f.write("changed\n")
        monkeypatch.setattr(ts, "apply_diff", boom)
        try:
            ts.build(repo, ts.WORKTREE, root)
            assert False
        except ts.SnapshotError:
            pass
        assert os.listdir(root) == [] and sha


def test_the_launch_line_names_both_roots_of_the_main_tree(capsys):
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        sha = make_repo(repo)
        assert ts.main([sha, "--root", root, "--repo", repo]) == 0
        out = capsys.readouterr().out
        norm = lambda t: t.replace("\\", "/").lower()
        main_tree = norm(ts.main_tree_of(repo))
        bash = norm([ln for ln in out.splitlines() if ln.startswith("bash: ")][0])
        assert "pzt_fixtures=%s/testing/fixtures" % main_tree in bash
        assert "pzt_runs=%s/testing/runs" % main_tree in bash
        assert norm(os.path.join(root, sha, "testing", "agent", "drivers", "x_trial.py")) in bash
        ps = [ln for ln in out.splitlines() if ln.startswith("powershell: ")][0]
        assert "$env:PZT_FIXTURES=" in ps and "$env:PZT_RUNS=" in ps
        assert "(made)" in out
        assert ts.main([sha, "--root", root, "--repo", repo]) == 0
        assert "(reused)" in capsys.readouterr().out


def test_the_main_tree_of_a_linked_worktree_is_the_main_checkout():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as other:
        make_repo(repo)
        wt = os.path.join(other, "wt")
        git(repo, "worktree", "add", "-q", "-b", "side", wt)
        assert os.path.normcase(ts.main_tree_of(wt)) == os.path.normcase(ts.main_tree_of(repo))
        assert os.path.normcase(ts.toplevel(wt)) != os.path.normcase(ts.main_tree_of(wt))


def test_the_default_root_follows_the_environment():
    assert ts.default_root({"PZT_SCRATCH": "S", "LOCALAPPDATA": "L"}) == os.path.join("S", "trials")
    assert ts.default_root({"LOCALAPPDATA": "L"}) == os.path.join("L", "pz-trials")


def test_an_unknown_commit_is_an_error_not_a_trace(capsys):
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        assert ts.main(["no-such-ref", "--root", root, "--repo", repo]) == 1
        assert "trial_snapshot:" in capsys.readouterr().err
        assert os.listdir(root) == []


def _build_expecting_oserror(repo, root):
    try:
        ts.build(repo, "HEAD", root)
    except OSError:
        return True
    return False


def test_an_extraction_failure_on_a_large_archive_raises_and_never_hangs(monkeypatch):
    # the archiver blocks on a full pipe when nothing reads it: the failure path stops it before it reads its stderr
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        with open(os.path.join(repo, "big.bin"), "wb") as f:
            f.write(os.urandom(4 << 20))
        git(repo, "add", "big.bin")
        git(repo, "commit", "-q", "-m", "big")

        def fail(*_a):
            raise OSError("disk says no")
        monkeypatch.setattr(ts, "_extract", fail)
        done = []
        t = threading.Thread(target=lambda: done.append(_build_expecting_oserror(repo, root)), daemon=True)
        t.start()
        t.join(30)
        assert done == [True], "the build hung or raised something else"
        assert os.listdir(root) == []


def test_a_large_archive_extracts_whole_and_the_archiver_exits_clean():
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        blob = os.urandom(5 << 20)
        with open(os.path.join(repo, "big.bin"), "wb") as f:
            f.write(blob)
        git(repo, "add", "big.bin")
        git(repo, "commit", "-q", "-m", "big")
        tree, _stamp, _r, _l = ts.build(repo, "HEAD", root)
        assert open(os.path.join(tree, "big.bin"), "rb").read() == blob


def _ext(path):
    """The test's own extended-length form, so the check does not lean on the tool's helper."""
    path = os.path.abspath(path)
    return "\\\\?\\" + path if os.name == "nt" else path


def test_a_root_deeper_than_the_windows_path_limit_still_extracts():
    base = tempfile.mkdtemp()
    try:
        with tempfile.TemporaryDirectory() as repo:
            make_repo(repo)
            deep = os.path.join(base, *["d" * 40] * 6)  # past 260 characters once the tree's own paths are added
            os.makedirs(_ext(deep))
            tree, stamp, _r, _l = ts.build(repo, "HEAD", deep)
            assert os.path.isfile(_ext(os.path.join(tree, "sub", "b.txt")))
            assert os.path.isfile(_ext(os.path.join(tree, "testing", "agent", "drivers", "x_trial.py")))
            assert stamp["dirty"] is False
    finally:
        shutil.rmtree(_ext(base), ignore_errors=True)


FAKE_ARCHIVER = """
import io, sys, tarfile
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w") as tf:
    data = b"hello\\n"
    info = tarfile.TarInfo("a.txt")
    info.size = len(data)
    tf.addfile(info, io.BytesIO(data))
out = sys.stdout.buffer
out.write(buf.getvalue())
for _ in range(8):   # a zero tail past the pipe buffer, which the tar reader stops short of
    out.write(bytes(1 << 20))
out.flush()
"""


def test_a_zero_tail_after_the_archive_is_drained_so_the_archiver_exits_clean(monkeypatch):
    # fails without the drain: the unread tail is a broken pipe for the archiver, whose non-zero exit is an error
    monkeypatch.setattr(ts, "archive_command", lambda repo, sha: [sys.executable, "-c", FAKE_ARCHIVER])
    with tempfile.TemporaryDirectory() as root:
        dest = os.path.join(root, "t")
        ts.extract_archive(".", "ignored", dest)
        assert open(os.path.join(dest, "a.txt")).read() == "hello\n"
