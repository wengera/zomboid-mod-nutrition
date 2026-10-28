"""The day session (Plan 23 Task 16d): what a chained day's session drivers share, moved out of `e_day.py` (Task 16c)
so `e_day.py` (the scripted survivor) and `f_goals.py` (the LLM goal source) import one copy and neither imports the
other (a driver is frozen at its boot; this library is not, and each driver's pre-boot records its commit).

- The constants both day drivers share (M-8): `USER`, `BUDGET_S`, `DAY_CAP_S`, `PLANNER_HZ`, `DAMAGE_POLL_S`,
  `MIN_FREE_GB`, `LIMITS` (laid over the library's DEFAULTS) and `CONSTANTS` (the record's); a driver keeps only its
  KEY, DRIVER, ARTIFACT and PROFILE, its planner, its extra record and its pre-boot additions.
- The arguments: `ALLOWED` (`--session N`, `--fixture NAME`, `--prev PATH`, each once with one value),
  `parse_argv(argv, driver_file)` (the library's refusal plus a `--session` that is not an int >= 1, named by the
  driver's own file), `flags(argv)` ({session, fixture, prev}, defaults 1, DEFAULT_FIXTURE, None).
- The chain's inputs: `load_prev(path)` (the previous session's artifact, or why it does not read as one),
  `chain_record(args, profile_fixture, commit)` (out["chain"]), `chain_checks(args)` (the dict a driver's pre-boot
  stores as "chain_checks"): the fixture's record and cache through `fx.load` (a missing, unreadable or corrupt
  record refuses the boot, never a traceback), --prev read as an artifact carrying `loop.last_frames` (the lineage's
  previous frame; a prev without them refuses), and `session_consistent`: `--session n` against the fixture
  record's `session` and the prev artifact's `chain.session`, each expected n-1 where present (None when neither
  is); False refuses the boot (ruling P23-Z: the chain is run by hand, and a wrong --session would freeze a
  mislabelled artifact), `session_line(checks)` the line the refusal prints.
- `Chain(DS.Session)`: the Session with the chain's two hooks. `on_frame` keeps the session's first frame (a frame
  row, read in the hello phase); `extra_record` returns `goals` (`GoalRunner.rows()`: the ended goals, then the
  running one), `night` ({wants, steps, sleeps}, copies), `lineage` (`chain.lineage_diff(prev, first frame)` with a
  prev, else None) and `t_loop0_ms` (equal to loop.startPyMs by construction: both are the loop's start), then lays
  `extra(session)` over them when the driver passes one (f_goals: `llm`; its keys must not be the contract's,
  CONTRACT_KEYS, asserted at every save). `copied` names run-dir files the artifact
  copy takes beside the decision log (f_goals: `goals.log`). The planner is the driver's `planner_factory`.
- `make_day_session(xs, transport, planner_factory, extra=None, copied=(), prev=None, ..., shots=None)`: the one
  builder of a day's Chain: LIMITS with the caller's `limits` laid over them, a PollThread on the session's clock
  (P23-13) and the session's screenshots (ruling P23-AL): `shots`, else `day_shots(xs, clock)`, a shots.ShotTaker
  over the run dir aimed at the user's client process (`xs.clients[user].proc.pid`), None when no client process is
  known (the offline tests' fake clients), so every day driver gains the shots without a driver edit.
- THE ARTIFACT'S FILES (testing/artifacts/<run_id>/, byte-identical, `copy_run`: `copy_shots_index` first, then
  `xs.copy_artifacts`, whose raise is printed and never skips the index):
  the driver's artifact JSON, decision.log, the driver's `copied` files (f_goals: goals.log), and
  shots/shots.jsonl, the screenshots' index (`copy_shots_index`; shots.py's docstring). The images stay in the run
  dir (testing/runs/, gitignored): a write-up copies the ones it cites byte-identical into the artifact's shots/.
- `next_fixture(n)` (the chain's fixtures are agent-s1, agent-s2, ..., spec section 4) and `next_steps(args, run_dir,
  artifact)`: the `pzt snapshot` argv into the next fixture and the next session's arguments (`--session n+1
  --fixture agent-s<n> --prev <this artifact>`), for an E session and for an F session on the chain's last fixture
  (P23-Z refuses any other --session).
- `grade(out, key, fn)`: out[key] = fn(out), else out[key + "_error"] (the controller re-grades the artifact).
  `grade_day(out)` is a new day session's grade: `grade(out, GRADE_KEY, gates_e.grade_e2)`, GRADE_KEY "grade_e2"
  (PZA/1.3's death signal, ruling P23-AO), so the record names the grade it carries; a driver passes GRADE_KEY as its
  boot's grade_key. The drivers frozen before it (e_day.py to e_day_4.py) keep their own grade_e1 call.
- `boot_and_run(args, ...)`: a day driver's whole boot (Plan 22's d_survive.py boot, generalised): the pre-boot
  checks (a failure prints them and exits 1 before anything starts), the profile and the fixture `--fixture` names,
  the run dir (`new_run_dir(key)`), Xs and the out header (run_id, preboot, constants, out["chain"], the fixture's
  record, driver_commit), the memory gate, `_dlib.boot` with the stale pzagent/ folder cleared, the verify rows
  (a failed one aborts), `ran = run_session(xs, transport, prev, pre)`, then out["teardown_started_wall"] (this
  host's epoch seconds as the teardown begins: the gap from the last kept frame to the server's save, which the next
  session's lineage reads), the teardown, the park count, `after_teardown(out, ran)` when the driver passes one
  (f_goals: the LLM worker joined, so no join widens that gap; a fault lands in out["after_teardown_error"]), the
  driver's grade, `finished`, the persist and the artifact copy (copy_run: the shots' index first); the summary printed
  names the grade's report lines and `next` (next_steps: the `pzt snapshot` argv for the chain's next fixture and
  the next session's arguments).
"""
import json
import os
import shutil
import sys
import time

