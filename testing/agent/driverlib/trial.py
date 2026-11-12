"""The trial (Plan 31 Task 6, ruling P31-T): one short live boot of a planner variant on a fixture, the instrument of
Plan 31's Explore phase, driven by `testing/agent/drivers/x_trial.py`. A trial is not evidence (CLAUDE.md section 5,
"Trials"): its run stays in `testing/runs/`, nothing is copied into `testing/artifacts/`, and `tools/trial_score.py`
reads the run folder into `testing/trials/trials.md`. The machine-safety rules bind every trial boot all the same.

THE ARGUMENTS (`parse_argv`, `flags`): `--variant <name>` and `--fixture <name>` (both required), `--minutes N` (the
loop's wall minutes, a number > 0 and at most MAX_MINUTES, default DEFAULT_MINUTES), `--no-llm` (bare: the scripted
goal source, no model and no probe), `--goals <scripted|hold>` (default `scripted`; `hold` is the arena's goal source,
`HoldSource`, below, and is refused without `--no-llm`: it holds the square, no model), `--waves <plan>` (a
WAVE_PLANS name, default DEFAULT_WAVES), `--teleport X,Y` (two numbers), `--make-fixture <name>` (a new fixture snapshotted off this run), `--detached` (bare: it changes only
the refusal below); each once. `--make-fixture` refuses a wave plan that spawns (the spawned zombies would be saved
into the fixture) and a name equal to `--fixture`. A trial whose wall bound passes FOREGROUND_CAP_S is refused
without `--detached` (CLAUDE.md section 5, Waiting: past the ten-minute cap the controller launches it detached after
Angus approves). Anything else is refused in one line naming the driver's file.

THE WALL BOUND (`wall_bound`, printed by `bound_line` as the boot's first line, before the pre-boot): PREBOOT_S, the
budget (BUDGET_EXTRA_S plus the loop's minutes, from the memory gate's end), the closing Stop's settle, the poll
worker's join, the wave join, the bounded teardown (75 s), the LLM worker's join and, under --make-fixture, the
snapshot's timeout. The default five minutes with the model is 568 s, under the 570 s cap.

THE BOOT (`boot_and_run`, a copy of `day.boot_and_run` with three edits): no `copy_run` (nothing is auto-copied into
`testing/artifacts/`), no `next_steps` (no chain), no grade (the scorecard reads the run). The pre-boot checks
(`preboot`): the profile on disk, `pzt doctor` clean, the profile's layout lint, the host's free memory read
(MIN_FREE_GB through `xlib.free_gb`: no floor since Angus's ruling of 2026-11-08, a reading that cannot be taken refuses), no game Java process (`pzt.doctor`'s own reader: the doctor only warns on one),
the fixture's record and cache (`fx.load`), the variant buildable (`variant_check`: Survive's `control` keyword and
the variant loader), a `--make-fixture` name not taken, and the `claude -p` probe (`driverlib.probe`) only without
`--no-llm`; every check's result in out["preboot"], a failure printed and exit 1 before anything starts. Then the
memory gate (one read, no wait: a refusal leaves no run folder), the run dir `testing/runs/x_trial-<variant>-<stamp>/`
(`new_run_dir`, PZT_RUNS honoured), `trial.json` written at its root (below), the boot, the session, the teardown,
the LLM worker's join, trial.json's end state, `finished`, the persist; with `--make-fixture`, `pzt snapshot
--from-run <run> --name <name> --parent <fixture> --session 1` last (`make_fixture`: only after a clean server stop,
a session that stopped at its cap, the teleport read by the frames and the character ended at its square unhurt;
the planner idle throughout, so nothing walks it off). A run folder whose artifact never reads `finished` is not a
run (the scorecard's rule).

TRIAL.JSON (TRIAL_KEYS): variant; switches (every name of survive.py's `T<n>_SWITCHES` tuples, then EXTRA_SWITCHES,
read off the built planner, as the variant left them; None until the planner is built, the file rewritten then);
commit (the stamp's `commit`, else `git rev-parse HEAD`); stamp (the content of TRIAL_STAMP.json at the tree's root, written by
`tools/trial_snapshot.py`, else None); dirty and diff_sha256 (the stamp's, else `git status --porcelain` and the
sha256 of `git diff HEAD` over SESSION_PATHS with every untracked file's block appended, the whole saved beside as
trial.diff); untracked (those files' paths; None from a stamp); provenance ("stamp" or "git"); fixture; minutes;
waves (the plan's name) and wave_plan (its period and spawns); no_llm; goals (the goal source's name); teleport
([x, y] or None); make_fixture; detached; wall_bound_s; argv; started_at (local ISO seconds); end_pos ([x, y, z]) and end_health (the last kept
frame's, written after the teardown; None before). The same dict is out["trial"].

THE HOLD (`HoldSource`, `--goals hold`, Plan 31 Task 12's pre-step): the arena's goal source. Task 10's first arena
trial (`x_trial-ladder-20261105-201433`) showed the scripted source's `ExploreToward` legs walking the character up to
33 tiles off the arena square between the waves, so three of six waves spawned where nobody was. The hold answers a
goal request with `Rest(HOLD_REST_S)` (never a `LootBuilding`, `Shelter` or `Stock`), a fresh one whenever one ends:
a `Rest` sends nothing, so the goal layer never moves the character, and the quiet is filled with standing where it
stands. The one other answer is the scan in place (Plan 31 Task 12's loop fix): the first request on each scan place
(`place_of`'s SCAN_R grid off the view's pos) is `ExploreToward` to the character's own square, which sends the place's
`Scan(SCAN_R)` and ends `arrived` at once (ARRIVE_R), never a walk off the square. The symptom that drove it: trial 1's
first boot (`x_trial-ladder-20261105-214209`) held Rest only, no scan was ever sent, the map stayed empty, and the
ladder's engage (`engage._engageable`: an idle zombie needs a clear line or a square in the player's bounded flood,
both read off the map) marked each wave's idle zombie `unsought`: six zombies stood idle 7 to 9 tiles east and the
character never fought. The scripted source scans as its first act, so the hold now gives every arm the same map.
The planner's instincts above the goal (the threat branch, the variant) still take any zombie that comes. `Rest`
carries no square, so the hold cannot walk the character back to the square it started on; the square is noted
(`HoldSource.square`, the first pos a view reads) for the record and the tests, and a fight that moves the character
leaves it where the fight ended.

THE SESSION (`TrialChain`, day.Chain with two hooks more): the planner is `Survive(..., source=..., control=<the
variant>)`, the scripted goal source under `--no-llm`, else the LLMSource over it (goals.log beside decision.log, the
`llm` record as f_goals_16.py's); the loop's cap DAY_CAP_S = 60 x minutes and the wall budget that plus
BUDGET_EXTRA_S. The teleport (`teleport`) is sent over RCON at the loop phase's start, before the loop: TELEPORT_CMD,
then the transport pumped until a frame reads within TELEPORT_NEAR of the square or TELEPORT_SETTLE_S;
out["loop"]["trial"]["teleport"] {cmd, ack, arrived, waitS, pos}. The waves (`Waves`) run on their own thread on the
session's clock, started at the loop's first frame and stopped at the loop's stop (before the closing Stop's settle),
never on the planner's tick: each wave sends CREATEHORDE2_CMD per spawn at the square of the character's last frame
position plus the spawn's distance at its bearing (`wave_square`), on the character's floor;
out["loop"]["trial"]["waves"] its rows. The confirmation (Plan 31 Task 12's loop fix, corrected in Task 14's
pre-step): WAVE_CONFIRM_S after a spawn's send the frames must list as many zombie ids first sighted after the send, at
a square within WAVE_CONFIRM_R tiles of the spawn's square, as the spawn's count (`TrialChain.first_seen`: every id any
frame listed, with the position of its first listing; a natural walker first seen anywhere else, or before the send,
confirms nothing: round one's re-send confirmed on any new id); a spawn short of them re-sends its missing count once,
at its own distance and bearing off the character's last frame (rows `resend_of`; round one's re-send repeated the
plan's first N spawns, whichever wave had gone missing), and the confirmations are out["loop"]["trial"]["waves"]
["confirm"] (one per send of a spawn: wave, spawn, resend, need, listed_ids, t, resent). Per wave
out["loop"]["trial"]["waves"]["by_wave"] counts {wave, sent (zombies the wave first sent), resent, listed_ids (the ids
confirmed for it), confirmed (listed at least sent)}, and "server_spawns" the "Spawning" lines of the server's
`server-stdout.log` read after the teardown (`server_spawns`; None without the log), the spawns the server logged against
the ids the frames listed. The symptom that drove the confirmation: the server logged every createhorde2 spawn, but the
frames never listed three of six (Task 10's `x_trial-ladder-20261105-201433`, waves 1-3) and three of six again in trial
1 (`x_trial-ladder-20261105-215332`, waves 1, 2 and 4: ids 11981, 11982 and 11984 never listed), so a trial fought half
its plan; and the round-one correction's own: trial 5's server log held 11 "Spawning" lines against 8 planned, three
allocated ids never listed by a frame, the natural walkers' ids having confirmed the sends.

THE RCON FORMS (TELEPORT_CMD, CREATEHORDE2_CMD) are read off the jar at 42.21 by the scoping read (TeleportToCommand's
"Teleport user" form; CreateHorde2Command's -x -y -z -count -radius) and are unconfirmed until the first smoke boot
(Plan 31 Task 10); each lives in one constant so a correction is one edit.
"""
import datetime
import hashlib
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from agent.base.planner import llm as L
from agent.base.planner import survive as SV
from agent.base.planner.goals import REST_S, ExploreToward, Rest, ScriptedSource
from agent.base.planner.policies import SCAN_R
from agent.base.planner.survive import Survive
from agent.driverlib import chain as CH
from agent.driverlib import day as DY
from agent.driverlib import probe as PR
from agent.driverlib import session as DS
from pzt import fixture as fx

