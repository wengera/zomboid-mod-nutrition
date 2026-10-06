"""File-based command bus + JSON result collection, shared by the server and client drivers.

Both live in <cachedir>/Lua/ (what the harness reaches through getFileReader/getFileWriter):
  pzt-cmd.txt      {seq, cmd, args}   written by us, atomically (tmp + rename)
  pzt-ack.txt      {seq, cmd, result} written by the harness; "running" while executing
  pzt-results/*.json                  one complete JSON object per result; parseable = ready
"""
import glob
import json
import os
import shutil
import time

RENAME_RETRIES = 8          # ~1.2 s of retrying the command-file swap; see CommandBus.send
RENAME_RETRY_WAIT = 0.15


def read_kv(path):
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def parse_ack(result):
    """'ok:<value>' / 'err:<msg>' -> (ok, value); JSON values are decoded."""
    if result is None:
        return False, None
    ok = result.startswith("ok:")
    body = result[3:] if ok else (result[4:] if result.startswith("err:") else result)
    if body[:1] in ("{", "["):
        try:
            return ok, json.loads(body)
        except ValueError:
            pass
    return ok, body


class CommandBus:
    def __init__(self, lua_dir, alive=None):
        self.lua_dir = lua_dir
        self.alive = alive or (lambda: True)
        self.seq = 0

    @property
    def cmd_path(self):
        return os.path.join(self.lua_dir, "pzt-cmd.txt")

    @property
    def ack_path(self):
        return os.path.join(self.lua_dir, "pzt-ack.txt")

    @property
    def results_dir(self):
        return os.path.join(self.lua_dir, "pzt-results")

    def reset(self):
        """Start both sides at seq 0 and drop stale results (restored fixtures carry Lua/)."""
        os.makedirs(self.lua_dir, exist_ok=True)
        for p in (self.cmd_path, self.ack_path):
            if os.path.exists(p):
                os.remove(p)
        if os.path.isdir(self.results_dir):
            shutil.rmtree(self.results_dir)
        self.seq = 0

    def send(self, cmd, args="", wait=True, timeout=30):
        self.seq += 1
        tmp = self.cmd_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(f"seq={self.seq}\ncmd={cmd}\nargs={args}\n")
        # os.replace onto a file the game currently has open raises PermissionError
        # (WinError 5) on Windows -- there is no atomic-replace-over-an-open-handle there.
        # The harness polls this file ~3x a second on each side, so the collision window is
        # real: it cost one row of exp03-20260910-045523. It is a RANDOM collision, not a
        # first-command problem -- r2_asleep had already run `player.sleep true`, all eight
        # `prime()` writes and `settimespeed 30` (27.6 s, timeline `row_start` 960.7 ->
        # `row_error` 988.3) and died on the first `stats.get` of its rate window. Retrying is
        # the whole fix -- the handle is released within a frame -- and a raise on the last
        # attempt keeps the old behaviour for a path that is genuinely unwritable.
        for attempt in range(RENAME_RETRIES):
            try:
                os.replace(tmp, self.cmd_path)
                break
            except PermissionError:
                if attempt == RENAME_RETRIES - 1:
                    raise
                time.sleep(RENAME_RETRY_WAIT)
        if not wait:
            return None
        end = time.time() + timeout
        while time.time() < end:
            ack = read_kv(self.ack_path)
            if ack.get("seq") == str(self.seq) and ack.get("result", "running") != "running":
                return ack["result"]
            if not self.alive():
                raise RuntimeError(f"process exited while waiting for ack of '{cmd}'")
            time.sleep(0.25)
        raise TimeoutError(f"no ack for #{self.seq} {cmd} within {timeout}s")

    def results(self):
        out = {}
        for p in glob.glob(os.path.join(self.results_dir, "*.json")):
            try:
                with open(p, encoding="utf-8") as fh:
                    d = json.load(fh)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and d.get("complete"):
                out[os.path.splitext(os.path.basename(p))[0]] = d
        return out

    def wait_result(self, name, timeout=30, after=0.0):
        """A complete JSON result file modified at/after `after` (wall time)."""
        p = os.path.join(self.results_dir, name + ".json")
        end = time.time() + timeout
        while time.time() < end:
            if os.path.exists(p) and os.path.getmtime(p) >= after:
                try:
                    with open(p, encoding="utf-8") as fh:
                        d = json.load(fh)
                except (OSError, ValueError):
                    d = None
                if isinstance(d, dict) and d.get("complete"):
                    return d
            if not self.alive():
                raise RuntimeError(f"process exited while waiting for result '{name}'")
            time.sleep(0.25)
        raise TimeoutError(f"no result '{name}' within {timeout}s")


# ---- the drivers' side (Plan 8 Task 1) ------------------------------------------------------

class UnknownSide(KeyError):
    """A side naming a client the run did not attach. A KeyError, so a caller that expects a
    lookup miss catches it; printed as the sentence, not KeyError's quoted repr."""

    def __str__(self):
        return str(self.args[0]) if self.args else ""


def _by_user(clients):
    """`{user: node}` from either shape the harness holds: the ordered dict
    `session.attach_clients` returns, or the list the run path keeps for its teardown."""
    if not clients:
        return {}
    if isinstance(clients, dict):
        return dict(clients)
    return {c.username: c for c in clients}


def resolve_side(side, server, clients):
    """The node a driver's `side` names: `"server"`, `"client"`, `"client:<user>"`, or a node
    passed through as it is.

    The bare `"client"` is the `admin` client (the first attached client when admin is not
    attached), so every driver and every `[[verify]]` row written before a run had two clients
    reads exactly as it did (Plan 8 ruling 3). `"client:<user>"` is that user's client; a user
    the run did not attach raises `UnknownSide` (a KeyError) naming the attached users. A node
    (anything with `send`) is returned unchanged: the drivers before Plan 8 pass the server or
    client object itself. Anything else is a ValueError, never a silent server.
    """
    from .paths import ADMIN_USER          # local: an import line up top would move line 119 (#1761)
    if not isinstance(side, str):
        if hasattr(side, "send"):
            return side
        raise ValueError(f"side {side!r}: expected server, client, client:<user> or a node")
    if side == "server":
        return server
    nodes = _by_user(clients)
    if side == "client":
        if not nodes:
            raise UnknownSide("side 'client': no client attached")
        return nodes.get(ADMIN_USER) or next(iter(nodes.values()))
    if side.startswith("client:") and side[len("client:"):]:
        user = side[len("client:"):]
        if user in nodes:
            return nodes[user]
        raise UnknownSide(f"side '{side}': no client '{user}' attached "
                          f"(attached: {', '.join(nodes) or 'none'})")
    raise ValueError(f"side '{side}': expected server, client or client:<user>")
