# Research slices — design for unattended execution

Decided by brainstorm 2026-09-09. Companion to [STRATEGY.md](../../../STRATEGY.md)
(the charter): this spec says *how* the charter's phases P1–P5 and T1–T2 get
done without anyone watching. Verified-against build for the whole program:
**42.20.4 (`b0bbce05d5`)**; every deliverable re-stamps the build it was
checked on.

## Goal and non-goals

**Goal.** Turn the remaining charter phases into slices that a session with no
memory of this conversation can pick up, finish, verify and hand off — so the
reference library gets built by a series of unattended runs on this machine.

**Non-goals.** Designing the mod (the library is the deliverable; design is a
later effort). Cloud/scheduled execution (every slice needs the local game
install, the jar, and the GPU-backed client). Any outward-facing action
(publishing, posting, contacting anyone) — those always wait for a human.

## Decisions made in the brainstorm

| Question | Decision |
|---|---|
| Operating model | **C** — plans written for cold start *and* execution begins immediately after approval |
| Order | **B** — verify as you go: P1 with its T2 scenario first, then P4, then T1 ahead of the P3 teardowns (so they are measured, not read), then P2, P5 |
| Judgment calls | **A** — take the default, log it in `docs/decisions.md`; never block |
| Experiments | encouraged in every slice: trial-and-error on the live server to confirm what code reading says |
| Structure | question-driven slices (Approach 1), with source sweeps folded in as tooling where a sweep is the cheapest way to answer a slice's questions |
| Execution style | subagent-driven: a lead session dispatches one subagent per task with review between tasks; live-server tasks are serialized (one session on this PC at a time); subagents on Opus, lead on Fable |
| Wiki access | `curl` with a browser user-agent (the plain fetcher gets 403); raw wikitext via `index.php?title=<Page>&action=raw`, which carries the wiki's `{{Page version|…}}` stamp |

## Slice catalog (execution order)

| # | Slice | Questions it must answer | Deliverables | Acceptance | Depends on | Est. h |
|---|---|---|---|---|---|---|
| 01 | P1a · Intake pipeline (food → body) | Every path by which eating moves hunger/thirst and calories/carbs/lipids/proteins into `Nutrition` — Java `Eat`, `ISEatFoodAction`, partial eating, cooked/burnt/rotten/frozen multipliers, drinks, the sandbox `Nutrition` toggle; which side computes it in MP | `docs/vanilla/eating-pipeline.md`; mirrors of the wiki pages used; `tools/wiki_mirror.py`, `tools/doc_lint.py`; harness `eat`, `nutrition.get/set`, `item.script` commands; `pzt doctor` | every modifier in one table with jar/lua citations; MP section names the computing side and packets, with a measured (M) row; predictions written for slice 04; lint green | — | 3 |
| 02 | P1c · Food item model & lifecycle | Full field reference for food script items; fresh → stale → rotten timeline incl. fridge/freezer; cooking state changes; evolved-recipe nutrition summation; packaged/canned items | `docs/vanilla/food-item-model.md` | complete field table with script + jar citations; MP section (item state ownership per spike S6); lint green | 01 | 3 |
| 03 | P1b · Body side | Hunger/thirst decay and their sandbox multipliers; weight → fitness/strength XP and speed; the moodles nutrition drives and their thresholds; appetite traits | `docs/vanilla/body-stats.md` | each effect has its numeric threshold cited; lint green | 01 | 2 |
| 04 | T2 · Accelerated nutrition scenario | Does the decoded weight model predict the live server? 3 game-days at a fixed daily intake at 30×, sampled hourly | harness test layer (`TK.test`, `TK.eventually`, assertions, scheduler); `pzt scenario nutrition-3day`; results JSON; "verified on server" section in `docs/vanilla/nutrition-core.md` | runs green unattended in < 15 min; measured vs predicted within the tolerance the doc states, or the discrepancy documented as a finding | 01, 02 | 3 |
| 05 | P4a · Food scanner + dataset | Every vanilla food/drink item with all nutrition and spoilage fields | `tools/food_scan.py`; `data/food-items.csv` + `.json`; `docs/vanilla/food-dataset-notes.md` | item count cross-checked against the live game via the harness; 10 items spot-checked in-game | 02 | 2 |
| 06 | P4b · Recipes & cooking dataset | Ingredient → result mapping; evolved recipes; nutrition deltas of cooking | `data/recipes.json`, `data/evolved-recipes.json`, notes | counts cross-checked in-game | 05 | 2 |
| 07 | T1 · Profile builder | Install a mod under test (workshop id or local path) with sandbox overrides; L0 layout lint | `pzt/profile.py`; `testing/profiles/*.toml`; `pzt run --profile`; `tools/mod_lint.py` | a two-mod profile passes; a profile with a missing mod fails | — | 3 |
| 08 | P3a · Nutrition-mod catalog | Which mods touch nutrition (approved list + workshop search), B42 status, APIs used; pick 3 for teardown | `docs/mods-survey/nutrition-mods.md`; ledger entry for the pick | ≥ 3 picked with rationale and sources | 07 | 2 |
| 09–11 | P3b–d · Teardowns ×3 | Template-driven, measured: installed via a profile, state probed with the witness | `docs/mods-survey/teardowns/<mod>.md` ×3 | every template section filled; MP behaviour measured, not inferred | 07, 08 | 2 each |
| 12 | P2a · Platform reference | B42 mod anatomy (verified); curated Lua API/events; how a mod overrides a vanilla item's nutrition (script merge rules) | `docs/modding/anatomy.md`, `lua-api.md`, `item-overrides.md`; experiment mods under `testing/experiments/` | each mechanism proven by a harness experiment (e.g. an override mod changing Apple's calories → witness) | 07 | 3 |
| 13 | P2b · Moddability wall map | What the mod cannot do (jar-locked) vs can vs can with a workaround: new nutrient fields, eat hooks, weight formula, moodles, sync | `docs/modding/wall-map.md` | every entry classified with evidence | 12 | 2 |
| 14 | P5 · Feasibility notes | Per design area (new nutrients, item pass, UI, MP sync, balance testing): mechanism, risks, what the research settled | `docs/feasibility/*.md` | every note cites the slice that established it | all | 2 |

