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

<a id="reading-the-jar"></a>
### The four subcommands and what each proves

The toolchain is a small pure-Python disassembler that opens the shipped game jar directly and reads class entries out of it.
It offers four subcommands — `grep`, `methods`, `refs` and `dump` — and they are reached through a wrapper that resolves the interpreter and the jar path for you and passes the class argument on through the shell [#1972].
The jar it reads is the live install's, opened read-only, and nothing in this library ever writes to it.
The toolchain itself lives outside this repository, in a local workspace, so a cite here is reproducible only by someone who has that workspace or an equivalent reader.
There is no decompiler anywhere in the chain: the reader parses the constant pool and the method table itself and prints instructions, so every claim on these pages is a claim about bytecode and never about a line of Java source.
That is also why a claim is phrased as an instruction sequence — a branch, a constant, a call, an order — rather than as a paraphrase of source that nobody in this library has seen.

Two things about the environment are worth knowing before the first command, because both bite before anything is read.
The wrapper exists precisely so that neither the interpreter nor the jar path has to be spelled out at the call site, and it hard-codes the interpreter as an absolute path, so a shell that resolves a different interpreter breaks the direct call to the disassembler rather than the wrapper.
The workspace's own notes are where those paths are kept current, and they are read first rather than reconstructed from a command line in an old document.

`grep <string>` is the locator, and it is the only subcommand that can answer a question about the whole jar at once.
The disassembler's grep is a byte scan over the raw bytes of every class entry in the jar, about 23.7 thousand of them, so it hits method names, field names, class names, descriptors and string literals alike — which makes a no-class-contains-that-literal answer a jar-wide absence of the identifier in any form, the strongest absence this toolchain can prove [#1968].
What it does not tell you is where in the class the string sits, or whether the hit is a declaration, a call, a field type or a constant: a hit is a class to open next.
The grep result cap defaults to `--max 60` and no reading in [the method notes](../reference/jar-method-notes.md) hit it [#1969].
A cap that is reached truncates the list without saying so, so a list quoted as exhaustive is exhaustive only when the cap stood clear of it.
A full-jar grep walks the whole class list and takes a while, and that cost is exactly what buys the exhaustiveness.
A common word is narrowed by piping the hit list into a second filter on the package path rather than by raising the cap, because a cap raised to fit a noisy search hides nothing and proves nothing.
A distinctive identifier is worth searching for in preference to a plausible one: the search is over bytes, so a long unique name answers cleanly where a short common one returns half the engine.

`methods <class>` is the existence check: it prints the class's declared members with their descriptors.
The methods subcommand lists every declared method regardless of access, discarding the access flags as it walks the method table — so the access flags in [the method notes](../reference/jar-method-notes.md) were read with a scratch parser over the same constant-pool module, because private is the difference between a wall and a door for Lua [#1970].
What the member list does not tell you is the access, the body, the line numbers or which of several overloads the caller you care about uses.
It is still the first thing to run on a class, because a member that is not in the list does not exist on this build and no amount of dumping will find it.
The descriptors are what separate overloads, and they are the part of the listing a later dump is selected with, so a member list is read for its shapes and not only for its names.
A member list is also the cheapest confirmation that the package path was right: an empty listing means the wrong class far more often than it means an empty class.

`refs <class> <method>` reads one method's outbound references.
The refs subcommand is not a reverse-caller query: it takes a class and a method and lists the constant-pool references inside that method, so callers are found by grepping for the method name to narrow to the classes that hold the literal and then scanning each of those classes' methods for the call [#1971].
What it tells you is what a method reaches for — which classes, fields and methods its body names — which is how a path is followed forward from a known entry point.
What it does not tell you is who reaches for the method you asked about, and reading it as if it did is the single easiest way to invent a wall that is not there.
It is the fastest way to walk a chain downward: the entry point's references name the next method, and each step is one cheap read instead of a dump.
A reference is a name the body carries, so a reference list is read with the same caution a grep hit gets: a method the body names on one branch is not a method every call reaches.

`dump <class> <method>` disassembles one method body and prints its instructions with their bytecode offsets and their source line numbers.
It is the only subcommand whose output supports a claim about behaviour, because it is the only one that shows the branches, the constants and the order in which the method does things.
An overload is selected by its descriptor and a long method can be windowed to an offset range, which is how a method too large to read whole is read in the part that matters.
A window is a convenience and a hazard in one: it is the only way to read some of the engine's larger methods, and it is also how a branch above the window gets missed, so a claim taken from a window says which window it came from.
A dump of a method on one of the very large classes is slow enough to plan around — allow a few minutes — and a dump is one method, so a claim that spans several methods is several dumps.
What a dump does not tell you is how often the method is called, by which process, or whether anything calls it at all.
The four subcommands have four different prices, and the order a reading runs them in follows that: the member list is instant, a reference list is cheap, a dump costs a method, and a whole-jar grep costs the jar.
A reading that starts with the expensive subcommand usually pays for it twice, because a dump of the wrong overload looks exactly like a dump of the right one until the descriptors are checked.

<a id="method"></a>
### How a Java claim is built

A Java claim in this library names a class, a member, an offset and a line, and it is written `Class.method @off L<n>` from the dump that was in front of the reader when it was written.
The form is not decoration: a member list proves only that a member is declared, so the offset and the line are the part of the cite that says the body itself was read [#1970].
An offset and a line belong to one build of one jar, and a game patch moves both, so a cite is re-located by dumping the method again and matching the instruction against the words of the claim before the claim is quoted.
Re-location is also what carries a claim across a rename: the content is the anchor and the name in the cite is only a lookup key.
A reading that was taken without recording an offset is carried with a bound that says so, because a pointer naming only a class and a method is a claim that the body was read and not a claim that anyone can find the same instruction again.
A value derived from a dump rather than read off one — a threshold worked back from a ramp, a rate assembled from two constants — is carried with a derivation bound for the same reason: the arithmetic is the part a re-reader has to redo.

A jar reading is evidence of one kind, and the whole library treats it that way.
It settles what the code says, which makes it the right evidence for a wall, a mechanism or an absence, and the wrong evidence for a rate, a cadence or anything a player would notice.
Where a note and the jar disagree, the jar is the claim and the note is the thing that gives way — which is why a reading that overturns something is still written as a plain statement of what the code does.

An absence is the one kind of answer this toolchain can make exhaustive, and it is the answer most of this library's walls rest on.
Because the scan reads raw bytes rather than a parsed class model, an absence is an absence of the identifier in every form a class file can hold it in — a declaration, a call, a descriptor or a string constant — and that is what makes it quotable as a wall rather than as a failure to find something [#1968].
An absence claim therefore names the exact string that was searched for, because what a reader reproduces is the search and not the conclusion.
It also depends on the hit list behind it having stood clear of the result cap, since a truncated list reads exactly like an exhaustive one [#1969].
It is bounded in the other direction as well: the identifier is absent, which is not the same as the capability being absent under a name nobody guessed.

Access is a second read, and it is the read that decides whether a member is a door.
The access flags quoted in this library came from a scratch parser written over the toolchain's own constant-pool module, and that parser is session-scoped on purpose: it is rewritten from those modules when a later task needs it rather than carried forward, so a flag is re-read rather than inherited [#1970].
A claim about reachability that rests on an access flag is therefore only as fresh as the last time the flag was parsed.
Access and exposure are two separate gates and a member has to clear both: a public member of an unexposed class is unreachable, and a private member of an exposed class is unreachable, and the member list shows neither condition.
The order that keeps a reading cheap is existence, then exposure, then access, then callers — each step can end the question, and only the last one costs a search of the jar.

A caller is established by narrowing and then reading, never by asking the toolchain for callers.
The caller set starts as the grep hit list for the method's name and ends as the subset whose own method bodies hold the call, and that grep-then-scan is the only reverse direction this toolchain has [#1971].
A caller claim is exactly as strong as the narrowing underneath it: it is exhaustive when the grep that produced the hit list was exhaustive, and no stronger.
A "no caller" claim is the same shape as an absence claim and is written with the same care, because a method with no caller in the jar can still be called from Lua.

Two kinds of claim come out of all this and they are not worth the same.
An exhaustive claim rests on a search that covered everything — the whole jar for an identifier, a whole method body for a branch, a whole class set for exposure — and it is the kind that can carry a wall.
An indicative claim rests on a read that found something — this caller, this branch, this constant — and it supports a mechanism but never an absence.
The distinction is worth making on the page rather than in the reader's head, because the two look identical once they are written as sentences.

A finished reading does not stay a note.
It becomes a claim with its grade, its pointer and its bound, owned by the page whose mechanism it belongs to, and this page owns only the claims about the reading itself.
That is why a jar cite reaches a page inside a tag rather than in the prose: the pointer travels with the claim, and the sentence is free to say what the code does.

A class is looked up by its package path and not by the name something printed.
An inner class needs its dollar sign escaped because the wrapper passes the argument through the shell, and a class is not always at the bare name a traceback prints — the packet class a traceback named sits several packages deeper [#1972].
A wrong path answers like an empty class rather than like an error, so the path is resolved with a grep first and the member list is the confirmation that the right class was opened.
The same trap closes on a class that was moved between builds: the old path still reads as an absence, which is why an absence about a named class is re-checked with a grep for the bare class name before it is written down.

<a id="exposed"></a>
### The exposer dump as the exposure test

Whether Lua can reach a Java member is not answered by the member list, and it is not answered by the access flags either.
It is answered by the exposer: the class set the runtime registers for Kahlua is dumped and the class is either in that set or it is not.
The worked case is the item-user class, which the jar declares and the exposer's class set does not hold, and it is stated at [reaching a Java member](lua-platform.md#java-members) ([#0963/C/C-only]).
The test is strict membership over the classes the exposer registers, which is why a class the engine's own code calls can still be out of reach from a mod [#1740/C/C-only].

The dump this test runs against is the whole exposer, read end to end rather than searched, and the readings taken against it are collected in [the jar method notes](../reference/jar-method-notes.md).
Reading it whole is what lets an absence in it be quoted: a class that is missing from a dump that was read in full is missing, while a class that is missing from a search is missing from the search.
The set itself is a list of classes the runtime hands to the scripting layer, so the test is about the class and not about the member — a member cannot be exposed out of a class that is not in the set, and nothing a mod writes adds a class to it.
That is why the verdict is worth taking early: it is the one answer that makes every further reading of a class's members pointless.
Two of this library's hardest walls are exposure-test results, the moodle stat and the Lua compiler alike, and both are recorded on [the wall map](../reference/wall-map.md) rather than here ([#1141/C/C-only], [#1172/C/C-only]).

What the exposure test does not cover is as important as what it settles.
Membership says a class can be reached; it does not say a given member is callable, what arity or overload the call resolves to, or that the call behaves the same on both sides of a session — those belong to [reaching a Java member](lua-platform.md#java-members).
It says nothing about whether the call is safe: a member that is reachable and wrong still costs a run.
And it is a per-build answer like every other jar reading, so an exposure verdict is re-checked against the exposer of the build in play rather than carried between builds.

The test is cheap to apply and expensive to establish, which shapes how it is used here.
Establishing it means dumping one very large method and reading the whole thing, so the dump is taken once and quoted, rather than re-run for each new question.
Applying it is then a membership question against that dump, which is why an exposure verdict appears in this library as a flat yes or no with no offset attached.
A class that clears the test is a candidate for a live check rather than a settled answer, and the next step for it is a call through [the harness](harness.md#probes) rather than another dump.

## Walls and bounds
<a id="walls"></a>

A jar read settles what a method does when it is called, and never how often it is called: a cadence is read as a constant or inferred from a caller, and only a run says whether the path runs at all on a given host.
A carrier read out of the bytecode can be exhaustive while its cadence stays entirely unread, which is the shape the multiplayer inventory re-send is in [#0376/C/C-only/open].
A side gate is readable — the branch that tests for a server or a client is right there in the dump — but which process actually reaches the gate on a real session is a question for a run, as the aging call shows [#0374/C/C-only/open].
Behaviour under a real session is outside a static read altogether: the order a mod's Lua runs in, what a client's copy of an object holds at the moment it is read, and what another mod did to the same field are all run questions.
An absence proved by grep is an absence of an identifier, not of a capability: the string is not in the jar, and a capability reached under a name nobody searched for would read exactly the same way.
A dump is one method, so a claim that spans a call chain is a chain of dumps and inherits the weakest link in it, and a claim about who writes a field is a grep-and-scan rather than a dump.
The exposure test says a class is reachable from Kahlua and nothing more — not that a member is callable, not that a call is safe, and not that both sides behave alike — see [reaching a Java member](lua-platform.md#java-members) ([#0963/C/C-only]).
The access flags quoted here came from a session-scoped scratch parser rather than from a shipped subcommand, so they are reproducible only by rebuilding that parser from the toolchain's own modules [#1970].
Every reading in this library is one jar of one build, the install patches on its own schedule, and the build the numbers belong to is re-checked against the install rather than quoted from a note [#1968, #1969].
The toolchain is not part of this repository and is not vendored anywhere in it, so a reader without that local workspace can check a cite only by re-reading the same jar with an equivalent disassembler.
The workspace it lives in also holds work that has nothing to do with this library and its own stale corners, so its notes are read for the paths and the toolchain and not quoted as evidence for anything here.
A jar reading says nothing about the shipped Lua or the script files, which are ordinary files on disk and are read as files rather than disassembled.
No claim here was taken from a modified or a patched jar: the install is read exactly as Steam left it, and a reading against anything else would not be comparable with the rest of the library.
A reading says what this build ships and never what the game will ship, so neither a member that exists today nor an absence proved today is a promise about the build after it.
Not covered: this library never attached a debugger or an instrumentation agent to the running game, never read decompiled Java source rather than bytecode, and never opened the jar's sound, tile and sprite, vehicle, world-map or save-format classes at all — every Java claim here comes from a static bytecode read of the classes the nutrition and modding questions happened to reach.

## Open
<a id="open"></a>

This page's own rows are settled readings of the toolchain, so the open items below are the jar questions the library left unread; each is owned by the page that would answer it.

- The spice branch of the evolved summation is unread: the overload set was never dumped — settled by dumping the overloads ([#0381/C/C-only/open], [areas/open-questions.md](../areas/open-questions.md)).
- The food-to-health scale is unread: the getter was never dumped — settled by one dump ([#0146/C/open], [facts/eating-pipeline.md#open](../facts/eating-pipeline.md#open)).
- The readers of the two maintained nutrition maxima are unfound: the reverse scan named none — settled by a scan wide enough to name a reader or to prove there is none ([#0190/C/snapshot/open], [facts/nutrition-core.md#open](../facts/nutrition-core.md#open)).
- The multiplayer inventory re-send cadence is unread: the carrier is read and its cadence is not — settled by a timed client read rather than another dump ([#0376/C/C-only/open], [platform/mp-model.md#open](mp-model.md#open)).
- The eat packet's recipient list, once unresolved because the send call's target was not settled from the bytecode, is settled on the code: a player-addressed send reaches the eater's own connection only, stated at [platform/mp-model.md#sync-globals](mp-model.md#sync-globals).
- Whether food ages at all on a single-player host is unsettled from the code alone: the side gate is readable and the question is not — settled by a single-player run ([#0374/C/C-only/open], [facts/spoilage.md#open](../facts/spoilage.md#open)).
- A decision the design must take: the Java half of this library is reproducible only with a toolchain that is not in this repository, and either an equivalent reader is vendored or every re-check stays a manual step in a separate workspace.
- A decision the design must take: an exposure verdict is a per-build answer, so the mod either pins the build it claims to support or re-runs the exposure test when the install patches.

## Worked examples

One question answered end to end from the jar: the script checksum gate, from the first locator grep to the classes that end the story, as it was read.
The shape is the procedure below — locate, resolve the path, list the members, dump the bodies — and the block carries both of the traps described at [how a Java claim is built](#method), the escaped inner class and the package path that is not the printed name.
What the gate does with the digest belongs to [the checksum gate](mod-anatomy.md#checksum-gate).

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

The second shape is an absence, and it runs in the other order: the grep comes first and everything after it is an attempt to make the absence fail.
A reading that ends in a wall starts by searching the jar for the identifier, opens every class that holds the literal, dumps the one method that looks like a live implementation, and only then asks the exposure test whether any of it is reachable from a mod.
The wall is written when all four steps agree, and the claim that goes on the page is the narrowest of them — usually the exposure result, because it is the one a mod actually runs into.

```bash
./pz.sh grep loadstring                        # every class entry that holds the literal
./pz.sh methods <the class the hits point at>  # a declared method, or only a dead constant?
./pz.sh dump    <that class> loadstring        # a real body, and who could reach it
./pz.sh grep rawset | grep -i lua              # is the global ever installed at runtime?
# then the exposure test: is the compiler's class in the exposer's class set at all?
```

The reading that comes out of a session like either of those is stored as a pointer, and the pointer's shape says which subcommand produced it.
A pointer that names an instruction range is a claim about an order or a branch; a pointer that names a method and no offset is a claim that the body was read; a pointer that names a search is a claim about the whole jar.
Reading the shape first tells you what kind of re-check the claim needs before you trust it, and it is the fastest way to spot a claim that is carrying more weight than its evidence.

```text
tool:pz-b42/tools/pzdis.py:150-153          a line of the toolchain's own source
jar:ScriptManager.Load @680 L1525           one method body, at an offset, on a line
jar:NetChecksum$Comparer.update @62–@85 L213–L215   an instruction range inside one body
jar:LuaManager$Exposer.exposeAll() dump     a whole method read end to end
jar:jar-wide grep loadstring                an absence proved over every class entry
```

## Procedure
<a id="procedure"></a>

The disassembler is not part of this repository: it is a local workspace on this machine, its own `WORKSPACE.md` is the file to read before running anything there, and the jar and the game install it reads are read-only.
The steps below turn a question into a claim that can be cited; each one is skipped only when the question does not need it, never because a previous answer looked obvious.

1. Write the question as a claim about one class and one member, with the answer it would have if the jar settles it — a question that cannot be phrased that way is a question for a run, not for the jar.
2. Locate the identifier with a jar-wide `grep`, and narrow the hit list with a second filter on the class path rather than by raising the cap.
3. Resolve the class's real package path from the hit list; a name printed by a traceback or a log line is a hint, and an inner class needs its dollar sign escaped before the wrapper passes it to the shell.
4. List the class's members with `methods` and confirm from the descriptors that this is the class and the overload the question is about.
5. If the question is whether Lua can reach it, stop here and run the exposure test against the exposer dump before spending a dump on the body.
6. If access decides the answer, read the flags out of the constant pool with a parser rebuilt from the toolchain's own modules; the member list will not tell you.
7. Dump the method body; select the overload by its descriptor when there is more than one, and window a long method to an offset range rather than reading it whole.
8. For callers, grep the member's name and then scan each hit class's own methods for the call — the references subcommand answers the other direction.
9. Write the cite as `Class.method @off L<n>` from the dump in front of you, and re-locate any older cite you are about to repeat by matching its instruction rather than its line number.
10. Write the bound in the same breath as the claim: what the read does not settle — the behaviour under a session, the cadence, the side it runs on — and hand each of those to a run.
11. Record the build the reading belongs to by re-checking the install rather than quoting a version from a note, because the next patch moves the offsets under every cite taken today.

A step that disagrees with an earlier note stops the reading rather than the note: the dump is re-taken, the path is re-resolved, and only when the same answer comes back twice does the claim change.
A question that survives every step unanswered is not a jar question, and the honest outcome is to write down what the code does settle, name what it does not, and hand the remainder to a run.
Nothing in this procedure boots the game or writes to the install; the whole of it is a read of one file, which is why it is the cheapest evidence this library has and the first thing to try.
A reading that took more than a handful of commands is worth keeping as the commands themselves, in the order they were run, because the next reader's first question is which commands produced the answer.

## See also

- [reaching a Java member](lua-platform.md#java-members) — what an exposure verdict means for a mod, and what a reachable member still costs.
- [the checksum gate](mod-anatomy.md#checksum-gate) — the mechanism the worked example above was read to establish.
- [the jar method notes](../reference/jar-method-notes.md) — the moved read these rows were harvested from, including the exposer readings and the worked query verbatim.
- [the wall map](../reference/wall-map.md) — where a jar-proven absence is recorded as a wall.
- [the tools](../reference/tools.md) — the repository's own scanners, written in the same parser style as this toolchain.
- [the harness](harness.md#probes) — where a question the jar cannot settle goes next.
- [the platform overview](overview.md#surfaces) — which surface a question belongs to before it reaches the jar at all.
