# Satiety research 2, dieting consensus harvest (2026-10-09)

The report of Task 28 of Satiety research 2 (2026-10-09): the standard dieting advice on reducing hunger at equal calories, argued as strongly as the evidence allows, followed by its citation review. The review's corrections stand over the report wherever they disagree (in short: four long-term low-GI trials, not five; Das 2007 (CALERIE) is a second year-long head-to-head protein null beside S28.8, against Leidy's direction and the 'protein damps the deficit drive' candidate; the equal-calorie hunger result holds only for Buckland at 12 weeks and its meals also differed in fat, protein and fibre; Stevens' fall is digestible energy; Forde states 14 %). The rows in docs/reference/science.tsv carry the corrected cells; S28.18's composition percentages from a press release were dropped by the controller.

# Task 28 report: the dieting consensus on hunger at equal calories, argued as strongly as the evidence allows

Model: claude-opus-5-5. Status: DONE. Part file: `28-science-part.tsv`, 33 rows (S28.1–S28.33): 31 settled, 2 open, 0 unverified.
- On a scratch copy of the register (`docs/reference/science.tsv` at S1630), `science_delta.py apply --dry-run` mapped them to S1631–S1663; the real apply on the copy, then `science_check.py --register <copy>`, read 0 findings, and `science_check.py --part` read 0 findings. The real register is untouched.
- Every settled row was resolved against its Europe PMC record (`EXT_ID:<pmid> AND SRC:MED`, resultType=core): title, first author, year, journal, volume, pages and DOI match. Every number is the source's own, from the abstract, or from the full text where Europe PMC or PMC has it: Buckland 2018 (PMC6054218), Roager 2019 (PMC6839833), Rebello 2016 (PMC4674378), Bellissimo 2020 (PMC7551271), Houchins 2013 (PMC3582731), Forde 2026 (PMC13084570), Razmpoosh 2025 (PMC12220269), Aston 2008 (PMC2699494; its tables did not extract, so its row is the abstract's).
- No study in the part is already in the register (each pmid grepped). Existing rows are cited by their minted ids.

The question Angus put: at equal calories, do more protein, more fibre, whole and minimally processed food, high-volume low-energy-density eating, avoiding liquid calories, and low-GI carbohydrate reduce hunger or intake? The short answer the evidence gives: the advice is right for **energy density and food mass** (the strongest lever, and the one the shipped model already reproduces), right in direction for **protein** (which the model under-reads), right for **whole-food structure** mostly through water, mass and eating rate, weak for **fibre** beyond the mass it brings, small for **liquid calories**, and not supported for **low GI**.

## 1. High-volume, low-energy-density eating

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.1 | Ello-Martin 2007 | 1 y ad libitum: reduced fat plus water-rich foods vs reduced fat: −7.9 vs −6.4 kg, more food weight eaten (P = 0.025), less hunger (P = 0.003) | RCT | n = 97 randomised, 71 completers; hunger size not in the abstract |
| S28.2 | Buckland 2018 | after calorie-matched fixed meals (≤ 0.8 vs ≥ 2.5 kcal/g) hunger lower at every time point (P < 0.001); total-day intake −1057 kcal (36 %); unchanged between weeks 3 and 12 | RCT | n = 96, within-day crossover probe days inside a 14-week programme; the ad libitum foods also differed in density |
| S28.3 | de Oliveira 2008 | fruit vs oat cookies at equal energy and equal fibre (about 6 g): intake −25 and −20 kcal/d vs +0.9; weight −0.9 vs +0.2 kg over 10 wk | RCT | n = 49, self-reported intake |
| S28.4 | Au-Yeung 2018 | volume-matched konjac gel replacing pasta: no compensation at the next eating, cumulative intake −47 % / −23 %; hunger +31 % at full replacement | RCT | n = 16 |
| S28.33 (open) | — | a pooled size for the hunger difference after calorie-matched density contrasts over weeks | — | — |
| existing | S1230 Robinson 2022; S1469, S1470; S1473 Rolls 2006; S1472 Bell 1998; S1229; S1231; S1468 | daily intake tracks density (SMD −1.002); 77 % pass-through; equal weight eaten; hunger equal | MA / RCT | the harvest's rows |

**Verdict: the harvest's verdict stands and strengthens on time course.**
- **Best estimate.** At equal calories, food of lower energy density (more water, more mass) lowers hunger for hours after the meal and lowers ad libitum intake at later meals, with little compensation. The new rows add what the harvest lacked: the effect **does not fade over weeks of dieting** (S28.2: unchanged at week 12; S28.1: less hunger over a year), and replacing energy with volume at equal volume brings no compensation at the next eating (S28.4).
- **Certainty: moderate.** Direction is high (Robinson's 31-study MA, S1230, and two long-term RCTs agree). The size of the chronic hunger effect is unpooled (S28.33 open): neither long-term trial gives a hunger magnitude in the text read.
- **Where the advice outruns the evidence.** Buckland's −1057 kcal/day is mostly the energy density of the ad libitum foods themselves (equal weight eaten, Bell's rule), not a hunger effect of the fixed meals; the honest equal-calorie reading is the lower hunger after the fixed meals. At the extreme (S28.4, all gel, 77 kcal), hunger rose 31 %: volume without energy does not sate indefinitely.

