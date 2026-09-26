# Project Zomboid Build 42 modding reference

An agent-facing reference for modding Project Zomboid Build 42.
Its first consumer is a realism nutrition mod: nutrients tracked mod-side beyond the vanilla macros, a rebalance of the vanilla food items, and multiplayer first.
Every claim on a page carries a tag naming its row in the claims register, and every row carries its grade and the pointer to its evidence.
The pages state what the game does and what a mod can and cannot change; the mod's design is not in this tree.

**Build:** `42.20.4` · jar `b0bbce05d5` · dedicated-server multiplayer · single-player never claimed.

## Reading order

Read in this order:

- [`CLAUDE.md`](CLAUDE.md) routes a task to the pages that answer it, in reading order, and carries the gates and the process.
- [`docs/areas/`](docs/areas/) is the nutrition lens: one page per design area of the mod, each with its rules, its options, its walls and what stays open, and the open questions gathered in one index.
- [`docs/platform/`](docs/platform/) is general modding knowledge — mod anatomy, the loader, the Lua platform, the multiplayer model, the harness, jar research and the lessons — entered at [`overview.md`](docs/platform/overview.md).
- [`docs/facts/`](docs/facts/) holds the measured mechanics of the vanilla food and nutrition systems, with [`other-mods/`](docs/facts/other-mods/) for the workshop corpus and its teardowns.
- [`docs/reference/`](docs/reference/) holds [the register](docs/reference/claims.tsv), [the datasets](docs/reference/datasets.md), [the tools](docs/reference/tools.md), [the experiments](docs/reference/experiments.md) and [the generated harness commands](docs/reference/harness-commands.md).

## The tree

```text
README.md                  the map
STRATEGY.md                the charter: the mod, the deliverable, the method rules
CLAUDE.md                  the agent handoff: task router, ground truth, gates, process
.claude/skills/            the project skills that route a task into the pages
docs/areas/                the nutrition lens: one page per design area, and the open questions
docs/platform/             general modding knowledge, entered at overview.md
docs/facts/                the vanilla food and nutrition mechanics
docs/facts/other-mods/     the workshop corpus catalogue and the teardowns
docs/reference/            the register and its coverage, experiments, jar notes, harness commands, datasets, tools
references/wiki-mirrors/   the mirrored wiki pages, each dated and digested
data/                      the generated datasets: food items, recipes, evolved recipes, the workshop corpus
tools/                     the register checker and delta applier, the page lint, the scanners and exporters
tools/tests/               the tool tests
testing/pzt/               the harness orchestrator: doctor, runs, scenarios
testing/PZTestKit/         the harness mod and its command bus
testing/profiles/          the test profiles: fixture, mods, sandbox, verify probes
testing/fixtures/          the server fixture
testing/experiments/       the experiment drivers and the experiment mods
testing/artifacts/         the committed run artifacts
testing/tests/             the harness tests
```

The wall map and the artifacts register move into `docs/reference/` at the cut, as `wall-map.md` and `artifacts.md`.
`docs/vanilla/`, `docs/modding/`, `docs/mods-survey/` and `docs/testing/` are the pre-restructure docs: readable until the cut, and forever at the tag `research-program-v1`.

## Tags

- A tag names a row of [`docs/reference/claims.tsv`](docs/reference/claims.tsv): a writer types `[#0417]` and the checker writes the suffix — the grade, then the bound token, then the status when the row is not settled — as `[#0417/M/n=1]` or `[#0417/C/open]`.
- Several ids share one bracket, `[#0417/M, #0512]`; a settled `C` row with no bound carries no suffix.
- Every register row has `id claim grade pointer bound status successor kind source owner`: the pointer is the evidence, and the owner is the page anchor that states the claim.
- `C` is read in the jar, the Lua or a script file; `M` is measured on a live run and points at an artifact key; `W` is a wiki mirror and only corroborates.
- `python tools/claims_check.py` checks the register's schema and pointers and every tag on the pages against its row.

## Coverage

