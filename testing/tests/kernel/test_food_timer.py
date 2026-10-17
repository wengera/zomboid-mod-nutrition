"""The food-timer bridge (Plan 15 Task 8; spec sections 2.3 and 2.4; jar-checks Check 1, rows #3893-#3900).

The mod owns vanilla's health-from-food timer, which alone drives the FOOD_EATEN moodle (Well Fed) and every vanilla
eat and drink refusal at its level 3. K.view.foodTimer maps the mod's state to the value: TIMER_FULL (level 3, the
refusal) at Overfull 4 whatever else holds; 0 while a drain state is active; Well Fed level 2 while sated at Overfull 2
or 3, level 1 while sated below it; else 0, sated being the meal pool M at WELL_FED_M or more. NR_Server_Writer's
W.foodTimer writes it each minute above 0, writes 0 only on the change to 0 (or on a minute an eat or a drink landed,
whose vanilla add it overwrites), writes at the first sight of each player object (a load) and pushes the body-damage
fields (mask 8) only when the band changes. The writer half is driven directly on test_writer_shape's host.
"""
import pytest

from . import test_writer_shape as WS

FULL, WF1, WF2 = 4400, 1000, 2800
WELL_FED_M = 435
HALF_LIFE_H = 0.583749          # K.satiety.MEAL_HALF_LIFE_H, read back below
UNITS_MIN = 2 * 90              # vanilla's drain a game minute at the 90-minute day (#2385, #2922)


def V(h):
    return h.K.view


def _mixed(h, kcal):
    """A mixed meal at 15/50/35 % of energy (protein, carbohydrate, fat), as a vector K.satiety.weigh reads."""
    return h.rt.table_from({"calories": kcal, "proteins": 0.15 * kcal / 4, "carbs": 0.50 * kcal / 4,
                            "lipids": 0.35 * kcal / 9})


def _well_fed_hours(h, kcal):
    """Game hours a single mixed meal of kcal keeps M at WELL_FED_M or more, cleared minute by minute (mealClear)."""
    M = h.K.satiety.weigh(_mixed(h, kcal))
    t = 0
    while M >= V(h).WELL_FED_M:
        M = h.K.satiety.mealClear(M, 1 / 60, 1)
        t += 1
    return t / 60


# --- the kernel: the mapping ------------------------------------------------------------------------------------------

def test_the_constants_sit_inside_their_bands_with_a_minutes_drain_to_spare(host):
    v = V(host)
    assert (v.TIMER_WELL_FED, v.TIMER_WELL_FED_2, v.TIMER_FULL, v.WELL_FED_M) == (WF1, WF2, FULL, WELL_FED_M)
    assert host.K.satiety.MEAL_HALF_LIFE_H == HALF_LIFE_H
    assert 0 < WF1 - UNITS_MIN and WF1 <= 1600                          # level 1 through the minute (#0511)
    assert 1600 < WF2 - UNITS_MIN and WF2 <= 3200                       # level 2
    assert 3200 < FULL - UNITS_MIN and FULL <= 4800                     # level 3, the refusal, never 4
    assert 3300 - UNITS_MIN * 34 / 60 < 3200                           # why not 3300: the drain takes it under in 34 s


@pytest.mark.parametrize("level,M,draining,want", [
    (0, 788.5, False, WF1),         # just after a 667 kcal mixed meal (788.5 weighted kcal): Well Fed
    (1, 788.5, False, WF1),         # pleasantly overfull: still level 1
    (2, 788.5, False, WF2),         # a large meal, Overfull 2: level 2
    (3, 788.5, False, WF2),         # Overfull 3: level 2
    (4, 788.5, False, FULL),        # Overfull 4: the refusal
    (4, 0.0, False, FULL),          # the refusal needs no satisfying meal (a kilogram of broccoli)
    (4, 788.5, True, FULL),         # nor is it lifted by a drain: the stomach is full, starving or not
    (0, 788.5, True, 0),            # a drain active: a starving body is not Well Fed
    (2, 788.5, True, 0),
    (0, 236.5, False, 0),           # a 200 kcal snack never reads sated
    (0, WELL_FED_M, False, WF1),    # the boundary is inclusive
    (0, WELL_FED_M - 1e-9, False, 0),
    (2, 100.0, False, 0),           # full but unsated: no Well Fed
    (0, float("nan"), False, 0),    # a NaN pool reads unsated
    (0, None, False, 0),            # so does none
])
def test_the_timer_mapping_by_state(host, level, M, draining, want):
    assert V(host).foodTimer(level, M, draining) == want


