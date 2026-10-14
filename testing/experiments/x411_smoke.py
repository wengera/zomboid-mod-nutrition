"""x411-smoke -- Plan 12 Task 5: the post-fix live smoke of the Plan 12 fixes on the re-staged release copy, the first
driver built on testing/experiments/xlib.py. One boot of profile x41-smoke: fixture two (admin -debug, then bob
release), Nutrition false, DayLength 1 (a game minute is 0.625 s of wall at true multiplier 1), [server] SleepAllowed
and SleepNeeded true (the sleep debt live, x151s), TKX_StudyFoods, and the STAGED copy at release/plan12-x41
(`python tools/release_pack.py stage mod/NutritionRevamp --out release/plan12-x41`, made by the controller before the
boot; release/ is gitignored; mod/ is never booted and the driver never stages). Before the boot: doctor clean, the
staged MANIFEST equal to release_pack.manifest() of a clean mod/NutritionRevamp and to the staged mod folder itself
(xlib.manifest_gate), the staged version equal to the verify rows', the harness markers in the repository files, at
least MIN_FREE_GB of host memory, and the layout lint clean. After it: every deployed copy of the three harness files
holds its markers (xlib.deployed_marker_check, each file read once) and every verify row ok. No commit or sha is
hard-coded. Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5).

`python testing/experiments/x411_smoke.py --selftest` runs the offline grade simulation and never boots: a fake bus
answering the harness's real reply shapes (xlib's Xs over a fake ask, a fake clock and a fake world that steps the mod's
record the way the fixed code does, or the way each defect would) runs every phase and grades it, and the run fails
unless every grade reads as_predicted on the fixed world and its failing verdict on a broken one (CLAUDE.md s5: every
grade has an offline failing case).

Artifact: `smoke.json`, with the staged MANIFEST.json and admin's minute-ring pages copied beside it, byte-identical.

PHASES (run order; each checked against the wall budget before it starts, Z always runs):
  S0  ping, players, the clock, both records present and MIN_RUNS minute runs; the sleep factor's switch
      (NutritionRevamp.server.nutrients.sleepDisabled); `minute.ring admin start <RING_PATHS>`; one column read on
      admin's first client (a COL sample).
  OFF THE OFFLINE SKIP (A1, B8). Admin's record read (acute.debtH, winStartH, winSleptH, mass90ageH, lastFedAgeH,
      lastVigAgeH, nutrients.lastAgeH, satiety.nicH) with the world age. Admin's client QUITS, then bob's (QUIT_USERS:
      no client is online while the clock is raised, and bob's character is not left two game days without food or
      water); `players` polled until neither is online (cap DEPART_CAP_S); the record read while away. The true
      multiplier is read (time.snapshot trueMult), `time.multiplier AWAY_MULT` set, and the world age polled every
      AWAY_POLL_S (each snapshot's trueMult kept) until it passes the away record's lastAgeH + AWAY_H (two game days
      and the one integrated hour; cap AWAY_CAP_S); in a finally the multiplier is set back to the value read before
      and read back (one retry). Only with the read-back equal does admin rejoin: a fresh fixture restore in <run>/c1b
      (x402a's form) at the restored clock. The record is polled until nutrients.lastAgeH moves (the first step back,
      cap FIRST_CAP_S) and read; OFF_SETTLE_MIN game minutes later the ring is read page by page (each page copied) and
      stopped. Bob does not rejoin.
  C0  the column on admin's rejoined client with every level 0 (a COL sample).
  MG  THE SUPPLEMENT-ONLY ULs (A2). One Base.Pasta (480.021 mg magnesium, 65.002089 mg niacin, 3541.287 ug folate,
      572.4024 ug selenium per item, NR_Data_Nutrients.lua) spawned by RCON additem and confirmed by item.get (xlib.spawn;
      a leftover voids it); intake.stats.landed read; xlib.eat_queue (foodtimer 0, `eat.action Base.Pasta 1`; a
      spawned other than "found" stops the eats); the landing polled (+1, cap LAND_CAP_S); then the record's
      nutrients.<key>.e24 and .x for magnesium, niacin, folate and selenium read every MG_READ_GAP_S for MG_READ_S.
      With the eat not landed, MG_FALLBACK (Base.Cereal, 894.292 mg magnesium) is tried once the same way.
  COL THE OWN COLUMN (C1). `requestMirror` on admin (REQUEST_GAP_S apart), the arrival polled (received +1, cap
      ARRIVE_CAP_S), then a column read: NutritionRevamp.client moodles.route and moodles.levels.<seven classes>, the
      probe (`lua.call NutritionRevamp.client.moodles.probe overfull`: level, onUI, route), the levels again (a sample
      counts only when both level reads agree), and moodles.isEnabled. With no level above 0 at that read, the overfull
      drive (x401's OF): at true multiplier SLOW_MULT (read before, restored in a finally) two TKX.Mixed650 spawned,
      eaten and landed, then the request, the arrival and the read again.
  XR  THE EXCESS ROW (C3). The request and the arrival; view.level read; then for level 2 (Bands) and 3 (Numbers) in
      turn: `lua.setpath NutritionRevamp.client.view.level <lv>` on admin's client, `lua.call
      NutritionRevamp.client.view.refresh true`, one read of the view's level, lastLevel, the mirror's nut_magnesium_x
      and nut_selenium_x and the row count, the rows' keys (60 a read), and the magnesium and selenium excess rows'
      key, text and valueText; in a finally view.level is set back to the value read before and refreshed.
  Z   the server's mod error lines, admin not parked, memory, then `players` and the clock.

LIVENESS AND THE BUDGET: xlib's step pings after a stalled server step and a missing pong marks the bus dead (every
later server step skipped, the phase void). BUDGET_S (840 s from t0, before the boot) is checked before each phase
against PHASE_EST_S and inside every poll (xlib.Xs.check raises Budget, which run_phase records). A phase that needs
admin's client is skipped while admin has not rejoined. Teardown, the log read, the grading and the artifact copy run
in finally (xlib.Xs.finish).

PREDICTIONS (graded in `verdicts` as as_predicted / falsified / trivial / unmeasured / void, each with its falsifier).
Q is the ring's state just before admin's first step back (the last row before it whose nutrients.lastAgeH is the
away value Lq), P1 the first row after the rejoin whose lastAgeH moved (A1, the first step's own world age; a row is
sampled inside EveryOneMinute before the mod's queue drains, so a row shows the state after the previous step). The
adapter caps a step at 60 game minutes and skips the rest: gap = ((A1 - Lq) x 60 - 60) / 60 game hours, computed the
way NR_Server_Nutrients.lua does. Without a ring pair the direct reads stand in, at OFF_TOL_DIRECT.
  OFF_AWAY    every away ring row (on false, record held) holds the away state of every OFF field: nothing
              integrates offline. Falsifier: an away row that moved. Unmeasured: no away row.
  OFF_WIN     acute.winStartH at P1 = Q's + gap (when Q's lies at or before Lq), plus 24 h for each window the one
              integrated hour then closes, within OFF_TOL. Falsifier: anything else, notably Q's value plus whole days
              (the unfixed close of every missed window). Trivial: the fixed and unfixed values within 0.01 h.
  OFF_DEBT    with gap >= 24 h and the sleep factor on: acute.debtH at P1 equals Q's when the integrated hour closes no
              window, else lies in [Q's - REPAY x 24, Q's + k x 7.5 x NEED_MORE] for its k windows. Falsifier: outside,
              notably about 7.5 h added per missed day. Unmeasured: gap < 24 h. Void: sleepDisabled true.
  OFF_ANCHORS acute.mass90ageH, lastFedAgeH and lastVigAgeH (each at or before Lq at Q) read Q's + gap at P1, or A1
              when the step itself re-lays one (counted relaid). Falsifier: an anchor left at Q's value or at any other.
              Trivial: every anchor relaid.
  OFF_NIC     satiety.nicH at P1 = Q's + gap when admin's NICOTINE_WITHDRAWAL reads above 0 (the writer keeps the
              anchor). Trivial: the stat 0 (the writer lays nicH at every minute's age). Unmeasured: no nicH.
  MG          every read with nutrients.magnesium.e24 >= 350 (the UL marked ulBasis "supplement") holds
              nutrients.magnesium.x = 0. Falsifier: a rung of 1 or more. Unmeasured: e24 never reached 350.
  MG_NIACIN   the same for niacin (UL 35 mg). MG_FOLATE the same for folate (UL 1000 ug).
  COL_ZERO    every agreeing column read with all seven levels 0, on route "own" with the moodles enabled, reads the
              probe's onUI false: the empty column is off the UI manager. Falsifier: onUI true. Unmeasured: no such read.
  COL_RAISED  every agreeing read with a level above 0 reads onUI true. Falsifier: false. Unmeasured: no such read.
  XR_MG       at Bands (view.level 2 read back), with the mirror's nut_magnesium_x 0: no row nut_magnesium_x.
              Falsifier: the row present. Unmeasured: no Bands read, or the rung not 0.
  XR_MG_NUM   at Numbers (3), with the rung 0: the row nut_magnesium_x present with text "0" (a graded key's excess
              row is listed at Numbers always, NR_Kernel_View.lua K.view.nutrientRows; DEVIATION 1). Falsifier: absent
              or another text. Unmeasured: no Numbers read or the rung not 0.
  XR_SE       with the mirror's nut_selenium_x n > 0 (an ungraded kind): at Bands the row nut_selenium_x with text
              UI_NR_Class_excess_<min(n, 3)>, at Numbers the row with text n. Falsifier: absent or another text at a
              read. Unmeasured: the rung 0 at every read, or no read at either level.
  Z           no mod error line on the server; admin not parked; `players` answered a list.

DEVIATIONS from the brief, stated before the run:
  1. XR reads magnesium's row at Bands for "absent at rung 0": at Numbers a graded key's excess row is always listed,
     its figure 0 (K.view.nutrientRows passes always = true), so XR_MG_NUM predicts it present with "0".
  2. One Base.Pasta serves MG and XR: its selenium passes the food UL, and its niacin and folate also pass their
     supplement-only ULs, so MG_NIACIN and MG_FOLATE are graded beside MG.
  3. Bob quits with admin before the clock is raised (QUIT_USERS) and does not rejoin: no client is online while it is
     raised (PauseEmpty is false in the fixture, so the clock runs) and bob's character is not left two game days
     unfed.
  4. OFF_NIC is trivial for a non-smoker: the writer lays nicH at the minute whenever the stat reads 0 (W.nicotine).
  5. The away wait targets the world age, not two days of wall: AWAY_MULT 30 is the measured speed (s02, #1813).

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time. 4. Free host
memory is read before the boot and the boot refused under MIN_FREE_GB. 5. A session killed by the host is reported,
and its readings are never re-run to replace their figures (ruling H2-1).
"""
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

