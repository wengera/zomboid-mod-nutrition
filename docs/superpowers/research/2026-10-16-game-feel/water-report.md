# Minimum water turnover and the food-water share: a harvest for the game-feel outline

Date: 2026-10-16. Asked by: the game-feel outline (`docs/superpowers/specs/2026-10-16-game-feel-outline.md`), Workstream B item 4, "the water base", and its research pass "Minimum water turnover and the food-water share".
Part file: `.superpowers/sdd/game-feel-research/water-part.tsv`, rows S12.1–S12.15: 12 settled and 3 open. Separately, S0089 is to be settled in place (§ 6). `python tools/science_check.py --part` reports 0 findings.
Each citation was checked against its record in Europe PMC (pmid, title, first author and year), except two. The EFSA opinion was checked through Crossref and its abstract read through the Semantic Scholar and OpenAlex mirrors, because the EFSA and Wiley pages return 403. The WHO note was read from its PDF.
Revised after the citation review `water-part-review.md` (D1–D12 applied with its text, and the controller's rulings).

## 1. The recommendation

**For a sedentary man in a temperate climate who is not sweating, set basal water loss to about 2000 g/day.** This is the water that drink and food must replace. About 1.3–1.4 L of it comes from drinking and about 0.6–0.7 L from food. For how it scales with body size, see § 9.

The outline's 2.2 L (1.5 L drunk plus 0.7 L from food) is inside the range the evidence allows. That figure means about 1.6 L of urine a day (2.2 + 0.3 metabolic − 0.9 breath, skin and faeces), which is still well below the 2.2 L average measured by isotope turnover (S1709).

| route | g/day | rests on |
|---|---|---|
| respiratory | 300 | S1688: 250–350 mL/d |
| skin, insensible (not sweating) | 450 | S1688: lower end of 450–1,900 mL/d (open S12.15: no temperate measurement was read) |
| faeces | 150 | S1688: 100–200 mL/d |
| urine | 1300 | about 650 mOsm/d of solute on a Western diet (S1687), excreted at EFSA's "desirable" 500 mOsm/L (S12.7); above S1688's minimum urine of 500–1,000 mL/d by choice, not an obligatory loss |
| **gross loss** | **2200** | |
| metabolic water produced | −300 | S1688: +250 to +350 mL/d; S12.5: about 10 % of turnover |
| **net loss, met by drink and food** | **≈ 1900, rounded to 2000** | |
| of which food moisture | ≈ 600–700 | 19 % and 0.7 L/d for men (S1708); 618 of 2718 mL/d, 23 % (S12.9); 0.55–0.68 L (S12.8) |
| of which drunk | ≈ 1300–1400 | the remainder |

The 2000 g/day figure is a **game choice** built from cited rows. It is not a cited value, and no single source measures this composite. When it is minted, its comment should say "game choice inside S1688's net range, built from S1686/S1687/S1688/S12.5/S12.7", using the minted ids, not cite one row.

### Bounds and cross-checks

- **Floor (sustainable with adaptation):** habitual low drinkers take 0.74 L of fluid plus 0.55 L from food, about 1.3 L in total (S12.8). They pass 1.0 L of urine at 767 mOsm/kg and keep a normal plasma osmolality, but their vasopressin, cortisol and creatinine are higher (S1711).
- **Floor (renal):** urine at maximal concentration needs at least about 500 mL/d (S1686), or about 600 mL/d for 650 mOsm at 1,089 mOsm/kg in young men (S1687). Below this, solute is retained, so it is the edge of dehydration, not a resting state.
- **Average, not minimum:** isotope turnover in men rises to about 4.3 L/d near age 30 (S12.1, Fig. 2 legend).
  - Yamada's equation (S12.2) for a 30-year-old 65 kg man gives 2.8 L/d at PAL 1.4 and 10 °C, and 3.2 L/d at 20 °C (50 % RH, high-HDI country). About 85 % of turnover is drink and food (S12.5), so the intake is about 2.4–2.7 L/d. The equation reproduces the paper's worked examples: 3.2 L/d for a 70 kg man and 2.7 L/d for a 60 kg woman. These are population means that include ordinary sweating and generous drinking.
  - Raman's 458 temperate adults, aged 40–79: preformed water 3.0 L/d in men (range 1.4–7.7) and urine 2.2 L/d (S1709).
- **Per unit of energy:** water loss is 0.20–0.35 L/MJ (S1710). Turnover is 0.33 ± 0.09 L/MJ (S12.4). A 65 kg, 175 cm, 30-year-old man has a Mifflin REE of about 1600 kcal (S0002); at PAL 1.4 his TEE is about 9.4 MJ, so loss is about 1.9–3.3 L/d. The recommendation sits at the bottom of this band, as a minimum should.
- **Authorities, all with margins:**
  - EFSA AI is 2.5 L/d for men and 2.0 L/d for women at PAL 1.6 (S0089, once settled).
  - IOM water-balance studies give about 2.5 L/d for resting men (S1707).
  - The IOM/NASEM AI is 3.7 L/d for men and 2.7 L/d for women (S0088). This is today's `K.fluids.AI`.
  - NHANES: those who meet the hydration criteria take a median 42 mL/kg/d of total water, about 2.7 L at 65 kg (S12.10).
  - The emergency "survival (drinking and food)" planning figure is 2.5–3 L/d (S12.12).

  None of these is a minimum. The recommendation is 54 % of the current 3700 g.

## 2. Measured water turnover

Yamada 2022 (S12.1–S12.6) measured deuterium turnover in 5604 people.
- The by-sex figures in S12.1 are quoted from the Fig. 2 legend of the author manuscript.
- The 4.3 L/d is the men's figure near the age-30 peak, not an adult mean.

Turnover is not intake. It also counts metabolic water (about 10 %) and water taken up from air through breath and skin (about 2–3 % each), which leaves about 85 % as drink plus food (S12.5).

The fat-free-mass form of the equation (S12.3) has no significant sex term: the sex difference is carried by fat-free mass. This matters for the mod's sex-indexed `AI` (see § 9).

Raman 2004 (S1709) and Westerterp 2005 (S1710) were already in the register and are cited, not duplicated.

## 3. Losses by route and the urine floor

- IOM Table 4-2 (S1688) is the authority's route table. Its net minimum loss is 1,050–3,100 mL/d when there is minimal sweating.
- The obligatory urine volume follows from solute load and concentrating limit (S1686, S1687).
- The habitual low-drinker cohort (S12.8, with S1711) is the best evidence that about 1 L of urine a day is sustained in daily life without a rise in plasma osmolality. Its food-water medians are from one visit (V5), and the groups did not differ significantly at any visit.
- The only whole-body insensible-loss measurement found (S12.11) is tropical: 1,230–1,423 mL/d for skin and breath together at rest in Kandy. By inference, it is an upper reading for the game's temperate default.

## 4. Metabolic water

- The daily total is in the register: +250 to +350 mL/d (S1688), or about 10 % of turnover (S12.5).
- The yields per gram of fat, carbohydrate and protein are not in the register (open S12.13).

`NR_Kernel_Fluids.lua` omits metabolic water, so the basal term must be the **net** loss (gross minus metabolic water), as in § 1. If the model later adds metabolic water from oxidation, basal goes back up to the gross 2200 g.

## 5. Water from food

- IOM, US adults 19–30 y: 19 % of total water, 0.7 L/d for men (S1708).
- NHANES 2011-16, 24 h recalls: 618 of 2718 mL/d, which the paper states as 23 %, children and adults pooled (S12.9). Its Table 1 gives 664 mL/d for males and 574 mL/d for females.
- French cohort, diaries: 0.55–0.68 L (S12.8).
- Self-report surveys worldwide: 20–50 %, with a warning that surveys under-report food water (S12.6).

**For the mod,** food water already arrives through the absorbed vector, from each item's own moisture. The 0.6–0.7 L/d is a check on a realistic diet, not a constant to add. A survivor eating dry or canned food gets less, so drinks a larger share.

## 6. Reference intakes, and the settle of S0089

- EFSA's 2010 AI is 2.5 L/d for men and 2.0 L/d for women at moderate temperature and PAL 1.6. It is based on observed intakes plus a desirable urine osmolarity of 500 mOsm/L, which comes from a secondary reading in Perrier 2013 (S12.7).
- The EFSA AI is not minted as a new row. The open row **S0089** ("adequate intake of total water (EFSA 2010)") asks for exactly this record, so it is settled in place (controller ruling, following the review's recommendation).
- The controller runs `python tools/science_delta.py settle S0089` with these cells. Its status becomes `settled`, and its parameter and source stay as they are.

| cell | text |
|---|---|
| `--topic` | `water` |
| `--grade` | `AUTH` |
| `--value` | `abstract: "Available data for adults permit the definition of AIs as 2.0 L/day (P 95 3.1 L) for females and 2.5 L/day (P95 4.0 L) for males. The same AIs as for adults are defined for the elderly"; "The reference values for total water intake include water from drinking water, beverages of all kind, and from food moisture and only apply to conditions of moderate environmental temperature and moderate physical activity levels (PAL 1.6)"` |
| `--range` | `an AI, not a requirement: "derived from a combination of observed intakes in population groups with desirable osmolarity values of urine and desirable water volumes per energy unit consumed"; abstract read through the Semantic Scholar and OpenAlex mirrors (the EFSA and Wiley pages return 403)` |
| `--population` | `adults (adolescents from 14 y counted as adults; the same AI for the elderly), EU reference populations, at moderate temperature and PAL 1.6` |
| `--citation` | `EFSA Panel on Dietetic Products, Nutrition and Allergies (NDA) 2010, Scientific Opinion on Dietary Reference Values for water, EFSA Journal 8(3):1459; doi:10.2903/j.efsa.2010.1459` |

- Stookey's NHANES analysis (S12.10) gives intake per kg among those meeting the hydration criteria.

## 7. Survival and military references

- WHO's emergency technical note, adapted from Sphere, gives "Survival (drinking and food) 2.5 to 3 lpd", depending on climate and physiology (S12.12). It is a supply-planning figure with a margin.
- No military planning value was found (open S12.14). The US Army SWET planning-app paper's abstract holds none, and the TB MED 507 equations it implements were not read.

## 8. Gaps

These stay open in the part file:
- **S12.13:** metabolic-water yields per gram of each fuel.
- **S12.14:** a military planning value for a sedentary soldier.
- **S12.15:** a temperate measurement of skin water loss when not sweating.

These were already open and are not closed here:
- **S1052:** respiratory loss by activity and climate. Mitchell, Nadel and Stolwijk 1972 (J Appl Physiol 32:474-476, pmid:5026494) is the classic source, but it has no abstract in Europe PMC and the publisher returns 403.
- **S1053:** cold diuresis.

## 9. How it maps onto the mod's fluid model

`K.fluids.losses` charges `basalG = F.AI[ctx.sex] / 1440 * dtM` every step. Sweat, cold diuresis and alcohol diuresis are charged on top. Respiratory loss beyond basal is 0 (open S1052), caffeine diuresis is 0, and metabolic water is omitted. So:

1. **Basal already holds every non-sweat route** (urine, skin, breath, faeces), net of metabolic water. Replace the 3700/2700 g with the § 1 net figure. Sweat (`sweatLh`, 0 below MET 3) stays on top unchanged, as the outline asks.
2. **Drop the sex index, and scale by lean mass on the affine form (recommended).**
   - The mod's standing rule is sex-neutral by default, and S12.3 shows the sex effect in turnover disappears once fat-free mass is known.
   - A lean-mass scale fits the model, which already reads `body.lm` for TBW. The proportional form `basalG/day = BASAL_PER_LM × lm`, with BASAL_PER_LM ≈ 2000 / 55 ≈ 36 g per kg of lean mass a day, is a game choice: S12.3 is affine (37.34 mL of turnover per kg FFM beside fixed terms), and at equal PAL, age and climate its eq. 2 gives a 40 kg-FFM person 0.81 of a 55 kg-FFM person. An affine form, `basalG/day = 2000 + 32 × (lm − 55)` (32 ≈ 0.85 × 37.34, the intake share of S12.5 applied to S12.3's slope), follows S12.3 more closely and gives the 40 kg-lean woman about 1520 g (0.76). The reference man's 55 kg of lean mass is the report's assumption, not a cited value.
   - **Recommended:** the affine form, `basalG/day = 2000 + 32 × (lm − LM_REF)`.
     - **The anchor LM_REF is a game choice.** The 2000 g comes from the route table (S1688), which names no body size, so no source fixes the lean mass that earns exactly 2000 g.
     - **Anchor on 52.02 kg, not 55.** 52.02 kg is the lean mass of the mod's no-trait body: the untrained average, `K.strength.averageLean()`, from which the starting body is built (`NR_Kernel_Body.lua`).
     - With that anchor, the default character gets the recommended 2000 g exactly, and the constant is one the mod already holds.
     - The 55 kg was only this report's guess for a 65 kg man, which the brief named and the mod does not model.
     - At 52.02, a 40 kg-lean character gets 2000 + 32 × (40 − 52.02) ≈ 1615 g, 0.81 of the default, matching eq. 2's 0.81 and EFSA's 0.80. At 55 it gets about 1520 g.
     - The default character's basal differs by 32 × 2.98 ≈ 95 g between the two anchors.
   - Either scale is a game choice: S12.3 supports dropping the sex term once lean mass is known, not the proportional constant; the REE scale rests on S12.4's water-per-energy ratio.
3. **Trait and option multipliers** (outline item 5) multiply basalG. They should not multiply sweat, so that a High Thirst trait does not double exercise losses.
4. **The existing clearance and thirst machinery is unchanged.** CLEAR_GH removes water above the set point. A lower basal means a player who drinks to vanilla habits carries a surplus that the kidneys clear (S1685). This is the real behaviour.
5. **Register housekeeping:**
   - The comment on `K.fluids.AI` cites "S0088 as basal turnover: a game choice above S1688's minimum losses". The new value would sit inside S1688's net range of 1,050–3,100 mL/d.
   - S1093 (the obligatory loss at rest) is already superseded by S1688.
   - The outline says "the register holds only the adequate intake (S1688)". That is a mislabel: S1688 is the IOM minimum-loss table, and the AI row is S0088 (S0515, an earlier copy of the same AI, is superseded by S0088).
   - The register already held S1686, S1687, S1688, S1707, S1708, S1709 and S1710 on this question. This harvest adds the turnover equations, the EFSA AI (through the S0089 settle), the food share and the low-drinker floor.
