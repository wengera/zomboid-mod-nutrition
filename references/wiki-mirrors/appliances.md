# Wiki mirror — Appliances

**Source:** https://pzwiki.net/wiki/Appliances
**Fetched:** 2026-09-10
**Wiki page version:** 42.8.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Tile catalogue of every B42 appliance object, one sortable table per family (Communication, Cooking appliances, Fridges, Washing machines, Other); each row gives encumbrance, footprint in tiles, whether it is a crafting surface, and the skill plus tool needed to pick it up or disassemble it. Stamped 42.8.0.
- The Fridges table is why this page is mirrored, but it carries no spoilage, power or temperature figure at all — it is hardware only. For the multiplier go to `fridge.md` or `docs/superpowers/plans/02-notes.md` Q2, not here.
- Refrigeration roster, 15 objects: nine residential/industrial fridges (40.0 encumbrance, 1 tile, except the 2-tile Large Fridge), Mini Fridge 10.0, Built-in Trailer Fridge 10.0, the 2-tile Popsicle Freezer, Chest Freezer 20.0, and two 3-tile shop fixtures — Generic Cooled Shelves and White Display Counter.
- Base-building detail worth having: the metal fridges need no skill to pick up but Welding plus a torch and mask to break down, while the shop coolers and the trailer fridge want Electrical or Carpentry with a screwdriver or hammer.
- Claims fridge-ness by category rather than by container type — verify each tile against `ItemContainer.isFridge()`/`isFreezer()` (type string `fridge`/`freezer`, else a parent `IsoObject` carrying `IsoPropertyType.IS_FRIDGE`); `isFridge()` returns false for anything already a freezer, and the two cooled shop fixtures are the likeliest false positives in this list.
- Stale by construction: the page's own banner says tiles were deliberately removed during B42 unstable, and 42.8.0 is twelve minors behind 42.20.4. Treat the roster as a lead list, and remember that appearing in it buys nothing unless the container is powered (`isInFridge` plus `getSourceGrid().haveElectricity()` in `Food.updateAge`).

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar furniture}}
{{Page version|42.8.0}}
{{Note|Some tiles have been intentionally removed from this list during [[Build 42]] unstable.}}
{{toc|right}}

== Communication ==
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="unsortable" rowspan=2 | Object
! class="sortable" rowspan=2 | Encumbrance
! class="sortable" rowspan=2 | Size<br>(tiles)
! class="unsortable" rowspan=2 | Crafting surface?
! class="unsortable" colspan=2 | Pick up
! class="unsortable" colspan=2 | Disassemble
|-
! class="sortable" | Skill
! class="sortable" | Tool(s)
! class="sortable" | Skill
! class="sortable" | Tool(s)
|-
| [[File:appliances_com_01_0.png|link=Premium Technologies Ham Radio]]<br>[[Premium Technologies Ham Radio]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_8.png|link=US ARMY COMM. Ham Radio]]<br>[[US ARMY COMM. Ham Radio]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_56.png|link=Makeshift Ham Radio]]<br>[[Makeshift Ham Radio]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_radio_01_0.png|link=ValuTech Radio]]<br>[[ValuTech Radio]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_radio_01_8.png|link=Premium Technologies Radio]]<br>[[Premium Technologies Radio]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_radio_01_16.png|link=Makeshift Radio]]<br>[[Makeshift Radio]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_18.png|link=Toys-R-Mine Walkie Talkie]]<br>[[Toys-R-Mine Walkie Talkie]]
| 1.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_26.png|link=ValuTech Walkie Talkie]]<br>[[ValuTech Walkie Talkie]]
| 2.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_34.png|link=Premium Tech. Walkie Talkie]]<br>[[Premium Tech. Walkie Talkie]]
| 3.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_42.png|link=Tactical Walkie Talkie]]<br>[[Tactical Walkie Talkie]]
| 4.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_50.png|link=US Army Walkie Talkie]]<br>[[US Army Walkie Talkie]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_66.png|link=Makeshift Walkie Talkie]]<br>[[Makeshift Walkie Talkie]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_television_01_1.png|link=Premium Technologies Television]]<br>[[Premium Technologies Television]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_television_01_4.png|link=ValuTech Television]]<br>[[ValuTech Television]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_television_01_9.png|link=Old Television]]<br>[[Old Television]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_72.png|link=Desktop Computer]]<br>[[Desktop Computer|Desktop Computer]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|}

