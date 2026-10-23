# `run-20260910-133916` reading guide

**`run-20260910-133916/report.json`** — written by `pzt run --profile missing-mod` (23 s wall;
`RESULT: FAIL`, exit 1). The regression for the failure mode S3-A found: the game *does not*
fail on a mod it cannot locate, so the harness has to.

- **Provenance — the profile.** `testing/profiles/missing-mod.toml` at this commit: `fixture =
  "default"`, `[[mods]] id = "PZTestKit"`, `[[mods]] id = "NoSuchModHere", copy = false`. Nothing
  is installed for it and nothing needs to be — `copy = false` names the mod in `Mods=` and
  places it nowhere, which is precisely the state S3-A measured.
- **What it proves, and where to read it.** The `timeline` phase list is
  `profile → server_launch → server_started → mods_not_found → mod_missing_line → error →
  server_stopped → faults`: **there is no `client_launch`**, and the run directory has no
  `clients/` folder at all, so the ~37 s of client boot was never paid for. `mod_missing_line`
  carries the server's own words verbatim — `WARN : Mod … at
  ZomboidFileSystem.loadModAndRequired> required mod "NoSuchModHere" not found` — which is the
  finding, in the game's voice rather than the harness's. `faults` repeats the reason once
  (`mods not found at load: NoSuchModHere`); the `RESULT:` line prints once.
- **Do not read `server_errors: 0` as "nothing was wrong".** It is 0 because a missing mod is
  *not* an error line to this game: the server booted normally in 13.7 s with the mod absent.
  That is the whole point of the run.
