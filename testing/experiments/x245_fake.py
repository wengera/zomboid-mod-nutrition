"""x245-fake -- Plan 10c Task H5 (live, optional): does the engine's own fake client, zombie.network.FakeClientManager
(jar 42.20.4), join the harness's -nosteam dedicated server, and if it does, what does vanilla's per-player load cost
the server frame at N = 0, 5, 10, ..., 60 connected players (E7's denominator)?

Written BEFORE the boot with every prediction in it and never edited after the run (CLAUDE.md s5, B3-1/B3-2). The
driver asserts that its PREFIX and PROFILE match its own file name (H3 session b's slip).

THE JAR READING (pz.sh, jar b0bbce05d5, before this driver was written):
  - FakeClientManager.main reads -scenarios=<file> and -id=<n>; with no -id every movement in the file becomes one
    client in ONE JVM, on one RakNet peer bound to local port 17500 (17500 + id with -id), each client on its own
    thread that sleeps its movement's `connect` milliseconds before connecting (Client.updateThread @84-@87).
  - Network.connect hard-codes the server port 16261 and the empty password hash (PZcrypt.hash("", true)); the host is
    config.client.connection.serverHost. So this session's server runs on port 16261.
  - The login packet is username, password (= the username), Core.getVersionNumber() (the fake's own static, so the
    version always matches this jar), authType 1 -- the field order LoginPacket.parse reads on the server.
  - With no `checksum` object in the scenario the fake skips its checksum step (Client.receive @164-@177 goes straight
    to PLAYER_EXTRA_INFO), so the server must not demand one: DoLuaChecksum = false in the RUN copy of the ini.
  - Usernames are Client<id> (Player.<init>); the server's ini has Open = true, so an unknown user is expected to be
    created at login (not read in the jar; the join reading settles it).
  - A dry run before this driver (no server listening; scratchpad only) started the JVM, loaded the scenario, tried
    127.0.0.1:16261 and wrote nothing into the install or the cache dir it was given.

READ-ONLY INSTALL: the fake JVM runs from the install's jre64 with an absolute classpath (<install>/ and
<install>/projectzomboid.jar) and library path, its working directory is the run dir's `fake/` folder, and
-Ddeployment.user.cachedir points at `fake/cache` in the run dir (ZomboidFileSystem.getCacheDir @7 reads it). Nothing
is written under the install or the workshop folder.

THE SESSION (one boot of profile x24-fake; fixture two restored into the run dir; NO game client is attached; NO
NutritionRevamp is loaded, so every reading is vanilla plus the harness's own ring hooks):
  S0    the idle ring at N = 0 (nobody online): perf.local PERF_N, tick.ring RING_N, RING_WALL_S of wall, read both.
  RAMP  the fake JVM is launched once with all NMAX movements; movement i (1-based) is in group g = (i-1)//STEP and
        connects at FIRST_S + g*STEP_S seconds after the launch. For each group g: a memory check just before its
        connect time (free < STOP_FREE_GB: the fake JVM is killed and the ramp ends -- the only way to stop adding,
        because the clients share one JVM), then at connect + JOIN_WAIT_S: `players` (who is online), free memory,
        the two JVMs' working sets, the fake log's counts; then perf.local + tick.ring over RING_WALL_S; then the
        reads and `players` again (held through the window). If nobody is online after group 1's window, the ramp
        stops: the join failed.
  HOLD  only if at least HOLD_MIN are online after the last group: HOLD_S of wall with `players` and memory every
        HOLD_EVERY_S, and a last ring over the final RING_WALL_S (the 10-minute hold the plan names).
  Z     the fake JVM is killed (stop only what this driver started), `players` after DISCONNECT_WAIT_S, teardown.
  A watcher thread samples free memory every WATCH_S during RAMP and HOLD and kills the fake JVM if it falls below
  WATCH_KILL_GB (a safety stop against a host kill; recorded, never silent).

THE SCHEDULER ARMS ARE NOT RUN: the harness's schedulers (ghost.load burst|budget<ms>|...) run harness-held ghost
records (N minus the online count, deep copies of online players' NutritionRevamp records) against real carriers;
no harness command drives P.work for the online usernames on a schedule, and this session loads no NutritionRevamp.
A burst/budget15 reading on real players needs a harness change (reported, not made).

THE READINGS (per N): the ring's busy (OnTickEvenPaused -> OnTick), period and endPeriod (OnTick -> OnTick) p50, p99
and max over the window's frames minus the frames overlapping the ring-read step; perf.local's window max p50/p99/max;
the online count before and after the window; free memory; the server's and the fake JVM's working set.

PREDICTIONS:
  J  at least one fake client is online at group 0's read. Falsifier: none online after group 1's window, with the
     fake log's errors and the server log's access-denied / exception lines as the failure read. Confidence is low:
     the fake's packet writers (PlayerConnect, ExtraInfo) were not checked against the 42.20.4 server's parsers.
  L  if they join: busy p50 rises at most VANILLA_MS_PER_PLAYER_MAX ms per online player (a vanilla remote player
     costs the server far less than the mod's minute, 1.583 ms a run, #3387); endPeriod p99 stays within the idle
     band plus RULE_P99_ADD ms at every N.
  H  if 58 or more are online after the ramp, at least HOLD_MIN stay online through the hold.
"""
import ctypes
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.harness import lint_paths                              # noqa: E402
from pzt.paths import JAVA, PZ_DIR, new_run_dir                 # noqa: E402
from pzt.session import Timeline, make_server, teardown, verify  # noqa: E402

