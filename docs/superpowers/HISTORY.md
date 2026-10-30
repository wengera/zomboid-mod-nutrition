# The program record

The design phase and Plans 0 to 19 are archived at the tag `program-record-v19`: every plan, spec and research report that stood under `docs/superpowers/` before Plan 20 removed the closed ones. Read a file at the tag with `git show program-record-v19:<path>`, for example `git show program-record-v19:docs/superpowers/plans/2026-10-13-plan-12-polish-review-refactor.md`, and list them with `git ls-tree -r --name-only program-record-v19 docs/superpowers/`. The pre-restructure library is at the older tag `research-program-v1`, and the design-phase reports were first tagged `design-phase-v1`.

What is still useful from the record is on [research-notes](../reference/research-notes.md); the rules it produced are in CLAUDE.md and the lessons files. Each plan's ledger is `.superpowers/sdd/<plan-basename>/progress.md`, which is local and gitignored. A range below runs from the plan's first commit (its spec or plan file) to its close, with the count from `git rev-list --count <first>^..<close>`; the ranges of plans that ran side by side overlap. Register ranges are claims rows `#NNNN` and science rows `SNNNN`.

## The design phase (2026-09-27)
- Built the spec `specs/2026-09-27-nutrition-mod-design.md` from 22 Opus research reports, with no code: wave 1 (five jar reads, three science, three platform, MoodleFramework, the food-data pipeline), wave 2 (five science and the training-signals jar read) and three compatibility reads. `research/_BRIEFS.md` holds the briefs and `_CONTROLLER-NOTES.md` the controller's jar reads N1-N6.
- Rulings: architecture C, the full `Hook.CalculateStats` takeover (Angus; N5 proved it player-only and server-only); registering the hook is the takeover (ruling 5); the mod owns the vanilla stat slots (ruling 2); Strength clamped from a lean-mass ceiling (ruling 6); sleep debt held mod-side; the trait list syncs with `sendSyncPlayerFields(p, 2)` (N2); the hook does not stop `IsoPlayer.updateEndurance` (N6).
- Live: none. Range 43b62c97..92542ca7 (5). Harvested by Plans 0a and 0b; tag `design-phase-v1`.

