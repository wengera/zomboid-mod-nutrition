# The harness
Verified against 42.20.4 (b0bbce05d5) · 2026-09-30 · scope: the instrument every measured row in this library was taken with — the `pzt` orchestrator, the profile, the sandbox block, the driven client, the command bus and how a reply is read, probe and witness design, scenarios, cadence and game time, artifact and driver discipline; the command inventory itself is generated into `reference/harness-commands.md` and the named experiment specs are `reference/experiments.md`.

## Rules

- Never read a green run as evidence that a mod loaded: the game answers a mod it cannot find with a warning and a clean boot, so the run fails fast at the server-started mark and the bus probes are what prove effect [#1793].
- Name a profile's mod by the engine-resolved id: that is the `id=` of the `mod.info` the build actually reads — the newest `42[.x[.y]]/` folder first, then `common/`, then the mod root — and never the folder name [#1558].
- Gate a probe that can stall the client on the server side: verification is asked only after the client is ready, so a stalled session's client row never runs and the run records a verification error instead of a pass or a fail [#1769/M/n=1].
- Cap the client wait in the profile whenever a probe can hang the client: the readiness wait is capped from the profile's client timeout, whose default is 300 seconds, and a profile that leaves the default sits out the full wait plus teardown — 384 seconds for a five-second hold — on a client that was never going to answer [#1768].
- Never launch a client in safe mode: it turns a seventeen-second world load into about 120, roughly seven times slower [#1711].
- Put every Java member call behind the index-first guard: a guarded call never raises and the argument-slot protected call never reaches the failure helper, while an unguarded raise, or a nested protected-call raise the mod catches, stalls the driven client [#1714/M/n=1].
- Take the measurement on the side that owns the quantity: for nutrition, hunger and thirst, item aging and perks the server's reading is the measurement and the client's is a once-a-second mirror [#1826].
- Ask a probe of both sides: the acceptance profile put the same trait check to the server and to the client and both returned the mod's effect, so the mod was present in both Lua states and not merely in the server's [#1825/M/n=1].
- Choose a modData exclusion set per scope and apply it to that scope and no other: an item census excludes the custom name and the tooltip, both of which vanilla writes into item modData itself [#1234/M/n=1].
- Report a member this build does not expose separately from a zero: a zero and an absent accessor are different findings, so a census reply names the members it could not read rather than leaving them silently absent, which is what keeps a false flag distinguishable from an unexposed member [#1725].
- Ask the field witness for zero-argument getters only: an arity mismatch is as fatal as a nil call, which is also why a two-call perk-experience read needs a command of its own [#1742].
- Reconcile a reply against the names that were sent and never against its count alone: the count is names read while the fields bucket is a map keyed by getter name, so their sizes add up only when every name asked for was distinct [#1744].
- Test a list for emptiness with a falsiness check or with the reply's own counts: the encoder renders an empty Lua table as an empty object, harness-wide, so a comparison against an empty array and an index both fail [#1751].
- Read the server error list rather than quoting its count: the pattern is applied to every non-indented server line that no baseline-noise pattern whitelists, so the number is a classifier's output and not a fault count [#1764].
- Keep `24 × speed / day_minutes` at or below about eight game-minutes per wall second: at the fixture's ninety-minute day and a multiplier of thirty, which is exactly eight, three runs recorded 7.99, 7.99 and 8.00 world-minutes per wall second with exactly one tick per game minute [#1814/M/n=3].
- Make every timing step a predicate with a budget and never a sleep: the world-ready barrier is a harness handshake rather than a timer [#1845].
- Record the measured window rather than the requested sleep, and name a snapshot tag by its measured offset rather than its intended one: one driver's window field read 10.0 seconds where the reads' own wall stamps give 12.54, and its tag named for three seconds after a transmit actually opened 7.58 seconds after it, so that driver's own window and tag keys are do-not-cite for exactly this reason [#1708/M/n=1].
- Copy every piece of measured evidence a document cites into a tracked per-run artifact folder as JSON, kept byte-identical: the full run directories with their logs stay local and untracked [#1705].
- Treat a scenario verdict as the test and the evaluator and a clean session together: exit code 0 needs the harness test's own pass, the evaluator's agreement and no environment fault, each of which turns the result into a failure naming its count, marks the timeline and lands in the faults block of both the report and the committed artifact [#1785].
- Read a run's exit code as a statement about the whole session and not only about the test: it is 0 only when the session had zero non-baseline server errors and no client Lua errors, the three fault reasons being a mod the game did not load, a non-baseline server error line and a client that logged a Lua error [#1702].

## How it works

<a id="pzt"></a>
### `pzt`, the orchestrator

The orchestrator ships seven commands — provision, boot, attach, run, scenario, spike and doctor — each with what it does and what it costs, from a roughly two-and-a-half-minute fixture provision through a fourteen-second warm boot to a one-minute run plus its hold; the inventory and its costs are the harness as it stood on one machine [#1701].

| Command | What it does | Cost |
|---|---|---|
| `provision --name default` | Fresh server (fixed sandbox: `Zombies=6` = none, override with `--sandbox K=V`), the `admin` client joins, creates the world and its character, quits cleanly; server stops; snapshot → `testing/fixtures/default/` | ~2.5 min, once per game/mod-set version |
| `boot --fixture default [--hold N]` | Restore the fixture's server world into a fresh run dir and start it | ~14 s |
| `attach --fixture default --server 127.0.0.1:27261 --user admin` | Restore that user's client cache, launch the client, wait until it is in-world (no creation screens), ping it | ~35 s |
| `run --fixture default [--profile <name>] [--hold N] [--clients a,b]` | boot + attach every fixture client + hold (the test slot) + graceful teardown + `report.json` (timeline, events, collected results); exit code 0 only with zero non-baseline server errors and no client lua errors. `--profile` puts a named mod set + sandbox overrides on the fixture and runs the profile's `[[verify]]` probes; a failed probe skips the hold. The **missing-mod fail-fast is not `--profile`'s**: it runs on the plain path too, right after `server_started` and before any client is launched, because a fixture's own recorded `Mods=` can stop resolving just as a profile's can — and it makes the RESULT line name the mod | ~1 min + hold |
| `scenario <name> [--side server\|client] [--speed N] [--timeout S] [--fixture F] [--profile <name>]` | run one registered harness test at accelerated time: boot + attach the subject client, `test.list` on the chosen side, RCON `settimespeed <N>`, `test.run <name> <user>`, wait for the result doc, **then the Python evaluator for that name, and only then** `settimespeed 1` + teardown from the `finally` — that order because the evaluator is scenario code that can raise, and a raise must not skip the speed restore; report and artifact are written last. `--profile` runs it on a named mod set (the profile's fixture wins over `--fixture` and its first client over `--user`; its `[[verify]]` probes **are** run on this path, once the client is ready, and a failed one folds into the result as `FAIL: verify <cmd>` after the test — plus the cadence ceiling on `DayLength` × `--speed`). The scenario artifact carries `profile` and `verify` on **every** run, `null` and `[]` when there is no profile | ~1 min + the test (3 game-days at `--speed 30` ≈ 10 min) |
| `spike S3 S4 S5 S6 S7 [--reloadalllua]` | the design spikes as scripted experiments; S3 boots its own sessions, the rest share one; findings → `runs/spike-*/findings.json` | 2–5 min |
| `doctor` | cold-start checks before booting anything: stray PZ `java.exe` (reported, never killed), ports 27261/27262/27015 free, fixture present and build-matched, workshop index reachable, pytest available; exit 1 on a FAIL | seconds |

The orchestrator's own folder-to-id rename is the one harness behaviour that needs a regression subject chosen deliberately rather than taken from whatever is installed.
The subject the verdict picks is the long-term-preservation mod, whose folder `SKITTLE_LongTermPreservation4220` and declared id `LongTermPreservation4220` differ by a whole prefix: that answers both halves of the question, because the run's mods listing names it and a wrong name would fail to load [#1657].
A case-only subject answers one half and cannot reach the other: the filesystem is case-preserving, so the listing after a run names whichever spelling the installer wrote, while path lookup is case-insensitive, so the mod loads either way and the run proves nothing about whether the rename is required [#1656].

<a id="profiles"></a>
### The profile: one file per named combination under test

A profile is one file per named combination under test: which golden fixture to restore, which mods go into the server's mod list and where each is copied from, which sandbox options to override, which client accounts to attach, and which bus probes have to answer before the session counts as the session that was asked for [#1789].
One declarative file replaces every hand-edit, and everything it asks for is resolved and validated before a single process starts — so a bad mod id or a misspelt sandbox key costs a second instead of a boot, and any key outside the known set is a pre-boot error naming that set, so a profile cannot typo its way into a silent no-op [#1790].
A profile never mutates the fixture: mods overlay a restored per-run copy and the sandbox block is merged into that copy's own options file rather than replacing it, the fixture excluding the mods folder from its snapshot so the overlay is rebuilt every run [#1792].
The fixture snapshot takes the server's configuration, database, saves and options and the client's options, saved-server database, Lua folder, saves and debug options, and deliberately excludes the mods folder, which is re-installed at boot and attach so a fixture never pins a stale harness [#1861].

The schema is fourteen documented rows over seven tables — the fixture, a description, four per-mod keys, a sandbox table, the two timeouts, the client users, the safe-mode and launcher keys, the hold, and the verification row's four keys — every one optional with the command line's own defaults, so a profile only says what differs; the loader's own key sets give seventeen leaves, because the fourteenth documented row bundles the four verification keys [#1796]. The two `[server]` booleans in the table and the top-level `clients` key described under [the driven client](#driven-client) were added after that count and are in neither figure.

| Key | Type | Default | What it does |
|---|---|---|---|
| `fixture` | string | `"default"` | The golden fixture restored for the run. It **wins over a typed `--fixture`** (it is the fixture the `[sandbox]` keys were validated against); the conflict is printed, not swallowed |
| `description` | string | `""` | Free text, carried into `report.json["profile"]` so an artifact says what the run was for |
| `[[mods]]` `id` | string | — | The name that goes in `Mods=`. A harness id resolves to the repo folder; any other bare id is looked up in the workshop index |
| `[[mods]]` `workshop_id` | string | — | Resolve from `<WORKSHOP_DIR>/<item>/mods/*`. An item shipping more than one mod needs `id` as well, and the error lists what it ships |
| `[[mods]]` `path` | string | — | An explicit folder — absolute, or relative to the repo root. This is how a mod that is not on the workshop (ours, once it exists) goes under test |
| `[[mods]]` `copy` | bool | `true` | `false` = named in `Mods=` and placed **nowhere**: the missing-mod path, reproducible with nothing installed. Needs an explicit `id`, since there is no `mod.info` to read the name from |
| `[sandbox]` | table | `{}` | Top-level `SandboxVars` options merged into the restored fixture's file. A key that is not a settable option of *that* file is a hard error before boot, with the three closest names — **except on a machine that has no fixture cache**: the caches are gitignored per-machine blobs, so on a fresh clone `check_sandbox` finds no file, checks nothing and a typo survives to the run (which cannot start anyway, the fixture being unprovisioned) |
| `[server]` `timeout` | int | `420` | Seconds to wait for `*** SERVER STARTED ****` |
| `[server]` `SleepAllowed` / `SleepNeeded` | bool | the fixture's ini (false, false) | Written into the server ini at seed, verbatim, so a boot reads them; a profile without the keys leaves the fixture's values. A sleep reading needs both true: with either false the server's fatigue reset erased each fatigue write at the next update [#2947/M/n=1, #2948/M/n=1, #2793/C/C-only] |
| `[client]` `timeout` | int | `300` | Seconds to wait for a client to reach in-world |
| `[client]` `users` | list | `["admin"]` | The accounts to attach. `pzt run` launches all of them; `pzt scenario` attaches the first as the test subject. An **empty** list is a pre-boot error, not "server only": `pzt run` would fall back to the *fixture's* client list and `pzt scenario` would raise on `users[0]` — a client-less run is not wired. This is the older spelling of the top-level `clients` key described under [the driven client](#driven-client), kept for the profiles written before it: naming both is allowed only when they agree, and `users` alone is not checked against the fixture |
| `[client]` `safemode` | bool | `false` | Never set it: `-safemode` turns a 17 s world load into ~120 s |
| `[client]` `launcher` | `"java"` / `"exe"` | `"java"` | Validated against argparse's own choices, which a profile would otherwise bypass |
| `[run]` `hold` | int | `5` | Seconds to hold the session open after `session_ready` — the test slot of `pzt run` |
| `[[verify]]` `side` / `cmd` / `args` / `expect` | array of tables | `[]` | Bus probes run **after the client is ready**, on both entry points — between `session_ready` and `hold` on `pzt run`, and between `client_ready` and `test.list` on `pzt scenario`, which has neither of those marks. `side` is `server` (default) or `client`; `expect` is a **string**, matched as a substring of `json.dumps(parsed ack)`, so a JSON fragment like `'"keenPerceptionLoaded": true'` matches at any nesting (a number is coerced; a TOML boolean is rejected pre-boot, because `True` could never match JSON's `true`). A failed probe makes the result `FAIL: verify <cmd>`, and on `pzt run` it also **skips the hold** — the test slot must not open on a session that is not the session that was asked for |

The profile's own fixture wins over a typed fixture flag, and the conflict is printed rather than swallowed, because it is the fixture the sandbox keys were validated against; every other typed flag beats the profile, which beats the module defaults, and because the argument parser cannot report whether a flag was typed, the two entry points clear five flags' defaults to a null and that null is what not given means [#1797].
The profile mark is the run's first timeline entry, before anything is launched, and it is the only place the log says that a later not-found mod was intended; the report then grows a profile block carrying what was asked for and what it resolved to, and a verification block, while a profile-less run's report keeps exactly its old keys [#1801/M/n=1].
A profile cannot be attached to a running session: the attach command builds a server stub and never installs mods, so the flag is rejected by the argument parser rather than accepted and ignored [#1812].
A profile naming a mod by the workshop item rather than by the mod id is a defect whenever the item ships more than one mod, and at least one installed item shipped three in the 2026-09-10 corpus snapshot [#1617/C/snapshot].

A mod entry resolves through six branches in a fixed order, and every miss raises before a process starts, naming the paths it looked at; for the folder and workshop branches the id comes from the folder's own mod-info file, with no id pointing the reader at the layout lint and a disagreeing id quoted both ways rather than picked between [#1799].

| Entry | Source folder | Fails when |
|---|---|---|
| `copy = false` | none — named in `Mods=`, deliberately unplaced | no explicit `id`; `copy` is not a bool; the id is the **harness** (`PZTestKit`) — no harness means no bus, no ready marker, no probes |
| `path = "…"` | the folder, absolute or repo-relative | not a directory (the error quotes the raw *and* resolved path); `workshop_id` is set as well (two sources for one mod, and the branch order would silently drop the id) |
| `workshop_id = "…"` | the item's single `mods/*` folder | the item is not installed; it ships >1 mod and no `id` picks one; no folder under it declares that `id` |
| `id` in `HARNESS_MODS` | `testing/PZTestKit/PZTestKit` | — |
| `id` alone | the workshop index entry | not a harness mod and not installed (the error carries the index size and the workshop root) |
| none of the above | — | always: "needs one of: id, workshop_id, path" |

The branch order is what makes an explicit folder beside a workshop id an error rather than a silent drop, and duplicate ids across two entries collapse to one name in the mod list [#1799].
The harness mod is prepended when a profile does not list it, because without it there is no command bus, no ready marker and no probes [#1800].
A mod entry with copying turned off is named in the mod list and placed nowhere, which is the missing-mod path reproducible with nothing installed; it needs an explicit id, since there is no mod-info file to read the name from, and the harness id is refused for the same reason [#1798].

Placement is a copy because a no-Steam client searches nothing else: every mod a profile names is copied into the per-run cache on both sides from one source map, the workshop-items line is written empty and the numeric workshop id survives only as provenance [#1791].
Copying is the only mechanism: the installer copies each source folder into the cachedir's mods folder, harness mods from the repository and everything else from the profile's source map, which wins over both the harness map and the workshop index [#1803].
The copy strategy is the seed of the profile builder: the orchestrator indexes the workshop tree by the id declared in each mod's version-folder mod-info file and copies by folder name, while the installer places harness mods from the repository and everything else from that index [#1865].
The harness copies every profile mod source to a folder named for the mod id, so a run's mods listing always shows ids rather than the source folder names; the rename is a convenience of the harness and not a loader requirement [#0836].
Every profile mod takes that rename whichever way it is named, because both profile branches return a non-empty source and the installer copies anything with a source to a folder named for the mod id — so no profile mod entry can reach the name-keeping fallback at all, which belongs to the plain non-profile path [#1804].
The measured placement half is that a profile source lands under its declared id: the teardown run's own mods listing held the id, the source folder name was absent anywhere, the mod-info file was found under the id folder and the configuration file's mod line named the id — and the mod demonstrably loaded [#1833/M/n=1].
A second session reproduced the same placement reading, the run's server mod listing carrying the declared id with no folder-named directory present [#1453/M/n=1].
A profile run's mod-folder metadata is not an answer to the folder-rename question, however: on this filesystem the two spellings of the folder are the same directory, and no profile can reach the installer's folder-name-keeping branch at all, because every profile mod carries a non-empty source and the fallback belongs to the plain non-profile path [#1506/C/C-only].
The workshop-items line stays empty: the seeding code writes it from a list no profile fills, and the numeric id survives in the report as provenance only — what makes a run re-subscribable, not what makes it load; clients log a missing-setting warning for the empty value and it is baselined noise [#1805/C/C-only].
Both sides are seeded from one source map, the client defaulting its mod sources and skip list to the server's so the two cannot drift, and after the acceptance run both the server's and the client's mods directories held exactly the two mods with the client's own enabled-mods file naming both in the same order [#1823/M/n=1].

Four things close the missing-mod hole, in cost order, and only the third of them proves effect rather than arrival; the design states the first net's cost and the other three costs are read off where each net sits in the run [#1818].

| Net | What it does | What it costs |
|---|---|---|
| pre-boot resolution | turns almost every way to get it wrong into an error before a process starts | a second |
| the fail-fast | runs immediately after the server-started mark and before any client is launched, marks the missing mods, copies up to five of the server's own warning lines into the timeline and raises; it runs on the plain path too, because a fixture's own recorded mod list can stop resolving just as a profile's can | a server boot |
| the verification probes | the only one of the four that proves effect rather than arrival | the whole session up to the client being ready |
| the end-of-run net | taken after teardown, so the server's closing log lines count | the whole session |

The end-of-run net is the only one of the four that catches a client-side missing mod, because it unions the server's not-found list with every client's where the fail-fast reads the server's alone; it cannot save the cost, only the verdict [#1819].
The missing-mod run cost 23 seconds wall and exited 1 against the two-mod run's 93 seconds, its timeline running from the profile mark through server launch, server started, mods not found, the copied warning line, an error mark, the server stop and the faults mark — with no client launch phase at all and no clients directory in the run folder [#1820/M/n=1].
Turning copying off is what makes the missing-mod path reproducible on any machine — the mod is named in the mod list and placed nowhere, so nothing has to be installed or uninstalled — and the client side is not spared it either, the enabling step still naming a skipped id in the client's own mod file so both sides walk the same road [#1822].

A verification expectation is matched as a substring of the dumped JSON acknowledgement, which is deliberately forgiving because it matches at any nesting and therefore cannot express not present or a numeric comparison; a probe that needs either belongs in a scenario with a Python evaluator, and a number is coerced while a boolean is rejected pre-boot [#1828].
A failed verification probe makes the result a named failure, and on a plain run it also skips the hold, because the test slot must not open on a session that is not the session that was asked for; on a scenario the probes run once the client is ready and a failure folds into the result after the test has run, because the time is already spent and the evidence is worth writing either way [#1829].

<a id="sandbox"></a>
### The sandbox block: what a profile may change on a restored world

The sandbox block merges and does not replace: writing a partial options table on a restored fixture would silently reset every option the world was provisioned with, so the merge rewrites only the named four-space keys in place, keeping the server's comments, the five nested tables and the file's line endings, and the seeding code picks it whenever the restored cache already has the file [#1806].
The server rewrites the whole options file on boot, which is what the merge has to survive [#1806].
A sandbox key that is not a settable option of the restored fixture's own file is a hard error before boot with the three closest names — except on a machine with no fixture cache, where the validation finds no file, checks nothing and a typo survives to a run that cannot start anyway [#1810].
A sandbox option set through the live setter applies at once on a running dedicated server with no push, measured on the server side of one fixture and one run [#0556/M/n=1].

A profile's sandbox value survives the server's own boot-time rewrite beside the fixture's [#1807/M/n=1].

| Measure | Fixture (before) | Run copy (after seed **and** the server's rewrite) |
|---|---|---|
| `DayLength` | `4` | **`1`** — the profile's value |
| `Zombies` | `6` | **`6`** — the fixture's value, untouched |
| Four-space assignments | 189 | 189 |
| `sandbox_keys()` settable options | 184 | 184 |
| Bytes / CRLF endings | 45 533 / 1 020 | 45 533 / 1 020 |
| `diff` against the fixture | — | **one hunk, one line** (the seeded one) |

Of the 189 four-space assignment lines five are nested-table openers, which is why the settable-option list a profile is validated against returns 184, and both counts are stable across the merge; a profile naming a vanilla nested option or a table opener is rejected rather than silently doing nothing [#2812/M/n=1].
A profile's nested `[sandbox.<Prefix>]` table sets a mod's own option, the harness writing it into the server file in the server's nested shape, a prefix at four spaces and its leaves at eight ([sandbox-options.md](sandbox-options.md#server-file)); the mod's two modes were booted that way on a live server, which a top-level key could not express [#2807/M/n=1].

Five sandbox options carry the nutrition work, with the fixture's value and what each does; all five are settable from a profile and only the day length has been exercised by one [#1809/C/C-only].

| Key | Fixture value | Why it matters | Where it is documented |
|---|---|---|---|
| `Nutrition` | `true` | The one sandbox option gating nutrition at all, and it gates only `Nutrition.update()` | [`../facts/eating-pipeline.md`](../facts/eating-pipeline.md) |
| `FoodRotSpeed` | `3` | Enum 1–5 scaling `age += ΔgameHours × FoodRotSpeed / 24` (3 = ×1.0, the default) | [`../facts/food-item-model.md`](../facts/food-item-model.md) |
| `FridgeFactor` | `3` | Enum 1–6 scaling aging inside a *powered* fridge or freezer (3 = ×0.2, the default) | [`../facts/food-item-model.md`](../facts/food-item-model.md) |
| `StatsDecrease` | `3` | Enum 1–5 on hunger and thirst drain (3 = ×1.0, the default) | [`../facts/body-and-weight.md`](../facts/body-and-weight.md) |
| `DayLength` | `4` | How long a game day lasts in real minutes (`1` = 15 min, `4` = 1 h 30 m) — the clock every timed scenario is fitted against | [the cadence ceiling](#cadence) |

<a id="driven-client"></a>
### The driven client

A driven client is a Java process started directly with no launcher executable and therefore no elevation prompt, run with no Steam, its own cachedir, no sound, no voice and a connect argument naming the server's address and port, with the debug flag added only for the admin account [#1710].
The harness mod has to be in the server's mod list, because the client reloads its Lua with the server's list on join; it then reads a join manifest from its own cachedir, presses connect and steps through the spawn, profession and appearance screens, while a restored fixture client skips creation entirely because the character persists server-side [#1715].
A golden client cachedir is about one megabyte and holds the options file with the terms flag, the mods folder with the harness, the enabled list and the reset marker, the saved-server database and the join manifest [#1857].
A loaded client sits on a click-to-start screen until a mouse click arrives, so the orchestrator posts one to the client's own window, matched by process id and without changing focus, until the harness reports the player's position [#1716].
Every in-world figure the join spike reports therefore means world loaded and sitting on that screen, because the loading state polls for mouse or key input before entering the in-game state and nothing in the client console or the harness fires until then — a posted click is delivered like real input, taking a loaded client to a ready player in about two seconds [#1859].
A client's window is owned by the Java process the orchestrator spawns, so matching by process id works, posted clicks need no focus, the harness survives the join-time Lua reset because the last executed sequence is recovered from the acknowledgement file, and the client's chunk cache is keyed by address and port, so booting a fixture on its recorded port keeps it warm [#1863].
Every copied mod adds baselined noise: each one logs a missing-file exception for the optional animation folders it does not ship, and the acceptance runs recorded zero server errors with those lines present [#1827/M/n=1].

The debug flag is session-ending for a driven client: on two independent boots the client reached the in-game state, printed one complete trace and then stopped — console dead at the last trace line, its ready line never printed, the bus never answering a command, and the process still alive [#1712/M/n=2].
The route into the modal break is the debug arm of the Kahlua failure helper, which prints its failure message and calls the interface breakpoint before the throw; the breakpoint returns at once on a server, so no server ever breaks, and otherwise enters the modal synchronisation pump [#1713/C/C-only].
What that costs a driver, and what a release client would do instead, is [`lua-platform.md`](lua-platform.md).

A fixture can carry a second account, and the debug flag is then a per-account record rather than a rule of the admin name: `pzt provision --name two --clients admin,bob` wrote a record with `admin` debug and `bob` not, and gave `bob` a ready time of 35.3 s at the provision, one reading of a client launched without `-debug` reaching a ready world (n=1) [#3302/C/snapshot].
A driver or a verification row names a client's side `client:<user>`: the bare `client` still means `admin`, so every driver and row written before a second client existed reads as it did, and a user the run did not attach is an error that names the attached users [#3303/C/snapshot].
A profile lists the accounts a run attaches in a top-level `clients` key, `["admin"]` by default, each name a client the fixture provisioned, and the run launches them one at a time with each ready before the next is launched [#3304/C/snapshot]; the two-client session attached `admin` and then `bob` that way, each reaching ready, `bob` 40.9 s after its own launch [#3298/M/n=1].
A release client in that session answered the bus, read its debug flags false and its debugger error count 0, and had the mod's tooltip hook installed [#3297/M/n=1], and `event.trigger` addressed to the named client toggled that client's own panel [#3296/M/n=1].
Two clients on one `pzt run` are one session: the profile's `clients` list is the whole set of client processes the run starts, launched one at a time with each ready before the next [#3304/C/snapshot].
A client reads only its own player, so a second client's copy of the other player's character is not reachable from the bus [#3292/C/C-only].

<a id="bus"></a>
### The command bus

The command bus is a pair of files in each side's cachedir: the orchestrator writes a sequence number, a command and its arguments, the harness executes each sequence once and answers with an ok or error prefix plus a string or one line of JSON, and the last executed sequence is recovered from the acknowledgement file after a Lua reset [#1717].
One protocol runs on both sides, carried by the same reader and writer pair, and the dedicated server polls the command file from the tick event and from the once-a-minute one [#1717].
A result is written as one complete JSON object and that completeness is the ready signal, because the file writer's extension allowlist rules out marker files; the orchestrator collects them into the run report and a bus helper blocks on one, a partial write never parsing [#1761].
The command bus answers with no client attached: a server ping answered in 1.51 seconds, the version control read 1, and all ten echo checks passed, over two boots on the server alone [#0933/M/n=2].
The live registration set, counted on 2026-10-06, is 109 distinct names over 125 registration sites, sixteen names being registered twice, once per side; the generated table counts the sites and not the names [#2808/C/snapshot].
That table — one row per name and side, with the arguments, the reply keys and the purpose of each — is [`harness-commands.md`](../reference/harness-commands.md), and it is generated from the registration sites rather than written by hand.

The test layer answers three bus commands: a sorted list of registered names, a run command whose acknowledgement is one of started, unknown, already running with the running name, or a player-resolution error — and only started leads to a result document — and a status reply carrying the running flag, name, clock, due minute, side and sample count [#1722].
The bus answers a translation lookup on both sides because the command is registered once in the harness's shared file, which loads before the client file, and a reply distinguishes a Java null return from a translation miss [#0930].
The harness's only string setter is the chef field on an item, and it is the only route from the bus into the cooking-experience branch of the food update, because an admin-command spawn leaves that field null; an empty value is refused rather than written, since an empty chef reads as no chef [#1723].
`lua.setpath` is the drivers' only setter of a plain Lua field, `globalmoddata.setpath` assigning into a global modData table instead: a server-side, test-only command that assigns a true, false, nil, number or string scalar to a field of a Lua table reached by a dotted path from the globals, and its first use flipped a mod flag live and read it back [#3078/M/n=1]. That it never creates a field on a missing parent and carries no role check, the bus being the harness's own file channel that only the driver writes, is the command's own text, its comment block and body at `repo:testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua:2767`, and not a reading. No chunk runner exists, because `loadstring` is removed on 42.20.x [#1082/C/snapshot].
Its client twin and a two-sided `lua.call` worked on their first live use: a zero-argument call replied a number on both sides, a two-argument call a table's key count, a missing target `failedAt`, and the client setter wrote and read back its value [#3199/M/n=1].
`event.trigger` and `lua.callm` worked on their first live use: a triggered key press ran the mod's own Lua key handler, the reply saying only that the call did not raise [#3265/M/n=1], and a method call reached a panel instance through a numeric path segment and the character-info tab's view through a vanilla global path [#3266/M/n=1].

The harness Lua is eight files split by load order and by which part of the work owns them [#1771].

| File | Where it sorts | What it carries |
|---|---|---|
| `shared/PZTestKit_Core.lua` | first | the global table, the key-value files, the encoder, the bus, results and the witness |
| `shared/PZTestKit_Test.lua` | after the core, by name | the test layer: the game-minute scheduler, the test registry and the test commands |
| `server/PZTestKit_Server.lua` | the server's first | the bus poll and the witness replies on the server |
| `server/PZTestKit_Server_Recipes.lua` | after the server file, because a dot sorts below an underscore | the recipe readers |
| `server/scenarios/PZTestKit_Scenario_Smoke.lua` | under a folder the loader walks recursively | the scheduler's own self-test |
| `server/scenarios/PZTestKit_Scenario_Nutrition.lua` | the same folder | the two three-game-day nutrition scenarios |
| `client/PZTestKit_Client.lua` | the client's first | auto-join, the client commands and the round-trip witness comparison |
| `client/PZTestKit_Client_Body.lua` | beside it, registering into the same table | the client mirror's own commands, kept separate so two lines of work cannot collide |

<a id="reading-a-reply"></a>
### Reading a reply

A subject that does not resolve is a result and not a usage error: both witness commands answer their usual envelope with a false resolved flag and an error, only the first-argument gate answers a bare string, and a third gate inside the table branch answers a table whose error begins with the usage word [#1748].
All three gates are recorded in the artifact, so a driver must check the error before trusting the fields: a type check on the reply is necessary and not sufficient [#1748].
The resolved field names the subject that answered and not the one that was asked for: for an item it is the owner, full type and id; on a client it always names the local player whatever user was sent, because that side has no one else; and the global scope sets it at all, having no subject to resolve [#1749].
A getter has three outcomes and not two — the build does not expose it, it is there and the call raised, or it answered with nothing — three separate lists, because each getter runs under its own protected call so a dispatch to an arity nobody asked for costs that one key rather than the whole reply [#1736].
The middle bucket exists for one overloaded getter, and on this build the no-argument overload is taken and all three lists came back empty on all fifteen probes of one session [#1736].
Three rules follow from how the global walk is written: a hop is taken only when the node is a table, so a non-table node ends the walk and the reply names the segment that could not be entered and the type that stopped it; the key count is gated on the same test because iterating a Java-backed object raises; and presence is a nil test rather than a falsiness test, so a global whose value is false or minus one reads as present [#1759].
A fourth reply shape, on a build with no global table at all, carries no failed segment, so a reader keying on that field must treat its absence as that case [#1759].
The modData witness differs from the global walk here: its dotted walk turns a false leaf into nil, so a nested boolean that is false is listed under `missing`, while the same boolean inside a table read whole comes back false [#2990/M/n=1].
A false resolved flag from the global walk means this path and not this mod: the two are the same claim only when the name is known to exist in one copy of a file and not another, which is why the harness's own version global is sent first as the control that says the walk works, and the control must answer on both sides [#1760].
One side answering a script read is not evidence about the other side, because script data loads per side and is never synced — but both sides run the same implementation and the reply names which side answered [#1724].

The translation read answers in four shapes: a hit, a miss that returns the key itself and is reported as a miss, a Java null return reported as a miss carrying a null flag and no text at all, and a usage string when no key is given [#1718].
What a dedicated server's translation route does and does not answer is [`mod-anatomy.md`](mod-anatomy.md), which owns that reading.
Two non-finite cases still answer null on the bus, because JSON has no literal for either and a bare one would lose the whole acknowledgement rather than one number [#1755/C/inference].

Seven vanilla noise signatures are allowlisted, four of them surfacing only once the big three were filtered, and with all of them in place a clean vanilla boot scores zero — so any nonzero count is a real finding [#1850].
The first over-count in the error classifier is harness echo: no echo pattern is whitelisted, so a bus reply that merely carries exception text is filed as a fault — a session reporting four server errors was four verbatim echoes of the driver's own reading and zero engine faults, and any session whose readings quote an exception string inflates it the same way [#1765/M/n=1].
The second over-count is genuine engine output counted per line: a single Lua error contributes ten entries — four error-message heads, four bare stack-trace lines the pattern also matches, and two exception lines — so a session reporting 892 error lines is about 89 fires and not 892 events [#1766/M/n=1].

Two replies are stale or side-relative by construction rather than by accident.
The nutrition setter's own acknowledgement carries the weight-direction flags one tick stale: the acknowledgement of a calorie write reads the increase flag false beside the new calorie value, because the weight update has not run again yet [#1492/M/n=1].
A container reading is presence and within-side stability only: the leading type token agreed on both sides while the full strings differed exactly where the jar says they must, because the container's string ends in the parent object's per-JVM identity hash — so comparing the strings across sides reads as a desync and is not one [#1507/C/n=1].

<a id="probes"></a>
### Probe design

For anything the server owns the client's reply is a mirror, so a probe's first decision is which side to ask [#1826].
Aging must be read on the server: an age probe on a client measures the client's stale copy, which is the finding rather than the number [#0359/M/n=1].
Every intake probe is server-side because a multiplayer client never calls the drink routine at all: the net timed action skips the Lua completion on a client, so a client-side probe would read the once-a-second mirror rather than the store [#1729].
A server-only script census is the whole answer, because a client census would count the same load-time objects [#0647/C/inference].
Every rate in the body model was fitted server-side, the client mirror being read only at session start, at the idle baseline's boundaries and in the two client-write probes, so nothing there bounds the client mirror between those points [#0573/M/one-side].

Exclude the custom name and the tooltip from any item-modData census, because vanilla writes both into item modData itself and a census that keeps them reports vanilla as a finding [#1043/M/n=1].
The same item's modData differs across sides for a reason that is not mod data at all — the client's copy carries a custom-name key the deserialisation path writes into modData — which is why an item census excludes it [#1753/M/n=1].
Every item-modData reading names the side it was taken on, and a probe that writes one key on the client and transmits rewrites the server's copy of every other key on that character [#1640/M/n=1].
A player census excludes the four vanilla fitness keys and the hotbar instead, and it is taken late in a session, because the server's copy of a player's modData is empty at join and holds four keys only about half a minute in [#1966/M/n=1].
The server-side player modData setter exists because the player census is four keys on the server against five on the client, a strict superset — so without a planted server-only key the difference set that would expose the receiving side's wipe-before-write is empty [#1757].
A pure client-interface mod's persistent state is invisible to a command bus until a human clicks: one mod's configuration key was absent on both sides at every one of six snapshots and its six probed leaves were read once per side, because all seven writers are input handlers and on that session's harness no bus command could synthesise a click or a key press; since Plan 8 the test-only `event.trigger` fires a Lua-side key event, and a physical click or key press is still not synthesised [#1498/M/n=1].

The item census is the game's own loaded-item list bucketed by the raw item-type string, counted raw so a registry rename is visible rather than silently zeroed, and it is the live cross-check for the script-side food scanner [#1726].
A live fluid census must pair the fluid-type string getter with the enum getter to be exhaustive [#0655/M/n=2].
The string getter answers for only 34 of the 61 definitions, coming back empty for every fluid that also has a built-in enum constant, so the command falls back to stringifying the enum and reports which route named the fluid [#1727].
The fluid read lists all sixteen members it asks for — the fourteen property getters plus the display name and the properties-set test — of which ten read the flag false on this build [#1725].

The drink probe picks the fullest container instance, ties broken by the highest id, rather than the first match, because the first-match finder would re-select an already-drained can on a second probe of the same type; the candidate list and the pick travel in the reply and a finder field says which route answered [#1730].
The drink probe is drift-free by construction: both snapshots are taken inside the one Lua call on either side of the single Java line, so they are the same game tick, and the world age before, after and its delta travel in the reply so that is checked rather than asserted — a bracket around the command is the independent outer reading and does carry the passive drain [#1731].
A container's aggregate properties are read before the drink, because an emptied container recalculates to all zeroes [#1732].
The item-use command consumes uses the way a craft input line without an item-count flag does and skips the bookkeeping that follows the reduction — a replace-on-use spawn, the client push when uses remain and the removal when they do not — so a fully consumed item stays in the inventory where the crafting code would have removed it, and the reply says which of the two happened rather than leaving it to be inferred [#1738].
The item-use command refuses an instance already at zero uses and answers with the before snapshot unchanged, because a depleted food has no hunger change and the setter would compute a not-a-number factor and write it into every macro [#1739].

A bare recipe name and its module-qualified spelling both answer, craft and evolved alike, but only for a recipe declared in the base module: a recipe declared in another module answers to neither spelling, because both still land in the base module, and every one of the fifteen probes behind that reading was a base-module recipe [#1734/M/n=1].
The craft-recipe read carries a third lookup route, tried only after both spellings miss: a walk over every loaded craft recipe matching on the last dotted segment of the cached full type and falling back to the plain name, so a bare non-base name answers and the resolution rule stays measured rather than papered over; a caller who wants the rule exercised asks module-qualified [#1735].
The global-walk command walks the Lua global table segment by segment and never calls what it finds: a function reports the string function, because reading its result would mean calling an unknown global at unknown arity — catchable, and still not worth making, since an unguarded one aborts the rest of the handler body and on a debug client parks the process [#1758].

<a id="witness"></a>
### The witness contract

Both reflective witness commands are registered in the shared harness file, so both sides answer them and every reply says which side did — one generic command instead of a getter-specific one per mod, so no new per-mod Lua is written before these two have been tried, and a name reported missing means the build does not expose the member, which a per-mod comparator would have died on [#1741].
Each name a field witness is asked for lands in exactly one of three buckets, and the three-way sort is the point: missing means this build's object does not expose the member at all, nils means it is exposed and the call returned nil, which is a reading rather than an absence, and fields is everything else — so the mod did not set it and this build never had it are different answers [#1743].
The guard indexes before it calls, because a caught nil call names no member [#1743].
Every modData witness reply carries the census — every top-level key as a sorted name-and-type list — so a wildcard or no key at all is a valid call and is how a mod's modData shape is discovered before anyone knows a key to ask for; a dotted path walks nested tables and a path that does not resolve is reported missing exactly as an unset key is, while the read count and the census size stay separate numbers [#1745].
The three scope words are reserved in the modData witness's first argument, the bare words and their trailing-colon forms alike, so a modData key literally named after a scope has to be asked for behind an explicit prefix where it is just a key; the gate is spelled as a lookup table because Lua patterns have no alternation [#1746].
A witness call reads at most 32 names, both replies travelling as one bus acknowledgement line, and the cap is counted before the read — so the count is what was actually read and a truncation marker is the only signal that more were asked for [#1747].
Both witness commands answered on both sides for a player and for an item in one session, with fifteen graded rows over seventeen probes — fourteen as expected, one finding and no misses — and no truncation anywhere, so the cap never bit [#1752/M/n=1].
The command shapes are structural, but every item number and the modData asymmetry of that session are each a single reading, and nothing there supports an always claim without a second run [#1752/M/n=1].
The maximum carry weight read 12 on both sides at all six snapshots of one session and matched the body snapshot's own field on both sides, which is what proves the harness's Java-member call wrapper sound [#1500/M/n=1].
The three weight-direction flags are read-only keys on the nutrition snapshot and appear in every nutrition and stats reply on both sides, so a build without them omits the keys rather than raising; they are not in the player-stats packet, which makes the pair of readings the only way to see whether a client recomputes them from its mirrored macros [#1756].
Every sample is stamped with the game minute, the world age and the wall clock, and the world-age-and-wall pair is what the Python side fits rates against — which makes the harness's own cadence measurable without a second bus round trip; the world-age read goes through the guarded call, so on a build that does not expose it the key is simply absent from the sample instead of the scheduler dying [#1778].
The older round-trip witness is a different instrument and still exists beside these two: its modData command carries a name of its own, while the kind on the wire, the comparison and the result file name are unchanged, and its nutrition and item witnesses are untouched [#1874].

<a id="scenarios"></a>
### Scenarios and the test layer

A scenario is a Lua test that runs on the world's own clock — days of game time in minutes of wall time — and hands its samples to a Python evaluator [#1772].
A registered test carries a backstop in game minutes, a subject username, a needs-player flag and a run function, and clearing the needs-player flag is the only way to register a test that runs without a subject [#1773].
Leave the backstop a clear margin above the finisher: it is armed first, so it holds the lowest sequence number and wins a same-minute tie, and a test that finishes at exactly the backstop minute is timed out instead and reports an anonymous detail [#1774].
The shipped nutrition scenarios finish one minute past their run length and set the backstop 29 game-minutes above that, while the smoke test finishes at twenty with a backstop of thirty [#1774].
The test context offers a schedule-once call, a repeating call re-armed before the callback runs so one raising callback cannot silently stop a multi-day sampler, a predicate poller under its own protected call that ends the test with a labelled timeout when its budget runs out, two assertion helpers, a sample appender and a finisher whose pass flag is combined with whether any failure was recorded [#1777].
That protected call catches ordinary Lua errors and not a call to a Java member the build lacks [#1777].
Every Java member in the test layer goes through the guarded call, because an unguarded nil call aborts the rest of the once-a-minute body it fires in — the handlers behind it still run, and a protected call does catch it, but it names nothing [#1781].
The scenario subject is resolved by username out of the online-player list, because there is no single-player getter on a dedicated server — so the client must be attached even for a server-side test, the fallback order being the run argument, then the test's own player, then the admin account [#1779].

Three scenarios ship, all server-side because the server owns nutrition [#1782].

| Scenario | What it runs | What it asserts |
|---|---|---|
| the scheduler self-test | about twenty game minutes | only that the clock ran, that samples landed and that one predicate poll reached a hit |
| the gain run | three game days at four thousand calories a game day, fed as two doses twelve game-hours apart under the calorie clamp | the weight model, through the Python evaluator, over its own hourly samples |
| the fast run | three game days at no intake | the same evaluator over the same hourly sampling |

Both nutrition runs are sampled hourly with hunger and thirst pinned to zero after every sample [#1782].
The scenario records the server's nutrition object once a game-hour and a Python evaluator integrates the weight model sample-to-sample over each run's own calorie and macro trace, passing when the weight it predicts is within the greater of fifteen per cent of the predicted delta and 0.05 kilograms of the weight the server reported [#0157].
A scenario evaluator is a Python function keyed by scenario name, registered by importing its module, and a name with no evaluator passes on the harness verdict alone; the nutrition evaluator fails the run outright if any sample is dead [#1786].
The scenario runner refuses a name the chosen side does not report and any run acknowledgement other than started, rather than paying the full result timeout for it, and a refused time-speed command ends the run there too with that reason, because the world would still be at real time and a three-game-day test could not finish inside any timeout worth waiting for [#1783].
An interrupt is caught rather than propagated, tearing down as usual and still writing the report and artifact [#1783].

A scenario runs the Python evaluator before it restores the time multiplier, because the evaluator is scenario code that can raise and a raise must not skip the speed restore, which sits in a cleanup block so a world change cannot outlive the run [#1704].

```
boot and attach the subject client
test.list on the chosen side
RCON settimespeed <N>
test.run <name> <user>
wait for the result doc
the Python evaluator for that name
settimespeed 1 + teardown, from the finally
report and artifact written last
```

The artifact then carries the profile and the probe results on every run, null and empty when there was no profile [#1704].

<a id="cadence"></a>
### The cadence ceiling

The scheduler's clock is game minutes and not wall seconds: the game's once-a-minute event advances it and dispatches every callback whose minute has come, sorted by scheduled minute and then by insertion order, the layer carrying its own sequence because the sort is not stable [#1775].
The scheduler hooks that event once, because a reload re-runs the file and a second registration would advance the clock twice a game minute and halve every rate fitted against it [#1974].
The once-a-minute event fired at exactly one tick per game minute on the dedicated server at a time multiplier of thirty, on all three of one set of runs, at the fixture's four-unit day length — which is what makes it eight game-minutes of world clock per wall second, a ratio that is not a property of the speed flag alone [#1776/M/n=3].
Each of those three three-day runs took 73 hourly samples over 72.0 game-hours at a multiplier of thirty with no server error lines, the once-a-minute event ticking 1.000 times per game-minute at 7.99 to 8.00 game-minutes per wall second [#0156/M/one-fixture].
Every run fits the harness clock against the world clock and the wall clock, and a tick rate outside 0.95 to 1.05 per game minute sets a suspect flag and prints a warning: the run still reports, but everything it scheduled in game minutes and every rate it fitted per game-hour was read off a clock that was not keeping time [#1787].
The usual cause is the combination of the fixture's day length and the speed flag, not the speed flag alone [#1787].
A fifteen-minute day at a time multiplier of thirty overruns the game-minute scheduler: the run recorded 0.22 ticks per game minute with the suspect flag set, the once-a-minute event firing twenty times while the world advanced 91.05 game minutes [#1813/M/n=1].
That run's scheduler self-test still passed, because every assertion it makes is counted in ticks, so nothing fitted against the game clock on it may be cited [#1813/M/n=1].
The ceiling holds on the fifteen-minute day as it did on the ninety-minute one: at a multiplier of five on a fifteen-minute day, the same arithmetic value of eight, the run recorded 7.57 world-minutes per wall second and 1.018 ticks per game minute with no suspect flag [#1816/M/n=1].

The other cadence a probe has to respect is the server's own item tick.
The dedicated server's inventory-item tick runs about once every 5 s rather than every frame, because the time-multiplier calculation's server arm is real-time-delta driven and clamped at 6 s, so a bus call cannot be made the cause of a server-side item transition at this time multiplier [#1113/M/n=2].
A bus call therefore cannot win a race against that tick, and a probe must not assume per-frame item updates [#1420/M/n=2].

<a id="time"></a>
### Game time against real time

One game minute is 3.75 real seconds at the fixture's day length of four, which is a 90-minute game day of 5400 seconds over 1440 game minutes [#0893/C/arith.].
The measured body run ran on a fixture whose clock was 16.027 game-seconds per real second — that same ninety-minute day — and every rate was fitted as a least-squares slope against the world age read from the same snapshot, so the speed setting cancels and the accelerated windows are directly comparable with the baseline [#0452/M/one-fixture].
Wall-clock boot cost is not constant within a session: the first boot of a session cost 36.6 seconds against 13.7 and 14.0 on the same session, and the gap is measured while its cause is not — the first boot of the session is the suspected reason and no spike measured it [#1846/M/n=1].

<a id="artifacts-discipline"></a>
### Artifact discipline

Every invocation writes its own run directory holding the server log, the server and per-client cachedirs and a report of timeline and events, where a timeline mark is a seconds-since-start stamp plus a phase, and a step that measured its own cost adds a separate duration field [#1706].
Every result document in the harness carries the same envelope beside its own keys: the document's own name, the side, a wall-clock timestamp at write and a completion flag; the timestamp is load-bearing rather than decorative, because with the start stamp it is the pair the cadence fit uses, so a side with no millisecond clock produces no cadence block at all [#1780].

Two shapes in the committed reports are traps if a file is read at face value.
The truncated timeline mark is the first: a mark's observed value is truncated at 100 characters, which on the acceptance run stops immediately before the value every took-effect claim rests on — quote the parsed verification block, never the mark [#1794/M/n=1].
The elapsed field on the server-started and client-ready marks is the second: it is that step's own duration and not elapsed time in every artifact committed before the harness passed the duration separately, because those two sites passed the duration in the elapsed slot — so a client ready at 37.3 seconds is a 37.3-second client boot on a run that reached in-world at about 74 [#1795/M/n=1].

The bus number format is a rendering property of the artifact and not a measurement one: integers still take the integral branch with its own cut-off, no key changes name or type, and the current path round-trips a non-integral double exactly where the older one quantised every float to six decimals and made cross-side comparison at the last bit impossible [#1754].
No bit-level claim may rest on an artifact written before the harness commit `291f977`: the encoder rendered every non-integral number at six decimals, so a cross-side comparison from such a run is equal at the bus's resolution and never bit-equal, and the one-in-a-million tolerance the graded rows used is exactly the encoder's own resolution [#1965].
Give a run id a prefix with no hyphen: the run-id form the checker reads is a lower-case alphanumeric prefix, a hyphen, eight digits, a hyphen and six digits, so a hyphenated prefix is refused; this form is stated in `tools/claimslib.py` and in no register row.
Two teardown sessions were measured under that limit, so every float on their bus arrived rounded and no row from either artifact supports a bit-level claim; those two artifacts stay exactly as recorded, and every desync graded on them is whole-value, far above the comparison tolerance [#1435/M/n=1].
The three scenario artifacts, as the tree stood on 2026-09-10, predate the thirst sample column and the evaluator's dead-subject verdict, neither of which has been exercised live, while the scenario's own die-early abort was in place for the second and third runs and never fired [#0171/C/snapshot].
The measured lifecycle run's artifact carries no fixture or build key of its own, which is known only from the fixture file [#0385/M/one-fixture].

A driver is frozen once its run is committed, so a do-not-cite key is a permanent property of the artifact rather than something to be fixed.
The drink probe's overall match flag is not evidence about the fluid arithmetic: all 54 fields of the primary drift-free reading matched and the three flagged rows are the outer corroboration bracket's calorie row on each drink, short of its band by 0.002 to 0.008 kcal because the band assumes an exactly proportional idle burn — cite the `atomic` and `container` blocks instead of the overall flag or the mismatched-field count [#0661/M/n=3].
The craft comparison's overall match flag is not evidence about the scanner: both run-time misses are the same field on two recipes, at 10 against 9 and at 3 against 2, and neither side lost an input [#0761/M/n=10].
The salad observation flags are not evidence that the expansion is wrong: the expected number they were written against is the wrong number, and an expansion that reproduces the game must include the two drainables [#0765/M/n=2].

<a id="driver-rules"></a>
### Driver discipline

A driver's own timeline is a reading about the driver and not about the engine, and it is graded that way.
A tag name in a driver's timeline is nominal, not a clock reading: the snapshot named three seconds after a transmit opened 7.58 s after it because the previous snapshot took 7.58 s to walk both sides, and the 1.78 s cross-side read skew at that tag is pure latency because nothing in a modData census decays [#1341/M/n=1].
A snapshot taken inside a write's push window is an arrival-latency reading by rule and is reported ungraded, and the two tags nominally three seconds after a write actually sat at 7.35 and 7.85 seconds because the poll and the snapshot already exceed the settle sleep, so the grading uses each snapshot's own time since the last write [#1488/M/n=1].

Put every negative a run establishes into the artifact's own output: one driver held the not-found mod lists on its server and client objects and never wrote them to the file, so that artifact cannot say no mod failed to load [#1707].
Keep a dormant fallback's routing table as wide as the commands that can reach it: one driver's probe fallback mapped only the two witness commands onto a result-document name although the probe also carried three more, so a fire on one of those would block on the wrong document [#1709].
A probe that deliberately raises always makes a run report failure, because the exit code needs zero non-baseline server errors — that is the harness working and not the probe failing, so the run is kept and the grading comes off the artifact [#1767/M/n=1].
An admin-command spawn can return an empty reply for an item that did in fact spawn — once in the census run and twice in the drink probe — so both of that pass's drivers key spawn success on a server-side read-back rather than on the echo [#0675/M/n=3].
Every store the drink probe read was taken through the server bus, with the client attached only so that the player exists, which leaves the client side of the drink path unmeasured [#0650/M/one-side].

<a id="experiment-contract"></a>
### The standing contract for a named experiment

A named experiment inherits the same contract whatever it measures: an existing profile or a new one in the acceptance profile's shape, a driver in the house shape with its provenance keys and its client-first paired reads, verification rows that are certain to pass if the mod loaded at all and never the reading that is the point of the session, and a gate placed on the side whose loading is not itself the question [#2050].
The specs themselves — one row per experiment, with the profile, the driver, the reading and the cost — are [`experiments.md`](../reference/experiments.md).

The remaining experiment programme is a ceiling and not a commitment: about 42 hours is what the named experiments would cost if every one of them were run, and every corpus count inside it is a dated snapshot [#1973].

This library's eight experiment mods declare nine ids between them, all live under the repository's experiments tree, all pin a minimum build of `42.0.0`, and all are installed only through a test profile and never into the fixture [#0868].

| Mod | Id(s) | Profile | What it measured |
|---|---|---|---|
| A | `TKX_ItemOverride` | `x12-overrides`, `x12-order`, `x12-order2` | script override shapes, three translation states, the Watermelon collision |
| B | `TKX_Nutrient` | `x12-overrides` | modData routes, and incidentally the `server/`-file finding |
| C | `TKX_EatHook` | `x12-overrides`, `x12-order`, `x12-order2` | `OnEat` on both sides, the `ISEatFoodAction.complete()` wrapper, the second Watermelon body |
| D | `TKX_LoaderVersion` (`42.20/`) and `TKX_LoaderCommon` (`common/`) | `x12-loader` | the merge direction, the `overrides` tails, the folder drift, the requested-id discriminator |
| E | `TKX_CommonOnly` | `x12-loader` | a version dir holding only a `mod.info` |
| F | `TKX_ZWatermelon` | `x12-order`, `x12-order2` | a Watermelon body whose id sorts last; gated at tier (c) |
| G | `TKX_PcallProbe` | `x12-pcall` | whether `pcall` catches a Kahlua nil call, and whether the handler body and the handler registered behind it survive one |
| H | `TKX_RaiseProbe` | `x12-raise` | whether an **unguarded** nil call aborts the rest of its own handler's body, whether the handlers registered behind it still run, and whether the nested `pcall(function() … end)` shape catches |

## Walls and bounds
<a id="walls"></a>

Every reading in this library was taken on one fixture with one admin character at a day-length setting of four, under a bus cadence ceiling of about 8 readings per game minute, and most measured rows are one session [#1253/C/one-fixture].
A `-debug` client is stopped dead by the first mod Lua error reaching `KahluaUtil.fail` and parks in `UIManager.debugBreakpoint`'s modal pump, so a raising mod cannot be driven on it; a release client launched once on the two-client fixture answered the bus with its debug calls false and its debugger error count 0 [#3297/M/n=1], but no run has raised on one, so what a release client does with a raise stays open [#0958/C/C-only/open], which is why every raising probe is gated on the server and the client timeout set low [#1246/M/n=2].
Every client-side reading of the unguarded-raise session is unusable: the debug client parked in the Lua debugger and its bus never answered, so that session is a server-VM reading only and its client readings are not citable [#0869/M/n=2].
The server error count is a classifier's output and not a fault count, and a run reporting failure on a raising probe is the profile working as designed: no count of trace blocks is evidence of a fault [#1247].
Nothing on the bus executes a craft: the recipe command is a reader and nothing on the bus reaches a right-click, so a recipe's create and test hooks and the create event itself stay read from code, the create event never having fired in this library [#1248/C/C-only].
The dispatch case of a protected call and an unguarded raise was measured only inside once-a-minute handlers on the server VM, when the bus had no trigger-event command; the test-only `event.trigger` since fires a Lua-side event from the bus and ran a key handler on each of two triggers without a raise inside it, so what a protected call and an unguarded raise do inside any other dispatch, and whether another mod's protected-call fork around one changes it, is still unmeasured [#1249/M/n=1] [#3265/M/n=1].
The translation session carried no in-run positive control: every reply missed, so the item-name routing claim leans on an earlier session's client-side interface-key hit, taken on a different harness shape, and every later session that calls the translation command must ship a control that hits [#1250/M/one-side].
The translation command's null guard has never fired in a committed run, zero replies carrying the null flag across both sessions that could have triggered it, so the branch has not executed and nothing confirms its behaviour [#1721/M/n=2].
That the guard holds is therefore an assumption about the harness rather than a measurement of it, which is why every translation reading of the overrides session is on that run's do-not-cite list [#1251].
No bus command cancels a timed action that has started: the client's stop clears the queue through vanilla `clearQueue`, which force-cancels only actions not yet started, so an eat stopped about 2 s after it was queued ran to completion on the server in the boot whose wrappers did not cycle; the vanilla call that stops a started action, `IsoGameCharacter.StopAllActionQueue`, is on no command [#2834/M/n=2].
The asleep hold re-asserts a connected player's server-side asleep flag once per tick: the flag read set at every in-hold sample (12 of 14 reads; the last two fell after the hold), but about 15 % of stat updates still run awake because the client's reset lands between the re-assert and the update (x132r), and the client's own copy reads awake; the run command still only walks: it sets the running and path-find running flags and the server read running false at every read of a 30 s run window [#2840/M/n=2].
The field witness reads zero-argument getters only and caps at 32 fields, so the nutrition macros are read through the nutrition command rather than through the witness [#1252].
The harness cannot read another player's character from a client: its client-side subject is always the local player, so what a second client's copy of a player holds after a push stays unmeasured [#3292/C/C-only].
Neither script-side command can return a per-item macro and no third one could: the food script object exposes no macro getter to Kahlua, so the live macro read-back has to go through a spawned instance instead; fluid containers have no live route at all, the script item exposing no component accessor, so only fluid definitions can be read back from the bus [#1728].
A global-scope modData census proves less than it looks: the read goes through a get-or-create static that creates the table when it is absent, so it can never report no such table — an empty census says only that nothing stores anything under that name, and the probe has just made it [#1750].
The client side of the scenario runner is wired end to end and has nothing to run: the test layer is shared and both bus commands answer on the client, but every registered scenario lives under the server folder because the server owns nutrition [#1784].
Artifacts older than commit `291f977` render every non-integral number at six decimal places, so no bit-level claim may rest on them [#1254/C/snapshot].
An option the world generator consumed once is not retroactive: the distributed zombie population, the spawn regions and the start date belong to the world and not to the boot that loads it, so a world-generation option has to be changed by re-provisioning a fresh fixture — only the day length has been measured on a restored world, so the other four are unproven rather than shown non-retroactive [#1811/C/inference].
A vanilla nested option of the server's file stays out of scope and a profile naming one fails validation [#2811]; a mod's own nested options are the `[sandbox.<Prefix>]` table above [#2807/M/n=1].
The one measurement of the once-a-minute event's own ceiling is 10.08 ticks per wall second, on the run that overran, and where the true ceiling sits between eight and 10.08 is unmeasured [#1815/M/n=1/open].
A case-only folder subject can never answer the rename question: the filesystem is case-preserving so the listing shows which spelling was written, but path lookup is case-insensitive, so such a mod loads whichever name is used — the regression subject has to differ from its id by more than case [#1834].
The counterfactual is out of reach from a profile rather than merely un-run: both profile branches return a non-empty source, so producing a mod left under its folder name in the run's mods directory would need it in the golden fixture's own mod list — a fixture re-provision and shared state [#1835].
Two legs of the experiment map are stated but not yet measured, the Lua drink-driver path and a deliberate client/server script mismatch, while modData persistence across a save and reload is measured by run x131p-20261004-192310 [#1255/C/C-only].

The design's own risk register names seven risks and what is done about each [#1844].

| Risk | Mitigation |
|---|---|
| Client windows on a desktop (no true headless) | `-nosound -novoip`, small window (normal rendering — `-safemode` is ~7× slower to load); Windows session must stay unlocked; CI runs L0–L2 only |
| First-join UI screens (account, character) | Golden fixture with pre-created accounts/characters — screens never render; lua fallback for the rare reset |
| Timing/races (spawn not ready, chunk not loaded) | Every step is `eventually(pred, budget)`; no sleeps; world-ready barrier = harness handshake, not a timer |
| Game/mod updates changing behavior | Run pins game build; harness self-reports versions; a `smoke` suite runs after every Steam update |
| Port/cachedir collisions between runs | Unique run-id per run; distinct ports; teardown verifies process exit |
| `-nosteam` ignores the workshop folder | The **profile builder** copies every mod a `testing/profiles/<name>.toml` names into the run cache's `mods/`, on both sides, from one source map. There is no alternative: both workshop roots are gated on Steam mode, there is **no** server `-modfolders`, and `WorkshopItems=` needs Steam and is written empty |
| Time acceleration side effects in MP | Only in L2/L3 with explicit multiplier; nutrition tests assert against game-seconds, not wall-clock |

Not covered: what a release client does with a raise, a Linux dedicated-server image or any continuous-integration host, a second client's copy of another player, a client-side scenario, a save-and-reload cycle beyond the persistence readings of [server-lifecycle.md](server-lifecycle.md#global-moddata), and any reading of the game through a channel other than this harness — every number on this page was taken on one Windows machine driving one dedicated server and at most one debug client, with one release client beside it in the two-client session.

## Open
<a id="open"></a>

- Which `mod.info` copy this build reads first when the harness mod ships two identical files, one at the mod root and one in the version folder, is open — settled by a boot that names each copy's own id in turn against a purpose-built folder [#1770/C/C-only/open].
- Which sandbox options survive a restore is open: only the day length has been set by a profile on a restored world and measured to apply, and the other four keys the mod work cares about are unexercised — settled by a profiled run that sets each of them on a restored world and reads it back [#1830/C/C-only/open].
- That a fresh server started in 13.9 seconds from a partial sandbox options file holding two keys, the server filling the rest with defaults so overrides need no template, is unverified: its only evidence is a provision whose artifact folder was never committed; re-measure by seeding a two-key options file on a fresh provision and reading the rewritten file back [#1860/M/uncommitted/unverified].
- That safe mode was the root cause of the eighty-second join stall — animal definition loading stalling on the five body-model loads it makes per animal type, the phase dropping from 81 seconds to under a second once the flag was removed and the whole launch-to-world time from about 148 seconds to 32 — is unverified: its only evidence is a spike whose artifact folder was never committed; re-measure by booting the same fixture client with and without the flag and timing the load phase from the client's own log [#1858/M/uncommitted/unverified].
- That a bus reply carrying the null flag is inconclusive rather than a miss — it says the lookup route answered nothing at all, where a miss returns the key itself — is unverified: the guard has never fired across the two sessions that could have triggered it, so it is untriggered rather than confirmed; re-measure by a session that ships a key known to return a Java null [#0931/M/n=2/unverified].
- That the round-trip witness takes about a second, the client sending to the server, the server's client-command handler answering with its own view and the client comparing and writing a result file, is unverified: its only evidence is a spike whose artifact folder was never committed; re-measure by a committed session that brackets one round trip on both sides [#1873/M/uncommitted/unverified].
- The first-ever cold server start figures — the server-started banner reached in 57.2 seconds over 1 856 log lines including first-run world and database creation, a remote console honoured from a pre-seeded configuration file and surviving the server's rewrite, a graceful shutdown on standard input with exit code 0 in eight seconds, 57 error-shaped lines in three signatures on a clean vanilla boot and a whole cache footprint of fifteen megabytes — are unverified: their only evidence is a spike whose artifact folder was never committed; re-measure by a committed provision on a fresh cachedir [#1847/M/uncommitted/unverified].
- That a hardened repeat on a fresh cachedir starts in 13.6 seconds, the twelve-second difference being a router-detection wait removed by turning plug-and-play off and the rest cache warmth, so the realistic per-run boot cost is about fifteen seconds and not a minute, is unverified for the same reason; re-measure by a committed boot with plug-and-play off [#1849/M/uncommitted/unverified].
- That a warm start from a restored fixture world takes 13.4 seconds, no slower than a fresh world, and that loading its map metadata echoes the vanilla duplicate-room defect as four invalid-room lines that are baselined, is unverified for the same reason; re-measure by a committed restore boot [#1851/M/uncommitted/unverified].
- The restored-fixture phase breakdown — a ready player at 34.3 seconds and a total of 68.6 including a ten-second hold, with the server started at 13.4, the harness loaded 8.6 seconds after client launch, the Lua reload at 15.2, the world loaded at 32.3 and a bus round trip of 0.3 seconds — is unverified for the same reason; re-measure by a committed run with a hold on the same fixture [#1862/M/uncommitted/unverified].
- That the time-multiplier getter is scaled rather than the argument that was passed, so the two sides' raw getter values are never comparable and only ratios are — the server's ratio reading 29.9 against the client's 143.8 — is unverified: its only evidence is two spike runs whose artifact folder was never committed; re-measure by reading the getter on both sides either side of one multiplier change in a committed session [#1869/M/uncommitted/unverified].
- That speed must always be changed through the broadcast admin command, restoring with a server-only call having left the client accelerated while the two clocks drifted 3.4 game-hours apart within a minute with no correction, is unverified for the same reason; re-measure by a committed session that restores the multiplier both ways [#1870/M/uncommitted/unverified].
- That a multiplier change re-syncs the client clock while steady state does not — after a restore the client's clock running backwards for the next window at minus 5.6 game-minutes per wall second, snapping back onto the server's clock it had overtaken, and ending 0.13 game-hours apart — is unverified for the same reason; re-measure in the same committed session [#1871/M/uncommitted/unverified].
- That the two sides' 0.2-calorie disagreement in the witness spike is the sampling skew of a once-a-second mirror against a drain of about a quarter of a calorie a second is unverified: its only evidence is two spike runs whose artifact folder was never committed, and the drain rate it is read against comes from a later measurement; re-measure by a committed paired read at a known drain [#1875/M/uncommitted/unverified].
- Decision: whether the mod's own timed tests run on the fixture's day length or on a shorter one — the cadence ceiling binds the day length and the speed multiplier together, so the two cannot be chosen independently, and the ceiling's own upper bound is open (see Walls and bounds).
- Decision: whether the mod's own load-time checks are written as verification probes or as scenarios — a verification expectation is a substring of the dumped acknowledgement and cannot express absence or a numeric comparison, while a scenario carries a Python evaluator (see the profile section).
- Decision: which side every test the mod ships reads its state from — the server's reading is the measurement for everything the server owns and the client's is a mirror, so a test that reads the client is testing the mirror (see probe design).

## Worked examples

| shape | file:lines | what it shows |
|---|---|---|
| the house driver's provenance block | `testing/experiments/_template.py:204-224` | the keys every artifact carries — the repository commit, the harness Lua commit and its dirty flag, the doctor verdict and the acceptance run — written before any process starts |
| the shape's origin: exclusion sets, wait sizing and declared field counts | `testing/experiments/x121_overrides.py:206-256` | the per-scope modData exclusion sets, the game-minute constant every wait is sized in, and the field counts a read is asserted against |
| the sibling driver's probe wrapper | `testing/experiments/td3_autocook.py:226-252` | one read with its own wall bracket, the dormant fallback branch, and the re-ask-once guard that keeps both readings |
| a profile | `testing/profiles/mod-under-test.toml:1-19` | the schema in use: the fixture, the hold, two inline verification rows, two mod entries and one sandbox override |
| the index-first guard | `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua:140-146` | the guard every Java member call goes through — index, then call — so an absent member answers false instead of raising |
| the command registry | `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua:513` | one table keyed by name, which is why the same command can be registered from the shared file and answer on both sides |
| a scenario registration | `testing/PZTestKit/PZTestKit/42/media/lua/server/scenarios/PZTestKit_Scenario_Nutrition.lua:162-175` | the backstop set a clear margin above the finisher, the subject's nutrition object read through the guarded call, and the hourly sampler |

## Procedure
<a id="procedure"></a>

The doctor command is the cold-start gate before any boot: it reports a stray game Java process and never kills it, checks three ports are free, checks the fixture is present and build-matched, checks the workshop index is reachable and that the test runner is available, and exits 1 on a failure [#1703].
The port check counts only listening and established local sockets, so a lingering closed connection does not false-fail it [#1703].
`pzt run` and `pzt provision` lint every `path=` mod folder with the layout lint before they seed a fixture and stop on an ERROR, so a malformed mod folder never reaches a boot [#3311/C/inference].
A staged release build boots the same way, its profile naming the staged folder by `path=`: the `x20-release` session attached `admin` and then the release client `bob` to it, and all three sides read the mod's version `1.0.0` and build `42.20.4` [#3316/M/n=1].

What a reading costs depends on which of five layers it needs, and every layer's failure is a hard fail of the run; the layer names and what each is are the design's own, while the last column reads back the cost and host it annotates each layer with [#1842].

| Layer | What it is | Cost and host |
|---|---|---|
| L0 static | lint and parse checks: `luacheck`/LuaLS stubs, the script-DSL parse, the `mod.info` and layout lint | seconds, CI |
| L1 boot | the dedicated server boots with the mod to a clean console — no lua errors, no checksum or definition mismatch — and shuts down cleanly | ~1 min, CI |
| L2 server sim | harness-server lua scenarios: spawn and mutate world and items, run accelerated time, assert via a JSON spool | minutes, CI |
| L3 e2e | one or two real clients auto-join; the harness client executes scripted player actions; the server asserts authoritative state | minutes, local |
| L4 sync | the sync witness: a client reports its view of an object and the server diffs against authority (fields, modData) | rides on L3 |

1. **Profile.** Write `testing/profiles/<name>.toml`: the fixture, the hold, the mods in load order with the harness first, the sandbox overrides, and verification rows that are certain to pass if the mod loaded at all. Every key is resolved and validated before a process starts.
2. **Harness, if the reading needs a command that does not exist.** Land the Lua change in its own commit before the session, with the balance check run over the changed files and the generated command table regenerated; the next acceptance run is its smoke test.
3. **Scenario, if the reading is a rate.** Register the test under `server/scenarios/`, give it a backstop a clear margin above its finisher, sample on the game-minute scheduler, and write a Python evaluator keyed by the scenario's name. Check `24 × speed / day_minutes` against the ceiling before choosing the speed.
4. **Driver, if the reading is a sequence of probes.** Copy `testing/experiments/_template.py`, keep the provenance block, take paired reads client-first at every tag, bracket every read with its own measured wall offsets, assert a declared field count per read, and write predictions, observations and verdicts with the four-word vocabulary.
5. **Run.** `python testing/pzt doctor`, then `python testing/pzt run --profile <name>` or `python testing/pzt scenario <test> --profile <name>`. A failed verification probe means the session was not the session that was asked for. A profile with two clients runs under the same command and is the same one session, each client's reads named by its side.
6. **Evidence.** Copy the artifact into `testing/artifacts/<run-id>/` byte-identical, add its row and its do-not-cite table, and never edit the driver afterwards. Grade every reading off the artifact, and write a trivial, unmeasured or falsified reading as such.

## See also

- [`harness-commands.md`](../reference/harness-commands.md) — the generated command inventory: one row per name and side, with arguments, reply keys and purpose.
- [`experiments.md`](../reference/experiments.md) — the named experiment specs, their owners and the cost roll-up.
- [`lua-platform.md`](lua-platform.md) — the Kahlua dialect, what a protected call catches, what an unguarded raise aborts, and the debug client's modal break.
- [`mp-model.md`](mp-model.md) — which side owns each quantity, and the routes a mod's own state can travel.
- [`mod-anatomy.md`](mod-anatomy.md) — the mod folder, the declared id and the loader chain a profile's mod entry resolves against.
- [`jar-research.md`](jar-research.md) — the other instrument: how a claim is read from the decompiled jar.
- [`nutrition-core.md`](../facts/nutrition-core.md) — what the two three-day scenarios measured.
- [`testing-your-mod.md`](../areas/testing-your-mod.md) — how a mod under development is put under this harness.
- [`lessons.md`](lessons.md#testing-discipline) — the observation rules a driver works under, among them that a grep limit is a break and not a window.
- [`wall-map.md`](../reference/wall-map.md) — the capability map whose evidence limits this page's walls carry.
