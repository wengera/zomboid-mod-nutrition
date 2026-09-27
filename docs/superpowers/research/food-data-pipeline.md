# The food-composition data pipeline for the item pass

Research report for the realism nutrition mod. Scope: where per-100 g values for calories, the four
macros, fibre, water and ~20 micronutrients come from, how cooking and canning losses are applied,
how ~700 generic game food names are mapped to a food-composition record, what the tool under
`tools/` looks like, and how the result is validated. Written 2026-09-27.

## How to read this

Every table row is marked with the kind of evidence behind it:

| grade | meaning |
|---|---|
| `LOCAL` | computed in this session directly from `data/food-items.csv` (the 2026-09-10 scan of `42.20.4`, jar `b0bbce05d5`) — reproducible from the committed file |
| `EXTRACT` | read in this session out of the actual downloaded dataset file, not off a web page |
| `HEAD` | the URL was requested in this session and its status and `Content-Length` recorded |
| `PAGE` | a statement quoted from a fetched page, not verified against the data itself |
| `LIT` | peer-reviewed literature, citation verified through Crossref or Europe PMC |
| `REPO` | a claim already in this library, cited by its register tag |

Nothing in this report is a register claim. It is a scoping document: the register rows get minted by
the commit that lands the pipeline and its extract, per CLAUDE.md § 4.

**The measured-not-quoted rule used here.** Every dataset size below is a `Content-Length` this
session recorded, not the number printed on the download page — the two disagree for FNDDS by a
factor of sixty, and the page is wrong. Every nutrient id, coverage count and retention factor below
was read out of the downloaded archive, not off a documentation page.

## Summary for the design

USDA FoodData Central is the right spine and **SR Legacy is the right table inside it**, not
Foundation Foods: SR Legacy carries all four macros plus energy and water on all 7 793 of its foods
and a target micronutrient on 5 000–7 700 of them, where Foundation Foods has only 469 foundation
records and puts energy on 135 of them. The whole SR Legacy CSV archive is a 5.8 MiB zip, CC0 public
domain, needs no API key, and ships the retention-factor code table inside it. The one nutrient it
lacks entirely is iodine: nutrient 314 is *defined* in its nutrient table and carries **zero** food
rows, so iodine must come from a second source — the USDA/FDA/ODS-NIH iodine database (478 foods,
per 100 g and per serving) or UK CoFID, which carries iodine natively. The USDA Table of Nutrient
Retention Factors Release 6 is available as a 7 018-row CSV on Ag Data Commons under CC0; it covers
270 food-group-by-method combinations across 13 SR food groups and **26** nutrients, and those 26 do
not include vitamin D, E, K, selenium, omega-3 or fibre, so for those nutrients the retention factor
has to be the literature or a flat assumption. The far better move for cooking is usually to skip
retention factors altogether: SR Legacy already holds 1 806 entries whose description says "cooked"
and 1 433 that say "raw", so a raw→cooked pair is normally a *measured* pair and retention factors
are the fallback for the pairs that do not exist. Canning is the same: 499 SR Legacy descriptions say
"canned", so a canned game item maps straight to the canned record and carries its loss already.

