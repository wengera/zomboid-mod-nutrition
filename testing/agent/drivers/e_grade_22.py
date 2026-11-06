"""e_grade_22 -- the chain sessions' report, pass 22 (Plan 31 Task 15b: grade_x1 over a chain session, the twenty-first
pass's readings under its `base` plus the trial loop's readings, the meet's and the Dress's, clipped at the loop's stop,
off the record, the state log and the decision log): the previous pass's script copied under its own key (that script
frozen; CLAUDE.md section 5) over grade_x1 (`kind` "e"), gate_x1 and report_lines_x1 of agent.base.grades.x1. What is
read beside an artifact, the output and the exit codes are the pass before's.

    python testing/agent/drivers/e_grade_22.py <artifact.json> [<prev artifact.json>]
    python testing/agent/drivers/e_grade_22.py --chain <a1.json> <a2.json> [...]
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.grades.x1 import gate_x1, grade_x1, report_lines_x1    # noqa: E402

KIND = "e"             # the session's kind grade_x1 reads: a chain session's base is grade_e21


def finite(v):
    """d_grade.py finite, copied: the value with every inf and NaN float mapped to None (strict JSON)."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: finite(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [finite(x) for x in v]
    return v


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dir(path):
    """The directory beside the artifact `path`: where its state*.log files and decision.log sit."""
    return os.path.dirname(os.path.abspath(path))


def load_log(path):
    """The decision.log lines beside the artifact `path` (dicts), else None when the file is absent or unreadable."""
    p = os.path.join(os.path.dirname(os.path.abspath(path)), "decision.log")
    try:
        with open(p, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh if l.strip()]
    except (OSError, ValueError):
        return None
    return [r for r in rows if isinstance(r, dict)]


def main(argv):
    chain = bool(argv) and argv[0] == "--chain"
    paths = argv[1:] if chain else argv
    if not paths or (not chain and len(paths) > 2):
        print("usage: e_grade_22.py <artifact.json> [<prev artifact.json>] | --chain <a1.json> <a2.json> ...")
        return 2
    try:
        outs = [load(p) for p in paths]
    except (OSError, ValueError) as e:
        print(f"cannot read an artifact: {type(e).__name__}: {e}")
        return 2
    logs = [load_log(p) for p in paths]
    if chain:
        res = gate_x1(outs)
        grades = [grade_x1(o, logs[i], state_dir=_dir(paths[i]), prev=outs[i - 1] if i else None, kind=KIND)
                  for i, o in enumerate(outs)]
        for line in report_lines_x1(dict(grades[-1], gate=res)):
            print(line)
    else:
        res = grade_x1(outs[0], logs[0], state_dir=_dir(paths[0]), prev=outs[1] if len(outs) > 1 else None,
                       kind=KIND)
        for line in report_lines_x1(res):
            print(line)
    print(json.dumps(finite(res), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
