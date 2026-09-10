"""Cold-start hygiene: what a fresh session must know before booting anything. Reports only."""
import os, re, subprocess, glob
from . import fixture as fx, mods
from .paths import RUNS

def _pz_java_pids():
    cmd = ["powershell", "-NoProfile", "-Command",
           "Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | ForEach-Object { \"$($_.ProcessId)|$($_.CommandLine)\" }"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [ln.split("|", 1)[0] for ln in out.splitlines() if "ProjectZomboid" in ln]

def _ports_in_use(ports):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return [p for p in ports if re.search(rf"[:.]{p}\s", out)]

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
    busy = _ports_in_use([27261, 27262, 27015])
    report("FAIL" if busy else "ok", f"ports 27261/27262/27015: {'in use ' + str(busy) if busy else 'free'}")
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
