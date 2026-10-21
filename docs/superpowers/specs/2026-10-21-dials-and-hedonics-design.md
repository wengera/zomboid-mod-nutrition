# Plan 19: tuning dials across the mod, and food hedonics — design

Angus, 2026-10-21. He asked to rethink the food boredom and unhappiness curves:
- how cooking skill affects them;
- how some foods, like eating sticks of butter, are inherently sad but calorically superior;
- keeping total punishment close to vanilla while each adjustment's reason is unique and realistic.

He also asked: "proceed with your recommendations but generalize and abstract in a way that we can quickly tune things, then also do a whole mod review to see how we can refactor generalize and abstract so we can tune dials without significant rework as well, proceed with normal planning and execution throughout, no need to review or ask questions".

The evidence:
- `.superpowers/sdd/plan-19-brainstorm/inventory.md`: vanilla's food mood, cooking, the mod's monotony, calorie density against mood, the levers;
- `.superpowers/sdd/plan-19-brainstorm/science.md`: the hedonics science in the register, and its gaps.

## Part A: tuning dials

### A.1 The problem
The mod's magnitudes are spread as named constants across about forty kernel and adapter files. Each carries its provenance in a comment: a science row, a register row, or "game choice". Tuning one means finding it, editing a code line, re-anchoring the register pointers that move, and re-recording the golden. There is no single place that lists what can be tuned, its unit, range and source, or which dials an admin may set.

### A.2 The design
- **The registry.** `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Dials.lua` holds the dials, grouped by domain: drain, symptoms, satiety, hunger curve, kinetics, body, strength, acute, fluids, effects, monotony, hedonics, and so on. Each dial is a row: `{ value, unit, min, max, src, note }`.
  - `src` is a science id (`S1234`), a register id (`#1234`), `"game choice"`, or `"vanilla"` (a value copied from the game, with its row).
  - A sandbox-exposed dial names its option.
- **Reading a dial.** Kernels read dials through `K.dials.get("domain.name")`. The result is resolved once, when the kernel module loads, into the module's own upvalue or constant. So no lookup ever runs per tick or per minute (Rule 6), and a hot path reads a plain local as now.
- **Sandbox overrides.** A dial with a sandbox option is re-resolved when the options poll sees a change. This is the existing `stimulantRealism` / `deathPace` pattern, generalised.
- **Structural constants stay in their kernels.** These are state codes, array sizes and the 17 body parts. Only tunable magnitudes move to the registry.
- **`tools/dials.py`:**
  - `list`: a table of every dial, filterable by domain or source;
  - `check`: each dial is in range, has a unit and a source, and every science or register source exists (`science.tsv`, `claims.tsv`);
  - `diff A B`: compares two commits' dials;
  - `set domain.name value`: edits the registry in place, keeping the file's formatting, so a tune is one command.
  - It is a § 3 gate on `mod/` commits.
- **The lint.** `tools/dial_lint.py` flags a numeric literal in a kernel or adapter assignment whose comment says "game choice", "science" or a register or science id, but which is not read from the registry. It is a § 3 gate once the migration is done.
- **Register pointers.** A claim that quotes a constant's kernel line moves to the registry line, which is stable because each dial is one line. A rename is requoted live; nothing is pinned for a pure move (ruling T10-2).
- **Migration** runs domain by domain. Each wave is a pure refactor, proven by the golden trace reproduced byte for byte and the full pytest green. No value changes in Part A.

### A.3 The review first
A read-only whole-mod review inventories every tunable constant: file, line, value, unit, source, and which outputs it reaches. It classes each one as dial or structural, finds duplicated magnitudes (the same number written in two places), dials that should be derived from others, and sandbox candidates. It proposes the domain grouping and the wave order. Its output is `dial-inventory.md`, and the build follows it.

## Part B: food hedonics

### B.1 What stays
Vanilla's per-item UnhappyChange and BoredomChange stay the base: subjective pacing follows vanilla. Vanilla already makes plain fats sad: butter +20, lard +30, oils +50 (inventory § 3). Its state terms stay too: burnt, stale, rotten, frozen, hot and cold, and utensils.

### B.2 What the mod adds, each for a stated realistic reason, all magnitudes as dials