def test_a_667_kcal_meal_shows_well_fed_for_about_vanillas_can_and_a_snack_shows_none(host):
    # vanilla's whole can (3120 units, #0054) shows Well Fed 17 game minutes raw and 35 heated at the 90-minute day
    assert abs(host.K.satiety.weigh(_mixed(host, 667)) - 788.5) < 0.1
    t = _well_fed_hours(host, 667)
    assert 3120 / UNITS_MIN / 60 < t < 2 * 3120 / UNITS_MIN / 60
    assert abs(t - 0.50) <= 1 / 60 + 1e-9                               # the last sated minute counted
    assert _well_fed_hours(host, 400) <= 5 / 60                          # a small meal: a few minutes
    assert _well_fed_hours(host, 200) == 0                               # a snack: none
    assert abs(_well_fed_hours(host, 1000) - 0.85) <= 2 / 60             # a large meal: longer


@pytest.mark.parametrize("t,band", [(0, 0), (-5, 0), (1, 1), (1600, 1), (1600.5, 2), (3200, 2), (3201, 3),
                                    (4400, 3), (11000, 3)])
def test_the_band_follows_food_eatens_strict_thresholds(host, t, band):
    assert V(host).timerBand(t) == band


@pytest.mark.parametrize("grams,level", [(None, 0), (700, 0), (800, 1), (900, 2), (1000, 3), (1100, 4), (1300, 4)])
def test_the_overfull_level_of_a_record_is_the_moodles(host, grams, level):
    rec = host.rt.table()
    if grams is not None:
        st = host.K.stomach.new()
        st.buffer.water = grams
        rec.stomach = st
    assert V(host).overfullOf(rec) == level
    assert level == V(host).fullnessLevel(host.K.mirror.stomachMass(rec))


@pytest.mark.parametrize("bad", ["key nil", "key string", "buffer string"])
def test_a_malformed_stomach_reads_overfull_0(host, bad):
    # Kinetics heals a malformed buffer on its own minute; until then neither the writer nor the effects step raises
    rec = host.rt.table()
    st = host.K.stomach.new()
    st.buffer.water = 1200
    if bad == "key nil":
        st.buffer.proteins = None
    elif bad == "key string":
        st.buffer.fibre = "x"
    else:
        st.buffer = "x"
    rec.stomach = st
    assert V(host).overfullOf(rec) == 0


# --- the writer: the bridge --------------------------------------------------------------------------------------------

BODY = r"""
function(p, C)
    local bd = { timer = 0, writes = {} }
    local function count(name) C[name] = (C[name] or 0) + 1; C.n = C.n + 1 end
    bd.setHealthFromFoodTimer = function(s, v) count("timer"); s.timer = v; s.writes[#s.writes + 1] = v end
    bd.getHealthReductionFromSevereBadMoodles = function(s) count("get"); return 0.0165 end
    bd.setHealthReductionFromSevereBadMoodles = function(s, v) count("set") end
    bd.setDrunkReductionValue = function(s, v) end
    bd.getThermoregulator = function(s) return nil end
    p.getBodyDamage = function(s) return bd end
    p.bd = bd
    NR_T.pushes = {}
    sendSyncPlayerFields = function(pl, mask) count("push"); NR_T.pushes[#NR_T.pushes + 1] = mask end
    return p
end
"""


