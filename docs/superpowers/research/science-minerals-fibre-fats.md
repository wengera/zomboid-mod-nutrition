# Minerals, electrolytes, fibre, essential fatty acids and macronutrient quality — evidence base

Research report for the realism nutrition mod. Scope: the twelve minerals and electrolytes,
dietary fibre, the essential fatty acids, carbohydrate quality, and alcohol and caffeine as they
touch hydration, sleep and nutrient status. Written 2026-09-27.

## How to read this

Every row carries a grade for the *kind* of evidence behind it, not a judgement of the number:

| grade | meaning |
|---|---|
| `MA` | meta-analysis or systematic review |
| `RCT` | randomised controlled trial (single trial) |
| `COH` | cohort, cross-sectional, case series, or a controlled human depletion/balance study |
| `AUTH` | authoritative report — IOM/NASEM Dietary Reference Intakes, EFSA, WHO, ACSM or a formal consensus statement |
| `TXT` | narrative review or textbook physiology |

**Verification.** Every citation in this report was verified by fetching either the Crossref API
record (`api.crossref.org/works/<DOI>`) or the Europe PMC REST record (`ebi.ac.uk/europepmc`), and
confirming that title, authors and year match what is claimed here. PubMed itself blocked automated
fetches during this work, so Europe PMC and Crossref are the verification trail. Where a number
could be found only in a secondary source, or where a well-known figure could not be pinned to a
fetched record, the row says **unverified** and must not be used as evidence.

**Unit convention.** Electrolytes are given in both mg and mmol where the game model will need
mass; 1 mmol Na = 23.0 mg, 1 mmol K = 39.1 mg, 1 mmol Cl = 35.5 mg. Sodium chloride is 39.3% sodium
by mass, so 1 g salt = 393 mg Na = 17.1 mmol Na.

**A standing caution for a game model.** Almost none of the deficiency literature measures *time to
onset on a fixed deficient intake* — the quantity a simulation actually needs. Requirements are well
characterised (AUTH), deficiency *consequences* are often well characterised (MA/RCT), and the
*kinetics between them* are usually the weakest link. Rows marked as depletion studies (`COH`) are
the closest thing to a timescale and are called out per nutrient.

## Sodium

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI | 1500 mg/d (65 mmol/d) | single value, no distribution | adults 19–50, both sexes | AUTH | NASEM 2019, *DRI for Sodium and Potassium*, doi:10.17226/25353 |
| CDRR | reduce intake if above 2300 mg/d (100 mmol/d) | first CDRR ever issued for any nutrient | adults 14+ | AUTH | NASEM 2019, doi:10.17226/25353 |
| EAR/RDA | none set | — | all adults | AUTH | NASEM 2019, doi:10.17226/25353 |
| UL | none set — "insufficient evidence of sodium toxicity risk within the apparently healthy population" | — | all adults | AUTH | NASEM 2019, doi:10.17226/25353 |
| sweat [Na⁺] | 10–90 mmol/L (230–2070 mg/L) | ninefold spread between individuals | exercising adults, whole-body and regional methods | TXT | Baker 2019, *Temperature* 6:211–259, doi:10.1080/23328940.2019.1632145, PMID 31608304 |
| sweat Na⁺ loss rate | 55.9 mmol/h (American football); 51.7 mmol/h (endurance) | means across 1303 athletes; other sports lower | trained athletes, field testing | COH | Barnes et al. 2019, *J Sports Sci* 37:2356–2366, doi:10.1080/02640414.2019.1633159, PMID 31230518 |
| BP effect of cutting salt 11.5 → 3.8 g/d | normotensive −1.14/+0.01 mmHg; hypertensive −5.71/−2.87 mmHg | 95% CI −1.65 to −0.63 (normotensive SBP); −6.67 to −4.74 (hypertensive SBP) | white adults, pooled RCTs | MA | Graudal, Hubeck-Graudal & Jurgens 2020, *Cochrane Database Syst Rev*, doi:10.1002/14651858.CD004022.pub5 |
| counter-regulation on low sodium | renin +55%, aldosterone +127%, noradrenalin +27%, adrenalin +14% | pooled across same trials | as above | MA | Graudal et al. 2020, doi:10.1002/14651858.CD004022.pub5 |
| exercise-associated hyponatraemia | serum/plasma [Na⁺] below 135 mmol/L | primary cause is drinking in excess of losses, not sodium loss per se | endurance athletes, military, hikers | AUTH | Hew-Butler et al. 2015, *Clin J Sport Med* 25:303–320, doi:10.1097/JSM.0000000000000221, PMID 26102445 |

**Interpretation for the game.** Sodium is the one mineral where the evidence supports a *fast* loop:
losses scale with sweat, and sweat sodium losses of 50–60 mmol/h (1.2–1.4 g Na/h) during heavy work
are several times the 65 mmol/d AI, so a day of hard labour in Kentucky summer heat can plausibly
run a negative sodium balance even on a normal diet. Model sodium loss as `sweat_litres ×
sweat_Na_concentration`, with the concentration a per-character constant drawn once from 10–90
mmol/L — Baker's review is explicit that the between-individual spread is large and stable, which
makes a per-character constant more faithful than a global average. Do **not** model acute sodium
deficiency as the cause of the classic "hyponatraemia collapse": the consensus statement is
unambiguous that exercise-associated hyponatraemia is driven by drinking too much water relative to
losses, so the game mechanic should be *high water intake plus high sweat sodium loss*, not sodium
loss alone. The blood-pressure side of excess is a decade-scale effect (a few mmHg) and is not worth
modelling in a survival game; there is no UL to hang an acute-excess penalty on. What *is* worth
modelling is the palatability and thirst side: salt drives thirst and is the reason a scavenger eats
canned soup and crisps. Note the counter-regulation row — the body defends sodium hard via
aldosterone, which is a good argument for making sodium depletion slow to bite and quick to correct
once salt is eaten.

## Potassium

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI | 3400 mg/d (87 mmol/d) men; 2600 mg/d (66 mmol/d) women | single values | adults 19–50 | AUTH | NASEM 2019, doi:10.17226/25353 |
| EAR/RDA | none set | — | all adults | AUTH | NASEM 2019, doi:10.17226/25353 |
| CDRR | none set — "lack of evidence to characterize the effect", not absence of effect | — | all adults | AUTH | NASEM 2019, doi:10.17226/25353 |
| UL | none set (reaffirmed: insufficient evidence) | — | healthy adults; does not apply to impaired renal excretion | AUTH | NASEM 2019, doi:10.17226/25353 |
| BP effect of increased intake | SBP −3.49 mmHg (95% CI −1.82 to −5.15) in hypertensives at 90–120 mmol/d | no significant effect in normotensives | pooled RCTs, adults | MA | Aburto et al. 2013, *BMJ* 346:f1378, doi:10.1136/bmj.f1378 |
| sweat [K⁺] | 2–8 mmol/L (78–313 mg/L) | fourfold spread; much lower than sweat Na | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |

**Interpretation for the game.** Potassium is an intracellular ion: the body pool is large (roughly
3000–4000 mmol in a lean adult, but see Gaps — I could not pin that figure to a fetched primary
source, so treat it as unverified) and sweat concentrations are 2–8 mmol/L, an order of magnitude
below sodium. That means **sweat is a poor driver for potassium in the model**: at 1.5 L/h and 5
mmol/L a hard hour costs about 7.5 mmol, under 10% of the daily AI. The real depletion routes are
diarrhoea and vomiting, both of which are game-plausible (food poisoning, bad water, illness), and
prolonged low intake on a grain-and-canned-meat diet. So charge potassium losses to *illness and
diarrhoea events*, not to running. On the intake side, potassium is the nutrient a 1993 Kentucky
scavenged diet most plausibly falls short on if the player lives on rice, pasta and canned fish —
potatoes, tomatoes and dried beans are the recoverable sources. The AI is also not a deficiency
threshold: it was set from blood-pressure and stone-risk evidence, not from a measured requirement,
so a mod should treat sustained intake well below ~1500 mg/d as the trigger for weakness effects
rather than any shortfall against 2600–3400 mg/d. Hyperkalaemia from food is essentially impossible
in a person with working kidneys, which is why no UL exists; only a supplement or salt-substitute
item would justify an excess mechanic.

## Chloride

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI | 2.3 g/d (65 mmol/d), equivalent to 3.8 g/d sodium chloride | set equimolar to the sodium AI, not from independent evidence | adults 19–50 | AUTH | IOM 2005, *DRI for Water, Potassium, Sodium, Chloride and Sulfate*, doi:10.17226/10925 |
| EAR/RDA | none set | — | all adults | AUTH | IOM 2005, doi:10.17226/10925 |
| UL | not established for chloride in the 2005 chapter (a sodium UL of 2.3 g/d was set, and later withdrawn in 2019) | some reproduced DRI tables list 3.6 g/d for chloride; my two fetches of the 2019 appendix disagreed with each other — **unverified** | adults | AUTH | IOM 2005, doi:10.17226/10925; NASEM 2019, doi:10.17226/25353 |
| sweat [Cl⁻] | 10–90 mmol/L | tracks sodium almost exactly | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |

**Interpretation for the game.** Chloride does not deserve its own stat. Its AI was derived by setting it
equimolar to sodium, dietary chloride comes overwhelmingly from sodium chloride, and its sweat
concentration tracks sodium 1:1 in the same 10–90 mmol/L band. Model it, if at all, as a fixed
multiple of the sodium pool (mass ratio 1.54 Cl per Na) so that a salt item moves both. The one place
chloride separates from sodium is vomiting, which loses hydrochloric acid and produces a
hypochloraemic alkalosis — a real clinical entity, but far below the resolution a survival game
needs. Simplify to a single "salt" axis.

## Calcium

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 1000 mg/d | — | adults 19–50, both sexes | AUTH | IOM 2011, *DRI for Calcium and Vitamin D*, doi:10.17226/13050 |
| EAR | 800 mg/d | — | adults 19–30 | AUTH | IOM 2011, doi:10.17226/13050 |
| UL | 2500 mg/d | — | adults 19–50 | AUTH | IOM 2011, doi:10.17226/13050 |
| skeletal calcium at maturity | 1200 g (women); 1400 g (men) | — | healthy adults | AUTH | IOM 2011, doi:10.17226/13050 |
| fraction of body calcium in bone and teeth | over 99% | — | adults | AUTH | IOM 2011, doi:10.17226/13050 |
| fractional absorption of dietary calcium | ~25% of intake | across a wide age range | adult men and non-pregnant women | AUTH | IOM 2011, doi:10.17226/13050 |
| obligatory renal loss | 5 mmol/d (200 mg/d) | mean urinary loss averages 22% of intake, faecal 75% | healthy adults | AUTH | IOM 2011, doi:10.17226/13050 |
| sweat [Ca²⁺] | 0.2–2.0 mmol/L (8–80 mg/L) | tenfold spread | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |
| calcium + vitamin D on fracture | total fractures −15%; hip fractures −30% | pooled RCTs; supplement doses, mostly older adults | community-dwelling and institutionalised middle-aged to older adults | MA | Weaver et al. 2016, *Osteoporos Int* 27:367–376, doi:10.1007/s00198-015-3386-5 |
| vitamin D alone on fracture | no statistically significant reduction in hip or any new fracture | Cochrane conclusion; vitamin D without calcium | post-menopausal women and older men | MA | Avenell, Mak & O'Connell 2014, *Cochrane Database Syst Rev*, doi:10.1002/14651858.CD000227.pub4 |
| calcium inhibits iron absorption | 40–300 mg Ca per meal reduces both heme and non-heme iron absorption, dose-related; little further effect above ~600 mg | single-meal radioisotope studies, 126 subjects | non-anaemic adults | COH | Hallberg et al. 1991, *Am J Clin Nutr* 53:112–119, doi:10.1093/ajcn/53.1.112 |

