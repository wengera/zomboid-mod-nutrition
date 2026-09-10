# Testing pipeline

Automated integration testing of mods on a **real** dedicated server with
**real** driven clients. Design: [pipeline-design.md](pipeline-design.md)
(layers L0–L4, harness mod + python orchestrator, fragility budget, spikes
S1–S7, roadmap T0–T4). Verified facts and measurements per spike:
[spikes.md](spikes.md).

## `pzt` — the orchestrator (`testing/pzt/`)

Run from the repo root with `python testing/pzt <command>` (or `python -m pzt`
from `testing/`). Requires the local game install (path in `pzt/paths.py`).

| Command | What it does | Cost |
|---|---|---|
| `provision --name default` | Fresh server (fixed sandbox: `Zombies=6` = none, override with `--sandbox K=V`), the `admin` client joins, creates the world and its character, quits cleanly; server stops; snapshot → `testing/fixtures/default/` | ~2.5 min, once per game/mod-set version |
| `boot --fixture default [--hold N]` | Restore the fixture's server world into a fresh run dir and start it | ~14 s |
| `attach --fixture default --server 127.0.0.1:27261 --user admin` | Restore that user's client cache, launch the client, wait until it is in-world (no creation screens), ping it | ~35 s |
| `run --fixture default [--hold N] [--clients a,b]` | boot + attach every fixture client + hold (the test slot) + graceful teardown + `report.json` (timeline, events, collected results); exit code 0 only with zero non-baseline server errors and no client lua errors | ~1 min + hold |
| `scenario <name> [--side server\|client] [--speed N] [--timeout S] [--fixture F]` | run one registered harness test at accelerated time: boot + attach the subject client, `test.list` on the chosen side, RCON `settimespeed <N>`, `test.run <name> <user>`, wait for the result doc, **then the Python evaluator for that name, and only then** `settimespeed 1` + teardown from the `finally` — that order because the evaluator is scenario code that can raise, and a raise must not skip the speed restore (`scenario.py:148-194`); report and artifact are written last (details below) | ~1 min + the test (3 game-days at `--speed 30` ≈ 10 min) |
| `spike S3 S4 S5 S6 S7 [--reloadalllua]` | the design spikes as scripted experiments; S3 boots its own sessions, the rest share one; findings → `runs/spike-*/findings.json` | 2–5 min |
| `doctor` | cold-start checks before booting anything: stray PZ `java.exe` (reported, never killed), ports 27261/27262/27015 free, fixture present and build-matched, workshop index reachable, pytest available; exit 1 on a FAIL | seconds |

Measured evidence that a doc cites as an **M** row is copied at slice close to
`testing/artifacts/<run-id>/` (tracked, JSON only, `.gitattributes` keeps the
blobs byte-identical); the full run directories with logs stay local under
`testing/runs/` (gitignored). Experiment scripts live in `testing/experiments/`
(`_common.py` = the shared boot/ask/save/teardown pattern).

