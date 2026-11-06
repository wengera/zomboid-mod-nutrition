#!/usr/bin/env python3
"""A trial's tree: a commit (or the working tree with its uncommitted diff) extracted outside the repository.

    python tools/trial_snapshot.py <commit-ish | WORKTREE> [--root <dir>] [--repo <dir>] [--main-tree <dir>]

A trial (Plan 31) boots from this tree, never from the live checkout, so the checkout may change while a session runs:
everything the session loads resolves from `__file__` inside the tree. The tool

  * resolves the commit-ish to a full sha (`WORKTREE` is HEAD's sha plus the tracked diff of `git diff HEAD --binary`
    applied on top; the tree's name is `<sha>-dirty-<diff sha256, 12 hex>`),
  * extracts `git archive <sha>` into `<root>/<name>/` (the archive carries no `.git`; the tool only reads the
    repository and never sets a GIT_* variable: the git calls run under a scrubbed environment),
  * reuses a tree already present (one tree per name; the stamp's `made_at` is left as it was),
  * writes `TRIAL_STAMP.json` {"commit", "dirty", "diff_sha256", "made_at"} at the tree's root (a dirty tree also
    holds the diff as `TRIAL_DIFF.patch`), and
  * prints the launch line, in the Bash and the PowerShell form, with `PZT_FIXTURES` and `PZT_RUNS` pointing at the
    main tree's `testing/fixtures` and `testing/runs` (a bare archive has no fixture caches and a run's folder belongs
    in the main tree's runs).

Untracked files are not part of a dirty tree (a new file in a variant is committed, or reached through a branch
head): the tool says how many it left out.

The root is `--root`, else `$PZT_SCRATCH/trials`, else `%LOCALAPPDATA%/pz-trials`, else `~/.pz-trials`.
The main tree is `--main-tree`, else the parent of the repository's common git dir (a linked worktree's main
checkout; the checkout itself otherwise).
"""
import argparse
import datetime
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STAMP = "TRIAL_STAMP.json"
DIFF = "TRIAL_DIFF.patch"
WORKTREE = "WORKTREE"
DRIVER = "testing/agent/drivers/x_trial.py"
# the variables that aim git at another repository (the same list as tools/tests/gitenv.py)
AIMING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
          "GIT_COMMON_DIR")


class SnapshotError(Exception):
    pass


def long(path):
    """`path` in Windows' extended-length form, which lifts the 260-character limit a deep root meets (no effect
    elsewhere); the tree is made through it, and a deep root still needs the same form from whatever reads the tree."""
    path = os.path.abspath(path)
    return "\\\\?\\" + path if os.name == "nt" and not path.startswith("\\\\") else path


def _env():
    return {k: v for k, v in os.environ.items() if k not in AIMING}


