-- nutrition_3day_gain / nutrition_3day_fast: three accelerated game-days at a fixed daily
-- intake, sampled hourly. The model check itself is Python (testing/pzt/scenarios_nutrition.py)
-- -- this file only drives the world and records what the SERVER's Nutrition object did.
--
-- SERVER-side (under server/scenarios/, run through the server's bus) because the server owns
-- Nutrition: `Nutrition.update @42 L75` is `!GameClient.client`, so on a client the macro drain
-- and updateCalories() never run and a client-side setCalories is overwritten by the next
-- PlayerStatsPacket within a second (measured, slice 01 exp01-20260910-000351). There is no
-- getPlayer() on a dedicated server; `t.player` is the IsoPlayer the test layer resolved out of
-- getOnlinePlayers() for the account named by `test.run <name> [username]`.
--
-- Feeding schedule -- WHY TWO DOSES A DAY. setCalories clamps at 3700 (slice 01, C+M), so the
-- plan's single +4000 dose would be truncated on contact and the run would measure the clamp
-- rather than the intake. +2000 at hour 0 and again at hour 12 keeps each dose under the
-- ceiling while still delivering 4000 kcal/game-day against an idle burn of ~1382 kcal/game-day
-- at 80 kg (0.016/game-s x 86400, 03-notes). The store still reaches the ceiling on day 2 --
-- that is the model's own behaviour, not an artefact: every feed logs calories before and after
-- with the value asked for, so the Python side can account for the kcal the clamp swallowed.
--
-- Sampling resolution is one game-hour. The evaluator integrates the weight model
-- sample-to-sample with the calorie value at the START of each interval, so the hour is the
-- resolution of the check; at the measured drift (~58 kcal/game-hour idle) the left-endpoint
-- error over three days is ~0.025 kg, an order below the tolerance.
--
-- WHY HUNGER AND THIRST ARE PINNED. Calories are not food: setCalories fills the nutrition
-- store and leaves CharacterStat.HUNGER/THIRST untouched, so the first attempt at this run
-- (scenario-20260910-052624) watered nobody -- health drain started at 29.13 game-h (the
-- predicted THIRST level-4 crossing is 29.17), fell 17.820 per game-hour of world time, and the
-- subject DIED at game-hour 35. That rate is `BodyDamage.Update`'s THIRST == 4 branch to five
-- figures: `healthReductionFromSevereBadMoodles / 10 x GameTime.getMultiplier()`
-- (`@1320-@1358 L2377-L2379`) = 1.65e-3 per multiplier unit x 3.0 units/game-s on this
-- fixture's 90-minute day = 17.820 health/game-h. The HUNGRY == 4 branch is a fifth of that
-- (/50, 3.564) and hunger never reached level 4 anyway. Nutrition.update stops on a corpse:
-- carbs froze at -437.9, nowhere near their -500 floor, and weight and the macros did not move
-- again for 37 game-hours, so the run measured a dead man for half of it. Both stats are
-- therefore reset after every sample. Neither is an input to the weight model -- updateWeight
-- reads calories, carbs and lipids only, and updateCalories' branches are posture and weight,
-- not hunger -- so pinning them removes a lethal confounder without touching what is under
-- test. The sampler also ENDS the run the moment it sees a corpse, so a future death costs one
-- sample rather than six wall minutes of flat lines.
--
-- Harness rules (slice 01/02/03): every Java member goes through TK.call -- index-first guard:
-- a caught nil call is silent and names nothing; an unguarded raise aborts the rest of this
-- handler (x126/x127), which here is Events.EveryOneMinute -- see docs/modding/lua-api.md
-- section 5. No `goto`, and never "%d" on a Lua number (they are all doubles); "%.0f" or
-- tostring instead.

local DAYS = 3
local RUN_MIN = DAYS * 24 * 60          -- 4320 game minutes of scenario
local SAMPLE_MIN = 60                   -- one sample per game-hour
local DOSE_MIN = 12 * 60                -- two doses a game-day
local DOSES = DAYS * 2                  -- 6 in total: hours 0, 12, 24, 36, 48, 60 -- none at the
                                        -- end, where a dose would only move the final sample.

-- Read helper: a getter this build does not expose leaves the key absent from the sample
-- instead of raising. `n` is the Nutrition object.
local function get(obj, getter)
    local _, v = TK.call(obj, getter)
    return v
end

-- Hunger and thirst are diagnostic only (neither is in the weight model), and both are the
-- read-back on the pin below. B42 moved the accessors to Stats:get(CharacterStat.X) -- on this
-- jar `Stats` exposes only get(CharacterStat)F / set(CharacterStat,F)Z, so the legacy
-- get<Name>() fallback is dead here and kept only for older builds. The enum is resolved BEFORE
-- the call because handing a nil enum to a live Java method is an arity or overload mismatch --
-- it raises and pcall catches it (lua-api.md section 5 row 2); the guard keeps the reply
-- informative. `getStats` goes through TK.call for the same reason.
local function statOf(p, enumName, getter)
    local _, s = TK.call(p, "getStats")
    if s == nil then return nil end
    local enum = CharacterStat and CharacterStat[enumName]
    if enum ~= nil then
        local ok, v = TK.call(s, "get", enum)
        if ok then return v end
    end
    return get(s, getter)
end

local function hungerOf(p) return statOf(p, "HUNGER", "getHunger") end
local function thirstOf(p) return statOf(p, "THIRST", "getThirst") end

-- The sandbox `Nutrition` option gates Nutrition.update() -- drain, calorie burn AND weight
-- (slice 01). If it were off, every sample would be flat and the run would look like a model
-- failure rather than a switched-off subsystem, so it is recorded at setup.
local function sandboxNutrition()
    if getSandboxOptions == nil then return "no getSandboxOptions()" end
    local opts = getSandboxOptions()
    if opts == nil then return "getSandboxOptions() returned nil" end
    local ok, opt = TK.call(opts, "getOptionByName", "Nutrition")
    if ok and opt ~= nil then
        local okv, v = TK.call(opt, "getValue")
        if okv then return tostring(v) end
    end
    if SandboxVars ~= nil and SandboxVars.Nutrition ~= nil then return tostring(SandboxVars.Nutrition) end
    return "unknown"
end

-- calories/weight/carbs/lipids/proteins are the model's own variables; hunger, thirst, health,
-- asleep and dead are the diagnostics that make a flat trace readable -- "the weight stopped
-- moving" means something entirely different once the health column shows why. They are what
-- caught the thirst death in the first run, and hunger/thirst are also the read-back proving
-- both halves of the pin hold. THIRST is sampled because it is the stat that killed run 1 and
-- the one the health drain is keyed on (BodyDamage.Update @1320-@1358 L2377-L2379): without the
-- column the attribution rests on timing alone, which is what the run-1 report had to do.
local function sample(t, n)
    local p = t.player
    local bd = get(p, "getBodyDamage")
    return t:sample({
        calories = get(n, "getCalories"), weight = get(n, "getWeight"),
        carbs = get(n, "getCarbohydrates"), lipids = get(n, "getLipids"),
        proteins = get(n, "getProteins"),
        hunger = hungerOf(p), thirst = thirstOf(p),
        health = bd ~= nil and get(bd, "getHealth") or nil,
        asleep = get(p, "isAsleep"), dead = get(p, "isDead"),
    })
end

-- Reset the two stats that kill an unfed character, through the harness's own setter (it tries
-- Stats:set(CharacterStat.X, v) first and set<Name>() second, and reports which answered).
-- Returns the two routes for the setup log; after that the result is ignored -- a stat that
-- cannot be written shows up as a rising `hunger` column in the samples.
local function water(p)
    local okH, howH = TK.setStat(p, "hunger", 0)
    local okT, howT = TK.setStat(p, "thirst", 0)
    return (okH and howH or ("hunger FAILED: " .. tostring(howH))),
           (okT and howT or ("thirst FAILED: " .. tostring(howT)))
