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
  Survival 18 (ruling P25-W, `planner/doorway.py`): a doorway stand ended under a group hands its Flee `walk_out`:
  the plan dropped and the adoption spent, so the choose walks the way out, else holds trapped; never the close.
  Survival 19 (ruling P26-A, the `window_exit` rule, Survive's `WINDOW_EXIT`): the way out may be a window
  (`policies.exit_plan`, `night.window_exits`), ranked after every door and opening; its step `window` walks to the
  centre of the window's inside square at the flee's gait while the player is not on it, then sends `Window(x, y,
  smash)` once (`_window_step`); the climb's end is read as the goal layer's `_climb_ended` reads one
  (`_window_ended`): `done` leaves the next choose to read the frame off the room squares (`left`), a frame still on
  one refusing the exit; `failed`, `rejected` or `timeout` notes the window's failure in the World
  (`World.note_window_fail`, so a WINDOW_DEAD end leaves it out of the next `exits`) and refuses the exit. Ruling
  P26-B (`stand_second_exit`, `STAND_SECOND_EXIT`): with the pick a doorway stand's (`stand_ok`), a free door whose
  building has no other way out on its floor is refused `one_exit` (`door_verdicts`).
  Survival 20 (ruling P26-I, the `window_inner` rule, Survive's `WINDOW_INNER`): a window whose inside square reads
  `solid` or `solidTrans` (E17's kitchen counter) is no way out (`night.window_exits`), for the exit and
  `_other_exit` alike.
  Ruling P26-J (`window_stall`, `WINDOW_STALL`): the window act is stall-read as the walk is (WINDOW_STALL_S,
  `_stall_limit`), a stalled one refused `stalled`; a first `interrupted` end is sent once more (`_window_ended`).
  Survival 25 (ruling P29-H', the `flee_held_stance` rule, Survive's `FLEE_HELD_STANCE`): a shelter step's or an
  exit's walk is heading-read on every observe once it has moved FLEE_HEAD_R, and one running at a held zombie is
  dropped with its plan, the door marked `walled` (`_held_ahead`).
  Plan 34 Task 2 (DOOR_INSIDE, the `door_inside` rule, Survive's `DOOR_INSIDE`; F19, `f_goals_19-20261109-060929`,
  its GUIDE § 3: the leave's plain plan's enter ended `done` 0.93 tiles off its target with the character outside the
  door's edge, line 1602's close shut the door from there with 12431 at 0.60 tiles, the bite 0.334 s later): every
  plan's enter is read on its `done` (`_at_post`, the stand plan's read until then), the close and the re-close sent
  only from a room square of the building with the door unguarded (`_close_refused`), else the plan dropped and logged
  `shelter_drop`. LEAVE_DOOR_RACE's side here: `door_verdicts`' `second_exit`, the Flee's `second_exit` for its pick,
  and `abort_door`.
  The switches reach the Flee as one `rules` frozenset (`FLEE_RULES`, each on unless Survive's switch for it is off:
  `threat.Threat._flee_rules`), as the Fight's do (`fight.FIGHT_RULES`).
"""
import math
import time

from agent.base.planner.policies import (AHEAD_CONE, AHEAD_R, DANGER_R, DISENGAGE_R, DOOR_CLEAR_R, DOOR_WALK_S,
                                         FLEE_GAIT, FLEE_HEAD_R, FLEE_S, NEAR_R, PREEMPTED, SHELTER_FLEE_R, STEER_PROBE,
                                         STEER_TURNS, STEP_PROBE, STUCK_MOVE, STUCK_NEAR_R, STUCK_SKIP_DEG,
                                         WALK_STALL_S, WIDE_TURNS, WINDOW_STALL_S, Policy, _night, _rotate,
                                         away_vector, centre,
                                         clear_heading, exit_plan, in_building, in_corridor, line_to, on_floor, on_post,
                                         on_room,
                                         running, stand_post, target_id_ok, zdist)
from agent.base.planner.windows import note_window_end, window_cmd
from agent.base.pza1 import Climb, Interact, Steer, Stop, WalkTo
from agent.base.world import me_floor, me_xy

__all__ = ["Flee", "FLEE_RULES"]

FLEE_RULES = ("door_walk", "window_exit", "stand_second_exit", "window_inner", "window_stall",
              "flee_held_stance", "door_inside")   # the Flee's rules of survival iterations 13, 17, 18 and 23 (P25-E;
                     # P26-A, P26-B; P26-I, P26-J; P29-H') and Plan 34 Task 2 (DOOR_INSIDE), each Survive's switch
                     # lower-cased and on in `rules` unless it is off


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
        self.gait = FLEE_GAIT    # Survive sets it each tick: the gait of every leg and walk (P25-C: `walk` under the
                                 # endurance hold with no zombie within DANGER_R)
        self.rules = frozenset(FLEE_RULES)   # Survive sets it each tick: the FLEE_RULES its switches leave on
        self.door_walk = None    # this observe: {stall, end} when a stand's walk stalled (P25-E), else None
        self.walking_out = None  # the doorway stand's end this Flee walks out on (P25-W: `walk_out`), else None
        self._walk_from = None   # (Action, (x, y) at its send) of the last shelter step's or exit's walk (P29-H')
        self.held_cut = None     # {target, heading, bearing, d} of the walk `_held_ahead` cut, till Survive takes it
        self.second_exit = None  # Survive sets it each tick: True on the leave's ticks under LEAVE_DOOR_RACE, so the
                                 # pick reads `one_exit` as the leave's leg did (`door_verdicts`), else None
        self._shelter_note = None  # DOOR_INSIDE: the dropped plan's {shelter, step, ...}, till the choose logs it

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

    def walk_out(self, end):
        """Ruling P25-W: the doorway stand ended `end` under a group (`wound`, `drag`, `inside`, and `crowd` unless
        nobody is inside and the door square is clear, which closes: P26-K2) walks out of the building, never the
        close: the stand's plan dropped (`picked` kept, so no other shelter this episode) and the
        adoption spent (`adopted`: the adopted building's re-close would be the close again), so the next choose takes
        `exit_plan` on a room square (a door, an opening or a window (P26-A) out, at FLEE_GAIT), else the trapped
        hold; off a room square, the steer. `walking_out` keeps `end` while the exit runs (`Survive._doorway`: ahead of
        every row, as the close ran) and is cleared when that exit ends or none is found (`_end_exit`, `choose`)."""
        self.plan = None
        self.adopted = True
        self.walking_out = end

    def abort_door(self):
        """Plan 34 Task 2 (LEAVE_DOOR_RACE, `group.ThreatGroup._leave_leg`): the leave's door plan dropped before its
        close with a standing zombie within DOOR_ABORT_R, for the episode (`picked` kept, never shunned); its step still
        running is dropped with it (`_dropped`, `ended` "abort"), so the leg re-read on the same line is not held."""
        if self.busy() and self.last is self._step:
            self._dropped, self._read, self.ended = self.last, self.last, "abort"
        self._drop(False)

    def stand_exit_running(self):
        """The stand's way out (P25-W, `walk_out`) is running: its exit not yet ended, refused or walked out of."""
        return self.walking_out is not None and self.exit is not None

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
        self.door_walk = None
        if self._leg is not None and running(self.actions, self._leg[0]):
            self._leg_anchor, self._leg_still = self._still_for(self._leg_anchor)
            self._cut_leg()
        self._held_ahead()   # P29-H': a walk heading at a held zombie dropped
        a = self._step
        if a is None or a is self._read or self.plan is None:
            return
        if not self.actions.done(a):
            still = self._step_still(a)
            stalled = self._stalled(still)
            if "door_walk" in self.rules and self.plan.get("stand") and a.type == "walkTo" and still is not None:
                if stalled or still >= DOOR_WALK_S:
                    self._door_stall(a, still)   # P25-E: the stand's walk re-routes once, then drops
                return
            if stalled:
                self._dropped, self._read, self.ended = a, a, "stalled"
                self._drop(False)   # this episode only (`picked` stays): the steer follows at once
            return
        self._read = a
        self.ended = _night().shelter_ended(self.plan, a)
        if self.ended not in ("advance", "resend", "passed"):
            self._drop(a.state == "failed" and a.reason in _night().SHUN_REASONS)
        elif self.plan["step"] == "close" and (self.plan.get("stand")   # P24-AO: the stand's enter ended
                                               or ("door_inside" in self.rules and self.ended == "advance")):
            self._at_post()   # Plan 34 Task 2 (DOOR_INSIDE): every plan's enter read on its `done`

    def _at_post(self):
        """The enter ended; read where it left the player (P24-AO, Task 32 fix 1, the review's blocker, for the stand
        plan; Plan 34 Task 2, DOOR_INSIDE, the Flee's `door_inside` rule, for every plan: F19's plain plan's enter
        ended `done` 0.93 tiles off its target with the character outside, east of the door's edge, and the close shut
        the door from there, the bite 0.334 s later). On a room square of the plan's building (`on_post`) the stand
        starts (`stand`, `stood`, `quiet`) and the plain plan goes on to its close; else the enter is walked again
        (`ended` "outside", a retry: STEP_RETRIES, as Night's own `outside` read), under `door_inside` to the stand's
        post square (`enter_to`, `_enter_to`: a walk ending within the Lua's DONE_R of it ends past the door's edge);
        once the retries are spent the stand is given up for the close (as before) and the plain plan is dropped
        (`shelter_drop` {step "enter", ended "outside", retries})."""
        plan = self.plan
        if on_post(self.world, plan["building"]):
            if plan.get("stand"):
                plan.update(step="stand", stood=True, quiet=self.clock())
            return
        plan["retries"] += 1
        self.ended = "outside"
        if plan["retries"] < _night().STEP_RETRIES:
            plan["step"] = "enter"
            if "door_inside" in self.rules:
                plan["enter_to"] = self._enter_to()
        elif plan.get("stand"):
            plan["stand"] = False
        else:
            self._drop_noted({"step": "enter", "ended": "outside", "retries": plan["retries"]})

    def _enter_to(self):
        """DOOR_INSIDE's enter target after an enter that ended outside: the stand's post square of the plan's door
        (`stand_post`, the room square one on from the threshold), else the plan's `inside`."""
        way = self.world.door_way(self.door())
        post = None if way is None else stand_post(self.world, way, self.plan["building"], self.trans)
        return post if post is not None else self.plan["inside"]

    def _drop_noted(self, note):
        """DOOR_INSIDE: drop the plan for the episode (never shunned), `note` ({step, ended | refused, ...}) kept as
        the next choose's `shelter_drop` with the building (`choose` merges it into whatever its why reads); the first
        of a choose's drops is kept (a close refused inside, then the adopted building's re-close refused, logs the
        close)."""
        if self._shelter_note is None:
            self._shelter_note = dict({"shelter": self.plan["building"]}, **note)
        self._drop(False)

    def _door_guarded(self, door):
        """A known zombie stands within DOOR_CLEAR_R of the door square's centre (concern 4), or on a square no farther
        from the door square than the player's (fix round 3, F2: the Lua's close walks the player to the door, so never
        toward a zombie nearer it): the close's and the re-close's guard (Plan 34 Task 2: factored out of
        `_shelter`)."""
        sq = _night().player_square(self.world)
        mine = math.hypot(sq[0] - door[0], sq[1] - door[1])   # square to square, as each zombie's below
        return any(math.hypot(z["x"] - door[0] - 0.5, z["y"] - door[1] - 0.5) < DOOR_CLEAR_R
                   or math.hypot(math.floor(z["x"]) - door[0], math.floor(z["y"]) - door[1]) <= mine
                   for z in self._known())

    def _close_refused(self, reclose=False):
        """DOOR_INSIDE (the `door_inside` rule): why the plan's close may not be sent now, else None: "outside" off the
        building's room squares (`on_post`: F19's close from outside the door's edge), "guarded" with the door guarded
        (`_door_guarded`), except for a doorway stand's own close step (`stood`, not a `reclose`: P24-AO's stand ends
        into the close from its post with the zombie it fought at the door, by design; `test_survive_p`'s and
        `test_survive_v`'s ends)."""
        if "door_inside" not in self.rules:
            return None
        if not on_post(self.world, self.plan["building"]):
            return "outside"
        exempt = not reclose and self.plan.get("stood")
        return "guarded" if not exempt and self._door_guarded(self.door()) else None

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
        far = self._far(self.world.zombies.values())
        ahead = {id(z) for z in self._ahead(leg[2], [z for _, z in far])}
        new = sorted((zid for zid, z in far if id(z) in ahead and zid not in leg[3]), key=repr)
        if new:
            self._dropped, self._cut = leg[0], new

    def _held_ahead(self):
        """Ruling P29-H' (`flee_held_stance`; F13, `f_goals_14-20261105-021722`, fight 2: the `held` flee's walk a140 to
        building 2's door 19.1 tiles west ran east-south-east, the engine's path heading 20.7 degrees for the east gate,
        and 28222 came from 6.198 tiles at the send to 0.568 four lines later, where the walk corner's attack took it;
        lines 412 and 413 read no flee reason and were held only by `_kept_flee`'s `flip`; the controller's ruling,
        `fight2-flee-read.md`): while a shelter step's or an exit's walk runs (`_walk_from`), its observed heading (the
        character's displacement since the send, read once it reaches FLEE_HEAD_R: a shorter move, the turn-in, is not
        read) is passed to `_ahead` (AHEAD_R, AHEAD_CONE, the CORRIDOR_R tube) over the held zombies (`_threats`, this
        tick's held list, the fallen left out: fix 1, review-t2 m1) beyond NEAR_R within DISENGAGE_R (`_far`); one
        ahead drops the walk (`_dropped`, so `busy` and the `flip` guard keep nothing) with its plan for the episode,
        as P23-AM 2's stall drop does (`picked` kept, never shunned), the plan's door marked
        `walled` from outside (`World.mark_door`: the next episode's pick leaves it out for DOOR_RETRY_MIN), or the exit
        refused and its door (an opening's outside square) marked `walled` from inside, which `policies.exit_plan`
        refuses for DOOR_RETRY_MIN (fix 1, review-t2 M2: the refusal lived in this Flee's `refused` alone, so E2's
        re-recorded line 149, the next episode's new Flee, sent exit 3's cut walk again at a run, the fight, flee, cut
        loop of `fight2-flee-read.md` section 4); kept in `held_cut` {target, heading, bearing, d} (degrees, 0 east,
        south positive; the nearest ahead), which Survive logs `flee_held_stance`. The hysteresis's fight then meets
        the zombie in the stance. On F13 it reads at line 412: the heading 14.9 degrees, 28222 5.290 tiles off on 8.3.
        Cost if wrong: one tick run toward the zombie before the read; a walk whose path would have bent past a held
        zombie beyond reach given up; a cut exit left out of every way out for DOOR_RETRY_MIN (E2's exit 3 at line
        148: its later `pair` flees took no way out by it)."""
        w = self._walk_from
        if "flee_held_stance" not in self.rules or w is None:
            return
        a, start = w
        if a is self._dropped or not running(self.actions, a) or (a is not self._step and a is not self._exit_a):
            return
        mx, my = me_xy(self.world)
        dx, dy = mx - start[0], my - start[1]
        dd = math.hypot(dx, dy)
        if dd < FLEE_HEAD_R:
            return
        v = (dx / dd, dy / dd)
        far = self._far(z for z in self._threats() if not on_floor(z))
        ahead = {id(z) for z in self._ahead(v, [z for _, z in far])}
        hits = sorted(((zdist(self.world, z), repr(zid), zid, z) for zid, z in far if id(z) in ahead))
        if not hits:
            return
        d, _, zid, z = hits[0]
        self._dropped = a
        self.held_cut = {"target": zid, "heading": math.degrees(math.atan2(v[1], v[0])),
                         "bearing": math.degrees(math.atan2(z["y"] - my, z["x"] - mx)), "d": d}
        if a is self._step and self.plan is not None:
            self.world.mark_door(self.door(), "walled", "out")
            self._read, self.ended = a, "held_ahead"
            self._drop(False)
        elif a is self._exit_a and self.exit is not None:
            self.world.mark_door(self.exit["door"] or self.exit["outer"], "walled", "in")   # fix 1, M2: kept past it
            self._exit_read = a
            self._refuse_exit()

    def _far(self, zs):
        """(id, record) of the zombie records `zs` the World lists under a wire id, with a position, beyond NEAR_R and
        within DISENGAGE_R, in their order: the candidates `_cut_leg` (every listed zombie, G1's current records) and
        `_held_ahead` (the held ones) read `_ahead` over (fix 1, review-t2 m4: one read)."""
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        return [(ids[id(z)], z) for z in zs if target_id_ok(ids.get(id(z))) and z.get("x") is not None
                and z.get("y") is not None and NEAR_R < zdist(self.world, z) <= DISENGAGE_R]

    def take_held_cut(self):
        """P29-H': the walk `_held_ahead` cut since the last take ({target, heading, bearing, d}), else None."""
        out, self.held_cut = self.held_cut, None
        return out

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
        held threat is within DANGER_R (`_step_still`, `_stalled`). With no held threat within DANGER_R the step waits
        the Lua's stuck time (a doorway stand's walk, DOOR_WALK_S: P25-E)."""
        return self._stalled(self._step_still(a))

    def _step_still(self, a):
        """Wall seconds the running shelter step `a` has left the player within STUCK_MOVE (its anchor moved on), else
        None: not running, or an `open` or `close` at the door. An `open` or `close` walks only while the player stands
        more than one square (Chebyshev) from the door (the Lua's interact `approach`); at the door its anchor follows
        the player, the door's own action being no walk."""
        if not running(self.actions, a):
            return None
        if a.type == "interact":
            sq, door = _night().player_square(self.world), self.door()
            if sq is None or max(abs(sq[0] - door[0]), abs(sq[1] - door[1])) <= 1:
                self._step_anchor = (self.clock(), me_xy(self.world))
                return None
        self._step_anchor, still = self._still_for(self._step_anchor)
        return still

    def _stalled(self, still):
        """P23-AM 2's stall on `still` seconds (`_step_still`): WALK_STALL_S with a held threat within DANGER_R."""
        return (still is not None and still >= WALK_STALL_S
                and any(zdist(self.world, z) <= DANGER_R for z in self._threats()))

    def _door_stall(self, a, still):
        """Ruling P25-E (E11: the stand's walk toward building 2's door stood 2.101 s 11.44 tiles from it against a
        fence and was dropped, the stand never fought, #4409): a doorway stand's walk step stalled (P23-AM 2's read, or
        still for DOOR_WALK_S whatever the zombies) is re-routed once, the plan kept: through the climb of the hoppable
        edge on the line to the walk's target (`World.hop_ahead`, P24-G 4's fence tool; a build announcing `climb`;
        review-t3 finding 4: a target one square over gives the pathfinder the same fence), the walk sent again from
        the far side; with no such edge, to the centre of the target's first `World.reachable_adjacent` square (nearest
        the player; the plan's `via` for this step). A second stall, or neither, drops the plan as P23-AM 2 does
        (`ended` stalled). Logged `door_walk` {stall, end: reroute | drop, climb: the fence square when climbed};
        Survive logs a drop `doorway_left` `stall`."""
        self._dropped, self._read = a, a
        if not self.plan.get("rerouted"):
            target = (a.args.get("x"), a.args.get("y"))
            hop = self.world.hop_ahead(me_xy(self.world), target) if self.world.can("climb") else None
            if hop is not None:
                self.plan.update(rerouted=True, climb=hop)
                self.ended, self.door_walk = "rerouted", {"stall": still, "end": "reroute", "climb": [hop[0], hop[1]]}
                return
            via = self.world.reachable_adjacent(target, me_floor(self.world), self.trans)
            if via:
                self.plan.update(rerouted=True, via=(self.plan["step"], via[0]))
                self.ended, self.door_walk = "rerouted", {"stall": still, "end": "reroute"}
                return
        self.ended, self.door_walk = "stalled", {"stall": still, "end": "drop"}
        self._drop(False)

    def keep_gait(self):
        """Ruling P25-C: a running leg sent at a walk (the steer leg, or a shelter step's or an exit's walkTo: review-t3
        finding 3, every flee reason may take a shelter and `gait` is the gait of every leg and walk) while the gait
        now wanted is the run (a zombie came within DANGER_R) is dropped (`_dropped`), so the choose re-aims at a run at
        once; a run is never cut for a walk."""
        if self.gait != FLEE_GAIT or not self.busy():
            return
        last = self.last
        leg = self._leg is not None and last is self._leg[0]
        walk = last.type == "walkTo" and (last is self._step or last is self._exit_a)
        if (leg or walk) and last.args.get("gait") != FLEE_GAIT:
            self._dropped = last

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
        """An exit step's end, and a running step's progress (fix round 1, the review's G2): a walk that has left the
        player within STUCK_MOVE of where it last moved for WALK_STALL_S wall seconds, or a window way out's act for
        WINDOW_STALL_S (ruling P26-J, `_stall_limit`), is dropped while still current (`_dropped`) and read as failed.
        An open `done` goes back to the walk (`opened`); a superseded step is sent again; a walk `done` with the frame
        reading outside waits for the choose to read it out (`_exit_step`); a walk that failed, stalled or ended `done`
        with the frame still inside goes to the open when its way out is a closed door not yet opened (I2), else
        refuses that exit for the episode, as does a failed open (P23-AJ 3: the next choose takes the next way out,
        else the adoption or the trapped hold); a window step's end is `_window_ended`'s."""
        a = self._exit_a
        if a is None or a is self._exit_read or self.exit is None:
            return
        if not self.actions.done(a):
            limit = self._stall_limit(a)
            if limit is None or not running(self.actions, a):
                return
            self._exit_anchor, still = self._still_for(self._exit_anchor)
            if still < limit:
                return
            self._dropped = a
        self._exit_read = a
        e = self.exit
        if a.state == "failed" and a.reason == PREEMPTED:
            if a.type == "window":
                e["sent"] = False   # P26-A: superseded, the climb is sent again
            return
        if e["step"] == "window":
            self._window_ended(e, a)
        elif e["step"] == "open":
            if a.state == "done":
                e["step"], e["opened"] = "walk", True
            else:
                self._refuse_exit()
        elif a is self._dropped or a.state != "done" or on_room(self.world):
            if e["door"] is not None and not e["opened"]:
                e["step"] = "open"
            else:
                self._refuse_exit()

    def _stall_limit(self, a):
        """The wall seconds the running exit step `a` may leave the player within STUCK_MOVE of where it last moved
        before it is dropped, else None (not stall-read): WALK_STALL_S for a walk (fix round 1, G2); WINDOW_STALL_S for
        a window way out's act under the `window_stall` rule (ruling P26-J; E17's a81 held the player 12.9 s on the
        square east of the kitchen counter while the Lua's queue stood empty from the first bite, `progress` on every
        act line, until it failed `dead`); an open's `interact` is not read."""
        if a.type == "walkTo":
            return WALK_STALL_S
        if a.type == "window" and "window_stall" in self.rules:
            return WINDOW_STALL_S
        return None

    def _window_ended(self, e, a):
        """Ruling P26-A: the end of a window way out's step `a`. The climb's (`Window`), as the goal layer's
        `_climb_ended` reads one: `done` marks the exit `climbed` (the next `_exit_step` reads the frame off the room
        squares and ends it `left`, or refuses it with the frame still on one); any other end notes the window's failure
        in the World (`windows.note_window_end`, the goal layer's own failure leg: a smash refused `locked`, a second
        `locked` or a second WINDOW_REPEAT end leaves the window dead) and refuses the exit, except a `locked` end of a
        try that was no smash (ruling P26-7c): the window is noted `locked`, its outside square is not refused and the
        exit ends, so the next `exit_plan` offers the same window with `smash` True (one episode tries the open, then
        the smash). Ruling P26-J (`window_stall`): a climb dropped for its stall (`_stall_limit`) notes the window
        `stalled` and refuses the exit, so the next choose takes the next way out or the trapped hold (its `Stop` ends
        the act still running; the `stalled` mark is a WINDOW_DEAD end, so the window stays out of the exits for
        DOOR_RETRY_MIN, ruling P26-J2); a first `interrupted` end (`windows.note_window_end` answers it so: a second
        within DOOR_RETRY_MIN reads `failed`) keeps the exit and sends the climb once more (`sent` reset), the second
        refusing it. The walk's to the window's inside square: `done` marks it `walked` (the climb goes next, the Lua's
        own walk to the near side taking it the rest of the way); a walk that failed or stalled refuses the exit, as a
        way out's failed walk with no door to open does."""
        if a.type == "window":
            if a is self._dropped:
                self.world.note_window_fail(e["window"], "stalled")   # P26-J: still running, its stall read
                self._refuse_exit()
            elif a.state == "done":
                e["climbed"] = True
            else:
                reason = note_window_end(self.world, e["window"], a)
                if reason == "locked":
                    self._end_exit()   # P26-7c: an unsmashed try refused locked, the next choose offers the smash
                elif reason == "interrupted" and "window_stall" in self.rules:
                    e["sent"] = False   # P26-J: the first interrupted climb is sent once more
                else:
                    self._refuse_exit()
        elif a is self._dropped or a.state != "done":
            self._refuse_exit()
        else:
            e["walked"] = True

    def _refuse_exit(self):
        self.refused.add(self.exit["outer"])
        self._end_exit()

    def _end_exit(self):
        """The running way out ended (walked out of, or refused): `exit` and the stand's `walking_out` cleared, so a
        later way out of this Flee (another room's, after a steer) is no stand's and never runs ahead of the corner
        and the drag guard (`stand_exit_running`; Task 14 fix 1, the review's minor 3)."""
        self.exit = None
        self.walking_out = None

    def _pick(self, ts):
        """The shelter plan to run (ruling P23-AG and its fix rounds), else None: never from a room square (P23-AJ
        3: inside, the flee walks out first, `exit_plan`); else, of the doors `door_verdicts` reads `ok`, the nearest
        approach square first, ties by the building, then the door; the plan `night.shelter_plan(..., door=)` kept to
        that door."""
        if on_room(self.world):
            return None
        ok = [(rank, b, door) for rank, b, door, verdict in self.door_verdicts(ts, self.second_exit) if verdict == "ok"]
        if not ok:
            return None
        _, b, door = min(ok)
        return _night().shelter_plan(self.world, b, door=door)

    def door_verdicts(self, ts, second_exit=None):
        """The pick's reads of each door (Plan 24 Task 36: split out of `_pick` so that ruling P24-AX's log reads the
        same doors, `Survive._doorway_pick`): `[(rank, building, door, verdict)]` for each exterior door of a building
        not shunned (`night.shunned_now`) nor walked out of this episode (`left`) whose `night.approach_square` lies
        within SHELTER_FLEE_R of the player, `rank` (its distance, the building's repr, the door); `verdict` "locked"
        when the map reads it locked or barricaded, "taken" when a known zombie stands on one of the building's squares
        (M4), in the door's corridor (`in_corridor`, I1 and M3) or nearer its approach square than to the player (a
        held threat of `ts`), "one_exit" (ruling P26-B, `stand_second_exit`: E16's stand in a shed whose one door the
        group came through, its `inside` end reading no way out) when the pick is a doorway stand's (`stand_ok`) and
        the door's building has no other way out on the door's floor (`_other_exit`), else "ok". Plan 34 Task 2
        (LEAVE_DOOR_RACE): `second_exit` True reads "one_exit" whatever the pick is (the leave's door, a plain plan
        when more than DOOR_STAND_N stand), False never; None the stand's rule above."""
        if second_exit is None:
            second_exit = self.stand_ok and "stand_second_exit" in self.rules
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
                elif second_exit and not self._other_exit(b, door):
                    verdict = "one_exit"
                else:
                    verdict = "ok"
                out.append(((d, repr(b), door), b, door, verdict))
        return out

    def _other_exit(self, building, door):
        """Ruling P26-B: `building` has a way out on `door`'s floor besides `door` (`night.exits`, its windows under
        the `window_exit` rule): another closed exterior door, an opening that is not the step through `door` itself
        (`World.door_way`: an open door's step is an opening), or a window (one whose inside square can be stood on,
        under the `window_inner` rule: ruling P26-I)."""
        way = self.world.door_way(door)
        return any(e["door"] != door and (e["inner"], e["outer"]) != way
                   for e in _night().exits(self.world, building, door[2], *self._window_rules()))

    def _window_rules(self):
        """`(windows, walkable)`, the `window_exit` and `window_inner` rules as `night.exits` and
        `policies.exit_plan` take them (P26-A, P26-I)."""
        return "window_exit" in self.rules, "window_inner" in self.rules

    def _shelter(self, ts):
        """The plan's next step (its walks at FLEE_GAIT); once done inside, a hold while every threat reads
        line-blocked, or while the door reads closed and no threat's line reads clear (an unknown line holds: fix
        round 2, concern 2); else one re-sent close of a door that reads open (again after each close that ended
        done), unless a known zombie stands within DOOR_CLEAR_R of the door (concern 4) or the player's square is no
        nearer the door square than every known zombie (fix round 3, F2: the Lua's close walks the player to the door,
        so never toward a zombie nearer it) (`_door_guarded`); else the plan dropped (I2). None with the plan dropped:
        the steer follows. Plan 34 Task 2 (DOOR_INSIDE, the `door_inside` rule; F19's line 1602 closed the door with the
        character outside its edge, 12431 at 0.60 tiles): the close step and the re-close are sent only from a room
        square of the plan's building with the door not guarded (`_close_refused`), else the plan is dropped, logged
        `shelter_drop` {step "close" | "reclose", refused "outside" | "guarded"}; a step re-sent after an enter that
        ended outside logs its `retries`."""
        N = _night()
        b = self.plan["building"]
        if self.plan["step"] == "stand":   # P24-AO: the stand is Survive's Doorway fight; the Flee holds its plan
            self.why = {"shelter": b, "step": "stand"}
            return None
        hop = self.plan.get("climb")
        if hop is not None:   # P25-E: the stalled walk's re-route through the fence on its line; sent once
            self._chosen = "climb"
            self.why = {"shelter": b, "step": self.plan["step"], "ended": self.ended, "climb": [hop[0], hop[1]]}
            return Climb(hop[0], hop[1])
        cmd, step = N.shelter_step(self.world, self.plan)
        if step == "shun":
            self._drop(True)
            return None
        if step != "done":
            refused = self._close_refused() if step == "close" else None
            if refused is not None:   # Plan 34 Task 2 (DOOR_INSIDE): the close only from inside, the door unguarded
                self._drop_noted({"step": "close", "refused": refused})
                return None
            self._chosen = "step"
            self.why = {"shelter": b, "step": step, "ended": self.ended}
            if self.ended == "outside":
                self.why["retries"] = self.plan["retries"]
            via = self.plan.get("via")
            if cmd.TYPE == "walkTo" and via is not None and via[0] == step:   # P25-E: the re-route of a stalled walk
                self.why["via"] = [via[1][0], via[1][1]]
                return WalkTo(*centre(via[1]), self.gait)
            return cmd if cmd.TYPE != "walkTo" else WalkTo(cmd.x, cmd.y, self.gait)
        if not on_room(self.world):
            self._drop(False)   # pushed out after the close: no shelter this episode
            return None
        door = self.door()
        rec = (self.world.map.get(door) or {}).get("door")
        if self.hold_ok and self.shelter_holds(ts):
            self.why = {"shelter": b, "step": "done"}
            return None
        failed = self._close is not None and self.actions.done(self._close) and self._close.state != "done"
        refused = (self._close_refused(reclose=True) if "door_inside" in self.rules
                   else "guarded" if self._door_guarded(door) else None)
        if rec is not None and rec.get("open") and not failed and refused is None:
            self._chosen = "close"
            self.why = {"shelter": b, "step": "reclose"}
            return Interact(door[0], door[1], "close")
        if refused is not None and "door_inside" in self.rules:
            self._drop_noted({"step": "reclose", "refused": refused})
        else:
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
            self._end_exit()
            return None
        if e["step"] == "window":
            return self._window_step(e)
        if e["step"] == "open" and ((self.world.map.get(e["door"]) or {}).get("door") or {}).get("open"):
            e["step"], e["opened"] = "walk", True
        self._chosen = "exit"
        self.why = {"exit": e["building"], "outer": list(e["outer"]), "door": list(e["door"]) if e["door"] else None,
                    "step": e["step"], "shelter": None, "refused": sorted(map(list, self.refused))}
        if e["step"] == "open":
            return Interact(e["door"][0], e["door"][1], "open")
        return WalkTo(*centre(e["target"]), self.gait)   # P24-A (f)'s group exit, at a run since P24-O

    def _window_step(self, e):
        """Ruling P26-A, a window way out's next command (`_exit_step`, the player on a room square): a climb that ended
        `done` with the frame still on a room square refuses the exit (None: the next way out or the trapped hold);
        else the walk at the flee's gait to the centre of the window's inside square (`inner`) while the player stands
        off it and no walk there has ended `done`; then `Window(x, y, smash)` once (`sent`, the Lua's climb-through
        after its own walk to the near side: the open first, or the smash for a locked one); None while it runs. Logged
        {exit, outer, window: [x, y], smash, step "window", shelter None, refused}."""
        if e.get("climbed"):
            self._refuse_exit()
            return None
        x, y = e["window"][0], e["window"][1]
        self.why = {"exit": e["building"], "outer": list(e["outer"]), "window": [x, y], "smash": e["smash"],
                    "step": "window", "shelter": None, "refused": sorted(map(list, self.refused))}
        if not e.get("walked") and _night().player_square(self.world) != e["inner"]:
            self._chosen = "exit"
            return WalkTo(*centre(e["inner"]), self.gait)
        if e["sent"]:
            return None
        self._chosen = "exit"
        return window_cmd(self.world, e["window"], e["smash"])   # Plan 32 Task 6: clear on a window reading glass

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
        one, walked at a run (P24-O), else the adoption, else the trapped hold. A plan DOOR_INSIDE dropped since the
        last choose (`_drop_noted`) is logged on this one's why as `shelter_drop`."""
        cmd = self._choose()
        note, self._shelter_note = self._shelter_note, None
        if note is not None:
            self.why = dict(self.why or {}, shelter_drop=note)
        return cmd

    def _choose(self):
        self._chosen = None
        if self.exit is None and not on_room(self.world):
            self.walking_out = None   # the stand's end read off a room square: the steer is the way out (`walk_out`)
        ts = self._threats()
        if not ts:
            self.why = {"centroid": None, "shelter": None}
            return None
        if self.steer_now and not on_room(self.world):
            return self._steer(ts)
        if self.exit is not None:
            cmd = self._exit_step()
            if cmd is not None or self.exit is not None:   # P26-A: a window's climb sent and running holds
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
            self.exit = exit_plan(self.world, ts, self.refused, self.trans, *self._window_rules())
            if self.exit is not None:
                return self._exit_step()
            self.walking_out = None   # the stand's way out found none: the trapped hold is no running exit
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
        return Steer(heading[0], heading[1], FLEE_S, self.gait)   # P24-O: a run, never a sprint (P25-C: a walk)

    def sent(self, cmd, action):
        if cmd.TYPE == "walkTo" and self._chosen in ("step", "exit"):
            self._walk_from = (action, me_xy(self.world))   # P29-H': the walk's heading read from here
        if self._chosen == "step":
            self._step, self._step_anchor = action, (self.clock(), me_xy(self.world))
        elif self._chosen == "close":
            self._close = action
        elif self._chosen == "climb":
            self.plan["climb"] = None   # sent: the step's walk follows the climb's end
        elif self._chosen == "exit":
            self._exit_a, self._exit_anchor = action, (self.clock(), me_xy(self.world))
            if cmd.TYPE == "window":
                self.exit["sent"] = True   # P26-A: the climb goes once
        elif cmd.TYPE == "steer":
            mx, my = me_xy(self.world)
            self._leg = (action, (mx, my), (cmd.vx, cmd.vy), self._aimed)
            self._leg_anchor, self._leg_still = (self.clock(), (mx, my)), 0.0
        self._chosen = None
