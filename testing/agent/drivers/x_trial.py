"""x_trial -- the generic trial driver (Plan 31 Task 6, ruling P31-T): one short live boot of a planner variant on a
fixture, scored afterwards by `tools/trial_score.py` into `testing/trials/trials.md`. A trial is not evidence: its run
stays in `testing/runs/x_trial-<variant>-<stamp>/` (trial.json at its root), nothing is copied into
`testing/artifacts/`, and no row, page or brief cites it (CLAUDE.md section 5, "Trials").

    python testing/agent/drivers/x_trial.py --variant <name> --fixture <name> [--minutes N] [--no-llm]
        [--goals scripted|hold] [--waves crawler|flank|lone|none|pair|street|trio] [--teleport X,Y] [--make-fixture <name>] [--detached]

Its first line is the wall bound and the launch form it needs (trial.wall_bound): a trial past the 570 s foreground
bound is refused without --detached, and a detached launch is the controller's, after Angus approves.

The driver is thin: its key, file, artifact and profile, and the refusal before `main`. Everything else is
`driverlib/trial.py`'s (its docstring): the arguments and their refusal, the pre-boot checks (`pzt doctor`, the layout
lint, the 10 GB floor through `xlib.free_gb`, no game Java process, the fixture, the variant, a free --make-fixture
name, and the `claude -p` probe only without --no-llm), the boot (`day.boot_and_run` without the artifact copy, the
chain's next steps or a grade), trial.json, the session (`Survive(control=<variant>)`, the --minutes cap, the
teleport over RCON before the loop, the wave plan's spawns on their own thread) and the fixture snapshot.

RULES: a trial driver is edited freely between trials (trial.json names the commit or the snapshot's stamp and the
dirty flag); the machine-safety rules bind every boot: one live session at a time, the memory floor, never
-safemode, Angus's own client never touched, no OS cursor, the console shown or minimized; a five-minute trial runs
in one foreground call polled under the ten-minute cap. It takes only the arguments above, each once, and refuses
anything else before `main`.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import xlib as X                                      # noqa: E402,F401 - the provenance the RULES name
from agent.driverlib import trial as TR               # noqa: E402
from agent.driverlib.trial import flags, parse_argv   # noqa: E402

KEY = "x_trial"
DRIVER = "x_trial.py"
ARTIFACT = "x_trial.json"
PROFILE = "testing/profiles/agent.toml"
_ME = os.path.basename(os.path.abspath(__file__))


def main(args, argv=()):
    return TR.boot_and_run(args, lambda: TR.preboot(args, PROFILE), key=KEY, driver=DRIVER, artifact=ARTIFACT,
                           profile=PROFILE, argv=argv)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    main(flags(sys.argv[1:]), sys.argv[1:])
