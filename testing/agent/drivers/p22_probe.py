"""p22_probe -- Plan 22, the agent-base probe: one live session of agent-nozombies (fixture `agent0`; admin -debug,
PZTestKit + PZAgent 0.2, zombies none) that runs three experiments before the agent's base is designed
(.superpowers/sdd/2026-10-27-plan-22-agent-base-design/plan-22-options.md § 4; the Lua <-> Python interface is
probe-interface.md beside it):
  X1  the motor arms: does a Lua route reach the run gait? `goto x y <arm>` legs on an open-ground line and
      `autowalk dx dy s <arm>` legs, each read off the frames as pace, endurance slope, flags and heading;
  X2  the emit bench: what one link line costs, by part (encoder, open, write, held writer, poll), via the harness's
      `bench.global PZA.bench.<arm> <n>` on the client;
  X3  the heavy-load drain: health against the HEAVY_LOAD level and posture, and which side hears the HEAVYLOAD
      damage event (the server's `fall.probe` listener counts every tag; the client's `event.watch` and the
      PZAgent `damage` events count the client's).
The probe decides a design; it has no GO/NO-GO. Its verdicts are xs.grade rows, each a prediction recorded with its
falsifier, never a gate.

PHASES (each through xs.run_phase; a fault is recorded and the next still runs; a "0.1" hello sets out["abort"] and
every later phase skips):
  hello_and_map  the hello (modVersion must read "0.2") and the `bench` line (out["bench_info"]); `scan SCAN_R`, awaited
                 to its done part; choose_line: the nearest run of LINE_LEN squares along +x, +y, -x, -y (that order on
                 a tie) at the player's z whose every square and both side rows read solid false, solidTrans false and
                 carry no room, building, door or window; A the end nearest the player, B the other. No such run:
                 the pass-4 leg (A the settled position, B = A + (FALLBACK_DX, 0)), out["line"]["fallback"].
  x2_bench       standing, before any walk: BENCH_REPS reps of every BENCH_ARMS arm, then per rep the held writer
                 (heldOpen 1, heldWrite HELD_N, heldClose 1). Rows {arm, rep, n, ms, usPerCall, error}; a reply with
                 error or a non-dict is a row with error (never raised). Summary per arm: the median usPerCall over
                 the reps, the bytes from bench_info and us_per_kb = usPerCall / (bytes / 1024) for US_PER_KB_ARMS.
  x1_motor       `goto A walk` (the approach, arm `approach`, ungraded); `rate X1_RATE_HZ` (10 Hz frames through
                 X1, ack awaited; the readings do not depend on the rate); MOTOR_ARMS x LEGS_PER_ARM legs, each to the
                 end of the line the character is not at (so the legs alternate A->B, B->A across the whole phase);
                 the AUTOWALK_LEGS (3 s walks, 1.5 s runs: about 4.8 tiles each), each after its own `goto` to the
                 line's midpoint M (arm `centre`, ungraded; its 1.0 done radius is accepted: the start lands within
                 a tile of M on the side it came from and the alternating legs head the other way, so at least 5
                 tiles of checked strip lie ahead), each (dx, dy) written along the line's axis (dx along it, A
                 toward B, so the first leg heads from M toward B; dy across it) as the wanted WORLD vector and sent
                 in the engine's INPUT space (input_vector: the inverse of IsoPlayer.updateMovementFromInput
                 L3025-L3026, world x = iy + ix, world y = iy - ix; the length kept as an input length), the heading
                 graded against the world vector. Before them, an ungraded calibration leg (a centre goto, then
                 CALIBRATE_LEG, world (1, 0) along the axis for 1.5 s, recorded as autowalk_calibration): a signed
                 heading error above CALIBRATE_TOL_DEG is snapped to the nearest 45 deg and its negative applied to
                 every later vector (autowalk_correction_deg; 0 otherwise or with no reading). A leg whose frames
                 leave the checked strip (the LINE_LEN squares and the rows one either
                 side; the fallback's band from A to B likewise) voided "left the strip", its heading and pace kept
                 and its samples out of every grade; the `toggle` arm only when pace_of("forcerun") <
                 TOGGLE_IF_BELOW x pace_of("walk"); a `goto A walk` back (arm `return`, ungraded). Past
                 X1_DEADLINE_S of the loop wall no new leg starts: each is recorded skipped ("x1 deadline"). X1
                 ends with `rate X1_RATE_BACK_HZ` (5), ack awaited, before X3; both acks are kept (rate_on,
                 rate_back).
  x3_load        the server `fall.probe admin` listener and the client `event.watch OnPlayerGetDamage`; `before` from
                 the latest frame; up to LOAD_MAX_ADDS RCON `additem "admin" "Base.Plank" 1` (the route that
                 reaches the client), each awaited by a frame whose weight rose (LOAD_SETTLE_S), until a frame
                 reads HEAVY_LOAD >= 3 (level3_at_ratio = weight / maxWeight there); the first add whose frame weight
                 did not rise stops the load (load_stalled_at); `walk` legs (arm `walk_loaded`) for
                 WALK_S since the first leg's ack or until a frame reads health <= HEALTH_FLOOR; STILL_S standing;
                 `drop Base.Plank k` to level 2 (k below); WALK2_S of `walk` legs (arm `walk_level2`); the readbacks.
                 k is the smallest count with 1.25 x max <= weight - k x PLANK_W < 1.5 x max (#3926's level-2 band),
                 else the smallest with weight - k x PLANK_W < 1.5 x max, else every plank added; at least 1.
  server         `stats.all admin` once, for the write-up.

READINGS (out["readings"]: bench, motor, load, line, server), verbatim from probe-interface.md § 7:
  pace (tiles/s) of a leg: over the leg's frames with moving == true, consecutive pairs' hypot(dx, dy) summed over
      the wallMs span between the first and last moving frame (the Stage C guide's measure,
      testing/artifacts/c_survive_2-20261026-195516/GUIDE.md § 4); None under 2 moving frames.
  endurance slope: (endurance_last - endurance_first) / (wallMs span / 1000) over the leg's frames.
  flags: counts of frames with running, sprinting, motor.forceRun, motor.updRunning, motor.updForceRun,
      motor.autoWalk true, and the frame count.
  heading error (autowalk legs): the angle in degrees between the commanded (dx, dy) and the displacement from the
      first to the last frame of the leg.
  A leg's frames are those with seq above its ack's up to its goal's end frame. Each leg row also keeps the goal's end
  state and detail, first_move (a_pipe_4.first_move) and cmd_move_ms (its wallMs minus the ack's, the client's clock).
  X3's trace keeps {seq, wallMs, health, level, weight, moving, action} per frame from the phase's start (level is
  moodles.HEAVY_LOAD); a drop is a consecutive-frame health fall > DROP_EPS, carrying the level and moving of the frame
  before it; its window (walk_loaded, still, walk_level2) is the seq range the frame after it falls in.

PREDICTIONS (recorded, not gates; each grade's falsifier is in its row; zero samples reads unmeasured, and every X3
grade rests on its evidence: the drops with a read level; the frames at health <= 75; the walk_level2 frames reading
level 2; the server readback with a drop observed; the drops; level 3 reached):
  x1_forcerun_runs     median pace of forcerun >= 1.3 x walk's (falsifier: below)
  x1_setrun_walks      median pace of setrun within 5 % of walk's (falsifier: outside)
  x1_autowalk_runs     median pace of the autowalk forcerun legs >= 1.3 x walk's (falsifier: below)
  x1_autowalk_heads    every autowalk leg's heading error <= 15 degrees (falsifier: one above)
  x1_forcerun_tick     observed and recorded whatever it reads (a walk confirms the frameStep reading)
  x1_once_holds        the once leg's updForceRun count >= 90 % of its frames reading motor.autoWalk true (falsifier:
                       below)
  x1_endurance         forcerun's endurance slope more negative than walk's (falsifier: not)
  x3_drops_at_level3_only   every drop's level >= 3 (falsifier: a drop at <= 2; an unread level is counted apart)
  x3_floor_75          no drop from a health <= 75 (falsifier: one)
  x3_drops_while_still the count of drops in the still window, recorded
  x3_level2_no_drop    no drop during walk_level2 (falsifier: one)
  x3_server_hears_heavyload  fall.probe's counts carry a HEAVYLOAD tag above 0 (falsifier: absent or 0)
  x3_client_hears_heavyload  0 client hearings (the register's #2597), event.watch's count and the HEAVYLOAD damage
                       events (falsifier: > 0)
  x3_level3_at_ratio   level 3 at a carry ratio >= 1.5 and < 1.75 (#3926; falsifier: outside)

Clocks: as pass 1 (a line's wallMs is the client's PZA.now(); a key ending in PyMs is this process's time.time() in ms).
The two are never subtracted from each other by a grade.

RULES: never edited after its run (the next probe is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode; launched detached by the controller. BUDGET_S counts
from the memory gate, so the boot spends it. a_pipe.py,
a_pipe_2.py and a_pipe_4.py are frozen and imported, never changed. PLANK_W is the 42.21 scripts' Base.Plank Weight,
re-read by the guide.
"""
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.drivers import a_pipe as AP                # noqa: E402  (the frozen pass-1 file: the boot seams)
from agent.drivers import a_pipe_2 as AP2             # noqa: E402  (the frozen pass-2 file: Pipe2)
from agent.drivers import a_pipe_4 as AP4             # noqa: E402  (the frozen pass-4 file: first_move)

