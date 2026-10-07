"""x201-release -- Plan 9 Task 4, live 1, ONE boot of profile `x20-release` on fixture `two` with TWO clients: `admin`
(-debug) and `bob` (a RELEASE client, no -debug: fixture two's record `clients.bob.debug = false`), attached one at a
time through pzt.session.attach_clients (each ready before the next launches). PZTestKit + the STAGED 1.0.0 build
(release/NutritionRevamp/Contents/mods/NutritionRevamp, written by `python tools/release_pack.py stage
mod/NutritionRevamp --out release` before the boot); Nutrition false; DayLength 1; no [sandbox.NR] block (every NR
option at its sandbox-options.txt default: Mode 1 takeover, LogLevel 2, LegacyMirror true). ONE artifact
`release.json`, plus the staged MANIFEST.json copied byte-identical beside it. Shape: x193_two_clients.py (step, keep,
gread, persist, run_phase, grade, the echo-excluding log greps, make_server + attach_clients, the artifact copied by
the driver). Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5,
B3-1/B3-2). A two-client run is one session.

BUILD UNDER TEST (Task 4 build block): HEAD 1a8e207; the mod tree at 5dbd63a + the Task 2 fix at 1a8e207 (the shipped
docs only); tools/release_pack.py at 3f2607d; the lint gate at 78ba25b. The driver lints the staged folder itself
(pzt.harness.lint_paths, the gate `pzt run` applies) and stops on an ERROR before any process starts.

READ ORDER: every paired read is `client:bob` first, `client:admin` second, the server third.

PHASES (run order D, S0, E, F, Z; A, B and C are read off the logs after teardown and graded there):
  D  the manifest check (offline, before the boot): release/NutritionRevamp/MANIFEST.json copied into the run folder
     byte-identical; sha256 over every file under the staged mod folder and over the same relative path under
     mod/NutritionRevamp/, equal/unequal per file; the files under mod/NutritionRevamp/ with no staged twin; each
     manifest entry's sha256 against the staged file's; after the boot, the same hashes over the copies the harness
     placed in the server's and each client's mods/NutritionRevamp.
  S0 the load: the ready marks (client_launch / client_ready per user); the verify rows; the server's players list.
  E  a paired read of NutritionRevamp.version and NutritionRevamp.build on bob, admin, the server.
  F  lua.global NutritionRevamp.itemPassActive on the server (its type only, never called); item.script Base.Acorn
     on bob, admin and the server (the script item's Calories as the harness's getter route reads it; the pass
     re-bases Base.Acorn to 109.71 kcal, vanilla's script says 55.0).
  Z  the mod-error check: the server's errors filtered to the mod's files; admin's lua_error marker.
  After teardown, each log grepped with the bus's `PZTK: ` echo lines dropped first (CLAUDE.md s5; the patterns below
  match no probe name this driver sends: no probe carries `NutritionRevamp v`, `Connected new client`, `first sight`
  or `checksum`):
  A  the server self-report: lines matching SELF_SRV_RX in the server log; the first parsed into key=value pairs.
  B  each client's self-report: lines matching SELF_CLI_RX in each console; the first parsed the same way.
  C  bob's join: the server log's connection lines (CONN_RX: `Connected new client`, the mod's `players: first sight
     of <user>` and `<user> left` lines); every line matching CHECKSUM_RX (case-insensitive `checksum`) in the server
     log and in bob's console, with the subset matching CHECKSUM_BAD_RX (mismatch, differ, kick, disconnect, fail);
     the join wall time per client from the timeline's client_launch and client_ready marks.

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured):
  D   every staged file has a repository twin and every pair is equal; no repository file is missing from the stage;
      every manifest sha256 equals the staged file's; the three deployed copies equal the stage.
  S0  both clients ready; every verify row ok; the players list holds admin and bob.
  E   version "1.0.0" and build "42.20.4" on bob, admin and the server.
  F   itemPassActive type function on the server; Base.Acorn Calories 109.71 (within 0.01) on all three sides.
  Z   no mod error line on the server; admin not parked.
  A   exactly one server self-report line; side=server, mode=takeover, itemPass=true, legacyMirror=on,
      frameworks=n/a, nutritionOn=false, log=2; hook and limitations recorded, not graded.
  B   one client self-report line on each console; side=client, mode=takeover, itemPass=true, frameworks=none
      (no MoodleFramework on this fixture), log=2.
  C   a `Connected new client` line per client and a `first sight of bob` line; no CHECKSUM_BAD_RX line on the server
      or on bob's console (the boot's own `Checksum: Warning` level line and the scriptChecksum / luaChecksum prints
      are recorded, not graded); bob ready and in the players list.
A parked -debug admin (the lua_error marker) stops the remaining live phases; bob cannot park (no debugger).
An itemPass=unread or itemPass=false is a FINDING (the line carries no reason), never a re-run.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
"""
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

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.bus import resolve_side                                # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, attach_clients,              # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x20-release"
PREFIX = "x201"
SESSION = ("Plan 9 Task 4, live 1: the staged 1.0.0 build on fixture two -- the server and client self-reports, "
           "bob's join with no checksum line, the staged bytes against the repository's, the version on all three "
           "sides; one boot of " + PROFILE)
