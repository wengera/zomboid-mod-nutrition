"""x183-interface -- Plan 7 Task 11, the interface acceptance, LIVE. Does the interface build (the options page, the
view cache, the panel, the tooltip band, the character-info tab and the moodles) load clean on a dedicated-server
client and do its surfaces do what the client files' headers say they do? TWO boots of this one driver, one after
the other, never at the same time:
  python testing/experiments/x183_interface.py          -> run id prefix `x183`,  profile `x18-interface`
                                                           (PZTestKit + NutritionRevamp + TKX_DeclaredFood: the OWN route)
  python testing/experiments/x183_interface.py --mf     -> run id prefix `x183m`, profile `x18-interface-mf`
                                                           (+ MoodleFramework by workshop_id 3396446795: the FRAMEWORK route)
ONE artifact `interface.json` per boot. Shape: x181_moodleframework.py / x172_itempass.py (step, persist, run_phase,
mod_error, both logs grepped, the artifact copied by the driver). Written BEFORE the first boot with every prediction
in it (both routes) and never edited after either run (CLAUDE.md s5, B3-1/B3-2).

BUILD UNDER TEST (Task 11 build block): HEAD dd9d1ef, mod/ quiescent; NR_Client_ModOptions/View/Panel.lua (c67a01d,
f84c37a, d0a777a), NR_Client_Tooltip.lua (451365d, d83b475, 472ebbc), NR_Client_Tab.lua (0e31ea2), NR_Client_Moodles.lua
+ NR_Kernel_View.lua (9befcdb, dd9d1ef), translations and icons (c71bbcb, 3ca4781), the profiles (4413be4).

THE "UNMEASURED UNTIL x183" HEADER NOTES this boot exists for, and the arm that reads each:
  NR_Client_ModOptions.lua / NR_Client_Panel.lua risk 1 (the layout restore re-adds the panel visible) -> B
     (stats.restoredVisible right after RegisterWindow; the golden fixture's layout.ini carries no NutritionRevamp.panel
     line, so this boot reads the FIRST-registration branch only: a re-add from a saved visible=true line is not
     exercised by a fresh fixture -- stated, not engineered);
  risk 2 (layout.ini written at all on the harness client's exit path) -> G (the file after the client process exits);
  risk 3 (PZAPI.ModOptions:load() at OnGameStart finds ModOptions.ini) -> S0 (modOptions.stats.loads / loadFailures)
     and G (the file after exit);
  NR_Client_Tooltip.lua 1-3 (the band below the box on screen, the setHeight fight, the bottom edge) -> D: the driver
     cannot hover, so stats.draws is read and the three stay UNMEASURED; the band's line source and count are read
     through tooltip.probe (the entry the band would draw), not the draw;
  NR_Client_Tab.lua (AutoCook's shape never run here) -> E (tab.stats.added after player creation) and G (the
     charinfowindow line of layout.ini: the SaveLayout wrap appends the tab's name to tabs=); the torn-off wrap and
     the tab's own render need a click: UNMEASURED;
  NR_Client_Moodles.lua (the bad-side draw on the framework route; the column's inset against the vanilla band
     1238-1270 of x181) -> F (probe deficiency; on the own route the column's x / y / width / height Lua fields, set by
     ISUIElement.new; on the framework route the handle's addedToUIManager, x, y);
  NR_Client_View.lua / Panel (the scrolled rows' clip) -> no wheel is synthesised: UNMEASURED.

ARMS (the plan's Task 11 with the amendments' decisions; deviations listed in out["deviations"]):
  S0 first sight: server error count, the client debugger marker, NR.client.view.level, NR.client.received, the three
     option accessors through lua.call (NutritionRevamp.client.options.key / tooltipLines / moodles), the moodles
     route, modOptions.stats, every surface's stats table, the server's options.visibilityMode.
  A  the mirror's new keys: client NutritionRevamp.client.mirror.nut_vitC_p, nut_vitC_x, nut_vitC_g.
  B  the panel: stats.restoredVisible read first; lua.call NutritionRevamp.client.panel.toggle 0 (r1 true = it opened,
     false = it closed: the branch is the reply, because lua.global cannot index instances[0], a numeric key); opens,
     requests, received polled to +1 within 3 s; renders read twice 3 s apart; toggle again; closes; renders twice
     3 s apart (static).
  C  the gate: trait.local NUTRITIONIST add (CharacterTrait[<name>] takes the enum field name) -> lua.call
     NutritionRevamp.client.requestMirror -> view.level polled to 3 within 3 s; view.hasTrait; rebuilds before/after.
  D  the tooltip: item.spawn Base.Apple, lua.call NutritionRevamp.client.tooltip.probe Base.Apple (r1 count, r2
     source); item.spawn TKX.DeclaredBar, the same; tooltip.stats (draws expected 0: no hover).
  E  the tab: NutritionRevamp.client.tab.stats.*.
  F  the forced deficiency: probe deficiency (baseline), server bus.effects.stats; globalmoddata.setpath
     NutritionRevamp.players admin.nutrients.vitC.p 0.05 (read back; witness.moddata of vitC.p / vitC.g); poll the
     server's pushes every 5 s up to 70 s (PUSH_GAP_MS 60000); 3 s later the client's received, view.classes, probe
     deficiency, moodles.levels.deficiency, moodles.stats; own route: the column's renders twice 3 s apart and its
     x / y / width / height; framework route: handles.deficiency.addedToUIManager / x / y / width / height. If no push
     lands in 70 s the driver pulls once (requestMirror) and says so (the push verdict stays as observed).
  H  tick.rate 20 x 3, server and client armed in the same windows, against x172b's server 10.05/s.
  Z  every stats table again, the NR error counters.
  G  the quit path: client.quit() (the harness `quit` -> quitToDesktop) and the process exit awaited; then the client
     cachedir's Lua/layout.ini and Lua/ModOptions.ini: existence, size, mtime against the client's start, and only the
     lines naming NutritionRevamp, charinfowindow or the [WxH] header (never the whole files).
  I  after teardown: the server log grepped for getText|getTexture|ISUI|NR_Client (limit 400) and the hits naming the
     mod (NutritionRevamp|NR_|nutritionrevamp) kept apart.

PREDICTIONS (written before the first boot; graded in `verdicts` with as_predicted / falsified / trivial / unmeasured):
  S0  server_error_count 0, no client lua_error, view.level 1, received >= 1, options key 39 (ruling T5-1),
      tooltipLines true, moodles true, route "own" (x183) / "framework" (x183m), modOptions loads 1 and loadFailures 0
      (getFileReader("ModOptions.ini", true) creates the file: x181's run dir holds an empty one), server
      options.visibilityMode 1.
  A   nut_vitC_p a number in (0, 1] (a fresh record stamps p = 1), nut_vitC_x 0, nut_vitC_g 1.
  B   restoredVisible false (no saved line); toggle 1 r1 true; opens 1, requests 1, requestFailures 0; received +1
      within 3 s; renders delta > 0 across 3 s; toggle 2 r1 false; closes 1; renders delta 0 across 3 s.
  C   enumFound true, after true; view.level 3 within 3 s of the request; rebuilds +1 (+2 if a push lands in the
      window); hasTrait true.
  D   Base.Apple r1 >= 1, r2 "table"; TKX.DeclaredBar r1 >= 1, r2 "declared"; tooltip.stats.draws 0 (no hover:
      the band's on-screen draw UNMEASURED).
  E   tab.stats.added >= 1, errors 0.
  F   before: probe deficiency level 0; after the write: setpath ok, after 0.05; the record's vitC.g 4 within the poll;
      server pushes +1 within 70 s; client received +1; view.classes deficiency 3; own route: probe r1 3, r2 true,
      r3 "own", levels.deficiency 3, column renders delta > 0, column x 1184 (1280 - 96), y 240, width 40, height 264;
      framework route: probe r1 3 (getLevel on the BAD side, ruling T8-1: value 0.0 under bad3 0.08333), r2 true
      (addedToUIManager), r3 "framework" -- the FIRST bad-side reading (x181 read the good side only).
  H   server ticks per second near x172b's 10.05 (itempass.json phases.A.ticks[*].result.ticksPerSecond); client > 0.
  G   layout.ini exists, written after the client started, carries a `NutritionRevamp.panel` line with visible=false
      (the panel closed in B) and a charinfowindow line whose tabs= ends `,NutritionRevamp` (the SaveLayout wrap);
      ModOptions.ini exists and carries NO NutritionRevamp line: vanilla writes it only from PZAPI.ModOptions:save(),
      whose one caller is MainOptions (media/lua/client/OptionScreens/MainOptions.lua:3766, the options screen's
      apply), and the harness never opens that screen -- the plan's "ModOptions.ini carries the page id" is
      predicted FALSIFIED on this exit path.
  I   zero server-log lines naming the mod among the getText|getTexture|ISUI|NR_Client hits (vanilla's own ISUI
      warnings are expected and are not the mod's).
A parked -debug client (the lua_error marker) is the primary load reading: the remaining arms are skipped, the
session is torn down, both logs grepped, and the file that raised named from the console lines kept.

RULES: 1. A driver is NEVER edited after its run; a post-run edit is a skew note. 2. A reading that comes back
trivial, unmeasured or falsified is written as such, never re-run. 3. One live session at a time.
"""
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
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

