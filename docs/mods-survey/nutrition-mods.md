# Nutrition mods — the catalog, and the three teardown picks

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 08 (P3).
Evidence grades: **C** read off a shipped file — the mod's own tree, cited
`<version folder>/<path>:<line>`, or the game's jar/Lua — **M** measured on the live dedicated
server (run id + artifact link), **W** a Workshop page or a wiki mirror: secondary, and never on
its own a teardown candidate.
Three datasets carry the numbers and are the **column authority**, not this page:
[`data/README.md`](../../data/README.md) § mod-inventory for the installed corpus
([`data/mod-inventory.json`](../../data/mod-inventory.json), swept **2026-09-10 17:47**),
§ workshop-search for the public sweep
([`data/workshop-search.json`](../../data/workshop-search.json), fetched **2026-09-10 16:26**,
quoted here at commit `ce7cd72`) and § workshop-catalog-details for the nine item pages this
page's B42-status table needs
([`data/workshop-catalog-details.json`](../../data/workshop-catalog-details.json), fetched
**2026-09-10 17:46**). Every count on this page carries the stamp of the sweep it came
from, because both trees are live: Steam rewrites a mod folder under you (item `3490370700`, 13:47
that same day) and the Workshop reorders its browse pages hourly.

## Summary

1. **Nineteen of the 230 installed mod folders touch the nutrition surface at all**, on two
   independent signals: **11** call a nutrition API from Lua (`signals.food_nutrition`) and **9**
   write a nutrition key in a shipped script (`signals.script_nutrition`), with exactly one mod —
   Long Term Preservation — on both lists. Everything else in the approved corpus is silent on
   nutrition. Ev C.
2. **Only two mods in the whole corpus write a macro, and they write it on different objects.**
   `SomewhatTraitsCore` moves the *player's* calories from `lua/server/` on `OnTick`
   (`42.15/media/lua/server/SWTraitsCore_server.lua:84,86`); Long Term Preservation multiplies an
   *item's* four macros and its hunger by 0.70 from an `OnCooked` script hook
   (`42.20/media/lua/server/recipe_meats.lua:45-49`). Every other Lua hit is a read, a getter name
   in a reflection table, or a comment — a UI number, an XP multiplier, a recipe filter — and
   **nine of the eleven mods never write a macro at all**. Ev C.
3. **The reads are almost all client-side, and the server owns everything they read.** `Nutrition`,
   hunger, thirst, weight and traits are server-owned and reach a client on a 1 Hz
   `PlayerStatsPacket` snapshot (slices 01–03); `ItemStatsPacket` carries the macro block but not
   `age`/`offAge`/`offAgeMax`/`freezingTime`, and reuses cached packets so a zero-valued field can
   arrive stale (slice 02). So a client-only reader such as simpleStatus can only ever show the
   1 Hz mirror, and a mod that edits an item's fields client-side desyncs silently — the
   ItemQuality class of bug. Ev C + M.
4. **The Workshop sweep found no second corpus.** 212 results over 8 terms collapse to 180 distinct
   items, **3 installed** — a Lincoln Town Car, Big Bottles and BeyondTen — and **none of the 30
   `nutrition`-term results is installed here**. A not-installed row cannot be linted, profiled or
   measured from this repo, so it is graded W and carries the exact action that would change that.
   Ev W (+ C for the three installed).
5. **The three picks, in order, are `SKITTLE_LongTermPreservation4220` (slice 09), `simpleStatus`
   (slice 10) and `AutoCook` (slice 11)** — the write side, the read side and the cooking-pipeline
   hook points. All three are installed, B42-current enough to boot, small enough to read whole,
   and each carries a live static finding of its own. Ev C.

---

## Method and scope

**The corpus is the approved modlist**, i.e. the locally installed workshop tree
(`D:\SteamLibrary\steamapps\workshop\content\108600`, read and never written): **179 workshop items
holding 230 mod folders, 229 of which declare an id** the engine can index. One folder
(`3782784855/Skill Recovery Journal`) ships no `mod.info` anywhere and is invisible to
`pzt.mods.workshop_index()`. Class distribution, measured 2026-09-10 15:30 and reproduced from the
committed 17:47 dataset for this page: **175** light-lua systems · **31** other · **15** heavy-lua
systems · **5** scripts-only content · **4** 3D+lua content. `other` is not "ships nothing": **24
of those 31 have no `media/` under the LIVE folder at all**, so nothing was scanned rather than
nothing shipped. Where the content actually is varies — all 24 ship a `common/media`, **12 of
them also ship a B41 root `media/`**, and `STA_PryOpen` ships `42.18/media` and `42.19/media`
as well, beside a live `42.20/` holding none. Ev C.

**Ids are the engine-resolved ids.** `mod_id` is the `id=` of the `mod.info` the build actually
reads — newest `42[.x[.y]]/` folder first, then `common/`, then the mod root — never the folder
name. 20 of the 230 rows changed against this slice's own plan table when that rule was applied;
Long Term Preservation declares `SKITTLE_LongTermPreservation4220`, not `LongTermPreservation4220`.
A profile's `[[mods]] id` must be the resolved id. Ev C.

**The signal scan reads the LIVE version folder only** — the one folder the running 42.20.4 build
resolves — because a mod that ships the same scripts in three version folders must not be counted
three times. Two consequences, and they cut in opposite directions:

- A stale copy is genuinely dead. `3041122351/63Type2Van` writes nutrition keys **only** in a B41
  flat root `media/`, so its B42 script signal is 0 and it is not on this page.
- **`common/media` is not dead**, and this scan did not read it. **177 of the 230 rows have one**
  (2026-09-10), so a zero in `stats` or `signals` is trustworthy only when `media_at` does not
  include `common/media`. `live_media: false` marks something much narrower — the **24** rows with
  no live `media/` at all. Every readiness statement below reads `media_at`, not `live_media`.
  Ev C.

**Measured impact of that gap on this page: none.** Every `common/media` in the corpus was swept
for the ten `script_nutrition` keys twice on 2026-09-10 and not one carries a single key, so no
nutrition candidate is hidden by the scope. It still bites on *architecture* — AutoCook's entry
points are in `common/` and nowhere else (§ Open questions Q1). Ev C.

**What this page does not do.** It does not read a mod's behaviour: every claim here is a file read
or a count of regex hits over shipped files, and a hit count is not a behaviour. It does not rank
the Workshop, which is a trend-sorted top-30-per-term slice and not a census. And it asserts no
rule for how `common/` and `42.x/` combine — that is § Open questions Q1, left for a teardown pass
to settle.

---

## Sweep 1 — Lua nutrition signals (live version folder, 2026-09-10 17:47)

`signals.food_nutrition` counts hits of `getNutrition()`, `setCalories`, `setProteins`, `setLipids`,
`setCarbohydrates` or `HungerChange` in any `.lua` **under the live version folder**. `net` is
`send_client_cmd` + `on_client_cmd` + `send_server_cmd` — and it is a **floor**, because the
inventory has no signal for `OnServerCommand` (`SkillRecoveryJournal` has 3 of those on top of its
23). Every `food_nutrition` count was reproduced file by file for this page and all eleven totals
matched the dataset exactly.

`patch` is `signals.monkey_patch` — the **save-and-wrap** idiom, `local original… = X.y`. It is
not the `global_write_vanilla` count the § API surface table carries (`function IS…:` headers),
and the two disagree by design: AutoCook reads `patch` **0** here and 21 there.

| Mod id | Item | Hits | `lua_kb` | net | `mod_data` | `monkey_patch` | `pcall` | Sandbox | Class | Ev |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `simpleStatus` | `2867431511` | 12 | 46 | 0 | 4 | 0 | 0 | no | light-lua | C |
| `CleanUI` | `3437629766` | 11 | 1064 | 8 | 12 | 3 | 101 | no | heavy-lua | C |
| `SkillRecoveryJournal` | `2503622437` | 8 | 134 | 23 | 13 | 0 | 2 | yes | heavy-lua | C |
| `AutoCook` | `3388721641` | 4 | 41 | 0 | 9 | 0 | 0 | no | light-lua | C |
| `BeyondTen` | `3765241705` | 4 | 170 | 8 | 14 | 12 | 47 | no | light-lua | C |
| `Economy` | `3624538051` | 4 | 503 | 46 | 9 | 0 | 63 | yes | heavy-lua | C |
| `SKITTLE_LongTermPreservation4220` | `3774789651` | 4 | 3 | 0 | 0 | 0 | 0 | no | light-lua | C |
| `SomewhatTraitsCore` | `3498347699` | 3 | 44 | 4 | 0 | 66 | 0 | yes | light-lua | C |
| `CustomGamepadUI` | `3001154607` | 1 | 35 | 0 | 3 | 11 | 0 | no | light-lua | C |
| `MoodleFramework` | `3396446795` | 1 | 27 | 0 | 1 | 0 | 0 | no | light-lua | C |
| `QuestSystem` | `3624538051` | 1 | 718 | 96 | 28 | 12 | 13 | yes | heavy-lua | C |

