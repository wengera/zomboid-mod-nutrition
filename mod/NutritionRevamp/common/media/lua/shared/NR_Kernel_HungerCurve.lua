-- NR_Kernel_HungerCurve.lua -- the calibrated hunger writer (Plan 15 Task 6; spec section 2.1, items 3, 10a and 10b).
-- The study-fitted satiety model (NR_Kernel_Satiety.lua) yields its own hunger, h_model: the target times the circadian,
-- acute, nicotine and sleep factors, which the writer keeps on record.satiety.hModel for the study oracles. The HUNGER
-- written to the game is H = write(h_model, state): a monotone piecewise-linear curve (map) fitted so a satisfying meal
-- reads about 0 and vanilla's Peckish and Hungry return on vanilla's cadence (tools/fit_hunger_curve.py); while unfed,
-- the morning circadian dip is taken out and H never falls (the fasting bend); and a dead zone at each HUNGRY threshold
-- holds a moodle level until H is DEAD_ZONE under its threshold, so the level does not blink. K.hybrid.write caps the
-- result (K.hybrid.caps). Pure; one statement a line for the coverage gate.
local K = NutritionRevamp.kernel
K.hungerCurve = {}

-- The knots, h_model (X) to HUNGER (Y), increasing in both. Each Y from the third to the sixth is a HUNGRY threshold
-- (VANILLA #0508: above 0.15, 0.25, 0.45 and 0.70), so each X is the h_model at which that moodle level shows; the
-- second knot ends the flat foot, so a meal that takes h_model under it reads 0. Every X is a game choice (spec section
-- 10: the curve's knots), fitted by tools/fit_hunger_curve.py on the server replay (the default body, three 667 kcal
-- meals a day at 07:30, 12:30 and 18:30 with the guide's water) against vanilla's cadence (tools/vanilla_model.py: a
-- can that takes HUNGER to 0.01, and three cans a day with each meal's return to Peckish, Plan 15 Task 6c; re-fitted in
-- Task 14b on the liquid lane slowed only by drink-borne kcal), and re-fitted in Plan 16 Task 4b jointly on both server
-- sleep settings, weighted 2:1 (a game choice, spec section 6): sleep off, the default, with no daily rhythm, and sleep
-- on, asleep 23:00 to 07:00, the rhythm on the body clock a full sleep resets to 07:00; loss 0.526 against 0.565 for the
-- Task 14b knots (fit-hunger-curve-20261018); no knot sits at its search bound; each line names its reading with sleep
-- off, then with sleep on, and its x0.95 and x1.05 readings with sleep off. No curve of h_model meets vanilla's
-- three-can breakfast (Peckish 1.17 h, a can short of the night's rise) and its lunch and dinner (4.25 h, 5.00 h) at
-- once: a satisfying meal resets the meal pool, so h_model keeps no additive residual of the earlier hunger (the hunger
-- before carries only through the gut fill and the deficit drive), and with sleep on the circadian factor (S1273, peak
-- 19:50) wears dinner off first; the Peckish knot is the compromise the fit's weights choose.
K.hungerCurve.X = {
    0, -- the curve's foot: no row needed
    K.dials.get("hungerCurve.X.2"),
    K.dials.get("hungerCurve.X.3"),
    K.dials.get("hungerCurve.X.4"),
    K.dials.get("hungerCurve.X.5"),
    K.dials.get("hungerCurve.X.6"),
    1, -- the model's top: no row needed
}
K.hungerCurve.Y = {
    0, -- no row needed
    K.dials.get("hungerCurve.Y.2"),
    K.dials.get("hungerCurve.Y.3"),
    K.dials.get("hungerCurve.Y.4"),
    K.dials.get("hungerCurve.Y.5"),
    K.dials.get("hungerCurve.Y.6"),
    1, -- the stat's top (#0021): no row needed
}
-- The HUNGRY thresholds the dead zone guards, each a strict greater-than (#0507): VANILLA #0508, Y's level knots.
K.hungerCurve.THRESHOLDS = { K.hungerCurve.Y[3], K.hungerCurve.Y[4], K.hungerCurve.Y[5], K.hungerCurve.Y[6] }
K.hungerCurve.DEAD_ZONE = K.dials.get("hungerCurve.DEAD_ZONE")
K.hungerCurve.HOLD_EPS = K.dials.get("hungerCurve.HOLD_EPS")
K.hungerCurve.FED_M = K.dials.get("hungerCurve.FED_M")

-- The curve: H at h_model h, linear between the knots, held at the end knots outside them.
function K.hungerCurve.map(h)
    local X = K.hungerCurve.X
    local Y = K.hungerCurve.Y
    if h <= X[1] then
        return Y[1]
    end
    for i = 2, #X do
        if h <= X[i] then
            return Y[i - 1] + (Y[i] - Y[i - 1]) * (h - X[i - 1]) / (X[i] - X[i - 1])
        end
    end
    return Y[#Y]
end

-- The curve's inverse, the h_model a written H reads (the meal pool's seed, W.satietyMeal): on the flat foot the foot's
-- end (the least sated h_model that reads that H), linear between the knots, held at the end knots outside them.
function K.hungerCurve.inverse(H)
    local X = K.hungerCurve.X
    local Y = K.hungerCurve.Y
    for i = 2, #Y do
        if H <= Y[i] and Y[i] > Y[i - 1] then
            if H <= Y[i - 1] then
                return X[i - 1]
            end
            return X[i - 1] + (X[i] - X[i - 1]) * (H - Y[i - 1]) / (Y[i] - Y[i - 1])
        end
    end
    return X[#X]
end

-- The dead zone (item 10b): when the last H, prev, stands over a threshold and H has fallen to it or under it by less
-- than DEAD_ZONE, H is held HOLD_EPS over that threshold (never over prev), so the level steps down only past the zone.
-- A rise is never held.
function K.hungerCurve.hold(H, prev)
    local T = K.hungerCurve.THRESHOLDS
    for i = 1, #T do
        local t = T[i]
        if prev > t and H <= t and H > t - K.hungerCurve.DEAD_ZONE then
            return K.min(prev, t + K.hungerCurve.HOLD_EPS)
        end
    end
    return H
end

-- The circadian dip an unfed write takes out of h_model: the minute's factor circ when it is a positive number under 1
-- (the morning trough of the body clock, Plan 16), else 1 (no dip: the evening rise stays; with sleep off the factor is
-- 1, so there is no dip).
function K.hungerCurve.dip(circ)
    if circ ~= nil and circ > 0 and circ < 1 then
        return circ
    end
    return 1
end

-- The HUNGER to write for h_model h. state carries the last HUNGER (state.hunger, the stat as read this minute: the
-- last write unless an eat moved it), whether the character is fed (state.fed, the meal pool at FED_M or more) and the
-- minute's circadian factor (state.circ, the factor h carries). Unfed, the circadian dip (a factor under 1) is taken out
-- of h (dip) and H never falls under the last HUNGER (item 10a: a fast never lowers the moodle, a stated bend); fed,
-- the curve and the dead zone. cap (optional) is the minute's HUNGER cap (K.hybrid.caps): a last HUNGER above it was
-- written under a lifted cap or the starving minimum that has just ended, so it is not held (Plan 15 Task 6 fix 3): the
-- curve re-seeds HUNGER, which may fall, rather than the hold parking it at the cap.
function K.hungerCurve.write(h, state, cap)
    local prev = state.hunger
    if cap ~= nil and prev > cap then
        prev = 0
    end
    if not state.fed then
        return K.max(K.hungerCurve.map(h / K.hungerCurve.dip(state.circ)), prev)
    end
    return K.hungerCurve.hold(K.hungerCurve.map(h), prev)
end
