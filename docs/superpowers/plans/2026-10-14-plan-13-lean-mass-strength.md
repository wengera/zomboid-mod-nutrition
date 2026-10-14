# Plan 13: Lean-mass Strength and body-composition traits — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Strength level a reading of the character's lean mass. Vanilla Strength XP becomes a training signal. Lean mass grows only when the signal, protein and energy act together, under the fitted growth law of point T. The weight and strength traits describe body composition: they are offered at creation for points, set the starting body, and switch in play from three daily axes. Nothing changes while a player is offline.

**Architecture:**
- **One constants table.** `K.strength.DEFAULTS` in `NR_Kernel_Strength.lua` holds every fitted and game-choice constant of the growth law, the energy gate and the lean partition. Its values are point T's (`compact_T.json` "chosen") under the oracle's own key names. `K.strength.params(sv)` merges the sandbox options over it once per change. Every kernel function takes that table as `P`. Nothing else in the mod restates a point-T number.
- **The kernel** (pure, lupa-tested, one statement a line):
  - `K.strength`: the FFMI scale, the signal, the gates, growth, regain, detraining, the peak, the day orchestration, the XP capture arithmetic and the params guard;
  - `K.partition`: the surplus and deficit lean arms with the labile lean `lx` (the old lean-gain product is removed);
  - `K.body`: the creation body table (`K.body.create`) and the new `K.body.new`;
  - `K.traits` (new file `NR_Kernel_Traits.lua`): the fat, muscle and thinness axes with damping.
- **The server:**
  - `NR_Server_Metabolism`: the day close (once per online game day), the calendar pause, first sight from held traits;
  - `NR_Server_Strength`: the `AddXP` capture, the level write with the level-9 park and BeyondTen, the per-minute re-assertion and carry;
  - `NR_Server_Weight`: the weight slot and the § 8 trait writes (the vanilla band refresh is retired);
  - `NR_Server_Creation` (new): the `OnNewGame` creation handler with pick validation;
  - `NR_Server_Training` is deleted (its whole content was the resistance side).
- **Content:** `common/media/scripts/NR_Traits_Body.txt` restates 10 trait blocks; translations; 28 sandbox options.

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
- **The `mod/` lane is serial.** Tasks 3 to 18 edit `mod/` one at a time, in order. Tasks 2, 23 and the live tasks' libs run in the docs or tests lane beside them, on disjoint files. No live boot overlaps an offline `mod/` edit (§ 5).
- **Refactor heavily as you go** (Angus, 2026-10-12). Each code task names its refactor scope, and each review judges structure and performance beside correctness.
- **No backward compatibility.** The mod is unreleased. Removed fields (`l0`, `lm0`, `shownL`, `n`, `nPeak`, `nHist`, `cumDef`, `vStr`, `vHyp`, `vStrHigh`, `riseHeldH`, `lastFallAge`, `r`, `fm0`) are dropped from `K.store.INPUTS`, never migrated, and a corrupt record heals fresh.
- **Rule 6.** The `AddXP` capture is an event-driven add with no clock work. Growth, the traits and the level write run at the day close, once per player per online game day. Task 12 benches the day close before and after. Every task that changes a per-minute adapter (Tasks 4, 12, 14, 15) adds a Java-call-count stub test against the build before.
- **The golden trace** (`testing/tests/kernel/golden/trace-1.0.0.json`) is re-recorded only in a commit that names its cause, with every moved leaf attributed in the task report (ruling T2-1). The named causes are listed per task.
- **Constants.** Every shipped constant sits on a settled `science.tsv` row or is labelled `game choice` with the rows that bound it (spec § 10's Basis column). `python tools/science_check.py --scan mod` → 0 at every `mod/` commit.
- **Models.** Opus for the live tasks, the oracle, the kernels the fit governs (Tasks 2, 5–10), the server adapters (12–15, 17), the register task, and every review of evidence or of a whole task. Sonnet for spelled-out edits (Tasks 3, 11, 16, 18) and scoped re-reviews. Every dispatch names its model and asks for the exact model id back.
- **Frozen files.** A driver is never edited after its run. A test of a frozen lib that reads a removed field is deleted by name under a ledgered ruling, and the pytest baseline is reset by name at the close.

## The constants block (point T; the one place a refit amends)
This table is the plan's only copy of the point-T values (refit 2, which superseded point S; spec § 5.2). Task 2 asserts that `testing/tests/kernel/strength_model.py`'s `POINT_T` equals `compact_T.json`'s `"chosen"`, and Task 5 asserts that `K.strength.DEFAULTS` equals `POINT_T` key by key. Every task below names keys, never numbers. A refit (ruling 13-1) amends the compact JSON the tests name, this table and the one Lua block, and nothing else.

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
| `ffmi5` | 18.0 kg/m² | level 5's FFMI | fixed |
| `ffmiPerLevel` | 0.5 kg/m² | one level | fixed |
| `capLevel` | 16.5 | the untrained natural cap | `NR.StrengthCapLevel` |
| `capShare` | 0.5 | a muscle trait's share of its offset applied to the cap | `NR.StrengthTraitCapShare` |
| `ts` | 1.0 | the biology clock | `NR.StrengthTimeScale` |
| `xpPerSet` | 346 (provisional until Task 1) | XP of one hard set | `NR.StrengthXPPerSet` |
| `incidental` | 0.35 | non-exercise grant weight | `NR.StrengthIncidentalWeight` |
| `fMinShare` | 0.35 | F's floor as a share of F0 (the model's `0.35 * F0`) | fixed |
| `fmMin` | 0.5 kg | the fat floor (`K.partition.FM_MIN`) | fixed |

`K.HEIGHT_M = 1.70` (spec § 2) lives in `NR_Kernel.lua`, outside the table, because `K.acute`, `K.body`, `K.traits` and `K.strength` all read it (ruling 13-4).