ARTIFACT = "release.json"
MANIFEST_NAME = "MANIFEST.json"
BOB = "client:bob"
ADMIN = "client:admin"
SRV = "server"
CLIENT_SIDES = (BOB, ADMIN)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
STAGE_ROOT = "release/NutritionRevamp"
STAGE_MOD = "release/NutritionRevamp/Contents/mods/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
NR = "NutritionRevamp"
MOD_ID = "NutritionRevamp"
SENTINEL = "Base.Acorn"
SENTINEL_KCAL = 109.71
EXPECT_VERSION = "1.0.0"
EXPECT_BUILD = "42.20.4"
SELF_SRV_RX = re.compile(r"NutritionRevamp v1\.0\.0 build \S+ side=server .*")
SELF_CLI_RX = re.compile(r"NutritionRevamp v1\.0\.0 build \S+ side=client .*")
PAIR_RX = re.compile(r"(\w+)=(\S+)")
CONN_RX = re.compile(r"Connected new client|players: first sight of |\[NutritionRevamp\] players: \w+ left")
CHECKSUM_RX = re.compile(r"checksum", re.I)
CHECKSUM_BAD_RX = re.compile(r"mismatch|differ|kick|disconnect|fail", re.I)
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
LOG_LIMIT = 200
ECHO_RX = re.compile(r"PZTK: ")            # the bus's own echo of every command and reply (CLAUDE.md s5)
MOD_LINE_RX = re.compile(r"\[NutritionRevamp\]")
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")
SRV_PRED = {"side": "server", "mode": "takeover", "itemPass": "true", "legacyMirror": "on", "frameworks": "n/a",
            "nutritionOn": "false", "log": "2"}
CLI_PRED = {"side": "client", "mode": "takeover", "itemPass": "true", "frameworks": "none", "log": "2"}

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, clients, started = None, {}, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_files(root):
    """Every file under root as a sorted list of forward-slash relative paths."""
    outl = []
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            outl.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    return sorted(outl)


