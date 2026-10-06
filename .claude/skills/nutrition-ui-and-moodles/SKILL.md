---
name: nutrition-ui-and-moodles
description: Showing nutrition to a player — a client panel and how often it reads, a moodle through `MoodleFramework` rather than the vanilla moodle registry, `CleanUI` beside it, a `Tooltip`, `ItemName.json` translations keyed by `Module.Name`, `getText` and display names on a dedicated server, trait checks against the registry object, the band traits, and the cooked-food thirst and freshness a client copy misreports.
---
## Read first
- docs/areas/ui-and-moodles.md
- docs/platform/lua-platform.md
- docs/platform/mod-anatomy.md

## Rules quoted
- Cache a nutrition value at the push cadence rather than the frame cadence: the source changes once a second and the measured arrivals show it, while a viewer's read count is the viewer's own and drifts with its version, the arrivals measured in one session [#2692/M/n=1] [#2524/C/C-only].
- Never register a moodle type of your own through the vanilla registry: a registered type reaches every character and is driven back to its lowest level every tick, and a duplicate id corrupts the registry before the call throws [#1140/C/C-only, #2060/C/inference].
- Render through `MoodleFramework` or the mod's own panels rather than patching the widgets a resident interface mod already patches: `CleanUI` redraws the status surfaces on this server [#1083/C/snapshot].
- Set a framework moodle's value on its bad side for a symptom: when the framework's background-colour option is on, the plate's tint follows the polarity the value reaches, and a moodle at the neutral value is never drawn [#3235/C/inference] [#2534/C/C-only] [#3234/C/C-only] [#3191/M/n=1] [#3192/M/n=1] [#3229/M/n=1].
- Give a mod's own status column a fixed inset of the viewport clear of the vanilla stack's measured band rather than a slot counted off the stack: the framework places its own moodles in the vanilla band's x by a count of vanilla's moodles, another moodle manager's and its own, never a mod's column [#3236/C/inference] [#2549/C/C-only] [#3197/M/n=1] [#3223/M/n=1].
- Rebuild a panel's row model when the mirror's arrival counter moves and draw the held rows in between: the mirror changes only at a push, the view's rebuilds followed the client's arrival count, and an open panel's render calls climbed about 60 a second [#3237/C/inference] [#2692/M/n=1] [#2524/C/C-only] [#3219/M/n=1] [#3227/M/n=1] [#3214/M/n=1] [#3195/M/n=1].
- Evaluate anything keyed on the Obese, Overweight, Underweight or Emaciated band server-side, or push the trait list after you write it as [the trait-push rule](../areas/mp-sync.md#rules) says: the band traits are not in the player-stats packet; they reach the affected player's client on the player-fields packet's trait block and on the timed experience packet, each as fresh as its last push, and no player-addressed push refreshes another client's copy [#2727/C/inference] [#2595/C/C-only] [#2606/C/C-only] [#2603/C/C-only] [#2612/C/C-only].
- Compare a trait by the registry object and never by its name: the name getter answers lowercased, so a string comparison against the registry spelling reads false on a trait that is demonstrably applied [#0550/M/n=1].
- Read a food's numbers from the side that owns them and never build mod math on a getter whose value is transformed again on the wire: the item packet sends a cooked food's derived thirst getter and the receiver stores it as the raw field [#1084/M/n=2].
- Ship a mod's item names in a B42 `ItemName.json` whose keys are the bare `Module.Name`: the B41 `ItemName_EN` table layout produces no name at all on this build [#1025/M/n=1].
- Never branch on an item's display name server-side or reach for one through `getText`: a dedicated server resolves no mod display name and the text router carries no item-name prefix [#1026/M/n=2].

## Also
- docs/platform/client-ui.md#panel-toolkit — the widget toolkit, the tooltip and character-info wrap points, and the moodle stack as an anchor.
- docs/facts/other-mods/moodleframework.md#what-it-does — the framework torn down as a client widget library.
- docs/facts/body-and-weight.md#moodles — the vanilla moodles, their thresholds and what each level does.
- docs/facts/wire-packets.md#staircase — the staircase a client-side reader sees, and the band that grades it.
- docs/areas/mp-sync.md#sync-options — the routes a mod-owned value takes to reach a client panel (skill `nutrition-mp-sync`).
