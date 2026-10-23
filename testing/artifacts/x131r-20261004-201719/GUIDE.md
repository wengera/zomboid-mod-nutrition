# `x131r-20261004-201719` reading guide

**`x131r-20261004-201719/ss_track.json`** — produced by `testing/experiments/x131_ss_track.py` at commit
`1ae3425` with the harness Lua clean (`harness_lua_dirty` false) and `doctor_clean` true. Plan 1 Task 15:
**X44** in one live session of one boot, profile `x13-ssread` (PZTestKit, `simpleStatus` from workshop
`2867431511`, its live `42.20/` tree read 2026-10-04, then `TKX_SSRead`; the fixture's own sandbox).
Both `[[verify]]` rows passed (`text.get IGUI_SS_BARTITLE_HAPPY` answered "Happiness" on the client;
`TKX_SS.calls` resolved), no mod was missing, `server_error_count` 0, `client_lua_error` false, client
quit and server stop rc 0; 97.8 s wall. sha256 `f0e58bf6…d19eb92d` (26 408 bytes), byte-for-byte identical to its run copy. **Skew-free**: the driver was written before the run and not edited after it.

How to read it. `phases.L` is the wrap check: `TKX_SS.calls` read 11, then 26 about 2.5 s later, and
209 at the end (`phases.E`); `phases.L.bars` holds all four macro bars' text at the start. Every other
row is a client triplet: `bar_before` (`lua.global TKX_SS.<macro>`, the bar's text as the probe copied it
from `self.barInfo`), `store` (client `stats.get`'s `calories` or `proteins`, with `store_wall` the
client's `getTimestampMs`), `bar_after` (the same global again); `match` is true when either bar read
equals `round(store, 1)`. `phases.C0.rows` are three pre-write triplets; `phases.AC` writes
`nutrition.set admin calories 1500` and `phases.AP` `proteins 120` on the server (`set` with its python
bracket, `readback` the server's `nutrition.get`), then triplets for 6 s from the acknowledgement;
`t_from_ack_ms` is the store read's client stamp less the acknowledgement's python stamp (one host,
one clock). Each triplet took about 1.5 s of client bus round trips.

- **Control.** Three of three pre-write triplets matched (bar 797.9 → store 797.63 → bar 797.6, and so on):
  the read before the store carried the previous push's value, the read after it the store's.
- **Calories 1500.** The server read back 1499.67; the first bar read after the write (1.77 s after
  the acknowledgement) read 1499.7, the store 1499.4 at 2.18 s, the next bar 1499.4; four of four
  triplets matched as the store drained.
- **Proteins 120.** The server read back 119.97; the first bar read (2.27 s) read `120(x1.5)` — the
  mod's own multiplier caption appended — and five of five triplets matched, the bar following the store
  to 119.9.
- The arrival lag is **not resolved**: both the store and the bar already held the written value at the
  first read after each write.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one client, one build; calories and proteins written, carbohydrates and lipids only read. |
| `phases.AC.tagged`, `phases.AP.tagged`, `verdicts.AC.observed.tagged`, `verdicts.AP.observed.tagged` | `+1s`, `+2s`, `+4s` | Each triplet took about 1.5 s, so no read fell near +1 s: the `+1s` and `+2s` tags name the same triplet at 2.18 s (calories) and 2.76 s (proteins). Read `phases.<arm>.rows[n].t_from_ack_ms`. |
| `phases.AC.store_first`, `phases.AC.bar_first_ms`, `phases.AP.store_first`, `phases.AP.bar_first_ms`, `summary.AC`, `summary.AP`, `verdicts.AC.observed.store_first_ms`, `verdicts.AC.observed.bar_first_ms`, `verdicts.AP.observed.store_first_ms`, `verdicts.AP.observed.bar_first_ms` | 1774–2760 ms | Both had already changed at the first read after the write, and the two are stamped on different clocks (the bar on the python read's end, the store on the client's snapshot), so neither is an arrival and their difference is not a lag. |
| `constants.POLL_S` | 0.5 | The requested spacing; the triplets came about 1.5 s apart. |