1. **Plain-energy unpalatability (the stick of butter).**
   - Under the mod a resting day burns about 1.8 to 2.3 times vanilla's calories, so dense plain fats and oils become the efficient calorie source. Vanilla's per-item sadness doesn't scale with how much of the day's food they are.
   - The science: an unpalatable food is eaten at 40–65 % of a palatable one's amount (S1599); liking tracks intake (S1601). Fat, sugar or starch alone is unpleasant; the combination is palatable (a gap, harvested in B.4).
   - The rule: each eat of a **plain energy food** adds its energy to a rolling **unpalatable-energy share** of the last 24 online hours. A plain energy food is one whose energy is more than a dial threshold (e.g. 80 %) from a single macro with no flavour pairing: plain fats, oils, sugar, flour, plain starch. An evolved dish's ingredients are exempt.
   - The share drives an **unhappiness floor** through the monotony composer's floor mechanism (it self-releases; a raw add would never decay), on a dial curve.
   - Eating a little butter is vanilla's own sadness. Living on it adds a floor that grows with the share.
2. **Cooking quality.**
   - Vanilla cooking skill reaches dish mood only through the per-ingredient −5 term and the spice term (inventory § 2). Under vanilla a fat or spice cooked into a dish loses its sadness, which is realistic: butter in a sauce is pleasant.
   - The mod adds a **preparation quality** that scales a cooked or evolved dish's unhappiness relief by the cook's Cooking level, on a dial curve: a level-0 cook gains less relief, a level-10 cook more. Science: cooked against raw palatability, and home cooking skill against diet satisfaction (a gap, harvested).
   - It is applied at the add-ingredient seat, or by the `OnCooked` hook where the dish's mood is set (inventory § 4), so it costs nothing per tick.
3. **Hunger sharpens taste (alliesthesia).**
   - A hungry character minds an unpalatable food less. S1604 gives the direction; Cabanac 1971 is a gap to harvest.
   - The mod scales a food's **positive** (sad) UnhappyChange down by a dial factor while the mod's hunger is at Hungry or above. It never scales the happy side.
   - The reason: starving survivors eat what they must. It eases the stick-of-butter penalty when truly hungry, so the floor in rule 1 carries the long-run cost.
4. **Monotony by taste class.**
   - The same-food floor, today keyed on the full item type, also counts a **taste class**: sweet, savoury, fatty, bland staple. Sensory-specific satiety keys more on sweet against savoury than on the item (S1591). Staples resist (S1593); they keep the quarter weight.
   - One stew is still one food, and its class is set from its main ingredient.

### B.3 The budget
"Equitable total punishment" is enforced by an oracle. A reference-diet replay runs a set of vanilla-plausible diets over 14 days on the replay host:
- a mixed diet;
- cooked dishes;
- canned food only;
- a stick-of-butter diet;
- a sugar diet;
- one food only.

It compares unhappiness-hours (and boredom-hours) against vanilla's model of the same diets. The oracle fails when a balanced or cooked diet is materially sadder than vanilla, or when a degenerate diet (butter, sugar, one food) is not sadder than vanilla, with the bands as dials. This makes every hedonics dial tunable against one test.

### B.4 Research first
- A science harvest fills the gaps the hedonics rules lean on: Drewnowski and Greenwood 1983 (fat-sugar), Rolls et al. 1981 (sensory-specific satiety), Cabanac 1971 (alliesthesia), the cooked-against-raw palatability and cooking-skill studies, and Meiselman and Kramer on ration acceptance. Rows are settled only against their records (CLAUDE.md § 4.8). Every hedonics dial's `src` names its row, or "game choice" where none settles.
- A **jar recheck** of `EvolvedRecipe.useSpice` on 42.21: the inventory found it lowers dish unhappiness and boredom, which contradicts #0296, #0299, #0365, #0731 and #1157. The rows are superseded or noted before any hedonics rule rests on them.

### B.5 Live
One session:
- a stick of butter eaten plain against cooked into a dish, at two Cooking levels;
- the unpalatable-energy floor rising over repeated plain eats;
- the alliesthesia scale while Hungry.

Each graded against the HEAD replay.

## Rule 6
Every hedonics rule runs at an eat, an ingredient add, or inside the existing writer minute (the floors), never per tick. The rolling share is a fixed-size ring updated at the eat. Part A's dial reads are resolved at load. A bench and a Java-call count are taken before and after.

## Not in this plan
- new moodles;
- changing vanilla's per-item base values;
- comfort-food mood lifts (the science is contested: S0933 against S1560 and S1561; Wagner 2014's "myth of comfort food").
