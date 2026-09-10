"""Pure-Python tests for the profile wiring in `pzt run` / `pzt scenario`: the verify probes,
the missing-mod fail-fast, the three-way option precedence, and one whole `cmd_run` driven
through stub processes. No game, no fixture blob, no java.
"""
import argparse, contextlib, json, os, re, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pytest
from pzt import cli, profile, scenario, session, spikes
from pzt import fixture as fx
from pzt.paths import HARNESS_MODS

# A profile that needs nothing installed: the harness mod is in the repo, and the workspace
# below supplies both the fixture record and the SandboxVars file the [sandbox] key is
# validated against.
KIT_PROFILE = """
fixture = "default"
description = "unit"
run = { hold = 33 }
verify = [ { side = "server", cmd = "trait.check", expect = '"loaded": true' } ]

[[mods]]
id = "PZTestKit"

[sandbox]
Zombies = 4
"""

SANDBOX = ("SandboxVars = {\r\n"
           "    VERSION = 6,\r\n"
           "    Zombies = 6,\r\n"
           "}\r\n")


class Stop(Exception):
    """Ends a CLI entry point where the test has seen everything it needs."""


def _write(path, text, newline=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text)
    return path


@contextlib.contextmanager
def workspace(toml=KIT_PROFILE, name="p", fixtures=("default", "other")):
    """A throwaway testing/profiles + testing/fixtures pair (same trick as test_profile.py),
    so the CLI resolves both without touching the repo's own machine-local fixture cache."""
    with tempfile.TemporaryDirectory() as d:
        profiles, fixdir = os.path.join(d, "profiles"), os.path.join(d, "fixtures")
        _write(os.path.join(profiles, f"{name}.toml"), toml, newline=None)
        for f in fixtures:
            _write(os.path.join(fixdir, f, "cache", "server", "Server", "pzt_SandboxVars.lua"),
                   SANDBOX)
            _write(os.path.join(fixdir, f, "fixture.json"),
                   json.dumps({"name": f, "build": "42.20.4",
                               "server": {"name": "pzt", "mods": ["PZTestKit"]},
                               "clients": {"admin": {}}}), newline=None)
        old = (profile.PROFILES, fx.FIXTURES)
        profile.PROFILES, fx.FIXTURES = profiles, fixdir
        try:
            yield d
        finally:
            profile.PROFILES, fx.FIXTURES = old


class Node:
    """A server or client stub for the bus probes: canned ack strings, one per command."""

    def __init__(self, acks=None, name="server"):
        self.acks, self.username, self.sent = acks or {}, name, []

    def send(self, cmd, args="", **kw):
        self.sent.append((cmd, args))
        return self.acks.get(cmd, "err:unknown command")


def prof_with(verify):
    return argparse.Namespace(verify=verify)


# ---- verify(): the probes that prove a mod took effect ------------------------------------

def test_verify_pass_fail_and_error():
    """Three replies, three verdicts: the expected substring present, absent, and an err:."""
    server = Node({"trait.check": 'ok:{"loaded": true}', "other.check": 'ok:{"loaded": false}'})
    tl = session.Timeline()
    prof = prof_with([{"cmd": "trait.check", "expect": '"loaded": true'},
                      {"cmd": "other.check", "expect": '"loaded": true'},
                      {"cmd": "nope", "expect": ""}])
    out = session.verify(prof, server, [], tl)
    assert [v["ok"] for v in out] == [True, False, False]
    assert out[0]["got"] == {"loaded": True}
    # an err: body is still recorded -- what the harness said is the finding
    assert out[2]["got"] == "unknown command"
    marks = [m for m in tl.items if m["phase"] == "verify"]
    assert [m["cmd"] for m in marks] == ["trait.check", "other.check", "nope"]
    assert [m["ok"] for m in marks] == [True, False, False]
    assert marks[0]["side"] == "server"          # the default side


def test_verify_expect_is_a_substring_of_the_dumped_value():
    """A dict ack is matched against json.dumps, so an `expect` written as a JSON fragment
    hits whatever nesting the harness answered with."""
    server = Node({"stats": 'ok:{"a": 1, "nested": {"keen": true}}'})
    prof = prof_with([{"cmd": "stats", "expect": '"keen": true'}])
    assert session.verify(prof, server, [], session.Timeline())[0]["ok"] is True


