# `run-20260910-133657` reading guide

**`run-20260910-133657/report.json`** — written by `pzt run --profile mod-under-test --hold 5`
(93 s wall; the server BOOT took 36.6 s and the client took a further 37.3 s to reach in-world;
`RESULT: PASS`, exit 0). The slice-07 acceptance run: a named mod set on the golden fixture,
proven to have taken **effect** and not merely to have booted quietly.

- **Read it this way — two traps in the file's own shape.** (a) `t` on the `server_started` and
  `client_ready` marks is the STEP's duration, not elapsed time: 37.3 is how long the client took,
  and the run reached in-world at about 74 s. Every other mark's `t` is elapsed, and a run at HEAD
  writes the duration under `took` instead (see the skew list above). (b) `timeline[].got` is
  truncated at 100 characters (`session.verify`) — on both `verify` marks here it ends at
  `"keenPerceptionLoaded"`, immediately before the value the claim rests on. The full parsed value
  is `report.json["verify"][n]["got"]`; quote that, never the mark.

- **Provenance — the profile.** `testing/profiles/mod-under-test.toml` at this commit:
  `fixture = "default"`, `run = { hold = 5 }`, `[[mods]] id = "PZTestKit"` then
  `[[mods]] id = "KeenPerception", workshop_id = "3685392864"`, `[sandbox] DayLength = 1`, and
  two `verify` entries (`side = "server"` / `"client"`, `cmd = "trait.check"`,
  `expect = '"keenPerceptionLoaded": true'`). The file's own bytes are reproduced in the
  artifact's `profile` block, which records both what was asked for and what it **resolved to**
  — the two source folders that actually reached `<run>/server/mods/`.
- **Provenance — the mod.** Workshop item `3685392864` (15 KB), version folder `42/`, whose
  `42/mod.info` declares `id=KeenPerception`, `name=Keen Perception`, `author=somewhatfrog`,
  `pack=trait_keenhearing`, **no `require=`**, no sandbox options; one shared Lua file
  (`42/media/lua/shared/SWKeenPerception.lua`), a translation JSON and a texture pack. It is
  spike S3's own subject. The workshop folder is read-only to the harness: `harness.install`
  copies it into the per-run cache, so nothing under `steamapps/` is touched by a run.
- **What `verify` proves.** Both probes returned
  `{"keenHearingExcludesDeaf": false, "keenHearingExcludesHardOfHearing": false,
  "keenPerceptionLoaded": true}` — the Keen Hearing ↔ Deaf / Hard-of-Hearing exclusivity is
  *gone* on the server **and** on the client. `trait.check` is the harness's own command
  (`PZTestKit_Core.lua`), reading `CharacterTraitDefinition.getCharacterTraitDefinition(
  CharacterTrait.KEEN_HEARING):getMutuallyExclusiveTraits()`. A boot log alone could not say
  this: under `-nosteam` a mod the game cannot find is a WARN and a clean boot (S3-A), so
  "0 errors" is compatible with the mod never having loaded. Server log line 94 also has the
  positive form, `LOG : Mod … loading KeenPerception`. Three keys, **two** independent readings:
  `keenPerceptionLoaded` is defined as `not ex:contains(CharacterTrait.DEAF)`
  (the harness's own `trait.check` in `PZTestKit_Core.lua`), the negation of
  `keenHearingExcludesDeaf` — not a third witness.
- **The sandbox merge, measured.** `[sandbox] DayLength = 1` was merged into the restored
  fixture's `Server/pzt_SandboxVars.lua` (`applied ['DayLength'], appended none`), and the
  server then rewrote that file during boot as it always does (spike **T0**: a *partial*
  SandboxVars file is filled in with defaults and rewritten whole; `server.py:80-81`). After the rewrite the
  run's copy still reads `DayLength = 1` **and** the fixture's own `Zombies = 6`, at **189**
  four-space assignments / **184** `sandbox_keys()` settable options — the fixture's counts
  exactly. `diff` against the fixture file is **one line**, the seeded one; every comment, the
  five nested tables and their 86 eight-space options and all 1 020 CRLF endings survive. The
  merge composes, it does not replace. (**Where those numbers live.** Not in `report.json`, and
  not in its timeline either — the merge line is a `[server]` console `echo`, not a timeline
  mark. They are read off the file itself, and this block is what records them. The file is
  `pzt_SandboxVars.lua`, committed beside `report.json` in this folder: a byte-for-byte copy of
  `testing/runs/run-20260910-133657/server/Server/pzt_SandboxVars.lua`, which lives under the
  gitignored run directory. 45 533 bytes, sha256
  `6f0109c687a9d2b588f319924b0190f8ca06d73e67f7204e2bb9bd621914cffa`; `.gitattributes` here sets
  `* -text`, so the 1 020 CRLF endings are the committed blob's own.)
- `server_errors` is **0** and `faults` is empty, so the `RESULT: PASS` is a pass on a clean
  session, not merely a green probe.
