# `x125-20260911-042055` reading guide

**`x125-20260911-042055/platform-order2.json`** — produced by
`testing/experiments/x125_order2.py` at commit `6549e4a` (75.7 s wall, no `error` key,
`server_error_count 0`, `client_lua_error false`; 67 727 bytes, sha256 `3b874318…a47695e`,
byte-for-byte identical to the run copy). Slice 12's session 5, the **discriminator** session 4
earned: the same three mod bodies in a different `Mods=` order, chosen so that the three surviving
rules name three different numbers. **Skew-free** — driver and artifact in one commit on harness Lua
at `5d9633f`, clean, `doctor_clean true`, `acceptance_run run-20260911-041437`.

- **Provenance — the profile.** `testing/profiles/x12-order2.toml`:
  `Mods=PZTestKit;TKX_ItemOverride;TKX_ZWatermelon;TKX_EatHook` — `TKX_ZWatermelon` in the **middle**
  of `Mods=` and **last** alphabetically — `fixture = "default"`, **no `[sandbox]`**, the same two
  tier-(a) rows as `x12-order`, both `ok=True`, with mod F ungated and gated at tier (c) by the
  driver (`f_tier_c`).
- **The design, stated in advance and in the file.** 999 ⇒ the body that sorts last; 111 ⇒
  first-in-`Mods=` (a reverse-`Mods=` replay); 777 ⇒ `Mods=`-last (falsified twice already, so a 777
  would have reopened the whole line). `candidates`, `prior` and `still_confounded` record all of it
  before the reading.
- **The reading.** `Base.Watermelon` `getCalories` **999** on all three routes, the four other macro
  keys invariant on both sides (`summary.O1_watermelon_calories`, `verdicts.P20` `as_predicted`).
  The loader's own `loading` lines still walk `Mods=` (server 94/97/99; client twice, 84/87/89 and
  168/171/173) — `summary.loading_lines.matches_mods_order` is `true`, which is the point: the
  announce order and the replay order are **different orders**.
- **What is settled, and how to word it.** "Script bodies are replayed in a **sorted** order that is
  **`Mods=`-independent**, with **last body wins per key**." The sort key is **C**, from the jar:
  `ScriptManager$38.compare @67-@71 L1497` is `String.compareTo` on the full **stored path**
  strings, and `ScriptManager.searchFolders @93-@114 L1208-L1209` stores
  `getRelativeFile(uri, abs).toLowerCase(ENGLISH)` relative to the version dir or `common/` — **no
  mod component in the key**; `L1500-L1502` sorts the vanilla and mod lists separately and
  `addAll(vanilla, mods)`, so vanilla is always first. Two rivals die on the jar alone: a tie plus a
  stable sort would have given `Mods=` order (777), and file size (2430 / 1293 / 640) would have
  given 111 or 777.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one build, the same three mod bodies as session 4 in a second permutation. |
| `summary.O1_body_that_won.*.means`, `summary.O1_means` and `verdicts.P20.observed.means` | "ALPHABETICAL-LAST wins" / "the body replayed last is the one whose id sorts last" | **They name the wrong key.** Measurement cannot separate sort-by-**id** from sort-by-**folder name**, by **script path** or by **`mod.info` display name** — all four sort identically in every boot this library ran. The jar names the key and it is the **stored script path** (C, above). The id-vs-path boot (a mod whose id sorts last while its script file sorts first) is the named check, handed to slice 13. |
| "`Mods=`-independent, n = 3 boots" | — | The independence clause rests on **two permutations of the same bodies** (the winner held `Mods=` slots 1 and 2) plus `x121`'s independent kills. Write "n = 2 permutations + x121". |
| `verdicts.O2` / the script-path grep, read as a replay order | `trivial` | Same as `x124`: the engine prints no script-path lines. The citable form is the negative — "no script path is printed at default verbosity", direct grep, n = 3 sessions. |
| `summary.O3_foodByModule`, read as a fourth redefinition boot | `Base` 722 / `TKX` 3 | The baseline is `exp05-20260910-084109`, not a redefinition boot. Write "722 in all three redefinition boots against the `exp05` baseline". |
| `testing/profiles/x12-order.toml:11` ("999 ⇒ alphabetical-by-id") and `x12-overrides.toml:2` ("`Mods=` order is LOAD order, and it is load-bearing here") | — | **Frozen with their artifacts and falsified for script bodies.** They are the predictions the runs were measured against; the profiles are not edited. Cite this run and [`platform/loader-and-scripts.md#sorted-replay`](../../../docs/platform/loader-and-scripts.md#sorted-replay), never the comments. [`testing/profiles/README.md`](../../profiles/README.md) says so on both rows. |
| `classify()`'s file/mod-id split, if this driver is copied | — | Frozen-driver notes: `x125_order2.py` ~:688 admits a mod-id-only line when the line also carries a `media/scripts` path (`is_file = bool(m) or in_scripts`) — it did not fire here; `grep_numbered` ~:427 classifies a 200-character truncation as a hit; and the re-classification of `x124`'s hits (0 true file hits) is true but is recorded in **no** artifact key. |
