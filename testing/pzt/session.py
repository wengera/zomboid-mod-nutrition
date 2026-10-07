"""Shared plumbing for the CLI and the spikes: timelines, building servers/clients from a
fixture, holding a session open, tearing it down."""
import json
import os
import time

from . import fixture as fx
from . import profile
from .bus import UnknownSide, parse_ack, resolve_side
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

    def mark(self, phase, took=None, **kw):
        """One timeline entry. `t` is ALWAYS seconds since the timeline started -- it is the
        thing that makes a list of marks readable as a run.

        A step that also measured its own duration passes it as `took=`, which is stored beside
        `t` rather than over it. Before slice 07's final fix wave `server_started` and
        `client_ready` passed `t=<duration>` instead, so `t` on those two marks -- and only
        those two -- was the step's cost, not elapsed time: every artifact committed before that
        wave has to be read that way (`testing/artifacts/README.md`).
        """
        t = round(time.time() - self.t0, 1)
        detail = {**({} if took is None else {"took": took}), **kw}
        self.items.append({"t": t, "phase": phase, **detail})
        say(f"[{t:7.1f}s] {phase} " + " ".join(f"{k}={v}" for k, v in detail.items()))
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
    value, then `profile.DEFAULTS`.

    `run` and `scenario` clear these flags' argparse defaults to None (`cli.profile_defaults`),
    so None here means "not typed" -- which is the only way to tell a typed `--hold 5` from an
    untyped one. It used to mean "differs from the default", and a flag typed AT the default
    silently lost to the profile.

    The last fallback is `PROFILE_DEFAULTS`, not None: without it a plain `pzt run` would hand
    `hold=None` to `session.hold` and die on a TypeError inside the session it just paid a
    minute of boot for.
    """
    given = getattr(a, name, None)
    if given is not None:
        return given
    if prof is not None:
        return getattr(prof, name)
    return PROFILE_DEFAULTS[name]


def profile_args(a):
    """`--profile` and `--fixture`, settled once for both entry points.

    Loads the profile -- everything it names is resolved and validated before a process starts
    (profile.py) -- settles the fixture (the profile's own wins: it is the fixture its
    `[sandbox]` keys were checked against) and writes it back onto `a`, where the report and the
    scenario artifact read it. Returns `(profile|None, the --fixture the caller typed or None,
    the four make_server kwargs a profile supplies)`.

    `cli.cmd_run` and `scenario.run` held this block verbatim; one definition is what stops the
    two paths placing a different mod set (Task 3 review).
    """
    prof = profile.load(a.profile) if a.profile else None
    flag = a.fixture                    # None unless --fixture was typed
    a.fixture = prof.fixture if prof else (flag or "default")
    mods = {"mods": prof.mods if prof else None,
            "mod_sources": prof.sources if prof else None,
            "mod_skip": prof.skip if prof else (),
            "sandbox": prof.sandbox if prof else None, "ini": prof.ini if prof else None, **({"gclog": True} if prof is not None and getattr(prof, "gclog", False) else {})}
    return prof, flag, mods


def mark_profile(tl, prof, flag=None):
    """The first line of a profiled run: exactly which combination is under test.

    `flag` is the `--fixture` the caller typed (None when it did not). The profile's own
    fixture wins -- it is the fixture its sandbox keys were validated against -- so a
    conflicting flag is called out rather than silently dropped.
    """
    if flag and flag != prof.fixture:
        say(f"  [profile] --fixture {flag} ignored: profile '{prof.name}' names "
            f"fixture '{prof.fixture}'")
    # `skip` names the mods deliberately NOT placed (`copy = false`): harness.install drops them
    # from `missing_mods` on purpose, so this mark is the only place the run log says the later
    # `mods_not_found` was intended (Task 2 review).
    return tl.mark("profile", name=prof.name, fixture=prof.fixture, mods=";".join(prof.mods),
                   sandbox=",".join(f"{k}={v}" for k, v in prof.sandbox.items()) or "none",
                   skip=",".join(prof.skip) or "none")


def make_server(run_dir, rec=None, port=None, rcon_port=None, mods=None, name="pzt", sandbox=None,
                workshop=True, workshop_items=(), mod_sources=None, mod_skip=(), reuse=False, ini=None, gclog=False):
    """`mod_sources`/`mod_skip` come from a profile (see profile.py): a folder to copy in for
    a given mod id, and the ids named in Mods= that are deliberately not placed."""
    if rec:
        srv = rec["server"]
        if reuse:
            cache = os.path.join(run_dir, "server")
            if not os.path.isdir(os.path.join(cache, "Server")):
                raise SystemExit(f"make_server(reuse=True): {cache} holds no server cache to boot again; "
                                 "a reuse boot follows a first boot on the same run_dir")
        else:
            cache = fx.restore_server(rec["name"], run_dir)
        name, mods = srv["name"], mods or srv["mods"]
        port, rcon_port = port or srv["port"], rcon_port or srv["rcon_port"]
    else:
        cache = os.path.join(run_dir, "server")
    s = Server(cache, name=name, port=port, rcon_port=rcon_port, mods=mods,
               log_path=os.path.join(run_dir, "server-stdout.log"), echo=say,
               workshop=workshop, workshop_items=workshop_items,
               mod_sources=mod_sources, mod_skip=mod_skip)
    s.ini_overrides = dict(ini or {}); s.gclog = bool(gclog); s.seed(sandbox=sandbox)   # a profile's [server] ini keys and gclog flag
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
    fails rather than raising -- the run has already paid for the session, so it reports, and
    the mark and the report carry the same `got` so a reader comparing them finds no gap.

    `expect` is coerced with str(): TOML happily types it as an int or a bool, and `x in
    json.dumps(val)` on a non-string is a TypeError raised *after* the session was paid for,
    with no probe verdict in the report to explain it.
    """
    out = []
    for v in prof.verify:
        side = v.get("side", "server")
        node, why = verify_node(side, server, clients)     # "client" = admin; "client:<user>"
        if node is None:
            tl.mark("verify", side=side, cmd=v["cmd"], ok=False, got=why)
            out.append({**v, "ok": False, "got": why})
            continue
        ok, val = parse_ack(node.send(v["cmd"], v.get("args", "")))
        passed = bool(ok) and str(v.get("expect", "")) in json.dumps(val)
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


