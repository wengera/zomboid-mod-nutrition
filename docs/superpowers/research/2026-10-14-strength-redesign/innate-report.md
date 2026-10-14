# Strength redesign: innate force per unit muscle and the strength traits (harvest 2026-10-14)

This harvest asks whether the Strong creation trait, and its siblings Stout, Feeble and Weak, can carry part of their start in an innate size-independent factor `N0`, instead of in lean mass alone. The model is `S = (M/M5)^0.8 · N` with `N = N0 · T`, where T is the training factor of the neural report (1 untrained, up to about 1.10; `neural-report.md` § 6, not repeated here).

**Citations**

- `S7.n` ids are provisional rows in `innate-part.tsv`: 31 rows, 28 settled and 3 open.
- Four-digit ids are rows already in `docs/reference/science.tsv`, cited rather than re-filed: S0082 (= S0644, Maughan 1983), S0589, S1978, S2101, S2104, S2121, S2127.
- Every settled row's record was resolved through PubMed E-utilities (efetch XML: authors, journal, volume, pages, DOI). Numbers come from the abstract unless the row names the full text. Full texts were read from Europe PMC for Maden-Wilkinson 2021 (PMC7966212) and Trezise & Blazevich 2019 (PMC6691166). The other full texts were closed or scanned.

**Labels**: **derived** marks my arithmetic (never in a TSV cell); **game choice** marks a constant the studies do not pin.

Model: claude-opus-5-5.

## 1. Size-independent spread

**Force per unit muscle size between untrained adults (single muscle group).**

| source | measure | mean ± SD | CV (derived unless read) | n |
|---|---|---|---|---|
| Maughan & Nimmo 1984 (S7.1) | knee-extensor MVC / CT ACSA | 8.92 ± 1.01 N/cm², range 7.09–10.85 | 11.3 %; range −21 % to +22 % of the mean | 15 men |
| Maughan 1983 (S0082) | same | men 9.49 ± 1.34, women 8.92 ± 1.11 | 14.1 % men, 12.4 % women | 25 + 25 |
| Maden-Wilkinson 2020 (S2121) | specific tension, corrected for coactivation and moment arm, effective PCSA | 33.3 ± 4.5 N/cm² untrained; 36.1 ± 5.3 trained | 13.5 % untrained; 14.7 % trained | 52 + 16 men |
| Erskine 2009 (S7.2) | specific tension, also corrected for voluntary activation | 30 ± 5 N/cm² | **read:** 16 % (MVC 18 %) | 27 men |
| O'Brien 2010 (S7.3) | as Erskine | men 55 ± 11, women 57.3 ± 13 | 20 %, 23 % | 20 adults |

**Strength against muscle size within groups.**

- MVT varies more than size: CVb 17 % for MVT against 14.4 % for quadriceps volume and 11.2 % for effective PCSA in 53 untrained men (S7.4).
- Size explains about half to most of the strength variance:
  - knee-extensor MVC vs CSA: r = 0.70 (S7.1);
  - quadriceps volume vs isometric moment: R² = 0.60, with the sexes pooled (S7.6);
  - elbow-flexor volume vs torque: r = 0.95 by MRI in 26 men, and 0.78 by ultrasound in 259 men (S7.5);
  - r = 0.564–0.926 across age-sex groups (S7.7);
  - fat-free mass: partial R² 33–45 % for knee and trunk strength in 748 brothers (S7.16);
  - size, architecture and activation together: R² = 72 % (S7.8).
- **derived residual SD**: with strength CV 17 % (S7.4), r = 0.70 leaves 12.1 %, R² 0.60 leaves 10.8 %, and r = 0.95 leaves 5.3 %.
- Erskine's conclusion (S7.2): after correcting for activation, coactivation, moment arm and PCSA, most of the between-person spread in MVC "remains largely unexplained". Specific tension varies almost as much as MVC (16 % vs 18 %).
- Sex: force per unit size does not differ between men and women (S0082, S7.3).