**11 rows. Grades: 11 C, 0 M, 0 W.**

**Where each mod's hits actually are, and which side runs them** — the column the count cannot
carry. `lua/client` runs on a client only, `lua/server` on the dedicated server (and in
singleplayer), `lua/shared` on **both**.

| Mod id | Side | Site(s) | What it does there | Ev |
|---|---|---|---|---|
| `simpleStatus` | client | `42.16/media/lua/client/ss.stats.lua:238,280,294,308,381,404-411` | all 12 hits, in one file: `getProteins` / `getCalories` / `getCarbohydrates` / `getLipids` / `getWeight` and the three weight-trend predicates, each wrapped in a `round(…, 1)` for a status bar | C |
| `CleanUI` | client | `42.19/media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:806,2442,2444,2689,3571,4664,4665`, `…/ISUI/ISInventoryPane.lua:3503,5623`, `…/CleanUI/Vanilla/CleanUI_Vanilla_ISInventoryPane.lua:1111,2810` | 9 of the 11 are `item:getHungerChange()` in inventory tooltips and the eat-portion menu; the two `getNutrition()` hits (`ISInventoryPane.lua:3503`, `CleanUI_Vanilla_ISInventoryPane.lua:1111`) are inside commented-out vanilla lines. Every one of these files is a whole copy of a vanilla UI file | C |
| `SkillRecoveryJournal` | **shared** | `42.20.1/media/lua/shared/Skill Recovery Journal Main.lua:23,54,55` and `…XP.lua:134,139,140` | answers the approved-modlist's open "reads nutrition (why?)": `canAddFitnessXp()` gates fitness XP, and `getProteins()` scales the exercise multiplier 1.5 / 1.0 / 0.7. `Main.lua:51` carries an upstream comment marking the `checkProteinLevelMulti` below it as not yet implemented | C |
| `AutoCook` | client | `42.13/media/lua/client/AutoCook.lua:214,329`, `…_AutoCraftRecipes.lua:39`, `…/ISCharacterCook.lua:71` | `getNutrition():getWeight()` + `isIncWeight` / `isDecWeight` choose whether to add spices, and `getLipids` / `getCarbohydrates` filter which food goes into a recipe; the fourth is `item:getHungerChange() < 0` selecting edible recipe outputs | C |
| `BeyondTen` | shared | `42/media/lua/shared/BeyondTen/ExtendedBonuses.lua:497-500` | four `{getter, setter}` name pairs in a reflection table, not four calls (teardown done) | C |
| `Economy` | shared | `42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:240-243` | the same shape: a serializer field map naming the four macro getters and setters so a shop item survives a round trip | C |
| `SKITTLE_LongTermPreservation4220` | **server** | `42.20/media/lua/server/recipe_meats.lua:45-48` | `setCarbohydrates` / `setLipids` / `setProteins` / `setCalories`, each `× 0.70`, on the crafted instance. `setHungChange(… × 0.70)` at `:49` is a fifth macro write the regex does not match | C |
| `SomewhatTraitsCore` | **server** | `42.15/media/lua/server/SWTraitsCore_server.lua:78,84,86` | the corpus's only **player** macro write: an `OnTick` handler gated on the `SWAdaptiveMetabolism` trait adds or subtracts `dayLengthMultiplier × 0.5` calories to hold body weight inside 77–83 kg | C |
| `CustomGamepadUI` | client | `42/media/lua/client/SWSelectAndStart.lua:57` | inside a commented-out line copied from vanilla — a false positive of the regex, and the honest reading of a 1 | C |
| `MoodleFramework` | client | `42.20/media/lua/client/MF_ISMoodle.lua:98` | a `print()` debug line that appends `proteins=…` to a moodle-level log | C |
| `QuestSystem` | shared | `42/media/lua/shared/Utilities/ItemDumpExport.lua:89` | `hungerChange = round4(item:getHungerChange())` in a developer item-dump exporter | C |

**11 rows. Grades: 11 C, 0 M, 0 W.** Read the two together: of the **53** Lua hits across the
corpus, **6 are writes** (LTP's four macro setters, SomewhatTraitsCore's two `setCalories`) — and a
seventh write, LTP's `setHungChange` at `recipe_meats.lua:49`, is not matched by the regex at all;
**8 are a getter/setter *name* in a reflection table rather than a call** (BeyondTen 4, Economy 4);
**3 sit inside comments** (CleanUI 2, CustomGamepadUI 1); and the remaining **36 are live reads**.
A hit count is not a behaviour, which is what this second table is for.

## Sweep 2 — script nutrition definitions (live version folder, 2026-09-10 17:47)

`signals.script_nutrition` counts `Calories`, `Carbohydrates`, `Lipids`, `Proteins`,
`HungerChange`, `ThirstChange`, `DaysFresh`, `DaysTotallyRotten`, `FoodType` or `EvolvedRecipe` at
the start of a line in a `.txt` under `<live>/media/**/scripts`, **read comment-stripped** as the
engine and `tools/food_scan.parse_script` read it. `Items` is
`script_item_blocks` — **every** `item` definition in those files, clothing and vehicles included;
it is not a food count. The Items column dropped on two rows and the Keys column on one when the comment fix landed in
`Slice 08: final fix wave` (`9f551f6`): LTP 135 keys / 17 items → **117 / 15**,
`ZVirusVaccine42BETA` 102 items → **86**, and 899 → **881** items over the nine rows.
§ Discrepancies row 1 has the per-block arithmetic. `module Base` is the *capability* to override
a vanilla item, not proof of one: the
`Collide` column is the measured name-collision count against the **5 092** distinct
`module Base` item names 42.20.4's own `media/scripts` declares (parsed comment-stripped, so it is
lower than the 5 105 raw `item` lines `data/README.md` quotes).

| Mod id | Item | Keys | Items | Modules | Collide | Live folder | Ev |
|---|---|---:|---:|---|---:|---|---|
| `SKITTLE_LongTermPreservation4220` | `3774789651` | 117 | 15 | `Skittles` | 0 | `42.20` | C |
| `Horse` | `3661336777` | 116 | 288 | `Base`, `HorseMod` | **1** | `42` | C |
| `OCsPacking` | `3626823538` | 76 | 308 | `Base`, `OCP` | 0 | `42.15` | C |
| `ZVirusVaccine42BETA` | `3615135168` | 36 | 86 | `Base`, `LabBooks`, `LabItems`, `LabItems{`, `LabSounds` | 0 | `42.20` | C |
| `GirthsTweaks` | `3745960616` | 26 | 14 | `Base`, `GirthsTweaks`, `SDCaches`, `SDFoods`, `SDQuests`, `ST_Tweaks` | 0 | `42` | C |
| `JadePackingSD` | `3779653231` | 18 | 125 | `Packing` | 0 | `42` | C |
| `69mini` | `2937786633` | 7 | 32 | `Base` | 0 | `42.13` | C |
| `SDQuests` | `3745960616` | 6 | 12 | `Base`, `SDQuests` | 0 | `42` | C |
| `biogas` | `2925657627` | 1 | 1 | `Base`, `Biofuel` | 0 | `42` | C |

**9 rows. Grades: 9 C, 0 M, 0 W.** Per-key breakdowns are in `script_nutrition_keys` on each
record. **Seven of the nine declare `module Base`; two of the seven actually define an item
under it** — `Horse` 1 and `69mini` all 32 — **and exactly one of those collides with a vanilla
item name**: `Horse` redefines `Base.Rope`. The other five declare the module and then define
everything under a module of their own, which is why the declaration alone proves nothing. So on
42.20.4 the installed corpus contains
**no vanilla food override at all**: every nutrition-bearing script block in it adds a new item.
That is a stronger statement than the module column alone supports, and it is why the column
carries a measured collision count beside it. Ev C — the intersection of each mod's
`module <name> / item <name>` pairs with vanilla `media/scripts`, parsed with
`tools/food_scan.parse_script` (which strips `/* */` as the engine does).

**The two readings now agree row for row.** With `mod_inventory` stripping comments the same
way, `script_item_blocks` and the parser's own block count are **identical on all nine rows**
(15 · 288 · 308 · 86 · 14 · 125 · 32 · 12 · 1, 2026-09-10 17:47) — they disagreed on LTP and
`ZVirusVaccine42BETA` before it. Two independent readers of the same files landing on the same
number is what makes the Items column quotable at all. Ev C.