PRED = {
    "D": {"staged files with a repo twin": "all", "pairs equal": "all", "repo files missing from the stage": 0,
          "manifest sha256 equal to the staged file": "all", "deployed copies equal to the stage": "server, admin, bob"},
    "S0": {"both_ready": True, "verify": "every row ok", "players": ["admin", "bob"]},
    "E": {"version": {"bob": EXPECT_VERSION, "admin": EXPECT_VERSION, "server": EXPECT_VERSION},
          "build": {"bob": EXPECT_BUILD, "admin": EXPECT_BUILD, "server": EXPECT_BUILD}},
    "F": {"server itemPassActive type": "function", "Base.Acorn Calories": f"{SENTINEL_KCAL} +- 0.01 on bob, admin, server"},
    "Z": {"mod_error": "none", "admin_lua_error": False},
    "A": {"server self-report lines": 1, "pairs": SRV_PRED, "hook/limitations": "recorded, not graded"},
    "B": {"client self-report lines": {"bob": 1, "admin": 1}, "pairs": CLI_PRED},
    "C": {"connected lines": ">= 2", "first sight of bob": ">= 1", "checksum bad lines": {"server": 0, "bob": 0},
          "bob ready": True, "bob in players": True},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "users": list(prof.users), "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                "clients": {u: {"debug": (rec_fx.get("clients") or {}).get(u, {}).get("debug")}
                            for u in (rec_fx.get("clients") or {})}},
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty": git_dirty(MOD_DIR)[0],
    "release_tool_commit": git_say("log", "-1", "--format=%h", "--", "tools/release_pack.py"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "meta": {"staged_mod": STAGE_MOD, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
             "staging_command": "python tools/release_pack.py stage mod/NutritionRevamp --out release"},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "PRED")},
    "predictions": PRED,
    "deviations": [
        "Phases A, B and C are read off the server log and the client consoles after teardown (the self-report lines "
        "print once, at OnServerStarted and OnGameStart, before any probe can run); their verdicts are graded there.",
        "Phase F reads the script item's Calories through the harness's item.script getter route; the mod's own "
        "sentinel reads a fresh instance's Food.getCalories (#2680), so the two routes are not the same read.",
        "The driver runs the layout lint itself (pzt.harness.lint_paths, the gate pzt run applies) because it builds "
        "the session through make_server rather than pzt run.",
    ],
    "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
    "mod_error_checks": [],
}


def grep_noecho(log, rx, limit):
    """The bus's echo lines dropped BEFORE the limit counts: (kept lines, echo lines skipped)."""
    hits, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append(line.strip()[:600])
                if len(hits) >= limit:
                    break
    except OSError:
        pass
    return hits, skipped


def note(msg):
    out["notes"].append({"wall": wall(), "phase": cur_phase["name"], "note": msg})


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


def node(side):
    return resolve_side(side, server, clients)


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    try:
        n = node(side)
        v = ask(n, cmd, args, timeout=timeout)
    except Exception as e:                     # noqa: BLE001 - an unknown side is a recorded fault
        v = {"error": f"{type(e).__name__}: {e}"}
    t_after = wall()
    row = {"step": name, "side": side, "cmd": cmd, "args": args, "phase": cur_phase["name"],
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": v}
    if not isinstance(v, dict):
        row["ack_shape"] = type(v).__name__
    out["steps"].append(row)
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    a["side"] = a.get("side", r["side"])
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def gread(side, name, tag):
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    row = {"name": name, "side": side, "wall": r["wall_before"], "wall_after": r["wall_after"],
           "resolved": a.get("resolved"), "type": a.get("type")}
    for k in ("value", "keyCount", "failedAt", "stoppedOn", "error"):
        if k in a:
            row[k] = a.get(k)
    if not isinstance(r.get("ack"), dict):
        row["raw"] = r.get("ack")
    return row


def val(row):
    if not isinstance(row, dict) or not row.get("resolved"):
        return None
    return row.get("value")


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def who(side):
    return side.split(":", 1)[1] if side.startswith("client:") else side


def parked():
    c = clients.get("admin") if isinstance(clients, dict) else None
    return c is not None and "lua_error" in getattr(c, "seen", {})


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


def parse_pairs(line):
    """`key=value` pairs after `side=` in a self-report line, plus the version and build words."""
    m = re.search(r"NutritionRevamp v(\S+) build (\S+) (side=.*)$", line)
    if not m:
        return None
    d = {"version": m.group(1), "build": m.group(2)}
    for k, v in PAIR_RX.findall(m.group(3)):
        d[k] = v
    return d


# ---------------------------------------------------------------- phases
def phase_D():
    """Offline: the staged files against the repository's, and the manifest against the staged files."""
    P = out["phases"]["D"] = {}
    stage_abs, repo_abs = os.path.join(REPO, STAGE_MOD), os.path.join(REPO, MOD_DIR)
    man_src = os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME)
    man_dst = os.path.join(run_dir, MANIFEST_NAME)
    shutil.copyfile(man_src, man_dst)
    P["manifest_sha256"] = sha256_file(man_src)
    P["manifest_copy_sha256"] = sha256_file(man_dst)
    with open(man_src, encoding="utf-8") as fh:
        manifest = json.load(fh)
    out["meta"]["staged_manifest_sha256"] = P["manifest_sha256"]
    staged, repo = tree_files(stage_abs), tree_files(repo_abs)
    files = {}
    for rel in staged:
        s = sha256_file(os.path.join(stage_abs, rel))
        rp = os.path.join(repo_abs, rel)
        r = sha256_file(rp) if os.path.isfile(rp) else None
        m = manifest.get(rel) if isinstance(manifest, dict) else None
        ms = m.get("sha256") if isinstance(m, dict) else None
        files[rel] = {"staged": s, "repo": r, "equal": (r is not None and r == s), "manifest": ms,
                      "manifest_equal": ms == s}
    P["files"] = files
    P["staged_count"] = len(staged)
    P["repo_count"] = len(repo)
    P["equal_count"] = sum(1 for f in files.values() if f["equal"])
    P["unequal"] = sorted(k for k, f in files.items() if not f["equal"])
    P["repo_only"] = sorted(set(repo) - set(staged))
    P["manifest_count"] = len(manifest) if isinstance(manifest, dict) else None
    P["manifest_equal_count"] = sum(1 for f in files.values() if f["manifest_equal"])
    P["manifest_only"] = sorted(set(manifest) - set(staged)) if isinstance(manifest, dict) else None