import xlib as X                                                # noqa: E402

PROFILE = "x41-smoke"
PREFIX = "x411"
SESSION = ("Plan 12 Task 5 (x411): the post-fix smoke on the staged release -- the offline skip, the supplement-only "
           "ULs, the own moodle column and the excess row; one boot of " + PROFILE)
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"PREFIX {PREFIX} does not match the driver file {_ME}"
assert PROFILE == "x41-smoke", f"PROFILE {PROFILE} is not this driver's profile"
ARTIFACT = "smoke.json"
MANIFEST_NAME = "MANIFEST.json"
SRV = X.SRV
ADMIN = "client:admin"
USERS = ("admin", "bob")
QUIT_USERS = ("admin", "bob")
REPO = X.REPO
MOD_DIR = "mod/NutritionRevamp"
STAGE_OUT = "release/plan12-x41"
STAGE_ROOT = STAGE_OUT + "/NutritionRevamp"
STAGE_MOD = STAGE_ROOT + "/Contents/mods/NutritionRevamp"
STAGED_CORE = "common/media/lua/shared/NR_Core.lua"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_FILES = {"PZTestKit_Server.lua": LUA_DIR + "/server/PZTestKit_Server.lua",
                 "PZTestKit_Client.lua": LUA_DIR + "/client/PZTestKit_Client.lua",
                 "PZTestKit_Core.lua": LUA_DIR + "/shared/PZTestKit_Core.lua"}
HARNESS_MARKERS = {
    "PZTestKit_Server.lua": ('TK.register("minute.ring", function(argv)', "-- Reply change (016dce05)",
                             'TK.register("item.get", function(argv)', 'TK.register("foodtimer.set", function(argv)'),
    "PZTestKit_Client.lua": ('TK.register("eat.action", function(argv)', 'TK.register("lua.setpath", function(argv)'),
    "PZTestKit_Core.lua": ('TK.register("lua.call", function(argv)', 'TK.register("lua.read", function(argv)',
                           "trueMult = gt:getTrueMultiplier()"),
}
NR = "NutritionRevamp"
MIN_FREE_GB = 12.0
BUDGET_S = 840.0
PHASE_EST_S = {"S0": 25.0, "OFF": 300.0, "C0": 8.0, "MG": 70.0, "COL": 110.0, "XR": 30.0}
PING_TIMEOUT_S = 5
POLL_S = 0.3
S0_WAIT_S = 90.0
MIN_RUNS = 4
LOG_LIMIT = 400
SPAWN_WAIT_S = 2.5
GAME_MIN_S = 0.625               # wall seconds a game minute at true multiplier 1, DayLength 1
# OFF
OFF_PATHS = ("acute.debtH", "acute.winStartH", "acute.winSleptH", "acute.mass90ageH", "acute.lastFedAgeH",
             "acute.lastVigAgeH", "nutrients.lastAgeH", "satiety.nicH")
RING_PATHS = OFF_PATHS
LAST = "nutrients.lastAgeH"
ANCHORS = ("acute.mass90ageH", "acute.lastFedAgeH", "acute.lastVigAgeH")
DEPART_CAP_S = 30.0
AWAY_MULT = 30.0
AWAY_H = 49.0                    # game hours past the away lastAgeH: two days skipped plus the one integrated hour
AWAY_POLL_S = 2.0
AWAY_CAP_S = 150.0
FIRST_CAP_S = 30.0
OFF_SETTLE_MIN = 3.0
OFF_TOL = 1e-6                   # game hours; the ring carries the record's doubles
OFF_TOL_DIRECT = 0.05            # game hours, when only the direct reads place the first step
STEP_CAP_M = 60.0                # NR_Server_Nutrients.lua: dtM = K.clamp(stepM, 0, 60)
WINDOW_H = 24.0                  # K.acute.WINDOW_H
SLEEP_NEED_H = 7.5               # K.acute.SLEEP_NEED_H
NEED_MORE = 1.3                  # NUT.NEED_MORE
REPAY = 0.5                      # K.acute.REPAY
DEBT_MAX = 40.0                  # K.acute.DEBT_MAX
SLEEP_SWITCH = f"{NR}.server.nutrients.sleepDisabled"
# MG
MG_FOOD = "Base.Pasta"
MG_FALLBACK = "Base.Cereal"
UL_KEYS = (("MG", "magnesium", 350.0), ("MG_NIACIN", "niacin", 35.0), ("MG_FOLATE", "folate", 1000.0))
NUT_KEYS = ("magnesium", "niacin", "folate", "selenium")
NUT_PATHS = tuple(f"nutrients.{k}.{f}" for k in NUT_KEYS for f in ("e24", "x")) + (LAST,)
LAND_CAP_S = 60.0
MG_READ_S = 10.0
MG_READ_GAP_S = 1.0
LANDED = f"{NR}.server.intake.stats.landed"
# COL
CLASSES = ("energy", "hydration", "deficiency", "excess", "stimulant", "sleep", "overfull")
COL_PATHS = ("received", "moodles.route") + tuple(f"moodles.levels.{c}" for c in CLASSES)
REQUEST_GAP_S = 5.5              # past NR_Server_Bus.lua REQUEST_GAP_MS (5000)
ARRIVE_CAP_S = 8.0
SLOW_MULT = 0.1
DRIVE_FOOD = "TKX.Mixed650"
DRIVE_EATS = 2
# XR
ROW_CHUNK = 60
ROW_MAX = 240
XR_ROWS = ("nut_magnesium_x", "nut_selenium_x")
ROW_FIELDS = ("key", "text", "valueText", "label", "level")
RUNG_MAX = 3
ECHO_RX = re.compile(r"PZTK: ")
PROBE_RX = re.compile(r"\b(?:lua\.(?:read|global|call|setpath)|minute\.ring|time\.(?:snapshot|multiplier)|item\.get|"
                      r"foodtimer\.set|eat\.action|additem|requestMirror|moodles\.probe|view\.refresh)")
CMD_ECHO_RX = re.compile(r"^\s*(?:lua\.|minute\.ring|time\.|item\.get|foodtimer\.set|eat\.action|additem)")
LOG_RX = re.compile(r"NR_|NutritionRevamp|LuaError|STACK TRACE|lua error|attempted index|tried to call nil|"
                    r"Exception", re.I)
MOD_ERR_RX = re.compile(r"NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server|failed:")

PRED = {
    "OFF_AWAY": {"every away ring row": "the away state of every OFF field", "falsifier": "an away row that moved",
                 "unmeasured": "no away row"},
    "OFF_WIN": {"winStartH at P1": "Q's + gap, + 24 h per window the integrated hour closes", "tolerance": OFF_TOL,
                "falsifier": "any other value (the unfixed: Q's + whole days)",
                "trivial": "the fixed and unfixed values within 0.01 h"},
    "OFF_DEBT": {"debtH at P1": "Q's when no window closes in the integrated hour, else within "
                                "[Q's - REPAY x 24, Q's + k x 7.5 x NEED_MORE]",
                 "falsifier": "outside (about 7.5 h per missed day)", "unmeasured": "gap < 24 h",
                 "void": "sleepDisabled true"},
    "OFF_ANCHORS": {"mass90ageH, lastFedAgeH, lastVigAgeH at P1": "Q's + gap, or A1 when re-laid",
                    "falsifier": "an anchor left at Q's value or at any other", "trivial": "every anchor re-laid"},
    "OFF_NIC": {"nicH at P1": "Q's + gap with NICOTINE_WITHDRAWAL above 0", "trivial": "the stat 0",
                "falsifier": "another value", "unmeasured": "no nicH"},
    "MG": {"magnesium.x at every read with e24 >= 350": 0, "falsifier": "a rung >= 1",
           "unmeasured": "e24 never reached 350"},
    "MG_NIACIN": {"niacin.x at every read with e24 >= 35": 0, "falsifier": "a rung >= 1",
                  "unmeasured": "e24 never reached 35"},
    "MG_FOLATE": {"folate.x at every read with e24 >= 1000": 0, "falsifier": "a rung >= 1",
                  "unmeasured": "e24 never reached 1000"},
    "COL_ZERO": {"onUI at an agreeing read with every level 0": False, "falsifier": "true",
                 "unmeasured": "no such read (route own, moodles enabled)"},
    "COL_RAISED": {"onUI at an agreeing read with a level above 0": True, "falsifier": "false",
                   "unmeasured": "no such read"},
    "XR_MG": {"at Bands with the rung 0": "no row nut_magnesium_x", "falsifier": "the row present",
              "unmeasured": "no Bands read or the rung not 0"},
    "XR_MG_NUM": {"at Numbers with the rung 0": "the row nut_magnesium_x with text 0",
                  "falsifier": "absent or another text", "unmeasured": "no Numbers read or the rung not 0"},
    "XR_SE": {"with nut_selenium_x n > 0": "Bands: text UI_NR_Class_excess_<min(n,3)>; Numbers: text n",
              "falsifier": "absent or another text", "unmeasured": "the rung 0 or no read"},
    "Z": {"mod_error": "none", "admin_lua_error": False, "players": "a list"},
}