**`3041122351/63Type2Van` is deliberately absent**: its 7 nutrition keys live only in a B41 flat
root `media/` the 42.20.4 build never reads. Ev C.

## Sweep 3 — the public Workshop (fetched 2026-09-10 16:26, commit `ce7cd72`)

Eight terms against the `Build 42`-tagged ready-to-use section, one browse page each (Steam serves
30 a page and the tool does not paginate): **212 results → 180 distinct ids, 3 installed, 0 term
failures**. 29 ids appear under more than one term. An item page may answer 200 with a template
the parser cannot read, so **details were fetched for the named ids only** — a declared subset,
9 at the browse pass and 6 more in the repair pass below. At `ce7cd72` the file's own census
reads **`details_status`: 15 `fetched` / 165 `not_requested` / 0 `failed`**, and a row's three
stat columns may be quoted only when it says `fetched`. Take the census from `details_status`,
never from a count in prose.

| Term | Results | Installed | Note | Ev |
|---|---:|---:|---|---|
| `nutrition` | 30 | **0** | a full page of third-party nutrition work, and not one item of it is installed here | W |
| `vitamin` | 30 | 0 | — | W |
| `malnutrition` | 2 | 0 | the only term that does not fill a page | W |
| `diet` | 30 | 1 | the hit is a car mod | W + C |
| `hydration` | 30 | 2 | a bottle-capacity tweak and BeyondTen | W + C |
| `food overhaul` | 30 | 0 | — | W |
| `cooking overhaul` | 30 | 0 | — | W |
| `spoilage` | 30 | 0 | — | W |

**8 rows. Grades: 6 W, 2 W + C.**

**The load-bearing rows.** Titles and ids verbatim from `data/workshop-search.json`. The three
installed rows are **C + W**: `installed` and `mod_ids` join to a record in `mod-inventory`, which
*is* read off shipped files, while their Size and Updated cells are Workshop-page readings like
every other row's — the same split the § B42 status table makes. The C belongs to the inventory,
never to the page. Every W row's
unblocking action is the same sentence: *subscribe to `<id>` in Steam, let it download, re-run
`python tools/mod_inventory.py`*.

| `workshop_id` | Title | Installed | Size | Updated | Why it is here | Ev |
|---|---|---|---|---|---|---|
| `2932547723` | '93 Lincoln Town Car + Limo | yes (`93townCar`) | 14.655 MB | Jul 2 @ 11:40am | matched `diet` on its page text; not a nutrition mod | C + W |
| `3759421894` | Big Bottles | yes (`BigBottles`) | 107.238 KB | Aug 1 @ 6:44am | matched `hydration`; a container-capacity tweak, no nutrition signal in the inventory | C + W |
| `3765241705` | Beyond Ten - Level 15 Skills [B41/B42] | yes (`BeyondTen`) | 348.184 KB | Sep 4 @ 1:25pm | the only installed hit with a nutrition signal, and its teardown is already done | C + W |
| `3736275816` | ApocalipseBR - Nutrition Sync Fix | no | 453.434 KB | May 31 @ 11:18am | **someone else hit the MP nutrition-sync problem this library exists to characterise** and shipped a fix. Subscribing is the only way to read how | W |
| `3796644824` | [NUTRITION LAUNDERING PATCH + FEATURES] Long Term Preservation | no | 471.224 KB | *never* | **a third-party patch to pick 1**, four days old, claiming the preservation mod launders nutrition — a claim about a mod we *can* read | W |
| `3690404044` | Nutrition Makes Sense | no | 1.042 MB | Aug 18 @ 5:01pm | the largest nutrition overhaul on the page, and the one with an add-on ecosystem | W |
| `3785515388` | Reasonable Nutrition | no | 145.008 KB | Aug 26 @ 3:49pm | the cheapest comparison read if only one of these is ever subscribed | W |
| `3782835400` | Realistic Nutrition | no | 636.708 KB | *never* | third of the three same-month nutrition overhauls | W |
| `3078272807` | Nutrition Tweaker Enhanced | no | 503.836 KB | Jul 22, 2025 @ 1:35pm | the B41-era ancestor still carrying the `Build 42` tag | W |

**9 rows. Grades: 3 C + W, 6 W.** Named in the sweep and never asked for at `ce7cd72` —
all W with the same unblock action: `3796753621` Nutrition Makes Sense Immersive Addon. Three
more the browse pass left `not_requested` were read by the repair pass below and now carry real
stats: `3492090092` TwisTonFire - Calories & Nutrition, `3426165280` Fix NaN Nutrition Stats,
`3388844542` Minimal Display Bars + Nutritions + Discomfort [B41/B42.20].

**This section's tables were written against `74ba5b0` and are pinned to `ce7cd72`, which is
what the repo holds.** A Task-2 repair pass timestamped `meta.fill` **2026-09-10 16:56** —
uncommitted while this page was written, committed as `ce7cd72` — runs
six more item pages (`3354834585`, `3388844542`, `3426165280`, `3430945294`, `3492090092`,
`3653719735`), taking `details_requested` from 9 to **15** and the never-asked-for rows from 171
to **165**, and replaces the old not-fetched `error` string with
`details_status: "not_requested"` — a decision about the run, not a fetch failure.
**Nothing above changes**: the same 212 results, the same 180 distinct ids, the same 3 installed
rows, the same 0 term failures. A reader on a later commit should take the census from
`meta.counts` and the not-fetched marker from `details_status`, not from any sentence.
Ev W.

**Two coverage facts bound what this sweep may be used for.** 176 of the 179 installed workshop
items are returned by none of the eight terms; and `3774789651` Long Term Preservation — the one
installed mod carrying both nutrition signals — **appears in none of the eight pages**, while a
third-party patch to it does. Absence from this dataset is not evidence about a mod. Ev W.

---

## B42 status per candidate

`mod_lint` counts are `python tools/mod_lint.py <item>` on 2026-09-10; the corpus-wide sweep at
13:47 that day was **84 findings — 3 ERROR, 30 WARN, 51 INFO across 230 mods**, and every mod below
is inside that sweep. `Bytes` is the whole mod folder on disk, every version folder included.
**`workshop_item_mtime` is a download stamp, not an update stamp** — Steam rewrites a mod folder
inside an item without touching the item folder — so a real "last updated" has to come from the
Workshop page. Eight of these nine are in none of the sweep's 180 rows, so `--details-ids` could
not reach them; `python tools/workshop_search.py --catalog-ids <the nine>` read the nine item
pages directly on **2026-09-10 17:46**, 9 fetched / 0 failed in one pass, into
[`data/workshop-catalog-details.json`](../../data/workshop-catalog-details.json). That is where
the *Workshop updated* column comes from, and it is **W**: a page reading, at that minute.

**The two stamps disagree in both directions, and neither is wrong.** `3774789651` has **never
been updated** since it was posted while its item folder was written 2026-09-01; `3624538051` was
updated on the page at 4:53am on the day of this read while its item folder still says
2026-08-12. A cross-check falls out of the same pass: the page's *File Size* equalled the sum of
`bytes` over the item's mod folders on **all nine**, to the byte — including the two items that
ship several mods (`3498347699` 1 737 473, `3624538051` 3 641 208), whose page title and size
are the **item's**, not the named mod's.

| Mod id | Version folders | Live | `mod.info` at | Lint E/W/I | Deps | Deps installed | Bytes | Download stamp | Workshop updated | Ev |
|---|---|---|---|---|---|---|---:|---|---|---|
| `SKITTLE_LongTermPreservation4220` | `42.20` | `42.20` | `42.20/mod.info` | 0/0/1 | none | n/a | 239 131 | 2026-09-01 13:13 | **never** (posted Jul 30 @ 6:31pm) | C + W |
| `simpleStatus` | `42.16`, `42.15`, `42.14`, `42` | `42.16` | `42.16/mod.info` | 0/0/1 | none | n/a | 1 132 005 | 2026-08-12 00:03 | Apr 5 @ 5:37pm | C + W |
| `AutoCook` | `42.13`, `42` (+ `common/`) | `42.13` | **`common/mod.info`** | **0/1/0** | none | n/a | 129 161 | 2026-08-12 00:03 | Sep 6 @ 9:04pm | C + W |
| `SkillRecoveryJournal` | `42.20.1`, `42.19` | `42.20.1` | `42.20.1/mod.info` | 0/0/1 | `ChuckleberryFinnAlertSystem`, `errorMagnifier` | **both** (`3077900375`, `2896041179`) | 4 460 232 | 2026-08-12 00:03 | Sep 4 @ 8:57am | C + W |
| `MoodleFramework` | `42.20`, `42.13`, `42.0` (+ `common/`) | `42.20` | **`42.0/mod.info`** | **0/1/0** | none | n/a | 180 592 | 2026-08-12 00:03 | Sep 7 @ 5:15am | C + W |
| `SomewhatTraitsCore` | `42.15`, `42.13`, `42.12` | `42.15` | `42.15/mod.info` | 0/0/0 | none | n/a | 277 350 | 2026-08-12 00:03 | Aug 10 @ 3:03am (item: 3 mods) | C + W |
| `CleanUI` | `42.19` … `42.12` (6) | `42.19` | `42.19/mod.info` | 0/0/0 | `NeatUI_Framework` | **yes** (`3508537032`) | 11 300 184 | 2026-08-17 13:37 | Sep 7 @ 5:57am | C + W |
| `Economy` | `42` | `42` | `42/mod.info` | 0/0/0 across the item's **5** mods | `QuestSystem` | **yes** (same item) | 600 070 | 2026-08-12 00:03 | Sep 10 @ 4:53am (item: 5 mods) | C + W |
| `BeyondTen` | `42` | `42` | `42/mod.info` | 0/0/0 | none | n/a | 348 184 | 2026-08-12 00:03 | Sep 4 @ 1:25pm (read twice) | C + W |