def test_verify_no_expect_passes_on_any_ok():
    server = Node({"ping": "ok:pong"})
    assert session.verify(prof_with([{"cmd": "ping"}]), server, [], session.Timeline())[0]["ok"]


def test_verify_client_side_uses_the_first_client():
    server, client = Node({"trait.check": "ok:server"}), Node({"trait.check": "ok:client"}, "admin")
    prof = prof_with([{"side": "client", "cmd": "trait.check", "expect": "client"},
                      {"side": "server", "cmd": "trait.check", "args": "x", "expect": "server"}])
    out = session.verify(prof, server, [client], session.Timeline())
    assert [v["ok"] for v in out] == [True, True]
    assert client.sent == [("trait.check", "")] and server.sent == [("trait.check", "x")]


def test_verify_client_side_without_a_client_fails_rather_than_raising():
    """The mark and the report say the same thing: a reader comparing the two finds no gap."""
    prof = prof_with([{"side": "client", "cmd": "trait.check"}])
    tl = session.Timeline()
    out = session.verify(prof, Node(), [], tl)
    assert out[0]["ok"] is False
    assert out[0]["got"] == tl.items[0]["got"] == "no client attached"


def test_verify_coerces_a_non_string_expect_instead_of_raising():
    """`x in json.dumps(val)` on a non-string is a TypeError raised after the session was paid
    for, with no verdict in the report to explain it. A number round-trips; the loader rejects
    the one shape that cannot (a TOML boolean)."""
    server = Node({"num": 'ok:{"n": 12}', "flag": 'ok:{"on": true}'})
    out = session.verify(prof_with([{"cmd": "num", "expect": 12},
                                    {"cmd": "flag", "expect": True}]), server, [], session.Timeline())
    assert [v["ok"] for v in out] == [True, False]      # "12" matches; "True" is not "true"


# ---- check_mods_loaded(): the fail-fast right after server_started ------------------------

class FakeBus:
    """`node.bus.wait_result` for the scenario path: one canned result doc."""

    def __init__(self, doc=None):
        self.doc = doc if doc is not None else {"pass": True, "detail": "ok", "gameMinutes": 20}

    def wait_result(self, name, timeout=None, after=None):
        return self.doc


class FakeServer:
    """The parts of Server the run path touches, with no process behind them."""

    def __init__(self, log_path, mods_not_found=(), acks=None, doc=None):
        self.log_path, self.mods_not_found = log_path, list(mods_not_found)
        self.acks = dict({"ping": "ok:pong", "trait.check": 'ok:{"loaded": true}',
                          "test.list": 'ok:["smoke_clock"]', "test.run": "ok:started"},
                         **(acks or {}))
        self.errors, self.build, self.port = [], "42.20.4", 27261
        self.t_started, self.alive, self.mods = 1.0, True, ["PZTestKit"]
        self.bus = FakeBus(doc)
        self.rcons = []
        self.sent = []

    def rcon(self, cmd):
        self.rcons.append(cmd)
        return True, "ok"

    def start(self, timeout=None):
        return self.t_started

    def send(self, cmd, args="", **kw):
        self.sent.append((cmd, args))
        return self.acks.get(cmd, "err:unknown command")

    def stop(self):
        self.alive = False
        return 0

    def kill(self):
        self.alive = False

    def results(self):
        return {}


class FakeClient:
    def __init__(self, user):
        self.username, self.events, self.seen, self.mods_not_found = user, [], set(), []
        self.alive = True

    def start(self):
        pass

    def wait_ready(self, timeout=None):
        return 2.0

    def send(self, cmd, args="", **kw):
        return "ok:pong"

    def quit(self):
        self.alive = False
        return 0

    def kill(self):
        self.alive = False

    def results(self):
        return {}


WARN = ('WARN  : General     , 1757475000000> ZomboidFileSystem.loadModAndRequired> '
        'required mod "NoSuchModHere" not found\n')


def test_check_mods_loaded_is_silent_on_a_clean_boot(tmp_path):
    tl = session.Timeline()
    session.check_mods_loaded(tl, FakeServer(str(tmp_path / "no.log")))
    assert tl.items == []


