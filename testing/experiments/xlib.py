"""Shared session helpers for the live experiment drivers (Plan 12 Task 4).

Every driver from x391h to x406 copied the same plumbing -- the bus step with its ping and dead-bus
handling, the phase runner, the wall budget, the deployed-marker and staged-manifest gates, the RCON
food spawn, the log grep, the grade recorder and the abort/teardown/copy skeleton -- and a defect in
one copy reached every copy (`tl.mark(phase=...)`, closed at the source in testing/pzt/session.py at
52a7de93). A new driver imports this module instead of copying the helpers.

The module holds no state of its own. One `Xs` (an experiment session) holds a driver's state --
its output dict, bus flag, timeline, server, clients and constants -- and every helper is a method on
it or a function taking what it needs. A frozen driver (one that has run) never imports this module.

Reply shapes the helpers read are the harness's own: `ping` answers "pong"; `item.get` answers a dict
with `id` (PZTestKit_Server.lua, `@reply` of item.get) or a string; `eat.action` answers
{queued, spawned, itemId, ...} where `spawned` is "found" for an item the player held
(PZTestKit_Client.lua, `@reply` of eat.action); `time.snapshot` answers {worldAge, hour, minutes,
mult, trueMult, wall} (PZTestKit_Core.lua).
"""
import ctypes
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask as _ask                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRV = "server"
STALL_RX = re.compile(r"^(?:TimeoutError|RuntimeError)\b")


class BusDead(Exception):
    """The server bus stopped answering; the phase ends and every later server step is skipped."""


class Budget(Exception):
    """The wall budget passed, or admin parked in the debugger, inside a phase's poll."""