PROFILE = "x24-fake"
PREFIX = "x245"
_ME = os.path.basename(os.path.abspath(__file__))
assert _ME.startswith(PREFIX + "_"), f"{_ME} does not start with {PREFIX}_"
assert PROFILE == "x24-fake", PROFILE

SESSION = ("Plan 10c Task H5: do the engine's FakeClientManager clients join a 42.20.4 -nosteam dedicated server, "
           "and vanilla's frame busy and end-to-end period at N = 0..60 in steps of 5 (server-only, no mod)")
ARTIFACT = "fake.json"
SCENARIO = "scenario.json"
GCLOG = "gc.log"
FAKE_LOG = "fake-stdout.log"
FAKE_LOG_COPY_MAX = 2 * 1024 * 1024
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
HARNESS_SERVER = LUA_DIR + "/server/PZTestKit_Server.lua"
SRV = "server"

PORT = 16261                     # FakeClientManager.Network.connect: sipush 16261 (hard-coded)
RCON_PORT = 27015
INI = {"MaxPlayers": 64, "DoLuaChecksum": False}
NMAX = 60
STEP = 5
FIRST_S = 20.0
STEP_S = 180.0
JOIN_WAIT_S = 30.0
RING_WALL_S = 105.0              # about 1050 frames at the ten-tick lock
RING_N = 1500
PERF_N = 400
MIN_FRAMES = 1000
HOLD_MIN = 58
HOLD_S = 600.0
HOLD_EVERY_S = 60.0
DISCONNECT_WAIT_S = 30.0
MIN_FREE_GB = 12.0
STOP_FREE_GB = 2.0
WATCH_KILL_GB = 1.0
WATCH_S = 2.0
FAKE_XMX = "-Xmx1536m"
RESULT_WAIT_S = 30.0
LOG_LIMIT = 300
VANILLA_MS_PER_PLAYER_MAX = 0.5
RULE_P99_ADD = 20.0
FAKE_FPS = 10
FAKE_PREDICT = 1000
TOWNS = ((10580, 9700), (11750, 6850), (6400, 5300), (8050, 11550))   # Muldraugh, West Point, Riverside, Rosewood
GRID = 40                        # tiles between fake spawns within a town
ECHO_RX = re.compile(r"PZTK: ")
SRV_JOIN_RX = re.compile(r"access-denied|AccessDenied|Client\d+|login|LoginPacket|PlayerConnect|fully connected|"
                         r"disconnect|kick|Exception|Overflow|Underflow|too busy|ServerFull", re.I)
FAKE_RX = {"start": re.compile(r"Start client"), "connected": re.compile(r"Client connected to"),
           "conn_failed": re.compile(r"Connection failed|connection to .* failed", re.I),
           "error": re.compile(r"^ERROR"), "disconnect": re.compile(r"disconnect", re.I),
           "kicked": re.compile(r"kick", re.I), "denied": re.compile(r"denied|AccessDenied", re.I),
           "exception": re.compile(r"Exception|at zombie\.", re.I), "checksum": re.compile(r"checksum", re.I),
           "run_state": re.compile(r"RUN\b")}
GC_UP_RX = re.compile(r"^\[(\d+(?:\.\d+)?)s\]")
GC_PAUSE_RX = re.compile(r"Pause [^\n]*?(\d+(?:\.\d+)?)ms\s*$")
GC_STALL_RX = re.compile(r"Allocation Stall \([^)]*\) (\d+(?:\.\d+)?)ms")

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir(PREFIX)
path = os.path.join(run_dir, ARTIFACT)
fake_dir = os.path.join(run_dir, "fake")
tl, t0 = Timeline(), time.time()
server = None
fake = {"proc": None, "launch_epoch": None, "killed": None, "fh": None}
cur_phase = {"name": "pre"}
launch = {"epoch_ms": None}
watch = {"stop": False, "min_free": None, "kill": None}


