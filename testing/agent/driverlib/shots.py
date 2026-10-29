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
THE SHOT (`take`, on the worker): the window finder `find(pid)` -> {rect, source} of the client's top-level window
(pixels: the process is made DPI-aware first; `window_rect`: the DWM extended frame bounds, source "dwm", else
GetWindowRect, "gwr", whose rect on Windows 10/11 carries invisible resize borders and a shadow, so the first live
shots took a strip of the host desktop; clipped to the virtual screen) or None; `grab(bbox)` (PIL.ImageGrab.grab)
over it (the primary screen only with guard=None, bbox None, window.found false); downscaled to SHOT_WIDTH
wide (aspect kept, never upscaled), JPEG quality SHOT_QUALITY, written to <run dir>/shots/shot-<n:04d>-<seq>.jpg,
and one line appended to shots/shots.jsonl: {n, file, bytes, sha256, wallMs, pyMs (the taker's clock at the grab,
ms), seq, gameMin, health, branch, flee, fight, goal, decision_line, trigger, window {found, rect, rect_source},
grab_ms (the grab, the scale and the write, ms)}. A write-up matches `seq` against state.log and `decision_line`
against decision.log. A finder or grab that raises is counted (`failures`, the last message kept), the try still
resets the cadence, and nothing reaches the loop; a fault in the worker's pass itself (`due`) is counted too
("worker: ...") and the worker goes on, so the finals still land.
ImageGrab reads the screen's pixels: a window behind another shows the one in front, so the client is left uncovered.
THE GUARD (ruling P24-S; `guard(hwnd, rect, pid)` -> None to grab, else (reason, class_name)): immediately before the
grab the foreground window must be the client's (`find` gives `hwnd`), else the index line is written with
`skipped: "not foreground"`; and no window of another process may lie over the rect by more than OCCLUDED_FRAC of its
area (the Z-order walked above the client), else `skipped: "occluded"`. The skipped line carries the usual fields minus
file, bytes and sha256, plus `skipped` and `other_class` (the other window's class name only, never its title, which
may carry personal text); it takes the next n, and the record's `skipped` counts them (n counts the written shots).
A found window without `hwnd`, or none found, is `skipped: "no window"` (class "") and no grab: the guard fails closed;
only `guard=None` (the tests) grabs unguarded, the primary screen when no window is found. The first skip of each
reason in a session is printed once to stdout. A guard that raises is a failure and no grab. `cited_ok(index_path, numbers)` refuses a cited shot that was skipped or
whose window was not found: the controller's copy script runs it before copying any image.
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
DWMWA_EXTENDED_FRAME_BOUNDS = 9    # dwmapi: the visible frame, without GetWindowRect's invisible borders and shadow
CLIENT_TITLE = "Project Zomboid"     # pzt.win32.find_windows' title: preferred among the process's windows
OCCLUDED_FRAC = 0.1          # another process's window over more than this fraction of the rect: no grab (P24-S)
GW_HWNDPREV = 3              # GetWindow: the window above in the Z-order


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


def _rect_ok(r):
    """True for a (left, top, right, bottom) of numbers with an area, not a minimised window's (-32000)."""
    return (isinstance(r, (tuple, list)) and len(r) == 4 and all(_num(v) is not None for v in r)
            and r[2] > r[0] and r[3] > r[1] and r[0] > -32000)


def clip(rect, screen):
    """rect clipped to screen (both left, top, right, bottom); None when nothing is left."""
    l, t, r, b = max(rect[0], screen[0]), max(rect[1], screen[1]), min(rect[2], screen[2]), min(rect[3], screen[3])
    return (l, t, r, b) if r > l and b > t else None


def dwm_rect(hwnd):
    """DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS): the visible frame in pixels, or None when it fails."""
    import ctypes.wintypes as w
    r = w.RECT()
    hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(w.HWND(hwnd), ctypes.c_uint(DWMWA_EXTENDED_FRAME_BOUNDS),
                                                    ctypes.byref(r), ctypes.sizeof(r))
    return (r.left, r.top, r.right, r.bottom) if hr == 0 else None


def gwr_rect(hwnd):
    """GetWindowRect: the frame plus the invisible resize borders and shadow (Windows 10/11), or None."""
    import ctypes.wintypes as w
    r = w.RECT()
    if not ctypes.windll.user32.GetWindowRect(w.HWND(hwnd), ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right, r.bottom)