# ---------------------------------------------------------------- the session
class Sess:
    """The driver's session: xlib's Xs plus what the phases launch, quit and copy. Faked by --selftest."""

    def __init__(self, xs, server, clients, started, run_dir, launch, tl=None):
        self.xs = xs
        self.out = xs.out
        self.server = server
        self.clients = clients
        self.started = started
        self.run_dir = run_dir
        self.launch = launch
        self.tl = tl
        self.admin_back = True
        self.last_req = None
        self.ring_rows = []

    def mark(self, phase, **kw):
        if self.tl is not None:
            self.tl.mark(phase, **kw)


def num(v):
    return X.num(v)


def fmtnum(v):
    return repr(float(v))


def vals(a):
    return (a or {}).get("values") or {}


def present(a, p):
    a = a or {}
    return p in (a.get("values") or {}) or p in (a.get("tables") or {}) or p in (a.get("types") or {})


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def players_gone(lst):
    """`players` answers a list of usernames, or {} when none are online: true when no QUIT_USERS name is in it."""
    if isinstance(lst, list):
        return not any(u in lst for u in QUIT_USERS)
    return isinstance(lst, dict) and not lst


def players_of(S, tag):
    v = S.xs.step(tag, SRV, "players").get("ack")
    return v if isinstance(v, (list, dict)) else {"unexpected": v}


def lread(S, side, root, paths, tag):
    return S.xs.keep(S.xs.step(tag, side, "lua.read", " ".join([root] + list(paths))))


def poll(S, tag, fn, cap_s, sleep_s=POLL_S):
    """fn() -> (done, reading), polled until done or the cap; xs.check() raises Budget past the wall budget."""
    xs = S.xs
    end = xs.clock() + cap_s
    polls, done, last = [], False, None
    while True:
        done, last = fn()
        polls.append(last)
        if done:
            break
        if xs.clock() >= end:
            xs.note(f"{tag}: not reached inside {cap_s} s")
            break
        xs.check()
        if sleep_s:
            xs.sleep(sleep_s)
    return {"done": done, "last": last, "polls": len(polls),
            "kept": polls[:5] + polls[-5:] if len(polls) > 10 else polls}


def wait_age(S, target, tag, cap_s, sleep_s=POLL_S, keep_mults=None):
    if target is None:
        S.xs.note(f"{tag}: no target age (an unread clock); not waited")
        return {"done": False, "skipped": "no target age"}

    def fn():
        s = S.xs.snap(tag, log=False)
        a = num(s.get("worldAge"))
        if keep_mults is not None:
            keep_mults.append({"wall": s.get("wall"), "worldAge": a, "trueMult": s.get("trueMult"),
                               "mult": s.get("mult")})
        return (a is not None and a >= target), {"worldAge": a, "wall": s.get("wall"), "trueMult": s.get("trueMult")}
    return poll(S, tag, fn, cap_s, sleep_s)


def landed_now(S, tag):
    return num(vals(lread(S, SRV, "_G", [LANDED], tag)).get(LANDED))


def set_mult(S, value, tag):
    r = S.xs.keep(S.xs.step(tag, SRV, "time.multiplier", fmtnum(value)))
    s = S.xs.snap(tag + "_t")
    tm = num(s.get("trueMult"))
    return {"reply": r.get("raw"), "snap": s, "trueMult": tm,
            "ok": tm is not None and abs(tm - value) <= 1e-6 * max(1.0, abs(value))}


def restore_mult(S, value, tag):
    """The multiplier back to the value read before, read back; one retry."""
    r1 = set_mult(S, value, tag)
    if r1["ok"]:
        return {"first": r1, "ok": True}
    r2 = set_mult(S, value, tag + "_retry")
    return {"first": r1, "retry": r2, "ok": r2["ok"]}


def mult_read(S, tag):
    s = S.xs.snap(tag)
    m0 = num(s.get("trueMult"))
    return s, (m0 if m0 is not None and m0 > 0 else 1.0)


def read_pages(S, user, tag):
    """minute.ring <user> read, page after page; each page's document kept for the grade and its file copied."""
    xs = S.xs
    pages, frm = [], None
    for _ in range(12):
        after = time.time() - 1.0
        args = f"{user} read" + ("" if frm is None else f" {frm}")
        r = xs.keep(xs.step(f"{tag}_read", SRV, "minute.ring", args, timeout=60))
        pg = {"reply": {k: r.get(k) for k in ("ok", "from", "rows", "skipped", "next", "more", "oldest", "newest",
                                               "recorded", "overwritten", "errors", "lastError", "result", "error")}}
        name = r.get("result")
        if isinstance(name, str) and name:
            doc = xs.wait_doc(name, after)
            rows = (doc or {}).get("rows_list") or []
            pg["doc_rows"] = len(rows)
            S.ring_rows.extend(rows)
            src = os.path.join(getattr(S.server.bus, "results_dir", ""), name + ".json")
            if doc is not None and os.path.isfile(src) and S.run_dir:
                shutil.copyfile(src, os.path.join(S.run_dir, name + ".json"))
                xs.copied.append(name + ".json")
                pg["file"] = name + ".json"
        pages.append(pg)
        if not r.get("ok") or not r.get("more") or r.get("next") is None:
            break
        frm = r.get("next")
    return pages


def request_mirror(S, tag):
    """requestMirror on admin, REQUEST_GAP_S after the last; the arrival polled (received + 1)."""
    xs = S.xs
    if S.last_req is not None and xs.clock() - S.last_req < REQUEST_GAP_S:
        xs.sleep(REQUEST_GAP_S - (xs.clock() - S.last_req))
    rc0 = num(vals(lread(S, ADMIN, f"{NR}.client", ["received"], tag + "_rc0")).get("received"))
    S.last_req = xs.clock()
    req = xs.keep(xs.step(tag + "_req", ADMIN, "lua.call", f"{NR}.client.requestMirror"))

    def arrived():
        v = num(vals(lread(S, ADMIN, f"{NR}.client", ["received"], tag + "_arr")).get("received"))
        return (v is not None and rc0 is not None and v > rc0), {"received": v}
    a = poll(S, tag + "_arr", arrived, ARRIVE_CAP_S, 0.5)
    return {"rc0": rc0, "request": {k: req.get(k) for k in ("ok", "r1", "err", "raw")}, "arrived": a["done"],
            "polls": a["polls"]}


def levels_of(v):
    return {c: num(v.get(f"moodles.levels.{c}")) for c in CLASSES}


def col_read(S, tag):
    """One column sample: the levels, the probe (level, onUI, route), the levels again, the enabled switch."""
    xs = S.xs
    b = vals(lread(S, ADMIN, f"{NR}.client", COL_PATHS, tag + "_lv0"))
    pr = xs.keep(xs.step(tag + "_probe", ADMIN, "lua.call", f"{NR}.client.moodles.probe overfull"))
    a = vals(lread(S, ADMIN, f"{NR}.client", COL_PATHS, tag + "_lv1"))
    en = xs.keep(xs.step(tag + "_enabled", ADMIN, "lua.call", f"{NR}.client.moodles.isEnabled"))
    lb, la = levels_of(b), levels_of(a)
    return {"tag": tag, "levels": lb, "levels_after": la, "stable": lb == la, "route": b.get("moodles.route"),
            "received": b.get("received"), "probe": [pr.get("r1"), pr.get("r2"), pr.get("r3")],
            "probe_ok": pr.get("ok"), "enabled": en.get("r1"), "wall": pr.get("wall")}


# ---------------------------------------------------------------- phases
def phase_S0(S):
    xs = S.xs
    P = S.out["phases"]["S0"] = {}
    P["ping"] = xs.ping("S0_ping")
    P["players"] = players_of(S, "S0_players")
    P["time"] = xs.snap("S0_time")

    def ready():
        a = lread(S, SRV, "_G", [f"{NR}.server.minute.stats.runs", f"{NR}.server.store.records.admin",
                                 f"{NR}.server.store.records.bob", SLEEP_SWITCH], "S0_runs")
        v = vals(a)
        runs = num(v.get(f"{NR}.server.minute.stats.runs"))
        recs = all(present(a, f"{NR}.server.store.records.{u}") for u in USERS)
        return (recs and runs is not None and runs >= MIN_RUNS), {"runs": runs, "records": recs,
                                                                  "sleepDisabled": v.get(SLEEP_SWITCH)}
    P["wait"] = poll(S, "S0_wait", ready, S0_WAIT_S)
    P["sleepDisabled"] = g(P, "wait", "last", "sleepDisabled")
    P["ring_start"] = xs.keep(xs.step("S0_ring", SRV, "minute.ring", "admin start " + " ".join(RING_PATHS)))
    if not P["ring_start"].get("ok"):
        xs.note(f"S0: minute.ring start failed: {P['ring_start'].get('error') or P['ring_start'].get('raw')}")
    P["record"] = lread(S, SRV, "record:admin", OFF_PATHS, "S0_rec")
    S.out.setdefault("col_reads", []).append(col_read(S, "S0_col"))


