"""c_grade -- Stage C's report (spec § 4.3) over a c_survive or c_survive_dense artifact: prints agent.grade_c.grade_c
as strict JSON (inf and NaN as null). No gate: exit 0 whenever the artifact was read, 2 on a bad call or an unreadable
artifact.

    python testing/agent/drivers/c_grade.py <artifact.json>
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.grade_c import grade_c                      # noqa: E402


def finite(v):
    """The value with every inf and NaN float mapped to None (strict JSON)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [finite(x) for x in v]
    return v


def main(argv):
    if len(argv) != 1:
        print("usage: c_grade.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    print(json.dumps(finite(grade_c(out)), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
