# The Nutrition Revamp player guide — design

Status: approved in brainstorming (Angus, 2026-10-15: "go ahead and spec plan and execute"). The plan is written from this spec.

## 1. Goal

A player-facing guide to Nutrition Revamp. It describes every system the mod has, how each differs from vanilla Project Zomboid, and what can and can no longer happen in play. Charts compare vanilla with the mod using tested values. Players come first: plain language, charts first, mechanics second. The science sits behind collapsed boxes.

Angus's choices in brainstorming (2026-10-15):

| Question | Choice |
|---|---|
| reader | players |
| format | an interactive web page, published as a private claude.ai artifact and kept in the repository |
| evidence | live measurements, plus the mod's own code run offline, plus new live runs for the headline vanilla-versus-modded comparisons; each series is labelled by source |
| science depth | light main text, with an expandable "The science" box per section and a reference list |
| structure | layered: At a glance, then Scenarios, then the Systems reference, then back matter |

## 2. Content

### 2.1 At a glance
**A comparison table** with three columns: Vanilla / Nutrition Revamp / What it means for you. One row per system:
- hunger;
- thirst;
- weight and the body;
- Strength;
- the weight-band traits;
- nutrients;
- foods;
- death by hunger, thirst or deficiency.

**Four headline charts:**
- **H1:** hunger over 6 game hours after one meal, vanilla against the mod;
- **H2:** body mass over 30 game days at 1500 kcal a day, vanilla against the mod, the mod's split into fat and lean;
- **H3:** Strength over one game year of training, vanilla's experience-driven level against the mod's lean-mass level;
- **H4:** five common foods, with vanilla's calories and macros against the mod's.

### 2.2 Scenarios
Each scenario sets vanilla beside the mod. Its prose links into the Systems reference.

1. **S1, Your first day:** spawning, eating, the panel, the moodles, and what feels different.
2. **S2, Skipping meals and starving:**
   - a 36-hour fast and its refeed;
   - hunger rising as fat is lost;
   - the refeeding risk;
   - what no longer happens: death by hunger in the Managed mode, and hunger cleared by any food's hunger value.
3. **S3, Living on one food:** weeks on one canned food, with the deficiencies that develop, monotony, and what fixes them.
4. **S4, A year at the gym:**
   - training with protein;
   - Strength rising toward the natural cap;
   - Strength fading without training and regained fast;
   - vanilla's experience-driven levels beside it.
5. **S5, Choosing your body at creation:** Strong, Weak, Overfat and Gaunt with its underfed start, and how each body drifts over the first months.
6. **S6, Coffee, beer and no sleep:** caffeine tolerance, blood alcohol and the hangover, and sleep debt raising hunger.

### 2.3 Systems reference
**Sections:**
- nutrients and foods;
- eating and the stomach;
- hunger;
- thirst and salt;
- monotony;
- the body;
- exercise and energy;
- Strength;
- the body traits and character creation;
- deficiency and excess;
- caffeine, alcohol and sleep;
- what you see on screen.

**Each section has these blocks, in order:**
1. **Vanilla:** what the game does.
2. **This mod:** what the mod does.
3. **The charts.**
4. **What can happen.**
5. **What no longer happens.**
6. **The science**, collapsed.

### 2.4 Back matter
- the sandbox options a player meets, linking to the operator README for the rest;
- compatibility;
- known limitations;
- references.

## 3. Evidence

### 3.1 The data file
- **The generator.** `tools/mod_guide_data.py` builds `docs/mod-guide/data.json`, and the page reads every number from that file. No number is typed into the page.
- **What each series carries:**
  - an id;
  - its points, unrounded;
  - units;
  - a badge, from §3.2;
  - provenance.
- **Provenance is one of:**
  - artifact: run id, file and JSON path, never a do-not-cite key or its parent;
  - kernel: the commit, the script and the inputs;
  - vanilla model: the formula ids and the register rows they cite;
  - study: an S-id.
- **The `--check` gate.** `--check` regenerates the file and fails on any difference, as `tools/food_nutrients.py --check` does. `--write` rewrites it.

### 3.2 Badges

| Badge | Source |
|---|---|
| Measured live | a committed artifact under `testing/artifacts/` |
| Simulated by the mod's code | the mod's kernel, run offline under lupa at the named commit from the inputs the live runs used, linked to the live run that shows the replay matches the game |
| Vanilla, measured | a vanilla-baseline live run (§3.4), or a measured row on a `docs/facts/` page |
| Vanilla, from the game's code | the vanilla model (§3.3) |
| Study | a row of `docs/reference/science.tsv`, drawn as reference points |

