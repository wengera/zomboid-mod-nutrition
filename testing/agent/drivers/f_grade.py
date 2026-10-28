"""f_grade -- the LLM session's report (Plan 23 Task 15) over an f_goals artifact: prints gates_f.report_lines_f one
finding a line, then grade_f1 as strict JSON (inf and NaN as null). d_grade.py's form: 0 whenever the artifact was
read, 2 on a bad call or an unreadable artifact.

    python testing/agent/drivers/f_grade.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_f import grade_f1    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: f_grade.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_f1(out)
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
