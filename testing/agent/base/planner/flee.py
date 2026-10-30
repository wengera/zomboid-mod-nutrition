"""The Flee (Plan 22 Task 10, spec § 3; ruling P23-AG's flee to shelter and its way out), one of the multi-step
policies whose common rules (`Policy`, one action at a time, distances, the shared reads and the way out's and the
shelter's square reads) are `policies.py`'s; moved out of it whole at Plan 24 Task 36 (a pure move: its rules,
constants and record unchanged; the constants stay in `policies.py`).

- `Flee` (one per flee episode): a `Steer` of `FLEE_S` seconds away from the threats (the `threats` list its caller
  passes, else every zombie the World holds), at a run (ruling P24-O, Task 12: the planner never sprints; E6 sprinted
  13 steers and Angus saw the character trip, and a fence climb begun at a sprint rolls a trip, #4296); re-aimed on
  every end of its steer. Every leg runs along the sum of the unit vectors from each threat to the player, each weighted
  by 1/distance (ruling P23-AG 3, amended at fix round 1 to every leg: away from the centroid and from the nearest, so a
  group spread round the player is not fled into); a zero sum steers along +x. The steer reads the map (fix round 1, I4:
  the chain's E1 died sprinting 15 s into a fence the World already held as `blockW`, the group biting): the away vector
  turns by STEER_TURNS (30, 60, 90 degrees either way, nearest first) to the first heading whose `world.line_clear` over
  AHEAD_R (9 tiles, about a leg's run: fix round 3, F3) and over STEER_PROBE is true (survival 2, the fix-3 review's
  (a): the two rasterised lines cross different squares, so a 9-tile clear alone may graze a wall the 3-tile line
  meets), else over STEER_PROBE (3) tiles, an unknown square read
  open (`unknown_open`, its unknown diagonal corner open too: F5) (fix round 2, concern 1: unscanned ground is no wall,
  so the flee does not bend along the scanned area's edge), and along which no held threat beyond NEAR_R lies within
  AHEAD_R (9 tiles, a 3 s leg at E1's 3 tiles/s) inside AHEAD_CONE (20 degrees) or in the CORRIDOR_R tube (fix round 2,
  T2: E1's first leg, set by a melee zombie at 0.18 tiles, ran at the far pair); with none such, the first clear on the
  map, else the away vector kept. A leg that ended having moved under STUCK_MOVE (0.5) tiles is stuck, and the next
  leg's turn skips the away vector's own 0 and every heading within STUCK_SKIP_DEG (15 degrees) of the stuck leg's (F4).
  The way out (ruling P23-AJ 3, as amended: E2 died steering into its own room's walls in a building whose doors were
  all broken): on a room square, with no shelter plan running or held, each choose (the episode's start and every
  re-aim) takes `exit_plan`, of the building's `night.exits` (its openings, `world.openings`, and its closed,
  unbarricaded exterior doors at their approach squares) the one whose outside square is no nearer any held threat
  than the player is to it and lies farthest from their centroid, and runs it: a closed door opened first (`Interact`
  open), then a `WalkTo` at FLEE_GAIT of the centre of the square one on beyond the outside square (`_beyond`, when
  the map holds it open: a walk ends `done` within the Lua's DONE_R, so the outside square's own centre may end it on
  the room square); a superseded step is sent again, any other failed end, or a walk that ended done with the frame
  still inside, refuses that exit for the episode (`refused`) and the next choose takes the next. Fix round 1: no
  window's edge is an opening (`world.openings`, the review's G1); an exit with no open square beyond is skipped
  (I1); the walk goes first even at a closed door, the open only after it fails there (I2); a walk that leaves the
  player within STUCK_MOVE for WALK_STALL_S is dropped and read as failed (G2); the
  exit is the nearest acceptable one, its straight line passing no held threat within EXIT_CLEAR_R; with none, the
  building is adopted once an episode (`_adopt`, iteration 1's fix round 2 brought back as the fallback: the
  sheltered hold, the re-close guard, the door fight), and with that dropped or no exterior door the Flee holds with
  no command (`trapped`): on a room square it never steers (Survive's corner fights at melee range); the frame
  reading
  outside ends the exit, the building is `left` (never the episode's shelter) and the steer follows.
  The shelter (ruling P23-AG 1): at each re-aim until a plan is chosen (fix round 2, T1: a melee zombie's corridor
  refusal is retried once it has moved), the episode picks, never from a room square: of the buildings not shunned
  (`night.shunned_now` over `shunned`, Night's store) nor left this episode with
  no known zombie on one of their room or door squares, the exterior door the map reads neither locked nor barricaded
  whose `night.approach_square` lies within SHELTER_FLEE_R (25 tiles) of the player, is no nearer any held threat than
  the player is to it, and has no known zombie ahead within CORRIDOR_R (2 tiles) of the straight line to it
  (`in_corridor`), the nearest such square first; the plan (`night.shelter_plan(..., door=)`) is kept to that door, and
  its steps (`night.shelter_step`: approach, open, enter, close) go out with their walks at FLEE_GAIT, a run (never a
  sprint: P24-O). A step's end is read by `night.shelter_ended`: `advance`, `resend`
  and `passed` keep the plan; any other end drops it for the steer (the episode never picks again), shunning the
  building only for a reason in `night.SHUN_REASONS`. Once the close ended with the player inside (`sheltered`), choose
  holds with no command while every threat reads line-blocked (`line_to` False), or while the door reads closed and no
  threat's line reads clear (an unknown line holds: concern 2), and while `hold_ok` (Survive clears it on a breach,
  ruling P23-AJ 1); else it re-sends the close when the door reads open (again after each close that ended done, never
  after one that did not), unless a known zombie stands within DOOR_CLEAR_R (1.5 tiles) of the door (concern 4) or the
  player's square is no nearer the door square than every known zombie's (F2: the Lua's close walks the player to the
  door); else drops the plan, and the way out or the steer follows. A plan done with the player outside is dropped for
  the steer. `night` imports this module at its top, so the Flee imports `night` at the call (`_night()`).
  Survival 3 (ruling P23-AM, the chain's E3): a shelter step's walk (approach, enter, or an open's or close's walk
  while the player stands more than one square from the door, the Lua interact's own approach) that leaves the
  player within STUCK_MOVE for WALK_STALL_S (1.0) wall seconds while a held threat is within DANGER_R is dropped
  (`ended` `stalled`, `_dropped` as the exit's walk) with its plan for the episode (never shunned in the night's
  store), and the steer follows at once; with no held threat within DANGER_R the step waits the Lua's stuck time.
  P23-AM 3's group sprint (a `many` flee sprinting while the endurance allowed) is gone with every other sprint
  (ruling P24-O). With `steer_now` (Survive's group at melee range, its last leg not stuck), the choose steers first.
  Survival 4 (ruling P23-AP 3, E4's line 440: a leg aimed west before two zombies there were listed ran 8.92 tiles
  into them): on every threat tick the running steer leg's heading is re-read against the held threats (`_cut_leg`:
  `_ahead`, AHEAD_R, AHEAD_CONE and the CORRIDOR_R tube, beyond NEAR_R); a threat ahead that was not ahead when the
  leg was aimed cuts it, and the next choose re-aims by the turn rules (its why's `cut` the ids), the new leg
  superseding it. Fix round 1: the cut reads the World's current records by id (G1), and a cornered Fight
  (`point_blank`) re-pins at each choose to the nearest zombie within POINT_BLANK_R (R4).
  Survival 5 (ruling P24-A; survive.py's docstring is the record): the re-pin only while the pin stands beyond
  POINT_BLANK_R (d); no approach walk at point blank (e); no attack while the frame's `me.hitReaction` names one
  (`hit_reaction`, i); `others_behind` (b), Survive's look past a fight's walk target; the episode's first leg
  repulsed from `World.met_window`'s centre too (a); on a room square `steer_now` never steers: the exit (at a run
  since P24-O), else the adoption or the trapped hold, and `give_way` keeps a running exit (f).
"""
import math
import time