import x49b_lib as B                                 # noqa: E402 - bounded_teardown's waits (on sys.path by session.py)

DL, X = DS.DL, DS.X
USER = DY.USER
DEFAULT_MINUTES = 5
MAX_MINUTES = 60                     # a trial is short; a longer reading is an evidence session's
# the boot and the kit beyond the loop's own minutes, from the memory gate's end (F15: the loop began 91 s after the
# launch, the pre-boot about 10 s of it): with it the default five minutes fits the foreground cap (wall_bound); a
# slower boot ends the loop early on the budget, named in out["stop"]
BUDGET_EXTRA_S = 110.0
MIN_FREE_GB = DS.DEFAULTS["MIN_FREE_GB"]     # the pre-boot floor: 0.0, no floor (CLAUDE.md section 5, Angus 2026-11-08)
TRIAL_JSON = "trial.json"
TRIAL_DIFF = "trial.diff"
STAMP = "TRIAL_STAMP.json"           # tools/trial_snapshot.py's stamp at the extracted tree's root
GOALS_LOG = "goals.log"
LLM_JOIN_S = L.LLM_TIMEOUT_S + 5.0   # the worker's join after the teardown (f_goals_16.py's)
MODEL = L.model_of(L.DEFAULT_CLI)
SESSION_PATHS = ("testing/agent", "testing/PZAgent", "testing/PZTestKit", "testing/pzt", "testing/experiments")
SWITCH_RX = re.compile(r"^T(\d+)_SWITCHES$")
# the instance switches outside every T<n>_SWITCHES tuple that a trial records after them (Plan 31 Task 12): the Dress
# maneuver (Task 8), on by default since Plan 31 Task 15a (so Task 12's ladder-arm override, 62776c14, is gone)
EXTRA_SWITCHES = ("DRESS_MANEUVER",)
TRIAL_KEYS = ("variant", "switches", "commit", "stamp", "dirty", "diff_sha256", "untracked", "provenance", "fixture",
              "minutes", "waves", "wave_plan", "no_llm", "goals", "teleport", "make_fixture", "detached", "wall_bound_s",
              "argv", "started_at", "end_pos", "end_health")

# ---------------------------------------------------------------- the wall-time bound (CLAUDE.md section 5, Waiting)
FOREGROUND_CAP_S = 570.0             # a foreground call's bound: the ten-minute cap with 30 s to spare
PREBOOT_S = 15.0                     # the doctor and the probe (F15's pre-boot: about 10 s, the probe 3.2 s)
TEARDOWN_S = float(B.TEARDOWN_QUIT_S + B.TEARDOWN_STOP_S)     # bounded_teardown's client quit and server stop, 75 s
POLLS_JOIN_S = max(DS.STEP_TIMEOUT_S, DS.DEFAULTS["SERVER_TIMEOUT_S"]) + 5.0   # Session.polls_join_s (Xs's ping 5 s)

# ---------------------------------------------------------------- the arguments
VALUED = ("--variant", "--fixture", "--minutes", "--waves", "--teleport", "--make-fixture", "--goals")
BARE = ("--no-llm", "--detached")
REQUIRED = ("--variant", "--fixture")
NAME_RX = re.compile(r"^[a-z][a-z0-9_]*$")                  # a variant: a planner package's name
FIXTURE_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")    # a fixture folder's name
TELEPORT_RX = re.compile(r"^(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$")

# ---------------------------------------------------------------- RCON (read off the jar; unconfirmed until boot 1)
# TeleportToCommand's "Teleport user" form: a username, then x,y,z; its role check is skipped over RCON (no connection)
TELEPORT_CMD = 'teleportto "{user}" {x},{y},{z}'
TELEPORT_TAG = "setup_tp"
TELEPORT_Z = 0
TELEPORT_SETTLE_S = 10.0             # the command's own text asks the player to wait two seconds for the chunks
TELEPORT_NEAR = 2.0                  # tiles: a frame this near the square reads the teleport as arrived
# CreateHorde2Command (capability CreateHorde): -x -y -z -count -radius, addZombiesInOutfit at the square; -z is the
# character's floor off its last frame (an upstairs character's wave spawns on its floor), 0 when the frame has none
CREATEHORDE2_CMD = "createhorde2 -x {x} -y {y} -z {z} -count {count} -radius {radius}"
# `-crawler true` (CreateHorde2Command's own pair: the next token read as a boolean, true unless "false"; read off the
# jar at 42.22.2, its slot is addZombiesInOutfit's first boolean, the crawler flag), appended for a crawler spawn
CRAWLER_ARG = " -crawler true"
WAVE_RADIUS = 1

