"""Slice 12, session 1 (`x121`): the override / eat-hook / nutrient session -- LIVE.

**The subject is ours, and that is the whole design.** Every teardown before this one probed a
mod somebody else shipped and had to work around whatever surface it happened to expose. Here
the three mods under test (`TKX_ItemOverride`, `TKX_Nutrient`, `TKX_EatHook`, built offline in
Task 1) were written to ship exactly the file that discriminates, so each phase below is a
prepared experiment rather than an opportunistic read.

Nine phases, in an order that is load-bearing (controller amendment 4):

  M1  script census -- `items.count` plus `item.script` on the four redefined/new types, BOTH
      sides. **A Base `item.script` yields no macro, by design**: `TK.SCRIPT_GETTERS`
      (`PZTestKit_Core.lua:207-211`) comes back with all four nutrition keys ABSENT on a SCRIPT
      item because Kahlua does not expose them (measured slice 01, re-confirmed in
      `td1-20260910-192457`). A missing `Calories` here is the known gap, NOT a defect; only the
      INSTANCE getters of M2/M3 discriminate.
  M2  R1 (full restatement) + R2 (the narrowed partial block) -- does a second `item Apple` in
      `module Base` REPLACE the vanilla block or MERGE into it?
  M3  R7 -- two mods redefining `item Watermelon`; which body wins.
  M4  R3 -- three identical items in `module TKX` with three different translation states, read
      through the instance getters and through `text.get` on both sides.
  M5  the two eating interception points -- the script `OnEat` callback and a Lua wrapper of
      `ISEatFoodAction:complete` -- and which SIDE each fires on.
  M6  a new nutrient field on PLAYER modData, and the SERVER -> client `transmitModData()`
      direction this library has never measured.
  M7  the same field on ITEM modData, through `syncItemFields()`.
  M8  carried from slice 11: the weight-direction flags under a NON-TRIVIAL arm.
  M9  the WIPE half of `transmitModData` -- a server-only key, then a CLIENT transmit.

M5 runs before M6 on purpose: the eat-hook's own modData keys are then part of the table M6
transmits, so the transmit is graded on a table with something in it. M6 runs before M9 for the
same kind of reason -- M9's wipe reading is only meaningful once the client's table is already
the server's, which is exactly what M6's arm 2 makes true.

**Why every read is wall-bracketed, and why the CLIENT is read first at every tag** (pass-2
lesson, `docs/decisions.md:158`): the two sides of a snapshot are separate bus round trips ~1 s
apart, so the sign of any cross-side comparison follows the READ ORDER rather than the game. A
key seen on one side and not the other inside a transmit's push window is a LATENCY reading, not
a desync. Every tag records its own measured wall offsets and is NAMED by what was measured, not
by the sleep that was asked for (slice-11 driver note, `docs/testing/README.md`: the `td3`
driver's `t+3s` tag actually landed at +7.6 s).

**World changes restored inside the `try`:** the calorie store M8 drives is written back to the
value it held when M8 started. Everything else this run writes is modData the fixture does not
own and the next run does not read -- `TKX_transmit_now` (M6), `TKX_ServerOnly` (M9) and the
mod's own `TKX_fibre` / `TKX_fibre_client` / `TKX_eat_onEat_*` -- and there is no delete on the
bus, so they are LEFT IN PLACE and named in `out["world_changes"]` instead. The RCON-spawned
items live in this run's copy of the fixture (`fx.restore_server` / `restore_client` into
`run_dir`) and never touch the golden one.

**`lua.reload` is NEVER sent.** Mod C's `ISEatFoodAction.complete` wrapper is sentinel-guarded
and idempotent, but reloading the file would re-execute VANILLA's `ISEatFoodAction` definition
underneath a live wrapper, and that is not a state any reading here should be taken in.

Never raises through teardown; the artifact is written before and after teardown and copied
byte-for-byte into `testing/artifacts/<run-id>/`.
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

PROFILE = "x12-overrides"
USER = "admin"
MODS = ("PZTestKit", "TKX_ItemOverride", "TKX_Nutrient", "TKX_EatHook")
# Step 2's acceptance run: RESULT PASS, all three [[verify]] rows ok=True, 0 server error lines,
# 0 client Lua errors. It is also the smoke test for BOTH slice-12 harness commits (ad683fe, the
# text.get move to shared/, and 5d9633f, the null guard this task landed ahead of the session).
ACCEPTANCE_RUN = "run-20260911-024303"

# ---- timings, all of them derived rather than guessed -----------------------------------------
DAY_LENGTH = 4           # the fixture's own (testing/fixtures/default/.../pzt_SandboxVars.lua:53)
GAME_MINUTE_S = 3.75     # DayLength 4 = a 90-minute game day: 5400 s / 1440 game minutes
TICK_WAIT = 3 * GAME_MINUTE_S      # >= 2 EveryOneMinute firings, with a third for the round trip
MIRROR_WAIT = 3.0        # > the 1 Hz PlayerStatsPacket window (every prior slice's number)
LAZY_WAIT = 40.0         # s past session_ready for the LATE census: pass 2 saw the server's four
                         # vanilla fitness keys appear between +22 s and +33.4 s
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory (s01/s02/s05)
SPAWN_TRIES = 4
EAT_POLL_S, EAT_POLL_N = 2.5, 10   # up to 25 s for the queued action to complete server-side

# ---- M8's cadence, CONFIRMED ON THE JAR before the wait was chosen (amendment 3) ---------------
# `./pz.sh grep updateWeight` names only three classes, and the only one that is this method's
# owner is `Nutrition` itself -- so `Nutrition.updateWeight` has NO caller outside its own class.
# Inside it the single call site is `Nutrition.update @107 L81`, reached UNCONDITIONALLY (the
# `GameClient.client` test at `@42 L75` guards only the three macro decays and `updateCalories`,
# and jumps to @106, i.e. straight onto the `updateWeight` call). `Nutrition.update` is in turn
# called from `IsoPlayer.updateInternal2 @392-@402 L2306-L2307` behind ONE gate,
# `SystemDisabler.doCharacterStats` -- no timer, no game-minute stamp -- and `updateInternal2` is
# reached every character update: `IsoPlayer.update @8` -> `updateInternal1` -> `@51 L2200`
# `updateInternal2` (the non-animal arm).
M8_CADENCE = ("per character update tick, no timer gate: IsoPlayer.update @8 -> updateInternal1 "
              "@51 L2200 -> updateInternal2 @392-@402 L2306-L2307 (gated only on "
              "SystemDisabler.doCharacterStats) -> Nutrition.update @107 L81 -> updateWeight. "
              "Jar-read 2026-09-11 on 42.20.4; `grep updateWeight` finds the name in only three "
              "classes and no caller of THIS one outside Nutrition itself.")
# Amendment 3's rule: ">= 40 s per arm if it runs once per game hour or every ten game minutes; if
# once per game minute, 8 s suffices". Per-TICK is strictly more frequent than once per game
# minute, so the 8 s arm applies -- and 8 s is independently >= 2x the 1 Hz PlayerStatsPacket
# mirror window that decides whether the CLIENT's flags can have been recomputed yet, which is
# the actual question. Recorded beside the reading rather than left implicit.
M8_WAIT_S = 8.0
M8_HIGH, M8_LOW = "1500", "-100"

# ---- M1 ---------------------------------------------------------------------------------------
SCRIPT_TYPES = ("Base.Apple", "Base.Orange", "Base.Watermelon", "TKX.FibreBar")
# TK.SCRIPT_GETTERS, copied here so the absent set can be computed Python-side
# (PZTestKit_Core.lua:207-211). The four MACRO_KEYS are the ones Kahlua is known not to expose on
# a SCRIPT object -- their absence below is that gap, not a defect.
SCRIPT_GETTERS = ("HungerChange", "ThirstChange", "Calories", "Carbohydrates", "Lipids",
                  "Proteins", "DaysFresh", "DaysTotallyRotten", "IsCookable",
                  "MinutesToCook", "MinutesToBurn")
MACRO_KEYS = ("Calories", "Carbohydrates", "Lipids", "Proteins")
# testing/artifacts/exp05-20260910-084109/food-scan.json:350 -- `foodByModule.Base`. NOT 1005,
# which is that dataset's total item RECORDS; the live census's own `total` is the comparable
# number for that.
BASE_FOOD_BASELINE = 722

# ---- M2 / M3: the five macro getters, comma-joined and whitespace-free (witness.fields grammar).
# Zero-argument getters only -- an arity mismatch is as uncatchable in Kahlua as a nil call.
MACROS = "getCalories,getCarbohydrates,getLipids,getProteins,getHungChange"
MACRO_COUNT = 5
# Vanilla instance values, for the falsifier. `getHungChange()` is the SCRIPT's HungerChange / 100
# (Item.InstanceItem), so Orange's -12.0 in the script reads -0.12 on the instance.
VANILLA = {
    "Base.Apple": {"getCalories": 95.0, "getCarbohydrates": 25.13, "getLipids": 0.31,
                   "getProteins": 0.47, "getHungChange": -0.16},
    "Base.Orange": {"getCalories": 65.0, "getCarbohydrates": 16.27, "getLipids": 0.3,
                    "getProteins": 1.0, "getHungChange": -0.12},
    "Base.Watermelon": {"getCalories": 1355.0, "getCarbohydrates": 341.11, "getLipids": 6.78,
                        "getProteins": 27.56, "getHungChange": -0.6},
}

# ---- M4 ---------------------------------------------------------------------------------------
FIBRE_TYPES = ("TKX.FibreBar", "TKX.FibreBarNamed", "TKX.FibreBarJson")
NAME_FIELDS = "getDisplayName,getFullType,getActualWeight,getActualWeightUnmodded"
NAME_COUNT = 4
# The two the brief names, plus TWO controls that cost one ack each and without which the server
# half is unreadable. `ItemName_Base.Apple` is the VANILLA control: the acceptance run's server
# log shows `mod "TKX_ItemOverride" overrides media/lua/shared/translate/en/itemname.json`, so a
# reader has to be able to tell "the mod's ItemName.json displaced vanilla's whole table" from
# "mod translations never reach a dedicated server". `ItemName_TKX.FibreBar` is the NEGATIVE
# control -- an item with no entry in either file, which must miss on both sides or the command
# is answering something other than the translation table.
TEXT_KEYS = (
    ("ItemName_TKX.FibreBarJson", "mod, B42 ItemName.json layout -- the hypothesis (iii) test"),
    ("ItemName_TKX.FibreBarNamed", "mod, B41 ItemName_EN.txt layout -- the hypothesis (ii) test"),
    ("ItemName_TKX.FibreBar", "negative control: no entry in EITHER file, must miss on both "
                              "sides"),
    ("ItemName_Base.Apple", "vanilla control: did the mod's same-named ItemName.json displace "
                            "vanilla's table, and does a dedicated server have one at all?"),
)

# ---- M5 ---------------------------------------------------------------------------------------
EAT_TYPE = "Base.Banana"          # mod C restates it with `OnEat = TKX_OnEatProbe`
EAT_FRACTION = "1.0"
# `lua.global` never CALLS what it finds, so every name here is a value read. Presence is
# `v == nil` and never `if not v`: `lastFraction` starts at -1 and `wrapped` can be the boolean
# false, both of which are PRESENT.
EAT_GLOBALS = (
    ("TK.version", "control -- MUST answer 1 on BOTH sides; resolved=false here means the _G "
                   "walk is broken, not that a mod global is absent"),
    ("TKX_EatHook.calls", "P6: >= 1 on BOTH sides. The server's from Eat @762 L5811; the "
                          "client's from EatFoodPacket -> EatOnClient @0-@57 L5725-L5736, which "
                          "applies NO numbers"),
    ("TKX_EatHook.completes", "P7: >= 1 on the SERVER only. A client >= 1 would overturn "
                              "LuaTimedActionNew.complete @31 L162"),
    ("TKX_EatHook.order", "P7: begins \"complete\" on the server -- the Lua wrapper runs before "
                          "IsoGameCharacter.Eat, which is the whole point of sitting there"),
    ("TKX_EatHook.lastSide", "which side the OnEat probe resolved itself as"),
    ("TKX_EatHook.lastFraction", "the fraction the engine passed OnEat; -1 = never called"),
    ("TKX_EatHook.lastCalories", "the calorie store as OnEat saw it; -1 = never called"),
    ("TKX_EatHook.lastComplete", "the item the complete() wrapper saw, still intact"),
    ("TKX_EatHook.wrapped", "NOT a measurement -- the disambiguator. completes == 0 with "
                            "wrapped == false is 'the wrapper never installed'; with "
                            "wrapped == true it is 'complete() never ran on this side'"),
    ("TKX_EatHook.wrapAt", "which install call did the wrapping (file scope / boot event)"),
)
EAT_MODDATA = f"player:{USER} TKX_eat_onEat_server TKX_eat_onEat_client"

# ---- M6 / M7 ----------------------------------------------------------------------------------
PLAYER_SCOPE = f"player:{USER} *"
ITEM_TYPE = "Base.Cheese"
ITEM_SCOPE = f"item:{USER}/{ITEM_TYPE} *"
TRANSMIT_KEY = "TKX_transmit_now"      # arm 2's trigger, cleared by the mod's own next tick
NUTRIENT_GLOBALS = ("TKX_Nutrient.ticks", "TKX_Nutrient.itemWrites", "TKX_Nutrient.side")

# ---- M9 ---------------------------------------------------------------------------------------
# A key the CLIENT's copy has never held, planted server-side BEFORE any client transmit.
SERVER_ONLY_KEY, SERVER_ONLY_VALUE = "TKX_ServerOnly", "1"

# ---- Per-SCOPE exclusion sets (pass-1 precedent, docs/decisions.md:133). Applying the item set
# to a player census would report vanilla's own keys as findings, and vice versa.
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}
VANILLA_ITEM_KEYS = {"customName", "Tooltip"}

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"

# `session.grep_file` / `grep_numbered` take a COMPILED regex and the escaping is the caller's job
# (pass-2 lesson, session.py:51). LIMITS: the acceptance run printed FOUR `mod "TKX_*" overrides`
# lines on the server and EIGHT on the client (two Lua states x four), and three / six `loading
# TKX_` lines. A limit is a BREAK, not a window -- a result of exactly `limit` means SATURATION --
# so every one of these is sized at >= 2 x predicted with headroom on top.
OVERRIDE_RX = re.compile(r'mod "TKX_[A-Za-z]+" overrides')
LOADING_RX = re.compile(r"loading TKX_")
NILCALL_RX = re.compile(r"tried to call nil|stack traceback|attempted to index")
OVERRIDE_LIMIT, LOADING_LIMIT, NILCALL_LIMIT = 20, 16, 12

# The dormant `sent` branch's routing table, widened per the slice-11 driver note
# (docs/testing/README.md: td3's map covered only two of the five commands `probe` carries, so a
# fire on any other would have blocked on the wrong result document). Anything NOT in here is
# recorded raw rather than waited on.
RESULT_DOC = {"witness.fields": "witness_fields", "witness.moddata": "witness_moddata"}

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x121")
path = os.path.join(run_dir, "platform-overrides.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": "x121 -- slice 12 session 1: item overrides, eat hooks, custom nutrient fields",
    "user": USER,
    "profile": prof.report(),
    "mods": list(MODS),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "fixture_day_length": DAY_LENGTH,
    "game_minute_seconds": GAME_MINUTE_S,
    "vanilla_player_keys": sorted(VANILLA_PLAYER_KEYS),
    "vanilla_item_keys": sorted(VANILLA_ITEM_KEYS),
    "field_counts_expected": {"macros": MACRO_COUNT, "names": NAME_COUNT},
    "phase_order_note": "amendment 4: M5 before M6 so the eat-hook's modData keys are in the "
                        "table M6 transmits; M6 before M9 so M9's wipe reading is taken on a "
                        "client table that is already the server's.",
    "world_changes": {
        "restored": "the calorie store (M8) is written back to the value it held when M8 "
                    "started, inside the try, before teardown.",
        "left_in_place": [TRANSMIT_KEY, SERVER_ONLY_KEY, "TKX_fibre", "TKX_fibre_client",
                          "TKX_eat_onEat_server", "TKX_eat_onEat_client",
                          f"item modData TKX_fibre on {ITEM_TYPE}"],
        "why": "there is no delete on the bus; none of these keys is owned by the fixture and "
               "none is read by any other run. They are named here rather than removed.",
        "spawned": "RCON-spawned items live in this run's copy of the fixture (run_dir), never "
                   "in the golden one.",
        "lua_reload": "never sent -- mod C's ISEatFoodAction wrapper is sentinel-guarded, but "
                      "re-executing the vanilla file underneath a live wrapper is not a state "
                      "any reading here should be taken in.",
    },
    "m8": {"cadence": M8_CADENCE, "wait_s": M8_WAIT_S},
    "steps": [], "notes": [], "phases": {}, "verdicts": {},
}


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). Every command used here answers INLINE, so it is
        DORMANT; `RESULT_DOC` is the widened routing table (slice-11 driver note) and a command
        absent from it is recorded raw rather than blocked on.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A string
        where a table belongs is re-asked ONCE and BOTH readings are kept.
    """
    t, t_epoch = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall()}
    if isinstance(val, str) and val.strip().startswith("sent"):
        name = RESULT_DOC.get(cmd)
        out["notes"].append({"dormant_sent_branch": cmd, "routed_to": name})
        if name is None:
            meta["route"] = "unmapped -- ack kept raw rather than waiting on a result doc"
        else:
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


