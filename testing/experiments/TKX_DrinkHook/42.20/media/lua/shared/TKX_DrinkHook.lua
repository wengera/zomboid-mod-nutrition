-- TKX_DrinkHook -- X13 state table. Shared on purpose so BOTH Lua states define it; the
-- per-side counters the run reads live in global modData "TKX_Drink" (see the side files).
TKX_DrinkHook = { version = 1, updateEat = 0, complete = 0 }
