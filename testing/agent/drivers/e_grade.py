"""e_grade -- the chain sessions' report (Plan 23 Task 15) over e_day artifacts: prints gates_e.report_lines_e one finding
a line, then the grade (or the gate) as strict JSON (inf and NaN as null). d_grade.py's form: 0 whenever the artifacts
were read, 2 on a bad call or an unreadable artifact.

    python testing/agent/drivers/e_grade.py <artifact.json> [<prev artifact.json>]
    python testing/agent/drivers/e_grade.py --chain <a1.json> <a2.json> [...]      # gate_e1 over the chain
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_e import gate_e1, grade_e1, report_lines_e    # noqa: E402


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


def main(argv):
    chain = bool(argv) and argv[0] == "--chain"
    paths = argv[1:] if chain else argv
    if not paths or (not chain and len(paths) > 2):
        print("usage: e_grade.py <artifact.json> [<prev artifact.json>] | --chain <a1.json> <a2.json> ...")
        return 2
    try:
        outs = [load(p) for p in paths]
    except (OSError, ValueError) as e:
        print(f"cannot read an artifact: {type(e).__name__}: {e}")
        return 2
    if chain:
        res = gate_e1(outs)
        grades = [grade_e1(o, outs[i - 1] if i else None) for i, o in enumerate(outs)]
        for line in report_lines_e(dict(grades[-1], gate=res)):
            print(line)
    else:
        res = grade_e1(outs[0], outs[1] if len(outs) > 1 else None)
        for line in report_lines_e(res):
            print(line)
    print(json.dumps(finite(res), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
