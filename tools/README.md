# Tools

Builds on the pz-b42 toolchain (`C:\Users\Angus\pz-b42\tools\` — pzdis.py jar
disassembler + `pz.sh` wrapper, item/vehicle/tile scanners). Don't duplicate;
import patterns from there.

## Intake pipeline

- `wiki_mirror.py` — `python tools/wiki_mirror.py <Page> ["Another page" ...]`
  Fetches each PZwiki page as raw wikitext (curl with a browser UA — plain
  fetchers get 403) and writes `references/wiki-mirrors/<slug>.md`: provenance
  header (`**Source:**`, `**Fetched:**`, `**Wiki page version:**` from
  `{{Page version|X}}` or `unstamped`, `**License:**` CC BY-NC-SA 3.0), a
  `## Digest` stub reading `_digest pending_`, then `## Wikitext` with the raw
  text in a fence. Method rule 3 in STRATEGY.md: mirror, then digest by hand —
  the placeholder lint keeps an un-digested mirror visible until you do.
- `doc_lint.py` — `python tools/doc_lint.py [paths...]` (default: repo root)
  Prints `path:line: rule: detail` per finding, exits 1 if any. Rules:
  `stamp` (docs under `docs/vanilla`, `docs/modding`, `docs/feasibility`,
  `docs/mods-survey/teardowns` carry `Verified against: 42.20.4`),
  `placeholder` (`TODO`/`TBD`/`_digest pending_`), `sources` (a non-empty
  `## Sources` section in those same docs), `grades` (every body row of a
  table with an `Ev` column has a C/M/W evidence grade), `mirror-header`
  (the four header keys above, on every mirror). Skips `docs/superpowers/`,
  `docs/progress.md` and every `README.md`.

## Planned (P4)

- `food_scan.py` — every item with Food type across vanilla + workshop:
  HungerChange, Calories, Carbohydrates, Lipids, Proteins, ThirstChange,
  Unhappy/Boredom/Stress changes, DaysFresh/DaysTotallyRotten, Cooked/
  DangerousUncooked/Poison, FoodType, EvolvedRecipe roles, tags →
  `data/food-items.{json,csv}`. This dataset drives the full item pass.
- `evolved_recipes.py` — evolvedrecipe graph (base items, ingredients,
  nutrition math) → `data/evolved-recipes.json`.
- `mod_food_diff.py` — which installed mods add/override Food items (compat
  matrix for the item pass).

Conventions: stdlib-only python, same parser style as
`pz-b42/tools/insulation_scan.py` (proven against the generated-script DSL,
including capital-`Scripts` mod dirs and version-folder resolution).
