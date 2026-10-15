# Hunger and the fat store: level or loss (Plan 13 strength research, harvest 9)

Model: claude-opus-5-5. Written 2026-10-15, read-only. Every record was resolved on Europe PMC by PMID and DOI, and each number in the part file was read in the record's abstract or, where stated, its open full text (Kissileff 2012 Tables 1-2 on PMC3260066; Dulloo 2018 on PMC5945583; Buechel 2026 Table 2 on PMC13202672). Rows are `hunger-fat-part.tsv`, S9.1-S9.26: 23 settled and 3 open. Arithmetic in this report is mine and labelled; none of it is in a cell.

## What the mod already does (read before the evidence)

The mod already has a fat-store term, and it works on loss, not on the level of fat:

- `NR_Kernel_Deficit.lua:25-27`: `K.deficit.state(eb24h, fatDep) = clamp(1 + 0.5 * clamp(-eb24h / 3970.55, -1, 1) + 0.5 * fatDep, 0.5, 2.0)`.
- `NR_Server_Metabolism.lua:585-586`: `fatDep = clamp((fmRef - fm) / fmRef, 0, 1)`.
- `NR_Kernel_Body.lua:331`: creation sets `fmRef = spec.fm`.
- `NR_Server_Metabolism.lua:423`: each day close ratchets the reference up, `fmRef = max(fmRef, fm)`, and never lowers it.
- `hungerTarget = clamp((1 - x) * es, 0, 1)`, so the fat term scales the unsated share.

The term applies to everyone. A character created at 10 % fat starts with `fatDep = 0`. The `0.5` is ruling 14's game choice; no study was fitted to it. Registered rows already cover parts of this question, and I did not repeat them:

| Row | What it covers |
|---|---|
| S1254 | Polidori 2016: about 100 kcal/d more intake per kg lost |
| S1255 | CALERIE: hunger rose by less than 10 mm |
| S1256 | Sumithran 2011: hunger still up at 62 weeks |
| S1258 | Weigle 1997: leptin fell 62 % in a 3-day fast with 2.6 % weight loss |
| S1616 | Dulloo 1997: post-starvation hyperphagia correlates with fat recovery (r -0.6) and with fat-free-mass recovery (r -0.5) |
| S0014, S0016 | the reduced-weight state and adaptive thermogenesis |
| S1910, S1911 | body-fat floors |

## 1. Leptin and appetite under fat loss

- **Leptin tracks the level of fat at a stable weight.** Across 275 adults, leptin correlates with % body fat at r = 0.85 (S9.1).
- **The acute fall is mostly a signal of energy balance, not of fat.**
  - Leptin fell 54 % after one week of a moderate deficit (S9.2), 39 % in 4 days at 36 % of requirements (S9.3) and 27 % in 2 days (S9.4).
  - It fell 62 % in a 3-day fast that removed almost no fat (S1258).
  - Keim found the leptin-hunger relation (r -0.6 to -0.7) "not influenced by amount of weight or body fat loss" (S9.2). Mars found the leptin fall did not predict the next days' compensatory intake, which was 143 % and 124 % of requirements (S9.4).
  - The mod's balance term, `eb24h`, already carries this acute part.
- **What outlasts the deficit is the reduced-weight state.**
  - At a stable weight 10 % below usual, on a weight-maintaining diet, post-meal fullness fell from 110.8 to 93.1 mm on a 150-mm scale. Leptin replacement restored it to 107.7 mm.
  - Pre-meal fullness (21.8, 16.1, 21.8 mm) and test-meal intake (949, 924, 931 kcal) did not differ (S9.5).
  - So the depleted state blunts satiation (how full a meal leaves you) more than it raises fasting hunger.
  - Rosenbaum and Leibel read this as a defended minimum. Leptin signals "negative energy balance and decreased energy stores", and leptin given at usual weight "has little, if any, effect" (S9.6, S9.7). The signal is one of deficiency, and it is asymmetric.