def _git(repo, *args, stdin=None):
    """git's stdout bytes in `repo`; a non-zero exit raises with its stderr."""
    r = subprocess.run(["git", "-C", repo, *args], input=stdin, capture_output=True, env=_env())
    if r.returncode:
        raise SnapshotError("git %s: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout


def resolve(repo, ref):
    """The full sha of a commit-ish."""
    return _git(repo, "rev-parse", "--verify", "-q", ref + "^{commit}").decode().strip()


def toplevel(repo):
    return os.path.normpath(_git(repo, "rev-parse", "--show-toplevel").decode().strip())


def main_tree_of(repo):
    """The main checkout: the parent of the common git dir (the repository's own top level when not a worktree)."""
    common = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()
    return os.path.normpath(os.path.dirname(common))


def default_root(environ=None):
    environ = os.environ if environ is None else environ
    if environ.get("PZT_SCRATCH"):
        return os.path.join(environ["PZT_SCRATCH"], "trials")
    if environ.get("LOCALAPPDATA"):
        return os.path.join(environ["LOCALAPPDATA"], "pz-trials")
    return os.path.join(os.path.expanduser("~"), ".pz-trials")


def tracked_diff(repo):
    """`git diff HEAD --binary` of the working tree (the tracked files' uncommitted edits), as bytes."""
    return _git(toplevel(repo), "diff", "HEAD", "--binary")


def untracked_count(repo):
    out = _git(toplevel(repo), "ls-files", "-o", "--exclude-standard", "-z")
    return len([p for p in out.split(b"\0") if p])


def _extract(tf, dest):
    """The stream's directories and regular files under `dest` (an archive of git's own holds nothing else a trial
    reads). The member's path is joined with os.sep here, since tarfile's own join mixes slashes into an
    extended-length path, which Windows then refuses."""
    for m in tf:
        parts = [x for x in m.name.split("/") if x not in ("", ".")]
        if ".." in parts or os.path.isabs(m.name):
            raise SnapshotError("archive member outside the tree: %s" % m.name)
        target = os.path.join(dest, *parts) if parts else dest
        if m.isdir():
            os.makedirs(target, exist_ok=True)
        elif m.isreg():
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as out:
                shutil.copyfileobj(tf.extractfile(m), out, 1 << 20)


def extract_archive(repo, sha, dest):
    """`git archive <sha>` read as a tar stream into `dest`, no tar binary and no .git."""
    dest = long(dest)
    os.makedirs(dest)
    p = subprocess.Popen(["git", "-C", repo, "archive", "--format=tar", sha], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=_env())
    try:
        with tarfile.open(fileobj=p.stdout, mode="r|") as tf:
            _extract(tf, dest)
        while p.stdout.read(1 << 20):  # the archive's zero padding, which tarfile stops short of: an unread pipe
            pass                       # closed on git is a broken pipe and a non-zero exit
    except BaseException:
        p.kill()  # git blocks writing a full pipe, and reading its stderr to the end would wait on it for good
        raise
    finally:
        p.stdout.close()
        err = p.stderr.read().decode("utf-8", "replace")
        p.stderr.close()
        rc = p.wait()
    if rc:
        raise SnapshotError("git archive %s: %s" % (sha, err.strip()))


def apply_diff(dest, diff):
    """The diff applied to the extracted tree (no repository is needed for `git apply`, none is touched)."""
    r = subprocess.run(["git", "apply", "--whitespace=nowarn", "-p1", "-"], cwd=dest, input=diff,
                       capture_output=True, env=_env())
    if r.returncode:
        raise SnapshotError("git apply: %s" % r.stderr.decode("utf-8", "replace").strip())


def build(repo, ref, root):
    """(tree dir, stamp dict, reused flag, untracked count) for `ref` under `root`."""
    top = toplevel(repo)
    dirty = ref == WORKTREE
    sha = resolve(top, "HEAD" if dirty else ref)
    diff = tracked_diff(top) if dirty else b""
    dirty = bool(diff)
    digest = hashlib.sha256(diff).hexdigest() if dirty else None
    name = "%s-dirty-%s" % (sha, digest[:12]) if dirty else sha
    tree = os.path.join(root, name)
    left_out = untracked_count(top) if ref == WORKTREE else 0
    stamp_path = os.path.join(tree, STAMP)
    if os.path.isfile(long(stamp_path)):
        with open(long(stamp_path), encoding="utf-8") as f:
            return tree, json.load(f), True, left_out
    os.makedirs(long(root), exist_ok=True)
    part = tree + ".partial"
    if os.path.exists(long(part)):
        shutil.rmtree(long(part))
    try:
        extract_archive(top, sha, part)
        if dirty:
            apply_diff(part, diff)
            with open(long(os.path.join(part, DIFF)), "wb") as f:
                f.write(diff)
        stamp = {"commit": sha, "dirty": dirty, "diff_sha256": digest,
                 "made_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
        with open(long(os.path.join(part, STAMP)), "w", encoding="utf-8", newline="\n") as f:
            json.dump(stamp, f, indent=2)
            f.write("\n")
        if os.path.exists(long(tree)):  # a half-made tree with no stamp
            shutil.rmtree(long(tree))
        os.replace(long(part), long(tree))
    except BaseException:
        shutil.rmtree(long(part), ignore_errors=True)
        raise
    return tree, stamp, False, left_out


def launch_lines(tree, main_tree):
    """(bash line, PowerShell line): the driver run from the tree with both roots in the main tree."""
    fixtures = os.path.join(main_tree, "testing", "fixtures")
    runs = os.path.join(main_tree, "testing", "runs")
    driver = os.path.join(tree, *DRIVER.split("/"))
    fwd = lambda p: p.replace("\\", "/")
    sh = "PZT_FIXTURES=%s PZT_RUNS=%s python %s ..." % (shlex.quote(fwd(fixtures)), shlex.quote(fwd(runs)),
                                                         shlex.quote(fwd(driver)))
    q = lambda p: "'%s'" % p.replace("'", "''")
    ps = "$env:PZT_FIXTURES=%s; $env:PZT_RUNS=%s; python %s ..." % (q(fixtures), q(runs), q(driver))
    return sh, ps


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ref", help="a commit-ish, or WORKTREE for the working tree with its uncommitted diff")
    ap.add_argument("--root", default=None, help="where trees live (default: see the module docstring)")
    ap.add_argument("--repo", default=REPO, help="the repository to snapshot (default: this tool's own)")
    ap.add_argument("--main-tree", default=None, help="the tree whose testing/fixtures and testing/runs the launch "
                                                      "line names (default: the repository's main checkout)")
    a = ap.parse_args(argv)
    try:
        root = os.path.abspath(a.root or default_root())
        tree, stamp, reused, left_out = build(a.repo, a.ref, root)
        main_tree = os.path.abspath(a.main_tree) if a.main_tree else main_tree_of(a.repo)
    except SnapshotError as e:
        print("trial_snapshot: %s" % e, file=sys.stderr)
        return 1
    sh, ps = launch_lines(tree, main_tree)
    print("tree: %s (%s)" % (tree, "reused" if reused else "made"))
    print("stamp: commit %s dirty %s diff_sha256 %s made_at %s" % (stamp["commit"], str(stamp["dirty"]).lower(),
                                                                   stamp["diff_sha256"], stamp["made_at"]))
    if left_out:
        print("note: %d untracked file(s) are not in the tree (commit them to take them)" % left_out)
    print("bash: %s" % sh)
    print("powershell: %s" % ps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
