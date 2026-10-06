# Data

Generated datasets (do not hand-edit): food-items, recipes, evolved-recipes,
mod overlays. Regenerate with tools/ scanners. The **JSON** of a pair carries the
build it was generated from, in its `meta` block; the **CSV deliberately
carries no stamp row** — a `meta` line above the header would break every
`csv.reader` consumer — and is documented instead by its JSON twin's `meta`
and by this file (logged 2026-09-10, slice 05).

The column authority for every dataset below — what each column means, the
item kinds, the dated counts and the CSV and JSON schemas — is
[`docs/reference/datasets.md`](../docs/reference/datasets.md); this file keeps
each dataset's description, its regeneration command and its stamp rule, and
points at the section that owns the rest.

## food-items

`data/food-items.json` + `data/food-items.csv`, written by
`python tools/food_scan.py` from the 42.20.4 scripts under
`media/scripts/generated/`. Evidence grade **C** throughout: every value is a
line in a shipped script file, and every record names the file and line it
came from — bar the columns marked *derived* in [`datasets.md#schemas`](../docs/reference/datasets.md#schemas), which are arithmetic on
those lines (`C (arith.)`) and show their arithmetic. Nothing is measured,
inferred or defaulted here — the live checks are `testing/`, and a key a
script does not write has no value in this dataset.

- **The nutrition basis:** [`datasets.md#columns`](../docs/reference/datasets.md#columns).
- **The selection rule:** [`datasets.md#kinds`](../docs/reference/datasets.md#kinds).
- **CSV columns:** [`datasets.md#columns`](../docs/reference/datasets.md#columns); the full list, [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).
- **Per litre, not per item:** [`datasets.md#columns`](../docs/reference/datasets.md#columns); the drink probe that measured it, [`datasets.md#fidelity-links`](../docs/reference/datasets.md#fidelity-links).
- **JSON:** [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).

## food-nutrients

`data/food-nutrients.json` + `data/food-nutrients.csv`, written by
`python tools/food_nutrients.py --build` (Plan 6) from four committed inputs
and nothing else: `data/food-items.json`, the mapping
`data/food-nutrient-map/*.csv`, the extract `data/fdc-extract.json` and the
three side tables (`iodine-db-r4.csv`, `phytate-literature.csv`,
`insect-literature.csv`). It never opens the FDC zips under `tools/.fdc/`,
so a fresh clone rebuilds it. It refuses, writing nothing, unless
`--check-map` is clean, every `proxy` carries `notes`, every mapped row has
`portion_grams` and the extract holds every citation (else re-run
`--build-extract`).

`{"meta": {...}, "items": [...], "fluids": [...]}`, one record per dataset id
(items and fluids each sorted by id), `indent=1`, sorted keys, LF, byte-stable
within one UTC day (`meta.generated` is the UTC date).

**The record.** The mapping's cells (`family`, `fdc_id` as a string,
`fdc_source`, `fdc_description`, `confidence`, `state_baseline`,
`cook_retention_code` as an integer, `portion_grams`, `portion_source`,
`iodine_ref`, `phytate_source`, `no_nutrition_reason`, `notes`; an empty cell
is `null`), `kind`, and:

- `basis` — `per_item` (an item), `per_litre` (a fluid) or `none` (a
  `no_nutrition_reason` record, which carries no per-basis block);
- `per_100g` — the 31 `K.vector.KEYS` per 100 g in the units of
  `NR.data.UNITS` (`NR_Data_Nutrients.lua`): the SR Legacy amounts by identity
  unit, `iodine` from the iodine table, `phytate` the phytate table's dry-weight
  value × (100 − the entry's water) / 100 (`0` on a `zero:` row), or a
  literature row's dry matter × its dry-matter fraction; all `null` on a `none`
  record;
- `per_item` or `per_litre` — the same 31 keys, `per_100g × portion_grams / 100`
  (a fluid's `portion_grams` is the litre's mass), save two overrides named in
  `checks.notes`: a fluid's `ethanol` is its `alcohol` property × 789 g/L, and
  SimpleSyrup's `water` is its 1230 g litre less the 615 g of sugar;
- `vanilla` — the dataset's `calories`, `carbohydrates`, `lipids`, `proteins`,
  `hunger` and `thirst`, `null` where absent;
- `checks` — on `per_100g`, never clamping: `atwater_ratio` (fibre-aware
  4/2/4/9 plus 7 kcal/g ethanol over the entry's energy) and `atwater_outlier`
  (outside ±10 %, ±25 % where fibre is null, never flagged under 10 kcal),
  `proximate_sum` (water + proteins + lipids + carbs; over 102 is noted),
  `fibre_le_carb`, `retention_le_100` (every factor of the cited code; `null`
  with no code), `out_of_range` (the keys outside the tool's `SANITY_RANGES`),
  `energy_vs_fdc_ratio` (the per-basis energy over vanilla's calories, the
  re-base factor; `null` where vanilla has no positive calories) and `notes`.

Absence is `null` and never `0`, as in food-items.

**`meta`:** `build`, `jar_hash`, `generated`, `tool`, `sources` (the extract's,
with their sha256), `inputs` (the dataset's date and build, the mapping's
parts and row counts, the extract's date and counts, the side tables' row
counts) and `counts` — `items`, `fluids`, `by_kind`, `by_basis`, `mapped`,
`no_nutrition`, `by_confidence`, `by_fdc_source`, `by_state_baseline`,
`by_reason`, `by_portion_source` (`fdc_portion:<n>` counted as `fdc_portion`),
`cook_retention_set`, `cookable_without_code`, `atwater_checked`,
`atwater_outliers` with `atwater_outlier_ids`, `out_of_range` (per key) and
`out_of_range_records`, `proximate_over_102`, `fibre_over_carbs`,
`retention_over_100`, `rebase_factor_bands` (`<0.5`, `0.5-0.8`, `0.8-0.95`,
`0.95-1.05`, `1.05-1.25`, `1.25-2.0`, `>2.0`, `none`; lower bound inclusive),
`guesses` (the ids), `unmapped` and `orphan_mappings` (both `[]`).

**The CSV twin:** one row per record in the JSON's order, no stamp row. The
columns are the record's cells, `vanilla_<name>`, then the 31 per-basis values
under the bare key names (the `basis` column says per item or per litre), then
`p100_<key>` for `per_100g`, then the checks (`out_of_range` joined by `;`,
`check_notes` joined by ` | `). The mapping's free-text `notes` stays in the
JSON. Empty string for `null`, `true`/`false` for a boolean.

## recipes

`data/recipes.json` + `data/recipes.csv`, written by
`python tools/recipe_scan.py --out-dir data` from the 42.20.4 scripts under
`media/scripts/` — **one row per `craftRecipe` block**, 969 of them in 74
files, with its inputs and outputs parsed line by line. Evidence grade **C**
for everything read off a script line (every record names its
`sourceFile:sourceLine`); the `delta` block is `C (arith.)` — arithmetic on
those lines and on `data/food-items.json`, under a rule whose measured half is
`testing/artifacts/exp06b-20260910-120123/use-probe.json`. The mechanism, the
refusals and the live cross-check are
[`docs/facts/cooking-and-recipes.md#uses`](../docs/facts/cooking-and-recipes.md#uses);
the column authority is [`datasets.md#columns`](../docs/reference/datasets.md#columns).

`{"meta": {...}, "recipes": [...969...], "replacements": [...163...]}`,
`indent=1`, recipes sorted by `name`, LF endings, byte-stable across runs
**within one UTC day** — `meta.generated` is today's UTC *date*, so it is the
one line a rebuild after midnight UTC changes.

- **Input amounts and the delta:** [`datasets.md#columns`](../docs/reference/datasets.md#columns).
- **CSV columns:** [`datasets.md#columns`](../docs/reference/datasets.md#columns); the full list, [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).
- **JSON** (the record, `replacements` and `meta`): [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).

## evolved-recipes

`data/evolved-recipes.json` + `data/evolved-recipes.csv`, written by the same
run of `tools/recipe_scan.py` — **the 63 `evolvedrecipe` blocks** (62 in
`generated/evolvedrecipes.txt`, `AddBaitToChum` in
`generated/recipes/recipes_fishing_evolvedrecipe.txt`) resolved to their
ingredient lists the way the game resolves them, each ingredient carrying what
it contributes to the dish at Cooking **0** and Cooking **10**. Grade **C** for
the script values, `C (arith.)` for the two contribution blocks — the
summation itself is
[`docs/facts/cooking-and-recipes.md#evolved`](../docs/facts/cooking-and-recipes.md#evolved),
cited and not re-derived.

- **The join:** [`datasets.md#counts`](../docs/reference/datasets.md#counts); the mechanism, [`facts/cooking-and-recipes.md#evolved-join`](../docs/facts/cooking-and-recipes.md#evolved-join).
- **CSV columns:** [`datasets.md#columns`](../docs/reference/datasets.md#columns); the full list, [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).
- **JSON:** [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).

## mod-inventory

`data/mod-inventory.json`, written by `python tools/mod_inventory.py` from the
**installed workshop tree**
(`D:\SteamLibrary\steamapps\workshop\content\108600`, read and never written) —
one record per mod folder, a bare JSON array, `indent=1`. **230 records across
179 workshop items, swept 2026-09-10 17:47.** Evidence grade **C** for
everything read off a shipped file (`mod.info` values, file counts, regex hit
counts); nothing here is measured in a running game, and a signal count is a
count of regex hits, not of behaviour.

**No `meta` block, and no build stamp** — unlike the four datasets above, this
one describes a *live* tree that Steam rewrites under you (item `3490370700`
was rewritten mid-slice on 2026-09-10 at 13:47). **7 rows' `stats` moved
between the 09-09 and 09-10 sweeps, for two different reasons**: the two
`Skill Recovery Journal` rows (`2503622437`, `3782784855`) moved because the
resolution fix reads their `42.20.1/` folder where the old rule fell back to an
older one, and the other five (`3490370700` ×2, `3623584152`, `3703948448`,
`3745960616`) because Steam rewrote those items' files between the sweeps. Only
2 of the 7 are item `3490370700`. The sweep date above is the stamp; quote a
count from this dataset with it.

Regenerating is cheap (~2 s) and byte-stable:
the same tree in gives the same bytes out, LF-terminated on every platform
(the writer pins `encoding="utf-8", newline="\n"`, so the file no longer picks
up CRLF when it is generated on Windows — the committed blob was already LF,
`core.autocrlf` having normalised it, so this changed no committed byte).

- **The sweep-to-sweep differences:** [`datasets.md#mod-inventory`](../docs/reference/datasets.md#mod-inventory).
- **`mod_id` and the dated drift:** [`datasets.md#mod-inventory`](../docs/reference/datasets.md#mod-inventory).
- **Scope and the partial view** (`common/media`, `live_media`): [`datasets.md#mod-inventory`](../docs/reference/datasets.md#mod-inventory).
- **Fields** and the `workshop_item_mtime` caveat: [`datasets.md#mod-inventory`](../docs/reference/datasets.md#mod-inventory).
- **The two nutrition signals:** [`datasets.md#mod-inventory`](../docs/reference/datasets.md#mod-inventory).

## workshop-search

`data/workshop-search.json` + `data/workshop-search.csv`, written by
[`tools/workshop_search.py`](../tools/README.md) from the **public Steam
Workshop browse pages** — eight search terms against the `Build 42`-tagged,
ready-to-use section, one page per term (Steam serves 30 results a page and the
tool does not paginate), then a second pass over a declared subset of item
pages for size/posted/updated, joined to [§ mod-inventory](#mod-inventory) on
`workshop_id`. **212 results over 8 terms → 180 distinct items, 3 of them
installed, fetched 2026-09-10 16:26** (the run itself ran 16:25:31–16:26:22).
A `meta` block and a `results` array, `indent=1`; the CSV is the same 180 rows
flat, **10 columns** (`details_status` after `updated`), minus `grade` and
`unblock` — **14 500 bytes at 2026-09-10 16:56**, half the 30 427 of the first
encoding, which spent a 107-character sentence on each of 171 rows to say that
the row had not been asked for.

**Steam is live and `browsesort=trend` reorders hourly, so every count below
carries the fetch stamp and none of them is quotable without it.** Two browse
passes 34 minutes apart on 2026-09-10 — 15:52 and 16:26 — returned the same
212 / 180 / 3 and the same three installed ids, which says the answer held for
half an hour, not that it is stable. Nothing here was subscribed, downloaded
or written under the workshop root: pages were read once and never faster than
one request a second (browse pages 1 s apart, item pages 4 s), and only the
extracted facts (id, title, size, posted, updated) are recorded — no page is
mirrored.

Because a read may not land, the details pass
asks only for a **declared subset** (`meta.details_ids`) and a later
`--fill --include-not-requested [--fill-ids <ids|N>]` tops up
`not_requested` rows without re-sweeping — a re-sweep would change the
trend-sorted row set and the `meta.fetched` stamp with it.

- **The hard constraint: a Workshop row is not a measurable mod:** [`datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).
- **Per term (2026-09-10 16:26):** [`facts/other-mods/catalog.md#sweep`](../docs/facts/other-mods/catalog.md#sweep); the totals, [`datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).
- **The three installed hits (2026-09-10 16:26):** [`datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).
- **The load-bearing not-installed items (2026-09-10 16:26):** [`datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).
- **The six rows topped up at 16:56 (`meta.fill`):** the rows themselves in `data/workshop-search.json`; `meta.fill`, [`datasets.md#schemas`](../docs/reference/datasets.md#schemas).
- **The three row states, the fields and `meta`:** [`datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows); `meta`, [`datasets.md#schemas`](../docs/reference/datasets.md#schemas); the item-page read limit, [`datasets.md#open`](../docs/reference/datasets.md#open).

### workshop-catalog-details — the nine catalogued mods (2026-09-10 17:46)

`data/workshop-catalog-details.json`, written by
`python tools/workshop_search.py --catalog-ids <ids>` — the **same item-page
read as `--details`, for ids that are not sweep rows**. Eight of the nine mods
in [`docs/facts/other-mods/catalog.md#status`](../docs/facts/other-mods/catalog.md#status)
are returned by none of the eight search terms, so neither
`--details-ids` (which rejects an id the sweep did not return, on purpose) nor
`--fill` (which has no row to fill) can reach them, and the table's *Workshop
updated* column had nothing to put in it. This file is that column.

**One pass, 2026-09-10 17:46:08–17:46:49: 9 requested, 9 fetched, 0 failed, 0
incomplete**, 4 s apart, one retry per failure mode available and none needed.
Row shape — `workshop_id`, `title`, `size`, `posted`, `updated`,
`details_status`, `error`, **`fetched_at`** — and no `terms`, `installed`,
`mod_ids`, `grade` or `unblock`: no browse page returned these ids and nothing
here is joined to anything. `fetched_at` is per row because there is no browse
pass whose `meta.fetched` would cover them. Every reading is **W**: it is what
a Workshop page said at that minute.

- **The nine catalogued mods (2026-09-10 17:46):** [`facts/other-mods/catalog.md#status`](../docs/facts/other-mods/catalog.md#status); what the pass answers and its caveats, [`datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).
