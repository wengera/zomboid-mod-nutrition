"""x141-strength-gate -- Plan 3 Task 3, the strength gate session: X50 (the perk-level write live,
minted by this task), X40 (#2085, the experience anti-cheat on a burst), X48 (#2087, which side's
protein store gates the Strength x1.5 branch) and X39's AddXP-event arm (#2084; the hit and rep
arms are Task 5's). ONE boot, profile `x14-strength` (PZTestKit + NutritionRevamp Mode 1 +
TKX_XpEvents + TKX_XpBurst), the fixture's 90-minute day (a game minute is 3.75 s wall, a
ten-minute pass 37.5 s wall). The run id prefix is `x141s`. Copied from `_template.py` (provenance,
client-first pairs, wall-bracketed steps, predictions/verdicts) and `x132_residual.py` (`to_num`,
the persist/step shape, the log greps).

SCHEDULE (in this order; X40 is LAST because a tripped check may kick the client):

  S0  setup   server `nutrition.set admin proteins 0` (the protein branch off: every grant before
              D is x1 by construction, the control for D); the TKX_XpEvents counters; the starting
              Strength XP/level; both sides' traitList. `lua.global TKX_XpBurst_Installed` (server).
  S1  cross   `xp.grant admin Strength <37600 - xp0>` (one more top-up grant if the XP is still under
              37500), so the XP implies level 6 (cumulative 37500, #2102) and STOUT is the band.
              The crossing is X39's LevelPerk reading (counter +1, gained true) and the remap's
              (STOUT present on the server).
  A   write   `perk.level admin Strength 3` (setPerkLevelDebug ONLY, Task 2). Then 15 samples ~2 s
              apart over 30 s: client `witness.chain getPerkLevel(Perks.Strength)` FIRST, then
              server `perk.xp admin Strength`; a client-first `stats.get` pair (traitList) at the
              first, middle and last sample.
  R   rust    server `moddata.set admin strengthUpTimer 30000` (a string; XpUpdate.getModData runs
              it through tonumber, XpUpdate.lua:340) and a read of strengthUpTimer/strengthMod;
              then poll the server clock until TWO game ten-minute boundaries have passed (real
              time at multiplier 1: no time.multiplier, so the #1870 restore hazard never arises),
              then read moddata, perk.xp, the counters and both sides' level/traits.
  Y   sync    client `witness.chain` level, client `xp.sync` (SyncXp(getPlayer()), Task 2), then 6
              samples ~2 s apart (client chain level + server perk.xp), a stats.get pair, counters.
  B   X39     the counters, `xp.grant admin Strength 10` x3 (each reply's xpBefore/xpAfter/
              levelBefore/levelAfter), the counters.
  D   X48     D1: server proteins 200; client-first nutrition.get pair; `xp.grant ... 100`;
              server nutrition.get. D2: server proteins 0; 2.5 s; client nutrition.get; client
              `nutrition.set proteins 200`; IMMEDIATELY server `xp.grant ... 100`; client
              nutrition.get (does the client copy still read 200 after the grant?).
  C   X40     server proteins 0; the server ini's AntiCheat* values (the run's own pzt.ini);
              `globalmoddata.set TKX_XpBurst perk Strength`, `amount 1000`, perk.xp, `fire 1`;
              poll `witness.moddata global:TKX_XpBurst firedCount fired` + perk.xp until the
              burst lands (<= 30 s); then hold 75 s (the XpChecker's 60000 ms UpdateLimit, X40's
              C-reading) with a client `ping` every 15 s; grep both logs. Control: `xp.grant ...
              1000` (the checker-refreshing route), hold 75 s with pings, grep again.

PREDICTIONS AND FALSIFIERS (written before the run):

  X50-write   perk.level replies before=6, after=3, xp unchanged (>= 37500).  Falsifier: after != 3
              or xp moved.
  X50-push    the server's level reads 3 at every A sample (nothing on the server rebuilds it) and
              the client's chain read reads 3 from its first or second sample on (the 1 s
              experience push carries the level down, #2608). Falsifier: any server sample != 3;
              a client that never reads 3 (the push does not carry a debug-written level).
  X50-rust    the forced pass FIRES (strengthMod becomes floor(timer/1200) = 25 and the Strength XP
              drops by getLoosingXpValue's step) and the level holds at 3, because
              checkForLosingLevel lowers only a level whose XP is below its requirement (#2124).
              Falsifier: level != 3 after the pass. `unmeasured` if strengthMod never moves (the
              moddata write did not take or no pass ran).
  X50-sync    the client reads 3 before the sync, so SyncXp uploads level 3 and the server stays at
              3; no AddXP/LevelPerk counter moves (#2614). Falsifier: the server level moves to a
              value other than the client's pre-sync reading, or a counter moves.
              `trivial` if the client read already equals the server's (the sync cannot be told
              from no sync); the reading is still recorded.
  X50-remap   after the write STOUT stays on the server's traitList and FEEBLE is absent (the debug
              setter fires no LevelPerk, #2119): the mod must re-run the remap. Falsifier: FEEBLE
              present / STOUT gone. `trivial` if STOUT was never present after S1.
  X39-AddXP   three grants move addxp_Strength_count by exactly +3 with lastAmount the final
              amount; the S1 crossing moved levelperk_count by +1 with lastGained true and
              lastLevel 6. Falsifier: a count that does not move.
  X48         D1: XP rises by 150 for a 100 grant at server proteins 200 (the branch runs on the
              server against the server's store, #2112). D2: XP rises by 100 (server store 0)
              whatever the client copy reads. Falsifier: D1 delta 100 (the branch is not on this
              route) -> D2 `trivial`; D2 delta 150 (the client copy gated it).
              D2 is `unmeasured` if the client write did not read 200 in its own reply.
  X40         the burst lands +1000 XP (protein 0) with no checker refresh; under the run's
              AntiCheatXP value the check (1000 x multiplier x boost; 250 at boost 0, #2147/#2149)
              trips within ~60 s: a 'xp growth is too high' server line and/or a kick (client ping
              fails). The control grant (refreshed) trips nothing. Either outcome is graded under
              the recorded settings: no line and no kick = "no trip under these settings".

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
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

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import (Timeline, grep_file, make_client,      # noqa: E402
                         make_server, teardown, verify)

PROFILE = "x14-strength"
SESSION = ("X50 perk-level write (push, rust, SyncXp, stale remap), X39 AddXP arm, X48 protein side, "
           "X40 burst under the default AntiCheat settings: one boot of x14-strength at the fixture's "
           "90-minute day")
ARTIFACT = "strength_gate.json"
USER = "admin"
ACCEPTANCE_RUN = "x132e-20261005-063700"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

PERK = "Strength"
LVL_HOP = "getPerkLevel(Perks.Strength)"
XP_HOP = "getXp.getXP(Perks.Strength)"
TARGET_XP = 37600.0              # > 37500, the cumulative total for level 6 (#2102)
L6_TOTAL = 37500.0
WRITE_LEVEL = 3
PUSH_S, PUSH_GAP = 30.0, 2.0
TRAIT_PAIR_AT = (0, 7, 14)
RUST_TIMER = "30000"
RUST_PASSES, RUST_MAX_S = 2, 110.0
SYNC_SAMPLES, SYNC_GAP = 6, 2.0
X39_GRANTS, X39_AMOUNT = 3, 10
X48_AMOUNT, X48_PROTEIN = 100, 200
BURST_AMOUNT, BURST_POLL_S = 1000, 30.0
CHECK_HOLD_S, PING_GAP = 75.0, 15.0
CONTROL_AMOUNT = 1000
EV_KEYS = ["addxp_Strength_count", "addxp_Strength_lastAmount", "addxp_Strength_lastLevel",
           "levelperk_count", "levelperk_lastPerk", "levelperk_lastLevel", "levelperk_lastGained"]
BAND = ["weak", "feeble", "stout", "strong"]

AC_RX = re.compile(r"xp growth is too high|update failed|AntiCheatXP|anticheat|anti-cheat|"
                   r"kick|doKickUser|doLogUser|suspicious", re.IGNORECASE)
LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
AC_LIMIT, LUAERR_LIMIT = 60, 40
INI_RX = re.compile(r"^\s*AntiCheat\w*\s*=")


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


def note(msg):
    out["notes"].append({"wall": wall(), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:20]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is server else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def grade(phase, predicted, observed, verdict, falsifier):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def sleep_until(target_wall):
    while wall() < target_wall:
        time.sleep(min(0.25, max(0.0, target_wall - wall())))


def band_of(tlist):
    names = []
    if isinstance(tlist, dict):
        tlist = list(tlist.values())
    if not isinstance(tlist, list):
        return None
    for x in tlist:
        names.append(str(x).lower().split(":")[-1].split(".")[-1])
    return sorted(b for b in BAND if b in names)


def perk_xp(tag):
    r = step(tag, server, "perk.xp", f"{USER} {PERK}")
    a = ack(r)
    return {"tag": tag, "wall": r["wall_before"], "xp": to_num(a.get("xp")), "level": to_num(a.get("level")),
            "worldAge": a.get("serverWorldAge")}


def chain(tag, hop):
    r = step(tag, client, "witness.chain", hop)
    a = ack(r)
    return {"tag": tag, "wall": r["wall_before"], "ok": a.get("ok"), "value": to_num(a.get("value")),
            "raw": a.get("value"), "failedAt": a.get("failedAt")}


def trait_pair(tag):
    rc = step(f"{tag}_stats_client", client, "stats.get", "")
    rs = step(f"{tag}_stats_server", server, "stats.get", USER)
    c_, s_ = ack(rc), ack(rs)
    p = {"tag": tag, "client_wall": rc["wall_before"], "server_wall": rs["wall_before"],
         "client_traitList": c_.get("traitList"), "server_traitList": s_.get("traitList"),
         "client_band": band_of(c_.get("traitList")), "server_band": band_of(s_.get("traitList")),
         "client_proteins": c_.get("proteins"), "server_proteins": s_.get("proteins")}
    out["trait_pairs"].append(p)
    return p


def events(tag):
    r = step(tag, server, "witness.moddata", "global:TKX_XpEvents " + " ".join(EV_KEYS))
    a = ack(r)
    vals = a.get("values") if isinstance(a.get("values"), dict) else {}
    e = {"tag": tag, "wall": r["wall_before"], "values": vals, "missing": a.get("missing"),
         "keys": a.get("keys"),
         "addxp_count": to_num(vals.get("addxp_Strength_count")) or 0.0,
         "levelperk_count": to_num(vals.get("levelperk_count")) or 0.0}
    out["events"].append(e)
    return e


def grant(tag, amount):
    r = step(tag, server, "xp.grant", f"{USER} {PERK} {amount}")
    a = ack(r)
    g = {"tag": tag, "amount": amount, "wall": r["wall_before"], "ok": a.get("ok"), "error": a.get("error"),
         "xpBefore": to_num(a.get("xpBefore")), "xpAfter": to_num(a.get("xpAfter")),
         "levelBefore": to_num(a.get("levelBefore")), "levelAfter": to_num(a.get("levelAfter"))}
    g["delta"] = (None if g["xpBefore"] is None or g["xpAfter"] is None else g["xpAfter"] - g["xpBefore"])
    out["grants"].append(g)
    return g


def nut(tag, side):
    r = step(tag, side, "nutrition.get", "" if side is client else USER)
    return to_num(ack(r).get("proteins"))


def game_minutes():
    r = step("clock", server, "time.snapshot", "")
    a = ack(r)
    h, m = to_num(a.get("hour")), to_num(a.get("minutes"))
    return None if h is None or m is None else h * 60 + m, a


def log_paths():
    paths = {"server_stdout": server.log_path, "server_console": os.path.join(server.cache, "console.txt"),
             "client_console": client.console}
    return paths


def sizes():
    o = {}
    for k, p in log_paths().items():
        try:
            o[k] = os.path.getsize(p)
        except OSError:
            o[k] = 0
    return o


def tail_grep(offsets, limit=AC_LIMIT):
    """The AC_RX lines written to each log AFTER `offsets` (byte sizes taken earlier): a boot that
    prints many matching lines cannot crowd the new ones out of a capped grep."""
    o = {}
    for k, p in log_paths().items():
        hits = []
        try:
            with open(p, "rb") as fh:
                fh.seek(offsets.get(k, 0))
                for raw in fh.read().decode("utf-8", errors="replace").splitlines():
                    if AC_RX.search(raw):
                        hits.append(raw.strip()[:240])
                        if len(hits) >= limit:
                            break
        except OSError:
            pass
        o[k] = hits
    return o


def ping_client(tag):
    r = step(tag, client, "ping", "", timeout=15)
    return r["ack"] == "pong"


def body():
    P = out["phases"]
    # ---------------- S0 setup ----------------
    S0 = P["S0"] = {}
    S0["burst_installed"] = ack(step("burst_installed", server, "lua.global", "TKX_XpBurst_Installed"))
    S0["events_installed"] = ack(step("events_installed", server, "lua.global", "TKX_XpEvents_Installed"))
    S0["proteins_before"] = nut("s0_prot_server", server)
    S0["prot_set"] = ack(step("s0_prot0", server, "nutrition.set", f"{USER} proteins 0"))
    S0["xp0"] = perk_xp("s0_xp")
    S0["events0"] = events("s0_events")
    S0["traits0"] = trait_pair("s0")
    S0["client_level0"] = chain("s0_client_level", LVL_HOP)
    persist()
    # ---------------- S1 crossing to level 6 ----------------
    S1 = P["S1"] = {}
    x0 = S0["xp0"]["xp"] or 0.0
    S1["grant"] = grant("s1_grant", int(round(TARGET_XP - x0)))
    after = perk_xp("s1_xp")
    if after["xp"] is not None and after["xp"] < L6_TOTAL:
        S1["topup"] = grant("s1_topup", int(round(TARGET_XP - after["xp"])))
        after = perk_xp("s1_xp2")
    S1["xp1"] = after
    S1["events1"] = events("s1_events")
    time.sleep(2.0)
    S1["traits1"] = trait_pair("s1")
    S1["client_level1"] = chain("s1_client_level", LVL_HOP)
    persist()
    # ---------------- A the level write + the push window ----------------
    A = P["A"] = {}
    w = step("a_write", server, "perk.level", f"{USER} {PERK} {WRITE_LEVEL}")
    A["write"] = ack(w)
    A["write_wall"] = w["wall_after"]
    A["samples"] = []
    start = wall()
    i = 0
    while wall() < start + PUSH_S:
        sleep_until(start + i * PUSH_GAP)
        s = {"i": i, "client": chain(f"a{i}_client", LVL_HOP), "server": perk_xp(f"a{i}_server")}
        if i in TRAIT_PAIR_AT:
            s["traits"] = trait_pair(f"a{i}")
        A["samples"].append(s)
        i += 1
    if not any("traits" in s for s in A["samples"][-1:]):
        A["traits_end"] = trait_pair("a_end")
    A["client_xp_end"] = chain("a_client_xp", XP_HOP)
    A["events"] = events("a_events")
    persist()
    # ---------------- R the forced rust pass ----------------
    R = P["R"] = {}
    R["set"] = ack(step("r_set", server, "moddata.set", f"{USER} strengthUpTimer {RUST_TIMER}"))
    R["md0"] = ack(step("r_md0", server, "witness.moddata", f"player:{USER} strengthUpTimer strengthMod"))
    R["xp0"] = perk_xp("r_xp0")
    R["events0"] = events("r_events0")
    m0, snap0 = game_minutes()
    R["clock0"] = snap0
    R["clock_polls"] = []
    passes = 0
    last_bucket = None if m0 is None else int(m0 // 10)
    end = wall() + RUST_MAX_S
    while wall() < end and passes < RUST_PASSES:
        time.sleep(3.0)
        m, snap = game_minutes()
        R["clock_polls"].append({"wall": wall(), "hour": snap.get("hour"), "minutes": snap.get("minutes")})
        if m is not None and last_bucket is not None and int(m // 10) != last_bucket:
            passes += 1
            last_bucket = int(m // 10)
    time.sleep(2.0)
    R["boundaries_seen"] = passes
    R["md1"] = ack(step("r_md1", server, "witness.moddata", f"player:{USER} strengthUpTimer strengthMod"))
    R["xp1"] = perk_xp("r_xp1")
    R["events1"] = events("r_events1")
    R["client_level"] = chain("r_client_level", LVL_HOP)
    R["traits"] = trait_pair("r")
    persist()
    # ---------------- Y the admin SyncXp ----------------
    Y = P["Y"] = {}
    Y["client_level_before"] = chain("y_client_level0", LVL_HOP)
    Y["client_xp_before"] = chain("y_client_xp0", XP_HOP)
    Y["server_before"] = perk_xp("y_server0")
    Y["events0"] = events("y_events0")
    sy = step("y_sync", client, "xp.sync", "")
    Y["sync"] = sy["ack"]
    Y["sync_wall"] = sy["wall_after"]
    Y["samples"] = []
    start = wall()
    for i in range(SYNC_SAMPLES):
        sleep_until(start + i * SYNC_GAP)
        Y["samples"].append({"i": i, "client": chain(f"y{i}_client", LVL_HOP),
                             "server": perk_xp(f"y{i}_server")})
    Y["traits"] = trait_pair("y")
    Y["events1"] = events("y_events1")
    persist()
    # ---------------- B X39 AddXP ----------------
    B = P["B"] = {}
    B["events0"] = events("b_events0")
    B["grants"] = [grant(f"b_grant{i}", X39_AMOUNT) for i in range(X39_GRANTS)]
    time.sleep(1.0)
    B["events1"] = events("b_events1")
    persist()
    # ---------------- D X48 protein side ----------------
    D = P["D"] = {}
    D["d1_set"] = ack(step("d1_prot", server, "nutrition.set", f"{USER} proteins {X48_PROTEIN}"))
    time.sleep(2.5)
    D["d1_client_prot"] = nut("d1_prot_client", client)
    D["d1_server_prot"] = nut("d1_prot_server", server)
    D["d1_grant"] = grant("d1_grant", X48_AMOUNT)
    D["d1_server_prot_after"] = nut("d1_prot_server_after", server)
    D["d2_set_server"] = ack(step("d2_prot0", server, "nutrition.set", f"{USER} proteins 0"))
    time.sleep(2.5)
    D["d2_client_prot_before"] = nut("d2_prot_client0", client)
    cw = step("d2_client_set", client, "nutrition.set", f"proteins {X48_PROTEIN}")
    D["d2_client_set"] = ack(cw)
    D["d2_client_set_proteins"] = to_num(ack(cw).get("proteins"))
    D["d2_grant"] = grant("d2_grant", X48_AMOUNT)
    D["d2_gap_s"] = round(D["d2_grant"]["wall"] - cw["wall_after"], 3)
    D["d2_client_prot_after"] = nut("d2_prot_client1", client)
    D["d2_server_prot_after"] = nut("d2_prot_server1", server)
    D["events"] = events("d_events")
    persist()
    # ---------------- C X40 the burst ----------------
    C = P["C"] = {}
    C["prot0"] = ack(step("c_prot0", server, "nutrition.set", f"{USER} proteins 0"))
    ini = server.ini
    lines = []
    try:
        with open(ini, encoding="utf-8", errors="replace") as fh:
            lines = [ln.strip() for ln in fh if INI_RX.match(ln)]
    except OSError as e:
        lines = [f"unreadable: {type(e).__name__}: {e}"]
    out["anticheat"] = {"settings": lines, "ini": os.path.relpath(ini, REPO).replace("\\", "/")}
    C["log_sizes_before"] = sizes()
    C["set_perk"] = ack(step("c_perk", server, "globalmoddata.set", f"TKX_XpBurst perk {PERK}"))
    C["set_amount"] = ack(step("c_amount", server, "globalmoddata.set", f"TKX_XpBurst amount {BURST_AMOUNT}"))
    C["xp_before"] = perk_xp("c_xp0")
    fire = step("c_fire", server, "globalmoddata.set", "TKX_XpBurst fire 1")
    C["fire"] = fire["ack"]
    C["fire_wall"] = fire["wall_after"]
    C["polls"] = []
    landed = None
    end = wall() + BURST_POLL_S
    while wall() < end:
        time.sleep(2.0)
        md = ack(step("c_poll_md", server, "witness.moddata", "global:TKX_XpBurst firedCount fired fire"))
        px = perk_xp("c_poll_xp")
        C["polls"].append({"wall": wall(), "values": md.get("values"), "xp": px["xp"], "level": px["level"]})
        if px["xp"] is not None and C["xp_before"]["xp"] is not None and px["xp"] > C["xp_before"]["xp"] + 1:
            landed = px
            break
    C["landed"] = landed
    C["landed_wall"] = None if landed is None else landed["wall"]
    C["pings"] = []
    hold_end = wall() + CHECK_HOLD_S
    while wall() < hold_end:
        sleep_until(min(hold_end, wall() + PING_GAP))
        C["pings"].append({"wall": wall(), "pong": ping_client("c_ping")})
    C["xp_after_hold"] = perk_xp("c_xp1")
    C["log_after_burst"] = tail_grep(C["log_sizes_before"])
    C["log_sizes_after_burst"] = sizes()
    persist()
    if C["pings"] and C["pings"][-1]["pong"]:
        C["control"] = grant("c_control", CONTROL_AMOUNT)
        C["control_pings"] = []
        hold_end = wall() + CHECK_HOLD_S
        while wall() < hold_end:
            sleep_until(min(hold_end, wall() + PING_GAP))
            C["control_pings"].append({"wall": wall(), "pong": ping_client("c_cping")})
        C["xp_after_control"] = perk_xp("c_xp2")
        C["log_after_control"] = tail_grep(C["log_sizes_after_burst"])
    else:
        note("client did not answer the last burst-hold ping: the control grant was skipped")
    persist()


def lv(x):
    return None if x is None else int(round(x))


def grade_all():
    P = out["phases"]
    S0, S1, A, R, Y, B, D, C = (P.get(k, {}) for k in ("S0", "S1", "A", "R", "Y", "B", "D", "C"))
    # ---- X50-write ----
    w = A.get("write") or {}
    xp_w = to_num(w.get("xp"))
    obs = {"before": w.get("before"), "after": w.get("after"), "xp": w.get("xp"),
           "xp_before_write": (S1.get("xp1") or {}).get("xp")}
    if not w:
        v = "unmeasured"
    elif lv(to_num(w.get("after"))) == WRITE_LEVEL and xp_w is not None and xp_w >= L6_TOTAL:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X50-write", "perk.level replies before=6, after=3, xp unchanged (>= 37500)", obs, v,
          "after != 3 or the XP moved")
    # ---- X50-push ----
    srv = [lv(s["server"]["level"]) for s in A.get("samples", [])]
    cli = [lv(s["client"]["value"]) for s in A.get("samples", [])]
    first3 = next((i for i, c in enumerate(cli) if c == WRITE_LEVEL), None)
    obs = {"server_levels": srv, "client_levels": cli, "client_first_3_index": first3,
           "sample_walls": [s["client"]["wall"] for s in A.get("samples", [])],
           "write_wall": A.get("write_wall"),
           "client_first_3_after_write_s": None if first3 is None else
           round(A["samples"][first3]["client"]["wall"] - A["write_wall"], 3)}
    if not srv or all(x is None for x in srv):
        v = "unmeasured"
    elif all(x == WRITE_LEVEL for x in srv) and first3 is not None and first3 <= 1 and \
            all(c == WRITE_LEVEL for c in cli[first3:]):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X50-push", "server level 3 at every sample; client reads 3 from sample 0 or 1 on", obs, v,
          "a server sample != 3; a client that never reads 3")
    # ---- X50-rust ----
    md0 = (R.get("md0") or {}).get("values") or {}
    md1 = (R.get("md1") or {}).get("values") or {}
    mod0, mod1 = to_num(md0.get("strengthMod")), to_num(md1.get("strengthMod"))
    x0, x1 = (R.get("xp0") or {}).get("xp"), (R.get("xp1") or {}).get("xp")
    l1 = lv((R.get("xp1") or {}).get("level"))
    obs = {"md0": md0, "md1": md1, "xp0": x0, "xp1": x1, "level_after": l1,
           "boundaries_seen": R.get("boundaries_seen"),
           "events0": (R.get("events0") or {}).get("values"), "events1": (R.get("events1") or {}).get("values")}
    if mod1 is None or mod1 == mod0:
        v = "unmeasured"
    elif l1 == WRITE_LEVEL:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X50-rust", "the forced pass fires (strengthMod -> floor(timer/1200)) and the level holds at 3",
          obs, v, "level != 3 after the pass; unmeasured if strengthMod never moves")
    # ---- X50-sync ----
    cb = lv((Y.get("client_level_before") or {}).get("value"))
    sb = lv((Y.get("server_before") or {}).get("level"))
    sa = [lv(s["server"]["level"]) for s in Y.get("samples", [])]
    ca = [lv(s["client"]["value"]) for s in Y.get("samples", [])]
    e0, e1 = Y.get("events0") or {}, Y.get("events1") or {}
    moved = (e1.get("addxp_count"), e1.get("levelperk_count")) != (e0.get("addxp_count"), e0.get("levelperk_count"))
    obs = {"sync_ack": Y.get("sync"), "client_before": cb, "server_before": sb, "server_after": sa,
           "client_after": ca, "event_counter_moved": moved}
    sync_ok = isinstance(Y.get("sync"), dict) and Y["sync"].get("called") is True
    if not sync_ok or not sa:
        v = "unmeasured"
    elif any(x not in (cb,) for x in sa if x is not None) or moved:
        v = "falsified"
    elif cb == sb:
        v = "trivial"
    else:
        v = "as_predicted"
    grade("X50-sync", "SyncXp uploads the client's level; the server stays at the client's pre-sync "
                      "reading (3); no AddXP/LevelPerk counter moves (#2614)", obs, v,
          "the server moves to a level other than the client's pre-sync reading, or a counter moves; "
          "trivial when client == server before the sync")
    # ---- X50-remap ----
    t1 = S1.get("traits1") or {}
    ta = [s["traits"] for s in A.get("samples", []) if "traits" in s]
    obs = {"after_cross": {"server": t1.get("server_band"), "client": t1.get("client_band")},
           "after_write": [{"tag": t["tag"], "server": t["server_band"], "client": t["client_band"]} for t in ta]}
    if not t1 or t1.get("server_band") is None or not ta:
        v = "unmeasured"
    elif "stout" not in (t1.get("server_band") or []):
        v = "trivial"
    elif all("stout" in (t["server_band"] or []) and "feeble" not in (t["server_band"] or []) for t in ta):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X50-remap", "STOUT stays on the server traitList after the write, FEEBLE absent", obs, v,
          "FEEBLE present or STOUT gone; trivial if STOUT never present after the crossing")
    # ---- X39-AddXP ----
    b0, b1 = B.get("events0") or {}, B.get("events1") or {}
    d_add = None if not b0 or not b1 else b1["addxp_count"] - b0["addxp_count"]
    s0e, s1e = S0.get("events0") or {}, S1.get("events1") or {}
    d_lp = None if not s0e or not s1e else s1e["levelperk_count"] - s0e["levelperk_count"]
    obs = {"addxp_delta_over_3_grants": d_add, "b_values_after": b1.get("values"),
           "levelperk_delta_over_crossing": d_lp, "s1_values_after": s1e.get("values"),
           "grants": B.get("grants"), "s1_grant": S1.get("grant")}
    lp_vals = s1e.get("values") or {}
    if d_add is None or d_lp is None:
        v = "unmeasured"
    elif d_add == X39_GRANTS and d_lp >= 1 and str(lp_vals.get("levelperk_lastGained")).lower() == "true":
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X39-AddXP", "addxp_Strength_count +3 over three grants; levelperk_count +1 (gained true) over "
                       "the S1 crossing", obs, v, "a count that does not move")
    # ---- X48 ----
    g1, g2 = D.get("d1_grant") or {}, D.get("d2_grant") or {}
    obs = {"d1": {"server_prot": D.get("d1_server_prot"), "client_prot": D.get("d1_client_prot"),
                  "delta": g1.get("delta"), "server_prot_after": D.get("d1_server_prot_after")},
           "d2": {"client_set_proteins": D.get("d2_client_set_proteins"),
                  "client_before": D.get("d2_client_prot_before"),
                  "client_after": D.get("d2_client_prot_after"), "server_after": D.get("d2_server_prot_after"),
                  "delta": g2.get("delta"), "gap_s": D.get("d2_gap_s")},
           "control_deltas_b": [g.get("delta") for g in B.get("grants", [])]}
    d1, d2 = g1.get("delta"), g2.get("delta")
    if d1 is None:
        v = "unmeasured"
    elif abs(d1 - 1.5 * X48_AMOUNT) > 0.5:
        v = "falsified"
    elif d2 is None or D.get("d2_client_set_proteins") != float(X48_PROTEIN):
        v = "unmeasured"
    elif abs(d2 - X48_AMOUNT) <= 0.5:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X48", "D1 delta 150 (server store 200); D2 delta 100 (server 0, client copy 200)", obs, v,
          "D1 delta 100 (branch not on this route); D2 delta 150 (client copy gated)")
    # ---- X40 ----
    xb = (C.get("xp_before") or {}).get("xp")
    xl = (C.get("landed") or {}).get("xp")
    trip_lines = [ln for v in (C.get("log_after_burst") or {}).values() for ln in v]
    kicked = any(p["pong"] is False for p in C.get("pings", []))
    obs = {"xp_before": xb, "xp_landed": xl, "burst_delta": None if xb is None or xl is None else xl - xb,
           "new_log_lines_after_burst": trip_lines, "pings": C.get("pings"), "kicked": kicked,
           "anticheat": out.get("anticheat"), "control": C.get("control"),
           "control_pings": C.get("control_pings"),
           "new_log_lines_after_control": C.get("log_after_control")}
    tripped = any("xp growth is too high" in ln.lower() for ln in trip_lines) or kicked
    if xl is None:
        v = "unmeasured"
    elif tripped:
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X40", "a 1000-XP checker-free burst trips the XP check within ~60 s (a 'xp growth is too "
                 "high' line and/or a kick) under the run's AntiCheatXP value; the refreshed control "
                 "trips nothing", obs, v,
          "no line and no kick after 75 s = no trip under these settings")


prof = profile.load(PROFILE)
rec = None if DRY_RUN else fx.load(prof.fixture)
run_id, run_dir = ("x141s-dry-run", None) if DRY_RUN else new_run_dir("x141s")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": prof.report(),
    "mods": list(prof.mods),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_mod_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_XpBurst",
                                "testing/experiments/TKX_XpEvents"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"TARGET_XP": TARGET_XP, "L6_TOTAL": L6_TOTAL, "WRITE_LEVEL": WRITE_LEVEL,
                  "PUSH_S": PUSH_S, "PUSH_GAP": PUSH_GAP, "RUST_TIMER": RUST_TIMER,
                  "RUST_PASSES": RUST_PASSES, "SYNC_SAMPLES": SYNC_SAMPLES, "X39_GRANTS": X39_GRANTS,
                  "X39_AMOUNT": X39_AMOUNT, "X48_AMOUNT": X48_AMOUNT, "X48_PROTEIN": X48_PROTEIN,
                  "BURST_AMOUNT": BURST_AMOUNT, "CHECK_HOLD_S": CHECK_HOLD_S,
                  "CONTROL_AMOUNT": CONTROL_AMOUNT, "AC_RX": AC_RX.pattern},
    "deviations": [
        "This session is the first live use of perk.level, xp.grant, xp.sync and witness.chain (Task 2, "
        "no acceptance run since): the profile's verify rows plus each command's own reply are its smoke test.",
        "The rust arm runs at the fixture's 90-minute day and multiplier 1 (a ten-minute pass is 37.5 s "
        "wall), not under time.multiplier: two passes fit the schedule and the #1870 restore hazard is avoided.",
        "Server proteins are set to 0 before the first grant so every grant before D is x1 by construction; "
        "D sets 200/0 explicitly; C resets 0.",
        "X40 runs LAST because a tripped check may kick the client and end the session.",
    ],
    "world_changes": {"restored": "the golden fixture restored into the run dir",
                      "left_in_place": ["Strength XP ~38800+, level written 3", "proteins 0",
                                        "strengthUpTimer written 30000"]},
    "steps": [], "notes": [], "phases": {}, "verdicts": {}, "events": [], "grants": [], "trait_pairs": [],
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    server = make_server(run_dir, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None)
    server.start(timeout=prof.server_timeout)
    client, _ = make_client(run_dir, USER, server, rec)
    client.start()
    clients.append(client)
    client.wait_ready(timeout=prof.client_timeout)
    tl.mark("session_ready")
    out["session_ready_wall"] = wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, tl)
    out["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                             "client": sorted(set(client.mods_not_found))}
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001 - keep the rows already collected
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    persist()
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": [v.get("ok") for v in out.get("verify", [])],
        "mods_not_found": out.get("mods_not_found"),
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
        "anticheat": (out.get("anticheat") or {}).get("settings"),
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    try:
        if server is not None:
            teardown(tl, server, clients)
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, clients)
        out["wall_seconds"] = round(time.time() - t0, 1)
        out["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
        if server is not None:
            out["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                           "server_anticheat": grep_file(server.log_path, AC_RX, AC_LIMIT),
                           "limits": {"luaerr": LUAERR_LIMIT, "anticheat": AC_LIMIT}}
            if clients:
                out["logs"].update({"client_luaerr": grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT),
                                    "client_anticheat": grep_file(clients[0].console, AC_RX, AC_LIMIT)})
        persist()
        dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied to {dest}")
        except Exception as e:                 # noqa: BLE001 - never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error"),
                  "body_error": out.get("body_error")}, indent=1)[:7000])
