# Plan 22 — the agent base: design spec (candidate K1)

Status: for Angus's review before the plan is written. Decision it rests on (Angus, 2026-10-27): candidate K1 of the options brief (`.superpowers/sdd/2026-10-27-plan-22-agent-base-design/plan-22-options.md` § 3); the JVM sidecar (K2) designed behind the transport seam, not built; no JDK on the host. The three design reviews, the jar research and the options brief are in that workspace. The probe session that settles the three open mechanisms is `testing/artifacts/p22_probe-20261027-032502/` (its `GUIDE.md`, cited below by line; rows #4197–#4202 on `docs/platform/harness.md#agent`).

## 1. The question and the answer

Plan 21b showed the file-linked Lua agent works as a test tool (every goal live, 0 gaps, 0 Lua errors, a 0.79 ms tick mean at 60 Hz) and fails as a survival agent for reasons below the planner: a flag set is not a run; a scan is 49 lines of about 3 KB; the frames lacked the fields the deaths needed; and multi-step policy was split across two languages (`docs/superpowers/specs/2026-10-26-agent-harness-report.md` § 7; the options brief § 1). Plan 22 rebuilds the base so that:

1. the Lua is a thin **motor and sensor** that drives the engine's own input layer and emits typed, versioned lines;
2. every multi-step decision lives in **Python**, replayable and testable offline;
3. the **transport** is an interface with one implementation (files) and room for a second (a sidecar) without touching the schema, the world model or the actions;
4. an **LLM planner** can read the state and call the actions without `summary.py` guessing.

The yardstick stays Plan 21b's: a gate is a measurement with a falsifier, graded on an artifact.

## 2. Principles (binding on every task)