# ---------------------------------------------------------------- the wave plans
# spawns: (count, distance in tiles, bearing in degrees from the world's +x axis toward +y[, delay_s[, crawler[,
# radius]]]); the first wave fires at the loop's first frame, then one every period_s (None: that one wave only);
# delay_s (default 0.0) is the spawn's send that many seconds after its wave's first send, crawler (default False)
# adds CRAWLER_ARG to its command, radius (default WAVE_RADIUS) is the command's -radius
WAVE_PLANS = {
    "lone": {"period_s": 60.0, "spawns": ((1, 8.0, 0.0),)},
    "pair": {"period_s": 90.0, "spawns": ((1, 8.0, -35.0), (1, 8.0, 35.0))},     # 70 degrees apart
    "street": {"period_s": None, "spawns": ()},
    # Plan 36 Task 5a: the engagement's arena waves
    "trio": {"period_s": 90.0, "spawns": ((1, 8.0, -60.0), (1, 8.0, 0.0), (1, 8.0, 60.0))},   # 120 degrees across
    "flank": {"period_s": 90.0, "spawns": ((1, 8.0, 0.0), (1, 8.0, 120.0, 10.0))},     # the second 10 s after the first
    "crawler": {"period_s": 90.0, "spawns": ((1, 8.0, 0.0), (1, 5.0, 90.0, 0.0, True))},   # a standing one and a crawler
    # Plan 33 Task 4: no spawns, the fixture's own zombies (the evidence fixture `agent` with the model: the trial
    # on the fixture where the evidence session ran); `Waves.start` starts no thread without spawns
    "none": {"period_s": None, "spawns": ()},
    # Plan 37 Task 1a: the crowd waves, one wave each (period_s None), the crowd on a radius-2 square
    "horde8": {"period_s": None, "spawns": ((8, 10.0, 0.0, 0.0, False, 2),)},         # spec 3.6: eight at once
    "horde10": {"period_s": None, "spawns": ((10, 10.0, 0.0, 0.0, False, 2),)},       # spec 3.6: ten at once
    # F22's shape: a group that grows while the fight is on (three, then four at 10 s and four at 20 s)
    "town": {"period_s": None, "spawns": ((3, 8.0, 0.0), (4, 10.0, 90.0, 10.0, False, 2),
                                          (4, 10.0, 200.0, 20.0, False, 2))},
    # the two open ends of F22's death lane (north-south: the ring at the lane square x 10691, y 10097 reads 90 and 270
    # open to 3 tiles, every other heading a wall within 2.5, read on the controller's boot x_trial-ladder-20261112-041235)
    "pocket": {"period_s": None, "spawns": ((5, 10.0, 90.0, 0.0, False, 2), (5, 10.0, 270.0, 5.0, False, 2))},
}


def spawn_fields(spawn):
    """A spawn tuple's (count, dist, bearing, delay_s, crawler, radius), the optional elements at their defaults."""
    count, dist, bearing = spawn[:3]
    return (count, dist, bearing, spawn[3] if len(spawn) > 3 else 0.0, bool(spawn[4]) if len(spawn) > 4 else False,
            spawn[5] if len(spawn) > 5 else WAVE_RADIUS)

DEFAULT_WAVES = "street"
GOALS = ("scripted", "hold")         # --goals: the goal source's name under --no-llm
DEFAULT_GOALS = "scripted"
HOLD_REST_S = REST_S                 # the hold's Rest: the scripted source's own rest, 30 s, a fresh one when it ends
WAVE_POLL_S = 0.5                    # the wave thread's pass
WAVE_JOIN_S = 6.0                    # its join at the loop's stop: one RCON call's 5 s socket timeout and 1 s
WAVE_CONFIRM_S = 8.0                 # seconds a spawn's zombies have to reach the frames before its one re-send
                                     # (a read spawn was listed within 0.3 s on Task 10's boots and trial 1)
WAVE_CONFIRM_R = 2.0                 # tiles: a zombie first listed this near its spawn's square (the square's centre) after
                                     # the send is that spawn's; the spawn's own radius is WAVE_RADIUS
SPAWN_RX = re.compile(r"CreateHorde2Command\.Command\s*> Spawning ")    # one server log line per spawned zombie
SERVER_LOG = "server-stdout.log"     # in the run folder (pzt.session's log_path)

# ---------------------------------------------------------------- the fixture snapshot
SNAPSHOT_SESSION = 1
SNAPSHOT_TIMEOUT_S = 120             # a fixture's copy (a few hundred MB of caches) in well under two minutes
END_NEAR = TELEPORT_NEAR             # tiles: the character's end this near the teleport's square, for a fixture


def usage(me):
    return ("%s takes only --variant <name> --fixture <name> [--minutes N] [--no-llm] [--goals %s] [--waves %s] "
            "[--teleport X,Y] [--make-fixture <name>] [--detached]" % (me, "|".join(GOALS), "|".join(sorted(WAVE_PLANS))))


def _tokens(argv):
    """{flag: value or True} for argv made only of VALUED flags (each once, with one value not itself a flag) and
    BARE flags (each once, no value); None when it is not."""
    got, i = {}, 0
    argv = list(argv)
    while i < len(argv):
        flag = argv[i]
        if flag in got:
            return None
        if flag in BARE:
            got[flag] = True
            i += 1
        elif flag in VALUED and i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            got[flag] = argv[i + 1]
            i += 2
        else:
            return None
    return got


def tidy(v):
    """A number as the record and the commands carry it: an int when whole, else the float (the one formatter)."""
    v = float(v)
    return int(v) if v.is_integer() else v


def _minutes(s):
    try:
        v = float(s)
    except ValueError:
        return None
    if not math.isfinite(v) or v <= 0 or v > MAX_MINUTES:
        return None
    return tidy(v)


def parse_argv(argv, driver_file):
    """The one-line refusal of anything but the trial's arguments (the module docstring), else None."""
    me = os.path.basename(driver_file)
    head = "%s; refused: %s" % (usage(me), " ".join(argv))
    t = _tokens(argv)
    if t is None:
        return head
    why = None
    missing = [f for f in REQUIRED if f not in t]
    if missing:
        why = "missing %s" % ", ".join(missing)
    elif not NAME_RX.match(t["--variant"]):
        why = "--variant takes a package name ([a-z][a-z0-9_]*)"
    elif not FIXTURE_RX.match(t["--fixture"]):
        why = "--fixture takes a fixture name"
    elif "--minutes" in t and _minutes(t["--minutes"]) is None:
        why = "--minutes takes a number > 0 and at most %d" % MAX_MINUTES
    elif "--goals" in t and t["--goals"] not in GOALS:
        why = "--goals takes one of %s" % ", ".join(GOALS)
    elif t.get("--goals") == "hold" and "--no-llm" not in t:
        why = "--goals hold holds the square with no model: pass --no-llm"
    elif "--waves" in t and t["--waves"] not in WAVE_PLANS:
        why = "--waves takes one of %s" % ", ".join(sorted(WAVE_PLANS))
    elif "--teleport" in t and not TELEPORT_RX.match(t["--teleport"]):
        why = "--teleport takes X,Y"
    elif "--make-fixture" in t and not FIXTURE_RX.match(t["--make-fixture"]):
        why = "--make-fixture takes a fixture name"
    elif t.get("--make-fixture") == t["--fixture"]:
        why = "--make-fixture names the booted fixture; a snapshot never overwrites its parent"
    elif "--make-fixture" in t and WAVE_PLANS[t.get("--waves", DEFAULT_WAVES)]["spawns"]:
        why = "--make-fixture with a spawning wave plan would save the spawned zombies into the fixture"
    else:
        bound = wall_bound(flags(argv))["total_s"]
        if bound > FOREGROUND_CAP_S and "--detached" not in t:
            why = ("the wall bound %s s passes the foreground cap %s s: pass --detached (the controller launches it "
                   "detached after Angus approves)" % (tidy(bound), tidy(FOREGROUND_CAP_S)))
    return "%s (%s)" % (head, why) if why else None


