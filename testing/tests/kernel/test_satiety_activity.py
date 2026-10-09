"""The activity oracle (Plan 11c Task 4b; spec § 5c; ruling 11c-29): published exercise protocols replayed through the
real kernels -- structure D's stomach, meal pool and hunger function (as test_satiety_meal_studies.py runs them) with
the acute suppression term (K.satiety.exerciseSuppression, acuteFactor) and the energy state built by
K.energy.activityState from a trailing-24 h balance and the exercise lag (K.energy.exerciseLag) -- one step a game
minute. Displayed hunger is min(0.69, hungerTarget(sated(F, post(P)), es) x circadian(h)) x acuteFactor(S).

The mappings (each a labelled assumption or inference, not a row):
- VAS to HUNGER, request-anchored (ruling 11c-31, an ASSUMPTION): a pre-meal 65 mm reads as the request level 0.25,
  so 1 mm = 0.25 / 65 of HUNGER (260 mm per unit).
- An effect size to mm: the between-trial SD of appetite is read off S1303's main effect (Douglas 2017: 95 % CI -3.1
  to -0.5 mm, ES 0.07): 1.8 / 0.07 = 25.7 mm (an INFERENCE). An acute replay's ES = the suppression in HUNGER at the
  request level (0.25 x ACUTE_MAX x S) in mm over 25.7.
- "Gone" is an ES below 0.2, Cohen's small effect (a labelled threshold).
- Compensation (S1318) is read as the share of the exercise deficit the lag lets into the energy state, mean over
  days 3-16 (the brief's definition). A closed loop eats back that share only at a high intake gain, so the intake
  compensation is at most this share (named in the report).
- Energy enters the balance at the eat and the expenditure at the minute (no absorption lag); fat depletion 0 and
  glycogen full (g = 1) in every replay.

The protocols' clock: Douglas 2017's 0.5, 1.0 and 1.5 h are hours of the trial, whose bout ran 0-1 h (S1303), so
1.5 h is 30 min after the bout. The brief's framing (45 min at 70 % read 0.5-1.5 h after the bout) is reported, not
asserted: under the rows' clock the suppression is gone by about 1.5 h after the bout (S1305).

Karl 2021 (S1325) is a test the model may fail (spec § 5c): its readings are pinned. The kernel bypasses the exercise
lag on a linear ramp of the 24 h total deficit between EX_BYPASS_LO and EX_BYPASS_HI of the 24 h expenditure (ruling
11c-32 as amended): with the work vigorous both arms pass (DEF +20.4 % against +26 %); with heavy work the model does
not class as vigorous, DEF overshoots (+62.9 %), a NON-REPRODUCTION pinned as such. King 2011 is also replayed at
steady state (the two prior days carrying the same meals), where a 25 % step in place of the ramp raises the exercise
arm by more than the band, which is why the bypass is a ramp (S1312, S1318).

Accepted only after the mutation pass (CLAUDE.md § 6): ACUTE_MAX, ACUTE_HALF_LIFE_H and EX_LAG_TAU_D at x2 and x0.5
each fail a replay here. Every test takes only `host`; no test uses `parametrize`.
"""
import math

from .test_satiety_meal_studies import H_REQ, mixed

MM_PER_HUNGER = 65.0 / H_REQ          # ruling 11c-31's request-anchored mapping (an assumption)
SD_MM = 1.8 / 0.07                    # S1303's main effect, CI midpoint over ES (an inference): 25.7 mm
ES_LO, ES_HI = 0.60, 1.47             # S1303 (>= 0.60 at 0.5-1.5 h) and S1306 (0.62-1.47 just after the run)
ES_GONE = 0.2                         # Cohen's small effect: below it the suppression is gone (a labelled threshold)
TOL = 1.5                             # the brief's tolerance on Whybrow's 30 %
KCAL_PER_KJ = 1 / 4.184

