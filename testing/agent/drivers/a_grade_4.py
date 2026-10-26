"""a_grade_4 -- Stage A pass 4's grade (the agent harness report's § 6 changes) over an a_pipe_4 artifact: prints
grades.gate_a4 as JSON; exit 0 on GO, 1 on NO-GO, 2 on a bad call or an unreadable artifact. A copy of a_grade.py
(frozen: its output is committed in three artifacts) over gate_a4.

    python testing/agent/drivers/a_grade_4.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.grades import gate_a4                       # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: a_grade_4.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = gate_a4(out)
    print(json.dumps(g, indent=1, sort_keys=True))
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