# ---- Plan 8 Task 1: more than one client --------------------------------------------------------
# Appended at the end of the file: the claims register holds `repo:` pointers into this file by
# line number, so new sites go here and the edits above keep every line where it was.

def verify_node(side, server, clients):
    """`(node, None)` for a `[[verify]]` row's side, or `(None, why)` when the side names no
    attached node -- a verdict for the row, never a raise (the session is already paid for).
    The pre-Plan-8 wording stays for a client row on a session with no client at all."""
    try:
        return resolve_side(side, server, clients), None
    except UnknownSide as e:
        return None, ("no client attached" if not clients else str(e))


def attach_clients(run_dir, prof, server, rec, tl, users=None, started=None, safemode=None,
                   launcher=None, timeout=None, make_client=None):
    """Launch each listed user in turn and wait for each to be ready before the next is
    launched (two clients booting together is unmeasured); return `{user: Client}` in order.

    `users` defaults to the profile's own list (`clients`, default `["admin"]`), and without a
    profile to the fixture's provisioned clients -- the lists `pzt run` always used. Each client
    is built by `make_client` from the fixture record, so it takes the record's own `debug` flag
    (fixture `two`: `admin` debug, `bob` release). `started` (a list) receives each client the
    moment it is launched, so a caller's teardown still reaches one whose wait raised. The
    three run settings fall back from the argument to the profile to `profile.DEFAULTS`.
    `make_client` is injectable because the CLI's tests stub the CLI's own name.
    """
    make = make_client or globals()["make_client"]
    if users is None:
        users = list(prof.users) if prof is not None else list(rec["clients"])

    def pick(given, name):
        if given is not None:
            return given
        return getattr(prof, name) if prof is not None else PROFILE_DEFAULTS[name]
    safemode, launcher = pick(safemode, "safemode"), pick(launcher, "launcher")
    timeout = pick(timeout, "client_timeout")
    out = {}
    for user in users:
        c, restored = make(run_dir, user, server, rec, safemode=safemode, launcher=launcher, **override_kw(prof, user, server))
        c.start()
        out[user] = c
        if started is not None:
            started.append(c)
        tl.mark("client_launch", user=user, restored=restored)
        tl.mark("client_ready", user=user, took=c.wait_ready(timeout=timeout))
    return out


# ---- Plan 10 Task S6: a per-client mod source override ------------------------------------------

def override_kw(prof, user, server):
    """`{}` unless the profile's `client_overrides` names `user`; then `{"mod_sources": ...}`, the
    server's own map with that user's folders laid over it (a fresh dict: the server's map and
    every other client's stay as they were). A profile without the key passes nothing extra, so
    every caller's `make_client` sees exactly the arguments it saw before."""
    table = (getattr(prof, "client_overrides", None) or {}).get(user) if prof is not None else None
    if not table:
        return {}
    return {"mod_sources": {**dict(getattr(server, "mod_sources", None) or {}), **table}}
