"""x4_grade -- X4's grade (Plan 22, "the link") over an x4_link artifact: prints agent.base.gates.gate_x4 as JSON
(the verdict, every gate's {ok, value, threshold, n} and the ungraded sidecar trigger); exit 0 on GO, 1 on NO-GO, 2 on
a bad call or an unreadable artifact. a_grade_4.py's form over gate_x4.

    python testing/agent/drivers/x4_grade.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates import gate_x4                   # noqa: E402


def main(argv):
    if len(argv) != 1:
        print("usage: x4_grade.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    if not isinstance(out, dict):
        print(f"cannot read {argv[0]}: not an artifact dict")
        return 2
    g = gate_x4(out)
    print(json.dumps(g, indent=1, sort_keys=True))
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
