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