# One replay of a protocol: meals[m] lists the minute's eats; vig[m] the vigorous kind or nil; ex[m] the minute's
# exercise kcal (beside the steady non-exercise expenditure ee kcal a minute); the trailing 24 h starts as a balanced
# day (intake = expenditure = ee0 a minute, no exercise). mode: "lag" (activityState with the 24 h expenditure, so the
# kernel's ramp), "nobypass" (activityState without it: the lag alone), "raw" (today's state of eb24h, the activity
# billed at once) or "step" (the lag alone, bypassed whole when eb24h is a deficit of at least 25 % of the 24 h
# expenditure: a test-local variant ruling 11c-32 rejected). The coverage hook is off (the kernels' own tests cover
# every line).
REPLAY = r"""
function(cfg)
    local K = NutritionRevamp.kernel
    local hook, mask = debug.gethook()
    debug.sethook()
    local st = K.stomach.new()
    local P = cfg.P0
    local S = 0
    local L = 0
    local ring = {}
    local inS = 0
    local eeS = 0
    local exS = 0
    for i = 0, 1439 do
        ring[i] = { cfg.ee0, cfg.ee0, 0 }
        inS = inS + cfg.ee0
        eeS = eeS + cfg.ee0
    end
    local hs = {}
    local es = {}
    local ss = {}
    local ls = {}
    for m = 0, cfg.minutes - 1 do
        local inMin = 0
        local list = cfg.meals[m]
        if list ~= nil then
            for i = 1, #list do
                local v = K.vector.new()
                for k, x in pairs(list[i]) do
                    v[k] = x
                end
                P = K.satiety.feed(P, v)
                K.stomach.ingest(st, v)
                inMin = inMin + v.calories
            end
        end
        local exMin = cfg.ex[m] or 0
        local eeMin = cfg.ee + exMin
        local r = ring[m % 1440]
        inS = inS - r[1] + inMin
        eeS = eeS - r[2] + eeMin
        exS = exS - r[3] + exMin
        r[1] = inMin
        r[2] = eeMin
        r[3] = exMin
        local kind = cfg.vig[m]
        S = K.satiety.exerciseSuppression(S, 1 / 60, kind ~= nil, kind)
        L = K.energy.exerciseLag(L, exMin, 1 / 60)
        K.stomach.drain(st, 1 / 60)
        P = K.satiety.decay(P, 1 / 60, K.satiety.HALF_LIFE_H, 1)
        local F = K.satiety.fill(K.stomach.satietyMass(st), K.stomach.CAPACITY_MAX_G)
        local eb = inS - eeS
        local ee24 = eeS
        if cfg.mode == "nobypass" or cfg.mode == "step" then
            ee24 = nil
        end
        local e = K.energy.activityState(eb, exS, L, 0, 1, ee24)
        if cfg.mode == "raw" then
            e = K.energy.state(eb, 0, 1)
        end
        if cfg.mode == "step" and eb <= -0.25 * eeS then
            e = K.max(e, K.energy.state(eb, 0, 1))
        end
        local c = K.satiety.circadian((cfg.h0 + (m + 1) / 60) % 24)
        local h = K.min(0.69, K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(P)), e) * c)
        hs[m + 1] = h * K.satiety.acuteFactor(S)
        es[m + 1] = e
        ss[m + 1] = S
        ls[m + 1] = K.energy.lagged(L)
    end
    debug.sethook(hook, mask)
    return hs, es, ss, ls
end
"""