from agent.base import gates_e as GE
from agent.driverlib import chain as CH
from agent.driverlib import session as DS
from agent.driverlib import shots as SH
from agent.driverlib.polls import PollThread
from pzt import fixture as fx

DL, X = DS.DL, DS.X
ALLOWED = ("--session", "--fixture", "--prev")
DEFAULT_FIXTURE = "agent"
USER = "admin"
BUDGET_S = 1200.0                    # the wall budget from the end of the memory gate, the boot included
DAY_CAP_S = 840                      # the loop's own wall time
PLANNER_HZ = 2
DAMAGE_POLL_S = 5
MIN_FREE_GB = DS.DEFAULTS["MIN_FREE_GB"]
LIMITS = {"DAY_CAP_S": DAY_CAP_S, "PLANNER_HZ": PLANNER_HZ, "DAMAGE_POLL_S": DAMAGE_POLL_S}
CONSTANTS = dict(DS.DEFAULTS, **LIMITS, BUDGET_S=BUDGET_S)
CONTRACT_KEYS = ("goals", "night", "lineage", "t_loop0_ms")     # Chain.extra_record's own keys (task-15-amendments)


# ================================================================ arguments
def parse_argv(argv, driver_file):
    """The one-line refusal of anything but ALLOWED (each once, with one value) and of a --session that is not an int
    >= 1, else None."""
    refusal = DS.parse_argv(argv, driver_file, ALLOWED)
    if refusal:
        return refusal
    s = DS.parse_flags(argv, ALLOWED).get("--session")
    if s is not None and not (s.isdigit() and int(s) >= 1):
        return "%s: --session takes an int >= 1; refused: %s" % (os.path.basename(driver_file), " ".join(argv))
    return None


def flags(argv):
    """{session, fixture, prev} off an argv parse_argv accepted (the defaults 1, DEFAULT_FIXTURE, None)."""
    f = DS.parse_flags(argv, ALLOWED) or {}
    return {"session": int(f.get("--session", 1)), "fixture": f.get("--fixture", DEFAULT_FIXTURE),
            "prev": f.get("--prev")}


# ================================================================ the chain's inputs
def load_prev(path):
    """(the previous session's artifact, None), or (None, why) when it does not read as one; (None, None) without a
    path."""
    if path is None:
        return None, None
    try:
        with open(path, encoding="utf-8") as fh:
            art = json.load(fh)
    except (OSError, ValueError) as e:
        return None, "%s: %s" % (type(e).__name__, e)
    if not isinstance(art, dict):
        return None, "not an artifact (a JSON %s): %s" % (type(art).__name__, path)
    return art, None


def chain_record(args, profile_fixture, commit):
    """out["chain"]: the session, the fixture booted beside the profile's own, the previous artifact's path and the
    tree's commit."""
    return {"session": args["session"], "fixture_arg": args["fixture"], "profile_fixture": profile_fixture,
            "prev": args["prev"], "commit": commit}


