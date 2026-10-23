-- NR_Kernel_HungerCurve.lua -- the calibrated hunger writer: H = write(h_model, state). A monotone piecewise-linear map
-- fitted so a satisfying meal reads about 0 and Peckish and Hungry return on vanilla's cadence; unfed, the morning
-- circadian dip is taken out and H never falls; a dead zone at each HUNGRY threshold stops a level blinking.
-- K.hybrid.write caps the result. One statement a line for the coverage gate.
local K = NutritionRevamp.kernel
K.hungerCurve = {}

-- The knots, h_model (X) to HUNGER (Y). Y's third to sixth are the HUNGRY thresholds (#0508), so each X is where that
-- level shows. X is fitted by tools/fit_hunger_curve.py on both sleep settings. No curve meets vanilla's three-can
-- breakfast and its lunch and dinner at once, because a satisfying meal resets the meal pool; the Peckish knot is the
-- compromise the fit's weights choose.
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
-- Each a strict greater-than (#0507).
K.hungerCurve.THRESHOLDS = { K.hungerCurve.Y[3], K.hungerCurve.Y[4], K.hungerCurve.Y[5], K.hungerCurve.Y[6] }
K.hungerCurve.DEAD_ZONE = K.dials.get("hungerCurve.DEAD_ZONE")
K.hungerCurve.HOLD_EPS = K.dials.get("hungerCurve.HOLD_EPS")
K.hungerCurve.FED_M = K.dials.get("hungerCurve.FED_M")

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

-- On the flat foot it reads the foot's end, the least sated h_model that reads that H.
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

-- The level steps down only past the zone; a rise is never held.
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

-- With sleep off the factor is 1, so there is no dip; the evening rise is never taken out.
function K.hungerCurve.dip(circ)
    if circ ~= nil and circ > 0 and circ < 1 then
        return circ
    end
    return 1
end

-- Unfed, H never falls under the last HUNGER (a fast never lowers the moodle). A last HUNGER above cap was written
-- under a lifted cap or the starving minimum that just ended, so it is not held: the curve re-seeds it.
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
