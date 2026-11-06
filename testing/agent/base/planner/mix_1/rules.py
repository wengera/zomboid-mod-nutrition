"""mix_1's rules over the tactical view (Plan 31 Task 13; `task-13-composition-read.md` § 7, "mix_1"): the tactician's
doctrine (`tactician.fallback`), its rubric (`tactician.rubric`) and its table (`tactician.table`), each with the two
pieces mix_1 adds, everything else imported from the tactician unchanged.

The two pieces:

1. **`clear`, the ladder's lone-idle seek as a doctrine rule** (`engage.Engage._sought`, ruling P24-X, cut to one
   zombie after P24-AT's `_lone`): armed, no group (`fallback.is_group`), and exactly one standing zombie listed within
   ENGAGE_R (9), idle or aware, which the decider has read reachable (the view's `clear` key, below) → `fight` it. It
   sits after `fight` and `unarmed` and before `night`, `goal`, `loot`, `travel` and `explore`, so it reaches only what
   `fight` leaves: one idle zombie between DANGER_R and ENGAGE_R (round one's tactician left 6073 at 8.4 tiles for 79 s,
   trial 4). With two or more standing within ENGAGE_R it does not fire (the `fight` rule's stand lets them come; U's
   trial-7 walk toward one of a pair is not repeated). The lone zombie binds (`clear_due`, read by `bound`) whichever
   rule fights it: `clear` for an idle one, `fight` for an aware one coming within ENGAGE_R, which the tactician's
   `fight` rule answers but its `bound` leaves to the running play until it is within DANGER_R (E23, 71.5 to 73.5 s:
   26240 coming from 7.2 to 6.1 tiles under a running travel). So the table's cells never answer over it, a running
   strategic play is replaced at once (the tactician's `rule` path, logged rule `clear` by the decider), and the
   rubric's `lone_not_cleared` vetoes a model answer that is no fight while it binds.
2. **The crawler, a threat at the dressing** (round one's doctrine death, trial 10: the crawler 15465, `onFloor` and
   `crawler` both true, bit through the Dress at 1.0 to 1.1 tiles three times; every variant's `standing` drops it):
   a crawler within KEEP_R (2.5) blocks the dressing (`keep_clear`, read by `bleed`'s test and by `dress_due`), and the
   decider's `crawler` guard finishes it first. The rubric's `crawler_first` vetoes a model answer that leaves a
   crawler within KEEP_R unfinished (nothing standing within KEEP_R) for anything but a retreat.

A crawler is the frame's `crawler` true, one predicate for the view and the world (fix 1, review-t13-mix1 finding 3):
the view's `posture == "crawler"` (`tactician.tview.posture`) and the world record's `is_crawler` read the same field,
whatever `onFloor` reads. Every crawler record in the four rings read for this package (F15, E23, trials 4 and 10: 528,
all trial 10's) carried `onFloor` true too, which `test_mix_1_replay.py` pins.

The view's `clear` key: the label of the zombie `lone(view)` names, set by the decider (`decide.Mix1._masked`) only
when `Survive._engageable` reads it reachable (the ladder's own reading: on the character's side of a building's
walls, chasing, or its line clear, or a square beside it in the bounded flood; idle beyond DANGER_R while the character
holds a room or door square is not), else None. The rules read it as given: they never touch the World.

No constant is new or changed: ENGAGE_R, DANGER_R, KEEP_R and LISTED_R are `policies`'; GROUP_N the tactician's."""
from agent.base.planner.night import TIRED_T
from agent.base.planner.policies import DANGER_R, ENGAGE_R, KEEP_R
from agent.base.planner.tactician import fallback as F
from agent.base.planner.tactician import table as TT
from agent.base.planner.tactician.plays import RETREATS

RULE_NAMES = ("reach", "bleed", "group", "fight", "unarmed", "clear", "night", "goal", "loot", "travel", "explore")


# -- the crawler ----------------------------------------------------------------------------------------------------
def is_crawler(z):
    """World record `z` is a crawler: the frame's `crawler` true, as the view reads it (the module docstring)."""
    return z.get("crawler") is True


def crawlers(view, r):
    """The view's crawlers within `r` tiles, nearest first (the view's order)."""
    return [z for z in view.get("zombies") or () if z.get("posture") == "crawler" and (z.get("dist") or 0) <= r]


def keep_clear(view):
    """Nothing standing and nothing crawling within KEEP_R: the dressing may start (piece 2)."""
    return not F._standing(view, KEEP_R) and not crawlers(view, KEEP_R)


# -- the lone zombie ------------------------------------------------------------------------------------------------
def lone(view):
    """The label of the one standing zombie the view lists within ENGAGE_R, idle or aware, else None (two or more,
    or none). The decider reads its reach (`Survive._engageable`) and sets the view's `clear` key from it."""
    s = F._standing(view, ENGAGE_R)
    return s[0]["label"] if len(s) == 1 else None


def clear_target(view):
    """The `clear` rule's target: the view's `clear` label while it is still `lone(view)`'s, armed, and no group."""
    c = view.get("clear")
    if c is None or c != lone(view) or not F.armed(view) or F.is_group(view):
        return None
    return c