Wiki mirroring is not a slice: each slice mirrors the pages it cites, so
mirrors accrue with use. Total ≈ 33 hours of agent work.

## Plans: waves and the template

Plans live in `docs/superpowers/plans/NN-<slug>.md`, one per slice, written
**just in time in waves**: wave 1 = 01–04 (right after this spec), wave 2 =
05–07, wave 3 = 08–11, wave 4 = 12–14. A wave's plans are written at the
previous wave's end from this spec plus the finished slices' findings.

Every plan has the same eight parts:

1. **Header** — slice id, phase, status, build to verify against, depends-on, estimate.
2. **Cold-start context** — the ten lines a fresh session needs: repo
   conventions; the two toolchains (`./pz.sh` in `C:\Users\Angus\pz-b42` for
   the jar — `grep`, `methods`, `refs`, `dump`; `python testing/pzt` for the
   live server); where prior findings live; the standing rules (citations, MP
   section, commit style: brief message, no attribution).
3. **Questions** — numbered; the slice is done when each has a cited answer.
4. **Method** — ordered steps with concrete sources (jar classes, Lua files,
   script paths, wiki pages) and the experiments to run on the harness.
5. **Deliverables** — exact file paths.
6. **Acceptance checks** — mechanical wherever possible.
7. **Expected decision points** with defaults.
8. **Done protocol** — ledger updates and the commit.

## The unattended protocol

Two ledgers at the docs root:

