"""drivers/a_pipe_2.py and the gate_a amendment (Plan 21 Stage A pass 2), offline: the driver is never invoked.

The phases run against FakeMod2, test_a_pipe's FakeMod with pass 2's Lua shapes (PZAgent_Main.lua after Stage A pass 2):
a `scan r` acked at once with reason "queued" and its line emitted ceil((2r+1)^2 / 60) ticks later carrying scanMs (the
summed chunk ms) and scanTicks; every frame carrying health, nZombies and cost.scanStepMs. A leg's health drop or its
zombies are scheduled per goto command."""
import math
import os

import pytest

from agent import grades as G
from agent.drivers import a_pipe_2 as D
from agent.link import Link
from . import test_a_pipe as T1

REPO = T1.REPO
X = D.X


# ================================================================ static: refusal and constants
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert D.parse_argv(["x"], D.__file__) and D.parse_argv(["--help"], D.__file__)
    assert D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "a_pipe_2.py"
    assert D.KEY == "a_pipe_2" and D.ARTIFACT == "a_pipe_2.json"
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert D.PASS1_RUN == "a_pipe-20261026-101003" and D.PASS1_RUN in D.__doc__
    assert "scanStepMs" in D.COST_KEYS and D.MOTION_TRIPS * len(D.MOTION_DX) == G.MOTION_COMMANDS


def test_the_frozen_pass_1_driver_is_imported_never_copied_over():
    src = open(D.__file__, encoding="utf-8").read()
    assert "from agent.drivers import a_pipe as AP" in src
    assert D.AP.KEY == "a_pipe" and issubclass(D.Pipe2, D.AP.Pipe)
    assert "make_client=AP.clearing_make_client(session.make_client)" in src


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (False, ""))
    real = D.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-nozombies" and pre["driver_checks"]["driver_file"] is True
    tracked["v"] = "testing/artifacts/a_pipe_2-20261027-120000/a_pipe_2.json"
    assert D.preboot(D.__file__)[1] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "a_pipe.py"))[1] is False


# ================================================================ gate_a: voided legs
def legs(n, voided=0, ms=100):
    rows = [{"ack": {"wallMs": 1000}, "first_motion": {"wallMs": 1000 + ms}} for _ in range(n)]
    rows += [{"ack": {"wallMs": 1000}, "first_motion": None, "voided": "health fell 100 -> 61"} for _ in range(voided)]
    return rows


def test_gate_a_counts_unvoided_legs_and_reports_the_voided_apart():
    o = T1.passing_out()
    o["readings"]["motion"] = legs(20, voided=3)
    g = G.gate_a(o)
    assert g["pass"]["cmd_motion_p90"] is True and g["verdict"] == "GO", g
    assert g["cmd_motion_n"] == 20 and g["cmd_motion_paired"] == 20 and g["cmd_motion_voided"] == 3
    assert g["cmd_motion_voided_reasons"] == ["health fell 100 -> 61"] * 3


def test_gate_a_needs_twenty_unvoided_legs():
    o = T1.passing_out()
    o["readings"]["motion"] = legs(18, voided=2)
    g = G.gate_a(o)
    assert g["pass"]["cmd_motion_p90"] is False and g["cmd_motion_n"] == 18 and g["cmd_motion_voided"] == 2
    assert [k for k, v in g["pass"].items() if not v] == ["cmd_motion_p90"]


def test_a_pass_1_artifact_grades_as_before():
    g = G.gate_a(T1.passing_out())
    assert g["cmd_motion_n"] == 20 and g["cmd_motion_voided"] == 0 and g["verdict"] == "GO"


