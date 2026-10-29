# Plan 23 — the survivor: instincts, a chained day and the goal seam

**Date:** 2026-10-28 · **Owner:** Angus · **Base:** the Plan 22 agent base at `ee723a7d` (report `docs/superpowers/specs/2026-10-27-plan-22-agent-base-report.md`) · **Build:** 42.21 (jar `4a0e9546ec`)

Angus's standing direction (2026-10-28): the programme's goal is a character that plays the game, with scripted actions for its instincts and LLM-driven actions for its broader decisions; the design's minutiae are the controller's to explore, prototype and iterate, with no design approval round. Every fork below is therefore a ruling (`P23-n`), weighed by long-term operability, maintainability and control of the base, survival first, each with its downside stated.

## 1. The question and the answer

Plan 22 left a base whose channel works (0 gaps, 0 Lua errors in six sessions, a 128–181 ms move, a client copy of a zombie's health that agrees with the server's) and whose planner dies below any decision worth an LLM: a fight that hit a door for two minutes because the map names no edges, a flee pinned by a load the loot itself built, a death window the server's records could not fill, and needs that no session lived long enough to feel (the first moodle arrives after about 4 to 5 game hours, which is 16 to 18 wall minutes at the 90-minute day, past the 15-minute session rule, and each run restores its fixture, so no session could continue the last).

**The question.** Can the base drive one character through a game day and its night — fighting what it must, fleeing what it cannot fight, eating, drinking and sleeping when the game says to — on sessions that chain on one world, so that a goal layer, scripted first and an LLM next, has a living character to steer?

