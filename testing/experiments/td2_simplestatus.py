"""Teardown 2: simpleStatus measured on a live dedicated server + a real client (slice 10 of the
09-11 teardown wave, pass 2).

**The subject reads; it never writes.** `simpleStatus` (workshop 2867431511) is 7 client-only Lua
files that draw five server-owned macros -- `getCalories` / `getCarbohydrates` / `getLipids` /
`getProteins` / `getWeight` on `Nutrition` (`ss.stats.lua:280,294,308,238,381`) -- plus the three
weight-direction flags (`ss.stats.lua:404-411`), every UI frame, uncached. It stores one modData
key, `SimpleStatusConfig`, written only from UI input handlers (`ISSSBar.lua:274,282,290,297,307,
476,540`, all landing on `:34`) followed by `player:transmitModData()` (`:35`). So there is
nothing of the mod's own to trigger from the bus, and what this session measures is the BOUNDARY
the mod is built on:

  phase 1 -- the server-owned nutrition store arriving on the client inside the 1 Hz
             `PlayerStatsPacket`, with a signed, per-snapshot band (below);
  phase 2 -- the `transmitModData()` boundary `ISSSBar.lua:35` depends on, including the
             wipe-and-replace half that needs a SERVER-only key to be visible at all;
  appendix -- the two pass-1 follow-up controls (A1 display names, A2 the client copy's tick).
             They are NOT simpleStatus findings and are reported as pass-1 follow-ups.

**Why every read is wall-bracketed.** The two sides of a snapshot are separate bus round trips
~1 s apart and the SERVER's copy is moving between them (`Nutrition.update @42 L75` skips all four
decays on a client, so the client is a staircase that steps on a packet while the server is a
ramp). The gap is therefore a TIMING reading, not float noise, and it is graded against a band
computed from that snapshot's own read skew:

    client - server  in  [ r*d_min , r*(d_max + 1 s) ]
    d_min = t_server_before - t_client_after,  d_max = t_server_after - t_client_before

with `r` the per-real-second decay rate. `TK.bodySnapshot`'s own `wall` / `worldAge` CANNOT be
differenced into a skew (they are each side's clock with an unmeasured offset), so the brackets
come from THIS driver's clock, around every macro read -- which is the one thing pass 1's driver
does not do (`td1_longtermpreservation4220.py:287` sends `stats.get` through a bare `ask()`).
The CLIENT half is read first at every tag, for the same reason pass 1 gives at its `:273-277`
and because the sign of the band follows the read order: a server-first loop puts the whole band
below zero and would grade a healthy mirror as falsifying the client-skip.

**Three grading clauses that are NOT in the notes' first draft** (controller amendments 15-17):
  * a snapshot taken inside a write's push window is an ARRIVAL LATENCY reading, not a band test;
    only snapshots >= 1.5 s after the last server write are graded against the band;
  * weight's rate is computed per snapshot from that snapshot's own readings (the arm, the
    carb/lipid multiplier and the calorie ratio), never from a ceiling, and the arm is CHECKED
    against the same snapshot's `isIncWeight` / `isDecWeight` (the harness's new H1 keys);
  * the empirical decay slope is recorded beside the derived `r` -- successive server readings
    divided by this driver's own wall deltas -- because `r` rests on
    `Thermoregulator.getEnergyMultiplier() ~= 1`, which nothing has measured.

**World changes: none to restore.** `nutrition.set` writes the character's own store, which the
next fixture provision rewrites; the two RCON-spawned items and the planted modData keys live in
this run's copy of the fixture (`fx.restore_server` / `restore_client` into `run_dir`).
Never raises through teardown; the artifact is copied byte-for-byte after the session.
"""
import json
import os
import re
import shutil
import struct
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill, num, save   # noqa: E402
from pzt import fixture as fx, profile                                      # noqa: E402
from pzt.paths import new_run_dir                                           # noqa: E402
from pzt.session import (Timeline, grep_file, make_client, make_server,     # noqa: E402
                         teardown, verify)

MOD = "simpleStatus"
PROFILE = "teardown-simplestatus"
USER = "admin"
ACCEPTANCE_RUN = "run-20260910-230752"       # PASS, verify text.get ok=True, 0 server errors

MIRROR_WAIT = 3.0        # > the 1 Hz PlayerStatsPacket window (every prior slice's number)
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory (s01/s02/s05)
TICK_WAIT = 10.0         # A2's window: comfortably longer than the ~5 s server item tick
PUSH_WINDOW = 1.0        # the packet interval the band's upper end allows for
SETTLE = 1.5             # a snapshot closer than this to a server write is a LATENCY reading

# Five zero-argument getters on IsoPlayer, comma-joined and WHITESPACE-FREE (`splitArgs` splits on
# %S+ and `witness.fields` reads argv[3] only, so a space silently drops everything after it).
# The five MACROS are deliberately NOT here: they live on Nutrition, which witness.fields cannot
# reach (TK.call(subject, name), no sub-object hop) -- they come from stats.get instead. So does
# getMaxWeight, which is in this list as a witness-vs-snapshot cross-check of the same number by
# two routes on one side. getNutrition/getStats are excluded on purpose: TK.json renders a Java
# object as its toString(), i.e. a per-JVM identity hash that would read as a desync.
FIELDS = "getInventoryWeight,getMaxWeight,isDead,isGodMod,getUsername"
FIELD_COUNT = 5

