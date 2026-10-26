# `c_survive-20261026-183905` reading guide

**`c_survive-20261026-183905/c_survive.json`** (with `state.log`, `decision.log` and `c_grade.txt`) — produced by `testing/agent/drivers/c_survive.py` at `driver_commit` `7b01bc87` (Plan 21 Task 12 fix 1: a live memory floor on two reads; a players error is not a death; …), unedited since, which imports the frozen `testing/agent/drivers/a_pipe.py`, `_dlib.py`, `testing/agent/policy.py`, `testing/agent/grade_c.py` (`pct`) and `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`); on HEAD `4b025035` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `ee23b53c`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `52a7de93`; `preboot.driver_checks` all true or false as required: `agent_lua_dirty`, `agent_py_dirty`, `driver_dirty` false). The policy under test is `testing/agent/policy.py` at its last commit before the boot, `4744e066` (Plan 21b Task 2: the policy never cools a pre-empted goal and never passes over the threat branch), unchanged at `4b025035`; the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`profile.sources.PZAgent`; `preboot.agent_commit` `4b025035`), whose last commit is `942859f2` (Plan 21b Task 1 Lua: 20-square scan parts; …), so every `PZAgent_*.lua` line cited below is at `942859f2` (`git show 942859f2:testing/PZAgent/PZAgent/42/media/lua/client/<file>`), identical at `4b025035`. Fixture `agent` (`fixture.provision_run` `prov-20261026-092028`, `fixture.build` `42.21.0`; `hello.build` `42.21`); profile `testing/profiles/agent.toml` (`profile.name` `agent`, `profile.description` "PZTestKit + PZAgent, zombies Low, 90-minute day, sleep allowed."; `profile.sandbox` `{}`, so Zombies = 5 is the fixture's provisioned value; the profile file's `[server]` sets `SleepAllowed` and `SleepNeeded` true; user `admin`). **Plan 21b Stage C, run 1** (spec § 4.3, the survival run). `preboot.doctor_clean` true; `preboot.lint_errors` empty; `verify` both pings `ok`; `server_error_count` 0; `admin_lua_error` false; `client_lua_errors` 0; `lua_errors` 0; `phase_errors` `{}`; `finished` true; `bus_dead` null; one note, the stop (`notes[0].note` "stop death: frame seq 2461 health 0"). Free memory 16.05 GB at the preboot read and the memory wait, 2.49 GB at ready, 16.3 GB after teardown (`memory`, `memory_wait`). 477.0 s wall (`wall_seconds`; `timeline`: client quit rc 0, server stopped rc 0 with 0 errors).

Files, byte-identical to the run copy under `testing/runs/c_survive-20261026-183905/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `c_survive.json` | the driver's auto-copy of `testing/runs/c_survive-20261026-183905/c_survive.json` (`cmp` equal); CRLF endings, 1803 lines | 39256 | `d92319d5b5816df42cbda72d7d744186484b616ecf9d0431528d383b0d3f4b9c` |
| `decision.log` | the driver's auto-copy (`copied` `["decision.log"]`) of `testing/runs/c_survive-20261026-183905/decision.log` (`cmp` equal); LF endings, 795 lines, one per planner tick | 372715 | `bced3b38e5d4d215daba603dfae51475b65afa296dae6bdbee0a12b29e38d93a` |
| `state.log` | `testing/runs/c_survive-20261026-183905/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal); LF endings, 2462 lines, `seq` 1–2462 without a gap: 1 `hello`, 2081 `frame`, 115 `scanPart`, 45 `ack`, 220 `event` (92 `hit`, 70 `item_added`, 21 `goal_done`, 19 `goal_failed`, 10 `zombie_enter`, 8 `zombie_leave`); the driver read 2461 of them (`lines_read`; `frames_read` 2080), the last being a frame after the death frame | 2385498 | `f32626b43b210fea391cc0061859a06e3f46ae107de689c3586bbc4f8a16c54b` |
| `c_grade.txt` | the controller's stdout of `python testing/agent/drivers/c_grade.py` over this run's `c_survive.json` (`agent/grade_c.py`'s report, no gate), copied from the run dir by the write-up (`cmp` equal), never regenerated; CRLF endings, 864 lines, a JSON object (`grade_c.py` and `c_grade.py` last changed at `7b01bc87`) | 18822 | `bc7d81e3ca235fe3479085a56e2a178e78bdebf1103f870914e43662b2d7c34b` |

`state.log` is the only evidence of the frames (positions, zombies, health, moodles, the per-tick cost leaves), the scan parts and the goal events below; `decision.log` the only evidence of each planner tick's branch and inputs. The hashes are of the working-tree bytes as written (re-hash a checkout's blob with `git show <commit>:<path> | sha256sum`). The client console `testing/runs/c_survive-20261026-183905/clients/admin/console.txt` (308574 bytes; 0 hits of `constants.CLIENT_ERR_RX`), `server-stdout.log` (295291 bytes) and the logs under `server/` and `clients/` are per-machine and untracked, and nothing below rests on them.

