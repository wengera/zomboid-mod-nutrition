"""Plan 6 Task 8, X16 (`x171c`): the one-byte script-checksum kick and its CR control -- LIVE.

The boot IS the action: no bus call reaches a kicked client. The server holds TKX_ChecksumA
(`media/scripts/tkx_checksum.txt`, `Weight = 0.2`, LF) in every boot; the client's copy is passed
per side through `session.make_client(mod_sources=...)` (a profile cannot name a per-side source).

Three boots, one artifact (`checksum.json`, `phases.kick`, `phases.cr`, `phases.bypass`):

  kick    profile x17-checksum, client TKX_ChecksumB (`Weight = 0.3`: one byte, not a CR), the account
          demoted to the `user` role by RCON `setaccesslevel "admin" "user"` before the client starts,
          the client run WITHOUT -debug (a dedicated server refuses -debug for a non-admin account).
  cr      profile x17-checksum-cr, client TKX_ChecksumCR (A's bytes with CRLF endings), the same demotion.
  bypass  profile x17-checksum, client TKX_ChecksumB, the account left in the fixture's `admin` role,
          -debug as every harness boot.

WHY THE DEMOTION (added by the implementer before the run, from the jar): `ChecksumPacket.parseServer
@118-@143 L234-L235` sets all three ok flags when the connection's role holds
`Capability.BypassLuaChecksum`, and `Roles.addStatic` builds the `admin` role from
`Capability.values()` ("Have all capabilities.", @969-@1039 L447). The fixture's only account is
`admin`, so the profile as built would read the bypass, not the kick. The kick and its CR control
run under the `user` role so the control discriminates; the third boot reads the bypass (#1230).

The jar's four `ChecksumPacket.getReason(B)` strings (`@28-@49 L379-L388`), matched against the
client console:
  "File doesn't match the one on the server" / "File doesn't exist on the server" /
  "File doesn't exist on the client" / "File status unknown".
The server arms: `ChecksumPacket.parseServer @208-@223 L244` (a Multiplayer warn naming the user and
the timeout), `AntiCheat.log @291 L255`, `ServerWorldDatabase.addUserlog @314 L256` (the userlog row),
and `AntiCheatChecksumUpdate.isDifferentChecksumTimeoutExpired @29-@34 L19`
("Timed out connection because checksum was different") after `DIFFERENT_CHECKSUM_STATE_TIMEOUT`.
The client arm: `NetChecksum$Comparer.update @62-@85 L213-L215` (forceDisconnect, serverDisconnected,
kickReason).

PREDICTIONS (the brief's, recorded for grading; never cited): kick -- the client is disconnected and
never reaches `ready`; the server log carries the timeout line at or after 60 s from the connect; a
userlog row of type LuaChecksum. cr -- connects, `lua.global TK.version` answers on the client at
ready and again after 90 s, no checksum line in either log. bypass -- connects (the jar's role
bypass).

`pzt run` is not run: a profile hands both sides the same source, so its own verdict could only read
A against A; the driver's per-boot verdict replaces it.

**The two rules a driver never breaks.**
  1. A driver is NEVER edited after its run; a post-run edit is a skew note.
  2. A reading that comes back trivial, unmeasured or falsified is written as such, never re-run.
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

from _common import ask, doctor, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile               # noqa: E402
from pzt.paths import new_run_dir                    # noqa: E402
from pzt.session import Timeline, make_client, make_server, teardown   # noqa: E402

SESSION = ("Plan 6 X16: the one-byte script checksum mismatch (kick, user role), the CRLF-only control "
           "(cr, user role) and the admin-role bypass (bypass): three boots of the default fixture")
ARTIFACT = "checksum.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = "TKX_Checksum"
SRC = {k: os.path.join(REPO, "testing", "experiments", f"TKX_Checksum{k}") for k in ("A", "B", "CR")}
REASONS = ("File doesn't match the one on the server", "File doesn't exist on the server",
           "File doesn't exist on the client", "File status unknown")
OBS_S = 180.0          # kick: wall seconds observed from client start
HOLD_AFTER_READY = 90.0   # cr/bypass: seconds held past ready (the 60 s grace + margin)
READY_MAX = 180.0
CHK_SRV = re.compile(r"checksum|AntiCheat|LuaChecksum|kick|disconnect|File doesn|File status|"
                     r"access ?level|role|ConnectionManager|logged|login|connected|setaccesslevel", re.I)
CHK_CLI = re.compile(r"checksum|kick|disconnect|File doesn|File status|AntiCheat|forceDisconnect|"
                     r"serverDisconnected|STATE: enter|ConnectionManager|connection lost|"
                     r"Connection failed|access|LuaChecksum", re.I)
LINE_CAP = 300
INI_RX = re.compile(r"^(DoLuaChecksum|AntiCheatChecksum|Open|AutoCreateUserInWhiteList)=(.*)$")

run_id, run_dir = new_run_dir("x171c")
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []


def wall():
    return round(time.time() - t0, 3)


out = {
    "run_id": run_id, "session": SESSION, "user": USER,
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "probe_commits": {k: git_say("log", "-1", "--format=%h", "--", f"testing/experiments/TKX_Checksum{k}")
                      for k in SRC},
    "reasons_jar": list(REASONS),
    "predictions": {"kick": "disconnected, never ready; timeout line >= 60 s after connect; LuaChecksum userlog row",
                    "cr": "connects; TK.version at ready and +90 s; no checksum line",
                    "bypass": "connects (admin role holds BypassLuaChecksum)"},
    "deviations": [
        "Three boots, not two: the fixture's account is admin, whose role holds BypassLuaChecksum (jar), so "
        "the kick and the CR control run with the account demoted to the user role by RCON setaccesslevel, "
        "and a third boot reads the admin bypass.",
        "The demoted boots run the client without -debug (a non-admin account is refused -debug).",
        "pzt run is not run: a profile cannot give the client a different source.",
    ],
    "phases": {}, "notes": [],
}


def persist():
    try:
        out["timeline"] = list(tl.items)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001
        print(f"could not write {path}: {type(e).__name__}: {e}")


class Tail:
    """Stamps each new line of a log with the driver's wall clock; keeps the matches (capped) and the
    total line count. A file truncated under us restarts at 0."""

    def __init__(self, fname, rx):
        self.fname, self.rx, self.pos, self.n, self.hits, self.capped = fname, rx, 0, 0, [], False

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
                if self.rx.search(line):
                    if len(self.hits) < LINE_CAP:
                        self.hits.append({"wall": w, "n": self.n, "text": line.strip()[:260]})
                    else:
                        self.capped = True
        except Exception as e:                 # noqa: BLE001
            out["notes"].append({"wall": wall(), "tail_error": f"{type(e).__name__}: {e}"})

    def report(self):
        return {"file": self.fname, "lines_read": self.n, "cap": LINE_CAP, "capped": self.capped,
                "hits": self.hits}


def file_facts(root):
    rows = []
    for p in glob.glob(os.path.join(root, "**", "tkx_checksum.txt"), recursive=True):
        with open(p, "rb") as fh:
            b = fh.read()
        rows.append({"path": os.path.relpath(p, root), "size": len(b), "cr": b.count(b"\r"),
                     "sha256": hashlib.sha256(b).hexdigest(),
                     "md5_cr_stripped": hashlib.md5(b.replace(b"\r", b"")).hexdigest()})
    return rows


def db_rows(root):
    res = []
    for p in glob.glob(os.path.join(root, "server", "**", "*.db"), recursive=True):
        row = {"db": os.path.relpath(p, root), "tables": None, "userlog": None, "whitelist_admin": None}
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            row["tables"] = tabs
            for t in tabs:
                if t.lower() == "userlog":
                    cur = con.execute(f"select * from {t}")
                    cols = [d[0] for d in cur.description]
                    row["userlog"] = {"cols": cols, "rows": [list(map(str, r)) for r in cur.fetchall()][:50]}
                if t.lower() == "whitelist":
                    cur = con.execute(f"select * from {t}")
                    cols = [d[0] for d in cur.description]
                    row["whitelist_admin"] = {"cols": cols, "rows": [
                        [str(x) for x in r] for r in cur.fetchall() if "admin" in [str(x) for x in r]][:5]}
            con.close()
        except Exception as e:                 # noqa: BLE001
            row["error"] = f"{type(e).__name__}: {e}"
        res.append(row)
    return res


def read_ini(srv):
    vals = {}
    try:
        with open(srv.ini, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = INI_RX.match(line.strip())
                if m:
                    vals[m.group(1)] = m.group(2)
    except Exception as e:                     # noqa: BLE001
        vals["error"] = f"{type(e).__name__}: {e}"
    return vals


def boot(name, prof_name, client_src, demote, debug):
    global server, client, clients
    prof = profile.load(prof_name)
    rec = fx.load(prof.fixture)
    ph = {"name": name, "profile": prof.report(), "client_source": os.path.relpath(SRC[client_src], REPO),
          "server_source": os.path.relpath(prof.sources.get(MOD), REPO) if prof.sources.get(MOD) else None,
          "demote": demote, "client_debug": debug}
    out["phases"][name] = ph
    client, clients = None, []
    ok, text = doctor()
    ph["doctor_clean"], ph["doctor"] = ok, text.strip().splitlines()
    if not ok:
        ph["error"] = "doctor not clean; boot not started (CLAUDE.md s5)"
        persist()
        return
    sub = os.path.join(run_dir, name)
    os.makedirs(sub, exist_ok=True)
    server = make_server(sub, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    stail = Tail(server.log_path, CHK_SRV)
    ctail = None
    try:
        server.start(timeout=prof.server_timeout)
        ph["server_started_wall"] = wall()
        tl.mark("server_started", stage=name)
        ph["ini"] = read_ini(server)
        if demote:
            okr, rep = server.rcon(f'setaccesslevel "{USER}" "user"')
            ph["setaccesslevel"] = {"wall": wall(), "ok": okr, "reply": str(rep)[:300]}
            tl.mark("setaccesslevel", ok=okr, reply=str(rep)[:80])
        csrc = dict(prof.sources)
        csrc[MOD] = SRC[client_src]
        client, _ = make_client(sub, USER, server, rec, debug=debug, mod_sources=csrc)
        clients = [client]
        ph["files"] = file_facts(sub)
        ctail = Tail(client.console, CHK_CLI)
        stail.poll()
        client.start()
        ph["client_start_wall"] = wall()
        tl.mark("client_start", stage=name)
        last_click, alive_prev, ready_wall = 0.0, True, None
        reads = []
        deadline = time.time() + (OBS_S if name == "kick" else READY_MAX)
        while time.time() < deadline:
            stail.poll()
            ctail.poll()
            alive = client.alive
            if alive != alive_prev:
                ph.setdefault("alive_changes", []).append({"wall": wall(), "alive": alive})
                alive_prev = alive
            if "ready" in client.seen and ready_wall is None:
                ready_wall = wall()
                ph["ready_wall"] = ready_wall
                tl.mark("ready", stage=name)
                r = ask(client, "lua.global", "TK.version")
                reads.append({"tag": "at_ready", "wall": wall(), "reply": r})
                if name != "kick":
                    deadline = time.time() + HOLD_AFTER_READY
            if "in_game" in client.seen and "ready" not in client.seen and time.time() - last_click > 2.0 \
                    and alive:
                last_click = time.time()
                try:
                    client.click_to_start()
                except Exception as e:         # noqa: BLE001
                    ph.setdefault("click_errors", []).append(str(e)[:120])
            time.sleep(0.25)
        if ready_wall is not None and client.alive:
            r = ask(client, "lua.global", "TK.version")
            reads.append({"tag": "end_of_window", "wall": wall(), "reply": r})
        stail.poll()
        ctail.poll()
        ph["reads"] = reads
        ph["window_end_wall"] = wall()
        ph["client_alive_at_end"] = client.alive
        ph["client_seen"] = dict(client.seen)
        ph["client_events"] = client.events[:200]
        ph["client_t0_wall"] = round(client.t0 - t0, 3)
    except Exception as e:                     # noqa: BLE001
        ph["error"], ph["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", stage=name, detail=str(e)[:200])
    finally:
        persist()
        try:
            teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            ph["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            hard_kill(server, clients)
        stail.poll()
        if ctail is not None:
            ctail.poll()
        ph["server_log"] = stail.report()
        ph["client_log"] = ctail.report() if ctail else None
        ph["server_errors"] = server.errors[:20]
        ph["server_error_count"] = len(server.errors)
        ph["reason_hits"] = {r: {"client": [h for h in (ctail.hits if ctail else []) if r in h["text"]][:5],
                                 "server": [h for h in stail.hits if r in h["text"]][:5]} for r in REASONS}
        ph["db"] = db_rows(sub)
        persist()


try:
    boot("kick", "x17-checksum", "B", True, False)
    boot("cr", "x17-checksum-cr", "CR", True, False)
    boot("bypass", "x17-checksum", "B", False, None)
    s = {}
    for name, ph in out["phases"].items():
        reads = ph.get("reads") or []
        s[name] = {"ready_wall": ph.get("ready_wall"), "client_start_wall": ph.get("client_start_wall"),
                   "tk_version_reads": [(r["tag"], (r["reply"] or {}).get("value")
                                         if isinstance(r["reply"], dict) else r["reply"]) for r in reads],
                   "client_alive_at_end": ph.get("client_alive_at_end"),
                   "timeout_line": [h for h in (ph.get("server_log") or {}).get("hits", [])
                                    if "Timed out connection because checksum was different" in h["text"]][:3],
                   "reasons_client": {r: len(v["client"]) for r, v in (ph.get("reason_hits") or {}).items()},
                   "setaccesslevel": ph.get("setaccesslevel"), "error": ph.get("error")}
    out["summary"] = s
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:6000])
