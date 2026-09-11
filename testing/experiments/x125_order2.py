"""Slice 12, session 5 (`x125`): the THREE-WAY ordering discriminator -- LIVE.

**This session exists because sessions 1 and 4 each read a number that two different rules
predict.** Both runs put the winning body's mod simultaneously FIRST in `Mods=` and LAST
alphabetically, so the two rules could not disagree:

  * `x121-20260911-030023` read `Base.Watermelon` = **111** (`TKX_ItemOverride`) with
    `Mods= … TKX_ItemOverride, TKX_Nutrient, TKX_EatHook`. ItemOverride was first of the bodies in
    `Mods=` AND the alphabetically last of the two ids that carried a Watermelon block.
  * `x124-20260911-035819` read **999** (`TKX_ZWatermelon`) with
    `Mods= … TKX_ZWatermelon, TKX_ItemOverride, TKX_EatHook`. ZWatermelon was first of the three in
    `Mods=` AND last of the three alphabetically.

Session 4's report called it for ALPHABETICAL-BY-ID, and that call is not wrong so much as
under-determined: "the bodies are replayed in REVERSE `Mods=` order" fits both readings exactly as
well, and nothing in either run separates them. What IS settled, twice over, is that `Mods=`-LAST
does not win (777 never came back), and per-key last-wins itself (x121 M2b: the narrowed
`item Orange` merged, vanilla's `Calories 95` losing to the mod's 400).

**The separator, with no new mod.** The same three bodies, re-ordered in `Mods=` so that being
first in `Mods=` and being last alphabetically land on DIFFERENT mods:

    Mods= …, TKX_ItemOverride, TKX_ZWatermelon, TKX_EatHook
    alphabetical: TKX_EatHook < TKX_ItemOverride < TKX_ZWatermelon

  | `getCalories` | whose body ran last | the rule it SELECTS | the rules it KILLS |
  |---|---|---|---|
  | **999** | `TKX_ZWatermelon` (`Mods=` middle, id last)  | ALPHABETICAL-LAST wins | first-in-`Mods=`, `Mods=`-last, alphabetical-first |
  | **111** | `TKX_ItemOverride` (`Mods=` first, id first) | FIRST-IN-`Mods=` wins (reverse-`Mods=` replay) | alphabetical-last, `Mods=`-last, alphabetical-first |
  | **777** | `TKX_EatHook` (`Mods=` last, id middle)      | `Mods=`-LAST *or* alphabetical-FIRST -- and BOTH were falsified in x121 and again in x124 | nothing; it REOPENS both earlier sessions instead |
  | **1355** | none -- vanilla survived | no mod body applied at all | nothing; the session measured nothing about order |

Every cell of that table is a different world, and one read picks one. The 777 row is the one to
read carefully: it is the only number that does not close the question, because `TKX_EatHook` is
both `Mods=`-last and alphabetically-first here, and the two rules that predict it have each been
falsified twice. A 777 would therefore not select a rule; it would say the previous two readings
and this one cannot all three be about the same mechanism.

**What a 999 does NOT settle** (session 4's concern 2, carried forward rather than quietly
dropped): the three IDs, the three script FILE basenames (`tkx_eat_hook.txt` <
`tkx_item_override.txt` < `tkx_zwatermelon.txt`) and the three FOLDER names all sort in the SAME
order. So a 999 says "alphabetical by something that orders these three the way their ids do" --
id, script path and folder name stay confounded, and the artifact says so (`still_confounded`).

Four readings, none of which needs the others to be interpretable:

  O1  the discriminator itself -- RCON-spawn a `Base.Watermelon`, poll until the CLIENT sees it,
      then read the five macro getters off the instance client-side and `item.get` server-side.
      The instance is the only route: `TK.SCRIPT_GETTERS` comes back with all four nutrition keys
      ABSENT on a SCRIPT object (measured slice 01, re-confirmed in `td1-20260910-192457`, in
      `x121` M1 and in `x124`), so `item.script` cannot answer this.
  O2  the replay order read straight off the server log, IF the engine prints script paths at all.
      `x124` graded this `unmeasured` and its report raised a do-not-cite: the regex alternative
      `tkx_zwatermelon` is BOTH a script basename and the lowercase of the mod id
      `TKX_ZWatermelon`, so six loader/`NoSuchFileException` lines about the MOD were counted as
      if they named the FILE. This run keeps the same broad grep (so the counts stay comparable)
      and CLASSIFIES each hit -- a hit is a file-path hit only if the name carries the `.txt`
      extension or the line sits inside a `media/scripts` path -- and computes the order from the
      file-path hits alone.
  O3  the census control -- `foodByModule.Base` must still be 722. Three redefinitions of one
      existing type add no item, and a number other than 722 means the run is not measuring what
      the table above assumes it is measuring.
  O4  the harness control -- `lua.global TK.version` == 1 on BOTH sides. A `resolved: false` here
      means the `_G` walk is broken and every `lua.global` reading in the file is suspect, not
      that some mod global is absent.

`text.get` is NOT re-asked. `x124`'s O5 answered it for good: all five key forms, bare and
prefixed, missed on both sides, and `getText` is simply not the route to item names on 42.20.4.

**The one thing this session must not do is take the 999 for granted.** Session 1 predicted 777
with the same confidence and was wrong, which is the only reason this line of sessions exists.

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

PROFILE = "x12-order2"
USER = "admin"
# `Mods=` order IS this tuple's order (profile.mods -> the ini's Mods= line). The alphabetical
# order of the same three is EatHook < ItemOverride < ZWatermelon. Unlike sessions 1 and 4, NO mod
# is both first in Mods= and last alphabetically -- that separation is the whole session.
MODS = ("PZTestKit", "TKX_ItemOverride", "TKX_ZWatermelon", "TKX_EatHook")
TKX_MODS = ("TKX_ItemOverride", "TKX_ZWatermelon", "TKX_EatHook")
# Step 2's acceptance run: RESULT PASS, both [[verify]] rows ok=True, 0 server error lines, and
# `loading TKX_ItemOverride` / `TKX_ZWatermelon` / `TKX_EatHook` at server lines 94 / 97 / 99 and
# client lines 84/87/89 + 168/171/173 (two Lua states) -- i.e. the loader walks `Mods=` order,
# exactly as in x121 (94/97/99) and x124 (94/96/99). The loader's order is NOT in question here;
# whether the BODY replay follows it is.
ACCEPTANCE_RUN = "run-20260911-041437"
ACCEPTANCE_LOADING_LINES = {"server": {"TKX_ItemOverride": 94, "TKX_ZWatermelon": 97,
                                       "TKX_EatHook": 99},
                            "client": {"TKX_ItemOverride": [84, 168], "TKX_ZWatermelon": [87, 171],
                                       "TKX_EatHook": [89, 173]}}

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
# Every number that can come back, and what each one MEANS, stated before the run. `mods_position`
# and `alpha_position` are 1-based among the THREE TKX mods (PZTestKit carries no Watermelon body).
# The four non-Calories macros are IDENTICAL in all three mod bodies and in vanilla, so they are
# the integrity check on the read, not a second discriminator.
CANDIDATES = {
    999.0: {"mod": "TKX_ZWatermelon", "mods_position": 2, "alpha_position": 3,
            "selects": "ALPHABETICAL-LAST wins",
            "kills": ["first-in-Mods= (reverse-Mods= replay)", "Mods=-last", "alphabetical-first"],
            "means": "the body replayed last is the one whose id sorts last, from the MIDDLE of "
                     "Mods= -- so Mods= position is irrelevant to the body order, and session "
                     "4's alphabetical call stands on a reading that could finally disagree with "
                     "the reverse-Mods= rule and did"},
    111.0: {"mod": "TKX_ItemOverride", "mods_position": 1, "alpha_position": 1,
            "selects": "FIRST-IN-Mods= wins (bodies replayed in REVERSE Mods= order)",
            "kills": ["alphabetical-last", "Mods=-last", "alphabetical-first"],
            "means": "the body replayed last is the one FIRST in Mods=, from the FIRST "
                     "alphabetical slot -- so session 4's alphabetical-by-id call is wrong and "
                     "both earlier readings were reverse-Mods= all along"},
    777.0: {"mod": "TKX_EatHook", "mods_position": 3, "alpha_position": 2,
            "selects": "Mods=-LAST or ALPHABETICAL-FIRST -- the two rules coincide on this mod "
                       "in this order, and BOTH were falsified in x121 and again in x124",
            "kills": [],
            "means": "REOPENS both earlier sessions: no single rule over these three ids explains "
                     "111 (x121), 999 (x124) and 777 (here) together, so the ordering key is not "
                     "a property of the id set at all"},
    1355.0: {"mod": "vanilla", "mods_position": 0, "alpha_position": 0,
             "selects": "none",
             "kills": [],
             "means": "no mod body applied at all -- the session measured nothing about order"},
}
# The four keys every body agrees on (mod A's, mod C's and mod F's Watermelon blocks are byte
# for byte the vanilla block apart from Calories). Read as the integrity check described above.
INVARIANT = {"getCarbohydrates": 341.11, "getLipids": 6.78, "getProteins": 27.56,
             "getHungChange": -0.6}
# `getHungChange()` is the SCRIPT's HungerChange / 100 (Item.InstanceItem), so -60.0 reads -0.6.
STILL_CONFOUNDED = (
    "a 999 selects 'alphabetical-last' but not alphabetical BY WHAT. The three ids "
    "(TKX_EatHook < TKX_ItemOverride < TKX_ZWatermelon), the three script file basenames "
    "(tkx_eat_hook.txt < tkx_item_override.txt < tkx_zwatermelon.txt) and the three FOLDER names "
    "(identical to the ids) all sort in the SAME order, so id / script path / folder name remain "
    "confounded -- exactly as x124's report recorded. The cheap discriminator, if a later task "
    "wants it closed, is a fourth mod whose id sorts last while its script file sorts first "
    "(session 3 proved the loader resolves through mod.info, not the folder name -- "
    "x123-20260911-034426, P16 as_predicted -- so the drift is safe to introduce)."
)
NEXT_IF_777 = (
    "if 777: the ordering key is not a property of the id set. Mods=-last was falsified by x121 "
    "(111, EatHook last in Mods=) and by x124 (999, EatHook last in Mods=); alphabetical-first "
    "was falsified by the same two readings. A 777 here would contradict both, and the next step "
    "is NOT another ordering profile but a re-read of whether the three bodies are all reaching "
    "the same table -- start by confirming f_tier_c and the loading lines in THIS artifact, then "
    "re-run x124's exact profile to check the 999 reproduces at all."
)

# ---- O2: the three script FILES, and the subject's name. Case-insensitive because a log may
# print either the on-disk casing or a normalised one, and which it prints is not the question.
SCRIPT_FILE_RX = re.compile(r"tkx_zwatermelon|tkx_item_override|tkx_eat_hook", re.I)
# x124's do-not-cite (report concern 1): `tkx_zwatermelon` is BOTH a script basename and the
# lowercase of the mod id, so loader lines and NoSuchFileException paths naming the MOD were
# indistinguishable from lines naming the FILE. A hit counts as a FILE hit only if the name
# carries the `.txt` extension, OR the line is inside a `media/scripts` path. A bare path
# separator is NOT enough: x124's four `NoSuchFileException` lines are
# `…\TKX_ZWatermelon\42.20\media\AnimSets` — a MOD FOLDER under a path, naming no script at all.
# The broad grep is kept unchanged so the counts stay comparable with x124; the classification is
# what the order is computed from.
FILE_HIT_RX = re.compile(r"(?:tkx_zwatermelon|tkx_item_override|tkx_eat_hook)\.txt", re.I)
SCRIPTS_CTX_RX = re.compile(r"media[/\\]scripts", re.I)
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

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"

# Per-SCOPE modData exclusion sets (pass-1 precedent, docs/decisions.md:133), carried for shape
# parity with the sessions that take a census. THIS session takes NONE -- O1-O4 read script data
# and log files, and not one of them touches modData -- so the sets are recorded in the artifact
# as inapplicable rather than silently omitted, which would leave a reader of the series
# wondering which census this file forgot.
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}
VANILLA_ITEM_KEYS = {"customName", "Tooltip"}

# The dormant `sent` branch's routing table, widened per the slice-11 driver note. Anything NOT
# in here is recorded raw rather than waited on.
RESULT_DOC = {"witness.fields": "witness_fields", "witness.moddata": "witness_moddata"}

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x125")
path = os.path.join(run_dir, "platform-order2.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": "x125 -- slice 12 session 5: the three-way ordering discriminator",
    "user": USER,
    "profile": prof.report(),
    "mods": list(MODS),
    "mods_order": list(MODS),
    "alphabetical_order": sorted(TKX_MODS),
    "mods_order_note": "Mods= order is this list's order. The ALPHABETICAL order of the three TKX "
                       "ids is TKX_EatHook < TKX_ItemOverride < TKX_ZWatermelon. Unlike x121 and "
                       "x124, NO mod here is both first in Mods= and last alphabetically: "
                       "ItemOverride is Mods=-first and alpha-first, ZWatermelon is Mods=-middle "
                       "and alpha-last, EatHook is Mods=-last and alpha-middle. That is the whole "
                       "design -- the three rules now name three different numbers.",
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "acceptance_loading_lines": ACCEPTANCE_LOADING_LINES,
    "fixture_day_length": DAY_LENGTH,
    "game_minute_seconds": GAME_MINUTE_S,
    "scope_exclusions": {
        "player": sorted(VANILLA_PLAYER_KEYS), "item": sorted(VANILLA_ITEM_KEYS),
        "applies_here": False,
        "why": "no modData census is taken this session -- O1-O4 read script data and log files. "
               "The sets are recorded so a reader of the series can see they were considered and "
               "found inapplicable, not omitted.",
    },
    "field_counts_expected": {"macros": MACRO_COUNT},
    "candidates": {str(int(k)): v for k, v in CANDIDATES.items()},
    "still_confounded": STILL_CONFOUNDED,
    "prior": {
        "x121_run": "x121-20260911-030023",
        "x121_M3": "getCalories 111 (TKX_ItemOverride) -- Mods=-first AND alpha-last of the two "
                   "bodies in that run. Verdict falsified against a Mods=-last prediction.",
        "x121_M2b": "verdict falsified -- a partial block MERGES per key, so per-key LAST-wins is "
                    "established independently (vanilla's Apple 95 lost to the mod's 400)",
        "x124_run": "x124-20260911-035819",
        "x124_P18": "getCalories 999 on both sides (TKX_ZWatermelon) -- Mods=-first AND alpha-last "
                    "again. Verdict as_predicted, but ALPHABETICAL-LAST and FIRST-IN-Mods= fit it "
                    "equally, which is why this session exists.",
        "x124_O5": "all five text.get key forms missed on both sides -- getText is not the route "
                   "to item names on 42.20.4. Not re-asked here.",
        "loading_lines_prior": "x121 server 94/97/99, x124 server 94/96/99, both in Mods= order. "
                               "The LOADER walks Mods=; the body replay is the open question.",
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


def loading_rows(hits):
    """The `loading <id>` lines as {id, line} rows, in the order they were printed. The brief asks
    for the line NUMBERS beside the reading, because 'the loader walked Mods=' is a claim about
    order and order is unreadable without them."""
    rows = []
    for h in hits:
        if "error" in h or "loading " not in h.get("text", ""):
            continue
        rows.append({"mod": h["text"].split("loading ")[-1].strip(), "line": h["line"]})
    return rows


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
    load_server = loading_rows(out["greps"]["loading"]["server"]["hits"])
    load_client = loading_rows(out["greps"]["loading"]["client"]["hits"])
    loading_ids = [r["mod"] for r in load_server]
    out["loading_lines"] = {
        "server": load_server, "client": load_client,
        "server_ids_in_order": loading_ids,
        "matches_mods_order": loading_ids == [m for m in MODS if m in loading_ids],
        "acceptance_run_lines": ACCEPTANCE_LOADING_LINES,
        "why": "the LOADER's order, recorded beside the reading because the whole session is the "
               "claim that the BODY replay order is a different order. x121 read 94/97/99 and "
               "x124 94/96/99, both Mods= order.",
    }
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
        "loading_matches_mods_order": out["loading_lines"]["matches_mods_order"],
    }
    out["f_tier_c"]["ok"] = bool(out["f_tier_c"]["folder_present"]
                                 and out["f_tier_c"]["mods_not_found_empty"]
                                 and out["f_tier_c"]["loading_line_present"])
    tl.mark("tier_c", ok=str(out["f_tier_c"]["ok"]))
    if not out["f_tier_c"]["ok"]:
        note("mod F's tier-(c) gate did NOT hold -- every reading below is about a world that "
             "may not contain TKX_ZWatermelon, and P20 must be read as unmeasured whatever "
             "number comes back.")
    save(path, out, tl, server)

    # ================= O1 -- the discriminator ==========================================
    sp = spawn(SUBJECT, c, "O1: the macros live on the INSTANCE -- Kahlua does not expose them "
                           "on the script object, so item.script cannot answer this")
    o1 = {"question": "with TKX_ItemOverride FIRST in Mods= and TKX_ZWatermelon LAST "
                      "alphabetically but only MIDDLE in Mods=, whose Watermelon body is "
                      "applied last?",
          "spawn": sp,
          "witness": both_fields(c, f"item {USER}/{SUBJECT}", MACROS, MACRO_COUNT,
                                 "Calories: 999 in TKX_ZWatermelon, 111 in TKX_ItemOverride, "
                                 "777 in TKX_EatHook, 1355 in vanilla"),
          "server_item_get": step("o1_item_get", server, "item.get",
                                  f"{USER} {SUBJECT}")["ack"],
          "mods_order": list(MODS),
          "alphabetical_order": sorted(TKX_MODS),
          "loading_lines": out["loading_lines"],
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
        p20v = "unmeasured"
    elif not close(cal_c, cal_s):
        p20v = "falsified"       # the two sides disagreeing is itself a falsifier of the claim
    elif close(cal_c, 999.0):
        p20v = "as_predicted"
    else:
        p20v = "falsified"
    grade("P20",
          "getCalories == 999 on BOTH sides -- TKX_ZWatermelon's body, from the MIDDLE of Mods= "
          "and the LAST alphabetical slot, is applied last. That selects ALPHABETICAL-LAST and "
          "kills first-in-Mods= (reverse-Mods= replay), Mods=-last and alphabetical-first, "
          "confirming x124's call on a reading where the two surviving rules could finally "
          "disagree. The loader's own `loading` lines still walk Mods=; the two orders differ.",
          {"getCalories": {"client": cal_c, "server": cal_s, "server_witness": cal_s_fields},
           "body_that_won": o1["body"],
           "sides_agree": close(cal_c, cal_s),
           "invariant": inv, "invariant_ok": o1["invariant_ok"],
           "mods_order": list(MODS), "alphabetical_order": sorted(TKX_MODS),
           "loading_lines": out["loading_lines"],
           "rule_selected": (which_body(cal_c) or {}).get("selects"),
           "rules_killed": (which_body(cal_c) or {}).get("kills"),
           "means": (which_body(cal_c) or {}).get("means"),
           "still_confounded": STILL_CONFOUNDED,
           "next_if_777": NEXT_IF_777},
          p20v,
          "111 means FIRST-IN-Mods= wins -- the bodies are replayed in REVERSE Mods= order, "
          "x124's alphabetical-by-id call is wrong, and both earlier readings were reverse-Mods= "
          "all along. 777 means TKX_EatHook won from the Mods=-LAST and alphabetically-FIRST "
          "slot, and BOTH of those rules were falsified in x121 and again in x124 -- so a 777 "
          "selects nothing and REOPENS the whole line (see next_if_777). 1355 means no mod body "
          "applied at all and the session measured nothing about order. The two sides disagreeing "
          "falsifies it outright: script data is loaded per side and never synced, so a split "
          "would say the replay order is not even a property of the build.")

    # ================= O2 -- the replay order in the log, if the engine prints it =======
    o2 = {"question": "does the server log name the three script FILES, and if so in what order?",
          "script_files": out["greps"]["script_files"],
          "watermelon": out["greps"]["watermelon"],
          "loading": out["greps"]["loading"],
          "reading": "the `loading <id>` lines are the LOADER walking Mods=; x121 measured them "
                     "at 94/97/99, x124 at 94/96/99 and this run's acceptance boot at 94/97/99. "
                     "They are NOT the body replay order, which is what O1 measures indirectly "
                     "and what this grep would measure directly IF the engine printed script "
                     "paths.",
          "classification_rule": "x124's do-not-cite (report concern 1): `tkx_zwatermelon` is "
                                 "BOTH a script basename and the lowercase of the mod id, so "
                                 "loader lines and NoSuchFileException paths naming the MOD "
                                 "counted as if they named the FILE. Here a hit is a FILE hit "
                                 "only if the name carries the `.txt` extension or the line sits "
                                 "inside a `media/scripts` path -- a bare path separator is NOT "
                                 "enough, because x124's four NoSuchFileException lines put the "
                                 "MOD FOLDER under a path while naming no script "
                                 "(…/TKX_ZWatermelon/42.20/media/AnimSets). The order is computed "
                                 "from the file hits alone, and the raw broad-grep counts are "
                                 "kept beside them unchanged so the two sessions stay "
                                 "comparable.",
          "order_rule": "if the engine prints the script files, the LINE ORDER is the replay "
                        "order and can be compared against both Mods= order and alphabetical "
                        "order directly. If it prints nothing, `script_load_lines` classifies to "
                        "zero file hits and this reading is TRIVIAL -- O1 still answers the "
                        "question."}
    # Re-read at reading time rather than reusing the boot-time grep: script loading can happen
    # after the point the boot-time greps were taken, and an empty list from the wrong moment
    # would be recorded as "the engine prints nothing".
    o2["script_load_lines"] = grep_numbered(server.log_path, SCRIPT_FILE_RX, SCRIPT_FILE_LIMIT)
    o2["script_load_lines_client"] = grep_numbered(c.console, SCRIPT_FILE_RX, SCRIPT_FILE_LIMIT)
    o2["watermelon_lines"] = grep_numbered(server.log_path, WATERMELON_RX, WATERMELON_LIMIT)

    def classify(hits):
        """Each broad-grep hit tagged `file_path` or `id_or_other`, so a loader line naming the
        MOD is never read as a line naming the FILE (x124 report concern 1)."""
        rows = []
        for h in hits:
            if "error" in h:
                rows.append(dict(h, hit_class="error"))
                continue
            text = h.get("text", "")
            m = FILE_HIT_RX.search(text)
            in_scripts = bool(SCRIPTS_CTX_RX.search(text))
            is_file = bool(m) or in_scripts
            rows.append(dict(h, hit_class="file_path" if is_file else "id_or_other",
                             file_match=m.group(0).lower() if m else None,
                             scripts_path=in_scripts))
        return rows

    o2["classified_server"] = classify(o2["script_load_lines"])
    o2["classified_client"] = classify(o2["script_load_lines_client"])
    o2["file_hits_server"] = [r for r in o2["classified_server"] if r["hit_class"] == "file_path"]
    o2["file_hits_client"] = [r for r in o2["classified_client"] if r["hit_class"] == "file_path"]
    o2["id_or_other_server"] = sum(1 for r in o2["classified_server"]
                                   if r["hit_class"] == "id_or_other")

    def file_order(rows):
        """The order the three script files appear in, first mention only -- which is what a
        replay order would look like if the engine printed one. FILE hits only."""
        seen, order = set(), []
        for r in rows:
            m = SCRIPT_FILE_RX.search(r.get("text", ""))
            if not m:
                continue
            k = m.group(0).lower()
            if k not in seen:
                seen.add(k)
                order.append({"file": k, "line": r["line"]})
        return order

    o2["first_mention_order_server"] = file_order(o2["file_hits_server"])
    o2["first_mention_order_client"] = file_order(o2["file_hits_client"])
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
          "IF the engine prints the three script file PATHS, their first-mention order is "
          "ALPHABETICAL (tkx_eat_hook, tkx_item_override, tkx_zwatermelon) and not Mods= order "
          "(tkx_item_override, tkx_zwatermelon, tkx_eat_hook) -- the same claim P20 makes, read "
          "directly off the log instead of inferred from a number. x124 printed NONE, so this is "
          "expected to come back trivial again.",
          {"observed": seen_files,
           "expected_if_alphabetical": o2["expected_if_alphabetical"],
           "expected_if_mods_order": o2["expected_if_mods_order"],
           "broad_grep_hits_server": out["greps"]["script_files"]["server"]["count"],
           "broad_grep_hits_client": out["greps"]["script_files"]["client"]["count"],
           "file_path_hits_server": len(o2["file_hits_server"]),
           "file_path_hits_client": len(o2["file_hits_client"]),
           "id_or_other_hits_server": o2["id_or_other_server"],
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
        "note": "x121 read 722 with TWO Watermelon redefinitions in play and x124 read 722 with "
                "the same three as here, in a different Mods= order. A count that moved with the "
                "ORDER would be the real finding.",
    }
    if base_food is None or tkx_food is None:
        o3v = "unmeasured"
    elif base_food == BASE_FOOD_BASELINE and tkx_food == TKX_FOOD_EXPECTED:
        o3v = "as_predicted"
    else:
        o3v = "falsified"
    grade("O3",
          f"foodByModule.Base == {BASE_FOOD_BASELINE} (-0 against the baseline, unchanged from "
          f"x121 and x124) and foodByModule.TKX == {TKX_FOOD_EXPECTED} -- three redefinitions of "
          "an existing type add NO item record, and re-ordering Mods= does not change that",
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

    # ================= the readings, stated as verdicts ================================
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "f_tier_c_ok": out["f_tier_c"]["ok"],
        "field_count_ok": all(x["count_ok"] for x in FIELD_CHECKS) if FIELD_CHECKS else None,
        "field_checks": len(FIELD_CHECKS),
        "field_count_failures": [x for x in FIELD_CHECKS if not x["count_ok"]],
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "mods_order": list(MODS),
        "alphabetical_order": sorted(TKX_MODS),
        "loading_lines": out["loading_lines"],
        "O1_watermelon_calories": {"client": cal_c, "server": cal_s,
                                   "server_witness": cal_s_fields},
        "O1_body_that_won": o1["body"],
        "O1_invariant_ok": o1["invariant_ok"],
        "O1_rule_selected": (which_body(cal_c) or {}).get("selects"),
        "O1_rules_killed": (which_body(cal_c) or {}).get("kills"),
        "O1_means": (which_body(cal_c) or {}).get("means"),
        "O1_still_confounded": STILL_CONFOUNDED,
        "O2_script_file_order": seen_files,
        "O2_file_path_hits": {"server": len(o2["file_hits_server"]),
                              "client": len(o2["file_hits_client"])},
        "O2_broad_grep_hits": {"server": out["greps"]["script_files"]["server"]["count"],
                               "client": out["greps"]["script_files"]["client"]["count"]},
        "O2_loading_ids": loading_ids,
        "O3_foodByModule": {"Base": base_food, "TKX": tkx_food},
        "O4_TK_version": ctrl_vals,
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
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "platform-order2.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