def chain_checks(args):
    """(checks, ok): {fixture, fixture_ok, fixture_error, fixture_session, prev, prev_ok, prev_error, prev_frames,
    prev_session, session, session_consistent} (the module docstring)."""
    n = args["session"]
    cc = {"fixture": args["fixture"], "fixture_ok": False, "fixture_error": None, "fixture_session": None,
          "prev": args["prev"], "prev_ok": None, "prev_error": None, "prev_frames": None, "prev_session": None,
          "session": n, "session_consistent": None}
    try:
        rec = fx.load(args["fixture"])
        cc["fixture_ok"] = True
        cc["fixture_session"] = rec.get("session") if isinstance(rec, dict) else None
    except (SystemExit, OSError, ValueError) as e:       # fx.load names a missing record or cache by SystemExit
        cc["fixture_error"] = str(e) if isinstance(e, SystemExit) else "%s: %s" % (type(e).__name__, e)
    if args["prev"] is not None:
        art, cc["prev_error"] = load_prev(args["prev"])
        cc["prev_ok"] = art is not None
        if art is not None:
            frames = DS._d(art.get("loop")).get("last_frames")
            cc["prev_frames"] = isinstance(frames, list) and len(frames) > 0
            if not cc["prev_frames"]:
                cc["prev_error"] = "no loop.last_frames: the lineage has no previous frame"
            cc["prev_session"] = DS._d(art.get("chain")).get("session")
    seen = [s for s in (cc["fixture_session"], cc["prev_session"]) if s is not None]
    cc["session_consistent"] = all(s == n - 1 for s in seen) if seen else None
    return cc, bool(cc["fixture_ok"] and cc["prev_ok"] is not False and cc["prev_frames"] is not False
                    and cc["session_consistent"] is not False)


def session_line(cc):
    """The refusal's line when --session does not follow the chain (session_consistent False), else None."""
    if cc.get("session_consistent") is not False:
        return None
    return ("refused (P23-Z): --session %s does not follow the chain: the fixture's session %s, the prev's %s "
            "(each expected %s)" % (cc.get("session"), cc.get("fixture_session"), cc.get("prev_session"),
                                    cc["session"] - 1 if isinstance(cc.get("session"), int) else "n-1"))


# ================================================================ the session
class Chain(DS.Session):
    """The library's Session with the chain's hooks: the first frame kept, the goals, the night, the lineage and the
    loop's start in the record, and the driver's `extra(session)` laid over them."""

    def __init__(self, xs, transport, prev=None, extra=None, copied=(), **kw):
        self.prev = prev
        self.first_frame = None
        self.extra = extra
        for name in copied:
            xs.copied.append(name)
        super().__init__(xs, transport, **kw)

    def on_frame(self, line):
        if self.first_frame is None:
            self.first_frame = DS.frame_row(line)

    def extra_record(self):
        p = self.planner
        n = p.night
        rec = {"goals": p.goals.rows(),
               "night": {"wants": n.wants_n, "steps": [dict(r) for r in n.steps],
                         "sleeps": [dict(r) for r in n.sleeps]},
               "lineage": CH.lineage_diff(self.prev, self.first_frame) if self.prev is not None else None,
               # loop.startPyMs's value: both are the loop's start on this host's clock
               "t_loop0_ms": self.t_loop0 * 1000.0 if self.t_loop0 is not None else None}
        if self.extra is not None:
            ex = self.extra(self)
            clash = sorted(set(ex) & set(CONTRACT_KEYS))
            assert not clash, "extra overwrites the record's contract keys: %s" % clash
            rec.update(ex)
        return rec


def day_shots(xs, clock=time.time):
    """A shots.ShotTaker over the run dir (xs.path's) aimed at the user's client process, on `clock`; None when the
    client has no process (a fake client) or the run has no path."""
    client = (getattr(xs, "clients", None) or {}).get(getattr(xs, "user", None))
    pid = getattr(getattr(client, "proc", None), "pid", None)
    if pid is None or not getattr(xs, "path", None):
        return None
    return SH.ShotTaker(os.path.dirname(xs.path), pid=pid, clock=clock)


def make_day_session(xs, transport, planner_factory, extra=None, copied=(), prev=None, clock=time.time,
                     sleep=time.sleep, free=X.free_gb, polls=None, limits=None, shots=None):
    """The day's Chain: the driver's planner, extra record and copied files, LIMITS (with `limits` laid over them),
    a PollThread on `clock` unless `polls` is given, and `shots` (else day_shots(xs, clock))."""
    return Chain(xs, transport, prev=prev, extra=extra, copied=copied, planner_factory=planner_factory, clock=clock,
                 sleep=sleep, free=free, limits=dict(LIMITS, **(limits or {})),
                 polls=polls if polls is not None else PollThread(clock),
                 shots=shots if shots is not None else day_shots(xs, clock))


def copy_shots_index(repo, run_id, run_dir):
    """The run dir's shots/shots.jsonl copied byte-identical to testing/artifacts/<run_id>/shots/; its path, or None
    when there is none or the copy failed (never raises: the artifact copy is already made)."""
    src = os.path.join(run_dir, SH.SHOTS_DIR, SH.INDEX)
    if not os.path.isfile(src):
        return None
    dest = os.path.join(repo, "testing", "artifacts", run_id, SH.SHOTS_DIR, SH.INDEX)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
        return dest
    except OSError as e:
        print("could not copy the shots' index to %s: %s: %s" % (dest, type(e).__name__, e))
        return None


