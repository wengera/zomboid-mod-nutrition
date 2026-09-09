# Project Zomboid — Nutrition Revamp: Reference Library

Research and reference documentation for building a nutrition/food overhaul mod
for Project Zomboid Build 42. The library is the current deliverable; the mod
design comes after. See [STRATEGY.md](STRATEGY.md) for the charter, method
rules, and phase plan.

**Verified against:** PZ 42.20.4 · MP-first · docs for maintainer + collaborators

## Map

| | |
|---|---|
| [STRATEGY.md](STRATEGY.md) | Charter: what we're building, method rules, phases |
| [docs/vanilla/](docs/vanilla/README.md) | How the game's nutrition/food systems actually work (code-cited) |
| [docs/modding/](docs/modding/README.md) | The modding platform: what's possible, how, and what's jar-locked |
| [docs/mods-survey/](docs/mods-survey/README.md) | Existing mods: catalog + deep teardowns |
| [docs/testing/](docs/testing/README.md) | Automated integration-testing pipeline (real server + driven clients) — design, spikes, roadmap |
| [docs/references.md](docs/references.md) | Annotated external sources (wiki, docs projects, guides, community) |
| [references/wiki-mirrors/](references/wiki-mirrors/README.md) | Dated excerpts of key wiki pages (drift insurance) |
| [tools/](tools/README.md) | Scanners/exporters (builds on the pz-b42 toolchain) |
| [data/](data/README.md) | Generated datasets (food items, recipes) |

## Related workspace

Game-mechanics research that predates this repo lives in
`C:\Users\Angus\pz-b42` (findings/, tools/pzdis.py). Relevant findings are
migrated here in adapted form; the disassembler stays there and is used via
`pz.sh`.