def wall():
    return round(time.time() - t0, 3)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class _MemStat(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_gb():
    try:
        m = _MemStat()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return round(m.ullAvailPhys / float(2 ** 30), 2)
    except Exception:                          # noqa: BLE001 - a missing reading is recorded as None
        return None


def ws_mb(pid):
    """The working set of one process in MB from tasklist, or None."""
    if pid is None:
        return None
    try:
        p = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True,
                           text=True, timeout=20)
        line = (p.stdout or "").strip().splitlines()
        if not line or "," not in line[0]:
            return None
        cells = [c.strip('"') for c in line[0].split('","')]
        kb = re.sub(r"[^0-9]", "", cells[-1])
        return round(int(kb) / 1024.0, 1) if kb else None
    except Exception:                          # noqa: BLE001
        return None


def fake_alive():
    p = fake["proc"]
    return p is not None and p.poll() is None


def mem(tag):
    row = {"tag": tag, "wall": wall(), "free_gb": free_gb(),
           "server_ws_mb": ws_mb(server.proc.pid if server is not None and server.proc is not None else None),
           "fake_ws_mb": ws_mb(fake["proc"].pid if fake_alive() else None), "fake_alive": fake_alive()}
    out["memory"].append(row)
    return row


def note(msg):
    out["notes"].append({"wall": wall(), "phase": cur_phase["name"], "note": msg})


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001 - never raise on the write path
        print(f"could not write {path}: {type(e).__name__}: {e}")


def step(name, cmd, args="", timeout=30):
    t_before, e_before = wall(), time.time()
    try:
        v = ask(server, cmd, args, timeout=timeout)
    except Exception as e:                     # noqa: BLE001
        v = {"error": f"{type(e).__name__}: {e}"}
    t_after = wall()
    row = {"step": name, "cmd": cmd, "args": args, "phase": cur_phase["name"], "wall_before": t_before,
           "wall_after": t_after, "epoch_ms_before": int(e_before * 1000), "epoch_ms_after": int(time.time() * 1000),
           "took": round(t_after - t_before, 3), "ack": v}
    out["steps"].append(row)
    return row


def ack(r):
    return r["ack"] if isinstance(r.get("ack"), dict) else {}


def keep(r):
    a = dict(ack(r))
    a["wall"] = r["wall_before"]
    a["wall_after"] = r["wall_after"]
    a["epoch_ms_before"] = r.get("epoch_ms_before")
    a["epoch_ms_after"] = r.get("epoch_ms_after")
    if not isinstance(r.get("ack"), dict):
        a["raw"] = r.get("ack")
    return a


def online(tag):
    r = step(tag, "players")
    v = r.get("ack")
    names = v if isinstance(v, list) else ([] if isinstance(v, dict) and not v else None)
    fakes = sorted(n for n in (names or []) if isinstance(n, str) and n.startswith("Client"))
    row = {"tag": tag, "wall": r["wall_before"], "online": len(names) if names is not None else None,
           "fakes": len(fakes), "names": fakes if names is not None else None}
    if names is None:
        row["raw"] = v
    out["online"].append(row)
    return row


def wait_doc(name, after, timeout=RESULT_WAIT_S):
    try:
        return server.bus.wait_result(name, timeout=timeout, after=after)
    except Exception as e:                     # noqa: BLE001
        note(f"result {name}: {type(e).__name__}: {e}")
        return None


def pct(xs, p):
    s = sorted(xs)
    if not s:
        return None
    k = max(1, min(len(s), math.ceil(round(p * len(s), 9))))
    return s[k - 1]


