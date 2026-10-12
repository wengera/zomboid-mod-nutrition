# Gut satiety: the meal pool rebuilt as a gut stage (C-1) — design

- **Status:** design approved by Angus, 2026-10-12.
- **Source:** mechanism candidate C-1, from Plan 11f's live study replays (`docs/superpowers/research/2026-10-10-live-study-replays/04-mechanism-candidates.md`).
- **Decisions (Angus, 2026-10-12):**
  - judge it on both the surplus arm and post-meal time courses, with the harvest first;
  - weight the signal by macronutrient where the evidence supports it;
  - use the two-stage chain, chosen as the most accurate and the cleanest once built.

## 1. Why
The satiety model (Plan 11c, structure D; refit in 11d and 11f) sates on two signals:
- **F**, the stomach's fullness;
- **P**, a meal pool fed in full at the eat that halves every 0.7 game hours.

P is an abstraction. Its single fitted half-life stands in for gastric emptying plus the gut hormones (CCK, PYY, GLP-1). This has two costs:
- **Karl 2021's well-fed arm.** The study suppresses hunger by about −55 %; the model reaches −45 %, and post-meal hunger never falls below about 0.08. Fitting that arm through the energy-balance term pulled `BALANCE_SPAN_KCAL` down to 3100, about 20 % below its deficit-only fit of 3800. That entangles the deficit drive with a surplus effect.
- **Meal timing.** Large, fatty or protein-rich meals empty more slowly and sate for longer. P cannot express that beyond its one half-life.

The mod already empties the stomach by meal size and composition (`K.stomach.drain`; Hunt 1985, S0131; Mudie 2014, S1245; Camps 2016, S1234). The gut signal can therefore be fed by what the stomach actually empties.

## 2. Evidence plan (a harvest before any fit)
Three Opus research agents run in parallel. Each files science rows in a part file. Each harvest passes a citation review before its rows are minted (CLAUDE.md § 4.8). Every harvest so far has failed its first review, so budget for a correction round.

1. **Hormone and hunger time courses after meals of known size and composition.**
   - Collect CCK, PYY, GLP-1 and ghrelin over 0–6 h, with hunger and fullness ratings on the same timeline wherever the study reports them.
   - Cover meal size (about 250–1,000 kcal), macronutrient at equal kcal (protein, carbohydrate, fat), fibre, and liquid against solid.
   - This decides the number of stages and their time constants.
2. **Nutrient transit and absorption.**
   - Collect small-intestinal transit, glucose and amino-acid appearance curves, and duodenal-infusion studies that deliver nutrients past the stomach. Those separate the gut signal from fullness.
   - This sets the rise and clearance without a blind fit.
3. **Surplus and repeated meals.**
   - Collect the Karl 2021 well-fed arm in detail (research 03 already has its facts), overfeeding studies with hunger ratings, and evidence on whether satiety builds up meal on meal across a day.

## 3. The model