def test_check_mods_loaded_raises_and_quotes_the_server_line(tmp_path):
    log = _write(str(tmp_path / "server-stdout.log"), "boot\n" + WARN + "SERVER STARTED\n")
    tl = session.Timeline()
    with pytest.raises(RuntimeError) as e:
        session.check_mods_loaded(tl, FakeServer(log, ["NoSuchModHere"]))
    assert str(e.value) == "mods not found at load: NoSuchModHere"
    assert [m["phase"] for m in tl.items] == ["mods_not_found", "mod_missing_line"]
    assert tl.items[0]["mods"] == "NoSuchModHere"
    assert 'required mod "NoSuchModHere" not found' in tl.items[1]["detail"]


def test_check_mods_loaded_names_a_repeated_mod_once(tmp_path):
    """The server reader appends a line per WARN; the raise (and the mark) must not repeat it,
    because session.fault_reasons names the same set again at the end of the run."""
    log = _write(str(tmp_path / "s.log"), WARN * 3)
    with pytest.raises(RuntimeError) as e:
        session.check_mods_loaded(session.Timeline(),
                                  FakeServer(log, ["NoSuchModHere", "NoSuchModHere"]))
    assert str(e.value) == "mods not found at load: NoSuchModHere"


def test_check_mods_loaded_survives_a_log_that_is_not_there(tmp_path):
    with pytest.raises(RuntimeError):
        session.check_mods_loaded(session.Timeline(), FakeServer(str(tmp_path / "gone.log"), ["X"]))


def test_grep_file_has_one_definition(tmp_path):
    """It moved to session.py for the fail-fast; spikes.py re-exports the same object."""
    assert spikes.grep_file is session.grep_file
    log = _write(str(tmp_path / "s.log"), WARN * 8)
    assert len(session.grep_file(log, re.compile(r"not found"), limit=5)) == 5


# ---- opt(): typed flag > profile > profile.DEFAULTS -----------------------------------------

KEYS = ("hold", "launcher", "safemode", "server_timeout", "client_timeout")


def test_opt_prefers_a_typed_flag_then_the_profile_then_the_default():
    prof = argparse.Namespace(hold=33, launcher="exe", safemode=True, server_timeout=99,
                              client_timeout=88)
    untyped = argparse.Namespace(**{k: None for k in KEYS})
    assert [session.opt(untyped, prof, k) for k in KEYS] == [33, "exe", True, 99, 88]
    assert [session.opt(untyped, None, k) for k in KEYS] == [profile.DEFAULTS[k] for k in KEYS]
    typed = argparse.Namespace(hold=7, launcher="java", safemode=False, server_timeout=1,
                               client_timeout=2)
    assert [session.opt(typed, prof, k) for k in KEYS] == [7, "java", False, 1, 2]
    assert [session.opt(typed, None, k) for k in KEYS] == [7, "java", False, 1, 2]


def test_a_flag_typed_at_its_own_default_still_beats_the_profile():
    """The bug the None defaults fix: `--hold 5` is 5 because it was asked for, and argparse
    cannot say so -- so `run`/`scenario` clear the default and None means 'not given'."""
    prof = argparse.Namespace(hold=33, launcher="exe", safemode=True, server_timeout=99,
                              client_timeout=88)
    assert session.opt(argparse.Namespace(hold=5), prof, "hold") == 5
    assert session.opt(argparse.Namespace(hold=None), prof, "hold") == 33


def test_run_and_scenario_clear_these_defaults_so_none_means_not_given(monkeypatch):
    """`profile_defaults` runs after the common_* helpers, so it rewrites their defaults; every
    other subparser keeps its concrete ones (they never consult a profile)."""
    seen = {}
    monkeypatch.setattr(cli, "cmd_run", lambda a: seen.update(vars(a)))
    cli.main(["run"])                                  # set_defaults(fn=...) reads the global
    assert {k: seen[k] for k in profile.DEFAULTS} == {k: None for k in profile.DEFAULTS}
    seen.clear()
    monkeypatch.setattr(scenario, "run", lambda a: seen.update(vars(a)))
    cli.main(["scenario", "smoke_clock"])
    assert {k: seen[k] for k in profile.DEFAULTS} == {k: None for k in profile.DEFAULTS}
    seen.clear()
    monkeypatch.setattr(cli, "cmd_attach", lambda a: seen.update(vars(a)))
    cli.main(["attach"])
    assert (seen["client_timeout"], seen["launcher"], seen["safemode"]) == (300, "java", False)


