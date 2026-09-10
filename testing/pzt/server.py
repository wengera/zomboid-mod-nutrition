"""Dedicated server process under orchestrator control."""
import collections
import os
import re
import subprocess
import threading
import time

from . import harness
from .bus import CommandBus
from .paths import ADMIN_PW, JAVA, PZ_DIR, RCON_PW
from .rcon import rcon

STARTED_RX = re.compile(r"\*\*\* SERVER STARTED")
ERROR_RX = re.compile(r"ERROR|Exception|STACK TRACE|LuaError|lua error")
BUILD_RX = re.compile(r"\bversion=(\d+\.\d+\.\d+)")
# A mod listed in Mods= that the game cannot find is only a WARN: the server boots and
# clients join without it (spike S3). Treated as a hard failure by the orchestrator.
MOD_MISSING_RX = re.compile(r'required mod "([^"]+)" not found')

# Known vanilla 42.20.4 noise (baseline from spikes S1/T0); matched head lines are not
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
FRESH_INI = {"Public": "false", "Open": "true", "SteamVAC": "false",
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


def lua_value(v):
    """A profile's TOML value as a Lua literal. Only booleans need translating (Python's
    True/False are not Lua's); numbers and strings already round-trip through str()."""
    return "true" if v is True else "false" if v is False else str(v)


def write_sandbox_vars(path, overrides):
    """Partial table: unlisted keys take server defaults; the server rewrites the full
    file on boot (verified in T0). For a cache that already HAS a SandboxVars file (a
    restored fixture) this would drop every option the fixture was built with -- use
    merge_sandbox_vars there."""
    body = "".join(f"    {k} = {lua_value(v)},\n" for k, v in overrides.items())
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("SandboxVars = {\n    VERSION = 6,\n" + body + "}\n")


# Top-level options sit at exactly four spaces; the five nested tables (Basement, Map,
# ZombieLore, ZombieConfig, MultiplierConfig) open with `= {` at that same indent and hold
# their options at eight, so the lookahead both protects a table opener and keeps `Map` out
# of sandbox_keys() -- a profile naming it fails validation instead of no-op'ing.
SANDBOX_KEY_RX = re.compile(r"^ {4}(\w+) = (?!\{)")


def sandbox_keys(path):          # the settable options of an existing file, for validation
    with open(path, encoding="utf-8", errors="replace") as fh:
        return [m.group(1) for m in map(SANDBOX_KEY_RX.match, fh) if m]


def merge_sandbox_vars(path, overrides):
    """Rewrite only the named top-level keys, keeping every other option (and the server's
    comments) as the fixture had them. -> (applied, appended); CRLF preserved."""
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        text = fh.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    pending = {k: lua_value(v) for k, v in overrides.items()}
    out = []
    for line in text.splitlines():
        m = SANDBOX_KEY_RX.match(line)
        hit = m and m.group(1) in pending
        out.append(f"    {m.group(1)} = {pending.pop(m.group(1))}," if hit else line)
    applied, appended = [k for k in overrides if k not in pending], sorted(pending)
    if appended:                       # before the file's own closing brace (col 0)
        close = max(i for i, l in enumerate(out) if l.strip() == "}")
        out[close:close] = [f"    {k} = {pending[k]}," for k in appended]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nl.join(out) + nl)
    return applied, appended


class Server:
    def __init__(self, cache, name="pzt", port=27261, rcon_port=27015, mods=("PZTestKit",),
                 admin_pw=ADMIN_PW, rcon_pw=RCON_PW, log_path=None, echo=None,
                 workshop=True, workshop_items=(), mod_sources=None, mod_skip=()):
        self.cache = os.path.abspath(cache)
        self.name = name
        self.port = int(port)
        self.rcon_port = int(rcon_port)
        self.mods = list(mods)
        self.workshop = workshop                  # copy non-harness mods in from the workshop folder
        self.workshop_items = list(workshop_items)
        self.mod_sources = dict(mod_sources or {})   # mod id -> folder to copy (a profile's)
        self.mod_skip = tuple(mod_skip)              # named in Mods=, deliberately not placed
        self.missing_mods = []        # not placed in mods/ by us
        self.mods_not_found = []      # reported missing by the game at load
        self.admin_pw = admin_pw
        self.rcon_pw = rcon_pw
        self.log_path = log_path or os.path.join(os.path.dirname(self.cache), "server-stdout.log")
        self.echo = echo
        self.bus = CommandBus(os.path.join(self.cache, "Lua"), alive=lambda: self.alive)
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
        refresh the mods, rewrite ports so a fixture can boot on any port."""
        os.makedirs(os.path.join(self.cache, "Server"), exist_ok=True)
        self.missing_mods = harness.install(os.path.join(self.cache, "mods"), self.mods,
                                            workshop=self.workshop, sources=self.mod_sources,
                                            skip=self.mod_skip)
        self.bus.reset()
        values = {} if os.path.exists(self.ini) else dict(FRESH_INI)
        values.update({"DefaultPort": self.port, "UDPPort": self.port + 1, "RCONPort": self.rcon_port,
                       "RCONPassword": self.rcon_pw, "Mods": ";".join(self.mods),
                       "WorkshopItems": ";".join(self.workshop_items)})
        update_ini(self.ini, values)
        if sandbox:
            # A restored fixture already has the server's own 1000-line file: rewrite the
            # named options in place, because replacing it would silently reset every option
            # the fixture was provisioned with (its Zombies = 6 among them).
            if os.path.exists(self.sandbox_path):
                applied, appended = merge_sandbox_vars(self.sandbox_path, sandbox)
                if self.echo:
                    self.echo(f"  [server] sandbox merged into the fixture's file: "
                              f"applied {applied or 'none'}, appended {appended or 'none'}")
            else:
                write_sandbox_vars(self.sandbox_path, sandbox)
                if self.echo:
                    self.echo(f"  [server] sandbox written fresh: {sorted(sandbox)}")

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
                m = MOD_MISSING_RX.search(line)
                if m:
                    self.mods_not_found.append(m.group(1))
                    if self.echo:
                        self.echo(f"  [server] mod not found at load: {m.group(1)}")
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

    def send(self, cmd, args="", wait=True, timeout=30):
        """Harness command on the server's Lua side (see bus.py)."""
        return self.bus.send(cmd, args, wait=wait, timeout=timeout)

    def results(self):
        return self.bus.results()

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