**9 rows. Grades: 9 C + W** — every row now pairs a file reading with a page reading, and
`3765241705` was read on both routes (sweep 16:26, catalog pass 17:46) with the same answer.
The three findings that matter:

- **`AutoCook` — `mod-info-place` WARN.** Its `mod.info` is in `common/`, not in the newest
  version folder `42.13/` that B42 runs. It is one of the 6 corpus-wide `mod-info-place` warnings,
  and it is a real B42-status finding rather than cosmetics, because the same mod's *code* is split
  the same way (§ Open questions Q1).
- **`MoodleFramework` — `mod-info-place` WARN, and a split that is worse.** Its `mod.info` sits in
  the oldest folder, `42.0/`. Its newest folder `42.20/media` ships **exactly one file**,
  `lua/client/MF_ISMoodle.lua`, while `MF_Config.lua` exists only in `42.0/media` and
  `common/media`. Whether the moodle framework is therefore whole on 42.20.4 depends entirely on
  the merge rule this page refuses to assert — recorded as § Open questions Q1, not as a verdict.
- **`SKITTLE_LongTermPreservation4220` is the only nutrition candidate whose *only* version
  folder is `42.20`** — `version_dirs == ["42.20"]`, `media_at == ["42.20/media"]`, no `common/`.
  It is not the only one that *ships* a `42.20`: `MoodleFramework` ships `42.20`, `42.13` and
  `42.0`, and `ZVirusVaccine42BETA`'s live folder is `42.20` with its `mod.info` in it. What is
  rare is having nothing else. Two mods on this page have an unambiguous live tree, not one —
  `Economy` is the other (`media_at == ["42/media"]`), and it is out of the picks on size. Ev C.