# ================================================================ the phases against FakeMod2
class FakeMod2(T1.FakeMod):
    """FakeMod with pass 2's chunked scan, health and nZombies. `hurt` maps a goto's 1-based index to the health it
    falls to 5 ticks after its poll; `zombies` maps an index to the nZombies it reads from 5 to 15 ticks after."""
    CHUNK = 60

    def __init__(self, d, clock, hurt=None, zombies=None, chunk_ms=1, **kw):
        super().__init__(d, clock, **kw)
        self.hurt, self.zmap, self.chunk_ms = dict(hurt or {}), dict(zombies or {}), chunk_ms
        self.health, self.nz, self.gotos = 100.0, 0, 0
        self.pending = None           # (due tick, r, ticks)
        self.at = {}                  # tick -> ("health"|"nz", value)

    def poll(self):
        cmd = super().poll()
        if cmd is None:
            return None
        if cmd["goal"] == "scan":
            self.cmds.append(cmd)
            r = int(cmd["args"].split()[0])
            ticks = math.ceil((2 * r + 1) ** 2 / self.CHUNK)
            self.pending = (self.tick + ticks - 1, r, ticks)
            self.emit("ack", {"cmdSeq": cmd["seq"], "ok": True, "reason": "queued"})
            self.flush()
            return None
        if cmd["goal"] == "goto":
            self.gotos += 1
            if self.gotos in self.hurt:
                self.at[self.tick + 5] = ("health", self.hurt[self.gotos])
            if self.gotos in self.zmap:                  # a zombie passes inside the leg and is gone before its end
                self.at[self.tick + 5] = ("nz", self.zmap[self.gotos])
                self.at[self.tick + 15] = ("nz", 0)
        return cmd

    def emit(self, kind, body):
        if kind == "frame":
            body.update(health=self.health, nZombies=self.nz)
            body["cost"]["scanStepMs"] = self.chunk_ms if self.pending else 0
        super().emit(kind, body)

    def step(self):
        super().step()
        ch = self.at.pop(self.tick, None)
        if ch and ch[0] == "health":
            self.health = ch[1]
        elif ch:
            self.nz = ch[1]
        if self.pending and self.tick >= self.pending[0]:
            _, r, ticks = self.pending
            self.pending = None
            sq = [{"x": int(self.x) + dx, "y": int(self.y) + dy, "z": 0, "solid": False}
                  for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
            self.emit("scan", {"r": r, "squares": sq, "missing": [], "scanMs": self.chunk_ms * ticks,
                               "scanTicks": ticks, "hour": 7})
            self.flush()


@pytest.fixture
def short_window(monkeypatch):
    monkeypatch.setattr(D, "WINDOW_S", 5.0)


def run_pipe(tmp_path, **flags):
    clock = T1.Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = FakeMod2(sd, clock, **flags)
    out = D.new_out()

    def ask(node, cmd, args, timeout=30):
        mod.sleep(0.05)
        return {"ok": True, "user": args, "stats": {"HUNGER": 0.1}}

    xs = X.Xs(out, node=lambda side: side, ask=ask, clock=clock.now, sleep=mod.sleep, budget_s=1e9, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    D.Pipe2(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep).run()
    return out, mod


def test_a_clean_run_records_hello_build_chunked_scans_and_twenty_unvoided_legs(tmp_path, short_window):
    out, mod = run_pipe(tmp_path)
    assert out["phase_errors"] == {}, out["phase_errors"]
    assert out["mode"] == "append" and out["hello_build"] == "42.21.0"
    for r in (5, 10, 15):
        rows = out["readings"]["scans"][str(r)]
        ticks = math.ceil((2 * r + 1) ** 2 / 60)
        assert len(rows) == 5 and all(s["scanTicks"] == ticks and s["scanMs"] == ticks for s in rows), rows[0]
        assert all(s["ack"]["reason"] == "queued" and s["squares"] == (2 * r + 1) ** 2 for s in rows)
        assert all(s["scanMsPerTick"] == 1 and "error" not in s for s in rows)
    assert [s["scanTicks"] for s in out["readings"]["scans"]["15"]] == [17] * 5
    m = out["readings"]["motion"]
    assert len(m) == 20 and not any(r.get("voided") for r in m)
    assert all(r["at_send"] == {"health": 100.0, "nZombies": 0} and r["at_end"] == {"health": 100.0, "nZombies": 0}
               for r in m)
    rates = out["readings"]["rates"]["5"]
    assert rates["tickMs"][0] == pytest.approx(0.6) and rates["scanStepMs"][0] == 0
    out["client_lua_errors"] = 0
    g = G.gate_a(out)
    assert g["cmd_motion_n"] == 20 and g["cmd_motion_voided"] == 0 and g["pass"]["cmd_motion_p90"], g
    assert out["voided_legs"] == 0 and not any("voided" in n for n in out["notes"])


def test_a_leg_whose_health_falls_or_meets_zombies_is_voided_and_excluded(tmp_path, short_window):
    out, mod = run_pipe(tmp_path, hurt={3: 61.0}, zombies={6: 2})
    m = out["readings"]["motion"]
    void = [i for i, r in enumerate(m) if r.get("voided")]
    assert void == [2, 5], [r.get("voided") for r in m]
    assert m[2]["voided"].startswith("health fell") and m[2]["at_send"]["health"] == 100.0
    assert m[2]["at_end"]["health"] == 61.0
    assert m[5]["voided"].startswith("zombies") and m[5]["max_nZombies"] == 2 and m[5]["at_end"]["nZombies"] == 0
    assert m[3]["at_send"]["health"] == 61.0 and not m[3].get("voided")          # lower, but it did not fall in-leg
    out["client_lua_errors"] = 0
    g = G.gate_a(out)
    assert g["cmd_motion_n"] == 18 and g["cmd_motion_voided"] == 2 and g["pass"]["cmd_motion_p90"] is False
    assert out["voided_legs"] == 2 and any("voided" in n for n in out["notes"])


def test_a_dead_character_at_send_voids_the_leg(tmp_path, short_window):
    out, mod = run_pipe(tmp_path, hurt={1: 0.0})
    m = out["readings"]["motion"]
    assert m[0]["voided"].startswith("health fell")
    assert all(r["voided"] == "dead at send" for r in m[1:]), [r.get("voided") for r in m[1:]]


def test_a_scan_line_without_scan_ticks_is_an_error_row(tmp_path, short_window):
    class OldScan(FakeMod2):
        def emit(self, kind, body):
            if kind == "scan":
                body.pop("scanTicks", None)
            super().emit(kind, body)
    clock = T1.Clock()
    sd = str(tmp_path / "sd")
    mod = OldScan(sd, clock)
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=mod.sleep, user="admin")
    pipe = D.Pipe2(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    row = pipe.one_scan(15)
    assert row["error"] == "no scanTicks: not the chunked scan" and row["scanMs"] == 17


def test_a_hello_in_chunk_mode_fails_the_rates_phase(tmp_path, short_window):
    class Chunky(FakeMod2):
        def emit(self, kind, body):
            if kind == "hello":
                body["mode"] = "chunk"
            super().emit(kind, body)
    clock = T1.Clock()
    sd = str(tmp_path / "sd")
    mod = Chunky(sd, clock)
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=mod.sleep, user="admin")
    pipe = D.Pipe2(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    xs.run_phase("rates", pipe.phase_rates)
    assert "not append" in xs.out["phase_errors"]["rates"]["error"]
    assert xs.out["mode"] == "chunk" and xs.out["hello_build"] == "42.21.0" and xs.out["readings"]["rates"] == {}
