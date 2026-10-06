"""x161p-seats -- Plan 5 Task 4, gate 2: the perception, trait and ownership seats, live. TWO boots,
serial, one driver. Boot 1 is profile `x16-seats` (SleepAllowed and SleepNeeded true); boot 2 is
`x16-seats-sleepoff` (both false). Both carry PZTestKit + NutritionRevamp (Mode 1, LegacyMirror, HEAD's
tree) + TKX_TraitProbe + TKX_StatWatch, `Nutrition = false`, DayLength 1 (a game hour is 37.5 s wall, a
game minute 0.625 s). Boot 1 runs to completion and is torn down; the driver then polls `pzt doctor`
until the game Java is gone before boot 2 starts (one live session at a time). The run id prefix is
`x161p`; ONE artifact `seats.json` carries `boot1` and `boot2` blocks. Shape: x151_sleep_gate.py (two
boots) with x161_surfaces_gate.py's helpers (step, stats.all, the StatWatch arm/collect).

THE X IDS (platform briefing s 9; X75-X81 and X88 are gate 1's): X82 INTOXICATION ownership, X83 fatigue
ownership on a sleep-off server (boot 2), X84 night vision live, X85 Short Sighted weapon sight, X86 the
aiming-delay seat, X87 the landing side; X47 the speed write (existing row #2096) and X4b the residual of
X4 (the band edges at 50 and 65 kg, an admin SyncXp carrying a different trait list).

THE HARNESS FOR THIS RUN (committed before it; this run is their smoke test):
  cfc8e7f  client `sight.range [wear <fullType>|unwear]` (getMaxSightRange(p) and getMinSightRange(p)
           on the primary-hand weapon, a client-only glasses wear), client `trait.local <Trait>
           <add|remove> [sync]` (a client-copy trait edit and SyncXp in the same tick), client
           `event.watch <EventName>` (a counting listener with the aiming delay at each firing).
  c9b76d0  TKX_StatWatch hold arm (holdMode handler: the probe wraps NutritionRevamp.kernel.fast.step,
           which the takeover handler calls every update inside Hook.CalculateStats, and after it sets
           out.fatigue = holdFatigue and writes INTOXICATION = holdIntox -- the handler-path seat;
           holdMode tick: the same writes on OnTick) and band arm (setWeight + applyTraitFromWeight in one
           server tick, the trait list read back).

SCHEDULE.
  boot 1 (x16-seats):
    S0   stats.all and stats.get both sides, time.snapshot both, intox.reduction read, fluid.script
         Beer, the client Aiming and Strength levels, health both sides, the ini, the mod version,
         tick.rate 10 (the multiplier per tick), the weight adapter's counters.
    X82  (a) intox.reduction admin 0; StatWatch 30 s; INTOXICATION 40 written once armed; pairs.
         (b) RCON additem Base.BeerCan resolved on the client; StatWatch 40 s; drink.action
         Base.BeerCan 1 (server `drink` fallback at 25 s if the server can still holds its litres);
         pairs and the server can's litres ~1 Hz.
         (c) intox.reduction back to the value read in S0 (decay on); INTOXICATION 0; StatWatch 22 s;
         hold handler holdIntox 25 for 16 s; client/server stats.all pairs; hold status read.
         (d) INTOXICATION 0.
    X84  client trait.watch nightvision 8; server trait.add.push admin NIGHT_VISION; wait_result;
         stats.get pair (traitList both sides); time.snapshot (the hour; the ambient floor is C-only,
         #3027, no arm spent on it).
    X4b  (control) client `trait.local NIGHT_VISION remove` (no sync); client stats.get polled ~4 s
         and the server's once; (sync) the client list re-checked (trait.push admin if NV is not back);
         client `trait.local NIGHT_VISION remove sync`; server stats.get polled ~5 s, the client's
         after; cleanup trait.set remove + trait.push.
         (bands) for 49.9, 50.1, 64.9, 65.1 kg: band_status reset; `bandW <kg>`; band keys read; a server
         stats.get at once and a client stats.get ~2 s later (the mod's weight minute re-asserts its own
         weight and band in between: recorded, not graded); the adapter counters after.
    X85  sight.range (no trait); client trait.watch shortsighted 8 + server trait.add.push admin
         SHORT_SIGHTED; sight.range; sight.range wear Base.Glasses_Prescription; sight.range unwear;
         trait.set admin SHORT_SIGHTED remove + trait.push; sight.range.
    X47  standing: anim.probe WalkSpeed 0.3 250 16, wait_result; walking: player.walk 20 0, 0.5 s,
         anim.probe WalkSpeed 0.3 250 16, wait_result, player.stop.
    X87  health both; StatWatch 20 s with FALLDOWN counters at -1; server fall.probe admin (listener);
         client fall.probe admin 2; wait_result fall-probe (9 s); server fall.probe admin (records);
         health both; then the direct arm: client fall.probe admin 0 land 2.0; the same reads;
         StatWatch collected; every part health 100 and fractureTime 0.
    X86  (last: the zombie) client event.watch OnWeaponSwing, OnPlayerAttackFinished,
         OnWeaponSwingHitPoint; zombie.near 1; W1 vanilla: aim.probe admin 10, aim.fire 3,
         wait_result aim-probe; the weapon's aimingTime and recoilDelay through witness.chain;
         W2 bump: aim.probe admin 10, aim.bump 6.25, aim.fire 3, wait_result; W3 a bump with no shot:
         aim.probe admin 6, after 2 s aim.bump 6.25 now, wait_result; the three event reads; the
         server event view is not read (no server listener; the client is the hit roll's side).
    Z    the mod's counters and lastError, health, stats.
  boot 2 (x16-seats-sleepoff):
    S0   as boot 1 (no beer script, no tick.rate repeat: the multiplier is read from stats.all).
    X83  (a) baseline: StatWatch 20 s; client/server stats.all pairs (the mod's own FATIGUE write on a
         sleep-off server); (b) hold handler holdFatigue 0.42 for 20 s inside a 25 s StatWatch window;
         pairs; (c) hold tick holdFatigue 0.42 for 20 s inside a 25 s window; pairs; (d) 10 s of pairs
         after.
    Z    as boot 1.

PREDICTIONS (written before the run). M ~1800 multiplier units per game hour (#2951's 7.5599 / 0.0042);
mult per server tick ~4.8 at 10 ticks per second.
  X82 (#2918, #2921, #2923, #2951): (a) with the reduction 0 INTOXICATION 40 holds flat (max - min under
      1e-3 over 30 s = 48 game minutes; falsifier any fall above 0.02); (b) the beer adds 0.3 x 0.05 x 400
      = 6 (x1.25 when HUNGER is in (0.6, 0.8], x1.1 above 0.8) and then holds flat; (c) with the
      reduction restored (0.0042) a handler-path hold of 25 is the later write: the per-tick sampler and
      every client copy read 25 exactly while the hold stands; falsifier a server sample at 25 - 0.0042 x
      mult (the decay after the write) or a client copy off 25; after the hold the decay resumes.
  X84 (#2099, #3027): the client first sees nightvision <= 32 ms after the push's wallAfter; the
      ambient floor is C-only.
  X4b (#2620, #2740, #2759, #0155): control: a client-only removal is restored on the client by the
      1 Hz experience push within ~1 s and the server keeps NV; sync: the server's list loses NV at the
      next read (XP.load replaces the list) -- falsified if the server keeps NV. Bands (#0531 table,
      both ends inclusive): 49.9 emaciated, 50.1 very underweight, 64.9 very underweight, 65.1
      underweight, each read on the server in the setting tick.
  X85 (#2331): without the trait getMaxSightRange(p) = 6.0 x (1 + Aiming/30); with SHORT_SIGHTED and no
      glasses it equals getMinSightRange(p) (2 at the item's MinSightRange); with Glasses_Prescription
      (VisualAid) worn it is back to 6.0 x (1 + Aiming/30); after the removal back to that value.
  X47 (#2599, #2096): the written 0.3 is gone at the first sample after the write in both arms (the
      client copies the network AI's speed into WalkSpeed on every calculateWalkSpeed call); a value that
      holds ~2 s then reverts, or holds 4 s, falsifies the per-call copy.
  X87 (#3028, #3032): the client's push falls and lands; FALLDOWN fires on the server (the falling-state
      exit packet's DoLand) and, if updateFalling's DoLand also runs client-side, on the client too;
      counts per side per fall are the reading; a direct client DoLand(2.0) fires FALLDOWN on the client
      only (no packet path); a fracture is a roll (hard fall 1.5-2.5), so any leg fractureTime is
      recorded, not predicted.
  X86 (#2326, #3026, #3031, jar updateAimingDelay L11242-L11252): each shot raises the delay by
      getRecoilDelay(p) x 0.25 + aimingTime x 0.05 = 12 x 0.25 + 25 x 0.05 = 4.25 at Aiming 0 and
      Strength 5 (one-handed with an empty off hand), clamped to [0, 25]; between shots it falls
      0.625 x mult x (1 + 0.05 x Aiming) per client update; OnWeaponSwing fires on the client after
      the post-shot write (its delay reading carries the sum); a standing bump of 6.25 applied after
      DoAttack returns is inside the sum at OnWeaponSwing and decays away before the next shot 1.2 s
      later; W3's bump decays at the same per-update slope.
  X83 (#2723, #2947): (a) the mod's FATIGUE on a sleep-off server reads ~1e-4 on both sides (the
      kernel reads the reset value); (b) the handler-path 0.42 is the last write before the push: the
      server's per-tick samples and the client's copies read 0.42; falsifier a client copy at ~1e-4
      while the hold stands; (c) an OnTick 0.42 is erased by the next update's reset before the push:
      the client reads ~1e-4 (the sampler may read 0.42 on the tick it was written).

DEVIATIONS FROM THE AMENDMENTS (decided before the run):
  1. X82's handler-path write and X83's sentinel need a writer the probe lacked; it was built in c9b76d0
     as a wrap of NutritionRevamp.kernel.fast.step (no mod/ edit), so the write sits inside the
     takeover handler, after its own kernel step and before its FATIGUE set.
  2. X85 reads getMaxSightRange(p) through the new client sight.range (witness.chain cannot pass the
     player); the glasses are Base.Glasses_Prescription (VisualAid = true, clothing.txt), worn
     client-side only.
  3. X4b's different-list sync is a client-copy removal and SyncXp in one client tick (trait.local
     ... sync), because the 1 Hz experience push would restore a slower edit; the band edges use the
     probe's same-tick set-and-apply, because the mod re-asserts its own weight every game minute.
  4. X84 runs at whatever hour the fixture holds: the ambient floor is C-only (#3027) and the trait
     list's arrival does not depend on the hour.
  5. X86's bump is 6.25 (the design's (k - 1) x aimingTime at k = 1.25, 25 x 0.25), not 0.5, so it
     stands out against the 4.25 post-shot sum; X86 runs last because the spawned zombie attacks.
  6. The mod is not touched: HEAD's handler runs underneath every arm.

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

PROFILES = ("x16-seats", "x16-seats-sleepoff")
SESSION = ("Plan 5 gate 2, the perception, trait and ownership seats live: INTOXICATION ownership (X82), "
           "night vision (X84), the X4 residual (X4b), Short Sighted sight (X85), the speed write (X47), the "
           "landing (X87), the aiming delay (X86) on x16-seats; fatigue ownership on a sleep-off server (X83) "
           "on x16-seats-sleepoff; two serial boots at DayLength 1")
ARTIFACT = "seats.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
DRY_RUN = os.environ.get("PZT_TEMPLATE_DRY_RUN") == "1"

SW = "TKX_StatWatch"
SW_FIELDS = ("fatigue", "intoxication", "endurance", "stress", "panic", "unhappiness", "temperature", "core")
SW_TAGS = ("POISON", "SICK", "FALLDOWN", "BLEEDING", "HUNGRY", "THIRST", "HEAVYLOAD", "other")
SW_DONE_WAIT = 12.0
HOLD_KEYS = ["holdStatus", "holdCalls", "holdWrapped", "holdMissing", "holdModeUsed"]
BAND_KEYS = ["band_req", "band_weight", "band_traits", "band_wall", "band_status"]
BEER = "Base.BeerCan"
GLASSES = "Base.Glasses_Prescription"
X82A_S, X82B_S, X82B_FALLBACK_S, X82C_S, X82C_HOLD_S = 30, 40, 25.0, 22, 16
X82_INTOX, X82_HOLD = 40, 25
BANDS = (49.9, 50.1, 64.9, 65.1)
AIM_W, AIM_W3, AIM_BUMP = 10, 6, 6.25
EVENTS = ("OnWeaponSwing", "OnPlayerAttackFinished", "OnWeaponSwingHitPoint")
FALL_Z, LAND_F = 2, 2.0
X83_S, X83_HOLD_S, X83_F = 25, 20, 0.42
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6
TICK_S = 10
DOCTOR_WAIT_S = 180
HEALTH_GUARD = 40.0

LUAERR_RX = re.compile(r"tried to call nil|stack traceback|attempted to index|LuaError|"
                       r"Exception thrown|non-table|Stack overflow|STACK TRACE|NutritionRevamp.*(fail|error)")
LUAERR_LIMIT = 40
INI_RX = re.compile(r"^(SleepAllowed|SleepNeeded)=(.*)$")
MOD_ERR_RX = re.compile(r"NutritionRevamp|NR_[A-Z][A-Za-z_]*\.lua|nutrients: .* failed")


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
    out["notes"].append({"wall": wall(), "boot": cur["tag"], "note": msg})


def persist():
    if path is None:
        return
    try:
        out["timeline"] = list(tl.items)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def S():
    return cur["server"]


def C():
    return cur["client"]


def B():
    return out[cur["tag"]]


def step(name, side, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    val = ask(side, cmd, args, timeout=timeout)
    t_after = wall()
    row = {"boot": cur["tag"], "step": name, "cmd": cmd, "args": args,
           "side": "server" if side is S() else "client",
           "wall_before": t_before, "wall_after": t_after, "epoch_before": round(e_before, 3),
           "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
           "took": round(t_after - t_before, 3), "ack": val}
    if not isinstance(val, dict):
        row["ack_shape"] = type(val).__name__
    out["steps"].append(row)
    tl.mark("step", name=name, cmd=cmd, took=row["took"])
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def gv(side, name, tag):
    a = ack(step(tag, side, "lua.global", name))
    if not a.get("resolved"):
        return None
    v = a.get("value")
    n = to_num(v)
    return n if n is not None else v


# ---------------------------------------------------------------- reads and writes
def sall(tag, side):
    r = step(tag, side, "stats.all", USER if side is S() else "")
    a = ack(r)
    st = a.get("stats") if isinstance(a.get("stats"), dict) else {}
    row = {"boot": cur["tag"], "tag": tag, "side": "server" if side is S() else "client", "wall": r["wall_before"],
           "wall_after": r["wall_after"], "sideWall": a.get("wall"), "worldAge": a.get("worldAge"),
           "mult": a.get("mult"), "stats": st}
    if not st:
        row["reply"] = r["ack"]
    out["stats_all"].append(row)
    return row


def sget(tag, side):
    r = step(tag, side, "stats.get", USER if side is S() else "")
    a = ack(r)
    row = {"boot": cur["tag"], "tag": tag, "side": "server" if side is S() else "client", "wall": r["wall_before"],
           "wall_after": r["wall_after"], "sideWall": a.get("wall"), "worldAge": a.get("worldAge"),
           "mult": a.get("mult"), "traitList": a.get("traitList"), "traits": a.get("traits"),
           "weight": a.get("weight"), "hunger": a.get("hunger"), "fatigue": a.get("fatigue"),
           "moving": a.get("moving"), "asleep": a.get("asleep")}
    if not a:
        row["reply"] = r["ack"]
    out["stats_get"].append(row)
    return row


def has(row, name):
    tl_ = row.get("traitList")
    if isinstance(tl_, list):
        return name in [str(x).lower() for x in tl_]
    if isinstance(tl_, dict):
        return name in [str(x).lower() for x in tl_.values()]
    return None


def hget(tag, side):
    r = step(tag, side, "health.get", USER)
    a = ack(r)
    row = {"boot": cur["tag"], "tag": tag, "side": "server" if side is S() else "client", "wall": r["wall_before"],
           "overall": a.get("overall"), "health": a.get("health"), "parts": a.get("parts"), "ok": a.get("ok")}
    out["health_reads"].append(row)
    return row


def setany(tag, stat, v):
    r = step(tag, S(), "stats.setany", f"{USER} {stat} {v}")
    a = ack(r)
    row = {"boot": cur["tag"], "tag": tag, "wall": r["wall_before"], "wall_after": r["wall_after"], "stat": stat,
           "ok": a.get("ok"), "requested": a.get("requested"), "before": a.get("before"), "after": a.get("after"),
           "reason": a.get("reason")}
    out["stat_writes"].append(row)
    return row


def chain(tag, side, hop):
    args = f"{USER} {hop}" if side is S() else hop
    r = step(tag, side, "witness.chain", args)
    a = ack(r)
    return {"tag": tag, "wall": r["wall_before"], "ok": a.get("ok"), "value": a.get("value"),
            "failedAt": a.get("failedAt"), "error": a.get("error"), "reason": a.get("reason")}


def gset(tag, key, value):
    return ack(step(tag, S(), "globalmoddata.set", f"{SW} {key} {value}"))


def md_read(tag, keys):
    vals, missing = {}, []
    chunks = [keys[i:i + 30] for i in range(0, len(keys), 30)] or [[]]
    for j, ch in enumerate(chunks):
        a = ack(step(f"{tag}_{j}", S(), "witness.moddata", f"global:{SW} " + " ".join(ch)))
        if isinstance(a.get("values"), dict):
            vals.update(a["values"])
        if isinstance(a.get("missing"), list):
            missing.extend(a["missing"])
    return {"values": vals, "missing": missing, "wall": wall()}


def sw_status(tag):
    return ack(step(tag, S(), "witness.moddata", f"global:{SW} status samples windowMs arm")).get("values") or {}


def sw_reset_tags(tag, tags):
    for t in tags:
        gset(f"{tag}_rd_{t}", f"dmg_{t}", -1)
        gset(f"{tag}_rs_{t}", f"dmgsum_{t}", -1)
    return {"reset": list(tags), "to": -1, "wall": wall()}


def sw_arm(tag, seconds):
    res = {"seconds": seconds}
    r = step(f"{tag}_arm", S(), "globalmoddata.set", f"{SW} arm {seconds}")
    res["arm_wall"] = r["wall_after"]
    res["armed_seen_wall"] = None
    end = wall() + 8.0
    while wall() < end:
        if sw_status(f"{tag}_armchk").get("status") == "armed":
            res["armed_seen_wall"] = wall()
            break
        time.sleep(0.25)
    return res


def parse_raw(s):
    d = {}
    for part in str(s).split(" "):
        if "=" in part:
            k, v = part.split("=", 1)
            n = to_num(v)
            d[k] = n if n is not None else v
    return d


def sw_collect(tag, arm):
    end = (arm.get("armed_seen_wall") or arm["arm_wall"]) + arm["seconds"] + SW_DONE_WAIT
    done = None
    while wall() < end:
        s = sw_status(f"{tag}_donechk")
        if s.get("status") == "done":
            done = s
            break
        time.sleep(1.0)
    keys = ["samples", "windowMs", "status"]
    for f in SW_FIELDS:
        keys += [f"first_{f}", f"last_{f}", f"min_{f}", f"max_{f}", f"n_{f}", f"absent_{f}"]
    keys += [f"dmg_{t}" for t in SW_TAGS] + [f"dmgsum_{t}" for t in SW_TAGS]
    sc = md_read(f"{tag}_scal", keys)
    raws = md_read(f"{tag}_raw", [f"raw_{i}" for i in range(1, 61)])
    g = sc["values"]
    raw_s = [raws["values"][f"raw_{i}"] for i in range(1, 61) if raws["values"].get(f"raw_{i}") is not None]
    flds = {f: {"first": to_num(g.get(f"first_{f}")), "last": to_num(g.get(f"last_{f}")),
                "min": to_num(g.get(f"min_{f}")), "max": to_num(g.get(f"max_{f}")),
                "n": to_num(g.get(f"n_{f}")), "absent": g.get(f"absent_{f}")} for f in SW_FIELDS}
    dmg = {t: {"count": to_num(g.get(f"dmg_{t}")), "sum": to_num(g.get(f"dmgsum_{t}"))} for t in SW_TAGS}
    res = {"done": done, "status": g.get("status"), "samples": to_num(g.get("samples")),
           "windowMs": to_num(g.get("windowMs")), "fields": flds, "dmg": dmg, "raw_strings": raw_s,
           "raw": [parse_raw(v) for v in raw_s], "collected_wall": wall()}
    out["watches"].append({"boot": cur["tag"], "tag": tag, "arm": arm, "result": res})
    return res


def hold_arm(tag, mode, seconds, fatigue=-1, intox=-1):
    res = {"mode": mode, "seconds": seconds, "fatigue": fatigue, "intox": intox}
    gset(f"{tag}_hs", "holdStatus", "pending")
    gset(f"{tag}_hc", "holdCalls", -1)
    gset(f"{tag}_hm", "holdMode", mode)
    gset(f"{tag}_hf", "holdFatigue", fatigue)
    gset(f"{tag}_hi", "holdIntox", intox)
    r = step(f"{tag}_hold", S(), "globalmoddata.set", f"{SW} hold {seconds}")
    res["arm_wall"] = r["wall_after"]
    res["armed_seen_wall"] = None
    end = wall() + 6.0
    while wall() < end:
        v = md_read(f"{tag}_hchk", ["holdStatus"])["values"]
        if v.get("holdStatus") in ("armed", "failed"):
            res["armed_seen_wall"] = wall()
            res["status_at_arm"] = v.get("holdStatus")
            break
        time.sleep(0.25)
    return res


def hold_read(tag):
    return md_read(tag, HOLD_KEYS)["values"]


def pairs(key, until, every=1.5):
    rows = []
    i = 0
    while wall() < until:
        t_start = wall()
        c = sall(f"{key}_c{i}", C())
        s = sall(f"{key}_s{i}", S())
        rows.append({"i": i, "c": c["tag"], "s": s["tag"]})
        i += 1
        rest = every - (wall() - t_start)
        if rest > 0:
            time.sleep(rest)
    return rows


def wait_res(name, after, timeout):
    try:
        return C().bus.wait_result(name, timeout=timeout, after=after)
    except Exception as e:                     # noqa: BLE001 - recorded, not raised
        return {"error": f"{type(e).__name__}: {e}"}


def tick_rate(label):
    after = time.time()
    arm = ack(step(f"{label}_tick_arm", S(), "tick.rate", str(TICK_S)))
    res = None
    if arm.get("armed"):
        try:
            res = S().bus.wait_result(arm.get("result") or "tick-rate", timeout=TICK_S + 20, after=after)
        except (RuntimeError, TimeoutError, OSError) as e:
            res = {"error": f"{type(e).__name__}: {e}"}
    return {"arm": arm, "result": res}


def read_ini(server):
    vals = {"path": None, "values": {}, "error": None}
    try:
        vals["path"] = os.path.relpath(server.ini, REPO)
        with open(server.ini, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = INI_RX.match(line.strip())
                if m:
                    vals["values"][m.group(1)] = m.group(2)
    except Exception as e:                     # noqa: BLE001
        vals["error"] = f"{type(e).__name__}: {e}"
    return vals


def spawn(full_type, why):
    ok, reply = S().rcon(f'additem "{USER}" "{full_type}" 1')
    row = {"type": full_type, "why": why, "rcon_ok": ok, "rcon_reply": str(reply)[:200], "wall_rcon": wall(),
           "attempts": []}
    for attempt in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        seen = ack(step(f"spawn_{why}_{attempt}", C(), "witness.fields", f"item {USER}/{full_type} getID"))
        row["attempts"].append({"attempt": attempt + 1, "wall": wall(), "resolved": seen.get("resolved"),
                                "id": (seen.get("fields") or {}).get("getID")})
        if seen.get("resolved"):
            break
    row["resolved"] = bool(row["attempts"] and row["attempts"][-1]["resolved"])
    return row


def litres_srv(tag, full_type):
    c = chain(tag, S(), f"getInventory.getFirstTypeRecurse({full_type}).getFluidContainer.getAmount")
    return to_num(c.get("value"))


def run_phase(name, fn):
    try:
        fn()
    except Exception as e:                     # noqa: BLE001 - one phase's fault keeps the others
        B()["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    persist()


def mod_error(after):
    why = []
    srv = S()
    errs = [str(e) for e in (srv.errors if srv is not None else [])]
    hits = [e[:400] for e in errs if MOD_ERR_RX.search(e)]
    if hits:
        why.append({"server_error_lines": hits[:10]})
    le = gv(srv, "NutritionRevamp.server.nutrients.lastError", f"chk_{after}_nle")
    ne = gv(srv, "NutritionRevamp.server.nutrients.stats.errors", f"chk_{after}_nerr")
    fe = gv(srv, "NutritionRevamp.server.fast.stats.failures", f"chk_{after}_ffail")
    if le is not None or (to_num(ne) or 0) > 0 or (to_num(fe) or 0) > 0:
        why.append({"nutrients_lastError": le, "nutrients_errors": ne, "fast_failures": fe})
    if cur["clients"] and "lua_error" in getattr(cur["clients"][0], "seen", ()):
        why.append({"client": "lua_error seen (parked in the debugger)"})
    h = hget(f"chk_{after}_h", srv)
    o = to_num(h.get("overall"))
    if o is not None and o < HEALTH_GUARD:
        why.append({"health_guard": o})
    B()["mod_error_checks"].append({"after": after, "wall": wall(), "found": why, "health": o})
    return why


# ---------------------------------------------------------------- phases
def phase_S0():
    P = B()["phases"]["S0"] = {}
    P["stats_server"] = sall("S0_sall_s", S())["tag"]
    P["stats_client"] = sall("S0_sall_c", C())["tag"]
    P["get_server"] = sget("S0_sget_s", S())
    P["get_client"] = sget("S0_sget_c", C())
    P["time_server"] = ack(step("S0_time_s", S(), "time.snapshot"))
    P["time_client"] = ack(step("S0_time_c", C(), "time.snapshot"))
    P["intox_reduction"] = ack(step("S0_intox_red", S(), "intox.reduction", USER))
    P["aiming_client"] = chain("S0_aim_c", C(), "getPerkLevel(Perks.Aiming)")
    P["strength_client"] = chain("S0_str_c", C(), "getPerkLevel(Perks.Strength)")
    P["health_server"] = hget("S0_h_s", S())["tag"]
    P["health_client"] = hget("S0_h_c", C())["tag"]
    P["mod_version"] = {"server": gv(S(), "NutritionRevamp.version", "S0_ver_s"),
                        "client": gv(C(), "NutritionRevamp.version", "S0_ver_c")}
    P["weight_stats"] = {k: gv(S(), f"NutritionRevamp.server.weight.stats.{k}", f"S0_ws_{k}")
                         for k in ("minutes", "weightWrites", "bandChanges", "bandRepairs", "pushes")}
    P["fast_stats"] = {k: gv(S(), f"NutritionRevamp.server.fast.stats.{k}", f"S0_fs_{k}")
                       for k in ("calls", "failures")}
    if cur["tag"] == "boot1":
        P["beer_script"] = ack(step("S0_beer", S(), "fluid.script", "Beer"))
        P["tick"] = tick_rate("S0")


def phase_X82():
    X = B()["phases"]["X82"] = {}
    red0 = to_num(B()["phases"]["S0"].get("intox_reduction", {}).get("after"))
    if red0 is None:
        red0 = to_num(B()["phases"]["S0"].get("intox_reduction", {}).get("before"))
    X["reduction_default"] = red0
    # (a) the reduction at 0, a written 40
    X["a_set_red"] = ack(step("X82a_red0", S(), "intox.reduction", f"{USER} 0"))
    X["a_arm"] = sw_arm("X82a", X82A_S)
    X["a_write"] = setany("X82a_w40", "INTOXICATION", X82_INTOX)
    X["a_pairs"] = pairs("X82a", X["a_arm"]["arm_wall"] + X82A_S - 1.0, 3.0)
    X["a_watch"] = sw_collect("X82a", X["a_arm"])
    X["a_red_after"] = ack(step("X82a_red_rd", S(), "intox.reduction", USER))
    persist()
    # (b) a beer at reduction 0
    X["b_spawn"] = spawn(BEER, "X82b")
    X["b_stats_before"] = sall("X82b_before_s", S())["tag"]
    X["b_get_before"] = sget("X82b_get_before", S())
    X["b_litres_before"] = litres_srv("X82b_l_before", BEER)
    X["b_arm"] = sw_arm("X82b", X82B_S)
    X["b_drink_wall"] = wall()
    X["b_drink"] = ack(step("X82b_drink", C(), "drink.action", f"{BEER} 1"))
    X["b_fallback"] = None
    X["b_polls"] = []
    fell = False
    i = 0
    end = X["b_arm"]["arm_wall"] + X82B_S - 1.0
    while wall() < end:
        t_start = wall()
        s = sall(f"X82b_p{i}", S())
        lv = litres_srv(f"X82b_l{i}", BEER)
        if lv is not None and X["b_litres_before"] is not None and lv < X["b_litres_before"] - 1e-6:
            fell = True
        if X["b_fallback"] is None and not fell and wall() > X["b_drink_wall"] + X82B_FALLBACK_S:
            X["b_fallback"] = {"wall": wall(), "ack": ack(step("X82b_fallback", S(), "drink", f"{USER} {BEER} 1"))}
        X["b_polls"].append({"i": i, "s": s["tag"], "litres": lv})
        i += 1
        rest = 1.0 - (wall() - t_start)
        if rest > 0:
            time.sleep(rest)
    X["b_watch"] = sw_collect("X82b", X["b_arm"])
    X["b_client_after"] = sall("X82b_after_c", C())["tag"]
    persist()
    # (c) the reduction restored, a handler-path hold of 25
    X["c_set_red"] = ack(step("X82c_red_def", S(), "intox.reduction", f"{USER} {red0 if red0 is not None else 0.0042}"))
    X["c_zero"] = setany("X82c_w0", "INTOXICATION", 0)
    X["c_arm"] = sw_arm("X82c", X82C_S)
    X["c_hold"] = hold_arm("X82c", "handler", X82C_HOLD_S, -1, X82_HOLD)
    X["c_pairs"] = pairs("X82c", X["c_hold"]["arm_wall"] + X82C_HOLD_S - 0.5, 1.5)
    X["c_after_pairs"] = pairs("X82c_after", wall() + 3.0, 1.5)
    X["c_watch"] = sw_collect("X82c", X["c_arm"])
    X["c_hold_read"] = hold_read("X82c_hread")
    X["c_red_after"] = ack(step("X82c_red_rd", S(), "intox.reduction", USER))
    X["d_zero"] = setany("X82d_w0", "INTOXICATION", 0)


def phase_X84():
    X = B()["phases"]["X84"] = {}
    X["time_client"] = ack(step("X84_time_c", C(), "time.snapshot"))
    X["pre_client"] = sget("X84_pre_c", C())
    t_arm = time.time()
    X["watch"] = ack(step("X84_watch", C(), "trait.watch", "nightvision 8"))
    s = step("X84_addpush", S(), "trait.add.push", f"{USER} NIGHT_VISION")
    X["addpush"] = ack(s)
    X["result"] = wait_res("trait-watch", t_arm - 0.5, 12)
    seen = to_num(X["result"].get("firstSeenWall")) if X["result"].get("found") else None
    wa = to_num(X["addpush"].get("wallAfter"))
    X["latency_ms"] = (seen - wa) if (seen is not None and wa is not None) else None
    X["after_client"] = sget("X84_after_c", C())
    X["after_server"] = sget("X84_after_s", S())
    X["has"] = {"client": has(X["after_client"], "nightvision"), "server": has(X["after_server"], "nightvision")}


def phase_X4b():
    X = B()["phases"]["X4b"] = {}
    # control: a client-only removal, no sync
    X["ctl_pre_c"] = sget("X4b_ctl_pre_c", C())
    X["ctl_local"] = ack(step("X4b_ctl_local", C(), "trait.local", "NIGHT_VISION remove"))
    X["ctl_polls"] = []
    end = wall() + 4.0
    i = 0
    while wall() < end:
        c = sget(f"X4b_ctl_p{i}_c", C())
        X["ctl_polls"].append({"i": i, "wall": c["wall"], "sideWall": c["sideWall"], "has": has(c, "nightvision")})
        i += 1
    X["ctl_server"] = sget("X4b_ctl_s", S())
    X["ctl_server_has"] = has(X["ctl_server"], "nightvision")
    # sync: a client-only removal and SyncXp in one client tick
    pre = sget("X4b_syn_pre_c", C())
    X["syn_pre_client_has"] = has(pre, "nightvision")
    if not X["syn_pre_client_has"]:
        X["syn_repush"] = ack(step("X4b_syn_repush", S(), "trait.push", USER))
        time.sleep(1.0)
        X["syn_pre_client_has2"] = has(sget("X4b_syn_pre_c2", C()), "nightvision")
    X["syn_pre_server_has"] = has(sget("X4b_syn_pre_s", S()), "nightvision")
    r = step("X4b_syn_local", C(), "trait.local", "NIGHT_VISION remove sync")
    X["syn_local"] = ack(r)
    X["syn_local_wall"] = r["wall_after"]
    X["syn_polls"] = []
    end = wall() + 5.0
    i = 0
    while wall() < end:
        s = sget(f"X4b_syn_p{i}_s", S())
        X["syn_polls"].append({"i": i, "wall": s["wall"], "sideWall": s["sideWall"], "has": has(s, "nightvision"),
                               "traitList": s.get("traitList")})
        i += 1
    X["syn_after_client"] = sget("X4b_syn_after_c", C())
    X["syn_after_client_has"] = has(X["syn_after_client"], "nightvision")
    X["cleanup_remove"] = ack(step("X4b_clean_rm", S(), "trait.set", f"{USER} NIGHT_VISION remove"))
    X["cleanup_push"] = ack(step("X4b_clean_push", S(), "trait.push", USER))
    persist()
    # bands: a same-tick weight set and band apply
    X["bands"] = []
    X["ws_before"] = {k: gv(S(), f"NutritionRevamp.server.weight.stats.{k}", f"X4b_wsb_{k}")
                      for k in ("bandChanges", "bandRepairs", "pushes", "weightWrites")}
    for w in BANDS:
        tag = "X4b_band_" + str(w).replace(".", "_")
        gset(f"{tag}_rs", "band_status", "pending")
        gset(f"{tag}_rt", "band_traits", "none")
        r = step(f"{tag}_set", S(), "globalmoddata.set", f"{SW} bandW {w}")
        row = {"w": w, "set_wall": r["wall_after"], "reads": []}
        end = wall() + 6.0
        while wall() < end:
            v = md_read(f"{tag}_rd", BAND_KEYS)["values"]
            row["reads"].append(v)
            if v.get("band_status") == "done":
                break
            time.sleep(0.3)
        row["band"] = row["reads"][-1] if row["reads"] else {}
        row["server_after"] = sget(f"{tag}_s", S())
        time.sleep(1.5)
        row["client_after"] = sget(f"{tag}_c", C())
        X["bands"].append(row)
        persist()
    X["ws_after"] = {k: gv(S(), f"NutritionRevamp.server.weight.stats.{k}", f"X4b_wsa_{k}")
                     for k in ("bandChanges", "bandRepairs", "pushes", "weightWrites")}
    time.sleep(2.0)
    X["final_server"] = sget("X4b_final_s", S())
    X["final_client"] = sget("X4b_final_c", C())


def phase_X85():
    X = B()["phases"]["X85"] = {}
    X["base"] = ack(step("X85_base", C(), "sight.range"))
    t_arm = time.time()
    X["watch"] = ack(step("X85_watch", C(), "trait.watch", "shortsighted 8"))
    X["addpush"] = ack(step("X85_addpush", S(), "trait.add.push", f"{USER} SHORT_SIGHTED"))
    X["result"] = wait_res("trait-watch", t_arm - 0.5, 12)
    X["trait"] = ack(step("X85_trait", C(), "sight.range"))
    X["glasses"] = ack(step("X85_glasses", C(), "sight.range", f"wear {GLASSES}"))
    X["unworn"] = ack(step("X85_unworn", C(), "sight.range", "unwear"))
    X["remove"] = ack(step("X85_remove", S(), "trait.set", f"{USER} SHORT_SIGHTED remove"))
    X["push"] = ack(step("X85_push", S(), "trait.push", USER))
    time.sleep(1.5)
    X["after"] = ack(step("X85_after", C(), "sight.range"))
    X["after_client"] = sget("X85_after_c", C())


def phase_X47():
    X = B()["phases"]["X47"] = {}
    X["stop0"] = ack(step("X47_stop0", C(), "player.stop"))
    t_arm = time.time()
    X["stand_arm"] = ack(step("X47_stand", C(), "anim.probe", "WalkSpeed 0.3 250 16"))
    X["stand"] = wait_res("anim-probe", t_arm - 0.5, 15)
    X["walk"] = ack(step("X47_walk", C(), "player.walk", "20 0"))
    time.sleep(0.5)
    t_arm = time.time()
    X["walk_arm"] = ack(step("X47_walk_arm", C(), "anim.probe", "WalkSpeed 0.3 250 16"))
    X["walking"] = wait_res("anim-probe", t_arm - 0.5, 15)
    X["moving_server"] = sget("X47_mv_s", S())
    X["stop"] = ack(step("X47_stop", C(), "player.stop"))


def fall_arm(X, key, args):
    X[f"{key}_h_s_pre"] = hget(f"X87_{key}_hs0", S())["tag"]
    X[f"{key}_h_c_pre"] = hget(f"X87_{key}_hc0", C())["tag"]
    X[f"{key}_srv_listen"] = ack(step(f"X87_{key}_srv0", S(), "fall.probe", USER))
    t_arm = time.time()
    r = step(f"X87_{key}_cli", C(), "fall.probe", f"{USER} {args}")
    X[f"{key}_cli"] = ack(r)
    X[f"{key}_cli_wall"] = r["wall_after"]
    X[f"{key}_result"] = wait_res("fall-probe", t_arm - 0.5, 14)
    X[f"{key}_srv_after"] = ack(step(f"X87_{key}_srv1", S(), "fall.probe", USER))
    X[f"{key}_h_s_post"] = hget(f"X87_{key}_hs1", S())["tag"]
    X[f"{key}_h_c_post"] = hget(f"X87_{key}_hc1", C())["tag"]


def phase_X87():
    X = B()["phases"]["X87"] = {}
    X["reset"] = sw_reset_tags("X87", ("FALLDOWN",))
    X["arm"] = sw_arm("X87", 40)
    fall_arm(X, "push", f"{FALL_Z}")
    fall_arm(X, "land", f"0 land {LAND_F}")
    X["watch"] = sw_collect("X87", X["arm"])
    nparts = len((out["health_reads"][-1].get("parts") or [])) or 17
    X["restore"] = []
    for i in range(nparts):
        X["restore"].append(ack(step(f"X87_h100_{i}", S(), "bodypart.set", f"{USER} {i} health 100")))
        X["restore"].append(ack(step(f"X87_fr0_{i}", S(), "bodypart.set", f"{USER} {i} fractureTime 0 sync")))
    X["h_after_restore"] = hget("X87_h_restored", S())["tag"]


def aim_window(X, key, seconds, bump=None, shots=0, bump_now_after=None):
    t_arm = time.time()
    X[f"{key}_arm"] = ack(step(f"X86_{key}_arm", C(), "aim.probe", f"{USER} {seconds}"))
    if bump is not None:
        X[f"{key}_bump"] = ack(step(f"X86_{key}_bump", C(), "aim.bump", f"{bump}"))
    if shots:
        X[f"{key}_fire"] = ack(step(f"X86_{key}_fire", C(), "aim.fire", f"{shots}"))
    if bump_now_after is not None:
        time.sleep(bump_now_after)
        X[f"{key}_bump_now"] = ack(step(f"X86_{key}_bumpnow", C(), "aim.bump", f"{AIM_BUMP} now"))
    X[f"{key}_result"] = wait_res("aim-probe", t_arm + 0.5, seconds + 15)
    if bump is not None:
        X[f"{key}_unbump"] = ack(step(f"X86_{key}_unbump", C(), "aim.bump", "0"))


def phase_X86():
    X = B()["phases"]["X86"] = {}
    X["events_install"] = {e: ack(step(f"X86_ev_{e}", C(), "event.watch", e)) for e in EVENTS}
    X["zombie"] = ack(step("X86_zombie", S(), "zombie.near", "1"))
    X["aiming"] = chain("X86_aim_lvl", C(), "getPerkLevel(Perks.Aiming)")
    X["strength"] = chain("X86_str_lvl", C(), "getPerkLevel(Perks.Strength)")
    aim_window(X, "W1", AIM_W, shots=3)
    X["weapon_aimingTime"] = chain("X86_aimtime", C(), "getPrimaryHandItem.getAimingTime")
    X["weapon_recoilDelay"] = chain("X86_recoil", C(), "getPrimaryHandItem.getRecoilDelay")
    X["weapon_secondary"] = chain("X86_second", C(), "getSecondaryHandItem.getFullType")
    X["events_W1"] = {e: ack(step(f"X86_evW1_{e}", C(), "event.watch", e)) for e in EVENTS}
    persist()
    aim_window(X, "W2", AIM_W, bump=AIM_BUMP, shots=3)
    X["events_W2"] = {e: ack(step(f"X86_evW2_{e}", C(), "event.watch", e)) for e in EVENTS}
    persist()
    aim_window(X, "W3", AIM_W3, bump_now_after=2.0)
    X["events_W3"] = {e: ack(step(f"X86_evW3_{e}", C(), "event.watch", e)) for e in EVENTS}
    X["health_after"] = hget("X86_h_s", S())["tag"]


def phase_X83():
    X = B()["phases"]["X83"] = {}
    X["a_arm"] = sw_arm("X83a", 20)
    X["a_pairs"] = pairs("X83a", X["a_arm"]["arm_wall"] + 19.0, 1.5)
    X["a_watch"] = sw_collect("X83a", X["a_arm"])
    persist()
    X["b_arm"] = sw_arm("X83b", X83_S)
    X["b_hold"] = hold_arm("X83b", "handler", X83_HOLD_S, X83_F, -1)
    X["b_pairs"] = pairs("X83b", X["b_hold"]["arm_wall"] + X83_HOLD_S - 0.5, 1.5)
    X["b_watch"] = sw_collect("X83b", X["b_arm"])
    X["b_hold_read"] = hold_read("X83b_hread")
    persist()
    X["c_arm"] = sw_arm("X83c", X83_S)
    X["c_hold"] = hold_arm("X83c", "tick", X83_HOLD_S, X83_F, -1)
    X["c_pairs"] = pairs("X83c", X["c_hold"]["arm_wall"] + X83_HOLD_S - 0.5, 1.5)
    X["c_watch"] = sw_collect("X83c", X["c_arm"])
    X["c_hold_read"] = hold_read("X83c_hread")
    X["d_pairs"] = pairs("X83d", wall() + 10.0, 1.5)


def phase_Z():
    Z = B()["phases"]["Z"] = {}
    Z["nutrients_stats"] = {k: gv(S(), f"NutritionRevamp.server.nutrients.stats.{k}", f"Z_ns_{k}")
                            for k in ("minutes", "errors", "players")}
    Z["lastError"] = gv(S(), "NutritionRevamp.server.nutrients.lastError", "Z_lastError")
    Z["fast_stats"] = {k: gv(S(), f"NutritionRevamp.server.fast.stats.{k}", f"Z_fs_{k}")
                       for k in ("calls", "failures")}
    Z["fast_lastError"] = gv(S(), "NutritionRevamp.server.fast.lastError", "Z_fast_lastError")
    Z["weight_stats"] = {k: gv(S(), f"NutritionRevamp.server.weight.stats.{k}", f"Z_ws_{k}")
                         for k in ("minutes", "weightWrites", "bandChanges", "bandRepairs", "pushes")}
    Z["health_s"] = hget("Z_h_s", S())["tag"]
    Z["stats_s"] = sall("Z_s", S())["tag"]
    Z["stats_c"] = sall("Z_c", C())["tag"]
    Z["intox_reduction"] = ack(step("Z_intox_red", S(), "intox.reduction", USER))


def body1():
    for name, fn in (("S0", phase_S0), ("X82", phase_X82), ("X84", phase_X84), ("X4b", phase_X4b),
                     ("X85", phase_X85), ("X47", phase_X47), ("X87", phase_X87), ("X86", phase_X86),
                     ("Z", phase_Z)):
        run_phase(name, fn)
        why = mod_error(name)
        if why and name != "Z":
            B()["abort"] = {"after": name, "why": why}
            note(f"mod error or health guard after {name}: the arms stop here")
            persist()
            break


def body2():
    for name, fn in (("S0", phase_S0), ("X83", phase_X83), ("Z", phase_Z)):
        run_phase(name, fn)
        why = mod_error(name)
        if why and name != "Z":
            B()["abort"] = {"after": name, "why": why}
            note(f"mod error after {name}: the arms stop here")
            persist()
            break


def wait_doctor(Bk):
    rows = []
    end = time.time() + DOCTOR_WAIT_S
    clean = False
    while time.time() < end:
        ok, text = doctor()
        rows.append({"wall": wall(), "clean": ok, "text": text.strip().splitlines()[-6:]})
        if ok:
            clean = True
            break
        time.sleep(5.0)
    Bk["doctor_after"] = rows
    return clean


def run_boot(tag, prof, run_dir_b, body_fn):
    Bk = out[tag] = {"profile": prof.report(), "mods": list(prof.mods), "ini_requested": dict(prof.ini or {}),
                     "run_dir": os.path.relpath(run_dir_b, REPO), "phases": {}, "phase_errors": {},
                     "mod_error_checks": []}
    cur.update({"tag": tag, "server": None, "client": None, "clients": []})
    server = None
    try:
        server = make_server(run_dir_b, rec, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini)
        cur["server"] = server
        Bk["ini_seeded"] = read_ini(server)
        server.start(timeout=prof.server_timeout)
        client, _ = make_client(run_dir_b, USER, server, rec)
        cur["client"] = client
        client.start()
        cur["clients"].append(client)
        client.wait_ready(timeout=prof.client_timeout)
        tl.mark("session_ready", boot=tag)
        Bk["session_ready_wall"] = wall()
        Bk["build"] = server.build
        Bk["ini_after_ready"] = read_ini(server)
        Bk["verify"] = verify(prof, server, cur["clients"], tl)
        Bk["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                                "client": sorted(set(client.mods_not_found))}
        persist()
        try:
            body_fn()
        except Exception as e:                 # noqa: BLE001 - keep the rows already collected
            Bk["body_error"], Bk["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
            tl.mark("error", boot=tag, detail=str(e)[:200])
        persist()
    except Exception as e:                     # noqa: BLE001
        Bk["error"], Bk["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", boot=tag, detail=str(e)[:200])
    finally:
        clients = cur["clients"]
        try:
            if server is not None:
                teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            Bk["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            if server is not None:
                hard_kill(server, clients)
            Bk["client_lua_error"] = ("lua_error" in getattr(clients[0], "seen", ())) if clients else None
            if server is not None:
                Bk["server_errors"] = server.errors[:20]
                Bk["server_error_count"] = len(server.errors)
                Bk["ini_after_stop"] = read_ini(server)
                Bk["logs"] = {"server_luaerr": grep_file(server.log_path, LUAERR_RX, LUAERR_LIMIT),
                              "limits": {"luaerr": LUAERR_LIMIT}}
                if clients:
                    Bk["logs"]["client_luaerr"] = grep_file(clients[0].console, LUAERR_RX, LUAERR_LIMIT)
            Bk["wall_end"] = wall()
            persist()
    return Bk


# ---------------- summaries (derived after the run; the grade is taken from the raw) ----------------
def summarise():
    sm = out["summaries"]
    b1, b2 = out.get("boot1") or {}, out.get("boot2") or {}
    sm["ini"] = {b: {"seeded": ((out.get(b) or {}).get("ini_seeded") or {}).get("values"),
                     "ready": ((out.get(b) or {}).get("ini_after_ready") or {}).get("values"),
                     "stop": ((out.get(b) or {}).get("ini_after_stop") or {}).get("values")} for b in ("boot1", "boot2")}
    P1 = b1.get("phases") or {}
    P2 = b2.get("phases") or {}
    x = P1.get("X82") or {}
    sm["X82"] = {k: ((x.get(w) or {}).get("fields") or {}).get("intoxication")
                 for k, w in (("a", "a_watch"), ("b", "b_watch"), ("c", "c_watch"))}
    sm["X82"]["c_hold"] = x.get("c_hold_read")
    sm["X84"] = {k: (P1.get("X84") or {}).get(k) for k in ("latency_ms", "has")}
    sm["X85"] = {k: {kk: ((P1.get("X85") or {}).get(k) or {}).get(kk)
                     for kk in ("maxSightChar", "minSightChar", "shortSighted", "wearingGlasses", "aiming")}
                 for k in ("base", "trait", "glasses", "unworn", "after")}
    x = P1.get("X4b") or {}
    sm["X4b"] = {"ctl_server_has": x.get("ctl_server_has"), "ctl_polls": x.get("ctl_polls"),
                 "syn_polls_has": [p.get("has") for p in (x.get("syn_polls") or [])],
                 "bands": [{"w": r.get("w"), "band": r.get("band")} for r in (x.get("bands") or [])]}
    x = P2.get("X83") or {}
    sm["X83"] = {k: ((x.get(w) or {}).get("fields") or {}).get("fatigue")
                 for k, w in (("a", "a_watch"), ("b", "b_watch"), ("c", "c_watch"))}
    sm["X83"]["holds"] = {"b": x.get("b_hold_read"), "c": x.get("c_hold_read")}


prof1, prof2 = profile.load(PROFILES[0]), profile.load(PROFILES[1])
rec = None if DRY_RUN else fx.load(prof1.fixture)
run_id, run_dir = ("x161p-dry-run", None) if DRY_RUN else new_run_dir("x161p")
path = None if DRY_RUN else os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
cur = {"tag": "pre", "server": None, "client": None, "clients": []}

doctor_clean, doctor_text = (None, "") if DRY_RUN else doctor()
lua_dirty, lua_dirty_note = git_dirty(LUA_DIR)
out = {
    "run_id": run_id,
    "session": SESSION,
    "user": USER,
    "profiles": list(PROFILES),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "mod_commit": git_say("log", "-1", "--format=%h", "--", "mod/NutritionRevamp"),
    "mod_dirty": git_dirty("mod/NutritionRevamp")[0],
    "probe_commits": {m: git_say("log", "-1", "--format=%h", "--", f"testing/experiments/{m}")
                      for m in ("TKX_StatWatch", "TKX_TraitProbe")},
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": lua_dirty,
    "harness_lua_dirty_note": lua_dirty_note,
    "doctor_clean": doctor_clean,
    "doctor": doctor_text.strip().splitlines(),
    "dry_run": DRY_RUN,
    "constants": {k: (list(v) if isinstance(v, tuple) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, tuple))
                  and k not in ("REPO", "LUA_DIR")},
    "deviations": [
        "X82's handler-path INTOXICATION write and X83's FATIGUE sentinel use the TKX_StatWatch hold arm built in "
        "c9b76d0 (a wrap of NutritionRevamp.kernel.fast.step; no mod/ edit).",
        "X85 reads getMaxSightRange(p) through the new client sight.range (cfc8e7f); the glasses are "
        "Base.Glasses_Prescription worn client-side only.",
        "X4b's different-list sync is trait.local NIGHT_VISION remove sync (a client-copy edit and SyncXp in one "
        "client tick); the band edges use the probe's same-tick setWeight + applyTraitFromWeight.",
        "X84 runs at the fixture's hour; the ambient floor is C-only (#3027).",
        "X86's bump is 6.25 (k = 1.25 x aimingTime 25), not 0.5; X86 runs last because of the zombie.",
        "The mod at HEAD runs underneath every arm.",
    ],
    "world_changes": {"restored": "the golden fixture restored into each boot's run dir",
                      "left_in_place": ["a BeerCan, a client-side pistol and glasses", "traits added and removed",
                                        "INTOXICATION and FATIGUE written", "the drunk-reduction value set and restored",
                                        "weight set at the band edges", "a fall and a direct landing, health restored",
                                        "a zombie spawned"]},
    "steps": [], "notes": [], "summaries": {}, "stats_all": [], "stats_get": [], "health_reads": [],
    "stat_writes": [], "watches": [],
}

if DRY_RUN:
    print(json.dumps(out)[:2000])
    sys.exit(0)

if not doctor_clean:
    out["error"] = "doctor not clean; the session was not started (CLAUDE.md s5)"
    print(json.dumps(out["doctor"], indent=1))
    sys.exit(1)

try:
    run_boot("boot1", prof1, run_dir, body1)
    if wait_doctor(out["boot1"]):
        run_boot("boot2", prof2, os.path.join(run_dir, "boot2"), body2)
    else:
        out["boot2"] = {"error": "doctor did not come back clean after boot 1; boot 2 not started (one session at a time)"}
    try:
        summarise()
    except Exception as e:                     # noqa: BLE001
        out["summary_error"] = f"{type(e).__name__}: {e}"
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001 - never raise
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summaries": out.get("summaries"), "error": out.get("error"),
                  "boot1_error": (out.get("boot1") or {}).get("body_error"),
                  "boot2_error": (out.get("boot2") or {}).get("body_error"),
                  "phase_errors": {b: (out.get(b) or {}).get("phase_errors") for b in ("boot1", "boot2")}},
                 indent=1, default=str)[:9000])