def phase_D_deployed():
    """After the boot: the copies the harness placed in each cache's mods/NutritionRevamp against the stage."""
    P = out["phases"]["D"]
    files = P.get("files") or {}
    dep = {}
    for cand in sorted(glob.glob(os.path.join(run_dir, "**", "mods", MOD_ID), recursive=True)):
        if not os.path.isdir(cand):
            continue
        rel_dir = os.path.relpath(cand, run_dir).replace(os.sep, "/")
        fl = tree_files(cand)
        eq = sum(1 for rel in fl if rel in files and sha256_file(os.path.join(cand, rel)) == files[rel]["staged"])
        dep[rel_dir] = {"count": len(fl), "equal_count": eq,
                        "missing": sorted(set(files) - set(fl)), "extra": sorted(set(fl) - set(files))}
    P["deployed"] = dep


def phase_S0():
    P = out["phases"]["S0"] = {}
    P["ready"] = [it for it in tl.items if it.get("phase") in ("client_launch", "client_ready")]
    P["players"] = keep(step("S0_players", SRV, "players"))
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}


def phase_E():
    P = out["phases"]["E"] = {}
    for side in CLIENT_SIDES + (SRV,):
        P[who(side)] = {"version": gread(side, f"{NR}.version", f"E_{who(side)}_ver"),
                        "build": gread(side, f"{NR}.build", f"E_{who(side)}_build")}


def phase_F():
    P = out["phases"]["F"] = {}
    P["server_itemPassActive"] = gread(SRV, f"{NR}.itemPassActive", "F_srv_ipa")
    P["acorn"] = {}
    for side in CLIENT_SIDES + (SRV,):
        P["acorn"][who(side)] = keep(step(f"F_{who(side)}_acorn", side, "item.script", SENTINEL))


def phase_Z():
    P = out["phases"]["Z"] = {}
    errs = [str(e) for e in (server.errors if server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)][:10]
    P["admin_parked"] = parked()
    P["seen"] = {who(s): dict(getattr(node(s), "seen", {})) for s in CLIENT_SIDES}


def body():
    for name, fn in (("S0", phase_S0), ("E", phase_E), ("F", phase_F), ("Z", phase_Z)):
        run_phase(name, fn)
        if parked() and name != "Z":
            out["abort"] = f"admin parked in the debugger after phase {name}"
            run_phase("Z", phase_Z)
            return


