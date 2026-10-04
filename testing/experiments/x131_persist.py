"""x131-persist -- X28 (modData across a save and reload), X49a (the global modData file's save
cadence) and X49b (a global value written a minute before a hard stop): Plan 1 Task 13.

The run id prefix is `x131p` (run id `x131p-<date>-<time>`): the register's run-id pattern (a
lowercase alphanumeric prefix, then eight and six digits) refuses a hyphen in the prefix, so the
amendments' `x131-persist-<id>` could not be named by a `run:` pointer.

Copied from `_template.py` (house shape) and from `x131_calcrepro.py` (the step / persist /
grade wrappers, the per-boot structure). ONE live session, profile `x13-persist` (PZTestKit only,
the fixture's own sandbox: DayLength 4, a 90-minute game day, one game-minute = 3.75 s wall,
#0893), FIVE server processes in sequence, one at a time:

  1   fresh restore into `<run>/server`. X49a arm (a): no write for WINDOW_WALL_S. Then the X28
      writes, which are also X49a arm (b)'s write: client `moddata.set TKX_persist_c 1` +
      `moddata.transmit` FIRST (one client transmit replaces the server's copy, #1042, so the
      server write comes after it), then server `moddata.set admin TKX_persist 1`, server
      `globalmoddata.set TKX_persist k 1` + `globalmoddata.transmit TKX_persist`; witness reads
      client-first; arm (b): WINDOW_WALL_S with no further write; arm (c): RCON `save` (the
      positive control), watched for SAVE_WATCH_S; then a clean teardown (client quit, server
      `quit`).
  2   `make_server(..., reuse=True)` on the same `<run>/server`: the X28 read (both scopes, both
      sides, client-first). Then the quit-only arm (a driver addition beside the brief, decided
      before the run): server `moddata.set admin TKX_quit 1` and `globalmoddata.set TKX_quit k 1`
      with NO RCON save and no transmit, then a clean teardown -- boot 3 reads whether a clean
      `quit` alone carries a value to disk.
  3   reuse boot: reads TKX_persist (a second clean cycle) and TKX_quit; then X49b: server
      `globalmoddata.set TKX_restart k 2` + `globalmoddata.transmit TKX_restart`, read back on both
      sides client-first, the game clock polled until one game-minute has passed since the write,
      then the server process HARD-KILLED (`Server.kill`: `taskkill /T /F`, no `quit`, no save),
      wall-stamped either side; the client is then killed too.
  3r  reuse boot after the kill: reads TKX_restart (X49b), TKX_persist and TKX_quit; clean teardown.
  4   the control: a FRESH restore of the golden fixture into `<run>/boot4/server`; every key must
      MISS on both sides, which proves the run directory and not the fixture carried them.

Every boot's client cache is a FRESH restore of the fixture's client into its own sub-directory
(`<run>/c<label>/clients/admin`): the fixture's client holds no character save (its Saves folder
has no player file), so a player key present after a reload came from the server's store.

Throughout the session a background sampler `stat`s the current server's `global_mod_data.bin`
every SAMPLE_S seconds (exists, size, mtime_ns, sha256, whether the bytes contain each table
name), keeps the whole file as hex on every change, and tails the current boot's server log for
`Saving GlobalModData`, stamping each new line with the wall time it was first seen. The run's
ini `SaveWorldEveryMinutes` (and the backup keys) is read and recorded. At each phase point the
server's SQLite store (`db/pzt.db` and any `-wal`/`-journal`) is scanned for the player keys'
bytes.

Global reads go through `ModData.getOrCreate`, which CREATES an absent table (#1750): the driver
never reads a global table on the server before the run writes it in that world (except boot 4,
the control, whose file is never graded), so a table name in the file's bytes means a table the
run wrote. Every global reading is the KEY's presence, never the table's existence. A
player-scope census includes the vanilla fitness keys and the hotbar (#1966); only the named keys
are graded.

Window length (deviation, decided before the run): the amendments give an arm as "ten
game-minutes ... 37.5 s x 10 = 375 s wall"; at DayLength 4 ten game-minutes are 37.5 s wall
(#0893), not 375 s. The driver holds each of arms (a) and (b) for WINDOW_WALL_S = 375 s wall
(about 100 game-minutes, ten times the brief's ten game-minutes) so that a cadence slower than a
minute can show; the game clock is snapshotted at each arm's start and end and both lengths are
recorded.

PREDICTIONS AND FALSIFIERS (written before the run):

  X28 player scope (#1294). Boot 2's SERVER census of admin's modData holds TKX_persist = "1"
      (server-written) and TKX_persist_c = "1" (client-written and transmitted), and boot 4's
      misses both (the code reading: the player blob carries character modData, #2394).
      Falsifier: either key absent at boot 2 while boot 4 misses it (the two keys are graded
      separately -- the client's quit-time upload could carry the client's copy, which lacks the
      server-written key, over the server's). Boot 4 holding a key makes the arm `unmeasured`
      (the control failed); a witness that does not answer is `unmeasured`.
  X28 global scope (#1294). Boot 2's server read of `global:TKX_persist k` is "1", and boot 4's
      misses it (#2397: one file per world). Falsifier: absent at boot 2 with boot 4 missing.
  X49a (#2097). SaveWorldEveryMinutes is 0 in the fixture's ini (read and recorded at run time),
      so: arm (a) -- no mtime change and no `Saving GlobalModData` line over the window; arm (b) --
      no prediction favoured (whether a write and transmit triggers a save is the reading); arm
      (c) -- RCON `save` moves the mtime and logs the line (the positive control). The clean
      `quit` is predicted to move it once (a shutdown save). Falsifier of the control: (c) moves
      nothing, which makes (a) and (b) `unmeasured`. A move in (a) is a cadence the ini did not
      predict: `falsified`, with the interval written down.
  X49b (#2098). Predicted from the load path (`GlobalModData.load` clears the map and reads the
      file, #2098's C): TKX_restart k is present at boot 3r if and only if the sampler saw the
      file change between the write and the kill. Falsifier: present with no change in that
      window (some other path persisted it), or absent with a change containing the table name.
      Boot 4 must miss it.
  Quit-only arm (driver addition, recorded as M `verdict` material, not one of the three
      questions): TKX_quit (both scopes) is present at boot 3 if a clean `quit` saves.

What follows is the template's own rule, kept as the house shape this driver obeys.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. The artifact is evidence of what this exact file
     did; changing the file afterwards makes the pair unreadable. If something has to change,
     that is a new driver (`xNNNb_...`) and a new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier, and never collapse "the read did not happen" into "the
     prediction failed" -- they are different answers.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill, num   # noqa: E402
from pzt import fixture as fx, profile                                # noqa: E402
from pzt.paths import new_run_dir                                     # noqa: E402
from pzt.session import (Timeline, make_client, make_server,         # noqa: E402
                         teardown, verify)

PROFILE = "x13-persist"
SESSION = ("X28 + X49a + X49b: player and global modData across a clean save and reload, the "
           "global_mod_data.bin save cadence (no write / write+transmit / RCON save), and a "
           "global value written one game-minute before a hard kill; five server boots, the "
           "last a fresh fixture control")
ARTIFACT = "persist.json"
USER = "admin"
ACCEPTANCE_RUN = "x131b-20261004-175911"

# ---- constants ------------------------------------------------------------------------------
GAME_MIN_WALL_S = 3.75                 # DayLength 4: a 90-minute game day (#0893)
WINDOW_WALL_S = 375.0                  # arms (a) and (b), see the docstring's deviation note
SAMPLE_S = 5.0
SAVE_WATCH_S = 30.0                    # arm (c): how long the RCON save is watched
POST_TEARDOWN_S = 10.0                 # sampler time after each teardown / kill
LOG_LIMIT = 100
SAVE_RX = re.compile(r"Saving GlobalModData")
HEX_CAP = 8192
SAVE_DIR = os.path.join("Saves", "Multiplayer", "pzt")
GMD_FILE = "global_mod_data.bin"
TABLES = ("TKX_persist", "TKX_quit", "TKX_restart")
PLAYER_KEYS = ("TKX_persist", "TKX_persist_c", "TKX_quit")
INI_KEYS = ("SaveWorldEveryMinutes", "BackupsOnStart", "BackupsPeriod", "BackupsCount",
            "BackupsOnVersionChange")
TRACE_RX = re.compile(r"Lua\(\(MOD:TKX|STACK TRACE")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

lock = threading.Lock()
watch = {"file": None, "boot": None, "phase": "pre", "log": None, "log_off": 0, "log_line": 0,
         "stop": False, "last_sig": None}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    with lock:
        out["notes"].append({"wall": wall(), "boot": cur.get("label"), "note": msg})


def set_phase(name):
    with lock:
        watch["phase"] = name
    tl.mark("phase", boot=cur.get("label"), name=name)


def persist():
    """Write the artifact (never raises): the timeline and each boot's server error list."""
    try:
        with lock:
            out["timeline"] = list(tl.items)
            for label, srv in servers.items():
                if srv is not None:
                    out["boots"][label]["server_errors"] = srv.errors[:20]
                    out["boots"][label]["server_error_count"] = len(srv.errors)
            text = json.dumps(out, indent=1)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - teardown path, never raise
        print(f"could not write {path}: {type(e).__name__}: {e}")


