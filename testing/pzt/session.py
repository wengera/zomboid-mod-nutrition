"""Shared plumbing for the CLI and the spikes: timelines, building servers/clients from a
fixture, holding a session open, tearing it down."""
import json
import os
import time

from . import fixture as fx
from .client import Client
from .paths import ADMIN_PW, ADMIN_USER
from .server import Server


def say(msg):
    print(msg, flush=True)


class Timeline:
    def __init__(self):
        self.t0 = time.time()
        self.items = []

    def mark(self, phase, **kw):
        t = round(time.time() - self.t0, 1)
        self.items.append({"t": t, "phase": phase, **kw})
        say(f"[{t:7.1f}s] {phase} " + " ".join(f"{k}={v}" for k, v in kw.items()))
        return t


def client_password(user):
    return ADMIN_PW if user == ADMIN_USER else f"{user}-pw"


def write_report(run_dir, data):
    with open(os.path.join(run_dir, "report.json"), "w") as fh:
        json.dump(data, fh, indent=1)


def make_server(run_dir, rec=None, port=None, rcon_port=None, mods=None, name="pzt", sandbox=None,
                workshop=True, workshop_items=(), mod_sources=None, mod_skip=()):
    """`mod_sources`/`mod_skip` come from a profile (see profile.py): a folder to copy in for
    a given mod id, and the ids named in Mods= that are deliberately not placed."""
    if rec:
        cache = fx.restore_server(rec["name"], run_dir)
        srv = rec["server"]
        name, mods = srv["name"], mods or srv["mods"]
        port, rcon_port = port or srv["port"], rcon_port or srv["rcon_port"]
    else:
        cache = os.path.join(run_dir, "server")
    s = Server(cache, name=name, port=port, rcon_port=rcon_port, mods=mods,
               log_path=os.path.join(run_dir, "server-stdout.log"), echo=say,
               workshop=workshop, workshop_items=workshop_items,
               mod_sources=mod_sources, mod_skip=mod_skip)
    s.seed(sandbox=sandbox)
    if s.missing_mods:
        say(f"  [server] mods not placed in mods/: {s.missing_mods}")
    return s


def make_client(run_dir, user, server, rec=None, debug=None, safemode=False, launcher="java",
                workshop=True, mod_sources=None, mod_skip=None):
    """Restored from the fixture when it has a snapshot for this user (no creation
    screens); seeded fresh otherwise.

    The client's mod list already comes from `server.mods`, so its placement follows the
    server's too: both default to the server's own `mod_sources`/`mod_skip` (None = 'the
    server's', not 'none') and the two sides cannot drift apart."""
    mod_sources = server.mod_sources if mod_sources is None else mod_sources
    mod_skip = server.mod_skip if mod_skip is None else mod_skip
    restored = False
    info = {}
    if rec:
        cache, restored = fx.restore_client(rec["name"], user, run_dir)
        info = rec["clients"].get(user, {})
    else:
        cache = os.path.join(run_dir, "clients", user)
    if debug is None:
        debug = info.get("debug", user == ADMIN_USER)
    c = Client(cache, f"127.0.0.1:{server.port}", user, info.get("password") or client_password(user),
               debug=debug, safemode=safemode, launcher=launcher, mods=server.mods, echo=say,
               workshop=workshop, mod_sources=mod_sources, mod_skip=mod_skip)
    if restored:
        c.prepare()
    else:
        c.seed()
    if c.missing_mods:
        say(f"  [{user}] mods not placed in mods/: {c.missing_mods}")
    return c, restored


def hold(seconds, tl, server, clients):
    """Keep the session alive (the slot where test suites run). 0 = until Ctrl-C."""
    end = time.time() + seconds if seconds > 0 else None
    tl.mark("hold", seconds=seconds or "until-interrupt")
    try:
        while end is None or time.time() < end:
            if not server.alive:
                tl.mark("server_died", rc=server.proc.returncode)
                return False
            dead = [c.username for c in clients if not c.alive]
            if dead:
                tl.mark("client_died", users=",".join(dead))
                return False
            time.sleep(1)
    except KeyboardInterrupt:
        tl.mark("interrupted")
    return True


def fault_reasons(server, clients):
    """Environment faults that must fail a run whatever the run's own verdict said.

    Three of them, in the order a run hits them: a mod the game did not load (the session is
    not the session that was asked for), a server error line the vanilla-noise baseline did
    not account for (`server.py` classifies them: `self.errors` is already the non-baseline
    set), and a client that logged a Lua error (the harness on that side may have stopped
    answering the bus at any point after it).

    Shared by `pzt run` (`cli.cmd_run`) and `pzt scenario` (`scenario.run`) so the two
    verdicts cannot drift. It matters most for `scenario`: a test whose Lua raised somewhere
    the scheduler swallowed can still write `pass = true`, and that run's committed artifact
    must not say PASS. Call it AFTER teardown -- the last log lines land while the server is
    stopping.

    Returns a list of short reasons with their counts, most specific first; empty is clean.
    """
    out = []
    not_found = sorted(set(server.mods_not_found + [m for c in clients for m in c.mods_not_found]))
    if not_found:
        out.append("mods not found at load: " + ",".join(not_found))
    if server.errors:
        out.append(f"{len(server.errors)} server error lines")
    lua_errors = [c.username for c in clients if "lua_error" in c.seen]
    if lua_errors:
        out.append("lua errors on " + ",".join(lua_errors))
    return out


def teardown(tl, server, clients):
    for c in clients:
        if c.alive:
            rc = c.quit()
            tl.mark("client_quit", user=c.username, rc=rc)
    if server.alive:
        rc = server.stop()
        tl.mark("server_stopped", rc=rc, errors=len(server.errors))
