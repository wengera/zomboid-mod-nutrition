# Wiki mirror — Mod_structure

**Source:** https://pzwiki.net/wiki/Mod_structure
**Fetched:** 2026-09-10
**Wiki page version:** 42.20.0
**License:** CC BY-NC-SA 3.0 — attribution: PZwiki contributors

## Digest

- **The B42 shape.** A mod folder holds a `common/` folder plus one or more version folders
  `42[.x[.y]]/`, each with its own `media/` and its own `mod.info`; a B41 flat `media/` may sit
  beside them and does not clash, because B42's tree is one level deeper. "At least one
  versioning or a common folder is needed for the mod to be recognized in-game."
- **The load order the page states** — and the reason this page is mirrored: *"These folders
  load with the following order: 1. Common folder. 2. Closest versioning folder to the game
  version (**overwrites** common files which are present in it)."* This is the merge rule our
  own datasets deliberately do not assert; it is **W**, unconfirmed against 42.20.4 code or a
  run, and it is open question 1 of
  [`docs/mods-survey/nutrition-mods.md`](../../docs/mods-survey/nutrition-mods.md).
- **Minor versions are dropped from the folder name**: `42.1.5` is treated as `42.1`, `42.0.5`
  as `42.0`, `42` as `42.0`. Our `tools/mod_lint.py` `version_dirs()` instead tuple-sorts three
  part names as themselves, which is a live discrepancy on the one corpus mod that ships a
  three-part folder (`2503622437` Skill Recovery Journal, `42.20.1`).
- **Duplicate copies clash by mod id.** The same `id=` under `Zomboid/mods/`, under
  `Zomboid/Workshop/…/Contents/mods/` and under `steamapps/workshop/content/108600/` overwrite
  one another — the page's repeated warning, and the reason our harness copies a mod into a
  per-run cache instead of loading it in place.
- **Media subfolders** are typed by modding field: `lua` (`client`/`server`/`shared`),
  `scripts`, `clothing`, `models_X`, `textures`, `ui`, `sound`, `anims_X`, `AnimSets`, `maps`,
  `texturepacks`. `.bank` sound files cannot be loaded from or overwritten by a mod.

## Wikitext

