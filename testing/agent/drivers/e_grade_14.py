"""e_grade_14 -- the chain sessions' report, pass 14 (Plan 26 Task 5: grade_e14's readings with survival iteration 17's six read off the
decision log's why fields, the state log's act lines, frames and map and the artifact's actions: the window way out, the stand's second
way out, the inside corner's shove, the bleed under the threat branch, the worn wear and the edge-out check): `e_grade_13.py` copied under
its own key (that script frozen; CLAUDE.md section 5) over grade_e14, gate_e14 and report_lines_e14 of agent.base.grades.e14. What is read
beside an artifact, the output and the exit codes are e_grade_13.py's.

    python testing/agent/drivers/e_grade_14.py <artifact.json> [<prev artifact.json>]
    python testing/agent/drivers/e_grade_14.py --chain <a1.json> <a2.json> [...]
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.grades.e14 import gate_e14, grade_e14, report_lines_e14    # noqa: E402


def finite(v):
    """d_grade.py finite, copied: the value with every inf and NaN float mapped to None (strict JSON)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [finite(x) for x in v]
    return v


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dir(path):
    """The directory beside the artifact `path`: where its state*.log files and decision.log sit."""
    return os.path.dirname(os.path.abspath(path))


def load_log(path):
    """The decision.log lines beside the artifact `path` (dicts), else None when the file is absent or unreadable."""
    p = os.path.join(os.path.dirname(os.path.abspath(path)), "decision.log")
    try:
        with open(p, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        return None
    return [r for r in rows if isinstance(r, dict)]


def main(argv):
    chain = bool(argv) and argv[0] == "--chain"
    paths = argv[1:] if chain else argv
    if not paths or (not chain and len(paths) > 2):
        print("usage: e_grade_14.py <artifact.json> [<prev artifact.json>] | --chain <a1.json> <a2.json> ...")
        return 2
    try:
        outs = [load(p) for p in paths]
    except (OSError, ValueError) as e:
        print(f"cannot read an artifact: {type(e).__name__}: {e}")
        return 2
    logs = [load_log(p) for p in paths]
    if chain:
        res = gate_e14(outs)
        grades = [grade_e14(o, outs[i - 1] if i else None, logs[i], state_dir=_dir(paths[i])) for i, o in enumerate(outs)]
        for line in report_lines_e14(dict(grades[-1], gate=res)):
            print(line)
    else:
        res = grade_e14(outs[0], outs[1] if len(outs) > 1 else None, logs[0], state_dir=_dir(paths[0]))
        for line in report_lines_e14(res):
            print(line)
    print(json.dumps(finite(res), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
