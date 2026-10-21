# Plan 19: tuning dials and food hedonics — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:**
- Move every tunable magnitude in the mod into one registry of dials, with a tool to list, check and set them.
- Then add food hedonics on top:
  - plain-energy unpalatability;
  - cooking quality by skill;
  - alliesthesia;
  - taste-class monotony.

  It is tuned against an equitable-punishment budget oracle.

**Architecture:**
- `NR_Data_Dials.lua` (rows `{ value, unit, min, max, src, note }`).
- `K.dials.get`, resolved at module load into locals.
- Sandbox-backed dials re-resolved by the options poll.
- `tools/dials.py` (list, check, diff, set) and `tools/dial_lint.py`.
- Migration by domain waves, each a pure refactor proven by the golden.
- The hedonics rules are dial-driven, run at eat or ingredient-add time and in the existing writer minute, and are tuned against a reference-diet oracle on the replay host.

**Spec:** `docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md`.

## Global Constraints

- CLAUDE.md §§ 3–6 bind every task, including the rule that the full pytest runs before any register apply that supersedes a guide-cited row.
- **Part A changes no value.** Every wave reproduces the golden trace byte for byte, keeps the guide data's series identical (provenance only), and keeps the full pytest green.
- A dial read is resolved at load or at an options change, never per tick and never per minute in a hot path. The bench and Java-call count are unchanged by Part A.
- Register pointers to a moved constant are re-anchored to its registry line (a move, ruling T10-2), never pinned.
- Every dial has a unit, a range and a source.
- Part B's magnitudes are dials with `src` naming a settled science row, a register row, or "game choice".

---

### Task 1: The whole-mod dial review (read-only)
Inventory every tunable constant in `mod/NutritionRevamp`:
- its file, line, value, unit, source and the outputs it reaches;
- its class: dial or structural;
- duplicated magnitudes, derivable dials and sandbox candidates.

Propose the domain grouping, the registry row shape and the migration wave order, with each wave's register re-anchor count. Output `.superpowers/sdd/2026-10-21-plan-19-dials-and-hedonics/dial-inventory.md`. Opus.

### Task 2: The dial framework, with the first domain
**Create:**
- `NR_Data_Dials.lua` and `NR_Kernel_Dials.lua` (`K.dials.get`, the at-load resolution, the sandbox re-resolve hook);
- `tools/dials.py` (list, check, diff, set);
- `tools/dial_lint.py`;
- tests under `tools/tests/` and `testing/tests/kernel/`.

**Migrate** the first domain from Task 1's order, the smallest with the most game choices, as the worked example.

**Gates:**
- the golden byte-identical;
- the guide data's series unchanged;
- the bench unchanged;
- a CLAUDE.md § 3 gate line added for `dials.py check` (the controller edits CLAUDE.md).

### Task 3: Migration waves
One sub-task per domain in Task 1's order, serial in the mod lane. Each wave:
- moves its domain's constants into the registry;
- has its kernels read them at load;
- re-anchors the register pointers;
- keeps the golden byte-identical and pytest green.

The last wave turns `dial_lint` on as a gate. Each wave is reviewed (Opus) with a mutation probe: changing a dial in the registry changes the output without a code edit.

### Task 4: Research: the jar recheck and the hedonics science
- Run `tools/jar_recheck.py` (or a direct read) on `EvolvedRecipe.useSpice` and the rows #0296, #0299, #0365, #0731, #1157, #0381 and #1278. Write the supersede or settle delta.
- Harvest the hedonics gaps (spec B.4) into a science delta, settled only against their records.

Opus. No mod edit. Its outputs feed Task 5's dial sources.

### Task 5: The hedonics kernel and the budget oracle
- Dials for B.2's four rules in the `hedonics` domain.
- The kernel:
  - classify each food as plain energy and by taste class, from the nutrient data at item-pass build time (a generated table, like the fills);
  - the rolling unpalatable-energy share and its floor;
  - the preparation-quality scale;
  - the alliesthesia scale;
  - the monotony taste-class count.
- The reference-diet oracle on the replay host against `tools/vanilla_model.py`, with its bands as dials.
- Tests, plus a mutation pass. The golden is re-recorded under a named cause.

### Task 6: The adapters and Rule 6
- The eat wrapper applies alliesthesia and records the plain-energy share.
- The add-ingredient wrapper or `OnCooked` applies the preparation quality.
- The floors go through the writer.
- `replay_live` carries the new rows.
- Bench and Java-call count against the build before.

### Task 7: Live
One session (spec B.5): drivers reviewed before the boot, then a live review and the delta.

### Task 8: The guide and the register
- **The guide:** the Monotony topic becomes a divergence topic (butter, cooking, hunger, taste class), with charts from the oracle diets.
- **The register:** rows for the dial framework, the hedonics mechanisms, the oracle, and the live readings; the science rows from Task 4.
- Trial apply, with the guide tests green.

### Task 9: Re-stage, smoke and close
- Re-stage and run a smoke boot (x485's design).
- The whole-pass review, the fix wave and the re-review.
- README, CHANGELOG and COMPATIBILITY.
- The CLAUDE.md baseline and gates (`dials.py check`, `dial_lint`).
- Memory, then push.
