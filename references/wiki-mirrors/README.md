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

**Absent pages:** none. Every page requested up to 2026-09-09 fetched successfully;
add a row here (page name + date) when one 404s, so nobody re-tries blindly.

**Renames:** `modding-hub.md` became `modding.md` on 2026-09-09 when the hand
excerpt was re-fetched through `wiki_mirror.py` (the slug now follows the page
name). Its 42.20.x modding-news section is not on the live page any more; the
parts we rely on live in `docs/modding/README.md`, the rest in git history.

**Archived:** [modding-hub-archived.md](modding-hub-archived.md) — the pre-2026-09-09 excerpt of the Modding hub page, kept because its 42.20.x modding-news section is gone from the live page.