def flags(argv):
    """{variant, fixture, minutes, no_llm, goals, waves, teleport ([x, y] or None), make_fixture, detached} off an argv
    parse_argv accepted."""
    t = _tokens(argv) or {}
    tp = TELEPORT_RX.match(t["--teleport"]) if "--teleport" in t else None
    return {"variant": t.get("--variant"), "fixture": t.get("--fixture"),
            "minutes": _minutes(t["--minutes"]) if "--minutes" in t else DEFAULT_MINUTES,
            "no_llm": bool(t.get("--no-llm")), "goals": t.get("--goals", DEFAULT_GOALS),
            "waves": t.get("--waves", DEFAULT_WAVES),
            "teleport": [tidy(tp.group(1)), tidy(tp.group(2))] if tp else None,
            "make_fixture": t.get("--make-fixture"), "detached": bool(t.get("--detached"))}


def limits_of(args):
    """The session's limits off --minutes: DAY_CAP_S = 60 x minutes (seconds)."""
    return {"DAY_CAP_S": 60.0 * args["minutes"]}


def budget_of(args):
    """The wall budget from the end of the memory gate: the loop's seconds plus BUDGET_EXTRA_S."""
    return 60.0 * args["minutes"] + BUDGET_EXTRA_S


def wall_bound(args):
    """{total_s, parts, launch}: the longest the launch can take, every wait it holds summed: the pre-boot (PREBOOT_S),
    the budget (the boot and the loop: budget_of), then what runs past the budget: the closing Stop's settle, the poll
    worker's join, the wave thread's join, the bounded teardown, the LLM worker's join (none under --no-llm) and the
    snapshot (only under --make-fixture). `launch` "foreground" at or under FOREGROUND_CAP_S, else "detached"."""
    parts = {"preboot": PREBOOT_S, "budget": budget_of(args), "stop_settle": DS.STOP_SETTLE_S,
             "polls_join": POLLS_JOIN_S, "wave_join": WAVE_JOIN_S, "teardown": TEARDOWN_S,
             "llm_join": 0.0 if args["no_llm"] else LLM_JOIN_S,
             "snapshot": float(SNAPSHOT_TIMEOUT_S) if args.get("make_fixture") else 0.0}
    total = sum(parts.values())
    return {"total_s": total, "parts": parts, "launch": "foreground" if total <= FOREGROUND_CAP_S else "detached"}


def bound_line(args):
    """The line printed before the pre-boot: the bound, its parts and the launch form it needs."""
    w = wall_bound(args)
    form = ("foreground: under the %s s cap" % tidy(FOREGROUND_CAP_S) if w["launch"] == "foreground" else
            "detached: past the ten-minute cap, the controller launches it after Angus approves")
    return "x_trial wall bound %s s (%s): %s" % (
        tidy(w["total_s"]), " + ".join("%s %s" % (k, tidy(v)) for k, v in w["parts"].items() if v), form)


# ---------------------------------------------------------------- provenance and trial.json
def _git(repo, *args):
    """(returncode, stdout bytes) of `git -C repo <args>`; (None, b"") when git cannot be run."""
    try:
        p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, timeout=60)
        return p.returncode, p.stdout or b""
    except Exception:                                    # noqa: BLE001 - provenance, never fatal
        return None, b""


UNTRACKED_HEAD = "### untracked file %s (sha256 %s, %d bytes)\n"     # a block of trial.diff past `git diff HEAD`


def untracked_blocks(repo, git=_git):
    """([paths], bytes): the untracked files under SESSION_PATHS (`git ls-files -o --exclude-standard`, the ignored
    ones left out: an uncommitted variant package is one of these), each as an UNTRACKED_HEAD line and its bytes;
    ([], b"") when git does not answer. A file that cannot be read is named with its error and no bytes."""
    rc, raw = git(repo, "ls-files", "-o", "--exclude-standard", "-z", "--", *SESSION_PATHS)
    if rc != 0:
        return [], b""
    paths = sorted(p for p in raw.decode("utf-8", "replace").split("\0") if p)
    out = []
    for rel in paths:
        try:
            with open(os.path.join(repo, rel), "rb") as fh:
                data = fh.read()
        except OSError as e:
            out.append(("### untracked file %s (unread: %s: %s)\n" % (rel, type(e).__name__, e)).encode("utf-8"))
            continue
        out.append((UNTRACKED_HEAD % (rel, hashlib.sha256(data).hexdigest(), len(data))).encode("utf-8") + data
                   + (b"" if data.endswith(b"\n") else b"\n"))
    return paths, b"".join(out)


def provenance(repo=DS.REPO, git=_git):
    """{commit, stamp, dirty, diff_sha256, untracked, provenance, diff}: the stamp's when TRIAL_STAMP.json sits at the
    tree's root (a snapshot tree has no .git; its stamp's diff hash is trial_snapshot.py's), else git's over
    SESSION_PATHS: `diff` the `git diff HEAD` text followed by every untracked file's block (untracked_blocks) when
    dirty, its sha256 the hash of those bytes, saved beside trial.json as trial.diff; None otherwise. A tree with
    neither a stamp nor git records commit and dirty None, never refused (a trial is not evidence)."""
    p = os.path.join(repo, STAMP)
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as fh:
                stamp = json.load(fh)
        except (OSError, ValueError) as e:
            stamp = {"error": "%s: %s" % (type(e).__name__, e)}
        if not isinstance(stamp, dict):
            stamp = {"error": "not a JSON object"}
        return {"commit": stamp.get("commit"), "stamp": stamp, "dirty": stamp.get("dirty"),
                "diff_sha256": stamp.get("diff_sha256"), "untracked": None, "provenance": "stamp", "diff": None}
    rc, head = git(repo, "rev-parse", "HEAD")
    commit = head.decode("utf-8", "replace").strip() if rc == 0 else None
    rc_s, status = git(repo, "status", "--porcelain", "--", *SESSION_PATHS)
    dirty = bool(status.strip()) if rc_s == 0 else None
    diff = digest = untracked = None
    if dirty:
        rc_d, raw = git(repo, "diff", "HEAD", "--", *SESSION_PATHS)
        untracked, blocks = untracked_blocks(repo, git)
        if rc_d == 0:
            raw += blocks
            digest = hashlib.sha256(raw).hexdigest()
            diff = raw.decode("utf-8", "replace")
    return {"commit": commit, "stamp": None, "dirty": dirty, "diff_sha256": digest, "untracked": untracked,
            "provenance": "git", "diff": diff}


def trial_record(args, prov, argv, started_at):
    """trial.json's dict (TRIAL_KEYS, the module docstring); `switches` None until the planner is built, `end_pos` and
    `end_health` None until the session ends."""
    return {"variant": args["variant"], "switches": None, "commit": prov["commit"], "stamp": prov["stamp"],
            "dirty": prov["dirty"], "diff_sha256": prov["diff_sha256"], "untracked": prov.get("untracked"),
            "provenance": prov["provenance"], "fixture": args["fixture"], "minutes": args["minutes"],
            "waves": args["waves"], "wave_plan": {"period_s": WAVE_PLANS[args["waves"]]["period_s"],
                                                  "spawns": [list(s) for s in WAVE_PLANS[args["waves"]]["spawns"]]},
            "no_llm": args["no_llm"], "goals": args["goals"], "teleport": args["teleport"],
            "make_fixture": args["make_fixture"],
            "detached": bool(args.get("detached")), "wall_bound_s": tidy(wall_bound(args)["total_s"]),
            "argv": list(argv), "started_at": started_at, "end_pos": None, "end_health": None}


def write_trial(run_dir, rec):
    """trial.json at the run's root (a tmp file replaced: never half written); its path."""
    path = os.path.join(run_dir, TRIAL_JSON)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, default=str)
    os.replace(tmp, path)
    return path