def phase_OFF(S):
    xs = S.xs
    P = S.out["phases"]["OFF"] = {"rejoined": False}
    P["pre_snap"] = xs.snap("OFF_pre_t")
    P["pre"] = lread(S, SRV, "record:admin", OFF_PATHS, "OFF_pre")
    S.admin_back = False
    for user in QUIT_USERS:
        c = S.clients.get(user)
        q = {"wall0": xs.wall()}
        try:
            q["rc"] = c.quit() if c is not None else None
        except Exception as e:                 # noqa: BLE001 - recorded
            q["error"] = f"{type(e).__name__}: {e}"
        q["wall1"] = xs.wall()
        S.clients.pop(user, None)
        S.mark("client_quit", user=user, which="first", rc=q.get("rc"))
        P[f"quit_{user}"] = q

    def departed():
        r = xs.step("OFF_players", SRV, "players")
        lst = r.get("ack")
        return players_gone(lst), {"players": lst, "wall": r.get("wall_before")}
    P["depart"] = poll(S, "OFF_depart", departed, DEPART_CAP_S, 0.5)
    P["away"] = lread(S, SRV, "record:admin", OFF_PATHS, "OFF_away")
    P["away_snap"] = xs.snap("OFF_away_t")
    lq = num(vals(P["away"]).get(LAST))
    if lq is None:
        lq = num(vals(P["pre"]).get(LAST))
    P["Lq"] = lq
    P["mult0_snap"], P["restore_to"] = mult_read(S, "OFF_mult0")
    P["true_mults"] = []
    try:
        P["raise"] = set_mult(S, AWAY_MULT, "OFF_raise")
        P["true_mults"].append({"at": "raise", "trueMult": P["raise"]["trueMult"]})
        P["away_wait"] = wait_age(S, None if lq is None else lq + AWAY_H, "OFF_away_wait", AWAY_CAP_S, AWAY_POLL_S,
                                  keep_mults=P["true_mults"])
    finally:
        P["restore"] = restore_mult(S, P["restore_to"], "OFF_restore")
        P["restored_ok"] = P["restore"]["ok"]
    P["back_snap"] = xs.snap("OFF_back_t")
    if not P["restored_ok"]:
        xs.note("OFF: the multiplier did not read back the value read before; admin does not rejoin under it")
        return
    P["launch_snap"] = xs.snap("OFF_launch_t")
    P["launch"] = S.launch(S, "admin", "c1b")
    S.admin_back = True
    P["rejoined"] = True
    P["join_snap"] = xs.snap("OFF_join_t")

    def moved():
        a = lread(S, SRV, "record:admin", OFF_PATHS, "OFF_first")
        v = num(vals(a).get(LAST))
        return (v is not None and lq is not None and v != lq), a
    P["first"] = poll(S, "OFF_first", moved, FIRST_CAP_S)
    j0 = num(P["join_snap"].get("worldAge"))
    P["settle"] = wait_age(S, None if j0 is None else j0 + OFF_SETTLE_MIN / 60.0, "OFF_settle",
                           OFF_SETTLE_MIN * GAME_MIN_S * 4 + 10)
    P["post"] = lread(S, SRV, "record:admin", OFF_PATHS, "OFF_post")
    P["pages"] = read_pages(S, "admin", "OFF_ring")
    P["ring_stop"] = xs.keep(xs.step("OFF_ring_stop", SRV, "minute.ring", "admin stop"))
    S.out["world_changes"]["left_in_place"].append(
        "OFF: admin and bob quit; the clock ran at AWAY_MULT and was restored; admin rejoined from a fresh fixture "
        "restore in <run>/c1b; bob did not rejoin")


def phase_C0(S):
    S.out["phases"]["C0"] = {"read": True}
    S.out.setdefault("col_reads", []).append(col_read(S, "C0_col"))


def eat_landed(S, food, tag):
    """spawn (xlib, confirmed by item.get), landed read, eat_queue, the landing polled; returns the row."""
    xs = S.xs
    row = {"food": food, "spawn": xs.spawn(food, 1, tag + "_spawn")}
    if not row["spawn"]["confirmed"]:
        row["void"] = "spawn not confirmed"
        return row
    base = landed_now(S, tag + "_landed0")
    row["landed0"] = base
    row["eat"] = xs.eat_queue(food, tag)
    if row["eat"].get("queued") is not True:
        row["void"] = f"eat.action did not queue: {row['eat'].get('raw') or row['eat'].get('error')}"
        return row

    def landed():
        v = landed_now(S, tag + "_land")
        return (base is not None and v is not None and v >= base + 1), {"landed": v}
    row["land"] = poll(S, tag + "_land", landed, LAND_CAP_S, 0.5)
    row["landed"] = row["land"]["done"]
    if not row["landed"]:
        row["void"] = "the landing did not read inside LAND_CAP_S"
    return row


def phase_MG(S):
    xs = S.xs
    P = S.out["phases"]["MG"] = {"reads": [], "void": None}
    P["pre"] = vals(lread(S, SRV, "record:admin", NUT_PATHS, "MG_pre"))
    P["eats"] = [eat_landed(S, MG_FOOD, "MG")]
    if not P["eats"][-1].get("landed"):
        xs.note(f"MG: {MG_FOOD}: {P['eats'][-1].get('void')}; the fallback {MG_FALLBACK} is tried")
        P["eats"].append(eat_landed(S, MG_FALLBACK, "MG_fb"))
    if not P["eats"][-1].get("landed"):
        P["void"] = f"no eat landed: {[e.get('void') for e in P['eats']]}"
        return
    P["food"] = P["eats"][-1]["food"]
    end = xs.clock() + MG_READ_S
    while True:
        a = lread(S, SRV, "record:admin", NUT_PATHS, "MG_read")
        P["reads"].append({"wall": a.get("wall"), "values": vals(a)})
        if xs.clock() >= end:
            break
        xs.check()
        xs.sleep(MG_READ_GAP_S)
    S.out["world_changes"]["left_in_place"].append(f"MG: admin ate {P['food']}")


def phase_COL(S):
    P = S.out["phases"]["COL"] = {"drive": None}
    P["arrival"] = request_mirror(S, "COL_m1")
    r = col_read(S, "COL_col1")
    S.out.setdefault("col_reads", []).append(r)
    if any((v or 0) > 0 for v in r["levels"].values()):
        return
    D = P["drive"] = {"eats": []}
    D["mult0_snap"], D["restore_to"] = mult_read(S, "COL_mult0")
    try:
        D["slow"] = set_mult(S, SLOW_MULT, "COL_slow")
        for i in range(DRIVE_EATS):
            e = eat_landed(S, DRIVE_FOOD, f"COL_eat{i + 1}")
            D["eats"].append(e)
            if e.get("void"):
                break
        D["arrival"] = request_mirror(S, "COL_m2")
        S.out["col_reads"].append(col_read(S, "COL_col2"))
    finally:
        D["restore"] = restore_mult(S, D["restore_to"], "COL_restore")
    S.out["world_changes"]["left_in_place"].append(f"COL: the overfull drive, {DRIVE_EATS} x {DRIVE_FOOD}")


def rows_read(S, tag):
    """The view's level, the mirror's two rungs, the row keys and the two excess rows' fields."""
    root = f"{NR}.client"
    a = lread(S, ADMIN, root, ["view.level", "view.lastLevel", "received", "mirror.nut_magnesium_x",
                               "mirror.nut_selenium_x", "view.rows"], tag + "_head")
    v = vals(a)
    n = num((a.get("tables") or {}).get("view.rows")) or 0
    n = int(min(n, ROW_MAX))
    keys = []
    for lo in range(1, n + 1, ROW_CHUNK):
        hi = min(n, lo + ROW_CHUNK - 1)
        b = vals(lread(S, ADMIN, root, [f"view.rows.{i}.key" for i in range(lo, hi + 1)], f"{tag}_keys{lo}"))
        keys.extend(b.get(f"view.rows.{i}.key") for i in range(lo, hi + 1))
    rows = {}
    for k in XR_ROWS:
        if k in keys:
            i = keys.index(k) + 1
            rows[k] = vals(lread(S, ADMIN, f"{root}.view.rows.{i}", ROW_FIELDS, f"{tag}_{k}"))
    return {"level": num(v.get("view.level")), "lastLevel": num(v.get("view.lastLevel")),
            "received": v.get("received"), "mg_x": num(v.get("mirror.nut_magnesium_x")),
            "se_x": num(v.get("mirror.nut_selenium_x")), "n": n, "keys": keys, "rows": rows}


def phase_XR(S):
    xs = S.xs
    P = S.out["phases"]["XR"] = {"reads": {}}
    P["arrival"] = request_mirror(S, "XR_m")
    lv0 = num(vals(lread(S, ADMIN, f"{NR}.client", ["view.level"], "XR_lv0")).get("view.level"))
    P["level_before"] = lv0
    try:
        for lv in (2, 3):
            P[f"set{lv}"] = xs.keep(xs.step(f"XR_set{lv}", ADMIN, "lua.setpath", f"{NR}.client.view.level {lv}"))
            P[f"refresh{lv}"] = xs.keep(xs.step(f"XR_refresh{lv}", ADMIN, "lua.call", f"{NR}.client.view.refresh true"))
            P["reads"][str(lv)] = rows_read(S, f"XR_L{lv}")
    finally:
        back = lv0 if lv0 is not None else 2
        P["restore"] = xs.keep(xs.step("XR_restore", ADMIN, "lua.setpath", f"{NR}.client.view.level {int(back)}"))
        P["restore_refresh"] = xs.keep(xs.step("XR_restore_refresh", ADMIN, "lua.call",
                                               f"{NR}.client.view.refresh true"))
        P["level_after"] = num(vals(lread(S, ADMIN, f"{NR}.client", ["view.level"], "XR_lv1")).get("view.level"))


def phase_Z(S):
    xs = S.xs
    P = S.out["phases"]["Z"] = {}
    errs = [str(e) for e in (S.server.errors if S.server is not None else [])]
    P["server_mod_error_lines"] = [e[:400] for e in errs if MOD_ERR_RX.search(e) and not ECHO_RX.search(e)
                                   and not CMD_ECHO_RX.search(e)][:20]
    P["admin_parked"] = xs.parked()
    P["mem"] = xs.mem("Z")
    P["bus_dead"] = xs.bus_dead
    P["players"] = players_of(S, "Z_players")
    P["time"] = xs.snap("Z_time")


PHASES = (("S0", phase_S0, False), ("OFF", phase_OFF, False), ("C0", phase_C0, True), ("MG", phase_MG, True),
          ("COL", phase_COL, True), ("XR", phase_XR, True))