The game side constrains this harder than the data side. The engine applies **no** cooked, rotten,
frozen or stale modifier to the four macros — the only nutrition modifier in the whole game is a ÷5
for burnt [#0036, #0019] — and no game item is a separate "cooked" or "burnt" record: zero of the
722 food rows carry `Burnt`, `Cooked`, `Rotten` or `Overdone` in their name or display name, because
those are instance flags on one record. So a script override block can carry exactly one baseline
state per record, and every retention factor must be applied mod-side at eat time off `isCooked()`,
`isBurnt()`, the rot age and `isFrozen()`. The baseline to put in the block is the item's
as-spawned state: raw for raw meat, canned for the 41 `CannedFood` rows, dried for the 45 dried ones.

Mapping is the real cost. The 1 005 rows collapse to 855 distinct display names and the 722 food rows
to 613, with 81 names shared by two or more rows (`Berries` ×11, `Bottle` ×10, `Hot Drink` ×8), so the
mapping key must be the item id and never the display name. `FoodType` is nearly useless as a
classifier: 641 of the 1 005 rows write none at all, and one of its 44 values is literally
`NoExplicit`. Portion mass cannot be taken from the item's `Weight`: for ten foods sampled against
their SR Legacy counterpart, the implied portion mass agrees between all four macros to within 3 %
on six of them — Apple is exactly USDA's 182 g medium apple, Beef Jerky exactly 100 g, Watermelon
Slice 452 g — but the implied mass has no fixed relation to `Weight` (Rabbit Meat implies 850 g at a
0.3 kg weight, Canned Corn implies 143–488 g at a 0.8 kg weight), and four of the ten are internally
inconsistent between macros by 1.7× to 8.3×. So the pipeline must carry an explicit
`portion_grams` per mapping row, sourced from FDC's own portion table where one fits and stated as a
judgement where it does not, and must never derive it from `Weight`.

Validation has a cheap, powerful test already available: Atwater. Over the 597 per-item rows that
carry all four macros and a non-zero energy, the median of `(4C+4P+9F)/kcal` is **1.019** and 236 rows
sit within ±5 % — vanilla is broadly Atwater-consistent — but 217 rows are off by more than 25 %, 63
are below 0.5 and 53 above 2.0, and `Base.Ramen` declares 52 kcal against 166 kcal of macros. Those
outliers are exactly the rows where the vanilla number carries no information and the FDC value
should simply replace it.

Evolved dishes and fluids stay out of the composition table. A dish's macros are summed from its
ingredients at cook time by the engine's own evolved-recipe arithmetic, which this library already
measures, so the base bowl or pot carries only the vessel; and a fluid's nutrition is per litre, not
per item [#1881, #1891], so a drink's micronutrients belong on the 61 fluid definitions in a
per-litre table of their own and must never be added to a per-item number.

## A. Source candidates

### The FDC data types, measured

Every size below is a `Content-Length` measured this session. Note the two places the download page
misreports: it prints 200 M / 1.6 G for the FNDDS CSV (the file is 3.2 MiB) and 428 M for Branded CSV
(the file is 428 MiB — that one is right).

| Data type | Format | Release | measured zip | page says | Foods usable | Fit for this job | Grade |
|---|---|---|---|---|---|---|---|
| **SR Legacy** | CSV | 04/2018 (final) | **5.79 MiB** (6 074 592 B) | 6.7 M / 54 M | **7 793**, all with energy + 4 macros + water | **the spine.** Complete micronutrient panel, raw/cooked/canned entries, portion table, retention code table | `HEAD` `EXTRACT` |
| SR Legacy | JSON | 04/2018 | 12.83 MiB (13 456 312 B) | 12.3 M / 205 M | same | same data, larger | `HEAD` |
| Foundation Foods | CSV | 04/2026 | 3.65 MiB (3 825 741 B) | 3.7 M / 32 M | **469** `foundation_food` rows | too small; newer analytical values and the only USDA iodine in FDC, but 135 of the 469 carry energy 208 | `HEAD` `EXTRACT` |
| Foundation Foods | JSON | 04/2026 | 0.45 MiB (469 303 B) | 459 K / 6.5 M | 469 | same | `HEAD` |
| FNDDS (survey) | CSV | 10/2024 | **3.17 MiB** (3 325 692 B) | *200 M / 1.6 G* — wrong | ~7 000 survey codes | useful for **mixed dishes** (a "bowl of soup", "onion rings") where SR Legacy has no entry; recipe-level, portion-weighted | `HEAD` |
| Branded Foods | CSV | 04/2026 | 428 MiB (448 767 220 B) | 428 M / 2.9 G | ~1.9 M label rows | **avoid.** Label data, brand names, no micronutrients beyond the label panel, huge | `HEAD` |
| Full download (all types) | CSV | 04/2026 | 459 MiB (481 517 495 B) | 460 M / 3.1 G | all | unnecessary; SR Legacy + Foundation is 9.4 MiB | `HEAD` |

Recommended acquisition: **SR Legacy CSV + Foundation Foods CSV = 9.44 MiB of zip**, plus the iodine
database PDF. No API key, one `curl` each, both re-downloadable byte-identically because SR Legacy is
frozen at its final 2018 release.

### Licence

| Fact | Statement | Grade |
|---|---|---|
| Licence | CC0 1.0 Universal — the Ag Data Commons record for the retention factors carries `https://creativecommons.org/publicdomain/zero/1.0/` and access level `public` | `PAGE` |
| Public domain | "USDA FoodData Central data are in the public domain and they are not copyrighted"; no permission needed for use | `PAGE` |
| Request (not condition) | USDA *requests* that FoodData Central be listed as the source and, where possible, be notified of the product using it | `PAGE` |
| Suggested citation | "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, 2019. fdc.nal.usda.gov." | `PAGE` |
| Download page licence text | The download page itself carries **no** licence statement — the CC0 wording lives on the Ag Data Commons / data.gov records | `PAGE` |

CC0 means the extract can be committed into this repository and shipped inside the mod without
attribution obligation; the attribution goes in anyway, as provenance.

### Nutrient id conventions — the join trap

Read out of `nutrient.csv` in both archives. **There are two numbering systems and they are not
interchangeable.**

| Column | What it is | Example |
|---|---|---|
| `nutrient.id` | FDC's own internal nutrient id — **this is the key `food_nutrient.nutrient_id` joins on** | `1008` |
| `nutrient.nutrient_nbr` | the legacy NDB/SR nutrient number everyone quotes | `208` |

Joining `food_nutrient` on `208` returns nothing. The pipeline must build the
`nutrient_nbr → id` map from `nutrient.csv` first. `nutrient.csv` holds **477** rows in the
Foundation archive.

The 22 target nutrients, with the row each one needs, and coverage measured over SR Legacy's 7 793
foods and over Foundation's 469 `foundation_food` rows (`EXTRACT`):

| Target | `nutrient_nbr` | `nutrient.id` | unit | SR Legacy foods | Foundation foods | note |
|---|---|---|---|---|---|---|
| Energy | 208 | 1008 | kcal | **7 793** | 135 | Foundation prefers 957 (Atwater general, 347 rows) / 958 (specific, 312) |
| Protein | 203 | 1003 | g | **7 793** | 425 | |
| Total fat | 204 | 1004 | g | **7 793** | 413 | |
| Carbohydrate, by difference | 205 | 1005 | g | **7 793** | 377 | 205.2 "by summation" on 47 Foundation rows |
| Fibre, total dietary | 291 | 1079 | g | 7 231 | 241 | AOAC 2011.25 variant is 293 (309 rows, Foundation only) |
| Water | 255 | 1051 | g | **7 793** | 460 | the hydration input |
| Vitamin A, RAE | 320 | 1106 | µg | 6 918 | 79 | 318 (IU) on 7 356 SR rows — **the retention table uses 318 and 392, not 320** |
| Thiamin (B1) | 404 | 1165 | mg | 7 402 | 229 | |
| Riboflavin (B2) | 405 | 1166 | mg | 7 421 | 208 | |
| Niacin (B3) | 406 | 1167 | mg | 7 402 | 240 | |
| Vitamin B6 | 415 | 1175 | mg | 7 262 | 270 | 411–414 are vitamers, 0 rows |
| Folate, total (B9) | 417 | 1177 | µg | 6 851 | 172 | DFE (435) has **0** rows in either archive |
| Vitamin B12 | 418 | 1178 | µg | 7 113 | 94 | |
| Vitamin C | 401 | 1162 | mg | 7 332 | 140 | |
| Vitamin D (D2+D3) | 328 | 1114 | µg | 5 185 | 63 | 324 is the same value in IU |
| Vitamin E (α-tocopherol) | 323 | 1109 | mg | 5 580 | 87 | |
| Vitamin K (phylloquinone) | 430 | 1185 | µg | 5 054 | 94 | MK-4 (428) and dihydro (429) are separate rows |
| Sodium | 307 | 1093 | mg | 7 709 | 403 | |
| Potassium | 306 | 1092 | mg | 7 516 | 439 | |
| Calcium | 301 | 1087 | mg | 7 708 | 439 | |
| Magnesium | 304 | 1090 | mg | 7 421 | 439 | |
| Iron | 303 | 1089 | mg | 7 713 | 439 | heme/non-heme split (364/365) has 0 rows |
| Zinc | 309 | 1095 | mg | 7 406 | 439 | |
| **Iodine** | **314** | **1100** | µg | **0** | **55** | defined but empty in SR Legacy — see below |
| Selenium | 317 | 1103 | µg | 6 865 | 193 | |
| Omega-3 ALA (18:3 n-3) | 851 | 1404 | g | 1 967 | 90 | 619 "PUFA 18:3" (unspecified isomer) on 6 940 SR rows is the wider column |
| Omega-3 EPA (20:5 n-3) | 629 | 1278 | g | 5 800 | 90 | |
| Omega-3 DHA (22:6 n-3) | 621 | 1272 | g | 5 772 | 90 | |
| Choline (bonus) | 421 | 1180 | mg | 4 611 | 211 | the only "extra" the retention table covers |

Two conventions worth pinning: **omega-3 needs three columns summed**, and for a plant food only
851/619 will be present while for a fish all three will; and **vitamin A must be chosen once** —
320 (RAE, modern) for the nutrition model, but 318 (IU) or 392 (RE) if a retention factor is to be
applied, because those are the two the retention table indexes.

### The iodine gap — verified, and where to fill it

| Finding | Value | Grade |
|---|---|---|
| SR Legacy iodine | nutrient 314 **is** in `nutrient.csv`, and `food_nutrient.csv` carries **0** rows for it over 7 793 foods | `EXTRACT` |
| Foundation Foods iodine | 592 rows across all food records in the archive, of which **55** are on the 469 `foundation_food` rows | `EXTRACT` |
| The dedicated USDA source | *USDA, FDA and ODS-NIH Database for the Iodine Content of Common Foods*, Release 4 (Oct 2024): **478 foods**, values per 100 g **and** per serving | `PAGE` |
| Its format | PDF only (`IODINE_DATABASE_RELEASE_4_PER_100G.pdf`, 349 KiB, HTTP 200) — no CSV published | `HEAD` |
| Its join key | the PDF's first columns are `DB_ID`, SR/Foundation reference, **FDC id** and NDB No., so it joins to SR Legacy by NDB number | `PAGE` |
| UK CoFID iodine | carried natively; the 2021 release notes list an iodine correction among its changes | `PAGE` |

**Recommendation:** iodine values for the ~40 game foods where iodine actually matters (dairy, eggs,
fish, seaweed, iodised salt, bread) come from the iodine database, transcribed by hand into the
mapping CSV with a `source = iodine-db-r4` marker. It is 478 foods in a PDF; a hand transcription of
40 rows is cheaper and more auditable than a PDF-scrape tool, and iodine is near-zero in almost
everything else.

### Alternatives — only where USDA lacks something

| Source | Adds what USDA lacks | Size / format | Licence | Verdict | Grade |
|---|---|---|---|---|---|
| **USDA/FDA/ODS-NIH Iodine DB r4** | **iodine**, 478 foods per 100 g and per serving | PDF, 349 KiB | US federal, public domain | **take it** — the only USDA route to iodine | `HEAD` `PAGE` |
| **UK CoFID 2021** | iodine natively; ~3 300 UK foods; useful for British-coded foods | XLSX, **4.41 MiB** (4 629 542 B) | **Open Government Licence v3.0** — attribution required | take as **iodine cross-check only**; OGL attribution is a real (small) obligation CC0 does not impose, and the food codes do not join to FDC | `HEAD` `PAGE` |
| Canadian Nutrient File 2015 | a second iodine-bearing table; 5 relational + 7 support files, CSV/XLSX/Access | zip, not measured | Crown copyright — free use, **Health Canada must be named as source** | skip unless CoFID and the iodine DB both miss a food | `PAGE` |
| FAO/INFOODS | regional tables, biodiversity foods | per-table | varies per table | skip — no single joinable dataset; its value here is the *insect* literature instead | `PAGE` |
| Rumpold & Schlüter 2013 | **insects** — 236 nutrient compositions; energy 426.3 kcal/100 g for grasshoppers/locusts/crickets to 508.9 for caterpillars | journal article | © Wiley — numbers are facts, transcribe values not text | **take it** for the 20 `Insect` `FoodType` rows; FDC has **zero** entries matching cricket, insect, grasshopper, mealworm or earthworm | `LIT` `EXTRACT` |

### API key

| Fact | Value | Grade |
|---|---|---|
| Bulk downloads | **no key, no registration** — a plain HTTPS GET; all seven URLs returned HTTP 200 this session | `HEAD` |
| API (`/foods/search` etc.) | "A data.gov API key must be incorporated into each API request" | `PAGE` |
| API rate limit | default **1 000 requests/hour per IP**; `DEMO_KEY` is 30/hour and 50/day | `PAGE` |
| Endpoints | `/food/{fdcId}`, `/foods`, `/foods/list`, `/foods/search` | `PAGE` |

For this job: **use the bulk download, never the API.** ~700 mappings at 1 000 req/h would be a
key-bound, unreproducible, rate-limited build step, where the zip is 5.8 MiB and frozen.

## B. Retention factors and the game's states

### The USDA table, measured from the CSV

| Fact | Value | Grade |
|---|---|---|
| Release | Release 6 (2007), replacing Release 5 (2003) | `PAGE` |
| Formats | `retn06.pdf` (126 629 B at ars.usda.gov, HTTP 200), `NutrientRetention.csv`, `NutrientRetentionDD.csv` (data dictionary) | `HEAD` `EXTRACT` |
| CSV shape | 7 018 data rows, 7 columns: `Retn_Code, FdGrp_CD, RetnDesc, Nutr_No, NutrDesc, Retn_Factor, Date` | `EXTRACT` |
| Coverage | **270** distinct retention codes × **26** nutrients | `EXTRACT` |
| Food groups | **13** SR food-group codes: 1 Dairy & Egg, 5 Poultry, 8 Breakfast Cereals, 9 Fruits, 10 Pork, 11 Vegetables, 12 Nut & Seed, 13 Beef, 14 Beverages, 15 Finfish & Shellfish, 16 Legumes, 17 Lamb/Veal/Game, 20 Cereal Grains & Pasta | `EXTRACT` |
| Factor units | integer percent, range **10–100** | `EXTRACT` |
| Also shipped | the *code* table (270 rows: code, food group, description) is inside the SR Legacy CSV zip as `retention_factor.csv` — **the factor values are not**; only the PDF and the Ag Data Commons CSV carry the numbers | `EXTRACT` |
| Licence | CC0 1.0 | `PAGE` |

**What the 26 nutrients are** (`EXTRACT`): 221 alcohol; minerals 301 Ca, 303 Fe, 304 Mg, 305 P,
306 K, 307 Na, 309 Zn, 312 Cu; vitamin A as 318 (IU) and 392 (RE) plus carotenoids 321, 322, 334,
337, 338; and the water-solubles 401 vitamin C, 404 thiamin, 405 riboflavin, 406 niacin, 415 B6,
417 folate total, 418 B12, 421 choline, 431 folic acid, 432 food folate.

**What it does not cover — and this is the important gap:** vitamin D, vitamin E, vitamin K,
selenium, iodine, omega-3 fatty acids, fibre and water. Eight of the 22 targets have no USDA
retention factor at all. For fat-soluble vitamins and minerals not listed, the physical justification
for assuming ~100 % retention with a leaching term is good (they are not heat-labile); for omega-3
the loss is oxidative and method-specific and no table covers it.

### Methods covered

Counting the last comma-field of each of the 270 descriptions (`EXTRACT`), the method vocabulary is:
`REHEATED` 27, `W/DRIPPINGS` 21, `WO/DRIPPINGS` 17, `W/DRIP` 17, `WO/DRIP` 17, `BROILED` 13,
`BAKED` 11, `FRIED` 10, `ROASTED` 8, `WATER USED` 8, `DRAINED` 7, `W/COATING` 6, `WO/COATING` 6,
`SAUTEED` 6, `STEAMED` 5, `COOKED` 4, `STIR FRY` 3, `BOILED+BAKED` 3, `BOILED+FRIED` 3, `STEWED` 2,
`CANNED` 1, `DRIED` 1, `FROZEN` 1, plus the singletons (`POACHED`, `HARD COOKED`,
`MILK,HEATED APPROX 1 HOUR`, `BOILED IN SKIN`, …).

The important distinction the table encodes and a naive model misses: **`WATER USED` vs `DRAINED`**.
Boiling and keeping the water retains the leached minerals and water-solubles; draining loses them.
The vegetable group alone carries both variants for greens, roots and "other" — e.g.
`VEG,ROOTS,ETC,BLD,DRAIND,WTR COVER` vs `VEG,ROOTS,ETC,BOILED,WATER USED`. A game that models a
stew (water kept) differently from boiled-and-drained vegetables gets this for free.

### Worked factors, read out of the CSV

| code | description | vit C | B1 | B2 | B3 | B6 | folate | vit A (IU) | Ca | K | Fe |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 154 | `FRUITS,CANNED` | **50** | **80** | 90 | 90 | 90 | **50** | 75 | 95 | 90 | 100 |
| 3371 | `POTATOES,CANNED,BOILED,WATER USED` | 85 | 90 | 100 | 100 | 100 | 95 | — | — | — | — |
| 3375 | `POTATOES,CANNED,FRIED` | 85 | 90 | 100 | 100 | 100 | 95 | — | — | — | — |

Alcohol retention (nutrient 221) is its own usable ladder for a cooking mod (`EXTRACT`):

| code | description | alcohol retained |
|---|---|---|
| 5002 | `ALC BEV,STIRRED INTO HOT LIQ` | 85 % |
| 5003 | `ALC BEV,FLAMED` | 75 % |
| 5001 | `ALC BEV,NO HEAT,STORED OVERNIGHT` | 70 % |
| 5010 | `ALC BEV,NOT STIRRED IN,BKD 25 MIN` | 45 % |
| 5004 | `ALC BEV,STIRRED,BKD/SIMMRD 15 MIN` | 40 % |
| 5005 | `ALC BEV,STIRRED,BKD/SIMMRD 30 MIN` | 35 % |
| 5006 / 5007 / 5008 | stirred, baked/simmered 1 h / 1.5 h / 2 h | 25 % / 20 % / 10 % |

**A defect in the CSV to guard against.** On code `5005` alone, 24 of its 26 rows carry the string
`Sep-75` in the `Retn_Factor` column and an empty `Date` — a one-column shift. Every other row in the
file has `Retn_Factor` as an integer and `Date` as `Sep-75`. So **24 of 7 018 factors are lost in the
CSV** and must be read from `retn06.pdf` (they are all 100, the alcohol row at 35 being the only real
number on that code). The pipeline's loader must reject a non-integer `Retn_Factor` loudly rather
than coercing it, and the test surface must assert exactly 24 such rows so a silently repaired
upstream file is noticed (`EXTRACT`).

### Canning losses from the literature

| Claim | Value | Grade | Citation |
|---|---|---|---|
| Canning's thermal step is where water-soluble and oxygen-labile nutrient loss happens; canned storage is then *relatively stable* because there is no oxygen | qualitative, and the load-bearing structural point | `LIT` | Rickman, Barrett & Bruhn 2007, *J Sci Food Agric* 87:930–944, doi:10.1002/jsfa.2825 (abstract verified via Europe PMC) |
| Thiamin loss from canning | **7–70 %** across vegetables, commodity-dependent | `PAGE` (secondary report of the above) | as above |
| Frozen products lose fewer nutrients initially (short blanch) but more in storage, by oxidation | qualitative | `LIT` | as above |
| Part 2 covers vitamin A/carotenoids, vitamin E, minerals and fibre | companion paper | `LIT` | Rickman, Bruhn & Barrett 2007, *J Sci Food Agric* 87:1185–1196, doi:10.1002/jsfa.2824 |
| USDA's own canned-fruit factors | vit C **50 %**, folate **50 %**, thiamin 80 %, riboflavin/niacin/B6 90 %, vitamin A 75 % | `EXTRACT` | retention code 154 |

The USDA factor (vit C 50 %, thiamin 80 %) sits inside the literature's range and is machine-readable
and self-consistent. **Use USDA code 154 / 3371 as the canning numbers and the Rickman reviews as the
justification and the uncertainty band**, not the other way round.

### How a loss is applied given the game's states — the constraint that decides the design

| Game fact | Consequence for the pipeline | Grade |
|---|---|---|
| The engine applies **no** cooked, burnt, rotten or frozen modifier to calories, carbohydrates, lipids or proteins — they are bare field reads [#0036] | a script block carries **one** composition per record; there is no second "cooked" block to write | `REPO` |
| The **only** nutrition modifier in the game is `Eat`'s **÷5 for burnt** [#0019] (apple 95→19, steak 220→44, bread 532→106.4, carrots 25→5) | burnt is already punitive on macros; a mod's own burnt factor for micronutrients must be chosen knowing the macros are already ÷5 | `REPO` |
| Hunger *is* state-modified: cooked ×1.3 beats burnt ÷3, stale ÷1.3, rotten ÷2.2 [#0029–#0032]; thirst runs the opposite precedence, burnt ÷5 beating cooked ÷2 [#0033, #0034] | the mod's own retention ladder should mirror this precedence shape so the two feel consistent | `REPO` |
| `cookingTime`, `heat`, `cooked` and `burnt` are instance fields driven only by `Food.update` [#0202]; frozen/burnt/rotten are three independent axes [#0204] | retention is a runtime multiply on the mod's stored per-item micronutrient vector, keyed on the instance's flags | `REPO` |
| **Zero** of the 722 food rows carry `Burnt`, `Cooked`, `Rotten` or `Overdone` in name or display name | confirms the above from the data side: no record to attach a cooked composition to | `LOCAL` |
| 41 rows are `CannedFood = true`, 21 of them also `CantEat` (sealed) | the canned rows' **baseline** is the canned composition — losses already applied, no runtime factor | `LOCAL` `REPO` [#0312] |
| 45 rows say "Dried" in the display name, 34 in the internal name | same: dried is the baseline, not a runtime state | `LOCAL` |
| 257 rows are `IsCookable = true`; 81 `DangerousUncooked`; 148 `GoodHot`; 50 `CantBeFrozen` | 257 records need a cooked-state retention row; the rest never cook | `LOCAL` |

**The resulting state model.** Per food record the pipeline emits one baseline vector (the as-spawned
state) plus, on the 257 cookable records, one `cook_retention` code naming the retention row to apply
at eat time. The mod then applies, at eat time:

| state | macros | micronutrients | basis |
|---|---|---|---|
| raw / as-shipped | the script block's values | the baseline vector | the record |
| cooked | unchanged by the engine | × the record's `cook_retention` factors (USDA, per nutrient) | USDA R6 |
| burnt | ÷5 by the engine | × a flat punitive factor (proposal: the cooked factor squared, floored) — **no USDA row covers burning** | a mod judgement, labelled as such |
| rotten | unchanged by the engine | × a decay factor on vitamin C, folate and thiamin only — **no USDA row covers spoilage** | a mod judgement |
| frozen | unchanged by the engine | ~100 %, with a small vitamin C term over long storage | Rickman 2007's frozen-storage oxidation finding |
| canned (as shipped) | the script block's values, already canned | the baseline **is** the canned record — no runtime factor | SR Legacy's 499 canned entries, or code 154 |

Two of those six rows are mod judgements with no data behind them. They must be written as such in
the tool's own comment block, and never presented as USDA numbers.

## C. Mapping strategy

### What is actually being mapped — measured

| Fact | Value | Grade |
|---|---|---|
| Rows in `data/food-items.csv` | **1 005** (header + 1 005 = 1 006 lines), 61 columns | `LOCAL` [#0639] |
| Kinds | `food` **722**, `drainable` **150**, `fluid_container` **133**; plus 61 `fluid` records in the JSON only | `LOCAL` [#1882] |
| Nutrition basis | `per_item` **653**, `per_litre` **72**, empty **280** | `LOCAL` [#1884] |
| Rows with no nutrition value at all (14 nutrition columns + 6 per-container) | **290** — 141 drainable, 78 food, 71 fluid_container | `LOCAL` [#0625] |
| Food-kind rows carrying per-item nutrition | **644** of 722 | `LOCAL` |
| Drainables carrying any nutrition column | **9**, and only `Base.Vinegar2` / `Base.Vinegar_Jug` carry `Calories` (both `0.0`) | `LOCAL` [#0612] |
| Distinct display names over all 1 005 rows | **855** | `LOCAL` |
| Names shared by ≥2 rows | **81** names covering **231** rows — `Berries` ×11, `Bottle` ×10, `Hot Drink` ×8, `Mushrooms` ×8, `Rice` ×8, `Caterpillar` ×6, `Pasta` ×5, `Bucket`/`Canteen`/`Mug`/`Juice Box` ×4 | `LOCAL` |
| Rows with no EN display name | **6** | `LOCAL` [#0606, #1430] |
| Distinct `FoodType` values | **44** — but **641** of 1 005 rows write none, and one value is literally `NoExplicit` (49 rows) | `LOCAL` |
| `spice = true` | **111** | `LOCAL` |
| `CantEat = true` among food rows | **96** | `LOCAL` |
| Rows carrying an `EvolvedRecipe` key | **374** | `LOCAL` [#0724] |
| Distinct macro tuples over the 644 per-item food rows | **342**; 109 tuples shared by >1 row, covering **411** rows. Largest: the empty tuple (47 rows), `(0.1, 0, 0, 0)` (37 — herbs), `(159, 1, 1, 35)` (20) | `LOCAL` |

**So the real mapping workload is not 700 rows, it is ~342 compositions.** The 644 per-item food rows
collapse to 342 distinct macro tuples, and the shared-tuple families are exactly the mod-relevant
equivalence classes (37 dried herbs all at 0.1 kcal; 20 items at `(159, 1, 1, 35)`). Map the family,
not the row.

### The mapping CSV

`data/food-nutrient-map.csv`, hand-curated, the **only** hand-edited file in the pipeline. One row
per game item id — **never keyed on display name**, which is ambiguous on 231 rows.

| Column | Type | Meaning |
|---|---|---|
| `pz_id` | string | `Base.Apple` — the join key, exactly `food-items.csv`'s `id` |
| `pz_display` | string | copied in for human review only; never read by the tool |
| `pz_kind` | string | `food` / `drainable` / `fluid_container` / `fluid` — copied in, and the tool asserts it matches |
| `fdc_id` | int or empty | the SR Legacy / Foundation `fdc_id`. Empty **only** when `no_nutrition_reason` is set |
| `fdc_source` | enum | `sr_legacy` / `foundation` / `fndds` / `iodine_db_r4` / `cofid` / `literature` / `derived` |
| `fdc_description` | string | the FDC description verbatim, so a wrong mapping is visible in review |
| `confidence` | enum | `exact` / `close` / `proxy` / `guess` — see the rubric below |
| `portion_grams` | float or empty | the mass the script block's numbers describe. **Never** derived from `Weight` |
| `portion_source` | enum | `fdc_portion:<seq>` / `fdc_100g` / `vanilla_implied` / `judgement` |
| `cook_retention_code` | int or empty | a `Retn_Code` from `NutrientRetention.csv`, set only where `IsCookable` is true |
| `state_baseline` | enum | `raw` / `cooked` / `canned` / `dried` / `frozen` / `prepared` — which state the emitted numbers are |
| `no_nutrition_reason` | enum or empty | why this row carries no composition — see the taxonomy below |
| `notes` | string | free text; where a `guess` explains itself |

### The confidence rubric

| `confidence` | Rule | Example | Count expectation |
|---|---|---|---|
| `exact` | the FDC description names the same food in the same state, and the vanilla macros already imply a single consistent portion mass across all four | `Base.Apple` → 171688 *Apples, raw, with skin*; four macros imply 181–183 g | the generic produce, most meats |
| `close` | same food, a defensible cultivar/cut/brand substitution | `Base.Crisps` → 169677 *Snacks, potato chips, plain, salted*; `Base.Baguette` → 172675 *Bread, french or vienna* | most manufactured foods |
| `proxy` | a different food standing in for one FDC does not carry | `Base.Venison` → 173855 *Game meat, deer, raw*, used for every deer product; `Base.Rabbitmeat` → 174347 *rabbit, wild, raw* | the game meats, the fictional items |
| `guess` | no defensible FDC entry; the number is a judgement | `Base.Cricket`, `Base.Worm` (literature), the herbs at `0.1` kcal | ≤ 40 rows; every one must carry a `notes` |

A `guess` row is a design decision, not data. The tool must emit their count and the coverage test
must assert it does not grow silently.

### The no-nutrition taxonomy

Every one of the 290 zero-nutrition rows and the 96 `CantEat` rows needs a named reason, or the
coverage test fails.

| `no_nutrition_reason` | Meaning | Examples | Approx count |
|---|---|---|---|
| `not_food` | a drainable or container that is not consumable at all | `Base.PaintWhite`, `Base.Wire`, `Base.Wallpaper_PinkFloral`, `Base.BucketPlasterFull` | ~135 of the 141 drainables |
| `empty_container` | a `fluid_container` listing no fluid | `Base.MetalCup`, `Base.ClayJar`, `Base.Kettle_Copper` | 61 |
| `fluid_sourced` | nutrition lives on the fluid, per litre | `Base.Brandy`, `Base.PopBottle`, `Base.Milk` | 72 |
| `inedible_body_part` | a butchery/animal record the player cannot eat | `Base.Raccoon_Boar_Head`, `Base.CorpseAnimal`, the 3 `Bull Head` / `Cow Head` rows | ~20 of the 78 food rows |
| `hazard` | consumable but not food; belongs to the poison model, not the nutrition model | `Base.Bleach` (a fluid container), `Base.RatPoison`, `Base.CorrectionFluid` | ~8 |
| `vessel_only` | an evolved-dish base whose composition is summed at cook time | `Base.SoupBowl`, `Base.RicePot`, the 12 `Bowl`-named and 24 `Pot`-named rows | ~50 |
| `spice_only` | `Spice = true`; carries flavour, not nutrition worth modelling | 111 rows, 48 of them `FoodType = Herb` | 111 |
| `tobacco_or_drug` | a drainable consumed but not eaten | `Base.CigarettePack`, `Base.TobaccoChewing`, `Base.PillsVitamins` | ~6 |

Note `Base.Bleach` is a `fluid_container` whose fluid writes `ThirstChange = -20.0` per litre and no
macro key at all — it is already correctly absent from the nutrition columns, and the mapping row
should say `hazard`, not leave it blank (`LOCAL`).

### Portion weight — do not use `Weight`

The decisive measurement. For each of ten sampled foods, the game's four macros were divided by the
matched SR Legacy per-100 g value to get the portion mass each macro implies (`LOCAL` + `EXTRACT`):

| game id | display | `Weight` kg | SR Legacy entry | vanilla kcal/C/P/F | implied g from kcal | from C | from P | from F | spread |
|---|---|---|---|---|---|---|---|---|---|
| `Base.Apple` | Apple | 0.2 | 171688 Apples, raw, with skin | 95 / 25.13 / 0.47 / 0.31 | 183 | 182 | 181 | 182 | **1.0×** |
| `Base.BeefJerky` | Beef Jerky | 0.2 | 167536 Snacks, beef jerky, chopped and formed | 410 / 11 / 33 / 26 | 100 | 100 | 99 | 102 | **1.0×** |
| `Base.Rabbitmeat` | Rabbit Meat | 0.3 | 174347 Game meat, rabbit, wild, raw | 969 / 20 / 185 / 20 | 850 | — | 849 | 862 | **1.0×** |
| `Base.FrogMeat` | Frog Meat | 0.2 | 168148 Frog legs, raw | 66 / 0 / 14.6 / 0.28 | 90 | — | 89 | 93 | **1.0×** |
| `Base.Butter` | Butter | 0.3 | 173410 Butter, salted | 3200 / 0 / 0 / 352 | 446 | — | — | 434 | **1.0×** |
| `Base.WatermelonSliced` | Watermelon Slice | 0.3 | 167765 Watermelon, raw | 135.5 / 34.11 / 2.75 / 0.67 | 452 | 452 | 451 | 447 | **1.0×** |
| `Base.PeanutButter` | Peanut Butter | 0.3 | 174266 Peanut butter, smooth, w/ salt | 2660 / 128 / 84 / 224 | 445 | 574 | 378 | 436 | 1.5× |
| `Base.Chocolate` | Milk Chocolate Bar | 0.2 | 167587 Candies, milk chocolate | 850 / 110 / 10 / 66 | 159 | 185 | 131 | 223 | 1.7× |
| `Base.Baguette` | Baguette | 0.3 | 172675 Bread, french or vienna | 532 / 99 / 17.7 / 6.66 | 196 | 191 | 165 | 275 | 1.7× |
| `Base.Crisps` | Chips - Plain | 0.2 | 169677 Snacks, potato chips, plain, salted | 720 / 72 / 4.5 / 45 | 135 | 134 | 70 | 132 | 1.9× |
| `Base.Venison` | Venison | 0.5 | 173855 Game meat, deer, raw | 440 / 0 / 62.62 / 18.7 | 367 | — | 273 | 773 | 2.8× |
| `Base.CannedCorn` | Canned Corn | 0.8 | 169214 Corn, sweet, yellow, canned, drained | 315 / 70 / 7 / 1.75 | 470 | 488 | 306 | 143 | **3.4×** |
| `Base.Ramen` | Dry Ramen Noodles | 0.2 | 171177 Soup, ramen noodle, any flavor, dry | 52 / 0 / 10 / 14 | 12 | — | 98 | 80 | **8.3×** |

Three findings, all load-bearing:

1. **Six of thirteen are internally exact.** `Base.Apple` is USDA's 182 g medium apple copied
   verbatim; `Base.BeefJerky` is exactly one 100 g SR Legacy serving; `Base.Butter` is a 445 g
   (1 lb) pack; `Base.WatermelonSliced` is 452 g. Vanilla was partly built from USDA per-portion
   numbers, so **the vanilla macros are a usable prior and a usable portion oracle** on those rows.
2. **`Weight` is not the portion mass.** `Base.Rabbitmeat` implies 850 g at a 0.3 kg weight (2.8×);
   `Base.CannedCorn` implies 143–488 g at 0.8 kg; the apple's 182 g against 0.2 kg is a coincidence
   of scale, not a rule. Deriving `portion_grams` from `Weight` would corrupt every meat row.
3. **Four rows are internally impossible** and their vanilla numbers carry no information.
   `Base.Ramen` declares 52 kcal against 0 C / 10 P / 14 F = 166 kcal. Those rows get
   `portion_source = judgement` and the FDC value replaces the vanilla one outright.

**The portion rule, in order:**

1. If the four vanilla macros imply one consistent mass (spread ≤ 1.1×), use it —
   `portion_source = vanilla_implied`. It is the game's own intent and it round-trips.
2. Else, if an FDC `food_portion` row matches the item's evident serving, use its `gram_weight` —
   `portion_source = fdc_portion:<seq_num>`. SR Legacy carries 14 449 portion rows over 7 533 of its
   7 793 foods, mostly as an `amount` + a `modifier` string (`1 bar (1.55 oz) = 44 g`,
   `1 medium (3" dia) = 182 g`), with `measure_unit` usually `undetermined` — so the modifier string
   is the label, and it must be recorded, not parsed (`EXTRACT`).
3. Else state a mass as `judgement` with a `notes`.

### Evolved-recipe dishes

`374` rows carry an `EvolvedRecipe` key and there are 63 evolved recipes over 6 881 ingredient rows
[#0724, #1910]. The engine sums a dish's macros from its ingredients at cook time, with a Cooking-skill
share (`share10` is exactly 0.7 × `share0` on all 6 881 rows [#1911]) and a clamp. **Do not give an
evolved dish a composition.** Its base item — `Base.SoupBowl`, `Base.RicePot`, `Base.RamenBowl` —
gets `no_nutrition_reason = vessel_only`, and the mod's micronutrient vector for a dish is summed
from the same ingredient shares the engine already uses for macros, so the two can never diverge. The
12 `Bowl`-named, 24 `Pot`-named and 16 `Pan`-named rows are where to look for these. Note the
duplicate-name trap: `Base.SoupBowl` and `Base.SoupBowlClay` are two rows with the same display name
and identical macros (`LOCAL`).

### Fluids — per litre, never per item

72 container rows carry `per_litre` nutrition joined from the first of their listed fluids, and 61
fluid definitions exist of which 51 write a `Properties` block [#0614, #0623, #1886]. Three
consequences for the mapping:

- The micronutrient table for drinks is keyed on the **fluid id**, not the container, and is
  **per litre**. A per-item number must never be added to a per-litre one [#1881, #1891, #0717].
- A container carries only its *first* fluid's numbers. `Base.PopBottle` reports Cola's 400 kcal/L
  though it lists `Cola;ColaDiet;GingerAle;SodaPop;SodaLime;SodaGrape`, and `Base.Flask` reports
  Gin's though it can hold Rum, Scotch, Vodka or Whiskey [#0656, #1898]. The mapping must cover
  **all** 61 fluids, and the nine `PickRandomFluid` containers resolve at spawn, not in the table.
- Alcohol is a fluid property with no nutrition column (`alcohol`, `fluReduction`, `painReduction`
  live only in `properties_raw` [#1886]). Ethanol energy (7 kcal/g) has to be reconciled against the
  fluid's own `Calories` by hand — `Base.Brandy` declares 2 000 kcal/L, `Base.Gin` 2 630,
  `Base.Whiskey` 2 500 — and SR Legacy has 13 "whiskey" and 10 "distilled" entries to check against.

### The hard cases from the brief, resolved

| Game item | Actual id / display | Mapping | `confidence` |
|---|---|---|---|
| Apple | `Base.Apple` | 171688 *Apples, raw, with skin*, 182 g | `exact` |
| Canned Corn | `Base.CannedCorn` | 169214 *Corn, sweet, yellow, canned, whole kernel, drained solids*; `state_baseline = canned` | `close` |
| Rabbit Meat | `Base.Rabbitmeat` | 174347 *Game meat, rabbit, wild, raw*; retention from grp 17 `LAMB/…` rows | `proxy` |
| Frog Meat | `Base.FrogMeat` | 168148 *Frog legs, raw* — the **one** frog entry in SR Legacy | `exact` |
| Venison | `Base.Venison` | 173855 *Game meat, deer, raw* (SR Legacy has 8 deer entries incl. cooked) | `exact` |
| Beef Jerky | `Base.BeefJerky` | 167536 *Snacks, beef jerky, chopped and formed*, 100 g | `exact` |
| Chips | `Base.Crisps` … `Crisps4` — display `Chips - Plain` / `- Barbecue` / `- Salt & Vinegar` / `- Sour Cream & Onion`; all 720 kcal | one FDC row (169677) for all four; flavour is cosmetic | `close` |
| Chocolate | `Base.Chocolate` = *Milk Chocolate Bar*; plus 7 other chocolate rows | 167587 *Candies, milk chocolate* | `close` |
| Ramen Noodles | `Base.Ramen` = *Dry Ramen Noodles*; `Base.RamenBowl` = *Bowl of Ramen Noodles* | 171177 *Soup, ramen noodle, any flavor, dry*; the bowl is an evolved vessel | `close` / `vessel_only` |
| Cereal | `Base.Cereal`, 2 360 kcal — a whole box | SR Legacy has **108** `Cereals ready-to-eat` entries; pick an unfortified generic, not a branded one (one of the 108 reads Fe = 34.82 mg/100 g) | `close` |
| Peanut Butter | `Base.PeanutButter`, `FoodType = NoExplicit` | 174266 *Peanut butter, smooth style, with salt*; ~450 g jar | `close` |
| Milk | `Base.Milk` = *Milk Carton*, a `fluid_container` at 615 kcal/L | **fluid table**, per litre; also `Milk_Personalsized`, `MilkChocolate_Personalsized`, and `Base.AnimalMilkPowder` (a drainable, no nutrition) | `close`, per-litre |
| Orange Soda | `Base.PopBottle`, joined to fluid `Cola` (400 kcal/L), lists 6 fluids | **fluid table** — map all six fluids, not the container | `close`, per-litre |
| Whiskey | `Base.Whiskey` = *Bottle of Whiskey*, fluid-sourced, 2 500 kcal/L | fluid table; SR Legacy has 13 whiskey entries | `close`, per-litre |
| **Bourbon** | **no such row** — zero matches on `bourbon` in 1 005 rows and zero in SR Legacy | nothing to map | — |
| Coffee | `Base.Coffee2` = *Coffee*, 2 kcal, `ThirstChange = 60` (positive — it dehydrates) | 37 SR Legacy coffee entries; caffeine is nutrient 262, outside the 22 targets | `close` |
| Tea | `Base.Teabag2` = *Tea Bag*, **no nutrition columns at all**; 41 SR Legacy `tea,` entries | `no_nutrition_reason = spice_only` for the bag; the brewed drink is a fluid | — |
| Bleach | `Base.Bleach`, a `fluid_container` on fluid `Bleach`, `ThirstChange = -20`/L, no macros | `no_nutrition_reason = hazard` | — |
| Watermelon Slice | `Base.WatermelonSliced` | 167765 *Watermelon, raw*, 452 g | `exact` |
| Onion Rings | `Base.FriedOnionRings` + `Base.FriedOnionRingsCraft` (same display name) | FNDDS, or SR Legacy *Onion rings, breaded, par fried, frozen, prepared* | `close` |
| Baguette | `Base.Baguette` + `Base.BaguetteDough` (same display name, same macros, different hunger) | 172675 *Bread, french or vienna*; the dough row needs its own `state_baseline` | `close` |
| Pie | `Base.PieWholeRaw` + `Base.PieWholeRawSweet` (same display name, identical macros) | SR Legacy pie entries; `state_baseline = raw` | `close` |
| Cake | `Base.CakeRaw` = *Cake*; plus `Base.CakeBlackForest`, `CakeChocolate` = *… Cake Slice* | SR Legacy cake entries | `close` |
| Bowl of Soup | `Base.SoupBowl` **and** `Base.SoupBowlClay` — both *Bowl of Soup*, identical macros | `vessel_only`, summed from ingredients | — |
| Insect (Cricket) | `Base.Cricket`, 20 kcal, `FoodType = Insect` (20 such rows, incl. 6 `Caterpillar`) | **literature** — Rumpold & Schlüter 2013; SR Legacy has zero insect entries | `guess` |
| Worm | `Base.Worm`, 3 kcal, 0.01 kg, `FoodType = Insect` | literature, scaled to one worm | `guess` |
| **Zombie** | **no such row** — zero matches on `zombie` or `human`; the closest is `Base.CorpseAnimal` (*Animal Corpse*, no nutrition) | nothing to map | — |

Two of the brief's twenty-seven named items do not exist in the dataset at all (`Bourbon`, `Zombie`).
That is itself a finding about how the mapping must be built: **generated from the dataset's own id
list, never from a wish list**, or rows get invented and real rows get missed.

## D. Pipeline shape

### Files

| Path | Kind | Committed? | Why |
|---|---|---|---|
| `tools/food_nutrients.py` | the tool | **yes** | the pipeline; the repository's scanners are its model (`food_scan.py`, `recipe_scan.py`) |
| `data/food-nutrient-map.csv` | hand-curated mapping | **yes** | the only hand-edited input; the design decisions live here |
| `data/fdc-extract.json` | the FDC subset | **yes** | see below |
| `data/food-nutrients.json` | the output | **yes** | `{"meta", "items", "fluids"}` like `food-items.json` |
| `data/food-nutrients.csv` | the flat twin | **yes** | one row per item, **no stamp row** — `data/README.md`'s rule: a `meta` line above the header breaks every `csv.reader` |
| `tools/fdc_fetch.py` | the downloader | **yes** | separate from the pipeline, so the pipeline has no network in it |
| the FDC zips | raw archives | **no** | `.gitignore` already excludes `*.zip`; 5.8 MiB + 3.7 MiB of redistributable-but-pointless bytes |
| `tools/tests/test_food_nutrients.py` | tests | **yes** | `unittest.TestCase` classes, run under `pytest`, as every `tools/tests/test_*.py` does |

**What the committed extract is.** `data/fdc-extract.json`: only the FDC rows the mapping actually
cites — ~400 `fdc_id`s — each carrying its description, `data_type`, `food_category`, the 22 target
nutrients with `nutrient_nbr`, amount and unit, and its `food_portion` rows. Plus the ~30 retention
codes cited, with their 26 factors each. Estimated 300–500 KiB, versus 9.4 MiB of zip. This is the
reproducibility anchor: the pipeline then runs offline, deterministically, from three committed files.

Its `meta` block, following `food_scan.build_dataset`'s shape exactly:

```
"meta": {
  "build": "42.20.4",                    # the game build the mapping's pz_ids were read from
  "jar_hash": "b0bbce05d5",
  "generated": "<UTC date>",             # a date, not a timestamp -- byte-stable within one UTC day
  "tool": "tools/food_nutrients.py",
  "sources": [
    {"name": "FoodData Central SR Legacy",
     "release": "2018-04", "licence": "CC0-1.0",
     "url": "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip",
     "sha256": "<of the zip as downloaded>", "bytes": 6074592},
    {"name": "FoodData Central Foundation Foods", "release": "2026-04-30", ...},
    {"name": "USDA Table of Nutrient Retention Factors R6", "release": "2007",
     "licence": "CC0-1.0", "url": "https://ndownloader.figshare.com/files/44488754", ...},
    {"name": "USDA/FDA/ODS-NIH Iodine Database", "release": "4.0 (2024-10)", ...}
  ],
  "counts": {...},                       # per the table below
  "unmapped": [...],                     # pz_ids in food-items.csv with no mapping row -- must be []
  "orphan_mappings": [...],              # mapping rows whose pz_id is not in food-items.csv -- []
  "guesses": [...],                      # every confidence=guess pz_id, named
  "missing_nutrients": {...}             # per nutrient: the fdc_ids that carry no value for it
}
```

`meta.counts` mirrors `food_scan`'s habit of publishing every counter it computed, so a
definition-dependent number is never a bare prose figure: `items`, `mapped`, `no_nutrition`,
`by_confidence`, `by_state_baseline`, `by_no_nutrition_reason`, `fluids`, `cook_retention_set`,
`atwater_outliers`, `portion_source_counts`.

### Output record

One record per `pz_id`. Nutrient values are stored **per 100 g** *and* **per item**, both, because the
mod needs the per-item number at eat time and a human needs the per-100 g number to review:

```
{"pz_id": "Base.Apple", "kind": "food", "basis": "per_item",
 "portion_grams": 182.0, "portion_source": "vanilla_implied",
 "fdc_id": 171688, "fdc_source": "sr_legacy", "confidence": "exact",
 "state_baseline": "raw", "cook_retention_code": null,
 "per_100g": {"energy_kcal": 52, "protein_g": 0.26, ..., "iodine_ug": null},
 "per_item": {"energy_kcal": 94.6, ...},
 "vanilla": {"calories": 95.0, "carbohydrates": 25.13, "lipids": 0.31, "proteins": 0.47},
 "checks": {"atwater_ratio": 0.99, "energy_vs_fdc_ratio": 1.00, "out_of_range": []}}
```

Absence is `null`, never `0` — the same rule the food dataset already enforces ([#0618, #1896]): an
absent iodine value means unknown, and a zero means measured zero. The CSV twin writes the empty
string for both, as `food_scan._cell` does.

### The generated script blocks

Emitted by `tools/food_nutrients.py --emit-scripts`, into the mod tree, never into `data/`. Per
[item-pass](../../areas/item-pass.md#minimal-block): a partial `module Base` `item` block per record,
re-basing only the keys it changes, merged per key by the loader. Micronutrients are **not** script
keys — an unrecognised key in a `module Base` item block lands in default modData, which is one of
the routes the `nutrition-new-nutrients` skill covers, and whichever store is chosen, the generated
blocks carry only the vanilla keys (`Calories`, `Carbohydrates`, `Proteins`, `Lipids`,
`HungerChange`, `ThirstChange`) and the micronutrient vector ships as data the mod's Lua reads.

### Test surface

| Test | Asserts | Fails when |
|---|---|---|
| `test_schema_row` | every output record carries every declared key; types match; absence is `null` and never `0`; `per_100g` and `per_item` have identical key sets | a record shape drifts |
| `test_units` | `energy_kcal` in kcal, `protein_g`/`fat_g`/`carb_g`/`fibre_g`/`water_g` in g, vitamins A/D/K/B9/B12 and Se/I in µg, the rest in mg; and the round trip `per_item = per_100g × portion_grams / 100` holds to 1e-6 | a unit is silently mixed |
| `test_coverage` | **every** one of the 1 005 `pz_id`s has either an `fdc_id` or a `no_nutrition_reason` from the closed enum; `meta.unmapped == []`; `meta.orphan_mappings == []` | a new game item, or a typo'd id |
| `test_basis_never_mixed` | no record with `basis = per_litre` carries a `per_item` block, and no fluid value is ever summed into a per-item one | the [#0717] unit trap reappears |
| `test_nutrient_id_join` | the `nutrient_nbr → nutrient.id` map is built from `nutrient.csv` and the 22 targets all resolve; a join on the legacy number alone returns nothing | someone joins on 208 |
| `test_retention_csv_defect` | exactly **24** rows of `NutrientRetention.csv` have a non-integer `Retn_Factor`, all on code `5005`; the loader raises rather than coercing | upstream silently fixes or worsens it |
| `test_atwater` | `meta.counts.atwater_outliers` is published and the per-record `checks.atwater_ratio` is computed for every record with four macros | the check is dropped |
| `test_sanity_ranges` | every nutrient within its declared per-100 g range (below); every violation named in `checks.out_of_range`, none silently clamped | a decimal-point error |
| `test_guess_budget` | `len(meta.guesses)` ≤ a pinned number, and every guess row carries a non-empty `notes` | guesses creep in unexamined |
| `test_byte_stable` | two runs on the same inputs give the same bytes, `meta.generated` (a UTC **date**) aside | non-determinism, per `data/README.md`'s existing rule |
| `test_fixtures_verbatim` | the FDC fixture rows in the test file are byte-identical quotes from the extract, each with its `fdc_id` as the re-check anchor | the `test_food_scan.py` convention |

## E. Validation cross-checks

### Atwater against declared energy — vanilla, measured

Over the 653 `per_item` rows: 54 write no macro keys at all, 2 declare `Calories = 0`, leaving **597**
comparable. Ratio = `(4·carbs + 4·protein + 9·lipids) / calories` (`LOCAL`):

| Statistic | Value |
|---|---|
| median ratio | **1.019** |
| mean ratio | 1.385 |
| within ±5 % (0.95–1.05) | **236** rows |
| off by more than 25 % | **217** rows |

| band | rows |
|---|---|
| < 0.5 | 63 |
| 0.5 – 0.8 | 32 |
| 0.8 – 0.95 | 36 |
| **0.95 – 1.05** | **236** |
| 1.05 – 1.25 | 105 |
| 1.25 – 2.0 | 72 |
| > 2.0 | 53 |

**Reading.** Vanilla's *centre* is Atwater-consistent — the median is 1.9 % off, which is what an
Atwater 4/4/9 check should give when fibre is counted inside carbohydrate-by-difference. The tails are
data errors, not a different convention: 53 rows declare more than twice the energy their macros
imply and 63 declare less than half. `Base.Ramen` (52 kcal declared, 166 from macros) is the extreme.

**Fibre handling.** FDC's carbohydrate 205 is *by difference* and **includes** fibre, so
`4C + 4P + 9F` systematically overstates energy by ~2 kcal per gram of fibre (fibre is ~2 kcal/g, not
4). The pipeline's check must use the FDC-consistent form:

```
atwater = 4*(carb_g - fibre_g) + 2*fibre_g + 4*protein_g + 9*fat_g
```

and compare it to nutrient 208 with a ±10 % band, widening to ±25 % where fibre is null. Where
SR Legacy carries the Atwater-specific energy (957/958 in Foundation Foods) that is the better
comparator still. Alcohol adds 7 kcal/g and must be in the formula for the 18 alcoholic fluids.

### Vanilla vs FDC for ten sampled foods

Per-100 g view: vanilla energy spread over the item's `Weight` (× 1 000 g), against the matched
SR Legacy per-100 g energy (`LOCAL` + `EXTRACT`):

| game id | `Weight` → g | vanilla kcal/100 g | FDC kcal/100 g | ratio | reading |
|---|---|---|---|---|---|
| `Base.Apple` | 200 | 48 | 52 | 0.91 | close; the real portion is 182 g, not 200 |
| `Base.FrogMeat` | 200 | 33 | 73 | 0.45 | the portion is 90 g; `Weight` is wrong, the macros are right |
| `Base.BeefJerky` | 200 | 205 | 410 | 0.50 | the portion is exactly 100 g |
| `Base.CannedCorn` | 800 | 39 | 67 | 0.59 | internally inconsistent (3.4× spread) |
| `Base.Baguette` | 300 | 177 | 272 | 0.65 | the portion is ~195 g |
| `Base.Crisps` | 200 | 360 | 532 | 0.68 | the portion is ~134 g; protein is the odd one out |
| `Base.Venison` | 500 | 88 | 120 | 0.73 | 2.8× internal spread — fat is 2.8× the protein-implied mass |
| `Base.Chocolate` | 200 | 425 | 535 | 0.79 | the portion is ~160 g, not a 43 g bar |
| `Base.PeanutButter` | 300 | 887 | 598 | 1.48 | the portion is a ~450 g jar |
| `Base.Butter` | 300 | 1067 | 717 | 1.49 | the portion is a ~445 g (1 lb) pack |
| `Base.WatermelonSliced` | 300 | 45 | 30 | 1.51 | the portion is a ~452 g slice |
| `Base.Rabbitmeat` | 300 | 323 | 114 | **2.83** | the portion is ~850 g — a whole rabbit at a 0.3 kg weight |
| `Base.Ramen` | 200 | 26 | 440 | **0.06** | macros internally impossible |

**The conclusion for the design.** `Weight` and the macro-implied portion disagree by 0.06× to 2.83×.
Vanilla's macros are a good prior *for a portion* on the six internally consistent rows and no prior
at all on the four inconsistent ones. Anyone who rebases by "scale vanilla to FDC per 100 g using
`Weight`" will halve frog meat and triple rabbit. The pipeline must read the portion out of the
macros, not out of `Weight`.

### Sanity ranges per nutrient

Per 100 g of food, for `checks.out_of_range`. Violations are **named, never clamped**.

| Nutrient | plausible per-100 g range | hardest real case |
|---|---|---|
| energy | 0 – 900 kcal | oils at 884 |
| protein | 0 – 90 g | gelatin/dried egg white ~88 |
| fat | 0 – 100 g | pure oil at 100 |
| carbohydrate | 0 – 100 g | sugar at 100 |
| fibre | 0 – 80 g | wheat bran ~43; psyllium higher |
| water | 0 – 100 g | must satisfy water + protein + fat + carb + ash ≈ 100 |
| vitamin A RAE | 0 – 20 000 µg | beef liver ~9 440; cod-liver oil higher |
| thiamin | 0 – 25 mg | fortified cereal |
| riboflavin | 0 – 25 mg | fortified cereal |
| niacin | 0 – 100 mg | fortified cereal |
| vitamin B6 | 0 – 25 mg | fortified cereal |
| folate | 0 – 2 500 µg | fortified cereal; brewer's yeast |
| vitamin B12 | 0 – 100 µg | clams ~98.9 |
| vitamin C | 0 – 2 000 mg | acerola ~1 678 |
| vitamin D | 0 – 250 µg | cod-liver oil ~250 |
| vitamin E | 0 – 150 mg | wheat-germ oil ~149 |
| vitamin K | 0 – 1 800 µg | parsley/dried basil ~1 700 |
| sodium | 0 – 40 000 mg | table salt ~38 800 |
| potassium | 0 – 20 000 mg | cream of tartar ~16 500 |
| calcium | 0 – 8 000 mg | dried basil / fortified |
| magnesium | 0 – 1 000 mg | rice bran ~781 |
| iron | 0 – 130 mg | fortified cereal; dried spirulina |
| zinc | 0 – 100 mg | oysters ~78 |
| iodine | 0 – 3 000 µg | dried kelp; the wide tail is real |
| selenium | 0 – 2 000 µg | Brazil nuts ~1 917 |
| omega-3 (ALA+EPA+DHA) | 0 – 60 g | flaxseed oil ~53 ALA |

Three structural checks beyond the ranges: **the proximate sum** (water + protein + fat +
carbohydrate ≤ 102 g, allowing ash and rounding); **fibre ≤ carbohydrate**; and **retention ≤ 100 %**
on every applied factor, which catches a mis-joined retention code immediately.

## Recommended pipeline

1. **`tools/fdc_fetch.py`** downloads four files into a gitignored scratch dir, recording each one's
   `sha256` and byte count: SR Legacy CSV (5.79 MiB), Foundation Foods CSV (3.65 MiB),
   `NutrientRetention.csv` (473 KiB), and the iodine database PDF (349 KiB). No API key. It never
   writes into `data/`.
2. **Build the nutrient id map** from `nutrient.csv`: `nutrient_nbr → nutrient.id`. Assert all 22
   targets resolve. Every later join uses `nutrient.id`.
3. **Seed the mapping CSV from the dataset**: emit one row per `pz_id` from `data/food-items.csv`'s
   1 005 rows, pre-filled with `pz_display`, `pz_kind`, and a `no_nutrition_reason` guess for the 290
   zero-nutrition rows, the 111 spices and the 96 `CantEat` rows. Never from a hand-written wish list
   (`Bourbon` and `Zombie` do not exist).
4. **Curate the mapping by family, not by row.** The 644 per-item food rows hold only 342 distinct
   macro tuples; map the 109 shared-tuple families once. Prioritise: the 342 tuples, then the 61
   fluids, then the ~40 iodine-relevant foods, then the ~20 insect rows.
5. **Set `portion_grams` by the three-step rule**: vanilla-implied where the four macros agree within
   1.1× (six of thirteen sampled rows qualify); else an FDC `food_portion.gram_weight`; else a
   labelled judgement. Never `Weight`.
6. **Assign `state_baseline`** from the dataset: `canned` on the 41 `CannedFood` rows, `dried` on the
   45 dried ones, `raw` otherwise, `prepared` on the manufactured foods. Prefer a **measured** FDC
   entry in that state (1 806 "cooked", 1 433 "raw", 499 "canned", 385 "frozen", 122 "dried") over
   applying a retention factor to a raw one.
7. **Assign `cook_retention_code`** only on the 257 `IsCookable` rows, and only where step 6 could
   not find a measured cooked entry. Map the item's `FoodType` / FDC `food_category` to one of the 13
   retention food groups, and pick the method row matching the game's cooking (a pot of stew is
   `WATER USED`; a grilled steak is `BROILED`).
8. **Build the extract**: `data/fdc-extract.json`, only the ~400 cited `fdc_id`s with the 22 target
   nutrients, their portion rows, and the ~30 cited retention codes with their 26 factors each.
   Commit it with its `meta.sources` provenance. The rest of the pipeline is then offline.
9. **Emit `data/food-nutrients.json` + `.csv`** — `meta` / `items` / `fluids`, `indent=1`, LF, no CSV
   stamp row, absence as `null`, sorted by `pz_id`, byte-stable within one UTC day.
10. **Run the checks in-line** and publish them per record and in `meta.counts`: Atwater with the
    fibre-at-2-kcal form, energy against nutrient 208, the per-nutrient sanity ranges, the proximate
    sum, fibre ≤ carbohydrate, and retention ≤ 100 %. Name violations; clamp nothing.
11. **`--emit-scripts`** writes the partial `module Base` item blocks (vanilla keys only) into the mod
    tree, and the micronutrient vectors as the mod's own data file. Never into `data/`.
12. **Gate the commit**: `python -m pytest tools/tests -q` green; `tools/claims_check.py --staged` at
    zero for the pages and register rows the same commit lands; the extract's provenance rows in the
    artifacts register per CLAUDE.md § 4.

## Gaps

- **Iodine has no machine-readable USDA route.** SR Legacy carries zero iodine values over 7 793
  foods; the dedicated 478-food database is published as PDF only. Either hand-transcribe ~40 rows
  (recommended) or take CoFID's XLSX and accept its OGL attribution and its non-joinable food codes.
- **Eight of the 22 targets have no USDA retention factor**: vitamin D, E, K, selenium, iodine,
  omega-3, fibre, water. For the fat-solubles and minerals ~100 % with a leaching term is defensible;
  for omega-3 the loss is oxidative and no table covers it.
- **Burning and rotting have no retention data at all.** The game has both states and the literature
  does not model either as a retention factor. Those two rows of the state table are mod judgements
  and must be labelled as such wherever they appear.
- **Insects are literature-only.** FDC has zero entries matching cricket, insect, grasshopper,
  mealworm or earthworm. Twenty game rows (`FoodType = Insect`, six of them `Caterpillar`) rest on
  Rumpold & Schlüter 2013's compiled values, whose per-species spread is wide.
- **The retention CSV's 24 shifted rows** on code 5005 mean the CSV alone is not a complete copy of
  Release 6; the PDF is the authority for those, and this session had no PDF text extractor available
  (no `pypdf`, `pdfminer` or `pymupdf`, and no `pdftoppm`), so those 24 values were **not** read.
- **The alcohol energy reconciliation is unresolved.** Fluid `Calories` (Brandy 2 000, Gin 2 630,
  Whiskey 2 500 kcal/L) versus ethanol at 7 kcal/g has not been checked against SR Legacy's 13
  whiskey and 38 wine entries; `alcohol` is a fluid property with no dataset column [#1886].
- **The 14 part-filled containers** (`InitialPercentMin`/`Max`) and the 9 `PickRandomFluid` ones make
  a spawned container's nutrition a draw the dataset does not model [#1897, #1898]; a per-litre
  micronutrient table inherits that, and the mod must read the instance, not the row.
- **FNDDS was not opened.** It is the right source for the mixed dishes (onion rings, prepared soups)
  and its actual CSV is only 3.2 MiB, but its portion and recipe conventions were not examined here.
- **Caffeine (nutrient 262)** is outside the 22 targets and the game already models coffee's effects
  through `ThirstChange` and fatigue; if the mod wants a caffeine stat, SR Legacy carries it and this
  report does not scope it.
- **No claim here is a register row.** Every `LOCAL` figure is reproducible from the committed
  `data/food-items.csv`, and every `EXTRACT` figure from a re-download of a named URL, but the rows
  get minted by the commit that lands the pipeline, not by this document.

## Sources

**USDA FoodData Central — bulk downloads.** Every URL below returned HTTP 200 this session with the
byte count shown; the two SR Legacy / Foundation CSV archives were downloaded and read.

- `https://fdc.nal.usda.gov/download-datasets/` — the download index (the page's FNDDS CSV size,
  200 M / 1.6 G, disagrees with the file's measured 3 325 692 B).
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip` —
  **6 074 592 B**, the recommended spine. Contains `food.csv` (7 793 rows), `nutrient.csv`,
  `food_nutrient.csv` (644 125 rows), `food_portion.csv` (14 449 rows), `food_category.csv`,
  `retention_factor.csv` (the 270 code descriptions, no factor values),
  `all_downloaded_table_record_counts.csv`.
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2018-04.zip` —
  13 456 312 B.
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-04-30.zip` —
  **3 825 741 B**, 469 `foundation_food` rows, 477 nutrients, the only FDC iodine (55 foundation rows).
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2026-04-30.zip` —
  469 303 B.
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_survey_food_csv_2024-10-31.zip` —
  **3 325 692 B** (FNDDS; the page's 200 M is wrong).
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_csv_2026-04-30.zip` —
  448 767 220 B. Not recommended.
- `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_csv_2026-04-30.zip` — 481 517 495 B, the
  full download. Unnecessary.
- `https://fdc.nal.usda.gov/api-guide/` — the API guide: a data.gov key is required for API requests,
  1 000 requests/hour per IP by default, `DEMO_KEY` 30/hour and 50/day; four endpoints. Bulk
  downloads need no key.
- `https://data.nal.usda.gov/dataset/fooddata-central-0` → redirects to
  `https://agdatacommons.nal.usda.gov/articles/FoodData_Central/24668133` (403 to automated fetch) —
  the Ag Data Commons record; the CC0 / public-domain wording and the suggested citation are quoted
  from it via search results, not from a successful fetch of the record itself.

**USDA Table of Nutrient Retention Factors, Release 6 (2007).**

- `https://catalog.data.gov/dataset/usda-table-of-nutrient-retention-factors-release-6-2007` — the
  data.gov record; licence `https://creativecommons.org/publicdomain/zero/1.0/`, access level public.
- `https://ndownloader.figshare.com/files/44488754` — **`NutrientRetention.csv`, 472 734 B,
  downloaded and read**: 7 018 rows, 270 codes, 13 food groups, 26 nutrients, factors 10–100, and the
  24-row column shift on code 5005.
- `https://ndownloader.figshare.com/files/44488757` — `NutrientRetentionDD.csv`, 803 B, the data
  dictionary (downloaded and read; the seven field definitions quoted in § B come from it).
- `https://ndownloader.figshare.com/files/44488751` — `retn06.pdf` via figshare.
- `https://www.ars.usda.gov/arsuserfiles/80400530/pdf/retn06.pdf` — **126 629 B**, HTTP 200, the ARS
  copy of the Release 6 PDF (the authority for the 24 values the CSV loses).
- `https://www.ars.usda.gov/ARSUserFiles/80400525/Data/retn/retn06.pdf` — **126 629 B**, HTTP 200, a
  second ARS path to the same PDF.
- `https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/methods-and-application-of-food-composition-laboratory/mafcl-site-pages/nutrient-retention-factors/`
  — the ARS landing page for the retention factors.

**Iodine.**

- `https://www.ars.usda.gov/ARSUserFiles/80400535/Data/Iodine/IODINE_DATABASE_RELEASE_4_PER_100G.pdf`
  — **357 524 B**, HTTP 200. Release 4 per-100 g table; `DB_ID`, SR/Foundation reference, FDC id,
  NDB No., description, n, iodine µg/100 g, SD, min, max, sources.
- `https://www.ars.usda.gov/ARSUSERFILES/80400535/DATA/IODINE/IODINE%20DATABASE_DOCUMENTATION.PDF` —
  **727 810 B**, HTTP 200. The database documentation.
- `https://www.ars.usda.gov/ARSUSERFILES/80400535/DATA/IODINE/IODINE_DATABASE_RELEASE_3_PER_100G.PDF`
  — Release 3, for comparison.
- `https://ods.od.nih.gov/Research/Iodine.aspx` — the NIH ODS project page (403 to automated fetch;
  reachable in a browser).

**Alternatives.**

- `https://www.gov.uk/government/publications/composition-of-foods-integrated-dataset-cofid` — UK
  CoFID; published 25 March 2015, last updated 19 March 2021; Open Government Licence v3.0.
- `https://assets.publishing.service.gov.uk/media/60538b91e90e07527df82ae4/McCance_Widdowsons_Composition_of_Foods_Integrated_Dataset_2021..xlsx`
  — **4 629 542 B**, HTTP 200, the CoFID 2021 workbook (note the double dot in the filename).
- `https://assets.publishing.service.gov.uk/media/60538e66d3bf7f03249bac58/McCance_and_Widdowsons_Composition_of_Foods_integrated_dataset_2021.pdf`
  — the CoFID 2021 user guide, 759 KB, 37 pages.
- `https://assets.publishing.service.gov.uk/media/60538ba4e90e07527f645f88/CoFID_oldFoods.xlsx` —
  CoFID legacy foods, 634 KB.
- `https://open.canada.ca/data/en/dataset/089885f9-ed53-44e6-854a-14d21a1ec2e0` — Canadian Nutrient
  File 2015; CSV / Excel / Access; Crown copyright, Health Canada must be named as the source.
- `https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/nutrient-data/copyright-guidelines-canadian-nutrient-file.html`
  — the CNF copyright guidelines.
- `https://www.nal.usda.gov/human-nutrition-and-food-safety/nutrient-lists-standard-reference-legacy-2018`
  — NAL's curated SR Legacy nutrient lists (PDF/XLSX per nutrient). Useful as a cross-check; note
  that its curated set omits iodine and the omega-3 columns, which is *not* the same as their absence
  from the underlying data — 851/629/621 are all present in SR Legacy, iodine is genuinely empty.

**Literature.**

- Rickman JC, Barrett DM, Bruhn CM (2007). *Nutritional comparison of fresh, frozen and canned
  fruits and vegetables. Part 1. Vitamins C and B and phenolic compounds.* J Sci Food Agric
  87:930–944. doi:10.1002/jsfa.2825 — verified through Crossref (`api.crossref.org/works/`) and the
  abstract retrieved verbatim from Europe PMC. The canning/blanching/storage structure and the
  thiamin 7–70 % range.
- Rickman JC, Bruhn CM, Barrett DM (2007). *Nutritional comparison of fresh, frozen, and canned
  fruits and vegetables II. Vitamin A and carotenoids, vitamin E, minerals and fiber.* J Sci Food
  Agric 87:1185–1196. doi:10.1002/jsfa.2824 — verified through Crossref.
- Rumpold BA, Schlüter OK (2013). *Nutritional composition and safety aspects of edible insects.*
  Mol Nutr Food Res 57:802–823. doi:10.1002/mnfr.201200735, PMID 23471778 — verified through
  Crossref. 236 nutrient compositions; energy 426.3 kcal/100 g (grasshoppers, locusts, crickets) to
  508.9 (caterpillars). The only source for the 20 `FoodType = Insect` rows.

**This repository.**

- `data/food-items.csv` and `data/food-items.json` — every `LOCAL` figure in this report is computed
  from the committed CSV (the 2026-09-10 scan of `42.20.4`, jar `b0bbce05d5`).
- `docs/reference/datasets.md` — the column authority; the nutrition basis, the four kinds, the
  dated counts, the CSV and JSON schemas.
- `data/README.md` — the no-stamp-row rule for a CSV, the `meta`-block rule for its JSON twin, and
  the byte-stability rule.
- `tools/food_scan.py` — the `meta` block, `_cell`'s absence rule, and the writer conventions this
  pipeline copies; `tools/tests/test_food_scan.py` — the verbatim-fixture convention.
- `docs/facts/food-item-model.md` — the three state axes [#0202, #0204], the per-key table (its
  `Calories` row reads "stored unscaled; **no state modifier at any age** — the only nutrition
  modifier in the game is `Eat`'s ÷5 for burnt"), and the state-free macros [#0369].
- `docs/facts/eating-pipeline.md` — the burnt ÷5 [#0019], the macros as bare field reads [#0036], the
  hunger ladder [#0029–#0032] and the thirst precedence [#0033, #0034].
- `docs/areas/item-pass.md` — the minimal override block and the per-key merge.
- `docs/facts/cooking-and-recipes.md` — the evolved-recipe summation and the use rule the
  recipe dataset's deltas rest on.
