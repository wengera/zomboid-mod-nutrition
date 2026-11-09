"""x_facing -- the facing trial driver (Plan 32 Task 2, ruling P31-T): one short live boot that holds the character
still and runs the `probe` act under each facing mechanism for N ticks, standing and back-pedalling, scored afterwards
by `tools/facing_score.py` into `testing/trials/facing.md`. A trial is not evidence: its run stays in
`testing/runs/x_facing-<stamp>/` (trial.json at its root), nothing is copied into `testing/artifacts/`, and no row,
page or brief cites it (CLAUDE.md section 5, "Trials").

    python testing/agent/drivers/x_facing.py [--fixture arena-east] [--ticks 60] [--zombie]
        [--modes read,snap_aimed,...] [--minutes N] [--detached]

The driver is thin: its key, file, artifact and profile, and the refusal before `main` (an argument it does not define
is refused in one line, exit 2). Everything else is `driverlib/facing.py`'s (its docstring: the plan, the sequencer and
its decision line) over `driverlib/trial.py`'s boot, pre-boot and wall bound (a run past the 570 s foreground bound is
refused without --detached, and a detached launch is the controller's, after Angus approves).

RULES: the machine-safety rules bind the boot (one live session at a time, never -safemode, Angus's own client never
touched, no OS cursor, the console shown or minimized); a trial driver is edited freely between trials (trial.json names
the commit and the dirty flag).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import xlib as X                                      # noqa: E402,F401 - the provenance the RULES name
from agent.driverlib import facing as FC              # noqa: E402
from agent.driverlib import trial as TR               # noqa: E402
from agent.driverlib.facing import flags, parse_argv  # noqa: E402

KEY = "x_facing"
DRIVER = "x_facing.py"
ARTIFACT = "x_facing.json"
PROFILE = "testing/profiles/agent.toml"
ALLOWED = ("--fixture", "--ticks", "--zombie", "--modes", "--minutes", "--detached")
_ME = os.path.basename(os.path.abspath(__file__))


def main(args, argv=()):
    return TR.boot_and_run(args, lambda: FC.preboot(args, PROFILE), key=KEY, driver=DRIVER, artifact=ARTIFACT,
                           profile=PROFILE, argv=argv, run_prefix=KEY,
                           run_session_fn=lambda xs, tr, pre, note: FC.run_session(args, xs, tr, pre, note))


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        print(refusal, file=sys.stderr)
        sys.exit(2)
    main(flags(sys.argv[1:]), sys.argv[1:])
