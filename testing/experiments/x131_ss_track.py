"""x131-ss-track -- X44: do simpleStatus's macro bars track the vanilla macro stores on a client,
and how late after a server write does the bar change: Plan 1 Task 15.

The run id prefix is `x131r` (run id `x131r-<date>-<time>`): the register's run-id pattern
refuses a hyphen in the prefix.

Copied from `x131_traits.py` (the template's house shape). ONE live session, ONE boot, profile
`x13-ssread` (PZTestKit + simpleStatus from workshop 2867431511, live `42.20/` tree read
2026-10-04, files dated 2026-09-13, + TKX_SSRead after it in Mods= order; the fixture's own
sandbox). The profile's gate: client `text.get IGUI_SS_BARTITLE_HAPPY` -> "Happiness" (the mod
loaded on the client) and client `lua.global TKX_SS.calls` resolved (the probe loaded).

The subject. Each macro bar's value is `round(player:getNutrition():get<Macro>(), 1)`
(`ss.stats.lua:238`, `:280`, `:294`, `:308`); the bar rebuilds its `self.barInfo` every 10
frames from `SSBar:prerender` (`ISSSBar.lua:452-461`); the proteins bar's text appends
`(x1.5)` between 50 and 300 (`ss.stats.lua:240-248`). The four macro bars ship hidden; the
probe sets `shown = true` at file scope before `OnCreatePlayer` builds the config, and wraps
`SSBar:prepareBarInfo` to copy each macro row's text into `TKX_SS` and bump `TKX_SS.calls`.

Phases:

  L   live wrap: client `lua.global TKX_SS.calls` twice, LIVE_GAP_S apart; it must rise.
  C0  control: CTRL_N client triplets (bar, store, bar) -- `lua.global TKX_SS.calories`,
      client `stats.get` (its `calories` and its own `wall`), `lua.global TKX_SS.calories` --
      before any write: the bar reads the client's store rounded to one decimal.
  AC  server `nutrition.set admin calories 1500` (its python bracket is the zero; measured
      from the ack, because the server picks a command up 0.26-2.02 s after it is written),
      server `nutrition.get admin` read back; then client triplets back to back, at least
      POLL_S apart, for WINDOW_S seconds from the ack; the triplets nearest +1, +2 and +4 s
      after the ack are tagged.
  AP  the same for `proteins 120` with `TKX_SS.proteins`.
  E   `lua.global TKX_SS.calls` at the end.

PREDICTIONS AND FALSIFIERS (written before the run):

  L: TKX_SS.calls rises between the two reads (the bar refreshes every 10 frames). Falsifier:
      flat or unresolved -- the wrap did not take; every arm below is then `unmeasured`.
  C0: every triplet's store value rounded to one decimal equals one of its bracketing bar
      texts (the bar follows the client's store, #1483). A bar text of "" means the calories
      bar was never built (the shown flag did not take) -> `unmeasured`.
  AC/AP: after the write the client's store changes at the next push (1 Hz), and the bar
      follows within one 10-frame refresh: from the first triplet whose store is near the
      written value (|store - value| < TOL), the bar equals round(store, 1) at every triplet
      (one of the two bracketing bar reads), and the bar's first change comes no earlier than
      the store's first change. The bar never shows the server's value ahead of the client's
      store. Falsifier: a bar that keeps the pre-write value while the store has changed for
      more than 1 s, or a bar that changes before the client's store does. A bar that never
      changes while the store does, or calls flat, is written `unmeasured`, never a
      falsification. The gap between the store's and the bar's first change is the arrival
      lag; it is bounded by one bus round trip, so a sub-poll lag is not a reading. A store
      already within TOL of the written value before the write makes the arm `trivial`.

What follows is the template's own rule, kept as the house shape this driver obeys.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. The artifact is evidence of what this exact file
     did; changing the file afterwards makes the pair unreadable. If something has to change,
     that is a new driver (`xNNNb_...`) and a new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier, and never collapse "the read did not happen" into "the
     prediction failed" -- they are different answers.
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

from _common import ask, doctor, git_dirty, git_say, hard_kill, num, save   # noqa: E402
from pzt import fixture as fx, profile                                      # noqa: E402
from pzt.paths import new_run_dir                                           # noqa: E402
from pzt.session import (Timeline, make_client, make_server,               # noqa: E402
                         teardown, verify)

PROFILE = "x13-ssread"
SESSION = ("X44: simpleStatus macro bars (TKX_SSRead copies the bar text) against the client's "
           "own Nutrition store after a server write of calories 1500 and proteins 120; client "
           "(bar, store, bar) triplets timed from the write's ack")
ARTIFACT = "ss_track.json"
USER = "admin"
ACCEPTANCE_RUN = "x131b-20261004-175911"

LIVE_GAP_S = 2.0
CTRL_N = 3
POLL_S = 0.5
WINDOW_S = 6.0
TAGS_S = (1.0, 2.0, 4.0)
TOL = 5.0
ARMS = [("AC", "calories", 1500, "TKX_SS.calories"), ("AP", "proteins", 120, "TKX_SS.proteins")]
NUM_RX = re.compile(r"^\s*(-?\d+(?:\.\d+)?)")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"


def wall():
    return round(time.time() - t0, 3)


def ms():
    return int(time.time() * 1000)


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), ms()
    val = ask(side, cmd, args, timeout=timeout)
    t_after, e_after = wall(), ms()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": e_before,
           "epoch_ms_after": e_after, "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    save(path, out, tl, server)
    return row


def bar_num(text):
    if not isinstance(text, str):
        return None
    m = NUM_RX.match(text)
    return float(m.group(1)) if m else None


def gval(name):
    e_b = ms()
    v = ask(c, "lua.global", name)
    e_a = ms()
    text = v.get("value") if isinstance(v, dict) else None
    return {"epoch_ms_before": e_b, "epoch_ms_after": e_a, "text": text,
            "num": bar_num(text) if isinstance(text, str) else num(text),
            "resolved": v.get("resolved") if isinstance(v, dict) else None}


def triplet(tag, field, gname, zero_ms):
    b1 = gval(gname)
    e_b = ms()
    st = ask(c, "stats.get")
    e_a = ms()
    b2 = gval(gname)
    store = num(st.get(field)) if isinstance(st, dict) else None
    snap_wall = num(st.get("wall")) if isinstance(st, dict) else None
    r1 = round(store, 1) if store is not None else None
    row = {"tag": tag, "bar_before": b1, "bar_after": b2,
           "store": store, "store_r1": r1, "store_wall": snap_wall,
           "store_epoch_ms_before": e_b, "store_epoch_ms_after": e_a,
           "match_before": (b1["num"] is not None and r1 is not None
                            and abs(b1["num"] - r1) < 0.051),
           "match_after": (b2["num"] is not None and r1 is not None
                           and abs(b2["num"] - r1) < 0.051)}
    row["match"] = row["match_before"] or row["match_after"]
    if zero_ms is not None:
        row["t_from_ack_ms"] = (snap_wall - zero_ms) if snap_wall is not None else None
        row["bar_after_from_ack_ms"] = b2["epoch_ms_after"] - zero_ms
    return row


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x131r-dry-run", None) if DRY_RUN else new_run_dir("x131r")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, clients, t0 = Timeline(), [], time.time()
server = None if DRY_RUN else make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                                          mod_skip=prof.skip, sandbox=prof.sandbox or None)
c = None

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
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "subject_tree": {"workshop_item": "2867431511", "mod": "SimpleStatus/42.20",
                     "read_on": "2026-10-04", "files_mtime": "2026-09-13 16:53"},
    "constants": {"LIVE_GAP_S": LIVE_GAP_S, "CTRL_N": CTRL_N, "POLL_S": POLL_S,
                  "WINDOW_S": WINDOW_S, "TAGS_S": TAGS_S, "TOL": TOL, "ARMS": ARMS},
    "world_changes": {"restored": "none", "left_in_place": ["calories near 1500",
                                                            "proteins near 120"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {},
}

if DRY_RUN:
    print(json.dumps(out))
    sys.exit(0)

try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    # ---- L: the wrap is live ---------------------------------------------------------------
    l1 = gval("TKX_SS.calls")
    time.sleep(LIVE_GAP_S)
    l2 = gval("TKX_SS.calls")
    out["phases"]["L"] = {"first": l1, "second": l2,
                          "installed": gval("TKX_SSRead_Installed"),
                          "bars": {k: gval("TKX_SS." + k) for k in
                                   ("calories", "carbs", "lipids", "proteins")}}
    live = (l1["num"] is not None and l2["num"] is not None and l2["num"] > l1["num"])
    grade("L", predicted="TKX_SS.calls rises", verdict="as_predicted" if live else "unmeasured",
          observed={"first": l1["num"], "second": l2["num"]},
          falsifier="flat or unresolved: the wrap did not take")
    save(path, out, tl, server)

    # ---- C0: control triplets --------------------------------------------------------------
    ctrl = []
    for i in range(CTRL_N):
        ctrl.append(triplet(f"c0_{i}", "calories", "TKX_SS.calories", None))
        time.sleep(POLL_S)
    out["phases"]["C0"] = {"server": step("c0_server", server, "nutrition.get", USER)["ack"],
                           "rows": ctrl}
    built = all(r["bar_before"]["num"] is not None for r in ctrl)
    grade("C0", predicted="each store value rounded to 0.1 equals a bracketing bar text",
          observed={"matches": [r["match"] for r in ctrl],
                    "bars": [r["bar_before"]["text"] for r in ctrl],
                    "stores": [r["store_r1"] for r in ctrl]},
          verdict=("unmeasured" if not (live and built) else
                   ("as_predicted" if all(r["match"] for r in ctrl) else "falsified")),
          falsifier="a pre-write bar that differs from the client's store")
    save(path, out, tl, server)

    # ---- AC / AP: write, then triplets -----------------------------------------------------
    for label, field, value, gname in ARMS:
        ph = {"field": field, "value": value}
        ph["pre"] = triplet(f"{label}_pre", field, gname, None)
        s = step(f"{label}_set", server, "nutrition.set", f"{USER} {field} {value}")
        ph["set"] = s
        zero = s["epoch_ms_after"]
        ph["readback"] = step(f"{label}_readback", server, "nutrition.get", USER)["ack"]
        rows, t_s = [], time.time()
        while time.time() - t_s < WINDOW_S:
            t_i = time.time()
            rows.append(triplet(f"{label}_post", field, gname, zero))
            left = POLL_S - (time.time() - t_i)
            if left > 0:
                time.sleep(left)
        ph["rows"] = rows
        tagged = {}
        for tg in TAGS_S:
            cands = [r for r in rows if r.get("t_from_ack_ms") is not None]
            if cands:
                best = min(cands, key=lambda r: abs(r["t_from_ack_ms"] - tg * 1000))
                tagged[f"+{tg:g}s"] = {"t_from_ack_ms": best["t_from_ack_ms"],
                                       "bar_before": best["bar_before"]["text"],
                                       "store_r1": best["store_r1"],
                                       "bar_after": best["bar_after"]["text"],
                                       "match": best["match"]}
        ph["tagged"] = tagged
        near = lambda x: x is not None and abs(x - value) < TOL       # noqa: E731
        store_first = next((r for r in rows if near(r["store"])), None)
        bar_first = next((r for r in rows if near(r["bar_before"]["num"])
                          or near(r["bar_after"]["num"])), None)
        bar_early = next((r for r in rows if near(r["bar_before"]["num"])
                          and not near(r["store"])), None)
        after = rows[rows.index(store_first):] if store_first is not None else []
        ph["store_first"] = store_first["t_from_ack_ms"] if store_first else None
        ph["bar_first_ms"] = (bar_first["bar_before"]["epoch_ms_after"] - zero
                              if bar_first and near(bar_first["bar_before"]["num"]) else
                              (bar_first["bar_after"]["epoch_ms_after"] - zero
                               if bar_first else None))
        ph["matches_after_store_change"] = [r["match"] for r in after]
        ph["bar_before_store"] = bar_early is not None
        out["phases"][label] = ph
        if not live or ph["pre"]["bar_before"]["num"] is None:
            v = "unmeasured"
        elif near(ph["pre"]["store"]):
            v = "trivial"
        elif store_first is None:
            v = "unmeasured"
        elif bar_first is None:
            v = "unmeasured"
        elif bar_early is not None:
            v = "falsified"
        elif all(ph["matches_after_store_change"][1:]) or (
                len(ph["matches_after_store_change"]) == 1 and ph["matches_after_store_change"][0]):
            v = "as_predicted"
        else:
            v = "falsified"
        grade(label,
              predicted=("the bar equals the client's store rounded to 0.1 from the triplet "
                         "after the store's first change on, never ahead of the store"),
              observed={"store_first_ms": ph["store_first"], "bar_first_ms": ph["bar_first_ms"],
                        "matches": ph["matches_after_store_change"],
                        "bar_before_store": ph["bar_before_store"], "tagged": tagged},
              verdict=v,
              falsifier="the bar lags the store by more than one triplet, or leads it")
        save(path, out, tl, server)

    out["phases"]["E"] = {"calls": gval("TKX_SS.calls")}
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "calls": [l1["num"], l2["num"], out["phases"]["E"]["calls"]["num"]],
        "AC": {k: out["phases"]["AC"][k] for k in ("store_first", "bar_first_ms")},
        "AP": {k: out["phases"]["AP"][k] for k in ("store_first", "bar_first_ms")},
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    save(path, out, tl, server)
    try:
        teardown(tl, server, clients)
    finally:
        hard_kill(server, clients)
        out["wall_seconds"] = round(time.time() - t0, 1)
        out["server_error_count"] = len(server.errors)
        out["client_lua_error"] = "lua_error" in getattr(clients[0], "seen", ()) if clients else None
        save(path, out, tl, server)
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
