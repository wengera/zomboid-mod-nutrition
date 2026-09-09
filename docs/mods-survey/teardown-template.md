# Teardown template

Copy for each mod. Cite files as `mod-relative/path.lua:line` and pin the
mod build date (they update often — note workshop ID + folder mtime).

```markdown
# Teardown: <Mod Name>

- Workshop ID / mod ID(s):
- Build examined (date + version folder used):
- Author · dependencies · license/permissions posture:

## What it does (player-facing)

## Architecture
How it's wired: entry points (events hooked), data model (modData? sandbox
vars? item scripts?), client/server split, files that matter.

## MP handling
What syncs, how (commands? modData? item fields?), where authority lives,
observed or latent desync risks.

## Techniques worth stealing
Concrete patterns with file:line references.

## Pitfalls / anti-patterns
What bit them (or will), and the rule we derive from it.

## Compatibility notes
Load-order sensitivity, API surface it monkey-patches, conflicts seen.

## Verdict for our mod
What we adopt, what we avoid, whether it's a dependency candidate.
```