**Teardown readiness — what a profile can already do with each.** `pzt run --profile` /
`pzt scenario --profile` copy a mod into a per-run cache by its **resolved id** and run
`[[verify]]` bus probes before the session counts
([`docs/testing/profiles.md`](../testing/profiles.md)). The per-mod instrument for slices 09–11 is
the pair of reflective commands measured in this slice: **`witness.fields <player|item> <id>
<getter,…>`** and **`witness.moddata [player[:<user>]|item:<id>|global:<name>] <key…>`**, which
answer on both sides and name the subject that answered in `resolved`. Both live in the
`witness.*` block of `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, and
the command list in [`../testing/README.md`](../testing/README.md) § Command bus is the
authority for them.

| Mod id | `media_at` (the zero-guard) | Profilable today | The one thing a probe must settle | Ev |
|---|---|---|---|---|
| `SKITTLE_LongTermPreservation4220` | `42.20/media` only — **no `common/media`, so its zeros are trustworthy** | yes | does the ×0.70 on a crafted instance reach the client, and through which packet | C |
| `simpleStatus` | `42.14`, `42.15`, `42.16`, `42`, and a B41 root `media` — **no `common/media`** | yes | what the client's mirror shows against the server's store at the moment of a write | C |
| `AutoCook` | `42.13/media` **and `common/media`** — every zero on this row is suspect | yes, but the copy must carry `common/` | whether the live folder alone is a working mod at all | C |
| `SkillRecoveryJournal` | `42.19`, `42.20.1`, `common/media`, and a B41 root `media` | yes | its `sendClientCommand` / `OnClientCommand` bus under a second client | C |
| `MoodleFramework` | `42.0`, `42.13`, `42.20`, `common/media` | yes | whether `MF_Config` is present at runtime on 42.20.4 | C |
| `SomewhatTraitsCore` | `42.12`, `42.13`, `42.15`, and a B41 root `media` | yes — but the item ships **3** mods, so a profile must name the `id` | whether an `OnTick` server-side calorie write survives the 1 Hz push | C |

**6 rows. Grades: 6 C.**

---

## API surface

One row per API class × candidate, each with the `file:line` of one real use in the **live** version
folder. Counts are the inventory's `signals`; the citation is a hand reading. The
monkey-patching rows count **`signals.global_write_vanilla`** — `function IS…:` headers — which
is a **different signal** from § Sweep 1's `patch` column (`signals.monkey_patch`, the
save-and-wrap idiom). AutoCook is 21 here and 0 there; `SomewhatTraitsCore` carries both, and
its row says which number is which.

| API class | Mod id | Count | One real use | Ev |
|---|---|---:|---|---|
| `Events.<X>.Add` | `SomewhatTraitsCore` | 37 (`OnTick` 24, `OnPlayerUpdate` 6) | `42.15/media/lua/server/SWTraitsCore_server.lua:89` `Events.OnTick.Add(SWAdaptiveMetabolism)` | C |
| `Events.<X>.Add` | `SkillRecoveryJournal` | 15 (`OnServerCommand` 3, `OnClientCommand` 2, `OnGameBoot` 2) | `42.20.1/media/lua/client/Skill Recovery Journal Client Events.lua:111` | C |
| `Events.<X>.Add` | `CleanUI` | 18 (`OnTick` 5, `OnGameBoot` 5, `OnGameStart` 5) | client only, all 18 | C |
| `Events.<X>.Add` | `simpleStatus` | 2 (`OnCreatePlayer`, `OnKeyPressed`) | `42.16/media/lua/client/ss.main.lua:82` `Events.OnCreatePlayer.Add(onCreatePlayer)` | C |
| `Events.<X>.Add` | `SKITTLE_LongTermPreservation4220` | 1 (`onAddForageDefs`) | `42.20/media/lua/shared/Foraging/forageable_items.lua:28` — its whole Lua event surface | C |
| `Events.<X>.Add` | `AutoCook` | **0 in the live folder** | the only registration, `Events.OnPreFillInventoryObjectContextMenu.Add`, is `common/media/lua/client/AutoCook_RISCookMenuInsertion.lua:117` — a file `42.13/` does not ship | C |
| `sendClientCommand` | `SkillRecoveryJournal` | 5 | `42.20.1/media/lua/client/Skill Recovery Journal Context.lua:138` | C |
| `sendClientCommand` | `SomewhatTraitsCore` | 3 | `42.15/media/lua/client/SWTraitsCore_client.lua:61` | C |
| `sendClientCommand` | `CleanUI` | 8 | `42.19/media/lua/client/ISUI/ISInventoryPane.lua:3069` — vanilla's own `'object'` module, carried over in a copied file | C |
| `OnClientCommand` | `SomewhatTraitsCore` | 1 | `42.15/media/lua/server/SWTraitsCore_server.lua:497` | C |
| `OnClientCommand` / `sendServerCommand` | `SkillRecoveryJournal` | 9 / 9 (plus 3 `OnServerCommand`, which the inventory has no signal for) | `42.20.1/media/lua/client/Skill Recovery Journal Admin Panel.lua:446` `Events.OnServerCommand.Add(onServerCommand)` — the client half of its own bus | C |
| `sendServerCommand` | `simpleStatus`, `AutoCook`, `SKITTLE_LongTermPreservation4220` | **0** | none of the three picks has a command bus of any kind | C |
| `getModData` | `AutoCook` | 9 | `42.13/media/lua/client/AutoCook.lua:35` and `…/ISCharacterCook.lua:238,258,339` — settings persisted per player | C |
| `getModData` | `simpleStatus` | 4 | `42.16/media/lua/client/ss.main.lua:59`, `…/ISSSBar.lua:33` | C |
| `transmitModData` | `simpleStatus` | **1** | `42.16/media/lua/client/ISSSBar.lua:35`, immediately after writing `md["SimpleStatusConfig"]` at `:34` — the only `transmitModData` among the three picks | C |
| `transmitModData` | `AutoCook`, `SKITTLE_LongTermPreservation4220` | 0 | AutoCook writes player modData on the client and never transmits it | C |
| monkey-patching (`global_write_vanilla`) | `CleanUI` | 287 | `42.19/media/lua/client/ISUI/InventoryWindow/ISInventoryWindowContainerControls.lua:24` — CleanUI ships whole *copies* of vanilla UI files, so the count is a file-replacement count | C |
| monkey-patching (`global_write_vanilla`) | `SomewhatTraitsCore` | 56 `function IS…:` + 66 `monkey_patch` | `42.15/media/lua/client/SWTraitsCoreOverrides_client.lua:8-9` — `local original_ISMedicalCheckAction = ISMedicalCheckAction.new` then `function ISMedicalCheckAction:new(...)`; the save-and-wrap idiom done 66 times | C |
| monkey-patching (`global_write_vanilla`) | `AutoCook` | 21 (`monkey_patch` 0) | **all 21 are `function ISCharacterCook:…` in `42.13/media/lua/client/ISCharacterCook.lua`, and `ISCharacterCook` is AutoCook's own class** — no such name exists in the game's `media/lua`. The signal name overstates it: this is a new `ISPanelJoypad` subclass, not 21 vanilla overrides | C |
| item / recipe script overrides | `SKITTLE_LongTermPreservation4220` | 15 live item blocks (= `script_item_blocks`), **8** `craftRecipe` blocks | `42.20/media/scripts/items/items_dried.txt:8` `item CuredPork` inside `module Skittles`; `42.20/media/scripts/recipes/recipe_cured.txt:8` `craftRecipe MakeCuredMeat` | C |
| item / recipe script overrides | `simpleStatus`, `AutoCook` | **0 script files** | neither ships a `scripts/` folder in any folder; they cannot change an item definition | C |
| script → Lua hooks | `SKITTLE_LongTermPreservation4220` | **12** `OnCooked`, 2 Lua `onCreate`, 1 `onTest`, plus 2 Java `RecipeCodeOnCreate` | `items_dried.txt:22` `OnCooked = OnCookedTest` (4 items) and `:160` `OnCooked = CannedFood_OnCooked` (8 items); `recipe_cured.txt:12-13` `onCreate = AdjustStates`, `onTest = TryMeat`; `:78` `OnCreate = RecipeCodeOnCreate.makeJar` and `:110` `…applyLidCondition` are the Java pair | C |
| sandbox options | `SkillRecoveryJournal` | 30 `SandboxVars.` reads, `sandbox-options.txt` present | `42.20.1/media/lua/client/Skill Recovery Journal SkillProgressBar.lua:26` | C |
| sandbox options | `SomewhatTraitsCore`, `Economy`, `QuestSystem` | present | the three picks ship **none** — nothing to configure, and nothing to mis-configure in a profile | C |

**24 rows. Grades: 24 C, 0 M, 0 W.**

---

## MP behaviour

This is the section every system doc in this library carries, and here it decides what each
teardown can even hope to observe.

**The server owns the store.** `Nutrition`, hunger, thirst, weight, traits and aging are
server-side; a client runs `updateWeight()` and throws the result away, and the client's copy is
refreshed by a full-snapshot `PlayerStatsPacket` on a 1 000 ms `UpdateLimit`. A client-side write
to a player stat is measured to revert **within 1.5 s**. The wiki says the same thing in its own
words — *"Since Build 42.13.1 release, server side handles most of the logic for player damage,
item stats etc."* ([networking mirror](../../references/wiki-mirrors/networking.md), page version
42.13.1). Ev C + M (slices 01–03) + W.

| Fact | Mechanism | Consequence for a mod on this page | Ev |
|---|---|---|---|
| `Nutrition` is server-owned; the client mirror lags up to 1 Hz | `PlayerStatsPacket.write` is an unconditional full snapshot at 1 000 ms | `simpleStatus` can only ever draw the mirror. Its bars are correct to within one push and cannot be more correct than that | C + M, slices 01–03 |
| A client-side player-stat write reverts | measured: client `stats.set hunger 0.9` read back `0.3004` at t = 1.42 s while the server never left `0.3007` | `SomewhatTraitsCore`'s calorie write is on the **server** and therefore is the one that sticks; the same code in `lua/client/` would be a no-op with a visible flicker | **M** `exp03-20260910-045523` |
| `ItemStatsPacket` carries the macro block but **not** `age` / `offAge` / `offAgeMax` / `freezingTime` | the packet's 39 applied item-state values, field by field (slice 02) | LTP's `setOffAge(1000000000)` / `setOffAgeMax(1000000000)` at `recipe_meats.lua:39-40` change fields the packet does not carry. Whether the client ever learns the crafted item is now non-perishable is the slice-09 question | C, and **M** for `age` (`exp02-20260910-030433`) |
| A zero-valued `ItemStatsPacket` field can arrive stale | twenty fields are written only when non-zero, `parse` mirrors the guard, `applyItemStats` applies unconditionally, and the receiver reuses one cached packet per type with no reset | any client-side `getCalories()` on an item that *should* read zero may be reading the previous item's number — the trap under AutoCook's client-side recipe filter | C, and **M** for `cookingTime` |
| Player modData does not cross sides until `transmitModData()` | `IsoObject.transmitModData()` → `ObjectModDataPacket`, whose `write` serialises the **whole** table | `simpleStatus` transmits (`ISSSBar.lua:35`); `AutoCook` does not, so its per-player settings live only on the client that set them | C + **M** `exp08-20260910-152944` |
| `transmitModData()` moves the whole table, not the changed key | measured: server `keyCount` went 4 → 6 after the client transmitted **one** key, a `hotbar:table` riding along | a teardown that writes one probe key on the client and transmits is rewriting the server's copy of every other key on that character | **M** `exp08-20260910-152944` |
| An item's modData is **not the same table on the two sides** | `InventoryItem.setCustomName` unconditionally `rawset`s `customName` into modData, and `InventoryItem.load` (client deserialization), `SyncItemFieldsPacket.processClient/processServer`, `CraftRecipeData.createOutputItems` and two corpse paths all call it — six sites, jar-verified | measured on one apple: server `getModData() == {}`, client `{"customName": "Apple"}`, same instance `#199691187`. Every item-modData reading in slices 09–11 must name the side, and `customName` is excluded from any mod-key census | **M** `exp08-20260910-152944` (`item_sides_cross_check`, n = 1) |
| When item modData *does* move, it moves wholesale | `SyncItemFieldsPacket.processModData()` `wipe()`s the receiver's table and `rawset`s every key of the sender's | a mod writing item modData on one side loses it to the next such sync from the other — the shape of the ItemQuality failure, restated for modData | C |
| `SyncItemFieldsPacket` carries condition and modData but **not** `conditionMax` | the ItemQuality teardown's root cause | the standing rule: never store authoritative mod state in an unsynced Java field | C, [teardowns/itemquality.md](teardowns/itemquality.md) |
| The three client-only boot events never fire on a dedicated server | `OnCreatePlayer`, `OnGameStart`, `OnLoad` are marked *client only* on the [Lua_event mirror](../../references/wiki-mirrors/lua-event.md) (page version 42.20.4); `OnInitGlobalModData` and `OnServerStarted` are the server-side pair | `simpleStatus` initialises in `OnCreatePlayer` and has **no** server-side counterpart — by construction it cannot be authoritative about anything | W + C |

**10 rows. Grades: 2 C, 3 M, 4 C + M, 1 W + C.**

**What follows for the three picks.** A **client-only macro write can only ever show the 1 Hz
mirror** — that is simpleStatus's whole read path and AutoCook's whole crafting path, and neither
mod is wrong to be client-side, because neither claims authority. **A mod that edits an item's
fields client-side desyncs silently**, which is the ItemQuality class of bug and the reason LTP's
server-side `recipe_meats.lua` is the interesting one: it writes on the authoritative side, into
fields the item packet only partly carries. Slices 09–11 answer that with `witness.fields` and
`witness.moddata` run on **both** sides of one session, and slice 09's first pass owes the
client-side item-modData census the slice-08 probe did not run.

---

## The three picks

**Criteria, applied in order.** (1) **Installed locally** — only an installed mod can be linted,
profiled and measured; a Workshop row is W and cannot be promoted however relevant it looks.
(2) **Touches the nutrition surface directly** — a macro write, a script macro definition, or a
nutrition read. (3) **B42-ready on the current build** — a version folder the build resolves, a
lint that does not error, dependencies installed. (4) **MP behaviour worth measuring** — it writes
state, or it reads state the server owns. (5) **Small enough to read whole in a 2 h teardown.**
(6) **Not already torn down** — ItemQuality and BeyondTen are done.

