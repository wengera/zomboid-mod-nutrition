# Plan 18: symptoms through vanilla's own moodles — design

Angus, 2026-10-21, in a brainstorm in chat. Characters now outlive vanilla's starvation death: the straight-line ceilings of Plan 17. They must be punished for it through existing vanilla moodles and stats, at rates that make sense, with no new moodle-panel indicators. The principle is Plan 17's equitable total punishment: alive past vanilla's death point is fine while the character is miserable.

The evidence behind this design:
- `.superpowers/sdd/plan-18-brainstorm/inventory.md`: what the mod drives today, which stats a mod can write, and their constraints.
- `.superpowers/sdd/plan-18-brainstorm/science.md`: the register's science per condition, and its gaps.

## 1. The symptom model

### 1.1 The clock
Each lethal cause's progress is `p_i = 1 − f_i`. Here `f_i` is the cause's remaining fraction in `record.drain` (Plan 17: `D.frac[code]`), and the causes are:
- starvation;
- dehydration;
- scurvy;
- wet beriberi;
- pellagra;
- severe hyponatraemia;
- the iron rung (an overdose).

`p_i` runs from 0 at onset to 1 at the cause's death point. It already follows the death pace (Vanilla, Shortened or Realistic). It also eases while the ceiling recovers (Plan 17 R2), so the symptoms ease with the body.

### 1.2 One table per cause
Each cause has a small table of symptom rows. A row names:
- a lever (§ 1.3);
- the body part, for pain;
- a shape over `p_i` (or over the cause's own time, for later research shapes);
- a magnitude.

There are three shapes:
- `flat`: constant while the cause applies;
- `linear` from `a` at `p = 0` to `b` at `p = 1`;
- `knots`: piecewise linear points.

The table is data in the effects table's module, so researched shapes later replace the flat ones without code changes. An example is the hunger pangs, which rise over days 1–3, fade as a total fast settles, and give way to deeper aches from about week 2 (Angus wants this eventually).

### 1.3 The levers in this plan
- **Endurance cap.** It deepens with progress: light at onset, so the character tires sooner, and severe near death, so the character can barely run or fight. It works on every server, sleep on or off.

  Angus's choice replaces fatigue on sleep-off servers, where the engine resets an out-of-handler FATIGUE write (#2947). The mod's existing fatigue rows stay, and still work only where sleep is on.
- **Pain.**
  - Flat and low-grade, about the first Pain moodle level, while the cause is **active**: its ceiling falling, not merely recovering.
  - It sits on the cause's body part:
    - starvation: the lower torso (stomach);
    - dehydration: the head;
    - scurvy: the lower legs and knees;
    - wet beriberi: the lower legs;
    - pellagra: the lower torso;
    - severe hyponatraemia: the head;
    - the iron overdose: the lower torso.

    These body parts are game choices pending research.
  - Angus: "a full day of not eating starts to cause low grade pain". Starvation's onset (`K.drain.STARVE_ONSET_H`, 30 unfed hours) is about that.
- **Stress and unhappiness floors.** They reach their first moodle level partway through a cause and deepen toward the end. Angus asked for them visible; today's condition stress floors sit below the Stress moodle's first level. Stress and pain also natively lengthen the time to fall asleep (#2786), which gives "can't sleep well when starving" without new code.

### 1.4 Overlap
When causes overlap:
- endurance takes the lowest cap;
- pain adds per body part, under a cap;
- stress and unhappiness take the highest floor.

`NR.HealthCombine` governs health only.

### 1.5 Severity
The sandbox Severity dial scales these symptom magnitudes, as it scales the mod's other effects. The health lines stay unscaled (Plan 15).

### 1.6 Overlay mode
Vanilla owns HUNGER and THIRST in Overlay mode. So starvation and dehydration add no symptoms there, as their health lines don't. The deficiencies, hyponatraemia and the iron rung still apply.

## 2. Mechanics

### 2.1 Pain
- The engine sets added pain per body part (`BodyPart.setAdditionalPain`). A direct write to the PAIN stat snaps back to the body-part target (#2362).
- Added pain decays on its own. A 42.21 jar read gives about 0.005 × the game-time multiplier a tick, about 0.9 a game minute at the 90-minute day; it is not yet in the register.
- The server re-sets each affected part's added pain to its target once a minute. The level holds with a small dip between minutes. When the cause stops, the mod stops setting it and it decays naturally.
- A real injury's pain stacks on top, as vanilla does.

### 2.2 Endurance
- The mod's ENDURANCE cap (`K.hybrid` caps, the Overfull row, Plan 15 Task 8) is generalised so it can reach the severe Endurance moodle levels. Today's clamp allows level 1 only.
- Endurance regenerates between minutes and is pulled back each minute, as the Overfull cap is.

### 2.3 Floors
Stress and unhappiness use the composer's existing floor ops at larger magnitudes, set from vanilla's moodle thresholds.

### 2.4 The probe first
One short live session measures, before any design number is fixed:
- a server-set added pain shows the client's Pain moodle, and the dip between minutes;
- the pain survives a relog and a restart (whether added pain is saved);
- a deep endurance cap shows the right Endurance moodle levels, and endurance's climb between minutes;
- the floors reach their moodles.

The design's magnitudes are set from these readings.

## 3. Rule 6
- There is no per-tick work.
- Each player-minute costs only, per active cause: one Java call per painful body part, plus the endurance cap through the existing write.
- With no cause active the cost is zero.
- A bench before and after, and a Java-call count against the build before.

## 4. Proof
- **Kernel tests** for:
  - the clock;
  - each shape;
  - the overlap rules;
  - Severity scaling;
  - Overlay;
  - easing during recovery;
  - pain only while active.

  Followed by a mutation pass.
- **The golden trace,** re-recorded under a named cause.
- **A live acceptance session** on a Realistic fast with water. The Exertion, Pain, Stress and Unhappy moodles appear at their predicted progress, on the server and on the client, graded against the HEAD replay of the run's own inputs.
- **A smoke boot** of the final upload copy.

## 5. Guide and register
- **The guide:** each cause's section and the fast chart's notes name its symptoms. The limitations name the flat pain as a placeholder for researched shapes.
- **The register:** rows for the mechanism, the probe's readings, the live acceptance, and the game-choice magnitudes. Open rows for the research plan:
  - hunger-pang time course;
  - the deeper aches of wasting;
  - sleep disturbance;
  - the deficiency prodromes (beriberi, pellagra);
  - per-symptom onsets (science.md's gaps).

## 6. Game choices (set after the probe)
- the endurance cap's light and severe ends, as Endurance moodle levels;
- the flat pain level and the body parts;
- the floor curves: first moodle level at a stated progress, the second near the end;
- the pain cap per body part.

## 7. Not in this plan
- the researched shapes;
- waking a sleeper from Lua (`forceAwake` and kin are unmeasured in multiplayer);
- new moodles;
- the dead speed and temperature seats (open item X47).
