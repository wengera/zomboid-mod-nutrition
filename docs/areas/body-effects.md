# Body effects — driving the body from mod state
Verified against 42.20.4 (b0bbce05d5) · 2026-10-06 · scope: the nutrition-design reading of the levers a mod pulls when its own state is meant to move the body — a takeover of the stat update, the Strength and Fitness levels, carry capacity, the traits, health, the thermal core, perception and speed, activity read as an input, and the seats where mood, sickness, health, temperature and perception writes land; the stat registry and the updaters are `facts/character-stats.md`, the rates `facts/body-and-weight.md` and `facts/endurance-fatigue-sleep.md`, the perks `facts/perks-and-strength.md`, the hook surface `platform/lua-platform.md` and the pushes `platform/mp-model.md`

## Rules
<a id="rules"></a>

- Never register the stat hook unless your handler reproduces every updater it skips, [their side effects](../areas/body-effects.md#rules) included, and cannot raise: registration is all-or-nothing for every player on the server, the handler's return is discarded, a second registrant cannot restore the updaters, and a raise inside it leaves the stats frozen [#2737/C/inference] [#2238/C/C-only] [#2240/C/C-only] [#2236/C/C-only] [#0896/C/C-only].
- Integrate endurance in a takeover handler from the mod's own stored value, never from the stat it reads back: the player's endurance model runs earlier in the same server update than the hook, so the stat a handler reads already carries vanilla's drain or regeneration for that tick [#2699/C/inference] [#2235/C/C-only] [#2232/C/C-only] [#2596/C/C-only].
- Reproduce the seven non-stat side effects when a handler skips the updaters — the last-endurance stamp, the anger decay, the idle-square timer, the time-of-sleep advance, the thirst ghost-mode gate, the auto-drink call and the fitness stat's refresh: each lives inside one of the seven updaters the hook skips, so a registered handler stops all seven at once [#2700/C/inference] [#2724/C/C-only] [#2238/C/C-only] [#2215/C/C-only] [#2226/C/C-only] [#2227/C/C-only] [#0560/M/n=1] [#2250/C/C-only] [#2223/C/C-only].
- Never set a Strength or Fitness level above the one its experience implies: the rust pass lowers such a level one step per rust step, each step fires the level event whose listener rewrites the band traits, and neither the level setter nor the experience setter writes the other store [#2701/C/inference] [#2124/C/C-only] [#2127/C/C-only] [#2119/C/C-only] [#2103/C/C-only].
- Re-assert a clamped level and the traits the mod owns on a server schedule: the rust pass and the level event's listener move them on vanilla's own tiers, and an accepted experience sync loads the sender's whole level and trait lists over the server's [#2740/C/inference] [#2158/C/C-only] [#2157/C/C-only] [#2620/C/C-only] [#2612/C/C-only].
- Grant Strength or Fitness experience on the server through the `addXp` global, never to a sleeping character, and keep each check's growth under the anti-cheat bound: the short `AddXP` overloads do nothing on a dedicated server, the global does nothing on a client, a sleeping character's amount is dropped whole, and a tripped check can kick or ban the player [#2703/C/inference] [#2130/C/C-only] [#2105/C/C-only] [#2161/C/C-only] [#2147/C/C-only] [#2148/C/C-only].
- Move carry capacity on the server through `setMaxWeightDelta` and leave the base where it is: only the server's body-damage tick recomputes capacity, the delta multiplies the finished capacity after the Strength term, the moodle penalty and the floor on every recompute, nothing in the jar writes it after the player's constructor, a direct maximum-weight write lasts only until the next body-damage update, and the client learns the result from the damage packet's maximum weight [#2704/C/inference] [#2143/C/C-only] [#2142/C/C-only] [#2144/C/C-only] [#2145/C/C-only] [#2597/C/C-only] [#2713/C/C-only] [#2609/C/C-only].
- Give a mod effect a trait of its own rather than a vanilla band trait: the level event's listener removes every band trait of the perk before it adds one, and the weight refresh removes every weight-band trait before it adds one, so a band trait granted for any other reason is gone at the next of either [#2705/C/inference] [#2157/C/C-only] [#2722/C/C-only] [#0531/M/n=1].
- Change health through `ReduceGeneralHealth` and `AddGeneralHealth`, never `setOverallBodyHealth`: overall health is recomputed from the parts at the end of every server body-damage tick, so a direct write is replaced on the next tick unless it is exactly zero, which stops the tick and kills [#2706/C/inference] [#2344/C/C-only] [#2343/C/C-only] [#2346/C/C-only] [#2347/C/C-only] [#2349/C/C-only].
- Retune healing through the regeneration constants and the wound timers, never the injury speed modifiers: the constants and the timers are the healing handles that carry setters, the injury speed modifiers are read only by the injury speed term, and no healing-rate setter exists [#2707/C/inference] [#2354/C/C-only] [#2366/C/C-only] [#2368/C/C-only] [#2382/C/C-only].
- Drive the thermal core through `CharacterStat.TEMPERATURE`, rewritten on every update if the value is to hold: the stat is the one Lua door into the core, every step of the thermal update is private, no thermal node has a setter, and one write moves the core only one lerp step toward it on the next update [#2708/C/inference] [#2373/C/C-only] [#2374/C/C-only] [#2375/C/C-only] [#2376/C/C-only].
- Grant night vision or short sight through the Night Vision and Short Sighted traits rather than through the cone or the lighting bridge: the rendered cone is computed only on the client from inputs that include the trait list, the native bridge is unexposed, and neither the cone nor hearing range has a setter [#2709/C/inference] [#2298/C/C-only] [#2303/C/C-only] [#2301/C/C-only] [#2302/C/C-only] [#2333/C/C-only].
- Add to the aiming delay rather than replace it, and expect it rewritten after every shot: the combat manager rewrites it per shot as the current value plus the weapon's terms, clamped to the weapon's aiming time, and vanilla's rack action adds to the current value [#2710/C/inference] [#2326/C/C-only] [#2340/C/C-only].
- Move a player's speed through the inputs of the speed formula, the endurance stat behind the Endurance moodle first, never through a speed setter or a modifier field: the modifier fields are reset on every speed update, `setSpeedMod` and move speed reach no player path, base speed is cut per level of the Endurance and Heavy Load moodles, and no moodle level has a setter [#2711/C/inference] [#2289/C/C-only] [#2318/C/C-only] [#2319/C/C-only] [#2313/C/C-only] [#2285/C/C-only].
- Read a player's activity from the thermoregulator's metabolic rate, with endurance and carried load held still or accounted for, never from a counter: the engine keeps no distance, running-time total, step, rep or training-load counter, while the metabolic target is raised to a class floor by attacking, moving and exercising, can sit above a low class when endurance is low, and rises with carried weight, read from the bytecode, and measured on a server only as the rate: the server classifies a connected player through `getMetabolicRate()` while its target reads -1 at every tick [#2712/C/inference] [#2875/M/n=1] [#2633/C/C-only] [#2649/C/C-only] [#2197/C/C-only] [#2198/C/C-only] [#2200/C/C-only].
- Clamp a Strength level by writing it with `setPerkLevelDebug` below the experience-implied level and re-asserting it every slow tick, never by adding or removing experience: the write holds through the timed experience push, a rust pass and a mirrored admin sync (#2869 — a sync carrying a different level loads the sender's level over the server's, #2740, and the per-minute re-assertion is what answers it), it runs no band remap of its own so the remap is re-applied after it, and a vanilla level-up above the clamp is written back within a slow tick [#2902/C/inference, #2867/M/n=1, #2868/M/n=1, #2869/M/n=1, #2870/M/n=1, #2894/M/n=1, #2896/M/n=1, #2701/C/inference, #2740/C/inference].
- Write total mass into the vanilla weight slot and the three direction flags on every slow tick, whatever the last read held: any logged-in client can set any online player's weight through the `player` `setWeight` client command, which no handler or dispatch gates on a role, and with the `Nutrition` option off nothing else moves the flags [#2903/C/inference, #2643/C/C-only, #2644/C/C-only, #2883/M/n=1, #2885/M/n=1].
- Keep the engine's MET table and the model's own apart: bank a training dose on the engine's own MET value above its resting floor, bill expenditure on the model's table for the classified state, and divide the engine's load factor out of the rate before either use, with endurance accounted for (the tired floor also lifts the rate, #2649), so that a carried load is charged once: the engine's classes are one fixed table and its rate already carries the load factor [#2904/C/inference, #2632/C/C-only, #2649/C/C-only, #2875/M/n=1].
- Read activity on a server from the thermoregulator's metabolic rate alone, with its load factor divided out, and treat a runner as a walker until the run flag is measured to arrive: the target reads -1 there, the run and sprint flags never reach the server's copy of the player and a timed action's stack is empty server-side, so no other per-tick activity CLASS reaches the server (the moving flag arrives at ~75 % of ticks, #2877, and reps and hits arrive as events, #2879/#2880, but no run, sprint or action class does) [#2905/C/inference, #2875/M/n=1, #2877/M/n=1, #2878/M/n=1, #2712/C/inference].
- Run a nutrition mod's acceptance with the vanilla `Nutrition` sandbox option off, the design's precondition: with it on, vanilla's per-tick update rewrites the weight-direction flags and drifts the weight slot and the macro stores between the mod's minute writes [#2906/C/inference, #2884/M/n=1, #2883/M/n=1, #2886/M/n=1, #0555, #2885/M/n=1].
- Grant a mod trait on the server with the trait-block push in the same tick, put it back on a server schedule after an outside removal, and withdraw it only when the mod itself added it, never a copy it did not add: the granted Night Vision reached the client inside one round trip, an outside removal was undone by the next read, a grade-2 withdrawal took it off both sides and a Night Vision the mod had not added stood through about twelve slow minutes, while an admin experience sync carrying a list without the trait erased it from the server and a client-only removal was undone from the server at the first read [#3117/C/inference, #3059/M/n=1, #3093/M/n=1, #3094/M/n=1, #3095/M/n=1, #3096/M/n=1, #3067/M/n=1, #3068/M/n=1, #2620/C/C-only].
- Write a mood or sickness floor from the stat hook's handler, which runs after the body-damage tick, and only while the stat reads below its target, and hold a PANIC floor rather than raise it: the body-damage updaters add to or remove from the stored value and never set it, so what the handler leaves is the base the next update changes, a FOOD_SICKNESS floor therefore rose at 22.30 a game hour, its 25 less vanilla's 2.7 decay, and held, while a PANIC floor raised by about 0.064 an update read 0.0635 to 0.0643 at every one of 1300 samples because vanilla's decay of about 0.18 an update removed each rise, and a floor written whenever PANIC read under its target read exactly the target from the first sample that left 0 [#3118/C/inference, #2921/C/C-only, #3017/C/inference, #3014/C/C-only, #3048/M/n=1, #3116/M/n=1, #3082/M/n=1, #3101/M/n=1, #3102/M/n=1, #3084/M/n=1].
- Release an UNHAPPINESS floor when its target falls, by subtracting the fall once, because nothing in vanilla's updates lowers UNHAPPINESS but an antidepressant's term: the stat read 100 at every read after a window of writes ended, a floor rose 22.0 a game hour and held, and when its target fell from 25 to 4.1667 the one subtraction read 4.1667 at the first read [#3119/C/inference, #3016/C/C-only, #3033/C/inference, #3048/M/n=1, #3083/M/n=1].
- Drive a toxicity rung through a FOOD_SICKNESS floor at 85 or below with POISON at 0, never through SICKNESS and never at or above 90: vanilla decays FOOD_SICKNESS only while POISON sits at its minimum and decays SICKNESS never, SICKNESS being the thermal set point's fever term (37 plus twice its value), the SICK moodle reads FOOD_SICKNESS as a hundredth with SICKNESS added straight on and its last threshold is 0.90, and floors at 55 and 85 held with POISON 0 at every sample, the 85 floor with no damage tag, while a value of 95 fired the SICK tag at 287 of 300 ticks [#3120/C/inference, #3018/C/C-only, #3019/C/inference, #3024/C/C-only, #3025/C/arith., #2369/C/C-only, #3130/C/C-only, #3084/M/n=1, #3104/M/n=1, #3039/M/n=1].
- Fold a per-part effect by scaling the engine's own per-update delta of a timer, a bleeding time or an infection level, written in the one server tick that read it, never the shared growth rate, which also grows FOOD_SICKNESS while POISON is above zero: the folds read 0.6785, 0.8002 and 2.3055 of the engine's rate against the 0.68, 0.8 and 2.3 asked, while a fold driven as a read and a write a second apart reached 1.18 where it asked 2.3, each write overwriting the rise between its read and itself [#3121/C/inference, #2359/C/C-only, #2364/C/C-only, #2366/C/C-only, #3044/M/n=1, #3108/M/n=1, #3109/M/n=1, #3111/M/n=1, #3113/M/n=1].
- Drain health through the mod's own per-minute `ReduceGeneralHealth` behind a kill dial, with the four regeneration constants written to 0 while the drain runs and back to their defaults when it stops, and write them again at first sight because a reload returns the constructor's values: with the constants at 0 the rung-3 drain read 4.1709 health a game hour against 4.1667 and the scurvy drain 0.5985 against 0.5952, and the dial off stopped the drain by the first record read 7.8 s later with the constants at their defaults [#3122/C/inference, #3020/C/inference, #2346/C/C-only, #3040/M/n=1, #3104/M/n=1, #3105/M/n=1, #3106/M/n=1].
- Cap the HUNGER and THIRST views under moodle level 4 on every update whatever the mod's own dials say, at 0.69 and 0.83: the level-4 hunger and thirst terms are compiled into the body-damage tick, the THIRST one costing 11.88 health a game hour on the 60-minute day, an unfed character's HUNGER view rose to 1 with the HUNGRY damage tag firing at 600 of 600 samples, and the capped views read 0.69 on both sides over 406 server reads and 0.83 at all 55 server reads with no hunger or thirst tag [#3123/C/inference, #0508/M/n=1, #0509/M/n=1, #0518/C/arith., #0519/M/arith., #3035/M/n=1, #3074/M/n=1, #3103/M/n=1].
- Write INTOXICATION on every update from the mod's own value with the drunk-reduction value at 0, and write the 0 again after a reload: the decay runs on the body-damage tick before the hook so the handler's write is the later one, a reduction of 0 stopped the decay outright, a drink action's per-sip jump stood for one update before the next write replaced it, and the reduction value is not saved [#3124/C/inference, #2919/C/C-only, #2920/C/inference, #2921/C/C-only, #3054/M/n=1, #3056/M/n=1, #3086/M/n=1, #3087/M/n=1].
- Write an absolute TEMPERATURE target only while the write moves the core in the adjustment's direction, a target under the set point only while the core reads above it, because one write moves the core halfway toward the written value on the next update, so a write made with the core under the target warms it against the adjustment: the fixture's core rested 0.45 to 0.46 under the set point of 37, a target 0.2 under that set point sat above it, and the steady offset a target written every update holds is not measured [#3125/C/inference, #2373/C/C-only, #3046/M/n=1, #3100/M/n=1, #3115/M/n=1, #3047/M/n=1/open].
- Never write the aiming delay or `WalkSpeed` from a server-side multiplier until a seat for the write is measured: the engine cleared a written aim flag at 555 of 601 ticks so the delay read the weapon's aiming time, 25.00, at all 1563 samples and a delay written to 31.25 read 25.00 from the next sample, a `WalkSpeed` write was gone by the first sample a quarter second later, and an aim multiplier the server computed reached the client's mirror and a swing stub and was applied by nothing [#3126/C/inference, #2326/C/C-only, #2289/C/C-only, #2318/C/C-only, #2319/C/C-only, #3062/M/n=1, #3066/M/n=1, #3088/M/n=1, #3063/M/n=1/open, #2096/C/C-only/open].

## How it works

A nutrition mod that wants a diet to matter has to move something the body already reads, because no engine reader looks at a mod's own store.
This page walks the levers in the order a design meets them: the stat update itself, the two perks that carry strength and fitness, carry capacity, the traits, health, the thermal core, perception and speed, then the activity signal a mod reads rather than writes, and last the seats where the effects a diet drives are written.
Each lever's mechanism is stated on the facts page that owns it, and this page states what the lever costs a mod and which rule it forces.
Where a rule another page already states applies here, this page links it rather than restating it.
The store a mod keeps its own state in, the online id it must never key on and the transmit that moves a whole table are the rules of [the server lifecycle](../platform/server-lifecycle.md#player-store), at [its ids](../platform/server-lifecycle.md#ids) and [its global store](../platform/server-lifecycle.md#global-moddata).
The push a mod sends after a server-side trait write is a rule of [the sync area](mp-sync.md#rules), and the re-run of the band remap after a debug level write is a rule of [the lessons](../platform/lessons.md#rules).
The rule on registering the stat hook at all belongs to [the lessons](../platform/lessons.md#rules) as well.

<a id="takeover"></a>
### Taking over the stat update

The heaviest lever is the `CalculateStats` hook, because registering it replaces vanilla's per-character stat update rather than adding to it.
The stat update fires the hook and, unless it answers true, runs seven updaters in a fixed order: endurance, tripping, thirst, stress, the wake state, morale and fitness [#2724/C/C-only].
The hook answers true whenever any handler is registered, whatever the handler returns, so registration alone is the takeover [#2238/C/C-only].
Once one handler is registered a second mod's handler cannot restore the updaters, and a mod cannot count or list the registrants from Lua [#2240/C/C-only] [#2242/C/C-only].
What the hook surface is, and what it exposes to Lua, is [the hook surface](../platform/lua-platform.md#hooks); what each updater does is [the updaters](../facts/character-stats.md#updaters).
A handler is therefore not a filter on one stat: it is a promise to run every stat the seven updaters run, for every character that reaches the hook.

The takeover is server-side by construction.
On a multiplayer client the player's stat update returns before it calls the character's, so the fatigue reset, the hook and the seven updaters never run there for a player [#2236/C/C-only].
A handler registered in a client's Lua state is therefore never called for that player, and the stats it would write are the server's anyway [#0568/M/n=2].
The values a handler writes reach the owning client on the timed player-stats push, as [the packets](../platform/mp-model.md#packets) state [#0565/C/C-only].
Each side then recomputes its own moodles from its own copy of the stats, so the client's moodle follows the handler's write one push later [#0563].

Three things the hook cannot stop sit around it in the same server update.
The server resets fatigue to its default before the hook on every update unless sleep is both allowed and needed, so no handler can stop that reset [#2723/C/C-only].
The player's endurance model is a separate private method that runs earlier in the same update than the hook, so a handler's endurance write lands after vanilla's drain or regeneration for that tick [#2214/C/C-only] [#2235/C/C-only].
On a dedicated server that model runs inside the remote-player branch of the player's update, which returns before the local-player path that fires `OnPlayerUpdate` [#2232/C/C-only].
The nutrition update and the fitness object's update also run in that earlier stage, so a takeover touches neither the macro drain nor exercise regularity [#2234/C/C-only].
The body-damage tick, where panic, boredom, pain and sickness move, is outside the stat update as well and the hook never reaches it [#2352/C/C-only] [#2384/C/C-only].
The order of one server update of a player, up to the hook, is drawn at [the tick order](../facts/character-stats.md#tick-order).

The endurance consequence is [the rule](#rules) on integrating endurance from the mod's own value.
A handler that reads endurance back and integrates from it double-counts whatever vanilla's model already removed or restored that tick [#2235/C/C-only].
A handler that keeps its own endurance figure and writes it as the last word avoids that, and whether its write really is the last before the push is an experiment, not a reading (see [Open](#open)).
Endurance and fatigue both live on a fixed range that no setter widens, and every `Stats` write passes the stat's own clamp [#2208/C/C-only] [#2209/C/C-only].
A mod quantity wider than that range therefore cannot be held in the stat itself [#2209/C/C-only].

The seven updaters do more than write their stats, and [the rule](#rules) on the seven side effects names what a handler loses with them.
The character's endurance updater stamps the last-endurance value and honours the unlimited-endurance cheat [#2215/C/C-only].
The stress updater is the only anger write among the seven, and the awake path of the wake-state updater advances the idle-square timer and resets idleness in combat [#2226/C/C-only].
The player's sleeping path advances the time-of-sleep value its restoration gate compares against [#2227/C/C-only].
The thirst updater carries the ghost-mode gate on the thirst add, and it is the auto-drink method's only call site in the jar, so a handler also stops auto-drinking and the `AutoDrink` hook that method fires [#0560/M/n=1] [#2250/C/C-only].
The auto-drink method is public on an exposed class, so a handler can call it itself [#2250/C/C-only].
The fitness updater writes the `FITNESS` stat from the Fitness level and is private, so a handler that wants the stat fresh writes it from the same formula [#2223/C/C-only] [#2222/C/C-only].
A Fitness experience grant also rewrites that stat at the end of the grant, so the stat is refreshed on every Fitness grant even under a takeover [#2114/C/C-only].
The tripping updater's angle has no reader outside `Stats`, and the morale literal reaches no moodle, speed or combat term, so those two can be dropped at no visible cost [#2225/C/C-only] [#2228/C/C-only].

The seven formulas a handler reproduces are reachable from [the updaters](../facts/character-stats.md#updaters), which hands thirst and hunger to [the hunger and thirst rates](../facts/body-and-weight.md#hunger-thirst) and endurance and fatigue to [the endurance drain](../facts/endurance-fatigue-sleep.md#drain) and [the fatigue accumulation](../facts/endurance-fatigue-sleep.md#fatigue).
The thirst updater's add is server-gated and skips a player in ghost mode, so a reproduction without both gates adds thirst where vanilla adds none [#0560/M/n=1].
Whether a reproducing handler tracks vanilla's trajectory stat by stat is an experiment, listed under [Open](#open).
The other shape, leaving the updaters running and correcting after them, is one of the options below rather than a lever of its own.

A stat the mod registers is no shortcut around any of this.
A registered stat answers `get` and `set` but sits outside the fixed stat order, so no save and no sync carries it [#2211/C/C-only].

The mod's own live readings of this seat are on [testing-your-mod](testing-your-mod.md#scenario-inputs).

<a id="perk-level"></a>
### Strength and Fitness levels

The two perks are the body's long-term state, and a diet that builds or wastes muscle moves them.
A perk's level and its experience are two separate stores, and a write to one leaves the other where it was [#2101/C/C-only] [#2103/C/C-only].
The level is written outside a whole-object load by four methods only: `LevelPerk`, `LoseLevel`, the debug setter and `level0` [#2117/C/C-only].
The debug setter writes the level and nothing else — no experience, no level event — and pushes only from a client [#2119/C/C-only].
The experience setter writes the experience map to a level's cumulative total and leaves the level untouched [#2103/C/C-only].
The Java readers of the two levels read them live on every call, so a level write takes effect at each reader's next call [#2135/C/C-only].
The ladders those readers apply are [the level readers](../facts/perks-and-strength.md#readers).
A server `setPerkLevelDebug` write on its own held through the experience push, a rust pass and a mirrored admin sync [#2867/M/n=1][#2868/M/n=1][#2869/M/n=1], and it ran no band remap, so a writer re-applies the band itself [#2870/M/n=1][#2729/C/inference]; the clamp's rule is [in the rules](#rules).

Vanilla moves the levels on its own schedules, and every schedule is a writer the mod must expect.
The experience system raises and lowers a level only on crossings of a threshold, so a level a mod lowers is neither walked back up nor pushed further down by it [#2122/C/C-only] [#2123/C/C-only].
The one absolute test is Lua: the rust pass lowers a Strength or Fitness level whose experience sits below its stored level's requirement, one step at a time on its own tier [#2124/C/C-only].
Each such step fires the level event with a gained flag of false [#2127/C/C-only].
The event's listener rewrites the band traits and re-checks the recipes, so a level that moves without the event leaves every one of its jobs stale [#2129/C/C-only].
Both handlers that move a level or its traits outside Java are registered by one server file, so the level a mod's clamp reads can move on the rust pass's tier as well as on a grant [#2158/C/C-only].
So a mod that raises a level writes the experience with it, as [the rules](#rules) say, or the rust pass pulls the level back down.
The rule that a debug level write must re-run the band remap itself is [the lessons'](../platform/lessons.md#rules), not this page's.

Grants run through one route on a dedicated server.
The short `AddXP` overloads return unless the player is local, and no player is local on a server, so they do nothing there [#2105/C/C-only].
The `addXp` global routes to the server's grant on a server and does nothing on a client [#2130/C/C-only].
The server's grant reaches the six-argument body past the local-player gate and refreshes the anti-cheat's snapshot after it lands [#2132/C/C-only].
That body drops every amount to a sleeping character before anything else, whatever the perk [#2161/C/C-only].
It discards a non-negative amount once the perk's experience has reached the top level's total, so a mod's grant past the cap does nothing [#2109/C/C-only].
The `AddXP` event fires only off a multiplayer client, so on a dedicated server it fires on the server for every grant that reaches the store, as read from the bytecode [#2125/C/C-only].
The event fires at the end of the body, with the final amount, after the experience write and after any threshold crossing has already called `LevelPerk`, so a server-side listener sees each grant, its own and vanilla's, only after any level change it caused has happened [#2125/C/C-only] [#2126/C/C-only] [#2122/C/C-only].
A clamp therefore acts on the experience and the level together, through the setters and the level methods that hold each store, rather than by trimming a grant in that listener [#2103/C/C-only] [#2117/C/C-only].

The anti-cheat bounds how fast a mod may move experience.
On the server a perk whose experience rose by more than the bound between two checks is flagged, per perk and per check [#2147/C/C-only].
A failing check can log, kick or ban the user [#2148/C/C-only].
The check's interval and the option that enables it are unread, so a mod's safe grant size per check is not known (see [Open](#open)).

The level reaches the owning client whole, and the client cannot push one back.
The server pushes the whole experience object, levels and traits included, to each player's own connection on a timed push [#2608/C/C-only].
The receiver's load replaces its levels, experience, multipliers and traits rather than merging [#2620/C/C-only].
The only client-to-server route is the `SyncXp` global, which the server accepts only from a connection with the stats-panel capability [#2612/C/C-only].
An accepted sync fires neither the `AddXP` nor the level event on the server, because it loads the object rather than granting [#2614/C/C-only].
The vanilla admin panel sends that sync on every trait add or remove [#2615/C/C-only].
An admin's panel, the rust pass, the level listener and the weight refresh are all writers the mod does not control, so a clamp and an owned trait hold only if the mod re-asserts them, which is why [the rules](#rules) put the re-assertion on a schedule.
The perk-level packet carries three levels into remote fields only, never into the perk list [#2623/C/C-only].

The mod's own live readings of this seat are on [testing-your-mod](testing-your-mod.md#scenario-inputs).

<a id="carry"></a>
### Carry capacity

Carry capacity is the one Strength reader with its own levers, so a mod can move what a body can carry without moving the level.
The recompute sets carry capacity from the base times the Strength weight multiplier, less a moodle penalty, floors it at zero and, for a player, multiplies it by the player's delta [#2142/C/C-only].
The penalty's moodle terms are measured in one run, and [the moodles](../facts/body-and-weight.md#moodles) state them [#0513/M/n=1].
The base and delta setters are public, have no caller anywhere in the jar and are re-read on every recompute, and the delta lives on the player alone [#2143/C/C-only].
The Strength band traits reach the delta only in the player's two constructors, so a later level change that swaps those traits never refreshes it [#2144/C/C-only].
A Lua write to the maximum weight itself lasts only until the next body-damage update, because the recompute calls the same setter [#2145/C/C-only].
The unlimited-carry flag removes the limit but is written by the save load, the role setter and both arms of a packet, so it is contested [#2146/C/C-only].
The recompute is the server's, because the body-damage tick returns at once for a live player on a client [#2597/C/C-only].
The damage packet carries the player's maximum weight after the player id, written from `getMaxWeight` and applied on the receiver through `setMaxWeight` when the packet is consistent [#2713/C/C-only].
The server pushes that packet to each player's own connection on its timed injuries tick, so a client learns a new capacity on that push and not at the recompute [#2609/C/C-only].

The rule on carry capacity follows from where each setter sits in the formula.
The base is multiplied by the Strength term and then has the penalty subtracted, so a base write is entangled with the level a mod may also be moving [#2142/C/C-only].
The delta multiplies after the floor, so it scales the finished capacity and nothing reads it but the recompute [#2142/C/C-only] [#2143/C/C-only].
That no vanilla Lua calls either setter is unverified, because it rests on a hand scan of the install, as [the perks page](../facts/perks-and-strength.md#open) records.
A second mod that owns carry capacity collides with this one on the same field, and cooperative registration with such a mod is a rule of [the lessons](../platform/lessons.md#rules).
Where the carry penalty reaches speed, it does so through the Heavy Load moodle, under [perception](#perception).

The mod's own live readings of this seat are on [testing-your-mod](testing-your-mod.md#scenario-inputs).

<a id="traits"></a>
### Traits the mod grants or reads

Traits are the cheapest lever and the least stable one, because several vanilla writers rewrite the trait list wholesale.
Traits are applied on the server, and a character's trait list reaches that player's own client on the timed experience push and on the player-fields packet's trait block [#2595/C/C-only].
Both carriers replace the receiver's list rather than adding to it [#2617/C/C-only] [#2620/C/C-only].
No Java code sends the trait bit of the player-fields packet, so a server-side trait write reaches the client before the next experience push only if server Lua sends it [#2604/C/C-only].
Vanilla's own send of that bit is the book read's completion, with recipes and read books in the same push [#2606/C/C-only].
The global that sends it does nothing off a server and returns silently for a player with no connection [#2602/C/C-only].
Every one of those sends reaches the affected player's own connection and no other client's copy of that player [#2603/C/C-only].
The push itself, and when a mod sends it, is the rule of [the sync area](mp-sync.md#rules), linked rather than restated here.

Two vanilla writers strip band traits on their own schedule.
The level event's listener removes every band trait of the perk before it adds the one the level names, and the middle level gets none [#2157/C/C-only].
The weight refresh removes exactly the weight-band traits and no other, adds back the one the weight names and pushes nothing [#2722/C/C-only].
That refresh runs only when a counter of weight updates rolls over, so the band trait lags the weight unless something forces it [#0534/C/C-only].
A band trait granted for any other reason is therefore gone at the next level event or the next refresh, which is why [the rules](#rules) give a mod effect a trait of its own.
A mod's own trait is outside both sets, so neither writer touches it.

A new trait is real but carries nothing by itself.
The trait definition call is public, static and exposed, so a mod can register a trait that is selectable and saved [#1212/C/C-only].
Every effect such a trait has must be written in Lua, because no Java effect site tests a trait the engine does not know [#1158/C/C-only].
A trait is compared by the registry object, never by its name, which is a rule of [the Lua platform](../platform/lua-platform.md).
The character screen rebuilds its trait icon row whenever the client's trait list differs from the icons it holds, so a server-side trait write shows there once the list arrives [#2504/C/C-only].
Whether a weight-band trait can be relied on client-side is [the wall map's trait verdict](../reference/wall-map.md#g4).
Where a mod evaluates a band-keyed effect is [the band rule](mp-sync.md#rules).

<a id="health"></a>
### Health

Health is a part sum the server recomputes every tick, so a mod moves it through the parts or through the two general methods that spread an amount over them.
The body-damage tick is the server's in multiplayer: it returns at once for the local player on a client and restores full health for a remote one there [#2597/C/C-only].
The per-part update returns at once on a client for the local player, so every wound timer and per-part damage call is the server's too [#2598/C/C-only].
Overall body health is recomputed from the parts at the end of every tick and written through a raw field setter [#2344/C/C-only] [#2345/C/C-only].
A direct write to it is therefore replaced on the next server tick, except a write of exactly zero, which persists [#2344/C/C-only].
At exactly zero the tick returns before its regeneration, drain, pain, infection and recompute, while a negative value does not stop it [#2343/C/C-only].
A character at or below zero is killed by the server alone [#2349/C/C-only].
So a mod moves health through the two general methods, as [the rules](#rules) say.

The two general methods behave differently, and a design picks one by the shape it wants.
The reducing method wakes a sleeper when overall health is low enough, returns for a non-positive argument and otherwise spreads the loss over every part by its damage modifier [#2346/C/C-only].
The adding method divides its argument only among the parts below full health, so a heal concentrates on the damaged parts [#2347/C/C-only].
The engine's own fatal move is a reduction large enough that the recompute reads exactly zero [#2348/C/C-only].
The character's separate `health` field has its own setter, which refuses only an exact zero while invulnerable [#2350/C/C-only].
Every nonzero drain term reports itself to Lua through `OnPlayerGetDamage`, so a mod can listen to the drain rather than poll it [#2357/C/C-only].

Healing is a set of handles, not a rate.
The regeneration constants have public setters per character, so a mod retunes the whole regeneration ladder for one character [#2354/C/C-only].
The single severe-moodle constant scales every severe-moodle health-loss term together [#2355/C/C-only].
Wound healing is the wound timers counting down, and the timers and the poultice and splint factors are the per-wound handles with setters [#2366/C/C-only].
The injury speed modifiers on a body part look like healing rates and are read only by the injury speed term [#2368/C/C-only].
The engine has no healing-rate setter and no health-addition modifier [#2382/C/C-only].
So healing is retuned through the constants and the timers, as [the rules](#rules) say.
A part's wound-damage scale is fixed for its life [#2363/C/C-only].

A server-side health write reaches the owning client through the per-part push only.
The per-part sync global is the body-part packet's only sender, and its mask selects which part fields travel [#2607/C/C-only] [#2626/C/C-only].
The player-fields packet's body block carries the cold, infection and timer state and never health [#2618/C/C-only].
The injury diff channel reaches a watching player's client, not the owner's [#2610/C/C-only].
How a mod drives sleep or a knock-down is outside the health API: the sleep and knock-down setters are bare field writes [#2351/C/C-only].
The engine has no unconscious or fainting state for a mod to set [#2383/C/C-only].
The decoded regeneration switch and the drain table are [the health surfaces](../facts/health-surfaces.md#regeneration).

<a id="thermal"></a>
### The thermal core

A diet that changes how warm a body runs reaches the thermal model through one door.
Body temperature is a registered stat, not a body-damage field [#2372/C/C-only].
The thermal update lerps the core toward that stat whenever the two differ, then writes the core back into the stat [#2373/C/C-only].
A server-side write therefore moves the core one lerp step on the next update, after which the stat is driven from the core again [#2373/C/C-only].
A held temperature is therefore a stat rewritten every update, as [the rules](#rules) say.
Every step of the thermal update is private, and only the whole update is public [#2374/C/C-only].
The public writable surface beside save and load is a process-wide simulation multiplier, the two metabolic-target setters and the reset [#2375/C/C-only].
No thermal node has a setter, so insulation and node temperature are read-only from Lua [#2376/C/C-only].

Body fat already reaches the model, through weight.
The thermoregulator derives its fatness term from body weight, so a mod changes the fat effect only by changing the weight [#2378/C/C-only].
That term moves heat loss and heat generation each way [#2379/C/C-only].
Hunger and fatigue scale cold-side heat generation and thirst scales hot-side heat loss [#2380/C/C-only].
The thermoregulator reads no lipid store and no fat store of its own [#2381/C/C-only].
A nutrient that should change warmth therefore reaches it through weight, hunger, fatigue, thirst or the temperature stat, and through nothing the mod stores.
The model's terms are [the thermal door](../facts/health-surfaces.md#thermal), and what the thermal totals do to burn and fatigue is [the multipliers](../facts/body-and-weight.md#multipliers).

<a id="perception"></a>
### Perception and speed

Perception has no single quantity and no setter, so a mod reaches it through its inputs.
The rendered view cone is computed by the lighting bridge from fatigue, intoxication, Panic, worn items and traits [#2292/C/C-only] [#2294/C/C-only] [#2295/C/C-only].
That computation does not run on a dedicated server, because the lighting thread's creator returns there [#2301/C/C-only].
The lighting bridge is absent from the exposer's class set, so no mod Lua can call it [#2302/C/C-only].
A server-side mod moves the cone only by moving its inputs, which reach the client on the stats push and the trait carriers.
The server runs a visibility cone of its own from fatigue, intoxication, Panic and Eagle Eyed [#2305/C/C-only].

Night vision is a trait.
The Night Vision trait widens the rendered cone by a term that is largest in full darkness [#2298/C/C-only].
It also raises the player's render ambient to a floor whenever the computed ambient is below it [#2339/C/C-only].
Night-vision goggles are a render flag with no packet, so a server that sets them changes nothing the client draws [#2328/C/C-only].
Short sight is a trait too, and it is not the only distance input.
The engine hands the lighting bridge the Short Sighted boolean beside the detection range, a float the jar names `perceptionDistance` [#2303/C/C-only].
Short Sighted also drives a screen blur and collapses weapon sight range without glasses [#2329/C/C-only] [#2331/C/C-only].
The detection range is hearing range, built from the hearing traits, worn items, fatigue and intoxication [#2308/C/C-only] [#2309/C/C-only].
Neither hearing range nor the cone has a setter [#2333/C/C-only].
So the two traits are the levers, as [the rules](#rules) say, and what the native side makes of either distance input is outside the bytecode, so the design takes it as a decision (see [Open](#open)).
The trait constants and the clothing and spawn tables vanilla keys on them are [the perception traits](../facts/perception-speed.md#dynamic-traits).

Movement speed is the server's, and the client copies it.
A multiplayer client copies the network AI's walk or run speed rather than running the formula [#2599/C/C-only].
Off a client the formula runs and the server publishes the two speeds into the network AI object [#2600/C/C-only].
The injuries packet carries the walk and run floats to the client [#2624/C/C-only].
Base movement speed is cut per level of the Endurance and Heavy Load moodles [#2313/C/C-only].
No nutrition quantity, macro or body weight enters the speed chain [#2315/C/C-only].
The speed-modifier update resets the run, walk and combat modifiers on every call [#2289/C/C-only].
`setSpeedMod` reaches no player path, and a player's move speed reaches no engine path [#2318/C/C-only] [#2319/C/C-only].
No moodle level has a setter, so a mod moves the Endurance moodle by moving endurance [#2285/C/C-only].
A diet therefore slows a body by spending its endurance or loading its back, as [the rules](#rules) say.

Combat is split between the sides.
Combat speed is computed by the attacking client for its own player and by the server for everyone on the server, and it travels client to server in the hit packets [#2322/C/C-only] [#2323/C/C-only].
It answers to the Endurance and Heavy Load moodle levels, so a mod that drives the Endurance moodle moves swing speed with no combat code [#2324/C/C-only].
Knockback and the combat-speed modifier are not writable from Lua [#2338/C/C-only].
Melee delay is a gate read only on the pass a non-remote player takes, so a dedicated server never reads it for a connected player [#2321/C/C-only].
The aiming delay is rewritten after each shot from its current value plus the weapon's terms, clamped to the weapon's aiming time [#2326/C/C-only].
Vanilla's rack action adds to the current delay rather than replacing it [#2340/C/C-only].
A per-update aiming step writes the delay as well, which [the perception page](../facts/perception-speed.md#walls) lists as not covered.
A reaction effect therefore composes with both writers only as an addition, as [the rules](#rules) say.

<a id="activity-input"></a>
### Reading activity as an input

A diet model needs to know how hard the body is working, and the engine offers one scale for it.
`Metabolics` is an enum of activity classes in MET, exposed to Lua with getters and converters [#2631/C/C-only].
The thermoregulator's metabolic-rate update starts from the default class and raises its target to the class each state names: attacking, sprinting, running, sneaking, walking and exercising [#2633/C/C-only].
Each class is a floor rather than an assignment, so the highest class that applies sets the target [#2633/C/C-only].
The target is then raised twice more: a tired character's target can sit above a class below the endurance floor, and a loaded character's target rises by a carry factor [#2649/C/C-only].
The exercise floor is a flat class, and a per-exercise class reaches the thermoregulator only through the exercise action's per-frame target write [#2634/C/C-only].
The character declares no metabolic-rate getter; the rate is read through the thermoregulator's public getters [#2635/C/C-only].
The classes and their values are [the metabolic-rate classes](../facts/body-and-weight.md#metabolic-rate).

What the engine does not keep matters as much.
The engine holds no per-player distance-run, running-time total, sprinting-time or step counter [#2197/C/C-only].
It holds no per-day experience accumulator and no training-load concept [#2198/C/C-only].
It holds no exercise-rep or exercise-time counter beyond the last-done stamp per exercise type [#2200/C/C-only].
A mod that wants a training dose therefore builds it from what the server already sees, as [the rules](#rules) say.
On the server the player's coarse speed class is set from the network movement flag, and a consecutive-running timer resets whenever the player stops [#2334/C/C-only] [#2336/C/C-only].
Both are public fields with no accessor, and whether Lua can read them is not settled by the bytecode [#2337/C/C-only].

The server sees training events, not a training total.
The fitness object's update runs on a fixed in-game interval and is called with no side gate [#2163/C/C-only] [#2164/C/C-only].
A rep runs on the server through the state packet's handler, and its experience is granted through the server's grant truncated to an integer [#2184/C/C-only] [#2173/C/C-only].
`OnWeaponHitXp` fires on a dedicated server from the server's hit handling, so a server-side listener sees every hit [#2193/C/C-only].
Endurance has three event writers outside the per-update model — a swing, a vault and a rep — so a model that counts effort from endurance alone sees those too [#2269/C/C-only].
The exercise action sets a calorie modifier and a per-frame metabolic target [#2187/C/C-only].
A timed action's calorie modifier reaches the burn only at rest, because every moving branch of the calorie update overwrites it before use [#0462].
The server cannot read a connected player's current action: its character-action stack is empty there at every poll while the client reads the action and its calorie modifier [#2878/M/n=1].
The exercise reaches the server with no client command a mod could intercept [#2189/C/C-only].
The grants and their triggers are [the training signals](../facts/exercise-and-training.md#training-signals).

On the server the rate lags the activity and already carries the load factor [#2649/C/C-only], and it never reaches the running or sprinting classes, because those flags do not reach the server [#2875/M/n=1][#2877/M/n=1]. A rep and a melee hit reach a server-side listener as the `AddXP` and `OnWeaponHitXp` events [#2879/M/n=1][#2880/M/n=1], and the current action's calorie modifier is not readable there [#2878/M/n=1]. The rules say how to read activity on a server, and how to count a rep, [in the rules](#rules).

<a id="effects-seats"></a>
### The effects engine's seats

A diet that is to move mood, sickness, health, temperature or perception writes each of them at a seat, and each seat has its own owner in vanilla and its own road to the owning client.
This section states what the game does at each seat and what a mod can do there; [the rules](#rules) are its imperatives, and the numbers sit on [the tick order](../facts/character-stats.md#tick-order), [the health surfaces](../facts/health-surfaces.md#poison-infection) and [the perception page](../facts/perception-speed.md#combat).

Mood and sickness stats belong to the body-damage tick, and the tick increments rather than sets.
Its panic updater adds to PANIC for newly visible zombies and removes a decay each update, its boredom updater only ever raises UNHAPPINESS, and its illness updater decays FOOD_SICKNESS only while POISON sits at its minimum [#3013/C/C-only] [#3014/C/C-only] [#3016/C/C-only] [#3018/C/C-only].
The stat hook's handler runs after that tick in the same update, so what it writes is the base the next update changes [#2921/C/C-only] [#3017/C/inference].
A floor on a stat vanilla decays each update is therefore written whenever the stat reads under it: a rise of about 0.064 an update lost to the panic decay of 0.17957 an update, which was read directly, and the hold read its target from the first sample that left 0 [#3082/M/n=1] [#3116/M/n=1] [#3101/M/n=1].
STRESS and FOOD_SICKNESS floors rose at the net rate and held [#3080/M/n=1] [#3084/M/n=1].
Nothing in the engine but an antidepressant lowers UNHAPPINESS, which read 100 after its writes stopped, so a floor on it takes its own release [#3033/C/inference] [#3048/M/n=1] [#3083/M/n=1].
The client's copies of these stats trail the server's by up to about a second [#3049/M/n=1] [#3101/M/n=1].

Sickness has two stats, and only one is safe to move.
SICKNESS is read in three places and nothing decays it; it is the thermoregulator's fever term, the set point being 37 plus twice its value, so a held 0.30, 0.55 or 0.90 raises the target to 37.6, 38.1 or 38.8 °C [#3019/C/inference] [#3024/C/C-only] [#3025/C/arith.].
FOOD_SICKNESS feeds the SICK moodle, which reads it as a hundredth with SICKNESS added straight on, and the moodle's levels begin at 0.25, 0.50, 0.75 and 0.90 of its 0 to 1 scale [#2369/C/C-only] [#3130/C/C-only].
Floors at 55 and 85 held with POISON at 0 at every sample, the 85 floor with no damage tag, and a value of 95 fired the SICK tag at 287 of 300 ticks [#3084/M/n=1] [#3104/M/n=1] [#3039/M/n=1].
The moodle level at each value is read from the thresholds and not from the game, as [the moodle section](ui-and-moodles.md#stat-moodles) says.

Wound state is per part and the server's, and the part setters are the handles.
Every timer has a public setter on the part, and the engine counts an unbandaged timer down at its own rate [#2366/C/C-only] [#3113/M/n=1].
A server write of a part's `bleedingTime` reaches the owning client without the sync call after about a second, and with it at once [#3041/M/n=1].
A fold that reads a part and writes it back in one server tick, adding to the engine's own delta, reached 0.6785, 0.8002 and 2.3055 of the engine's rates against the 0.68, 0.8 and 2.3 asked [#3108/M/n=1] [#3109/M/n=1] [#3111/M/n=1].
The same fold driven from outside as a read and a write a second apart reached 1.18 where it asked 2.3, because each write overwrote the rise between its read and itself [#3044/M/n=1].
A bleed that counts down more slowly lasts longer, so the total it costs grows by about the square of the factor [#2365/C/arith.].
The cold's accumulator is the one seat no run could read: the engine adds to `catchACold` only in its wetness updater while the thermoregulator's delta is above 0.1, subtracts 0.175 an update unscaled below it, zeroes it at 100 and saves it with the character [#3021/C/C-only] [#3023/C/C-only].
A climate override of -10 and a soaked character left the delta at 0.0115 to 0.0222 and `catchACold` at 0 at all 32 reads, so no fold of the rise was exercised and its scaling is unmeasured ([X105](open-questions.md#x105)) [#3114/M/n=1].

Health has one lever that moves it and one that fights it.
The server's `ReduceGeneralHealth` reaches the owning client within about a second [#3040/M/n=1].
The four regeneration constants have setters per character and are not saved with it [#2354/C/C-only] [#3020/C/inference].
A drain written each minute with the constants at 0 ran at the rate asked, 4.1709 a game hour against 4.1667 and 0.5985 against 0.5952, and stopped at the next read after the drain's switch was turned off, the constants back at their defaults [#3104/M/n=1] [#3106/M/n=1] [#3105/M/n=1].
Whether halving the constants halves awake regeneration is open, because both windows read at hunger level 4, whose tier adds nothing ([X80](open-questions.md#x80)) [#3045/M/n=1/open].
The level-4 hunger and thirst terms are compiled into the body-damage tick, so a view stays under that level to avoid them whatever a mod dial says: an unfed character's HUNGER view rose to 1 with the HUNGRY tag at 600 of 600 samples, and the held views read 0.69 and 0.83 with no tag [#0518/C/arith.] [#3035/M/n=1] [#3074/M/n=1] [#3103/M/n=1].

INTOXICATION and TEMPERATURE each have a single door.
INTOXICATION decays on the body-damage tick at the drunk-reduction value times the multiplier, and that value has a public setter and is not saved [#2918/C/C-only] [#2919/C/C-only] [#2920/C/inference].
A handler's write is the later one, a reduction of 0 stopped the decay outright, and a drink action's per-sip jump stood for one update before the next write replaced it [#3056/M/n=1] [#3054/M/n=1] [#3087/M/n=1].
`CharacterStat.TEMPERATURE` is the one door into the core, and one write moves the core halfway on the next update [#2373/C/C-only] [#3046/M/n=1].
The set point is public and read-only, and the fixture's core rested 0.45 to 0.46 under it, so a target 0.2 under the set point still sat above the core and a write of it would have warmed the character [#3024/C/C-only] [#3115/M/n=1] [#3100/M/n=1].
What steady offset a target written on every update holds is unmeasured ([X81](open-questions.md#x81)) [#3047/M/n=1/open].

Traits, perception and speed are the client's to draw and the server's to grant.
Both trait pushes replace the client's list, and the engine fires no event when a trait is written [#2620/C/C-only] [#2601/C/C-only].
A pushed trait add reached the client's list 14 ms later, an admin client's experience sync without the trait erased it from the server, and a client-only removal was undone from the server by the next push [#3059/M/n=1] [#3067/M/n=1] [#3068/M/n=1].
Night Vision's ambient floor is reachable from no Lua, and Short Sighted collapsed a pistol's sight range from 6 to 2 on the client until glasses were worn [#3027/C/C-only] [#3060/M/n=1].
The three attack events fire on the shooting client [#3061/M/n=1].
A written aim flag was cleared by the engine and the delay sat at the aiming time, so the seat for a delay write is open ([X86](open-questions.md#x86)) [#3062/M/n=1] [#3063/M/n=1/open].
A `WalkSpeed` write was gone by the next sample, so that seat is open as well ([X47](open-questions.md#x47)) [#3066/M/n=1] [#2096/C/C-only/open].
A connected player's fall lands once, on the server, and a direct landing call on the client fires nothing [#3064/M/n=1] [#3065/M/n=1].

Fatigue and sleep have two more facts a mod meets.
On a server where sleep is neither allowed nor needed a FATIGUE written in the handler reached the client, as did one written on `OnTick` [#3057/M/n=1] [#3058/M/n=1].
No fatigue value wakes a sleeping player, and a bed sleep's length is set once, at its start, from FATIGUE [#3029/C/C-only] [#3030/C/C-only].

## Options

A body effect takes one of a few shapes on each lever, and the shapes differ in what they own and what they fight.
None of them is free, and the costs below are the rows above, gathered per choice.

### Takeover against overlay

A takeover registers the stat hook and runs every stat the seven updaters run, plus the seven side effects, for every character that reaches the hook [#2724/C/C-only] [#2238/C/C-only].
It owns hunger, thirst, stress, morale and the rest outright, and it collides with any other mod that registers the same hook, because a second registrant cannot restore what the first suppressed [#2240/C/C-only].
It cannot stop the server's fatigue reset or the player's endurance model, both of which run before it [#2723/C/C-only] [#2235/C/C-only].
An overlay leaves the updaters running and corrects the stats after them from a server-side handler later in the frame, whose place in the frame is [the server tick order](../platform/server-lifecycle.md#tick-order).
It owns nothing outright: vanilla's rates keep running, and the only sandbox dial on them scales hunger, thirst and fatigue together and never calories [#0553].
It composes with other mods, because nothing it does suppresses anyone else's code.
The direction flags the sides read are vanilla's own while the `Nutrition` option is on [#2884/M/n=1].
Which shape a design takes decides whether the seven formulas must be reproduced at all.

### Level clamp against experience clamp

A level clamp writes the perk level and leaves the experience where it is [#2119/C/C-only].
It fires no level event when it goes through the debug setter, so the band traits stay as the last real change set them [#2119/C/C-only] [#2129/C/C-only].
It is pulled back down by the rust pass whenever it sits above its experience [#2124/C/C-only].
An experience clamp holds the experience below a level's threshold and lets vanilla's crossing tests move the level [#2122/C/C-only] [#2123/C/C-only].
It keeps the level event and its listener in step only for grants the mod sizes before it issues them [#2122/C/C-only].
A vanilla grant that crosses the threshold has already raised the level and fired the level event by the time a server-side `AddXP` listener sees it, so the mod walks that level back with its experience after the fact [#2126/C/C-only] [#2127/C/C-only].
Both reach the client whole on the timed experience push [#2608/C/C-only].
Which store the design treats as the truth decides which vanilla writer it fights.

### Own icon column against a framework

A status icon the mod draws in its own column is anchored on the vanilla moodle stack's box, which is readable from Lua though the stack offers no mutator [#2509/C/C-only].
The column is code the mod owns end to end, drawn on the client from whatever the client holds.
A framework moodle rides a third-party mod whose wholeness on this build no run has confirmed [#1295/C/open].
A mod's own vanilla moodle type is not a third choice, as [the moodle route](ui-and-moodles.md#moodle-route) states.
Which one a body effect uses decides whether the mod ships a runtime dependency.

## Walls and bounds
<a id="walls"></a>

- The engine has no effective-strength concept: no setter overrides a Strength-derived modifier, and no Strength or Fitness level setter exists besides the generic perk methods [#2159/C/C-only].
- The engine has no lean-mass, fat-mass or aerobic-capacity field, so a body-composition model is the mod's own [#2159/C/C-only].
- The engine has no speed setter that reaches a player: the modifier fields are reset each update, `setSpeedMod` is zombie-only and move speed reaches no engine path [#2289/C/C-only] [#2318/C/C-only] [#2319/C/C-only].
- The engine has no walk-speed modifier, recovery, pacing or fatigue-multiplier setter in any class [#2287/C/C-only].
- The engine has no setter for hearing range, the view cone or the worn-item vision and hearing modifiers [#2333/C/C-only].
- `LightingJNI` is absent from the exposer's class set, so the view-cone computation and the native lighting bridge are unreachable from Lua [#2302/C/C-only].
- `MoodleStat` is absent from the exposer's class set, so the moodle thresholds are unreachable from Lua and a mod moves a moodle only through its stat [#2248/C/C-only] [#1141/C/C-only].
- No stat's bounds can be moved, so endurance and fatigue stay on their fixed range [#2209/C/C-only].
- The stat hook is a global compatibility wall: registration suppresses the updaters for every character that reaches the hook, its answer ignores what any handler returns, a second registrant cannot undo it, and no mod can read who registered [#2238/C/C-only] [#2240/C/C-only] [#2242/C/C-only].
- The wall map's verdict on skipping the stat tick is [its stat-tick row](../reference/wall-map.md#b8).
Not covered: the dragging-corpse, strength, temperature-state and discomfort sub-updaters of the body-damage tick, whose bodies are unread, the cold fold's scaling, and the steady offset a per-update temperature target holds; what the native lighting makes of the Short Sighted boolean and the detection range as distances; the per-update aiming step and the per-update melee-delay decay; the injury-speed helpers; the thermoregulator's own temperature formulas beyond the fat, energy and fluid terms; whether Lua can call the stat-registration static; the anti-cheat's scheduler and enabling option; and the sleep, knock-down and unconscious states as effects.

## Open
<a id="open"></a>

- Whether a handler that reproduces the seven skipped updaters tracks vanilla's stat trajectory stat by stat over several game-hours — settled by two boots of one fixture, with no handler and with the reproducing handler; -> [X34](open-questions.md#x34) [#2081/C/open].
- Whether a handler's endurance write is the last before the player-stats push — settled by a sentinel endurance written each tick and read in client-first pairs; -> [X35](open-questions.md#x35) [#2082/C/open].
- Whether the fitness object's update ticks on the server for a connected player — settled by a seeded exercise and two idle game-days, reading the server's regularity; -> [X36](open-questions.md#x36) [#2083/C/open].
- What the experience anti-cheat's check interval is, and whether a server-side burst of grants trips it — settled by a desk read of the enabling option and timed bursts either side of the bound; -> [X40](open-questions.md#x40) [#2085/C/open].
- Whether a client-side write to the `WalkSpeed` animation variable holds inside the injuries-packet window — settled by a client write sampled every quarter second; -> [X47](open-questions.md#x47) [#2096/C/C-only/open].
- Which side evaluates the Strength experience protein branch for a connected player, and against which side's protein value — settled by melee hits with the protein store raised on one side at a time; -> [X48](open-questions.md#x48) [#2087/C/open].
- Whether halving the four regeneration constants halves awake regeneration — settled by a damaged part read before and after the halving with the hunger, thirst and sickness moodles under the level that zeroes the tier; -> [X80](open-questions.md#x80) [#3045/M/n=1/open].
- What steady core offset a TEMPERATURE target written on every update holds — settled by a per-tick writer of an absolute target for game hours, reading the core and the set point; -> [X81](open-questions.md#x81) [#3047/M/n=1/open].
- Whether the aiming delay follows the jar's post-shot sum while a player really aims — settled by an aim held by input with the delay below the aiming time; -> [X86](open-questions.md#x86) [#3063/M/n=1/open].
- Whether a cold fold scales a `catchACold` rise — settled by an outdoor or wet-and-cold seat that lifts the thermoregulator's delta over 0.1 for game hours; -> [X105](open-questions.md#x105) [#3129/M/n=1/open].
- Decision: takeover or overlay for the stats a diet moves — a takeover suppresses all seven updaters for every player and cannot be undone by another mod, while an overlay leaves vanilla's rates running [#2238/C/C-only] [#2240/C/C-only].
- Decision: which store is the truth for a clamped Strength or Fitness — the level and the experience are separate stores, and each is moved by a different vanilla writer [#2101/C/C-only] [#2124/C/C-only].
- Decision: how large a single server-side grant the mod issues — a tripped anti-cheat check can kick or ban and its interval is unread [#2147/C/C-only] [#2148/C/C-only].
- Decision: whether a warmth effect writes the temperature stat every update or accepts the single lerp step of one write [#2373/C/C-only].
- Decision: which distance input a sight effect goes through, the Short Sighted boolean or the detection range — both reach the native lighting, whose use of either is outside the bytecode [#2303/C/C-only].
- Decision: whether an activity-scaled quantity reads the metabolic-rate classes or classifies the player itself — the classes are floors raised by endurance and load [#2633/C/C-only] [#2649/C/C-only], and on a server the rate is what classifies a connected player, the target reading -1 there [#2875/M/n=1].

## See also

- [`../facts/character-stats.md`](../facts/character-stats.md#updaters) — the seven updaters, their side effects and the tick order around the hook.
- [`../platform/lua-platform.md`](../platform/lua-platform.md#hooks) — the hook surface and the exposer's class set.
- [`../facts/endurance-fatigue-sleep.md`](../facts/endurance-fatigue-sleep.md#drain) — the endurance model, fatigue and sleep a takeover reproduces.
- [`../facts/body-and-weight.md`](../facts/body-and-weight.md#metabolic-rate) — the metabolic-rate classes, the weight-band traits and the hunger and thirst rates.
- [`../facts/perks-and-strength.md`](../facts/perks-and-strength.md#level-writes) — the level and experience stores, the grants, the rust pass and carry capacity.
- [`../facts/exercise-and-training.md`](../facts/exercise-and-training.md#training-signals) — the exercise object and every training signal the server sees.
- [`../facts/health-surfaces.md`](../facts/health-surfaces.md#health-api) — the health API, healing handles and the thermal door.
- [`../facts/perception-speed.md`](../facts/perception-speed.md#vision-cone) — the view cones, hearing, speed and combat.
- [`../platform/mp-model.md`](../platform/mp-model.md#sync-globals) — the pushes that carry the stats, the experience object and the trait list.
- [`mp-sync.md`](mp-sync.md#rules) — the trait push and the band rule.
- [`ui-and-moodles.md`](ui-and-moodles.md#moodle-route) — the moodle route and the display surfaces.
- [`open-questions.md`](open-questions.md#x34) — the experiments this page waits on.