def read_logs(every):
    """After teardown: the self-report lines, the connection lines and the checksum lines, echo lines dropped."""
    L = out["logs"] = {"patterns": {"self_server": SELF_SRV_RX.pattern, "self_client": SELF_CLI_RX.pattern,
                                    "conn": CONN_RX.pattern, "checksum": CHECKSUM_RX.pattern,
                                    "checksum_bad": CHECKSUM_BAD_RX.pattern, "log": LOG_RX.pattern,
                                    "mod": MOD_LINE_RX.pattern, "echo_excluded": ECHO_RX.pattern},
                       "limits": {"log": LOG_LIMIT}, "clients": {}}
    if server is not None:
        raw, echoed = grep_noecho(server.log_path, LOG_RX, LOG_LIMIT)
        mod_lines, _ = grep_noecho(server.log_path, MOD_LINE_RX, LOG_LIMIT)
        self_lines, self_echo = grep_noecho(server.log_path, SELF_SRV_RX, LOG_LIMIT)
        conn, conn_echo = grep_noecho(server.log_path, CONN_RX, LOG_LIMIT)
        cks, cks_echo = grep_noecho(server.log_path, CHECKSUM_RX, LOG_LIMIT)
        L["server"] = {"lines": raw, "echo_lines_excluded": echoed, "mod_lines": mod_lines,
                       "self_report_lines": self_lines, "self_report_echo_excluded": self_echo,
                       "conn_lines": conn, "conn_echo_excluded": conn_echo,
                       "checksum_lines": cks, "checksum_echo_excluded": cks_echo,
                       "checksum_bad_lines": [ln for ln in cks if CHECKSUM_BAD_RX.search(ln)]}
    for c in every:
        u = getattr(c, "username", "?")
        lines, ech = grep_noecho(c.console, LOG_RX, LOG_LIMIT)
        mlines, _ = grep_noecho(c.console, MOD_LINE_RX, LOG_LIMIT)
        sl, se = grep_noecho(c.console, SELF_CLI_RX, LOG_LIMIT)
        ck, ce = grep_noecho(c.console, CHECKSUM_RX, LOG_LIMIT)
        L["clients"][u] = {"lines": lines, "echo_lines_excluded": ech, "mod_lines": mlines,
                           "self_report_lines": sl, "self_report_echo_excluded": se,
                           "checksum_lines": ck, "checksum_echo_excluded": ce,
                           "checksum_bad_lines": [ln for ln in ck if CHECKSUM_BAD_RX.search(ln)]}


# ---------------------------------------------------------------- grading
def ready_walls():
    """Per user: the client_launch and client_ready timeline t, and the difference."""
    res = {}
    for it in tl.items:
        ph, u = it.get("phase"), it.get("user") or it.get("username")
        if ph in ("client_launch", "client_ready") and u:
            res.setdefault(u, {})[ph] = it.get("t")
            if ph == "client_ready" and it.get("took") is not None:
                res[u]["ready_took"] = it.get("took")
    for u, d in res.items():
        if d.get("client_launch") is not None and d.get("client_ready") is not None:
            d["launch_to_ready_s"] = round(d["client_ready"] - d["client_launch"], 3)
    return res


