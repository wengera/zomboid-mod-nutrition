"""pzt scenario <name>: run one harness test on the fixture session at accelerated time.

The test itself lives in the harness mod (shared/PZTestKit_Test.lua plus the scenario files
under server/scenarios/); this drives it end to end: boot the fixture's server, attach the
admin client, accelerate the world, start the test on the chosen side's bus, wait for its
result doc, put the clock back, tear down, evaluate, report.

--side defaults to SERVER because nutrition is server-authoritative (`Nutrition.update @42 L75`
is `!GameClient.client`, 03-notes Q7): a client-side scenario would drive a mirror that the
next PlayerStatsPacket overwrites. --side client is kept for the convergence readings, where
the point IS the mirror. The client is attached either way -- the server resolves the test's
subject by username out of getOnlinePlayers(), so it has to be online.
"""
import json
import os
import time

from . import fixture as fx
from .bus import parse_ack
from .paths import new_run_dir
from .session import Timeline, make_client, make_server, say, teardown, write_report

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


def write_artifact(run_dir, a, run_id, server, result, doc, ev, cad):
    """The evidence file, written by the run itself: the result doc, the evaluation, and the
    fixture/build that produced them, in one JSON. testing/artifacts/ takes byte-for-byte copies
    of what a run wrote (its README), so composing this here rather than by hand afterwards is
    what keeps the committed evidence machine-written -- and carrying `fixture`/`build` inside it
    is what keeps it readable without the run report beside it (the gap flagged for the slice-02
    artifact)."""
    art = {"run_id": run_id, "scenario": a.name, "fixture": a.fixture, "build": server.build,
           "side": a.side, "user": a.user, "speed": a.speed, "result": result,
           "cadence": cad, "evaluation": ev, "server_errors": server.errors[:20], "test": doc}
    path = os.path.join(run_dir, f"scenario-{a.name}.json")
    with open(path, "w") as fh:
        json.dump(art, fh, indent=1)
    return path


def run(a):
    rec = fx.load(a.fixture)
    run_id, run_dir = new_run_dir("scenario")
    tl = Timeline()
    say(f"run: {run_dir}")
    server = make_server(run_dir, rec, port=a.port, rcon_port=a.rcon_port)
    clients, result, doc, ev = [], "FAIL", None, {}
    try:
        server.start(timeout=a.server_timeout)
        tl.mark("server_started", t=server.t_started, build=server.build)
        c, restored = make_client(run_dir, a.user, server, rec, safemode=a.safemode,
                                  launcher=a.launcher)
        c.start()
        clients.append(c)
        tl.mark("client_launch", user=a.user, restored=restored)
        tl.mark("client_ready", user=a.user, t=c.wait_ready(timeout=a.client_timeout))
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
    # result FAIL (exit 1). KeyboardInterrupt/SystemExit are deliberately still let through:
    # the finally restores and tears down either way.
    except Exception as e:                     # noqa: BLE001 - see above
        tl.mark("error", detail=f"{type(e).__name__}: {e}"[:200])
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
    cad = cadence(doc or {})
    if cad:
        tl.mark("cadence", **cad)
        if cad.get("cadence_suspect"):
            say("  WARNING: EveryOneMinute did not fire once per game minute "
                f"({cad['ticks_per_world_min']} ticks/game-min) -- anything this run fitted "
                "against the game clock is suspect")
    write_artifact(run_dir, a, run_id, server, result, doc, ev, cad)
    write_report(run_dir, {"run_id": run_id, "result": result, "side": a.side, "user": a.user,
                           "speed": a.speed, "timeline": tl.items, "cadence": cad, "test": doc,
                           "evaluation": ev, "server_errors": server.errors[:20],
                           "client_events": {c.username: c.events for c in clients}})
    say(f"\nRESULT: {result}   (report: {os.path.join(run_dir, 'report.json')})")
    return 0 if result == "PASS" else 1


# Evaluator modules register themselves in EVALUATORS on import. At the BOTTOM because
# scenarios_nutrition imports EVALUATORS from here: at the top this would be a cycle, and the
# name has to exist before the evaluator module is executed.
from . import scenarios_nutrition  # noqa: E402,F401  (import for side effect: EVALUATORS)
