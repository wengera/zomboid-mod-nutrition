"""The fallback doctrine (Plan 31 Task 11, variant T; the proposal § 2 "The fallback doctrine"): Angus's rules as a
table, answering at zero latency whenever no play holds, a bound breaks, or a call is out with nothing running.

`RULES` is the table, tried in order, the first whose test holds answering (`doctrine(view) -> (rule, answer)`, the
answer a flat play object `plays.validate` passes on the same view, or None when no rule holds: no building listed and
nothing near, which the live executor hands to the strategic goal layer):

| rule | test (the tactical view's reads) | play |
|---|---|---|
| `reach` | armed, a standing zombie within KEEP_R (2.5) | `fight` the nearest standing (a zombie in reach is struck) |
| `bleed` | a part bleeds, no standing zombie within KEEP_R, something held to dress or tear | `dress` the worst-bleeding part (least part health) with a bandage, else a rag, else a rip |
| `group` | three or more standing within DANGER_R, or three or more standing and targeting the player within 12 (but never with exactly one standing within DANGER_R while armed), or two standing within DANGER_R unarmed | `kite` the nearest standing toward a refuge while any stands within DANGER_R, else `avoid` toward one |
| `fight` | armed, one or two standing within DANGER_R, or one or two standing and targeting the player within ENGAGE_R (9) | `fight` the nearest standing (one zombie is never fled; the zombies near are cleared before a loot) |
| `unarmed` | unarmed, one standing within DANGER_R | `kite` it toward a refuge |
| `night` | night or tired, a shelter building listed | `shelter` the nearest one |
| `goal` | the strategic goal's building listed and not looted | `loot` it |
| `loot` | an unlooted building listed | `loot` the nearest |
| `travel` | a building listed | `travel` to the nearest |
| `explore` | none of the above, nothing near | `travel` to `explore` (the goal layer's edge walk) |

The sources: Angus's directions (memories `stand-and-fight-dress-first` 1 and 2, `combat-approach-not-flee`,
`clear-then-loot-strategy`: "clear the zombies nearby", ENGAGE_R the ladder's engage radius, `policies.ENGAGE_R`,
ruling P24-X; `intent-doors-sneak`) and the common amendments' item 5 (the dressing before any retreat
from a zombie beyond the stance's reach; a group avoided before it arrives; a retreat to a named refuge, ending in the
stance). The proposal's rule 1 (one standing armed → fight) is split into `reach` and `fight` around the dressing
(a bleed is dressed before a fight with a zombie still beyond reach: the Dress ends `superseded` once a standing zombie
reads within KEEP_R, and `reach` fights it); its rule 2 kites "toward the nearest known door or open square": an open
square is never a refuge here, so with none listed the kite holds the stance (`toward` "stance").

The refuge (`refuge(view)`): the nearest listed door none of whose bearing's neighbours (the compass eighth either
side) holds a standing zombie within DANGER_R and with no zombie at it, else the nearest shelter building so placed,
else None ("stance" for a kite, no avoid).

The targets the table shares (`target_for(play, view)`): the answer this module would give for a play type at a view,
so the cached table (`table.py`) labels a cell with a play type only."""
from agent.base.planner.night import TIRED_T
from agent.base.planner.policies import DANGER_R, ENGAGE_R, KEEP_R, LISTED_R
from agent.base.world import COMPASS

GROUP_N = 3          # standing zombies that make a group (the common amendments' item 5: "three or more aware")
UNARMED_GROUP_N = 2  # ... while unarmed (the proposal's fallback rule 2)
RULE_NAMES = ("reach", "bleed", "group", "fight", "unarmed", "night", "goal", "loot", "travel", "explore")


def _standing(view, r):
    return [z for z in view.get("zombies") or () if z.get("posture") == "standing" and (z.get("dist") or 0) <= r]


def _aware(view):
    return [z for z in _standing(view, LISTED_R) if z.get("targets_me")]


def armed(view):
    return bool((view.get("me") or {}).get("armed"))


def bleeding(view):
    """The bleeding parts, the worst (least part health) first."""
    parts = [p for p in (view.get("body") or {}).get("parts") or () if p.get("bleeding")]
    return sorted(parts, key=lambda p: (p.get("h") if p.get("h") is not None else 100.0, p["label"]))


def dress_with(view):
    """The `with` a dress takes from the kit: a bandage, else a rag (clean or dirty), else a rip; None with nothing."""
    k = view.get("kit") or {}
    if (k.get("bandages") or 0) > 0:
        return "bandage"
    if (k.get("rags") or 0) + (k.get("dirty_rags") or 0) > 0:
        return "rag"
    if (k.get("rip") or 0) + (k.get("unwear") or 0) > 0:
        return "rip"
    return None


