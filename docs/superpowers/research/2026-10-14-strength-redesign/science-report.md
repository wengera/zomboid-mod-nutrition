# Strength redesign: the lean-mass science (harvest 2026-10-14)

Harvested for the redesign of the mod's Strength level as a linear function of fat-free mass index (FFMI). The design fixes height, is gender-neutral, puts an untrained adult near level 5 and puts the natural ceiling at level 10, reached after about five years of good training and diet. Lean gain gets harder each training year, and lost lean comes back fast.

Every value below cites a row. `S1.n` ids are provisional rows in `lean-science-part.tsv` (36 rows: 32 settled, 1 unverified, 3 open, `science_check.py --part` 0 findings). Four-digit ids are rows already in `docs/reference/science.tsv`, reused rather than duplicated. Each citation was resolved against its PubMed record, with the abstract read through NCBI efetch. Hull 2011's table values and Benito 2020's subgroup values were read from the PMC full text. The two coach models were read from the author's page. Wherever the studies do not pin a proposal, it is labelled **game choice**.

Model id: claude-opus-5-5.

## 1. FFMI anchors

FFMI = fat-free mass (kg) / height (m)².

**Untrained adults, by sex**

| source | men | women | method, population |
|---|---|---|---|
| Schutz 2002 (S1.2) | median 18.9 | median 15.4 | BIA, 18–34 y, 5635 Swiss adults |
| Hull 2011 (S1.3) | Caucasian mean 20.5 ± 2.1 | 16.6 ± 1.7 | DXA, mixed ages (≈40 y), 1339 New York adults |
| Magee 2024 (S1.5), collegiate athletes | 21.5 ± 1.9 | 17.9 ± 1.8 | air-displacement plethysmography, 1961 NCAA athletes |

General-population FFMI is therefore about 19–20.5 in men and 15.5–16.5 in women. Athletes sit about one point higher. In men FFMI starts to fall in the mid-20s and in women in the mid-40s (S1.3).

**The natural ceiling**

- **Men: 25.0** (Kouri 1995, S1.1). Normalised to a 1.80 m man; 20 pre-steroid Mr America winners averaged 25.4.
- **The limit is soft.**
  - 26.4 % of collegiate football players exceed 25, and the 97.5th percentile is 28.1 (S1.4, steroid status not tested).
  - Male throwers average 25.7 (S1.5).
  - Tested natural physique professionals reached 23.8 on competition day, which is below 25 (S1.8).
- **Women: no published natural limit.** This is open row S1.34. Three readings bound it indirectly:
  - Female collegiate athletes have a mean of 16.9 and a single maximum of 25.5 (S1.6).
  - The largest female skeletal-muscle index is about 77 % of the largest male (S1.7).
  - Scaling 25 by the untrained female/male ratio (15.4/18.9 = 0.81, S1.2) gives about 20.4.

**Proposed gender-neutral pair (game choice)**

