"""b_actions -- Plan 21 Task 10, Stage B (spec § 4.2): the actions' go/no-go. One boot of agent-nozombies (fixture
`agent`, admin -debug, PZTestKit + PZAgent, zombies none); a fixed goal sequence, no policy.

PHASES (each through xs.run_phase; a phase's fault is recorded and the next still runs):
  hello   wait for the hello line (HELLO_TIMEOUT_S) and the first frame (FRAME_TIMEOUT_S); the first frame's x, y is
          the spawn (readings.spawn_xy), the target of every repetition's last goto.
  spawn   the fallback items through xs.spawn (RCON additem confirmed by item.get): SPAWN's Base.WaterBottleFull x1
          and Base.Apple x SEQUENCES, so every repetition's eat and drink have an item when its loot found none
          (readings.spawned, xs.spawn's rows as returned).
  rep1-5  one repetition each (rep_once), its row appended to readings.reps before its first step and persisted after:
            scan SCAN_R -> the pick: among the scan's squares with a non-empty `containers` not picked by an earlier
              repetition, the best tier (container items guessed food-like and water-like by world.FOOD_RX and
              WATER_RX, one point each, one more for any item), nearest the player within it; none -> the row's
              notes take `no_container_in_scan` and SCAN_R_WIDE is scanned once; still none -> the row stops there
            -> open: the first square on the Bresenham line between the player's square and the pick (endpoints
              excluded) carrying a `door` or `window` entry; opened only while shut (an open one is noted)
            -> goto beside the pick: its non-solid 8-neighbour in the scan nearest the player, sent as the square's
              centre in world coordinates (none free -> the step is recorded skipped)
            -> loot x y food -> loot x y water
            -> eat <fullType>: the first item_added event of this repetition whose fullType matches FOOD_RX and not
              WATER_RX (a drink is not a top-level Food), else Base.Apple (the spawned fallback)
            -> drink -> goto back to the spawn x, y.
          Every goal: its ack (ACK_TIMEOUT_S), then its end through a_pipe's goal_end map (the first frame whose goal
          is that seq and done or failed; the frame's gameMin and worldAge are the step's game clock), GOAL_TIMEOUT_S. Around the eat: the server's stats.all Hunger before the eat's send, then,
          when the eat ended done, every EAT_POLL_S up to EAT_POLL_MAX_S until Hunger fell below the pre-eat reading
          (row.server_hunger {before, after[], moved}), each with this process's wall ms; the frames' client hunger
          at the same points is kept beside it, informational.
          A row: rep, scan, pick, door, steps [{goal, args, seq, state, detail, ms, ack, gameMin, worldAge}],
          eat_pick, server_hunger, notes, completed (every step planned ran and ended done).

A step's state: done | failed (the Lua's own detail, graded against agent.reasons.REASONS) | refused (the ack's
reason) | timeout | skipped. out["missing"], gaps, bad, lua_errors and client_lua_errors as a_pipe's; the grade is
b_grade.py over the artifact (grades.gate_b). out["finished"] is set last; the controller polls the persisted artifact.

Clocks: a line's wallMs is the client's PZA.now(); a key ending in PyMs (and server_hunger's wallMs) is this
process's time.time() in ms. The grade never subtracts one from the other.

RULES: never edited after its run (the next pass is b_actions_2.py); takes no argument; one live session at a time;
free memory gated at MIN_FREE_GB before the boot; never -safemode.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.drivers import a_pipe as AP                # noqa: E402  (Pipe and the boot seams; a later cleanup moves them to _pipe.py)
from agent.world import FOOD_RX, WATER_RX             # noqa: E402

KEY = "b_actions"
DRIVER = "b_actions.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "b_actions.json"
BUDGET_S = 560.0
USER = "admin"
MIN_FREE_GB = 12.0
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))

SEQUENCES = 5
HELLO_TIMEOUT_S = 60.0
FRAME_TIMEOUT_S = 10.0
ACK_TIMEOUT_S = 10.0
SCAN_R = 15
SCAN_R_WIDE = 25
SCAN_TIMEOUT_S = 15.0
GOAL_TIMEOUT_S = 60.0
EAT_POLL_S = 5.0
EAT_POLL_MAX_S = 60.0
FALLBACK_FOOD = "Base.Apple"
SPAWN = (("Base.WaterBottleFull", 1), (FALLBACK_FOOD, SEQUENCES))
POLL_S = 0.1
AGENT_LUA = "testing/PZAgent"
CLIENT_ERR_RX = AP.CLIENT_ERR_RX
WATER_PREFIX_RX = re.compile(r"\.Water")
STEP_ORDER = ("scan", "open", "goto", "loot food", "loot water", "eat", "drink", "goto")

CONSTANTS = {k: globals()[k] for k in (
    "SEQUENCES", "HELLO_TIMEOUT_S", "FRAME_TIMEOUT_S", "ACK_TIMEOUT_S", "SCAN_R", "SCAN_R_WIDE", "SCAN_TIMEOUT_S",
    "GOAL_TIMEOUT_S", "EAT_POLL_S", "EAT_POLL_MAX_S", "FALLBACK_FOOD", "SPAWN", "POLL_S", "BUDGET_S", "MIN_FREE_GB",
    "CLIENT_ERR_RX")}

parse_argv = AP.parse_argv
client_errors = AP.client_errors
clearing_make_client = AP.clearing_make_client
_seq = AP._seq


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "readings": {"spawn_xy": None, "spawned": [], "reps": []},
            "world_changes": {"left_in_place": []}, "finished": False}


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks (a_pipe's, on this driver's key and file). Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


def memory_gate(xs, wait=None):
    """a_pipe's memory wait: a false result refuses; the wall budget's clock restarts after it."""
    ok, readings = (wait or DL.wait_memory)(MIN_FREE_GB)
    xs.out["memory_wait"] = readings
    if not ok:
        xs.refuse("blocked: memory")
    xs.t0 = xs.clock()
    return readings


# ================================================================ pure helpers (planning over one scan line)
def line_cells(x0, y0, x1, y1):
    """Bresenham's cells from (x0, y0) to (x1, y1), both endpoints excluded."""
    cells = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    x, y = x0, y0
    while (x, y) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
        if (x, y) != (x1, y1):
            cells.append((x, y))
    return cells


