"""x223-luasum -- Plan 10 Task S6 (live): the Lua arm of the join checksum, on the FROZEN 1.0.0 spike copy.

The server and `admin` boot release/spike-1.0.0/NutritionRevamp/Contents/mods/NutritionRevamp (staged by Task 0 at
42784ff; release/ is gitignored, so the hashes below are the record); `bob` alone gets a copy whose ONE Lua file
differs, through the profile's `[client_overrides.bob]` (harness commit aaa51f4). mod/ is never booted (Plan 10
ruling 2).

Two boots, in sequence, one at a time (two sessions, one artifact each, `luasum.json`):
  python testing/experiments/x223_luasum.py --boot a   profile x22-luasum-a, run prefix x223a: bob's
        common/media/lua/shared/NR_Core.lua differs from the server's by ONE byte inside its first comment line
        ("its version" -> "its versiom"; same length, LF endings kept).
  python testing/experiments/x223_luasum.py --boot b   profile x22-luasum-b, run prefix x223b: bob's NR_Core.lua is
        the frozen file with every line ending CRLF (no other byte changed).
Every NR_Core.lua the run deploys (server, admin, bob caches) is hashed: sha256, size, CR count and the MD5 of the
bytes with every CR dropped (the checksummer's own tolerance: NetChecksum$Checksummer.addFile @37-@55 L41-L43 skips
byte 13 before MessageDigest.update, and LuaManager.LoadDirBase @486-@522 L1225-L1226 feeds every loaded Lua file
except SandboxVars.lua to it when GameServer.server or GameClient.client is set -- a jar reading by this driver's
author, recorded for the prediction, never cited from here). The whole override tree is diffed against the frozen
tree, so the artifact names every file whose bytes differ.

THE BOOT IS THE ACTION. admin attaches first through session.attach_clients (it must reach ready: the admin role
bypasses the gate, #3139, and the verify rows read the version on the server and on admin). bob is then made with
the override (session.override_kw) and started by this driver, which watches it on its own clock: clicks through
"Click to Start" once in_game, stamps every alive change, and stops at READY + HOLD_AFTER_READY_S or at
OBS_S from bob's start, whichever comes first. A bob that never reaches ready, is kicked or exits is the READING,
recorded and never a failure of the driver (the raising-probe precedent for an expected failure; CLAUDE.md s5).
Both logs are tailed live with the driver's wall clock (server-stdout.log, bob's console.txt), so a kick is timed
against the server's line. After teardown: the server's ini checksum keys, its db role and whitelist rows for both
users and every userlog row, bob's console tail, and every checksum line on both sides.

LOG PATTERNS (CLAUDE.md s5: a server-log pattern excludes the driver's own probe names): the probes this driver
sends are `lua.global NutritionRevamp.version`, `lua.global TK.version` and `players`; none of them carries
`checksum`, `kick`, `disconnect`, `AntiCheat`, `File doesn` or `File status`, and every harness echo line (`PZTK: `)
is dropped before a match is kept.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / unmeasured):
  a  bob (role `user`) is disconnected before ready, as the script arm's one-byte copy was (#1282, #3137): bob never
     reaches ready; bob's console carries a disconnect/kick line; the server log carries the
     `will be kicked ... checksums do not match` warning and an `Anti-cheat`/`ChecksumUpdate` line; the db holds a
     `LuaChecksum` userlog row for bob. admin (same frozen bytes as the server) stays connected.
     Falsifier: bob reaches ready and answers lua.global NutritionRevamp.version after HOLD_AFTER_READY_S with no
     checksum line in either log (a Lua byte difference is not compared at the join).
  b  the CRLF-only copy joins, as the script arm's did (#3138): bob reaches ready, answers at ready and again after
     HOLD_AFTER_READY_S (past the 60 s grace, #1231), and neither log carries a checksum mismatch line.
     Falsifier: bob is disconnected, or either log carries a mismatch line naming the session.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time; never -safemode;
never kill a ProjectZomboid64.exe that predates the session (doctor checks game Java only).
"""
import glob
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients, check_mods_loaded,   # noqa: E402
                         make_client, make_server, override_kw, teardown, verify)

