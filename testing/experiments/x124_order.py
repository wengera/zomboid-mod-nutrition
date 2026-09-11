"""Slice 12, session 4 (`x124`): in what ORDER are script bodies replayed? -- LIVE.

**This session exists because session 1 falsified its own prediction and left exactly one
hypothesis standing.** `x121-20260911-030023` measured two things about a redefined `item` block:

  * a partial block MERGES per key -- the narrowed `item Orange` kept vanilla's `hungChange`
    -0.12 and `carbohydrates` 16.27 beside the mod's `Calories 400` (M2b, `falsified`); and
  * `Base.Watermelon` read **111**, the body of `TKX_ItemOverride`, which was **FIRST** of the
    three mods in `Mods=` -- not **777**, the body of `TKX_EatHook`, which was **LAST** (M3,
    `falsified`).

Per-key LAST-wins is not in doubt: vanilla's body is first in every conceivable order and its
`Calories 95` lost to the mod's 400 on Apple. So what 111 falsifies is not "last wins" but
"`Mods=` position is what LAST means". `TKX_EatHook` < `TKX_ItemOverride` in ASCII, so the mod
whose body ran last is also the mod whose id sorts last -- and with only ONE collision pair in
the session, "alphabetical by id" and "`Mods=` order" could not be told apart, because the two
rules happened to disagree in the one direction the pair could not resolve.

**The separator.** `TKX_ZWatermelon` (built for this session, Task 6b Step 1) ships mod C's
Watermelon block byte for byte apart from `Calories = 999.0`, and the profile `x12-order` places
it **FIRST of the three in `Mods=`** while its id sorts **LAST of the three alphabetically**. The
two rules now predict different numbers, and one read separates them:

  | `getCalories` | which mod's body ran last | what it means |
  |---|---|---|
  | **999** | `TKX_ZWatermelon` (`Mods=` first, id last)  | replay is ALPHABETICAL BY ID; `Mods=` position is irrelevant to the body order |
  | **777** | `TKX_EatHook` (`Mods=` last, id middle)     | replay IS `Mods=` order after all -- and session 1's 111 becomes unexplained |
  | **111** | `TKX_ItemOverride` (`Mods=` middle, id first) | NEITHER rule; the next discriminator is named in the artifact |
  | **1355** | none -- vanilla survived | no mod body applied at all; every reading above is void |

Question 7 of the slice-12 plan ("when two mods redefine the same block, which wins?") is
settled by this one number, whichever way it falls.

Five readings, none of which needs the others to be interpretable:

  O1  the discriminator itself -- RCON-spawn a `Base.Watermelon`, poll until the CLIENT sees it,
      then read the five macro getters off the instance client-side and `item.get` server-side.
      The instance is the only route: `TK.SCRIPT_GETTERS` comes back with all four nutrition keys
      ABSENT on a SCRIPT object (Kahlua does not expose them -- measured slice 01, re-confirmed in
      `td1-20260910-192457` and again in `x121` M1), so `item.script` cannot answer this.
  O2  the server log's own account of the replay -- every line naming one of the three script
      FILES, and every line naming `Watermelon`, with line numbers, because ORDER is the evidence
      and order is unreadable without them. The engine may print no script paths at all; that is
      recorded as an empty list and graded `trivial`, never re-run into something prettier.
      **Not to be confused with the loader's `loading <id>` lines**, which `x121` already measured
      at server lines 94 / 97 / 99 in `Mods=` order and which this run reproduces at 94 / 96 / 99.
      Those say when a mod was LOADED; O2 asks when its BODY was REPLAYED, and the whole session
      is the claim that those two orders differ.
  O3  the census control -- `foodByModule.Base` must still be 722. Three redefinitions of one
      existing type add no item, and a number other than 722 means the run is not measuring what
      the table above assumes it is measuring.
  O4  the harness control -- `lua.global TK.version` == 1 on BOTH sides. A `resolved: false` here
      means the `_G` walk is broken and every `lua.global` reading in the file is suspect, not
      that some mod global is absent.
  O5  the re-ask of `text.get`, in the BARE B42 key form (controller addition after the Task 4
      review). `x121` M4 asked only `ItemName_<fullType>`, the B41 prefixed form, and all four
      keys missed on both sides -- which cannot distinguish "mod translations never reach a
      dedicated server" from "42.20.4's table is not keyed that way at all". B42's
      `Translator`/`ItemName.json` layout is keyed by the BARE fullType, so this asks
      `Base.Apple`, `TKX.FibreBarJson` and `TKX.FibreBarNamed` directly, with the two prefixed
      keys kept beside them as the controls that make the comparison a comparison.

**The one thing this session must not do is take the 999 for granted.** Session 1's M3 predicted
777 with the same confidence and was wrong, which is the only reason this file exists.

`lua.reload` is NEVER sent, for the reason `x121` gives: mod C's `ISEatFoodAction:complete`
wrapper is sentinel-guarded and idempotent, but reloading the file re-executes VANILLA's
`ISEatFoodAction` definition underneath a live wrapper, and that is not a state any reading here
should be taken in. Nothing here eats, so no wrapper is exercised either way.

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

PROFILE = "x12-order"
USER = "admin"
# `Mods=` order IS this tuple's order (profile.mods -> the ini's Mods= line). The alphabetical
# order of the same three is EatHook < ItemOverride < ZWatermelon, which is what makes the
# profile a separator rather than a repeat of session 1.
MODS = ("PZTestKit", "TKX_ZWatermelon", "TKX_ItemOverride", "TKX_EatHook")
TKX_MODS = ("TKX_ZWatermelon", "TKX_ItemOverride", "TKX_EatHook")
# Step 3's acceptance run: RESULT PASS, both [[verify]] rows ok=True, 0 server error lines, and
# `loading TKX_ZWatermelon` / `TKX_ItemOverride` / `TKX_EatHook` at server lines 94 / 96 / 99 --
# i.e. the loader walked `Mods=` order, which is the order O2 expects the BODIES not to follow.
ACCEPTANCE_RUN = "run-20260911-035203"

# ---- timings -----------------------------------------------------------------------------------
DAY_LENGTH = 4           # the fixture's own (testing/fixtures/default/.../pzt_SandboxVars.lua:53)
GAME_MINUTE_S = 3.75     # DayLength 4 = a 90-minute game day: 5400 s / 1440 game minutes
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory (s01/s02/s05)
SPAWN_TRIES = 4

# ---- O1 ----------------------------------------------------------------------------------------
SUBJECT = "Base.Watermelon"
# Zero-argument getters only, comma-joined and whitespace-free (`witness.fields` grammar). An
# arity mismatch is as uncatchable in Kahlua as a nil call.
MACROS = "getCalories,getCarbohydrates,getLipids,getProteins,getHungChange"
MACRO_COUNT = 5
# Every number that can come back, and what each one MEANS, stated before the run. The four
# non-Calories macros are IDENTICAL in all three mod bodies and in vanilla, so they are the
# integrity check on the read, not a second discriminator: a Carbohydrates that is not 341.11
# says the instance is not the item this table is about.
CANDIDATES = {
    999.0: {"mod": "TKX_ZWatermelon", "mods_position": 1, "alpha_position": 3,
            "means": "replay is ALPHABETICAL BY ID with per-key last-wins; Mods= position is "
                     "irrelevant to which body lands last"},
    777.0: {"mod": "TKX_EatHook", "mods_position": 3, "alpha_position": 1,
            "means": "replay IS Mods= order with last-wins -- which REOPENS session 1's M3, "
                     "whose 111 that rule cannot explain"},
    111.0: {"mod": "TKX_ItemOverride", "mods_position": 2, "alpha_position": 2,
            "means": "NEITHER rule. Middle in both orderings, so no ordering over these three "
                     "ids puts it last"},
    1355.0: {"mod": "vanilla", "mods_position": 0, "alpha_position": 0,
             "means": "no mod body applied at all -- the session measured nothing about order"},
}
# The four keys every body agrees on (mod A's, mod C's and mod F's Watermelon blocks are byte
# for byte the vanilla block apart from Calories). Read as the integrity check described above.
INVARIANT = {"getCarbohydrates": 341.11, "getLipids": 6.78, "getProteins": 27.56,
             "getHungChange": -0.6}
# `getHungChange()` is the SCRIPT's HungerChange / 100 (Item.InstanceItem), so -60.0 reads -0.6.
NEXT_DISCRIMINATOR = (
    "if 111: no ordering over the three IDS puts TKX_ItemOverride last (it is middle in both), "
    "so the rule keys on something that is neither the id nor the Mods= slot. The next "
    "discriminator swaps the FOLDER name: install mod F under a folder that sorts FIRST while "
    "its mod.info id still sorts last (session 3 proved the loader resolves through mod.info, "
    "so the mod still loads under the drifted folder -- `x123-20260911-034426`, P16 "
    "as_predicted). If the winner follows the folder name, the replay order is a directory walk "
    "of <cachedir>/mods and the id was never the key; if it still follows the id, neither, and "
    "the remaining candidate is the media-file PATH (`tkx_eat_hook.txt` < `tkx_item_override.txt` "
    "< `tkx_zwatermelon.txt`, which is the same order as the ids here and is therefore NOT "
    "separated by this session either -- name it as still-confounded rather than excluded)."
)

# ---- O2: the three script FILES, and the subject's name. Case-insensitive because a log may
# print either the on-disk casing or a normalised one, and which it prints is not the question.
SCRIPT_FILE_RX = re.compile(r"tkx_zwatermelon|tkx_item_override|tkx_eat_hook", re.I)
WATERMELON_RX = re.compile(r"watermelon", re.I)
LOADING_RX = re.compile(r"loading TKX_")
NILCALL_RX = re.compile(r"tried to call nil|stack traceback|attempted to index")
# A limit is a BREAK, not a window: a result of exactly `limit` means SATURATION (amendment 6).
# The acceptance run printed 3 `loading TKX_` lines server-side and 6 client-side (two Lua states),
# so LOADING_LIMIT is 2x + headroom. SCRIPT_FILE and WATERMELON are OPEN reads -- nothing predicts
# their count -- so they are sized generously and their saturation flag is part of the reading.
SCRIPT_FILE_LIMIT, WATERMELON_LIMIT, LOADING_LIMIT, NILCALL_LIMIT = 60, 60, 16, 12

# ---- O3 ----------------------------------------------------------------------------------------
# testing/artifacts/exp05-20260910-084109/food-scan.json:350 -- `foodByModule.Base`. NOT 1005,
# which is that dataset's total item RECORDS; the live census's own `total` is the comparable one.
BASE_FOOD_BASELINE = 722
TKX_FOOD_EXPECTED = 3          # TKX.FibreBar / FibreBarNamed / FibreBarJson, all from mod A

# ---- O4 ----------------------------------------------------------------------------------------
CONTROL_GLOBAL = "TK.version"

# ---- O5: the bare B42 key form, plus the prefixed B41 controls -----------------------------
# Session 1 asked ONLY the prefixed form and every one of the four missed on both sides, which is
# consistent with two very different worlds (mod translations absent server-side / the table not
# keyed that way at all). The bare keys are what B42's ItemName.json actually declares.
TEXT_KEYS = (
    ("Base.Apple", "bare, VANILLA: the key B42's own ItemName.json declares. A hit here is what "
                   "makes every miss below readable as a miss rather than as a dead command"),
    ("TKX.FibreBarJson", "bare, MOD, B42 ItemName.json layout -- slice 09's hypothesis (iii) "
                         "asked in the key form B42 actually uses"),
    ("TKX.FibreBarNamed", "bare, MOD, B41 ItemName_EN.txt layout -- (ii): declared only in the "
                          "legacy .txt, so a hit says the .txt is still read on 42.20.4"),
    ("ItemName_Base.Apple", "PREFIXED control: session 1 read this as miss on both sides. It "
                            "must miss again, or the two sessions disagree about the same key"),
    ("ItemName_TKX.FibreBarJson", "PREFIXED control, same role for the mod half"),
)
# What session 1 measured for the two prefixed keys, so this run's reply is compared against a
# recorded number and not against a memory (`x121-20260911-030023`, summary.M4_server_text).
X121_PREFIXED = {"ItemName_Base.Apple": {"text": "ItemName_Base.Apple", "miss": True},
                 "ItemName_TKX.FibreBarJson": {"text": "ItemName_TKX.FibreBarJson", "miss": True}}

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"

# Per-SCOPE modData exclusion sets (pass-1 precedent, docs/decisions.md:133), carried for shape
# parity with the sessions that take a census. THIS session takes NONE -- O1-O5 read script data,
# log files and the translation table, and not one of them touches modData -- so the sets are
# recorded in the artifact as inapplicable rather than silently omitted, which would leave a
# reader of the series wondering which census this file forgot.
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}
VANILLA_ITEM_KEYS = {"customName", "Tooltip"}

# The dormant `sent` branch's routing table, widened per the slice-11 driver note. Anything NOT
# in here is recorded raw rather than waited on.
RESULT_DOC = {"witness.fields": "witness_fields", "witness.moddata": "witness_moddata"}

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x124")
path = os.path.join(run_dir, "platform-order.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": "x124 -- slice 12 session 4: which mod's script body is applied last",
    "user": USER,
    "profile": prof.report(),
    "mods": list(MODS),
    "mods_order_note": "Mods= order is this list's order. The ALPHABETICAL order of the three "
                       "TKX ids is TKX_EatHook < TKX_ItemOverride < TKX_ZWatermelon, i.e. the "
                       "EXACT REVERSE of their Mods= positions -- which is the whole design.",
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "fixture_day_length": DAY_LENGTH,
    "game_minute_seconds": GAME_MINUTE_S,
    "scope_exclusions": {
        "player": sorted(VANILLA_PLAYER_KEYS), "item": sorted(VANILLA_ITEM_KEYS),
        "applies_here": False,
        "why": "no modData census is taken this session -- O1-O5 read script data, log files and "
               "the translation table. The sets are recorded so a reader of the series can see "
               "they were considered and found inapplicable, not omitted.",
    },
    "field_counts_expected": {"macros": MACRO_COUNT},
    "candidates": {str(int(k)): v for k, v in CANDIDATES.items()},
    "prior": {
        "x121_run": "x121-20260911-030023",
        "x121_M3": "getCalories 111 on both sides, verdict falsified -- the mod FIRST in Mods= "
                   "won, not the one last in it",
        "x121_M2b": "verdict falsified -- a partial block MERGES per key, so per-key LAST-wins "
                    "is established independently (vanilla's Apple 95 lost to the mod's 400)",
        "x121_loading_lines": "server 94/97/99 in Mods= order; the loader walks Mods=. O2 asks "
                              "about the BODY replay, which is the order this session claims "
                              "differs.",
        "x123_run": "x123-20260911-034426 -- P16 as_predicted, the loader resolves a mod through "
                    "mod.info and not through the folder name. That is what makes the "
                    "folder-name swap a usable next discriminator if this session reads 111.",
    },
    "world_changes": {
        "restored": "nothing needs restoring -- this session writes no state. No nutrition.set, "
                    "no moddata.set, no item.set, no eat.action.",
        "left_in_place": ["one RCON-spawned Base.Watermelon in admin's inventory"],
        "why": "the spawned item lives in THIS run's copy of the fixture (run_dir), never in the "
               "golden one, so it is discarded with the run directory.",
        "lua_reload": "never sent -- re-executing vanilla's ISEatFoodAction underneath mod C's "
                      "live wrapper is not a state any reading here should be taken in.",
    },
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
    `serverWorldAge` / `gameMinute` lifted out where the reply carries them."""
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