end

-- Logged before/after with the value asked for: `asked` minus `after` IS the clamp loss, and
-- the evaluator parses these lines back out of the result doc rather than re-deriving them.
local function feed(t, n, dose)
    local before = get(n, "getCalories") or 0
    local asked = before + dose
    TK.call(n, "setCalories", asked)
    local after = get(n, "getCalories")
    t:log(string.format("fed +%.0f: calories %s -> %s (asked %s)", dose, tostring(before),
                        tostring(after), tostring(asked)))
end

local function setup(t, n, dose)
    t:log("before: calories=" .. tostring(get(n, "getCalories")) ..
          " weight=" .. tostring(get(n, "getWeight")) ..
          " carbs=" .. tostring(get(n, "getCarbohydrates")))
    TK.call(n, "setWeight", 80)
    TK.call(n, "setCalories", 0)
    TK.call(n, "setCarbohydrates", 0)
    TK.call(n, "setLipids", 0)
    TK.call(n, "setProteins", 0)
    t:log(string.format("setup weight=%s calories=%s carbs=%s lipids=%s proteins=%s",
                        tostring(get(n, "getWeight")), tostring(get(n, "getCalories")),
                        tostring(get(n, "getCarbohydrates")), tostring(get(n, "getLipids")),
                        tostring(get(n, "getProteins"))))
    local howH, howT = water(t.player)
    t:log("pinning hunger/thirst each sample via " .. tostring(howH) .. " / " .. tostring(howT))
    t:log(string.format("plan: %.0f game-days, dose=%.0f x %.0f (%.0f kcal/game-day), " ..
                        "sample every %.0f game-min, sandbox Nutrition=%s",
                        DAYS, dose, DOSES / DAYS, dose * DOSES / DAYS, SAMPLE_MIN,
                        sandboxNutrition()))
