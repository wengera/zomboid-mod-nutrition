"""f_grade_4 -- the LLM session's report, pass 4 (Plan 24 Task 17: kills the headline): f_grade.py's command line (that script untouched,
its default grade_f2) over an f_goals_3 artifact (graded by grade_f4): prints gates_f.report_lines_f4 one finding a line, then grade_f4 as
strict JSON (inf and NaN as null). d_grade.py's form: 0 whenever the artifact was read, 2 on a bad call or an
unreadable artifact.

    python testing/agent/drivers/f_grade_4.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_f import grade_f4    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402
from agent.drivers.e_grade_4 import load_log   # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: f_grade_4.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_f4(out, None, load_log(argv[0]))
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