- `docs/progress.md` — the status board: slice, status (`ready` / `in progress`
  / `done` / `blocked`), date, commit, one-line outcome, a **resume note** for
  in-progress slices (done / next / half-written files, updated at every
  checkpoint commit), and a **ripples** list (findings that change a later
  slice's plan).
- `docs/decisions.md` — the choice ledger: date, slice, the choice, the
  alternatives, why. Every default taken unattended goes here.

The run loop a session follows:

1. Open `docs/progress.md`; take the first `ready` slice whose dependencies are `done`.
2. Read this spec, the slice plan, and the docs it links. Nothing else is assumed to be in memory.
3. Work the method; run experiments freely; at each judgment call take the default and write the ledger entry.
4. Run the acceptance checks; record their results in the plan.
5. Write the deliverables in house style (build stamp, citations, MP section).
6. Commit (brief message naming the slice, no attribution) and push; intermediate commits at natural checkpoints, each updating the resume note.
7. Update both ledgers; add ripple notes; at a wave boundary write the next wave's plans first; then go to 1.

Guard rails: a slice past twice its estimate is **split** (the remainder
becomes a new catalog entry) rather than delivered thin; a slice needing
something only a human can supply is marked `blocked` with the exact unblocking
action and the loop moves on; never unattended: outward-facing actions,
modifying the game install or the workshop folder (read-only), or two
server+client sessions at once on this PC (it distorts timing measurements).

## Evidence and documentation standard

- **Evidence grades on every claim**: **C** read from code (jar via pzdis,
  Lua, scripts), **M** measured on the live server (run/spike id + results
  path), **W** wiki/community (secondary). A C claim about MP behaviour is
  expected to gain an M in the slice that can measure it. Where C and W
  disagree the doc gets a **Discrepancies** subsection; code wins; the mirror
  preserves the wiki's version.
- **Citation forms**: jar `zombie/inventory/types/Food.getCalories()`; Lua
  `media/lua/client/TimedActions/ISEatFoodAction.lua:123`; scripts
  `media/scripts/items/<file>.txt` + block name; measured: run id + results
  path; wiki: the mirror file (which records the page's own version stamp).
- **System-doc skeleton** (`docs/vanilla/*`, `docs/modding/*`): five-line
  summary → model (formulas as code, thresholds in tables) → code map → **MP
  behaviour** (owning side, sync mechanism, effect of a client-side change,
  witness evidence) → discrepancies → open questions → sources. Header:
  `Verified against: 42.20.4 (b0bbce05d5)` + date. One system per file.
- **Wiki mirrors**: `tools/wiki_mirror.py <Page>` → `references/wiki-mirrors/
  <page>.md` with URL, fetch date, the wiki's page-version stamp, CC BY-NC-SA
  attribution, a short digest, and the wikitext verbatim in a fenced block.
- **Data files**: CSV for humans + JSON for tools, each with a `meta` block
  (build, generated date, tool, source paths, counts); `data/README.md`
  documents every column.
- **Lint**: `tools/doc_lint.py` — build stamp present, no `TODO`/`TBD`,
  non-empty Sources, evidence grades on tables, complete mirror headers. Runs
  in every slice's acceptance and fails the slice.

## Tooling per wave

Base (reused as-is): `pzdis` via `./pz.sh`; the `pzt` package and `PZTestKit`
harness; `tools/mod_inventory.py`.

- **Wave 1**: `tools/wiki_mirror.py`, `tools/doc_lint.py`; harness experiment
  commands `eat <item> [fraction]` (Java `Eat` on a real item, reports the
  nutrition delta vs the item's script values), `nutrition.get` / `nutrition.set`
  (read or set calories/weight/macros), `item.script <type>`; the test layer
  (`TK.test`, `TK.eventually`, assertions, `EveryOneMinute` scheduler, one
  result per test) and `pzt scenario <name>` (boot fixture, attach admin,
  `settimespeed`, trigger over the bus, wait for results, report); `pzt doctor`
  (stray PZ `java.exe`, ports 27261/27015, fixture present and build-matched,
  workshop index reachable — reports, never kills). The 3-day scenario drives
  calories directly (`setCalories` per game-day) to test the weight model in
  isolation; the eating pipeline is verified by the `eat` experiments.
- **Wave 2**: `tools/food_scan.py` (parser for the script block format —
  check `pz-b42` for an existing parser first); harness `items.count` /
  `recipes.count`; `pzt/profile.py` + `testing/profiles/*.toml` + `pzt run
  --profile`; `tools/mod_lint.py` (mod.info in the version folder, id match,
  no `loadstring`).
- **Wave 3**: generic reflective witness — `witness.fields <player|item> <id>
  <getter,…>` and `witness.moddata <keys…>`.
- **Wave 4**: experiment mods under `testing/experiments/<name>/`, installed
  through profiles; test-profile only, never in the fixture.

Constraint: harness Lua changes never need re-provisioning (the fixture
excludes `mods/`); a change to the fixture's mod list or sandbox does.

## Execution and hand-off

- Runs in sessions on this PC, started by the user ("continue the research
  slices"); the memory note points at `docs/progress.md`.
- This session: commit this spec → write wave-1 plans → execute slice 01 and
  continue through wave 1, subagent-driven, for as long as the session lasts.
- Subagent-driven means: the lead session owns the ledgers, the commits and
  the live server; it dispatches one subagent per plan task with the task text
  and the cold-start context, reviews the subagent's output against the
  acceptance checks before moving on, and runs live-server tasks one at a time
  (pure code-reading tasks may run in parallel). Subagents run on Opus; the
  lead thread stays on Fable (user instruction 2026-09-09).
- Compaction/resumption: re-read the plan and the resume note; the cost is at
  most the work since the last checkpoint.
- Visibility: one commit per slice named for it, pushed on completion;
  `docs/progress.md` is the dashboard; `docs/decisions.md` lists every choice.
- **Program done** when all slices are `done`, feasibility notes exist for
  every design area, and `doc_lint` is green across the library — the library
  then answers the questions the mod design will ask (the charter's finish).
