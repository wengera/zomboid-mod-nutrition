"""f_grade_5 -- the LLM session's report, pass 5 (Plan 24 Task 35: the strategy lines' effect, the wants, the refusals, the
latencies and the fight readings of grade_e7): f_grade_4.py's command line (that script frozen with its grade_f4 output) over an
f_goals_4 artifact (graded by grade_f5): prints gates_f.report_lines_f5 one finding a line, then grade_f5 as strict JSON (inf and NaN
as null). d_grade.py's form: 0 whenever the artifact was read, 2 on a bad call or an unreadable artifact.

Files read beside the artifact when they are there: `decision.log` and the `state*.log` files with `shots/shots.jsonl`
(grade_e7's readings) and `goals.log` (the model's prompts and answers, one JSON line each; the readings that need it say so
when it is absent).

    python testing/agent/drivers/f_grade_5.py <artifact.json>
"""
import json
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_f import grade_f5    # noqa: E402
from agent.drivers.e_grade import finite   # noqa: E402
from agent.drivers.e_grade_7 import _dir, load_log   # noqa: E402


def load_goals(path):
    """The goals.log rows (dicts) beside the artifact `path`, a line that does not parse skipped, else None when the
    file is absent or unreadable."""
    p = os.path.join(_dir(path), "goals.log")
    rows = []
    try:
        with open(p, encoding="utf-8") as fh:
            for ln in fh:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    rows.append(r)
    except OSError:
        return None
    return rows


def main(argv):
    if len(argv) != 1:
        print("usage: f_grade_5.py <artifact.json>")
        return 2
    try:
        with open(argv[0], encoding="utf-8") as fh:
            out = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read {argv[0]}: {type(e).__name__}: {e}")
        return 2
    g = grade_f5(out, None, load_log(argv[0]), state_dir=_dir(argv[0]), goal_lines=load_goals(argv[0]))
    for line in g["report_lines"]:
        print(line)
    print(json.dumps(finite(g), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
