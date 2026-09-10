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
a run that looks green while the thing under test was never loaded. Three profiles ship:
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
`recipes.craft MakeCuredMeat` on the server, `item.script Skittles.CuredPork` on the client (that
command is registered client-side only).

Use one with `python testing/pzt run --profile <name>` or
`python testing/pzt scenario <test> --profile <name>`; the profile's own fixture wins over a typed
`--fixture` (it is the fixture its `[sandbox]` keys were validated against), and an explicit CLI
flag wins over the profile's `run`/`server`/`client` settings. The full schema is the module
docstring of `testing/pzt/profile.py`; the model, the `-nosteam` copy rule, the missing-mod path
and what was measured are in [`docs/testing/profiles.md`](../../docs/testing/profiles.md).
