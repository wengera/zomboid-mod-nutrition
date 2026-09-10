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
        # real: it cost one row of exp03-20260910-045523 (r2_asleep aborted on the FIRST
        # command it sent). Retrying is the whole fix -- the handle is released within a
        # frame -- and a raise on the last attempt keeps the old behaviour for a path that is
        # genuinely unwritable.
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