def switches(planner):
    """{name: value} for every name of survive.py's T<n>_SWITCHES tuples (in T order, then the tuple's), then
    EXTRA_SWITCHES, read off the built planner: the variant's settings, the ladder's defaults for any it leaves."""
    tuples = sorted(((int(m.group(1)), n) for n in dir(SV) for m in [SWITCH_RX.match(n)] if m))
    out = {}
    for _, n in tuples:
        for name in getattr(SV, n):
            out[name] = getattr(planner, name, None)
    for name in EXTRA_SWITCHES:
        out[name] = getattr(planner, name, None)
    return out


# ---------------------------------------------------------------- pre-boot
def variant_check(name, survive=None, control=None):
    """{variant, fork, ok, error}: Survive takes the `control` keyword (Plan 31 Task 1's fork) and the variant loads
    (`control`, default the module `planner.control`: a CONTROLS name, else `load(name)`)."""
    survive = survive or Survive
    r = {"variant": name, "fork": "control" in inspect.signature(survive.__init__).parameters, "ok": False,
         "error": None}
    if not r["fork"]:
        r["error"] = "Survive takes no control= keyword: Plan 31 Task 1's fork is not on this tree"
        return r
    try:
        if control is None:
            from agent.base.planner import control as C
        else:
            C = control
        if name not in getattr(C, "CONTROLS", ()):
            C.load(name)
        r["ok"] = True
    except Exception as e:                               # noqa: BLE001 - an unbuildable variant refuses the boot
        r["error"] = "%s: %s" % (type(e).__name__, e)
    return r


def _java_pids():
    from pzt.doctor import _pz_java_pids                  # the doctor's own reader of the game's Java processes
    return _pz_java_pids()


NOT_PROBED = {"ok": None, "exit": None, "answer": None, "latency_s": None, "error": "not probed: --no-llm"}


def preboot(args, profile, repo=DS.REPO, free=None, java_pids=_java_pids, which=shutil.which, run=subprocess.run,
            survive=None, control=None, min_free_gb=MIN_FREE_GB):
    """(pre, ok): the trial's pre-boot checks (the module docstring), each result in pre["checks"] and its reading
    beside it; ok only when every check holds."""
    free = free or X.free_gb
    path = os.path.join(repo, profile)
    pre = {"profile_path": path, "profile": os.path.splitext(os.path.basename(profile))[0], "checks": {}}
    c = pre["checks"]
    c["profile_exists"] = os.path.isfile(path)
    c["doctor_clean"], text = DL.C.doctor()
    pre["doctor"] = (text or "").strip().splitlines()
    try:
        prof = DL.profile.load(path)
        pre["lint_errors"] = DL.harness.lint_paths(DL.profile.lint_sources(prof, prof.sources))
    except SystemExit as e:                              # ProfileError and fixture errors are SystemExit
        pre["profile_error"], pre["lint_errors"] = str(e), None
    c["lint_clean"] = pre["lint_errors"] == []
    pre["free_gb"] = free()
    c["memory"] = X.memory_ok(pre["free_gb"], min_free_gb)
    try:
        pre["java_pids"] = list(java_pids())
    except Exception as e:                               # noqa: BLE001 - an unread process list refuses the boot
        pre["java_pids"], pre["java_error"] = None, "%s: %s" % (type(e).__name__, e)
    c["no_game_java"] = pre["java_pids"] == []
    try:
        fx.load(args["fixture"])
        c["fixture_ok"], pre["fixture_error"] = True, None
    except (SystemExit, OSError, ValueError) as e:       # fx.load names a missing record or cache by SystemExit
        c["fixture_ok"] = False
        pre["fixture_error"] = str(e) if isinstance(e, SystemExit) else "%s: %s" % (type(e).__name__, e)
    if args.get("make_fixture"):
        c["make_fixture_free"] = not os.path.exists(fx.fixture_dir(args["make_fixture"]))
    pre["variant"] = variant_check(args["variant"], survive, control)
    c["variant_ok"] = pre["variant"]["ok"]
    if args["no_llm"]:
        pre["claude_available"], pre["claude_version"], pre["claude_answers"] = dict(NOT_PROBED), None, dict(NOT_PROBED)
    else:
        ca = PR.claude_available(which, run)
        pre["claude_available"], pre["claude_version"] = ca, ca["version"]
        pre["claude_answers"] = PR.claude_answers(run=run, which=which) if ca["ok"] else dict(
            NOT_PROBED, ok=False, error="not probed: no CLI")
        c["claude_ok"] = bool(ca["ok"] and pre["claude_answers"]["ok"])
    return pre, all(v is True for v in c.values())


# ---------------------------------------------------------------- the waves
def wave_square(pos, dist, bearing_deg):
    """The square (x, y) `dist` tiles from `pos` at `bearing_deg` (degrees from the world's +x axis toward +y)."""
    b = math.radians(bearing_deg)
    return int(math.floor(pos[0] + dist * math.cos(b))), int(math.floor(pos[1] + dist * math.sin(b)))


