"""Teardown 3: AutoCook measured on a live dedicated server + a real client (slice 11 of the
09-11 teardown wave, pass 3).

**The subject is unreachable by its own front door, and that is the design constraint.**
`AutoCook` (workshop 3388721641) is 10 client-only Lua files whose cooking pipeline is entered
ONLY from a context-menu option (`common/.../AutoCook_RISCookMenuInsertion.lua:87`), i.e. from a
right-click -- and nothing on the shipped bus clicks, presses a key or calls `triggerEvent`. So
this session measures the READ side and the LOAD-TIME state, and the one question it can answer
that no static read can is **the `common/`-vs-version-directory merge rule**: the mod ships the
same three client Lua files in `common/` and in `42.13/`, and which physical copy the engine
actually ran is invisible from disk.

That rule is measured FOUR independent ways, and only the fourth can name the winner:

  M1  the loader's own `mod "AutoCook" overrides <rel>` lines, on the SERVER log and on the
      CLIENT console, with line numbers. Prediction P1: exactly 5 on the server -- two
      translation JSONs (pass A, over vanilla) then three client Lua (pass B, over `common/`).
      A 3-line set with an icon tail instead would mean `getVersionDir()` resolved to `42/`.
  M2  the client's player-modData census carries `AutoCook:table` at baseline. CORRECTED by the
      Task 2 review: the `common/` copy of `AutoCook.lua` writes the same key at the same line
      (`:38`), one line BEFORE its B41-era `HasTrait` call at `:39`, so a green row proves
      `common/` RAN (the key is reached only through `addCharacterPageTab`, which exists only in
      `common/`) and that the require chain completed -- it does NOT identify the winner.
  M3  `text.get UI_AutoCookMode` -> "Cooking diet: " -- the Translator half, plus two vanilla
      controls (P7) that falsify "the mod's same-named ContextMenu.json / UI.json displaced
      vanilla's".
  M4  `lua.global` (the H4 command added in this slice's harness-prep commit) on both sides.
      `AutoCook.acceptIngredient` and `AutoCook.baseAcceptsSpice` exist ONLY in
      `42.13/.../AutoCook.lua` (`:245`, `:234`); the `common/` copy of that file defines neither
      and is otherwise a strict subset. Their presence is version-wins; their absence beside a
      present `AutoCook.selectPreferedFood` (a `common/`-ONLY file) is common-wins.

**Why every read is wall-bracketed** (pass-2 lesson, kept even though nothing here decays):
the two sides of a snapshot are separate bus round trips ~1 s apart, so a key seen on one side
and not the other inside a transmit's push window is a LATENCY reading and not a desync. Only
the baseline pair -- taken before anything is transmitted -- grades as authority. The CLIENT
half is read first at every tag for the same reason pass 2 gives.

**The baselines are TIMED, not time-invariant** (pass 2 measured it): the server's player
modData is EMPTY at join and gains the four vanilla fitness keys ~30 s in. So there are two
baseline pairs -- one taken as close to `client_ready` as the bus allows, one at >= 40 s past
`session_ready` -- and every census records its own wall offset against `session_ready`.

**World changes: none to restore.** No `settimespeed`, no sandbox write. The planted modData key
and the RCON-spawned Steak live in this run's copy of the fixture (`fx.restore_server` /
`restore_client` into `run_dir`). `lua.reload` is NEVER sent: AutoCook's three
`ISCharacterInfoWindow` wrappers are non-idempotent and a second execution stacks a second Cook
tab (notes Q4 / D4).

Never raises through teardown; the artifact is copied byte-for-byte after the session.
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
from pzt.session import (Timeline, grep_file, make_client, make_server,     # noqa: E402
                         teardown, verify)

MOD = "AutoCook"
PROFILE = "teardown-autocook"
USER = "admin"
ACCEPTANCE_RUN = "run-20260911-001251"   # PASS, both [[verify]] rows ok=True, 0 server errors

MIRROR_WAIT = 3.0        # > the 1 Hz PlayerStatsPacket window (every prior slice's number)
LAZY_WAIT = 40.0         # s past session_ready for the LATE baseline: pass 2 saw the server's
                         # four vanilla fitness keys appear between +22 s and +33.4 s
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory (s01/s02/s05)
TICK_WAIT = 10.0         # the carrier probe's window, as pass 2's A2 used

# Five ZERO-ARGUMENT getters that are on IsoPlayer, comma-joined and whitespace-free. This list
# is thin ON PURPOSE and the thinness is a finding, not an omission: AutoCook reads NOTHING off
# IsoPlayer with a zero-argument getter -- its player-facing calls are hasTrait(CharacterTrait),
# getPerkLevel(Perks.Cooking) and isKnownPoison(item), all of which take an argument, and
# `witness.fields` invokes TK.call(subject, name) with no trailing arguments
# (PZTestKit_Core.lua:687), so an argument-taking getter is reached with none and the Kahlua
# raise is as uncatchable as a nil call. Everything else it reads hangs off getNutrition(), i.e.
# the Nutrition object, which witness.fields cannot hop to -- those come from nutrition.get.
# So these five are a CONTROL that the subject resolved and that both sides are looking at the
# same character, and nothing more.
FIELDS = "getUsername,getInventoryWeight,getMaxWeight,isDead,isGodMod"
FIELD_COUNT = 5

PLAYER_SCOPE = f"player:{USER} *"
# One top-level key holding a nested table, so the census (`*`) and a dotted read of the leaves
# answer different questions: the census says the key exists, the dotted read says what is IN it.
# Predicted (P9): the table is EMPTY on a fresh character -- AutoCook.init creates it at
# 42.13/.../AutoCook.lua:38 and writes AutoCraftIngredients into it at :45 -- so every leaf but
# that one should land in `missing`, and the leaves' real values live on the Lua GLOBAL instead.
AUTOCOOK_KEYS = (f"player:{USER} AutoCook AutoCook.CookMode AutoCook.MaxSpices "
                 "AutoCook.UseRotten AutoCook.SmartSpices AutoCook.PrioritizeVariety "
                 "AutoCook.MaxDuplicate AutoCook.CompleteExistingMeal "
                 "AutoCook.AutoCraftIngredients")
PROBE_KEY, PROBE_VALUE = "AutoCookProbe", "7"     # a TOP-LEVEL sentinel: `moddata.set` is
                                                  # getModData()[argv[1]] = argv[2]
                                                  # (PZTestKit_Client.lua:86-89) and cannot
                                                  # write a nested path
KEYS = f"{PLAYER_SCOPE} | {AUTOCOOK_KEYS} | (planted: {PROBE_KEY})"
KEYS_NOTE = ("moddata_keys is a DISPLAY string: the ` | ` joins three separate probes for the "
             "reader and is not a bus token.")

# Per-SCOPE exclusion sets (pass-1 precedent, docs/decisions.md:133). Applying the item set to a
# player census would report vanilla's own keys as findings, and vice versa.
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}
VANILLA_ITEM_KEYS = {"customName", "Tooltip"}

# ---- M4: the names, why each one is asked for, and which tree it lives in --------------------
# Checked on disk this task against both copies of every file (`grep -n "^function AutoCook[.:]"`):
# 42.13/AutoCook.lua is a strict SUPERSET of common/AutoCook.lua -- it adds baseAcceptsSpice
# (:234) and acceptIngredient (:245) and removes nothing -- so those two are the only Lua-global
# discriminators the subject has. AutoCook_AutoCraftRecipes.lua and ISCharacterCook.lua differ
# across trees only INSIDE existing functions and define no new global, so they discriminate
# nothing.
GLOBALS = (
    ("TK.version", "control",
     "TK is a global on purpose (PZTestKit_Core.lua:2). MUST resolve to 1 on BOTH sides: a "
     "resolved=false here means the _G walk is broken, not that a mod global is absent."),
    ("ISContinue", "common-only file",
     "common/media/lua/client/ISContinue.lua:4. Absent => common/ never ran and the mod is inert."),
    ("addCharacterPageTab", "common-only file",
     "common/.../ISCharacterInfoWindow_AddTab.lua:2. The only route to the modData key M2 reads."),
    ("ISCharacterCook", "both trees",
     "ISCharacterCook.lua:5 in BOTH copies -- present either way, so NOT a discriminator."),
    ("AutoCook", "both trees",
     "the config table itself; keyCount is the reading (23 file-scope scalars + the methods of "
     "every AutoCook_* file that ran)."),
    ("AutoCook.selectPreferedFood", "common-only file",
     "common/.../AutoCook_Diets.lua:21. A common-ONLY FILE, so it proves that file ran whichever "
     "copy of AutoCook.lua won -- it is not the version discriminator."),
    ("AutoCook.acceptIngredient", "42.13 only",
     "42.13/.../AutoCook.lua:245, ABSENT from the common copy. THE discriminator: present = "
     "version-wins."),
    ("AutoCook.baseAcceptsSpice", "42.13 only",
     "42.13/.../AutoCook.lua:234, ABSENT from the common copy. The second discriminator; it must "
     "agree with the first; a disagreement would mean the copies were merged per-FUNCTION."),
    ("AutoCook.CookMode", "both trees",
     "P9: file-scope default 1 at :22 in both copies. 5 would mean the fixture character is a "
     "Nutritionist (init :38-41 sets the GLOBAL only, never modData)."),
    ("AutoCook.Verbose", "both trees",
     "P9 and the H4 guard: the value is the boolean FALSE, which is exactly why presence is "
     "tested with `v == nil` and never with `if not v`."),
    ("AutoCook.MaxSpices", "both trees",
     "P9 and the H4 guard: the value is -1."),
)

# ---- the carrier probe carried from passes 1 and 2 (amendment 9) -----------------------------
# Pass 1 measured a client item copy that did NOT move while the server's did (patterns.md:148);
# pass 2's appendix A2 pinned a Steak's heat at 2.0 -- ABOVE the 1.6 cooking gate -- and the
# client copy DID move, bit-identically to the server's. The two readings are reconciled if the
# carrier is the per-game-minute sendItemStats inside Food.update's COOKING branch
# (@86-@103 L377-L379, gated @49-@71). This probe pins heat BELOW that gate: if the client now
# freezes while the server decays, the cooking branch is the carrier and pass 1 and pass 2 agree.
# If both sides still move together, something else pushes and the question stays open.
ITEM = "Base.Steak"
HEAT_BELOW_GATE = "1.2"          # the gate is 1.6
TICK_FIELDS = "getHeat,getCookingTime,getContainer"
TICK_FIELD_COUNT = 3

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"

# session.grep_file takes a COMPILED regex and the escaping is the caller's job (pass-2 lesson,
# session.py:51). MOD_RX must NOT be re.escape("AutoCook") as pass 1's driver had it
# (td1_longtermpreservation4220.py:116) -- that also matches the mod's own path lines. With the
# tighter text the two greps are disjoint: format string #1668 is 'loading \x01' and #1670 is
# 'mod "\x01" overrides \x01', so `loading AutoCook` never contains `mod "AutoCook" overrides`.
# limit=12 and not 5: 5 saturates at exactly the predicted number, so a 6th line -- the single
# most informative falsifier P1 has -- would be truncated away and read as a pass.
MOD_RX = re.compile(re.escape('mod "AutoCook" overrides'))
LOADING_RX = re.compile(re.escape("loading AutoCook"))
# A raise at HasTrait / getTypeString is the common-wins signature: both members were removed in
# 42.20.4 and only the common/ copies still call them (AutoCook.lua:39, ISCharacterCook.lua:50).
NILCALL_RX = re.compile(r"tried to call nil|HasTrait|getTypeString")

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("td3")
path = os.path.join(run_dir, "teardown-autocook.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "mod": MOD,
    "workshop_item": prof.items.get(MOD),
    "subject": f"player {USER} (the mod owns no item and no script; it ships no media/scripts)",
    "user": USER,
    "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "fields": FIELDS,
    "field_count_expected": FIELD_COUNT,
    "moddata_keys": KEYS,
    "moddata_note": KEYS_NOTE,
    "vanilla_player_keys": sorted(VANILLA_PLAYER_KEYS),
    "vanilla_item_keys": sorted(VANILLA_ITEM_KEYS),
    "world_changes": "none to restore -- no settimespeed, no sandbox write, no lua.reload (the "
                     "mod's three ISCharacterInfoWindow wrappers are non-idempotent). The "
                     "planted modData key and the RCON-spawned Steak live in this run's copy of "
                     "the fixture.",
    "snapshots": [], "steps": [], "phase2": [], "notes": [KEYS_NOTE],
}


def wall():
    return round(time.time() - t0, 3)


def probe(side, cmd, args, timeout=20):
    """One read, with its own wall bracket, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the `sent` branch -- the older client-witness shape (ack `sent`, the reply written by
        OnServerCommand into a result doc). Every command used here answers INLINE, so it is
        DORMANT; `dormant_sent_branch` records it if it ever fires.
      * the re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A
        string where a table belongs is re-asked ONCE and BOTH readings are kept.
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


