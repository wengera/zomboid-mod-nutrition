# Slice 14 — P5 Feasibility notes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Six notes under `docs/feasibility/`, one per design area the mod will have to decide — each carrying the charter's question for that area, the mechanism **as the research established it**, the risks, a numbered ledger of what is settled (every row citing the slice and the artifact that established it, with the grade it was given *there*), a numbered ledger of what stays open (every row naming the check that settles it), and a recommendation. **Slice 14 mints no evidence**: it measures nothing, boots nothing, grades nothing new. Every claim is a pointer into the library. Slice 14 is the **last** slice, so its final task closes the research program and hands off to the mod-design phase.

**Architecture:** Task 1 audits the inputs (slices 12 and 13 are being planned in parallel and may not have executed), fixes the shared skeleton, and writes the index. Tasks 2–4 write **two notes each, grouped by evidence base**, so one dispatch reads one corpus once: T2 the sync corpus (`mp-sync.md` → `new-nutrients.md`), T3 the dataset/model corpus (`item-pass.md`, `balance-testing.md`), T4 the platform/survey corpus (`ui.md`, `packaging-compat.md`). Task 5 is the cross-reference gate: a throwaway snippet resolves every link, run id and row reference, then `doc_lint`. Task 6 writes the ledgers and the program close — **no push, no board flip**.

**Tech Stack:** Markdown; `tools/doc_lint.py`; Python 3.13 stdlib (one **untracked** check snippet under gitignored `.superpowers/`). No game, no server, no new tracked tooling, no new tests.

**Spec:** `docs/superpowers/specs/2026-09-09-research-slices-design.md` — row 14, § Plans: waves and the template, § Evidence and documentation standard, § Execution and hand-off.

## Global Constraints

- Build **42.20.4 (`b0bbce05d5`)**; grades **C/M/W** on every claim row, **inherited** from the source row and never invented here; brief commits (`Slice 14: …`) without attribution; **pathspec commits** (`git commit -m … -- <paths>`), never `--amend`; take the default at every decision point and log it in `docs/decisions.md`; house doc skeleton (stamp, graded tables, `## Sources`); `cd /c/Users/Angus/repos/project_zomboid` in every shell call (the cwd resets between calls). **No live session in this slice** — it is a documentation slice; the live budget belongs to 12 and 13.

---

## Header

- Slice **14** · Phase **P5** · Status: ready · Verify against **42.20.4 (`b0bbce05d5`)** · Depends on: **all** (01–13) · Unblocks: the mod-design phase · Estimate: 2 h · Tasks: 6.

## Cold-start context

