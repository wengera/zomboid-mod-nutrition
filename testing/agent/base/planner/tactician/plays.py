"""The tactician's plays (Plan 31 Task 11, variant T; the proposal `rebuild-proposal-model-tactician.md` § 2 and § 4):
the closed vocabulary `plays.json` beside this module, the answer's validation against a tactical view, and the system
prompt rendered from it.

- The answer: one JSON object `{play, <the play's args>, bound, why}`, nothing more. `play` one of PLAYS; each arg a
  label the view lists (`Z<n>` a zombie, `D<n>` a door, `B<id>` a building, `P<i>` a body part) or a closed enum;
  `bound` one of the play's own exits; `why` one of WHYS. No free-text field anywhere (ruling P28-K): a write-up
  cites keys, never prose.
- `validate(obj, view) -> Play`, a stdlib walk of `plays.json` (as `goal_runner.validate` walks `goals.json`), raising
  `Refused(why)` with `why` one of REFUSALS: the shape (`not_object`, `unknown_play`, `extra_key`, `missing_arg`,
  `bad_arg`, `bad_bound`, `bad_why`), the labels against this view (`unknown_label`: no such label listed now, so a
  late answer naming a zombie that died is refused, the proposal's late validation), and the meaning (`not_bleeding`:
  a dress of a part that does not bleed; `no_item`: a dress `with` an item the kit lacks; `looted`: a loot of a building
  the view reads looted; `no_shelter`: a shelter of a building with no shelter plan).
- `system()`: the system prompt, rendered once from `plays.json` and the doctrine lines (DOCTRINE: Angus's rules, the
  memories `stand-and-fight-dress-first`, `combat-approach-not-flee`, `intent-doors-sneak`, `no-sprinting`), the
  answer's shape, then that the user message is the view (`tview.render`).
"""
import json
import os
import re
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "plays.json")

with open(SCHEMA_PATH, encoding="utf-8") as _f:
    SCHEMA = json.load(_f)

PLAYS = tuple(SCHEMA["plays"])              # fight, kite, avoid, dress, loot, travel, shelter
WHYS = tuple(SCHEMA["whys"])
BOUNDS = {p: tuple(s["bounds"]) for p, s in SCHEMA["plays"].items()}
ARGS = {p: dict(s["args"]) for p, s in SCHEMA["plays"].items()}
RETREATS = ("kite", "avoid")                # the plays the scorecard reads as retreats (their labels start so)
TACTICAL = ("fight", "kite", "avoid", "dress")   # the plays whose target the bench's agreement compares
STRATEGIC = ("loot", "travel", "shelter")   # the plays the strategic goal layer executes
REFUSALS = ("malformed", "not_object", "unknown_play", "extra_key", "missing_arg", "bad_arg", "unknown_label",
            "bad_bound", "bad_why", "not_bleeding", "no_item", "looted", "no_shelter", "timeout", "exit",
            "cli_error", "doctrine")   # `doctrine`: the decider's veto of an answer breaking a rubric rule (decide.py)
LABEL_RX = {"zombie": re.compile(r"Z[1-9][0-9]*"), "door": re.compile(r"D[1-9][0-9]*"),
            "building": re.compile(r"B-?[0-9]+"), "part": re.compile(r"P[0-9]+")}
KINDS = {"zombie": ("zombie",), "refuge": ("door", "building"), "place": ("building", "door"),
         "building": ("building",), "part": ("part",)}   # an arg's label kind -> the label families it admits
TARGET_ARGS = ("target", "toward", "to", "part", "building")   # the arg naming a play's target, first present wins
WITH_KIT = {"bandage": ("bandages",), "rag": ("rags", "dirty_rags"), "rip": ("rip", "unwear")}   # a dress's `with` ->
                                                       # the kit counts any one of which makes it possible

DOCTRINE = (
    "One standing zombie in danger range (6 tiles) with a weapon in hand is fought (`fight`), never fled, whatever "
    "the health; two are fought one at a time, the nearest first; one or two coming at you within 9 tiles are "
    "fought too: clear the zombies near before looting.",
    "A bleeding part with no standing zombie within 2.5 tiles is dressed (`dress`) before any goal and before any "
    "retreat from a zombie farther off; with no bandage or rag held, rip a garment (`with` rip).",
    "A group (three or more standing zombies that target you, or two while unarmed) is left before it arrives: "
    "`avoid` toward a named door or building with none in danger range, else `kite` toward one in the stance.",
    "A retreat always names its refuge (a door D<n> or a building B<id>); `kite` with `stance` only when no refuge "
    "is listed. Never run into a zombie; never sprint.",
    "A zombie behind a door is decided once: fight it through the door, or leave by another way.",
    "With no zombie near: loot the next unlooted building (`loot`), or `travel` to one; `shelter` at night.",
)


class Refused(ValueError):
    """An answer the view refuses: `why` one of REFUSALS."""

    def __init__(self, why, detail=None):
        super().__init__(why if detail is None else "%s: %s" % (why, detail))
        self.why = why
        self.detail = detail


@dataclass
class Play:
    """One validated play: its type, its args (labels and enums), its bound and its why."""
    play: str
    args: dict = field(default_factory=dict)
    bound: str = ""
    why: str = ""

    def target(self):
        """The label of the play's target (its first TARGET_ARGS arg), else None."""
        return next((self.args[k] for k in TARGET_ARGS if k in self.args), None)

    def row(self):
        """The answer as a flat object (the shape the model writes)."""
        return dict({"play": self.play}, **self.args, bound=self.bound, why=self.why)


