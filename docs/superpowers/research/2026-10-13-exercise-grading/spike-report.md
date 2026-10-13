# C-2 spike report: grading Fitness exercise billing by exercise type

Model: claude-opus-5-5 · 2026-10-13 · read-only research; jar read is the installed one (42.21, `4a0e9546ec` per CLAUDE.md § 2); nothing booted.

## 1. The jar: can the server read the exercise type?

**Not off the Java objects. But yes off the server's own Lua action instance, through a one-time wrapper of `ISFitnessAction.serverStart`.**

### What does not work
- `getFitness():getCurrentExe()` answers a `Fitness$FitnessExercise`. Its only member is the constructor `<init>(KahluaTableImpl)`, and its four fields (`type`, `metabolics`, `stiffnessInc`, `xpModifier`) are package-private with no getter (`Fitness$FitnessExercise.<init> @0–@78 L57–L73`, re-read today; register #2180). Indexing `.type` raised `attempted index: type of non-table` live (#2901, x141c).
- The reflective field readers `getClassField` and `getClassFieldVal` throw `Not in debug` unless `Core.debug` is set (#2736). A production server is not `-debug`, so this route is dead.
- `Fitness` declares no getter for the current type or for its exercise map. It has only per-type queries (`getRegularity(String)`, `getCurrentExeStiffnessTimer(String)`, `getCurrentExeStiffnessInc(String)`) and `getRegularityMap()` (member list re-read today).
- The server's character-action stack is empty during a set (#2878). The current action cannot be read.
- The thermoregulator is no help either. On the server, `updateMetabolicRate` applies the flat `Metabolics.Fitness` 6.0 while an exercise is current (#2634). The per-exercise target (`FitnessHeavy` 9.0) arrives only through `ISFitnessAction:update`'s `setMetabolicTarget`, which runs on the client (#2876 read 6.0 on the client only). The server's rate is also a slow lag: the x29 gate read squats at most 2.0 and burpees at most 3.0 billed, and a 60 min burpee chain reached at most 5.33 engine MET. So the engine rate cannot tell exercises apart.

### What works: the server-side Lua action instance
New readings, taken today. They are not yet in the register.

1. **The client sends the type.** `NetTimedAction.set(IsoPlayer, KahluaTable) @58–@139 L44–L51` reads the parameter names of the action class's `new` closure (`metatable.rawget('new')`, then `LuaClosure.prototype`, `numParams` and `locvars[1..numParams-1]`). It copies the instance's field of each name into `actionArgs`. For `ISFitnessAction:new(character, exercise, timeToExe, exeData, exeDataType)`, that copy includes the string `exeDataType`.
2. **The server rebuilds the action.** `NetTimedAction.parse` calls `<type>.new(classTable, args...)` and stores the result as `action` (#2932). On the server, `ISFitnessAction.new` therefore sets `o.exeDataType` to the type string. It also calls `fitness:setCurrentExercise(exeDataType)`; the shipped Lua is `ISFitnessAction.lua:204–225`.
3. **The server calls `serverStart` from the class table.** `NetTimedAction.start @0–@57 L102–L110` fetches `action.rawget('serverStart')` and calls it with the action. PZ's `KahluaTableImpl.rawget @92–@122 L126–L127` falls through to the metatable's `rawget` when the key is absent. The instance's metatable is `ISFitnessAction` (`ISBaseTimedAction:new` does `setmetatable(o, self)`), so the function called is whatever sits in `ISFitnessAction.serverStart` at that moment.
4. **It runs live.** `ISFitnessAction:serverStart` (`ISFitnessAction.lua:128–151`; #2186) is what arms the server's rep loop. Its effects ran on a live dedicated server: the server-side regularity rose and the per-rep `AddXP` events fired (#2879, #2900). So serverStart runs server-side in practice.

**The route.** In a shared or server file, at file scope and installed once (so the #2835 re-install cycle cannot form), replace `ISFitnessAction.serverStart` with a wrapper:
- the wrapper calls the original first, then reads `self.exeDataType` and `self.character:getUsername()`;
- it stores the type in a mod table keyed by username;
- it clears that entry on `serverStop`, by wrapping that the same way;
- the billing still gates on the existing exercise flag `getCurrentExe() ~= nil`, so a stale entry never bills (the flag clears on the set's last minute, #3680).

**Cost:** one Lua call per set, and no per-tick work. Per minute it is one table read beside the flag read Metabolism already does. Rule 6 is not touched.

**Trust:** the type is client-asserted, but it is the same string the engine itself uses for the set's reps and XP (`setCurrentExercise(exeDataType)`). So the mod trusts nothing vanilla does not already trust. Validate the string against a known key list, and let an unknown or modded type fall back:
- read `FitnessExercises.exercisesType[type].metabolics:getMet()` (`Metabolics` is exposed and has `getMet`; #2631, #2248), mapped to a Compendium value per class;
- or bill the flat Fitness class.

**Hard hazard (new): never wrap `ISFitnessAction.new`.** The client copies the action's arguments by the parameter names of the `new` closure it finds (reading 1 above). A `function(self, ...)` wrapper has `numParams` 1, so the set would send no arguments. The server's `new` would then get a nil character, and Fitness would break for every player. Wrap only `serverStart` and `serverStop`.

**Rejected alternatives**
- **Infer the type from regularity.** Diff `getRegularity(t)` across the seven types each minute. That is seven Java calls per exercising player-minute, and a capped or decaying regularity does not move, so this is fragile.
- **A client command carrying the type.** It adds a client file and a send per set. Its trust is weaker, because the claim is detached from the server's own action. It is strictly worse than the wrapper, which reads the value the server already holds.

**Bonus:** the same table gives `NR_Server_Training` the real exercise key. That would replace the Strength-grant inference (`exeKey`, the third limitation line).

**Not yet measured.** No live run has read a wrapper's record. A short experiment is needed before the claim is settled: one set of each type, reading the wrapper's table and the flag on the server. It also needs the register rows for readings 1–3 minted, with grade C and a `jar:` pointer each.

## 2. The vanilla exercise list (42.21 install)

The source is `media/lua/shared/Definitions/FitnessExercises.lua`. The engine MET values are from #2632; the rep periods are from `ISFitnessAction:serverStart` (#2186).

| type | stiffness | item | `metabolics` (engine MET) | rep period |
|---|---|---|---|---|
| squats | legs | — | Fitness 6.0 | 3000 ms |
| pushups | arms,chest | — | Fitness 6.0 | 1300 ms |
| situp | abs | — | Fitness 6.0 | 1300 ms |
| burpees | legs,arms,chest | — | FitnessHeavy 9.0 | 2400 ms |
| barbellcurl | arms,chest | Base.BarBell | FitnessHeavy 9.0 | 2200 ms |
| dumbbellpress | arms | Base.DumbBell | FitnessHeavy 9.0 | 1500 ms |
| bicepscurl | arms | Base.DumbBell | FitnessHeavy 9.0 | 1900 ms |

On the server, every one of these runs the thermoregulator at the flat 6.0 floor (#2634).

## 3. The activity tables

**Source.** The 2024 Adult Compendium is reachable. I read it from the Compendium's own Conditioning Exercise page (pacompendium.com/adult-compendium/conditioning-exercise/, the "2024 Adult Compendium of Physical Activities" pages) on 2026-10-13. The record is Herrmann SD et al 2024, J Sport Health Sci 13:6–12, doi:10.1016/j.jshs.2023.10.010, pmid:38242596. I re-resolved it on Crossref today: the title, first author Herrmann, the journal, 13:6-12 and 2024 all matched.

**Existing rows.** `science.tsv` holds S0018–S0043 from the same record. None of them is a conditioning-exercise code; `K.energy.COMPENDIUM.Fitness` says "no resistance-exercise row". The nine new codes are filed as S1895–S1903 in `c2-rows.tsv`, all `settled` and read off the source.

| exercise | proposed code | Compendium description | MET | match |
|---|---|---|---|---|
| squats | 02056 (S1898) | Body weight resistance exercises (e.g., squat, lunge, push-up, crunch), general | 3.0 | named; intensity approximate (high-intensity 02057 is 6.5, S1899) |
| pushups | 02022 (S1896) | Calisthenics (e.g., pushups, sit ups, pull-ups, lunges), moderate effort | 3.8 | named; intensity approximate (vigorous 02020 is 7.5) |
| situp | 02022 (S1896) | as above | 3.8 | named; light 02024 (curl ups, crunches, plank) is 2.8, S1897 |
| burpees | 02020 (S1895) | Calisthenics (e.g., pushups, sit ups, pull-ups, jumping jacks, burpees, battling ropes), vigorous effort | 7.5 | named and vigorous; HIIT burpees 02214 is 11.0 (S1903), for interval protocols, not a paced set |
| barbellcurl | 02054 (S1902) | Resistance (weight) training, multiple exercises, 8-15 reps at varied resistance | 3.5 | approximate: there is no curl code; vigorous body building 02050 is 6.0 (S1900) |
| dumbbellpress | 02054 (S1902) | as above | 3.5 | approximate, as above |
| bicepscurl | 02054 (S1902) | as above | 3.5 | approximate, as above |

**How the table compares to the engine.** The Compendium reverses the engine's ranking for the weights. The engine bills curls at 9.0, while the Compendium puts free-weight work at 3.5 to 6.0, and a single-arm curl is the low end. Burpees are the only exercise the Compendium places as high as the engine's FitnessHeavy class.

**Which intensity to pick is a game choice.** It is either general or moderate (as proposed) or vigorous, and the rows give both ends. The game's sets run until the ENDURANCE moodle passes level 2, which argues for the upper code. The paced rep periods (a squat every 3 s) argue for the lower one. One option is a ruling that bills the general or moderate code, and switches to the vigorous code above an endurance level. That would be a new mechanism and is unevidenced as a switch.

## 4. The vigorous bar: should acute suppression grade with MET?

**Short answer: no.** The rows do not support a continuous MET grading. They do support two narrower changes.

**What the rows say**
- **The aerobic threshold is relative, not absolute.**
  - S1305 (Dorling 2018, TXT): suppression appears at or above 60 % of peak VO2, and after resistance work it is "less marked and not observed consistently".
  - S1302 (King 2010, RCT): brisk walking at 7.0 km/h did not move appetite in fit men (VO2max 55.9). (Corrected at the Plan 11h citation review: 7.0 km/h falls in S0025's 6.4-7.1 km/h band, 5.5 MET, under the 6.0 bar, so this walk does not test the bar; the conclusion rests on S1305's relative threshold and the resistance rows.)
  - The 6.0 bar is a fair stand-in for 60 % of an average untrained VO2max, but it is a proxy, not the rule the evidence states.
- **The size grades only weakly with intensity, and the effect is short.**
  - S1500 (pooled): suppression immediately after, and none at 30–90 min.
  - S1304 and S1501: HIIT/SIT beat MICT at 30–90 min only for SIT (−10.4 mm); the HIIT subgroup was null.
  - S1502: −33 % during the bout and nothing after.
  - That is a step at a threshold, plus a bigger and longer tail only for sprint intervals. It is not a dose-response in MET.
- **Resistance suppression does not grade with load.**
  - S1508 (Liu 2023, RCT): 4×8 at 85 % 8RM and 4×15 at 45 % 8RM suppressed hunger alike, against control, immediately after.
  - S1509 (McCarthy 2024): 30 % and 90 % 1RM to fatigue both suppressed appetite at 0 min, with nothing at 60–120 min.
  - S1301: suppressed during resistance work, too.
  - So a set's suppression should not scale with that set's MET.

**What this supports**
1. **Decouple a Fitness set from the 6.0 bar.** Today `W.vigorous` reaches the resistance kind for a set only through `met >= 6.0`, which is true only because C-17 bills every set at 6.0. Under graded billing, squats (3.0), push-ups (3.8) and curls (3.5) would fall under the bar and lose all suppression. Evidence S1508 and S1509 say low-load resistance work still suppresses. So `ctx.exercising` should yield `true, "resistance"` before the MET test. The weight stays the 0.5 game choice that S1305 motivates.
2. **Keep the binary bar for aerobic work.** If anything, a later candidate could make the bar relative to the character's aerobic capacity (60 % of their VO2max in MET), as S1305 states it. That is a separate mechanism candidate, not part of C-2.
3. **Optionally, bill burpees as the aerobic kind** (weight 1). They are the one exercise the Compendium files as vigorous calisthenics or HIIT (S1895, S1903). This is a game choice resting on S1304 and S1501's interval reading; the evidence is thin (the HIIT subgroup is null).

## Recommended design sketch

1. **Server wrapper** (`NR_Server_Training` or a small new server file). At file scope and installed once:
   - `ISFitnessAction.serverStart` = call the original, then `TRN.exeType[username] = self.exeDataType` when it is a known string;
   - `serverStop` clears the entry the same way;
   - never wrap `new`.
2. **Kernel table.** `K.energy.EXERCISE_MET = { squats = 3.0 (S1898), pushups = 3.8 (S1896), situp = 3.8 (S1896), burpees = 7.5 (S1895), barbellcurl = 3.5 (S1902), dumbbellpress = 3.5 (S1902), bicepscurl = 3.5 (S1902) }`. Each intensity pick is named as a game choice over its row pair.
3. **Billing.** `MET.readBilled` / `K.energy.billClass`: while the flag is set, bill `EXERCISE_MET[type]` when the type is known. Otherwise bill the flat Fitness class (6.0, today's behaviour) and count the fallback in a stat. The training sample keeps the engine's `CLASS_MET`.
4. **`W.vigorous`.** A minute with the flag set returns `true, "resistance"` regardless of the billed MET (S1508, S1509, S1301). Aerobic work keeps the 6.0 bar. Burpees as aerobic is an option for Angus.
5. **Training.** `exeKey` reads `TRN.exeType[username]` first, and the Strength-grant inference becomes the fallback.
6. **Golden trace.** It moves where a set's billed MET moves. Re-record it under the named cause in the task's own commit.
7. **Live acceptance.** One set of each of the seven types. On the server, read the wrapper table, the flag and the billed MET each minute, and check the fallback stat at 0. It runs as one session, under § 5.

## Risks
- **The serverStart wrapper is unproven live** (readings 1–3 are C-only). The mechanism is solid: the same netAction pattern carries the mod's eat wrapper. But a run must show the wrapper's record before it ships.
- **Another mod that wraps `ISFitnessAction.new`** with varargs breaks vanilla Fitness itself. Worth a lessons rule. Another mod that wraps `serverStart` and re-installs it at a boot event can form the #2835 cycle.
- **Lower billing for most exercises.** Squats drop from 6.0 to 3.0 and curls from 6.0 to 3.5. That lowers exercise kcal, sweat, glycogen draw and the exercise lag L. Any fitted constant tuned against the flat 6.0 will move: the x29 lag rows, and the replays that used burpee bouts, which bill 7.5 instead of 6.0.
- **Exercise-to-code mapping and intensity choice are approximate.** There is no curl code at all, and the general/moderate versus vigorous split is a game choice.
- **The type is client-asserted** (same trust as vanilla). Modded exercises fall back to the flat class or a mapped engine value.
- **The vigorous change is a behaviour change.** Every set minute stays resistance-vigorous, as today, but by the flag instead of by the bar, so the outcome is the same for sets. Burpees as aerobic would raise their suppression and is optional.