end

local function register(name, dose)
    -- timeoutMin is the test layer's own backstop: RUN_MIN + 1 is when the finisher runs, so
    -- the backstop sits 29 game-minutes past it and only fires if the finisher never did.
    TK.test(name, { timeoutMin = RUN_MIN + 30, run = function(t)
        local ok, n = TK.call(t.player, "getNutrition")
        if not ok or n == nil then
            t:done(false, "no getNutrition() on the server player")
            return
        end
        setup(t, n, dose)
        if dose > 0 then feed(t, n, dose) end
        sample(t, n)                        -- baseline at minute 0, after the first dose
        t:every(SAMPLE_MIN, function()
            local s = sample(t, n)
            if s.dead == true then
                t:assert(false, string.format("subject died by game-hour %.1f (health %s)",
                                              s.gameMinute / 60, tostring(s.health)))
                t:done(false, "subject died: Nutrition.update stops on a corpse")
                return
            end
            water(t.player)                 -- after the sample, so each row is the pre-pin value
        end)
        -- WHY EVERY DOSE IS ALREADY IN THAT HOUR'S SAMPLE. The sampler above and this dose timer
        -- come due together every 12th game-hour (minutes 720, 1440, ...), and a shared minute is
        -- dispatched in `seq` order -- the order the callbacks were SCHEDULED, not registered.
        -- t:every re-arms with a fresh seq on every tick, so the sample due at minute 720 took its
        -- seq at minute 660, while the dose due at minute 720 took its seq here, at minute 0. The
        -- dose therefore lands BEFORE that hour's sample (and the same holds at 1440, 2160, ...:
        -- the dose's seq always comes from one dose-interval back, the sample's from one hour
        -- back). So each dose is credited at the END of the interval it fell in -- exactly the
        -- assumption behind the midpoint re-integration in nutrition-core.md § Verified on server,
        -- and the reason the evaluator's left-endpoint integral, which cannot credit it there,
        -- carries a ~0.025 kg bias over three game-days rather than a model error.
        if dose > 0 then
            local left = DOSES - 1          -- the hour-0 dose is already in
            t:every(DOSE_MIN, function()
                if left <= 0 then return end
                left = left - 1
                feed(t, n, dose)
            end)
        end
        -- RUN_MIN + 1, not RUN_MIN: within a game minute the due callbacks run in the order
        -- they were scheduled and this finisher was armed first, so at RUN_MIN it would end the
        -- test before that hour's sample was taken (smoke_clock hit the same ordering). One
        -- extra game minute buys the 72-hour sample.
        t:at(RUN_MIN + 1, function()
            t:assert(#t.samples >= DAYS * 24,
                     string.format("expected >= %.0f samples, got %.0f", DAYS * 24, #t.samples))
            local last = t.samples[#t.samples] or {}
            t:log(string.format("end: calories=%s weight=%s carbs=%s hunger=%s thirst=%s dead=%s",
                                tostring(last.calories), tostring(last.weight),
                                tostring(last.carbs), tostring(last.hunger),
                                tostring(last.thirst), tostring(last.dead)))
            t:done(true, string.format("%.0f game-days, %.0f samples", DAYS, #t.samples))
        end)
    end })
end

register("nutrition_3day_gain", 2000)
register("nutrition_3day_fast", 0)