def summ(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return {"n": len(xs), "p50": pct(xs, 0.5), "p99": pct(xs, 0.99), "max": max(xs) if xs else None,
            "min": min(xs) if xs else None, "mean": (sum(xs) / len(xs)) if xs else None,
            "p99_reachable": len(xs) >= 100}


def nonneg(xs):
    """The ring's first frame carries -1 (no previous frame) in period and endPeriod: left out."""
    return [x for x in xs if isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0]


def frames_of(doc):
    F = (doc or {}).get("frames_list") or {}
    keys = ("frame", "start", "stop", "busy", "period", "endPeriod", "minute")
    cols = [F.get(k) or [] for k in keys]
    n = min(len(c) for c in cols) if cols else 0
    return [dict(zip(keys, (c[i] for c in cols))) for i in range(n)]


def overlaps(f, wins):
    lo, hi = f.get("start"), f.get("stop")
    for w in wins:
        if None in (lo, hi, w[0], w[1]):
            continue
        if lo <= w[1] and hi >= w[0]:
            return True
    return False


def perf_series(doc):
    """perf.local's per-window max series, whatever the document names it."""
    if not isinstance(doc, dict):
        return []
    for k in ("maxes", "max_list", "series"):
        v = doc.get(k)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, (int, float))]
        if isinstance(v, dict) and isinstance(v.get("max"), list):
            return [x for x in v["max"] if isinstance(x, (int, float))]
    S = doc.get("samples_list") or doc.get("samples")
    if isinstance(S, dict) and isinstance(S.get("max"), list):
        return [x for x in S["max"] if isinstance(x, (int, float))]
    return []


def window(tag, n_target):
    """One idle reading: perf.local and tick.ring over RING_WALL_S, read both, summarise."""
    W = {"tag": tag, "N_target": n_target, "mem_before": mem(f"{tag}_0"), "online_before": online(f"{tag}_on0")}
    W["perf_arm"] = keep(step(f"{tag}_perf_arm", "perf.local", str(PERF_N)))
    W["ring_arm"] = keep(step(f"{tag}_ring_arm", "tick.ring", str(RING_N)))
    W["window_start_wall"] = wall()
    time.sleep(RING_WALL_S)
    W["window_end_wall"] = wall()
    after = time.time() - 1.0
    rr = step(f"{tag}_ring_read", "tick.ring", f"read {tag}")
    pr = step(f"{tag}_perf_read", "perf.local", f"read {tag}")
    W["ring_read"], W["perf_read"] = keep(rr), keep(pr)
    ring_doc = wait_doc(f"tick-ring-{tag}", after)
    perf_doc = wait_doc(f"perf-local-{tag}", after)
    W["ring_doc_present"], W["perf_doc_present"] = ring_doc is not None, perf_doc is not None
    if isinstance(perf_doc, dict):
        W["perf_doc"] = perf_doc
    drops = [[rr.get("epoch_ms_before"), rr.get("epoch_ms_after")], [pr.get("epoch_ms_before"), pr.get("epoch_ms_after")]]
    fr = frames_of(ring_doc)
    kept = [f for f in fr if not overlaps(f, drops)]
    W["frames"] = {"all": len(fr), "kept": len(kept), "dropped": len(fr) - len(kept)}
    W["summary"] = {"busy": summ([f["busy"] for f in kept]), "period": summ(nonneg([f["period"] for f in kept])),
                    "endPeriod": summ(nonneg([f["endPeriod"] for f in kept])),
                    "perf_window_max": summ(perf_series(perf_doc))}
    W["online_after"] = online(f"{tag}_on1")
    W["mem_after"] = mem(f"{tag}_1")
    W["fake_log"] = fake_counts()
    out["windows"].append(W)
    persist()
    return W


