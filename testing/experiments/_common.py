"""Helpers shared by every experiment script under this directory (slices 01-05 and on).

An experiment is not a test: a wedged command or an unwritable path must degrade the
evidence, never abort the run or -- worse -- leave a PZ process alive. Every helper here is
written to that rule and none of them raises.

Two groups. `ask` / `save` / `hard_kill` drive a live session. `load_json` / `git_say` /
`git_dirty` / `doctor` / `num` are the **provenance and reading** helpers slices 05 and 06
had grown a copy of in each driver (`s05_food_scan.py`, `s05b_drink_probe.py`,
`s06_recipes.py`, `s06b_use_probe.py`); they were promoted here verbatim, by the final fix
wave of slice 06, because four identical definitions is four places for one of them to
drift. Only the copies that were already byte-equal moved: `s05_food_scan.py` keeps its own
`git_short` (a different answer on an empty reply) and its own retrying `load_dataset`,
because those are not this `git_say` and not this `load_json`.
"""
import hashlib
import json
import os
import subprocess
import sys

from pzt.bus import parse_ack

# The repo root: `<repo>/testing/experiments/_common.py` -> `<repo>`. Every driver computes
# the same path for itself; this is the copy the helpers below use.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ask(side, cmd, args="", timeout=20):
    """One bus command. A dead or wedged side is recorded, not raised: the remaining
    probes are still worth collecting.

    `OSError` is caught for the same reason: `CommandBus.send` writes the command file with
    `os.replace`, which on Windows raises `PermissionError` (a subclass of `OSError`) when the
    game happens to hold the file open. That is a harness collision, not a finding, and it
    cost a whole row of exp03-20260910-045523 by escaping this helper -- `bus.py` now retries
    the rename, and if every retry loses, the sample is recorded as an error like any other
    wedged read instead of aborting the row around it."""
    try:
        return parse_ack(side.send(cmd, args, timeout=timeout))[1]
    except (RuntimeError, TimeoutError, OSError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


def save(path, out, tl, server):
    """Snapshot the timeline and the server's error list into `out` and write it.

    Called twice: once before teardown (so a shutdown that goes wrong still leaves
    evidence on disk) and once after it (the committed artifact has to show the
    `client_quit` / `server_stopped` marks and any shutdown-phase server errors, which a
    pre-teardown snapshot misses). Writes via a temp file so a half-written second pass
    cannot corrupt a good first one, and never raises: this runs on the teardown path and
    a failed write must not skip the kills that follow it."""
    try:
        out["timeline"] = list(tl.items)
        out["server_errors"] = server.errors[:20]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
        print(f"\nwrote {path}")
    except Exception as e:                       # noqa: BLE001 - see docstring
        print(f"could not write {path}: {type(e).__name__}: {e}")


def hard_kill(server, clients):
    """taskkill everything, whatever else went wrong. Never raises, and one failure does
    not skip the rest: no PZ process may outlive this script."""
    for proc in list(clients) + [server]:
        try:
            proc.kill()
        except Exception as e:                   # noqa: BLE001 - best effort by design
            print(f"kill failed: {type(e).__name__}: {e}")


def load_json(path):
    """`(data, error, sha256)` -- one read, hashed and decoded, so the digest is of the same
    bytes that were parsed. Why the digest and not just the commit: `git log -1` names the
    newest commit that TOUCHED the path, which is a different question from where these bytes
    came from (see `git_say` / `git_dirty`)."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        return json.loads(raw.decode("utf-8")), None, hashlib.sha256(raw).hexdigest()
    except (ValueError, OSError, UnicodeDecodeError) as e:
        return None, f"{type(e).__name__}: {e}", None


def git_say(*args):
    """A short `git` answer, or the error string. Provenance only -- never fatal."""
    try:
        p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                           timeout=30)
        if p.returncode != 0:
            return f"git rc={p.returncode}"
        return (p.stdout or "").strip()
    except Exception as e:                       # noqa: BLE001 - provenance, never fatal
        return f"{type(e).__name__}: {e}"


def git_dirty(rel_path):
    """`git status --porcelain -- <path>` non-empty: the working tree differs from the index or
    HEAD, so the commit `git log -1` names is NOT where the bytes came from.

    Returns `(dirty, note)`. `dirty` is `True` / `False` when git answered and **`None`** when it
    could not be asked -- unknown is a third state, and it must not be a truthy error string in
    the flag's own slot, where `if dirty:` would read it as "dirty" and a JSON consumer would
    have to type-check before believing it. The reason travels beside it as
    `meta.dataset_dirty_note`. Provenance, never fatal."""
    try:
        p = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--", rel_path],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return None, f"git status rc={p.returncode}"
        return bool((p.stdout or "").strip()), None
    except Exception as e:                       # noqa: BLE001 - provenance, never fatal
        return None, f"{type(e).__name__}: {e}"


def doctor():
    """`pzt doctor` from inside the run: `(clean, text)`. The brief's precondition, recorded
    rather than remembered -- a run booted onto a dirty machine is not evidence."""
    try:
        p = subprocess.run([sys.executable, os.path.join(REPO, "testing", "pzt"), "doctor"],
                           capture_output=True, text=True, timeout=300)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:                       # noqa: BLE001 - reported, not raised
        return False, f"{type(e).__name__}: {e}"


def num(v):
    """A number, or None for anything else (a missing key, an `{'error': ...}` reply).
    Booleans are excluded: `isinstance(True, int)`."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
