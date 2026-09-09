"""Dedicated server process under orchestrator control."""
import collections
import os
import re
import subprocess
import threading
import time

from . import harness
from .paths import ADMIN_PW, JAVA, PZ_DIR, RCON_PW
from .rcon import rcon

STARTED_RX = re.compile(r"\*\*\* SERVER STARTED")
ERROR_RX = re.compile(r"ERROR|Exception|STACK TRACE|LuaError|lua error")
BUILD_RX = re.compile(r"\bversion=(\d+\.\d+\.\d+)")

# Known vanilla 42.20.4 boot noise (baseline from spike S1); matched lines are not
# counted as errors. Re-baseline after game updates.
BASELINE_NOISE = [re.compile(p) for p in (
    r"FluidContainerScript\.load .*Sanitizing container name",
    r"IsoPropertyType\.lookupOrDefaultStr> Exception thrown",
    r"BrokenFences\.addBrokenTiles .*Missing ThumpSound",
    r"IsoPropertyTypeNotFoundException: Property Name not found: (ladder[NSEW]|WindowShape)",
    r"CraftRecipeComponentScript: Recipe Piano missing UiConfigScript",
    r"handleMannequinZone .*Mannequin zone missing properties",
    r"Basements\.mergeRoomsOntoMetaCell .*duplicate RoomDef\.metaID",
    # the same vanilla duplicate-room defect, echoed when a SAVED world's map_meta.bin loads
    r"IsoMetaGrid\.load\s+> invalid room metaID .* while reading map_meta\.bin",
    # vanilla map data around the Muldraugh spawn, logged when a player loads those chunks
    r"ERROR: IsoThumpable not found on square",
    # every mod: the loader probes optional folders (AnimSets, actiongroups, ...) and
    # logs the misses as exceptions (head line + java stack frames)
    r"AdvancedAnimator\$1\.visitFileFailed> Exception thrown",
    r"NoSuchFileException: .*[\\/]mods[\\/].*[\\/]media[\\/](AnimSets|actiongroups|anims_X|AnimSets_X)",
)]
MAX_FRAMES = 6  # stack-frame lines kept per reported error

JVM = ["--enable-native-access=ALL-UNNAMED", "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED",
       "-XX:+UseZGC", "-XX:-CreateCoredumpOnCrash", "-XX:-OmitStackTraceInFastThrow", "-Xmx3072m",
       "-Djava.library.path=./natives/;./natives/win64/;./", "-cp", "./;projectzomboid.jar"]

# Written only when the ini does not exist yet; the server fills in every other option
# with defaults and rewrites the file on first boot, keeping these values (spike S1).
FRESH_INI = {"Public": "false", "Open": "true", "SteamVAC": "false", "WorkshopItems": "",
             "PauseEmpty": "false", "UPnP": "false"}


def update_ini(path, values):
    """Rewrite Key=Value lines in place, append the ones that are missing."""
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    pending = {k: str(v) for k, v in values.items()}
    out = []
    for line in lines:
        key = None
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
        if key in pending:
            out.append(f"{key}={pending.pop(key)}")
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in pending.items()]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def write_sandbox_vars(path, overrides):
    """Partial table: unlisted keys take server defaults; the server rewrites the full
    file on boot."""
    body = "".join(f"    {k} = {v},\n" for k, v in overrides.items())
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("SandboxVars = {\n    VERSION = 6,\n" + body + "}\n")


