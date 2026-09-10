"""pzt command line: provision / boot / attach / run / spike."""
import argparse
import datetime
import os
import time

from . import doctor
from . import fixture as fx
from . import scenario
from . import spikes
from .paths import ADMIN_PW, ADMIN_USER, PZ_DIR, new_run_dir
from .server import Server
from .session import (Timeline, fault_reasons, hold, make_client, make_server, say, teardown,
                      write_report)


def parse_kv(items):
    out = {}
    for item in items or []:
        k, _, v = item.partition("=")
        out[k.strip()] = v.strip()
    return out


def cmd_provision(a):
    run_id, run_dir = new_run_dir("prov")
    tl = Timeline()
    say(f"run: {run_dir}")
    mods = [m for m in a.mods.split(";") if m]
    sandbox = dict({"Zombies": "6"}, **parse_kv(a.sandbox))   # 6 = none: a quiet test world
    server = make_server(run_dir, port=a.port, rcon_port=a.rcon_port, mods=mods, name=a.server_name,
                         sandbox=sandbox)
    clients = {}
    timings = {}
    ok = False
    try:
        tl.mark("server_launch")
        timings["server_start"] = server.start(timeout=a.server_timeout)
        tl.mark("server_started", build=server.build, t=timings["server_start"])
        for user in a.clients:
            c, _ = make_client(run_dir, user, server, debug=(user == ADMIN_USER), safemode=a.safemode,
                               launcher=a.launcher)
            c.start()
            tl.mark("client_launch", user=user)
            timings[f"client_{user}_ready"] = c.wait_ready(timeout=a.client_timeout)
            tl.mark("client_ready", user=user, t=timings[f"client_{user}_ready"])
            rc = c.quit()
            tl.mark("client_quit", user=user, rc=rc)
            clients[user] = c
        ok = True
    finally:
        for c in clients.values():
            c.kill()
        rc = server.stop()
        tl.mark("server_stopped", rc=rc, errors=len(server.errors))
    if not ok:
        return 1
    record = {
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "build": server.build, "game_dir": PZ_DIR, "provision_run": run_id,
        "server": {"name": server.name, "port": server.port, "rcon_port": server.rcon_port,
                   "mods": server.mods, "sandbox": sandbox, "admin_user": ADMIN_USER,
                   "admin_password": ADMIN_PW},
        "clients": {u: {"password": c.password, "debug": c.debug} for u, c in clients.items()},
        "timings": timings, "boot_errors": server.errors[:20],
    }
    record = fx.snapshot(a.name, server.cache, {u: c.cache for u, c in clients.items()}, record)
    tl.mark("snapshot", fixture=fx.fixture_dir(a.name), size_mb=record["size_mb"])
    write_report(run_dir, {"run_id": run_id, "timeline": tl.items, "record": record,
                           "clients": {u: c.events for u, c in clients.items()}})
    say(f"\nFIXTURE '{a.name}' built: {record['size_mb']} MB, build {server.build}, "
        f"{len(server.errors)} server error lines")
    return 0


def cmd_boot(a):
    rec = fx.load(a.fixture)
    run_id, run_dir = new_run_dir("boot")
    tl = Timeline()
    say(f"run: {run_dir}")
    server = make_server(run_dir, rec, port=a.port, rcon_port=a.rcon_port)
    tl.mark("server_launch", port=server.port)
    try:
        server.start(timeout=a.server_timeout)
        tl.mark("server_started", t=server.t_started, build=server.build)
        if rec.get("build") and server.build and server.build != rec["build"]:
            tl.mark("build_mismatch", fixture=rec["build"], installed=server.build)
        hold(a.hold, tl, server, [])
    finally:
        teardown(tl, server, [])
    write_report(run_dir, {"run_id": run_id, "timeline": tl.items, "server_errors": server.errors})
    return 1 if server.errors else 0


def cmd_attach(a):
    rec = fx.load(a.fixture)
    run_id, run_dir = new_run_dir("attach")
    tl = Timeline()
    say(f"run: {run_dir}")
    ip, port = a.server.split(":")
    stub = Server(os.path.join(run_dir, "server-stub"), port=port, mods=rec["server"]["mods"])
    c, restored = make_client(run_dir, a.user, stub, rec, safemode=a.safemode, launcher=a.launcher)
    c.start()
    tl.mark("client_launch", user=a.user, restored=restored)
    try:
        t = c.wait_ready(timeout=a.client_timeout)
        tl.mark("client_ready", t=t)
        tl.mark("ping", ack=c.send("ping"))
        end = time.time() + a.hold if a.hold > 0 else None
        while (end is None or time.time() < end) and c.alive:
            time.sleep(1)
    except KeyboardInterrupt:
        tl.mark("interrupted")
    finally:
        rc = c.quit()
        tl.mark("client_quit", rc=rc)
    write_report(run_dir, {"run_id": run_id, "timeline": tl.items, "events": c.events, "results": c.results()})
    return 0


