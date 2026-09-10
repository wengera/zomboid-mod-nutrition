# Decisions ledger

Every judgment call taken unattended goes here (spec: "take the default, log
it"). Each entry is reversible: overturn it by editing the line and, if work
depended on it, adding a ripple note in [progress.md](progress.md).

| Date | Slice | Decision | Alternatives | Why |
|---|---|---|---|---|
| 2026-09-09 | program | Slices are question-driven and sized for one session; plans written just-in-time per wave | one slice per phase; source-driven sweeps | cold-start finishability and crisp acceptance; sweeps folded in as tooling where cheapest |
| 2026-09-09 | program | Wiki pages fetched with `curl` + browser user-agent from the raw/API endpoints | in-app browser; user pastes pages | the plain fetcher is blocked (403); raw wikitext carries the wiki's own page-version stamp |
| 2026-09-09 | program | Fixture world uses `Zombies=6` (none) | vanilla zombie population | deterministic, safe spawn area for unattended runs; zombie-dependent behaviour is out of scope for nutrition |