def body(S):
    xs = S.xs
    S.out["budget"] = {"BUDGET_S": BUDGET_S, "checks": []}
    for name, fn, needs_admin in PHASES:
        if xs.bus_dead:
            break
        est = PHASE_EST_S.get(name, 0.0)
        S.out["budget"]["checks"].append({"phase": name, "wall": xs.wall(), "estimate": est})
        if xs.wall() + est > BUDGET_S:
            xs.note(f"wall budget: {name} (estimate {est} s) would end past {BUDGET_S} s at wall {xs.wall()} s; "
                    "skipped with every later phase but Z")
            break
        if needs_admin and not S.admin_back:
            xs.note(f"{name}: skipped, admin has not rejoined")
            continue
        xs.run_phase(name, lambda fn=fn: fn(S))
        if xs.parked():
            S.out["abort"] = f"admin parked in the debugger after phase {name}"
            break
    xs.run_phase("Z", lambda: phase_Z(S))


# ---------------------------------------------------------------- grading
def off_points(rows):
    """Q (the state just before the first step back), the away rows and P1 (the first step back) off the ring."""
    rows = sorted((r for r in rows if isinstance(r, dict) and r.get("s") is not None), key=lambda r: r["s"])
    i0 = next((i for i, r in enumerate(rows) if r.get("on") is False), None)
    if i0 is None:
        return {"away": [], "q": None, "p1": None, "p0_is_away": None}
    j = i0
    while j < len(rows) and rows[j].get("on") is False:
        j += 1
    away = [r for r in rows[i0:j] if not r.get("norec")]
    q = away[-1] if away else None
    lq = num(q.get(LAST)) if q else None
    p1, p0_is_away = None, True
    for r in rows[j:]:
        if r.get("norec") or r.get("on") is not True:
            continue
        v = num(r.get(LAST))
        if v is not None and lq is not None and v != lq:
            p1 = r
            break
        if v == lq:
            q, p0_is_away = r, False
    return {"away": away, "q": q, "p1": p1, "p0_is_away": p0_is_away}


def skip_gap(a1, lq):
    step_m = (a1 - lq) * 60
    return (step_m - STEP_CAP_M) / 60 if step_m > STEP_CAP_M else 0.0


def close_windows(w, a1):
    k = 0
    while a1 - w >= WINDOW_H:
        w += WINDOW_H
        k += 1
    return w, k


def near(a, b, tol):
    return a is not None and b is not None and abs(a - b) <= tol + 1e-12 * max(abs(a), abs(b))


def grade_off(xs, P, rows, sleep_disabled):
    pts = off_points(rows)
    src = "ring"
    q, p1, tol = pts["q"], pts["p1"], OFF_TOL
    if q is None or p1 is None:
        src, tol = "direct", OFF_TOL_DIRECT
        q = vals(P.get("away"))
        p1 = vals(g(P, "first", "last")) if g(P, "first", "done") else {}
    obs = {"source": src, "tolerance": tol, "away_rows": len(pts["away"]), "q_from_away_row": pts["p0_is_away"],
           "q": {k: q.get(k) for k in OFF_PATHS} if q else None,
           "p1": {k: p1.get(k) for k in OFF_PATHS + ("s", "age", "NICOTINE_WITHDRAWAL")} if p1 else None}
    # OFF_AWAY
    if pts["away"]:
        a0 = pts["away"][0]
        moved = [r.get("s") for r in pts["away"] if any(r.get(k) != a0.get(k) for k in OFF_PATHS)]
        xs.grade("OFF_AWAY", "falsified" if moved else "as_predicted",
                 {"away_rows": len(pts["away"]), "moved": moved[:10]}, PRED["OFF_AWAY"]["falsifier"],
                 samples=pts["away"])
    else:
        xs.grade("OFF_AWAY", "unmeasured", {"away_rows": 0}, PRED["OFF_AWAY"]["falsifier"])
    lq, a1 = num((q or {}).get(LAST)), num((p1 or {}).get(LAST))
    if lq is None or a1 is None or a1 == lq:
        for k in ("OFF_WIN", "OFF_DEBT", "OFF_ANCHORS", "OFF_NIC"):
            xs.grade(k, "unmeasured", obs, "no first step back read")
        return obs
    gap = skip_gap(a1, lq)
    obs.update({"Lq": lq, "A1": a1, "gap_h": gap, "missed_days": gap / WINDOW_H,
                "true_mults": [m.get("trueMult") for m in (P.get("true_mults") or [])][:40]})
    # OFF_WIN
    wq, w1 = num(q.get("acute.winStartH")), num(p1.get("acute.winStartH"))
    if wq is None or w1 is None:
        xs.grade("OFF_WIN", "unmeasured", obs, "winStartH not read")
        k_fix = None
    else:
        w_skip = wq + gap if wq <= lq else wq
        w_exp, k_fix = close_windows(w_skip, a1)
        w_unf, k_unf = close_windows(wq, a1)
        sep = abs(w_exp - w_unf) >= 0.01
        ok = near(w1, w_exp, tol)
        v = ("as_predicted" if sep else "trivial") if ok else "falsified"
        xs.grade("OFF_WIN", v, {"winStartH_q": wq, "winStartH_1": w1, "expected": w_exp, "windows_closed": k_fix,
                                "unfixed": w_unf, "unfixed_windows": k_unf, "separated": sep, "gap_h": gap},
                 PRED["OFF_WIN"]["falsifier"], samples=[w1])
        obs["unfixed_windows"] = k_unf
    # OFF_DEBT
    dq, d1 = num(q.get("acute.debtH")), num(p1.get("acute.debtH"))
    dobs = {"debtH_q": dq, "debtH_1": d1, "windows_closed": k_fix, "gap_h": gap, "sleepDisabled": sleep_disabled,
            "unfixed_expected": (min(DEBT_MAX, dq + SLEEP_NEED_H * obs.get("unfixed_windows", 0))
                                 if dq is not None else None)}
    if sleep_disabled is True:
        xs.grade("OFF_DEBT", "void", dobs, "the sleep factor is off (sleepDisabled)")
    elif gap < WINDOW_H:
        xs.grade("OFF_DEBT", "unmeasured", dobs, "gap < 24 h: no missed day to book")
    elif dq is None or d1 is None or k_fix is None:
        xs.grade("OFF_DEBT", "unmeasured", dobs, "debtH or winStartH not read")
    else:
        if k_fix == 0:
            ok = near(d1, dq, tol)
            dobs["allowed"] = [dq, dq]
        else:
            lo, hi = max(0.0, dq - REPAY * WINDOW_H), min(DEBT_MAX, dq + k_fix * SLEEP_NEED_H * NEED_MORE)
            ok = lo - tol <= d1 <= hi + tol
            dobs["allowed"] = [lo, hi]
        xs.grade("OFF_DEBT", "as_predicted" if ok else "falsified", dobs, PRED["OFF_DEBT"]["falsifier"],
                 samples=[d1])
    if gap < 0.01:
        for k in ("OFF_ANCHORS", "OFF_NIC"):
            xs.grade(k, "unmeasured", {"gap_h": gap}, "no offline time skipped")
        return obs
    # OFF_ANCHORS
    per, moved, relaid, bad = {}, [], [], []
    for k in ANCHORS:
        xq, x1 = num(q.get(k)), num(p1.get(k))
        if xq is None or x1 is None or xq > lq:
            per[k] = {"q": xq, "1": x1, "class": "not graded"}
            continue
        exp = xq + gap
        if near(x1, exp, tol):
            c = "moved"
            moved.append(k)
        elif near(x1, a1, tol):
            c = "relaid"
            relaid.append(k)
        else:
            c = "unmoved" if near(x1, xq, tol) else "other"
            bad.append(k)
        per[k] = {"q": xq, "1": x1, "expected": exp, "class": c}
    if bad:
        v = "falsified"
    elif moved:
        v = "as_predicted"
    elif relaid:
        v = "trivial"
    else:
        v = "unmeasured"
    xs.grade("OFF_ANCHORS", v, {"anchors": per, "gap_h": gap}, PRED["OFF_ANCHORS"]["falsifier"],
             samples=moved + relaid + bad)
    # OFF_NIC
    nq, n1 = num(q.get("satiety.nicH")), num(p1.get("satiety.nicH"))
    nw = num(p1.get("NICOTINE_WITHDRAWAL"))
    nobs = {"nicH_q": nq, "nicH_1": n1, "NICOTINE_WITHDRAWAL": nw, "gap_h": gap}
    if nq is None or n1 is None:
        xs.grade("OFF_NIC", "unmeasured", nobs, "no nicH")
    elif nw is None or nw <= 0:
        xs.grade("OFF_NIC", "trivial", nobs, "the stat reads 0: the writer lays nicH at the minute")
    else:
        exp = nq + gap if nq <= lq else nq
        nobs["expected"] = exp
        xs.grade("OFF_NIC", "as_predicted" if near(n1, exp, tol) else "falsified", nobs,
                 PRED["OFF_NIC"]["falsifier"], samples=[n1])
    return obs


def grade_mg(xs, P):
    if not P:
        for name, _, _ in UL_KEYS:
            xs.grade(name, "void" if xs.phase_dead("MG") else "unmeasured", None, "phase MG not run")
        return
    if P.get("void"):
        for name, _, _ in UL_KEYS:
            xs.grade(name, "void", {"void": P["void"]}, "no eat landed")
        return
    if xs.phase_dead("MG"):
        for name, _, _ in UL_KEYS:
            xs.grade(name, "void", None, "the bus died inside MG")
        return
    for name, key, ul in UL_KEYS:
        pts = [(num(r["values"].get(f"nutrients.{key}.e24")), num(r["values"].get(f"nutrients.{key}.x")))
               for r in P.get("reads") or []]
        samples = [(e, x) for e, x in pts if e is not None and e >= ul and x is not None]
        bad = [(e, x) for e, x in samples if x >= 1]
        xs.grade(name, "falsified" if bad else "as_predicted",
                 {"food": P.get("food"), "ul": ul, "reads": len(pts), "samples": len(samples),
                  "e24_max": max((e for e, _ in pts if e is not None), default=None), "bad": bad[:5],
                  "selenium": [(num(r["values"].get("nutrients.selenium.e24")),
                                num(r["values"].get("nutrients.selenium.x"))) for r in (P.get("reads") or [])][-1:]},
                 PRED[name]["falsifier"], samples=samples)


