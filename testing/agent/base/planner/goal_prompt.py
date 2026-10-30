"""The LLM goal source's system prompt (Plan 23 Task 14, P23-11; lifted out of `llm.py` at Plan 24 Task 29): the text
`llm.SYSTEM` is, rendered once at import from `schema/goals.json`, game state only (principle 8: no path, credential,
log or planner internal; a test asserts it).

`system(explore_max_tiles)` reads, in order: the game and the contract; one line per goal type with its fields, their
types, enums and bounds (`field_text`); the strategy paragraph (Task 29); how the view's building line reads; the
refusal rule (P24-B 3, the bound `explore_max_tiles`, `llm.EXPLORE_MAX_TILES`, and `goals.WOODS_R`); the loop (P24-Y,
`goals.BUILDING_R`); the meaning of the view keys the rules read (met, attackers, worn, hit_reaction, tired and night,
last_goal); then that the user message is the view.

The strategy paragraph (Task 29; `docs/superpowers/specs/2026-10-30-plan-24-guides-notes.md` § 8, the written guides'
rules worded for the prompt): `strategy()` is the schema's `strategy` list, one entry per rule, `{text, pages,
reads}`: `text` the line as the model reads it, naming the view keys it reads and never a planner internal, `pages`
the guides notes' page ids it rests on, `reads` the view keys it reads (dotted for a sub-key, `buildings.<field>` for
a building line's field). The lines go in the notes' order, each once, under one heading after the goal types.
"""
import json

from agent.base.planner.goals import BUILDING_R, SCHEMA_PATH, WOODS_R
from agent.base.planner.night import DAWN_HOUR, LATE_HOUR, TIRED_T
from agent.base.planner.view import BUILDING_ZOMBIE_R, WHYS

__all__ = ["system", "strategy", "field_text"]


def _schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def strategy():
    """The schema's strategy entries, `[{text, pages, reads}]` in order."""
    return list(_schema().get("strategy") or ())


def field_text(name, spec):
    """One goal field as the prompt names it: `name (type[, one of a|b][, min to max]): description`."""
    kind = spec.get("type", "value")
    if "enum" in spec:
        kind = "%s, one of %s" % (kind, "|".join(spec["enum"]))
    if "minimum" in spec and "maximum" in spec:
        kind = "%s, %s to %s" % (kind, spec["minimum"], spec["maximum"])
    return "%s (%s): %s" % (name, kind, spec.get("description", ""))


def system(explore_max_tiles):
    """The system prompt (the module docstring)."""
    schema = _schema()
    entries = schema["oneOf"]
    names = [e["properties"]["type"]["const"] for e in entries]
    lines = [
        "You play Project Zomboid: a survivor in a zombie apocalypse, driven by a program. The program's instincts "
        "answer threats, hunger, thirst, the load and the night on their own; you choose the survivor's next goal "
        "from the view. Answer with one JSON object and nothing else: {\"type\": <one of %s>, ...that type's "
        "fields}." % ", ".join(names),
        "The goal types:",
    ]
    for e in entries:
        t = e["properties"]["type"]["const"]
        fields = "; ".join(field_text(k, v) for k, v in e["properties"].items() if k != "type")
        lines.append("- %s: %s Fields: %s" % (t, e.get("description", ""), fields))
    lines.append("Strategy, the rules of the game's written guides (each line names the view keys it reads):")
    lines.extend("- " + s["text"] for s in schema.get("strategy") or ())
    lines.append("Squares are x, y tiles; north is -y. pos is your position. In the view, each building reads "
                 "`id @x,y door x,y dist cN flags h:holds z:N`: @x,y its nearest room square, door its exterior door "
                 "square (- none), dist in tiles, N its containers, flags L looted (nothing left to take), v visited, "
                 "s shunned, x blocked (every door stuck: never named), - none; z:N the zombies listed within %g "
                 "tiles of it." % BUILDING_ZOMBIE_R)
    lines.append("The refusal rule: name a building only by an id the view lists; an ExploreToward square within "
                 "%g tiles of pos and, once the view lists a building, within woods_r tiles of one (the view's "
                 "woods_r, %g at the start; farther is the woods); a LootBuilding only a building listed without the L flag. An answer breaking it is refused "
                 "and the program chooses instead." % (explore_max_tiles, WOODS_R))
    lines.append("Your loop, every goal a building: the program clears the zombies near you itself; you loot the "
                 "nearest building listed without L within %g tiles (LootBuilding), then the next nearest (h: lists "
                 "what each building is known to hold); walk only toward buildings: toward names the next building "
                 "to walk to when none is near (its door), and an ExploreToward finds the next house at the edge of "
                 "the known buildings, never out into open ground." % BUILDING_R)
    lines.append("met is the ground where zombies were met in the last minutes: dense the centre of the densest "
                 "group, n how many, bearing and dist from pos. Zombies there are still about: prefer ground away "
                 "from met.dense, and never explore toward its bearing while met.n is 3 or more.")
    lines.append("attackers is how many zombies are attacking you now (the instincts answer them; a goal cannot).")
    lines.append("worn lists what you wear as [location, bite, scratch, holes]: a higher bite and scratch turns more "
                 "zombie attacks, a hole defends nothing there, null means not read yet. The program puts on a "
                 "garment you hold when it beats the one worn at its location, so looting clothing with better "
                 "protection helps.")
    lines.append("hit_reaction names the hit you are reeling from now, null when none.")
    lines.append("tired is true when needs.fatigue is above %g, the first Tired moodle; night is true from hour %g "
                 "to hour %g; null means not read yet." % (TIRED_T, LATE_HOUR, DAWN_HOUR))
    lines.append("last_goal is how the last goal ended: end done, failed, superseded or refused, and why, one of: "
                 "%s." % ", ".join(WHYS))
    lines.append("The user message is the view: one `key: value` line per key.")
    return "\n".join(lines) + "\n"
