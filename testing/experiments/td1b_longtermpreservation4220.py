"""Teardown 1b: the SKITTLE_LongTermPreservation4220 follow-up micro-session (slice 09, fix
round 1 of Task 3).

Five readings the first session (`td1-20260910-192457`) left inferred rather than measured.
Same shape as `td1_longtermpreservation4220.py` -- never raises through teardown, artifact
copied byte-for-byte -- and deliberately SMALLER: two RCON spawns and one cook transition are
the only world changes, and there is no `settimespeed` and no sandbox write.

**4.1 -- the display-name claim, read directly.** td1's s4.4 inferred "the display name is
unresolved" from the field chain: the server's `getActualWeightUnmodded` answered 0 with the
instance field at 0.35, and the only route to 0 is
`getDisplayName().equals(getFullType())` (`@0-@24 L2638-L2641`). It never read
`getDisplayName()` itself. One `witness.fields` per side closes it.

**4.2 -- the vanilla control.** `Item.InstanceItem @3380-@3393` feeds BOTH `setActualWeight`
and `setWeight` from the SAME `Item.actualWeight`, so the guard is not mod-specific by
construction; and td1's own BASELINE pair already read `getActualWeightUnmodded` 0 on both
sides with the field at 0.5. `Base.Steak` says whether the unresolved name is about MOD items
(a translation / module-prefix problem) or about this dedicated server generally. Spawned and
read on both sides, never cooked.

**4.3 -- the second server->client hop.** td1's s4.5 measured server `getThirstChange` 0.1 vs
client 0.05 after the cook and wrote "every further `sendItemStats` halves it again". That is
an extrapolation. `ItemStatsPacket.setData @299` packs the MODIFIED getter and
`applyItemStats @188/@191` stores it through `setThirstChange` as the RAW field, so the
client's own ladder halves it once on read -- but the SERVER's raw field never moves, so every
push carries the same 0.1 and the client should land on 0.05 again. A second push settles it:
0.05 again = one halving per hop (converges); 0.025 = compounding. The push is one
`item.set heat 2.0`, chosen because `heat` is packet-carried, changes nothing about thirst, and
`item.set` fires `sendItemStats` on its way out.

**4.4 -- the vanilla modData census.** td1 found `Tooltip` on both sides of a MOD item and
traced it to `InventoryItem.setTooltip`, whose first act is
`getModData():rawset("Tooltip", value)` (`@0-@13 L3040`). If that is the route, a vanilla item
with a `Tooltip =` line has the key too and the slice-08 exclusion rule needs both keys, not
just `customName`. This is the baseline slices 10/11 compare against.

**4.5 -- two null controls.** (i) `chef` is deliberately NOT set this time: td1 set it, the XP
gate at `Food.update @755-@779` opened and +2.5 landed, so with `chef` null the same
transition must grant ZERO. `perk.xp admin Cooking` before and after. (ii) the server's
`lastCookMinute` after the cook, which the harness only started exposing in this fix round
(`TK.ITEM_STATE.lastCookMinute`, and `gameMinute` on every `item.set` ack) -- td1 could read
neither, which is why it could not tell a gate it opened from one that had already reopened.

**The cook is NOT driven by `item.update` here.** td1 measured the server's own inventory-item
tick running the transition ~5 s after the preconditions were in place, so this session pins
the three gates and then POLLS `item.get` until `cooked` is true. That records the same
outcome (c) with no bus call that could be mistaken for the cause, and every poll carries the
new `lastCookMinute` / the ack's `gameMinute` so the gate is visible rather than inferred.
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
ITEM = "Skittles.CuredPork"          # the mod item
CONTROL = "Base.Steak"               # the vanilla control, spawned and read, never cooked
PERK = "Cooking"

MIRROR_WAIT = 3.0        # 3 s > the 1 Hz PlayerStatsPacket window (every prior slice's number)
SPAWN_WAIT = 2.5         # RCON additem -> item visible in the client's inventory (s01/s02/s05)
COOK_POLL = 2.0          # the server's own item tick runs ~every 5 s (task-3 report s3.5)
COOK_POLLS = 12          # 12 x 2 s = 24 s, ~5 cadences: generous, and bounded

# The six weight/name getters, comma-joined and WHITESPACE-FREE (`splitArgs` splits on `%S+`
# and `witness.fields` reads argv[3] only, so a space silently drops every getter after it).
# getDisplayName is the one td1 never read; getFullType is beside it because the guard at
# `getActualWeightUnmodded @0-@8` is literally `displayName.equals(fullType)`.
WEIGHT_FIELDS = ("getDisplayName,getFullType,getActualWeight,getActualWeightUnmodded,"
                 "isCustomWeight,getWeight")
WEIGHT_COUNT = 6
# The thirst hop is read alone so the two readings are cheap and their wall clocks are tight.
THIRST_FIELDS = "getThirstChange,isCooked"

ITEM_SCOPE = f"item:{USER}/{ITEM} *"
CONTROL_SCOPE = f"item:{USER}/{CONTROL} *"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
MOD_RX = re.compile(re.escape(MOD))
# recipe_meats.lua:35,37,41,52 -- the four prints OnCookedTest makes. Their presence in the
# SERVER console is direct evidence the Lua hook ran there.
HOOK_STRINGS = ["changing da meat", "post cookable", "meat change days", "meat done"]
HOOK_RX = re.compile("|".join(re.escape(s) for s in HOOK_STRINGS), re.I)
CLIENT_ERR_RX = re.compile("|".join(re.escape(s) for s in HOOK_STRINGS) +
                           r"|OnCookedTest|tried to call nil|protectedCallVoid|LuaCaller",
                           re.I)

prof = profile.load(PROFILE)
rec = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("td1b")
path = os.path.join(run_dir, "teardown-longtermpreservation4220-followup.json")
tl, clients, t0 = Timeline(), [], time.time()
server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources,
                     mod_skip=prof.skip, sandbox=prof.sandbox or None)

doctor_clean, doctor_text = doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "follow_up_to": "td1-20260910-192457",
    "mod": MOD,
    "workshop_item": prof.items.get(MOD),
    "subject": ITEM,
    "control": CONTROL,
    "user": USER,
    "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "weight_fields": WEIGHT_FIELDS,
    "weight_field_count_expected": WEIGHT_COUNT,
    "thirst_fields": THIRST_FIELDS,
    "moddata_scopes": {"mod_item": ITEM_SCOPE, "vanilla_item": CONTROL_SCOPE},
    "questions": {
        "4.1": "getDisplayName on both sides for the MOD item -- is it the full type?",
        "4.2": "the same six getters on a VANILLA item -- mod-specific or server-wide?",
        "4.3": "one more server->client push: client getThirstChange 0.05 (one halving per "
               "hop) or 0.025 (compounding)?",
        "4.4": "the vanilla item's modData census on both sides -- the slices 10/11 baseline",
        "4.5": "chef UNSET: XP delta 0? and the server's lastCookMinute after the cook",
    },
    "world_changes": "none to restore -- two RCON additem spawns and one cook transition; no "
                     "settimespeed, no sandbox write, no chef; every write lands in this run's "
                     "copy of the fixture",
    "reads": [], "steps": [], "notes": [], "weight_reads": [], "censuses": [],
}


def wall():
    return round(time.time() - t0, 3)


def probe(side, cmd, args, timeout=20):
    """One witness read, with its wall clock, recorded whatever comes back. td1's re-ask guard,
    kept: `TK.writeKV` writes the ack file non-atomically and the poller reads it every 0.25 s,
    so `parse_ack` can degrade a table reply to a raw string. A string where a table belongs is
    re-asked ONCE, both readings are kept, and a second non-dict reply is filed in `notes`
    rather than dropped (td1 fix round 1, m10)."""
    t = wall()
    val = ask(side, cmd, args, timeout=timeout)
    meta = {"cmd": cmd, "args": args, "wall": t, "wall_done": wall()}
    if not isinstance(val, dict):
        meta["reasked"] = True
        meta["first_reply"] = val
        val = ask(side, cmd, args, timeout=timeout)
        meta["wall_done"] = wall()
    if isinstance(val, dict):
        val = dict(val)
        val["_probe"] = meta
    else:
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def read(tag, side, side_name, cmd, args, timeout=20):
    """One recorded reading: the tag that names the question it answers, the side, the reply
    and its wall bracket. Every answer in this artifact is one of these rows."""
    val = probe(side, cmd, args, timeout=timeout)
    row = {"tag": tag, "side": side_name, "cmd": cmd, "args": args, "reply": val,
           "wall": (val.get("_probe") or {}).get("wall") if isinstance(val, dict) else wall(),
           "wall_done": (val.get("_probe") or {}).get("wall_done")
           if isinstance(val, dict) else wall()}
    out["reads"].append(row)
    tl.mark("read", tag=tag, side=side_name)
    save(path, out, tl, server)
    return row


def step(name, side, cmd, args, timeout=30):
    """One SEQUENCED bus call: the ack, both wall clocks bracketing it, and the ack's own
    `serverWorldAge` / `gameMinute` / `lastCookMinute` lifted out. `gameMinute` on an `item.set`
    ack and `lastCookMinute` in the item state are BOTH new in slice 09 fix round 1 -- they are
    the two halves of the gate at `Food.update @86`, which td1 could only infer."""
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if isinstance(val, dict):
        row["serverWorldAge"] = val.get("serverWorldAge")
        row["gameMinute"] = val.get("gameMinute")
        row["lastCookMinute"] = val.get("lastCookMinute")
        before = val.get("before")
        row["before_lastCookMinute"] = before.get("lastCookMinute") \
            if isinstance(before, dict) else None
        row["cooked"] = val.get("cooked")
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


def weight_pair(tag, fullType, c):
    """The six weight/name getters on BOTH sides of one item, client first, with the
    server-vs-client comparison of each. Client first for the same reason as td1: a server read
    is free of side effects but the ORDER is what bounds a mirror window if one ever opens."""
    rows = {}
    for name, side in (("client", c), ("server", server)):
        rows[name] = read(tag, side, name, "witness.fields", f"item {USER}/{fullType} "
                                                             f"{WEIGHT_FIELDS}")
    sf, cf = fields_of(rows["server"]["reply"]), fields_of(rows["client"]["reply"])
    cmp_ = {"tag": tag, "fullType": fullType,
            "server_count": (rows["server"]["reply"] or {}).get("count")
            if isinstance(rows["server"]["reply"], dict) else None,
            "client_count": (rows["client"]["reply"] or {}).get("count")
            if isinstance(rows["client"]["reply"], dict) else None,
            "server": sf, "client": cf}
    if isinstance(sf, dict) and isinstance(cf, dict):
        cmp_["nameIsFullType"] = {
            "server": sf.get("getDisplayName") == sf.get("getFullType"),
            "client": cf.get("getDisplayName") == cf.get("getFullType"),
        }
        cmp_["differs"] = sorted(g for g in set(sf) | set(cf) if sf.get(g) != cf.get(g))
    out["weight_reads"].append(cmp_)
    save(path, out, tl, server)
    return cmp_


def census_pair(tag, scope, c, vanilla):
    """One modData census on both sides, with the per-side key list and what is beyond the
    named vanilla set for THAT scope (td1 fix round 1, m11: one shared exclusion list makes
    `beyondVanilla` meaningless on the scope it was not written for)."""
    rows = {}
    for name, side in (("client", c), ("server", server)):
        r = read(tag, side, name, "witness.moddata", scope)
        ks = keys_of(r["reply"])
        names = sorted(s.split(":")[0] for s in ks) if ks is not None else None
        rows[name] = {"resolved": r["reply"].get("resolved")
                      if isinstance(r["reply"], dict) else None,
                      "keyCount": r["reply"].get("keyCount")
                      if isinstance(r["reply"], dict) else None,
                      "keys": ks, "keyNames": names,
                      "beyondVanilla": sorted(set(names or []) - vanilla)
                      if names is not None else None}
    row = {"tag": tag, "scope": scope, "vanillaExclusions": sorted(vanilla), **rows}
    out["censuses"].append(row)
    save(path, out, tl, server)
    return row


def thirst_of(reply):
    f = fields_of(reply)
    return f.get("getThirstChange") if isinstance(f, dict) else None


def weight_answer(tag):
    """The one-line answer a `weight_reads` row gives to 4.1 / 4.2: the display name each side
    reported, whether it equals the full type (the `getActualWeightUnmodded` guard), and the
    two weight readings that guard decides."""
    row = next((r for r in out["weight_reads"] if r["tag"] == tag), None)
    if row is None:
        return None
    ans = {"tag": tag, "fullType": row.get("fullType"),
           "nameIsFullType": row.get("nameIsFullType"), "differs": row.get("differs")}
    for s in ("server", "client"):
        f = row.get(s) or {}
        ans[s] = {k: f.get(k) for k in ("getDisplayName", "getActualWeight",
                                        "getActualWeightUnmodded", "isCustomWeight",
                                        "getWeight")}
    return ans


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

    # ---- step 0: two server-side spawns (a client AddItem is invisible to the server, S6) ----
    out["rcon"] = {}
    for full in (ITEM, CONTROL):
        ok, reply = server.rcon(f'additem "{USER}" "{full}" 1')
        out["rcon"][full] = {"ok": ok, "reply": str(reply)}
        tl.mark("rcon_additem", item=full, ok=ok, reply=str(reply)[:60])
    # Wait for the CLIENT's copies to exist before anything is read or pushed: a
    # `resolved: false` here would lose the reading rather than measure anything.
    out["spawn_wait"] = []
    for attempt in range(3):
        time.sleep(SPAWN_WAIT)
        seen = {f: probe(c, "witness.fields", f"item {USER}/{f} getID") for f in (ITEM, CONTROL)}
        out["spawn_wait"].append({"attempt": attempt + 1, "wall": wall(),
                                  "resolved": {f: (v.get("resolved")
                                                   if isinstance(v, dict) else None)
                                               for f, v in seen.items()}})
        if all(isinstance(v, dict) and v.get("resolved") for v in seen.values()):
            break
    tl.mark("client_sees_items", attempts=len(out["spawn_wait"]))

    # ---- 4.1 / 4.2: the six weight/name getters, both items, both sides, BEFORE the cook -----
    weight_pair("4.1-mod-raw", ITEM, c)
    weight_pair("4.2-vanilla-raw", CONTROL, c)

    # ---- 4.4: the vanilla modData census, both sides (and the mod item's, for the diff) ------
    census_pair("4.4-vanilla", CONTROL_SCOPE, c, {"customName"})
    census_pair("4.4-mod", ITEM_SCOPE, c, {"customName"})

    # ---- 4.5(i): XP before, with chef DELIBERATELY UNSET ------------------------------------
    out["xp_before"] = step("xp_before", server, "perk.xp", f"{USER} {PERK}")

    # ---- the cook: pin the three gates, then let the SERVER'S OWN TICK run it ---------------
    # No `chef` (4.5's null control) and no `item.update`: td1 measured the server's own
    # inventory-item tick running the transition on a ~5 s cadence, so polling `item.get` is
    # both sufficient and free of any call that could be mistaken for the cause.
    step("set_heat", server, "item.set", f"{USER} {ITEM} heat 2.0")
    step("set_cookingTime", server, "item.set", f"{USER} {ITEM} cookingTime 301")
    step("set_lastCookMinute", server, "item.set", f"{USER} {ITEM} lastCookMinute -1")

    out["cook_poll"] = []
    cooked_at = None
    for i in range(COOK_POLLS):
        got = ask(server, "item.get", f"{USER} {ITEM}")
        row = {"poll": i + 1, "wall": wall(),
               "cooked": got.get("cooked") if isinstance(got, dict) else None,
               "heat": got.get("heat") if isinstance(got, dict) else None,
               "cookingTime": got.get("cookingTime") if isinstance(got, dict) else None,
               "lastCookMinute": got.get("lastCookMinute") if isinstance(got, dict) else None,
               "serverWorldAge": got.get("serverWorldAge") if isinstance(got, dict) else None,
               "isCookable": got.get("isCookable") if isinstance(got, dict) else None,
               "thirstChange": got.get("thirstChange") if isinstance(got, dict) else None,
               "ack_shape": None if isinstance(got, dict) else type(got).__name__}
        swa = num(row["serverWorldAge"])
        row["worldAgeMinutes"] = round(swa * 60.0, 4) if swa is not None else None
        out["cook_poll"].append(row)
        save(path, out, tl, server)
        if row["cooked"] is True:
            cooked_at = row
            break
        time.sleep(COOK_POLL)
    tl.mark("cooked", found=cooked_at is not None, wall=cooked_at["wall"] if cooked_at else None)
    out["cooked_at"] = cooked_at

    # ---- 4.5(ii): the server's item state after the cook -- the NEW lastCookMinute field -----
    out["item_get_after_cook"] = ask(server, "item.get", f"{USER} {ITEM}")

    # ---- 4.3: the thirst hop. Reading 1 = after the transition's own sendItemStats -----------
    h1_srv = read("4.3-hop1", server, "server", "witness.fields",
                  f"item {USER}/{ITEM} {THIRST_FIELDS}")
    h1_cli = read("4.3-hop1", c, "client", "witness.fields",
                  f"item {USER}/{ITEM} {THIRST_FIELDS}")
    # ONE more server->client push. `heat` is packet-carried, touches nothing thirst-related,
    # and `item.set` fires sendItemStats(item) on its way out -- so this is a clean second hop.
    push = step("second_push", server, "item.set", f"{USER} {ITEM} heat 2.0")
    time.sleep(MIRROR_WAIT)
    h2_srv = read("4.3-hop2", server, "server", "witness.fields",
                  f"item {USER}/{ITEM} {THIRST_FIELDS}")
    h2_cli = read("4.3-hop2", c, "client", "witness.fields",
                  f"item {USER}/{ITEM} {THIRST_FIELDS}")
    t1, t2 = thirst_of(h1_cli["reply"]), thirst_of(h2_cli["reply"])
    out["thirst_hops"] = {
        "server_hop1": thirst_of(h1_srv["reply"]), "client_hop1": t1,
        "client_hop1_wall": h1_cli["wall"],
        "push_wall": {"before": push["wall_before"], "after": push["wall_after"]},
        "push_sync": push["ack"].get("sync") if isinstance(push["ack"], dict) else None,
        "server_hop2": thirst_of(h2_srv["reply"]), "client_hop2": t2,
        "client_hop2_wall": h2_cli["wall"],
        "delta": None if (num(t1) is None or num(t2) is None) else round(num(t2) - num(t1), 6),
        "reading": "equal => ONE halving per server->client hop (the server's raw field never "
                   "moves, so every push carries the same value and the client converges); "
                   "halved again => compounding, which would need a client->server hop that "
                   "docs/modding/patterns.md:83 records as a silent no-op",
    }

    # ---- 4.1 again, AFTER the cook: this is the state td1's s4.4 graded --------------------
    weight_pair("4.1-mod-cooked", ITEM, c)
    weight_pair("4.2-vanilla-after", CONTROL, c)

    # ---- 4.5(i) again ---------------------------------------------------------------------
    out["xp_after"] = step("xp_after", server, "perk.xp", f"{USER} {PERK}")
    xb = num((out["xp_before"].get("ack") or {}).get("xp")
             if isinstance(out["xp_before"].get("ack"), dict) else None)
    xa = num((out["xp_after"].get("ack") or {}).get("xp")
             if isinstance(out["xp_after"].get("ack"), dict) else None)
    out["xp_delta"] = None if (xb is None or xa is None) else round(xa - xb, 4)

    out["server_hook_lines"] = grep_file(server.log_path, HOOK_RX, limit=20)
    out["client_hook_lines"] = grep_file(c.console, CLIENT_ERR_RX, limit=20)
    tl.mark("hook_lines", server=len(out["server_hook_lines"]),
            client=len(out["client_hook_lines"]))

    out["answers"] = {
        "4.1_mod_raw": weight_answer("4.1-mod-raw"),
        "4.1_mod_cooked": weight_answer("4.1-mod-cooked"),
        "4.2_vanilla_raw": weight_answer("4.2-vanilla-raw"),
        "4.2_vanilla_after": weight_answer("4.2-vanilla-after"),
        "4.3_one_halving_per_hop": (None if (num(t1) is None or num(t2) is None)
                                    else abs(num(t2) - num(t1)) <= 1e-6),
        "4.3_client_readings": [t1, t2],
        "4.4_vanilla_keys": next((r["server"]["keyNames"] for r in out["censuses"]
                                  if r["tag"] == "4.4-vanilla"), None),
        "4.5_xp_delta_with_chef_unset": out["xp_delta"],
        "4.5_lastCookMinute_after_cook": out["item_get_after_cook"].get("lastCookMinute")
        if isinstance(out["item_get_after_cook"], dict) else None,
        "cooked": cooked_at is not None,
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
                            "teardown-longtermpreservation4220-followup.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"answers": out.get("answers"), "thirst_hops": out.get("thirst_hops"),
                  "weight_reads": out.get("weight_reads"), "censuses": out.get("censuses"),
                  "cooked_at": out.get("cooked_at"), "xp_delta": out.get("xp_delta"),
                  "error": out.get("error")}, indent=1)[:6000])