# ---- the file sampler -----------------------------------------------------------------------
def file_state(p):
    try:
        st = os.stat(p)
        with open(p, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        return {"exists": False, "error": f"{type(e).__name__}"}, None
    return {"exists": True, "size": st.st_size, "mtime": st.st_mtime, "mtime_ns": st.st_mtime_ns,
            "sha256": hashlib.sha256(raw).hexdigest()[:16],
            "has": {t: t.encode() in raw for t in TABLES}}, raw


def tail_log():
    """New `Saving GlobalModData` lines in the current boot's log since the last call."""
    p = watch["log"]
    if not p:
        return
    try:
        with open(p, "rb") as fh:
            fh.seek(watch["log_off"])
            chunk = fh.read()
    except OSError:
        return
    if not chunk:
        return
    cut = chunk.rfind(b"\n")
    if cut < 0:
        return
    body = chunk[:cut + 1]
    watch["log_off"] += len(body)
    for line in body.decode("utf-8", errors="replace").splitlines():
        watch["log_line"] += 1
        if SAVE_RX.search(line):
            out["save_log_lines"].append({"wall_seen": wall(), "boot": watch["boot"],
                                          "phase": watch["phase"], "line": watch["log_line"],
                                          "text": line.strip()[:240]})


def sample_once(tag="tick"):
    with lock:
        p = watch["file"]
        if p is None:
            return None
        st, raw = file_state(p)
        row = {"wall": wall(), "boot": watch["boot"], "phase": watch["phase"], "tag": tag, **st}
        out["mtime_series"].append(row)
        sig = (st.get("exists"), st.get("mtime_ns"), st.get("size"), st.get("sha256"))
        if sig != watch["last_sig"]:
            out["file_changes"].append({**row, "prev": watch["last_sig"],
                                        "hex": raw[:HEX_CAP].hex() if raw is not None else None})
            watch["last_sig"] = sig
        tail_log()
        return row


def sampler():
    while not watch["stop"]:
        try:
            sample_once()
        except Exception as e:                 # noqa: BLE001 - the sampler never dies quietly
            with lock:
                out["notes"].append({"wall": wall(), "sampler_error": f"{type(e).__name__}: {e}"})
        for _ in range(int(SAMPLE_S * 4)):
            if watch["stop"]:
                return
            time.sleep(0.25)


def point_watch(label, server_cache, log_path):
    with lock:
        watch["boot"] = label
        watch["file"] = os.path.join(server_cache, SAVE_DIR, GMD_FILE)
        watch["log"] = log_path
        watch["log_off"] = 0
        watch["log_line"] = 0


def db_scan(tag):
    """The server's SQLite player store: does it hold each player key's bytes? Phase points
    only (the file can be large)."""
    res = {"tag": tag, "wall": wall(), "boot": cur.get("label"), "files": {}}
    base = os.path.join(cur["server_cache"], "db", "pzt.db")
    for suffix in ("", "-wal", "-journal"):
        p = base + suffix
        try:
            with open(p, "rb") as fh:
                raw = fh.read()
            st = os.stat(p)
            res["files"][os.path.basename(p)] = {"size": len(raw), "mtime": st.st_mtime,
                                                 "has": {k: k.encode() in raw for k in PLAYER_KEYS}}
        except OSError:
            pass
    with lock:
        out["db_scans"].append(res)
    return res


# ---- bus wrappers ---------------------------------------------------------------------------
def step(name, side, cmd, args="", timeout=30):
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is cur.get("server") else "client",
           "phase": watch["phase"], "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    with lock:
        cur["B"]["steps"].append(row)
    return row


def clock(tag):
    r = step(f"clock_{tag}", cur["server"], "time.snapshot", "")
    a = r["ack"] if isinstance(r["ack"], dict) else {}
    with lock:
        cur["B"]["clock"].append({"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge"),
                                  "hour": a.get("hour"), "minutes": a.get("minutes"),
                                  "mult": a.get("mult")})
    return num(a.get("worldAge"))


