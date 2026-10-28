"""ShotTaker: timestamped screenshots of the game client's window during a live session (ruling P23-AL).

Why: a session's record (the frames in state.log, the decision log) gives positions but not the scene, and the first
trace of each of the chain's two deaths read the scene wrong. A shot is the scene at a moment the logs name.

    t = ShotTaker(run_dir, pid=client_pid, clock=clock)
    t.start()                                 # the daemon worker (the loop's start)
    t.mark(moment)                            # the loop, each planner tick: a cheap dict (Session.shot_moment)
    t.mark(moment, final="death")             # the death frame; final="stop" at the loop's closing Stop
    joined = t.end(timeout_s)                 # the loop's end: the pending final shots taken, the worker joined
    t.summary()                               # loop.shots {n, failures, last_error, dir, every_s, cap_hit}

THE MOMENT (Session.shot_moment): {seq, wallMs, gameMin, health} off the latest frame, {branch, flee (the threat
why's flee value), goal (the decision line's goal type)} off the latest decision line, fight (the Fights row open,
by index, else None) and decision_line (the decision log's line count read so far).
THE TRIGGERS, decided in `mark` on the loop's thread (comparisons only) and taken on the worker:
  cadence  SHOT_EVERY_S after the last shot (or try) of any trigger; the first mark shoots at once;
  threat   the fight index changes to a new fight, or the flee value changes (a hold beginning or breaking counts:
           `held_inside` -> None is a change), against the previous mark;
  goal     the goal name changes against the previous mark (an ended goal, to None, counts);
  health   health HEALTH_DROP or more below the last shot's;
  death, stop  `final`: taken with their own moment, the gap and the cap waived.
An event trigger waits out SHOT_MIN_GAP_S after the last shot, then fires with the latest moment (one event slot: the
first event wins until it fires; a final mark clears it, its own shot being that moment's). Past SHOT_MAX shots
only the finals fire (cap_hit). The first mark sets the comparison state and fires no event (the cadence shoots it).
THE SHOT (`take`, on the worker): the window finder `find(pid)` -> the client's top-level window rect (pixels:
the process is made DPI-aware first) or None; `grab(bbox)` (PIL.ImageGrab.grab) over it, or over the primary screen
(bbox None, window.found false) when none is found; downscaled to SHOT_WIDTH wide (aspect kept, never upscaled), JPEG
quality SHOT_QUALITY, written to <run dir>/shots/shot-<n:04d>-<seq>.jpg, and one line appended to shots/shots.jsonl:
{n, file, bytes, sha256, wallMs, pyMs (the taker's clock at the grab, ms), seq, gameMin, health, branch, flee, fight,
goal, decision_line, trigger, window {found, rect}, grab_ms (the grab, the scale and the write, ms)}. A write-up
matches `seq` against state.log and `decision_line` against decision.log. A finder or grab that raises is counted
(`failures`, the last message kept), the try still resets the cadence, and nothing reaches the loop; a fault in
the worker's pass itself (`due`) is counted too ("worker: ...") and the worker goes on, so the finals still land.
ImageGrab reads the screen's pixels: a window behind another shows the one in front, so the client is left uncovered.
"""
import ctypes
import hashlib
import io
import json
import os
import threading
import time

SHOT_EVERY_S = 10.0          # the cadence
SHOT_MIN_GAP_S = 1.0         # an event trigger's least gap after the last shot
SHOT_MAX = 800               # per session; past it only death and stop
SHOT_WIDTH = 1280
SHOT_QUALITY = 80
HEALTH_DROP = 5.0            # health fallen this much since the last shot
SHOT_JOIN_S = 5.0            # the worker's join at the loop's end: a grab and a write take well under a second
SHOTS_DIR = "shots"
INDEX = "shots.jsonl"
TRIGGERS = ("cadence", "threat", "goal", "health", "death", "stop")
FINAL = ("death", "stop")
MOMENT_KEYS = ("seq", "wallMs", "gameMin", "health", "branch", "flee", "fight", "goal", "decision_line")
CLIENT_TITLE = "Project Zomboid"     # pzt.win32.find_windows' title: preferred among the process's windows


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ================================================================ the window and the grab (Windows)
_dpi = {"set": False}


