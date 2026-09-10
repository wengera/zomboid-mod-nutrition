"""Slice 08, task 4: the first live exercise of the reflective witness commands.

Slices 09-11 have to read fields and modData keys **nobody has named yet** -- a nutrition mod's
own getters, its own `getModData()` shape -- and a harness command per mod is not a plan. Task 3
answered that with two generic commands in `PZTestKit_Core.lua`: `witness.fields <player|item>
<id> <getter,...>` and `witness.moddata [player[:<user>]|item:<id>|global:<name>] <key ...>`.
They were reviewed and committed (`726d31a`, `d260671`) but never executed: there is no Lua
interpreter on this host, so every claim about their behaviour was a reading of the source. This
run is the first time either has answered a live game, and its artifact is what slices 09-11
cite instead of that reading.

**What is being measured, and why each probe is here.**

  * **Both sides, same command.** `player_server` / `player_client` ask the same five zero-arg
    getters of the same subject on the dedicated server and on the client. A `fields` map that
    is non-empty on both is the claim "one shared command reads either side"; the pair of
    `resolved` labels is the claim about *which subject answered*, which is not the same
    question -- on a client `subjectOf` resolves the LOCAL player and ignores the `<user>` it
    was given (Task 4 amendment 4). `player_client_wrong_user` measures exactly that: the same
    command with a username that is not logged in, answered for `admin` anyway.
  * **An item, on both sides, against the dataset.** `item_server` / `item_client` read
    `Base.Apple`'s macros through the witness. The dataset says 95.0 kcal / 25.13 / 0.31 / 0.47
    (`data/food-items.json`), so the reply is checkable against something other than itself --
    that is what makes this an `M` row rather than "the witness said so". `item_get_server` is
    the independent second reading: the slice-01 `item.get` command, a different code path to
    the same instance, and the source of the item id.
  * **The `#<id>` route.** `item_byid` re-asks for the same item by numeric id. The id is never
    guessed: it is read back out of a reply (see `id_source` in the artifact).
  * **The three-way sort.** `absent_getter` asks a player for `getCalories` (which lives on
    `Nutrition`, not on `IsoPlayer`) and `getNoSuchThing` (which lives nowhere). Both are
    expected in `missing`, and the point of the probe is that `missing` is not `nils`: a getter
    the build never had and a getter that answered nil are different findings, and slices 09-11
    turn on telling "the mod did not set it" from "this build never had it".
  * **The modData triple (S6 again, through the new command).** The client writes a key, the
    server is asked for it BEFORE `transmitModData` and AFTER. Slice 06 measured that shape with
    a bespoke command pair; this reproduces it through the generic one.
  * **`global:` and `item:` scopes.** `ModData.getOrCreate` CREATES the table it is asked for,
    so an empty census of `global:pzt_probe_table` is the EXPECTED result and evidence only that
    the binding exists (amendment 3). `item:` censuses the apple's own modData.
  * **The shape gates.** Every later driver has to know when it can meet a bare string instead
    of a table. `gate_bad_subject_word`, `gate_bare_scope_word` and `gate_item_no_id` walk the
    three boundaries the header comments claim: a missing/unknown `<player|item>` word and a
    bare `item`/`global` scope word answer the usage STRING; everything else -- including a
    subject that does not resolve -- answers a TABLE with `resolved = false` and `error`.

**Two harness properties every reading here inherits.**

  * `TK.json` encodes an empty Lua table as `{}`, so an empty `missing` / `nils` / `keys`
    arrives in Python as an empty **dict**, not an empty list. Nothing below tests a list with
    `== []` or indexes position 0 without checking; `listy()` is the single place that
    normalises it, and `count` / `keyCount` are numbers and are the safe things to assert on.
  * `parse_ack` degrades JSON it cannot parse to a raw string, and `TK.writeKV` writes the ack
    file non-atomically while the Python poller reads it every 0.25 s. A reply that should be a
    table and arrives as a string is therefore a *bus* finding, not a witness one: `probe()`
    re-asks once and records both readings.

The run makes no world change -- no `settimespeed`, no sandbox write. The one write is the
client's `moddata.set pzt_witness v08`, which the triple exists to measure, and it lands in this
run's own COPY of the fixture (`fx.restore_server` / `fx.restore_client`), so there is nothing to
restore and teardown is the whole cleanup path. `data/food-items.json` is read, never written: a
number that disagrees is the finding, recorded with both values.

Everything lands in `<run_dir>/witness-probe.json`, copied byte-for-byte at the end to
`testing/artifacts/<run-id>/witness-probe.json`. Run with `python testing/pzt doctor` clean and
nothing else live; the doctor is re-run from here and its verdict is in the artifact.
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
from _common import ask, doctor, git_dirty, git_say, hard_kill, load_json, num, save
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import (Timeline, check_mods_loaded, fault_reasons, make_client, make_server,
                         teardown)

USER = "admin"
# 3.0, not the 2.5 the brief's skeleton carried: `spikes.py` sleeps 3 s after this same
# `rcon additem` and that is the number with a live run behind it (Task 4 amendment 8). If the
# server-side item probe still does not resolve, the probe is retried ONCE after a further
# SPAWN_RETRY_WAIT before the miss is recorded.
SPAWN_WAIT, SPAWN_RETRY_WAIT = 3.0, 3.0
TRANSMIT_SETTLE = 2.0     # client transmitModData -> the server's copy of the character

PLAYER_GETTERS = "getUsername,getNutrition,getHoursSurvived,getMaxWeight,getSlicesOfBreadEaten"
ITEM_GETTERS = "getCalories,getCarbohydrates,getLipids,getProteins,getHungChange,getAge,getModData"
ITEM_TYPE = "Base.Apple"
MOD_KEY, MOD_VALUE = "pzt_witness", "v08"
GLOBAL_TABLE = "pzt_probe_table"
ABSENT_GETTERS = "getCalories,getNoSuchThing"
BAD_USER = "nosuchuser"          # deliberately not logged in

# `TK.WITNESS_MAX` in PZTestKit_Core.lua. Both getter lists are under it; the assertion that
# `truncatedAt` is absent is what says the cap did not silently shorten a reading.
WITNESS_MAX = 32

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET = os.path.join(REPO, "data", "food-items.json")
LUA = "testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua"

# (witness getter, dataset column, factor, transform label). The /100 on `getHungChange` is the
# instance constructor's, not the fluid loader's -- slice 05 measured and attributed both
# (`s05_food_scan.py:173-182`, docs/vanilla/food-dataset-notes.md); the four macros are identity.
ITEM_EXPECT = (("getCalories", "calories", 1.0, "identity"),
               ("getCarbohydrates", "carbohydrates", 1.0, "identity"),
               ("getLipids", "lipids", 1.0, "identity"),
               ("getProteins", "proteins", 1.0, "identity"),
               ("getHungChange", "hunger_change", 0.01, "x0.01 (Item.InstanceItem)"))
# The same five, spelled as `TK.ITEM_STATE` spells them, for the independent `item.get` reading.
ITEM_GET_KEYS = {"getCalories": "calories", "getCarbohydrates": "carbs", "getLipids": "lipids",
                 "getProteins": "proteins", "getHungChange": "hungChange"}

# Nutrition is float32 on the Java side, so an exact compare is wrong even when the arithmetic
# is: 25.13 reads back 25.129999. Absolute floor plus a relative term against the larger of the
# two values compared -- the anchoring slice 06's fix round settled on.
ATOMIC_ABS, ATOMIC_REL = 1e-4, 1e-6


def tol(*magnitudes):
    m = max([abs(x) for x in magnitudes if isinstance(x, (int, float))] or [0.0])
    return ATOMIC_ABS + ATOMIC_REL * m


def listy(v):
    """A witness list as a Python list, or `None` when the reply is not list-shaped at all.

    `TK.json` encodes an empty Lua table as `{}` (it is not an array: `#v == 0`), so an EMPTY
    `missing` / `nils` / `keys` arrives as an empty dict. Every emptiness test in this file goes
    through here; nothing tests `== []` and nothing indexes a list it has not measured."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [] if not v else None
    return None


