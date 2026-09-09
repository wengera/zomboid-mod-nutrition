"""Game client process, driven through the PZTestKit harness mod.

Control: the file-based command bus in <cachedir>/Lua/ (see bus.py).
Observation: the client's console.txt is tailed for STATE transitions and "PZTK:" lines.
"""
import os
import re
import sqlite3
import subprocess
import threading
import time

from . import harness, win32
from .bus import CommandBus
from .paths import EXE, JAVA, PZ_DIR

MARKERS = [
    ("tos_screen",    re.compile(r"STATE: enter zombie\.gameStates\.TermsOfServiceState")),
    ("main_menu",     re.compile(r"STATE: enter zombie\.gameStates\.MainScreenState")),
    ("connect_state", re.compile(r"STATE: enter zombie\.gameStates\.ConnectToServerState")),
    ("loading_world", re.compile(r"STATE: enter zombie\.gameStates\.(LoadingQueueState|GameLoadingState)")),
    ("in_game",       re.compile(r"STATE: enter zombie\.gameStates\.IngameState|game loading took \d+ seconds")),
    ("ready",         re.compile(r"PZTK: player \S+ at ")),
    ("lua_error",     re.compile(r"LuaError|STACK TRACE|lua error")),
    ("kicked",        re.compile(r"[Kk]icked|[Dd]isconnect(ed)? from server|connection lost|Connection failed")),
]
HARNESS_RX = re.compile(r"PZTK: (.*)")
MOD_MISSING_RX = re.compile(r'required mod "([^"]+)" not found')   # a WARN only; see spike S3

JVM = ["-Djava.awt.headless=true", "--enable-native-access=ALL-UNNAMED",
       "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED", "-Xmx3072m",
       "-Dzomboid.steam=0", "-Dzomboid.znetlog=1", "-Djava.library.path=win64/;.",
       "-XX:-CreateCoredumpOnCrash", "-XX:-OmitStackTraceInFastThrow", "-XX:+UseZGC",
       "-cp", ".;projectzomboid.jar"]

SERVERLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS server (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
 ip TEXT NOT NULL, port INTEGER NOT NULL, serverPassword TEXT, description TEXT, mods TEXT,
 icon BLOB, banner BLOB, panelBackground BLOB, screenBackground BLOB, lastOnline TEXT, lastDataUpdate TEXT);
CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY AUTOINCREMENT, serverId INTEGER NOT NULL,
 playerFirstAndLastName TEXT, username TEXT NOT NULL, password TEXT, isSavePassword INTEGER DEFAULT 0,
 isUseSteamRelay INTEGER DEFAULT 0, authType INTEGER DEFAULT 1, icon BLOB, timePlayed INTEGER DEFAULT 0,
 lastLogon TEXT, FOREIGN KEY (serverId) REFERENCES server (id));