MF_ARM = "--mf" in sys.argv[1:]
PROFILE = "x18-interface-mf" if MF_ARM else "x18-interface"
PREFIX = "x183m" if MF_ARM else "x183"
ROUTE = "framework" if MF_ARM else "own"
SESSION = ("Plan 7 Task 11, the interface acceptance: the options page, the view cache, the panel, the tooltip band, "
           "the character-info tab and the moodles (" + ROUTE + " route) on a dedicated-server client; one boot of "
           + PROFILE)
ARTIFACT = "interface.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_DIR = "mod/NutritionRevamp"
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
STORE = "NutritionRevamp.players"
NR = "NutritionRevamp"
X172B_RUN = "x172b-20261006-130714"
X172B_TICKS = (10.052752065293122, 10.050751318539158, 10.053752737407924)  # itempass.json phases.A.ticks[*].result.ticksPerSecond
X181_RUN = "x181-20261006-152607"
X181_BAND = (1238, 1270)                   # the vanilla moodle band's x span at 32 px (#3197)
SETTLE_S = 3.0                             # a read window after a write
GAP_S = 3.0                                # between two render-count reads
POLL_S = 0.5                               # the received / level poll step
POLL_CAP_S = 3.0                           # the received / level poll cap (the plan's "within 3 s")
PUSH_POLL_S = 5.0                          # the server pushes poll step
PUSH_CAP_S = 70.0                          # PUSH_GAP_MS 60000 plus a slow minute's margin
GRADE_WAIT_S = 2.0                         # >= 2 slow minutes at DayLength 1 (0.625 s per game minute)
FORCE_P = "0.05"                           # vitC.p forced below the clinical rung 0.15 (NR_Data_Records.lua vitC ladder)
TICK_S = 20
TICK_N = 3
PRED_KEY = 39                              # Keyboard.KEY_SEMICOLON (ruling T5-1)
PRED_COL = {"x": 1280 - 96, "y": 240, "width": 40, "height": 6 * 44}
LOG_RX = re.compile(r"NR_|NutritionRevamp|TKX|MoodleFramework|MF_ISMoodle|LuaError|STACK TRACE|lua error|"
                    r"attempted index|tried to call nil|Exception", re.I)
LOG_LIMIT = 120
UI_RX = re.compile(r"getText|getTexture|ISUI|NR_Client")
UI_LIMIT = 400
MOD_RX = re.compile(r"NutritionRevamp|NR_|nutritionrevamp")
MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|NR_Client|NR_Kernel|NR_Server")
INI_RX = re.compile(r"NutritionRevamp|charinfowindow|^\[\d+x\d+\]")
SURFACES = {
    "panel": ("opens", "closes", "fits", "renders", "requests", "requestFailures", "creates", "registers",
              "keyPresses", "errors", "restoredVisible"),
    "view": ("rebuilds", "traitReads", "listenerErrors", "errors", "overflowRows"),
    "tooltip": ("draws", "lines", "cacheHits", "errors", "installs", "builds", "invalidations"),
    "tab": ("added", "tornOff", "saves", "renders", "errors", "noView"),
    "moodles": ("sets", "skips", "renders", "errors", "created", "got", "columns"),
    "modOptions": ("loads", "loadFailures"),
}
CLASSES = ("energy", "hydration", "deficiency", "excess", "stimulant", "sleep")
BOX = ("x", "y", "width", "height")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []
cur_phase = {"name": "pre"}