# ---------------------------------------------------------------- the fake JVM
def scenario():
    moves = []
    for i in range(1, NMAX + 1):
        g = (i - 1) // STEP
        town = TOWNS[(i - 1) % len(TOWNS)]
        k = (i - 1) // len(TOWNS)
        x, y = town[0] + GRID * (k % 5), town[1] + GRID * (k // 5)
        moves.append({"id": i, "description": f"x245 group {g}", "spawn": {"x": x, "y": y}, "type": "Circle",
                      "radius": 10, "motion": "Walk", "connect": int((FIRST_S + g * STEP_S) * 1000)})
    return {"version": "x245", "config": {
        "client": {"connection": {"serverHost": "127.0.0.1", "interval": 1000, "timeout": 60000, "delay": 10000},
                   "statistics": {"period": 0, "id": 0}},
        "player": {"fps": FAKE_FPS, "predict": FAKE_PREDICT},
        "movement": {"radius": 10, "motion": {"aim": 2, "sneak": 3, "sneakrun": 4, "walk": 3, "run": 5, "sprint": 7,
                                              "pedestrian": {"min": 5, "max": 20},
                                              "vehicle": {"min": 10, "max": 30}}}},
        "movements": moves}


def fake_cmd(scen_path):
    return [JAVA, "--enable-native-access=ALL-UNNAMED", FAKE_XMX,
            "-Ddeployment.user.cachedir=" + os.path.join(fake_dir, "cache"),
            "-Djava.library.path=" + ";".join([PZ_DIR + os.sep, os.path.join(PZ_DIR, "natives") + os.sep,
                                               os.path.join(PZ_DIR, "natives", "win64") + os.sep]),
            "-cp", PZ_DIR + os.sep + ";" + os.path.join(PZ_DIR, "projectzomboid.jar"),
            "zombie.network.FakeClientManager", "-scenarios=" + scen_path]


def fake_launch():
    os.makedirs(os.path.join(fake_dir, "cache"), exist_ok=True)
    scen_path = os.path.join(run_dir, SCENARIO)
    with open(scen_path, "w", encoding="utf-8") as fh:
        json.dump(scenario(), fh, indent=1)
    cmd = fake_cmd(scen_path)
    out["fake"]["cmd"] = cmd
    fake["fh"] = open(os.path.join(run_dir, FAKE_LOG), "w", encoding="utf-8", errors="replace")
    fake["proc"] = subprocess.Popen(cmd, cwd=fake_dir, stdin=subprocess.DEVNULL, stdout=fake["fh"],
                                    stderr=subprocess.STDOUT)
    fake["launch_epoch"] = time.time()
    out["fake"]["pid"] = fake["proc"].pid
    out["fake"]["launch_wall"] = wall()
    tl.mark("fake_launch", pid=fake["proc"].pid)


def fake_kill(why):
    if fake_alive():
        try:
            subprocess.run(["taskkill", "/PID", str(fake["proc"].pid), "/T", "/F"], capture_output=True, timeout=30)
        except Exception as e:                 # noqa: BLE001
            note(f"fake kill: {type(e).__name__}: {e}")
        try:
            fake["proc"].wait(15)
        except Exception:                      # noqa: BLE001
            pass
    if fake["killed"] is None:
        fake["killed"] = {"wall": wall(), "why": why, "rc": fake["proc"].poll() if fake["proc"] else None}
        out["fake"]["killed"] = fake["killed"]
        tl.mark("fake_killed", why=why)


def fake_counts():
    p = os.path.join(run_dir, FAKE_LOG)
    c = {k: 0 for k in FAKE_RX}
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for k, rx in FAKE_RX.items():
                    if rx.search(line):
                        c[k] += 1
    except OSError:
        pass
    c["alive"] = fake_alive()
    return c


def fake_lines(limit):
    keep_rx = re.compile(r"ERROR|WARN|Exception|denied|kick|checksum|disconnect|connected|failed|Player", re.I)
    p = os.path.join(run_dir, FAKE_LOG)
    hits, total = [], 0
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                total += 1
                if keep_rx.search(line) and len(hits) < limit:
                    hits.append(line.rstrip()[:400])
    except OSError:
        pass
    return {"lines_total": total, "lines": hits}


def watcher():
    while not watch["stop"]:
        f = free_gb()
        if f is not None:
            if watch["min_free"] is None or f < watch["min_free"]:
                watch["min_free"] = f
            if f < WATCH_KILL_GB and fake_alive():
                watch["kill"] = {"wall": wall(), "free_gb": f}
                fake_kill(f"watcher: free memory {f} GB under {WATCH_KILL_GB} GB")
        time.sleep(WATCH_S)


def sleep_until(epoch):
    d = epoch - time.time()
    if d > 0:
        time.sleep(d)


# ---------------------------------------------------------------- phases
def phase_S0():
    out["phases"]["S0"] = {"time": keep(step("S0_time", "time.snapshot")), "perf_now": keep(step("S0_perf_now", "perf.local", "now"))}
    window("N00", 0)


def phase_RAMP():
    R = out["phases"]["RAMP"] = {"steps": [], "stopped": None}
    fake_launch()
    for g in range(NMAX // STEP):
        n_target = (g + 1) * STEP
        t_connect = fake["launch_epoch"] + FIRST_S + g * STEP_S
        sleep_until(t_connect - 5.0)
        pre = mem(f"g{g}_pre")
        row = {"group": g, "N_target": n_target, "pre": pre}
        R["steps"].append(row)
        if not fake_alive():
            R["stopped"] = {"group": g, "why": "the fake JVM is not running", "rc": fake["proc"].poll()}
            break
        if pre["free_gb"] is not None and pre["free_gb"] < STOP_FREE_GB:
            fake_kill(f"free memory {pre['free_gb']} GB under {STOP_FREE_GB} GB before group {g}")
            R["stopped"] = {"group": g, "why": "memory", "free_gb": pre["free_gb"]}
            break
        sleep_until(t_connect + JOIN_WAIT_S)
        W = window(f"N{n_target:02d}", n_target)
        row["online_before"] = W["online_before"]["online"]
        row["online_after"] = W["online_after"]["online"]
        if g >= 1 and not any((o.get("online") or 0) > 0 for o in out["online"]):
            R["stopped"] = {"group": g, "why": "no fake client online after group 1's window: the join failed"}
            fake_kill("no join")
            break
    R["max_online"] = max([o.get("online") or 0 for o in out["online"]] or [0])


def phase_HOLD():
    H = out["phases"]["HOLD"] = {}
    last = out["online"][-1]["online"] if out["online"] else 0
    H["start_online"] = last
    if not fake_alive() or (last or 0) < HOLD_MIN:
        H["skipped"] = f"{last} online after the ramp (< {HOLD_MIN}) or the fake JVM is not running"
        return
    t_end = time.time() + HOLD_S - RING_WALL_S - 20.0
    while time.time() < t_end:
        online(f"hold_{int(wall())}")
        mem(f"hold_{int(wall())}")
        persist()
        time.sleep(min(HOLD_EVERY_S, max(0.0, t_end - time.time())))
    W = window("HOLD", NMAX)
    hold_rows = [o for o in out["online"] if o["tag"].startswith("hold_") or o["tag"].startswith("HOLD_")]
    H["min_online"] = min([o.get("online") or 0 for o in hold_rows] or [0])
    H["samples"] = len(hold_rows)
    H["wall_span"] = [hold_rows[0]["wall"], hold_rows[-1]["wall"]] if hold_rows else None
    H["ring"] = W["summary"]


def phase_Z():
    Z = out["phases"]["Z"] = {}
    Z["online_before_kill"] = online("Z_on0")
    fake_kill("end of session")
    time.sleep(DISCONNECT_WAIT_S)
    Z["online_after_kill"] = online("Z_on1")
    Z["mem"] = mem("Z")


def run_phase(name, fn):
    cur_phase["name"] = name
    out["phase_walls"][name] = {"start": wall()}
    try:
        fn()
    except Exception as e:                     # noqa: BLE001
        out["phase_errors"][name] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-3000:]}
        tl.mark("error", phase=name, detail=str(e)[:200])
        note(f"phase {name} raised: {type(e).__name__}: {e}")
    out["phase_walls"][name]["end"] = wall()
    persist()


