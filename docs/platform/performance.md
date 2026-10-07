# Server performance
Verified against 42.20.4 (b0bbce05d5) · 2026-10-07 · scope: what a dedicated server frame is and what a mod's work costs inside it — the loop and its catch-up, the order of a frame and its clock events, the scheduling primitives a mod has, the clocks and the engine's frame counter, Lua tables and the collector, the packet pass and a send, the global modData save and request — how to budget a change against the frame, and the costs measured so far; who owns a value is `mp-model.md`'s, the event roster `lua-platform.md`'s, the time events' place in the lifecycle `server-lifecycle.md`'s, and the instrument `harness.md`'s.

## Rules
<a id="rules"></a>

- Put slow simulation such as nutrient decay on `EveryOneMinute` and never move it to `EveryTenMinutes`, `EveryHours` or `EveryDays` in the hope of lightening the minute frame, never put a server's simulation on `OnPlayerUpdate`, keep a client's per-frame needs on it behind a cheap early-out, and keep steady per-tick simulation off `OnTick`, though a queue drained on `OnTick` that only schedules the minute's work is not ruled out here and which shape is best is open: on a dedicated server `OnPlayerUpdate` never fires for a connected player, while on a client it fires for the local player at each of its updates and the corpus registers it at least 61 times over 43 mods, the slower clock events fire inside the same `GameTime.update` as the minute so work moved to them lands on a minute frame, and `OnTick` is the corpus's expensive tier [#3423/C/inference, #2232/C/C-only, #2959/M/n=1, #3453/C/C-only, #2580/C/snapshot, #3427/C/C-only, #2400/C/C-only, #1080/C/snapshot].
- Budget work that runs for every player in one event as one frame's work, the per-player cost times the player count: an event's handlers all run on the server's main thread inside one frame, the minute event fires at most once a frame, and eighteen ghost records' minutes in one `EveryOneMinute` frame read 18 ms of the frame's busy time at the median and 39 ms at the worst [#3441/C/inference, #3426/C/C-only, #3348/C/C-only, #3405/M/n=1].
- Judge server-side work by the longest frame it makes and how often that frame comes, never by its mean cost: a burst moves the frame's end and not the loop's cadence, and under a burst of eighteen ghost records once a game minute the start-to-start period held at 103 ms at the 99th percentile while the engine's per-window longest frame rose from 112 to 134 ms [#3442/C/inference, #3424/C/C-only, #3406/M/n=1, #3404/M/n=1].
- Read a server frame's length off the engine's counter, the `max-update-period` of `getPerformanceLocal()`, and use Lua's clock only for totals over many runs with their count: every clock Lua reads through the global API and the `os` library is 1 ms or coarser, the engine's per-window longest frame agreed with a Lua frame ring within 2 ms at the 99th percentile, and the counter's `avg-update-period` is no mean [#3443/C/inference, #3432/C/C-only, #3403/M/n=1, #3409/C/C-only].
- Carry a spread queue's unserved players into the next minute rather than rebuilding the queue at each minute event: a queue that serves one player a tick and is rebuilt each minute serves only as many players a minute as the minute has ticks, about 6 at `DayLength` 1 and 37 at `DayLength` 4, and starves the same players every minute [#3444/C/inference, #3439/C/inference, #3346/M/n=1, #3347/M/n=1, #3352/M/n=1].
- Keep per-player records out of global modData unless every connected client may read all of them: any logged-in client can request a global modData table by name and receive it, serialised whole up to the connection's send buffer, a mod cannot refuse the request, and the console save and the autosave serialise every table on the server's main loop [#3445/C/inference, #3417/C/C-only, #3418/C/C-only, #3419/C/C-only, #3420/C/C-only, #2416/C/inference].
- Never call `collectgarbage()` or its `collect` or `step` forms from mod code: each calls `System.gc()` on the calling thread, which for an event handler on a server is the main loop, and its `count` form reports the JVM's heap rather than Lua's [#3446/C/inference, #3435/C/C-only, #3426/C/C-only].
- Keep long work out of `OnClientCommand` handlers: they run inside the server loop's packet pass, and once a pass has run 70 ms the loop drops the rest of that pass's vehicle-physics packets and reports the server too busy [#3447/C/inference, #3429/C/C-only, #3430/C/C-only, #3431/C/C-only].

## How it works

This page is written for the next change to server-side work: it opens with how to budget one, then gives the mechanisms the budget rests on, then the costs measured so far.
Every mechanism here is a bytecode reading, and every cost comes off live sessions with two real players, one of which also ran eighteen ghost records through the real pipeline [#3448/C/C-only] [#3405/M/n=1].
A ghost record is cost and never behaviour: it runs the pipeline against a real player object, so its state is not a player's state [#3405/M/n=1].
Every figure for more players than that is arithmetic, labelled where it is used [#3440/M/arith.].
What a dedicated server fires at boot and the full event roster are [lua-platform.md](lua-platform.md#events)'s, and the time events' place in a player's lifecycle is [server-lifecycle.md](server-lifecycle.md#tick-order)'s.

<a id="budget"></a>
### Budgeting a change

A dedicated server runs one frame every 100 ms on one thread, and every handler a mod registers runs inside the frame that fires it, so a handler's time is frame time [#3424/C/C-only] [#3426/C/C-only].
Nothing else runs on that thread until the handler returns: no packet, no world update, no player sync [#3424/C/C-only] [#3429/C/C-only].
A change is budgeted by four questions, asked in this order.

The first is which frame the work lands in.
The minute event fires at most once a frame, however many game minutes the frame advanced, so a loop over every player inside its handler is one frame's work, the per-player cost times the player count [#3348/C/C-only] [#3441/C/inference].
The minute, ten-minute, hour and day events all fire in the same clock update, so moving work to a slower event stacks it on a minute frame rather than spreading it [#3427/C/C-only].
Of the events in the table below, the two that fire on every frame whatever the players do are `OnTickEvenPaused` and `OnTick`, so spreading a fixed workload across frames means a queue drained from one of them [#3428/C/C-only] [#2401/C/C-only].

The second is how often that frame comes.
A game minute is 6.270 frames on average at `DayLength` 1 and 37.46 at `DayLength` 4, so a minute's burst comes every 0.63 s on the short day and about every 3.75 s on the long one [#3346/M/n=1] [#3347/M/n=1].
Under a fast clock, an admin's time speed or every player asleep, the minute event fires on every frame [#3349/M/n=1] [#3350/M/n=1] [#3351/C/C-only].
A once-a-minute design is therefore an every-frame design whenever the clock runs fast [#3349/M/n=1].

The third is how the cost grows with the player count.
A per-player loop grows linearly, and at sixty players the measured per-run costs put one event's loop at 73.7 to 103.3 ms (arithmetic), about a whole frame before vanilla's own work [#3440/M/arith.].
The same work spread over a minute's frames is about 95 ms a game minute, about 15 % of the server at `DayLength` 1 (arithmetic), so the mean is affordable where the burst is not [#3440/M/arith.].
Read the other way, a burst over N players stays under a frame budget only while one run costs at most that budget divided by N, so keeping a sixty-player event under 10 ms allows about 0.167 ms a run (arithmetic), about a ninth of the 1558.33 µs an in-play run measured [#3441/C/inference] [#3387/M/n=1].

The fourth is the measured cost of one run on a live server, read under [How to measure](#measure).
The verdict is the longest frame the change adds and how often that frame comes, never the mean [#3442/C/inference].
The engine's own counter is the reading of a frame's length, and a Lua timer is a total over many runs with its count [#3443/C/inference].
Offline timings rank a pipeline's blocks by share and never price a frame [#3438/C/inference].

<a id="frame"></a>
### The server frame

`GameServer.main` builds an `UpdateLimit` of 100 ms and locks the frame rate at 10 before its loop [#3424/C/C-only].
Each pass of the loop first handles the queued packets, then runs one frame when the limit's check passes, or sleeps 5 ms less the time the pass took and starts the next pass [#3424/C/C-only] [#3429/C/C-only].
So packets are handled roughly every 5 ms between frames, and a frame runs about every 100 ms [#3424/C/C-only].
The frame itself starts with `IngameState.update`, whose order is [below](#frame-order) [#3424/C/C-only] [#3428/C/C-only].

Lua events are synchronous on that thread.
On the main thread `LuaEventManager.triggerEvent` runs an event's handlers at once through `Event.trigger`, which calls each in registration order inside its own catch, and only a trigger from another thread is queued [#3426/C/C-only] [#0896/C/C-only].
Every handler of an event the frame fires therefore runs inside that frame [#3426/C/C-only].

The loop catches up after a long frame, up to a limit.
The limit's check passes once more than 100 ms have gone by since its stored time and then moves that time forward by one delay, so a late loop runs frames on consecutive passes until it is back on schedule [#3425/C/C-only].
A loop more than 300 ms behind resets the stored time to the present instead, and the frames it missed are never run [#3425/C/C-only].
The game clock advances each frame by a multiplier of 60 over a smoothed frame rate that moves by at most 1 a frame, so a single late frame moves the world clock very little [#2797/C/C-only].

A long frame moves the frame's end and not the loop's cadence.
With two players and the mod's own drain only, the frame's busy time read 1 ms at the median and 9 ms at the 99th percentile, and the frame-start period 100 ms at the median [#3404/M/n=1].
Under eighteen ghost records run in one minute event the minute frames' busy time read 18 ms at the median and 39 ms at the worst, the start-to-start period held at 103 ms at the 99th percentile, and the engine's per-window longest frame rose from 112 to 134 ms at the 99th percentile [#3405/M/n=1] [#3406/M/n=1] [#3404/M/n=1].

What a long frame does to a player is read from the loop and never measured on a client.
A packet that arrives during the frame waits for the next pass, so a client's request is answered up to the frame's length late [#3429/C/C-only].
The player-stats push runs after the frame's `IngameState.update` in the same pass, so it leaves late by the frame's length too [#2402/C/C-only].
Whether a player notices a periodic long frame is [open](#open).

<a id="frame-order"></a>
### Inside a frame: the order and the clock events

`IngameState.updateInternal` fires `OnTickEvenPaused` near its start, runs `IsoWorld.update`, where the per-player updates run, then `UpdateStuff`, whose `GameTime.update` fires the clock events, then `onTick`, which fires `OnTick` [#3428/C/C-only] [#2401/C/C-only].
A live ring confirmed the order on a dedicated server: the minute's work ran between the frame's `OnTickEvenPaused` and its `OnTick` in all 193 minute frames [#3410/M/n=1].
`IngameState.update`, and with it `OnTick`, runs before `NetworkPlayerManager.update` in the same pass [#2402/C/C-only].

One `GameTime.update` fires `EveryDays` at a day rollover, `EveryHours` when the hour changed, `EveryTenMinutes` when the ten-minute block changed, and `EveryOneMinute` when the minute stamp changed, in that order [#3427/C/C-only] [#2400/C/C-only].
Vanilla's own erosion, climate and room-light updates run in the ten-minute arm just before its Lua event, so the ten-minute frame is already vanilla's heavier one [#3427/C/C-only].
`EveryOneMinute` fires at most once per update, however many game minutes the update advanced [#3348/C/C-only].
`EveryDays` takes one of two paths: with the client flag clear, as on a dedicated server, the update rolls the day over once and fires it once, while on a client it loops while the clock sync's day count is above 0 and fires it once for every day it takes off [#3449/C/C-only].

```
GameServer.main pass
  packet pass                         high priority, player updates, vehicle physics (70 ms guard)
  UpdateLimit.Check (100 ms)          false: sleep up to 5 ms, next pass
  IngameState.update -> updateInternal
    OnTickEvenPaused
    IsoWorld.update                   the per-player updates
    UpdateStuff -> GameTime.update    EveryDays, EveryHours, EveryTenMinutes, EveryOneMinute
    onTick                            OnTick
  ...
  NetworkPlayerManager.update         the player-stats push
```

Every player's work on a clock event lands in the same frame as every other mod's work on it and vanilla's own minute-boundary work [#3427/C/C-only] [#3426/C/C-only].
A game-time boundary every player shares, such as a fixed hour of the day, falls in the same game minute for all of them, so a per-player close keyed on it is a synchronised burst unless it goes through the same queue as the minute [#3427/C/C-only].

<a id="scheduling"></a>
### The scheduling primitives

| primitive | when it fires on a dedicated server | spreads work? | rows |
|---|---|---|---|
| `OnTickEvenPaused` | once a frame, first in the frame, even paused | per frame, like `OnTick`; a frame-start stamp | [#3428/C/C-only, #3410/M/n=1] |
| `OnTick` | once a frame, after the clock events | per frame; the queue a spread workload drains from | [#2401/C/C-only, #3428/C/C-only, #3346/M/n=1, #3347/M/n=1] |
| `EveryOneMinute` | at most once per clock update; every frame under a fast clock | no: every handler on it runs in one frame | [#3348/C/C-only, #3349/M/n=1, #3350/M/n=1] |
| `EveryTenMinutes`, `EveryHours`, `EveryDays` | inside the same clock update as the minute | no: work moved there stacks on a minute frame | [#3427/C/C-only, #2400/C/C-only] |
| `OnPlayerUpdate` | on the server never for a connected player, the remote-player branch returning first; on a client for the local player at each of its updates | no | [#2232/C/C-only, #2959/M/n=1, #3453/C/C-only] |
| `Hook.CalculateStats` | on the server once per player update, in place of the seven stat updaters, and never on a client | no: its handler's cost is paid for every player on every frame | [#2238/C/C-only, #2100/M/n=1, #3355/M/n=1] |
| `OnPlayerMove` | only from the server's remote-player update | only while a player moves | [#2245/C/C-only] |
| `OnClientCommand` | per command packet, in the packet pass between frames | paced by the clients, not the server | [#3431/C/C-only, #3429/C/C-only] |
| a timer | none among the readings here | a delay is counted in frames or read off a 1 ms clock | [#3432/C/C-only] |
| a coroutine | `CoroutineLib` is registered in every Lua environment and a `yield` asserts `canYield`; that a coroutine runs only when a handler resumes it is inference | only across the frames whose handlers resume it | [#3451/C/C-only] |

Whether a coroutine can yield from inside a protected call, which is how `pcall` and a handler entered from Java run, is unread: the setter of the frame's yield flag was not read [#3451/C/C-only].

A mod has three shapes for a per-player workload that recurs every game minute.
A burst runs every player in one minute event, and its frame grows with the player count [#3441/C/inference].
A round-robin runs a share of the players in each minute event, so each player runs every few minutes, and that coarser minute changes the simulation it steps [#3391/M/n=1] [#3396/C/inference].
A drain queues the players at the minute event and runs a number of them on each `OnTick`, spreading the work over the minute's frames [#3439/C/inference].
At two players the burst cost 145 ms over 59 events, at most 6 ms in one, and a round-robin of one player an event 105 ms over 61 events, at most 4 ms [#3391/M/n=1].

A drain that rebuilds its queue at every minute event starves players once there are more of them than the minute has frames [#3444/C/inference].
In the worked example, this mod's shipped drain, read off its code, replaces its queue each minute and serves one player a frame, so at sixty players about 6 run a game minute at `DayLength` 1 and about 37 at `DayLength` 4 (arithmetic), the same ones every minute [#3439/C/inference].
The starvation itself was measured only under a fast clock, where the queue served one of two players a minute [#3352/M/n=1].
Which of the three shapes keeps the longest frame lowest at a large player count is [open](#open).

<a id="levers"></a>
### What a mod can do about its frame cost

A mod has five levers on the frame it adds, and each rests on a mechanism above.

- Make one run cheaper: in the worked example the nutrients step is about half of an in-play minute, and it makes 9 of the run's 79 `NR.call` calls [#3387/M/n=1] [#3388/M/n=1]; offline, the seven heal passes are about half of the pipeline's C-Lua time, a heal once after the step changes the golden trace, and a heal once before it keeps the trace and saves 27.7 % [#3411/C/inference] [#3412/C/inference] [#3413/C/inference].
- Spread a fixed workload over the minute's frames with a queue drained on `OnTick` that carries its unserved players forward, rather than running it in one event [#3444/C/inference] [#3428/C/C-only].
- Keep work off the ten-minute, hour and day events, which fire in the minute's own clock update [#3427/C/C-only].
- Keep a push out of a burst frame: each send serialises its table on the main thread, once per receiver [#3437/C/C-only]; a push gap counted in wall time from each player's last push keeps players first seen together pushing in the same minute ever after, and under a burst in the burst frame (inference) [#3456/C/inference].
- Keep a store that grows with every player ever seen out of global modData, where every save serialises it and any client can request it [#3445/C/inference] [#3422/C/inference].

Two more keep a mod from adding a frame by accident.
A mod that asks for a collection asks for it inside its own frame [#3446/C/inference].
A mod whose command handlers run long spends the packet pass that the vehicle-physics guard counts [#3447/C/inference].
A per-frame site is not free either: a queue drained on `OnTick` runs its early-out on every frame of the session, so its own empty check is part of its cost [#3428/C/C-only] [#2401/C/C-only].
Whether that check costs more than the spreading saves at a given player count is a measurement and not a reading [#3442/C/inference].

Moving a per-tick write to the minute has a cost of its own when vanilla moves the stat every tick.
A stat vanilla decays each tick falls between two minute writes, so the value a player carries is a sawtooth whose floor is the target less the fall per tick times the ticks in the gap [#3402/M/n=1].
Under Overlay, PANIC fell about 1.12 a game minute at either clock, linearly whatever its value, and a target of 6.5 written once a minute dropped under 6, the first PANIC moodle threshold, in every gap [#3392/M/n=1] [#3400/M/n=1] [#3401/M/n=1].
The updaters that move a stat each tick are [character-stats.md](../facts/character-stats.md#updaters)'s.

<a id="clocks"></a>
### Clocks and the engine's frame counter

The wall clocks a mod's Lua reads from the global API and the `os` library are 1 ms or coarser [#3432/C/C-only].
`getTimestampMs` and `getTimeInMillis` return `System.currentTimeMillis`, `getTimestamp` returns it in seconds, and Kahlua's `os` library registers only `date`, `difftime` and `time` [#3432/C/C-only].
`getServerFPS` is the constant 10, so it measures nothing [#3432/C/C-only].
A Lua bracket around one short handler reads 0 or 1 ms, so a figure under a few milliseconds is a count of truncations and is read only as a total over its runs [#3432/C/C-only] [#3443/C/inference].
A budget metered in milliseconds inside one handler is therefore good only to 1 ms, and a scheduler's budget is counted in runs, with milliseconds only as a coarse cap [#3432/C/C-only] [#3443/C/inference].

The engine keeps its own frame-period figures, and Lua reads them through `getPerformanceLocal()` [#3409/C/C-only].
Its `max-update-period` and `min-update-period` are the window's extremes and are cleared after each copy into the table, while its `avg-update-period` is set each frame to a twentieth of the gap between the frame's period and itself, so it is no mean [#3409/C/C-only].
The table is refreshed every `MultiplayerStatisticsPeriod` seconds, a server option from 0 to 10 that defaults to 1, and 0 stops the refresh [#3433/C/C-only].
Over about a second's window the engine's longest frame and the longest gap a Lua ring recorded agreed within 2 ms at the 99th percentile, idle and under a burst [#3403/M/n=1].
The engine's figure is the hitch reading; a Lua ring is for attributing a frame's time to the work in it [#3443/C/inference].
A tick-rate count is blind to work that fits under the frame: two players under the takeover handler and without it ticked 10.073 and 10.070 a second [#3355/M/n=1].

<a id="gc"></a>
### Tables and garbage collection

Kahlua has no collector of its own: a Lua table is a `KahluaTableImpl` over a `java.util.LinkedHashMap`, made by the platform the game builds its Lua environment through, so every table belongs to the JVM's collector [#3434/C/C-only].
The server runs on ZGC with a 3 GB heap ceiling [#3436/C/inference].
Over a session of about seven minutes the GC log held 128 pauses, the largest 0.12 ms, and 18 allocation stalls, all at boot [#3408/M/n=1].
So table churn costs the allocating handler's own time, which a step timer already includes, and the risk left is an allocation stall when the heap nears its ceiling [#3436/C/inference] [#3408/M/n=1].

`collectgarbage()`, and its `collect` and `step` forms, call `System.gc()`, and its `count` form reports the JVM's used, free and total memory rather than Lua's [#3435/C/C-only].
On a server the caller is the main thread, so a mod that calls it asks for a full collection inside its own frame [#3435/C/C-only] [#3426/C/C-only].

<a id="packets"></a>
### The packet pass

`addIncoming` puts player-update packets on one queue, vehicle-physics packets on a second and every other packet of a known type on a high-priority queue [#3429/C/C-only].
Each pass handles the high-priority queue, then the player updates, then the vehicle physics, before it checks whether a frame is due [#3429/C/C-only].
Only the vehicle-physics queue has a time guard: every tenth packet the loop checks whether more than 70 ms have passed since the pass began, and if so it drops the rest of that queue and reports the server too busy [#3430/C/C-only].
The pass's time counts from its top, so the two earlier queues' time, a mod's command handlers among it, counts toward the guard [#3430/C/C-only] [#3431/C/C-only].
`OnClientCommand` fires from the server's handler of a client's command packet, which the routing puts on the high-priority queue, so a command handler runs between frames in the packet pass [#3431/C/C-only] [#3429/C/C-only].
A long frame does not trip the guard by itself, because the pass's timer starts after the frame [#3430/C/C-only] [#3424/C/C-only].

<a id="network"></a>
### Sends

`sendServerCommand` serialises its table on the calling thread once per receiving connection and sends one packet each, with no batching [#3437/C/C-only].
The player form looks up that player's connection and sends once, and the form with no player sends to every connection, serialising the table once for each [#3437/C/C-only].
A send addressed to a player reaches that player's own connection only [#2603/C/C-only].
So the main-thread cost of a push grows with the table's keys and with the receivers, and a burst of pushes in one frame is that frame's time [#3437/C/C-only] [#3426/C/C-only].
A send's cost per key is unmeasured [#3437/C/C-only].

<a id="global-moddata"></a>
### Global modData: the save and the request

The console `save` and the autosave run `GlobalModData.save` on the server's main loop, inside the world save, and the quit save runs it on the JVM's shutdown-hook thread [#3420/C/C-only].
The save serialises every table into one heap buffer, 1 MiB at first, growing by 512 KiB and re-serialising the overflowing table on each overflow, and the world save sends clients a pause between its steps after 600 ms [#3421/C/C-only].
A record of this mod's shape is about 10.8 KB in the save's format, so a store of 500 such records is about 5.4 MB, held for every player who ever joined unless the mod prunes it [#3422/C/inference].
Any logged-in client can request a global modData table by name and receive it, serialised whole up to the connection's send buffer, and a mod cannot refuse the request [#3417/C/C-only] [#3418/C/C-only].
A reply larger than the connection's 1,000,000-byte send buffer goes out truncated [#3419/C/C-only].
Keeping only a record's inputs makes it about a fifth smaller, 8,774.2 bytes against 10,807.8 on average, and it still grows with every player ever seen [#3422/C/inference].
A server-side transmit sends the whole named table to every connection [#2416/C/inference] [#2398/C/C-only].
A whole record survived a clean quit and reload leaf for leaf, the file then 10965 bytes [#3275/M/n=1].
The lifecycle of the store is [server-lifecycle.md](server-lifecycle.md#global-moddata)'s, and the request route [mp-model.md](mp-model.md#routes-client-to-server)'s.

<a id="costs"></a>
### Measured costs

Every live figure is one session with two real players at `DayLength` 1 unless the row says otherwise, and every per-run figure is a total over its runs divided by their count [#3387/M/n=1] [#3443/C/inference].

| reading | figure | rows |
|---|---|---|
| ticks in a game minute | 6.270 at `DayLength` 1, 37.46 at `DayLength` 4 | [#3346/M/n=1, #3347/M/n=1] |
| one player's slow minute in play | 1558.33 µs a run over 240 runs, the nutrients step 192 of 374 ms | [#3387/M/n=1] |
| the same under `settimespeed 30` | 1358.09 µs a run over 606 runs | [#3389/M/n=1] |
| the same at an unchanged world age | 430, 389 and 333 µs a run; 390, 395 and 345 in an earlier session | [#3390/M/n=1, #3354/M/n=1] |
| engine calls a run | 79 `NR.call` calls | [#3388/M/n=1] |
| a burst and a round-robin at two players | 145 ms over 118 runs, at most 6 ms an event; 105 ms over 61, at most 4 | [#3391/M/n=1] |
| the takeover stat handler | 19, 21 and 18 µs a call, each player each frame | [#3353/M/n=1] |
| the pure fast step | 4.36 µs a call | [#3356/M/n=1] |
| three stat writes | 0.8, 0.9 and 0.6 µs a call | [#3373/M/n=1] |
| one player's vanilla `update()` without a stat hook against with an empty one, at `DayLength` 4 | 22.8 against 14.8 µs, and two more pairs | [#3386/M/n=1] |
| the tick rate with and without the takeover | 10.073 and 10.070 a second | [#3355/M/n=1] |
| an idle frame, two players | busy 1 ms median, 9 ms p99, 13 ms max | [#3404/M/n=1] |
| a minute frame carrying eighteen ghost runs | busy 18 ms median, 34 ms p99, 39 ms max | [#3405/M/n=1] |
| one ghost run | 2991 ms over 3474 runs | [#3405/M/n=1] |
| the engine's longest frame against a Lua ring | within 2 ms at p99, idle and under the burst | [#3403/M/n=1] |
| ZGC over one session | 128 pauses, at most 0.12 ms; stalls only at boot | [#3408/M/n=1] |
| one stored record | 10,807.8 bytes on average | [#3422/C/inference] |
| sixty players' minutes in one event (arithmetic) | 73.7 to 103.3 ms; about 51.7 ms on the ghost basis | [#3440/M/arith.] |
| sixty players' minutes spread over the minute (arithmetic) | about 95 ms a game minute | [#3440/M/arith.] |

The sixty-player rows are linear extrapolation from two players, and vanilla's own per-player cost at that load is in no reading, so the absolute frame there is unknown [#3440/M/arith.].
The ghost run read about half the in-play run, so the two bases bracket the per-run cost rather than agree on it [#3405/M/n=1] [#3440/M/arith.].

<a id="measure"></a>
### How to measure

The harness reads a frame's length and a load's cost on a live server; its commands are listed in [harness-commands.md](../reference/harness-commands.md) and the instrument is [harness.md](harness.md).
`tick.ring` stamps each frame at `OnTickEvenPaused` and `OnTick` and reports the busy time and the period, for attributing a frame's time [#3403/M/n=1] [#3410/M/n=1].
`perf.local` samples the engine's per-window longest and shortest frame once a window, the hitch reading [#3403/M/n=1] [#3409/C/C-only].
`ghost.load` runs a number of ghost records through the real pipeline under a named scheduler, for cost at a player count two clients cannot reach [#3405/M/n=1] [#3407/M/n=1].
`bench.global` brackets many calls of one function with the 1 ms clock and reports the cost a call [#3432/C/C-only].
A profile's `gclog` key writes the server's GC log beside the run, for lining a pause or a stall up with a frame [#3408/M/n=1].
Offline, the kernel's host is C Lua, so an offline profile ranks blocks by share and a live reading prices them [#3438/C/inference].

`ghost.load <N>` takes its scheduler as `burst`, `rr<m>`, `drainTicks`, `budget<ms>` or `shipped`, `ghost.stats reset` zeroes the load's counters for the next arm, and `ghost.bench <n>` arms a bench of interleaved ghost and real-player minutes that `ghost.bench read` replies [#3455/C/inference].
The bench runs each record at most once a minute event and never at a zero interval, because a run at an unchanged world age reads the zero-interval shape of the work, and `ghost.bench` carried the same zero-interval bias before 30bba11 [#3455/C/inference].
That shape is about four times under an in-play minute: back-to-back runs read 390, 395 and 345 µs and 430, 389 and 333 µs a call in two sessions, against 1558.33 µs a run in play [#3354/M/n=1] [#3390/M/n=1] [#3387/M/n=1].
The slow minute's per-step profiler and `NR.call` counter are kept at `testing/spikes/instruments/x231_NR_Server_Bench.lua`, an instrument appended only to a staged copy and never to `mod/` [#3454/C/inference].
A step's total there is a sum of 1 ms truncations, so a small step's per-run figure is indicative only: in play the `nutrients` total of 192 ms carried about ±6.2 ms (arithmetic) and the `bus` total of 2 ms about ±1.4 ms (arithmetic) [#3387/M/n=1].
Set `DayLength` in the profile and never at run time: set through `SandboxOptions:set` on a live server it read back 4 and left the clock at 6.47 ticks a game minute [#3394/M/n=1].
The engine's own slow-handler warning is no instrument for this: `Event.trigger` warns `SLOW Lua event callback` only for a call over 250 ms and only while the debug-only option `SlowLuaEvents`, created off, is on [#3450/C/C-only].
The jar also ships a fake client, `zombie.network.FakeClientManager`, whose `main` takes `-scenarios=<file>` and `-id=<n>`, loads the `ZNetNoSteam64` library and reads a scenario's server host, checksum, Lua, frame-rate and movement keys, and the harness's server runs `-nosteam`; whether it joins a server of this build is [open](#open) [#3452/C/C-only].

## Walls and bounds
<a id="walls"></a>

Every live cost here is one session with two real players on one host, so each is a reading of that host and not a bound for any other [#3387/M/n=1] [#3405/M/n=1].
A ghost load is cost and never behaviour, and its runs share two real player objects, so it carries the mod's per-run cost and none of vanilla's per-player cost [#3405/M/n=1] [#3440/M/arith.].
Every figure for sixty players is linear arithmetic on those readings, and the frame vanilla itself takes at that load is unread [#3440/M/arith.].
Every consequence for a player of a long server frame is read from the loop, and no client-side frame or position was measured [#3429/C/C-only] [#2402/C/C-only].
The mechanisms are bytecode readings of one build, and a build bump moves their offsets and may move their behaviour [#3424/C/C-only] [#3427/C/C-only].
The clocks reading covers the global API and the `os` library only; a finer clock exposed elsewhere is not excluded [#3432/C/C-only].
The packet guard's effect on a connection was not read beyond its log line and its counter [#3430/C/C-only].
The scheduler shapes are compared live at two real players only [#3391/M/n=1].
The record size is an offline model of this mod's records in the save's format, corroborated by one live record's leaf count [#3422/C/inference] [#3275/M/n=1].
The arithmetic for sixty players assumes a run costs the same whatever its interval, which one fast-clock session supports and nothing at load tests [#3389/M/n=1] [#3440/M/arith.].
Not covered: a listen server or single-player, a client's own frame time, a session driven by the engine's fake client, whether a coroutine can yield across a protected call, and any reading from a populated public server.

## Open
<a id="open"></a>

- What each sub-step of the slow minute costs on a live server is the hitching plan's live sub-step run, pending; offline, the heal passes are about half of the pipeline's C-Lua time and a heal once before the step keeps the golden trace, which a live run has not priced [#3387/M/n=1] [#3411/C/inference] [#3413/C/inference].
- Which shape keeps the longest frame lowest at a large player count, a burst, a round-robin or a budgeted queue drained on `OnTick`, and whether the queue's own per-frame check costs more than it spreads, is the hitching plan's scheduler run [#3391/M/n=1, #3440/M/arith.].
- Whether a player notices a periodic long server frame, and at what length, is unmeasured: every client consequence above is read from the loop [#3429/C/C-only].
- Whether the jar's fake client joins a server of this build, and so gives real per-player load beyond two clients, is unread; its entry point and scenario keys are read [#3452/C/C-only].
- What vanilla's own frame costs at a large player count is unread, and it sets the headroom a mod has [#3440/M/arith.].
- How much heavier a day-boundary minute, a first sight and a mass reconnect are than a typical minute is unmeasured [#3387/M/n=1].
- What one push of a large table costs on the main thread is unmeasured [#3437/C/C-only].
- How long the global modData save takes at a large store, and what a client's request of it costs the server, is unmeasured [#3421/C/C-only, #3422/C/inference].

## Procedure
<a id="procedure"></a>

1. Name the frame the change lands in: the event it runs on, and whether that event fires every frame, once a game minute or inside the minute's clock update.
2. Name how often that frame comes at the day lengths the server runs, and under a fast clock.
3. Name how its cost grows: flat, per player, per player ever seen, or per packet.
4. Stage the change, never `mod/`, and measure one run's cost on a live server with a bracket over many runs, stating the count.
5. Measure the frame at the target player count with `ghost.load` under the scheduler the change uses, reading `perf.local` for the frame's length and `tick.ring` for its attribution, against an idle baseline from the same session.
6. Write the longest frame the change adds and how often it comes, with the readings' rows, and never the mean alone.
7. Turn on `gclog` when the change allocates per player, and line any stall up with the frames.

## See also

- [lessons.md](lessons.md#rules) — the standing rules, the frame rules among them.
- [server-lifecycle.md](server-lifecycle.md#tick-order) — the time events in the lifecycle, the tick counts and the fast clock.
- [lua-platform.md](lua-platform.md#events) — the event roster, what a handler's raise costs, and the stat hook.
- [mp-model.md](mp-model.md#routes-client-to-server) — the routes a value travels, the global modData request among them.
- [harness.md](harness.md) — the instrument and its commands.
- [../facts/character-stats.md](../facts/character-stats.md#tick-order) — the player update inside `IsoWorld.update`, and where `OnPlayerUpdate` returns.
- [../facts/character-stats.md](../facts/character-stats.md#updaters) — the updaters that move a stat each tick, behind the sawtooth of a once-a-minute write.
- [../areas/testing-your-mod.md](../areas/testing-your-mod.md#walls) — the mod's own cost readings and their bounds.
- [jar-research.md](jar-research.md) — how the readings on this page were taken and re-checked.