# The mod writes ONE key and only from UI input handlers, so the player probe is a CENSUS (`*`)
# plus a dotted read of the config's leaves -- which report `missing` until a human clicks.
PLAYER_SCOPE = f"player:{USER} *"
CONFIG_KEY = f"player:{USER} SimpleStatusConfig"
CONFIG_LEAVES = (f"player:{USER} SimpleStatusConfig.SS_pos_x SimpleStatusConfig.SS_locked "
                 "SimpleStatusConfig.SS_fontSize SimpleStatusConfig.SS_isVertical "
                 "SimpleStatusConfig.SS_isRulerOn SimpleStatusConfig.SS_shown_calories")
GLOBAL_SCOPE = "global:SimpleStatusConfig *"
KEYS = f"{PLAYER_SCOPE} | {CONFIG_KEY} | {GLOBAL_SCOPE}"
KEYS_NOTE = ("moddata_keys is a DISPLAY string: the ` | ` joins three probes for the reader and is "
             "not a bus token. They are sent separately. The global-scoped one is NON-DISCRIMINATING "
             "in both directions -- ModData.getOrCreate CREATES the table for the census itself, and "
             "the mod's server half only ever created it empty -- so it is metadata, not a control.")
# The player-scope exclusion set, from pass 1 (docs/decisions.md:133 and the td1b artifact): the
# four vanilla fitness keys plus `hotbar`, which is CLIENT-only. The item-scope set
# ({customName, Tooltip}) must never be applied here -- this subject has no item scope at all, and
# the two appendix items are read through witness.fields, not through a census.
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}
PLANT_SERVER = ("pzt_ss_server", "1")        # planted on the SERVER: needs slice 10's moddata.set
PLANT_CLIENT = ("pzt_ss_client", "1")        # the client's own, the direction S6 already measured

# ---- appendix A1/A2 -------------------------------------------------------------------------
# A1: the criterion is ABSENCE FROM media/lua/shared/Translate/EN/ItemName.json, not a missing
# `DisplayName =` line (no vanilla food has one). FruitSaladClay is absent, Steak is present at
# ItemName.json:4218. A2 pins the same Steak.
ITEM_ABSENT = "Base.FruitSaladClay"
ITEM_PRESENT = "Base.Steak"
ITEM_FIELDS = ("getDisplayName,getFullType,getActualWeight,getActualWeightUnmodded,"
               "isCustomWeight,getWeight")
ITEM_FIELD_COUNT = 6
TICK_FIELDS = "getHeat,getCookingTime,getContainer"
TICK_FIELD_COUNT = 3

# ---- the drift arithmetic (all from the jar plus the fixture's own DayLength) ------------------
# DayLength = 4 -> 86 400 game-seconds per 5 400 real seconds at multiplier 1.
GAME_S_PER_REAL_S = 16.0
# Per GAME second, from Nutrition.update @48-@99 L76-L78 and updateCalories' idle branch
# @295-@316 L118 at f1 = 1 (no action), f2 = Thermoregulator.getEnergyMultiplier() ~= 1 (the one
# unverified term -- see the empirical slope) and f3 = weight/80, which is applied per snapshot.
MACRO_RATE = {"calories": 0.016, "carbs": 0.0035, "lipids": 0.00113, "proteins": 0.00086}
CAL_REF_WEIGHT = 80.0
# Nutrition.updateWeight, read off the jar this task (42.20.4):
#   gain = 1000 (700 if weight < 90 and WEIGHT_GAIN; 1800 if weight > 70 and WEIGHT_LOSS)
#          + (weight - 80) * 40                                   @15-@94  L142-L158
#   loss = min(0, (weight - 70) * 30)                             @95-@118 L159-L161
#   calories > gain -> IncWeight, rate 1.3e-5 * mult * min(1, calories/4000)   @120-@245 L166-L184
#     mult = 3 if carbs > 700 or lipids > 700  (IncWeightLot)     @156-@191 L176-@178
#     mult = 2 if carbs > 400 or lipids > 400  (IncWeightLot TOO) @194-@226 L179-L181
#   calories < loss -> DecWeight, rate -8.5e-6 * min(1, |calories|/2500)       @250-@308 L186-L193
#   otherwise the same weight is re-stored -> rate 0                           @311-@315 L195
#   ...and the write is behind `if not GameClient.client` (@317-@320 L198), which is why the
#   CLIENT's weight is a pure staircase and its band has the OPPOSITE sign to the macros'.
WEIGHT_GAIN_BASE, WEIGHT_LOT_RATE = 1.3e-5, 8.5e-6

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_RX = re.compile(re.escape(MOD))
# The mod's three prints, each grepped SEPARATELY (a compiled regex, with the brackets escaped --
# session.grep_file takes a regex, not a string). Execution order is :62 -> :13 -> :79, so all
# three = the bar was built; :62 + :13 without :79 = loadPlayerConfig or the bar construction
# (:73-77) raised; :62 alone = the raise was at :64-72; :79 without :13 is IMPOSSIBLE and means
# log lines were lost. The evidence file is the CLIENT console -- the mod registers nothing
# server-side and client Lua print() lands on the `LOG : Lua` channel.
PRINTS = (("show", "ss.main.lua:62",
           re.compile(r"\[SimpleStatus\] Showing status bar for player: " + USER)),
          ("load", "ss.main.lua:13",
           re.compile(r"\[SimpleStatus\] Loading config for player: " + USER)),
          ("built", "ss.main.lua:79",
           re.compile(r"\[SimpleStatus\] Status bar created for player: " + USER)))

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("td2")
path = os.path.join(run_dir, "teardown-simplestatus.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "mod": MOD,
    "workshop_item": prof.items.get(MOD),
    "subject": f"player {USER} (the mod owns no item and no script)",
    "user": USER,
    "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "fields": FIELDS,
    "field_count_expected": FIELD_COUNT,
    "moddata_keys": KEYS,
    "moddata_note": KEYS_NOTE,
    "float_format": "TK.json renders a non-integral number with tostring(v) from the harness-prep "
                    "commit of this slice on (Kahlua's numberToString -> Double.toString, an exact "
                    "round trip); every artifact before it is quantised to six decimals.",
    "tolerance": {
        "rule": "per snapshot, on the SIGNED skew of that snapshot's own wall brackets: "
                "client - server in [r*d_min, r*(d_max + 1 s)], d_min = t_srv_before - "
                "t_cli_after, d_max = t_srv_after - t_cli_before. Weight uses the opposite sign "
                "(-rho) plus one float32 ulp at each end, with rho computed from the same "
                "snapshot's readings and its arm checked against isIncWeight/isDecWeight.",
        "push_window_s": PUSH_WINDOW,
        "settle_s": SETTLE,
        "settle_rule": "a snapshot closer than settle_s to the last server write is an ARRIVAL "
                       "LATENCY reading, not a band test (graded = false).",
        "game_s_per_real_s": GAME_S_PER_REAL_S,
        "macro_rate_per_game_s": MACRO_RATE,
    },
    "acceptance_run": ACCEPTANCE_RUN,
    "world_changes": "none to restore -- no settimespeed, no sandbox write; nutrition.set writes "
                     "the character's own store and every write lands in this run's copy of the "
                     "fixture",
    "snapshots": [], "steps": [], "phase2": [], "appendix": {}, "notes": [KEYS_NOTE],
}
last_write_wall = [None]        # wall of the last SERVER write, for the settle rule


