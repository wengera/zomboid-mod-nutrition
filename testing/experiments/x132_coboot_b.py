"""x132-coboot-b -- a SECOND co-boot run (a new driver and a new run, never an edit of the first):
`x132_coboot.py` verbatim but for (1) one boot only, `x13-coboot`, and (2) three more markers.

Why: run x132b-20261005-071013 read `QualityCooking.Server` as a table on both sides, but that table
is created by QualityCooking's SHARED init (`QualityCookingInit.lua:3`); the server file that wraps
`ISEatFoodAction.complete` (`server/EventHandlers/CookingRollHandler.lua`) prints nothing, and an
RCON Apple carries no tier, so no buff can show it ran. That run therefore did not witness
QualityCooking's wrap being installed on the server. `CookingRollHandler.lua:14` creates
`QualityCooking.Server.EventHandlers.Roll` at file scope beside its unconditional save-and-replace of
`complete` (`:172-176`), and `CookingBuffTicker.lua:13` creates `...EventHandlers.BuffTicker`: a
`Roll` table that resolves on the server is the reading that the wrap's file ran. Prediction:
`Roll` and `BuffTicker` resolve as tables on the server (and on the client, whose Lua state also runs
`server/` files); `Roll.ApplyBuff` a function. Everything else (the eat, its reads, its grades) is
the first driver's, its predictions unchanged, including `.outermost` FALSE as pre-registered there;
the first run read it TRUE and that reading stands. The cross-boot X45b grade needs the control and
is not repeated (the first run's control boot is the comparison).

x132-coboot -- X45a (QualityCooking and BeyondTen co-boot beside the mod) and X45b (does the mod's
eat wrapper compose with QualityCooking's save-and-replace wrap of ISEatFoodAction.complete, and
which wrap is outermost). Plan 2 Task 15, session 1, TWO boots of one session:

  A  `x13-coboot`          PZTestKit, NutritionRevamp, ItemQuality, QuestSystem, QualityCooking,
                           MoodleFramework, BeyondTen, TKX_EatProbe (Mods= order).
  B  `x13-coboot-control`  the same without QualityCooking and its three requirements (BeyondTen
                           stays, so the control isolates QualityCooking alone).

The run id prefix is `x132b` (the register's run-id grammar refuses a hyphen in a prefix).
Copied from `x132_eat_b.py` (the item route, the probe/step/grade wrappers, `to_num`) and from
`x131_calcrepro.py` (the two-boot shape: one sub-directory per boot, each restored from the golden
fixture and torn down before the next).

THE ITEM ROUTE (x121 M5, as x132_eat_b.py): the Apple is spawned SERVER-side by RCON `additem` and
polled until it resolves on the client before `eat.action` is sent; `item.get admin Base.Apple`
on the server gives the prediction (no TKX_ItemOverride in either profile, so the vanilla Apple:
95 kcal expected; the prediction uses the live server read). `foodtimer.set admin 0` before the eat.

`witness.moddata` answers every value as a STRING (the Task 13 lesson): every counter and record
field is parsed through `to_num` and its parsed value asserted present in the phase.

PREDICTIONS AND FALSIFIERS (written before the run):

  X45a (#2094), boot A. Each marker resolves on BOTH sides, client first: `QualityCooking.Server`
      a table (its type and keyCount reported), `BeyondTen.VERSION` "1.3.4", `TKX_EatProbe.version`
      1 (THE CONTROL: it must resolve in the same read, so a nil beside it names the mod, not the
      command), `NutritionRevamp.version` "0.1.0"; the consoles carry no Lua error (compiled regex,
      limit >= 2x predicted). Falsifier: a nil marker (names the mod and the side), a Lua error
      line, a failed join (the client's kick line names the pair).
  X45b (#2095), both boots. One `eat.action Base.Apple 1`:
      - TKX_EatProbe `.enter` +1 and `.exit` +1 on the server (the sentinel wrap survived one eat
        with its saved original called); the client's stay 0 (the probe wraps server-side only);
      - the stores move ONCE: server calories +item calories (drift-corrected, within 3 kcal); a
        doubled intake says a wrap re-entered the original;
      - the mod: `stats.eats` +1, `stats.landed` +1, `failures` +0, `lastIntake.share` 1.0
        (its wrapper composed and captured);
      - `.outermost`: boot A FALSE (QualityCooking's server file runs after the probe's and wraps
        it: QC -> probe -> mod -> vanilla; the controller's pre-run note), boot B TRUE (nothing
        wraps the probe). NOTE written before the run: the profile x13-coboot's own header
        comment expects the probe outermost (Mods= puts it last); the outermost reading decides;
      - every mod read finite (stats, lastIntake, stomach.bulk, stomachFill, the client mirror's
        stomachFill and pool_*) and HUNGER finite on both sides after the eat (intake fix-3).
        A NaN or non-finite value is a BLOCKING finding, not a reading;
      - QualityCooking's per-eat effect: a `cookingBuff` record under QuestSystemPersistent
        `players.<steamId|username>`. PRE-REGISTERED DEVIATION from the amendments: an Apple
        spawned by RCON carries no `QualityCookingTier` item-modData key, and eatWithBuff returns
        `callOriginal()` with no buff when the tier's points are 0
        (CookingRollHandler.lua:150-155), so the buff is predicted ABSENT on this eat; no harness
        command can stamp an item's modData server-side. The census is recorded; QualityCooking's
        wrap having RUN is read instead off `.outermost` (false in A, true in B: something loaded
        after the probe replaced complete only when the QC stack is present) together with
        `.enter` +1 (that wrapper called its saved original, the probe).
      Falsifier: `.enter` without `.exit` (the chain below raised or never returned); a doubled
      intake; the mod's `eats` 0 while the stores moved (a non-chaining wrap above the mod removed
      its capture -- the wall named in the intake file's limitations); a stack overflow or a
      NetTimedAction.perform raise on the eat (the cycle hazard #2835: the arm stops, its server
      errors are recorded, graded unmeasured).
      The control boot's counts and store change are what the co-boot's must match (apart from the
      buff and `.outermost`).

**The two rules a driver never breaks.**

  1. A driver is NEVER edited after its run. If something has to change, that is a new driver and a
     new run, and a post-run edit is a skew note.
  2. A reading that comes back `trivial` or `unmeasured` is written down as such. Never re-run a
     phase to make a number prettier.
"""
import json
import math
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

