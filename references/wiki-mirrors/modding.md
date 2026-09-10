# Wiki mirror — Modding

**Source:** https://pzwiki.net/wiki/Modding
**Fetched:** 2026-09-09
**Wiki page version:** 42.20.4
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- Modding hub: policy, communities, and the index of modding fields (Scripts, Lua API, Java, modeling, texturing, mapping, translation) with the tool page for each. Stamped 42.20.4.
- Policy points that bound our mod: TIS may ship any feature regardless of existing mods; modders must warrant original or properly licensed work; no paywalled or donor-exclusive mods, though commissioned work is allowed provided access is not sold per user.
- Every entry point we need is one hop from here: Mod structure, Game files, File formats, Debug mode, Startup parameters, Mod optimization, Procedural distributions, PZ API Documentation (ScriptsDocs + LuaDocs).
- Field notes for our pillars: Scripts are no-code item definitions (ZedScripts VSCode extension); the Lua API is Kahlua, a Java Lua 5.1, with Umbrella typestubs plus Lua object / Lua event / Java object / Decompiling game code; Java modding means hand-swapping jar classes and is not Workshop-distributable the normal way.
- Carries a dated notice (last updated 2025-12-11) pointing at TIS's B42 unstable-MP modding-migration guides, with off-forum copies for anyone without a TIS forum account — the relevant pointer for our MP work.
- Drift note: the hand excerpt this file replaces (retrieved 2026-09-13, filed as `modding-hub.md`) also captured a 42.20.x modding-news section the live page no longer carries — `loadstring` removal after a public security report, `getFileWriter` extension limits, new faction/foraging sync methods, the `RequestMedicalCheck`/`AcceptedMedicalCheck` events, `language.txt` -> `language.json`. The first two survive in `docs/modding/README.md`; the rest are in git history only.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar modding}}
{{Page version|42.20.4}}
{{About|an overview about modding|PZwiki project|PZwiki:Project Modding}}
[[File:SpiffosWorkshop.png|link=https://steamcommunity.com/app/108600/workshop/|frame|right|Spiffo's Workshop is the home of [[Project Zomboid]] mods on [[Steam]]]]
Modding is the process of creating new content by creating [[mods]] for a game. For Project Zomboid, modding is a natively integrated part of the game with a mod manager and an API to allow modders to create a various quantity of content, from simple items to complex systems. Mods are usually uploaded to the [[Spiffo's Workshop]] which serves as the official method for sharing mods with the community.

== Latest information on MP unstable release ==
{{Main|TIS Modding Guides#Build 42 MP unstable release}}
''Last updated: 11th of December 2025''

The Indie Stone has recently released an ''unstable'' version of Project Zomboid which adds back multiplayer in the game. They provided the modding community with modding instructions to applying the new networking changes to existing mods that you can find [[forums:topic/88499-modding-migration-guide-4213/|here]]. If you don't have a TIS Forum account to download them, you find copies of these files [[github:pz-wiki-modding/Archive.Project-Zomboid-Modding/tree/main/TIS guides/B42 unstable MP|here]].

== Terms & Conditions ==
By playing Project Zomboid, you agree to the '''[[pz:blog/support/terms-conditions/|Terms & Conditions]]'''.

By modding Project Zomboid, you also agree with the '''[[pz:blog/modding-policy/|Modding Policy]]'''.

=== Key restrictions ===
* The Indie Stone reserves the right to implement any features in the game, irrespective of whether mods exist that accomplish the same goal.
* Modders are solely responsible for their mod, including (but not limited to) compliance with any hosting platforms (such as Steam Workshop). They are also responsible for obtaining third party consents for any third party materials in the mod. Legally, we have to ask that modders to ‘represent and warrant’ (i.e., promise legally) that their mod is their own original work and any third party contents are fully and properly licensed by the modder.
* Creation of mods is subject to our [https://projectzomboid.com/blog/modding-policy/ modding policy], which may be updated from time to time with any technical requirements regarding how PZ mods must work.
* Project Zomboid modders are free to receive monetary/gift donations from the players who use their releases, and appreciate the time and effort put into them. However, having mods created exclusively for those who choose to donate (or separate ‘in-mod’ content and bonuses) is not allowed. Mod creators cannot sell modifications to Project Zomboid.

== Commissions ==
Modders may choose to provide their skills and services through commissions, but with that comes a lot of responsibility.

If you're instead looking to commission work (have a mod made), and need advice, see [[Mods#Commissions|Commissioning Mods]].

As per the official Terms & Conditions (Section 2.4. Commercialisation) modders are in fact allowed to sell their services / create commissioned work, provided access to the mod and its content is not sold on an individual basis.

The advice below is not part of the TOS, nor legal advice, merely points to consider before going forward as a modder-for-hire:
* You should learn the ins and outs of modding before offering your services. The Zomboid API is fairly unique/niche.
* Have a portfolio ready to show. This can be as simple as your workshop page, and help build trust.
* Maintain transparency with pricing, timelines, and deliverables. Miscommunications cost time.
* Requesting payment upfront might appear to safeguard your time but it also comes with a lot more responsibility.

== Communities ==
Different communities exist to get help with modding, be it installing or debugging mod problems or creating mods, maps, tiles, etc.:
* [https://discord.gg/theindiestone Official Discord] – check out the '''Workshop''' category to get help on installing mods, problems with mods, or developing mods.
* [[PZ Modding Community]] – provides help on coding, modeling, animating and more.
* [[Unofficial PZ Mapping Discord]] – provides help on mapping and tile making.
* [[Unofficial PZ Animation Discord]] - provides help on cinematic animations and [[Rendering|renders]].

=== Modding Projects ===
{{Main|Modding projects}}
Various projects are created and handled by the community in relation to Project Zomboid modding. It varies from APIs, debug tools, to complete software development. Communities were also created to focus on modding Project Zomboid. You can contribute to some of these projects or communities directly or indirectly.

== How to get started ==
You can learn more in detail how to get started with modding in the [[getting started with modding]] page, which will also teach you about various tools for different modding fields. Depending on the type of modding you are interested in, the [[#Modding fields]] will provide you with the necessary resources to get started as well as links to some important pages per modding fields.

== Modding fields ==
Modding is split in different fields, each with their own tools and creation process. For a few general resources on modding that you will need to know regardless of the field you are working on:
* [[Mod structure]] - Explains a mod files structure.
* [[Game files]] - Explains Project Zomboid's file structure.
* [[File formats]] - Documentation of file formats used by the game.
* [[Debug mode]] - Explanations of how to run the game in the debug (developer) mode and how to use it.
* [[Startup parameters]] - Startup parameters to launch the game with.
* [[Mod optimization]] - Learn various tips, tricks and good habits that will improve your mods performances.
* [[Procedural distributions]] - List and explanations of procedural distributions.
* [[PZ API Documentation]] - An in-depth documentation of different API elements for modding such as [[Scripts]], [[Lua (API)]], [[Mapping]], [[Translation]] etc.

Below is a list of all the modding fields with a brief description of what they involve and links to the relevant pages:
{| class="wikitable theme-blue sortable" style="text-align: left;
|+ style="white-space:nowrap" | Modding fields
|-
! Field !! Description !! Important pages
|-
| [[Scripts]]
([[:Category:Scripts]])
| Allow to add items in the game with simple parameters which can be edited in any text editor. No programming knowledge is needed.
|
* [[ZedScripts]] - a [[Visual Studio Code|VSCode]] extension to help working with scripts.
* [[PZ API Documentation]] - provided an in-depth ScriptsDocs.
|-
| [[Lua (API)|Lua API]]
([[:Category:Lua (API)]])
| Allows modders to program functionalities via a Java implementation of Lua called Kahlua which enables Lua scripts to run within Java programs. It bases itself on [https://www.lua.org/manual/5.1/ Lua 5.1] with a few differences and allows the use of exposed Java class and methods from Lua scripts.
|
* [[Visual Studio Code]] and [[Umbrella (modding)|Umbrella]] - the perfect tools to work with Lua programming for Project Zomboid.
* [[Lua (language)]] to learn how to code with the Lua programming language.
* [[Lua object]] – a list of available Lua Objects to be used by modders.
* [[Lua event]] – a full list of available Events to hook on.
* [[Java object]] – a list of informations about some Java objects which can be used with the Lua API.
* [[Java documentation]] - a list of external links to the Java documentation of game.
* [[Decompiling game code]] - a guide to decompiling the Java to better understand how the game works.
* [[LuaDocs]]
|-
| [[Java]]
([[:Category:Java]])
| Involves modifying the Java game code directly and the manual installation of the Java files to modify deep game functionalities. It is not recommended for beginners as it requires a good knowledge of Java and programming in general.
|
* [[Decompiling game code]] - a guide to decompiling the Java to better understand how the game works.
* [[IntelliJ IDEA]] - IntelliJ IDEA is an IDE specialized for Java development.
|-
| [[Modeling]]
| Creating 3D models to be used in item making, vehicle making or renders.
|
* [[Creating custom animations]]
* [[Creating a hair mod]]
* [[Creating a clothing mod]]
|-
| [[Texturing]]
| Creating textures to be applied on 3D models or to create 2D tiles.
|
|-
| [[Rendering]]
| Creating 2D images from 3D models to be used in various medias in-game such as [[fliers]].
|
* [[Character rigs]] - character rigs which can be used to create renders of characters in various poses.
|-
| [[Animation]]
([[:Category:Animation]])
| Used to create new animations for characters to visually do certain actions. It involves knowledge of 3D softwares for animating but also a small bit of XML programming required to get your animation in-game.
|
* [[Character rigs]] - character rigs which can be used to create animations of characters.
|-
| [[Mapping]]
([[:Category:Mapping]])
| Create new locations, buildings and general environments in the form of a map for users to play on.
|
* [[map.info]] - Definition of the file used to define the map informations.
* [[Tiledefs used by mods]] - List of tiledef IDs which are already used by other mods.
* [[Adding new tiles]] - Guide to adding new tiles.
* [[Tile properties]] - Explanation of [[tile]] properties.
* [[Room definitions and item spawns]] - Explanation of room definitions, used mainly for loot distribution.
* [[Vehicle zones]] - Explanation of vehicle zones.
|-
| [[Translations]]
| Translating the game or mods to various languages.
|
* [[PZ API Documentation]] - provides an in-depth documentation of the available language codes and translation files.
|}

== Modding guides ==
Each [[#Modding fields]] will contain links to their respective appropriate guides, but there are also some more general guides which are too general to be linked in a specific field, which will be listed below. You can also find internal wiki guides in the category [[:Category:Modding guides|Modding guides category]].

Unlisted external guides are listed below:
{| class="wikitable theme-blue sortable" style="text-align: center;
|+ style="white-space:nowrap" | External tutorials
|-
! Tutorial !! Type !! Description !! Author !! Last updated
|-
| [[Sit-Down Sunday]]
| Modding presentations
| Modders teaching others about their modding and game dev knowledge in relation to PZ modding.
| [[PZ Modding Community]]
| {{#dateformat:2026-08-02|ymd}}
|-
| [https://www.youtube.com/playlist?list=PL91PT-Vd7Vhp_eBA8pE4hCXPcrxHWgr_E PZ Modding Video Guides]
| General guide
| Video guides for modding Project Zomboid, covering various aspects of modding.
| [[User:SirDoggyJvla|SimKDT]]
| {{#dateformat:2026-03-07|ymd}}
|-
| [https://github.com/demiurgeQuantified/PZModdingGuides PZ Modding Guides]
| General guide
| A collection of guides and documentation for modding Project Zomboid.
| [[User:Albion|Albion]]
| {{#dateformat:2025-05-18|ymd}}
|-
| [https://www.youtube.com/watch?v=yFMLmgM20xc Project Zomboid B42 - How to Create a Mod]
| Item creation
| A short video tutorial explaining how to create an item mod for Project Zomboid.
| Rainmaker
| {{#dateformat:2025-04-23|ymd}}
|-
| [https://steamcommunity.com/sharedfiles/filedetails/?id=3060255898 How to create Custom Firearm with working muzzle/attachments]
| Item creation
| A guide on how to create a custom firearm with working muzzle and attachments.
| Nik
| {{#dateformat:2024-06-29|ymd}}
|-
| [https://steamcommunity.com/sharedfiles/filedetails/?id=2474838710 How to change Zomboid's in-game music and sound effects]
| Sound
| A guide on how to change the in-game music and sound effects of Project Zomboid.
| Sokolov
| {{#dateformat:2024-04-02|ymd}}
|-
| [https://github.com/MrBounty/PZ-Mod---Doc PZ Mod Documentation]
| General guide
| A collection of guides and documentation for modding Project Zomboid.
| [[User:MrBounty|MrBounty]]
| {{#dateformat:2023-08-25|ymd}}
|-
| [https://github.com/FWolfe/Zomboid-Modding-Guide FWolfe's Modding Guide] (WIP)
| General guide
| A comprehensive guide to modding Project Zomboid, covering various aspects of modding. However a lot of the information is outdated or better explained by the official wiki. Good pratices are notably way more up-to-date than the wiki. The guide is incomplete on a lot of aspects and now inactive.
| Fenris Wolf
| {{#dateformat:2023-01-22|ymd}}
|-
| [https://www.youtube.com/watch?v=-yrmCAwzTbY Full Project Zomboid Mod Tutorial - Start to Finish]
| Item creation
| A 2 hour and a half long step-by-step video tutorial on how to add a new item to Project Zomboid, including creating an icon, adding it to the game, testing it and uploading it to the Steam Workshop.
| W. Patrick
| {{#dateformat:2022-12-13|ymd}}
|-
| [https://theindiestone.com/forums/index.php?/topic/28633-complete-vehicle-modding-tutorial/ Complete Vehicle Modding Tutorial]
| Vehicle making
| A forum post which details how to create vehicles. While a bit outdated, it still covers various aspects of vehicle making well.
| tubetarakan
| {{#dateformat:2020-05-04|ymd}}
|}

== External resources ==
{| class="wikitable theme-blue sortable" style="text-align: center;
|+ style="white-space:nowrap" | External resources
|-
! Resource !! Description !! Author !! Last updated
|-
| [https://discord.com/channels/136501320340209664/1070852229654917180 Mod Resources (Official Discord - Thread The Under Mod Development Channel)]
| A thread on the official Discord server that contains a list of resources for modding Project Zomboid, including links to resources, tools, and other useful information.
| Glytch3r and more
| {{#dateformat:2025-07-04|ymd}}
|}

=== General additional modding resources ===
* [https://discord.com/channels/136501320340209664/279303619277488128/864229655867031572 Photoshop Masks used for making and editing tile sprites, a link to a post on TIS Discord with the file]
* [https://github.com/Poltergeistzx/Project-Zomboid/blob/main/docs/TimedActions%20Flow%20Chart.pdf A flow chart for the timed actions]
* [https://github.com/Konijima/PZ-Community-API/tree/master/Contents/mods/CommunityAPI/media/lua/client/SpawnerAPI  SpawnerAPI: Allows for pending the spawns of vehicles, items, zombies in order to spawn things anywhere in the world. Upon loading the cell in question the item becomes spawned in]
* [https://discord.com/channels/136501320340209664/232196827577974784/891769429543759883 How to spawn loot on specific zombie outfit corpses: a link to a post on TIS Discord explaining how]
* [https://www.youtube.com/watch?v=iv7N7gmowWU WordZed tutorial on YouTube]
* [https://theindiestone.com/forums/index.php?/topic/28633-complete-vehicle-modding-tutorial/  Complete Vehicle Modding Tutorial on TIS forum]
* [https://github.com/Konijima/PZ-Community-API/blob/master/Contents/mods/CommunityAPI/media/lua/shared/CommunityAPI/IsoUtils.lua isoRangeScan: This is a utility function meant for large-scale scans of isoGridSquares around a given IsoObject. The scans are done fractally – that is to say, from a center (or centers) outward to fill a larger area.]

== Navigation ==
{{Navbox modding}}

{{ll|Category:Modding|&#32;}}
{{ll|Category:Modding}}
```