- **Level 5 = FFMI 18.0.** This is the mean of the male and female untrained values: (18.9 + 15.4)/2 = 17.2 by BIA medians and (20.5 + 16.6)/2 = 18.6 by DXA means.
- **Level 10 = FFMI 23.0.** This is the mean of the male limit of 25 and an estimated female limit of about 20.5–21.
- The mapping is **level = 5 + (FFMI − 18.0)**, so one level is one FFMI point. Level 0 is FFMI 13, about the leanest female athlete measured (13.3, S1.6), so the low end reads as wasting.
- Kilograms per level is height². At a fixed **1.70 m** (game choice, the midpoint of Hull's Caucasian heights 177.3 and 162.7 cm, S1.3), one level is **2.89 kg** of fat-free mass, and levels 5→10 are **14.5 kg**.
  - The register's stature row S1117 is still open. A population-reference height would settle it.
- **Cross-check against the coach models:**
  - McDonald's career total is 40–50 lb (18–23 kg) for men and about half for women (S1.15), so the neutral midpoint is about 13.6–17 kg. 14.5 kg falls inside it.
  - A man going 18.9 → 25 at 1.80 m gains 19.8 kg, which also falls inside McDonald's male range.
- **Caveat:** one FFMI point is about the size of the method spread between BIA, DXA and skinfolds. A level is a coarse unit.

## 2. Lean gain per training year

**What the studies measure**

- **Short trials (≈10 wk):**
  - Pooled resistance training adds 1.53 kg of muscle mass (95 % CI 1.30–1.76) over a mean 10.4 wk (S1.9).
  - Untrained subjects gain more fat-free mass than trained ones: FFM 1.54 vs 0.98 kg, LMM 1.70 vs 1.09 kg. The difference is not significant.
  - By experience category there is **no clean gradient**: ≤2 y 0.69 kg, ≤3 y 0.9 kg, ≥4 y 2.96 kg, p = 0.33 (S1.10). Treat this as noise in sparse categories, not as evidence against slowing.
- **Trained vs untrained under one programme:**
  - Over 21 wk, untrained men gained CSA +5.6 % and force +20.9 %, while strength athletes gained −1.8 % and +3.9 % (S1.11).
  - Long-trained men carry 56 % more muscle volume than untrained (S0648).
  - Elite weightlifters gained no significant fibre area over 2 years (+5.9 %, NS; S1.14).
- **Multi-year data (already-trained starters only):**
  - College football players gained lean mass +2.8 ± 2.8 kg in one year and +4.3 ± 3.0 kg over four years (S1.12).
  - In a 4-year programme, year 1 brought most of the significant improvements and years 2–4 were inconsistent (S1.13).
  - No study follows untrained starters through years 2–5. This is open row S1.35.
- **Untrained rate and spread:**
  - The untrained gain rate is about 1.7 %/wk in quadriceps CSA (S0590). That is local, not whole-body.
  - Ogasawara's continuous group slowed after the first 6 wk (S1.17).
  - Individual response ranges from −2 % to +59 % CSA (S0589). Men gained 2.5 % more CSA and women more relative strength, so the relative curve fits both sexes.

**Coach models (clearly not data)**

- **McDonald, men** (S1.15, settled TXT):
  - Year 1: 20–25 lb
  - Year 2: 10–12 lb
  - Year 3: 5–6 lb
  - Year 4: 2–3 lb
  - Women: about half
- **Aragon/Helms**, as McDonald reports it (S1.16, unverified because the primary was not read): beginner 1–1.5 %, intermediate 0.5–1 % and advanced 0.25–0.5 % of body weight per month. These are total-weight rates, and women use about half.
- **Iraki/Helms 2019** (S1.32): a target gain of 0.25–0.5 % of body weight per week for novices and intermediates, and less for advanced lifters.

**Shape:** each year's gain is about half of the year before. McDonald's model halves exactly, and Stodden's and Trexler's data are consistent with a large first year followed by a sharp fall.

**Proposed curve (the halving is drawn from the coach models; the constant is a game choice)**

The rate is proportional to the remaining headroom:

`dL/dt = k · (10 − L) · gates`, with `k = ln 2 per training-year` (0.0133 per training-week).

That gives `L(t) = 10 − 5·2^(−t)` from an untrained start:

| training year | levels gained | at the end | kg FFM at 1.70 m | McDonald scaled ×0.75 (neutral) |
|---|---|---|---|---|
| 1 | +2.50 | 7.50 | 7.2 | 6.8–8.5 |
| 2 | +1.25 | 8.75 | 3.6 | 3.4–4.1 |
| 3 | +0.63 | 9.38 | 1.8 | 1.7–2.0 |
| 4 | +0.31 | 9.69 | 0.9 | 0.7–1.0 |
| 5 | +0.16 | 9.84 | 0.45 | — |

**Checks against the data**

- The model's initial rate at level 5 is 0.19 kg/wk, about 1.8 kg over the first 10 wk. Benito's untrained FFM is +1.54 kg (CI 1.12–1.96) in about 10 wk (S1.9).
- Year 2 gives 3.6 kg, against Trexler's one-year +2.8 kg in already-trained players (S1.12).
- Years 4–5 come out at about 1 % or less, against the near-zero 21-wk response of strength athletes (S1.11) and of elite lifters (S1.14).
- Because the rate depends on the level and not on elapsed time, "training year" is implicit. Interrupted or poor training simply leaves the character lower on the curve, as McDonald's "proper years" caveat says (S1.15).

## 3. Muscle memory, regain and detraining

**Regain after detraining**

- **Short breaks cost almost nothing:**
  - 3 wk off lost no significant CSA or 1RM (S1.18).
  - 3-wk-off/6-wk-on cycles matched 24 wk of continuous training, and the retraining blocks outgained the continuous group's slowed blocks (S1.17).
  - 2 wk off kept strength and lean mass in trained men (S1.26).
  - Power athletes after 14 d kept strength, but type II fibre area fell 6.4 % (S1.25).
- **Strength comes back fast:**
  - Older men restored their 1RM in under 8 wk of retraining after a 12-wk break (S0618).
  - Women regrew fast-fibre CSA in 6 wk of retraining after 30–32 wk off (S0080).
- **Previously trained human muscle does not clearly regrow faster than naive muscle:**
  - Psilander 2019: after 20 wk detraining, size was back to baseline and the trained and untrained legs responded alike (S0078).
  - Cumming 2024: myonuclei were kept through 16 wk detraining, but the change on retraining was not different between arms (S1.19).
  - In rodents the effect is clear: +19 % CSA in 2 wk vs little in naive animals (S1.22, S0074–S0076). This is open row S1.36.
- **The mechanism:**
  - Myonuclei are kept through detraining (S1.19, S0074) and through 6 wk of immobilisation (S1.20).
  - An epigenetic trace is also kept (S0620).
  - Whether the myonuclear mechanism holds in humans is still called ambiguous (S0622).

**How long the memory lasts**

- In humans, myonuclei are retained for at least 16–20 wk (S1.19, S0078).
- In mice they are retained for a considerable part of the lifespan (S0074).
- The review claim is "stable for at least 15 years and might be permanent" (S1.21). That claim rests on ¹⁴C nuclear dating, not on a retraining study.

**How fast muscle is lost when training stops**

- Gains that took a few months to build are lost on about the same time scale:
  - Detraining followed the training time course over 40 d (S1.24).
  - Isometric-trained CSA was back to baseline in 1 month (S1.23).
  - Psilander's CSA was back to baseline by 20 wk (S0078).
  - Pooled, lean and muscle-mass gains are no longer significant at any follow-up (S1.27).
- Strength is lost more slowly than size after training stops:
  - In S1.23 strength did not change over 3 months.
  - Pooled strength SMD after training cessation is −0.46 to −0.62 (S0610).
- One study disagrees: in women fibre CSA stayed relatively stable through 30–32 wk (S0080).
- Disuse is far faster than detraining: immobilisation costs about 0.7 %/d of CSA early (S0069), and bed-rest loss is logarithmic (S0612).
- Maintenance is cheap: 1 session/wk at the same relative load held strength and size for up to 32 wk in younger people (S0616).

**Proposed regain and detraining model (game choice throughout)**

- **Peak memory.** Store a peak level P, the highest L reached.
  - P is permanent, or decays with a half-life of years.
  - Basis: S1.21 and S1.19. Human evidence only covers 16–20 wk, so the length is a game choice.
- **Regain bonus.** While training with L < P, add `k_r · (P − L)` to the headroom rate.
  - `k_r = ln 2 / 3 wk`: half of the lost level comes back every 3 training weeks, and about 90 % within 10 wk.
  - Basis: the 1RM was restored in under 8 wk (S0618), 6 wk of retraining was enough (S0080), and the 3-wk breaks were fully recovered (S1.17).
  - **Weak spot:** this is faster than the human hypertrophy data support (S0078, S1.19 show no rate advantage). It rests on strength regain and on rodents.
  - The conservative alternative is no bonus term. The headroom term alone already makes regain faster than frontier progress: a lifter detrained from 9.8 to 8.0 regrows at k·2.0 against k·0.2 at the frontier, which is 10× faster. That still takes months, not weeks.
- **Detraining.**
  - Grace period: none while weekly training stays at or above about 1 hard session (S0616).
  - Otherwise there is a grace period of **2 wk** before any loss (S1.18, S1.26, S1.25).
  - After the grace period, L decays toward the character's untrained baseline with a **6-wk half-life**, which leaves about 12 % of gained levels after 20 wk. Basis: S1.23, S1.24, S0078 and S1.27.
  - Immobilisation and starvation are faster pathways and belong to the injury and energy models (S0069, S0612, S0072).

## 4. Diet gates

**Protein**

- FFM gains plateau at **1.62 g/kg/day** (S0591; break point CI 1.03–2.20).
- A significant lean gain appears only at ≥1.6 g/kg/day in adults under 65 (S0592; strength S0593).
- The added effect of supplementation is modest: +0.30 kg FFM over trials whose pooled gain is about 1.5 kg (S0591, S1.9).
- The RDA is 0.8 g/kg (S0509).

**Proposed protein gate (game choice):** `f_p` rises linearly from **0.5 at 0.8 g/kg** to **1.0 at 1.6 g/kg**, is flat above, and falls toward 0 below 0.8 g/kg.

**Energy deficit vs surplus**

- **Deficit:**
  - A deficit impairs lean gain (ES −0.57) but not strength gain (S1.28).
  - About **−500 kcal/day prevents lean gain** (Murphy & Koehler 2022, S1.28). This is not Murphy NE 2018, S0602, which is the military-performance row.
  - Exception: untrained young men at 2.4 g/kg protein with very hard training still gained 1.2 kg in 4 wk in a 40 % deficit, against 0.1 kg at 1.2 g/kg (S0064; protein guidance S0063).
- **Surplus:**
  - Large surpluses add fat, not muscle. In trained lifters a 15 % surplus did not raise muscle thickness more than 5 %, and body-mass gain mostly predicted skinfold gain (S1.29).
  - In elite athletes a planned surplus raised fat mass by +15 % vs +3 % with no difference in lean gain (S1.30).
  - The recommended surplus is about 10–20 % with 0.25–0.5 % body weight per week for novices, and less for advanced lifters (S1.32). The optimum is unvalidated (S1.33).
  - In untrained men a surplus does raise FFM: a 2010 kcal/d supplement added 2.9–3.4 kg in 8 wk (S1.31). Overfeeding adds lean mass even without training (S0605, S0606).

**Proposed energy gate (game choice):**

- `f_e` = **0 at ≤ −500 kcal/d**, rising linearly to **0.8 at energy balance**.
- It reaches **1.0 at about a +10 % surplus**, and is flat above that.
- Energy above what the lean gain uses goes to fat through the mod's existing energy model (S0605, S1.29, S1.30).
- Optional term: at ≥2.4 g/kg protein the zero point moves deeper, to about −40 % of energy, but only for the first training year (S0064).

**Training gate.** No gain happens without a stimulus. The mod's exercise model supplies it:

- Hypertrophy follows weekly sets with diminishing returns (S0576, S0577).
- Load drives strength, not size (S0575).

The full gain rate is `k · (10 − L) · f_p · f_e · f_train`, plus the regain term while L < P.

## Existing rows reused

S0063, S0064, S0069, S0072, S0074, S0075, S0076, S0078, S0080, S0509, S0575, S0576, S0577, S0589, S0590, S0591, S0592, S0593, S0605, S0606, S0610, S0612, S0616, S0618, S0620, S0622, S0648.

Open rows that bear on this redesign:

- S0077 (Eftestøl 2020). Its record is a comment letter with no abstract finding, so it stays open.
- S0125 (Wernbom's rate table).
- S1117 (reference stature, needed for the kg per level).

## Gaps

- **S1.34:** there is no female natural FFMI ceiling.
- **S1.35:** no longitudinal data follow untrained starters through years 2–5.
- **S1.36:** a human retraining-rate advantage is unproven.

Further limits:

- The study populations are young, mostly male, and trained under supervision.
- Age-related slowing (S1.15, S1.3) is not modelled.
- A level is about one FFMI point, which is the size of the measurement error between methods.