== Cooking appliances ==
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="unsortable" rowspan=2 | Object
! class="sortable" rowspan=2 | Encumbrance
! class="sortable" rowspan=2 | Size<br>(tiles)
! class="unsortable" rowspan=2 | Crafting surface?
! class="unsortable" colspan=2 | Pick up
! class="unsortable" colspan=2 | Disassemble
|-
! class="sortable" | Skill
! class="sortable" | Tool(s)
! class="sortable" | Skill
! class="sortable" | Tool(s)
|-
| [[File:appliances_cooking_01_1.png|link=Green Oven]]<br>[[Green Oven|Green Oven]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_9.png|link=Red Oven]]<br>[[Red Oven|Red Oven]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_13.png|link=Modern Oven]]<br>[[Modern Oven|Modern Oven]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_21.png|link=Industrial Oven]]<br>[[Industrial Oven|Industrial Oven]]
| 25.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_25.png|link=White Microwave]]<br>[[White Microwave|White Microwave]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_28.png|link=Chrome Microwave]]<br>[[Chrome Microwave|Chrome Microwave]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_33.png|link=Small Chrome Toaster]]<br>[[Small Chrome Toaster|Small Chrome Toaster]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_42+43.png|link=Large Modern Oven]]<br>[[Large Modern Oven|Large Modern Oven]]
| 20.0
| 2
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_cooking_01_53.png|link=Fryers Club Industrial 2000]]<br>[[Fryers Club Industrial 2000|Fryers Club Industrial 2000]]
| 30.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_cooking_01_56.png|link=Coffee X-Press]]<br>[[Coffee X-Press|Coffee X-press]]
| 4.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_cooking_01_61.png|link=Espresso Deluxe]]<br>[[Espresso Deluxe|Espresso Deluxe]]
| 6.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_cooking_01_65.png|link=Bake-O-Matic Industrial]]<br>[[Bake-O-Matic Industrial|Bake-O-Matic Industrial]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:appliances_cooking_01_17.png|link=Old Stove]]<br>[[Old Stove|Antique Oven]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:crafted_01_26.png|link=Metal Drum]]<br>[[Metal Drum|Metal Drum (variant 3)]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_01_27.png|link=Metal Drum]]<br>[[Metal Drum|Metal Drum (variant 4)]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_01_30.png|link=Metal Drum]]<br>[[Metal Drum|Metal Drum (variant 7)]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_01_31.png|link=Metal Drum]]<br>[[Metal Drum|Metal Drum (variant 8)]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_42.png|link=Brazier]]<br>[[Brazier|Brazier]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_43.png|link=Brazier]]<br>[[Brazier|Brazier (variant 2)]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_44.png|link=Brazier]]<br>[[Brazier|Brazier (variant 3)]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_05_7.png|link=Crafted Oven]]<br>[[Crafted Oven]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_35.png|link=Barbecue]]<br>[[Barbecue|Charcoal Barbecue]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_cooking_01_36.png|link=Jorge Foreguy Barbecue]]<br>[[Jorge Foreguy Barbecue|Full Jorge Foreguy Barbecue]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:appliances_cooking_01_44.png|link=Jorge Foreguy Barbecue]]<br>[[Jorge Foreguy Barbecue]]
| 15.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Carpentry}}
| {{ll|Claw Hammer}}
|-
| [[File:crafted_02_48.png|link=LightCharcoal Burner]]<br>[[LightCharcoal Burner]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_49.png|link=Charcoal Burner]]<br>[[Charcoal Burner]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_50.png|link=Charcoal Burner (variant 2)]]<br>[[Charcoal Burner (variant 2)]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_51.png|link=Charcoal Burner (variant 3)]]<br>[[Charcoal Burner (variant 3)]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|-
| [[File:crafted_02_52.png|link=Electric Blower Forge]]<br>[[Electric Blower Forge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|}

== Fridges ==
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="unsortable" rowspan=2 | Object
! class="sortable" rowspan=2 | Encumbrance
! class="sortable" rowspan=2 | Size<br>(tiles)
! class="unsortable" rowspan=2 | Crafting surface?
! class="unsortable" colspan=2 | Pick up
! class="unsortable" colspan=2 | Disassemble
|-
! class="sortable" | Skill
! class="sortable" | Tool(s)
! class="sortable" | Skill
! class="sortable" | Tool(s)
|-
| [[File:appliances_refrigeration_01_0.png|link=White Fridge]]<br>[[White Fridge|White Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_4.png|link=Blue Fridge]]<br>[[Blue Fridge|Blue Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_8.png|link=Steel Fridge]]<br>[[Steel Fridge|Steel Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_12.png|link=Green Fridge]]<br>[[Green Fridge|Green Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_18+19.png|link=Large Fridge]]<br>[[Large Fridge|Large Fridge]]
| 40.0
| 2
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_22.png|link=Industrial Fridge]]<br>[[Industrial Fridge|Industrial Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_25.png|link=Mini Fridge]]<br>[[Mini Fridge|Mini Fridge]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_28.png|link=Plain Fridge]]<br>[[Plain Fridge|Plain Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_32.png|link=Red Fridge]]<br>[[Red Fridge|Red Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_40.png|link=White Industrial Fridge]]<br>[[White Industrial Fridge|White Industrial Fridge]]
| 40.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:location_shop_generic_01_64+65+66.png|link=Generic Cooled Shelves]]<br>[[Generic Cooled Shelves|Generic Cooled Shelves]]
| 10.0
| 3
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Carpentry}}
| {{ll|Claw Hammer}}<br>{{ll|Hacksaw}}
|-
| [[File:location_trailer_02_16.png|link=Build-in Trailer Fridge]]<br>[[Build-in Trailer Fridge]]
| 10.0
| 1
| [[File:UI Tick.png|link=|Can be used as a surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Carpentry}}
| {{ll|Claw Hammer}}<br>{{ll|Hacksaw}}
|-
| [[File:appliances_refrigeration_01_38+39.png|link=Popsicle Fridge]]<br>[[Popsicle Fridge|Popsicle Freezer]]
| 40.0
| 2
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_refrigeration_01_48.png|link=Chest Freezer]]<br>[[Chest Freezer|Chest Freezer]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:location_shop_generic_01_80+81+82.png|link=White Display Counter]]<br>[[White Display Counter|White Display Counter]]
| 10.0
| 3
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Carpentry}}
| {{ll|Claw Hammer}}<br>{{ll|Hacksaw}}
|}