FIELD_CHECKS = []


def field_read(side, side_name, subject, names, count, why=""):
    """One `witness.fields` read with its `count` CHECKED against the expected name count on every
    reply (amendment 7), not merely recorded. The reconciliation is against the names SENT, which
    is what the README's own warning asks for."""
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
    """CLIENT FIRST, then the server -- the read order is what fixes the sign of any cross-side
    comparison, so it is never left to chance."""
    return {"client": field_read(c, "client", subject, names, count, why),
            "server": field_read(server, "server", subject, names, count, why)}


def grep_numbered(path_, rx, limit):
    """`session.grep_file` with the LINE NUMBER kept: which lines arrived, and in what order, is
    the evidence here, and order is unreadable without the numbers."""
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

    RCON and not a client-side `AddItem`: a client spawn is invisible to the server (spike S6),
    and the SERVER half of O1 reads the same instance out of the same inventory, so a spawn the
    server cannot see would answer a different question on each side."""
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


def close(a, b, tol=1.3e-4):
    """float32 band, the slice-08 tolerance: the bus renders with `tostring`, and a script value
    round-trips through a float, so 341.11 reads 341.10998. Never an equality test."""
    if a is None or b is None:
        return None
    return abs(a - b) <= tol * max(1.0, abs(b))


def which_body(v):
    """The candidate row a measured `getCalories` lands on, matched in the float32 band rather
    than by equality -- 999.0 arrives through `tostring` on a float and 111 already arrived as
    the integer 111 in session 1, so neither `== 999.0` nor `is int` is safe."""
    if v is None:
        return None
    for k, row in CANDIDATES.items():
        if close(v, k):
            return dict(row, calories=k)
    return None


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
    # Slice-11 driver note 1: a NEGATIVE the run establishes belongs in the artifact.
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(c.mods_not_found))}

    # ---- the tier-(c) gate on mod F. `TKX_ZWatermelon` ships no Lua and no item of its own, so
    # no [[verify]] row can distinguish "it loaded" from "vanilla answered" -- the profile says so
    # in a comment and this is where the claim is actually discharged: the folder reached
    # <cachedir>/mods, the game reported no missing mod on either side, and the loader printed
    # `loading TKX_ZWatermelon`. All three, together, are the gate.
    mods_dir = os.path.join(server.cache, "mods")
    try:
        listing = sorted(os.listdir(mods_dir))
    except OSError as e:                          # noqa: BLE001 - recorded, not raised
        listing = [f"error: {type(e).__name__}: {e}"]
    out["greps"] = {k: greps(k, rx, lim, c) for k, rx, lim in (
        ("loading", LOADING_RX, LOADING_LIMIT),
        ("script_files", SCRIPT_FILE_RX, SCRIPT_FILE_LIMIT),
        ("watermelon", WATERMELON_RX, WATERMELON_LIMIT),
        ("lua_errors", NILCALL_RX, NILCALL_LIMIT))}
    loading_ids = [h["text"].split("loading ")[-1].strip()
                   for h in out["greps"]["loading"]["server"]["hits"] if "loading " in h["text"]]
    out["f_tier_c"] = {
        "why": "TKX_ZWatermelon is UNGATED in the profile on purpose: it ships no Lua (nothing "
               "for lua.global) and no new item (nothing for item.script), and the obvious row "
               "`item.script Base.Watermelon` passes with the mod absent because vanilla defines "
               "Watermelon. Tier (c) is folder + mods_not_found + the loader's own line.",
        "mods_dir": os.path.relpath(mods_dir, REPO),
        "listing": listing,
        "folder_present": "TKX_ZWatermelon" in listing,
        "mods_not_found_empty": (not out["mods_not_found"]["server"]
                                 and not out["mods_not_found"]["client"]),
        "loading_line_present": any("TKX_ZWatermelon" in h["text"]
                                    for h in out["greps"]["loading"]["server"]["hits"]),
        "loading_ids_server_in_order": loading_ids,
        "loading_matches_mods_order": loading_ids == [m for m in MODS if m in loading_ids],
    }
    out["f_tier_c"]["ok"] = bool(out["f_tier_c"]["folder_present"]
                                 and out["f_tier_c"]["mods_not_found_empty"]
                                 and out["f_tier_c"]["loading_line_present"])
    tl.mark("tier_c", ok=str(out["f_tier_c"]["ok"]))
    if not out["f_tier_c"]["ok"]:
        note("mod F's tier-(c) gate did NOT hold -- every reading below is about a world that "
             "may not contain TKX_ZWatermelon, and P18 must be read as unmeasured whatever "
             "number comes back.")
    save(path, out, tl, server)

    # ================= O1 -- the discriminator ==========================================
    sp = spawn(SUBJECT, c, "O1: the macros live on the INSTANCE -- Kahlua does not expose them "
                           "on the script object, so item.script cannot answer this")
    o1 = {"question": "with mod F FIRST in Mods= and LAST alphabetically, whose Watermelon body "
                      "is applied last?",
          "spawn": sp,
          "witness": both_fields(c, f"item {USER}/{SUBJECT}", MACROS, MACRO_COUNT,
                                 "Calories: 999 in TKX_ZWatermelon, 111 in TKX_ItemOverride, "
                                 "777 in TKX_EatHook, 1355 in vanilla"),
          "server_item_get": step("o1_item_get", server, "item.get",
                                  f"{USER} {SUBJECT}")["ack"],
          "mods_order": list(MODS),
          "alphabetical_order": sorted(TKX_MODS),
          "candidates": {str(int(k)): v for k, v in CANDIDATES.items()}}
    out["phases"]["O1"] = o1

    cal_c = num((o1["witness"]["client"].get("fields") or {}).get("getCalories"))
    srv_get = o1["server_item_get"] if isinstance(o1["server_item_get"], dict) else {}
    cal_s = num(srv_get.get("calories"))
    # The server's second route, kept beside the first: `item.get` is the brief's server read, and
    # `witness.fields` on the server side is the SAME getter through a different command. They
    # must agree; if they do not, that disagreement is the finding and not a rounding note.
    cal_s_fields = num((o1["witness"]["server"].get("fields") or {}).get("getCalories"))
    o1["calories"] = {"client_witness": cal_c, "server_item_get": cal_s,
                      "server_witness": cal_s_fields,
                      "server_routes_agree": close(cal_s, cal_s_fields)
                      if (cal_s is not None and cal_s_fields is not None) else None}
    o1["body"] = {"client": which_body(cal_c), "server": which_body(cal_s)}
    # The integrity check: the four keys every body shares.
    inv = {}
    for side_name, wrow in (("client", o1["witness"]["client"]),
                            ("server", o1["witness"]["server"])):
        f = wrow.get("fields") or {}
        inv[side_name] = {k: {"read": num(f.get(k)), "expected": exp,
                              "ok": close(num(f.get(k)), exp)}
                          for k, exp in INVARIANT.items()}
    o1["invariant"] = inv
    o1["invariant_ok"] = all(row["ok"] is True for side in inv.values() for row in side.values())
    o1["invariant_rule"] = ("all three mod bodies and vanilla carry IDENTICAL Carbohydrates / "
                            "Lipids / Proteins / HungerChange, so these four are the check that "
                            "the instance read is the item this session is about -- never a "
                            "second discriminator.")

    if cal_c is None or cal_s is None or not out["f_tier_c"]["ok"]:
        p18v = "unmeasured"
    elif not close(cal_c, cal_s):
        p18v = "falsified"       # the two sides disagreeing is itself a falsifier of the claim
    elif close(cal_c, 999.0):
        p18v = "as_predicted"
    else:
        p18v = "falsified"
    grade("P18",
          "getCalories == 999 on BOTH sides -- TKX_ZWatermelon's body, the mod FIRST in Mods= "
          "and LAST alphabetically, is applied last. That is script bodies replayed in "
          "ALPHABETICAL-BY-ID order with per-key last-wins, and Mods= position irrelevant to the "
          "body order (the loader's own `loading` lines still walk Mods=; the two orders differ).",
          {"getCalories": {"client": cal_c, "server": cal_s, "server_witness": cal_s_fields},
           "body_that_won": o1["body"],
           "sides_agree": close(cal_c, cal_s),
           "invariant": inv, "invariant_ok": o1["invariant_ok"],
           "mods_order": list(MODS), "alphabetical_order": sorted(TKX_MODS),
           "means": (which_body(cal_c) or {}).get("means"),
           "next_discriminator_if_111": NEXT_DISCRIMINATOR},
          p18v,
          "777 means Mods= order with last-wins after all -- which REOPENS session 1's M3, since "
          "that rule cannot explain its 111. 111 means NEITHER rule (TKX_ItemOverride is middle "
          "in both orderings, so no ordering over these three ids puts it last) and the next "
          "discriminator is the folder-name swap named in `next_discriminator_if_111`. 1355 "
          "means no mod body applied at all and the session measured nothing about order. The "
          "two sides disagreeing falsifies it outright: script data is loaded per side and never "
          "synced, so a split would say the replay order is not even a property of the build.")

    # ================= O2 -- the replay order in the log, if the engine prints it =======
    o2 = {"question": "does the server log name the three script FILES, and if so in what order?",
          "script_files": out["greps"]["script_files"],
          "watermelon": out["greps"]["watermelon"],
          "loading": out["greps"]["loading"],
          "reading": "the `loading <id>` lines are the LOADER walking Mods=; x121 measured them "
                     "at 94/97/99 and this run's acceptance boot at 94/96/99. They are NOT the "
                     "body replay order, which is what O1 measures indirectly and what this "
                     "grep would measure directly IF the engine printed script paths.",
          "order_rule": "if the engine prints the script files, the LINE ORDER is the replay "
                        "order and can be compared against both Mods= order and alphabetical "
                        "order directly. If it prints nothing, `script_load_lines` is [] and "
                        "this reading is TRIVIAL -- O1 still answers the question."}
    # Re-read at reading time rather than reusing the boot-time grep: script loading can happen
    # after the point the boot-time greps were taken, and an empty list from the wrong moment
    # would be recorded as "the engine prints nothing".
    o2["script_load_lines"] = grep_numbered(server.log_path, SCRIPT_FILE_RX, SCRIPT_FILE_LIMIT)
    o2["script_load_lines_client"] = grep_numbered(c.console, SCRIPT_FILE_RX, SCRIPT_FILE_LIMIT)
    o2["watermelon_lines"] = grep_numbered(server.log_path, WATERMELON_RX, WATERMELON_LIMIT)

    def file_order(hits):
        """The order the three script files appear in, first mention only -- which is what a
        replay order would look like if the engine printed one."""
        seen, order = set(), []
        for h in hits:
            if "error" in h:
                continue
            m = SCRIPT_FILE_RX.search(h.get("text", ""))
            if not m:
                continue
            k = m.group(0).lower()
            if k not in seen:
                seen.add(k)
                order.append({"file": k, "line": h["line"]})
        return order

    o2["first_mention_order_server"] = file_order(o2["script_load_lines"])
    o2["first_mention_order_client"] = file_order(o2["script_load_lines_client"])
    FILE_OF = {"TKX_ZWatermelon": "tkx_zwatermelon", "TKX_ItemOverride": "tkx_item_override",
               "TKX_EatHook": "tkx_eat_hook"}
    o2["expected_if_mods_order"] = [FILE_OF[m] for m in MODS if m in FILE_OF]
    o2["expected_if_alphabetical"] = [FILE_OF[m] for m in sorted(TKX_MODS)]
    seen_files = [r["file"] for r in o2["first_mention_order_server"]]
    o2["observed_order_server"] = seen_files
    o2["matches_mods_order"] = (seen_files == o2["expected_if_mods_order"]) if seen_files else None
    o2["matches_alphabetical"] = (seen_files == o2["expected_if_alphabetical"]) \
        if seen_files else None
    out["phases"]["O2"] = o2
    if not seen_files:
        o2v = "trivial"
    elif len(seen_files) < 3:
        o2v = "unmeasured"       # a partial order cannot be compared against either rule
    else:
        o2v = "as_predicted" if o2["matches_alphabetical"] else "falsified"
    grade("O2",
          "IF the engine prints the three script file paths, their first-mention order is "
          "ALPHABETICAL (tkx_eat_hook, tkx_item_override, tkx_zwatermelon) and not Mods= order "
          "(tkx_zwatermelon, tkx_item_override, tkx_eat_hook) -- the same claim P18 makes, read "
          "directly off the log instead of inferred from a number.",
          {"observed": seen_files,
           "expected_if_alphabetical": o2["expected_if_alphabetical"],
           "expected_if_mods_order": o2["expected_if_mods_order"],
           "script_file_hits_server": out["greps"]["script_files"]["server"]["count"],
           "script_file_hits_client": out["greps"]["script_files"]["client"]["count"],
           "watermelon_hits_server": len(o2["watermelon_lines"]),
           "saturated": out["greps"]["script_files"]["server"]["saturated"]},
          o2v,
          "an order matching Mods= falsifies it. NOTHING printed is TRIVIAL, not a falsifier: the "
          "engine is under no obligation to log script paths, and O1 is the reading that "
          "actually settles the question. Fewer than three files named is UNMEASURED -- a "
          "partial order cannot be compared against either rule.")

    # ================= O3 -- the census control ========================================
    counts = step("o3_items_count", server, "items.count", "")
    cnt = counts["ack"] if isinstance(counts["ack"], dict) else {}
    by_module = cnt.get("foodByModule") if isinstance(cnt.get("foodByModule"), dict) else {}
    base_food, tkx_food = by_module.get("Base"), by_module.get("TKX")
    out["phases"]["O3"] = {
        "question": "do THREE redefinitions of one existing type add any item record?",
        "items_count": cnt, "foodByModule_Base": base_food, "foodByModule_TKX": tkx_food,
        "baseline": BASE_FOOD_BASELINE,
        "baseline_source": "testing/artifacts/exp05-20260910-084109/food-scan.json:350 "
                           "(foodByModule.Base; 1005 is that dataset's total item RECORDS)",
        "note": "x121 read the same 722 with TWO Watermelon redefinitions in play. Mod F makes it "
                "three, and a redefinition that ADDED would show as 723 or 724.",
    }
    if base_food is None or tkx_food is None:
        o3v = "unmeasured"
    elif base_food == BASE_FOOD_BASELINE and tkx_food == TKX_FOOD_EXPECTED:
        o3v = "as_predicted"
    else:
        o3v = "falsified"
    grade("O3",
          f"foodByModule.Base == {BASE_FOOD_BASELINE} (-0 against the baseline, unchanged from "
          f"x121's reading with two redefinitions) and foodByModule.TKX == {TKX_FOOD_EXPECTED} "
          "-- three redefinitions of an existing type add NO item record",
          {"foodByModule.Base": base_food, "foodByModule.TKX": tkx_food,
           "delta_vs_baseline": None if base_food is None else base_food - BASE_FOOD_BASELINE,
           "total": cnt.get("total"), "food": cnt.get("food")},
          o3v,
          f"{BASE_FOOD_BASELINE + 1} (or +2) falsifies it -- a redefinition would then ADD a "
          "record and 'which body wins' would be the wrong question entirely, since there would "
          "be several records rather than one contested one.")

    # ================= O4 -- the harness control ======================================
    ctrl = {"client": probe(c, "lua.global", CONTROL_GLOBAL),        # CLIENT FIRST
            "server": probe(server, "lua.global", CONTROL_GLOBAL)}
    out["phases"]["O4"] = {
        "question": "is the _G walk itself sound on both sides?",
        "global": CONTROL_GLOBAL, "replies": ctrl,
        "why": "a resolved=false here means the walk is broken and every lua.global reading in "
               "this file is suspect -- it does NOT mean a mod global is absent.",
    }
    ctrl_vals = {s: (num(r.get("value")) if isinstance(r, dict) else None)
                 for s, r in ctrl.items()}
    ctrl_res = {s: (r.get("resolved") if isinstance(r, dict) else None) for s, r in ctrl.items()}
    if ctrl_vals["client"] is None and ctrl_vals["server"] is None:
        o4v = "unmeasured"
    elif ctrl_vals["client"] == 1 and ctrl_vals["server"] == 1:
        o4v = "as_predicted"
    else:
        o4v = "falsified"
    grade("O4", f"{CONTROL_GLOBAL} resolves to 1 on BOTH sides",
          {"value": ctrl_vals, "resolved": ctrl_res}, o4v,
          "anything else means the harness's own _G walk is broken on that side and the session's "
          "lua.global readings cannot be trusted -- it is a harness finding, not a mod finding.")

    # ================= O5 -- text.get in the BARE B42 key form ========================
    o5 = {"question": "is 42.20.4's translation table keyed by the BARE fullType, and does a "
                      "DEDICATED SERVER have a translation table at all?",
          "why_reasked": "x121 M4 asked ONLY the B41 prefixed form (ItemName_<fullType>) and all "
                         "four keys missed on BOTH sides. That is consistent with two very "
                         "different worlds -- 'mod translations never reach a dedicated server' "
                         "and 'the table is not keyed that way at all' -- and the bare form is "
                         "what separates them.",
          "x121_prefixed": X121_PREFIXED,
          "client": {}, "server": {}}
    for key, why in TEXT_KEYS:                     # CLIENT FIRST at every key
        o5["client"][key] = {"why": why, "reply": probe(c, "text.get", key)}
        o5["server"][key] = {"why": why, "reply": probe(server, "text.get", key)}
        save(path, out, tl, server)
    o5["grading_rule"] = (
        "amendment 12: a server-side text.get carrying `null = true` (or, without the slice-12 "
        "null guard, `text == \"nil\"`) is INCONCLUSIVE for the server half, not a miss -- it "
        "says the lookup route answered nothing at all. A MISS returns the key itself "
        "(Translator.getTextInternal), which is also what makes a hit evidence: the text cannot "
        "be an echo of the argument.")

    def txt(side, key):
        r = o5[side].get(key, {}).get("reply")
        if not isinstance(r, dict):
            return {"reply_shape": type(r).__name__, "raw": str(r)[:200]}
        row = {k: r.get(k) for k in ("text", "miss", "null", "error") if k in r}
        row["hit"] = (r.get("miss") is False and not r.get("null") and not r.get("error"))
        row["inconclusive"] = bool(r.get("null") or r.get("error"))
        return row

    texts = {key: {"client": txt("client", key), "server": txt("server", key)}
             for key, _why in TEXT_KEYS}
    o5["reads"] = texts
    # Session 1's two prefixed keys, re-read here: if they do not reproduce, the two sessions
    # disagree about the same key and NEITHER reading can be cited without the other.
    o5["prefixed_reproduced"] = {
        k: {"x121": X121_PREFIXED[k],
            "x124_client": texts[k]["client"], "x124_server": texts[k]["server"],
            "client_still_miss": texts[k]["client"].get("miss") is True}
        for k in X121_PREFIXED}
    out["phases"]["O5"] = o5

    apple_c, apple_s = texts["Base.Apple"]["client"], texts["Base.Apple"]["server"]
    json_c, json_s = texts["TKX.FibreBarJson"]["client"], texts["TKX.FibreBarJson"]["server"]
    named_c = texts["TKX.FibreBarNamed"]["client"]
    if apple_c.get("hit") is None and apple_c.get("miss") is None:
        p19v = "unmeasured"
    elif apple_c.get("hit") and json_c.get("hit") and not json_s.get("hit"):
        p19v = "as_predicted"
    else:
        p19v = "falsified"
    grade("P19",
          "the BARE key hits on the CLIENT -- `Base.Apple` answers the vanilla display name with "
          "miss:false -- and on the dedicated SERVER it misses or reads null:true; "
          "`TKX.FibreBarJson` hits on the client only. Together that says 42.20.4's table is "
          "keyed by the bare fullType (so x121's four prefixed misses were the WRONG KEY FORM, "
          "not an absent table) and that a dedicated server's table is a separate reading.",
          {"bare": {"Base.Apple": {"client": apple_c, "server": apple_s},
                    "TKX.FibreBarJson": {"client": json_c, "server": json_s},
                    "TKX.FibreBarNamed": {"client": named_c,
                                          "server": texts["TKX.FibreBarNamed"]["server"]}},
           "prefixed_controls": {k: texts[k] for k in X121_PREFIXED},
           "prefixed_reproduced": o5["prefixed_reproduced"],
           "server_inconclusive": {k: v["server"].get("inconclusive") for k, v in texts.items()}},
          p19v,
          "a bare `Base.Apple` that MISSES on the client too says the table is not keyed by the "
          "bare fullType either, and slice 09's hypotheses stay open with both key forms "
          "eliminated. A `TKX.FibreBarJson` that hits on the SERVER kills hypothesis (iii) -- mod "
          "translations WOULD reach a dedicated server. A `TKX.FibreBarNamed` that hits says the "
          "B41 .txt layout is still read on 42.20.4. A prefixed control that now HITS contradicts "
          "x121 on the same key and puts both sessions' M4/O5 rows in doubt.")

    # ================= the readings, stated as verdicts ================================
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "f_tier_c_ok": out["f_tier_c"]["ok"],
        "field_count_ok": all(x["count_ok"] for x in FIELD_CHECKS) if FIELD_CHECKS else None,
        "field_checks": len(FIELD_CHECKS),
        "field_count_failures": [x for x in FIELD_CHECKS if not x["count_ok"]],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "O1_watermelon_calories": {"client": cal_c, "server": cal_s,
                                   "server_witness": cal_s_fields},
        "O1_body_that_won": o1["body"],
        "O1_invariant_ok": o1["invariant_ok"],
        "O1_means": (which_body(cal_c) or {}).get("means"),
        "O2_script_file_order": seen_files,
        "O2_script_file_hits": {"server": out["greps"]["script_files"]["server"]["count"],
                                "client": out["greps"]["script_files"]["client"]["count"]},
        "O2_loading_ids": loading_ids,
        "O3_foodByModule": {"Base": base_food, "TKX": tkx_food},
        "O4_TK_version": ctrl_vals,
        "O5_bare": {k: {"client": texts[k]["client"], "server": texts[k]["server"]}
                    for k in ("Base.Apple", "TKX.FibreBarJson", "TKX.FibreBarNamed")},
        "O5_prefixed": {k: {"client": texts[k]["client"], "server": texts[k]["server"]}
                        for k in X121_PREFIXED},
        "lua_error_hits": {"client": out["greps"]["lua_errors"]["client"]["count"],
                           "server": out["greps"]["lua_errors"]["server"]["count"]},
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
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-order.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
