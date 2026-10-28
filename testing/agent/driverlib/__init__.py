"""The driver library: the code a live-session driver shares, imported rather than copied.

A driver under `testing/agent/drivers/` is frozen once it has run (CLAUDE.md § 5, "Freezing"), so until Plan 23 every
driver copied its helpers from the last one. This package holds that shared code instead:

- `session`  the constants (`DEFAULTS`), the argument refusal, the pre-boot checks, the memory gate, the pure
             helpers over the PZA/1 lines and the server's replies, and `Session`: the hello, damage-hook, kit and
             planner-loop phases over one FileTransport, with the loop's stop conditions;
- `polls`    `PollThread`, the server reads run on a worker thread so a slow bus never blocks the loop;
- `record`   the artifact's loop summary, action rows and death record, built off a Session;
- `chain`    a chained day's lineage check between two sessions and the `pzt snapshot` argv between them.
- `day`      the day drivers' shared session (Task 16d): their arguments, the chain's pre-boot checks, `Chain` (the
             Session with the chain's record) and `boot_and_run`, the boot a day driver calls.

The library is not frozen: it changes as the drivers need, and its tests guard it. A session's artifact names the
tree's commit (`out["preboot"]["commit"]`, with `driverlib_commit` beside it, and the pre-boot checks refuse a dirty
library), so the library's state at any boot is recoverable with `git show <commit>:testing/agent/driverlib/...`.
The drivers that ran before it (the Plan 22 drivers, `_dlib.py`) keep their own copies and are never edited; nothing
here imports a driver but `_dlib`'s boot seams.
"""
