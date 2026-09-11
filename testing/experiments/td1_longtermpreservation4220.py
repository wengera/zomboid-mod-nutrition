"""Teardown 1: SKITTLE_LongTermPreservation4220 measured on a live dedicated server + a real
client (slice 09 of the 09-11 teardown wave).

Paired snapshots of the SAME item on both sides around the mod's one reachable key action, so
the teardown's MP section is measured rather than read off the jar. Never raises through
teardown; the artifact is copied byte-for-byte after the session.

**The subject.** `Skittles.CuredPork`, an item this mod adds, spawned SERVER-side by RCON
`additem` (a client `AddItem` is invisible to the server, spike S6). The mod's whole nutrition
surface is one Lua function, `OnCookedTest` (`42.20/media/lua/server/recipe_meats.lua:34-53`),
reached only from `Food.update()`'s cook transition. Nothing on the bus executes a
`craftRecipe`, so the mod's `onCreate` / `onTest` hooks stay unreachable and stay C-grade.

**The action is the LAST GATE FLIP, not `item.update`.** `Food.update`'s cook block is gated on
`isCookable && !frozen` (`@49-@60`), `heat > 1.6` (`@63-@71`), `GameTime.getMinutes() !=
lastCookMinute` (`@86`) and `!cooked && !burnt && cookingTime > minutesToCook` (`@186-@221`) --
none of them side-gated -- and BOTH sides tick their own inventory items through
`IsoGameCharacter.updateInternal @1911-@1923` -> `recursiveItemUpdater` -> `InventoryItem
.update()`, with no `GameServer.server` / `GameClient.client` guard anywhere on that path. So
once the last gate flips, whichever copy ticks next runs the transition. The bus's
`item.update` is therefore the WITNESS, not the action: its `before.cooked` is the record of
whether the server's own tick had already fired the hook.

**Three outcomes, and the timeline is what separates them** (notes s"The one key action",
amendment 12b):
  (a) the CLIENT ran its own transition -- visible as `isCooked true` in the step-3b client
      read, taken while the server's copy is still blocked, or as a client console line
      stamped before `t_action`. `lua/server/` does not load client-side, so its `OnCooked`
      resolves to nil there and the reading also measures what `LuaCaller.protectedCallVoid`
      does with a nil hook on 42.20.4;
  (b) the SERVER's bus call ran it -- `item.update`'s `before.cooked` is false;
  (c) the SERVER's own tick ran it first, on a game-minute rollover between the preconditions
      and the action -- `before.cooked` true, with the console prints stamped before
      `t_action`. `serverWorldAge` is read off EVERY ack (x60 = the game minute) so a rollover
      between two commands is detectable rather than inferred.
(a) and (b)/(c) are independent events on two different copies of the item: both halves can be
positive in one run.

**Two timing clauses built into the sequence** (amendment 12): heat decays -- `Food.update`
calls `updateTemperature()` BEFORE the heat gate on every tick, ~0.03/s, so a pinned `heat 2.0`
falls under the 1.6 gate in ~13 real seconds; the guard read therefore asserts `heat > 1.6` and
the pin is REFRESHED immediately before the action. And the guard read itself moved to BEFORE
the action: after it, `cooked true` no longer distinguishes "additem spawned it cooked" from
"the server's tick won".

**What the numbers are compared with.** Every field is a Java float32 widened to a double on
its way through Kahlua, so `getHungChange` arrives as -0.42000001668930054 on both sides. The
rule (notes s"Read-back"): |server - client| <= 1e-6 is SYNCED; the graded desyncs are whole
values apart (53 vs 1e9, true vs false). A last-digit gap on `getActualWeight` / `getWeight` is
evidence that the two sides took different arms of `Food.getActualWeight`, not a failure.

**World changes: none to restore.** No `settimespeed`, no sandbox write. Every write is to this
run's own COPY of the fixture (`fx.restore_server` / `restore_client` into `run_dir`): the item
setters, and the +10 Cooking XP the transition may grant the admin character.
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

MOD = "SKITTLE_LongTermPreservation4220"
PROFILE = "teardown-longtermpreservation4220"
USER = "admin"
ITEM = "Skittles.CuredPork"
PERK = "Cooking"

MIRROR_WAIT = 3.0        # 3 s > the 1 Hz PlayerStatsPacket window (every prior slice's number)
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory (s01/s02/s05)
TOL = 1e-6               # the notes' float32 tolerance rule: <= this apart is SYNCED

# 26 zero-argument getters, comma-joined and WHITESPACE-FREE: `splitArgs` splits the command
# line on `%S+` and `witness.fields` reads argv[3] only, so a space here would silently drop
# every getter after it. Under TK.WITNESS_MAX = 32; the reply's `count` is asserted == 26.
# `getID` is in the list so both sides can be shown to be reading the SAME instance.
FIELDS = ("getCalories,getProteins,getLipids,getCarbohydrates,getHungChange,getHungerChange,"
          "getBaseHunger,getThirstChange,getOffAge,getOffAgeMax,getAge,isFresh,isRotten,"
          "isCooked,isBurnt,isCookable,getCookingTime,getHeat,getMinutesToCook,"
          "getMinutesToBurn,getActualWeight,getActualWeightUnmodded,getWeight,isCustomWeight,"
          "getID,getFullType")
FIELD_COUNT = 26

# LTP writes NO modData (Task 1 Q5: zero getModData / transmitModData / ModData. in the whole
# live tree), so the modData probe is a CENSUS, not a key list. Keys are SPACE-separated after
# an explicit scope, and `*` is the census wildcard -- never `item:` or `global:` with a
# trailing colon and no name (that was slice 08's parked defect; slice 09 gated it, and this
# driver still never sends it). Any key on either side beyond `customName` falsifies the static
# read and is the headline finding. `customName` itself is EXCLUDED from every comparison: it
# is an `InventoryItem.setCustomName` deserialisation side effect with six vanilla call sites.
ITEM_SCOPE = f"item:{USER}/{ITEM} *"
PLAYER_SCOPE = f"player:{USER} *"
# A DISPLAY string for the artifact header -- the ` | ` is a human separator, NOT a bus token.
# The two probes are sent separately, as ITEM_SCOPE and PLAYER_SCOPE; nothing ever sends KEYS.
KEYS = f"{ITEM_SCOPE} | {PLAYER_SCOPE}"
KEYS_NOTE = ("moddata_keys is a DISPLAY string: the ` | ` joins the two scopes for the reader and "
             "is not a bus token. The probes are sent separately as `" + ITEM_SCOPE + "` and `" +
             PLAYER_SCOPE + "`.")
# Two exclusion sets, one per scope. Applying the ITEM list to the PLAYER census reports all four
# vanilla fitness keys as `beyondVanilla`, which is the opposite of what that field means.
VANILLA_ITEM_KEYS = {"customName"}
VANILLA_PLAYER_KEYS = {"fitnessMod", "fitnessUpTimer", "strengthMod", "strengthUpTimer", "hotbar"}

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_RX = re.compile(re.escape(MOD))
# recipe_meats.lua:35,37,41,52 -- the four prints OnCookedTest makes, quoted exactly. Their
# presence in the SERVER console is direct evidence the Lua hook ran there; their TIMESTAMP
# against t_action is what says whether the server's own tick or the bus call reached
# Food.update first.
HOOK_STRINGS = ["changing da meat", "post cookable", "meat change days", "meat done"]
HOOK_RX = re.compile("|".join(re.escape(s) for s in HOOK_STRINGS), re.I)
# A client that reached the transition itself calls a NIL OnCooked through
# LuaCaller.protectedCallVoid (`lua/server/` does not load client-side): expect none of the
# four prints, and possibly a Kahlua error line at that timestamp.
CLIENT_ERR_RX = re.compile("|".join(re.escape(s) for s in HOOK_STRINGS) +
                           r"|OnCookedTest|tried to call nil|protectedCallVoid|LuaCaller",
                           re.I)

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("td1")
path = os.path.join(run_dir, "teardown-longtermpreservation4220.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "mod": MOD,
    "workshop_item": prof.items.get(MOD),
    "subject": ITEM,
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
    "moddata_note": "LTP writes no modData; both probes are censuses (`*`). customName is "
                    "excluded from every key comparison (vanilla setCustomName side effect).",
    "tolerance": {"rule": "|server - client| <= 1e-6 is SYNCED; a last-digit gap on "
                          "getActualWeight / getWeight is two arms of Food.getActualWeight, "
                          "not a desync", "value": TOL},
    "acceptance_run": "run-20260910-191842",
    "world_changes": "none to restore -- no settimespeed, no sandbox write; every write lands "
                     "in this run's copy of the fixture",
    "snapshots": [], "steps": [], "notes": [KEYS_NOTE],
}


def wall():
    return round(time.time() - t0, 3)


def probe(side, cmd, args, timeout=20):
    """One witness read, with its wall clock, recorded whatever comes back.

    Two guards, both inherited rather than invented:
      * the brief's `sent` branch -- slice 08's commands could have answered out-of-band, in
        the older client-witness shape (ack `sent`, reply written by OnServerCommand into a
        result doc). The SHIPPED commands answer inline, so this branch is DORMANT; it is kept
        because a future command may not, and `dormant_sent_branch` records if it ever fires.
      * s08's re-ask-once guard: `TK.writeKV` writes the ack file non-atomically and the poller
        reads it every 0.25 s, so `parse_ack` can degrade a table reply to a raw string. A
        string where a table belongs is re-asked ONCE and both readings are kept.
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
        # A non-dict SECOND reply has nowhere to carry `_probe`, so the re-ask evidence --
        # that this reading was degraded once and re-asked, and what the first reply said --
        # would be dropped on the one path where it matters most. Keep it beside the run.
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def step(name, side, cmd, args, timeout=30):
    """One SEQUENCED bus call: the ack, both wall clocks bracketing it, and the ack's own
    `serverWorldAge` / `gameMinute` lifted out. The wall bracket around the action step IS
    `t_action`; `serverWorldAge * 60` is the game minute the gate at `Food.update @86` reads,
    so a rollover between two steps is measured, not assumed."""
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
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
    arrives as a dict -- never test `== []`, and `keyCount` is the numeric emptiness test."""
    if not isinstance(reply, dict):
        return None
    k = reply.get("keys")
    if isinstance(k, list):
        return k
    if isinstance(k, dict):
        return [] if not k else None
    return None


def census_row(reply, side_name, vanilla=VANILLA_ITEM_KEYS):
    """The per-side item/player modData census, named by side (amendment 3: slice 08 ran the
    server only and its README marks the client half do-not-cite).

    `vanilla` is the exclusion set for THIS scope: the item list for an item census, the
    player list for a player one. One shared list makes `beyondVanilla` meaningless on the
    player scope, where the four fitness keys and `hotbar` are exactly what vanilla puts there.
    """
    ks = keys_of(reply)
    names = sorted(s.split(":")[0] for s in ks) if ks is not None else None
    extra = sorted(set(names or []) - vanilla) if names is not None else None
    return {"side": side_name,
            "resolved": reply.get("resolved") if isinstance(reply, dict) else None,
            "keyCount": reply.get("keyCount") if isinstance(reply, dict) else None,
            "count": reply.get("count") if isinstance(reply, dict) else None,
            "keys": ks, "keyNames": names,
            "beyondVanilla": extra,
            "error": reply.get("error") if isinstance(reply, dict) else reply}


def snapshot(tag, c):
    """One paired reading. The CLIENT is always read FIRST: every server `item.set` fires its
    own `sendItemStats` on the way out, so at `baseline` the client half has to be taken before
    anything is pushed, and after the action the earliest possible client reading is the one
    that bounds the mirror window."""
    row = {"tag": tag, "wall": wall()}
    for name, side in (("client", c), ("server", server)):
        f = probe(side, "witness.fields", f"item {USER}/{ITEM} {FIELDS}")
        row[name] = {
            "fields": f,
            "field_count": f.get("count") if isinstance(f, dict) else None,
            "field_count_ok": (f.get("count") == FIELD_COUNT) if isinstance(f, dict) else False,
            "moddata_item": probe(side, "witness.moddata", ITEM_SCOPE),
            "moddata_player": probe(side, "witness.moddata", PLAYER_SCOPE),
            "stats": ask(side, "stats.get", USER if name == "server" else ""),
        }
        row[name]["census_item"] = census_row(row[name]["moddata_item"], name,
                                              VANILLA_ITEM_KEYS)
        row[name]["census_player"] = census_row(row[name]["moddata_player"], name,
                                                VANILLA_PLAYER_KEYS)
    row["server"]["item_get"] = ask(server, "item.get", f"{USER} {ITEM}")
    row["wall_done"] = wall()
    out["snapshots"].append(row)
    tl.mark("snapshot", tag=tag, took=round(row["wall_done"] - row["wall"], 2))
    save(path, out, tl, server)          # evidence on disk before the next phase can wedge
    return row


def compare(tag):
    """Server vs client, getter by getter, under the tolerance rule. `synced` is the numeric
    test; `exact` says the two doubles are bit-equal, which is what the packet-copied fields
    (`getHungChange`, `getActualWeightUnmodded`) have to be, not merely close."""
    row = next((r for r in out["snapshots"] if r["tag"] == tag), None)
    if row is None:
        return None
    sf, cf = fields_of(row["server"]["fields"]), fields_of(row["client"]["fields"])
    if sf is None or cf is None:
        return {"tag": tag, "error": "no fields on one side",
                "server_fields": sf is not None, "client_fields": cf is not None}
    cmp_ = {"tag": tag, "getters": {}}
    for g in sorted(set(sf) | set(cf)):
        s, c = sf.get(g), cf.get(g)
        sn, cn = num(s), num(c)
        e = {"server": s, "client": c}
        if sn is not None and cn is not None:
            e["delta"] = sn - cn
            e["synced"] = abs(sn - cn) <= TOL
            e["exact"] = s == c
        else:
            e["synced"] = s == c
            e["exact"] = s == c
        cmp_["getters"][g] = e
    cmp_["same_instance"] = sf.get("getID") == cf.get("getID")
    cmp_["desynced"] = sorted(g for g, e in cmp_["getters"].items() if not e["synced"])
    return cmp_


try:
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mod_log_lines"] = grep_file(server.log_path, MOD_RX, limit=5)

    # ---- folder-name check (settles docs/testing/profiles.md OQ 6) --------------------
    mods_dir = os.path.join(run_dir, "server", "mods")
    ini = os.path.join(run_dir, "server", "Server", "pzt.ini")
    try:
        listing = sorted(os.listdir(mods_dir))
    except OSError as e:                             # noqa: BLE001 - recorded, not raised
        listing = [f"<{type(e).__name__}: {e}>"]
    mods_line = next((ln.strip() for ln in grep_file(ini, re.compile(r"^Mods="), limit=2)), None)
    out["folder_check"] = {
        "mods_dir": os.path.relpath(mods_dir, REPO).replace("\\", "/"),
        "listing": listing,
        "id_folder_present": MOD in listing,
        "source_folder_present": "LongTermPreservation4220" in listing,
        "mod_info_at_id": os.path.isfile(os.path.join(mods_dir, MOD, "42.20", "mod.info")),
        "ini_mods_line": mods_line,
        "predicted": "harness.install copies a profile `sources` entry to <mods_dir>/<mod id>, "
                     "so the folder is renamed from LongTermPreservation4220 to the declared id",
    }
    tl.mark("folder_check", listing=",".join(listing)[:80])

    # ---- join-time item census (amendment 9): the NUMBER, not the substring --------------
    v0 = out["verify"][0].get("got") if out["verify"] else None
    fbm = v0.get("foodByModule") if isinstance(v0, dict) else None
    out["items_census"] = {
        "foodByModule_Skittles": (fbm or {}).get("Skittles"),
        "expected": 14,
        "total": v0.get("total") if isinstance(v0, dict) else None,
        "food": v0.get("food") if isinstance(v0, dict) else None,
        "modules": sorted(fbm) if isinstance(fbm, dict) else None,
        "meaning": "items.count walks ScriptManager.getAllItems(), so this is a SCRIPT census "
                   "at join with nothing spawned: 14 = the 15 live item blocks minus SaltRock "
                   "(base:normal). A short or missing bucket would be the engine rejecting the "
                   "brace-unbalanced items_dried.txt (Task 1 Q7 defect 6).",
    }
    # The recipe-resolution finding, both halves: the profile's module-qualified spelling
    # (already in verify[1]) and the bare one, which exercises slice 09's new module scan.
    out["recipe_lookup"] = {
        "qualified": (out["verify"][1].get("got") or {}).get("lookup")
        if len(out["verify"]) > 1 and isinstance(out["verify"][1].get("got"), dict) else None,
        "bare": ask(server, "recipes.craft", "MakeCuredMeat"),
    }
    # Script definitions on BOTH sides -- the server half only exists from slice 09 on.
    out["item_script"] = {"server": ask(server, "item.script", ITEM),
                          "client": ask(c, "item.script", ITEM)}

    # ---- step 0: spawn server-side ------------------------------------------------------
    ok_rcon, reply = server.rcon(f'additem "{USER}" "{ITEM}" 1')
    # The boolean belongs in the artifact, not only in the timeline: `additem` answers with an
    # empty body on success, so `rcon_additem: ""` alone cannot be told from a silent failure.
    out["rcon_additem_ok"] = ok_rcon
    out["rcon_additem"] = str(reply) if ok_rcon else f"rcon failed: {reply}"
    tl.mark("rcon_additem", ok=ok_rcon, reply=str(reply)[:80])
    # The baseline is the only reading taken before anything is pushed, so it is worth waiting
    # for the client's copy to exist rather than recording a `resolved: false` and losing it.
    # No `item.set` has run yet, so this wait cannot disturb what the baseline measures.
    out["spawn_wait"] = []
    for attempt in range(3):
        time.sleep(SPAWN_WAIT)
        seen = probe(c, "witness.fields", f"item {USER}/{ITEM} getID")
        out["spawn_wait"].append({"attempt": attempt + 1, "wall": wall(),
                                  "resolved": seen.get("resolved")
                                  if isinstance(seen, dict) else None,
                                  "error": seen.get("error")
                                  if isinstance(seen, dict) else seen})
        if isinstance(seen, dict) and seen.get("resolved"):
            break
    tl.mark("client_sees_item", attempts=len(out["spawn_wait"]),
            resolved=str(out["spawn_wait"][-1]["resolved"])[:40])

    # ---- step 1: the baseline pair, before ANY item.set fires a sendItemStats ------------
    snapshot("baseline", c)
    out["xp_before"] = step("xp_before", server, "perk.xp", f"{USER} {PERK}")

    # ---- step 1b: chef, so Food.update's Cooking-XP branch is reachable at all -----------
    # @755-@779 gates on chef != null and non-empty; @789 GameServer.server ->
    # getPlayerByUserNameForCommand(chef) -> addXp(player, Perks.Cooking, 10). An RCON spawn
    # leaves it null. Read it straight back: a silent no-op here would make "no XP" look like
    # the side discriminator when it was only an unset field.
    step("set_chef", server, "item.set", f"{USER} {ITEM} chef {USER}")
    out["chef_readback"] = probe(server, "witness.fields", f"item {USER}/{ITEM} getChef")

    # ---- steps 2 and 3: the gates that are NOT the action --------------------------------
    step("set_heat", server, "item.set", f"{USER} {ITEM} heat 2.0")
    step("set_cookingTime", server, "item.set", f"{USER} {ITEM} cookingTime 301")

    # ---- step 3b: the guard read -- the LAST moment `cooked false` is assertable ----------
    guard_srv = probe(server, "witness.fields", f"item {USER}/{ITEM} {FIELDS}")
    guard_cli = probe(c, "witness.fields", f"item {USER}/{ITEM} {FIELDS}")
    gs, gc = fields_of(guard_srv) or {}, fields_of(guard_cli) or {}
    # `frozen` is not a FIELDS getter (the getter is `isFrozen()` but the notes' 26 do not carry
    # it); it comes off TK.ITEM_STATE instead, which is the same instance through item.get.
    guard_get = ask(server, "item.get", f"{USER} {ITEM}")
    out["guard"] = {
        "wall": wall(),
        "server": guard_srv, "client": guard_cli,
        "server_item_get": guard_get,
        "assertions": {
            # additem must not have spawned it cooked -- after step 4 a `true` here would mean
            # "the server's tick won", and the old placement graded the first as the second.
            "server_cooked_false": gs.get("isCooked") is False,
            "server_burnt_false": gs.get("isBurnt") is False,
            "server_frozen_false": (guard_get.get("frozen") is False)
                                   if isinstance(guard_get, dict) else None,
            "server_isCookable_true": gs.get("isCookable") is True,
            # heat decays ~0.03/s (updateTemperature runs BEFORE the gate on every tick), so a
            # pin set seconds ago may already be under 1.6 -- hence the re-pin below.
            "server_heat": gs.get("getHeat"),
            "server_heat_above_gate": (num(gs.get("getHeat")) or 0.0) > 1.6,
            "server_cookingTime": gs.get("getCookingTime"),
            "server_cookingTime_past_gate":
                (num(gs.get("getCookingTime")) or 0.0) > (num(gs.get("getMinutesToCook")) or 0.0),
            # THE outcome-(a) test, decided without any console line: the client cannot have
            # been unblocked by us -- lastCookMinute is not packet-carried -- so a `true` here
            # is the client's own tick having run the transition.
            "client_cooked": gc.get("isCooked"),
            "client_isCookable": gc.get("isCookable"),
            "client_heat": gc.get("getHeat"),
            "outcome_a_at_guard": gc.get("isCooked") is True,
        },
    }
    tl.mark("guard", server_cooked=str(gs.get("isCooked")), client_cooked=str(gc.get("isCooked")),
            heat=str(gs.get("getHeat")))

    # ---- step 3c: re-pin heat immediately before the flip (amendment 12a) -----------------
    step("repin_heat", server, "item.set", f"{USER} {ITEM} heat 2.0")

    # ---- step 4: THE ACTION -- the last gate flip. This bracket is t_action. --------------
    action = step("t_action", server, "item.set", f"{USER} {ITEM} lastCookMinute -1")
    out["t_action"] = {"wall_before": action["wall_before"], "wall_after": action["wall_after"],
                       "serverWorldAge": action.get("serverWorldAge"),
                       "worldAgeMinutes": action.get("worldAgeMinutes")}

    # ---- step 5: the WITNESS, immediately and with no pause -------------------------------
    witness = step("item_update", server, "item.update", f"{USER} {ITEM}")
    before = witness["ack"].get("before") if isinstance(witness["ack"], dict) else None
    out["who_ran_it"] = {
        "before_cooked": before.get("cooked") if isinstance(before, dict) else None,
        "before": before,
        "reading": "before.cooked TRUE = the server's own item tick fired the hook between the "
                   "action and this call (outcome c); FALSE = this bus call is the transition "
                   "(outcome b). Either is independent of what the CLIENT's copy did.",
        "gameMinute": witness.get("gameMinute"),
    }

    # ---- step 6: the two post-action pairs ------------------------------------------------
    snapshot("t+0s", c)
    time.sleep(MIRROR_WAIT)
    snapshot("t+3s", c)
    out["xp_after"] = step("xp_after", server, "perk.xp", f"{USER} {PERK}")

    # ---- the two free readings (notes s"Two further readings") -----------------------------
    out["server_hook_lines"] = grep_file(server.log_path, HOOK_RX, limit=20)
    out["client_hook_lines"] = grep_file(c.console, CLIENT_ERR_RX, limit=20)
    tl.mark("hook_lines", server=len(out["server_hook_lines"]),
            client=len(out["client_hook_lines"]))

    out["comparisons"] = [x for x in (compare("baseline"), compare("t+0s"), compare("t+3s"))
                          if x is not None]
    xb = num((out["xp_before"].get("ack") or {}).get("xp")
             if isinstance(out["xp_before"].get("ack"), dict) else None)
    xa = num((out["xp_after"].get("ack") or {}).get("xp")
             if isinstance(out["xp_after"].get("ack"), dict) else None)
    out["xp_delta"] = None if (xb is None or xa is None) else round(xa - xb, 4)
    out["outcome"] = {
        "a_client_ran_it": out["guard"]["assertions"]["outcome_a_at_guard"],
        "b_bus_call_ran_it": out["who_ran_it"]["before_cooked"] is False,
        "c_server_tick_ran_it": out["who_ran_it"]["before_cooked"] is True,
        "xp_delta": out["xp_delta"],
        "xp_reading": "Food.update grants the cook 10 Cooking XP and only ever on the server "
                      "(@789 GameServer.server); an MP client that runs the same transition "
                      "skips the block. +10 therefore says the SERVER ran it.",
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
        save(path, out, tl, server)      # post-teardown timeline + shutdown-phase errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id,
                            "teardown-longtermpreservation4220.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"outcome": out.get("outcome"), "who_ran_it": out.get("who_ran_it", {})
                  .get("before_cooked"), "guard": out.get("guard", {}).get("assertions"),
                  "folder_check": out.get("folder_check"),
                  "items_census": out.get("items_census"),
                  "desynced": [{c_["tag"]: c_.get("desynced")} for c_ in
                               out.get("comparisons", [])],
                  "error": out.get("error")}, indent=1)[:6000])