def test_a_plain_run_falls_back_to_profile_defaults_not_none(monkeypatch, tmp_path):
    """B4(b): with no flag and no profile, `opt` must reach profile.DEFAULTS -- `hold=None`
    would reach `session.hold` and raise a TypeError inside a session already paid for."""
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_run(monkeypatch, tmp_path, server) as made:
        a = argparse.Namespace(profile=None, fixture=None, clients=None, port=None,
                               rcon_port=None, **{k: None for k in profile.DEFAULTS})
        assert cli.cmd_run(a) == 0
    assert made["hold"] == profile.DEFAULTS["hold"] == 5
    assert made["clients"][0][1] == {"safemode": False, "launcher": "java"}
    assert isinstance(made["hold"], int)


# ---- the CLI surface ------------------------------------------------------------------------

def test_run_and_scenario_report_a_missing_profile_and_start_nothing():
    for argv in (["run", "--profile", "nope"], ["scenario", "smoke_clock", "--profile", "nope"]):
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        msg = str(e.value)
        assert msg.startswith("profile 'nope' not found") and "nope.toml" in msg
        assert "have:" in msg          # the profiles dir need not exist yet (Task 4 creates it)


def test_only_run_and_scenario_take_a_profile(capsys):
    for cmd in ("boot", "attach", "spike"):
        argv = [cmd, "--profile", "x"] if cmd != "spike" else [cmd, "S3", "--profile", "x"]
        with pytest.raises(SystemExit) as e:
            cli.main(argv)
        assert e.value.code == 2               # argparse: unrecognized arguments
        capsys.readouterr()


def test_profile_fixture_wins_over_the_flag(monkeypatch):
    """The profile's fixture is the one its [sandbox] keys were validated against."""
    monkeypatch.setattr(cli, "new_run_dir", lambda p: (_ for _ in ()).throw(Stop()))
    with workspace():
        a = argparse.Namespace(profile="p", fixture="other")
        with pytest.raises(Stop):
            cli.cmd_run(a)
        assert a.fixture == "default"           # resolved in place, for the report/artifact
        b = argparse.Namespace(profile=None, fixture="other")
        with pytest.raises(Stop):
            cli.cmd_run(b)
        assert b.fixture == "other"             # no profile: the flag, untouched
        c = argparse.Namespace(profile=None, fixture=None)
        with pytest.raises(Stop):
            cli.cmd_run(c)
        assert c.fixture == "default"           # nothing given: the old default


def test_scenario_user_defaults_to_the_profiles_first_client(monkeypatch):
    monkeypatch.setattr(scenario, "new_run_dir", lambda p: (_ for _ in ()).throw(Stop()))
    # bare keys must precede the first table header, so this one is written out in full
    toml = 'fixture = "default"\nclient = { users = ["tester", "second"] }\n\n[[mods]]\nid = "PZTestKit"\n'
    with workspace(toml=toml):
        a = argparse.Namespace(profile="p", fixture=None, user=None)
        with pytest.raises(Stop):
            scenario.run(a)
        assert a.user == "tester"
        b = argparse.Namespace(profile="p", fixture=None, user="typed")
        with pytest.raises(Stop):
            scenario.run(b)
        assert b.user == "typed"
        c = argparse.Namespace(profile=None, fixture=None, user=None)
        with pytest.raises(Stop):
            scenario.run(c)
        assert c.user == "admin"


def test_mark_profile_prints_the_combination_and_flags_a_conflicting_fixture(capsys):
    prof = argparse.Namespace(name="mod-under-test", fixture="default", mods=["PZTestKit", "Keen"],
                              sandbox={"DayLength": 1}, skip=("Ghost",))
    session.mark_profile(session.Timeline(), prof, "other")
    out = capsys.readouterr().out
    assert "--fixture other ignored" in out
    assert ("profile name=mod-under-test fixture=default mods=PZTestKit;Keen "
            "sandbox=DayLength=1 skip=Ghost") in out
    session.mark_profile(session.Timeline(),
                         argparse.Namespace(**dict(vars(prof), sandbox={}, skip=())), "default")
    out = capsys.readouterr().out
    assert "sandbox=none" in out and "skip=none" in out and "ignored" not in out


# ---- one whole cmd_run, on stub processes ---------------------------------------------------