def wall():
    return round(time.time() - t0, 3)


def f32_ulp(x):
    """One float32 ulp at |x| -- the representation floor on weight, which is a double narrowed
    by `Nutrition.save`'s d2f (@36-@45 L213) and widened again by `load`'s f2d (@32-@38 L221).
    7.63e-6 at 80 kg (2^-17); computed rather than hard-coded so a different weight is honest."""
    try:
        f = struct.unpack("<f", struct.pack("<f", abs(x)))[0]
        nxt = struct.unpack("<f", struct.pack("<I", struct.unpack("<I",
                            struct.pack("<f", f))[0] + 1))[0]
        return float(nxt - f)
    except (struct.error, OverflowError, ValueError):
        return 7.62939453125e-06


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited from pass 1 rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, reply written by
        OnServerCommand into a result doc). The commands used here all answer INLINE, so it is
        DORMANT; `dormant_sent_branch` records it if it ever fires.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A string
        where a table belongs is re-asked ONCE and both readings are kept.

    Unlike pass 1's, this one is used for `stats.get` as well -- the macro read the whole band
    rests on -- so `_probe.wall` / `_probe.wall_done` exist on every reading this driver grades.
    """
    t, t_epoch = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall()}
    if isinstance(val, str) and val.strip().startswith("sent"):
        out["notes"].append(f"dormant_sent_branch fired on {cmd}")
        name = "witness_fields" if cmd == "witness.fields" else "witness_moddata"
        try:
            val = side.bus.wait_result(name, timeout=20, after=t_epoch)
        except (RuntimeError, TimeoutError, OSError) as e:
            val = {"error": f"{type(e).__name__}: {e}", "ack": val}
        meta["route"] = "result-doc"
    elif not isinstance(val, dict):
        meta["reasked"] = True
        meta["first_reply"] = val
        val = ask(side, cmd, args, timeout=timeout)
        meta["wall_done"] = wall()
    if isinstance(val, dict):
        val = dict(val)
        val["_probe"] = meta
    elif meta.get("reasked"):
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def step(name, side, cmd, args, timeout=30, is_write=False):
    """One SEQUENCED bus call: the ack, both wall clocks bracketing it, and the ack's own
    `serverWorldAge` / `gameMinute` lifted out. A server WRITE also stamps `last_write_wall`,
    which is what the settle rule reads."""
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "side": getattr(side, "username", "server"),
           "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if isinstance(val, dict):
        row["serverWorldAge"] = val.get("serverWorldAge")
        row["gameMinute"] = val.get("gameMinute")
        swa = num(val.get("serverWorldAge"))
        row["worldAgeMinutes"] = round(swa * 60.0, 4) if swa is not None else None
    else:
        row["ack_shape"] = type(val).__name__
    if is_write:
        last_write_wall[0] = t_after
        row["stamped_last_write"] = t_after
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    save(path, out, tl, server)
    return row


def fields_of(reply):
    return reply.get("fields") if isinstance(reply, dict) and \
        isinstance(reply.get("fields"), dict) else None


def keys_of(reply):
    """The census as a list. TK.json encodes an EMPTY Lua table as `{}`, so an empty `keys`
    arrives as a dict -- never test `== []`; `keyCount` is the numeric emptiness test."""
    if not isinstance(reply, dict):
        return None
    k = reply.get("keys")
    if isinstance(k, list):
        return k
    if isinstance(k, dict):
        return [] if not k else None
    return None


def census_row(reply, side_name, vanilla=VANILLA_PLAYER_KEYS):
    """The per-side player-modData census, named by side. `vanilla` is the exclusion set for THIS
    scope; applying the item-scope set here would report vanilla's own keys as findings."""
    ks = keys_of(reply)
    names = sorted(s.split(":")[0] for s in ks) if ks is not None else None
    extra = sorted(set(names or []) - vanilla) if names is not None else None
    return {"side": side_name,
            "resolved": reply.get("resolved") if isinstance(reply, dict) else None,
            "keyCount": reply.get("keyCount") if isinstance(reply, dict) else None,
            "keys": ks, "keyNames": names, "beyondVanilla": extra,
            "wall": (reply.get("_probe") or {}).get("wall") if isinstance(reply, dict) else None,
            "error": reply.get("error") if isinstance(reply, dict) else reply}


