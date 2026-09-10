# Wiki mirror — Trait

**Source:** https://pzwiki.net/wiki/Trait
**Fetched:** 2026-09-10
**Wiki page version:** 42.20.4
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- The full trait roster with point costs, tooltips and effect notes, plus the adaptive strength/fitness/weight trait tables. Stamped `{{Page version|42.20.4}}` — the same build slice 03 disassembled, so its disagreements below are live contradictions rather than staleness. Only the appetite/thirst/weight/fitness traits are digested here.
- Display names have drifted from the API strings: the page's Fast Metabolism is `WeightLoss`, Slow Metabolism is `WeightGain`, and Very Low / Low / High / Very High Weight are `Very Underweight` / `Underweight` / `Overweight` / `Obese`. `CharacterTrait.<clinit>` and `media/scripts/generated/characters/character_traits.txt` still register the old strings, so Lua must call `hasTrait("Obese")` or `hasTrait("Very Underweight")` (with the space) — never the display names.
- Several multipliers match the jar exactly: Hearty Appetite 150 % and Light Eater 75 % hunger (`getAppetiteMultiplier` x1.5 / x0.75), Low Thirst 50 % (`updateThirst` x0.5), Athletic -20 % running endurance loss (`updateEndurance` 0.8), and the 40 / 70 / 30 % endurance-regeneration figures for Obese / Overweight / Emaciated, which are `getRecoveryMod`'s x0.4 / x0.7 / x0.3.
- Its weight-band table (35–50 / 51–65 / 66–75 / 76–85 none / 86–100 / 101–130) contradicts `Nutrition.applyTraitFromWeight`, whose comparisons are **inclusive at both ends**: `weight >= 100` is Obese and `weight <= 50` is Emaciated, 85 is Overweight and 75 is Underweight, and normal is the open interval (75, 85). The 35 and 130 endpoints are the weight-change floor and ceiling, not band edges. Verify against `Nutrition.applyTraitFromWeight @65-@217`.
- Claims High Thirst makes you "twice as thirsty as normal when dying of thirst". The x2 at `updateThirst @2-@18` is unconditional — both the awake and the asleep branch, at every thirst level, with no health-bar term of its own. Verify against `IsoGameCharacter.updateThirst`.
- Claims Nutritionist "improves foraging", and caps fitness at 7 for Obese against 9 for Overweight. `Food.DoTooltip @1269-@1291` is the only reader of `NUTRITIONIST`/`NUTRITIONIST2` in the jar and `media/lua` has no gameplay use of it (display-only), while `Nutrition.canAddFitnessXp` blocks Fitness and Strength XP from level **6** for Obese / Emaciated / Very Underweight and from 9 for Overweight — and plain Underweight never blocks at all, because `characterHaveWeightTrouble` tests `VERY_UNDERWEIGHT` twice and `UNDERWEIGHT` never. Verify against `Food.DoTooltip` and `Nutrition.canAddFitnessXp @0-@85`.
- Its per-trait melee-damage and climb-failure percentages (Emaciated 40 % damage / 75 % climb fail, Underweight 80 % / 85 %, Very Underweight 60 % / 75 %) have no reader in this jar: a whole-jar scan for the five weight-trait fields finds them only in `IsoGameCharacter`, `IsoPlayer`, `IsoMovingObject`, `ClimbOverFenceState` and `ClimbSheetRopeState`, and `getClimbingFailChanceFloat` branches on Obese and Overweight alone. Overweight's "starting weight is 90" also disagrees with `applyWeightFromTraits`, which writes 95. Verify against `getClimbingFailChanceFloat @113-@153`, `applyWeightFromTraits @0-@100` and the melee damage path.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar player}}
{{Page version|42.20.4}}
{{Improve|Some traits are alphabetized and some not, sentence case and formatting is not entirely consistent with the most recent [[Help:Style guide|style guide]] updates.}}
[[File:Character creation 2.jpg|300px|thumb|right|The traits menu as of [[Build 41]].]]
'''Trait''' is a modifier, positive or negative, that is available to the [[player]] through direct choice when creating a character, occupation, or gameplay decisions.