**Reading.**

- The measured spread of force per unit size, in one muscle group, is a CV of **11–16 %**. The residual SD from size regressions is **5–12 %**.
- Both include imaging error and moment-arm spread. Moment arm has a CVb of 6.7 % at free height (S7.4). The game fixes height, which removes most of that spread.
- **Game choice:** the whole-body size-independent SD is **σ_res = 10 %** (range 8–12 %) of untrained strength.
  - It sits at the lower middle of the single-muscle figures, because a general factor that spans several muscle groups averages out part of each muscle's own deviation.
  - Strength measures share genes across muscle groups (S7.22: genetic r = 0.78 between elbow flexion and grip; S7.26), but no study measures size-independent strength in several groups of the same people (**S7.29, open**).
- **Total untrained strength spread: σ_tot = 17 %** (S7.4; S2121 untrained 245 ± 43 N·m, derived 17.6 %; S7.2 18 %).

## 2. Voluntary activation

- **Spread in untrained men:** quadriceps %VA 88.51 ± 6.71 % before training (S7.9, n = 36). **derived:** CV 7.6 %. On the same muscle, other laboratories report baseline means above 95 % (S2104). The level depends on the method and the laboratory; the spread is the usable figure.
- **Muscle dependence:** within the same 12 men, inactivation was 15.5 % in the quadriceps and 1.3–5.0 % in the elbow flexors, plantar flexors and dorsiflexors (S7.10). Large, high-threshold muscles carry most of the activation deficit.
- **Activation is a stable trait:** VA differed consistently between subjects, but did not differ within 4 of 5 subjects across days (S7.11).
- **How much of the strength variance VA explains:**
  - Correcting MVC for VA, coactivation and moment arm barely narrows the spread (18 % → 16 %, S7.2).
  - %VA and agonist EMG enter the best predictive model alongside CSA (R² 72 %, S7.8); the abstract does not give VA's own share.
  - **derived upper bound:** a VA SD of 7.6 %, if it were independent of size, would be at most about (7.6/17)² ≈ 20 % of the strength variance, and up to about half of the size-independent variance at σ_res = 10 %. Erskine's narrow change after correction (S7.2) puts the real share well below that bound.
- **Reading.** VA is a real, stable, neural part of N0 in untrained people, but probably the smaller part. Most of the size-independent spread is in specific tension at full activation (S7.2). That is intrinsic, not neural: fibre packing, lateral force transmission and architecture (S2121 and the neural report § 3). Single fibres of one type vary threefold in force per area (S7.15).

## 3. Heritability

| study | phenotype | heritability | adjusted for size? |
|---|---|---|---|
| Zempo 2017 (S7.23), meta-analysis of 58 measures | strength phenotypes | 0.52 (0.48–0.56); isometric 0.49, grip 0.56 | no |
| Silventoinen 2008 (S7.22), 1.14 M men | elbow, grip, knee | 0.50–0.60; genetic r with height only 0.13 (elbow flexion) | no; genetic correlations with body size reported |
| Arden & Spector 1997 (S7.24), women | leg extensor, grip, lean mass | 0.46, 0.30; lean 0.52 | no |
| Huygens 2004 (S7.16), 748 brothers | isometric knee, trunk, elbow | upper limit 0.82–0.96 (genes + shared environment) | FFM explains a partial R² of 33–45 % |
| Thomis 1997 (S7.17), male twins | elbow isometric at 5 angles | 0.66–0.78; general genes for area and strength **plus a specific strength factor** | modelled jointly with CSA |
| Thomis 1998 (S7.18) | eccentric / concentric arm strength; arm CSA | 0.62–0.82 / 0.29–0.65; CSA > 0.85 | — |
| Thomis 2000 (S7.19) | strength-CSA covariation | 84–97 % genetic | — |
| **Reed 1991 (S7.21)**, older male twins | **grip adjusted for weight, height, fatness, muscle mass, frame** | **0.65** (the largest estimate, larger than unadjusted) | **yes** |
| **Tiainen 2008 (S7.25)**, older female twins | a genetic factor common to CSA, strength, power and gait | explains **51 % of strength but 7 % of CSA** | yes, structurally |
| Tiainen 2004 (S7.26) | genes shared by grip and knee strength | 14 % / 31 % of variance | no |