def macro_of(reply, name):
    return num(reply.get(name)) if isinstance(reply, dict) else None


def weight_rate(srv):
    """kg per REAL second on the server, SIGNED, computed from that snapshot's own readings --
    never a ceiling. Returns (rate, detail) with the predicted arm, so the H1 flags can be graded
    against it rather than the other way round."""
    cal, carbs = macro_of(srv, "calories"), macro_of(srv, "carbs")
    lip, w = macro_of(srv, "lipids"), macro_of(srv, "weight")
    if None in (cal, carbs, lip, w):
        return None, {"error": "a macro was unreadable on the server"}
    traits = [str(t).lower() for t in (srv.get("traitList") or [])
              if isinstance(srv.get("traitList"), list)]
    base = 1000.0
    if w < 90 and any("gain" in t for t in traits):
        base = 700.0
    if w > 70 and any("loss" in t for t in traits):
        base = 1800.0
    gain = base + (w - 80.0) * 40.0
    loss = min(0.0, (w - 70.0) * 30.0)
    d = {"gainThreshold": gain, "lossThreshold": loss, "traitList": srv.get("traitList"),
         "traitRoute": srv.get("traitRoute"), "base": base}
    if cal > gain:
        mult = 3.0 if (carbs > 700 or lip > 700) else (2.0 if (carbs > 400 or lip > 400) else 1.0)
        rate = WEIGHT_GAIN_BASE * mult * min(1.0, cal / 4000.0)
        d.update(arm="gain", mult=mult, ratio=min(1.0, cal / 4000.0),
                 predicted_flags={"incWeight": True, "incWeightLot": mult > 1, "decWeight": False})
    elif cal < loss:
        rate = -WEIGHT_LOT_RATE * min(1.0, abs(cal) / 2500.0)
        d.update(arm="loss", mult=1.0, ratio=min(1.0, abs(cal) / 2500.0),
                 predicted_flags={"incWeight": False, "incWeightLot": False, "decWeight": True})
    else:
        rate = 0.0
        d.update(arm="none", mult=0.0, ratio=0.0,
                 predicted_flags={"incWeight": False, "incWeightLot": False, "decWeight": False})
    d["rate_per_real_s"] = rate * GAME_S_PER_REAL_S
    return rate * GAME_S_PER_REAL_S, d


def snapshot(tag, c, globals_too=False):
    """One paired reading. The CLIENT half is read FIRST at every tag -- not only at baseline:
    the band is stated on the signed skew `t_server - t_client` and is a non-negative interval
    only while that is positive. Within a side, `stats.get` comes first: it is the macro read the
    band is built on, and putting it first keeps its bracket as tight as the bus allows."""
    row = {"tag": tag, "wall": wall(),
           "since_last_write": None if last_write_wall[0] is None
           else round(wall() - last_write_wall[0], 3)}
    for name, side in (("client", c), ("server", server)):
        arg = "" if name == "client" else USER
        stats = probe(side, "stats.get", arg)
        f = probe(side, "witness.fields", f"player {USER} {FIELDS}")
        md = probe(side, "witness.moddata", PLAYER_SCOPE)
        row[name] = {
            "stats": stats,
            "fields": f,
            "field_count": f.get("count") if isinstance(f, dict) else None,
            "field_count_ok": (f.get("count") == FIELD_COUNT) if isinstance(f, dict) else False,
            "moddata_player": md,
            "config_key": probe(side, "witness.moddata", CONFIG_KEY),
            "census_player": census_row(md, name),
        }
        if globals_too:
            row[name]["moddata_global"] = probe(side, "witness.moddata", GLOBAL_SCOPE)
            row[name]["config_leaves"] = probe(side, "witness.moddata", CONFIG_LEAVES)
    row["wall_done"] = wall()
    out["snapshots"].append(row)
    tl.mark("snapshot", tag=tag, took=round(row["wall_done"] - row["wall"], 2))
    save(path, out, tl, server)          # evidence on disk before the next phase can wedge
    return row


