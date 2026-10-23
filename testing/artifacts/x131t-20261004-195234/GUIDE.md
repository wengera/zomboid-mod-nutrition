# `x131t-20261004-195234` reading guide

**`x131t-20261004-195234/traits.json`** — produced by `testing/experiments/x131_traits.py` at commit
`de0525e` with the harness Lua clean (`harness_lua_dirty` false) and `doctor_clean` true. Plan 1 Task 14:
**X4** in one live session of one boot, profile `x13-traits` (PZTestKit and `TKX_TraitProbe`, the
fixture's own sandbox). Both `[[verify]]` rows passed (the probe's `version` 1, and
`TKX_TraitProbe_Traits.probe` resolved to `tkx:probe` on the server), no mod was missing,
`server_error_count` 0, `client_lua_error` false, client quit and server stop rc 0; 171.6 s wall.
sha256 `e58270c0…1db5186` (121 930 bytes), byte-for-byte identical to its run copy. **Skew-free**: the
driver was written before the run and not edited after it.

How to read it. `trials[0]`–`trials[5]` are the vanilla-trait trials in run order A1, A2, A1, A2, A1, A2:
A1 is `trait.set admin HeartyAppetite add` with no push, A2 is `trait.set admin LightEater add` then
`trait.push admin 2`. Each trial holds `set` (the server step, with `epoch_ms_before` and `epoch_ms_after`,
the python bracket in epoch ms), A2's `push` and `push_wall` (the server's `getTimestampMs` at the push),
`add_poll` and `remove_poll` (the client `stats.get` reads: each row's `snap_wall` is the client's own
`getTimestampMs` at the snapshot and `traitList` its list), and `server_after_add` /
`server_after_remove` (the server's own `stats.get`). Both processes run on one host and share its
clock, so a client `snap_wall` minus a server-side stamp is a latency. The server executes a command and
writes its acknowledgement in the same call, and the driver sees the acknowledgement at most about
0.25 s later, so a write lies in the last 0.25 s of its `set` bracket; the server picked commands up
0.26–2.02 s after they were sent (it polls its command file every 20 ticks). `phases.A3` is the
registered trait: `route_probe` (the server's `ResourceLocation.of` global and the client's registry
object), the grant (`moddata.set admin TKX_grant TKX:Probe`), `grants_polls`, the push key, `add_poll`,
`server_after_add`, `lastId`, then the removal. An empty Lua list serialises as `{}`, not `[]`.

- **A1, no push** (`trials[0]`, `[2]`, `[4]`): the server's list held `heartyappetite` after each add
  (the first non-empty trait list any run has read), and the client's first read holding it came 0.511,
  0.562 and 0.417 s after the add's acknowledgement was seen; the read before it, where there was one,
  came 0.010 and 0.062 s after. Removal, no push: the first client read without it came 0.469, 0.527 and
  1.141 s after the removal's acknowledgement, and in `trials[4]` the client still held it at 0.639 s.
- **A2, push** (`trials[1]`, `[3]`, `[5]`): the server ran the push 1.21, 1.36 and 1.56 s after the
  add's acknowledgement, and the client's first read after the push, 0.18–0.37 s after its stamp,
  already held `lighteater` each time. The push and the experience packet are not separated.
- **A3, registered trait**: `ResourceLocation.of` is a function on the server, so the probe's resolver
  took the `ResourceLocation` branch; `grants` read 1 at the first poll, 1.26 s after the grant's
  acknowledgement, and `lastId` `TKX:Probe`. Server and client lists both read `probe` (the id's path,
  without `tkx:`), the client's first read holding it 3.72 s after the grant's acknowledgement (the
  server's 2 s pickup of the push key sat between). The removal (`lastId` `-TKX:Probe`, `removes` 1)
  left both lists empty.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` session**, one fixture, one client, one build; three trials per vanilla arm, one registered-trait trial. |
| `verdicts.A1.verdict`, `summary.verdicts.A1` | `falsified` | Graded on arrivals measured from the start of the add's bracket, which includes the server's command pickup (up to 1.76 s in `trials[2]`), not the write. Read `trials[n].add_poll.rows` against `trials[n].set.epoch_ms_after`. |
| `phases.A1A2_summary.A2.add_hit_ms_from_push`, `summary.A2_from_push`, `trials[n].add_poll.hit_ms_from_push` for A2 | 177–371 ms | The first client read after each push already held the trait and the push came 1.2–1.6 s after the write, so the number bounds when the list was present, not when the push arrived. |
| `phases.A1A2_summary.A1.removed`, `phases.A1A2_summary.A2.removed`, `trials[n].remove_poll.arrived`, `phases.A3.remove_poll.arrived`, `verdicts.A3.observed.removed` | `false` | The empty list serialises as `{}`, which the driver's name test reads as no answer rather than as absent, so a removal never registered as arrived. Read `trials[n].remove_poll.rows`. |
| `phases.A1A2_summary.A1.pre_client_has`, `phases.A1A2_summary.A2.pre_client_has`, `trials[n].pre_client_has` | `null` | The same `{}` serialisation: the client's list was empty before every add (`trials[n].pre_client.traitList`). |