def setup(mode=1):
    h = WS.boot(mode)
    p = WS.player(h)
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval(BODY)(p, C)
    return h, p, C


def writes(p):
    return [p.bd.writes[i] for i in range(1, len(p.bd.writes) + 1)]


def pushes(h):
    t = h.rt.eval("NR_T.pushes")
    return [t[i] for i in range(1, len(t) + 1)]


def fill(h, rec, grams):
    st = h.K.stomach.new()
    st.buffer.water = grams
    rec.stomach = st


def test_the_first_sight_writes_and_a_steady_unfed_minute_calls_nothing():
    h, p, C = setup()
    rec = WS.record(h)                                  # M 6: unsated, no stomach
    WS.step(h, p, rec, 1)
    assert writes(p) == [0] and pushes(h) == [8]        # the saved timer is overwritten at first sight (a load)
    n = C.n
    for m in range(2, 12):
        WS.step(h, p, rec, m)
    assert C.n == n                                     # Rule 6: no Java call on a steady unfed minute


def test_a_sated_minute_writes_once_and_pushes_only_on_a_band_change():
    h, p, C = setup()
    rec = WS.record(h)
    rec.satiety.M = 788.5
    WS.step(h, p, rec, 1)
    assert writes(p) == [WF1] and pushes(h) == [8]
    n = C.n
    for m in range(2, 6):
        WS.step(h, p, rec, m)
    assert writes(p) == [WF1] * 5 and pushes(h) == [8]  # every minute one write (vanilla drains it), no push
    assert C.n == n + 4
    fill(h, rec, 900)                                   # Overfull 2: Well Fed level 2, a band change
    WS.step(h, p, rec, 6)
    assert writes(p)[-1] == WF2 and pushes(h) == [8, 8]
    fill(h, rec, 1100)                                  # Overfull 4: the refusal
    WS.step(h, p, rec, 7)
    assert writes(p)[-1] == FULL and pushes(h) == [8, 8, 8]
    rec.stomach = None
    rec.satiety.M = 1.0                                 # unsated and empty: 0 once, pushed, then nothing
    WS.step(h, p, rec, 8)
    assert writes(p)[-1] == 0 and pushes(h) == [8, 8, 8, 8]
    n = C.n
    WS.step(h, p, rec, 9)
    assert C.n == n


def test_the_satiety_steps_clearance_reaches_the_bridge_the_same_minute():
    # the writer reads record.satiety.M after its own satiety step; Kinetics clears M before the writer in ORDER
    h, p, C = setup()
    rec = WS.record(h)
    rec.satiety.M = WELL_FED_M
    WS.step(h, p, rec, 1)
    assert writes(p) == [WF1]
    rec.satiety.M = WELL_FED_M - 1
    WS.step(h, p, rec, 2)
    assert writes(p) == [WF1, 0]


def test_a_drain_state_turns_well_fed_off_but_never_the_refusal():
    h, p, C = setup()
    rec = WS.record(h)
    rec.satiety.M = 788.5
    rec.drain = h.rt.table_from({"active": True, "starving": False, "dehydrated": False})
    WS.step(h, p, rec, 1)
    assert writes(p) == [0]
    fill(h, rec, 1150)
    WS.step(h, p, rec, 2)
    assert writes(p) == [0, FULL]


def test_a_landed_eat_or_drink_overwrites_vanillas_add_even_at_0():
    # vanilla's eat at HUNGER 0 (#3598) and every drink (J1.1, ungated) add to the timer; that minute writes it again
    h, p, C = setup()
    rec = WS.record(h)
    WS.step(h, p, rec, 1)
    p.bd.timer = 3900                                   # a can eaten at HUNGER 0 filled vanilla's timer
    h.NR.server.intake.landed["a"] = True
    WS.step(h, p, rec, 2)
    assert writes(p) == [0, 0] and p.bd.timer == 0 and pushes(h) == [8]     # band unchanged on the mod's side
    n = C.n
    WS.step(h, p, rec, 3)
    assert C.n == n