def grade_all():
    ph = out["phases"]
    D = ph.get("D") or {}
    if D.get("files") is not None:
        dep = D.get("deployed") or {}
        obs = {"staged_count": D.get("staged_count"), "repo_count": D.get("repo_count"),
               "equal_count": D.get("equal_count"), "unequal": D.get("unequal"), "repo_only": D.get("repo_only"),
               "manifest_count": D.get("manifest_count"), "manifest_equal_count": D.get("manifest_equal_count"),
               "manifest_only": D.get("manifest_only"),
               "deployed": {k: {"count": v["count"], "equal_count": v["equal_count"]} for k, v in dep.items()}}
        n = D.get("staged_count")
        ok = (n and D.get("equal_count") == n and not D.get("repo_only") and D.get("manifest_equal_count") == n
              and not D.get("manifest_only") and len(dep) >= 3
              and all(v["count"] == n and v["equal_count"] == n for v in dep.values()))
        grade("D", PRED["D"], obs, "as_predicted" if ok else "falsified",
              "a staged file differing from the repository's, a repository file not staged, a manifest hash off, a "
              "deployed copy differing")
    else:
        grade("D", PRED["D"], None, "unmeasured", "phase D not run")

    S = ph.get("S0") or {}
    rw = ready_walls()
    out["join_walls"] = rw
    if S:
        pl = json.dumps(S.get("players") or {})
        vr = out.get("verify") or []
        obs = {"ready": {u: (u in rw and rw[u].get("client_ready") is not None) for u in ("admin", "bob")},
               "verify_ok": [bool(v.get("ok")) for v in vr],
               "players_has": {u: (f'"{u}"' in pl) for u in ("admin", "bob")}}
        ok = (all(obs["ready"].values()) and vr and all(obs["verify_ok"]) and all(obs["players_has"].values()))
        grade("S0", PRED["S0"], obs, "as_predicted" if ok else "falsified",
              "a client not ready, a verify row failed, a user absent from the players list")
    else:
        grade("S0", PRED["S0"], None, "unmeasured", "phase S0 not run")

    E = ph.get("E") or {}
    if E:
        obs = {"version": {u: val((E.get(u) or {}).get("version")) for u in ("bob", "admin", "server")},
               "build": {u: val((E.get(u) or {}).get("build")) for u in ("bob", "admin", "server")}}
        ok = (all(v == EXPECT_VERSION for v in obs["version"].values())
              and all(v == EXPECT_BUILD for v in obs["build"].values()))
        grade("E", PRED["E"], obs, "as_predicted" if ok else "falsified", "a side reading another version or build")
    else:
        grade("E", PRED["E"], None, "unmeasured", "phase E not run")

    F = ph.get("F") or {}
    if F:
        ac = F.get("acorn") or {}
        obs = {"server_itemPassActive_type": (F.get("server_itemPassActive") or {}).get("type"),
               "acorn_calories": {u: num((ac.get(u) or {}).get("Calories")) for u in ("bob", "admin", "server")},
               "acorn_access": {u: (ac.get(u) or {}).get("access") for u in ("bob", "admin", "server")}}
        cals = list(obs["acorn_calories"].values())
        if all(c is None for c in cals):
            verdict = "unmeasured"
        else:
            ok = (obs["server_itemPassActive_type"] == "function"
                  and all(c is not None and abs(c - SENTINEL_KCAL) < 0.01 for c in cals))
            verdict = "as_predicted" if ok else "falsified"
        grade("F", PRED["F"], obs, verdict, "the function absent, a side reading the vanilla 55.0 or another value")
    else:
        grade("F", PRED["F"], None, "unmeasured", "phase F not run")

    Z = ph.get("Z") or {}
    if Z:
        obs = {"server_mod_error_lines": Z.get("server_mod_error_lines") or [],
               "admin_lua_error": out.get("admin_lua_error")}
        ok = not obs["server_mod_error_lines"] and not obs["admin_lua_error"]
        grade("Z", PRED["Z"], obs, "as_predicted" if ok else "falsified", "a mod error line, admin parked")
    else:
        grade("Z", PRED["Z"], None, "unmeasured", "phase Z not run")

    L = out.get("logs") or {}
    Ls = L.get("server") or {}
    if Ls:
        sl = Ls.get("self_report_lines") or []
        pairs = parse_pairs(sl[0]) if sl else None
        out["phases"]["A"] = {"line_count": len(sl), "line": sl[0] if sl else None, "pairs": pairs}
        if pairs is None:
            grade("A", PRED["A"], {"line_count": len(sl)}, "unmeasured" if not sl else "falsified",
                  "no server self-report line")
        else:
            obs = {"line_count": len(sl), "pairs": {k: pairs.get(k) for k in sorted(pairs)}}
            ok = len(sl) == 1 and all(pairs.get(k) == v for k, v in SRV_PRED.items())
            grade("A", PRED["A"], obs, "as_predicted" if ok else "falsified",
                  "itemPass not true, a flag other than the defaults, a second or no line")
    else:
        grade("A", PRED["A"], None, "unmeasured", "server log not read")

    Lc = L.get("clients") or {}
    if Lc:
        out["phases"]["B"] = {}
        obs = {"line_count": {}, "pairs": {}}
        ok = True
        for u in ("bob", "admin"):
            sl = (Lc.get(u) or {}).get("self_report_lines") or []
            pairs = parse_pairs(sl[0]) if sl else None
            out["phases"]["B"][u] = {"line_count": len(sl), "line": sl[0] if sl else None, "pairs": pairs}
            obs["line_count"][u] = len(sl)
            obs["pairs"][u] = {k: pairs.get(k) for k in sorted(pairs)} if pairs else None
            ok = ok and len(sl) == 1 and pairs is not None and all(pairs.get(k) == v for k, v in CLI_PRED.items())
        grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified",
              "itemPass not true on a client, a framework detected, a missing or doubled line")
    else:
        grade("B", PRED["B"], None, "unmeasured", "client consoles not read")

    if Ls:
        conn = Ls.get("conn_lines") or []
        bob_c = (Lc.get("bob") or {})
        pl = json.dumps((S.get("players") or {}))
        obs = {"connected_lines": sum(1 for ln in conn if "Connected new client" in ln),
               "first_sight_bob": sum(1 for ln in conn if "first sight of bob" in ln),
               "checksum_bad": {"server": len(Ls.get("checksum_bad_lines") or []),
                                "bob": len(bob_c.get("checksum_bad_lines") or [])},
               "checksum_lines": {"server": len(Ls.get("checksum_lines") or []),
                                  "bob": len(bob_c.get("checksum_lines") or [])},
               "bob_ready": (rw.get("bob") or {}).get("client_ready") is not None,
               "bob_in_players": '"bob"' in pl,
               "join_walls": rw}
        out["phases"]["C"] = {"conn_lines": conn, "server_checksum_lines": Ls.get("checksum_lines"),
                              "bob_checksum_lines": bob_c.get("checksum_lines")}
        ok = (obs["connected_lines"] >= 2 and obs["first_sight_bob"] >= 1 and obs["checksum_bad"]["server"] == 0
              and obs["checksum_bad"]["bob"] == 0 and obs["bob_ready"] and obs["bob_in_players"])
        grade("C", PRED["C"], obs, "as_predicted" if ok else "falsified",
              "a checksum mismatch or kick line, bob never connected or never first-seen")
    else:
        grade("C", PRED["C"], None, "unmeasured", "server log not read")