**Interpretation for the game.** Calcium is the clearest case in this report for **not** modelling a
short-term deficiency effect. Over 99% of body calcium is skeletal, the bone pool is 1200–1400 g
against an obligatory renal loss of about 200 mg/d, and parathyroid hormone will strip bone to hold
serum calcium constant. A survivor on a calcium-free diet loses bone mineral, not function: there is
no acute weakness, cramp or collapse to model on a days-to-months timescale, and the fracture
evidence is a multi-year, older-adult signal. If the mod wants calcium at all, make it a slow
background "bone integrity" counter that only matters over a months-long save and at most modulates
fracture risk if the game ever models one — and note the honest caveat that the 15%/30% figures come
from supplement trials in older adults, not from young survivors. What *is* worth modelling is the
interaction: 300 mg of calcium in a meal roughly halves iron absorption from that meal, so a
milk-heavy meal eaten with the day's meat is a real, mechanistically sound reason for iron intake to
underperform. Canned milk, cheese and tinned fish with bones are the 1993 Kentucky calcium sources;
a diet of rice, pasta and deer meat is calcium-poor but that shortfall is invisible within a
one-season save.

## Magnesium

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 400 mg/d (men 19–30), 420 mg/d (men 31–50); 310 mg/d (women 19–30), 320 mg/d (women 31–50) | — | adults | AUTH | IOM 1997, *DRI for Calcium, Phosphorus, Magnesium, Vitamin D and Fluoride*, doi:10.17226/5776 |
| EAR | 330 mg/d (men), 255 mg/d (women) | — | adults 19–30 | AUTH | IOM 1997, doi:10.17226/5776 |
| UL | 350 mg/d **from supplements and pharmacological sources only** — no UL on food magnesium | the adverse effect is osmotic diarrhoea, not systemic toxicity | adults | AUTH | IOM 1997, doi:10.17226/5776 |
| total body magnesium | ~25 g (1000 mmol) | — | normal adult | AUTH | IOM 1997, doi:10.17226/5776 |
| distribution | 50–60% in bone; remainder soft tissue, ~1% extracellular | — | normal adult | AUTH | IOM 1997, doi:10.17226/5776 |
| renal conservation on depletion | urinary magnesium falls below 20 mg (1 mmol)/d within 3–4 days | — | human experimental depletion | COH | IOM 1997, doi:10.17226/5776 |
| first clinical sign of deficiency | neuromuscular hyperexcitability — latent tetany (Chvostek and Trousseau signs), spontaneous carpopedal spasm | — | magnesium-deficient humans | AUTH | IOM 1997, doi:10.17226/5776 |
| magnesium supplements for idiopathic muscle cramps | "unlikely … clinically meaningful cramp prophylaxis … at any of the dosages used" | 11 trials, 735 participants, largely older adults | idiopathic cramps | MA | Garrison et al. 2020, *Cochrane Database Syst Rev*, doi:10.1002/14651858.CD009402.pub3 |
| sweat [Mg²⁺] | 0.02–0.40 mmol/L (0.5–10 mg/L) | twentyfold spread but tiny absolute loss | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |

**Interpretation for the game.** The magnesium evidence points in two directions at once and the mod
should respect both. The kidney defends magnesium fast — urine output collapses to under 1 mmol/d
within three to four days of a deficient intake — which means the *body* treats magnesium as
precious and biochemical depletion is quick to start but the 25 g pool (over half of it in bone)
makes clinical depletion slow. The first sign is neuromuscular hyperexcitability, which is exactly
the "cramps and twitching" a survival game wants. But the Cochrane review is decisive that
**supplementing magnesium does not prevent ordinary cramps**, so the mod must not sell magnesium as
a cramp cure: the defensible design is that frank, sustained magnesium deficiency causes
hyperexcitability effects, while topping magnesium up in a replete character does nothing. Sweat
magnesium loss is negligible (at 1.5 L/h and 0.2 mmol/L, about 0.3 mmol/h against a 1000 mmol pool),
so do not charge magnesium to exertion. Green vegetables, nuts, peanut butter and whole grains are
the sources; a canned-and-refined scavenged diet is genuinely magnesium-poor, which makes it a
reasonable candidate for a slow months-scale stat.

## Phosphorus

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 700 mg/d | — | adults 19–50, both sexes | AUTH | IOM 1997, doi:10.17226/5776 |
| EAR | 580 mg/d | — | adults 19–30 | AUTH | IOM 1997, doi:10.17226/5776 |
| UL | 4 g/d | — | adults 19–50 | AUTH | IOM 1997, doi:10.17226/5776 |

**Interpretation for the game.** Phosphorus should not be a mod stat. It is present in essentially
every protein- or grain-containing food, dietary deficiency in someone who is eating at all is
effectively unknown, and the one clinically important hypophosphataemia — refeeding syndrome after
prolonged starvation — is a *treatment* complication driven by the insulin surge of rapid
carbohydrate refeeding rather than by low phosphorus intake. If the mod ever models refeeding after
a long starvation arc, hypophosphataemia is the correct mechanism to reach for, but I did not verify
a primary citation for its thresholds or timescale in this pass (see Gaps). Otherwise: fold
phosphorus into "protein and grain intake" and do not surface it.

## Iron

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 8 mg/d (men); 18 mg/d (women 19–50) | the 2.25× sex difference is menstrual loss | adults 19–50 | AUTH | IOM 2001, *DRI for Vitamin A, Vitamin K, … and Zinc*, doi:10.17226/10026 |
| EAR | 6 mg/d (men); 8.1 mg/d (women) | — | adults 19–30 | AUTH | IOM 2001, doi:10.17226/10026 |
| UL | 45 mg/d | based on gastrointestinal distress, not systemic toxicity | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| assumed dietary bioavailability used to set the RDA | 18% (16.8% non-heme plus ~2.5% heme contribution) | mixed North American diet | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| total body iron | ~4 g / 50 mg/kg (75 kg man); ~40 mg/kg (menstruating women) | — | healthy adults | AUTH | IOM 2001, doi:10.17226/10026 |
| distribution | almost two-thirds in circulating haemoglobin; a readily mobilisable store of another ~25% | so store iron ≈ 1000 mg in a man, far less in a woman | healthy adults | AUTH | IOM 2001, doi:10.17226/10026 |
| basal (obligatory) loss | 0.9–1.0 mg/d (men); ~1.5 mg/d average (menstruating women), up to 3.4 mg/d | mean menstrual contribution 0.6–0.7 mg/d | healthy adults | AUTH | IOM 2001, doi:10.17226/10026 |
| depletion sequence | stage 1 stores fall (ferritin drops, haemoglobin normal) → stage 2 iron-restricted erythropoiesis → stage 3 microcytic hypochromic anaemia | ferritin below ~15 µg/L indicates absent stores | adults | TXT | Camaschella 2015, *N Engl J Med* 372:1832–1843, doi:10.1056/NEJMra1401038 |
| iron supplementation, VO₂max | +2.35 mL·kg⁻¹·min⁻¹ (95% CI 0.82, 3.88; P = 0.003; 18 studies); overall SMD 0.37 (95% CI 0.11, 0.62; 20 studies) | clearest in iron-deficient and trained women | women of reproductive age, pooled RCTs | MA | Pasricha et al. 2014, *J Nutr* 144:906–914, doi:10.3945/jn.113.189589, PMID 24717371 |
| iron supplementation, submaximal exercise | heart rate −4.05 bpm (95% CI −7.25, −0.85; 6 studies); work at −2.68% of VO₂max (95% CI −4.94, −0.41) | — | as above | MA | Pasricha et al. 2014, doi:10.3945/jn.113.189589 |
| two mechanisms of the work-capacity effect | (i) tissue oxidative capacity → endurance and efficiency, present in iron deficiency *without* anaemia; (ii) low haemoglobin → maximal work output | 29 research reports judged to show a strong causal effect | adults, lab and field studies | MA | Haas & Brownlie 2001, *J Nutr* 131:676S–688S, doi:10.1093/jn/131.2.676S, PMID 11160598 |
| acute oral toxicity | under 20 mg/kg elemental iron non-toxic; 20–60 mg/kg mild to moderate; above 60 mg/kg severe | consensus guideline thresholds | children and adults | AUTH | Manoguerra et al. 2005, *Clin Toxicol* 43:553–570, doi:10.1081/CLT-200068842 |
| calcium inhibits iron absorption | 40–300 mg Ca per meal, dose-related, both heme and non-heme | — | non-anaemic adults | COH | Hallberg et al. 1991, doi:10.1093/ajcn/53.1.112 |

**Interpretation for the game.** Iron is the single best candidate in this whole report for a
player-visible, mechanically interesting nutrient, because the arithmetic gives genuinely
game-relevant timescales. A replete man carries about 1000 mg of mobilisable store against a basal
loss of about 1 mg/d, so *dietary* depletion to empty stores takes on the order of two to three years
— too slow for most saves. Blood loss changes everything: whole blood carries roughly 0.5 mg iron per
mL, so a wound losing half a litre costs about 250 mg, a quarter of the store, and a menstruating
character starts with roughly a third of the male store and loses 50% more per day. That makes the
right design **two clocks**: a slow dietary clock that only matters in long saves, and a fast
injury/bleeding clock that can plausibly drive a character to iron-deficiency anaemia inside a
season. Model the consequence as the two mechanisms Haas and Brownlie separate: an *endurance and
efficiency* penalty that appears before anaemia (higher heart rate and higher fractional VO₂max for
the same work — Pasricha's submaximal numbers, about 4 bpm and 2.7% of VO₂max, are the size of the
real effect) and a *maximal output* penalty once haemoglobin falls. Both are modest in absolute
terms — a 2.35 mL/kg/min VO₂max shift is around 5–6% for a typical adult — so resist the temptation
to make anaemia crippling; make it a persistent tax on stamina regeneration and sprint duration
instead. Absorption deserves to be modelled because it is where food choice bites: heme iron from
deer, rabbit and liver is absorbed several-fold better than non-heme iron from rice, pasta and
beans; calcium in the same meal halves absorption; and the whole-diet assumption behind the RDA is
only 18%. For excess, the UL (45 mg/d) is a gastrointestinal-distress threshold, and real acute
danger starts around 20 mg/kg — about 1.4 g of elemental iron for a 70 kg adult, which no food can
deliver. Only an iron-tablet item justifies a poisoning mechanic, and it would be lethal above about
250 mg/kg.

## Zinc

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 11 mg/d (men); 8 mg/d (women) | — | adults 19–50 | AUTH | IOM 2001, doi:10.17226/10026 |
| EAR | 9.4 mg/d (men); 6.8 mg/d (women) | — | adults 19–30 | AUTH | IOM 2001, doi:10.17226/10026 |
| UL | 40 mg/d | basis is **reduction in erythrocyte copper-zinc superoxide dismutase activity** — i.e. the UL exists to protect copper status | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| distribution | over 85% in skeletal muscle and bone; plasma is 0.1% of body zinc | — | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| mobilisable pool | "readily exchangeable zinc pools (those that exchange with zinc in plasma within 72 hours)" shrink under dietary restriction; no large reserve | the DRI report gives no store size — this is the key kinetic gap | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| onset of depletion | "clinically important features of zinc deficiency can occur with only modest degrees of dietary zinc restriction" (no timeline given in the DRI) | — | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| experimental depletion timeline | 7 weeks on a low-zinc, high-phytate diet (3–5 mg Zn/d) produced measurable falls in plasma, urine and hair zinc with changes in **taste acuity** and **cell-mediated immune response**; reversed by 30 mg/d over 2 weeks | 15 men, mean age 25.3 y | healthy young men | COH | Prasad 2020, *J Immunol Res* 2020:9207279, doi:10.1155/2020/9207279 |
| deficiency signs | growth retardation, alopecia, diarrhoea, delayed sexual maturation and impotence, eye and skin lesions, **impaired appetite** | — | humans | AUTH | IOM 2001, doi:10.17226/10026 |
| immune mechanism of deficiency | decreased thymulin activity in Th1 cells, decreased IL-2 and IFN-γ mRNA, impaired natural killer cell function | — | experimental human zinc deficiency | COH | Prasad 2020, doi:10.1155/2020/9207279 |
| zinc lozenges on cold duration | high-dose zinc acetate (>75 mg/d): **−42% duration** (95% CI 35% to 48%); other high-dose zinc salts: −20% (95% CI 12% to 28%); doses under 75 mg/d: uniformly no effect | 13 placebo-controlled trials | adults with common colds | MA | Hemilä 2011, *Open Respir Med J* 5:51–58, doi:10.2174/1874306401105010051 |
| phytate effect | reduces zinc absorption by complexation and precipitation in the gut | — | — | AUTH | IOM 2001, doi:10.17226/10026 |
| sweat [Zn] | 0.0001–0.02 mmol/L (0.007–1.3 mg/L) | negligible absolute loss | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |

