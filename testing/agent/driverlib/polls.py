"""PollThread: a driver's slow reads (the server bus) run on one worker thread, so the planner loop never waits on one.

    p = PollThread(clock)
    p.schedule("stats", 60, read_stats)      # read_stats() runs on the worker at most every 60 s of `clock`
    p.start()
    ...
    result, wall = p.latest("stats")         # the newest result and the `clock` time it finished, or (None, None)
    p.stop()

One worker runs every scheduled read in turn: a read is due at its first chance and then `every_s` after its last
start. A read that raises lands in `errors` as {name, wall, error} and its schedule is kept. `latest` returns the same
tuple object until a newer read finishes, so a caller detects a new result by identity. Nothing on the worker touches
the caller's state beyond what each read itself does: the caller merges `latest` on its own thread.
"""
import threading
import time


class PollThread:
    def __init__(self, clock=time.time, idle_s=0.01):
        self.clock = clock
        self.idle_s = idle_s
        self.errors = []
        self._jobs = []
        self._latest = {}
        self._running = set()
        self._lock = threading.Lock()
        self._halt = threading.Event()
        self._thread = None

    def schedule(self, name, every_s, fn):
        """`fn()` runs on the worker at most every `every_s` of the clock, the first at the worker's first chance."""
        with self._lock:
            self._jobs.append({"name": name, "every_s": float(every_s), "fn": fn, "next": None})

    def start(self):
        """Start the worker (again after a stop: a stopped PollThread may be restarted once its worker has ended)."""
        if self._thread is None or not self._thread.is_alive():
            self._halt.clear()
            self._thread = threading.Thread(target=self._run, name="PollThread", daemon=True)
            self._thread.start()

    def stop(self, timeout_s=5.0):
        """Ask the worker to stop and join it; True when it ended within timeout_s. A read in flight is never
        interrupted: a caller that must not overlap it passes a timeout covering the longest read, and reads
        `alive()` when the join timed out."""
        self._halt.set()
        if self._thread is None:
            return True
        self._thread.join(timeout_s)
        return not self._thread.is_alive()

    def alive(self):
        """True while the worker thread runs (a read may be in flight)."""
        return self._thread is not None and self._thread.is_alive()

    def latest(self, name):
        """(result, wall) of the newest finished read of `name`, else (None, None)."""
        with self._lock:
            return self._latest.get(name, (None, None))

    def pending(self, name):
        """True while a read of `name` is running."""
        with self._lock:
            return name in self._running

    def run_due(self, only=None):
        """Run every due read (or only `only`'s) in schedule order on the calling thread; the number run. The worker
        calls it in a loop; a caller with no worker may call it itself."""
        n = 0
        with self._lock:
            jobs = [j for j in self._jobs if only is None or j["name"] == only]
        for j in jobs:
            if self._halt.is_set():
                break
            now = self.clock()
            if j["next"] is not None and now < j["next"]:
                continue
            j["next"] = now + j["every_s"]
            name = j["name"]
            with self._lock:
                self._running.add(name)
            try:
                result = j["fn"]()
                with self._lock:
                    self._latest[name] = (result, self.clock())
            except Exception as e:                       # noqa: BLE001 - a read's fault is recorded, the schedule kept
                with self._lock:
                    self.errors.append({"name": name, "wall": self.clock(), "error": "%s: %s" % (type(e).__name__, e)})
            finally:
                with self._lock:
                    self._running.discard(name)
            n += 1
        return n

    def _run(self):
        while not self._halt.is_set():
            if self.run_due() == 0:
                self._halt.wait(self.idle_s)