def dpi_aware():
    """Make this process DPI-aware once (per-monitor, else system), so GetWindowRect and the grab share pixels."""
    if _dpi["set"] or os.name != "nt":
        return
    _dpi["set"] = True
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:                                    # noqa: BLE001 - older Windows, or already set
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:                                # noqa: BLE001
            pass


def find_window(pid):
    """The rect (left, top, right, bottom) in pixels of `pid`'s visible top-level window (CLIENT_TITLE's first, else
    the largest), or None: no pid, not Windows, no such window, or it is minimised."""
    if pid is None or os.name != "nt":
        return None
    import ctypes.wintypes as w
    dpi_aware()
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        owner = w.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != pid:
            return True
        r = w.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        if r.right - r.left <= 0 or r.bottom - r.top <= 0 or r.left <= -32000:      # empty, or minimised
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        found.append((buf.value == CLIENT_TITLE, (r.right - r.left) * (r.bottom - r.top),
                      (r.left, r.top, r.right, r.bottom)))
        return True
    user32.EnumWindows(cb, 0)
    if not found:
        return None
    return max(found, key=lambda f: (f[0], f[1]))[2]


def grab_screen(bbox):
    """PIL.ImageGrab.grab over bbox (in virtual-desktop pixels, so a window on any monitor; a maximised window's
    border overhang is padded black), or the primary screen when bbox is None."""
    from PIL import ImageGrab
    dpi_aware()
    if bbox is None:
        return ImageGrab.grab()
    return ImageGrab.grab(bbox=bbox, all_screens=True)


