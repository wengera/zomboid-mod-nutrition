# `td2-20260910-231655` reading guide

**`td2-20260910-231655/teardown-simplestatus.json`** — produced by
`testing/experiments/td2_simplestatus.py` at commit `7453580` (167.8 s wall, no `error` key,
`server_error_count 0`, `client_lua_error false`, `client_quit rc=0`; 105 267 bytes, sha256
`a91b19eecd7c676bf955f3867b50d4f15f4bfbc6cb4275561808745de7796298`). Slice 10's teardown
session, and the **read** side of the pair: a pure client-UI mod on a real dedicated server with
a real client, comparing the five server-owned nutrition numbers the mod draws on **both** sides
at six snapshots. **Skew-free**: driver and artifact landed in one commit on harness Lua at
`291f977`, clean in the working tree, which the file records for itself (`commit`,
`harness_lua_commit`, `harness_lua_dirty false`, `doctor_clean true`). **It is the first
artifact written under the widened float rendering** — see § Script/artifact skew, "a skew of a
third kind": every float here is `tostring(v)` (`Double.toString`, an exact round trip) rather
than `%.6f`, verified on this file's own bytes at **1 225 JSON number tokens** (871 non-integral,
354 integer) / 0 non-round-tripping — the **1 292** first recorded for this run has no recorded
provenance and does not reproduce as any census of the file (`\d+` gives 2 339) — cite 1 225 —
and that is why its weight rows can carry a bit-level claim when no earlier artifact's can.

- **Provenance — the profile.** `testing/profiles/teardown-simplestatus.toml`:
  `fixture = "default"`, `[[mods]] id = "PZTestKit"` then `[[mods]] id = "simpleStatus",
  workshop_id = "2867431511"`, **no `[sandbox]` block**, and **one** `[[verify]]` probe — client
  `text.get IGUI_SS_BARTITLE_HAPPY`, expecting `"Happiness"`. The profile was committed at
  `a42c8b4` with `verify = []` (tier (b): no tier-(a) probe existed **on the shipped bus**); the
  `text.get` reader and the row both landed in `291f977`, moving the tier to **(a)**. Its
  acceptance run is named in `acceptance_run`: **`run-20260910-230752`** (`RESULT: PASS`, 95 s)
  — that run's `report.json` is *not* committed here, and the session re-asked the same probe
  itself, so cite `verify[0]` from this file and treat the acceptance run id as provenance.
- **Provenance — the mod.** Workshop item `2867431511`, folder `SimpleStatus`, declared id
  `simpleStatus` (a **case-only** drift), live version folder `42.16/` of four (`42.16`,
  `42.15`, `42.14`, `42`) beside an empty `common/` and a root-level B41 `media/`; no `author=`
  in any `mod.info`, no `require=`, no sandbox options, **no `media/scripts/` anywhere**;
  1 132 005 B, every file stamped 2026-08-12 00:02. The workshop tree is read-only to the
  harness.
- **How to read the cross-side rows — they are TIMING readings, not equality tests.** The
  server's nutrition store decays continuously while the client's copy steps only on the 1 Hz
  `PlayerStatsPacket`, and the two sides are read ~1–3 s apart, so `grades[]` grades each
  snapshot against a band computed from **that snapshot's own signed read skew**
  (`delta_min` / `delta_max`, client half read first) and records `gap_client_minus_server`,
  `band`, `in_band` and `residual` per field. **Never quote a gap without its snapshot's skew**;
  and `in_band` is the verdict — "equal" is not what a healthy mirror looks like here. Weight's
  band is **negative** and is built from a per-snapshot rate (`weight_model.arm` / `mult` /
  `ratio`), widened by one float32 ulp.
- **`graded` is not `in_band`.** Two of the six snapshots (`t0`, `t2+0s`) sit inside a write's
  push window and are **ungraded by rule** (`tolerance.settle_rule`, 1.5 s) — they are arrival
  readings, and `arrivals[]` is where the latency actually lives (0.766 s / 0.765 s). Both fell
  inside their bands anyway, which is a bonus, not the grade. `summary.graded_snapshots` names
  the four that were graded.
- **The wipe is the phase-2 headline** (`wipe_reading`): a key planted on the **server** only
  vanished after one client `transmitModData()`, while the client's key and `hotbar` arrived and
  `server_census_equals_client` went `true`. `baseline_difference_set` is **empty**, which is
  why the planted key was needed at all — without it the run would have proved nothing in that
  direction.