A chart that mixes live points and simulation draws live points as dots and simulation as lines.

### 3.3 The vanilla model
- **What it is.** `tools/vanilla_model.py`, a small model of vanilla's hunger, thirst, weight (the calorie store and its weight change) and Strength experience. It is built from the formulas the register already holds for vanilla, on `docs/facts/body-and-weight.md`, `docs/facts/nutrition-core.md`, `docs/facts/perks-and-strength.md` and `docs/facts/character-stats.md`.
- **Its formulas.** Each formula is a named function citing its claim ids. A rule the register lacks is read off the jar (`C:\Users\Angus\pz-b42`, `./pz.sh`) or the game's Lua, and minted as a claim in the commit that lands it (CLAUDE.md § 4).
- **Its validation.** It is validated against the vanilla-baseline runs (§3.4) before any chart extrapolates with it. Each validated quantity's miss is stated in the data file.

### 3.4 New live runs
**The vanilla baseline.** The fixture runs with the mod not loaded and vanilla Nutrition on: the game as players know it. Sessions:
- **V1**, serving H1, S1 and S2: a measured meal, then hunger, thirst and weight over game hours; then a fast and a refeed.
- **V2**, serving S3: one food eaten for several game days, read for weight and stats.
- **V3**, serving H3 and S4: Strength experience from push-up sets over a session, with the level and experience curve.
- **V4**, serving S6: coffee and beer, then intoxication, endurance and fatigue over game hours.

**Modded runs** are needed only where no committed artifact covers a scenario's live point. The plan maps each chart to its source first, and lists the gaps.

**CLAUDE.md § 5 governs every session:**
- a driver per run;
- offline failing grades;
- the memory gate;
- the artifact commit with its row, guide and do-not-cite keys;
- live readings minted as claims in their run's commit or the plan's register task.

### 3.5 Display rules
- **Defaults.** Charts use the default sandbox options and a male character, since `NR.SexSpecific` is off by default.
- **Rounding.** Values are rounded for display only. The hover shows the stored value.
- **Promises.** Every "what no longer happens" promise rests on a register claim, a science row or a data series, checked at the fact-check review.

## 4. The page

### 4.1 Files and layout
- **Files:**
  - `docs/mod-guide/index.html`;
  - `docs/mod-guide/charts.js`;
  - `docs/mod-guide/data.json`.
- **Layout.** It follows the `artifact-design` skill's page contract, loaded before the page is written:
  - a sticky table of contents;
  - anchors for every scenario and system;
  - collapsed science boxes;
  - light and dark themes;
  - phone width with a 16px gutter.
- **Charts.** Chart.js from cdnjs. Each chart has:
  - a vanilla/mod toggle where both series exist;
  - hover values;
  - its badges, each opening its provenance.
- **Prose numbers.** A number in the prose that `data.json` holds is filled from it at render time.

### 4.2 Language
The main text is plain. These terms appear only inside "The science" boxes:
- MET;
- FMI;
- kernel;
- fatDep;
- partition;
- oracle;
- any S- or #-id.

### 4.3 Publishing
- The page is published as a private claude.ai artifact, with `data.json` and `charts.js` as its files.
- The repository copy is the source.
- A Workshop description linking to it is out of scope here.

## 5. Upkeep
CLAUDE.md § 3 gains a gate. `python tools/mod_guide_data.py --check` must be in sync before any commit that touches:
- `mod/`;
- `tools/mod_guide_data.py`;
- `tools/vanilla_model.py`;
- `docs/mod-guide/`.

A change of mod behaviour that moves a chart regenerates `data.json` in the same commit.

The guide is not a register page: it carries no claim tags, and its provenance lives in `data.json`. The pages under `docs/areas`, `docs/facts` and `docs/platform` remain the cited reference.

## 6. Verification
- **The tools.** The data tool and the vanilla model have tests, including a mutation case for each generator. A changed formula or a changed kernel output must fail `--check`.
- **The fact-check review (Opus).**
  - Every sentence of the page is checked against the register, the science register or `data.json`.
  - The reviewer re-derives a sample of series from their artifacts and from the kernel.
- **The plain-language read** (§4.2).
- **The live-evidence review** of the new runs, as Plan 13's.

## 7. Out of scope
- the Workshop description;
- the operator README (it stays the operator guide);
- a modder guide;
- translation.