def _items(sq):
    return [ft for c in _seq(sq.get("containers")) for ft in _seq((c or {}).get("items"))]


def water_like(ft):
    """WATER_RX, or any fullType whose name starts with Water (world.WATER_RX's trailing word boundary misses
    Base.WaterBottleFull)."""
    return bool(WATER_RX.search(ft) or WATER_PREFIX_RX.search(ft))


def tier(sq):
    """0..3: one point for any item in the square's containers, one for a food-like, one for a water-like fullType."""
    items = [str(i) for i in _items(sq)]
    return ((1 if items else 0) + (1 if any(FOOD_RX.search(i) for i in items) else 0)
            + (1 if any(water_like(i) for i in items) else 0))


def by_xy(scan, z=None):
    out = {}
    for s in _seq(scan.get("squares")):
        if z is None or s.get("z") == z:
            out[(s.get("x"), s.get("y"))] = s
    return out


def pick_container(scan, px, py, exclude=()):
    """The best-tier container square not in `exclude`, nearest (px, py) within its tier; None when none."""
    best = None
    for s in _seq(scan.get("squares")):
        if not _seq(s.get("containers")) or (s.get("x"), s.get("y"), s.get("z")) in exclude:
            continue
        d = math.hypot(s["x"] + 0.5 - px, s["y"] + 0.5 - py)
        key = (-tier(s), d)
        if best is None or key < best[0]:
            best = (key, s)
    if best is None:
        return None
    s = best[1]
    return {"x": s["x"], "y": s["y"], "z": s.get("z"), "dist": best[0][1], "tier": -best[0][0],
            "items": len(_items(s))}


def door_between(scan, px, py, pick):
    """The first square on the line from the player's square to the pick carrying a door or window; None when none."""
    sq = by_xy(scan, pick.get("z"))
    for cell in line_cells(int(math.floor(px)), int(math.floor(py)), pick["x"], pick["y"]):
        s = sq.get(cell)
        if s is None:
            continue
        for kind in ("door", "window"):
            if isinstance(s.get(kind), dict):
                return {"x": cell[0], "y": cell[1], "kind": kind, "open": s[kind].get("open") is True}
    return None


def beside(scan, px, py, pick):
    """The pick's non-solid 8-neighbour in the scan nearest (px, py); None when none is free."""
    sq = by_xy(scan, pick.get("z"))
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            s = sq.get((pick["x"] + dx, pick["y"] + dy))
            if s is None or s.get("solid") is True:
                continue
            d = math.hypot(s["x"] + 0.5 - px, s["y"] + 0.5 - py)
            if best is None or d < best[0]:
                best = (d, s["x"], s["y"])
    return None if best is None else (best[1], best[2])


def eat_choice(added):
    """The first fullType in `added` that is food-like and not a drink, else the fallback."""
    for ft in added:
        ft = str(ft)
        if FOOD_RX.search(ft) and not water_like(ft):
            return ft, "looted"
    return FALLBACK_FOOD, "fallback"


