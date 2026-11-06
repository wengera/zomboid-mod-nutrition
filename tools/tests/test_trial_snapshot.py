"""tools/trial_snapshot.py: a commit's tree, the working tree with its diff, the stamp, the reuse and the launch line.
Every git call runs under gitenv.scrubbed_env in a repository the test makes."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
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
        # the commit's own clean tree is not touched by it
        assert git(repo, "show", "HEAD:a.txt") == "alpha"


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
        assert os.path.normcase(ts.main_tree_of(wt)) == os.path.normcase(os.path.realpath(repo)) or \
            os.path.normcase(ts.main_tree_of(wt)) == os.path.normcase(os.path.abspath(repo))


def test_the_default_root_follows_the_environment():
    assert ts.default_root({"PZT_SCRATCH": "S", "LOCALAPPDATA": "L"}) == os.path.join("S", "trials")
    assert ts.default_root({"LOCALAPPDATA": "L"}) == os.path.join("L", "pz-trials")


def test_an_unknown_commit_is_an_error_not_a_trace(capsys):
    with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as root:
        make_repo(repo)
        assert ts.main(["no-such-ref", "--root", root, "--repo", repo]) == 1
        assert "trial_snapshot:" in capsys.readouterr().err
        assert os.listdir(root) == []
