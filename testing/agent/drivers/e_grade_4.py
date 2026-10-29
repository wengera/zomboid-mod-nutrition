"""e_grade_4 -- the chain sessions' report, pass 4 (Plan 24 Task 17: kills the headline, the stance held, the riding
bandages, the care yield, the glides): e_grade_3.py's command line (that script frozen with the E6 artifact's grade_e3
output; CLAUDE.md section 5) over grade_e4, gate_e4 and report_lines_e4: prints the report lines (the first reads
`kills <n> (engine <e>, planner <p>); <survived|died at m>; <game minutes>`) one finding a line, then the grade (or the
gate) as strict JSON (inf and NaN as null). d_grade.py's form: 0 whenever the artifacts were read, 2 on a bad call or an
unreadable artifact.

The care yield and the dead skip are read off the decision log: the `decision.log` beside an artifact (the run's copy,
`xs.copied`) is read when it is there and every line parses, else the grade carries no `yields.log` and the report
says so.

    python testing/agent/drivers/e_grade_4.py <artifact.json> [<prev artifact.json>]
    python testing/agent/drivers/e_grade_4.py --chain <a1.json> <a2.json> [...]      # gate_e4 over the chain
"""
import json
import math
import os
import sys

TESTING = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if TESTING not in sys.path:
    sys.path.insert(0, TESTING)

from agent.base.gates_e import gate_e4, grade_e4, report_lines_e4    # noqa: E402


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
        print("usage: e_grade_4.py <artifact.json> [<prev artifact.json>] | --chain <a1.json> <a2.json> ...")
        return 2
    try:
        outs = [load(p) for p in paths]
    except (OSError, ValueError) as e:
        print(f"cannot read an artifact: {type(e).__name__}: {e}")
        return 2
    logs = [load_log(p) for p in paths]
    if chain:
        res = gate_e4(outs)
        grades = [grade_e4(o, outs[i - 1] if i else None, logs[i]) for i, o in enumerate(outs)]
        for line in report_lines_e4(dict(grades[-1], gate=res)):
            print(line)
    else:
        res = grade_e4(outs[0], outs[1] if len(outs) > 1 else None, logs[0])
        for line in report_lines_e4(res):
            print(line)
    print(json.dumps(finite(res), indent=1, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
