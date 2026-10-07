# Architecture review, hitching: the platform lens

Model: claude-opus-5-5. Read-only review, 2026-10-07. Jar 42.20.4 (the install's `projectzomboid.jar`), read with `C:\Users\Angus\pz-b42\pz.sh`. Tree read at `997ed00`.
Labels: **jar** = a bytecode reading made for this review, cited `Class.method @off Lline`. **row** = an existing register row. **inference** = reasoning from those readings, not measured. **estimate** = a number nobody has measured. Nothing here is a register row yet; a writer who mints one re-reads the cite first.

## Part A. The five platform questions

### A1. The server's main loop, and what a long Lua handler does to it

**One thread does everything, and Lua blocks it.**
- `GameServer.main` builds an `UpdateLimit(100)` and calls `PerformanceSettings.setLockFPS(10)` (jar: `GameServer.main @2565–@2579 L855–L856`). This is the 10-tick lock behind #3346 and #3355.
- Each pass of the loop does the same steps in order:
  1. It drains three packet queues and runs each packet through `mainLoopDealWithNetData` (jar: `@2703–@3307 L883–L952`). The queues are high priority, then player updates, then the general queue. `OnClientCommand` handlers run here, inside the packet handling.
  2. If `UpdateLimit.Check` is false, it sleeps `clamp(5 ms − time since the pass started, 0, 100)` and starts the next pass (jar: `@3360–@3421 L961–L970`).
  3. If the check is true, it runs one frame: `IngameState.update` (jar: `@3740 L1024`), then the player list, fast-forward, connections, `NetworkPlayerManager.update` (row #2402) and the rest.
- Lua events are synchronous on that thread. `LuaEventManager.triggerEvent` calls `Event.trigger` directly when it runs on the main thread, and queues the event only otherwise (jar: `LuaEventManager.triggerEvent(String) @27–@48 L244–L248`). `Event.trigger` runs each callback in registration order through `LuaCaller.protectedCallVoid` (jar: `Event.trigger @32–@89 L31–L36`).
- **So every microsecond of a mod's handler is a microsecond of the frame.** Until the handler returns, nothing else runs: no network packet, no zombie AI, no player sync.

**The order inside one frame.** `IngameState.updateInternal` runs these steps in this order:
1. `OnTickEvenPaused` (jar: `@56–@67 L1342`).
2. `IsoWorld.update` (jar: `@1064–@1067 L1508`). The per-player updates run here, and so does the `CalculateStats` hook.
3. The GEM, Animal and Radio updates.
4. `UpdateStuff`. This calls `GameTime.update` (row #2401), which fires the clock events.
5. `onTick`, which fires `OnTick` (jar: `IngameState.onTick @0–@11 L1615`; row #2401).

So the minute event and `OnTick` fire in the same frame, the minute first.

**Does the server catch up after a long tick, or drop the time? It catches up, up to 300 ms.**
- `UpdateLimit.Check` returns true once more than `delay` has passed since `last` (jar: `UpdateLimit.Check @0–@60 L43–L52`). It then does one of two things:
  - **Up to 3 × delay late (300 ms at the lock):** it sets `last += delay`. The next frame is due at once, so the server runs frames back to back until it is back on schedule.
  - **More than 300 ms late:** it sets `last = now`, and the backlog is dropped.
- The game clock does not read wall time on the server. `GameTime.update` advances the time of day by `(1 / minutesPerDay / 60) × getMultiplier() / 2` a frame (jar: `GameTime.update @469–@486 L519`). `getMultiplier` multiplies by `fpsMultiplier` (jar: `GameTime.getMultiplier @110–@116 L997`). `fpsMultiplier` is 60 ÷ a smoothed fps, and the smoothing falls by 5 % of the gap and rises by at most 1 a frame (row #2797; jar: `GameServer.main @4377–@4424 L1118–L1123`).
- The arithmetic for one 150 ms frame (inference): the smoothed fps moves from 10 to 9.83, and the catch-up frame lifts it about 1. So **one spike up to about 200 ms costs the world clock almost nothing**: the frame count per second holds and each frame's game time barely moves.
- Sustained overload is a different case. When every frame runs long (more than 300 ms behind), whole frames are dropped and the world clock runs slow (inference). Under the burst design, sleep fast-forward or `settimespeed` reaches that state, because there a minute event fires every tick (#3348–#3350).

**What a 50–100 ms server spike does to a player** (inference from the loop; nothing is measured client-side):
- **Delayed actions.** Packets that arrive during the frame wait in their queues until the next pass. A client's action, such as a timed-action completion, a hit or a door, is answered up to the spike's length late.
- **Stalled world updates.** The world's server-side simulation (zombie AI, other players' relays) and `NetworkPlayerManager.update` (row #2402) run after the long frame. Remote entities then show a gap of the spike's length, and the catch-up frame brings a burst of updates. At DayLength 1 a once-a-minute spike lands every 0.63 s, about 1.6 Hz: a periodic stutter, not one hitch.
- **The owning player's own walk should not rubber-band.**
  - On a dedicated server every player is remote.
  - `IsoPlayer.updateRemotePlayer`'s server arm copies `NetworkPlayerAI.moving` from the client's data and returns true on every remote path (jar: `IsoPlayer.updateRemotePlayer @0–@59 L7352–L7368, @1691 L7592`).
  - So the server follows the client's movement and does not drive it. Whether anti-cheat, which runs every frame (row #2861), corrects a position after a stall is unread.
- **The packet-drop guard.** While it handles the general packet queue, the loop checks every 10 packets whether more than 70 ms have passed since the pass started. If so, it **discards the rest of that pass's general queue**. It also logs and posts to admin chat "Server is too busy… Server is closed for new connections", and holds a `droppedPackets` counter that refuses connections until it decays (jar: `GameServer.main @3145–@3229 L936–L945, @3342–@3357 L959`).
  - The frame does not count toward the 70 ms, because the pass's timer starts at the top of the loop (jar: `@2695 L879`).
  - What counts is a backlog that piles up behind a long frame, plus **any Lua run inside `OnClientCommand`**.
  - So mod work moved into a command handler risks lost packets, which a frame spike does not (inference).

**The engine has its own frame-time counters, and Lua can read them.**
- `StatisticManager.update` is called every frame with a millisecond interval (jar: `GameServer.main @4430–@4435 L1126`). It feeds `PerformanceStatistic.addUpdate`, which keeps `min-`, `max-` and `avg-update-period` in ms and an `fps` counter (jar: `PerformanceStatistic.<init> @102–@155`; `addUpdate`).
- They are refreshed into a Lua table every `MultiplayerStatisticsPeriod` seconds. The default is 1, the range 0–10, and 0 disables it (jar: `StatisticManager.update @7–@44 L179–L181`; `ServerOptions.<init> @2386–@2396`).
- The Lua global `getPerformanceLocal()` returns that table (jar: `LuaManager$GlobalObject.getPerformanceLocal @0–@3 L3101`).
- Two inferences that a live read must confirm:
  - The interval is the gap between frame ends.
  - The max is per window.
- `getServerFPS()` is a constant 10 (jar: `L9962`), so it is useless as a measure.
- Separately, `Event.trigger` times every callback and warns `SLOW Lua event callback … %dms` above 250 ms, but only with the debug option `checks.slowLuaEvents` on (jar: `Event.trigger @17–@148 L30–L39`). That threshold is too coarse for this question.

### A2. Every Lua-visible scheduling primitive on the server, and when each fires

| primitive | where and when it fires | spreads work? |
|---|---|---|
| `OnTickEvenPaused` | Once a frame, first thing in `updateInternal`, even when paused (jar `@56 L1342`). | Per tick, like `OnTick`. It is earlier in the frame, which makes it a frame-start timestamp. |
| `OnTick` | Once a frame, last thing (jar `IngameState.onTick L1615`; #2401). 10 Hz at the lock, 6.27 ticks a game minute at DayLength 1 and 37.46 at DayLength 4 (#3346, #3347). | **This is the only clock that fires every frame on the server.** |
| `EveryOneMinute` | At most once per `GameTime.update` (#3348). Under a fast clock it fires once a tick (#3349, #3350). | It does not spread work: everything registered on it runs in one frame. |
| `EveryTenMinutes`, `EveryHours`, `EveryDays` | **The same `GameTime.update`, the same frame, as the minute.** The order is `EveryDays` (jar `@983 L596`, `@1108 L611`), `EveryHours` (`@1199 L628`), `EveryTenMinutes` (`@1368 L658`), then `EveryOneMinute` (`@1407 L665`). The ten-minute frame also runs vanilla's `ErosionMain.EveryTenMinutes`, `ClimateManager.updateEveryTenMins` and `updateRoomLight` (jar `@1353–@1365 L654–L657`). | **Moving work to a slower event stacks it on a minute frame.** It does not spread it. The ten-minute frame is already vanilla's heavier one. |
| `OnPlayerUpdate` | **Never on a dedicated server for a connected player.** `updateInternal2` returns at `L2391` or `L2410`, once `updateRemotePlayer` returns true, before the trigger at `@1141 L2438`. `updateRemotePlayer` returns true for every remote player on the server (jar: `IsoPlayer.updateInternal2 @859–@942 L2389–L2410, @1141 L2438`; `updateRemotePlayer @20–@48 L7360–L7364, @1691 L7592`). | No. The events table's "client" side agrees. |
| `OnPlayerMove` | Server only, per remote player per frame while the player moves (#2245). | Per tick, and only while moving. It cannot be a scheduler. |
| `Hook.CalculateStats` | Per player per frame, inside `IsoWorld.update`. It replaces vanilla's stat update (#2238). | Per tick; withdrawn under Decision 1. |
| `OnClientCommand` | Per client packet, between frames, in the packet passes. | **This is the one non-`OnTick` way to spread work.** A client-paced pump (each client asks once every N seconds) spreads work by the clients' own phases. It counts toward the 70 ms drop guard above, and a silent client stops its own minute, so it needs a server fallback. Inference; never run. |
| Timers | **None.** No timer API is exposed. The clocks are `getTimestampMs` and `getTimeInMillis` (both `System.currentTimeMillis`, 1 ms; jar `GlobalObject.getTimestampMs L7810`) and `getTimestamp` in seconds. Kahlua's `OsLib` has `time`, `difftime` and `date`, and no `clock`. No `nanoTime` reaches Lua. | A wall-time budget is good only to 1 ms, so a scheduler's budget is counted in players, with milliseconds only as a coarse cap. |
| Coroutines | `CoroutineLib` is registered in the Lua environment (jar `J2SEPlatform.setupEnvironment @51`). `yield` needs the frame's `canYield` (jar `Coroutine.yieldHelper @0–@6 L371`). Yielding across a Java-entered frame, which is how `pcall` and `NR.call` enter, is expected to fail. That is inference: the flag's setter was not read. | A coroutine is still resumed from `OnTick`, so it adds no new clock. It could slice one player's minute below 1.6 ms. That is not needed while one player is the scheduling unit. |

**Is `EveryOneMinute` "the same tick for everything"?** Yes: every handler on it, every handler on the coinciding ten-minute, hour and day events, and vanilla's own minute-boundary work run in one frame. Every player's day close (the 07:00 close, `NR_Server_Metabolism.lua:303`, `NR_Server_Effects.lua:481–483`) also falls in the same game minute for everyone. So a design that runs every player at the same minute stacks it in one frame. A drain spreads it over the minute's ticks.

### A3. Lua garbage collection on Kahlua

**Kahlua has no collector of its own.** A Lua table is a `KahluaTableImpl` wrapping a `java.util.LinkedHashMap` (jar: `J2SEPlatform.newTable @0–@14 L38`; `KahluaTableImpl.<init>(Map) L51–L53`). Every table, closure and boxed number is a Java object, collected by the JVM's collector.

**The server runs ZGC on Java 25.**
- The shipped `ProjectZomboidServer.bat` passes `-XX:+UseZGC -Xmx3072m`. The bundled runtime is Zulu 25.0.1 (`jre64/release`). The harness boots the same flags (`testing/pzt/server.py:43`).
- From the JVM, not the jar (inference): ZGC on JDK 25 is generational and concurrent. Its pauses are sub-millisecond, and they do not grow with the heap or with how many objects survive.
- The risk is an **allocation stall**: the heap nears `-Xmx` faster than ZGC can reclaim it. That is not stop-the-world, but the allocating thread waits. Table churn from 60 players' minutes is very unlikely to reach that on 3 GB, but no reading exists.

**One real hazard.**
- `collectgarbage()` with no argument, `"collect"` or `"step"` calls `System.gc()` (jar: `BaseLib.collectgarbage @12–@40 L449–L451`). Under ZGC that asks for a full cycle, and the calling thread (the server's main thread) waits for it to finish (JVM inference).
- `collectgarbage("count")` returns the JVM's used heap, not Lua's (jar `@41–@102 L454–L461`).
- The mod has no `collectgarbage` call (grep of `mod/`).
- A one-line lint rule in `tools/kahlua_lint.py` would keep it out. That is a suggestion; nothing was changed.

### A4. Network cost and batching

**`sendServerCommand` sends one packet per call, with no batching.**
- The player form looks up the connection (jar: `GameServer.sendServerCommand(IsoPlayer,…) @0–@47 L3547–L3555`).
- The connection form builds the packet **on the main thread**: two `putUTF`s, then a walk of the table that logs every value `canSave` rejects, then `TableNetworkUtils.save`, then `PacketType.send` (jar: `sendServerCommand(String,String,KahluaTable,UdpConnection) @0–@152 L3485–L3502`).
- RakNet transmits from its own thread. So the main-thread cost is the serialisation, which grows with the table's keys.

**What the mod sends:**
- The whole mirror, at most once per player per real minute (`NR_Server_Bus.lua:20` `PUSH_GAP_MS = 60000`; the send is at `:39`), plus one at first sight and one per client request.
- `sendSyncPlayerFields(player, 2)` on a trait or band change (`NR_Server_Strength.lua:155`, `NR_Server_Weight.lua:71`, `NR_Server_Effects.lua:319`). Each reaches one connection (#2603).
- No `ModData.transmit` and no player modData. The store is global modData that is never transmitted (#2416, #1042; `NR_Server_Store.lua:1–3`).

**A burst of 60 sends in one frame** (estimate): 60 serialisations of a mirror of about 100 keys. At a guessed 20–50 µs each, that is 1–3 ms of the frame, and 60 packets to 60 different connections. That is small against the minute itself. Nobody has measured a send.

**A phase-lock to watch.** The push gap is wall time, measured from each player's last push. Players seen in the same minute, such as after a restart, push in the same minute ever after. Under the drain the pushes spread with the work. Under a burst they all land in the burst frame (inference).

**The save.** Global modData is saved in `ServerMap.QueuedSaveAll` (jar: the caller of `GlobalModData.save`, found by refs) and in `GameWindow.save`. The record table is serialised on every world save, and it grows with every player who ever joined (Decision 3). It adds to vanilla's save stall and is unmeasured.

### A5. What the harness can measure today, and what a change would add

**Today:**
- `tick.rate` counts `OnTick` calls over a wall window, as ticks a second (`PZTestKit_Core.lua:1123`). At the lock it is blind to work under about 100 ms a frame (#3355).
- `time.snapshot` reads the clock once.
- `bench.global` brackets n calls with 1 ms `getTimestampMs`.
- `event.watch` timestamps an event's firings, on the client only.
- The x231 instruments (`testing/spikes/instruments/x231_NR_Server_Bench.lua`) time the steps, count the calls, and run the burst and the round-robin with a per-event ms histogram (`e0`–`e5`, `maxMs`).

**What none of them gives:** a per-frame duration, the worst frame, or any load above two real players.

**What a harness change would add:**
1. **`tick.ring <seconds>`, server side.** Arming it appends two listeners, so they run after every mod's handler:
   - `OnTickEvenPaused` stamps the frame start.
   - `OnTick` stamps the frame end and notes whether a minute event fired this frame (`EveryOneMinute` sets a flag).
   - It also reads `getPerformanceLocal()` once a second.

   The result file holds four things:
   - a 1 ms histogram of **busy** time (start to `OnTick`);
   - a histogram of **period** (start to start);
   - the 20 worst frames, each with its minute flag;
   - the engine's `max-update-period` series.

   Busy time misses the work after `OnTick` and the packet passes. The engine's update period covers the whole loop. The two together bracket a frame.
2. **A synthetic-load mode**, appended to a staged copy as x231's instruments were, never to `mod/`:
   - It builds N stand-in records, `synth01`–`synthN`, with the store's own `get`. All of them are bound to one sacrificial real player object, the carrier, so every run makes real Java calls.
   - Each record keeps its own `lastSeen` and world age, so it integrates real elapsed time. That is better than calling `P.work` N times on one record: after its first call that record integrates a zero interval, the 377 µs shape (#3354, #3390), 4× under the in-play cost (#3387).
   - Selectable schedulers:
     - `burst` (all N on `EveryOneMinute`);
     - `rr m` (ceil(N / m) players an event);
     - `drainK` (ceil(N / ticks last minute) players a tick on `OnTick`, and the wall-cycle share under a fast clock, Appendix C S3.2);
     - `drainB b` (run players on `OnTick` until `getTimestampMs` has moved b ms).
   - Each record gets a synthetic eat every few hours, so the Nutrients branches that depend on meals run.
3. **The engine's fake client.**
   - The jar ships `zombie.network.FakeClientManager`, a standalone `main` (`-scenarios=<json> -id=<n>`). It loads `RakNet64` and `ZNetNoSteam64`, reads a scenario file (`connection.serverHost`, `checksum`, `lua`, `player.fps`, `movement`, `movements[]`, `zombies`), and runs the whole login: login, queue, checksum, connect, chunk requests, time sync and player packets (jar: `FakeClientManager.main @15–@355 L2528–L2568`; `FakeClientManager.load`; the `FakeClientManager$Client` method list).
   - The harness's server runs `-nosteam` (`testing/pzt/server.py:244`), which matches the fake client's no-Steam network library.
   - If it still joins on 42.20.4, it gives real server-side `IsoPlayer`s: vanilla's own per-player cost plus the mod's, which is the true 60-player server from two real clients.
   - Whether it joins on this build is unknown, the checksum handshake included (Appendix F's Lua checksum arm).
4. **GC logging.** Adding `-Xlog:gc*:file=<run>/gc.log` to the server's JVM arguments (`testing/pzt/server.py:43`) records ZGC's pauses and allocation stalls for each run.

## Part B. The hitch risks, ranked

The ranking is by worst frame × frequency at 60 players, on the platform's facts above.

### R1. The minute burst under rule 6, and under any fast clock
- **Site:**
  - today, `NR_Server_Players.lua:98` (`EveryOneMinute` → `P.minute`);
  - the Plan 11 design moves `P.work` for every player into that event.
- **Cost:** 74–103 ms for one frame at 60 players (arithmetic on #3387 and #3391; the memo's 60-player section; unmeasured above 2 players). That is a whole tick before vanilla's own work.
- **Frequency:**
  - every game minute: 0.63 s at DayLength 1 and 3.75 s at DayLength 4;
  - **every tick** under sleep fast-forward or `settimespeed` (#3349, #3350).
- **Scaling:** linear in N.
- **Platform consequence** (A1, inference):
  - one late frame, caught up within 300 ms;
  - stalled world updates;
  - a delayed action for every packet that arrived in the frame;
  - a periodic stutter at 1.6 Hz at DayLength 1.
  - Under a fast clock frames overrun every tick, `UpdateLimit` resets, and the world clock slows.
- **Candidate fixes:**
  - (a) a cheaper player-run (Decision 6 (a));
  - (b) a budgeted `OnTick` drain (Decision 6 (b));
  - (c) a round-robin of period m on `EveryOneMinute`;
  - (d) the client-paced `OnClientCommand` pump.
- **Experiments:** X1, X2 and X3 decide between them.

### R2. The clock events coincide, and the 07:00 day close lands at once for everyone
- **Sites:**
  - the event order (A2);
  - `NR_Server_Metabolism.lua:303` (up to `MET.MAX_CLOSES = 7` closes in one run, `:50`);
  - `NR_Server_Effects.lua:481–483`.
- **Cost:** unmeasured. P1 measured a typical awake minute with no day close (Appendix G). The ten-minute frame also carries vanilla's erosion and climate work.
- **Frequency:**
  - the 07:00 close once a game day for every player in the same game minute;
  - a returning player's catch-up of up to 7 closes in one run.
- **Scaling:** linear in N in one frame under a burst. Under a drain it spreads over the minute's 6–37 ticks.
- **Candidate fixes:**
  - keep all mod work off `EveryTenMinutes`, `EveryHours` and `EveryDays`;
  - schedule the day close through the same drain;
  - stagger each player's close minute (that changes behaviour, so it is a golden-trace matter).
- **Experiment:** X4.

### R3. The first-sight burst, which runs inline in the minute event
- **Site:** `NR_Server_Players.lua:62`. `P.minute` fires `P.onFirstSight`, which is Metabolism's body build and one mirror send (`NR_Server_Metabolism.lua:349, :389`), inside the `EveryOneMinute` handler, not the drain. The respawn path does the same at `:109`.
- **Cost:** unmeasured. It includes `store.load` (`fillInPlace`), the body init and a mirror serialisation.
- **Frequency:** once a join; bursty after a server restart, when many players are first seen in one minute.
- **Scaling:** the joiners in that minute.
- **Candidate fix:** queue first sight into the drain, as one more unit of work.
- **Experiment:** X4.

### R4. The packet backlog behind a long frame, and work inside `OnClientCommand`
- **Site:** `GameServer.main L936–L945` (jar); `NR_Server_Bus.lua:45` (the `mirror.request` handler).
- **Cost:** none today. It matters only if the minute moves into command handlers (fix (d) of R1), or if a long frame leaves a backlog over 70 ms.
- **Frequency:** per pass.
- **Scaling:** with the packet rate, which grows with N.
- **Consequence:** packets dropped and new connections refused (A1).
- **Candidate fix:** keep the minute out of command handlers, or cap one handler run a pass.
- **Experiment:** X2 reads the server log for "Server is too busy".

### R5. The mirror push and other sends
- **Site:** `NR_Server_Bus.lua:20, :39`; the three `sendSyncPlayerFields` sites (A4).
- **Cost:** estimated 1–3 ms when 60 sends land in one frame.
- **Frequency:** at most once per player per real minute, and phase-locked (A4).
- **Scaling:** linear in N.
- **Candidate fix:** none needed under a drain. Under a burst, add a per-player jitter to the gap.
- **Experiment:** X5.

### R6. GC and table churn
- **Site:** the whole pipeline's table creation (for example `P.queue = {}` at `NR_Server_Players.lua:49`, `:85`, and the kernels' working tables).
- **Cost:** ZGC is concurrent, and the risk is allocation stalls only (A3, inference).
- **Frequency:** continuous.
- **Scaling:** allocation rate, linear in N.
- **Candidate fix:** reuse tables, but only if X6 shows a stall.
- **Experiment:** X6.

### R7. The global modData save
- **Site:** `NR_Server_Store.lua:110` (the attach). The save itself is vanilla's `QueuedSaveAll`.
- **Cost:** unmeasured; it grows with every player who ever joined (Decision 3).
- **Frequency:** each world save.
- **Scaling:** the total record count, not N online.
- **Candidate fix:** Decision 3's pruning.
- **Experiment:** X7 (cheap).

### R8. The client side (low)
- **Sites:** the panel's `prerender` and `render`, and the moodle column's `render`, read cached values (`NR_Client_Panel.lua:92–123`, `NR_Client_Moodles.lua:171`). The view rebuilds only when the mirror's counter moves, once per real minute.
- **Risk:** low by reading. The client's real exposure is R1's server stutter, not its own Lua.
- **Experiment:** X8 (the client-perceived side of R1).

## Part C. Experiments

The thresholds below are proposals for Angus. "Mod-added busy" means a frame's busy time with the mod's scheduler on, less the same session's baseline with it off.

**X0, the harness change, which goes first.**
- Two pieces, landed in their own commit with the balance check and the regenerated command table (CLAUDE.md § 5):
  - `tick.ring`, with the busy and period histograms, the 20 worst frames and their minute flags, and the `getPerformanceLocal()` series;
  - the `-Xlog:gc*` server flag, behind a profile key.
- **Smoke test:** a 2-player baseline of 10 minutes at DayLength 1, with the mod's scheduler off and then on.
- **Readings:** the busy p50, p99 and max, and the share of frames with a period over 110 ms.
- **Cost:** one harness commit and one short session.
- **Rule:** if the engine's `max-update-period` and the Lua-measured period disagree by more than 2 ms at p99, use the engine's figure as the hitch reading and the Lua busy time only for attribution.

**X1, synthetic load: the four schedulers at N = 20, 40 and 60, live.**
- **Question:** which scheduler minimises the worst frame and its frequency at 60, and does the per-tick drain add more than it removes?
- **Method:**
  - a staged copy with the synthetic instrument (A5 item 2), fixture `two`, `bob` as the carrier;
  - DayLength 1 and DayLength 4 (`time.multiplier` 0.1674, since a live DayLength change did not take, #3394);
  - for each N, 10 game minutes per scheduler: `burst`, `rr 2`, `drainK` and `drainB 10`;
  - a `drainK` arm under `settimespeed 30`.
- **Readings:**
  - X0's histograms, per scheduler and N;
  - µs per player-run;
  - the players served a minute (a starvation check against #3352);
  - world minutes per wall second (clock loss);
  - "Server is too busy" lines.
- **Decision rule for Decision 6:**
  - **Prefer (b):** take the budgeted drain if both of these hold:
    - at N = 60 its mod-added busy is at most 20 ms at p99 and at most 25 ms at max;
    - the burst's minute frames exceed a mod-added 33 ms, or push any period over 133 ms.
  - **Take (c):** if `rr 2` meets the same bounds, and Angus adopts Appendix H's fairer band, (c) at m = 2 is admissible without per-tick work.
  - **Keep rule 6 (a) only if** the burst itself stays at most 25 ms mod-added at N = 60. That needs about 0.4 ms a player-run, against 1.583 today (#3387).
  - **The "does not aggravate" check:** at N = 0 and N = 2, the drain's empty early-out must add at most 0.1 ms to the mean busy, and the drain's summed busy over a minute must be at most 1.1 × the burst's. Otherwise the per-tick drain costs more than it spreads.
- **Cost:** one harness commit (X0), one instrument file, and one session of about 2 h. The repository allows one live session at a time.

**X2, the client stutter: a real burst against a real drain at the largest synthetic N, live.**
- **Question:** does a player notice?
- **Method:** X1's `burst` and `drainK` at N = 60, with `zombie.near 10` around `admin`. A client-side `OnTick` ring on `admin` records each frame's wall time and the position of the nearest zombie and of `bob`.
- **Readings:**
  - the largest gap between position changes of a remote entity;
  - the client's own frame-time histogram;
  - how far the two series line up with the server's minute frames.
- **Rule:** if the burst's gaps of 100 ms or more line up with server minute frames at about 1.6 Hz (DayLength 1) and the drain shows none, the hitch is player-visible, and that backs Decision 6 (b) with evidence.
- **Cost:** a small client harness command, and 30 minutes of the X1 session.

**X3, the fake-client spike (`FakeClientManager`), live.**
- **Question:** can 42.20.4's shipped fake client join the harness server with the mod loaded, and how many?
- **Method:**
  - write a scenario JSON (`serverHost` 127.0.0.1, `checksum`, `player.fps` 10, a radius walk);
  - launch `java -cp projectzomboid.jar zombie.network.FakeClientManager -scenarios=… -id=1` (jar: `FakeClientManager.main`) beside a `pzt run` with fixture `two`;
  - raise the client count in steps of 5.
- **Readings:**
  - the joins in `players`;
  - whether the mod's first sight fires per fake player;
  - X0's ring;
  - the server's memory (`getPerformanceLocal` `memory-used`).
- **Rule:**
  - if 58 fake players hold for 10 minutes, X1's matrix is re-run on real players, and those figures replace the extrapolation;
  - if no fake player joins within one session, drop it, and X1's stand-ins stay the instrument.
- **Cost:** one session, and no harness change unless it works.

**X4, the heavy minutes: the day close, a 7-close catch-up, and first sight, live bench.**
- **Question:** how much heavier are these minutes than P1's typical minute?
- **Method:** in the X1 instrument, time `P.work` for a stand-in record across 07:00, one with `body.dayIndex` 7 days stale, and `MET.onFirstSight` on a fresh stand-in, 200 each.
- **Readings:** µs per run against #3387's 1583.
- **Rule:**
  - a day-close run over 3 × the typical one goes through the scheduler (never the burst);
  - first sight goes into the drain whatever its cost.
- **Cost:** 20 minutes of an X1 session.

**X5, the mirror send cost, live bench.**
- **Question:** what does one `sendServerCommand` mirror cost on the main thread?
- **Method:** time `B.sendMirror` on the carrier 1000 times in the X1 instrument.
- **Readings:** µs per send.
- **Rule:** if 60 sends cost more than 5 ms, the push gets a per-player jitter and is never sent from a burst frame. Otherwise R5 is closed.
- **Cost:** 5 minutes.

**X6, GC and allocation: offline, then live.**
- **Question:** could table churn cause a hitch?
- **Method:**
  - offline in lupa, the `collectgarbage("count")` delta per `P.work` over the golden scenario, as an allocation proxy (Lua 5.1 is not Kahlua: a lower bound);
  - live, X1's N = 60 runs with X0's GC log.
- **Readings:**
  - KB a player-run;
  - ZGC's pause max;
  - the count of "Allocation Stall" lines;
  - whether any pause or stall lines up with a worst frame.
- **Rule:** any stall, or any pause over 1 ms that lines up with a minute frame, starts a table-reuse task. Otherwise R6 is closed.
- **Cost:** about 1 h offline, plus nothing extra live.

**X7, the record table's save size (offline).**
- **Question:** how big is one stored record, and what does the table weigh at 60 and 500 players?
- **Method:** serialise one stored record in lupa (key count and bytes) and multiply out.
- **Rule:** over about 1 MB at 500 players, Decision 3's default flips to pruning on.
- **Cost:** 30 minutes.

**X8, the coroutine and yield check (jar plus one live call; only if sub-player slicing is ever needed).**
- **Question:** can a coroutine yield from inside `pcall` or `NR.call`?
- **Method:** read the setter of `LuaCallFrame.canYield` in the jar; then one `lua.call` of a test function in a staged copy.
- **Rule:** if it cannot, any slicing below one player must yield outside every protected call. Per-player units stay the default.
- **Cost:** 30 minutes.

## Concerns

1. **The current tree's drain starves players beyond the ticks in a minute** (a reading of the code, not measured at N > 2).
   - `P.minute` replaces the queue every minute (`NR_Server_Players.lua:49`), and `P.drain` serves one player a tick (`:82–95`).
   - At DayLength 1, about 6 of 60 players run a minute, and the rest never do. At DayLength 4 it is about 37 of 60.
   - This is #3352's fast-clock starvation at speed 1.
   - So the current tree is not a valid 60-player baseline. X1 must use its own schedulers, and Plan 11 Task 2's share must handle N above the ticks in a minute.
2. **The memo's 60-player spike is linear extrapolation from two players** (#3387, #3391).
   - Vanilla's own per-player server cost at 60 (LOS, zombie AI, packets) is in no reading.
   - The mod's spike lands on top of vanilla's frame, so the absolute frame matters, not only the mod's share. Only X3 (fake clients) reaches that.
3. **Every client-side consequence in A1 is inference from the server loop.** No client reading exists; X2 is the first.
4. **Use the engine's `update-period` counter carefully.** Its argument is presumably the interval between frame ends, and its max is presumably per window. Both are inferred from the bytecode around `L1113–L1126` and need one live read (X0) before anyone quotes them.
5. **The wall clock Lua can read has 1 ms resolution.** A tick histogram is fine at that grain, but a budgeted drain cannot meter work in microseconds. Its budget has to be counted in player-runs, with milliseconds only as a coarse cap.