def run(host, minutes, h0, meals=None, vig=None, ex=None, ee=2500.0 / 1440, ee0=None, mode="lag", P0=None):
    """Displayed hunger, energy state, suppression state and lagged deficit per minute (index i is minute i + 1)."""
    rt = host.rt
    tm = rt.table()
    for minute, items in (meals or {}).items():
        lst = rt.table()
        for i, vec in enumerate(items, 1):
            lst[i] = host.table(vec)
        tm[minute] = lst
    tv = rt.table()
    for minute, kind in (vig or {}).items():
        tv[minute] = kind
    tx = rt.table()
    for minute, kcal in (ex or {}).items():
        tx[minute] = kcal
    if P0 is None:
        P0 = host.call("satiety.seedP", H_REQ / host.call("satiety.circadian", h0 % 24), 0, 1)
    cfg = host.table({"minutes": minutes, "h0": h0, "ee": ee, "ee0": ee if ee0 is None else ee0, "mode": mode,
                      "P0": P0})
    cfg.meals = tm
    cfg.vig = tv
    cfg.ex = tx
    hs, es, ss, ls = rt.eval(REPLAY)(cfg)
    r = range(1, minutes + 1)
    return [hs[i] for i in r], [es[i] for i in r], [ss[i] for i in r], [ls[i] for i in r]


def bout(start, minutes, kind, kcal):
    """A bout: `minutes` vigorous minutes of `kind` from `start`, spending `kcal` exercise kcal evenly."""
    vig = {m: kind for m in range(start, start + minutes)}
    ex = {m: kcal / minutes for m in range(start, start + minutes)}
    return vig, ex


def mean(xs):
    return sum(xs) / len(xs)


def es_of(host, S):
    """The acute ES of a suppression state S at the request level, under the stated mappings."""
    return H_REQ * host.K.satiety.ACUTE_MAX * S * MM_PER_HUNGER / SD_MM


# --- the readings, shared by the tests and the mutation script -------------------------------------------------------

def acute_run(host, minutes_of_bout=60, kind="aerobic"):
    """A bout from minute 0 (no meals, no energy): the suppression state per minute over 4 h."""
    vig, _ = bout(0, minutes_of_bout, kind, 0.0)
    return run(host, 240, 8.0, vig=vig)[2]


def douglas_goltz(host):
    """S1303 (Douglas 2017: 60 min at 59 % peak VO2, trial hours 0-1; ES >= 0.60 at 0.5, 1.0 and 1.5 h) and S1306
    (Goltz 2018: 60 min at 70 %, ES 0.62-1.47 just after): the ES at trial hours 0.5, 1.0, 1.5, 2.0 and 2.5."""
    ss = acute_run(host)
    return {h: es_of(host, ss[int(h * 60) - 1]) for h in (0.5, 1.0, 1.5, 2.0, 2.5)}


def king_2011(host):
    """S1312 (King 2011): equal deficits, 4715 kJ by a 90 min run at the start of a 9 h trial (from 08:00) and 4820 kJ
    by food restriction; test meals at 2 and 4.75 h (an ASSUMED 800 kcal each for control and exercise, the
    restriction arm's each cut by half the deficit). Mean displayed hunger over the 8 h to the buffet ("all") and from
    3 h on ("late": 1.5 h after the bout, the acute term gone), per arm, and the exercise arm under today's form
    (the activity billed at once, "raw")."""
    run_kcal = 4715.0 * KCAL_PER_KJ
    cut = 4820.0 * KCAL_PER_KJ / 2
    full = {120: [mixed(800.0)], 285: [mixed(800.0)]}
    less = {120: [mixed(800.0 - cut)], 285: [mixed(800.0 - cut)]}
    vig, ex = bout(0, 90, "aerobic", run_kcal)
    arms = {
        "control": run(host, 480, 8.0, meals=full)[0],
        "exercise": run(host, 480, 8.0, meals=full, vig=vig, ex=ex)[0],
        "restriction": run(host, 480, 8.0, meals=less)[0],
        "raw": run(host, 480, 8.0, meals=full, vig=vig, ex=ex, mode="raw")[0],
    }
    return {n: {"all": mean(hs), "late": mean(hs[180:])} for n, hs in arms.items()}