class Server:
    def __init__(self, cache, name="pzt", port=27261, rcon_port=27015, mods=("PZTestKitClient",),
                 admin_pw=ADMIN_PW, rcon_pw=RCON_PW, log_path=None, echo=None):
        self.cache = os.path.abspath(cache)
        self.name = name
        self.port = int(port)
        self.rcon_port = int(rcon_port)
        self.mods = list(mods)
        self.admin_pw = admin_pw
        self.rcon_pw = rcon_pw
        self.log_path = log_path or os.path.join(os.path.dirname(self.cache), "server-stdout.log")
        self.echo = echo
        self.proc = None
        self.errors = []
        self.build = None
        self.line_count = 0
        self.tail = collections.deque(maxlen=40)
        self.t_started = None
        self._started = threading.Event()

    @property
    def ini(self):
        return os.path.join(self.cache, "Server", f"{self.name}.ini")

    @property
    def sandbox_path(self):
        return os.path.join(self.cache, "Server", f"{self.name}_SandboxVars.lua")

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def seed(self, sandbox=None):
        """Fresh cache: write the ini (+ sandbox overrides). Restored cache: keep the world,
        refresh the harness mods, rewrite ports so a fixture can boot on any port."""
        os.makedirs(os.path.join(self.cache, "Server"), exist_ok=True)
        harness.install(os.path.join(self.cache, "mods"), self.mods)
        values = {} if os.path.exists(self.ini) else dict(FRESH_INI)
        values.update({"DefaultPort": self.port, "UDPPort": self.port + 1, "RCONPort": self.rcon_port,
                       "RCONPassword": self.rcon_pw, "Mods": ";".join(self.mods)})
        update_ini(self.ini, values)
        if sandbox:
            write_sandbox_vars(self.sandbox_path, sandbox)

    def start(self, timeout=420):
        cmd = [JAVA, *JVM, "zombie.network.GameServer", "-nosteam", "-servername", self.name,
               "-adminpassword", self.admin_pw, f"-cachedir={self.cache}",
               "-port", str(self.port), "-udpport", str(self.port + 1)]
        self.cmd = cmd
        self.t0 = time.time()
        self.proc = subprocess.Popen(cmd, cwd=PZ_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                     errors="replace", bufsize=1)
        threading.Thread(target=self._reader, daemon=True).start()
        while not self._started.wait(1.0):
            if self.proc.poll() is not None:
                raise RuntimeError(f"server exited rc={self.proc.returncode} before start; "
                                   f"tail: {list(self.tail)[-5:]}")
            if time.time() - self.t0 > timeout:
                self.kill()
                raise TimeoutError(f"no SERVER STARTED marker within {timeout}s; tail: {list(self.tail)[-5:]}")
        self.t_started = round(time.time() - self.t0, 1)
        return self.t_started

    def _reader(self):
        head_is_error, frames = False, 0
        with open(self.log_path, "w", encoding="utf-8") as fh:
            for line in self.proc.stdout:
                fh.write(line)
                fh.flush()
                self.line_count += 1
                self.tail.append(line.rstrip()[:200])
                if self.build is None:
                    m = BUILD_RX.search(line)
                    if m:
                        self.build = m.group(1)
                if not self._started.is_set() and STARTED_RX.search(line):
                    self._started.set()
                if line[:1] in (" ", "\t"):
                    # indented = stack frame of the preceding head line: attach, don't count
                    if head_is_error and frames < MAX_FRAMES:
                        self.errors[-1] += "\n" + line.rstrip()[:200]
                        frames += 1
                    continue
                head_is_error = bool(ERROR_RX.search(line)) and not any(p.search(line) for p in BASELINE_NOISE)
                frames = 0
                if head_is_error:
                    self.errors.append(line.rstrip()[:300])
                    if self.echo:
                        self.echo("  [server] error: " + line.rstrip()[:160])

    def rcon(self, cmd):
        return rcon("127.0.0.1", self.rcon_port, self.rcon_pw, cmd)

    def stop(self, timeout=120):
        """Graceful: 'quit' on stdin (falls back to RCON), wait; kill on timeout."""
        if not self.alive:
            return self.proc.returncode if self.proc else None
        try:
            self.proc.stdin.write("quit\n")
            self.proc.stdin.flush()
        except OSError:
            self.rcon("quit")
        try:
            return self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            self.kill()
            return None

    def kill(self):
        if self.alive:
            subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