Applying (1) removes every one of the six most on-topic Workshop items, including
`3736275816` ApocalipseBR - Nutrition Sync Fix, which is the closest thing on the Workshop to this
library's own subject. Applying (2) leaves the 19 mods of sweeps 1 and 2. **Applying (3) removes
nobody**: all 19 resolve a version folder the build reads and none lints ERROR, so B42 status
never eliminates — it only annotates, which is why two picks are not on a `42.20` folder.
`simpleStatus`'s newest folder is `42.16` and `AutoCook` carries a `mod-info-place` WARN; both
are B42-current enough to boot, and each of those facts is itself a teardown finding. Applying
(5) removes `CleanUI` (1 064 KB of Lua over 54 files) and `QuestSystem` / `Economy` (718 + 503
KB, and their own resident framework). Applying (6) removes `BeyondTen`. What is left is ranked
by (4).

**(4) is what removes the eight script-only mods, and it is not a size judgement.** A pure
content mod — item definitions and nothing else — scores zero on "MP behaviour worth measuring"
because **script data is parsed identically on both sides and never synced**: the server and the
client each read the same `.txt` at load and there is no packet, no command and no modData in
the picture, so a paired snapshot has nothing to disagree about. `OCsPacking` is the sharpest
case: 308 item blocks, 76 nutrition keys, B42-live, and **5 KB of Lua in a 230 KB folder** —
well inside the 2 h box, and less Lua than two of the three picks (`simpleStatus` 46 KB,
`AutoCook` 41 KB) — and it is still out, because a teardown of it would produce no measured MP
row at all.
The same reasoning removes `Horse`, `ZVirusVaccine42BETA`, `JadePackingSD`, `69mini`,
`GirthsTweaks`, `SDQuests` and `biogas`. Ev C.

**Among the code mods, (4) is ranked by domain relevance and finding-richness, not by hit
count** — which is why `AutoCook` is pick 3 and `SomewhatTraitsCore` is a fall-through despite
the latter owning the corpus's only **server-side player** calorie write
(`42.15/media/lua/server/SWTraitsCore_server.lua:84,86`). AutoCook sits on the cooking pipeline
our own mod extends, and it arrives carrying three live findings of its own (a `mod-info-place`
WARN, a live folder with no event registration, two `require`s that resolve only in `common/`);
`SomewhatTraitsCore`'s write is one line of behaviour on a trait we do not ship, its item packs
three mods so a profile must name the id, and its 66 save-and-wrap sites are a *patching*
lesson already covered by the BeyondTen teardown. Ev C.

| # | Slice | Mod id | Item | Why this one, against the criteria | Ev |
|---|---|---|---|---|---|
| 1 | 09 | `SKITTLE_LongTermPreservation4220` | `3774789651` | The domain twin, and the only nutrition candidate whose **only** version folder is `42.20` (`version_dirs == ["42.20"]`). Both mechanisms in one 239 KB mod: 15 live `module Skittles` item blocks, 14 of them food with a full macro set, **and** a **server-side** `OnCooked` hook that multiplies all four macros and `HungerChange` by 0.70 on the crafted instance (`42.20/media/lua/server/recipe_meats.lua:45-49`) while pinning `offAge`/`offAgeMax` to the non-perishable sentinel at `:39-40` — fields `ItemStatsPacket` does **not** carry. That is exactly the question slice 02 left open, now on a real mod. No deps, 0E/0W/1I, `media_at` is `42.20/media` alone so every zero on its record is trustworthy | C |
| 2 | 10 | `simpleStatus` | `2867431511` | The read/refresh side: **12** nutrition reads, all in one file and all client-side (`42.16/media/lua/client/ss.stats.lua:238,280,294,308,381,404-411`), 47 803 bytes over 7 files, one `transmitModData` (`ISSSBar.lua:35`), one `ISPanel:derive`. It measures what a pure client reader can and cannot see while the server owns the store — and it is the UI our own mod would overlap, since users already watch these numbers. Its newest folder is `42.16`, so it also documents "works, but not shipped for this build", and its live folder has dropped the `lua/server/` file older folders carry: it is now **100 % client** | C |
| 3 | 11 | `AutoCook` | `3388721641` | The cooking-pipeline hook points: it reads `getNutrition()` client-side to choose spices and filter ingredients (`42.13/media/lua/client/AutoCook.lua:214,329`), keeps 9 `getModData` settings it never transmits, and automates the actions our mod must not break. It also carries two live findings of its own — a `mod-info-place` WARN, and a live version folder that ships **no event registration and two unresolvable `require`s**, both of which resolve only inside `common/` (§ Open questions Q1). It is the corpus's sharpest example of the merge question | C |

**3 rows. Grades: 3 C.**

**Fall-through order**, if a pick's teardown profile will not boot or its lint regresses — the pass
that uses one records that it did:

1. `SkillRecoveryJournal` (`2503622437`, the item that ships `42.20.1`) — 134 KB, a real
   `sendClientCommand` / `OnClientCommand` bus (23 net sites), 30 `SandboxVars.` reads, two
   installed deps, and its nutrition reads are in `lua/shared/` so they run on **both** sides.
   Ev C.
2. `MoodleFramework` (`3396446795`) — the new-nutrient moodle dependency question, and the
   `42.20/media`-ships-one-file problem above. Ev C.
3. `SomewhatTraitsCore` (`3498347699`) — 66 monkey-patch sites, the patching exemplar, **and** the
   corpus's only server-side player-calorie write. Item `3498347699` ships **3** mods
   (`SomewhatTraits`, `SomewhatTraitsCore`, `SomewhatTraitsSkills`), so its profile must name the
   `id`, not the item. Ev C.

---

## Discrepancies

Places where two sources of truth disagree, or where an earlier statement in this library is
superseded.

