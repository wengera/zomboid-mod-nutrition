"""ServerReads: a Session's server reads (stats.all, players, damage.watch since) behind one interface the loop calls.

    reads = ServerReads(session, polls)       # polls: a polls.PollThread, or None for the synchronous path
    reads.start()                             # at the loop's start: the worker's schedule (none on the sync path)
    reads.due(now)                            # each pass: the sync path runs every read now due on this thread
    reads.merge(reads.latest(), now)          # each pass: every result newer than the last merged, then the checks
    reads.end()                               # at the loop's end: the worker stopped and joined

THE READS: stats and players every SERVER_POLL_S, damage every DAMAGE_POLL_S (its `since` read off `since_i` at each
call), each due at its first chance. On the synchronous path (`polls` None) `due(now)` runs them on the loop's thread,
as the first Plan 22 acceptance driver did, and a read that raises propagates out of the loop (xlib's BusDead ends it
as bus_dead); through a PollThread `due` does nothing, the worker runs them, and a read that raised on the worker
arrives from `latest()` as an error (that half failed), so a slow bus never holds the loop.
`latest()` returns [(name, result, error)]: the sync path's results since the last call, or the worker's errors and
then each read whose (result, wall) tuple is newer than the last merged.
`merge(results, now)`: a stats result into the World's server map, a pump, one needs row [gameMin, hunger, thirst,
fatigue, health, serverHunger] off the frame nearest the read's wallMs with its pair row {frameSeq, frameWallMs,
serverWallMs, dtMs, paired (within PAIR_S)}; a players result read as the list of names (an error reply kept as
players_error); a stats half and a players half make one server poll (a half arriving twice closes the round, the
other half counted failed), a poll with neither a stats map nor a players list counted failed; a damage result's new
records merged into the World, kept (the last SERVER_RECORDS_KEPT), summed by tag, a gap in the indices counted
`lost`. Then the checks, in the order the synchronous poll made them: a players list without the user is a death,
a bus xlib marked dead is bus_dead, BUS_DEAD_POLLS consecutive failed polls is bus_dead, and a worker that ended
outside a read is an error (each a session.Stop).
THE WORKER AND THE MAIN THREAD: session.py's docstring. `end()` joins the worker with the session's polls_join_s and
records loop.polls_joined; `busy()` is True while it still runs a read (the death record then skips its final damage
read: one bus caller at a time). `damage_poll(args)` is the one read made outside the schedule (the damage hook's
install and the death record's last read), always on the caller's thread.
"""
from collections import deque

from agent.driverlib import session as DS