def wall():
    return round(time.time() - t0, 3)


PRED = {
    "S0": {"server_error_count": 0, "client_lua_error": False, "view.level": 1, "received": ">= 1",
           "options.key": PRED_KEY, "options.tooltipLines": True, "options.moodles": True, "moodles.route": ROUTE,
           "modOptions.loads": 1, "modOptions.loadFailures": 0, "server options.visibilityMode": 1},
    "A": {"nut_vitC_p": "a number in (0, 1]", "nut_vitC_x": 0, "nut_vitC_g": 1},
    "B": {"restoredVisible": False, "toggle1_r1": True, "opens": 1, "requests": 1, "requestFailures": 0,
          "received_delta": ">= 1 within 3 s", "open_renders_delta": "> 0", "toggle2_r1": False, "closes": 1,
          "closed_renders_delta": 0},
    "C": {"enumFound": True, "after": True, "view.level": 3, "rebuilds_delta": "1 (2 if a push lands)",
          "hasTrait": True},
    "D": {"Base.Apple": {"r1": ">= 1", "r2": "table"}, "TKX.DeclaredBar": {"r1": ">= 1", "r2": "declared"},
          "draws": "0 (no hover: the on-screen band UNMEASURED)"},
    "E": {"added": ">= 1", "errors": 0},
    "F": {"before_level": 0, "setpath_after": 0.05, "record_g": 4, "pushes_delta": ">= 1 within 70 s",
          "received_delta": ">= 1", "classes.deficiency": 3,
          "probe": ({"r1": 3, "r2": True, "r3": "own", "levels.deficiency": 3, "column_renders_delta": "> 0",
                     "column": PRED_COL} if ROUTE == "own" else
                    {"r1": 3, "r2": True, "r3": "framework", "first_bad_side_reading": True})},
    "H": {"server_tps": f"near {X172B_TICKS} ({X172B_RUN})", "client_tps": "> 0"},
    "G": {"layout.ini": "exists, mtime after the client start, a NutritionRevamp.panel line with visible=false, a "
                        "charinfowindow line whose tabs= ends ,NutritionRevamp",
          "ModOptions.ini": "exists, NO NutritionRevamp line (only MainOptions apply saves it, MainOptions.lua:3766)"},
    "I": {"mod_lines": 0},
}

doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "user": USER, "profile": prof.report(), "route": ROUTE,
    "argv": sys.argv[1:],
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", MOD_DIR),
    "mod_dirty": git_dirty(MOD_DIR)[0],
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_DeclaredFood"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "baseline": {"tick_run": X172B_RUN, "tick_path": "itempass.json phases.A.ticks[*].result.ticksPerSecond",
                 "ticks": list(X172B_TICKS), "band_run": X181_RUN, "band_x": list(X181_BAND)},
    "constants": {k: v for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool))
                  and k not in ("REPO", "LUA_DIR", "MOD_DIR")},
    "predictions": PRED,
    "deviations": [
        "trait.local takes the CharacterTrait enum field name (CharacterTrait[<name>]), so the plan's "
        "`trait.local Nutritionist add` is sent as `trait.local NUTRITIONIST add`.",
        "lua.global cannot index NutritionRevamp.client.panel.instances[0] (a numeric key; lua.global indexes by "
        "string only), so arm B's branch is read off the toggle's own r1 (true = opened) and stats.restoredVisible.",
        "The golden fixture's layout.ini carries no NutritionRevamp.panel line, so the restore's re-add of a saved "
        "visible=true panel (risk 1) is not exercised: only the first-registration branch is read.",
        "ModOptions.ini is predicted to carry no page line on this exit path (MainOptions.lua:3766 is the one save "
        "site), against the plan's expectation; the prediction is the code reading's.",
        "tick.rate is armed on both sides in each of the three windows.",
        "If no effects push lands within 70 s the driver pulls the mirror once (requestMirror) so the moodle reads "
        "still run; the push verdict is graded on the poll alone.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["client-local NUTRITIONIST trait (no packet)", "client-local Base.Apple and "
                                        "TKX.DeclaredBar (the server never hears of them)",
                                        "the admin record's nutrients.vitC.p forced to 0.05"]},
    "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
    "mod_error_checks": [],
}


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": int(e_before * 1000),
           "epoch_ms_after": int(time.time() * 1000), "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def gread(side, name, tag):
    """One lua.global read, kept whole: {resolved, type, value | keyCount | failedAt, wall}."""
    r = step(tag, side, "lua.global", name)
    a = ack(r)
    row = {"name": name, "wall": r["wall_before"], "wall_after": r["wall_after"], "resolved": a.get("resolved"),
           "type": a.get("type")}
    for k in ("value", "keyCount", "failedAt", "stoppedOn", "error"):
        if k in a:
            row[k] = a.get(k)
    if not isinstance(r.get("ack"), dict):
        row["raw"] = r.get("ack")
    return row


def lcall(side, args, tag):
    """One lua.call, its reply kept whole plus its walls."""
    r = step(tag, side, "lua.call", args)
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


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
    return bool(clients) and "lua_error" in getattr(clients[0], "seen", {})


def stats(surface, tag):
    return {k: gread(client, f"{NR}.client.{surface}.stats.{k}", f"{tag}_{surface}_{k}") for k in SURFACES[surface]}


def all_stats(tag):
    return {s: stats(s, tag) for s in SURFACES}


def sv(snap, surface, k):
    return num(val(((snap or {}).get(surface) or {}).get(k)))


def received(tag):
    return num(val(gread(client, f"{NR}.client.received", tag)))


def poll_client(name, target_fn, tag, cap=POLL_CAP_S):
    """Polls one client lua.global until target_fn(value) holds or cap; returns (rows, hit_wall)."""
    rows, end, i = [], time.time() + cap, 0
    while True:
        row = gread(client, name, f"{tag}_p{i}")
        rows.append(row)
        i += 1
        if target_fn(val(row)):
            return rows, row["wall"]
        if time.time() >= end:
            return rows, None
        time.sleep(POLL_S)


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier, "observed": observed,
           "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)