## 2. More protein

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.5 | Leidy 2007 | equal 750 kcal/d deficit, 30 % vs 18 % protein, 12 wk: the dieting decline in satiety less on higher protein (p < 0.005) | RCT | n = 46; direction only; no ad libitum intake |
| S28.6 | Westerterp-Plantenga 2004 | +48.2 g/d protein, 3 mo maintenance (18 vs 15 %): satiety up, energy intake not different, regain 50 % lower | RCT | n = 148; direction only |
| S28.7 | Lejeune 2005 | +30 g/d protein, 6 mo: fasted satiety up; regain 0.8 vs 3.0 kg | RCT | n = 113; same group as S28.6 |
| S28.8 | Leidy 2015 | 12 wk breakfast 35 g vs 13 g protein vs skipping: high protein lowered daily intake and hunger vs skipping, but **high vs normal protein: no difference in any outcome** | RCT | n = 57 |
| S28.32 (open) | — | no GRADE-rated protein appetite MA exists | — | — |
| existing | S1222 Kohanmoo, S1223 Dhillon, S1380 Ben-Harchache, S1383 Qiu corrected, S1384 Mollahosseini, S1392 Weigle, S1403/S1404 Martens, S1412 Hägele, S1381 (longitudinal null) | acute −7 to −8.5 mm hunger; next meal −39 to −107 kcal; chronic ad libitum intake −6 to −25 % at 25–30 % protein; long-term ratings null | MA / RCT | ungraded MAs |