def king_2011_steady(host):
    """S1312 at steady state: the same three meals (833 kcal at 10:00, 12:45 and 19:00) on the two prior days, so the
    trailing 24 h is a balanced eating day when the trial starts at 08:00 of day 3; the restriction arm cuts the
    trial's two test meals by half the deficit each. Mean displayed hunger from 3 h of the trial on ("late"), per arm,
    the exercise arm also under a 25 % step bypass ("step") and with no bypass ("nobypass")."""
    run_kcal = 4715.0 * KCAL_PER_KJ
    cut = 4820.0 * KCAL_PER_KJ / 2
    day = 1440

    def meals(trim):
        out = {}
        for d in range(3):
            for hh in (2, 4.75, 11):
                kc = 2500.0 / 3 - (trim if d == 2 and hh in (2, 4.75) else 0.0)
                out[d * day + int(hh * 60)] = [mixed(kc)]
        return out

    vig, ex = bout(2 * day, 90, "aerobic", run_kcal)
    full, less = meals(0.0), meals(cut)

    def late(hs):
        return mean(hs[2 * day + 180:2 * day + 480])

    return {
        "control": late(run(host, 3 * day + 480, 8.0, meals=full)[0]),
        "restriction": late(run(host, 3 * day + 480, 8.0, meals=less)[0]),
        "exercise": late(run(host, 3 * day + 480, 8.0, meals=full, vig=vig, ex=ex)[0]),
        "step": late(run(host, 3 * day + 480, 8.0, meals=full, vig=vig, ex=ex, mode="step")[0]),
        "nobypass": late(run(host, 3 * day + 480, 8.0, meals=full, vig=vig, ex=ex, mode="nobypass")[0]),
    }


def king_2010(host):
    """S1302 (King 2010): 60 min of brisk walking at 7.0 km/h from 08:00, a net 2008 kJ, no suppression (kind walk);
    buffet meals at 1.75 and 5.25 h (an ASSUMED 650 kcal each in both arms); mean hunger over 8 h, walk minus control."""
    vig, ex = bout(0, 60, "walk", 2008.0 * KCAL_PER_KJ)
    meals = {105: [mixed(650.0)], 315: [mixed(650.0)]}
    walk = mean(run(host, 480, 8.0, meals=meals, vig=vig, ex=ex)[0])
    control = mean(run(host, 480, 8.0, meals=meals)[0])
    return walk - control


def whybrow(host, mj_per_day=3.5):
    """S1318 (Whybrow 2008): exercise every day from day 1 (an ASSUMED single 60 min bout at 10:00 of mj_per_day; the
    study's high arm 3.0-4.0 MJ/d, moderate 1.5-2.0); the mean share of the daily exercise deficit the lag lets into
    the energy state over days 3-16, and the share at the end of day 1."""
    kcal = mj_per_day * 1000 * KCAL_PER_KJ
    L = 0.0
    shares = []
    day1 = None
    for m in range(16 * 1440):
        exm = kcal / 60 if 120 <= m % 1440 < 180 else 0.0
        L = host.call("energy.exerciseLag", L, exm, 1 / 60)
        if m >= 2 * 1440:
            shares.append(host.call("energy.lagged", L) / kcal)
        if m == 1440 - 1:
            day1 = host.call("energy.lagged", L) / kcal
    return mean(shares), day1


# Karl 2021 (S1325): 72 h of strenuous work, about 9.6 MJ a day of activity expenditure, after a sedentary balanced
# day; BAL at +18 % of expenditure, DEF at -43 %. ASSUMED: REST expenditure 2700 kcal a day, so work days spend 2700 +
# 2294; the activity as 8 h of work a day (08:00-12:00, 13:00-17:00), vigorous aerobic or not vigorous at all (two
# readings); three equal meals at 07:00, 12:00 and 18:00; sleep 02:00-06:00 (limited); hunger averaged awake.
KARL_REST = 2700.0
KARL_PAEE = 9.6e3 * KCAL_PER_KJ