def grade_col(xs, reads):
    zero, raised, bad_zero, bad_raised, skipped = [], [], [], [], []
    for r in reads:
        lv = r.get("levels") or {}
        if (not r.get("stable") or r.get("route") != "own" or r.get("enabled") is not True
                or any(v is None for v in lv.values()) or not isinstance(g(r, "probe")[1], bool)):
            skipped.append(r.get("tag"))
            continue
        on = r["probe"][1]
        if any(v > 0 for v in lv.values()):
            raised.append(r["tag"])
            if on is not True:
                bad_raised.append(r["tag"])
        else:
            zero.append(r["tag"])
            if on is not False:
                bad_zero.append(r["tag"])
    obs = {"reads": [{k: r.get(k) for k in ("tag", "levels", "stable", "route", "probe", "enabled")} for r in reads],
           "skipped": skipped}
    xs.grade("COL_ZERO", "falsified" if bad_zero else "as_predicted", dict(obs, samples=zero, bad=bad_zero),
             PRED["COL_ZERO"]["falsifier"], samples=zero)
    xs.grade("COL_RAISED", "falsified" if bad_raised else "as_predicted", dict(obs, samples=raised, bad=bad_raised),
             PRED["COL_RAISED"]["falsifier"], samples=raised)


def grade_xr(xs, P):
    reads = (P or {}).get("reads") or {}
    b, n = reads.get("2"), reads.get("3")
    b_ok = b is not None and b.get("level") == 2
    n_ok = n is not None and n.get("level") == 3
    obs = {"bands": b, "numbers": n, "bands_valid": b_ok, "numbers_valid": n_ok}
    # XR_MG
    if b_ok and b.get("mg_x") == 0:
        present_ = "nut_magnesium_x" in (b.get("keys") or [])
        xs.grade("XR_MG", "falsified" if present_ else "as_predicted", {"present": present_, "mg_x": 0},
                 PRED["XR_MG"]["falsifier"], samples=[b])
    else:
        xs.grade("XR_MG", "unmeasured", {"bands_valid": b_ok, "mg_x": (b or {}).get("mg_x")},
                 "no Bands read or the rung not 0")
    if n_ok and n.get("mg_x") == 0:
        row = (n.get("rows") or {}).get("nut_magnesium_x")
        ok = row is not None and str(row.get("text")) == "0"
        xs.grade("XR_MG_NUM", "as_predicted" if ok else "falsified", {"row": row}, PRED["XR_MG_NUM"]["falsifier"],
                 samples=[n])
    else:
        xs.grade("XR_MG_NUM", "unmeasured", {"numbers_valid": n_ok, "mg_x": (n or {}).get("mg_x")},
                 "no Numbers read or the rung not 0")
    # XR_SE
    checked, bad = [], []
    for lv, rd, valid in ((2, b, b_ok), (3, n, n_ok)):
        if not valid or rd.get("se_x") is None or rd["se_x"] <= 0:
            continue
        x = rd["se_x"]
        want = f"UI_NR_Class_excess_{int(min(max(x, 1), RUNG_MAX))}" if lv == 2 else str(int(x))
        row = (rd.get("rows") or {}).get("nut_selenium_x")
        checked.append(lv)
        if row is None or str(row.get("text")) != want:
            bad.append({"level": lv, "want": want, "row": row})
    xs.grade("XR_SE", "falsified" if bad else "as_predicted", dict(obs, checked=checked, bad=bad),
             PRED["XR_SE"]["falsifier"], samples=checked)


def grade_z(xs, out):
    Z = out["phases"].get("Z") or {}
    if not Z:
        xs.grade("Z", "unmeasured", None, "phase Z not run")
        return
    lines = list(Z.get("server_mod_error_lines") or []) + list(g(out, "logs", "server", "mod_errors") or [])
    answered = isinstance(Z.get("players"), list) or Z.get("players") == {}
    ok = not lines and not out.get("admin_lua_error") and not Z.get("admin_parked") and answered
    xs.grade("Z", "as_predicted" if ok else "falsified",
             {"mod_error_lines": lines[:20], "admin_lua_error": out.get("admin_lua_error"),
              "admin_parked": Z.get("admin_parked"), "players": Z.get("players")},
             "a mod error line, admin parked, or no players answer", samples=[1])


def grade_all(S):
    xs, out = S.xs, S.out
    ph = out["phases"]
    rows = S.ring_rows
    out.setdefault("readings", {})["ring_rows"] = len(rows)
    OFF = ph.get("OFF")
    if not OFF:
        for k in ("OFF_AWAY", "OFF_WIN", "OFF_DEBT", "OFF_ANCHORS", "OFF_NIC"):
            xs.grade(k, "unmeasured", None, "phase OFF not run")
    elif xs.phase_dead("OFF"):
        for k in ("OFF_AWAY", "OFF_WIN", "OFF_DEBT", "OFF_ANCHORS", "OFF_NIC"):
            xs.grade(k, "void", None, "the bus died inside OFF")
    else:
        out["readings"]["OFF"] = grade_off(xs, OFF, rows, g(ph, "S0", "sleepDisabled"))
    grade_mg(xs, ph.get("MG"))
    grade_col(xs, out.get("col_reads") or [])
    if not ph.get("XR") or xs.phase_dead("XR"):
        for k in ("XR_MG", "XR_MG_NUM", "XR_SE"):
            xs.grade(k, "void" if xs.phase_dead("XR") else "unmeasured", None, "phase XR not run")
    else:
        grade_xr(xs, ph["XR"])
    grade_z(xs, out)


def read_logs(S, every):
    xs, out = S.xs, S.out
    L = out["logs"] = {"patterns": {"log": LOG_RX.pattern, "mod_err": MOD_ERR_RX.pattern,
                                    "echo_excluded": ECHO_RX.pattern, "probe_excluded": PROBE_RX.pattern},
                       "clients": {}}
    if S.server is not None and getattr(S.server, "log_path", None):
        lines, skipped = X.grep_noecho(S.server.log_path, LOG_RX, LOG_LIMIT, ECHO_RX, PROBE_RX)
        L["server"] = {"lines": lines, "excluded": skipped,
                       "mod_errors": [ln for ln in lines if MOD_ERR_RX.search(ln) and not CMD_ECHO_RX.search(ln)][:20]}
    for c in every:
        u = getattr(c, "username", "?")
        con = getattr(c, "console", None)
        if not con:
            continue
        lines, skipped = X.grep_noecho(con, LOG_RX, 60, ECHO_RX, PROBE_RX)
        L["clients"].setdefault(u, []).append({"console": os.path.relpath(con, S.run_dir) if S.run_dir else con,
                                               "lines": lines, "excluded": skipped})
    xs.note("logs read")


def fresh_out():
    return {"steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
            "readings": {}, "memory": [], "col_reads": [], "world_changes": {"left_in_place": []}}


# ---------------------------------------------------------------- the live run
def launch_real(make_client, prof, rec_fx):
    def launch(S, user, sub):
        c, restored = make_client(os.path.join(S.run_dir, sub), user, S.server, rec_fx,
                                  safemode=prof.safemode, launcher=prof.launcher)
        c.start()
        S.started.append(c)
        S.clients[user] = c
        S.mark("client_launch", user=user, which=sub, restored=restored)
        took = c.wait_ready(timeout=prof.client_timeout)
        S.mark("client_ready", user=user, which=sub, took=took)
        return {"restored": restored, "ready_took": took}
    return launch


def main():
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_client, make_server, teardown, verify   # noqa: E402
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import release_pack as RP                                       # noqa: E402

    prof = profile.load(PROFILE)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(PREFIX)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = fresh_out()
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=BUDGET_S, ping_timeout_s=PING_TIMEOUT_S, spawn_wait_s=SPAWN_WAIT_S, predictions=PRED)
    xs.path = os.path.join(run_dir, ARTIFACT)
    S = Sess(xs, None, clients, started, run_dir, launch_real(make_client, prof, rec_fx), tl=tl)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session": SESSION, "users": list(prof.users), "profile": prof.report(),
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
        "harness_lua_dirty": git_dirty(LUA_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "meta": {"staged_mod": STAGE_MOD, "staged_manifest": f"{STAGE_ROOT}/{MANIFEST_NAME}",
                 "staging": "python tools/release_pack.py stage mod/NutritionRevamp --out release/plan12-x41 (the "
                            "controller, before the boot); the driver checks it and never stages",
                 "ring_note": "a ring row is sampled inside EveryOneMinute before the mod's queue drains that minute",
                 "skip_note": "NR_Server_Nutrients.lua caps a step at 60 game minutes and K.acute.skipRecord moves "
                              "every world-age anchor laid at or before the previous step's age by the rest"},
        "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                      if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict,
                                                                             re.Pattern))
                      and k not in ("REPO", "PRED")},
        "predictions": PRED,
        "world_changes": {"restored": "fixture two restored into the run dir (server and both client caches)",
                          "left_in_place": []},
    })
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    mg = out["manifest_gate"] = X.manifest_gate(RP, REPO, MOD_DIR, STAGE_ROOT, STAGE_MOD, MANIFEST_NAME, git_say,
                                                git_dirty)
    try:
        with open(os.path.join(REPO, *STAGE_MOD.split("/"), *STAGED_CORE.split("/")), encoding="utf-8") as fh:
            m = re.search(r'version\s*=\s*"([^"]+)"', fh.read())
        mg["staged_version"] = m.group(1) if m else None
    except OSError as e:
        mg["staged_version_error"] = f"{type(e).__name__}: {e}"
    want = f'"value": "{mg.get("staged_version")}"'
    vrows = [v for v in prof.verify if v.get("args") == f"{NR}.version"]
    mg["verify_rows_match"] = bool(vrows) and all(str(v.get("expect")) == want for v in vrows)
    if not (mg["ok"] and mg["verify_rows_match"]):
        xs.refuse(f"the staged copy does not match the clean tree or the verify rows: {mg!r}; not started")
    found = {}
    for fname, rel in HARNESS_FILES.items():
        try:
            with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        found[fname] = {mk: (mk in text) for mk in HARNESS_MARKERS[fname]}
    out["meta"]["harness_markers_found"] = found
    if not all(all(d.values()) for d in found.values()):
        xs.refuse("a repository harness file lacks a marker; not started")
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    try:
        shutil.copyfile(os.path.join(REPO, STAGE_ROOT, MANIFEST_NAME), os.path.join(run_dir, MANIFEST_NAME))
        xs.copied.append(MANIFEST_NAME)
    except OSError as e:
        out["meta"]["manifest_copy_error"] = f"{type(e).__name__}: {e}"
    server = None
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = S.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        tl.mark("server_started")
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        dm, ok = X.deployed_marker_check(run_dir, list(HARNESS_MARKERS), HARNESS_MARKERS)
        xs.mem("ready")
        xs.persist()
        if xs.abort_on_missing_marker(dm, ok):
            pass
        elif not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            body(S)
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)
        xs.finish(teardown, hard_kill, every, read_logs=lambda: read_logs(S, every), grade_all=lambda: grade_all(S))
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "gap_h": g(out, "readings", "OFF", "gap_h"), "bus_dead": out.get("bus_dead"),
                      "error": out.get("error"), "abort": out.get("abort"), "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])