if "--boot" not in sys.argv or sys.argv[sys.argv.index("--boot") + 1:][:1] not in (["a"], ["b"]):
    print("usage: x223_luasum.py --boot a|b")
    sys.exit(2)
BOOT = sys.argv[sys.argv.index("--boot") + 1]
PROFILE = f"x22-luasum-{BOOT}"
PREFIX = f"x223{BOOT}"
SESSION = ("Plan 10 Task S6: the Lua arm of the join checksum -- the server and admin on the frozen 1.0.0 spike copy, "
           "bob on " + ("a copy whose NR_Core.lua differs by one byte inside a comment" if BOOT == "a" else
                        "a copy whose NR_Core.lua is the frozen file with CRLF line endings") + "; one boot of " + PROFILE)
ARTIFACT = "luasum.json"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = "NutritionRevamp"
FROZEN_ROOT = "release/spike-1.0.0/NutritionRevamp"
FROZEN_MOD = FROZEN_ROOT + "/Contents/mods/NutritionRevamp"
COPY_ROOT = f"release/spike-luasum-{BOOT}/NutritionRevamp"
COPY_MOD = COPY_ROOT + "/Contents/mods/NutritionRevamp"
CHANGED_REL = "common/media/lua/shared/NR_Core.lua"
FROZEN_AT = "42784ff"
HARNESS_COMMIT = "aaa51f4"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
BOB, ADMIN = "bob", "admin"
OBS_S = 180.0                 # bob watched at most this long from its start when it never reaches ready
HOLD_AFTER_READY_S = 90.0     # a ready bob is held this long past ready (the 60 s server grace + margin, #1231)
POLL_S = 0.25
LINE_CAP = 300
TAIL_LINES = 120
ECHO_RX = re.compile(r"PZTK: ")
CHK_SRV = re.compile(r"checksum|AntiCheat|Anti-cheat|LuaChecksum|kick|disconnect|File doesn|File status|"
                     r"ConnectionManager|logged|login|connected|access ?level", re.I)
CHK_CLI = re.compile(r"checksum|kick|disconnect|File doesn|File status|AntiCheat|Anti-cheat|forceDisconnect|"
                     r"serverDisconnected|STATE: enter|ConnectionManager|connection lost|Connection failed|"
                     r"LuaChecksum", re.I)
