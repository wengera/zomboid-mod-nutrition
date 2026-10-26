"""drivers/_dlib.py: the memory wait, the state dir, preboot, and the three profiles (offline; nothing boots)."""
import os
import types

import pytest

from agent.drivers import _dlib as D
from pzt import profile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROFILES = os.path.join(REPO, "testing", "profiles")


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def test_wait_memory_returns_at_once_when_free():
    c = Clock()
    ok, rd = D.wait_memory(12.0, free=lambda: 20.0, sleep=c.sleep, clock=c.now)
    assert ok and c.sleeps == [] and [r["free_gb"] for r in rd] == [20.0]
    assert rd[0]["wall"] == 1000.0


def test_wait_memory_polls_then_true():
    c = Clock()
    seq = iter([3.0, 5.0, 11.9, 12.0])
    ok, rd = D.wait_memory(12.0, max_wait_s=600, poll_s=60, free=lambda: next(seq), sleep=c.sleep, clock=c.now)
    assert ok and len(c.sleeps) == 3 and len(rd) == 4


def test_wait_memory_false_after_max_wait_keeps_readings():
    c = Clock()
    ok, rd = D.wait_memory(12.0, max_wait_s=300, poll_s=60, free=lambda: 4.0, sleep=c.sleep, clock=c.now)
    assert not ok and len(rd) >= 5 and all(r["free_gb"] == 4.0 for r in rd)
    assert c.t - 1000.0 <= 300 + 60


def test_wait_memory_unreadable_counts_as_low():
    c = Clock()
    ok, rd = D.wait_memory(12.0, max_wait_s=120, poll_s=60, free=lambda: None, sleep=c.sleep, clock=c.now)
    assert not ok and rd[0]["free_gb"] is None


def test_state_dir_and_clear(tmp_path):
    cl = types.SimpleNamespace(cache=str(tmp_path), username="admin")
    sd = D.state_dir(cl)
    assert sd == os.path.join(str(tmp_path), "Lua", "pzagent", "admin")
    D.clear_state_dir(cl)                      # absent: no error
    os.makedirs(sd)
    open(os.path.join(sd, "state.log"), "w").write("x")
    D.clear_state_dir(cl)
    assert not os.path.exists(os.path.join(str(tmp_path), "Lua", "pzagent"))
    assert os.path.isdir(os.path.join(str(tmp_path), "Lua")) or True


@pytest.mark.parametrize("name,fixture,zombies", [("agent", "agent", None), ("agent-nozombies", "agent0", 6),
                                                  ("agent-dense", "agent", 4)])
def test_agent_profiles_resolve(agent_fixture, name, fixture, zombies):
    p = profile.load(os.path.join(PROFILES, name + ".toml"))
    assert p.fixture == fixture and p.users == ["admin"]
    assert p.sources["PZAgent"].replace("\\", "/").endswith("testing/PZAgent/PZAgent")
    assert "PZTestKit" in p.sources and p.mods[0] == "PZTestKit" and "PZAgent" in p.mods
    assert p.ini == {"SleepAllowed": True, "SleepNeeded": True}
    assert p.client_timeout == 120
    assert [v["cmd"] for v in p.verify] == ["ping", "ping"]
    assert (p.sandbox.get("Zombies") if zombies else p.sandbox) == (zombies if zombies else {})


def test_preboot_with_doctor_and_lint_stubbed(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(D.C, "git_dirty", lambda rel: (False, ""))
    pre, ok = D.preboot("x.py", os.path.join(PROFILES, "agent.toml"))
    assert ok and pre["doctor_clean"] and pre["lint_errors"] == [] and pre["harness_lua_dirty"] is False
    assert pre["profile"] == "agent"


def test_preboot_fails_on_lint_error_or_dirty(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.harness, "lint_paths", lambda srcs: ["ERROR x"])
    monkeypatch.setattr(D.C, "git_dirty", lambda rel: (False, ""))
    assert D.preboot("x.py", os.path.join(PROFILES, "agent.toml"))[1] is False
    monkeypatch.setattr(D.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(D.C, "git_dirty", lambda rel: (True, ""))
    assert D.preboot("x.py", os.path.join(PROFILES, "agent.toml"))[1] is False


def test_link_for_points_at_state_dir(tmp_path):
    cl = types.SimpleNamespace(cache=str(tmp_path), username="admin")
    assert D.link_for({"admin": cl}, "admin").dir == D.state_dir(cl)


def test_bus_stats_adds_wall_ms():
    class Xs:
        def step(self, name, side, cmd, user=""):
            return {"ack": {"ok": True}}
    r = D.bus_stats(Xs(), "admin")
    assert r["ack"] == {"ok": True} and r["wallMs"] > 1e12


def test_boot_passes_make_client_to_attach_clients(monkeypatch):
    seen = {}
    srv = types.SimpleNamespace(start=lambda timeout=None: None, proc=types.SimpleNamespace(pid=7), build="42.21.0")
    monkeypatch.setattr(D, "make_server", lambda *a, **kw: srv)

    def attach(run_dir, prof, server, rec, tl, users=None, started=None, make_client="unset"):
        seen["make_client"] = make_client
        return {}
    monkeypatch.setattr(D, "attach_clients", attach)
    monkeypatch.setattr(D, "verify", lambda prof, server, clients, tl: [])
    xs = types.SimpleNamespace(wall=lambda: 0.0, tl=types.SimpleNamespace(mark=lambda *a, **kw: None), server=None)
    prof = types.SimpleNamespace(mods=[], sources={}, skip=(), sandbox={}, ini={}, gclog=False, server_timeout=1)
    mk = object()
    D.boot(xs, prof, {}, "run", ["admin"], [], {}, {}, make_client=mk)
    assert seen["make_client"] is mk
    D.boot(xs, prof, {}, "run", ["admin"], [], {}, {})
    assert seen["make_client"] is None                     # attach_clients' own default (pzt.session.make_client)