def step(name, side, cmd, args, timeout=30):
    """One SEQUENCED bus call: the ack, both wall clocks bracketing it, and the ack's own
    `serverWorldAge` / `gameMinute` lifted out where the reply carries them, so a game-minute
    rollover between two steps is measured rather than assumed."""
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
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    save(path, out, tl, server)
    return row


def grade(phase, predicted, observed, verdict, falsifier, extra=None):
    """The prediction, the falsifier, the reading and the verdict, in one place and beside each
    other. `verdict` is one of as_predicted / falsified / trivial / unmeasured -- a reading that
    comes back trivial or unmeasured is RECORDED as such and never re-run into a prettier one."""
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    if extra:
        row.update(extra)
    out["verdicts"][phase] = row
    # `name=`, NOT `phase=`: Timeline.mark's first POSITIONAL parameter is called `phase`
    # (session.py:31), so a `phase=` keyword here is a TypeError, not a detail field.
    tl.mark("verdict", name=phase, verdict=verdict)
    save(path, out, tl, server)
    return row


def fields_of(reply):
    return reply.get("fields") if isinstance(reply, dict) and \
        isinstance(reply.get("fields"), dict) else None


def keys_of(reply):
    """The census as a list. `TK.json` encodes an EMPTY Lua table as `{}`, so an empty `keys`
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
    """The per-side census, named by side, with the wall offset against session_ready that makes
    a server reading of 0 keys READABLE (pass 2: the four vanilla fitness keys are written
    server-side lazily, ~30 s into the session)."""
    ks = keys_of(reply)
    names = sorted(s.split(":")[0] for s in ks) if ks is not None else None
    extra = sorted(set(names or []) - vanilla) if names is not None else None
    w = (reply.get("_probe") or {}).get("wall") if isinstance(reply, dict) else None
    ready = out.get("session_ready_wall")
    return {"side": side_name,
            "resolved": reply.get("resolved") if isinstance(reply, dict) else None,
            "keyCount": reply.get("keyCount") if isinstance(reply, dict) else None,
            "keys": ks, "keyNames": names, "beyondVanilla": extra,
            "wall": w,
            "since_session_ready": None if w is None or ready is None else round(w - ready, 3),
            "error": reply.get("error") if isinstance(reply, dict) else reply}


def census_pair(tag, c, note_text, scope=PLAYER_SCOPE, vanilla=VANILLA_PLAYER_KEYS):
    """Both sides' modData census at one moment, CLIENT FIRST, with the difference sets -- which
    is what every transmit phase grades: a key on the server the client lacks is what a
    `transmitModData()` wipe would delete, and vice versa."""
    cli = probe(c, "witness.moddata", scope)
    srv = probe(server, "witness.moddata", scope)
    rc, rs = census_row(cli, "client", vanilla), census_row(srv, "server", vanilla)
    sn, cn = set(rs["keyNames"] or []), set(rc["keyNames"] or [])
    row = {"tag": tag, "wall": wall(), "note": note_text, "scope": scope,
           "client": rc, "server": rs, "client_raw": cli, "server_raw": srv,
           "server_only": sorted(sn - cn), "client_only": sorted(cn - sn),
           "identical": sn == cn,
           "measured_span_s": round(wall() - (rc["wall"] or wall()), 3)}
    out.setdefault("censuses", []).append(row)
    tl.mark("census", tag=tag, server=rs["keyCount"], client=rc["keyCount"])
    save(path, out, tl, server)
    return row


FIELD_CHECKS = []


def field_read(side, side_name, subject, names, count, why=""):
    """One `witness.fields` read with its `count` CHECKED against the expected name count on every
    reply (amendment 7), not merely recorded. Note `len(fields) + len(missing) + len(nils)` equals
    `count` only when every name asked for was distinct -- so the reconciliation here is against
    the names SENT, which is what the README's own warning asks for."""
    r = probe(side, "witness.fields", f"{subject} {names}")
    ok = isinstance(r, dict) and r.get("count") == count
    row = {"side": side_name, "subject": subject, "why": why,
           "count": r.get("count") if isinstance(r, dict) else None,
           "count_expected": count, "count_ok": ok,
           "resolved": r.get("resolved") if isinstance(r, dict) else None,
           "error": r.get("error") if isinstance(r, dict) else r,
           "fields": fields_of(r),
           "missing": r.get("missing") if isinstance(r, dict) else None,
           "nils": r.get("nils") if isinstance(r, dict) else None,
           "wall": (r.get("_probe") or {}).get("wall") if isinstance(r, dict) else None,
           "reply": r}
    FIELD_CHECKS.append({"subject": subject, "side": side_name, "count_ok": ok,
                         "count": row["count"], "expected": count})
    return row


