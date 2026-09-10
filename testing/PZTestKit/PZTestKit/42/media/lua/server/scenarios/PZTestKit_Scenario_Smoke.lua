-- smoke_clock: the scheduler's own test. No nutrition claim is made here -- it only proves
-- that Events.EveryOneMinute drives TK.tests' game-minute clock on the DEDICATED SERVER, that
-- a repeating t:every fires, and that a result doc lands in pzt-results/ within the run.
--
-- Server-side on purpose (and under server/scenarios/, which the mod loader walks recursively
-- the same way it walks vanilla's media/lua/server/Farming): the server owns Nutrition, so the
-- calorie read has to be taken here to mean anything. `t.player` is the server's IsoPlayer for
-- the account named by `test.run <name> [username]` (default "admin").
--
-- The assertion is ">= 3 samples at minute 20" rather than "== 4": within one game minute the
-- due callbacks run in the order they were scheduled, and the minute-20 finisher was armed
-- before the minute-20 sample, so the fourth sample is still pending when it reads #t.samples.
--
-- This is also the only live exercise of t:eventually in the shipped scenarios, deliberately:
-- the helper's whole point is the re-arm path (poll once a game minute until the predicate holds
-- or the budget runs out), and a path that never runs is a path that is not known to work. It is
-- cheap here -- this test is ~65 s of wall clock -- and it fails loudly if the re-arm ever breaks
-- again, instead of that breakage surfacing as an anonymous timeout in a ten-minute nutrition run.

TK.test("smoke_clock", { timeoutMin = 30, run = function(t)
    t:log("smoke_clock: sampling calories every 5 game minutes")
    t:every(5, function()
        -- TK.call, not t.player:getNutrition():getCalories(): a missing Java member is
        -- "tried to call nil", which pcall does not catch and which would kill EveryOneMinute
        -- for the whole side (slice 01, exp01-20260909-235420).
        local _, n = TK.call(t.player, "getNutrition")
        local _, cal = TK.call(n, "getCalories")
        t:sample({ calories = cal })
    end)
    -- Must hold on any healthy server, with room to spare: the sampler above lands its second
    -- sample at game-minute 10, so the poll is false at minutes 1-9 (that is the re-arm being
    -- exercised) and true by minute 10 or 11 depending on which of the two callbacks that minute
    -- sorts first -- either way well inside the 15-minute budget, and inside this test's own
    -- 20-minute finisher. Pure Lua on t.samples, so no Java member is touched from the predicate.
    t:eventually(function() return #t.samples >= 2 end, 15, "second sample")
    t:at(20, function()
        t:assert(#t.samples >= 3, "expected >= 3 samples, got " .. tostring(#t.samples))
        t:done(true, "clock ok")
    end)
end })
