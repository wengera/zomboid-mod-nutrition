# Patterns & anti-patterns — evidence from the approved corpus

Derived from the 230-mod inventory
([survey](../mods-survey/approved-modlist.md)) + line-level reads of
ItemQuality, BeyondTen, damnlib, KBW/ElyonLib, ChuckleberryFinn mods.
Rule of thumb throughout: **adopt what the well-behaved heavy mods converge
on; treat divergence as a decision point, not a free choice.**

## KEEP — patterns to adopt

1. **modData as the only durable mod state** (universal among survivors).
   Character/item/global modData saves and syncs on engine paths; live java
   fields are unsynced cache. Corollary from ItemQuality's failure: any live
   field you set must be *derivable* from modData and re-applied idempotently.
2. **The MP command bus**: `sendClientCommand(player, module, cmd, args)` →
   server `OnClientCommand` → validate → mutate → `sendServerCommand` back.
   20 mods client-side, 14 server-side — including the server's own stack.
   Server validates; client predicts at most.
3. **`OnInitGlobalModData` for world-scoped state** (14 mods) — the sanctioned
   init point for shared tables, before players exist.
4. **Idempotent monkey-patching with kept originals** (BeyondTen exemplar):
   `if target == BT._wrapper then return; BT._orig = target; target = wrapper`
   — safe under lua reload, unwindable, and composes when two mods wrap the
   same function. HorseMod (22 patch sites) shows the volume this reaches.
5. **Derived-on-read values** (BeyondTen): store XP/inputs in modData, compute
   levels/effects on read. No migrations when formulas change.
6. **Declarative config tables** driving generic engines (ItemQuality's stat
   categories; KBW's JSON buildable definitions at the extreme). Content
   changes then never touch logic.
7. **Cooperative framework detection** (BeyondTen×UCWF): if a framework owns a
   contested value (carry weight, moodles), register with it when present
   instead of last-write-wins. For us: MoodleFramework is server-approved —
   evaluate adoption before rolling our own moodle rendering.
8. **Heartbeat discipline**: prefer `EveryOneMinute`/`EveryTenMinutes` (10
   mods) for slow simulation (nutrient decay!), `OnPlayerUpdate` only for
   per-frame needs with cheap early-outs — 38 mods share that hook; be a good
   neighbor. `OnTick` is the expensive tier (14 mods) — avoid.
9. **Error hygiene at boundaries**: CleanUI (101 pcall), Economy (58),
   BeyondTen (47) wrap third-party/engine-boundary calls. A failed hook that
   throws kills every later handler on that event — pcall at the rim, fail
   soft, log.
10. **Version-folder layout** `42/` + `42.x/` overrides + `common/` (every
    mod on the list) with `mod.info` `require=` for dependency ordering
    (ChuckleberryFinn mods chain: SRJ → AlertSystem + errorMagnifier).

## FILTER OUT — anti-patterns observed or implied

1. **Unsynced-field authority** — ItemQuality's conditionMax lesson; the
   engine's sync packet list is the contract, verify per field.
2. **One-shot repair logic + observation trackers that overwrite truth**
   (ItemQuality's KnownCondition poisoning). Reconciliation must converge,
   not latch.
3. **Effective-level/local-variable injection for core math** (BeyondTen uses
   it for *bonuses*, acceptably) — each injection point breaks silently on
   game updates. Core nutrient math owns its own tick instead.
4. **Zero error-handling in huge codebases** — KBW/HorseMod/damnlib run 0
   pcall across 2MB+ lua; they get away with it via author discipline, but
   KBW's own bug thread (server-freeze on chunk load, T-junction silent
   failures) shows the cost. Not our style for an MP mod.
5. **`OnTick` for simulation** — 69 hook registrations concentrated in the
   heavy tier; nutrition has no business there.
6. **Data-as-lua at scale without laziness** (BaseQuests: 423KB of tables
   parsed at boot) — fine for a quest pack; our item-pass data belongs in
   script files or lazily-loaded modules.
7. **`loadstring` anything** — removed from the engine (42.20.x security
   fixes); corpus count is zero, keep it zero.
8. **Fighting resident UI mods** — CleanUI redraws status surfaces on this
   server; render through MoodleFramework/own panels, don't patch the same
   widgets it patches.

## Measured MP sync facts (42.20.4, spike S6 — [testing/spikes.md](../testing/spikes.md))

Established with the sync witness on a real dedicated server + real client;
they sharpen KEEP 1–2 and FILTER 1.

| Change made on the client | Reaches the server? |
|---|---|
| `player:getModData().k = v` | **no** — until `player:transmitModData()`, then yes |
| `setCondition` / `setConditionMax` / `getModData()` on an inventory item, then `sendItemStats(item)` | **never** — `sendItemStats` is `GameServer.sendItemStats` (server → owning client, packet `ItemStats`); on a client it is a silent no-op. There is no client→server "push my item fields" API, and waiting 60 s changes nothing |
| `inventory:AddItem("Base.X")` client-side | **never** — the server's copy of the player's inventory (it does hold one: a server-side `additem` shows up on both sides with one id) never gains the item |
| nutrition (`getNutrition()` calories/weight/macros) | the client computes; the server keeps a live mirror (within 0.2 kcal). Nutrition is client-authoritative in MP; server-side code reads a lagging copy |

Consequences for the nutrition mod:
- **Item mutations go through the command bus** (KEEP 2): client →
  `sendClientCommand` → server edits the item → `sendItemStats` broadcasts.
  Editing a food item's fields client-side (e.g. per-item nutrient values)
  desyncs silently — the ItemQuality failure, now reproducible on demand.
- **Per-player nutrient state lives in player modData and is
  `transmitModData()`-ed on change**, or lives server-side and is pushed with
  `sendServerCommand`. One owner per value; the witness suite checks it.
- Accelerated tests: RCON `settimespeed <x>` broadcasts to every client and
  nutrition ticks scale with it (spike S5); always restore through the same
  command.

## Open pattern questions (feed into teardowns)

- How does LongTermPreservation4220 override vanilla food spoilage — item
  script redefinition, lua-side, or both? (→ our item-pass mechanism choice)
- What cadence does simpleStatus poll nutrition at, and does it read
  getNutrition() client-side only?
- MoodleFramework API surface + MP behavior — adoption decision.
- How the Girth stack namespaces its 110+ command sites (collision risk for
  our module names on the same bus).
