"""f_grade -- the LLM session's report (Plan 23 Task 15) over an f_goals artifact: prints gates_f.report_lines_f one
finding a line, then grade_f2 (grade_f1 on `--grade f1`) as strict JSON (inf and NaN as null). d_grade.py's form: 0 whenever the artifact was
read, 2 on a bad call or an unreadable artifact.

    python testing/agent/drivers/f_grade.py [--grade f1|f2] <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_f import grade_f1, grade_f2    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402


def main(argv):
    grade = grade_f2
    if len(argv) == 3 and argv[0] == "--grade" and argv[1] in ("f1", "f2"):
        grade = grade_f1 if argv[1] == "f1" else grade_f2
        argv = argv[2:]
    if len(argv) != 1:
        print("usage: f_grade.py [--grade f1|f2] <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade(out)
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