def wit_one(side, scope, keys):
    r = step(f"wit_{scope}", side, "witness.moddata", scope + " " + " ".join(keys))
    a = r["ack"] if isinstance(r["ack"], dict) else None
    if a is None or a.get("error"):
        return {"answered": False, "ack": r["ack"], "wall": r["wall_before"]}
    vals = a.get("values") or {}
    return {"answered": True, "wall": r["wall_before"], "worldAge": a.get("worldAge"),
            "values": {k: vals.get(k) for k in keys}, "present": {k: k in vals for k in keys},
            "missing": a.get("missing"), "keyCount": a.get("keyCount"), "keys": a.get("keys"),
            "count": a.get("count"), "count_ok": a.get("count") == len(keys)}


def witness(tag, tables):
    """Client first, then server; the player census and each named global table's key `k`."""
    rec_ = {"tag": tag, "wall": wall()}
    for side_name in ("client", "server"):
        side = cur["client"] if side_name == "client" else cur["server"]
        sr = {"player": wit_one(side, f"player:{USER}", PLAYER_KEYS)}
        for t in tables:
            sr["global:" + t] = wit_one(side, f"global:{t}", ["k"])
        rec_[side_name] = sr
    with lock:
        cur["B"]["witness"][tag] = rec_
    tl.mark("witness", boot=cur.get("label"), tag=tag)
    persist()
    return rec_


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def grep_numbered(path_, rx, limit):
    hits = []
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:240]})
                    if len(hits) >= limit:
                        break
    except OSError as e:                       # noqa: BLE001 - recorded, not raised
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