def shape_of(v):
    if isinstance(v, dict):
        return "dict"
    if isinstance(v, list):
        return "list"
    return type(v).__name__


def truncation_note(reply):
    """`(count, truncatedAt, ok)` -- `ok` is False only when the cap actually bit. Amendment 6:
    assert on `count` / `keyCount`, which are numbers whatever the `{}`-for-empty shape does."""
    if not isinstance(reply, dict):
        return None, None, False
    return reply.get("count"), reply.get("truncatedAt"), not reply.get("truncatedAt")


rec = fx.load("default")
run_id, run_dir = new_run_dir("exp08")
path = os.path.join(run_dir, "witness-probe.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
t_start = time.time()

doctor_clean, doctor_text = doctor()
data, data_err, data_sha = load_json(DATASET)
items_by_id = {r["id"]: r for r in (data or {}).get("items", [])}
apple = items_by_id.get(ITEM_TYPE)
lua_dirty, lua_dirty_note = git_dirty(LUA)
out = {
    "run_id": run_id,
    "meta": {
        "purpose": "first live exercise of witness.fields / witness.moddata (slice 08 task 4): "
                   "both commands, both sides, against a dataset-checkable item and the S6 "
                   "modData triple",
        "commands_under_test": ["witness.fields", "witness.moddata"],
        "harness_lua": LUA,
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA),
        "harness_lua_dirty": lua_dirty,
        "harness_lua_dirty_note": lua_dirty_note,
        "head_commit": git_say("rev-parse", "--short", "HEAD"),
        "dataset": os.path.relpath(DATASET, REPO).replace("\\", "/"),
        "dataset_commit": git_say("log", "-1", "--format=%h", "--", "data/food-items.json"),
        "dataset_sha256": data_sha,
        "dataset_read_error": data_err,
        "dataset_meta": (data or {}).get("meta"),
        "doctor_clean": doctor_clean,
        "doctor": doctor_text.strip().splitlines(),
        "user": USER, "item_type": ITEM_TYPE,
        "player_getters": PLAYER_GETTERS, "item_getters": ITEM_GETTERS,
        "spawn_wait_s": SPAWN_WAIT, "spawn_retry_wait_s": SPAWN_RETRY_WAIT,
        "transmit_settle_s": TRANSMIT_SETTLE,
        "witness_max": WITNESS_MAX,
        "empty_list_shape": "TK.json encodes an empty Lua table as {}, so an empty missing / "
                            "nils / keys arrives as an empty DICT, not []. Test emptiness with "
                            "`not x`; assert on the numeric `count` / `keyCount` instead.",
        "bus_hazard": "TK.writeKV writes the ack file non-atomically and the poller reads it "
                      "every 0.25 s; parse_ack degrades unparseable JSON to a raw string. A "
                      "table reply that arrives as a string is re-asked once and BOTH readings "
                      "are kept (probes.<key>.first_reply).",
        "world_changes": "none -- no settimespeed, no sandbox write. The one write is the "
                         "client's moddata.set, and it lives in this run's COPY of the fixture.",
    },
    "session": {}, "probes": {}, "grading": [], "summary": {},
}
grades_by_name = {}
print(f"dataset sha256 {str(data_sha)[:16]}; {ITEM_TYPE} in dataset: {apple is not None}; "
      f"doctor {'clean' if doctor_clean else 'DIRTY'}")