## How to read it

The schedule is `c_survive.py`'s docstring: `hello` (52.97–52.98 s, `phase_walls`), `kit` (to 59.671: spawn a `Base.BaseballBat` by RCON, confirm it with `item.get`, equip it through the client's `weapon.equip`, wait for a frame showing it), `survive` (59.672–467.112: the planner loop, until a stop). The loop polls the link every `constants.POLL_S` 0.1 s, ticks the policy at `PLANNER_HZ` 2, polls the server every `SERVER_POLL_S` 60 s and memory every `MEM_POLL_S` 300 s. The link ran at `hello.rate` 5 throughout: one frame every 12 ticks (`PZAgent_Main.lua` line 88, `60 / RATE`).

- **The policy** (`policy.py` at `4744e066`): each planner tick tries the branches `threat`, `need`, `sleep`, `forage`, `explore` in order and sends the first answer only when it differs from the goal still running (`fight` and `flee` compared by name). `threat` fights when armed, at most `MAX_FIGHT` 2 zombies are within `DANGER_R` 6 tiles and health ≥ `FLEE_HEALTH` 40, and flees otherwise; `need` drinks above thirst 0.5 and eats above hunger 0.5; `sleep` only above fatigue 0.7 between game minutes 1260 and 360; `forage` loots the nearest unlooted container (`loot x y all` with no need marked); `explore` scans (`scan 10`) from each new explore target, then walks (`goto`) to an unexplored edge. Every tick writes one `decision.log` line `{wall, gameMin, branch, inputs, goal, args, sent}`.
- **The Lua goals** (`PZAgent_Act.lua` at `942859f2`): `fight` swings (`DoAttack`, line 593) only when the nearest live zombie is within `A.FIGHT_R` 3 tiles (line 589) and otherwise waits where it stands; it steps back inside `A.GRAB_R` 1.0, ends `done clear` after 60 ticks with no zombie within `ZOMBIE_RADIUS` 12, and fails `low health` under 40 (line 573). `flee x y` walks there as a run (line 137) and re-aims every 30 ticks 8 tiles away from the zombies' centroid; any end of its walk but `done` is `failed cornered` (line 638). `loot x y` first walks next to the square (`approach`), failing `not adjacent` when that walk fails (line 398). A goal replaced by the policy's next send ends `failed superseded`.
- **The artifact's loop record** (`loop`): `ticks`, `decisions` (goals sent), `last_decisions` (the log's last ten lines), `needs` (rows `[gameMin, hunger, thirst, fatigue, health, serverHunger]`, `needs_fields`), `fights` (one row per `fight` sent: `seq` its command seq, `startS`, `startWallMs`, `gameMin`, `health`, `threats`, `nearest`, `end`), `lua_errors_per_min`, `cost` (`{n, p50, p99, max}` of each frame's summed `COST_KEYS`), `goal_outcomes` (`{goal: {state: {detail: n}}}`), `server_polls`, `server_fails`, `players_error`, `memory`, `wallS`, `death`.
- **Clocks.** A line's `wallMs` is the client's `PZA.now()`; `wallS`, `startS` and `decision.log`'s `wall` are the driver's clock (`loop.startPyMs` is the loop's zero). A `hit` event is not a zombie contact: it is any drop of more than 0.5 in overall body health between two consecutive frames (`PZAgent_Sense.lua` lines 126–127).
- **Command seqs.** The policy's 45 sends are command seqs 1–45 in `decision.log` order, each acked `ok` true in `state.log` (`ack.cmdSeq` 1–45; the five scans acked `reason` `queued`).

## The stop and the survival time

`c_grade.txt`: `outcome` **died**, `survived` false, `stop.reason` `death`, `stop.detail` "frame seq 2461 health 0", `stop.gameMin` 670.

- **Survival: 407.4 s of loop wall time** (`loop.wallS` 407.43753457069397; `stop.wallS` 407.43744254112244; `c_grade.txt` `survival_s` 407.43744254112244, `report_lines[0]` "died after 407 s of the loop (6.8 wall min)"), **dying at game minute 670** (`stop.gameMin`, `loop.death.gameMin`, `loop.death.frame.gameMin` 670; the death frame `state.log` seq 2461, `health` 0, `worldAge` 4.172520637512207, `stop.worldAge`). The loop's first planner tick read game minute 561 (`decision.log` line 1 `gameMin`) and the first frame 559 (`state.log` seq 2): the character lived 109 game minutes of the loop, 111 from the first frame, on the 90-minute day.
- **The death** (`loop.death`): `via` `frame`, `detail` "frame seq 2461 health 0", `gameMin` 670. The other stop conditions did not hold: `lua_errors` 0, `loop.server_fails` 0 of `loop.server_polls` 7, `loop.players_error` null, `loop.memory` one read of 2.69 GB at loop second 300.0 (above `LIVE_MIN_FREE_GB` 0.5), far from `DAY_CAP_S` 5400 and `BUDGET_S` 5700.
- **How it died: a melee fight lost to two zombies, then a walking flee they kept pace with.** Not hunger, thirst or sleep: at the last decision hunger read 0.06191468983888626, thirst 0.05539152771234512, fatigue 0.10874800384044647 (`loop.death.last_decisions[9].inputs`), all under the policy's thresholds, and no `eat`, `drink` or `sleep` goal was ever sent. The last ten decisions (`loop.death.last_decisions`, game minutes 669–670) are all branch `threat`, goal `flee 10734 10609`, `sent` false (the flee already running, compared by name), `armed` true, `threats` 2, `nearest` 1.64 to 1.43 tiles, health falling 10.47 → 0.73. Section 4 reads the fight and the flee off the frames.
- **The start kit** (`readings.start_kit`): `spawn.confirmed` true (`spawn.before.raw` "no item Base.BaseballBat in admin's inventory", `spawn.additem.ok` true, `spawn.after.fullType` `Base.BaseballBat`, `id` 1091816352); one equip ask (`equip_asks` length 1: `ok` true, `queued` true, `twoHands` true, `itemId` 1091816352); `armed` true (`c_grade.txt` `start_kit_armed` true). The first frame carrying the bat is `state.log` seq 46 (game minute 561); the 42 frames before it read `weapon` null, the 2039 from it on read `{"type": "Base.BaseballBat", "condition": 15, "ammo": 0}`, condition 15 on every one of them, the death frame included.

## 1. Needs over time

`loop.needs`, one row per server poll (`SERVER_POLL_S` 60; client frame values beside the server's `stats.all` Hunger in the same poll; `diff` = client hunger − `serverHunger`):

| gameMin | hunger | thirst | fatigue | health | serverHunger | diff |
|---|---|---|---|---|---|---|
| 561 | 0.0014882 | 0.0012411 | 0.0014218 | 100 | 0.0015951 | −0.000107 |
| 577 | 0.0106416 | 0.0089154 | 0.0113647 | 95.232 | 0.0107631 | −0.000121 |
| 593 | 0.0196615 | 0.0167338 | 0.0214450 | 74.385 | 0.0197818 | −0.000120 |
| 609 | 0.0286493 | 0.0248034 | 0.0318032 | 74.512 | 0.0287686 | −0.000119 |
| 625 | 0.0375554 | 0.0326224 | 0.0438108 | 74.639 | 0.0376736 | −0.000118 |
| 641 | 0.0463803 | 0.0403883 | 0.0617234 | 74.768 | 0.0464975 | −0.000117 |
| 657 | 0.0551217 | 0.0485999 | 0.0861344 | 74.895 | 0.0552377 | −0.000116 |

(values rounded from the row's floats.) `c_grade.txt` `needs_summary`: `rows` 7, `paired_rows` 7, `hunger_client_server_max_diff` 0.00012149382382631302, `peak` hunger 0.05512170493602753, thirst 0.04859991744160652, fatigue 0.0861344039440155, `min_health` 74.38496398925781.

- **Client against server.** The client's hunger reads below the server's in every row, by 0.000107–0.000121, with no drift: after the first row the gap shrinks by about 0.000001 a row. Against the hunger accrued between rows (about 0.009 per 16 game minutes) the gap is about 1.3 % of one interval's rise: a small, steady lead of the server's value, not a divergence.
- **What the needs did.** Hunger, thirst and fatigue rose almost linearly and stayed under 0.09 for the whole life (the policy's thresholds 0.5, 0.5, 0.7); the session ended at game minute 670, inside the day (the `sleep` branch's night is minutes 1260–360). So the `need` branch never answered (0 of 795 ticks, section 2) and **no `eat`, `drink` or `sleep` goal was sent** (`loop.goal_outcomes` has no such key). Their responses are unread here. The policy's held-food list (`inputs.branches.need.food`) read `[]` until `decision.log` line 670 (game minute 653) and `["Base.Carrots"]` after, although the loot had added `Base.CannedMilk`, `Base.TinnedSoup` and `Base.Macandcheese` at game minutes 586–588 (`state.log` `item_added`): `world.py`'s `FOOD_RX` at `4b025035` (line 20) puts `\b` after each name, so `Canned` does not match `CannedMilk`. This did not matter in this run, which never grew hungry.
- **Health** is section 4's: 100 to game minute 574, 74.55 by 587, flat at 74.2–75.1 to 659, then 0 at 670.

## 2. Decisions

`loop.ticks` 795 planner ticks (`decision.log` 795 lines), `loop.decisions` 45 goals sent; `c_grade.txt` `decisions_per_min` 6.626784183506872 and `ticks_per_min` 117.07318724195474 over `survival_s` (against `PLANNER_HZ` 2, 120 a minute).

Branch counts by loop minute (`decision.log` `wall` − `loop.startPyMs`/1000, whole minutes; `None` is a tick with no answer):

| loop minute | ticks | threat | need | sleep | forage | explore | None | sent |
|---|---|---|---|---|---|---|---|---|
| 0 | 116 | 22 | 0 | 0 | 92 | 1 | 1 | 12 |
| 1 | 115 | 22 | 0 | 0 | 73 | 20 | 0 | 15 |
| 2 | 118 | 118 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | 118 | 118 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | 118 | 118 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 118 | 61 | 0 | 0 | 28 | 29 | 0 | 17 |
| 6 (to 407 s) | 92 | 92 | 0 | 0 | 0 | 0 | 0 | 1 |
| **all** | **795** | **551** | **0** | **0** | **193** | **50** | **1** | **45** |

- **What won:** `threat` 551 ticks (fight on 507, flee on 44), `forage` 193 (all `loot`), `explore` 50 (`goto` 45, `scan` 5), `need` and `sleep` never. Of the 551 threat ticks 12 sent a goal; the rest re-chose the goal already running.
- **Goals sent** (by goal): `loot` 21, `fight` 7, `goto` 7, `scan` 5, `flee` 5. `fight` was sent 7 times and `flee 10711 10620` 4 times, each re-sent after the other replaced it (section 4's flap).
- **`cooled` entries: 0.** `inputs.cooled` is null on all 795 lines: no failed goal was ever passed over (the policy's cooldown applies to non-`superseded` failures outside `threat`, and the only such failures, three `loot … not adjacent`, were not re-chosen within 10 ticks: each square was marked looted, `policy.py` `_settle_loots`).
- **Scans and squares.** 5 scans sent (`scan 10`, command seqs 1, 23, 25, 37, 41); `state.log` holds 5 complete scans (`scanId` 1–5, `r` 10, 23 parts each of at most 20 squares, part numbers 1–23 without a gap, 441 squares each), whose union is **1179 distinct squares** learned (`x, y, z` keys of every `scanPart` square).

## 3. Goal outcomes

`c_grade.txt` `goal_outcomes` (numeric-tail details folded; raw per-detail counts under `loop.goal_outcomes`):

| goal | done | failed |
|---|---|---|
| `loot` | 16 (`moved=` 16: `moved=3` ×4, `=6` ×4, `=7` ×2, `=4` ×2, `=5` ×2, `=1` ×2) | 5 (`not adjacent` 3, `superseded` 2) |
| `goto` | 5 (`d=` 5, each 0.98–0.99) | 2 (`superseded` 2) |
| `fight` | 0 | 7 (`superseded` 6, `low health` 1) |
| `flee` | 0 | 5 (`superseded` 4, `cornered` 1) |

(`scan` is excluded by the driver as a configuration command; `refused` and `open` read 0: every goal sent was acked and seen to end.)

- **First live goals.** `fight` and `flee` ran live for the first time and **neither ever finished `done`**: no fight ended `clear` and no flee reached its square. `sleep`, `eat` and `drink` were never sent (section 1).
- **`loot` worked**: 16 of 21 moved items (`item_added` 70 events), the 5 failures being 2 supersessions (command seq 6, replaced by the first `fight`; seq 16, replaced by a nearer container's `loot` as the character moved) and 3 `not adjacent`.
- **The three `loot … not adjacent`** (command seqs 5, 10, 12; targets (10722, 10633) a fridge and freezer, (10725, 10633) a sidetable, (10726, 10634) a counter, all `solidTrans` true in the scan): in each the character never moved, `action.n` 0 on every frame, and the goal failed after exactly 360 ticks (ticks 1428–1788, 3312–3672, 3816–4176 in `state.log`; 4 × `STUCK_TICKS` 90, the sub-goto's stuck failure, line 155). `adjacentTo` (lines 254–268) keeps every neighbour whose `isSolid` is not true (line 261) and takes the one nearest the player; from the scan, that neighbour is in each case itself a `solidTrans` square: (10721, 10632) for seq 5 from (10721.48, 10630.49), (10724, 10632) for seq 10 and (10725, 10633) (the sidetable) for seq 12 from (10723.65, 10631.65), at 2.0, 1.2 and 2.6 tiles against 2.25 or more for the nearest plain floor. The frames do not carry the sub-goto's target, so the choice is an inference from the rule and the scan; it is the Stage B pass-1 guide's finding (`testing/artifacts/b_actions-20261026-183143/GUIDE.md`, "Cause 2 — the neighbour rule") recurring live: a `solidTrans` square is not one to stand on.
- **`goto` superseded ×2**: seq 21 (`explore` re-chose its edge one square west, seq 22) and seq 26 (replaced by the second `fight`).

## 4. Fights, flees and health

`loop.fights` (7 rows; `c_grade.txt` `fights.count` 7, `outcomes` `failed:superseded` 6, `failed:low health` 1). Duration = `end.wallMs` − `startWallMs`, the client's clock; "replaced by" is the next goal sent (`decision.log`) with its `inputs.threats`:

| seq | gameMin | health | threats | nearest | end | duration | replaced by |
|---|---|---|---|---|---|---|---|
| 7 | 568 | 100 | 1 | 5.90 | failed superseded | 11.2 s | `loot 10724 10632` (forage, threats 0) |
| 27 | 591 | 74.88 | 1 | 5.28 | failed superseded | 210.1 s | `flee 10711 10620` (threats 3) |
| 29 | 647 | 74.56 | 2 | 3.50 | failed superseded | 2.1 s | `flee 10711 10620` (threats 3) |
| 31 | 647 | 74.65 | 2 | 4.20 | failed superseded | 0.6 s | `flee 10711 10620` (threats 3) |
| 33 | 648 | 74.67 | 2 | 4.61 | failed superseded | 1.0 s | `flee 10711 10620` (threats 3) |
| 35 | 648 | 74.73 | 1 | 5.77 | failed superseded | 0.6 s | `goto 10732 10629` (explore, threats 0) |
| 44 | 656 | 74.77 | 1 | 5.22 | failed low health | 33.6 s | `flee 10740 10649` (threats 2) |

**Which goal pre-empted each superseded fight.** One (seq 7) was replaced by the `forage` branch's `loot`, one (seq 35) by the `explore` branch's `goto`, both when every zombie had stepped beyond `DANGER_R` 6 (threats 0); the other four (27, 29, 31, 33) were replaced by `flee`, when a third zombie came within 6 tiles (threats 3 > `MAX_FIGHT` 2). The reading that the zombie stepped beyond `DANGER_R` and `loot` replaced the fight holds for seq 7 only.

- **Fight 7 (game minutes 568–571).** Zombie 10678 (`hasTarget` false on every frame) wandered from 5.9 to 4.59 tiles and back out past 6 (`state.log` seqs 219–280); it never came within `FIGHT_R` 3, so the fight only waited, the character still at (10721.5, 10630.5). No damage.
- **Fight 27 (591–646): a 210 s standoff.** Zombie 10661 (`hasTarget` true) approached to 2.74 tiles and **stood there for 1041 consecutive frames** (seqs 809–1861, position (10732.4, 10642.4)); the character stood at (10730.98, 10640.04) on all 1050 of the fight's frames, `moving` false, `action.n` 0. At 2.74 tiles the zombie was inside `FIGHT_R` 3, so by the code the Lua faced it and called `DoAttack` on its 1200 ms cadence (lines 589–595) without closing the distance: the fight goal has no approach step. The frames record no swing and no zombie health, and the bat's condition stayed 15, so whether any swing landed is not read here; what the frames do show is endurance falling 0.951 → 0.318 and pain rising 3.6 → 40.3 while health held at 74.2–75.1 (8 `hit` events of 0.77–0.78 each, each recovered within the next minutes). Neither party moved until other zombies arrived.
- **The flap (game minutes 646–648, `decision.log` lines 622–637, 7.6 s of driver clock).** Zombie 10662 hovered at 5.8–6.1 tiles, the `DANGER_R` boundary (`state.log` seqs 1864–1908), so the threat count alternated 3 and 2 on successive ticks and the policy sent flee, fight, flee, fight, flee, fight, flee, fight (command seqs 28–35): 4 flees and 4 fights in 7.6 s, each superseded within 0.5–2.1 s. The flees each walked a few steps (the character drifted from (10731.0, 10640.0) to (10729.2, 10637.3)), which took all three zombies past 6 tiles, so the last fight (35) gave way to `explore`'s `goto 10732 10629`, which walked away from them; they fell behind to 12 tiles by game minute 650.
- **Fight 44 (656–665) and the death.** Zombie 10670 closed from 5.0 tiles to 0.8 in 3.4 s of client clock (`state.log` seqs 2135–2152); 10673 joined; for most of the fight (108 of its 168 frames) the nearest zombie was under 1.0 tile, and the threat count read 1 or 2 on every tick (`decision.log` lines 694–758: fight with threats 2 on 56, 1 on 9), never above `MAX_FIGHT`, so the policy held the fight while health fell 74.77 → 39.67 (22 `hit` events; `BLEEDING` moodle rising 0 → 4 from game minute 661). The character entered this fight with endurance 0.251 (the standoff's cost) and left it at 0.198. At 39.67 < 40 the Lua failed the fight `low health` (event seq 2328, game minute 665) and the policy sent `flee 10740 10649` (line 759: health 39.7, threats 2, nearest 0.79).
- **The flee (command seq 45, 665–670, 18.2 s of client clock, `state.log` seqs 2331–2461).** The character walked from (10715.79, 10628.15) to (10713.58, 10654.63), about 26.5 tiles south (the Lua's re-aim, 8 tiles from the centroid, overrode the policy's target to the east); `running` and `sprinting` read false on all 92 of its frames, although the flee's walk asks for a run (line 137); the two zombies kept 0.72–1.78 tiles behind it the whole way, and health fell 39.67 → 0 in 37 `hit` events of 0.73–1.08 (mean 1.07), one every third or fourth frame, with `BLEEDING` 4. On the frame whose health read 0 (seq 2461) the flee read `failed cornered`: the goto under it fails `dead` once health reads 0 (line 130) and the flee maps any end but `done` to `cornered` (line 638), so this `cornered` is the death read through the flee, not a dead end in the map (an inference from the code and the coincident frame).
- **Flees and their outcomes**: 5 sent; 4 (seqs 28, 30, 32, 34) superseded by a fight after 1.5, 0.5, 0.5 and 1.0 s; seq 45 ended `cornered` at the death. None reached its square.

**Health over the session** (`state.log` frames and `hit` events):

| game minutes | health | what the frames show |
|---|---|---|
| 559–573 | 100 | looting; fight 7 at a distance |
| 574–587 | 100 → 74.55 | **no zombie within 12 tiles on any frame** (`nZombies` 0; zombie 10678 left at 572, the next entered at 589); the character looting (command seqs 10–20); 24 `hit` events of 0.78–3.15 each (mean 0.93); `INJURED` moodle 1 from game minute 586; pain 0 → 2.5 |
| 588–659 | 74.2–75.1 | flat: the standoff, the flap, loot and explore; 9 `hit` events of 0.77–0.78, each recovered |
| 659–665 | 74.25 → 39.67 | fight 44, zombies under 1 tile |
| 665–670 | 39.67 → 0 | the flee, two zombies within 0.7–1.8 tiles |

The first quarter of the character's health was lost **with no zombie in sense radius**: 25.45 points over game minutes 574–587, while the loot goals moved items into the inventory (`items` 37 → 70 over the same minutes). The needs table's 95.2 at game minute 577 and 74.4 at 593 sit inside and after this stretch, not in a fight: fight 7 did no damage and fight 27 began at 74.88. The cause is not read by these files: the frame carries no inventory weight, no body-part wounds and no damage source, `BLEEDING` read 0 throughout the stretch, and the console and server logs are not evidence here. It was the largest single loss before the last fight and is the run's first open question.

## 5. Per-tick cost over the session

`loop.cost`: `n` 2080, `p50` 1, `p99` 2, `max` 7 (`c_grade.txt` `cost_n`, `cost_p50`, `cost_p99`, `cost_max`) over the summed `COST_KEYS` (`pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs`) of every frame read, each leaf an integer difference of `getTimestampMs` stamps on a 1 ms clock (a 2 is any span of about 1–2 ms; p50 and p99 are bounds, not values). From the same 2080 frames in `state.log`: counts 0:783, 1:992, 2:285, 3:13, 4:3, 5:3, 7:1; mean 0.786 ms per frame tick (by leaf: `pollMs` 0.209, `actMs` 0.081, `scanStepMs` 0.009, `senseMs` 0.236, `linkMs` 0.251).

- **Against Stage A** (`testing/artifacts/a_pipe_4-20261026-181848/GUIDE.md` § 2, the same Lua at `942859f2`, the 5 Hz window, idle and goal-free): `tickMs` p50 1, p99 2, max 3, mean 0.777 over 300 frames. The survival loop at the same 5 Hz, with goals, scans and up to four zombies in sense, reads the same p50 and p99 and a mean within 0.01 ms; its tail is longer (max 7).
- **The tail.** The five frames reading 4 or more on `pollMs` alone or with it (seqs 629, 693, 1917, 2043, 2077: totals 4, 5, 7, 5, 5, `pollMs` 4–5) each directly follow an `ack` line (seqs 628, 692, 1916, 2042, 2076; command seqs 18, 21, 36, 40, 42): the tick that read a new command and started its goal. The other two over 3 are seq 4 (`linkMs` 2 + `senseMs` 2) and seq 73 (`scanStepMs` 3 during the first scan). Seven frames in 2080 read 4 or more.
- **Errors**: `lua_errors` 0, `loop.lua_errors_per_min` `{}`, `c_grade.txt` `lua_errors_max_per_min` 0, `client_lua_errors` 0, `lua_error_lines` empty.
- **Memory**: `loop.memory` (and `memory_reads`) one read, `free_gb` 2.69 at loop second 300.0148241519928; `memory` 2.49 GB at ready.
- **Server**: `loop.server_polls` 7, `loop.server_fails` 0, `loop.players_error` null; `steps` holds 7 `stats.all` and 7 `players` calls, each answered.

## 6. The dense run

**It did not run.** Spec § 4.3 runs `c_survive_dense.py` (profile `agent-dense.toml`, fixture `agent-dense`, Zombies = 4, Normal) only after the first run survives (a `day_cap` or `budget` stop); this run stopped on `death` at loop second 407.4, game minute 670, so the condition was not met and there is no `DENSE_c_survive-20261026-183905` artifact to compare.

## Stage C run 1 conclusion

The loop held for the whole life: 795 planner ticks at 117 a minute, 45 goals sent and every one acked and seen to end, a gapless log of 2462 lines, 0 Lua errors, 7 of 7 server polls answered, and a per-tick cost at the Stage A 5 Hz reading (p50 1, p99 2, mean 0.786 ms; max 7 on a goal-start tick). The character died 407 s into the loop at game minute 670, 109 game minutes after the loop began, of zombie damage: hunger, thirst and fatigue stayed under 0.09, so `eat`, `drink` and `sleep` were never asked and stay unread live. `loot` worked (16 of 21, 70 items), and its three `not adjacent` failures are the Stage B neighbour rule picking a `solidTrans` square. The two goals that ran live for the first time never finished `done`, and the run shows four ways they lost: (1) `fight` swings only within 3 tiles and never approaches, so it stood 210 s and spent two-thirds of its endurance against a zombie that stayed at 2.74 tiles; (2) a zombie on the 6-tile `DANGER_R` boundary flapped the policy between `fight` and `flee` 8 times in 7.6 s; (3) the policy holds a fight against two grabbing zombies until health falls under 40, and the last fight cost 35 points of health in 34 s; (4) the flee walked rather than ran, at no faster than the zombies, which stayed within 1.8 tiles until the death. Separately, a quarter of the character's health (100 → 74.55) was lost during looting with no zombie within 12 tiles, from a cause these files do not show.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character, one death. |
| every wall-clock leaf, by one wildcard sentence: `wallMs`, `startWallMs`, `end.wallMs`, `wallS`, `startS`, `*PyMs` (`loop.startPyMs`), `wall`, `wall_*`, `*_wall`, `epoch_ms_*`, `took`, `phase_walls.*`, `notes[*].wall`, `timeline`, `wall_seconds`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `hello_wait_ms`, `client_seen[*].*`, `memory[*].wall`, `memory_wait[*].wall`, `loop.memory[*].wallS`, `memory_reads[*].wallS`, `steps[*].*wall*`, `loop.death.wallS`, `stop.wallS`, `loop.wallS`, every `decision.log` `wall` and every `state.log` `wallMs`, in `c_survive.json`, `c_grade.txt`, `decision.log` and `state.log` (wildcard) | host epoch ms and seconds | This host's timing, cited only as a difference within this run (the survival time, a fight's duration), never as a reading. |
| `loop.cost.*`, `c_grade.txt` `cost_p50` 1, `cost_p99` 2, `cost_max` 7, and every frame's `cost.*Ms` leaf | integers 0–7 | Quantised to a 1 ms clock: cite a small value as a bound, never a value, and the 0.786 ms mean only as this clock's mean of the measured spans, never as one tick's cost or the tail. |
| `loop.last_decisions`, `loop.death.last_decisions`, `c_grade.txt` `last_decisions` and `deaths[*].last_decisions` | ten `decision.log` lines | A log excerpt, not a reading; cite `decision.log` by line. |
| `c_grade.txt` `report_lines` "client-server hunger max diff 0.000" | `%.3f` of 0.000121 | Rounded for display; the reading is `needs_summary.hunger_client_server_max_diff` 0.00012149382382631302. |
| `readings.start_kit.*`, `world_changes`, the RCON `additem` and the `weapon.equip` step | the harness's own writes | The harness gave the character its bat; not a reading of the game. |
| `c_grade.txt` keys reading `null` or absent for this stop | — | `grade_c` marks a reading the artifact lacks as None; none of this guide's numbers rest on one. |
| the `hit` events as zombie hits | 92 events | Each is a health drop over 0.5 between frames (`PZAgent_Sense.lua` lines 126–127), whatever its cause. |
| the `cornered` detail of command seq 45 as a map reading | `failed cornered` | It coincides with the death frame and is, by inference from lines 130 and 638, the death read through the flee. |
| the sub-goto targets of the three `not adjacent` loots | (10721, 10632), (10724, 10632), (10725, 10633) | Inferred from `adjacentTo`'s rule and the scan; the frames do not carry them. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `verify`, `steps` | the driver's tables and checks | Written before or around the run; not readings. |