def is_group(view):
    """A group (the module docstring's `group` row): three or more standing within DANGER_R; or three or more
    standing and targeting the player within LISTED_R, unless exactly one stands within DANGER_R and the character is
    armed (that one is fought, never fled: memory `stand-and-fight-dress-first` 1, "no flee of any reason"); or two
    standing within DANGER_R while unarmed."""
    s6 = len(_standing(view, DANGER_R))
    if s6 >= GROUP_N or (not armed(view) and s6 >= UNARMED_GROUP_N):
        return True
    return len(_aware(view)) >= GROUP_N and not (s6 == 1 and armed(view))


def _neighbours(b):
    if b not in COMPASS:
        return set()
    i = COMPASS.index(b)
    return {COMPASS[(i - 1) % 8], b, COMPASS[(i + 1) % 8]}


def refuge(view):
    """The refuge's label (the module docstring), else None."""
    bad = set()
    for z in _standing(view, DANGER_R):
        bad |= _neighbours(z.get("bearing"))
    for d in view.get("doors") or ():
        if d.get("bearing") not in bad and not d.get("zombies_near"):
            return d["label"]
    for b in view.get("buildings") or ():
        if b.get("shelter") and b.get("bearing") not in bad and not b.get("here"):
            return b["label"]
    return None


def _nearest_standing(view):
    s = _standing(view, LISTED_R)
    return s[0]["label"] if s else None


def _building(view, label):
    return next((b for b in view.get("buildings") or () if b.get("label") == label), None)


def _goal_building(view):
    g = view.get("goal") or {}
    b = _building(view, g.get("building"))
    return b["label"] if b is not None and b.get("looted") is False else None


def target_for(play, view):
    """The flat answer this module gives for play type `play` at `view` (the module docstring's targets), else None
    when the view admits none (no standing zombie to fight, no bleed, no building)."""
    if play == "fight":
        t = _nearest_standing(view)
        return None if t is None else {"play": "fight", "target": t, "bound": "dead", "why": "lone_chaser"}
    if play == "kite":
        t = _nearest_standing(view)
        if t is None:
            return None
        return {"play": "kite", "target": t, "toward": refuge(view) or "stance", "bound": "alone",
                "why": "group" if is_group(view) else "unarmed"}
    if play == "avoid":
        r = refuge(view)
        return None if r is None else {"play": "avoid", "toward": r, "gait": "sneak", "bound": "clear", "why": "group"}
    if play == "dress":
        parts, w = bleeding(view), dress_with(view)
        if not parts or w is None:
            return None
        return {"play": "dress", "part": parts[0]["label"], "with": w, "bound": "dressed", "why": "bleeding"}
    if play == "shelter":
        b = next((b for b in view.get("buildings") or () if b.get("shelter")), None)
        return None if b is None else {"play": "shelter", "building": b["label"], "bound": "inside", "why": "night"}
    if play == "loot":
        b = _goal_building(view) or next((b["label"] for b in view.get("buildings") or () if b.get("looted") is False),
                                         None)
        return None if b is None else {"play": "loot", "building": b, "want": "any", "bound": "looted", "why": "clear"}
    if play == "travel":
        bs = view.get("buildings") or ()
        to = bs[0]["label"] if bs else "explore"
        return {"play": "travel", "to": to, "gait": "walk", "bound": "arrived", "why": "clear"}
    return None


def _tests(view):
    """(rule, play type) in RULES order, each with its test read."""
    s6, keep = _standing(view, DANGER_R), _standing(view, KEEP_R)
    n = view.get("needs") or {}
    tired = (n.get("fatigue") or 0) > TIRED_T
    bs = view.get("buildings") or ()
    yield "reach", "fight", armed(view) and bool(keep)
    yield "bleed", "dress", bool(bleeding(view)) and not keep and dress_with(view) is not None
    yield "group", ("kite" if s6 else "avoid"), is_group(view)
    coming = [z for z in _standing(view, ENGAGE_R) if z.get("targets_me")]
    yield "fight", "fight", armed(view) and (1 <= len(s6) <= 2 or 1 <= len(coming) <= 2)
    yield "unarmed", "kite", not armed(view) and bool(s6)
    yield "night", "shelter", bool(n.get("night") or tired) and any(b.get("shelter") for b in bs)
    yield "goal", "loot", _goal_building(view) is not None
    yield "loot", "loot", any(b.get("looted") is False for b in bs)
    yield "travel", "travel", bool(bs)
    yield "explore", "travel", True


def doctrine(view):
    """(rule, flat answer) of the first rule whose test holds and whose play the view admits (`target_for`); a group
    with no refuge to avoid toward kites in the stance."""
    for rule, play, ok in _tests(view):
        if not ok:
            continue
        ans = target_for(play, view)
        if ans is None and play == "avoid":
            ans = target_for("kite", view)
        if ans is not None:
            return rule, ans
    return None, None


RULES = RULE_NAMES