class ServerReads:
    def __init__(self, session, polls=None):
        self.s = session
        self.polls = polls
        lim = session.lim
        self.jobs = (("stats", lim["SERVER_POLL_S"], self.read_stats),
                     ("players", lim["SERVER_POLL_S"], self.read_players),
                     ("damage", lim["DAMAGE_POLL_S"], self.damage_read))
        self.needs, self.needs_pairs = [], []
        self.server_polls = self.server_fails = self.fails_in_row = 0
        self.players_error = None
        self.since_i = 0              # the largest damage record index merged; each damage read asks since it
        self.server_records = deque(maxlen=lim["SERVER_RECORDS_KEPT"])
        self.damage = {"polls": 0, "fails": 0, "since": 0, "merged": 0, "lost": 0, "dropped": None, "counts": None,
                       "totals": {}}
        self._next = {}               # sync: the clock time each read is next due, by name
        self._ready = []              # sync: the results run by due() and not yet returned by latest()
        self._seen = {}               # polls: the (result, wall) tuple last merged, by name
        self._round = {}              # the current server poll's halves, {"stats"|"players": ok}
        self._err_i = 0               # polls: the worker's errors already returned

    # -- the reads (run on the loop's thread, or on the worker) --------------------------------------------------
    def read_stats(self):
        return DS.DL.bus_stats(self.s.xs, self.s.user) or {}

    def read_players(self):
        return self.s.players(self.s.xs)      # looked up at each read: a test or driver may swap it

    def damage_read(self, args=None):
        """The damage.watch step's ack; `since` is the largest index merged when the call is made."""
        args = args or "%s since %d" % (self.s.user, self.since_i)
        return self.s.xs.step("damage_watch", DS.X.SRV, "damage.watch", args, timeout=self.s.lim["SERVER_TIMEOUT_S"],
                              log=False).get("ack")

    def damage_poll(self, args=None):
        """One damage.watch read on the caller's thread, merged; the ack."""
        self.damage["polls"] += 1
        return self.damage_merge(self.damage_read(args))

    # -- the interface the loop calls ---------------------------------------------------------------------------
    def start(self):
        if self.polls is None:
            self._next = {name: None for name, _, _ in self.jobs}
            return
        for name, every, fn in self.jobs:
            self.polls.schedule(name, every, fn)
        self.polls.start()

    def due(self, now):
        """The sync path: every read due at `now` run on this thread (a raise propagates); through a PollThread,
        nothing (the worker runs them)."""
        if self.polls is not None:
            return
        for name, every, fn in self.jobs:
            nxt = self._next.get(name)
            if nxt is None or now >= nxt:
                self._next[name] = now + every
                self._ready.append((name, fn(), None))

    def latest(self):
        """[(name, result, error)] newer than the last call's (the module docstring)."""
        if self.polls is None:
            got, self._ready = self._ready, []
            return got
        errs = self.polls.errors[self._err_i:]
        self._err_i += len(errs)
        got = [(e["name"], None, e["error"]) for e in errs]
        for name, _, _ in self.jobs:
            new = self.polls.latest(name)
            if new[1] is not None and new is not self._seen.get(name):
                self._seen[name] = new
                got.append((name, new[0], None))
        return got

    def merge(self, results, now):
        """Each result merged, then the death, dead-bus, failed-poll and worker checks (each raises session.Stop)."""
        names = None
        for name, result, error in results:
            if name == "damage":
                self.damage["polls"] += 1
                if error is None:
                    self.damage_merge(result)
                else:
                    self.damage["fails"] += 1
                    self.damage["last_error"] = str(error)[:300]
            elif name == "stats":
                self._half("stats", error is None and self.merge_stats(result or {}))
            elif name == "players":
                if error is None:
                    names = self.read_names(result, now)
                    self._half("players", names is not None)
                else:
                    self.players_error = {"wallS": now - self.s.t_loop0, "reply": str(error)[:300]}
                    self._half("players", False)
        self.check_death(names)
        if self.s.xs.bus_dead:
            raise DS.Stop("bus_dead", "server bus dead after %s" % self.s.xs.bus_dead)
        self.check_fails()
        t = getattr(self.polls, "_thread", None)
        if t is not None and not t.is_alive():
            raise DS.Stop("error", "the poll worker ended outside a read")

    def end(self):
        """The worker stopped and joined (the session's polls_join_s); loop.polls_joined records whether it ended,
        and a worker still in a read is noted."""
        s = self.s
        if self.polls is None or "polls_joined" in s.loop:
            return
        joined = self.polls.stop(s.polls_join_s)
        s.loop["polls_joined"] = joined
        if not joined:
            s.xs.note("the poll worker did not end within %ss: a read still in flight" % s.polls_join_s)

    def busy(self):
        return self.polls is not None and self.polls.alive()

    # -- the merges ---------------------------------------------------------------------------------------------
    def merge_stats(self, r):
        """One stats.all read ({ack, wallMs}) merged: the World's server map, a pump, the needs row and its pair row.
        True when it carried a stats map."""
        s = self.s
        stats = DS.server_stats(DS._d(r).get("ack"))
        if stats is not None:
            s.world.merge_server(stats, r.get("wallMs"))
        s.pump()
        f, pair = DS.pair_frame(list(s.frames), DS._d(r).get("wallMs"), s.lim["PAIR_S"])
        self.needs.append(DS.needs_row(f, stats))
        self.needs_pairs.append(pair)
        return stats is not None

    def read_names(self, reply, now):
        names = DS.players_list(reply)
        if names is None:
            self.players_error = {"wallS": now - self.s.t_loop0, "reply": str(reply)[:300]}
        return names

    def damage_merge(self, ack):
        """The new records merged into the World, kept with their i and server wall, and summed by tag; a gap in the
        indices (records aged out of the server's list) counts in `lost`. A record merged twice is skipped."""
        s, dm = self.s, self.damage
        if not (isinstance(ack, dict) and ack.get("ok") is True):
            dm["fails"] += 1
            dm["last_error"] = str(ack)[:300]
            return ack
        merge_ms = s.clock() * 1000.0
        seen = set(s.world.damage_seen_i)
        new = [r for r in DS.damage_last(ack) if r["i"] not in seen]
        s.world.merge_damage(ack, merge_ms)
        for r in new:
            if r["i"] > self.since_i + 1:
                dm["lost"] += int(r["i"] - self.since_i - 1)
            self.since_i = max(self.since_i, r["i"])
            tag = str(r.get("tag"))
            self.server_records.append({"i": r["i"], "tag": tag, "amount": r.get("amount"), "wall": r.get("wall"),
                                        "wallMs": merge_ms})
            t = dm["totals"].setdefault(tag, {"n": 0, "amount": 0.0})
            t["n"] += 1
            t["amount"] += DS._num(r.get("amount")) or 0.0
        dm["merged"] += len(new)
        dm["since"], dm["dropped"], dm["counts"] = self.since_i, ack.get("dropped"), ack.get("counts")
        return ack

    # -- the server poll's count and checks ---------------------------------------------------------------------
    def _half(self, name, ok):
        """One half of a server poll arrived; a poll is closed when both have, or when a half arrives twice (the other
        then counts failed)."""
        if name in self._round:
            self._close_round()
        self._round[name] = bool(ok)
        if len(self._round) == 2:
            self._close_round()

    def _close_round(self):
        rd, self._round = self._round, {}
        self.server_polls += 1
        if any(rd.values()):
            self.fails_in_row = 0
        else:
            self.server_fails += 1
            self.fails_in_row += 1

    def check_death(self, names):
        if names is not None and self.s.user not in names:
            raise DS.Stop("death", "players reply without %s: %s" % (self.s.user, names))

    def check_fails(self):
        if self.fails_in_row >= self.s.lim["BUS_DEAD_POLLS"]:
            raise DS.Stop("bus_dead", "%d consecutive failed server polls, %ss apart" % (
                self.fails_in_row, self.s.lim["SERVER_POLL_S"]))
