# Decisions ledger

Every judgment call taken unattended goes here (spec: "take the default, log
it"). Each entry is reversible: overturn it by editing the line and, if work
depended on it, adding a ripple note in [progress.md](progress.md).

| Date | Slice | Decision | Alternatives | Why |
|---|---|---|---|---|
| 2026-09-09 | program | Slices are question-driven and sized for one session; plans written just-in-time per wave | one slice per phase; source-driven sweeps | cold-start finishability and crisp acceptance; sweeps folded in as tooling where cheapest |
| 2026-09-09 | program | Wiki pages fetched with `curl` + browser user-agent from the raw/API endpoints | in-app browser; user pastes pages | the plain fetcher is blocked (403); raw wikitext carries the wiki's own page-version stamp |
| 2026-09-09 | program | Fixture world uses `Zombies=6` (none) | vanilla zombie population | deterministic, safe spawn area for unattended runs; zombie-dependent behaviour is out of scope for nutrition |
| 2026-09-10 | program | Slices execute on `main` directly (no worktree) | feature branch + worktree | the golden fixture blobs are gitignored and exist only in this checkout; the approved protocol is commit+push per slice |
| 2026-09-10 | program | All subagents run on Opus; the lead stays on Fable | cost-tiered models per task | user instruction |
| 2026-09-10 | program | Research-only subagents (notes, mirrors) may run beside one implementer and never commit; the lead commits their output | strict serialization | no file overlap, and withholding git from them removes index contention |
| 2026-09-10 | 01 | `doc_lint` acceptance per slice = 0 findings in the dirs the slice owns/touches; pre-existing findings elsewhere are deferred to the slice that owns those docs | repo-wide zero from slice 01 | keeps slices bounded |
| 2026-09-10 | 01 | `doc_lint` resolves paths against the repo root (`--root` for tests), lints file targets directly, skips `.superpowers/`; `sources` must have a non-blank line before the next `## ` | brief's original root-relative design | the original gave false greens on file/path arguments |
| 2026-09-10 | 01 | The pre-refresh Modding hub excerpt is kept as `references/wiki-mirrors/modding-hub-archived.md` | delete it (page slug changed) | mirrors exist to preserve drift; the page's 42.20.x news section is gone from the live page |
| 2026-09-10 | 01 | Harness `eat` keeps its client-side `AddItem` fallback (experiment-only, reports `spawned`); anything that must stay error-free spawns server-side via RCON `additem` | remove the fallback / baseline the NPE | the NPE is a real vanilla symptom of client-created items and must not be masked; `pzt run` never uses `eat` |
| 2026-09-10 | 01 | No live re-run for a fix round that only reorders teardown/writes; the next live task validates it | re-run the smoke (~2 min) | the matrix run exercises the same code path minutes later |
| 2026-09-10 | 01 | Measured-evidence JSON (matrix/smoke results) is committed under `testing/artifacts/<run-id>/`; docs cite those paths | keep results only in gitignored `testing/runs/` or `.superpowers/` | an M grade must be checkable from a clone; the files are small |
| 2026-09-10 | 01 | Harness `eat` uses the 3-argument `IsoGameCharacter.Eat(item, fraction, useUtensil)` (works from Lua); recorded in the command's `signature` field | 2-argument form | the 3-arg form is what `ISEatFoodAction` calls |
| 2026-09-10 | 01 | Drink-type test item is `Base.HotDrink` (HungerChange 0, ThirstChange −20, not a `Test*` item) | any other `food.txt` drink | first match of the plan's criterion |
| 2026-09-10 | 01 | Sandbox `Nutrition` flipped at runtime via `getSandboxOptions():set(name, value)` (worked first try; the `getOptionByName(...):setValue` fallback and the `sendToServer` push path are untested) | re-provision with `--sandbox Nutrition=false` | runtime flip was enough for the probe |
| 2026-09-10 | 01 | The n=1 observation that a client-local sandbox flip coincided with the server's drain slowing is recorded only as an open question (slice 03 re-tests with an explicit push and a no-flip control), not as an M row | record it as measured | `SandboxOptions.set` is client-local per bytecode; one run without a control cannot establish the mechanism |
| 2026-09-10 | program | When a fix round follows a slice's last live run, the artifact README must note the script/artifact skew (producing commit + what the current script adds) instead of assuming a later run erases it | re-run the experiment after every fix round | re-runs for teardown-only changes are poor value; disclosure keeps the evidence honest |
| 2026-09-10 | 02 | All measured steps of the slice run as one live session script (`s02_lifecycle.py`, phased saves) instead of four scripts | one script per plan task | one boot instead of four; per-phase saves keep earlier evidence if a late phase wedges |
| 2026-09-10 | 02 | Claim-level fixes after the last live run are not re-run; the artifact README discloses the script/artifact skew | re-run the session (~6 min) | the fixes changed wording and a prediction denominator, not measurements |
| 2026-09-10 | 02 | The doc task ran in parallel with the measured task's scoped re-review, working from the controller-corrected brief | strict serialization | disjoint files; the corrections were already known |
| 2026-09-10 | 02 | `cooked` is graded C (not M) in the ItemStats packet table: both sides already read `false`, so agreement was uninformative | grade it M with burnt/cookingTime/heat | only diverging fields carry information |
| 2026-09-10 | 02 | `ItemStatsPacket` item-state field count is stated as 39 (isCustomName is applied to the item via `setCustomName`, so it is state, not a header flag); the doc names both counting conventions | 38 (isCustomName as a presence flag) | the doc's own criterion — applied on receipt — decides |
| 2026-09-10 | 02 | The cross-item `cookingTime` leak is documented from code (write skips zero fields, apply is unconditional) with at most one confirming live run | three discriminating live runs | the mechanism is C-gradable; the hazard covers every conditionally-written field |