**Interpretation for the game.** Zinc is the best-supported micronutrient for a *weeks*-scale mechanic,
and it is the one whose deficiency effects map most directly onto survival-game systems. The critical
fact is that there is no large mobilisable zinc store: over 85% of body zinc is locked in muscle and
bone and unavailable, so status follows intake with a lag of weeks, not years. Prasad's experimental
model gives the number the mod needs — **seven weeks at 3–5 mg/d produces measurable taste and
immune changes** — so a reasonable model is a zinc pool that empties in roughly six to eight weeks of
intake at a third of the RDA, with effects appearing in that window. Model three consequences,
because all three are supported: blunted taste and appetite (a beautiful mechanic — food gives less
satisfaction, the player eats less, which compounds), impaired wound healing, and increased
infection duration/severity. The cold-duration meta-analysis is the strongest quantitative hook: a
**42% reduction in illness duration** at high zinc dose is a large, well-bounded effect, though note
carefully that it is a *therapeutic lozenge* effect at pharmacological dose (>75 mg/d, twice the UL),
not proof that ordinary dietary zinc repletion shortens colds — the mod should model deficiency
lengthening illness rather than dietary zinc curing it. On the excess side the UL of 40 mg/d exists
purely to protect copper status, so zinc excess in the game should manifest as copper deficiency, not
as zinc toxicity. Kentucky 1993 sources: red meat (deer), eggs, and whole grains are good; the
phytate in beans, whole grains and peanut butter both supplies and blocks zinc, and a
rice-pasta-canned-vegetable diet is a realistic zinc-deficiency scenario. I did not verify a primary
citation for the acute zinc-induced vomiting dose (see Gaps).

## Iodine

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 150 µg/d | — | adults 19–50, both sexes | AUTH | IOM 2001, doi:10.17226/10026 |
| EAR | 95 µg/d | — | adults 19–30 | AUTH | IOM 2001, doi:10.17226/10026 |
| UL | 1100 µg/d | from a LOAEL of 1700 µg/d (significant rise in baseline and TRH-stimulated TSH) ÷ uncertainty factor 1.5; critical adverse effect is **elevated TSH** | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| thyroid iodine content | about 15 mg in an average adult thyroid in an iodine-sufficient region | ~one-third as thyroid hormone, two-thirds as precursors | iodine-sufficient adults | AUTH | IOM 2001, doi:10.17226/10026 |
| goitre threshold | urinary iodine 100 µg/L (≈125 µg/d intake) is the level at which goitre prevalence falls to about 2% | population-level indicator, not an individual one | populations | AUTH | IOM 2001, doi:10.17226/10026 |
| severe deficiency | goitre and hypothyroidism: thyroid activity rises to maximise uptake and recycling, but iodine is still too low to make thyroid hormone | — | populations in severely deficient regions | TXT | Zimmermann & Boelaert 2015, *Lancet Diabetes Endocrinol* 3:286–295, doi:10.1016/S2213-8587(14)70225-6 |
| mild-to-moderate deficiency | increased thyroid activity maintains euthyroidism in most individuals, at the cost of a higher population prevalence of toxic nodular goitre and hyperthyroidism | — | populations | TXT | Zimmermann & Boelaert 2015, doi:10.1016/S2213-8587(14)70225-6 |
| iodine excess | iodine status is a key determinant of thyroid disorders in adults in both directions; excess raises TSH and can precipitate thyroid dysfunction | — | adults | TXT | Zimmermann & Boelaert 2015, doi:10.1016/S2213-8587(14)70225-6 |

**Interpretation for the game.** Iodine is a **months-to-years** nutrient and should be modelled as
such or not at all. The thyroid holds about 15 mg against a 150 µg/d requirement — roughly a hundred
days of supply even at zero intake, and the thyroid upregulates uptake and recycles hormone
aggressively as stores fall, so goitre is a multi-month-to-multi-year process. That makes iodine a
poor fit for a survival game unless the save runs a year or more. The *adult* consequences to model
are hypothyroid: cold intolerance, lethargy, low energy, and a slowed metabolic rate — which maps
neatly onto a slower stamina recovery and a lower calorie burn — plus a visible goitre if the mod
wants a cosmetic tell at the extreme. Critically, the devastating iodine effects in the literature
(cretinism, IQ loss) are *developmental*, so they are irrelevant to an adult survivor and must not be
imported. Kentucky 1993 is well placed on the supply side: iodised salt had been standard in the US
since 1924 and dairy is iodine-rich, so as long as the player eats table salt or milk they cannot
become deficient — a nice detail is that a player living on unsalted foraged and hunted food in an
inland, historically goitre-belt state is the one who is exposed. Excess is essentially unreachable
from food; only kelp or an iodine antiseptic item could exceed 1100 µg/d.

## Selenium

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 55 µg/d | — | adults 19–50, both sexes | AUTH | IOM 2000, *DRI for Vitamin C, Vitamin E, Selenium and Carotenoids*, doi:10.17226/9810 |
| EAR | 45 µg/d | — | adults 19–30 | AUTH | IOM 2000, doi:10.17226/9810 |
| UL | 400 µg/d | adverse effect is selenosis (hair and nail brittleness and loss) | adults | AUTH | IOM 2000, doi:10.17226/9810 |
| Keshan disease | endemic congestive cardiomyopathy in a long belt of rural China where food selenium was low; multifocal myocardial necrosis and fibrous replacement; sodium selenite was protective in intervention trials | co-factor (coxsackievirus) implicated — selenium deficiency alone is necessary but probably not sufficient | rural Chinese populations, 1960s–70s | COH | Ge et al. 1983, *Virchows Arch A* 401:1–15, doi:10.1007/BF00644785, PMID 6412443 |
| selenosis | occurred where average intake was **5.0 mg/d** (range 3.2–6.7); **no selenosis** where average intake was 0.750 mg/d (range 0.240–1.51); morbidity affected nearly half of 248 inhabitants of the five worst-affected villages at peak (1961–1964) | loss of hair and nails was the commonest sign; skin, nervous system and possibly teeth also affected | high-selenium region of China | COH | Yang et al. 1983, *Am J Clin Nutr* 37:872–881, doi:10.1093/ajcn/37.5.872 |

**Interpretation for the game.** Selenium is a **geography** nutrient, not a diet nutrient, and that
is exactly why it is hard to justify in this game. Food selenium content tracks soil selenium, and
Keshan disease required a whole region eating locally grown food from selenium-poor soil for years.
Kentucky soils are not selenium-deficient and the American food supply is selenium-adequate, so a
1993 Kentucky survivor eating canned goods, grain and local game is not a plausible selenium
deficiency case. Recommend **omitting selenium as a tracked stat** and folding it into a generic
micronutrient axis if one exists. If the mod insists, the honest model is a very slow (year-plus)
counter whose extreme consequence is cardiomyopathy — reduced maximum stamina and exertional
breathlessness — with the caveat that the Keshan literature itself does not attribute the disease to
selenium alone. The excess side is unusually well characterised and gives a rare, usable *acute*
toxicity band: nothing at 0.75 mg/d, frank selenosis at 5 mg/d, a roughly sevenfold window. Since the
UL is 400 µg/d and a single Brazil nut can carry 70–90 µg, a "handful of Brazil nuts" toxicity
mechanic is technically supportable — but Brazil nuts are not a Kentucky scavenging item, so this is
flavour rather than substance.

## Copper

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| RDA | 900 µg/d | — | adults 19–50, both sexes | AUTH | IOM 2001, doi:10.17226/10026 |
| EAR | 700 µg/d | — | adults 19–30 | AUTH | IOM 2001, doi:10.17226/10026 |
| UL | 10 mg/d | NOAEL from 7 adults taking 10 mg/d copper gluconate for 12 weeks with normal liver function tests; critical endpoint is **liver damage** | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| distribution | nearly two-thirds of body copper is in skeleton and muscle | — | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| deficiency signs | normocytic hypochromic anaemia, leukopenia, neutropenia, osteoporosis; connective-tissue defects causing vascular and skeletal problems; anaemia from defective iron utilisation | — | humans | AUTH | IOM 2001, doi:10.17226/10026 |
| acquired deficiency causes | excess zinc (an infant given 16–24 mg Zn/d developed copper deficiency); premature infants on milk formula; malnourished infants with chronic diarrhoea fed cow's milk; prolonged total parenteral nutrition | primary dietary copper deficiency in free-living adults is essentially unreported | humans | AUTH | IOM 2001, doi:10.17226/10026 |

**Interpretation for the game.** Copper earns a place in the mod for exactly one reason: it is the
**failure mode of zinc excess**. Primary dietary copper deficiency in an adult who is eating is
effectively undocumented, so do not give copper its own intake-driven deficiency clock. Instead make
copper a *derived* state that falls when zinc intake is chronically high (the 40 mg/d zinc UL exists
precisely to protect it), and give it the anaemia-plus-neutropenia phenotype the DRI describes —
which conveniently overlaps the iron-deficiency anaemia effects already modelled, so it can reuse the
same stamina penalty plus an infection-susceptibility penalty. Note that copper deficiency anaemia is
*iron-refractory*: it does not respond to iron, which is a genuinely interesting mechanic if the game
ever surfaces a diagnosis. On the excess side the UL is a liver endpoint from a 12-week 10 mg/d study,
and food cannot reach it; the realistic in-game route to copper excess is drinking from copper
plumbing or a corroded container, which is a nice piece of 1993-house flavour but not a mechanic
worth building. Recommendation: derived stat only, no UI.

## Manganese

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI | 2.3 mg/d (men); 1.8 mg/d (women) | an AI, not an RDA — the evidence was insufficient to set an EAR | adults 19–50 | AUTH | IOM 2001, doi:10.17226/10026 |
| EAR/RDA | none set | — | all adults | AUTH | IOM 2001, doi:10.17226/10026 |
| UL | 11 mg/d | — | adults 19+ | AUTH | IOM 2001, doi:10.17226/10026 |

**Interpretation for the game.** Do not model manganese. The DRI panel could not even establish an
average requirement, dietary manganese deficiency has not been convincingly demonstrated in
free-living humans, and manganese is plentiful in grains, nuts and tea — all abundant in the game's
food list. The only human manganese toxicity of note is occupational *inhalation* (manganism, a
parkinsonian syndrome in welders and miners), which is not a dietary route and not a survival-game
mechanic. Recommendation: omit entirely, or list it in a "tracked but inert" tier if the mod wants
completeness in its UI.

