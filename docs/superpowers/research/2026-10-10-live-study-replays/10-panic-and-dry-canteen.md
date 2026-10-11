# 10. The PANIC ~6 source (F-T9-1) and the HUNGER drift after the dry-canteen refill (F-T9-4)

Plan 11f, ruling T9-2: a read-only investigation. Investigator model: claude-opus-5-5. Read at HEAD `cf40f100`; the
x331-x333 artifacts were read from the working tree (staged, not committed). Every replay below ran on a scratch
script that imports `tools/replay_live.py` and `testing/experiments/x33_grade.py` unchanged. Nothing in the repo was
edited, and no game was booted.

## Verdicts

| Finding | Source | Verdict |
|---|---|---|
| F-T9-1: PANIC 5.74-6.28 at 6 of 8 positive eats | **The mod's own dehydration PANIC floor.** At 1.5 % body-mass water deficit and above, the effects set carries `panicTarget` 7 (`NR_Data_Effects.lua:210-213`). The writer raises PANIC to 7 once a game minute (`NR_Kernel_Hybrid.lua:98-101`, `NR_Server_Writer.lua:277-278, 299`), and vanilla's per-tick decay pulls it back to about 5.7 before the next write (#3400). | **Mod behaviour, working as designed: neither a writer bug nor a harness artifact.** The design has a consequence nobody had read: vanilla's `UpdateBoredom` zeroes BOREDOM whenever PANIC is above 5. So every dehydrated character (≥ 1.5 %) has BOREDOM pinned at 0, and monotony's BOREDOM add is wiped. Task 9's line "no mod panicTarget source is active: the only panicTarget rows are caffeine's" is wrong. |
| F-T9-4: the replay's HUNGER over tolerance on 3/16/18 rows | **The libs' autodrop drink events land the water one drain too early.** The lib injects the sip as a `drink` event through `IN.land` before the drain, so the replay empties it in that same drain. The mod lands `fluids.autoDrop` in Nutrients, after Kinetics has already emptied the stomach that minute. So the replay's stomach runs one landing-minute (dtM) of emptying ahead. It holds less liquid, so it is less full, so its HUNGER is higher. | **A tool (lib) limitation, not mod behaviour.** The libs' `autodrop_events` mis-time the landing. When the same events are re-expressed as `setpath fluids.autoDrop`, all three sessions pass with 0 findings (HUNGER max 0.00062, 0.00055, 0.00066 against 0.002). |

## A. Where the PANIC came from (F-T9-1)

### The mod writes it

- **The effects data.** The `dehyd` band rows at bands 2-8 (≥ 1.5 % body mass) add `stressTarget` 0.06 and
  `panicTarget` 7. Source: `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Effects.lua:210-213`. The comment there reads
  "7, not 6: level 1 is > 6 #2369". The band edges are 1, 1.5, 2, … % (`NR_Kernel_Effects.lua:62-71`), and the band
  is computed as `b[I.dehyd] = E.atOrAbove(fluids.dehydPct, E.DEHYD_EDGES)` (`NR_Kernel_Effects.lua:257`).
- **The kernel holds the floor and never raises it by a rate.** `out.panic = inp.panicTarget` applies only when
  `panicTarget > 0` and PANIC reads under it. Otherwise `out.panic` is nil and nothing is written
  (`mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Hybrid.lua:98-101`).
- **The writer** reads PANIC and the record's `effects.panicTarget`, then sets `CS.PANIC` from `out.panic`
  (`mod/NutritionRevamp/common/media/lua/server/NR_Server_Writer.lua:277-278, 299`). The writer's own disclosure,
  line 23, says: "PANIC is written once a game minute and vanilla decays it between writes, up to 1.2556 under its
  floor at DayLength 1 (#3400)".
- **The decay.** Under the once-a-minute write, vanilla's decay takes about 0.179 a tick, about 1.12 a game minute
  (#3392, #3400). #3401 shows that a 6.5 floor drops under 6 in every gap. From a floor of 7, then, the readings
  should fall between about 5.75 and 7. Live read 6.28 and then 5.74 a few ticks apart at M1, and 5.74-6.28 across
  the six eats (Task 9's `steps[<label>_post].ack.stats.Panic`). That is the floor's own sawtooth, not a source of
  its own.

### The replay's `effects.panicTarget` splits the eats exactly as live PANIC does (inference)

This is the mod's own kernels, offline, on the same inputs. The ring carries neither `effects.panicTarget` nor
`fluids.dehydPct`, so these columns come from the replay's record, not from the live record.

| Eat | Replay `fluids.dehydPct` | Replay `panicTarget` | Live PANIC (ack) | Live BOREDOM add |
|---|---|---|---|---|
| M0, S0 (day 0) | 0.37, 0.49 | 0 | 0 | drift only |
| M1, S1 | 1.91, 1.72 | 7 | 5.93, 5.93 | 0 |
| M2, S2 | 1.72, 1.54 | 7 | 6.28, 5.93 | 0 |
| M3, S3 | 0.77, 0.78 | 0 | 0 | +8.38, +2.16 |
| M4, S4 | 1.93, 1.76 | 7 | 5.92, 5.75 | 0 |

M3 and S3 are the exception because x333 opened with `X_refill0` at age 71.28 (06:17 on day 3). The deficit dropped
from about 1.68 % to 1.48 % by 06:22, and day 3's eats ran at 0.77 %. On days 1, 2 and 4 the canteen ran dry
overnight, and the 10:30 refill of 0.9 L left the deficit above 1.5 % through the eats.

### Corroboration on the ring, with no setany anywhere near

Live BOREDOM goes to 0 and comes back as the replay's `panicTarget` switches. The replay crosses 1.5 % a few game
minutes after live does: its pool sits about 10 g wetter than live's before that point.

- **x331, s 1134-1137 (05:14-05:17, overnight):** live BOREDOM 27.27 → 0 at s 1134, and the replay's target goes
  0 → 7 at s 1137 (dehydPct 1.500).
- **x331, s 1735 (15:15):** the target goes 7 → 0, and live BOREDOM starts rising at s 1740.
- **x332, s 1066 (11:12):** the target goes 7 → 0, and BOREDOM rises from s 1071. This explains the day-2 blip
  (BOREDOM 0.41 and 1.32 at 11:30-12:00, with THIRST 0.33).
- **x332, s 1125 (12:11):** the target goes back 0 → 7, and BOREDOM reads 0 at 12:30.
- **x333, s 58 (06:22, after X_refill0):** the target goes 7 → 0, and BOREDOM rises from s 60.

The harness's `stats.setany` sets only BOREDOM and UNHAPPINESS (`testing/experiments/x33_monotony_lib.py:154-155`).
The overnight transitions above happen with no harness write at all. So the PANIC is not a setany side effect.

### The review's point: PANIC ~5.9 at S1, S2 and S4 while THIRST read 0.12-0.18

The review is right that PANIC does not co-occur with THIRST. That is expected, because **THIRST is not the band's
input**:

- **The band reads the pool-only deficit.** `f.dehydPct = K.fluids.dehydPct(f, w, 0)` (`NR_Server_Nutrients.lua:434`)
  is the value `K.effects.bands` reads (`NR_Kernel_Effects.lua:257`).
- **THIRST reads the view.** The thirst target is built from `f.viewPct = K.fluids.dehydPct(f, w, pendingG)`
  (`NR_Server_Nutrients.lua:440, 451`, ruling T1-1). The view counts the stomach's still-unabsorbed water as already
  drunk.

The S eats came about an hour after the 10:30 refill and about 30 minutes after the noon-to-13:30 drink of the M
stop. Most of the drink was still pending in the stomach then. So the view, and therefore THIRST, fell while the pool
stayed at or above 1.5 %:

| Eat | Pool `dehydPct` (band) | View `viewPct` (THIRST) |
|---|---|---|
| S1 | 1.72 | 0.72 (THIRST 0.18) |
| S2 | 1.54 | 0.51 |
| S4 | 1.76 | 0.72 |
| M3 | 0.77, under the 1.5 % edge | — (THIRST 0.18, PANIC 0) |

These are the replay record's values, as inference.

The ring carries no PANIC column: its stats are HUNGER, THIRST, FATIGUE, BOREDOM, UNHAPPINESS and
NICOTINE_WITHDRAWAL (`minute-ring-*.json` `stats`). So "throughout the day" was read through BOREDOM == 0, the
vanilla reset's own footprint.

**Every ring row on which the replay's `panicTarget` is 7 reads live BOREDOM exactly 0:** 598 of 598 (x331), 433 of
433 (x332) and 615 of 615 (x333). Of the rows with target 0, only 8, 20 and 14 read 0: the setany resets, plus the
few-minute lag at each edge.

| Session | Spans with target 7 |
|---|---|
| x331 | 05:17 → 15:15 on day 1 (age 22.3 on) |
| x332 | 06:20 → 11:12 and 12:11 → 14:32 on day 2 |
| x333 | 06:12 → 06:22 on day 3 (ended by X_refill0), and 05:15 → 15:20 on day 4 |

So the PANIC holds for hours, overnight and idle, from the dry-canteen pre-dawn until the afternoon drinks bring the
pool back under 1.5 %. It is not tied to the eat steps, to a time of day, or to the setany.

### Vanilla is the boredom reset, not the PANIC source

- **The reset.** `BodyDamage.UpdateBoredom @482-@509 L2037-L2038` (42.21 jar, re-read here):
  `stats.get(PANIC) > 5.0` → `stats.reset(BOREDOM)`. This matches #3015.
- **No vanilla thirst or hunger PANIC term was found.** A jar-wide literal grep for `PANIC` lists BodyDamage,
  IsoGameCharacter, IsoPlayer, CombatManager, SleepingEvent, the zombie-encounter states (CloseWindowState,
  FakeDeadAttackState, PlayerGetUpState) and the UI, audio and moodle classes. `Stats.class` is not in the list.
- **BodyDamage's PANIC writers** are the panic family: `IncreasePanic`, `IncreasePanicFloat`, `ReducePanic` and
  `UpdatePanicState`, which is zombie-count driven and never sets a level of its own (#3013, #3014, #3017).
- No zombie, combat or sleep event explains PANIC appearing exactly with the 1.5 % crossing, overnight and idle.
  (I did not walk every caller of IncreasePanic; the timing evidence carries the verdict.)

### Vanilla's boredom-to-unhappiness term (the review's second point, confirmed)

Read in `BodyDamage.UpdateBoredom @510-@575 L2042-L2043` (42.21 jar). The condition is
`getMoodles().getMoodleLevel(MoodleType.BORED) > 1` and `!isReading()`. When it holds, the method runs
`stats.add(UNHAPPINESS, ZomboidGlobals.unhappinessIncrease × BORED level × GameTime.getMultiplier())`.
So vanilla adds UNHAPPINESS at a rate proportional to the BORED moodle level, from level 2 up, except while the
character is reading.

The BORED level thresholds come from `MoodleStat.<clinit> @118-@133 L16`: `register(MoodleType.BORED, 0, 25, 50, 75,
90)`. That is #2369's BORED 25/50/75/90, re-read on 42.21 here. Level 2 therefore starts above 50 BOREDOM.
(I did not read the exact comparison in `Moodles.getMoodleLevel`, so whether it is > or ≥ is unread.)

Consistency with Task 9's holds: idle BOREDOM peaked at 27.3 and 29.2, which is level 1, so this term never fired and
UNHAPPINESS held flat. That matches the report. For the monotony floor design, this matters in two ways:

- A BOREDOM held above 50 would start vanilla's own UNHAPPINESS climb, on top of monotony's.
- While PANIC is above 5, BOREDOM is reset to 0, so this vanilla term is off for any dehydrated eater.

### What it means for the design

1. **Any mod PANIC floor above 5 zeroes BOREDOM vanilla-side**, every tick it holds. That covers:
   - dehydration (7);
   - sleep loss from iuS band 4 (7.0);
   - caffeine from band 3, 150 mg (5.625).

   The panic moodle's level 1 needs PANIC above 6 (#2369), so a floor that is meant to show the moodle always
   wipes boredom. The coupling is inherent to vanilla, not to the writer.
2. **The dehydration floor's own aim is only partly held.** "7 so that level 1 holds" still dips under 6 for 1-2
   ticks of every minute (5.74 read live). The panic moodle therefore flickers at level 0/1 each minute (#3401).
   That is a small mod-side defect in the floor's stated intent, separate from F-T9-1.
3. **Monotony's BOREDOM add (C-21)** is lost whenever the eater is ≥ 1.5 % dehydrated, or under any other PANIC > 5
   source.

### Fix options for A (each with its downside)

- **A1. Accept and document (my recommendation, for the coupling).** A panicked character is not bored: vanilla's
  rule is plausible physiology. Write it as a lessons rule: "a mod PANIC floor above 5 zeroes BOREDOM every tick;
  BOREDOM-side effects do not coexist with panic floors".
  - Downside: monotony's BOREDOM half silently does nothing in the commonest survival state (thirsty). Grading it
    live needs hydration under 1.5 %.
- **A2. Drop monotony's BOREDOM add and carry monotony on UNHAPPINESS alone (C-21's second branch).**
  - Downside: it loses the "bored of the same food" face of monotony. It is a design change and needs a ruling.
- **A3. Lower the dehydration `panicTarget` to 5 or below.**
  - Downside: PANIC 5 shows no moodle (level 1 is above 6), so the dehydration anxiety becomes invisible. It also
    contradicts the row's own reason for 7, and does nothing for caffeine or sleep-loss floors above 5.
- **A4. Fix the sawtooth (item 2): raise the floor to about 7.3, or write PANIC more often.**
  - Raising the floor keeps PANIC over 6 through a ~1.26 decay gap. Downside: it is a tuned number tied to
    DayLength and tick rate (#3400 gives 1.07-1.26 per gap).
  - Writing more often is per-tick work, and rule 6 forbids it without a hitching measurement.
- **A5. Harness, for the re-runs of row 13.** Keep the eater under 1.5 %: a larger canteen, or a refill before
  06:00, as day 3 had by accident.
  - Downside: the reading then covers only the hydrated case. The ≥ 1.5 % case is already known: BOREDOM is wiped.
  - Also fix F-T9-5 (map Panic and Stress in `mood_read`), and add `effects.panicTarget` and `fluids.dehydPct` to
    the ring paths, so the next run reads the cause directly instead of through the replay.

## B. The HUNGER drift after the 10:30 refill (F-T9-4)

### What the rows show

The replay was reproduced exactly on the scratch copy (x331 max 0.002267 on 3 rows; x332 0.004950 on 16; x333 0.003045
on 18). Every finding follows a large autodrop event: 900 g at x331 s 1460 and x332 s 1033; 797.7 + 102.3 g at x333
s 54/56; 667.8 + 232.2 g at x333 s 314/316; 900 g at x333 s 1755.

| x332 row | Live `stomach.liquid` | Replay `stomach.liquid` | Live HUNGER | Replay HUNGER | d |
|---|---|---|---|---|---|
| 1033 (10:39, dtM 1.59; live `fluids.autoDrop` 0.450) | 0 | 0 | 0.48436 | 0.48395 | −0.00041 (the standing offset) |
| 1034 | 900.0 | 826.7 | 0.41975 | 0.42470 | +0.00495 |
| 1035 | 862.5 | 792.2 | 0.42272 | 0.42745 | +0.00473 |
| 1040 | 668.0 | 613.6 | 0.43837 | 0.44195 | +0.00358 |

The x331 pair is the same shape. At s 1461 live reads 900.0 against the replay's 862.5, and the landing minute's
dtM is 0.80, so the lead is half as large and only 3 rows exceed tolerance.

Live's liquid at the first row after the landing is the whole 900 g, untouched. The replay's has already lost one
landing-minute of emptying (dtM 1.59 → 73 g; dtM 0.80 → 37.5 g), and it stays one minute behind live from there on.
The smaller stomach gives the replay less fullness, so its HUNGER sits higher. The difference decays as the stomach
empties, which matches the "within ~20 game minutes" pattern.

### The mechanism

- **The mod's order.** Within one player's minute the order is
  `{ "bus", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight", "writer", "store" }`
  (`mod/NutritionRevamp/common/media/lua/server/NR_Server_Minute.lua:18`).
- **Kinetics drains first.** It drains the stomach for the minute (`KIN.drain(record.stomach, dtH * 60)`,
  `NR_Server_Kinetics.lua:91-95`).
- **Then Nutrients lands the sip.** It lands the writer's previous-minute sip as liquid only after that drain:
  `if f.autoDrop > 0 then … K.stomach.ingestLiquid(stomach, NUT.waterVec); f.autoDrop = 0`
  (`NR_Server_Nutrients.lua:423-433`).
- **So the sip waits a full minute.** The sip folded by the writer at drain k (`NR_Server_Writer.lua:290-291`,
  "landed as water at the next minute (ruling 7)") enters the stomach late in drain k+1 and is not emptied until
  drain k+2.
- **The replay goes the other way.** `x33_monotony_lib.py:295-305` `autodrop_events` emits
  `{s, kind "drink", vec {water}}` at the ring row that first shows the autoDrop. The tool applies an event
  "before the drain of ring row s" (`tools/replay_live.py` docstring, lines 30-33). `ev_drink` → `IN.land` puts the
  water into the liquid lane (`NR_Server_Intake.lua:197-219`) before that drain's Kinetics, so the replay empties it
  one drain early.
- **Side effects of the IN.land path.** It also sets `IN.landed`, which suppresses the writer's sip fold that minute
  (line 198), and calls `IN.feed` and `addIngested`. The mod's autoDrop path does none of these.
- **The same function exists in x28-x32's libs** (`x28_steady_lib.py:198`, `x29_exercise_lib.py:218`,
  `x30_sleep_lib.py:280`, `x31_nicotine_lib.py:346`, `x32_nicotine_lib.py:361`). Their replays carry the same lead,
  sized by each autodrop. The 200 g drops of a normally watered run move HUNGER by roughly a fifth as much and stay
  under 0.002, which is why only the dry-canteen refills (≥ 0.67 L at once) showed it.

### The confirmation

The same three replays were re-run with every `label: "autodrop"` event replaced by
`{s, kind "setpath", path "fluids.autoDrop", value <autoDrop>}`, so that the replay's own Nutrients step lands the
water where the mod does. All other events and inputs were unchanged.

| Session | HUNGER max (drink event) | Over 0.002 | HUNGER max (setpath) | Over 0.002 |
|---|---|---|---|---|
| x331 | 0.002267 | 3 | 0.000622 | 0 |
| x332 | 0.004950 | 16 | 0.000553 | 0 |
| x333 | 0.003045 | 18 | 0.000663 | 0 |

es and L are unchanged (es max 0.00136, 0.00142, 0.00143; L 0). The dehydration state on the record did not drive the
miss: the satiety writer behaves the same in both runs, and only the landing minute differs. **Verdict: a lib/tool
limitation, not a mod behaviour the replay fails to model.**

### Fix options for B (each with its downside)

- **B1. In the libs, emit the autodrop as a record input (recommended).** `{s, kind "setpath", path
  "fluids.autoDrop", value}` at the row that shows it, exactly as the mod stores it.
  - Downside: `setpath` overwrites, not adds. It is exact while the replay's own writer folds no sip (its stand-in
    THIRST never sees vanilla's drink). A run whose replay writer does fold sips would lose them. A drink event
    keyed this way is also no longer a "drink" in the replay's eats log, so a grade that counts drinks there needs
    the new label.
  - The frozen libs (x28-x33) stay as run (§ 5: a driver is never edited after its run). The change goes into the
    next lib and into a regrade script that re-derives the events, named as a regrade.
- **B2. A tool-level `autodrop` event kind in `tools/replay_live.py`.** It would add to `fluids.autoDrop` before
  the drain (the mod's own landing path), with a test pinned on x332's s 1033-1049.
  - Downside: a tool change with its own review, and the tool's events grammar grows. It is cleaner than B1 for
    every later lib, though, because it adds rather than overwrites and documents the semantics in one place.
- **B3. Keep the drink event and mark the k+1..k+20 rows after a large autodrop as `between`.**
  - Downside: it hides a real mis-timing behind a skip, loses grading exactly where a large drink tests satiety,
    and leaves x28-x32's smaller errors in place.

## Cited and new evidence (for the controller)

- **Existing rows:**
  - #2369 (the PANIC thresholds);
  - #3013-#3015 and #3017 (the panic and boredom updaters);
  - #3392, #3400 and #3401 (the once-a-minute decay and the under-6 dips).
- **Jar, re-read on 42.21 here:** `BodyDamage.UpdateBoredom @482-@509 L2037-L2038`. A candidate C row for Task 9's
  claim 4.
- **Inference, scratch replay only, no artifact:**
  - the replay's `effects.panicTarget` and `fluids.dehydPct` per eat (the table in A);
  - the setpath re-run's HUNGER maxima (B).

  To cite either, a regrade has to land them as an artifact first (§ 4.1).