- Repo `C:\Users\Angus\repos\project_zomboid`; charter `STRATEGY.md`; spec above; board `docs/progress.md`; ledger `docs/decisions.md`; map `README.md` (root). Jar toolchain (**not needed here**): `cd C:\Users\Angus\pz-b42 && ./pz.sh grep|methods|refs|dump`.
- **SDD conventions that bind you.** A fresh implementer per task and per fix round; a review after each task with C/M/W as the lens; one live session at a time (this slice opens none); every `~:NN` line cite you copy is **re-located by content** in the current file before you reuse it — line numbers drift. Never quote an *unexecuted plan* as evidence: a plan has no grade.
- **The library at the time of writing (2026-09-11, HEAD `f853d38`).** Slices 01–09 are `done` on the board; **10 and 11 are complete on disk but not yet flipped** (`docs/mods-survey/teardowns/{simplestatus,autocook}.md`, artifacts `td2-20260910-231655`, `td3-20260911-001948`). Cite the docs and artifacts, which exist; do not say "slice 10 is done" — say "landed at `<commit>`". Board flips belong to the controller.
- **Measured baselines to hold.** `python tools/doc_lint.py` (repo-wide) → `0 finding(s)`. `python -m pytest tools/tests testing/tests -q` → `282 passed`. Both re-checked 2026-09-11 at `f853d38`.
- **Lint rules that shape these files** (`tools/doc_lint.py`): `docs/feasibility` is in `STAMPED_DIRS` (`:8`) — every `.md` in it needs `Verified against: 42.20.4` in the text, a non-empty `## Sources`, no placeholder marker anywhere (`PLACEHOLDER_RX` at `:7` — the two banned abbreviations plus `_digest pending_`), and a `C`/`M`/`W` in **every** row of **any** table whose header contains a cell `Ev` (`:57-62`). Two traps: (a) `SKIP_FILES` matches with `rel.endswith(...)` (`:10,39`), so **`docs/feasibility/README.md` is skipped entirely** — the index gets no enforcement and is checked by Task 5's snippet instead; (b) `doc_lint` on a directory that does not exist raises `SystemExit: no such file or directory`, so the dir is created in Task 1 before anything lints it.
- **Evidence conventions you are inheriting** (spec § Citation forms): **C** = jar/Lua/script read, cited as `zombie/inventory/types/Food.getCalories()` or `path/file.lua:123` or `media/scripts/items/<file>.txt` + block; **M** = a run id **and** `testing/artifacts/<run-id>/<file>.json`; **W** = a wiki mirror file or a URL + fetch date. `testing/artifacts/README.md` is the artifact register — it also carries **skew notes** and per-artifact ***do not cite*** tables. A key listed there is not citable: cite the corrected value the block names, or the graded row in the owning doc.
- **The MP facts every note is written against** (`docs/modding/patterns.md` § Measured MP sync facts, plus the three teardowns' § MP handling): the **server** owns `Nutrition`, hunger/thirst, weight, traits, item aging and the Cooking perk, and a client write is overwritten within ~1.5 s by the 1 Hz `PlayerStatsPacket`; `player:transmitModData()` sends the **whole table** and the receiver **wipes and replaces** (M, `td2-20260910-231655`); `ItemStatsPacket` puts **43** fields on the wire of which **39** are item state (`actualWeight` yes; `isCookable`/`offAge`/`offAgeMax`/`lastCookMinute`/`customWeight` no) and reuses cached packets, so a zero-valued field can arrive stale; a cooked food's thirst **halves once per server→client hop** and converges (vanilla defect, `td1-20260910-192457`); the server ticks an inventory item about every **5 s**, and the client's held copy moves **only while `Food.update`'s cooking branch is live** (`heat > 1.6`) — below the gate it is bit-frozen (`td3-20260911-001948`, per-arm M, mechanism C); script-declared item data is **identical on both sides for free**, Lua-written data is only as good as the packet (`patterns.md` KEEP 11).
- **`docs/testing/README.md` § Command bus is a bold bullet at `:64`, not a heading** — several repo docs cite `§ <name>` sections that are bullets. Task 5's section check is a `grep` for the section name, not a heading match.
- **The charter's own gaps, verified 2026-09-11.** `STRATEGY.md` names the three mod pillars at `:9-14` (new nutrients / item pass / MP-first), P5 at `:60-61` ("what the research says is/isn't possible, per future design area. **Reference, not design**" — `:56` is the **P2** wall-map line, not this one), the method rules at `:22-38`, the standing warnings at `:68-74`. It contains **no** occurrence of "UI" or "moodle" (grep) and its pillars table (`:42-49`) has **no `docs/feasibility/` row**. So two of the six notes' questions are **derived**, and each says so in its own text rather than inventing a charter line.

## Questions (the slice is done when each has a cited answer or a named open check)

1. **New nutrients.** Can a mod track vitamin/mineral-class stats beside the vanilla four, where does that state live, and what makes it survive a save, a client, and a server? (`STRATEGY.md:9-11`)
2. **The item pass.** By what mechanism does a mod rebalance the nutrition of 1 005 vanilla food records, what does the mechanism cost on each side of the wire, and what does the corpus show about doing it at scale? (`STRATEGY.md:12`)
3. **UI.** How does a player see a mod-side nutrient — panel, moodle, tooltip, translation — and what does the corpus show about the cost and the neighbours? (derived: spec row 14 + `docs/modding/README.md` § Planned documents)
4. **MP sync.** Which side owns each quantity the mod touches, which wire routes exist for mod state, and which of them are safe? (`STRATEGY.md:13-14`, method rule 2 at `:27-29`)
5. **Balance testing.** What can the shipped pipeline already prove about a balance change, at what cadence, and what must a balance claim carry to be citable? (`STRATEGY.md:48`)
6. **Packaging and compatibility.** What shape does the mod ship in on 42.20.4, what does it have to coexist with on this machine, and what re-verification does the monthly patch cycle force? (derived: ripples from 08 and 09 + `STRATEGY.md:68-74`)
7. **Program close.** Are the spec's three done-conditions met, and what does the mod-design phase read first?

## The shared skeleton (every note copies this, in this order)

```markdown
# Feasibility — <Area>

**Verified against: 42.20.4 (`b0bbce05d5`)** — written <DATE>, slice 14 (P5).
**Reference, not design** (`STRATEGY.md:60-61`): this note says what the research established,
not what the mod should be.

**The question.** <The charter's own words with their cite — or, where the area has no charter
line, one sentence saying the question is DERIVED and from where.> This note answers:
**Q1** … **Qn** <numbered sub-questions, one line each>.

## Mechanism

<How it would work on this build, as the research established it: prose, plus a short table where
it makes claims. This section states no ungraded fact of its own — every load-bearing sentence
ends in an S-row or O-row reference (`S3`, `O2`, or `mp-sync.md S4` across notes).>

## Risks

<One bullet per risk: the failure mode, the row it rests on, and what a design would have to do
about it. At least one MP risk, or an explicit sentence saying why this area has no MP surface
(STRATEGY method rule 2). Name the failure the library actually observed, not a hypothetical.>

## What the research settled

| # | Claim | Established by | Ev |
|---|---|---|---|
| S1 | <one sentence, with its numbers> | slice NN · [`doc`](../x/y.md) § Section · `run-id` | M |

## What stays open

| # | Open question | The check that settles it | Recorded in |
|---|---|---|---|
| O1 | <the question> | <the concrete read or experiment, with the command or the probe> | <doc § Open questions N / slice NN (open)> |

## Recommendation

<3–8 bullets. What the design can rely on, what it must not do, what it must decide. Every bullet
cites an S- or O-row. No new claims; a recommendation is a reading of rows, not a finding.>

## Sources

<Docs, artifacts, datasets, jar/Lua/script citations this note rests on, by path.>
```

**Rules that come with the skeleton.** (1) **Grades are inherited.** An `M` row carries the source's run id; a `C` row carries the source's `path:line`/jar member/script block; a `W` row carries the mirror or URL + fetch date. If a source states a claim without a grade, either grade it as that doc's own section does or leave the claim out. (2) **A claim lives once.** MP facts live in `mp-sync.md`; other notes cite `mp-sync.md S<n>` instead of restating. (3) **Size.** 120–220 lines per note. A note *digests*; it never restates a teardown. Overflow goes back to the source doc as a citation, not into the note. (4) **The open table must not have a header cell `Ev`** — `doc_lint` would demand a grade on rows that by definition have none. (5) **Never write a placeholder marker** — anything `PLACEHOLDER_RX` (`tools/doc_lint.py:7`) matches — even inside a quote.

## Area → question → evidence base (fixed; do not re-derive)

| Note | Question source | Primary evidence base |
|---|---|---|
| `mp-sync.md` | `STRATEGY.md:13-14`, method rule 2 | `docs/modding/patterns.md`; `docs/vanilla/*` § MP behaviour; the three teardowns' § MP handling; `docs/testing/spikes.md` S6; slice 13 `wall-map.md` (sync rows) |
| `new-nutrients.md` | `STRATEGY.md:9-11` | `patterns.md` KEEP 1/2/3/11 + FILTER 1/10; `td2`/`exp08` modData evidence; `docs/vanilla/nutrition-core.md`; slice 12 `lua-api.md` + experiment (b); slice 13 `wall-map.md` (new nutrient fields) |
| `item-pass.md` | `STRATEGY.md:12` | `data/{food-items,recipes,evolved-recipes}.*` + `data/README.md`; `docs/vanilla/{food-item-model,food-dataset-notes,recipes-dataset-notes}.md`; slice 12 `item-overrides.md` + experiment (a); catalog § Open questions 8 |
| `balance-testing.md` | `STRATEGY.md:48` | `docs/testing/{README,profiles,pipeline-design,spikes}.md`; `testing/artifacts/README.md`; `docs/vanilla/nutrition-core.md` § Verified on server; `body-stats.md` |
| `ui.md` | derived (spec row 14; `docs/modding/README.md` § Planned documents) | `teardowns/simplestatus.md`; `patterns.md` FILTER 8; `docs/vanilla/body-stats.md` (moodles); catalog (MoodleFramework, CleanUI); slice 12 `lua-api.md`; slice 13 `wall-map.md` (moodles, translations) |
| `packaging-compat.md` | derived (ripples 08/09; `STRATEGY.md:68-74`) | `teardowns/autocook.md` § Architecture (the merge rule); `docs/modding/README.md`; `tools/mod_lint.py` rules; `data/mod-inventory.json`; `data/workshop-search.*`; slice 12 `anatomy.md` |

## Method

### Task 1: Input audit, skeleton, index

**Files:** Create `docs/feasibility/README.md`, `.superpowers/sdd/14-feasibility/input-audit.md`; Modify `README.md` (root).

- [ ] **Step 1: Audit the wave-4 inputs.** Slices 12 and 13 are being planned in parallel; their deliverables may or may not exist.

```bash
cd /c/Users/Angus/repos/project_zomboid
for f in docs/modding/anatomy.md docs/modding/lua-api.md docs/modding/item-overrides.md \
         docs/modding/wall-map.md; do
  if [ -f "$f" ]; then echo "PRESENT $f  $(git log -1 --format='%h %ad' --date=short -- "$f")";
  else echo "ABSENT  $f"; fi; done
ls -1 testing/experiments/ testing/profiles/ testing/artifacts/
ls -1 testing/artifacts/ | grep -i '^x12'    # slice 12's experiment artifacts, if it ran
git log --oneline -12
```

  Write `.superpowers/sdd/14-feasibility/input-audit.md`: per expected file PRESENT/ABSENT, and for each PRESENT one its `Verified against:` stamp line and its `##` headings (`grep -n '^#\{1,3\} '`). **The rule, and it is not negotiable:** an ABSENT input never becomes a guess. Every claim that would have rested on it becomes an **O-row** reading `slice 12 (open) — plan docs/superpowers/plans/12-platform-reference.md § <task>` (same for 13), with the check that settles it named. A PRESENT input whose stamp is not 42.20.4 is cited **and** flagged as a risk row. A PRESENT input that simply does not contain the claim is also an O-row — do not infer from a neighbouring section. And when `wall-map.md` is present, its verdicts are **consumed, not re-derived**: a `CANNOT` / `CAN` / `CAN WITH A WORKAROUND` row becomes an S-row citing the map (grade inherited), while its fourth class, **`UNKNOWN`**, becomes an **O-row** carrying the map's own named experiment as the check.

  **Read `.superpowers/sdd/wave-4/not-settled.md` as part of this audit, and record it in the audit file.** It is the slice-11 whole-pass review's list of what waves 1–3 did **not** establish, and it outranks a cheerful sentence in any doc: the merge rule bounded to a version dir that ships colliding files (n = 1); MoodleFramework "whole on 42.20.4" as **C derived** from that rule with nothing booted; the carrier as M *per arm* (n = 1 each, one item, one 12.54 s window, one fixture — "`Food.update` did not advance the client copy in this window", never "client copies cannot tick"); `mod.info` resolution order open; `common/` inertness bounded to the window-build path; the `allowSpice` weight-flag agreement holding only in the trivial arm; CleanUI's runtime half C-inferred with the collision live; the cooking pipeline C; the transmit **WIPE** half a single pass-2 reading. **Every one of these is an O-row in whichever note owns it unless slice 12 or 13 settled it** — and the audit says, per item, which slice settled it and with which artifact, or that it stays open. An S-row that swallows one of these bounds is the one way this slice can mint evidence it was told not to mint.
- [ ] **Step 2: Create the directory and prove the lint path.** `mkdir -p docs/feasibility && python tools/doc_lint.py docs/feasibility` → Expected `0 finding(s)` on an empty dir (and, before the `mkdir`, `SystemExit: no such file or directory` — that is the trap this step retires).
- [ ] **Step 3: Write `docs/feasibility/README.md`** — the index. It is **not** linted (`SKIP_FILES`), so write the house furniture by hand: title; `**Verified against: 42.20.4 (`b0bbce05d5`)**` + date; one paragraph saying what a feasibility note is and is not (`STRATEGY.md:60-61`); then
  - **§ Start here** — the reading order for the mod-design phase (Task 6 finalises it): `STRATEGY.md` → `docs/modding/wall-map.md` (or, while it is open, `docs/modding/patterns.md`) → `mp-sync.md` → the five remaining notes → `data/README.md` → `docs/testing/README.md`.
  - **§ The notes** — a table `Area | Note | The question (with its cite) | Status`, `Status ∈ {answered, partly open, open}`, one row per note, filled as Tasks 2–4 land.
  - **§ How to read a note** — the skeleton's section order, the `S<n>`/`O<n>` row ids, the cross-note form `<note>.md S<n>`, and "grades are inherited; slice 14 measured nothing".
  - **§ Coverage** — the spec row-14 areas (new nutrients, item pass, UI, MP sync, balance testing) each mapped to their note, plus the sixth note and the one-line reason it exists (the 08/09 ripples asked slice 14 for a compatibility constraint and a Workshop-neighbour note, and no other note owns mod anatomy).
  - **§ Sources**.
- [ ] **Step 4: Make it reachable.** Add one row to the root `README.md` § Map, after the `docs/mods-survey/` row: `| [docs/feasibility/](docs/feasibility/README.md) | What the research says is and is not possible, per design area (P5) |`.
- [ ] **Step 5: Commit** — `git commit -m "Slice 14: feasibility index and skeleton" -- docs/feasibility/README.md README.md`.

### Task 2: The sync corpus — `mp-sync.md`, then `new-nutrients.md`

**Files:** Create `docs/feasibility/mp-sync.md`, `docs/feasibility/new-nutrients.md`.

- [ ] **Step 1: Read the corpus once.** `docs/modding/patterns.md` whole (KEEP 1/2/3/11, FILTER 1/9/10/11, § Measured MP sync facts incl. *The other direction*, § Open pattern questions); the § MP behaviour / § MP handling sections of `docs/vanilla/{eating-pipeline,food-item-model,body-stats,nutrition-core}.md` and `docs/mods-survey/teardowns/{longtermpreservation4220,simplestatus,autocook}.md`; `docs/testing/spikes.md` § S6; and whichever of `docs/modding/{lua-api,wall-map}.md` the audit found.
- [ ] **Step 2: Write `mp-sync.md` first** — it is the hub every other note cites. Its S-rows must cover, at minimum: server ownership per quantity (`Nutrition`, hunger/thirst, weight, traits, item aging, Cooking perk) and the 1 Hz overwrite; the three routes mod state can travel (`sendClientCommand`/`sendServerCommand` — `patterns.md` KEEP 2; `transmitModData()` whole-table wipe-and-replace — M `td2-20260910-231655`; `ItemStatsPacket`'s 43/39 field contract with its cached-packet zero leak and its per-arm client-copy behaviour — M `td1-…`/`td3-…`); the cooked-thirst halving per hop; script data identical on both sides for free (M `td1-20260910-192457`); the server's player modData being **empty at join** and gaining four vanilla fitness keys ~30 s in; the item-modData census exclusions (`customName`, `Tooltip`) and that exclusion sets are **per scope**. § Risks must carry the measurement discipline as a risk to the *design's own* telemetry: a client-side reader sees a staircase, so a cross-side comparison needs client-first reads and driver-side wall brackets (slice 10) — a design that "checks sync" without them measures its own read order. § What stays open takes the unresolved rows verbatim from `patterns.md` § Open pattern questions and the teardowns.
- [ ] **Step 3: Write `new-nutrients.md`** citing `mp-sync.md` S-rows rather than repeating them. Its own S-rows are about *storage and effect*: `Nutrition` is a Java class — paralleled, never extended (`docs/modding/README.md` § Hard-won platform facts; wall-map entry if 13 landed, else O-row); modData is the only durable mod state (`patterns.md` KEEP 1) and `OnInitGlobalModData` the sanctioned world-scoped store (KEEP 3); the vanilla stores clamp (calories `[-2200, 3700]`, macros `[-500, 1000]`, slice 01, measured) so a parallel store inherits no clamping and must define its own; **protein has no live vanilla effect at all** and the deficit penalties below −1000/−1500 are dead code behind the −500 clamp (slice 03) — a new nutrient with no consumer is a number, so the note must say where an effect path could attach (moodles → `ui.md`; the weight model → `item-pass.md`/`balance-testing.md`). § Risks leads with FILTER 10: never keep server-authoritative state in player modData on a server whose clients also transmit — **the mod that loses the data is not the mod that transmitted it**. If slice 12's experiment (b) (a mod-side new-nutrient field on item + player modData with its sync measured) has landed, its artifact is this note's central M row; if not, that is O-row #1 and the note says the mechanism is **unproven on this build**.
- [ ] **Step 4: Self-check** — `python tools/doc_lint.py docs/feasibility` → `0 finding(s)`; `wc -l docs/feasibility/*.md` → each note 120–220 lines.
- [ ] **Step 5: Commit** — `git commit -m "Slice 14: MP-sync and new-nutrient feasibility notes" -- docs/feasibility/mp-sync.md docs/feasibility/new-nutrients.md`.

### Task 3: The dataset and model corpus — `item-pass.md`, `balance-testing.md`

**Files:** Create `docs/feasibility/item-pass.md`, `docs/feasibility/balance-testing.md`.

- [ ] **Step 1: Read the corpus once.** `data/README.md` § food-items / § recipes / § evolved-recipes (incl. § Per litre, not per item); `docs/vanilla/{food-item-model,food-dataset-notes,recipes-dataset-notes,nutrition-core,body-stats}.md`; `docs/testing/{README,profiles,pipeline-design}.md`; `testing/artifacts/README.md` (**read the *do not cite* tables before citing any scenario key**); `docs/mods-survey/nutrition-mods.md` § Open questions 8; and `docs/modding/item-overrides.md` if the audit found it. Confirm the dataset shape yourself rather than trusting this plan:

```bash
cd /c/Users/Angus/repos/project_zomboid && python -c "import json; d=json.load(open('data/food-items.json',encoding='utf-8')); print(d['meta']['counts']); print(len(d['items']),'item records')"
```

  Expected at 2026-09-11: `{'food': 722, 'drainable': 150, 'fluid_container': 133, 'fluids': 61, …}` and `1005 item records`. A different number is the current truth — quote it and date it.
- [ ] **Step 2: Write `item-pass.md`.** Mechanism: the four ways a mod can change a vanilla item's nutrition (`module Base` re-declaration / per-item script override / an `OnEat`/`OnCooked`-class Lua hook / modData), each pointing at slice 12's `item-overrides.md` row — and where 12 is open, at O-rows naming its experiment (a) (an override mod changing `Base.Apple`'s calories, witnessed on both sides). S-rows: script-declared data is correct on both sides for free while Lua-written data is only as good as the packet (KEEP 11, M `td1-…`); cooking moves no nutrition — only a **type change** does (slice 06, from the data); an evolved recipe banks `macro × (1 + cookLvl/15) × share`, i.e. ~17 % of calories created at Cooking 10 (slice 02) — an item pass that ignores it is rebalancing the wrong quantity; rot is a **view, not a mutation** (slice 02); the corpus contains **no precedent** for re-declaring vanilla `module Base` foods at scale — one name collision across the nine script-signal mods (catalog § Open questions 8), so the mechanism is a wall-map/experiment question, not a folklore one; mod-added foods (LTP's 14 `module Skittles` items) fall **outside** a `module Base`-scoped pass and the design must say whether they are in or out (ripple from 09). § Risks: the dataset's own unit traps (`food-dataset-notes.md` § Open questions 4), absent-vs-zero, per-litre fluids, pick-random rows, the 37 unresolved `ReplaceOn*` links, and the display-name dependency — `getActualWeightUnmodded()` returns **0** when `getDisplayName() == getFullType()`, which is what an item missing from `ItemName.json` reads (M `td1b`/`td2`), so a new or renamed item needs its translation entry or the server itself holds a wrong value.
- [ ] **Step 3: Write `balance-testing.md`.** Mechanism: the shipped pipeline as the instrument — L0 `mod_lint` → profiles (`testing/profiles/<name>.toml`: `fixture`, `[[mods]]` by **engine-resolved id**, `[sandbox]` merged, `[[verify]]` bus probes) → `pzt run --profile` → scenarios (`pzt scenario`, the `TK.test` layer) → the command bus → artifacts committed byte-identical with a `testing/artifacts/README.md` row. S-rows: the decoded weight model is verified live to **sub-gram** accuracy over three game-days (slice 04, `scenario-20260910-05{4012,5029}`) so a balance change can be *predicted* and then checked; the 3 700 calorie clamp discards 4 790 of 12 000 kcal at two +2 000 doses/day — **intake pacing is itself a balance lever** (ripple from 04); `DayLength = 4` is **90 real minutes per game day** and the cadence ceiling is `24 × speed / day_minutes ≲ 8`; **THIRST level 4 drains health at 5× the hunger rate**, so any scenario past ~29 game-hours manages thirst or the subject dies (slice 04's first run did); `setCalories` is not food; the server ticks an item ~every 5 s so a bus call cannot be made the cause of a server-side item transition. § Risks: measuring the mirror instead of the mechanism; a fixture re-provision is needed when the mod list or sandbox changes while harness Lua changes are free; one live session at a time on this machine. § Recommendation ends on the rule the program has been running on: **every balance number carries a run id**, and a claim without one is C at best.
- [ ] **Step 4: Self-check and commit** — `python tools/doc_lint.py docs/feasibility` → `0 finding(s)`; `git commit -m "Slice 14: item-pass and balance-testing feasibility notes" -- docs/feasibility/item-pass.md docs/feasibility/balance-testing.md`.

### Task 4: The platform and survey corpus — `ui.md`, `packaging-compat.md`

**Files:** Create `docs/feasibility/ui.md`, `docs/feasibility/packaging-compat.md`.

- [ ] **Step 1: Read the corpus once.** `docs/mods-survey/teardowns/{simplestatus,autocook,longtermpreservation4220,beyondten,itemquality}.md`; `docs/mods-survey/{nutrition-mods,approved-modlist}.md`; `docs/modding/{README,patterns}.md`; `docs/vanilla/body-stats.md` (moodle thresholds) and `nutrition-core.md` (the Nutritionist trait is display-only); `data/mod-inventory.json` + `data/workshop-search.*` + `data/workshop-catalog-details.json`; `tools/mod_lint.py`'s rule list; and whichever of `docs/modding/{anatomy,lua-api,wall-map}.md` the audit found.
- [ ] **Step 2: Write `ui.md`.** State in the first paragraph that the question is **derived** — `STRATEGY.md` names no UI requirement (grep, 2026-09-11); the question comes from the spec's row-14 list and `docs/modding/README.md` § Planned documents (`parallel-stats.md`: "UI (moodles — evaluate Moodle Framework vs own)"). Mechanism: the three surfaces a mod-side nutrient can use — an `ISPanel`-class client panel (simpleStatus is the worked example), a moodle (vanilla moodle thresholds are jar-side per `body-stats.md`; MoodleFramework is installed and **whole on 42.20.4**, closed slice 11), and tooltip/translation text (`Translator` **merges** mod translation JSONs — M, slice 11; `text.get` on the harness proves a mod's table loaded). S-rows: the client's copy of the macros is a **1 Hz staircase** of a server value (cite `mp-sync.md`); a per-frame uncached read of a server-owned store is the corpus's headline anti-pattern — `SSBar:prerender` issues up to **four** `getNutrition()` round trips per bar per frame against a 1 Hz source (M/C, slice 10) — so **cache on the push, not on the frame**; a displayed thirst number may be **half** the one the server applied (`td1`), i.e. a UI can be honest and still wrong; CleanUI redraws status surfaces and simpleStatus renders the same six numbers the mod will change (compatibility, not dependency).
- [ ] **Step 3: Write `packaging-compat.md`.** Mechanism: the B42 mod shape — version dirs + `common/`, with the merge rule **measured** (the version dir wins a same-relative-path collision; `common/` supplies what the version dir does not ship; translations are merged rather than resolved; M `td3-20260911-001948`, mechanism C, bounded to one mod/one build), the declared id vs the folder name (**52 of 230** corpus rows drift; `Mods=` takes the declared id), `Mods=` order is load order, `require` resolves through the same map, and `mod_lint`'s layout rules. S-rows for the breakage seeds: `loadstring` **removed** in 42.20.x; `HasTrait(String)` and `getTypeString()` **removed** on 42.20.4; `ItemName_EN.txt` in the B41 layout is not loaded (hypothesis (ii) still open → O-row). § Risks: the resident stack (CleanUI's UI surfaces, the Girth mods' 228 command sites, AutoCook's client-side automation, LTP's own foods), one workshop item shipping several mods, and the charter's standing warning that the game patches ~monthly (`STRATEGY.md:68-74`) — every note's stamp is a **shelf life**. W-rows: the two uninstalled Workshop neighbours `3736275816` ("Nutrition Sync Fix" — the closest public thing to this library's own subject) and `3796644824` (a third-party patch to teardown pick 1), each with its unblocking action (subscribe in Steam, let it download, re-run `python tools/mod_inventory.py`).
- [ ] **Step 4: Self-check and commit** — `python tools/doc_lint.py docs/feasibility` → `0 finding(s)`; `git commit -m "Slice 14: UI and packaging feasibility notes" -- docs/feasibility/ui.md docs/feasibility/packaging-compat.md`.

### Task 5: Cross-reference and gates

**Files:** Create `.superpowers/sdd/14-feasibility/xref.py` (**untracked** — `.superpowers/` is gitignored, `.gitignore:49`); Modify the notes as findings require.

- [ ] **Step 1: Write the checker** exactly as below and run it. It resolves links, run ids and row references; `doc_lint` already owns stamps, placeholders and grades.

```python
#!/usr/bin/env python3
"""Slice 14 cross-reference gate: every citation in docs/feasibility resolves."""
import os, re, sys
REPO = r"C:\Users\Angus\repos\project_zomboid"
DOCS = os.path.join(REPO, "docs", "feasibility")
RUN_RX = re.compile(r"\b((?:exp|run|scenario|td|x\d+)\d*[a-z]?-\d{8}-\d{6})\b")  # x\d+ = slice 12
LINK_RX = re.compile(r"\]\(([^)\s]+?)(?:#[^)]*)?\)")
ROW_RX = re.compile(r"^\|\s*([SO]\d+)\s*\|")
XREF_RX = re.compile(r"([a-z-]+\.md)[^A-Za-z0-9]{1,4}([SO]\d+)\b")   # `mp-sync.md` S4
REF_RX = re.compile(r"\b([SO]\d+)\b")
ART_DIR = os.path.join(REPO, "testing", "artifacts")
arts = {d for d in os.listdir(ART_DIR) if os.path.isdir(os.path.join(ART_DIR, d))}  # not README.md
files = sorted(f for f in os.listdir(DOCS) if f.endswith(".md"))
texts = {f: open(os.path.join(DOCS, f), encoding="utf-8").read() for f in files}
ids = {f: {m.group(1) for l in t.splitlines() if (m := ROW_RX.match(l))} for f, t in texts.items()}
bad = []
for f, text in texts.items():
    for rid in sorted(set(RUN_RX.findall(text))):
        if rid not in arts:
            bad.append(f"{f}: run id absent from testing/artifacts/: {rid}")
    for link in sorted(set(LINK_RX.findall(text))):
        if link.startswith(("http", "mailto:")):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(DOCS, link))):
            bad.append(f"{f}: dead link: {link}")
    for other, ref in XREF_RX.findall(text):          # cross-note references
        if ref not in ids.get(other, set()):
            bad.append(f"{f}: {other} has no row {ref}")
    local = REF_RX.findall(XREF_RX.sub(" ", text))    # bare refs, after removing cross-note ones
    for ref in sorted(set(local) - ids[f]):
        bad.append(f"{f}: row id used but not defined: {ref}")
    for n, line in enumerate(text.splitlines(), 1):
        m = ROW_RX.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            bad.append(f"{f}:{n}: row {m.group(1)} has {len(cells)} cells, needs 4"); continue
        claim, est, last = cells[1], " ".join(cells[2:-1]), cells[-1]   # extra '|' tolerated
        if not claim or not est or not last:
            bad.append(f"{f}:{n}: row {m.group(1)} has an empty cell")
        if m.group(1).startswith("S"):
            if not re.search(r"\b[CMW]\b", last):
                bad.append(f"{f}:{n}: S-row without a C/M/W grade")
            if re.search(r"\bM\b", last) and not RUN_RX.search(est):
                bad.append(f"{f}:{n}: M row with no run id in 'Established by'")
            if not re.search(r"\]\(|`", est):
                bad.append(f"{f}:{n}: 'Established by' names no path, link or artifact")
for b in bad:
    print(b)
print(f"{len(bad)} finding(s)")
sys.exit(1 if bad else 0)
```

  Two details in it are load-bearing and were got wrong once already. **`RUN_RX` carries `x\d+`** because slice 12's artifacts are `x121-`/`x122-`/`x123-<stamp>` — without that arm every S-row citing a slice-12 run is invisible to the run-id check *and* trips the `M row with no run id in 'Established by'` rule, which Step 1's "fix the notes, never the checker" would then send you to break a correct citation over. And **`arts` is filtered to directories**, because `testing/artifacts/` also holds `README.md` and a bare `listdir` would let a note "cite" it.

  Run: `cd /c/Users/Angus/repos/project_zomboid && python .superpowers/sdd/14-feasibility/xref.py` → Expected `0 finding(s)`, exit 0. Fix the **notes**, never the checker, unless the checker is wrong about the repo (if it is, fix it and say so in the task report).
- [ ] **Step 2: The three checks the snippet cannot make.** (a) For every `§ <Section>` citation, `grep -n "<Section>" <the cited file>` and confirm it exists — some sections are bold bullets, not headings (`docs/testing/README.md` § Command bus is `:64`). (b) For every artifact cited, open its block in `testing/artifacts/README.md` and confirm the **key** you cite is not in that block's ***do not cite*** table (the scenario corpse readings and `exp03`'s movement ratios are the traps). (c) For every "slice NN" named, confirm the deliverable exists on disk or the row is explicitly an open one.
- [ ] **Step 3: Gates** — `python tools/doc_lint.py docs/feasibility` → `0 finding(s)`; `python tools/doc_lint.py` (repo-wide) → `0 finding(s)` (the baseline at `f853d38`); `python -m pytest tools/tests testing/tests -q` → `282 passed` (no code changed; this is a no-regression check).
- [ ] **Step 4: Coverage check** — every area in the spec's row 14 (new nutrients, item pass, UI, MP sync, balance testing) has a note; every note has a row in `docs/feasibility/README.md` § The notes with its status; every one of this plan's Questions 1–6 is answered in its note or carries an O-row. `ls -1 docs/feasibility/` → 7 files.
- [ ] **Step 5: Commit** — `git commit -m "Slice 14: cross-reference fixes" -- docs/feasibility` (skip if nothing changed; the snippet is untracked).

### Task 6: Ledgers and the program close

**Files:** Modify `docs/progress.md`, `docs/decisions.md`, `testing/artifacts/README.md`, `docs/feasibility/README.md`.

- [ ] **Step 1: Artifact register.** For each artifact a note actually cites, append the citing note to that row's **Cited by** cell in `testing/artifacts/README.md` (e.g. `…; slice 14 [`docs/feasibility/mp-sync.md`](../../docs/feasibility/mp-sync.md)`). Only rows actually cited; do not touch the rest.
- [ ] **Step 2: `docs/decisions.md`** — one row per default taken, at minimum: the six-note split and why a sixth exists; the `S<n>`/`O<n>` row-id convention; **grades are inherited, slice 14 mints none**; no live session in slice 14; the cross-reference checker stays an untracked snippet rather than tracked tooling (tracked tooling needs tests under `tools/tests/`, and this is a one-slice check); `doc_lint.SKIP_FILES` left alone even though it exempts the index (same ruling slices 07/08 took for `STAMPED_DIRS`); `STRATEGY.md` **not** edited to add a `docs/feasibility/` pillar row (the charter changes deliberately — record it as a deferred edit for the human); plus every decision-point default this run actually took.
- [ ] **Step 3: `docs/progress.md`** — under row 14, a **resume note**: what landed, the commits, which of slices 12/13 were present at write time and which claims are consequently open. Then a **Ripples** block — but these ripples have no later slice to change, so they are addressed to the **mod-design phase** and each names the note that carries them. Finally a new `## Program close` section stating the spec's three done-conditions (§ Execution and hand-off) and their status: (i) all slices `done` — **rows 10–14 are the controller's flip**, say which are still open on the board and that their deliverables are on disk with their commits; (ii) feasibility notes exist for every design area — list the six with their commits; (iii) `doc_lint` green across the library — quote the repo-wide run and its date. Then one sentence handing off: the mod-design phase starts at `docs/feasibility/README.md` § Start here.
- [ ] **Step 4: Finalise the index.** Fill `docs/feasibility/README.md` § The notes statuses from what the notes actually say (`answered` only where no O-row blocks the question), and § Start here with the reading order as it really landed.
- [ ] **Step 5: Commit — and stop.** `git commit -m "Slice 14: ledgers and program close" -- docs/progress.md docs/decisions.md testing/artifacts/README.md docs/feasibility/README.md`. **No `git push`. Do not flip any board row to `done`** — not 14's, not 12's or 13's. The row stays `in progress` with the resume note until the whole-branch review has run; the controller flips it, pushes, and closes the program.

## Deliverables

- `docs/feasibility/README.md` (index: Start here, The notes, How to read a note, Coverage, Sources)
- `docs/feasibility/{mp-sync,new-nutrients,item-pass,balance-testing,ui,packaging-compat}.md` — stamped, graded, S/O row ledgers, `## Sources`
- Updates: root `README.md` § Map row; `testing/artifacts/README.md` Cited-by cells; `docs/progress.md` (resume note, ripples, § Program close); `docs/decisions.md` rows
- `.superpowers/sdd/14-feasibility/{input-audit.md,xref.py}` (working files, untracked)

## Acceptance checks

1. `python tools/doc_lint.py docs/feasibility` → `0 finding(s)`; `python tools/doc_lint.py` (repo-wide) → `0 finding(s)`.
2. `python .superpowers/sdd/14-feasibility/xref.py` → `0 finding(s)`, exit 0.
3. `ls -1 docs/feasibility/` → **7** files; `wc -l docs/feasibility/*.md` → every note 120–220 lines.
4. Every note has all seven skeleton sections in order, a non-empty `## What the research settled` with at least one **M** row carrying a run id, and a non-empty `## What stays open` with the check named in each row.
5. Every spec row-14 design area maps to a note in `docs/feasibility/README.md` § Coverage, and each of this plan's Questions 1–7 is answered in its note or carried as an O-row.
6. No note cites a key listed under a ***do not cite*** block in `testing/artifacts/README.md`, and no note quotes an unexecuted plan as evidence (`grep -n "superpowers/plans" docs/feasibility/*.md` → only O-rows and only as "slice NN (open)").
7. `python -m pytest tools/tests testing/tests -q` → `282 passed` (no regression; slice 14 ships no code).

## Expected decision points (defaults)

- **Slice 12 and/or 13 has not executed** → cite the slice as **open**: an O-row naming the plan file and the check that settles it; the note says the mechanism is unproven on this build. Never guess from the plan text, never grade a plan. Log once.
- **A slice-12/13 doc exists but contradicts an earlier finding** → the **measured, later** doc wins; record the contradiction in the note's § Risks and add a `docs/decisions.md` row. Do not silently pick a side, and do not edit the older doc (it belongs to its slice).
- **The board shows 10–13 not `done` while their deliverables are on disk** → cite the doc and the artifact, and say "landed at `<commit>`" rather than "slice done". Board flips are the controller's.
- **A note needs a measurement nobody took** → slice 14 opens **no** live session. It becomes an O-row with the concrete probe (which command on which side, what would separate the arms). Default: never boot.
- **A cited artifact key is in a *do not cite* block** → cite the corrected value that block names, or drop to the graded row in the owning doc; never the raw key.
- **A note runs past ~220 lines** → push the detail back to the source doc and cite it. If the source doc has no such section, that is an O-row, not a reason to grow the note. Never deliver a thin note silently either: a slice past twice its estimate is **split** into a new catalog entry.
- **An area has no charter line** (UI, packaging) → say so in the note's first paragraph, name where the question was derived from, and never invent a charter requirement. Same posture if a seventh area suggests itself: fold it into the nearest of the six unless the charter names it.
- **A Workshop row (not installed)** → stays **W** with its unblocking action; it is never a mechanism and never a recommendation.
- **Two notes want the same claim** → it lives once in the owning note (MP facts in `mp-sync.md`) and the other cites `mp-sync.md S<n>`.
- **`doc_lint` reports a finding outside `docs/feasibility`** → fix only what slice 14 wrote; record anything else and leave it to the slice that owns those docs (the slice-01 ruling).
- **The xref snippet disagrees with the repo** (a legitimate citation form it does not know) → fix the snippet, say so in the task report and in `docs/decisions.md`; do not weaken a citation to satisfy a checker.

## Done protocol

- `docs/progress.md`: row 14 stays **`in progress`** with a resume note (what landed, the commits, which wave-4 inputs were present); **ripples addressed to the mod-design phase**, each naming the note that carries it; and a new `## Program close` section with the spec's three done-conditions, their status, and the hand-off sentence.
- `docs/decisions.md`: the rows from Task 6 Step 2 plus every default this run took.
- `testing/artifacts/README.md`: the Cited-by cells of the artifacts the notes actually cite.
- Root `README.md`: the `docs/feasibility/` Map row (Task 1).
- Commits, subject line only, no attribution, pathspec form. **The slice does not push and does not flip a board row.** The controller runs the whole-branch review, flips rows 12/13/14, pushes, and declares the research program closed — after which the mod-design phase is a separate effort that starts at `docs/feasibility/README.md` § Start here.
