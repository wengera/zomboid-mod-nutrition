# `x121-20260911-030023` reading guide

**`x121-20260911-030023/platform-overrides.json`** — produced by
`testing/experiments/x121_overrides.py` at commit `6afcb40` (205.1 s wall, no `error` key,
`server_error_count 0`, `client_lua_error false`; 159 955 bytes, sha256 `49efda95…9fab3e7`,
byte-for-byte identical to the run copy). Slice 12's session 1 and the widest of the seven: nine
phases (M1–M9) on **our own** three experiment mods, every reading taken client-first and paired.
**Skew-free** — driver and artifact in one commit on harness Lua at `5d9633f`, clean, with
`commit`, `harness_lua_commit`, `harness_lua_dirty false`, `doctor_clean true` and
`acceptance_run run-20260911-024303` all in the file. `summary.field_count_ok` is `true` across
**12** `witness.fields` checks.

- **Provenance — the profile.** `testing/profiles/x12-overrides.toml`: `fixture = "default"`,
  `Mods=PZTestKit;TKX_ItemOverride;TKX_Nutrient;TKX_EatHook`, **no `[sandbox]`** (DayLength stays
  the fixture's 4, so a game minute is 3.75 real s), and **three** tier-(a) `[[verify]]` rows, one
  per mod — server `item.script TKX.FibreBar`, server `lua.global TKX_Nutrient.version`, client
  `lua.global TKX_EatHook.version`. All three read `ok=True` (`summary.verify_ok`).
- **Provenance — the mods.** Three `path =` mods from `testing/experiments/`, not workshop items:
  `TKX_ItemOverride` (A), `TKX_Nutrient` (B) and `TKX_EatHook` (C). They are installed only through
  a profile and never sit in the fixture.
- **The two headline readings are per-side facts, not wire facts.** `phases.M2.items` (verdict `verdicts.M2b`; a narrowed
  `item Orange` block keeps vanilla's `hungChange −0.12` and `carbohydrates 16.27` while taking the
  mod's `Calories 400`) and `phases.M4` (the client resolves a B42 `ItemName.json` name; the
  **dedicated server** resolves none at all) are things each side *builds* — nothing is synced, so
  neither belongs in [`platform/mp-model.md`](../../../docs/platform/mp-model.md)'s sync
  tables and both live in [`platform/loader-and-scripts.md#per-key-merge`](../../../docs/platform/loader-and-scripts.md#per-key-merge) and [`platform/mod-anatomy.md#translations`](../../../docs/platform/mod-anatomy.md#translations).
- **`phases.M7.mod_globals.client` is the highest-consequence row and it is incidental.** A mod's
  `media/lua/server/` file executed in the **client's** Lua state, on three independent witnesses
  in one session: (i) `TKX_Nutrient.side` reading **`server` on the client**, the `server/`
  file's write landing over the client-only file's own `client`; (ii) the per-tick counter at
  **58 client / 38 server**; and (iii) `TKX_EatHook.wrapped` **true client-side**. (**Corrected
  2026-09-17, slice 13:** this line had witness (i) inverted; the artifact and
  [`platform/overview.md#two-lua-states`](../../../docs/platform/overview.md#two-lua-states) are right.) The run was not designed to find it, the
  mechanism was **not traced**, and the discriminating probe (one file per `client|server|shared`
  folder, each writing its folder name into a global) is named in [`areas/open-questions.md#x18`](../../../docs/areas/open-questions.md#x18) and handed to
  slice 13.
- **`m8` is a two-arm probe, and the arms are the point.** `+1500` kcal read `T / F / F` and
  `−100` kcal read `F / F / T` for `isIncWeight` / `isIncWeightLot` / `isDecWeight`, identically on
  both sides — the arms slice 11 could not reach. Both arms were read back after a measured
  **8.004 s** wait (`m8.wait_s 8.0`, `m8.cadence`), and `nutrition.set calories −100` was **not
  clamped** (−102.5664 server, −102.10 client).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1`.** One session, build 42.20.4, fixture `default`, three mods we wrote, one character, one machine. Per-arm counts are smaller still: one item for the merge rule, one eat for `OnEat`, one transmit per direction. |
| `phases.M4.text.client.*` / `phases.M4.text.server.*` — every `text.get` reading of this run | four keys, all `miss: true` | **Wrong key form, and no positive control.** The probe asked the **prefixed** form `ItemName_<type>`, and the vanilla control `ItemName_Base.Apple` missed too — so this run cannot separate "the key form is wrong" from "the route does not reach item names". The graded reading is `x124-20260911-035819` → `phases.O5`, which asked the **bare** form as well and still missed on both sides (nine keys across the two runs), with slice 10's client-side `IGUI_` hit (`291f977`) as the out-of-run control. The rule is [`platform/mod-anatomy.md#translations`](../../../docs/platform/mod-anatomy.md#translations)'s. |
| `verdicts.M7`, and P9's **server → client** item-modData direction | `as_predicted`, `TKX_fibre` true on both sides | **No hop was exercised.** Both sides already held `TKX_fibre` when the phase opened and `observed.itemWrites_server` is **0** — the verdict grades a *state*, not a crossing. The server→client **item**-modData direction is un-run and is named as slice 13's probe ([`areas/open-questions.md#x14`](../../../docs/areas/open-questions.md#x14)). |
| `verdicts.M6.observed.join`, read as a route — "the join handshake carried it" | client keys at `client_since_ready 2.785` already include `TKX_fibre` | **The carrier was not measured.** The client held the key before the phase's transmit; nothing traced which packet put it there, and no control excluded the mod's own client-side write (its `server/` file runs client-side — see `phases.M7`). Cite `verdicts.M6.observed.after` and `client_only_after_less_rewrites` (`[]`) for the transmit's wipe-and-replace, and nothing at all for the earlier arrival. |
| `verdicts.M6`'s **verdict string** | `trivial` | It grades **P8's premise** (a key present server-side only), which failed — not the direction. The measured statement is in `observed.after`: the client's table became the server's once `TKX_fibre_client`, the key the client's own mod rewrites every tick, is set aside. |
| `getActualWeightUnmodded` in `phases.M4.items.*.witness.*.fields` | `0` on both sides | **Not a weight fact.** `Food.getActualWeightUnmodded` returns 0 whenever `getDisplayName()` is not the vanilla name — it is slice 09's display-name guard, read here only as part of the `witness.fields` set. Weight facts are `getActualWeight` and the `m8` flags. |
| `phases.M3` / `verdicts.M3`, read as a general ordering rule | `getCalories 111`, verdict `falsified` | **A reading, not a rule.** 111 is the body of the mod *earlier* in `Mods=`, which kills "`Mods=`-last wins" and nothing else: four rival orderings survive it. The settled rule — sorted by the stored script path (C), `Mods=`-independent (M), last body wins per key (M) — is `x125-20260911-042055` and [`platform/loader-and-scripts.md#sorted-replay`](../../../docs/platform/loader-and-scripts.md#sorted-replay). |
| the `text.get` **null guard** (`5d9633f`), read as "confirmed" | 0 replies carrying `null: true` | **Untriggered, not confirmed.** No key in this run (or in `x124`) returned a Java null, so the guard's branch never executed. It is code that has not yet been exercised. |
