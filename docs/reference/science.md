# The science register

The science register `docs/reference/science.tsv` holds every evidenced value the nutrition mod may ship: a requirement, a store size, an onset time, an effect size, a threshold, a rate, a fitted model constant. It is the second of the two registers the mod cites (spec § 0): the claims register says what the game does, the science register says what the evidence says, and a number in the mod with no row in either does not ship.

## Columns

| column | what it holds |
|---|---|
| `id` | `S` and four digits, contiguous from `S0001`; the mod cites the bare id (`S0000` is this page's illustration and is never minted) |
| `topic` | one slug of the controlled vocabulary below, so the rows a nutrient record or a system model needs are one filter away; empty on an open row |
| `parameter` | the quantity, as a noun phrase, with the direction of an effect where the row is an effect |
| `value` | the number and its unit, or the qualitative finding |
| `range` | the uncertainty or spread as the source gives it — a confidence interval, a study count, a between-study range |
| `population` | who was studied and in what context; every value is a central tendency for that population |
| `grade` | `MA`, `RCT`, `COH`, `EXP`, `MODEL`, `AUTH` or `TXT` (below); empty on an open row, because nothing was graded |
| `citation` | authors, year, journal, then the record: `doi:10.…`, `pmid:…`, `url:https://…` for an authority page, `isbn:…` for a book; two records separated by `; ` |
| `source` | the research report and section the row was harvested from, readable at the tag `design-phase-v1` |
| `status` | `settled`, `open` (a named gap: topic, grade, value and citation may be empty), `unverified` (a number quoted but not resolved), `superseded` |
| `successor` | the row that replaces a superseded one |

## Topics

Nutrients: `vitamin-a`, `vitamin-d`, `vitamin-e`, `vitamin-k`, `vitamin-c`, `thiamine`, `riboflavin`, `niacin`, `pantothenate`, `vitamin-b6`, `biotin`, `folate`, `vitamin-b12`, `choline`, `sodium`, `potassium`, `chloride`, `calcium`, `magnesium`, `phosphorus`, `iron`, `zinc`, `copper`, `iodine`, `selenium`, `manganese`, `water`, `fibre`, `essential-fats`, `carbohydrate-quality`, `alcohol`, `caffeine`, `phytate`, `sweat`, `digestion`. Systems: `energy`, `body-composition`, `lean-mass`, `strength`, `aerobic-capacity`, `glycogen`, `protein`, `fatigue-sleep`, `cognition`, `mood`, `perception`, `healing`, `immunity`, `thermal`, `toxicity`, `starvation`, `refeeding`. `general` is for a cross-cutting row that fits no other. The vocabulary is `sciencelib.TOPICS`; a slug is requested in a harvest task's report and added by the controller in the commit that lands the rows, with the reason.

## Grades

| grade | meaning |
|---|---|
| `MA` | a meta-analysis, network meta-analysis, meta-regression or systematic review |
| `RCT` | a randomised controlled trial, a controlled crossover or an inpatient controlled trial |
| `EXP` | a controlled human depletion or dosing experiment that is not randomised |
| `COH` | a cohort, an observational or cross-sectional study, a regression derived from one, or a case report |
| `AUTH` | an authority report — a DRI, an EFSA opinion, a position stand, a consensus statement |
| `TXT` | a narrative review, a textbook chapter, an editorial or a modelling paper |
| `MODEL` | a published mathematical model cited for its shape and fitted constants, never for an effect size |

A row's grade is the source's, never the row's importance. A source graded with a slashed pair takes the left-most member of the rank `MA`, `RCT`, `EXP`, `COH`, `AUTH`, `TXT`, whichever order it is written in; `MODEL` never appears in a pair, because a model cited beside a trial is two rows. Where a meta-analysis and a later update disagree, the row carries the later reading and both records. Two irreconcilable sources are two `settled` rows whose `parameter` names the disagreement; the design's choice between them is a ruling, not a row.

## Rules

- A value the mod ships rests on a `settled` row; an `open` or `unverified` row names what is missing and ships nothing.
- Every `settled` row's citation was resolved against its record through Europe PMC or Crossref before the row was minted: title, first author and year matched.
- A game choice — a saturation constant, a clamp, a cadence, a dial's default — is not a row; the row is the cited value the choice rests on, and the choice is named as one where it is made.
- `python tools/science_check.py` checks the register's schema before every commit that touches it; `python tools/science_check.py --scan <the mod's tree>` resolves every `S` id token the mod carries and fails a token that names no row or a superseded one; the scan is never given `tools/` or `docs/`, which carry the reserved illustration in prose.
- A row is minted by the controller from a task's part file with `python tools/science_delta.py apply <part.tsv>`; a writer never edits the register.
- A superseded row keeps its id and names its successor; a row withdrawn after minting goes `unverified` or `superseded`, never deleted; contiguity is a minting invariant, not a repair path.
- A row is self-sufficient: its citation is the record, and its source is provenance.

## Sources

The rows were distilled from the eight science reports of the design phase (2026-09-27), each of which resolved every citation it carried through Europe PMC and matched title, authors, journal and year before quoting a number. One paragraph per report follows as its rows land.