**Verdict: the harvest's verdict stands.**
- **Best estimate.** Unchanged: an acute level effect of about −7 to −8.5 mm hunger at equal energy (low certainty), and lower ad libitum intake on 25–30 % protein diets over days to weeks (low to moderate). New and consistent: at an **equal energy deficit**, a higher protein share blunts the fall in satiety that dieting brings (S28.5), and modest added protein (15 → 18 %) raises fasted satiety over 3–6 months (S28.6, S28.7). These are direction-only readings from two research groups, with no magnitude in the abstracts.
- **No GRADE-rated meta-analysis** on protein and appetite was found (S28.32 open). The pooled long-term ratings stay null (S1222's 19 long-term trials; S1381), and the one 12-week trial that compared high with normal protein head to head was null (S28.8).
- **Certainty: low** for a sustained hunger effect; **low to moderate** for lower chronic intake.
- **Where the advice outruns the evidence:** "high protein keeps you less hungry for months" rests on direction-only single trials against pooled nulls.

## 3. More fibre

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.9 | Rigaud 1998 | psyllium 7.4 g: hunger −13 %, intake −17 %; no change in gastric emptying | RCT | n = 14, double-blind |
| S28.10 | Stevens 1987 | ~23 g/d psyllium gum crackers for 2 wk: digestible intake −153 kcal/d; wheat bran no effect; faecal energy +63 kcal/d | RCT | n = 12, balanced crossover |
| S28.11 | Salas-Salvadó 2008 | 16 wk psyllium plus glucomannan: postprandial satiety up; weight difference not significant | RCT | n = 200, double-blind; satiety size not in the abstract |
| S28.3 | de Oliveira 2008 | whole fruit vs oat cookies **at equal fibre**: the fruit's effect follows energy density | RCT | n = 49 |
| S28.12 | Roager 2019 | 8 wk ad libitum whole vs refined grain: equal grams of product eaten (244 vs 255 g/d) at lower density, total intake not different (9.22 vs 9.47 MJ/d, P = 0.78), weight lower | RCT | n = 50; no appetite outcome |
| S28.13 | Karl 2017 | 6 wk at equal energy, 40 vs 21 g/d fibre: prospective consumption trend only (P = 0.07, gone in adherent analysis); net energy loss +92 kcal/d through RMR and stool energy | RCT | n = 81, controlled feeding |
| S28.14 | Isaksson 2012 | 3 wk rye porridge vs wheat bread: lower hunger for 4 h, sustained to day 22; free-living intake not different | RCT | n = 24 |
| existing | S1338 Salleh, S1236 Clark & Slavin, S1365 Sanders, S1369 Jovanovski, S1353 Samra, S1366 Flood-Obbagy | only polydextrose excludes zero; 78 % of treatments null on intake; whole-grain effect vanishes at matched calories (low); −0.33 kg chronic (GRADE moderate) | MA / RCT | — |

**Verdict: the harvest's verdict stands.**
- **Isolated viscous fibre.** Small trials of psyllium show what the advice claims (S28.9 −17 % at the next meal; S28.10 −153 kcal/d over 2 weeks; S28.11 higher satiety over 16 weeks). They agree with the harvest's one surviving property, gel-forming fibre (S1339, S1358), and they are a supplement at 7–23 g, a dose no vanilla food carries as isolated fibre. Wheat bran, an insoluble fibre, did nothing (S28.10). Certainty: low (n = 12–14 for the intake readings; S28.11's satiety size is not reported in the abstract).
- **Fibre in whole food at equal energy.** The new rows point the same way as the harvest: the effect follows mass and energy density, not fibre grams. Fruit beat oat cookies of equal fibre (S28.3). Whole-grain products were eaten at equal grams but lower density, and total intake did not differ (S28.12). At fixed equal energy, the appetite difference was a non-significant trend (S28.13). The rye porridge's rating effect (S28.14) did not reach free-living intake, and a porridge carries its cooking water. Certainty: low, as the harvest's review set it (Sanders' calorie-matched subgroup is non-significant, not a demonstrated null).
- **What the advice gets right that is not satiety:** more fibre lowers *digestible* energy: faecal energy +57 to +63 kcal/d (S28.10, S28.13). That is an energy-accounting effect, not hunger.
- **Where the advice outruns the evidence:** "fibre grams reduce hunger" in ordinary foods at equal energy density.

## 4. Whole and minimally processed foods

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.28 | Forde 2026 | two ultra-processed diets matched for density, palatability and variety, slow vs fast texture: −369 kcal/d (95 % CI 221, 517), **steady across 14 days**; appetite ratings not different | RCT | n = 41, single-blind crossover |
| S28.29 | Rego 2026 | 81 % vs 0 % ultra-processed for 2 wk, matched for macronutrients, fibre, sugar and density: buffet intake null (exploratory 18–21 y subgroup up) | RCT | n = 27, proof of concept |
| S28.24 | Rebello 2016 | isocaloric oatmeal (cooked in 360 g water) vs oat cereal (water drunk beside it): hunger AUC lower, lunch −85 kcal | RCT | n = 48; PepsiCo-funded |
| S28.25 | Geliebter 2015 | isocaloric oatmeal vs corn flakes: lunch intake lowest after oatmeal, slower emptying | RCT | n = 36; magnitudes not in the abstract |
| existing | S1442–S1447 (Hall 2019, Hamano, Dicken, Robinson 2026, Barros 2026), S1450 Robinson 2014 | UPF +508 kcal/d inpatient; MA: SMD 0.71 if the UPF arm was denser, 0.02 if matched; slower eating SMD 0.45 | RCT / MA | MA certainty low |

**Verdict: the harvest's verdict stands, and its eating-rate half strengthens.**
- **Best estimate.** Whole-food advantages run through water held in the food (S28.24 is a near-exact replay of Rolls' water-in-food vs water-beside-it, S1231), energy density (S1446), and texture-driven eating rate. Forde 2026 (S28.28) shows the eating-rate effect is not a one-meal artefact: about 12 % of daily intake, steady over two weeks, at matched density, with no change in rated appetite. Processing as such, at matched density and macronutrients, did not move intake (S28.29; S1446's matched subgroup).
- **Certainty: moderate** that density and eating rate carry the effect; **low** that processing matters beyond them.
- **Where the advice outruns the evidence:** "processed food is less satiating per calorie" when density and texture are matched.

## 5. Avoiding liquid calories

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.20 | Houchins 2012 | 8 wk energy-matched fruit and vegetables as beverages vs solids: compensation 53 % vs 78 %, weight +1.95 vs +1.36 kg, **form difference not significant** | RCT | n = 34 crossover |
| S28.21 | Houchins 2013 | acute 400 kcal fruit preload: the challenge meal fell 350 g after solid vs 216 g after beverage (p = 0.005); latency to next eating equal; ratings stable over 8 wk | RCT | the same trial |
| existing | S1474 Stribiţcaia; S1264 DiMeglio; S1265 Mourao; S1427 Reid; S1431 Malik; S1433 de Ruyter; S1476 Cassady | hunger −6.58 mm solid vs liquid; next meal −55.5 kcal (borderline); liquid sugar under-compensated over days to months | MA / RCT | — |

**Verdict: the harvest's verdict stands.**
- **Best estimate.** Solid food sates the next meal more than the same calories drunk (S28.21 replicates S1474's direction with a larger acute contrast). Over 8 weeks, compensation was incomplete for both forms and the form difference was not significant in the one long-term crossover of matched food (S28.20). The chronic SSB evidence stays as the harvest left it: incomplete compensation, direction moderate, size low.
- **Read but not minted:** CHOICE (Tate 2012, pmid 22301929): replacing caloric beverages with water or diet drinks for 6 months gave weight losses not significantly different from an attention control. Weight only, so outside this pass's outcome rule.
- **Where the advice outruns the evidence:** "liquid calories are not compensated at all" (S28.20: 53 %).

## 6. Low-GI or slowly digested carbohydrate

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.15 | Sloth 2004 | 10 wk ad libitum, matched energy density, fibre and macronutrients: intake and weight not different | RCT | n = 45 |
| S28.16 | Krog-Mikkelsen 2011 | the same trial at 10 wk: fullness slightly higher after the low-GI test meal, lunch intake not different | RCT | not independent |
| S28.17 | Aston 2008 | two 12-wk periods: no difference in intake, weight, hunger, fullness or test-meal intake | RCT | n = 19 crossover |
| S28.18 | Das 2007 (CALERIE) | 1 y, 30 % restriction, high vs low glycaemic load: no difference in intake (doubly labelled water), hunger, satiety or weight | RCT | n = 34 |
| S28.19 | Juanola-Falgarona 2014 | 6 mo isocaloric restriction: hunger and satiety not different among diets | RCT | n = 122 |
| S28.23 | Holt 1996 | across 38 foods, satiety unrelated to glucose or insulin response | EXP | the satiety-index data |
| existing | S1421 Sun (ES −0.01), S1422 Bornet, S1423 Zafar | next-meal null; weight benefit small | MA | — |

**Verdict: the harvest's null strengthens.** Five long-term randomised trials (10 weeks to 1 year) that matched energy density and fibre found no difference in hunger or intake; one reports a slightly higher fullness rating with no intake difference (S28.16). With Sun's pooled null (S1421), certainty for **no effect of GI on hunger or intake at equal energy density and fibre is moderate** (consistent, but every trial is small, n = 19–122). The advice outruns the evidence here: where low-GI foods sate more, they are denser in fibre, water or protein, not lower in GI.

## 7. The satiety index (Holt 1995, S1226): does the potato and oatmeal ranking hold?

| id | source | key value | grade |
|---|---|---|---|
| S1226 (existing) | Holt 1995 | boiled potatoes 323 %; SI correlated with serving weight r = 0.66, water r = 0.64 | EXP |
| S28.22 | Holt 2001 | breads 100–561 %; SI predicted intake (r = −0.88); the strongest predictor was portion size, thus energy density | EXP |
| S28.26 | Bellissimo 2020 | baked, mashed or fried potatoes vs white bread at equal energy and fat: appetite and intake not different | RCT (potato-industry funded) |
| S28.27 | Diaz-Toledo 2016 | four potato meals vs pasta at equal energy: later intake comparable; only fries rated more satiating | RCT |
| S28.24, S28.25 | Rebello 2016, Geliebter 2015 | oatmeal beats an isocaloric cereal at the next meal | RCT |

**Verdict.** The satiety index is real as a ranking of 240 kcal portions, but its own authors' analyses say it is mostly **portion weight** (S1226 r = 0.66; S28.22 "portion size and thus energy density"). Plain boiled potato tops the list because 240 kcal of it is a large, watery mass. Once fat is added to equalise energy and macronutrients, potatoes no longer beat bread or pasta at the next meal (S28.26, S28.27). Oatmeal's advantage is real at the next meal, but the oatmeal is eaten with its cooking water inside it (S28.24 shows the comparator drank the same water beside it) and carries more protein and less sugar. Certainty: moderate that the ranking is mostly mass and water; the two potato trials are industry-funded and small.

## 8. Umbrella reviews of dietary strategies

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S28.30 | Hansen 2019 | > 8 wk satiety-enhancing or hunger-reducing foods: weight −3.60 kg (95 % CI 1.05, 6.15) vs control; lower ad libitum intake explained 58 % and 23 % of weight change in two studies | MA | 12 studies; risk-of-bias verdict not in the abstract; weight is the pooled outcome |
| S28.31 | Razmpoosh 2025 | low-fat vs high-fat diets: 3 of 7 studies lower hunger; little or no appetite benefit overall | MA | 9 RCTs, RoB 2: 2 low, 4 some concerns, 2 high |

**Verdict.** No umbrella review of dietary strategies for appetite control was found (searched 2026-10-09). The one pooled analysis of long-term satiety-enhancing foods (S28.30) supports the general claim that foods which reduce appetite help weight control, but it pools heterogeneous products and weight, not hunger. The low-fat appetite review is null to weak (S28.31), consistent with the harvest's fat ruling (fat acts through density).

**Read but not minted (weight-only outcomes, or weaker than what is minted):** Pérez-Escamilla 2012 (DGAC review, "strong" evidence that low-density diets improve weight; pmid 22480489), Stelmach-Mardas 2016 (−0.53 kg; pmid 27104562), Rolls 2005 soups (weight; pmid 15976148), Conceição de Oliveira 2003 (weight; the parent of S28.3), Solah 2017 (per-protocol subgroup only), Kusuma 2026 (mostly animal studies), Wang 2015 (no magnitudes), Leidy 2010 (one-day crossovers: fullness up, hunger not), Huang 2014 (a genotype interaction).

## 9. What this means for the shipped model

**Supported, and now on stronger ground:**
- **Fill by food mass (F, FULL_WEIGHT 0.6) with water staying in the solid lane.** This is how the model reproduces the advice's strongest lever. A low-density meal at equal kcal holds more mass for the same emptying time (ruling 11c-4 empties energy and carries water and fibre out in proportion), so F stays higher and hunger lower throughout the residence, as Buckland measured all day after calorie-matched meals (S28.2). The time course is now supported over weeks (S28.1, S28.2): the model has no adaptation term, and the evidence shows none.
- **Water in food vs beside it.** Rebello's oatmeal trial (S28.24) is a fresh replication of the S1231 contrast the model was fitted to (LIQUID_WEIGHT 0.2): the water inside the porridge sates; the same water drunk beside the cereal does not.
- **Fibre neutral except through mass (#3626, ruling 11c-6).** Every new whole-food row points to mass and energy density (S28.3, S28.12, S28.13, S28.14). The psyllium trials (S28.9–S28.11) concern a supplement no vanilla item is.
- **GI absent.** Now backed by five long-term nulls (S28.15–S28.19) beside S1421.
- **No processing flag.** S28.29 (null at matched density) and S1446's matched subgroup.
- **Liquid lane.** The acute solid > beverage contrast (S28.21) is what LIQUID_WEIGHT already produces; the 8-week form difference was not significant (S28.20).

**Argued against, with size:**
- **Protein's level, about 10× short** (the harvest's § 5 finding, S1222, S1223, S1380, S1383): it stands. The new long-term rows add direction, not a size.
- **Protein and the deficit drive (new, low certainty).** At an equal energy deficit, a higher protein share blunted the fall in satiety (S28.5); added protein raised fasted satiety in maintenance (S28.6, S28.7). The model's deficit drive (`K.hybrid.hungerTarget`'s floor) is diet-blind. In game terms the mod would read a rolling protein share of eaten energy (the intake history it already feeds into P) and damp the deficit drive's rise when protein is high. No source gives a size (abstracts are direction only; S28.32 is open), and the one head-to-head 12-week trial was null (S28.8). Under the measured-or-neutral rule this does not ship; it is a candidate beside the harvest's ketosis damping (S1455 open), with the same weak spot.

**Left out, with size and certainty:**
- **Eating rate and texture, now shown sustained:** about −369 kcal/d (−12 %) over 14 days at matched density, with unchanged ratings (S28.28). It remains satiation the player governs, and the mod has no texture field, so leaving it out stays right. The limitation string could name it as the largest food-side effect the model does not see.
- **Fibre lowers digestible energy:** +57 to +63 kcal/d of faecal energy at 20–40 g/d extra fibre (S28.10, S28.13), with RMR +43 kcal/d in one trial (S28.13). This is an energy-side question, not satiety: if the mod credits every gram of fibre with energy, these rows bound the error. I did not check how the energy kernel counts fibre; the controller may want a separate look.
- **Isolated psyllium:** −17 % at the next meal (S28.9), −153 kcal/d over 2 weeks (S28.10). No vanilla food; leave out.

**Why the reports read as contradicting the advice, and why they mostly do not.** The harvest called fibre and GI neutral and the processing effect "density and eating rate", which reads as rejecting the advice. In game terms the advice largely survives through the mass path: an apple, a soup, a porridge or a salad sates more per kcal in the shipped model because its vector carries water and mass. What does not survive is the claim that the *named nutrient* (fibre grams, low GI, "unprocessed") does the work at equal density. The two places the advice is right and the model is short are protein's level (known, about 10×) and, at low certainty, protein's damping of dieting hunger (new).

## 10. Per piece of advice: does the harvest's verdict stand?

| advice | harvest verdict | after this pass | rows that decide it |
|---|---|---|---|
| more protein | acute level −7 to −8.5 mm (low); chronic intake lower (low–moderate); model ~10× short | **stands**; direction added for blunted dieting hunger (low; no GRADE MA) | S1222, S1380, S1383, S1392, S1403, S28.5–S28.8, S28.32 |
| more fibre | neutral beyond mass; gel-forming fibre the one exception | **stands**; psyllium positives added (low, supplement-only) | S1338, S1365, S28.3, S28.9–S28.14 |
| whole, minimally processed | density and eating rate, not processing | **stands; eating rate strengthened** (sustained 2 wk) | S1446, S28.24, S28.28, S28.29 |
| high volume, low energy density | intake tracks density ~1:1 (moderate) | **strengthens** (sustained over 12 wk to 1 y, hunger lower at equal kcal) | S1230, S1473, S28.1, S28.2, S28.4 |
| avoid liquid calories | modestly less satiating; under-compensated over days (size low) | **stands** | S1474, S1264, S28.20, S28.21 |
| low GI / slow carbohydrate | null at the next meal | **null strengthens** (moderate) | S1421, S28.15–S28.19, S28.23 |
| satiety index ranking | (S1226, correlates only) | the ranking is mostly portion weight; potato's lead disappears at equal energy and fat | S1226, S28.22, S28.26, S28.27 |

## 11. Slug requests and supersede candidates

- **Slugs:** none. Hunger and intake rows use `satiety`; the three psyllium rows use `fibre` (the S1236–S1240 and S1349 precedent).
- **Supersede candidates:** none. No register row is contradicted by better evidence of the same quantity. S1226 stands; S28.22 and S28.26–S28.27 sit beside it.
- **Not independent, named in the range cells:** S28.16 is the Sloth 2004 trial (S28.15); S28.21 is the Houchins 2012 trial (S28.20); S28.23 is the Holt 1995 data (S1226); S28.6 and S28.7 are the same research group's design.

## 12. Concerns

- **Direction-only rows.** S28.1, S28.5, S28.6, S28.7, S28.11, S28.14 and S28.25 give a direction and a P but no magnitude in the text read (paywalled full texts). Each says so in its range cell, and the two open rows name the gaps.
- **Industry funding:** S28.24 (PepsiCo; four authors employees), S28.26 (Alliance for Potato Research and Education). S28.27's funding was not read.
- **Grades.** Crossovers and within-subject designs in random order are graded RCT, the precedent the wave's reviews set. Holt 2001 and Holt 1996 are EXP, as S1226 is. Stevens 1987 ("balanced design") is graded RCT on that precedent; EXP would be the conservative grade if the reviewer reads the order as unrandomised. Buckland 2018's probe days are a within-day crossover; their order's randomisation is not stated in the text read.
- **S28.2's 1057 kcal** is the paper's figure, but it is not an equal-calorie effect (the ad libitum foods differed in density); the row's range cell says so, and the verdict uses the hunger reading.
- **S28.12 (Roager)** carries the abstract's "consistent with a reduction in energy intake", but Table 1 shows total intake not different (P = 0.78); the row carries the table's numbers.
- **Very recent sources:** Forde 2026 and Rego 2026 (2026 volumes, resolved in Europe PMC with DOIs).
- **Provisional ids.** The dry-run mapping S1631–S1663 holds only if no other part is applied first.

---

# Citation review

# Task 28 citation review (dieting consensus)

Model: claude-opus-5-5. Reviewer, read-only. Verdict: **FAIL**. The fixes are small dictated cell corrections, plus report corrections.

## Method
- All 31 settled PMIDs were resolved through PubMed esummary and efetch (2026-10-09). Title, first author, year, journal, volume, pages and DOI match the citation cell for every row. Holt 1996 has no DOI, as cited.
- Every number in every settled row was checked against its abstract.
- Full texts were read through Europe PMC fullTextXML for Buckland 2018 (PMC6054218), Roager 2019 (PMC6839833, Tables 1 and 2), Rebello 2016 (PMC4674378), Bellissimo 2020 (PMC7551271), Houchins 2013 (PMC3582731), Forde 2026 (PMC13084570) and Razmpoosh 2025 (PMC12220269).
- Ello-Martin 2007 (PMC2018610) and Karl 2017 (PMC5320410) return abstracts only through the open XML.
- Das 2007's diet composition was read from the Tufts press release (ScienceDaily, 2007-04-09); the paper's full text was not read.
- No PMID in the part is already in the register.

## Grades
- **Stevens 1987: RCT stands.** It has a control-cracker period and a balanced (counterbalanced) crossover, which is science.md's "controlled crossover".
- **Buckland 2018: RCT stands.** The full text says "a randomized within-subjects crossover design with 2 conditions (LED, HED)". The order was counterbalanced on the first two probe days and reversed for the last two. The parallel SW and SC arms were nonrandomised, but the row's readings are the probe-day crossover. This answers the report's § 12 concern.
- **Holt 2001 and Holt 1996: EXP stands.** Each row's reading is a correlation across foods, not a randomised contrast (the S1226 precedent).
- **The rest are right:** Bellissimo (randomised within-subject, with control and skip arms) is RCT, Geliebter (randomised sequence, with a water control) is RCT, and Hansen and Razmpoosh (systematic reviews) are MA.

## Equal-calorie checks
- **S28.2 (Buckland).** The −1057 kcal/d is correctly kept out of the equal-calorie reading, and the row carries the hunger reading.
  - The fixed meals were matched in energy only. The full text says "The LED breakfasts were lower in energy density and percentage of energy from fat and higher in weight (grams), percentage of energy from protein and carbohydrates, and grams of fiber (Supplemental Table 2)".
  - So the equal-energy hunger contrast is not energy density alone. See defect 1.
- **S28.1 (Ello-Martin)** is an ad libitum advice trial, not equal calories. The row does not claim equal calories, but the report does (R3).
- **S28.18 (Das).** Glycaemic load is confounded with protein: HG was 60/20/20 and LG 40/30/30 (carbohydrate/fat/protein %), with fibre matched. See defect 5 and R1–R2.
- **S28.28 (Forde).** As consumed, the diets differed in protein, 19 vs 15 EN% (Table 3), and in fat EN% by 9 points.

## Roager (S28.12) against Table 1
- Every number matches:
  - total energy 9.47 ± 2.11 (refined) vs 9.22 ± 2.33 MJ/d (whole grain);
  - provided products 255 ± 53 vs 244 ± 50 g/d, P = 0.074;
  - 3.17 vs 2.79 MJ/d;
  - 12.4 vs 11.5 kJ/g;
  - whole grain 13 ± 10 vs 179 ± 50 g/d;
  - weights from Table 2.
- The row correctly does not use the abstract's "consistent with a reduction in energy intake".
- The one problem is the P = 0.78. It is Table 1's one-way ANOVA across **baseline and both diet periods** (Tukey), not a two-period contrast. The text's own statement is that overall intake "did not differ between the two diet periods". See defect 3.

## Defects (row id, cell, problem, corrected cell verbatim)

1. **S28.2, range.** The equal-energy hunger contrast also differs in macronutrients and fibre, and the probe-day crossover's randomisation is stated in the full text. Corrected cell:
   `probe days in a randomised within-subjects crossover (order counterbalanced on the first 2 probe days and reversed for the last 2) at weeks 3-4 and 12-13 inside a 14-week nonrandomised parallel-group weight-management study, n = 96; the ad libitum evening meal and snacks were themselves low or high in energy density, so the intake difference mixes the fixed meals' after-effect with the ad libitum foods' energy density; the hunger difference after the fixed meals is at equal energy, but the low-energy-dense fixed meals were also lower in percentage energy from fat and higher in weight, percentage energy from protein and carbohydrate, and fibre (Supplemental Table 2), so it is not energy density alone; no certainty rating given`

2. **S28.10, range.** "Digestible energy" is energy eaten less faecal energy. The −153 and −115 kcal/d therefore overlap the +63 kcal/d faecal loss, and the report reads them as intake (R4). Corrected cell:
   `balanced crossover of 2-week periods after a 1-week control, n = 12; digestible energy is energy eaten less faecal energy, so the 153 and 115 kcal/d falls include part of the +63 kcal/d faecal loss, and the gross intake change is not in the abstract; no certainty rating given`

3. **S28.12, value.** The P = 0.78 is a three-column ANOVA that includes baseline (a pooled test read as the contrast). Corrected cell:
   `whole grain 179 +/- 50 vs 13 +/- 10 g/day; provided products eaten 244 +/- 50 vs 255 +/- 53 g/day (P = 0.074) at 11.5 +/- 0.6 vs 12.4 +/- 0.5 kJ/g, giving 2.79 vs 3.17 MJ/day from them (P < 0.001); total energy intake 9.22 +/- 2.33 vs 9.47 +/- 2.11 MJ/day (P = 0.78, a one-way ANOVA across baseline and both diet periods; the text states overall intake did not differ between the two diet periods); body weight 85.4 to 85.2 kg on whole grain vs 86.1 to 87.0 kg on refined grain (P < 0.001); the weight difference correlated with the between-period difference in energy intake (P < 0.0001); fasting leptin, GLP-1 and GLP-2 not different`

4. **S28.13, value.** The abstract says the RMR difference was also not significant once nonadherent participants were excluded. The row and the report (§ 9) carry the RMR as if it stood. Corrected cell:
   `207 +/- 39 g/d whole grain with 40 +/- 5 g/d fibre vs 0 g whole grain with 21 +/- 3 g/d fibre: prospective consumption trended lower on whole grain (P = 0.07); resting metabolic rate +43 +/- 25 kcal/d (P = 0.04) and stool energy +57 +/- 17 kcal/d (P = 0.003), a net daily energy loss 92 kcal/d higher (95% CI 28, 156); when nonadherent participants were excluded, the between-group differences in resting metabolic rate and prospective consumption were not significant and the stool-energy difference increased`

5. **S28.18, range.** Glycaemic load was confounded with a 10-point protein and fat difference. Corrected cell:
   `randomised controlled trial (CALERIE), n = 34; all food provided for 6 months, then self-administered for 6 months; the diets also differed in macronutrients (high load 60% carbohydrate, 20% fat, 20% protein; low load 40%, 30%, 30%) and were matched for fibre, palatability and variety (composition per the Tufts release of 2007-04-09, the full text not read), so the contrast is not glycaemic load alone; no certainty rating given`

6. **S28.21, range.** The solid preload carried 470 g of water to match the beverage's volume, and the beverage carried 150 g. The current cell names only the beverage's water. Corrected cell:
   `the same randomised crossover as Houchins 2012 (not independent of it), n = 34; preloads matched on fruit type, energy, carbohydrate, soluble fibre and volume: the solid preload was apple, grapes, dried apple and raisins with 470 g water, the beverage apple and grape juice with soluble fibre added and 150 g water; no certainty rating given`

7. **S28.28, parameter and value.**
   - The 2331 vs 2641 kcal/d are Table 3's means corrected for fat served (a difference of 310). The 369 (95% CI 221, 517) is the main-effect model. Setting them side by side reads as one contrast.
   - The diets were matched on non-beverage energy density.
   - The consumed protein share differed.

   Corrected parameter:
   `daily ad libitum energy intake over 14 days of two ultra-processed diets matched for non-beverage energy density, palatability, portion size and energy served, and variety, that differ in texture-derived eating rate`

   Corrected value:
   `intake 369 kcal/d (95% CI 221, 517) lower on the slow-eating-rate diet (main effect; 2331 vs 2641 kcal/d in the model corrected for fat served), consistent across the 14 days (diet x time P = 0.486) and not attributable to liking or macronutrient intake by the authors' analysis; as consumed, protein was 19 vs 15 EN% and fat EN% differed by 9 points; food eaten 1481 vs 1746 g/d; no notable differences in appetite ratings before or after meals; no weight difference; fat mass -0.43 kg on the slow diet`

8. **S28.25, range.** The abstract's P values are tests across the three conditions, water included. The oatmeal vs corn flakes contrast is stated in the conclusion without its own P. Corrected cell:
   `three conditions in randomised sequence, n = 36 (18 lean, 18 overweight); lunch at 180 min; the abstract's P values are tests across the three conditions including water, and the oatmeal vs corn flakes contrast is the authors' conclusion without its own P in the abstract; serving weights not in the abstract; no certainty rating given`

## Report corrections (28-report.md)

- **R1, § 6 and § 9 (low GI).** "Five long-term randomised trials ... that matched energy density and fibre" is wrong.
  - S28.15 and S28.16 are one trial (Sloth), so there are four trials.
  - Das (S28.18) did not match macronutrients (20 vs 30% protein).
  - Corrected sentence: "Four long-term randomised trials (10 weeks to 1 year; S28.16 is the Sloth trial's meal test) found no difference in hunger or intake; Sloth and Aston matched energy density, fibre and macronutrients, while Das's low-load arm also carried 30 vs 20% protein." The null still holds, so the certainty stays moderate.
- **R2, § 2, § 9 and § 10 (protein).** The protein verdict leaves out Das (S28.18).
  - At an equal 30% restriction for a year, the low-load diet with 30% protein against 20% showed no difference in hunger, satiety, intake (doubly labelled water) or weight.
  - This is a long-term protein null at equal energy, confounded with glycaemic load. It bears directly against the Leidy 2007 direction (S28.5: 30 vs 18%, 12 weeks), and so on the new "protein damps the deficit drive" candidate.
  - Add it beside S28.8 as the second head-to-head null.
- **R3, § 1 and § 10 (energy density).**
  - "Strengthens (sustained over 12 wk to 1 y, hunger lower at equal kcal)" should read: "sustained over 12 weeks at equal kcal (S28.2, whose fixed meals also differed in fat, protein and fibre); lower hunger over 1 year of ad libitum low-density advice (S28.1, not equal kcal)".
  - In § 1, "S28.1: less hunger over a year" is an ad libitum reading. It does not show that an equal-calorie effect persists.
- **R4, § 3 and § 9 (fibre).**
  - "+57 to +63 kcal/d at 20–40 g/d extra fibre" should read "at about 19 g/d extra fibre". The two trials compared 40 vs 21 g/d (Karl) and about 23 vs 4 g/d (Stevens).
  - Stevens' "−153 kcal/d" is digestible energy, which overlaps that faecal loss, so it is not an intake effect alone (defect 2).
  - Karl's RMR +43 kcal/d did not survive the adherent analysis (defect 4).
- **R5, § 4 and § 9 (eating rate).** "About 12 % of daily intake" and "−12 %" are harvester arithmetic. The source states a 14% difference in daily energy intake. The consumed protein also differed (19 vs 15 EN%; defect 7).
- **R6, § 12.** Buckland's probe-day randomisation is stated in the full text, so the concern closes and RCT stands. Stevens' RCT grade is upheld.

## Residuals
- **The source cell.** It reads `28-dieting-consensus.md § Satiety research 2, dieting consensus review (2026-10-09)`. The wave's ruled form ends `<topic> harvest (2026-10-09)`. The controller rules, and the report must be committed under that filename at the mint.
- **Das's composition** comes from a secondary source (the Tufts press release). Read the AJCN full text before the mint if possible.
- **Unread funding.** Diaz-Toledo 2016's funding was not read (Kurilich's affiliation may be industry), and neither was Geliebter 2015's. Each row says so, or is silent; there is no fabrication.
- **Razmpoosh's RoB 2 counts** (2 low, 4 some concerns, 2 high) sum to 8 of 9 included studies. That is the source's own count.
- **Ello-Martin.** An author manuscript exists (PMC2018610), but the open XML is abstract-only. The row's "Europe PMC carries no open full text" is accurate in effect.
- **Unaffected rows.** All the other settled rows (S28.1, S28.3–S28.9, S28.11, S28.14–S28.17, S28.19, S28.20, S28.22–S28.24, S28.26, S28.27, S28.29–S28.31) are verbatim against their sources. The open rows S28.32 and S28.33 are well formed.
