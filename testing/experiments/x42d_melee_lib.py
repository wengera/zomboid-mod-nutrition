"""x42d_melee_lib -- the session engine of the Plan 13 Task 1 melee re-measure (x424_melee.py), after x423-20261015-040740.

x423's melee window swung a Base.BaseballBat that the harness's attack.melee had added client-side (it adds one when the
primary hand is empty): the server logged every PlayerHitZombie packet "not consistent" with "weapon": null, no AddXP
event of any perk fired, and the client's target read dead after 9 swings. x423's pre-registered grade read that dead
target as a hit and graded the window falsified; the server log says no hit reached the server's hit path, so the
melee source was not measured. This lib measures it with a weapon the server owns (the harness's weapon.equip,
c92ffdd7): the server's inventory.add puts the bat in admin's inventory, weapon.equip queues vanilla's
ISEquipWeaponAction on it, and the window opens only once the server's getPrimaryHandItem reads the bat.

The plumbing (the recorder read, the XP-cap gate, the endurance rest, the bus helpers) is x42c_calib_lib's Calib,
imported from that frozen file and never edited; the window and its grade are new here.

THE WINDOW (M2): the XP-cap gate (perk.xp admin Strength; at or above CAP_XP, perk.set admin Strength PARK_LEVEL);
stats.setany admin ENDURANCE 1; inventory.add admin WEAPON 1 (server); weapon.equip WEAPON (client); the server's and
the client's getPrimaryHandItem.getFullType polled until the server's reads WEAPON (EQUIP_CAP_S); the recorder emptied
and the server log's size marked; RCON createhorde 1 admin; attack.melee MELEE_SWINGS at the nearest zombie within 2
tiles, retried every 2 s for MELEE_FIND_S (one more createhorde past half of it), up to MELEE_WINDOWS windows until the
target is dead; the AddXP events read back; the server log's lines since the mark matching INCONSISTENT_RX counted.

THE GRADE (pure; each branch has a failing case in testing/tests/test_x42d_melee_lib.py):
  as_predicted  at least one positive Strength AddXP event for admin;
  falsified     none, with a hit evidenced on the server: a positive AddXP event of a perk other than Strength and
                Fitness (the weapon skill's hit XP), or the target dead with no inconsistent hit packet logged;
  unmeasured    the cap at the open, the weapon not in the server's primary hand, no zombie in range, an inconsistent
                hit packet logged (the server rejected the hit), or swings with no hit evidenced.

Reply shapes (the harness's @reply lines): weapon.equip {ok, fullType, itemId, twoHands, queued [, reason |
queueError]}; inventory.add {ok, fullType, count, side, invWeight, maxWeight}; witness.chain {ok, value, hops,
failedAt}; attack.melee {ok, target, swings, weapon, result, file} | {ok, reason}; the attack-melee result {n, swings,
targetDead, returns}; the rest as x42c_calib_lib names them.

FROZEN WITH ITS FIRST RUN: once x424 has run, this file is never edited (CLAUDE.md s5); a later change is a new file.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # testing/
sys.path.insert(0, HERE)                    # experiments/

import xlib as X                                                 # noqa: E402
import x42c_calib_lib as C                                       # noqa: E402

REPO = C.REPO
SRV = C.SRV
CLI = C.CLI
USER = C.USER
LIB_FILE = "x42d_melee_lib.py"
WEAPON = "Base.BaseballBat"
EQUIP_WAIT_S = 2.0
EQUIP_CAP_S = 15.0
MELEE_SWINGS = 10
MELEE_WINDOWS = 3
MELEE_FIND_S = 60.0
MELEE_RESULT_S = 20.0
INCONSISTENT_RX = re.compile(r"PlayerHitZombie is not consistent|AttackCollisionCheckPacket is not consistent")
ECHO_RX = C.ECHO_RX


def grade_melee2(w):
    w = w or {}
    ev_all = w.get("events") or []
    ev = C.strength_events(ev_all)
    hits = C.other_perk_hits(ev_all)
    wins = w.get("windows") or []
    dead = any(isinstance(x.get("result"), dict) and x["result"].get("targetDead") is True for x in wins)
    bad = w.get("inconsistent") or []
    obs = {"events": len(ev), "amounts": [X.num(e.get("amount")) for e in ev][:30], "all_events": len(ev_all),
           "perks": sorted({str(e.get("perk")) for e in ev_all}),
           "other_perk_events": [{"perk": e.get("perk"), "amount": X.num(e.get("amount"))} for e in hits][:30],
           "windows": len(wins), "swings_made": [((x.get("result") or {}).get("swings")) for x in wins],
           "target_dead": dead, "inconsistent_lines": len(bad), "weapon_on_server": w.get("weapon_on_server"),
           "hordes": len(w.get("hordes") or []), "misses": w.get("misses"),
           "strength_sum": round(sum(X.num(e.get("amount")) or 0.0 for e in ev), 6), "dropped": w.get("dropped"),
           "xp_delta": ((X.num((w.get("xp_after") or {}).get("xp")) or 0) - (X.num((w.get("xp_before") or {})
                                                                                 .get("xp")) or 0))
           if (w.get("xp_after") and w.get("xp_before")) else None,
           "gate": w.get("gate")}
    if C.at_cap(w.get("gate")):
        obs["why"] = "the Strength experience was at the level-10 total (or unread) when the window opened"
        return "unmeasured", obs
    if ev:
        return "as_predicted", obs
    if w.get("weapon_on_server") is not True:
        obs["why"] = "the weapon never read in the server's primary hand"
        return "unmeasured", obs
    if not wins:
        obs["why"] = "no zombie came within 2 tiles: no swing window ran"
        return "unmeasured", obs
    if hits:
        obs["why"] = "a weapon-skill hit event and no positive Strength event"
        return "falsified", obs
    if bad:
        obs["why"] = "the server logged an inconsistent hit packet: the hit did not reach the server's hit path"
        return "unmeasured", obs
    if dead:
        obs["why"] = "the target died with no inconsistent hit packet and no positive Strength event"
        return "falsified", obs
    obs["why"] = "swings ran and no hit is evidenced"
    return "unmeasured", obs


class Melee(C.Calib):
    def __init__(self, xs, log_path=None):
        super().__init__(xs)
        self.log_path = log_path

    def log_mark(self):
        try:
            return os.path.getsize(self.log_path) if self.log_path else 0
        except OSError:
            return 0

    def lines_since(self, rx, mark, limit=60):
        if not self.log_path:
            return []
        out = []
        try:
            with open(self.log_path, encoding="utf-8", errors="replace") as fh:
                fh.seek(mark)
                for line in fh:
                    if rx.search(line) and not ECHO_RX.search(line):
                        out.append(line.strip()[:300])
                        if len(out) >= limit:
                            break
        except OSError:
            pass
        return out

    def phase_E(self):
        """The weapon: added by the server, equipped through vanilla's timed action, read in the server's hand."""
        w = self.D["equip"] = {}
        w["add"] = self.k("E_add", SRV, "inventory.add", f"{USER} {WEAPON} 1")
        self.sleep_until(self.xs.clock() + EQUIP_WAIT_S)
        w["equip"] = self.k("E_equip", CLI, "weapon.equip", WEAPON)
        end = self.xs.clock() + EQUIP_CAP_S
        polls = []
        w["on_server"] = False
        while True:
            s = self.k("E_hand_s", SRV, "witness.chain", f"{USER} getPrimaryHandItem.getFullType", log=False)
            c = self.k("E_hand_c", CLI, "witness.chain", "getPrimaryHandItem.getFullType", log=False)
            polls.append({"wall": s.get("wall"), "server": s.get("value"), "client": c.get("value")})
            if s.get("value") == WEAPON:
                w["on_server"] = True
                break
            if self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + 1.0)
        w["polls"] = polls

    def phase_M2(self):
        w = self.D["melee"] = {"windows": [], "hordes": [], "misses": 0}
        w["weapon_on_server"] = (self.D.get("equip") or {}).get("on_server")
        w["gate"] = self.xp_gate("M_gate")
        w["rest"] = self.rest("M_rest")
        w["xp_before"] = self.k("M_xp_before", SRV, "perk.xp", f"{USER} Strength")
        w["reset"] = self.xp_reset("M_reset")
        mark = self.log_mark()
        w["hordes"].append(self.xs.rcon(f"createhorde 1 {USER}", "M_horde"))
        self.out["world_changes"]["left_in_place"].append("zombies spawned by createhorde near admin in M2")
        c = self.xs.clients.get(USER) if isinstance(self.xs.clients, dict) else None
        t_find = self.xs.clock()
        while len(w["windows"]) < MELEE_WINDOWS:
            self.xs.check()
            r = self.k("M_atk", CLI, "attack.melee", str(MELEE_SWINGS))
            if not r.get("ok"):
                w["misses"] += 1
                waited = self.xs.clock() - t_find
                if waited > MELEE_FIND_S:
                    self.xs.note(f"melee: no zombie within 2 tiles for {MELEE_FIND_S} s; {len(w['windows'])} window(s)")
                    break
                if waited > MELEE_FIND_S / 2 and len(w["hordes"]) < 2 + len(w["windows"]):
                    w["hordes"].append(self.xs.rcon(f"createhorde 1 {USER}", "M_horde"))
                self.sleep_until(self.xs.clock() + 2.0)
                continue
            started = self.xs.clock()
            win = {"reply": {k: r.get(k) for k in ("ok", "target", "swings", "weapon", "wall")}}
            res = None
            if c is not None and getattr(c, "bus", None) is not None:
                try:
                    res = c.bus.wait_result("attack-melee", timeout=MELEE_RESULT_S, after=started - 1.0)
                except Exception as e:             # noqa: BLE001
                    self.xs.note(f"melee: attack-melee result: {type(e).__name__}: {e}")
            else:
                self.sleep_until(started + MELEE_SWINGS * 1.2 + 2.0)
            win["result"] = res
            w["windows"].append(win)
            if isinstance(res, dict) and res.get("targetDead"):
                break
        self.sleep_until(self.xs.clock() + C.SETTLE_S)
        w.update(self.xp_read("M_read"))
        w["xp_after"] = self.k("M_xp_after", SRV, "perk.xp", f"{USER} Strength")
        w["hand_after"] = self.k("M_hand", SRV, "witness.chain", f"{USER} getPrimaryHandItem.getFullType")
        w["inconsistent"] = self.lines_since(INCONSISTENT_RX, mark)

    def body(self, phases=None):
        for name, fn in (phases or (("S", self.phase_S), ("E", self.phase_E), ("M2", self.phase_M2))):
            if self.xs.parked():
                self.out["abort"] = f"admin parked in the debugger before phase {name}"
                break
            self.xs.run_phase(name, fn)

    def grade_all(self):
        v, o = grade_melee2(self.D.get("melee"))
        self.xs.grade("7_melee", v, o, "a server-side hit (a weapon-skill event, or a dead target with no "
                                       "inconsistent hit packet) with no positive Strength event")


def main(profile_name, prefix, artifact, session_text, pred, budget_s, driver_file):
    from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
    from pzt import fixture as fx, profile                          # noqa: E402
    from pzt.bus import resolve_side                                # noqa: E402
    from pzt.harness import lint_paths                              # noqa: E402
    from pzt.paths import new_run_dir                               # noqa: E402
    from pzt.session import Timeline, attach_clients, make_server, teardown, verify   # noqa: E402

    prof = profile.load(profile_name)
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(prefix)
    tl = Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
           "world_changes": {"restored": "fixture default restored into the run dir (server and client caches)",
                             "left_in_place": []}}
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, predictions=pred, user="admin")
    xs.path = os.path.join(run_dir, artifact)
    doctor_clean, doctor_text = doctor()
    out.update({
        "run_id": run_id, "session": session_text, "driver": driver_file, "lib": LIB_FILE,
        "lib_base": C.LIB_FILE, "user": USER, "users": list(prof.users), "profile": prof.report(),
        "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                    "build": rec_fx.get("build")},
        "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
        "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", C.LUA_DIR),
        "harness_lua_dirty": git_dirty(C.LUA_DIR)[0],
        "probe_commit": git_say("log", "-1", "--format=%h", "--", C.PROBE_DIR),
        "probe_dirty": git_dirty(C.PROBE_DIR)[0],
        "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
        "xlib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
        "lib_commit": git_say("log", "-1", "--format=%h", "--", "testing/experiments/" + LIB_FILE),
        "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
        "constants": {k: v for k, v in globals().items() if re.match(r"^[A-Z][A-Z0-9_]+$", k)
                      and isinstance(v, (int, float, str, bool, tuple)) and k not in ("REPO",)},
        "predictions": pred,
    })
    out["constants"]["INCONSISTENT_RX"] = INCONSISTENT_RX.pattern
    if not doctor_clean:
        xs.refuse("doctor not clean; the session was not started (CLAUDE.md s5)")
    if out["harness_lua_dirty"] or out["probe_dirty"]:
        xs.refuse("the harness Lua or the probe mod is dirty; commit before the boot (CLAUDE.md s5)")
    m0 = xs.mem("preboot")
    if not X.memory_ok(m0["free_gb"], C.MIN_FREE_GB):
        xs.refuse(f"free memory {m0['free_gb']} GB under {C.MIN_FREE_GB} GB; the session was not started")
    out["lint_errors"] = lint_paths(prof.sources)
    if out["lint_errors"]:
        xs.refuse("the layout lint found an ERROR in a profile mod folder; the session was not started")
    server = None
    mm = None
    try:
        server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                             sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
        holder["server"] = server
        xs.server = server
        out["server_launch_wall"] = xs.wall()
        server.start(timeout=prof.server_timeout)
        out["server_started_wall"] = xs.wall()
        tl.mark("server_started")
        clients.update(attach_clients(run_dir, prof, server, rec_fx, tl, started=started))
        tl.mark("session_ready")
        out["session_ready_wall"] = xs.wall()
        out["build"] = server.build
        out["verify"] = verify(prof, server, clients, tl)
        xs.mem("ready")
        xs.persist()
        mm = Melee(xs, log_path=server.log_path)
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            mm.body()
    except Exception as e:                         # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            L = out["logs"] = {"patterns": {"log": C.LOG_RX.pattern, "inconsistent": INCONSISTENT_RX.pattern}}
            if server is not None:
                L["server"], L["server_echo_excluded"] = X.grep_noecho(server.log_path, C.LOG_RX, 200, ECHO_RX,
                                                                         C.NEVER_RX)
                L["server_inconsistent"], _ = X.grep_noecho(server.log_path, INCONSISTENT_RX, 40, ECHO_RX,
                                                            C.NEVER_RX)
            for c in every:
                lines, _ = X.grep_noecho(c.console, C.LOG_RX, 60, ECHO_RX, C.NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        def grade_all():
            if mm is not None:
                mm.grade_all()

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "observed": (out.get("verdicts", {}).get("7_melee") or {}).get("observed"),
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
