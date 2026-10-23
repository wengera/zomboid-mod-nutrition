# `run-20260910-151642` reading guide

**`run-20260910-151642/report.json`** — written by `pzt run --profile mod-under-test --hold 5`
(70.7 s wall; `RESULT: PASS`, exit 0) on the CLI at `a6b0b54`, the commit of slice 07's final fix
wave. The same profile as `run-20260910-133657`, re-run as the wave's acceptance: nothing here is
new evidence about the mod, and everything about the file's shape is.

- **Read `t` as elapsed on every mark.** `server_started` is at `t: 16.3` with `took: 15.8` (a
  warm boot — the fixture's world already existed), `client_ready` at `t: 54.2` with `took: 37.3`;
  then `session_ready` 54.9, the two `verify` marks 55.2 and 55.4, `hold` 55.4, `client_quit`
  62.7, `server_stopped` 70.7. The `took` values are what the pre-wave artifacts carried under `t`.
- **What `verify` proves, again.** Both probes returned the same three keys as
  `run-20260910-133657` with `keenPerceptionLoaded: true` on the server and on the client;
  `report.json["verify"][n]["got"]` holds the parsed value (the marks' `got` is still the
  100-character string).
- `server_errors` and `faults` are both empty. The hold ran because both probes passed; at HEAD a
  failed probe skips it, which a passing run cannot show.
- **Provenance** is the same profile file and workshop item as `run-20260910-133657`
  (`3685392864`, `42/`, `id=KeenPerception`), resolved to the same two source folders in the
  artifact's `profile` block.