**Reading.**

- Strength is about half heritable (S7.23, S7.22).
- The size-independent part is at least as heritable:
  - Grip adjusted for size and muscle mass gives the highest estimate, 0.65 (S7.21).
  - The main genetic factor behind strength in older women hardly touches muscle CSA (S7.25).
  - Thomis's twins need a strength-specific genetic factor beyond the area genes (S7.17).
- **Inference:** about **0.4–0.65** of the size-independent spread is heritable. It is therefore a legitimate innate, creation-time property, not noise.
- No twin study measures imaging-based specific tension directly (**S7.30, open**). The adjustment in Reed 1991 is anthropometric.

## 4. Fibre type

- **Between-person spread:** about 25 % of people have under 35 % or over 65 % type I fibres. Of the variance, about 45 % is inherited, 40 % environmental and 15 % error (S7.14). In 15 untrained men the share of type I was 46.1 ± 10.5 % (S7.1).
- **Single fibres:** Po/CSA is lower in type I than in type II fibres (S7.12; the magnitude is in a scanned full text that was not read).
- **Whole muscle, untrained:** strength/CSA was not related to fibre-type proportions or area fractions (S7.1). The authors conclude that fibre composition cannot explain the spread in force per area.
- **Velocity, not maximum force:** %MHC II correlated with concentric strength per volume at medium-to-high speed (rs 0.61–0.93) but not consistently with eccentric strength (S7.13, n = 7).
- **Reading.** Fibre type is heritable and varies widely, but it does not carry maximal force per unit muscle between people. It belongs to power and speed, which this model does not represent. N0 should not be framed as fibre type.

## 5. Training and persistence

**Persistence.**

- **Group spread:** after 4 yr of training, specific tension is 36.1 ± 5.3 against 33.3 ± 4.5 N/cm² untrained (S2121). **derived:** CV 14.7 % against 13.5 %. Trained men do not converge.
- **Ratio by training:** torque per muscle volume was identical in athletes and controls (S7.5). The group mean of force per unit size is barely moved by training in the elbow flexors, and the spread stays.
- **Ranking over 10 weeks:** the ranking holds, with pre-post torque r = 0.93 isometric (S7.28). The stronger at baseline gain as much absolute strength as the weaker. The range of the change was 31 % of the baseline range.
- **Genetics:** pre- and post-training strength share their genes ("high pleiotropic gene action"), and training-specific genes add about 20 % (S7.20).
- **Later life:** grip strength tracks over 10 years (r = 0.62), held mostly by genetic and familial factors (S7.27).

**Partial convergence.**

- **Genetic factor score:** a high score predicts smaller gains (r −0.24 to −0.51, S7.19).
- **Pre-training strength:** it correlates −0.43 with the gain (S2101).
- **VA:** the spread narrows with training, from 88.51 ± 6.71 to 92.00 ± 4.99 % (S7.9). **derived:** the SD falls by about a quarter as VA nears its ceiling.
- **Responses:** they vary widely in any case (S0589, S1978, S2127).

**Reading.**

- **The intrinsic part of N0 persists:** specific tension at full activation, which is the larger part (§ 2).
- **The VA part partly converges,** because training raises everyone toward full activation.
- **No longitudinal study follows an individual's specific-tension advantage over years** (**S7.31, open**).
- **Game choice:** `N = N0 · T`, multiplicative, with full persistence by default.
- **Optional convergence (game choice):** `N = N0^(1 − c·τ) · T`, where τ ∈ [0, 1] is the training saturation the neural factor already tracks.
  - c ≈ 0.25 would remove the VA share of the advantage at full training.
  - The data bound c between 0 (S2121, S7.5) and about 0.5 (the upper-bound VA share, § 2).