| # | Claim / expectation | What is actually the case | Ev |
|---|---|---|---|
| 1 | `script_item_blocks` is an **exact** count of item definitions ([`data/README.md`](../../data/README.md) § mod-inventory), so LTP's 17 is "17 real items" | **Resolved in `Slice 08: final fix wave` (`9f551f6`)**: it counted `item <Name>` lines *without* stripping `/* */`, which the engine and `tools/food_scan.parse_script` both do, and `mod_inventory` now imports the same `_strip_comments`. LTP's `items_dried.txt` holds five comment blocks: a 36-line `/* OBSOLETE */` at `:374-409` containing two whole item definitions (`DriedPork`, `DriedBeef`), and four two-line `/*DaysFresh = 60,` / `DaysTotallyRotten = 90,*/` pairs at `:180-181, 229-230, 277-278, 325-326`. The **135 → 117** delta (2026-09-10 17:47) is **14 + 4**: the two obsolete definitions carry 7 keys each, while each two-liner cost only its `DaysTotallyRotten` — the `DaysFresh` beside it never matched, because `SCRIPT_KEYS` anchors to line start and that line starts `/*`. Live figures: **15** item definitions, **14** of them food (the fifteenth is `SaltRock`, `ItemType = base:normal`), and **117** key writes. `ZVirusVaccine42BETA` is the second case, 102 → **86** (`LabItemsOld.txt` and `LabTestZone.txt` are each commented out whole). The other seven `script_nutrition` mods are unaffected: 899 → **881** over the nine, 6648 → **6630** corpus-wide | C |
| 2 | The plan's Lua-signal list names **10** mods | The measured list is **11**: `Economy` (`3624538051`, 4 hits, `42/media/lua/shared/Utilities/ShopkeepItemSerializer.lua:240-243`) is absent from the plan's table and present in the data. `data/README.md` § mod-inventory already says 11 | C |
| 3 | The plan's script-signal list names **10** mods, with its own item-block figures | **9.** The scan reads the live version folder only, and the plan's wider figures counted stale duplicate copies: `63Type2Van`'s keys live only in a B41 flat root `media/` (B42 signal 0, B41 signal 7), `ZVirus` reads 36 keys not 72, `69mini` 7 not 21. The plan's **item-block** figures moved too, on the live-folder rule and then on the comment fix (2026-09-10 17:47): `Horse` 56 → **288**, `OCsPacking` 144 → **308**, `ZVirus` 162 → 102 → **86**, `GirthsTweaks` 6 → **14**, `69mini` 97 → **32**, `JadePackingSD` 42 → **125**; and `SkillRecoveryJournal`'s `SandboxVars.` reads 26 → **30** | C |
| 4 | AutoCook has "21 `function IS…:` **redefinitions**" | 21 `function IS…:` definitions, all of them `function ISCharacterCook:…` in the mod's **own** new class. `ISCharacterCook` appears nowhere in the game's `media/lua`, and neither does `ISContinue`. The `global_write_vanilla` signal matches a name shape, not an override; AutoCook's real vanilla-facing patch lives in `common/media/lua/client/ISCharacterInfoWindow_AddTab.lua`, outside the scanned folder | C |
| 5 | A mod declaring `module Base` overrides vanilla items ([`data/README.md`](../../data/README.md) § The two nutrition signals) | Declaring `module Base` is the *capability*; an override needs a **name collision**. Measured across the nine `script_nutrition` mods against the 5 092 distinct `module Base` item names vanilla declares: **one** collision in the whole set, `Horse` redefining `Base.Rope`. Seven declare `module Base`; only **two** define an item under it at all (`Horse` 1, `69mini` 32), and the other five put every definition under a module of their own | C |
| 6 | `simpleStatus` is the cheapest mod for settling slice 07 open question 6 (does `harness.install`'s folder→id rename actually happen?) — [`docs/testing/profiles.md`](../testing/profiles.md) § Open questions 6, and carry-over note 9 | Its folder is `SimpleStatus` and its id is `simpleStatus` — **a case-only difference**, and it settles only half the question. NTFS is case-*preserving*, so the `mods/` listing after a run **would** show which of the two names `harness.install` wrote — that half it can answer. The half it cannot is the **behavioural** one: path lookup on Windows is case-*insensitive*, so `<mods_dir>/SimpleStatus` and `<mods_dir>/simpleStatus` are the same directory, the mod loads either way, and the run proves nothing about whether the rename is *required*. **Pick 1 answers both halves**: `LongTermPreservation4220` → `SKITTLE_LongTermPreservation4220` differs by a whole prefix, so the listing names it and a wrong name would fail to load — and slice 09 runs it first | C |
| 7 | `workshop_item_mtime` is when the mod was last updated | It is a **download** stamp. Steam rewrote the mod folder of item `3490370700` at 13:47 on 2026-09-10 while the item folder still read `2026-08-12`. Corpus range is `2026-08-12` … `2026-09-04` — the shape of one subscriber's download history, not of the Workshop's update history | C |
| 8 | `mod_lint.version_dirs()` and the wiki agree on how a three-part folder name is read | They do not. The [Mod_structure mirror](../../references/wiki-mirrors/mod-structure.md) (page version 42.20.0) says the minor version is **dropped**: `42.1.5` is treated as `42.1`. Our `version_dirs()` tuple-sorts `42.20.1` as itself and ranks it above `42.20`. The corpus has **two** three-part folders, both named `42.20.1` and both a Skill Recovery Journal copy — `2503622437` (beside `42.19`) and `3782784855` (alone, and the one row with no `mod.info`) — and on both, the two readings choose the same folder, so nothing observable differs today. A mod shipping both `42.20` and `42.20.1` would separate them | C vs W |
| 9 | The corpus figures in [approved-modlist.md](approved-modlist.md) — class distribution `173/33/15/5/4`, event histogram `OnGameStart 71/25`, `OnTick 69/14`, `OnPlayerUpdate 54/38`, `OnClientCommand 53/20`, `OnServerCommand 41/14`, `OnCreatePlayer 18/15`, and the heavy-lua sizes (`Economy 497KB`, `GirthsTweaks 269KB`) | All recomputed from the regenerated dataset on 2026-09-10 and corrected in that file: class distribution **175/31/15/5/4**, events **70/25, 70/15, 55/39, 54/20, 43/14, 17/14**, `Economy` **503KB**, `GirthsTweaks` **280KB**. The old figures predate the `42.20.1` resolution fix and Steam's rewrite of `3490370700`. The event census is summed over each record's `top_events`, which keeps only a mod's 8 most-used events, so it is a floor, not a total — that caveat is now in the file too | C |

**9 rows. Grades: 8 C, 1 C vs W.**

---

## Open questions

1. **How do `common/` and the live `42.x/` folder combine?** The
   [Mod_structure mirror](../../references/wiki-mirrors/mod-structure.md) (page version 42.20.0)
   states it plainly — *"1. Common folder. 2. Closest versioning folder to the game version
   (overwrites common files which are present in it)"* — but that is **W**: nothing in this repo
   has confirmed it against the 42.20.4 engine or a run, and
   [`docs/testing/profiles.md`](../testing/profiles.md) § Open questions 1 has its sibling — the
   `mod.info` resolution order — open from the other end. The corpus makes it urgent rather than
   academic:
   `63Type2Van`, `69mini` and `ZVirusVaccine42BETA` keep models, textures and UI in `common/media`
   and Lua plus scripts in a version folder; `MoodleFramework`'s `42.20/media` ships one file while
   its config lives in `42.0/` and `common/`; and **`AutoCook`'s live `42.13/media` registers no
   event at all and `require`s two files (`ISContinue`, `ISCharacterInfoWindow_AddTab`) that exist
   only in `common/media`**. That last one is close to a proof by working mod — AutoCook is a
   popular, functioning mod, so the common folder must be loaded — but it is an *inference*, not a
   reading of the engine, and this page does not promote it. Slice 11's teardown of AutoCook can
   settle it from the outside with one profiled boot. Ev W + C.
2. ~~**`script_item_blocks` and `signals.script_nutrition` do not strip `/* */` comments.**~~
   **Closed** in `Slice 08: final fix wave` (`9f551f6`): `tools/mod_inventory.py`
   imports `food_scan._strip_comments` and all three script regexes read the stripped file, so
   the raw field and this page now agree — LTP **15** items / **117** keys, ZVirus **86**, 6630
   corpus-wide, and `script_item_blocks` matches `parse_script`'s own block count on all nine
   rows. § Discrepancies row 1 keeps the arithmetic. Ev C.
3. **Is `MoodleFramework` whole on 42.20.4?** `42.20/media` ships only `MF_ISMoodle.lua`;
   `MF_Config.lua` exists in `42.0/media` and `common/media`. Under the wiki's merge rule it is
   whole; under a version-folder-only rule the framework loads a moodle class with no config. This
   matters directly, because the new-nutrient UI in our own mod is the reason MoodleFramework is on
   the list at all. Q1 settles it. Ev C.
4. ~~**Does LTP's ×0.70 reach the client, and what happens to the sentinel?**~~
   `recipe_meats.lua:39-49` writes `offAge` / `offAgeMax` (**not** in `ItemStatsPacket`) beside the
   four macros and `HungChange` (**in** it). The crafted item is produced by
   `CraftRecipeData.createOutputItems`, which is one of the six `setCustomName` call sites, so the
   crafted instance carries a `customName` modData key on whichever side built it. Slice 09 reads
   the same instance with `witness.fields` on both sides. Ev C.
   **Closed (slice 09)** — [`teardowns/longtermpreservation4220.md`](teardowns/longtermpreservation4220.md)
   § MP handling, runs `td1-20260910-192457` and `td1b-20260910-202029`. **The ×0.70 reaches the
   client; the sentinel does not.** Four packet-carried writes arrive intact (carbohydrates 0 → 0 carries no information) on the same
   instance (`getID 562521975`, `same_instance true` at every snapshot): calories 300 → 210,
   proteins 50 → 35, lipids 12 → 8.4, `hungChange` −0.6 → −0.42, equal on both sides to within the
   comparison tolerance. The sentinel `1000000000` never crosses — the client kept `offAge 53` and
   `offAgeMax 60` against the server's 1e9 on the two post-cook snapshots 11.1 s apart (the baseline snapshot is not desynced), and nothing later
   repairs it; `isCookable` and `isCustomWeight` desync the same way, making **four** uncarried
   fields, not two. Two corrections to the framing above: the measured instance was **RCON-spawned,
   not crafted** (nothing on the bus executes a `craftRecipe`), so the `createOutputItems` half is
   still C — on that instance `customName` was present on the **client only**; and the packet
   puts **43** fields on the wire, of which **39 are item state** (the other four —
   `containerId`, `id`, `isFluidContainer`, `isFood` — are addressing and presence flags, never
   applied to the item), so slice 02's 39 stands and the field list is the contract either way
   ([`../vanilla/food-item-model.md`](../vanilla/food-item-model.md) § MP behaviour reconciles
   the two counts). Ev **M**.
5. **`AutoCook` writes player modData on the client and never transmits it** (9 `getModData`, 0
   `transmitModData`). Whether its per-player cooking settings survive a relog on a dedicated
   server is unmeasured, and it is the cheapest MP question on the whole page. Ev C.
6. ~~**Three dead or defective code paths in pick 1**, all latent, all worth one line in the
   slice-09 teardown:~~ `AdjustStates` and `AdjustStatesPemmican` (`recipe_meats.lua:26-32`) are empty
   function bodies wired into two `craftRecipe onCreate` keys; `TryMeatLard` and `TryMeatCanned`
   (`:9-22`) are referenced by no shipped recipe; and `TryMeatCanned:19` writes
   `0.15 < sourceItem:getActualWeight() < 1`, which parses as `(0.15 < w) < 1` — a boolean compared
   to a number, which standard Lua raises on. Nothing calls it, so it has never run; whether
   Kahlua raises the same way is unverified. Ev C.
   **Closed (slice 09)** — all three are written up, re-verified on disk, in
   [`teardowns/longtermpreservation4220.md`](teardowns/longtermpreservation4220.md) § Pitfalls /
   anti-patterns 4, with **two additions**: a fourth defect, the *live* `onTest` `TryMeat`, whose
   comment says "only meats above a weight of 0.2" while its body returns `getActualWeight() > 0.0`
   and passes a non-`Food` input unconditionally (`recipe_meats.lua:1,4,6`) — a no-op guard, not a
   dead one; and a fifth, `items_dried.txt`'s brace imbalance (17 `{` against 18 `}` after comment
   stripping), whose row moves **C → M**: the engine loaded all 15 blocks regardless —
   `items.count` answered `foodByModule {"Base": 722, "Skittles": 14}` at join (acceptance run
   `run-20260910-191842`, reproduced on `td1-20260910-192457` and `td1b-20260910-202029`). The
   Kahlua question on `(0.15 < w) < 1` stays open and unreachable: nothing calls it. Ev C + **M**.