`docs/platform/` is not a modding manual: [its coverage section](docs/platform/overview.md#coverage) marks each topic covered, touched or absent, and an absent topic has no page and no claim here, never a wall inferred from silence.

## Sources

The wiki pages this reference depends on are mirrored in [`references/wiki-mirrors/`](references/wiki-mirrors/README.md), each with its source, fetch date and page version in the header and a hand-written digest; the mirrors are attributed and carry the wiki's CC BY-NC-SA licence.

| Page | Mirror | Why |
|---|---|---|
| [Modding](https://pzwiki.net/wiki/Modding) | [`modding.md`](references/wiki-mirrors/modding.md), [`modding-hub-archived.md`](references/wiki-mirrors/modding-hub-archived.md) | the modding hub: policy, the tool index, the pointer to the multiplayer migration guides |
| [Mod structure](https://pzwiki.net/wiki/Mod_structure) | [`mod-structure.md`](references/wiki-mirrors/mod-structure.md) | mod anatomy: the `common/` and version-folder layout and the load order the page states |
| [Lua event](https://pzwiki.net/wiki/Lua_event) | [`lua-event.md`](references/wiki-mirrors/lua-event.md) | the event roster, and the boot events it marks client-only or server-only |
| [Mod data](https://pzwiki.net/wiki/Mod_data) | [`mod-data.md`](references/wiki-mirrors/mod-data.md) | object and global modData, the store for mod-side stats, and what the page says about sync |
| [Networking](https://pzwiki.net/wiki/Networking) | [`networking.md`](references/wiki-mirrors/networking.md) | the command-bus vocabulary and the side gates |
| [Startup parameters](https://pzwiki.net/wiki/Startup_parameters) | [`startup-parameters.md`](references/wiki-mirrors/startup-parameters.md) | the client and server arguments the harness launches with |
| [Testing mods in multiplayer](https://pzwiki.net/wiki/Testing_mods_in_multiplayer) | not mirrored | the manual multiplayer test procedure the harness automates |
| [Nutrition](https://pzwiki.net/wiki/Nutrition) | [`nutrition.md`](references/wiki-mirrors/nutrition.md) | the weight model: bands, thresholds, rates and macro ceilings |
| [Nutritional values](https://pzwiki.net/wiki/Nutritional_values) | [`nutritional-values.md`](references/wiki-mirrors/nutritional-values.md) | the per-item calorie and macro table, a cross-check for the datasets |
| [Food](https://pzwiki.net/wiki/Food) | [`food.md`](references/wiki-mirrors/food.md) | the food overview, the rot and cook states, per-item hunger, thirst and mood |
| [Cooking](https://pzwiki.net/wiki/Cooking) | [`cooking.md`](references/wiki-mirrors/cooking.md) | the cooking skill: ingredient use per level, evolved-recipe nutrition, poison thresholds |
| [Evolved recipes](https://pzwiki.net/wiki/Evolved_recipes) | [`evolved-recipes.md`](references/wiki-mirrors/evolved-recipes.md) | how ingredients combine into dishes, from an older build |
| [Appliances](https://pzwiki.net/wiki/Appliances) | [`appliances.md`](references/wiki-mirrors/appliances.md) | the appliance catalogue and its fridge roster |
| [Fridge](https://pzwiki.net/wiki/Fridge) | [`fridge.md`](references/wiki-mirrors/fridge.md) | the fridge and freezer spoil-rate multipliers |
| [Hungry](https://pzwiki.net/wiki/Hungry) | [`hungry.md`](references/wiki-mirrors/hungry.md) | the hunger moodle: level thresholds, penalties, the base rate and its traits |
| [Thirsty](https://pzwiki.net/wiki/Thirsty) | [`thirsty.md`](references/wiki-mirrors/thirsty.md) | the thirst moodle: level thresholds, penalties, the base rate and its modifiers |
| [Moodle](https://pzwiki.net/wiki/Moodle) | [`moodle.md`](references/wiki-mirrors/moodle.md) | the index of moodles with their causes and effects |
| [Trait](https://pzwiki.net/wiki/Trait) | [`trait.md`](references/wiki-mirrors/trait.md) | the trait roster and the adaptive strength, fitness and weight tables |
| [Fitness](https://pzwiki.net/wiki/Fitness) | [`fitness.md`](references/wiki-mirrors/fitness.md) | the fitness skill: endurance and combat multipliers per level |

### Ecosystem projects

Projects the wiki names, listed for orientation; none is mirrored here.

- API and editor docs: Umbrella (Lua typestubs), the Unofficial JavaDocs for Build 42, PZEventDoc and PZEventStubs, LuaDocs, ZedScripts and Zed Script for script files.
- Decompilers beside the jar toolchain: Zomboid Decompiler, Beautiful Java.
- Shared libraries: Starlit Library, TchernoLib, Doggy's Library, Elyon Lib.
- Moodles: Moodle Framework, "Moodles in lua".
- Loot and distributions: Easy Distributions API, SpawnerAPI, PZ Loot Analyzer, LootZed.
- Conventions: the Community Modding template.

### Internal sources

The local `42.20.4` install at `D:\SteamLibrary\steamapps\common\ProjectZomboid` and its workshop folder are the standing evidence base, read-only; the pz-b42 findings on the nutrition weight model and on the ItemQuality and BeyondTen mods are stated in [`docs/facts/nutrition-core.md`](docs/facts/nutrition-core.md) and the teardowns under [`docs/facts/other-mods/`](docs/facts/other-mods/).

## Related workspace

The jar toolchain lives at `C:\Users\Angus\pz-b42`: read its `WORKSPACE.md` first, treat it as read-only from here, and reach the disassembler through `pz.sh` (`./pz.sh grep|methods|refs|dump <class> [method]`).
[`docs/platform/jar-research.md`](docs/platform/jar-research.md) is how this reference turns a jar reading into a citable claim.