**The answer this plan builds.** Three layers and a chain:
- **Instincts** (`Survive`'s pre-empting branches, reshaped): threat, need, load and night. They run every planner tick, read the frames alone, and pre-empt any goal.
- **Goals** (new `planner/goals.py`): a small typed set (explore toward a place, loot a building, shelter in a building, stock water or food, rest) chosen by a `GoalSource`. Plan 23 ships the scripted source, the LLM source behind the same seam, and one session of each.
- **The chain**: a fixture snapshotted from a finished run, so session n+1 boots the world session n left; the character changes in no way between sessions (Angus's offline rule holds by construction).

GO is a chain that lives through 24 game hours with a drink, an eat and a sleep each landed `done` at the game's own need, every fight ended or fled, and, if it dies, a death the frames and the server's records explain from the first wound.

## 2. Principles (binding on every task)

1. **Instincts before goals.** No goal is sent while an instinct branch answers; a goal pre-empted by an instinct is `superseded`, never lost (its container, place or building stays available).
2. **The frame is the truth the planner acts on**; the server's reads inform grades and the goal view, never a reflex. A server read never stalls the planner (P23-9).
3. **Index first, through `PZA.call`, Kahlua rules**, one flush a tick, the per-tick budget of spec 22 § 2 (under 1 ms at 60 Hz) — unchanged.
4. **A need is the game's.** The planner acts at the first moodle (thirst above 0.12, hunger above 0.15 [#0509, #0508]; fatigue above 0.6 [#2279]); nothing seeds, speeds or writes a stat. A session that never reaches a need says so.
5. **The load is never built.** A loot stops at the weight the carry ratio allows; the drop guard is a backstop, not a plan.
6. **Nothing changes offline.** A chain's snapshot is the world as the server saved it at the session's stop; the next session's first frame is diffed against the last session's last frame (position, health, stats, inventory count) and the guide reports every difference.
7. **One driver file per session kind, frozen at its first boot**; the library (`testing/agent/driverlib/`) is not frozen, and each artifact names the tree's commit so the library's state at the boot is recoverable. A defect found mid-chain is fixed in the library and the chain continues on `e_day_2.py`, the split named in both guides.
8. **The LLM is a goal source, nothing more.** It sees a view of at most about 2 KB of game state, answers one goal in a JSON shape validated against a schema generated from the goal types, and on a late, malformed or unsafe answer the scripted source stands in for that goal. It never sends an action, never sees a frame, and never receives anything but game state.
9. **Every gate is versioned per pass and every grade has an offline case that fails it**; `gates.py` stays frozen, new gates live in new modules.
10. **Trial and error is encouraged**: a session that reads a mechanic wrong is written up and the next session fixes the base; a prettier number is never re-run for.

## 3. Architecture

```
  frames/events ──► World ──► Survive.tick ──► instincts (threat, need, load, night) ──► Action
                      │              │                    (any answers: the goal waits)
                      │              └──► goals: current Goal.step(world) ──► Action
                      │                        ▲
                      │     view(world) ───► GoalSource.propose(view) ──► Goal   (scripted | LLM via `claude -p`)
                      │
  server polls (thread) ──► World.merge_server / merge_damage      (grades and the view; never a reflex)

  session n ──stop──► server save ──► pzt snapshot --from-run ──► fixture agent-s<n> ──► session n+1 boots it
```

The Python base's modules keep their names; new ones are `planner/goals.py` (goal types, the scripted source, the goal runner), `planner/view.py` (the view), `planner/llm.py` (the CLI source), `driverlib/` (the drivers' shared library), `gates_e.py` and `gates_f.py` (the new sessions' gates), and `pzt`'s `snapshot` command.

## 4. The chain: a fixture from a run

**P23-1 — sessions chain by snapshotting a run.** `pzt snapshot --from-run <run_dir> --name <fixture> [--parent <fixture>]` calls the existing `fixture.snapshot(name, server_cache, client_caches, record)` on `<run_dir>/server` and `<run_dir>/clients/<user>` after the session's teardown (the same paths and skip lists `provision` snapshots), and writes a `fixture.json` whose record carries `parent` (the fixture the run booted), `run` (the run id), `session` (the chain index), `build` and the parent's sandbox block copied. The blobs are gitignored as every fixture's are; the record is tracked. The chain's fixtures are `agent-s1`, `agent-s2`, … and a chain never overwrites one (a re-run of session n+1 boots `agent-s<n>` again).
- *Why this and not a multiplier, a seeded stat or an aged fixture:* it is the only route that keeps principle 4 and the 15-minute rule at once, it costs one small `pzt` command on code that exists, and it is what a survivor over days needs anyway. *Downside:* the snapshot's fidelity rests on the server's save at `quit`, which Task 1 verifies by a round trip (session A moves the character and loots one item; the snapshot; session B's first frame reads the moved position and the inventory count) before any chain runs; a fixture per session costs about the fixture's size on disk each (the record says how much).
- *The client's side:* a restored fixture client skips creation because the character persists server-side [#1715]; the chain relies on that and the round trip reads it.

**P23-2 — the session cap.** A chain session's loop runs at most `DAY_CAP_S` 840 s (14 minutes) inside a `BUDGET_S` of 1200 s; 24 game hours at the 90-minute day are 90 minutes of loop wall, so a day is 7 sessions, a day and its night about 8. The controller boots each after the doctor and the 12 GB read, ledgers it, ticks the chain table, snapshots, and boots the next; a death ends the chain and the plan's reading.

## 5. The protocol PZA/1.2

**P23-3 — PZA/1.2 appends, never reorders.** `schema/pza1.json` gains, each at the end of its group's `x-order` so the 1.1 prior arity stays decodable (the generator's `x-prior` per group, ruling S-31):
- `square`: `blockN`, `blockW` (booleans: movement from this square to its north and west neighbours is blocked, `IsoGridSquare.isBlockedTo`), `edgeN`, `edgeW` (a wall, door or window stands on that edge, open or closed, `isSomethingTo`); the east and south edges are the neighbours' west and north. *Amended 2026-10-28 after Task 3's jar read* (`docs/superpowers/specs/2026-10-28-plan-23-jar-reads.md` § 1): `isBlockedTo` reads a square's own north or west edge for its north or west neighbour and blocks on a `collideN`/`collideW` flag with no window, a closed or barricaded door, an intact closed or barricaded window, or a stair top (an open door or a smashed window does not block); `isWallTo` is the same movement flag, not a sight read, so the spec's first draft's `wallN`/`wallW` "sight-blocking" fields are replaced by `edgeN`/`edgeW` off `isSomethingTo`, which reads any wall, window or door structure on the edge; a diagonal is blocked when any of the four edges at the shared corner is.
- `frame.me`: `hour` (the game's hour of day as a number, from `getGameTime():getTimeOfDay()`, confirmed by the jar read) — the night branch's clock; `gameMin` stays.
- a `sleep` action with no arguments (the hours are vanilla's own formula from fatigue and the bed quality, P23-E) → `done {sleptH, fatigueBefore, fatigueAfter, bedType}` or `failed <reason>` with the new reasons `not safe` (a zombie visible, chasing or very close, vanilla's own refusal) and `not allowed` (the server's `SleepAllowed` off), pain and panic refusals reading the existing `not valid`; its skill is § 7's night branch's. *Amended 2026-10-28 at Task 4:* the first draft's `{hours?}` argument and the reasons `not tired` and `no bed` went: the floor is a bed (vanilla's `floor` quality), and vanilla has no "not tired" refusal.
- `PZA.VERSION` "1.2", `proto` "PZA/1"; `--write` regenerates the three targets; the goldens are re-recorded under this named change, the decoder's tolerance carrying the 1.1 logs.

**P23-4 — the poll paced to every third tick.** `L.POLL_EVERY = 3`: `L.poll` opens `cmd.txt` on every third tick (20 Hz at 60 fps), whatever the frame rate; the ack write is unchanged. The X4 fix pass put the command-accept burst and 0.42 ms a tick in the poll (#4216); a third of it is the cheapest cut with no new mechanism. *Downside:* a command waits up to two extra ticks (33 ms at 60 fps) to be accepted, which a 2 Hz planner never feels but a 128–181 ms move reading will carry; and if the poll's cost is the open of a file the driver has just replaced rather than the read, the saving is a third of less than expected. The sidecar stays out of scope: its trigger did not fire in two sessions (S-18, S-34). Read by `x4_link_3.py` under the frozen `gate_x4` (§ 10).

## 6. The map's edges and the line

**P23-5 — the World knows edges, and the Fight uses them.** `World.blocked(a, b)` reads the edge between two adjacent squares from the kept map (`blockN`/`blockW` of the southern or eastern of the pair), `World.line_clear(a, b)` walks the squares between two positions and is false at any blocked edge (`blockN`/`blockW`) the line crosses or any `solid` square (a melee swing crosses what movement crosses: an open doorway, not a closed door or an intact window; `edgeN`/`edgeW` are kept for the view and a later sight reading, since the jar's wall flag is a movement flag: Task 3's read), and `World.reachable_adjacent(target)` lists the target's neighbours from which `blocked` is false. The watch's fingerprint includes the four edge fields, so a door opening on a watched square sends its delta (door events come from the watch already). The scan's per-square read grows by four calls, within the 8-squares-a-frame budget (`x4_link_3` reads the map watch's cost after the change).
- *Downside:* a diagonal step's blocking is the engine's own rule (a corner cut past two walls), which `blocked` approximates by both orthogonal edges; the first stand-off the chain meets on a diagonal is the reading that refines it.

## 7. The instincts

`Survive`'s branches become `threat`, `need`, `load`, `night`, then the goal runner (`BRANCHES` in that order). Each is a small class with `observe(world)`/`choose(world)`, as the policies are today, under `planner/`.

**Threat (P23-6).** The Fight pins its target: the zombie it chose stays its target until dead, unreachable (the landed three-swing stall, or a failed approach) or out of `DANGER_R`; it never swaps to a nearer one mid-swing. Before an attack it requires `line_clear(me, target)`; if not, it walks to the nearest `reachable_adjacent` square from which the line is clear (one reposition per target), else marks the target unreachable and disengages. The flee rules: three within 6 tiles (as today); two within 6 tiles when health is under 60 **or** the body reads any wound or bleeding (the pair rule read on wounds, from the acceptance's reading); one zombie when unarmed. A flee at load level 3 or more first drops the heaviest item that is not the held weapon, a water container or food, then runs (so a flee is never pinned by the load it should never have built; principle 5 makes this rare).

**Need (P23-7).** `THIRST_T` 0.12, `HUNGER_T` 0.15 (the first moodles). Drink the held container with the most fluid (by the inventory's fluid fields, as the Lua loot picks water), else eat the held food of the smallest spoil risk by `data/food-items.json`'s full types (`FOOD_RX` and `WATER_RX` go; a name regex missed four foods and matched an empty bowl). When nothing held answers, the need marks `water` or `food` wanted, which the goal layer's `stock` goal reads. *Downside:* a filled container is the only water the chain can drink (no `fill` skill this plan); a chain that empties its containers says so.

**Load (P23-8).** A loot takes items only while `(weight + item) / max <= LOAD_RATIO_MAX` 1.0 (level 0; the moodle's level 1 begins above 1.0 [#3926]), by a use filter (water, food, weapon, bandage) and never `all`; the Lua `interact loot` gains a `maxWeight` argument so the stop is the skill's, not a drop after. The drop guard stays (`DROP_AT` 3 → `DROP_TO` 2) as the backstop and is expected never to fire; a guide that sees it fire names the loot that built the load.

**Night (P23-9).** The branch answers when fatigue is above 0.6 or the hour is past 22 with fatigue above 0.3 (the jar read of the client's bed handler, #3030's source, settles the second clause's condition: the engine's own "can sleep" rule, or the plan's). It walks to the nearest known interior square (a square with `room` set, in a `building` the map has seen, reachable with every door on the path openable: `interact open` as needed), closes the door it came through, and sends `sleep`. The `sleep` skill is the client's bed handler's calls through `PZA.call` (the jar read lists them: at least `setAsleep`, `setTimeOfSleep`, the wake time, and whether the server's `SleepAllowed` ini and `allPlayersAsleep` fast-forward the single player's night; the profile's `[server]` `SleepAllowed`/`SleepNeeded` are set true as `agent.toml` already does). The frame keeps emitting while asleep (the night's frames are the reading of the fast-forward). *Downside, as first written:* if the dedicated server does not fast-forward a lone sleeper, a sleep is 7 to 9 game hours of wall time at the 90-minute day, which the chain cannot afford. *Amended 2026-10-28 after Task 3's jar read* (the jar-reads note § 3): the server's main loop sets fast-forward when `SleepAllowed` is on and every living connected player reads asleep, at `FastForwardMultiplier` × day minutes / 30 (120× on the 90-minute day at the default 40), so a lone sleeper's 8 game hours are about 4 wall minutes; the first night measures that rate on 42.21 (unread live) and the client's clock under it.

## 8. The goal layer

**P23-10 — goals are a typed set, chosen by a source behind one seam.**
- `Goal` types (dataclasses in `planner/goals.py`, each with `step(world) -> Action | None` and a terminal `state`): `ExploreToward(x, y)`, `LootBuilding(building)`, `Shelter(building)`, `Stock(kind: water|food)`, `Rest(seconds)`. Each is a bounded sequence of the existing actions (walk, open, loot, scan) with a budget (`GOAL_MAX_S` 90 s) and the end reasons the actions give.
- `GoalSource` protocol: `propose(view: dict) -> Goal`. The scripted source (`ScriptedSource`) is today's forage and explore reshaped: `Stock` when a need wants, `LootBuilding` for the nearest unlooted building with containers, else `ExploreToward` the unexplored edge, `Shelter` when the night branch wants a building it does not know.
- `planner/view.py`: `view(world) -> dict` with position, hour, health, needs, load, held weapon, inventory by use, buildings known (each with containers seen, looted, distance), zombies seen in the last minute by distance band, the last goal and its end, the last three events — serialised under about 2 KB; the same dict renders to the text the LLM reads and to a line in `decision.log`.
- The goal runner (in `Survive`): one goal at a time, a new one proposed when the current ends or at `GOAL_MAX_S`; an instinct's answer supersedes the goal (its state `superseded`, re-proposable).

**P23-11 — the LLM source is the `claude` CLI, in a thread, validated.** `LLMSource` runs `claude -p --output-format json --model <model>` (default `sonnet`; the installed Claude Code 2.1.310 on this host, authenticated by Angus's own login, so no key is stored in the tree) with a system prompt naming the goal types from `schema/goals.json` (generated from the dataclasses by `tools/pza_schema.py`'s sibling step, `--write`/`--check`) and the view's text; the answer is parsed as one goal, validated against the schema, and applied; a call runs in a worker thread with `LLM_TIMEOUT_S` 20 and the scripted source answers whenever the call is late, malformed or names an unknown place. The prompt and every answer are logged beside `decision.log` as `goals.log`. The view holds game state only (principle 8).
- *Why the CLI and not the API:* no credential in the tree or the environment, the same account Angus already pays for, one process boundary that a fake binary tests offline. *Downside:* a cold `claude -p` call costs seconds on this host (the F session reads the latency), the CLI's output format is a contract outside this repo (pinned by the version the guide names), and a model's refusal or a rate limit reads as a fallback, not an error.

## 9. The instrument

**P23-12 — a driver library, not copies.** `testing/agent/driverlib/` (`session.py`: the memory gate, preboot, boot, hello, kit, the stop conditions; `polls.py`: the server reads in a thread with a queue, the planner reading the latest; `record.py`: the loop record, the death record, persist; `chain.py`: the snapshot step and the lineage diff of § 2 (6)). `_dlib.py` and every frozen driver stay as they are. New drivers import the library and `xlib` and copy nothing; each refuses undefined arguments (tested statically), names its own file and profile, and runs its pre-boot checks offline.

**P23-13 — the server never stalls the planner.** Every server read (`stats.all`, `players`, `damage.watch since`, `zombie.get`) is issued by the poll thread; the loop reads the newest result and its age. `damage.watch` is read every `DAMAGE_POLL_S` 5 (the ring holds 5000; `dropped` is graded 0).

**P23-14 — the grades.** `gates_e.py`: `grade_e1(artifact, prev_artifact)` reports alive-through, the needs answered (`consume` and `sleep` `done` with the stat's fall on the next frames), fights (ended, fled, stand-offs), loads (the max ratio seen, the guard's firings), the lineage diff, the cost summary, and a death from the first wound (the window opens at the first `body` wound or bleeding rise, not 300 frames before the stop); `gate_e1` is GO on § 1's bar over the chain's artifacts. `gates_f.py`: `grade_f1` reports the LLM calls (count, latency p50/p99, parsed, fallbacks, each goal's end) beside `grade_e1`'s survival reading. `x4_link_3.py` uses `gate_x4` unchanged; `x5_combat_2.py` uses `gate_x5` unchanged with the target pinned.

## 10. Sessions

| Session | Driver | Fixture | Reads | Cap |
|---|---|---|---|---|
| X4-3 | `x4_link_3.py` | `agent0` | the paced poll's 60 Hz tick and the map watch with edges, under `gate_x4` (the plan's cost reading; one session, no fix pass) | 14 min |
| X5-2 | `x5_combat_2.py` | `agent0` + spawned zombies | the pinned fight, the line check, the swings that never start, with the reads off the thread (S-22's listing diagnostic: `zombiesSeen`/`zombiesListed` on the spawn frames) | 14 min |
| E1…En | `e_day.py` | `agent` → `agent-s1` → … | the chain: a day and its night under the scripted source; each session snapshotted into the next's fixture | 14 min each, ≤ 9 |
| F1 | `f_goals.py` | the chain's last fixture, or `agent` | one session under `LLMSource`: the goals proposed, their latency and ends, survival | 14 min |

Order: X4-3 and X5-2 first (the Lua frozen before the chain), then the chain, then F1. Every boot: doctor, 12 GB free read and ledgered, one session at a time, launched detached by the controller and polled in foreground calls (CLAUDE.md § 5). Angus's 2026-10-28 direction is the standing approval for these boots (ledgered as a ruling); a boot still waits for a quiescent tree.

## 11. Out of scope

The sidecar and any JDK; a `fill` skill or any water source but a looted container; vehicles, firearms, crafting, building, farming, the sit posture; a second client or another player; a model API key or any LLM route but the installed CLI; prompt engineering past one session's reading; the nutrition mod's own code; any change to the install or the launcher.

## 12. Plan shape (for `writing-plans`)

About 20 tasks: the library and the snapshot command with the round trip (2); the jar reads (sleep's handler and fast-forward, the edge members, the hour) (1); PZA/1.2 and its generator step for `goals.json` (1); the Lua: the paced poll, the edges in the watch and scan, `loot maxWeight`, the `sleep` skill (3); the World's edges and line, the buildings index, the inventory by use (1); the instincts: threat, need, load, night (3); the goal types, the scripted source, the view, the runner (2); the LLM source with a fake CLI (1); the grades and the four drivers (2); the sessions X4-3 and X5-2 (1 each, written up); the chain's sessions (ticked off a chain table) and F1 (2); the report and close (1). Every live session is written up with its artifact, rows and guide under CLAUDE.md § 4.

## 13. Open after this spec

The fast-forward rate a lone sleeper's night runs at on 42.21 and the client's clock under it (§ 7, read off the jar, measured by the first night); which tiles carry the collide flag beside doors, low fences and empty window frames (§ 6); the poll's cost split between the open and the read (§ 5); a `fill` skill and the water sources' reach; the LLM's prompt and model choice past F1's reading; the sidecar, dormant unless a later session's flush rises.

## 14. Amendments at the close (2026-10-29)

The plan's live phase ruled four survival iterations from the chains' deaths (P23-AG, P23-AJ/AK, P23-AM, P23-AP in the ledger and the close report's § 8); the close review (`.superpowers/sdd/2026-10-28-plan-23-survivor/review-close.md`, item 7) names where the code now diverges from § 7's text. The rule record is `testing/agent/base/planner/survive.py`'s module docstring, not this section:

1. § 7 "before an attack it requires `line_clear`": a cornered Fight swings at a target within `POINT_BLANK_R` 1.0 whatever the line reads (P23-AJ fix 1), and a `stuck` or `inside` corner takes a target within 1.5 tiles whose line is not read blocked (`in_reach`).
2. § 7 "it never swaps to a nearer one mid-swing": the corner's re-pin to the nearest zombie within point blank (P23-AP R4) swaps whenever the nearest is not the pin; in F1 it alternated between two zombies about eight times. Plan 24 adds the hysteresis (re-pin only when the pin itself is beyond point blank); until then the rule reads as the code does.
3. § 7's flee rules (three within 6, the pair rule, health) are overridden by the corner (any count, any health), the door fight and the trapped fight (P23-AJ, P23-AK), and the `many` episode's keeps (P23-AM rule 1); § 7 does not describe the shelter flee, the exit walk, the hold's breach, the group steer or the leg's cut (P23-AG to P23-AP). The corner's override of the `health` flee on a `walk` corner is the close review's I1, for Plan 24 to rule.
4. § 7 "out of `DANGER_R`": the Fight drops its pin at `DISENGAGE_R` 10 tiles (Task 10), not `DANGER_R` 6.
5. § 7 Need, "the held container with the most fluid": the need branch drinks the water item of least id (fix wave P), a Plan 24 item or an amendment of the rule.