7. ~~**No Workshop "last updated" exists for eight of the nine catalogued mods.**~~ **Closed.**
   None of them is in the sweep's 180 rows, so `--details-ids` rejected them by name and `--fill`
   had no row to fill; `tools/workshop_search.py --catalog-ids` reads item pages for ids named
   from outside, and one pass on **2026-09-10 17:46** read all nine (9 fetched / 0 failed) into
   [`data/workshop-catalog-details.json`](../../data/workshop-catalog-details.json). The
   B42-status column is filled from it and graded **W**. `workshop_item_mtime` is still a
   download stamp and still cannot substitute (§ Discrepancies row 7) — the two disagree in both
   directions on this very set. Ev W.
8. **The corpus contains no vanilla food override to learn from.** Exactly one name collision
   exists in the nutrition-bearing script set and it is `Base.Rope`. So the item-pass mechanism our
   own mod needs — re-declaring vanilla `module Base` food items at scale — has **no precedent in
   the approved modlist**, and the nearest evidence is on the Workshop (`3690404044` Nutrition
   Makes Sense and the other five, all W). This is the strongest argument for spending one
   subscription. Ev C + W.

---

## Sources

**Datasets (the column authority, all three stamped in-file)**
[`data/mod-inventory.json`](../../data/mod-inventory.json) — 230 records / 179 items, swept
2026-09-10 17:47, written by `tools/mod_inventory.py`; fields, signal regexes and every caveat in
[`data/README.md`](../../data/README.md) § mod-inventory.
[`data/workshop-search.json`](../../data/workshop-search.json) + `.csv` — 180 rows, fetched
2026-09-10 16:26, quoted at commit `ce7cd72`, written by `tools/workshop_search.py`; columns and
the declared-subset caveat in [`data/README.md`](../../data/README.md) § workshop-search. The
browse and item URL templates are in that file's `meta.source_url_pattern`, so any row can be
re-checked by hand.
[`data/workshop-catalog-details.json`](../../data/workshop-catalog-details.json) — 9 rows, one
per catalogued mod's workshop item, fetched 2026-09-10 17:46 by
`tools/workshop_search.py --catalog-ids` (9 fetched / 0 failed, one pass); it is the source of
the § B42 status *Workshop updated* column and of nothing else.
[`data/README.md`](../../data/README.md) § workshop-catalog-details.

**Mod files read for this page** (all under
`D:\SteamLibrary\steamapps\workshop\content\108600\<item>\mods\<folder>\`, read and never written)
— `3774789651/LongTermPreservation4220/42.20/`: `mod.info`, `media/lua/server/recipe_meats.lua`
(61 lines), `media/lua/shared/Foraging/forageable_items.lua`, `media/scripts/items/items_dried.txt`
(411 lines), `media/scripts/recipes/recipe_cured.txt` (185 lines),
`media/scripts/items/models_skittles.txt`. `2867431511/SimpleStatus/42.16/`: `mod.info` and all
seven `media/lua/client/*.lua` (47 803 bytes). `3388721641/AutoCook/`: `common/mod.info`, the three
`42.13/media/lua/client/*.lua` (42 604 bytes) and the seven `common/media/lua/client/*.lua`.
`2503622437/Skill Recovery Journal/42.20.1/media/lua/`, `3498347699/SomewhatTraitsCore/42.15/media/lua/`,
`3437629766/CleanUI/42.19/media/lua/`, `3396446795/MoodleFramework/` (whole tree),
`3624538051/{Economy,QuestSystem}/42/media/lua/`, `3765241705/BeyondTen/42/media/lua/`,
`3001154607/CustomGamepadUI/42/media/lua/`. Vanilla `media/scripts/**/*.txt` was parsed for the
collision census in § Sweep 2.

**Tools run** `python tools/mod_lint.py <item>` for each of the nine catalogued mods (results in
§ B42 status; the corpus sweep of 84 findings — 3 ERROR / 30 WARN / 51 INFO — is dated 2026-09-10
13:47 in `tools/mod_lint.py`'s own docstring); `tools/food_scan.parse_script` / `.walk` as the
comment-stripping parser behind § Discrepancies rows 1 and 5; `python tools/wiki_mirror.py` for the
four mirrors below.

**Wiki mirrors added by this slice** (CC BY-NC-SA 3.0, PZwiki contributors, all fetched
2026-09-10) — [Mod_data](../../references/wiki-mirrors/mod-data.md) (page version 42.13.1,
4 139 wikitext bytes), [Networking](../../references/wiki-mirrors/networking.md) (42.13.1, 7 904),
[Lua_event](../../references/wiki-mirrors/lua-event.md) (42.20.4, 2 876) and
[Mod_structure](../../references/wiki-mirrors/mod-structure.md) (42.20.0, 20 586). These four are
the vocabulary this page's signal columns are named in; each is listed in
[`docs/references.md`](../references.md).

**Measured runs cited** `exp08-20260910-152944`
([`witness-probe.json`](../../testing/artifacts/exp08-20260910-152944/witness-probe.json)) — the
only live artifact of slice 08: 87.1 s, fixture `default`, build 42.20.4, `server_errors []`,
doctor all-`ok`, 15 graded rows (14 as expected, 1 finding, 0 misses), **n = 1 on one item
(`Base.Apple`) and one player**. Cite `item_sides_cross_check` for the modData asymmetry and the
`moddata_*` probes for the transmit shape; the **seven** *do not cite* rows — among them
`moddata_global.keyCount`, `getMaxWeight` as a body weight, the `getHoursSurvived` gap,
`session.rcon_additem`, `moddata_item` as an independent corroboration, and everything here as a
population (`n = 1`) — are listed in
[`testing/artifacts/README.md`](../../testing/artifacts/README.md).
Earlier runs quoted through this library's own docs, never re-derived here:
`exp02-20260910-030433` (the `ItemStatsPacket` field-by-field analysis and the stale-zero trap →
[vanilla/food-item-model.md](../vanilla/food-item-model.md) § MP behaviour),
`exp03-20260910-045523` (the 1.5 s client-write revert →
[vanilla/body-stats.md](../vanilla/body-stats.md)), and slices 01/03's eating and body-stat
measurements ([vanilla/eating-pipeline.md](../vanilla/eating-pipeline.md),
[vanilla/nutrition-core.md](../vanilla/nutrition-core.md)).

**Prior work in this library** [teardowns/itemquality.md](teardowns/itemquality.md) (the sync
failure this page's MP section generalises), [teardowns/beyondten.md](teardowns/beyondten.md),
[approved-modlist.md](approved-modlist.md) (the corpus tiering this page corrects in
§ Discrepancies row 9), [README.md](README.md) (the teardown queue),
[../modding/patterns.md](../modding/patterns.md), [../testing/profiles.md](../testing/profiles.md)
(profiles, L0 and the folder→id question of § Discrepancies row 6) and
[`../testing/README.md`](../testing/README.md) § Command bus — the authority for this slice's
`witness.*` commands, beside `PZTestKit_Core.lua` and the artifact above.