- **The Minnesota experiment** lost about 25 % of body weight, 70 % of body fat and 27 % of fat-free mass (FFM) (S9.8).
  - Hyperphagia during ad-libitum refeeding persisted after weight and fat were fully back, until FFM was restored.
  - Dulloo calls this a "memory" of the initial fat and FFM: a set point in the form of a reference, not a level.
  - The FFM deficit is an "active" drive of its own (S9.11). Collateral fattening (S9.8, S9.9) is the fat overshoot it causes.
  - The overshoot grows exponentially as initial % body fat falls (S9.9). For the same weight loss, a lean person's fat store is a larger fraction depleted.

## 2. Level or loss

**Answer: hunger tracks the loss from a person's own reference, not the level of fat.** A chronically low but stable fat mass does not raise hunger.

- **Constitutional thinness: stable low weight, normal or low appetite.**
  - These women eat 7,565 kJ/d against controls' 7,961 (similar), with normal leptin (8.3 ng/mL) and normal T3 and IGF-I (S9.17).
  - They have the lowest ghrelin and the highest PYY of the three groups. Their leptin profile matches controls', while anorexia nervosa's is depressed (S9.18).
  - They resist 4 weeks of +2640 kJ/d overfeeding: +0.22 kg against controls' +0.72. Their anorexigenic hormones rose further (S9.19).
  - They show no group effect on hunger (S9.21).
  - Caveat: these women are underweight but not underfat. They average 18.9 % fat (S9.20), so this is evidence for "stable thin" but not direct evidence for "stable at 10 % fat".
- **Fat level does not predict intake near energy balance.**
  - Fat mass and BMI did not predict meal size or daily intake; FFM did (S9.12).
  - In 242 adults, fat mass had a direct negative path to intake, partly offset by a positive path through RMR. Leptin did not predict intake (S9.13).
  - In 130 mostly normal-weight adults, fat mass was not associated with laboratory intake. It was inversely associated with postprandial hunger (S9.16), a small cross-sectional hint of a level effect. The study gives no size, and it is confounded by restraint.
  - Blundell 2015 states that fat mass is "strongly inhibitory in lean subjects" (S9.15). That is a narrative formulation with no number. Its own reviewers summarise the cross-sectional data as "weak negative or no association" (S9.14).
- **Lean people at low fat show the hormone signature only while losing.** Bodybuilders dieted to 6.5 % fat: ghrelin +20 %, leptin -28 % (S9.22). Non-dieting controls changed nothing.
- **The loss drive outlasts the return of fat.**
  - After contest preparation, physique athletes ate +10.3 kcal/kg FFM/d above baseline 12 weeks later. By then their fat mass was not clearly below baseline and their FFM was above it (S9.23).
  - This fits Dulloo: the drive is tied to the memory of the depletion and to the lean compartment, not to the current fat level.

So the mod's existing input, the depletion from `fmRef`, is the right one. A stable 10 % character should not feel it.

## 3. Size and shape

- **Per kg.** About 100 kcal/d more intake per kg of weight lost (S1254), measured in mostly overweight patients and weight-based, not fat-based. No record gives hunger in mm, or intake, against % body fat or against kg of fat lost in lean people (open S9.24).
- **Small at modest depletion, marked at large depletion.**
  - At modest loss: CALERIE's roughly 25 % restriction in non-obese adults raised hunger by less than 10 mm over 2 years (S1255). Kissileff's 10 % reduced-weight state moved post-meal fullness about 18 mm of 150 and left fasting hunger and intake unchanged (S9.5; my subtraction).
  - At large depletion: Minnesota's 70 % fat loss gave marked hyperphagia for weeks (S9.8; its size in kcal/d is still open as S1618).
  - Dulloo infers a threshold for the related fat-specific thermogenesis: it is seen above a third of fat depleted and not at about 6 % (S9.10). That is a threshold for thermogenesis, not for hunger. It is the only threshold-like reading found.
  - Together these support a convex shape, or a ramp with a soft threshold. They do not support a linear term from zero.
