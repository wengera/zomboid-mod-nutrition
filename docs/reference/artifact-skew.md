# Script/artifact skew

The skew preamble of the artifacts register, moved whole from [`artifacts.md`](artifacts.md) in Plan 20; where it says a run's block is below or at the end of this file, that block is now the run's own `testing/artifacts/<run>/GUIDE.md`.

Standing rule (logged 2026-09-10, program): **when a fix round follows a
slice's last live run, this README notes the skew — the commit that produced the artifact and
what the current script adds — instead of assuming a later run erases it.** Re-running an
experiment for a teardown-only change is poor value; disclosure is what keeps the evidence
honest. Both slice-01 artifacts predate that slice's last fix round, the slice-02 artifact
predates slice 02's, the slice-03 artifact predates slice 03's fix round 1, all three
slice-04 scenario artifacts predate slice 04's, and the slice-05 artifact predates slice 05's
fix round 1 — which added the dataset's `sha256` and dirty flag to `meta`, kept the routed
dataset number as `dataset_routed`, gave the `fluid.script` rows their own transform labels,
narrowed a fluid container's `"n/a"` permission to the six `Food`-only getters and made a
wedged reply a mismatch on every field. The ninth, `exp05b-20260910-093307`, was skew-free
until slice 05's **final fix wave** corrected two of its drift labels and the band they set;
it is listed with the rest, at the end, where it also carries a *do not cite* block of its
own. So all nine are below.

The tenth, **`exp06-20260910-112726`**, and the eleventh, **`exp06b-20260910-120123`**, were
skew-free — each landed in the same commit as the script and the harness command that produced
it — **until slice 06's final fix wave**, which edited both drivers *and* both harness files.
Neither block's measured numbers move, and both blocks now open with a skew note saying exactly
what changed and why (the verdict defect that scored an unmeasured row as a pass, the
`collect()` absent-vs-empty guard, the `item.use` refusal on a depleted item, the tolerance
anchoring, the corrected citations, and a pure move of five helpers into `_common.py`). Both
blocks are also reading guides: `exp06`'s carries three **errata** and two *do not cite* keys —
two of its `summary` keys mislead when quoted alone, one *plan* expectation it was run against
turns out to be wrong, and the scanner has since resolved the two mismatches its `comparison`
block records; `exp06b`'s carries two *do not cite* keys and the reminder that the reduction ran
through the `setCurrentUses` **fallback** rather than through `ItemUser.UseItem`.

The twelfth, thirteenth and fourteenth — **`run-20260910-133657`**, **`run-20260910-133916`** and
**`scenario-20260910-134012`** — were **skew-free** for that same reason (the profiles that produced
them and the artifacts landed in one commit, and the CLI they ran on was already at HEAD) **until
slice 07's final fix wave**, which edited seven modules under `testing/pzt/` — `mods.py`,
`profile.py`, `session.py`, `cli.py`, `scenario.py`, `server.py` and `spikes.py`. `server.py` is the
one that matters here: `merge_sandbox_vars`, the path behind the sandbox `M` of run 1, now keeps a
trailing comment on a rebuilt line and finds the closing `}` at column 0 only; run 1 appended
nothing and its seeded line carries no comment, so nothing it wrote would differ. `spikes.py` only
moved three `took=` sites. **No measured number in any of the three
moves**; every difference is a shape a *future* run would write, and they are listed here rather
than re-run:

- **`took=`.** `server_started` and `client_ready` used to pass the step's own duration as `t=`,
  overwriting the elapsed timestamp every other mark carries. They now pass it as `took=`, beside
  an elapsed `t`. In these three artifacts — and every artifact committed before this wave — `t`
  on exactly those two marks is the STEP's duration, not elapsed time. Read run 1's
  `server_started t=36.6` as "the boot took 36.6 s", never as "36.6 s into the run".
- **`[[verify]]` on the scenario path.** `scenario.run` now runs the profile's probes after
  `client_ready` and records them in `report["verify"]` and the artifact's new `verify` key. The
  scenario artifact below has neither, and its block says so.
- **The artifact's `profile` is the resolved name** (`Profile.name`) rather than the raw
  `--profile` token, so it cannot disagree with `report["profile"]["name"]`. Identical here: the
  run was `--profile mod-under-test` and the name resolves to `mod-under-test`.
- **A RESULT that had no reason of its own now takes the faults.** Run 2's committed
  `result` is the bare `"FAIL"`; the same run today would write
  `"FAIL: mods not found at load: NoSuchModHere"`. The reason is unchanged and is already in
  `faults` in this file — only the RESULT string is shorter here.