## Dietary fibre

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI (total fibre) | 38 g/d (men 19–50); 25 g/d (women 19–50) | an AI, derived from coronary-heart-disease risk, not from a measured requirement; 14 g per 1000 kcal | adults | AUTH | IOM 2005, *DRI for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein and Amino Acids*, doi:10.17226/10490 |
| EAR/RDA | none set | — | all adults | AUTH | IOM 2005, doi:10.17226/10490 |
| UL | none set | the adverse effect of excess is gastrointestinal, not systemic | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| fibre supplementation on constipation, responder rate | RR 1.48 (95% CI 1.17–1.88; P = 0.001); 66% responded on fibre vs 41% on control | 16 RCTs, 1251 participants | adults with chronic constipation | MA | van der Schoot et al. 2022, *Am J Clin Nutr* 116:953–969, doi:10.1093/ajcn/nqac184 |
| fibre on stool frequency | SMD 0.72 (95% CI 0.36–1.08; P = 0.0001) | best at doses above 10 g/d and durations of at least 4 weeks; psyllium most effective | as above | MA | van der Schoot et al. 2022, doi:10.1093/ajcn/nqac184 |
| fibre on stool consistency | SMD 0.32 (95% CI 0.18–0.46; P < 0.0001) | — | as above | MA | van der Schoot et al. 2022, doi:10.1093/ajcn/nqac184 |
| fibre adverse effect | flatulence SMD 0.80 (95% CI 0.47–1.13; P < 0.00001) | the one reliable downside | as above | MA | van der Schoot et al. 2022, doi:10.1093/ajcn/nqac184 |
| fibre and chronic disease | 15–30% lower all-cause mortality, cardiovascular mortality, coronary heart disease, stroke, type 2 diabetes and colorectal cancer at higher vs lower intake; 25–29 g/d gives the greatest risk reduction, more above 30 g/d | 185 prospective studies (≈135 million person-years) and 58 trials (4635 participants) | adults | MA | Reynolds et al. 2019, *Lancet* 393:434–445, doi:10.1016/S0140-6736(18)31809-9 |
| fibre and satiety | viscous fibres (pectins, β-glucans, guar gum) reduced appetite in 59% of comparisons vs 14% for less viscous fibres; effects on body weight modest | systematic review of RCTs | adults | MA | Wanders et al. 2011, *Obes Rev* 12:724–739, doi:10.1111/j.1467-789X.2011.00895.x |

**Interpretation for the game.** Fibre is the mod's best opportunity for a *new* nutrient that vanilla
does not model and that the game's food list makes genuinely variable, but its supported effects are
gut effects, not performance effects. Two things are solidly modellable. First, **constipation**: the
meta-analysis is clean and the numbers are usable — 66% versus 41% responders and a stool-frequency
SMD of 0.72, with the dose threshold above 10 g/d and the time constant of about four weeks. That
gives a defensible design: sustained fibre intake far below the AI produces a constipation state over
days to a few weeks, relieved by fibre above roughly 10–15 g/d, and the relief is not instant.
Second, **satiety**: viscous fibre reduces appetite about four times as often as non-viscous fibre in
RCTs, which supports a mechanic where a high-fibre meal (beans, cabbage, oats, whole grain) keeps
hunger down longer per calorie than an equal-calorie low-fibre meal (crisps, chocolate, white rice).
That is a real and interesting food-choice lever. Do not model fibre as affecting stamina, strength
or immunity: the chronic-disease benefits in Reynolds are 15–30% relative risk reductions over
decades in observational data, which is invisible on a survival-game timescale and must not be
converted into a short-term stat. Also model the downside — the flatulence SMD of 0.80 is the largest
effect in the constipation meta-analysis, so a sudden jump to a very high-fibre diet earning a
temporary discomfort penalty is evidence-based, not just comic. Kentucky 1993 gap analysis: canned
vegetables, cabbage, beans, potatoes with skin, peanut butter, corn and whole-grain bread carry
fibre; rice, pasta, crisps, chocolate, eggs, milk, canned fish and all meat carry effectively none. A
survivor living on hunted venison plus white rice is a textbook zero-fibre diet, which makes this a
mechanic the game's own item set will exercise naturally.

## Omega-3 fatty acids (ALA, EPA, DHA)

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI, α-linolenic acid (ALA, 18:3n-3) | 1.6 g/d (men); 1.1 g/d (women) | AMDR 0.6–1.2% of energy | adults 19–50 | AUTH | IOM 2005, doi:10.17226/10490 |
| EAR/RDA/UL for ALA | none set | — | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| EPA and DHA | no US DRI set; they were considered within the ALA AMDR | this is a real gap in the US DRI framework | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| long-chain n-3 (EPA/DHA) supplementation, all-cause mortality | RR 0.97 (95% CI 0.93–1.01); 143,693 participants, 11,297 deaths, 45 RCTs | i.e. no clear effect | adults, mostly cardiovascular prevention trials | MA | Abdelhamid et al. 2020, *Cochrane Database Syst Rev*, doi:10.1002/14651858.CD003177.pub5 |
| long-chain n-3, coronary heart disease events | RR 0.91 (95% CI 0.85–0.97), NNTB 167; 134,116 participants, 8791 events, 32 RCTs | small benefit, moderate-to-low certainty | as above | MA | Abdelhamid et al. 2020, doi:10.1002/14651858.CD003177.pub5 |
| long-chain n-3, triglycerides | reduced by about 15%, dose-dependent | — | as above | MA | Abdelhamid et al. 2020, doi:10.1002/14651858.CD003177.pub5 |
| ALA supplementation, all-cause mortality | RR 1.01 (95% CI 0.84–1.20); 19,327 participants, 5 RCTs | no effect | adults | MA | Abdelhamid et al. 2020, doi:10.1002/14651858.CD003177.pub5 |
| ALA, arrhythmia | RR 0.73 (95% CI 0.55–0.97), NNTB 91; 4912 participants, 2 RCTs | only 2 trials — fragile | adults | MA | Abdelhamid et al. 2020, doi:10.1002/14651858.CD003177.pub5 |
| total trials | 86 RCTs, 162,796 participants, 12–88 months duration | — | — | MA | Abdelhamid et al. 2020, doi:10.1002/14651858.CD003177.pub5 |

**Interpretation for the game.** The honest conclusion is that **omega-3 status should not drive any
short-term game mechanic**. The largest and best-conducted synthesis available — 86 trials and over
162,000 participants — finds no effect on all-cause mortality, a small effect on coronary events over
1–7 years, and a triglyceride change with no gameplay analogue. There is no evidence base for
omega-3 affecting stamina, strength, mood on a weeks timescale, healing or immunity at a magnitude a
survival simulation could justify. The defensible role for omega-3 in the mod is as a **dietary
variety and food-quality marker**: a diet including oily fish (canned salmon, sardines, freshly
caught fish) meets the ALA/EPA/DHA intakes, and one that does not simply scores lower on a
"diet quality" axis without a mechanical penalty. If the owner wants a mechanic anyway, the only
supportable one is that ALA and long-chain n-3 intake is a *prerequisite* alongside linoleic acid for
avoiding essential fatty acid deficiency (next section) — that is, fold n-3 into a single "essential
fat" requirement rather than tracking it separately. Kentucky 1993: canned fish, walnuts and eggs are
the recoverable sources; deer and rabbit are very lean, and a diet of lean wild game plus refined
grain is low in total fat generally, which matters much more than the n-3 fraction of it.

## Omega-6 (linoleic acid) and essential fatty acid deficiency

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| AI, linoleic acid (LA, 18:2n-6) | 17 g/d (men); 12 g/d (women) | AMDR 5–10% of energy | adults 19–50 | AUTH | IOM 2005, doi:10.17226/10490 |
| EAR/RDA/UL for LA | none set | — | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| total fat AMDR | 20–35% of energy; no UL, no RDA ("ND") | — | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| biochemical onset of EFA deficiency | eicosatrienoic acid and linoleic acid levels abnormal **after 1 week**; arachidonic acid abnormal **after 2 weeks** | 32 patients studied prospectively | adults on fat-free parenteral nutrition | COH | Goodgame, Lowry & Brennan 1978, *Surgery* 84:271–277, PMID 98859 |
| diagnostic threshold reached | **all** patients on fat-free parenteral nutrition for 4 weeks had a triene:tetraene ratio above 0.4 | the standard biochemical marker of EFA deficiency | as above | COH | Goodgame et al. 1978, PMID 98859 |
| clinical signs | skin lesions suggestive of EFA deficiency developed in 2 of the 32 patients; biochemical abnormalities reversed rapidly on intravenous lipid | dry, scaly dermatitis is the classic sign | as above | COH | Goodgame et al. 1978, PMID 98859 |

**Interpretation for the game.** This is the one essential-fat mechanic with a real, measured
timescale, and it is faster than most people expect: **one week of a truly fat-free intake moves the
biochemistry, two weeks impairs arachidonic acid, four weeks reaches the diagnostic
triene:tetraene threshold of 0.4, and dermatitis follows**. That gives a clean model — a "fat-free
diet" counter that begins at about 7 days, becomes a visible dry, scaly, flaking skin condition
somewhere in the 4–8 week band, impairs wound healing, and resolves quickly once any fat is eaten. Two
strong caveats the mod must respect. First, this evidence comes from *total parenteral nutrition* with
literally zero fat; almost any real food contains some fat, so the trigger should be a very low
absolute fat intake (well under a few grams a day), not merely "a low-fat diet". Second, the classic
survival-game version of this — "rabbit starvation" — is really a *protein-excess plus
energy-and-fat-deficit* syndrome rather than pure EFA deficiency, and its acute symptoms (nausea,
diarrhoea, lassitude within about a week on lean meat alone) belong under the protein section below.
Kentucky 1993 makes this mechanic live: deer and rabbit are extremely lean, so a player who hunts
exclusively and eats no peanut butter, chocolate, eggs, milk, crisps or cooking fat is a genuine
candidate. Peanut butter in particular is a powerful corrective item — a few tablespoons covers the
linoleic acid AI on its own. Practical simplification: collapse LA and ALA into one "essential fat"
requirement of roughly 15 g/d of plant or fish fat, with the deficiency clock above.

## Carbohydrate quality: glycaemic effects and sugar

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| carbohydrate RDA | 130 g/d | set from the brain's glucose requirement | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| carbohydrate AMDR | 45–65% of energy | — | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| added sugars | "limit to no more than 25% of total energy" | this is the IOM's maximal intake, not a target | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| free sugars | reduce to **below 10% of total energy** (strong recommendation); a further reduction below 5% is suggested (conditional) | free sugars = sugars added by manufacturer/cook/consumer plus those in honey, syrups and fruit juice | adults and children | AUTH | WHO 2015, *Guideline: sugars intake for adults and children*, ISBN 978-92-4-154902-8 |
| glycaemic index / glycaemic load | "smaller or no risk reductions were found … comparing the effects of diets characterised by low rather than higher glycaemic index or load" | contrasted against clear dose-response for fibre and whole grains | adults, observational | MA | Reynolds et al. 2019, doi:10.1016/S0140-6736(18)31809-9 |
| what does carry the signal | dietary fibre and whole-grain intake, with dose-response consistent across prospective studies and trials | 15–30% risk reductions, see fibre section | adults | MA | Reynolds et al. 2019, doi:10.1016/S0140-6736(18)31809-9 |

**Interpretation for the game.** The single most useful finding here is a **negative** one: the
best-available synthesis of carbohydrate quality finds the health signal in fibre and whole grains,
and *little or nothing* in glycaemic index or glycaemic load. So a mod should resist building a GI
system — it would be a lot of per-item data for an effect the evidence does not support. Model
carbohydrate quality through the fibre axis instead, which is the same data with real evidence behind
it. The IOM's 130 g/d carbohydrate RDA is genuinely useful as the floor the brain needs, and is the
right number to hang a "cognitive fog on very low carbohydrate" effect on if the mod wants one.
Sugar: there is an authoritative ceiling (WHO: below 10% of energy; IOM: no more than 25%), but the
harms behind it are dental caries and long-run weight gain, neither of which a
days-to-months survival save will show. The defensible treatment of chocolate, sweets and soda is
therefore that they are **calorie-dense, nutrient-poor and satiety-poor** — they fill the calorie
budget without filling the micronutrient or fibre budgets — which is exactly the mechanic the mod
already wants for rebalancing vanilla items, and needs no new sugar stat. What is *not* supported is
any acute "sugar crash" performance penalty in a healthy person, or a sugar-addiction mechanic.