PROFILES = {"A": "x13-coboot"}
SESSION = ("X45a + X45b: the mod co-booted with QualityCooking (+ ItemQuality, QuestSystem, "
           "MoodleFramework) and BeyondTen, the markers read on both sides; one eat.action "
           "Base.Apple 1 against TKX_EatProbe's enter/exit/outermost and the mod's intake; boot B "
           "the same without the QualityCooking stack (the control)")
ARTIFACT = "coboot.json"
USER = "admin"
# Task 14's measuring boot, the last accepted run (it smoke-tested the Task 12 commands).
ACCEPTANCE_RUN = "x132e-20261005-063700"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

# ---- the markers (X45a), each read client first then server -------------------------------------
MARKERS = ["TK.version", "TKX_EatProbe.version", "NutritionRevamp.version", "QualityCooking",
           "QualityCooking.Server", "BeyondTen", "BeyondTen.VERSION", "QuestSystem",
           "QuestSystem.PersistentData", "ItemQuality",
           "QualityCooking.Server.EventHandlers.Roll", "QualityCooking.Server.EventHandlers.BuffTicker",
           "QualityCooking.Server.EventHandlers.Roll.ApplyBuff"]
EXPECT = {"TKX_EatProbe.version": 1, "NutritionRevamp.version": "0.1.0", "BeyondTen.VERSION": "1.3.4"}
QC_MARKERS = ("QualityCooking", "QualityCooking.Server", "QuestSystem", "QuestSystem.PersistentData",
              "ItemQuality")

# ---- the probe, the mod's intake and record -------------------------------------------------------
PROBE = ["TKX_EatProbe.enter", "TKX_EatProbe.exit", "TKX_EatProbe.outermost"]
INTAKE = "NutritionRevamp.server.intake"
REC = "NutritionRevamp.server.store.records." + USER
SERVER_GLOBALS = PROBE + [INTAKE + ".stats.eats", INTAKE + ".stats.landed",
                          INTAKE + ".stats.failures", INTAKE + ".stats.cancels",
                          INTAKE + ".stats.passthrough", INTAKE + ".lastError",
                          INTAKE + ".wrappedComplete", INTAKE + ".wrappedServerStop",
                          REC + ".lastIntake.share", REC + ".lastIntake.frac",
                          REC + ".stomachFill"]
MIRROR = "NutritionRevamp.client.mirror"
CLIENT_GLOBALS = PROBE + [MIRROR + ".stomachFill", MIRROR + ".pool_calories", MIRROR + ".pool_fibre",
                          MIRROR + ".pool_water", "NutritionRevamp.client.received"]
STORE_TABLE = "NutritionRevamp.players"
REC_KEYS = [f"{USER}.stomach.bulk", f"{USER}.stomach.buffer.calories", f"{USER}.stomachFill",
            f"{USER}.kineticsAge", f"{USER}.lastIntake.share", f"{USER}.lastIntake.frac",
            f"{USER}.lastIntake.fullType", f"{USER}.pool.calories", f"{USER}.pool.fibre",
            f"{USER}.pool.water"]
REC_ARGS = f"global:{STORE_TABLE} " + " ".join(REC_KEYS)
REC_FIELD_COUNT = len(REC_KEYS)
FINITE_REC = [k for k in REC_KEYS if not k.endswith("fullType")]
QC_ARGS = "global:QuestSystemPersistent players"

