"""Cold-start hygiene: what a fresh session must know before booting anything. Reports only."""
import os, re, subprocess, glob
from . import fixture as fx, mods
from .paths import RUNS

def _pz_java_pids():
    cmd = ["powershell", "-NoProfile", "-Command",
           "Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [ln.split("|", 1)[0] for ln in out.splitlines() if "ProjectZomboid" in ln]

# `netstat -ano` columns: Proto | Local Address | Foreign Address | State | PID -- UDP rows carry
# no State. Only these TCP states actually hold the port; a plain substring match over the whole
# output used to count the run's OWN closed RCON connection, which sits in TIME_WAIT on 27015 for
# ~2 min after every scenario, and false-FAILed this check for that long. Matching the LOCAL
# address column also stops a foreign address that happens to use the port from counting.
_HOLDS_PORT = ("LISTENING", "ESTABLISHED")

def _ports_in_use(ports):
    """-> (busy, ignored): ports held by a live socket, and the (port, state) pairs skipped."""
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    busy, ignored = set(), set()
    for line in out.splitlines():
        f = line.split()
        if len(f) < 4 or f[0].upper() not in ("TCP", "UDP"):
            continue
        port = f[1].rsplit(":", 1)[-1]                  # 0.0.0.0:27015 and [::]:27015 alike
        if not port.isdigit() or int(port) not in ports:
            continue
        # A bound UDP socket (the game ports) has no state and always holds the port.
        state = f[3].upper() if f[0].upper() == "TCP" and len(f) >= 5 else "BOUND"
        if state == "BOUND" or state in _HOLDS_PORT:
            busy.add(int(port))
        else:
            ignored.add((int(port), state))
    return sorted(busy), sorted(ignored)

def _installed_build():
    logs = sorted(glob.glob(os.path.join(RUNS, "*", "server-stdout.log")), key=os.path.getmtime)
    for log in reversed(logs):
        m = re.search(r"\bversion=(\d+\.\d+\.\d+)", open(log, encoding="utf-8", errors="replace").read())
        if m:
            return m.group(1)
    return None

def run(a):
    status = 0
    def report(level, msg):
        nonlocal status
        print(f"{level:4} {msg}")
        if level == "FAIL":
            status = 1
    pids = _pz_java_pids()
    report("WARN" if pids else "ok", f"PZ java processes: {pids or 'none'}" + (" — a previous session may still be running; do not boot until they exit" if pids else ""))
    busy, ignored = _ports_in_use([27261, 27262, 27015])
    msg = f"ports 27261/27262/27015: {'in use ' + str(busy) if busy else 'free'}"
    if ignored:
        # Named, not hidden: "free" while netstat shows the port is the one line here that would
        # otherwise look like the check is lying.
        msg += " (ignored, not holding the port: " + ", ".join(f"{p} {s}" for p, s in ignored) + ")"
    report("FAIL" if busy else "ok", msg)
    try:
        rec = fx.load("default")
        build = _installed_build()
        if build and build != rec.get("build"):
            report("FAIL", f"fixture build {rec.get('build')} != installed {build}: re-provision")
        else:
            report("ok", f"fixture 'default' present (build {rec.get('build')}, {rec.get('size_mb')} MB)")
    except SystemExit as e:
        report("FAIL", str(e))
    idx = mods.workshop_index()
    report("WARN" if not idx else "ok", f"workshop index: {len(idx)} mods")
    try:
        import pytest  # noqa: F401
        report("ok", "pytest available")
    except ImportError:
        report("WARN", "pytest missing (pip install pytest)")
    return status
