"""One shared scrubbed git environment for every test that runs git in a temporary directory (Plan 19 Task 3e fix 1).

A test run under GIT_DIR (a reviewer pointing a clone at the real .git so pins resolve) would otherwise commit to the
real repository: e68042a1 "c1" landed on main that way. The scrub drops every variable that aims git at another
repository, and a test that writes with git takes its environment from here."""
import os

AIMING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES")


def scrubbed_env(base=None):
    """`base` (default os.environ) without the variables that aim git at another repository."""
    return {k: v for k, v in (os.environ if base is None else base).items() if k not in AIMING}