def run_args(**kw):
    """A parsed `pzt run` Namespace with nothing typed: the five profile-backed flags default
    to None (`cli.profile_defaults`), which is what lets the profile's own values through."""
    a = argparse.Namespace(profile="p", fixture=None, clients=None, port=None, rcon_port=None,
                           **{k: None for k in profile.DEFAULTS})
    return argparse.Namespace(**dict(vars(a), **kw))


@contextlib.contextmanager
def stub_run(monkeypatch, tmp_path, server):
    """cmd_run with make_server/make_client/hold replaced: everything but the processes."""
    made = {"server_kw": None, "clients": [], "hold": None}

    def fake_make_server(run_dir, rec=None, **kw):
        made["server_kw"], made["rec"] = kw, rec
        return server

    def fake_make_client(run_dir, user, srv, rec=None, **kw):
        made["clients"].append((user, kw))
        return FakeClient(user), True

    def fake_hold(seconds, tl, srv, clients):
        made["hold"] = seconds
        tl.mark("hold", seconds=seconds)
        return True
    monkeypatch.setattr(cli, "new_run_dir", lambda p: ("unit", str(tmp_path)))
    monkeypatch.setattr(cli, "make_server", fake_make_server)
    monkeypatch.setattr(cli, "make_client", fake_make_client)
    monkeypatch.setattr(cli, "hold", fake_hold)
    yield made


def report_of(tmp_path):
    with open(os.path.join(str(tmp_path), "report.json")) as fh:
        return json.load(fh)


def test_cmd_run_with_a_profile_threads_it_everywhere(monkeypatch, tmp_path, capsys):
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_run(monkeypatch, tmp_path, server) as made:
        assert cli.cmd_run(run_args()) == 0
    kw = made["server_kw"]
    assert kw["mods"] == ["PZTestKit"] and kw["sandbox"] == {"Zombies": 4}
    assert kw["mod_sources"] == {"PZTestKit": HARNESS_MODS["PZTestKit"]} and kw["mod_skip"] == ()
    assert [u for u, _ in made["clients"]] == ["admin"]      # the profile's own users
    assert made["hold"] == 33                                # run = { hold = 33 }
    rep = report_of(tmp_path)
    assert rep["result"] == "PASS" and rep["faults"] == []
    assert rep["profile"]["name"] == "p" and rep["profile"]["mods"] == ["PZTestKit"]
    assert rep["profile"]["sandbox"] == {"Zombies": 4} and rep["profile"]["sources"] == kw["mod_sources"]
    assert rep["verify"] == [{"side": "server", "cmd": "trait.check", "expect": '"loaded": true',
                              "ok": True, "got": {"loaded": True}}]
    phases = [m["phase"] for m in rep["timeline"]]
    assert phases[0] == "profile" and "verify" in phases
    assert phases.index("verify") == phases.index("session_ready") + 1 < phases.index("hold")
    assert "RESULT: PASS" in capsys.readouterr().out


def test_cmd_run_without_a_profile_is_unchanged(monkeypatch, tmp_path, capsys):
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_run(monkeypatch, tmp_path, server) as made:
        assert cli.cmd_run(run_args(profile=None)) == 0
    assert made["server_kw"] == {"port": None, "rcon_port": None, "mods": None,
                                 "mod_sources": None, "mod_skip": (), "sandbox": None}
    assert [u for u, _ in made["clients"]] == ["admin"]      # the fixture's own clients
    assert made["hold"] == 5                                 # the CLI default
    rep = report_of(tmp_path)
    assert rep["result"] == "PASS"
    assert "profile" not in rep and "verify" not in rep      # the old report keys, exactly
    assert [m["phase"] for m in rep["timeline"]][0] == "server_launch"


def test_cmd_run_fails_the_verify_probe_and_skips_the_hold(monkeypatch, tmp_path, capsys):
    """The probes run before the hold so the test slot never opens on the wrong session --
    which only holds if a failed probe actually skips it."""
    server = FakeServer(str(tmp_path / "server-stdout.log"),
                        acks={"ping": "ok:pong", "trait.check": 'ok:{"loaded": false}'})
    with workspace(), stub_run(monkeypatch, tmp_path, server) as made:
        assert cli.cmd_run(run_args()) == 1
    assert made["hold"] is None                              # the 33 s slot never opened
    rep = report_of(tmp_path)
    assert rep["result"] == "FAIL: verify trait.check" and rep["verify"][0]["ok"] is False
    phases = [m["phase"] for m in rep["timeline"]]
    assert "verify" in phases and "hold" not in phases
    assert "RESULT: FAIL: verify trait.check" in capsys.readouterr().out


