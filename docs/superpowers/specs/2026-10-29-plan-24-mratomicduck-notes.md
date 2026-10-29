# Plan 24 Task 14: notes from MrAtomicDuck's beginner and combat videos

Angus (2026-10-29): "There is some youtube videos by MrAtomicDuck about beginner and combat tips, see if you can get the transcripts and make some notes about it." These notes are design input for the survival agent's instincts (`testing/agent/base/planner/`) and the LLM goal source's system prompt. Every note is the presenter's claim (or, where marked, a machine summary of the video), never register evidence: no claim tag, no row. Where the register or the Plan 24 jar reads already say something on the same mechanic, the row id is named beside the note.

## The videos

All are on the channel MrAtomicDuck (`UC6BOGC2EEBgjp4vS_S7PQ2g`), its owner name read off each watch page. Dates are the watch pages' `publishDate`; lengths their `lengthSeconds`.

### Chosen (four)

| # | Video | Uploaded | Length | Build | Why chosen |
|---|---|---|---|---|---|
| A | [Project Zomboid Beginner's Guide To Combat & Stealth! Tips & Tricks On How To Avoid & Fight Zombies!](https://www.youtube.com/watch?v=ob_OeR-nb6c) | 2022-01-15 | 11:39 | 41 (its tags say `project zomboid build 41`) | the only full combat guide on the channel |
| B | [Surviving Your First Week In Build 42 - THE FULL SERIES! A New Player Guide To Project Zomboid!](https://www.youtube.com/watch?v=if_QfqNo8DE) | 2025-01-29 | 2:33:04 | 42 | the Build 42 beginner guide (a supercut of the seven "Day" episodes) |
| C | [50+ Tips & Tricks For Build 42! Project Zomboid Guide To Things You NEED To Know About This Update!](https://www.youtube.com/watch?v=Dxr7sHJR8N4) | 2025-01-16 | 31:25 | 42 | Build 42's changes, muscle strain and darkness among them |
| D | [Must Know Muscle Strain Tips! Project Zomboid Build 42 Tips Done Quick!](https://www.youtube.com/watch?v=i-5KweicstE) | 2024-12-24 | 1:18 | 42 | Build 42's combat cost, which A predates |

Build 41 against 42: A is a Build 41 video. Where a note from A bears on a mechanic Build 42 may have changed (the swing, the shove, zombie hearing and sight), that the mechanic is unchanged is unverified unless a row named beside it was read on the 42 jar.

### Candidates not chosen

| Video | Uploaded | Length | Build | Why not |
|---|---|---|---|---|
| [Get Better At Combat in Project Zomboid! Tips Done Quick!](https://www.youtube.com/watch?v=CJT4ODq1RXY) | 2022-11-03 | 0:43 | 41 | 43 s; its description says only that combat "takes time" |
| [Surviving Your First Week In Build 42 - DAY ONE!](https://www.youtube.com/watch?v=YTf3qnqc0mM) | 2024-12-22 | 30:37 | 42 | contained in B |
| [Use This Tip When Looting At Night In Build 42!](https://www.youtube.com/watch?v=6SQlqRqFYWs) | 2024-12-28 | 1:00 | 42 | its description names no tip ("a handy trick you can use when exploring the map at night"); cited once below |
| [101 Project Zomboid Tips For New & Experienced Players!](https://www.youtube.com/watch?v=KGllwEXihwc) | 2023-11-19 | 27:10 | 41 | one chapter "101 Tips!", nothing finer readable |
| [Project Zomboid Melee Weapons Guide!](https://www.youtube.com/watch?v=fpHvBdh8to4) | 2022-06-01 | 16:17 | 41 | weapon classes and occupations; cited once below |
| [Project Zomboid New Player Tips! (Build 41)](https://www.youtube.com/watch?v=kRiyAlC9mHA) | 2021-04-18 | 8:32 | 41 | superseded by B |
| [Tips For Surviving Day One On Project Zomboid!](https://www.youtube.com/watch?v=y_J-uyuPA2E) | 2021-08-11 | 8:57 | 41 | superseded by B |
| [Preparing For The Long Term In Build 42 - THE FULL SERIES](https://www.youtube.com/watch?v=xxGg_96pq10) | listed "1y ago" | not read | 42 | long-term base building, past the agent's first days |

The candidates were found by the channel's own search page (queries `combat`, `beginner`, `guide`, `tips`) after web searches returned only other creators' guides (CzechStag, British__Badger and Sunny Survival's are not MrAtomicDuck's, read through YouTube's oEmbed).

### Transcript routes and completeness

**No transcript was obtained for any video.** The routes tried, in the brief's order:

1. Public transcript services through `WebFetch`: youtubetotranscript.com (HTTP 403), youtubetranscript.com (its XML says "YouTube is currently blocking us from fetching subtitles"), youtube-transcript.io, tactiq.io and tubetranscript.com (each a client-side page with no transcript text in it), summarize.tech (HTTP 503), glasp.co (HTTP 403), notegpt.io (404). The watch pages list an English auto-generated caption track, but its `timedtext` URL returns 404 to a plain fetch, and YouTube's own transcript panel request returned `FAILED_PRECONDITION`; a further attempt through another client was refused by the session's permission classifier and not pursued.
2. `yt-dlp`: not installed on this host (`where yt-dlp` finds nothing); nothing was installed.
3. The fallback, used for every note below: each watch page's description, its chapter list (the creator's own titles and start times) and YouTube's "AI-generated video summary" paragraph on the page, read from the public watch page. The channel links no written guide (the descriptions link only the VOD channel, Twitch, Discord, Patreon, the mod collection and a store).

So every note is at the level of a chapter title or a one-paragraph machine summary: it says what a section is about and the claim its title makes, never the presenter's detailed advice. A timestamp is the chapter's start. Completeness per video: A five chapters and a summary; B 32 chapters and a summary; C 34 chapters and a summary; D four chapters, no summary. One more source is marked where used: a web search engine's description of A ("zombie detection, stealth, line of sight, pulling small groups, backpedaling, shoving, stomping, using obstacles, and escaping bad fights"), which the watch page does not carry and which may be the search engine's own inference; it is the weakest source here.

### What the notes are compared against

The planner's rules as of HEAD `12d20238`: `survive.py`'s and `policies.py`'s module docstrings and the design's § 6 (items 9-16, rulings P24-G to P24-R). P24-N, P24-O and P24-P (the stance opens the fight, no sprint, the bandage under a far threat) are ruled but not yet built (Task 12): `policies.Flee` still sprints within `SPRINT_R` and on a `many` flee. A note marked **agrees with** matches a current or ruled rule, **contradicts** goes against one, **new** has no rule.

## 1. Zombies' behaviour

- **Aggro is learnable and managed by line of sight.** A 1:00 "Understanding zombie aggro"; the summary: "explaining how to utilize line of sight to manage hordes effectively". *For the agent:* **new**. Today the threat branch reacts to distance alone (DANGER_R 6, the hold to DISENGAGE_R 10, `many` on four listed within LISTED_R 12) and the flee steers by distance-weighted away vectors; nothing breaks line of sight on purpose. A flee leg that puts a wall or a building corner between the character and the group (the map already has `line_to`) would act on this. Register: turning does not change the cell's zombie list (#4302), so the agent's frames see every zombie whatever line of sight it has; the claim is about the zombies' sight of the player, which no row reads.
- **Build 42 changed zombie behaviour in Rosewood.** B's summary: "changes to zombie behavior in Rosewood"; C 25:24 "Zombie Settings". *For the agent:* **new**, nothing to build from a title; the chapters do not say what changed.
- **Darkness matters in Build 42.** C 4:19 "Darkness"; the night-looting short (6SQlqRqFYWs) offers "a handy trick you can use when exploring the map at night". *For the agent:* bears on the night branch (shelter and sleep when tired or late, LATE_HOUR 22 to DAWN_HOUR 6). **Agrees with** the night's shelter at late hours as far as a title says; what the darkness does (to the player's sight, to the zombies') is not in the chapters, and no row reads it.
- **The drag-down** is not in any chapter title; the register's #4290 (three or more attackers within 0.9 tiles turn the next hit into the kill) is what the planner's P24-A (h) guard rests on.

## 2. Combat

- **Fight or flight is a decision taken before engaging.** A 2:58 "Fight or flight decision". *For the agent:* **agrees with** the threat branch's hysteresis (flee unarmed, more than MAX_FIGHT 2, under FLEE_HEALTH 40, a pair under 60 or wounded, `many` on four listed). The title gives no thresholds to compare.
- **Effective combat techniques** (A 4:29), which the search engine's description lists as backpedalling, shoving, stomping and using obstacles (the weakest source; Build 41).
  - *Backpedalling.* **Agrees with** P24-N (the backpedal in the stance whenever the target is inside KEEP_R 2.5) and Angus's own direction (§ 6); contradicts today's built standing leg (E6: 8 of 11 stance legs stood with a zero vector), which Task 12 replaces.
  - *The shove.* **New.** The planner never shoves. The jar reads 2 § 1 found the shove is the attack call with `isDoShove()` true (the melee key's flag), and the register has its Strength ladder (#2136) and its muscle-strain cost (#2140). A shove to knock one zombie back while a second closes, or to make room inside KEEP_R, would be a new PZA action.
  - *The stomp.* **New.** A stomp is the `isAimAtFloor() && isDoShove()` branch (#2196), its damage `0.7-1.0 + 0.2 × Strength` before shoes, halved and worse by the TIRED moodle (#2280). The planner has no read of a downed zombie and no stomp; the frames would need a zombie's on-the-ground state first.
  - *Obstacles.* **New** outside a shelter. The only obstacle fight today is the sheltered door fight (P23-AG: a doorway kill from inside). A fence or a doorway between the character and one or two zombies, fought across, is not a rule.
- **Muscle strain is Build 42's combat cost, and it is managed.** C 5:18 "Muscle Strain", 5:57 "Building Muscle Strain", 6:23 "Additional Layers To Muscle Strain", 7:15 "Combating Muscle Strain"; D 0:00 "Understanding muscle strain", 0:14 "Utilizing the environment", 0:38 "Weapon selection and skills", 1:01 "Using pain management"; B's and C's summaries both name muscle strain's "impact ... on combat". *For the agent:* **new**. The standing fight swings until STAND_MAX_S 20 s pass with no fall of the target's health, and nothing reads the arms' strain. The register: muscle strain is `BodyPart.stiffness` per part, public getters (#2141), every combat strain term scaled by `(15 − Strength) / 10` (#2140). A frame field for the arms' stiffness, and a fight that stops taking new targets (or prefers a flee to the next one) past a level, would act on it; D's "utilizing the environment" (likely the obstacle or the door) and "pain management" (painkillers) are second steps.
- **Weapon choice matters, with Build 42 crafted weapons and the class perks.** D 0:38 "Weapon selection and skills"; C 29:17 "Crafting Weapons"; the Build 41 melee guide's chapters (blunt 1:00, spear 9:12, axe 12:40) and its summary on "weapon durability, damage mechanics". *For the agent:* the loot wants `weapon` and the fight reads `world.weapon` None as unarmed; nothing ranks two weapons or reads durability. **New**: a weapon rank (the item data's damage, reach and condition) in the loot's pick and the hand's choice.
- **Firearms** (C 19:07 "Shotguns", 20:12 "Shooting Tips"; the separate guns guides). *For the agent:* out of scope; the agent fights melee only, and a shot's noise draws a group, which the planner's group rules already fear.
- **The "Armed Confrontations" and "Final Combat" sections** of B (1:02:00, 2:24:20) are play, not chapters of advice; "Escape and Recovery" (B 1:09:00) follows the first. *For the agent:* **agrees with** the flee-then-care order (the care branch after the threat; P24-P lets it bandage under a far threat).

## 3. Movement and stamina

- **Stamina is managed by walking, jogging and crouching rather than running everywhere.** A's summary: "optimize stamina usage by balancing walking, jogging, and tactical crouching". *For the agent:* **agrees with** P24-O (Angus after E6: never sprint, "running is plenty"), not yet built; today a flee sprints within SPRINT_R and on a `many` flee while endurance reads above SPRINT_END. The register backs walking over running: walking drains no endurance below heavy-load level 3 (#2256), running drains at `runningEnduranceReduce` 5.2e-5 and sprinting at 4.55e-4, nearly nine times as much (#2251). On crouching the register differs from the summary's wording: sneaking multiplies every drain arm by 1.5 and no regeneration arm (#2254), so (an inference from #2254 and #2256) a crouch saves stamina only by keeping the pace at a walk; its gain is stealth, not stamina. **New** for the planner: a sneak gait for the goal's walks near listed zombies (none today).
- **A vault is a risk** is not in these chapters; the register has it (#4296: a fence begun at a run or a sprint rolls a fall, none at a walk), and the planner already never steers over a hoppable edge and climbs at a walk (P24-G 4).

## 4. First aid

- No chapter of the four videos is on wounds or bandaging; C 30:08 "Cleaning" is the nearest (Build 42's washing). *For the agent:* the care branch (P24-G 2, P24-P, P24-R) rests on the jar reads (#4298, #4299), not on these videos; nothing here contradicts or adds to it.

## 5. Looting and the first day

- **The first day's order: set up, look around, loot the local area, then manage what you hold.** B 0:49 "Character Setup", 6:25 "First Steps", 9:39 "Local Area Looting", 14:06 "Resource Management", 20:32 "Surviving Scares", 26:58 "Ending Day One". *For the agent:* **agrees with** the goal source's order (the scan on a fresh session, then `LootBuilding` by STOCK_WANTS water, food, bandage, weapon, the night's shelter); "Surviving Scares" before "Ending Day One" matches the threat branch pre-empting the goal.
- **Day two takes a weapon source (the fire station) and picks a new base.** B 35:02 "Fire Station Looting", 40:20 "New Base Selection", 50:20 "Base Securing". *For the agent:* **new**. The goal source loots the nearest building and shelters in the nearest; no goal travels to a named building type for a want (a fire station for an axe, a police station for weapons, B 57:28) and no base is chosen and secured. A goal to the LLM source rather than an instinct.
- **Water is secured early and then solved for the long term.** B 1:58:28 "Securing Water", 2:18:52 "Water Solutions"; C 26:12 "Water Pumps". *For the agent:* **agrees with** the water chain (P24-G 3, Angus's § 6 item 13: a container filled at a sink or a toilet); the long-term solution (collectors, the shut-off) is past the agent's horizon.
- **Bags and keys.** C 0:54 "Backpack Keys"; B's summary "key management". *For the agent:* **new**, minor: the loot takes one use at a time and never a bag; a bag would raise `load.max` and so the loot's reach (LOOT_MAX_LEVEL 1).
- **Build 42 maps in the literature show places.** C 2:36 "Readable Literature" (the summary: "new literature for location discovery"). *For the agent:* **new**, a goal-source idea only.
- **Nutrition and weight.** C 27:06 "Nutrition", 27:32 "Weight Loss". *For the agent:* the need branch eats the most perishable first at the first moodle (HUNGER_T 0.15); the chapter titles add nothing to compare.

## 6. The night, sleep and the long term

- **The helicopter event is a day-seven danger.** B 2:30:28 "The Helicopter Event"; the Build 41 new-player video's 3:34 "Helicopter Event". *For the agent:* **new**. Nothing in the planner reads the event; a session long enough to meet it (the agent's chains die before game day two) would want a rule (stay inside while it passes is the usual advice, not read here).
- **Pillows, generators, survivor houses** (C 9:10, 24:09, 28:34): past the agent's horizon.

## 7. The five changes most worth building

The ranking weighs what the videos claim against what the agent's deaths and Angus's metric (P24-Q: zombies killed) say the agent lacks. Every claim behind them is a chapter title or a summary, so each change is a hypothesis for a live read, never a rule the videos prove.

1. **Read the arms' muscle strain and let it end the standing fight.** Claim: C 5:18-9:10 and D (muscle strain is Build 42's combat cost, managed by weapon, environment and painkillers); register #2140, #2141. Today the stance fight swings until STAND_MAX_S with nothing tracking strain; what strain does to a swing is the presenter's claim, read by no row here. Change: the frame's `me` carries the arms' `getStiffness`, and past a level the fight takes no new target and the goal source rests. Live read: kills per swing against the arms' stiffness over a session's fights; the change pays if the swings per kill rise with stiffness.
2. **Build P24-O's no-sprint rule, and walk where nothing is listed.** Claim: A's summary (balance walking and jogging for stamina); register #2251, #2256 (a sprint drains nearly nine times a run; a walk nothing below heavy-load 3); Angus after E6. Change: Task 12's no-sprint, plus the goal's walks at a walk with no zombie listed. Live read: the frame's endurance at each fight's start and the kills per fight against it, and no `VaultSprintFallLanded` trip in the session.
3. **The shove (and later the stomp) as a stance action.** Claim: A 4:29 as the search engine lists it (shoving, stomping; Build 41, the weakest source); the jar reads 2 § 1 (the shove is the attack with `isDoShove`), #2136, #2196. Change: a PZA `shove {targetId}` from the stance when a second zombie is inside KEEP_R while the first is in reach, and a stomp once the frames carry a zombie's knocked-down state. Live read: the drag-down guard's trips (`group` "drag") and the deaths with two or more attackers, before and after; kills per standing fight.
4. **Break line of sight in the flee.** Claim: A 1:00 and its summary (line of sight manages hordes). Change: of the flee's clear headings, prefer one whose leg ends with `line_to` blocked from the group's centroid (a building corner, a wall), and hold there while it stays blocked, as the inside hold does. Live read: the held count on the ticks after such a leg against an open-ground leg, and how often a `many` flee ends with the group dropping below LISTED_R.
5. **Fight one or two across an obstacle, outside a shelter.** Claim: A 4:29 (using obstacles, the weakest source) and D 0:14 "Utilizing the environment". Change: with one or two held and a doorway or a fence the map knows within a few tiles, the Fight's stand moves to the far side and waits there, the door fight's rule taken outside the sheltered building (a climb at a walk, #4296, never the vault). Live read: kills per fight and health lost per fight in fights taken at an edge against in the open.

For the LLM goal source's system prompt, the titles support three short lines, each the presenter's advice: walk rather than run unless chased; on the first days take the nearest buildings' water, food and a weapon before travelling; a fire station or a police station is where weapons are.
