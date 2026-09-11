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
a run that looks green while the thing under test was never loaded. Eight profiles ship:
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
`lua.global TKX_EatHook.version` — each certain to pass IF the mod loaded at all. The `Mods=` order
is LOAD order and is load-bearing here: `TKX_EatHook` is last, so its `item Watermelon` body is
replayed after `TKX_ItemOverride`'s, and the `Calories` that results is the MEASUREMENT, never a
gate; and **`x12-loader.toml`** — slice 12's sessions 2 and 3, PZTestKit + the two loader probes,
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
sides — which the driver records in the artifact.

Use one with `python testing/pzt run --profile <name>` or
`python testing/pzt scenario <test> --profile <name>`; the profile's own fixture wins over a typed
`--fixture` (it is the fixture its `[sandbox]` keys were validated against), and an explicit CLI
flag wins over the profile's `run`/`server`/`client` settings. The full schema is the module
docstring of `testing/pzt/profile.py`; the model, the `-nosteam` copy rule, the missing-mod path
and what was measured are in [`docs/testing/profiles.md`](../../docs/testing/profiles.md).
