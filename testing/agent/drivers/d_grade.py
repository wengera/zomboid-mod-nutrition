"""d_grade -- the survival acceptance's report (Plan 22 Task 17, spec § 10) over a d_survive artifact: prints
agent.base.gates.report_lines_d(grade_d(out)), one finding a line, then grade_d as strict JSON (inf and NaN as null).
c_grade.py's form. No gate: the exit code is never a verdict; 0 whenever the artifact was read, 2 on a bad call or an
unreadable artifact.

    python testing/agent/drivers/d_grade.py <artifact.json>
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates import grade_d, report_lines_d    # noqa: E402


def finite(v):
    """c_grade.py's finite, copied: the value with every inf and NaN float mapped to None (strict JSON)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [finite(x) for x in v]
    return v


def main(argv):
    if len(argv) != 1:
        print("usage: d_grade.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_d(out)
    for line in report_lines_d(g):
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
