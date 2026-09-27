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
parts we rely on live in [`platform/lua-platform.md#removed-apis`](../../docs/platform/lua-platform.md#removed-apis) and [`platform/lua-platform.md#file-io`](../../docs/platform/lua-platform.md#file-io), the rest in git history.

**Archived:** [modding-hub-archived.md](modding-hub-archived.md) — the pre-2026-09-09 excerpt of the Modding hub page, kept because its 42.20.x modding-news section is gone from the live page.

<!-- reference_gen: contradictions start -->
## Contradictions

Generated from [the claims register](../../docs/reference/claims.tsv) by `python tools/reference_gen.py contradictions --write`; never edit it by hand: `python tools/claims_check.py` fails when it drifts. Each table is one mirror, in the `## Mirrors` order, and lists every live register row of kind `contradiction` whose `wiki:` pointer names that mirror: the row's tag, what the code says (the row's claim), what the mirror says (the words its bound quotes after `mirror wrong:`), and the page that owns the row.

### nutrition.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0136] | The sandbox `Nutrition` option gates `Nutrition.update()` — drain, burn and weight — while intake continues unguarded. | the weight simulation is always on and the sandbox Nutrition option is never mentioned (nutrition.md, 42.11.0) | [`facts/eating-pipeline.md`](../../docs/facts/eating-pipeline.md#walls) |
| [#0137] | Protein has no Strength-XP effect on this build: its only verified effect is `IsoGameCharacter.getRecoveryMod`, and the Fitness and Strength XP gate `canAddFitnessXp` is weight-trait based. | proteins 50 to 300 give 1.5 times Strength XP and below -300 give 0.7 times, self-dated Build 34.5 (nutrition.md, 42.11.0) | [`facts/eating-pipeline.md`](../../docs/facts/eating-pipeline.md#walls) |

### nutritional-values.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0135/M/one-fixture] | The macro values are state-free but hunger is not: `Food.getHungerChange` scales hunger by 1.3 cooked, a third burnt, 1.3 stale and 2.2 rotten, and the mirror's hunger column is the raw script value rather than an arithmetic one. | nutritional-values rows are state-free (nutritional-values.md, 42.20.0), which holds for the macros but not for hunger; its Fat column is the script and Java Lipids | [`facts/eating-pipeline.md`](../../docs/facts/eating-pipeline.md#walls) |
| [#0369/M/n=1] | The nutritional-values rows are state-free for the macros, which are bare field reads with no cooked, burnt, rotten or frozen modifier, but the hunger column is the raw script value that is divided by 100 at instantiation and so is an identity column rather than an arithmetic one, and its fat column is the script and Java lipids. | nutritional-values rows are state-free | [`facts/food-item-model.md`](../../docs/facts/food-item-model.md#walls) |

### food.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0133/M/one-fixture] | Rot leaves all four nutrients untouched and moves neither thirst nor endurance: only hunger (divided by 2.2), stress (divided by 2), boredom and unhappiness (plus 20) and the sickness roll degrade with rot. | as food begins to rot, its effects will become more negative, read as blanket (food.md, 42.20.0); the measured arm is rotten bread, which delivered its full 532 kcal and 99 g of carbohydrate | [`facts/eating-pipeline.md`](../../docs/facts/eating-pipeline.md#walls) |
| [#0134/M/one-fixture] | Burnt is the one real nutrition modifier in the game: `Eat` divides all four nutrients by 5 for a burnt item, while `getThirstChange` divides thirst by 5 and `getHungerChange` divides hunger by 3. | burnt loses most of its positive effects, never quantified (food.md, 42.20.0); measured on four items | [`facts/eating-pipeline.md`](../../docs/facts/eating-pipeline.md#walls) |
| [#0363/C/C-only] | A fridge's five-times figure is true only as the default: the fridge factor is a sandbox enum of 0.4, 0.3, 0.2, 0.1, 0.03 and 0.0 whose default 3 is that five times, it applies only on a powered grid, the Outbreak preset ships 4 for ten times, and unpowered food reverts to the full rate once the electricity-shutoff window closes. | the spoil rate is reduced by 5 times, repeated as increases spoil time by 5 times | [`facts/spoilage.md`](../../docs/facts/spoilage.md#walls) |
| [#0364/M/n=1] | Rot leaves all four macros untouched — 220 kcal, 0 carbohydrates, 9.35 lipids and 31.62 proteins identical at ages 0, 1.9, 2.1 and 4.1 — and only the read-time hunger, stress, boredom, unhappiness and the sickness roll degrade, while thirst and endurance have no rot branch at all. | as food begins to rot its effects become more negative, which reads as blanket | [`facts/spoilage.md`](../../docs/facts/spoilage.md#walls) |

### cooking.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0138] | `Eat` reads calories and macros as bare fields with no skill term anywhere on the intake path, so any cooking-skill effect must be baked into the crafted item at recipe-build time. | cooking increases the nutrition of evolved recipes (cooking.md, 42.18.0); the recipe-build side is unverified here and is an input to slices 02 and 06 | [`facts/eating-pipeline.md`](../../docs/facts/eating-pipeline.md#walls) |
| [#0367/C/C-only] | An evolved dish's age is proportional rather than inherited: phase A sets the new age to the new `offAgeMax` times the old age over the old `offAgeMax` and only when both items have real thresholds, and ingredients contribute no age at all. | an evolved recipe inherits the age of its base ingredient only | [`facts/cooking-and-recipes.md`](../../docs/facts/cooking-and-recipes.md#walls) |

### appliances.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0368/C/C-only] | The appliances fridges table groups tiles by category rather than by container type and carries no spoilage, power or temperature figure, and because the fridge test returns false for anything already a freezer, the cooled shelves and display counter tiles are its likeliest false positives. | the fridges table read as a refrigeration roster, and the page's own banner says tiles were removed during B42 unstable | [`facts/spoilage.md`](../../docs/facts/spoilage.md#walls) |

### evolved-recipes.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0365/C/C-only] | An evolved dish's boredom is zeroed once in phase A and never touched again, only its unhappiness moves as the unmodified value less five less five per duplicate clamped at plus 25 with an over-stuffing term, and the bonus already stops on the second identical copy with the penalty starting on the third. | every ingredient adds minus five boredom and unhappiness the first time, and three of the same negates the bonus | [`facts/cooking-and-recipes.md`](../../docs/facts/cooking-and-recipes.md#walls) |
| [#0366/C/C-only] | `generated/evolvedrecipes.txt` holds 62 evolved-recipe blocks (a 63rd, `AddBaitToChum`, lives in the fishing recipe file) and an item's recipe key attaches both to the matching recipe and to every recipe whose template equals that key. | a roster of about 35 rows with no template mechanism | [`facts/cooking-and-recipes.md`](../../docs/facts/cooking-and-recipes.md#walls) |

### fridge.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0362/M/n=1] | No factor of 25 appears anywhere on the aging path: a freezer applies the same fridge factor as a fridge while the item is unfrozen, and once `freezingTime` reaches 100 the rate is 0.0, stopped rather than divided. | in the freezer compartment the spoil rate is reduced by 25 times | [`facts/spoilage.md`](../../docs/facts/spoilage.md#walls) |
| [#0363/C/C-only] | A fridge's five-times figure is true only as the default: the fridge factor is a sandbox enum of 0.4, 0.3, 0.2, 0.1, 0.03 and 0.0 whose default 3 is that five times, it applies only on a powered grid, the Outbreak preset ships 4 for ten times, and unpowered food reverts to the full rate once the electricity-shutoff window closes. | the spoil rate is reduced by 5 times, repeated as increases spoil time by 5 times | [`facts/spoilage.md`](../../docs/facts/spoilage.md#walls) |

### hungry.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0574/M/n=1] | Hunger does not tick at a flat rate: the coded 9.6e-6 per game-second is 3.456 per cent per game-hour at zero hunger and falls as hunger rises, a first-order approach rather than a linear fill. | the Hungry page states a flat 4.32 per cent per in-game hour, and its 0.00032 per cent per tick is the defines.lua literal 0.0000032 quoted before its multiplication by 3 | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0575/C/C-only] | The health-regeneration tier fires only from HUNGRY level 2 and runs 0.002, 0.0013, 0.0008 then 0.0, that is minus 35, 60 and 100 per cent, with level 1 having no effect at all. | the Hungry page states a cut of about 25 per cent at Peckish and then 25, 55 and 100 per cent; the sister Thirsty page quotes exactly minus 35, 60 and 100, corroborating the code | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0576/C/C-only] | No thermoregulator read of the HUNGRY moodle exists and no healing multiplier is attached to it: its whole footprint is carry capacity, the regeneration tier, the zeroed sleeping health addition at level 4, the level 4 health loss, and for FOOD_EATEN the hunger gate, the poison-decay term and the eat block at level 3. | the Hungry page states that each Hungry level decreases body heat generation and that every positive level heals 750 per cent faster | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |

### thirsty.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0577/M/n=1] | The THIRST moodle thresholds are 0.12, 0.25, 0.70 and 0.84 on a strict greater-than. | the Thirsty page states thresholds above 13 per cent and above 85 per cent, off by a point at both ends | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0578/C/C-only] | The 1.2 running thirst factor is returned only for the local player instance while the running flag is set, which is a different flag from sprinting, and the asleep thirst branch applies neither it nor the heat term. | the Thirsty page states that sprinting carries the same 1.2 thirst factor as running | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0579/M/arith.] | The THIRST level 4 health-loss branch is real and is the harshest severe-moodle term of its class at five times the hunger branch, but its rate is day-length dependent - 11.88 per cent per game-hour on the 60-minute default day and 17.82 per cent on a 90-minute one - and matches no standard day length at 22 per cent. | the Thirsty page states a flat 22 per cent per in-game hour at Dying of Thirst - right in kind, wrong in number, a units error on a real mechanic | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |

### moodle.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0580/M/n=1] | MoodleType registers a distinct FOOD_EATEN moodle that is not threshold-driven from a stat at all but reads the health-from-food timer against 1600, and it is FOOD_EATEN rather than HUNGRY that gates the hunger rate. | the moodle index has no FoodEaten entry and folds the well-fed state into Hungry | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0589/C/C-only] | The thermoregulator's cold-side energy multiplier multiplies resting and sleeping calorie burn and nothing else, because the three moving branches never read it. | the moodle page never mentions the cold side's body effect at all | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |

### trait.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0581/M/n=1] | The weight-band comparisons are inclusive at both ends - 100 kg or more for Obese, 50 kg or less for Emaciated, 85 for Overweight, 75 for Underweight and the open interval between 75 and 85 for normal - and the 35 and 130 endpoints are the weight-change floor and ceiling rather than band edges. | the trait page gives bands of 35-50, 51-65, 66-75, 76-85 as none, 86-100 and 101-130, on the same build 42.20.4, so this is a live contradiction | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0582/M/n=1] | The weight and metabolism trait API strings are WeightLoss and WeightGain and Very Underweight, Underweight, Overweight and Obese, and getKnownTraits returns them lowercased, so a display name must never be matched on. | the trait page gives display names Fast and Slow Metabolism and Very Low, Low, High and Very High Weight | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0583/C/C-only] | applyWeightFromTraits writes 95 kg for Overweight, and canAddFitnessXp blocks from Fitness 6 for Obese, Emaciated and Very Underweight and from Fitness 9 for Overweight, while plain Underweight never blocks. | the trait page states that Overweight's starting weight is 90 and that Obese caps fitness at 7 | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0584/C/C-only] | The Nutritionist trait has exactly one reader in the jar, the food tooltip, and no gameplay use in media/lua. | the trait page states that Nutritionist improves foraging | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0585/C/C-only] | No reader on this jar applies a melee-damage or climb-failure percentage to Emaciated, Underweight or Very Underweight: the climb-failure score branches on Obese and Overweight alone. | the trait page gives per-trait melee-damage and climb-failure percentages for Emaciated, Underweight and Very Underweight | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0586/M/n=1] | The High Thirst doubling is unconditional - both thirst branches, every thirst level, with no health term. | the trait page states that High Thirst makes you twice as thirsty when dying of thirst; the doubling was measured at moderate thirst | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#1260/C/C-only] | `hasTrait` takes only `CharacterTrait` or `CharacterTrait[]` on 42.20.4: there is no String overload. | the mirror tells modders to call hasTrait with a String literal; where a wiki mirror disagrees with the jar, the code wins and the mirror keeps the wiki's version | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |

### fitness.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0587/C/C-only] | The endurance-drain multiplier is composed from a base of 1.4, Overweight 2.9, Athletic 0.8 and a 2.3 stage before pacing and hyperthermia, and the only per-level Fitness curve read in that area is on recovery, running 0.7 to 1.6. | the Fitness page gives a per-level endurance loss curve from 90 to 43 per cent, though its own footnote hedges that column; its recovery column matches the jar exactly | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |
| [#0588/C/C-only] | Fitness applies no term to landing impact: the landing handler's only trait terms are the weight ones, and Fitness enters the vault-fall chance as a subtraction inside a random roll and the bump-trip score additively inside a clamp of 1 to 80, neither of which is a percentage. | the Fitness page states that Fitness reduces damage taken from long falls and gives a flat 2 per cent per level trip reduction | [`facts/body-and-weight.md`](../../docs/facts/body-and-weight.md#walls) |

### mod-structure.md

| Row | The code says | The mirror says | Owner |
|---|---|---|---|
| [#0881/M] | Only one of a mod folder's `mod.info` files is ever read, so shipping two with different ids makes the other id unaddressable. | the B42 page says each version folder has its own `mod.info` — true as a permission, misleading as a plan | [`platform/mod-anatomy.md`](../../docs/platform/mod-anatomy.md#walls) |
| [#1659] | mod_lint.version_dirs tuple-parses a three-part folder name and ranks 42.20.1 above 42.20 as itself. | the Mod_structure mirror says the minor version is dropped, so 42.1.5 is treated as 42.1 | [`platform/mod-anatomy.md`](../../docs/platform/mod-anatomy.md#walls) |
<!-- reference_gen: contradictions end -->
