# Reference restructure — design spec

Date 2026-09-17 · Status: draft for review · Author: the controller session, from a brainstorm with Angus.

## Goal

Turn the research library into an **agent-facing development reference** for Project Zomboid Build 42 modding, with the nutrition mod as its first consumer: a canonical markdown tree an agent reads on demand, plus thin **project-scoped skills** that route a task to the right pages. Remove the process history ("how we got there") from the tree while keeping every established claim with its evidence pointer. Keep the **general** PZ modding knowledge (platform, loader, Lua, MP, harness, jar research) first-class and nutrition-agnostic, so a tangential mod capability does not have to be relearned.

## Non-goals

- No new measurements. The restructure mints no evidence; every claim in the new tree is a harvested claim from the current library with its grade and pointer.
- No mod design. The areas layer says what the research established, not what the mod should be (the charter's "reference, not design" rule stands).
- No change to the harness, runner, datasets, probe mods or artifacts beyond one generator and one checker.
- No rewrite of the wiki mirrors or the wall map's verdict table (they move as-is).

## Decisions taken in the brainstorm

1. Consumer model: a canonical markdown tree **plus** project-scoped skills (`.claude/skills/`) that route into it. Skills never duplicate a page; they quote its `## Rules` and point at it.
2. Slice 14 (feasibility notes) is **folded into** this restructure: its six design areas become the `docs/areas/` top layer, written once in the new contract. The research program closes at the tag; no separate program-close ceremony.
3. Process history is **deleted from the tree**; git keeps it under the tag `research-program-v1`. No `archive/` directory.
4. Tree shape: **three layers** — `areas/` (the nutrition lens), `platform/` (general PZ B42 modding knowledge), `facts/` (measured game mechanics by mechanism) — over a `reference/` layer (generated harness commands, datasets, artifacts register, the wall map).
5. Evidence: every claim keeps its grade and pointer, in a **compact tag** that resolves to a row in a claims register; bounds live in the register and are stated as facts in prose where they matter.
6. Tooling docs are first-class: "testing your mod" is an area page; the harness command reference is **generated from the Lua** so it cannot trail the code.
7. Execution is **register-first**: harvest every graded claim into a machine-checkable register, write the pages from the register, prove coverage with a checker, then delete the old tree.

## The target tree

```
README.md                    the map: what the repo is, the reading order, the tag grammar, the tree
CLAUDE.md                    agent operating rules for this repo (process, gotchas, standing rules)
STRATEGY.md                  the charter, trimmed of program history
docs/
  areas/                     the nutrition lens — one page per design question, skill-backed
    new-nutrients.md         where a mod nutrient can live, sync, persist, act
    item-pass.md             overriding vanilla foods: script merge rules, load order, the dataset
    eat-and-cook-hooks.md    OnEat / complete wrappers / OnCooked: sides, order, limits
    mp-sync.md               who owns what, the wire routes, the hazards (the hub the others cite)
    ui-and-moodles.md        panels, moodles (the walls), translations, display names
    packaging.md             mod anatomy for THIS mod, the checksum gate, the resident stack, compat
    testing-your-mod.md      profile -> scenario -> driver -> evidence; the harness in one page
    open-questions.md        the named experiments + every area's open rows, with owners and costs
  platform/                  GENERAL PZ B42 modding knowledge — nutrition-agnostic
    overview.md              the two Lua states, server authority, events and timed actions, the
                             script DSL, the packet model, save/load — the engine's shape
    mod-anatomy.md           mod.info, version dirs, common/, the merge rule, load order, the id
                             chain, the checksum gate, translations, require
    lua-platform.md          Kahlua's limits and behaviours (pcall, raises, the debug break, removed
                             APIs, Java-member access), the events actually exercised
    mp-model.md              ownership per quantity, the wire routes, wipe-and-replace, packet field
                             contracts, what a client copy is and is not
    loader-and-scripts.md    the script bucket, per-key merge, sorted replay, path collisions
    lessons.md               general lessons as RULES with tags: sync mistakes, Kahlua traps, testing
                             discipline, corpus drift, "measure the mechanism, not the mirror"
    jar-research.md          answering a question from the jar: pz.sh grep/methods/refs/dump,
                             offsets, the exposer list, what "exposed" means
  facts/                     game mechanics as measured or read, by mechanism
    eating-pipeline.md  food-item-model.md  body-and-weight.md  nutrition-core.md  wire-packets.md
    other-mods.md            what the catalog and the three teardowns established: one fact sheet
                             per mod (what it does, techniques worth stealing, pitfalls), no story
  reference/
    harness-commands.md      GENERATED by tools/bus_inventory.py from every TK.register(...)
    datasets.md              data/* schemas and counts, dated
    artifacts.md             run id -> file -> what it measured -> do-not-cite keys (trimmed)
    wall-map.md              the 64-row verdict table (moved as-is)
    claims.csv               the claims register (a deliverable, see below)
.claude/skills/
  pz-modding-platform/       fires on ANY PZ modding task -> docs/platform/*
  pz-jar-research/           fires when a question needs the jar -> platform/jar-research.md
  pz-mod-testing/            fires when a mod needs a live test -> areas/testing-your-mod.md
  nutrition-<area>/          one skill per areas/ page (seven), nutrition-specific
data/  tools/  testing/  references/wiki-mirrors/    unchanged; a short README each; outside the skills
```

**Placement rule.** A mechanism goes in `platform/` if it would hold for a weapon mod or a UI mod; in `facts/` if it is a measured property of the food, body or nutrition systems; in `areas/` only as a nutrition-design reading of the two layers below. A fact lives on one page; other pages link.

**Deleted from the tree at the cut** (kept under the tag): `docs/superpowers/` (plans, specs, notes — this spec included), `docs/progress.md`, `docs/decisions.md`, `docs/references.md` (folded into the README), and the current `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing` once every claim they carry has landed.

## The claims register

`docs/reference/claims.csv`, tracked, one row per graded claim harvested from the current library.

| column | content |
|---|---|
| `id` | stable, `C0001`… (never reused) |
| `claim` | one sentence, numbers included |
| `grade` | `C` / `M` / `W` |
| `pointer` | jar site `Class.method @off L<n>`; or `<run-id> <json.key.path>`; or mirror file + fetch date |
| `bound` | shorthand: `n=1`, `server VM only`, `dedicated-server path`, `one fixture`, `42.20.4`, … or empty |
| `status` | `settled` / `open` / `superseded` (a superseded row keeps its id and names its successor) |
| `source` | the old doc and section the row came from (several, `;`-separated, when duplicated) |
| `target` | the new page and anchor the claim belongs to (`platform/lua-platform.md#pcall`) |

**Harvest rules.** Every row of every `Ev` table; every KEEP/FILTER row in `patterns.md`; every measured-fact bullet; every wall-map row (verdict rows become claims about capability; `UNKNOWN` rows become `open`); every bound on the not-settled lists (`.superpowers/sdd/wave-4/not-settled.md`, `.superpowers/sdd/{13-wall-map,14-feasibility-notes}/slice-1{2,3}-bounds.md`); every do-not-cite key (as a constraint on pointers, not as a claim). A claim appearing in several docs is one row with several sources. Narrative — how a claim was found, reviewed, previously stated or corrected — is not a claim and is not harvested; the 23 dated-correction sites become `superseded` rows pointing at their successors.

**Sizing.** Roughly 600–900 rows expected (the wall map alone is 64; slice 12's claims files hold about 60; the three teardowns' MP tables about 60; the vanilla docs' `Ev` tables the rest).

## The checker and the generator

`tools/claims_check.py` (tracked, with tests under `tools/tests/`), run before every commit that touches `docs/areas`, `docs/platform`, `docs/facts`:

1. every `settled`/`open` register row's `target` page exists and contains the row's id in a tag;
2. every tag in those three layers names a register id, and the page's stated grade (where a page spells one) matches the register;
3. every `M` pointer's run id exists under `testing/artifacts/` and its key is not on that artifact's do-not-cite list (the register absorbs the current `testing/artifacts/README.md` tables);
4. warn-only: a sentence carrying a number and no tag;
5. `docs/reference/harness-commands.md` equals a fresh run of the generator (drift = failure);
6. every skill's quoted rules appear verbatim in its page's `## Rules` (drift = failure).

`tools/bus_inventory.py` (tracked, tested): reads every `TK.register("<name>", …)` in `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`, its side, its argument line and the docstring/comment above it, and emits `docs/reference/harness-commands.md` (one table: name · side · args · reply shape · one-line purpose). The current `docs/testing/README.md` § Command bus is the seed for the purpose column where the Lua carries no comment.

The old `tools/doc_lint.py` keeps enforcing the stamp and the `Ev`-grade rule on `docs/reference/wall-map.md` only; the three page layers are governed by the claims checker.

**Tag grammar.** A claim sentence ends with `[C0417]` or `[C0417, C0512]`. The register carries grade, pointer and bound; a page may restate the bound in words where the reader needs it ("measured on the dedicated-server path only"). No other citation form appears in the three layers.

## The page contract

Every page in `areas/`, `platform/`, `facts/`:

```markdown
# <Title>
Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>

## Rules            imperative, one line each, tagged; 10–20 lines; what the skill quotes
## How it works     the mechanism in prose, tagged per paragraph; tables where tabular
## Walls and bounds what cannot be done, or is only measured this far, tagged
## Open             open questions, each with the check that settles it (-> open-questions.md id)
## See also         the pages this one rests on or hands off to
```

Writing rules: present tense, current truth only — no "previously", "corrected", "resolved", "the review found", no dates except the stamp and dated counts; every number carries a tag; no restated numbers across pages (link instead); no run narratives (a session is cited, never described); bounds stated as facts, not as caveats about the process; 150–400 lines per page. The teardowns' useful residue (what the mod does, techniques worth stealing, pitfalls) becomes `facts/other-mods.md` fact sheets in the same contract.

**Skills.** `.claude/skills/<name>/SKILL.md`: frontmatter `name` + `description` (a trigger sentence listing the concrete things a task would touch — identifiers, file names, verbs); body = the page's `## Rules` verbatim + "read `docs/<page>` for the mechanism" + the two or three cross-page pointers. About 40 lines. The three general skills (`pz-modding-platform`, `pz-jar-research`, `pz-mod-testing`) fire on any PZ modding task; the seven `nutrition-<area>` skills on their area's identifiers.

## Execution

Four SDD plans, run with the existing process (fresh Opus implementers and reviewers, pathspec commits, never `--amend`, the checker green before every page commit). No game boot except one acceptance run to prove the generated harness reference against a live server.

- **Phase 0 — close the program.** Stop slice 14 (its SDD ledger records the ruling: the six notes are superseded by `docs/areas/`); tag `main` as `research-program-v1` and push the tag; leave the gitignored SDD workspaces on disk. Nothing else changes.
- **Phase 1 — the register.** Harvest `claims.csv` from the whole library (including the wall map, the claims files and the not-settled lists); deliver `tools/claims_check.py` and `tools/bus_inventory.py` with tests. Review: a sample of rows against their sources, and per-source coverage against each old doc's `Ev` tables. No page is written.
- **Phase 2 — `platform/` and `facts/`.** Pages written from the register rows targeted at them; disjoint files, so implementers run in parallel; the checker runs per page; review = fidelity to the register + the page contract.
- **Phase 3 — `areas/`, skills, roots.** The seven area pages and `open-questions.md`; the ten skills; the root `README.md`; `STRATEGY.md` trimmed; `CLAUDE.md` rewritten for the mod-development phase (operating rules stay; research resume points go).
- **Phase 4 — the cut.** Delete the old docs, ledgers and plans by pathspec in one commit; run the checker and the generator; push. `wall-map.md` and `artifacts.md` move rather than rewrite.

Process rules that change: `docs/progress.md` and `docs/decisions.md` retire; the per-plan SDD ledgers remain the only ledgers; a ruling a future agent must know becomes a rule in `CLAUDE.md` or `platform/lessons.md`, not a ledger row.

## Acceptance

1. `python tools/claims_check.py` → 0 findings: every register row placed once, every tag resolves, every `M` pointer exists and is citable, the harness reference and the skills in sync.
2. `python tools/bus_inventory.py --check` → in sync; one acceptance run (`pzt run --profile mod-under-test --hold 5`) green against the generated command table.
3. Every page obeys the contract (the five sections; 150–400 lines; no narrative markers — a grep for `previously|corrected 20|resolved|CONTESTED|the review` returns nothing under `docs/areas`, `docs/platform`, `docs/facts`).
4. Ten skills exist, each ≤ ~60 lines, each pointing at a page that exists; a dry-run prompt per skill (e.g. "add an `OnEat` handler") lists the expected skill as applicable.
5. The tag `research-program-v1` exists on the remote and `docs/superpowers/`, `docs/progress.md`, `docs/decisions.md`, `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing` are gone from `main`.
6. `python -m pytest tools/tests testing/tests -q` green (283 + the new tools' tests).
7. Coverage: the register's per-source counts equal the old docs' harvested rows (the Phase-1 review's table), so nothing established was dropped.

## Open questions for the spec review

- Should `claims.csv` be split per layer (three files) to keep merge conflicts small when pages are written in parallel? Default: one file, rows appended by target; implementers only write pages, never the register, in Phase 2/3.
- Should the wall map be rewritten into the page contract too (its Ev cells become tags) or kept verbatim? Default: keep verbatim under `reference/`, tag its rows in the register, let `areas/` pages cite the row ids.
- Where do the 26 named experiments' full specs live (currently gitignored `gaps.md`)? Default: `areas/open-questions.md` carries the table (id, question, shape, reading, cost, owner); the long specs are folded into that page's appendix rather than left gitignored.
- Do the datasets (`data/*.json`) need a checker of their own for the dated counts? Default: no; `reference/datasets.md` states counts with dates and the register tags them.
