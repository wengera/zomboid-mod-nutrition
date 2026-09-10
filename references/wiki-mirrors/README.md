# Wiki mirrors

Mirrors of the PZwiki pages we depend on, kept so page edits/deletions can't
erase our sources. Each file header carries the source URL, the retrieval date,
and the page's own `{{Page version}}` stamp at retrieval.

**License/attribution:** PZwiki content is published under
CC BY-NC-SA (see pzwiki.net site notices). These excerpts are attributed,
non-commercial, and share-alike accordingly. If any part of this library ever
goes public, these files and their attribution ride along under that license.

Files written by `tools/wiki_mirror.py` store the page's **raw wikitext verbatim**
in a fenced block, so no fact is lost to summarising; rendered tables, images and
transcluded templates are not resolved. If a rendered snapshot is ever needed,
save the page via browser alongside.

## Mirrors

Written by `tools/wiki_mirror.py <Page>` (raw wikitext + provenance header);
the `## Digest` section under each header is hand-written — 3-8 lines saying what
the page claims that our docs use or contradict, and what to verify in code first.

| File | Page | Page version | Fetched | Topic |
|---|---|---|---|---|
| `nutrition.md` | [Nutrition](https://pzwiki.net/wiki/Nutrition) | 42.11.0 | 2026-09-09 | The weight model: bands, gain/loss thresholds and rates, macro ceilings |
| `nutritional-values.md` | [Nutritional values](https://pzwiki.net/wiki/Nutritional_values) | 42.20.0 | 2026-09-09 | Per-item calories/carbs/protein/fat table for every food |
| `food.md` | [Food](https://pzwiki.net/wiki/Food) | 42.20.0 | 2026-09-09 | Food overview + the rot/cook state machine + per-item hunger/thirst/mood tables |
| `cooking.md` | [Cooking](https://pzwiki.net/wiki/Cooking) | 42.18.0 | 2026-09-09 | Cooking skill: per-level ingredient use, evolved-recipe nutrition, poison thresholds |
| `modding.md` | [Modding](https://pzwiki.net/wiki/Modding) | 42.20.4 | 2026-09-09 | Modding hub: policy, fields, tool index, MP migration pointer |
| `startup-parameters.md` | [Startup parameters](https://pzwiki.net/wiki/Startup_parameters) | 42.20.4 | 2026-09-09 | Launcher/JVM/game arguments for client and server (test-harness input) |
| `appliances.md` | [Appliances](https://pzwiki.net/wiki/Appliances) | 42.8.0 | 2026-09-10 | B42 appliance tile catalogue; the Fridges table is the refrigeration roster (hardware only, no spoilage numbers) |
| `evolved-recipes.md` | [Evolved recipes](https://pzwiki.net/wiki/Evolved_recipes) | 41.78.19 | 2026-09-10 | How ingredients combine into dishes: per-recipe hunger values, spices, stale/rotten rules, B41 recipe roster |
| `fridge.md` | [Fridge](https://pzwiki.net/wiki/Fridge) | 41.78.19 | 2026-09-10 | The fridge/freezer spoil-rate multipliers and the B41 fridge variant list |
| `hungry.md` | [Hungry](https://pzwiki.net/wiki/Hungry) | 42.12.3 | 2026-09-10 | The Hungry/FoodEaten moodle: level thresholds, per-level penalties, the base hunger rate and its traits |
| `thirsty.md` | [Thirsty](https://pzwiki.net/wiki/Thirsty) | 42.12.3 | 2026-09-10 | The Thirst moodle: level thresholds, per-level penalties, the base thirst rate and its activity/trait modifiers |
| `moodle.md` | [Moodle](https://pzwiki.net/wiki/Moodle) | 42.13.2 | 2026-09-10 | Index of every moodle with a one-paragraph cause/effect summary; no thresholds or rates |
| `trait.md` | [Trait](https://pzwiki.net/wiki/Trait) | 42.20.4 | 2026-09-10 | Full trait roster with point costs and effects, plus the adaptive strength/fitness/weight band tables |
| `fitness.md` | [Fitness](https://pzwiki.net/wiki/Fitness) | 42.18.0 | 2026-09-10 | The Fitness skill: per-level endurance loss/recovery and combat multipliers, and the trait/occupation offsets |
| `mod-data.md` | [Mod data](https://pzwiki.net/wiki/Mod_data) | 42.13.1 | 2026-09-10 | Object vs global modData, and the page's claim that neither syncs automatically; `ModData.transmit` + `OnReceiveGlobalModData` is the only native sync it names |
| `networking.md` | [Networking](https://pzwiki.net/wiki/Networking) | 42.13.1 | 2026-09-10 | The command bus (`sendClientCommand`/`OnClientCommand`, `sendServerCommand`/`OnServerCommand`), the `isClient()`/`isServer()` gates, and the "server side handles most of the logic" statement |
| `lua-event.md` | [Lua event](https://pzwiki.net/wiki/Lua_event) | 42.20.4 | 2026-09-10 | `Events.<X>.Add/Remove`, and the boot-order list marking `OnCreatePlayer`/`OnGameStart`/`OnLoad` client-only and `OnServerStarted` server-only |
| `mod-structure.md` | [Mod structure](https://pzwiki.net/wiki/Mod_structure) | 42.20.0 | 2026-09-10 | The B42 `common/` + `42[.x[.y]]/` layout, the media subfolder taxonomy, and the page's stated load order (common first, then the closest version folder, which overwrites) |

**Absent pages:** "Food spoilage", "Canned food" and "Character stats" (all 404,
2026-09-10). Every other page requested up to 2026-09-10 fetched successfully; add a row
here (page name + date) when one 404s, so nobody re-tries blindly.

**Redirects, not mirrored:** "Refrigerator" and "Freezer" both redirect to
`Appliances#Refrigerators` and "Rotten" redirects to `Food`, so all three resolve to pages
already mirrored here — fetch `appliances.md` / `food.md` instead. Note the redirect anchor
is stale: the Appliances page's refrigeration section is headed `== Fridges ==` as of 42.8.0.
Likewise "Hunger" -> `Hungry`, "Thirst" -> `Thirsty`, "Moodles" -> `Moodle`,
"Weight" -> `Nutrition#Weight` and "Traits" -> `Trait` are redirects whose targets are all
mirrored here — fetch `hungry.md` / `thirsty.md` / `moodle.md` / `nutrition.md` / `trait.md`.

**Renames:** `modding-hub.md` became `modding.md` on 2026-09-09 when the hand
excerpt was re-fetched through `wiki_mirror.py` (the slug now follows the page
name). Its 42.20.x modding-news section is not on the live page any more; the
parts we rely on live in `docs/modding/README.md`, the rest in git history.

**Archived:** [modding-hub-archived.md](modding-hub-archived.md) — the pre-2026-09-09 excerpt of the Modding hub page, kept because its 42.20.x modding-news section is gone from the live page.