def server_hunger(r):
    """stats.all's Hunger from a bus_stats row; None when the reply carries none."""
    a = (r or {}).get("ack")
    v = a.get("stats") if isinstance(a, dict) else None
    v = v.get("Hunger") if isinstance(v, dict) else None
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ================================================================ the sequence
class Actions(AP.Pipe):
    """The hello, spawn and repetition phases over one Link; clock, sleep, bus_stats and spawn are injectable."""

    def __init__(self, xs, link, spawn=None, **kw):
        kw.setdefault("poll_s", POLL_S)
        super().__init__(xs, link, **kw)
        self.rd.setdefault("spawn_xy", None)
        self.rd.setdefault("spawned", [])
        self.rd.setdefault("reps", [])
        self.spawn = spawn or xs.spawn
        self.added = []           # item_added fullTypes, in line order
        self.end_clock = {}       # goal seq -> the game clock of its first done/failed frame
        self.picked = set()

    def on_line(self, l):
        super().on_line(l)
        k = l.get("kind")
        if k == "event" and l.get("event") == "item_added":
            self.added.append(l.get("fullType"))
        elif k == "frame":
            g = l.get("goal") or {}
            if g.get("state") in ("done", "failed") and g.get("seq") not in self.end_clock:
                self.end_clock[g.get("seq")] = {"gameMin": l.get("gameMin"), "worldAge": l.get("worldAge")}

    # ---- phase: hello
    def phase_hello(self):
        t0 = self.py_ms()
        self.wait_until(lambda: self.hello is not None, HELLO_TIMEOUT_S)
        self.out["hello_wait_ms"] = self.py_ms() - t0
        self.need_hello()
        self.out["hello"] = self.hello
        self.out["mode"] = self.hello.get("mode")
        if not self.wait_until(lambda: bool(self.frames), FRAME_TIMEOUT_S):
            raise RuntimeError("no frame after the hello: no spawn x, y")
        f = self.frames[0][0]
        self.rd["spawn_xy"] = {"x": f.get("x"), "y": f.get("y"), "z": f.get("z"), "seq": f.get("seq")}

    # ---- phase: spawn
    def phase_spawn(self):
        for ft, n in SPAWN:
            self.rd["spawned"].append(self.spawn(ft, n, "spawn_" + ft.split(".")[-1]))
            self.xs.persist()
        # one fresh frame read, so the spawn's own item_added events land before repetition 1 counts its loot
        n0 = len(self.frames)
        self.wait_until(lambda: len(self.frames) > n0, FRAME_TIMEOUT_S)

    # ---- the goal and scan steps
    def frame_hunger(self):
        f = self.frames[-1][0] if self.frames else {}
        return {"hunger": f.get("hunger"), "seq": f.get("seq"), "wallMs": f.get("wallMs")}

    def scan(self, row, r):
        n0 = len(self.scans)
        sent = self.py_ms()
        seq = self.link.send("scan", str(r))
        step = {"goal": "scan", "args": str(r), "seq": seq, "sentPyMs": sent}
        row["steps"].append(step)
        self.wait_until(lambda: len(self.scans) > n0 and self.link.ack_of(seq) is not None, SCAN_TIMEOUT_S)
        step["ack"] = self.link.ack_of(seq)
        step["ms"] = self.py_ms() - sent
        if len(self.scans) <= n0:
            step["state"], step["detail"] = "timeout", "no scan line"
            return None
        line = self.scans[n0][0]
        step["state"], step["detail"] = "done", "squares=%d" % len(_seq(line.get("squares")))
        row.setdefault("scan", []).append({"r": r, "seq": line.get("seq"), "squares": len(_seq(line.get("squares"))),
                                           "scanMs": line.get("scanMs"), "missing": _seq(line.get("missing"))})
        return line

    def goal(self, row, name, args=""):
        sent = self.py_ms()
        seq = self.link.send(name, args)
        step = {"goal": name, "args": args, "seq": seq, "sentPyMs": sent}
        row["steps"].append(step)
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        step["ack"] = ack
        if ack is None:
            step["state"], step["detail"] = "timeout", "no ack"
        elif not ack.get("ok"):
            step["state"], step["detail"] = "refused", ack.get("reason")
        elif self.wait_until(lambda: seq in self.goal_end, GOAL_TIMEOUT_S):
            # the end is read off the frames (a_pipe's goal_end map): the goal_done/goal_failed event cannot name its
            # goal, since PZA.emit overwrites the body's seq (the goal's) with the line's own
            end = self.goal_end[seq]
            step["state"], step["detail"] = end["state"], end["detail"]
            step["endSeq"], step["endWallMs"] = end.get("seq"), end.get("wallMs")
            step.update(self.end_clock.get(seq) or {})
        else:
            step["state"], step["detail"] = "timeout", "goal %d not finished in %ss" % (seq, GOAL_TIMEOUT_S)
        step["ms"] = self.py_ms() - sent
        return step

    def skip(self, row, name, args, why):
        row["steps"].append({"goal": name, "args": args, "state": "skipped", "detail": why})

    def stats_row(self):
        r = self.bus_stats(self.xs, USER)
        return {"hunger": server_hunger(r), "wallMs": r.get("wallMs")}

    def eat_watch(self, row, step):
        """After the eat: stats.all every EAT_POLL_S up to EAT_POLL_MAX_S until the server's Hunger fell below its
        pre-eat reading; only when the eat ended done."""
        sh = row["server_hunger"]
        if step.get("state") != "done":
            sh["skipped"] = "eat %s" % step.get("state")
            return
        pre = sh["before"].get("hunger")
        if pre is None:
            sh["skipped"] = "no pre-eat Hunger"
            return
        t0 = self.clock()
        while self.clock() - t0 < EAT_POLL_MAX_S:
            t_next = self.clock() + EAT_POLL_S
            self.wait_until(lambda: self.clock() >= t_next, EAT_POLL_S + 1.0)
            a = self.stats_row()
            sh["after"].append(a)
            if a["hunger"] is not None and a["hunger"] < pre:
                sh["moved"] = True
                break
        sh["client_after"] = self.frame_hunger()

    # ---- one repetition
    def rep_once(self, i):
        self.need_hello()
        spawn = self.rd.get("spawn_xy") or {}
        if not isinstance(spawn.get("x"), (int, float)):
            raise RuntimeError("no spawn x, y: the hello phase found no frame")
        self.xs.check()                     # a repetition past the budget records no row
        row = {"rep": i, "steps": [], "notes": [], "pick": None, "door": None, "eat_pick": None,
               "server_hunger": {"before": {}, "after": [], "moved": False}, "completed": False}
        self.rd["reps"].append(row)
        a0 = len(self.added)
        try:
            self._rep(row, spawn, a0)
        finally:
            self.sync_out()
            self.xs.persist()

    def _rep(self, row, spawn, a0):
        scan = self.scan(row, SCAN_R)
        me = self.world.me
        px, py = me.get("x"), me.get("y")
        pick = pick_container(scan, px, py, self.picked) if scan else None
        if pick is None:
            row["notes"].append("no_container_in_scan")
            scan = self.scan(row, SCAN_R_WIDE)
            pick = pick_container(scan, px, py, self.picked) if scan else None
        if pick is None:
            row["notes"].append("no_container_in_wide_scan")
            return
        row["pick"] = pick
        self.picked.add((pick["x"], pick["y"], pick["z"]))
        door = door_between(scan, px, py, pick)
        row["door"] = door
        if door is not None:
            if door["open"]:
                row["notes"].append("door_already_open")
            else:
                self.goal(row, "open", "%d %d" % (door["x"], door["y"]))
        nb = beside(scan, px, py, pick)
        if nb is None:
            self.skip(row, "goto", "", "no free neighbour")
        else:
            self.goal(row, "goto", "%s %s" % (str(nb[0] + 0.5), str(nb[1] + 0.5)))
        xy = "%d %d" % (pick["x"], pick["y"])
        self.goal(row, "loot", xy + " food")
        self.goal(row, "loot", xy + " water")
        ft, src = eat_choice(self.added[a0:])
        row["eat_pick"] = {"fullType": ft, "from": src, "added": list(self.added[a0:])}
        sh = row["server_hunger"]
        sh["before"] = self.stats_row()
        sh["client_before"] = self.frame_hunger()
        step = self.goal(row, "eat", ft)
        self.eat_watch(row, step)
        self.goal(row, "drink")
        self.goal(row, "goto", "%s %s" % (str(spawn["x"]), str(spawn["y"])))
        row["completed"] = all(s.get("state") == "done" for s in row["steps"])

    def phases(self):
        return ([("hello", self.phase_hello), ("spawn", self.phase_spawn)]
                + [("rep%d" % i, (lambda i=i: self.rep_once(i))) for i in range(1, SEQUENCES + 1)])


# ================================================================ the boot
def main(budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import fixture as fx, profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, PROFILE))
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = new_out()
    out["world_changes"]["restored"] = f"fixture {prof.fixture} restored into the run dir"
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    act = None
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            act = Actions(xs, DL.link_for(clients, USER))
            act.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = client_errors([(getattr(c, "username", "?"), c.console) for c in every])
            out["logs"] = {"patterns": {"client_error": CLIENT_ERR_RX}, "clients": found}
            out["client_lua_errors"] = n

        if act is not None:
            act.sync_out()
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "wall_seconds": out.get("wall_seconds")},
                     indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