def read_ini(p):
    vals = {}
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                k, _, v = line.strip().partition("=")
                if k in INI_KEYS:
                    vals[k] = v
    except OSError as e:
        vals["error"] = f"{type(e).__name__}: {e}"
    return vals


def hold_window(tag, seconds):
    a0 = clock(f"{tag}_start")
    w0 = wall()
    sample_once(f"{tag}_start")
    while wall() < w0 + seconds:
        time.sleep(min(1.0, max(0.0, w0 + seconds - wall())))
    sample_once(f"{tag}_end")
    a1 = clock(f"{tag}_end")
    with lock:
        cur["B"]["windows"][tag] = {"wall_start": w0, "wall_end": wall(), "worldAge_start": a0,
                                    "worldAge_end": a1,
                                    "game_minutes": round((a1 - a0) * 60.0, 3) if a0 is not None
                                    and a1 is not None else None}


# ---- the boots ------------------------------------------------------------------------------
def body_1():
    srv = cur["server"]
    B = cur["B"]
    B["file_path"] = os.path.relpath(watch["file"], run_dir)
    B["ini"] = read_ini(srv.ini)
    out["ini"] = B["ini"]
    db_scan("b1_ready")
    set_phase("a_nowrite")
    hold_window("a", WINDOW_WALL_S)
    set_phase("b_write")
    witness("b1_prewrite", ("TKX_persist",))
    c = cur["client"]
    B["writes"] = [step("c_set", c, "moddata.set", "TKX_persist_c 1"),
                   step("c_transmit", c, "moddata.transmit", "")]
    time.sleep(3.0)
    B["writes"] += [step("s_set", srv, "moddata.set", f"{USER} TKX_persist 1"),
                    step("s_gset", srv, "globalmoddata.set", "TKX_persist k 1"),
                    step("s_gtransmit", srv, "globalmoddata.transmit", "TKX_persist")]
    B["write_wall"] = B["writes"][-1]["wall_after"]
    sample_once("b_after_write")
    witness("b1_postwrite", ("TKX_persist",))
    hold_window("b", WINDOW_WALL_S)
    witness("b1_window_end", ("TKX_persist",))
    db_scan("b1_before_save")
    set_phase("c_save")
    before = sample_once("c_before")
    t_a = wall()
    ok, reply = srv.rcon("save")
    t_b = wall()
    B["rcon_save"] = {"wall_before": t_a, "wall_after": t_b, "ok": ok, "reply": reply,
                      "mtime_before": (before or {}).get("mtime_ns")}
    tl.mark("rcon_save", ok=ok, reply=str(reply)[:80])
    end = wall() + SAVE_WATCH_S
    while wall() < end:
        time.sleep(1.0)
        sample_once("c_watch")
    db_scan("b1_after_save")
    witness("b1_after_save", ("TKX_persist",))
    set_phase("quit")


