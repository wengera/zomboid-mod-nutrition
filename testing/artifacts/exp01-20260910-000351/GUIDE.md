# `exp01-20260910-000351` reading guide

**`exp01-20260910-000351/eat-smoke.json`** — produced by `testing/experiments/s01_eat_smoke.py`
at commit `21af6d1`. Since `eb123fd` the script (and the harness command it drives) write two
things this file therefore lacks:

- A **second, post-teardown save**. The current script saves once before teardown and again
  after it, so the committed JSON carries the `client_quit` / `server_stopped` timeline marks
  and any shutdown-phase server errors. Here the `timeline` stops at the last probe and
  `server_errors` is the pre-teardown list — the shutdown of this run is simply not evidenced
  either way.
- The **`spawned`** provenance field ("found" vs "client") on every `eat` / `item.state` /
  `eat.action` result (`PZTestKit_Client.lua`). Absent here. This run spawned client-side
  throughout, which is what its `server_errors[0..1]` `SyncItemFields` NPE demonstrates.
