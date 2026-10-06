"""x192-persist-mod -- Plan 8 Task 6, live 2: the mod's own record in the global table `NutritionRevamp.players` across a
reconnect, a clean restart, a respawn and a hard kill, a planted version-1 record's migration, and a control boot.
Profile `x19-persist` (PZTestKit + NutritionRevamp by path; Nutrition false; DayLength 1, a game-minute = 0.625 s wall;
no [sandbox.NR] block; sleep off). ONE artifact `persist.json`. Shape: x131_persist.py (several server boots in one
driver on ONE run dir, `make_server(reuse=True)`, the clean teardown, the hard kill by the started server's pid, the
file-change witness on global_mod_data.bin, the control on the restored fixture) with x191_gate_race.py's bus helpers
(step, keep, gread, the echo-excluding log reads). Written BEFORE the first boot with every prediction in it and never
edited after the run (CLAUDE.md s5, B3-1/B3-2).

BUILD UNDER TEST (Task 6 build block): HEAD 70f3cb1, mod/ quiescent at 0df50bb: Task 3's kernels (NR_Kernel_Store.lua:
K.store.VERSION 2, K.store.INPUTS, load / fillInPlace) at 1cf2a44 + bbfa4cc; Task 4's adapters (NR_Server_Store.lua's
S.get loading IN PLACE once per sight, S.forget on departure, the migration line `store: migrated <u> v<old> -> v<new>`
at log level 2; S.reset REPLACING the record on OnNewGame) at 2d4dc4d + 0df50bb.

THE READ SET is the kernel's own: K.store.INPUTS is read out of NR_Kernel_Store.lua by regex over its array literal
(the quoted strings between `K.store.INPUTS = {` and the closing brace), and a record's inputs are picked from a whole
record the way K.store.inputsOnly picks them (a `*` walks every key the record holds at that level; a JSON array is
walked with Lua's 1-based keys). The whole record is read in ONE bus call, `witness.moddata
global:NutritionRevamp.players <user>`, whose dotted key returns the record table itself, JSON-encoded by TK.json
(numbers through tostring, exact doubles; depth cap 8). Every value is a server read: the global table is never on a
client (#2416); the client reads are the mirror (`NutritionRevamp.client.mirror.*`, `received`), read client first
where both are read.

THE BOOTS (one server at a time; every client quit cleanly before a server quit, except the kill; the client caches are
FRESH fixture restores under <run>/c<label> -- pzt's restore_client copies into <dir>/clients/admin and refuses an
existing folder, so the reconnect's client gets its own folder c1b: a reconnect of the same account with a fresh client
cache, never a warm client; the client's Lua/layout.ini presence is read in c1 after its quit and in c1b before its
start):

  1   fresh restore into <run>/server.
      S0  the load: TK and NR versions, received, the record's v, store and reconcile stats, no migration line.
      A   the forced state: globalmoddata.setpath NutritionRevamp.players admin.nutrients.vitC.p 0.05 and
          admin.stomach.buffer.calories 123.5, each read back; WAIT_A_S (4 s, about six slow minutes); the record
          read whole (the INPUTS census); the client pulls one mirror (lua.call NutritionRevamp.client.requestMirror:
          the change push is held to one a minute) and reads nut_vitC_g.
      B   the reconnect (ruling 8): two plants first (driver additions decided before the run): admin.v 1 (the
          record's version set back to 1, so the reconnect's in-place load is a v1 -> v2 migration of a FULL record)
          and admin.zzProbe 1 (a field outside INPUTS, never touched by a step: the derived-on-read witness); read
          back. The client quits (rc); the server log is polled for `players: admin left` (cap DEPART_CAP_S); the
          record read whole once the walk has dropped admin (R_off: frozen, no step touches an offline record); a new
          client from c1b attaches; the log polled for the next `players: first sight of admin` and `store: migrated
          admin`; received polled to >= 1 on the new client, then nut_vitC_g, username, resets; the record read whole
          (R_on); reconcile.count.
      C   the planted v1 record and the quit state: lua.call NutritionRevamp.server.store.get bob 0 (a username that
          never joins: S.new lays the identity fields only, at v 2); setpath bob.v 1, bob.resets 5, bob.kineticsAge
          7.5 (two inputs) and bob.stomachFill 0.9 (a derived top-level field; deviation: the amendments' bob.nutrients
          .vitC.p and .g cannot be planted because globalmoddata.setpath creates no table and bob's record has no
          nutrients table; and g is an INPUT under ruling T3-1, not a derived field); bob read whole. A second probe
          admin.zzProbe 2. The client quits; `players: admin left` awaited; admin and bob read whole (R_quit, the frozen
          state the quit saves); then the clean teardown (server quit), its `Saving GlobalModData` line and the file
          change seen by the sampler.
  2   reuse boot on <run>/server.
      pre  BEFORE the client attaches: admin and bob read whole from the table the file carried (no S.get has run
           for either: OnInitGlobalModData attaches the table, the walk loads only online players).
      bob  lua.call NutritionRevamp.server.store.get bob 0 (its first load in this Lua state); bob read whole; the
           store stats; the log polled for `store: migrated bob v1 -> v2`.
      on   the client attaches (c2); `players: first sight of admin` awaited; received polled; nut_vitC_g; the record
           read whole after WAIT_ON_S; no `store: migrated admin` line on this boot; reconcile.count.
      F/D  the death and the respawn (ruling 9). The route read before the run: the harness's server `health.reduce
           admin 110` calls BodyDamage:ReduceGeneralHealth(110), the engine's own fatal move (#2348), and a character
           at or below zero health is killed by die() on the server (#2349); the vanilla client then builds
           ISPostDeathUI (ISPostDeathUI.lua:219-247, OnPlayerDeath) at ISPostDeathUI.instance[playerNum]; its
           onRespawn (:149, self only) opens CoopCharacterCreation:newPlayerMouse (CoopCharacterCreation.lua:287): the
           spawn list (CoopMapSpawnSelect, whose NEXT and the profession screen's NEXT the harness's own creation
           driver presses -- PZTestKit_Client.lua:47-62, its step flags unset on a restored client that never created)
           and then the coop appearance screen, which the harness does not press (it reads MainScreen.instance.
           charCreationMain, the menu's own screen), so the driver calls CoopCharacterCreation.instance:accept() (no
           argument, :74) through lua.callm, which sets the player description and calls setPlayerMouse(nil): the new
           character is created and its CreatePlayer packet fires OnNewGame on the server (#2411), where the mod's
           S.reset logs `store: reset record for admin (reset 1)`.
           Steps: health.reduce admin 110; the server's witness.chain admin isDead polled; the log polled for
           `players: admin is dead`; the record's dead read (F); the client polled for ISPostDeathUI.instance.0
           (lua.callm ... getIsVisible); lua.callm ISPostDeathUI.instance.0 onRespawn; the screens' visibility polled
           (CoopMapSpawnSelect.instance, CharacterCreationProfession.instance, CharacterCreationMain.instance) for up to
           CREATE_CAP_S; if the spawn list is still visible at the cap the driver calls CoopMapSpawnSelect.instance
           clickNext; then CoopCharacterCreation.instance accept; the log polled for `store: reset record for admin`
           (cap RESPAWN_CAP_S); received polled to +1; the mirror's resets, nut_vitC_g, firstSeen; the record read
           whole (dead, resets, vitC.p, firstSeen); reconcile.count. If the death or the post-death UI never comes, the
           arm is UNMEASURED and says which step failed.
      E    the kill write: setpath admin.nutrients.vitC.p 0.07 and admin.zzKill 1, read back; KILL_WAIT_S (3 s, about
           five slow minutes); the client killed first, then the server process the driver started hard-killed by its
           pid (Server.kill: taskkill /PID <pid> /T /F; precedent x131p), walls stamped; no teardown.
  3   reuse boot after the kill: admin and bob read whole BEFORE the client attaches (the file's state); the client
      (c3) attaches; the first-sight and any reset lines and the record recorded (whether the server's player store
      kept a living character after the kill is the engine's and is recorded, not graded); clean teardown.
  4   the control: a FRESH restore into <run>/boot4/server; admin read before the client attaches (absent); the
      client (c4) attaches; the record read whole: new.

Throughout, a sampler thread stats the current server's Saves/Multiplayer/pzt/global_mod_data.bin every SAMPLE_S s
(exists, size, mtime_ns, sha256 head, whether its bytes hold `zzProbe`, `zzKill`, `bob`) and tails the current boot's
server log, keeping every `[NutritionRevamp]` line and every `Saving GlobalModData` line with the wall it was first
seen, the bus's own `PZTK: ` echo lines dropped first (CLAUDE.md s5: a driver's log pattern excludes its own probes).

PREDICTIONS (graded in `verdicts` with as_predicted / falsified / trivial / unmeasured):
  S0   server_error_count 0 on the boot; no client lua_error; received >= 1; the record's v "2"; store created 1,
       migrations 0, failures 0; no `store: migrated` line; reconcile.count 0.
  A    both setpaths ok (vitC.p before about 0.99, after 0.05; the buffer key after 123.5); after the wait the record's
       nutrients.vitC.g 4 and p below 0.06 (x183: g 4 within seconds of the same write); the pulled mirror's
       nut_vitC_g 4.
  B    the departure line `players: admin left` within DEPART_CAP_S of the quit, then `players: first sight of admin`
       after the new client attaches, in that order; `store: migrated admin v1 -> v2` logged once at that sight;
       R_on: v 2, zzProbe ABSENT (dropped by the in-place load), every concrete INPUTS path R_off holds present in
       R_on, resets 0, username admin, firstSeen equal to R_off's, lastSeen greater than R_off's, nutrients.vitC.p
       below 0.06 and vitC.g 4 (both inputs, kept); the new client's received >= 1 with the mirror's nut_vitC_g 4,
       username admin, resets 0; reconcile.count 0. The layout.ini check: c1b's absent before its start (a fresh
       cache).
  C    the bob record created with 6 keys (K.store.new's identity fields); the four setpaths ok.
  RESTART (boot 2 pre vs boot 1 R_quit): every leaf of admin's record read before the client attaches equals R_quit's
       (exact doubles: the table save writes doubles), so every concrete INPUTS path compared is equal -- the count of
       paths compared is the claim's number; zzProbe 2 PRESENT in the file's table (the save holds the whole table;
       derived is dropped on READ, not on save); v 2. Boot 1's quit logs one `Saving GlobalModData` line and moves
       the file (#2756).
  DERIVED (boot 2 on): after the first sight zzProbe ABSENT, v 2, every INPUTS path the pre read held present, no
       `store: migrated admin` line on boot 2, vitC.g 4 and p below 0.06, the mirror's nut_vitC_g 4. (Derived fields
       before the first minute are not separable at this clock: the first sight's load and the first minute's work
       are a few ticks apart; the amendments' `g read 0 before the minute` does not apply: g is an INPUT, T3-1.)
  MIGRATE (bob): the pre read v 1, resets 5, kineticsAge 7.5, stomachFill 0.9 (the file carried the plant); after
       store.get: v 2, resets 5, kineticsAge 7.5, stomachFill ABSENT, firstSeen 0 kept; one `store: migrated bob v1
       -> v2` line; store.stats.migrations >= 1.
  F    after health.reduce admin 110 the server's isDead true within DEATH_CAP_S; the walk logs `players: admin is
       dead; record kept until respawn`; the record's dead true, resets 0, vitC.p still below 0.06 (the record kept).
  D    the post-death UI at ISPostDeathUI.instance.0 within UI_CAP_S; onRespawn ok; accept ok; `store: reset record
       for admin (reset 1)` within RESPAWN_CAP_S of the accept; the record: resets 1, dead false, v 2, vitC.p above
       0.9 (a fresh pool), firstSeen greater than boot 1's; received +1 with the mirror's resets 1 and nut_vitC_g 0
       (the reset record has no nutrients table until its first slow minute lays one, and K.mirror writes 0 for an
       absent sub-table, NR_Kernel_Mirror.lua:71; a 1 is accepted if a later push landed before the read);
       reconcile.count 0. (Predicted MEASURED: the route above was read before the run.)
  KILL (boot 3 pre): no `Saving GlobalModData` line on boot 2 before the kill (#2097: SaveWorldEveryMinutes 0 saves
       only on a console save and a clean quit), so admin's record read before the client attaches equals boot 1's
       R_quit leaf for leaf: resets 0, boot 1's firstSeen, vitC.p R_quit's (not 0.07), zzKill ABSENT, zzProbe 2
       present; bob's v 1 (boot 2's migration was in memory only). The mod's table follows the engine's file (#2098).
       Falsifier: zzKill present or the 0.07 back with no save line. If a save line did land in boot 2 before the
       kill, the arm grades against the state of that save (stated).
  CTRL (boot 4): admin ABSENT from the table before the client attaches; after it, a new record: resets 0,
       firstSeen at this boot's world age, vitC.p above 0.9, zzProbe absent; bob absent.
  Z    every boot: server errors 0 that name the mod, no client lua_error, reconcile.count 0 for admin at each read.
A parked -debug client (the lua_error marker) stops that boot's remaining arms; the next boot still runs.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
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

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, make_client, make_server,    # noqa: E402
                         teardown, verify)

PROFILE = "x19-persist"
PREFIX = "x192"
SESSION = ("Plan 8 Task 6, live 2: the mod's record across a reconnect, a clean restart, a respawn and a hard kill, a "
           "planted v1 record's migration, and a fresh-fixture control; four server boots of " + PROFILE)
ARTIFACT = "persist.json"
USER = "admin"
GHOST = "bob"                                  # a username that never joins
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
KERNEL_STORE = os.path.join(REPO, MOD_DIR, "common", "media", "lua", "shared", "NR_Kernel_Store.lua")
STORE = "NutritionRevamp.players"
NR = "NutritionRevamp"
SAVE_DIR = os.path.join("Saves", "Multiplayer", "pzt")
GMD_FILE = "global_mod_data.bin"
FILE_MARKS = ("zzProbe", "zzKill", "bob")
WAIT_A_S = 4.0
WAIT_ON_S = 3.0
KILL_WAIT_S = 3.0
DEPART_CAP_S = 60.0
FIRST_SIGHT_CAP_S = 30.0
DEATH_CAP_S = 20.0
UI_CAP_S = 30.0
CREATE_CAP_S = 15.0
RESPAWN_CAP_S = 60.0
POLL_S = 0.5
RECV_CAP_S = 10.0
SAMPLE_S = 2.0
POST_TEARDOWN_S = 6.0
KILL_HEALTH = 110                              # the engine's own fatal ReduceGeneralHealth (#2348)
LOG_LIMIT = 400
ECHO_RX = re.compile(r"PZTK: ")
MOD_LINE_RX = re.compile(r"\[NutritionRevamp\]")
SAVE_RX = re.compile(r"Saving GlobalModData")
ERR_RX = re.compile(r"LuaError|STACK TRACE|lua error|attempted index|tried to call nil|Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server")
STORE_KEYS = ("loads", "migrations", "created", "failures")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
cur = {}
servers = {}
lock = threading.Lock()
watch = {"file": None, "boot": None, "phase": "pre", "log": None, "log_off": 0, "log_line": 0, "stop": False,
         "last_sig": None}


def wall():
    return round(time.time() - t0, 3)


def read_inputs():
    """K.store.INPUTS out of the kernel file: the quoted strings of its array literal."""
    with open(KERNEL_STORE, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"K\.store\.INPUTS = \{(.*?)\n\}", text, re.S)
    if not m:
        return [], None
    body = "\n".join(ln.split("--", 1)[0] for ln in m.group(1).splitlines())
    paths = re.findall(r'"([^"]+)"', body)
    with open(KERNEL_STORE, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    return paths, sha


INPUTS, KERNEL_SHA = read_inputs()

PRED = {
    "S0": {"server_error_count": 0, "client_lua_error": False, "received": ">= 1", "record.v": "2",
           "store.created": 1, "store.migrations": 0, "store.failures": 0, "migration_line": "absent",
           "reconcile.count": 0},
    "A": {"setpath_vitC.p.after": 0.05, "setpath_buffer.after": 123.5, "record.vitC.g": 4, "record.vitC.p": "< 0.06",
          "mirror.nut_vitC_g": 4},
    "B": {"order": "players: admin left, then players: first sight of admin", "migrated_admin_line": 1,
          "R_on.v": 2, "R_on.zzProbe": "absent", "R_off inputs present in R_on": "all", "R_on.resets": 0,
          "R_on.firstSeen": "== R_off", "R_on.lastSeen": "> R_off", "R_on.vitC.p": "< 0.06", "R_on.vitC.g": 4,
          "mirror": {"received": ">= 1", "nut_vitC_g": 4, "username": USER, "resets": 0}, "reconcile.count": 0,
          "c1b layout.ini before start": "absent"},
    "C": {"bob.store.get r1_keys": 6, "setpaths ok": 4},
    "RESTART": {"boot2 pre == boot1 R_quit": "every leaf", "zzProbe in the file's table": 2, "v": 2,
                "boot1 quit Saving GlobalModData lines": 1, "file changed at boot 1 quit": True},
    "DERIVED": {"zzProbe after first sight": "absent", "v": 2, "pre inputs present after": "all",
                "migrated admin line on boot 2": "absent", "vitC.g": 4, "vitC.p": "< 0.06", "mirror.nut_vitC_g": 4},
    "MIGRATE": {"pre": {"v": 1, "resets": 5, "kineticsAge": 7.5, "stomachFill": 0.9},
                "after": {"v": 2, "resets": 5, "kineticsAge": 7.5, "stomachFill": "absent", "firstSeen": 0},
                "migrated bob line": "v1 -> v2", "store.migrations": ">= 1"},
    "F": {"isDead": True, "dead_line": "players: admin is dead; record kept until respawn", "record.dead": True,
          "record.resets": 0, "record.vitC.p": "< 0.06"},
    "D": {"post-death UI": "ISPostDeathUI.instance.0 within UI_CAP_S", "onRespawn ok": True, "accept ok": True,
          "reset line": "store: reset record for admin (reset 1)", "record.resets": 1, "record.dead": False,
          "record.v": 2, "record.vitC.p": "> 0.9", "record.firstSeen": "> boot 1's", "mirror.resets": 1,
          "mirror.nut_vitC_g": "0 (no nutrients table at the reset's first-sight mirror; 1 accepted after a later push)", "received": "+1", "reconcile.count": 0, "status": "predicted MEASURED"},
    "KILL": {"boot2 Saving lines before the kill": 0, "boot3 pre == boot1 R_quit": "every leaf", "zzKill": "absent",
             "vitC.p": "R_quit's, not 0.07", "resets": 0, "zzProbe": 2, "bob.v": 1},
    "CTRL": {"admin before attach": "absent", "after": {"resets": 0, "vitC.p": "> 0.9", "zzProbe": "absent"},
             "bob": "absent"},
    "Z": {"mod error lines": 0, "client_lua_error": False, "reconcile.count": 0},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "ghost": GHOST, "profile": prof.report(),
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty": git_dirty(MOD_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "inputs": {"source": os.path.relpath(KERNEL_STORE, REPO).replace("\\", "/"), "sha256": KERNEL_SHA,
               "count": len(INPUTS), "paths": INPUTS},
    "constants": {k: v for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple))
                  and k not in ("REPO", "LUA_DIR", "MOD_DIR", "KERNEL_STORE", "KERNEL_SHA")},
    "predictions": PRED,
    "deviations": [
        "The reconnect's client is a fresh fixture restore in its own folder c1b: pzt's restore_client copies into "
        "<dir>/clients/admin and refuses an existing folder, so 'make_client again on the same run dir' cannot reuse "
        "c1's folder; every boot's client is likewise a fresh restore under <run>/c<label>.",
        "Two plants before the reconnect, decided before the run: admin.v 1 (the reconnect's in-place load is then a "
        "v1 -> v2 migration of a full record) and admin.zzProbe 1 (a field outside INPUTS that no step touches: the "
        "derived-on-read witness); a second probe admin.zzProbe 2 before the boot-1 quit.",
        "bob's plant is top-level only (v 1, resets 5, kineticsAge 7.5 as inputs, stomachFill 0.9 as a derived "
        "field): globalmoddata.setpath creates no table and bob's S.new record has no nutrients table, so the "
        "amendments' bob.nutrients.vitC.p / .g cannot be written; and g is an INPUT (ruling T3-1), so a g plant would "
        "be kept, not dropped.",
        "The derived-before-the-first-minute read (the amendments' g 0 or absent) is not taken: g is an INPUT, and at "
        "DayLength 1 the first sight's load and the first minute's work are a few ticks apart; the derived-on-read "
        "witness is the probe key's drop.",
        "Arm A's mirror is pulled once with requestMirror (the change push is held to one a minute, PUSH_GAP_MS).",
        "The kill arm also writes admin.zzKill 1 beside vitC.p 0.07, so the file's bytes and the next boot's table "
        "can be read for a key name.",
        "The respawn's last screen is accepted through lua.callm CoopCharacterCreation.instance accept: the harness "
        "presses the spawn and profession screens' NEXT itself but reads the menu's own appearance screen, not the "
        "coop one.",
        "The optional level-3 panel wheel arm is not taken (no trait push in this run).",
    ],
    "world_changes": {"restored": "boots 1-3 share <run>/server (one fresh restore at boot 1); boot 4 restores the "
                                  "fixture into <run>/boot4/server; every client is a fresh fixture restore under "
                                  "<run>/c<label>",
                      "left_in_place": ["boot 2's respawned character and its record were lost by the hard kill"]},
    "boots": {}, "notes": [], "verdicts": {}, "log_lines": [], "file_changes": [], "file_series_count": 0,
}


def note(msg):
    with lock:
        out["notes"].append({"wall": wall(), "boot": cur.get("label"), "note": msg})


def persist():
    try:
        with lock:
            out["timeline"] = list(tl.items)
            for label, srv in servers.items():
                if srv is not None and label in out["boots"]:
                    out["boots"][label]["server_errors"] = srv.errors[:30]
                    out["boots"][label]["server_error_count"] = len(srv.errors)
            text = json.dumps(out, indent=1, default=str)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def set_phase(name):
    with lock:
        watch["phase"] = name
    tl.mark("phase", boot=cur.get("label"), name=name)


# ---------------------------------------------------------------- the sampler and the log tail
def file_state(p):
    try:
        st = os.stat(p)
        with open(p, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        return {"exists": False, "error": type(e).__name__}
    return {"exists": True, "size": st.st_size, "mtime_ns": st.st_mtime_ns,
            "sha256": hashlib.sha256(raw).hexdigest()[:16], "has": {m: m.encode() in raw for m in FILE_MARKS}}


def tail_log():
    p = watch["log"]
    if not p:
        return
    try:
        with open(p, "rb") as fh:
            fh.seek(watch["log_off"])
            chunk = fh.read()
    except OSError:
        return
    cut = chunk.rfind(b"\n")
    if cut < 0:
        return
    body = chunk[:cut + 1]
    watch["log_off"] += len(body)
    for line in body.decode("utf-8", errors="replace").splitlines():
        watch["log_line"] += 1
        if ECHO_RX.search(line):
            continue
        if MOD_LINE_RX.search(line) or SAVE_RX.search(line):
            out["log_lines"].append({"i": len(out["log_lines"]), "wall_seen": wall(), "boot": watch["boot"],
                                     "phase": watch["phase"], "line": watch["log_line"], "text": line.strip()[:300]})


def sample_once(tag="tick"):
    with lock:
        p = watch["file"]
        if p is not None:
            st = file_state(p)
            out["file_series_count"] += 1
            sig = (st.get("exists"), st.get("mtime_ns"), st.get("size"), st.get("sha256"))
            if sig != watch["last_sig"]:
                out["file_changes"].append({"wall": wall(), "boot": watch["boot"], "phase": watch["phase"],
                                            "tag": tag, "prev": watch["last_sig"], **st})
                watch["last_sig"] = sig
        tail_log()


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


def lines_since(rx, since_i, boot=None):
    with lock:
        return [ln for ln in out["log_lines"] if ln["i"] >= since_i and rx.search(ln["text"])
                and (boot is None or ln["boot"] == boot)]


def log_mark():
    with lock:
        return len(out["log_lines"])


def wait_line(rx, since_i, cap_s, tag):
    """Polls the kept log lines (the sampler tails the log; this forces a tail each poll) for rx after index since_i."""
    end = time.time() + cap_s
    while True:
        sample_once(f"wait_{tag}")
        hits = lines_since(rx, since_i)
        if hits:
            return hits[0]
        if time.time() >= end:
            return None
        time.sleep(POLL_S)


# ---------------------------------------------------------------- bus helpers
def step(name, side, cmd, args="", timeout=30):
    t_before = wall()
    v = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is cur.get("server") else "client",
           "phase": watch["phase"], "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": v}
    if not isinstance(v, dict):
        row["ack_shape"] = type(v).__name__
    with lock:
        cur["B"]["steps"].append(row)
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def gread(side, name, tag):
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    row = {"name": name, "wall": r["wall_before"], "resolved": a.get("resolved"), "type": a.get("type")}
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


def parked():
    c = cur.get("client")
    return c is not None and "lua_error" in getattr(c, "seen", {})


def record(user, tag):
    """The whole record of `user`, one witness.moddata call: {present, record, wall, worldAge, keyCount}."""
    r = step(f"{tag}_rec_{user}", cur["server"], "witness.moddata", f"global:{STORE} {user}")
    a = ack(r)
    vals = a.get("values") or {}
    rec_ = vals.get(user)
    row = {"tag": tag, "user": user, "wall": r["wall_before"], "worldAge": a.get("worldAge"),
           "present": isinstance(rec_, dict), "record": rec_ if isinstance(rec_, dict) else None,
           "missing": a.get("missing"), "tableKeyCount": a.get("keyCount"), "answered": bool(a)}
    if a.get("error"):
        row["error"] = a.get("error")
    with lock:
        cur["B"]["records"][f"{tag}:{user}"] = row
    return row


def setpath(p, value, tag):
    return keep(step(tag, cur["server"], "globalmoddata.setpath", f"{STORE} {p} {value}"))


def store_stats(tag):
    return {k: num(val(gread(cur["server"], f"{NR}.server.store.stats.{k}", f"{tag}_ss_{k}"))) for k in STORE_KEYS}


def rc_count(tag):
    return gread(cur["server"], f"{NR}.server.store.records.{USER}.reconcile.count", f"{tag}_rc")


def mirror(tag):
    c = cur["client"]
    return {k: gread(c, f"{NR}.client.mirror.{k}", f"{tag}_m_{k}")
            for k in ("nut_vitC_g", "nut_vitC_p", "username", "resets", "firstSeen")}


def received(tag):
    return num(val(gread(cur["client"], f"{NR}.client.received", tag)))


def poll_received(before, tag, cap=RECV_CAP_S):
    rows, end, i = [], time.time() + cap, 0
    while True:
        v = received(f"{tag}_p{i}")
        rows.append({"i": i, "wall": wall(), "received": v})
        i += 1
        if v is not None and (before is None or v > before):
            return rows, rows[-1]["wall"]
        if time.time() >= end:
            return rows, None
        time.sleep(POLL_S)


def mcall(side, args, tag):
    return keep(step(tag, side, "lua.callm", args))


# ---------------------------------------------------------------- record arithmetic (also used by grading)
def as_map(v):
    """A JSON array read as the Lua table it came from (1-based keys)."""
    if isinstance(v, list):
        return {str(i + 1): x for i, x in enumerate(v)}
    return v


def pick(src, segs, i, prefix, outd):
    if not isinstance(src, dict):
        return
    seg = segs[i]
    keys = list(src.keys()) if seg == "*" else [seg]
    for k in keys:
        if k not in src:
            continue
        sv = as_map(src[k])
        p = f"{prefix}.{k}" if prefix else k
        if i == len(segs) - 1:
            outd[p] = sv
        elif isinstance(sv, dict):
            pick(sv, segs, i + 1, p, outd)


def inputs_of(rec_):
    outd = {}
    if not isinstance(rec_, dict):
        return outd
    for p in INPUTS:
        pick(rec_, p.split("."), 0, "", outd)
    return outd


def leaves(v, prefix="", outd=None):
    outd = {} if outd is None else outd
    v = as_map(v)
    if isinstance(v, dict):
        if not v and prefix:
            outd[prefix] = {}
        for k, x in v.items():
            leaves(x, f"{prefix}.{k}" if prefix else str(k), outd)
    else:
        outd[prefix] = v
    return outd


def compare(a, b):
    la, lb = leaves(a or {}), leaves(b or {})
    diff = [{"path": k, "a": la.get(k), "b": lb.get(k)} for k in sorted(set(la) | set(lb)) if la.get(k) != lb.get(k)]
    return {"leaves_a": len(la), "leaves_b": len(lb), "equal": len(diff) == 0 and len(la) > 0, "diffs": diff[:40],
            "diff_count": len(diff)}


def compare_inputs(a, b):
    ia, ib = inputs_of(a), inputs_of(b)
    leaves_a, leaves_b = leaves(ia), leaves(ib)
    diff = [{"path": k, "a": leaves_a.get(k), "b": leaves_b.get(k)} for k in sorted(set(leaves_a) | set(leaves_b))
            if leaves_a.get(k) != leaves_b.get(k)]
    missing = sorted(k for k in leaves_a if k not in leaves_b)
    return {"input_paths_a": len(ia), "input_leaves_a": len(leaves_a), "input_leaves_b": len(leaves_b),
            "equal": len(diff) == 0 and len(leaves_a) > 0, "diff_count": len(diff), "diffs": diff[:40],
            "missing_in_b": missing[:40], "missing_count": len(missing)}


def rget(rec_, dotted):
    node = rec_
    for part in dotted.split("."):
        node = as_map(node)
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def recv_of(row):
    return (row or {}).get("record")


# ---------------------------------------------------------------- the boots' bodies
def arm_S0():
    B = cur["B"]
    s, c = cur["server"], cur["client"]
    P = B["S0"] = {}
    P["tk_version"] = {"client": gread(c, "TK.version", "S0_tkv_c"), "server": gread(s, "TK.version", "S0_tkv_s")}
    P["nr_version"] = {"client": gread(c, f"{NR}.version", "S0_v_c"), "server": gread(s, f"{NR}.version", "S0_v_s")}
    P["received"] = gread(c, f"{NR}.client.received", "S0_received")
    P["record"] = record(USER, "S0")
    P["store_stats"] = store_stats("S0")
    P["rc"] = rc_count("S0")
    P["client_seen"] = dict(getattr(c, "seen", {}))


def body_1():
    B = cur["B"]
    s = cur["server"]
    set_phase("S0")
    time.sleep(2.0)                            # a few slow minutes after ready: the walk's first sight has run
    arm_S0()
    persist()
    if parked():
        B["abort"] = "client parked at S0"
        return
    # A: the forced state
    set_phase("A")
    A = B["A"] = {}
    A["record_before"] = record(USER, "A0")
    A["set_vitC"] = setpath(f"{USER}.nutrients.vitC.p", 0.05, "A_set_vitC")
    A["set_buffer"] = setpath(f"{USER}.stomach.buffer.calories", 123.5, "A_set_buf")
    time.sleep(WAIT_A_S)
    A["record_after"] = record(USER, "A1")
    A["received_before_pull"] = received("A_rcv0")
    A["pull"] = keep(step("A_pull", cur["client"], "lua.call", f"{NR}.client.requestMirror"))
    A["pull_poll"], A["pull_arrival"] = poll_received(A["received_before_pull"], "A_rcv")
    A["mirror"] = mirror("A")
    A["rc"] = rc_count("A")
    persist()
    # B: the reconnect
    set_phase("B")
    R = B["B"] = {}
    R["plant_v"] = setpath(f"{USER}.v", 1, "B_plant_v")
    R["plant_probe"] = setpath(f"{USER}.zzProbe", 1, "B_plant_probe")
    R["record_planted"] = record(USER, "B0")
    c1 = cur["client"]
    mark = log_mark()
    R["quit_wall"] = wall()
    try:
        R["quit_rc"] = c1.quit()
    except Exception as e:                     # noqa: BLE001
        R["quit_error"] = f"{type(e).__name__}: {e}"
    R["quit_done_wall"] = wall()
    tl.mark("client_quit", user=USER, rc=R.get("quit_rc"))
    R["c1_layout_ini_after_quit"] = os.path.exists(os.path.join(c1.cache, "Lua", "layout.ini"))
    dep = wait_line(re.compile(rf"players: {USER} left"), mark, DEPART_CAP_S, "depart")
    R["departure_line"] = dep
    time.sleep(1.0)
    R["R_off"] = record(USER, "B_off")
    R["rc_off"] = rc_count("B_off")
    persist()
    c1b_base = os.path.join(run_dir, "c1b")
    os.makedirs(c1b_base, exist_ok=True)
    mark2 = log_mark()
    c2, restored = make_client(c1b_base, USER, s, rec_fx)
    R["c1b_restored"] = restored
    R["c1b_layout_ini_before_start"] = os.path.exists(os.path.join(c2.cache, "Lua", "layout.ini"))
    R["c1_cache"] = os.path.relpath(c1.cache, run_dir)
    R["c1b_cache"] = os.path.relpath(c2.cache, run_dir)
    cur["client"] = c2
    cur["clients"].append(c2)
    R["c1b_start_wall"] = wall()
    c2.start()
    c2.wait_ready(timeout=prof.client_timeout)
    R["c1b_ready_wall"] = wall()
    tl.mark("client_ready", user=USER, which="c1b")
    fs = wait_line(re.compile(rf"players: first sight of {USER}"), mark2, FIRST_SIGHT_CAP_S, "first_sight")
    R["first_sight_line"] = fs
    R["migrated_lines"] = lines_since(re.compile(rf"store: migrated {USER} "), mark2)
    R["recv_poll"], R["recv_wall"] = poll_received(0, "B_rcv")
    R["mirror"] = mirror("B")
    time.sleep(1.0)
    R["R_on"] = record(USER, "B_on")
    R["rc_on"] = rc_count("B_on")
    R["store_stats"] = store_stats("B")
    R["client_seen"] = dict(getattr(c2, "seen", {}))
    persist()
    if parked():
        B["abort"] = "client parked after the reconnect"
        return
    # C: the planted v1 record and the quit state
    set_phase("C")
    C = B["C"] = {}
    C["bob_get"] = keep(step("C_bob_get", s, "lua.call", f"{NR}.server.store.get {GHOST} 0"))
    C["bob_created"] = record(GHOST, "C0")
    C["bob_v"] = setpath(f"{GHOST}.v", 1, "C_bob_v")
    C["bob_resets"] = setpath(f"{GHOST}.resets", 5, "C_bob_resets")
    C["bob_kin"] = setpath(f"{GHOST}.kineticsAge", 7.5, "C_bob_kin")
    C["bob_fill"] = setpath(f"{GHOST}.stomachFill", 0.9, "C_bob_fill")
    C["bob_planted"] = record(GHOST, "C1")
    C["plant_probe2"] = setpath(f"{USER}.zzProbe", 2, "C_plant_probe2")
    C["rc"] = rc_count("C")
    mark3 = log_mark()
    C["quit_wall"] = wall()
    try:
        C["quit_rc"] = c2.quit()
    except Exception as e:                     # noqa: BLE001
        C["quit_error"] = f"{type(e).__name__}: {e}"
    tl.mark("client_quit", user=USER, rc=C.get("quit_rc"))
    C["departure_line"] = wait_line(re.compile(rf"players: {USER} left"), mark3, DEPART_CAP_S, "depart2")
    time.sleep(1.0)
    C["R_quit"] = record(USER, "C_quit")
    C["bob_quit"] = record(GHOST, "C_quit")
    C["file_before_stop"] = file_state(watch["file"])
    persist()
    set_phase("quit")


def body_2():
    B = cur["B"]
    s = cur["server"]
    set_phase("pre")
    P = B["pre"] = {}
    P["admin"] = record(USER, "pre")
    P["bob"] = record(GHOST, "pre")
    P["store_stats"] = store_stats("pre")
    persist()
    set_phase("bob")
    M = B["bob"] = {}
    mark = log_mark()
    M["get"] = keep(step("bob_get", s, "lua.call", f"{NR}.server.store.get {GHOST} 0"))
    M["after"] = record(GHOST, "bob_after")
    M["store_stats"] = store_stats("bob")
    sample_once("bob_after")
    M["migrated_lines"] = lines_since(re.compile(rf"store: migrated {GHOST} "), mark)
    persist()
    # the client attaches
    set_phase("on")
    O = B["on"] = {}
    mark2 = log_mark()
    c = attach("2")
    O["first_sight_line"] = wait_line(re.compile(rf"players: first sight of {USER}"), mark2, FIRST_SIGHT_CAP_S,
                                      "first_sight")
    O["recv_poll"], O["recv_wall"] = poll_received(0, "on_rcv")
    time.sleep(WAIT_ON_S)
    O["mirror"] = mirror("on")
    O["R_on"] = record(USER, "on")
    O["migrated_admin_lines_boot2"] = lines_since(re.compile(rf"store: migrated {USER} "), 0, boot="2")
    O["rc"] = rc_count("on")
    O["store_stats"] = store_stats("on")
    persist()
    if parked():
        B["abort"] = "client parked at the boot-2 attach"
        return
    # F / D: the death and the respawn
    set_phase("death")
    D = B["death"] = {}
    D["received_before"] = received("D_rcv0")
    mark3 = log_mark()
    D["reduce"] = keep(step("D_reduce", s, "health.reduce", f"{USER} {KILL_HEALTH}"))
    D["reduce_wall"] = wall()
    polls, end = [], time.time() + DEATH_CAP_S
    dead_wall = None
    while True:
        r = keep(step("D_isDead", s, "witness.chain", f"{USER} isDead"))
        polls.append({"wall": r.get("wall"), "value": r.get("value"), "ok": r.get("ok"), "error": r.get("error")})
        if str(r.get("value")).lower() == "true":
            dead_wall = r.get("wall")
            break
        if time.time() >= end:
            break
        time.sleep(POLL_S)
    D["isDead_polls"] = polls
    D["isDead_wall"] = dead_wall
    D["dead_line"] = wait_line(re.compile(rf"players: {USER} is dead"), mark3, 10.0, "dead_line")
    D["health_server"] = keep(step("D_health_s", s, "health.get", USER))
    D["record_dead"] = record(USER, "dead")
    D["dead_flag"] = gread(s, f"{NR}.server.store.records.{USER}.dead", "D_dead")
    persist()
    if parked():
        B["abort"] = "client parked at the death"
        return
    # the post-death UI
    set_phase("respawn")
    c = cur["client"]
    ui_polls, end = [], time.time() + UI_CAP_S
    ui_wall = None
    while True:
        r = mcall(c, "ISPostDeathUI.instance.0 getIsVisible", "D_ui")
        ui_polls.append({"wall": r.get("wall"), "ok": r.get("ok"), "r1": r.get("r1"), "failedAt": r.get("failedAt"),
                         "type": r.get("type"), "err": r.get("err")})
        if r.get("ok"):
            ui_wall = r.get("wall")
            break
        if time.time() >= end:
            break
        time.sleep(1.0)
    D["ui_polls"] = ui_polls
    D["ui_wall"] = ui_wall
    D["client_health"] = keep(step("D_health_c", c, "health.get", USER))
    if ui_wall is None:
        D["unmeasured"] = "the post-death UI never appeared at ISPostDeathUI.instance.0"
        persist()
        return
    mark4 = log_mark()
    D["onRespawn"] = mcall(c, "ISPostDeathUI.instance.0 onRespawn", "D_onRespawn")
    scr, end = [], time.time() + CREATE_CAP_S
    while True:
        row = {"wall": wall(),
               "coop": gread(c, "CoopCharacterCreation.instance", "D_coop").get("type"),
               "spawn": mcall(c, "CoopMapSpawnSelect.instance getIsVisible", "D_spawn_vis").get("r1"),
               "profession": mcall(c, "CharacterCreationProfession.instance getIsVisible", "D_prof_vis").get("r1"),
               "main": mcall(c, "CharacterCreationMain.instance getIsVisible", "D_main_vis").get("r1")}
        scr.append(row)
        if row["main"] is True and row["spawn"] is not True and row["profession"] is not True:
            break
        if time.time() >= end:
            break
        time.sleep(1.0)
    D["screens"] = scr
    if scr and scr[-1].get("spawn") is True:
        D["clickNext"] = mcall(c, "CoopMapSpawnSelect.instance clickNext", "D_clickNext")
        time.sleep(3.0)
        D["screens_after_clickNext"] = {
            "profession": mcall(c, "CharacterCreationProfession.instance getIsVisible", "D_prof_vis2").get("r1"),
            "main": mcall(c, "CharacterCreationMain.instance getIsVisible", "D_main_vis2").get("r1")}
    D["selectedRegion"] = gread(c, "CoopMapSpawnSelect.instance.selectedRegion.name", "D_region")
    D["accept"] = mcall(c, "CoopCharacterCreation.instance accept", "D_accept")
    D["accept_wall"] = wall()
    D["reset_line"] = wait_line(re.compile(rf"store: reset record for {USER}"), mark4, RESPAWN_CAP_S, "reset")
    D["recv_poll"], D["recv_wall"] = poll_received(D["received_before"], "D_rcv", cap=RECV_CAP_S * 2)
    time.sleep(2.0)
    D["mirror"] = mirror("respawn")
    D["record_respawn"] = record(USER, "respawn")
    D["rc"] = rc_count("respawn")
    D["lines_after_accept"] = lines_since(re.compile(r"players:|store:"), mark4)
    D["client_seen"] = dict(getattr(c, "seen", {}))
    persist()


def body_2_kill():
    """E: the kill write, then the client killed and the server hard-killed (called by boot 2 after body_2)."""
    B = cur["B"]
    s, c = cur["server"], cur.get("client")
    set_phase("kill")
    E = B["kill"] = {}
    E["set_vitC"] = setpath(f"{USER}.nutrients.vitC.p", 0.07, "E_set_vitC")
    E["set_mark"] = setpath(f"{USER}.zzKill", 1, "E_set_mark")
    E["record_after_write"] = record(USER, "E_write")
    E["write_wall"] = wall()
    time.sleep(KILL_WAIT_S)
    sample_once("kill_before")
    E["saves_boot2_before_kill"] = [ln for ln in lines_since(SAVE_RX, 0, boot="2")]
    E["client_kill_wall"] = wall()
    try:
        if c is not None:
            c.kill()
    except Exception as e:                     # noqa: BLE001
        E["client_kill_error"] = f"{type(e).__name__}: {e}"
    E["server_pid"] = getattr(s.proc, "pid", None)
    E["server_kill_wall"] = wall()
    try:
        s.kill()
        E["server_rc"] = s.proc.wait(30)
    except Exception as e:                     # noqa: BLE001
        E["server_kill_error"] = f"{type(e).__name__}: {e}"
    E["server_killed_wall"] = wall()
    E["server_alive_after"] = s.alive
    tl.mark("server_killed", rc=E.get("server_rc"))
    time.sleep(2.0)
    sample_once("kill_after")
    E["file_after_kill"] = file_state(watch["file"])
    set_phase("killed")


def body_2_all():
    try:
        body_2()
    except Exception as e:                     # noqa: BLE001 - the kill arm still runs
        cur["B"]["body_error"] = f"{type(e).__name__}: {e}"
        cur["B"]["body_traceback"] = traceback.format_exc()[-3000:]
        persist()
    body_2_kill()


def body_3():
    B = cur["B"]
    P = B["pre"] = {}
    set_phase("pre")
    P["admin"] = record(USER, "pre")
    P["bob"] = record(GHOST, "pre")
    persist()
    set_phase("on")
    mark = log_mark()
    attach("3")
    O = B["on"] = {}
    O["first_sight_line"] = wait_line(re.compile(rf"players: first sight of {USER}"), mark, FIRST_SIGHT_CAP_S,
                                      "first_sight")
    time.sleep(WAIT_ON_S)
    O["R_on"] = record(USER, "on")
    O["mirror"] = mirror("on")
    O["lines"] = lines_since(re.compile(r"players:|store:"), mark)
    O["rc"] = rc_count("on")
    persist()
    set_phase("quit")


def body_4():
    B = cur["B"]
    P = B["pre"] = {}
    set_phase("pre")
    P["admin"] = record(USER, "pre")
    P["bob"] = record(GHOST, "pre")
    persist()
    set_phase("on")
    mark = log_mark()
    attach("4")
    O = B["on"] = {}
    O["first_sight_line"] = wait_line(re.compile(rf"players: first sight of {USER}"), mark, FIRST_SIGHT_CAP_S,
                                      "first_sight")
    time.sleep(WAIT_ON_S)
    O["R_on"] = record(USER, "on")
    O["bob"] = record(GHOST, "on")
    O["mirror"] = mirror("on")
    O["rc"] = rc_count("on")
    persist()
    set_phase("quit")


def attach(label):
    s = cur["server"]
    base = os.path.join(run_dir, f"c{label}")
    os.makedirs(base, exist_ok=True)
    c, restored = make_client(base, USER, s, rec_fx)
    B = cur["B"]
    B.setdefault("clients", []).append({"base": os.path.relpath(base, run_dir), "restored": restored,
                                        "start_wall": wall()})
    cur["client"] = c
    cur["clients"].append(c)
    c.start()
    c.wait_ready(timeout=prof.client_timeout)
    B["clients"][-1]["ready_wall"] = wall()
    tl.mark("session_ready", label=label)
    B["verify"] = verify(prof, s, [c], tl)
    B["mods_not_found"] = {"server": sorted(set(s.mods_not_found)), "client": sorted(set(c.mods_not_found))}
    return c


BOOTS = [("1", False, body_1, True), ("2", True, body_2_all, False), ("3", True, body_3, True),
         ("4", False, body_4, True)]


def boot(label, reuse, body, clean):
    B = out["boots"][label] = {"reuse": reuse, "steps": [], "records": {}}
    cur.clear()
    cur.update({"label": label, "B": B, "clients": []})
    tl.mark("boot", label=label, reuse=reuse)
    server = None
    base = run_dir if label != "4" else os.path.join(run_dir, "boot4")
    try:
        os.makedirs(base, exist_ok=True)
        server = make_server(base, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, reuse=reuse, ini=prof.ini)
        server.log_path = os.path.join(run_dir, f"server-stdout-boot{label}.log")
        servers[label] = server
        cur["server"] = server
        B["server_cache"] = os.path.relpath(server.cache, run_dir)
        point_watch(label, server.cache, server.log_path)
        set_phase("boot")
        sample_once("before_start")
        B["launch_wall"] = wall()
        server.start(timeout=prof.server_timeout)
        B["server_started_wall"] = wall()
        B["server_t_started"] = getattr(server, "t_started", None)
        tl.mark("server_started", label=label)
        sample_once("server_started")
        B["build"] = server.build
        if label == "1":
            attach("1")
        persist()
        body()
    except Exception as e:                     # noqa: BLE001 - the boot is a result; keep its rows
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", label=label, detail=str(e)[:200])
    finally:
        B["wall_end_body"] = wall()
        persist()
        live = [c for c in cur.get("clients", []) if c.alive]
        try:
            if server is not None and clean and server.alive:
                set_phase("quit")
                B["teardown_wall"] = wall()
                teardown(tl, server, live)
                B["server_rc"] = server.proc.returncode if server.proc else None
        except Exception as e:                 # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, cur.get("clients", []))
            end = wall() + POST_TEARDOWN_S
            while wall() < end:
                time.sleep(1.0)
            sample_once("after_teardown")
            set_phase("down")
            B["client_lua_error"] = any("lua_error" in getattr(c, "seen", {}) for c in cur.get("clients", []))
            B["client_seen"] = [dict(getattr(c, "seen", {})) for c in cur.get("clients", [])]
            if server is not None:
                errs = [str(e) for e in server.errors]
                B["mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)]
                B["client_error_lines"] = []
                for c in cur.get("clients", []):
                    hits = []
                    try:
                        with open(c.console, encoding="utf-8", errors="replace") as fh:
                            for line in fh:
                                if ERR_RX.search(line) and not ECHO_RX.search(line):
                                    hits.append(line.strip()[:300])
                                    if len(hits) >= 40:
                                        break
                    except OSError:
                        pass
                    B["client_error_lines"].append({"console": os.path.relpath(c.console, run_dir), "lines": hits})
                B["server_log"] = os.path.relpath(server.log_path, run_dir)
            B["wall_end"] = wall()
            persist()


# ---------------------------------------------------------------- grading
def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def fnum(v):
    return num(v)


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def grade_all():
    b1, b2, b3, b4 = (out["boots"].get(k) or {} for k in ("1", "2", "3", "4"))
    # S0
    S = b1.get("S0") or {}
    if S:
        rec1 = recv_of(S.get("record"))
        obs = {"server_error_count": b1.get("server_error_count"), "mod_error_lines": b1.get("mod_error_lines"),
               "client_lua_error": b1.get("client_lua_error"), "received": num(val(S.get("received"))),
               "record.v": rget(rec1, "v"), "store_stats": S.get("store_stats"),
               "migration_lines_boot1_before_B": [ln["text"] for ln in out["log_lines"] if ln["boot"] == "1"
                                                  and ln["phase"] in ("boot", "S0", "A") and "store: migrated" in ln["text"]],
               "reconcile.count": val(S.get("rc"))}
        ss = obs["store_stats"] or {}
        ok = (not obs["mod_error_lines"] and obs["client_lua_error"] is False and (obs["received"] or 0) >= 1
              and str(obs["record.v"]) == "2" and ss.get("created") == 1 and ss.get("migrations") == 0
              and ss.get("failures") == 0 and not obs["migration_lines_boot1_before_B"]
              and (num(obs["reconcile.count"]) or 0) == 0)
        grade("S0", PRED["S0"], obs, "as_predicted" if ok else "falsified",
              "a mod error, a parked client, no mirror, a record version other than 2, a migration or a reconciled "
              "intake")
    else:
        grade("S0", PRED["S0"], None, "unmeasured", "boot 1 never reached S0")
    # A
    A = b1.get("A") or {}
    if A.get("record_after"):
        ra = recv_of(A["record_after"])
        obs = {"set_vitC": {k: A["set_vitC"].get(k) for k in ("ok", "before", "after")},
               "set_buffer": {k: A["set_buffer"].get(k) for k in ("ok", "before", "after")},
               "record.vitC.g": rget(ra, "nutrients.vitC.g"), "record.vitC.p": rget(ra, "nutrients.vitC.p"),
               "record.buffer.calories": rget(ra, "stomach.buffer.calories"),
               "pull_arrival": A.get("pull_arrival"), "mirror.nut_vitC_g": val((A.get("mirror") or {}).get("nut_vitC_g")),
               "inputs_census": {"paths": len(inputs_of(ra)), "leaves": len(leaves(inputs_of(ra)))}}
        ok = (A["set_vitC"].get("ok") is True and A["set_buffer"].get("ok") is True
              and num(obs["record.vitC.g"]) == 4 and (num(obs["record.vitC.p"]) or 1) < 0.06
              and num(obs["mirror.nut_vitC_g"]) == 4)
        grade("A", PRED["A"], obs, "as_predicted" if ok else "falsified",
              "a setpath refused, the grade not 4, or the pulled mirror's grade not 4")
    else:
        grade("A", PRED["A"], None, "unmeasured", "arm A not reached")
    # B
    R = b1.get("B") or {}
    if R.get("R_on"):
        off, on = recv_of(R.get("R_off")), recv_of(R.get("R_on"))
        dep, fs = R.get("departure_line"), R.get("first_sight_line")
        ci = compare_inputs(off, on)
        m = R.get("mirror") or {}
        obs = {"departure_line": dep, "first_sight_line": fs,
               "order_ok": bool(dep and fs and dep["i"] < fs["i"]),
               "quit_rc": R.get("quit_rc"), "departure_after_quit_s": (round(dep["wall_seen"] - R["quit_wall"], 3)
                                                                       if dep else None),
               "migrated_lines": [ln["text"] for ln in (R.get("migrated_lines") or [])],
               "R_off.v": rget(off, "v"), "R_off.zzProbe": rget(off, "zzProbe"),
               "R_on.v": rget(on, "v"), "R_on.zzProbe_present": rget(on, "zzProbe") is not None,
               "R_on.resets": rget(on, "resets"), "R_on.username": rget(on, "username"),
               "firstSeen": [rget(off, "firstSeen"), rget(on, "firstSeen")],
               "lastSeen": [rget(off, "lastSeen"), rget(on, "lastSeen")],
               "R_on.vitC.p": rget(on, "nutrients.vitC.p"), "R_on.vitC.g": rget(on, "nutrients.vitC.g"),
               "inputs_off_vs_on": {k: ci[k] for k in ("input_paths_a", "input_leaves_a", "input_leaves_b",
                                                       "missing_count", "missing_in_b", "diff_count")},
               "mirror": {k: val(m.get(k)) for k in ("nut_vitC_g", "username", "resets", "firstSeen")},
               "received_poll_last": (R.get("recv_poll") or [{}])[-1], "recv_wall": R.get("recv_wall"),
               "reconcile.count": [val(R.get("rc_off")), val(R.get("rc_on"))],
               "c1_layout_ini_after_quit": R.get("c1_layout_ini_after_quit"),
               "c1b_layout_ini_before_start": R.get("c1b_layout_ini_before_start"),
               "c1b_restored": R.get("c1b_restored")}
        try:
            ok = (obs["order_ok"] and len(obs["migrated_lines"]) == 1 and "v1 -> v2" in obs["migrated_lines"][0]
                  and str(obs["R_off.v"]) == "1" and num(obs["R_on.v"]) == 2 and not obs["R_on.zzProbe_present"]
                  and num(obs["R_on.resets"]) == 0 and obs["R_on.username"] == USER
                  and obs["firstSeen"][0] == obs["firstSeen"][1]
                  and num(obs["lastSeen"][1]) > num(obs["lastSeen"][0])
                  and num(obs["R_on.vitC.p"]) < 0.06 and num(obs["R_on.vitC.g"]) == 4
                  and ci["missing_count"] == 0 and ci["input_paths_a"] > 0
                  and num(obs["mirror"]["nut_vitC_g"]) == 4 and obs["mirror"]["username"] == USER
                  and num(obs["mirror"]["resets"]) == 0
                  and all((num(x) or 0) == 0 for x in obs["reconcile.count"])
                  and obs["c1b_layout_ini_before_start"] is False)
        except TypeError:
            ok = False
        grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified",
              "no departure or first-sight line or the wrong order, no single migration line, the probe kept, a lost "
              "input path, a moved firstSeen, a reset, the grade not carried, the mirror's grade not 4, a reconciled "
              "intake, or a warm client cache")
    else:
        grade("B", PRED["B"], None, "unmeasured", "the reconnect did not complete")
    # C
    C = b1.get("C") or {}
    if C.get("bob_planted"):
        bp = recv_of(C["bob_planted"])
        sets = [C.get(k) or {} for k in ("bob_v", "bob_resets", "bob_kin", "bob_fill")]
        obs = {"bob_get_r1_keys": (C.get("bob_get") or {}).get("r1_keys"),
               "bob_created_keys": sorted((recv_of(C.get("bob_created")) or {}).keys()),
               "setpaths_ok": sum(1 for x in sets if x.get("ok") is True), "bob_planted": bp,
               "probe2_ok": (C.get("plant_probe2") or {}).get("ok"), "quit_rc": C.get("quit_rc"),
               "departure_line": C.get("departure_line")}
        ok = obs["bob_get_r1_keys"] == 6 and obs["setpaths_ok"] == 4 and obs["probe2_ok"] is True
        grade("C", PRED["C"], obs, "as_predicted" if ok else "falsified", "bob not created at 6 keys or a plant refused")
    else:
        grade("C", PRED["C"], None, "unmeasured", "arm C not reached")
    # RESTART
    rq = recv_of(C.get("R_quit")) if C else None
    pre2 = recv_of(g(b2, "pre", "admin"))
    if rq is not None and pre2 is not None:
        cmp_all = compare(rq, pre2)
        ci = compare_inputs(rq, pre2)
        saves1 = [ln for ln in out["log_lines"] if ln["boot"] == "1" and SAVE_RX.search(ln["text"])]
        ch1 = [c for c in out["file_changes"] if c["boot"] == "1" and c["phase"] in ("quit", "down")
               and c.get("prev") is not None]
        obs = {"all_leaves": {k: cmp_all[k] for k in ("leaves_a", "leaves_b", "equal", "diff_count", "diffs")},
               "inputs": {k: ci[k] for k in ("input_paths_a", "input_leaves_a", "input_leaves_b", "equal",
                                             "diff_count", "missing_count", "diffs")},
               "pre.zzProbe": rget(pre2, "zzProbe"), "pre.v": rget(pre2, "v"),
               "boot1_save_lines": saves1, "boot1_quit_file_changes": [{k: c.get(k) for k in
                                                                        ("wall", "phase", "size", "mtime_ns", "has")}
                                                                       for c in ch1]}
        ok = (cmp_all["equal"] and ci["equal"] and num(obs["pre.zzProbe"]) == 2 and num(obs["pre.v"]) == 2
              and len(saves1) == 1 and len(ch1) >= 1)
        grade("RESTART", PRED["RESTART"], obs, "as_predicted" if ok else "falsified",
              "a leaf or an input that differs across the clean quit and reload, the probe not in the file's table, "
              "or no save line / file change at the quit")
    else:
        grade("RESTART", PRED["RESTART"], None, "unmeasured", "R_quit or the boot-2 pre read missing")
    # DERIVED
    O2 = b2.get("on") or {}
    on2 = recv_of(O2.get("R_on"))
    if on2 is not None and pre2 is not None:
        ci = compare_inputs(pre2, on2)
        obs = {"first_sight_line": O2.get("first_sight_line"), "on.zzProbe_present": rget(on2, "zzProbe") is not None,
               "on.v": rget(on2, "v"), "pre_inputs_missing_after": ci["missing_count"],
               "pre_input_paths": ci["input_paths_a"], "missing": ci["missing_in_b"],
               "migrated_admin_lines_boot2": [ln["text"] for ln in (O2.get("migrated_admin_lines_boot2") or [])],
               "on.vitC.g": rget(on2, "nutrients.vitC.g"), "on.vitC.p": rget(on2, "nutrients.vitC.p"),
               "mirror.nut_vitC_g": val(g(O2, "mirror", "nut_vitC_g")), "recv_wall": O2.get("recv_wall"),
               "reconcile.count": val(O2.get("rc")), "store_stats": O2.get("store_stats")}
        try:
            ok = (not obs["on.zzProbe_present"] and num(obs["on.v"]) == 2 and ci["missing_count"] == 0
                  and not obs["migrated_admin_lines_boot2"] and num(obs["on.vitC.g"]) == 4
                  and num(obs["on.vitC.p"]) < 0.06 and num(obs["mirror.nut_vitC_g"]) == 4
                  and (num(obs["reconcile.count"]) or 0) == 0)
        except TypeError:
            ok = False
        grade("DERIVED", PRED["DERIVED"], obs, "as_predicted" if ok else "falsified",
              "the probe kept after the first sight, an input path lost, a migration line for admin, the grade not "
              "carried or a reconciled intake")
    else:
        grade("DERIVED", PRED["DERIVED"], None, "unmeasured", "the boot-2 reads missing")
    # MIGRATE
    bpre, bafter = recv_of(g(b2, "pre", "bob")), recv_of(g(b2, "bob", "after"))
    if bpre is not None and bafter is not None:
        mig = [ln["text"] for ln in (g(b2, "bob", "migrated_lines") or [])]
        obs = {"pre": {k: rget(bpre, k) for k in ("v", "resets", "kineticsAge", "stomachFill", "firstSeen")},
               "after": {k: rget(bafter, k) for k in ("v", "resets", "kineticsAge", "stomachFill", "firstSeen")},
               "after_keys": sorted(bafter.keys()), "migrated_lines": mig,
               "store_stats": g(b2, "bob", "store_stats"), "get_reply": g(b2, "bob", "get")}
        p, a = obs["pre"], obs["after"]
        try:
            ok = (num(p["v"]) == 1 and num(p["resets"]) == 5 and num(p["kineticsAge"]) == 7.5
                  and num(p["stomachFill"]) == 0.9 and num(a["v"]) == 2 and num(a["resets"]) == 5
                  and num(a["kineticsAge"]) == 7.5 and a["stomachFill"] is None and num(a["firstSeen"]) == 0
                  and len(mig) == 1 and "v1 -> v2" in mig[0]
                  and (num((obs["store_stats"] or {}).get("migrations")) or 0) >= 1)
        except TypeError:
            ok = False
        grade("MIGRATE", PRED["MIGRATE"], obs, "as_predicted" if ok else "falsified",
              "the plant not in the file, an input dropped, the derived field kept, no or more than one migration "
              "line")
    else:
        grade("MIGRATE", PRED["MIGRATE"], None, "unmeasured", "bob's reads missing")
    # F and D
    D = b2.get("death") or {}
    if D.get("reduce"):
        rd = recv_of(D.get("record_dead"))
        obs = {"reduce": {k: D["reduce"].get(k) for k in ("ok", "before", "after", "reason")},
               "isDead_wall": D.get("isDead_wall"), "reduce_wall": D.get("reduce_wall"),
               "isDead_polls": len(D.get("isDead_polls") or []), "dead_line": D.get("dead_line"),
               "record.dead": rget(rd, "dead"), "dead_flag": val(D.get("dead_flag")),
               "record.resets": rget(rd, "resets"), "record.vitC.p": rget(rd, "nutrients.vitC.p")}
        if D.get("isDead_wall") is None:
            grade("F", PRED["F"], obs, "unmeasured", "the character never read dead on the server")
        else:
            try:
                ok = (D.get("dead_line") is not None and obs["record.dead"] is True and num(obs["record.resets"]) == 0
                      and num(obs["record.vitC.p"]) < 0.06)
            except TypeError:
                ok = False
            grade("F", PRED["F"], obs, "as_predicted" if ok else "falsified",
                  "the record's dead not true after the death, a reset before the respawn, or the record replaced")
        if D.get("unmeasured") or D.get("isDead_wall") is None:
            grade("D", PRED["D"], {"ui_polls": D.get("ui_polls"), "reason": D.get("unmeasured")}, "unmeasured",
                  "the death or the post-death UI did not come")
        else:
            rr = recv_of(D.get("record_respawn"))
            m = D.get("mirror") or {}
            b1first = rget(recv_of(C.get("R_quit")) if C else None, "firstSeen")
            obs2 = {"ui_wall": D.get("ui_wall"), "onRespawn": {k: (D.get("onRespawn") or {}).get(k)
                                                               for k in ("ok", "err", "failedAt", "type")},
                    "screens": D.get("screens"), "clickNext": D.get("clickNext"),
                    "selectedRegion": val(D.get("selectedRegion")),
                    "accept": {k: (D.get("accept") or {}).get(k) for k in ("ok", "err", "failedAt", "type")},
                    "accept_wall": D.get("accept_wall"), "reset_line": D.get("reset_line"),
                    "reset_after_accept_s": (round(D["reset_line"]["wall_seen"] - D["accept_wall"], 3)
                                             if D.get("reset_line") else None),
                    "lines_after_accept": [ln["text"] for ln in (D.get("lines_after_accept") or [])],
                    "record": {k: rget(rr, k) for k in ("v", "resets", "dead", "firstSeen", "lastSeen",
                                                         "nutrients.vitC.p", "nutrients.vitC.g", "zzProbe")},
                    "boot1_firstSeen": b1first,
                    "received": [D.get("received_before"), (D.get("recv_poll") or [{}])[-1].get("received")],
                    "recv_wall": D.get("recv_wall"),
                    "mirror": {k: val(m.get(k)) for k in ("resets", "nut_vitC_g", "firstSeen", "username")},
                    "reconcile.count": val(D.get("rc"))}
            r_ = obs2["record"]
            try:
                ok = (obs2["accept"]["ok"] is True and D.get("reset_line") is not None
                      and "(reset 1)" in D["reset_line"]["text"] and num(r_["resets"]) == 1 and r_["dead"] is False
                      and num(r_["v"]) == 2 and num(r_["nutrients.vitC.p"]) > 0.9
                      and num(r_["firstSeen"]) > num(b1first) and D.get("recv_wall") is not None
                      and num(obs2["mirror"]["resets"]) == 1 and num(obs2["mirror"]["nut_vitC_g"]) in (0, 1)
                      and (num(obs2["reconcile.count"]) or 0) == 0)
            except TypeError:
                ok = False
            if D.get("reset_line") is None and obs2["accept"]["ok"] is not True:
                grade("D", PRED["D"], obs2, "unmeasured", "accept did not run, so no respawn was driven")
            else:
                grade("D", PRED["D"], obs2, "as_predicted" if ok else "falsified",
                      "no reset line after the accept, a record that is not fresh (resets, dead, pool, firstSeen), or "
                      "no first-sight mirror with resets 1")
    else:
        grade("F", PRED["F"], None, "unmeasured", "the death arm was not reached")
        grade("D", PRED["D"], None, "unmeasured", "the death arm was not reached")
    # KILL
    E = b2.get("kill") or {}
    pre3 = recv_of(g(b3, "pre", "admin"))
    if E and pre3 is not None and rq is not None:
        saves2 = E.get("saves_boot2_before_kill") or []
        cmp_all = compare(rq, pre3)
        obs = {"write": {k: (E.get("set_vitC") or {}).get(k) for k in ("ok", "before", "after")},
               "mark": {k: (E.get("set_mark") or {}).get(k) for k in ("ok", "after")},
               "write_to_kill_s": (round(E["server_kill_wall"] - E["write_wall"], 3)
                                   if E.get("server_kill_wall") and E.get("write_wall") else None),
               "server_rc": E.get("server_rc"), "server_alive_after": E.get("server_alive_after"),
               "saves_boot2_before_kill": saves2,
               "boot2_file_changes": [{k: c.get(k) for k in ("wall", "phase", "size", "has")} for c in
                                      out["file_changes"] if c["boot"] == "2" and c.get("prev") is not None],
               "pre3_vs_R_quit": {k: cmp_all[k] for k in ("leaves_a", "leaves_b", "equal", "diff_count", "diffs")},
               "pre3": {k: rget(pre3, k) for k in ("resets", "firstSeen", "nutrients.vitC.p", "zzKill", "zzProbe", "v",
                                                   "dead")},
               "bob3.v": rget(recv_of(g(b3, "pre", "bob")), "v")}
        if saves2:
            ok = rget(pre3, "zzKill") is None
            grade("KILL", PRED["KILL"], obs, "as_predicted" if ok else "falsified",
                  "a save line landed on boot 2 before the kill: graded on the write alone (zzKill absent)",
                  {"save_landed": True})
        else:
            ok = (cmp_all["equal"] and rget(pre3, "zzKill") is None and num(rget(pre3, "nutrients.vitC.p")) != 0.07
                  and num(rget(pre3, "resets")) == 0 and num(rget(pre3, "zzProbe")) == 2
                  and num(obs["bob3.v"]) == 1)
            grade("KILL", PRED["KILL"], obs, "as_predicted" if ok else "falsified",
                  "zzKill present, the 0.07 back, or the table not boot 1's quit state with no save line")
    else:
        grade("KILL", PRED["KILL"], None, "unmeasured", "the kill or the boot-3 pre read missing")
    # CTRL
    pre4 = g(b4, "pre", "admin") or {}
    on4 = recv_of(g(b4, "on", "R_on"))
    if pre4 and on4 is not None:
        obs = {"pre.present": pre4.get("present"), "pre.answered": pre4.get("answered"),
               "pre.tableKeyCount": pre4.get("tableKeyCount"),
               "on": {k: rget(on4, k) for k in ("resets", "firstSeen", "nutrients.vitC.p", "zzProbe", "v")},
               "bob_pre_present": (g(b4, "pre", "bob") or {}).get("present"),
               "bob_on_present": (g(b4, "on", "bob") or {}).get("present"),
               "worldAge_on": (g(b4, "on", "R_on") or {}).get("worldAge")}
        try:
            ok = (pre4.get("answered") and pre4.get("present") is False and num(obs["on"]["resets"]) == 0
                  and num(obs["on"]["nutrients.vitC.p"]) > 0.9 and obs["on"]["zzProbe"] is None
                  and obs["bob_pre_present"] is False)
        except TypeError:
            ok = False
        grade("CTRL", PRED["CTRL"], obs, "as_predicted" if ok else "unmeasured",
              "a record present before the attach on the restored fixture (the control failed: the arms' reads are "
              "then unproven, so the verdict is unmeasured, not falsified)")
    else:
        grade("CTRL", PRED["CTRL"], None, "unmeasured", "boot 4's reads missing")
    # Z
    zs = {}
    for k, b in out["boots"].items():
        rcs = []
        for p_ in ("S0", "A", "B", "C", "on", "death"):
            sub = b.get(p_) or {}
            for kk in ("rc", "rc_off", "rc_on"):
                if isinstance(sub.get(kk), dict):
                    rcs.append(val(sub[kk]))
        zs[k] = {"mod_error_lines": b.get("mod_error_lines"), "client_lua_error": b.get("client_lua_error"),
                 "server_error_count": b.get("server_error_count"), "reconcile_counts": rcs,
                 "error": b.get("error")}
    ok = all(not z["mod_error_lines"] and z["client_lua_error"] is False and all((num(x) or 0) == 0
                                                                                  for x in z["reconcile_counts"])
             for z in zs.values()) and len(zs) == 4
    grade("Z", PRED["Z"], zs, "as_predicted" if ok else "falsified",
          "a mod error line, a parked client, or a reconciled intake on an idle admin")


# ---------------------------------------------------------------- main
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
if not INPUTS:
    out["error"] = "K.store.INPUTS not read from the kernel file; the session was not started"
    persist()
    print(out["error"])
    sys.exit(1)

th = threading.Thread(target=sampler, daemon=True)
th.start()
try:
    for label, reuse, body, clean in BOOTS:
        boot(label, reuse, body, clean)
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-3000:]
    out["summary"] = {
        "verify_ok": {k: [v.get("ok") for v in b.get("verify", [])] for k, b in out["boots"].items()},
        "boot_errors": {k: b.get("error") for k, b in out["boots"].items()},
        "aborts": {k: b.get("abort") for k, b in out["boots"].items()},
        "server_error_count": {k: b.get("server_error_count") for k, b in out["boots"].items()},
        "client_lua_error": {k: b.get("client_lua_error") for k, b in out["boots"].items()},
        "file_change_count": len(out["file_changes"]),
        "log_line_count": len(out["log_lines"]),
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

print(json.dumps({"summary": out.get("summary"), "error": out.get("error"), "grade_error": out.get("grade_error"),
                  "run_id": run_id}, indent=1, default=str)[:6000])