== Washing machines ==
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="unsortable" rowspan=2 | Object
! class="sortable" rowspan=2 | Encumbrance
! class="sortable" rowspan=2 | Size<br>(tiles)
! class="unsortable" rowspan=2 | Crafting surface?
! class="unsortable" colspan=2 | Pick up
! class="unsortable" colspan=2 | Disassemble
|-
! class="sortable" | Skill
! class="sortable" | Tool(s)
! class="sortable" | Skill
! class="sortable" | Tool(s)
|-
| [[File:appliances_laundry_01_12.png|link=White Clothing Dryer]]<br>[[White Clothing Dryer]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_laundry_01_4.png|link=White Washing Machine]]<br>[[White Washing Machine]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:appliances_laundry_01_0.png|link=Blue Combo Washer Dryer]]<br>[[Blue Combo Washer Dryer]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|}

== Other ==
{| class="wikitable theme-red sortable" style="text-align: center;"
|-
! class="unsortable" rowspan=2 | Object
! class="sortable" rowspan=2 | Encumbrance
! class="sortable" rowspan=2 | Size<br>(tiles)
! class="unsortable" rowspan=2 | Crafting surface?
! class="unsortable" colspan=2 | Pick up
! class="unsortable" colspan=2 | Disassemble
|-
! class="sortable" | Skill
! class="sortable" | Tool(s)
! class="sortable" | Skill
! class="sortable" | Tool(s)
|-
| [[File:appliances_com_01_84.png|link=Cinema Projector]]<br>[[Cinema Projector|Cinema Projector]]
| 10.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_69.png|link=Standing Microphone]]<br>[[Standing Microphone|Standing Microphone]]
| 5.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_cooking_01_69.png|link=Extractor Hood]]<br>[[Extractor Hood|Extractor Hood]]
| N/A
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_52.png|link=CeroSec Terminal]]<br>[[CeroSec Terminal|CeroSec Terminal]]
| 35.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:security_01_0.png|link=Security Terminal]]<br>[[Security Terminal|Security Terminal]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_44.png|link=Imekagi HK533p]]<br>[[Imekagi HK533p|Imekagi HK533p]]
| 25.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:appliances_com_01_20.png|link=Satellite Dish]]<br>[[Satellite Dish|Satellite Dish]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
| {{ll|Carpentry}}
| {{ll|Claw Hammer}}
|-
| [[File:location_community_school_01_32.png|link=Wall Clock]]<br>[[Wall Clock|Wall Clock]]
| 3.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:walls_decoration_01_105.png|link=Square Wall Clock]]<br>[[Square Wall Clock]]
| 3.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:industry_01_4.png|link=Air Conditioner]]<br>[[Air Conditioner|Air conditioner]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_2.png|link=Air conditioner (variant 2)]]<br>[[Air conditioner (variant 2)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_5.png|link=Air conditioner (variant 3)]]<br>[[Air conditioner (variant 3)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_6.png|link=Air conditioner (variant 4)]]<br>[[Air conditioner (variant 4)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_8.png|link=Air conditioner (variant 5)]]<br>[[Air conditioner (variant 5)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_10.png|link=Air conditioner (variant 6)]]<br>[[Air conditioner (variant 6)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_13.png|link=Air conditioner (variant 7)]]<br>[[Air conditioner (variant 7)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_18.png|link=Air conditioner (variant 8)]]<br>[[Air conditioner (variant 8)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:rooftop_furniture_20.png|link=Air conditioner (variant 9)]]<br>[[Air conditioner (variant 9)]]
| 2.5
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| {{ll|Carpentry}}
| [[Item tag#tag-Hammer|Hammer (tag)]]
| {{ll|Welding}}
| {{ll|Welding Torch}}<br>[[Item tag#tag-WeldingMask|WeldingMask (tag)]]<br>{{ll|Welder Mask}}
|-
| [[File:recreational_01_20.png|link=Kaboom! Arcade Machine]]<br>[[Kaboom! Arcade Machine|Kaboom Arcade Machine]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:recreational_01_16.png|link=Dr. Oids Arcade Machine]]<br>[[Dr. Oids Arcade Machine|Dr. Oids Arcade Machine]]
| 20.0
| 1
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| {{ll|Electrical}}
| {{ll|Screwdriver}}
|-
| [[File:recreational_01_25+24.png|link=PAWS Pinball Machine]]<br>[[PAWS Pinball Machine|PAWS Pinball Machine]]
| 20.0
| 2
| [[File:UI Cross.png|link=|Not a crafting surface]]
| [[File:UI Cross.png|link=|No skill required]]
| [[File:UI Cross.png|link=|No tool required]]
| colspan="2" | [[File:UI Cross.png|link=|Can't be disassembled]]<br>Can't be disassembled
|}

{{ll|Category:Tiles}}
```