## Very-low-carbohydrate and high-protein diets

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| protein RDA | 56 g/d (men); 46 g/d (women) — 0.8 g/kg/d | — | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| protein AMDR | 10–35% of energy | the 35% ceiling is the IOM's upper bound | adults | AUTH | IOM 2005, doi:10.17226/10490 |
| prudent maximum protein intake | ~2–2.5 g/kg/d, about 25% of energy | gut amino-acid absorption is limited to 1.3–10 g/h | adults | TXT | Bilsborough & Mann 2006, *Int J Sport Nutr Exerc Metab* 16:129–152, doi:10.1123/ijsnem.16.2.129 |
| ketogenic LCHF diet and performance | 3 weeks of a ketogenic LCHF diet **negated** the performance benefit of intensified training: no improvement in 10 km race-walk time vs 5–7% improvement in the carbohydrate groups | despite markedly increased whole-body fat oxidation and an equal rise in peak aerobic capacity | elite race walkers, 3-arm controlled trial | RCT | Burke et al. 2017, *J Physiol* 595:2785–2807, doi:10.1113/JP273230 |
| mechanism | LCHF adaptation **impaired exercise economy** — a higher oxygen cost for the same speed | measured directly | as above | RCT | Burke et al. 2017, doi:10.1113/JP273230 |
| sports-nutrition position | carbohydrate availability governs performance in high-intensity and prolonged exercise | ACSM/AND/DC joint position stand | athletes | AUTH | *Nutrition and Athletic Performance*, 2016, *Med Sci Sports Exerc* 48:543–568, doi:10.1249/MSS.0000000000000852 |

**Interpretation for the game.** Burke's trial is the best single piece of evidence in this report for
a *macronutrient composition* mechanic, and it says something a survival game can use directly: a
very-low-carbohydrate diet does not reduce aerobic capacity, but it makes the character **less
economical** — the same work costs more oxygen — so hard efforts fatigue faster and the benefit of
training is lost. That maps cleanly onto stamina: on a sustained very-low-carbohydrate intake, leave
maximum stamina alone but raise the stamina cost of running, fighting and heavy work by a modest
amount (the paper's effect was the difference between no improvement and a 5–7% improvement over
three weeks, so a penalty in the 5–10% range on exertion cost is the right order), and make the
penalty take one to three weeks to develop and to reverse. Pair it with the 130 g/d carbohydrate RDA
as the floor below which the penalty starts accruing. On protein, the important game-relevant ceiling
is that there is one: the prudent maximum is around 2–2.5 g/kg/d and the gut can only absorb amino
acids at 1.3–10 g/h, which is the physiological basis of "rabbit starvation" — an all-lean-meat diet
forces protein intake above what urea synthesis can comfortably clear while supplying no fat or
carbohydrate for energy. For a player eating nothing but venison and rabbit, the defensible model is a
protein-excess state appearing within about a week — nausea, diarrhoea, weakness and paradoxically
rising hunger — that resolves the moment fat or carbohydrate is added. I did not verify a primary
citation for the classic rabbit-starvation case reports in this pass (see Gaps); the protein ceiling
above is the verified part, the one-week timescale is inference from it.

## Sweat and loss modelling (water and electrolytes)

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| total water AI | 3.7 L/d (men); 2.7 L/d (women) | includes water in food and all beverages, not just drinking water | adults 19–50 | AUTH | IOM 2005, doi:10.17226/10925 (values as tabulated in NASEM 2019, doi:10.17226/25353) |
| whole-body sweating rate | 1.51 ± 0.70 L/h (American football); 1.28 ± 0.57 L/h (endurance sport); basketball, soccer and baseball significantly lower | SDs are about half the mean — individual variation dominates | 1303 athletes, field testing | COH | Barnes et al. 2019, doi:10.1080/02640414.2019.1633159, PMID 31230518 |
| sweat sodium loss rate | 55.9 mmol/h (American football); 51.7 mmol/h (endurance) | ≈1.3 g Na/h, ≈3.3 g salt/h | as above | COH | Barnes et al. 2019, doi:10.1080/02640414.2019.1633159 |
| sweat electrolyte concentrations | Na⁺ 10–90 mmol/L; Cl⁻ 10–90; K⁺ 2–8; Ca²⁺ 0.2–2.0; Mg²⁺ 0.02–0.40; Fe 0.0001–0.03; Zn 0.0001–0.02; Cu 0.0005–0.02 mmol/L | Table 3 of the review; ranges span the literature | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |
| dehydration threshold for performance | avoid excessive dehydration, defined as **more than 2% body weight loss** from water deficit | the standard operational threshold | exercising adults | AUTH | American College of Sports Medicine, Sawka et al. 2007, *Med Sci Sports Exerc* 39:377–390, doi:10.1249/mss.0b013e31802ca597, PMID 17277604 |
| hyponatraemia risk | plasma [Na⁺] below 135 mmol/L; primary cause is drinking in excess of losses; drinking to thirst is the recommended strategy | applies to prolonged exercise, hikers and military as well as athletes | adults | AUTH | Hew-Butler et al. 2015, doi:10.1097/JSM.0000000000000221 |

**Interpretation for the game.** This is the section a mod can implement most directly, because it
yields a single equation. Charge water loss as `sweat_rate × hours`, with sweat rate scaled by
exertion and heat and landing in the 1.2–1.6 L/h band for hard work in warm conditions and well under
0.5 L/h at rest — note that Barnes's standard deviations are roughly half the means, so an individual
multiplier per character (0.5×–1.5×) is more faithful than a single global rate. Then charge each
electrolyte as `sweat_litres × concentration` using the Baker ranges, and the arithmetic itself tells
you what to model: sodium and chloride at 10–90 mmol/L are the only two where a few hours of work
moves a meaningful fraction of the daily requirement, potassium at 2–8 mmol/L is marginal, and
calcium, magnesium, iron, zinc and copper are three to five orders of magnitude below their body
pools per litre of sweat and should simply be ignored as exertion losses. The 2% body-mass threshold
from the ACSM position stand is the right hook for the existing thirst and performance systems: below
2% deficit, no penalty; above it, escalating penalties. Pair it with the hyponatraemia rule from the
consensus statement — a character who drinks large volumes of plain water while sweating heavily and
eating no salt should trend toward low sodium, because that combination, not sweat loss alone, is what
actually produces hyponatraemia. A "drink to thirst" design is both the evidence-based recommendation
and the simplest implementation. One practical simplification: because Cl⁻ tracks Na⁺ 1:1 in sweat and
in food, model a single salt axis and derive chloride if it is ever displayed.

## Alcohol

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| diuresis, euhydrated | 1 L of 4% beer (≈40 g ethanol) produced 1279 ± 256 mL urine over 4 h vs 1121 ± 148 mL for alcohol-free beer | the *extra* diuresis was about 160 mL — roughly 4 mL urine per g ethanol, far less than folklore suggests | healthy men, crossover | RCT | Hobson & Maughan 2010, *Alcohol Alcohol* 45:366–373, doi:10.1093/alcalc/agq029 |
| diuresis, hypohydrated | 261 ± 138 mL urine vs 174 ± 61 mL for alcohol-free beer over 4 h | total urine output collapses when already dehydrated | as above | RCT | Hobson & Maughan 2010, doi:10.1093/alcalc/agq029 |
| key finding | "the diuretic action of alcohol is blunted when the body is hypohydrated" | directly contradicts the common assumption | as above | RCT | Hobson & Maughan 2010, doi:10.1093/alcalc/agq029 |
| blood alcohol reached | 7.1 ± 1.8 mmol/L (hypohydrated) and 6.0 ± 2.7 mmol/L (euhydrated) 1 h after 1 L of 4% beer | ≈0.033% and 0.028% BAC | as above | RCT | Hobson & Maughan 2010, doi:10.1093/alcalc/agq029 |
| sleep architecture | dose-dependent: shortens sleep latency and consolidates the first half of the night, then **disrupts the second half**; REM onset significantly delayed at all doses; total REM reduced at moderate-to-high doses; slow-wave sleep increased in the first half at all doses | consistent across doses and demographics | healthy adults | MA | Ebrahim et al. 2013, *Alcohol Clin Exp Res* 37:539–549, doi:10.1111/acer.12006 |
| coordination / cognition | all six domains assessed — divided attention, executive function, perception, psychomotor skills, reaction time, vigilance — showed impairment at blood alcohol concentrations **at or below the legal driving limit** in many jurisdictions | the review found inconsistent measures across studies, so it does not give per-BAC effect sizes | adults | MA | Garrisson et al. 2021, *Accid Anal Prev* 154:106052, doi:10.1016/j.aap.2021.106052 |
| thiamine | Wernicke encephalopathy prevalence is higher in people who misuse alcohol; dietary deficiency is one of the four diagnostic criteria; treatment is 200 mg thiamine three times daily, given **before any carbohydrate** | the abstract does not itemise the mechanisms (reduced intake, reduced absorption, impaired hepatic storage, raised requirement) | adults | AUTH | Galvin et al. 2010, *Eur J Neurol* 17:1408–1418, doi:10.1111/j.1468-1331.2010.03153.x |

**Interpretation for the game.** The most valuable finding here is a correction: **alcohol is a much
weaker dehydrating agent than the game-design instinct assumes, and it is weakest precisely when the
character is already dehydrated.** One litre of beer produced only about 160 mL of extra urine in
euhydrated men, and the diuresis was blunted when hypohydrated. So beer should be modelled as a *net
positive* fluid source (a litre in, roughly 1.28 L out over four hours means the beer itself still
contributed water, and the 4% drink is 96% water), and spirits as roughly neutral to mildly negative
because they carry little water per gram of ethanol. Do not implement a large thirst penalty for
drinking beer — that is not what the evidence shows. Where alcohol genuinely earns a penalty is
**sleep and coordination**. The sleep effect is the cleanest mechanic in this whole report: drinking
before bed makes the character fall asleep faster and sleep well for the first half of the night, then
sleep badly for the second half, with REM suppressed — so the correct model is a *reduced sleep
quality* outcome (the character wakes less rested despite sleeping as long), not a reduced sleep
duration, and the effect should scale with dose. For coordination, the review is clear that impairment
begins at or below legal driving limits, i.e. well below visible drunkenness, so a graded aim,
reaction-time and stumble penalty starting at a low dose is defensible — but note the review declined
to publish per-BAC effect sizes, so the *shape* of the curve is a design choice, not a measurement.
Thiamine is a long-arc mechanic: heavy chronic drinking plus a poor diet is the classic route to
thiamine deficiency and Wernicke encephalopathy, and the game-relevant detail is the guideline's
warning to give thiamine *before* carbohydrate — carbohydrate refeeding in a thiamine-deficient person
precipitates the encephalopathy, which is a genuinely interesting trap if the mod ever models a
long-term alcoholic character. For a typical save, model alcohol as: mild fluid gain, sleep-quality
penalty, coordination penalty, calories with no micronutrients, and a slow thiamine drain only for
sustained heavy use.