## Plan 0: the page procedure (2026-09-27)
- Built the binding procedure: Part A for page tasks (page shape, tags, delta files, the reviewer's bar), Part B for science harvests (part files, citation resolving, grades).
- Ruling: where the procedure and a spec disagree the spec wins; where it and the tools disagree the tools win.
- Committed with 0a and 0b at 041bc204; no rows of its own. Its rules now live in `page_lint`, `claims_check` and CLAUDE.md § 4.

## Plan 0a: the claims pass (2026-09-28 to 10-01)
- Built the design phase's jar, platform and compatibility research as register rows in 27 tasks (Wave C, 15 page tasks; Wave D, 7 area tasks): the perks and strength, endurance and fatigue, perception and speed, health surfaces, server lifecycle, sandbox options and client UI pages, the MoodleFramework teardown, the body-effects area page and skill, experiments X34-X49b, and the delta applier's `supersede` op.
- Rulings: work on `main`; provisional-tag gates until Task 27; SkillRecoveryJournal's protein gate is dead code (X43); links sharpened to anchors at each wave close.
- Live: none. Range 041bc204..f53c51b (80); register #2078-#2745; pytest 398.

## Plan 0b: the science register (2026-10-01 to 10-04)
- Built `sciencelib`, `science_check` and `science_delta` with their tests, the register and its page, and 14 parallel harvests (Wave S) from the eight science reports.
- Rulings: subagents sized to the task (Angus, overriding all-Opus); an open row closes through `status` or `settle`; an apply refuses a duplicate triple; the record's grade beats the report's when they conflict.
- Live: none. Range f53c51b..ab98819 (8); science S0001-S1054; pytest 429.

## Plan 1: foundations (2026-10-04)
- Built the mod skeleton and lints (`kahlua_lint`, `hotpath_lint`), the lupa kernel host with a 100 % line gate, the store, the bus and the client mirror, the sandbox options, and the `Hook.CalculateStats` takeover reproducing the seven updaters (desk read `research/jar-calculatestats-updaters.md`).
- Rulings: the version dir is 42.20.4; kernels one statement per line; one rim pcall per tick; a failed tick writes nothing and three strikes remove the handler; an artifact commit re-anchors its pointers; harness edits append at file end.
- Live: x131 and x131b-t (X32 settled: a no-op registrant froze thirst; X46 settled). Range c333ed63..4c3a06a9 (33); register #2746-#2816; pytest 489.

## Plan 2: intake (2026-10-05)
- Built three wrappers (the eat `complete`, `serverStop`, the drink `updateEat`), the four-source nutrient vector, the stomach with emptying and absorption, and the QualityCooking eat-wrap read.
- Rulings: T8-1 two eat fractions; T8-2 re-wrap only when the class table was re-created; no re-wrap at a boot event (#2835); mg units for micronutrients; #2808 is the living harness count; plan files are kept as the record.
- Live: x132b-e, x132r (X13 and X24 settled; X33 open). Range e0d482fe..4d5cc517 (36); register #2817-#2848; pytest 676.

## Plan 3: energy and body (2026-10-05)
- Built the Body, Energy, Partition, Training, Strength and Aerobic kernels with their adapters: the two-compartment body, the Strength clamp and carry delta, aerobic capacity and the legacy macro mirror (the Strength model was replaced in Plan 13).
- Rulings: T5-2 activity from the server's metabolic rate; T13-2 a rep counts on the Strength XP event; T3-1 `setPerkLevelDebug` plus re-applying the band; T18-1 acceptance profiles set `Nutrition = false`.
- Live: x141a, x141b, x141b2, x141c, x141s. Range 26d85c32..2e3bdc5c (53); register #2849-#2917; science S1055-S1056; pytest 1216.

## Plan 4: kinetics (2026-10-05)
- Built the declarative record engine (`NR_Kernel_Nutrients`, `NR_Data_Records`, 27 nutrients), the fluids kernel (water, sodium and potassium as the thirst view), the acute kernel (caffeine, alcohol, glycogen, sleep debt, impairment, refeeding) and the four dials.
- Rulings: T1-1 the thirst view counts the stomach's water; T4-1 the `mod/` lane is serial; T17-1 interactions read the meal; T17-2 caffeine and ethanol take a fast lane; T11-3 a fixed basal sodium draw (it later drained every diet, fixed in Plan 11f); B3-1 an aborted boot is not a run.
- Live: x151w, x151s, x151t, x151r, x151r2. Range 00ff1146..3ef08fd8 (64); register #2918-#3012; science S1057-S1118; pytest 1552.

## Plan 5: effects (2026-10-06)
- Built `NR_Data_Effects` and `NR_Kernel_Effects` (the composer, Severity, the night-vision machine, aim, the fatigue offset), `NR_Server_Effects` across five channels, and harness probes.
- Rulings: T6-1 Severity scales every penalty; T6-2 exercise credits are behaviour credits; T8-1 the refeed flag is day-long; the endurance fold ships off (X35); the status-op gap that led to the fill-step rule.
- Live: x161s, x161p (the gates), x161f, x161b (the acceptances). Range f7dffe96..2e4930a9 (58); register #3013-#3132; science S1119-S1180; pytest 1855.

## Plan 6: the item pass (2026-10-06)
- Built the pipeline (`food_nutrients.py`, `fdc_fetch.py`), curated mapping waves 4a-4h with iodine, phytate and insect tables, and the generated `NR_Data_Nutrients.lua`, `NR_ItemPass_Food.txt` and `NR_Data_Infer.lua`.
- Rulings: T3-1 `spice_only`; T4-5 a kcal-implied portion over an FDC serving; T6-1 an alcoholic fluid's energy follows the game's ethanol; ruling 17 class retention factors (the per-record codes unused); B3-2 a crash before any reading may take one fix.
- Live: x171p (X15, a block without `ItemType` merges), x171c (X16, the checksum), x172, x172b. Range 53e1600d..8ffb03e2 (53); register #3133-#3187; science S1181-S1221; pytest 2100.

## Plan 7: the interface (2026-10-06)
- Built the `K.view` row model, the panel, the tooltip band, the character-info tab, the moodles (MoodleFramework and the mod's own column), the ModOptions keybind and EN translations.
- Rulings: T5-1 the default key is semicolon (K is Display FPS); T8-1 the moodles sit on the bad side; T8-3 they serve player 0 only; T13-1 VisibilityMode defaults to Bands.
- Live: x181, x182 (X29, X5), x183, x183m, x183b. Range a1d1c26a..3ca6a81a (37); register #3188-#3258; pytest 2416.

## Plan 8: sync and persistence (2026-10-06)
- Built `K.store` (the version and the inputs-only contract), `K.reconcile` (missed intake, as macros only), the band-change push and the two-client fixture `two`.
- Rulings: T3-1 the input fields are those the kernel steps read; T3-2 `RECONCILE_EPS` 0.5 kcal; T6-1 `OnInitGlobalModData`'s flag reads true on a reload; T9-1 the scoped re-review rule; T9-2 derived fields dropped on read.
- Live: x191, x192, x193 (a reconnect, a respawn, a restart). Range b51b3ea0..0a8975b7 (26); register #3259-#3310; pytest 2506.

## Plan 9: packaging and release (2026-10-06)
- Built `tools/release_pack.py` (check, stage, manifest), the boot self-report, the README, CHANGELOG and COMPATIBILITY, the layout lint before every boot, and 1.0.0 staged.
- Rulings: T1-1 Translate JSON exempt from the vanilla-path rule; T5-1 a settle runs its contradiction sweep; the five neighbour reads deferred (the mods were absent).
- Live: x201 (the staged bytes equal the deployed ones), x202 (X23, a release client survives an unguarded raise). Range 5b261dea..1571f59c (25); register #3311-#3325; pytest 2544.

## Plan 10: spikes and the refactor (2026-10-07)
- Built six spikes (S1/S1b the zeroed rates, S2/S3 cost and the clock, S4 hunger feel, S5 food instances, S6 the Lua checksum), the golden trace (R0) and a behaviour-preserving refactor (R1-R4). An independent whole-mod review found four release blockers (the stagger starving players past one per tick, the takeover's cost, Overlay a stub, a gate that benched only `K.fast.step`); its fixes became the Plan 11 draft.
- Rulings: R0-1 three oracle recordings from the frozen tree; R1-1, R2-1, R3-1 changes the trace cannot see, accepted.
- Live: x221, x222, x222d, x223a, x223b, x224. Range 5566e3b0..175f248e (43; the plan file 42784ffc); register #3326-#3386; pytest 2634.

## Plan 10b: performance spikes (2026-10-07)
- Measurements only: P1 the slow minute by step, P2 a coarse minute, P3 the cost of no per-tick work, P3b the PANIC sawtooth.
- Rulings: Rule 6, no per-tick work (later restated as no noticeable hitching); the 60-player design load (Angus); M-1 Opus writes and the controller mints.
- Live: x231, x232. Range f25310a0..614c7087 (11, plus P3b to 9d489f20); register #3387-#3402.

## Plan 10c: hitching experiments (2026-10-07)
- Measurements only: H0 the frame instrument, H1 offline prototypes (heal-once among them), H2/H2b sub-step costs, H3 the scheduler shoot-out at N = 20, 40 and 60, H4 noticeability, H5 fake clients (not reachable), H6 the global store's privacy leak, and Task D, `docs/platform/performance.md`.
- Rulings: H2-1 a host-killed partial run stands; H4-1, H4-2 the thresholds stay; H5-1, D-1 a row is never minted before its sentence.
- Live: x241, x242 (host-killed), x242b, x243a/c/d, x244a-c, x245. Range 78524978..ee65568f (42); register #3403-#3499; pytest 2637.

## Plan 11: the draft and the decision memo (2026-10-07 to 10-08)
- Built nothing. The draft (`plans/2026-10-07-plan-11-review-fixes-DRAFT.md`, 42784ffc) was the review's 14-task fix plan for 1.0.1, held back before execution.
- The memo (`specs/2026-10-07-plan-11-decisions.md`, 13da2c0b..a4fa182d) recorded Angus's eight decisions: the once-a-minute hybrid; hunger as option (c); the store in server-local files; ids kept in shipped comments; subscribe to the neighbour mods; the budgeted `OnTick` queue; the neighbour reads' additions; Build 42.21.
- No register range of its own: the memo's rows are Plans 10, 10b and 10c's.

## Plan 11a: the offline build (2026-10-08)
- Built Task R, the 42.21 re-baseline (`jar_recheck`); the hybrid writer in place of `Hook.CalculateStats`; the budgeted queue (`NR_Kernel_Sched`); the file store (`NR_Kernel_Json`, alternating slot files); the interim satiety scalar; heal-once; the tooltip guards; the neighbour reads; the recipe-conservation report.
- Rulings: 1-17 (ruling 14: the tiered cadence and the dt biases deferred; ruling 17: re-baseline a game update first); W-1 a worktree may fast-forward; T9-2 the pinned pointer form; T16-3, T17-1 recipe conservation is a report, never a fix (a same-name `craftRecipe` appends); T20-1 dirty-marked saves (no save or stop event).
- Live: x250, the re-baseline smoke. Range 3cdd0af2..21fe816d (86; the 11b plan file landed in the same first commit); register #3500-#3595; pytest 2979.

## Plan 11b: the live release (written 2026-10-08, run 2026-10-13 after Plan 11h)
- Built the release acceptance: the scheduler shoot-out (the shipped queue kept, the spread cap not adopted; Angus), the Kahlua `%g` hang found and linted (x391g froze its server for 2787 s), the body-fat band harvest (`research/2026-10-13-bodyfat-bands`), the 1.0.0 release text (Tasks 3a-3c), the acceptance sessions, the docs task, and the close lessons in CLAUDE.md.
- Rulings: 11b-0 a run sheet before Task 1; 11b-1 the no-compatibility rule lapses at the Workshop upload; 11b-3 `record.set` as a setter; 11b-4 a detached long session; T2-10 the men's 6 % Very-lean edge is a game choice; T2-13 Angus's choices stay off the pages (the reconcile save storm among them).
- Live: x391a-h, x401-x406. Range b932cbb2..82e73f86 (49); register #3740-#3817; science S1904-S1912; pytest 4077.

## Plan 11c: satiety from physiology (2026-10-08)
- Built a two-lane stomach (zero-order solid energy, a liquid lane), fullness F by mass against 730 g, the post-absorptive pool P, structure D chosen by fit, the circadian factor, the activity terms (acute suppression, the exercise lag, the deficit bypass), the Overfull moodle and the meal-study oracle (spec `specs/2026-10-08-satiety-physiology-design.md`).
- Rulings: 11c-19 F against 730 g; 11c-24/24a the circadian factor a game choice; 11c-25 the mod's own moodle, never DISCOMFORT; 11c-27/30 the structure chosen by fit; 11c-31 W_PROTEIN; 11c-32 the bypass ramp.
- Live: none. Range 46d90da4..e25857ee (36); register #3596-#3626; science S1222-S1336; pytest 3264.

## Plan 11d: the satiety revisit (2026-10-09)
- Before it, Satiety research 2 (`research/2026-10-09-satiety-research-2`): seven quality-weighted harvests and the dieting-consensus review Angus asked for (261f8041, e99b39ff; S1337-S1663), then the revisit memo (`specs/2026-10-09-satiety-revisit-memo.md`, 104c8dd8: 15 candidates, 12 decisions).
- Built the memo's decisions: the acute term decays faster than it rises (11d-1), a sleep-debt hunger factor (11d-2), the 36 h fast and six-against-three replays (11d-3), the exercise lag's gain 0.7 (11d-4), the protein fullness term (11d-5).
- Rulings: T4-1 the glycogen term retired; 9b the backward-compatibility code removed; C9-10 a corrupt file heals to a fresh record; 9c a true trailing-24 h window; 9d the deficit drive refit (`BALANCE_SPAN_KCAL` 7500); contested effects ship neutral.
- Live: none. Range 9203b897..684e2887 (52); register #3627-#3650; science S1664; pytest 3340.

## Plan 11e: the deferred items (2026-10-09)
- Built: the golden trace records the written stats (11e-3); nicotine-withdrawal hunger (11e-2); monotony mood at the eat (11e-1, meal-sized portions counted); the store-size spike; the loose ends (11e-4).
- Rulings: 11e-0 evidence-neutral items stay neutral; T2-F an anchor with no fall seen starts fully faded; T3-2 the UNHAPPINESS accumulation flagged (fixed in 11f).
- Live: none. Range f058d593..7fb7ca3d (18); register #3651-#3657; pytest 3473.

## Plan 11f: live study replays (2026-10-10 to 10-11)
- Built `tools/replay_live.py` and the study foods, the S0 cadence gate, and live grades of satiety, energy, nicotine and monotony graded against replays of their own rings. Fixes the runs forced: renal sodium adaptation with water following sodium (C-6), volume thirst and sweat-sodium adaptation (C-9, C-14), thirst reading the stomach's pending water (C-8), Fitness-class billing with an EPOC pool (C-17) and a falling rate on the raw rate (C-26), the deficit refit on Karl's twin K, the monotony floor (C-22).
- Rulings: 11f-1 run before 11b; S0-1 the cadence gate reads writes per minute, never each minute's dtM; MC-1 keep the mechanism-candidate list; F5-2 harvest the science before the fix; C17-1 option C; 8-R live against replay is not agreement with a study; T5R-3 the foreground wait.
- Live: x260, x260b, x261-x266, x271-x276, x281-x284, x291-x296, x301-x302, x311, x321-x323, x331-x333, x341-x343, x351-x353. Range 011d2f40..24adf5c3 (104); register #3658-#3695; science S1665-S1798; pytest 3828.

## Plan 11g: gut satiety (2026-10-12 to 10-13)
- Built harvests 11-13, the oracle registry and the gut stage G fed at emptying, which was withdrawn when its fit went flat (emptying already carries the meal into F). Angus's option 1 shipped: the meal pool M fed at the eat, F counted past 730 g to the 1100 g capacity, stability checks among the oracles. The deficit drive was refit with Karl's well-fed arm held as a constraint, and the energy level is mirrored.
- Rulings: 11g-2 oracles pinned before the build; T6c-1 one system's fitted weight never drives another's quantity; T6c-4 compact fit artifacts; T7-1 DEFICIT_FLOOR removed; T8-1 a fresh record's empty window is a named limitation; T10-2 requote a moved line, never pin it.
- Live: x361-x364. Range 99d0f7d0..2c500d04 (47); register #3696-#3720; science S1799-S1894; pytest 3945.

## Plan 11h: exercise grading (2026-10-13)
- Built each Fitness exercise billed at its 2024 Compendium MET (squats 3.0 to burpees 7.5), the type read from a server wrapper of `ISFitnessAction.serverStart` and `serverStop`, every set minute resistance-vigorous through the exercise flag; the harness gained a stop through `ISTimedActionQueue.clear` and closed its helper dialogs.
- Rulings: never wrap a timed action's `new`; T2-1 an asleep guard; T3-1 graders stay frozen; T4-1 C-30 not built; T4-2 to T4-4 the movement end recorded as inference and 21 drivers' idle windows audited; HD-1 same-line appends split at the close.
- Live: x371, x372 (a set left running on the server past the stop), x381 (the dialog smoke). Range cbbf0076..1db9b54c (26); register #3721-#3739; science S1895-S1903; pytest 4032.

## Plan 12: polish, review and refactor (2026-10-13 to 10-14)
- Built a whole-mod review (K1, K2, S, C), bug waves A to C2 and refactor waves 3a-3d: an offline gap skipped, not booked; supplement-only ULs for Mg, niacin, folate and vitamin E (S1913, S1914); one engine read per member per player-minute (Java calls 108 to 80); the dead `dmod` chain removed; the drivers' shared `xlib`; the checker resolving superseded rows' pointers (8a5ec795).
- Rulings: P12-1 to P12-3 no-change rulings written where each item lives; P12-11/12/17 a reviewer's verbatim fix needs no re-review; P12-13 the baseline reset by name; P12-15 a superseded row's evidence resolves; P12-16 enriched staples exempt from the ULs; P12-18 a deferral past the mint waits for the close review.
- Live: x411 (the first xlib driver). Range f089fb0e..6a71486c (58; the plan file 797aad90 committed mid-plan); register #3818-#3829; science S1913-S1914; pytest 4173.

## Plan 13: lean-mass Strength (2026-10-14 to 10-15)
- Built Strength read from the body: lean mass on an FFMI scale × a trained neural factor T × an innate N0; the point-T growth law (signal × protein × energy gates; fit record `research/2026-10-14-strength-redesign/refit/`, its compact point now `data/fits/strength-refit-T/`), labile lean, detraining, regain toward a peak; the creation body table, weight-band traits on body-fat %, the low-fat hunger ramp, BeyondTen mastery; eleven harvests.
- Rulings: 13-1 one constants block; 13-45 a strength-linear level; 13-46 trait starts and anti-stacking; 13-47 every cap clamped at Kouri's natural limit (6.3 on S1915); Weak's floor is level 1; `xpPerSet` 360 (x423); the bench +38 % accepted under Rule 6; the detached-launch rule.
- Live: x421-x425, x431-x436 (x435 detached). Range 9a55c069..cdda734f (116; plan aca5907c); register #3830-#3877; science S1915-S2208; pytest 5592.

## Plan 14: the player guide (2026-10-15 to 10-16)
- Built `docs/mod-guide/` (index.html, charts.js, data.json) and its generators `tools/mod_guide_data.py`, `mod_guide_series.py` and `vanilla_model.py` with the `--check` gate: 39 charts and 147 series, vanilla against the mod, each badged by provenance; its source map now `docs/mod-guide/source-map.md`.
- Rulings: the source map is the run sheet; G12 a fifth provenance kind, `dataset`; I-3 an old live point drawn only where the HEAD replay matches at a stated tolerance; G17 an unsupported promise reworded or dropped; R-1 to R-4 a multi-day replay stays alive and hydrated.
- Live: x441-x445b (the vanilla baselines), x446, x447 and its regrade. Range abbee78c..92bdd753 (45; plan 10dfbc9b); register #3878-#3892; pytest 6444.

## Plan 15: game feel (2026-10-16 to 10-17)
- Built "subjective follows vanilla, objective follows science": the fitted hunger curve writer, the β volume fill, Overfull consequences and Well Fed, drain-and-floor lethal states on science's clocks (`NR_Kernel_Drain`), the lean-scaled water base, the fresh-record seed plate, and the drink-kcal-only liquid lane (Task 14b); the Energy and Hydration moodles removed.
- Rulings: M1 dehydration opens at 4 %; M2 thiamine clinical at about 6 weeks with none eaten; M3 `BMI_CHRONIC` 13; starvation opens at vanilla's timing; DRINK_NAMED a named non-reproduction; the guide's REBUILD_PENDING marker.
- Live: x451-x457 (x452b, x453b and regrades); fits `fit-hunger-curve-20261016`, `20261017b`, `20261017c`. Range 187cb492..c594ad0f (78; outline 187cb492, spec c5b65a14, plan af2a2d20); register #3893-#3954; science S2209-S2277; pytest 6983.

## Plan 16: the pre-upload fixes (2026-10-18 to 10-19)
- Built "nothing changes offline" (`K.resume`, record days in online hours, the stall carried at most 4 sub-steps a slot, no prune, a backup of the record on the character), the per-character body clock and a refitted hunger curve, long fasts on Forbes with Alpert's ceiling dropped from the deficit arm, the server-side refusal at Overfull 4 (`NR_Server_IntakeGuard`), the replay's named overlays and the release check.
- Rulings: F2 carry the stall, never freeze it; H1 the copy rewinds onto the world; the joint hunger fit 2:1, sleep off first; QualityCooking's buff a limitation line, not a `loadModAfter`; a driver may kill only its own recorded PID.
- Live: x461a/b, x462, x463a/b, x464-x467, the release x471 and x472 (written up offline after a rate limit), `fit-hunger-curve-20261018`. Range ed5d8855..c55ebd9e (71; plan fd84c54a); register #3955-#4003; science S2278-S2288; pytest 7290.

## Plan 17: the health curve and the combining options (2026-10-19 to 10-20)
- Built a remaining fraction per lethal state, `NR.DeathPace` (Vanilla, Shortened, Realistic) and `NR.HealthCombine` (Worst, Multiply, Add), `tools/calibrate_drain_curve.py`; revision R1 (straight lines in place of the log curve, under equitable total punishment) and R2 (each target a ceiling that rises only as the body recovers).
- Rulings: T1-4/T2-1 the smoothed BMI clock; T2-2 Realistic rates fixed in game time; R1-5 never under vanilla's level-4 rate; R2-2 no extrapolated fall while lapsed; T5-1 lanes must not collide.
- Live: x481-x485 (an accidental x485 boot killed, not a run). Range 7b784c4c..8e21d83f (67; plan 869ef685); register #4004-#4056; pytest 7545.

## Plan 18: symptoms through vanilla's moodles (2026-10-21)
- Built a per-cause symptom table on progress p = 1 − frac (flat, linear and knot shapes), folded per channel (the endurance cap takes the minimum, pain adds per part under a cap, the stress and unhappiness floors take the maximum), scaled by Severity, with Overlay dropping starvation and dehydration; the guide's divergence-first rework.
- Rulings: T3-1 never lower a part's added pain; T4-1 a mod defect fixed before the boot; T4-2 a second release session; T56-1 four causes can reach Pain 3.
- Live: x491, x492 (P3 unmeasured: `{}` against `[]`), x493-x495. Range 64b057c4..113e1d71 (37); register #4057-#4118; pytest 7844.

## Plan 19: tuning dials and food hedonics (2026-10-21 to 10-23)
- Part A built the dial registry (`NR_Data_Dials.lua`, about 650 dials, `K.dials.get` resolved at load into table fields, sandbox options generated from it, `tools/dials.py`, `dial_lint`, `tools/tests/gitenv.py`), every wave golden byte-identical. Part B built food hedonics R1-R4 (`NR_Server_Hedonics.lua`, `tools/food_hedonics.py`, the `hedonics_budget.py` oracle) and the guide's Food mood section.
- Rulings: T1-1 dials resolve to table fields; T4-1 fix `recipe_scan`'s spice rows first; T4-2 R3's `src` names the dispute; T5-1 `PAIR_SHARE` 0.95; T6-1 a dish's taste class is its heaviest ingredient type; T7-1 static-field pairs may span 10 s; T8-1 the cook's scale covers evolved dishes only. A stray test commit (e68042a1, removed in 3f8ab5a8) is a GIT_DIR leak.
- Live: x501-x504 (with the x502 regrade), the x505 smoke, `hedonics-budget-20261023`. Range 0ac21a9f..7d247fc2 (83); register #4119-#4172; science S2289-S2309; pytest 8269.

## Plan 20: slim the docs and comments (closed, 2026-10-24)
- Spec `specs/2026-10-23-slim-docs-design.md`, plan `plans/2026-10-23-plan-20-slim-docs.md` (Angus's decisions A, 3, b, i, beta, y). Built: the claims archive (`claims-archive.tsv`; 297 superseded rows archived, 67 retired, none minted), the `retire` and `archive-superseded` delta ops, tag pins, per-run `GUIDE.md` (artifacts.md 6402 -> 288 lines), checker rules 12 (orphan) and 13 (owner-block), `comment_id_lint`; this record archived at `program-record-v19` with [research-notes](../reference/research-notes.md); CLAUDE.md 247 -> 162 lines with [process/lessons](../process/lessons.md); every page rewritten lean (areas -31 %, platform -21 %, facts -20 %); mod comments 7732 -> 4592 lines with code proven identical.
- Rulings: P20-1/P20-6 (waves: writers, an integrator on an archive copy, serial applies), P20-2 (tag-form citations), P20-3 (fit points under `data/fits/`), P20-7 (closed plans stay until a consolidation), P20-9 (pointer-only base check), P20-14 (untagged HEAD facts stay), P20-17/P20-18 (orphan and owner-block rules), P20-19 (the page and register size targets missed are accepted: meaning beats length, the remaining bulk is owned evidence).
- Range ae6d9036..the close commit (36 commits); pytest 8329.

## Plan 21: the agent harness feasibility exploration (closed, 2026-10-26)
- Spec `specs/2026-10-26-agent-harness-design.md`, plan `plans/2026-10-26-plan-21-agent-harness.md`, report `specs/2026-10-26-agent-harness-report.md` (Angus's decisions: one interface for a scripted bot and a later LLM agent; built in the harness, separable; prove survival; a pure-Lua mod over files; 5 Hz plus events; one goal at a time; unattended). Built: `testing/PZAgent/` (Core, Link, Sense, Act, Main: JSON lines to `Lua/pzagent/<user>/state.log`, `cmd.txt` by seq, goals goto/open/loot/eat/drink/fight/flee/sleep/stop as per-tick state machines, the scan chunked and emitted in parts); `testing/agent/` (`link.py`, `world.py`, `policy.py`, `summary.py`, `grades.py`, `grade_c.py`, `reasons.py`, the drivers `a_pipe`, `a_pipe_2`, `a_pipe_3`, `b_actions`, `c_survive`, `c_survive_dense`); fixtures `agent` (Zombies 5) and `agent0` (none); 300+ offline tests under `testing/tests/pzagent/` on a lupa 5.1 host. Stage A ran three passes (artifacts `a_pipe-20261026-101003`, `a_pipe_2-20261026-115846`, `a_pipe_3-20261026-130558`; rows #4173–#4182 on `platform/harness.md#agent`) and ended NO-GO on its budget: the link held (append mode, 0 gaps, 0 missing members; mean tick cost 0.482 ms), the scan's per-tick cost is governed by the part size (60 squares read 7 ms; emit ≈ 0.5 ms per KB), the walk's ack→motion is ≈ 0.5 s on a direct path, the tick gate sits at the 1 ms clock's resolution; Stages B and C are built, reviewed and unrun. Recommendation: go-with-changes (grade the tick on the 60 Hz mean; one boot with 20-square parts and an ack→first-movement measure; then B, then C).
- Rulings: P21-0 (cmd.txt key=value), P21-1 (append probe, chunk fallback), P21-2 (Start-Process detached launches polled through the artifact), P21-3 (lupa host with stubs; a missing member reported, never raised); the scan15 gate reads the per-tick frame cost; every position goal takes world coordinates; stuck means no movement; a failed goal clears its walk; a zombie-free fixture for Stages A and B (a boot-time `Zombies = 6` does not despawn a provisioned population); the in-session memory stop is 0.5 GB on two reads; Stage A ends NO-GO on its budget and the plan goes to the report. The full list is the report's "Decisions taken".
- Range e5829564..3442e8b8; pytest at the close 8649 passed, 28 skipped.

## Plan 21b: the agent harness, the go-with-changes passes (closed, 2026-10-26)
- Plan `plans/2026-10-26-plan-21b-agent-harness-go-with-changes.md`; the report's § 7 (`specs/2026-10-26-agent-harness-report.md`) is the deliverable. Angus ordered the report's § 6 changes run ("run the go-with-changes boot"). Built first: the two parked must-fix items (vanilla classes index-checked before every action build; the policy never cools a pre-empted goal nor passes over the threat branch), 20-square scan parts, `gate_a4` (the tick on the 60 Hz mean; motion as ack→first position change), `a_pipe_4`. Five live sessions, each a committed artifact with its guide and register row: Stage A pass 4 (`a_pipe_4-20261026-181848`: NO-GO on scan15 alone — a per-line emit cost of about 1.7 ms that does not shrink with the part; the tick mean 0.794 ms and the ack→first-move p90 195 ms pass); Stage B pass 1 (`b_actions-20261026-183143`: loot, eat and drink live for the first time, every eat seen by the server; NO-GO on `completed`, the fixture holding no square with both food and a fluid container, and a beside-square defect in the driver and the Lua's `adjacentTo`) and pass 2 (`b_actions_2-20261026-194009`: two picks a repetition, `solidTrans` squares skipped; 13 gotos, 8 loots, 5 eats, 5 drinks all done, `open` live at two locked windows; NO-GO on `completed` 2 of 5, bound by the world's four fluid containers); Stage C run 1 (`c_survive-20261026-183905`: death at game minute 670 after 407 s — a fight/flee flap, a 210 s standoff at 2.74 tiles the fight never closed, a walking flee, an unexplained 25-health fall while looting) and pass 2 (`c_survive_2-20261026-195516`, after the policy's threat hysteresis and the Lua's closing step and every-tick run ask: death at game minute 593 after 119 s — the hysteresis held, the fight closed to reach, the flee's flags set but its pace a walk's, the same health fall at the same 37th inventory item). The dense run never ran. Recommendation (§ 7.6): go-with-changes as a test tool, not yet a survival agent; spike D not yet; the JVM fallback's condition met but unproven.
- Rulings: P21b-0 (the ordered extra pass graded by `gate_a4`), P21b-1 (BUDGET_S 800), P21b-2 (the measure changes, the legs' start does not), P21b-3 (the must-fix items land first); the scan15 NO-GO stands and B and C still run under Angus's order; one Stage B fix pass and no third; Stage C's one fix pass and no third run; the `DISENGAGE_R` count widening the too-many rule is the first fix of any third run. The full list is the report's § 5.
- Range 9a728223..the close commit; pytest at the close in CLAUDE.md § 3. Next: Plan 22, a fresh-eyes design pass toward a future-proof base (Angus, 2026-10-26).

## Plan 22: the agent base, candidate K1 (closed, 2026-10-27)
- Spec `specs/2026-10-27-plan-22-agent-base-design.md`, plan `plans/2026-10-27-plan-22-agent-base.md` (19 tasks), report `specs/2026-10-27-plan-22-agent-base-report.md` (the deliverable; its § 7 recommends the fixes first and an LLM planner on `tools.json` after). Built: the PZA/1 schema `testing/agent/base/schema/pza1.json` with its generator `tools/pza_schema.py` (three targets: `shared/PZAgent_Schema.lua`, `pza1.py`, `tools.json`); the Lua base `testing/PZAgent` 1.0 (Core, Link with positional frames, group deltas and one flush a tick, the `OnPlayerUpdate` Motor, the Skills runner with ten typed skills, Sense, the dirty-set Map, Main); the server's `damage.watch` and `zombie.get`; the Python base `testing/agent/base/` (`FileTransport` behind a Transport seam, `Actions`, `World`, the Fight/Flee/Explore/LootHouse policies and `Survive`, the versioned gates `gate_x4`, `measure_x5`, `grade_d`); the fake mod, the fault test and the replays under `testing/tests/pzagent/`; the drivers `x4_link`, `x5_combat`, `d_survive` with their graders. The Plan 21 layer stays frozen with the drivers that import it (P22-0); `PZAgent_Act.lua` and `PZAgent_Bench.lua` left, their 115 tests deleted by name (the report's appendix).
- Five live sessions, each a committed artifact with its guide and register rows: X4 `x4_link-20261027-171916` (NO-GO on the two cost gates: the 60 Hz tick 1.672 ms against 1.0, the worst tick 19 ms against 3; GO on gaps, Lua errors, parks, the legs' p90 165 ms and the kept map 1.0; the sidecar trigger read not fired on the honest population, S-18; #4203–#4207), X5 `x5_combat-20261027-173248` (a measurement: the client's copy of zombie health within 0.001 of the server's on 15 of 15 pairs, 10 of 15 swings started, the agent's own loop 29 and 12 ms with the driver's 2 s server reads named as the instrument's cost; #4208–#4210), the acceptance `d_survive-20261027-173724` (stopped by a transport sharing violation at 134 game minutes, fixed at 6925886d: S-24) and `d_survive-20261027-175917` (64.70 game minutes under the planner, death by zombie wounds explained by the frames' wound arm; #4211–#4213). Angus's per-session approval was his message of 17:11 to iterate without waiting (S-17).
- Rulings S-1 to S-26 in the report's § 6 (the ledger is gitignored): S-7/S-8 the keyed kinds' envelope, S-11 seq rises in file order, S-14 the watch ignores light, S-15 a raising Java member is contained, S-16 a death is explained by a tagged or a wound arm, S-18 the sidecar reading, S-19 go-with-findings, S-21 the fight reflex stays in Python (provisional), S-25 container pointers, S-26 a bus step's reply time subtracted from a loop reading. Open for the fix wave and Plan 23: the fight that hits nothing (a door the map's square record cannot place; the Fight's stall clock), the stuck re-send, the loot overload, the spawned zombie in no frame, `grade_d`'s wound window, `damage.watch`'s 200-record list, the 60 Hz cost and the command-accept burst (the X4 fix pass `x4_link_2.py`), the schema's cost wording.
- Range ba5c4024..the close commit; pytest at the close in CLAUDE.md § 3.

## Plan 23: the survivor (closed, 2026-10-29)
- Spec `specs/2026-10-28-plan-23-survivor-design.md`, plan `plans/2026-10-28-plan-23-survivor.md` (21 tasks), report `specs/2026-10-28-plan-23-survivor-report.md` (the deliverable; its § 7 recommends a threat instinct that sees the group before it fights, then the one-step death's cause on the server and the pathfinder's edges in the jar, before more goal-layer or LLM work). Angus's standing direction (2026-10-28): drive toward a character that fully plays and survives, scripted instincts and LLM broader decisions, no design-approval round. Built: PZA/1.2 (the squares' edges, `me.hour`, `sleep`, `interact.maxWeight`, `item_added.use`) and PZA/1.3 (the `death` event, P23-AO), the paced poll, the driver library `testing/agent/driverlib/` (the session, the poll thread, the record, the chain, the day, the shot taker: screenshots of the client window indexed to the frame seq and the decision line, P23-AL, Angus's suggestion), the survival planner (`Survive` with the threat, need, load, night and goal branches; the goal layer with `ScriptedSource` and `LLMSource` over the `claude` CLI) and its four survival iterations ruled from the live deaths (P23-AG, P23-AJ/AK, P23-AM, P23-AP), `pzt snapshot`, the saved UI closed at prepare (P23-AN), the grades frozen and versioned (`grade_e1` for E1–E4; `grade_e2`, `grade_f2`, P23-AQ).
- Eight live sessions of nine, each a committed artifact with its guide and register rows (#4217–#4287): X4-3 (the paced poll, NO-GO at 1.012 ms), X5-2 (the pinned fight and the line check live), the five chains E1–E5 each one session ending in the character's death (game minutes 606, 592, 600, 627 unseen by the driver, 595: a fence corner, a bathroom, a stuck shelter walk, a stuck corner under a group with the first kill, a horde of seven within 2.6 s), and F1, the LLM goal source's first session (84 game minutes, the plan's longest, three kills, 14 calls at p50 4.1 s, one refused answer). Open threads on `docs/reference/research-notes.md#agent-link`: the horde's listing reach and a threat memory, the one-step deaths, the fence climb against the map's edges, the walk keeping its steer, the melee's unstarted swings, the night and the needs never reached live.
- Rulings P23-A to P23-AR in the report's § 8 (the ledger is gitignored); the process rule on write-up briefs (a trace is a hypothesis the writer verifies) in CLAUDE.md § 6 and `docs/process/lessons.md`. Full pytest 10298 passed, 28 skipped (the Plan 22 baseline 9481 plus the plan's tests).

## Plan 24: the group (closed, 2026-10-30)
- Spec `specs/2026-10-29-plan-24-the-group-design.md` (§ 6 items 1–27 carry the rulings P24-F to P24-AY and each session's reading), plan `plans/2026-10-29-plan-24-the-group.md` (Tasks 1–27 and the run sheet of Tasks 24, 28–40), report `specs/2026-10-30-plan-24-the-group-report.md`, the written guides' notes `specs/2026-10-30-plan-24-guides-notes.md`, the jar reads `specs/2026-10-29-plan-24-jar-reads-2.md`.
- Eight live sessions and the stance probe, each a committed artifact with its guide and register rows (#4294–#4427 minted this plan): F2 (2 kills), E6 (1), E7 (0, the woods), E8 (4), E9 (0, a group from the start), E10 (0, the day cap under the strain hold), E11 (3, two stomps and a swing), F3 (5, all stomps, the day cap at full health on the strategy prompt); the stomp on a fallen target the agent's killer; the record's grades undercounted every stomp kill until `grade_e9` read the act lines (Task 40).
- Survival iterations 5 to 12 on the planner (the stance and the backpedal, the engage, the rag stock and the legs, strain-aware fighting, the shove and the stomp, the pull, the doorway stand, the wounded fight, the hold on the stiffness, the listing-edge hold, the fill from a loaded source; the Fight, the Flee and the threat branch split into their modules); PZA/1.4 → 1.7.1 on the agent mod; the LLM goal source's strategy prompt from the guides; the shot guard and the window-content grab; the slow marker's inner loop. Rulings P24-A to P24-AY in the spec; the process rules (the loop P24-AF, the live-session quiescence, the gate race, the shot rules) in CLAUDE.md §§ 5–6 and `docs/process/lessons.md`. Full pytest 11811 passed, 29 skipped (the Plan 23 baseline 10298 plus the plan's tests; one test of removed bag code deleted by name).