def cmd_run(a):
    rec = fx.load(a.fixture)
    run_id, run_dir = new_run_dir("run")
    tl = Timeline()
    say(f"run: {run_dir}")
    users = a.clients or list(rec["clients"])
    server = make_server(run_dir, rec, port=a.port, rcon_port=a.rcon_port)
    clients = []
    result = "FAIL"
    try:
        tl.mark("server_launch", port=server.port)
        server.start(timeout=a.server_timeout)
        tl.mark("server_started", t=server.t_started, build=server.build)
        if rec.get("build") and server.build and server.build != rec["build"]:
            tl.mark("build_mismatch", fixture=rec["build"], installed=server.build)
        for user in users:
            c, restored = make_client(run_dir, user, server, rec, safemode=a.safemode, launcher=a.launcher)
            c.start()
            clients.append(c)
            tl.mark("client_launch", user=user, restored=restored)
            tl.mark("client_ready", user=user, t=c.wait_ready(timeout=a.client_timeout))
        tl.mark("ping", server=server.send("ping"), **{c.username: c.send("ping") for c in clients})
        tl.mark("session_ready", clients=len(clients))
        if hold(a.hold, tl, server, clients):
            result = "PASS"
    except (RuntimeError, TimeoutError) as e:
        tl.mark("error", detail=str(e))
    finally:
        try:
            teardown(tl, server, clients)
        finally:
            for c in clients:
                c.kill()
            server.kill()
    # The environment checks, shared with `pzt scenario` (session.fault_reasons): missing mods,
    # non-baseline server errors, client lua errors. They carry their own counts into the RESULT
    # line; a hold that already failed keeps its own reason and records these in the timeline.
    faults = fault_reasons(server, clients)
    if faults:
        tl.mark("faults", detail="; ".join(faults)[:200])
        if result == "PASS":
            result = "FAIL: " + "; ".join(faults)
    write_report(run_dir, {"run_id": run_id, "result": result, "faults": faults,
                           "timeline": tl.items, "server_errors": server.errors[:40],
                           "clients": {c.username: c.events for c in clients},
                           "results": {"server": server.results(),
                                       **{c.username: c.results() for c in clients}}})
    say(f"\nRESULT: {result}   (report: {os.path.join(run_dir, 'report.json')})")
    return 0 if result == "PASS" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pzt", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common_server(p):
        p.add_argument("--port", type=int, default=None, help="game port (default: fixture's / 27261)")
        p.add_argument("--rcon-port", type=int, default=None)
        p.add_argument("--server-timeout", type=int, default=420)

    def common_client(p):
        p.add_argument("--client-timeout", type=int, default=300)
        p.add_argument("--safemode", action="store_true", help="-safemode (GPU-less hosts; ~100 s slower)")
        p.add_argument("--launcher", choices=["java", "exe"], default="java")

    p = sub.add_parser("provision", help="build a golden fixture from scratch")
    p.add_argument("--name", default="default")
    p.add_argument("--server-name", default="pzt")
    p.add_argument("--mods", default="PZTestKit", help="semicolon-separated Mods= list")
    p.add_argument("--clients", default=[ADMIN_USER], type=lambda s: [u for u in s.split(",") if u],
                   help="comma-separated accounts to create characters for (admin gets -debug)")
    p.add_argument("--sandbox", action="append", metavar="KEY=VALUE",
                   help="SandboxVars override (default Zombies=6, i.e. none)")
    common_server(p)
    common_client(p)
    p.set_defaults(fn=cmd_provision, port=27261, rcon_port=27015)

    p = sub.add_parser("boot", help="restore a fixture's server and start it")
    p.add_argument("--fixture", default="default")
    p.add_argument("--hold", type=int, default=0, help="seconds to keep it up (0 = until Ctrl-C)")
    common_server(p)
    p.set_defaults(fn=cmd_boot)

    p = sub.add_parser("attach", help="restore a fixture's client and join a running server")
    p.add_argument("--fixture", default="default")
    p.add_argument("--server", default="127.0.0.1:27261")
    p.add_argument("--user", default=ADMIN_USER)
    p.add_argument("--hold", type=int, default=0)
    common_client(p)
    p.set_defaults(fn=cmd_attach)

    p = sub.add_parser("run", help="boot + attach every fixture client + hold + teardown")
    p.add_argument("--fixture", default="default")
    p.add_argument("--clients", default=None, type=lambda s: [u for u in s.split(",") if u])
    p.add_argument("--hold", type=int, default=5)
    common_server(p)
    common_client(p)
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("scenario", help="run one harness test on the fixture at accelerated time")
    p.add_argument("name", help="registered test name (see `test.list` on the chosen side)")
    p.add_argument("--fixture", default="default")
    p.add_argument("--side", choices=["server", "client"], default="server",
                   help="whose bus runs the test (default server: nutrition is server-authoritative)")
    p.add_argument("--user", default=ADMIN_USER, help="the test's subject; must be online")
    p.add_argument("--speed", type=int, default=30, help="settimespeed multiplier for the run")
    p.add_argument("--timeout", type=int, default=900, help="seconds to wait for the result doc")
    common_server(p)
    common_client(p)
    p.set_defaults(fn=scenario.run)

    p = sub.add_parser("spike", help="run design spikes (S3..S7) and write findings.json")
    p.add_argument("ids", nargs="+", help="e.g. S3 S4 S5 S6 S7")
    p.add_argument("--fixture", default="default")
    p.add_argument("--s3-client-timeout", type=int, default=90)
    p.add_argument("--reloadalllua", action="store_true", help="S7: also try the heavier reloadalllua")
    common_server(p)
    common_client(p)
    p.set_defaults(fn=spikes.run)

    p = sub.add_parser("doctor", help="cold-start checks; reports, never kills")
    p.set_defaults(fn=doctor.run)

    a = ap.parse_args(argv)
    return a.fn(a)
