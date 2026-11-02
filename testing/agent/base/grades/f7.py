"""grades.f7 -- the LLM session grade, pass 7 (Plan 26 Task 4): `grade_f7` is `gates_f.grade_f6` under "grade_f7" with
the three readings of the LLM source's fourth round (Plan 26 Task 3), read off the goals log (`goals.log`, one JSON
row per call: `cycle`, `reask`, `skipped` [{goal, why}], `goal`, `error`, `answer`, `prompt`, `ok`, ...):

  open_views  P26-G, the all-looted line: the views whose prompt carries the `open:` line and the answers on them.
  objects     P26-F, every object parsed: the objects per answer (`llm.objects`) and the `skipped` ones by why.
  reasks      P26-H, the re-ask once: the cycles re-asked, the re-asks taken and those that fell to the stand-in.

Each reading is {"read": False} without the goals log. A row's stand-in is read as grade_f6 reads a fallback (a row
whose `ok` is not true), counted only on the row that ends its cycle (a refused first call re-asked is no stand-in).
Frozen once an artifact carries its output (`grades/__init__.py`); `gates_f` and every driver stay untouched."""
from agent.base import gates_e as E
from agent.base import gates_f as F
from agent.base.planner.llm import objects as llm_objects
from agent.base.planner.view import OPEN_KEY

OPEN_LINE = OPEN_KEY + ": "          # the view's `open` key rendered as its own `key: value` line (view._open)
INVALID = "invalid: "


def _rows(goal_lines):
    return [r for r in E._l(goal_lines) if isinstance(r, dict)]


def _has_open(prompt):
    """True when the rendered view carries the `open:` line (P26-G: every listed building reads looted)."""
    return any(ln.startswith(OPEN_LINE) for ln in str(prompt).splitlines())


def _all_looted(prompt):
    """True when the view's building line lists at least one building and every one reads `L` (an inference off the
    view: the condition `view.view` sets `open` on)."""
    shown = F._view_buildings(prompt)
    return bool(shown) and all("L" in b["flags"] for b in shown)


def _cycle_key(i, r):
    """The cycle a row belongs to: its `cycle` (a call and its re-ask share it), else the row's own index (a log of
    the third round or earlier: every call its own cycle)."""
    c = r.get("cycle")
    return ("c", c) if isinstance(c, int) and not isinstance(c, bool) else ("i", i)


def _ends_cycle(rows):
    """[bool] per row: no later row of the same cycle is a re-ask (the row whose answer stood for its cycle)."""
    keys = [_cycle_key(i, r) for i, r in enumerate(rows)]
    last = {k: i for i, k in enumerate(keys)}
    return [last[k] == i for i, k in enumerate(keys)]


def _stand_in(r, ends):
    return ends and r.get("ok") is not True


def f_open_views(rows, read):
    """The all-looted line (P26-G, `view.OPEN_KEY`): {read, n, taken, refused, other, stand_in, all_looted,
    all_looted_no_open}. Reading: `n` the rows whose prompt carries the `open:` line, `taken` the goals taken on them by
    type (`ok` true), `refused` the answers refused there by why (`error` "invalid: <why>"), `other` the other errors
    (malformed, timeout, cli error) and `stand_in` the rows that fell to the scripted stand-in (not `ok` and ending
    their cycle). Inference off the view: `all_looted` the rows whose building line lists buildings that all read `L`,
    and `all_looted_no_open` those without the `open:` line (must read 0 on a log of the fourth round; a log written
    before P26-G reads every all-looted view here)."""
    if not read:
        return {"read": False}
    ends = _ends_cycle(rows)
    n = stand = looted = no_open = 0
    taken, refused, other = {}, {}, {}
    for r, e in zip(rows, ends):
        p = r.get("prompt")
        if _all_looted(p):
            looted += 1
            no_open += 0 if _has_open(p) else 1
        if not _has_open(p):
            continue
        n += 1
        g = F._goal_of(r)
        err = str(r.get("error"))
        if g.get("type") is not None:
            taken[str(g["type"])] = taken.get(str(g["type"]), 0) + 1
        elif err.startswith(INVALID):
            refused[err[len(INVALID):]] = refused.get(err[len(INVALID):], 0) + 1
        else:
            other[err] = other.get(err, 0) + 1
        stand += 1 if _stand_in(r, e) else 0
    return {"read": True, "n": n, "taken": taken, "refused": refused, "other": other, "stand_in": stand,
            "all_looted": looted, "all_looted_no_open": no_open}


