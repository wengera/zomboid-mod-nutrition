# Process lessons
Verified against 42.21.0 (4a0e9546ec) · 2026-10-23 · scope: the process pitfalls behind CLAUDE.md's rules, each with the incident that made it a rule and where that incident is recorded.

This page is untagged. [CLAUDE.md](../../CLAUDE.md) states each rule in one line; this page says why, so read it before you do a thing for the first time.
Each entry gives the rule in bold, the incident in a line or two, and its source.
Engine and modding rules are on [platform/lessons](../platform/lessons.md), not here.

How to read a source:
- A plan, spec or research path is read at the tag `program-record-v19` (`git show program-record-v19:<path>`). [`docs/superpowers/HISTORY.md`](../superpowers/HISTORY.md) indexes the plans.
- A ruling id (`B3-2`, `P12-15`) is in that plan's ledger, `.superpowers/sdd/<plan>/progress.md`. The ledgers are local and gitignored, and `L` numbers are lines in them.
- A run id (`x391g`) names a folder under `testing/artifacts/`, whose `GUIDE.md` is its reading guide.
- `#NNNN` names a row of the claims register or its archive, and a short sha names a commit.

<a id="live-runs"></a>
## Live runs

- **Boot only with at least 12 GB free, read and ledgered; a two-client session closes the host's other memory users first.** x411 booted at 13.84 GB free and fell to 0.3 GB at ready (#3818).
- **Split a driver longer than about 15 minutes of wall time into separate sessions, each with its own driver.** Claude Code's background-shell reaper killed x242 mid-run for memory, and the 60-ghost sessions took free memory down to 0.55 GB. Source: Plan 10c ruling H2-1.
- **If live sessions keep getting reaped, restart Claude Code with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1`.** Source: the Plan 10c ledger L143.
- **Wait on a live driver in a foreground Bash call with a polling loop, never `run_in_background`.** The reaper killed x281's first boot while its client attached; the foreground wait kept every later Plan 11f session alive. Source: ruling T5R-3.
- **Launch a session longer than the Bash tool's 10-minute cap once, detached, and poll it across foreground calls; the controller makes that launch itself, after Angus approves it.** x391g ran 3053 s (Plan 11b ruling 11b-4). The auto-mode classifier refused a subagent's detached launch and its pre-run timing edit, so x435 ran only from the main thread. Source: Plan 13 Task 22b.
- **`pzt run`, `provision` and `scenario` lint every `path=` mod folder and stop on an ERROR before seeding.** Source: Plan 9 Task 3.
- **Boot a release profile from the staged copy, never from `mod/`.** That way the bytes a server would download are the bytes under test. Source: x201.
- **Gate a raising probe on the server side.** A release client raised on once answered through the raise (x202), while the `-debug` client parks on the first unguarded error ([platform/lua-platform#debug-break](../platform/lua-platform.md#debug-break)).
- **A live boot never overlaps an offline edit under `mod/`.** The boot loads the whole tree, and a half-saved file parks the `-debug` client. Source: the Plan 2 ruling.
- **An acceptance profile for the mod sets `Nutrition = false`.** x141b ran without it. Source: ruling T18-1.
- **A sleep reading needs a profile that sets `SleepAllowed` and `SleepNeeded` true.** The fixture's default is false/false. Source: x151s.
- **Set a world-generation value by provisioning a fixture, never through a profile.** Plan 21's `agent-nozombies` profile set `[sandbox]` `Zombies = 6` against a settled row saying `Zombies` is fixed at world generation (#1811); pass 1 (`a_pipe-20261026-101003`) booted fixture `agent` with its zombies intact, the character died at cmdSeq 28 and the boot was spent (#4181). Source: the Plan 21 close review.
- **Never join or relaunch a client under a near-stopped clock.** x402b's rejoin at `time.multiplier 0.001` never reached ready in 180 s (#3788).
- **Write a driver's grades against the harness's real reply shapes, read off the handler's `@reply` line or a recorded artifact.** x401's `spawned` check was inverted because its fake bus answered a bool where `eat.action` answers `"found"` or `"client"`. Source: Plan 11b Task 4.
- **The fake bus answers the empty-collection shapes the handler gives (`players` with nobody online is `{}`).** x492's relog and restart grades were lost to a driver that accepted only a list, and two reviews passed it. Source: Plan 18 Task 1.
- **Give every driver grade an offline case that fails it.** All three Plan 11b Task 4 driver reviews caught grades that passed on zero samples, zero changes or a read taken before the hold was established.
- **Check a falsifier at the live fixture's own values, not only the fake's.** x504's DISH_EAT could not tell a scaled eat from an unscaled one at Cooking 0 (scale 0.8 = 1/1.25, the utensil factor) or at Cooking 3 (scale 1), while the fake sat at Cooking 2. Source: Plan 19 Task 7 fix 2.
- **Run a driver's pre-boot checks offline against the real staged copy and a real run layout.** x391f's deployed-marker check read the file once per marker and aborted its first boot. Source: ruling B3-2.
- **Write a driver's preboot test with its post-run branch from the start** (it skips `no_prior_artifact` and `staged_from_is_mod_head` once the artifact exists). The same post-run fix landed six times: x441 c2da2696, x445b e77539ed, x46 8535cfc5, x48b b373ac3c, x49 0baf815a, x50 ec59729e. Source: the Plan 14 ledger L61 and L77, Plan 16 L67, Plan 17 L104, Plan 18 L23, Plan 19 L132.
- **A driver refuses any argument it does not define, and its refusal is tested statically.** x485_smoke.py ignored `--help` and booted a live server by mistake (killed at LOADING ASSETS, not a run; Plan 17 Task 7b). A Plan 18 reviewer and an implementer each then tested the refusal by invoking a driver with a bad argument.
- **A driver's run prefix and profile constants name its own file and profile.** x243b ran under x243a's prefix and profile, so its artifact folder is `x243a-20261007-162255`. Source: Plan 10c.
- **Start a new driver from `testing/experiments/xlib.py` and the latest driver's lib, and place every set or setpath event at the drain its read brackets.** x33 repeated x31's event-placement defect. Source: Plan 11f F-T8-5 and F-T9-3; `xlib` is Plan 12 Task 4's.
- **Grep a defect found in one driver copy across every unrun copy before the next boot.** `tl.mark("error", phase=...)` collided with `Timeline.mark`'s first parameter in x391a-x391h and x401-x403. Source: the Plan 11b close.
- **Size a driver's budget from a recorded session's call timing, never from the fake bus.** In x494 each seeded arm cost about 25 s of real bus calls beyond the fake world's estimate, the budget stopped the run before its release half, and x495 was a second session. Source: the Plan 18 ledger L52.
- **A pre-run prediction replays the live first sight as the server will see it, a fresh record's seed plate included.** x452b's prerun started at HUNGER 0.2 with no plate, the live fresh record took one, and both cadence grades came back falsified against the prerun though the replay of the run's own inputs reproduced the live exactly. Source: Plan 15 Task 14b.
- **A prerun's stand-in starts from the fixture's own creation body.** x48's prerun gave its stand-in 80 kg where the fresh record carries 65.025 kg. Source: Plan 17 Task 4.
- **Read a prediction about a vanilla value off the jar or the data before the run.** x401's and x403's self-report grades predicted every saved rate non-zero, and vanilla's `HungerIncreaseWhenWellFed` is 0. Source: Plan 11b Task 4.
- **Before testing an XP source, pull the character's XP below the level-10 total.** After `LoseLevel` from 10 the XP stays at 487500, so `AddXP` discards every grant before the event fires (#2109); x422's "no Strength event from push-ups" came from this setup, not from the engine. Source: the Plan 13 ledger L202.
- **Restore a setting from the value read before setting it, never from a reply's echo, and name each clock's unit and source in a check comparing two.** x391e restored `time.multiplier` from `getMultiplier` (about 4.7 times the true value) and ran five times fast; x260b's `keep()` overwrote the server wall with the driver's, so its ms-against-s flush check always passed (#3762). Source: ruling T4-5.
- **Pair each client read with a server read taken in the same wall second.** Under a floor's rise the stat moves about 0.37 a game minute, and x341/x342's per-eat client verdict, comparing reads 0.5-3 s apart, was falsified by the rise, not by the sync. Source: F-T9r-1.
- **A static field's client-arrival pair may span up to 10 s (`PAIR_SLACK_S`) when two equal server reads bracket the client read.** Source: ruling T7-1, x501-x504.
- **A driver's store read precedes its write by at most one slow minute when the legacy mirror is on.** Otherwise the landing measures the mirror's rewrite. Source: x193's D; [areas/testing-your-mod#rules](../areas/testing-your-mod.md#rules).
- **Gate a cadence on writes per game minute, counter deltas, the mean dtM and a ceiling, never on each minute's dtM.** At DayLength 1 a minute's dtM alternates 0.8 and 1.6 at speed 5 and sits at 0.94-1.11 at speed 1. Source: ruling S0-1.
- **A driver whose character carries a filled container logs the engine's auto-drinks off `fluids.autoDrop`.** The server's `setAutoDrink(false)` does not hold (#2941).
- **Check that a container is unsealed in the item scripts before a driver fills it for a drink.** `fluid.fill` into a sealed bottle reads back 0 L and the drink never lands. Source: x445's BeerBottle and BeerImported (Plan 14).
- **Stop a started timed action through a harness command that calls `ISTimedActionQueue.clear`, or wait for the server's own moving or exercise flag to clear.** `player.stop` clears only the client queue, and a queued action's `StartAction` drops it without a stop: x372's squat set ran 44.6 game minutes past its stop, and an audit caught 10 of 19 earlier windows still moving. Source: Plan 11h.
- **A night driver polls `acute.winSleptH`, never `acute.sleptH`.** The mod zeroes the unbroken run on every awake drain and the hold's isAsleep misses about one drain in six (#2840): x447's poll never passed 0.266 h while the mod booked 41.0 h asleep, and its 90 s cap ran 48 game hours. Source: Plan 16 Task 7.
- **A driver's server-log pattern excludes its own probe names.** The harness echoes a client-side probe's name into the server log: x183's arm I was falsified twice by its own grep.
- **A multi-day guide or study replay asserts its character stays alive and hydrated.** Every multi-day replay of Plan 14 Task 4 ran a character the mod had killed by dehydration.
- **A multi-day replay that drinks needs about 4 L a day in eight drinks, and eats whole-vector plate meals.** The guide's first schedule, 600 g four times a day, sat below the mod's resting loss and killed every multi-day replay by dehydration from about day 5; macro-only meals reach cardiac beriberi by day 24. Source: [`docs/mod-guide/source-map.md`](../mod-guide/source-map.md) § 0.
- **Pass `sleep_allowed` explicitly to `replay_live.replay_arm`.** Its default `None` reads an unset option as sleep on, so the guide's first replays (Plan 14 Task 1) built sleep debt on an awake stand-in. Only a comment says it (`tools/replay_live.py`). Source: the source map § 0, "Kernel replay".
- **Log the eat's landing age, or grade to the band its minute spans, when replaying a quantity that decays with time since an eat.** x502's REPLAY_moodLast.u came back falsified on the replay's placement, not the mod (#4142; x502-regrade).
- **Freeze a grade or analysis script once its output is staged, committed or cited, and fix a later defect in a new regrade script.** x34's three grade bugs were fixed in `x34_regrade.py` (ef47385c), as x30's were in `x30_regrade.py`. Source: Plan 11f.
- **Version a gate function per pass (`gate_a1`, `gate_a2`, …) once an artifact carries its output; never edit it.** Plan 21's `gate_a` was edited after pass 1's `a_grade.txt` was committed (`e154171a`, `fb87c875`) and again after pass 2's (`1406d70e`); the harm was nil, since the report re-derives each pass's grade at HEAD and names where it differs, but a re-run no longer reproduces pass 1's committed file. Source: the Plan 21 ledger's gate_a rulings and its close review.
- **Never patch a grade or replay script that a later mod change broke at HEAD: re-run it on a `git archive` of its build.** The x29 and x35 graders call `K.energy.lagged`, which moved in Plan 11g. Source: Plan 11h ruling T3-1.
- **Restore a broken HEAD replay test through a named replay-only overlay, proved exact against the last build that held the rule.** x332's and x263's tests came back at HEAD through `LIQUID_SOLID_KCAL`, proved against bcf99149, and `FAT_CEILING`, proved against 3a93d51c. Source: Plan 16 Task 7.
- **An aborted boot that took no reading is not a run, and its auto-copied artifacts folder is never staged.** x151r2's first attempt was killed by the host for memory, and `x260-20261010-105039` stays untracked. Source: ruling B3-1.
- **A driver that crashes before any reading takes one named fix before the real run.** x171p's first attempt died on a TypeError at its first phase. Source: ruling B3-2.
- **A live implementer stopped after its sessions ended is not a re-run.** x471 and x472 were checked byte-identical against `testing/runs/` and written up offline by a fresh agent. Source: Plan 16 Task 12.
- **Commit the server log when it is a run's only evidence of an event.** x273's death is cited by line in its `server-stdout.log`. Source: ruling T5-1.
- **Tick each session off the run sheet's session table before dispatching the write-up.** x403 was skipped in order and caught only at the write-up brief. Source: Plan 11b Task 4.
- **A two-client run is one session, its clients attached one at a time.** Source: Plan 8 Task 1.
- **Never use `%g` or `%G` on a value that can be tiny in Kahlua; use `tostring`.** Kahlua's `%g` never returns below about 1e-292, and it froze x391g's server for 2787 s (#3763, #3764). `kahlua_lint`'s `format-g` rule catches it.
- **`lua.setpath`, `record.set` and `lua.call` are the drivers' only setters and caller.** No chunk runner exists, because `loadstring` is removed on 42.20.x. `lua.setpath` has been two-sided since Plan 7; `record.set` is Plan 11b ruling 11b-3's.
- **A test client opens no helper dialog.** Source: Angus, 2026-10-13.
- **Before a boot, check a completion gate whose items come from the world against the fixture's stock.** Plan 21b's Stage B gate asked each of five repetitions to loot food and water. On fixture `agent0` no container held both, so pass 1 (`b_actions-20261026-183143`) could complete none whatever its pick. Pass 2 (`b_actions_2-20261026-194009`) picked each water square once, and the 3 water squares in reach capped it below the gate of 4. Both caps were read off the scans only after the boots. Source: the Plan 21b ledger's Stage B rulings and pass 2's guide § 7.
- **A rule that a driver and the mod it drives each copy is fixed in both, or kept in one place.** In Stage B pass 1, the driver's `beside` and the link's `adjacentTo` both kept any neighbour that is not `isSolid`. A stove square stopped the driver's goto, and by the same rule the Lua's loots. Stage C's first run used only the Lua's copy and failed three loots the same way. The fix took two commits, `e1d298d3` (the Lua) and `e1af7ba6` (the driver). Source: `b_actions-20261026-183143/GUIDE.md` "Cause 2" and the Plan 21b ledger.

<a id="register-and-deltas"></a>
## Register and deltas

- **An artifact may land in its own controller commit; its register rows follow at the task's mint in the same plan, and a row is never minted before its owner sentence.** Source: rulings M-1 and D-1.
- **A commit that adds an artifacts-register row re-anchors every `repo:docs/reference/artifacts.md:` pointer the row shifts, in the same commit.** Five Plan 10 artifact commits left the checker red until a follow-up. An implementer who may not edit the register hands the commit to the controller, as 061630a needed 5e0b230 in Plan 10b.
- **A superseded row's evidence must still resolve while the row is live.** 8a5ec795 fixed 61 stale pointers in 29 rows (Plan 12 ruling P12-15). Plan 20 Task 2 moved the 297 superseded rows to `claims-archive.tsv`, where a superseded row keeps its evidence as written.
- **A retired row's `repo:` pointers are pinned, and `reference_gen cited-by --write` runs after any retire.** The archive is resolved only in pinned form (ruling P20-T1-3), and the artifacts register's `Cited by` column counts both files. Source: Plan 20 Task 1 and its review.
- **Check a wildcard `do-not-cite` key and a parent of a restricted key by hand at review.** The checker matches neither: the five Plan 4 live reviews each returned five to nine wildcard defects, and every Plan 8 live review caught such parents on the first pass.
- **A run's wildcard sentence keeps the word `wildcard` on the pattern's line.** `reference_gen` reads the patterns line by line, so the Plan 20 move of the guides into `GUIDE.md` kept each pattern beside its word. Source: the Plan 20 Task 1 review.
- **A live row that names a study says in its bound that the match is by construction wherever a constant was fitted to that study.** Source: ruling 8-R, Plan 11f. Wall-clock epoch-ms leaves are restricted by one wildcard sentence in the guide, never enumerated (ruling T5-2).
- **Run the controller's provisional-tag regex over the touched pages only, matching `T<n>.<m>` before a `/` anywhere.** A plan record carries its own T-numbering (Plan 7 Task 4); the `[##` cleanup hit a heading link once; a provisional ref also sits inside a combined bracket such as `[#3315/M/n=1, T7.1/C/inference]` (Plan 9 Task 7).
- **A correction pass runs `claims_delta.py apply` and the controller's fill step, and the fill step copies only non-empty cells.** In the Plan 5 gate-1 lesson every Plan 4 correction pass had landed status and bound only, and the claim and pointer cells were replayed at a8fc4b2; the Plan 17 Task 6 apply then blanked two status rows' claims before the commit caught it.
- **Copy a `status` row's bound prefix from `claims.tsv` as UTF-8 and diff it before the apply.** The dry run does not catch a mojibake bound. Source: Plan 10c, #3419.
- **An added `rule` row rests on register rows.** Source: ruling T15-1.
- **A `C/inference` row whose evidence is the mod's own line may own an area-page sentence about what a mod can do.** Source: ruling T12-1, Plan 7.
- **Run the full pytest before committing an apply that supersedes a row the guide cites, and re-point the guide in that commit.** a7cbf636 and 70398a86 each left the guide citing a superseded id and HEAD red. Source: Plan 17.
- **Commit the plan file before Task 1's first dispatch.** The Plan 12 plan stayed untracked while #3818-#3829 cited it in their source cells.
- **Pin removed code to the last commit holding it, never a later one.** The first #3456 pin chose a commit already past the change. Source: the Plan 11a wave close.
- **A task that changes a quoted line before the task that rewrites the claim pins the pointer, and the rewrite task removes the pin.** Source: Plan 11d rulings T7-3 and T1-4.
- **Re-anchor a pointer whose line only moved; pin only a line the change removed or rewrote.** 203 of 250 pins in Plan 11g Task 4 were moves, each hiding a live quote behind a dead commit. Source: ruling T10-2.
- **Split a line appended in place to keep pointers still onto its own line at the plan's close cleanup, with the re-anchor.** Source: Plan 11h: `NR_Server_Fitness.lua:40`, `testing/pzt/client.py` and `server.py`.
- **Run a trial apply of a claims delta on a `git archive` copy, never in the worktree against a scratch register.** Plan 11f Task 10's scratch apply rewrote tags on four real pages.
- **A number in a brief comes from its row, never from memory.** The cap-clamp brief used Kouri's height coefficient as 6.1; S1915 (PMID 7496846) carries 6.3, and every derived cap was recomputed. Source: the Plan 13 ledger L50-54.
- **`science_delta.py` cannot rewrite an open row's `range` cell.** Its row edits are `settle` and `status`, so a "keep open, new bound" change is a direct cell edit by the controller (precedent 3262bfb5), and nothing gates it. Source: `docs/superpowers/research/2026-10-16-game-feel/starvation-part-review.md`, "The existing open rows".
- **A `source` cell is provenance: it is never renumbered, and a `docs/superpowers/` path in it resolves at the tag `program-record-v19`.** Source: Plan 20 Task 3.

<a id="reviews-and-agents"></a>
## Reviews and agents

- **Name the model in every dispatch and ask for the exact model id back.** The Agent picker offers only family aliases with no version pin, so the Claude Code default-model config sets the version. Both aliases were verified on 2026-10-05 by the subagents' own reports (`claude-opus-5-5`, `claude-sonnet-5-5`). Source: Angus, 2026-10-04 and 2026-10-05.
- **List a brief and its amendments on disk, non-empty, in their own call before dispatching, and never write a brief through Bash.** In Plan 10c two agents were dispatched against files a failed heredoc never wrote, and Plan 11b repeated it.
- **Write briefs from a consolidated run sheet, never from the plan text, when amendments span several closes.** Plan 11b Task 3's brief carried the plan's stale `release/plan11-x251`, so the re-stage diff ran against `rebaseline-x250`. Source: ruling 11b-0.
- **A verbatim fix names its target by file:line and old text, and the spot-check greps the old text gone.** A Plan 11b delta-review fix landed on the duplicate of its target sentence, and the wrong copy survived to the close review. Source: T2-14.
- **A controller fix after a FAIL takes a scoped re-review unless it is pointer-, comment- or tag-only and mechanically verified.** Source: ruling T9-1, Plan 8.
- **A deferred wording re-review is named in the ledger and passed item by item by the next whole-delta review before the mint, or, past the mint, by the close review before the push.** Source: Plan 10c rulings H2-2, H4-3 and H5-1. In Plan 12 (P12-18), #3820, #3824 and #3829 were minted before their review.
- **The reviewer's own scratch-verified text, applied verbatim with its probes landed as tests, takes no re-review.** Source: Plan 12 P12-11, P12-12 and P12-17.
- **A small, spot-checked curator fix round takes no re-review when the close review re-samples the data.** Source: Plan 6 ruling T4-11.
- **Cut a bug triage's fix waves by file lane.** Source: Plan 12 waves A to C2.
- **Reproduce a checker miss on a minimal case before a fix brief names its cause.** The Plan 12 Task 3d brief blamed the multi-pointer cell; the cause was the superseded-row exemption (8a5ec795).
- **Write a no-change ruling's reason where the item lives, never only in the ledger.** Source: Plan 12 P12-1 to P12-3; #3788's settling cell had named the method P12-3 ruled out.
- **Take a commit's plan label from `git log -1 --format=%s <sha>`.** Plan 11c's Task 10 brief labelled 42784ff "Plan 11a"; it is Plan 10's.
- **Never assert an engine mechanism in a question to Angus without a register row or a jar read behind it.** The chips question offered a same-name `craftRecipe` override, which appends on 42.21. Source: Plan 11a Task 16.
- **Run the skill's scripts from the repository root.** A script writes its workspace relative to its cwd, so Plan 11f Task 10's brief landed in the plugin cache.
- **A subagent never installs a package into the host Python.** Plan 11f's thirst harvest installed pymupdf.
- **A plan's spec and plan stay in `docs/superpowers/` through and after its close, with a `HISTORY.md` entry; a consolidation on Angus's request archives the closed ones to a tag.** Plans 0-19 were removed by Plan 20 and are read at `program-record-v19`, indexed by `docs/superpowers/HISTORY.md`. Source: the 2026-10-05 ruling, Plan 20 decision 3 and ruling P20-7.
- **Never send Angus's email address to an outside service.** A Plan 6 subagent passed it to Unpaywall as that API's required parameter. Source: the Plan 6 ledger L65.
- **Run an independent whole-system review at milestones, and measure the expensive part.** Per-task and whole-pass reviews miss systemic defects: the 2026-10-07 whole-mod review, after nine closed plans, caught four release blockers (the stagger starving players past one per tick, a costly takeover, Overlay a stub, a gate benching only `K.fast.step`). Its diagnosis: instruments chosen for what was easy to measure and minted as proof. Source: the Plan 10 ledger L6 and L14.
- **Check a plan's hand-computed test values in doubles, and trace callers at review.** The coverage gate cannot see production-dead code: Plan 3's xpLevel ladder slipped twice, and Plan 4's caffeine hand values were wrong until recomputed. Source: the Plan 3 ledger L113, Plan 4 L32.
- **Budget a correction round for every science harvest.** Every harvest through Plan 11g failed its first citation review: 0b's Wave S, 11c, 11d and 11g. Source: `docs/superpowers/specs/2026-10-12-gut-satiety-design.md` L22.
- **Brief a harvest and its reviewer on the recurring citation defects (none was fabrication).** They are:
  - harvester arithmetic in a cell;
  - a within-group change read as a between-arm contrast;
  - a pooled or baseline-inclusive test read as the contrast (Dennis 2010, Roager's three-column ANOVA);
  - a controlled crossover graded EXP, which science.md counts as RCT;
  - the paper's label read as the achieved dose (Helms 2023's "+5 %" arm ate +18 %);
  - a figure legend quoted as Results;
  - a single-visit median without its visit;
  - a figure the source states relabelled as the harvester's arithmetic;
  - a superseded row (S0515) cited as live;
  - a self-contradictory abstract sentence resolved silently (Kwiatek 2009);
  - a list order read as an order of onset (Gétaz 2012).

  Source: the `*-review` halves of `docs/superpowers/research/2026-10-09-satiety-research-2/` and `2026-10-14-strength-redesign/*-part-review.md`; `2026-10-16-game-feel/water-part-review.md` §§ 3, 6 and 9, `volume-part-review.md` defect 1, and `starvation-part-review.md` defect 3.
- **Two grading rules science.md does not carry.** A row takes the report's grade unless the resolved record contradicts it outright, and then the record wins (a record typed Review with no pooling is not MA). The token "(via AUTH)" maps to AUTH. Source: the Plan 0b ledger L53 and L56.
- **Harvest-brief pitfalls:**
  - Give harvesters a conforming source cell (`<path>.md § …`). The brief's literal string failed `SOURCE_RX` in all seven Satiety-research-2 parts and the body-fat part.
  - Europe PMC REST returns 503 under parallel load, while PubMed E-utilities serves the same record. It also cuts abstracts at a `<`; re-read them through efetch.
  - PDF text layers can drop minus signs (Gallagher 2000), so rebuild signs against the tables.
  - Provisional dry-run ids hold only in apply order.

  Source: the Task 21-27 reports' Concerns; `docs/superpowers/research/2026-10-13-bodyfat-bands/harvest-report.md` L42.
- **Budget a research agent's Steam and search calls.**
  - The item-detail prefix `/sharedfiles/filedetails/` (and changelog and comments) returned HTTP 429 after about 4 fetches. It refilled at about 1 page per 20 min, shared by every agent on the IP. The browse and discussion-search paths were never limited.
  - `WebFetch` quotes are model-rendered, so re-read before quoting.
  - A science reader whose WebSearch budget is spent falls back to Europe PMC `TITLE:` queries, which miss oblique titles.

  The 2026-09-27 neighbours read got 5 of 6 detail pages and none of the families. Source: `docs/superpowers/research/compat-workshop-neighbours.md` L327-331; `wave2-science-cognition-mood-perception.md` L21.

<a id="git-and-worktrees"></a>
## Git and worktrees

- **Commit by pathspec only, and never run `git stash`, `checkout --`, `reset`, `restore`, `add -N`, `add -f` or any other index-wide command in the shared worktree.** A `git add -N .` marks every untracked folder intent-to-add, the agents' worktrees included, and only Angus clears the index. Source: the Plan 11h harness cleanup.
- **A scratch copy that needs git history is a standalone clone or an archive with the repository's objects as alternates, never a shell with `GIT_DIR` or any `GIT_*` variable aimed at the real `.git`.** A 3e reviewer's pytest under `GIT_DIR` let a test fixture commit `mod/x.lua` onto main (e68042a1, removed in 3f8ab5a8). The tests that write a repository now take `tools/tests/gitenv.scrubbed_env`. Source: Plan 19 and its Task 3e fix 1.
- **Run a mutation on a scratch copy, never on a tracked file restored afterwards.** Three Plan 11a fix rounds mutated tracked files.
- **A worktree task reaches `main` only by the controller's cherry-pick, after its complete line.** Source: Plan 11a ruling 1, ruling W-1.
- **When the intent-to-add index entries block a cherry-pick, bring the task over with `git show <c> | git apply` and pathspec commits.** The stale `A .claude/worktrees/...` entries are still in the index (only Angus clears them). Plan 13 used `git show | git apply`, kept the same subjects, and diffed the content empty. Source: the Plan 13 ledger L23.
- **Parallel agents never share a scratch directory.** A Plan 6 curator's generator was overwritten by a parallel curator, so curators moved to per-agent subfolders. In Plan 7 an unidentified agent appended Task 2's harness blocks a second time in the working tree. Source: the Plan 6 ledger L65, Plan 7 L97.
- **No lane leaves register-breaking files uncommitted while another lane commits under `docs/`.** In Plan 15 a register commit picked up a live lane's uncommitted `artifacts.md` re-anchor (6fe4d529). In Plan 17 (T5-1) a docs commit's staged gate read 6 findings, all from another lane's uncommitted page. Source: the Plan 15 ledger L20, Plan 17 L65.
- **Preserve each file's line endings.** Under `core.autocrlf=true` about half of `testing/tests/kernel/*.py` are CRLF in the working tree though LF in the index (Plan 11b Task 5). autocrlf rewrote six PNG blobs under `mod/` once, so they are pinned `binary` (Plan 7 Task 9).

<a id="fits-and-oracles"></a>
## Fits and oracles

- **Accept an oracle only after a mutation pass.** Plan 10's first golden trace missed six of seventeen mutations.
- **Re-record the golden trace only under a named behaviour change, in the commit of the task that reaches it.** Source: Plan 10 rulings 3 and R0-1, and Plan 11d ruling T2-1.
- **A fixture artifact never decides a production design.** When a one-shot test stub made the correct change move the golden, the change landed and the golden re-recorded under a named cause. Source: Plan 11g ruling T10-1.
- **A fit carries stability checks that a flat or degenerate read fails, and a reviewer probes each constant at ×0.95 and ×1.05.** In Plan 11g Task 6, G_STEEP 0.0197 went flat unseen by the loss, and its review set the probe.
- **A weight fitted to one system's studies never drives a quantity another system reads.** LIQUID_WEIGHT had set the fed gates' fill. Source: Plan 11g ruling T6c-1.
- **A fit's committed artifact is its compact projection, and the full file stays in `testing/runs/`.** Source: Plan 11g ruling T6c-4.
- **Pin a named non-reproduction at its reading, and also assert it still outside its band.** Source: Plan 11g, `gut_oracles.check`.
- **Replay a fit's constants through the shipped pipeline before accepting it; never fit on a simplification the mod does not ship.** The energy oracles booked a meal at the eat, while the shipped path books it as the stomach empties. That carried most of the 36 h fast's overshoot (1.348 against 1.304; F-1). Source: `docs/superpowers/research/2026-10-10-live-study-replays/02-fast-overshoot.md` L8-32, L216-231.
- **A constant that drains a conserved pool needs a multi-day balance test, and a thirst calibration belongs in the thirst function.** Ruling T11-3 (Plan 4) cured 10 h dry-rest thirst with a fixed isotonic basal sodium draw of 337 mmol/d. Every diet then walked the character to hyponatraemic death by about day 7 (F-T5-1), and no test ran a sodium balance past 10 h. Source: `docs/superpowers/research/2026-10-10-live-study-replays/05-sodium-drain.md` L83-88, L282.
- **Anchor a fitted scale on a constant the mod already holds.** The water report anchored its lean-mass scale on a guessed 55 kg reference man the mod does not model. The mod's 52.02 kg (`K.strength.averageLean()`) gives the recommended 2000 g exactly. Source: `docs/superpowers/research/2026-10-16-game-feel/water-report.md` § 9 item 2.

<a id="tools-and-gates"></a>
## Tools and gates

- **Read pytest's summary line and exit code from a saved output file.** At the Plan 15 close two piped runs reported exit 0 and hid 64 failures behind the stubs' log lines.
- **Read the checker's findings count before committing, never through a grep in a chained command.** Source: Plan 10: 1de05d0, 8593c10.
- **Run a test in its own call, and never chain a commit after it.** A chained command commits past a red test: Plan 7's icon_gen residual took three commits.
- **Run the full `claims_check` after any commit that touches `mod/`, `tools/README.md` or any file the register points into.** The staged gate does not trigger there: #3012 went stale after 6307559 (Plan 5), and 4c20a113 left 16 stale pointers (Plan 11g ruling T4-2).
- **Regenerate the guide data after every commit under `mod/`.** The data names mod/'s last commit: at the Plan 15 close, a README commit after the regeneration failed 64 provenance tests.
- **Recipe conservation is a report, never a fix.** Source: Plan 11a rulings T16-3 and T17-1.
- **The generators' gates trace to their plans:**
  - `dials.py check`: Plan 19 Task 2. Every dial row in `NR_Data_Dials.lua` has a unit, a finite range and a source that resolves, and every `K.dials.get` names a row.
  - `dial_lint`: Plan 19 Task 3g.
  - `sandbox_options`: Plan 19 Task 3f.
  - `food_hedonics`: Plan 19 Task 5.
  - `comment_id_lint`: Plan 20 Task 6 (gate at its close).
  - `food_fills`: Plan 15 Task 9. It replays each item through the server's kernels for the tooltip's fill table.
  - `mod_guide_data`: Plan 14.
- **A lupa bench stubs Java, so count a per-minute adapter's Java calls with a recording stub, against the build before.** The Plan 11g close caught two duplicated reads a player-minute that the bench could not see.
- **A bench counts the calls on every Java object it stubs, including objects a module fetched before the count began.** `tools/bench_drain.py` missed every stat get and set until Plan 18 Task 3, so earlier bench numbers are not comparable with later ones.
- **A rename sweep touches present-tense text only.** `MEAL_HALF_LIFE_H` was written into Plan 11g Task 4's mutation record.
- **Never wrap a timed action's `new`.** The client sends the action's arguments by the parameter names of the `new` closure, so a varargs wrapper sends none and the action breaks for everyone. Source: Plan 11h; [platform/lessons#rules](../platform/lessons.md#rules).
- **The mod is unreleased: write no migration or compatibility code, and remove any found.** Source: Angus, 2026-10-09; Plan 11d Task 9b ruling C9-10. The rule lapses at Angus's Workshop upload, not at packaging (Plan 11b ruling 11b-1).
- **Refactor heavily as you go until the first release.** Source: Angus, 2026-10-12.
- **Re-baseline before any build work after a game update.** Source: Plan 11a ruling 17, Task R.
- **Plan 19's hedonics rulings (T5-1 to T8-1) live in the dial notes and #4156-#4168's bounds.** Changing one is a dial tune or a ruling.
- **`preview.png` beside the staged item is Angus's to supply, 256×256.** It was absent on 2026-10-06, and `release_pack.py stage` WARNs without it.
- **A ring row's keys are flat dotted strings (`"stomach.liquid"`).** A reader matches the longest key before splitting a path on dots, and a leaf is written `rows_list[k]["stomach.liquid"]`. `tools/mod_guide_data.py` handles it, and no reference page says it. Source: the source map § 0, "Ring leaves".
- **Rule 3b line-checks a run's `GUIDE.md`, and only that file under `testing/artifacts/`.** The rest of the folder is evidence the checker cannot quote by line. Before Plan 20 Task 4 the whole folder was exempt, so #1504's pointer into `td2-20260910-231655/GUIDE.md` was never checked.

<a id="test-baseline"></a>
### The test baseline

The full pytest count never drops. A reset by name deletes tests of dead code only, and names each one in its task report. CLAUDE.md § 3 keeps the latest count.

| Close | Passed | Resets and notes |
|---|---|---|
| Plan 1, 2026-10-04 | 489 | |
| Plan 2, 2026-10-05 | 676 | |
| Plan 3 | 1216 | |
| Plan 4, 2026-10-05 | 1552 | |
| Plan 5 | 1855 | |
| Plan 6 | 2100 | |
| Plan 7 | 2416 | |
| Plan 8 | 2506 | |
| Plan 9 | 2544 | |
| Plans 10 and 10b | 2634 | |
| Plan 10c | 2637 | |
| Plan 11a | 2979 | two resets by name (rulings T8-1, T14-1): deleted tests of dead code, never live code |
| Plan 11c, 2026-10-08 | 3264 | reset by name (T6-1, T9-1): the retired stomach and Task 15 satiety code |
| Plan 11d | 3340 | Task 9b deleted tests of removed compatibility code by name |
| Plan 11e, 2026-10-09 | 3473 | |
| Plan 11f, 2026-10-11 | 3828 | |
| Plan 11g, 2026-10-12 | 3945 | none deleted; tests of removed code rewritten under the meal pool M's names, one dead `--stage A` test removed with its option |
| Plan 11h | 4032 | with the harness dialog tests |
| Plan 11b, 2026-10-13 | 4077 | one test that asserted the Timeline.mark TypeError rewritten to assert its fix |
| Plan 12, 2026-10-14 | 4173 | reset mid-plan from 4181 to 4159 (P12-13): 23 tests of the removed `dmod` chain, named in `task-3a-report.md` |
| Plan 13, 2026-10-15 | 5592 | the old Strength model's tests deleted with it at c7e816e6 (`task-12-report.md`); 15 thin-rung and exclusion tests replaced at 31ce0635 (`task-10c-report.md`) |
| Plan 14, 2026-10-16 | 6444 | none deleted |
| Plan 15, 2026-10-17 | 6983 | the marker plumbing's tests, the 72-slot ring's 4, the calendar starved-hours test and 4 SE1 live-guide cases with their check (task-6, task-13 and task-14b reports) |
| Plan 16, 2026-10-19 | 7290 | 38 tests of the removed prune, the return catch-up hour and the world-clock rhythm (the task reports) |
| Plan 17, 2026-10-20 | 7545 | the curve-era x481 HEAD tests frozen into one archive test and one DROPPED-series check (task-2b report) |
| Plan 18, 2026-10-21 | 7844 | the composer's dead enduranceCap test removed with its line (the close-fix report) |
| Plan 19, 2026-10-23 | 8269 | none deleted; two `test_recipe_scan.py` spice tests replaced by name in eb97dbfb (`task-4b-report.md`) |
| Plan 20, 2026-10-24 | 8329 | none deleted; `test_pointer_with_a_non_hex_pin_says_only_a_hex_commit_is_supported` replaced by name in 350040d0 (`task-1-report.md`) |