- **The `error` mark's `detail` gains its exception type** (`RuntimeError: mods not found at
  load: …`), because `cmd_run`'s `except` widened to `Exception` so that a bus `PermissionError`
  cannot lose `report.json`.
- **A failed probe now skips the hold** on `pzt run` (it used to hold anyway), and `mods.py`
  resolves a mod folder's `mod.info` by parsed version tuple. Neither changes these runs: every
  probe passed, and `KeenPerception` ships one version folder.

The fifteenth and sixteenth — **`run-20260910-151642`** and **`scenario-20260910-151753`** — are
the wave's own acceptance runs, made by the controller on the CLI at `a6b0b54` after the wave
committed and before anything else touched `testing/pzt/`, so they are **skew-free** and are the
first artifacts written in the shapes the list above describes: `client_ready` carries
`took: 37.3` beside an elapsed `t: 54.2`, and the scenario artifact has a `verify` key. Their
blocks are at the end of this file.

The seventeenth, **`exp08-20260910-152944`**, is the first artifact of a different wave: its
driver (`testing/experiments/s08_witness.py`) landed in the same commit as the file (`ba19649`),
and the harness Lua it exercises — the `witness.*` block of `PZTestKit_Core.lua` — was at
`d260671` and clean in the working tree when the run booted, which the artifact records for
itself (`meta.harness_lua_commit`, `meta.harness_lua_dirty`). It writes the `took` shape as well.
It was skew-free until **slice 08's review round 1**, which edited the driver and not the Lua:
`isinstance` guards on four grading blocks, a checked `WITNESS_MAX`, a `getOrCreate` finding
recognised in a string reply as well as a table's `error`, tighter `expected` text on two rows,
and two dead names removed. **Every one of those paths was inert on this run**, so no number in
the file moves and it was not re-run; its block opens with the note. Its block is at the end of
this file.

The eighteenth, **`td1-20260910-192457`**, is slice 09's first teardown session, and it carries
skew of both kinds — a driver fix round and a **harness** one. Its own commit (`e3afaa0`) landed
the driver and the artifact together, on harness Lua at `37e411e` (clean, recorded in the file as
`commit` / `harness_lua_commit` / `harness_lua_dirty`). Then the review round edited the driver
(`4239c5d`, four minors) and the harness (`903ccaa`, two read-backs), with **no re-run**:

- **Driver (`4239c5d`), four edits, none of which changes what a command sent or what a reply
  said** — they change only how the Python side files what came back: a failed re-ask now records
  `reasked` / `first_reply` under `notes` instead of dropping them; the modData exclusion set is
  now per scope (`VANILLA_ITEM_KEYS` for items, `VANILLA_PLAYER_KEYS` for the player — see the
  *do not cite* row below, which is the defect this fixes); `KEYS` is documented as a **display**
  string whose ` | ` is a reader's separator and never a bus token, with a `KEYS_NOTE` in
  `notes`; and the RCON spawn's success is recorded as `rcon_additem_ok` beside the empty
  `rcon_additem` body. **No number in this file moves.**
- **Harness (`903ccaa`), two additions only** — `TK.ITEM_STATE` gained a read-only
  `lastCookMinute` and `item.set`'s ack gained `gameMinute`. The ripple is wider than the three
  server commands: **every `itemState`-bearing reply on both sides gains `lastCookMinute`**,
  because the state table lives in the shared core. This artifact predates both, so every
  `item.get` / `item.set` / `item.update` reply in it simply lacks those keys; `td1b-*` is the
  first artifact that carries either. A diff against a later artifact will show the addition —
  it is an addition, never a changed value.

The nineteenth, **`td1b-20260910-202029`**, is the follow-up micro-session that the same review
round commissioned, and it is **skew-free**: driver and artifact landed in one commit (`38ecf23`)
on harness Lua at `903ccaa`, clean in the working tree, which the file records for itself
(`commit`, `harness_lua_commit`, `harness_lua_dirty false`, `doctor_clean true`). Both blocks are
at the end of this file.

The twentieth, **`td2-20260910-231655`**, is slice 10's teardown session and is **skew-free** the
same way — driver and artifact in one commit (`7453580`) on harness Lua at `291f977`, clean, all
four facts recorded in the file itself. One disclosure that is *not* skew but belongs beside it:
a later residuals commit (`0449fa3`) touched only a **comment block** in `PZTestKit_Core.lua`
(and prose elsewhere) — **no executable path moved**, so the harness this file was measured on
is the harness at `291f977` in every sense that can change a number. It is nevertheless the artifact the next paragraph is
about: it is the first one written on the far side of the rendering change, and no artifact
listed above it can be diffed against it number-for-number.

The twenty-first, **`td3-20260911-001948`**, is slice 11's teardown session and is **skew-free**
in both senses: driver and artifact landed in one commit (`3f4b646`) on harness Lua at `d8cc34e`,
clean in the working tree, with `commit` / `harness_lua_commit` / `harness_lua_dirty false` /
`doctor_clean true` / `acceptance_run` all recorded in the file itself — **and no fix round
followed the run**, so there is nothing to disclose on either side. Its harness addition
(`lua.global`) landed in its own commit **ahead of** the session, as the standing rule requires,
and the acceptance run was its smoke test. Two *driver* notes that are not skew but are worth
knowing before reading the file: `carrier.window_s` records the **requested** 10.0 s while the
probe's own wall stamps give the **measured** 12.54 s, and the `t+3s` tag is a nominal name whose
snapshot actually opened at transmit + 7.58 s. Both are in the block's *do not cite* table.

The twenty-second through twenty-eighth — **`x121-20260911-030023`**, **`x122-20260911-032326`**,
**`x123-20260911-034426`**, **`x124-20260911-035819`**, **`x125-20260911-042055`**,
**`x126-20260911-045205`** and **`x127-20260911-052049`** — are slice 12's seven platform sessions,
and **all seven are skew-free**. Each driver landed in the **same commit** as its artifact
(`6afcb40`, `73e1fd6`, `ef1f678`, `f6c336e`, `6549e4a`, `72b6355`, `5d3f22d`) and **none was edited
afterwards**: `git log -- testing/experiments/x12*.py` shows exactly one commit per driver. All
seven ran on harness Lua at **`5d9633f`**, clean in the working tree, and every file records
`commit` / `harness_lua_commit` / `harness_lua_dirty false` for itself; all but `x123` also record
`doctor_clean true` and their `acceptance_run`. The slice's **only** harness change — the
`text.get` move to `shared/` and its null guard — landed in its own commits **ahead of** the first
session (`ad683fe`, then `5d9633f`), as the standing rule requires, and `x121`'s acceptance run
`run-20260911-024303` was its smoke test.

Three disclosures that are **not** skew but belong beside the list. (i) **`x121`'s first attempt
aborted**, at run id `x121-20260911-025811`: the driver died in M1's grading call
(`TypeError: Timeline.mark() got multiple values for argument 'phase'`) **before any verdict
existed**, no reading of any kind was taken, the run directory was its own copy of the fixture, and
the aborted artifact folder was deleted. The driver was fixed, `doctor` re-run clean and the
session re-run — so the committed driver is the one that produced the committed file, and this is
the opposite of skew. (ii) **`x123` skips `session.verify` by ruling** and says so in its own
`verify_skipped` key: every `[[verify]]` row of profile `x12-loader` is client-side and that
session attaches no client, so each row would have recorded `no client attached` — neither a pass
nor a fail, and not evidence. (iii) a later **comment-only** harness commit (`fefe323`, the
`TK.call` header note that carries x126/x127's correction into the code) moved **no executable
path**, so the harness these seven were measured on is the harness at `5d9633f` in every sense that
can change a number. The slice-12 blocks at the end of this file were written after all seven runs;
they are reading guides, never edits to the files.

One further disclosure, unchanged by the wave and about the harness mod rather than the CLI: a concurrent slice-06 fix round had
`PZTestKit_Server.lua` and `PZTestKit_Server_Recipes.lua` modified in the working tree when these
three ran, so the copies in their run caches are that in-flight text rather than either commit's.
Nothing on the paths these runs exercised is in those two files — `trait.check` is in
`PZTestKit_Core.lua`, `smoke_clock` in `server/scenarios/PZTestKit_Scenario_Smoke.lua`, the bus and
the game-minute scheduler in `PZTestKit_Core.lua` / `PZTestKit_Test.lua`, and all four were at HEAD
— and all three runs recorded `server_errors: 0`. Beside the skew list, these blocks carry the
**provenance a profiled run needs and a plain experiment does not**: the two inputs are the
profile file and the mod folder, so each block records the profile's bytes (they are also in the
artifact's own `profile` block) and which workshop item, `mod.info` id and version folder the mod
was copied from.

A skew entry is about the *script*. Which **dataset** an artifact was measured against is a
separate question, and `exp05-20260910-084109` is the run that shows why: its
`meta.dataset_commit` names a commit the bytes it read were not in. That is a *do not cite*
row in its block, not a skew bullet.

**A skew of a third kind landed in `291f977`, and this is it.** Until that commit
`TK.json` rendered every non-integral number with `string.format("%.6f")`, so **every float on the
bus — in every artifact listed above — is quantised to six decimals**, and none of them supports a
bit-for-bit claim. From `291f977` on, the same branch renders `tostring(v)`, which is
Kahlua's `KahluaUtil.numberToString` → `Double.toString(d)` for a non-integral double and therefore
round-trips exactly; integers are untouched (the `%.0f` branch still takes them first), so no key
changes name or type, and NaN still answers `null` while ±Inf — previously an unparseable ack (C, inferred, not measured) —
answers `null` too. The three candidate formats the deferral named (`%.9g` / `%.10g` / `%.17g`)
were not chosen; the reason is in
[`platform/harness.md#artifacts-discipline`](../platform/harness.md#artifacts-discipline), beside the format
itself. This is a **rendering** change, not a measurement one: it changes the shape of every ack
the harness emits and therefore of every artifact written after it, while everything written
before it — `td1`, `td1b` and all seventeen older runs — stays exactly as recorded and stays
readable at six decimals. **The first artifact written under the new format is `td2-20260910-231655`**
(`teardown-simplestatus.json`, its Contents row below), whose client-side weight readings are
exactly float32-representable while its server-side ones are not — the `d2f`/`f2d` narrowing on
the wire, which six decimals could not have shown; it is also
the first artifact whose `nutrition.get` / `stats.get` replies carry the three
`incWeight` / `incWeightLot` / `decWeight` keys that same commit added.