def test_the_timeline_keeps_step_durations_under_took_and_t_stays_elapsed(monkeypatch, tmp_path):
    """`server_started` / `client_ready` carry their own cost in `took`; `t` is elapsed on
    every mark, as it always was on all the others. Artifacts written before slice 07's final
    fix wave have the duration in `t` on exactly those two marks."""
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_run(monkeypatch, tmp_path, server):
        assert cli.cmd_run(run_args()) == 0
    marks = {m["phase"]: m for m in report_of(tmp_path)["timeline"]}
    assert marks["server_started"]["took"] == 1.0        # FakeServer.t_started
    assert marks["client_ready"]["took"] == 2.0          # FakeClient.wait_ready
    assert all(m["t"] <= marks["server_stopped"]["t"] for m in marks.values())
    assert not any("took" in m for p, m in marks.items()
                   if p not in ("server_started", "client_ready"))


def test_cmd_run_fails_fast_on_a_mod_the_server_did_not_load(monkeypatch, tmp_path, capsys):
    log = _write(str(tmp_path / "server-stdout.log"), WARN)
    server = FakeServer(log, ["NoSuchModHere"])
    with workspace(), stub_run(monkeypatch, tmp_path, server) as made:
        assert cli.cmd_run(run_args()) == 1
    assert made["clients"] == [] and made["hold"] is None    # nothing was paid for
    rep = report_of(tmp_path)
    phases = [m["phase"] for m in rep["timeline"]]
    assert phases == ["profile", "server_launch", "server_started", "mods_not_found",
                      "mod_missing_line", "error", "server_stopped", "faults"]
    assert rep["faults"] == ["mods not found at load: NoSuchModHere"]
    out = capsys.readouterr().out
    # The fail-fast and fault_reasons name the same mod; the RESULT line carries it ONCE, and
    # names it -- a bare `FAIL` would make the console say only that something went wrong.
    assert rep["result"] == "FAIL: mods not found at load: NoSuchModHere"
    assert "RESULT: FAIL: mods not found at load: NoSuchModHere   (report:" in out
    assert out.count("RESULT:") == 1
    # mods_not_found, the server's WARN line, error, faults, and the RESULT line itself
    assert out.count("NoSuchModHere") == 5
    error = next(m for m in rep["timeline"] if m["phase"] == "error")
    assert error["detail"] == "RuntimeError: mods not found at load: NoSuchModHere"


# ---- one whole scenario.run, on stub processes ----------------------------------------------

def scenario_args(**kw):
    """A parsed `pzt scenario` Namespace: the same five flags default to None."""
    a = argparse.Namespace(name="smoke_clock", profile="p", fixture=None, user=None, side="server",
                           speed=30, timeout=900, port=None, rcon_port=None,
                           **{k: None for k in profile.DEFAULTS})
    return argparse.Namespace(**dict(vars(a), **kw))


@contextlib.contextmanager
def stub_scenario(monkeypatch, tmp_path, server):
    """scenario.run with make_server/make_client replaced: everything but the processes."""
    made = {"server_kw": None, "clients": []}

    def fake_make_server(run_dir, rec=None, **kw):
        made["server_kw"] = kw
        return server

    def fake_make_client(run_dir, user, srv, rec=None, **kw):
        made["clients"].append((user, kw))
        return FakeClient(user), True
    monkeypatch.setattr(scenario, "new_run_dir", lambda p: ("unit", str(tmp_path)))
    monkeypatch.setattr(scenario, "make_server", fake_make_server)
    monkeypatch.setattr(scenario, "make_client", fake_make_client)
    yield made


def artifact_of(tmp_path, name="smoke_clock"):
    with open(os.path.join(str(tmp_path), f"scenario-{name}.json")) as fh:
        return json.load(fh)