"""


class Client:
    def __init__(self, cache, server, username, password, server_password="", debug=False,
                 safemode=False, launcher="java", mods=("PZTestKit",), echo=None, workshop=True):
        self.cache = os.path.abspath(cache)
        self.server = server
        self.ip, self.port = server.split(":")
        self.username = username
        self.password = password
        self.server_password = server_password
        self.debug = debug
        self.safemode = safemode
        self.launcher = launcher
        self.mods = list(mods)
        self.workshop = workshop
        self.missing_mods = []        # not placed in mods/ by us
        self.mods_not_found = []      # reported missing by the game at load
        self.echo = echo
        self.bus = CommandBus(os.path.join(self.cache, "Lua"), alive=lambda: self.alive)
        self.proc = None
        self.seen = {}
        self.events = []
        self.t0 = None
        self._stop = threading.Event()

    @property
    def console(self):
        return os.path.join(self.cache, "console.txt")

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    # ---- cache preparation -------------------------------------------------
    def seed(self):
        """Brand-new cachedir: pre-accept the T&C, then the same as prepare()."""
        os.makedirs(self.cache, exist_ok=True)
        with open(os.path.join(self.cache, "options.ini"), "w") as fh:
            fh.write("termsOfServiceVersion=1\n")
        self.prepare()

    def prepare(self):
        """Fresh or restored cachedir: mods, join manifest, saved server/account row
        (prefills the connect popup), debug options; reset the command channel."""
        mods_dir = os.path.join(self.cache, "mods")
        self.missing_mods = harness.install(mods_dir, self.mods, workshop=self.workshop)
        harness.enable_client_mods(mods_dir, self.mods)
        self.bus.reset()
        with open(os.path.join(self.bus.lua_dir, "pzt-join.txt"), "w") as fh:
            fh.write(f"username={self.username}\npassword={self.password}\n"
                     f"ip={self.ip}\nport={self.port}\nserverPassword={self.server_password}\n")
        self._upsert_serverlist()
        if self.debug:
            # GameWindow.initShared skips TISLogoState only for -debug clients with this set.
            with open(os.path.join(self.cache, "debug-options.ini"), "w") as fh:
                fh.write("UI.DisableLogoState=true\nUI.DisableWelcomeMessage=true\n")

    def _upsert_serverlist(self):
        os.makedirs(os.path.join(self.cache, "db"), exist_ok=True)
        con = sqlite3.connect(os.path.join(self.cache, "db", "ServerList.db"))
        con.executescript(SERVERLIST_SCHEMA)
        row = con.execute("SELECT id FROM server WHERE name='pzt'").fetchone()
        if row:
            sid = row[0]
            con.execute("UPDATE server SET ip=?, port=?, serverPassword=? WHERE id=?",
                        (self.ip, int(self.port), self.server_password, sid))
        else:
            sid = con.execute("INSERT INTO server (name, ip, port, serverPassword) VALUES (?,?,?,?)",
                              ("pzt", self.ip, int(self.port), self.server_password)).lastrowid
        acc = con.execute("SELECT id FROM account WHERE serverId=? AND username=?", (sid, self.username)).fetchone()
        if acc:
            con.execute("UPDATE account SET password=?, isSavePassword=1, authType=1 WHERE id=?", (self.password, acc[0]))
        else:
            con.execute("INSERT INTO account (serverId, username, password, isSavePassword, authType) VALUES (?,?,?,1,1)",
                        (sid, self.username, self.password))
        con.commit()
        con.close()

    # ---- process -----------------------------------------------------------
    def start(self):
        args = ["-nosteam", f"-cachedir={self.cache}", "-nosound", "-novoip", "-debuglog=Network",
                "+connect", self.server]
        if self.safemode:
            # ~100 s slower world load (spike S2); only for hosts without a usable GPU.
            args.insert(2, "-safemode")
        if self.debug:
            # Servers refuse -debug for non-admin accounts.
            args.insert(2, "-debug")
        if self.server_password:
            args += ["+password", self.server_password]
        if self.launcher == "exe":
            cmd = [EXE] + args
        else:
            # Start the JVM directly (ProjectZomboid64.exe triggers a UAC prompt).
            cmd = [JAVA, *JVM, "zombie.gameStates.MainScreenState"] + args
        self.cmd = cmd
        # A reused cachedir still holds last run's console.txt: start at its end.
        self._pos0 = os.path.getsize(self.console) if os.path.exists(self.console) else 0
        self.t0 = time.time()
        self.proc = subprocess.Popen(cmd, cwd=PZ_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        threading.Thread(target=self._tail, daemon=True).start()

    def _tail(self):
        pos = self._pos0
        while True:
            exited = self.proc.poll() is not None
            if os.path.exists(self.console):
                size = os.path.getsize(self.console)
                if size < pos:
                    pos = 0  # the game truncates console.txt on boot
                if size > pos:
                    with open(self.console, encoding="utf-8", errors="replace") as fh:
                        fh.seek(pos)
                        chunk = fh.read()
                        pos = fh.tell()
                    for line in chunk.splitlines():
                        self._parse(line)
            if exited or self._stop.is_set():
                break
            time.sleep(0.5)

    def _parse(self, line):
        t = round(time.time() - self.t0, 1)
        m = HARNESS_RX.search(line)
        if m:
            self._event("harness", t, msg=m.group(1)[:200])
        m = MOD_MISSING_RX.search(line)
        if m and m.group(1) not in self.mods_not_found:
            self.mods_not_found.append(m.group(1))
            self._event("mod_not_found", t, msg=m.group(1))
        for name, rx in MARKERS:
            if name not in self.seen and rx.search(line):
                self.seen[name] = t
                self._event(name, t, line=line.strip()[:200])

    def _event(self, kind, t, **kw):
        self.events.append({"t": t, "kind": kind, **kw})
        if self.echo:
            self.echo(f"  [{self.username} {t:6.1f}s] {kind}: {kw.get('msg') or kw.get('line') or ''}")

    def wait_for(self, name, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if name in self.seen:
                return self.seen[name]
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.username}: client exited rc={self.proc.returncode} "
                                   f"before '{name}' (seen: {list(self.seen)})")
            time.sleep(0.5)
        raise TimeoutError(f"{self.username}: no '{name}' within {timeout}s (seen: {list(self.seen)})")

    def click_to_start(self):
        """After the world is loaded, GameLoadingState waits for a mouse click ('Click to
        Start'); post one to this client's own window (matched by pid)."""
        hwnds = win32.find_windows(pid=self.proc.pid)
        for hwnd in hwnds:
            win32.post_click(hwnd)
        return len(hwnds)

    def wait_ready(self, timeout=300):
        """In-world with a player object (harness 'player <user> at x,y,z' line),
        clicking through 'Click to Start' once loading has finished."""
        end = time.time() + timeout
        last_click, clicks = 0.0, 0
        while time.time() < end:
            if "ready" in self.seen:
                return self.seen["ready"]
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.username}: client exited rc={self.proc.returncode} "
                                   f"before ready (seen: {list(self.seen)})")
            if "in_game" in self.seen and time.time() - last_click > 2.0:
                last_click = time.time()
                n = self.click_to_start()
                clicks += 1
                if clicks == 1:
                    self._event("click_to_start", round(time.time() - self.t0, 1), msg=f"{n} window(s)")
            time.sleep(0.5)
        raise TimeoutError(f"{self.username}: not ready within {timeout}s "
                           f"(seen: {list(self.seen)}, clicks: {clicks})")

    # ---- command channel ---------------------------------------------------
    def send(self, cmd, args="", wait=True, timeout=30):
        return self.bus.send(cmd, args, wait=wait, timeout=timeout)

    def results(self):
        return self.bus.results()

    def quit(self, timeout=60):
        """Graceful: harness calls getCore():quitToDesktop() (proper disconnect, server
        saves the player); kill on timeout."""
        if not self.alive:
            return self.proc.returncode if self.proc else None
        self.bus.send("quit", wait=False)
        try:
            rc = self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            self.kill()
            rc = None
        self._stop.set()
        return rc

    def kill(self):
        if self.alive:
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
        self._stop.set()