## Caffeine

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| diuresis | acute doses of **at least 250–300 mg** cause a short-term rise in urine output in people who have abstained; tolerance develops in regular consumers | — | adults | MA | Maughan & Griffin 2003, *J Hum Nutr Diet* 16:411–420, doi:10.1046/j.1365-277X.2003.00477.x |
| net fluid balance | "no support for the suggestion that consumption of caffeine-containing beverages as part of a normal lifestyle leads to fluid loss in excess of the volume ingested" | i.e. coffee and tea hydrate | adults | MA | Maughan & Griffin 2003, doi:10.1046/j.1365-277X.2003.00477.x |
| moderate coffee intake | no evidence of dehydration; total body water and hydration biomarkers unchanged vs equal water | counterbalanced crossover in a free-living population | habitual male coffee drinkers | RCT | Killer, Blannin & Jeukendrup 2014, *PLoS ONE* 9:e84154, doi:10.1371/journal.pone.0084154 |
| sleep disruption | 400 mg caffeine disrupted sleep when taken 0, 3 **or 6 hours** before bed (all P < 0.05 vs placebo) | the abstract reports significance, not minutes | healthy adults | RCT | Drake et al. 2013, *J Clin Sleep Med* 9:1195–1200, doi:10.5664/jcsm.3170 |
| sleep, broader synthesis | caffeine lengthens sleep latency, shortens total sleep time and reduces sleep efficiency and slow-wave sleep | systematic review of epidemiological studies and RCTs | adults | MA | Clark & Landolt 2017, *Sleep Med Rev* 31:70–78, doi:10.1016/j.smrv.2016.01.006 |
| endurance performance | 3–6 mg/kg improved mean power output by 3.03 ± 3.07% (ES 0.23 ± 0.15) and time-trial completion time by 2.22 ± 2.59% (ES 0.41 ± 0.2) | 46 studies; 2 studies found slower time trials and 5 found lower power — non-responders exist | trained adults | MA | Southward, Rutherfurd-Markwick & Ali 2018, *Sports Med* 48:1913–1928, doi:10.1007/s40279-018-0939-8 |

**Interpretation for the game.** Caffeine is the mirror image of alcohol: the folk model is wrong in
the opposite direction. **Coffee and tea should count as full hydration in the mod.** Two independent
lines of verified evidence say so — the review finds no net fluid loss from normal caffeine
consumption, and the controlled crossover trial found no dehydration from moderate coffee versus equal
water. A diuretic effect appears only at 250–300 mg or more in someone unaccustomed to caffeine, which
in game terms means a first cup after a long dry spell might justify a trivial, transient effect and
nothing more. The two mechanics worth building are the two the evidence supports well. First,
**sleep**: 400 mg — roughly four cups of drip coffee — measurably disrupted sleep even taken six hours
before bed, so caffeine should carry a lasting sleep-latency and sleep-quality penalty with a half-life
of several hours, and a player who drinks coffee in the afternoon should sleep worse that night. That
is a genuinely good tactical trade-off: stay alert now, sleep badly later. Second, **performance**: a
3–6 mg/kg dose (about 210–420 mg for a 70 kg adult) improves endurance power by about 3% and time-trial
performance by about 2%, so a small, short-lived stamina benefit is evidence-based — but keep it
small, and note that the meta-analysis found genuine non-responders, which would justify a
per-character responsiveness trait if the mod wants that texture. Do not model caffeine as reducing
fatigue debt: it masks sleepiness without repaying sleep, and the sleep evidence says the debt
accumulates underneath. Kentucky 1993: instant coffee, ground coffee, tea and soda are all plausible
scavenged items, and caffeine tolerance in a habitual drinker (relevant to the diuresis row) would be
a reasonable trait to model as decaying over days of abstinence.

## Cross-cutting

These are the interactions that cross section boundaries. Everything here is a *second-order* effect —
nutrient A changing how much of nutrient B the character actually gets, or one intake driving another
nutrient's loss — which is exactly the class of mechanic a nutrition mod can implement cheaply, because
it needs only a multiplier on an absorption or loss term rather than a new stat.

| parameter | value | range or uncertainty | population/context | grade | citation |
|---|---|---|---|---|---|
| calcium × iron | 40–300 mg Ca per meal reduces both heme and non-heme iron absorption, dose-related; little further effect above ~600 mg | single-meal radioisotope studies, 126 subjects | non-anaemic adults | COH | Hallberg et al. 1991, *Am J Clin Nutr* 53:112–119, doi:10.1093/ajcn/53.1.112 |
| phytate × iron | dose-dependent inhibition of iron absorption: 2 mg phytate phosphorus **−18%**, 25 mg **−64%**, 250 mg **−82%** (all P < 0.001) | seven dose levels, dual-radioisotope wheat rolls | healthy men | COH | Hallberg, Brune & Rossander 1989, *Am J Clin Nutr* 49:140–144, doi:10.1093/ajcn/49.1.140, PMID 2911999 |
| vitamin C × iron, single meal | ascorbic acid "significantly counteracted" the phytate inhibition; the meat effect was weaker and seen only at the highest phytate level | same study | healthy men | COH | Hallberg et al. 1989, doi:10.1093/ajcn/49.1.140 |
| vitamin C × iron, whole diet | **no** significant difference in mean iron absorption across mean vitamin C intakes of 51–247 mg/d; "the facilitating effect of vitamin C on iron absorption from a complete diet is far less pronounced than that from single meals" | 12 subjects, labelled wheat roll with every meal for 5 d per period | adults | COH | Cook & Reddy 2001, *Am J Clin Nutr* 73:93–98, doi:10.1093/ajcn/73.1.93, PMID 11124756 |
| whole-diet iron bioavailability | 14–18% for mixed diets; 5–12% for vegetarian diets, in subjects with no iron stores | "in multimeal studies with a varied diet and multiple inhibitors and enhancers, the effect of single components has been … more modest"; iron status generally matters more than diet composition | adults, isotope and intake data | TXT | Hurrell & Egli 2010, *Am J Clin Nutr* 91:1461S–1467S, doi:10.3945/ajcn.2010.28674F, PMID 20200263 |
| phytate × magnesium | fractional apparent Mg absorption fell **32.5% → 13.0%** at 1.49 mmol added phytic acid (whole-meal-bread level, P < 0.0005) and **32.2% → 24.0%** at 0.75 mmol (brown-bread level, P < 0.01); dose-dependent (P < 0.005) | two stable-isotope studies, 8–9 adults each, total Mg standardised across meals | healthy adults | COH | Bohn et al. 2004, *Am J Clin Nutr* 79:418–423, doi:10.1093/ajcn/79.3.418, PMID 14985216 |
| phytate × zinc | reduces zinc absorption by complexation and precipitation in the gut | the DRI gives no dose-response | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| zinc × copper | 2 × 25 mg Zn/d (50 mg/d total) for 6 weeks significantly **reduced erythrocyte Cu,Zn-superoxide dismutase** (P < 0.05 at 6 wk) with plasma copper and ferroxidase unchanged at 2, 4 and 6 weeks | placebo-controlled; a marker change, not clinical copper deficiency | healthy adult men | RCT | Fischer, Giroux & L'Abbé 1984, *Am J Clin Nutr* 40:743–746, doi:10.1093/ajcn/40.4.743, PMID 6486080 |
| zinc UL rationale | the 40 mg/d zinc UL is set on reduction in erythrocyte Cu,Zn-superoxide dismutase activity — i.e. it exists to protect copper status | — | adults | AUTH | IOM 2001, doi:10.17226/10026 |
| magnesium × potassium | magnesium deficiency "aggravates hypokalemia and renders it refractory to treatment by potassium"; mechanism is loss of intracellular-Mg inhibition of ROMK channels, increasing distal K secretion | "magnesium deficiency alone … does not necessarily cause hypokalemia" — an increase in distal sodium delivery or elevated aldosterone may be required | humans | TXT | Huang & Kuo 2007, *J Am Soc Nephrol* 18:2649–2652, doi:10.1681/ASN.2007070792, PMID 17804670 |
| iodine × selenium | combined selenium and iodine deficiency leads to myxoedematous cretinism; selenoprotein deiodinases are required for thyroid hormone metabolism; the thyroid retains high selenium even on poor supply | in combined severe deficiency, **iodine must be normalised before selenium is given**, or hypothyroidism is precipitated | populations | TXT | Zimmermann & Köhrle 2002, *Thyroid* 12:867–878, doi:10.1089/105072502761016494, PMID 12487769 |
| iron × iodine | iron deficiency impairs thyroid hormone synthesis by reducing the activity of heme-dependent thyroid peroxidase; iron-deficiency anaemia blunts, and iron supplementation improves, the efficacy of iodine supplementation | — | populations | TXT | Zimmermann & Köhrle 2002, doi:10.1089/105072502761016494 |
| sodium × water | exercise-associated hyponatraemia (serum [Na⁺] < 135 mmol/L) is caused primarily by **drinking in excess of losses**, not by sodium loss per se; "drinking to thirst" is the recommended strategy | applies to hikers and military as well as athletes | adults | AUTH | Hew-Butler et al. 2015, *Clin J Sport Med* 25:303–320, doi:10.1097/JSM.0000000000000221, PMID 26102445 |
| sodium/potassium × sweat | sweat Na⁺ and Cl⁻ 10–90 mmol/L against a 65 mmol/d sodium AI; sweat K⁺ only 2–8 mmol/L against a 66–87 mmol/d potassium AI | so sweat is a first-order sodium driver and at most a marginal potassium one | exercising adults | TXT | Baker 2019, doi:10.1080/23328940.2019.1632145, PMID 31608304 |
| alcohol × thiamine | Wernicke encephalopathy prevalence is higher in people who misuse alcohol; dietary deficiency is one of the four diagnostic criteria; give **thiamine before any carbohydrate** | — | adults | AUTH | Galvin et al. 2010, *Eur J Neurol* 17:1408–1418, doi:10.1111/j.1468-1331.2010.03153.x |
| alcohol × magnesium, chronic | both total and ionised circulating magnesium are "markedly reduced" in chronic alcohol-use disorder; skeletal muscle magnesium content is reduced and the kidney's normal response to hypomagnesaemia is blunted | 25 studies retained from 2719 records; significant statistical heterogeneity (I²), no significant publication bias | adults with chronic alcohol-use disorder | MA | Vanoni et al. 2021, *Nutrients* 13:1959, doi:10.3390/nu13061959, PMID 34200366 |
| alcohol × magnesium, moderate | significantly higher, alcohol-dose-related urinary Mg **and Ca** excretion after an oral Mg load in moderate consumers vs non-consumers | 14 consumers vs 10 non-consumers, differing smoking habits — small and confounded | adult men | COH | Rylander et al. 2001, *Scand J Clin Lab Invest* 61:401–405, doi:10.1080/003655101316911459, PMID 11569488 |
| caffeine × calcium | oral caffeine raises urinary excretion of **calcium, magnesium, sodium and chloride** for at least 3 h; the effect is proportional to dose per lean body mass and **no adaptation occurs** with continued consumption | "for younger adult women consuming adequate calcium, moderate caffeine intakes may have little or no deleterious effects", partly via increased intestinal absorption; older women compensate less well | adults | TXT | Massey & Whiting 1993, *J Nutr* 123:1611–1614, doi:10.1093/jn/123.9.1611, PMID 8360789 |