def body_2():
    srv = cur["server"]
    B = cur["B"]
    db_scan("b2_ready")
    set_phase("x28_read")
    witness("b2_x28", ("TKX_persist",))
    set_phase("quit_arm_write")
    B["writes"] = [step("s_set_quit", srv, "moddata.set", f"{USER} TKX_quit 1"),
                   step("s_gset_quit", srv, "globalmoddata.set", "TKX_quit k 1")]
    witness("b2_after_quit_write", ("TKX_persist", "TKX_quit"))
    set_phase("quit")


def body_3():
    srv = cur["server"]
    B = cur["B"]
    db_scan("b3_ready")
    set_phase("reads")
    witness("b3_reads", ("TKX_persist", "TKX_quit"))
    set_phase("x49b_write")
    B["writes"] = [step("s_gset_restart", srv, "globalmoddata.set", "TKX_restart k 2"),
                   step("s_gtransmit_restart", srv, "globalmoddata.transmit", "TKX_restart")]
    B["write_wall"] = B["writes"][0]["wall_after"]
    a_write = clock("x49b_write")
    sample_once("x49b_after_write")
    witness("b3_after_restart_write", ("TKX_restart",))
    target = (a_write + 1.0 / 60.0) if a_write is not None else None
    polls = []
    while True:
        a = clock("x49b_poll")
        polls.append({"wall": wall(), "worldAge": a})
        if target is None or (a is not None and a >= target) or wall() > B["write_wall"] + 30:
            break
        time.sleep(0.5)
    B["x49b_polls"] = polls
    set_phase("kill")
    sample_once("kill_before")
    t_a = wall()
    srv.kill()
    rc = None
    try:
        rc = srv.proc.wait(30)
    except Exception as e:                     # noqa: BLE001
        note(f"wait after kill: {type(e).__name__}: {e}")
    t_b = wall()
    B["kill"] = {"wall_before": t_a, "wall_after": t_b, "rc": rc, "alive_after": srv.alive,
                 "worldAge_write": a_write, "worldAge_last_poll": polls[-1]["worldAge"] if polls else None,
                 "write_to_kill_wall_s": round(t_a - B["write_wall"], 3)}
    tl.mark("server_killed", rc=rc, write_to_kill=B["kill"]["write_to_kill_wall_s"])
    sample_once("kill_after")
    try:
        cur["client"].kill()
    except Exception as e:                     # noqa: BLE001
        note(f"client kill: {type(e).__name__}: {e}")
    set_phase("killed")


def body_3r():
    db_scan("b3r_ready")
    set_phase("x49b_read")
    witness("b3r_reads", TABLES)
    set_phase("quit")


def body_4():
    db_scan("b4_ready")
    set_phase("control_read")
    witness("b4_control", TABLES)
    set_phase("quit")


BOOTS = [("1", False, body_1), ("2", True, body_2), ("3", True, body_3), ("3r", True, body_3r),
         ("4", False, body_4)]


