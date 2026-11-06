import datetime
import os

PZ_DIR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid"
JAVA = os.path.join(PZ_DIR, "jre64", "bin", "java.exe")
EXE = os.path.join(PZ_DIR, "ProjectZomboid64.exe")
WORKSHOP_DIR = r"D:\SteamLibrary\steamapps\workshop\content\108600"

PKG = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(PKG)


def _root(var, default):
    """The directory named by environment variable `var`, made absolute, else `default`: a run
    booted from a git-archive snapshot has neither the fixture caches nor the run folder (both
    gitignored), so it is told where the main tree's are (Plan 31 Task 3)."""
    value = os.environ.get(var)
    return os.path.abspath(value) if value else default


RUNS = _root("PZT_RUNS", os.path.join(TESTING, "runs"))
FIXTURES = _root("PZT_FIXTURES", os.path.join(TESTING, "fixtures"))
HARNESS_MODS = {"PZTestKit": os.path.join(TESTING, "PZTestKit", "PZTestKit")}

ADMIN_USER = "admin"          # bootstrap account created by -adminpassword
ADMIN_PW = "pzt-admin-pw"
RCON_PW = "pzt-rcon-pw"


def new_run_dir(prefix):
    run_id = datetime.datetime.now().strftime(f"{prefix}-%Y%m%d-%H%M%S")
    run_dir = os.path.join(RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_id, run_dir
