# Plan 16: the pre-upload fixes — design

Date: 2026-10-18. Owner: Angus. Status: approved in brainstorming, section by section.

The brainstorm's evidence is in `.superpowers/sdd/plan-16-brainstorm/`:
- `offline-audit.md`
- `plan14-findings.md`
- `carries.md`
- `circadian.md`
- `circadian-player.md`
- `circadian-science.md`
- `circadian-systems.md`

## 0. The rules this plan serves
- **Nothing changes offline (Angus, 2026-10-18):** nothing about a character may change while its player is offline, at all. The character resumes exactly as it was left.
- **Subjective pacing follows vanilla; objective effects follow science** (Plan 15). Every deviation from either is a labelled game choice.
- **Rule 6:** no per-tick work; judged at 60 players.
- **The mod is unreleased:** no compatibility code. This plan ends at the staged copy Angus uploads.

## 1. Nothing changes offline

### 1.1 The freeze on return
- **One resume step.** It runs at the first touch of every sight (`S.get` / `S.load`), before any step. It shifts every world-age stamp and anchor in the record by the full offline gap. The list comes from the audit: L1, L3, and the stamps in the stomach, the nutrients, fluids, body, acute, drain, satiety, monotony, the writer and the nicotine anchor.
- **What the shift prevents.** No step integrates offline time. The current 60-minute clamp on a return's first step goes, and every test that pins that hour as intended is rewritten to the freeze (the audit lists them).
- **Absence against a stall.** An absence is keyed on a new player object (a real logout and login). A stall while the player stays online (a slow server, the fast-forwarded night) is never an absence. It is integrated in sub-steps no longer than the existing step bound, so booked sleep is not lost (audit L6, circadian-systems § 6).

### 1.2 The record day counts online time
- **The rule.** The body's day closes after 24 online game hours, from a record-day start anchor shifted by the gap. It no longer closes at the world's day boundary (audit L2).
- **What reads the day close:** every day-close rule.
  - the partition;
  - Strength training, detraining and regain;
  - the low-day count and refeeding;
  - the protein-energy grade;
  - the recent-intake window and its day buckets.
- **The limitation string** at `NR_Server_Nutrients.lua:51` is corrected.

### 1.3 The record is never pruned
- **The removal.** `NR.RecordKeepDays` is removed: the option, its sandbox and translation entries, the prune at the store's minute and at boot, its README row and its tests (audit L4).
- **The effect.** Records are kept for good, so neither a long absence nor long server downtime can reset a character.