Every invocation gets its own `testing/runs/<cmd>-<timestamp>/` with
`server-stdout.log`, `server/` (cachedir), `clients/<user>/` (cachedirs incl.
the game's `console.txt`) and `report.json` (timeline + events). Fixture
blobs (`fixtures/*/cache/`) and runs are gitignored; `fixtures/*/fixture.json`
records how a fixture was built (build, mods, sandbox, accounts, timings).

### How a driven client is controlled

- **Launch**: JVM started directly (no UAC prompt) with
  `-nosteam -cachedir <dir> -nosound -novoip [-debug] +connect ip:port`.
  Never `-safemode` (7× slower world load). The `admin` account (bootstrapped
  by the server's `-adminpassword`) runs with `-debug`, which lets the logo
  screen be skipped; other accounts sit through the ~20 s logo.
- **Join + character creation**: the `PZTestKit` harness mod (must be in
  the server's `Mods=` — the client reloads Lua with the server's list on
  join) reads `<cachedir>/Lua/pzt-join.txt`, presses CONNECT, and NEXTs
  through spawn/profession/appearance. Restored fixture clients skip creation
  entirely (the character persists server-side).
- **Click to Start**: after loading, `GameLoadingState` waits for a mouse
  click; `pzt` posts one to the client's own window (matched by pid, no
  focus change) until the harness reports `player <user> at x,y,z`.
- **Command bus** (both sides, `pzt/bus.py` ↔ `PZTestKit_Core.lua`): `pzt`
  writes `<cachedir>/Lua/pzt-cmd.txt` (`seq`, `cmd`, `args`), the harness
  executes each seq once (last seq recovered from `pzt-ack.txt` after a Lua
  reset) and answers in `pzt-ack.txt` (`ok:`/`err:` + a string or one-line
  JSON). Shared commands: `ping`, `version`, `state`, `result <name>`,
  `time.snapshot`, `trait.check`, `lua.reload <file>`, and the slice-04 test
  layer's `test.list` (registered names, sorted), `test.run <name> [user]`
  (ack `started` / `unknown` / `already running <x>` / the player-resolution
  error — only `started` leads to a result doc) and `test.status`
  (`{running, name, clock, due, side, samples}`); server: `time.multiplier`,
  `players`, `nutrition.get <user>`, `nutrition.set <user> <field> <v>`,
  `stats.set <user> <stat> <v> …`; client: `quit`, `player.stats`,
  `moddata.set/transmit`, `witness.moddata|nutrition|item`, `item.spawn`,
  `item.tamper`, and the slice-01 experiment commands `nutrition.get`,
  `nutrition.set`, `stats.set`, `item.script <type>`, `item.state <type> <state>`,
  `eat <type> [fraction]` (direct `Eat`, intake arithmetic), `eat.action`
  (queues the real timed action — completes on the server), `sandbox.set`.
  The server owns `Nutrition` and hunger/thirst in MP: client-side writes are
  overwritten within ~1 s (see `docs/vanilla/eating-pipeline.md`).
  Slice-02 lifecycle commands — server: `item.get <user> <type>`,
  `item.set <user> <type> <field> <v>` (+`sendItemStats`),
  `item.age.tick <user> <type>` (`updateAge(true)`),
  `item.freeze <user> <type>`, `item.update <user> <type>` (the cooking
  driver), `perk.set <user> <perk> <level>` (the authoritative one — a
  client-only perk write is overwritten by the server's copy within a
  second); client: `item.age <type> <days>`, `perk.set <perk> <level>`,
  `recipe.evolved <recipe> <base> <ingredient>…`. The server also owns item
  **aging**: `age` was **measured** not to reach the client — not on
  `sendItemStats`, not on `updateAge(true)`, not over an accelerated game day
  (`testing/artifacts/exp02-20260910-030433/`) — while
  `offAge`/`offAgeMax`/`freezingTime` being absent from `ItemStatsPacket` is
  so far only **read off the packet code** (no run has made them differ
  between the two sides). Either way those readings are taken on the server
  bus (see `docs/superpowers/plans/02-notes.md` Q8).
  Slice-03 body commands — server: `stats.get <user>` (one **atomic**
  `TK.bodySnapshot`: stats, moodles, nutrition, weight, max weight, traits and
  the world clock in a single reply, so a sample cannot straddle a tick),
  `sandbox.set <key> <value>` — **the server twin of the client command of the
  same name, and a different thing**: a client flip is local (the admin panel
  guards `getSandboxOptions():set()` with `if not isClient()`,
  `ISServerSandboxOptionsUI.lua:738`, and pushes a copy), while this one *is*
  the live server config, which `getStatsDecreaseMultiplier` reads on the next
  tick — `trait.set <user> <Trait> <add|remove>`
  (`getCharacterTraits():add/remove(CharacterTrait.X)`, with a `held`
  read-back), `player.sleep <user> <true|false>` (`setAsleep` + read-back — the
  flag that picks `updateStats_Sleeping` and `updateCalories`' 0.003 branch),
  `nutrition.applytraits <user>` (`applyTraitFromWeight()` on demand; vanilla
  runs it only every 2000 `updateWeight` calls) and
  `foodtimer.set <user> <v>` (`BodyDamage.healthFromFoodTimer`, the
  `FOOD_EATEN` driver, before/after read-back); client: `stats.get` (the same
  snapshot with no user argument — a client only ever has its own player — and
  a mirror of the last 1 Hz `PlayerStatsPacket`, never a rate),
  `player.walk <dx> <dy> [run]` (queues the game's own `ISWalkToTimedAction`
  onto the square `dx,dy` away, `setRunning` first when `run`; **one attempt by
  ruling**, since the server's copy of a remote player's movement comes from
  this client) and `player.stop` (clears the timed-action queue and unsets
  running, so a half-finished path cannot bleed into the next window). The
  plan's `stats.sample` / `stats.sampler` were **dropped**: sampling is the
  atomic `stats.get` plus Python-side polling, so the cadence lives in the
  experiment script rather than in Lua.
  Slice-05 script-census commands — server only, both reading `ScriptManager`
  (script data is loaded identically on both sides and never synced, so the
  server's copy is the whole answer): `items.count` (no args) →
  `{total, food, byType, foodByModule, fluidDefs}`, plus a conditional
  `fluidDefsError` when `ScriptManager:getAllFluidDefinitionScripts()` is not
  exposed — `fluidDefs` reads `0` in that case and in the "no fluids loaded"
  one, and they are different findings, so the reply says which. It is
  the game's own loaded-item
  list bucketed by `getItemType():toString()` (the `base:food` /
  `base:drainable` ResourceLocation strings, counted raw in `byType` so a
  registry rename is visible rather than silently zeroed) — this is the live
  cross-check for `tools/food_scan.py`, which reads the same definitions off
  `media/scripts/`; and `fluid.script <fluidId>` →
  `{fluidType, fluidTypeRoute, displayName, hasPropertiesSet}` plus the 14 live
  property getters (`HungerChange`, `ThirstChange`, `Calories`,
  `Carbohydrates`, `Lipids`, `Proteins`, `FatigueChange`, `StressChange`,
  `UnhappyChange`, `Alcohol`, `FluReduction`, `PainReduction`,
  `EnduranceChange`, `FoodSicknessChange`) off one
  `FluidDefinitionScript`; any of the **16** members this build does not expose
  — the 14 properties and `getDisplayName` / `hasPropertiesSet` — is listed in
  `missingGetters` rather than left silently absent, which is what keeps
  `hasPropertiesSet: false` (true of 10 of the 61 fluids) distinguishable from
  "not exposed"; and a miss reports every id the list did yield. `fluidTypeRoute` is there because
  `getFluidTypeString()` answers for only 34 of the 61 definitions — it is
  empty for every fluid that also has a built-in `FluidType` enum constant
  (`Water`, `Beer`, `Coffee`, `Blood`, `Petrol`, …), so the command falls back
  to stringifying `getFluidType()` and says which route named the fluid.
  Neither command returns per-item macros, and no third one can: the food
  script `Item` exposes **no** macro getter to Kahlua — `item.script` already
  measured that `getCalories` / `isCalories` / the public field `calories` all
  fail on the script object (same for carbohydrates/lipids/proteins) even
  though the jar keeps them as public fields that `Item.InstanceItem` reads
  directly. That is why `item.script` cannot answer the four macros and the
  live macro read-back goes through the server's `item.get` on an RCON-spawned
  **instance** instead. Fluid **containers** have no live route at all —
  `Item` exposes no component accessor — so only fluid **definitions** can be
  read back this way. Driven by `testing/experiments/s05_food_scan.py`, which
  pairs the census with ten field-for-field spot checks against RCON-spawned
  instances (`docs/vanilla/food-dataset-notes.md`).
  Slice-05 drink probe — server only, for the same reason every other intake
  command is: an MP client never calls `DrinkFluid` at all
  (`LuaTimedActionNew.complete @31 L162` skips the Lua `complete` when
  `GameClient.client`, and `ISDrinkFluidAction`'s own hooks are
  `if not isClient()` / `if isServer()`), so a client-side probe would read the
  1 Hz mirror rather than the store. `drink <user> <fullType> [fraction]`
  (default fraction `1.0`) is the shipped drink action's payload with the timed
  action taken off: it finds the user, picks an instance, reads the container,
  makes **one** `DrinkFluid` call and reports both stores on either side of it.
  * **Route**: `IsoGameCharacter:DrinkFluid(InventoryItem, f, false)` — the
    same overload and the same argument shape `ISDrinkFluidAction:updateEat`
    (`:109–120`) ends in, followed by the same `syncItemFields()` (`:117`).
    Measured on 42.20.4: Kahlua's overload dispatch takes it as written, so the
    command's `(FluidContainer, f, false)` fallback was never exercised — it is
    attempted only when the first route cannot have applied anything (the
    member was absent, or it raised with the container's `getAmount()`
    untouched), never after a partial application, and `route` names whichever
    one answered. `useUtensil` is `false` because the action always passes
    `false` and the jar never reads the argument.
  * **Which instance**: the **fullest**, ties broken by the highest id — not
    `item.get`'s `getFirstTypeRecurse`, which answers the *first* match and
    would re-select an already-drained can on a second probe of the same type.
    The candidate list (`id`, `amount`, `capacity` per instance) and the pick
    travel in the reply, and `finder` says whether the list route
    (`getAllTypeRecurse`, one argument, as `ISBuildUtil.lua:201` calls it) or
    the `getFirstTypeRecurse` fallback answered.
  * **Drift-free by construction**: both snapshots (`TK.nutritionSnapshot` +
    `BodyDamage.getHealthFromFoodTimer` + the container's
    amount/capacity/filledRatio) are taken **inside the one Lua call**, on
    either side of the single Java line, so they are the same game tick;
    `worldAgeBefore` / `worldAgeAfter` and `delta.worldAgeHours` are in the
    reply so that is checked rather than asserted. A `stats.get` /
    `nutrition.get` bracket *around* the command is the independent outer
    reading and it does carry the passive drain.
  * **Reply**: `{user, fullType, fraction, finder, selectionRule, candidates,
    selected, selectedFullType, primaryFluid, primaryFluidRoute,
    fluidDisplayName, containerProperties, predictedNutrition, predictedStats,
    predictedFoodTimer, worldAgeBefore, before, after, worldAgeAfter, delta,
    route, drinkFluidReturned, syncItemFields, syncItemFieldsReturned}` — plus
    `routeAttempts` / `error` when a route failed, `containerPropertiesError`
    when the container would not answer `getProperties()`, and
    `syncItemFieldsError` if that last call raised. `syncItemFields` is the
    **presence/ran flag** for `InventoryItem:syncItemFields()` (it is void, so
    `syncItemFieldsReturned` is `nil` on 42.20.4) and `drinkFluidReturned` is
    what the `DrinkFluid` overload itself returned. `containerProperties` is the
    container's **litres-weighted** aggregate (`getProperties()`, all fifteen
    `SealedFluidProperties` getters), read **before** the drink because an
    emptied container recalculates to all zeroes.
  The `fraction` is a share of the container's **current contents**, not of its
  capacity (`removeFluid(getAmount() * f, true)`): on a full can `f = 1` empties
  it and `f = 0.5` halves it, but a *second* `0.5` would take half of what is
  left. Driven by `testing/experiments/s05b_drink_probe.py`.
  Slice-06 recipe commands — server only, and in their own file
  (`server/PZTestKit_Server_Recipes.lua`, which sorts *after*
  `PZTestKit_Server.lua` because `.` < `_`, so `TK` is loaded when it runs);
  same `ScriptManager` reasoning as the slice-05 census, and the live
  cross-check for `tools/recipe_scan.py`. `recipes.count` (no args) →
  `{craft, evolved, legacy, unique}` — the sizes of `getAllCraftRecipes()`,
  `getAllEvolvedRecipesList()`, `getAllRecipes()` (the pre-B42 `recipe`
  blocks) and `getAllUniqueRecipes()`, with `missingAccessors` naming any the
  build does not expose, because "0" and "no such accessor" are different
  findings (the `fluidDefsError` rule). Measured on 42.20.4:
  **969 / 63 / 0 / 0**. `recipes.evolved <name>` → one `EvolvedRecipe`'s
  `getBaseItem` / `getResultItem` / `getMaxItems` / `isCookable` /
  `getMinimumWater`, plus `items` (the labels
  `getPossibleItems()` yields), `itemFullTypes` and `ingredientCount` —
  `getPossibleItems()` is the values of the recipe's own `itemsList`, which
  the *item* scripts fill (`EvolvedRecipe = Salad:10` on a food item registers
  it against the `Salad` recipe), so its size is the ingredient count.
  `recipes.craft <name>` → `getCategory` / `getTime` / `getInputCount` /
  `getOutputCount` plus one row per output line with `amount`
  (`getIntAmount()`), `resourceType`, `originalLine` and the items it resolves
  to (`items`, `itemFullTypes`, `itemCount`). `originalLine` is the recipe
  file's own trimmed text for the line, so it can be compared against the
  scanner's `outputs[].raw` without either side having to parse the other's
  model. Three details worth knowing before reading a reply:
  * **Both name spellings work.** Every lookup asks the accessor for both
    `<Name>` and `Base.<Name>` and reports the pair as `lookup`
    (`askedAnswered` / `alternateAnswered` / `route`). Measured: both answer,
    for craft and evolved alike — `ScriptBucketCollection.getScript` resolves
    a bare name against module `Base` and a dotted one against its prefix
    (`@45–@99 L78–L96`), the same tolerance slice 05 measured on
    `getFluidDefinitionScript`.
  * **A getter has three outcomes, not two.** `missingGetters` (the build does
    not expose it), `getterErrors` (it is there and the *call* raised) and
    `nullGetters` (it answered with nothing) are separate lists. The middle
    one exists for `CraftRecipe.getTime`, which is overloaded (`()I` and
    `(IsoGameCharacter)I`): each getter runs under its own `pcall`, so a
    dispatch to the arity we did not ask for costs that one key rather than
    the whole reply. On 42.20.4 Kahlua takes the no-argument overload and all
    three lists came back empty on all fifteen probes.
  * **`getInputCount()` is not the number of input *lines*.**
    `CraftRecipe.LoadIO @218–@317` attaches a `-` (or `+`) prefixed line
    inside an `inputs` block to the *preceding* input as
    `consumeFromItemScript` / `createToItemScript` and adds it to `ioLines`,
    never to `inputs`; `getInputCount()` is `inputs.size()` (`@0–@7 L257`).
    So a recipe written with a fluid sub-line answers one less than its
    script has lines. Driven by `testing/experiments/s06_recipes.py`.
- **Results**: `TK.result(name, table)` writes `<cachedir>/Lua/pzt-results/
  <name>.json` as one complete JSON object (that is the ready signal — the
  writer's extension allowlist rules out `.ready` markers); `pzt` collects
  them into `report.json` and `bus.wait_result()` blocks on one.
- **Observation**: the client's `console.txt` is tailed for
  `STATE: enter …` transitions and `PZTK:` harness lines.

### Harness layout (`testing/PZTestKit/PZTestKit/`)

`mod.info` + `42/mod.info` (B42 reads the one inside the version folder),
`42/media/lua/shared/PZTestKit_Core.lua` (global `TK`: KV files, JSON, command
bus, results, shared commands), `shared/PZTestKit_Test.lua` (slice 04: the test
layer — game-time scheduler, test registry, the `test.*` bus commands; shared so
either side can host a test, and named `_Test` so it loads after `_Core`, since
Lua files in one folder load alphabetically), `server/PZTestKit_Server.lua` (bus
polling on `OnTick`, `OnClientCommand` witness replies),
`server/scenarios/PZTestKit_Scenario_{Smoke,Nutrition}.lua` (the registered
tests — the loader walks the folder recursively, as vanilla does for
`media/lua/server/Farming`), `server/PZTestKit_Server_Recipes.lua` (slice 06:
`recipes.count` / `recipes.evolved` / `recipes.craft`; a separate file for the
same reason `PZTestKit_Client_Body.lua` is one, and it sorts after
`PZTestKit_Server.lua` — `.` < `_` — so `TK` exists when it loads),
`client/PZTestKit_Client.lua` (auto-join, client
commands, `OnServerCommand` witness comparison) and
`client/PZTestKit_Client_Body.lua` (slice 03: the client mirror — `stats.get`,
`player.walk`, `player.stop`; a separate file loaded into the same client Lua
state, registering into the same `TK` table, purely so two slices' edits do not
collide).

### Scenarios and the test layer

A **scenario** is a Lua test that runs on the world's own clock — days of game
time in minutes of wall time — and hands its samples to a Python evaluator.
`python testing/pzt scenario <name>` is the runner; `PZTestKit_Test.lua` is the
layer the tests are written against.

- **Registration**: `TK.test(name, spec)` with
  `spec = { timeoutMin = <game minutes>, player = <username>, needsPlayer = <bool>,
  run = function(t) … end }`. `timeoutMin` is the layer's own backstop (a
  `t:done(false, "test timeout")` armed at start); `needsPlayer = false` is the
  only way to register a test that runs without a subject.
  **Leave the backstop a clear margin above the finisher.** It is armed *first*, so it
  holds the lowest `seq` and **wins a same-minute tie**: a test that finishes at exactly
  `timeoutMin` is timed out instead, and reports the anonymous `detail: "test timeout"`.
  The nutrition scenarios finish at `RUN_MIN + 1` and set `timeoutMin = RUN_MIN + 30`
  (`PZTestKit_Scenario_Nutrition.lua:160-162`); `smoke_clock` finishes at 20 with a
  backstop of 30.
- **The clock is game minutes, not wall seconds.** `Events.EveryOneMinute`
  advances `TK.tests.clock` and dispatches every callback whose minute has come,
  sorted by scheduled minute and then by insertion order (`table.sort` is not
  stable, so the layer carries its own `seq`). It hooks once — `reloadlua`
  re-runs the file, and a second `Add()` would advance the clock twice a game
  minute and halve every rate fitted against it. Measured at **1.000 ticks per
  game-minute** on the dedicated server at `settimespeed 30` (all three slice-04
  runs).
- **The context `t`**: `t:at(minutes, fn)` schedules once; `t:every(minutes, fn)`
  repeats (re-armed *before* `fn` runs, so one raising callback cannot silently
  stop a three-day sampler); `t:eventually(pred, budgetMinutes, label)` polls
  `pred` once a game minute under its own `pcall` and ends the test with a
  labelled timeout when the budget runs out (that `pcall` catches ordinary Lua
  errors in the predicate, **not** a call to a Java member the build lacks — see
  the Java rules below; `smoke_clock` runs one `t:eventually` on every smoke run,
  so the re-arm path is exercised rather than assumed); `t:assert(cond, msg)` and
  `t:near(a, b, tol, msg)` record failures; `t:sample(tbl)` appends `tbl` to
  `t.samples` after stamping `gameMinute`, `worldAge`
  (`getGameTime():getWorldAgeHours()`, itself read through `TK.call`, so on a build
  that does not expose it the key is simply absent from the sample instead of the
  scheduler dying) and `wall` — the `(worldAge, wall)` pair is
  what the Python side fits rates against, and what makes the harness's own
  cadence measurable without a second bus round-trip; `t:log(msg)` prefixes the
  game minute; `t:done(pass, detail)` finishes now (`pass` is ANDed with "no
  failures recorded").
- **`t.player`** is the subject, resolved **by username** out of
  `getOnlinePlayers()` — there is no `getPlayer()` on a dedicated server — from
  `test.run <name> [user]`, defaulting to `spec.player` and then `admin`. The
  client must therefore be attached even for a server-side test.
- **Result doc**: `t:done` writes `TK.result("test_" .. name, …)` →
  `<cachedir>/Lua/pzt-results/test_<name>.json` with `test`, `pass`, `detail`,
  `failures`, `samples`, `log`, `gameMinutes`, `player`, `side`, `startedWall`,
  `startedWorldAge`, `endedWorldAge` — **plus the envelope `TK.result` stamps on
  every result doc in the harness** (`PZTestKit_Core.lua:85-87`): `name` (the doc's
  own name, `test_<name>`), `side`, `t` (wall-clock ms at write) and
  `complete: true`. `t` is load-bearing, not a timestamp for the reader: with
  `startedWall` it is the pair `scenario.cadence()` fits the harness clock against
  (`scenario.py:56`), so a side without `getTimestampMs()` produces no `cadence`
  block at all. `bus.wait_result` blocks on the file.
- **Same Java rules as the rest of the harness**: every Java member goes through
  `TK.call` (Kahlua's "tried to call nil" escapes `pcall` and would kill
  `EveryOneMinute` for the whole side), no `goto`, and never `%d` on a Lua number.
- **Shipped scenarios** (all under `server/scenarios/`, all server-side because
  the server owns `Nutrition`): `smoke_clock` — the scheduler's own test, ~20 game
  minutes, asserts only that the clock ran, that samples landed and that one
  `t:eventually` polled to a hit; `nutrition_3day_gain`
  and `nutrition_3day_fast` — three game-days at 4 000 kcal/game-day (two +2 000
  doses 12 game-hours apart, under the 3 700 `setCalories` clamp) and at no intake,
  sampled hourly, hunger and thirst pinned to 0 after every sample. Results:
  [`../vanilla/nutrition-core.md`](../vanilla/nutrition-core.md) § Verified on server.
- **The runner** (`pzt/scenario.py`): `--side server|client` (default server),
  `--speed N` (default 30), `--timeout S` (seconds to wait for the result doc,
  default 900), `--fixture F`, `--user U` (default `admin`). It refuses a name that
  `test.list` does not report on that side, and any `test.run` ack other than
  `started`, rather than paying the full result timeout for it. A **refused
  `settimespeed`** ends the run there too, with that reason: the world would still be
  at 1×, so a three-game-day test could not finish inside any timeout worth waiting
  for. `settimespeed` is restored in a `finally` — a world change must not outlive the
  run — and always through the broadcast admin command (spike S5). Ctrl-C is caught,
  not propagated: it tears down as usual and still writes the report and artifact,
  as `RESULT: FAIL: interrupted`.
  **`--side client` is wired end to end but has nothing to run yet** — the test layer
  is in `shared/`, `test.list` / `test.run` answer on the client bus, and the runner
  will drive it; there is simply no client-side scenario registered (all three live
  under `server/scenarios/`, because the server owns `Nutrition`). It exists for the
  convergence readings, where the mirror IS the subject.
- **What a run writes**: `runs/scenario-<ts>/report.json` (timeline, cadence, the
  result doc, the evaluation, `faults`, the `traceback` of anything that ended the run
  early, server errors, client events) and `runs/scenario-<ts>/scenario-<name>.json` —
  the result doc plus
  `fixture`/`build`/`side`/`user`/`speed`/`result`/`cadence`/`evaluation`/`faults`/`server_errors`,
  self-contained, and the file copied byte-for-byte into `testing/artifacts/`. The
  report is written first and unconditionally; a failing artifact write is a warning,
  not a lost run. Last line is `RESULT: PASS|FAIL[: reason]   (report: …)`.
- **The verdict is the test AND the evaluator AND a clean session.** Exit code 0 needs
  the harness test's own `pass`, the evaluator's ok, **and** no environment fault:
  missing mods, non-baseline server error lines, or a client Lua error each turn the
  RESULT into `FAIL: <reason with its count>`, mark the timeline, and land in `faults`
  in both the report and the committed artifact. That is the same check `pzt run`
  applies, from the same place (`session.fault_reasons`, called after teardown so the
  server's closing log lines count). It matters more here than there: a scenario
  writes committed evidence, and a test whose Lua died somewhere the scheduler
  swallowed can still write `pass = true`.
- **Evaluators** are Python: `EVALUATORS[name] = fn(doc) -> (ok, detail)`, registered
  by importing the module at the bottom of `scenario.py`
  (`scenarios_nutrition.py` for the two nutrition scenarios — it integrates the
  documented weight model over the run's own calorie trace against a
  `max(15 % of the predicted delta, 0.05 kg)` tolerance, and fails the run outright
  if any sample is dead). A name with no evaluator passes on the harness verdict alone.
- **`cadence` / `cadence_suspect`**: every run fits the harness clock against the
  world clock and the wall clock (`ticks_per_world_min`, `world_min_per_wall_s`,
  `ticks_per_wall_s`). `ticks_per_world_min` outside 0.95–1.05 sets
  `cadence_suspect` and prints a warning: the run still reports, but everything it
  scheduled in game minutes and every rate it fitted per game-hour was read off a
  clock that was not keeping time.

### Server side

`pzt/server.py` seeds `Server/<name>.ini` (ports, RCON, `Mods=`, `Open=true`,
`UPnP=false`), installs mods into the cachedir's `mods/` (harness mods from the
repo, anything else copied from the Steam workshop folder by `pzt/mods.py` —
under `-nosteam` the game searches nothing else), starts
`zombie.network.GameServer -nosteam -adminpassword …`, waits for
`*** SERVER STARTED ****`, classifies error-shaped log lines against the
vanilla-noise baseline (stack frames attach to their head line), and stops
with `quit` on stdin (RCON `quit` as fallback).
