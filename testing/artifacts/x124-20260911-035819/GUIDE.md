# `x124-20260911-035819` reading guide

**`x124-20260911-035819/platform-order.json`** — produced by `testing/experiments/x124_order.py`
at commit `f6c336e` (81.7 s wall, no `error` key, `server_error_count 0`, `client_lua_error false`;
63 642 bytes, sha256 `097bfb10…d190c9a`, byte-for-byte identical to the run copy). Slice 12's
session 4, added by the controller after session 1 read a number **two** rules predicted: which
`item` body lands last when several mods redefine the same item, and — on the way past — whether
`getText` reaches an item name on either side. **Skew-free** — driver and artifact in one commit on
harness Lua at `5d9633f`, clean, `doctor_clean true`, `acceptance_run run-20260911-035203`.

- **Provenance — the profile.** `testing/profiles/x12-order.toml`: `fixture = "default"`,
  `Mods=PZTestKit;TKX_ZWatermelon;TKX_ItemOverride;TKX_EatHook`, **no `[sandbox]`**, two tier-(a)
  `[[verify]]` rows (server `item.script TKX.FibreBar`, client `lua.global TKX_EatHook.version`),
  both `ok=True`. `TKX_ZWatermelon` (mod F) is **ungated on purpose** — it ships no Lua and no new
  item, and the obvious `item.script Base.Watermelon` row would pass with the mod absent because
  vanilla defines Watermelon. It is gated at **tier (c)** instead, recorded in `f_tier_c`: folder
  copied, `mods_not_found` empty on both sides, `loading TKX_ZWatermelon` at server log 94.
- **The reading.** `Base.Watermelon` `getCalories` **999** on all three routes — client
  `witness.fields`, server `item.get`, server `witness.fields` — with the four other macro keys
  invariant on both sides (`summary.O1_watermelon_calories`, `summary.O1_invariant_ok`). The
  loader's own `loading <id>` lines still walk `Mods=` order (94/96/99).
- **What 999 kills, and what it does not.** `Mods=`-last-wins is falsified here and was already
  falsified in `x121` (n = 2). What 999 **cannot** separate is alphabetical-by-id, by folder name,
  by script path and first-in-`Mods=`-wins: `TKX_ZWatermelon` is simultaneously alphabetically last
  and `Mods=`-first, so all four predict it. The discriminator is session 5
  (`x125-20260911-042055`).
- **`phases.O5` is the graded `text.get` reading of the slice.** Bare `Base.Apple`,
  `TKX.FibreBarJson`, `TKX.FibreBarNamed` and the prefixed controls all returned a genuine miss
  (`miss: true`, `text == key`, no `null`, no `error`) on **both** sides, while `x121` read
  `getDisplayName() == "TKX Fibre Bar Json"` off the instance for the same item. A dedicated
  server's `text.get` **answers** — the route exists there; it is simply not the route to an item
  name.
- **Three empty-tail `overrides` lines per Lua state** (server 95/97/100, client 85/87/90 and
  169/171/174) — one per mod, all three of them `common/`-less, with `PZTestKit` (also
  `common/`-less, loaded first) printing none. The mechanism is slice 11's re-reading
  (`td3-20260911-001948`; `ZomboidFileSystem.loadMod` L754-L755 / L769-L770, `getRelativeFile`
  returning `""`), not slice 09's first sighting.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one build, three mod bodies, one item. |
| `summary.O1_means` and `summary.O1_body_that_won.{client,server}.means` | "replay is ALPHABETICAL BY ID with per-key last-wins; `Mods=` position is irrelevant to which body lands last" | **The driver's own over-reading, frozen in the file.** Four rival rules predict 999 in this `Mods=` order (alphabetical by id, by folder name, by script path, and first-in-`Mods=`-wins), so this run selects none of them. The settled rule is "**sorted by the stored script path** (C), `Mods=`-independent (M, two permutations plus `x121`), last body wins per key (M)" — `x125-20260911-042055` and [`platform/loader-and-scripts.md#sorted-replay`](../../../docs/platform/loader-and-scripts.md#sorted-replay). Do not write "question 7 settled" from this file. |
| `summary.O2_script_file_order` / `summary.O2_script_file_hits`, read as a **replay** order | `["tkx_zwatermelon"]`; server 6 / client 8 hits | **Those are loader and `NoSuchFileException` lines that merely contain the mod id**, not script-path lines. `verdicts.O2` is `unmeasured` for that reason (its honest grade is `trivial` — zero true script-path lines), and the "8 hits" figure is a *reading-time* re-grep that includes the harness's own echoes; the boot-time count is 6. The one citable form is the negative: **the engine prints no script path at default verbosity** (direct grep, n = 3 sessions). |
| any `phases.O5` reply, read as evidence about the **`ItemName` table** | nine keys, all `miss: true` across `x121` + `x124` | It is evidence about the **`getText` route**, not about whether the table is populated: `x121` read the JSON display name off the *instance* in the same build. And this run carries **no in-run positive control** — every key missed — so soundness rests on slice 10's client-side `IGUI_SS_BARTITLE_HAPPY` hit (`291f977`), a different session on an earlier harness shape. |
| the empty-tail `overrides` lines, read as truncation or as a real collision | `mod "TKX_ZWatermelon" overrides ` and two more | **Neither.** They are the known empty-tail line: a `common/`-less mod's non-directory branch in `searchFolders` with `getRelativeFile` returning `""`. Cite it as a second and third instance, with slice 11's mechanism. |
| `verdicts.P19` | `falsified` | The verdict word grades **the plan's prediction** that `getText` would reach the name, not the reading. The reading is `phases.O5` and it is a clean, bounded negative on both sides. |