MISMATCH_RX = re.compile(r"will be kicked|checksums do not match|ChecksumUpdate|File doesn't match|"
                         r"File doesn't exist|File status unknown|Timed out connection because checksum|LuaChecksum",
                         re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server")
INI_RX = re.compile(r"^(DoLuaChecksum|AntiCheat\w*|Open|AutoCreateUserInWhiteList)=(.*)$")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, admin, bob, started = None, None, None, []


def wall():
    return round(time.time() - t0, 3)


def file_facts(p):
    try:
        with open(p, "rb") as fh:
            b = fh.read()
        return {"size": len(b), "cr": b.count(b"\r"), "sha256": hashlib.sha256(b).hexdigest(),
                "md5_cr_dropped": hashlib.md5(b.replace(b"\r", b"")).hexdigest()}
    except OSError as e:
        return {"error": f"{type(e).__name__}: {e}"}


def tree_diff(a_root, b_root):
    """Relative paths whose bytes differ, or that exist on one side only."""
    def files(root):
        out = {}
        for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if os.path.isfile(p):
                out[os.path.relpath(p, root).replace(os.sep, "/")] = p
        return out
    fa, fb = files(a_root), files(b_root)
    differ = []
    for rel in sorted(set(fa) | set(fb)):
        if rel not in fa or rel not in fb:
            differ.append({"path": rel, "only_in": "frozen" if rel in fa else "copy"})
            continue
        with open(fa[rel], "rb") as x, open(fb[rel], "rb") as y:
            if x.read() != y.read():
                differ.append({"path": rel})
    return {"files_frozen": len(fa), "files_copy": len(fb), "differ": differ}


PRED = {
    "a": {"bob ready": False, "bob disconnect line": True, "server warning": "will be kicked ... checksums do not match",
          "userlog": "a LuaChecksum row for bob", "admin": "stays connected"},
    "b": {"bob ready": True, "bob answers after HOLD_AFTER_READY_S": True, "checksum mismatch lines": 0},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "boot": BOOT, "users": list(prof.users), "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                "clients": {u: {"debug": (rec_fx.get("clients") or {}).get(u, {}).get("debug")}
                            for u in (rec_fx.get("clients") or {})}},
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "meta": {"frozen_mod": FROZEN_MOD, "frozen_at": FROZEN_AT, "copy_mod": COPY_MOD, "changed_file": CHANGED_REL,
             "harness_commit": HARNESS_COMMIT,
             "edit": ("one byte inside the first comment line of NR_Core.lua: 'its version' -> 'its versiom' "
                      "(same length, LF kept)") if BOOT == "a" else
                     "NR_Core.lua rewritten with every LF as CRLF; no other byte changed",
             "frozen_file": file_facts(os.path.join(REPO, FROZEN_MOD, CHANGED_REL)),
             "copy_file": file_facts(os.path.join(REPO, COPY_MOD, CHANGED_REL)),
             "frozen_manifest_sha256": file_facts(os.path.join(REPO, FROZEN_ROOT, "MANIFEST.json")).get("sha256")},
    "constants": {"OBS_S": OBS_S, "HOLD_AFTER_READY_S": HOLD_AFTER_READY_S, "LINE_CAP": LINE_CAP,
                  "TAIL_LINES": TAIL_LINES, "CHK_SRV": CHK_SRV.pattern, "CHK_CLI": CHK_CLI.pattern,
                  "MISMATCH_RX": MISMATCH_RX.pattern, "ECHO_RX": ECHO_RX.pattern},
    "predictions": PRED[BOOT],
    "deviations": [
        "One profile per boot (x22-luasum-a, x22-luasum-b) rather than one x22-luasum.toml: a profile's "
        "client_overrides names one folder per user, and the two boots give bob two different folders.",
        "bob is started by this driver rather than session.attach_clients, so a kick is a recorded reading and "
        "not a raise out of wait_ready; it is made with session.override_kw, the same call attach_clients makes.",
    ],
    "phases": {}, "notes": [], "reads": [],
}
try:
    out["meta"]["tree_diff"] = tree_diff(os.path.join(REPO, FROZEN_MOD), os.path.join(REPO, COPY_MOD))
except Exception as e:                         # noqa: BLE001
    out["meta"]["tree_diff_error"] = f"{type(e).__name__}: {e}"


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


class Tail:
    """Stamps each new line of a log with the driver's wall clock; keeps the matches (echo lines dropped, capped)
    and the total line count. A file truncated under us restarts at 0. Never raises."""

    def __init__(self, fname, rx):
        self.fname, self.rx, self.pos, self.n, self.hits, self.capped, self.echo = fname, rx, 0, 0, [], False, 0

    def start_at_end(self):
        try:
            self.pos = os.path.getsize(self.fname) if os.path.exists(self.fname) else 0
        except OSError:
            self.pos = 0

    def poll(self):
        try:
            if not os.path.exists(self.fname):
                return
            size = os.path.getsize(self.fname)
            if size < self.pos:
                self.pos = 0
            if size == self.pos:
                return
            with open(self.fname, encoding="utf-8", errors="replace") as fh:
                fh.seek(self.pos)
                chunk = fh.read()
                self.pos = fh.tell()
            w = wall()
            for line in chunk.splitlines():
                self.n += 1
                if not self.rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    self.echo += 1
                    continue
                if len(self.hits) < LINE_CAP:
                    self.hits.append({"wall": w, "n": self.n, "text": line.strip()[:400]})
                else:
                    self.capped = True
        except Exception as e:                 # noqa: BLE001
            out["notes"].append({"wall": wall(), "tail_error": f"{type(e).__name__}: {e}"})

    def report(self):
        return {"file": os.path.relpath(self.fname, run_dir), "lines_read": self.n, "cap": LINE_CAP,
                "capped": self.capped, "echo_lines_dropped": self.echo, "hits": self.hits}