KEY = "p22_probe"
DRIVER = "p22_probe.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "p22_probe.json"
USER = "admin"
BUDGET_S = 720.0           # the wall budget from the memory gate on, the boot included (AP.memory_gate resets the
                           # clock before DL.boot): the whole session stays under the 15-minute split
MIN_FREE_GB = DL.MIN_FREE_GB
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))
AGENT_LUA = "testing/PZAgent"
AGENT_PY = "testing/agent"
CLIENT_ERR_RX = AP.CLIENT_ERR_RX

MOD_VERSION = "0.2"
HELLO_TIMEOUT_S = 60.0
ACK_TIMEOUT_S = 10.0
POLL_S = 0.1
SCAN_R = 15
SCAN_TIMEOUT_S = 30.0
LINE_LEN = 12
LINE_DIRS = (("+x", 1, 0), ("+y", 0, 1), ("-x", -1, 0), ("-y", 0, -1))
FALLBACK_DX = 10

BENCH_REPS = 3
BENCH_ARMS = [("json", 500), ("jsonNoSort", 500), ("compact", 500), ("concat", 500), ("openWrite", 500),
              ("openWrite20", 500), ("openOnly", 500), ("poll", 500)]
HELD_ARMS = [("heldOpen", 1), ("heldWrite", 500), ("heldClose", 1)]
US_PER_KB_ARMS = ("json", "jsonNoSort", "compact", "openWrite", "heldWrite")
S20_BYTES = 20             # probe-interface.md § 5: S20 is a 20-byte string
BENCH_BYTES_KEY = {"json": "json21Bytes", "jsonNoSort": "noSortBytes", "compact": "compactBytes",
                   "concat": "json21Bytes", "openWrite": "json21Bytes", "heldWrite": "json21Bytes"}

MOTOR_ARMS = ["walk", "setrun", "forcerun", "forcerun_tick", "forcesprint"]
X1_DEADLINE_S = 450.0      # past this loop wall (from the memory gate, the boot included) X1 starts no new leg (each
                           # recorded skipped), so X3 keeps its wall
CALIBRATE_LEG = (1, 0, 1.5, "walk")   # the ungraded first autowalk leg: world (1 along the axis, 0), 1.5 s, walk
CALIBRATE_TOL_DEG = 15.0   # a calibration heading error above this is snapped to 45 deg and corrected
SNAP_DEG = 45.0
CALIBRATE_MIN_TILES = 1.0  # a calibration leg that moved less than this gives no correction (its heading is noise)
LEGS_PER_ARM = 3
SETTLE_S = 3.0
GOAL_TIMEOUT_S = 40.0
AUTOWALK_LEGS = [(1, 0, 3.0, "walk"), (-1, 0, 1.5, "forcerun"), (2, 0, 1.5, "forcerun"), (-1.95, 0, 1.5, "once"),
                 (1, 0, 1.5, "forcerun"), (-1, 0, 3.0, "walk")]   # ~4.8 tiles each at 1.6 / 3.2 tiles/s: inside the
                                                                  # >= 5 tiles of strip ahead of a re-centred start
X1_RATE_HZ = 10            # `rate 10` after the approach: a 1.5 s leg carries ~15 frames for its pace
X1_RATE_BACK_HZ = 5        # `rate 5` at X1's end, before X3
AUTOWALK_PAD_S = 10.0      # an autowalk leg's goal timeout is its seconds plus this
TOGGLE_IF_BELOW = 1.3
TOGGLE_LEGS = 3
RUN_RATIO = 1.3            # A's and C's placeholder: no vanilla run speed is read
SETRUN_TOL = 0.05
HEADING_MAX_DEG = 15.0
ONCE_HOLD_FRAC = 0.9

LOAD_MAX_ADDS = 14
LOAD_ITEM = "Base.Plank"
LOAD_SETTLE_S = 5.0
HEAVY_LEVEL = 3
LEVEL2_RATIO = 1.25        # #3926's thresholds: level 2 from 1.25, 3 from 1.5, 4 from 1.75 of maxWeight
LEVEL3_RATIO = 1.5
LEVEL4_RATIO = 1.75
PLANK_W = 3.0              # the 42.21 scripts' Base.Plank Weight; the guide re-reads it
WALK_S = 30.0
HEALTH_FLOOR = 75.0
WALK_MAX_LEGS = 12         # a guard on the timed walk loops: refused legs return at once
STILL_S = 15.0
DROP_TIMEOUT_S = 20.0
WALK2_S = 15.0
DROP_EPS = 0.05

CONSTANTS = {k: globals()[k] for k in (
    "BUDGET_S", "MIN_FREE_GB", "CLIENT_ERR_RX", "MOD_VERSION", "HELLO_TIMEOUT_S", "ACK_TIMEOUT_S", "POLL_S", "SCAN_R",
    "SCAN_TIMEOUT_S", "LINE_LEN", "LINE_DIRS", "FALLBACK_DX", "BENCH_REPS", "BENCH_ARMS", "HELD_ARMS",
    "US_PER_KB_ARMS", "S20_BYTES", "BENCH_BYTES_KEY", "MOTOR_ARMS", "LEGS_PER_ARM", "SETTLE_S", "GOAL_TIMEOUT_S",
    "AUTOWALK_LEGS", "AUTOWALK_PAD_S", "X1_DEADLINE_S", "CALIBRATE_LEG", "CALIBRATE_TOL_DEG", "SNAP_DEG", "CALIBRATE_MIN_TILES", "X1_RATE_HZ", "X1_RATE_BACK_HZ", "TOGGLE_IF_BELOW", "TOGGLE_LEGS", "RUN_RATIO", "SETRUN_TOL",
    "HEADING_MAX_DEG", "ONCE_HOLD_FRAC", "LOAD_MAX_ADDS", "LOAD_ITEM", "LOAD_SETTLE_S", "HEAVY_LEVEL",
    "LEVEL2_RATIO", "LEVEL3_RATIO", "LEVEL4_RATIO", "PLANK_W", "WALK_S", "HEALTH_FLOOR", "WALK_MAX_LEGS", "STILL_S",
    "DROP_TIMEOUT_S", "WALK2_S", "DROP_EPS")}