# ---------------------------------------------------------------- the offline grade simulation (--selftest)
# A fake world behind a fake ask: the reply shapes are the harness's own (`ping` "pong", `players` a list or {},
# `time.snapshot` {worldAge, hour, minutes, mult, trueMult, wall}, `time.multiplier` "mult=<t> eff=<e>", `lua.read`
# {ok, side, root, n, values, tables, types, missing}, `lua.call` {ok, side, path, nargs, r1, r2, r3}, `lua.setpath`
# {ok, side, path, before, after}, `item.get` a dict with id or a string, `foodtimer.set` {requested, before, set,
# after}, `eat.action` {queued, fraction, spawned, itemId, validStart, maxTime}, `minute.ring` start {ok, armed, ...},
# read {ok, from, rows, next, more, result, ...} with the page document {rows_list} through server.bus.wait_result).
# Its mod steps admin's record once a game minute the way the fixed code does; a defect flag makes it step the way
# the defect would.
DOSES = {"Base.Pasta": {"magnesium": 480.021, "niacin": 65.002089, "folate": 3541.287, "selenium": 572.4024},
         "Base.Cereal": {"magnesium": 894.292}, "TKX.Mixed650": {}}
ULS = {"magnesium": (350.0, True), "niacin": (35.0, True), "folate": (1000.0, True), "selenium": (400.0, False)}


class _FakeBus:
    def __init__(self, world, results_dir):
        self.world = world
        self.results_dir = results_dir

    def wait_result(self, name, timeout=30, after=None):
        return self.world.docs.get(name)


class _FakeServer:
    def __init__(self, world, results_dir):
        self.world = world
        self.bus = _FakeBus(world, results_dir)
        self.errors = world.errors
        self.log_path = None

    def rcon(self, cmd):
        m = re.match(r'additem "(\w+)" "([\w.]+)" (\d+)', cmd)
        if m:
            self.world.inv.add(m.group(2))
            return True, "Item added"
        return False, "unknown"


class _FakeClient:
    def __init__(self, world, user):
        self.world, self.username, self.seen, self.alive, self.console = world, user, {}, True, None

    def quit(self):
        self.world.online[self.username] = False
        self.alive = False
        return 0

    def kill(self):
        self.alive = False


class _FakeWorld:
    def __init__(self, flags, results_dir):
        self.f = flags
        self.results_dir = results_dir
        self.now = 1000.0
        self.age = 100.0
        self.mult = 1.0
        self.online = {"admin": True, "bob": True}
        self.rec = {"acute": {"debtH": 2.0, "winStartH": 90.5, "winSleptH": 0.0, "mass90ageH": 10.0,
                              "lastFedAgeH": 99.0, "lastVigAgeH": -1e9},
                    "nutrients": {"lastAgeH": 100.0, **{k: {"e24": 0.0, "x": 0} for k in ULS}},
                    "satiety": {"nicH": 99.5}}
        self.landed, self.runs = 0, 10
        self.inv = set()
        self.pending = []
        self.dose = {}
        self.ring, self.docs = None, {}
        self.errors = ["ERROR NR_Server_Nutrients.lua:353: attempted index of non-table"] if flags.get("z") else []
        self.client = {"received": 0, "mirror": {}, "levels": {c: 0 for c in CLASSES}, "view_level": 2,
                       "last_level": 2, "rows": {}, "onUI": False}
        self.stomach_min = 0.0
        self._rebuild()

    def clock(self):
        return self.now

    def sleep(self, s):
        self.advance(max(0.0, s))

    def advance(self, dt):
        self.now += dt
        new_age = self.age + dt * self.mult / (GAME_MIN_S * 60)
        n = int(math.floor(new_age * 60)) - int(math.floor(self.age * 60))
        if self.mult > 5:
            n = min(n, 1)                          # the minute scheduler overruns at a raised clock (#1813)
        self.age = new_age
        for _ in range(max(0, n)):
            self._event()

    def _event(self):
        if self.ring is not None:
            r = {"s": len(self.ring) + 1, "age": self.age, "on": self.online["admin"],
                 "NICOTINE_WITHDRAWAL": 0.3 if self.f.get("smoker") else 0.0}
            for p in RING_PATHS:
                sect, key = p.split(".")
                r[p] = self.rec[sect][key]
            self.ring.append(r)
        if self.online["admin"] or self.f.get("away_moves"):
            self._step()
        if self.stomach_min > 0:
            self.stomach_min -= 1

    def _step(self):
        a, n = self.rec["acute"], self.rec["nutrients"]
        age = self.age
        step_m = (age - n["lastAgeH"]) * 60
        dt_m = min(max(step_m, 0.0), STEP_CAP_M)
        from_h = n["lastAgeH"]
        n["lastAgeH"] = age
        if dt_m <= 0:
            return
        if step_m > STEP_CAP_M and not self.f.get("off"):
            gap = (step_m - STEP_CAP_M) / 60
            for k in ("winStartH", "mass90ageH", "lastFedAgeH", "lastVigAgeH"):
                if a[k] <= from_h:
                    a[k] = a[k] + gap
            s = self.rec["satiety"]
            if s["nicH"] <= from_h:
                s["nicH"] = s["nicH"] + gap
        while age - a["winStartH"] >= WINDOW_H:
            a["debtH"] = min(DEBT_MAX, a["debtH"] + SLEEP_NEED_H)
            a["winStartH"] += WINDOW_H
            a["winSleptH"] = 0.0
        if not self.f.get("smoker"):
            self.rec["satiety"]["nicH"] = age
        for k, (ul, supp) in ULS.items():
            st = n[k]
            st["e24"] = st["e24"] * math.exp(-dt_m / 1440) + self.dose.get(k, 0.0)
            st["x"] = 1 if (st["e24"] >= ul and (not supp or self.f.get("ul"))) else 0
        self.dose = {}

    # the client's mirror and view (K.view.rows and the column, as the fixed code builds them, or as a defect would)
    def _rebuild(self):
        c = self.client
        m = c["mirror"]
        lv = c["view_level"]
        rows = [{"key": k, "text": "UI_NR_Class_" + k + "_0"} for k in CLASSES[:6]]
        for key in ("magnesium", "niacin", "folate"):
            x = m.get(f"nut_{key}_x", 0)
            if lv >= 2:
                rows.append({"key": f"nut_{key}_g", "text": "UI_NR_Grade_1"})
            if lv >= 3:
                rows.append({"key": f"nut_{key}_p", "text": "100.0%"})
                if x > 0 or not self.f.get("xr_num"):
                    rows.append({"key": f"nut_{key}_x", "text": str(int(x))})
            elif lv == 2 and (x > 0 or (key == "magnesium" and self.f.get("xr_mg"))):
                rows.append({"key": f"nut_{key}_x", "text": f"UI_NR_Class_excess_{max(1, min(int(x), 3))}"})
        xs_ = m.get("nut_selenium_x", 0)
        if xs_ > 0 and not self.f.get("xr_se"):
            rows.append({"key": "nut_selenium_x",
                         "text": str(int(xs_)) if lv >= 3 else f"UI_NR_Class_excess_{min(int(xs_), 3)}"})
        c["rows"] = {i + 1: r for i, r in enumerate(rows)}
        c["last_level"] = lv
        levels = c["levels"]
        levels["excess"] = min(3, max([m.get(f"nut_{k}_x", 0) for k in ULS] + [0]))
        levels["overfull"] = 1 if m.get("stomach", 0) > 0 else 0
        anyl = any(v > 0 for v in levels.values())
        c["onUI"] = True if self.f.get("col_zero") else (False if self.f.get("col_raised") else anyl)

    def _mirror(self):
        n = self.rec["nutrients"]
        self.client["mirror"] = {**{f"nut_{k}_x": n[k]["x"] for k in ULS}, "stomach": self.stomach_min}
        self.client["received"] += 1
        self._rebuild()

    # the bus
    def ask(self, node, cmd, args="", timeout=20):
        self.advance(1.3)
        if node.startswith("client:"):
            user = node.split(":", 1)[1]
            if not self.online.get(user):
                return {"error": f"UnknownSide: {user} is not attached"}
            return self._client(cmd, args)
        return self._server(cmd, args)

    def _resolve(self, root, path):
        segs = path.split(".")
        if segs[0] == "_G":
            root, segs = self._G(), segs[1:]
        node = root
        for s in segs:
            if isinstance(node, dict) and s in node:
                node = node[s]
            elif isinstance(node, dict) and s.isdigit() and int(s) in node:
                node = node[int(s)]
            else:
                return False, "nil"
        return True, node

    def _read(self, root, paths, side):
        out = {"ok": True, "side": side, "root": "?", "n": len(paths), "values": {}, "tables": {}, "types": {},
               "missing": {}}
        for p in paths:
            ok, v = self._resolve(root, p)
            if not ok:
                out["missing"][p] = v
            elif isinstance(v, dict):
                out["tables"][p] = len(v)
            elif isinstance(v, bool) or isinstance(v, (int, float, str)):
                out["values"][p] = v
            else:
                out["types"][p] = "userdata"
        return out

    def _G(self):
        online = {u: "player" for u, on in self.online.items() if on}
        return {"NutritionRevamp": {"server": {
            "minute": {"stats": {"runs": self.runs}}, "intake": {"stats": {"landed": self.landed}},
            "store": {"records": {"admin": self.rec, "bob": {"acute": {}}}},
            "nutrients": {"sleepDisabled": False}, "players": {"online": online}}}}

    def _server(self, cmd, args):
        a = args.split()
        if cmd == "ping":
            return "pong"
        if cmd == "players":
            lst = [u for u, on in self.online.items() if on]
            return lst if lst else {}
        if cmd == "time.snapshot":
            return {"worldAge": self.age, "hour": int(self.age) % 24, "minutes": int(self.age * 60) % 60,
                    "mult": self.mult, "trueMult": self.mult, "wall": int(self.now * 1000)}
        if cmd == "time.multiplier":
            self.mult = float(a[0])
            return f"mult={self.mult} eff={self.mult}"
        if cmd == "lua.read":
            root = self.rec if a[0] == "record:admin" else self._G()
            return self._read(root, a[1:], "server")
        if cmd == "item.get":
            if a[1] in self.inv:
                return {"id": 4411, "fullType": a[1], "calories": 1.0}
            return f"no item {a[1]} in {a[0]}'s inventory"
        if cmd == "foodtimer.set":
            return {"requested": 0, "before": 0, "set": True, "after": 0}
        if cmd == "minute.ring":
            if a[1] == "start":
                self.ring = []
                return {"ok": True, "side": "server", "user": a[0], "armed": True, "cap": 4320, "paths": a[2:]}
            if a[1] == "stop":
                return {"ok": True, "side": "server", "user": a[0], "stopped": True, "recorded": len(self.ring or [])}
            frm = int(a[2]) if len(a) > 2 else 1
            rows = (self.ring or [])[frm - 1:frm - 1 + 720]
            nxt = frm + len(rows)
            name = f"minute-ring-{a[0]}-{frm}"
            self.docs[name] = {"rows_list": [dict(r) for r in rows]}
            with open(os.path.join(self.results_dir, name + ".json"), "w", encoding="utf-8") as fh:
                json.dump(self.docs[name], fh)
            return {"ok": True, "side": "server", "user": a[0], "from": frm, "rows": len(rows), "next": nxt,
                    "more": nxt <= len(self.ring or []), "result": name}
        return {"error": f"RuntimeError: no fake for {cmd}"}

    def _client(self, cmd, args):
        a = args.split()
        c = self.client
        croot = {"received": c["received"], "mirror": c["mirror"],
                 "moodles": {"route": "own", "levels": dict(c["levels"])},
                 "view": {"level": c["view_level"], "lastLevel": c["last_level"], "rows": c["rows"]}}
        if cmd == "lua.read":
            root = a[0]
            node = croot
            if root.startswith(f"{NR}.client."):
                for s in root[len(f"{NR}.client."):].split("."):
                    node = node[int(s)] if s.isdigit() else node[s]
            return self._read(node, a[1:], "client")
        if cmd == "lua.call":
            path = a[0]
            base = {"ok": True, "side": "client", "path": path, "nargs": len(a) - 1}
            if path.endswith("requestMirror"):
                self._mirror()
                return dict(base, r1=True)
            if path.endswith("moodles.probe"):
                return dict(base, r1=c["levels"].get(a[1], 0), r2=c["onUI"], r3="own")
            if path.endswith("moodles.isEnabled"):
                return dict(base, r1=True)
            if path.endswith("view.refresh"):
                self._rebuild()
                return dict(base, r1=True)
        if cmd == "lua.setpath":
            before = c["view_level"]
            c["view_level"] = int(a[1])
            return {"ok": True, "side": "client", "path": a[0], "before": before, "after": c["view_level"]}
        if cmd == "eat.action":
            if a[0] not in self.inv:
                return {"queued": True, "spawned": "client", "itemId": 1}
            self.inv.discard(a[0])
            dose = dict(DOSES.get(a[0], {}))
            if self.f.get("lowdose") and "magnesium" in dose:
                dose["magnesium"] = 100.0
            raise_ = not (self.f.get("no_raise") and a[0] == MG_FOOD)
            if not raise_:
                dose.pop("selenium", None)
            for k, v in dose.items():
                self.dose[k] = self.dose.get(k, 0.0) + v
            self.landed += 1
            if raise_:
                self.stomach_min = 30
            return {"queued": True, "fraction": 1.0, "spawned": "found", "itemId": 4411, "validStart": True,
                    "maxTime": 120}
        return {"error": f"RuntimeError: no fake for {cmd}"}


