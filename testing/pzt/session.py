"""Shared plumbing for the CLI and the spikes: timelines, building servers/clients from a
fixture, holding a session open, tearing it down."""
import json
import os
import time

from . import fixture as fx
from .bus import parse_ack
from .client import Client
from .paths import ADMIN_PW, ADMIN_USER
from .profile import DEFAULTS as PROFILE_DEFAULTS
from .server import MOD_MISSING_RX, Server


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


def grep_file(path, rx, limit=10):
    """The matching lines of a log, stripped and capped -- evidence for a report. A log that
    is not there yet (or is being written) is no matches, not an error."""
    hits = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if rx.search(line):
                    hits.append(line.strip()[:200])
                    if len(hits) >= limit:
                        break
    except OSError:
        pass
    return hits


def opt(a, prof, name):
    """One run setting from three places: an explicit CLI flag wins, then the profile's own
    value, then the default.

    argparse cannot report whether a flag was typed, so "explicit" here means "differs from
    the default" -- and `profile.DEFAULTS` holds exactly these CLI defaults, so typing the
    default value is a no-op either way. Without a profile the flag is returned untouched.
    """
    given = getattr(a, name)
    if prof is None or given != PROFILE_DEFAULTS[name]:
        return given
    return getattr(prof, name)


def mark_profile(tl, prof, flag=None):
    """The first line of a profiled run: exactly which combination is under test.

    `flag` is the `--fixture` the caller typed (None when it did not). The profile's own
    fixture wins -- it is the fixture its sandbox keys were validated against -- so a
    conflicting flag is called out rather than silently dropped.
    """
    if flag and flag != prof.fixture:
        say(f"  [profile] --fixture {flag} ignored: profile '{prof.name}' names "
            f"fixture '{prof.fixture}'")
    return tl.mark("profile", name=prof.name, fixture=prof.fixture, mods=";".join(prof.mods),
                   sandbox=",".join(f"{k}={v}" for k, v in prof.sandbox.items()) or "none")


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


def check_mods_loaded(tl, server):
    """Fail the run the moment the server says a mod is missing -- before a client is paid for.

    The game's own reaction to a mod it cannot find is a WARN and a clean boot (spike S3-A):
    the session comes up, every probe answers, and the run looks green while the thing under
    test was never loaded. `fault_reasons` catches that at the end of the run; catching it
    here as well is purely about cost -- a broken profile stops at ~20 s instead of a minute
    of client boot plus the hold. The server's own line goes into the timeline verbatim,
    because "which mod, in whose words" is the whole finding.

    Raises RuntimeError, which every caller's except-path already turns into an `error` mark,
    a teardown and RESULT: FAIL.
    """
    missing = sorted(set(server.mods_not_found))
    if not missing:
        return
    tl.mark("mods_not_found", mods=",".join(missing))
    for line in grep_file(server.log_path, MOD_MISSING_RX, limit=5):
        tl.mark("mod_missing_line", detail=line)
    raise RuntimeError("mods not found at load: " + ",".join(missing))


def verify(prof, server, clients, tl):
    """Bus probes proving the mods took EFFECT, not merely that the server did not complain:
    a mod can be absent (S3-A) and the run still look clean. `expect` is matched as a
    substring of json.dumps(parsed ack).

    Returns the list of probes with their verdicts, for report.json; the caller owns the
    RESULT. A probe whose side has no node (a `client` probe on a session with no client)
    fails rather than raising -- the run has already paid for the session, so it reports.
    """
    out = []
    for v in prof.verify:
        side = v.get("side", "server")
        node = server if side == "server" else (clients[0] if clients else None)
        if node is None:
            tl.mark("verify", side=side, cmd=v["cmd"], ok=False, got="no client attached")
            out.append({**v, "ok": False, "got": None})
            continue
        ok, val = parse_ack(node.send(v["cmd"], v.get("args", "")))
        passed = bool(ok) and v.get("expect", "") in json.dumps(val)
        tl.mark("verify", side=side, cmd=v["cmd"], ok=passed, got=json.dumps(val)[:100])
        out.append({**v, "ok": passed, "got": val})
    return out


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
