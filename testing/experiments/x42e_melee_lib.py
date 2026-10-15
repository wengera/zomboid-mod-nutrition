"""x42e_melee_lib -- the session engine of the Plan 13 Task 1 melee driver x425_melee.py, after x424-20261015-041802.

x424 (x42d_melee_lib.py, frozen with it) never swung: the server's inventory.add put the bat in the server's copy of
admin's inventory (its reply read invWeight 3.41) but the client's inventory never held it, so the harness's
weapon.equip answered "no Base.BaseballBat in the local inventory" and the server's primary hand stayed empty; and no
zombie came within 2 tiles in the 60 s after two RCON createhorde calls. Two changes here, the rest x42d's:
  1. the bat is added through RCON `additem "admin" "Base.BaseballBat" 1`, the admin command whose item reaches the
     client (the route xlib.Xs.spawn uses for every eaten food, confirmed there by the server's item.get), and
     weapon.equip is asked every EQUIP_RETRY_S until it answers ok, for EQUIP_ASK_CAP_S at most, before the server's
     primary hand is polled;
  2. the zombie search runs MELEE_FIND_S = 120 s with a createhorde every HORDE_EVERY_S (at most HORDE_MAX).
The grade is x42d's grade_melee2, unchanged.

FROZEN WITH ITS FIRST RUN: once x425 has run, this file is never edited (CLAUDE.md s5); a later change is a new file.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # testing/
sys.path.insert(0, HERE)                    # experiments/

import json
import re

import xlib as X                                                 # noqa: E402
import x42c_calib_lib as C                                       # noqa: E402
import x42d_melee_lib as D                                       # noqa: E402

LIB_FILE = "x42e_melee_lib.py"
USER = C.USER
SRV, CLI = C.SRV, C.CLI
WEAPON = D.WEAPON
ADD_WAIT_S = 2.5
EQUIP_RETRY_S = 1.0
EQUIP_ASK_CAP_S = 15.0
EQUIP_CAP_S = 15.0
MELEE_SWINGS = 10
MELEE_WINDOWS = 3
MELEE_FIND_S = 120.0
HORDE_EVERY_S = 30.0
HORDE_MAX = 4
MELEE_RESULT_S = 20.0
grade_melee2 = D.grade_melee2


class Melee(D.Melee):
    def phase_E(self):
        w = self.D["equip"] = {}
        w["additem"] = self.xs.rcon(f'additem "{USER}" "{WEAPON}" 1', "E_additem")
        self.out["world_changes"]["left_in_place"].append(f"RCON additem {WEAPON} x1")
        self.sleep_until(self.xs.clock() + ADD_WAIT_S)
        asks, end = [], self.xs.clock() + EQUIP_ASK_CAP_S
        while True:
            r = self.k("E_equip", CLI, "weapon.equip", WEAPON)
            asks.append({k: r.get(k) for k in ("ok", "queued", "itemId", "twoHands", "reason", "wall")})
            if r.get("ok") is True or self.xs.clock() >= end:
                break
            self.sleep_until(self.xs.clock() + EQUIP_RETRY_S)
        w["equip_asks"] = asks
        w["equip"] = asks[-1] if asks else None
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
        t_horde = t_find
        while len(w["windows"]) < MELEE_WINDOWS:
            self.xs.check()
            r = self.k("M_atk", CLI, "attack.melee", str(MELEE_SWINGS))
            if not r.get("ok"):
                w["misses"] += 1
                if self.xs.clock() - t_find > MELEE_FIND_S:
                    self.xs.note(f"melee: no zombie within 2 tiles for {MELEE_FIND_S} s; {len(w['windows'])} window(s)")
                    break
                if self.xs.clock() - t_horde > HORDE_EVERY_S and len(w["hordes"]) < HORDE_MAX:
                    w["hordes"].append(self.xs.rcon(f"createhorde 1 {USER}", "M_horde"))
                    t_horde = self.xs.clock()
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
            t_find = self.xs.clock()
        self.sleep_until(self.xs.clock() + C.SETTLE_S)
        w.update(self.xp_read("M_read"))
        w["xp_after"] = self.k("M_xp_after", SRV, "perk.xp", f"{USER} Strength")
        w["hand_after"] = self.k("M_hand", SRV, "witness.chain", f"{USER} getPrimaryHandItem.getFullType")
        w["inconsistent"] = self.lines_since(D.INCONSISTENT_RX, mark)


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
        "lib_base": [D.LIB_FILE, C.LIB_FILE], "user": USER, "users": list(prof.users), "profile": prof.report(),
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
    out["constants"]["D.INCONSISTENT_RX"] = D.INCONSISTENT_RX.pattern
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
            L = out["logs"] = {"patterns": {"log": C.LOG_RX.pattern, "inconsistent": D.INCONSISTENT_RX.pattern}}
            if server is not None:
                L["server"], L["server_echo_excluded"] = X.grep_noecho(server.log_path, C.LOG_RX, 200, C.ECHO_RX,
                                                                         C.NEVER_RX)
                L["server_inconsistent"], _ = X.grep_noecho(server.log_path, D.INCONSISTENT_RX, 40, C.ECHO_RX,
                                                            C.NEVER_RX)
            for c in every:
                lines, _ = X.grep_noecho(c.console, C.LOG_RX, 60, C.ECHO_RX, C.NEVER_RX)
                L.setdefault("clients", {})[getattr(c, "username", "?")] = lines

        def grade_all():
            if mm is not None:
                mm.grade_all()

        xs.finish(teardown, hard_kill, every, read_logs=read_logs, grade_all=grade_all)
        xs.mem("after")
        xs.persist()
        xs.copy_artifacts(C.REPO, run_id, run_dir, artifact)
    print(json.dumps({"verdicts": {k: v.get("verdict") for k, v in out.get("verdicts", {}).items()},
                      "observed": (out.get("verdicts", {}).get("7_melee") or {}).get("observed"),
                      "bus_dead": out.get("bus_dead"), "error": out.get("error"), "abort": out.get("abort"),
                      "budget_stop": out.get("budget_stop"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "summary_error": out.get("summary_error"), "run_id": run_id, "run_dir": run_dir,
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str)[:8000])
    return out