== Overview ==
A variety of traits can be chosen during [[Player#Character Creation|character creation]] (indicated by a ''points'' value). Some traits are given with the choice of an [[occupation]]. Multiple presets can be saved and, thus, quickly loaded as a preset of an occupation and a combination of traits when creating a new character.

The “Points to Spend” needs to be a positive value or equal to zero. This means any positive traits beyond 8 points altogether need to be evened out by negative traits.

Traits categorized as “Mutually exclusive” cannot be chosen simultaneously (for example, [[File:trait_deaf.png]] [[Deaf]] cannot be chosen in combination with [[File:trait_hardofhearing.png]] [[Hard of Hearing]] or [[File:trait_keenhearing.png]] [[Keen Hearing]]).

Consider that choosing an occupation reduces the amount of available starting points that can be spent on traits.

Some traits can be [[Trait#Adaptive traits|gained or lost during gameplay]], depending on the player's activities.

A player's traits can be checked in “Character Info Window > Info”, which is opened with the {{Key|J}} key by default.

A character who start with a trait that gives them some previous experience in a skill will gain an experience boost.

'''Starting skill level and experience boost:'''
{{BugBox|The modifiers in-game for level 1, 2, and 3 are incorrect and show as 75%, 100% and 125% accordingly.|version=42.13.1}}
* Level 0 — 25% (default for all skills)
* Level 1 — 100% [[File:greenblits.png]]
* Level 2 — 133% [[File:greenblits.png]]&hairsp;[[File:greenblits.png]]
* Level 3+ — 166% [[File:greenblits.png]]&hairsp;[[File:greenblits.png]]&hairsp;[[File:greenblits.png]]

Major skill boosts can also be obtained by taking certain [[occupation]]s.

'''Note:''' there is a bug as of [[Build 41.78.16]] where the bonus for [[strength]] and [[fitness]] is shown, even if these are disabled, which is a default behavior that can be changed in the [[Custom Sandbox|sandbox]].{{Verify|verify if this is still present in latest Build 42 version.}}

== List of traits ==

=== Positives ===
{| class="wikitable theme-red sortable" style="text-align: center; width: 100%;"
|+
! class="unsortable" style="width: 2%;" | Icon
! style="width: 10%;" | Name
! style="width: 2%;" | Points
! class="unsortable" style="width: 34%;" | Description
! class="unsortable" style="width: 34%;" | Effects
|-
| [[File:trait_adrenalinejunkie.png]]
| id="traitAdrenalineJunkie" | [[Adrenaline Junkie]]
| -4
| ''Moves faster when highly panicked.''
| Adds a flat bonus of 0.20 or 0.25 for the character's base speed at Strong or Extreme Panic, which increases walking, running, and sprinting speed.
|-
| [[File:trait_fishing.png]]
| id="traitAngler" | [[Angler (trait)|Angler]]
| -4
| ''Knows the basics of fishing.''
| +1 Fishing<br> Knows how to make and fix a [[Fishing Rod|fishing rod]]<br> Improves [[foraging]].
|-
| [[File:trait_artisan.png]]
| id="traitArtisan" | [[Artisan]]
| -2
| ''Better at pottery and glass crafts.''
| +1 Glassmaking<br>+1 Pottery
|-
| [[File:trait_athletic.png]]
| id="traitAthletic" | [[Athletic]]
| -10
| ''Can run faster and longer without tiring.''
| +4 Fitness. +20% running/sprinting speed. -20% running/sprinting endurance loss from the trait itself.
|-
| [[File:trait_baseballplayer.png]]
| id="traitBaseballPlayer" | [[Baseball Player]]
| -4
| ''Has practice with a baseball bat and knows how to hit with precision.''
| +1 Long Blunt
|-
| [[File:trait_blacksmith.png]]
| id="traitBlacksmith" | [[Blacksmith Knowledge]]
| -6
| ''Can use an anvil to create metal items.''
| +1 Maintenance<br>+2 Blacksmithing
|-
| [[File:trait_brave.png]]
| id="traitBrave" | [[Brave]]
| -4
| ''Less prone to becoming panicked.''
| 30% panic except for night terrors and phobias.
|-
| [[File:trait_brawler.png]]
| id="traitBrawler" | [[Brawler]]
| -6
| ''Used to getting into trouble.''
| +1 Axe<br> +1 Long Blunt
|-
| [[File:trait_nightvision.png]]
| id="traitCatsEyes" | [[Cat's Eyes]]
| -3
| ''Better vision at night.''
| +20% better vision at night<br>Improves [[foraging]].
|-
| [[File:Trait crafty.png]]
| id="traitCrafty" | [[Crafty]]
| -3
| ''Increased XP gains for Crafting skills.''
| 130% XP for all crafting skills
|-
| [[File:trait_dextrous.png]]
| id="traitDextrous" | [[Dextrous]]
| -2
| ''Transfers inventory items quickly.''
| 50% inventory transferring time.
|-
| [[File:trait_eagleeyed.png]]
| id="traitEagleEyed" | [[Eagle Eyed]]
| -4
| ''Has a faster visibility fade and a higher visibility arc.''
| Character has a wider field of view<br>Improves [[foraging]].
|-
| [[File:trait_fasthealer.png]]
| id="traitFastHealer" | [[Fast Healer]]
| -6
| ''Recovers faster from injury and illness.''
| Does not apply to exercise fatigue. Recently inflicted injuries have less severity.
Including Scratches, Lacerations, Lodged Bullets, Deep wounds (with/without glass), Bites and Fractures. (Check [[Health]] for more details.)
|-
| [[File:trait_fastlearner.png]]
| id="traitFastLearner" | [[Fast Learner]]
| -6
| ''Increases XP gains.''
| 130% XP for all skills except Strength and Fitness.
|-
| [[File:trait_fastreader.png]]
| id="traitFastReader" | [[Fast Reader]]
| -2
| ''Takes less time to read books.''
| 130% reading speed.
|-
| [[File:trait_firstaid.png]]
| id="traitFirstAider" | [[First Aider]]
| -2
| ''Has a CPR and First Aid course certificate.''
| +1 First Aid
|-
| [[File:trait_fit.png]]
| id="traitFit" | [[Fit]]
| -6
| ''In good physical shape.''
| +2 Fitness.
|-
| [[File:trait_formerscout.png]]
| id="traitFormerScout" | [[Former Scout]]
| -6
| ''Knows how to pick wild berries and how to treat small injuries.''
| +1 First Aid<br> +1 Fishing<br> +1 Foraging <br> Knows how to make and fix a [[Fishing Rod|fishing rod]]<br> Improves [[foraging]].<br>Start a fire on campfires with [[Notched Plank|notched plank]] faster.
|-
| [[File:trait_gardener.png]]
| id="traitGardener" | [[Gardener]]
| -2
| ''Has basic agriculture knowledge.''
| Increases the [[player]]'s [[agriculture]] skill by 1<br> Improves [[foraging]].
|-
| [[File:trait_graceful.png]]
| id="traitGraceful" | [[Graceful]]
| -4
| ''Makes less noise when moving.''
| 60% footsteps sound radius.
|-
| [[File:trait_gymnast.png]]
| id="traitGymnast" | [[Gymnast]]
| -5
| ''Agile and discreet.''
| +1 Lightfooted<br> +1 Nimble
|-
| [[File:trait_handy.png]]
| id="traitHandy" | [[Handy]]
| -8
| ''Faster and stronger constructions.''
| +1 Carpentry <br> +1 Carving <br> +1 Maintenance <br> +1 Masonry <br> +100HP to all constructions. <br> Increases building speed (≈11%).
|-
| [[File:trait_herbalist.png]]
| id="traitHerbalist" | [[Herbalist]]
| -4
| ''Can find [[Medicinal Plants|medicinal plants]] and craft medicines and poultices from them.''
| +1 Foraging. Able to find herbal medicines, make poultices from them, and identify poisonous wild food. Improves [[foraging]].
|-
| [[File:trait_hiker.png]]
| id="traitHiker" | [[Hiker]]
| -5
| ''Used to surviving in the jungle.''
| +1 Foraging<br> +1 Trapping<br> Improves [[foraging]].
|-
| [[File:trait_hunter.png]]
| id="traitHunter" | [[Hunter]]
| -8
| ''Know the basics of hunting.''
| +1 Aiming<br> +1 Short Blade<br> +1 Sneaking<br> +1 Tracking<br> +1 Butchering<br> Improves [[foraging]].
|-
| [[File:trait_inconspicuous.png]]
| id="traitInconspicuous" | [[Inconspicuous]]
| -4
| ''Less likely to be spotted by zombies.''
| 50% chance of zombies spotting you.
|-
| [[File:trait_inventive.png]]
| id="traitInventive" | [[Inventive]]
| -2
| ''Has lower skill level requirements to research recipes from items or auto learn recipes.''
| Reduced auto-learn skill points by 1
|-
| [[File:trait_irongut.png]]
| id="traitIronGut" | [[Iron Gut]]
| -2
| ''Less chance to have food illness.''
| 50% chance of food illness. Food illness lasts shorter. Check [[Health]] for more details.
|-
| [[File:trait_cook.png]]
| id="traitCook" | [[Keen Cook]]
| -3
| ''Knows cooking recipes.''
| +2 Cooking<br>+1 Butchering<br> Improves [[foraging]].
|-
| [[File:trait_keenhearing.png]]
| id="traitKeenHearing" | [[Keen Hearing]]
| -6
| ''Larger perception radius.''
| 200% perception radius. Zombies that approach from behind will be visible much earlier.
|-
| [[File:trait_lighteater.png]]
| id="traitLightEater" | [[Light Eater]]
| -2
| ''Needs to eat less regularly.''
| 75% hunger.
|-
| [[File:trait_lowthirst.png]]
| id="traitLowThirst" | [[Low Thirst]]
| -2
| ''Needs to drink water less regularly.''
| 50% thirst.
|-
| [[File:trait_mason.png]]
| id="traitMason" | [[Mason]]
| -2
| ''Better at building stone and brick constructions.''
| +2 Masonry
|-
| [[File:trait_nutritionist.png]]
| id="traitNutritionist" | [[Nutritionist]]
| -2
| ''Can see the nutritional values of any food.''
| Allows the player to see the nutritional values of any food, even those that aren't packaged. Improves [[foraging]].
|-
| [[File:trait_organized.png]]
| id="traitOrganized" | [[Organized]]
| -4
| ''Increased container inventory capacity.''
| 130% capacity for all containers, including boxes, cupboards and cars
|-
| [[File:trait_outdoorsman.png]]
| id="traitOutdoorsman" | [[Outdoorsy]]
| -2
| ''Not affected by harsh weather conditions.''
| 10% chance of catching a cold. 1% or 1.25% chance of getting scratched/lacerated while walking or running through trees.<br>Improves [[foraging]].
|-
| [[File:trait_resilient.png]]
| id="traitResillient" | [[Resilient]]
| -4
| ''Less prone to disease. Slower rate of zombification.''
| 75% zombification progression rate, 45% chance of catching a cold, 80% cold strength and 50% cold progression speed.
|-
| [[File:trait_jogger.png]]
| id="traitRunner" | [[Runner]]
| -4
| ''Runner in the spare times.''
| +1 Sprinting
|-
| [[File:trait_tailor.png]]
| id="traitSewer" | [[Sewer]]
| -4
| ''+1 Tailoring''
| +1 Tailoring
|-
| [[File:trait_speeddemon.png]]
| id="traitSpeedDemon" | [[Speed Demon]]
| -1
| ''The fast driver.''
| 200% Gear switching speed, 115% top speed for all vehicles
|-
| [[File:trait_stout.png]]
| id="traitStout" | [[Stout]]
| -6
| ''Extra knockback from melee weapons and increased carry weight.''
| +2 Strength
|-
| [[File:trait_strong.png]]
| id="traitStrong" | [[Strong]]
| -10
| ''Extra knockback from melee weapons and increased carry weight.''
| +4 Strength, +40% knockback power (damage does not increase).
|-
| [[File:trait_target_shooter.png]]
| id="traitTargetShooter" | [[Target Shooter]]
| -5
|''+1 Aiming''
| +1 Aiming
|-
| [[File:trait_thickskinned.png]]
| id="traitThickSkinned" | [[Thick Skinned]]
| -8
| ''Less chance of scratches or bites breaking the skin.''
| Multiplies the chance of not being injured by a zombie attack by 1.3 (base 15% chance, modified by character's weapon skill). Additionally, alters the chance of clothes being damaged by walking through trees to 1 in 13.
|-
| [[File:Trait tinkerer.png]]
| id="traitTinkerer" | [[Tinkerer]]
| -4
|''+1 Maintenance''
| +1 Maintenance
|-
| [[File:trait_mechanics.png]]
| id="traitAmateurMechanic2" | [[Vehicle Knowledge]]
| -3
| ''Has a detailed knowledge of common and heavy vehicle models and their repairs.''
| +1 Mechanics, can repair standard and heavy-duty vehicles.
|-
| [[File:trait_needslesssleep.png]]
| id="traitWakeful" | [[Wakeful]]
| -3
| ''Needs less sleep.''
| -30% Fatigue increase rate, +10% Sleep efficiency
|-
| [[File:trait_whittler.png]]
| id="traitWhittler" | [[Whittler]]
| -2
| ''Can carve wood and bone items.''
| +2 Carving. Can craft [[Bone Fishing Hook]], [[Bone Needle|Bone Sewing Needle]], and sharpen animal bones<br> Improves [[foraging]].
|-
| [[File:trait_wildernessknowledge.png]]
| id="traitWildernessKnowledge" | [[Wilderness Knowledge|Bushcrafter]]
| -8
| ''Can find medicinal herbs and craft medicines and poultices from them, and make simple stone and bone tools. Start fires faster.''
| +1 Carving<br>+1 Foraging<br>+1 Knapping<br>+1 Maintenance<br> Improves [[foraging]].<br>Start a fire on campfires with [[Notched Plank|notched plank]] faster.
|}

=== Negatives ===
{| class="wikitable theme-red sortable" style="text-align: center; width: 100%;"
! class="unsortable" style="width: 2%;" | Icon
! style="width: 10%;" | Name
! style="width: 2%;" | Points
! class="unsortable" style="width: 34%;" | Description
! class="unsortable" style="width: 34%;" | Effect
|-
| [[File:trait_agoraphobic.png]]
| id = "traitAgoraphobic" | [[Agoraphobic]]
| +4
| ''Gets panicked when outdoors.''
| [[Panic]] increases when outdoors. [[Foraging]] search radius decreased.
|-
| [[File:trait_allthumbs.png]]
| id = "traitAllThumbs" | [[All Thumbs]]
| +2
| ''Transfers inventory items slowly.''
| 400% inventory transferring time.
|-
| [[File:trait_asthmatic.png]]
| id="traitAsthmatic" | [[Asthmatic]]
| +5
| ''Faster endurance loss.''
| 140% running/sprinting endurance loss. 130% increase in swing endurance lost.
|-
| [[File:trait_claustophobic.png]]
| id = "traitClaustrophobic" | [[Claustrophobic]]
| +4
| ''Gets panicked when indoors.''
| Panic increases in enclosed and cramped spaces; the smaller the environment, the greater the panic.
|-
| [[File:trait_clumsy.png]]
| id = "traitClumsy" | [[Clumsy]]
| +2
| ''Makes more noise when moving.''
| 120% footsteps sound radius (results in 144% footsteps sound area).
|-
| [[File:trait_conspicuous.png]]
| id = "traitConspicuous" | [[Conspicuous]]
| +4
| ''More likely to be spotted by zombies.''
| 200% chance of getting spotted by zombies.
|-
| [[File:trait_cowardly.png]]
| id = "traitCowardly" | [[Cowardly]]
| +2
| ''Especially prone to becoming panicked.''
| 200% panic except for night terrors and phobias.
|-
| [[File:trait_deaf.png]]
| id = "traitDeaf" | [[Deaf]]
| +12
| ''Can't hear sound.''
| The player can't hear any sound and can't listen to the radio; they can still watch TV with subtitles, but the dialogue won't be displayed on the screen.
|-
| [[File:trait_disorganized.png]]
| id = "traitDisorganized" | [[Disorganized]]
| +6
| ''Decreased container inventory capacity.''
| 70% capacity for all containers, including boxes and cupboards.
|-
| [[File:trait_emaciated.png]]
| id = "traitEmaciated" | [[Emaciated]]
| -
| ''Low strength, low endurance and prone to injury.''
| Is only present at weight 50 and less and will begin taking damage at weight 35. 40% melee damage. 75% chance to fail to climb a tall fence. 30% endurance regeneration. 20 more fall damage.
|-
| [[File:trait_weightloss.png]]
| id = "traitFastMetabolism" | [[Fast Metabolism]]
| +2
| ''Permanent tendency to lose weight. Starts with Low Weight trait.''
| Has a persistent tendency to lose weight, starting with a weight below 70 kg (154 lb).
|-
| [[File:trait_hemophobic.png]]
| id = "traitHemophobic" | [[Fear of Blood]]
| +5
| ''Panic when performing first aid on self, cannot perform first aid on others, gets stressed when bloody.''
| Gets stressed when he's bleeding, panics when administering first aid to himself, but only when the wound is bleeding; he can't perform a medical assessment on other players.
|-
| [[File:trait_feeble.png]]
| id="traitFeeble" | [[Feeble]]
| +6
| ''Less knockback from melee weapons. Decreased carrying weight.''
| -2 Strength, reduced carrying capacity to 9 (instead of the standard 12), decreases the chance to push zombies, does not affect melee weapon damage.
|-
| [[File:trait_hardofhearing.png]]
| id = "traitHardofHearing" | [[Hard of Hearing]]
| +4
| ''Smaller perception radius. Smaller hearing range.''
| With a smaller perception radius, the game audio becomes muffled.
|-
| [[File:trait_heartyappetite.png]]
| id = "traitHeartyAppetite" | [[Hearty Appetite]]
| +4
| ''Needs to eat more regularly.''
| 150% hunger. Gives a +3% bonus to packaged foods, mushrooms, berries, and animals for foraging.
|-
| [[File:trait_highthirst.png]]
| id = "traitHighThirst" | [[High Thirst]]
| +2
| ''Needs more water to survive.''
| Feel twice as thirsty as normal when dying of thirst, and the health bar drops faster.
|-
| [[File:trait_illiterate.png]]
| id="traitIlliterate" | [[Illiterate]]
| +10
| ''Cannot read books.''
| Cannot read any text except comic books, illustrated books, and HottieZ magazine.
Cannot write notes in notebooks and on survivor maps found; if there is anything written, it appears as: ???????
|-
| [[File:trait_obese.png]]
| id="traitObese" | [[Obese]]
| -
| ''Reduced running speed, very low endurance and prone to injury.''
| Is only present at weights 100 and above. Max fitness of 7 (while have this trait, losing it removes limitation). The trait itself reduce run speed and endurance. 120% chance to trip while run/sprint vaulting a low fence. 90% chance to trip from lunging zombies. 75% chance to climb a tall fence. 40% endurance regeneration. 20 more fall damage.
|-
| [[File:trait_out of shape.png]]
| id="traitOutofShape" | [[Out of Shape]]
| +6
| ''Low endurance, low endurance regeneration.''
| -2 Fitness
|-
| [[File:trait_overweight.png]]
| id = "traitOverweight" | [[Overweight]]
| -
| ''Reduced running speed, low endurance and prone to injury.''
| Max [[fitness]] of 9 (while have this trait, losing it removes limitation). The starting weight is 90 and is only present between weights 85 and 100. 1% slower running speed, 200% endurance loss. 110% chance to trip while run/sprint vaulting a low fence. 95% chance to trip by lunging zombies. 85% chance to climb a tall fence. 70% endurance regeneration.
|-
| [[File:trait_pacifist.png]]
| id = "traitPacifist" | [[Pacifist]]
| +5
| ''Less effective with weapons.''
| 75% of skill XP for [[Short Blade|short blade]], [[Long Blade|long blade]], [[Short Blunt|small blunt]], [[Long Blunt|long blunt]], [[Axe (skill)|axe]], [[spear]], [[maintenance]] and [[aiming]].
|-
| [[File:trait_hypercondriac.png]]
| id = "traitPronetoIllness" | [[Prone to Illness]]
| +4
| ''More prone to disease. Faster rate of zombification.''
| 125% progression rate of zombification. 170% chance of catching a cold, 120% cold strength, and 150% cold progression speed.
|-
| [[File:trait_weak.png]]
| id="traitPuny" | [[Puny]]
| +10
| ''Less knockback from melee weapons. Decreased carrying weight.''
| -5 Strength,-40% knockback power (damage does not decrease).
|-
| [[File:trait_insomniac.png]]
| id = "traitRestlessSleeper" | [[Restless Sleeper]]
| +6
| ''Slow loss of tiredness while sleeping.''
| Recovers slowly from fatigue while sleeping, the chance of waking up to a zombie banging on doors or windows is higher.
|-
| [[File:trait_shortsighted.png]]
| id = "traitShortSighted" | [[Short Sighted]]
| +2
| ''Small view distance. Slower visibility fade.''
| Anything more than 4 tiles away becomes blurred. The effect can be removed using any type of eyeglasses, whether dark, round, square...
|-
| [[File:trait_needsmoresleep.png]]
| id = "traitSleepyhead" | [[Sleepyhead]]
| +4
| ''Needs more sleep.''
| +30% increase in fatigue -10% decrease in sleep effectiveness; needs to sleep at least 12 hours a day to recover.
|-
| [[File:trait_slowhealer.png]]
| id = "traitSlowHealer" | [[Slow Healer]]
| +3
| ''Recovers slowly from injuries and illness.''
| Does not apply to exercise fatigue. Recently inflicted injuries have more severity.
Including Scratches, Lacerations, Lodged Bullets, Deep wounds (with/without glass), Bites, and Fractures. (Check [[Health]] for more details.)
|-
| [[File:trait_slowlearner.png]]
| id = "traitSlowLearner" | [[Slow Learner]]
| +6
| ''Decreased XP gains.''
| 70% XP in all skills except [[strength]] and [[fitness]].
|-
| [[File:trait_weightgain.png]]
| id = "traitSlowMetabolism" | [[Slow Metabolism]]
| +2
| ''Permanent tendency to gain weight. Starts with High Weight trait.''
| Has a persistent tendency to gain weight, starting with a weight above 95 kg (209 lb).
|-
| [[File:trait_slowreader.png]]
| id = "traitSlowReader" | [[Slow Reader]]
| +2
| ''Takes longer to read books.''
| 70% reading speed.
|-
| [[File:trait_smoker.png]]
| id = "traitSmoker" | [[Smoker]]
| +3
| ''Stress and unhappiness decrease after smoking tobacco. Unhappiness rises when tobacco is not smoked.''
| [[Stress]] will constantly slowly rise. Smoking [[cigarettes]] will lower the stress level.
|-
| [[File:Trait_sundaydriver.png]]
| id = "traitSundayDriver" | [[Sunday Driver]]
| +1
| ''The very slow driver.''
| Accelerates vehicles 40% slower, has a maximum speed of 30 mph (50 km/h). If the easy-to-use option is enabled in the sandbox settings, the speed is not limited to 30 mph (50 km/h).
|-
| [[File:trait_thinskinned.png]]
| id = "traitThinskinned" | [[Thin-skinned]]
| +8
| ''Increased chance of scratches, lacerations, or bites breaking the skin.''
| Multiplies the chance of not being injured by a zombie attack by 0.7 (base 15% chance, modified by character's weapon skill). Additionally, alters the chance of clothes being damaged by walking through trees to 1 in 3.
|-
| [[File:trait_underweight.png]]
| id="traitUnderweight" | [[Underweight]]
| -
| ''Low strength, low endurance and prone to injury.''
| Starting weight is 70 and is only present between weights 65 and 75. 80%x melee damage. +10% chance to trip by while run/sprint vaulting a low fence or from lunging zombies. 85%x chance to fail a tall fence climb.
|-
| [[File:trait_unfit.png]]
| id = "traitUnfit" | [[Unfit]]
| +10
| ''Very low endurance, very low endurance regeneration.''
| -4 [[fitness]]
|-
| [[File:trait_very underweight.png]]
| id = "traitVeryUnderweight" | [[Very Underweight]]
| -
| ''Very low strength, very low endurance and prone to injury.''
| Is only present between weights 50 and 65. 60% melee damage. 20% higher chance to trip by while run/sprint vaulting a low fence or from lunging zombies. 75% chance to fail a tall fence climb. 10% more fall damage.
|-
| [[File:trait_weakstomach.png]]
| id = "traitWeakStomach" | [[Weak Stomach]]
| +2
| ''Higher chance to have food illness.''
| 200% chance of food illness. Food illness lasts longer. Check [[Health]] for more details.
|}

=== Occupation exclusive traits ===
{| class="wikitable theme-red" style="text-align: center; width: 100%;"
! class="unsortable" style="width: 2%;" | Icon
! style="width: 10%;" | Name
! style="width: 2%;" | Occupation
! class="unsortable" style="width: 34%;" | Description
! class="unsortable" style="width: 34%;" | Effect
|-
| [[File:trait_desensitized.png]]
| id="traitAgoraphobic" | [[Desensitized]]
| [[Veteran]]
| ''Does not reach states of panic.''
| 0% [[panic]] from all sources except nightmares<br> 200% chance to have nightmares.
|-
| [[File:trait_axeman.png]]
| [[Ax-pert]]
| [[Lumberjack]]
| ''Better at chopping trees. Faster axe swing.''
| Swing axes 25% faster (combat and tree cutting).
|-
| [[File:trait_burglar.png]]
| [[Burglar (trait)|Burglar]]
| [[Burglar]]
| ''Can hotwire vehicles, less chance of breaking the lock of a window.''
| Can hotwire vehicles and has less chance of breaking the lock of a window when forced open.
|-
| [[File:trait_blacksmith.png]]
| [[Blacksmith Knowledge (occupation trait)|Blacksmith Knowledge]]
| [[Blacksmith (occupation)|Blacksmith]]
| ''Can use an anvil to create metal items.''
| +1 [[Maintenance]], +2 [[Blacksmithing]]
|-
| [[File:trait_cook.png]]
| [[Keen Cook (occupation trait)|Keen Cook]]
| [[Chef]]
| ''Knows how to cook.''
| Improves [[foraging]].
|-
| [[File:trait_mechanics.png]]
| <span id="AmateurMechanic">[[Vehicle Knowledge (occupation trait)|Vehicle Knowledge]]</span>
| [[Mechanic]]
| ''Familiar with the maintenance and repair of all vehicle models on the roads of Kentucky.''
| +3 [[Mechanics]], can repair all vehicle types without having to read any [[recipe magazines]].
|-
| [[File:trait_nightowl.png]]
| id = "traitNightOwl" | [[Night Owl]]
| [[Security Guard|Security guard]]
| ''Requires little sleep.''<br>''Stays extra alert even when sleeping.''
| Recovers from [[tired]]ness quicker while [[sleep]]ing.
Doesn't reduce sleep duration.
|}

== Removed/future traits ==
{| class="wikitable theme-red sortable" style="text-align: center; width: 100%;"
|-
! class = "unsortable" style = "width: 2%;" | Icon
! style = "width: 10%;" | Name
! style = "width: 6%;" | Type
! style = "width: 12%;" | Mutually exclusive
! style = "width: 2%;" | Points
! class = "unsortable" style = "width: 34%;" | Description
! class = "unsortable" style = "width: 34%;" | Effect
|-
| [[File:trait_poorpassenger.png]]
| id="" | [[Motion Sensitive]]
|Negative
| -
| <span style="color: #2d9600; font-weight: bold;">+4</span>
| ''Gets motion sickness in a moving vehicle.''
| Applies motion sickness if in a moving vehicle, similar to the normal sickness moodle
|-
| [[File:trait_brooding.png]]
| [[Brooding]]
| Negative
| -
| <span style="color: #2d9600; font-weight: bold;">+2</span>
| ''Recovers slower from bad moods.''
| -
|-
| [[File:trait_hypercondriac.png]]
| [[Hypochondriac]]
| Negative
| -
| <span style="color: #2d9600; font-weight: bold;">+2</span>
| ''May develop infection symptoms without having been infected.''
| ''Any'' scratch or laceration (and possibly other injuries) may cause the character to gain Sickness and Stress [[moodles]] as if they had caught the [[Knox Infection]].
|-
| [[File:trait_lucky.png]]
| [[Lucky]]
| Positive
| [[Unlucky]]
| <span style="color: #7f0000; font-weight: bold;">-4</span>
| ''Sometimes things just go your way.''
| +10% chance of finding loot. -5% chance of failing item repairs. Affects [[Foraging|search mode]].<br>Was not available in multiplayer.
|-
| [[File:trait_unlucky.png]]
| [[Unlucky]]
| Negative
| [[Lucky]]
| <span style="color: #2d9600; font-weight: bold;">+4</span>
| ''What could go wrong for you, often does.''
| -10% chance of finding rare loot. +5% chance of failing item repairs. Affects [[Foraging|search mode]].<br>Was not available in multiplayer.
|-
| [[File:trait_patient.png]]
| [[Patient]]
| Positive
| [[Short Tempered]]
| <span style="color: #7f0000; font-weight: bold;">-4</span>
| ''Less like to get angry.''
| -
|-
| [[File:trait_shorttemper.png]]
| [[Short Tempered]]
| Negative
| [[Patient]]
| <span style="color: #2d9600; font-weight: bold;">+4</span>
| ''Quick to anger.''
| -
|-
| [[File:trait_lightdrinker.png]]
| [[Light Drinker]]
| Negative
| [[Hardened Drinker]]
| <span style="color: #2d9600; font-weight: bold;">+2</span>
| ''Gets drunk quickly.''
| 400% drunkness from alcohol.
|-
| [[File:trait_hardeneddrinker.png]]
| [[Hardened Drinker]]
| Positive
| [[Light Drinker]]
| <span style="color: #7f0000; font-weight: bold;">-3</span>
| ''Doesn't get drunk easily.''
| 30% drunkness from alcohol.
|-
| [[File:trait_crackshot.png]]
| [[Marksman]]
| Hobby
| -
| 0
| ''Improved gun accuracy. Quicker reload.''
| Whilst not completely commented-out like other traits here, Marksman is currently no longer active. It previously was automatically granted to [[Police Officer|police officer]]s, and granted a significant boost to weapon accuracy ''independent'' of [[aiming]] skill.
|-
| [[File:trait_talkative.png]]
| [[Gift Of The Gab]]
| Positive
| -
| ?
| ''Extra high charisma. Better chance of currying favor from NPCs.''
| -
|}

== Adaptive traits ==
Some traits can be gained or lost during gameplay, but note that losing a negative trait during the game will not grant the lost skill points back. For example, the [[File:trait_overweight.png]] [[High Weight]] trait is gained if the player surpasses a weight of 85 and is lost by reaching a weight below 85. Losing the trait again will not improve the [[Fitness]] skill level.

=== Strength traits ===
Negative traits [[File:trait_feeble.png]] [[Weak]] and [[File:trait_weak.png]] [[Puny]] can be removed by leveling up [[strength]].<br>
Positive traits [[File:trait_stout.png]] [[Stout]] and [[File:trait_strong.png]] [[Strong]] can be gained by leveling up [[strength]].

{| class="wikitable theme-red sortable"
|-
! Strength level
| 0-1
| 2-4
| 5
| 6-8
| 9-10
|-
! Trait
| [[File:trait_weak.png]] [[Puny]]
| [[File:trait_feeble.png]] [[Weak]]
| None
| [[File:trait_stout.png]] [[Stout]]
| [[File:trait_strong.png]] [[Strong]]
|}

=== Fitness traits ===
Negative traits [[File:trait_out_of_shape.png]] [[Out of Shape]] and [[File:trait_unfit.png]] [[Unfit]] can be removed by leveling up [[fitness]].<br>
Positive traits [[File:trait_fit.png]] [[Fit]] and [[File:trait_athletic.png]] [[Athletic]] can be gained by leveling up [[fitness]].

{| class="wikitable theme-red sortable"
|-
! Fitness level
| 0-1
| 2-4
| 5
| 6-8
| 9-10
|-
! Trait
| [[File:trait_unfit.png]] [[Unfit]]
| [[File:trait_out_of_shape.png]] [[Out of Shape]]
| None
| [[File:trait_fit.png]] [[Fit]]
| [[File:trait_athletic.png]] [[Athletic]]
|}

=== Weight traits ===
Negative traits [[File:trait_obese.png]] [[Very High Weight]] and [[File:trait_overweight.png]] [[High Weight]] can be removed by losing weight or obtained by gaining weight.<br>
Negative traits [[File:trait_underweight.png]] [[Low Weight]], [[File:trait_very_underweight.png]] [[Very Low Weight]], and [[File:trait_emaciated.png]] [[Emaciated]] can be removed by gaining weight or obtained by losing weight.

{| class="wikitable theme-red sortable"
|-
! Player weight
| 35 - 50
| 51 - 65
| 66 - 75
| 76 - 85
| 86 - 100
| 101 - 130
|-
! Trait
| [[File:trait_emaciated.png]] [[Emaciated]]
| [[File:trait_very_underweight.png]] [[Very Low Weight]]
| [[File:trait_underweight.png]] [[Low Weight]]
| None (ideal weight)
| [[File:trait_overweight.png]] [[High Weight]]
| [[File:trait_obese.png]] [[Very High Weight]]
|}

''Note: once a player reaches a weight of 35 kilograms and is still in a deficit, no more weight can be lost, but instead their health will deplet at a rather fast pace. Similarly, reaching 130 kilograms and still being in a surplus, no more weight can be gained. However, this has no effect on their health.''

=== Panic traits ===
Panic recovery speed is increased each day, capping at 150 days.

Panic resistance is not affected.

[[File:trait_agoraphobic.png]] [[Agoraphobic|Agoraphobia]] will eventually no longer increase panic because the character will recover from panic quicker than the trait adds panic.
However, the trait is still there. When a player is outside, the recovery speed from panic is slower.

[[File:trait_claustophobic.png]] [[Claustrophobic|Claustrophobia]] will still make the player's panic depending on the size of the room. On a new character, the limit for a sealed room seems to be 63 floor tiles, at which point the player's panic gain stagnates. This seems to work for any room shape, as long as the floor tiles are not interrupted in some way (doors, fences, etc.). Furniture does not seem to impede this. It is useful to note that this number will decrease based on the player's acclimatization to panic gain.

(The panic recovery speed is constantly fighting against [[File:trait_agoraphobic.png]] [[Agoraphobic|Agoraphobia]] and [[File:trait_claustophobic.png]] [[Claustrophobic|Claustrophobia]].)

== Gallery ==
<gallery>
File:trait_assertive.png|Unused {{Code|assertive}} icon, present in the game files.
File:trait_cheerful.png|Unused {{Code|cheerful}} icon, present in the game files.
File:trait_depressed.png|Unused {{Code|depressed}} icon, present in the game files.
File:trait_despairing.png|Unused {{Code|despairing}} icon, present in the game files.
File:trait_intelligent.png|Unused {{Code|intelligent}} icon, present in the game files, slightly different shade of [[Fast Learner]].
File:trait_kindhearted.png|Unused {{Code|kindhearted}} icon, present in the game files.
File:trait_nervous.png|Unused {{Code|nervous}} icon, present in the game files.
File:trait_skinney.png|Unused {{Code|skinney}} icon, present in the game files, slightly different shade of [[Hiker]].
File:trait_shifty.png|Unused {{Code|shifty}} icon, present in the game files.
File:trait_unstable.png|Unused {{Code|unstable}} icon, present in the game files.
File:trait_weakwilled.png|Unused {{Code|weakwilled}} icon, present in the game files.
</gallery>

== Trivia ==
* Similar to the [[First Aid Kit|first aid kit]], the [[File:trait_firstaid.png]] [[First Aider]] trait has its icon changed from a brown cross to green, after issues other games had with the depiction of the Red Cross. Old image: [[File:trait_firstaid-old.png]].

== See also ==
* {{ll|Moodles}}
* {{ll|Skills}}

== Navigation ==
{{Navbox stats|traits}}

{{ll|Category:Character}}
{{ll|Category:Traits|&#32;}}
```
