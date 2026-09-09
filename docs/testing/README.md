# Testing pipeline

Automated integration testing of mods on a **real** dedicated server with
**real** driven clients. Design: [pipeline-design.md](pipeline-design.md)
(layers L0–L4, harness mod + python orchestrator, fragility budget, spikes
S1–S7, roadmap T0–T4).

Status: designed 2026-09-13 on verified facts (auto-connect args, RCON,
lua-exposed `serverConnect`, `GameTime.setMultiplier`, DataLogger's
spool/ready handoff). Next: spike S1 (boot loop) → T1.

Code will live in `testing/` at repo root (`pzt/` orchestrator, `PZTestKit/`
harness mod, `profiles/`, `fixtures/`).