**Interpretation for the game.** The absorption interactions are where a nutrition mod gets the most
realism per line of code, because they turn *what you eat together* into a mechanic rather than just
*what you eat*. The single strongest number in this section is the phytate effect on iron: 25 mg of
phytate phosphorus cuts iron absorption by 64%, and 250 mg by 82%, which is a bigger lever than
almost anything else in this report — so a meal of beans, whole grain or peanut butter eaten with the
day's iron source should deliver far less iron than the same iron eaten with meat, and vitamin C in
the same meal should claw a good part of that back. But the mod must respect the whole-diet
correction: Cook and Reddy found **no** effect of vitamin C intake on iron absorption from a complete
diet across 51–247 mg/d, and Hurrell and Egli say plainly that single-component effects shrink in
multimeal studies. The honest design is therefore a **per-meal absorption multiplier** with a modest
total range — anchor whole-diet iron bioavailability at Hurrell and Egli's 14–18% for a mixed diet and
5–12% for a meat-free one, and let phytate, calcium and vitamin C move the per-meal figure inside
roughly a twofold band rather than the eightfold band a single-meal study would suggest. Phytate
should be a *single item property* used for iron, zinc and magnesium at once: the same compound drives
all three, and Bohn's stable-isotope numbers (Mg absorption 32.5% → 13.0% at whole-meal-bread phytate
levels) are strong enough to be worth implementing. That is also the correct way to model "fibre
blocks minerals" — the inhibitor is phytate, which travels *with* whole grains, bran and legumes, not
fibre itself, so a psyllium or cabbage fibre source should carry no mineral penalty while whole-grain
bread and beans should. Two interactions deserve to be *loss* terms rather than absorption terms.
Caffeine raises urinary calcium, magnesium, sodium and chloride for at least three hours with no
tolerance — a small, clean, per-cup drain that is worth adding precisely because the caffeine section
otherwise gives caffeine no cost but sleep — and alcohol both wastes magnesium acutely (Rylander) and
depletes it chronically, with the kidney's defence blunted (Vanoni), which makes a heavy-drinking
character the mod's natural magnesium-deficiency case and links straight to the neuromuscular
hyperexcitability effects in the magnesium section. Chain the derived deficiencies rather than giving
each one its own intake clock: high zinc → low copper (Fischer's 50 mg/d for six weeks is the only
verified adult dose-response, and it moved a marker rather than a person); low magnesium →
potassium-refractory hypokalaemia (Huang and Kuo, with the important caveat that low magnesium alone
usually is not enough); low iron → blunted thyroid function, and low selenium → impaired thyroid
hormone metabolism, so a character who is iron- *and* iodine-poor should be worse off than the sum of
the two. Finally, keep the water axis honest in both directions: hyponatraemia is a *drinking* fault,
not a sweating fault, so the trigger condition must be high plain-water intake plus high sweat sodium
loss plus no salt — and salt tablets, canned soup or a salted meal should fix it, while more water
should make it worse.

## Gaps

What this report looked for and could not verify. Everything listed here is either a figure used in an
interpretation paragraph that rests on inference rather than on a fetched record, a number the source
literature does not contain, or a claim whose primary citation I failed to pin down. None of it may be
cited as evidence.

**Marked unverified in the sections above.**

| gap | where | status |
|---|---|---|
| total body potassium pool, quoted as roughly 3000–4000 mmol in a lean adult | Potassium, interpretation | **unverified** — could not be pinned to a fetched primary record; the interpretation flags it in place |
| chloride UL of 3.6 g/d | Chloride, table | **unverified** — reproduced DRI tables list it, but two fetches of the 2019 appendix disagreed with each other; the 2005 chapter set no chloride UL |
| refeeding-syndrome hypophosphataemia: serum thresholds, onset timescale, carbohydrate dose that triggers it | Phosphorus, interpretation | **not verified** — named as the correct mechanism, with no primary citation fetched for any of its numbers |
| acute zinc dose that induces vomiting | Zinc, interpretation | **not verified** — no primary citation fetched |
| size of the mobilisable zinc pool in grams | Zinc, table | **absent from the source** — the DRI report describes "readily exchangeable zinc pools (those that exchange with zinc in plasma within 72 hours)" but gives no store size; this is the key kinetic gap for a zinc clock |
| rabbit-starvation case reports; the ~1-week onset of protein-excess symptoms on an all-lean-meat diet | Very-low-carbohydrate and high-protein diets | **not verified** — the protein ceiling (2–2.5 g/kg/d; 1.3–10 g/h absorption) is verified from Bilsborough & Mann; the one-week timescale is inference from it |
| per-BAC effect sizes for alcohol on attention, reaction time and psychomotor skill | Alcohol, table | **absent from the source** — the systematic review found inconsistent measures across studies and declined to publish effect sizes, so the *shape* of any in-game curve is a design choice |
| minutes of sleep latency added, or minutes of total sleep lost, per mg of caffeine | Caffeine, table | **absent from the source** — Drake et al. report significance (P < 0.05) at 0, 3 and 6 h, not magnitudes |
| the four mechanisms by which alcohol misuse causes thiamine deficiency (reduced intake, reduced absorption, impaired hepatic storage, raised requirement) | Alcohol, table | **absent from the fetched record** — the EFNS guideline abstract does not itemise them |

**Figures used in interpretation that rest on inference or general knowledge, not on a fetched record.**

| figure | where used | status |
|---|---|---|
| whole blood carries ~0.5 mg iron per mL, hence ~250 mg iron per 500 mL of blood lost | Iron, interpretation — the entire "fast injury clock" rests on it | **unverified** — arithmetic from haemoglobin iron content; no record fetched. Verify before building the bleeding mechanic |
| ~2–3 years to empty a 1000 mg male iron store at 1 mg/d basal loss | Iron, interpretation | **inference** — arithmetic from two verified DRI rows, not a measured depletion time |
| selenium content of a single Brazil nut, given as 70–90 µg | Selenium, interpretation | **unverified** — no food-composition record fetched |
| iodised salt standard in the United States since 1924; Kentucky in the historical goitre belt | Iodine, interpretation | **unverified** — historical claim, no record fetched |
| caffeine content of a cup of drip coffee, used to convert 400 mg to "about four cups" | Caffeine, interpretation | **unverified** — no food-composition record fetched |
| resting sweat rate "well under 0.5 L/h" | Sweat and loss modelling, interpretation | **inference** — Barnes et al. measured athletes during sport; the resting end of the band is extrapolation |
| beer as a net positive fluid source | Alcohol, interpretation | **inference** from the verified Hobson & Maughan urine volumes (1 L in, 1279 mL out over 4 h including baseline diuresis); the trial did not report net fluid balance as such |
| ~15 g/d as a single combined "essential fat" requirement | Omega-6 / EFA deficiency, interpretation | **inference** — a practical collapse of the verified 17 g/d LA and 1.6 g/d ALA AIs, not a published figure |
| 5–10% exertion-cost penalty for a very-low-carbohydrate diet | Very-low-carbohydrate diets, interpretation | **inference** — scaled from Burke's verified 5–7% *training-improvement* difference, which is not the same quantity |
| free sugars / added sugars in the WHO and IOM ceilings | Carbohydrate quality, table | verified, but note the WHO guideline was cited by ISBN only; it has **PMID 25905159**, now verified and carried in the bibliography |
| Haas & Brownlie page range | Iron, table | the table gives 676S–688S; the fetched Crossref record gives **676S–690S**. Minor, and the bibliography carries the fetched range |
| Ebrahim et al. 2013 page range 539–549 | Alcohol, table | volume 37, year 2013, authors and title all verified; Crossref carries **no page range** for this record |

**Questions the literature does not answer at the resolution a simulation needs.**

- **Time to onset on a fixed deficient intake** — the quantity a game model actually needs — is missing
  for almost every nutrient here. The exceptions are the three worth naming: essential fatty acids
  (1 week biochemical, 2 weeks arachidonic acid, 4 weeks diagnostic threshold — Goodgame et al.), zinc
  (7 weeks at 3–5 mg/d to measurable taste and immune change — Prasad), and magnesium (urinary
  conservation within 3–4 days, but no measured time to tetany). Iron's timescale is arithmetic, not
  measurement. Iodine's is inferred from a 15 mg thyroid store. Everything else is uncharacterised.
- **Reversal kinetics** are worse characterised than depletion kinetics everywhere except zinc (Prasad's
  30 mg/d for 2 weeks) and EFA deficiency ("reversed rapidly on intravenous lipid"). For sodium,
  magnesium, potassium and iron I found no verified repletion time constant at all.
- **Wound healing** is asserted as a zinc-deficiency consequence from the DRI's list of deficiency
  signs; I found no verified quantitative effect size for dietary zinc status on healing rate, so the
  magnitude of any in-game healing penalty is unsupported.
- **Sweat sodium acclimatisation.** Heat acclimation is widely held to lower sweat sodium
  concentration, which would matter for a character who works through a Kentucky summer. I did not
  verify a primary source, so the per-character sweat-sodium constant recommended in the sodium section
  is modelled as fixed rather than adapting — **unverified** either way.
- **Stool electrolyte losses in diarrhoea.** The potassium section recommends charging potassium losses
  to illness and diarrhoea events rather than to sweat, but I found no verified figure for potassium,
  sodium or water lost per episode, so the size of that charge is undetermined.
- **Low-fat whole-food diets.** The only verified EFA-deficiency timeline comes from fat-free *total
  parenteral nutrition*. No study was found that induced EFA deficiency on a low-fat diet of real food,
  so the trigger threshold ("well under a few grams a day") is a judgement, not a measurement.
- **Adult dietary copper deficiency** has no verified dose-response. Fischer et al. 1984 is the closest:
  50 mg Zn/d for six weeks moved a copper enzyme marker in healthy men. The IOM's clinical case of
  zinc-induced copper deficiency at 16–24 mg Zn/d was an infant.
- **Keshan disease causation is confounded.** The Ge et al. report itself implicates a coxsackievirus
  co-factor, so selenium deficiency appears necessary but not sufficient; any in-game cardiomyopathy
  driven by selenium alone overstates the evidence.
- **Glycaemic index** is a negative finding drawn from observational data within Reynolds et al.; the
  absence of a signal is not the same as a demonstrated absence of effect, though it is more than
  enough reason not to build a GI system.
- **Nothing in this report is specific to the game's own items.** No verified nutrient composition for
  any Project Zomboid food is established here; every Kentucky-1993 sourcing note is general
  food-composition knowledge and needs a dataset pass before it drives item values.

## Bibliography

Every citation used as evidence anywhere in this report, once, alphabetical by first author. Each was
verified by fetching the Crossref API record (`api.crossref.org/works/<DOI>`) or the Europe PMC REST
record and confirming that title, authors and year match the claim made here; two entries carry a PMID
only because no DOI exists for them. Where a fetched record's page range or identifier differs from an
in-table citation above, the fetched value is given here and the discrepancy is listed in Gaps.
Nothing named only in the Gaps section appears below: those are the unverified items.

