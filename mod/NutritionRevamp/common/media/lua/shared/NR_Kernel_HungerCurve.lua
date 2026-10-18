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
    0.097, -- game choice (spec section 10: the curve's knots): the flat foot's end, the highest lowest h_model after a 667 kcal meal on the fit's three-meal days in either sleep setting (0.0966 after the evening meal with sleep on, rounded up; Plan 16 Task 4b), so such a meal reads 0 and a 400 kcal one 0.054 with sleep off, 0.035 with sleep on
    0.21125, -- game choice (spec section 10: the curve's knots), fitted (Plan 15 Task 6c, re-fitted in Task 14b and Plan 16 Task 4b): Peckish shows above it, 3.9 h after the fast's 667 kcal breakfast with sleep off and 4.4 h with sleep on (vanilla 4.4 h); on three such meals a day 4.0 h after breakfast, 4.1 h after lunch and 4.0 h after dinner with sleep off, 4.4 h, 3.9 h and 3.7 h with sleep on (vanilla 1.2 h, 4.25 h and 5.0 h), 24 % and 22 % of waking hours at level 1 or more (vanilla 38 %); at x0.95 and x1.05 lunch 3.8 h and 4.5 h, dinner 3.7 h and 4.3 h, 3.5 h and 4.3 h after the fast's breakfast
    0.289531, -- game choice (spec section 10: the curve's knots), fitted (Plan 16 Task 4b): Hungry shows above it, 8.1 h after the meal with sleep off and 7.8 h with sleep on (vanilla 8.0 h); 3.1 % of waking hours at level 2 or more in both (vanilla 4.4 %); at x0.95 and x1.05 7.2 h and 9.4 h
    0.420782, -- game choice (spec section 10: the curve's knots), fitted (Plan 16 Task 4b): Very Hungry shows above it, 17.3 h after the meal with sleep off and 16.8 h with sleep on (vanilla 17.0 h); at x0.95 and x1.05 15.8 h and 19.2 h
    0.6825, -- game choice (spec section 10: the curve's knots), fitted (Plan 16 Task 4b): the cap 0.69 comes at 34.5 h with sleep off and 33.1 h with sleep on (vanilla's Starving at 34.5 h), and Starving shows at the acute starvation onset (K.hybrid.caps), 34.6 h in both; at x0.95 and x1.05 32.0 h and 37.4 h
    1, -- the model's top: no row needed
}
K.hungerCurve.Y = {
    0, -- no row needed
    0, -- the flat foot: game choice (spec section 10: the curve's knots)
    0.15, -- VANILLA #0508 (HUNGRY level 1, Peckish)
    0.25, -- VANILLA #0508 (HUNGRY level 2, Hungry)
    0.45, -- VANILLA #0508 (HUNGRY level 3, Very Hungry)
    0.70, -- VANILLA #0508 (HUNGRY level 4, Starving)
    1, -- the stat's top (#0021)
}
-- The HUNGRY thresholds the dead zone guards, each a strict greater-than (#0507): VANILLA #0508.
K.hungerCurve.THRESHOLDS = { 0.15, 0.25, 0.45, 0.70 }
K.hungerCurve.DEAD_ZONE = 0.02 -- game choice (spec section 10: the dead-zone width; item 10b): a level steps down only once H is this far under its threshold
K.hungerCurve.HOLD_EPS = 0.001 -- game choice (spec section 10: the dead-zone width): a held H sits this far over its threshold, far under a moodle step and over float noise
K.hungerCurve.FED_M = 3.80654 -- game choice (spec section 10: the curve's knots; item 10a): fed while the meal pool M holds at least K.satiety.MEAL_REQ weighted kcal, the M at which the meal pool alone reads the request; about 4.5 h after a 667 kcal meal and 3 h after a 200 kcal snack

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
