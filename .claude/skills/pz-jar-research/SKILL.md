---
name: pz-jar-research
description: Answering a question only the decompiled `projectzomboid.jar` settles — "what does the engine do when …", is a class or member exposed to Lua, is it private, where is a method called from, which fields does a packet write — with `pz.sh grep|methods|refs|dump`, reading a class path, a member list, access flags, an offset or a line; writing or re-checking a `Class.method @off L<n>` cite; proving a member absent with a jar-wide grep; finding callers by hand.
---
## Read first
- docs/platform/jar-research.md
- docs/reference/jar-method-notes.md

## Rules quoted
- Re-locate a class, a member and an offset by re-reading the jar before you quote them: a name printed somewhere else is a lookup key and not an address, a class is not always at the bare name a traceback prints, and a wrong path answers like an empty class rather than like an error [#1972].
- Write a jar cite as `Class.method @off L<n>`: a member list proves only that the member is declared, so the offset and the line are the part of the cite that says the body was read [#1970].
- Prove an absence with a jar-wide grep before calling a member missing: the scan reads the raw bytes of every class entry, so a no-class-contains-that-literal answer is the absence of the identifier in any form, which is the strongest absence this toolchain can prove [#1968].
- Treat a grep hit as a byte match and never as a call site: the scan hits method names, field names, class names, descriptors and string literals alike, so a hit list is the candidate set a reading narrows [#1968].
- Check the result cap before reading a hit list as complete: the cap has a default and a truncated list looks exactly like an exhaustive one [#1969].
- Never read access off the member list: the methods subcommand lists every declared method regardless of access and discards the flags as it walks the method table [#1970].
- Read `refs` as the outbound references of one method: it takes a class and a method and lists the constant-pool references inside that method, which is not a reverse-caller query [#1971].
- Hand a question about timing to a live run rather than to the jar: a carrier can be read out of the bytecode while its cadence stays unread, as the multiplayer inventory re-send is [#0376/C/C-only/open].

## Also
- docs/platform/lua-platform.md#java-members — the exposure test and what reaching a Java member costs a mod once the jar has named it.
- docs/platform/harness.md — the live run a timing or which-side question goes to (skill `pz-mod-testing`).
- docs/reference/tools.md#claims-tools — the `jar:` pointer form a cite takes in the register.
