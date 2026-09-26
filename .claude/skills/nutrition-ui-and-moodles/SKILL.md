---
name: nutrition-ui-and-moodles
description: Showing nutrition to a player — a client panel and how often it reads, a moodle through `MoodleFramework` rather than the vanilla moodle registry, `CleanUI` beside it, a `Tooltip`, `ItemName.json` translations keyed by `Module.Name`, `getText` and display names on a dedicated server, trait checks against the registry object, the band traits, and the cooked-food thirst and freshness a client copy misreports.
---
## Read first
- docs/areas/ui-and-moodles.md
- docs/platform/lua-platform.md
- docs/platform/mod-anatomy.md

## Rules quoted
- Never register a moodle type of your own through the vanilla registry: a registered type reaches every character and is driven back to its lowest level every tick, and a duplicate id corrupts the registry before the call throws [#1140/C/C-only, #2060/C/inference].
- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Take a client-side moodle read at least one push after a server-side stat write: the moodle recompute has no side guard, so the client recomputes from a mirror that can lag by a push [#0570/C/C-only].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or feed it an explicitly transmitted value: the band traits are not in the player-stats packet and no other packet was traced carrying the trait list [#1104/C/inference].
- Compare a trait by the registry object and never by its name: the name getter answers lowercased, so a string comparison against the registry spelling reads false on a trait that is demonstrably applied [#0550/M/n=1].
- Read a food's numbers from the side that owns them and never build mod math on a getter whose value is transformed again on the wire: the item packet sends a cooked food's derived thirst getter and the receiver stores it as the raw field [#1084/M/n=2].
- Ship a mod's item names in a B42 `ItemName.json` whose keys are the bare `Module.Name`: the B41 `ItemName_EN` table layout produces no name at all on this build [#1025/M/n=1].
- Never branch on an item's display name server-side or reach for one through `getText`: a dedicated server resolves no mod display name and the text router carries no item-name prefix [#1026/M/n=2].

## Also
- docs/facts/body-and-weight.md#moodles — the vanilla moodles, their thresholds and what each level does.
- docs/facts/wire-packets.md#staircase — the staircase a client-side reader sees, and the band that grades it.
- docs/areas/mp-sync.md#sync-options — the routes a mod-owned value takes to reach a client panel (skill `nutrition-mp-sync`).
