#!/usr/bin/env python3
"""Spike S2 / `pzt join`: launch a real game client with auto-connect args into
an isolated cachedir, observe which states it reaches (from its console.txt),
then kill it. Reports the state timeline and any screens it got stuck on.
"""
import os, re, sys, time, json, argparse, datetime, subprocess

PZ_DIR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid"
EXE = os.path.join(PZ_DIR, "ProjectZomboid64.exe")
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, "..", "runs"))

# State markers to look for in the client console (order of appearance matters).
# The client logs game-state transitions as "STATE: enter/exit zombie.gameStates.<X>"
# (learned in spike S2). Match those plus a few network/lua signatures.
MARKERS = [
    ("tos_screen",       r"STATE: enter zombie\.gameStates\.TermsOfServiceState"),
    ("tos_accepted",     r"STATE: exit zombie\.gameStates\.TermsOfServiceState"),
    ("main_menu",        r"STATE: enter zombie\.gameStates\.MainScreenState"),
    ("connect_state",    r"STATE: enter zombie\.gameStates\.ConnectToServerState"),
    ("connecting",       r"[Cc]onnecting to|LoginPacket|ConnectionManager"),
    ("connected",        r"[Cc]onnected to server|received ServerResponse|Connection accepted"),
    ("char_creation",    r"CoopCharacterCreation|CharacterCreationMain"),
    ("loading_world",    r"STATE: enter zombie\.gameStates\.GameLoadingState|ClientChunkRequest"),
    ("in_game",          r"STATE: enter zombie\.gameStates\.IngameState|OnGameStart|game loading took \d+ seconds"),
    ("lua_error",        r"LuaError|STACK TRACE|lua error"),
    ("kicked",           r"[Kk]icked|[Dd]isconnect(ed)? from server|connection lost|Connection failed"),
    ("state_other",      r"STATE: enter zombie\.gameStates\.\w+"),
]
# Harness (PZTestKitClient) log lines are all reported, in order, as their own events.
HARNESS_RX = re.compile(r"PZTK: (.*)")

HARNESS_SRC = os.path.abspath(os.path.join(HERE, "..", "PZTestKit", "PZTestKitClient"))

def seed_client_cache(cache, args):
    """Golden-client essentials: T&C pre-accepted, harness mod installed + enabled,
    join manifest written. Learned in spike S2."""
    import shutil
    # 1. options.ini with the T&C acceptance flag (skips TermsOfServiceState)
    with open(os.path.join(cache, "options.ini"), "w") as fh:
        fh.write("termsOfServiceVersion=1\n")
    # 2. harness mod into <cachedir>/mods/ and enable it (ScriptParser block format)
    dst = os.path.join(cache, "mods", "PZTestKitClient")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(HARNESS_SRC, dst)
    with open(os.path.join(cache, "mods", "default.txt"), "w") as fh:
        fh.write("VERSION = 1,\n\nmods\n{\n    mod = PZTestKitClient,\n}\n\nmaps\n{\n}\n")
    # ZomboidFileSystem.resetDefaultModsForNewRelease: if this marker is missing the
    # game writes it AND wipes default.txt on first launch. Seeding it keeps our list.
    # (Marker name is per major release: 42_00 for all of B42.)
    with open(os.path.join(cache, "mods", "reset-mods-42_00.txt"), "w") as fh:
        fh.write("If this file does not exist, default.txt will be reset to empty (no mods active).")
    # 3. manifest read by the harness via getFileReader (<cachedir>/Lua/)
    os.makedirs(os.path.join(cache, "Lua"), exist_ok=True)
    ip, port = args.server.split(":")
    with open(os.path.join(cache, "Lua", "pzt-join.txt"), "w") as fh:
        fh.write(f"username={args.username}\npassword={args.account_password}\n"
                 f"ip={ip}\nport={port}\nserverPassword={args.password}\n")
    # 4. pre-saved server + account so the join popup prefills credentials
    seed_serverlist(cache, ip, port, args.username, args.account_password, args.password)
    # 5. debug-mode conveniences: GameWindow.initShared skips TISLogoState only when
    #    Core.debug && DebugOptions UI.DisableLogoState (persisted in debug-options.ini).
    #    Requires an admin account (servers refuse -debug for non-admins).
    if args.debug:
        with open(os.path.join(cache, "debug-options.ini"), "w") as fh:
            fh.write("UI.DisableLogoState=true\nUI.DisableWelcomeMessage=true\n")

SERVERLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS server (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
 ip TEXT NOT NULL, port INTEGER NOT NULL, serverPassword TEXT, description TEXT, mods TEXT,
 icon BLOB, banner BLOB, panelBackground BLOB, screenBackground BLOB, lastOnline TEXT, lastDataUpdate TEXT);
CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY AUTOINCREMENT, serverId INTEGER NOT NULL,
 playerFirstAndLastName TEXT, username TEXT NOT NULL, password TEXT, isSavePassword INTEGER DEFAULT 0,
 isUseSteamRelay INTEGER DEFAULT 0, authType INTEGER DEFAULT 1, icon BLOB, timePlayed INTEGER DEFAULT 0,
 lastLogon TEXT, FOREIGN KEY (serverId) REFERENCES server (id));
