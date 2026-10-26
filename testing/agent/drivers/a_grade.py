"""a_grade -- Stage A's grade (spec § 4.1) over an a_pipe artifact: prints grades.gate_a as JSON; exit 0 on GO,
1 on NO-GO, 2 on a bad call or an unreadable artifact.

    python testing/agent/drivers/a_grade.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.grades import gate_a                        # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: a_grade.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = gate_a(out)
    print(json.dumps(g, indent=1, sort_keys=True))
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