# ================================================================ the taker
class ShotTaker:
    """The module docstring. `grab(bbox)` and `find(pid)` are injectable (the tests' fakes); `clock` is the
    session's."""

    def __init__(self, run_dir, pid=None, grab=grab_screen, find=find_window, clock=time.time, every_s=SHOT_EVERY_S,
                 min_gap_s=SHOT_MIN_GAP_S, cap=SHOT_MAX, width=SHOT_WIDTH, quality=SHOT_QUALITY, idle_s=0.05):
        self.run_dir, self.pid = run_dir, pid
        self.grab, self.find, self.clock = grab, find, clock
        self.every_s, self.min_gap_s, self.cap = float(every_s), float(min_gap_s), cap
        self.width, self.quality, self.idle_s = width, quality, idle_s
        self.dir = os.path.join(run_dir, SHOTS_DIR)
        self.n = 0
        self.failures = 0
        self.last_error = None
        self.cap_hit = False
        self._lock = threading.Lock()
        self._latest = None           # the latest marked moment
        self._prev = None             # the previous mark's moment (the threat and goal comparisons)
        self._event = None            # the pending event trigger
        self._final = []              # pending (trigger, moment) finals, in order
        self._last_t = None           # the clock at the last shot or try
        self._last_health = None      # the health at the last shot
        self._closing = False
        self._halt = threading.Event()
        self._thread = None

    # -- the loop's side -----------------------------------------------------------------------------------------
    def mark(self, moment, final=None):
        """The loop's cheap call: the latest moment kept and the event triggers decided (comparisons only); `final`
        ("death" | "stop") queues a final shot of this moment. Never raises."""
        try:
            m = {k: moment.get(k) for k in MOMENT_KEYS} if isinstance(moment, dict) else dict.fromkeys(MOMENT_KEYS)
            with self._lock:
                prev, self._prev, self._latest = self._prev, m, m
                if final in FINAL:
                    self._final.append((final, m))
                    self._event = None                   # the final shot is this moment's
                    return
                if prev is None or self._event is not None:
                    return
                if m["fight"] is not None and m["fight"] != prev["fight"] or m["flee"] != prev["flee"]:
                    self._event = "threat"
                elif m["goal"] != prev["goal"]:
                    self._event = "goal"
                elif (_num(m["health"]) is not None and _num(self._last_health) is not None
                      and self._last_health - m["health"] >= HEALTH_DROP):
                    self._event = "health"
        except Exception as e:                           # noqa: BLE001 - a mark never reaches the loop
            self.failures += 1
            self.last_error = "mark: %s: %s" % (type(e).__name__, e)

    # -- the worker's side ---------------------------------------------------------------------------------------
    def due(self):
        """(trigger, moment) of the shot due now, else None; consumes it."""
        with self._lock:
            now = self.clock()
            if self._final:
                return self._final.pop(0)
            if self._closing or self._latest is None:
                return None
            last = self._last_t
            if self.n >= self.cap:
                if self._event is not None or last is None or now - last >= self.every_s:
                    self.cap_hit = True
                    self._event = None
                    self._last_t = now
                return None
            if self._event is not None and (last is None or now - last >= self.min_gap_s):
                trig, self._event = self._event, None
                return trig, self._latest
            if last is None or now - last >= self.every_s:
                return "cadence", self._latest
            return None

    def run_due(self):
        """One worker pass: the due shot taken; 1 when a shot was written, else 0."""
        d = self.due()
        if d is None:
            return 0
        return 1 if self.take(*d) else 0

    def take(self, trigger, m):
        """One shot of moment `m` (the module docstring); True when written. A fault is counted, never raised."""
        t0 = time.perf_counter()
        now = self.clock()
        with self._lock:
            self._last_t = now
        try:
            rect = self.find(self.pid)
            bbox = tuple(int(v) for v in rect) if rect is not None else None
            img = self.grab(bbox)
            if img.mode != "RGB":
                img = img.convert("RGB")
            if img.width > self.width:
                img = img.resize((self.width, max(1, round(img.height * self.width / img.width))))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=self.quality)
            data = buf.getvalue()
            n = self.n + 1
            seq = m.get("seq")
            name = "shot-%04d-%s.jpg" % (n, seq if seq is not None else "none")
            os.makedirs(self.dir, exist_ok=True)
            with open(os.path.join(self.dir, name), "wb") as fh:
                fh.write(data)
            row = {"n": n, "file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                   "wallMs": m.get("wallMs"), "pyMs": now * 1000.0, "seq": seq, "gameMin": m.get("gameMin"),
                   "health": m.get("health"), "branch": m.get("branch"), "flee": m.get("flee"),
                   "fight": m.get("fight"), "goal": m.get("goal"), "decision_line": m.get("decision_line"),
                   "trigger": trigger, "window": {"found": bbox is not None, "rect": list(bbox) if bbox else None},
                   "grab_ms": (time.perf_counter() - t0) * 1000.0}
            with open(os.path.join(self.dir, INDEX), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
            with self._lock:
                self.n = n
                if _num(m.get("health")) is not None:
                    self._last_health = m["health"]
            return True
        except Exception as e:                           # noqa: BLE001 - a grab's fault is counted, never raised
            with self._lock:
                self.failures += 1
                self.last_error = "%s: %s" % (type(e).__name__, e)
            return False

    def _run(self):
        while not self._halt.is_set():
            try:
                took = self.run_due()
            except Exception as e:                       # noqa: BLE001 - the worker outlives a fault
                took = 0
                with self._lock:
                    self.failures += 1
                    self.last_error = "worker: %s: %s" % (type(e).__name__, e)
            with self._lock:
                done = self._closing and not self._final
            if done:
                break
            if took == 0:
                self._halt.wait(self.idle_s)

    # -- the thread ----------------------------------------------------------------------------------------------
    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._halt.clear()
            self._thread = threading.Thread(target=self._run, name="ShotTaker", daemon=True)
            self._thread.start()

    def end(self, timeout_s=SHOT_JOIN_S):
        """The loop's end: no more cadence or event shots, the pending finals taken, the worker joined within
        timeout_s; True when it ended (an unstarted taker is joined). A grab in flight is never interrupted."""
        with self._lock:
            self._closing = True
        if self._thread is None:
            return True
        self._thread.join(timeout_s)
        if self._thread.is_alive():
            return False
        return True

    def summary(self):
        """loop.shots."""
        with self._lock:
            return {"n": self.n, "failures": self.failures, "last_error": self.last_error, "dir": SHOTS_DIR,
                    "every_s": self.every_s, "cap_hit": self.cap_hit}