def mod_error(after):
    why = []
    errs = [str(e) for e in (server.errors if server is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    if parked():
        why.append({"client": "lua_error seen (parked in the debugger)"})
    counts = {}
    for s in ("panel", "view", "tooltip", "tab", "moodles"):
        e = num(val(gread(client, f"{NR}.client.{s}.stats.errors", f"chk_{after}_{s}_err")))
        counts[s] = e
        if (e or 0) > 0:
            why.append({f"{s}.errors": e,
                        f"{s}.lastError": val(gread(client, f"{NR}.client.{s}.lastError", f"chk_{after}_{s}_le"))})
    ne = num(val(gread(server, f"{NR}.server.nutrients.stats.errors", f"chk_{after}_nerr")))
    if (ne or 0) > 0:
        why.append({"server.nutrients.errors": ne,
                    "lastError": val(gread(server, f"{NR}.server.nutrients.lastError", f"chk_{after}_nle"))})
    out["mod_error_checks"].append({"after": after, "wall": wall(), "client_error_counts": counts,
                                    "server_nutrients_errors": ne, "found": why})
    return why


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


# ---------------------------------------------------------------- phases
def phase_S0():
    P = out["phases"]["S0"] = {}
    P["tk_version"] = {"client": gread(client, "TK.version", "S0_tkv_c"), "server": gread(server, "TK.version", "S0_tkv_s")}
    P["nr_version"] = {"client": gread(client, f"{NR}.version", "S0_v_c"), "server": gread(server, f"{NR}.version", "S0_v_s")}
    P["view_level"] = gread(client, f"{NR}.client.view.level", "S0_level")
    P["view_optionLevel"] = gread(client, f"{NR}.client.view.optionLevel", "S0_optlevel")
    P["view_hasTrait"] = gread(client, f"{NR}.client.view.hasTrait", "S0_hastrait")
    P["received"] = gread(client, f"{NR}.client.received", "S0_received")
    P["mirror"] = gread(client, f"{NR}.client.mirror", "S0_mirror")
    P["options"] = {k: lcall(client, f"{NR}.client.options.{k}", f"S0_opt_{k}") for k in ("key", "tooltipLines", "moodles")}
    P["route"] = gread(client, f"{NR}.client.moodles.route", "S0_route")
    P["stats"] = all_stats("S0")
    P["server_visibilityMode"] = gread(server, f"{NR}.server.options.visibilityMode", "S0_s_vis")
    P["server_bus_effects"] = {k: gread(server, f"{NR}.server.bus.effects.stats.{k}", f"S0_s_bus_{k}")
                               for k in ("marks", "pushes", "deferred", "failed")}
    P["sentinels"] = {n: gread(client, n, f"S0_sent_{n}") for n in (
        "NR_ClientTooltip_Installed.original", "NR_ClientTab_Installed.createChildren", "NR_ClientPanel_Installed.create",
        "NR_ClientModOptions_Page", "NR_ClientModOptions_Loaded", "NR_ClientMoodles_Installed.boot",
        "NR_ClientView_Installed.create", "NR_Client_Panel", "NR_Client_MoodleColumn", "NR_Client_TabPanel")}
    P["server_side_client_tables"] = {n: gread(server, n, f"S0_s_{n}") for n in (
        f"{NR}.client.panel", f"{NR}.client.tooltip", "NR_ClientTooltip_Installed", "NR_Client_Panel")}
    P["client_seen"] = dict(getattr(client, "seen", {}))
    P["server_errors_at_S0"] = list(server.errors)
    P["mod_error"] = mod_error("S0")
    P["parked"] = parked()


def phase_A():
    P = out["phases"]["A"] = {}
    for k in ("nut_vitC_p", "nut_vitC_x", "nut_vitC_g", "nut_iron_p", "nut_iron_x", "nut_iron_g", "body_band",
              "body_energyState", "fluids_dehydPct", "acute_caf", "acute_debtH"):
        P[k] = gread(client, f"{NR}.client.mirror.{k}", f"A_{k}")


def phase_B():
    P = out["phases"]["B"] = {}
    P["restoredVisible"] = gread(client, f"{NR}.client.panel.stats.restoredVisible", "B_restored")
    P["before"] = stats("panel", "B0")
    P["received_before"] = received("B_rcv0")
    P["toggle1"] = lcall(client, f"{NR}.client.panel.toggle 0", "B_toggle1")
    P["received_poll"], P["received_hit_wall"] = poll_client(
        f"{NR}.client.received", lambda v: num(v) is not None and P["received_before"] is not None
        and num(v) > P["received_before"], "B_rcv")
    P["after_open"] = stats("panel", "B1")
    P["open_r1"] = gread(client, f"{NR}.client.panel.stats.renders", "B_open_r1")
    time.sleep(GAP_S)
    P["open_r2"] = gread(client, f"{NR}.client.panel.stats.renders", "B_open_r2")
    P["view_after_open"] = {k: gread(client, f"{NR}.client.view.{k}", f"B_view_{k}") for k in ("level", "rows")}
    P["overflowRows"] = gread(client, f"{NR}.client.view.stats.overflowRows", "B_overflow")
    P["mod_error_open"] = mod_error("B_open")
    P["toggle2"] = lcall(client, f"{NR}.client.panel.toggle 0", "B_toggle2")
    P["after_close"] = stats("panel", "B2")
    P["closed_r1"] = gread(client, f"{NR}.client.panel.stats.renders", "B_closed_r1")
    time.sleep(GAP_S)
    P["closed_r2"] = gread(client, f"{NR}.client.panel.stats.renders", "B_closed_r2")
    for lbl in ("open", "closed"):
        a, b = num(val(P[f"{lbl}_r1"])), num(val(P[f"{lbl}_r2"]))
        P[f"{lbl}_renders_delta"] = (b - a) if (a is not None and b is not None) else None
        P[f"{lbl}_window_s"] = round(P[f"{lbl}_r2"]["wall"] - P[f"{lbl}_r1"]["wall"], 3)
    P["mod_error"] = mod_error("B")
    P["parked"] = parked()


def phase_C():
    P = out["phases"]["C"] = {}
    P["level_before"] = gread(client, f"{NR}.client.view.level", "C_lvl0")
    P["rebuilds_before"] = gread(client, f"{NR}.client.view.stats.rebuilds", "C_rb0")
    P["received_before"] = received("C_rcv0")
    P["trait_local"] = ack(step("C_trait", client, "trait.local", "NUTRITIONIST add"))
    P["request"] = lcall(client, f"{NR}.client.requestMirror", "C_req")
    P["level_poll"], P["level_hit_wall"] = poll_client(f"{NR}.client.view.level", lambda v: num(v) == 3, "C_lvl")
    P["rebuilds_after"] = gread(client, f"{NR}.client.view.stats.rebuilds", "C_rb1")
    P["received_after"] = received("C_rcv1")
    P["hasTrait"] = gread(client, f"{NR}.client.view.hasTrait", "C_has")
    P["optionLevel"] = gread(client, f"{NR}.client.view.optionLevel", "C_opt")
    P["traitReads"] = gread(client, f"{NR}.client.view.stats.traitReads", "C_tr")
    P["mod_error"] = mod_error("C")


def phase_D():
    P = out["phases"]["D"] = {}
    P["level"] = gread(client, f"{NR}.client.view.level", "D_lvl")
    for full in ("Base.Apple", "TKX.DeclaredBar"):
        tag = "D_" + full.split(".")[1]
        P[full] = {"spawn": step(f"{tag}_spawn", client, "item.spawn", full)["ack"]}
        time.sleep(0.5)
        P[full]["probe"] = lcall(client, f"{NR}.client.tooltip.probe {full}", f"{tag}_probe")
    P["stats"] = stats("tooltip", "D")
    P["lastError"] = gread(client, f"{NR}.client.tooltip.lastError", "D_le")
    P["mod_error"] = mod_error("D")


def phase_E():
    P = out["phases"]["E"] = {}
    P["stats"] = stats("tab", "E")
    P["cls"] = gread(client, f"{NR}.client.tab.cls", "E_cls")
    P["lastError"] = gread(client, f"{NR}.client.tab.lastError", "E_le")


def bus_stats(tag):
    return {k: num(val(gread(server, f"{NR}.server.bus.effects.stats.{k}", f"{tag}_{k}")))
            for k in ("marks", "pushes", "deferred", "failed")}


def record(tag):
    r = step(tag, server, "witness.moddata",
             f"global:{STORE} {USER}.nutrients.vitC.p {USER}.nutrients.vitC.g {USER}.nutrients.epoch")
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    return {"tag": tag, "wall": r["wall_before"], "worldAge": a.get("worldAge"), "missing": a.get("missing"),
            "values": vals}


def moodle_reads(tag):
    R = {"probe": lcall(client, f"{NR}.client.moodles.probe deficiency", f"{tag}_probe"),
         "levels": {c: gread(client, f"{NR}.client.moodles.levels.{c}", f"{tag}_lv_{c}") for c in CLASSES},
         "classes": {c: gread(client, f"{NR}.client.view.classes.{c}", f"{tag}_cl_{c}") for c in CLASSES},
         "stats": stats("moodles", tag)}
    if ROUTE == "own":
        R["column"] = {k: gread(client, f"{NR}.client.moodles.column.{k}", f"{tag}_col_{k}") for k in BOX + ("onUI",)}
    else:
        R["handle"] = {k: gread(client, f"{NR}.client.moodles.handles.deficiency.{k}", f"{tag}_h_{k}")
                       for k in BOX + ("addedToUIManager", "name", "value")}
    return R


def phase_F():
    P = out["phases"]["F"] = {}
    P["before"] = moodle_reads("F0")
    P["bus_before"] = bus_stats("F0_bus")
    P["record_before"] = record("F0_rec")
    P["received_before"] = received("F0_rcv")
    sp = step("F_setpath", server, "globalmoddata.setpath", f"{STORE} {USER}.nutrients.vitC.p {FORCE_P}")
    P["setpath"] = sp["ack"]
    P["setpath_wall"] = sp["wall_after"]
    time.sleep(GRADE_WAIT_S)
    P["record_after_grade_wait"] = record("F1_rec")
    pushes0 = P["bus_before"].get("pushes")
    polls, hit, end, i = [], None, time.time() + PUSH_CAP_S, 0
    while time.time() < end:
        b = bus_stats(f"F_poll{i}")
        b["wall"] = wall()
        polls.append(b)
        i += 1
        if pushes0 is not None and b.get("pushes") is not None and b["pushes"] > pushes0:
            hit = b["wall"]
            break
        time.sleep(PUSH_POLL_S)
    P["push_polls"], P["push_hit_wall"] = polls, hit
    P["push_after_setpath_s"] = round(hit - P["setpath_wall"], 3) if hit is not None else None
    P["record_after_push"] = record("F2_rec")
    time.sleep(SETTLE_S)
    P["received_after_push"] = received("F_rcv1")
    P["pulled"] = None
    if hit is None:
        note("no effects push within the poll cap; the driver pulls the mirror once (requestMirror)")
        P["pulled"] = lcall(client, f"{NR}.client.requestMirror", "F_pull")
        time.sleep(SETTLE_S)
        P["received_after_pull"] = received("F_rcv2")
    P["after"] = moodle_reads("F1")
    P["mirror_vitC"] = {k: gread(client, f"{NR}.client.mirror.nut_vitC_{k}", f"F_m_{k}") for k in ("p", "g", "x")}
    P["after_r1"] = gread(client, f"{NR}.client.moodles.stats.renders", "F_mr1")
    time.sleep(GAP_S)
    P["after_r2"] = gread(client, f"{NR}.client.moodles.stats.renders", "F_mr2")
    a, b = num(val(P["after_r1"])), num(val(P["after_r2"]))
    P["column_renders_delta"] = (b - a) if (a is not None and b is not None) else None
    P["column_window_s"] = round(P["after_r2"]["wall"] - P["after_r1"]["wall"], 3)
    P["mod_error"] = mod_error("F")
    P["parked"] = parked()


def phase_H():
    P = out["phases"]["H"] = {"windows": []}
    for i in range(TICK_N):
        after = time.time()
        arm_s = ack(step(f"H{i}_arm_s", server, "tick.rate", str(TICK_S)))
        arm_c = ack(step(f"H{i}_arm_c", client, "tick.rate", str(TICK_S)))
        w = {"i": i, "arm_server": arm_s, "arm_client": arm_c}
        for side, node, arm in (("server", server, arm_s), ("client", client, arm_c)):
            res = None
            if arm.get("armed"):
                try:
                    res = node.bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 25, after=after)
                except (RuntimeError, TimeoutError, OSError) as e:
                    res = {"error": f"{type(e).__name__}: {e}"}
            w[f"result_{side}"] = res
        P["windows"].append(w)
        persist()


def phase_Z():
    P = out["phases"]["Z"] = {}
    P["stats"] = all_stats("Z")
    P["view_level"] = gread(client, f"{NR}.client.view.level", "Z_level")
    P["received"] = gread(client, f"{NR}.client.received", "Z_received")
    P["client_seen"] = dict(getattr(client, "seen", {}))
    P["mod_error"] = mod_error("Z")


def ini_read(name):
    p = os.path.join(client.cache, "Lua", name)
    row = {"path": os.path.relpath(p, REPO).replace("\\", "/"), "exists": os.path.exists(p)}
    if row["exists"]:
        st = os.stat(p)
        row["size"] = st.st_size
        row["mtime_epoch_ms"] = int(st.st_mtime * 1000)
        row["client_start_epoch_ms"] = int((client.t0 or 0) * 1000)
        row["written_after_client_start"] = st.st_mtime >= (client.t0 or 0)
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
            row["line_count"] = len(lines)
            row["lines_kept"] = [ln.strip()[:400] for ln in lines if INI_RX.search(ln)]
        except OSError as e:
            row["read_error"] = f"{type(e).__name__}: {e}"
    return row


def phase_G():
    P = out["phases"]["G"] = {}
    P["quit_sent_wall"] = wall()
    rc = client.quit(timeout=90)
    P["quit_rc"] = rc
    P["exited_wall"] = wall()
    P["client_alive_after"] = client.alive
    tl.mark("client_quit", user=USER, rc=rc)
    P["layout"] = ini_read("layout.ini")
    P["modoptions"] = ini_read("ModOptions.ini")


def body():
    run_phase("S0", phase_S0)
    if parked():
        out["abort"] = "client parked in the debugger by first sight: a mod file raised at boot"
        return
    run_phase("A", phase_A)
    run_phase("B", phase_B)
    if parked():
        out["abort"] = "client parked in the debugger during the panel arm"
        return
    run_phase("C", phase_C)
    run_phase("D", phase_D)
    if parked():
        out["abort"] = "client parked in the debugger during the tooltip arm"
        return
    run_phase("E", phase_E)
    run_phase("F", phase_F)
    if parked():
        out["abort"] = "client parked in the debugger during the moodle arm"
        return
    run_phase("H", phase_H)
    run_phase("Z", phase_Z)
    run_phase("G", phase_G)


# ---------------------------------------------------------------- grading
def tps(res):
    return (res or {}).get("ticksPerSecond") if isinstance(res, dict) else None


def grade_all():
    ph = out["phases"]
    S = ph.get("S0") or {}
    if S:
        o = S.get("options") or {}
        st = S.get("stats") or {}
        obs = {"server_error_count": out.get("server_error_count"), "client_lua_error": out.get("client_lua_error"),
               "view.level": num(val(S.get("view_level"))), "received": num(val(S.get("received"))),
               "options.key": (o.get("key") or {}).get("r1"), "options.tooltipLines": (o.get("tooltipLines") or {}).get("r1"),
               "options.moodles": (o.get("moodles") or {}).get("r1"), "moodles.route": val(S.get("route")),
               "modOptions.loads": sv(st, "modOptions", "loads"),
               "modOptions.loadFailures": sv(st, "modOptions", "loadFailures"),
               "server options.visibilityMode": num(val(S.get("server_visibilityMode")))}
        ok = (obs["server_error_count"] == 0 and obs["client_lua_error"] is False and obs["view.level"] == 1
              and (obs["received"] or 0) >= 1 and obs["options.key"] == PRED_KEY and obs["options.tooltipLines"] is True
              and obs["options.moodles"] is True and obs["moodles.route"] == ROUTE and obs["modOptions.loads"] == 1
              and obs["modOptions.loadFailures"] == 0 and obs["server options.visibilityMode"] == 1)
        grade("S0", PRED["S0"], obs, "as_predicted" if ok else "falsified",
              "a server error, a parked client, a level other than 1, no mirror, an option value or the route other "
              "than predicted, or the ModOptions load failing")
    else:
        grade("S0", PRED["S0"], None, "unmeasured", "no first-sight reads")
    A = ph.get("A") or {}
    if A:
        p, x, g = num(val(A.get("nut_vitC_p"))), num(val(A.get("nut_vitC_x"))), num(val(A.get("nut_vitC_g")))
        obs = {"nut_vitC_p": p, "nut_vitC_x": x, "nut_vitC_g": g}
        if p is None:
            grade("A", PRED["A"], obs, "unmeasured", "the key did not resolve")
        else:
            grade("A", PRED["A"], obs, "as_predicted" if (0 < p <= 1 and x == 0 and g == 1) else "falsified",
                  "p outside (0, 1], x non-zero or g other than 1")
    else:
        grade("A", PRED["A"], None, "unmeasured", "arm A not run")
    B = ph.get("B") or {}
    if B:
        rb = B.get("received_before")
        rp = [num(val(r)) for r in (B.get("received_poll") or [])]
        rmax = max([v for v in rp if v is not None], default=None)
        a1, a2 = B.get("after_open") or {}, B.get("after_close") or {}
        obs = {"restoredVisible": val(B.get("restoredVisible")),
               "restoredVisible_resolved": (B.get("restoredVisible") or {}).get("resolved"),
               "toggle1_r1": (B.get("toggle1") or {}).get("r1"), "opens": num(val(a1.get("opens"))),
               "requests": num(val(a1.get("requests"))), "requestFailures": num(val(a1.get("requestFailures"))),
               "received_before": rb, "received_max_in_poll": rmax, "received_hit_wall": B.get("received_hit_wall"),
               "toggle1_wall": (B.get("toggle1") or {}).get("wall"),
               "open_renders": [val(B.get("open_r1")), val(B.get("open_r2"))],
               "open_renders_delta": B.get("open_renders_delta"), "open_window_s": B.get("open_window_s"),
               "toggle2_r1": (B.get("toggle2") or {}).get("r1"), "closes": num(val(a2.get("closes"))),
               "closed_renders": [val(B.get("closed_r1")), val(B.get("closed_r2"))],
               "closed_renders_delta": B.get("closed_renders_delta"), "closed_window_s": B.get("closed_window_s")}
        if obs["open_renders_delta"] is None:
            grade("B", PRED["B"], obs, "unmeasured", "a render count did not read")
        else:
            ok = (obs["restoredVisible"] is False and obs["toggle1_r1"] is True and obs["opens"] == 1
                  and obs["requests"] == 1 and obs["requestFailures"] == 0 and B.get("received_hit_wall") is not None
                  and obs["open_renders_delta"] > 0 and obs["toggle2_r1"] is False and obs["closes"] == 1
                  and obs["closed_renders_delta"] == 0)
            grade("B", PRED["B"], obs, "as_predicted" if ok else "falsified",
                  "the restore leaving it visible, the open not counted or not requesting, no mirror within 3 s, the "
                  "count static while open or climbing while closed")
    else:
        grade("B", PRED["B"], None, "unmeasured", "arm B not run")
    C = ph.get("C") or {}
    if C:
        tlc = C.get("trait_local") or {}
        r0, r1 = num(val(C.get("rebuilds_before"))), num(val(C.get("rebuilds_after")))
        obs = {"enumFound": tlc.get("enumFound"), "before": tlc.get("before"), "after": tlc.get("after"),
               "request_r1": (C.get("request") or {}).get("r1"), "level_before": num(val(C.get("level_before"))),
               "level_last": num(val((C.get("level_poll") or [{}])[-1])), "level_hit_wall": C.get("level_hit_wall"),
               "request_wall": (C.get("request") or {}).get("wall"), "rebuilds_before": r0, "rebuilds_after": r1,
               "rebuilds_delta": (r1 - r0) if (r0 is not None and r1 is not None) else None,
               "received_before": C.get("received_before"), "received_after": C.get("received_after"),
               "hasTrait": val(C.get("hasTrait"))}
        ok = (obs["enumFound"] is True and obs["after"] is True and obs["level_hit_wall"] is not None
              and obs["rebuilds_delta"] in (1, 2) and obs["hasTrait"] is True)
        grade("C", PRED["C"], obs, "as_predicted" if ok else "falsified",
              "the trait not added, the level not 3 within 3 s of the request, or no rebuild")
    else:
        grade("C", PRED["C"], None, "unmeasured", "arm C not run")
    D = ph.get("D") or {}
    if D:
        ap = (D.get("Base.Apple") or {}).get("probe") or {}
        dp = (D.get("TKX.DeclaredBar") or {}).get("probe") or {}
        obs = {"level": num(val(D.get("level"))), "Base.Apple": {"r1": ap.get("r1"), "r2": ap.get("r2")},
               "TKX.DeclaredBar": {"r1": dp.get("r1"), "r2": dp.get("r2")},
               "draws": num(val((D.get("stats") or {}).get("draws"))),
               "builds": num(val((D.get("stats") or {}).get("builds")))}
        ok = ((num(ap.get("r1")) or 0) >= 1 and ap.get("r2") == "table" and (num(dp.get("r1")) or 0) >= 1
              and dp.get("r2") == "declared")
        grade("D", PRED["D"], obs, "as_predicted" if ok else "falsified",
              "a probe count of 0 or a source other than table / declared",
              {"band_on_screen": "unmeasured (the driver cannot hover; stats.draws counts only hovered draws)"})
    else:
        grade("D", PRED["D"], None, "unmeasured", "arm D not run")
    E = ph.get("E") or {}
    if E:
        obs = {k: num(val((E.get("stats") or {}).get(k))) for k in SURFACES["tab"]}
        grade("E", PRED["E"], obs, "as_predicted" if ((obs["added"] or 0) >= 1 and obs["errors"] == 0) else "falsified",
              "no tab added at player creation, or a tab error",
              {"torn_off_and_tab_render": "unmeasured (no click synthesised)"})
    else:
        grade("E", PRED["E"], None, "unmeasured", "arm E not run")
    F = ph.get("F") or {}
    if F:
        bp = ((F.get("before") or {}).get("probe") or {})
        ap = ((F.get("after") or {}).get("probe") or {})
        rec2 = ((F.get("record_after_push") or {}).get("values") or {})
        rec1 = ((F.get("record_after_grade_wait") or {}).get("values") or {})
        b0 = (F.get("bus_before") or {}).get("pushes")
        polls = F.get("push_polls") or []
        b1 = polls[-1].get("pushes") if polls else None
        obs = {"before_level": bp.get("r1"), "before_onUI": bp.get("r2"), "setpath": F.get("setpath"),
               "record_g_after_wait": rec1.get(f"{USER}.nutrients.vitC.g"),
               "record_p_after_wait": rec1.get(f"{USER}.nutrients.vitC.p"),
               "record_g_after_push": rec2.get(f"{USER}.nutrients.vitC.g"),
               "pushes_before": b0, "pushes_last_poll": b1, "push_hit_wall": F.get("push_hit_wall"),
               "push_after_setpath_s": F.get("push_after_setpath_s"), "pulled": F.get("pulled") is not None,
               "received_before": F.get("received_before"), "received_after_push": F.get("received_after_push"),
               "received_after_pull": F.get("received_after_pull"),
               "classes.deficiency": num(val(((F.get("after") or {}).get("classes") or {}).get("deficiency"))),
               "probe": {"r1": ap.get("r1"), "r2": ap.get("r2"), "r3": ap.get("r3")},
               "levels.deficiency": num(val(((F.get("after") or {}).get("levels") or {}).get("deficiency"))),
               "column_renders": [val(F.get("after_r1")), val(F.get("after_r2"))],
               "column_renders_delta": F.get("column_renders_delta"), "column_window_s": F.get("column_window_s")}
        if ROUTE == "own":
            obs["column"] = {k: val(((F.get("after") or {}).get("column") or {}).get(k)) for k in BOX + ("onUI",)}
        else:
            obs["handle"] = {k: val(((F.get("after") or {}).get("handle") or {}).get(k))
                             for k in BOX + ("addedToUIManager", "name", "value")}
        pushed = F.get("push_hit_wall") is not None
        lvl_ok = ap.get("r1") == 3 and ap.get("r2") is True and ap.get("r3") == ROUTE and obs["classes.deficiency"] == 3
        if ROUTE == "own":
            lvl_ok = lvl_ok and obs["levels.deficiency"] == 3 and (num(obs["column_renders_delta"]) or 0) > 0
        if ap.get("r1") is None:
            grade("F", PRED["F"], obs, "unmeasured", "the probe did not answer")
        else:
            grade("F", PRED["F"], obs, "as_predicted" if (pushed and lvl_ok and bp.get("r1") == 0) else "falsified",
                  "no push within 70 s, the class not 3 after it, the moodle level not 3 or not on the UI manager, "
                  "or a non-zero baseline", {"push_verdict": "as_predicted" if pushed else "falsified",
                                             "moodle_verdict": "as_predicted" if lvl_ok else "falsified"})
    else:
        grade("F", PRED["F"], None, "unmeasured", "arm F not run")
    H = ph.get("H") or {}
    ws = H.get("windows") or []
    st = [tps(w.get("result_server")) for w in ws]
    ct = [tps(w.get("result_client")) for w in ws]
    if not any(v is not None for v in st + ct):
        grade("H", PRED["H"], None, "unmeasured", "no tick-rate result")
    else:
        sn = [v for v in st if isinstance(v, (int, float))]
        obs = {"server_tps": st, "client_tps": ct,
               "server_ratio_to_x172b": [v / (sum(X172B_TICKS) / len(X172B_TICKS)) for v in sn]}
        ok = len(sn) == TICK_N and all(abs(v - 10.05) < 0.5 for v in sn) and all(
            isinstance(v, (int, float)) and v > 0 for v in ct)
        grade("H", PRED["H"], obs, "as_predicted" if ok else "falsified",
              "a server window more than 0.5/s off x172b's 10.05, or a client window absent or zero")
    G = ph.get("G") or {}
    if G:
        lay, mo = G.get("layout") or {}, G.get("modoptions") or {}
        kept = lay.get("lines_kept") or []
        panel = [ln for ln in kept if ln.startswith("NutritionRevamp.panel")]
        ciw = [ln for ln in kept if ln.startswith("charinfowindow")]
        tabs = None
        if ciw:
            m = re.search(r"tabs=(\S+)", ciw[0])
            tabs = m.group(1) if m else None
        mo_lines = [ln for ln in (mo.get("lines_kept") or []) if "NutritionRevamp" in ln]
        obs = {"quit_rc": G.get("quit_rc"), "layout_exists": lay.get("exists"),
               "layout_written_after_start": lay.get("written_after_client_start"), "panel_lines": panel,
               "charinfowindow_lines": ciw, "tabs": tabs, "modoptions_exists": mo.get("exists"),
               "modoptions_size": mo.get("size"), "modoptions_line_count": mo.get("line_count"),
               "modoptions_nr_lines": mo_lines}
        lay_ok = (lay.get("exists") is True and lay.get("written_after_client_start") is True and len(panel) == 1
                  and "visible=false" in panel[0] and tabs is not None and tabs.endswith(",NutritionRevamp"))
        mo_ok = mo.get("exists") is True and not mo_lines
        grade("G", PRED["G"], obs, "as_predicted" if (lay_ok and mo_ok) else "falsified",
              "layout.ini not rewritten at the quit, no panel line or a visible one, the tab missing from tabs=, or "
              "a NutritionRevamp line in ModOptions.ini",
              {"layout_verdict": "as_predicted" if lay_ok else "falsified",
               "modoptions_verdict": "as_predicted" if mo_ok else "falsified"})
    else:
        grade("G", PRED["G"], None, "unmeasured", "the quit arm was not run")
    logs = out.get("logs") or {}
    ui = logs.get("server_ui")
    if ui is None:
        grade("I", PRED["I"], None, "unmeasured", "no server log grep")
    else:
        mod = logs.get("server_ui_mod") or []
        grade("I", PRED["I"], {"ui_lines": len(ui), "ui_limit": UI_LIMIT, "mod_lines": len(mod), "mod_kept": mod[:20]},
              "as_predicted" if not mod else "falsified", "a getText / getTexture / ISUI / NR_Client line naming the mod")


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

try:
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    out["server_launch_wall"] = wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    tl.mark("server_started")
    client, _ = make_client(run_dir, USER, server, rec_fx)
    out["client_start_wall"] = wall()
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["boot"] = {"server_launch_to_started_s": getattr(server, "t_started", None),
                   "client_markers_s": dict(getattr(client, "seen", {})),
                   "server_started_wall": out.get("server_started_wall"),
                   "client_start_wall": out.get("client_start_wall"),
                   "session_ready_wall": out.get("session_ready_wall")}
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)), "client": sorted(set(client.mods_not_found))}
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
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        out["client_seen"] = dict(getattr(clients[0], "seen", {})) if clients else None
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_t_started"] = getattr(server, "t_started", None)
            ui = grep_file(server.log_path, UI_RX, UI_LIMIT)
            out["logs"] = {"server": grep_file(server.log_path, LOG_RX, LOG_LIMIT),
                           "server_ui": ui, "server_ui_mod": [ln for ln in ui if MOD_RX.search(ln)],
                           "limits": {"log": LOG_LIMIT, "ui": UI_LIMIT},
                           "patterns": {"log": LOG_RX.pattern, "ui": UI_RX.pattern, "mod": MOD_RX.pattern}}
            if clients:
                out["logs"]["client"] = grep_file(clients[0].console, LOG_RX, LOG_LIMIT)
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                  "error": out.get("error"), "body_error": out.get("body_error"), "abort": out.get("abort"),
                  "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                  "summary_error": out.get("summary_error"), "run_id": run_id}, indent=1, default=str)[:6000])