def virtual_screen():
    """The virtual desktop (every monitor) as (left, top, right, bottom) in pixels, or None."""
    m = ctypes.windll.user32.GetSystemMetrics
    x, y, cx, cy = m(76), m(77), m(78), m(79)     # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, ...
    return (x, y, x + cx, y + cy) if cx > 0 and cy > 0 else None


def window_rect(hwnd, dwm=dwm_rect, gwr=gwr_rect, screen=virtual_screen):
    """(rect, source) of a window: the DWM extended frame bounds ("dwm"), else GetWindowRect ("gwr") when the DWM
    call fails or gives no area; clipped to the virtual screen when it reads; None for no area or a minimised
    window."""
    rect, src = None, "dwm"
    try:
        rect = dwm(hwnd)
    except Exception:                                    # noqa: BLE001 - no dwmapi: GetWindowRect
        rect = None
    if not _rect_ok(rect):
        rect, src = gwr(hwnd), "gwr"
    if not _rect_ok(rect):
        return None
    rect = tuple(int(v) for v in rect)
    try:
        scr = screen()
    except Exception:                                    # noqa: BLE001
        scr = None
    if scr is not None:
        rect = clip(rect, scr)
        if rect is None:
            return None
    return rect, src


def find_window(pid):
    """{rect, source} of `pid`'s visible top-level window (CLIENT_TITLE's first, else the largest; window_rect), or
    None: no pid, not Windows, no such window, or it is minimised."""
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
        got = window_rect(hwnd)
        if got is None:
            return True
        (l, t, r, b), src = got
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        found.append((buf.value == CLIENT_TITLE, (r - l) * (b - t),
                      {"rect": (l, t, r, b), "source": src, "hwnd": hwnd}))
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


class _User32:
    """The user32 calls the guard needs, as plain methods (the tests' fake replaces the whole object)."""

    def __init__(self):
        import ctypes.wintypes as w
        self.w, self.u = w, ctypes.windll.user32
        self.u.GetForegroundWindow.restype = w.HWND
        self.u.GetWindow.restype = w.HWND
        self.u.GetWindow.argtypes = [w.HWND, ctypes.c_uint]
        self.u.IsWindowVisible.argtypes = [w.HWND]

    def foreground(self):
        return self.u.GetForegroundWindow()

    def above(self, hwnd):
        return self.u.GetWindow(self.w.HWND(hwnd), GW_HWNDPREV)

    def visible(self, hwnd):
        return bool(self.u.IsWindowVisible(self.w.HWND(hwnd)))

    def rect(self, hwnd):
        return gwr_rect(hwnd)

    def owner_pid(self, hwnd):
        o = self.w.DWORD()
        self.u.GetWindowThreadProcessId(self.w.HWND(hwnd), ctypes.byref(o))
        return o.value

    def class_name(self, hwnd):
        buf = ctypes.create_unicode_buffer(256)
        self.u.GetClassNameW(self.w.HWND(hwnd), buf, 256)
        return buf.value


def screen_guard(hwnd, rect, pid, user32=None):
    """None when the client window `hwnd` (rect, owned by `pid`) is the foreground window and the other-process
    windows above it overlap rect by no more than OCCLUDED_FRAC of its area in all (the overlaps are summed, so
    several small windows count together and overlapping ones count twice: the safe direction); else (reason, the
    class name of the window that tipped the sum). `pid` None is unknown: the foreground check alone is made, since
    the client's own windows could not be told from another's. `rect` is the client's DWM frame and the others'
    GetWindowRect (invisible borders, cloaked windows read as visible): both over-count, so a skip errs safe."""
    u = user32 if user32 is not None else _User32()
    fg = u.foreground()
    if fg != hwnd:
        return "not foreground", (u.class_name(fg) if fg else "")
    area = max(1, (rect[2] - rect[0]) * (rect[3] - rect[1]))
    h, steps, covered = (u.above(hwnd) if pid is not None else 0), 0, 0
    while h and steps < 4096:
        steps += 1
        if u.visible(h):
            r = u.rect(h)
            if r is not None and u.owner_pid(h) != pid:
                w_ = min(r[2], rect[2]) - max(r[0], rect[0])
                h_ = min(r[3], rect[3]) - max(r[1], rect[1])
                if w_ > 0 and h_ > 0:
                    covered += w_ * h_
                    if covered > OCCLUDED_FRAC * area:
                        return "occluded", u.class_name(h)
        h = u.above(h)
    return None