def body():
    th = threading.Thread(target=watcher, daemon=True)
    for name, fn in (("S0", phase_S0), ("RAMP", phase_RAMP), ("HOLD", phase_HOLD), ("Z", phase_Z)):
        if name == "RAMP":
            th.start()
        run_phase(name, fn)
    watch["stop"] = True
    out["watch"] = {"min_free_gb": watch["min_free"], "kill": watch["kill"]}


# ---------------------------------------------------------------- after the session
def grep_noecho(log, rx, limit):
    hits, skipped = [], 0
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not rx.search(line):
                    continue
                if ECHO_RX.search(line):
                    skipped += 1
                    continue
                hits.append(line.strip()[:600])
                if len(hits) >= limit:
                    break
    except OSError:
        pass
    return hits, skipped


def read_gc():
    p = os.path.join(run_dir, GCLOG)
    G = out["gc"] = {"exists": os.path.isfile(p)}
    if not G["exists"]:
        return
    with open(p, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    pauses, stalls = [], []
    for ln in lines:
        if not GC_UP_RX.search(ln):
            continue
        ms, mp = GC_STALL_RX.search(ln), GC_PAUSE_RX.search(ln)
        if ms:
            stalls.append(float(ms.group(1)))
        elif mp:
            pauses.append(float(mp.group(1)))
    G.update({"bytes": os.path.getsize(p), "lines": len(lines), "pause_events": len(pauses),
              "pause_max_ms": max(pauses) if pauses else None, "stall_events": len(stalls),
              "stall_max_ms": max(stalls) if stalls else None})


def grade_all():
    S = out["summaries"]
    rows = []
    for W in out["windows"]:
        s = W["summary"]
        rows.append({"tag": W["tag"], "N_target": W["N_target"], "online_before": W["online_before"]["online"],
                     "online_after": W["online_after"]["online"], "frames_kept": W["frames"]["kept"],
                     "busy_p50": s["busy"]["p50"], "busy_p99": s["busy"]["p99"], "busy_max": s["busy"]["max"],
                     "busy_mean": s["busy"]["mean"], "endPeriod_p50": s["endPeriod"]["p50"],
                     "endPeriod_p99": s["endPeriod"]["p99"], "endPeriod_max": s["endPeriod"]["max"],
                     "period_p99": s["period"]["p99"], "perf_max_p99": s["perf_window_max"]["p99"],
                     "perf_max_max": s["perf_window_max"]["max"], "free_gb_after": W["mem_after"]["free_gb"],
                     "server_ws_mb_after": W["mem_after"]["server_ws_mb"], "fake_ws_mb_after": W["mem_after"]["fake_ws_mb"]})
    S["by_N"] = rows
    joined = max([o.get("fakes") or 0 for o in out["online"]] or [0])
    S["max_fakes_online"] = joined
    out["verdicts"]["J"] = {"predicted": "at least one fake online at group 0's read",
                            "observed": joined, "verdict": "held" if joined > 0 else "falsified",
                            "failure_read": None if joined > 0 else {"fake": fake_lines(80)}}
    pts = [(r["online_after"], r["busy_mean"]) for r in rows
           if isinstance(r.get("online_after"), int) and isinstance(r.get("busy_mean"), (int, float))
           and r["frames_kept"] >= MIN_FRAMES]
    if len(pts) >= 3 and len({p[0] for p in pts}) >= 2:
        n = len(pts)
        mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx else None
        S["busy_mean_fit"] = {"points": pts, "slope_ms_per_player": slope,
                              "intercept_ms": (my - slope * mx) if slope is not None else None,
                              "note": "least squares of each window's mean busy on its online count after the window"}
        out["verdicts"]["L"] = {"predicted": f"slope <= {VANILLA_MS_PER_PLAYER_MAX} ms a player", "observed": slope,
                                "verdict": None if slope is None else ("held" if slope <= VANILLA_MS_PER_PLAYER_MAX
                                                                       else "falsified")}
        idle = rows[0]["endPeriod_p99"] if rows else None
        worst = max([r["endPeriod_p99"] for r in rows if isinstance(r.get("endPeriod_p99"), (int, float))] or [None])
        out["verdicts"]["L_p99"] = {"predicted": f"endPeriod p99 <= idle + {RULE_P99_ADD} ms at every N",
                                    "idle": idle, "worst": worst,
                                    "verdict": None if idle is None or worst is None else
                                    ("held" if worst <= idle + RULE_P99_ADD else "falsified")}
    else:
        out["verdicts"]["L"] = {"verdict": "unmeasured", "why": "fewer than three windows with players online"}
    H = out["phases"].get("HOLD") or {}
    if "min_online" in H:
        out["verdicts"]["H"] = {"predicted": f">= {HOLD_MIN} online through {HOLD_S} s", "observed": H["min_online"],
                                "verdict": "held" if H["min_online"] >= HOLD_MIN else "falsified"}
    else:
        out["verdicts"]["H"] = {"verdict": "not run", "why": H.get("skipped")}
    out["verdicts"]["arms"] = {"verdict": "not run", "why": "no harness command drives P.work for online usernames "
                               "on a schedule, and this session loads no NutritionRevamp (vanilla denominator only)"}


# ---------------------------------------------------------------- main
doctor_clean, doctor_text = doctor()
out = {
    "run_id": run_id, "session": SESSION, "profile": prof.report(),
    "fixture": {"name": rec_fx.get("name"), "provision_run": rec_fx.get("provision_run")},
    "argv": sys.argv[1:], "commit": git_say("rev-parse", "--short", "HEAD"),
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR), "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "harness_py_commit": git_say("log", "-1", "--format=%h", "--", "testing/pzt"),
    "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
    "meta": {"server_port": PORT, "ini_run_copy": {k: (str(v).lower()) for k, v in INI.items()},
             "no_mod": "PZTestKit only: no NutritionRevamp is loaded, so the frames carry vanilla plus the ring hooks",
             "no_game_client": "no game client is attached; the only players are the fake clients",
             "read_only_install": "the fake JVM runs from the install's jre64 and classpath with its cwd and cache "
                                  "dir in the run dir",
             "timer_note": "getTimestampMs is 1 ms resolution; busy and endPeriod are 1 ms readings"},
    "constants": {k: (v.pattern if isinstance(v, re.Pattern) else v) for k, v in globals().items()
                  if re.match(r"^[A-Z][A-Z0-9_]+$", k) and isinstance(v, (int, float, str, bool, tuple, dict, re.Pattern))
                  and k not in ("REPO", "FAKE_RX")},
    "predictions": {"J": "at least one fake online at group 0's read",
                    "L": f"busy rises <= {VANILLA_MS_PER_PLAYER_MAX} ms a player; endPeriod p99 <= idle + {RULE_P99_ADD}",
                    "H": f">= {HOLD_MIN} online through the {HOLD_S} s hold, if reached"},
    "fake": {}, "steps": [], "notes": [], "phases": {}, "phase_errors": {}, "phase_walls": {}, "verdicts": {},
    "summaries": {}, "memory": [], "online": [], "windows": [],
}
try:
    out["meta"]["harness_server_sha256"] = sha256_file(os.path.join(REPO, HARNESS_SERVER))