def both_fields(c, subject, names, count, why=""):
    """CLIENT FIRST at every tag, then the server -- the read order is what fixes the sign of any
    cross-side comparison, so it is never left to chance."""
    return {"client": field_read(c, "client", subject, names, count, why),
            "server": field_read(server, "server", subject, names, count, why)}


def grep_numbered(path_, rx, limit):
    """`session.grep_file` with the LINE NUMBER kept: which loader lines arrived, and in what
    order, is part of the evidence, and order is unreadable without the numbers."""
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


def greps(name, rx, limit, c):
    """One regex over BOTH logs, with the saturation test written down rather than left to the
    reader: `limit` is a BREAK, so a result of exactly `limit` is saturation, never a census."""
    s = grep_numbered(server.log_path, rx, limit)
    k = grep_numbered(c.console, rx, limit)
    return {"pattern": rx.pattern, "limit": limit,
            "server": {"count": len(s), "saturated": len(s) >= limit, "hits": s},
            "client": {"count": len(k), "saturated": len(k) >= limit, "hits": k},
            "client_rule": "a client console runs TWO Lua states and prints engine load output "
                           "once per state, so the client count is expected at 2x the server's.",
            "name": name}


def spawn(fullType, c, why=""):
    """RCON `additem`, then poll the CLIENT until the instance resolves there.

    RCON and not a client-side `AddItem`: a client spawn is invisible to the server (spike S6) and
    eating one makes the server log a `SyncItemFields` NPE. The poll matters for the same reason --
    `eat.action`'s own `findOrSpawn` falls back to a CLIENT spawn when the item is not there yet,
    so M5 must not be sent until this returns resolved."""
    ok, reply = server.rcon(f'additem "{USER}" "{fullType}" 1')
    row = {"type": fullType, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = probe(c, "witness.fields", f"item {USER}/{fullType} getID")
        res = seen.get("resolved") if isinstance(seen, dict) else None
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res,
                                "id": (fields_of(seen) or {}).get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    row["measured_wait_s"] = round(row["attempts"][-1]["wall"] - row["wall_rcon"], 3) \
        if row["attempts"] else None
    out.setdefault("spawns", []).append(row)
    tl.mark("spawn", type=fullType, resolved=row["resolved"])
    save(path, out, tl, server)
    return row


def cal(reply):
    """The calorie store out of a `nutrition.get` reply, or None."""
    return num(reply.get("calories")) if isinstance(reply, dict) else None


def flags(reply):
    """The three weight-direction flags. They are BOOLEANS, so presence is tested with `in` and
    never with truthiness -- `false` is a reading."""
    if not isinstance(reply, dict):
        return None
    return {k: reply.get(k) for k in ("incWeight", "incWeightLot", "decWeight") if k in reply}


def nutrition_pair(tag, c):
    """`nutrition.get` on both sides, CLIENT FIRST, with its own wall bracket. The client takes no
    argument (a client only ever has its own player); the server takes the username."""
    t = wall()
    cli = probe(c, "nutrition.get", "")
    srv = probe(server, "nutrition.get", USER)
    row = {"tag": tag, "wall": t, "wall_done": wall(),
           "client": cli, "server": srv,
           "client_calories": cal(cli), "server_calories": cal(srv),
           "client_flags": flags(cli), "server_flags": flags(srv),
           "client_weight": num(cli.get("weight")) if isinstance(cli, dict) else None,
           "server_weight": num(srv.get("weight")) if isinstance(srv, dict) else None}
    row["flags_agree"] = (row["client_flags"] == row["server_flags"]
                          and row["client_flags"] is not None)
    out.setdefault("nutrition", []).append(row)
    tl.mark("nutrition", tag=tag, server=row["server_calories"], client=row["client_calories"])
    save(path, out, tl, server)
    return row


def close(a, b, tol=1.3e-4):
    """float32 band, the slice-08 tolerance: the bus renders with `tostring`, and a script value
    round-trips through a float, so 25.13 reads 25.129999. Never an equality test."""
    if a is None or b is None:
        return None
    return abs(a - b) <= tol * max(1.0, abs(b))


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
    # Slice-11 driver note 1: a NEGATIVE the run establishes belongs in the artifact. `pzt run`
    # checks this and the artifact never recorded it, so "no mod failed to load" was unsayable.
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    # ---- the loader's own lines. From FILES, so this costs no bus time and cannot delay the
    # join-time census below.
    out["greps"] = {k: greps(k, rx, lim, c) for k, rx, lim in (
        ("overrides", OVERRIDE_RX, OVERRIDE_LIMIT),
        ("loading", LOADING_RX, LOADING_LIMIT),
        ("lua_errors", NILCALL_RX, NILCALL_LIMIT))}
    out["greps"]["reading"] = (
        "`overrides` is the loader's activeFileMap shadowing print, one line per shadowed file "
        "per mod. TKX_ItemOverride ships media/lua/shared/Translate/EN/ItemName.json, which "
        "COLLIDES with vanilla's -- so an `itemname.json` tail here is what makes M4's vanilla "
        "text.get control load-bearing rather than decorative.")
    tl.mark("greps", overrides_server=out["greps"]["overrides"]["server"]["count"],
            overrides_client=out["greps"]["overrides"]["client"]["count"])

    # ================= M6, part 1: the JOIN-time census pair ============================
    # Part of M6 but taken HERE, as close to client_ready as the bus allows: pass 2 measured the
    # server's player modData empty at join and carrying the four vanilla fitness keys only from
    # ~30 s in, so "server-side only" is a claim about a moment and not about the session.
    m6_join = census_pair("m6_join", c, "as close to client_ready as the bus allows; the server's "
                                        "vanilla fitness keys are written LAZILY (~30 s), so a "
                                        "keyCount here is only readable beside its offset")

    # ================= M1 -- the script census ==========================================
    counts = step("m1_items_count", server, "items.count", "")
    cnt = counts["ack"] if isinstance(counts["ack"], dict) else {}
    by_module = cnt.get("foodByModule") if isinstance(cnt.get("foodByModule"), dict) else {}
    scripts = {}
    for t in SCRIPT_TYPES:
        scripts[t] = {"client": probe(c, "item.script", t),      # CLIENT FIRST at every tag
                      "server": probe(server, "item.script", t)}
    out["phases"]["M1"] = {
        "question": "does a redefinition ADD an item record or REPLACE one, and does the script "
                    "object expose the macros to Kahlua?",
        "items_count": cnt,
        "scripts": scripts,
        "script_macro_gap": "TK.SCRIPT_GETTERS (PZTestKit_Core.lua:207-211) comes back with all "
                            "four nutrition keys ABSENT on a SCRIPT item -- measured slice 01, "
                            "re-confirmed in td1-20260910-192457. A missing `Calories` below is "
                            "that KNOWN GAP, not a defect; only M2/M3's instance getters "
                            "discriminate.",
        "baseline_base_food": BASE_FOOD_BASELINE,
        "baseline_source": "testing/artifacts/exp05-20260910-084109/food-scan.json:350 "
                           "(foodByModule.Base; 1005 is that dataset's total item RECORDS, not "
                           "its food count)",
    }

    def script_access(t, side):
        """Which of TK.SCRIPT_GETTERS this side's SCRIPT object actually answered, and which it
        did not. An absent getter simply never lands in `access` (TK.scriptValues:231-245), so
        the absent set is the complement -- and for the four nutrition keys it is the KNOWN
        Kahlua gap, which is why it is reported rather than graded."""
        r = scripts[t][side]
        if not isinstance(r, dict):
            return {"reply_shape": type(r).__name__, "raw": str(r)[:120]}
        acc = r.get("access") if isinstance(r.get("access"), dict) else {}
        return {"answered": sorted(acc), "absent": sorted(set(SCRIPT_GETTERS) - set(acc)),
                "via": r.get("via"),
                "macro_keys_present": [g for g in MACRO_KEYS if g in acc]}

    base_food, tkx_food = by_module.get("Base"), by_module.get("TKX")
    if base_food is None or tkx_food is None:
        m1v = "unmeasured"
    elif tkx_food == 3 and base_food == BASE_FOOD_BASELINE:
        m1v = "as_predicted"
    else:
        m1v = "falsified"
    out["phases"]["M1"]["script_access"] = {t: {s: script_access(t, s)
                                                for s in ("client", "server")}
                                            for t in SCRIPT_TYPES}
    grade("M1",
          f"P1: foodByModule.TKX == 3 and foodByModule.Base == {BASE_FOOD_BASELINE} (-0 against "
          "the baseline) -- a redefinition REPLACES, it does not add",
          {"foodByModule.TKX": tkx_food, "foodByModule.Base": base_food,
           "delta_vs_baseline": None if base_food is None else base_food - BASE_FOOD_BASELINE,
           "total": cnt.get("total"), "food": cnt.get("food"),
           "script_access": out["phases"]["M1"]["script_access"]},
          m1v,
          f"{BASE_FOOD_BASELINE + 3} falsifies it (a redefinition ADDS). "
          f"{BASE_FOOD_BASELINE - 1} says the narrowed Orange lost its ItemType after all and "
          "R2 must be re-read before M2 is graded")

    # ================= M2 -- R1 (full restatement) + R2 (the narrowed partial block) =====
    m2 = {"question": "what happens to the vanilla block, and to the keys the mod's block omits?",
          "items": {}}
    for t in ("Base.Apple", "Base.Orange"):
        sp = spawn(t, c, "M2: the instance is the only route to the macros -- the script object "
                         "does not expose them to Kahlua")
        m2["items"][t] = {"spawn": sp,
                          "witness": both_fields(c, f"item {USER}/{t}", MACROS, MACRO_COUNT,
                                                 "the five macro getters on the INSTANCE"),
                          "server_item_get": step(f"m2_item_get_{t}", server, "item.get",
                                                  f"{USER} {t}")["ack"],
                          "vanilla": VANILLA[t]}
        save(path, out, tl, server)
    out["phases"]["M2"] = m2

    def macro(t, side, name):
        f = m2["items"].get(t, {}).get("witness", {}).get(side, {}).get("fields") or {}
        return num(f.get(name))

    def missing_of(t, side):
        return (m2["items"].get(t, {}).get("witness", {}).get(side, {}).get("missing") or [])

    ap_c, ap_s = macro("Base.Apple", "client", "getCalories"), macro("Base.Apple", "server",
                                                                    "getCalories")
    ap_other = {n: {"client": macro("Base.Apple", "client", n),
                    "server": macro("Base.Apple", "server", n),
                    "vanilla": VANILLA["Base.Apple"][n],
                    "at_vanilla_client": close(macro("Base.Apple", "client", n),
                                               VANILLA["Base.Apple"][n])}
                for n in ("getCarbohydrates", "getLipids", "getProteins", "getHungChange")}
    if ap_c is None and ap_s is None:
        m2av = "unmeasured"
    elif (ap_c == 400.0 and ap_s == 400.0
          and all(v["at_vanilla_client"] for v in ap_other.values())):
        m2av = "as_predicted"
    else:
        m2av = "falsified"
    grade("M2a", "P2: Apple getCalories 400 on BOTH sides, every other macro at vanilla -- a full "
                 "restatement changes exactly what it restates differently",
          {"getCalories": {"client": ap_c, "server": ap_s}, "others": ap_other}, m2av,
          "a getCalories of 95 says the mod's block never applied; a macro off vanilla says a "
          "full restatement is not a clean substitution")

    or_c, or_s = macro("Base.Orange", "client", "getCalories"), macro("Base.Orange", "server",
                                                                     "getCalories")
    or_hc = {"client": macro("Base.Orange", "client", "getHungChange"),
             "server": macro("Base.Orange", "server", "getHungChange")}
    or_cb = {"client": macro("Base.Orange", "client", "getCarbohydrates"),
             "server": macro("Base.Orange", "server", "getCarbohydrates")}
    or_missing = {"client": missing_of("Base.Orange", "client"),
                  "server": missing_of("Base.Orange", "server")}
    zeroed = or_hc["client"] == 0 and or_cb["client"] == 0
    absent = ("getHungChange" in or_missing["client"] and
              "getCarbohydrates" in or_missing["client"])
    survived = close(or_hc["client"], -0.12) or close(or_cb["client"], 16.27)
    if or_c is None and not absent:
        m2bv, arm = "unmeasured", "no reading"
    elif survived:
        m2bv, arm = "falsified", "FIELD MERGE -- the vanilla keys the mod's block omits survived"
    elif zeroed:
        m2bv, arm = "as_predicted", ("arm A: Orange still instantiates as a Food and the dropped "
                                     "keys are back at their DEFAULTS (0)")
    elif absent:
        m2bv, arm = "as_predicted", ("arm B: the getters are MISSING, so Orange instantiated as a "
                                     "plain InventoryItem -- the reset took ItemType with it")
    else:
        m2bv, arm = "falsified", "neither arm: read the per-field table"
    grade("M2b", "P3: Orange getCalories 400, with the ResetExisting replacement showing in "
                 "EITHER readable form -- getHungChange and getCarbohydrates at 0 (arm A, still "
                 "a Food), or those two in the reply's `missing` set (arm B, a plain "
                 "InventoryItem). Both are the same finding: a WHOLESALE RESET",
          {"getCalories": {"client": or_c, "server": or_s},
           "getHungChange": or_hc, "getCarbohydrates": or_cb, "missing": or_missing,
           "vanilla": {"getHungChange": -0.12, "getCarbohydrates": 16.27, "getCalories": 65.0},
           "arm": arm}, m2bv,
          "-0.12 / 16.27 SURVIVING is a field merge and falsifies the reset reading outright")

    # ================= M3 -- R7, two mods redefining the same block =====================
    wm_spawn = spawn("Base.Watermelon", c, "M3: the load-order discriminator")
    wm = {"spawn": wm_spawn,
          "witness": both_fields(c, f"item {USER}/Base.Watermelon", MACROS, MACRO_COUNT,
                                 "Calories is 111 in TKX_ItemOverride and 777 in TKX_EatHook"),
          "server_item_get": step("m3_item_get", server, "item.get",
                                  f"{USER} Base.Watermelon")["ack"],
          "mods_order": list(MODS),
          "vanilla": VANILLA["Base.Watermelon"]}
    out["phases"]["M3"] = {"question": "when two mods redefine the same block, which wins?",
                           "watermelon": wm}
    wm_c = num((wm["witness"]["client"].get("fields") or {}).get("getCalories"))
    wm_s = num((wm["witness"]["server"].get("fields") or {}).get("getCalories"))
    if wm_c is None and wm_s is None:
        m3v = "unmeasured"
    elif wm_c == 777.0 and wm_s == 777.0:
        m3v = "as_predicted"
    else:
        m3v = "falsified"
    grade("M3", "P4: getCalories 777 -- the body of the mod LATER in Mods= is applied last "
                "(ScriptBucket.LoadScripts replays LoadData.scriptBodies in order)",
          {"getCalories": {"client": wm_c, "server": wm_s},
           "mods_order": list(MODS),
           "candidates": {"TKX_ItemOverride": 111.0, "TKX_EatHook": 777.0, "vanilla": 1355.0}},
          m3v, "111 means FIRST-wins and inverts the rule; 1355 means neither body applied")

    # ================= M4 -- R3, new items and the three translation states =============
    m4 = {"question": "which translation layout does 42.20.4 load, and are mod translations "
                      "consulted on a DEDICATED SERVER?",
          "items": {}, "text": {"client": {}, "server": {}}}
    for t in FIBRE_TYPES:
        sp = spawn(t, c, "M4: the display name is only readable off an instance")
        m4["items"][t] = {"spawn": sp,
                          "witness": both_fields(c, f"item {USER}/{t}", NAME_FIELDS, NAME_COUNT,
                                                 "getDisplayName == getFullType is the "
                                                 "UNTRANSLATED signature")}
        save(path, out, tl, server)
    for key, why in TEXT_KEYS:                     # CLIENT FIRST at every tag
        m4["text"]["client"][key] = {"why": why, "reply": probe(c, "text.get", key)}
        m4["text"]["server"][key] = {"why": why, "reply": probe(server, "text.get", key)}
    m4["grading_rule"] = (
        "amendment 12: a server-side text.get reply carrying `null = true` (or, without the "
        "slice-12 null guard, `text == \"nil\"`) is INCONCLUSIVE for the server half of question "
        "4, not a miss. The server-side display-name reading then rests on witness.fields "
        "getDisplayName, which is the brief's decision-point default.")
    out["phases"]["M4"] = m4

    def dn(t, side):
        """`translated` is None when the subject did not resolve -- an UNMEASURED read and a
        read of "not translated" are different answers, and collapsing them into False would
        grade a failed spawn as a falsifier."""
        w = m4["items"].get(t, {}).get("witness", {}).get(side, {})
        f = w.get("fields") or {}
        ok = bool(w.get("resolved")) and f.get("getDisplayName") is not None
        return {"getDisplayName": f.get("getDisplayName"), "getFullType": f.get("getFullType"),
                "getActualWeight": num(f.get("getActualWeight")),
                "getActualWeightUnmodded": num(f.get("getActualWeightUnmodded")),
                "resolved": w.get("resolved"),
                "translated": (f.get("getDisplayName") != f.get("getFullType")) if ok else None}

    def txt(side, key):
        r = m4["text"][side].get(key, {}).get("reply")
        if not isinstance(r, dict):
            return {"reply_shape": type(r).__name__, "raw": r}
        return {k: r.get(k) for k in ("text", "miss", "null", "error") if k in r}

    names = {t: {"client": dn(t, "client"), "server": dn(t, "server")} for t in FIBRE_TYPES}
    texts = {key: {"client": txt("client", key), "server": txt("server", key)}
             for key, _why in TEXT_KEYS}
    json_ok = names["TKX.FibreBarJson"]["client"]["translated"]
    named_ok = names["TKX.FibreBarNamed"]["client"]["translated"]
    plain_ok = names["TKX.FibreBar"]["client"]["translated"]
    if json_ok is None or named_ok is None or plain_ok is None:
        m4v = "unmeasured"
    elif json_ok and not named_ok and not plain_ok:
        m4v = "as_predicted"
    else:
        m4v = "falsified"
    grade("M4", "P5: Json resolves its name and keeps a non-zero getActualWeightUnmodded; Named "
                "(B41 .txt only) and the untranslated FibreBar read getDisplayName() == "
                "getFullType() and 0. That splits slice 09's hypotheses (ii) and (iii): a "
                "server-side hit on Json kills (iii), a miss on Named confirms (ii)",
          {"names": names, "text": texts,
           "json_translated": json_ok, "named_translated": named_ok,
           "plain_translated": plain_ok,
           "server_text_inconclusive": {k: bool(v["server"].get("null") or
                                                v["server"].get("error"))
                                        for k, v in texts.items()}},
          m4v,
          "a Named that resolves means the B41 .txt layout is still read on 42.20.4; a Json that "
          "misses means the .json layout is not, and hypothesis (iii) survives")

    # ================= M5 -- the two eating interception points =========================
    m5 = {"question": "where can a mod intercept eating in MP -- which sides does OnEat fire on, "
                      "and where does a Lua wrapper of ISEatFoodAction:complete fire?",
          "spawn": spawn(EAT_TYPE, c, "M5: RCON first -- eat.action's own findOrSpawn falls back "
                                      "to a CLIENT spawn, which trips a server "
                                      "SyncItemFields NPE")}
    if not m5["spawn"]["resolved"]:
        m5["skipped"] = ("the Banana never resolved client-side, so eat.action was NOT sent: it "
                         "would have client-spawned one and put an NPE in the server log.")
        note("M5 skipped -- RCON spawn never reached the client's inventory")
        eat_ack = None
    else:
        eat_ack = step("m5_eat_action", c, "eat.action", f"{EAT_TYPE} {EAT_FRACTION}")
        m5["eat_action"] = eat_ack["ack"]
        m5["queued_at_wall"] = eat_ack["wall_after"]
    m5["polls"] = []
    if eat_ack is not None:
        before = nutrition_pair("m5_post_queue", c)
        m5["post_queue"] = before
        # The baseline is the ack's OWN `before` block: `eat.action` snapshots the store inside
        # the same Lua call that queues the action (PZTestKit_Client.lua:428), so it is the one
        # reading that certainly predates the eat. The bus pair above is already a round trip
        # later and is kept as the client-side mirror at queue time, not as the baseline.
        ack_before = m5["eat_action"].get("before") if isinstance(m5["eat_action"], dict) else None
        base_cal = cal(ack_before) if isinstance(ack_before, dict) else None
        m5["baseline_calories"] = base_cal
        m5["baseline_source"] = ("eat.action ack `before.calories`" if base_cal is not None
                                 else "fell back to the post-queue bus pair")
        if base_cal is None:
            base_cal = before["server_calories"]
        for i in range(EAT_POLL_N):
            time.sleep(EAT_POLL_S)
            p = nutrition_pair(f"m5_poll_{i + 1}", c)
            moved = (p["server_calories"] is not None and base_cal is not None and
                     abs(p["server_calories"] - base_cal) > 1.0)
            m5["polls"].append({"i": i + 1, "wall": p["wall"], "moved": moved,
                               "server_calories": p["server_calories"],
                               "client_calories": p["client_calories"]})
            if moved:
                break
        m5["calories_moved"] = any(p["moved"] for p in m5["polls"])
        m5["measured_wait_s"] = round(wall() - eat_ack["wall_after"], 3)
    m5["globals"] = {"client": {}, "server": {}}
    for name, why in EAT_GLOBALS:                  # CLIENT FIRST at every tag
        m5["globals"]["client"][name] = {"why": why, "reply": probe(c, "lua.global", name)}
        m5["globals"]["server"][name] = {"why": why, "reply": probe(server, "lua.global", name)}
        save(path, out, tl, server)
    m5["moddata"] = {"client": probe(c, "witness.moddata", EAT_MODDATA),
                     "server": probe(server, "witness.moddata", EAT_MODDATA)}
    out["phases"]["M5"] = m5

    def gval(side, name):
        r = m5["globals"][side].get(name, {}).get("reply")
        if not isinstance(r, dict) or not r.get("resolved"):
            return None
        return r.get("value")

    calls = {s: gval(s, "TKX_EatHook.calls") for s in ("client", "server")}
    completes = {s: gval(s, "TKX_EatHook.completes") for s in ("client", "server")}
    orders = {s: gval(s, "TKX_EatHook.order") for s in ("client", "server")}
    wrapped = {s: gval(s, "TKX_EatHook.wrapped") for s in ("client", "server")}
    tkver = {s: gval(s, "TK.version") for s in ("client", "server")}
    if tkver["client"] != 1 or tkver["server"] != 1:
        note(f"TK.version control did not answer 1 on both sides: {tkver} -- the _G walk, not the "
             "mod globals, is what that impugns")
    cn, sn_ = num(calls["client"]), num(calls["server"])
    if cn is None and sn_ is None:
        m5av = "unmeasured"
    elif (cn or 0) >= 1 and (sn_ or 0) >= 1:
        m5av = "as_predicted"
    else:
        m5av = "falsified"
    grade("M5a", "P6: TKX_EatHook.calls >= 1 on BOTH sides -- the server's from Eat @762 L5811, "
                 "the client's from EatFoodPacket -> EatOnClient @0-@57 L5725-L5736, which "
                 "applies NO numbers",
          {"calls": calls, "lastSide": {s: gval(s, "TKX_EatHook.lastSide") for s in
                                        ("client", "server")},
           "lastFraction": {s: gval(s, "TKX_EatHook.lastFraction") for s in ("client", "server")},
           "lastCalories": {s: gval(s, "TKX_EatHook.lastCalories") for s in ("client", "server")},
           "moddata": {"client": (m5["moddata"]["client"] or {}).get("values"),
                       "server": (m5["moddata"]["server"] or {}).get("values")},
           "TK_version_control": tkver,
           "calories_moved": m5.get("calories_moved")},
          m5av,
          "calls == 0 on a side means OnEat never fired there; a client 0 with a server >= 1 "
          "would mean EatOnClient does not resolve the script's OnEat at all")
    cc, sc = num(completes["client"]), num(completes["server"])
    order_s = orders["server"] if isinstance(orders["server"], str) else ""
    if sc is None and cc is None:
        m5bv = "unmeasured"
    elif wrapped["server"] is False:
        m5bv = "unmeasured"
    elif (sc or 0) >= 1 and (cc or 0) == 0 and order_s.startswith("complete"):
        m5bv = "as_predicted"
    else:
        m5bv = "falsified"
    grade("M5b", "P7: completes >= 1 on the SERVER ONLY, and `order` begins \"complete\" -- the "
                 "Lua wrapper runs BEFORE IsoGameCharacter.Eat, which is why a mod that wants "
                 "the item intact has to sit there",
          {"completes": completes, "order": orders, "wrapped": wrapped,
           "wrapAt": {s: gval(s, "TKX_EatHook.wrapAt") for s in ("client", "server")},
           "lastComplete": {s: gval(s, "TKX_EatHook.lastComplete") for s in ("client", "server")},
           "disambiguation": "completes == 0 with wrapped == false is 'the wrapper never "
                             "installed on this side' -- a DIFFERENT finding from 'complete() "
                             "never ran there', and the reason `wrapped` is read at all."},
          m5bv,
          "a client completes >= 1 would overturn LuaTimedActionNew.complete @31 L162 (the Lua "
          "complete is skipped when GameClient.client); an order beginning \"onEat\" on the "
          "server would put the wrapper AFTER Eat")

    # ================= M6, part 2: the LATE census, then the SERVER -> client transmit ===
    while wall() - out["session_ready_wall"] < LAZY_WAIT:
        time.sleep(0.5)
    m6_late = census_pair("m6_late", c, f"past the server's lazy vanilla-fitness write "
                                        f"(>= {LAZY_WAIT} s since session_ready), and past "
                                        "M5, so the eat-hook's own modData keys are in the "
                                        "table the transmit below will send")
    m6_set = step("m6_arm_transmit", server, "moddata.set", f"{USER} {TRANSMIT_KEY} 1")
    time.sleep(TICK_WAIT)                                # >= 2 EveryOneMinute firings
    m6_after = census_pair("m6_after_server_transmit", c,
                           "after the mod's next EveryOneMinute tick cleared TKX_transmit_now and "
                           "called player:transmitModData() SERVER-side -- the direction this "
                           "library has never measured")
    out["phases"]["M6"] = {
        "question": "can a mod put a new nutrient field on PLAYER modData and have the client "
                    "see it -- in the server -> client direction?",
        "join": m6_join, "late": m6_late, "after_transmit": m6_after,
        "arm_step": {k: m6_set[k] for k in ("wall_before", "wall_after", "ack")},
        "measured_wait_s": round(m6_after["wall"] - m6_set["wall_after"], 3),
        "requested_wait_s": TICK_WAIT,
        "tick_note": f"EveryOneMinute fires every {GAME_MINUTE_S} s at DayLength {DAY_LENGTH} "
                     "with settimespeed 1; the wait covers at least two firings.",
    }
    srv_has = "TKX_fibre" in (m6_late["server"]["keyNames"] or [])
    cli_had = "TKX_fibre" in (m6_late["client"]["keyNames"] or [])
    cli_has = "TKX_fibre" in (m6_after["client"]["keyNames"] or [])
    # `identical` is the SECONDARY reading here and is deliberately NOT part of the verdict: the
    # mod's own client file writes `TKX_fibre_client` on EVERY EveryOneMinute tick, so whatever a
    # server -> client replace does to the client's table, that key is back within 3.75 s and the
    # census cannot be identical by the time the bus can read it. The difference set with the
    # mod's own re-writes taken out is the honest version of the same question.
    REWRITTEN_CLIENT_SIDE = {"TKX_fibre_client"}
    residual = sorted(set(m6_after["client_only"]) - REWRITTEN_CLIENT_SIDE)
    if m6_late["server"]["keyNames"] is None or m6_after["client"]["keyNames"] is None:
        m6v, m6arm = "unmeasured", "a census did not answer"
    elif not srv_has:
        m6v, m6arm = "unmeasured", ("the server never held TKX_fibre, so nothing about the "
                                    "transmit direction was exercised -- read TKX_Nutrient.ticks")
    elif cli_had:
        # P8's premise is that the key is server-side ONLY beforehand. If the client ALREADY has
        # it, some earlier route (the join handshake, or an earlier transmit) carried it, and the
        # transmit under test cannot be shown to have done anything: that is TRIVIAL, not
        # falsified, and it is itself the finding about how player modData first reaches a client.
        m6v, m6arm = "trivial", ("the client ALREADY held TKX_fibre before the transmit -- P8's "
                                 "premise (server-side only) does not hold on this build, and "
                                 "the route that carried it earlier is the finding")
    elif cli_has:
        m6v, m6arm = "as_predicted", "the client gained TKX_fibre only after the server transmit"
    else:
        m6v, m6arm = "falsified", "the client never gained TKX_fibre"
    grade("M6", "P8: TKX_fibre present SERVER-SIDE ONLY before the transmit; after the "
                "server-side transmitModData() the client's census GAINS it and becomes exactly "
                "the server's -- the untested direction of slice 10's wipe-and-replace",
          {"before": {"server_keys": m6_late["server"]["keyNames"],
                      "client_keys": m6_late["client"]["keyNames"],
                      "server_only": m6_late["server_only"],
                      "client_only": m6_late["client_only"],
                      "TKX_fibre_server": srv_has, "TKX_fibre_client": cli_had},
           "after": {"server_keys": m6_after["server"]["keyNames"],
                     "client_keys": m6_after["client"]["keyNames"],
                     "server_only": m6_after["server_only"],
                     "client_only": m6_after["client_only"],
                     "TKX_fibre_client": cli_has, "identical": m6_after["identical"]},
           "arm": m6arm,
           "join": {"server_keys": m6_join["server"]["keyNames"],
                    "client_keys": m6_join["client"]["keyNames"],
                    "client_since_ready": m6_join["client"]["since_session_ready"],
                    "server_since_ready": m6_join["server"]["since_session_ready"]},
           "client_only_after_less_rewrites": residual,
           "replacement_reading": ("the client's table is the server's once the keys the CLIENT's "
                                   "own mod rewrites every tick are set aside; "
                                   f"{sorted(REWRITTEN_CLIENT_SIDE)} is that set, and a non-empty "
                                   "`client_only_after_less_rewrites` is what would say the "
                                   "receiver MERGES. `identical` is reported but NOT graded, for "
                                   "the same reason."),
           "graded_on": "the client gaining TKX_fibre; `identical` is secondary"},
          m6v,
          "a client that still lacks TKX_fibre after the transmit says the server -> client "
          "direction does not carry modData at all; a client that gains it while KEEPING keys "
          "the server never had says the receiver MERGES rather than wipes-and-replaces")

    # ================= M7 -- the same field, ITEM scope, through syncItemFields() ========
    ch = spawn(ITEM_TYPE, c, "M7: the mod writes item modData + syncItemFields() once per "
                             "instance, on its next EveryOneMinute tick")
    m7_before = census_pair("m7_item_before", c,
                            "the ITEM census, taken as early after the spawn as the bus allows; "
                            "the mod's write lands on its next tick, so a TKX_fibre here means "
                            "the tick beat the read -- which the wall stamps say",
                            scope=ITEM_SCOPE, vanilla=VANILLA_ITEM_KEYS)
    time.sleep(TICK_WAIT)
    m7_after = census_pair("m7_item_after", c, "after >= 2 EveryOneMinute firings",
                           scope=ITEM_SCOPE, vanilla=VANILLA_ITEM_KEYS)
    m7_globals = {"client": {}, "server": {}}
    for name in NUTRIENT_GLOBALS:
        m7_globals["client"][name] = probe(c, "lua.global", name)
        m7_globals["server"][name] = probe(server, "lua.global", name)
    out["phases"]["M7"] = {
        "question": "does a custom item-modData field reach the client through syncItemFields()?",
        "spawn": ch, "before": m7_before, "after": m7_after,
        "mod_globals": m7_globals,
        "measured_wait_s": round(m7_after["wall"] - m7_before["wall"], 3),
        "exclusion_set": sorted(VANILLA_ITEM_KEYS),
        "exclusion_note": "the ITEM exclusion set is applied HERE and nowhere else; the player "
                          "censuses use the five vanilla player keys instead. `customName` is a "
                          "deserialization side effect of InventoryItem.setCustomName, not mod "
                          "data (exp08-20260910-152944).",
    }
    it_s = "TKX_fibre" in (m7_after["server"]["keyNames"] or [])
    it_c = "TKX_fibre" in (m7_after["client"]["keyNames"] or [])
    writes = (m7_globals["server"].get("TKX_Nutrient.itemWrites") or {})
    writes_n = num(writes.get("value")) if isinstance(writes, dict) else None
    if m7_after["server"]["keyNames"] is None:
        m7v = "unmeasured"
    elif not it_s:
        m7v = "unmeasured"          # the mod never wrote it: nothing about SYNC was tested
    elif it_c:
        m7v = "as_predicted"
    else:
        m7v = "falsified"
    grade("M7", "P9: TKX_fibre reaches the client through syncItemFields() "
                "(SyncItemFieldsPacket.processModData wipes and replaces)",
          {"server_keys": m7_after["server"]["keyNames"],
           "client_keys": m7_after["client"]["keyNames"],
           "before_server": m7_before["server"]["keyNames"],
           "before_client": m7_before["client"]["keyNames"],
           "TKX_fibre_server": it_s, "TKX_fibre_client": it_c,
           "server_values": (m7_after["server_raw"] or {}).get("values"),
           "itemWrites_server": writes_n,
           "consequence": "if it does not reach the client, per-item custom nutrients are a "
                          "CANNOT for slice 13."},
          m7v,
          "TKX_fibre on the server and NOT on the client falsifies P9. TKX_fibre on NEITHER side "
          "is unmeasured, not falsified: the mod's own write did not happen (read itemWrites)")

    # ================= M8 -- the weight-direction flags on a NON-TRIVIAL arm =============
    m8_base = nutrition_pair("m8_baseline", c)
    baseline_cal = m8_base["server_calories"]
    out["m8"]["baseline_calories"] = baseline_cal
    m8 = {"question": "do the weight-direction flags agree across sides under a NON-TRIVIAL arm?",
          "cadence": M8_CADENCE, "wait_s": M8_WAIT_S, "baseline": m8_base,
          "baseline_calories": baseline_cal, "arms": []}
    for label, value in (("incWeight", M8_HIGH), ("decWeight", M8_LOW)):
        s = step(f"m8_set_{label}", server, "nutrition.set", f"{USER} calories {value}")
        time.sleep(M8_WAIT_S)
        r = nutrition_pair(f"m8_{label}", c)
        m8["arms"].append({
            "arm": label, "wrote": value, "set_ack": s["ack"],
            "requested_wait_s": M8_WAIT_S,
            "measured_wait_s": round(r["wall"] - s["wall_after"], 3),
            "reading": r,
            "server_flags": r["server_flags"], "client_flags": r["client_flags"],
            "flags_agree": r["flags_agree"],
            "server_calories": r["server_calories"], "client_calories": r["client_calories"],
            "wrote_float": float(value),
            "delta_from_write": (None if r["server_calories"] is None
                                 else round(r["server_calories"] - float(value), 3)),
            # "the store ended up materially ABOVE what was written" -- which covers a clamp at
            # 0 and an overwrite alike, and does NOT mistake the few kcal `updateCalories` burns
            # during the wait for either. A clamp would land near 0 from a -100 write, i.e. ~+100
            # above it; the passive burn over 8 s is far under 50.
            "clamped": (r["server_calories"] is not None and
                        r["server_calories"] - float(value) > 50.0)})
        save(path, out, tl, server)
    m8["threshold_model"] = ("at weight 80 the gain threshold is 1000 + (80-80)*40 = 1000 and the "
                             "loss threshold 0, so 1500 takes the incWeight arm and -100 the "
                             "decWeight arm -- unless the store clamps at 0 on the negative "
                             "write, which is itself the reading.")
    out["phases"]["M8"] = m8
    inc, dec = m8["arms"][0], m8["arms"][1]
    # An EMPTY flag map is unmeasured, not "all false": the three keys are emitted only when the
    # build exposes the members (TK.nutritionSnapshot's optional-read idiom), so `{}` means the
    # read never happened and `{"incWeight": false, ...}` is a reading.
    if not inc["server_flags"] or not dec["server_flags"]:
        m8v = "unmeasured"
    elif not (inc["flags_agree"] and dec["flags_agree"]):
        m8v = "falsified"
    elif inc["server_flags"].get("incWeight") and dec["server_flags"].get("decWeight"):
        m8v = "as_predicted"
    elif dec["clamped"]:
        m8v = "trivial"            # the negative write never reached the decWeight arm
    else:
        m8v = "falsified"
    grade("M8", "P10: at weight 80 the gain threshold is 1000, so 1500 takes the incWeight arm "
                "and -100 the decWeight arm; both sides should AGREE if the client recomputes "
                "the flags (updateWeight's flag half sits ahead of the GameClient.client skip at "
                "@317-@320 L198)",
          {"incWeight_arm": {k: inc[k] for k in ("wrote", "server_flags", "client_flags",
                                                 "flags_agree", "server_calories",
                                                 "client_calories", "measured_wait_s")},
           "decWeight_arm": {k: dec[k] for k in ("wrote", "server_flags", "client_flags",
                                                 "flags_agree", "server_calories",
                                                 "client_calories", "measured_wait_s",
                                                 "clamped")},
           "weight": {"server": m8_base["server_weight"], "client": m8_base["client_weight"]},
           "cadence": M8_CADENCE, "wait_s": M8_WAIT_S},
          m8v,
          "a disagreement on either arm falsifies the slice-10 flag-mirroring finding under a "
          "non-trivial arm -- which is exactly what slice 11 could not test. A clamp at 0 on the "
          "negative write makes the decWeight half TRIVIAL, and that is the reading, not a retry")

    # ================= M9 -- the transmit WIPE half =====================================
    # M6 has already run, so the client's table IS the server's: that is what makes the loss of a
    # freshly planted server-only key readable as a WIPE rather than as "it was never there".
    m9_set = step("m9_plant_server_only", server, "moddata.set",
                  f"{USER} {SERVER_ONLY_KEY} {SERVER_ONLY_VALUE}")
    m9_before = census_pair("m9_before", c, f"{SERVER_ONLY_KEY} planted SERVER-side, BEFORE any "
                                            "client transmit -- a key the client's copy has "
                                            "never held")
    m9_action = step("m9_client_transmit", c, "moddata.transmit", "")
    m9_after = census_pair("m9_after", c, "immediately after the CLIENT's transmitModData(); read "
                                          "fast, because the mod's own EveryOneMinute tick "
                                          "re-writes TKX_fibre server-side every "
                                          f"{GAME_MINUTE_S} s and would mask a wipe of THAT key "
                                          f"(never of {SERVER_ONLY_KEY}, which nothing rewrites)")
    out["phases"]["M9"] = {
        "question": "does the receiver of a transmitModData() WIPE before it rawsets?",
        "transmit_wipe": {
            "before": {"client": m9_before["client"], "server": m9_before["server"]},
            "after": {"client": m9_after["client"], "server": m9_after["server"]},
        },
        "plant_step": {k: m9_set[k] for k in ("wall_before", "wall_after", "ack")},
        "transmit_step": {k: m9_action[k] for k in ("wall_before", "wall_after", "ack")},
        "measured_wait_s": round(m9_after["wall"] - m9_action["wall_after"], 3),
        "masking_note": "only TKX_ServerOnly is an unambiguous reading here: the mod rewrites "
                        "TKX_fibre server-side on every tick, so its presence after the transmit "
                        "cannot distinguish 'never wiped' from 'wiped and rewritten'.",
    }
    planted = SERVER_ONLY_KEY in (m9_before["server"]["keyNames"] or [])
    still = SERVER_ONLY_KEY in (m9_after["server"]["keyNames"] or [])
    if not planted or m9_after["server"]["keyNames"] is None:
        m9v = "unmeasured"
    elif not still:
        m9v = "as_predicted"
    else:
        m9v = "falsified"
    grade("M9", "P11: the server's census has LOST TKX_ServerOnly after the client's transmit -- "
                "KahluaTableImpl.load @5-@6 L333 wipes before it rawsets, so the receiver keeps "
                "only what the sender sent. Pass 3 corroborated wipe-and-REPLACE only; the wipe "
                "half rested on a single pass-2 reading and this takes it to n = 2",
          {"planted_server_side": planted,
           "present_after_client_transmit": still,
           "server_before": m9_before["server"]["keyNames"],
           "server_after": m9_after["server"]["keyNames"],
           "client_before": m9_before["client"]["keyNames"],
           "client_after": m9_after["client"]["keyNames"],
           "server_only_after": m9_after["server_only"],
           "client_only_after": m9_after["client_only"]},
          m9v,
          f"{SERVER_ONLY_KEY} still present server-side falsifies it and says the receiver MERGES")

    # ================= world-state restoration, inside the try ==========================
    if baseline_cal is not None:
        r = step("restore_calories", server, "nutrition.set",
                 f"{USER} calories {baseline_cal}")
        check = nutrition_pair("restored", c)
        out["m8"]["restore"] = {"wrote": baseline_cal, "ack": r["ack"],
                                "read_back_server": check["server_calories"],
                                "read_back_client": check["client_calories"],
                                "ok": close(check["server_calories"], baseline_cal, 1e-2)}
    else:
        out["m8"]["restore"] = {"skipped": "no baseline calorie reading to restore to"}
        note("M8 calorie baseline unreadable -- nothing restored; the store is left where the "
             "arms put it and that is recorded rather than papered over")

    # ================= the readings, stated as verdicts ================================
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "field_count_ok": all(x["count_ok"] for x in FIELD_CHECKS) if FIELD_CHECKS else None,
        "field_checks": len(FIELD_CHECKS),
        "field_count_failures": [x for x in FIELD_CHECKS if not x["count_ok"]],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "M1_foodByModule": by_module,
        "M2a_apple_calories": {"client": ap_c, "server": ap_s},
        "M2b_orange": {"calories": {"client": or_c, "server": or_s},
                       "getHungChange": or_hc, "getCarbohydrates": or_cb, "arm": arm},
        "M3_watermelon_calories": {"client": wm_c, "server": wm_s},
        "M4_translated": {"Json": json_ok, "Named": named_ok, "FibreBar": plain_ok},
        "M4_server_text": {k: v["server"] for k, v in texts.items()},
        "M5_calls": calls, "M5_completes": completes, "M5_order": orders,
        "M6_client_gained_fibre": cli_has,
        "M7_item_fibre": {"server": it_s, "client": it_c},
        "M8_flags": {"inc": {"server": inc["server_flags"], "client": inc["client_flags"]},
                     "dec": {"server": dec["server_flags"], "client": dec["client_flags"]}},
        "M9_server_only_survived": still,
        "lua_error_hits": {"client": out["greps"]["lua_errors"]["client"]["count"],
                           "server": out["greps"]["lua_errors"]["server"]["count"]},
        "overrides_lines": {"client": out["greps"]["overrides"]["client"]["count"],
                            "server": out["greps"]["overrides"]["server"]["count"]},
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
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-overrides.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