### 1.4 A backup of the record on the character
- **What it is.** A compact copy of the player's record kept in the character's own modData. It is refreshed on each store save, mirrored to the owning client and validated on read, because a client `transmitModData` can overwrite the server copy (#1042).
- **Restoring a lost file.** A missing or corrupt store file restores from the copy exactly. This covers a corrupt file, a renamed server, a moved host and a deleted folder.
- **A hard kill.** When the store's record is newer than the world (stamps ahead of the clock, after a hard-kill rollback), the copy saved with the world wins. That prevents a double integration and re-eating already-landed food (audit L5).
- **Cost.**
  - Size: a few KB per character in the world save. Measure it, and keep the copy to the store's INPUTS.
  - Rule 6: the copy is written only at the store's save cadence, never per minute.

### 1.5 Out of scope, stated
These belong to the item or to vanilla, not to the mod's character, and are stated as limitations:
- carried food spoiling over the gap (vanilla `Food.updateAge`);
- vanilla Fitness regularity counting calendar time.

### 1.6 Tests
For each item above, a kernel or server-replay test logs a character out for at least 3 game days, logs it back in, and asserts that every record value and every written stat is unchanged. That covers:
- the stomach and the meal pool;
- the nutrients;
- fluids;
- the body;
- acute (caffeine, alcohol, hangover);
- sleep;
- monotony;
- the drain clocks;
- the record day;
- the body clock (§ 2);
- the written HUNGER, THIRST and FATIGUE.

It also covers:
- a stall integrated in sub-steps with no sleep lost;
- the backup's restore of a deleted file;
- the hard-kill case;
- a client-side wipe of the copy.

## 2. The body clock

### 2.1 Behaviour by server setting
- **Sleep off** (vanilla multiplayer's default: `SleepAllowed` and `SleepNeeded` not both true). There is no body rhythm. The hunger circadian factor is 1, the fatigue circadian term is 0 and the carry morning halving is off. This is a labelled game choice: the server has no sleep cycle, vanilla has no hunger rhythm, and S1273 is set aside on these servers.
- **Sleep on** (both options true, including the fast-forwarded night and accelerated-sleep mods). Each character carries a body-clock phase, `acute.bodyHour`, which is the only reader of all three consumers.
  - **It advances only by integrated online time**, so it freezes offline by § 1.1.
  - **Waking from a main sleep** of at least 4 h of booked sleep resets it to 07:00 body time. This is a labelled game choice, Angus's: in real bodies light, not sleep, sets the phase (circadian-science § 1), and the 4 h threshold is game pacing. Naps and the few-minute bouts of accelerated-sleep mods do not reset it.
  - **A player who never sleeps** runs on play time. The sleep debt already pushes them to sleep.
  - **A fresh record** starts the clock at the world hour.
  - **At the switch.** When sleep goes from off to on mid-game, the clock starts at the world hour. When it goes from on to off, the rhythm stops and the phase is kept.

### 2.2 The sleep settings are polled
- `SleepAllowed` and `SleepNeeded` are read in the existing per-minute options poll, two Java calls per server minute. They are no longer read only at `OnServerStarted`, so an admin's live change takes effect within a minute.
- The sleep-off test is `isServer() and not (allowed and needed)`, keeping single player's sleep correct for the next plan (circadian-systems § 2).

### 2.3 Fixes
- The `readHour` fallback becomes `(ageH + 7) mod 24`.
- The test host's `getTimeOfDay` offset is fixed (circadian-systems § 10).
- The world-hour read is hoisted to once per server minute.

### 2.4 Single player
Single player is the next plan. The mod's engine is gated on `isServer()` and finds players through `getOnlinePlayers()`, and neither works in single player. That plan ports the engine and adds single-player testing. This plan keeps § 2.2's test ready for it.

## 3. Long fasts

### 3.1 Research first
A science pass reads the following, and its rows are applied before the fix:
- Alpert 2005 in full: the fat-oxidation ceiling and its lean energy density;
- Elia and Henry on the protein share of energy against initial fat (this settles S1056);
- nitrogen excretion over a fast;
- the Keys 1950 body-composition series, if reachable (S0657, S0058).

### 3.2 The fix
- **The cap.** The deficit arm (`NR_Kernel_Partition.lua:61-80`) stops paying the overflow above the Alpert ceiling from lean. The Forbes split (S0054, S2241, S2243, S0104, S1910) governs the share, so a long fast takes about 15–22 % of its energy from lean, and fat can reach its essential floor.
- **The exact form** follows § 3.1. Options:
  - drop the ceiling from the deficit arm;
  - re-base it on a corrected lean energy density;
  - keep it with the protein-sparing term the research supports.
- **Fit discipline:** the fit rules apply (CLAUDE.md § 6: stability checks, constants at bounds reported).

### 3.3 Death follows the science
- Whatever state kills first on the science kills first.
- The default fast with water is expected to die of wet beriberi at about day 77, past the strikers' 46–73 days (S2231). That is stated, not tuned away.
- Report the outcomes for the default, heavy (Obese) and thin (Gaunt) bodies: cause and day.

### 3.4 Knock-on work
- **Plan 13's fitted Strength constants** are re-scored against their oracles on the new partition. A moved oracle is reported and re-fit only if it leaves its band.
- **The guide's fasting series** (S2d, SD, H2) are regenerated.

### 3.5 Fasting dehydration
- The residual creep is physiological after Plan 15's lean-scaled water base (plan14-findings § 2). There is no mod change.
- The stale comment at `tools/mod_guide_series.py:59-62` is corrected.

## 4. Eating and fullness

### 4.1 Server-side refusal at Overfull 4
- **The hook.** The mod installs a `serverStart` on `ISEatFoodAction` (vanilla defines none). At Overfull 4 it refuses through `netAction:forceComplete()`, the pattern of about 20 vanilla actions (carries § 2). It never wraps `new` (CLAUDE.md § 6).
- **What the player sees.** The player gets vanilla's `Tooltip_CantEatMore` message.
- **Guard.** A `serverStop` guard ensures a refused or cancelled eat never consumes the item.
- **Rulings.** This supersedes the Plan 15 Task 11 ruling that kept the menu refusal only (#3599). It is a deliberate exception to the intake's rule of always calling the original, stated in the code and the register.

### 4.2 Overfull 4 stays as is
A full meal followed at once by 500 mL holds Overfull 4 for about 3 minutes at the default day length, with mild nausea. That is kept: the sip-by-sip drink is real (carries § 1).

### 4.3 Drinks in the replay
- `tools/replay_live.py` spreads a drink over its action's duration as the game does (20 ms per unit of the action length, landed per sip).
- The "a drink lands whole in its minute" sentence is corrected in the spec, the README limitation, the writer's limitation and the guide.

### 4.4 Folic acid
Not tracked (Angus). The existing limitation stays.

## 5. Testing and release

### 5.1 Replay fidelity
- **The cold multiplier.** The harness ring records `body.coldMult` (a `cold` field), and `replay_live` feeds it as an exogenous input. This settles #3947 with a live run.
- **x332 and x263.** Their replay tests regain their full checks at HEAD through a replay-only overlay, `replay.LIQUID_SOLID_KCAL` (the old liquid rule), in the style of `HUNGER_CURVE_OFF`. A § 5 rule is added: a replay test broken by a later rule change is restored through a named replay-only overlay.

### 5.2 Harness additions
Each lands in its own commit with the balance check and the command table, plus the #2808 and #1235 update:
- a tooltip measure command: the client measures an item tooltip's height with the hide on and off, without hovering;
- the `cold` ring field;
- any offline-gap command the freeze session needs.

### 5.3 Live sessions
Each session stays under 10 minutes, and each driver passes a driver review first.
- **Water beside a meal.** A 667 kcal plate followed at once by 500 mL of water. Then x363's water, milk and solid sequence, with the `cold` field. It restores the guide's SE1 live lines and settles #3947.
- **Tooltip hide.** The hunger line is hidden with the option on and shown with it off.
- **Offline freeze.** A logout for at least 3 game days, then a rejoin, with every value unchanged. A hard-kill arm restores from the backup.
- **Body clock.** With sleep on, a full sleep resets the clock to body 07:00. With sleep off, no rhythm.
- **Fast-forwarded night.** A night with every player asleep books its sleep with no stall loss.
- **Server-side refusal.** A directly queued eat at Overfull 4 is refused, and the item is untouched.

### 5.4 Corrections
- x447's reading guide (`docs/reference/artifacts.md:5992`) is corrected: the mod booked 41.0 h asleep. The "under 0.27 h" figure was the unbroken run.
- A § 5 rule is added: a night driver polls `acute.winSleptH`, never the unbroken run.

### 5.5 Pre-upload checks
These run last, on the exact staged bytes, on fixture `two`, 42.21:
- **Boot A:** set one `[sandbox.NR]` value in the server's options file and read it back on the server, the admin and bob. This doubles as the clean release join.
- **Boot B:** a one-byte comment change in one Lua file on bob's client. Expect the checksum kick.

### 5.6 Close
- Re-stage `release/NutritionRevamp`.
- Rebuild and re-publish the player guide.
- The registers: supersede the rows these changes overturn, and mint the new mechanism and live rows.
- The whole-pass review, the fix wave, the gates, the push, CLAUDE.md and memory.
- Angus uploads, with `preview.png` his.

## 6. Game choices this plan adds (for spec § 10's list)
- No body rhythm on sleep-off servers.
- A full sleep (≥ 4 h) resets the body clock to 07:00.
- The fast's death is whatever the science gives first (beriberi about day 77 for the default body), not tuned to the strikers' range.

## 7. Verification
- Every § 1 freeze test.
- The § 5.3 sessions.
- The fasting outcomes by body.
- The Strength oracles re-scored.
- Rule 6 (Java calls per player-minute, against Plan 15's 70/68/76).
- The full pytest, read from its own summary.
- Every CLAUDE.md § 3 gate.
