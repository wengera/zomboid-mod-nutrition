# Reading the jar
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: how a question about the game's Java becomes a citable claim here — the disassembler's four subcommands and what each proves, how an absence, a caller, an access flag and an offset are established, the exposer dump as the exposure test, and the numbered procedure; the disassembler is a local workspace and is not part of this repository, and what an exposure verdict costs a mod is handed off to `lua-platform.md`.

## Rules

- Read every jar answer as a statement about one build: each reading here was taken from one jar of build `42.20.4`, and a patch moves class names, offsets and line numbers together [#1968, #1969].
- Re-locate a class, a member and an offset by re-reading the jar before you quote them: a name printed somewhere else is a lookup key and not an address, a class is not always at the bare name a traceback prints, and a wrong path answers like an empty class rather than like an error [#1972].
- Write a jar cite as `Class.method @off L<n>`: a member list proves only that the member is declared, so the offset and the line are the part of the cite that says the body was read [#1970].
- Prove an absence with a jar-wide grep before calling a member missing: the scan reads the raw bytes of every class entry, so a no-class-contains-that-literal answer is the absence of the identifier in any form, which is the strongest absence this toolchain can prove [#1968].
- Treat a grep hit as a byte match and never as a call site: the scan hits method names, field names, class names, descriptors and string literals alike, so a hit list is the candidate set a reading narrows [#1968].
- Check the result cap before reading a hit list as complete: the cap has a default and a truncated list looks exactly like an exhaustive one [#1969].
- Never read access off the member list: the methods subcommand lists every declared method regardless of access and discards the flags as it walks the method table [#1970].
- Read the access flags out of the constant pool before calling a member a door: private is the difference between a wall and a door for Lua, and the flags come from a scratch parser rather than from a shipped subcommand [#1970].
- Rebuild that scratch parser from the toolchain's own constant-pool and disassembly modules rather than reusing a saved copy: it is session-scoped by design, so a flag is re-read rather than trusted [#1970].
- Read `refs` as the outbound references of one method: it takes a class and a method and lists the constant-pool references inside that method, which is not a reverse-caller query [#1971].
- Find callers by grepping the method name and then scanning each hit class's own methods for the call: the toolchain has no reverse-caller index, so a caller set is a grep result narrowed by hand [#1971].
- Escape the dollar sign of an inner class: the wrapper passes its argument on through the shell [#1972].
- Resolve a class's package path before dumping it: a class is not always at the bare name a traceback prints, and a wrong path answers like an empty class rather than like an error [#1972].
- Test a class against the exposer's class set before planning any Lua call on it, whatever the jar declares about the member: membership in that constant-pool class set is the exposure test, and what it costs a mod is reaching a Java member [#0963/C/C-only, #1740/C/C-only].
- Hand a question about timing to a live run rather than to the jar: a carrier can be read out of the bytecode while its cadence stays unread, as the multiplayer inventory re-send is [#0376/C/C-only/open].
- Say which side a gated path runs on only after a run has touched it: a side gate is readable in the bytecode while whether the path ever runs on a given host is not, as the aging call is [#0374/C/C-only/open].

## How it works

The toolchain readings that follow are of the build their rows' bounds name; they are re-read on any other.

<a id="reading-the-jar"></a>
### The four subcommands and what each proves

The toolchain is a pure-Python disassembler over the shipped jar, reached through a wrapper that resolves the interpreter and the jar path and passes the class argument on through the shell [#1972].
The wrapper hard-codes the interpreter as an absolute path, so a shell that resolves a different interpreter breaks a direct call to the disassembler rather than the wrapper.
It lives in a local workspace outside this repository, whose `WORKSPACE.md` keeps its paths current; the jar is read-only.
It parses the constant pool and the method table and prints instructions, with no decompiler, so every Java claim here is about bytecode and is phrased as a branch, a constant, a call or an order.

| Subcommand | What it proves | What it does not |
|---|---|---|
| `grep <string>` | which class entries hold the bytes, jar-wide | where in the class, or whether a hit is a declaration, a call or a constant |
| `methods <class>` | which members are declared, with descriptors | access, body, lines, which overload a caller uses |
| `refs <class> <method>` | what one method's body references | who calls that method |
| `dump <class> <method>` | the body: branches, constants, order, offsets, lines | how often it runs, on which side, or whether anything calls it |

The disassembler's grep is a byte scan over the raw bytes of every class entry in the jar, about 23.7 thousand of them, so it hits method names, field names, class names, descriptors and string literals alike — which makes a no-class-contains-that-literal answer a jar-wide absence of the identifier in any form, the strongest absence this toolchain can prove [#1968].
The grep result cap defaults to sixty and no reading in [the method notes](../reference/jar-method-notes.md) hit it [#1969]; a reached cap truncates silently, so a noisy search is narrowed with a second filter on the class path, never by raising the cap.
The methods subcommand lists every declared method regardless of access, discarding the access flags as it walks the method table [#1970].
An empty member list usually means a wrong package path, and the descriptors are what a later dump selects an overload by.
The refs subcommand is not a reverse-caller query: it takes a class and a method and lists the constant-pool references inside that method [#1971]; it walks a chain forward, and a name on one branch is not a call every path makes.
`dump` is the only subcommand whose output supports a claim about behaviour; a long method can be windowed to an offset range, and a claim taken from a window names its window, because a branch above it is easy to miss.
Run them cheapest first: the member list, then the references, then a dump, then a whole-jar grep.
A full-jar grep walks the whole class list and takes a while, and a dump of a method on one of the very large classes is slow enough to plan around — allow a few minutes; a dump is one method, so a claim that spans several methods is several dumps.

<a id="method"></a>
### How a Java claim is built

A cite is `Class.method @off L<n>`: a member list proves only that a member is declared, so the offset and the line are the part of the cite that says the body was read [#1970].
An offset and a line belong to one jar of one build, and a patch moves both [#1968, #1969]; a cite is re-located by re-dumping and matching the instruction, the content being the anchor and the name only a lookup key.
A reading without an offset carries a bound that says so, and a value derived from a dump (a threshold worked back from a ramp) carries a derivation bound.
A jar read settles what the code says, so it is the evidence for a wall, a mechanism or an absence, never for a rate or a cadence.

An absence is the one answer this toolchain makes exhaustive, because the grep reads raw bytes: the identifier is absent in every form a class file can hold it [#1968].
An absence claim names the exact string searched, and holds only when its hit list stood clear of the cap [#1969].

Access is a second read.
The access flags were read with a scratch parser over the same constant-pool module, because private is the difference between a wall and a door for Lua; the parser is session-scoped and is rewritten from the toolchain's own modules when a later task needs it, so a flag is re-read rather than inherited [#1970].
Access and exposure are separate gates and a member must clear both; the order existence, exposure, access, callers lets each step end the question cheaply.

Callers are found by grepping for the method name to narrow to the classes that hold the literal and then scanning each of those classes' methods for the call [#1971].
A caller set is exhaustive only when that grep was; a "no caller" claim is written like an absence, since Lua can still call the method.
An exhaustive claim (a whole jar, a whole body, a whole class set) can carry a wall; an indicative one (this caller, this branch) supports a mechanism, never an absence.

An inner class needs its dollar sign escaped because the wrapper passes the argument through the shell, and a class is not always at the bare name a traceback prints — the packet class a traceback named sits several packages deeper [#1972].
A wrong path answers like an empty class, so the path is resolved with a grep first, and an absence about a named class is re-checked with a grep for the bare class name.
A finished reading becomes a register row owned by the page whose mechanism it belongs to; this page owns only the rows about the reading itself.

<a id="exposed"></a>
### The exposer dump as the exposure test

Whether Lua can reach a Java class is answered by neither the member list nor the access flags but by membership in the class set the exposer registers for Kahlua.
The worked case is the item-user class, which the jar declares and the exposer's class set does not hold, stated at [reaching a Java member](lua-platform.md#java-members) ([#0963/C/C-only]).
The test is strict membership over the classes the exposer registers, which is why a class the engine's own code calls can still be out of reach from a mod [#1740/C/C-only].
The exposer is dumped once and read whole, so a class missing from it is missing; nothing a mod writes adds a class to the set, and the readings are in [the jar method notes](../reference/jar-method-notes.md).
Two of the hardest walls are exposure results, the moodle stat and the Lua compiler, recorded on [the wall map](../reference/wall-map.md) ([#1141/C/C-only], [#1172/C/C-only]).
Membership does not say a member is callable, which overload resolves, or that both sides behave alike: [reaching a Java member](lua-platform.md#java-members) owns those; a class that clears the test goes next to a call through [the harness](harness.md#probes).

## Walls and bounds
<a id="walls"></a>

A jar read settles what a method does when called, never how often: a carrier can be read in full while its cadence stays unread, as the multiplayer inventory re-send is [#0376/C/C-only/open].
A side gate is readable in the dump, but which process reaches it on a real session is a run question, as the aging call shows [#0374/C/C-only/open].
Lua order, a client copy's state at read time and another mod's writes are all outside a static read.
A grep absence is of an identifier, not of a capability reached under a name nobody searched.
A dump is one method, so a claim along a call chain is a chain of dumps with the weakest link's strength.
The exposure test says a class is reachable from Kahlua and nothing more — see [reaching a Java member](lua-platform.md#java-members) ([#0963/C/C-only]).
The access flags came from a session-scoped scratch parser, not a shipped subcommand, so they are reproducible only by rebuilding it from the toolchain's modules [#1970].
Every reading is one jar of one build, re-checked against the install rather than quoted from a note [#1968, #1969].
The toolchain is not vendored here; a reader without the workspace checks a cite only with an equivalent disassembler on the same jar, and the workspace's notes are read for paths, never cited as evidence.
The shipped Lua and scripts are files on disk, read as files, never disassembled; the jar is read as Steam left it, never patched.
Not covered: no debugger or instrumentation agent was attached to the running game, no decompiled Java source was read, and the sound, tile and sprite, vehicle, world-map and save-format classes were never opened.

## Open
<a id="open"></a>

The jar questions the library left unread, each owned by the page that would answer it.

- The food-to-health scale is unread: the getter was never dumped — settled by one dump ([#0146/C/open], [facts/eating-pipeline.md#open](../facts/eating-pipeline.md#open)).
- The readers of the two maintained nutrition maxima are unfound: the reverse scan named none — settled by a scan wide enough to name a reader or to prove there is none ([#0190/C/snapshot/open], [facts/nutrition-core.md#open](../facts/nutrition-core.md#open)).
- The multiplayer inventory re-send cadence is unread: the carrier is read and its cadence is not — settled by a timed client read rather than another dump ([#0376/C/C-only/open], [platform/mp-model.md#open](mp-model.md#open)).
- Whether food ages at all on a single-player host is unsettled from the code alone: the side gate is readable and the question is not — settled by a single-player run ([#0374/C/C-only/open], [facts/spoilage.md#open](../facts/spoilage.md#open)).
- A decision the design must take: the Java half of this library is reproducible only with a toolchain that is not in this repository, and either an equivalent reader is vendored or every re-check stays a manual step in a separate workspace.
- A decision the design must take: an exposure verdict is a per-build answer, so the mod either pins the build it claims to support or re-runs the exposure test when the install patches.

## Worked examples

The script checksum gate, read end to end — locate, resolve the path, list the members, dump the bodies — with both path traps of [how a Java claim is built](#method); what the gate does with the digest is [the checksum gate](mod-anatomy.md#checksum-gate).

```bash
./pz.sh grep checksum | grep -i script
./pz.sh dump zombie/scripting/ScriptManager Load
./pz.sh dump zombie/scripting/ScriptManager getChecksum
./pz.sh methods zombie/network/NetChecksum
./pz.sh dump    zombie/network/NetChecksum makeDigest
# inner classes need the $ escaped in Git Bash:
./pz.sh methods "zombie/network/NetChecksum\$Checksummer"
./pz.sh dump    "zombie/network/NetChecksum\$Checksummer" addFile
./pz.sh dump    "zombie/network/NetChecksum\$Checksummer" checksumToString
./pz.sh dump    "zombie/network/NetChecksum\$Comparer"    update
# ChecksumPacket is NOT at the bare name a traceback prints — the class path is
# zombie/network/packets/service/ChecksumPacket
./pz.sh methods zombie/network/packets/service/ChecksumPacket
./pz.sh dump    zombie/network/packets/service/ChecksumPacket parseServer
./pz.sh dump    zombie/network/packets/service/ChecksumPacket getReason
./pz.sh methods zombie/network/anticheats/AntiCheatChecksumUpdate
./pz.sh dump    zombie/network/anticheats/AntiCheatChecksumUpdate update
./pz.sh dump    zombie/network/anticheats/AntiCheatChecksumUpdate isDifferentChecksumTimeoutExpired
./pz.sh dump    zombie/network/anticheats/AntiCheat update
```

An absence runs the other way: the grep first, then every step tries to make the absence fail, and the claim written is the narrowest that holds, usually the exposure result a mod actually meets.

```bash
./pz.sh grep loadstring                        # every class entry that holds the literal
./pz.sh methods <the class the hits point at>  # a declared method, or only a dead constant?
./pz.sh dump    <that class> loadstring        # a real body, and who could reach it
./pz.sh grep rawset | grep -i lua              # is the global ever installed at runtime?
# then the exposure test: is the compiler's class in the exposer's class set at all?
```

A register pointer's shape says which subcommand produced it and so what re-check it needs: an instruction range claims an order or a branch, a method without an offset claims the body was read, and a search claims the whole jar.

```text
tool:pz-b42/tools/pzdis.py:150-153          a line of the toolchain's own source
jar:ScriptManager.Load @680 L1525           one method body, at an offset, on a line
jar:NetChecksum$Comparer.update @62–@85 L213–L215   an instruction range inside one body
jar:LuaManager$Exposer.exposeAll() dump     a whole method read end to end
jar:jar-wide grep loadstring                an absence proved over every class entry
```

## Procedure
<a id="procedure"></a>

Read the workspace's own `WORKSPACE.md` before running anything there; the jar and the install are read-only. Skip a step only when the question does not need it.

1. Write the question as a claim about one class and one member; a question that cannot be phrased that way is for a run.
2. Locate the identifier with a jar-wide `grep`, narrowing with a second filter on the class path rather than by raising the cap.
3. Resolve the class's real package path from the hit list, escaping an inner class's dollar sign.
4. List the members with `methods` and confirm the class and the overload from the descriptors.
5. If the question is whether Lua can reach it, run the exposure test before spending a dump.
6. If access decides it, read the flags out of the constant pool with a parser rebuilt from the toolchain's modules.
7. Dump the body, selecting the overload by descriptor and windowing a long method to an offset range.
8. For callers, grep the member's name and scan each hit class's methods for the call.
9. Write the cite as `Class.method @off L<n>` from the dump in front of you, re-locating any older cite by its instruction, not its line.
10. Write the bound with the claim: what the read does not settle (session behaviour, cadence, side) goes to a run.
11. Record the build by re-checking the install, not by quoting a note.

A step that disagrees with an earlier note stops the reading, not the note: re-take the dump, re-resolve the path, and change the claim only when the same answer comes back twice. A reading of more than a handful of commands is kept as the commands, in order.

## See also

- [reaching a Java member](lua-platform.md#java-members) — what an exposure verdict means for a mod.
- [the checksum gate](mod-anatomy.md#checksum-gate) — the mechanism the worked example was read to establish.
- [the jar method notes](../reference/jar-method-notes.md) — the readings these rows were harvested from, the exposer readings included.
- [the wall map](../reference/wall-map.md) — where a jar-proven absence is recorded as a wall.
- [the harness](harness.md#probes) — where a question the jar cannot settle goes next.
- [the platform overview](overview.md#surfaces) — which surface a question belongs to before it reaches the jar.