class Waves:
    """A wave plan's spawns over RCON on its own thread (never the planner's tick: an RCON call may take its 5 s
    socket timeout). `rcon(cmd, tag)` is xs.rcon; `position()` the character's last frame position (x, y, z) or
    None; `clock` the session's own (TrialChain passes it, so the waves and the loop read one clock).
    The first wave fires at `begin`, then one at each period_s boundary; a late pass fires the latest boundary's wave
    and skips the missed ones (no burst), its lateness and the count missed in the row. `listed()` (None: no
    confirmation) is {zombie id: (x, y) of its first listing, or None}, every id any frame has listed: WAVE_CONFIRM_S
    after a spawn's send the ids first listed after it within WAVE_CONFIRM_R tiles of its square are its zombies, and a
    spawn short of its count re-sends the missing count once at its own distance and bearing (the module docstring),
    each confirmation in `confirms` and each wave's counts in `by_wave`. `server_spawns` is set after the teardown from
    the server's log."""

    def __init__(self, plan, rcon, position, clock=time.time, poll_s=WAVE_POLL_S, join_s=WAVE_JOIN_S, listed=None,
                 confirm_s=WAVE_CONFIRM_S, confirm_r=WAVE_CONFIRM_R):
        spec = WAVE_PLANS[plan]
        self.plan, self.period_s, self.spawns = plan, spec["period_s"], tuple(spec["spawns"])
        self.rcon, self.position, self.clock = rcon, position, clock
        self.poll_s, self.join_s = poll_s, join_s
        self.listed, self.confirm_s, self.confirm_r = listed, confirm_s, confirm_r
        self.delayed = []        # {wave, spawn, due, late_s, missed}: a spawn with a delay_s, sent at its `due`
        self.pending = []        # {wave, spawn, due, before, need, at, resend}: a send waiting for its confirmation
        self.confirms = []
        self.by_wave = {}        # wave -> {wave, sent, resent, listed_ids, confirmed}
        self.server_spawns = None
        self.t0 = None
        self.next_i = 0
        self.rows = []
        self.started = False
        self.error = None
        self.joined = None
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()        # one `step` at a time: confirm reads `pending`, calls `listed` and RCON between its reads and removes

    def begin(self, now):
        self.t0, self.started = now, True

    def step(self, now):
        """Confirm the sends that are due, re-sending a short spawn's missing count once, then fire the wave due at
        `now`, if any; the rows added."""
        if self.t0 is None or not self.spawns:
            return []
        with self._lock:                                  # two callers would each re-send the one due confirmation
            added = self.send_delayed(now) + self.confirm(now)
            # a period_s None plan is its one wave: wave 0 now, and no boundary after it
            k = 0 if self.period_s is None else int((now - self.t0) // self.period_s)    # the latest boundary at or before now
            if k < self.next_i:
                return added
            missed, self.next_i = k - self.next_i, k + 1
            return added + self.fire(k, now, now - (self.t0 + k * (self.period_s or 0.0)), missed)

    def _near(self, seen, p):
        """The ids of `seen` first listed after the send `p` (not in its `before`) within `confirm_r` tiles of its
        square's centre, in `repr` order."""
        cx, cy = p["at"][0] + 0.5, p["at"][1] + 0.5
        return sorted((i for i, pos in seen.items() if i not in p["before"] and pos is not None
                       and math.hypot(pos[0] - cx, pos[1] - cy) <= self.confirm_r), key=repr)

    def confirm(self, now):
        """The pending sends past their `confirm_s`: each one's ids (`_near`) against the zombies it spawned, recorded in
        `confirms` and in its wave's `by_wave`; a spawn's first send short of them re-sends the missing count once at
        its own distance and bearing, its own confirmation pending in turn and never re-sent. The rows re-sent."""
        added = []
        due = [p for p in self.pending if now >= p["due"]]
        seen = self.listed() if due else {}
        for p in due:
            self.pending.remove(p)
            ids = self._near(seen, p)
            rec = {"wave": p["wave"], "spawn": p["spawn"], "resend": p["resend"], "need": p["need"],
                   "listed_ids": ids, "t": round(now - self.t0, 3)}
            self.confirms.append(rec)
            w = self.by_wave[p["wave"]]
            w["listed_ids"] = sorted(set(w["listed_ids"]) | set(ids), key=repr)
            w["confirmed"] = len(w["listed_ids"]) >= w["sent"]
            short = p["need"] - len(ids)
            if short > 0 and not p["resend"]:
                rec["resent"] = short
                added += self.fire(p["wave"], now, resend={p["spawn"]: short})
        return added

    def send_delayed(self, now):
        """The delayed spawns due at `now` (a wave's `delay_s` spawns, queued by `fire`), each sent at the character's
        position then; the rows added."""
        due = [d for d in self.delayed if now >= d["due"]]
        added = []
        for d in due:
            self.delayed.remove(d)
            added += self.fire(d["wave"], now, d["late_s"], d["missed"], only=d["spawn"], delayed=True)
        return added

    def fire(self, i, now, late_s=0.0, missed=0, resend=None, only=None, delayed=False):
        """Wave `i`'s spawns at the square off the character's last frame (`resend` {spawn: count}: only those spawns, at
        that count and each its own distance and bearing and no delay, the rows marked `resend_of`); a spawn with a
        `delay_s` is queued in `delayed` and sent by `send_delayed` that long after (`only`, `delayed`: that spawn's
        own send); one pending confirmation per spawn sent, when `listed` is set."""
        pos = self.position()
        before = frozenset(self.listed()) if self.listed is not None else None
        added = []
        w = self.by_wave.setdefault(i, {"wave": i, "sent": 0, "resent": 0, "listed_ids": [], "confirmed": False})
        for j, spawn in enumerate(self.spawns):
            count, dist, bearing, delay_s, crawler, radius = spawn_fields(spawn)
            if only is not None and j != only:
                continue
            if resend is not None:
                if j not in resend:
                    continue
                count = resend[j]
            elif delay_s > 0.0 and not delayed:
                self.delayed.append({"wave": i, "spawn": j, "due": now + delay_s, "late_s": late_s, "missed": missed})
                continue
            row = {"wave": i, "spawn": j, "t": round(now - self.t0, 3), "lateS": round(late_s, 3), "missed": missed,
                   "count": count, "dist": dist, "bearing": bearing, "from": list(pos) if pos else None, "at": None,
                   "cmd": None, "ack": None}
            if delay_s > 0.0:
                row["delayS"] = delay_s
            if crawler:
                row["crawler"] = True
            if radius != WAVE_RADIUS:
                row["radius"] = radius
            if resend is not None:
                row["resend_of"] = i
            if pos is None:
                row["skipped"] = "no frame position"
            else:
                x, y = wave_square(pos, dist, bearing)
                z = int(pos[2]) if len(pos) > 2 and DS._num(pos[2]) is not None else 0     # the character's floor
                row["at"] = [x, y, z]
                row["cmd"] = CREATEHORDE2_CMD.format(x=x, y=y, z=z, count=int(count), radius=radius) + (
                    CRAWLER_ARG if crawler else "")
                row["ack"] = self.rcon(row["cmd"], "wave_%d_%d%s" % (i, j, "" if resend is None else "_resend"))
                w["resent" if resend is not None else "sent"] += int(count)
                if before is not None:
                    self.pending.append({"wave": i, "spawn": j, "due": now + self.confirm_s, "before": before,
                                         "need": int(count), "at": (x, y), "resend": resend is not None})
            self.rows.append(row)
            added.append(row)
        return added

    def _run(self):
        try:
            while True:
                self.step(self.clock())
                if self._stop.wait(self.poll_s):
                    return
        except Exception as e:                           # noqa: BLE001 - a wave fault ends the waves, never the loop
            self.error = "%s: %s" % (type(e).__name__, e)

    def start(self):
        """Begin now and, when the plan spawns, start the thread."""
        self.begin(self.clock())
        if self.spawns:
            self._thread = threading.Thread(target=self._run, name="x_trial-waves", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(self.join_s)
            self.joined = not self._thread.is_alive()

    def record(self):
        return {"plan": self.plan, "period_s": self.period_s, "spawns": [list(s) for s in self.spawns],
                "started": self.started, "rows": [dict(r) for r in self.rows], "error": self.error,
                "joined": self.joined, "confirm": [dict(c) for c in self.confirms],
                "by_wave": [dict(w) for _, w in sorted(self.by_wave.items())], "server_spawns": self.server_spawns}


def server_spawns(run_dir, name=SERVER_LOG):
    """The number of "Spawning" lines CreateHorde2Command wrote to the run's server log (one per spawned zombie, SPAWN_RX),
    read after the teardown; None without the log or when it cannot be read."""
    try:
        with open(os.path.join(run_dir, name), encoding="utf-8", errors="replace") as fh:
            return sum(1 for ln in fh if SPAWN_RX.search(ln))
    except OSError:
        return None


def note_server_spawns(out, run_dir):
    """The server's spawn count into out["loop"]["trial"]["waves"]["server_spawns"] (no session, no loop record or no wave
    record: nothing to note); the count."""
    w = DS._d(DS._d(DS._d(out.get("loop")).get("trial")).get("waves"))
    if not w:
        return None
    n = server_spawns(run_dir)
    w["server_spawns"] = n
    return n


# ---------------------------------------------------------------- the session
def teleport(sess, x, y, settle_s=TELEPORT_SETTLE_S, near=TELEPORT_NEAR):
    """TELEPORT_CMD over RCON, then the transport pumped until a frame reads within `near` tiles of (x, y), or
    `settle_s`: {cmd, ack, arrived, waitS, pos}."""
    cmd = TELEPORT_CMD.format(user=sess.user, x=tidy(x), y=tidy(y), z=TELEPORT_Z)
    ack = sess.xs.rcon(cmd, TELEPORT_TAG)
    t0 = sess.clock()

    def there():
        p = sess.last_pos
        return p is not None and math.hypot(p[0] - x, p[1] - y) <= near
    arrived = sess.wait(there, settle_s)
    return {"cmd": cmd, "ack": ack, "arrived": arrived, "waitS": round(sess.clock() - t0, 3),
            "pos": list(sess.last_pos) if sess.last_pos else None}


class TrialChain(DY.Chain):
    """day.Chain with the trial's setup: the teleport at the loop phase's start (before the loop), the waves started
    at the loop's first frame on the session's clock and stopped at the loop's stop (before the closing Stop's settle
    and the poll worker's join), both in out["loop"]["trial"]. `idle` (--make-fixture) keeps the planner from deciding:
    the loop pumps, polls and saves, and no variant assess runs, so the fixture keeps the character where the teleport
    put it."""

    def __init__(self, xs, transport, teleport_to=None, waves=DEFAULT_WAVES, wave_kw=None, idle=False, **kw):
        self.teleport_to = teleport_to
        self.teleport_rec = None
        self.idle = idle
        # (x, y, z) of the last frame: a tuple assigned whole, so the wave thread reads it without a lock (the frames
        # deque is the loop's)
        self.last_pos = None
        self.first_seen = {}                     # {zombie id: (x, y) of its first listing}: assigned whole, read by the waves
        super().__init__(xs, transport, **kw)
        self.waves = Waves(waves, xs.rcon, lambda: self.last_pos,
                           **dict({"clock": self.clock, "listed": lambda: self.first_seen}, **(wave_kw or {})))

    def on_frame(self, line):
        super().on_frame(line)
        me = line.get("me")
        if isinstance(me, dict) and DS._num(me.get("x")) is not None and DS._num(me.get("y")) is not None:
            self.last_pos = (me["x"], me["y"], me.get("z"))
        new = {}
        for z in line.get("zombies") or ():
            if isinstance(z, dict) and z.get("id") is not None and z["id"] not in self.first_seen and z["id"] not in new:
                x, y = DS._num(z.get("x")), DS._num(z.get("y"))
                new[z["id"]] = (x, y) if x is not None and y is not None else None
        if new:
            self.first_seen = {**self.first_seen, **new}
        if self.t_loop0 is not None and self.stopped is None and not self.waves.started:    # the loop's, not the stop's
            self.waves.start()

    def planner_tick(self):
        if self.idle:
            self.mark_shot()
            return
        super().planner_tick()

    def stop_character(self):
        self.waves.stop()                        # no wave past the loop's stop, a death's included
        super().stop_character()

    def phase_loop(self):
        try:
            if self.ready and self.teleport_to:
                self.teleport_rec = teleport(self, *self.teleport_to)
            super().phase_loop()
        finally:
            self.waves.stop()
            self.save()

    def extra_record(self):
        rec = super().extra_record()
        rec["trial"] = {"teleport": self.teleport_rec, "waves": self.waves.record(), "idle": self.idle}
        return rec

    def end_state(self):
        """{pos [x, y, z], health, start_health}: the last kept frame's, the first frame's health beside it."""
        last = self.frames[-1] if self.frames else {}
        me = DS._d(last.get("me"))
        return {"pos": [me.get("x"), me.get("y"), me.get("z")] if me else None, "health": DS.body_health(last),
                "start_health": DS.body_health(self.first_frame or {})}


class HoldSource:
    """The arena's goal source (the module docstring, THE HOLD): `Rest(HOLD_REST_S)` for every request, a fresh goal
    each time one ends, never a loot, a shelter or a stock; the first request on each scan place (`place`, the view's
    pos on the SCAN_R grid as `policies.place_of` rounds it) is the scan in place, `ExploreToward` to the character's
    own square (floored), which scans and ends arrived. `square` is the first pos a view reads (None before one), noted
    and never walked to: a `Rest` carries no square. `scanned` the places a scan was proposed on."""
    NAME = "hold"

    def __init__(self):
        self.square = None
        self.scanned = []

    @staticmethod
    def place(x, y):
        return int(math.floor(x / SCAN_R + 0.5)) * SCAN_R, int(math.floor(y / SCAN_R + 0.5)) * SCAN_R

    def propose(self, view):
        pos = (view or {}).get("pos") or {}
        if not (isinstance(pos.get("x"), (int, float)) and isinstance(pos.get("y"), (int, float))):
            return Rest(HOLD_REST_S)
        if self.square is None:
            self.square = [pos["x"], pos["y"]]
        place = self.place(pos["x"], pos["y"])
        if place not in self.scanned:
            self.scanned.append(place)
            return ExploreToward(int(math.floor(pos["x"])), int(math.floor(pos["y"])))
        return Rest(HOLD_REST_S)


def planner_factory(variant, no_llm, runner=None, goals=DEFAULT_GOALS):
    """Survive with `control=<variant>` over the scripted goal source (no_llm), the HoldSource (`goals` "hold"), else
    the LLMSource over the scripted source, goals.log beside the decision log; `runner` the CLI's (None: the real
    one; tests inject a fake). Every arm runs Survive's own defaults (the Dress maneuver on since Plan 31 Task 15a);
    a variant sets its own switches in its `prepare`."""
    def planner(world, actions, log_path, clock):
        if goals == "hold":
            source = HoldSource()
        elif no_llm:
            source = ScriptedSource()
        else:
            source = L.LLMSource(ScriptedSource(), log_path=os.path.join(os.path.dirname(log_path), GOALS_LOG),
                                 timeout_s=L.LLM_TIMEOUT_S, clock=clock, runner=runner)
        return Survive(world, actions, log_path, clock, source=source, control=variant)
    return planner


def llm_extra(cli_version):
    """The `llm` record key off the session's LLMSource (f_goals_16.py's)."""
    def extra(sess):
        src = sess.planner.goals.source
        return {"llm": dict(src.totals(), calls=[dict(c) for c in src.calls], model=MODEL, cli_version=cli_version)}
    return extra


def make_session(xs, transport, args, cli_version=None, runner=None, **kw):
    """The trial's TrialChain (day.make_day_session): the variant's planner, the --minutes cap (laid under any
    `limits` in kw), the teleport, the wave plan and the idle planner under --make-fixture; the `llm` record without
    --no-llm."""
    limits = dict(limits_of(args), **(kw.pop("limits", None) or {}))
    return DY.make_day_session(xs, transport, planner_factory(args["variant"], args["no_llm"], runner, args["goals"]),
                               extra=None if args["no_llm"] else llm_extra(cli_version), limits=limits,
                               cls=TrialChain, teleport_to=args["teleport"], waves=args["waves"],
                               idle=bool(args.get("make_fixture")), **kw)


def run_session(args, xs, transport, pre, note_planner, **kw):
    """The session: built (`kw` make_session's clock, sleep, free, polls and limits), its planner noted (trial.json's
    switches), run; returned for after_teardown."""
    sess = make_session(xs, transport, args, cli_version=pre.get("claude_version"), **kw)
    note_planner(sess.planner)
    sess.run()
    return sess


def after_teardown(out, sess):
    """The LLMSource's worker joined after the teardown (out["llm_joined"]); nothing under --no-llm or without a
    session."""
    if sess is None or not hasattr(sess.planner.goals.source, "join"):
        return
    out["llm_joined"] = sess.planner.goals.source.join(LLM_JOIN_S)


# ---------------------------------------------------------------- the fixture
def server_stop(out):
    """{marked, rc, clean}: the teardown's `server_stopped` mark off the timeline (x49b_lib.bounded_teardown: rc None
    when the 45 s stop timed out and the process was killed), clean only on rc 0 with no teardown or hard-kill error."""
    marks = [m for m in out.get("timeline") or () if isinstance(m, dict) and m.get("phase") == "server_stopped"]
    rc = marks[-1].get("rc") if marks else None
    return {"marked": bool(marks), "rc": rc, "clean": bool(marks) and rc == 0 and not out.get("teardown_error")
            and not out.get("hard_kill_error")}


def make_fixture(out, args, run_dir, end=None, run=subprocess.run):
    """`pzt snapshot --from-run <run_dir> --name <make_fixture> --parent <fixture> --session 1` after the teardown,
    only when every gate holds: no error or abort, the server stopped by its own stop (server_stop clean: a killed
    server may have saved a stale world), the session stopped at its cap, the teleport (if any) arrived, and the
    character's end (`end`, TrialChain.end_state) within END_NEAR of the teleport's square and no less healthy than at
    its first frame. {name, cmd, ran, exit, output, skipped, error, server_stop, end}."""
    cmd = CH.snapshot_cmd(run_dir, args["make_fixture"], args["fixture"], SNAPSHOT_SESSION)
    end = end or {"pos": None, "health": None, "start_health": None}
    ss = server_stop(out)
    r = {"name": args["make_fixture"], "cmd": cmd, "ran": False, "exit": None, "output": None, "skipped": None,
         "error": None, "server_stop": ss, "end": end}
    stop = (out.get("stop") or {}).get("reason")
    tp = DS._d(DS._d(out.get("loop")).get("trial")).get("teleport")
    pos, tgt = end.get("pos"), args["teleport"]
    if out.get("error") or out.get("abort"):
        r["skipped"] = "the session failed: %s" % (out.get("error") or out.get("abort"))
    elif not ss["clean"]:
        r["skipped"] = "the server did not stop cleanly (rc %s, marked %s)" % (ss["rc"], ss["marked"])
    elif stop != "day_cap":
        r["skipped"] = "the session stopped %s, not at its cap" % stop
    elif tgt and not DS._d(tp).get("arrived"):
        r["skipped"] = "no frame read the teleport's square"
    elif tgt and not (pos and DS._num(pos[0]) is not None and DS._num(pos[1]) is not None
                      and math.hypot(pos[0] - tgt[0], pos[1] - tgt[1]) <= END_NEAR):
        r["skipped"] = "the character ended at %s, not within %s tiles of the teleport's square" % (pos, END_NEAR)
    elif DS._num(end.get("health")) is None or (DS._num(end.get("start_health")) is not None
                                                and end["health"] < end["start_health"]):
        r["skipped"] = "the character ended wounded or unread (health %s, %s at the start)" % (
            end.get("health"), end.get("start_health"))
    if r["skipped"]:
        return r
    try:
        p = run(cmd, capture_output=True, text=True, timeout=SNAPSHOT_TIMEOUT_S)
        r.update(ran=True, exit=p.returncode, output=((p.stdout or "") + (p.stderr or ""))[-2000:])
    except Exception as e:                               # noqa: BLE001 - the record is written whatever the call does
        r["error"] = "%s: %s" % (type(e).__name__, e)
    return r


# ---------------------------------------------------------------- the boot
def boot_and_run(args, preboot_fn, *, key, driver, artifact, profile, argv, user=USER, repo=DS.REPO,
                 wall=time.time, run_session_fn=None, boot=None, teardown=None, kill=None, run=subprocess.run,
                 provenance_fn=provenance, run_prefix=None):
    """A trial's boot (the module docstring): day.boot_and_run without copy_run, next_steps or a grade, with
    trial.json, the --minutes limits and the --make-fixture snapshot. `run_session_fn(xs, transport, pre,
    note_planner)` (default run_session over args); `boot`, `teardown`, `kill` and `run` are _dlib.boot,
    x49b_lib.bounded_teardown, _common.hard_kill and subprocess.run unless a test injects them. Returns out."""
    from _common import ask, hard_kill                       # noqa: E402
    from pzt import profile as pzt_profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402
    from agent.base.transport.files import FileTransport     # noqa: E402

    boot = boot or DL.boot
    teardown = teardown or B.bounded_teardown
    kill = kill or hard_kill
    run_session_fn = run_session_fn or (lambda xs, tr, pre, note: run_session(args, xs, tr, pre, note))
    print(bound_line(args), flush=True)                      # first: the launch form this trial needs
    pre, ok = preboot_fn()
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the trial was not started: %s" % ", ".join(
            k for k, v in pre.get("checks", {}).items() if v is not True))
        sys.exit(1)
    prof = pzt_profile.load(os.path.join(repo, profile))
    rec_fx = fx.load(args["fixture"])
    limits, budget_s = limits_of(args), budget_of(args)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    ran = None
    out = DS.new_out()
    out["world_changes"]["restored"] = "fixture %s restored into the run dir" % args["fixture"]
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=user)
    # the memory gate before the run folder (a refusal leaves no folder that never booted), one read and no wait: the
    # pre-boot read the floor already, and a wait would run outside the wall bound
    DS.memory_gate(xs, MIN_FREE_GB, wait=lambda g: DL.wait_memory(g, max_wait_s=0.0))
    run_id, run_dir = new_run_dir(run_prefix or "%s-%s" % (key, args["variant"]))     # run_prefix: x_facing's x_facing-<stamp>
    prov = provenance_fn(repo)
    trial = trial_record(args, prov, argv, datetime.datetime.now().isoformat(timespec="seconds"))
    if prov.get("diff") is not None:
        with open(os.path.join(run_dir, TRIAL_DIFF), "w", encoding="utf-8", newline="") as fh:
            fh.write(prov["diff"])
    write_trial(run_dir, trial)

    def note_planner(planner):
        trial["switches"] = switches(planner)
        write_trial(run_dir, trial)

    xs.path = os.path.join(run_dir, artifact)
    out.update({"run_id": run_id, "session_key": key, "driver": driver, "user": user, "profile": prof.report(),
                "preboot": pre, "argv": list(argv), "trial": trial, "wall_bound": wall_bound(args),
                "constants": dict(DS.DEFAULTS, **dict(DY.LIMITS, **limits), BUDGET_S=budget_s,
                                  LLM_TIMEOUT_S=L.LLM_TIMEOUT_S),
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build"), "parent": rec_fx.get("parent"),
                            "session": rec_fx.get("session")},
                "driver_commit": prov["commit"]})
    xs.mem("preboot")
    xs.persist()
    try:
        out.update(boot(xs, prof, rec_fx, run_dir, [user], started, clients, holder,
                        make_client=DS.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[user])
            ran = run_session_fn(xs, FileTransport(DL.state_dir(clients[user])), pre, note_planner)
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = "%s: %s" % (type(e).__name__, e), traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n_parks = DS.count_parks([(getattr(c, "username", "?"), c.console) for c in every], xs.parked())
            out["logs"] = {"patterns": {"park": DS.DEFAULTS["PARK_RX"]}, "clients": found}
            out["frames"]["parks"] = n_parks

        out["teardown_started_wall"] = wall()
        xs.finish(teardown, kill, every, read_logs=read_logs)
        xs.mem("after")
        DY.run_after_teardown(after_teardown, out, ran)
        note_server_spawns(out, run_dir)
        end = ran.end_state() if ran is not None else None
        if end is not None:
            trial["end_pos"], trial["end_health"] = end["pos"], end["health"]
        write_trial(run_dir, trial)
        out["finished"] = True
        xs.persist()
    if args["make_fixture"]:
        out["make_fixture"] = make_fixture(out, args, run_dir, end, run)
        xs.persist()
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "stop": out.get("stop"), "trial": trial,
                      "make_fixture": out.get("make_fixture"), "wall_seconds": out.get("wall_seconds"),
                      "score": "python tools/trial_score.py %s" % run_dir}, indent=1, default=str))
    return out