for line in doctor_text.strip().splitlines():
    print("  doctor| " + line)


def probe(key, side, side_name, cmd, args, expect="table", timeout=20):
    """One witness call, recorded whatever comes back.

    Writes the raw reply to `out[key]` (the artifact key the brief names) and the call's own
    facts -- side, args, reply shape, and the reply's `resolved` / `count` / `keyCount` /
    `truncatedAt` / `error` -- to `out["probes"][key]`, which is the table the report's graded
    rows are read off. Never raises: `ask` reports a wedged side as `{"error": ...}` and the
    remaining probes are still worth collecting.

    `expect="table"` also arms the bus guard (amendment 10): a string where a table belongs is
    re-asked ONCE, both readings are kept, and the second is the one that goes into `out[key]`.
    """
    reply = ask(side, cmd, args, timeout=timeout)
    meta = {"side": side_name, "cmd": cmd, "args": args, "expect": expect,
            "reply_shape": shape_of(reply), "reasked": False}
    if expect == "table" and not isinstance(reply, dict):
        meta["reasked"] = True
        meta["first_reply"] = reply
        meta["first_reply_shape"] = shape_of(reply)
        second = ask(side, cmd, args, timeout=timeout)
        meta["second_reply_shape"] = shape_of(second)
        meta["bus_finding"] = ("a table reply arrived as a %s; re-asked once"
                               % shape_of(reply))
        reply = second
        meta["reply_shape"] = shape_of(reply)
    if isinstance(reply, dict):
        if set(reply) == {"error"} and isinstance(reply.get("error"), str) and \
                reply["error"].split(":")[0] in ("RuntimeError", "TimeoutError", "OSError",
                                                 "PermissionError"):
            meta["bus_error"] = reply["error"]     # a wedged side, not a witness answer
        for k in ("side", "subject", "id", "scope", "arg", "resolved", "count", "keyCount",
                  "truncatedAt", "error", "worldAge"):
            if k in reply:
                meta[k] = reply[k]
        for k in ("missing", "nils", "keys"):
            if k in reply:
                meta[k] = listy(reply[k]) if listy(reply[k]) is not None else reply[k]
        if isinstance(reply.get("fields"), dict):
            meta["field_names"] = sorted(reply["fields"])
        if isinstance(reply.get("values"), dict):
            meta["value_names"] = sorted(reply["values"])
    out[key] = reply
    out["probes"][key] = meta
    tl.mark("probe", key=key, on=side_name, shape=meta["reply_shape"],
            resolved=str(meta.get("resolved"))[:40])
    return reply