def test_a_new_player_object_is_written_at_its_first_sight():
    # a reload restores the saved timer (saveMainFields) but not the mod's last write: the new hoist writes again
    h, p, C = setup()
    rec = WS.record(h)
    fill(h, rec, 1100)
    WS.step(h, p, rec, 1)
    assert writes(p) == [FULL]
    p2 = WS.player(h)
    C2 = h.rt.eval("{ n = 0 }")
    h.rt.eval(BODY)(p2, C2)
    rec.stomach = None
    WS.step(h, p2, rec, 2)
    assert writes(p2) == [0] and pushes(h) == [8]


def test_overlay_never_touches_the_timer():
    h, p, C = setup(mode=2)
    rec = WS.record(h)
    fill(h, rec, 1100)
    for m in range(1, 4):
        WS.step(h, p, rec, m)
    assert writes(p) == [] and (C.timer or 0) == 0 and (C.push or 0) == 0


def test_a_body_damage_without_the_setter_is_counted_and_retried():
    h = WS.boot()
    p = WS.player(h)                                    # test_writer_shape's body damage has no timer setter
    rec = WS.record(h)
    W = h.NR.server.writer
    WS.step(h, p, rec, 1)
    WS.step(h, p, rec, 2)
    assert W.timerStats.failures == 2 and W.timerStats.writes == 0


def test_a_missing_push_global_is_counted():
    h, p, C = setup()
    h.rt.execute("sendSyncPlayerFields = nil")
    rec = WS.record(h)
    WS.step(h, p, rec, 1)
    W = h.NR.server.writer
    assert writes(p) == [0] and W.timerStats.pushMissing == 1 and W.timerStats.pushes == 0


# --- the writer: the Overfull endurance ceiling -------------------------------------------------------------------------

def test_the_endurance_ceiling_holds_endurance_at_or_under_it():
    h, p, C = setup()
    rec = WS.record(h)
    rec.effects.enduranceCap = 0.73
    WS.step(h, p, rec, 1)
    assert p.st.sets.ENDURANCE == 0.73                  # read 0.9: held at the ceiling, the Endurance moodle's level 1
    p.st.sets.ENDURANCE = None
    p.st.v.ENDURANCE = 0.6                              # already under it: no write
    WS.step(h, p, rec, 2)
    assert p.st.sets.ENDURANCE is None
    rec.effects.enduranceCap = 1                        # the ceiling lifts: no write
    p.st.v.ENDURANCE = 0.9
    WS.step(h, p, rec, 3)
    assert p.st.sets.ENDURANCE is None


def test_the_ceiling_caps_the_asleep_regeneration_too():
    h, p, C = setup()
    rec = WS.record(h)
    rec.effects.enduranceCap = 0.73
    p.asleep = True
    p.st.v.ENDURANCE = 0.5
    WS.step(h, p, rec, 1)
    p.st.v.ENDURANCE = 0.9                              # vanilla regenerated past the ceiling between writes
    WS.step(h, p, rec, 2)
    assert p.st.sets.ENDURANCE == 0.73


@pytest.mark.parametrize("e,e1,cap,want", [
    (None, 0.9, 0.73, 0.73), (None, 0.5, 0.73, None), (0.8, 0.9, 0.73, 0.73), (0.6, 0.9, 0.73, 0.6),
    (None, 0.9, 1.0, None), (0.8, 0.9, 1.0, 0.8), (None, 0.9, float("nan"), None), (None, 0.73, 0.73, None),
])
def test_the_hybrid_endurance_ceiling(host, e, e1, cap, want):
    got = host.K.hybrid.endCap(e, e1, cap)
    assert got == want
