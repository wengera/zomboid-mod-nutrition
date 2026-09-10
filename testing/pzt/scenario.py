"""pzt scenario <name>: run one harness test on the fixture session at accelerated time.

The test itself lives in the harness mod (shared/PZTestKit_Test.lua plus the scenario files
under server/scenarios/); this drives it end to end: boot the fixture's server, attach the
admin client, accelerate the world, start the test on the chosen side's bus, wait for its
result doc, evaluate it -- and only then, from a `finally`, put the clock back and tear the
session down, so an evaluator that raises cannot leave a 30x world behind. The report and the
artifact are written last, after teardown, because the environment verdict below needs the log
lines the server writes while it is stopping.

The RESULT is the harness test's own `pass`, AND the evaluator's ok, AND a clean session
(`session.fault_reasons`, shared with `pzt run`: no missing mods, no non-baseline server error
lines, no client Lua errors). A scenario writes committed evidence, so a green test on a
session that was throwing errors must not be reported as a pass.

--side defaults to SERVER because nutrition is server-authoritative (`Nutrition.update @42 L75`
is `!GameClient.client`, 03-notes Q7): a client-side scenario would drive a mirror that the
next PlayerStatsPacket overwrites. --side client is wired end to end for the convergence
readings, where the point IS the mirror, but no client-side scenario is registered yet, so it
currently has nothing to run. The client is attached either way -- the server resolves the
test's subject by username out of getOnlinePlayers(), so it has to be online.

--profile <name> (testing/profiles/<name>.toml) puts the scenario on a named mod set and
sandbox: the profile's fixture wins over --fixture, its first client is the subject unless
--user says otherwise, and a mod the server reports missing ends the run right after
server_started -- a scenario run on a mod that did not load is not evidence, and the client
and the test are ten minutes that need not be spent to find that out.
"""
import json
import os
import time
import traceback

from . import fixture as fx
from . import profile
from .bus import parse_ack
from .paths import ADMIN_USER, new_run_dir
from .session import (Timeline, check_mods_loaded, fault_reasons, make_client, make_server,
                      mark_profile, opt, say, teardown, write_report)

# name -> function(result_doc) -> (ok: bool, detail: dict). Filled by the scenario evaluator
# modules (slice 04 T3), which are imported at the bottom of this file.
EVALUATORS = {}


def evaluate(name, doc):
    fn = EVALUATORS.get(name)
    return fn(doc) if fn else (True, {})


def scalars(d):
    """Timeline marks are one printed line each: keep the scalars, leave the rest to the
    report."""
    return {k: v for k, v in (d or {}).items() if not isinstance(v, (list, dict))}


def cadence(doc):
    """The harness's own clock, measured: game-minute ticks vs the world clock vs the wall
    clock. ticks_per_world_min ~= 1 is the claim that Events.EveryOneMinute fires once per
    game minute on the side that ran the test -- everything scheduled in game minutes rests
    on it, so it is recorded on every run rather than assumed."""
    try:
        started, ended = float(doc["startedWall"]), float(doc["t"])
        world_min = (float(doc["endedWorldAge"]) - float(doc["startedWorldAge"])) * 60.0
        ticks = float(doc["gameMinutes"])
    except (KeyError, TypeError, ValueError):
        return {}
    wall_s = (ended - started) / 1000.0
    if not started or not ended or wall_s <= 0:
        return {}                       # no getTimestampMs() on this side: nothing to fit
    out = {"wall_s": round(wall_s, 1), "game_minutes": ticks,
           "ticks_per_wall_s": round(ticks / wall_s, 2),
           "world_min_per_wall_s": round(world_min / wall_s, 2)}
    if world_min > 0:
        out["ticks_per_world_min"] = round(ticks / world_min, 3)
        # Anything outside a few percent of 1.0 means the event did NOT fire once per game
        # minute -- ticks lost at a high multiplier, or counted twice by a double-registered
        # handler. Everything the tests schedule is in game minutes and every rate the
        # evaluators fit is per game hour, so the run is still reported, but flagged: the
        # numbers are being read off a clock that was not keeping time.
        if not 0.95 <= out["ticks_per_world_min"] <= 1.05:
            out["cadence_suspect"] = True
    return out


def write_artifact(run_dir, a, server, result, doc, ev, cad, faults=()):
    """The evidence file, written by the run itself: the result doc, the evaluation, and the
    fixture/build that produced them, in one JSON. testing/artifacts/ takes byte-for-byte copies
    of what a run wrote (its README), so composing this here rather than by hand afterwards is
    what keeps the committed evidence machine-written -- and carrying `fixture`/`build` inside it
    is what keeps it readable without the run report beside it (the gap flagged for the slice-02
    artifact). Everything else it needs is already on `a` or derivable from `run_dir`, which is
    named for the run id."""
    art = {"run_id": os.path.basename(os.path.normpath(run_dir)), "scenario": a.name,
           "fixture": a.fixture, "profile": a.profile, "build": server.build,
           "side": a.side, "user": a.user, "speed": a.speed, "result": result,
           "cadence": cad, "evaluation": ev, "faults": list(faults),
           "server_errors": server.errors[:20], "test": doc}
    path = os.path.join(run_dir, f"scenario-{a.name}.json")
    with open(path, "w") as fh:
        json.dump(art, fh, indent=1)
    return path