def karl_arm(host, intake_per_day, work, kind="aerobic", mode="lag"):
    h0 = 6.0
    meals = {}
    for d in range(3):
        for hh in (7, 12, 18):
            meals[d * 1440 + (hh - 6) * 60] = [mixed(intake_per_day / 3, water=300.0 * intake_per_day / 1950)]
    vig, ex = {}, {}
    if work:
        per = KARL_PAEE / 480
        for d in range(3):
            for hh in (8, 9, 10, 11, 13, 14, 15, 16):
                for k in range(60):
                    m = d * 1440 + (hh - 6) * 60 + k
                    ex[m] = per
                    if kind is not None:
                        vig[m] = kind
    hs = run(host, 3 * 1440, h0, meals=meals, vig=vig, ex=ex, ee=KARL_REST / 1440, mode=mode)[0]
    awake = [x for m, x in enumerate(hs) if not (20 <= (m // 60) % 24 < 24)]   # 02:00-06:00 is hours 20-24 from 06:00
    return mean(awake)


def karl(host, kind="aerobic", mode="lag"):
    """Percent change in mean awake hunger against REST for BAL and DEF."""
    work = KARL_REST + KARL_PAEE
    rest = karl_arm(host, KARL_REST, False)
    bal = karl_arm(host, 1.18 * work, True, kind, mode)
    dfc = karl_arm(host, 0.57 * work, True, kind, mode)
    return round(100 * (bal / rest - 1), 1), round(100 * (dfc / rest - 1), 1)


def karl_pass(bal, dfc):
    """Each arm passes when its sign matches the study's and it sits within 1.5x of it (-55 % and +26 %)."""
    ok_bal = bal < 0 and max(bal / -55.0, -55.0 / bal) <= 1.5
    ok_dfc = dfc > 0 and max(dfc / 26.0, 26.0 / dfc) <= 1.5
    return ok_bal, ok_dfc


# --- acute suppression (S1303, S1305, S1306, S1304) -----------------------------------------------------------------

def test_douglas_and_goltz_suppression_sits_in_the_effect_size_band(host):
    # S1303: ES >= 0.60 at trial hours 0.5, 1.0 and 1.5 (the bout ran 0-1 h); S1306: <= 1.47 just after a 60 min run
    es = douglas_goltz(host)
    for h in (0.5, 1.0, 1.5):
        assert ES_LO <= es[h] <= ES_HI, es


def test_the_suppression_is_gone_by_about_one_and_a_half_hours_after_the_bout(host):
    # S1305: appetite returns to control within 30-60 min of the bout's end; S1304: nothing 30-90 min after in that
    # pooling. Gone (ES < 0.2) at trial hour 2.5, 1.5 h after the bout, and falling all the way
    es = douglas_goltz(host)
    assert es[2.5] < ES_GONE, es
    assert es[1.0] > es[1.5] > es[2.0] > es[2.5], es


def test_resistance_swinging_suppresses_less_than_running(host):
    # S1301 (suppressed during resistance work too), S1305 (less marked): the swing state's weight
    a = acute_run(host, kind="aerobic")[59]
    r = acute_run(host, kind="resistance")[59]
    assert 0 < r < a


def test_brisk_walking_moves_hunger_by_about_zero(host):
    # S1302 (King 2010): a net 2008 kJ walk, no effect on appetite: the 8 h mean moves by under 1 mm
    d = king_2010(host)
    assert abs(d) * MM_PER_HUNGER < 1.0, d


# --- no same-day compensation (S1312, S1310, S1311) -----------------------------------------------------------------

def test_king_2011_restriction_raises_same_day_hunger_and_exercise_does_not(host):
    # S1312: equal deficits. The food-restriction arm's hunger rises above control; the exercise arm's never does: over
    # the 8 h it sits at or below control (the bout's transient suppression, S1311), and once the acute term is gone
    # (from 3 h) it stays within a small band of control (under a quarter of the restriction's rise, and under 3 mm),
    # where today's form (the activity billed at once) would raise it by more than the band
    k = king_2011(host)
    rise = k["restriction"]["late"] - k["control"]["late"]
    assert k["restriction"]["all"] - k["control"]["all"] > 0.02, k
    assert rise > 0.02, k
    assert k["exercise"]["all"] <= k["control"]["all"], k
    late = abs(k["exercise"]["late"] - k["control"]["late"])
    assert late < 0.25 * rise and late * MM_PER_HUNGER < 3.0, k
    assert k["raw"]["late"] - k["control"]["late"] > 3.0 / MM_PER_HUNGER, k


def test_the_lag_lets_in_about_nothing_the_same_day(host):
    # S1312, S1310: about 0 the same day
    _, day1 = whybrow(host)
    assert day1 < 0.05, day1


# --- compensation over days (S1318) ----------------------------------------------------------------------------------

def test_whybrow_compensation_over_days_3_to_16_is_about_30_percent(host):
    # S1318 (Whybrow 2008): about 30 % of the exercise deficit compensated over days 3-16, within 1.5x, at both doses
    for mj in (3.5, 1.75):
        share, _ = whybrow(host, mj)
        assert max(share / 0.30, 0.30 / share) <= TOL, (mj, share)


# --- heavy labour (S1325), a test the model may fail ------------------------------------------------------------------

def test_king_2011_at_steady_state_exercise_stays_with_control(host):
    # S1312 (King 2011) with the prior days eating the same meals: the exercise arm's late hunger sits within a small
    # band of control (under a quarter of the restriction's rise, and under 3 mm), where a 25 % step bypass lifts it
    # by more than the band (S1312; S1318 measured the compensating arms at 26-28 %)
    k = king_2011_steady(host)
    rise = k["restriction"] - k["control"]
    assert rise > 0.02, k
    band = abs(k["exercise"] - k["control"])
    assert band < 0.25 * rise and band * MM_PER_HUNGER < 3.0, k
    assert k["exercise"] >= k["nobypass"], k            # the ramp only ever raises the lag's share
    step = k["step"] - k["control"]
    assert step > 0.25 * rise and step * MM_PER_HUNGER >= 3.0, k


def test_karl_2021_vigorous_both_arms_pass_with_the_ramp(host):
    # S1325 (Karl 2021): hunger -55 % against REST in an 18 % surplus, +26 % at a 43 % deficit (a pass: the sign and
    # within 1.5x). With the work vigorous the ramp reads BAL -73.6 % and DEF +20.4 %; both pass. Pinned
    bal, dfc = karl(host, "aerobic")
    assert (bal, dfc) == (-73.6, 20.4)
    assert karl_pass(bal, dfc) == (True, True)
    assert 26.0 / 1.5 <= dfc <= 26.0 * 1.5


def test_karl_2021_not_vigorous_overshoots_a_pinned_non_reproduction(host):
    # The same work not classed as vigorous (heavy work the model does not class as vigorous): BAL passes (-65.8 %) and
    # DEF reads +62.9 % against +26 %, past 1.5x -- a NON-REPRODUCTION, pinned so a change is noticed
    bal, dfc = karl(host, None)
    assert (bal, dfc) == (-65.8, 62.9)
    assert karl_pass(bal, dfc) == (True, False)


def test_karl_2021_the_lag_alone_and_today_s_form_for_comparison(host):
    # the lag with no bypass (DEF fails in direction) and today's form (the activity billed at once)
    assert karl(host, "aerobic", mode="nobypass") == (-73.6, -26.5)
    assert karl(host, None, mode="nobypass") == (-65.8, -0.9)
    assert karl(host, "aerobic", mode="raw") == (-66.0, 39.7)
    assert karl(host, None, mode="raw") == (-55.1, 87.7)
    assert karl(host, "aerobic", mode="step") == (-73.6, 31.8)
    assert karl(host, None, mode="step") == (-65.8, 76.7)