# ---------------------------------------------------------------- run
if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    persist()
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)
if out["mod_dirty"]:
    out["error"] = "mod/ not quiescent (git status --short mod/ not empty); the session was not started"
    persist()
    print(out["error"])
    sys.exit(1)
lint_errors = lint_paths(prof.sources)
out["lint_errors"] = lint_errors
if lint_errors:
    out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
    persist()
    print(json.dumps(lint_errors, indent=1))
    sys.exit(1)

run_phase("D", phase_D)

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    clients = attach_clients(run_dir, prof, server, rec_fx, tl, started=started)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                   "client_markers_s": {u: dict(getattr(c, "seen", {})) for u, c in clients.items()},
                   "client_debug": {u: getattr(c, "debug", None) for u, c in clients.items()},
                   "server_started_wall": out.get("server_started_wall"),
                   "session_ready_wall": out.get("session_ready_wall")}
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             **{u: sorted(set(c.mods_not_found)) for u, c in clients.items()}}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    every = list(started)
    try:
        if server is not None:
            teardown(tl, server, every)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, every)
        adm = clients.get("admin") if isinstance(clients, dict) else None
        out["admin_lua_error"] = ("lua_error" in getattr(adm, "seen", ())) if adm is not None else None
        out["client_seen"] = {getattr(c, "username", str(i)): dict(getattr(c, "seen", {})) for i, c in enumerate(every)}
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
        try:
            read_logs(every)
        except Exception as e:                 # noqa: BLE001
            out["logs_error"] = f"{type(e).__name__}: {e}"
        try:
            phase_D_deployed()
        except Exception as e:                 # noqa: BLE001
            out["phase_errors"]["D_deployed"] = {"error": f"{type(e).__name__}: {e}"}
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
            if os.path.isfile(os.path.join(run_dir, MANIFEST_NAME)):
                shutil.copyfile(os.path.join(run_dir, MANIFEST_NAME), os.path.join(dest_dir, MANIFEST_NAME))
            print(f"copied to {dest_dir}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest_dir}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
