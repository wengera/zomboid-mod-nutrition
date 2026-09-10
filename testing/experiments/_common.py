"""Helpers shared by every experiment script under this directory (slices 01-05 and on).

An experiment is not a test: a wedged command or an unwritable path must degrade the
evidence, never abort the run or -- worse -- leave a PZ process alive. All three helpers
here are written to that rule and none of them raises.
"""
import json
import os

from pzt.bus import parse_ack


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