CONSTANTS["MOVE_EPS_TILES"] = AP4.MOVE_EPS_TILES

PREDICTIONS = {
    "x1_forcerun_runs": "median forcerun pace >= %s x walk's" % RUN_RATIO,
    "x1_setrun_walks": "median setrun pace within %s of walk's" % SETRUN_TOL,
    "x1_autowalk_runs": "median autowalk forcerun pace >= %s x walk's" % RUN_RATIO,
    "x1_autowalk_heads": "every autowalk leg's heading error <= %s deg" % HEADING_MAX_DEG,
    "x1_forcerun_tick": "read either way (a walk confirms the frameStep reading)",
    "x1_once_holds": "the once leg's updForceRun count >= %s of its autoWalk frames" % ONCE_HOLD_FRAC,
    "x1_endurance": "forcerun's endurance slope more negative than walk's",
    "x3_drops_at_level3_only": "every drop at HEAVY_LOAD >= %d" % HEAVY_LEVEL,
    "x3_floor_75": "no drop from a health <= %s" % HEALTH_FLOOR,
    "x3_drops_while_still": "recorded",
    "x3_level2_no_drop": "no drop while walking at level 2",
    "x3_server_hears_heavyload": "the server listener counts HEAVYLOAD > 0",
    "x3_client_hears_heavyload": 0,
    "x3_level3_at_ratio": "level 3 at a carry ratio >= %s and < %s (#3926)" % (LEVEL3_RATIO, LEVEL4_RATIO),
}


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "readings": {"bench": {}, "motor": {}, "load": {}, "line": None, "server": []},
            "world_changes": {"left_in_place": []}, "finished": False}


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua, the agent Python (link, world, the imported drivers) and the driver
    committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    c["agent_py_dirty"] = git_dirty(AGENT_PY)[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["driver_dirty"] is False and c["agent_py_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint) and the driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


# ================================================================ readings (pure functions of frames)
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _median(vals):
    vals = [v for v in vals if _num(v) is not None]
    return statistics.median(vals) if vals else None


def _motor(f):
    m = f.get("motor")
    return m if isinstance(m, dict) else {}


def pace(frames):
    """Tiles/s over the frames with moving == true: consecutive pairs' hypot summed over the wallMs span between the
    first and last moving frame; None under 2 moving frames or on a zero span."""
    mv = [f for f in frames if f.get("moving") is True and _num(f.get("x")) is not None
          and _num(f.get("y")) is not None and _num(f.get("wallMs")) is not None]
    if len(mv) < 2:
        return None
    span = (mv[-1]["wallMs"] - mv[0]["wallMs"]) / 1000.0
    if span <= 0:
        return None
    d = sum(math.hypot(b["x"] - a["x"], b["y"] - a["y"]) for a, b in zip(mv, mv[1:]))
    return d / span


def endurance_slope(frames):
    """(endurance_last - endurance_first) / (wallMs span / 1000) over the frames that read both; None under 2 or on a
    zero span."""
    fr = [f for f in frames if _num(f.get("endurance")) is not None and _num(f.get("wallMs")) is not None]
    if len(fr) < 2:
        return None
    span = (fr[-1]["wallMs"] - fr[0]["wallMs"]) / 1000.0
    if span <= 0:
        return None
    return (fr[-1]["endurance"] - fr[0]["endurance"]) / span


def flags(frames):
    """Counts of frames reading running, sprinting, motor.forceRun, motor.updRunning, motor.updForceRun and
    motor.autoWalk true, and the frame count."""
    return {"running": sum(1 for f in frames if f.get("running") is True),
            "sprinting": sum(1 for f in frames if f.get("sprinting") is True),
            "forceRun": sum(1 for f in frames if _motor(f).get("forceRun") is True),
            "updRunning": sum(1 for f in frames if _motor(f).get("updRunning") is True),
            "updForceRun": sum(1 for f in frames if _motor(f).get("updForceRun") is True),
            "autoWalk": sum(1 for f in frames if _motor(f).get("autoWalk") is True),
            "frames": len(frames)}


def _placed(frames):
    return [f for f in frames if _num(f.get("x")) is not None and _num(f.get("y")) is not None]


def displacement(frames):
    """Tiles from the first to the last placed frame; None under 2."""
    p = _placed(frames)
    if len(p) < 2:
        return None
    return math.hypot(p[-1]["x"] - p[0]["x"], p[-1]["y"] - p[0]["y"])


def heading_error_deg(frames, dx, dy):
    """The angle in degrees between the commanded (dx, dy) and the first-to-last displacement; None under 2 placed
    frames, a zero displacement or a zero command."""
    p = _placed(frames)
    if len(p) < 2:
        return None
    ex, ey = p[-1]["x"] - p[0]["x"], p[-1]["y"] - p[0]["y"]
    n1, n2 = math.hypot(ex, ey), math.hypot(dx, dy)
    if n1 == 0 or n2 == 0:
        return None
    c = max(-1.0, min(1.0, (ex * dx + ey * dy) / (n1 * n2)))
    return math.degrees(math.acos(c))


def _open(s):
    return (isinstance(s, dict) and s.get("solid") is False and s.get("solidTrans") is False
            and s.get("room") is None and s.get("building") is None and s.get("door") is None
            and s.get("window") is None)


AXES = {name: (ux, uy) for name, ux, uy in LINE_DIRS}


def axis_vector(dirname, dx, dy):
    """(dx, dy) written along a line's axis: dx along it (from A toward B), dy across it (its left normal)."""
    ux, uy = AXES[dirname]
    vx, vy = dx * ux - dy * uy, dx * uy + dy * ux
    return (vx + 0.0) or 0.0, (vy + 0.0) or 0.0           # never a -0.0


def input_vector(wx, wy, correction_deg=0.0):
    """The auto-walk input vector for a wanted world vector (wx, wy): its unit direction, rotated by correction_deg,
    taken into the engine's input space by the inverse of IsoPlayer.updateMovementFromInput @136-157 L3025-L3026
    (42.21: playerMoveDir.x = iy + ix, playerMoveDir.y = iy - ix), its length L = |(wx, wy)| kept as an INPUT length
    (as the key vectors' L206-L207): ix = L (ux - uy) / sqrt 2, iy = L (ux + uy) / sqrt 2, so the engine's world
    vector is L sqrt 2 (ux, uy). Rounded to 6 decimals; (0, 0) for a zero vector."""
    n = math.hypot(wx, wy)
    if n == 0:
        return 0.0, 0.0
    th = math.atan2(wy, wx) + math.radians(correction_deg)
    ux, uy = math.cos(th), math.sin(th)
    r2 = math.sqrt(2.0)
    return round(n * (ux - uy) / r2, 6) + 0.0, round(n * (ux + uy) / r2, 6) + 0.0


def heading_signed_deg(frames, dx, dy):
    """The signed angle in degrees (-180, 180] from the commanded (dx, dy) to the first-to-last displacement
    (counter-clockwise positive in world x, y); None where heading_error_deg is None."""
    p = _placed(frames)
    if len(p) < 2 or math.hypot(dx, dy) == 0:
        return None
    ex, ey = p[-1]["x"] - p[0]["x"], p[-1]["y"] - p[0]["y"]
    if math.hypot(ex, ey) == 0:
        return None
    a = math.degrees(math.atan2(ey, ex) - math.atan2(dy, dx))
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def correction_of(signed_deg, displacement=None, tol=CALIBRATE_TOL_DEG):
    """The extra rotation for every later autowalk vector: minus the calibration's signed heading error snapped to
    the nearest multiple of SNAP_DEG, when its magnitude is above tol; else 0 (no reading included). Two guards (the
    fix-3 re-review): only a +-45 deg snap is applied, the one frame error the jar's L3025-L3026 transform can give (a
    +-90 or 180 reading is a deflected leg, not a frame), and none when the calibration moved under CALIBRATE_MIN_TILES
    (a leg that barely moved reads a direction the engine did not choose)."""
    if signed_deg is None or abs(signed_deg) <= tol:
        return 0.0
    if displacement is not None and displacement < CALIBRATE_MIN_TILES:
        return 0.0
    snapped = -SNAP_DEG * round(signed_deg / SNAP_DEG) + 0.0
    return snapped if abs(snapped) == SNAP_DEG else 0.0


def _arg(v):
    """A number as a goal argument: an integral float bare ("1", "-1"), else its repr ("-1.95")."""
    v = float(v) or 0.0
    return str(int(v)) if v.is_integer() else repr(v)


def strip_of(x0, y0, dirname, n):
    """The checked strip of a run: its n squares from (x0, y0) along the axis and the rows one either side, as
    choose_line checks them, as a set of (x, y)."""
    ux, uy = AXES[dirname]
    return {(x0 + ux * i + uy * side, y0 + uy * i + ux * side) for i in range(n) for side in (-1, 0, 1)}


def off_strip(frames, strip):
    """The placed frames whose square (floor(x), floor(y)) is not in the strip."""
    return [f for f in _placed(frames) if (int(math.floor(f["x"])), int(math.floor(f["y"]))) not in strip]


def choose_line(squares, me_xy, z=0, n=LINE_LEN):
    """The nearest open run of n squares. `squares` maps (x, y, z) to a scan square (World.map). A run starts at a
    square A and steps along one of LINE_DIRS; every square and the squares one row either side of it must be in the
    scan and open (_open). The nearest run by A's centre to me_xy wins (a run's reverse is the same squares from its
    other end, so A is the end nearest the player); a tie goes to the LINE_DIRS order. Returns {ax, ay, bx, by, dir,
    dist, candidates} or None (candidates is the open runs seen)."""
    mx, my = me_xy
    best, seen = None, 0
    for (x, y, sz) in squares:
        if sz != z:
            continue
        for rank, (name, ux, uy) in enumerate(LINE_DIRS):
            ok = True
            for i in range(n):
                cx, cy = x + ux * i, y + uy * i
                for side in (-1, 0, 1):
                    if not _open(squares.get((cx + uy * side, cy + ux * side, z))):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            seen += 1
            dist = math.hypot(x + 0.5 - mx, y + 0.5 - my)
            key = (dist, rank, x, y)
            if best is None or key < best[0]:
                best = (key, {"ax": x, "ay": y, "bx": x + ux * (n - 1), "by": y + uy * (n - 1), "dir": name,
                              "dist": dist})
    if best is None:
        return None
    out = dict(best[1])
    out["candidates"] = seen
    return out


def unload_count(weight, max_weight, added, plank_w=PLANK_W):
    """The planks to drop for level 2: the smallest k (1..added) with LEVEL2_RATIO x max <= weight - k x plank_w <
    LEVEL3_RATIO x max; else the smallest with weight - k x plank_w < LEVEL3_RATIO x max; else every plank added (at
    least 1). Returns (k, the predicted ratio after the drop, which rule chose it)."""
    if _num(weight) is None or not _num(max_weight) or added < 1:
        return max(1, added), None, "unread"
    ks = range(1, added + 1)
    band = [k for k in ks if LEVEL2_RATIO * max_weight <= weight - k * plank_w < LEVEL3_RATIO * max_weight]
    if band:
        k, why = band[0], "level2 band"
    else:
        below = [k for k in ks if weight - k * plank_w < LEVEL3_RATIO * max_weight]
        k, why = (below[0], "below level 3") if below else (added, "every plank")
    return k, (weight - k * plank_w) / max_weight, why


def level_of(f):
    m = f.get("moodles")
    return _num(m.get("HEAVY_LOAD")) if isinstance(m, dict) else None


def trace_row(f):
    return {"seq": f.get("seq"), "wallMs": f.get("wallMs"), "health": f.get("health"), "level": level_of(f),
            "weight": f.get("weight"), "moving": f.get("moving"), "action": f.get("action")}


def drops_of(trace, windows):
    """Consecutive-frame health falls > DROP_EPS, each with the level and moving of the frame before it and the window
    (by name) whose seq range (lo, hi] the frame after it falls in."""
    out = []
    for a, b in zip(trace, trace[1:]):
        ha, hb = _num(a.get("health")), _num(b.get("health"))
        if ha is None or hb is None or ha - hb <= DROP_EPS:
            continue
        win = next((k for k, (lo, hi) in windows.items() if hi is not None and lo < b["seq"] <= hi), None)
        out.append({"seq": b.get("seq"), "wallMs": b.get("wallMs"), "from": ha, "to": hb, "fall": ha - hb,
                    "level": a.get("level"), "moving": a.get("moving"), "window": win})
    return out


# ================================================================ the probe
class Probe(AP2.Pipe2):
    """Pass 2's Pipe (the link reader, settle and goal-end bookkeeping) with the probe's phases."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.parts = []                  # scanPart lines
        self.bench_line = None
        self.damage_events = []
        self.line = None
        self.line_dir = "+x"
        self.strip = set()
        self.at_end = "A"                # which end of the line the character is at (set by the approach)
        self.mt = {"legs": [], "centre": [], "autowalk": [], "toggle": []}
        self.ld = {}
        self.x3_seq0 = None
        self.windows = {}
        self.planks = 0

    def on_line(self, l):
        super().on_line(l)
        k = l.get("kind")
        if k == "scanPart":
            self.parts.append(l)
        elif k == "bench" and self.bench_line is None:
            self.bench_line = l
        elif k == "event" and l.get("event") == "damage":
            self.damage_events.append({kk: l.get(kk) for kk in ("seq", "tag", "amount", "isLocal", "gameMin",
                                                                  "wallMs")})

    def phases(self):
        return [("hello_and_map", self.phase_hello_and_map), ("x2_bench", self.phase_x2_bench),
                ("x1_motor", self.phase_x1_motor), ("x3_load", self.phase_x3_load), ("server", self.phase_server)]

    def aborted(self):
        if self.out.get("abort"):
            self.xs.note("phase %s skipped: %s" % (self.xs.cur_phase, self.out["abort"]))
            return True
        return False

    def frame_list(self):
        return [f for f, _ in self.frames]

    def latest(self):
        return self.frames[-1][0] if self.frames else {}

    def grade(self, name, verdict, observed, falsifier, samples=None, extra=None):
        ex = {"predicted": PREDICTIONS.get(name)}
        ex.update(extra or {})
        return self.xs.grade(name, verdict, observed, falsifier, extra=ex, samples=samples)

    # ---- phase 0: hello and the line
    def phase_hello_and_map(self):
        t0 = self.py_ms()
        self.wait_until(lambda: self.hello is not None, HELLO_TIMEOUT_S)
        self.out["hello_wait_ms"] = self.py_ms() - t0
        self.need_hello()
        self.out["hello"] = self.hello
        self.out["mode"] = self.hello.get("mode")
        if self.hello.get("modVersion") != MOD_VERSION:
            self.out["abort"] = "Lua %s: the probe mod did not load" % self.hello.get("modVersion")
            self.xs.note(self.out["abort"])
            return
        self.wait_until(lambda: self.bench_line is not None, ACK_TIMEOUT_S)
        self.out["bench_info"] = ({k: v for k, v in self.bench_line.items() if k not in ("kind", "tick")}
                                  if self.bench_line else None)
        self.wait_until(self.still, SETTLE_S)
        scan = self.scan_once(SCAN_R)
        me = self.world.me
        mx, my, mz = _num(me.get("x")), _num(me.get("y")), _num(me.get("z"))
        row = {"scan": scan, "me": {"x": mx, "y": my, "z": mz}}
        if mx is None or my is None:
            raise RuntimeError("no frame position: no line")
        z = int(math.floor(mz)) if mz is not None else 0
        got = choose_line(self.world.map, (mx, my), z)
        if got is None:
            ax, ay = mx, my
            row.update({"fallback": "pass 4 legs", "ax": ax, "ay": ay, "bx": ax + FALLBACK_DX, "by": ay,
                        "dir": "+x", "dist": 0.0, "candidates": 0})
            self.line = {"A": (ax, ay), "B": (ax + FALLBACK_DX, ay)}
            self.strip = strip_of(int(math.floor(ax)), int(math.floor(ay)), "+x", FALLBACK_DX + 1)
        else:
            row.update(got)
            self.line = {"A": (got["ax"] + 0.5, got["ay"] + 0.5), "B": (got["bx"] + 0.5, got["by"] + 0.5)}
            self.strip = strip_of(got["ax"], got["ay"], got["dir"], LINE_LEN)
        self.line_dir = row["dir"]
        (a0, a1), (b0, b1) = self.line["A"], self.line["B"]
        self.line["M"] = ((a0 + b0) / 2.0, (a1 + b1) / 2.0)
        row["targets"] = {k: list(v) for k, v in self.line.items()}
        row["strip_squares"] = len(self.strip)
        self.rd["line"] = row

    def scan_once(self, r):
        n0 = len(self.parts)
        seq = self.link.send("scan", str(r))
        row = {"r": r, "cmdSeq": seq, "sentPyMs": self.py_ms()}
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        row["ack"] = ack
        if ack is None:
            row["error"] = "no ack"
            return row
        mine = lambda: [l for l in self.parts[n0:] if l.get("seq", 0) > ack["seq"]]      # noqa: E731
        row["done"] = self.wait_until(lambda: any(l.get("done") for l in mine()), SCAN_TIMEOUT_S)
        got = mine()
        row["parts"] = len(got)
        row["declared"] = got[0].get("parts") if got else None
        row["map_squares"] = len(self.world.map)
        if not row["done"]:
            row["error"] = "no done part in %ss" % SCAN_TIMEOUT_S
        return row

    # ---- phase 1: the emit bench
    def phase_x2_bench(self):
        if self.aborted():
            return
        self.need_hello()
        bench = self.rd["bench"]
        rows = bench.setdefault("rows", [])
        for rep in range(BENCH_REPS):
            for arm, n in BENCH_ARMS + HELD_ARMS:
                rows.append(self.bench_row(arm, n, rep))
            self.sync_out()
            self.xs.persist()
        bench["summary"] = self.bench_summary(rows)

    def bench_row(self, arm, n, rep):
        r = self.xs.step("bench_%s_%d" % (arm, rep), "client", "bench.global", "PZA.bench.%s %d" % (arm, n))
        a = r.get("ack")
        row = {"arm": arm, "rep": rep, "n": n, "ms": None, "usPerCall": None, "error": None}
        if not isinstance(a, dict):
            row["error"] = "non-dict reply: %r" % (a,)
            return row
        row.update({"n": a.get("n", n), "ms": a.get("ms"), "usPerCall": a.get("usPerCall"), "error": a.get("error")})
        return row

    def bench_summary(self, rows):
        info = self.out.get("bench_info") or {}
        out = {}
        for arm, _ in BENCH_ARMS + HELD_ARMS:
            us = _median(r["usPerCall"] for r in rows if r["arm"] == arm and not r.get("error"))
            key = BENCH_BYTES_KEY.get(arm)
            b = S20_BYTES if arm == "openWrite20" else (_num(info.get(key)) if key else None)
            s = {"median_usPerCall": us, "bytes": b, "reps": sum(1 for r in rows if r["arm"] == arm
                                                                 and not r.get("error") and _num(r["usPerCall"]) is not None)}
            if arm in US_PER_KB_ARMS:
                s["us_per_kb"] = us / (b / 1024.0) if us is not None and b else None
            out[arm] = s
        return out

    # ---- legs
    def target(self, end):
        return self.line[end]

    def leg_frames(self, ack, end_seq, i0):
        after = ack["seq"] if isinstance(ack, dict) and _num(ack.get("seq")) is not None else None
        if after is None:
            return []
        return [f for f, _ in self.frames[i0:] if f["seq"] > after and (end_seq is None or f["seq"] <= end_seq)]

    def run_goal(self, goal, args, timeout_s, row):
        """Send, await the ack and the goal's end; fills row and returns (ack, i0)."""
        i0 = len(self.frames)
        row["sentPyMs"] = self.py_ms()
        seq = self.link.send(goal, args)
        row.update({"args": args, "cmdSeq": seq})
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        row["ack"] = ack
        if ack is None:
            row["error"] = "no ack"
            return ack, i0
        row["ackPyMs"] = self.py_ms()
        if not ack.get("ok"):
            row["error"] = "refused: %s" % ack.get("reason")
            return ack, i0
        if self.wait_until(lambda: seq in self.goal_end, timeout_s):
            row["goal"] = dict(self.goal_end[seq])
        else:
            row["goal"] = {"state": "timeout", "detail": "goal %d not finished in %ss" % (seq, timeout_s)}
            row["error"] = "timeout"
        row["donePyMs"] = self.py_ms()
        return ack, i0

    def read_leg(self, row, ack, i0, x0, y0):
        end_seq = (row.get("goal") or {}).get("seq")
        fr = self.leg_frames(ack, end_seq, i0)
        row["frames"] = len(fr)
        row["pace"] = pace(fr)
        row["endurance_slope"] = endurance_slope(fr)
        row["flags"] = flags(fr)
        fm = AP4.first_move(self.frames[i0:], ack, x0, y0)
        row["first_move"] = fm
        aw = _num((ack or {}).get("wallMs"))
        row["cmd_move_ms"] = fm["wallMs"] - aw if fm and aw is not None and _num(fm.get("wallMs")) is not None else None
        ew = _num((row.get("goal") or {}).get("wallMs"))
        row["wall_ms"] = ew - aw if ew is not None and aw is not None else None
        return fr

    def one_leg(self, arm, end, goal_arm=None, leg=None):
        """One `goto` to the line's `end` ("A" or "B") with the motor arm `goal_arm` (default `arm`; `walk` is sent
        bare); `arm` is the row's label."""
        goal_arm = goal_arm or arm
        settled = self.wait_until(self.still, SETTLE_S)
        me = self.world.me
        x0, y0 = _num(me.get("x")), _num(me.get("y"))
        tx, ty = self.target(end)
        row = {"arm": arm, "leg": leg, "from": {"x": x0, "y": y0}, "to": {"end": end, "x": tx, "y": ty},
               "settled": settled, "cmdSeq": None, "ack": None, "goal": None, "frames": 0, "pace": None,
               "endurance_slope": None, "flags": None, "first_move": None, "cmd_move_ms": None, "error": None}
        args = "%s %s" % (str(tx), str(ty)) + ("" if goal_arm == "walk" else " %s" % goal_arm)
        t0 = self.py_ms()
        ack, i0 = self.run_goal("goto", args, GOAL_TIMEOUT_S, row)
        if row["error"] is None or row["error"] == "timeout":
            self.read_leg(row, ack, i0, x0, y0)
        row["legPyMs"] = self.py_ms() - t0
        if (row.get("goal") or {}).get("state") == "done":
            self.at_end = end
        return row

    def next_end(self):
        return "B" if self.at_end == "A" else "A"

    def autowalk_leg(self, i, dx, dy, s, arm, correction_deg=0.0):
        """One `autowalk` leg: its (dx, dy) written along the line's axis (axis_vector) as the wanted world vector,
        sent as input_vector's (ix, iy) with the calibration's correction; graded against the world vector. A leg
        whose frames leave the checked strip is voided (its readings kept, its samples out of every grade)."""
        settled = self.wait_until(self.still, SETTLE_S)
        me = self.world.me
        x0, y0 = _num(me.get("x")), _num(me.get("y"))
        vx, vy = axis_vector(self.line_dir, dx, dy)
        ix, iy = input_vector(vx, vy, correction_deg)
        row = {"arm": arm, "leg": i, "kind": "autowalk", "dx": dx, "dy": dy, "vx": vx, "vy": vy, "ix": ix, "iy": iy,
               "correction_deg": correction_deg, "heading_signed_deg": None, "seconds": s,
               "from": {"x": x0, "y": y0}, "settled": settled, "cmdSeq": None, "ack": None, "goal": None,
               "frames": 0, "pace": None, "endurance_slope": None, "flags": None, "first_move": None,
               "cmd_move_ms": None, "heading_error_deg": None, "displacement": None, "voided": None,
               "off_strip_frames": 0, "error": None}
        args = "%s %s %s" % (_arg(ix), _arg(iy), s) + ("" if arm == "walk" else " %s" % arm)
        t0 = self.py_ms()
        ack, i0 = self.run_goal("autowalk", args, s + AUTOWALK_PAD_S, row)
        if row["error"] is None or row["error"] == "timeout":
            fr = self.read_leg(row, ack, i0, x0, y0)
            row["heading_error_deg"] = heading_error_deg(fr, vx, vy)
            row["heading_signed_deg"] = heading_signed_deg(fr, vx, vy)
            row["displacement"] = displacement(fr)
            aw = [f for f in fr if _motor(f).get("autoWalk") is True]
            row["autoWalk_frames"] = len(aw)       # the frames the walk ran on (not before it latched or after its end)
            row["autoWalk_updForceRun"] = sum(1 for f in aw if _motor(f).get("updForceRun") is True)
            off = off_strip(fr, self.strip)
            row["off_strip_frames"] = len(off)
            if off:
                row["voided"] = "left the strip"
                row["off_strip_first"] = {k: off[0].get(k) for k in ("seq", "x", "y")}
        row["legPyMs"] = self.py_ms() - t0
        return row

    def pace_of(self, arm):
        return _median(r["pace"] for r in self.mt["legs"] + self.mt["toggle"] if r["arm"] == arm)

    def x1_late(self):
        """The X1 deadline: past X1_DEADLINE_S of the loop wall (the Xs clock), X1 starts no new leg."""
        return self.xs.wall() > X1_DEADLINE_S

    @staticmethod
    def skipped_row(arm, leg, kind="goto"):
        return {"arm": arm, "leg": leg, "kind": kind, "skipped": "x1 deadline", "frames": 0, "pace": None,
                "endurance_slope": None, "flags": None, "heading_error_deg": None, "displacement": None,
                "voided": None, "error": None}

    def x1_goto(self, arm, end=None, goal_arm=None, leg=None):
        """one_leg under the X1 deadline (a skipped row once it has passed); end None is the end not stood at."""
        if self.x1_late():
            return self.skipped_row(arm, leg)
        return self.one_leg(arm, end or self.next_end(), goal_arm=goal_arm, leg=leg)

    def nearer_end(self):
        me = self.world.me
        x, y = _num(me.get("x")), _num(me.get("y"))
        if x is None or y is None:
            return self.at_end
        da = math.hypot(x - self.line["A"][0], y - self.line["A"][1])
        db = math.hypot(x - self.line["B"][0], y - self.line["B"][1])
        return "A" if da <= db else "B"

    # ---- phase 2: the motor arms
    def phase_x1_motor(self):
        if self.aborted():
            return
        self.need_hello()
        if self.line is None:
            raise RuntimeError("no line: hello_and_map did not choose one")
        self.rd["motor"] = self.mt
        try:
            self.mt["approach"] = self.x1_goto("approach", "A", goal_arm="walk")
            self.at_end = "A"
            self.mt["rate_on"] = self.set_rate(X1_RATE_HZ)
            for arm in MOTOR_ARMS:
                for leg in range(LEGS_PER_ARM):
                    self.mt["legs"].append(self.x1_goto(arm, leg=leg))
                    self.sync_out()
                self.xs.persist()
            corr = self.calibrate()
            for i, (dx, dy, s, arm) in enumerate(AUTOWALK_LEGS):
                # re-centred before every leg: each starts within the goto's 1.0 done radius of M
                self.mt["centre"].append(self.x1_goto("centre", "M", goal_arm="walk", leg=i))
                row = (self.skipped_row(arm, i, "autowalk") if self.x1_late()
                       else self.autowalk_leg(i, dx, dy, s, arm, corr))
                self.mt["autowalk"].append(row)
                self.sync_out()
            self.xs.persist()
            self.at_end = self.nearer_end()          # the autowalk legs leave the character anywhere on the strip
            fr, wk = self.pace_of("forcerun"), self.pace_of("walk")
            if fr is not None and wk is not None and fr < TOGGLE_IF_BELOW * wk:
                for leg in range(TOGGLE_LEGS):
                    self.mt["toggle"].append(self.x1_goto("toggle", leg=leg))
                    self.sync_out()
            else:
                self.mt["toggle_skipped"] = {"forcerun": fr, "walk": wk}
            self.mt["return"] = self.x1_goto("return", "A", goal_arm="walk")
        finally:
            self.mt["paces"] = {arm: self.pace_of(arm) for arm in MOTOR_ARMS + ["toggle"]}
            self.mt["deadline_skipped"] = sum(1 for r in self.x1_rows() if r.get("skipped"))
            self.grade_x1()
            self.mt["rate_back"] = self.set_rate(X1_RATE_BACK_HZ)

    def set_rate(self, hz):
        """The `rate <hz>` config command, its ack awaited; a budget stop while awaiting it is recorded, never
        raised (it runs in X1's finally)."""
        row = {"rate": hz, "sentPyMs": self.py_ms()}
        row["cmdSeq"] = self.link.send("rate", str(hz))
        try:
            row["ack"] = self.await_ack(row["cmdSeq"], ACK_TIMEOUT_S)
        except X.Budget as e:
            row["ack"], row["error"] = None, "budget: %s" % e
            return row
        if row["ack"] is None:
            row["error"] = "no ack"
        return row

    def calibrate(self):
        """The ungraded calibration leg (a centre goto, then CALIBRATE_LEG through input_vector with no correction):
        its signed heading error, snapped by correction_of, is the correction every later autowalk vector takes."""
        self.mt["centre"].append(self.x1_goto("centre", "M", goal_arm="walk", leg="calibration"))
        dx, dy, s, arm = CALIBRATE_LEG
        if self.x1_late():
            row = self.skipped_row(arm, "calibration", "autowalk")
        else:
            row = self.autowalk_leg("calibration", dx, dy, s, arm)
        self.mt["autowalk_calibration"] = row
        corr = correction_of(row.get("heading_signed_deg"), row.get("displacement"))
        self.mt["autowalk_correction_deg"] = corr
        raw = correction_of(row.get("heading_signed_deg"))
        if raw != corr:
            self.mt["autowalk_correction_note"] = "guarded: a %s deg snap or a %s-tile calibration is not applied" % (
                raw, row.get("displacement"))
        self.sync_out()
        return corr

    def x1_rows(self):
        one = [self.mt.get(k) for k in ("approach", "autowalk_calibration", "return") if self.mt.get(k)]
        return one + self.mt["centre"] + self.mt["legs"] + self.mt["autowalk"] + self.mt["toggle"]

    def grade_x1(self):
        legs = self.mt["legs"] + self.mt["toggle"]
        paced = lambda arm: [r["pace"] for r in legs if r["arm"] == arm and r["pace"] is not None]      # noqa: E731
        wk, fr, sr = self.pace_of("walk"), self.pace_of("forcerun"), self.pace_of("setrun")

        def ratio_grade(name, val, samples, falsifier, test, extra_obs=None):
            obs = {"pace": val, "walk": wk, "ratio": val / wk if val is not None and wk else None}
            obs.update(extra_obs or {})
            if val is None or not wk:
                return self.grade(name, "unmeasured", obs, falsifier, samples=samples)
            return self.grade(name, "as_predicted" if test(val) else "falsified", obs, falsifier, samples=samples)

        ratio_grade("x1_forcerun_runs", fr, paced("forcerun") + paced("walk"),
                    "forcerun's median pace below %s x walk's" % RUN_RATIO, lambda v: v >= RUN_RATIO * wk)
        ratio_grade("x1_setrun_walks", sr, paced("setrun") + paced("walk"),
                    "setrun's median pace outside %s of walk's" % SETRUN_TOL,
                    lambda v: abs(v - wk) <= SETRUN_TOL * wk)
        every = [r for r in self.mt["autowalk"] if not r.get("skipped")]
        voided = sum(1 for r in every if r.get("voided"))
        aw = [r for r in every if not r.get("voided")]          # a voided leg is out of every grade's samples
        awr = [r["pace"] for r in aw if r["arm"] == "forcerun" and r["pace"] is not None]
        ratio_grade("x1_autowalk_runs", _median(awr), awr + paced("walk"),
                    "the autowalk forcerun legs' median pace below %s x walk's" % RUN_RATIO,
                    lambda v: v >= RUN_RATIO * wk, {"voided_legs": voided})
        hd = [r["heading_error_deg"] for r in aw if r["heading_error_deg"] is not None]
        self.grade("x1_autowalk_heads", "as_predicted" if all(h <= HEADING_MAX_DEG for h in hd) else "falsified",
                   {"heading_error_deg": [r["heading_error_deg"] for r in every], "max": max(hd) if hd else None,
                    "unread_legs": len(aw) - len(hd), "voided_legs": voided},
                   "an autowalk leg's heading error above %s deg" % HEADING_MAX_DEG, samples=hd)
        ft = self.pace_of("forcerun_tick")
        self.grade("x1_forcerun_tick", "recorded",
                   {"pace": ft, "walk": wk, "ratio": ft / wk if ft is not None and wk else None,
                    "legs": len(paced("forcerun_tick"))}, "none: read either way")
        once = [r for r in aw if r["arm"] == "once" and r.get("autoWalk_frames")]
        if once:
            o = once[0]
            frac = o["autoWalk_updForceRun"] / o["autoWalk_frames"]
            self.grade("x1_once_holds", "as_predicted" if frac >= ONCE_HOLD_FRAC else "falsified",
                       {"updForceRun": o["autoWalk_updForceRun"], "frames": o["autoWalk_frames"], "fraction": frac,
                        "leg_frames": (o.get("flags") or {}).get("frames")},
                       "updForceRun on fewer than %s of the once leg's autoWalk frames" % ONCE_HOLD_FRAC, samples=once)
        else:
            self.grade("x1_once_holds", "unmeasured", {"fraction": None, "voided_legs": voided},
                       "updForceRun on fewer than %s of the once leg's frames" % ONCE_HOLD_FRAC, samples=[])
        sl = lambda arm: [r["endurance_slope"] for r in legs if r["arm"] == arm      # noqa: E731
                          and r["endurance_slope"] is not None]
        fs, ws = _median(sl("forcerun")), _median(sl("walk"))
        obs = {"forcerun": fs, "walk": ws}
        if fs is None or ws is None:
            self.grade("x1_endurance", "unmeasured", obs, "forcerun's slope not below walk's", samples=[])
        else:
            self.grade("x1_endurance", "as_predicted" if fs < ws else "falsified", obs,
                       "forcerun's slope not below walk's", samples=sl("forcerun") + sl("walk"))

    # ---- phase 3: the heavy load
    def health_floored(self):
        return any(_num(f.get("health")) is not None and f["health"] <= HEALTH_FLOOR
                   for f, _ in self.frames if self.x3_seq0 is not None and f["seq"] > self.x3_seq0)

    def timed_walk(self, arm, seconds, rows, stop_on_floor):
        lo = self.last_seq
        t_first = None
        for _ in range(WALK_MAX_LEGS):
            if t_first is not None and self.clock() - t_first >= seconds:
                break
            if stop_on_floor and self.health_floored():
                self.ld.setdefault("floor_reached", {"arm": arm, "seq": self.last_seq})
                break
            t_send = self.clock()
            row = self.one_leg(arm, self.next_end(), goal_arm="walk", leg=len(rows))
            rows.append(row)
            if t_first is None:
                t_first = row["ackPyMs"] / 1000.0 if row.get("ackPyMs") is not None else t_send
            self.sync_out()
        self.windows[arm] = (lo, self.last_seq)

    def phase_x3_load(self):
        if self.aborted():
            return
        self.need_hello()
        if self.line is None:
            raise RuntimeError("no line: hello_and_map did not choose one")
        ld = self.ld
        self.rd["load"] = ld
        self.x3_seq0 = self.last_seq
        try:
            ld["server_arm"] = self.xs.keep(self.xs.step("damage_server_arm", "server", "fall.probe", USER))
            if ld["server_arm"].get("hooked") is not True:
                self.xs.note("fall.probe: the server listener is not hooked")
            ld["client_arm"] = self.xs.keep(self.xs.step("damage_client_arm", "client", "event.watch",
                                                         "OnPlayerGetDamage"))
            f = self.latest()
            ld["before"] = {"weight": f.get("weight"), "maxWeight": f.get("maxWeight"), "level": level_of(f),
                            "health": f.get("health"), "seq": f.get("seq")}
            self.load_up()
            ld["walk_loaded"] = []
            self.timed_walk("walk_loaded", WALK_S, ld["walk_loaded"], True)
            lo = self.last_seq
            t_end = self.clock() + STILL_S
            self.wait_until(lambda: self.clock() >= t_end, STILL_S + 1.0)
            self.windows["still"] = (lo, self.last_seq)
            self.unload()
            ld["walk_level2"] = []
            self.timed_walk("walk_level2", WALK2_S, ld["walk_level2"], False)
            ld["server_read"] = self.xs.keep(self.xs.step("damage_server_read", "server", "fall.probe", USER))
            ld["client_read"] = self.xs.keep(self.xs.step("damage_client_read", "client", "event.watch",
                                                          "OnPlayerGetDamage read"))
            self.wait_until(lambda: False, 2 * POLL_S)        # a last pump for the damage events
        finally:
            self.fold_load()
            self.grade_x3()

    def load_up(self):
        """Up to LOAD_MAX_ADDS RCON `additem` planks (the route that reaches the client), each followed by a wait of
        up to LOAD_SETTLE_S for a frame whose weight rose above the previous frame's; the first add whose frame weight
        did not rise stops the load (load_stalled_at), and the X3 grades then read unmeasured on their samples."""
        ld = self.ld
        adds = ld["adds"] = []
        for i in range(1, LOAD_MAX_ADDS + 1):
            prev = _num(self.latest().get("weight"))
            rep = self.xs.rcon('additem "%s" "%s" 1' % (USER, LOAD_ITEM), "add_%d" % i)
            moved = self.wait_until(lambda: _num(self.latest().get("weight")) is not None and (
                prev is None or self.latest()["weight"] > prev), LOAD_SETTLE_S)
            f = self.latest()
            fw, fm, lv = _num(f.get("weight")), _num(f.get("maxWeight")), level_of(f)
            adds.append({"i": i, "rcon": rep, "frame_weight": fw, "frame_maxWeight": fm, "level": lv,
                         "frame_seq": f.get("seq"), "weight_rose": moved})
            if not moved:
                ld["load_stalled_at"] = i
                ld["load_stalled_reply"] = rep
                self.xs.note("load stalled at add %d: the frame weight did not rise in %ss" % (i, LOAD_SETTLE_S))
                break
            self.planks += 1
            if lv is not None and lv >= HEAVY_LEVEL:
                ld["level3_at_ratio"] = fw / fm if fw is not None and fm else None
                ld["level3_at_add"] = i
                break
        if "level3_at_add" not in ld:
            ld["level_reached"] = adds[-1]["level"] if adds else None
        ld["planks_added"] = self.planks

    def unload(self):
        ld = self.ld
        f = self.latest()
        fw, fm = _num(f.get("weight")), _num(f.get("maxWeight"))
        k, ratio, why = unload_count(fw, fm, self.planks)
        row = ld["drop"] = {"k": k, "predicted_ratio": ratio, "rule": why, "weight": fw, "maxWeight": fm,
                            "planks": self.planks, "cmdSeq": None, "ack": None, "goal": None, "error": None}
        if self.planks < 1:
            row["error"] = "no plank added: nothing to drop"
            return
        lo = self.last_seq
        self.run_goal("drop", "%s %d" % (LOAD_ITEM, k), DROP_TIMEOUT_S, row)
        self.wait_until(self.still, SETTLE_S)
        g = self.latest()
        row["after"] = {"weight": g.get("weight"), "maxWeight": g.get("maxWeight"), "level": level_of(g),
                        "seq": g.get("seq")}
        self.windows["drop"] = (lo, self.last_seq)

    def fold_load(self):
        if self.x3_seq0 is None:
            return
        tr = [trace_row(f) for f, _ in self.frames if f["seq"] > self.x3_seq0]
        self.ld["trace"] = tr
        self.ld["windows"] = {k: list(v) for k, v in self.windows.items()}
        self.ld["drops"] = drops_of(tr, self.windows)
        self.ld["damage_events"] = list(self.damage_events)

    def grade_ev(self, name, verdict, observed, falsifier, samples):
        """An X3 grade resting on its evidence: no samples reads unmeasured, whatever the verdict would be."""
        return self.grade(name, verdict if samples else "unmeasured", observed, falsifier, samples=samples)

    def grade_x3(self):
        ld = self.ld
        drops = ld.get("drops") or []
        tr = ld.get("trace") or []
        read = [d for d in drops if d["level"] is not None]          # an unread level is counted, never graded
        low = [d for d in read if d["level"] < HEAVY_LEVEL]
        self.grade_ev("x3_drops_at_level3_only", "falsified" if low else "as_predicted",
                      {"drops": len(drops), "below_level3": len(low), "unread_level": len(drops) - len(read),
                       "levels": sorted({str(d["level"]) for d in drops})},
                      "a drop at HEAVY_LOAD <= 2", read)
        floor_frames = [r for r in tr if _num(r.get("health")) is not None and r["health"] <= HEALTH_FLOOR]
        under = [d for d in drops if d["from"] <= HEALTH_FLOOR]
        self.grade_ev("x3_floor_75", "falsified" if under else "as_predicted",
                      {"drops": len(drops), "from_at_or_below_floor": len(under), "frames_at_or_below_floor":
                       len(floor_frames), "min_health": min((_num(r.get("health")) for r in tr
                                                            if _num(r.get("health")) is not None), default=None)},
                      "a drop from a health <= %s" % HEALTH_FLOOR, floor_frames)
        still = [d for d in drops if d["window"] == "still"]
        self.grade("x3_drops_while_still", "recorded", {"drops": len(still), "fall": sum(d["fall"] for d in still)},
                   "none: recorded")
        l2 = [d for d in drops if d["window"] == "walk_level2"]
        lo, hi = self.windows.get("walk_level2", (None, None))
        l2_frames = [r for r in tr if hi is not None and lo < r["seq"] <= hi and r.get("level") == 2]
        self.grade_ev("x3_level2_no_drop", "falsified" if l2 else "as_predicted",
                      {"drops": len(l2), "level2_frames": len(l2_frames),
                       "drop_after": (ld.get("drop") or {}).get("after")},
                      "a drop while walking at level 2", l2_frames)
        sr = ld.get("server_read") or {}
        counts = sr.get("counts") if isinstance(sr.get("counts"), dict) else None
        heavy = {k: v for k, v in (counts or {}).items() if "heavyload" in str(k).lower()}
        hit = any(_num(v) is not None and v > 0 for v in heavy.values())
        self.grade_ev("x3_server_hears_heavyload", "as_predicted" if hit else "falsified",
                      {"counts": counts, "hooked": sr.get("hooked"), "drops": len(drops)},
                      "no HEAVYLOAD tag counted above 0", [1] if counts is not None and drops else [])
        cr = ld.get("client_read") or {}
        n_watch = _num(cr.get("count"))
        n_ev = sum(1 for e in ld.get("damage_events") or [] if "heavyload" in str(e.get("tag")).lower())
        heard = (n_watch or 0) > 0 or n_ev > 0
        self.grade_ev("x3_client_hears_heavyload", "falsified" if heard else "as_predicted",
                      {"event_watch_count": n_watch, "damage_events_heavyload": n_ev,
                       "damage_events": len(ld.get("damage_events") or []), "hooked": cr.get("hooked"),
                       "drops": len(drops)},
                      "the client hears it (> 0)", drops)
        r = _num(ld.get("level3_at_ratio"))
        self.grade_ev("x3_level3_at_ratio",
                      "as_predicted" if r is not None and LEVEL3_RATIO <= r < LEVEL4_RATIO else "falsified",
                      {"level3_at_ratio": r, "level_reached": ld.get("level_reached"),
                       "load_stalled_at": ld.get("load_stalled_at")},
                      "level 3 at a ratio outside [%s, %s)" % (LEVEL3_RATIO, LEVEL4_RATIO),
                      [1] if "level3_at_add" in ld and r is not None else [])

    # ---- phase 4: server
    def phase_server(self):
        if self.aborted():
            return
        t0 = self.py_ms()
        r = self.bus_stats(self.xs, USER)
        self.rd["server"] = [{"i": 0, "startPyMs": t0, "rttMs": self.py_ms() - t0, "ack": r.get("ack"),
                              "wallMs": r.get("wallMs")}]

    def sync_out(self):
        super().sync_out()
        self.out["frames_n"] = len(self.frames)
        self.out["damage_events_n"] = len(self.damage_events)


def summary(out):
    """What main prints: the median paces per arm, the bench medians and the X3 verdicts."""
    rd = out.get("readings") or {}
    v = out.get("verdicts") or {}
    bench = (rd.get("bench") or {}).get("summary") or {}
    return {"paces": (rd.get("motor") or {}).get("paces"),
            "bench_median_us": {k: s.get("median_usPerCall") for k, s in bench.items()},
            "x1": {k: r.get("verdict") for k, r in v.items() if k.startswith("x1_")},
            "x3": {k: r.get("verdict") for k, r in v.items() if k.startswith("x3_")}}


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
              ask=ask, budget_s=budget_s, user=USER, predictions=PREDICTIONS)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS, "predictions": PREDICTIONS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    AP.memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    probe = None
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=AP.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            probe = Probe(xs, DL.link_for(clients, USER))
            probe.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = AP.client_errors([(getattr(c, "username", "?"), c.console) for c in every])
            out["logs"] = {"patterns": {"client_error": CLIENT_ERR_RX}, "clients": found}
            out["client_lua_errors"] = n

        if probe is not None:
            probe.sync_out()
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    s = summary(out)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "median_pace_per_arm": s["paces"],
                      "bench_median_usPerCall": s["bench_median_us"], "x1_verdicts": s["x1"],
                      "x3_verdicts": s["x3"], "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
