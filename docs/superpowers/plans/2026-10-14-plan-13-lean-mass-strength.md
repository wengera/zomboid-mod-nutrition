# Plan 13: Lean-mass Strength and body-composition traits — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Strength level a reading of the character's general strength: lean mass, a trained neural factor and an innate factor, with the shown level linear in strength and level 10 at 4 years of perfect training (spec § 2, ruling 13-45). Vanilla Strength XP becomes a training signal. Lean mass grows only when the signal, protein and energy act together, under the fitted growth law of point T. The weight and strength traits describe body composition: they are offered at creation for points, set the starting body, and switch in play from three daily axes. Nothing changes while a player is offline.

**Architecture:**
- **One constants table.** `K.strength.DEFAULTS` in `NR_Kernel_Strength.lua` holds every fitted and game-choice constant of the growth law, the energy gate and the lean partition, and in a second block those of the strength model (the level, N0, T). Its values are point T's (`compact_T.json` "chosen") under the oracle's own key names. `K.strength.params(sv)` merges the sandbox options over it once per change. Every kernel function takes that table as `P`. Nothing else in the mod restates a point-T number.
- **The kernel** (pure, lupa-tested, one statement a line):
  - `K.strength`: the bio scale (the growth law's FFMI coordinate) and the shown strength level with the neural factor T and the innate factor N0 (ruling 13-45), the signal, the gates, growth, regain, detraining, the peak, the day orchestration, the XP capture arithmetic and the params guard;
  - `K.partition`: the surplus and deficit lean arms with the labile lean `lx` (the old lean-gain product is removed);
  - `K.body`: the creation body table (`K.body.create`) and the new `K.body.new`;
  - `K.traits` (new file `NR_Kernel_Traits.lua`): the fat, muscle and thinness axes with damping.
- **The server:**
  - `NR_Server_Metabolism`: the day close (once per online game day), the calendar pause, first sight from held traits;
  - `NR_Server_Strength`: the `AddXP` capture, the level write with the level-9 park and BeyondTen, the per-minute re-assertion and carry;
  - `NR_Server_Weight`: the weight slot and the § 8 trait writes (the vanilla band refresh is retired);
  - `NR_Server_Creation` (new): the `OnNewGame` creation handler with pick validation;
  - `NR_Server_Training` is deleted (its whole content was the resistance side).
- **Content:** `common/media/scripts/NR_Traits_Body.txt` restates 10 trait blocks; translations; 34 sandbox options.

**Tech Stack:**
- Lua 5.1 (Kahlua) kernels, one statement a line;
- Python tests on lupa 2.8, the tracked Python oracle under `testing/tests/kernel/`;
- `testing/pzt` and `testing/experiments/xlib.py` for the live checks.

**Spec:** `docs/superpowers/specs/2026-10-14-lean-mass-strength-design.md` (approved by Angus, 2026-10-14). The fit record is `docs/superpowers/research/2026-10-14-strength-redesign/refit/`.

## Global Constraints
- **CLAUDE.md governs.**
  - § 3: every gate a commit's paths trigger, ending at zero or green; the full `claims_check` after any commit that touches `mod/`, `tools/` or a file the register points into.
  - § 4: claims and science rows, minted in the commit that lands their evidence.
  - § 5: every live step, from `pzt doctor` and the 12 GB memory check to the foreground wait and the frozen driver.
  - § 6: process, lanes, models, rulings and pathspec commits.
- **The `mod/` lane is serial.** Tasks 3 to 18 edit `mod/` one at a time, in order. Task 2 is a pure-kernel task and runs in a worktree, reaching `main` by the controller's cherry-pick after its `Task 2: complete` line (§ 6, ruling 13-40); Task 2b, Task 23 and the live tasks' libs run in the docs lane beside the `mod/` lane, on disjoint files. No live boot overlaps an offline `mod/` edit (§ 5), except Tasks 0 and 1, whose profiles load no `mod/` file (§ 5's reason is that the boot loads the whole tree; ruling 13-39).
- **The order** is 0 → 1 → (2, 2b, 3, 4) → 5 → … → 18 → 19 → 22 → 23 → 24. Task 5 waits for Tasks 1, 2 and 2b (it imports Task 2's `strength_model` and Task 2b's `strength_level`, and labels `xpPerSet` with Task 1's run id). A close-wave change to a code path a live run measured is re-smoked or named as a skew note (ruling 13-39).
- **Refactor heavily as you go** (Angus, 2026-10-12). Each code task names its refactor scope, and each review judges structure and performance beside correctness.
- **No backward compatibility.** The mod is unreleased. Removed fields (`l0`, `lm0`, `shownL`, `n`, `nPeak`, `nHist`, `cumDef`, `vStr`, `vHyp`, `vStrHigh`, `riseHeldH`, `lastFallAge`, `r`, `fm0`) are dropped from `K.store.INPUTS`, never migrated, and a corrupt record heals fresh.
- **Rule 6.** The `AddXP` capture is an event-driven add with no clock work. Growth, the traits and the level write run at the day close, once per player per online game day. Task 12 benches the day close before and after. Every task that changes a per-minute adapter (Tasks 4, 12, 14, 15) adds a Java-call-count stub test against the build before.
- **The golden trace** (`testing/tests/kernel/golden/trace-1.0.0.json`) is re-recorded only in a commit that names its cause, with every moved leaf attributed in the task report (ruling T2-1). The named causes are listed per task.
- **Constants.** Every shipped constant sits on a settled `science.tsv` row or is labelled `game choice` with the rows that bound it (spec § 10's Basis column). `python tools/science_check.py --scan mod` → 0 at every `mod/` commit.
- **Models.** Opus for the live tasks, the oracle, the kernels the fit governs (Tasks 2, 5–10), the server adapters (12–15, 17), the register task, and every review of evidence or of a whole task. Sonnet for spelled-out edits (Tasks 3, 11, 16, 18) and scoped re-reviews. Every dispatch names its model and asks for the exact model id back.
- **Frozen files.** A driver is never edited after its run. A test of a frozen lib that reads a removed field is deleted by name under a ledgered ruling, and the pytest baseline is reset by name at the close.

## The constants block (point T; the one place a refit amends)
This table is the plan's only copy of the point-T values (refit 2, which superseded point S; spec § 5.2). Task 2 asserts that `testing/tests/kernel/strength_model.py`'s `POINT_T` equals `compact_T.json`'s `"chosen"`, and Task 5 asserts that `K.strength.DEFAULTS` equals `POINT_T` key by key. Every task below names keys, never numbers. A refit (ruling 13-1) amends the compact JSON the tests name, this table, the one Lua block, the option file's declared defaults (`sandbox-options.txt`, which Task 11's test binds) and the trait descriptions where they restate a constant, and nothing else.

| Key (oracle and kernel) | Point T value | Spec name | Option (§ 10) |
|---|---|---|---|
| `k` | 0.009906127265972144 per week | k | `NR.StrengthRate` multiplies it |
| `beta` | 3.0 | β | `NR.StrengthThresholdRise` |
| `Sg0` | 0.5 sets/wk | S_g0 | `NR.StrengthThreshold` |
| `Sref` | 12.0 | S_ref | fixed |
| `Smax` | 30.0 | S_max0 | fixed |
| `Smax1` | 12.0 | S_max1 | `NR.StrengthTrainedSetCap` |
| `fp_knots` | (0.4, 0), (0.8, 0.5), (1.3, 0.92), (1.6, 1.0) g/kg/d | f_p knots | `NR.StrengthProteinFull` scales the x values by value/1.6 |
| `E0` | −650.0 kcal/d | E₀ at s = 0 | `NR.StrengthDeficitZero` |
| `E0_drop` | 0.5 | E₀'s status drop | `NR.StrengthDeficitZeroStatusDrop` |
| `fbal0` | 1.0 | f_bal at s = 0 | `NR.StrengthBalanceGate` |
| `fbal_drop` | 0.5 | f_bal's status drop | `NR.StrengthBalanceGateStatusDrop` |
| `surplus_full` | 0.10 of TDEE | surplus_full (E_full at s = 0) | `NR.StrengthSurplusFull` |
| `full_drop` | 0.5 | E_full's status drop: E_full(s) = surplus_full · (1 − full_drop · s) · TDEE | `NR.StrengthSurplusFullStatusDrop` |
| `a_nov` | 6.0 | a_nov | `NR.StrengthNoviceDeficitDepth` |
| `trained_need` | 0.0 | — | `NR.StrengthTrainedNeedsSurplus` |
| `forbes_c` | 10.4 kg | forbes c | fixed |
| `wT` | 0.35 | wT | `NR.LeanLossTrainingProtect` |
| `S_def` | 10.0 sets/wk | T = min(1, S/10) | fixed |
| `wP` | 0.6 | wP | `NR.LeanLossProteinProtect` |
| `pdef_lo` | 0.8 g/kg/d | protection ramp start | fixed |
| `pdef_hi` | 1.6 g/kg/d | p_hi | `NR.LeanLossProteinFull` |
| `prot_floor` | 0.1 | prot floor | `NR.LeanLossProtectFloor` |
| `x_max_frac` | 0.05 of F | labile-lean cap | fixed |
| `x_tau_d` | 28.0 days | labile-lean decay | fixed |
| `m` | 0.3333333333333333 | maintenance share | `NR.StrengthMaintainShare` |
| `grace_d` | 14 days | grace | `NR.StrengthGraceDays` |
| `detrain_hl_wk` | 6.0 | detraining half-life | `NR.StrengthDetrainHalfLifeWeeks` |
| `detrain_status` | 2.0 | detraining status slowing | `NR.StrengthDetrainStatusSlowing` |
| `regain_hl_wk` | 6.0 | λ_r half-life | `NR.StrengthRegainHalfLifeWeeks` |
| `peak_hl_yr` | 2.0 | P's half-life | `NR.StrengthPeakHalfLifeYears` |

The non-fitted game constants sit in the same Lua block under their own keys, so one table carries every number the law reads:

| Key | Value | Spec | Option |
|---|---|---|---|
| `ffmi5` | 18.0 kg/m² | bio level 5's FFMI (spec § 2.4) | fixed |
| `ffmiPerLevel` | 0.5 kg/m² | one bio level | fixed |
| `capLevel` | 16.5 | the untrained natural cap, in bio levels | `NR.StrengthCapLevel` |
| `ts` | 1.0 | the biology clock | `NR.StrengthTimeScale` |
| `xpPerSet` | 360 (measured, run x423-20261015-040740) | XP of one hard set | `NR.StrengthXPPerSet` |
| `incidental` | 0.35 | non-exercise grant weight | `NR.StrengthIncidentalWeight` |
| `fMinShare` | 0.35 | F's floor as a share of F0 (the model's `0.35 * F0`) | fixed |
| `fmMin` | 0.5 kg | the fat floor (`K.partition.FM_MIN`) | fixed |
| `nov_p0` | 1.6 g/kg/d | the novice deficit deepening's ramp start (the oracle's literal, spec § 5) | fixed |
| `nov_pspan` | 0.8 g/kg/d | that ramp's span | fixed |
| `xs_p0` | 0.8 g/kg/d | the surplus share's protein ramp start (the oracle's literal `(p - 0.8) / 0.8`, spec § 5.1) | fixed |
| `xs_pspan` | 0.8 g/kg/d | that ramp's span | fixed |

### The strength-model block (spec § 2; ruling 13-45)
The second block of `K.strength.DEFAULTS`, under the same one-place rule (ruling 13-1). Task 2b's `strength_level.LEVEL_MODEL` holds the same keys, and Task 5 asserts that `DEFAULTS` equals it key by key. A change amends this table, `LEVEL_MODEL`, the Lua block, the option file's declared defaults and the trait descriptions where they restate a value, and nothing else.

| Key | Value | Spec name | Option (§ 10) |
|---|---|---|---|
| `b` | 0.8 | b | fixed |
| `Fnm` | 27.0 kg | F_nm | fixed |
| `M5` | derived at file load: `fOfBio(5) − Fnm` (25.02 kg), so S = 1 exactly at the average | M5 | — |
| `N0` | `{ STRONG = 1.14, STOUT = 1.07, none = 1.0, FEEBLE = 0.915, WEAK = 0.82 }` | N0 | fixed |
| `startLevel` | `{ STRONG = 9, STOUT = 7, none = 5, FEEBLE = 3, WEAK = 1 }` | the vanilla start levels (Weak's 1 the floor) | fixed |
| `traitShare` | 0.5 | the share of a muscle trait's start lean difference applied to the set point and the cap | `NR.StrengthTraitShare` |
| `ffmiNatural` | 25.0 kg/m² normalised to 1.80 m | the natural FFMI limit (Kouri 1995, S1915; ruling 13-47); each Fc is clamped at `ffmiNaturalRaw · H²` with `ffmiNaturalRaw = ffmiNatural − 6.3 · (1.8 − K.HEIGHT_M)` = 24.37 and 70.43 kg; the coefficient 6.3 is Kouri 1995's (S1915) | fixed |
| `Tmax` | 1.10 | T_max | `NR.StrengthNeuralMax` |
| `tauUpWk` | 3.0 weeks | τ_up | `NR.StrengthNeuralRiseWeeks` |
| `tauDownWk` | 12.0 weeks | τ_down | `NR.StrengthNeuralDecayWeeks` |
| `Tgrace_d` | 21 days | the neural grace | `NR.StrengthNeuralGraceDays` |
| `Wsat` | 5.0 sets/wk | W_sat; the neural maintenance threshold is `m · Wsat` | `NR.StrengthNeuralSaturationSets` |
| `yearsTo10` | 4.0 | Y | `NR.StrengthYearsToLevel10` |
| `perfectS`, `perfectP`, `perfectE` | 20 sets/wk, 2.0 g/kg/d, 0.10 of TDEE | perfect training (spec § 2.4) | fixed |
| `R` | derived at file load: `K.strength.R(yearsTo10)`, 1.5651015746939971 at 4 years; `params` recomputes it only at a `yearsTo10` change | R | derived |

`K.HEIGHT_M = 1.70` (spec § 2) lives in `NR_Kernel.lua`, outside the table, because `K.acute`, `K.body`, `K.traits` and `K.strength` all read it (ruling 13-4).

## Rulings this plan carries
- **13-1 (one constants block).** Ruling: every constant of the growth law, the energy gate and the lean partition is written once, in `K.strength.DEFAULTS`, under the oracle's key names, with a test binding it to `strength_model.POINT_T` and that to `compact_T.json` (point T); task text names keys, never point-T numbers — a harvest on small surpluses in trained lifters is running and a refit may follow, so a refit must amend one block, one JSON, this plan's table, the option file's declared defaults and the trait descriptions — cost if wrong: none; a table indirection costs one Lua index per read at the day close.
- **13-2 (the oracle's flags).** Ruling: the tracked oracle keeps the fit's daily step verbatim, so it reproduces `compact_T.json`, and gains a flag `exact` (default False) that switches on the four places where the spec states a form the fit did not run. With `exact=True`: detraining is integrated exactly over the day; the labile lean decays on every day with no surplus left after growth (the fit decayed it only at `E == 0` exactly, which a live day never meets); growth's energy cost is charged at `grow / ts`; and the biology clock `ts` scales growth, regain, detraining, the peak decay and divides the grace days. The kernel reproduces the oracle with `exact=True`. Task 2 re-scores the registry under it and pins every value — the spec states exact detraining (§ 6) and a time scale (§ 10), which the fit ran at `ts = 1` with an Euler step — cost if wrong: the detraining half-life oracle moves by a few hundredths of a week; Task 2 asserts every weighted oracle that passed under the record still passes.
- **13-3 (growth's energy cost under a time scale).** Ruling: at `ts > 1` the lean a day gains is `grow` (scaled) while the energy it costs is `grow / ts · RHO_LEAN` — the time scale compresses muscle biology, not the food clock, and charging the scaled gain would bill a compressed server's trainee up to 30 days of tissue energy a game day — cost if wrong: lean is cheaper than real at `ts > 1`; at the default `ts = 1` nothing differs.
- **13-4 (height).** Ruling: `K.HEIGHT_M = 1.70` in `NR_Kernel.lua`, and `K.acute.HEIGHT_M` is removed, with `K.acute.refeed`'s BMI reading `K.HEIGHT_M` — `NR_Kernel_Acute.lua` sorts before `NR_Kernel_Body.lua`, so a file-scope read of a body constant would be nil; the core file loads first — cost if wrong: none.
- **13-5 (the record calendar).** Ruling: `body.dayIndex` becomes the record's own count of closed online days, born at `math.floor(bornAge / 24)`, and a new field `body.wday` holds the world day the open record day belongs to. A minute closes the day when `math.floor(ageH / 24) > body.wday` and then sets `body.wday` to that world day, closing at most one day per minute. A minute whose step from `body.lastAgeH` exceeds 60 game minutes is a reconnect after a gap: it re-stamps `body.wday` to today's world day and closes nothing, so the day open at departure continues as today's record day. `MET.MAX_CLOSES` and `stats.skippedDays` are removed — the spec's "resumes the calendar where it stopped", and the existing rule that a step over 60 minutes is offline time (`dtM` clamp, `trailShift`) — cost if wrong: a server stall over 60 game minutes with the player online reads as a gap and folds those days into one record day.
- **13-6 (first sight without `OnNewGame`).** Ruling: a body built at first sight, with no creation handler before it (a character older than the mod, a pruned record, a reset made with no clock), is `K.body.create` over the band traits the character holds (muscle: WEAK, FEEBLE, STOUT, STRONG; weight: the five weight-band traits, Emaciated read as Very Underweight), not over its native Strength level or weight, so the held muscle trait also sets N0 — one creation path, and vanilla's band swap already keeps the held muscle trait within one band of the native level — cost if wrong: a character adopted mid-save restarts at its band's level and may lose up to two native levels.
- **13-7 (`traitCarry`).** Ruling: `body.traitCarry` is removed; the carry delta's trait factor is `K.strength.TRAIT_CARRY[band]`, the constructor's own values for the muscle trait the level implies (WEAK 0.75, FEEBLE 0.9, STOUT 1.25, STRONG 1.5, none 1.0; #2144), recomputed at every level write — the constructor ran before `applyTraits` on a new character (trait-levers § 3.3), so a first-sight read of `getMaxWeightDelta` returns 1.0 for every new character, and a reconnect's constructor would then disagree with the mod's write — cost if wrong: carry capacity changes at an in-play band swap, where vanilla changes it only at the next load.
- **13-8 (the level-write route).** Ruling: the level write moves the native level one step at a time with `player:LevelPerk(perk)` and `player:LoseLevel(perk)`, vanilla's creation route, so vanilla's `LevelPerk` listener runs the band swap at each step (spec § 7), then pins the XP. If Task 0 measures that the server-side `LevelPerk` or `LoseLevel` write does not hold or does not reach the client, the write falls back to `setPerkLevelDebug` plus the mod's own band write (`STR.remap`, today's measured route, #2867, #2870), and Task 0's report names the branch taken — the spec requires vanilla's swap on the mod's write, and #2870 measured that the debug setter runs none — cost if wrong: a stepped write fires one listener call per level, at most 10 at creation and 1 at a day close.
- **13-9 (the XP pin).** Ruling: the bar's XP is written as `getXp():setXPToLevel(perk, n)` followed, when the fraction is above 0, by one `addXp(player, perk, x)` with `x = frac · (totals[n+1] − totals[n])` divided by the multiplier chain the capture divides out, under `STR.pinning = true` so the capture ignores it. Task 0 Step 1 first reads the jar for an absolute experience setter reachable from Lua, and a found one replaces the pair. The `addXp` route re-seeds the anti-cheat's snapshot after it lands (#2132, #2862), which `setXPToLevel` alone does not, so a pin that raises XP never trips the check for a user connection — the spec pins "the level's starting total plus the fraction", and the only Lua-reachable setter known writes level totals — cost if wrong: the landed fraction can be off by the rounding of the protein factor; the panel's true level is unaffected.
- **13-10 (the level-10 guard).** Ruling: while the body's level is 10 or more and the native level is 10, the server wraps `xpUpdate.checkForLosingLevel` with a guard that returns for Strength without calling the original, chained after BeyondTen's own wrapper when that is loaded (#2856) — the spec's "guarded … as BeyondTen does" — cost if wrong: a second mod that replaces the function after ours drops our guard; the guard is re-installed at `OnServerStarted` and checked by a Task 19 read.
- **13-11 (the multiplier chain divided out).** Ruling: the capture divides the landed amount by the protein factor read off the server's protein store (×1.5 when 50 < store < 300, ×0.7 below −300; #2112), by the sandbox multiplier (`MultiplierConfig.Global` when `GlobalToggle` is true, else `MultiplierConfig.Strength`), and also by the per-perk book multiplier `getXp():getMultiplier(perk)` when it is above 1 (#2113), the third because it is the same chain and any book that multiplies Strength would scale biology — spec § 4 names the first two; a book is the third link — cost if wrong: one Java call per Strength grant; no vanilla Strength book exists to our knowledge.
- **13-12 (the signal ring).** Ruling: today's signal accumulates in `body.sigDay` and `body.sig7` holds the seven closed days (slot 1 the oldest), the `pDay`/`p7` pattern; at the close the ring shifts, `sigDay` lands in slot 7 and S is the ring's sum divided by `xpPerSet` — the spec's "today's slot of a 7-slot daily ring" — cost if wrong: none.
- **13-13 (an immobilised day).** Ruling: an immobilised day (a leg fracture or splint) runs the existing disuse arm in place of growth, regain and detraining; the grace counter still counts it — the disuse curve already carries immobilised loss (S0069), and running detraining beside it would count the loss twice — cost if wrong: none measured.
- **13-14 (thinness and Weak).** Ruling: a thin pick sets `F = min(F_start, BMI_target · H² − fat_target)` — "lowered to reach" never raises F; Weak and Feeble, whose starts lie at or below the thin targets, cannot be taken with a thin pick (ruling 13-46) — cost if wrong: none. Replaced in Task 10c (Angus, 2026-10-15): a thin pick is fat-only, at 10 % or 6.5 % body fat on the muscle pick's lean, and the exclusions are lifted.
- **13-15 (the BMI the axes read).** Ruling: the thinness axis reads BMI from `F + fm` (spec § 8), not from the weight slot, which also carries `lx` — the spec's text — cost if wrong: at most 0.05 · F of labile lean, about 1 BMI unit at the cap, never counted toward thinness.
- **13-16 (pick validation).** Ruling: validation runs on the server's own definitions. The point total is legal when the creation screen's remaining points, by the formula Task 0 Step 2 reads off the install's `CharacterCreationProfession.lua`, are 0 or more. Picks are stripped from the end of `getKnownTraits()` (the order the client's list sent, the server's only order), skipping free (profession-granted) traits, until the total is legal and no two remaining picks exclude each other (`isMutuallyExclusive` either way). A stripped trait's XP boosts are reverted with `setPerkLevelDebug(perk, max(0, level − boost))` plus `setXPToLevel`, since `applyTraits` already applied them — the spec's "stripped, latest first, and logged"; the server keeps no pick order (trait-levers § 4) — cost if wrong: a cheating client loses its last-listed trait, not its last-picked one.
- **13-17 (the female fat cuts).** Ruling: with `NR.SexSpecific` on, a female character reads Kelly 2009's female FMI cuts from the settled row S2057 (excess fat above 9, obese class I above 13 kg/m²), and the male cuts come from S2056 — both rows were minted at b6b73a49 — cost if wrong: none; the option defaults off.
- **13-18 (the Training adapter).** Ruling: `NR_Server_Training.lua` is deleted and `test_training_shape.py` with it; `K.training` keeps the aerobic side (`metMinutes`, `band`, `sample`, `climbCredit`, `closeDay`, `weekMinutes`), and the resistance side (`event`, `loadMinute`, `actionMinute`, `decay`, `doses`, `W_STR`, the `S_*` and `K_*` constants, `MAINTAIN_HIGH`, `TAU_V_DAYS`) goes. The capture lives in `NR_Server_Strength.lua`, the module that owns Strength — the file's whole content was the resistance side (spec § 9.2) — cost if wrong: none.
- **13-19 (the panel's Strength row).** Ruling: the mirror carries `body_level`, the true level to two decimals' precision as a number, and `body_sets`, the closed week's S; the view shows "Strength 12.3" on the Bands level and up, under the body block. The old `body_shownL`, `body_dStr` and `body_dHyp` keys go — spec § 2's panel line — cost if wrong: none.
- **13-20 (`lx` in mass).** Ruling: `lx` counts in the weight slot (`fm + lm + lx`), the `mass7` ring, the trailing weight readers and `K.energy.minute`'s total-mass terms (`NR_Kernel_Energy.lua:264` and `:267`, the activity bill and the exercise kcal per kg of total mass); REE's lean term keeps reading `body.lm` (`NR_Kernel_Energy.lua:263`; `ree` takes `lm` only) — spec § 5.1: weight, not level or REE — cost if wrong: none.
- **13-21 (F1, the curve check's inputs).** Ruling: Task 8's curve check runs at `p = 2.0` and `E = 0.10 · tdee`, where `f_e = 1` at every status (E_full(s) is at most 0.10 · TDEE), so it reproduces the anchor of `fast_grow` (bio level 15 at 5 years); the parity test at `E = 130` stays and covers the partial-gate path — the spec's "full gates" is exactly that, and `E = 130` is half of E_full(0), which gives 14.879 — cost if wrong: none.
- **13-22 (F2, the Räntilä bound).** Ruling: Task 8 asserts the oracle's band (`0.80 <= ratio <= 1.25`, `rantila_block2_over_1`) and pins the exact-mode ratio from Task 2's `EXACT_PINS` to 1e-9; the stated 0.94 was a rounding of a value below it (0.9385 Euler, 0.93811 exact) — cost if wrong: none.
- **13-23 (F3, the detraining test).** Ruling: Task 2's half-life test runs with `detrain_status = 0` and asserts the ratio is 0.5 within 0.01; the status term, which shortens the half-life as F falls (0.4421 at point T), is left to Task 8's one-day-factor test — the plan's old band had the direction backwards and could not pass — cost if wrong: none.
- **13-24 (F4, BeyondTen's global).** Ruling: BeyondTen is detected as `BeyondTen ~= nil and BeyondTen.API_VERSION == 1` and called as `BeyondTen.SetStoredXP` and `BeyondTen.GetTotalMasteryCost` (its `Shared.lua:1-6` reads `BeyondTen = BeyondTen or {}`; `BT` is a local of its files); Task 14's stub sets the global `BeyondTen`; spec § 7's wording is corrected at the close (Task 24) — the install's file is the ground truth — cost if wrong: none.
- **13-25 (F5, the trait descriptions).** Ruling: the restated blocks point `UIDescription` at new mod keys `UI_NR_trait_<id>desc`, so no vanilla key is redefined and `test_shape` and `test_no_vanilla_key_redefined` hold; `test_every_ui_key_is_read` gains the script-referenced keys read off `NR_Traits_Body.txt`; Task 0 check 3's marker override stays as a reading — cost if wrong: if Angus wants the vanilla keys overridden, the two tests need a ruled exception list.
- **13-26 (F6, the harness reads).** Ruling: Task 0's harness commit adds a client `perk.xp` twin (`<PerkName>` → `{perk, side, xp, level}`); a server `bt.stored <user> <Perk>` (a pcall'd BeyondTen read, nil-safe when absent) lands in its own harness commit before Task 19; the level guard is identified by a sentinel global the mod sets — every live read must exist before its run (§ 5) — cost if wrong: one more harness commit and a `#2808` update.
- **13-27 (F7, the AddXP recorder).** Ruling: `TKX_TraitLevers_Server.lua` gains an `AddXP` recorder (perk, amount, wall ms, protein store, whether an `ISFitnessAction` was running), capped at 200 events and read by `lua.read`; `TKX_XpEvents` stays frozen and leaves the profiles; Task 1 sums the recorder's events; check 7's tree and barricade sources are ruled out of check 7 (no harness command makes them) and keep the `incidental` weight, unmeasured — cost if wrong: unmeasured sources keep the default weight.
- **13-28 (F8, the carry across Tasks 12 to 14).** Ruling: Task 12 brings `K.strength.TRAIT_CARRY` and `traitCarry(n)` forward, and the carry reads `traitCarry(native level)` until Task 14 switches it to `body.wroteL` — every commit stays green and the golden records no failure leaf — cost if wrong: none.
- **13-29 (F9, the repin call).** Ruling: Task 13 stamps `body.levelDue = true` when the native level differs from `body.wroteL`; Task 14 replaces that stamp with the `STR.repin` call — no forward reference in a serial lane — cost if wrong: one minute's delay before a re-pin between Tasks 13 and 14 only.
- **13-30 (F10, the owner of `fatT`, `thinT` and `band`).** Ruling: `K.body.create` returns `fatT` and `thinT` (rung numbers from the weight pick: OVERWEIGHT 1, OBESE 2, UNDERWEIGHT 1, VERY_UNDERWEIGHT 2; Emaciated read as 2) and `sexIdx`; `K.body.new` copies them and sets `body.band` from `K.traits.axes` once Task 10 lands, and Task 10's Files list `NR_Kernel_Body.lua` for that line — one owner per field — cost if wrong: none.
- **13-31 (F11, female creation fat).** Ruling: `K.body.create(muscle, weight, P, sexIdx)`; with `NR.SexSpecific` on, a female pick sits at the middle of S2057's bands (normal 7.0, Overweight 11.0, Obese 15.0 kg/m² of fat), labelled game choices on S2057, and Task 10's creation-pick test runs for both sexes; with the option off the male table is used — spec § 3.2 requires it and the axes already read the female cuts — cost if wrong: female starting weights become a game choice; the option defaults off.
- **13-32 (F12, one clamp rule).** Ruling: `readLeaf` moves to the kernel as `K.readLeaf` (pure, no Java) and `NR_Server_Options` calls it, all in Task 11 — cost if wrong: none.
- **13-33 (F13, the bench seam).** Ruling: the seam `MET._closeDay = closeDay` under a `NR_BENCH` guard (one line, no behaviour change) lands in its own commit first, with § 3's mod gates and the full `claims_check` (it shifts Metabolism's lines), and the before-figure is read on that commit — "before" must be a real tree — cost if wrong: none.
- **13-34 (F14, the weight readers).** Ruling: Task 12's Files add `NR_Kernel_Energy.lua`, `NR_Kernel_Mirror.lua` and `NR_Kernel_Heal.lua`; every site (`NR_Kernel_Energy.lua:264`, `:267`; `NR_Kernel_Mirror.lua:56`; `NR_Kernel_Heal.lua:140`; `NR_Kernel_Store.lua:194`; `NR_Server_Weight.lua:119`) reads `fm + lm + lx`; ruling 13-20 is reworded to `K.energy.minute`'s total-mass terms — cost if wrong: none (`lx` is at most 0.05 · F).
- **13-35 (F15, the immobilised day).** Ruling: the immobilised branch applies `K.partition.disuse`'s `dFM, dLM` under `P.fmMin` and `P.fMinShare · body.F0`, leaves `lx` untouched and lets step 5's `fmRef` re-base apply as for any day; `K.partition.FM_MIN` and `LM_MIN_RATIO` are removed in favour of `DEFAULTS` — cost if wrong: none.
- **13-36 (F16, Task 14 and 17's files and the golden stand-in).** Ruling: Task 14's Files add `NR_Server_Metabolism.lua` and `testing/tests/kernel/golden_trace.py` (the stand-in player gains `LevelPerk`, `LoseLevel`, `getXp():setXPToLevel` and a global `addXp`, recording calls); Task 17's add the stand-in's descriptor and trait-definition stubs; each re-record names the stand-in change beside its behaviour cause; `ctx` is optional in `writeLevel` and `writeTraits` — the golden is an oracle and a silent stand-in change is a defect — cost if wrong: none.
- **13-37 (F17, the literals).** Ruling: the non-fitted table gains `nov_p0` 1.6, `nov_pspan` 0.8, `xs_p0` 0.8 and `xs_pspan` 0.8 (fixed, spec §§ 5 and 5.1), and the surplus arm reads `xs_*`, never `pdef_*`, because spec § 5.1 states the surplus share's ramp as a literal and ties `NR.LeanLossProteinFull` to the deficit protection only — cost if wrong: if Angus wants the option to move both ramps, the surplus arm reads `pdef_*` and the oracle gains the same change.
- **13-38 (F18, artifacts rows).** Ruling: after each live run the controller commits the run's artifact folder in its own commit with its artifacts row, do-not-cite keys and the `artifacts.md` re-anchor (full `claims_check` → 0), per § 4 item 1 and rulings M-1 and D-1; Task 23 Step 1 shrinks to the claims — cost if wrong: none.
- **13-39 (F19, the order).** Ruling: the order is 0 → 1 → (2, 2b, 3, 4) → 5; Tasks 0 and 1 may overlap mod-lane edits because their profiles load no `mod/` file (a reading of § 5's reason: the boot loads the whole tree); Task 5 waits for Tasks 1, 2 and 2b; a close-wave change to a code path a live run measured is re-smoked or named as a skew note — cost if wrong: Task 5 waits on two sessions.
- **13-40 (F20, Task 2's lane).** Ruling: Task 2 runs in a worktree and reaches `main` by the controller's cherry-pick (§ 6's allowed form) — a pure-Python oracle is a pure-kernel task — cost if wrong: none.
- **13-41 (F21, the fit's code).** Ruling: Task 2 consumes `model.py` and `oracles.py` from `docs/superpowers/research/2026-10-14-strength-redesign/refit/` (tracked at 5987ac7a), never from a scratchpad — the fit's record holds its code — cost if wrong: none.
- **13-42 (F22, BeyondTen at levels 10 to 15).** Ruling: with BeyondTen loaded and native 10, every write sets the stored XP to `GetTotalMasteryCost(min(floor(L), 15)) + frac · (cost(next) − cost(floor(L)))`, which reads 0 + frac · cost(11) for L in [10, 11) and writes cost(15) for L >= 15; the body is the only source of the level — BeyondTen banks every grant above the parked level-9 total as mastery (#2850) and clamps at 15, while Strong's cap reads shown level 13.40 at the defaults (spec § 7; 14.23 before ruling 13-47's clamp), so the clamp at 15 binds only on a tuned server — cost if wrong: none.
- **13-43 (F23, the guard's order).** Ruling: Task 19 grades behaviour (a forced ten-minute rust pass on a parked level-10 Strength leaves level 10) and records which wrapper is outermost as a reading; ruling 13-10's "chained after BeyondTen's own wrapper" holds only if the mods load in that order (BeyondTen installs at `OnServerStarted`, as the mod does) — the behaviour is the requirement — cost if wrong: none.
- **13-44 (F32, the creation profile).** Ruling: `x43-creation.toml` sets `[sandbox] Nutrition = false` and `DayLength = 1`, like Tasks 19, 20 and 22 (§ 5, ruling T18-1) — cost if wrong: none.
- **13-45 (the strength-linear level).** Ruling: the shown level is `K.strength.level(F, N0, T, P)` = 5 + 5 · (S − 1)/(R − 1), with S = ((F − Fnm)/M5)^b · N0 · T; the growth law keeps its linear FFMI coordinate as `K.strength.bioLevel` and `fOfBio` (the fit, the anchor, `capLevel` and every `s`); `M5 = fOfBio(5) − Fnm`, so the untrained average is level 5 exactly; R is `K.strength.R(yearsTo10)`, run on `DEFAULTS`' growth constants and `Tmax`, never a server's other options, and recomputed by `params` only when `NR.StrengthYearsToLevel10` changes; T is a body field advanced at the day close by `K.strength.neural` inside `K.strength.day`, with its own grace counter `Tgrace` counting days below `m · Wsat`; the perk floors `L + 1e-9`; the per-trait values and the verified table are Task 2b's `strength_level`, pinned — Angus (2026-10-14): the level is linear in general strength all the way, level 10 is the general strength of 4 years of perfect training (an option, default 4), strength combines muscle, a trained neural factor and an innate factor, and every Strength-XP source counts as one general full-body workout; the neural and innate harvests (S2090–S2141, S2142–S2172) size the factors — cost if wrong: R taken from the defaults means a server that changes `NR.StrengthRate` reaches level 10 in other than Y years (by design, so the rate option keeps its meaning); a literal M5 of 25 would move R by 0.001.
- **13-46 (the trait starts and creation anti-stacking).** Ruling: `K.body.create` builds a muscle pick at its vanilla start level (Weak 1, Feeble 3, none 5, Stout 7, Strong 9) through N0 and lean, F solving `level(F, N0, 1) = startLevel`; F0 and Fc move by `traitShare` of `F − fOfBio(5)`; the peak starts at `max(F, F0)`, so Feeble's and Weak's deconditioned half comes back on the regain path; Underweight and Very Underweight exclude Weak and Feeble (`K.body.EXCLUDES`, Task 16's blocks, Task 17's validation; lifted in Task 10c, Angus 2026-10-15: "Lift the exclusions", the table, the pairs and the validation's kernel check removed); Task 9's pick-set test enumerates every legal set of the 8 body traits for both sexes and asserts that each point-giving body trait makes the created body measurably worse than the same set without it — Angus (2026-10-14): the traits keep their vanilla start levels, half the start's lean difference is the permanent base and the cap moves by the same half, Weak's floor is level 1, and "a floor is acceptable but we need to make sure that at player creation they cant take advantage of the floor by stacking things that give points but dont add downsides, or remove some of the traits" — cost if wrong: two fewer legal combinations; an idle Strong character detrains to level 7.64, Stout's band.
- **13-47 (the natural cap clamp).** Ruling: every trait's natural cap Fc is clamped at the natural FFMI limit, `Fc = min(Fc5 + traitShare · (F − F5), ffmiNaturalRaw · H²)` with `ffmiNaturalRaw = ffmiNatural − 6.3 · (1.8 − K.HEIGHT_M)` = 24.37, F = 70.43 kg, `ffmiNatural` = 25.0 normalised to 1.80 m (Kouri's limit, S1915) fixed and not an option, in `trait_start` (Task 2b), `K.body.create` (Task 9) and the tests; Strong's cap becomes 13.40 and Stout's 12.34 (from 14.23 and 12.50) and their trajectories in the TABLE are recomputed (25 and 348 days to level 10); none (10.78), Feeble (8.93) and Weak (6.99) are unchanged; the coefficient 6.3 is Kouri 1995's (S1915) — the controller (2026-10-14): no natural trait sits above the natural limit — cost if wrong: a server wanting an enhanced Strong character has no option for it.

## File structure
| File | Change |
|---|---|
| `testing/tests/kernel/strength_model.py` (new) | the fit's `model.py`, verbatim, plus `POINT_T`, the `exact` flag and `ts` (Task 2) |
| `testing/tests/kernel/strength_level.py`, `test_strength_level.py` (new) | the strength-level reference: the level, R, the trait starts, the neural factor, the verified table pinned (Task 2b) |
| `testing/tests/kernel/strength_oracles.py` (new) | the fit's `oracles.py`, verbatim, imports renamed (Task 2) |
| `testing/tests/kernel/test_strength_oracle.py` (new) | the record reproduced, the `exact` re-score pinned (Task 2) |
| `testing/tests/kernel/test_strength_parity.py` (new) | the kernel against the oracle, day by day (Tasks 5–9) |
| `mod/.../shared/NR_Kernel.lua` | `K.HEIGHT_M` (Task 4); `K.readLeaf` (Task 11) |
| `mod/.../shared/NR_Kernel_Strength.lua` | rewritten: `DEFAULTS` (both blocks), the bio scale, the strength level, the neural factor, the law, the capture arithmetic, `params`; the neural term, the memory floor, the cumulative deficit, the disuse term, `fSlow`, `ceiling`, `xpLevel`, `policy` removed (Tasks 5–8, 12) |
| `mod/.../shared/NR_Kernel_Partition.lua` | the lean arms replaced; `leanGain`, `headroom`, `gEnergy`, `gProt`, `protection`, `surplus`, `deficit`, `day`, `G0`, `LM_CAP_RATIO`, `P_LO`, `P_HI`, `SURPLUS_RAMP`, `DEFICIT_HALF*`, `PROT_*` removed (Tasks 7, 12) |
| `mod/.../shared/NR_Kernel_Training.lua` | the resistance side removed (Task 12) |
| `mod/.../shared/NR_Kernel_Body.lua` | `create`, `new` rewritten, `effSex`; `split`, `interp`, `ANCHORS_W`, `BF_*`, `BUILD_*`, `KNOTS`, `W_MIN`, `W_MAX`, `band` removed (Tasks 3, 9, 12, 15) |
| `mod/.../shared/NR_Kernel_Traits.lua` (new) | the three axes with damping (Task 10) |
| `mod/.../shared/NR_Kernel_Heal.lua`, `NR_Kernel_Store.lua` | the no-trait body fallback; the new fields healed and saved (Tasks 4, 12) |
| `mod/.../shared/NR_Kernel_Acute.lua` | `HEIGHT_M` removed, the BMI reads `K.HEIGHT_M` (Task 4) |
| `mod/.../shared/NR_Kernel_Energy.lua` | the total-mass terms read `fm + lm + lx` (Task 12) |
| `mod/.../shared/NR_Kernel_Mirror.lua`, `NR_Kernel_View.lua` | `body_level`, `body_sets`, the Strength row (Task 18) |
| `mod/.../server/NR_Server_Metabolism.lua` | the calendar, the day close, first sight (Tasks 4, 12) |
| `mod/.../server/NR_Server_Strength.lua` | rewritten: capture, level write, park, BeyondTen, carry (Tasks 13, 14) |
| `mod/.../server/NR_Server_Training.lua` | deleted (Task 12) |
| `mod/.../server/NR_Server_Weight.lua` | the band refresh retired; the § 8 trait writes (Task 15) |
| `mod/.../server/NR_Server_Creation.lua` (new) | the `OnNewGame` handler (Task 17) |
| `mod/.../server/NR_Server_Players.lua` | the `P.onNewGame` hook list (Task 17) |
| `mod/.../server/NR_Server_Options.lua` | the strength options and `sexSpecific` (Tasks 3, 11) |
| `mod/.../server/NR_Server_Nutrients.lua`, `NR_Server_Effects.lua` | the effective sex (Task 3) |
| `mod/.../client/NR_Client_View.lua` | the effective sex (Task 3) |
| `mod/.../scripts/NR_Traits_Body.txt` (new) | the 10 restated trait blocks (Task 16) |
| `mod/.../42.21/media/sandbox-options.txt`, `Translate/EN/Sandbox.json`, `Translate/EN/UI.json` | options and translations (Tasks 3, 11, 16, 18) |
| `testing/PZTestKit/...` | `trait.def`, `creation.picks`, `perk.park` and the client `perk.xp` (Task 0); `bt.stored` (Task 19) |
| `testing/tests/kernel/golden_trace.py` | the stand-in player's route, descriptor and trait-definition stubs (Tasks 14, 17) |
| `testing/experiments/TKX_TraitLevers/` (new) | the trait-lever probe mod (Task 0) |
| `testing/experiments/x42_levers_lib.py`, `x421_levers.py`, `x422_calib.py`, `x43_strength_lib.py`, `x431_beyondten.py`, `x432_offline.py`, `x433_creation.py`, `x434_growth.py` and their profiles (new) | the live runs |
| `tools/bench_day_close.py` (new) | the Rule 6 bench (Task 12) |

---

### Task 0: Live engine checks before any build (Opus; harness lane, then live; controller opens the workspace)
Spec § 12.2's Task 0 checks. A finding that falsifies a spec assumption stops the plan for a ruling before the dependent task (the stop table in Step 6).

**Files:**
- Modify `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `.../client/PZTestKit_Client.lua` and `.../server/PZTestKit_Server.lua` (new sites appended at the end of each file, § 5). The Core and Server files are CRLF (§ 7): edit them with `newline=''` handling and preserve the endings.
- Regenerate `docs/reference/harness-commands.md` (`python tools/bus_inventory.py`); update `#2808`'s claim text and quote and `#1235`'s quote for the new count (§ 5).
- Create `testing/experiments/TKX_TraitLevers/42.21/mod.info` and its `media/scripts/TKX_TraitLevers.txt`, `media/lua/shared/TKX_TraitLevers_Shared.lua`, `media/lua/server/TKX_TraitLevers_Server.lua`, `media/lua/shared/Translate/EN/UI.json`.
- Create `testing/experiments/x42_levers_lib.py`, `testing/experiments/x421_levers.py`, `testing/profiles/x42-levers.toml`, `testing/tests/test_x42_levers_lib.py`.

**Interfaces (the harness change, its own commit before the run):**
- `trait.def` (shared) `<TraitName>` → `{ok, side, trait, cost, free, xpBoosts = {<Perk> = n}, exclusive = {names}, granted = {names}, label, description}`: reads `CharacterTraitDefinition.getCharacterTraitDefinition(CharacterTrait[<TraitName>])` and walks its getters; the Java maps and lists are walked with `size()`/`get(i)` and `keySet():iterator()` (#0940), never `#`.
- `creation.picks` (client) `<TraitName> [<TraitName> ...]` → `{ok, armed, picks}`: arms a one-shot rewrite of the pick list that runs after vanilla's copy in the coop creation accept path (`CoopCharacterCreation.lua:65–68`; the implementer reads `:60–:80` first) and before `sendCreatePlayer` reads it: `getWorld():getLuaTraits():clear()` then one `getWorld():addLuaTrait(name)` per argument. It sends what it is given, legal or not.
- `perk.park` (server) `<user> <Perk> <xpLevel>` → `{ok, perk, levelBefore, levelAfter, xpBefore, xpAfter}`: `getXp():setXPToLevel(perk, xpLevel)` only, the level untouched.
- `perk.xp` (client twin of the server command; ruling 13-26) `<PerkName>` → `{perk, side, xp, level}`: the local player's Strength (or any perk) experience and level, so check 4 and Task 21 grade what the client holds. A harness command exists for every live read before its run (§ 5).

**`TKX_TraitLevers` (installed only through `x42-levers.toml`, never into a fixture):**
- `TKX_TraitLevers.txt` restates `base:obese` in full in `module Base` with `Cost = -10`, `IsProfessionTrait = false`, no `XPBoosts`, and vanilla's exclusions plus `base:overweight` (the vanilla block's other keys copied from `scripts/generated/characters/character_traits.txt:743`).
- `TKX_TraitLevers_Shared.lua` at file scope: `getXpBoosts():remove(Perks.Fitness)` on Underweight's definition; `getMutuallyExclusiveTraits():remove(CharacterTrait.ATHLETIC)` on Overweight's; `getMutuallyExclusiveTraits():add(CharacterTrait.OBESE)` on Overweight's; each records its pcall result into a global `TKX_TraitLevers.edits`.
- `TKX_TraitLevers_Server.lua`: an `OnNewGame(player, square)` handler under `isServer()` that records the known-trait list, the weight, the Strength and Fitness levels and XP; then writes `getNutrition():setWeight(77.7)`, removes STRONG if present, adds OUT_OF_SHAPE, steps Strength once with `LevelPerk` (or `LoseLevel` at 10), and records the after state. A global `TKX_TraitLevers.newGame` table holds both reads.
- `TKX_TraitLevers_Server.lua` also holds an `AddXP` recorder (ruling 13-27): one record per `Events.AddXP` call with the perk, amount, wall ms, the protein store (`getNutrition():getProteins()`) and whether an `ISFitnessAction` was running, capped at 200 events and read by `lua.read`. `TKX_XpEvents` stays frozen (it records counters only and ships only a `42.20/` folder) and leaves the profiles.
- `UI.json` overrides `UI_trait_obesedesc` with a marker string (the key name taken from the vanilla block's `UIDescription`).

- [ ] **Step 1: The jar and install reads (Opus, read-only; `pz.sh` per CLAUDE.md § 2).** Write each answer into `task-0-reads.md` with its `Class.method @off L<n>` or `lua:<path>:<line>` cite:
  - an absolute experience setter on `IsoGameCharacter$XP` reachable from Lua (ruling 13-9);
  - whether `GameServer.addXp` calls `updateXpChecker` after `AddXP` returns early (an amount of 0, and XP at the level-10 total);
  - `IsoGameCharacter.LevelPerk` and `LoseLevel` on a server: what they push, and whether the band listener runs (`XpUpdate.lua:196–238`);
  - `xpUpdate.checkForLosingLevel`'s signature and BeyondTen's wrapper (`3765241705/.../Server.lua:445–460`), and BeyondTen's global `BeyondTen` with its `API_VERSION`, `SetStoredXP`, `GetStoredXP` and `GetTotalMasteryCost` signatures and units (ruling 13-24) (`3765241705/mods/BeyondTen/42/media/lua/shared/BeyondTen/Shared.lua`);
  - `Nutrition.updateWeight`'s call of `applyTraitFromWeight`, and whether the `Nutrition = false` early return skips it (#2644);
  - `SandboxVars.MultiplierConfig`'s field names on 42.21 (`Global`, `GlobalToggle`, `Strength`) from `media/lua/shared/Sandbox/Apocalypse.lua:242–246`;
  - whether `XP.AddXP` fires the `AddXP` event after its level-up (#2125 places the event at @1346, near the end of the method), so an in-listener re-pin is not undone by a later level-up;
  - whether `AddXP` applies `MultiplierConfig` at all, which spec § 4 assumes.
- [ ] **Step 2: The creation-screen reads.** From `client/OptionScreens/CharacterCreationProfession.lua`, read the remaining-points formula (the profession cost, the sandbox free points, each trait's cost sign) and write it as a formula into `task-0-reads.md` (ruling 13-16). From `CoopCharacterCreation.lua`, read the respawn path that copies the picks.
- [ ] **Step 3: The harness change.** Write the four commands (`trait.def`, `creation.picks`, `perk.park` and the client `perk.xp`) with their `@reply` lines and comment blocks. No command is added for a tree hit or a barricade removal (ruling 13-27). Run `python tools/luabalance.py` on the HEAD copies then the working tree, `python tools/kahlua_lint.py testing/PZTestKit testing/experiments`, `python tools/bus_inventory.py`, `python tools/claims_check.py --staged` → 0 (the commit touches `testing/PZTestKit/` and `docs/`), and the full `claims_check` → 0 (after the `#2808`/`#1235` update). Commit by pathspec: `"Plan 13 Task 0: harness trait.def, creation.picks, perk.park and client perk.xp"`.
- [ ] **Step 4: The lib and driver.** `x42_levers_lib.py` imports `xlib.py` and starts from `x37_fitness_lib.py`'s newest patterns. Its offline tests (`test_x42_levers_lib.py`) run every grade against fake buses whose replies are the three commands' `@reply` shapes and recorded shapes of the others (§ 5), each grade with a case that fails it. Commit the lib, driver, profile and tests before the boot.
  - The profile `x42-levers.toml`: fixture `two` (an admin and a user-role client), `[[mods]]` PZTestKit and TKX_TraitLevers (its `AddXP` recorder replaces `TKX_XpEvents`, ruling 13-27); `[sandbox] Nutrition = false`, `DayLength = 1`; no NutritionRevamp.
- [ ] **Step 5: The run (one session; § 5's memory check, `pzt doctor`, the foreground polling wait).** The driver `x421_levers.py` grades:
  1. **Restated block replaces vanilla's on both sides:** `trait.def Obese` on server and client reads cost −10, free false, no Fitness boost, Overweight among the exclusions.
  2. **The Lua list edits bind:** `trait.def Underweight` reads no Fitness boost; `trait.def Overweight` lists Obese and not Athletic, on both sides; `TKX_TraitLevers.edits` holds no error.
  3. **The client sees the server's definitions** after the join: the client's `trait.def` answers equal the server's for the three traits, and the client reads the marker description (a reading only: Task 16 points its descriptions at mod keys, ruling 13-25).
  4. **`OnNewGame` writes reach the client:** the user client dies (`health.reduce <user> 110`) and respawns through x192's route (`ISPostDeathUI` → `CoopCharacterCreation.instance accept` via `lua.callm`); the server's `TKX_TraitLevers.newGame` after-state is read beside the client's `stats.get` and client-side `perk.xp` (the twin of Step 3) in the same wall second (§ 5's same-second pairs): weight 77.7, OUT_OF_SHAPE present and STRONG absent, the stepped Strength level.
  5. **An illegal pick list reaches `OnNewGame`:** before the second respawn, `creation.picks Strong Stout Obese Overweight` (over-budget and mutually exclusive); the server's recorded known-trait list holds all four.
  6. **Vanilla's band swap fires on the mod's level write:** in the handler's write (route of ruling 13-8), the band trait after the step is the stepped level's band on both sides; a `perk.level` (debug) write in the same session shows no swap, as #2870 did.
  7. **`AddXP` sees every Strength source:** with `TKX_TraitLevers`' recorder running, the user client runs `exercise.do pushups 1`, a melee hit on a spawned target with a knockback weapon (`attack.melee`) and loaded movement above half the max weight for 60 real seconds (`inventory.add`, `player.walk`); each source's events are read from the recorder with amount and whether an `ISFitnessAction` was running. The tree-hit and barricade-removal sources are ruled out of this check (no harness command makes them, ruling 13-27) and keep the `incidental` weight, unmeasured.
  8. **The level-10 park keeps `AddXP` firing:** `perk.set <user> Strength 10`, `perk.park <user> Strength 9`, `xp.grant <user> Strength 100`: the event's amount is the full grant (after the protein factor of the store read beside it), the level stays 10.
  9. **The pin under the anti-cheat:** on the user-role connection with `AntiCheatXP = 2`, `perk.set` to level 7 then the ruling 13-9 pair (`setXPToLevel` via `perk.park` then `xp.grant` of 30000) draws no kick across two minutes (two check intervals, #2860).
  Write the report with the do-not-cite leaves and the candidate claims, as Plan 11h Task 4 did. The controller then commits the artifact folder byte-identical in its own commit with its artifacts row, its do-not-cite keys and the `artifacts.md` re-anchor (full `claims_check` → 0; § 4 item 1, ruling 13-38).
- [ ] **Step 6: The stop table (controller).** Ledger each check's verdict. A falsified check stops these tasks for a ruling before they start:

  | Check | Falsified means | Stops |
  |---|---|---|
  | 1, 2, 3 | a restated block merges or does not reach the client | Task 16 |
  | 4 | creation writes do not reach the client in the reply | Task 17 |
  | 5 | the server drops an illegal list | Task 17's validation (then dropped as dead code) |
  | 6 | neither route of ruling 13-8 swaps the band | Task 14 |
  | 7 | a source fires no server event | Task 13 (the source's weight is then 0, a ruled limitation) |
  | 8, 9 | the park stops the event, or the pin trips the check | Task 14 |

### Task 1: The XP-per-set calibration run (Opus; live; one session)
Spec § 4 and § 12.2. The constant `xpPerSet` ships at the reading.

**Files:**
- Create `testing/experiments/x422_calib.py` (on `x42_levers_lib.py`), `testing/profiles/x42-calib.toml` (fixture `default`; PZTestKit and TKX_TraitLevers for its `AddXP` recorder; `Nutrition = false`; `DayLength = 1`).

- [ ] **Step 1: Offline tests** of the grade on fake buses, each with a failing case (zero events, a protein store outside the neutral window).
- [ ] **Step 2: The run.** `nutrition.set <user> proteins 0` on the server (the factor-1 window between −300 and 50; read back), endurance full (`stats.setany <user> ENDURANCE 1`), then `exercise.do pushups 5`; the driver stops the set through `action.cancel` (client; § 5) when the server's endurance reads 0.25 or below or the action ends. Read every Strength `AddXP` event (amount, wall time) from the recorder and the protein store before and after.
- [ ] **Step 3: The reading.** XP per set = the sum of the set's Strength amounts, each divided by the protein factor read at the store (the store stays in the neutral window, so the factor is 1; any event outside it is reported, never dropped). Report reps, XP, wall seconds and XP per real second beside vanilla-strength-rate § 4's 346 and 1.8–1.95.
- [ ] **Step 4: The amendment.** The controller commits the run's artifact folder in its own commit with its artifacts row, do-not-cite keys and `artifacts.md` re-anchor (ruling 13-38), and ledgers the reading. Task 5 writes it as `DEFAULTS.xpPerSet` with the run's id in its label, and Task 11 as the option's default. The provisional 346 never ships unless the run comes back unmeasured, in which case 346 ships labelled `provisional, vanilla-strength-rate § 4` and a ruling is ledgered.

### Task 2: Track the oracle (Opus; a worktree task, ruling 13-40)
**Files:**
- Create `testing/tests/kernel/strength_model.py`, `testing/tests/kernel/strength_oracles.py`, `testing/tests/kernel/test_strength_oracle.py`.

**Interfaces:**
- **Consumes:** `docs/superpowers/research/2026-10-14-strength-redesign/refit/model.py` and `oracles.py` (point T's fit, tracked at 5987ac7a; ruling 13-41); `docs/superpowers/research/2026-10-14-strength-redesign/refit/compact_T.json`.
- **Produces:**
  - `strength_model.POINT_T` (a dict: `DEFAULT` updated with `compact_T.json`'s `"chosen"`, `fp_knots` kept from `DEFAULT`);
  - `strength_model.Body(P, L0, cap, fat_kg, F0L=None, peakL=None)` and `Body.day(S, p, E, tdee=2600.0)` unchanged when `P.get('exact')` is falsy;
  - with `P['exact']` true, `Body.day` applies ruling 13-2's four forms and reads `P['ts']` (default 1.0);
  - `strength_oracles.score(P, verbose=False)` unchanged.

- [ ] **Step 1: Write the failing tests.**
  ```python
  import json, os
  import pytest
  from . import strength_model as sm
  from . import strength_oracles as so

  REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
  COMPACT = os.path.join(REPO, "docs", "superpowers", "research", "2026-10-14-strength-redesign", "refit", "compact_T.json")

  def _compact():
      with open(COMPACT, encoding="utf-8") as fh:
          return json.load(fh)

  def test_point_t_is_the_record():
      chosen = _compact()["chosen"]
      for k, v in chosen.items():
          if k == "infeasible":
              continue
          assert sm.POINT_T[k] == v, k

  def test_the_record_score_and_every_oracle_reproduce():
      c = _compact()
      total, rows = so.score(dict(sm.POINT_T), True)
      assert abs(total - c["score"]) < 1e-12
      by = {r[0]: r for r in rows}
      for o in c["oracles"]:
          assert abs(by[o["name"]][1] - o["value"]) < 1e-12, o["name"]

  def test_exact_mode_keeps_every_weighted_pass():
      c = _compact()
      P = dict(sm.POINT_T, exact=True, ts=1.0)
      _, rows = so.score(P, True)
      was = {o["name"]: o for o in c["oracles"]}
      for name, value, lo, hi, miss, weight, src in rows:
          if weight and was[name]["miss"] == 0.0:
              assert lo <= value <= hi, name

  def test_exact_detraining_halves_in_its_half_life():
      P = dict(sm.POINT_T, exact=True, ts=1.0, grace_d=0, detrain_status=0.0)
      b = sm.Body(P, 10.0, 16.5, 13.0, F0L=5.0)
      F0 = b.F0
      gap0 = b.F - F0
      hl_days = 7 * P["detrain_hl_wk"]
      # S = 0, energy balance, no protein: growth and regain are 0, the detraining runs alone
      b.Pk = b.F
      for _ in range(int(round(hl_days))):
          b.day(0.0, 0.0, 0.0)
      assert abs((b.F - F0) / gap0 - 0.5) < 0.01
  ```
  The last test runs with `detrain_status = 0`: with the status term on, the half-life is fixed at the start status and shortens as F falls, so more than half is lost (0.4421 at point T, ruling 13-23). Task 8's kernel test pins the one-day factor with the status term.
- [ ] **Step 2: Run them.** `python -m pytest testing/tests/kernel/test_strength_oracle.py -q`. Expect FAIL (no module).
- [ ] **Step 3: Copy and extend.**
  - Copy `model.py` to `strength_model.py` byte for byte, then append `POINT_T` (built from the JSON at import) and edit `Body.day` only inside `if P.get('exact'):` branches:
    - detraining: `detr = (F − F0) · (1 − exp(−lam · ts · (1 − S/Sm) / 7))`;
    - the grace test: `self.grace > P['grace_d'] / ts`;
    - growth and regain multiplied by `ts`; the peak decay `exp(−dec · ts)`;
    - the surplus arm's `rest = E − grow / ts · RHO_L`, the deficit arm's recomposition `dM −= grow / ts · RHO_L / RHO_F`;
    - the labile decay `dX −= X / x_tau_d` on every day whose surplus arm left `rest <= 0` and on every deficit day, on the remaining store (base `X − fromX`, after the deficit's own `fromX` draw).
  - Copy `oracles.py` to `strength_oracles.py` with `from model import` changed to `from .strength_model import` (and the same for any other module import). Change nothing else.
  - Add a module docstring to each naming the source path, the copy date and ruling 13-2.
- [ ] **Step 4: Run them.** Expect PASS. Record the `exact` re-score's every oracle value in the test file as a pinned table (`EXACT_PINS`), with a test asserting each to 1e-9, so a later kernel or oracle change that moves one is named.
- [ ] **Step 5: Commit** in the worktree (the controller cherry-picks it to `main` after `Task 2: complete`, ruling 13-40). `git commit -m "Plan 13 Task 2: the strength fit's model and oracles tracked, point T reproduced, exact mode pinned" -- testing/tests/kernel/strength_model.py testing/tests/kernel/strength_oracles.py testing/tests/kernel/test_strength_oracle.py`

### Task 2b: The strength-level reference (Opus; pure Python, docs lane on new files; ruling 13-45)
Spec §§ 2, 3.2, 4, 6. The tracked Python reference of the strength model, the counterpart of Task 2's oracle: Tasks 5, 8, 9 and 17 test the kernel against it. It needs only Task 2's `strength_model`, so it runs as soon as Task 2 is on `main`.

**Files:**
- Create `testing/tests/kernel/strength_level.py` and `testing/tests/kernel/test_strength_level.py`.

**Interfaces** (pure Python, no packages; imports `strength_model` only):
- `LEVEL_MODEL`: the strength-model block under its key names (`b`, `Fnm`, `N0`, `startLevel`, `traitShare`, `ffmiNatural`, `Tmax`, `tauUpWk`, `tauDownWk`, `Tgrace_d`, `Wsat`, `yearsTo10`, `perfectS`, `perfectP`, `perfectE`), with `N0` and `startLevel` dicts keyed `STRONG`, `STOUT`, `none`, `FEEBLE`, `WEAK`.
- `F5 = strength_model.F_of(5.0)`, `FC5 = strength_model.F_of(16.5)`, `M5 = F5 - LEVEL_MODEL["Fnm"]`.
- `S_of(F, N0, T)` (0 at or below `Fnm`), `level(F, N0, T, R=None)` and `F_of_level(L, N0, T, R=None)`, where `R=None` reads `R_of(yearsTo10)`, computed once and cached.
- `R_of(years)`: `strength_model.creation(dict(strength_model.POINT_T))`, then `round(years * 365)` days of `fast_grow(perfectS)`, then `S_of(F, 1.0, Tmax)`.
- `trait_start(trait, R=None)` → `F, F0, Fc, Pk`: `F = F_of_level(startLevel, N0, 1)`, `F0 = F5 + traitShare · (F − F5)`, `Fc = min(FC5 + traitShare · (F − F5), FFMI_NATURAL_RAW · H²)` with `FFMI_NATURAL_RAW = ffmiNatural − 6.3 · (1.8 − 1.70)` = 24.37 and the limit 70.4293 kg, `Pk = max(F, F0)` (spec § 3.2, rulings 13-46 and 13-47).
- `neural_day(T, tgrace, S, ts=1.0)` → `T, tgrace` (spec §§ 4, 6): `tgrace + 1` when `S < POINT_T["m"] · Wsat`, else 0; when `tgrace > Tgrace_d / ts`, `T = 1 + (T − 1) · exp(−ts / (7 · tauDownWk))`; else `T = Tmax − (Tmax − T) · exp(−min(1, S / Wsat) · ts / (7 · tauUpWk))`.
- `perfect_run(trait, days)` → the shown level after each day of perfect training from creation: a `strength_model.Body` under `dict(POINT_T, exact=True, ts=1.0)` set to `trait_start`'s `F, F0, Fc, Pk` with 13.005 kg of fat, one `day(perfectS, perfectP, perfectE · 2600, 2600)` and one `neural_day` a day from `T = 1`.

- [ ] **Step 1: The failing tests** (`test_strength_level.py`). Every value is the amendment's verification (`.superpowers/sdd/2026-10-14-plan-13-lean-mass-strength/levelmodel-report.md`):
  ```python
  import math
  import pytest
  from . import strength_level as sl

  MARKS = (28, 70, 182, 365, 730, 1460, 3650)
  TABLE = {  # shown level at MARKS under perfect training, and the cap (Fc at Tmax)
      "none":   ((5.91, 6.49, 7.33, 8.25, 9.26, 10.00, 10.51), 10.78),
      "STOUT":  ((8.01, 8.57, 9.28, 10.06, 10.92, 11.59, 12.08), 12.34),
      "STRONG": ((10.09, 10.59, 11.10, 11.64, 12.25, 12.76, 13.17), 13.40),
      "FEEBLE": ((3.79, 4.37, 5.29, 6.30, 7.39, 8.17, 8.67), 8.93),
      "WEAK":   ((1.85, 2.42, 3.37, 4.41, 5.51, 6.28, 6.76), 6.99),
  }

  def test_R_reads_the_years():
      assert abs(sl.R_of(4.0) - 1.5651015746939971) < 1e-12
      assert abs(sl.R_of(2.0) - 1.4814209731145318) < 1e-12

  def test_the_average_is_level_5_exactly():
      assert sl.S_of(sl.F5, 1.0, 1.0) == 1.0
      assert abs(sl.level(sl.F5, 1.0, 1.0) - 5.0) < 1e-12

  @pytest.mark.parametrize("trait, F, F0, Fc", [
      ("none", 52.020, 52.020, 68.6375),
      ("STOUT", 56.661, 54.341, 70.429),   # clamped (70.958 before ruling 13-47)
      ("STRONG", 60.857, 56.438, 70.429),  # clamped (73.056 before ruling 13-47)
      ("FEEBLE", 47.296, 49.658, 66.275),
      ("WEAK", 42.115, 47.068, 63.685),
  ])
  def test_trait_starts(trait, F, F0, Fc):
      s = sl.trait_start(trait)
      assert abs(s[0] - F) < 5e-4 and abs(s[1] - F0) < 5e-4 and abs(s[2] - Fc) < 5e-4
      assert s[3] == max(s[0], s[1])

  def test_each_start_floors_to_its_own_level():
      for t, L in sl.LEVEL_MODEL["startLevel"].items():
          x = sl.level(sl.trait_start(t)[0], sl.LEVEL_MODEL["N0"][t], 1.0)
          assert math.floor(x + 1e-9) == L

  @pytest.mark.parametrize("trait", list(TABLE))
  def test_perfect_training_table(trait):
      levels = sl.perfect_run(trait, MARKS[-1])
      for day, want in zip(MARKS, TABLE[trait][0]):
          assert abs(levels[day - 1] - want) <= 0.005, (trait, day)
      F, F0, Fc, Pk = sl.trait_start(trait)
      cap = sl.level(Fc, sl.LEVEL_MODEL["N0"][trait], sl.LEVEL_MODEL["Tmax"])
      assert abs(cap - TABLE[trait][1]) <= 0.005

  def test_the_neural_rise_grace_and_decay():
      T, g = 1.0, 0
      for _ in range(28):
          T, g = sl.neural_day(T, g, 20.0)
      assert abs(T - (1.1 - 0.1 * math.exp(-28 / 21))) < 1e-12
      T0 = T
      for _ in range(21):
          T, g = sl.neural_day(T, g, 0.0)
      assert T == T0
      for _ in range(84):
          T, g = sl.neural_day(T, g, 0.0)
      assert abs((T - 1) / (T0 - 1) - math.exp(-1.0)) < 1e-12
  ```
- [ ] **Step 2: Run.** `python -m pytest testing/tests/kernel/test_strength_level.py -q`. Expect FAIL (no module).
- [ ] **Step 3: Write** `strength_level.py` with a module docstring naming the spec sections and ruling 13-45.
- [ ] **Step 4: Run.** Expect PASS. Then pin every `TABLE` value and the five starts to 1e-9 in a `PINS` table read off the run, with a test asserting each, as Task 2's `EXACT_PINS`. Mutations on a scratch copy (`git archive HEAD | tar -x -C <scratch>`): `M5` at a literal 25; F0 at the full lean difference; `Pk = F`; the neural grace on `>=`; R at `T = 1`; each fails a test.
- [ ] **Step 5: Commit** `"Plan 13 Task 2b: the strength-level reference (level, R, trait starts, the neural factor) with the verified table pinned" -- testing/tests/kernel/strength_level.py testing/tests/kernel/test_strength_level.py`.

### Task 3: The mod-wide sex option (Sonnet; `mod/` lane)
Spec § 13.

**Files:**
- Modify `NR_Kernel_Body.lua` (`K.body.effSex`), `NR_Server_Options.lua`, `NR_Server_Nutrients.lua` (lines 370, 372, 395, 439), `NR_Server_Effects.lua` (lines 277, 512), `NR_Kernel_Heal.lua` (line 39–43's sex read), `NR_Client_View.lua` (`V.recompute` at line 168), `42.21/media/sandbox-options.txt`, `Translate/EN/Sandbox.json`.
- Modify `testing/tests/kernel/test_kernel_body.py`, `test_nutrients_shape.py`, `test_effects_shape.py`, `test_client_view_shape.py`; the golden.

**Interfaces:**
- `K.body.effSex(sex, specific)` → `sex` when `specific == true` and `sex == 2`, else `1`.
- `NR.server.options.sexSpecific` (boolean, default false), read by `readLeaf(sv, "SexSpecific", false)`.
- `record.body.sex` keeps the engine's value.

- [ ] **Step 1: The failing tests.**
  ```python
  def test_eff_sex_is_male_unless_the_option_is_on(host):
      assert host.call("body.effSex", 2, False) == 1
      assert host.call("body.effSex", 2, True) == 2
      assert host.call("body.effSex", 1, True) == 1
      assert host.call("body.effSex", 1, False) == 1
  ```
  In `test_nutrients_shape.py`: a female record's requirement map, choline factor, Widmark r and fluids AI equal a male's with `sexSpecific` false, and today's female values with it true. In `test_effects_shape.py`: `rec.R[sex]` and `K.effects.drain`'s `BF_FLOOR` index read the effective sex. In `test_client_view_shape.py`: `V.female` is false for a female player unless `SandboxVars.NR.SexSpecific == true`, and `T.sex()` follows it.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.**
  - `NR_Server_Nutrients`: one local `local sex = K.body.effSex(body.sex, opts.sexSpecific)` per minute, read once at the step's start; `kMul.choline`, `kctx.sex`, `fctx.sex` and `K.acute.alcohol(..., sex, ...)` read it.
  - `NR_Server_Effects`: the same local at line 277 and passed at 512.
  - `NR_Kernel_Heal`: the heal's fallback reads `body.sex` raw (it rebuilds masses, not requirements; Task 12 replaces the fallback).
  - `NR_Client_View.recompute`: `V.female = V.readFemale(player) and V.readSexSpecific()`, with `V.readSexSpecific()` reading `SandboxVars.NR.SexSpecific` in a pcall (false when unreadable).
  - Option block: `option NR.SexSpecific { type = boolean, default = false, page = NutritionRevamp, translation = NR_SexSpecific, }`; translations `Sandbox_NR_SexSpecific` = "Sex-specific values" and its tooltip: "Off: every character uses the male values wherever the mod indexes by sex (requirements, body-fat bands, alcohol, iron, calcium). On: a female character uses the female values."
- [ ] **Step 4: Gates and golden.** Full pytest in its own call. Mutation on a scratch copy (`git archive HEAD | tar -x -C <scratch>`): `effSex` returning `sex` always; the client ignoring the option. Each fails a test. Re-record the golden under **"Plan 13 Task 3: NR.SexSpecific off by default; g5 reads the male values"**, attributing every moved leaf to g5. The report states that the effective-sex local adds no Java call to Nutrients or Effects (it reads the record), so no stub test is needed. § 3 mod gates, full `claims_check` (pin or re-anchor moved pointers).
- [ ] **Step 5: Commit** by pathspec: `"Plan 13 Task 3: NR.SexSpecific, one effective-sex helper, golden re-recorded"`.

### Task 4: Height and the offline calendar pause (Opus; `mod/` lane)
Spec § 2 (H) and § 9.3.

**Files:**
- Modify `NR_Kernel.lua`, `NR_Kernel_Acute.lua` (line 150 removed; line 597 reads `K.HEIGHT_M`), `NR_Kernel_Body.lua` (`body.wday` laid by `new`), `NR_Kernel_Heal.lua`, `NR_Kernel_Store.lua` (INPUTS `body.wday`), `NR_Server_Metabolism.lua` (lines 58–59, 426–469), `NR_Server_Effects.lua` (line 186–187), `NR_Server_Nutrients.lua` (lines 213, 257, 356–357).
- Modify `testing/tests/kernel/test_kernel_acute.py`, `test_kernel_heal.py`, `test_kernel_store.py`, `test_metabolism_shape.py`, `test_effects_shape.py`; the golden.

**Interfaces:**
- `K.HEIGHT_M = 1.70` (ruling 13-4).
- `K.body.calendar(body, ageH, gapped)` → `closes` (0 or 1): when `gapped`, sets `body.wday = math.floor(ageH / 24)` and returns 0; else returns 1 and sets `body.wday` to that day when `math.floor(ageH / 24) > body.wday`, else 0. It never touches `dayIndex`; `K.partition.closeDay` still advances `dayIndex` by 1.
- `body.wday`: laid by `K.body.new` as `math.floor(ageH / 24)`; healed to `math.floor(ageH / 24)`; saved.

- [ ] **Step 1: The failing tests.**
  ```python
  def test_calendar_closes_once_on_a_new_world_day(host):
      b = host.table({"wday": 5, "dayIndex": 5})
      assert host.call("body.calendar", b, 5 * 24 + 23.9, False) == 0
      assert host.call("body.calendar", b, 6 * 24 + 0.1, False) == 1
      assert b["wday"] == 6 and b["dayIndex"] == 5

  def test_calendar_closes_nothing_after_a_gap(host):
      b = host.table({"wday": 5, "dayIndex": 5})
      assert host.call("body.calendar", b, 9 * 24 + 3.0, True) == 0
      assert b["wday"] == 9 and b["dayIndex"] == 5

  def test_bmi_reads_the_shared_height(host):
      assert host.K.HEIGHT_M == 1.70
      assert host.K.acute.HEIGHT_M is None
  ```
  In `test_metabolism_shape.py`: a player away 3 game days returns with `dayIndex`, `eb7`, `p7`, `mass7`, `bandWeek`, `fm`, `lm` unchanged by the return minute, and its next world-day boundary closes exactly one day; `MET.MAX_CLOSES` and `stats.skippedDays` are absent. A Java-call-count stub test: the Metabolism minute makes no more Java calls than at HEAD (§ 6, Plan 11g close rule).
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement.**
  - Metabolism step: `local gapped = stepM > 60` (already computed as `stepM`); replace the `while today > body.dayIndex` loop and the `skippedDays` block with `if K.body.calendar(body, ageH, gapped) == 1 then closeDay(...) end`.
  - Effects line 187: `body.dayIndex - math.floor(body.bornAge / 24) >= EFF.P7_DAYS` stays valid (both count from birth in record days). Read and confirm; no change unless a test fails.
  - Nutrients: `days = body.dayIndex - n.lastDayIndex` is 0 or 1 now; keep the code, note it in its comment.
  - **The ring audit** (spec § 9.3): list every daily or weekly ring and counter in the task report with its writer and whether it advances only at an online close: `p7`, `eb7`, `mass7`, `bandWeek` (shifted by `K.partition.closeDay`/`K.training.closeDay` inside `closeDay` only), `acute.alc7` and `starvedDays` (Nutrients' close, keyed on `dayIndex`), `effects.lastDay`, and the trailing-24 h window (shifted, not integrated, `trailShift`). `sig7`, `grace` and P's decay are Task 8's and close inside `closeDay`. Any ring that advances on world time is a finding fixed in this task.
  - Rewrite the Metabolism limitation line 36 ("a multi-day catch-up runs days 2..n …") to the new rule.
- [ ] **Step 4: Gates, golden, commit.** Mutations: `gapped` ignored; `calendar` closing on `>=`. Golden re-recorded under **"Plan 13 Task 4: the BMI at the shared 1.70 m height (was 1.75); the MET.stats.skippedDays snapshot leaf removed (ruling 13-5)"** (no golden player has a gap over 60 minutes: g4 is away 30, so the calendar moves no value leaf; the removed `skippedDays` leaf is attributed to this cause). Commit: `"Plan 13 Task 4: one 1.70 m height; the record calendar advances on online days only"`.

### Task 5: The constants blocks, the bio scale and the strength level (Opus; `mod/` lane, kernel; waits for Tasks 1, 2 and 2b, ruling 13-39)
Spec §§ 2, 10; ruling 13-45.

**Files:**
- Modify `NR_Kernel_Strength.lua` (a new section at the top; the old functions stay until Task 12).
- Create `testing/tests/kernel/test_strength_parity.py`; modify `test_kernel_strength.py`.

**Interfaces:**
- `K.strength.DEFAULTS`: both constants blocks' keys, one per line, each with its label (the § 10 Basis column; `xpPerSet` labelled with Task 1's run id). `M5` and `R` are not literals: at file load `DEFAULTS.M5 = K.strength.fOfBio(5, DEFAULTS) - DEFAULTS.Fnm`, then `DEFAULTS.R = K.strength.R(DEFAULTS.yearsTo10)`.
- `K.strength.fOfBio(L, P)` → `(P.ffmi5 + (L - 5) * P.ffmiPerLevel) * K.HEIGHT_M * K.HEIGHT_M` (the growth law's coordinate).
- `K.strength.bioLevel(F, P)` → `5 + (F / (K.HEIGHT_M * K.HEIGHT_M) - P.ffmi5) / P.ffmiPerLevel`.
- `K.strength.strengthOf(F, N0, T, P)` → `((F - P.Fnm) / P.M5) ^ P.b * N0 * T`, and 0 when `F <= P.Fnm`.
- `K.strength.level(F, N0, T, P)` → `5 + 5 * (strengthOf(F, N0, T, P) - 1) / (P.R - 1)`: the shown level.
- `K.strength.fOfLevel(L, N0, T, P)` → `P.Fnm + P.M5 * ((1 + (L - 5) * (P.R - 1) / 5) / (N0 * T)) ^ (1 / P.b)`, the inverse of `level` above `5 - 5 / (P.R - 1)`.
- `K.strength.threshold`, `setCap` and `signal` (Task 6's interfaces, written here because `R` needs them; Task 6 keeps their tests).
- `K.strength.R(years)` → the S of the untrained average after `years` of perfect training at `DEFAULTS.Tmax`: from `F = fOfBio(5, DEFAULTS)`, `F0 = F` and `Fc = fOfBio(DEFAULTS.capLevel, DEFAULTS)`, `math.floor(years * 365 + 0.5)` days of `F = F + DEFAULTS.k * (Fc - F) * signal(DEFAULTS.perfectS, s, DEFAULTS) / 7`, with `s` the status from `F`, `F0` and `Fc` (the oracle's `fast_grow`), then `strengthOf(F, 1, DEFAULTS.Tmax, DEFAULTS)`. It reads `DEFAULTS` only, never a server's options. It runs about 1460 steps at file load and at a `yearsTo10` change only, with no clock work (Rule 6).
- `K.strength.shown(L)` → `n, frac` with `n = K.clamp(math.floor(L + 1e-9), 0, K.strength.L_MAX)`; `frac = K.max(0, L - n)` when `0 <= n < 10` and `L >= 0`, else 0. The 1e-9 keeps a start built exactly on its level from flooring one low (Stout's start reads 6.999999999999997).
- `K.strength.status(body)` → `K.clamp((body.lm - body.F0) / (body.Fc - body.F0), 0, 1)`, 0 when `body.Fc <= body.F0` (bio units by construction).

- [ ] **Step 1: The failing tests.**
  ```python
  import json, os
  from . import strength_model as sm
  from . import strength_level as sl

  def _d(host):
      return host.K.strength.DEFAULTS

  def test_defaults_equal_the_oracle_point(host):
      D = _d(host)
      for k, v in sm.POINT_T.items():
          if k in ("fp_knots", "infeasible", "regain_gated", "regain_sum"):
              continue
          assert D[k] == v, k
      knots = D["fp_knots"]
      for i, (x, y) in enumerate(sm.POINT_T["fp_knots"]):
          assert knots[i + 1][1] == x and knots[i + 1][2] == y

  def test_level_block_equals_the_reference(host):
      D = _d(host)
      for k, v in sl.LEVEL_MODEL.items():
          if isinstance(v, dict):
              for t, x in v.items():
                  assert D[k][t] == x, (k, t)
          else:
              assert D[k] == v, k
      assert abs(D["M5"] - sl.M5) < 1e-12
      assert abs(D["R"] - sl.R_of(D["yearsTo10"])) < 1e-9

  def test_bio_scale_matches_the_oracle(host):
      D = _d(host)
      for L in (0.0, 3.0, 5.0, 9.0, 14.0, 16.5, 18.5):
          assert abs(host.call("strength.fOfBio", L, D) - sm.F_of(L)) < 1e-12
          assert abs(host.call("strength.bioLevel", sm.F_of(L), D) - L) < 1e-12

  def test_level_matches_the_reference_and_inverts(host):
      D = _d(host)
      for F in (20.0, 27.0, 42.115, 52.02, 60.857, 73.056):
          for N0 in (0.82, 1.0, 1.14):
              for T in (1.0, 1.05, 1.10):
                  assert abs(host.call("strength.level", F, N0, T, D) - sl.level(F, N0, T)) < 1e-9
      for L in (1.0, 3.0, 5.0, 7.0, 9.0, 12.3):
          F = host.call("strength.fOfLevel", L, 1.07, 1.0, D)
          assert abs(host.call("strength.level", F, 1.07, 1.0, D) - L) < 1e-9

  def test_R_reads_the_years_only(host):
      for y in (1.0, 2.0, 4.0, 10.0):
          assert abs(host.call("strength.R", y) - sl.R_of(y)) < 1e-9

  def test_shown_level_and_bar(host):
      n, frac = host.call("strength.shown", 7.25)
      assert n == 7 and abs(frac - 0.25) < 1e-12
      n, frac = host.call("strength.shown", 6.999999999999997)
      assert n == 7 and frac == 0
      n, frac = host.call("strength.shown", 12.3)
      assert n == 10 and frac == 0
      n, frac = host.call("strength.shown", -0.4)
      assert n == 0 and frac == 0

  def test_status(host):
      b = host.table({"lm": 60.0, "F0": 52.0, "Fc": 68.0})
      assert abs(host.call("strength.status", b) - 0.5) < 1e-12
      b = host.table({"lm": 50.0, "F0": 52.0, "Fc": 52.0})
      assert host.call("strength.status", b) == 0
  ```
  `test_defaults_equal_the_oracle_point` and `test_level_block_equals_the_reference` are the bindings of ruling 13-1 for the two blocks.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement** the blocks and the functions. `shown` returns 0 for a negative level (the floor clamp) with frac 0.
- [ ] **Step 4: Gates** (no golden move: nothing calls the new functions yet; the golden test proves it). Mutations: `ffmiPerLevel` at 0.55; `b` at 0.67; `M5` at a literal 25; `R` read from a server's `k`; `shown` without the clamp; `shown` without the 1e-9. Commit: `"Plan 13 Task 5: the strength constants blocks (point T and the level model), the bio scale and the strength level"`.

### Task 6: Growth: the signal, the threshold, the set cap and the gates (Opus; `mod/` lane, kernel)
Spec § 5.

**Interfaces:**
- `K.strength.threshold(s, P)` → `P.Sg0 * math.exp(P.beta * s)`.
- `K.strength.setCap(s, P)` → `P.Smax + (P.Smax1 - P.Smax) * s`.
- `K.strength.signal(S, s, P)` → `K.max(0, math.sqrt(K.min(S, setCap)) - math.sqrt(threshold)) / (math.sqrt(P.Sref) - math.sqrt(P.Sg0))`.
- `K.strength.fp(p, P)` → `K.interp(P.fp_knots, p)`, the knots already scaled by `params` (Task 11).
- `K.strength.fe(E, s, p, tdee, P)` → the oracle's `fe`: `E0s = P.E0 * (1 - P.E0_drop * s) * (1 + P.a_nov * (1 - s)^2 * K.clamp((p - P.nov_p0) / P.nov_pspan, 0, 1))`; `bal = P.fbal0 * (1 - P.fbal_drop * s) * (1 - P.trained_need * s)`; 0 at `E <= E0s`; `bal * (1 - E / E0s)` for `E < 0`; `bal + (1 - bal) * K.min(1, E / (P.surplus_full * (1 - P.full_drop * s) * tdee))` for `E >= 0`. (`nov_p0` and `nov_pspan` are the oracle's literals for the protein deepening's ramp, not the f_p knots; they are fixed keys of `DEFAULTS`, ruling 13-37.)
- `K.strength.growth(body, S, p, E, tdee, alcGkg, P)` → `grow` kg/day before `ts`: `P.k * (body.Fc - body.lm) * G * fp * fe / 7 * K.partition.gAlc(alcGkg)`; the regain term `lr * (body.Pk - body.lm) * K.min(1, G) * fp * fe / 7` with `lr = ln 2 / P.regain_hl_wk` while `body.lm < body.Pk`; returns `K.max(0, K.max(grow, regain))`.

- [ ] **Step 1: The failing tests** in `test_strength_parity.py`: for a grid of `S in (0, 0.5, 3, 12, 20, 40)`, `s in (0, 0.5, 0.9, 1)`, `p in (0.3, 0.8, 1.3, 2.4)`, `E in (-1200, -500, 0, 130, 400)`, each kernel function equals the oracle's (`sm.Gsig`, `sm.fp`, `sm.fe`) to 1e-12, and:
  ```python
  def test_no_signal_no_growth_whatever_the_protein_and_surplus(host):
      D = host.K.strength.DEFAULTS
      b = host.table({"lm": 52.02, "F0": 52.02, "Fc": 85.3, "Pk": 52.02})
      assert host.call("strength.growth", b, 0.0, 2.4, 400.0, 2600.0, 0.0, D) == 0

  def test_low_volume_stalls_where_the_threshold_meets_the_sets(host):
      D = host.K.strength.DEFAULTS
      s = 0.6
      S = host.call("strength.threshold", s, D)
      assert host.call("strength.signal", S, s, D) == 0
      assert host.call("strength.signal", S * 1.01, s, D) > 0
  ```
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).**
- [ ] **Step 4: Gates and commit.** Mutation: the √ removed; `setCap` flat; `fe`'s status drop removed; `gAlc` dropped. Each fails a test. No golden move. Commit: `"Plan 13 Task 6: the growth law's signal, threshold, set cap and gates"`.

### Task 7: The energy and protein partition (Opus; `mod/` lane, kernel)
Spec § 5.1. The constants are `DEFAULTS`' (`forbes_c`, `wT`, `S_def`, `wP`, `pdef_lo`, `pdef_hi`, `prot_floor`, `x_max_frac`, `x_tau_d`); the partition names no number of its own besides `RHO_LEAN`, `RHO_FAT` and `FAT_CEIL_KCAL` (Hall, Alpert; unchanged). The surplus arm's protein ramp reads `xs_p0` and `xs_pspan` (`(p − xs_p0) / xs_pspan`, the oracle's literal `(p − 0.8) / 0.8`), never `pdef_lo` or `pdef_hi`, which `NR.LeanLossProteinFull` moves (ruling 13-37).

**Interfaces:**
- `K.partition.forbes(fm, P)` → `P.forbes_c / (P.forbes_c + fm)`.
- `K.partition.training(S, P)` → `K.min(1, S / P.S_def)`.
- `K.partition.surplusLean(body, grow, S, p, E, P, ts)` → `dX, dM` (the oracle's `E >= 0` arm with ruling 13-2's `rest` and decay).
- `K.partition.deficitLean(body, grow, S, p, E, P, ts)` → `dF, dX, dM` (the oracle's `E < 0` arm, Alpert's overflow split by `prot`, `lx` paying first, recomposition at `grow / ts`, then the decay).
- `body.lx` is laid by `K.body.new` at 0 (Task 9) and saved (Task 12).

- [ ] **Step 1: The failing tests** in `test_strength_parity.py`: for the Longland, Mettler, Bray and the four § 9 cases' daily inputs (taken from `strength_oracles.py`'s helpers), the kernel's arm equals the oracle `exact=True` arm's `dX`, `dM` and lean change to 1e-12 for one day, from the same body state; plus a case at `pdef_hi = 2.4` showing the surplus arm unmoved while the deficit arm moves, and mass balance. The parity test is given here as prose; the implementer writes it in full and the review checks each assertion against this prose (F40):
  ```python
  def test_surplus_mass_balance_closes(host):
      D = host.K.strength.DEFAULTS
      b = host.table({"lm": 52.0, "lx": 0.0, "fm": 13.0, "F0": 52.0})
      dX, dM = host.call("partition.surplusLean", b, 0.02, 4.0, 1.6, 300.0, D, 1.0)
      kcal = 0.02 * host.K.partition.RHO_LEAN + dX * host.K.partition.RHO_LEAN + dM * host.K.partition.RHO_FAT
      assert abs(kcal - 300.0) < 1e-9
  ```
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** The old arms stay until Task 12.
- [ ] **Step 4: Gates and commit.** Mutations: Forbes' share at `c/(c+2M)`; `prot`'s floor removed; `lx` uncapped; `lx` not paying first. Commit: `"Plan 13 Task 7: the lean partition's surplus and deficit arms with the labile lean"`.

### Task 8: Maintenance, detraining, regain, the peak and the day (Opus; `mod/` lane, kernel)
Spec § 6.

**Interfaces:**
- `K.strength.maintainSets(s, P)` → `P.m * K.strength.threshold(s, P)`.
- `K.strength.detrain(body, S, s, P, ts)` → `detr` kg: advances `body.grace` (+1 when `S < maintainSets`, else 0); when `body.grace > P.grace_d / ts` and `body.lm > body.F0`: `(body.lm - body.F0) * (1 - math.exp(-lam * ts * (1 - S / Sm) / 7))` with `lam = ln 2 / (P.detrain_hl_wk * (1 + P.detrain_status * s))`; else 0.
- `K.strength.peakStep(body, P, ts)`: `body.Pk = K.max(body.Pk, body.lm)`, then `body.Pk = body.lm + (body.Pk - body.lm) * math.exp(-ln 2 / (P.peak_hl_yr * 365) * ts)`.
- `K.strength.day(body, S, p, E, tdee, alcGkg, P, ts)` → `dF, dX, dM`: the oracle's `Body.day` order with `exact=True`: `s`, growth (× `ts`), detraining, the partition arm by the sign of `E`, the floors (`lm >= P.fMinShare * body.F0`, `lx >= 0`, `fm >= P.fmMin`), then `peakStep`, then `neural` (it reads S only, so its place in the order moves nothing else). Writes `body.lm`, `body.lx`, `body.fm`, `body.Pk`, `body.grace`, `body.T`, `body.Tgrace`.
- `K.strength.neural(body, S, P, ts)`: `body.Tgrace` + 1 when `S < P.m * P.Wsat`, else 0; when `body.Tgrace > P.Tgrace_d / ts`, `body.T = 1 + (body.T - 1) * math.exp(-ts / (7 * P.tauDownWk))`; else `body.T = P.Tmax - (P.Tmax - body.T) * math.exp(-K.min(1, S / P.Wsat) * ts / (7 * P.tauUpWk))` (spec §§ 4, 6; ruling 13-45).

- [ ] **Step 1: The failing tests.**
  ```python
  def _days(host, oracle_body, lua_body, n, S, p, E, tdee, ts=1.0):
      D = host.K.strength.DEFAULTS
      for _ in range(n):
          oracle_body.day(S, p, E, tdee)
          host.call("strength.day", lua_body, S, p, E, tdee, 0.0, D, ts)
          assert abs(lua_body["lm"] - oracle_body.F) < 1e-9
          assert abs(lua_body["lx"] - oracle_body.X) < 1e-9
          assert abs(lua_body["fm"] - oracle_body.M) < 1e-9
          assert abs(lua_body["Pk"] - oracle_body.Pk) < 1e-9

  @pytest.mark.parametrize("ts", [1.0, 7.0, 30.0])
  def test_five_years_of_the_anchor_match_the_oracle(host, ts):
      P = dict(sm.POINT_T, exact=True, ts=ts)
      ob = sm.creation(P)
      lb = _lua_body_from(host, ob)
      _days(host, ob, lb, int(5 * 365 / ts), 20.0, 2.0, 130.0, 2600.0, ts)

  def test_detraining_one_day_factor(host):
      ...  # grace past, S = 0: lm - F0 falls by exactly exp(-lam * ts / 7) in one day

  def test_retraining_block_two_over_block_one_is_the_pinned_ratio(host):
      ...  # Räntilä: 10 wk on, 10 wk off, 10 wk on at 12 sets; the ratio of block 2's gain to block 1's lies in the oracle's band (`0.80 <= ratio <= 1.25`, `rantila_block2_over_1`) and equals Task 2's `EXACT_PINS` value (0.93811) to 1e-9; the 0.94 once stated was a rounding of a value below it (ruling 13-22)
  ```
  `_lua_body_from(host, ob)` copies `F, F0, Fc, Pk, M, X, grace` into a Lua table under the kernel's names (`lm, F0, Fc, Pk, fm, lx, grace`).   The two elided bodies are written in full by the implementer from the stated assertions; the Räntilä protocol is `strength_oracles._rantila`'s. The review checks each assertion against this prose.
  Also the spec § 12.1 checks, each with its mutation:
  - the growth anchor: an average character on 20 sets with full gates (`p = 2.0`, `E = 0.10 · tdee`, where `f_e = 1` at every status, so it reproduces `fast_grow`'s anchor; ruling 13-21) reaches bio level 15 at 5 years (± 0.02 bio level); the parity test at `E = 130` keeps the partial-gate path;
  - the strength level: the same run, with `neural` advancing T each day, reads `K.strength.level(lm, 1, T, D)` = 10 at 4 years (± 0.02) and equals `strength_level.perfect_run("none", …)` to 1e-9 at every mark of Task 2b's table (the per-trait runs are Task 9's, once `create` exists);
  - the neural factor against `strength_level.neural_day`, day by day to 1e-12, on 70 days at 20 sets, 140 at 0, 30 at 3 and 70 at 20, at `ts` 1 and 7: the rise, the hold inside the grace, the decay and the retraining;
  - the s = 0.9 gate over 8 weeks: balance ΔF < 0.5 %; +10 % gives ≤ 2 × the balance gain, < 1 %, ≥ 50 % of the weight gain as fat; −500 kcal/day at 3.5 kg of fat gives ΔF ≤ 0;
  - detraining's half-life is 6 weeks after a 14-day grace (`detrain_status` 0 for the novice reading, S2001's population).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).**
- [ ] **Step 4: Gates and commit.** Mutations: Euler detraining; grace `>=`; regain as a sum; the peak not decaying; `ts` not dividing the grace; `neural` decaying inside its grace; T's rise ignoring g; T's decay without `ts`. Commit: `"Plan 13 Task 8: maintenance, detraining, regain, the peak, the neural factor and the kernel day"`.

### Task 9: The creation body table (Opus; `mod/` lane, kernel)
Spec § 3.2; ruling 13-46. Task 10c (Angus, 2026-10-15) replaced the thin targets below with body-fat shares on the muscle pick's lean, added `spec.fmRef` and `K.body.fatStart`, and removed `K.body.EXCLUDES`; the interfaces and tests below are Task 9's as written, and `test_body_create.py` carries Task 10c's.

**Interfaces:**
- The muscle pick reads `P.startLevel[key]` and `P.N0[key]`, with `key = muscle or "none"` (the strength-model block); the old offsets table `K.body.MUSCLE` is not written.
- `K.body.EXCLUDES = { UNDERWEIGHT = { WEAK = true, FEEBLE = true }, VERY_UNDERWEIGHT = { WEAK = true, FEEBLE = true } }` (spec § 3.2's anti-stacking exclusions; Task 16's blocks and Task 17's validation carry the same pairs). Removed in Task 10c.
- `K.body.FAT_FMI = { none = 4.5, OVERWEIGHT = 7.5, OBESE = 10.5 }` (S2056; the default the middle of the male normal 3–6; Obese the middle of class I, 9–12, since Task 10b, Angus 2026-10-15; it was 12.5).
- `K.body.FAT_FMI_F = { none = 7.0, OVERWEIGHT = 11.0, OBESE = 15.0 }` (the middle of S2057's female bands, labelled game choices; read when `sexIdx == 2`, i.e. `NR.SexSpecific` is on and the character is female; ruling 13-31).
- `K.body.THIN = { UNDERWEIGHT = { bmi = 18.0, fmi = 1.5 }, VERY_UNDERWEIGHT = { bmi = 16.5, fmi = 1.0 } }` (WHO grades; S1905 for the fat at BMI 18). Since Task 10c `K.body.THIN = { UNDERWEIGHT = 0.10, VERY_UNDERWEIGHT = 0.065 }`, the start body-fat shares (female values 8 points higher).
- `K.body.create(muscle, weight, P, sexIdx)` → `spec = { lm, F0, Fc, Pk, N0, fm, fatT, thinT, sexIdx }` (rulings 13-30, 13-31, 13-46): `N0 = P.N0[key]`; `F = K.strength.fOfLevel(P.startLevel[key], N0, 1, P)`; `F5 = fOfBio(5, P)`; `F0 = F5 + P.traitShare * (F - F5)`; `Fc = K.min(fOfBio(P.capLevel, P) + P.traitShare * (F - F5), P.ffmiNaturalRaw * H²)` with `P.ffmiNaturalRaw = P.ffmiNatural − 6.3 · (1.8 − K.HEIGHT_M)` (ruling 13-47); `Pk = K.max(F, F0)`; `fm = FAT_FMI[weight or "none"] * H² * F / K.traits.leanAvg()` for a fat or no weight pick (`FAT_FMI_F` when `sexIdx == 2`; scaled by the start lean since Task 10b); for a thin pick `fm = THIN.fmi * H²` and `lm = K.min(F, THIN.bmi * H² - fm)` (ruling 13-14); else `lm = F`. Since Task 10c every pick's `lm = F`, a thin pick's `fm = bf · F / (1 − bf)` (`K.body.fatStart`) and its `fmRef` the no-pick fat on F; every other pick's `fmRef = fm`. `fatT` and `thinT` are the rungs of the weight pick: OVERWEIGHT 1, OBESE 2, UNDERWEIGHT 1, VERY_UNDERWEIGHT 2, else 0 (Emaciated is read as 2); `sexIdx` is carried for `new`. `create` builds an excluded pair by the same rules (the creation handler strips one first, Task 17), so the pick-set test can show why it is excluded.
- `K.body.new(spec, sex, ageH)` replaces today's `new(w, sex, build, l0, traitCarry, r, ageH)`: lays `lm, F0, Fc, Pk, N0, fm, lx = 0, grace = 0, sigDay = 0, sig7 = {0 x7}, T = 1, Tgrace = 0, fatT, thinT` copied from `spec` (`create` returns them), `band` from `K.traits.axes(body, spec.sexIdx)` once Task 10 lands (ruling 13-30), `fmRef = fm`, `lm0dis = lm`, `sex`, `bornAge`, `wday`, the rings (`mass7` at `lm + lx + fm`), the window, and every field today's `new` lays that survives Task 12's removals. Task 12 switches the callers; until then `new` keeps its old name and this one is written as `K.body.newLean` so both coexist, renamed in Task 12.

- [ ] **Step 1: The failing tests,** against spec § 3.2's table through Task 2b's reference:
  ```python
  from . import strength_level as sl
  H2 = 1.70 * 1.70
  MUSCLE = (None, "WEAK", "FEEBLE", "STOUT", "STRONG")
  WEIGHT = (None, "OVERWEIGHT", "OBESE", "UNDERWEIGHT", "VERY_UNDERWEIGHT")
  THIN = ("UNDERWEIGHT", "VERY_UNDERWEIGHT")

  def _legal(m, w):
      return not (w in THIN and m in ("WEAK", "FEEBLE"))

  @pytest.mark.parametrize("muscle", MUSCLE)
  def test_muscle_starts_match_the_reference(host, muscle):
      D = host.K.strength.DEFAULTS
      key = muscle or "none"
      s = host.call("body.create", muscle, None, D)
      F, F0, Fc, Pk = sl.trait_start(key)
      for k, v in (("lm", F), ("F0", F0), ("Fc", Fc), ("Pk", Pk)):
          assert abs(s[k] - v) < 1e-9, k
      assert s["N0"] == D["N0"][key]
      L = host.call("strength.level", s["lm"], s["N0"], 1.0, D)
      assert host.call("strength.shown", L)[0] == D["startLevel"][key]
      assert abs(s["fm"] - 4.5 * H2 * F / (18.0 * H2)) < 1e-9   # 4.5 * H2 before Task 10b

  @pytest.mark.parametrize("weight, fat_kg, lean", [
      ("OVERWEIGHT", 21.675, None), ("OBESE", 30.345, None),   # Obese 36.125 before Task 10b
      ("UNDERWEIGHT", 4.335, 47.685), ("VERY_UNDERWEIGHT", 2.89, 44.795),
  ])
  def test_weight_picks(host, weight, fat_kg, lean):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", None, weight, D)
      assert abs(s["fm"] - fat_kg) < 1e-9
      assert abs(s["lm"] - (lean if lean is not None else sl.F5)) < 1e-9

  @pytest.mark.parametrize("muscle", MUSCLE)
  def test_set_point_and_cap_move_by_the_share(host, muscle):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", muscle, None, D)
      d = D["traitShare"] * (s["lm"] - sl.F5)
      assert abs(s["F0"] - (sl.F5 + d)) < 1e-9
      lim = (D["ffmiNatural"] - 6.3 * (1.8 - 1.70)) * 1.70 ** 2
      assert abs(s["Fc"] - min(host.call("strength.fOfBio", D["capLevel"], D) + d, lim)) < 1e-9
      assert s["Fc"] <= lim + 1e-9                      # every trait is at most the natural limit
      assert (s["Fc"] == lim) == (muscle in ("STRONG", "STOUT"))   # only Strong's and Stout's are clamped

  def test_thin_is_depletion_below_the_peak(host):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", "STRONG", "VERY_UNDERWEIGHT", D)
      assert s["lm"] < s["F0"] < s["Pk"]
      assert abs(s["Pk"] - sl.trait_start("STRONG")[0]) < 1e-9

  @pytest.mark.parametrize("muscle", MUSCLE)
  def test_perfect_training_from_each_start_matches_the_reference(host, muscle):
      ...  # K.body.newLean(create(muscle, nil, D), 1, 0); 3650 days of K.strength.day at perfectS, perfectP, perfectE · 2600, tdee 2600;
           # K.strength.level(lm, N0, T, D) equals strength_level.perfect_run's value to 1e-9 at every mark; FEEBLE and WEAK stay below 10

  @pytest.mark.parametrize("weight, fmi", [(None, 7.0), ("OVERWEIGHT", 11.0), ("OBESE", 15.0)])
  def test_female_fat_picks_sit_in_the_female_bands(host, weight, fmi):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", None, weight, D, 2)
      assert abs(s["fm"] - fmi * 1.70 * 1.70) < 1e-9

  @pytest.mark.parametrize("sexIdx", [1, 2])
  def test_creation_pick_sets_every_point_giver_costs_the_body(host, sexIdx):
      D = host.K.strength.DEFAULTS

      def body(m, w):
          s = host.call("body.create", m, w, D, sexIdx)
          return host.call("strength.level", s["lm"], s["N0"], 1.0, D), s["fm"], s["fatT"]

      for m in MUSCLE:
          for w in WEIGHT:
              if not _legal(m, w):
                  continue
              L, fm, fatT = body(m, w)
              if m in ("WEAK", "FEEBLE"):
                  assert L <= body(None, w)[0] - 0.5, (m, w)
              if w in THIN:
                  assert L <= body(m, None)[0] - 0.5, (m, w)
              if w in ("OVERWEIGHT", "OBESE"):
                  _, fm0, fatT0 = body(m, None)
                  assert fatT > fatT0 and fm > fm0, (m, w)
      # the pairs the rule excludes because they cost nothing
      for m, w in (("WEAK", "UNDERWEIGHT"), ("WEAK", "VERY_UNDERWEIGHT"), ("FEEBLE", "UNDERWEIGHT")):
          assert body(m, w)[0] > body(m, None)[0] - 0.5, (m, w)
      for w in THIN:
          for m in ("WEAK", "FEEBLE"):
              assert host.K.body.EXCLUDES[w][m] is True
  ```
  The kg columns are spec § 3.2's at 1.70 m (2.89 m²), unrounded. The elided body of `test_perfect_training_from_each_start_matches_the_reference` is written in full by the implementer from its stated assertions; the review checks each one. Feeble with Very Underweight would cost 0.68 levels; it is excluded with the other three pairs by the same rule (spec § 3.2), so the test asserts only its exclusion.
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).**
- [ ] **Step 4: Gates and commit.** Mutations: the set point at the full lean difference; the cap unmoved by the share; `Pk = F`; thin raising F; `N0` left out of `fOfLevel`; an exclusion dropped; `sexIdx` ignored; fat at FMI 11 for Obese (the draft in `spec-review.md`'s Appendix 7). Commit: `"Plan 13 Task 9: the creation body table (starts through N0 and lean, the half-share set point and cap, the anti-stacking pick sets)"`.

### Task 10: The trait axes with damping (Opus; `mod/` lane, kernel)
Spec § 8.

**Files:**
- Create `mod/.../shared/NR_Kernel_Traits.lua`; create `testing/tests/kernel/test_kernel_traits.py`.
- Modify `mod/.../shared/NR_Kernel_Body.lua`: the one line in `K.body.new` that lays `body.band` from `K.traits.axes` (ruling 13-30).

**Interfaces:**
- `K.traits.FAT_CUTS = { { 6, 9 }, { 9, 13 } }` by sex index (FMI, kg/m²; S2056 male, S2057 female), `K.traits.FAT_WORDS = { "overweight", "obese" }`, `K.traits.FAT_MARGIN = 0.3`.
- `K.traits.THIN_CUTS = { 18.5, 17, 16 }`, `K.traits.THIN_WORDS = { "underweight", "veryUnderweight", "emaciated" }`, `K.traits.THIN_MARGIN = 0.5` (WHO; game-choice margins). Since Task 10c (Angus, 2026-10-15) the thin axis reads body-fat share, `K.traits.thinReading(fm, lm, sex)` against `THIN_CUTS = { 0.12, 0.08, 0.05 }` with `THIN_MARGIN = 0.005` and `THIN_F_OFFSET = 0.08` for effective sex 2, height-free; the BMI read below is Task 10's.
- `K.traits.held(rung, x, cuts, margin, up)` → the new rung: from `rung`, step deeper while the next cut is passed by more than `margin`, step back while the current cut is undone by more than `margin`; `up` true for the fat axis (higher is worse), false for thinness.
- `K.traits.axes(body, sex)` → writes `body.fatT` and `body.thinT` (rung numbers 0..2 and 0..3) from `fmi = K.traits.fatIndex(body.fm, body.lm)` = `body.fm · Favg / (H² · body.lm)` (the lean-scaled index since Task 10b, Angus 2026-10-15: each fat cut and its margin scale by `lm / Favg`, `Favg = K.traits.leanAvg()` = `fOfBio(5, DEFAULTS)`; it was `body.fm / H²`) and `bmi = (body.lm + body.fm) / H²` (ruling 13-15), clears `fatT` to 0 while `thinT > 0` (precedence), and returns the band word: the thin word, else the fat word, else `"normal"`.
- `K.traits.WANT(fatT, thinT)` → the five weight-band trait names each true or false (`OBESE`, `OVERWEIGHT`, `UNDERWEIGHT`, `VERY_UNDERWEIGHT`, `EMACIATED`).
- `K.body.create` (Task 9) returns the picked rungs `fatT` and `thinT` (OVERWEIGHT 1, OBESE 2, UNDERWEIGHT 1, VERY_UNDERWEIGHT 2), and `K.body.new` copies them; this task adds the line `body.band = K.traits.axes(body, spec.sexIdx)` to `new` and owns nothing else of it (ruling 13-30).

- [ ] **Step 1: The rows.** The cuts rest on the settled rows S2056 (men) and S2057 (women, Kelly 2009 Table 4); each constant's comment names its row. No science check is needed.
- [ ] **Step 2: The failing tests.**
  ```python
  H2 = 1.70 * 1.70

  def _b(host, fm, lm, fatT=0, thinT=0):
      return host.table({"fm": fm, "lm": lm, "fatT": fatT, "thinT": thinT})

  def test_overweight_needs_the_margin(host):
      b = _b(host, 6.2 * H2, 52.0)
      assert host.call("traits.axes", b, 1) == "normal"
      b = _b(host, 6.4 * H2, 52.0)
      assert host.call("traits.axes", b, 1) == "overweight"

  def test_overweight_holds_inside_the_margin_on_the_way_back(host):
      b = _b(host, 5.8 * H2, 52.0, fatT=1)
      assert host.call("traits.axes", b, 1) == "overweight"
      b = _b(host, 5.6 * H2, 52.0, fatT=1)
      assert host.call("traits.axes", b, 1) == "normal"

  def test_thinness_excludes_the_fat_traits(host):
      b = _b(host, 7.0 * H2, 44.0 - 7.0 * H2, fatT=1)   # BMI 15.2 with FMI 7: thin wins
      assert host.call("traits.axes", b, 1) == "emaciated"
      assert b["fatT"] == 0

  def test_creation_picks_sit_inside_their_held_ranges(host):
      D = host.K.strength.DEFAULTS
      for muscle, weight, word in ((None, "UNDERWEIGHT", "underweight"), (None, "VERY_UNDERWEIGHT", "veryUnderweight"),
                                   (None, "OVERWEIGHT", "overweight"), (None, "OBESE", "obese"), ("STOUT", "UNDERWEIGHT", "underweight")):
          for sexIdx in (1, 2):
              s = host.call("body.create", muscle, weight, D, sexIdx)
              assert host.call("traits.axes", s, sexIdx) == word
  ```
- [ ] **Step 3–4: Run (FAIL), implement, run (PASS).** Mutations: no margin; precedence removed; female cuts used when the option is off (the caller passes `K.body.effSex`).
- [ ] **Step 5: Commit** the kernel, its test and the `NR_Kernel_Body.lua` band line: `"Plan 13 Task 10: the fat, muscle and thinness axes with damping"`.

### Task 11: The sandbox options and `K.strength.params` (Sonnet; `mod/` lane)
Spec § 10.

**Files:**
- Modify `42.21/media/sandbox-options.txt`, `Translate/EN/Sandbox.json`, `NR_Kernel_Strength.lua` (`params`), `NR_Kernel.lua` (`K.readLeaf`, moved from the local at `NR_Server_Options.lua:31`; ruling 13-32), `NR_Server_Options.lua` (calls `K.readLeaf`); tests `test_kernel_strength.py`, `testing/tests/kernel/test_translations.py` (the key set), and the options test that reads the file.

**Interfaces:**
- `K.strength.params(sv)` → `P, fellBack`: a new table copied from `DEFAULTS`, each option in the table below read through `K.readLeaf`, the one clamp rule (out of range clamps for a double, reads the default for the integer), then `P.k = DEFAULTS.k * StrengthRate`, the knots' x values scaled by `StrengthProteinFull / 1.6`; then `P.R = DEFAULTS.R` when `P.yearsTo10 == DEFAULTS.yearsTo10`, else `K.strength.R(P.yearsTo10)`, cached by the year value so a rebuild for another option never re-runs it, and `P.M5 = DEFAULTS.M5` (ruling 13-45); then the guard, in bio levels: with `s15 = (15 - 5) / (P.capLevel - 5)` when `P.capLevel > 15`, if `threshold(s15, P) >= setCap(s15, P)` then `beta`, `Sg0`, `Smax1` revert to `DEFAULTS` and `fellBack = true`.
- `NR.server.options.strength` = `P`, rebuilt only when a strength leaf changed (one comparison loop at the poll; the table is not rebuilt per minute, Rule 6); a fallback logs once at level 1 with the three values read.

| Option | Type | Min | Max | Default | Key |
|---|---|---|---|---|---|
| `NR.StrengthTimeScale` | double | 0.25 | 30 | 1.0 | `ts` |
| `NR.StrengthXPPerSet` | double | 50 | 2000 | Task 1's reading | `xpPerSet` |
| `NR.StrengthIncidentalWeight` | double | 0 | 1 | 0.35 | `incidental` |
| `NR.StrengthCapLevel` | double | 12 | 20 | 16.5 | `capLevel` |
| `NR.StrengthTraitShare` | double | 0 | 1 | 0.5 | `traitShare` |
| `NR.StrengthYearsToLevel10` | double | 1 | 10 | 4 | `yearsTo10` (R recomputed) |
| `NR.StrengthNeuralMax` | double | 1.0 | 1.15 | 1.10 | `Tmax` |
| `NR.StrengthNeuralRiseWeeks` | double | 1 | 8 | 3 | `tauUpWk` |
| `NR.StrengthNeuralDecayWeeks` | double | 4 | 26 | 12 | `tauDownWk` |
| `NR.StrengthNeuralGraceDays` | integer | 0 | 60 | 21 | `Tgrace_d` |
| `NR.StrengthNeuralSaturationSets` | double | 1 | 12 | 5 | `Wsat` |
| `NR.StrengthRate` | double | 0.25 | 4 | 1.0 | `k` multiplier |
| `NR.StrengthThreshold` | double | 0.25 | 1.0 | 0.5 | `Sg0` |
| `NR.StrengthThresholdRise` | double | 0 | 4 | 3.0 | `beta` |
| `NR.StrengthTrainedSetCap` | double | 8 | 30 | 12 | `Smax1` |
| `NR.StrengthProteinFull` | double | 1.0 | 3.0 | 1.6 | knots' x scale |
| `NR.StrengthDeficitZero` | double | −2000 | −200 | −650 | `E0` |
| `NR.StrengthDeficitZeroStatusDrop` | double | 0 | 0.9 | 0.5 | `E0_drop` |
| `NR.StrengthNoviceDeficitDepth` | double | 0 | 10 | 6.0 | `a_nov` |
| `NR.StrengthBalanceGate` | double | 0.5 | 1.0 | 1.0 | `fbal0` |
| `NR.StrengthBalanceGateStatusDrop` | double | 0 | 0.7 | 0.5 | `fbal_drop` |
| `NR.StrengthSurplusFull` | double | 0.02 | 0.30 | 0.10 | `surplus_full` |
| `NR.StrengthSurplusFullStatusDrop` | double | 0 | 0.9 | 0.5 | `full_drop` |
| `NR.StrengthTrainedNeedsSurplus` | double | 0 | 1 | 0 | `trained_need` |
| `NR.LeanLossTrainingProtect` | double | 0 | 0.9 | 0.35 | `wT` |
| `NR.LeanLossProteinProtect` | double | 0 | 0.9 | 0.6 | `wP` |
| `NR.LeanLossProtectFloor` | double | 0 | 0.5 | 0.10 | `prot_floor` |
| `NR.LeanLossProteinFull` | double | 1.2 | 3.0 | 1.6 | `pdef_hi` |
| `NR.StrengthMaintainShare` | double | 0.1 | 1.0 | 0.333 | `m` |
| `NR.StrengthGraceDays` | integer | 0 | 60 | 14 | `grace_d` |
| `NR.StrengthDetrainHalfLifeWeeks` | double | 2 | 26 | 6 | `detrain_hl_wk` |
| `NR.StrengthDetrainStatusSlowing` | double | 0 | 4 | 2.0 | `detrain_status` |
| `NR.StrengthRegainHalfLifeWeeks` | double | 1 | 26 | 6 | `regain_hl_wk` |
| `NR.StrengthPeakHalfLifeYears` | double | 0.25 | 20 | 2 | `peak_hl_yr` |
| `NR.SexSpecific` | boolean | — | — | false | Task 3 |

The defaults column restates spec § 10 for the option file; the kernel's defaults are `DEFAULTS` (ruling 13-1), and a test asserts every option's declared default equals the `DEFAULTS` value of its key (the multiplier and scale options at 1.0 and 1.6), so a refit that moves `DEFAULTS` fails the test until the option file follows. `NR.StrengthMaintainShare`'s default 0.333 is the option file's three-place value; `params` maps a value within 0.0005 of 0.333 to `DEFAULTS.m` exactly.

- [ ] **Step 1: The failing tests:** every option parses (the existing option-file test pattern); each tooltip key exists in `Sandbox.json`; `params` with no options equals `DEFAULTS` key by key; `StrengthRate = 2` doubles `k`; `StrengthThreshold = 1.0` with `StrengthThresholdRise = 4` falls back with `fellBack == true`; `StrengthCapLevel = 14` skips the guard; `StrengthYearsToLevel10 = 2` gives `P.R == strength_level.R_of(2.0)` to 1e-9; `StrengthRate = 2` leaves `P.R` at `DEFAULTS.R`; a rebuild for another leaf does not call `K.strength.R` (a counting stub); out-of-range doubles clamp; `K.readLeaf` clamps exactly as the Options adapter's local did (its existing test moves with it).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Tooltips (in `Sandbox.json`): one plain sentence per option saying what it scales and its unit; `NR.StrengthMaintainShare`'s states its range (0.1 to 1.0) and makes no claim about 0; `NR.StrengthTimeScale`'s says "the biology clock: 1.0 is one biological day per game day; weekly sets are still counted over 7 game days".
- [ ] **Step 4: Gates and commit.** The golden does not move (nothing calls `params` yet; the golden test proves it and the report says so); if the options table gains a snapshot leaf, it is re-recorded under **"Plan 13 Task 11: the strength options table in the options snapshot"**, attributing that leaf. `"Plan 13 Task 11: the strength sandbox options and the load-time guard"`.

### Task 12: The switch: the day close, first sight, the removals (Opus; `mod/` lane)
Spec §§ 4 (Replaced), 5, 6, 9.1, 9.2, 9.4.

**Files:**
- Modify `NR_Server_Metabolism.lua` (`closeDay` at 301–320, `ensureBody` at 148–170, `heal` at 332–345, `MET.GUARD` at 74–76, the step at 452–458, `MET.BUILD_TRAITS`, `responder`), `NR_Kernel_Strength.lua`, `NR_Kernel_Partition.lua`, `NR_Kernel_Training.lua`, `NR_Kernel_Body.lua`, `NR_Kernel_Heal.lua`, `NR_Kernel_Store.lua` (`INPUTS`, `bodyBase`), `NR_Server_Strength.lua` (the minute: the ceiling and policy call removed; the carry reads `K.strength.traitCarry(native level)` until Task 14 switches it to `body.wroteL`, ruling 13-28), `NR_Kernel_Mirror.lua` (the `dStr`/`dHyp` and `shownL` reads removed, and `body_weight` reads `fm + lm + lx`; Task 18 adds the new keys), `NR_Kernel_Energy.lua` (`:264` and `:267` read `fm + lm + lx`; ruling 13-34).
- Delete `NR_Server_Training.lua` and `testing/tests/kernel/test_training_shape.py` (ruling 13-18).
- Create `tools/bench_day_close.py`.
- Tests: rewrite `test_kernel_strength.py`, `test_kernel_partition.py`, `test_kernel_training.py`, `test_kernel_body.py`, `test_kernel_heal.py`, `test_kernel_store.py`, `test_metabolism_shape.py`, `test_strength_shape.py`, `test_heal_once.py`; the golden.

**Interfaces:**
- **`closeDay(body, w, immobilised, ageH, ironGrade, debtH)` in Metabolism** becomes, in this order:
  1. the disuse count, as today;
  2. `local sum = K.strength.signalClose(body)` (shifts `sig7`, lands `sigDay` in slot 7, zeroes `sigDay`, returns the ring's sum); `local S = sum / P.xpPerSet`;
  3. `local p = body.pDay / w`; `local tdee = K.max(body.eeDay, K.energy.ree(body.lm))`;
  4. immobilised: `K.partition.disuse(body)`'s `dFM, dLM` applied under `P.fmMin` and `P.fMinShare · body.F0` (ruling 13-35), `lx` untouched, `body.grace` advanced by `K.strength.detrain`'s counter rule only; else `K.strength.day(body, S, p, body.ebDay, tdee, body.alcDay / w, P, P.ts)`, which also advances T (Task 8); an immobilised day still runs `K.strength.neural(body, S, P, P.ts)`;
  5. `body.fmRef = K.max(body.fmRef, body.fm)`;
  6. `body.band = K.traits.axes(body, K.body.effSex(body.sex, opts.sexSpecific))` and `body.traitsDirty = true` when the band word changed;
  7. `body.S = S` (the closed week's sets, for the mirror and `T`);
  8. `K.training.closeDay`, TAC, `pPrevKg`, `inDayClosed`, `K.partition.closeDay`, AT, as today (TAC's `gEnergy` reads `body.lm`, unchanged).
  `P` is `NR.server.options.strength`, falling back to `K.strength.DEFAULTS` when the options table is absent.
- **`MET.ensureBody`**: when `record.body` is nil, reads the band traits held (ruling 13-6) into `muscle` and `weight`, builds `K.body.new(K.body.create(muscle, weight, P, K.body.effSex(sex, opts.sexSpecific)), sex, ageH)`, and stamps `body.levelDue = true` so Task 14's minute writes the level once.
- **`K.body.new`** (renamed from `newLean`) replaces the old constructor; `split` and its tables, `BUILD_*`, `band(w)`'s callers outside Weight (Weight's goes in Task 15) are removed. `body.traitCarry` and `body.delta` (the latter laid from it at `NR_Kernel_Body.lua:213`) are no longer laid, and `ensureBody` reads no `getMaxWeightDelta`.
- **`K.store.bodyBase(rb, ageH)`**: `K.body.new(K.body.create(nil, nil, P0), sex, lastAgeH)` with `P0` the server's `NR.server.options.strength` where the adapter has it, else `K.strength.DEFAULTS` (so a tuned server's cap holds), with the stored `lm`, `fm`, `lx` overlaid by the INPUTS copy.
- **`K.heal.body(body, ageH)`**: a non-finite `lm`, `fm`, `F0`, `Fc` or `Pk` heals to the no-trait body's value (`K.body.create(nil, nil, P0)`, `P0` as for `bodyBase`); `lx`, `grace`, `Tgrace`, `sigDay` and each `sig7` slot to 0; a non-finite `N0` to the no-trait 1.0 and a non-finite `T` to 1; `wday` as Task 4; `S` to 0. The `l0` argument and the Strength read in Metabolism's `heal` go.
- **`K.store.INPUTS`**: add `body.F0`, `body.Fc`, `body.Pk`, `body.lx`, `body.grace`, `body.sigDay`, `body.sig7.*`, `body.S`, `body.fatT`, `body.thinT`, `body.band`, `body.wroteL`, `body.wday`, `body.N0`, `body.T`, `body.Tgrace`; remove `body.fm0`, `body.lm0`, `body.l0`, `body.r`, `body.traitCarry`, `body.strAgeH`, `body.vStr`, `body.vHyp`, `body.vStrHigh`, `body.n`, `body.nPeak`, `body.tPeakD`, `body.nHist.*`, `body.cumDef`, `body.shownL`, `body.riseHeldH`, `body.lastFallAge`.
- **The weight readers**: `fm + lm` becomes `fm + lm + lx` in `NR_Server_Weight` (the slot), `K.partition.closeDay`'s `mass7`, `K.body.new`'s rings and every `w = body.fm + body.lm` in Metabolism, Strength, Nutrients and Effects that means body mass, and the other total-mass readers: `NR_Kernel_Energy.lua:264` and `:267`, `NR_Kernel_Mirror.lua:56`, `NR_Kernel_Heal.lua:140`, `NR_Kernel_Store.lua:194` and `NR_Server_Weight.lua:119` (rulings 13-20, 13-34; grep `fm + body.lm` and `fm + lm` and list each site in the report).
- **Removed** (spec § 9.2): `K.strength.neuralStep`, `closeDay`, `floorF`, `fSlow`, `ceiling`, `xpLevel`, `policy` and their constants (`N_TARGET_K` through `RISE_HOLD_H`, `FALL_MIN_H`, `MEM_*`, `CUMDEF_*`, `E_ENERGY_MAX`, `DISUSE_K`, `DISUSE_T`, `F_MIN`, `F_MAX`, `LEVELS_PER_DOUBLING`); the partition's and training's lists in the file table; `K.partition.FM_MIN` and `LM_MIN_RATIO` (now `DEFAULTS.fmMin` and `fMinShare`); Metabolism's `responder`, `MET.BUILD_TRAITS`, the step's `neuralStep`, `doses`, `decay`, `loadMinute`, `actionMinute` calls, and `MET.GUARD`'s removed names (`n`, `nPeak`, `tPeakD`, `cumDef`, `vStr`, `vHyp`).

- [ ] **Step 1: The seam, then the bench before.** First, in its own commit before any other edit (ruling 13-33): the one-line seam `MET._closeDay = closeDay` under a `NR_BENCH` global guard in `NR_Server_Metabolism.lua` (no behaviour change), with § 3's mod gates and the full `claims_check` (the seam shifts Metabolism's lines: re-anchor); commit `"Plan 13 Task 12: the day-close bench seam"`. Then create `tools/bench_day_close.py` (it loads `server_host.Host`, builds 60 records with bodies, times `MET._closeDay` and prints µs per player-close) and run `python tools/bench_day_close.py --players 60 --closes 200` on that commit, a real tree. Ledger the figure.
- [ ] **Step 2: Write the failing tests.** The Metabolism shape tests: one close runs `signalClose`, `day` and `axes` once each and writes `body.S`; an immobilised close runs disuse and no growth (ruling 13-13); a first sight with STRONG and OBESE held builds Strong's F0 and Obese's fat; `ensureBody` no longer reads `getMaxWeightDelta` or `getPerkLevel`; the store round-trips every new INPUTS path and drops the removed ones; the heal rebuilds a NaN `F0` to the no-trait body's. A Java-call-count stub test: the Metabolism minute makes no more Java calls than at HEAD, and the report states the actual delta (the build-trait reads leave the minute; no per-minute call is added).
- [ ] **Step 3: Implement the switch and the removals.** Delete each dead test by name: list every deleted test in `task-12-report.md` (the neural, memory floor, cumulative deficit, ceiling, policy, xpLevel, resistance-event, dose, lean-gain, gEnergy, headroom and split tests, and `test_training_shape.py` whole). A frozen-lib test that reads a removed field is deleted by name under a ledgered ruling (Global Constraints).
- [ ] **Step 4: Run** full pytest in its own call. Mutations on a scratch copy: the close skipping `signalClose`; `S` from the ring without today's slot; `lx` left out of the weight; first sight reading the native level. Each fails a test.
- [ ] **Step 5: Bench after** with the same command; ledger the delta. A rise above 25 % of the before figure is reported with its cause before the commit (Rule 6).
- [ ] **Step 6: Golden, gates and commit.** Re-record under **"Plan 13 Task 12: the lean-mass body (creation table at first sight, the growth law and lean partition at the day close; the neural term, the clamp policy and the resistance doses removed)"**, attributing every moved leaf (the masses from first sight, the minute-90 close, the removed fields). § 3 mod gates, `bus_inventory --check`, full `claims_check`: every pointer into a removed line is pinned to its last-holding commit, every moved line re-anchored (§ 6). Commit by pathspec, the deletions included: `"Plan 13 Task 12: the switch to the lean-mass body; the old Strength model and the resistance side removed"`.

### Task 13: The `AddXP` capture (Opus; `mod/` lane)
Spec § 4.

**Files:**
- Modify `NR_Server_Strength.lua`, `NR_Kernel_Strength.lua`; tests `test_strength_shape.py`, `test_kernel_strength.py`.

**Interfaces:**
- `K.strength.proteinFactor(store)` → 1.5 when `50 < store < 300`, 0.7 when `store < -300`, else 1 (#2112).
- `K.strength.capture(amount, store, sandboxMult, bookMult, fitness, P)` → the signal XP: 0 for a non-finite or non-positive amount; else `amount / proteinFactor(store) / sandboxMult / K.max(1, bookMult)`, times 1 when `fitness`, else `P.incidental`. A `sandboxMult` that is not a positive finite number reads 1.
- `STR.onXp(player, perk, amount)`: Strength only; returns at once under `STR.pinning`; resolves the record without creating one (Training's `bodyOf`, moved here); reads the protein store (`getNutrition():getProteins()`), the sandbox multiplier (`SandboxVars.MultiplierConfig`, by Task 0 Step 1's field names), the book multiplier (`getXp():getMultiplier(perk)`), and `fitness = NR.server.fitness.typeOf(username) ~= nil` (no Java); adds `capture(...)` into `body.sigDay`; then, when the native level differs from `body.wroteL`, stamps `body.levelDue = true` (Task 14 replaces the stamp with the `STR.repin` call; ruling 13-29). One pcall; counts `stats.captures`, `stats.ignored`, `stats.failures`.
- Wired at `OnServerStarted` on the server: `Events.AddXP.Add(STR.onXp)`.

- [ ] **Step 1: The failing tests.**
  ```python
  @pytest.mark.parametrize("store, f", [(0, 1.0), (60, 1.5), (299.9, 1.5), (300, 1.0), (-301, 0.7), (-300, 1.0)])
  def test_protein_factor(host, store, f):
      assert host.call("strength.proteinFactor", store) == f

  def test_capture_divides_the_chain_and_weights_the_source(host):
      D = host.K.strength.DEFAULTS
      assert abs(host.call("strength.capture", 9.0, 60, 2.0, 1.0, True, D) - 3.0) < 1e-12
      assert abs(host.call("strength.capture", 6.0, 0, 1.0, 1.0, False, D) - 6.0 * D["incidental"]) < 1e-12
      assert host.call("strength.capture", -1.0, 0, 1.0, 1.0, True, D) == 0
      assert abs(host.call("strength.capture", 6.0, 0, 0.0, 1.0, True, D) - 6.0) < 1e-12
  ```
  Shape tests: an `AddXP` for Fitness adds nothing; a Strength event during a recorded set adds the full share, outside it the incidental share; the pinning flag blocks capture; a player with no record creates none; a grant that moves the native level off `wroteL` stamps `body.levelDue`.
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: protein factor not divided; the incidental weight applied to Fitness sets; capture during pinning.
- [ ] **Step 4: Golden and commit.** The golden fires no `AddXP`, so it does not move; the golden test proves it and the report says so. Commit: `"Plan 13 Task 13: the AddXP capture with the multiplier chain divided out"`.

### Task 14: The level write, the park and BeyondTen (Opus; `mod/` lane)
Spec § 7. The route is ruling 13-8's branch as Task 0 measured it; the pin is ruling 13-9's.

**Files:**
- Modify `NR_Server_Strength.lua`, `NR_Kernel_Strength.lua`; tests `test_strength_shape.py`, `test_kernel_strength.py`; `NR_Server_Metabolism.lua` (the close sets `body.levelDue = true`); `testing/tests/kernel/golden_trace.py` (the stand-in player gains `LevelPerk`, `LoseLevel`, `getXp():setXPToLevel` and a global `addXp`, recording their calls; ruling 13-36); the golden.

**Interfaces:**
- `K.strength.TRAIT_CARRY = { WEAK = 0.75, FEEBLE = 0.9, STOUT = 1.25, STRONG = 1.5 }` (#2144) and `K.strength.traitCarry(n)` → `TRAIT_CARRY[bandOf(n)] or 1` (ruling 13-7). Both are brought forward to Task 12 (ruling 13-28); this task only switches the carry's argument to `body.wroteL`.
- `K.strength.pinXp(n, frac, totals)` → the target XP: `totals[n] + frac * (totals[n + 1] - totals[n])` for `n <= 9`; `totals[9]` for `n == 10`.
- `STR.writeLevel(player, body, ctx)` (`ctx` optional): `L = K.strength.level(body.lm, body.N0, body.T, P)` (the shown level, ruling 13-45); `n, frac = shown(L)`; steps the native level to `n` by the measured route; then:
  - `n <= 9`: pins XP to `pinXp(n, frac, totals)` (ruling 13-9);
  - `n == 10` and BeyondTen absent: parks with `setXPToLevel(perk, 9)`;
  - `n == 10` and `BeyondTen ~= nil and BeyondTen.API_VERSION == 1` (rulings 13-24, 13-42): never writes native XP; on every write sets `BeyondTen.SetStoredXP(player, Perks.Strength, v)` with `v = BeyondTen.GetTotalMasteryCost(min(math.floor(L), 15)) + frac · (cost(next) − cost(floor(L)))`, which reads 0 + frac · cost(11) for L in [10, 11) and `cost(15)` for L >= 15, by the signatures Task 0 Step 1 read;
  - stamps `body.wroteL = n`, re-applies the band only on the fallback route (`STR.remap`), pushes traits when the set changed (`NR.pushTraits`), and sets `body.levelDue = false`.
- `STR.repin(player, body)`: the `AddXP` listener's call when a grant crossed a level (native ≠ `body.wroteL`): `writeLevel` without reading the clock. It replaces Task 13's `body.levelDue = true` stamp in `STR.onXp` (ruling 13-29).
- The minute (`STR.minute`): when `body.levelDue` or the native level differs from `body.wroteL` (one `getPerkLevel` read, as today), `writeLevel`; then the carry with `traitCarry(body.wroteL)` (replacing Task 12's read of the native level's band). Metabolism's close (in the Files) sets `body.levelDue = true`.
- The guard (ruling 13-10): `STR.installLevelGuard()` at `OnServerStarted` wraps `xpUpdate.checkForLosingLevel(playerObj, perk)` once (a global sentinel `NR_StrengthGuardInstalled`, set by the mod and read by Task 19; the Fitness wrapper's shape): for Strength with native level 10 and the record's `wroteL == 10`, return; else call the saved original.

- [ ] **Step 1: The failing tests.** `pinXp` at (7, 0.25) reads 127500 + 0.25 · 90000; at 10 reads 337500. Shape tests:
  - a level drop from 7 to 5 steps twice through the route stub and pins XP at level 5's total plus the fraction;
  - the minute rewrites after an admin `setPerkLevelDebug` (the #2740 re-assertion);
  - at 10 without BeyondTen: XP parked at 337500, a granted 100 raises the stub's XP and the listener re-parks it;
  - with a BeyondTen stub (the global `BeyondTen` with `API_VERSION = 1`): no native XP write at 10, `SetStoredXP` called with the cost of level 12 for L = 12.0, with `frac · cost(11)` for L = 10.4 and with the cost of level 15 for L = 16.2 (each L set through `fOfLevel`; 16.2 lies above every default cap, so the clamp is reached only on a tuned server);
  - the guard returns for a parked Strength and calls the original for Fitness;
  - the carry uses `TRAIT_CARRY` for the written band;
  - a Java-call-count stub: the minute's calls without a due write equal today's (one level read, the carry reads).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: no park at 10; the pin at the level total without the fraction; BeyondTen's native write not skipped; the guard calling the original for Strength.
- [ ] **Step 4: Golden, gates, commit.** Re-record under **"Plan 13 Task 14: the Strength level written from lean mass at the day close, with the XP pin"** (the golden's players start at perk 5 with xp 260; the first-sight write moves `perk`, `xp` and the write counters). The commit message names the stand-in change beside this cause (ruling 13-36). Commit: `"Plan 13 Task 14: the level write, the level-9 park, BeyondTen and the level-10 guard"`.

### Task 15: The trait writes; the weight band refresh retired (Opus; `mod/` lane)
Spec § 8.

**Files:**
- Modify `NR_Server_Weight.lua` (`needsRepair`, `WGT.BAND_TRAIT`, lines 137–150), `NR_Kernel_Body.lua` (`band(w)` removed); tests `test_weight_shape.py`, `test_kernel_body.py`; the golden.

**Interfaces:**
- `WGT.writeTraits(player, body, ctx)` (`ctx` optional): when `body.traitsDirty` or the held set differs from `K.traits.WANT(body.fatT, body.thinT)` (the existing repair read, now against the axes), add and remove through `getCharacterTraits():add/remove` with the registry objects, `NR.pushTraits(player, WGT.stats)` once, `B.markBand(username)` when `body.band` changed, and clear `traitsDirty`. `applyTraitFromWeight` is never called.
- The weight slot writes `fm + lm + lx` (Task 12's sum).

- [ ] **Step 1: The failing tests:** an Overweight axis adds OVERWEIGHT and removes the other four with one push; an admin removal of OBESE under an obese axis is re-added the next minute; `applyTraitFromWeight` is never called (a stub that raises); the minute makes no more Java calls than at HEAD when nothing differs (the stub count).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: the push missing; the old band refresh left in.
- [ ] **Step 4: Golden and commit.** Re-record under **"Plan 13 Task 15: the weight-band traits from the § 8 axes (vanilla's band refresh retired)"**. Commit: `"Plan 13 Task 15: the body-composition trait writes; applyTraitFromWeight retired"`.

### Task 16: The restated trait blocks and their translations (Sonnet; `mod/` lane)
Spec § 3.1. Runs only if Task 0's checks 1–3 held.

**Files:**
- Create `mod/NutritionRevamp/common/media/scripts/NR_Traits_Body.txt`.
- Modify `common/media/lua/shared/Translate/EN/UI.json`; tests `test_translations.py` and a new `testing/tests/kernel/test_trait_script.py`.

**The content:** one `module Base { … }` holding 10 `character_trait_definition base:<id>` blocks, each copied whole from vanilla's `scripts/generated/characters/character_traits.txt` (lines 1014 weak, 325 feeble, 910 stout, 922 strong, 743 obese, 788 overweight, 978 underweight, 1002 very underweight, 1037 weight gain, 1049 weight loss; the id exactly as vanilla's block names it) with only these changes:

| Block | `Cost` | `IsProfessionTrait` | `XPBoosts` | `MutuallyExclusiveTraits` | `GrantedTraits` |
|---|---|---|---|---|---|
| Weak | −10 (vanilla) | false | removed | vanilla's (feeble, stout, strong) plus underweight and very underweight (ruling 13-46; removed in Task 10c) | — |
| Feeble | −6 (vanilla) | false | removed | vanilla's plus underweight and very underweight (ruling 13-46; removed in Task 10c) | — |
| Stout | 6 (vanilla) | false | removed | vanilla's | — |
| Strong | 10 (vanilla) | false | removed | vanilla's | — |
| Overweight | −6 | false | removed | vanilla's plus obese | — |
| Obese | −10 | false | removed | vanilla's (already lists overweight, underweight, very underweight) | — |
| Underweight | −6 | false | removed | vanilla's plus every missing one of obese, overweight, very underweight, weak, feeble | — |
| Very Underweight | −10 | false | removed | vanilla's plus every missing one of obese, overweight, underweight, weak, feeble | — |
| Weight Gain | −2 (vanilla) | false | — | vanilla's | removed |
| Weight Loss | −2 (vanilla) | false | — | vanilla's | removed |

Every block keeps every vanilla key the table does not change, read off the blocks (the 42.21 blocks carry no `Texture` key), except `UIDescription`, which points at the mod key `UI_NR_trait_<id>desc` (ruling 13-25). The file is CRLF-free, and `mod_lint.py`'s script-basename rule passes (the basename is mod-unique).

`UI.json` defines the ten new keys `UI_NR_trait_<id>desc`, in plain words:
- Weak, Feeble, Stout, Strong: "Starts weaker (or stronger): Strength N at the start, from less (or more) muscle and a lower (or higher) innate strength per kilo of muscle. Half of the muscle difference is permanent; the rest fades without training (or, for the weaker traits, comes back with it)." with N the start level (`startLevel`: 1, 3, 7, 9); no cap number is named, since a refit moves it (rulings 13-1, 13-25, 13-46). Weak's and Feeble's also say they cannot be taken with Underweight or Very Underweight.
- Overweight, Obese: "Starts carrying more body fat (about X kg). Fat is lost or gained by eating." with X from Task 9's table.
- Underweight, Very Underweight: "Starts underfed: low body fat and some muscle lost, which comes back quickly with food and training."
- Weight Gain, Weight Loss: vanilla's sentence without the granted-trait clause (read the vanilla string first).
(`UI_NR_Row_body_level` is Task 18's, not this task's.)

- [ ] **Step 1: The failing test** (`test_trait_script.py`): parses the file; asserts the 10 ids, each block's `Cost` and `IsProfessionTrait` per the table, no `XPBoosts` in the 8 body blocks, no `GrantedTraits` in Weight Gain and Weight Loss, every in-family exclusion and the four thin-against-Weak-or-Feeble pairs (ruling 13-46) present in both directions, and every vanilla key besides those four present (compared against a frozen copy of the 10 vanilla blocks the test carries as a string, read once from the install by the implementer). `test_translations.py` keeps `test_shape` and `test_no_vanilla_key_redefined` unchanged (the new keys start with `UI_NR_` and are not vanilla's) and extends `test_every_ui_key_is_read` with the keys the script file references, read off `NR_Traits_Body.txt`.
- [ ] **Step 2–3: Run (FAIL), write, run (PASS).** `mod_lint`, `release_pack check`, `kahlua_lint`, `hotpath_lint`, `science_check --scan mod` (the costs are Angus's; the file carries a header comment naming the ruling, § 11).
- [ ] **Step 4: Commit:** `"Plan 13 Task 16: the 10 body trait blocks restated, with their descriptions"`.

### Task 17: The `OnNewGame` creation handler with validation (Opus; `mod/` lane)
Spec § 3.2. Runs only if Task 0's check 4 held; validation only if check 5 held.

**Files:**
- Create `mod/.../server/NR_Server_Creation.lua`; modify `NR_Server_Players.lua` (the `OnNewGame` handler at 221–237 fires `P.onNewGame` after `store.reset`); tests: new `testing/tests/kernel/test_creation_shape.py`; `testing/tests/kernel/golden_trace.py` (the stand-in gains the `getDescriptor` and `CharacterTraitDefinition` stubs, ruling 13-36); the golden.

**Interfaces:**
- `P.onNewGame` (a list, `P.onFirstSight`'s pattern): fired with `(username, player, record)` after a successful `store.reset`; a pending reset fires it from `P.makeReset`.
- `CRE.validate(player)` → the list of stripped trait names: ruling 13-16's formula over `getCharacterTraits():getKnownTraits()` (walked with `size()`/`get(i)`), the server's definitions (`CharacterTraitDefinition.getCharacterTraitDefinition`), profession cost read off `player:getDescriptor()`; strips and reverts boosts, logs each strip at level 1.
- `CRE.picks(player)` → `muscle, weight`: the held muscle and weight-band traits after validation.
- `CRE.onNewGame(username, player, record)`: validate; `record.body = K.body.new(K.body.create(muscle, weight, P, K.body.effSex(sex, opts.sexSpecific)), sex, ageH)`; `getNutrition():setWeight(lm + lx + fm)`; `STR.writeLevel(player, record.body)`; `WGT.writeTraits(player, record.body)` (the band traits final, spec § 3.2 step 3, so a Weight Gain → Out of Shape swap is undone only for the five weight-band and four muscle traits; Fitness band traits are vanilla's and stay, § 14). The restated blocks remove the cause of vanilla's Weight Gain → Out of Shape swap (no Fitness `XPBoosts`, no `GrantedTraits`), so spec § 3.2 step 3's example no longer arises; the close updates it; counts `stats.created`, `stats.stripped`.
- Guarded by `NR.isServer()`; every Java read through `NR.call`.

- [ ] **Step 1: The failing tests** (server stand-ins, `test_strength_shape.py`'s pattern): Strong + Overweight builds Strong's start F (`strength_level.trait_start("STRONG")`, 60.86 kg), its N0 and Overweight's fat and writes weight F + 21.675; the level write lands 9 with STRONG; Weak + Underweight (excluded, ruling 13-46) loses the later pick; an over-budget list loses its last non-free entries until legal, each logged; Overweight + Obese (exclusive) loses the later; a stripped trait with a Strength XP boost has its level reverted; a respawn's `OnNewGame` builds a fresh body; with `sexSpecific` on, a female Overweight pick builds the female band's fat (11.0 kg/m²).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: validation skipped; the weight write left to vanilla's `applyWeightFromTraits`; the trait write before the level write (the swap then wins).
- [ ] **Step 4: Golden and commit.** Re-record under **"Plan 13 Task 17: the creation handler builds g3's respawn body from its picks"** (g3's respawn at minute 101; the stand-in's descriptor and trait-definition stubs are named in the commit beside this cause, ruling 13-36). Commit: `"Plan 13 Task 17: the OnNewGame creation handler with pick validation"`.

### Task 18: The panel's Strength row (Sonnet; `mod/` lane)
Ruling 13-19.

**Files:**
- Modify `NR_Kernel_Mirror.lua` (`K.mirror.body`), `NR_Kernel_View.lua` (`K.view.rows` after the body-fat row), `UI.json` (this task owns `UI_NR_Row_body_level` = "Strength"; Task 16 does not add it); tests `test_kernel_mirror.py`, `test_kernel_view.py`, `test_client_panel_shape.py`.

**Interfaces:**
- `m.body_level = K.strength.level(body.lm, body.N0, body.T, P)`, with `P` passed by `K.mirror.body`'s caller (the server's `NR.server.options.strength`, else `DEFAULTS`), because R moves with `NR.StrengthYearsToLevel10` (ruling 13-45); `K.mirror.body(m, body, P)` gains the argument; `m.body_sets = body.S`; `body_shownL`, `body_dStr`, `body_dHyp` removed (grep the client for readers first).
- `K.view.push(rows, "body_level", "UI_NR_Row_body_level", K.view.fmt(math.floor(mm.body_level * 10) / 10, 1), 2, false)`.

- [ ] **Step 1–3:** the failing tests (a level 12.34 mirror shows "12.3", a level 9.96 shows "9.9" (truncated, never rounded up to 10.0 beside a native 9); a body-less mirror shows No data), implement, pass. Golden: the mirror's sends are counted, not kept, so the golden does not move; if a mirror key-count leaf moves, it is re-recorded under **"Plan 13 Task 18: the mirror's body_level and body_sets keys replace body_shownL, body_dStr and body_dHyp"**, attributing each moved leaf.
- [ ] **Step 4: Commit:** `"Plan 13 Task 18: the panel shows the true Strength level"`.

### Task 19: Live: the BeyondTen run (Opus; live; one session)
Spec § 12.2.

**Files:** `testing/experiments/x43_strength_lib.py` (on `xlib.py`, from `x42_levers_lib.py`), `x431_beyondten.py`, `testing/profiles/x43-beyondten.toml` (the staged release copy, § 5; PZTestKit, NutritionRevamp, BeyondTen from workshop `3765241705` by path; `Nutrition = false`; `DayLength = 1`), `testing/tests/test_x43_strength_lib.py`.

- [ ] **Step 0: The harness read (its own commit before the run, § 5, ruling 13-26).** Add server `bt.stored <user> <Perk>` → `{ok, loaded, stored}` at the end of `PZTestKit_Server.lua` (CRLF; edit with `newline=''` and preserve the endings): a pcall'd `BeyondTen.GetStoredXP(player, Perks[<Perk>])`, with `loaded = false` and `stored = nil` when the global `BeyondTen` is absent. `luabalance` (HEAD copy first, then the tree), `kahlua_lint`, `bus_inventory`, `claims_check --staged` and the full `claims_check` → 0 with the `#2808`/`#1235` update. Commit `"Plan 13 Task 19: harness bt.stored"`.
- [ ] **Step 1: Offline tests**, each grade with a failing case, against the staged copy and a real run layout (§ 5).
- [ ] **Step 2: The run.** read the admin's `body.N0` and `body.T` (`lua.read`), then `record.set` its `body.lm` to `fOfLevel(12.3, N0, T)` (the driver's copy of `strength_level.F_of_level` at the run's R; N0 and T are re-read before each set) and `body.levelDue` true; after the next minute read: native Strength 10, native XP 337500 or BeyondTen's own park, BeyondTen's stored XP for 12.3 (`bt.stored`), the panel mirror's `body_level`. Then a 1000-XP `xp.grant`: the capture's `sigDay` rises by the grant's share; the native level stays 10. Then `record.set` `body.lm` to `fOfLevel(9.5, N0, T)` with `levelDue`: native 9, XP at level 9's total plus half its cost, STRONG held on both sides. Read the guard's sentinel `NR_StrengthGuardInstalled` (`lua.read`, a type read) and grade behaviour: a forced ten-minute rust pass on the parked level-10 Strength leaves the level at 10. Which wrapper is outermost is recorded as a reading only (ruling 13-43).
- [ ] **Step 3:** The report with the do-not-cite leaves and candidate claims; the controller commits the artifact folder in its own commit with its artifacts row and re-anchor (ruling 13-38).

### Task 20: Live: the offline-gap run (Opus; live; one session)
**Files:** `x432_offline.py`, `testing/profiles/x43-offline.toml` (staged copy; `Nutrition = false`; `DayLength = 1`).

- [ ] **Step 1: Offline tests.**
- [ ] **Step 2: The run.** Read the record whole (`lua.read record:<user>`), detach the client, raise the time multiplier (restored from the value read before, § 5) until 3 game days pass on the server, return the multiplier, re-attach the client (never under a near-stopped clock, #3788), read the record whole again at the first minute after first sight and again after the next world-day boundary. Grade: `dayIndex`, `sig7`, `p7`, `eb7`, `mass7`, `bandWeek`, `grace`, `Pk`, `lm`, `fm`, `lx` unchanged across the gap; the vanilla Strength XP unchanged (vanilla rust skips offline players); exactly one close after the next boundary.
- [ ] **Step 3:** Report; the controller commits the artifact folder in its own commit with its artifacts row and re-anchor (ruling 13-38).

### Task 21: Live: the creation run (Opus; live; one session)
**Files:** `x433_creation.py`, `testing/profiles/x43-creation.toml` (fixture `two`; staged copy; `[sandbox] Nutrition = false`, `DayLength = 1`; ruling 13-44).

- [ ] **Step 1: Offline tests.**
- [ ] **Step 2: The run.** Five respawns of the user client through x192's route, each with `creation.picks`: (a) none; (b) Strong + Overweight; (c) Strong + Very Underweight; (d) Feeble + Obese + Overweight (illegal: exclusive) with extra over-budget traits; (e) Weak + Underweight (illegal: excluded, ruling 13-46). Each: the record's `lm`, `fm`, `F0`, `Fc`, `Pk`, `N0`, the server and client weight, Strength level (the client's from client-side `perk.xp`), trait list (same-second pairs), and the server log's strip lines. Grade against Task 9's table and rulings 13-16 and 13-46.
- [ ] **Step 3:** Report; the controller commits the artifact folder in its own commit with its artifacts row and re-anchor (ruling 13-38). The report also tells Angus that the thin picks lower lean, so vanilla's band swap gives Underweight (level 3.75) and Very Underweight (level 2.89) a Feeble trait, and Strong with Very Underweight (level 3.83) shows Feeble: they are point sources that carry Feeble's engine penalties until the lean comes back, and a player may read this as a bug.

### Task 22: Live: the growth smoke (Opus; live; one session)
**Files:** `x434_growth.py`, `testing/profiles/x43-growth.toml` (staged copy; `[sandbox.NR] StrengthTimeScale = 30`, `StrengthIncidentalWeight = 1`; `Nutrition = false`; `DayLength = 1`).

- [ ] **Step 1: Offline tests,** including the replay: the driver's grade replays the run's own recorded day-close inputs (S, p, E, tdee) through the kernel (`K.strength.day` via lupa) and compares the live `lm` and `T` per close (ruling 8-R: live against its own replay, never against a study).
- [ ] **Step 2: The run.** For 3 game days: grant `xpPerSet · 20 / 7` Strength XP a game day in 10 server `xp.grant` calls (the anti-cheat bound kept per check), place `body.pDay` and `body.ebDay` before each close with `record.set` (p = 2.0 g/kg, E = +260 kcal), and read the record at each close. Grade: each close's ΔF equals the replay to 1e-6 kg and its T to 1e-9; the native level follows `floor(level(lm, N0, T) + 1e-9)`; the band trait follows the level.
- [ ] **Step 3:** Report; the controller commits the artifact folder in its own commit with its artifacts row and re-anchor (ruling 13-38).

### Task 23: The registers and the pages (Opus; docs lane; the Plan 11g Task 9 process)
- [ ] **Step 1: The artifacts rows are already in** (each run's artifact commit carried its row, do-not-cite keys and `artifacts.md` re-anchor, ruling 13-38); this task writes the claims only. The full `claims_check` → 0 first.
- [ ] **Step 2: The delta** (`.superpowers/sdd/<plan>/task-23-delta.tsv`), with ids reserved from the ledger's next id:
  - Task 0's readings as M rows (one per check) and the Step 1 jar reads as C rows; Task 1's XP per set; the live rows of Tasks 19–22;
  - the mod's mechanism rows as `C/inference` with `repo:` pointers (the growth law, the partition, the creation table, the axes, the capture, the level write, the calendar) where a sentence owns them (ruling T12-1);
  - **the stale rows:** `#0529` corrected (its "60-minute default" to the jar's 90-minute default, `SandboxOptions.<init> @110–@120 L70`, `getDayLengthMinutes @0–@66 L555–L561`, read on 42.21) by a correction pass under § 6's fill rule; `#3344` re-read first and only what is wrong in it corrected (its claim says "a 60-minute day (DayLength 3)", not a default); `#2115` and `#2116` superseded by successors read on 42.21 (`lua:lua/server/XpSystem/XpUpdate.lua:32-37`, `jar:IsoPlayer.isRandXp @0–@81 L9626–L9633`: one roll a real second, 1 in 20), every page tagging them moved in the same commit (§ 4 item 4);
  - the rules the new design overturns: `#2902` (the `setPerkLevelDebug` clamp rule on `areas/body-effects.md#rules`) superseded by the level-write rule this plan measured; `#2701` qualified for the level-10 park under ruling 13-10; `#2705` (a mod effect's own trait) rewritten to state that a mod owning the band traits writes them from its own axes; the testing-your-mod clamp readings `#2894`, `#2896`, `#2897`, `#2898` and `#2881` (the band-anchored split) given bounds naming the removed code (`#2894` to `#2898` are M rows with `run:` pointers, so nothing is pinned for them; only `repo:` pointers are pinned, to the last commit holding the code);
  - the science rows S1935 and S0065's per-meal reading qualified or superseded by the newer rows, as spec § 12.3 lists.
- [ ] **Step 3: The pages,** each sentence named in the delta's `owner` column:
  - `docs/areas/body-effects.md`: `#perk-level` (the clamp paragraph, lines 137–155), `#traits` (the weight refresh paragraph), `### Level clamp against experience clamp`, and the rules above;
  - `docs/facts/perks-and-strength.md`: `#xp-grants` line 110–111 (the carry roll) and `#trait-remap`;
  - `docs/facts/body-and-weight.md`: `#weight-traits` (the bands' Lua route under `Nutrition = false`, Task 0 Step 1's reading) and the creation weights;
  - `docs/areas/testing-your-mod.md` lines 185, 198–207;
  - `docs/areas/open-questions.md`: any question this plan settles, and S2046's open question kept.
  - `page_lint` on each touched page → 0.
- [ ] **Step 4: Process.** A trial apply on a `git archive` copy (§ 6), a whole-delta Opus review, the controller's apply with `tools/claims_delta.py` and the fill step, `--fix-tags` once, `claims_check --staged` → 0, the full `claims_check` → 0.

### Task 24: The close (controller; Opus whole-pass review)
- [ ] **Step 1:** The whole-pass review (structure, performance and the fit's parity included), one consolidated fix wave, its re-review. A fix-wave change to a code path a live run measured is re-smoked or named as a skew note (ruling 13-39).
- [ ] **Step 2:** The spec's corrections: § 7's `BT` wording to the global `BeyondTen` (ruling 13-24); § 3.2 step 3's "Out of Shape after Weight Gain" example (the restated blocks remove the cause, Task 17); § 10's `NR.StrengthMaintainShare` (range 0.1 to 1.0, no "0 never detrains"). Then `mod/NutritionRevamp/README.md` (the Strength and traits sections) and `CHANGELOG.md` folded into the 1.0.0 entry (the mod is unreleased).
- [ ] **Step 3:** Every § 3 gate; reset the pytest baseline by name (the deleted tests listed in Task 12's report) in CLAUDE.md § 3; update CLAUDE.md § 2 if a fixture or build changed; the memory file and `MEMORY.md` (§ 8).
- [ ] **Step 4:** Push; report to Angus: the Task 0 verdicts and branches taken, the XP-per-set reading, the bench before and after, the live readings, every ruling, and the mechanism candidates noticed.

---

## Self-Review

**Coverage (spec section → task):**

| Spec | Task |
|---|---|
| § 1 Goal | 5–18 |
| § 2 the strength level (S, N0, T, R), the bio scale, H shared with K.acute, the panel's true level | 2b, 4, 5, 8, 9, 11, 14, 18 |
| § 3.1 the 8 offered traits, costs, restated blocks, exclusions, Weight Gain/Loss, descriptions | 16 (Task 0 checks 1–3) |
| § 3.2 validation, the body table (N0, the trait starts, the half-share set point and cap, the Weak floor), thin depletion and the thin exclusions (fat-only thin picks with no exclusions since Task 10c), the pick-set test, fat bands by sex, weight, the final trait write | 2b, 9, 10, 16, 17 (Task 0 checks 4–5) |
| § 4 capture, multipliers, source weights, conversion, the calibration, T's rise, XP never moves the level, Training's resistance side replaced | 1, 8, 12, 13, 14 (Task 0 check 7) |
| § 5 growth, the gates, low-volume stall, `lx` | 6, 8 |
| § 5.1 the partition | 7 |
| § 5.2 the fit (point T) | 2, the constants block, 5 |
| § 6 maintenance, grace, detraining (exact), starvation, P, regain, T's grace and decay | 2b, 8 |
| § 7 the level write from the shown level, the park, the band swap, BeyondTen and how far above 10 | 14, 19 (Task 0 checks 6, 8, 9) |
| § 8 the axes, fat bands, precedence, damping, writes, the band refresh retired | 10, 15 |
| § 9.1 the new fields (`N0`, `T` and `Tgrace` included) | 8, 9, 12 |
| § 9.2 the removals | 12 (and 13-18's ruling on Training) |
| § 9.3 offline time and the ring audit | 4, 20 |
| § 9.4 Rule 6 | 12 (bench), 4, 12, 14, 15 (call-count stubs) |
| § 10 options (the strength-model options and R's recompute included), the guard, kept-out options | 11 (with `K.readLeaf` moved to the kernel) |
| § 11 rulings | the constants, rulings 13-45 and 13-46, Tasks 2b, 5, 9, 16, 17 |
| § 12.1 kernel tests with mutations | 2b, 5–10 |
| § 12.2 live: Task 0, calibration, BeyondTen, offline gap; plus creation and growth | 0, 1, 19–22 (the harness reads: Task 0's `perk.xp` and recorder, Task 19's `bt.stored`) |
| § 12.3 registers | 23 (the claims; the artifacts rows land at each run's own commit) |
| § 13 the sex option | 3, 10 (ruling 13-17) |
| § 14 out of scope | Task 17 leaves Fitness bands to vanilla; the carry formula untouched (ruling 13-7 keeps vanilla's constructor table) |

**Placeholders.** The XP-per-set default is Task 1's reading by design, with the provisional value and its fallback rule stated. The female FMI cuts are the settled row S2057. BeyondTen's call signatures and the creation-screen formula are Task 0 reads that land in its report before the tasks that use them. Two kernel test bodies in Task 8 and Task 7's parity test are given as stated assertions with their protocol named; the implementer writes each in full and the review checks every assertion against its prose; every other test is in full.

**Name and type consistency.** `K.strength.DEFAULTS`, `params`, `fOfBio`, `bioLevel`, `strengthOf`, `level`, `fOfLevel`, `R`, `neural`, `shown`, `status`, `threshold`, `setCap`, `signal`, `fp`, `fe`, `growth`, `maintainSets`, `detrain`, `peakStep`, `day`, `signalClose`, `proteinFactor`, `capture`, `pinXp`, `traitCarry`, `TRAIT_CARRY`; `K.partition.forbes`, `training`, `surplusLean`, `deficitLean`; `K.body.create`, `new`, `calendar`, `effSex`, `EXCLUDES`, `FAT_FMI`, `THIN`; `K.traits.axes`, `held`, `WANT`, `fatIndex`, `leanAvg`; the body fields `lm`, `fm`, `lx`, `N0`, `T`, `Tgrace`, `F0`, `Fc`, `Pk`, `grace`, `sigDay`, `sig7`, `S`, `fatT`, `thinT`, `band`, `wroteL`, `levelDue`, `traitsDirty`, `wday` are used identically in Tasks 4–22. `K.body.newLean` exists only between Tasks 9 and 12. `strength_level`'s `LEVEL_MODEL`, `R_of`, `trait_start`, `neural_day` and `perfect_run` are used identically in Tasks 2b, 5, 8, 9 and 17. The body keeps the name `lm` for F, as spec § 9.1 states. `K.readLeaf`, `K.body.FAT_FMI_F` and the `sexIdx` argument of `K.body.create` are used identically in Tasks 9–12 and 17.
