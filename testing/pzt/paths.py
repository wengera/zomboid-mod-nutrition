import datetime
import os

PZ_DIR = r"D:\SteamLibrary\steamapps\common\ProjectZomboid"
JAVA = os.path.join(PZ_DIR, "jre64", "bin", "java.exe")
EXE = os.path.join(PZ_DIR, "ProjectZomboid64.exe")
WORKSHOP_DIR = r"D:\SteamLibrary\steamapps\workshop\content\108600"

PKG = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(PKG)
RUNS = os.path.join(TESTING, "runs")
FIXTURES = os.path.join(TESTING, "fixtures")
HARNESS_MODS = {"PZTestKit": os.path.join(TESTING, "PZTestKit", "PZTestKit")}

ADMIN_USER = "admin"          # bootstrap account created by -adminpassword
ADMIN_PW = "pzt-admin-pw"
RCON_PW = "pzt-rcon-pw"


def new_run_dir(prefix):
    run_id = datetime.datetime.now().strftime(f"{prefix}-%Y%m%d-%H%M%S")
    run_dir = os.path.join(RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_id, run_dir