def grade(tag):
    """Server vs client at one tag, macro by macro, under the per-snapshot signed band."""
    row = next((r for r in out["snapshots"] if r["tag"] == tag), None)
    if row is None:
        return None
    srv, cli = row["server"]["stats"], row["client"]["stats"]
    if not isinstance(srv, dict) or not isinstance(cli, dict):
        return {"tag": tag, "error": "a stats.get reply was not a table"}
    sp, cp = srv.get("_probe") or {}, cli.get("_probe") or {}
    brackets = [num(sp.get("wall")), num(cp.get("wall_done")),
                num(sp.get("wall_done")), num(cp.get("wall"))]
    if any(b is None for b in brackets):
        # Ungradeable rather than guessed: without both sides' brackets there is no delta, and a
        # band computed from a missing one would be a number with no meaning behind it.
        return {"tag": tag, "error": "a stats.get reading carried no wall bracket",
                "brackets": brackets, "since_last_write": row["since_last_write"]}
    d_min = round(brackets[0] - brackets[1], 3)
    d_max = round(brackets[2] - brackets[3], 3)
    graded = row["since_last_write"] is None or row["since_last_write"] >= SETTLE
    w = macro_of(srv, "weight") or CAL_REF_WEIGHT
    rho, wd = weight_rate(srv)
    g = {"tag": tag, "wall": row["wall"], "delta_min": d_min, "delta_max": d_max,
         "since_last_write": row["since_last_write"], "graded": graded,
         "graded_reason": "band" if graded else
                          f"inside a write's push window (< {SETTLE}s since the last server "
                          f"write) -- an arrival latency reading, not a band test",
         "client_read": {"wall": cp.get("wall"), "wall_done": cp.get("wall_done")},
         "server_read": {"wall": sp.get("wall"), "wall_done": sp.get("wall_done")},
         "weight_model": wd, "macros": {}}
    for key in ("calories", "carbs", "lipids", "proteins", "weight"):
        s, cv = macro_of(srv, key), macro_of(cli, key)
        e = {"server": srv.get(key), "client": cli.get(key)}
        if s is None or cv is None:
            e["error"] = "unreadable on one side"
            g["macros"][key] = e
            continue
        gap = cv - s
        if key == "weight":
            r = rho
            if r is None:
                e["band"] = None
                e["note"] = "weight rate unavailable (a macro was unreadable)"
                g["macros"][key] = e
                continue
            ulp = f32_ulp(w)
            lo, hi = sorted((-r * d_min, -r * (d_max + PUSH_WINDOW)))
            lo, hi = lo - ulp, hi + ulp
            e.update(rate_per_real_s=r, arm=wd.get("arm"), ulp=ulp,
                     bit_identical=(srv.get(key) == cli.get(key)))
        else:
            r = MACRO_RATE[key] * GAME_S_PER_REAL_S
            if key == "calories":
                r *= (w / CAL_REF_WEIGHT)        # f3 = weight/80 in updateCalories' idle branch
            lo, hi = sorted((r * d_min, r * (d_max + PUSH_WINDOW)))
            e["rate_per_real_s"] = r
        e["gap_client_minus_server"] = gap
        e["band"] = [lo, hi]
        e["in_band"] = bool(lo <= gap <= hi)
        e["residual"] = 0.0 if e["in_band"] else (gap - hi if gap > hi else gap - lo)
        g["macros"][key] = e
    # The three H1 flags, per side, beside the arm the arithmetic predicts from the SERVER's own
    # readings. A client flag that disagrees with the client's OWN macros is the sharper finding.
    g["flags"] = {side: {k: row[side]["stats"].get(k) for k in
                         ("incWeight", "incWeightLot", "decWeight")}
                  for side in ("server", "client") if isinstance(row[side]["stats"], dict)}
    g["flags_predicted_from_server"] = wd.get("predicted_flags")
    g["flags_agree_across_sides"] = (g["flags"].get("server") == g["flags"].get("client"))
    g["flags_server_match_model"] = (g["flags"].get("server") == wd.get("predicted_flags"))
    # The two int/float controls that carry no band at all: neither drifts.
    sf, cf = fields_of(row["server"]["fields"]) or {}, fields_of(row["client"]["fields"]) or {}
    g["fields"] = {k: {"server": sf.get(k), "client": cf.get(k), "equal": sf.get(k) == cf.get(k)}
                   for k in sorted(set(sf) | set(cf))}
    g["maxWeight_cross_check"] = {
        "witness_server": sf.get("getMaxWeight"), "snapshot_server": srv.get("maxWeight"),
        "witness_client": cf.get("getMaxWeight"), "snapshot_client": cli.get("maxWeight"),
        "server_routes_agree": sf.get("getMaxWeight") == srv.get("maxWeight"),
        "client_routes_agree": cf.get("getMaxWeight") == cli.get("maxWeight")}
    g["traits_agree_across_sides"] = (srv.get("traitList") == cli.get("traitList"))
    g["traits"] = {"server": srv.get("traitList"), "client": cli.get("traitList"),
                   "serverRoute": srv.get("traitRoute"), "clientRoute": cli.get("traitRoute")}
    g["worldAge"] = {"server": srv.get("worldAge"), "client": cli.get("worldAge")}
    return g


def arrival_poll(c, key, target, tag, pre=None, timeout=6.0, every=0.0):
    """After a server write: how long until the CLIENT's mirror shows it. One bracketed client
    `nutrition.get` per iteration until the value reaches `target` or the window closes. This is
    the reading a t0 snapshot cannot be -- a push window's worth of latency, measured -- and it
    runs BEFORE the paired t0 snapshot for exactly that reason: a snapshot is eight bus calls, so
    a latency measured after one would be an artefact of the driver's own cadence.

    `pre` is the client's last pre-write reading. If it already met `target`, the poll measures
    nothing and says so rather than reporting a latency of one round trip."""
    rows, t_end, seen = [], time.time() + timeout, None
    while time.time() < t_end:
        r = probe(c, "nutrition.get", "")
        v = macro_of(r, key)
        rows.append({"wall": (r.get("_probe") or {}).get("wall") if isinstance(r, dict) else None,
                     "wall_done": (r.get("_probe") or {}).get("wall_done")
                     if isinstance(r, dict) else None, key: r.get(key) if isinstance(r, dict)
                     else r})
        if v is not None and v >= target:
            seen = rows[-1]["wall"]
            break
        if every:
            time.sleep(every)
    row = {"tag": tag, "key": key, "target": target, "client_before_write": pre,
           "already_at_target": None if pre is None else bool(pre >= target),
           "readings": rows, "first_seen_wall": seen, "write_wall": last_write_wall[0],
           "latency_s": None if seen is None or last_write_wall[0] is None
           else round(seen - last_write_wall[0], 3),
           "note": "an UPPER bound on arrival: the write's own ack and one client round trip "
                   "(~0.3-0.8 s each) are inside it, and the poll cannot see a packet that landed "
                   "between two reads. A lower bound it is not."}
    out.setdefault("arrivals", []).append(row)
    tl.mark("arrival", tag=tag, latency=row["latency_s"])
    save(path, out, tl, server)
    return row


