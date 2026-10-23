# `x381-20261013-074847` reading guide

**`x381-20261013-074847/dialogs.json`** — produced by `testing/experiments/x38_dialogs.py` and `testing/profiles/x38-dialogs.toml`, committed at `95cd91ab` before the boot (`commit`), on the harness change `bdaf000c` and `9a567d6b` (`harness_py_commit` `9a567d6b`, clean) and the mod at `cc3c9cef` (`mod_commit`, never booted: the staged copy `release/x38-dialogs` was booted). One session, 322 s of wall time (`wall_seconds`), exit 0, on fixture `two` (admin `-debug`, then bob release, attached one at a time), build 42.21.0, Nutrition false, DayLength 1, sleep off. `MANIFEST.json` is the staged copy's manifest, byte-identical.

How to read it. The grade is `verdicts.*.observed`; every verdict is as_predicted. `phases.A` and `phases.W` hold the raw per-client acks at ready and after the 60 s watch window, `phases.B.windows[i].result_server`, `.result_admin` and `.result_bob` the three 20 s tick.rate windows (server, admin and bob armed together), `phases.C` the panel and moodle reads, and `phases.Z` the post-run file reads.
- **Load gates and exit**: all 3 verify rows ok, NR version `1.0.0` on the server and both clients; `exit_code` 0, `fault_reasons` empty, `server_error_count` 0.
- **Survival Guide**: on both clients at A and at W the instance is a table with `isVisible` and `getIsVisible` false and its tick box (set from `getCore():getOptionShowSurvivalGuide()`) false. The option is read through the guide's own tick box; the Core value itself was not read by a direct call.
- **Tutorial options**: `showFirstTimeSearchTutorial` and `showFirstAnimalZoneInfo` false in both clients' `options.ini` at ready and after the run (read from the files only).
- **Character info window**: visible on both clients; `layout.ini` untouched.
- **Chat**: no welcome marker phrase in any chat tab or console on either client; bob has one empty tab, admin a second tab holding only the server's two `Safety: "<user>" restore true` lines. This is absence: the baseline presence was not re-measured in this run.
- **Debug flags**: admin `isDebugEnabled` and `getDebug` true; bob false for both, `getLuaDebuggerErrorCount` 0 on both; `UIManager.isShowLuaDebuggerOnError` true on both (the #3319 and #3297 shapes). The debug console's visibility was not read.
- **Mod panel and moodles**: through x191's key-39 route `getIsVisible` goes false, true, false on both clients (`opens` 1, `closes` 1, `keyPresses` 2, `errors` 0); moodle route `own`, 1 column, errors 0, and `stats.renders` rose by 330 on each client over 5 s (`verdicts.MOODLES.observed.<user>.renders1` minus `.renders0`); `probe energy` level 0. Cite the rise, never a count.
- **Options after the run and the welcome**: both `options.ini` still hold all three keys false (155 lines, CRLF), re-saved after the launch (`written_after_launch`, never the mtime); the run's server ini holds a blank `ServerWelcomeMessage`.
- **Game speed and tick rate**: `getGameSpeed()` reads 1 on both clients at A and W (every earlier run had the guide open, which leaves the client at 0). tick.rate windows: server 10.002 / 10.054 / 10.052 ticks per second, admin 60.023 / 60.017 / 60.020, bob 60.011 / 60.011 / 60.008, world minutes per second 1.5961 to 1.5989 on all sides; x183b read the same tps on 42.20.4, and that comparison crosses a build.
- **Unexplained**: bob's ready took 65.9 s (`timeline`, do-not-cite) against admin's 39.8 s; one sample, not explained.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one host, one build. |
| every leaf of `doctor`, `doctor_clean` | pre-run checks | Not readings. |
| every leaf of `timeline`; `server_started_wall`, `session_ready_wall`, `wall_seconds` | driver wall seconds | Wall-clock marks, join timing and the run length. |
| every `steps[i].wall_before` and `steps[i].wall_after` | driver wall seconds | Bus timing, not game state. |
| `host.free_gb_before_boot`, `host.free_gb_after` | 12.7895011901855, 19.8033752441406 | Host state, not a game reading. |
| `phases.A.admin.options_at_ready.mtime`, `phases.A.bob.options_at_ready.mtime`, `phases.Z.options.admin.mtime`, `phases.Z.options.bob.mtime` | epoch seconds | Wall-clock stamps; read only as `written_after_launch`. A wildcard, checked at review under § 4.9. |
| `phases.C.<user>.moodles0.values.stats.renders`, `phases.C.<user>.moodles1.values.stats.renders`, `steps[40].ack.values.stats.renders`, `steps[41].ack.values.stats.renders`, `steps[50].ack.values.stats.renders`, `steps[51].ack.values.stats.renders`, `verdicts.MOODLES.observed.<user>.renders0` and `.renders1` | 9019, 9349, 5868, 6198 | Frame-count dependent raw counts; only the rise over 5 s is cited. |
| every leaf of `phases.B.windows[i].arms` | the arm acks | The harness's acks that the windows were armed, not readings; read `result_server`, `result_admin`, `result_bob`. |
| parents of the keys above, as a whole, and the objects never pointed at as a whole: `phases.B.windows[i]` with its `arms`, `phases.C` and each `phases.C.<user>`, `host`, `timeline[i]`, `steps[i]`; `dialogs.json` as a whole file | — | Each holds the restricted children listed above beside citable ones; cite a child by its path (§ 4.9). |