def read(node, side, cmd, args, tag):
    w = wall()
    v = ask(node, cmd, args, timeout=15) if node is not None else {"error": "no node"}
    row = {"tag": tag, "side": side, "cmd": cmd, "args": args, "wall": w, "wall_after": wall(), "reply": v}
    out["reads"].append(row)
    return row


def deployed():
    rows = {}
    for p in sorted(glob.glob(os.path.join(run_dir, "**", "mods", MOD, "common", "media", "lua", "shared",
                                           "NR_Core.lua"), recursive=True)):
        rows[os.path.relpath(p, run_dir).replace(os.sep, "/")] = file_facts(p)
    return rows


def read_ini():
    vals = {}
    try:
        with open(server.ini, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = INI_RX.match(line.strip())
                if m:
                    vals[m.group(1)] = m.group(2)
    except Exception as e:                     # noqa: BLE001
        vals["error"] = f"{type(e).__name__}: {e}"
    return vals


def db_rows():
    res = []
    for p in glob.glob(os.path.join(run_dir, "server", "db", "*.db")):
        row = {"db": os.path.relpath(p, run_dir).replace(os.sep, "/")}
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            row["tables"] = tabs
            for t in tabs:
                low = t.lower()
                if low not in ("userlog", "whitelist", "role"):
                    continue
                cur = con.execute(f"select * from {t}")
                cols = [d[0] for d in cur.description]
                rows = [[str(x) for x in r] for r in cur.fetchall()]
                if low == "whitelist":   # the two users' rows only, and never a password hash
                    keep = [i for i, c in enumerate(cols) if c.lower() in ("id", "username", "role",
                                                                           "lastconnection", "authtype")]
                    rows = [[r[i] for i in keep] for r in rows if any(u in r for u in (ADMIN, BOB))]
                    cols = [cols[i] for i in keep]
                if low == "role":
                    keep = [i for i, c in enumerate(cols) if c.lower() in ("id", "name")]
                    rows = [[r[i] for i in keep] for r in rows]
                    cols = [cols[i] for i in keep]
                row[low] = {"cols": cols, "rows": rows[:60]}
            con.close()
        except Exception as e:                 # noqa: BLE001
            row["error"] = f"{type(e).__name__}: {e}"
        res.append(row)
    return res


def console_tail(fname, n):
    try:
        with open(fname, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        return {"total_lines": len(lines), "tail": [ln[:400] for ln in lines[-n:]]}
    except OSError as e:
        return {"error": f"{type(e).__name__}: {e}"}


def grep_noecho(fname, rx, limit):
    hits, skipped = [], 0
    try:
        with open(fname, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append({"n": i, "text": line.strip()[:400]})
                if len(hits) >= limit:
                    break
    except OSError:
        pass
    return {"hits": hits, "echo_lines_dropped": skipped}


def value(row):
    r = row.get("reply") if row else None
    return r.get("value") if isinstance(r, dict) else None


def watch_bob(ph, stail, ctail):
    global bob
    bob, restored = make_client(run_dir, BOB, server, rec_fx, safemode=prof.safemode, launcher=prof.launcher,
                                **override_kw(prof, BOB, server))
    started.append(bob)
    ph["bob_restored"] = restored
    ph["bob_debug"] = bob.debug
    ph["bob_mod_source"] = os.path.relpath(bob.mod_sources.get(MOD, ""), REPO).replace(os.sep, "/")
    ph["deployed_NR_Core"] = deployed()
    ctail.fname = bob.console
    ctail.start_at_end()
    stail.poll()
    bob.start()
    ph["bob_start_wall"] = wall()
    tl.mark("client_launch", user=BOB, restored=restored)
    last_click, alive_prev, ready_wall = 0.0, True, None
    deadline = time.time() + OBS_S
    while time.time() < deadline:
        stail.poll()
        ctail.poll()
        alive = bob.alive
        if alive != alive_prev:
            ph.setdefault("bob_alive_changes", []).append({"wall": wall(), "alive": alive})
            tl.mark("bob_alive", alive=alive)
            alive_prev = alive
        if "ready" in bob.seen and ready_wall is None:
            ready_wall = wall()
            ph["bob_ready_wall"] = ready_wall
            tl.mark("client_ready", user=BOB, took=bob.seen["ready"])
            read(bob, "client:bob", "lua.global", "NutritionRevamp.version", "bob_version_at_ready")
            read(bob, "client:bob", "lua.global", "TK.version", "bob_tk_at_ready")
            read(server, "server", "players", "", "players_at_bob_ready")
            deadline = time.time() + HOLD_AFTER_READY_S
        if "kicked" in bob.seen and "bob_kicked_marker_wall" not in ph:
            ph["bob_kicked_marker_wall"] = wall()
            tl.mark("bob_kicked_marker", t=bob.seen["kicked"])
        if alive and "in_game" in bob.seen and "ready" not in bob.seen and time.time() - last_click > 2.0:
            last_click = time.time()
            try:
                bob.click_to_start()
            except Exception as e:             # noqa: BLE001
                ph.setdefault("click_errors", []).append(str(e)[:120])
        time.sleep(POLL_S)
    stail.poll()
    ctail.poll()
    ph["window_end_wall"] = wall()
    ph["bob_alive_at_end"] = bob.alive
    if ready_wall is not None and bob.alive:
        read(bob, "client:bob", "lua.global", "NutritionRevamp.version", "bob_version_at_end")
    read(server, "server", "players", "", "players_at_end")
    read(admin, "client:admin", "lua.global", "TK.version", "admin_tk_at_end")
    ph["bob_seen"] = dict(bob.seen)
    ph["bob_events"] = bob.events[:200]
    ph["bob_t0_wall"] = round(bob.t0 - t0, 3) if bob.t0 else None


def grade():
    ph = out["phases"].get("boot") or {}
    logs = out.get("logs") or {}
    srv_mm = [h for h in (logs.get("server_mismatch") or {}).get("hits", [])]
    bob_mm = [h for h in (logs.get("bob_mismatch") or {}).get("hits", [])]
    adm_mm = [h for h in (logs.get("admin_mismatch") or {}).get("hits", [])]
    ready = ph.get("bob_ready_wall") is not None
    end_read = next((r for r in out["reads"] if r["tag"] == "bob_version_at_end"), None)
    answered_end = value(end_read) == "1.0.0"
    userlog = []
    for d in out.get("db") or []:
        for r in ((d.get("userlog") or {}).get("rows") or []):
            if any("LuaChecksum" in x for x in r) or any(BOB == x for x in r):
                userlog.append(r)
    disconnect = bool(ph.get("bob_kicked_marker_wall")) or any(
        re.search(r"disconnect|kick|connection lost|Connection failed", h["text"], re.I)
        for h in (out.get("live") or {}).get("bob", {}).get("hits", []))
    observed = {"bob_ready": ready, "bob_answered_at_end": answered_end, "bob_alive_at_end": ph.get("bob_alive_at_end"),
                "bob_disconnect_evidence": disconnect, "server_mismatch_lines": len(srv_mm),
                "bob_mismatch_lines": len(bob_mm), "admin_mismatch_lines": len(adm_mm),
                "userlog_rows_bob_or_luachecksum": userlog[:10],
                "admin_tk_at_end": value(next((r for r in out["reads"] if r["tag"] == "admin_tk_at_end"), None))}
    if ph.get("error") and not ph.get("bob_start_wall"):
        verdict = "unmeasured"
    elif BOOT == "a":
        if not ready and (disconnect or srv_mm or bob_mm):
            verdict = "as_predicted"
        elif ready and answered_end and not srv_mm and not bob_mm:
            verdict = "falsified"
        else:
            verdict = "unmeasured"
    else:
        if ready and answered_end and not srv_mm and not bob_mm:
            verdict = "as_predicted"
        elif not ready or srv_mm or bob_mm:
            verdict = "falsified"
        else:
            verdict = "unmeasured"
    out["verdicts"] = {BOOT: {"predicted": PRED[BOOT], "observed": observed, "verdict": verdict}}


# ---------------------------------------------------------------- run
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
lint_errors = lint_paths(profile.lint_sources(prof, prof.sources))
out["lint_errors"] = lint_errors
if lint_errors:
    out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
    persist()
    print(json.dumps(lint_errors, indent=1))
    sys.exit(1)

ph = out["phases"]["boot"] = {}
stail, ctail = None, Tail("", CHK_CLI)
try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    stail = Tail(server.log_path, CHK_SRV)
    server.start(timeout=prof.server_timeout)
    ph["server_started_wall"] = wall()
    tl.mark("server_started")
    out["build"] = server.build
    ph["ini"] = read_ini()
    check_mods_loaded(tl, server)
    admin = attach_clients(run_dir, prof, server, rec_fx, tl, users=[ADMIN], started=started)[ADMIN]
    ph["admin_ready_wall"] = wall()
    out["verify"] = verify(prof, server, {ADMIN: admin}, tl)
    persist()
    watch_bob(ph, stail, ctail)
    persist()
except Exception as e:                         # noqa: BLE001
    ph["error"], ph["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    try:
        if server is not None:
            teardown(tl, server, [c for c in started if c.alive])
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, started)
        if stail is not None:
            stail.poll()
        ctail.poll()
        out["live"] = {"server": stail.report() if stail is not None else None,
                       "bob": ctail.report() if ctail.fname else None}
        logs = out["logs"] = {"patterns": {"mismatch": MISMATCH_RX.pattern, "server": CHK_SRV.pattern,
                                           "client": CHK_CLI.pattern, "echo_dropped": ECHO_RX.pattern}}
        if server is not None:
            logs["server_mismatch"] = grep_noecho(server.log_path, MISMATCH_RX, LINE_CAP)
            logs["server_checksum_and_connection"] = grep_noecho(server.log_path, CHK_SRV, LINE_CAP)
            errs = [str(e) for e in server.errors]
            out["mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
        if bob is not None:
            logs["bob_mismatch"] = grep_noecho(bob.console, MISMATCH_RX, LINE_CAP)
            logs["bob_checksum_and_state"] = grep_noecho(bob.console, CHK_CLI, LINE_CAP)
            logs["bob_console_tail"] = console_tail(bob.console, TAIL_LINES)
        if admin is not None:
            logs["admin_mismatch"] = grep_noecho(admin.console, MISMATCH_RX, LINE_CAP)
            out["admin_lua_error"] = "lua_error" in admin.seen
        out["client_seen"] = [{"user": getattr(c, "username", "?"), **dict(getattr(c, "seen", {}))} for c in started]
        try:
            out["db"] = db_rows()
        except Exception as e:                 # noqa: BLE001
            out["db_error"] = f"{type(e).__name__}: {e}"
        try:
            grade()
        except Exception as e:                 # noqa: BLE001
            out["grade_error"] = f"{type(e).__name__}: {e}"
            out["grade_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": out.get("verdicts"), "error": ph.get("error"), "grade_error": out.get("grade_error"),
                  "run_id": run_id}, indent=1, default=str)[:6000])
