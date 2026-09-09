# Teardown: Beyond Ten — Level 15 Skills

- Workshop ID: 3765241705 · mod ID BeyondTen · author Patryk.
- Build examined: `42/` tree, 2026-09-04 session (B41 root + B42 subtree).
- Origin: full read of Shared/Bonuses/ExtendedBonuses/SkillRecoveryJournal lua.

## What it does

Extends every trainable skill to level 15 with "mastery" levels on top of the
native 10-cap, a 15-slot skills UI, and per-skill bonuses for ranks 11–15.

## Architecture — the parallel-stat blueprint

This is the working example of exactly what our nutrient stats need to be:
**stats the java engine doesn't know about, layered on via lua + modData.**

- Native cap untouched: mastery XP banked in character modData
  (`BT.GetStoredXP`) once native XP is full; levels derived on read
  (`GetMasteryState`) from stored XP vs computed per-level costs
  (`cost(n) = xp10 + (xp10−xp9)·(n−10)` — Shared.lua).
- Effects, three delivery mechanisms:
  1. **Wrappers**: `ISBaseTimedAction.adjustMaxTime` wrapped once, idempotently
     (`if already-ours return` guard) → −2.5%/rank action time; same pattern
     for `ISReloadWeaponAction.setReloadSpeed`.
  2. **Effective-level injection**: where vanilla lua reads a perk level into a
     local (fishing rod skill, doctorLevel on medical actions, foraging
     perkLevel...), ExtendedBonuses overwrites it with the 11–15 value —
     vanilla formulas then scale for free (splint ×8 at Doctor 15).
  3. **Event-time math**: maintenance wear negation rolls per condition point
     lost; carry weight via +1/rank with **UCWF integration** (registers as a
     modifier provider when that framework exists — cooperative, not clobbering).
- Third-party compat is explicit: Skill Recovery Journal shim (records mastery
  XP into journals), UCWF handshake, DetailedSkillTooltips compat file.

## MP handling

- All state in character modData → saved and synced by the engine's own
  character path; no custom packets needed for persistence.
- Bonuses recomputed locally from modData on both sides; server lua loads the
  same shared/ files. No observed desync in our sessions on 42.20.4.

## Techniques worth stealing

- Idempotent monkey-patch guards (`if X == BT._wrapper then return`) — safe
  under lua hot-reload; every wrapper stores the original on the namespace.
- Derived-on-read leveling (never store the level, store the XP) — no
  migration when curves change.
- Weak-keyed caches (`setmetatable({}, {__mode="k"})`) for per-item/-player
  transient state — no leaks across long MP sessions.
- Cooperative framework detection (UCWF) instead of last-write-wins on a
  contested field (max carry weight).

## Pitfalls

- Effective-level injection is inherently brittle: each injection point pins
  a vanilla local-variable pattern; game updates silently break individual
  bonuses. Acceptable for bonuses; NOT acceptable for core nutrient math —
  our core loop must own its own event tick instead.

## Verdict

The architectural north star for mod-side nutrient stats: modData reservoir +
derived-on-read values + idempotent wrappers + cooperative compat shims. Not
a dependency, but its patterns get lifted nearly wholesale.
