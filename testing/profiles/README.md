# testing/profiles

One TOML file per *named combination under test*: which golden fixture to restore, which mods
go into `Mods=` (and where each one is copied from — the repo for the harness, a workshop item
or an explicit folder for everything else), which `SandboxVars` to override, and which bus
probes have to answer before the session counts as the session that was asked for. A profile is
**text only** — never a blob: the fixture and the mods it names stay where they already live
(`testing/fixtures/<name>/cache/`, gitignored — the tracked `fixture.json` beside it records how
the fixture was built; `steamapps/workshop/content/108600/`, read-only), and each run overlays a
*restored per-run copy* of the fixture, so nothing here mutates either. Everything a
profile asks for is resolved and validated before a single process starts (`testing/pzt/profile.py`),
because the game's own reaction to a mod it cannot find is a WARN and a clean boot (spike S3-A) —
a run that looks green while the thing under test was never loaded. Eleven profiles ship:
**`mod-under-test.toml`** — PZTestKit + KeenPerception (workshop `3685392864`) on `default` with
`DayLength = 1`, the T1 acceptance case and the template for slices 09–11, whose `[[verify]]`
probes read `trait.check` back on both sides. **Copy its `[sandbox]` with care**: `DayLength = 1`
is fine for `pzt run`, which does not touch the clock, but it breaks the game-minute cadence under
`pzt scenario --speed` — keep `24 × speed / day_minutes ≲ 8`, so on a 15-minute day that is
`--speed 5`, not 30 (`docs/testing/profiles.md` § The cadence ceiling); and **`missing-mod.toml`** — the regression for the
failure mode, a mod named in `Mods=` that `copy = false` deliberately places nowhere, which must
FAIL before a client is ever launched; and **`teardown-longtermpreservation4220.toml`** — slice 09's
teardown subject, PZTestKit + `SKITTLE_LongTermPreservation4220` (workshop `3774789651`, folder
`LongTermPreservation4220`) on `default` with **no `[sandbox]`** so DayLength stays the fixture's 4,
whose `[[verify]]` probes read the mod's own scripts back — `items.count` and
`recipes.craft MakeCuredMeat` on the server, `item.script Skittles.CuredPork` on the client
(registered client-side only at the time; slice 09 added the server half); and
**`teardown-simplestatus.toml`** — slice 10's
teardown subject, PZTestKit + `simpleStatus` (workshop `2867431511`, folder `SimpleStatus`) on
`default` with **no `[sandbox]`** either, whose `verify` **shipped empty by ruling** at `a42c8b4` —
the mod ships no scripts and no bus-readable state — and **gained one tier-(a) row in `291f977`**:
client `text.get IGUI_SS_BARTITLE_HAPPY` expecting `"Happiness"`, which cannot pass unless the
mod's translation tree loaded, because a translation miss returns the key itself. The mod's own
client-side console print at join, grepped from the run's `clients/admin/console.txt`, is kept
beside it; and **`teardown-autocook.toml`** —
slice 11's teardown subject, PZTestKit + `AutoCook` (workshop `3388721641`, folder `AutoCook` — the
one pass where the declared id and the folder agree) on `default` with **no `[sandbox]`** either,
whose two `[[verify]]` rows are both **client** and both read load-time state, one per subsystem
that loads a mod split across two media trees: `text.get UI_AutoCookMode` for the Translator's
merge of `common/`'s JSON, and `witness.moddata player:admin *` for the modData key the Lua require
chain writes. A hit on the second proves `common/` ran and that the chain completed — **not** which
copy of `AutoCook.lua` won the collision, which is `lua.global`'s question; and
**`x12-overrides.toml`** — slice 12's session 1, and the first profile whose subjects are OURS:
PZTestKit + `TKX_ItemOverride` + `TKX_Nutrient` + `TKX_EatHook` (the three TKX mods each a `path =` into
`testing/experiments/`, not a workshop item) on `default` with **no `[sandbox]`** so DayLength stays
the fixture's 4, whose three `[[verify]]` rows are one tier-(a) gate per mod — server
`item.script TKX.FibreBar`, server `lua.global TKX_Nutrient.version`, client
`lua.global TKX_EatHook.version` — each certain to pass IF the mod loaded at all. The loader
announces mods in `Mods=` order, **but script bodies do not replay in it**: they replay in sorted
stored-script-path order with per-key last-wins, `Mods=`-independent (sessions 4 and 5,
`x124-20260911-035819` / `x125-20260911-042055` — see `docs/modding/item-overrides.md`
§ Load order between two mods). The `Calories` that results is the MEASUREMENT, never a gate.
**Superseded comment, frozen with the artifacts:** this profile's own header comment
(`x12-overrides.toml:2`, "`Mods=` order is LOAD order, and it is load-bearing here: `TKX_EatHook`
is LAST …") is **wrong for script bodies** and is left unedited because it is the input `x121`
was measured against — read it as the prediction the run falsified, and cite `x125-20260911-042055`
for the rule; and **`x12-loader.toml`** — slice 12's sessions 2 and 3, PZTestKit + the two loader probes,
`TKX_LoaderVersion` (folder `testing/experiments/tkx-loader-probe`, whose name matches neither id
the folder declares — `mods.mod_id_of` picks the newest version dir's) and `TKX_CommonOnly` (a
`42.20/` carrying only a `mod.info`, the whole payload under `common/`), on `default` with **no
`[sandbox]`** either, whose single `[[verify]]` row is client `lua.global TKX_LoaderVersionTree` —
that file has no `common/` counterpart, so it loads under EITHER merge direction, which is exactly
what makes it a gate and not a discriminator. `TKX_CommonOnly` is deliberately UNGATED: whether a
version dir with no `media/` still lets `common/` load is the measurement, and a measurement is
never a `[[verify]]` row; and **`x12-order.toml`** — slice 12's session 4, PZTestKit +
`TKX_ZWatermelon` + `TKX_ItemOverride` + `TKX_EatHook` on `default` with **no `[sandbox]`** either.
It exists because session 1 read `Base.Watermelon` at **111** — the body of the mod FIRST in
`Mods=`, not the 777 of the one last in it — so the surviving hypothesis is that script bodies are
replayed in an order that is not `Mods=` order, and `TKX_EatHook` sorts before `TKX_ItemOverride`.
`TKX_ZWatermelon` separates the two rules by sorting **last** of the three alphabetically while
sitting **first** of the three in `Mods=`; its `Calories = 999.0` is the reading. Two tier-(a)
`[[verify]]` rows gate the two mods that can be gated — server `item.script TKX.FibreBar` and
client `lua.global TKX_EatHook.version`. `TKX_ZWatermelon` is deliberately UNGATED: it ships no Lua
and no new item, the second `item Watermelon` body it does ship is the measurement, and the
obvious-looking `item.script Base.Watermelon` row would pass with the mod absent because vanilla
defines Watermelon. It is gated at tier (c) instead — folder copied, `mods_not_found` empty on both
sides — which the driver records in the artifact (`f_tier_c`). **Superseded comment, frozen with
the artifact:** `x12-order.toml:11` reads the 999 arm as "alphabetical-by-id replay"; session 5
showed the sort key is the **stored script path** (**C**, `ScriptManager$38.compare` /
`ScriptManager.searchFolders`) and that id, folder name, script path and `mod.info` display name
all sort identically in every boot we ran — so 999 licenses "sorted and `Mods=`-independent", not
"by id". Cite `x125-20260911-042055` and `docs/modding/item-overrides.md` § Load order, not the
comment; and **`x12-order2.toml`** — slice 12's session 5,
the SAME four mods as `x12-order` in a different `Mods=` order: PZTestKit + `TKX_ItemOverride` +
`TKX_ZWatermelon` + `TKX_EatHook` on `default` with **no `[sandbox]`** either, and the same two
tier-(a) rows. It exists because sessions 1 and 4 each read a number that TWO rules predict —
both times the winning body belonged to the mod that was simultaneously FIRST in `Mods=` and
alphabetically LAST — so "alphabetical-last wins" and "first-in-`Mods=` wins" (bodies replayed in
reverse `Mods=` order) were confounded by the orders themselves. Moving `TKX_ItemOverride` to the
front and `TKX_ZWatermelon` to the middle makes the three surviving rules name three different
`Calories`: **999** ⇒ alphabetical-last, **111** ⇒ first-in-`Mods=`, **777** ⇒ `Mods=`-last (out
twice already, so a 777 reopens both earlier sessions). `TKX_ZWatermelon` is UNGATED here for the
same reason and gated at tier (c) by the driver; and **`x12-pcall.toml`** — slice 12's session 6,
the smallest profile in the slice: PZTestKit + `TKX_PcallProbe` (a single `shared/` file,
`path = "testing/experiments/TKX_PcallProbe"`) on `default` with **no `[sandbox]`**, so DayLength
stays the fixture's 4 and `EveryOneMinute` fires every 3.75 s. It exists to measure the library's
own standing rule — "a Kahlua nil call escapes `pcall` and kills the whole handler", the reason
`TK.call` and every `tkxCall` guard exist — which rests on a run with no committed artifact while
the jar reads the other way twice over (`KahluaThread.pcall`'s try covers the nested `luaMainloop`;
`Event.trigger` calls each callback through `LuaCaller.protectedCallVoid` inside a per-iteration
`catch (Throwable)` that continues the loop). Four handlers register on one event: a counter, then
`pcall` on a global that is never defined, then a second counter BEHIND it, then `pcall(error,
"boom")` as the control. Its single tier-(a) row is client `lua.global TKX_P.version` — assigned in
the table constructor on the file's first line, so it answers 1 the moment the file has run at all,
whatever the handlers do. The other eight fields are the measurement and never gated, and the
SERVER side is ungated on purpose: the file is `shared/`, so whether the server VM runs it too is
itself a reading (`TKX_P.side`) rather than a boot requirement; and **`x12-raise.toml`** — slice
12's session 7, the follow-on `x12-pcall` earned: PZTestKit + `TKX_RaiseProbe` (a single `shared/`
file, `path = "testing/experiments/TKX_RaiseProbe"`) on `default` with **no `[sandbox]`** either.
Session 6 measured `pcall(<nil>)` and found it **catches** on both sides — so nothing raised, and
the standing rule's SECOND half ("kills the whole handler") went untested, as did the NESTED shape
`pcall(function() SomeNil() end)`, where the raise comes a frame deeper inside the nested
`luaMainloop`. This profile's four handlers close both: a counter, the nested-pcall shape, an
**UNGUARDED** `TKX_DefinitelyNilThree()` with a tail counter after it, and a counter registered
BEHIND the raising handler. `raw_tail` staying at `"0"` while `behind` advances is the reading —
the raise aborts its own handler's body and `Event.trigger` runs the rest of the chain. Its single
tier-(a) row is client `lua.global TKX_R.version`, for the same constructor-line reason, and the
server side is ungated for the same `shared/` reason; a raise in a mod's handler must not fail the
boot, and if it does, that is the session's first reading rather than a profile error.

Use one with `python testing/pzt run --profile <name>` or
`python testing/pzt scenario <test> --profile <name>`; the profile's own fixture wins over a typed
`--fixture` (it is the fixture its `[sandbox]` keys were validated against), and an explicit CLI
flag wins over the profile's `run`/`server`/`client` settings. The full schema is the module
docstring of `testing/pzt/profile.py`; the model, the `-nosteam` copy rule, the missing-mod path
and what was measured are in [`docs/testing/profiles.md`](../../docs/testing/profiles.md).
