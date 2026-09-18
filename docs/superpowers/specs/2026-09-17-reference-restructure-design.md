# Reference restructure — design spec

Date 2026-09-17 · Status: APPROVED 2026-09-17 by Angus (the four open questions confirmed as written) — v2 after a three-angle review (agentic consumer, general platform, nutrition depth; reports in the gitignored `.superpowers/spec-review/2026-09-17-restructure/`) · Author: the controller session, from a brainstorm with Angus.

## Goal

Turn the research library into an **agent-facing development reference** for Project Zomboid Build 42 modding, with the nutrition mod as its first consumer: a canonical markdown tree an agent reads on demand, plus thin **project-scoped skills** that route a task to the right pages. Remove the process history ("how we got there") from the tree while keeping every established claim with its evidence pointer. Keep the **general** PZ modding knowledge (platform, loader, Lua, MP, harness, jar research) first-class and nutrition-agnostic, so a tangential mod capability does not have to be relearned — and say plainly where that general knowledge ends.

## Non-goals

- No new measurements. The restructure mints no evidence; every claim in the new tree is a harvested claim from the current library with its grade and pointer.
- No mod design. The areas layer says what the research established, not what the mod should be (the charter's "reference, not design" rule stands). An options table with costs and walls is research; a chosen option is design.
- No change to the harness, runner, datasets, probe mods or artifacts beyond: one generator, one checker, one structured comment block above every `TK.register` site (no behaviour change), `tools/luabalance.py` moved into the tree, and one driver template `testing/experiments/_template.py` cut from `x121_overrides.py` with no measurement in it.
- No rewrite of the wiki mirrors. The wall map, the artifacts register and the experiment specs move with mechanical link rewrites only.

## Decisions taken in the brainstorm

1. Consumer model: a canonical markdown tree **plus** project-scoped skills (`.claude/skills/`) that route into it. Skills never duplicate a page; they quote its `## Rules` and point at it.
2. Slice 14 (feasibility notes) is **folded into** this restructure: its six design areas become the `docs/areas/` top layer, written once in the new contract. The research program closes at the tag; no separate program-close ceremony.
3. Process history is **deleted from the tree**; git keeps it under the tag `research-program-v1`. No `archive/` directory.
4. Tree shape: **three layers** — `areas/` (the nutrition lens), `platform/` (general PZ B42 modding knowledge), `facts/` (measured game mechanics by mechanism) — over a `reference/` layer (generated harness commands, datasets, artifacts register, the wall map).
5. Evidence: every claim keeps its grade and pointer, in a **compact tag** that resolves to a row in a claims register; bounds live in the register and are stated as facts in prose where they matter.
6. Tooling docs are first-class: "testing your mod" is an area page; the harness command reference is **generated from the Lua** so it cannot trail the code.
7. Execution is **register-first**: harvest every graded claim into a machine-checkable register, write the pages from the register, prove coverage with a checker, then delete the old tree.

## What the review changed

Counted 2026-09-17 against the working tree: 1,258 `Ev`-table rows and about 300 graded paragraphs across 23 source files; 64 `TK.register` sites over 56 names (8 registered on both sides with different arguments); 16 of the 43 run ids cited in the docs have no folder under `testing/artifacts/`; over 100 `C+M` cells, about 60 `C (arith.)`, 30 `W vs C`, 13 inference marks; the wall map cites the docs the cut deletes 74 times and the artifacts README 80 times. Consequences, each written into the sections below:

- The harness is general and moves to `platform/harness.md`; `areas/testing-your-mod.md` becomes this mod's test plan (decision 6 under decision 4's placement rule).
- The register grows a `kind`, a `successor` and an `owner` column, eight pointer forms, multi-pointer rows, an `unverified` status and controlled bound tokens; it is TSV; ids are `#0001` so a tag cannot be misread as grade C; the tag carries the grade at the sentence.
- Page writers never edit the register; they file deltas with provisional ids and the controller mints.
- The page contract gains `## Key facts` (facts pages), `## Options` (areas pages), `## Procedure` (the two how-to pages), `## Worked examples`, a reason clause on every rule line, annotated code blocks as one claim, and a coverage boundary.
- Two facts pages are added (`spoilage`, `cooking-and-recipes`); `other-mods` becomes one page per mod plus the catalog; the moodle and trait walls become platform rows.
- The generator reads a structured comment block; the reading rules live on a page, not in the generated file.
- The spec gains § Extending the reference after the cut and § What the rewritten `CLAUDE.md` carries.
- Three gitignored working reads move into `docs/reference/` so every register `source` resolves from a clone.

## The target tree

