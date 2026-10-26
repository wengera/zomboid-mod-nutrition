"""c_survive_dense -- Plan 21 Task 12, Stage C's second run (spec § 4.3): c_survive.py's session on agent-dense
(fixture `agent`, sandbox Zombies = 4, one step denser than agent.toml's 5). Run only if the first run survived (the
controller's call). Everything but the key, the file, the profile and the artifact is imported from c_survive.py,
which the pre-boot checks require committed clean beside this file (c_survive's docstring is this driver's).

RULES: never edited after its run; takes no argument; one live session at a time; free memory gated at MIN_FREE_GB
before the boot; never -safemode; launched detached by the controller and polled through the persisted artifact.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(TESTING, "experiments"), TESTING):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent.drivers import c_survive as CS             # noqa: E402

KEY = "c_survive_dense"
DRIVER = "c_survive_dense.py"
PROFILE = "testing/profiles/agent-dense.toml"
ARTIFACT = "c_survive_dense.json"
BUDGET_S = CS.BUDGET_S
USER = CS.USER
MIN_FREE_GB = CS.MIN_FREE_GB
REPO = CS.REPO
_ME = os.path.basename(os.path.abspath(__file__))

SPEC = CS.Spec(KEY, DRIVER, PROFILE, ARTIFACT)
parse_argv = CS.parse_argv
Survive = CS.Survive
new_out = CS.new_out


def driver_checks(driver_file, repo=REPO, git_say=None, git_dirty=None):
    return CS.driver_checks(driver_file, SPEC, repo, git_say=git_say, git_dirty=git_dirty)


def preboot(driver_file, repo=REPO):
    return CS.preboot(driver_file, SPEC, repo)


if __name__ == "__main__":
    refusal = parse_argv(sys.argv[1:], __file__)
    if refusal:
        sys.exit(refusal)
    CS.main(SPEC, _ME)
