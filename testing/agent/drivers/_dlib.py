"""Shared plumbing for the PZAgent drivers (Plan 21 Task 7): the memory gate, the client's state dir, the pre-boot
checks and the boot, on the x505 pattern (testing/experiments/x505_smoke.py preboot and main). Nothing here runs a
phase; a driver owns its own phases and grades."""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(TESTING)
for _p in (os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _common as C                                   # noqa: E402
import xlib                                           # noqa: E402
from pzt import profile                               # noqa: E402
from pzt import harness                               # noqa: E402
from pzt.session import attach_clients, make_server, verify   # noqa: E402
from agent.link import Link                           # noqa: E402

MIN_FREE_GB = 12.0
HARNESS_LUA = "testing/PZTestKit"


def wait_memory(min_gb=MIN_FREE_GB, max_wait_s=1800.0, poll_s=60.0, free=xlib.free_gb, sleep=time.sleep,
                clock=time.time):
    """Poll host free memory until it reaches `min_gb`; (ok, readings [{wall, free_gb}]). A reading that cannot be
    taken (None) counts as low. Gives up once `max_wait_s` has passed, every reading kept."""
    readings = []
    t0 = clock()
    while True:
        g = free()
        readings.append({"wall": clock(), "free_gb": g})
        if xlib.memory_ok(g, min_gb):
            return True, readings
        if clock() - t0 + poll_s > max_wait_s:
            return False, readings
        sleep(poll_s)


def state_dir(client):
    return os.path.join(client.cache, "Lua", "pzagent", client.username)


def clear_state_dir(client):
    """Remove a stale pzagent/ folder (the fixture snapshot copies the client's Lua/ folder)."""
    shutil.rmtree(os.path.join(client.cache, "Lua", "pzagent"), ignore_errors=True)


def preboot(me, profile_path):
    """Git provenance, doctor, harness-lua-dirty and the layout lint, as x505's preboot/main record them.
    Returns (the dict a driver stores under out["preboot"], ok)."""
    pre = {"driver": os.path.basename(me), "profile_path": profile_path,
           "profile": os.path.splitext(os.path.basename(profile_path))[0],
           "commit": C.git_say("rev-parse", "--short", "HEAD"),
           "harness_lua_commit": C.git_say("log", "-1", "--format=%h", "--", HARNESS_LUA),
           "harness_py_commit": C.git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
           "xlib_commit": C.git_say("log", "-1", "--format=%h", "--", "testing/experiments/xlib.py"),
           "agent_commit": C.git_say("log", "-1", "--format=%h", "--", "testing/agent", "testing/PZAgent")}
    pre["harness_lua_dirty"] = C.git_dirty(HARNESS_LUA)[0]
    pre["doctor_clean"], text = C.doctor()
    pre["doctor"] = text.strip().splitlines()
    try:
        prof = profile.load(profile_path)
        pre["lint_errors"] = harness.lint_paths(profile.lint_sources(prof, prof.sources))
    except SystemExit as e:                   # ProfileError and fixture errors are SystemExit
        pre["profile_error"] = str(e)
        pre["lint_errors"] = None
    ok = bool(pre["doctor_clean"]) and pre["harness_lua_dirty"] is False and pre["lint_errors"] == []
    return pre, ok


def boot(xs, prof, rec_fx, run_dir, users, started, clients, holder):
    """x505's boot: make_server, start, attach the clients, verify. Fills `holder["server"]`, `clients` and `started`
    in place; returns the out fields x505's main sets at that point."""
    out = {}
    server = make_server(run_dir, rec_fx, mods=prof.mods, mod_sources=prof.sources, mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini, gclog=prof.gclog)
    holder["server"] = server
    xs.server = server
    out["server_launch_wall"] = xs.wall()
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = xs.wall()
    out["server_pid"] = server.proc.pid
    xs.tl.mark("server_started", pid=server.proc.pid)
    clients.update(attach_clients(run_dir, prof, server, rec_fx, xs.tl, users=list(users), started=started))
    xs.tl.mark("session_ready")
    out["session_ready_wall"] = xs.wall()
    out["build"] = server.build
    out["verify"] = verify(prof, server, clients, xs.tl)
    return out


def bus_stats(xs, user):
    """The server's stats.all for `user`: the step's ack and the wall clock in epoch ms."""
    row = xs.step("stats", "server", "stats.all", user)
    return {"ack": row.get("ack"), "wallMs": time.time() * 1000}


def link_for(clients, user):
    return Link(state_dir(clients[user]))
