"""a_pipe_3 -- Plan 21 Stage A pass 3 (spec § 4.1), the last pass of the stage's budget: the pipe's go/no-go after pass 2
(run a_pipe_2-20261026-115846, NO-GO on scan15 and tick_p99_at5 alone). One boot of agent-nozombies (fixture `agent0`;
admin -debug, PZTestKit + PZAgent); the agent sits still and the driver measures the file channel.

WHY A PASS 3 (testing/artifacts/a_pipe_2-20261026-115846/GUIDE.md):
  - scan15 read 45 ms per tick, not in the chunked walk (steps 1-4 ms over 17 ticks) but in the completing tick's emit of
    the whole scan line: 16.7 KB -> 7 ms, 48.6 KB -> 20 ms, 99.3 KB -> 45 ms, about 0.45 ms per KB of PZA.json and
    append. The Lua now emits the scan in parts, one per tick, each the squares walked that tick (<= 60, about 6 KB);
  - tick_p99_at5 read 2 on a 1 ms clock: every cost is a difference of two integer getTimestampMs readings, so a single
    frame's tickMs is quantised to whole ms and its p99 cannot resolve a sub-ms cost. The new rate60 window reports the
    mean (below), ungraded, beside the p99 gate, which stays as written;
  - goto's stuck is no movement again and a failed goto clears its walk (the Lua; pass 2's progress rule failed a
    healthy walk round the agent0 house).

PHASES (each through xs.run_phase; a phase's fault is recorded and the next still runs). Pass 2's phases (a_pipe_2.py's
docstring) with these changes:
  rates   as pass 2 (a_pipe_2's own constants: RATES, WINDOW_S, ACK_TIMEOUT_S, HELLO_TIMEOUT_S).
  rate60  new, before scans: `rate 60` (a frame every tick), RATE60_WINDOW_S of wall clock collecting every frame after
          its ack, then `rate 5` back (its ack awaited; a missing one fails the phase after the row is kept). The row:
          frames, expected (60 * window), tickMs (each frame's sum of COST_KEYS; None when a key is absent), tick_sum
          (the sum of tickMs), the window's wall (the last frame's wallMs minus the first's) and tick_mean_ms_at60 =
          tick_sum / frames (None when any frame lacks a key or none came).
          WHAT THE MEAN IS: a mean of quantised readings. Each component is the difference of two 1 ms timestamps, so
          one frame reads 0, 1, 2 ... ms whatever its true cost; when a tick's phase against the ms boundary is
          unrelated to its work, each difference is an unbiased reading of the true span and the mean over ~1800 frames
          resolves a sub-ms average cost per frame tick. It does NOT resolve one tick's cost or the tail (a 0.3 ms
          mean is 0.3 ms every tick or 3 ms one tick in ten alike), it counts only the measured spans (poll, act, scan
          step, sense, the previous frame's flush; not the OnTick dispatch around them), and at rate 60 every tick
          builds a frame, so it is the cost of a frame tick, not of the average tick at rate 5. grades.gate_a reports
          it ungraded.
  scans   each `scan r` is acked at once ("queued"); its parts are the scanPart lines of the scanId whose part 1 is the
          first after the ack, collected until the part carrying done (SCAN_TIMEOUT_S), then the next frame after it.
          The row: scanId, parts (declared), partNumbers, partStepMs (each part's walk ms), partEmitMs (each part's
          emitMs: the PREVIOUS part's emit and flush, part 1's 0), partBytes and partSquares (each part line's
          re-serialised bytes and square count), squares, bytes, missing (the union), the done part's scanMs, scanTicks,
          scanMsPerTick, scanStepMaxMs and scanMsMeanPerTick, and from the next frame scanEmitMs (the last part's own
          emit and flush), senseMs and scanStepMs. A row whose part numbers are not 1..parts is an error row
          ("parts not contiguous"). grades.gate_a's scan15 reads max over ticks of (partStepMs[i] + partEmitMs[i+1]),
          scanEmitMs standing for partEmitMs[n+1].
  motion  as pass 2 (voided legs).
  server  as pass 2.

Clocks: as pass 1 (a line's wallMs is the client's PZA.now(); a key ending in PyMs is this process's time.time() in ms).

RULES: never edited after its run (the next pass is a new file); takes no argument; one live session at a time; free
memory gated at MIN_FREE_GB before the boot; never -safemode. a_pipe.py and a_pipe_2.py are frozen and imported, never
changed; the phases inherited from a_pipe_2 read a_pipe_2's own constants, named in CONSTANTS here for the artifact.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _dlib as DL                                    # noqa: E402
import xlib as X                                      # noqa: E402
from agent.drivers import a_pipe as AP                # noqa: E402  (the frozen pass-1 file: the boot seams)
from agent.drivers import a_pipe_2 as AP2             # noqa: E402  (the frozen pass-2 file: Pipe2)

KEY = "a_pipe_3"
DRIVER = "a_pipe_3.py"
PROFILE = "testing/profiles/agent-nozombies.toml"
ARTIFACT = "a_pipe_3.json"
PASS2_RUN = "a_pipe_2-20261026-115846"
BUDGET_S = 560.0
USER = "admin"
MIN_FREE_GB = 12.0
REPO = DL.REPO
_ME = os.path.basename(os.path.abspath(__file__))

RATE60 = 60
RATE60_WINDOW_S = 30.0
RATE_BACK = 5
SCAN_RADII = (5, 10, 15)
SCANS_PER_RADIUS = 5
SCAN_TIMEOUT_S = 15.0
NEXT_FRAME_TIMEOUT_S = 5.0
ACK_TIMEOUT_S = AP2.ACK_TIMEOUT_S
COST_KEYS = AP2.COST_KEYS
AGENT_LUA = "testing/PZAgent"
CLIENT_ERR_RX = AP.CLIENT_ERR_RX

CONSTANTS = {k: globals()[k] for k in (
    "RATE60", "RATE60_WINDOW_S", "RATE_BACK", "SCAN_RADII", "SCANS_PER_RADIUS", "SCAN_TIMEOUT_S", "NEXT_FRAME_TIMEOUT_S",
    "ACK_TIMEOUT_S", "COST_KEYS", "BUDGET_S", "MIN_FREE_GB", "CLIENT_ERR_RX", "PASS2_RUN")}
CONSTANTS["inherited_from_a_pipe_2"] = {k: getattr(AP2, k) for k in (
    "HELLO_TIMEOUT_S", "RATES", "WINDOW_S", "MOTION_TRIPS", "MOTION_DX", "MOTION_EPS", "SETTLE_S", "GOAL_TIMEOUT_S",
    "SERVER_CALLS", "POLL_S")}


def parse_argv(argv, driver_file):
    """The driver takes no argument: the refusal text, or None for a bare call."""
    if argv:
        return f"{os.path.basename(driver_file)} takes no arguments; a bare call boots the session"
    return None


def new_out():
    out = AP.new_out()
    out["pass2_run"] = PASS2_RUN
    out["readings"]["rate60"] = {}
    return out


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    """The driver's own pre-boot checks: its file name, the profile on disk, no committed artifact of its key (a
    driver that ran is frozen), the agent Lua and the driver committed clean. Returns (checks, ok)."""
    git_say = git_say or DL.C.git_say
    git_dirty = git_dirty or DL.C.git_dirty
    base = os.path.basename(driver_file)
    c = {"driver_file": base == DRIVER, "driver_prefix": base.startswith(KEY),
         "profile_exists": os.path.isfile(os.path.join(repo, PROFILE))}
    c["no_committed_artifact"] = git_say("ls-files", "--", f"testing/artifacts/{KEY}-*") == ""
    c["agent_lua_dirty"] = git_dirty(AGENT_LUA)[0]
    c["driver_dirty"] = git_dirty(f"testing/agent/drivers/{DRIVER}")[0]
    ok = (c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["no_committed_artifact"]
          and c["agent_lua_dirty"] is False and c["driver_dirty"] is False)
    return c, ok


def preboot(driver_file, repo=REPO):
    """_dlib.preboot (git provenance, doctor, harness Lua clean, the layout lint) and the driver's own checks."""
    pre, ok = DL.preboot(driver_file, os.path.join(repo, PROFILE))
    pre["driver_checks"], ok2 = driver_checks(driver_file, repo)
    return pre, bool(ok and ok2)


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def tick_ms(cost):
    """A frame's tickMs: the sum of COST_KEYS, None when any is absent."""
    cost = cost or {}
    return sum(cost[k] for k in COST_KEYS) if all(_num(cost.get(k)) is not None for k in COST_KEYS) else None