def f_objects(rows, read):
    """Every object parsed (P26-F, `llm.objects`): {read, answers, per_answer, multi, multi_calls, skipped_by_why,
    skipped_invalid, taken_after_skip}. Reading: `per_answer` a histogram of the JSON objects in each row's `answer`
    text counted by `llm.objects` itself (never `skipped`'s length: `skipped` lists the invalid objects and, with
    nothing taken, every object), `answers` the rows read, `multi` the answers holding two or more and `multi_calls`
    their calls (the row's 1-based place in the log), `skipped_by_why` every `skipped` entry by its `why`,
    `skipped_invalid` those whose `goal` is None (an object that failed validation) and `taken_after_skip` the rows
    that took a goal with an earlier object refused (a `skipped` entry with a `goal`: those before the taken one; an
    invalid object, `goal` None, counts wherever it stood and is no earlier skip; the rule taking a later object,
    F7's call 8)."""
    if not read:
        return {"read": False}
    hist, by, invalid, multi, after = {}, {}, 0, [], 0
    for i, r in enumerate(rows):
        k = len(llm_objects(r.get("answer") if isinstance(r.get("answer"), str) else ""))
        hist[str(k)] = hist.get(str(k), 0) + 1
        multi += [i + 1] if k >= 2 else []
        sk = [E._d(s) for s in E._l(r.get("skipped"))]
        for s in sk:
            by[str(s.get("why"))] = by.get(str(s.get("why")), 0) + 1
            invalid += 1 if s.get("goal") is None else 0
        after += 1 if r.get("ok") is True and any(s.get("goal") is not None for s in sk) else 0
    return {"read": True, "answers": len(rows), "per_answer": hist, "multi": len(multi), "multi_calls": multi,
            "skipped_by_why": by,
            "skipped_invalid": invalid, "taken_after_skip": after}


def f_reasks(out, rows, read):
    """The re-ask once (P26-H): {read, n, taken, stand_in, unpaired, cycles, reasks_total, agree}. Reading: `n` the
    rows whose `reask` reads true (one per re-asked cycle), `taken` those that took a goal (`ok` true), `stand_in`
    those that fell to the scripted stand-in (not `ok`, as grade_f6 reads a fallback), `unpaired` the re-asks whose
    cycle has no first call before them (must read 0), `cycles` the distinct cycles of the log (None on a log of the
    third round or earlier, whose rows carry no `cycle`), `reasks_total` the artifact's `loop.llm.reasks_total`
    (`LLMSource.totals`; None when absent) and `agree` whether it equals `n` (None unless both are read)."""
    if not read:
        return {"read": False}
    re_ = [(i, r) for i, r in enumerate(rows) if r.get("reask") is True]
    firsts = {}
    for i, r in enumerate(rows):
        if r.get("reask") is not True:
            firsts.setdefault(_cycle_key(i, r), i)
    unpaired = sum(1 for i, r in re_ if not (_cycle_key(i, r) in firsts and firsts[_cycle_key(i, r)] < i))
    cycles = {r.get("cycle") for r in rows if isinstance(r.get("cycle"), int) and not isinstance(r.get("cycle"), bool)}
    tot = E._n(E._d(E._d(E._d(out).get("loop")).get("llm")).get("reasks_total"))
    return {"read": True, "n": len(re_), "taken": sum(1 for _, r in re_ if r.get("ok") is True),
            "stand_in": sum(1 for _, r in re_ if r.get("ok") is not True), "unpaired": unpaired,
            "cycles": len(cycles) if cycles else None, "reasks_total": tot,
            "agree": (tot == len(re_)) if tot is not None else None}


def _lines_f7(g):
    o, b, r = (E._d(g.get(k)) for k in ("open_views", "objects", "reasks"))
    out = []
    out.append(("open views (P26-G) [reading]: %s views carrying the `open:` line, taken %s, refused %s, other %s, "
                "%s stand-ins; [inference off the view] %s all-looted views, %s of them without the line (must read 0 "
                "on a fourth-round log)" % (o.get("n"), o.get("taken"), o.get("refused"), o.get("other"),
                                            o.get("stand_in"), o.get("all_looted"), o.get("all_looted_no_open")))
               if o.get("read") else "open views (P26-G): no goals.log read")
    out.append(("objects (P26-F) [reading]: %s answers, objects per answer %s (%s with two or more, at calls %s), "
                "skipped by why %s (%s invalid), %s taken after a skipped object" % (
                    b.get("answers"), b.get("per_answer"), b.get("multi"), b.get("multi_calls"),
                    b.get("skipped_by_why"), b.get("skipped_invalid"), b.get("taken_after_skip")))
               if b.get("read") else "objects (P26-F): no goals.log read")
    out.append(("re-asks (P26-H) [reading]: %s cycles re-asked, %s taken on the re-ask, %s fell to the stand-in, %s "
                "unpaired (must read 0), %s cycles; reasks_total %s (%s)" % (
                    r.get("n"), r.get("taken"), r.get("stand_in"), r.get("unpaired"), r.get("cycles"),
                    r.get("reasks_total"), "agree" if r.get("agree") is True else "disagree" if r.get("agree") is False
                    else "not read")) if r.get("read") else "re-asks (P26-H): no goals.log read")
    return out


def report_lines_f7(g):
    """report_lines_f6's lines then one line per pass 7 reading, each marked reading or inference."""
    g = E._d(g)
    return F.report_lines_f6(g) + _lines_f7(g)


def grade_f7(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_f6 under "grade_f7" with the three readings of the LLM source's fourth round: `open_views`, `objects` and
    `reasks` (each {"read": False} without the goals log); every other key is grade_f6's."""
    g = F.grade_f6(out, prev, decision_lines, state_dir, lines, goal_lines)
    g["grade"] = "grade_f7"
    read, rows = goal_lines is not None, _rows(goal_lines)
    g["open_views"] = f_open_views(rows, read)
    g["objects"] = f_objects(rows, read)
    g["reasks"] = f_reasks(out, rows, read)
    g["report_lines"] = report_lines_f7(g)
    return g


def gate_f7(outs):
    """gate_f6 (grade_f7 changes none of what it reads), named gate_f7."""
    return F.gate_f6(outs)