## 6. Proposed N0

**Rule (derived from the measured spreads; constants are game choices).**

Take a person known only to be at total strength S. With size and size-independent factors independent and log-normal, the expected size-independent part is the regression share of the log gap:

`ln N0 = k · ln S_trait`, with `k = σ_res² / σ_tot² = 0.10² / 0.17² ≈ 0.35`. The range is 0.22–0.50 for σ_res from 8 to 12 %.

That is, **N0 = S_trait^0.35**: about a third of each trait's log strength gap is carried by force per unit muscle and two-thirds by muscle. This matches the owner's suggested "+1 to +1.5 residual SD" for Strong without picking it by hand.

**Cap (game choice):** |ln N0| ≤ 2·σ_res, so 0.82 ≤ N0 ≤ 1.22. The tails of the residual distribution are unmeasured beyond about ±2 SD (S7.1's range is −21 % to +22 % of the mean in n = 15). The cap binds only Weak.

**The trait table**

Level scale: one level is 0.1132 of S. The lean figures use M5 = 25 kg and b = 0.8.

| trait | vanilla offset | S_trait | **N0** | residual z | levels carried by N0 | lean left (ΔM), vs N0 = 1 |
|---|---|---|---|---|---|---|
| Strong | +4 | 1.453 | **1.14** (1.086–1.204) | +1.3 | +1.2 of 4 | **+8.9 kg** (6.6–11.0), vs +14.9 |
| Stout | +2 | 1.226 | **1.07** (1.046–1.107) | +0.7 | +0.65 of 2 | **+4.5 kg** (3.4–5.5), vs +7.3 |
| Feeble | −2 | 0.774 | **0.915** (0.88–0.945) | −0.9 | −0.75 of 2 | **−4.7 kg** (−3.7 to −5.5), vs −6.9 |
| Weak | −5 | 0.434 | **0.82** (capped; uncapped 0.749) | −2.0 (uncapped −2.9) | −1.6 of 5 | **−13.7 kg** (uncapped −12.4), vs −16.2 |

Everything in the table is derived. N0 = S^k; levels = (N0 − 1)/0.1132; ΔM = 25·((S/N0)^1.25 − 1). The ranges are k = 0.22 and k = 0.50.

**Notes for the design.**

- **What N0 stands for.** It is force per unit muscle at creation, meaning specific tension plus activation. Most of it is intrinsic (§ 2), so it is not purely "neural". The label "innate force per unit muscle" is the honest one. Fibre type should not be named as its cause (§ 4).
- **Sex.** The same N0 applies to both sexes, since force per unit size does not differ between them (S0082, S7.3).
- **Trained ceiling.** A trained Strong character reaches N = 1.14 × 1.10 ≈ 1.25 (derived). The natural-cap rule (half the offset in levels, spec § 3.2) is defined on levels. If the cap stays a level, its lean must be re-derived with N0 in place, or Strong's cap lean falls by about the same share. That is a controller decision; the data do not set it.
- **Weak** remains mostly a muscle deficit (−13.7 of −16.2 kg). Its level-0 start lies about 4.9 total SDs below the mean (derived, ln 0.434 / 0.17). That is beyond any measured healthy range, so most of it has to be thin muscle.
- **What the data do not support.** N0 above about 1.2 for Strong (k = 0.5 is already the 12 % upper σ_res); a factor that grows with training beyond T; or any size-independent factor that disappears with training (§ 5).

**Open.**

- S7.29: the whole-body (multi-muscle) size-independent SD. σ_res = 10 % rests on single-muscle data.
- S7.30: the heritability of imaging-measured specific tension.
- S7.31: whether an individual's specific-tension advantage persists over years.
