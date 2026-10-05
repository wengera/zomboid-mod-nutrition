"""x131-traits -- X4: does a server-side trait write reach the owning client's trait list, how
fast, does the mod's own trait-block push (`sendSyncPlayerFields(player, 2)`) make it arrive
sooner, and does a registered mod trait behave the same: Plan 1 Task 14.

The run id prefix is `x131t` (run id `x131t-<date>-<time>`): the register's run-id pattern (a
lowercase alphanumeric prefix, then eight and six digits) refuses a hyphen in the prefix, so the
amendments' `x131-traits-<id>` could not be named by a `run:` pointer.

Copied from `_template.py` (house shape). ONE live session, ONE boot, profile `x13-traits`
(PZTestKit + TKX_TraitProbe, the fixture's own sandbox). Phases:

  T0  client-first `stats.get` pair: the starting trait lists on both sides (no run before this
      one has held a non-empty list on either side, #2595).
  A1  control, NO push (x3): server `trait.set admin HeartyAppetite add`, its python wall
      bracket the zero; then client `stats.get` polled back to back (at least POLL_S apart) for
      up to WINDOW_S, the first poll whose `traitList` carries `heartyappetite` (names read back
      lowercased, #0550) is the arrival; then server `stats.get admin` proves the server's list
      holds it. Then `trait.set ... remove` and the same poll until the name is gone (the
      removal's arrival, a rider reading: the reset-then-add receiver must carry a removal too).
  A2  the mod's push (x3): server `trait.set admin LightEater add` then at once
      `trait.push admin 2`, whose returned `wall` (server getTimestampMs) is the push's zero;
      the same poll; server `stats.get admin`; then remove + push and the same poll for removal.
      A1 and A2 trials are interleaved (A1, A2, A1, A2, A1, A2) with GAPS between trials so
      the writes fall at different phases of the one-second experience push.
  A3  the registered trait: server `lua.global ResourceLocation.of` (which resolution branch
      the probe's `resolve` takes: the ResourceLocation branch iff that global resolves to a
      function on the server), then `moddata.set admin TKX_grant TKX:Probe`; server
      `lua.global TKX_TraitProbe.grants` polled until it rises (the probe grants on its next
      OnTick); then `moddata.set admin TKX_push 1`, and client `stats.get` polled for
      `tkx:probe` (a list entry containing `probe`, case-folded) from the grant's observation
      for up to WINDOW_S; server `stats.get admin` proves the server holds it;
      `TKX_TraitProbe.lastId` read. Then `TKX_grant -TKX:Probe` + `TKX_push 1` and the removal
      poll.

Timing method. Every client `stats.get` reply carries `wall`, the client's own getTimestampMs
at the snapshot; `trait.push` returns the server's getTimestampMs at the call. Both processes
run on this host and share its clock, so a client snapshot wall minus a server wall is a
latency. A `trait.set` reply carries no wall, so its zero is the python bracket
[send, ack-seen] in epoch ms: the server executed the write inside that bracket (the python
poller sees an ack up to 0.25 s after it is written). The arrival is bracketed by two client
snapshots: the last poll without the name (`prev_wall`) and the first with it (`hit_wall`), so
the true arrival lies in (prev_wall, hit_wall]; the headline arrival is hit_wall minus the
zero, an upper bound, and prev_wall minus the zero is the lower bound. Poll resolution is the
client bus round trip (the game polls its command file about three times a second), about
0.3-0.5 s, which is coarser than a network hop: a sub-poll difference between arms is not a
reading.

PREDICTIONS AND FALSIFIERS (written before the run):

  A1 (#2608, #2595, #2099): the trait arrives on the client with NO push, on the once-a-second
      experience packet: hit_wall - set-bracket-start <= 1.0 s + one poll interval in every
      trial (headline bound: arrival within 1.5 s), spread across the second by where the write
      fell in the push cycle. Falsifier: absent at +WINDOW_S (5 s) in any trial (the experience
      carrier does not carry the list, or the receiver does not load it). The server read must
      hold the name; a server list that does not hold it makes the trial `unmeasured`.
  A2 (#2595, #2099): the push carries the list at once: arrival measured from the push's own
      wall sits below one poll interval, and A2's arrivals measured from the set's bracket are
      no later than A1's. Falsifier: absent at +WINDOW_S. An A2 spread inside A1's spread is
      written `not discriminated` (the push and the experience packet are not separated at this
      resolution), never re-run.
  A3 (#2099's third question): `tkx:probe` arrives like A2's trait, because the client loads
      the same mod and its registries.lua registers the id on the client too. Falsifier: the
      server holds it and the client never shows it within WINDOW_S: the receiver's resolver
      does not know the registered trait's definition. A server that never holds it (grants
      does not rise, or the server list lacks it) makes A3 `unmeasured`.
  Removal riders (no row rests on them unless they settle): each removal arrives inside the
      same bounds as its add.

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
import shutil
import statistics
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

PROFILE = "x13-traits"
SESSION = ("X4: a server-side trait write timed to the owning client's trait list -- no push "
           "(x3), trait.set + trait.push mask 2 (x3), and a registered mod trait TKX:Probe "
           "granted by TKX_TraitProbe and pushed; client stats.get polled for the arrival")
ARTIFACT = "traits.json"
USER = "admin"
ACCEPTANCE_RUN = "x131b-20261004-175911"

POLL_S = 0.25          # minimum spacing between two client polls
WINDOW_S = 5.0         # how long a poll waits for an arrival (or a removal)
GRANT_WAIT_S = 10.0    # how long A3 waits for the probe's grant counter to rise
GAPS = [1.37, 2.11, 1.73, 2.59, 1.19, 2.33]   # sleeps before each A1/A2 trial: varied phase
FIELD_COUNT = 9        # stats.get `traits` block: 5 WEIGHT_TRAITS + 4 APPETITE_TRAITS
A1_TRAIT, A1_NAME = "HeartyAppetite", "heartyappetite"
A2_TRAIT, A2_NAME = "LightEater", "lighteater"
A3_ID, A3_MATCH = "TKX:Probe", "probe"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"


def wall():
    return round(time.time() - t0, 3)


def ms():
    return int(time.time() * 1000)


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


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


def has_name(lst, match, exact=True):
    if not isinstance(lst, list):
        return None
    for n in lst:
        s = str(n).lower()
        if (s == match) if exact else (match in s):
            return True
    return False


def snap(side, tag):
    """One stats.get (client: no args; server: admin), reduced to what the arms read."""
    args = "" if side is not server else USER
    t_b, e_b = wall(), ms()
    val = ask(side, "stats.get", args)
    t_a, e_a = wall(), ms()
    row = {"tag": tag, "side": "client" if side is not server else "server",
           "wall_before": t_b, "wall_after": t_a, "epoch_ms_before": e_b, "epoch_ms_after": e_a}
    if isinstance(val, dict):
        traits = val.get("traits")
        row["traitList"] = val.get("traitList")
        row["traitRoute"] = val.get("traitRoute")
        row["traits"] = traits
        row["field_count"] = len(traits) if isinstance(traits, dict) else None
        row["field_count_ok"] = row["field_count"] == FIELD_COUNT
        row["snap_wall"] = num(val.get("wall"))
        row["worldAge"] = num(val.get("worldAge"))
    else:
        row["reply"] = val
    return row


def poll(tag, match, want_present, zero_ms, exact=True):
    """Client stats.get back to back (>= POLL_S apart) until `match` is present (want_present)
    or absent (not want_present), or WINDOW_S has passed since the poll began."""
    rows, prev, hit = [], None, None
    start = time.time()
    while time.time() - start < WINDOW_S:
        t_s = time.time()
        r = snap(c, tag)
        r["has"] = has_name(r.get("traitList"), match, exact)
        if not r.get("field_count_ok"):
            out["field_count_failures"].append({"tag": tag, "field_count": r.get("field_count")})
        rows.append(r)
        if r["has"] is not None and r["has"] == want_present:
            hit = r
            break
        if r.get("snap_wall") is not None:
            prev = r
        left = POLL_S - (time.time() - t_s)
        if left > 0:
            time.sleep(left)
    res = {"tag": tag, "match": match, "want_present": want_present, "zero_ms": zero_ms,
           "polls": len(rows), "rows": rows, "arrived": hit is not None}
    if hit is not None and hit.get("snap_wall") is not None and zero_ms is not None:
        res["hit_wall"] = hit["snap_wall"]
        res["hit_ms"] = hit["snap_wall"] - zero_ms
        if prev is not None:
            res["prev_wall"] = prev["snap_wall"]
            res["prev_ms"] = prev["snap_wall"] - zero_ms
        res["first_poll_hit"] = len(rows) == 1
    return res


def proof(tag, match, exact=True):
    r = snap(server, tag)
    r["has"] = has_name(r.get("traitList"), match, exact)
    if not r.get("field_count_ok"):
        out["field_count_failures"].append({"tag": tag, "field_count": r.get("field_count")})
    return r


def trial_vanilla(arm, k, trait, name, push):
    tag = f"{arm}_{k}"
    tr = {"arm": arm, "trial": k, "trait": trait, "push": push}
    tr["pre_client"] = snap(c, f"{tag}_pre_client")
    tr["pre_client_has"] = has_name(tr["pre_client"].get("traitList"), name)
    s = step(f"{tag}_set_add", server, "trait.set", f"{USER} {trait} add")
    tr["set"] = s
    tr["set_zero_ms"] = {"start": s["epoch_ms_before"], "end": s["epoch_ms_after"]}
    zero = s["epoch_ms_before"]
    if push:
        p = step(f"{tag}_push_add", server, "trait.push", f"{USER} 2")
        tr["push"] = p
        pw = num(p["ack"].get("wall")) if isinstance(p["ack"], dict) else None
        tr["push_wall"] = pw
    tr["add_poll"] = poll(f"{tag}_add", name, True, zero)
    if push and tr.get("push_wall") is not None and tr["add_poll"].get("hit_wall") is not None:
        tr["add_poll"]["hit_ms_from_push"] = tr["add_poll"]["hit_wall"] - tr["push_wall"]
        if tr["add_poll"].get("prev_wall") is not None:
            tr["add_poll"]["prev_ms_from_push"] = tr["add_poll"]["prev_wall"] - tr["push_wall"]
    tr["server_after_add"] = proof(f"{tag}_server_after_add", name)
    s2 = step(f"{tag}_set_remove", server, "trait.set", f"{USER} {trait} remove")
    tr["remove"] = s2
    zero2 = s2["epoch_ms_before"]
    if push:
        p2 = step(f"{tag}_push_remove", server, "trait.push", f"{USER} 2")
        tr["push_remove"] = p2
        tr["push_remove_wall"] = num(p2["ack"].get("wall")) if isinstance(p2["ack"], dict) else None
    tr["remove_poll"] = poll(f"{tag}_remove", name, False, zero2)
    if (push and tr.get("push_remove_wall") is not None
            and tr["remove_poll"].get("hit_wall") is not None):
        tr["remove_poll"]["hit_ms_from_push"] = (tr["remove_poll"]["hit_wall"]
                                                 - tr["push_remove_wall"])
    tr["server_after_remove"] = proof(f"{tag}_server_after_remove", name)
    out["trials"].append(tr)
    save(path, out, tl, server)
    return tr


def spread(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return {"n": len(v), "min": min(v), "median": statistics.median(v), "max": max(v),
            "values": v}


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x131t-dry-run", None) if DRY_RUN else new_run_dir("x131t")
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
    "constants": {"POLL_S": POLL_S, "WINDOW_S": WINDOW_S, "GRANT_WAIT_S": GRANT_WAIT_S,
                  "GAPS": GAPS, "FIELD_COUNT": FIELD_COUNT},
    "world_changes": {"restored": "every trait added is removed in the same trial",
                      "left_in_place": []},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "trials": [],
    "field_count_failures": [],
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

    # ---- T0: starting lists, client first --------------------------------------------------
    out["phases"]["T0"] = {"client": snap(c, "t0_client"), "server": snap(server, "t0_server")}
    save(path, out, tl, server)

    # ---- A1 / A2 interleaved ---------------------------------------------------------------
    order = [("A1", 1), ("A2", 1), ("A1", 2), ("A2", 2), ("A1", 3), ("A2", 3)]
    for i, (arm, k) in enumerate(order):
        time.sleep(GAPS[i])
        if arm == "A1":
            trial_vanilla(arm, k, A1_TRAIT, A1_NAME, push=False)
        else:
            trial_vanilla(arm, k, A2_TRAIT, A2_NAME, push=True)

    # ---- A3: the registered trait ----------------------------------------------------------
    a3 = {}
    a3["route_probe"] = {
        "ResourceLocation": step("a3_rl", server, "lua.global", "ResourceLocation")["ack"],
        "ResourceLocation.of": step("a3_rl_of", server, "lua.global", "ResourceLocation.of")["ack"],
        "client_registry": step("a3_client_reg", c, "lua.global",
                                "TKX_TraitProbe_Traits.probe")["ack"],
    }
    a3["pre_client"] = snap(c, "a3_pre_client")
    g0 = step("a3_grants_before", server, "lua.global", "TKX_TraitProbe.grants")
    grants0 = num(g0["ack"].get("value")) if isinstance(g0["ack"], dict) else None
    a3["grants_before"] = grants0
    gs = step("a3_grant", server, "moddata.set", f"{USER} TKX_grant {A3_ID}")
    a3["grant_set"] = gs
    grant_seen, gpolls = None, []
    t_g = time.time()
    while time.time() - t_g < GRANT_WAIT_S:
        r = step("a3_grants_poll", server, "lua.global", "TKX_TraitProbe.grants")
        v = num(r["ack"].get("value")) if isinstance(r["ack"], dict) else None
        gpolls.append({"value": v, "epoch_ms_after": r["epoch_ms_after"]})
        if v is not None and grants0 is not None and v > grants0:
            grant_seen = r
            break
        time.sleep(POLL_S)
    a3["grants_polls"] = gpolls
    a3["granted"] = grant_seen is not None
    ps = step("a3_push", server, "moddata.set", f"{USER} TKX_push 1")
    a3["push_set"] = ps
    a3["add_poll"] = poll("a3_add", A3_MATCH, True, gs["epoch_ms_before"], exact=False)
    if a3["add_poll"].get("hit_wall") is not None:
        a3["add_poll"]["hit_ms_from_push_set"] = (a3["add_poll"]["hit_wall"]
                                                  - ps["epoch_ms_before"])
    a3["server_after_add"] = proof("a3_server_after_add", A3_MATCH, exact=False)
    a3["lastId"] = step("a3_lastid", server, "lua.global", "TKX_TraitProbe.lastId")["ack"]
    rs = step("a3_remove", server, "moddata.set", f"{USER} TKX_grant -{A3_ID}")
    a3["remove_set"] = rs
    time.sleep(0.5)
    a3["push_remove_set"] = step("a3_push_remove", server, "moddata.set", f"{USER} TKX_push 1")
    a3["remove_poll"] = poll("a3_remove", A3_MATCH, False, rs["epoch_ms_before"], exact=False)
    a3["server_after_remove"] = proof("a3_server_after_remove", A3_MATCH, exact=False)
    a3["removes"] = step("a3_removes", server, "lua.global", "TKX_TraitProbe.removes")["ack"]
    a3["lastId_after_remove"] = step("a3_lastid2", server, "lua.global",
                                     "TKX_TraitProbe.lastId")["ack"]
    out["phases"]["A3"] = a3
    save(path, out, tl, server)

    # ---- grading ---------------------------------------------------------------------------
    def arm_rows(arm):
        return [t for t in out["trials"] if t["arm"] == arm]

    summ = {}
    for arm in ("A1", "A2"):
        ts = arm_rows(arm)
        summ[arm] = {
            "server_held": [t["server_after_add"].get("has") for t in ts],
            "set_listed": [(t["set"]["ack"] or {}).get("held") if isinstance(t["set"]["ack"], dict)
                           else None for t in ts],
            "pre_client_has": [t["pre_client_has"] for t in ts],
            "arrived": [t["add_poll"]["arrived"] for t in ts],
            "add_hit_ms": spread([t["add_poll"].get("hit_ms") for t in ts]),
            "add_prev_ms": spread([t["add_poll"].get("prev_ms") for t in ts]),
            "add_first_poll_hit": [t["add_poll"].get("first_poll_hit") for t in ts],
            "removed": [t["remove_poll"]["arrived"] for t in ts],
            "remove_hit_ms": spread([t["remove_poll"].get("hit_ms") for t in ts]),
        }
        if arm == "A2":
            summ[arm]["add_hit_ms_from_push"] = spread(
                [t["add_poll"].get("hit_ms_from_push") for t in ts])
            summ[arm]["add_prev_ms_from_push"] = spread(
                [t["add_poll"].get("prev_ms_from_push") for t in ts])
            summ[arm]["set_to_push_ms"] = spread(
                [(t["push_wall"] - t["set_zero_ms"]["start"]) if t.get("push_wall") else None
                 for t in ts])
            summ[arm]["remove_hit_ms_from_push"] = spread(
                [t["remove_poll"].get("hit_ms_from_push") for t in ts])
    out["phases"]["A1A2_summary"] = summ

    for arm in ("A1", "A2"):
        s = summ[arm]
        if not all(x is True for x in s["server_held"]):
            v = "unmeasured"
        elif not all(s["arrived"]):
            v = "falsified"
        elif arm == "A1":
            v = "as_predicted" if s["add_hit_ms"]["max"] <= 1500 else "falsified"
        else:
            a1 = summ["A1"]["add_hit_ms"]
            a2 = s["add_hit_ms"]
            if a1 is None or a2 is None:
                v = "unmeasured"
            elif a2["max"] < a1["min"]:
                v = "as_predicted"
            else:
                v = "not discriminated"
        grade(arm,
              predicted=("arrival within 1.5 s of the set with no push (experience packet)"
                         if arm == "A1" else
                         "arrival below A1's spread, at about one poll after the push"),
              observed=s, verdict=v,
              falsifier="absent on the client at +5 s while the server holds the name")

    a3add = a3["add_poll"]
    if not a3["granted"] or a3["server_after_add"].get("has") is not True:
        v3 = "unmeasured"
    elif not a3add["arrived"]:
        v3 = "falsified"
    else:
        v3 = "as_predicted"
    grade("A3", predicted="tkx:probe arrives on the client like A2's trait",
          observed={"granted": a3["granted"], "server_has": a3["server_after_add"].get("has"),
                    "server_list": a3["server_after_add"].get("traitList"),
                    "arrived": a3add["arrived"], "hit_ms": a3add.get("hit_ms"),
                    "prev_ms": a3add.get("prev_ms"),
                    "hit_ms_from_push_set": a3add.get("hit_ms_from_push_set"),
                    "client_list_at_hit": (a3add["rows"][-1].get("traitList")
                                           if a3add["rows"] else None),
                    "removed": a3["remove_poll"]["arrived"],
                    "remove_hit_ms": a3["remove_poll"].get("hit_ms")},
          verdict=v3,
          falsifier="server holds tkx:probe and the client never shows it within 5 s")

    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out["mods_not_found"],
        "field_count_failures": len(out["field_count_failures"]),
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "A1": summ["A1"]["add_hit_ms"], "A2": summ["A2"]["add_hit_ms"],
        "A2_from_push": summ["A2"].get("add_hit_ms_from_push"),
        "A3": {"arrived": a3add["arrived"], "hit_ms": a3add.get("hit_ms")},
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
