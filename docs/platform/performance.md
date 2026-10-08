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
- Give a budgeted `OnTick` queue a per-tick cap with headroom over the minute's work divided by the minute's ticks, and never a fixed cap near or below it: with fifty-eight ghost records beside two players at `DayLength` 1 a 5 ms cap starved records at every minute event, a 10 ms cap ran 56.75 of the 58 due a minute event, and the drafted spread of ceil(records / ticks) a tick starved 176 record-minutes over 167 minute events, while a 15 ms cap starved none in ten draws over four sessions, at `DayLength` 1 and at 37 ticks a game minute; under a fast clock, where every frame is a minute frame, a 10 ms cap left records up to 42.8 game minutes stale [#3497/C/inference, #3428/C/C-only, #3477/M/n=1, #3476/M/n=1, #3478/M/n=1, #3489/M/n=1, #3490/M/n=1, #3480/M/n=1].
- Spread per-player pushes over the minute's frames rather than sending every player's push in one frame: each send serialises its table on the main thread once per receiver, one send of a 138-key payload cost about 0.1 ms of server frame, so sixty players' pushes in one frame are about 6.12 ms, and a push gap counted from each player's last push keeps pushes first sent together in the same minute [#3498/C/inference, #3437/C/C-only, #3464/M/n=1, #3456/C/inference].
- Compare two schedulers' total cost by the batch-timed work each ran a minute event and never by their frames' busy time over an idle arm: the two no-load arms of one session drifted from 1.873 to 1.256 ms of busy a frame, and in another session busy over idle put a 10 ms budget at 1.22 times the burst's total at 37 ticks a game minute where the ghosts' own milliseconds a minute event put it at 1.046 [#3499/C/inference, #3483/M/n=1, #3479/M/n=1, #3491/M/n=1].

## How it works

This page is written for the next change to server-side work: it opens with how to budget one, then gives the mechanisms the budget rests on, then the costs measured so far.
Every mechanism here is a bytecode reading, and every cost comes off live sessions with two real players, several of which also ran ghost records through the real pipeline, eighteen in the first and fifty-eight in the scheduler runs [#3448/C/C-only] [#3405/M/n=1] [#3472/M/n=1].
A ghost record is cost and never behaviour: it runs the pipeline against a real player object, so its state is not a player's state [#3405/M/n=1].
A fed ghost's minute cost 0.978 of a real player's over forty pairs, and with the coarseness of that bench a load of sixty is a cost stand-in for about 44 to 60 players' minutes (inference), carrying none of vanilla's own per-player work [#3466/M/n=1] [#3472/M/n=1] [#3440/M/arith.].
Every figure for more players than the ghosts reached is arithmetic, labelled where it is used [#3440/M/arith.].
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
A per-player loop grows linearly, and at sixty it was measured: fifty-eight fed ghost records beside two players at `DayLength` 1, run in one minute event, read 50 ms of the frame's busy time at the median and 88 at the worst [#3472/M/n=1].
The earlier arithmetic bracket, from two players' per-run costs, put that loop at 73.7 to 103.3 ms (arithmetic), about a whole frame before vanilla's own work [#3440/M/arith.].
The same work spread over a minute's frames is about 95 ms a game minute, about 15 % of the server at `DayLength` 1 (arithmetic), so the mean is affordable where the burst is not [#3440/M/arith.].
Read the other way, a burst over N players stays under a frame budget only while one run costs at most that budget divided by N, so keeping a sixty-player event under 10 ms allows about 0.167 ms a run (arithmetic), about a ninth of the 1558.33 µs an in-play run measured [#3441/C/inference] [#3387/M/n=1].
The burst's minute frame grew linearly with the load, 18, 32 and 50 ms of busy at the median at twenty, forty and sixty [#3474/M/n=1].
In the session with the players side by side, at sixty on this host, that burst's busy, up to 74 ms, ran inside an unbroken 100 ms start-to-start cadence, so what it lengthened was the end-to-end period, up to 176 ms [#3486/M/n=1].
Extrapolated linearly, the worst minute frame at sixty, 88 ms of busy, would cross the 100 ms period near 68 to 74 players on this host, and the median minute frame, about 50 ms, near 120 (inference) [#3472/M/n=1] [#3474/M/n=1].
That extrapolation carries none of vanilla's own per-player load at sixty real players, which is unmeasured because the engine's fake client could not join, so spreading the minute buys headroom for more players, heavier minutes and slower hosts rather than relief from a stall measured at sixty (inference) [#3486/M/n=1] [#3494/M/n=1].
A spread that keeps that headroom sizes its per-tick budget to the minute's work: at sixty and `DayLength` 1 a 10 ms budget ran 56.75 of the 58 records due a minute event, while a 15 ms budget starved none and added 12 to 13 ms to the end-to-end period's 99th percentile against the burst's 46 to 56, and 12 to 13 against 43 to 46 at 37 ticks a game minute [#3476/M/n=1] [#3489/M/n=1] [#3490/M/n=1].

The fourth is the measured cost of one run on a live server, read under [How to measure](#measure).
With step and sub-block timers on, an in-play run cost 1.459 ms, and an unprofiled bench of typical minutes 1.134 ms a run [#3457/M/n=1] [#3462/M/n=1].
The verdict is the longest frame the change adds and how often that frame comes, never the mean [#3442/C/inference].
The engine's own counter is the reading of a frame's length, and a Lua timer is a total over many runs with its count [#3443/C/inference].
Offline timings rank a pipeline's blocks by share and never price a frame [#3438/C/inference].

What one more of each part costs a run is read off the live minute, and every entry below is inference from the readings it names.

| one more | cost a run (inference) | rows |
|---|---|---|
| nutrient record | about 5 µs a record: `nutrients/records` took 34 ms over 244 runs of the 27 records (arithmetic) | [#3458/M/n=1, #3415/C/inference] |
| payload key on the send | unmeasured; one 138-key send cost about 0.1 ms whole | [#3437/C/C-only, #3464/M/n=1] |
| pipeline step | that step's summed total over 244 runs, divided by 244, from 0 ms (`fast`) to about 0.71 ms (`nutrients`, 173 ms) a run (arithmetic), each total a sum of 1 ms truncations | [#3457/M/n=1, #3458/M/n=1, #3459/M/n=1] |

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
With fifty-eight ghost records, in one session, the burst's busy reached 74 ms inside an unbroken 100 ms start-to-start cadence while the end-to-end period reached 176 ms [#3486/M/n=1].

What a long frame does to a player's own actions is read from the loop and not measured on a client.
A packet that arrives during the frame waits for the next pass, so a client's request is answered up to the frame's length late [#3429/C/C-only].
The player-stats push runs after the frame's `IngameState.update` in the same pass, so it leaves late by the frame's length too [#2402/C/C-only].
What a client shows of another player was measured: with two clients beside each other on the server's host, neither client's own frame reached 100 ms under the burst at sixty, and the gaps in the other player's motion lined up with the minute frames no more often than chance alignment, read against the same frames shifted by half their spacing [#3486/M/n=1] [#3488/M/n=1].
Whether a player notices a long frame through their own actions, over a real network or among zombies is [open](#open) [#3488/M/n=1].

<a id="frame-order"></a>
### Inside a frame: the order and the clock events

`IngameState.updateInternal` fires `OnTickEvenPaused` near its start, runs `IsoWorld.update`, where the per-player updates run, then `UpdateStuff`, whose `GameTime.update` fires the clock events, then `onTick`, which fires `OnTick` [#3428/C/C-only] [#2401/C/C-only].
A live ring confirmed the order on a dedicated server: the minute's work ran between the frame's `OnTickEvenPaused` and its `OnTick` in all 193 minute frames [#3410/M/n=1].
`IngameState.update`, and with it `OnTick`, runs before `NetworkPlayerManager.update` in the same pass [#2402/C/C-only].

One `GameTime.update` fires `EveryDays` at a day rollover, `EveryHours` when the hour changed, `EveryTenMinutes` when the ten-minute block changed, and `EveryOneMinute` when the minute stamp changed, in that order [#3427/C/C-only] [#2400/C/C-only].
Vanilla's own erosion and climate updates run in the ten-minute arm just before its Lua event, so the ten-minute frame is already vanilla's heavier one [T1199.9].
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
The starvation was measured under a fast clock, where the queue served one of two players a minute, and at a normal clock with fifty-eight ghost records, where a mirror of the drain ran 4.26 records a minute event and 53 of the 58 never ran [#3352/M/n=1] [#3482/M/n=1].
At sixty on one host a drain with a 15 ms per-tick budget added 12 to 13 ms to the end-to-end period's 99th percentile where the burst added 46 to 56 and a round-robin of two 32, and it starved no record; the shoot-out is under [Measured costs](#costs) [#3489/M/n=1] [#3475/M/n=1].

<a id="levers"></a>
### What a mod can do about its frame cost

A mod has five levers on the frame it adds, and each rests on a mechanism above.

- Make one run cheaper: in the worked example the nutrients step is about half of an in-play minute, and it makes 9 of the run's 79 `NR.call` calls [#3387/M/n=1] [#3388/M/n=1]; offline, the seven heal passes are about half of the pipeline's C-Lua time, a heal once after the step changes the golden trace, and a heal once before it keeps the trace and saves 27.7 % [#3411/C/inference] [#3412/C/inference] [#3413/C/inference]; live, the two Nutrients heal passes were the two largest sub-blocks of the minute, 28.4 % of it [#3458/M/n=1].
- Spread a fixed workload over the minute's frames with a queue drained on `OnTick` that carries its unserved players forward, rather than running it in one event [#3444/C/inference] [#3428/C/C-only], with a per-tick budget sized to the minute's work [#3477/M/n=1] [#3476/M/n=1].
- Keep work off the ten-minute, hour and day events, which fire in the minute's own clock update [#3427/C/C-only].
- Keep a push out of a burst frame: each send serialises its table on the main thread, once per receiver [#3437/C/C-only], and one send of a 138-key payload cost about 0.1 ms, so sixty in one frame are about 6.12 ms [#3464/M/n=1]; a push gap counted in wall time from each player's last push keeps players first seen together pushing in the same minute ever after, and under a burst in the burst frame (inference) [#3456/C/inference].
- Keep a store that grows with every player ever seen out of global modData, where every save serialises it and any client can request it [#3445/C/inference] [#3422/C/inference]; live, the first save at 2000 records made a 2990 ms frame [#3467/M/n=1].

Two more keep a mod from adding a frame by accident.
A mod that asks for a collection asks for it inside its own frame [#3446/C/inference].
A mod whose command handlers run long spends the packet pass that the vehicle-physics guard counts [#3447/C/inference].
A per-frame site is not free either: a queue drained on `OnTick` runs its early-out on every frame of the session, so its own empty check is part of its cost [#3428/C/C-only] [#2401/C/C-only].
Whether that check costs more than the spreading saves at a given player count is a measurement and not a reading [#3442/C/inference]; the one A/B taken did not resolve it above one host's drift between arms, under [How to measure](#measure) [#3483/M/n=1].

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
In four later sessions under loads of up to fifty-eight ghost records, the ZGC pauses inside the measured arms were at most 0.695 ms, and every allocation stall, 29 to 36 a session and the longest 274.56 ms, fell at 32.385 to 35.133 s of the server JVM's uptime, during boot, before any arm [#3484/M/n=1].
So table churn costs the allocating handler's own time, which a step timer already includes, and the risk left is an allocation stall when the heap nears its ceiling [#3436/C/inference] [#3408/M/n=1] [#3484/M/n=1].

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
One payload was measured live: a send of a 138-key table to one client cost about 0.1 ms of frame, and building the table alone about 0.04 ms [#3464/M/n=1].
A send's cost per key is unmeasured [#3437/C/C-only].

<a id="global-moddata"></a>
### Global modData: the save and the request

The console `save` and the autosave run `GlobalModData.save` on the server's main loop, inside the world save, and the quit save runs it on the JVM's shutdown-hook thread [#3420/C/C-only].
The save serialises every table into one heap buffer, 1 MiB at first, growing by 512 KiB and re-serialising the overflowing table on each overflow, and the world save sends clients a pause between its steps after 600 ms [#3421/C/C-only].
A record of this mod's shape is about 10.8 KB in the save's format, so a store of 500 such records is about 5.4 MB, held for every player who ever joined unless the mod prunes it [#3422/C/inference].
Live, each seeded copy of one record added 10877 bytes to `global_mod_data.bin`: the file was 21633 bytes with the two real records, 1109333 with 100 seeded, 5460133 with 500 and 21775633 with 2000, and 21633 again after the seeded records were cleared and the world saved [#3468/M/n=1].
The save's own time grew with the store, and the first save at a new size paid far more than the next: with 0, 100, 500 and 2000 seeded records, `Saving GlobalModData` to `Saving finish` took 11 then 9 ms, 22 then 16, 153 then 50, and 2770 then 193 ms for two console saves about 32 s apart [#3467/M/n=1].
The first save at 2000 records logged `Pausing clients because saving is taking longer than 600ms` and made a 2990 ms server frame against a median of 100 [#3467/M/n=1].
That the first save at a size pays the buffer's growth restarts is inference, and it makes the first save after the store passes its last high-water mark, an autosave after a long uptime among them, the save that stalls [#3467/M/n=1] [#3421/C/C-only].
Any logged-in client can request a global modData table by name and receive it, serialised whole up to the connection's send buffer, and a mod cannot refuse the request [#3417/C/C-only] [#3418/C/C-only].
A reply larger than the connection's 1,000,000-byte send buffer goes out truncated [#3419/C/C-only].
Live, a client's request returned the table whole at 2 and 60 records within 44 ms, at no frame cost above the idle jitter, and at 500 records it failed on both sides while the client kept its session [#3469/M/n=1] [#3470/M/n=1].
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
| sixty players' minutes in one event | measured, fifty-eight fed ghosts beside two players: busy 50 ms median, 88 max; the earlier arithmetic bracket 73.7 to 103.3 ms, about 51.7 ms on the ghost basis (arithmetic) | [#3472/M/n=1, #3440/M/arith.] |
| sixty players' minutes spread over the minute (arithmetic) | about 95 ms a game minute | [#3440/M/arith.] |
| one player's minute in play, sub-block timers on | 1.459 ms a run over 244 runs | [#3457/M/n=1] |
| the Nutrients heal pair in that minute | 101 of 356 ms, 28.4 %; the seven heal passes 143 ms, 40.2 % | [#3458/M/n=1] |
| a typical, a day-closing and a seven-day catch-up minute, benched | 1.134, 1.022 and 1.053 ms a run over 1000 | [#3462/M/n=1] |
| first sight's measured parts | 0.861 ms a joiner, a floor | [#3463/M/n=1] |
| one mirror send of 138 keys | 102 ms over 1000 sends; sixty in one frame about 6.12 ms | [#3464/M/n=1] |
| a ghost's minute against a real player's | 0.978 fed, 0.778 unfed, over forty pairs | [#3466/M/n=1] |
| the global modData save at 500 and 2000 seeded records | 153 then 50 ms; 2770 then 193 ms | [#3467/M/n=1] |
| one stored record on disk | 10877 bytes | [#3468/M/n=1] |
| fifty-eight ghost minutes in one minute frame | busy 50 ms median, 81 p99, 88 max | [#3472/M/n=1] |
| the longest engine window, burst against a 15 ms budget, six draws at `DayLength` 1 | 164 to 176 ms against 127 to 139 | [#3489/M/n=1] |

The sixty-player arithmetic rows are linear extrapolation from two players, and vanilla's own per-player cost at that load is in no reading, so the absolute frame there is unknown [#3440/M/arith.].
The ghost run read about half the in-play run, so the two bases bracket the per-run cost rather than agree on it [#3405/M/n=1] [#3440/M/arith.].

#### The minute by sub-step, live

With step and sub-block timers on, two players' slow minutes in play at `DayLength` 1, over two 60-game-minute windows each crossing the mod's day boundary, cost 356 ms over 244 runs, 195 ms over 122 for one player and 161 over 122 for the other, 1.459 ms a run; by step, `nutrients` 173 ms, `metabolism` 79, `effects` 38, `kinetics` 18, `strength` 15, `weight` 13, `reconcile` 9, `bus` 2 and `fast` 0 [#3457/M/n=1].
In that minute the two Nutrients heal passes are the two largest sub-blocks, `nutrients/heal.pre` 62 ms and `nutrients/heal.post` 39, 28.4 % of the minute, and the seven heal passes together 143 ms or 40.2 %; next come `nutrients/records` 34 ms, `metabolism/readActivity` 32 (9.0 %), `nutrients/acute` 20, `metabolism/heal.post` 15 and `metabolism/heal.pre` 11 [#3458/M/n=1].
Offline the Nutrients heal pair is 38.4 % of the C-Lua pipeline, so it leads on both hosts, but the two shares are not comparable as a Kahlua effect: the live minute holds Java-interop blocks the offline host stubs, its scenario differs, and about 30 bracket pairs were on [#3458/M/n=1] [#3411/C/inference].
The sub-blocks at 15 % or more of their own step are `nutrients/heal.pre` (62 of 173 ms), `nutrients/heal.post` (39), `nutrients/records` (34), `metabolism/readActivity` (32 of 79) and `metabolism/heal.post` (15), while five effects and strength sub-blocks also cross that line on totals of 5 to 9 ms, at the 1 ms noise [#3459/M/n=1].
A minute that closes a day is no heavier in play: the four in-play runs that closed a Metabolism day took 1 or 2 ms against plain runs of p50 1 ms and mean 1.600 and 1.317 ms over 120 runs each, too few at 1 ms to settle a ratio [#3460/M/n=1].
A player held deficient is no heavier at 1 ms resolution: with one player's vitamin C and iron grades at 4 for 60 game minutes, that player's pipeline took 93 ms over 63 runs against the other's 89 over 63, the steady deficient minute with its onset unmeasured [#3461/M/n=1].

#### Burst sources, benched

Over 1000 interleaved bench runs on copies of one player's record, a typical minute took 1134 ms in total, a minute closing one day in Metabolism, Nutrients and Effects 1022 ms and a catch-up closing seven days 1053 ms, the largest single run 5 ms, so a day close is 0.901 of the typical minute, and with the profile on `metabolism/closeDay` took 20 ms over 1400 closes [#3462/M/n=1].
First sight's measured parts, the store's load of a fresh record copy, `ensureBody` on an empty record and the first-sight hooks with the re-hoist skipped and sends stubbed, took 698, 74 and 89 ms over 1000 runs, 0.861 ms a joiner, a floor [#3463/M/n=1].
One mirror send of the real 138-key payload took 102 ms over 1000 sends, so sixty in one frame are about 6.12 ms, and building the payload alone took 42 ms over 1000 [#3464/M/n=1].
Across the mod's 07:00 day close at sixty, the burst's first minute frame after 07:00 read 67 ms busy and a 170 ms end-to-end period against the arm's minute-frame p50 of 50 and max of 76 ms, 1.34 times the p50, and under a 10 ms budget the frames within two game minutes of 07:00 read at most 20 ms, that arm's own max [#3481/M/n=1].
So of the per-minute burst sources benched, a day close and a seven-day catch-up are not one, and the send is one at sixty, when every player's push lands in one frame [#3464/M/n=1] [#3462/M/n=1].
First sight's 0.861 ms is a floor, so sixty joiners in one frame would cost at least 51.7 ms (arithmetic), and whether a mass join is a burst is [open](#open) [#3463/M/n=1].

#### The scheduler shoot-out at sixty

The shoot-out ran fifty-eight fed ghost records beside the two players under each scheduler, about 1020 frames an arm, against an idle arm of the same session; busy is the frame's start to the end of `OnTick`, the window is the engine's per-window longest frame, and an add is over the idle arm [#3472/M/n=1] [#3471/M/n=1].
With two players idle at `DayLength` 1 about 1020 consecutive frames read busy 2, 10 and 13 ms at p50, p99 and max in one session and 1, 8 and 15 in another, an end-to-end period of at most 111 and 114 ms and a longest window of at most 115 ms in both; at 37 ticks a game minute busy read 1, 5 and 18 ms and the longest window 119 ms, and under `settimespeed 30`, with a minute event on all 610 frames, 6, 16 and 47 ms and 145 ms [#3471/M/n=1].

| N | scheduler | spacing | busy p50 / p99 / max (ms) | longest window (ms) | added at the end-to-end period's p99 / the window max (ms) | starved ghost-minutes / minute events | rows |
|---|---|---|---|---|---|---|---|
| 2 | idle | `DayLength` 1 | 2 / 10 / 13 | 115 | — | — | [#3471/M/n=1] |
| 60 | burst | `DayLength` 1 | 50 / 81 / 88, minute frames | 188 | +62 / +73 | — | [#3472/M/n=1] |
| 60 | round-robin of two, 29 of 58 a minute | `DayLength` 1 | 31 / 45 / 48, minute frames | 146 | +32 / +31 | none (each ghost every second minute by design) | [#3475/M/n=1] |
| 60 | round-robin of five, 12 of 58 a minute | `DayLength` 1 | — | — | +9 / +8 | none (each ghost every fifth minute by design) | [#3475/M/n=1] |
| 60 | ceil(ghosts / ticks) a tick | `DayLength` 1 | 10 / 19 / 22 | 119 | — / +4 | 176 / 167 | [#3478/M/n=1] |
| 60 | 5 ms budget | `DayLength` 1 | — / — / 43 | 141 | — / +26 | 6079 / 167 | [#3477/M/n=1] |
| 60 | 10 ms budget | `DayLength` 1 | 10 / 16 / 26 | 124 | +5 / +9 | 207 / 166 | [#3476/M/n=1] |
| 60 | 15 ms budget | `DayLength` 1 | 11 / 19 / 31 | 134 | +13 / +19 | 0 / 165 | [#3477/M/n=1] |
| 60 | burst, six draws | `DayLength` 1 | — | 164 to 176 | +46 to +56 / +48 to +61 | — | [#3489/M/n=1] |
| 60 | 15 ms budget, six draws | `DayLength` 1 | — | 127 to 139 | +12 to +13 / +11 to +25 | none | [#3489/M/n=1] |
| 60 | burst | 37 ticks | 48 / — / 60, minute frames | 161 | +44 / +42 | — | [#3473/M/n=1] |
| 60 | ceil(ghosts / ticks) a tick | 37 ticks | — / — / 11 | 113 | — | none | [#3478/M/n=1] |
| 60 | burst, three draws | 37 ticks | — | 153 to 173 | +43 to +46 / +47 to +67 | — | [#3490/M/n=1] |
| 60 | 15 ms budget, three draws | 37 ticks | — | 123 | +12 to +13 / +17 | none | [#3490/M/n=1] |
| 60 | burst | `settimespeed 30` | 48 / 67 / 76 | 134, idle 145 | — | — | [#3480/M/n=1] |
| 60 | 10 ms budget | `settimespeed 30` | — | — | — | 29715 / 623 | [#3480/M/n=1] |

The table is a headroom reading: at sixty on this host the burst's busy fitted inside the 100 ms start-to-start cadence, one unexplained 136 ms start-to-start period in x244a aside, so every window above 100 ms is an end-to-end period, and a design's margin is how much frame it leaves for vanilla's own load, heavier minutes and slower hosts (inference) [#3486/M/n=1].
At `DayLength` 1 the 58 fed ghosts in one `EveryOneMinute` frame read busy 50, 81 and 88 ms over the 146 kept minute frames, the end-to-end period over all 1018 kept frames 170 ms at p99 and 188 at the max, and every one of the 95 kept engine windows held a frame over 133 ms, the burst adding 62 ms to the end-to-end period's p99 and 73 ms to the longest window at 0.868 ms a ghost run [#3472/M/n=1].
At 37 ticks a game minute the same burst read minute-frame busy p50 48 and max 60 ms over its 27 minute frames, the end-to-end period 149 ms at p99 and 161 at the max over 1024 frames, and added 44 ms at the end-to-end period's p99 and 42 to the longest window, at 0.794 ms a ghost run [#3473/M/n=1].
The burst grows linearly with the ghost count: its minute frame's busy p50 read 18, 32 and 50 ms with 18, 38 and 58 ghosts, at 0.897, 0.800 and 0.868 ms a run, and the longest window 135, 151 and 188 ms [#3474/M/n=1].
A round-robin of two, 29 of the 58 ghosts each minute, read minute-frame busy 31, 45 and 48 ms and a longest window of 146 ms, adding 32 ms at the end-to-end period's p99 and 31 to the longest window, and a round-robin of five, 12 a minute, added 9 and 8 ms but served each ghost once in five minutes, up to 5.1 game minutes stale [#3475/M/n=1].
A queue drained on `OnTick` under a 10 ms budget read busy 10, 16 and 26 ms over 1019 frames and a longest window of 124 ms, adding 5 and 9 ms, but ran 56.75 ghost minutes a minute event against 58 due, so 207 ghost-minutes starved over 166 minute events, 34 of them, each ghost at most one event late (2.08 game minutes stale), at 0.857 ms a run, and the same budget across 07:00 in another session starved 166 over 86 events [#3476/M/n=1].
That starvation is bounded lateness and not loss, a property of a budget at the margin of the minute's work: both its time cap and its run cap bound frames, and a six-tick minute at its 9.61 runs a frame serves about 57.7 of 58 (inference) [#3476/M/n=1].
Under a 15 ms budget the queue starved no ghost over 165 minute events and read busy 11, 19 and 31 ms over 1016 frames and a longest window of 134 ms, adding 13 and 19 ms, while under a 5 ms budget it ran 21.52 ghost minutes a minute event, every event starved ghosts, 6079 ghost-minutes over 167, staleness reached 4.12 game minutes, and one 43 ms frame, 40 ms of it outside the 3 ghost ms of its 3 runs, set a 141 ms window, 26 ms over idle [#3477/M/n=1].
The drafted spread of ceil(ghosts / ticks a minute) a tick read busy 10, 19 and 22 ms and a longest window of 119 ms, 4 ms over idle, yet starved 176 ghost-minutes over 167 minute events, 44 of them, as it did at forty, 88 over 166, while at 37 ticks a game minute it starved none, read busy at most 11 ms and a longest window of 113 ms, at 1.107 ms a run [#3478/M/n=1].
Over a game minute the frames' total busy at sixty and `DayLength` 1 rose over idle by 46.9 ms under the burst, 47.3 under the 10 ms budget (1.01 times the burst's, with 56.75 of 58 served), 41.8 under the 15 ms budget, 51.1 under the drafted spread and 27.2 under the round-robin of two, and at 37 ticks a game minute by 24.5 under the burst, 29.9 under the 10 ms budget (1.22 times) and 43.2 under the drafted spread [#3479/M/n=1].
The 1.22 is the idle drift between arms and not the budget: the ghosts' own batch-timed milliseconds a minute event put the 10 ms budget at 1.046 times the burst's there (inference) [#3479/M/n=1].
Under `settimespeed 30`, with a minute event on every frame, the burst ran 58 ghosts every frame at busy 48, 67 and 76 ms over 609 frames, yet the period stayed at 123 ms at p99 and the longest window at 134 ms against the fast idle arm's 145, because a load on every frame moves each frame's end alike (inference), while a 10 ms budget there served about 10.3 ghosts a frame against 58 due, starved 29715 ghost-minutes over 623 minute events and left ghosts up to 42.8 game minutes stale [#3480/M/n=1].
The 1.0.0 drain mirrored at sixty, its queue rebuilt each minute and one record a tick behind the mod's own drain of the two real players, ran 4.26 ghost minutes a minute event over 116 minute events at `DayLength` 1, dropped 6180 queued ghost-minutes and left 53 of the 58 ghosts never run, the longest 115.7 game minutes stale [#3482/M/n=1].

Repeated draws settle the budget against the burst.
At `DayLength` 1 and sixty, six draws of the burst over two sessions added 46 to 56 ms to the end-to-end period's p99 and 48 to 61 ms to the longest window (164 to 176 ms), while six draws of a 15 ms budget added 12 to 13 ms and 11 to 25 ms (127 to 139 ms) and starved no ghost [#3489/M/n=1].
At 37 ticks a game minute three draws of the burst added 43 to 46 ms and 47 to 67 ms (153 to 173 ms), while three draws of the 15 ms budget added 12 to 13 ms and 17 ms (123 ms) and starved no ghost [#3490/M/n=1].
Totalled as ghost milliseconds a minute event, the 15 ms budget ran 1.053, 1.061 and 1.060 times the burst's mean in three sessions, and busy a game minute over idle gave 1.052, 1.046 and 1.065 [#3491/M/n=1].
That 5 to 6 % excess is not resolved from the spread of ghost milliseconds a run between the arms of one session, 0.762 to 0.874, so its cause is unmeasured (inference) [#3491/M/n=1].
Read against the hitching plan's scheduler bounds at sixty, at most 20 ms added at the end-to-end period's p99 and 25 at the maximum, no starvation and a total at most 1.1 times the burst's, the 15 ms budget met the peak and starvation bounds in all nine draws at both spacings and the total bound in all three sessions, while the burst added more than 33 ms or made a frame over 133 ms in every draw, and the empty-queue bound of 0.1 ms a frame was not measured [#3492/M/n=1].

#### What a client shows of the burst

With the two players beside each other at `DayLength` 1 and sixty, neither client's own frame interval reached 100 ms in any arm, at most 32 ms under the burst, whose busy reached 74 ms inside an unbroken 100 ms start-to-start cadence, an end-to-end period of up to 176 ms; on each client the gaps of 100 ms or more in the other player's position changes lined up within one server frame of a minute frame 32 to 43 times an arm under the burst against 30 to 41 against the minute frames shifted by half their spacing, and 35 to 44 against 28 to 38 under the 15 ms budget, so the burst's minute frames left no gap in the other player's motion above the chance alignment [#3486/M/n=1].
The other player's `getLastRemoteUpdate()` stamp advanced every 201 to 400 ms at the median and at most every 801 to 818 ms on both clients in the idle, burst and budgeted arms alike, and its gaps of 100 ms or more lined up with a minute frame 175 to 244 times an arm in the loaded arms against 180 to 231 in the shifted control; every stamp gap exceeds 100 ms, so that count is no test of the burst [#3487/M/n=1].
The near-player stamps stayed within one or two client frames of the 200 ms grid in every arm, including the gaps that spanned a burst frame of 30 ms or more of busy, so at sixty on loopback, with no zombies present, the burst has no visible effect on another player's updates, while a count of stamp gaps of 100 ms or more could not have shown one at this cadence and its outcome of not noticeable follows from its construction (inference) [#3488/M/n=1].
A player's own actions on server-owned state wait on the server frame and were not measured, and neither were real network latency and zombies [#3488/M/n=1].

Vanilla's own frame at sixty real players, and the burst and the budget on real players beyond two, were not read: the engine's fake client puts no player on a server of this build, as [How to measure](#measure) gives [#3494/M/n=1].

<a id="measure"></a>
### How to measure

The harness reads a frame's length and a load's cost on a live server; its commands are listed in [harness-commands.md](../reference/harness-commands.md) and the instrument is [harness.md](harness.md).
`tick.ring` stamps each frame at `OnTickEvenPaused` and `OnTick` and reports the busy time and the period, for attributing a frame's time [#3403/M/n=1] [#3410/M/n=1].
`perf.local` samples the engine's per-window longest and shortest frame once a window, the hitch reading [#3403/M/n=1] [#3409/C/C-only].
`ghost.load` runs a number of ghost records through the real pipeline under a named scheduler, for cost at a player count two clients cannot reach [#3405/M/n=1] [#3407/M/n=1].
`bench.global` brackets many calls of one function with the 1 ms clock and reports the cost a call [#3432/C/C-only].
`world.posring <n>` is the client's per-frame series: on a client it records the last n `OnTick` frames, each with the wall time, the other player's position and `getLastRemoteUpdate()` stamp and the nearest zombie's position, the series a client-side effect is read off [#3485/C/C-only] [#3488/M/n=1].
A profile's `gclog` key writes the server's GC log beside the run, for lining a pause or a stall up with a frame [#3408/M/n=1].
Offline, the kernel's host is C Lua, so an offline profile ranks blocks by share and a live reading prices them [#3438/C/inference].

`ghost.load <N>` takes its scheduler as `burst`, `rr<m>`, `drainTicks`, `budget<ms>` or `shipped`, `ghost.stats reset` zeroes the load's counters for the next arm, and `ghost.bench <n>` arms a bench of interleaved ghost and real-player minutes that `ghost.bench read` replies [#3455/C/inference].
The bench runs each record at most once a minute event and never at a zero interval, because a run at an unchanged world age reads the zero-interval shape of the work, and `ghost.bench` carried the same zero-interval bias before 30bba11 [#3455/C/inference].
That shape is about four times under an in-play minute: back-to-back runs read 390, 395 and 345 µs and 430, 389 and 333 µs a call in two sessions, against 1558.33 µs a run in play [#3354/M/n=1] [#3390/M/n=1] [#3387/M/n=1].
The slow minute's per-step profiler and `NR.call` counter are kept at `testing/spikes/instruments/x231_NR_Server_Bench.lua`, an instrument appended only to a staged copy and never to `mod/` [#3454/C/inference].
A step's total there is a sum of 1 ms truncations, so a small step's per-run figure is indicative only: in play the `nutrients` total of 192 ms carried about ±6.2 ms (arithmetic) and the `bus` total of 2 ms about ±1.4 ms (arithmetic) [#3387/M/n=1].
Set `DayLength` in the profile and never at run time: set through `SandboxOptions:set` on a live server it read back 4 and left the clock at 6.47 ticks a game minute [#3394/M/n=1].
The engine's own slow-handler warning is no instrument for this: `Event.trigger` warns `SLOW Lua event callback` only for a call over 250 ms and only while the debug-only option `SlowLuaEvents`, created off, is on [#3450/C/C-only].
The jar also ships a fake client, `zombie.network.FakeClientManager`, whose `main` takes `-scenarios=<file>` and `-id=<n>`, loads the `ZNetNoSteam64` library and reads a scenario's server host, checksum, Lua, frame-rate and movement keys, and the harness's server runs `-nosteam` [#3452/C/C-only].

Run as shipped against a server started with `-nosteam`, `Open=true` and `DoLuaChecksum=false`, the fake client connects, logs in, passes the login queue and is kicked at `player-connect` with `UI_LoadPlayerProfileError`: over about five minutes its one connected client, `Client1`, was allowed to join and kicked 23 times and no fake player was ever online, so the shipped fake client gives no player load on this build [#3494/M/n=1].
The server kicks a joining player with `UI_LoadPlayerProfileError` when it finds no saved character for the connection: `GameServer.receivePlayerConnect` asks `ServerPlayerDB.serverLoadNetworkCharacter` for the player by username and kicks on a null; the fake client asks for its profile with `LoadPlayerProfile` straight after the login queue and sends `CreatePlayer` once when the server holds no character, and skips its checksum step when its scenario names no checksum [T1199.10].
It runs every movement of its scenario as a client on one RakNet peer in one JVM, bound to local port 17500 unless `-id=<n>` picks one movement and port 17500 + n; live, at each connect round all but one of the clients due failed, the server only ever saw `Client1`, so one JVM gave one connected client (inference), and the JVM with sixty client threads held a 133.3 to 180.9 MB working set [#3496/M/n=1].

Compare arms of one session on a measure the drift between arms cannot move.
In one session two no-load arms read 1.873 and 1.256 ms of busy a frame, so a total read as busy over an idle arm carries that drift, and the ghosts' own batch-timed milliseconds a minute event are the drift-immune total [#3483/M/n=1] [#3479/M/n=1] [#3491/M/n=1].
A ratio between two small totals is only as good as their truncations: forty interleaved pairs at the 1 ms clock put a fed ghost at 0.978 of a real player's minute on totals of 45 and 46 ms, so the shoot-out read each ghost's cost off `ghost.stats`' batch totals over whole arms instead, 0.868 ms a run in the burst at sixty [#3466/M/n=1] [#3472/M/n=1].
An empty budgeted queue's own per-frame check was not resolved above one session's drift: over about 3000 frames a side in the order none, empty, empty, none, the empty side's busy less its ghost's own milliseconds read 1.512 ms a frame against 1.565 with no load (-0.052 ms), and the frames with no ghost run and no minute event 1.166 against 1.243 (-0.077 ms), while the two pairs read -0.238 and +0.133 ms by the totals and the two no-load arms 1.873 and 1.256 ms a frame [#3483/M/n=1].
A fit of a linear drift plus an empty-side offset to the four arms gives -0.053 ms a frame, its largest residual 0.018 a one-degree-of-freedom curvature and not an error bar, and its standard error about 0.03 ms, so it weakly supports a check of at most 0.1 ms a frame and no more (inference) [#3483/M/n=1].
A direct bench of the empty check's loop is the reading that would settle it, and none was taken [#3483/M/n=1].

A client reads another player's updates in two series of different grain.
A remote player's `getLastRemoteUpdate()` on a client is the client's wall time at the last player packet it processed for that player, stamped by `GameClient.rememberPlayerPosition`, while a zombie's update stamp has no getter, so a client reads a zombie's updates only through its position [#3485/C/C-only].
The packet stamps advanced every 201 to 400 ms at the median, and every stamp gap was longer than 100 ms, so a count of gaps of 100 ms or more lined up with minute frames counts every gap and cannot see a frame shorter than the packet cadence [#3487/M/n=1].
The remote player's position changes on nearly every client frame, so a client-side effect is read off the position series, whose gaps resolve about one client frame, and off the stamps' distance from their grid, never off a stamp-gap count [#3488/M/n=1] [#3485/C/C-only].

## Walls and bounds
<a id="walls"></a>

Every live cost here comes off sessions with two real players on one host, each session n = 1, so each is a reading of that host and not a bound for any other [#3387/M/n=1] [#3405/M/n=1] [#3472/M/n=1].
A ghost load is cost and never behaviour, and its runs share two real player objects, so it carries the mod's per-run cost and none of vanilla's per-player cost [#3405/M/n=1] [#3440/M/arith.].
The sixty-player readings are ghost loads, a fed ghost costing 0.978 of a real player's minute over forty coarse pairs, so they price the mod's minute at sixty and not the frame vanilla itself takes at that load, which is unread [#3466/M/n=1] [#3472/M/n=1] [#3440/M/arith.].
Every consequence for a player's own actions of a long server frame is read from the loop; on a client only the frame interval and another player's motion and packet stamps were measured, on the server's host, with no zombies [#3429/C/C-only] [#2402/C/C-only] [#3486/M/n=1] [#3488/M/n=1].
The scheduler table reads the end-to-end period, and at sixty the burst's busy fitted inside the 100 ms period, one unexplained 136 ms start-to-start period in x244a aside, so its margins are headroom on this host and not the stall a player would see today (inference) [#3486/M/n=1].
The drift between arms of one session is about 0.6 ms a frame, so a total compared across arms on busy over idle is good only to that, and the empty-queue check sits below it [#3483/M/n=1].
The mechanisms are bytecode readings of one build, and a build bump moves their offsets and may move their behaviour [#3424/C/C-only] [#3427/C/C-only].
The clocks reading covers the global API and the `os` library only; a finer clock exposed elsewhere is not excluded [#3432/C/C-only].
The packet guard's effect on a connection was not read beyond its log line and its counter [#3430/C/C-only].
The engine's fake client puts no player on a server of this build as shipped, so no reading here carries vanilla's own per-player load beyond two real players [#3494/M/n=1].
The record size is an offline model of this mod's records in the save's format, corroborated by one live record's leaf count and by the live file's 10877 bytes a seeded copy [#3422/C/inference] [#3275/M/n=1] [#3468/M/n=1].
The sixty-player arithmetic assumes a run costs the same whatever its interval, which one fast-clock session supports, and the ghost loads at sixty ran at one interval [#3389/M/n=1] [#3440/M/arith.] [#3472/M/n=1].
The budgets were read at fixed caps of 5, 10 and 15 ms, so a cap sized to the minute's work as it changes is unmeasured [#3477/M/n=1] [#3492/M/n=1].
Not covered: a listen server or single-player, a player's own-action latency, real network latency, jitter or loss, zombies, load from more than two real players, whether a coroutine can yield across a protected call, and any reading from a populated public server.

## Open
<a id="open"></a>

- Whether healing once before the step saves live what it saves offline is unpriced: live, the two Nutrients heal passes are the two largest sub-blocks, 28.4 % of the minute, and offline a heal once before the step keeps the golden trace and saves 27.7 % [#3458/M/n=1] [#3413/C/inference].
- Whether a budget sized to the minute's work as the player count and the clock change keeps the frame flat at both spacings and under a fast clock, and what a budgeted queue's empty check costs a frame when benched directly, are unmeasured; at fixed caps a 15 ms budget starved none at sixty and the empty check was not resolved above the drift [#3492/M/n=1] [#3480/M/n=1] [#3483/M/n=1].
- Whether a player notices a long server frame through their own actions on server-owned state, over a real network or among zombies, is unmeasured: the client readings cover another player's motion on the server's host only [#3488/M/n=1] [#3429/C/C-only].
- Whether the jar's fake client gives per-player load on this build once each of its usernames has a saved character and each runs in its own JVM is untried: as shipped on `42.20.4` it was kicked at `player-connect` for want of a saved character, the `42.21` fake client creates one when it has none, and one JVM gave one connected client [#3494/M/n=1] [T1199.10] [#3496/M/n=1].
- What vanilla's own frame costs at a large player count is unread, and it sets the headroom a mod has; the shipped fake client could not supply it [#3440/M/arith.] [#3494/M/n=1].
- How much heavier a mass reconnect is than a typical minute is unmeasured; a day close, a seven-day catch-up and first sight's measured parts are not heavier a run, but first sight's 0.861 ms is a floor, so sixty joiners in one frame would cost at least 51.7 ms (arithmetic) [#3462/M/n=1] [#3463/M/n=1] [#3387/M/n=1].
- How a mod's own scheduler performs at sixty is unmeasured: `ghost.load`'s schedulers are the harness's own copies, so once a mod drains its own queue they no longer measure it, and measuring it needs the harness to feed ghost records into the mod's own queue, then a shoot-out of that queue against the 15 ms budget (inference) [#3455/C/inference] [#3489/M/n=1].
- A send's cost per key is unmeasured: one 138-key payload was priced, about 0.1 ms a send [#3464/M/n=1] [#3437/C/C-only].
- What a client's request of a global modData table costs the server's frame between 60 records and the 1,000,000-byte buffer, and when repeated, is unmeasured: at 60 it was within the idle jitter [#3469/M/n=1] [#3470/M/n=1].

## Procedure
<a id="procedure"></a>

1. Name the frame the change lands in: the event it runs on, and whether that event fires every frame, once a game minute or inside the minute's clock update.
2. Name how often that frame comes at the day lengths the server runs, and under a fast clock.
3. Name how its cost grows: flat, per player, per player ever seen, or per packet.
4. Stage the change, never `mod/`, and measure one run's cost on a live server with a bracket over many runs, stating the count.
5. Measure the frame at the target player count with `ghost.load` under the scheduler the change uses, reading `perf.local` for the frame's length and `tick.ring` for its attribution, against an idle baseline from the same session; `ghost.load`'s schedulers are the harness's own copies, so a scheduler that lives in the mod is measured only once the harness feeds ghost records into the mod's own queue, which is [open](#open).
6. Write the longest frame the change adds and how often it comes, with the readings' rows, and never the mean alone.
7. Turn on `gclog` when the change allocates per player, and line any stall up with the frames.
8. Compare arms on the ghosts' batch-timed milliseconds a minute event, and repeat each arm in alternation, because busy over idle carries the drift between arms.
9. Read a client-side effect off a per-frame series, never off a packet stamp slower than the effect.

## See also

- [lessons.md](lessons.md#rules) — the standing rules, the frame rules among them.
- [server-lifecycle.md](server-lifecycle.md#tick-order) — the time events in the lifecycle, the tick counts and the fast clock.
- [lua-platform.md](lua-platform.md#events) — the event roster, what a handler's raise costs, and the stat hook.
- [mp-model.md](mp-model.md#routes-client-to-server) — the routes a value travels, the global modData request among them.
- [client-ui.md](client-ui.md#tooltip) — the tooltip and its measured cost on a client.
- [harness.md](harness.md) — the instrument and its commands.
- [../facts/character-stats.md](../facts/character-stats.md#tick-order) — the player update inside `IsoWorld.update`, and where `OnPlayerUpdate` returns.
- [../facts/character-stats.md](../facts/character-stats.md#updaters) — the updaters that move a stat each tick, behind the sawtooth of a once-a-minute write.
- [../areas/testing-your-mod.md](../areas/testing-your-mod.md#walls) — the mod's own cost readings and their bounds.
- [jar-research.md](jar-research.md) — how the readings on this page were taken and re-checked.