def labels(view):
    """{family: set of labels} the view lists: zombies, doors, buildings and body parts."""
    v = view or {}
    return {"zombie": {z["label"] for z in v.get("zombies") or () if isinstance(z, dict) and "label" in z},
            "door": {d["label"] for d in v.get("doors") or () if isinstance(d, dict) and "label" in d},
            "building": {b["label"] for b in v.get("buildings") or () if isinstance(b, dict) and "label" in b},
            "part": {p["label"] for p in (v.get("body") or {}).get("parts") or () if isinstance(p, dict)
                     and "label" in p}}


def _family(label):
    """The family a label's shape names (zombie, door, building, part), else None."""
    if not isinstance(label, str):
        return None
    return next((fam for fam, rx in LABEL_RX.items() if rx.fullmatch(label)), None)


def _by_label(view, key, label):
    rows = (view.get("body") or {}).get("parts") if key == "parts" else view.get(key)
    return next((r for r in rows or () if isinstance(r, dict) and r.get("label") == label), None)


def _arg(name, spec, v, listed):
    """One arg's check (the module docstring), raising Refused."""
    if "enum" in spec:
        if v not in spec["enum"]:
            raise Refused("bad_arg", name)
        return
    if v in spec.get("or", ()):
        return
    fam = _family(v)
    if fam is None or fam not in KINDS[spec["label"]]:
        raise Refused("bad_arg", name)
    if v not in listed[fam]:
        raise Refused("unknown_label", "%s=%s" % (name, v))


def validate(obj, view):
    """The Play `obj` names, checked against `view` (the module docstring); raises Refused."""
    if not isinstance(obj, dict):
        raise Refused("not_object")
    p = obj.get("play")
    if p not in PLAYS:
        raise Refused("unknown_play")
    spec = ARGS[p]
    allowed = set(spec) | {"play", "bound", "why"}
    extra = sorted(set(obj) - allowed)
    if extra:
        raise Refused("extra_key", ",".join(map(str, extra)))
    missing = sorted(allowed - set(obj))
    if missing:
        raise Refused("missing_arg", ",".join(missing))
    listed = labels(view)
    for name, s in spec.items():
        _arg(name, s, obj[name], listed)
    if obj["bound"] not in BOUNDS[p]:
        raise Refused("bad_bound")
    if obj["why"] not in WHYS:
        raise Refused("bad_why")
    play = Play(p, {k: obj[k] for k in spec}, obj["bound"], obj["why"])
    _meaning(play, view)
    return play


def _meaning(play, view):
    """The checks past the labels (the module docstring): the dress's part bleeds and its item is held, the loot's
    building is not looted, the shelter's building has a shelter plan."""
    a = play.args
    if play.play == "dress":
        part = _by_label(view, "parts", a["part"]) or {}
        if part.get("bleeding") is not True:
            raise Refused("not_bleeding", a["part"])
        kit = view.get("kit") or {}
        if not any((kit.get(k) or 0) > 0 for k in WITH_KIT[a["with"]]):
            raise Refused("no_item", a["with"])
    elif play.play == "loot":
        if (_by_label(view, "buildings", a["building"]) or {}).get("looted") is True:
            raise Refused("looted", a["building"])
    elif play.play == "shelter":
        if (_by_label(view, "buildings", a["building"]) or {}).get("shelter") is not True:
            raise Refused("no_shelter", a["building"])


def _arg_line(name, spec):
    if "enum" in spec:
        return "%s: one of %s" % (name, "|".join(spec["enum"]))
    extra = " or %s" % "|".join(spec["or"]) if spec.get("or") else ""
    return "%s: %s%s" % (name, spec["label"], extra)


def system():
    """The system prompt (the module docstring)."""
    out = ["You are the tactician of a survivor in Project Zomboid (a zombie survival game), on a dedicated server.",
           "You are asked whenever the situation changes. Answer with ONE JSON object and nothing else: "
           '{"play": <play>, <its args>, "bound": <one of its bounds>, "why": <one of the whys>}.',
           "No other key, no prose. A label must be one the view lists right now.",
           "", "Labels: " + "; ".join("%s = %s" % (k, v) for k, v in SCHEMA["labels"].items()) + ".", "", "Plays:"]
    for p, s in SCHEMA["plays"].items():
        args = ", ".join(_arg_line(n, a) for n, a in s["args"].items())
        out.append("- %s {%s} bounds %s: %s" % (p, args, "|".join(s["bounds"]), s["description"]))
    out += ["", "whys: " + "|".join(WHYS), "", "Rules (your commander's, always):"]
    out += ["- " + line for line in DOCTRINE]
    out += ["", "Example: " + json.dumps({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}),
            "", "The user message is the view: the trigger, you, the zombies (nearest first; dist and closing in tiles "
            "and tiles per second, line clear|door|wall|window|unknown), the counts, a 21x21 map around @ (north up: "
            "# wall, + closed door, / open door, = window, ^ fence, . floor, , ground, digits the zombies Z1-Z8), "
            "your body and kit, the doors and buildings near, the play running and the goal."]
    return "\n".join(out)


SYSTEM = system()