def simulate(flags):
    tmp = tempfile.mkdtemp(prefix="x411-selftest-")
    res = os.path.join(tmp, "pzt-results")
    os.makedirs(res)
    try:
        world = _FakeWorld(flags, res)
        server = _FakeServer(world, res)
        clients = {u: _FakeClient(world, u) for u in USERS}
        out = fresh_out()
        xs = X.Xs(out, node=lambda side: side, server=server, clients=clients, ask=world.ask, budget_s=BUDGET_S,
                  ping_timeout_s=PING_TIMEOUT_S, spawn_wait_s=SPAWN_WAIT_S, predictions=PRED, clock=world.clock,
                  sleep=world.sleep)

        def launch(S, user, sub):
            world.advance(60.0)                    # the client boots while admin is away, at the restored clock
            world.online[user] = True
            S.clients[user] = _FakeClient(world, user)
            return {"restored": True, "ready_took": 60.0}
        S = Sess(xs, server, clients, list(clients.values()), tmp, launch)
        body(S)
        out["admin_lua_error"] = False
        grade_all(S)
        return {k: v["verdict"] for k, v in out["verdicts"].items()}, out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


SELFTEST = (
    ("fixed", {"smoker": True}, {
        "OFF_AWAY": "as_predicted", "OFF_WIN": "as_predicted", "OFF_DEBT": "as_predicted",
        "OFF_ANCHORS": "as_predicted", "OFF_NIC": "as_predicted", "MG": "as_predicted", "MG_NIACIN": "as_predicted",
        "MG_FOLATE": "as_predicted", "COL_ZERO": "as_predicted", "COL_RAISED": "as_predicted",
        "XR_MG": "as_predicted", "XR_MG_NUM": "as_predicted", "XR_SE": "as_predicted", "Z": "as_predicted"}),
    ("broken_b", {"smoker": True, "off": True, "ul": True, "col_zero": True, "xr_se": True, "z": True}, {
        "OFF_WIN": "falsified", "OFF_DEBT": "falsified", "OFF_ANCHORS": "falsified", "OFF_NIC": "falsified",
        "MG": "falsified", "MG_NIACIN": "falsified", "MG_FOLATE": "falsified", "COL_ZERO": "falsified",
        "XR_MG": "unmeasured", "XR_SE": "falsified", "Z": "falsified"}),
    ("broken_c", {"away_moves": True, "col_raised": True, "xr_mg": True, "xr_num": True, "lowdose": True}, {
        "OFF_AWAY": "falsified", "OFF_ANCHORS": "unmeasured", "MG": "unmeasured", "MG_NIACIN": "as_predicted",
        "COL_ZERO": "as_predicted", "COL_RAISED": "falsified", "XR_MG": "falsified", "XR_MG_NUM": "falsified",
        "XR_SE": "as_predicted", "Z": "as_predicted"}),
    ("drive", {"no_raise": True}, {
        "COL_ZERO": "as_predicted", "COL_RAISED": "as_predicted", "XR_SE": "unmeasured", "MG": "as_predicted"}),
)


def selftest():
    fails = []
    for name, flags, want in SELFTEST:
        got, out = simulate(flags)
        errs = {k: v.get("error") for k, v in out.get("phase_errors", {}).items()}
        if errs:
            fails.append(f"{name}: phase errors {errs}")
        for k, v in want.items():
            if got.get(k) != v:
                fails.append(f"{name}: {k} read {got.get(k)!r}, wanted {v!r}")
        for ph, key in (("OFF", "restore"), ("COL", "drive")):
            blk = g(out, "phases", ph, key)
            if ph == "COL" and blk is not None:
                blk = blk.get("restore")
                if name != "drive":
                    fails.append(f"{name}: the overfull drive ran with a level already above 0")
            if blk is not None and blk.get("ok") is not True:
                fails.append(f"{name}: phase {ph}'s multiplier was not restored")
        if name == "drive" and g(out, "phases", "COL", "drive") is None:
            fails.append("drive: the overfull drive did not run")
        print(f"{name}: " + ", ".join(f"{k}={v}" for k, v in sorted(got.items())))
        print(f"  gap_h={g(out, 'readings', 'OFF', 'gap_h')} ring_rows={g(out, 'readings', 'ring_rows')} "
              f"fake_wall={out['phase_walls'].get('Z', {}).get('end')}")
    if fails:
        print("SELFTEST FAILED:\n  " + "\n  ".join(fails))
        return 1
    print("SELFTEST OK: every grade as_predicted on the fixed world and its failing verdict on a broken one")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    main()