```wikitext
{{LangSwitch}}
{{Navbar modding}}
{{Page version|42.20.0}}
{{About|modding structure of Project Zomboid|game files of Project Zomboid|Game files|explanations of file formats|File formats}}
[[File:Mod structure.png|thumb|class=logo-dark]]

Local mods are recognized in two different folders which each have their own rules and structure and are both in the [[Game files#Cache folder|cache folder]]:
* {{Code|Zomboid/mods/}} - place to put mods to install manually without using the Steam Workshop. Not recommended for mod development.
* {{Code|Zomboid/workshop/}} - folder used for mod development and uploading to the Steam Workshop.

When downloading mods from the [[Steam Workshop]], they will be downloaded in [[#Online workshop folder|their own folders]] locally which you should **not** be working from when [[modding]]. Mods with the same [[mod.info|Mod ID]] as mods in other recognized folders, so for example in the online workshop folder and in the mods cache folder, will clash together and overwrite each others. This can lead to confusion when debugging your mods and even make it impossible to load new changes you applied to your mod when developing so make sure to not have two copies of your mods.

Example default mod structures are provided by the community to directly use:
* [[Project Zomboid Community Modding template]] - a template mod structure to use as a base for your own mods. Simply make a copy of the repository on your computer and modify the different elements for your own use.

{{Note|type=warn|Some [[Wikipedia:Operating system|operating systems]] like Linux and MacOS are case-sensitive regarding file and folder names. Make sure to use the correct casing when creating your mod structure to avoid issues for those users. (for example <code>common</code> and not <code>Common</code>)}}

== Video guide ==
{{Video
|id=MUGQ647o5M4
|image=PZ Modding Guides - setting up a mod structure - thumbnail.png
|name=PZ Modding Guides - setting up a mod structure
}}

== Mods or workshop ==
Using the <code>Workshop</code> folder is needed to use the [[Uploading mods#In-game uploader|in-game uploader]] meaning if you use the <code>mods</code> folder you will inevitably end up having to make a copy of your mod in the <code>Workshop</code> folder to upload it to the Steam Workshop. This is still an issue when using an external uploader like the [[Steam Uploader]] modding project, as you need to upload the <code>mods</code> folder which would upload all the extra folders. Take this for example, the folder structure of the cache folder:
{{CodeSnip
| code =
📁 ~/
    📁 Zomboid/
        📁 Crafting/
        📁 joypads/
        📁 logs/
        📁 Lua/
        📁 messaging/
        📁 mods/
            📁 MyMod1/
                ...
            📁 MyMod2/
                ...
        📁 Recording/
        📁 Sandbox Presets/
        📁 Saves/
        📁 Workshop/
            📁 MyModWorkshop/
                📁 Contents/
                    📁 mods/
                        📁 MyMod1/
                            ...
                        📁 MyMod2/
                            ...
        📄 console.txt
        ...
}}

In the case where you use the <code>mods</code> folder, to upload with an external tool you would have to indicate the application to upload the content of the folder <code>~/Zomboid</code> since the <code>mods</code> folder needs to be uploaded. This will also upload all the folders around it and will upload other mods you are developing inside the <code>mods</code> folder.

A bad solution is to copy the mods you want to upload inside of the <code>Workshop</code> folder for your mod but the problem with making copies of a mod is that they will clash and so you need to make sure to delete the mod copy inside the <code>Workshop</code> folder or you risk having invisible issues during the development.

This last principle also applies to downloading your own mods on the Workshop while having local copies inside the <code>mods</code> folder or the <code>Workshop</code> folder, as they will clash and cause issues. While working directly from the <code>Workshop</code> folder will assure you never get any problems in the future.

Another benefit of using the <code>Workshop</code> folder is that it allows you to store additional assets in the upper echelon of your mods <code>Workshop</code> folder. This is due to the <code>Workshop</code> folder having extra folders before the <code>mods</code> folder, taking the previous shared example you have <code>MyModWorkshop</code> and <code>Contents</code>. Anything in the <code>Contents</code> folder will be uploaded to the Workshop, but anything placed at the same level as it, inside <code>MyModWorkshop</code>, will not be uploaded and completely ignored by the game. You can use this to create other subfolders like <code>images</code> or <code>assets</code> which will hold your modding assets, you can have a file <code>README.md</code> and also a <code>.git</code> folder to have <code>MyModWorkshop</code> serve as your mod's [[Wikipedia:Git|git]] repository. This also applies to folders specific to your [[Wikipedia:Integrated development environment|IDE]] like <code>.vscode</code> ([[Visual Studio Code|VSCode]]) or <code>.idea</code> ([[IntelliJ IDEA|IDEA]]).

{{Note|type=error|When developing mods, make sure to not be subscribed to your own mod on the Steam Workshop. Any duplicated version of your mod on your computer which are loaded by the game, will mix and clash together, sometimes making any changes you make in a version, not appear in-game because they are being overwritten by this other duplicate version of the mod. Always keep only your local version inside the Workshop folder.}}

== Online workshop folder ==
When accessing the [[game files]], if you go in a few folders above in <code>Steam/steamapps/</code>, you can access the folder <code>workshop/content/</code> which stores every mods from all of your games. Project Zomboid has the Steam ID <code>108600</code> which can be seen in the URL of the Steam market page of the game. The mods are stored in the following folder:
{{CodeSnip
|code =
📁 Steam/
    📁 steamapps/
        📁 workshop/
            📁 content/
                📁 108600/
                    ...
}}

The folder of the mod will be named after its [[Workshop ID]].

== Workshop folder ==
The Workshop folder will use the following structure inside the [[Game files#Cache folder|cache folder]]:
{{CodeSnip
|code =
📁 Zomboid/
    📁 Workshop/
        📁 MyExampleMod/
            📁 Contents/
                📁 mods/
                    📁 MyMod1/
                        ...
                    📁 MyMod2/
                        ...
            📄 workshop.txt
            📄 preview.png
}}

* <code>Contents/</code>: The folder will only have the <code>mods/</code> folder.
* <code>Contents/mods/</code>: Your various mods which can be activated by the players will be put here, with each mod having their own [[mod.info]] file associated to be recognized (see [[#Mod folder]]). This is the folder uploaded to the Workshop.
* <code>workshop.txt</code>: Informations which are needed to upload your mod are put here (see [[workshop.txt]]).
* <code>preview.png</code>: The image used as your mod preview on the Steam Workshop. Game imposes a 256x256 resolution and an 8-bit color depth.

{{Note|Subfolders in <code>MyExampleMod/</code> which are not <code>Contents/</code> are not recognized by the game and can be used to store various files for your mod that shouldn't get uploaded. Thus you can store in it Python scripts, images, assets, etc.}}
{{Note|<code>MyExampleMod/</code> can be used as a Git repository (GitHub, GitLab...).}}
{{Note|type=error|Make sure to access the Workshop folder inside the [[Game files#Cache folder|cache folder]] and not the game files one which has the path {{Code|steamapps/common/ProjectZomboid/Workshop}} ! This folder cannot be used for modding.}}

== Mod folder ==
The files of your mods are placed in the folder <code>Contents/mods/</code> alongside a [[mod.info]] file which is the core of your mod. The folder structure of your mod folder should be as follows:

==== Build 41 ====
[[Build 41]] uses the following modding structure.
{{CodeSnip
| code =
📁 Contents/
    📁 mods/
        📁 MyMod1/
            📁 media/
                ...
            📄 mod.info
            📄 poster.png
            ...
        📁 MyMod2/             <--- for extra mods, simply add a new mod folder
            📁 media/
                ...
            📄 mod.info
            📄 poster.png
            ...
}}

{{Note|type=warn|The [[#Build 42|Build 42 modding structure]] is considered for the rest of the page. The main difference is the position of the [[#Media folder|media folder]] and the lack of versioning and common folders for Build 41.}}

=== Build 42 ===
[[Build 42]] uses the following modding structure.
{{CodeSnip
| code =
📁 Contents/
    📁 mods/
        📁 MyMod1/
            📁 common/
                📁 media/
                    ...
            📁 42/
                📁 media/
                    ...
                📄 mod.info
                📄 poster.png
            📁 42.1/           <--- for extra versions, simply add a new version folder
                📁 media/
                    ...
                📄 mod.info
                📄 poster.png
            📁 42.1.5/         <--- same here, another different version
                📁 media/
                    ...
                📄 mod.info
                📄 poster.png
            ...
        📁 MyMod2/             <--- for extra mods, simply add a new differently named mod folder
            ...
}}

{{Note|Multiple mods can be present in a single uploaded mod (inside <code>Contents/mods/</code>). This can be used for optional mods or different versions of the same mod.}}

=== Mixing build 41 and 42 ===
It is possible to mix both [[Build 41]] and [[Build 42]] modding structures in the same mod folder. Since the Build 42 structure is one folder deeper than the Build 41 one, they won't clash together and both will be properly isolated from each other.

{{CodeSnip
| code =
📁 Contents/
    📁 mods/
        📁 MyMod1/
            📁 media/        <--- Build 41 folder
                ...
            📁 common/       <--- Build 42 folder
                ...
            📁 42/           <--- Build 42 folder
                ...
}}

== Common and versioning folders ==
Common and versioning folders, introduced in [[Build 42]], help manage different mod versions per game version.

* '''Versioning folders''' are useful when players stick to older game versions. You don't need one for every version. They should contain code files and [[mod.info]], as they often change with the game version.
* '''Common folder''' stores large files (models, textures, animations) to keep mod size down.

These folders load with the following order:
#Common folder
#Closest versioning folder to the game version (overwrites common files which are present in it)

The versioning folders can have the following possible naming:
{{CodeSnip
| code =
buildVersion.majorVersion.minorVersion  ====> buildVersion.majorVersion
buildVersion.majorVersion               ====> buildVersion.majorVersion
buildVersion                            ====> buildVersion.0
}}
The minor version is not supported for the naming, so a folder named <code>42.1.5</code> will be treated as <code>42.1</code>. For example:
{{CodeSnip
| code =
42             ====> 42.0
43             ====> 43.0
42.12          ====> 42.12
42.1           ====> 42.1
42.0.5         ====> 42.0
43.5.1         ====> 43.5
}}

{{Note|The common and versioning folders of a mod are completely independent of other mods. If you try to [[Load order#File overwrites|overwrite]] another mod files, these folders will not play a role in it.}}
{{Note|type=warn|Common folder is not recognized by [[Build 41]] modding structure. However, the [[Build 41]] [[Lua (API)|Lua API]] can access some files in some cases.}}
{{Note|type=error|At least one versioning or a common folder is needed for the mod to be recognized in-game.}}

== Media folder ==
Mod assets are for the most part inside this folder. Different subfolders need to be created based on the type of assets. These are usually the same as the [[Game files#Media folder|game media folder]] and based on your [[Modding#Modding fields|modding field]], you may need different ones. See each modding fields individual pages for more details on their folder structure:
{| class="wikitable theme-blue"
|+ style="white-space:nowrap" | Subfolders and modding field
! Modding field !! Subfolder
|-
| [[Animation]] ||
Animations involve the storing of the [[File formats#Modeling and animation formats|animation files]], as well defining how those animations are triggered:
* <code>anims_X</code> - stores the animation files.
* <code>AnimSets</code> - stores the animation triggers and parameters definitions.
|-
| [[Lua (API)|Lua]] ||
Most of the time, Lua modding doesn't involve game assets but simple plain code lines, however in some cases you may want to add custom UI elements and maybe need textures.
* <code>lua</code> - stores the Lua scripts.
* <code>ui</code> and <code>textures</code> - used for custom UI elements
|-
| [[Mapping]] ||
* <code>maps</code> - stores the map files and assets.
|-
| [[Modeling]] ||
* <code>models_X</code> - stores the model assets.
|-
| [[Texturing]] ||
* <code>textures</code> - stores the texture assets
|-
| [[Translations]] ||
* <code>lua/shared/Translate</code> - translation files are put inside subfolders inside the main lua folder
|-
| [[Rendering]] ||
Renders are indirectly linked to modding, as in most cases is a process external to Project Zomboid where you use game assets for 3D renders:
* <code>models_X</code>
* <code>textures</code>
* <code>texturepacks</code> - holds the tile sprites that you will need to unpack with the [[Project Zomboid Modding Tools]]
But in the case where renders are used to create in-game assets, you will most likely need to access the <code>ui</code> or <code>textures</code> folders.
|-
| [[Scripts]] ||
Scripts involve mainly defining properties and behaviors via text files, but in most cases involve the use of assets like [[modeling|models]], [[texturing|textures]] and sounds.
* <code>scripts</code> - stores the script definitions.
* <code>clothing</code> - stores clothing item definitions.
* <code>textures</code>
* <code>models_X</code>
* <code>sound</code>
|}

=== clothing ===
The <code>clothing</code> folder is used to define clothing items via the use of XML files. Each clothing items is associated to its own XML file and a [[Wikipedia:Universally unique identifier|GUID]] to recognize the clothing item. Subfolders can be created to organize the clothing items. The outfit manager is also defined inside the file <code>clothing.xml</code> and is used to create or modify existing outfits. While this file is named the same as any others, it will not overwrite other files named like it.

=== models_X ===
{{Main|Model (scripts)}}
The <code>models_X</code> folder is used to store model files. The files need to be either in the DirectX format (<code>.x</code>) or Filmbox format (<code>.fbx</code>). They can be put in subfolders for organization and can replace files with the same relative path. See the [[File formats#Modeling and animation formats]] page for more detail.

=== textures ===
The <code>textures</code> folder is used to store texture files. The files need to be in the PNG format (<code>.png</code>). They can be put in subfolders for organization and can replace files with the same relative path. See the [[File formats#Image formats]] page for more detail.

=== ui ===
The <code>ui</code> folder is used to store images used in the user interface elements in the game. The files need to be in the PNG format (<code>.png</code>). They can be put in subfolders for organization and can replace files with the same relative path.

=== sound ===
The <code>sound</code> folder is used to store sound files. The files need to be in the OGG format (<code>.ogg</code>) or WAV format (<code>.wav</code>). They can be put in subfolders for organization and can replace files with the same relative path. Some sounds are stored inside bank files (<code>.bank</code>) which are used by the Fmod sound system, and they cannot be overwritten nor can bank files be loaded from mods.

== Example ==
Below is a full example of a mod structure in Windows.
{{CodeSnip
| code =
📁 %UserProfile%/
    📁 Zomboid/
        📁 Workshop/
            📁 MyMod/
                📄 workshop.txt                        <--- automatically generated when uploading
                📄 preview.png                         <--- 256x256 image
                📁 Contents/
                    📁 mods/
                        📁 MyMod1/
                        │   📄 mod.info
                        │   📄 poster.png
                        │   📄 icon.png
                        │   📁 42.0.0/                 <--- will be loaded for versions above 42.0.0
                        │   │   📁 media/
                        │   │       📁 AnimSets/
                        │   │           ...
                        │   │       📁 lua/
                        │   │           📁 client/
                        │   │               ...
                        │   │           📁 server/
                        │   │               ...
                        │   │           📁 shared/
                        │   │               ...
                        │   │       📁 scripts/
                        │   │           ...
                        │   │       ...
                        │   │   📄 mod.info
                        │   │   📄 poster.png
                        │   │   📄 icon.png
                        │   📁 42.X.Y/                 <--- will be loaded instead of older versions (42.0.0 for example will not load), for game versions compatibility if needed
                        │   │   ...
                        │   📁 common/                 <--- mandatory, mod won't be detected without it
                        │   │   📁 media/
                        │   │       📁 anims_X/
                        │   │           ...
                        │   │       📁 models_X/
                        │   │           ...
                        │   │       ...
                        │   📁 media/                  <--- Build 41 only folder, not used in Build 42
                        │       📁 anims_X/
                        │           ...
                        │       📁 AnimSets/
                        │           ...
                        │       📁 lua/
                        │           📁 client/
                        │               ...
                        │           📁 server/
                        │               ...
                        │           📁 shared/
                        │               ...
                        │       📁 models_X/
                        │           ...
                        │       📁 scripts/
                        │           ...
                        📁 MyMod2/                     <--- secondary mod, optional if needed
                            📄 mod.info
                            📄 poster.png
                            📄 icon.png
                            📁 42.0.0/
                                📄 mod.info
                                📄 poster.png
                                📄 icon.png
                                ...
                            📁 42.X.Y/
                                ...
                            📁 common/
                                ...
                            📁 media/
                                ...
}}

== See also ==
* [[Uploading mods]] - teaches about uploading mods.
* [[Game files]] - accessing the game files.
* [[Workshop.txt]] - about a file used by the in-game uploader.
* [[mod.info]] - about the core file which defines your mod.
* [[Load order]] - guide about load order.

== Navigation ==
{{Navbox modding}}

{{ll|Category:Modding guides}}
```
