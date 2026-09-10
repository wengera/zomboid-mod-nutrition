# Wiki mirror — Fridge

**Source:** https://pzwiki.net/wiki/Fridge
**Fetched:** 2026-09-10
**Wiki page version:** 41.78.19
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Short furniture page: what a fridge is for, the two spoil-rate numbers, and galleries of the residential and industrial variants. Stamped 41.78.19 — Build 41 furniture, so the roster and the capacities are pre-B42.
- Its two headline claims: a fridge divides spoil rate by 5 and a freezer compartment by 25; generic residential fridges carry 40 of fridge capacity and 20 of freezer, and the popsicle fridge is freezer-only.
- The 5x holds as a *default*, not a constant. `Food.updateAge` multiplies elapsed hours by `getFridgeFactor()` — sandbox `FridgeFactor`, enum 1-6 (0.4 / 0.3 / **0.2** / 0.1 / 0.03 / 0.0), default 3, which is exactly the 5x — and only when the container is on a live grid (`isInFridge` plus `getSourceGrid().haveElectricity()`); unpowered, food reverts to full rate once the `elecShutModifier` window closes (`docs/superpowers/plans/02-notes.md` Q2).
- Claims a 25x freezer slowdown — verify against `Food.updateAge`/`updateFreezing`: on 42.20.4 a freezer applies the same `getFridgeFactor()` as a fridge while the item is still unfrozen, and once `freezingTime` reaches 100 (four game-hours in a powered freezer, or a direct `freeze()`) the rate is x0.0. Stopped, not divided by 25 — no 25 appears anywhere in the aging path.
- Silent on everything that decides whether aging happens at all: `FoodRotSpeed` (default 1.0) scaling the same formula, `isRotten()` being `age >= offAgeMax` against a 1e9 never-ages sentinel, `DaysForRottenFoodRemoval` (-1 in every shipped preset), and `Food.update` calling `updateAge` only under `GameServer.server` — so these multipliers only bite where a server process is ticking.
- Cross-check the variant roster against `appliances.md` (42.8.0), which lists a Chest Freezer, Generic Cooled Shelves and a White Display Counter this page has never heard of; and treat 40/20 as unverified B41 container sizes, not encumbrance.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar furniture}}
{{Page version|41.78.19}}
{{Infobox tile
|name=Fridges
|icon=Appliances refrigeration 01 0.png
|icon2=appliances_refrigeration_01_22.gif
|icon3=IndustrialFridge Large.gif
|icon4=appliances_refrigeration_01_8.png
|icon5=appliances_refrigeration_01_25.png
|icon6=FridgeMini2.png
|icon7=IceBox.png
|function=Store [[food]]
}}
A '''fridge''' is an [[appliances|appliance]] use to store [[Food|perishable food]] for longer.

== Usage ==
Fridges are used to store perishable food, in order to extend the length of time needed before the food rots. When a food item is placed in a fridge, the spoil rate is reduced by 5 times.

Most fridges have a freezer, when a food item is placed in a the freezer compartment, the spoil rate is reduced by 25 times. The [[popsicle fridge]] is the only appliance that only has a freezer.

== Residential fridges ==

=== Variants ===
Generic residential fridges all have a fridge capacity of 40, and a freezer capacity of 20. They are commonly found in houses.
<div class="gallery-list">
<div>[[File:Appliances refrigeration 01 0.png|link=Plain Fridge{{lcs}}]]<br>{{ll|Plain Fridge}}</div>
<div>[[File:Appliances refrigeration 01 28.png|link=White Fridge{{lcs}}]]<br>{{ll|White Fridge}}</div>
<div>[[File:Appliances refrigeration 01 32.png|link=Red Fridge{{lcs}}]]<br>{{ll|Red Fridge}}</div>
<div>[[File:Appliances refrigeration 01 12.png|link=Green Fridge{{lcs}}]]<br>{{ll|Green Fridge}}</div>
<div>[[File:Appliances refrigeration 01 4.png|link=Blue Fridge{{lcs}}]]<br>{{ll|Blue  Fridge}}</div>
</div>
Other residential fridges can also be found, and have varying capacities.
<div class="gallery-list">
<div>[[File:Appliances refrigeration 01 25.png|link=Mini Fridge{{lcs}}]]<br>{{ll|Mini Fridge}}</div>
<div>[[File:FridgeMini2.png|link=Built-in Trailer Fridge{{lcs}}]]<br>{{ll|Built-in Trailer Fridge}}</div>
</div>

== Industrial fridges ==
Industrial fridges are most commonly found in industrial kitchens, such as [[Spiffo's]] and other food stores. The large fridge has a higher fridge capacity per tile than any other fridge, while the popsicle fridge has the highest freezer capacity per tile.

=== Variants ===
<div class="gallery-list">
<div>[[File:appliances_refrigeration_01_22.gif|link=Industrial Fridge{{lcs}}]]<br>{{ll|Industrial Fridge}}</div>
<div>[[File:appliances_refrigeration_01_40.png|link=White Industrial Fridge{{lcs}}]]<br>{{ll|White Industrial Fridge}}</div>
<div>[[File:IndustrialFridge Large.gif|link=Large Fridge{{lcs}}]]<br>{{ll|Large Fridge}}</div>
<div>[[File:appliances_refrigeration_01_8.png|link=Steel Fridge{{lcs}}]]<br>{{ll|Steel Fridge}}</div>
<div>[[File:IceBox.png|link=Popsicle Fridge{{lcs}}]]<br>{{ll|Popsicle Fridge}}</div>
</div>

== See also ==
* {{ll|Appliances}}
* {{ll|Sink}}
* {{ll|Tiles}}

== Navigation ==
{{Navbox tiles}}

{{ll|Category:Tiles}}
```
