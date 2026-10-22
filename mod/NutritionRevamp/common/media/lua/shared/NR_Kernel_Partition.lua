-- NR_Kernel_Partition.lua -- the body model's daily partition (spec section 5.1; the oracle's exact day, ruling 13-2):
-- once per game day K.strength.day moves fat, lean F (body.lm) and the labile lean lx by the sign of the day's
-- energy balance through the two lean arms below: a surplus pays growth first and splits the rest by Forbes' lean share
-- into lx and fat; a deficit splits by Forbes' lean share under the training and protein protection, lx paying the
-- lean loss first, with no fat ceiling (Plan 16 Task 5; S2278-S2283). An immobilised day (a leg fracture or splint)
-- follows the logarithmic disuse curve instead (the adapter's day close, ruling 13-13). The day close rotates the
-- seven-day rings and zeroes the day accumulators.
-- Pure: numbers and Lua tables in, numbers, booleans and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.log and the bounded numeric `for` over the kernel's own tables are allowed.
-- This file sorts after NR_Kernel.lua, and every K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.partition = {}

-- The fat store's maximum energy transfer rate, kcal per kg fat per day: the disuse arm's alone. The deficit arm
-- reads no ceiling (Plan 16 Task 5): 69 is the Minnesota men's own fat flux under a moderate deficit (arithmetic on
-- S2287), and measured fasts draw fat faster (S1910, S2282). The disuse arm keeps it, out of that task's scope.
K.partition.FAT_CEIL_KCAL = K.dials.get("partition.FAT_CEIL_KCAL")

-- The tissue energy densities, kcal per kg.
K.partition.RHO_LEAN = K.dials.get("partition.RHO_LEAN")
K.partition.RHO_FAT = K.dials.get("partition.RHO_FAT")

-- The lean-mass arms (Plan 13): F is body.lm, the labile lean (water, glycogen, organ: weight, not level or REE)
-- body.lx and fat body.fm. Every constant is P's (K.strength.DEFAULTS
-- or a server's params, ruling 13-1) save RHO_LEAN, RHO_FAT and FAT_CEIL_KCAL above. The arms return the
-- changes before the floors; the day applies them (Task 8). grow is the day's lean gain already scaled by
-- the biology clock ts, and its energy is charged at grow / ts (ruling 13-3).

-- Forbes' lean weight share of a mass change at fat mass fm kg: forbes_c / (forbes_c + fm) (S0054, S0055).
function K.partition.forbes(fm, P)
    return P.forbes_c / (P.forbes_c + fm)
end

-- The training dose T of S weekly hard sets: S / S_def, full at 1 (S1997).
function K.partition.training(S, P)
    return K.min(1, S / P.S_def)
end

-- The surplus arm (E >= 0), returning dX, dM (kg): growth is paid first; a surplus that cannot pay it has
-- fat fund the difference, and then lx decays on x_tau_d days (the day has no surplus left). Otherwise the
-- rest splits by the lean weight share xs = forbes(fm) * the protein ramp (p - xs_p0) / xs_pspan (ruling
-- 13-37, never pdef_*) * (1 - T) into lx, capped at x_max_frac * F, and fat.
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

-- The deficit arm (E < 0), returning dF, dX, dM (kg), dF the partition's own lean change (growth not in
-- it): the lean weight share forbes(fm) * prot, prot = 1 - wT * T - wP * the protein ramp over pdef_lo ..
-- pdef_hi, clamped to [prot_floor, 1], splits the whole deficit and fat pays the rest, with no ceiling (Plan 16
-- Task 5, the science pass's form (a)): in a water-only fast the share gives about 13 % of the energy from lean at
-- 20 % fat and about 6 % at 37 % (S2278, S2282, S2283; S1056), so fat can reach its floor. Fat funds the day's
-- growth (recomposition); the fat draw past the floor fmMin (a game choice) is paid by lean instead, energy for energy
-- (Plan 16 Task 5 fix 1), so the day's floor clamp never drops energy and a body at the floor keeps losing mass. lx
-- pays the lean loss first and F the remainder; what is left of lx decays on x_tau_d days.
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

-- The alcohol gate: above ALC_THRESH g per kg per day the lean gain carries G_ALC.
K.partition.ALC_THRESH = K.dials.get("partition.ALC_THRESH")
K.partition.G_ALC = K.dials.get("partition.G_ALC")

-- The disuse curve: the lean fraction lost after t days immobilised is DISUSE_A * ln(1 + t / DISUSE_T).
K.partition.DISUSE_A = K.dials.get("partition.DISUSE_A")
K.partition.DISUSE_T = K.dials.get("partition.DISUSE_T")

-- The alcohol gate: G_ALC above ALC_THRESH g alcohol per kg body mass per day, else 1.
function K.partition.gAlc(alcGPerKg)
    if alcGPerKg > K.partition.ALC_THRESH then
        return K.partition.G_ALC
    end
    return 1
end

-- The lean fraction lost after tDays immobilised: DISUSE_A * ln(1 + tDays / DISUSE_T).
function K.partition.disuseFraction(tDays)
    local P = K.partition
    return P.DISUSE_A * math.log(1 + tDays / P.DISUSE_T)
end

-- The disuse arm for immobilised day tDisuse (>= 1; the adapter stamps lm0dis, the lean mass on the
-- day disuse began, when tDisuse goes 0 -> 1), returning dFM, dLM (kg): lean loses lm0dis times the
-- curve's step from day tDisuse - 1 to day tDisuse, whatever the balance. Fat takes the deficit arm
-- with the lean overflow set to 0: fat pays up to the ceiling and the energy beyond it is UNPAID under
-- immobilisation (the disuse loss stands in for the lean arm); a surplus reads as a negative deficit
-- under the ceiling and is stored as fat. A tDisuse below 1 reads as day 1 (branchless guard).
function K.partition.disuse(body)
    local P = K.partition
    local t = K.max(body.tDisuse, 1)
    local dLM = -body.lm0dis * (P.disuseFraction(t) - P.disuseFraction(t - 1))
    local fromFat = K.min(-body.ebDay, P.FAT_CEIL_KCAL * body.fm)
    local dFM = -fromFat / P.RHO_FAT
    return dFM, dLM
end

-- Close the day: shift eb7, mass7 and p7 one slot (slot 1 the oldest), write the day's ebDay, the body mass
-- fm + lm + lx (ruling 13-20) and pDay into slot 7 (the 7-day readers': deficitWeek, K.body.trend, NR_Server_Effects' protein
-- week), zero the day accumulators and advance dayIndex. The trailing-24 h window is not the day's: it
-- runs on the clock (K.body.trailTo). Returns the body.
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

-- Whether the seven closed days sum to a deficit.
function K.partition.deficitWeek(body)
    local sum = 0
    for i = 1, K.body.WEEK_N do
        sum = sum + body.eb7[i]
    end
    return sum < 0
end