def boot(label, reuse, body):
    B = out["boots"][label] = {"reuse": reuse, "steps": [], "witness": {}, "clock": [],
                               "windows": {}}
    cur.clear()
    cur.update({"label": label, "B": B})
    tl.mark("boot", label=label, reuse=reuse)
    clients = []
    server = None
    base = run_dir if label != "4" else os.path.join(run_dir, "boot4")
    try:
        os.makedirs(base, exist_ok=True)
        server = make_server(base, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, reuse=reuse)
        server.log_path = os.path.join(run_dir, f"server-stdout-boot{label}.log")
        servers[label] = server
        cur["server"] = server
        cur["server_cache"] = server.cache
        B["server_cache"] = os.path.relpath(server.cache, run_dir)
        point_watch(label, server.cache, server.log_path)
        set_phase("boot")
        sample_once("before_start")
        server.start(timeout=prof.server_timeout)
        tl.mark("server_started", label=label)
        sample_once("server_started")
        B["build"] = server.build
        c, restored = make_client(os.path.join(run_dir, f"c{label}"), USER, server, rec)
        B["client_restored"] = restored
        cur["client"] = c
        c.start()
        clients.append(c)
        c.wait_ready(timeout=prof.client_timeout)
        tl.mark("session_ready", label=label)
        B["session_ready_wall"] = wall()
        B["verify"] = verify(prof, server, clients, tl)
        B["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                               "client": sorted(set(c.mods_not_found))}
        persist()
        body()
    except Exception as e:                     # noqa: BLE001 - the boot is a result; keep its rows
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", label=label, detail=str(e)[:200])
    finally:
        B["wall_end_body"] = wall()
        persist()
        try:
            if server is not None and label != "3":
                set_phase("quit")
                teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                B["server_rc"] = server.proc.returncode if server.proc else None
                hard_kill(server, clients)
            end = wall() + POST_TEARDOWN_S
            while wall() < end:
                time.sleep(1.0)
            sample_once("after_teardown")
            if server is not None:
                db_scan(f"b{label}_after_teardown")
            set_phase("down")
            B["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            if server is not None:
                logs = {"save_lines": grep_numbered(server.log_path, SAVE_RX, LOG_LIMIT),
                        "trace_lines": grep_numbered(server.log_path, TRACE_RX, 40),
                        "server_log": os.path.relpath(server.log_path, run_dir)}
                if clients:
                    logs.update({"client_trace_lines": grep_numbered(clients[0].console, TRACE_RX, 40),
                                 "client_console": os.path.relpath(clients[0].console, run_dir)})
                B["logs"] = logs
            B["wall_end"] = wall()
            persist()


# ---- grading --------------------------------------------------------------------------------
def srv_wit(label, tag):
    return ((out["boots"].get(label) or {}).get("witness") or {}).get(tag) or {}


def present(w, side, scope, key):
    """True / False when the side answered, None when it did not."""
    s = (w.get(side) or {}).get(scope) or {}
    if not s.get("answered"):
        return None
    return bool((s.get("present") or {}).get(key))


def value(w, side, scope, key):
    s = (w.get(side) or {}).get(scope) or {}
    return (s.get("values") or {}).get(key)


def changes_in(boot, phase):
    return [c for c in out["file_changes"] if c["boot"] == boot and c["phase"] == phase
            and c.get("prev") is not None]


def lines_in(boot, phase):
    return [ln for ln in out["save_log_lines"] if ln["boot"] == boot and ln["phase"] == phase]


def grade_all():
    w2, w3, w3r, w4 = srv_wit("2", "b2_x28"), srv_wit("3", "b3_reads"), srv_wit("3r", "b3r_reads"), \
        srv_wit("4", "b4_control")
    # X28 player
    keys = {}
    for k in ("TKX_persist", "TKX_persist_c"):
        keys[k] = {"b2_server": present(w2, "server", "player", k), "b2_client": present(w2, "client", "player", k),
                   "b2_server_value": value(w2, "server", "player", k),
                   "b3_server": present(w3, "server", "player", k),
                   "b4_server": present(w4, "server", "player", k), "b4_client": present(w4, "client", "player", k)}
    if any(v["b2_server"] is None or v["b4_server"] is None for v in keys.values()):
        vp = "unmeasured"
    elif any(v["b4_server"] for v in keys.values()):
        vp = "unmeasured"
    elif all(v["b2_server"] for v in keys.values()):
        vp = "as_predicted"
    else:
        vp = "falsified"
    grade("X28-player", "boot 2's server census holds TKX_persist and TKX_persist_c; boot 4 misses both",
          keys, vp, "either key absent at boot 2 while boot 4 misses it; boot 4 holding a key = unmeasured")
    # X28 global
    g = {"b2_server": present(w2, "server", "global:TKX_persist", "k"),
         "b2_client": present(w2, "client", "global:TKX_persist", "k"),
         "b2_server_value": value(w2, "server", "global:TKX_persist", "k"),
         "b3_server": present(w3, "server", "global:TKX_persist", "k"),
         "b4_server": present(w4, "server", "global:TKX_persist", "k"),
         "b4_client": present(w4, "client", "global:TKX_persist", "k")}
    if g["b2_server"] is None or g["b4_server"] is None or g["b4_server"]:
        vg = "unmeasured"
    elif g["b2_server"]:
        vg = "as_predicted"
    else:
        vg = "falsified"
    grade("X28-global", "boot 2's server read of global:TKX_persist k is 1; boot 4 misses it", g, vg,
          "absent at boot 2 while boot 4 misses it")
    # X49a
    arms = {}
    for ph in ("a_nowrite", "b_write", "c_save", "quit"):
        arms[ph] = {"file_changes": [{"wall": c["wall"], "mtime_ns": c.get("mtime_ns"), "size": c.get("size"),
                                      "has": c.get("has")} for c in changes_in("1", ph)],
                    "save_lines": [{"wall_seen": ln["wall_seen"], "line": ln["line"]} for ln in lines_in("1", ph)]}
    arms["windows"] = (out["boots"].get("1") or {}).get("windows")
    arms["rcon_save"] = (out["boots"].get("1") or {}).get("rcon_save")
    arms["ini"] = out.get("ini")
    c_moved = bool(arms["c_save"]["file_changes"]) and bool(arms["c_save"]["save_lines"])
    a_moved = bool(arms["a_nowrite"]["file_changes"]) or bool(arms["a_nowrite"]["save_lines"])
    win_ok = bool((arms["windows"] or {}).get("a")) and bool((arms["windows"] or {}).get("b"))
    if not c_moved or not win_ok:
        va = "unmeasured"
    elif a_moved:
        va = "falsified"
    else:
        va = "as_predicted"
    grade("X49a", "SaveWorldEveryMinutes 0: arm (a) no change and no log line; arm (b) the reading; "
                  "arm (c) RCON save moves the mtime and logs once; quit moves it once", arms, va,
          "(c) moving nothing = unmeasured; a move in (a) = a cadence the ini did not predict")
    # Quit-only arm
    q = {"player_b3_server": present(w3, "server", "player", "TKX_quit"),
         "global_b3_server": present(w3, "server", "global:TKX_quit", "k"),
         "player_b4_server": present(w4, "server", "player", "TKX_quit"),
         "global_b4_server": present(w4, "server", "global:TKX_quit", "k"),
         "boot2_quit_file_changes": [{"wall": c["wall"], "size": c.get("size"), "has": c.get("has")}
                                     for c in changes_in("2", "quit")],
         "boot2_quit_save_lines": [ln["line"] for ln in lines_in("2", "quit")]}
    if q["player_b3_server"] is None or q["global_b3_server"] is None:
        vq = "unmeasured"
    elif q["player_b4_server"] or q["global_b4_server"]:
        vq = "unmeasured"
    elif q["player_b3_server"] and q["global_b3_server"]:
        vq = "as_predicted"
    else:
        vq = "falsified"
    grade("quit-only", "TKX_quit present at boot 3 in both scopes if a clean quit saves", q, vq,
          "either scope absent at boot 3")
    # X49b
    B3 = out["boots"].get("3") or {}
    kill = B3.get("kill") or {}
    ww, kw = B3.get("write_wall"), kill.get("wall_before")
    win_changes = [c for c in out["file_changes"] if c["boot"] == "3" and c.get("prev") is not None
                   and ww is not None and kw is not None and ww <= c["wall"] <= kw + 0.5]
    after_kill = [c for c in out["file_changes"] if c["boot"] == "3" and c.get("prev") is not None
                  and kw is not None and c["wall"] > kw + 0.5]
    wrote_restart = any((c.get("has") or {}).get("TKX_restart") for c in win_changes)
    b = {"b3r_server": present(w3r, "server", "global:TKX_restart", "k"),
         "b3r_client": present(w3r, "client", "global:TKX_restart", "k"),
         "b3r_server_value": value(w3r, "server", "global:TKX_restart", "k"),
         "b4_server": present(w4, "server", "global:TKX_restart", "k"),
         "readback_b3_server": present(srv_wit("3", "b3_after_restart_write"), "server", "global:TKX_restart", "k"),
         "readback_b3_client": present(srv_wit("3", "b3_after_restart_write"), "client", "global:TKX_restart", "k"),
         "kill": kill, "write_wall": ww,
         "file_changes_write_to_kill": [{"wall": c["wall"], "has": c.get("has"), "size": c.get("size")}
                                        for c in win_changes],
         "file_changes_after_kill_boot3": [{"wall": c["wall"], "has": c.get("has")} for c in after_kill],
         "save_lines_boot3": [{"wall_seen": ln["wall_seen"], "phase": ln["phase"], "line": ln["line"]}
                              for ln in out["save_log_lines"] if ln["boot"] == "3"]}
    if b["b3r_server"] is None or b["b4_server"] is None or b["b4_server"] or not b["readback_b3_server"]:
        vb = "unmeasured"
    elif b["b3r_server"] == wrote_restart:
        vb = "as_predicted"
    else:
        vb = "falsified"
    b["file_wrote_restart_before_kill"] = wrote_restart
    grade("X49b", "TKX_restart k present at boot 3r iff the file changed (holding the table) between "
                  "the write and the kill; boot 4 misses it", b, vb,
          "present with no file change in the window, or absent with one")


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x131p-dry-run", None) if DRY_RUN else new_run_dir("x131p")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
servers, cur = {}, {}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),
    "mods": list(prof.mods),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"GAME_MIN_WALL_S": GAME_MIN_WALL_S, "WINDOW_WALL_S": WINDOW_WALL_S,
                  "SAMPLE_S": SAMPLE_S, "SAVE_WATCH_S": SAVE_WATCH_S,
                  "POST_TEARDOWN_S": POST_TEARDOWN_S, "TABLES": TABLES, "PLAYER_KEYS": PLAYER_KEYS,
                  "SAVE_DIR": SAVE_DIR, "GMD_FILE": GMD_FILE},
    "world_changes": {"restored": "boots 1-3r share <run>/server (one fresh restore at boot 1); boot 4 "
                                  "restores the fixture into <run>/boot4/server; every client is a "
                                  "fresh fixture restore under <run>/c<label>",
                      "left_in_place": []},
    "boots": {}, "notes": [], "verdicts": {},
    "mtime_series": [], "file_changes": [], "save_log_lines": [], "db_scans": [],
}

if DRY_RUN:
    print(json.dumps(out))
    sys.exit(0)

th = threading.Thread(target=sampler, daemon=True)
th.start()
try:
    for label, reuse, body in BOOTS:
        boot(label, reuse, body)
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": {k: [v.get("ok") for v in b.get("verify", [])] for k, b in out["boots"].items()},
        "mods_not_found": {k: b.get("mods_not_found") for k, b in out["boots"].items()},
        "boot_errors": {k: b.get("error") for k, b in out["boots"].items()},
        "server_error_count": {k: b.get("server_error_count") for k, b in out["boots"].items()},
        "client_lua_error": {k: b.get("client_lua_error") for k, b in out["boots"].items()},
        "file_change_count": len(out["file_changes"]),
        "save_log_line_count": len(out["save_log_lines"]),
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    watch["stop"] = True
    th.join(timeout=10)
    out["wall_seconds"] = round(time.time() - t0, 1)
    for srv in servers.values():
        try:
            hard_kill(srv, [])
        except Exception:                      # noqa: BLE001
            pass
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001 - never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