def cited_ok(index_path, numbers):
    """The numbers a write-up may cite: raises ValueError naming each number with no index line, a skipped line, or a
    window that was not found (the grab then took the whole primary screen); else the sorted numbers."""
    rows = {}
    with open(index_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                rows[r.get("n")] = r
    bad = []
    for n in numbers:
        r = rows.get(n)
        if r is None:
            bad.append("%s: no index line" % n)
        elif r.get("skipped"):
            bad.append("%s: skipped (%s)" % (n, r["skipped"]))
        elif not (r.get("window") or {}).get("found"):
            bad.append("%s: window not found" % n)
    if bad:
        raise ValueError("shots not citable: " + "; ".join(bad))
    return sorted(numbers)


# ================================================================ the taker
class ShotTaker:
    """The module docstring. `grab(bbox)` and `find(pid)` are injectable (the tests' fakes); `clock` is the
    session's."""

    def __init__(self, run_dir, pid=None, grab=grab_screen, find=find_window, clock=time.time, every_s=SHOT_EVERY_S,
                 guard=screen_guard,
                 min_gap_s=SHOT_MIN_GAP_S, cap=SHOT_MAX, width=SHOT_WIDTH, quality=SHOT_QUALITY, idle_s=0.05):
        self.run_dir, self.pid = run_dir, pid
        self.grab, self.find, self.clock, self.guard = grab, find, clock, guard
        self.every_s, self.min_gap_s, self.cap = float(every_s), float(min_gap_s), cap
        self.width, self.quality, self.idle_s = width, quality, idle_s
        self.dir = os.path.join(run_dir, SHOTS_DIR)
        self.n = 0                    # index lines written (shots and skipped)
        self.skipped = 0
        self._said = set()            # the skip reasons already printed once
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
            if self.n - self.skipped >= self.cap:
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
            win = self.find(self.pid)
            rect, src = (win.get("rect"), win.get("source")) if isinstance(win, dict) else (win, None)
            bbox = tuple(int(v) for v in rect) if rect is not None else None
            hwnd = win.get("hwnd") if isinstance(win, dict) else None
            if self.guard is not None:                   # fail closed: no found client window, no grab
                verdict = ("no window", "") if bbox is None or hwnd is None else self.guard(hwnd, bbox, self.pid)
                if verdict is not None:
                    return self._skip(trigger, m, now, verdict, bbox, src)
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
            row = {"n": n, "file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            row.update(self._fields(m, now, trigger, bbox, src))
            row["grab_ms"] = (time.perf_counter() - t0) * 1000.0
            self._append(row)
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

    @staticmethod
    def _fields(m, now, trigger, bbox, src):
        return {"wallMs": m.get("wallMs"), "pyMs": now * 1000.0, "seq": m.get("seq"), "gameMin": m.get("gameMin"),
                "health": m.get("health"), "branch": m.get("branch"), "flee": m.get("flee"),
                "fight": m.get("fight"), "goal": m.get("goal"), "decision_line": m.get("decision_line"),
                "trigger": trigger, "window": {"found": bbox is not None, "rect": list(bbox) if bbox else None,
                                               "rect_source": src if bbox else None}}

    def _append(self, row):
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, INDEX), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

    def _skip(self, trigger, m, now, verdict, bbox, src):
        """The index line of a shot the guard refused (no file); False, as `take` returns."""
        reason, other = verdict
        row = {"n": self.n + 1}
        row.update(self._fields(m, now, trigger, bbox, src))
        row["skipped"], row["other_class"] = reason, other
        self._append(row)
        with self._lock:
            self.n += 1
            self.skipped += 1
            first = reason not in self._said
            self._said.add(reason)
        if first:
            print("shots: skipped (%s), first of its kind this session" % reason, flush=True)
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
            return {"n": self.n - self.skipped, "skipped": self.skipped, "failures": self.failures,
                    "last_error": self.last_error, "dir": SHOTS_DIR,
                    "every_s": self.every_s, "cap_hit": self.cap_hit}
