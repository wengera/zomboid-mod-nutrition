#!/usr/bin/env python3
"""Spike S1 / `pzt boot`: start an isolated -nosteam dedicated server, wait for
the startup marker, quit cleanly, report timings and log signatures.

Isolation: own -cachedir under testing/runs/<run-id>/cache, own ports, no mods.
Shutdown: 'quit' on server stdin (primary); RCON probe (secondary, informational).
"""
import os, sys, time, json, threading, subprocess, socket, struct, argparse, datetime, re

PZ_DIR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid"
JAVA = os.path.join(PZ_DIR, "jre64", "bin", "java.exe")
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, "..", "runs"))

STARTED_PATTERNS = [r"\*\*\* SERVER STARTED", r"SERVER STARTED", r"Server started"]
ERROR_PATTERNS = [r"ERROR", r"Exception", r"STACK TRACE", r"LuaError", r"lua error"]
# Known vanilla 42.20.4 boot noise — matched lines are not counted as errors.
# Baseline established by spike S1 (2026-09-09): 57 error-shaped lines on a
# clean vanilla boot, all three signatures below. Re-baseline after game updates.
BASELINE_NOISE = [
    r"FluidContainerScript\.load .*Sanitizing container name",
    r"IsoPropertyType\.lookupOrDefaultStr> Exception thrown",
    r"BrokenFences\.addBrokenTiles .*Missing ThumpSound",
    r"IsoPropertyTypeNotFoundException: Property Name not found: (ladder[NSEW]|WindowShape)",
    r"CraftRecipeComponentScript: Recipe Piano missing UiConfigScript",
    r"handleMannequinZone .*Mannequin zone missing properties",
    r"Basements\.mergeRoomsOntoMetaCell .*duplicate RoomDef\.metaID",
    # every mod: the loader probes optional folders (AnimSets, actiongroups, ...)
    r"NoSuchFileException: .*[\\/]mods[\\/].*[\\/]media[\\/](AnimSets|actiongroups|anims_X|AnimSets_X)",
]

HARNESS_MODS = {"PZTestKitClient": os.path.abspath(os.path.join(HERE, "..", "PZTestKit", "PZTestKitClient"))}

def seed_ini(cache, name, port, rcon_port, rcon_pw, admin_pw, mods=()):
    """Server ini + any harness mods. Mods listed in Mods= are what the CLIENT
    reloads its Lua with after connecting (spike S2: locally-enabled client mods
    are dropped at join), so the harness must be server-listed and present in
    the server's own mods/ folder."""
    import shutil
    sdir = os.path.join(cache, "Server")
    os.makedirs(sdir, exist_ok=True)
    for mod_id in mods:
        src = HARNESS_MODS.get(mod_id)
        if src:
            dst = os.path.join(cache, "mods", mod_id)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    ini = os.path.join(sdir, f"{name}.ini")
    if not os.path.exists(ini):
        with open(ini, "w") as fh:
            fh.write(f"DefaultPort={port}\nUDPPort={port+1}\nRCONPort={rcon_port}\n"
                     f"RCONPassword={rcon_pw}\nPublic=false\nOpen=true\nSteamVAC=false\n"
                     f"Mods={';'.join(mods)}\nWorkshopItems=\nPauseEmpty=false\nUPnP=false\n")
    return ini