def census_pair(tag, c, note):
    """Both sides' player-modData census at one moment, client first, with the difference sets --
    which is what phase 2 grades: a key on the server that the client lacks is what a
    `transmitModData()` wipe would delete."""
    cli = probe(c, "witness.moddata", PLAYER_SCOPE)
    srv = probe(server, "witness.moddata", PLAYER_SCOPE)
    rc, rs = census_row(cli, "client"), census_row(srv, "server")
    sn, cn = set(rs["keyNames"] or []), set(rc["keyNames"] or [])
    row = {"tag": tag, "wall": wall(), "note": note, "client": rc, "server": rs,
           "server_only": sorted(sn - cn), "client_only": sorted(cn - sn),
           "identical": sn == cn}
    out["phase2"].append(row)
    tl.mark("census", tag=tag, server=rs["keyCount"], client=rc["keyCount"])
    save(path, out, tl, server)
    return row


def grep_numbered(path_, rx, limit=10):
    """`session.grep_file` with the LINE NUMBER kept: which of the mod's three prints arrived, and
    in what order, is the tier-(b) evidence, and order is unreadable without the numbers."""
    hits = []
    try:
        with open(path_, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:200]})
                    if len(hits) >= limit:
                        break
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


def item_read(side, side_name, full_type, names, count):
    r = probe(side, "witness.fields", f"item {USER}/{full_type} {names}")
    return {"side": side_name, "type": full_type, "reply": r,
            "count_ok": (r.get("count") == count) if isinstance(r, dict) else False,
            "resolved": r.get("resolved") if isinstance(r, dict) else None,
            "fields": fields_of(r), "missing": r.get("missing") if isinstance(r, dict) else None,
            "wall": (r.get("_probe") or {}).get("wall") if isinstance(r, dict) else None}