def run(a):
    # A profile is resolved and validated before anything starts (profile.py); its fixture wins
    # over --fixture (that is the fixture its sandbox keys were checked against) and its first
    # client is the test's subject unless --user says otherwise.
    prof = profile.load(a.profile) if a.profile else None
    flag = a.fixture                    # None unless --fixture was typed
    a.fixture = prof.fixture if prof else (flag or "default")
    a.user = a.user or (prof.users[0] if prof else ADMIN_USER)
    rec = fx.load(a.fixture)
    run_id, run_dir = new_run_dir("scenario")
    tl = Timeline()
    say(f"run: {run_dir}")
    if prof:
        mark_profile(tl, prof, flag)
    server = make_server(run_dir, rec, port=a.port, rcon_port=a.rcon_port,
                         mods=prof.mods if prof else None,
                         mod_sources=prof.sources if prof else None,
                         mod_skip=prof.skip if prof else (),
                         sandbox=prof.sandbox if prof else None)
    clients, result, doc, ev = [], "FAIL", None, {}
    tb = None                   # traceback of whatever ended the run early; goes in the report
    try:
        server.start(timeout=opt(a, prof, "server_timeout"))
        tl.mark("server_started", t=server.t_started, build=server.build)
        check_mods_loaded(tl, server)   # raises: a scenario on a mod that did not load is not
                                        # evidence, and the client is 35 s that need not be spent
        c, restored = make_client(run_dir, a.user, server, rec, safemode=opt(a, prof, "safemode"),
                                  launcher=opt(a, prof, "launcher"))
        c.start()
        clients.append(c)
        tl.mark("client_launch", user=a.user, restored=restored)
        tl.mark("client_ready", user=a.user, t=c.wait_ready(timeout=opt(a, prof, "client_timeout")))
        node = server if a.side == "server" else c
        ok_list, names = parse_ack(node.send("test.list"))
        if isinstance(names, dict) and not names:
            names = []          # TK.json writes an empty Lua table as {}: an empty registry
        # Without the ok flag an `err:...` body arrives here as a plain string, and both the
        # join and the membership test below then silently operate on its characters -- a test
        # whose name is a substring of the error message would look registered.
        if not ok_list or not isinstance(names, list):
            raise RuntimeError(f"test.list failed on the {a.side} side: {str(names)[:120]}")
        tl.mark("test_list", side=a.side, tests=",".join(names) or "none")
        if a.name not in names:
            raise RuntimeError(f"unknown test '{a.name}' on the {a.side} side; registered: {names}")
        ok, rep = server.rcon(f"settimespeed {a.speed}")
        tl.mark("settimespeed", x=a.speed, ok=ok, reply=str(rep)[:40])
        # A refused RCON (port shut, wrong password, server not listening yet) means the world
        # is still at 1x: a three-game-day test would then need three real days and the only
        # symptom would be the result timeout, ten wall minutes later with nothing to read. End
        # the run here, with the reason.
        if not ok:
            raise RuntimeError(f"settimespeed {a.speed} refused: {str(rep)[:120]} -- the world "
                               "is still at 1x, so the test cannot finish inside its timeout")
        t0 = time.time()
        ok_ack, ack = parse_ack(node.send("test.run", f"{a.name} {a.user}"))
        tl.mark("test_run", side=a.side, user=a.user, ack=ack)
        # "started" is the only ack that leads to a result doc; "unknown" / "already running X" /
        # "no online player X" would otherwise be paid for with the full result timeout.
        if not ok_ack or ack != "started":
            raise RuntimeError(f"test.run {a.name} refused: {ack}")
        doc = node.bus.wait_result(f"test_{a.name}", timeout=a.timeout, after=t0 - 0.2)
        tl.mark("test_result", passed=doc.get("pass"), game_minutes=doc.get("gameMinutes"),
                samples=len(doc.get("samples") or []), detail=str(doc.get("detail"))[:80])
        for line in (doc.get("failures") or [])[:10]:
            tl.mark("test_failure", detail=str(line)[:160])
        ok, ev = evaluate(a.name, doc)
        # Evaluator detail keys are scenario-authored, so they cannot be splatted blind:
        # `phase` collides with Timeline.mark's own parameter (TypeError, after the expensive
        # part of the run), `ok` with the flag below, and `t` would quietly overwrite the
        # timeline's own timestamp. Rename rather than drop -- the detail is evidence.
        marks = {"ok": ok}
        for k, v in scalars(ev).items():
            marks["ev_" + k if k in ("ok", "phase", "t") else k] = v
        tl.mark("evaluation", **marks)
        result = "PASS" if (doc.get("pass") and ok) else "FAIL"
    # Wider than the RuntimeError/TimeoutError the happy path raises: bus.send can raise
    # PermissionError (the command file swap losing to the game's reader), wait_result can
    # raise on a truncated JSON doc, and an evaluator is scenario code that can raise anything.
    # None of that may skip the finally below -- settimespeed is a world change and the clients
    # are real processes -- and all of it must still land in the report as an `error` mark with
    # result FAIL (exit 1). The one-line mark is for the console; the full traceback goes into
    # the report, because for an evaluator raise the line number IS the finding and the run
    # behind it cannot be re-run cheaply.
    except Exception as e:                     # noqa: BLE001 - see above
        tl.mark("error", detail=f"{type(e).__name__}: {e}"[:200])
        tb = traceback.format_exc()
    # Ctrl-C is caught rather than let through so that a run abandoned half way still leaves its
    # evidence: the finally below restores the clock and tears the session down either way, but
    # the report and artifact are written AFTER it, and an escaping KeyboardInterrupt would take
    # both with it -- ten wall minutes of live server with nothing to read. `session.hold` marks
    # an interrupt the same way (session.py:93). The run is FAIL: it is a partial run, whatever
    # the test had done by then. (An interrupt during teardown itself still escapes; the world
    # change is already undone by that point.)
    except KeyboardInterrupt:
        tl.mark("interrupted")
        result = "FAIL: interrupted"
    finally:
        # settimespeed is a WORLD change and must not outlive the run, whatever went wrong
        # above; and a failure to restore it must not skip the teardown that follows.
        try:
            if server.alive:
                ok, rep = server.rcon("settimespeed 1")
                tl.mark("settimespeed", x=1, ok=ok)
        except Exception as e:                     # noqa: BLE001 - teardown path, see above
            tl.mark("settimespeed_failed", detail=f"{type(e).__name__}: {e}"[:120])
        finally:
            try:
                teardown(tl, server, clients)
            finally:
                for c in clients:
                    c.kill()
                server.kill()
    # The same environment checks `pzt run` applies (session.fault_reasons), and for the same
    # reason: the harness `pass` flag and the evaluator only see what the test itself measured.
    # A mod that did not load, a non-baseline server error line or a client Lua error means the
    # run was not the run that was asked for -- and a scenario writes a COMMITTED artifact, so a
    # PASS on a session that was throwing errors would be evidence for a claim nobody checked.
    # Taken after teardown: the server's last log lines arrive while it is stopping.
    faults = fault_reasons(server, clients)
    if faults:
        tl.mark("faults", detail="; ".join(faults)[:200])
        if result == "PASS":
            result = "FAIL: " + "; ".join(faults)
    cad = cadence(doc or {})
    if cad:
        tl.mark("cadence", **cad)
        if cad.get("cadence_suspect"):
            say("  WARNING: EveryOneMinute did not fire once per game minute "
                f"({cad['ticks_per_world_min']} ticks/game-min) -- anything this run fitted "
                "against the game clock is suspect")
    # The report goes FIRST and unconditionally. It is the only record of the timeline -- and of
    # an `error` mark from the except above -- and the run behind it is ten wall minutes of live
    # server that cannot be re-run cheaply, so an artifact write that raises (a doc the encoder
    # chokes on, a full or read-only disk) must not take it with it. The artifact is a second
    # copy of what the report already holds, so it is written after, and its failure is a warning
    # rather than a lost run.
    report = {"run_id": run_id, "result": result, "side": a.side, "user": a.user,
              "speed": a.speed, "timeline": tl.items, "cadence": cad, "test": doc,
              "evaluation": ev, "faults": faults, "traceback": tb,
              "server_errors": server.errors[:20],
              "client_events": {c.username: c.events for c in clients}}
    if prof:                    # what was asked for AND what it resolved to (Profile.report)
        report["profile"] = prof.report()
    write_report(run_dir, report)
    try:
        write_artifact(run_dir, a, server, result, doc, ev, cad, faults)
    except Exception as e:                     # noqa: BLE001 - the report already landed
        say(f"  WARNING: artifact not written ({type(e).__name__}: {e}) -- "
            f"the run report in {run_dir} still has the result doc and the evaluation")
    say(f"\nRESULT: {result}   (report: {os.path.join(run_dir, 'report.json')})")
    return 0 if result == "PASS" else 1


# Evaluator modules register themselves in EVALUATORS on import. At the BOTTOM because
# scenarios_nutrition imports EVALUATORS from here: at the top this would be a cycle, and the
# name has to exist before the evaluator module is executed.
from . import scenarios_nutrition  # noqa: E402,F401  (import for side effect: EVALUATORS)
