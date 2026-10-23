# `td1b-20260910-202029` reading guide

**`td1b-20260910-202029/teardown-longtermpreservation4220-followup.json`** — produced by
`testing/experiments/td1b_longtermpreservation4220.py` at commit `38ecf23` (96.9 s wall, no
`error` key, `server_error_count 0`, `client_quit rc=0`; 41 075 bytes, sha256
`a69f3c89315fcf455f452f03f4f964f83db5ddfc1a07207b3abc6cf77af395e0`). **Skew-free**: driver,
artifact and the harness it ran on (`903ccaa`) are all pinned in the file itself (`commit`,
`harness_lua_commit`, `harness_lua_dirty false`, `doctor_clean true`). A five-question follow-up
to the run above, on the same profile and the same mod, commissioned by that run's review — and
the first artifact anywhere carrying `lastCookMinute` and an `item.set` ack's `gameMinute`.

- **What it adds that `td1` could not answer.** (1) `getDisplayName` read **directly** on both
  sides (`answers.4.1_*`, `weight_reads[0]` / `[2]`); (2) a **vanilla control**, `Base.Steak`,
  spawned into the same inventory and read with the same six getters (`answers.4.2_*`,
  `weight_reads[1]` / `[3]`); (3) a deliberate second server-to-client push on the already-cooked
  item with the client's `getThirstChange` read either side of it (`thirst_hops`); (4) a
  **vanilla item's** modData census on both sides (`censuses[0]`); (5) two null controls — the
  cook run with `chef` **unset** (`xp_delta` **0**, against `td1`'s 2.5) and `lastCookMinute`
  read after the transition (`item_get_after_cook.lastCookMinute` −1).
- **The bonus finding, and it is the load-bearing one.** `steps[set_lastCookMinute]` arrives with
  **`cooked` true** and **`before_lastCookMinute` 23** — flat keys on the step row itself; the
  nested `before` object one level deeper (`…ack.before`) carries the same two as `cooked` and
  `lastCookMinute`, and either path reads the same. The server's own tick had already
  stamped a minute and transitioned, 907 ms before our write landed — a figure that comes from the
  **server console** under the gitignored `testing/runs/td1b-20260910-202029/`, not from this
  file, which carries the ack's wall bracket (`wall_before 70.888` / `wall_after 72.4`) instead.
  `heat > 1.6` plus `cookingTime > minutesToCook` suffice; the minute gate
  opens on its own within one game minute. This is what settles `td1`'s withdrawn causal claim by
  reproduction rather than by argument.
- **Provenance — the mod and the profile** are the same as the block above (item `3774789651`,
  profile `teardown-longtermpreservation4220.toml`, `verify` 3/3 `ok=True`), and both RCON spawns
  are recorded in both shapes: `rcon["Skittles.CuredPork"].ok true` with an **empty** body and
  `rcon["Base.Steak"].ok true` with `"Item Base.Steak Added in admin's inventory."` — the pair
  that shows why an empty body is not a failure.
- **World changes:** two `additem` spawns and one cook transition, in this run's copy of the
  fixture. No `settimespeed`, no sandbox write, `chef` deliberately unset. Nothing to restore.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `censuses[].server.keys` | `[]` on the vanilla item | **A driver normalisation, not the wire's shape.** The empty census came back over the bus as `{}` (the harness-wide empty-table shape `exp08-20260910-152944` measured); the driver rendered it as a JSON list. Test emptiness with **`keyCount`**, which is `0` here and is what the readings quote; do not cite this file as evidence about the bus's empty-collection shape. |
| `answers.4.2_vanilla_raw` / `4.2_vanilla_after` | `Base.Steak` resolves its display name on both sides; `Skittles.CuredPork` does not | Supports exactly two claims — "not dedicated-server-wide" and "this item's name does not resolve" — and **not** "mod item names do not resolve". `n = 2`, and the two items differ in **two** ways at once: the mod item has no `DisplayName =` line *and* relies on a mod translation table. The discriminating control (an item that carries `DisplayName =`, or a vanilla item that does not) cannot come from this mod — its only two `DisplayName =` lines sit inside a commented-out block — so the cause stays **C** and open. |
| `cook_poll` | one row | The transition had already happened before the first poll fired, so the poll loop measured **nothing** about timing. The server console is what dated the transition, in this run as in `td1`; the bus still cannot time a server-side tick on its own. |
| `steps[set_lastCookMinute]` | the write is still sent | Kept from the `td1` sequence and, on this run, sent **after** the transition — a step the driver no longer needs. A future driver testing the *gate* must send it **before** the `cookingTime` pin; as recorded here it proves the flip is unnecessary and nothing else. |
| every float | rounded to six decimals | Same instrument limit as the block above: the bus quantises, so nothing in this file supports a bit-for-bit claim. `getActualWeight` 0 vs 0.35 and `getThirstChange` 0.1 vs 0.05 are whole-value differences, far above it. |
| everything measured here, as a population | — | **`n = 1` per question, `n = 2` for the item pair.** One session, one fixture, one mod item, one vanilla control. The five answers are each a single reading; three of them (the display-name pair, the thirst hop, the XP null control) are second readings of something `td1` saw, which is exactly why they are worth more than their count. |