def test_scenario_run_with_a_profile_threads_it_everywhere(monkeypatch, tmp_path, capsys):
    """The four make_server kwargs, the profile block in the report, and the RESOLVED profile
    name in the artifact -- `session.profile_args` is the single definition both paths use."""
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_scenario(monkeypatch, tmp_path, server) as made:
        assert scenario.run(scenario_args()) == 0
    kw = made["server_kw"]
    assert kw["mods"] == ["PZTestKit"] and kw["sandbox"] == {"Zombies": 4}
    assert kw["mod_sources"] == {"PZTestKit": HARNESS_MODS["PZTestKit"]} and kw["mod_skip"] == ()
    rep, art = report_of(tmp_path), artifact_of(tmp_path)
    assert rep["result"] == "PASS" and rep["profile"]["name"] == "p"
    assert art["profile"] == rep["profile"]["name"] == "p"   # resolved, not the raw token
    assert art["fixture"] == "default" and art["result"] == "PASS"
    assert server.rcons == ["settimespeed 30", "settimespeed 1"]
    assert "RESULT: PASS" in capsys.readouterr().out


def test_scenario_run_runs_the_profiles_verify_probes_after_client_ready(monkeypatch, tmp_path):
    """The gap slice 07 shipped with: a scenario artifact evidenced that the mods LOADED, never
    that they took effect. The probes run between `client_ready` and `test_list`."""
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_scenario(monkeypatch, tmp_path, server):
        assert scenario.run(scenario_args()) == 0
    rep, art = report_of(tmp_path), artifact_of(tmp_path)
    assert rep["verify"] == art["verify"] == [
        {"side": "server", "cmd": "trait.check", "expect": '"loaded": true',
         "ok": True, "got": {"loaded": True}}]
    phases = [m["phase"] for m in rep["timeline"]]
    assert phases.index("client_ready") < phases.index("verify") < phases.index("test_list")


def test_scenario_run_folds_a_failed_probe_in_after_the_test_has_run(monkeypatch, tmp_path, capsys):
    """A failed probe does NOT stop the run -- the ten minutes are already spent and the
    evidence is worth writing -- but the verdict says the numbers may not be cited."""
    server = FakeServer(str(tmp_path / "server-stdout.log"),
                        acks={"trait.check": 'ok:{"loaded": false}'})
    with workspace(), stub_scenario(monkeypatch, tmp_path, server):
        assert scenario.run(scenario_args()) == 1
    rep, art = report_of(tmp_path), artifact_of(tmp_path)
    assert rep["result"] == art["result"] == "FAIL: verify trait.check"
    assert art["test"]["pass"] is True            # the scenario itself still ran and passed
    assert [m["phase"] for m in rep["timeline"]].count("test_result") == 1
    assert "RESULT: FAIL: verify trait.check" in capsys.readouterr().out


def test_scenario_run_fails_fast_before_the_client_on_a_missing_mod(monkeypatch, tmp_path):
    """Same placement as `pzt run`: right after `server_started`, before the client is paid
    for -- and the RESULT names the mod."""
    log = _write(str(tmp_path / "server-stdout.log"), WARN)
    server = FakeServer(log, ["NoSuchModHere"])
    with workspace(), stub_scenario(monkeypatch, tmp_path, server) as made:
        assert scenario.run(scenario_args()) == 1
    # No client and the world was never accelerated; the `finally` still puts the clock back,
    # because "is it at 1x?" is not a question a failed run gets to leave open.
    assert made["clients"] == [] and server.rcons == ["settimespeed 1"]
    rep = report_of(tmp_path)
    assert [m["phase"] for m in rep["timeline"]] == [
        "profile", "server_started", "mods_not_found", "mod_missing_line", "error",
        "settimespeed", "server_stopped", "faults"]
    assert rep["result"] == "FAIL: mods not found at load: NoSuchModHere"
    assert rep["verify"] == [] and rep["profile"]["name"] == "p"


def test_scenario_run_without_a_profile_still_writes_the_new_keys(monkeypatch, tmp_path):
    """B5: the fail-fast and the artifact's `profile` key are on the plain path too. `profile`
    is null and `verify` empty there -- both new in slice 07."""
    server = FakeServer(str(tmp_path / "server-stdout.log"))
    with workspace(), stub_scenario(monkeypatch, tmp_path, server) as made:
        assert scenario.run(scenario_args(profile=None, user="admin")) == 0
    assert made["server_kw"] == {"port": None, "rcon_port": None, "mods": None,
                                 "mod_sources": None, "mod_skip": (), "sandbox": None}
    rep, art = report_of(tmp_path), artifact_of(tmp_path)
    assert art["profile"] is None and art["verify"] == []
    assert "profile" not in rep and "verify" not in rep