### 3.1 Signals
- **F, fullness (unchanged).** `K.stomach.fullnessMass / CAPACITY_MAX_G`, clamped to [0, 1]. Its weight is `FULL_WEIGHT`, refit jointly with G.
- **G, the gut stage (new; replaces P).** It is stored as `record.satiety.G`.
  - **Feed.** Each minute, `K.stomach.drain` returns what it emptied in that substep. G gains its kcal weighted by nutrient: `W_PROTEIN`, `W_CARB`, `W_FAT` and, if evidenced, a fibre term. A weight the harvest does not support stays at the neutral 1 (ruling 11c-7's convention).
  - **Clearance.** First-order, at `G_HALF_LIFE_H`, which comes from the harvest. The appetite traits and the sandbox's stats multiplier scale it as they scale P's decay today (ruling 11c-11).
  - **Read.** `gRead(G) = 1 − 1 / (1 + 3 (G / G_REQ)^G_STEEP)`, the shape of today's `post(P)`. It is near-logarithmic, so a snack leaves hunger in between.
- **A, the absorbed stage (conditional).** It is added only if a single G fails a time-course oracle that a second stage fixes (§ 4).
  - **Feed and clearance.** G clears into A, and A clears at its own half-life.
  - **Read.** `aRead(A)` has the same shape with its own constants.
  - **Storage.** It is stored as `record.satiety.A`.

### 3.2 Composition
- `sated = 1 − (1 − FULL_WEIGHT·F)(1 − gRead(G))`, times `(1 − aRead(A))` if A exists.
- Downstream is unchanged:
  - hunger = `K.hybrid.hungerTarget(sated, energyState)` × circadian × acute exercise × sleep × nicotine, capped by the writer;
  - the Overfull moodle reads F alone.

### 3.3 Seeding
On first sight the mod still solves for the hidden state that reproduces vanilla's HUNGER (today `seedP`). It now seeds G, under a cap sized like `P_SEED_MAX` (about a 1,000 kcal mixed meal), and never seeds A.

### 3.4 Removed
- P and `K.satiety.feed` at the eat.
- `P_REQ`, `HALF_LIFE_H`, `P_SEED_MAX`.
- The P-based tests, which are rewritten against G.
- `record.satiety.P`.

There is no migration: the mod is unreleased (CLAUDE.md § 6).

### 3.5 Performance (Rule 6)
- No per-tick work.
- Per player-minute, inside the drain that already runs: one weighted multiply-add, one `exp` for clearance, one read, and the same again for A if it exists.
- The kernel is benched before and after (lupa); the expected cost is about 1 µs per player-minute.

## 4. Acceptance (the fit's oracles)
- **Kept from 11c/11d:**
  - S1247: Callahan's preloads, from the request and fasted;
  - the 650 kcal anchor (S1247, S1248);
  - S1231: Rolls's soup, three arms;
  - S1233: the volume drink;
  - S1222: the protein contrast.
- **New:**
  - the post-meal hunger time course at two or three meal sizes;
  - one protein-against-carbohydrate time course at equal kcal;
  - Karl 2021's well-fed arm at about −55 % (tolerance set when the row is minted).
- **The deficit drive, refitted afterwards on deficit studies alone.**
  - Refit `BALANCE_SPAN_KCAL`, `K.hybrid.DEFICIT_FLOOR` and `EX_BYPASS_LO`/`HI` through the server path (`test_replay_live_energy.py`).
  - Whybrow, King, E-MECHANIC and Karl's deficit arm must pass.
  - `BALANCE_SPAN_KCAL` is free to move back toward its deficit-only fit.
- **Stage rule.** Start with G alone. A second stage enters only on a named failing time-course oracle that it fixes.
- **Labelling.** Every constant is on a settled science row or labelled a game choice, with the rows that bound it.

## 5. Order of work (for the plan)
1. **Harvest** (§ 2): three parallel agents, a citation review and the mint.
2. **Oracles.** Encode § 4's new oracles from the minted rows before any model change, and confirm they fail or pass as expected on today's model.
3. **The G build.** Kernel, writer and seed; remove P; store INPUTS; tests; golden re-record under this named cause.
4. **The joint fit.** FULL_WEIGHT plus G's constants against § 4. Add A only under the stage rule.
5. **The deficit-drive refit** on deficit studies alone.
6. **Live checks** (§ 5 harness rules):
   - one meal time course, live against its replay;
   - one surplus day of three large meals.
7. **The record.** Rows, pages, the lessons rule if a platform fact is found, and the 11b amendments.
8. **The close.**

## 5a. Refactoring (Angus, 2026-10-12)
Every task that touches code refactors heavily as it goes (CLAUDE.md § 6). Expected targets here:
- the satiety kernel's structure once P leaves;
- where the stomach drain and the satiety feed live, and how the writer reaches them;
- the long constant labels, which may move into a data table;
- the energy and hybrid split around the deficit drive.

Each task's brief names its refactor scope, and each review judges structure and performance beside correctness.

## 6. Risks
- **Thin hormone evidence.** Hormone studies are mostly short, small-sample sessions, and hunger ratings follow hormones only loosely. The fit therefore targets hunger over time, not hormone levels. Part of G's time course may stay a labelled game choice.
- **Too many constants.** The model has more constants than today's. The stage rule and the oracle count guard against over-fitting.
- **A full refit.** Every 11c/11d satiety constant, oracle and the golden move. The refit is one named change per task (ruling T2-1).
- **The seeding cap.** The cap and its read on a fresh record need re-deriving. Today's floor of 0.203 at the cap changes.

## 7. Amendment (Angus, 2026-10-12, after the Task 6 fit)
**What happened.**
- The Task 6 fit of the emptying-fed G was degenerate. G's read went flat (G_STEEP 0.0197), because the stomach's energy-limited emptying already carries meal size into fullness F, and G fed at emptying counted it a second time.
- The costs: a fasting rise about 4x slower than under P; evening requests swinging about 10 h on a 2 % factor; and Karl's post-meal lows never deepening.
- A spike over six model forms (`.superpowers/sdd/2026-10-12-plan-11g-gut-satiety/task-6b-spike-report.md`) drove the eat-feed fraction to 1 in every fit.

**Angus chose (option 1):**
- **G is fed in full at the eat.** It is the weighted-kcal meal pool, cleared first-order, and Kinetics clears it per substep through `K.satiety.drain`. The feed at emptying (§ 3.1) is withdrawn.
- **F counts past the comfortable maximum up to the hard capacity.** F = mass / CAPACITY_MAX_G, clamped to [0, CAPACITY_HARD_G / CAPACITY_MAX_G] (1100 / 730 = 1.507; S1250, S1253) instead of [0, 1]. The sated product is clamped to [0, 1].
  - Reason: the resting and well-fed post-meal stomachs both sat at F = 1, so the clamp hid the well-fed day's fuller stomach (harvest 13: gastric emptying 612 against 182 min).
- **Three stability checks join the oracle registry**, so no later fit can go flat unseen:
  - the 650 kcal meal at 19:00 under hunger x0.98 / x1.00 / x1.02 returns within S1248's 425 min, spread at most 60 min;
  - after one 650 kcal meal at 08:00, hunger at +24 h is at least 0.9 x P's 0.42.

  These are design choices with no row, labelled as such.
- **The fat trio is scored on one common scale** (Melanson's), so W_FAT is not a scale artefact.

**The spike's result for this form:**
- loss 1.378;
- Karl −52.94 % (in band);
- fasting rise 0.466 at +24 h;
- no cliff;
- 8 named misses against 13.

**Accepted downsides:**
- the hunger nadir stays at minute 1 (studies: about 15);
- LIQUID_WEIGHT is weakly held;
- Karl's post-meal lows improve (0.55 / 0.38 / 0.41 of REST) but stay above the study's 0.21 / 0.21 / 0.11;
- Tieken's liquid against solid stays out of reach under every form.

The C-1 hormone mechanism the evidence describes is real, but the oracles at hand do not need a delayed feed: the stomach's overfill carries the well-fed effect.