def next_fixture(n):
    """The fixture snapshotted off session n's run: agent-s<n> (spec section 4)."""
    return "%s-s%d" % (DEFAULT_FIXTURE, n)


def next_steps(args, run_dir, artifact):
    """{snapshot_cmd, next_session, f_session}: the `pzt snapshot` argv off this run into next_fixture(n), and the
    next session's arguments (--session n+1, that fixture, --prev this artifact), the F session's line naming P23-Z."""
    n = args["session"]
    nxt = next_fixture(n)
    boot = "--session %d --fixture %s --prev %s" % (n + 1, nxt, artifact)
    return {"snapshot_cmd": CH.snapshot_cmd(run_dir, nxt, args["fixture"], n), "next_session": boot,
            "f_session": "an F session on the chain's last fixture: f_goals.py %s (P23-Z: any other --session is "
                         "refused)" % boot}


def copy_run(xs, repo, run_id, run_dir, artifact):
    """The run's files into testing/artifacts/<run_id>/: the shots' index first (copy_shots_index), then
    xs.copy_artifacts (the artifact, the decision log, the copied files); its destination, or None when it raised
    (printed, never raised: the index is already copied)."""
    copy_shots_index(repo, run_id, run_dir)
    try:
        return xs.copy_artifacts(repo, run_id, run_dir, artifact)
    except Exception as e:                               # noqa: BLE001 - the summary still prints
        print("the artifact copy raised: %s: %s" % (type(e).__name__, e))
        return None


def run_after_teardown(fn, out, ran):
    """fn(out, ran) when given; a fault lands in out["after_teardown_error"], never raised (the finally goes on)."""
    if fn is None:
        return
    try:
        fn(out, ran)
    except Exception as e:                               # noqa: BLE001 - the grade and the copy still run
        out["after_teardown_error"] = "%s: %s" % (type(e).__name__, e)


GRADE_KEY = "grade_e2"           # the key a new day session's record carries its grade under (grade_day)


def grade(out, key, fn):
    """out[key] = fn(out), else out[key + "_error"] (the controller re-grades the artifact)."""
    try:
        out[key] = fn(out)
    except Exception as e:                               # noqa: BLE001 - the controller re-grades the artifact
        out[key + "_error"] = "%s: %s" % (type(e).__name__, e)


def grade_day(out):
    """A new day session's grade: out["grade_e2"] = gates_e.grade_e2(out), else out["grade_e2_error"]."""
    grade(out, GRADE_KEY, GE.grade_e2)


# ================================================================ the boot
def boot_and_run(args, preboot, run_session, grade_fn, *, key, driver, artifact, profile, constants, grade_key, user,
                 budget_s, min_free_gb, after_teardown=None, repo=DS.REPO, wall=time.time):
    """A day driver's boot (the module docstring): `preboot()` -> (pre, ok); `run_session(xs, transport, prev, pre)`
    builds and runs the driver's Chain (its return is passed to `after_teardown(out, ran)`); `grade_fn(out)` writes
    out[grade_key]. Returns out."""
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import profile as pzt_profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402
    from agent.base.transport.files import FileTransport     # noqa: E402

    pre, ok = preboot()
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        line = session_line(pre.get("chain_checks") or {})
        if line:
            print(line)
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = pzt_profile.load(os.path.join(repo, profile))
    rec_fx = fx.load(args["fixture"])
    prev = load_prev(args["prev"])[0]
    run_id, run_dir = new_run_dir(key)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    ran = None
    out = DS.new_out()
    out["world_changes"]["restored"] = "fixture %s restored into the run dir" % args["fixture"]
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=user)
    xs.path = os.path.join(run_dir, artifact)
    out.update({"run_id": run_id, "session_key": key, "driver": driver, "user": user, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": constants,
                "chain": chain_record(args, prof.fixture, DL.C.git_say("rev-parse", "--short", "HEAD")),
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build"), "parent": rec_fx.get("parent"),
                            "session": rec_fx.get("session")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", "testing/agent/drivers/" + driver)})
    DS.memory_gate(xs, min_free_gb)
    xs.mem("preboot")
    xs.persist()
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [user], started, clients, holder,
                           make_client=DS.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[user])
            ran = run_session(xs, FileTransport(DL.state_dir(clients[user])), prev, pre)
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
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        run_after_teardown(after_teardown, out, ran)
        grade_fn(out)
        out["finished"] = True
        xs.persist()
        copy_run(xs, repo, run_id, run_dir, artifact)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "stop": out.get("stop"), "chain": out.get("chain"),
                      "report": (out.get(grade_key) or {}).get("report_lines"),
                      "next": next_steps(args, run_dir, xs.path),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out