def snapshot(tag, c):
    """One paired reading, CLIENT FIRST at every tag (pass-2 ordering rule: the sign of any
    cross-side comparison follows the read order, and the earliest client read after an action is
    the one that bounds the mirror window)."""
    row = {"tag": tag, "wall": wall()}
    for name, side in (("client", c), ("server", server)):
        md = probe(side, "witness.moddata", PLAYER_SCOPE)
        f = probe(side, "witness.fields", f"player {USER} {FIELDS}")
        row[name] = {
            "moddata_player": md,
            "census_player": census_row(md, name),
            "autocook_keys": probe(side, "witness.moddata", AUTOCOOK_KEYS),
            "fields": f,
            "field_count": f.get("count") if isinstance(f, dict) else None,
            "field_count_ok": (f.get("count") == FIELD_COUNT) if isinstance(f, dict) else False,
            "nutrition": probe(side, "nutrition.get", "" if name == "client" else USER),
        }
    row["wall_done"] = wall()
    out["snapshots"].append(row)
    tl.mark("snapshot", tag=tag, took=round(row["wall_done"] - row["wall"], 2),
            client=row["client"]["census_player"]["keyCount"],
            server=row["server"]["census_player"]["keyCount"])
    save(path, out, tl, server)          # evidence on disk before the next phase can wedge
    return row