# -- the doctrine (tactician.fallback's, with the two pieces) -------------------------------------------------------
def _tests(view):
    """(rule, play type, test) in RULE_NAMES order: `tactician.fallback._tests` (829038d6) with `bleed` reading
    `dress_due` (its own test with `keep_clear`, piece 2) and `clear` after `unarmed` (piece 1); every other test as
    the tactician's."""
    s6, keep = F._standing(view, DANGER_R), F._standing(view, KEEP_R)
    n = view.get("needs") or {}
    tired = (n.get("fatigue") or 0) > TIRED_T
    bs = view.get("buildings") or ()
    yield "reach", "fight", F.armed(view) and bool(keep)
    yield "bleed", "dress", dress_due(view)
    yield "group", ("kite" if s6 else "avoid"), F.is_group(view)
    coming = [z for z in F._standing(view, ENGAGE_R) if z.get("targets_me")]
    yield "fight", "fight", F.armed(view) and (1 <= len(s6) <= 2 or 1 <= len(coming) <= 2)
    yield "unarmed", "kite", not F.armed(view) and bool(s6)
    yield "clear", "clear", clear_target(view) is not None
    yield "night", "shelter", bool(n.get("night") or tired) and any(b.get("shelter") for b in bs)
    yield "goal", "loot", F._goal_building(view) is not None
    yield "loot", "loot", any(b.get("looted") is False for b in bs)
    yield "travel", "travel", bool(bs)
    yield "explore", "travel", True


def target_for(play, view):
    """`tactician.fallback.target_for`, and the `clear` rule's own: a fight at the lone zombie, why `clear`."""
    if play == "clear":
        t = clear_target(view)
        return None if t is None else {"play": "fight", "target": t, "bound": "dead", "why": "clear"}
    return F.target_for(play, view)


def doctrine(view):
    """(rule, flat answer) of the first rule whose test holds and whose play the view admits: `tactician.fallback.
    doctrine` (829038d6) over this module's `_tests`, the stand where a retreat names no refuge kept as it is."""
    for rule, play, ok in _tests(view):
        if not ok:
            continue
        ans = target_for(play, view)
        if ans is None and play in ("kite", "avoid"):
            stand = F.target_for("fight", view)
            ans = None if stand is None else dict(stand, why="group" if rule == "group" else "unarmed")
        if ans is not None:
            return rule, ans
    return None, None


# -- the rubric (tactician.rubric's, with the two pieces) -----------------------------------------------------------
def dress_due(view):
    """The dressing binds: a bleed, nothing standing or crawling within KEEP_R (piece 2), something to dress with."""
    return bool(F.bleeding(view)) and keep_clear(view) and F.dress_with(view) is not None


def fight_due(view):
    """`tactician.rubric.fight_due` over this module's `dress_due`: one standing within DANGER_R, armed, no dressing."""
    return len(F._standing(view, DANGER_R)) == 1 and F.armed(view) and not dress_due(view)


def clear_due(view):
    """The lone zombie binds the view (piece 1): `clear_target` names one and the doctrine's answer is a fight at it
    (by `clear`, or by `fight` for one coming; an earlier rule's other answer, a dressing or a group's, stands)."""
    t = clear_target(view)
    if t is None:
        return False
    ans = doctrine(view)[1]
    return ans is not None and ans["play"] == "fight" and ans["target"] == t


def crawler_due(view):
    """A crawler within KEEP_R and nothing standing within KEEP_R: it is finished first (piece 2; the decider's
    guard)."""
    return bool(crawlers(view, KEEP_R)) and not F._standing(view, KEEP_R)


def violations(view, answer):
    """The rules `answer` breaks at `view`, in order: the tactician's three (`tactician.rubric.violations`, its
    `dress_due` and `fight_due` this module's), then `lone_not_cleared` (no fight while `clear` binds) and
    `crawler_first` (a crawler within KEEP_R, nothing standing within KEEP_R, and the answer neither a fight at a
    crawler nor a retreat)."""
    play = (answer or {}).get("play")
    out = []
    if fight_due(view) and play != "fight":
        out.append("lone_not_fight")
    if dress_due(view) and play != "dress":
        out.append("bleed_not_dress")
    if play == "travel" and (answer or {}).get("to") == "explore" and view.get("buildings"):
        out.append("travel_nowhere")
    if clear_due(view) and play != "fight":
        out.append("lone_not_cleared")
    if crawler_due(view) and play not in RETREATS and not (
            play == "fight" and (answer or {}).get("target") in {z["label"] for z in crawlers(view, KEEP_R)}):
        out.append("crawler_first")
    return out


def bound(view):
    """One of the rules binds the view, so the doctrine answers it whatever a cell holds: the tactician's two (one
    standing within DANGER_R while armed; a dressing due) and `clear`."""
    return fight_due(view) or dress_due(view) or clear_due(view)


# -- the table (tactician.table's, its answer over this module's doctrine) -------------------------------------------
class Table(TT.Table):
    """`tactician.table.Table` (its cells, `load`, `fit`, `save` as they are), its `answer` reading this module's
    `bound`, `target_for` and `doctrine` (829038d6's `Table.answer` otherwise)."""

    def answer(self, view):
        k = TT.key(view)
        play = None if bound(view) else self.cells.get(k)
        if play is not None:
            ans = target_for(play, view)
            if ans is not None:
                return "table", k, ans
        rule, ans = doctrine(view)
        return "doctrine", rule, ans