"""

def seed_serverlist(cache, ip, port, username, password, server_password=""):
    """Pre-save the server + account in the client's ServerList.db (schema captured in
    spike S2) so ServerConnectPopup:setServer prefills credentials from getServerList()."""
    import sqlite3
    os.makedirs(os.path.join(cache, "db"), exist_ok=True)
    con = sqlite3.connect(os.path.join(cache, "db", "ServerList.db"))
    con.executescript(SERVERLIST_SCHEMA)
    cur = con.execute("INSERT INTO server (name, ip, port, serverPassword) VALUES (?,?,?,?)",
                      ("pzt", ip, int(port), server_password))
    con.execute("INSERT INTO account (serverId, username, password, isSavePassword, authType) VALUES (?,?,?,1,1)",
                (cur.lastrowid, username, password))
    con.commit(); con.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="127.0.0.1:27261")
    ap.add_argument("--username", default="pzt_c1")
    ap.add_argument("--account-password", default="pzt-c1-pw")
    ap.add_argument("--password", default="")
    ap.add_argument("--observe", type=int, default=120, help="seconds to observe before killing")
    ap.add_argument("--client-id", type=int, default=1)
    ap.add_argument("--extra", default="", help="extra game args")
    ap.add_argument("--debug", action="store_true", help="launch client in -debug mode (admin accounts only)")
    ap.add_argument("--exit-on-spawn", action="store_true", help="stop observing once the client is in-world")
    ap.add_argument("--reuse-cache", default="", help="existing client cachedir (warm run: account/character persist)")
    ap.add_argument("--launcher", choices=["java", "exe"], default="java",
                    help="java: start the JVM directly (no UAC prompt); exe: use ProjectZomboid64.exe")
    args = ap.parse_args()

    run_id = datetime.datetime.now().strftime("s2-%Y%m%d-%H%M%S")
    run_dir = os.path.join(RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    if args.reuse_cache:
        cache = os.path.abspath(args.reuse_cache)   # warm run: existing account/character/assets
        # keep the manifest current but don't disturb the game-written options/db
        os.makedirs(os.path.join(cache, "Lua"), exist_ok=True)
        ip, port = args.server.split(":")
        with open(os.path.join(cache, "Lua", "pzt-join.txt"), "w") as fh:
            fh.write(f"username={args.username}\npassword={args.account_password}\n"
                     f"ip={ip}\nport={port}\nserverPassword={args.password}\n")
    else:
        cache = os.path.join(run_dir, f"client{args.client_id}")
        os.makedirs(cache, exist_ok=True)
        seed_client_cache(cache, args)

    game_args = ["-nosteam", f"-cachedir={cache}", "-safemode", "-nosound", "-novoip",
                 "-debuglog=Network", "+connect", args.server]
    if args.debug:
        # Servers reject debug-mode clients on non-admin accounts ("debug connection
        # not allowed for non admin") — only use with an admin test account.
        game_args.insert(5, "-debug")
    if args.password:
        game_args += ["+password", args.password]
    if args.extra:
        game_args += args.extra.split()
    if args.launcher == "exe":
        cmd = [EXE] + game_args
    else:
        # Bypass ProjectZomboid64.exe (it triggers a UAC prompt); replicate its
        # ProjectZomboid64.json config and start the JVM directly, like the server does.
        java = os.path.join(PZ_DIR, "jre64", "bin", "java.exe")
        vm = ["-Djava.awt.headless=true", "--enable-native-access=ALL-UNNAMED",
              "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED", "-Xmx3072m",
              "-Dzomboid.steam=0", "-Dzomboid.znetlog=1", "-Djava.library.path=win64/;.",
              "-XX:-CreateCoredumpOnCrash", "-XX:-OmitStackTraceInFastThrow", "-XX:+UseZGC"]
        cmd = [java] + vm + ["-cp", ".;projectzomboid.jar", "zombie.gameStates.MainScreenState"] + game_args

    report = {"run_id": run_id, "cmd": cmd, "cache": cache, "timeline": []}
    t0 = time.time()
    def ev(kind, **kw):
        e = {"t": round(time.time() - t0, 1), "kind": kind, **kw}
        report["timeline"].append(e)
        print(f"[{e['t']:6.1f}s] {kind} {kw if kw else ''}", flush=True)

    ev("launch")
    proc = subprocess.Popen(cmd, cwd=PZ_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    console = os.path.join(cache, "console.txt")
    seen = {}
    pos = 0
    deadline = t0 + args.observe
    while time.time() < deadline:
        if proc.poll() is not None:
            ev("client_exited", returncode=proc.returncode)
            break
        if os.path.exists(console):
            if os.path.getsize(console) < pos:
                pos = 0  # the game rotated/truncated console.txt; re-read from the top
            with open(console, encoding="utf-8", errors="replace") as fh:
                fh.seek(pos)
                chunk = fh.read()
                pos = fh.tell()
            for line in chunk.splitlines():
                hm = HARNESS_RX.search(line)
                if hm:
                    ev("harness", msg=hm.group(1)[:160])
                for name, rx in MARKERS:
                    if name not in seen and re.search(rx, line):
                        seen[name] = line.strip()[:200]
                        ev(name, line=seen[name])
        if "in_game" in seen and args.exit_on_spawn:
            ev("spawned_exit", note="in-game marker seen; ending observation early")
            break
        time.sleep(1.0)
    if proc.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        ev("killed_after_observe")

    # tail of console for context
    tail = []
    if os.path.exists(console):
        with open(console, encoding="utf-8", errors="replace") as fh:
            tail = [l.rstrip()[:200] for l in fh.readlines()[-40:]]
    report["console_tail"] = tail
    report["states_seen"] = list(seen.keys())
    with open(os.path.join(run_dir, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print("\nSTATES:", " -> ".join(seen.keys()) or "(none)")
    print(f"console: {console}")

if __name__ == "__main__":
    main()