- **The appendix is two PASS-1 follow-ups, not simpleStatus findings.** `appendix.A1` is the
  vanilla display-name control (`Base.FruitSaladClay` vs `Base.Steak`, both sides);
  `appendix.A2` is the client-copy tick check on a server-pinned `Base.Steak`. Cite them against
  [`facts/food-item-model.md#open`](../../../docs/facts/food-item-model.md#open) and [`platform/mp-model.md#what-a-client-copy-is`](../../../docs/platform/mp-model.md#what-a-client-copy-is),
  never against simpleStatus, which owns no item and reads no item field.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1`.** One session, build 42.20.4, fixture `default`, one mod, one character, one machine. Every gap landed **inside** its band, including the two ungraded snapshots, so the falsifier was never approached: the rule is validated as *consistent* with a 1 Hz push, not as *tight*. The weight arm was exercised on the **gain** side only (the loss arm and its opposite-signed band are untested), the ×2 arm at carbs/lipids > 400 was never entered (this run used carbs 800, the ×3 arm), and `isDead` / `isGodMod` were `false` throughout, so neither `Nutrition.update` gate was seen in its blocking state. |
| `grades[].flags*`, as an answer to body-stats open question 10 | flags agree on both sides at all six snapshots | Both sides' `traitList` came back **empty** (`grades[].traits`), so the reading is "**no disagreement on a character with no weight-band traits**". The flag prediction depends on both sides computing the same `gainThreshold`, which depends on `hasTrait(WEIGHT_GAIN)` / `hasTrait(WEIGHT_LOSS)` agreeing — untested here, and that is exactly open question 10. |
| `appendix.A2.container`, full strings | `ItemContainer:[type:none, parent:IsoPlayer{ Name:null, ID:5 }]` (client) against `ID:1` (server) | **Presence and within-side stability only.** `ItemContainer.toString() @0-@16 L3513` is `getType() + String.valueOf(getParent())` and the parent's `IsoObject.toString()` ends at `@42 L5982` in a per-JVM identity hash, so the two sides' strings differ **by construction**. Comparing them across sides reads as a desync and is not one; the leading type token is the comparable part. |
| `appendix.A1`, as an answer to LTP's B41-layout hypothesis | hypothesis "no translation entry" confirmed inside vanilla | It separates "no `ItemName.json` entry" from a mod-specific failure and no further: whether 42.20.4 ever loads a **B41-layout `ItemName_EN.txt`** stays open, because separating it needs an `ItemName.json` added to a mod tree — a write under the read-only workshop folder. `n = 1` for the absent-name case. |
| `moddata_keys` | the three probes joined by ` / ` for the reader | A **display** string, not a bus token — the three probes were sent separately, and `notes[0]` says so. The `global:`-scoped one is **non-discriminating in both directions** and is metadata, not a control: `ModData.getOrCreate` creates the table for the census itself, and the mod's retired server half only ever created it empty. |
| `folder_check` | `server_mods ["PZTestKit", "simpleStatus"]` | Run metadata, **not** an answer to the folder→id rename question: on NTFS `simpleStatus` and `SimpleStatus` are the same directory, and no profile can reach `mods.install`'s name-keeping branch at all. [`platform/harness.md#profiles`](../../../docs/platform/harness.md#profiles) stays "first half M, second half C". |
| `empirical_slope.pairs[0..2]` | 0.307242 / 0.235916 / 0.311225 kcal/real-s | The three **short** windows (6–11 s) scatter ±20 %, because ~6 s at 0.25 kcal/s is ~1.5 kcal against a quantised float32 store. Quote `empirical_slope.longest` (38.947 s, **0.250296**) against the derived 0.2560552 — ratio 0.9775 — which is the reading the bands were justified with. |
| `snapshots[].{client,server}.census_player`, quoted as a standing baseline | server 4 / client 5 | True only **after ~30 s of session**. The server's copy is **empty at join** (`keyCount 0` at 79.194 / 91.074 / 97.411 s, then 4 at 108.773 s): the four vanilla fitness/strength keys are written server-side lazily. Anything comparing censuses at join sees **server 0 / client 5** — which also corrects the pass-1 player-scope baseline recorded on `td1-20260910-192457`. |
| `float_format`, or any float here compared against an older artifact's | `tostring(v)` | This file renders non-integral numbers exactly; **every artifact before `291f977` renders them at six decimals**. A diff across that boundary shows a rendering change, never a measurement one — and the `±Inf → null` behaviour the same commit added is **C (inferred), not measured**. |
| `mod_log_lines_server`, read as the server's whole mod-log census | five lines: `loading simpleStatus` and four `overrides` lines (`ch`, `cn`, `de`, `en`) | **A SATURATED grep, not an exhaustive one.** The driver called `grep_file(server.log_path, MOD_RX, limit=5)` and `grep_file` **breaks** at its limit, so a result of exactly `limit` means the log had at least that many and the reader stopped. The server log itself holds **18** matching lines: `loading simpleStatus` (`:94`), **13** `overrides` lines at `:95-107` — one per shipped language, `ch` `cn` `de` `en` `es` `fr` `hu` `it` `ko` `pl` `pt` `ru` `tr` — and four `NoSuchFileException` lines for the `AnimSets` / `actiongroups` folders the mod does not ship (`:1278`, `:1299`, `:1320`, `:1341`, baseline noise). Quote **13**, from the log; the conclusion the four were used for (the mod shadows only its own JSONs, no key collision) is unchanged. Re-read 2026-09-11; the general rule is in [`platform/lessons.md#testing-discipline`](../../../docs/platform/lessons.md#testing-discipline). |
| `summary.client_copy_ticked` | `true` | **It names the wrong question.** What `appendix.A2` measured is that the two VALUES moved and stayed bit-identical across a 0.5 s read offset; whether the client's copy *simulates* is not something two agreeing reads can settle. Resolved elsewhere and the other way: below `Food.update`'s 1.6 cooking gate the copy is **bit-frozen** (`td3-20260911-001948`, `carrier`), and `Food.update`'s cooking-branch `sendItemStats` is the carrier that moved this one. Cite the two readings and the gate, never this boolean. |