def census_pair(tag, c, note):
    """Both sides' player-modData census at one moment, client first, with the difference sets --
    which is what the transmit phase grades: a key on the server the client lacks is what a
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


def grep_numbered(path_, rx, limit=12):
    """`session.grep_file` with the LINE NUMBER kept: which loader lines arrived, and in what
    order, is the M1 evidence, and order is unreadable without the numbers."""
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


def override_tails(hits):
    """The relative path each `mod "AutoCook" overrides <rel>` line names, in log order. P1's
    whole reading is the TAIL SET: 2 translation JSONs then 3 client Lua = the wiki's rule with
    getVersionDir() == 42.13/; one `autocookicon.png` tail and no client Lua = 42/."""
    tails = []
    for h in hits:
        t = str(h.get("text", ""))
        i = t.find("overrides ")
        tails.append(t[i + len("overrides "):].strip() if i >= 0 else None)
    return tails


def item_read(side, side_name, names, count):
    r = probe(side, "witness.fields", f"item {USER}/{ITEM} {names}")
    return {"side": side_name, "type": ITEM, "reply": r,
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
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)

    # ================= M1 -- the loader's own override lines ============================
    # Read from FILES, so this costs no bus time and cannot delay the join-time baseline below.
    srv_hits = grep_numbered(server.log_path, MOD_RX, limit=12)
    cli_hits = grep_numbered(c.console, MOD_RX, limit=12)
    out["M1_overrides"] = {
        "question": "which relative paths did the version dir take from common/, and which did "
                    "common/ take from vanilla?",
        "server_log": {"path": os.path.relpath(server.log_path, run_dir), "hits": srv_hits,
                       "count": len(srv_hits), "tails": override_tails(srv_hits)},
        "client_console": {"path": os.path.relpath(c.console, run_dir), "hits": cli_hits,
                           "count": len(cli_hits), "tails": override_tails(cli_hits)},
        "prediction": "P1: exactly 5 on the server -- media/lua/shared/translate/en/"
                      "{contextmenu,ui}.json (pass A, over vanilla) then media/lua/client/"
                      "{autocook,autocook_autocraftrecipes,ischaractercook}.lua (pass B, over "
                      "common/). limit=12 so a 6th line is visible rather than truncated.",
        "falsifiers": {
            "3 lines, client Lua only": "vanilla's media/** is not in activeFileMap when mods "
                                        "load -- a startup-order fact",
            "3 lines, one with an icon tail and NO client Lua": "getVersionDir() resolved to 42/ "
                                                                "(which ships only the two PNGs, "
                                                                "and the print gate filters any "
                                                                "rel ending poster.png)",
            "0 lines": "the version pass did not see common/'s keys -- the wiki rule is wrong",
        },
    }
    out["mod_log_lines_server"] = grep_file(server.log_path, MOD_RX, limit=12)
    out["loading_lines"] = {"server": grep_numbered(server.log_path, LOADING_RX, limit=6),
                            "client": grep_numbered(c.console, LOADING_RX, limit=6)}
    # The mod's OWN prints do not exist: they are all behind `if AutoCook.Verbose then` and
    # AutoCook.Verbose = false at 42.13/.../AutoCook.lua:6. So tier (b) is unavailable for this
    # subject and the only Lua-error grep that matters is the common-wins signature.
    out["nilcall_lines"] = {"client": grep_numbered(c.console, NILCALL_RX, limit=8),
                            "server": grep_numbered(server.log_path, NILCALL_RX, limit=8),
                            "reading": "a raise naming HasTrait or getTypeString is the "
                                       "COMMON-WINS signature: both members were removed in "
                                       "42.20.4 and only the common/ copies still call them "
                                       "(common/AutoCook.lua:39, common/ISCharacterCook.lua:50)."}
    tl.mark("greps", overrides_server=len(srv_hits), overrides_client=len(cli_hits))

    # ================= the JOIN-TIME baseline, taken as early as the bus allows ==========
    snapshot("baseline_join", c)

    # ================= M3 -- the Translator half, with P7's two vanilla controls =========
    out["M3_translations"] = {
        "question": "did the Translator read common/media/lua/shared/Translate/EN/UI.json?",
        "mod_key": probe(c, "text.get", "UI_AutoCookMode"),
        "expected": "Cooking diet: ",
        "controls": {k: probe(c, "text.get", k)
                     for k in ("ContextMenu_Destroy", "UI_Yes")},
        "controls_reading": "P7: both must still answer their VANILLA text. Either one missing "
                            "would mean the mod's same-named ContextMenu.json / UI.json "
                            "displaced vanilla's -- i.e. some consumer resolves translations "
                            "through activeFileMap after all, which the static read says is not "
                            "how Translator.tryFillMapFromFile works.",
    }
    tl.mark("M3", miss=out["M3_translations"]["mod_key"].get("miss")
            if isinstance(out["M3_translations"]["mod_key"], dict) else "?")

    # ================= M4 -- which physical AutoCook.lua won ============================
    out["M4_globals"] = {
        "question": "which copy of AutoCook.lua did the engine run?",
        "command": "lua.global (H4, added in this slice's harness-prep commit)",
        "names": [{"name": n, "tree": tree, "why": why} for n, tree, why in GLOBALS],
        "client": {}, "server": {},
    }
    for side_name, side in (("client", c), ("server", server)):
        for name, _tree, _why in GLOBALS:
            out["M4_globals"][side_name][name] = probe(side, "lua.global", name)
        save(path, out, tl, server)
    tl.mark("M4", read=len(GLOBALS) * 2)

    # ================= the LATE baseline, past the server's lazy fitness write ===========
    while wall() - out["session_ready_wall"] < LAZY_WAIT:
        time.sleep(0.5)
    snapshot("baseline_late", c)

    # ================= the action -- menu row 3, "writes player modData" ================
    a1 = step("plant_client", c, "moddata.set", f"{PROBE_KEY} {PROBE_VALUE}")
    out["plant"] = {k: a1[k] for k in ("wall_before", "wall_after", "ack")}
    census_pair("p2a_after_set", c,
                "the client's own write has not crossed (spike S6): a client modData write "
                "reaches the server ONLY after transmitModData (patterns.md:125)")
    a2 = step("t_action", c, "moddata.transmit", "")
    out["t_action"] = {k: a2[k] for k in ("wall_before", "wall_after", "ack")}
    snapshot("t0", c)
    time.sleep(max(0.0, MIRROR_WAIT - (wall() - a2["wall_after"])))
    snapshot("t+3s", c)

    base_j = out["snapshots"][0]
    base_l = out["snapshots"][1]
    last = out["snapshots"][-1]
    out["transmit_reading"] = {
        "planted_on_client": PROBE_KEY,
        "client_before": base_l["client"]["census_player"]["keyNames"],
        "server_before": base_l["server"]["census_player"]["keyNames"],
        "client_after": last["client"]["census_player"]["keyNames"],
        "server_after": last["server"]["census_player"]["keyNames"],
        "probe_key_crossed": PROBE_KEY in (last["server"]["census_player"]["keyNames"] or []),
        "autocook_crossed": "AutoCook" in (last["server"]["census_player"]["keyNames"] or []),
        "server_census_equals_client": (set(last["server"]["census_player"]["keyNames"] or []) ==
                                        set(last["client"]["census_player"]["keyNames"] or [])),
        "reading": "CORROBORATION of pass 2's wipe-and-replace reading with a second subject, "
                   "not a discovery. What is subject-specific: if the server census gains "
                   "AutoCook here having not had it at either baseline, AutoCook's 'client-only' "
                   "settings are private only until SOMEONE ELSE transmits -- a compatibility "
                   "fact for our own mod. The mod itself has 9 getModData() sites per tree and "
                   "ZERO transmitModData, so it never causes this crossing on its own.",
    }
    out["baseline_timing"] = {
        "rule": "pass 2 measured the server's player modData EMPTY at join and carrying the four "
                "vanilla fitness keys from ~30 s in, so a server keyCount is only readable "
                "beside its wall offset against session_ready.",
        "join": {"client": base_j["client"]["census_player"]["keyCount"],
                 "server": base_j["server"]["census_player"]["keyCount"],
                 "client_since_ready": base_j["client"]["census_player"]["since_session_ready"],
                 "server_since_ready": base_j["server"]["census_player"]["since_session_ready"]},
        "late": {"client": base_l["client"]["census_player"]["keyCount"],
                 "server": base_l["server"]["census_player"]["keyCount"],
                 "client_since_ready": base_l["client"]["census_player"]["since_session_ready"],
                 "server_since_ready": base_l["server"]["census_player"]["since_session_ready"]},
        "prediction": "P3/P4: client 6 at both (4 vanilla fitness + hotbar + AutoCook); server 0 "
                      "at join and 4 later, with AutoCook absent from the server at both.",
    }

    # ================= M -- the pass-1/pass-2 carrier probe (amendment 9) ================
    ok_add, add_reply = server.rcon(f'additem "{USER}" "{ITEM}" 1')
    out["carrier"] = {"question": "is the per-game-minute sendItemStats inside Food.update's "
                                  "COOKING branch the carrier that made pass 2's client copy "
                                  "move while pass 1's froze?",
                      "gate": "Food.update's cooking branch is gated at heat >= 1.6; this probe "
                              "pins heat at " + HEAT_BELOW_GATE + ", BELOW it.",
                      "spawn": {"ok": ok_add, "reply": str(add_reply)[:200],
                                "note": "RCON, not a bus command: a CLIENT AddItem is invisible "
                                        "to the server (spike S6)"}}
    tl.mark("rcon_additem", ok=ok_add)
    waits = []
    for attempt in range(3):
        time.sleep(SPAWN_WAIT)
        seen = probe(c, "witness.fields", f"item {USER}/{ITEM} getID")
        waits.append({"attempt": attempt + 1, "wall": wall(),
                      "resolved": seen.get("resolved") if isinstance(seen, dict) else None})
        if isinstance(seen, dict) and seen.get("resolved"):
            break
    out["carrier"]["spawn_wait"] = waits
    out["carrier"]["pin"] = step("pin_heat", server, "item.set",
                                 f"{USER} {ITEM} heat {HEAT_BELOW_GATE}")["ack"]
    r1 = item_read(c, "client", TICK_FIELDS, TICK_FIELD_COUNT)
    s1 = item_read(server, "server", TICK_FIELDS, TICK_FIELD_COUNT)
    # The item-scope census, with the ITEM exclusion set -- the one place the second set is used.
    im_c = probe(c, "witness.moddata", f"item:{USER}/{ITEM} *")
    im_s = probe(server, "witness.moddata", f"item:{USER}/{ITEM} *")
    time.sleep(TICK_WAIT)
    r2 = item_read(c, "client", TICK_FIELDS, TICK_FIELD_COUNT)
    s2 = item_read(server, "server", TICK_FIELDS, TICK_FIELD_COUNT)
    cf1, cf2 = r1["fields"] or {}, r2["fields"] or {}
    sf1, sf2 = s1["fields"] or {}, s2["fields"] or {}
    out["carrier"].update({
        "window_s": TICK_WAIT,
        "client_read_1": r1, "client_read_2": r2,
        "server_read_1": s1, "server_read_2": s2,
        "client_moved": {k: {"first": cf1.get(k), "second": cf2.get(k),
                             "changed": cf1.get(k) != cf2.get(k)}
                         for k in ("getHeat", "getCookingTime")},
        "server_moved": {k: {"first": sf1.get(k), "second": sf2.get(k),
                             "changed": sf1.get(k) != sf2.get(k)}
                         for k in ("getHeat", "getCookingTime")},
        "item_census": {"client": census_row(im_c, "client", vanilla=VANILLA_ITEM_KEYS),
                        "server": census_row(im_s, "server", vanilla=VANILLA_ITEM_KEYS),
                        "note": "the ITEM exclusion set ({customName, Tooltip}) is applied here "
                                "and NOWHERE else; the player censuses use the five vanilla "
                                "player keys instead."},
        "container_note": "PRESENCE and within-side stability only. ItemContainer.toString() is "
                          "getType() + String.valueOf(getParent()) and the parent's toString() "
                          "ends in an identity hash, so the full strings must NEVER be compared "
                          "across sides.",
        "reading": "client frozen while the server moved = the cooking branch's sendItemStats is "
                   "the carrier, and pass 1's freeze and pass 2's moving copy are reconciled. "
                   "Both sides moving = something else pushes and the question stays open. "
                   "NEITHER side moving = the pin itself is below every tick's threshold and the "
                   "probe measured nothing.",
    })
    save(path, out, tl, server)

    # ================= the readings, stated as verdicts ==================================
    def resolved(side_name, name):
        r = out["M4_globals"][side_name].get(name)
        return bool(r.get("resolved")) if isinstance(r, dict) else None

    cli_accept = resolved("client", "AutoCook.acceptIngredient")
    cli_spice = resolved("client", "AutoCook.baseAcceptsSpice")
    cli_pref = resolved("client", "AutoCook.selectPreferedFood")
    cli_cont = resolved("client", "ISContinue")
    if cli_cont is False:
        m4 = "neither -- common/ never ran and the mod is inert"
    elif cli_accept and cli_spice:
        m4 = "version-wins (42.13/ AutoCook.lua)"
    elif cli_pref and not cli_accept:
        m4 = "common-wins (the inverse of the wiki rule)"
    else:
        m4 = "indeterminate -- read the per-name table"
    tails = out["M1_overrides"]["server_log"]["tails"]
    lua_tails = [t for t in tails if t and t.endswith(".lua")]
    json_tails = [t for t in tails if t and t.endswith(".json")]
    if len(tails) == 5 and len(lua_tails) == 3 and len(json_tails) == 2:
        m1 = "version-wins: 2 translation JSONs (pass A over vanilla) + 3 client Lua (pass B " \
             "over common/), which is the wiki's rule with getVersionDir() == 42.13/"
    elif any(t and t.endswith(".png") for t in tails):
        m1 = "an icon tail is present -- getVersionDir() did NOT resolve to 42.13/"
    elif not tails:
        m1 = "neither -- the loader printed no overrides line at all"
    else:
        m1 = "indeterminate -- read the tail list"
    md_reply = out["M4_globals"]["client"].get("AutoCook")
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "verify_keyCount": (out["verify"][1]["got"].get("keyCount")
                            if len(out.get("verify", [])) > 1 and
                            isinstance(out["verify"][1].get("got"), dict) else None),
        "M1_overrides_server": len(tails), "M1_tails": tails, "M1_verdict": m1,
        "M2_autocook_key_client_at_join":
            "AutoCook" in (base_j["client"]["census_player"]["keyNames"] or []),
        "M2_autocook_key_server_at_join":
            "AutoCook" in (base_j["server"]["census_player"]["keyNames"] or []),
        "M2_verdict": "common/ ran and the require chain completed (it does NOT name the winner)",
        "M3_miss": out["M3_translations"]["mod_key"].get("miss")
        if isinstance(out["M3_translations"]["mod_key"], dict) else None,
        "M3_text": out["M3_translations"]["mod_key"].get("text")
        if isinstance(out["M3_translations"]["mod_key"], dict) else None,
        "M3_controls": {k: (v.get("text") if isinstance(v, dict) else v)
                        for k, v in out["M3_translations"]["controls"].items()},
        "M4_client": {n: resolved("client", n) for n, _t, _w in GLOBALS},
        "M4_server": {n: resolved("server", n) for n, _t, _w in GLOBALS},
        "M4_autocook_keyCount_client": md_reply.get("keyCount") if isinstance(md_reply, dict)
        else None,
        "M4_verdict": m4,
        "nilcall_hits_client": len(out["nilcall_lines"]["client"]),
        "transmit_probe_key_crossed": out["transmit_reading"]["probe_key_crossed"],
        "transmit_autocook_crossed": out["transmit_reading"]["autocook_crossed"],
        "transmit_server_equals_client": out["transmit_reading"]["server_census_equals_client"],
        "carrier_client_moved": any(v["changed"] for v in out["carrier"]["client_moved"].values()),
        "carrier_server_moved": any(v["changed"] for v in out["carrier"]["server_moved"].values()),
        "field_count_ok": all(r[s]["field_count_ok"] for r in out["snapshots"]
                              for s in ("client", "server")),
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
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "teardown-autocook.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"),
                  "baseline_timing": out.get("baseline_timing"),
                  "transmit_reading": out.get("transmit_reading"),
                  "error": out.get("error")}, indent=1)[:6000])