```
README.md                    the map: what the repo is, the reading order, the tag grammar, the tree,
                             the coverage line ("platform/ is not a modding manual")
CLAUDE.md                    agent operating rules for this repo; the router (tree map + task shape ->
                             reading order); see § What the rewritten CLAUDE.md carries
STRATEGY.md                  the charter, trimmed of program history
docs/
  areas/                     the nutrition lens — one page per design question, skill-backed
    new-nutrients.md         where a mod nutrient can live, sync, persist, act
    item-pass.md             overriding vanilla foods: the pass's own reading (minimal blocks, the
                             record count, the risks, X15/X33); cites the loader and the item model
    eat-and-cook-hooks.md    where a hook sits, on which side, with which limits; X24/X31/X33
    mp-sync.md               the options table and the rules; owns no fact — cites mp-model and
                             wire-packets (the hub the others cite)
    ui-and-moodles.md        the reading: MoodleFramework as the only route (X29), panels, translations,
                             display names; restates no registry mechanism
    packaging.md             what THIS mod does about anatomy, the checksum gate, the resident stack,
                             compat; X16
    testing-your-mod.md      this mod's test plan: its profiles, scenarios, [[verify]] rows, the
                             experiments it owns (X4, X5, X13, X29), the sandbox roll-up table
    open-questions.md        the index: one line per open row (id, question, owner, -> X<N>, the
                             settling check); cites reference/experiments.md; never restates a spec
  platform/                  GENERAL PZ B42 modding knowledge — nutrition-agnostic
    overview.md              the routing page: the four surfaces, the two Lua states, one server, the
                             process model (launch, join, RCON, admin commands), § Coverage (the
                             boundary), which page owns which mechanism; no number of its own
    mod-anatomy.md           mod.info and its keys, discovery under Steam and -nosteam, the id chain,
                             version dirs, Mods= and require=, the missing-mod and versionMin failure
                             modes, the join reset of default.txt, the checksum gate (all three arms),
                             translations, client-only mods, build pinning
    loader-and-scripts.md    the file map (activeFileMap, LoadDirBase, the overrides line, require),
                             then the script loader: bucket append, per-key merge, sorted replay, the
                             template_ pre-sort, same-path drop, default modData, InitLoadPP, reload
    lua-platform.md          Kahlua's limits and behaviours (pcall, raises, the debug break, removed
                             APIs, Java-member access and the exposure test), script hooks, the events
                             exercised, the registries (MoodleType, CharacterTrait: what registration
                             does and does not give you), file IO, the dev loop (reloadlua)
    mp-model.md              ownership per quantity, the wire routes, wipe-and-replace, what a client
                             copy is and is not, the command bus; the packet MECHANISMS (owns no field
                             list — wire-packets does)
    harness.md               the instrument: pzt, the profile schema, the bus protocol and
                             reply-reading rules, the witness, the scenario layer, driver discipline,
                             the standing experiment contract, the evidence limits; ## Procedure
    lessons.md               general lessons as RULES with tags and reasons: sync mistakes, Kahlua
                             traps, testing discipline (staircase vs ramp first), corpus drift,
                             "measure the mechanism, not the mirror"
    jar-research.md          answering a question from the jar: the disassembler's subcommands, what
                             each does and does not tell you, reverse callers, offsets re-located by
                             content, the exposer list and what "exposed" means; ## Procedure. States
                             that the disassembler lives in C:\Users\Angus\pz-b42, not in this repo
  facts/                     game mechanics as measured or read, by mechanism
    eating-pipeline.md       Eat, DrinkFluid, the modifier ladder, partial eating, OnEat/EatType, the
                             sandbox gate, the order of writes (an annotated block)
    food-item-model.md       the item's state axes, the 114 script keys and what the loader does with
                             each (a tagged table), poison
    spoilage.md              aging, fridge/freezer/frozen, spawn-time age, sealed cans, ReplaceOnRotten,
                             the rot sandbox options
    cooking-and-recipes.md   Food.update's cook block, evolved-recipe summation, craftRecipe IO and the
                             uses-not-items rule, type-change deltas
    body-and-weight.md       passive burn, hunger/thirst, moodle thresholds and their drivers, weight
                             bands and trait effects, the body-side sandbox options
    nutrition-core.md        the weight model, the store clamps, the three-day server verification
    wire-packets.md          ItemStatsPacket and PlayerStatsPacket field contracts for food and
                             nutrition, the measured desyncs, the staircase reading
    other-mods/              one page per torn-down mod in the contract (autocook.md,
                             longtermpreservation.md, simplestatus.md, beyondten.md, itemquality.md):
                             what it does, techniques worth stealing, pitfalls, compat; and catalog.md
                             for the survey's dated sweeps, status table and corpus-level facts. Engine
                             facts a teardown discovered are platform/facts rows, cited from the mod page
  reference/                 outside the page contract; doc_lint keeps the stamp rule on wall-map.md
    harness-commands.md      GENERATED by tools/bus_inventory.py from every TK.register(...) site
    datasets.md              data/* schemas, the column authority (from data/README.md), dated counts;
                             fidelity facts are facts/ rows it links
    artifacts.md             moved whole: run id -> file -> what it measured -> reading guide; Cited by
                             regenerated from the register; the x123b alias
    do-not-cite.csv          run, key, why, read_instead — the checker's input
    wall-map.md              the 64-row verdict table, moved; Ev cells rewritten to register ids
    experiments.md           the 26 named experiments' full specs, moved from the gitignored gaps.md
    jar-method-notes.md      the disassembler method notes and the exposer table, moved from jar-locks.md
    tools.md                 every tracked tool: what it reads and writes, its rules with their engine
                             standing (the mod_lint table), its conventions
    claims.tsv               the claims register (a deliverable, see below)
    claims-coverage.md       per old source: rows harvested, superseded, dropped with the reason
.claude/skills/
  pz-modding-platform/       fires on a PZ modding task OUTSIDE the nutrition areas; quotes § Coverage
  pz-jar-research/           fires when a question needs the jar -> platform/jar-research.md
  pz-mod-testing/            fires when a mod needs a live test -> platform/harness.md (paths: testing/**)
  nutrition-<area>/          one skill per areas/ page (seven), nutrition-specific
data/                        unchanged; data/README.md's column authority moves to reference/datasets.md
tools/                       + claims_check.py, bus_inventory.py, luabalance.py, tests
testing/                     unchanged + experiments/_template.py; the structured comments in PZTestKit
references/wiki-mirrors/     unchanged + a generated table of contradiction rows per mirror in its README
```

