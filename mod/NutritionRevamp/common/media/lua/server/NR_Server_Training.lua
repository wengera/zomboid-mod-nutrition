-- NR_Server_Training.lua -- the body model's resistance events (Plan 3, ruling 4 on its primary branch,
-- ruling T4): the X39 rep and hit arms fire server-side (run x141a), so the set-equivalents come from
-- Events.AddXP, Events.OnWeaponHitXp and Events.OnWeaponHitTree, wired once at OnServerStarted. The
-- per-minute work (load, timed action, decay, the climb-state sample) is NR_Server_Metabolism's; this
-- file owns the events only and never runs on a clock.
--
-- A rep (ruling T13-2, replacing T5-1's anchor): the engine grants one exercise rep as a Strength AddXP
-- then a Fitness AddXP back to back with no amount test (Fitness.incStats @201 L351, @211 L352:
-- Strength = 4 per "arms" + 2 per "chest", Fitness = 4 per "legs" + 2 per "abs", times the exercise's
-- xpMod, truncated). XP.AddXP returns before the Lua event when the perk is Fitness and the character
-- may not gain Fitness XP (L14196-L14198, #2647: the weight-trouble gate) or when the perk's XP sits at
-- its level-10 total (L14214-L14215), so the Fitness event drops reps for exactly the characters a
-- nutrition mod models. A rep is therefore counted ONCE on the STRENGTH event (0 for a legs exercise,
-- no weight gate) while getFitness():getCurrentExe() is current, and that opens the rep's pair; the
-- Fitness event that follows closes the pair and banks nothing. A Fitness event with no open pair is a
-- rep whose Strength event the level-10 cap dropped, and is counted there instead. A Strength event
-- whose Fitness partner was dropped leaves the pair open; the next rep's Strength event counts as usual.
-- The rep's class is the exercise's first stiffness group (EXERCISE_CLASS, read from the install):
-- legs/abs bank S_REP_LEGS, arms/chest S_REP_ARMS, both at the moderate class. getCurrentExe answers a
-- Fitness$FitnessExercise whose type is a field with no getter, so the key is read when it can be (a
-- string, or a readable .type) and otherwise inferred from the Strength grant: above 0 is arms/chest,
-- 0 is legs/abs. An event of either perk with no current exercise is a knockback, tree or load grant,
-- ignored here (the hit and tree hooks and the minute's load sample own them) and closes any open
-- pair; a negative amount is rust and is ignored.
--
-- Each handler resolves the record by username off the store's records WITHOUT creating one (a player
-- with no record or no body yet is skipped until Metabolism's first sight), runs under one pcall and
-- never raises into the engine's event dispatch (#1072). Every Java read is index-first through NR.call;
-- every Java global is named only inside a function behind a nil check, so the file loads with no
-- engine (testing/tests/kernel/test_training_shape.py).
local NR = NutritionRevamp
local K = NR.kernel
NR.server.training = {
    stats = { reps = 0, paired = 0, repsFitnessOnly = 0, hits = 0, trees = 0, ignored = 0, failures = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "a climb or vault has no Lua event and is sampled per minute from the character's state",
        "a rep is counted on the Strength XP event (unconditional, 0 for a legs exercise); vanilla's Fitness-XP gate (#2647) cannot drop it; a character whose Strength XP sits at the level-10 total fires no Strength event, and its reps are counted on the Fitness event instead",
        "the exercise type is a Java field with no getter, so an unreadable exercise is classed from its Strength grant (above 0 arms/chest, 0 legs/abs; legs on the Fitness-only path)",
    },
}
local TRN = NR.server.training

-- The exercise's first stiffness group, read-only from the install
-- (media/lua/shared/Definitions/FitnessExercises.lua :8, :16, :24, :32, :42, :52, :62); unknown -> legs.
TRN.EXERCISE_CLASS = {
    squats = "legs", pushups = "arms", situp = "abs", burpees = "legs",
    barbellcurl = "arms", dumbbellpress = "arms", bicepscurl = "arms",
}
-- The set-equivalent per group (the kernel's game choices).
TRN.GROUP_S = { legs = "S_REP_LEGS", abs = "S_REP_LEGS", arms = "S_REP_ARMS", chest = "S_REP_ARMS" }
-- The weapon weight above which a hit is a high-intensity event (Task 13's brief).
TRN.HEAVY_WEAPON = 2
-- The open rep pair per username: true after a rep's Strength event, cleared by its Fitness partner.
TRN.pairOpen = {}

local function finite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

-- The username of a player owner, or nil (a zombie or a nil owner has none).
local function username(owner)
    local ok, name = NR.call(owner, "getUsername")
    if ok and type(name) == "string" then return name end
    return nil
end

-- The body of an existing record, or nil; never creates a record.
local function bodyOf(name)
    local S = NR.server.store
    if S == nil or name == nil then return nil end
    local records = S.records
    if records == nil and S.attach ~= nil then records = S.attach() end
    if records == nil then return nil end
    local record = records[name]
    if record == nil then return nil end
    return record.body
end

-- The current exercise (nil when none), off getFitness():getCurrentExe().
local function currentExe(player)
    local okF, fitness = NR.call(player, "getFitness")
    if not okF then return nil end
    local okE, exe = NR.call(fitness, "getCurrentExe")
    if okE then return exe end
    return nil
end

local function readType(exe)
    return exe.type
end

-- The exercise's key when it can be read: the value itself when a string, else its .type when readable.
local function exeKey(exe)
    if type(exe) == "string" then return exe end
    local ok, t = pcall(readType, exe)
    if ok and type(t) == "string" then return t end
    return nil
end

local function fail(err)
    TRN.stats.failures = TRN.stats.failures + 1
    TRN.lastError = err
    NR.log.say(2, "training: " .. tostring(err))
end

local function xpStep(player, perk, amount)
    if Perks == nil then return end
    local isStr = perk == Perks.Strength
    local isFit = perk == Perks.Fitness
    if not isStr and not isFit then return end
    local name = username(player)
    local body = bodyOf(name)
    if body == nil then return end
    if not finite(amount) or amount < 0 then
        TRN.stats.ignored = TRN.stats.ignored + 1
        return
    end
    local exe = currentExe(player)
    if exe == nil then
        TRN.pairOpen[name] = nil
        TRN.stats.ignored = TRN.stats.ignored + 1
        return
    end
    if isFit and TRN.pairOpen[name] then
        TRN.pairOpen[name] = nil                      -- the same rep's Fitness partner; banks nothing
        TRN.stats.paired = TRN.stats.paired + 1
        return
    end
    local group = nil
    local key = exeKey(exe)
    if key ~= nil then
        group = TRN.EXERCISE_CLASS[key] or "legs"
    elseif isStr and amount > 0 then
        group = "arms"
    else
        group = "legs"
    end
    K.training.event(body, K.training[TRN.GROUP_S[group]], "moderate")
    TRN.stats.reps = TRN.stats.reps + 1
    if isStr then
        TRN.pairOpen[name] = true                     -- the Fitness event of this rep follows
    else
        TRN.stats.repsFitnessOnly = TRN.stats.repsFitnessOnly + 1
    end
end

local function hitStep(owner, weapon)
    local body = bodyOf(username(owner))
    if body == nil then return end
    local okW, w = NR.call(weapon, "getWeight")
    local class = "moderate"
    if okW and finite(w) and w > TRN.HEAVY_WEAPON then class = "high" end
    local okH, hits = NR.call(owner, "getLastHitCount")
    if not okH or not finite(hits) then hits = 1 end
    K.training.event(body, K.training.S_HIT, class, hits)
    TRN.stats.hits = TRN.stats.hits + 1
end

local function treeStep(owner)
    local body = bodyOf(username(owner))
    if body == nil then return end
    K.training.event(body, K.training.S_TREE, "high")
    TRN.stats.trees = TRN.stats.trees + 1
end

-- AddXP(chr, perk, amount) (#2125).
function TRN.onXp(player, perk, amount)
    local ok, err = pcall(xpStep, player, perk, amount)
    if not ok then fail(err) end
end

-- OnWeaponHitXp(owner, weapon, victim, damage, hitCount) (#2193-#2195): the literal hitCount is 1, so
-- the count is owner:getLastHitCount().
function TRN.onHit(owner, weapon, victim, damage, hitCount)
    local ok, err = pcall(hitStep, owner, weapon)
    if not ok then fail(err) end
end

-- OnWeaponHitTree(owner, weapon).
function TRN.onTree(owner, weapon)
    local ok, err = pcall(treeStep, owner)
    if not ok then fail(err) end
end

-- Wiring: the three event hooks, once, at OnServerStarted, on the server only.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if TRN.wired then return end
        TRN.wired = true
        if Events.AddXP ~= nil then Events.AddXP.Add(TRN.onXp) end
        if Events.OnWeaponHitXp ~= nil then Events.OnWeaponHitXp.Add(TRN.onHit) end
        if Events.OnWeaponHitTree ~= nil then Events.OnWeaponHitTree.Add(TRN.onTree) end
    end)
end