## Rulings this plan carries
- **13-1 (one constants block).** Ruling: every constant of the growth law, the energy gate and the lean partition is written once, in `K.strength.DEFAULTS`, under the oracle's key names, with a test binding it to `strength_model.POINT_T` and that to `compact_T.json` (point T); task text names keys, never point-T numbers — a harvest on small surpluses in trained lifters is running and a refit may follow, so a refit must amend one block, one JSON and this plan's table — cost if wrong: none; a table indirection costs one Lua index per read at the day close.
- **13-2 (the oracle's flags).** Ruling: the tracked oracle keeps the fit's daily step verbatim, so it reproduces `compact_T.json`, and gains a flag `exact` (default False) that switches on the four places where the spec states a form the fit did not run. With `exact=True`: detraining is integrated exactly over the day; the labile lean decays on every day with no surplus left after growth (the fit decayed it only at `E == 0` exactly, which a live day never meets); growth's energy cost is charged at `grow / ts`; and the biology clock `ts` scales growth, regain, detraining, the peak decay and divides the grace days. The kernel reproduces the oracle with `exact=True`. Task 2 re-scores the registry under it and pins every value — the spec states exact detraining (§ 6) and a time scale (§ 10), which the fit ran at `ts = 1` with an Euler step — cost if wrong: the detraining half-life oracle moves by a few hundredths of a week; Task 2 asserts every weighted oracle that passed under the record still passes.
- **13-3 (growth's energy cost under a time scale).** Ruling: at `ts > 1` the lean a day gains is `grow` (scaled) while the energy it costs is `grow / ts · RHO_LEAN` — the time scale compresses muscle biology, not the food clock, and charging the scaled gain would bill a compressed server's trainee up to 30 days of tissue energy a game day — cost if wrong: lean is cheaper than real at `ts > 1`; at the default `ts = 1` nothing differs.
- **13-4 (height).** Ruling: `K.HEIGHT_M = 1.70` in `NR_Kernel.lua`, and `K.acute.HEIGHT_M` is removed, with `K.acute.refeed`'s BMI reading `K.HEIGHT_M` — `NR_Kernel_Acute.lua` sorts before `NR_Kernel_Body.lua`, so a file-scope read of a body constant would be nil; the core file loads first — cost if wrong: none.
- **13-5 (the record calendar).** Ruling: `body.dayIndex` becomes the record's own count of closed online days, born at `math.floor(bornAge / 24)`, and a new field `body.wday` holds the world day the open record day belongs to. A minute closes the day when `math.floor(ageH / 24) > body.wday` and then sets `body.wday` to that world day, closing at most one day per minute. A minute whose step from `body.lastAgeH` exceeds 60 game minutes is a reconnect after a gap: it re-stamps `body.wday` to today's world day and closes nothing, so the day open at departure continues as today's record day. `MET.MAX_CLOSES` and `stats.skippedDays` are removed — the spec's "resumes the calendar where it stopped", and the existing rule that a step over 60 minutes is offline time (`dtM` clamp, `trailShift`) — cost if wrong: a server stall over 60 game minutes with the player online reads as a gap and folds those days into one record day.
- **13-6 (first sight without `OnNewGame`).** Ruling: a body built at first sight, with no creation handler before it (a character older than the mod, a pruned record, a reset made with no clock), is `K.body.create` over the band traits the character holds (muscle: WEAK, FEEBLE, STOUT, STRONG; weight: the five weight-band traits, Emaciated read as Very Underweight), not over its native Strength level or weight — one creation path, and vanilla's band swap already keeps the held muscle trait within one band of the native level — cost if wrong: a character adopted mid-save restarts at its band's level and may lose up to two native levels.
- **13-7 (`traitCarry`).** Ruling: `body.traitCarry` is removed; the carry delta's trait factor is `K.strength.TRAIT_CARRY[band]`, the constructor's own values for the muscle trait the level implies (WEAK 0.75, FEEBLE 0.9, STOUT 1.25, STRONG 1.5, none 1.0; #2144), recomputed at every level write — the constructor ran before `applyTraits` on a new character (trait-levers § 3.3), so a first-sight read of `getMaxWeightDelta` returns 1.0 for every new character, and a reconnect's constructor would then disagree with the mod's write — cost if wrong: carry capacity changes at an in-play band swap, where vanilla changes it only at the next load.
- **13-8 (the level-write route).** Ruling: the level write moves the native level one step at a time with `player:LevelPerk(perk)` and `player:LoseLevel(perk)`, vanilla's creation route, so vanilla's `LevelPerk` listener runs the band swap at each step (spec § 7), then pins the XP. If Task 0 measures that the server-side `LevelPerk` or `LoseLevel` write does not hold or does not reach the client, the write falls back to `setPerkLevelDebug` plus the mod's own band write (`STR.remap`, today's measured route, #2867, #2870), and Task 0's report names the branch taken — the spec requires vanilla's swap on the mod's write, and #2870 measured that the debug setter runs none — cost if wrong: a stepped write fires one listener call per level, at most 10 at creation and 1 at a day close.
- **13-9 (the XP pin).** Ruling: the bar's XP is written as `getXp():setXPToLevel(perk, n)` followed, when the fraction is above 0, by one `addXp(player, perk, x)` with `x = frac · (totals[n+1] − totals[n])` divided by the multiplier chain the capture divides out, under `STR.pinning = true` so the capture ignores it. Task 0 Step 1 first reads the jar for an absolute experience setter reachable from Lua, and a found one replaces the pair. The `addXp` route re-seeds the anti-cheat's snapshot after it lands (#2132, #2862), which `setXPToLevel` alone does not, so a pin that raises XP never trips the check for a user connection — the spec pins "the level's starting total plus the fraction", and the only Lua-reachable setter known writes level totals — cost if wrong: the landed fraction can be off by the rounding of the protein factor; the panel's true level is unaffected.
- **13-10 (the level-10 guard).** Ruling: while the body's level is 10 or more and the native level is 10, the server wraps `xpUpdate.checkForLosingLevel` with a guard that returns for Strength without calling the original, chained after BeyondTen's own wrapper when that is loaded (#2856) — the spec's "guarded … as BeyondTen does" — cost if wrong: a second mod that replaces the function after ours drops our guard; the guard is re-installed at `OnServerStarted` and checked by a Task 19 read.
- **13-11 (the multiplier chain divided out).** Ruling: the capture divides the landed amount by the protein factor read off the server's protein store (×1.5 when 50 < store < 300, ×0.7 below −300; #2112), by the sandbox multiplier (`MultiplierConfig.Global` when `GlobalToggle` is true, else `MultiplierConfig.Strength`), and also by the per-perk book multiplier `getXp():getMultiplier(perk)` when it is above 1 (#2113), the third because it is the same chain and any book that multiplies Strength would scale biology — spec § 4 names the first two; a book is the third link — cost if wrong: one Java call per Strength grant; no vanilla Strength book exists to our knowledge.
- **13-12 (the signal ring).** Ruling: today's signal accumulates in `body.sigDay` and `body.sig7` holds the seven closed days (slot 1 the oldest), the `pDay`/`p7` pattern; at the close the ring shifts, `sigDay` lands in slot 7 and S is the ring's sum divided by `xpPerSet` — the spec's "today's slot of a 7-slot daily ring" — cost if wrong: none.
- **13-13 (an immobilised day).** Ruling: an immobilised day (a leg fracture or splint) runs the existing disuse arm in place of growth, regain and detraining; the grace counter still counts it — the disuse curve already carries immobilised loss (S0069), and running detraining beside it would count the loss twice — cost if wrong: none measured.
- **13-14 (thinness and Weak).** Ruling: a thin pick sets `F = min(F_muscle, BMI_target · H² − fat_target)`, so Weak with Underweight keeps Weak's F and reads BMI 17.0 — "lowered to reach" never raises F — cost if wrong: Weak with Underweight starts below Underweight's BMI target; the axis keeps Underweight because Very Underweight needs BMI below 16.5 to switch on.
- **13-15 (the BMI the axes read).** Ruling: the thinness axis reads BMI from `F + fm` (spec § 8), not from the weight slot, which also carries `lx` — the spec's text — cost if wrong: at most 0.05 · F of labile lean, about 1 BMI unit at the cap, never counted toward thinness.
- **13-16 (pick validation).** Ruling: validation runs on the server's own definitions. The point total is legal when the creation screen's remaining points, by the formula Task 0 Step 2 reads off the install's `CharacterCreationProfession.lua`, are 0 or more. Picks are stripped from the end of `getKnownTraits()` (the order the client's list sent, the server's only order), skipping free (profession-granted) traits, until the total is legal and no two remaining picks exclude each other (`isMutuallyExclusive` either way). A stripped trait's XP boosts are reverted with `setPerkLevelDebug(perk, max(0, level − boost))` plus `setXPToLevel`, since `applyTraits` already applied them — the spec's "stripped, latest first, and logged"; the server keeps no pick order (trait-levers § 4) — cost if wrong: a cheating client loses its last-listed trait, not its last-picked one.
- **13-17 (the female fat cuts).** Ruling: with `NR.SexSpecific` on, a female character reads Kelly 2009's female FMI cuts from the settled row S2057 (excess fat above 9, obese class I above 13 kg/m²), and the male cuts come from S2056 — both rows were minted at b6b73a49 — cost if wrong: none; the option defaults off.
- **13-18 (the Training adapter).** Ruling: `NR_Server_Training.lua` is deleted and `test_training_shape.py` with it; `K.training` keeps the aerobic side (`metMinutes`, `band`, `sample`, `climbCredit`, `closeDay`, `weekMinutes`), and the resistance side (`event`, `loadMinute`, `actionMinute`, `decay`, `doses`, `W_STR`, the `S_*` and `K_*` constants, `MAINTAIN_HIGH`, `TAU_V_DAYS`) goes. The capture lives in `NR_Server_Strength.lua`, the module that owns Strength — the file's whole content was the resistance side (spec § 9.2) — cost if wrong: none.
- **13-19 (the panel's Strength row).** Ruling: the mirror carries `body_level`, the true level to two decimals' precision as a number, and `body_sets`, the closed week's S; the view shows "Strength 12.3" on the Bands level and up, under the body block. The old `body_shownL`, `body_dStr` and `body_dHyp` keys go — spec § 2's panel line — cost if wrong: none.
- **13-20 (`lx` in mass).** Ruling: `lx` counts in the weight slot (`fm + lm + lx`), the `mass7` ring, the trailing weight readers and `K.energy.ree`'s mass input only where that input is total mass; REE's lean term keeps reading `body.lm` (`NR_Kernel_Energy.lua:263`) — spec § 5.1: weight, not level or REE — cost if wrong: none.

## File structure
| File | Change |
|---|---|
| `testing/tests/kernel/strength_model.py` (new) | the fit's `model.py`, verbatim, plus `POINT_T`, the `exact` flag and `ts` (Task 2) |
| `testing/tests/kernel/strength_oracles.py` (new) | the fit's `oracles.py`, verbatim, imports renamed (Task 2) |
| `testing/tests/kernel/test_strength_oracle.py` (new) | the record reproduced, the `exact` re-score pinned (Task 2) |
| `testing/tests/kernel/test_strength_parity.py` (new) | the kernel against the oracle, day by day (Tasks 5–9) |
| `mod/.../shared/NR_Kernel.lua` | `K.HEIGHT_M` (Task 4) |
| `mod/.../shared/NR_Kernel_Strength.lua` | rewritten: `DEFAULTS`, the scale, the law, the capture arithmetic, `params`; the neural term, the memory floor, the cumulative deficit, the disuse term, `fSlow`, `ceiling`, `xpLevel`, `policy` removed (Tasks 5–8, 12) |
| `mod/.../shared/NR_Kernel_Partition.lua` | the lean arms replaced; `leanGain`, `headroom`, `gEnergy`, `gProt`, `protection`, `surplus`, `deficit`, `day`, `G0`, `LM_CAP_RATIO`, `P_LO`, `P_HI`, `SURPLUS_RAMP`, `DEFICIT_HALF*`, `PROT_*` removed (Tasks 7, 12) |
| `mod/.../shared/NR_Kernel_Training.lua` | the resistance side removed (Task 12) |
| `mod/.../shared/NR_Kernel_Body.lua` | `create`, `new` rewritten, `effSex`; `split`, `interp`, `ANCHORS_W`, `BF_*`, `BUILD_*`, `KNOTS`, `W_MIN`, `W_MAX`, `band` removed (Tasks 3, 9, 12, 15) |
| `mod/.../shared/NR_Kernel_Traits.lua` (new) | the three axes with damping (Task 10) |
| `mod/.../shared/NR_Kernel_Heal.lua`, `NR_Kernel_Store.lua` | the no-trait body fallback; the new fields healed and saved (Tasks 4, 12) |
| `mod/.../shared/NR_Kernel_Acute.lua` | `HEIGHT_M` removed, the BMI reads `K.HEIGHT_M` (Task 4) |
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
| `testing/PZTestKit/...` | `trait.def`, `creation.picks`, `perk.park` (Task 0) |
| `testing/experiments/TKX_TraitLevers/` (new) | the trait-lever probe mod (Task 0) |
| `testing/experiments/x42_levers_lib.py`, `x421_levers.py`, `x422_calib.py`, `x43_strength_lib.py`, `x431_beyondten.py`, `x432_offline.py`, `x433_creation.py`, `x434_growth.py` and their profiles (new) | the live runs |
| `tools/bench_day_close.py` (new) | the Rule 6 bench (Task 12) |

---

### Task 0: Live engine checks before any build (Opus; harness lane, then live; controller opens the workspace)
Spec § 12.2's Task 0 checks. A finding that falsifies a spec assumption stops the plan for a ruling before the dependent task (the stop table in Step 6).

**Files:**
- Modify `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `.../client/PZTestKit_Client.lua` and `.../server/PZTestKit_Server.lua` (new sites appended at the end of each file, § 5).
- Regenerate `docs/reference/harness-commands.md` (`python tools/bus_inventory.py`); update `#2808`'s claim text and quote and `#1235`'s quote for the new count (§ 5).
- Create `testing/experiments/TKX_TraitLevers/42.21/mod.info` and its `media/scripts/TKX_TraitLevers.txt`, `media/lua/shared/TKX_TraitLevers_Shared.lua`, `media/lua/server/TKX_TraitLevers_Server.lua`, `media/lua/shared/Translate/EN/UI.json`.
- Create `testing/experiments/x42_levers_lib.py`, `testing/experiments/x421_levers.py`, `testing/profiles/x42-levers.toml`, `testing/tests/test_x42_levers_lib.py`.

**Interfaces (the harness change, its own commit before the run):**
- `trait.def` (shared) `<TraitName>` → `{ok, side, trait, cost, free, xpBoosts = {<Perk> = n}, exclusive = {names}, granted = {names}, label, description}`: reads `CharacterTraitDefinition.getCharacterTraitDefinition(CharacterTrait[<TraitName>])` and walks its getters; the Java maps and lists are walked with `size()`/`get(i)` and `keySet():iterator()` (#0940), never `#`.
- `creation.picks` (client) `<TraitName> [<TraitName> ...]` → `{ok, armed, picks}`: arms a one-shot rewrite of the pick list that runs after vanilla's copy in the coop creation accept path (`CoopCharacterCreation.lua:65–68`; the implementer reads `:60–:80` first) and before `sendCreatePlayer` reads it: `getWorld():getLuaTraits():clear()` then one `getWorld():addLuaTrait(name)` per argument. It sends what it is given, legal or not.
- `perk.park` (server) `<user> <Perk> <xpLevel>` → `{ok, perk, levelBefore, levelAfter, xpBefore, xpAfter}`: `getXp():setXPToLevel(perk, xpLevel)` only, the level untouched.

**`TKX_TraitLevers` (installed only through `x42-levers.toml`, never into a fixture):**
- `TKX_TraitLevers.txt` restates `base:obese` in full in `module Base` with `Cost = -10`, `IsProfessionTrait = false`, no `XPBoosts`, and vanilla's exclusions plus `base:overweight` (the vanilla block's other keys copied from `scripts/generated/characters/character_traits.txt:743`).
- `TKX_TraitLevers_Shared.lua` at file scope: `getXpBoosts():remove(Perks.Fitness)` on Underweight's definition; `getMutuallyExclusiveTraits():remove(CharacterTrait.ATHLETIC)` on Overweight's; `getMutuallyExclusiveTraits():add(CharacterTrait.OBESE)` on Overweight's; each records its pcall result into a global `TKX_TraitLevers.edits`.
- `TKX_TraitLevers_Server.lua`: an `OnNewGame(player, square)` handler under `isServer()` that records the known-trait list, the weight, the Strength and Fitness levels and XP; then writes `getNutrition():setWeight(77.7)`, removes STRONG if present, adds OUT_OF_SHAPE, steps Strength once with `LevelPerk` (or `LoseLevel` at 10), and records the after state. A global `TKX_TraitLevers.newGame` table holds both reads.
- `UI.json` overrides `UI_trait_obesedesc` with a marker string (the key name taken from the vanilla block's `UIDescription`).

- [ ] **Step 1: The jar and install reads (Opus, read-only; `pz.sh` per CLAUDE.md § 2).** Write each answer into `task-0-reads.md` with its `Class.method @off L<n>` or `lua:<path>:<line>` cite:
  - an absolute experience setter on `IsoGameCharacter$XP` reachable from Lua (ruling 13-9);
  - whether `GameServer.addXp` calls `updateXpChecker` after `AddXP` returns early (an amount of 0, and XP at the level-10 total);
  - `IsoGameCharacter.LevelPerk` and `LoseLevel` on a server: what they push, and whether the band listener runs (`XpUpdate.lua:196–238`);
  - `xpUpdate.checkForLosingLevel`'s signature and BeyondTen's wrapper (`3765241705/.../Server.lua:445–460`), and BeyondTen's `BT.API_VERSION`, `BT.SetStoredXP` and `GetTotalMasteryCost` signatures and units (`3765241705/mods/BeyondTen/42/media/lua/shared/BeyondTen/Shared.lua`);
  - `Nutrition.updateWeight`'s call of `applyTraitFromWeight`, and whether the `Nutrition = false` early return skips it (#2644);
  - `SandboxVars.MultiplierConfig`'s field names on 42.21 (`Global`, `GlobalToggle`, `Strength`) from `media/lua/shared/Sandbox/Apocalypse.lua:242–246`.
- [ ] **Step 2: The creation-screen reads.** From `client/OptionScreens/CharacterCreationProfession.lua`, read the remaining-points formula (the profession cost, the sandbox free points, each trait's cost sign) and write it as a formula into `task-0-reads.md` (ruling 13-16). From `CoopCharacterCreation.lua`, read the respawn path that copies the picks.
- [ ] **Step 3: The harness change.** Write the three commands with their `@reply` lines and comment blocks. Run `python tools/luabalance.py` on the HEAD copies then the working tree, `python tools/kahlua_lint.py testing/PZTestKit testing/experiments`, `python tools/bus_inventory.py`, and the full `claims_check` → 0 (after the `#2808`/`#1235` update). Commit by pathspec: `"Plan 13 Task 0: harness trait.def, creation.picks and perk.park"`.
- [ ] **Step 4: The lib and driver.** `x42_levers_lib.py` imports `xlib.py` and starts from `x37_fitness_lib.py`'s newest patterns. Its offline tests (`test_x42_levers_lib.py`) run every grade against fake buses whose replies are the three commands' `@reply` shapes and recorded shapes of the others (§ 5), each grade with a case that fails it. Commit the lib, driver, profile and tests before the boot.
  - The profile `x42-levers.toml`: fixture `two` (an admin and a user-role client), `[[mods]]` PZTestKit, TKX_TraitLevers, TKX_XpEvents; `[sandbox] Nutrition = false`, `DayLength = 1`; no NutritionRevamp.
- [ ] **Step 5: The run (one session; § 5's memory check, `pzt doctor`, the foreground polling wait).** The driver `x421_levers.py` grades:
  1. **Restated block replaces vanilla's on both sides:** `trait.def Obese` on server and client reads cost −10, free false, no Fitness boost, Overweight among the exclusions.
  2. **The Lua list edits bind:** `trait.def Underweight` reads no Fitness boost; `trait.def Overweight` lists Obese and not Athletic, on both sides; `TKX_TraitLevers.edits` holds no error.
  3. **The client sees the server's definitions** after the join: the client's `trait.def` answers equal the server's for the three traits, and the client reads the marker description.
  4. **`OnNewGame` writes reach the client:** the user client dies (`health.reduce <user> 110`) and respawns through x192's route (`ISPostDeathUI` → `CoopCharacterCreation.instance accept` via `lua.callm`); the server's `TKX_TraitLevers.newGame` after-state is read beside the client's `stats.get` and `perk.xp` in the same wall second (§ 5's same-second pairs): weight 77.7, OUT_OF_SHAPE present and STRONG absent, the stepped Strength level.
  5. **An illegal pick list reaches `OnNewGame`:** before the second respawn, `creation.picks Strong Stout Obese Overweight` (over-budget and mutually exclusive); the server's recorded known-trait list holds all four.
  6. **Vanilla's band swap fires on the mod's level write:** in the handler's write (route of ruling 13-8), the band trait after the step is the stepped level's band on both sides; a `perk.level` (debug) write in the same session shows no swap, as #2870 did.
  7. **`AddXP` sees every Strength source:** with `TKX_XpEvents` recording, the user client runs `exercise.do pushups 1`, a melee hit on a spawned target with a knockback weapon, a tree hit, loaded movement above half the max weight for 60 real seconds and one plank barricade removal; each source's events are counted, with amount and whether an `ISFitnessAction` was running.
  8. **The level-10 park keeps `AddXP` firing:** `perk.set <user> Strength 10`, `perk.park <user> Strength 9`, `xp.grant <user> Strength 100`: the event's amount is the full grant (after the protein factor of the store read beside it), the level stays 10.
  9. **The pin under the anti-cheat:** on the user-role connection with `AntiCheatXP = 2`, `perk.set` to level 7 then the ruling 13-9 pair (`setXPToLevel` via `perk.park` then `xp.grant` of 30000) draws no kick across two minutes (two check intervals, #2860).
  Stage the artifacts byte-identical and write the report with the artifacts rows, the do-not-cite leaves and the candidate claims, as Plan 11h Task 4 did.
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
- Create `testing/experiments/x422_calib.py` (on `x42_levers_lib.py`), `testing/profiles/x42-calib.toml` (fixture `default`; PZTestKit and TKX_XpEvents; `Nutrition = false`; `DayLength = 1`).

- [ ] **Step 1: Offline tests** of the grade on fake buses, each with a failing case (zero events, a protein store outside the neutral window).
- [ ] **Step 2: The run.** `nutrition.set <user> proteins 0` on the server (the factor-1 window between −300 and 50; read back), endurance full (`stats.setany <user> ENDURANCE 1`), then `exercise.do pushups 5`; the driver stops the set through the queue-clear command (§ 5) when the server's endurance reads 0.25 or below or the action ends. Read every Strength `AddXP` event (amount, wall time) and the protein store before and after.
- [ ] **Step 3: The reading.** XP per set = the sum of the set's Strength amounts, each divided by the protein factor read at the store (the store stays in the neutral window, so the factor is 1; any event outside it is reported, never dropped). Report reps, XP, wall seconds and XP per real second beside vanilla-strength-rate § 4's 346 and 1.8–1.95.
- [ ] **Step 4: The amendment.** The controller ledgers the reading. Task 5 writes it as `DEFAULTS.xpPerSet` with the run's id in its label, and Task 11 as the option's default. The provisional 346 never ships unless the run comes back unmeasured, in which case 346 ships labelled `provisional, vanilla-strength-rate § 4` and a ruling is ledgered.

### Task 2: Track the oracle (Opus; tests lane)
**Files:**
- Create `testing/tests/kernel/strength_model.py`, `testing/tests/kernel/strength_oracles.py`, `testing/tests/kernel/test_strength_oracle.py`.

**Interfaces:**
- **Consumes:** `C:\Users\Angus\AppData\Local\Temp\claude\C--Users-Angus-repos-project-zomboid\e5eaf55d-0ef3-42a5-b6e6-4827b799b827\scratchpad\strev3\model.py` and `oracles.py` (point T's fit); `docs/superpowers/research/2026-10-14-strength-redesign/refit/compact_T.json`.
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

  def test_point_s_is_the_record():
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
      P = dict(sm.POINT_T, exact=True, ts=1.0, grace_d=0)
      b = sm.Body(P, 10.0, 16.5, 13.0, F0L=5.0)
      F0 = b.F0
      gap0 = b.F - F0
      hl_days = 7 * P["detrain_hl_wk"] * (1 + P["detrain_status"] * b.s())
      # S = 0, energy balance, no protein: growth and regain are 0, the detraining runs alone
      b.Pk = b.F
      for _ in range(int(round(hl_days))):
          b.day(0.0, 0.0, 0.0)
      assert 0.45 < (b.F - F0) / gap0 < 0.6
  ```
  The last test's band is wide because the status term moves as F falls; Task 8's kernel test pins the exact one-day factor.
- [ ] **Step 2: Run them.** `python -m pytest testing/tests/kernel/test_strength_oracle.py -q`. Expect FAIL (no module).
- [ ] **Step 3: Copy and extend.**
  - Copy `model.py` to `strength_model.py` byte for byte, then append `POINT_T` (built from the JSON at import) and edit `Body.day` only inside `if P.get('exact'):` branches:
    - detraining: `detr = (F − F0) · (1 − exp(−lam · ts · (1 − S/Sm) / 7))`;
    - the grace test: `self.grace > P['grace_d'] / ts`;
    - growth and regain multiplied by `ts`; the peak decay `exp(−dec · ts)`;
    - the surplus arm's `rest = E − grow / ts · RHO_L`, the deficit arm's recomposition `dM −= grow / ts · RHO_L / RHO_F`;
    - the labile decay `dX −= X / x_tau_d` on every day whose surplus arm left `rest <= 0` and on every deficit day, after the deficit's own `fromX`.
  - Copy `oracles.py` to `strength_oracles.py` with `from model import` changed to `from .strength_model import` (and the same for any other module import). Change nothing else.
  - Add a module docstring to each naming the source path, the copy date and ruling 13-2.
- [ ] **Step 4: Run them.** Expect PASS. Record the `exact` re-score's every oracle value in the test file as a pinned table (`EXACT_PINS`), with a test asserting each to 1e-9, so a later kernel or oracle change that moves one is named.
- [ ] **Step 5: Commit.** `git commit -m "Plan 13 Task 2: the strength fit's model and oracles tracked, point T reproduced, exact mode pinned" -- testing/tests/kernel/strength_model.py testing/tests/kernel/strength_oracles.py testing/tests/kernel/test_strength_oracle.py`

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
- [ ] **Step 4: Gates and golden.** Full pytest in its own call. Mutation on a scratch copy (`git archive HEAD | tar -x -C <scratch>`): `effSex` returning `sex` always; the client ignoring the option. Each fails a test. Re-record the golden under **"Plan 13 Task 3: NR.SexSpecific off by default; g5 reads the male values"**, attributing every moved leaf to g5. § 3 mod gates, full `claims_check` (pin or re-anchor moved pointers).
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
- [ ] **Step 4: Gates, golden, commit.** Mutations: `gapped` ignored; `calendar` closing on `>=`. Golden re-recorded under **"Plan 13 Task 4: the BMI at the shared 1.70 m height (was 1.75)"** (no golden player has a gap over 60 minutes: g4 is away 30, so the calendar moves no leaf; say so). Commit: `"Plan 13 Task 4: one 1.70 m height; the record calendar advances on online days only"`.

### Task 5: The constants block, the scale and the level (Opus; `mod/` lane, kernel)
Spec §§ 2, 10.

**Files:**
- Modify `NR_Kernel_Strength.lua` (a new section at the top; the old functions stay until Task 12).
- Create `testing/tests/kernel/test_strength_parity.py`; modify `test_kernel_strength.py`.

**Interfaces:**
- `K.strength.DEFAULTS`: the constants block's keys, one per line, each with its label (the § 10 Basis column; `xpPerSet` labelled with Task 1's run id).
- `K.strength.fOf(L, P)` → `(P.ffmi5 + (L - 5) * P.ffmiPerLevel) * K.HEIGHT_M * K.HEIGHT_M`.
- `K.strength.levelOf(F, P)` → `5 + (F / (K.HEIGHT_M * K.HEIGHT_M) - P.ffmi5) / P.ffmiPerLevel`.
- `K.strength.shown(L)` → `n, frac` with `n = K.clamp(math.floor(L), 0, K.strength.L_MAX)` and `frac = L - math.floor(L)` when `0 <= L < 10`, else 0.
- `K.strength.status(body)` → `K.clamp((body.lm - body.F0) / (body.Fc - body.F0), 0, 1)`, 0 when `body.Fc <= body.F0`.

- [ ] **Step 1: The failing tests.**
  ```python
  import json, os
  from . import strength_model as sm

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

  def test_scale_matches_the_oracle(host):
      D = _d(host)
      for L in (0.0, 3.0, 5.0, 9.0, 14.0, 16.5, 18.5):
          assert abs(host.call("strength.fOf", L, D) - sm.F_of(L)) < 1e-12
          assert abs(host.call("strength.levelOf", sm.F_of(L), D) - L) < 1e-12

  def test_shown_level_and_bar(host):
      n, frac = host.call("strength.shown", 7.25)
      assert n == 7 and abs(frac - 0.25) < 1e-12
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
  `test_defaults_equal_the_oracle_point` is the binding of ruling 13-1.
- [ ] **Step 2: Run.** Expect FAIL.
- [ ] **Step 3: Implement** the block and the four functions. `shown` returns 0 for a negative level (the floor clamp) with frac 0.
- [ ] **Step 4: Gates** (no golden move: nothing calls the new functions yet; the golden test proves it). Mutation: `ffmiPerLevel` at 0.55; `shown` without the clamp. Commit: `"Plan 13 Task 5: the strength constants block (point T) and the FFMI scale"`.

### Task 6: Growth: the signal, the threshold, the set cap and the gates (Opus; `mod/` lane, kernel)
Spec § 5.

**Interfaces:**
- `K.strength.threshold(s, P)` → `P.Sg0 * math.exp(P.beta * s)`.
- `K.strength.setCap(s, P)` → `P.Smax + (P.Smax1 - P.Smax) * s`.
- `K.strength.signal(S, s, P)` → `K.max(0, math.sqrt(K.min(S, setCap)) - math.sqrt(threshold)) / (math.sqrt(P.Sref) - math.sqrt(P.Sg0))`.
- `K.strength.fp(p, P)` → `K.interp(P.fp_knots, p)`, the knots already scaled by `params` (Task 11).
- `K.strength.fe(E, s, p, tdee, P)` → the oracle's `fe`: `E0s = P.E0 * (1 - P.E0_drop * s) * (1 + P.a_nov * (1 - s)^2 * K.clamp((p - 1.6) / 0.8, 0, 1))`; `bal = P.fbal0 * (1 - P.fbal_drop * s) * (1 - P.trained_need * s)`; 0 at `E <= E0s`; `bal * (1 - E / E0s)` for `E < 0`; `bal + (1 - bal) * K.min(1, E / (P.surplus_full * (1 - P.full_drop * s) * tdee))` for `E >= 0`. (The `1.6` and `0.8` here are the oracle's literals for the protein deepening's ramp, not the f_p knots; they go into `DEFAULTS` as `nov_p0 = 1.6` and `nov_pspan = 0.8`, fixed.)
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
Spec § 5.1. The constants are `DEFAULTS`' (`forbes_c`, `wT`, `S_def`, `wP`, `pdef_lo`, `pdef_hi`, `prot_floor`, `x_max_frac`, `x_tau_d`); the partition names no number of its own besides `RHO_LEAN`, `RHO_FAT` and `FAT_CEIL_KCAL` (Hall, Alpert; unchanged).

**Interfaces:**
- `K.partition.forbes(fm, P)` → `P.forbes_c / (P.forbes_c + fm)`.
- `K.partition.training(S, P)` → `K.min(1, S / P.S_def)`.
- `K.partition.surplusLean(body, grow, S, p, E, P, ts)` → `dX, dM` (the oracle's `E >= 0` arm with ruling 13-2's `rest` and decay).
- `K.partition.deficitLean(body, grow, S, p, E, P, ts)` → `dF, dX, dM` (the oracle's `E < 0` arm, Alpert's overflow split by `prot`, `lx` paying first, recomposition at `grow / ts`, then the decay).
- `body.lx` is laid by `K.body.new` at 0 (Task 9) and saved (Task 12).

- [ ] **Step 1: The failing tests** in `test_strength_parity.py`: for the Longland, Mettler, Bray and the four § 9 cases' daily inputs (taken from `strength_oracles.py`'s helpers), the kernel's arm equals the oracle `exact=True` arm's `dX`, `dM` and lean change to 1e-12 for one day, from the same body state; plus mass balance:
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
- `K.strength.day(body, S, p, E, tdee, alcGkg, P, ts)` → `dF, dX, dM`: the oracle's `Body.day` order with `exact=True`: `s`, growth (× `ts`), detraining, the partition arm by the sign of `E`, the floors (`lm >= P.fMinShare * body.F0`, `lx >= 0`, `fm >= P.fmMin`), then `peakStep`. Writes `body.lm`, `body.lx`, `body.fm`, `body.Pk`, `body.grace`.

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

  def test_retraining_a_novice_is_no_slower_than_the_first_block(host):
      ...  # Räntilä: 10 wk on, 10 wk off, 10 wk on at 12 sets; block 2's gain >= 0.94 x block 1's (point T's 0.9385, unchanged from point S)
  ```
  `_lua_body_from(host, ob)` copies `F, F0, Fc, Pk, M, X, grace` into a Lua table under the kernel's names (`lm, F0, Fc, Pk, fm, lx, grace`). The two elided bodies are written in full by the implementer from the stated assertions; the Räntilä protocol is `strength_oracles._rantila`'s.
  Also the spec § 12.1 checks, each with its mutation:
  - the curve: an average character on 20 sets with full gates (`p = 2.0`, `E = 0.05 · 2600`) reaches level 15 at 5 years (± 0.02 level); Weak never reaches 15 in 10 years; Feeble below the average at every year; Stout and Strong reach 15 sooner;
  - the s = 0.9 gate over 8 weeks: balance ΔF < 0.5 %; +10 % gives ≤ 2 × the balance gain, < 1 %, ≥ 50 % of the weight gain as fat; −500 kcal/day at 3.5 kg of fat gives ΔF ≤ 0;
  - detraining's half-life is 6 weeks after a 14-day grace (`detrain_status` 0 for the novice reading, S2001's population).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).**
- [ ] **Step 4: Gates and commit.** Mutations: Euler detraining; grace `>=`; regain as a sum; the peak not decaying; `ts` not dividing the grace. Commit: `"Plan 13 Task 8: maintenance, detraining, regain, the peak and the kernel day"`.

### Task 9: The creation body table (Opus; `mod/` lane, kernel)
Spec § 3.2.

**Interfaces:**
- `K.body.MUSCLE = { WEAK = -5, FEEBLE = -2, STOUT = 2, STRONG = 4 }` (the vanilla Strength offsets, #2157's order of traits; trait-levers § 1.3).
- `K.body.FAT_FMI = { none = 4.5, OVERWEIGHT = 7.5, OBESE = 12.5 }` (S2056; the default the middle of the male normal 3–6).
- `K.body.THIN = { UNDERWEIGHT = { bmi = 18.0, fmi = 1.5 }, VERY_UNDERWEIGHT = { bmi = 16.5, fmi = 1.0 } }` (WHO grades; S1905 for the fat at BMI 18).
- `K.body.create(muscle, weight, P)` → `spec = { lm, F0, Fc, Pk, fm }`: `off = K.body.MUSCLE[muscle] or 0`; `F0 = fOf(5 + off)`, `Fc = fOf(P.capLevel + P.capShare * off)`; `fm = FAT_FMI[weight or "none"] * H²` for a fat or no weight pick; for a thin pick `fm = THIN.fmi * H²` and `lm = K.min(F0, THIN.bmi * H² - fm)` (ruling 13-14); else `lm = F0`; `Pk = F0`.
- `K.body.new(spec, sex, ageH)` replaces today's `new(w, sex, build, l0, traitCarry, r, ageH)`: lays `lm, F0, Fc, Pk, fm, lx = 0, grace = 0, sigDay = 0, sig7 = {0 x7}, fatT, thinT` (Task 10's held words, from the picks), `fmRef = fm`, `lm0dis = lm`, `sex`, `bornAge`, `wday`, the rings (`mass7` at `lm + lx + fm`), the window, and every field today's `new` lays that survives Task 12's removals. Task 12 switches the callers; until then `new` keeps its old name and this one is written as `K.body.newLean` so both coexist, renamed in Task 12.

- [ ] **Step 1: The failing test,** cell by cell against spec § 3.2's table and Appendix 7's proposed block:
  ```python
  @pytest.mark.parametrize("muscle, weight, L, fat_kg, w", [
      (None, None, 5.0, 13.005, 65.025),
      ("FEEBLE", None, 3.0, 13.005, 62.135),
      ("WEAK", None, 0.0, 13.005, 57.8),
      ("STOUT", None, 7.0, 13.005, 67.915),
      ("STRONG", None, 9.0, 13.005, 70.805),
      (None, "OVERWEIGHT", 5.0, 21.675, 73.695),
      (None, "OBESE", 5.0, 36.125, 88.145),
      (None, "UNDERWEIGHT", 2.0, 4.335, 52.02),
      (None, "VERY_UNDERWEIGHT", 0.0, 2.89, 47.685),
  ])
  def test_creation_table(host, muscle, weight, L, fat_kg, w):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", muscle, weight, D)
      assert abs(host.call("strength.levelOf", s["lm"], D) - L) < 1e-9
      assert abs(s["fm"] - fat_kg) < 1e-9
      assert abs(s["lm"] + s["fm"] - w) < 1e-9

  @pytest.mark.parametrize("muscle, cap", [(None, 16.5), ("FEEBLE", 15.5), ("WEAK", 14.0), ("STOUT", 17.5), ("STRONG", 18.5)])
  def test_cap_moves_by_half_the_offset(host, muscle, cap):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", muscle, None, D)
      assert abs(host.call("strength.levelOf", s["Fc"], D) - cap) < 1e-9

  def test_thin_is_depletion_below_the_set_point(host):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", "STRONG", "VERY_UNDERWEIGHT", D)
      assert s["Pk"] == s["F0"] and s["lm"] < s["F0"]
      assert abs(host.call("strength.levelOf", s["F0"], D) - 9.0) < 1e-9

  def test_weak_underweight_keeps_weak_lean(host):
      D = host.K.strength.DEFAULTS
      s = host.call("body.create", "WEAK", "UNDERWEIGHT", D)
      assert abs(s["lm"] - host.call("strength.fOf", 0.0, D)) < 1e-12
  ```
  The kg columns are spec § 3.2's at 1.70 m (2.89 m²), unrounded.
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).**
- [ ] **Step 4: Gates and commit.** Mutations: the cap at the full offset; thin raising F; fat at FMI 11 for Obese (Appendix 7's draft). Commit: `"Plan 13 Task 9: the creation body table"`.

### Task 10: The trait axes with damping (Opus; `mod/` lane, kernel; with a science check)
Spec § 8.

**Files:**
- Create `mod/.../shared/NR_Kernel_Traits.lua`; create `testing/tests/kernel/test_kernel_traits.py`.

**Interfaces:**
- `K.traits.FAT_CUTS = { { 6, 9 }, { 9, 13 } }` by sex index (FMI, kg/m²; S2056 male, S2057 female), `K.traits.FAT_WORDS = { "overweight", "obese" }`, `K.traits.FAT_MARGIN = 0.3`.
- `K.traits.THIN_CUTS = { 18.5, 17, 16 }`, `K.traits.THIN_WORDS = { "underweight", "veryUnderweight", "emaciated" }`, `K.traits.THIN_MARGIN = 0.5` (WHO; game-choice margins).
- `K.traits.held(rung, x, cuts, margin, up)` → the new rung: from `rung`, step deeper while the next cut is passed by more than `margin`, step back while the current cut is undone by more than `margin`; `up` true for the fat axis (higher is worse), false for thinness.
- `K.traits.axes(body, sex)` → writes `body.fatT` and `body.thinT` (rung numbers 0..2 and 0..3) from `fmi = body.fm / H²` and `bmi = (body.lm + body.fm) / H²` (ruling 13-15), clears `fatT` to 0 while `thinT > 0` (precedence), and returns the band word: the thin word, else the fat word, else `"normal"`.
- `K.traits.WANT(fatT, thinT)` → the five weight-band trait names each true or false (`OBESE`, `OVERWEIGHT`, `UNDERWEIGHT`, `VERY_UNDERWEIGHT`, `EMACIATED`).
- `K.body.create` (Task 9) sets the picked rung directly: OVERWEIGHT 1, OBESE 2, UNDERWEIGHT 1, VERY_UNDERWEIGHT 2.

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
                                   (None, "OVERWEIGHT", "overweight"), (None, "OBESE", "obese"), ("WEAK", "UNDERWEIGHT", "underweight")):
          s = host.call("body.create", muscle, weight, D)
          assert host.call("traits.axes", s, 1) == word
  ```
- [ ] **Step 3–4: Run (FAIL), implement, run (PASS).** Mutations: no margin; precedence removed; female cuts used when the option is off (the caller passes `K.body.effSex`).
- [ ] **Step 5: Commit** the kernel, its test and (controller) the science row: `"Plan 13 Task 10: the fat, muscle and thinness axes with damping"`.

### Task 11: The sandbox options and `K.strength.params` (Sonnet; `mod/` lane)
Spec § 10.

**Files:**
- Modify `42.21/media/sandbox-options.txt`, `Translate/EN/Sandbox.json`, `NR_Kernel_Strength.lua` (`params`), `NR_Server_Options.lua`; tests `test_kernel_strength.py`, `testing/tests/kernel/test_translations.py` (the key set), and the options test that reads the file.

**Interfaces:**
- `K.strength.params(sv)` → `P, fellBack`: a new table copied from `DEFAULTS`, each option in the table below read through the `readLeaf` clamp rule (out of range clamps for a double, reads the default for the integer), then `P.k = DEFAULTS.k * StrengthRate`, the knots' x values scaled by `StrengthProteinFull / 1.6`; then the guard: with `s15 = (15 - 5) / (P.capLevel - 5)` when `P.capLevel > 15`, if `threshold(s15, P) >= setCap(s15, P)` then `beta`, `Sg0`, `Smax1` revert to `DEFAULTS` and `fellBack = true`.
- `NR.server.options.strength` = `P`, rebuilt only when a strength leaf changed (one comparison loop at the poll; the table is not rebuilt per minute, Rule 6); a fallback logs once at level 1 with the three values read.

| Option | Type | Min | Max | Default | Key |
|---|---|---|---|---|---|
| `NR.StrengthTimeScale` | double | 0.25 | 30 | 1.0 | `ts` |
| `NR.StrengthXPPerSet` | double | 50 | 2000 | Task 1's reading | `xpPerSet` |
| `NR.StrengthIncidentalWeight` | double | 0 | 1 | 0.35 | `incidental` |
| `NR.StrengthCapLevel` | double | 12 | 20 | 16.5 | `capLevel` |
| `NR.StrengthTraitCapShare` | double | 0 | 1 | 0.5 | `capShare` |
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

- [ ] **Step 1: The failing tests:** every option parses (the existing option-file test pattern); each tooltip key exists in `Sandbox.json`; `params` with no options equals `DEFAULTS` key by key; `StrengthRate = 2` doubles `k`; `StrengthThreshold = 1.0` with `StrengthThresholdRise = 4` falls back with `fellBack == true`; `StrengthCapLevel = 14` skips the guard; out-of-range doubles clamp.
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Tooltips (in `Sandbox.json`): one plain sentence per option saying what it scales and its unit; `NR.StrengthMaintainShare`'s says "0 never detrains"; `NR.StrengthTimeScale`'s says "the biology clock: 1.0 is one biological day per game day; weekly sets are still counted over 7 game days".
- [ ] **Step 4: Gates and commit.** `"Plan 13 Task 11: the strength sandbox options and the load-time guard"`.

### Task 12: The switch: the day close, first sight, the removals (Opus; `mod/` lane)
Spec §§ 4 (Replaced), 5, 6, 9.1, 9.2, 9.4.

**Files:**
- Modify `NR_Server_Metabolism.lua` (`closeDay` at 301–320, `ensureBody` at 148–170, `heal` at 332–345, `MET.GUARD` at 74–76, the step at 452–458, `MET.BUILD_TRAITS`, `responder`), `NR_Kernel_Strength.lua`, `NR_Kernel_Partition.lua`, `NR_Kernel_Training.lua`, `NR_Kernel_Body.lua`, `NR_Kernel_Heal.lua`, `NR_Kernel_Store.lua` (`INPUTS`, `bodyBase`), `NR_Server_Strength.lua` (the minute: the ceiling and policy call removed, carry kept), `NR_Kernel_Mirror.lua` (the `dStr`/`dHyp` read removed; Task 18 adds the new keys).
- Delete `NR_Server_Training.lua` and `testing/tests/kernel/test_training_shape.py` (ruling 13-18).
- Create `tools/bench_day_close.py`.
- Tests: rewrite `test_kernel_strength.py`, `test_kernel_partition.py`, `test_kernel_training.py`, `test_kernel_body.py`, `test_kernel_heal.py`, `test_kernel_store.py`, `test_metabolism_shape.py`, `test_strength_shape.py`, `test_heal_once.py`; the golden.

**Interfaces:**
- **`closeDay(body, w, immobilised, ageH, ironGrade, debtH)` in Metabolism** becomes, in this order:
  1. the disuse count, as today;
  2. `local sum = K.strength.signalClose(body)` (shifts `sig7`, lands `sigDay` in slot 7, zeroes `sigDay`, returns the ring's sum); `local S = sum / P.xpPerSet`;
  3. `local p = body.pDay / w`; `local tdee = K.max(body.eeDay, K.energy.ree(body.lm))`;
  4. immobilised: `K.partition.disuse(body)` applied as today, `body.grace` advanced by `K.strength.detrain`'s counter rule only; else `K.strength.day(body, S, p, body.ebDay, tdee, body.alcDay / w, P, P.ts)`;
  5. `body.fmRef = K.max(body.fmRef, body.fm)`;
  6. `body.band = K.traits.axes(body, K.body.effSex(body.sex, opts.sexSpecific))` and `body.traitsDirty = true` when the band word changed;
  7. `body.S = S` (the closed week's sets, for the mirror and `T`);
  8. `K.training.closeDay`, TAC, `pPrevKg`, `inDayClosed`, `K.partition.closeDay`, AT, as today (TAC's `gEnergy` reads `body.lm`, unchanged).
  `P` is `NR.server.options.strength`, falling back to `K.strength.DEFAULTS` when the options table is absent.
- **`MET.ensureBody`**: when `record.body` is nil, reads the band traits held (ruling 13-6) into `muscle` and `weight`, builds `K.body.new(K.body.create(muscle, weight, P), sex, ageH)`, and stamps `body.levelDue = true` so Task 14's minute writes the level once.
- **`K.body.new`** (renamed from `newLean`) replaces the old constructor; `split` and its tables, `BUILD_*`, `band(w)`'s callers outside Weight (Weight's goes in Task 15) are removed.
- **`K.store.bodyBase(rb, ageH)`**: `K.body.new(K.body.create(nil, nil, K.strength.DEFAULTS), sex, lastAgeH)` with the stored `lm`, `fm`, `lx` overlaid by the INPUTS copy.
- **`K.heal.body(body, ageH)`**: a non-finite `lm`, `fm`, `F0`, `Fc` or `Pk` heals to the no-trait body's value (`K.body.create(nil, nil, K.strength.DEFAULTS)`); `lx`, `grace`, `sigDay` and each `sig7` slot to 0; `wday` as Task 4; `S` to 0. The `l0` argument and the Strength read in Metabolism's `heal` go.
- **`K.store.INPUTS`**: add `body.F0`, `body.Fc`, `body.Pk`, `body.lx`, `body.grace`, `body.sigDay`, `body.sig7.*`, `body.S`, `body.fatT`, `body.thinT`, `body.band`, `body.wroteL`, `body.wday`; remove `body.fm0`, `body.lm0`, `body.l0`, `body.r`, `body.traitCarry`, `body.strAgeH`, `body.vStr`, `body.vHyp`, `body.vStrHigh`, `body.n`, `body.nPeak`, `body.tPeakD`, `body.nHist.*`, `body.cumDef`, `body.shownL`, `body.riseHeldH`, `body.lastFallAge`.
- **The weight readers**: `fm + lm` becomes `fm + lm + lx` in `NR_Server_Weight` (the slot), `K.partition.closeDay`'s `mass7`, `K.body.new`'s rings and every `w = body.fm + body.lm` in Metabolism, Strength, Nutrients and Effects that means body mass (ruling 13-20; grep `fm + body.lm` and `fm + lm` and list each site in the report).
- **Removed** (spec § 9.2): `K.strength.neuralStep`, `closeDay`, `floorF`, `fSlow`, `ceiling`, `xpLevel`, `policy` and their constants (`N_TARGET_K` through `RISE_HOLD_H`, `FALL_MIN_H`, `MEM_*`, `CUMDEF_*`, `E_ENERGY_MAX`, `DISUSE_K`, `DISUSE_T`, `F_MIN`, `F_MAX`, `LEVELS_PER_DOUBLING`); the partition's and training's lists in the file table; Metabolism's `responder`, `MET.BUILD_TRAITS`, the step's `neuralStep`, `doses`, `decay`, `loadMinute`, `actionMinute` calls, and `MET.GUARD`'s removed names (`n`, `nPeak`, `tPeakD`, `cumDef`, `vStr`, `vHyp`).

- [ ] **Step 1: Bench before.** `python tools/bench_day_close.py --players 60 --closes 200` on HEAD: it loads `server_host.Host`, builds 60 records with bodies, and times Metabolism's `closeDay` (reached through `NR.server.metabolism`'s test seam, which the tool adds as `MET._closeDay = closeDay` under a `NR_BENCH` global guard), printing µs per player-close. Ledger the figure.
- [ ] **Step 2: Write the failing tests.** The Metabolism shape tests: one close runs `signalClose`, `day` and `axes` once each and writes `body.S`; an immobilised close runs disuse and no growth (ruling 13-13); a first sight with STRONG and OBESE held builds Strong's F0 and Obese's fat; `ensureBody` no longer reads `getMaxWeightDelta` or `getPerkLevel`; the store round-trips every new INPUTS path and drops the removed ones; the heal rebuilds a NaN `F0` to the no-trait body's. A Java-call-count stub test: the Metabolism minute makes fewer Java calls than at HEAD (the build-trait reads at first sight only; no per-minute call added).
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
- `STR.onXp(player, perk, amount)`: Strength only; returns at once under `STR.pinning`; resolves the record without creating one (Training's `bodyOf`, moved here); reads the protein store (`getNutrition():getProteins()`), the sandbox multiplier (`SandboxVars.MultiplierConfig`, by Task 0 Step 1's field names), the book multiplier (`getXp():getMultiplier(perk)`), and `fitness = NR.server.fitness.typeOf(username) ~= nil` (no Java); adds `capture(...)` into `body.sigDay`; then, when the native level differs from `body.wroteL`, calls `STR.repin(player, body)` (Task 14). One pcall; counts `stats.captures`, `stats.ignored`, `stats.failures`.
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
  Shape tests: an `AddXP` for Fitness adds nothing; a Strength event during a recorded set adds the full share, outside it the incidental share; the pinning flag blocks capture; a player with no record creates none.
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: protein factor not divided; the incidental weight applied to Fitness sets; capture during pinning.
- [ ] **Step 4: Golden and commit.** The golden fires no `AddXP`, so it does not move; the golden test proves it and the report says so. Commit: `"Plan 13 Task 13: the AddXP capture with the multiplier chain divided out"`.

### Task 14: The level write, the park and BeyondTen (Opus; `mod/` lane)
Spec § 7. The route is ruling 13-8's branch as Task 0 measured it; the pin is ruling 13-9's.

**Files:**
- Modify `NR_Server_Strength.lua`, `NR_Kernel_Strength.lua`; tests `test_strength_shape.py`, `test_kernel_strength.py`; the golden.

**Interfaces:**
- `K.strength.TRAIT_CARRY = { WEAK = 0.75, FEEBLE = 0.9, STOUT = 1.25, STRONG = 1.5 }` (#2144) and `K.strength.traitCarry(n)` → `TRAIT_CARRY[bandOf(n)] or 1` (ruling 13-7).
- `K.strength.pinXp(n, frac, totals)` → the target XP: `totals[n] + frac * (totals[n + 1] - totals[n])` for `n <= 9`; `totals[9]` for `n == 10`.
- `STR.writeLevel(player, body, ctx)`: `L = levelOf(body.lm, P)`; `n, frac = shown(L)`; steps the native level to `n` by the measured route; then:
  - `n <= 9`: pins XP to `pinXp(n, frac, totals)` (ruling 13-9);
  - `n == 10` and BeyondTen absent: parks with `setXPToLevel(perk, 9)`;
  - `n == 10` and `BT ~= nil and BT.API_VERSION == 1`: never writes native XP; when `L >= 11`, writes `BT.SetStoredXP(player, Perks.Strength, v)` with `v` from BeyondTen's `GetTotalMasteryCost` for `math.floor(L)` plus the fraction toward the next, by the signatures Task 0 Step 1 read;
  - stamps `body.wroteL = n`, re-applies the band only on the fallback route (`STR.remap`), pushes traits when the set changed (`NR.pushTraits`), and sets `body.levelDue = false`.
- `STR.repin(player, body)`: the `AddXP` listener's call when a grant crossed a level (native ≠ `body.wroteL`): `writeLevel` without reading the clock.
- The minute (`STR.minute`): when `body.levelDue` or the native level differs from `body.wroteL` (one `getPerkLevel` read, as today), `writeLevel`; then the carry with `traitCarry(body.wroteL)`. Metabolism's close sets `body.levelDue = true`.
- The guard (ruling 13-10): `STR.installLevelGuard()` at `OnServerStarted` wraps `xpUpdate.checkForLosingLevel(playerObj, perk)` once (a global sentinel, the Fitness wrapper's shape): for Strength with native level 10 and the record's `wroteL == 10`, return; else call the saved original.

- [ ] **Step 1: The failing tests.** `pinXp` at (7, 0.25) reads 127500 + 0.25 · 90000; at 10 reads 337500. Shape tests:
  - a level drop from 7 to 5 steps twice through the route stub and pins XP at level 5's total plus the fraction;
  - the minute rewrites after an admin `setPerkLevelDebug` (the #2740 re-assertion);
  - at 10 without BeyondTen: XP parked at 337500, a granted 100 raises the stub's XP and the listener re-parks it;
  - with a BeyondTen stub (`BT.API_VERSION = 1`): no native XP write at 10, `SetStoredXP` called with the cost of level 12 for L = 12.0;
  - the guard returns for a parked Strength and calls the original for Fitness;
  - the carry uses `TRAIT_CARRY` for the written band;
  - a Java-call-count stub: the minute's calls without a due write equal today's (one level read, the carry reads).
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: no park at 10; the pin at the level total without the fraction; BeyondTen's native write not skipped; the guard calling the original for Strength.
- [ ] **Step 4: Golden, gates, commit.** Re-record under **"Plan 13 Task 14: the Strength level written from lean mass at the day close, with the XP pin"** (the golden's players start at perk 5 with xp 260; the first-sight write moves `perk`, `xp` and the write counters). Commit: `"Plan 13 Task 14: the level write, the level-9 park, BeyondTen and the level-10 guard"`.

### Task 15: The trait writes; the weight band refresh retired (Opus; `mod/` lane)
Spec § 8.

**Files:**
- Modify `NR_Server_Weight.lua` (`needsRepair`, `WGT.BAND_TRAIT`, lines 137–150), `NR_Kernel_Body.lua` (`band(w)` removed); tests `test_weight_shape.py`, `test_kernel_body.py`; the golden.

**Interfaces:**
- `WGT.writeTraits(player, body, ctx)`: when `body.traitsDirty` or the held set differs from `K.traits.WANT(body.fatT, body.thinT)` (the existing repair read, now against the axes), add and remove through `getCharacterTraits():add/remove` with the registry objects, `NR.pushTraits(player, WGT.stats)` once, `B.markBand(username)` when `body.band` changed, and clear `traitsDirty`. `applyTraitFromWeight` is never called.
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
| Weak | −10 (vanilla) | false | removed | vanilla's (feeble, stout, strong) | — |
| Feeble | −6 (vanilla) | false | removed | vanilla's | — |
| Stout | 6 (vanilla) | false | removed | vanilla's | — |
| Strong | 10 (vanilla) | false | removed | vanilla's | — |
| Overweight | −6 | false | removed | vanilla's plus obese | — |
| Obese | −10 | false | removed | vanilla's (already lists overweight, underweight, very underweight) | — |
| Underweight | −6 | false | removed | vanilla's plus every missing one of obese, overweight, very underweight | — |
| Very Underweight | −10 | false | removed | vanilla's plus every missing one of obese, overweight, underweight | — |
| Weight Gain | −2 (vanilla) | false | — | vanilla's | removed |
| Weight Loss | −2 (vanilla) | false | — | vanilla's | removed |

Every block keeps vanilla's `CharacterTrait`, `UIName`, `UIDescription` and `Texture` lines. The file is CRLF-free, and `mod_lint.py`'s script-basename rule passes (the basename is mod-unique).

`UI.json` overrides each block's `UIDescription` key (the key names read off the blocks), in plain words:
- Weak, Feeble, Stout, Strong: "Starts with less (or more) muscle: Strength N at the start, and a natural ceiling M." with N and M from Task 9's table (0/14, 3/15.5, 7/17.5, 9/18.5).
- Overweight, Obese: "Starts carrying more body fat (about X kg). Fat is lost or gained by eating." with X from Task 9's table.
- Underweight, Very Underweight: "Starts underfed: low body fat and some muscle lost, which comes back quickly with food and training."
- Weight Gain, Weight Loss: vanilla's sentence without the granted-trait clause (read the vanilla string first).
And the panel's `UI_NR_Row_body_level` = "Strength" (used by Task 18).

- [ ] **Step 1: The failing test** (`test_trait_script.py`): parses the file; asserts the 10 ids, each block's `Cost` and `IsProfessionTrait` per the table, no `XPBoosts` in the 8 body blocks, no `GrantedTraits` in Weight Gain and Weight Loss, every in-family exclusion present in both directions, and every vanilla key besides those four present (compared against a frozen copy of the 10 vanilla blocks the test carries as a string, read once from the install by the implementer).
- [ ] **Step 2–3: Run (FAIL), write, run (PASS).** `mod_lint`, `release_pack check`, `kahlua_lint`, `hotpath_lint`, `science_check --scan mod` (the costs are Angus's; the file carries a header comment naming the ruling, § 11).
- [ ] **Step 4: Commit:** `"Plan 13 Task 16: the 10 body trait blocks restated, with their descriptions"`.

### Task 17: The `OnNewGame` creation handler with validation (Opus; `mod/` lane)
Spec § 3.2. Runs only if Task 0's check 4 held; validation only if check 5 held.

**Files:**
- Create `mod/.../server/NR_Server_Creation.lua`; modify `NR_Server_Players.lua` (the `OnNewGame` handler at 221–237 fires `P.onNewGame` after `store.reset`); tests: new `testing/tests/kernel/test_creation_shape.py`; the golden.

**Interfaces:**
- `P.onNewGame` (a list, `P.onFirstSight`'s pattern): fired with `(username, player, record)` after a successful `store.reset`; a pending reset fires it from `P.makeReset`.
- `CRE.validate(player)` → the list of stripped trait names: ruling 13-16's formula over `getCharacterTraits():getKnownTraits()` (walked with `size()`/`get(i)`), the server's definitions (`CharacterTraitDefinition.getCharacterTraitDefinition`), profession cost read off `player:getDescriptor()`; strips and reverts boosts, logs each strip at level 1.
- `CRE.picks(player)` → `muscle, weight`: the held muscle and weight-band traits after validation.
- `CRE.onNewGame(username, player, record)`: validate; `record.body = K.body.new(K.body.create(muscle, weight, P), sex, ageH)`; `getNutrition():setWeight(lm + lx + fm)`; `STR.writeLevel(player, record.body)`; `WGT.writeTraits(player, record.body)` (the band traits final, spec § 3.2 step 3, so a Weight Gain → Out of Shape swap is undone only for the five weight-band and four muscle traits; Fitness band traits are vanilla's and stay, § 14); counts `stats.created`, `stats.stripped`.
- Guarded by `NR.isServer()`; every Java read through `NR.call`.

- [ ] **Step 1: The failing tests** (server stand-ins, `test_strength_shape.py`'s pattern): Strong + Overweight builds Strong's F and Overweight's fat and writes weight 57.80 + 21.675; the level write lands 9 with STRONG; an over-budget list loses its last non-free entries until legal, each logged; Overweight + Obese (exclusive) loses the later; a stripped trait with a Strength XP boost has its level reverted; a respawn's `OnNewGame` builds a fresh body.
- [ ] **Step 2–3: Run (FAIL), implement, run (PASS).** Mutations: validation skipped; the weight write left to vanilla's `applyWeightFromTraits`; the trait write before the level write (the swap then wins).
- [ ] **Step 4: Golden and commit.** Re-record under **"Plan 13 Task 17: the creation handler builds g3's respawn body from its picks"** (g3's respawn at minute 101). Commit: `"Plan 13 Task 17: the OnNewGame creation handler with pick validation"`.

### Task 18: The panel's Strength row (Sonnet; `mod/` lane)
Ruling 13-19.

**Files:**
- Modify `NR_Kernel_Mirror.lua` (`K.mirror.body`), `NR_Kernel_View.lua` (`K.view.rows` after the body-fat row), `UI.json`; tests `test_kernel_mirror.py`, `test_kernel_view.py`, `test_client_panel_shape.py`.

**Interfaces:**
- `m.body_level = K.strength.levelOf(body.lm, K.strength.DEFAULTS)` (the scale's constants are fixed, so the defaults are exact), `m.body_sets = body.S`; `body_shownL`, `body_dStr`, `body_dHyp` removed (grep the client for readers first).
- `K.view.push(rows, "body_level", "UI_NR_Row_body_level", K.view.fmt(mm.body_level, 1), 2, false)`.

- [ ] **Step 1–3:** the failing tests (a level 12.34 mirror shows "12.3"; a body-less mirror shows No data), implement, pass. Golden: the mirror's sends are counted, not kept, so the golden does not move unless a counter does; say which.
- [ ] **Step 4: Commit:** `"Plan 13 Task 18: the panel shows the true Strength level"`.

### Task 19: Live: the BeyondTen run (Opus; live; one session)
Spec § 12.2.

**Files:** `testing/experiments/x43_strength_lib.py` (on `xlib.py`, from `x42_levers_lib.py`), `x431_beyondten.py`, `testing/profiles/x43-beyondten.toml` (the staged release copy, § 5; PZTestKit, NutritionRevamp, BeyondTen from workshop `3765241705` by path; `Nutrition = false`; `DayLength = 1`), `testing/tests/test_x43_strength_lib.py`.

- [ ] **Step 1: Offline tests**, each grade with a failing case, against the staged copy and a real run layout (§ 5).
- [ ] **Step 2: The run.** `record.set` the admin's `body.lm` to `fOf(12.3)` and `body.levelDue` true; after the next minute read: native Strength 10, native XP 337500 or BeyondTen's own park, BeyondTen's stored XP for 12.3 (its own read), the panel mirror's `body_level`. Then a 1000-XP `xp.grant`: the capture's `sigDay` rises by the grant's share; the native level stays 10. Then `record.set` `body.lm` to `fOf(9.5)` with `levelDue`: native 9, XP at level 9's total plus half its cost, STRONG held on both sides. Read `xpUpdate.checkForLosingLevel` is the mod's guard over BeyondTen's (`lua.read`).
- [ ] **Step 3:** Stage the artifacts; the report with the artifacts rows, do-not-cite leaves and candidate claims.

### Task 20: Live: the offline-gap run (Opus; live; one session)
**Files:** `x432_offline.py`, `testing/profiles/x43-offline.toml` (staged copy; `Nutrition = false`; `DayLength = 1`).

- [ ] **Step 1: Offline tests.**
- [ ] **Step 2: The run.** Read the record whole (`lua.read record:<user>`), detach the client, raise the time multiplier (restored from the value read before, § 5) until 3 game days pass on the server, return the multiplier, re-attach the client (never under a near-stopped clock, #3788), read the record whole again at the first minute after first sight and again after the next world-day boundary. Grade: `dayIndex`, `sig7`, `p7`, `eb7`, `mass7`, `bandWeek`, `grace`, `Pk`, `lm`, `fm`, `lx` unchanged across the gap; the vanilla Strength XP unchanged (vanilla rust skips offline players); exactly one close after the next boundary.
- [ ] **Step 3:** Stage and report.

### Task 21: Live: the creation run (Opus; live; one session)
**Files:** `x433_creation.py`, `testing/profiles/x43-creation.toml` (fixture `two`; staged copy).

- [ ] **Step 1: Offline tests.**
- [ ] **Step 2: The run.** Four respawns of the user client through x192's route, each with `creation.picks`: (a) none; (b) Strong + Overweight; (c) Weak + Very Underweight; (d) Feeble + Obese + Overweight (illegal: exclusive) with extra over-budget traits. Each: the record's `lm`, `fm`, `F0`, `Fc`, the server and client weight, Strength level, trait list (same-second pairs), and the server log's strip lines. Grade against Task 9's table and ruling 13-16.
- [ ] **Step 3:** Stage and report.

### Task 22: Live: the growth smoke (Opus; live; one session)
**Files:** `x434_growth.py`, `testing/profiles/x43-growth.toml` (staged copy; `[sandbox.NR] StrengthTimeScale = 30`, `StrengthIncidentalWeight = 1`; `Nutrition = false`; `DayLength = 1`).

- [ ] **Step 1: Offline tests,** including the replay: the driver's grade replays the run's own recorded day-close inputs (S, p, E, tdee) through the kernel (`K.strength.day` via lupa) and compares the live `lm` per close (ruling 8-R: live against its own replay, never against a study).
- [ ] **Step 2: The run.** For 3 game days: grant `xpPerSet · 20 / 7` Strength XP a game day in 10 server `xp.grant` calls (the anti-cheat bound kept per check), place `body.pDay` and `body.ebDay` before each close with `record.set` (p = 2.0 g/kg, E = +260 kcal), and read the record at each close. Grade: each close's ΔF equals the replay to 1e-6 kg; the native level follows `floor(levelOf(lm))`; the band trait follows the level.
- [ ] **Step 3:** Stage and report.

### Task 23: The registers and the pages (Opus; docs lane; the Plan 11g Task 9 process)
- [ ] **Step 1: The artifacts rows** for x421, x422, x431–x434, each with its do-not-cite keys, re-anchoring the `artifacts.md` pointers each row shifts in the same commit (§ 6).
- [ ] **Step 2: The delta** (`.superpowers/sdd/<plan>/task-23-delta.tsv`), with ids reserved from the ledger's next id:
  - Task 0's readings as M rows (one per check) and the Step 1 jar reads as C rows; Task 1's XP per set; the live rows of Tasks 19–22;
  - the mod's mechanism rows as `C/inference` with `repo:` pointers (the growth law, the partition, the creation table, the axes, the capture, the level write, the calendar) where a sentence owns them (ruling T12-1);
  - **the stale rows:** `#0529` and `#3344` corrected (their "60-minute default" to the jar's 90-minute default, `SandboxOptions.<init> @110–@120 L70`, `getDayLengthMinutes @0–@66 L555–L561`, read on 42.21) by a correction pass under § 6's fill rule; `#2115` and `#2116` superseded by successors read on 42.21 (`lua:lua/server/XpSystem/XpUpdate.lua:32-37`, `jar:IsoPlayer.isRandXp @0–@81 L9626–L9633`: one roll a real second, 1 in 20), every page tagging them moved in the same commit (§ 4 item 4);
  - the rules the new design overturns: `#2902` (the `setPerkLevelDebug` clamp rule on `areas/body-effects.md#rules`) superseded by the level-write rule this plan measured; `#2701` qualified for the level-10 park under ruling 13-10; `#2705` (a mod effect's own trait) rewritten to state that a mod owning the band traits writes them from its own axes; the testing-your-mod clamp readings `#2894`, `#2896`, `#2897`, `#2898` and `#2881` (the band-anchored split) given bounds naming the removed code with pinned pointers;
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
- [ ] **Step 1:** The whole-pass review (structure, performance and the fit's parity included), one consolidated fix wave, its re-review.
- [ ] **Step 2:** `mod/NutritionRevamp/README.md` (the Strength and traits sections) and `CHANGELOG.md` folded into the 1.0.0 entry (the mod is unreleased).
- [ ] **Step 3:** Every § 3 gate; reset the pytest baseline by name (the deleted tests listed in Task 12's report) in CLAUDE.md § 3; update CLAUDE.md § 2 if a fixture or build changed; the memory file and `MEMORY.md` (§ 8).
- [ ] **Step 4:** Push; report to Angus: the Task 0 verdicts and branches taken, the XP-per-set reading, the bench before and after, the live readings, every ruling, and the mechanism candidates noticed.

---

## Self-Review

**Coverage (spec section → task):**

| Spec | Task |
|---|---|
| § 1 Goal | 5–18 |
| § 2 the scale, H shared with K.acute, the panel's true level | 4, 5, 18 |
| § 3.1 the 8 offered traits, costs, restated blocks, exclusions, Weight Gain/Loss, descriptions | 16 (Task 0 checks 1–3) |
| § 3.2 validation, the body table, cap rule, thin depletion, fat bands by sex, weight, the final trait write | 9, 10, 17 (Task 0 checks 4–5) |
| § 4 capture, multipliers, source weights, conversion, the calibration, XP never moves the level, Training's resistance side replaced | 1, 12, 13, 14 (Task 0 check 7) |
| § 5 growth, the gates, low-volume stall, `lx` | 6, 8 |
| § 5.1 the partition | 7 |
| § 5.2 the fit (point T) | 2, the constants block, 5 |
| § 6 maintenance, grace, detraining (exact), starvation, P, regain | 8 |
| § 7 the level write, the park, the band swap, BeyondTen | 14, 19 (Task 0 checks 6, 8, 9) |
| § 8 the axes, fat bands, precedence, damping, writes, the band refresh retired | 10, 15 |
| § 9.1 the new fields | 9, 12 |
| § 9.2 the removals | 12 (and 13-18's ruling on Training) |
| § 9.3 offline time and the ring audit | 4, 20 |
| § 9.4 Rule 6 | 12 (bench), 4, 12, 14, 15 (call-count stubs) |
| § 10 options, the guard, kept-out options | 11 |
| § 11 rulings | the constants, Tasks 9, 16 |
| § 12.1 kernel tests with mutations | 5–10 |
| § 12.2 live: Task 0, calibration, BeyondTen, offline gap; plus creation and growth | 0, 1, 19–22 |
| § 12.3 registers | 23 |
| § 13 the sex option | 3, 10 (ruling 13-17) |
| § 14 out of scope | Task 17 leaves Fitness bands to vanilla; the carry formula untouched (ruling 13-7 keeps vanilla's constructor table) |

**Placeholders.** The XP-per-set default is Task 1's reading by design, with the provisional value and its fallback rule stated. The female FMI cuts are the settled row S2057. BeyondTen's call signatures and the creation-screen formula are Task 0 reads that land in its report before the tasks that use them. Two kernel test bodies in Task 8 are given as stated assertions with their protocol named; every other test is in full.

**Name and type consistency.** `K.strength.DEFAULTS`, `params`, `fOf`, `levelOf`, `shown`, `status`, `threshold`, `setCap`, `signal`, `fp`, `fe`, `growth`, `maintainSets`, `detrain`, `peakStep`, `day`, `signalClose`, `proteinFactor`, `capture`, `pinXp`, `traitCarry`, `TRAIT_CARRY`; `K.partition.forbes`, `training`, `surplusLean`, `deficitLean`; `K.body.create`, `new`, `calendar`, `effSex`, `MUSCLE`, `FAT_FMI`, `THIN`; `K.traits.axes`, `held`, `WANT`; the body fields `lm`, `fm`, `lx`, `F0`, `Fc`, `Pk`, `grace`, `sigDay`, `sig7`, `S`, `fatT`, `thinT`, `band`, `wroteL`, `levelDue`, `traitsDirty`, `wday` are used identically in Tasks 4–22. `K.body.newLean` exists only between Tasks 9 and 12. The body keeps the name `lm` for F, as spec § 9.1 states.
