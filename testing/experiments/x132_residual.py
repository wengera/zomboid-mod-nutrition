"""x132-residual -- the Plan 1 residual arms the Task 12 harness additions can drive: X34's asleep and
running arms (#2081), X35's running pairs (#2082) and X4's push arm (#2099). Plan 2 Task 15,
session 2, TWO boots of one session at DayLength 1 (a game-hour is 37.5 s wall):

  A  `nr-overlay`    the control: the mod in overlay mode (Mode 2), nothing on Hook.CalculateStats,
                     so vanilla's seven updaters run. `NutritionRevamp.server.fast.registered` false.
  B  `x13-residual`  the mod in takeover (Mode 1) beside TKX_CalcStats. `registered` true.

The run id prefix is `x132r`. Copied from `x131_calcrepro.py` (the two-boot shape, the client-first
`pair`, the band) and `x131_traits.py` (X4's trials), with `x132_eat_b.py`'s `to_num`.

SCHEDULE, identical in both boots (wall windows; every window's rates are taken against the
server's own world age, so they are per game-hour whatever the clock does while asleep):

  W1 idle     `player.stop`, then client-first `stats.get` pairs every ~3 s for 30 s.
  W2 run      client `player.run 20 0` (the Task 12 route: setRunning + setPathfindRunning + the
              game's walk), re-issued in the opposite direction whenever the client reads not
              moving; pairs every ~2 s for 30 s; then `player.stop`.
  W3 settle   pairs every ~3 s for 6 s.
  W4 asleep   server `player.sleep.hold admin 60` (re-asserts the asleep flag every server tick
              for 60 s wall), pairs every ~5 s for 62 s; then `player.sleep.hold admin 0` and
              `player.sleep admin false`, and three wake pairs.
  X4          six trials of `HeartyAppetite` in both boots, alternating PUSH and NO-PUSH, push
              first. Each: absent on the client first (a removal polled out if needed); client
              `trait.watch HeartyAppetite 8` (the first-tick stamp); then PUSH: server
              `trait.add.push admin HeartyAppetite` (its wallAfter is the zero) or NO-PUSH: server
              `trait.set admin HeartyAppetite add` (the zero bracketed by the driver's epoch around
              the call); `wait_result("trait-watch")`; a client-first `stats.get` pair grading
              presence on `traitList` (never on `added`); then `trait.set ... remove` and client
              polls until the trait leaves.

PREDICTIONS AND FALSIFIERS (written before the run):

  X34 asleep (#2081). The server's `asleep` reads true at every W4 read (the hold wins against
      the client's reset); if it reads false the hold loses -- a harness finding, the arm
      `unmeasured`. While asleep, thirst rises at ThirstSleepingIncrease (1.0e-6 per game-second,
      0.0036 per game-hour, #0477) and fatigue falls; B's per-game-hour slope of thirst over W4,
      and of fatigue over W4's second half (the sleep-delay mirror, Plan 1 ruling 7, makes the
      onset differ), sits within max(2 % of |A's slope|, 1e-4) per game-hour of A's. Hunger is
      recorded on both and NOT graded for parity: under Plan 2 the takeover derives hunger from
      the stomach fill, so it is the mod's model, not vanilla's. A stat flat in both is `trivial`.
  X34 running (#2081). The server's `running` and `moving` read true during W2 (at least half the
      W2 server reads moving and running); if the server never reads running, the arm is
      `unmeasured` with the finding "the run arm walked" (Task 12's route is unproven). Thirst's
      W2 slope over W1's: the amendments predict 1.2 (getRunningThirstReduction, #0479 -- the
      amendment named #0486, a different row); #0593 reads that the factor is gated on
      IsoPlayer.getInstance() and may never fire on a dedicated server (ratio 1.0). The kernel
      applies 1.2 whenever its running input is set. Graded: B's W2 thirst slope within the band
      of A's (parity); the ratio is a reading, recorded per boot.
  X35 running pairs (#2082). UNMEASURABLE IN THIS TREE, written before the run: X35 needs a
      handler writing ENDURANCE 0.4242 each tick (its sentinel); the mod dropped its NR_sentinel
      at 9a424d8 ("no shipped sentinel") and TKX_CalcStats ships only the calc/A/B handlers, none
      of which writes a stat. The W2 pairs record both sides' endurance under the takeover's own
      endurance write (B) and vanilla's (A) for the record; X35 is graded `unmeasured`.
  X4 push (#2099). Every PUSH arrival (client first-tick stamp minus the server's wallAfter) sits
      below 1 s and below the NO-PUSH arrivals' spread (and Plan 1's 417/511/562 ms, #2759);
      `not discriminated` is the verdict when the push arrivals overlap the no-push spread --
      written, never re-run. Falsifier: a push arrival at or above 1 s, or a trait that never
      reaches the client's `traitList`.

`stats.get` field count: the 27 declared keys asserted present per read (`STATS_KEYS`).
Every value read is parsed through `to_num`; a non-finite stat in any read is recorded.

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
import json
import math
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

PROFILES = {"A": "nr-overlay", "B": "x13-residual"}
SESSION = ("X34 asleep + running arms, X35 running pairs (recorded), X4 push arm: an overlay control "
           "boot (A) and a takeover boot with TKX_CalcStats (B), DayLength 1; player.sleep.hold, "
           "player.run, trait.watch + trait.add.push / trait.set")
ARTIFACT = "residual.json"
USER = "admin"
ACCEPTANCE_RUN = "x132e-20261005-063700"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

STATS_KEYS = ["calories", "carbs", "lipids", "proteins", "weight", "hunger", "thirst", "statsApi",
              "incWeight", "incWeightLot", "decWeight", "endurance", "fatigue", "moodles", "traits",
              "traitList", "traitRoute", "maxWeight", "foodTimer", "standardFoodTime", "asleep",
              "running", "sprinting", "moving", "worldAge", "mult", "wall"]
PAIR_KEYS = ["hunger", "thirst", "fatigue", "endurance", "asleep", "running", "sprinting", "moving",
             "worldAge", "mult", "traitList", "calories"]
FAST = "NutritionRevamp.server.fast"
IDLE_S, IDLE_GAP = 30.0, 3.0
RUN_S, RUN_GAP, RUN_DX = 30.0, 2.0, 20
SETTLE_S, SETTLE_GAP = 6.0, 3.0
SLEEP_HOLD_S, SLEEP_S, SLEEP_GAP = 60, 62.0, 5.0
WAKE_PAIRS = 3
BAND_FRAC, BAND_FLOOR = 0.02, 1e-4                # per game-hour (x131_calcrepro.py)
FLAT = 1e-7
THIRST_SLEEP_PER_H = 1.0e-6 * 3600               # #0477
RUN_THIRST_FACTOR = 1.2                          # #0479
TRAIT = "HeartyAppetite"
TRAIT_LC = "heartyappetite"
X4_TRIALS = ["push", "nopush", "push", "nopush", "push", "nopush"]
WATCH_S = 8
REMOVE_POLL_S, REMOVE_POLL_GAP = 6.0, 0.3
PLAN1_NOPUSH_MS = [417, 511, 562]                # #2759
SENTINEL = 0.4242

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
NR_RX = re.compile(re.escape("[NutritionRevamp]"))
LUAERR_LIMIT, NR_LIMIT = 40, 40


def to_num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def wall():
    return round(time.time() - t0, 3)


def epoch_ms():
    return int(time.time() * 1000)


def note(msg):
    out["notes"].append({"wall": wall(), "boot": cur.get("label"), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        for label, srv in servers.items():
            if srv is not None:
                out["boots"][label]["server_errors"] = srv.errors[:20]
                out["boots"][label]["server_error_count"] = len(srv.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30, keep=True):
    t_before, e_before = wall(), epoch_ms()
    val = ask(side, cmd, args, timeout=timeout)
    t_after, e_after = wall(), epoch_ms()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is cur.get("server") else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_ms_before": e_before,
           "epoch_ms_after": e_after, "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    if keep:
        cur["B"]["steps"].append(row)
    return row


def grade(phase, predicted, observed, verdict, falsifier):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def gv(r):
    a = r["ack"] if isinstance(r, dict) and "ack" in r else r
    return a.get("value") if isinstance(a, dict) else None


def sleep_until(target_wall):
    while wall() < target_wall:
        time.sleep(min(0.25, max(0.0, target_wall - wall())))


def pick(a):
    a = a if isinstance(a, dict) else {}
    return {k: a.get(k) for k in PAIR_KEYS}


def pair(tag, window):
    c, srv = cur["client"], cur["server"]
    rc = step(f"{tag}_client", c, "stats.get", "", keep=False)
    rs = step(f"{tag}_server", srv, "stats.get", USER, keep=False)
    ac = rc["ack"] if isinstance(rc["ack"], dict) else {}
    as_ = rs["ack"] if isinstance(rs["ack"], dict) else {}
    for side, a in (("client", ac), ("server", as_)):
        miss = [k for k in STATS_KEYS if k not in a]
        if miss:
            cur["B"]["field_count_failures"].append({"tag": tag, "side": side, "missing": miss,
                                                     "expected": len(STATS_KEYS)})
        for k in ("hunger", "thirst", "fatigue", "endurance"):
            if k in a and (to_num(a.get(k)) is None or not math.isfinite(to_num(a.get(k)))):
                cur["B"]["non_finite"].append({"tag": tag, "side": side, "key": k, "value": a.get(k)})
    p = {"tag": tag, "window": window, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
         "skew_s": round(rs["wall_before"] - rc["wall_before"], 3),
         "client": pick(ac), "server": pick(as_)}
    cur["B"]["pairs"].append(p)
    return p


def window(name, seconds, gap, during=None):
    start = wall()
    last = None
    i = 0
    while wall() < start + seconds:
        if last is not None:
            sleep_until(last + gap)
        p = pair(f"{name}{i}", name)
        last = p["client_wall"]
        if during is not None:
            during(p)
        i += 1
    cur["B"]["windows"][name] = {"start": start, "end": wall(), "pairs": i}
    persist()


def run_window():
    c, B = cur["client"], cur["B"]
    st = {"dx": RUN_DX}
    r = step("run_0", c, "player.run", f"{st['dx']} 0")
    B["runs"].append({"wall": r["wall_before"], "dx": st["dx"], "ack": r["ack"]})

    def during(p):
        if p["client"].get("moving") is False:
            st["dx"] = -st["dx"]
            rr = step("run_again", c, "player.run", f"{st['dx']} 0")
            B["runs"].append({"wall": rr["wall_before"], "dx": st["dx"], "ack": rr["ack"]})
    window("W2", RUN_S, RUN_GAP, during)
    r = step("run_stop", c, "player.stop", "")
    B["runs"].append({"wall": r["wall_before"], "stop": r["ack"]})


def sleep_window():
    srv, B = cur["server"], cur["B"]
    r = step("sleep_hold", srv, "player.sleep.hold", f"{USER} {SLEEP_HOLD_S}")
    B["sleep_hold"] = r["ack"]
    window("W4", SLEEP_S, SLEEP_GAP)
    r = step("sleep_hold_cancel", srv, "player.sleep.hold", f"{USER} 0")
    B["sleep_hold_cancel"] = r["ack"]
    r = step("sleep_off", srv, "player.sleep", f"{USER} false")
    B["sleep_off"] = r["ack"]
    window("W5", WAKE_PAIRS * 3.0, 3.0)


def has_trait(a):
    tlist = a.get("traitList") if isinstance(a, dict) else None
    if isinstance(tlist, list):
        return TRAIT_LC in [str(x).lower() for x in tlist]
    if isinstance(tlist, dict):
        return False if not tlist else TRAIT_LC in [str(x).lower() for x in tlist.values()]
    return None


def client_has():
    r = step("x4_client_check", cur["client"], "stats.get", "", keep=False)
    return has_trait(r["ack"]), r


def ensure_absent(trial):
    present, r = client_has()
    log = {"initial": present, "removed": False, "polls": []}
    if present:
        rm = step(f"x4_{trial}_preremove", cur["server"], "trait.set", f"{USER} {TRAIT} remove")
        log["removed"] = True
        log["remove_ack"] = rm["ack"]
        end = wall() + REMOVE_POLL_S
        while wall() < end:
            time.sleep(REMOVE_POLL_GAP)
            present, r = client_has()
            log["polls"].append({"wall": r["wall_before"], "has": present})
            if present is False:
                break
    log["final"] = present
    return log


def x4_trials():
    c, srv, B = cur["client"], cur["server"], cur["B"]
    B["x4"] = []
    for i, arm in enumerate(X4_TRIALS):
        T = {"trial": i + 1, "arm": arm}
        T["pre"] = ensure_absent(i + 1)
        t_arm = time.time()
        w = step(f"x4_{i + 1}_watch", c, "trait.watch", f"{TRAIT} {WATCH_S}")
        T["watch_ack"] = w["ack"]
        if arm == "push":
            s = step(f"x4_{i + 1}_addpush", srv, "trait.add.push", f"{USER} {TRAIT}")
            a = s["ack"] if isinstance(s["ack"], dict) else {}
            T["zero_ms"] = to_num(a.get("wallAfter"))
            T["server_wallBefore"] = to_num(a.get("wallBefore"))
        else:
            s = step(f"x4_{i + 1}_set", srv, "trait.set", f"{USER} {TRAIT} add")
            T["zero_ms_bracket"] = [s["epoch_ms_before"], s["epoch_ms_after"]]
        T["server_ack"] = s["ack"]
        try:
            res = c.bus.wait_result("trait-watch", timeout=WATCH_S + 4, after=t_arm - 0.5)
        except Exception as e:                 # noqa: BLE001 - recorded, not raised
            res = {"error": f"{type(e).__name__}: {e}"}
        T["watch_result"] = res
        seen = to_num(res.get("firstSeenWall")) if isinstance(res, dict) and res.get("found") else None
        T["firstSeenWall"] = seen
        if arm == "push":
            T["latency_ms"] = None if seen is None or T["zero_ms"] is None else seen - T["zero_ms"]
        else:
            br = T["zero_ms_bracket"]
            T["latency_ms_range"] = None if seen is None else [seen - br[1], seen - br[0]]
        pc = step(f"x4_{i + 1}_after_client", c, "stats.get", "", keep=False)
        ps = step(f"x4_{i + 1}_after_server", srv, "stats.get", USER, keep=False)
        T["after"] = {"client_has": has_trait(pc["ack"]), "server_has": has_trait(ps["ack"]),
                      "client_traitList": (pc["ack"] or {}).get("traitList") if isinstance(pc["ack"], dict) else None,
                      "server_traitList": (ps["ack"] or {}).get("traitList") if isinstance(ps["ack"], dict) else None}
        rm = step(f"x4_{i + 1}_remove", srv, "trait.set", f"{USER} {TRAIT} remove")
        T["remove_ack"] = rm["ack"]
        polls, gone = [], None
        end = wall() + REMOVE_POLL_S
        while wall() < end:
            time.sleep(REMOVE_POLL_GAP)
            present, r = client_has()
            polls.append({"wall": r["wall_before"], "epoch_ms": r["epoch_ms_before"], "has": present})
            if present is False:
                gone = r["epoch_ms_before"] - rm["epoch_ms_before"]
                break
        T["remove_polls"] = polls
        T["removal_seen_ms_upper"] = gone
        B["x4"].append(T)
        persist()


def body(label):
    srv, c, B = cur["server"], cur["client"], cur["B"]
    B.update({"pairs": [], "windows": {}, "runs": [], "field_count_failures": [], "non_finite": []})
    B["registered"] = gv(step("registered", srv, "lua.global", FAST + ".registered"))
    B["mode"] = gv(step("mode", srv, "lua.global", "NutritionRevamp.server.options.mode"))
    B["calcstats_version"] = {"client": gv(step("tkx_c", c, "lua.global", "TKX_CalcStats.version")),
                              "server": gv(step("tkx_s", srv, "lua.global", "TKX_CalcStats.version"))}
    B["fast_calls_start"] = gv(step("calls0", srv, "lua.global", FAST + ".stats.calls"))
    B["fast_failures_start"] = gv(step("fail0", srv, "lua.global", FAST + ".stats.failures"))
    step("stop_t0", c, "player.stop", "")
    window("W1", IDLE_S, IDLE_GAP)
    run_window()
    window("W3", SETTLE_S, SETTLE_GAP)
    sleep_window()
    B["fast_calls_end"] = gv(step("calls1", srv, "lua.global", FAST + ".stats.calls"))
    B["fast_failures_end"] = gv(step("fail1", srv, "lua.global", FAST + ".stats.failures"))
    B["fast_lastError"] = step("lasterr", srv, "lua.global", FAST + ".lastError")["ack"]
    x4_trials()


def slope(rows, key, side="server"):
    pts = [(to_num(r[side].get("worldAge")), to_num(r[side].get(key))) for r in rows]
    pts = [p for p in pts if p[0] is not None and p[1] is not None and math.isfinite(p[1])]
    if len(pts) < 3:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx == 0:
        return None
    s = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    return {"n": n, "per_game_hour": s, "delta": pts[-1][1] - pts[0][1],
            "game_hours": pts[-1][0] - pts[0][0], "first": pts[0][1], "last": pts[-1][1]}


def win(Bb, name):
    return [p for p in (Bb.get("pairs") or []) if p.get("window") == name]


def band_check(a, b):
    if a is None or b is None:
        return None
    ra, rb = a["per_game_hour"], b["per_game_hour"]
    band = max(BAND_FRAC * abs(ra), BAND_FLOOR)
    return {"A": ra, "B": rb, "diff": rb - ra, "band": band, "in_band": abs(rb - ra) <= band}


def grade_all():
    A, Bb = out["boots"].get("A", {}), out["boots"].get("B", {})
    reg = {"A": A.get("registered"), "B": Bb.get("registered")}
    # ---- X34 asleep ----
    asleep = {}
    for lab, X in (("A", A), ("B", Bb)):
        w4 = win(X, "W4")
        srv_flags = [p["server"].get("asleep") for p in w4]
        cli_flags = [p["client"].get("asleep") for p in w4]
        half = w4[len(w4) // 2:]
        asleep[lab] = {"server_asleep": srv_flags, "client_asleep": cli_flags,
                       "held": bool(w4) and all(f is True for f in srv_flags[1:]) and srv_flags[0] is True,
                       "thirst": slope(w4, "thirst"), "fatigue_all": slope(w4, "fatigue"),
                       "fatigue_second_half": slope(half, "fatigue"), "hunger": slope(w4, "hunger"),
                       "endurance": slope(w4, "endurance"),
                       "mult": [p["server"].get("mult") for p in w4],
                       "worldAge": [p["server"].get("worldAge") for p in w4],
                       "hold_ack": X.get("sleep_hold")}
        th = asleep[lab]["thirst"]
        asleep[lab]["thirst_vs_0477"] = None if th is None else th["per_game_hour"] / THIRST_SLEEP_PER_H
    tb = band_check(asleep["A"]["thirst"], asleep["B"]["thirst"])
    fb = band_check(asleep["A"]["fatigue_second_half"], asleep["B"]["fatigue_second_half"])
    obs = {"per_boot": asleep, "thirst_band": tb, "fatigue_band": fb, "registered": reg,
           "hunger_note": "hunger recorded, not graded for parity (the takeover derives it from the "
                          "stomach fill under Plan 2)"}
    if not asleep["A"]["held"] or not asleep["B"]["held"]:
        v = "unmeasured"
    elif reg["A"] is not False or reg["B"] is not True or tb is None or fb is None:
        v = "unmeasured"
    elif abs(tb["A"]) <= FLAT and abs(fb["A"]) <= FLAT:
        v = "trivial"
    elif tb["in_band"] and fb["in_band"]:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X34-asleep", "server asleep true at every W4 read in both boots (the hold wins); B's thirst "
                        "slope (W4) and fatigue slope (W4 second half) within max(2 % |A|, 1e-4) per "
                        "game-hour of A's; A's asleep thirst ~0.0036 per game-hour (#0477)",
          obs, v, "asleep false on the server inside W4 (the hold loses: unmeasured, a harness "
                  "finding); a slope outside the band (the reproduction is wrong while asleep)")
    # ---- X34 running ----
    running = {}
    for lab, X in (("A", A), ("B", Bb)):
        w2, w1 = win(X, "W2"), win(X, "W1")
        sr = [p["server"].get("running") for p in w2]
        sm = [p["server"].get("moving") for p in w2]
        cr = [p["client"].get("running") for p in w2]
        cm = [p["client"].get("moving") for p in w2]
        n = len(w2) or 1
        t2, t1 = slope(w2, "thirst"), slope(w1, "thirst")
        running[lab] = {"server_running": sr, "server_moving": sm, "client_running": cr,
                        "client_moving": cm,
                        "server_running_frac": sum(1 for f in sr if f is True) / n,
                        "server_moving_frac": sum(1 for f in sm if f is True) / n,
                        "client_running_frac": sum(1 for f in cr if f is True) / n,
                        "thirst_run": t2, "thirst_idle": t1,
                        "ratio_run_over_idle": None if not t2 or not t1 or t1["per_game_hour"] == 0
                        else t2["per_game_hour"] / t1["per_game_hour"],
                        "endurance_run": slope(w2, "endurance"),
                        "endurance_pairs": [[p["client"].get("endurance"), p["server"].get("endurance")]
                                            for p in w2],
                        "run_acks": [r.get("ack") for r in (X.get("runs") or [])][:4]}
    rb = band_check(running["A"]["thirst_run"], running["B"]["thirst_run"])
    ran = all(running[lab]["server_running_frac"] >= 0.5 and running[lab]["server_moving_frac"] >= 0.5
              for lab in ("A", "B"))
    never = all(running[lab]["server_running_frac"] == 0 for lab in ("A", "B"))
    if never or not ran:
        v = "unmeasured"
    elif rb is None:
        v = "unmeasured"
    elif rb["in_band"]:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X34-running", "server running and moving true in at least half the W2 reads in both boots; "
                         "B's W2 thirst slope within max(2 % |A|, 1e-4) per game-hour of A's; the W2/W1 "
                         "thirst ratio recorded (1.2 if getRunningThirstReduction fires server-side, "
                         "#0479; 1.0 per #0593's reading)",
          {"per_boot": running, "thirst_run_band": rb}, v,
          "the server never reads running (the run arm walked: unmeasured, a harness finding); B's "
          "running thirst slope outside A's band")
    # ---- X35 ----
    grade("X35", "unmeasurable in this tree (written before the run): no handler writes the 0.4242 "
                 "sentinel -- the mod dropped NR_sentinel at 9a424d8 and TKX_CalcStats' three "
                 "handlers write no stat; the W2 endurance pairs are recorded only",
          {"endurance_pairs": {lab: running[lab]["endurance_pairs"] for lab in ("A", "B")},
           "server_running_frac": {lab: running[lab]["server_running_frac"] for lab in ("A", "B")}},
          "unmeasured", "-")
    # ---- X4 ----
    push, nop, presence = [], [], []
    for lab, X in (("A", A), ("B", Bb)):
        for T in X.get("x4") or []:
            presence.append({"boot": lab, "trial": T["trial"], "arm": T["arm"],
                             "client_has": T["after"]["client_has"], "server_has": T["after"]["server_has"],
                             "watch_found": (T.get("watch_result") or {}).get("found")
                             if isinstance(T.get("watch_result"), dict) else None})
            if T["arm"] == "push":
                push.append({"boot": lab, "trial": T["trial"], "ms": T.get("latency_ms")})
            else:
                nop.append({"boot": lab, "trial": T["trial"], "ms_range": T.get("latency_ms_range")})
    pm = [p["ms"] for p in push if p["ms"] is not None]
    nl = [r["ms_range"][0] for r in nop if r["ms_range"]]
    nh = [r["ms_range"][1] for r in nop if r["ms_range"]]
    all_present = all(p["client_has"] is True and p["server_has"] is True for p in presence)
    obs = {"push_ms": push, "nopush_ms_range": nop, "presence": presence,
           "push_max": max(pm) if pm else None, "push_min": min(pm) if pm else None,
           "nopush_lower_min": min(nl) if nl else None, "nopush_upper_max": max(nh) if nh else None,
           "plan1_nopush_ms": PLAN1_NOPUSH_MS, "all_present": all_present}
    if len(pm) < 3 or len(nl) < 3:
        v = "unmeasured"
    elif max(pm) >= 1000 or not all_present:
        v = "falsified"
    elif max(pm) < min(nl):
        v = "as_predicted"
    else:
        v = "not_discriminated"
    grade("X4-push", "every push arrival < 1000 ms and below every no-push arrival's lower bound; the "
                     "trait on both sides' traitList after every add",
          obs, v, "a push arrival >= 1 s or a trait missing from a traitList; overlapping spreads are "
                  "'not discriminated', never re-run")


def boot(label):
    prof = profs[label]
    sub = os.path.join(run_dir, f"boot-{label}")
    os.makedirs(sub, exist_ok=True)
    B = out["boots"][label] = {"profile": prof.name, "run_subdir": f"boot-{label}", "steps": [],
                               "sandbox": prof.sandbox, "mods": list(prof.mods)}
    cur.clear()
    cur.update({"label": label, "B": B})
    tl.mark("boot", label=label, profile=prof.name)
    clients = []
    server = None
    B["doctor_clean"], dtext = doctor()
    B["doctor"] = dtext.strip().splitlines()
    if not B["doctor_clean"]:
        B["error"] = "doctor not clean before this boot; the boot was not started (CLAUDE.md s5)"
        persist()
        return
    try:
        server = make_server(sub, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None)
        servers[label] = server
        cur["server"] = server
        server.start(timeout=prof.server_timeout)
        B["build"] = server.build
        c, _ = make_client(sub, USER, server, rec)
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
        body(label)
    except Exception as e:                     # noqa: BLE001 - the boot is a result; keep its rows
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", label=label, detail=str(e)[:200])
    finally:
        B["wall_end_body"] = wall()
        persist()
        try:
            if server is not None:
                teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, clients)
            B["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            if server is not None:
                logs = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                        "server_nr": grep_file(server.log_path, NR_RX, NR_LIMIT),
                        "limits": {"luaerr": LUAERR_LIMIT, "nr": NR_LIMIT}}
                if clients:
                    logs.update({"client_luaerr": grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT),
                                 "client_nr": grep_file(clients[0].console, NR_RX, NR_LIMIT)})
                B["logs"] = logs
            B["wall_end"] = wall()
            persist()


profs = {k: profile.load(v) for k, v in PROFILES.items()}
rec = None if DRY_RUN else fx.load(profs["A"].fixture)
run_id, run_dir = ("x132r-dry-run", None) if DRY_RUN else new_run_dir("x132r")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
servers, cur = {}, {}

lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": {k: p.report() for k, p in profs.items()},
    "mods": {k: list(p.mods) for k, p in profs.items()},
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_CalcStats"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": None,
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"IDLE_S": IDLE_S, "RUN_S": RUN_S, "RUN_DX": RUN_DX, "SLEEP_HOLD_S": SLEEP_HOLD_S,
                  "SLEEP_S": SLEEP_S, "BAND_FRAC": BAND_FRAC, "BAND_FLOOR": BAND_FLOOR,
                  "THIRST_SLEEP_PER_H": THIRST_SLEEP_PER_H, "RUN_THIRST_FACTOR": RUN_THIRST_FACTOR,
                  "TRAIT": TRAIT, "X4_TRIALS": X4_TRIALS, "WATCH_S": WATCH_S,
                  "PLAN1_NOPUSH_MS": PLAN1_NOPUSH_MS, "STATS_KEYS": STATS_KEYS, "SENTINEL": SENTINEL},
    "deviations": [
        "X35 is unmeasurable in this tree and graded unmeasured before the run: no handler writes the "
        "0.4242 sentinel (NR_sentinel dropped at 9a424d8; TKX_CalcStats ships calc/A/B handlers that "
        "write no stat, despite the x13-residual header calling it the sentinel's carrier).",
        "X4 adds a NO-PUSH arm with the same client first-tick stamp (trait.set add), alternated with "
        "the push arm, three trials each, in BOTH boots: the Plan 1 no-push arrivals (#2759) were "
        "poll-bounded and are not the same instrument. The removal is polled (trait.watch watches "
        "presence only).",
        "The amendments cite #0486 for the 1.2 running thirst factor; the factor's row is #0479 (and "
        "#0593 reads it may never fire on a dedicated server). Both readings are pre-registered.",
        "doctor is run before EACH boot (recorded per boot); the top-level doctor_clean is boot A's.",
    ],
    "world_changes": {"restored": "each boot restores the golden fixture into its own sub-directory",
                      "left_in_place": ["the player moved by player.run", "asleep flag held 60 s",
                                        "HeartyAppetite added and removed six times"]},
    "boots": {}, "notes": [], "verdicts": {},
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

try:
    for label in ("A", "B"):
        boot(label)
        if label == "A":
            out["doctor_clean"] = out["boots"]["A"].get("doctor_clean")
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
        "field_count_failures": {k: len(b.get("field_count_failures") or []) for k, b in out["boots"].items()},
        "non_finite": {k: len(b.get("non_finite") or []) for k, b in out["boots"].items()},
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
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