from agent.base.planner.policies import (AHEAD_CONE, AHEAD_R, DANGER_R, DISENGAGE_R, DOOR_CLEAR_R, FLEE_GAIT, FLEE_S,
                                         NEAR_R, PREEMPTED, SHELTER_FLEE_R, STEER_PROBE, STEER_TURNS, STEP_PROBE,
                                         STUCK_MOVE, STUCK_NEAR_R, STUCK_SKIP_DEG, WALK_STALL_S, WIDE_TURNS, Policy,
                                         _night, _rotate, away_vector, centre, clear_heading, exit_plan, in_building,
                                         in_corridor, line_to, on_post, on_room, running, stand_post, target_id_ok,
                                         zdist)
from agent.base.pza1 import Interact, Steer, Stop, WalkTo
from agent.base.world import me_floor, me_xy

__all__ = ["Flee"]


class Flee(Policy):
    def __init__(self, world, actions, clock=time.time, threats=None, shunned=None):
        super().__init__(world, actions, clock)
        self.threats = threats   # the zombies to flee; None: every zombie the World holds
        self.shunned = {} if shunned is None else shunned   # building -> world minutes shunned at (Night's store)
        self.plan = None         # the shelter plan this episode runs (night.shelter_plan kept to one door), else None
        self.picked = False      # a shelter plan was chosen this episode (once dropped, the episode only steers)
        self.ended = None        # the outcome of the last shelter step end read (night.shelter_ended)
        self.exit = None         # the way out this episode runs (`exit_plan`, P23-AJ 3), else None
        self.refused = set()     # the outside squares of exits that failed this episode
        self.left = set()        # the buildings this episode walked out of (never its shelter)
        self.hold_ok = True      # Survive clears it while a held threat breaks the hold (P23-AJ 1)
        self.adopted = False     # the building stood in was adopted this episode (fix round 1: once)
        self.steer_now = False   # Survive sets it: a group at melee range, the last leg not stuck (P23-AM 4)
        self._chosen = None      # "step", "close" or "exit": what the last choose returned, until it is sent
        self._step = None        # the last shelter step's Action
        self._step_anchor = None  # (wall, (x, y)) of the shelter step's send or its walk's last STUCK_MOVE (P23-AM 2)
        self._read = None        # the last shelter step whose end observe() read
        self._close = None       # the last re-sent close's Action (the sheltered re-close)
        self._exit_a = None      # the last exit step's Action
        self._exit_read = None   # the last exit step whose end observe() read
        self._exit_anchor = None  # (wall, (x, y)) of the exit step's send or its walk's last STUCK_MOVE (G2)
        self._dropped = None     # an exit or shelter walk dropped while still current (G2, P23-AM 2): not waited on
        self._leg = None         # (Action, (x, y) at its send, heading, ids ahead at its aim) of the last steer leg
        self._aimed = frozenset()  # the held ids `_ahead` of the heading the last `_steer` chose (P23-AP 3)
        self._cut = None         # the ids newly ahead that cut the running leg (P23-AP 3), till a steer logs them
        self._leg_anchor = None  # (wall, (x, y)) of the running leg's send or its last STUCK_MOVE (fix round 1, R1)
        self._leg_still = 0.0    # wall seconds the running leg has left the player within STUCK_MOVE of that anchor
        self.skip_heading = None  # Survive sets it: a stuck heading from before this Flee (a `stuck` corner's leg),
                                  # skipped by the first leg's turn as F4 skips a stuck leg's (P24-A fix 2, G2)
        self.stand_ok = False    # Survive sets it each tick: a shelter picked now is a doorway stand (ruling P24-AO,
                                 # `planner.doorway`)

    @property
    def sheltered(self):
        """The episode's shelter plan read done (its close ended) and is kept."""
        return self.plan is not None and self.plan["step"] == "done"

    def running_shelter(self):
        """A shelter plan is running and its close has not ended (Survive's inside hold waits for it)."""
        return self.plan is not None and self.plan["step"] != "done"

    def standing_door(self):
        """The doorway stand runs (ruling P24-AO): the plan's enter ended where its close would go (`stand`)."""
        return self.plan is not None and self.plan["step"] == "stand"

    def closing_stand(self):
        """A doorway stand left (Survive's `_doorway`) and its close not yet ended: the stand's own shelter step."""
        return self.plan is not None and bool(self.plan.get("stood")) and self.plan["step"] == "close"

    def running_exit(self):
        """A way out is running (Survive's inside hold waits for it, as for the shelter steps)."""
        return self.exit is not None

    def door(self):
        """The plan's one door square, else None."""
        return self.plan["doors"][0] if self.plan is not None else None

    def _threats(self):
        ts = self.threats if self.threats is not None else list(self.world.zombies.values())
        return [z for z in ts if z.get("x") is not None and z.get("y") is not None]

    def _known(self):
        return [z for z in self.world.zombies.values() if z.get("x") is not None and z.get("y") is not None]

    def _drop(self, shun):
        """Drop the plan: the steer for the rest of the episode; the building shunned only for a shun reason (M1)."""
        if shun:
            self.shunned[self.plan["building"]] = self.world.world_minutes()
        self.plan = None

    def observe(self):
        self._observe_exit()
        if self._leg is not None and running(self.actions, self._leg[0]):
            self._leg_anchor, self._leg_still = self._still_for(self._leg_anchor)
            self._cut_leg()
        a = self._step
        if a is None or a is self._read or self.plan is None:
            return
        if not self.actions.done(a):
            if self._step_stalled(a):
                self._dropped, self._read, self.ended = a, a, "stalled"
                self._drop(False)   # this episode only (`picked` stays): the steer follows at once
            return
        self._read = a
        self.ended = _night().shelter_ended(self.plan, a)
        if self.ended not in ("advance", "resend", "passed"):
            self._drop(a.state == "failed" and a.reason in _night().SHUN_REASONS)
        elif self.plan.get("stand") and self.plan["step"] == "close":   # P24-AO: the enter ended, the close is the
            self._stand_at_post()                                           # stand's (`planner.doorway`)

    def _stand_at_post(self):
        """P24-AO, Task 32 fix 1 (the review's blocker): the enter of a stand plan ended; the stand starts only on its
        post (`on_post`); else the enter is walked again (`ended` "outside", a retry: STEP_RETRIES, as Night's own
        `outside` read), and once they are spent the stand is given up for today's close."""
        plan = self.plan
        if on_post(self.world, plan["building"]):
            plan.update(step="stand", stood=True, quiet=self.clock())
            return
        plan["retries"] += 1
        self.ended = "outside"
        if plan["retries"] < _night().STEP_RETRIES:
            plan["step"] = "enter"
        else:
            plan["stand"] = False

    def _ids(self, zs):
        """The World's ids of the zombie records `zs` (this tick's dicts), sorted."""
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        return sorted((ids.get(id(z)) for z in zs), key=repr)

    def _cut_leg(self):
        """Ruling P23-AP 3 (E4's line 440: a leg aimed west before 19032 and 19035 were listed ran 8.92 tiles into
        them): the running steer leg's heading re-read against this tick's held threats beyond NEAR_R (`_ahead`: the
        cone and the tube the aim refuses); one ahead that was not ahead at its aim cuts it (`_dropped`, so the next
        choose re-aims by the turn rules and the new leg supersedes it), logged as the next steer's `cut`. Fix round 1
        (the review's G1): the World's current records by id, the held ones (within DISENGAGE_R) beyond NEAR_R, never
        the caller's list, which may be the last tick's records, every one replaced since by its frame (an id read None
        is never new: e07a52cb cut a fallback leg on every tick, so R1's stuck read never came)."""
        leg = self._leg
        if leg[0] is self._dropped:
            return
        far = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and z.get("x") is not None
               and z.get("y") is not None and NEAR_R < zdist(self.world, z) <= DISENGAGE_R]
        ahead = {id(z) for z in self._ahead(leg[2], [z for _, z in far])}
        new = sorted((zid for zid, z in far if id(z) in ahead and zid not in leg[3]), key=repr)
        if new:
            self._dropped, self._cut = leg[0], new

    def _still_for(self, anchor):
        """`(anchor, seconds)`: the anchor `(wall, (x, y))` moved on to now when the player has moved STUCK_MOVE or
        more from it, and the wall seconds the player has stood within STUCK_MOVE of it (G2, P23-AM 2)."""
        now, pos = self.clock(), me_xy(self.world)
        if math.hypot(pos[0] - anchor[1][0], pos[1] - anchor[1][1]) >= STUCK_MOVE:
            return (now, pos), 0.0
        return anchor, now - anchor[0]

    def _step_stalled(self, a):
        """Ruling P23-AM 2 (E3: the enter walk stood 14.5 s while the group closed from 7.9 tiles to 0.48): a shelter
        step still current whose walk has left the player within STUCK_MOVE for WALK_STALL_S wall seconds while a
        held threat is within DANGER_R. An `open` or `close` walks only while the player stands more than one square
        (Chebyshev) from the door (the Lua's interact `approach`); at the door its anchor follows the player, the
        door's own action being no walk. With no held threat within DANGER_R the step waits the Lua's stuck time."""
        if not running(self.actions, a):
            return False
        if a.type == "interact":
            sq, door = _night().player_square(self.world), self.door()
            if sq is None or max(abs(sq[0] - door[0]), abs(sq[1] - door[1])) <= 1:
                self._step_anchor = (self.clock(), me_xy(self.world))
                return False
        self._step_anchor, still = self._still_for(self._step_anchor)
        return still >= WALK_STALL_S and any(zdist(self.world, z) <= DANGER_R for z in self._threats())

    def busy(self):
        """As `Policy.busy`, except for an exit or shelter walk dropped while still current (G2, P23-AM 2): the next
        choose answers."""
        return super().busy() and self.last is not self._dropped

    def give_way(self):
        """P23-AM 4 with the coordinator's amendment 6 (E3: the enter walk ran on with three zombies at half a tile):
        Survive's group steer drops a running shelter or exit step (`_dropped`; the plan for the episode, `ended`
        `pre-empted`; the exit refused), so the steer goes at once; a running steer leg, or anything else, is kept. On
        a room square a running exit step is kept (ruling P24-A (f): inside, the group's answer is the exit; its walk
        is no longer re-sent at a sprint, P24-O)."""
        if not self.busy() or self.last.type not in ("walkTo", "interact"):
            return
        if self.last is self._exit_a and self.exit is not None and on_room(self.world):
            return
        self._dropped = self.last
        if self.last is self._step and self.plan is not None:
            self._read, self.ended = self._step, "pre-empted"
            self._drop(False)
        elif self.last is self._exit_a and self.exit is not None:
            self._exit_read = self._exit_a
            self._refuse_exit()

    def _observe_exit(self):
        """An exit step's end, and a running walk's progress (fix round 1, the review's G2): a walk that has left the
        player within STUCK_MOVE of where it last moved for WALK_STALL_S wall seconds is dropped while still current
        (`_dropped`) and read as failed. An open `done` goes back to the walk (`opened`); a superseded step is sent
        again; a walk `done` with the frame reading outside waits for the choose to read it out (`_exit_step`); a
        walk that failed, stalled or ended `done` with the frame still inside goes to the open when its way out is a
        closed door not yet opened (I2), else refuses that exit for the episode, as does a failed open (P23-AJ 3: the
        next choose takes the next way out, else the adoption or the trapped hold)."""
        a = self._exit_a
        if a is None or a is self._exit_read or self.exit is None:
            return
        if not self.actions.done(a):
            if self.exit["step"] != "walk" or not running(self.actions, a):
                return
            self._exit_anchor, still = self._still_for(self._exit_anchor)
            if still < WALK_STALL_S:
                return
            self._dropped = a
        self._exit_read = a
        if a.state == "failed" and a.reason == PREEMPTED:
            return
        e = self.exit
        if e["step"] == "open":
            if a.state == "done":
                e["step"], e["opened"] = "walk", True
            else:
                self._refuse_exit()
        elif a is self._dropped or a.state != "done" or on_room(self.world):
            if e["door"] is not None and not e["opened"]:
                e["step"] = "open"
            else:
                self._refuse_exit()

    def _refuse_exit(self):
        self.refused.add(self.exit["outer"])
        self.exit = None

    def _pick(self, ts):
        """The shelter plan to run (ruling P23-AG and its fix rounds), else None: never from a room square (P23-AJ
        3: inside, the flee walks out first, `exit_plan`); else, of the doors `door_verdicts` reads `ok`, the nearest
        approach square first, ties by the building, then the door; the plan `night.shelter_plan(..., door=)` kept to
        that door."""
        if on_room(self.world):
            return None
        ok = [(rank, b, door) for rank, b, door, verdict in self.door_verdicts(ts) if verdict == "ok"]
        if not ok:
            return None
        _, b, door = min(ok)
        return _night().shelter_plan(self.world, b, door=door)

    def door_verdicts(self, ts):
        """The pick's reads of each door (Plan 24 Task 36: split out of `_pick` so that ruling P24-AX's log reads the
        same doors, `Survive._doorway_pick`): `[(rank, building, door, verdict)]` for each exterior door of a building
        not shunned (`night.shunned_now`) nor walked out of this episode (`left`) whose `night.approach_square` lies
        within SHELTER_FLEE_R of the player, `rank` (its distance, the building's repr, the door); `verdict` "locked"
        when the map reads it locked or barricaded, "taken" when a known zombie stands on one of the building's squares
        (M4), in the door's corridor (`in_corridor`, I1 and M3) or nearer its approach square than to the player (a
        held threat of `ts`), else "ok"."""
        N = _night()
        mx, my = me_xy(self.world)
        known = self._known()
        skip = N.shunned_now(self.shunned, self.world.world_minutes()) | self.left
        out = []
        for b in self.world.interiors():
            if b is None or b in skip:
                continue
            occupied = any(in_building(self.world, z, b) for z in known)
            plan = N.shelter_plan(self.world, b)
            for door in plan["doors"] if plan is not None else ():
                sq = N.approach_square(self.world, door)
                if sq is None:
                    continue
                c = (sq[0] + 0.5, sq[1] + 0.5)
                d = math.hypot(c[0] - mx, c[1] - my)
                if d > SHELTER_FLEE_R:
                    continue
                rec = self.world.map[door].get("door") or {}
                if rec.get("locked") or rec.get("barricaded"):
                    verdict = "locked"
                elif (occupied or any(in_corridor((mx, my), c, z) for z in known)
                        or any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < zdist(self.world, z) for z in ts)):
                    verdict = "taken"
                else:
                    verdict = "ok"
                out.append(((d, repr(b), door), b, door, verdict))
        return out

    def _shelter(self, ts):
        """The plan's next step (its walks at FLEE_GAIT); once done inside, a hold while every threat reads
        line-blocked, or while the door reads closed and no threat's line reads clear (an unknown line holds: fix
        round 2, concern 2); else one re-sent close of a door that reads open (again after each close that ended
        done), unless a known zombie stands within DOOR_CLEAR_R of the door (concern 4) or the player's square is no
        nearer the door square than every known zombie (fix round 3, F2: the Lua's close walks the player to the door,
        so never toward a zombie nearer it); else the plan dropped (I2). None with the plan dropped: the steer
        follows."""
        N = _night()
        b = self.plan["building"]
        if self.plan["step"] == "stand":   # P24-AO: the stand is Survive's Doorway fight; the Flee holds its plan
            self.why = {"shelter": b, "step": "stand"}
            return None
        cmd, step = N.shelter_step(self.world, self.plan)
        if step == "shun":
            self._drop(True)
            return None
        if step != "done":
            self._chosen = "step"
            self.why = {"shelter": b, "step": step, "ended": self.ended}
            return cmd if cmd.TYPE != "walkTo" else WalkTo(cmd.x, cmd.y, FLEE_GAIT)
        if not on_room(self.world):
            self._drop(False)   # pushed out after the close: no shelter this episode
            return None
        door = self.door()
        rec = (self.world.map.get(door) or {}).get("door")
        if self.hold_ok and self.shelter_holds(ts):
            self.why = {"shelter": b, "step": "done"}
            return None
        failed = self._close is not None and self.actions.done(self._close) and self._close.state != "done"
        sq = N.player_square(self.world)
        mine = math.hypot(sq[0] - door[0], sq[1] - door[1])   # square to square, as each zombie's below
        guarded = any(math.hypot(z["x"] - door[0] - 0.5, z["y"] - door[1] - 0.5) < DOOR_CLEAR_R
                      or math.hypot(math.floor(z["x"]) - door[0], math.floor(z["y"]) - door[1]) <= mine
                      for z in self._known())
        if rec is not None and rec.get("open") and not failed and not guarded:
            self._chosen = "close"
            self.why = {"shelter": b, "step": "reclose"}
            return Interact(door[0], door[1], "close")
        self._drop(False)
        return None

    def shelter_holds(self, ts):
        """The sheltered hold's reading of the lines: every threat line-blocked (`line_to` False), or the plan's door
        read closed and no threat's line read clear (an unknown line holds: fix round 2, concern 2)."""
        rec = (self.world.map.get(self.door()) or {}).get("door")
        lines = [line_to(self.world, z) for z in ts]
        closed = rec is not None and not rec.get("open")
        return all(ln is False for ln in lines) or (closed and all(ln is not True for ln in lines))

    def _exit_step(self):
        """The running exit's next command (P23-AJ 3), else None with the exit ended: outside (the frame reads no
        room square) the building is left and the steer follows; else the walk to the centre of the exit's `target`
        (`_beyond`) at FLEE_GAIT, or, after that walk failed at a closed door, its open (`Interact`, fix round 1 I2)."""
        e = self.exit
        if not on_room(self.world):
            self.left.add(e["building"])
            self.exit = None
            return None
        if e["step"] == "open" and ((self.world.map.get(e["door"]) or {}).get("door") or {}).get("open"):
            e["step"], e["opened"] = "walk", True
        self._chosen = "exit"
        self.why = {"exit": e["building"], "outer": list(e["outer"]), "door": list(e["door"]) if e["door"] else None,
                    "step": e["step"], "shelter": None, "refused": sorted(map(list, self.refused))}
        if e["step"] == "open":
            return Interact(e["door"][0], e["door"][1], "open")
        return WalkTo(*centre(e["target"]), FLEE_GAIT)   # P24-A (f)'s group exit, at a run since P24-O

    def _adopt(self, ts):
        """Fix round 1 (concern 1): the building stood in, every way out refused, adopted as sheltered: its plan kept
        to its open exterior door nearest the threats, else its exterior door nearest them (iteration 1's F1), read
        done, so the sheltered hold, the re-close guard and Survive's door fight apply; None with no exterior door on
        this floor (E2's building 3: its doors all broken)."""
        N = _night()
        b = (self.world.map.get(N.player_square(self.world)) or {}).get("building")
        doors = N.exterior_doors(self.world, b, me_floor(self.world), marked=True) if b is not None else []
        if not doors:
            return None
        marked = self.world.marked_doors()   # Task 18 fix 1, major 4: kept from inside, ranked after the others

        def rank(d):
            is_open = bool(((self.world.map.get(d) or {}).get("door") or {}).get("open"))
            return d in marked, not is_open, min(math.hypot(z["x"] - d[0] - 0.5, z["y"] - d[1] - 0.5) for z in ts), d
        return N.shelter_plan(self.world, b, door=min(doors, key=rank), step="done", marked=True)

    def choose(self):
        """The running exit; else the shelter (picked at each re-aim until one is chosen: fix round 2, T1, and never
        from a room square); else, on a room square, a new exit (`exit_plan`, P23-AJ 3), else, once an episode, the
        building adopted (`_adopt`, fix round 1), else the trapped hold (no command, `why.trapped`: on a room square
        the flee never steers, fix round 1: steering inside killed E2); else the steer. With `steer_now` (P23-AM 4 and
        AP 2: Survive's group, `_group`, the last leg not stuck) the steer goes first off a room square (the next leg
        that ends stuck is Survive's corner); on a room square (ruling P24-A (f), the close review's I4: the group
        steer ran inside a room with a way out, E2's death mode) the steer is never sent: the running exit, else a new
        one, walked at a run (P24-O), else the adoption, else the trapped hold."""
        self._chosen = None
        ts = self._threats()
        if not ts:
            self.why = {"centroid": None, "shelter": None}
            return None
        if self.steer_now and not on_room(self.world):
            return self._steer(ts)
        if self.exit is not None:
            cmd = self._exit_step()
            if cmd is not None:
                return cmd
        if not self.picked:
            self.plan = self._pick(ts)
            self.picked = self.plan is not None
            if self.plan is not None and self.stand_ok:   # P24-AO: the door taken for the doorway stand, its post
                way = self.world.door_way(self.door())       # reached by a walk past it (`stand_post`, fix 1)
                post = None if way is None else stand_post(self.world, way, self.plan["building"], self.trans)
                if post is not None:
                    self.plan.update(stand=True, way=way, post=post)
        if self.plan is not None:
            cmd = self._shelter(ts)
            if cmd is not None or self.plan is not None:
                return cmd
        if on_room(self.world):
            self.exit = exit_plan(self.world, ts, self.refused, self.trans)
            if self.exit is not None:
                return self._exit_step()
            if not self.adopted:
                self.adopted = True
                self.plan = self._adopt(ts)
                if self.plan is not None:
                    cmd = self._shelter(ts)
                    if cmd is not None or self.plan is not None:
                        return cmd
            self.why = {"trapped": (self.world.map.get(_night().player_square(self.world)) or {}).get("building"),
                        "shelter": None, "refused": sorted(map(list, self.refused))}
            if self._dropped is not None and self.actions.current is self._dropped:
                return Stop()   # the dropped walk is still running: stand (G2)
            return None
        return self._steer(ts)

    def _leg_moved(self):
        """Tiles the player stands from the last steer leg's start once that leg ended, else None."""
        if self._leg is None or not self.actions.done(self._leg[0]):
            return None
        mx, my = me_xy(self.world)
        return math.hypot(mx - self._leg[1][0], my - self._leg[1][1])

    def stuck(self):
        """The last steer leg ended and moved the player under STUCK_MOVE tiles; or (survival 3 fix round 1, R1: E3's
        a40 stood 3 s, five zombies within 1.555 tiles, health 93.7 to 68.3) it still runs, has left the player
        within STUCK_MOVE for WALK_STALL_S (`observe`), and a held threat is within STUCK_NEAR_R."""
        d = self._leg_moved()
        if d is not None:
            return d < STUCK_MOVE
        if self._leg is None or not running(self.actions, self._leg[0]) or self._leg_still < WALK_STALL_S:
            return False
        return any(zdist(self.world, z) <= STUCK_NEAR_R for z in self._threats())

    def leg_heading(self):
        """The last steer leg's heading (vx, vy), else None."""
        return None if self._leg is None else self._leg[2]

    def drop_stuck_leg(self):
        """P24-A fix 2, I1: a running steer leg that reads stuck (`stuck`) is dropped (`_dropped`), so the choose
        re-aims at once with F4's skip; anything else is kept."""
        if self.busy() and self._leg is not None and self.last is self._leg[0] and self.stuck():
            self._dropped = self.last
            return True
        return False

    def _clear(self, v, reach=STEER_PROBE):
        return clear_heading(self.world, v, reach, self.trans)

    def _ahead(self, v, far):
        """The threats of `far` a leg along `v` would run at: within AHEAD_R and AHEAD_CONE of it, or in the
        CORRIDOR_R tube to AHEAD_R along it (fix round 2, T2)."""
        mx, my = me_xy(self.world)
        end = (mx + AHEAD_R * v[0], my + AHEAD_R * v[1])
        out = []
        for z in far:
            dx, dy = z["x"] - mx, z["y"] - my
            d = math.hypot(dx, dy)
            cone = d <= AHEAD_R and (dx * v[0] + dy * v[1]) >= d * math.cos(math.radians(AHEAD_CONE))
            if cone or in_corridor((mx, my), end, z):
                out.append(z)
        return out

    def _steer(self, ts):
        """A leg along the sum of the unit vectors from each threat to the player, each weighted by 1/distance (ruling
        P23-AG 3, amended at fix round 1: every leg), and on the episode's first leg the unit vector from the densest
        met window's centre (`World.met_window`, ruling P24-A (a)) weighted so too, logged `met` [cx, cy, n]; +x when
        the sum is zero (the away vector); turned by STEER_TURNS,
        nearest first, to the first heading clear of the map over AHEAD_R (fix round 3, F3: the leg runs about that
        far) and along which no held threat beyond NEAR_R lies ahead (`_ahead`, T2); else the first such heading
        clear over STEER_PROBE (I4; an unknown square open throughout); else the first clear over STEER_PROBE; else
        (Task 18, the E7 write-up's T19.5: four legs a71-a74 ran into a known fence corner, every turn within 90
        degrees blocked) the first of the rest of the circle (WIDE_TURNS) clear over AHEAD_R and STEER_PROBE with no
        held threat ahead (Task 18 fix 1, the review's minor 9: a 150 or 180 degree turn into the fled group is read
        first), else the first of them clear over STEER_PROBE, else the first of all whose first STEP_PROBE tile
        crosses no known blocked edge; else the away vector kept. After a leg that moved under STUCK_MOVE the turn skips the away vector's own 0 and every
        heading within STUCK_SKIP_DEG of the stuck leg's (F4), turning +30 when nothing is left."""
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for z in ts) / len(ts)
        cy = sum(z["y"] for z in ts) / len(ts)
        met = self.world.met_window() if self._leg is None else None   # P24-A (a): the episode's first leg only
        v = away_vector(self.world, [(z["x"], z["y"]) for z in ts] + ([met[:2]] if met is not None else []))
        v = (1.0, 0.0) if v is None else v
        stuck = self.stuck()
        h0 = self._leg[2] if stuck else (self.skip_heading if self._leg is None else None)
        turns = STEER_TURNS[1:] if h0 is not None else STEER_TURNS
        if h0 is not None:
            cos_skip = math.cos(math.radians(STUCK_SKIP_DEG))
            turns = tuple(t for t in turns if _rotate(v, t)[0] * h0[0] + _rotate(v, t)[1] * h0[1] < cos_skip)
        far = [z for z in ts if zdist(self.world, z) > NEAR_R]
        wide = tuple(t for t in WIDE_TURNS if h0 is None or _rotate(v, t)[0] * h0[0] + _rotate(v, t)[1] * h0[1]
                     < math.cos(math.radians(STUCK_SKIP_DEG)))
        turn, probe = None, None
        for reaches, group, among in (((AHEAD_R, STEER_PROBE), True, turns), ((STEER_PROBE,), True, turns),
                                      ((STEER_PROBE,), False, turns), ((AHEAD_R, STEER_PROBE), True, wide),
                                      ((STEER_PROBE,), False, wide), ((STEP_PROBE,), False, turns + wide)):
            turn = next((t for t in among if all(self._clear(_rotate(v, t), reach) for reach in reaches)
                         and not (group and self._ahead(_rotate(v, t), far))), None)
            if turn is not None:
                probe = reaches[0]
                break
        heading = _rotate(v, turn) if turn is not None else (_rotate(v, STEER_TURNS[1]) if h0 is not None else v)
        near = min(zdist(self.world, z) for z in ts)
        self._aimed = frozenset(self._ids(self._ahead(heading, far)))
        self.why = {"centroid": [cx, cy], "nearest": near, "turn": turn, "probe": probe, "stuck": stuck,
                    "ahead": self._ids(self._ahead(v, far)), "shelter": None, "ended": self.ended}
        if met is not None:
            self.why["met"] = [met[0], met[1], met[2]]
        if h0 is not None and not stuck:
            self.why["skip"] = [h0[0], h0[1]]   # fix 2, G2: the carried stuck heading
        if self._cut is not None:
            self.why["cut"], self._cut = self._cut, None
        return Steer(heading[0], heading[1], FLEE_S, FLEE_GAIT)   # P24-O: a run, never a sprint

    def sent(self, cmd, action):
        if self._chosen == "step":
            self._step, self._step_anchor = action, (self.clock(), me_xy(self.world))
        elif self._chosen == "close":
            self._close = action
        elif self._chosen == "exit":
            self._exit_a, self._exit_anchor = action, (self.clock(), me_xy(self.world))
        elif cmd.TYPE == "steer":
            mx, my = me_xy(self.world)
            self._leg = (action, (mx, my), (cmd.vx, cmd.vy), self._aimed)
            self._leg_anchor, self._leg_still = (self.clock(), (mx, my)), 0.0
        self._chosen = None