try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mod_log_lines_server"] = grep_file(server.log_path, MOD_RX, limit=5)

    # ---- tier (b), recorded beside the tier-(a) verify row -------------------------------
    out["mod_log_lines"] = {name: {"cite": cite, "hits": grep_numbered(c.console, rx, limit=4)}
                            for name, cite, rx in PRINTS}
    got = {k: bool(v["hits"]) for k, v in out["mod_log_lines"].items()}
    out["mod_log_reading"] = {
        "all_three": all(got.values()),
        "got": got,
        "rule": "order is :62 -> :13 -> :79. all three = the bar was built; show+load without "
                "built = loadPlayerConfig or the bar construction (:73-77) raised; show alone = "
                "the raise was at :64-72; built without load is IMPOSSIBLE and means log lines "
                "were lost.",
        "impossible_combination": bool(got.get("built") and not got.get("load")),
    }
    tl.mark("mod_prints", **{k: str(v) for k, v in got.items()})

    # ---- folder listing, as run metadata only (NTFS makes the two spellings one directory) ----
    mods_dir = os.path.join(run_dir, "server", "mods")
    client_mods = os.path.join(run_dir, "clients", USER, "mods")
    def listing(d):
        try:
            return sorted(os.listdir(d))
        except OSError as e:                      # noqa: BLE001 - recorded, not raised
            return [f"<{type(e).__name__}: {e}>"]
    out["folder_check"] = {
        "server_mods": listing(mods_dir), "client_mods": listing(client_mods),
        "id_folder_present": MOD in listing(mods_dir),
        "mod_info_at_id": os.path.isfile(os.path.join(mods_dir, MOD, "42.16", "mod.info")),
        "reading": "metadata, NOT an answer to the rename question: on NTFS 'simpleStatus' and "
                   "'SimpleStatus' are the same directory, and no profile can reach "
                   "mods.install's name-keeping branch (every profile mod carries a non-empty "
                   "src). docs/testing/profiles.md OQ 6 stays 'first half M, second half C'.",
    }

    # ================= PHASE 1 -- the mirror the mod is built on =========================
    base = snapshot("baseline", c, globals_too=True)
    pre = base["client"]["stats"] if isinstance(base["client"]["stats"], dict) else {}
    a1 = step("t_action1", server, "nutrition.set", f"{USER} calories 2000", is_write=True)
    out["t_action1"] = {k: a1[k] for k in ("wall_before", "wall_after", "ack")}
    arrival_poll(c, "calories", 1900.0, "after_calories_2000", pre=macro_of(pre, "calories"))
    snapshot("t0", c)                    # inside the push window: a latency reading, not a band
    time.sleep(max(0.0, MIRROR_WAIT - (wall() - a1["wall_after"])))
    snapshot("t+3s", c)

    a2 = step("t_action2", server, "nutrition.set", f"{USER} carbs 800", is_write=True)
    out["t_action2"] = {k: a2[k] for k in ("wall_before", "wall_after", "ack")}
    arrival_poll(c, "carbs", 700.0, "after_carbs_800", pre=macro_of(pre, "carbs"))
    snapshot("t2+0s", c)
    time.sleep(max(0.0, MIRROR_WAIT - (wall() - a2["wall_after"])))
    snapshot("t2+3s", c)

    # ================= PHASE 2 -- the transmitModData boundary ===========================
    census_pair("p2a_baseline", c, "before anything is planted; SimpleStatusConfig expected "
                                   "absent on both sides (its seven writers are UI-input only)")
    step("plant_server", server, "moddata.set", f"{USER} {PLANT_SERVER[0]} {PLANT_SERVER[1]}")
    census_pair("p2c_after_server_plant", c,
                "the server now holds a key the client's copy does not -- the difference set the "
                "wipe needs, which vanilla alone never provides (client 5 keys vs server 4)")
    step("plant_client", c, "moddata.set", f"{PLANT_CLIENT[0]} {PLANT_CLIENT[1]}")
    census_pair("p2e_after_client_plant", c,
                "the client's own write has not crossed (S6); the server is unchanged")
    a3 = step("t_action3", c, "moddata.transmit", "")
    out["t_action3"] = {k: a3[k] for k in ("wall_before", "wall_after", "ack")}
    census_pair("p2g0_after_transmit", c,
                "immediately after transmitModData(): the prediction is that the server's census "
                "becomes exactly the client's -- pzt_ss_client arrives and pzt_ss_server is GONE "
                "(KahluaTableImpl.load @5-@6 L333 wipes before it rawsets)")
    time.sleep(MIRROR_WAIT)
    census_pair("p2g3_after_transmit_3s", c, "and again one push window later")
    first, last = out["phase2"][0], out["phase2"][-1]
    out["wipe_reading"] = {
        "planted_on_server": PLANT_SERVER[0],
        "planted_on_client": PLANT_CLIENT[0],
        "server_before_transmit": next((r["server"]["keyNames"] for r in out["phase2"]
                                        if r["tag"] == "p2e_after_client_plant"), None),
        "server_after_transmit": last["server"]["keyNames"],
        "client_after_transmit": last["client"]["keyNames"],
        "server_key_wiped": (PLANT_SERVER[0] not in (last["server"]["keyNames"] or [])),
        "client_key_arrived": (PLANT_CLIENT[0] in (last["server"]["keyNames"] or [])),
        "server_census_equals_client": last["identical"],
        "baseline_difference_set": first["server_only"],
        "reading": "server_key_wiped TRUE with client_key_arrived TRUE = load() is a WIPE AND "
                   "REPLACE, not a merge: the receiving side's table is whatever the sender had. "
                   "server_key_wiped FALSE would make it a merge and falsify Q7 risk 3.",
    }

    # ================= APPENDIX -- the two pass-1 follow-up controls =====================
    # Unrelated to simpleStatus (it ships no items): pass-1 follow-ups, reported as such.
    ok1, rep1 = server.rcon(f'additem "{USER}" "{ITEM_ABSENT}" 1')
    ok2, rep2 = server.rcon(f'additem "{USER}" "{ITEM_PRESENT}" 1')
    out["appendix"]["spawn"] = {"absent_ok": ok1, "absent_reply": str(rep1)[:200],
                                "present_ok": ok2, "present_reply": str(rep2)[:200],
                                "note": "RCON, not a bus command: a CLIENT AddItem is invisible "
                                        "to the server (spike S6)"}
    tl.mark("rcon_additem", absent=ok1, present=ok2)
    waits = []
    for attempt in range(3):
        time.sleep(SPAWN_WAIT)
        seen = probe(c, "witness.fields", f"item {USER}/{ITEM_PRESENT} getID")
        waits.append({"attempt": attempt + 1, "wall": wall(),
                      "resolved": seen.get("resolved") if isinstance(seen, dict) else None})
        if isinstance(seen, dict) and seen.get("resolved"):
            break
    out["appendix"]["spawn_wait"] = waits

    # A1 -- the vanilla display-name control. The criterion is ABSENCE FROM ItemName.json
    # (Base.FruitSaladClay: 0 hits; Base.Steak: ItemName.json:4218), not a missing DisplayName=
    # line -- no vanilla food has one.
    out["appendix"]["A1"] = {
        "question": "does a vanilla food with NO ItemName.json entry read getDisplayName() == "
                    "getFullType(), and does getActualWeightUnmodded() take its guarded arm?",
        "hypotheses": ["1 no translation entry", "2 mod translations not consulted on a "
                       "dedicated server", "3 LTP ships a B41-layout ItemName_EN.txt 42.20.4 may "
                       "never load -- NOT testable in this session (a mod-tree write)"],
        "reads": [item_read(side, name, t, ITEM_FIELDS, ITEM_FIELD_COUNT)
                  for t in (ITEM_ABSENT, ITEM_PRESENT)
                  for name, side in (("client", c), ("server", server))],
    }
    save(path, out, tl, server)

    # A2 -- does a server-spawned item's CLIENT copy ever tick? Pass 1 measured the freeze over
    # 11.1 s on an item it had not pinned; this pins heat on the server and watches for 10 s.
    step("pin_heat", server, "item.set", f"{USER} {ITEM_PRESENT} heat 2.0")
    a2_r1 = item_read(c, "client", ITEM_PRESENT, TICK_FIELDS, TICK_FIELD_COUNT)
    a2_s1 = item_read(server, "server", ITEM_PRESENT, TICK_FIELDS, TICK_FIELD_COUNT)
    time.sleep(TICK_WAIT)
    a2_r2 = item_read(c, "client", ITEM_PRESENT, TICK_FIELDS, TICK_FIELD_COUNT)
    a2_s2 = item_read(server, "server", ITEM_PRESENT, TICK_FIELDS, TICK_FIELD_COUNT)
    cf1, cf2 = a2_r1["fields"] or {}, a2_r2["fields"] or {}
    sf1, sf2 = a2_s1["fields"] or {}, a2_s2["fields"] or {}
    out["appendix"]["A2"] = {
        "question": "does the client's copy of a server-spawned, server-pinned item tick?",
        "window_s": TICK_WAIT,
        "client_read_1": a2_r1, "client_read_2": a2_r2,
        "server_read_1": a2_s1, "server_read_2": a2_s2,
        "client_moved": {k: {"first": cf1.get(k), "second": cf2.get(k),
                             "changed": cf1.get(k) != cf2.get(k)}
                         for k in ("getHeat", "getCookingTime")},
        "server_moved": {k: {"first": sf1.get(k), "second": sf2.get(k),
                             "changed": sf1.get(k) != sf2.get(k)}
                         for k in ("getHeat", "getCookingTime")},
        "container": {
            "client_present": cf1.get("getContainer") is not None,
            "server_present": sf1.get("getContainer") is not None,
            "client_stable": cf1.get("getContainer") == cf2.get("getContainer"),
            "server_stable": sf1.get("getContainer") == sf2.get("getContainer"),
            "client_type_token": str(cf1.get("getContainer") or "").split(" ")[0] or None,
            "server_type_token": str(sf1.get("getContainer") or "").split(" ")[0] or None,
            "reading": "PRESENCE and within-side stability only. ItemContainer.toString() is "
                       "getType() + String.valueOf(getParent()) (@0-@16 L3513) and the parent's "
                       "IsoObject.toString() ends in an identity hash (@42 L5982), so the full "
                       "strings must NEVER be compared across sides.",
        },
        "reading": "client values identical while the server's moved = the client copy does not "
                   "tick, extending pass 1's freeze to a server-PINNED item. Client values moved "
                   "= the copy ticks and pass 1's freeze was a push-timing artefact.",
    }

    # ---- the last macro pair: a long, write-free window for the empirical slope -----------
    snapshot("final", c)

    # ================= grading ==========================================================
    out["grades"] = [g for g in (grade(t) for t in ("baseline", "t0", "t+3s", "t2+0s", "t2+3s",
                                                    "final")) if g is not None]
    # The empirical decay slope, which costs nothing and checks the one unverified term in `r`
    # (Thermoregulator.getEnergyMultiplier ~= 1): successive SERVER calorie readings over this
    # driver's own wall deltas, on every consecutive pair with no calorie write between them.
    slopes = []
    rows = [r for r in out["snapshots"] if isinstance(r["server"]["stats"], dict)]
    for a, b in zip(rows, rows[1:]):
        if a["tag"] == "baseline":
            continue                     # t_action1 sets calories between these two
        ca, cb = macro_of(a["server"]["stats"], "calories"), macro_of(b["server"]["stats"], "calories")
        wa = num(((a["server"]["stats"].get("_probe")) or {}).get("wall"))
        wb = num(((b["server"]["stats"].get("_probe")) or {}).get("wall"))
        if None in (ca, cb, wa, wb) or wb <= wa:
            continue
        slopes.append({"from": a["tag"], "to": b["tag"], "seconds": round(wb - wa, 3),
                       "calories_from": ca, "calories_to": cb,
                       "slope_per_real_s": round((ca - cb) / (wb - wa), 6)})
    w_last = macro_of(rows[-1]["server"]["stats"], "weight") if rows else None
    derived = MACRO_RATE["calories"] * GAME_S_PER_REAL_S * ((w_last or CAL_REF_WEIGHT) /
                                                            CAL_REF_WEIGHT)
    longest = max(slopes, key=lambda s: s["seconds"]) if slopes else None
    out["empirical_slope"] = {
        "pairs": slopes, "longest": longest, "derived_r_calories_per_real_s": derived,
        "ratio_measured_over_derived": None if not longest or not derived
        else round(longest["slope_per_real_s"] / derived, 4),
        "rule": "grade with the MEASURED slope when the two differ by more than 10 %, and say "
                "which was used; the derived one assumes Thermoregulator.getEnergyMultiplier "
                "~= 1, which nothing has measured.",
    }
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mod_prints": out["mod_log_reading"]["got"],
        "graded_snapshots": [g["tag"] for g in out["grades"] if g.get("graded")],
        "out_of_band": [{g["tag"]: [k for k, e in g["macros"].items() if e.get("in_band") is False]}
                        for g in out["grades"] if g.get("graded")],
        "flags_agree": {g["tag"]: g.get("flags_agree_across_sides") for g in out["grades"]},
        "traits_agree": {g["tag"]: g.get("traits_agree_across_sides") for g in out["grades"]},
        "wipe": out["wipe_reading"]["server_key_wiped"],
        "client_copy_ticked": any(v["changed"] for v in
                                  out["appendix"]["A2"]["client_moved"].values()),
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
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "teardown-simplestatus.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "empirical_slope": out.get("empirical_slope"),
                  "wipe_reading": out.get("wipe_reading"),
                  "grades": [{g["tag"]: {"delta": [g.get("delta_min"), g.get("delta_max")],
                                         "graded": g.get("graded"),
                                         "macros": {k: [e.get("gap_client_minus_server"),
                                                        e.get("band"), e.get("in_band")]
                                                    for k, e in g.get("macros", {}).items()}}}
                             for g in out.get("grades", [])],
                  "error": out.get("error")}, indent=1)[:6000])