1. Abdelhamid AS, Brown TJ, Brainard JS, Biswas P, et al. 2020. Omega-3 fatty acids for the primary and secondary prevention of cardiovascular disease. *Cochrane Database of Systematic Reviews*. doi:10.1002/14651858.CD003177.pub5
2. Aburto NJ, Hanson S, Gutierrez H, Hooper L, et al. 2013. Effect of increased potassium intake on cardiovascular risk factors and disease: systematic review and meta-analyses. *BMJ* 346:f1378. doi:10.1136/bmj.f1378
3. American College of Sports Medicine; Sawka MN, Burke LM, Eichner ER, Maughan RJ, Montain SJ, Stachenfeld NS. 2007. American College of Sports Medicine position stand: exercise and fluid replacement. *Medicine & Science in Sports & Exercise* 39:377–390. doi:10.1249/mss.0b013e31802ca597, PMID 17277604
4. Avenell A, Mak JCS, O'Connell DL. 2014. Vitamin D and vitamin D analogues for preventing fractures in post-menopausal women and older men. *Cochrane Database of Systematic Reviews*. doi:10.1002/14651858.CD000227.pub4
5. Baker LB. 2019. Physiology of sweat gland function: the roles of sweating and sweat composition in human health. *Temperature* 6:211–259. doi:10.1080/23328940.2019.1632145, PMID 31608304
6. Barnes KA, Anderson ML, Stofan JR, Dalrymple KJ, et al. 2019. Normative data for sweating rate, sweat sodium concentration, and sweat sodium loss in athletes: an update and analysis by sport. *Journal of Sports Sciences* 37:2356–2366. doi:10.1080/02640414.2019.1633159, PMID 31230518
7. Bilsborough S, Mann N. 2006. A review of issues of dietary protein intake in humans. *International Journal of Sport Nutrition and Exercise Metabolism* 16:129–152. doi:10.1123/ijsnem.16.2.129
8. Bohn T, Davidsson L, Walczyk T, Hurrell RF. 2004. Phytic acid added to white-wheat bread inhibits fractional apparent magnesium absorption in humans. *American Journal of Clinical Nutrition* 79:418–423. doi:10.1093/ajcn/79.3.418, PMID 14985216
9. Burke LM, Ross ML, Garvican-Lewis LA, Welvaert M, et al. 2017. Low carbohydrate, high fat diet impairs exercise economy and negates the performance benefit from intensified training in elite race walkers. *Journal of Physiology* 595:2785–2807. doi:10.1113/JP273230
10. Camaschella C. 2015. Iron-deficiency anemia. *New England Journal of Medicine* 372:1832–1843. doi:10.1056/NEJMra1401038
11. Clark I, Landolt HP. 2017. Coffee, caffeine, and sleep: a systematic review of epidemiological studies and randomized controlled trials. *Sleep Medicine Reviews* 31:70–78. doi:10.1016/j.smrv.2016.01.006
12. Cook JD, Reddy MB. 2001. Effect of ascorbic acid intake on nonheme-iron absorption from a complete diet. *American Journal of Clinical Nutrition* 73:93–98. doi:10.1093/ajcn/73.1.93, PMID 11124756
13. Drake C, Roehrs T, Shambroom J, Roth T. 2013. Caffeine effects on sleep taken 0, 3, or 6 hours before going to bed. *Journal of Clinical Sleep Medicine* 9:1195–1200. doi:10.5664/jcsm.3170
14. Ebrahim IO, Shapiro CM, Williams AJ, Fenwick PB. 2013. Alcohol and sleep I: effects on normal sleep. *Alcoholism: Clinical and Experimental Research* 37 (no page range in the fetched record). doi:10.1111/acer.12006
15. Fischer PW, Giroux A, L'Abbé MR. 1984. Effect of zinc supplementation on copper status in adult man. *American Journal of Clinical Nutrition* 40:743–746. doi:10.1093/ajcn/40.4.743, PMID 6486080
16. Galvin R, Bråthen G, Ivashynka A, Hillbom M, et al. 2010. EFNS guidelines for diagnosis, therapy and prevention of Wernicke encephalopathy. *European Journal of Neurology* 17:1408–1418. doi:10.1111/j.1468-1331.2010.03153.x
17. Garrison SR, Korownyk CS, Kolber MR, Allan GM, et al. 2020. Magnesium for skeletal muscle cramps. *Cochrane Database of Systematic Reviews*. doi:10.1002/14651858.CD009402.pub3
18. Garrisson H, Scholey A, Ogden E, Benson S. 2021. The effects of alcohol intoxication on cognitive functions critical for driving: a systematic review. *Accident Analysis & Prevention* 154:106052. doi:10.1016/j.aap.2021.106052
19. Ge K, Xue A, Bai J, Wang S. 1983. Keshan disease — an endemic cardiomyopathy in China. *Virchows Archiv A Pathological Anatomy and Histopathology* 401:1–15. doi:10.1007/BF00644785, PMID 6412443
20. Goodgame JT, Lowry SF, Brennan MF. 1978. Essential fatty acid deficiency in total parenteral nutrition: time course of development and suggestions for therapy. *Surgery* 84:271–277. PMID 98859 (no DOI)
21. Graudal NA, Hubeck-Graudal T, Jurgens G. 2020. Effects of low sodium diet versus high sodium diet on blood pressure, renin, aldosterone, catecholamines, cholesterol, and triglyceride. *Cochrane Database of Systematic Reviews*. doi:10.1002/14651858.CD004022.pub5
22. Haas JD, Brownlie T. 2001. Iron deficiency and reduced work capacity: a critical review of the research to determine a causal relationship. *Journal of Nutrition* 131:676S–690S. doi:10.1093/jn/131.2.676S, PMID 11160598
23. Hallberg L, Brune M, Rossander L. 1989. Iron absorption in man: ascorbic acid and dose-dependent inhibition by phytate. *American Journal of Clinical Nutrition* 49:140–144. doi:10.1093/ajcn/49.1.140, PMID 2911999
24. Hallberg L, Brune M, Erlandsson M, Sandberg AS, et al. 1991. Calcium: effect of different amounts on nonheme- and heme-iron absorption in humans. *American Journal of Clinical Nutrition* 53:112–119. doi:10.1093/ajcn/53.1.112
25. Hemilä H. 2011. Zinc lozenges may shorten the duration of colds: a systematic review. *Open Respiratory Medicine Journal* 5:51–58. doi:10.2174/1874306401105010051
26. Hew-Butler T, Rosner MH, Fowkes-Godek S, Dugas JP, et al. 2015. Statement of the Third International Exercise-Associated Hyponatremia Consensus Development Conference, Carlsbad, California, 2015. *Clinical Journal of Sport Medicine* 25:303–320. doi:10.1097/JSM.0000000000000221, PMID 26102445
27. Hobson RM, Maughan RJ. 2010. Hydration status and the diuretic action of a small dose of alcohol. *Alcohol and Alcoholism* 45:366–373. doi:10.1093/alcalc/agq029
28. Huang CL, Kuo E. 2007. Mechanism of hypokalemia in magnesium deficiency. *Journal of the American Society of Nephrology* 18:2649–2652. doi:10.1681/ASN.2007070792, PMID 17804670
29. Hurrell R, Egli I. 2010. Iron bioavailability and dietary reference values. *American Journal of Clinical Nutrition* 91:1461S–1467S. doi:10.3945/ajcn.2010.28674F, PMID 20200263
30. Institute of Medicine. 1997. *Dietary Reference Intakes for Calcium, Phosphorus, Magnesium, Vitamin D, and Fluoride*. Washington DC: National Academies Press. doi:10.17226/5776
31. Institute of Medicine. 2000. *Dietary Reference Intakes for Vitamin C, Vitamin E, Selenium, and Carotenoids*. Washington DC: National Academies Press. doi:10.17226/9810
32. Institute of Medicine. 2001. *Dietary Reference Intakes for Vitamin A, Vitamin K, Arsenic, Boron, Chromium, Copper, Iodine, Iron, Manganese, Molybdenum, Nickel, Silicon, Vanadium, and Zinc*. Washington DC: National Academies Press. doi:10.17226/10026
33. Institute of Medicine. 2005. *Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein, and Amino Acids*. Washington DC: National Academies Press. doi:10.17226/10490
34. Institute of Medicine. 2005. *Dietary Reference Intakes for Water, Potassium, Sodium, Chloride, and Sulfate*. Washington DC: National Academies Press. doi:10.17226/10925
35. Institute of Medicine. 2011. *Dietary Reference Intakes for Calcium and Vitamin D*. Washington DC: National Academies Press. doi:10.17226/13050
36. Killer SC, Blannin AK, Jeukendrup AE. 2014. No evidence of dehydration with moderate daily coffee intake: a counterbalanced cross-over study in a free-living population. *PLoS ONE* 9:e84154. doi:10.1371/journal.pone.0084154
37. Manoguerra AS, Erdman AR, Booze LL, Christianson G, et al. 2005. Iron ingestion: an evidence-based consensus guideline for out-of-hospital management. *Clinical Toxicology* 43:553–570. doi:10.1081/CLT-200068842
38. Massey LK, Whiting SJ. 1993. Caffeine, urinary calcium, calcium metabolism and bone. *Journal of Nutrition* 123:1611–1614. doi:10.1093/jn/123.9.1611, PMID 8360789
39. Maughan RJ, Griffin J. 2003. Caffeine ingestion and fluid balance: a review. *Journal of Human Nutrition and Dietetics* 16:411–420. doi:10.1046/j.1365-277X.2003.00477.x
40. National Academies of Sciences, Engineering, and Medicine. 2019. *Dietary Reference Intakes for Sodium and Potassium*. Washington DC: National Academies Press. doi:10.17226/25353
41. *Nutrition and Athletic Performance* (joint position statement of the Academy of Nutrition and Dietetics, Dietitians of Canada and the American College of Sports Medicine). 2016. *Medicine & Science in Sports & Exercise* 48:543–568. doi:10.1249/MSS.0000000000000852 — the fetched Crossref record carries no author list
42. Pasricha SR, Low M, Thompson J, Farrell A, et al. 2014. Iron supplementation benefits physical performance in women of reproductive age: a systematic review and meta-analysis. *Journal of Nutrition* 144:906–914. doi:10.3945/jn.113.189589, PMID 24717371
43. Prasad AS. 2020. Lessons learned from experimental human model of zinc deficiency. *Journal of Immunology Research* 2020:9207279. doi:10.1155/2020/9207279
44. Reynolds A, Mann J, Cummings J, Winter N, et al. 2019. Carbohydrate quality and human health: a series of systematic reviews and meta-analyses. *The Lancet* 393:434–445. doi:10.1016/S0140-6736(18)31809-9
45. Rylander R, Mégevand Y, Lasserre B, Amstutz W, Granbom S. 2001. Moderate alcohol consumption and urinary excretion of magnesium and calcium. *Scandinavian Journal of Clinical and Laboratory Investigation* 61:401–405. doi:10.1080/003655101316911459, PMID 11569488
46. Southward K, Rutherfurd-Markwick KJ, Ali A. 2018. The effect of acute caffeine ingestion on endurance performance: a systematic review and meta-analysis. *Sports Medicine* 48:1913–1928. doi:10.1007/s40279-018-0939-8
47. van der Schoot A, Drysdale C, Whelan K, Dimidi E. 2022. The effect of fiber supplementation on chronic constipation in adults: an updated systematic review and meta-analysis of randomized controlled trials. *American Journal of Clinical Nutrition* 116:953–969. doi:10.1093/ajcn/nqac184
48. Vanoni FO, Milani GP, Agostoni C, Treglia G, Faré PB, Camozzi P, Lava SAG, Bianchetti MG, Janett S. 2021. Magnesium metabolism in chronic alcohol-use disorder: meta-analysis and systematic review. *Nutrients* 13:1959. doi:10.3390/nu13061959, PMID 34200366
49. Wanders AJ, van den Borne JJGC, de Graaf C, Hulshof T, et al. 2011. Effects of dietary fibre on subjective appetite, energy intake and body weight: a systematic review of randomized controlled trials. *Obesity Reviews* 12:724–739. doi:10.1111/j.1467-789X.2011.00895.x
50. Weaver CM, Alexander DD, Boushey CJ, Dawson-Hughes B, et al. 2016. Calcium plus vitamin D supplementation and risk of fractures: an updated meta-analysis from the National Osteoporosis Foundation. *Osteoporosis International* 27:367–376. doi:10.1007/s00198-015-3386-5
51. World Health Organization. 2015. *Guideline: Sugars Intake for Adults and Children*. Geneva: WHO. PMID 25905159 (no DOI; ISBN 978-92-4-154902-8)
52. Yang GQ, Wang SZ, Zhou RH, Sun SZ. 1983. Endemic selenium intoxication of humans in China. *American Journal of Clinical Nutrition* 37:872–881. doi:10.1093/ajcn/37.5.872
53. Zimmermann MB, Köhrle J. 2002. The impact of iron and selenium deficiencies on iodine and thyroid metabolism: biochemistry and relevance to public health. *Thyroid* 12:867–878. doi:10.1089/105072502761016494, PMID 12487769
54. Zimmermann MB, Boelaert K. 2015. Iodine deficiency and thyroid disorders. *The Lancet Diabetes & Endocrinology* 3:286–295. doi:10.1016/S2213-8587(14)70225-6
