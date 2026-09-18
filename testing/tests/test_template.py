import json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(REPO, "testing", "experiments", "_template.py")

def test_template_dry_run_prints_provenance_and_boots_nothing():
    env = dict(os.environ, PZT_TEMPLATE_DRY_RUN="1")
    r = subprocess.run([sys.executable, TEMPLATE], capture_output=True, text=True, env=env, cwd=REPO, timeout=120)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    for key in ("run_id", "session", "profile", "commit", "harness_lua_commit", "harness_lua_dirty",
                "doctor_clean", "acceptance_run", "phases", "dry_run"):
        assert key in out, key
    assert out["dry_run"] is True and out["phases"] == {} and out["doctor_clean"] is None
