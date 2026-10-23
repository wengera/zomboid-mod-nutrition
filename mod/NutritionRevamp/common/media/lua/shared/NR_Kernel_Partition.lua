-- NR_Kernel_Partition.lua -- the body's daily partition: once a game day K.strength.day moves fat, lean F (body.lm) and
-- the labile lean lx (weight, not level or REE) by the sign of the day's balance. A surplus pays growth first and
-- splits the rest by Forbes' lean share; a deficit splits by that share under training and protein protection, lx
-- paying first. An immobilised day follows the disuse curve. K.clamp / K.min / K.max are read at call time.
local K = NutritionRevamp.kernel
K.partition = {}

-- The disuse arm's alone: the deficit arm reads no ceiling, since measured fasts draw fat faster (S1910).
K.partition.FAT_CEIL_KCAL = K.dials.get("partition.FAT_CEIL_KCAL")

K.partition.RHO_LEAN = K.dials.get("partition.RHO_LEAN")
K.partition.RHO_FAT = K.dials.get("partition.RHO_FAT")

-- Every arm constant is P's (K.strength.DEFAULTS or a server's params). grow is already scaled by the biology clock
-- ts, so its energy is charged at grow / ts.

-- (S0054)
function K.partition.forbes(fm, P)
    return P.forbes_c / (P.forbes_c + fm)
end

-- full at 1 (S1997)
function K.partition.training(S, P)
    return K.min(1, S / P.S_def)
end

-- A surplus that cannot pay growth has fat fund the difference, and lx decays; otherwise the rest splits into lx
-- (capped at x_max_frac * F) and fat.
function K.partition.surplusLean(body, grow, S, p, E, P, ts)
    local RL = K.partition.RHO_LEAN
    local RF = K.partition.RHO_FAT
    local rest = E - grow / ts * RL
    if rest <= 0 then
        return -body.lx / P.x_tau_d, rest / RF
    end
    local ramp = K.clamp((p - P.xs_p0) / P.xs_pspan, 0, 1)
    local xs = K.partition.forbes(body.fm, P) * ramp * (1 - K.partition.training(S, P))
    local dW = rest / (xs * RL + (1 - xs) * RF)
    local room = K.max(0, P.x_max_frac * body.lm - body.lx)
    local dX = K.min(xs * dW, room)
    return dX, (rest - dX * RL) / RF
end

-- The whole deficit splits by the lean share and fat pays the rest with no ceiling, so fat can reach its floor (S2278).
-- The fat draw past fmMin is paid by lean energy for energy, so the floor clamp never drops energy and a body at the
-- floor keeps losing mass.
function K.partition.deficitLean(body, grow, S, p, E, P, ts)
    local RL = K.partition.RHO_LEAN
    local RF = K.partition.RHO_FAT
    local gP = K.clamp((p - P.pdef_lo) / (P.pdef_hi - P.pdef_lo), 0, 1)
    local prot = K.clamp(1 - P.wT * K.partition.training(S, P) - P.wP * gP, P.prot_floor, 1)
    local share = K.partition.forbes(body.fm, P) * prot
    local dW = -E / (share * RL + (1 - share) * RF)
    local fatDraw = (1 - share) * dW + grow / ts * RL / RF
    local over = K.max(0, fatDraw - K.max(0, body.fm - P.fmMin))
    local leanLoss = share * dW + over * RF / RL
    local fromX = K.min(body.lx, leanLoss)
    local dX = -fromX - (body.lx - fromX) / P.x_tau_d
    local dM = over - fatDraw
    return -(leanLoss - fromX), dX, dM
end

K.partition.ALC_THRESH = K.dials.get("partition.ALC_THRESH")
K.partition.G_ALC = K.dials.get("partition.G_ALC")

K.partition.DISUSE_A = K.dials.get("partition.DISUSE_A")
K.partition.DISUSE_T = K.dials.get("partition.DISUSE_T")

function K.partition.gAlc(alcGPerKg)
    if alcGPerKg > K.partition.ALC_THRESH then
        return K.partition.G_ALC
    end
    return 1
end

function K.partition.disuseFraction(tDays)
    local P = K.partition
    return P.DISUSE_A * math.log(1 + tDays / P.DISUSE_T)
end

-- The adapter stamps lm0dis when tDisuse goes 0 -> 1. Fat takes the deficit arm with no lean overflow: the energy past
-- the ceiling is UNPAID under immobilisation, the disuse loss standing in for the lean arm. tDisuse below 1 reads day 1.
function K.partition.disuse(body)
    local P = K.partition
    local t = K.max(body.tDisuse, 1)
    local dLM = -body.lm0dis * (P.disuseFraction(t) - P.disuseFraction(t - 1))
    local fromFat = K.min(-body.ebDay, P.FAT_CEIL_KCAL * body.fm)
    local dFM = -fromFat / P.RHO_FAT
    return dFM, dLM
end

-- Slot 1 is the oldest. The trailing-24 h window is not the day's: it runs on the clock (K.body.trailTo).
function K.partition.closeDay(body)
    local eb = body.eb7
    local mass = body.mass7
    local p7 = body.p7
    local n = K.body.WEEK_N
    for i = 1, n - 1 do
        eb[i] = eb[i + 1]
        mass[i] = mass[i + 1]
        p7[i] = p7[i + 1]
    end
    eb[n] = body.ebDay
    mass[n] = body.fm + body.lm + body.lx
    p7[n] = body.pDay
    body.inDay = 0
    body.eeDay = 0
    body.ebDay = 0
    body.actKcalDay = 0
    body.exKcalDay = 0
    body.pDay = 0
    body.carbDay = 0
    body.lipDay = 0
    body.alcDay = 0
    body.dayIndex = body.dayIndex + 1
    return body
end

function K.partition.deficitWeek(body)
    local sum = 0
    for i = 1, K.body.WEEK_N do
        sum = sum + body.eb7[i]
    end
    return sum < 0
end