- **One schema, two hosts.** `PZA/1` is one source checked against both sides by a `--check` gate (§ 4). No field, kind or enum exists that the gate does not know.
- **Observe, never echo.** A sensor reads what the engine did (position, measured pace, the input latch *after* the frame step), never the flag the actor wrote. The probe's `setrun` arm read `running` true on 47 of 48 frames at a walk's pace (GUIDE.md L83).
- **Skills, not machines, in Lua.** A Lua skill is one bounded engine action with a typed result; a goal with two steps is Python's.
- **Index-first, every member.** `PZA.call` or an explicit `X ~= nil and X.m ~= nil`; a caught raise still parks the `-debug` client (#0957).
- **Bytes and ticks are budgets.** One flush a tick, a byte budget per tick, overflow an event; the worst tick is graded, not only the mean.
- **Frozen drivers, versioned gates, replays.** Plan 21b's discipline unchanged (CLAUDE.md § 5 "Freezing").
- **No server component on the control path.** Server reads are for grading and server-owned truths on the existing bus; the one server listener (§ 9) feeds typed damage events the client cannot hear.

## 3. Architecture

```
Python (testing/agent/)
  planner/    scripted policies now, an LLM tool-caller later; both call Actions and read World
  world.py    World = pure function of the PZA/1 lines (frames, events, map deltas, action results, server reads)
  actions.py  Action {aid, type, args, deadline} -> accepted|rejected -> progress* -> done|failed {reason, snapshot}
  transport/  Transport interface: send(cmd) / lines(); FileTransport (today's link.py, hardened); SocketTransport designed only
  schema/     pza1.json (one source) + a generator -> the Lua constants header, the Python dataclasses, the fake mod, the LLM tool descriptions
PZAgent client Lua (testing/PZAgent/)
  Core    PZA.call/field; keyed JSON for small kinds; the generated positional encoder for bulk kinds
  Link    one buffer, one flush per tick, a byte budget, overflow -> event; the seq/ack replay guard unchanged
  Motor   an OnPlayerUpdate handler re-asserting setForceRun/setForceSprint every frame while a skill wants a gait
  Skills  walkTo | steer | attack | interact | equip | consume | drop | stop ; each one engine action -> act lines
  Sense   self frame (measured pace, load, body parts, weapon reach, forceRun read after the frame), engine events, map from first sight + a dirty set
PZTestKit bus (server): grading reads (stats.all …) and damage.watch, the one server listener (§ 9)
```

## 4. The protocol PZA/1

**Line kinds.** `hello{proto:"PZA/1", mod, build, user, rate, caps[]}`; `frame{seq, tick, wallMs, gameMin, me{x,y,z,dir,pace,moving,running,sprinting,forceRun,autoWalk}, stats{…}, body{health, bleeding, scratched, bitten, parts[[i,h]]}, load{weight, max, level}, weapon{type, cond, reach}, action{class,n}, zombies[…], cost{…}}`, sent as a **delta** against the last acked full frame, a full frame every K frames; `event{kind: damage|swing|zombie_dead|item_added|item_removed|door|lua_error|overflow, …}`; `map{full|delta: squares by position, dirty set}`; `act{aid, state: accepted|rejected|progress|done|failed, reason, snapshot{me, nearest}}`; `reply{to, …}` for queries. Every line carries `seq`, `kind`, `tick`, `wallMs`. `frame` and `map` are encoded **positionally** (§ 8); the rest stay keyed JSON.

**Commands.** `cmd.txt` carries one JSON line `{seq, aid, type, args}`; `ack.txt` and the seq guard are unchanged.

**The schema's home (a ruling, not an experiment).** `testing/agent/schema/pza1.json` (JSON Schema) is the one source; `tools/pza_schema.py --write` generates the Lua constants header (field orders, enums), the Python dataclasses and reason sets (`agent/reasons.py` becomes generated), the fake mod's validators and the LLM tool descriptions; `--check` joins CLAUDE.md § 3 (the `bus_inventory` pattern). The three reviews proposed three homes; one JSON file read by one generator for three targets is the simplest form of "one source checked against both sides".

## 5. Actions

Types in this plan: `walkTo{x, y, gait}`, `steer{vx, vy, seconds, gait}` (a **world** vector; the Lua rotates it, § 7), `attack{targetId}` (steps to the engine's own reach, `getMaxRange × getRangeMod`, faces, swings; its result reports `attackStarted` and `meleeDelay`, never `DoAttack`'s return, which is always false), `interact{objectId | x,y; kind: open|close|loot(filter)}`, `equip{itemId}`, `consume{itemId}`, `drop{itemId}`, `stop`, `scan{r}` (a query), `rate{hz}`. Each: a precondition check in Lua (`rejected` with a reason from the schema's closed enum), `progress` at most once a second, `done|failed` with a snapshot. Gait is `walk|run|sprint`. **Fight, flee, explore and loot-house are Python policies** composed of these; the Lua fight and flee machines of Plan 21b are removed.

## 6. Observation and the map

The map lives in Python from `map` lines: a full `scan r` once at a new building or on request; thereafter the Lua emits a square only when an observed field changed (doors, windows, containers' counts, floor items: the dirty set), under the per-tick byte budget; a backlog drains over ticks and an `overflow` event names a cut. The frame carries what Plan 21b's deaths lacked (§ 4): `load.level`, `load.weight/max`, `body.parts`, `weapon.reach`, a measured `me.pace`.

## 7. Movement (settled by the probe, X1)

What the session read (GUIDE.md § 1, L80–L85; rows #4197–#4199; one session, n = 1, no client option changed, the client's `toggleToRun` option false):

- A pathed `goto` walks at 2.04–2.08 tiles/s. With `setForceRun(true)` **re-asserted on every frame from an `OnPlayerUpdate` handler** the same pathed walk runs at 3.70–3.73 tiles/s (1.81 ×), endurance falling where the walk's held (L80).
- The same write from `OnTick` every tick does **not** run (2.02–2.05): the frame read `forceRun` true after the write and the next `OnPlayerUpdate` read it false on every frame; something clears a force-run written after the world update before the next frame's input read, as the options brief's frameStep reading predicted; the jar research's "or `OnTick`, one frame late" is refuted (L81).
- `setRunning`/`setSprinting` from `OnTick` is a dead flag: a walk with `running` true on the frames (L83).
- `setForceSprint(true)` beside the force-run **sprints** a pathed walk: 4.59–5.16 tiles/s, `sprinting` true on 62 of 74 frames, endurance falling 4–9 × faster; the inferred degrade to a run did not happen (L84).
- Auto-walk steers: with the vector sent in the engine's **input space** (`ix = L(ux − uy)/√2`, `iy = L(ux + uy)/√2`, the inverse of `IsoPlayer.updateMovementFromInput` L3025–L3026, found in review and confirmed live by a calibration leg within 1.99°), six legs went within 1.52° of the commanded heading at lengths 1, 1.95 and 2, and ran (3.71–3.82) only with the force-run re-asserted; a force-run set once did not hold (L85).

**Decisions.** The `Motor` is one `OnPlayerUpdate` handler holding `wantRun`/`wantSprint`, re-asserted every frame through `setForceRun`/`setForceSprint`, cleared by every skill's end, supersede and stop; the toggle-to-run option is never written. `walkTo` is the vanilla path with the Motor's gait; `steer` takes a world vector, which the Lua rotates into input space (the one place the transform lives, with its jar line in the comment), sets auto-walk once and clears it at the end. `me.pace` is measured from positions; `me.forceRun` reads `isForceRun` after the frame (an honest field: it read false on the `OnTick` arm's update frames while the `OnTick` frame read true). `setRunning`, `setSprinting` and `setPathfindRunning` leave the mod. K2's input seam is not needed for gait.

## 8. The Link (settled by the probe, X2)

What the session read (GUIDE.md § 2, L95–L118; row #4200): encoding a 2740-byte scan part with today's `PZA.json` costs 1250 µs a call (the key sort 322 µs of it); `open + write + close` of the encoded line 138 µs, of 20 bytes 118 µs, open and close alone 62 µs; the poll's reader open-read-close 54 µs; a write to a held writer 4 µs; a positional encoder of the same part 148 µs for 1244 bytes. The encoder is 74.85 % of pass 4's 1.67 ms emit at the bench part's size and 57.42 % scaled per byte to pass 4's 2.1 KB part (an assumption the guide names); open, write and close are under 9 % together (L111–L118). Pass 4's "per-line fixed cost" was the encode of each 3 KB part.

**Decisions.** (1) `frame` and `map` are encoded **positionally** by the generated encoder (arrays in the schema's field order, strings quoted, numbers via `tostring`, `null` for an absent field; no `pairs` walk, no sort); small kinds stay keyed JSON. (2) **One flush per tick**: the scan part, the ack and the frame share one buffer and one open-write-close (about 100 µs saved per extra flush). (3) **No writer held across ticks** (the jar's `PrintWriter` has no autoflush: lumps). (4) The poll stays every tick (54 µs). (5) A byte budget of 1.5 KB of positional bytes a tick; a map backlog drains under it. (6) **The sidecar trigger, written before X4 runs:** K2's transport spike runs only if X4 reads the emit above 1 ms mean or 3 ms worst per tick at the budget; X2 projects about 0.2 ms a full tick (about 120 µs/KB plus one open), so the trigger is not expected to fire.

## 9. Server side (settled by the probe, X3)

What the session read (GUIDE.md § 3, L142–L161; rows #4201–#4202): six `Base.Plank` adds by RCON took the client's frame weight to 19.555 against a `maxWeight` of 12; HEAVY_LOAD read level 1 at a carry ratio of 1.13, 2 at 1.38, 3 at 1.63 and 2 again at 1.38 after the drop (#3926's thresholds read live). At level 3 the overall health fell in 34 frame-to-frame drops carrying 49 quanta of about 0.381 (the Stage C runs' quantum), every one at level 3, **walking and standing still** (standing drained at about a third of the walking rate), and none in the level-2 window; the 75 floor was not reached (the minimum 81.93; about 3.7 game minutes of loaded walking short, a projection). The server's `OnPlayerGetDamage` listener counted 49 `HEAVYLOAD` events, one per quantum; the client's listener and the mod's own client hook counted 0: **the client is deaf to the body-damage events**, as #2597 says (`BodyDamage.Update` returns at once on a client for the local player). The Stage C deaths' unexplained fall (the 37th inventory item, 74.56) is read as this drain by inference (#4192's clause): the planner looted itself to level 3.

**Decisions.** (1) The frame's `load{weight, max, level}` is the planner's input: a policy stops looting before level 3 and drops to level ≤ 2 on a fall. (2) Typed damage events come from **one narrow server listener** on the bus, `damage.watch` (the `fall.probe` pattern: per-tag counts and the last N records with wall and amount, every tag not FALLDOWN only), read by the Python side at the bus cadence into `World` as `damage` events tagged `server`; the client hook stays for the events that do fire client-side and the frame's health delta stays the fast signal. (3) Nothing else moves server-side; a server-side scan is out.

## 10. The test and measurement base

- **Offline:** the lupa 5.1 host (today's) with the fake mod generated from the schema; a fault-injection test (every Java member nil or raising → a typed `rejected`/`failed`, never a raise); golden replays of every live run's `state.log` through `World` (byte-stable JSON); property tests on the encoders (decode(encode(x)) == x on both forms); the `pza_schema --check` gate.
- **Live gates** (each versioned, graded off an artifact; the X4 session): tick mean < 1 ms at 60 Hz over 1800 ticks; worst `OnTick` ≤ 3 ms and 0 ticks ≥ 5 ms over 10 minutes (the instrument: JFR through `pzt`'s own JVM list if it costs one flag, else the 1 ms clock with the rule stated); 0 gaps; 0 Lua errors; 0 parks; ack→first-move p90 < 500 ms; the kept map ≥ 99 % of walls, doors, windows and containers against one full scan at the end.
- **The combat session (X5, on `agent`):** `attackStarted`/`meleeDelay` across swings, the client's copy of a zombie's health against a server read in the same wall second, the loop latency from a zombie event to the planner's command acting; it places the fight reflex (Lua skill or Python) by the measured latency against a lunge.
- **The acceptance:** one survival run on `agent` with the Python policies, graded by `grade_c`'s successor, any death explained by the frames (the frames now carry what the Stage C guides lacked).

## 11. Out of scope

The JVM sidecar's build, a JDK, any change to the install or the launcher JSON, a server-side scan, key or stick injection, a Kahlua-faithful offline host, a sit skill (the one posture X3 did not read), the nutrition mod's own code.

## 12. Plan shape (for `writing-plans`)

About 14 tasks: the schema and its generator and gate (2); the positional encoders and the one-flush Link (1); the Motor and `steer`/`walkTo` (1); the skills (`attack`, `interact`, `equip`, `consume`, `drop`) as typed actions (2); Sense, events and the server `damage.watch` (2); the map from first sight with the dirty set (1); `World`, `actions.py`, the Transport seam and the policies ported to Python (3); the fake mod, fault injection and replays (1); the X4 session and the X5 session (2, each under the 15-minute split with its own frozen driver); the acceptance run and the report (1). Plan 21b's drivers and gates stay frozen; `c_grade`'s successor is versioned.

## 13. Open after this spec

Whether the force-run clear is `CharacterInputComponent.updateToggleToRun` in `frameStep` (the frames show the order, not the caller: GUIDE.md L81); the 75 floor live; the drain while seated; the client's copy of zombie health (X5); JFR's cost as the worst-tick instrument (X4).