- **Refeeding.** Hyperphagia lasts until FFM is restored, past fat recovery (S9.8). In athletes it is still present at 12 weeks (S9.23).
- **Fat floors and athletes.**
  - The floors are 4-6 % for men (S1910) and the low teens for women (S1911; the authors suggest a minimum of 12-14 %).
  - Athletes near these floors show the hormone signature (S9.22). They report hunger, food focus and binges qualitatively (Buechel 2026, citing their interviews).
  - No hunger-by-body-fat series was found (open S9.26). Rossow 2013 and the other physique case studies were seen only through Schoenfeld 2023's review.

## 4. Recommended form for the mod's hunger drive

Every number below is a game choice unless a row is named.

1. **Input: keep `fatDep`, the fractional depletion from `fmRef`.** Do not add a level term at 12 %.
   - The fraction gives a lean character a stronger response per kg lost, which matches Dulloo's lean-overshoot evidence (S9.9).
   - It leaves a stable thin character at zero (S9.17-S9.21).
   - Angus's "below 12 % triggers hunger" holds for a character who got there by losing fat. It does not hold for one created there.
2. **Shape: a ramp with a soft threshold instead of the linear `0.5 * fatDep`.** Use `FAT_GAIN * clamp((fatDep - FAT_DEP_LO) / (FAT_DEP_HI - FAT_DEP_LO), 0, 1)`.
   - `FAT_DEP_LO` = 0.10 (game choice): near nothing at modest loss (S1255, S9.5).
   - `FAT_DEP_HI` = 0.70 (game choice): full at Minnesota's depletion (S9.8).
   - `FAT_GAIN` = 0.5 to start (game choice): fit it on the replay to S1254's per-kg intake gain, on a reference body.
   - Cap: the existing clamp on `es` at 2.0.
3. **Combination: keep it additive inside the energy state.**
   - The balance term was fitted on short studies with `fatDep` near 0, so changing the fat term leaves those fits alone.
   - Because `es` multiplies the unsated share, the fat term raises hunger between meals and speeds its rise.
   - Alternative, held as a named option: let depletion blunt the satiety read instead (`x * (1 - b * fatDep)`), which is closer to Kissileff's finding that satiation drops (S9.5). It would need the gut fit's oracles re-run.
4. **The reference and refeeding (game choices).**
   - Keep the upward ratchet of `fmRef`. An expanding fat mass gives little feedback (S9.14), and the defended level follows the highest store.
   - Add a slow downward re-basing of `fmRef` toward a stable `fm`, with a time constant of a year or more of game time. The effect is still present at 62 weeks (S1256) and the re-basing time is unknown (open S9.25).
   - Optionally add a smaller FFM-depletion term from the lean reference, which makes hyperphagia last until lean mass is back (S9.8, S9.11). Exclude detraining loss of trained muscle, which no row covers.

**A thin character created at 10 % fat (stable, constitutional) should not feel the term at all**, by the evidence (S9.17-S9.21; S9.12-S9.14). The current code already gives `fatDep = 0` there. If the trait is meant to carry appetite flavour, the evidence points slightly toward lower appetite: lowest ghrelin, highest PYY, resistance to overfeeding (S9.18, S9.19). It does not point to higher appetite.

## Gaps

- S9.24 (open): hunger or intake against % body fat or fat lost in lean people, as a dose-response. This is the missing number behind `FAT_DEP_LO`, `FAT_DEP_HI` and `FAT_GAIN`.
- S9.25 (open): how long the reduced-weight appetite takes to re-base at a maintained lower fat mass.
- S9.26 (open): hunger series across contest preparation against % body fat. Rossow 2013 and Pardue 2017 were not read.
- S1618 (already open): Minnesota's ad-libitum hyperphagia in kcal/d. Keys 1950 is a monograph with no PMID, and the Dulloo reviews give the course only as a figure.
- The constitutional-thinness evidence is in women averaging 18.9 % fat. No record gives appetite in stably lean men at 8-12 % fat.
- The fat-mass direct negative path to intake (S9.13, S9.16) is cross-sectional and has no size usable in the mod.
