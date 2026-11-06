"""The bench's rubric (Plan 31 Task 11, variant T; the amendments' item 2, the proposal § 7 score (a)): the doctrine's
three checkable rules, read off one tactical view and one answer (a flat play object, or None for none).

- `lone_not_fight`: one standing zombie within DANGER_R, armed, and the view not a `dress` one (below, so the two
  rules never both bind: the dressing comes before a fight with a zombie still beyond KEEP_R, the common amendments'
  item 5), but the answer is not `fight`.
- `bleed_not_dress`: a part bleeds, no standing zombie within KEEP_R and something held to dress or tear
  (`fallback.dress_with`), but the answer is not `dress`.
- `travel_nowhere`: a `travel` to `explore` while a building is listed (every walk has a named target: memory
  `stand-and-fight-dress-first` 5, ruling P24-Y).

`violations(view, answer) -> [rule]`; None (no valid answer) is read against the rules as no play."""
from agent.base.planner.policies import DANGER_R, KEEP_R
from agent.base.planner.tactician import fallback as F

RULES = ("lone_not_fight", "bleed_not_dress", "travel_nowhere")


def dress_due(view):
    """The view binds the dressing rule: a bleed, no standing zombie within KEEP_R, something to dress with."""
    return bool(F.bleeding(view)) and not F._standing(view, KEEP_R) and F.dress_with(view) is not None


def fight_due(view):
    """The view binds the lone-zombie rule: one standing within DANGER_R, armed, and no dressing due."""
    return len(F._standing(view, DANGER_R)) == 1 and F.armed(view) and not dress_due(view)


def violations(view, answer):
    """The RULES `answer` breaks at `view`, in order."""
    play = (answer or {}).get("play")
    out = []
    if fight_due(view) and play != "fight":
        out.append("lone_not_fight")
    if dress_due(view) and play != "dress":
        out.append("bleed_not_dress")
    if play == "travel" and (answer or {}).get("to") == "explore" and view.get("buildings"):
        out.append("travel_nowhere")
    return out