def rcon_probe(host, port, password, cmd="quit", timeout=5.0):
    """Minimal Source-RCON: auth then exec one command. Returns (ok, reply)."""
    def pkt(pid, ptype, body):
        b = body.encode() + b"\x00\x00"
        return struct.pack("<iii", len(b) + 8, pid, ptype) + b
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(pkt(1, 3, password))
            hdr = s.recv(4096)
            if len(hdr) < 12:
                return False, "short auth reply"
            _, pid, _ = struct.unpack("<iii", hdr[:12])
            if pid == -1:
                return False, "auth refused"
            s.sendall(pkt(2, 2, cmd))
            try:
                reply = s.recv(4096)
            except socket.timeout:
                reply = b""
            return True, reply[12:].decode(errors="replace").strip("\x00")
    except OSError as e:
        return False, str(e)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="pzt")
    ap.add_argument("--port", type=int, default=27261)
    ap.add_argument("--rcon-port", type=int, default=27015)
    ap.add_argument("--startup-timeout", type=int, default=420)
    ap.add_argument("--shutdown", choices=["stdin", "rcon"], default="stdin")
    ap.add_argument("--keep-alive", type=int, default=10, help="seconds to idle after start")
    ap.add_argument("--mods", default="", help="semicolon-separated mod ids for Mods= (harness mods are copied in)")
    args = ap.parse_args()

    run_id = datetime.datetime.now().strftime("s1-%Y%m%d-%H%M%S")
    run_dir = os.path.join(RUNS, run_id)
    cache = os.path.join(run_dir, "cache")
    os.makedirs(cache, exist_ok=True)
    admin_pw, rcon_pw = "pzt-admin-pw", "pzt-rcon-pw"
    seed_ini(cache, args.name, args.port, args.rcon_port, rcon_pw, admin_pw,
             mods=[m for m in args.mods.split(";") if m])

    cmd = [JAVA, "--enable-native-access=ALL-UNNAMED",
           "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED",
           "-XX:+UseZGC", "-XX:-CreateCoredumpOnCrash", "-XX:-OmitStackTraceInFastThrow",
           "-Xmx3072m", "-Djava.library.path=./natives/;./natives/win64/;./",
           "-cp", "./;projectzomboid.jar", "zombie.network.GameServer",
           "-nosteam", "-servername", args.name, "-adminpassword", admin_pw,
           f"-cachedir={cache}", "-port", str(args.port), "-udpport", str(args.port + 1)]

    log_path = os.path.join(run_dir, "server-stdout.log")
    report = {"run_id": run_id, "cmd": cmd, "cache": cache, "events": []}
    t0 = time.time()
    def ev(kind, **kw):
        e = {"t": round(time.time() - t0, 1), "kind": kind, **kw}
        report["events"].append(e)
        print(f"[{e['t']:6.1f}s] {kind} {kw if kw else ''}", flush=True)

    ev("launch")
    proc = subprocess.Popen(cmd, cwd=PZ_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                            bufsize=1)
    started = threading.Event()
    errors = []
    lines = []
    def reader():
        with open(log_path, "w", encoding="utf-8") as fh:
            for line in proc.stdout:
                fh.write(line); fh.flush()
                lines.append(line)
                if not started.is_set() and any(re.search(p, line) for p in STARTED_PATTERNS):
                    started.set()
                if any(re.search(p, line) for p in ERROR_PATTERNS) and \
                        not any(re.search(p, line) for p in BASELINE_NOISE):
                    errors.append(line.rstrip()[:300])
    threading.Thread(target=reader, daemon=True).start()

    if not started.wait(args.startup_timeout):
        ev("startup_timeout", lines=len(lines), last=[l.rstrip()[:160] for l in lines[-8:]])
        proc.kill()
        report["result"] = "FAIL: no startup marker"
    else:
        ev("server_started", lines_so_far=len(lines))
        time.sleep(args.keep_alive)
        ok, reply = rcon_probe("127.0.0.1", args.rcon_port, rcon_pw, cmd="servermsg s1probe")
        ev("rcon_probe", ok=ok, reply=reply[:120])
        if args.shutdown == "rcon" and ok:
            ok2, reply2 = rcon_probe("127.0.0.1", args.rcon_port, rcon_pw, cmd="quit")
            ev("rcon_quit", ok=ok2, reply=reply2[:120])
        else:
            try:
                proc.stdin.write("quit\n"); proc.stdin.flush()
                ev("stdin_quit_sent")
            except OSError as e:
                ev("stdin_quit_failed", err=str(e))
        try:
            rc = proc.wait(timeout=120)
            ev("exited", returncode=rc)
            report["result"] = "PASS" if rc == 0 else f"EXIT {rc}"
        except subprocess.TimeoutExpired:
            proc.kill()
            ev("killed_after_quit_timeout")
            report["result"] = "FAIL: hung on quit"

    report["errors_seen"] = errors[:40]
    report["total_lines"] = len(lines)
    report["console_txt"] = os.path.join(cache, "server-console.txt")  # dedicated server's own log name
    with open(os.path.join(run_dir, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"\nRESULT: {report['result']}  ({len(lines)} lines, {len(errors)} error-ish lines)")
    print(f"log: {log_path}")

if __name__ == "__main__":
    main()