class StopEats(Exception):
    """An eat.action reply's spawned was not "found": the session's eats stop (ruling T2-11)."""


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class _MemStat(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_gb():
    """Host free physical memory in GB, or None when it cannot be read."""
    try:
        m = _MemStat()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round(m.ullAvailPhys / float(2 ** 30), 2)
    except Exception:                          # noqa: BLE001 - a missing reading is recorded as None
        return None


def memory_ok(free, min_free_gb):
    """The boot gate: a missing reading or one under the floor refuses the session (CLAUDE.md s5)."""
    return free is not None and free >= min_free_gb


def stalled(v):
    return isinstance(v, dict) and isinstance(v.get("error"), str) and STALL_RX.match(v["error"]) is not None


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def grep_noecho(log, rx, limit, echo_rx, probe_rx):
    """Lines of `log` matching `rx`, minus the harness echo and the driver's own probe names
    (the echo of a client-side probe's name would read as a hit); returns (hits, skipped)."""
    hits_, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if echo_rx.search(line) or probe_rx.search(line):
                    skipped += 1
                    continue
                hits_.append(line.strip()[:600])
                if len(hits_) >= limit:
                    break
    except OSError:
        pass
    return hits_, skipped


def deployed_marker_check(run_dir, files, markers):
    """Every deployed copy of each harness file under run_dir holds its markers (each file read once).
    `files` is an iterable of file names; `markers` maps a file name to its marker strings.
    Returns (per-copy map, ok); ok needs a copy of every file and every copy true."""
    dm = {}
    for fname in files:
        for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", "PZTestKit", "**", fname), recursive=True)):
            rel = os.path.relpath(cand, run_dir).replace(os.sep, "/")
            try:
                with open(cand, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                dm[rel] = all(m in text for m in markers[fname])
            except OSError as e:
                dm[rel] = f"{type(e).__name__}: {e}"
    have = {f: any(k.endswith(f) for k in dm) for f in files}
    return dm, bool(have) and all(have.values()) and all(v is True for v in dm.values())


def manifest_gate(release_pack, repo, mod_dir, stage_root, stage_mod, manifest_name, git_say, git_dirty):
    """The staged copy against release_pack's manifest of mod_dir at HEAD (the tree clean)."""
    M = {"head": git_say("rev-parse", "HEAD"), "head_short": git_say("rev-parse", "--short", "HEAD"),
         "mod_commit": git_say("log", "-1", "--format=%h", "--", mod_dir), "mod_dirty": git_dirty(mod_dir)[0],
         "staged_manifest": f"{stage_root}/{manifest_name}", "staged_mod": stage_mod}
    try:
        mpath = os.path.join(repo, stage_root, manifest_name)
        M["staged_manifest_sha256"] = sha256_file(mpath)
        with open(mpath, encoding="utf-8") as fh:
            staged = json.load(fh)
        head = release_pack.manifest(os.path.join(repo, mod_dir))
        booted = release_pack.manifest(os.path.join(repo, stage_mod))
        M["files"] = len(head)
        M["staged_equals_head"] = staged == head
        M["staged_tree_equals_head"] = booted == head
        if staged != head:
            M["diff_staged_vs_head"] = release_pack.diff(staged, head)
        if booted != head:
            M["diff_tree_vs_head"] = release_pack.diff(booted, head)
    except (OSError, ValueError) as e:
        M["error"] = f"{type(e).__name__}: {e}"
    M["ok"] = (M.get("staged_equals_head") is True and M.get("staged_tree_equals_head") is True
               and M["mod_dirty"] is False and "error" not in M)
    return M


def grade_verdict(verdict, samples):
    """A grade with zero samples is unmeasured, never as_predicted: a vacuous pass proves nothing."""
    if verdict == "as_predicted" and not samples:
        return "unmeasured"
    return verdict


class Xs:
    """One driver's session state and the helpers over it.

    `out` is the artifact dict (it must hold "steps", "notes", "phase_walls", "phase_errors",
    "verdicts" and "world_changes": {"left_in_place": []}); `node(side)` resolves a side to its bus
    node; `ask` is the bus command function (default _common.ask); `clock` and `sleep` are injectable.
    `tl` (a pzt.session.Timeline) and `server` (for .rcon and .bus.wait_result) may be None before boot.
    """

    def __init__(self, out, node, tl=None, server=None, clients=None, ask=_ask, budget_s=840.0,
                 ping_timeout_s=5, spawn_wait_s=2.5, predictions=None, clock=time.time, sleep=time.sleep,
                 user="admin"):
        self.out = out
        self.node = node
        self.tl = tl
        self.server = server
        self.clients = clients if clients is not None else {}
        self.ask = ask
        self.budget_s = budget_s
        self.ping_timeout_s = ping_timeout_s
        self.spawn_wait_s = spawn_wait_s
        self.pred = predictions or {}
        self.clock = clock
        self.sleep = sleep
        self.user = user
        self.t0 = clock()
        self.bus_dead = None
        self.cur_phase = "pre"
        self.path = None
        self.copied = []

    # ---- clock, notes, persistence
    def wall(self):
        return round(self.clock() - self.t0, 3)

    def note(self, msg):
        self.out["notes"].append({"wall": self.wall(), "phase": self.cur_phase, "note": msg})

    def persist(self):
        if self.path is None:
            return
        try:
            self.out["timeline"] = list(self.tl.items) if self.tl is not None else []
            if self.server is not None:
                self.out["server_errors"] = self.server.errors[:30]
                self.out["server_error_count"] = len(self.server.errors)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.out, fh, indent=1, default=str)
            os.replace(tmp, self.path)
        except Exception as e:                 # noqa: BLE001 - never raise on the write path
            print(f"could not write {self.path}: {type(e).__name__}: {e}")

    def mem(self, tag):
        row = {"tag": tag, "wall": self.wall(), "free_gb": free_gb()}
        self.out.setdefault("memory", []).append(row)
        return row

    # ---- the bus: mark_dead, ping, step
    def mark_dead(self, tag):
        if not self.bus_dead:
            self.bus_dead = tag
            self.out["abort"] = f"server bus dead after {tag}"
            self.note(self.out["abort"])
            if self.tl is not None:
                self.tl.mark("error", detail=self.out["abort"][:200])

    def ping(self, tag):
        """True only when the server answers pong inside ping_timeout_s; no pong marks the bus dead."""
        if self.bus_dead:
            return False
        r = self.step(tag, SRV, "ping", timeout=self.ping_timeout_s, liveness=False)
        if r.get("ack") == "pong":
            return True
        self.mark_dead(tag)
        return False

    def step(self, name, side, cmd, args="", timeout=30, liveness=True, log=True):
        """One bus command as a recorded row. A server step on a dead bus is skipped; a stalled
        server step (timeout or runtime error) pings, and no pong marks the bus dead and raises BusDead."""
        t_before, e_before = self.wall(), self.clock()
        if side == SRV and self.bus_dead:
            row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": self.cur_phase,
                   "wall_before": t_before, "wall_after": t_before, "epoch_ms_before": int(e_before * 1000),
                   "epoch_ms_after": int(e_before * 1000), "took": 0.0, "skipped": True,
                   "ack": {"error": f"skipped: server bus dead after {self.bus_dead}"}}
            if log:
                self.out["steps"].append(row)
            return row
        try:
            v = self.ask(self.node(side), cmd, args, timeout=timeout)
        except Exception as e:                 # noqa: BLE001 - an unknown side is a recorded fault
            v = {"error": f"{type(e).__name__}: {e}"}
        t_after = self.wall()
        row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": self.cur_phase,
               "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
               "epoch_ms_after": int(self.clock() * 1000), "took": round(t_after - t_before, 3), "ack": v}
        if not isinstance(v, dict):
            row["ack_shape"] = type(v).__name__
        if log or stalled(v):
            self.out["steps"].append(row)
        if side == SRV and liveness and stalled(v):
            alive = self.ping(f"{name}_liveness")
            row["liveness_pong"] = alive
            if not alive:
                raise BusDead(self.out.get("abort") or f"server bus dead after {name}")
        return row

    @staticmethod
    def ack(r):
        return r["ack"] if isinstance(r.get("ack"), dict) else {}

    def keep(self, r):
        a = dict(self.ack(r))
        a["wall"] = r["wall_before"]
        a["wall_after"] = r["wall_after"]
        a["side"] = a.get("side", r["side"])
        if not isinstance(r.get("ack"), dict):
            a["raw"] = r.get("ack")
        return a

    # ---- the wall budget
    def parked(self):
        c = self.clients.get(self.user) if isinstance(self.clients, dict) else None
        return c is not None and "lua_error" in getattr(c, "seen", {})

    def check(self):
        """Every poll's guard: the wall budget and the debugger park."""
        if self.wall() > self.budget_s:
            raise Budget(f"wall {self.wall()} s past the budget {self.budget_s} s")
        if self.parked():
            raise Budget("admin parked in the debugger")

    # ---- phases and grades
    def grade(self, name, verdict, observed, falsifier, extra=None, samples=None):
        """Record a verdict. With `samples` given, zero samples turn as_predicted into unmeasured."""
        if samples is not None:
            verdict = grade_verdict(verdict, samples)
        row = {"phase": name, "predicted": self.pred.get(name), "falsifier": falsifier, "observed": observed,
               "verdict": verdict, "wall": self.wall()}
        if extra:
            row.update(extra)
        self.out["verdicts"][name] = row
        if self.tl is not None:
            self.tl.mark("verdict", name=name, verdict=verdict)
        return row

    def phase_dead(self, name):
        pw = self.out.get("phase_walls", {}).get(name)
        return bool(pw and pw.get("bus_dead"))

    def run_phase(self, name, fn):
        """Run one phase; its fault is recorded (failed_phase, never phase=) and the others still run."""
        self.cur_phase = name
        self.out["phase_walls"][name] = {"start": self.wall()}
        was_dead = self.bus_dead
        try:
            fn()
        except BusDead as e:
            self.out["phase_walls"][name]["bus_dead"] = str(e)
            self.note(f"phase {name} ended: {e}")
        except Budget as e:
            self.out["phase_walls"][name]["budget_stop"] = str(e)
            self.out["budget_stop"] = {"phase": name, "why": str(e), "wall": self.wall()}
            self.note(f"phase {name} stopped: {e}")
        except StopEats as e:
            self.out["phase_walls"][name]["stop_eats"] = str(e)
            self.note(f"phase {name} stopped: {e}")
        except Exception as e:                 # noqa: BLE001 - one phase's fault keeps the others
            self.out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}",
                                              "tb": traceback.format_exc()[-3000:]}
            if self.tl is not None:
                self.tl.mark("error", failed_phase=name, detail=str(e)[:200])
            self.note(f"phase {name} raised: {type(e).__name__}: {e}")
        if self.bus_dead and not was_dead and not self.out["phase_walls"][name].get("bus_dead"):
            self.out["phase_walls"][name]["bus_dead"] = f"server bus dead after {self.bus_dead}"
        self.out["phase_walls"][name]["end"] = self.wall()
        self.persist()

    # ---- RCON, spawn, eat
    def rcon(self, cmd, tag):
        t_before, e_before = self.wall(), self.clock()
        if self.bus_dead:
            row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": self.cur_phase,
                   "wall_before": t_before, "wall_after": t_before, "skipped": True,
                   "ack": {"ok": False, "reply": f"skipped: server bus dead after {self.bus_dead}"}}
            self.out["steps"].append(row)
            return dict(row["ack"], skipped=True)
        try:
            ok, rep = self.server.rcon(cmd)
        except Exception as e:                 # noqa: BLE001
            ok, rep = False, f"{type(e).__name__}: {e}"
        row = {"step": tag, "side": SRV, "cmd": "rcon", "args": cmd, "phase": self.cur_phase,
               "wall_before": t_before, "wall_after": self.wall(), "epoch_ms_before": int(e_before * 1000),
               "epoch_ms_after": int(self.clock() * 1000), "ack": {"ok": ok, "reply": str(rep)[:300]}}
        self.out["steps"].append(row)
        if self.tl is not None:
            self.tl.mark("rcon", cmd=cmd, ok=ok)
        return row["ack"]

    def item_id(self, full_type, tag):
        """The server copy of the user's first item of the type (item.get): its id and state, or no id."""
        a = self.keep(self.step(tag, SRV, "item.get", f"{self.user} {full_type}"))
        return {k: a.get(k) for k in ("id", "fullType", "hungChange", "hungerChange", "baseHunger", "calories",
                                      "uses", "age", "error", "raw", "wall")}

    def spawn(self, full_type, n, tag):
        """RCON additem confirmed by the server's item.get id (ruling T2-11); a leftover before the spawn
        voids it."""
        row = {"type": full_type, "n": n}
        row["before"] = self.item_id(full_type, tag + "_id0")
        row["additem"] = self.rcon(f'additem "{self.user}" "{full_type}" {int(n)}', tag + "_additem")
        self.sleep(self.spawn_wait_s)
        row["after"] = self.item_id(full_type, tag + "_id1")
        row["leftover_before"] = row["before"].get("id") is not None
        row["confirmed"] = row["after"].get("id") is not None and not row["leftover_before"]
        if row["confirmed"]:
            self.out["world_changes"]["left_in_place"].append(f"RCON additem {full_type} x{n}")
        else:
            self.note(f"spawn {full_type}: not confirmed "
                      f"({'a leftover before the spawn' if row['leftover_before'] else 'no id after'})")
        return row

    def spawned_stop(self, reply, tag):
        """Stop the session's eats at an eat.action reply whose spawned is not the string "found"
        (a "client" spawn trips the server NPE); records stop_reason and raises StopEats."""
        if reply.get("spawned") != "found":
            self.out["stop_reason"] = f"{tag}: eat.action spawned {reply.get('spawned')!r}, not 'found' (ruling T2-11)"
            raise StopEats(self.out["stop_reason"])

    def eat_queue(self, full_type, tag, admin="client:admin"):
        """foodtimer 0, then eat.action <type> 1 on the admin client; a `spawned` other than "found" stops the eats."""
        self.keep(self.step(tag + "_foodtimer", SRV, "foodtimer.set", f"{self.user} 0"))
        q = self.keep(self.step(tag + "_eat", admin, "eat.action", f"{full_type} 1"))
        row = {k: q.get(k) for k in ("queued", "fraction", "spawned", "itemId", "validStart", "maxTime", "error",
                                     "raw", "wall")}
        row["tag"] = tag
        self.out.setdefault("eats", []).append(row)
        self.spawned_stop(q, tag)
        return row

    # ---- clock reads
    def snap(self, tag, log=True):
        a = self.keep(self.step(tag, SRV, "time.snapshot", log=log))
        return {k: a.get(k) for k in ("worldAge", "hour", "minutes", "mult", "trueMult", "wall", "wall_after")}

    def wait_doc(self, name, after, timeout_s=30.0):
        if self.bus_dead:
            self.note(f"result {name}: skipped, server bus dead after {self.bus_dead}")
            return None
        try:
            return self.server.bus.wait_result(name, timeout=timeout_s, after=after)
        except Exception as e:                 # noqa: BLE001
            self.note(f"result {name}: {type(e).__name__}: {e}")
            return None

    # ---- the abort, teardown and artifact-copy skeleton
    def refuse(self, msg):
        """A pre-boot gate failed: record, persist, print and exit 1 before any boot."""
        self.out["error"] = msg
        self.persist()
        print(msg)
        sys.exit(1)

    def abort_on_missing_marker(self, dm, ok):
        """After verify: a deployed harness file lacking a marker ends the run; returns True when aborted."""
        self.out.setdefault("meta", {})["deployed_harness_markers"] = dm
        if ok:
            return False
        self.out["abort"] = f"a deployed harness file lacks a marker: {dm!r}"
        if self.tl is not None:
            self.tl.mark("error", detail=self.out["abort"][:200])
        print(self.out["abort"])
        return True

    def copy_artifacts(self, repo, run_id, run_dir, artifact):
        """Copy the run's artifact and the files named in `copied` byte-identical to
        testing/artifacts/<run_id>/; never raises."""
        dest_dir = os.path.join(repo, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(self.path, os.path.join(dest_dir, artifact))
            for nm in sorted(set(self.copied)):
                if os.path.isfile(os.path.join(run_dir, nm)):
                    shutil.copyfile(os.path.join(run_dir, nm), os.path.join(dest_dir, nm))
            print(f"copied to {dest_dir}")
            return dest_dir
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")
            return None

    def finish(self, teardown, hard_kill, started, read_logs=None, grade_all=None):
        """The run's finally block: teardown, hard kill, client facts, the log read and the grade, each
        fenced so one failure keeps the rest; the caller then copies the artifacts."""
        every = list(started)
        try:
            if self.server is not None:
                teardown(self.tl, self.server, [c for c in every if c.alive])
        except Exception as e:                 # noqa: BLE001
            self.out["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if self.server is not None:
                hard_kill(self.server, every)
            adm = self.clients.get(self.user) if isinstance(self.clients, dict) else None
            self.out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
            self.out["client_seen"] = [{"user": getattr(c, "username", str(i)), **dict(getattr(c, "seen", {}))}
                                       for i, c in enumerate(every)]
            if self.server is not None:
                self.out["server_errors"] = self.server.errors[:30]
                self.out["server_error_count"] = len(self.server.errors)
            for fn, key in ((read_logs, "logs_error"), (grade_all, "summary_error")):
                if fn is None:
                    continue
                try:
                    fn()
                except Exception as e:         # noqa: BLE001
                    self.out[key] = f"{type(e).__name__}: {e}"
                    self.out[key + "_traceback"] = traceback.format_exc()[-3000:]
            self.out["bus_dead"] = self.bus_dead
            self.out["copied"] = sorted(set(self.copied))
            self.out["wall_seconds"] = round(self.clock() - self.t0, 1)
            self.persist()