APPLE_SEED = {"fibre": 4.4, "water": 155.8}            # SEED Base.Apple (NR_Data_Nutrients)
KCAL_TOL = 3.0
SHARE_TOL = 0.01
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
POLL_S, POLL_MAX_S = 0.5, 20.0
SETTLE_S = 1.5
LATE_S = 6.0                                           # a second read: a late second landing shows
DRIFT_GAP_S = 6.0

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE")
MODLINE_RX = re.compile(r"QualityCooking|BeyondTen|QuestSystem|ItemQuality|MoodleFramework")
KICK_RX = re.compile(r"[Kk]ick|checksum|[Mm]ismatch|Connection failed")
LUAERR_LIMIT, MODLINE_LIMIT, KICK_LIMIT = 40, 40, 20


def to_num(v):
    """A number from a number OR a numeric string (witness.moddata answers strings); None else."""
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


def finite_check(v):
    """'finite' / 'NON-FINITE' / 'absent'. A present value that does not parse is NON-FINITE."""
    if v is None:
        return "absent"
    n = to_num(v)
    if n is None or not math.isfinite(n):
        return "NON-FINITE"
    return "finite"


def wall():
    return round(time.time() - t0, 3)


def note(msg):
    out["notes"].append({"wall": wall(), "boot": cur.get("label"), "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        for label, srv in servers.items():
            if srv is not None:
                out["boots"][label]["server_errors"] = srv.errors[:20]
                out["boots"][label]["server_error_count"] = len(srv.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                       # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def probe(side, cmd, args, timeout=20):
    """One read with its own wall bracket; the re-ask-once guard."""
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
    elif meta.get("reasked"):
        out["notes"].append({"reask_failed": meta, "second_reply": val})
    return val


def step(name, side, cmd, args="", timeout=30):
    t_before = wall()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args,
           "side": "server" if side is cur.get("server") else "client",
           "wall_before": t_before, "wall_after": t_after,
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    cur["B"]["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    persist()
    return row


def grade(phase, predicted, observed, verdict, falsifier):
    row = {"phase": phase, "predicted": predicted, "falsifier": falsifier,
           "observed": observed, "verdict": verdict, "wall": wall()}
    out["verdicts"][phase] = row
    tl.mark("verdict", name=phase, verdict=verdict)
    persist()
    return row


def gv(reply):
    if isinstance(reply, dict) and reply.get("resolved") and "value" in reply:
        return reply.get("value")
    return None


def diff(a, b):
    if a is None or b is None:
        return None
    return b - a


def md_values(reply):
    return (reply.get("values") or {}) if isinstance(reply, dict) else {}


def read_markers(tag):
    rows = {}
    for name in MARKERS:
        cr = probe(cur["client"], "lua.global", name)
        sr = probe(cur["server"], "lua.global", name)
        rows[name] = {"client": cr, "server": sr}
    cur["B"]["markers"][tag] = rows
    persist()
    return rows


def marker_summary(rows):
    s = {}
    for name, pair in rows.items():
        s[name] = {}
        for side in ("client", "server"):
            r = pair[side]
            if not isinstance(r, dict):
                s[name][side] = {"reply": r}
                continue
            s[name][side] = {"resolved": r.get("resolved"), "type": r.get("type"),
                             "value": r.get("value"), "keyCount": r.get("keyCount"),
                             "failedAt": r.get("failedAt")}
    return s


def snapshot(tag):
    """Every read at one tag: stats.get both sides (client first), nutrition.get server, the mod's
    record (one atomic witness.moddata of the store table), the server and client globals,
    QualityCooking's store census (both sides), the server's Apple."""
    c, srv = cur["client"], cur["server"]
    snap = {"tag": tag, "wall_start": wall()}
    snap["stats"] = {"client": probe(c, "stats.get", ""), "server": probe(srv, "stats.get", USER)}
    snap["nutrition_server"] = probe(srv, "nutrition.get", USER)
    snap["record"] = probe(srv, "witness.moddata", REC_ARGS)
    cnt = snap["record"].get("count") if isinstance(snap["record"], dict) else None
    if cnt != REC_FIELD_COUNT:
        cur["B"]["field_count_failures"].append({"tag": tag, "read": "record", "count": cnt,
                                                 "expected": REC_FIELD_COUNT})
    snap["globals"] = {"client": {n: probe(c, "lua.global", n) for n in CLIENT_GLOBALS},
                       "server": {n: probe(srv, "lua.global", n) for n in SERVER_GLOBALS}}
    snap["qc_store"] = {"client": probe(c, "witness.moddata", QC_ARGS),
                        "server": probe(srv, "witness.moddata", QC_ARGS)}
    snap["item"] = probe(srv, "item.get", f"{USER} Base.Apple")
    snap["wall_end"] = wall()
    cur["B"]["snapshots"][tag] = snap
    persist()
    return snap


def sval(snap, name, side="server"):
    return gv(snap["globals"][side].get(name))


def rval(snap, key):
    return md_values(snap["record"]).get(f"{USER}.{key}")


def finite_report(snap):
    rep = {"record": {k: finite_check(md_values(snap["record"]).get(k)) for k in FINITE_REC},
           "server_globals": {}, "client_mirror": {}, "hunger": {}}
    for n in (INTAKE + ".stats.eats", INTAKE + ".stats.landed", INTAKE + ".stats.failures",
              REC + ".lastIntake.share", REC + ".lastIntake.frac", REC + ".stomachFill"):
        rep["server_globals"][n] = finite_check(sval(snap, n))
    for n in (MIRROR + ".stomachFill", MIRROR + ".pool_calories", MIRROR + ".pool_fibre",
              MIRROR + ".pool_water"):
        rep["client_mirror"][n] = finite_check(sval(snap, n, "client"))
    for side in ("client", "server"):
        st = snap["stats"][side]
        rep["hunger"][side] = finite_check(st.get("hunger") if isinstance(st, dict) else None)
    bad = [f"{grp}:{k}" for grp, d in rep.items() for k, v in d.items() if v == "NON-FINITE"]
    hunger_bad = [s for s, v in rep["hunger"].items() if v != "finite"]
    rep["non_finite"] = bad
    rep["hunger_not_finite"] = hunger_bad
    rep["blocking"] = bool(bad or hunger_bad)
    return rep


def spawn(full_type, why):
    """RCON additem, then poll the CLIENT until the instance resolves there (x121's route)."""
    srv, c = cur["server"], cur["client"]
    ok, reply = srv.rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200],
           "wall_rcon": wall(), "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = probe(c, "witness.fields", f"item {USER}/{full_type} getID")
        res = seen.get("resolved") if isinstance(seen, dict) else None
        fields = (seen.get("fields") or {}) if isinstance(seen, dict) else {}
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": res,
                                "id": fields.get("getID")})
        if res:
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    row["server_item_get"] = probe(srv, "item.get", f"{USER} {full_type}")
    cur["B"]["spawns"].append(row)
    tl.mark("spawn", type=full_type, resolved=row["resolved"])
    persist()
    return row


def scal(snap, side="server"):
    st = snap["stats"][side]
    return to_num(st.get("calories")) if isinstance(st, dict) else None


def body(label):
    srv, c, B = cur["server"], cur["client"], cur["B"]
    B.update({"markers": {}, "snapshots": {}, "spawns": [], "field_count_failures": [],
              "phases": {}})
    # ---- X45a: the markers, then the probe and intake state at rest ----
    mk = read_markers("boot")
    B["phases"]["markers"] = marker_summary(mk)
    # ---- the Apple, server-side first ----
    sp = spawn("Base.Apple", "X45b: the one eat; RCON first -- eat.action's findOrSpawn would "
                             "client-spawn one (#0124)")
    item0 = sp.get("server_item_get") if isinstance(sp.get("server_item_get"), dict) else {}
    pred_kcal = to_num(item0.get("calories"))
    B["phases"]["apple"] = {"resolved": sp["resolved"], "calories": pred_kcal,
                            "hungChange": to_num(item0.get("hungChange")),
                            "baseHunger": to_num(item0.get("baseHunger")), "id": item0.get("id")}
    if pred_kcal is None:
        pred_kcal = 95.0
        note("item.get gave no calories; the prediction falls back to the vanilla Apple's 95")
    B["phases"]["apple"]["pred_kcal"] = pred_kcal
    B["phases"]["apple"]["pred_bulk"] = pred_kcal / 100 + APPLE_SEED["fibre"] * 0.5 + \
        APPLE_SEED["water"] / 100
    # ---- baseline + the calorie drift ----
    s0 = snapshot("pre")
    d0 = probe(srv, "nutrition.get", USER)
    t_d0 = wall()
    time.sleep(DRIFT_GAP_S)
    d1 = probe(srv, "nutrition.get", USER)
    t_d1 = wall()
    dk = diff(to_num(d0.get("calories")) if isinstance(d0, dict) else None,
              to_num(d1.get("calories")) if isinstance(d1, dict) else None)
    rate = (dk / (t_d1 - t_d0)) if dk is not None and t_d1 > t_d0 else 0.0
    B["phases"]["drift"] = {"first": d0, "second": d1, "kcal_per_s": rate}
    s1 = snapshot("pre2")                       # the baseline read right before the eat
    # ---- the eat ----
    ph = {}
    if not sp["resolved"]:
        ph["skipped"] = "the RCON Apple never resolved client-side"
        B["phases"]["eat"] = ph
        return
    ph["foodtimer"] = step("foodtimer", srv, "foodtimer.set", f"{USER} 0")["ack"]
    time.sleep(1.0)
    ack = step("eat_action", c, "eat.action", "Base.Apple 1")
    ph["ack"] = ack["ack"]
    ph["queued_wall"] = ack["wall_after"]
    base_srv = scal(s1)
    t_base = (s1["stats"]["server"].get("_probe") or {}).get("wall") \
        if isinstance(s1["stats"]["server"], dict) else None
    ph["polls"] = []
    while True:
        time.sleep(POLL_S)
        cr = probe(c, "nutrition.get", "")
        sr = probe(srv, "nutrition.get", USER)
        sc = to_num(sr.get("calories")) if isinstance(sr, dict) else None
        el = None if t_base is None else wall() - t_base
        ds = diff(base_srv, sc)
        dsc = None if ds is None or el is None else ds - rate * el
        ph["polls"].append({"wall": wall(), "since_queue": round(wall() - ph["queued_wall"], 3),
                            "server_calories": sc,
                            "client_calories": to_num(cr.get("calories")) if isinstance(cr, dict) else None,
                            "server_hunger": sr.get("hunger") if isinstance(sr, dict) else None,
                            "client_hunger": cr.get("hunger") if isinstance(cr, dict) else None,
                            "server_delta_corr": dsc})
        if (dsc is not None and dsc >= pred_kcal - KCAL_TOL) or wall() - ph["queued_wall"] >= POLL_MAX_S:
            break
    time.sleep(SETTLE_S)
    s2 = snapshot("post")
    time.sleep(LATE_S)
    s3 = snapshot("late")
    el2 = diff((s1["stats"]["server"].get("_probe") or {}).get("wall") if isinstance(s1["stats"]["server"], dict) else None,
               (s2["stats"]["server"].get("_probe") or {}).get("wall") if isinstance(s2["stats"]["server"], dict) else None)
    el3 = diff((s1["stats"]["server"].get("_probe") or {}).get("wall") if isinstance(s1["stats"]["server"], dict) else None,
               (s3["stats"]["server"].get("_probe") or {}).get("wall") if isinstance(s3["stats"]["server"], dict) else None)
    raw2, raw3 = diff(scal(s1), scal(s2)), diff(scal(s1), scal(s3))
    ph["kcal"] = {"server_before": scal(s1), "server_post": scal(s2), "server_late": scal(s3),
                  "raw_post": raw2, "raw_late": raw3,
                  "corrected_post": None if raw2 is None or el2 is None else raw2 - rate * el2,
                  "corrected_late": None if raw3 is None or el3 is None else raw3 - rate * el3,
                  "client_raw_post": diff(scal(s1, "client"), scal(s2, "client")),
                  "pred": pred_kcal}

    def dl(name, side="server", a=s1, b=s2):
        return diff(to_num(sval(a, name, side)), to_num(sval(b, name, side)))

    ph["probe"] = {"enter_delta": dl("TKX_EatProbe.enter"), "exit_delta": dl("TKX_EatProbe.exit"),
                   "enter_after": to_num(sval(s2, "TKX_EatProbe.enter")),
                   "exit_after": to_num(sval(s2, "TKX_EatProbe.exit")),
                   "outermost": sval(s2, "TKX_EatProbe.outermost"),
                   "outermost_pre": sval(s0, "TKX_EatProbe.outermost"),
                   "client_enter_after": to_num(sval(s2, "TKX_EatProbe.enter", "client")),
                   "client_exit_after": to_num(sval(s2, "TKX_EatProbe.exit", "client")),
                   "client_outermost": sval(s2, "TKX_EatProbe.outermost", "client"),
                   "late_enter_delta": dl("TKX_EatProbe.enter", b=s3)}
    ph["intake"] = {"eats_delta": dl(INTAKE + ".stats.eats"), "landed_delta": dl(INTAKE + ".stats.landed"),
                    "failures_delta": dl(INTAKE + ".stats.failures"),
                    "cancels_delta": dl(INTAKE + ".stats.cancels"),
                    "eats_late_delta": dl(INTAKE + ".stats.eats", b=s3),
                    "lastError": sval(s2, INTAKE + ".lastError"),
                    "wrappedComplete": sval(s0, INTAKE + ".wrappedComplete"),
                    "wrappedServerStop": sval(s0, INTAKE + ".wrappedServerStop"),
                    "share": to_num(sval(s2, REC + ".lastIntake.share")),
                    "frac": to_num(sval(s2, REC + ".lastIntake.frac")),
                    "share_md": to_num(rval(s2, "lastIntake.share")),
                    "fullType_md": rval(s2, "lastIntake.fullType"),
                    "bulk_before": to_num(rval(s1, "stomach.bulk")),
                    "bulk_after": to_num(rval(s2, "stomach.bulk")),
                    "buffer_kcal_before": to_num(rval(s1, "stomach.buffer.calories")),
                    "buffer_kcal_after": to_num(rval(s2, "stomach.buffer.calories")),
                    "stomachFill_before": to_num(rval(s1, "stomachFill")),
                    "stomachFill_after": to_num(rval(s2, "stomachFill"))}
    ph["intake"]["bulk_delta"] = diff(ph["intake"]["bulk_before"], ph["intake"]["bulk_after"])
    ph["intake"]["buffer_kcal_delta"] = diff(ph["intake"]["buffer_kcal_before"],
                                             ph["intake"]["buffer_kcal_after"])
    ph["finite"] = {"post": finite_report(s2), "late": finite_report(s3), "pre": finite_report(s1)}
    ph["hunger"] = {"server_post": (s2["stats"]["server"] or {}).get("hunger")
                    if isinstance(s2["stats"]["server"], dict) else None,
                    "client_post": (s2["stats"]["client"] or {}).get("hunger")
                    if isinstance(s2["stats"]["client"], dict) else None,
                    "stomachFill_post": ph["intake"]["stomachFill_after"]}
    ph["qc_store"] = {t: {side: (md_values(s["qc_store"][side]).get("players")
                                 if isinstance(s["qc_store"][side], dict) else s["qc_store"][side])
                          for side in ("client", "server")} for t, s in (("pre", s1), ("post", s2),
                                                                           ("late", s3))}
    ph["qc_store_keys"] = {t: {side: (s["qc_store"][side].get("keys")
                                      if isinstance(s["qc_store"][side], dict) else None)
                               for side in ("client", "server")} for t, s in (("pre", s1), ("post", s2))}
    post_players = ph["qc_store"]["post"]["server"]
    buff = None
    if isinstance(post_players, dict):
        for k, v in post_players.items():
            if isinstance(v, dict) and "cookingBuff" in v:
                buff = {"key": k, "cookingBuff": v.get("cookingBuff")}
    ph["qc_buff_post"] = buff
    ph["item_after"] = s2.get("item")
    B["phases"]["eat"] = ph


def grade_all():
    A, Bc = out["boots"].get("A", {}), out["boots"].get("B", {})
    # ---- X45a ----
    mk = (A.get("phases") or {}).get("markers")
    if not mk:
        grade("X45a", "every marker resolves on both sides; no Lua error", None, "unmeasured",
              "a nil marker; a Lua error; a failed join")
    else:
        rows, nil_markers = {}, []
        for name in ("QualityCooking.Server", "BeyondTen.VERSION", "TKX_EatProbe.version",
                     "NutritionRevamp.version"):
            for side in ("client", "server"):
                r = mk.get(name, {}).get(side, {})
                ok = r.get("resolved") is True
                if name in EXPECT:
                    ok = ok and r.get("value") == EXPECT[name]
                if name == "QualityCooking.Server":
                    ok = ok and r.get("type") == "table"
                rows[f"{name}@{side}"] = {"ok": ok, "type": r.get("type"), "value": r.get("value"),
                                          "keyCount": r.get("keyCount")}
                if not ok:
                    nil_markers.append(f"{name}@{side}")
        logs = A.get("logs") or {}
        errs = {"server": len(logs.get("server_luaerr") or []), "client": len(logs.get("client_luaerr") or []),
                "kick": len(logs.get("client_kick") or [])}
        control_ok = rows.get("TKX_EatProbe.version@client", {}).get("ok") and \
            rows.get("TKX_EatProbe.version@server", {}).get("ok")
        if not control_ok:
            v = "unmeasured"
        elif not nil_markers and errs["server"] == 0 and errs["client"] == 0:
            v = "as_predicted"
        else:
            v = "falsified"
        grade("X45a", "QualityCooking.Server a table, BeyondTen.VERSION 1.3.4, TKX_EatProbe.version 1 "
                      "(control), NutritionRevamp.version 0.1.0 -- each on BOTH sides; 0 Lua error "
                      "lines on either console",
              {"markers": rows, "not_ok": nil_markers, "luaerr_counts": errs,
               "verify": [v_.get("ok") for v_ in A.get("verify", [])],
               "mods_not_found": A.get("mods_not_found")}, v,
              "a nil marker (names the mod and side), a Lua error line, a failed join (kick line)")
    # ---- QualityCooking's server wrap file ran (this driver's added reading) ----
    if mk:
        rr = {}
        for name in ("QualityCooking.Server.EventHandlers.Roll", "QualityCooking.Server.EventHandlers.BuffTicker",
                     "QualityCooking.Server.EventHandlers.Roll.ApplyBuff"):
            for side in ("client", "server"):
                r = mk.get(name, {}).get(side, {})
                rr[f"{name}@{side}"] = {"resolved": r.get("resolved"), "type": r.get("type"),
                                        "keyCount": r.get("keyCount")}
        srv_ok = rr["QualityCooking.Server.EventHandlers.Roll@server"]["type"] == "table" and             rr["QualityCooking.Server.EventHandlers.Roll.ApplyBuff@server"]["type"] == "function"
        grade("QC-wrap-file", "QualityCooking.Server.EventHandlers.Roll a table and Roll.ApplyBuff a function on "
                              "the server (CookingRollHandler.lua ran, so its unconditional save-and-replace of "
                              "ISEatFoodAction.complete ran)", rr,
              "as_predicted" if srv_ok else "falsified", "Roll unresolved on the server")
    # ---- X45b per boot ----
    per = {}
    for label, Bb, want_outer in (("A", A, False),):
        ph = (Bb.get("phases") or {}).get("eat") or {}
        if not ph or "skipped" in ph:
            per[label] = {"verdict": "unmeasured", "why": ph.get("skipped") if ph else "no eat phase"}
            continue
        k = (ph.get("kcal") or {}).get("corrected_post")
        kl = (ph.get("kcal") or {}).get("corrected_late")
        pred = (ph.get("kcal") or {}).get("pred")
        pr, it = ph.get("probe") or {}, ph.get("intake") or {}
        once = k is not None and pred is not None and abs(k - pred) <= KCAL_TOL and \
            kl is not None and abs(kl - pred) <= KCAL_TOL + 2.0
        doubled = k is not None and pred is not None and k >= 2 * pred - KCAL_TOL
        overflow = any("Stack overflow" in str(e) for e in (Bb.get("server_errors") or []))
        fin = ph.get("finite", {}).get("post", {})
        row = {"kcal_corrected_post": k, "kcal_corrected_late": kl, "pred": pred, "once": once,
               "doubled": doubled, "enter_delta": pr.get("enter_delta"), "exit_delta": pr.get("exit_delta"),
               "outermost": pr.get("outermost"), "outermost_predicted": want_outer,
               "client_probe": [pr.get("client_enter_after"), pr.get("client_exit_after")],
               "eats_delta": it.get("eats_delta"), "landed_delta": it.get("landed_delta"),
               "failures_delta": it.get("failures_delta"), "share": it.get("share"),
               "bulk_delta": it.get("bulk_delta"), "buffer_kcal_delta": it.get("buffer_kcal_delta"),
               "non_finite": fin.get("non_finite"), "hunger_not_finite": fin.get("hunger_not_finite"),
               "qc_buff_post": ph.get("qc_buff_post"), "stack_overflow": overflow,
               "server_error_count": Bb.get("server_error_count")}
        if overflow:
            v = "unmeasured"
        elif fin.get("blocking"):
            v = "falsified"
        elif k is None or pr.get("enter_delta") is None or it.get("eats_delta") is None:
            v = "unmeasured"
        elif (pr.get("enter_delta") == 1 and pr.get("exit_delta") == 1 and once and not doubled
              and it.get("eats_delta") == 1 and it.get("landed_delta") == 1
              and (it.get("failures_delta") or 0) == 0
              and it.get("share") is not None and abs(it["share"] - 1.0) <= SHARE_TOL
              and pr.get("outermost") is want_outer):
            v = "as_predicted"
        else:
            v = "falsified"
        row["verdict"] = v
        per[label] = row
        grade(f"X45b-{label}", f"enter +1, exit +1; kcal +{pred} once (post and late); eats +1, landed "
                               f"+1, failures +0, share 1.0; outermost {want_outer}; every mod read and "
                               "HUNGER finite",
              row, v, "enter without exit; a doubled intake; eats 0 with the stores moved; a stack "
                      "overflow (#2835, unmeasured); a non-finite value (blocking)")
    return
    a, b = per.get("A") or {}, per.get("B") or {}
    match = {}
    for key in ("enter_delta", "exit_delta", "eats_delta", "landed_delta", "failures_delta"):
        match[key] = [a.get(key), b.get(key), a.get(key) == b.get(key)]
    ka, kb = a.get("kcal_corrected_post"), b.get("kcal_corrected_post")
    match["kcal"] = [ka, kb, ka is not None and kb is not None and abs(ka - kb) <= 2 * KCAL_TOL]
    match["outermost"] = [a.get("outermost"), b.get("outermost")]
    match["qc_buff_post"] = [a.get("qc_buff_post"), b.get("qc_buff_post")]
    if a.get("verdict") == "unmeasured" or b.get("verdict") == "unmeasured":
        v = "unmeasured"
    elif a.get("verdict") == b.get("verdict") == "as_predicted" and \
            all(m[2] for k_, m in match.items() if k_ not in ("outermost", "qc_buff_post")):
        v = "as_predicted"
    else:
        v = "falsified"
    grade("X45b", "boot A matches the control B on enter/exit/eats/landed/failures and the kcal step; "
                  "outermost false in A (QualityCooking wraps the probe), true in B; QualityCooking's "
                  "buff absent on an untiered Apple in both (pre-registered deviation)",
          {"per_boot": per, "match": match}, v,
          "a count or the kcal step differing from the control; outermost equal across the boots")


def boot(label):
    prof = profs[label]
    sub = os.path.join(run_dir, f"boot-{label}")
    os.makedirs(sub, exist_ok=True)
    B = out["boots"][label] = {"profile": prof.name, "run_subdir": f"boot-{label}", "steps": [],
                               "mods": list(prof.mods)}
    cur.clear()
    cur.update({"label": label, "B": B})
    tl.mark("boot", label=label, profile=prof.name)
    clients = []
    server = None
    B["doctor_clean"], dtext = doctor()
    B["doctor"] = dtext.strip().splitlines()
    if not B["doctor_clean"]:
        B["error"] = "doctor not clean before this boot; the boot was not started (CLAUDE.md s5)"
        persist()
        return
    try:
        server = make_server(sub, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None)
        servers[label] = server
        cur["server"] = server
        server.start(timeout=prof.server_timeout)
        B["build"] = server.build
        c, _ = make_client(sub, USER, server, rec)
        cur["client"] = c
        c.start()
        clients.append(c)
        c.wait_ready(timeout=prof.client_timeout)
        tl.mark("session_ready", label=label)
        B["session_ready_wall"] = wall()
        B["verify"] = verify(prof, server, clients, tl)
        B["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                               "client": sorted(set(c.mods_not_found))}
        persist()
        body(label)
    except Exception as e:                     # noqa: BLE001 - the boot is a result; keep its rows
        B["error"], B["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", label=label, detail=str(e)[:200])
    finally:
        B["wall_end_body"] = wall()
        persist()
        try:
            if server is not None:
                teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            B["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, clients)
            B["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            B["client_seen"] = sorted(getattr(clients[0], "seen", ())) if clients else None
            if server is not None:
                logs = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                        "server_modlines": grep_file(server.log_path, MODLINE_RX, MODLINE_LIMIT),
                        "limits": {"luaerr": LUAERR_LIMIT, "modlines": MODLINE_LIMIT, "kick": KICK_LIMIT}}
                if clients:
                    logs.update({"client_luaerr": grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT),
                                 "client_modlines": grep_file(clients[0].console, MODLINE_RX, MODLINE_LIMIT),
                                 "client_kick": grep_file(clients[0].console, KICK_RX, KICK_LIMIT)})
                B["logs"] = logs
            B["wall_end"] = wall()
            persist()


profs = {k: profile.load(v) for k, v in PROFILES.items()}
rec = None if DRY_RUN else fx.load(profs["A"].fixture)
run_id, run_dir = ("x132b-dry-run", None) if DRY_RUN else new_run_dir("x132b")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
servers, cur = {}, {}

lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profile": {k: p.report() for k, p in profs.items()},
    "mods": {k: list(p.mods) for k, p in profs.items()},
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/TKX_EatProbe"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": None,
    "acceptance_run": ACCEPTANCE_RUN,
    "dry_run": DRY_RUN,
    "constants": {"KCAL_TOL": KCAL_TOL, "SHARE_TOL": SHARE_TOL, "APPLE_SEED": APPLE_SEED,
                  "POLL_S": POLL_S, "POLL_MAX_S": POLL_MAX_S, "SETTLE_S": SETTLE_S, "LATE_S": LATE_S,
                  "REC_FIELD_COUNT": REC_FIELD_COUNT, "MARKERS": MARKERS, "EXPECT": EXPECT},
    "deviations": [
        "QualityCooking's buff is predicted ABSENT, not present: the RCON Apple carries no "
        "QualityCookingTier item-modData key, so eatWithBuff takes its no-points early return and "
        "only calls the original (CookingRollHandler.lua:150-155); no harness command stamps an "
        "item's modData server-side. QualityCooking's wrap having run is read off .outermost "
        "(false in A, true in B) with .enter +1. Decided before the run.",
        "Prediction for .outermost in boot A is FALSE per the controller's pre-run note (QC loads "
        "after the probe); x13-coboot.toml's header comment expects the probe outermost. The read "
        "decides. Decided before the run.",
        "doctor is run before EACH boot (recorded per boot); the top-level doctor_clean is the A "
        "boot's.",
    ],
    "world_changes": {"restored": "each boot restores the golden fixture into its own sub-directory",
                      "left_in_place": ["one RCON-spawned Base.Apple eaten per boot",
                                        "healthFromFoodTimer zeroed before the eat",
                                        "the record's stomach, pool and lastIntake"]},
    "boots": {}, "notes": [], "verdicts": {},
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

try:
    for label in ("A",):
        boot(label)
        if label == "A":
            out["doctor_clean"] = out["boots"]["A"].get("doctor_clean")
    try:
        grade_all()
    except Exception as e:                     # noqa: BLE001
        out["grade_error"] = f"{type(e).__name__}: {e}"
        out["grade_tb"] = traceback.format_exc()[-2000:]
    out["summary"] = {
        "verify_ok": {k: [v.get("ok") for v in b.get("verify", [])] for k, b in out["boots"].items()},
        "mods_not_found": {k: b.get("mods_not_found") for k, b in out["boots"].items()},
        "boot_errors": {k: b.get("error") for k, b in out["boots"].items()},
        "server_error_count": {k: b.get("server_error_count") for k, b in out["boots"].items()},
        "client_lua_error": {k: b.get("client_lua_error") for k, b in out["boots"].items()},
        "verdicts": {k: v["verdict"] for k, v in out["verdicts"].items()},
    }
except Exception as e:                         # noqa: BLE001 - keep the rows already collected
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    for srv in servers.values():
        try:
            hard_kill(srv, [])
        except Exception:                      # noqa: BLE001
            pass
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001 - never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1)[:7000])