**Placement rule.** A mechanism goes in `platform/` if it would hold for a weapon mod or a UI mod; in `facts/` if it is a measured property of the food, body or nutrition systems; in `areas/` only as a nutrition-design reading of the two layers below. A fact lives on one page (its `owner`); other pages cite the tag and never restate the number.

**Sync placement.** `platform/mp-model.md` owns the packet mechanisms (what a packet is, when it fires, wipe-and-replace, the cached-packet leak, the two item packets); `facts/wire-packets.md` owns the field contracts for food and nutrition (which `Food`/`Nutrition` getters each packet reads, the measured desyncs, the cooked-thirst halving, the 1 Hz staircase); `areas/mp-sync.md` owns no fact.

**The hard cases, decided.**

- Item overrides: `platform/loader-and-scripts.md#per-key-merge` owns the per-key merge, the sorted replay and the same-path drop; `facts/food-item-model.md` owns the 114 keys; `areas/item-pass.md` cites both and adds only the pass's own reading.
- The eat hooks: dispatch mechanics (how `OnEat`, `OnCooked`, `OnCreate` resolve, which side calls each, that `EatOnClient` applies no numbers, that a `server/` wrapper of `ISEatFoodAction.complete` runs before `Eat`) are `platform/lua-platform.md#script-hooks`; the order of writes inside `Eat` and the packets it sends are `facts/eating-pipeline.md`; `areas/eat-and-cook-hooks.md` is the reading.
- The checksum gate: `platform/mod-anatomy.md#checksum-gate` owns all three arms (script, Lua, anim), the normalisation, the bypass role and the AntiCheat timeout; `areas/packaging.md` cites them and adds X16.
- Moodles and traits: the registry mechanism and the two moodle walls (the pinned level, the unexposed `MoodleStat`) are `platform/lua-platform.md#registries`; `areas/ui-and-moodles.md` carries the reading and restates no mechanism.
- The harness: `platform/harness.md` is the instrument; `areas/testing-your-mod.md` is this mod's plan; `pz-mod-testing` points at the platform page.
- Two merges exist and are named apart: the file-level merge (version dir over `common/`, `LoadDirBase`'s vanilla-first dedupe, translations) on `mod-anatomy.md`; the block-level script merge on `loader-and-scripts.md`.

**The anchor plan.** Deliverable 0 of Phase 1 is the anchor list — every page's `## How it works` anchors, seeded from the platform review's Appendix D and the facts split above — reviewed before any row is given an owner. A row's `owner` is `page#anchor`.

**Deleted from the tree at the cut** (kept under the tag): `docs/superpowers/` (plans, specs, notes — this spec included), `docs/progress.md`, `docs/decisions.md`, `docs/references.md` (folded into the README), `docs/feasibility/`, and the current `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing` once every claim they carry has landed.

## The claims register

`docs/reference/claims.tsv`, tracked, tab-separated, no quoting (claims carry commas, semicolons, pipes and backticks), one row per claim.

| column | content |
|---|---|
| `id` | stable, `#0001`… (never reused). Phase 1 allocates blocks per source group: vanilla `#0001–#0800`, modding `#0801–#1300`, survey `#1301–#1700`, testing/data/tools/ledgers `#1701–#2000`; the controller alone mints `#2001+` afterwards |
| `claim` | one sentence, numbers and units included |
| `grade` | the strongest grade the row's pointers carry: `C` / `M` / `W` |
| `pointer` | one or more, `;`-separated, each prefixed by its form: `jar:Class.method @off L<n>` · `run:<run-id> <file> <json.key.path>` · `wiki:<mirror file> <page version or fetch date>` · `lua:<path under media/>:<line> "<anchor text>"` · `mod:<workshop id>/<tree>/<path>:<line> "<anchor text>"` (tree-qualified: `common`, `42.13`, …) · `repo:<path>:<line> "<anchor text>"` (this repository's code) · `data:<file> <sweep or fetch stamp>` · `tool:<repo>/<path>:<line>`. The form implies the grade (`run:` is M, `wiki:` is W, the rest C). Anchor text is mandatory on `lua:`, `mod:` and `repo:` and is re-located by content before quoting |
| `bound` | a controlled first token — `none`, `n=1`, `one-side`, `C-only`, `one-fixture`, `arith.`, `inference`, `uncommitted`, `snapshot <date>` — then free text (`server VM only`, `dedicated-server path`, `42.20.4`, the restriction quoted from a do-not-cite reading guide). An inference is never graded `M` |
| `status` | `settled` / `open` / `superseded` / `unverified` (kept with its old pointer, never quoted by a skill, listed on its owner's `## Open` with the check that re-verifies it) |
| `successor` | an id, filled only when `status = superseded` (a split names two) |
| `kind` | `mechanism` (a constant, rate, threshold or behaviour) · `order` (an annotated code block whose claim is a sequence) · `table` (a dataset-shaped table harvested as one row) · `count` (a dated corpus or dataset count) · `verdict` (a wall-map row) · `rule` (an imperative) · `bound` (a restriction on how a claim or artifact may be read) · `contradiction` (mirror vs code) · `tool` (a behaviour of a script) · `open` |
| `source` | the old doc and section the row came from (several, `;`-separated, when duplicated); for rows from the moved working reads, the new `docs/reference/` path |
| `owner` | the one page and anchor that states the claim with its number (`platform/lua-platform.md#pcall`); any page may cite the tag |

**Harvest grain.** A row is the smallest sentence one measurement or one dump could falsify, carrying one grade and the pointers that establish that sentence: split when two numbers rest on different pointers, sides or bounds; keep together when several numbers are one reading off one artifact key or one dump. A dataset-shaped table (a key list, a field list, a census, a schema, a sample table) is one `table` row whose claim states the count and the date, plus one row per exception the prose singles out; the page carries the table verbatim under that one tag. Per-food and per-recipe values never enter the register: the dataset is the pointer (`data:data/food-items.json items[id=Base.Apple].calories`), and a row exists only where a page states the value as an example, control or subject. A wall-map row yields one `verdict` row citing the map row id, plus one `mechanism` or `bound` row per fact the map states that no other source carries, plus one `open` row per `-> X` reference. A `C+M` cell is one row with two pointers. A KEEP/FILTER entry or a `## Rules` line is a `rule` row resting on the mechanism rows it cites. A code block whose claim is an order of operations is one `order` row, tagged on its caption, whose inline offsets are the pointer; numbers inside it are not re-tagged. A mirror-vs-code discrepancy is a `contradiction` row whose claim states the code-side fact, whose `wiki:` pointer names the mirror and version, and whose bound reads `mirror wrong: <the mirror's words>`; its owner is the facts page's `## Walls and bounds`.

**Harvest sources.** `docs/vanilla`, `docs/modding`, `docs/mods-survey` (the catalog and the teardowns), `docs/testing`, `data/README.md`, `tools/README.md`, `CLAUDE.md` § 8 and § 10, the slice-12 claims files; `docs/decisions.md` for `bound` rows (float rendering before `291f977`, per-scope exclusion sets, the unstamped CSV); `.superpowers/sdd/13-wall-map/jar-locks.md` § Tool note and § Summary (as `tool` rows, after the move to `reference/jar-method-notes.md`); `.superpowers/sdd/13-wall-map/gaps.md` § Named experiments onward (after the move to `reference/experiments.md`); `.superpowers/sdd/wave-4/not-settled.md`, `.superpowers/sdd/13-wall-map/slice-12-bounds.md` and `.superpowers/sdd/14-feasibility-notes/slice-13-bounds.md` — a bound from these is imported only where the wall map or a slice-12 doc does not already carry its successor; a superseded bullet becomes a `superseded` row naming it. A claim appearing in several docs is one row with several sources. Narrative — how a claim was found, reviewed, previously stated or corrected — is not harvested; every dated-correction site (counted by the harvest with a fixed grep, not assumed) becomes a `superseded` row pointing at its successor. Engine facts discovered inside a teardown are owned by placement, not by source.

**Runs without artifacts.** `pointer` may name only a run with a folder under `testing/artifacts/`; `reference/artifacts.md` carries an alias table for a boot stored inside another run's file (`x123b-20260911-034500 -> x123-20260911-034426 platform-folder.json boots.common_id`) that the checker honours. A run cited as non-evidence appears in `bound` only, as `uncommitted: <run-id>`. An `M` claim whose only run has no artifact is harvested `status unverified`, `bound uncommitted: <run-id>`, and its owner lists it under `## Open` with the re-measurement that settles it.

**Do-not-cite.** Keys are harvested into `docs/reference/do-not-cite.csv` (`run, key, why, read_instead`), never into the register. Reading restrictions that are not keys ("as a population, n = 1"; "`phases.M3` read as a general ordering rule") stay verbatim in `reference/artifacts.md` and are quoted in the `bound` of any row citing the key.

**Sizing.** Counted 2026-09-17: 1,258 `Ev`-table rows and about 300 graded paragraphs (vanilla 667 rows, modding 253, teardowns 161, catalog 109, profiles 53, data/README 15). Expect 1,000–1,500 register rows after the grain rule; the coverage table reports the per-kind counts so a 114-row table collapsing to one row is visible, not hidden.

**Deltas in Phases 2 and 3.** An implementer never edits `claims.tsv`. It writes its page with provisional tags `[T<task>.<n>]` where it needs a row the register lacks, retargets or splits, and files `claims-delta.tsv` in its SDD workspace beside its report (`op ∈ {retarget, split, add, status}`, the row, the reason). The checker fails a provisional tag unless run with `--allow-provisional` (the implementer's local run). Before the task's review closes, the controller applies the delta in a `Register: task N delta` commit — real ids from the next block, the page's tags rewritten, a split marking the parent `superseded` with two successors — and the reviewer sees the page with real tags. The cut fails while any delta file is unapplied.

**Coverage table.** `docs/reference/claims-coverage.md`, tracked: per old source, rows harvested, rows superseded, rows deliberately dropped with the reason, `unverified` rows; the Phase-1 review's table, kept so a clone can audit the harvest.

## The checker and the generator

`tools/claims_check.py` (tracked, with tests under `tools/tests/`), run with `--staged` before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or `tools/bus_inventory.py`; it runs every rule the staged paths can break:

1. every `settled` / `open` / `unverified` row's `owner` page exists and contains the row's id in a tag;
2. every tag in `docs/areas`, `docs/platform`, `docs/facts` names a register id; a tag's suffix agrees with the register's grade, bound token and status; a provisional `[T…]` tag fails unless `--allow-provisional`;
3. every `run:` pointer's run id exists under `testing/artifacts/` (aliases honoured) and its key is not in `do-not-cite.csv`; every `repo:` path exists; every `lua:`, `mod:` and `repo:` pointer carries anchor text;
4. warn-only: a sentence carrying a number and no tag — not inside code spans or fences, not under `## Procedure`, not under `docs/reference/`;
5. `docs/reference/harness-commands.md` equals a fresh run of the generator (drift = failure);
6. every line under a skill's `## Rules quoted` appears verbatim, tag included, in the `## Rules` of a page the skill names (line-level: a page may carry twenty rules while the skill quotes six);
7. every `file:lines` in a `## Worked examples` table exists;
8. `--fix-tags` writes each tag's suffix from the register; `--view <layer>` prints a per-layer slice of the register for a page writer.

`tools/bus_inventory.py` (tracked, tested) reads every `TK.register("<name>", …)` site under `testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/` and the structured comment block directly above it — `-- @args <user> <fullType> [fraction]`, `-- @reply {before, after, delta, …}` (the keys, never the values), `-- @purpose <one line>` — and emits `docs/reference/harness-commands.md`: one row per (name, side) — never per name, since eight names take different arguments per side — with name · side · `file:line` · args · reply keys · purpose. It fails on a site missing any of the three lines; a column the Lua truly cannot carry reads `unrecorded`, never a guess. Writing the 64 blocks (seeded from `docs/testing/README.md` § Command bus; 14 commands have no seed and get a purpose written from the Lua) is the one harness commit of this restructure, under the harness-iteration rule, with `tools/luabalance.py` green; the acceptance run is its smoke test. The reply-reading rules (the three buckets, `{}` for an empty list, `resolved` names the subject that answered, `limit` is a BREAK, the `null` guard) are `platform/harness.md#reading-a-reply`, not the generated file.

`tools/luabalance.py` moves into the tree from the gitignored `.superpowers/sdd/_tools/`, with a test. The old `tools/doc_lint.py` keeps enforcing the stamp and the `Ev`-grade rule on `docs/reference/wall-map.md` only.

**Tag grammar.** A writer types `[#0417]`; `claims_check.py --fix-tags` appends the canonical suffix: nothing for a settled C row with no bound; otherwise the grade, then the bound token if any, then the status if not settled: `[#0417/M]`, `[#0417/M/n=1]`, `[#0417/W]`, `[#0417/C/inference]`, `[#0417/C/open]`, `[#0417/M/uncommitted/unverified]`. Several tags: `[#0417/M, #0512]`. The register carries the pointer and the full bound; a page restates a bound in words where the reader needs it ("measured on the dedicated-server path only"). No other citation form appears in the three layers; a run id may appear in prose only inside a sentence that also carries a tag whose pointer names that run.

## The page contract

Every page in `areas/`, `platform/`, `facts/`:

```markdown
# <Title>
Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>

## Rules              areas/ and platform/: imperative, one line each, 10–20 lines; what a skill quotes
## Key facts          facts/ instead of Rules: declarative, one line each, tagged; 8–15 lines
## How it works       the mechanism in prose, tagged per paragraph; tables where tabular; an order of
                      operations as an annotated code block tagged on its caption
## Options            areas/ only: one table, option · what it costs · which wall it hits · tags
## Walls and bounds   what cannot be done, or is only measured this far, tagged; ends with a
                      "Not covered:" line naming the adjacent surface the library never read
## Open               two row kinds: an open question with the check that settles it (-> X<N>), and a
                      decision the design must take with the fact that forces it (no recommendation)
## Worked examples    platform/ pages with code shapes: | shape | file:lines | what it shows | into
                      testing/experiments/ and the TKX_* mods; optional elsewhere
## Procedure          jar-research.md and harness.md only: numbered steps; no tag needed on a number
## See also           the pages this one rests on or hands off to
```

**A rule line** is an imperative, a colon, the one-clause reason (the mechanism, never the history), the tag(s): `- Guard every media/lua/server/ file with a nil-checked isServer(): the file also executes in the MP client's Lua state [#0231/M/n=1].` A rule whose safety depends on its bound carries the bound in the line ("a client can derive a weight direction, never a weight"). A rule that belongs to two areas appears on both pages only as the byte-identical line with the same tags; the checker diffs them.

**An options table** cites a wall-map row or a register id per row, marks no row preferred, recommended or chosen, lists rows in wall-map row order, and ends with the decision the design must take, as a question.

**Writing rules:** present tense, current truth only — no "previously", "corrected", "resolved in", "the review found", no dates except the stamp and dated counts; every number outside a code block carries a tag; the number appears only on the owner page (other pages link); no run narratives (a session is cited, never described); bounds stated as facts, not as caveats about the process; an inference is written as one ("the consequence is read from the code, not measured"). Length: 150–400 lines of prose; tagged tables, index rows and code blocks do not count; `harness.md`, `mod-anatomy.md`, `lua-platform.md` and `mp-model.md` may run to 500 or split (`harness.md` into the instrument and the scenario layer). Pages under `docs/reference/` are outside the contract.

**Skills.** `.claude/skills/<name>/SKILL.md`: frontmatter `name`, `description` (the trigger sentence: the concrete identifiers, file names and verbs the task would touch, key use case first, under 1,000 characters — the listing truncates at 1,536 and shortens every description under budget pressure), `paths` where a skill is file-scoped (`pz-mod-testing`: `testing/**`). Body, about 30 lines: `## Read first` (the pages in reading order, two to four), `## Rules quoted` (at most eight lines copied verbatim with their tags from those pages' `## Rules`, chosen for the hazards an agent meets before it reads), the two or three cross-page pointers. `CLAUDE.md`, which is always loaded, is the router: the tree map and a table `task shape -> pages in reading order`. `pz-modding-platform` fires on a PZ modding task outside the nutrition areas (weapons, UI, world, vehicles, sounds) and quotes `platform/overview.md` § Coverage; it does not fire on a nutrition task. The seven `nutrition-<area>` skills fire on their area's identifiers.

**Coverage.** `platform/overview.md` § Coverage is a table of the general topics with a status each — `covered` (a mechanism page with rows), `touched` (rows, no page: sandbox options a mod declares, the UI framework, timed actions, the crafting pipeline, server admin and RCON, build detection, client-only mods, the events roster), `absent` (sounds, tiles and sprites, vehicles, world and map mods, Workshop publishing, the save format) — and the never-written vanilla docs (`food-sources`, cooking XP and the cooking UI). It opens: "`platform/` is not a modding manual. It holds what this library measured or read while building a nutrition mod on a dedicated 42.20.4 server with one client. A topic marked absent has no page, no rule and no claim here; an agent asked about it says so and reads the jar or the mirror, and never infers a wall from silence. Every verdict is dedicated-server multiplayer; single-player is never claimed." Each touched topic gets an `open` register row so the boundary is in the register, not only on the page. The root `README.md` and `CLAUDE.md` carry the one-line form.

## Extending the reference after the cut

A claim is minted in the commit that lands its evidence, never later.

1. **A new measurement.** The run's JSON is copied byte-identical to `testing/artifacts/<run-id>/` with a row in `reference/artifacts.md` (run id · file · what it measured · its reading guide) and its keys in `do-not-cite.csv` (empty allowed). The same commit adds the register rows and the tagged sentences on their owner pages, and is green under the checker.
2. **Ids.** The next unused id; the checker fails a duplicate or a gap. A parallel SDD wave reserves an id block per task in its ledger before dispatch.
3. **Settling an open row.** The row keeps its id: `open -> settled`, pointer and bound filled, the owner sentence rewritten to the settled form, its line removed from `areas/open-questions.md`, its row in `reference/experiments.md` and the wall map's experiment table marked `run <run-id>`. A reading that comes back unmeasured or trivial stays `open` with the run named in `bound`.
4. **Superseding.** A claim a run overturns keeps its id and goes `superseded` with `successor`; every page tagging it moves to the successor in the same commit.
5. **A harness change** (a new `TK.register`, a changed reply) lands in its own commit with its comment block, `tools/luabalance.py` green and `tools/bus_inventory.py` regenerating `reference/harness-commands.md`, before the run that uses it.
6. **A rule line edit** re-syncs the skills that quote it in the same commit (rule 6 fails otherwise).
7. **Who runs the checker.** The committer, `--staged`, before every commit that touches the trigger paths; an SDD reviewer re-runs it on the review package.

## What the rewritten `CLAUDE.md` carries

In order: (1) what the repo is now — the reference tree and the mod — and the router table (`task shape -> pages in reading order`); (2) ground truth: the 42.20.4 install and the workshop folder are read-only, always; the jar toolchain at `C:\Users\Angus\pz-b42`; the library is dedicated-server MP evidence, single-player never claimed; (3) gates before any commit: `claims_check.py --staged` → 0, `bus_inventory.py --check`, `doc_lint.py docs/reference/wall-map.md`, pytest green with the dated count; (4) § Extending the reference, one line per item; (5) harness rules: `pzt doctor` before every boot; one live game session at a time; never `-safemode`; harness changes before the run, in their own commit; a driver is never edited after its run; readings that come back trivial, unmeasured or falsified are written as such; artifacts byte-identical; a raising probe is gated on the server with `[client] timeout` low and `pzt run` expected to FAIL; a stray `ProjectZomboid64.exe` predating a session is the user's own client, never killed; fixture caches are per-machine and gitignored; (6) process: SDD with fresh Opus implementers and reviewers, Fable lead, no silent downgrade; per-plan ledgers are the only ledgers; a ruling about the platform becomes a rule on `platform/lessons.md` with its mechanism row, a ruling about how this repository works becomes a rule here, nothing is a ledger row; pathspec commits; never `--amend`; no Claude attribution; succinct messages; proceed to completion and ledger decisions; (7) environment gotchas that are about this repository (the cwd reset, heredoc apostrophes, the CRLF survivors by name, the stray client) — the platform truths (`-debug` parks on an unguarded raise; the corpus drifts, so every count is dated) move to `platform/lessons.md` and are pointed at; (8) the memory file to update at every close.

## Execution

Four SDD plans, run with the existing process (fresh Opus implementers and reviewers, pathspec commits, never `--amend`, the checker green before every page commit). No game boot except one acceptance run to prove the generated harness reference against a live server.

- **Phase 0 — close the program.** Stop slice 14 (its SDD ledger records the ruling: the six notes are superseded by `docs/areas/`); tag `main` as `research-program-v1` and push the tag; leave the gitignored SDD workspaces on disk. Nothing else changes.
- **Phase 1 — the register.** In order: move the three working reads into `docs/reference/` (`experiments.md`, `jar-method-notes.md`; `not-settled.md` and the bounds lists are consumed, not moved) and `luabalance.py` into `tools/`; the anchor plan (deliverable 0, reviewed); the harness comment commit; the harvest into `claims.tsv` by source-group id block, with `do-not-cite.csv` and `claims-coverage.md`; `tools/claims_check.py` and `tools/bus_inventory.py` with tests; the `old section -> ids` map the wall-map rewrite needs. Review: a sample of rows against their sources per kind, and the coverage table against each old doc's `Ev` tables. No page is written.
- **Phase 2 — `platform/` and `facts/`.** Pages written from the register rows owned by them; disjoint files, so implementers run in parallel; the checker runs per page; deltas applied by the controller before each review closes; review = fidelity to the register + the page contract. `overview.md` is written last, from the finished anchors.
- **Phase 3 — `areas/`, skills, roots.** The seven area pages and `open-questions.md`; the ten skills; the root `README.md`; `STRATEGY.md` trimmed; `CLAUDE.md` rewritten per its section above; `reference/datasets.md` and `reference/tools.md`.
- **Phase 4 — the cut.** Move `wall-map.md` with its `Ev`-cell rewrite (74 references to deleted docs become register ids) and `artifacts.md` whole with its `Cited by` regenerated; delete the old docs, ledgers and plans by pathspec in one commit; run the checker, the generator and the narrative grep; push.

Process rules that change: `docs/progress.md` and `docs/decisions.md` retire; the per-plan SDD ledgers remain the only ledgers; a ruling a future agent must know becomes a rule in `CLAUDE.md` or `platform/lessons.md`, not a ledger row.

## Acceptance

1. `python tools/claims_check.py` → 0 findings: every register row owned once, every tag resolves with the right suffix, every `run:` pointer exists and is citable, every `repo:` and worked-example path exists, the harness reference and the skills in sync, no provisional tag, no unapplied delta.
2. `python tools/bus_inventory.py --check` → in sync; one acceptance run (`pzt run --profile mod-under-test --hold 5`) green against the generated command table.
3. Every page obeys the contract (its sections; the prose cap; no narrative markers — `\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)\b` outside code spans returns nothing under `docs/areas`, `docs/platform`, `docs/facts`).
4. Ten skills exist, each ≤ 60 lines, each pointing at pages that exist; one prompt per skill in a fresh session invokes the expected skill (there is no dry-run mode; the transcripts are kept in the SDD workspace).
5. The tag `research-program-v1` exists on the remote and `docs/superpowers/`, `docs/progress.md`, `docs/decisions.md`, `docs/feasibility/`, `docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing` are gone from `main`.
6. `python -m pytest tools/tests testing/tests -q` green (283 + the new tools' tests).
7. Coverage: `claims-coverage.md` reconciles every old doc's `Ev` rows and graded paragraphs to harvested, superseded or dropped-with-reason rows, so nothing established was dropped silently.
8. Every register `source` and every page link resolves from a fresh clone (no `.superpowers/` path survives in the tree).

## Open questions from the draft — resolved in review

1. **Split the register per layer?** No. One `claims.tsv`; page writers never edit it (the delta protocol above); per-source id blocks make Phase 1's parallel harvest collision-free; a per-layer split would put an `areas/` citation of a `platform/` row across two id spaces. `--view <layer>` gives a writer its slice.
2. **Rewrite the wall map into the contract?** No. It moves verbatim under `reference/` with one mechanical rewrite: every `Ev`-cell reference to a deleted doc becomes the register id(s) harvested from it (the Phase-1 `old section -> ids` map is a deliverable). Its rows are `verdict` rows owned by `reference/wall-map.md`; `platform/` and `areas/` pages cite them by register id, never by row id, so one citation form holds.
3. **Where do the 26 experiments' full specs live?** `docs/reference/experiments.md`, moved verbatim from the gitignored `gaps.md` (tracked for the first time; outside the contract). The standing experiment contract and its riders become rules on `platform/harness.md`; `areas/open-questions.md` is an index of one-line rows (register id, question, owner, `-> X<N>`, the settling check as a pointer) and gives open rows no third id space. The four experiments the folded feasibility notes cannot be written without (X4 traits, X5 translation override, X13 the drink hook, X29 MoodleFramework) are stated on their area pages as walls ("no measured moodle route exists"; "the trait sync path is untraced"), not as findings.
4. **A checker for the datasets' dated counts?** No separate checker. A dated count is a `count` row (`data:` pointer, `snapshot <date>` bound) that `reference/datasets.md` states and the register tags; a re-scan mints a successor. The existing byte-stability tests pin the files; rule 4 does not run under `docs/reference/`.

## Consequences for Angus to confirm

- The tree is larger than the draft's: 8 area pages, 8 platform pages, 7 facts pages plus 6 mod pages, 11 reference files, 10 skills, a register of 1,000–1,500 rows, one harness comment commit and a driver template. Phase 1 is the long phase.
- Decision 2 folds slice 14 in without running X4, X5, X13 or X29; the area pages will carry those four as walls, and the mod-design phase inherits them as its first experiments.
- The harness comment block is an edit to the probe mod's Lua (comments only) — allowed by the harness-iteration rule, named here so it is not a surprise in the Phase-1 diff.