class Pipe3(AP2.Pipe2):
    """Pass 2's Pipe with the scan in parts and the rate-60 window."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.parts = []           # (scanPart line, read PyMs)

    def on_line(self, l):
        super().on_line(l)
        if l.get("kind") == "scanPart":
            self.parts.append((l, self.py_ms()))

    def phases(self):
        return [("rates", self.phase_rates), ("rate60", self.phase_rate60), ("scans", self.phase_scans),
                ("motion", self.phase_motion), ("server", self.phase_server)]

    # ---- phase 2: rate60
    def phase_rate60(self):
        self.need_hello()
        row = self.rate60_window()
        self.rd["rate60"] = row
        self.sync_out()
        self.xs.persist()
        if row.get("error"):
            raise RuntimeError(row["error"])

    def rate60_window(self):
        sent = self.py_ms()
        seq = self.link.send("rate", str(RATE60))
        row = {"rate": RATE60, "cmdSeq": seq, "sentPyMs": sent, "window_s": RATE60_WINDOW_S,
               "expected": RATE60 * RATE60_WINDOW_S}
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        row["ack"] = ack
        if ack is None:
            row["error"] = "no ack for rate %d" % RATE60
            return row
        t_end = self.clock() + RATE60_WINDOW_S
        self.wait_until(lambda: self.clock() >= t_end, RATE60_WINDOW_S + 1.0)
        fr = [f for f, read in self.frames if f["seq"] > ack["seq"] and read <= t_end * 1000.0]
        ticks = [tick_ms(f.get("cost")) for f in fr]
        row["frames"] = len(fr)
        row["tickMs"] = ticks
        row["tick_none"] = sum(1 for t in ticks if t is None)
        row["tick_sum"] = sum(t for t in ticks if t is not None)
        row["frame_wallMs_first"] = fr[0].get("wallMs") if fr else None
        row["frame_wallMs_last"] = fr[-1].get("wallMs") if fr else None
        first, last = _num(row["frame_wallMs_first"]), _num(row["frame_wallMs_last"])
        row["wall_ms"] = last - first if first is not None and last is not None else None
        # the mean of quantised readings (the module docstring): resolves a sub-ms mean, never one tick or the tail
        row["tick_mean_ms_at60"] = row["tick_sum"] / len(fr) if fr and row["tick_none"] == 0 else None
        back = self.link.send("rate", str(RATE_BACK))
        row["back_cmdSeq"] = back
        row["back_ack"] = self.await_ack(back, ACK_TIMEOUT_S)
        if row["back_ack"] is None:
            row["error"] = "no ack for rate %d back" % RATE_BACK
        return row

    # ---- phase 3: scans (in parts)
    def phase_scans(self):
        self.need_hello()
        for r in SCAN_RADII:
            rows = self.rd["scans"].setdefault(str(r), [])
            for _ in range(SCANS_PER_RADIUS):
                rows.append(self.one_scan(r))
            self.sync_out()
            self.xs.persist()

    def scan_parts(self, n0, after_seq):
        """The parts of the scan whose part 1 is the first scanPart after `after_seq` (from self.parts[n0:]), in arrival
        order, and whether its done part has come."""
        mine = [l for l, _ in self.parts[n0:] if l.get("seq", 0) > after_seq]
        first = next((l for l in mine if l.get("part") == 1), None)
        if first is None:
            return [], False
        sid = first.get("scanId")
        got = [l for l in mine if l.get("scanId") == sid]
        return got, any(l.get("done") for l in got)

    def one_scan(self, r):
        n0 = len(self.parts)
        seq = self.link.send("scan", str(r))
        row = {"r": r, "cmdSeq": seq, "sentPyMs": self.py_ms()}
        ack = self.await_ack(seq, ACK_TIMEOUT_S)
        row["ack"] = ack
        if ack is None:
            row["error"] = "no ack"
            return row
        done = self.wait_until(lambda: self.scan_parts(n0, ack["seq"])[1], SCAN_TIMEOUT_S)
        parts, _ = self.scan_parts(n0, ack["seq"])
        if not parts:
            row["error"] = "no scan part"
            return row
        last = parts[-1]
        nums = [l.get("part") for l in parts]
        declared = _num(parts[0].get("parts"))
        missing = []
        for l in parts:
            for m in AP._seq(l.get("missing")):
                if m not in missing:
                    missing.append(m)
        ms, ticks = _num(last.get("scanMs")), _num(last.get("scanTicks"))
        row.update({"scanId": parts[0].get("scanId"), "parts": declared, "partNumbers": nums,
                    "partStepMs": [_num(l.get("stepMs")) for l in parts],
                    "partEmitMs": [_num(l.get("emitMs")) for l in parts],
                    "partBytes": [AP._bytes(l) for l in parts],
                    "partSquares": [len(AP._seq(l.get("squares"))) for l in parts],
                    "squares": sum(len(AP._seq(l.get("squares"))) for l in parts),
                    "bytes": sum(AP._bytes(l) for l in parts), "missing": missing, "done": done,
                    "scanMs": ms, "scanTicks": ticks,
                    "scanMsPerTick": AP._seq(last.get("scanMsPerTick")) if last.get("scanMsPerTick") is not None
                    else None,
                    "scanStepMaxMs": _num(last.get("scanStepMaxMs")),
                    "scanMsMeanPerTick": ms / ticks if ms is not None and ticks else None,
                    "seq": last.get("seq"), "wallMs": last.get("wallMs"),
                    "firstWallMs": parts[0].get("wallMs")})
        if not done:
            row["error"] = "no done part in %ss" % SCAN_TIMEOUT_S
            return row
        if declared is None or nums != list(range(1, int(declared) + 1)):
            row["error"] = "parts not contiguous"
        nf = self.next_frame(last["seq"], NEXT_FRAME_TIMEOUT_S)
        cost = (nf.get("cost") or {}) if nf else {}
        row["next_frame_senseMs"] = cost.get("senseMs") if nf else None
        row["next_frame_scanStepMs"] = cost.get("scanStepMs") if nf else None
        # the last part's own emit and flush, carried once on the first frame after it
        row["scanEmitMs"] = _num(cost.get("scanEmitMs")) if nf else None
        return row


# ================================================================ the boot
def main(budget_s=BUDGET_S):
    from _common import ask, hard_kill                       # noqa: E402
    import x49b_lib as B                                     # noqa: E402
    from pzt import fixture as fx, profile, session          # noqa: E402
    from pzt.bus import resolve_side                         # noqa: E402
    from pzt.paths import new_run_dir                        # noqa: E402

    pre, ok = preboot(_ME)
    if not ok:
        print(json.dumps({"preboot": pre}, indent=1, default=str)[:20000])
        print("a pre-boot check failed; the session was not started")
        sys.exit(1)
    prof = profile.load(os.path.join(REPO, PROFILE))
    rec_fx = fx.load(prof.fixture)
    run_id, run_dir = new_run_dir(KEY)
    tl = session.Timeline()
    clients, started = {}, []
    holder = {"server": None}
    out = new_out()
    out["world_changes"]["restored"] = f"fixture {prof.fixture} restored into the run dir"
    xs = X.Xs(out, node=lambda side: resolve_side(side, holder["server"], clients), tl=tl, clients=clients,
              ask=ask, budget_s=budget_s, user=USER)
    xs.path = os.path.join(run_dir, ARTIFACT)
    out.update({"run_id": run_id, "session_key": KEY, "driver": _ME, "user": USER, "profile": prof.report(),
                "preboot": pre, "argv": sys.argv[1:], "constants": CONSTANTS,
                "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run"),
                            "build": rec_fx.get("build")},
                "driver_commit": DL.C.git_say("log", "-1", "--format=%h", "--", f"testing/agent/drivers/{DRIVER}")})
    AP.memory_gate(xs)
    xs.mem("preboot")
    xs.persist()
    pipe = None
    try:
        out.update(DL.boot(xs, prof, rec_fx, run_dir, [USER], started, clients, holder,
                           make_client=AP.clearing_make_client(session.make_client)))
        xs.mem("ready")
        xs.persist()
        if not all(v.get("ok") for v in out["verify"]):
            out["abort"] = "a verify row failed: the session is not the one asked for"
            tl.mark("error", detail=out["abort"])
        else:
            out["state_dir"] = DL.state_dir(clients[USER])
            pipe = Pipe3(xs, DL.link_for(clients, USER))
            pipe.run()
    except Exception as e:                                   # noqa: BLE001
        import traceback
        out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", detail=str(e)[:200])
    finally:
        every = list(started)

        def read_logs():
            found, n = AP.client_errors([(getattr(c, "username", "?"), c.console) for c in every])
            out["logs"] = {"patterns": {"client_error": CLIENT_ERR_RX}, "clients": found}
            out["client_lua_errors"] = n

        if pipe is not None:
            pipe.sync_out()
        xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)
        xs.mem("after")
        out["finished"] = True
        xs.persist()
        xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)
    print(json.dumps({"run_id": run_id, "run_dir": run_dir, "error": out.get("error"), "abort": out.get("abort"),
                      "phase_errors": {k: v.get("error") for k, v in out.get("phase_errors", {}).items()},
                      "budget_stop": out.get("budget_stop"), "voided_legs": out.get("voided_legs"),
                      "tick_mean_ms_at60": (out.get("readings", {}).get("rate60") or {}).get("tick_mean_ms_at60"),
                      "wall_seconds": out.get("wall_seconds")}, indent=1, default=str))
    return out


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main()
