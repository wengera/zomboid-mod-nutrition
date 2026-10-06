-- NR_Client_Effects.lua -- the client channel of the effects layer (Plan 5, spec § 6; ruling 20): the aim
-- multiplier and the speed multiplier, both read from the client's stored mirror (NR.client.mirror, the
-- table NR_Client_Mirror.lua keeps as the server sent it) and APPLIED BY NEITHER, because no seat for
-- either write came back measured.
--
-- The aim re-apply, UNAPPLIED (X86 open, #3063):
--  * The engine rewrites the aiming delay after each shot as its current value plus the weapon's terms,
--    clamped to the weapon's aiming time (#2326, the rule #2710), and OnWeaponSwing fires on the shooting
--    client AFTER that post-shot write, once per shot (#3026, #3061). It is the seat this file listens on.
--  * Whether a write made there survives the per-update aiming step is unmeasured: run
--    x161p-20261006-035559's harness aim flag did not hold -- the engine cleared a written aim flag on 555
--    of 601 client ticks and the delay sat at the weapon's aiming time throughout (#3062) -- so no seat
--    was seen to keep a written delay.
--  * The write is one line away once a seat is measured: on the local player, after the swing,
--    setAimingDelay(min(aimingTime, delay * aimMul)). Until then the listener reads the mirror's
--    effects_aimMul and the player's getAimingDelay(), counts them, logs them at log level 3, and writes
--    NOTHING (the value it would write is kept on lastWouldBe for the live reading).
--
-- The speed write, UNAPPLIED (X47 open, #2096): a client write to the WalkSpeed animation variable was
-- gone by the first sample 266 ms after it, standing and walking, and no holding window was seen; a
-- multiplayer client copies its walk speed from the network AI (#2599). speedMul() returns the mirror's
-- effects_speedMul and nothing calls an animation-variable setter.
--
-- Shape (NR_Server_Intake.lua's wrapper discipline, applied to an event listener):
--  * The sentinel NR_ClientEffects_Installed is a global of its own, never a field of NutritionRevamp,
--    which NR_Core re-creates on every load (#0943): it holds the one listener closure, so a re-run of
--    this file or of NR_Core adds no second listener.
--  * The closure names nothing from this file's load: it looks NutritionRevamp.client.effects up per call,
--    so a reload swaps the logic under the listener that stays added.
--  * The side test is per call; every Java global (Events, getPlayer) is named only inside a function
--    behind a nil check, so the file loads with no engine (testing/tests/kernel/test_client_effects_shape.py).
--  * The body runs under one pcall: a mod error never reaches the event (the -debug client would park).
--  * The mirror is read only through the stored table, never the engine per frame (spec § 6); the
--    mirror's effects_* keys are Task 11's, and an absent or non-finite key reads nil.
-- Cadence: once per swing on the local client; no @fastpath region in this file.
local NR = NutritionRevamp
NR.client.effects = {
    stats = { swings = 0, reads = 0, noMirror = 0, notLocal = 0, errors = 0 },
    lastAimMul = nil,
    lastDelay = nil,
    lastWouldBe = nil,
    lastError = nil,
    limitations = {
        "the aim multiplier is read from the mirror and logged after each swing but never applied: no seat was measured to keep a written aiming delay (X86 open; the engine cleared a written aim flag on most ticks)",
        "the speed multiplier is read from the mirror but no speed write is made (X47 open: a client WalkSpeed write was gone by the first sample, 266 ms after it)",
        "the client reads the mirror as last received: an effects change reaches it on the server's push, at most one per player per 60 s, or on a request",
    },
}
local CE = NR.client.effects

NR_ClientEffects_Installed = NR_ClientEffects_Installed or {}

local function finite(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

-- The mirror's value under key, or nil when no mirror arrived or the value is not a finite number.
local function mirrorNumber(key)
    local m = NR.client.mirror
    if type(m) ~= "table" then return nil end
    local v = m[key]
    if finite(v) then return v end
    return nil
end

function CE.aimMul()
    return mirrorNumber("effects_aimMul")
end

-- The speed stub: the multiplier the server composed, returned and never written (X47).
function CE.speedMul()
    return mirrorNumber("effects_speedMul")
end

local function swingBody(character, weapon)
    local okP, p = pcall(getPlayer)
    if not okP or p == nil or character ~= p then
        CE.stats.notLocal = CE.stats.notLocal + 1
        return
    end
    CE.stats.swings = CE.stats.swings + 1
    local aim = CE.aimMul()
    if aim == nil then
        CE.stats.noMirror = CE.stats.noMirror + 1
        return
    end
    local okD, delay = NR.call(p, "getAimingDelay")
    if not okD or not finite(delay) then return end
    local would = delay * aim
    local okT, aimingTime = NR.call(weapon, "getAimingTime")
    if okT and finite(aimingTime) and aimingTime < would then would = aimingTime end
    CE.stats.reads = CE.stats.reads + 1
    CE.lastAimMul = aim
    CE.lastDelay = delay
    CE.lastWouldBe = would
    if NR.log.level >= 3 then
        NR.log.say(3, "effects: swing aimMul=" .. tostring(aim) .. " delay=" .. tostring(delay)
                    .. " wouldBe=" .. tostring(would) .. " (unapplied, X86)")
    end
end

-- The listener's logic, looked up per call by the sentinel's closure.
function CE.onSwing(character, weapon)
    if not NR.isClient() then return end
    if getPlayer == nil then return end
    local ok, err = pcall(swingBody, character, weapon)
    if not ok then
        CE.stats.errors = CE.stats.errors + 1
        CE.lastError = err
        NR.log.say(2, "effects: swing read failed: " .. tostring(err))
    end
end

-- Adds the one listener; idempotent across re-runs of this file and of NR_Core.
function CE.install()
    local S = NR_ClientEffects_Installed
    if S.fn ~= nil then return true end
    if Events == nil or Events.OnWeaponSwing == nil then return false end
    S.fn = function(character, weapon)
        local nr = NutritionRevamp
        if nr == nil or nr.client == nil or nr.client.effects == nil then return end
        nr.client.effects.onSwing(character, weapon)
    end
    Events.OnWeaponSwing.Add(S.fn)
    return true
end

CE.install()