def grade(name, verdict, expected, observed, ok, **extra):
    """One row of the graded outcome table the brief's Step 4 asks for.

    `verdict` is one of: `as expected` (the reading is what the source claimed),
    `finding` (a real, recorded behaviour that the source did not claim, or claimed
    differently -- not a failure), `miss` (the probe did not produce a reading at all)."""
    r = {"row": name, "verdict": verdict, "expected": expected, "observed": observed, "ok": ok}
    r.update(extra)
    out["grading"].append(r)
    grades_by_name[name] = r
    return r


try:
    if not doctor_clean:
        raise RuntimeError("pzt doctor is not clean -- refusing to boot: " + doctor_text[:400])
    tl.mark("server_launch", port=server.port)
    server.start()
    tl.mark("server_started", took=server.t_started, build=server.build)
    check_mods_loaded(tl, server)
    c, restored = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    tl.mark("client_launch", user=USER, restored=restored)
    tl.mark("client_ready", took=c.wait_ready())
    tl.mark("session_ready")
    out["fixture"] = rec.get("name")
    out["build"] = server.build

    def srv(cmd, args="", timeout=30):
        return ask(server, cmd, args, timeout=timeout)

    # ---- 0. session start ----------------------------------------------------
    out["session"]["players"] = srv("players")
    out["session"]["version_server"] = srv("version")
    out["session"]["version_client"] = ask(c, "version")
    out["session"]["time_start"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 1. witness.fields on a PLAYER, both sides ---------------------------
    for side, side_name in ((server, "server"), (c, "client")):
        probe(f"player_{side_name}", side, side_name, "witness.fields",
              f"player {USER} {PLAYER_GETTERS}")
    # The client ignores <user> (amendment 4): the same command with a username that is not
    # logged in still answers for the LOCAL player. Measured, not asserted from the source.
    probe("player_client_wrong_user", c, "client", "witness.fields",
          f"player {BAD_USER} getUsername")
    # Its server counterpart is the failure SHAPE: a subject that does not resolve is a table
    # with resolved = false plus error, never a bare string (amendments 7 and 11).
    probe("player_server_bad_user", server, "server", "witness.fields",
          f"player {BAD_USER} getUsername")
    save(path, out, tl, server)

    # ---- 2. spawn the apple, then witness.fields on an ITEM, both sides ------
    ok_rcon, reply_rcon = server.rcon(f'additem "{USER}" "{ITEM_TYPE}" 1')
    out["session"]["rcon_additem"] = str(reply_rcon) if ok_rcon else f"rcon failed: {reply_rcon}"
    tl.mark("additem", item=ITEM_TYPE, ok=ok_rcon)
    time.sleep(SPAWN_WAIT)
    for side, side_name in ((server, "server"), (c, "client")):
        probe(f"item_{side_name}", side, side_name, "witness.fields",
              f"item {ITEM_TYPE} {ITEM_GETTERS}")
    # Amendment 8: one retry, after a further wait, before a miss is recorded. The first
    # attempt is kept beside the retry -- "it needed 6 s" is itself a reading.
    if isinstance(out.get("item_server"), dict) and out["item_server"].get("resolved") is False:
        out["item_server_first_attempt"] = out["item_server"]
        out["probes"]["item_server_first_attempt"] = out["probes"]["item_server"]
        tl.mark("item_retry", why="item_server resolved false", wait=SPAWN_RETRY_WAIT)
        time.sleep(SPAWN_RETRY_WAIT)
        for side, side_name in ((server, "server"), (c, "client")):
            if isinstance(out.get(f"item_{side_name}"), dict) and \
                    out[f"item_{side_name}"].get("resolved") is False:
                if f"item_{side_name}_first_attempt" not in out:
                    out[f"item_{side_name}_first_attempt"] = out[f"item_{side_name}"]
                    out["probes"][f"item_{side_name}_first_attempt"] = \
                        out["probes"][f"item_{side_name}"]
                probe(f"item_{side_name}", side, side_name, "witness.fields",
                      f"item {ITEM_TYPE} {ITEM_GETTERS}")
    # The independent second reading of the same instance, down a different command (slice 01's
    # `item.get` -> TK.itemState), and the id's primary source.
    out["item_get_server"] = srv("item.get", f"{USER} {ITEM_TYPE}", timeout=20)
    save(path, out, tl, server)

    # ---- 3. the #<id> route --------------------------------------------------
    # The id is never guessed. Three sources, in the order they are trusted: the fields map
    # (only if getID was asked for -- ITEM_GETTERS does not, so this is a no-op here and is kept
    # because a later driver's list may), the `resolved` label (which ends `#<id>`: amendment
    # 11), then the independent `item.get` reading.
    item_id, id_source = None, None
    srv_item = out.get("item_server")
    if isinstance(srv_item, dict):
        fid = (srv_item.get("fields") or {}).get("getID") if \
            isinstance(srv_item.get("fields"), dict) else None
        if fid is not None:
            item_id, id_source = fid, "item_server.fields.getID"
        else:
            m = re.search(r"#(\d+)\s*$", str(srv_item.get("resolved") or ""))
            if m:
                item_id, id_source = m.group(1), "item_server.resolved (#<id> suffix)"
    if item_id is None and isinstance(out.get("item_get_server"), dict):
        gid = num(out["item_get_server"].get("id"))
        if gid is not None:
            item_id, id_source = int(gid), "item_get_server.id (item.get, independent reading)"
    out["session"]["item_id"] = item_id
    out["session"]["item_id_source"] = id_source
    if item_id is None:
        out["item_byid"] = {"skipped": "no id in any reply: neither a getID field, nor a "
                                       "#<id> suffix on `resolved`, nor item.get's `id`"}
        out["probes"]["item_byid"] = {"skipped": out["item_byid"]["skipped"]}
    else:
        probe("item_byid", server, "server", "witness.fields",
              f"item #{item_id} {ITEM_GETTERS}")
    save(path, out, tl, server)

    # ---- 4. missing vs nils --------------------------------------------------
    probe("absent_getter", server, "server", "witness.fields", f"player {USER} {ABSENT_GETTERS}")
    save(path, out, tl, server)

    # ---- 5. witness.moddata: the census, then the S6 triple ------------------
    probe("moddata_census_server", server, "server", "witness.moddata", f"player:{USER} *")
    out["session"]["moddata_set"] = ask(c, "moddata.set", f"{MOD_KEY} {MOD_VALUE}")
    tl.mark("moddata_set", key=MOD_KEY, value=MOD_VALUE)
    probe("moddata_client", c, "client", "witness.moddata", MOD_KEY)
    probe("moddata_server_before", server, "server", "witness.moddata", f"player:{USER} {MOD_KEY}")
    out["session"]["moddata_transmit"] = ask(c, "moddata.transmit")
    tl.mark("moddata_transmit")
    time.sleep(TRANSMIT_SETTLE)
    probe("moddata_server_after", server, "server", "witness.moddata", f"player:{USER} {MOD_KEY}")
    save(path, out, tl, server)

    # ---- 6. the other two scopes ---------------------------------------------
    probe("moddata_global", server, "server", "witness.moddata", f"global:{GLOBAL_TABLE} *")
    probe("moddata_item", server, "server", "witness.moddata", f"item:{USER}/{ITEM_TYPE} *")
    save(path, out, tl, server)

    # ---- 7. the shape gates: where a bare STRING is the documented answer ----
    probe("gate_bad_subject_word", server, "server", "witness.fields", "bogus x y",
          expect="string")
    probe("gate_bare_scope_word", server, "server", "witness.moddata", "item", expect="string")
    probe("gate_item_no_id", server, "server", "witness.fields", "item", expect="table")
    out["session"]["time_end"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 8. the graded outcome table ----------------------------------------
    # (a) the same command on both sides
    for side_name in ("server", "client"):
        r = out.get(f"player_{side_name}")
        fields = r.get("fields") if isinstance(r, dict) else None
        cnt, trunc, untrunc = truncation_note(r)
        got = sorted(fields) if isinstance(fields, dict) else None
        grade(f"witness.fields player, {side_name} side",
              "as expected" if (isinstance(fields, dict) and fields and untrunc)
              else ("miss" if not isinstance(fields, dict) else "finding"),
              "a non-empty `fields` map for the 5 requested getters, `truncatedAt` absent",
              {"resolved": (r or {}).get("resolved") if isinstance(r, dict) else None,
               "count": cnt, "truncatedAt": trunc, "fields": got,
               "missing": listy((r or {}).get("missing")) if isinstance(r, dict) else None,
               "nils": listy((r or {}).get("nils")) if isinstance(r, dict) else None},
              bool(isinstance(fields, dict) and fields and untrunc),
              values=fields if isinstance(fields, dict) else None)
    # (b) the client ignores <user>
    wu = out.get("player_client_wrong_user")
    wu_resolved = wu.get("resolved") if isinstance(wu, dict) else None
    grade("client ignores <user> (subjectOf resolves the LOCAL player)",
          "as expected" if wu_resolved == USER else ("finding" if isinstance(wu, dict)
                                                     else "miss"),
          f"`witness.fields player {BAD_USER} ...` on the CLIENT answers for {USER!r} anyway "
          f"-- `resolved` is the disclosure",
          {"resolved": wu_resolved, "fields": (wu.get("fields") if isinstance(wu, dict)
                                               else None)},
          wu_resolved == USER)
    # (c) the failure shape on the server
    bu = out.get("player_server_bad_user")
    bu_ok = isinstance(bu, dict) and bu.get("resolved") is False and bool(bu.get("error"))
    grade("unresolved subject answers a TABLE (resolved=false + error), not a string",
          "as expected" if bu_ok else ("miss" if not isinstance(bu, dict) else "finding"),
          "a dict with `resolved: false` and an `error` naming the missing subject",
          {"shape": shape_of(bu), "resolved": bu.get("resolved") if isinstance(bu, dict)
           else None, "error": bu.get("error") if isinstance(bu, dict) else bu}, bu_ok)
    # (d) the item, against the dataset, on both sides
    item_rows = {}
    for side_name in ("server", "client"):
        r = out.get(f"item_{side_name}")
        fields = r.get("fields") if isinstance(r, dict) else None
        rows, bad = {}, []
        for getter, column, factor, label in ITEM_EXPECT:
            expected = None if not apple or apple.get(column) is None \
                else apple[column] * factor
            live = num((fields or {}).get(getter)) if isinstance(fields, dict) else None
            band = tol(expected, live)
            match = (expected is not None and live is not None
                     and abs(live - expected) <= band)
            rows[getter] = {"dataset_column": column, "factor": factor, "transform": label,
                            "expected": expected, "live": live, "tolerance": band,
                            "diff": (None if expected is None or live is None
                                     else live - expected),
                            "match": match}
            if not match:
                bad.append(getter)
        item_rows[side_name] = rows
        cnt, trunc, untrunc = truncation_note(r)
        grade(f"witness.fields item {ITEM_TYPE}, {side_name} side, vs data/food-items.json",
              "as expected" if (not bad and untrunc) else ("miss" if not isinstance(fields, dict)
                                                           else "finding"),
              "the four macros and getHungChange match the dataset within the float32 band",
              {"resolved": (r or {}).get("resolved") if isinstance(r, dict) else None,
               "count": cnt, "truncatedAt": trunc, "mismatched": bad,
               "missing": listy((r or {}).get("missing")) if isinstance(r, dict) else None,
               "nils": listy((r or {}).get("nils")) if isinstance(r, dict) else None},
              bool(not bad and untrunc), comparison=rows)
    out["item_comparison"] = item_rows
    # (d2) the two sides against each other -- the brief: matching and differing are BOTH results
    sf = out.get("item_server", {}).get("fields") if isinstance(out.get("item_server"), dict) \
        else None
    cf = out.get("item_client", {}).get("fields") if isinstance(out.get("item_client"), dict) \
        else None
    cross = {}
    if isinstance(sf, dict) and isinstance(cf, dict):
        for k in sorted(set(sf) | set(cf)):
            a, b = sf.get(k), cf.get(k)
            an, bn = num(a), num(b)
            same = (abs(an - bn) <= tol(an, bn)) if (an is not None and bn is not None) \
                else (a == b)
            cross[k] = {"server": a, "client": b, "same": bool(same)}
    differ = sorted(k for k, v in cross.items() if not v["same"])
    out["item_sides_cross_check"] = cross
    grade("item fields: server side vs client side",
          "as expected" if (cross and not differ) else ("miss" if not cross else "finding"),
          "both sides read the same instance, so the same values (a difference is a RESULT, "
          "not a failure -- record which)",
          {"compared": sorted(cross), "differ": differ,
           "server_resolved": (out.get("item_server") or {}).get("resolved")
           if isinstance(out.get("item_server"), dict) else None,
           "client_resolved": (out.get("item_client") or {}).get("resolved")
           if isinstance(out.get("item_client"), dict) else None},
          bool(cross and not differ))
    # (e) the #<id> route
    bi = out.get("item_byid")
    same_item = (isinstance(bi, dict) and isinstance(out.get("item_server"), dict)
                 and bi.get("resolved") == out["item_server"].get("resolved")
                 and isinstance(bi.get("fields"), dict) and bool(bi["fields"]))
    grade("witness.fields item #<id> resolves the same instance",
          "as expected" if same_item else ("miss" if not isinstance(bi, dict)
                                           or "skipped" in bi else "finding"),
          "the `#<id>` route answers the same `resolved` label as the fullType route",
          {"id": item_id, "id_source": id_source,
           "resolved": bi.get("resolved") if isinstance(bi, dict) else None,
           "resolved_by_fulltype": (out.get("item_server") or {}).get("resolved")
           if isinstance(out.get("item_server"), dict) else None,
           "fields": sorted(bi["fields"]) if isinstance(bi, dict)
           and isinstance(bi.get("fields"), dict) else None},
          bool(same_item))
    # (f) missing vs nils
    ag = out.get("absent_getter")
    ag_missing = listy(ag.get("missing")) if isinstance(ag, dict) else None
    ag_nils = listy(ag.get("nils")) if isinstance(ag, dict) else None
    cnt, trunc, untrunc = truncation_note(ag)
    grade("absent getters land in `missing`, not in `fields`",
          "as expected" if (ag_missing is not None and "getNoSuchThing" in ag_missing)
          else ("miss" if not isinstance(ag, dict) else "finding"),
          "`getNoSuchThing` in `missing`; `getCalories` too if IsoPlayer does not expose it "
          "(it lives on Nutrition) -- so `missing` may hold BOTH names",
          {"missing": ag_missing, "nils": ag_nils, "count": cnt,
           "fields": ag.get("fields") if isinstance(ag, dict) else None,
           "getCalories_in_missing": bool(ag_missing and "getCalories" in ag_missing),
           "getNoSuchThing_in_missing": bool(ag_missing and "getNoSuchThing" in ag_missing)},
          bool(ag_missing is not None and "getNoSuchThing" in ag_missing))
    # (g) the modData triple
    mc, mb, ma = (out.get("moddata_client"), out.get("moddata_server_before"),
                  out.get("moddata_server_after"))

    def mod_value(r):
        return (r.get("values") or {}).get(MOD_KEY) if isinstance(r, dict) \
            and isinstance(r.get("values"), dict) else None

    def mod_absent(r):
        m = listy(r.get("missing")) if isinstance(r, dict) else None
        return bool(m is not None and MOD_KEY in m)

    triple_ok = (mod_value(mc) == MOD_VALUE and mod_value(mb) is None
                 and mod_value(ma) == MOD_VALUE)
    grade("modData triple: client writes, server sees it only after transmitModData",
          "as expected" if triple_ok else ("miss" if not all(isinstance(x, dict)
                                                             for x in (mc, mb, ma))
                                           else "finding"),
          f"client `{MOD_KEY}` = {MOD_VALUE!r}; server absent BEFORE transmitModData, present "
          f"AFTER (slice 06's S6 shape, through the generic command)",
          {"client": {"resolved": (mc or {}).get("resolved"), "value": mod_value(mc),
                      "keyCount": (mc or {}).get("keyCount"), "count": (mc or {}).get("count")},
           "server_before": {"resolved": (mb or {}).get("resolved"), "value": mod_value(mb),
                             "key_in_missing": mod_absent(mb),
                             "keyCount": (mb or {}).get("keyCount")},
           "server_after": {"resolved": (ma or {}).get("resolved"), "value": mod_value(ma),
                            "key_in_missing": mod_absent(ma),
                            "keyCount": (ma or {}).get("keyCount")}},
          bool(triple_ok))
    # (h) the player census
    cs = out.get("moddata_census_server")
    cs_keys = listy(cs.get("keys")) if isinstance(cs, dict) else None
    grade("witness.moddata census of a player's modData",
          "as expected" if isinstance(cs, dict) and cs.get("resolved") and not cs.get("error")
          else ("miss" if not isinstance(cs, dict) else "finding"),
          "`keys` is every top-level key as sorted `<name>:<type>`, `keyCount` its size, and "
          "`count` is 0 because `*` reads no named key",
          {"resolved": (cs or {}).get("resolved"), "keys": cs_keys,
           "keyCount": (cs or {}).get("keyCount"), "count": (cs or {}).get("count"),
           "error": (cs or {}).get("error")},
          bool(isinstance(cs, dict) and cs.get("resolved") and not cs.get("error")))
    # (i) global: -- the getOrCreate disclosure (amendment 3)
    g = out.get("moddata_global")
    g_keys = listy(g.get("keys")) if isinstance(g, dict) else None
    g_err = g.get("error") if isinstance(g, dict) else None
    if isinstance(g, dict) and not g_err:
        g_verdict, g_ok = "as expected", True
        g_note = ("global ModData is reachable through ModData.getOrCreate; an EMPTY census is "
                  "the expected result and it is evidence of the binding, not of any mod -- "
                  "getOrCreate CREATED this table, the probe did")
    elif isinstance(g, dict) and "getOrCreate" in str(g_err):
        g_verdict, g_ok = "finding", False
        g_note = ("no ModData.getOrCreate on this build: keep the route, and teardowns must "
                  "read global modData through a mod-specific command instead")
    else:
        g_verdict, g_ok = ("finding" if isinstance(g, dict) else "miss"), False
        g_note = "unexpected reply; recorded verbatim"
    grade("witness.moddata global:<name> (ModData.getOrCreate)", g_verdict,
          "either an empty census (the binding exists AND the probe created the table) or the "
          "documented 'no ModData.getOrCreate on this build' finding",
          {"scope": (g or {}).get("scope"), "arg": (g or {}).get("arg"),
           "resolved_present": isinstance(g, dict) and "resolved" in g,
           "keys": g_keys, "keyCount": (g or {}).get("keyCount"), "error": g_err,
           "note": g_note}, g_ok)
    # (j) item: scope
    mi = out.get("moddata_item")
    mi_keys = listy(mi.get("keys")) if isinstance(mi, dict) else None
    grade("witness.moddata item:<user>/<fullType> census",
          "as expected" if isinstance(mi, dict) and mi.get("resolved") and not mi.get("error")
          else ("miss" if not isinstance(mi, dict) else "finding"),
          "the item resolves with the owner-prefixed label and its modData is censused",
          {"resolved": (mi or {}).get("resolved"), "keys": mi_keys,
           "keyCount": (mi or {}).get("keyCount"), "error": (mi or {}).get("error")},
          bool(isinstance(mi, dict) and mi.get("resolved") and not mi.get("error")))
    # (k) the three shape gates
    g1, g2, g3 = (out.get("gate_bad_subject_word"), out.get("gate_bare_scope_word"),
                  out.get("gate_item_no_id"))
    g1_ok = isinstance(g1, str) and g1.startswith("usage:")
    g2_ok = isinstance(g2, str) and g2.startswith("usage:")
    g3_ok = isinstance(g3, dict) and str(g3.get("error") or "").startswith("usage:")
    grade("shape gates: where a bare STRING is the documented answer",
          "as expected" if (g1_ok and g2_ok and g3_ok) else "finding",
          "a bad <player|item> word and a bare `item`/`global` scope word answer the usage "
          "STRING; `witness.fields item` with no id answers a TABLE whose error starts 'usage:'",
          {"bad_subject_word": {"shape": shape_of(g1), "reply": g1, "ok": g1_ok},
           "bare_scope_word": {"shape": shape_of(g2), "reply": g2, "ok": g2_ok},
           "item_no_id": {"shape": shape_of(g3),
                          "error": g3.get("error") if isinstance(g3, dict) else g3,
                          "resolved": g3.get("resolved") if isinstance(g3, dict) else None,
                          "ok": g3_ok}},
          bool(g1_ok and g2_ok and g3_ok))
    # (l) the empty-list shape, measured rather than asserted from the source
    empties = {}
    for key in sorted(out["probes"]):
        r = out.get(key)
        if not isinstance(r, dict):
            continue
        for field in ("missing", "nils", "keys"):
            if field in r and not r[field]:
                empties[f"{key}.{field}"] = {"json_type": shape_of(r[field]), "value": r[field]}
    out["empty_list_shapes"] = empties
    all_dicts = bool(empties) and all(v["json_type"] == "dict" for v in empties.values())
    grade("an empty missing / nils / keys arrives as `{}`, not `[]`",
          "as expected" if all_dicts else ("miss" if not empties else "finding"),
          "TK.json encodes an empty Lua table as an object, so every later driver must test "
          "emptiness with `not x` and assert on `count` / `keyCount`",
          {"empty_fields_seen": sorted(empties), "types": sorted(
              {v["json_type"] for v in empties.values()})}, all_dicts)
    save(path, out, tl, server)
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"] = f"{type(e).__name__}: {e}"
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # No world change to restore: the client's one modData write and the spawned apple live in
    # this run directory's own copy of the fixture. Teardown is the whole cleanup path.
    out["wall_seconds"] = round(time.time() - t_start, 1)
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        out["wall_seconds"] = round(time.time() - t_start, 1)
        faults = fault_reasons(server, clients)
        lua_err = {cl.username: ("lua_error" in cl.seen) for cl in clients}
        rows = out.get("grading") or []
        out["summary"] = {
            "rows": len(rows),
            "as_expected": sum(1 for r in rows if r["verdict"] == "as expected"),
            "findings": sum(1 for r in rows if r["verdict"] == "finding"),
            "misses": sum(1 for r in rows if r["verdict"] == "miss"),
            "not_as_expected": [r["row"] for r in rows if r["verdict"] != "as expected"],
            "probes": len(out.get("probes") or {}),
            "reasked_probes": sorted(k for k, v in (out.get("probes") or {}).items()
                                     if v.get("reasked")),
            "bus_errors": sorted(k for k, v in (out.get("probes") or {}).items()
                                 if v.get("bus_error")),
            "server_error_count": len(server.errors),
            "client_lua_errors": lua_err,
            "faults": faults,
            "doctor_clean": doctor_clean,
            "dataset_sha256": out["meta"]["dataset_sha256"],
            "harness_lua_commit": out["meta"]["harness_lua_commit"],
            "head_commit": out["meta"]["head_commit"],
            "wall_seconds": out["wall_seconds"],
            "error": out.get("error"),
        }
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "witness-probe.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied -> {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:9000])