except OSError as e:
    out["meta"]["hash_error"] = f"{type(e).__name__}: {e}"

if not doctor_clean:
    out["error"] = "doctor is not clean; the session was not started"
    persist()
    print(doctor_text)
    sys.exit(1)
_m0 = mem("preboot")
if _m0["free_gb"] is None or _m0["free_gb"] < MIN_FREE_GB:
    out["error"] = f"free memory {_m0['free_gb']} GB under {MIN_FREE_GB} GB; the session was not started"
    persist()
    print(out["error"])
    sys.exit(1)
lint_errors = lint_paths(prof.sources)
out["lint_errors"] = lint_errors
if lint_errors:
    out["error"] = "the layout lint found an ERROR in a profile mod folder; the session was not started"
    persist()
    sys.exit(1)

try:
    server = make_server(run_dir, rec_fx, port=PORT, rcon_port=RCON_PORT, mods=prof.mods, mod_sources=prof.sources,
                         mod_skip=prof.skip, sandbox=prof.sandbox or None, ini={**(prof.ini or {}), **INI},
                         gclog=prof.gclog)
    try:
        with open(server.ini, encoding="utf-8") as fh:
            out["meta"]["ini_lines"] = [ln.strip() for ln in fh if re.match(r"^(MaxPlayers|DoLuaChecksum|Open|Password|"
                                                                              r"DefaultPort|UDPPort|PauseEmpty|"
                                                                              r"DenyLoginOnOverloadedServer)=", ln)]
    except OSError as e:
        out["meta"]["ini_read_error"] = f"{type(e).__name__}: {e}"
    out["server_launch_wall"] = wall()
    launch["epoch_ms"] = int(time.time() * 1000)
    server.start(timeout=prof.server_timeout)
    out["server_started_wall"] = wall()
    out["build"] = server.build
    tl.mark("server_started")
    out["verify"] = verify(prof, server, {}, tl)
    mem("ready")
    persist()
    try:
        body()
    except Exception as e:                     # noqa: BLE001
        out["body_error"], out["body_traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
    persist()
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
finally:
    watch["stop"] = True
    fake_kill("teardown")
    try:
        if fake["fh"] is not None:
            fake["fh"].close()
    except Exception:                          # noqa: BLE001
        pass
    try:
        if server is not None:
            teardown(tl, server, [])
    except Exception as e:                     # noqa: BLE001
        out["teardown_error"] = f"{type(e).__name__}: {e}"
    finally:
        if server is not None:
            hard_kill(server, [])
        if server is not None:
            out["server_errors"] = server.errors[:30]
            out["server_error_count"] = len(server.errors)
            out["server_join_lines"], out["server_join_echo_excluded"] = grep_noecho(server.log_path, SRV_JOIN_RX,
                                                                                     LOG_LIMIT)
        out["fake_log"] = {"counts": fake_counts(), **fake_lines(LOG_LIMIT)}
        try:
            read_gc()
        except Exception as e:                 # noqa: BLE001
            out["gc_error"] = f"{type(e).__name__}: {e}"
        try:
            grade_all()
        except Exception as e:                 # noqa: BLE001
            out["summary_error"] = f"{type(e).__name__}: {e}"
            out["summary_traceback"] = traceback.format_exc()[-3000:]
        out["wall_seconds"] = round(time.time() - t0, 1)
        persist()
        dest_dir = os.path.join(REPO, "testing", "artifacts", run_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copyfile(path, os.path.join(dest_dir, ARTIFACT))
            for nm in (SCENARIO, GCLOG):
                if os.path.isfile(os.path.join(run_dir, nm)):
                    shutil.copyfile(os.path.join(run_dir, nm), os.path.join(dest_dir, nm))
            fl = os.path.join(run_dir, FAKE_LOG)
            if os.path.isfile(fl) and os.path.getsize(fl) <= FAKE_LOG_COPY_MAX:
                shutil.copyfile(fl, os.path.join(dest_dir, FAKE_LOG))
            print(f"artifact copied to {dest_dir}")
        except OSError as e:
            print(f"artifact copy failed: {type(e).__name__}: {e}")
        print(json.dumps({"run_id": run_id, "verdicts": out["verdicts"], "by_N": out["summaries"].get("by_N")},
                         indent=1, default=str)[:6000])
