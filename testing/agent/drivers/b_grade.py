"""b_grade -- Stage B's grade (spec § 4.2) over a b_actions artifact: prints grades.gate_b as JSON (inf and NaN as
null); exit 0 on GO, 1 on NO-GO, 2 on a bad call or an unreadable artifact.

    python testing/agent/drivers/b_grade.py <artifact.json>
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.grades import gate_b                        # noqa: E402


def finite(v):
    """The dict with every inf and NaN float mapped to None (strict JSON)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [finite(x) for x in v]
    return v


def main(argv):
    if len(argv) != 1:
        print("usage: b_grade.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = gate_b(out)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
