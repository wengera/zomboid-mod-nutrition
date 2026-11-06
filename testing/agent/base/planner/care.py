"""The care branch (Plan 24 Task 10, ruling P24-G 2; Angus's direction of 2026-10-29: bandage wounds first, rags from
ripping clothes and washing them; the jar reads #4298-#4301): `Care`, a one-action-at-a-time policy over PZA/1.5's
`bandage`, `rip` and `wash` (Task 9), which `survive.Survive` runs between `threat` and `need` while no threat is held
(the threat branch runs first and answers while any zombie is within its hold radius, so the branch yields to a
threat within DANGER_R, and a threat arriving supersedes its running action).

Its choose, the first that answers (`why` names the `reason`, the `part`, the `item` and its `kind`):
1. `bleeding`: the worst bleeding unbandaged part of the frame's `body.parts` (a deep wound first, then the longest
   `bleedingTime`, then the least index), bandaged (`Bandage(itemId, part)`) with the best held item by `care_kind`:
   a clean bandage, then a clean rag, then a dirty one only when the part's `bleedingTime` exceeds DIRTY_RAG_MIN (a
   dirty rag stops the bleeding but doubles the infection odds against none, #4299; the bleeding drain scales with
   the bleeding time, #4298; the threshold is in the engine's raw wound-time units, `BodyPart.getBleedingTime()`,
   never game minutes: a plain scratch reads about 2 to 9 by `generateBleeding`, 0.3 to 0.6 of a scratch time of 7 to
   15, the Task 10 review's jar read, and a cut, a deep wound, glass or a bullet adds to it, so a plain scratch never
   takes a dirty rag and a cut or a deep wound usually does: Task 10 fix 1, minor 12). With no rag of any kind held,
   one held cotton garment is ripped for it (`no_rag`: `rippable` names it, never one of the inventory's first sight,
   `World.first_sight`, the clothes the character stands in, which the Lua refuses `worn`; on a PZA/1.5.2 log the item
   record's `worn` and `rip` say instead, Task 10 fix 2: only a `cotton` unworn one; nor one marked
   `unrippable`, a rip refused `worn`, `not cotton` or `needs tool`, `World.mark`: `Rip(itemId)`); a dirty rag held
   under the time rule falls through to the wash.
2. `replace`: a bandaged part whose `bandageLife` reached 0 or that reads `bandageDirty`, with a clean bandage or rag
   held: bandaged again with it (the Lua takes the old one off first). Ruling P27-D (`spent_keep`, Survive's
   `SPENT_KEEP`; E18, `e_day_18-20261102-224036`: the neck read bleeding false under its spent dressing at
   bleedingTime 15.462026596069336 and 13.89616870880127, and its two re-dressings each took health, 82.34173583984375
   to 67.09330749511719 and 62.200069427490234 to 54.371578216552734, the part bleeding from the frame after the old
   dressing came off): only a part reading `bleeding` true or a `bleedingTime` at or under SPENT_REDRESS_BT (the
   engine's raw wound-time units, DIRTY_RAG_MIN's) is replaced (`_redresses`; a part whose frame carries no
   `bleedingTime` as before); the first spent part left is logged `spent_kept` {part, bleedingTime, dirty} on the
   care line whenever the step would have sent before. Cost if wrong: a dirty dressing's infection odds (#4299) on a
   part the engine would have re-bled. Ruling P27-K3 (`replace_quiet`, Survive's `REPLACE_QUIET`; F10,
   `f_goals_11-20261103-075140`: the five landed replaces bled their parts for the act's 5.978 to 6.281 s, and
   the one superseded after the dressing came off bled part 4 five game minutes): a replace is sent only with no
   listed zombie chasing within LISTED_R (`chasing_n`, Survive's count, the rest's test of P27-C2); with one the step
   holds, logged `spent_held` {part, chasing}. The bleeding step is unchanged. Cost if wrong: a spent dressing worn
   longer.
3. `wound` (ruling P28-A, `wound_dress`, Survive's `WOUND_DRESS`; F11, `f_goals_12-20261103-144240`: its scratched
   parts 4, 6 and 8 never bled, took no care line and fell to 0, 9.163058280944824 and 51.79861068725586, while
   63.577457427978516 of its 100 health fell on frames reading no bleed and no bite, #4581, #4585; an undressed
   scratch drains each tick where a bandage suppresses it, #2364): the first part `_wounds` lists (PZA/1.7.2's
   `wound` true, `bleeding` false, `bandaged` false; the lowest `h` first, then the least index) is dressed with the
   best clean item held (a bandage, then a clean rag, never a dirty one: #4299) while more than WOUND_RESERVE clean
   dressings are held and no zombie is within DANGER_R (`near_n`, Survive's count, set each care tick), logged
   `{reason "wound", part, item, kind, h}`; a part left for the reserve logs `wound_held` {part, clean} on the care
   line. A part so dressed is `fresh` as a bleed's. A frame whose parts carry no `wound` (an older log) reads none.
   Cost if wrong: a dressing's seconds on a quiet tick and the rag a later bleed wants, bounded by the reserve.
4. `wash`: a dirty rag held, no zombie within DISENGAGE_R (Survive sets `quiet` each tick), and a known water source
   (`World.water_sources`: the map's square `water` record with water in it, on the player's floor, not refused
   lately) within WASH_R: `Wash(itemId, x, y)`, the Lua walking next to it (a wash does not test the water's taint,
   #4301).
Ruling P24-P (Plan 24 Task 12, E6: the health fell from 100 to 17.6 while a zombie was held, the one bandage sent on
the first tick with none): the bleeding step also runs with a threat held, whenever the nearest listed zombie is
beyond CARE_R and `tends_wound` answers (Survive's threat branch yields to it only then, so no other step sends);
Task 12 fix 1 gives the yield its hysteresis (`survive.Survive._care_yields`): a bandage starts beyond CARE_R only
with the nearest not closing over CARE_STILL_TICKS ticks and no flee leg running from a chaser, and a running one is
superseded only inside CARE_HOLD_R. The ride (ruling P24-U, Task 12 fix 1; PZA/1.5.3's `keepMoving`, ruling P24-R):
under a running flee leg (a steer, or a walk on an open line) with the nearest zombie beyond RIDE_R or no zombie
chasing, Survive sets `ride_now` and the bleeding step bandages the worst bleeding part above the legs (index under
LEG_FIRST; a leg part takes the standing bandage only, under the hysteresis) with `Bandage(itemId, part,
keepMoving=True)`, no rip; the ride is tracked by its own act lines (`ride`, `riding`): the Care is busy while it runs
whatever was sent since (the flee's re-aims are new legs that keep it), and a ride the engine stopped (`failed
stopped`) holds no item out. Ruling P24-AR (Plan 24 Task 32; E9 bled from 96.39 health to 0 in 13.111 s under the
`many` flee, five rags held): under a `many` flee with a zombie chasing (where P24-U rode nothing) the ride goes with
the nearest beyond RIDE_MANY_R, or whatever the distance once FLEE_CARE_S have passed since the threat branch first
read `many` with FLEE_CARE_N or more parts bleeding (`bleeding_n`; Survive's `_rides_many`).
A garment is ripped from the choose only for a bleeding part (Task 10 fix 1, the review's major 2: ruling P24-G 2's
rip is the wound's; a rip for stock destroyed looted clothing and, from above the need branch, superseded a running
drink). The rag stock (ruling P24-AB, Plan 24 Task 21; E8, `e_day_8-20261029-174023`: the second bite bled 73 game
minutes to the death with no dressing held, its last 31 standing still with the only zombie idle 8.3 tiles off; Angus:
"he will need a couple clean rags, which he can get from ripping clothes and washing the resulting rags as
necessary"): `stock()` answers `Rip(itemId)` of the held unworn cotton garment (`_rip_item`) while fewer than
RAG_STOCK clean dressings (`bandage` and `rag` items) are held, the build announces `rip` and no zombie is within
DISENGAGE_R (`quiet`); Survive tries it only on an idle tick, behind the need, the load and the night and before the
goal, with no action running (so it never supersedes a drink, a fill or a goal's walk or loot: Task 10's objection),
its line the care branch's (`why` `stock`). `wants_dressing()`: a part bleeds, no item the bleeding step may put on
it is held (nor a dirty rag to wash) and no garment can be ripped: Survive then marks the want `bandage`, which the
view lists and the goal layer's loot takes first (`goals.wanted_uses`). Unwear then rip (ruling P24-AJ, Plan 24 Task
27; PZA/1.7's `unwear`, #4376, #4551: vanilla's Unequip leaves the garment in the main inventory, where the rip recipe,
which refuses a worn item, takes it): on the same idle tick, after the rag stock's rip found nothing unworn to rip, a
bleeding part with nothing to dress it (`_bleed_wants`) takes `Unwear(itemId)` of the worn cotton garment covering
the least (`_unwear_pick`: the item record's `worn` and `rip` "cotton", its clothing record's bite + scratch the least,
ties by the least id; never at a shoe or trouser location, UNWEAR_NEVER over the clothing record's `loc`), one per
item per WEAR_RETRY_MIN game minutes, none while the last one's garment still reads worn within WEAR_SETTLE_MAX frames
of its done; once its `item_changed` reads it unworn the bleeding step (or the stock) rips that same item first
(`_rip_item`). Never under a threat held: the stock runs only on Survive's idle tick. The unwear under a goal (ruling
P25-H, Plan 25 Task 7; F4, `f_goals_5-20261030-180527`: part 8 bled on 904 decision lines from game minute 1351, every
cotton garment worn, and a night of Shelter goals and flees gave the stock no idle tick, health 100 to
3.4362869262695312): the bleeding step itself takes the same unwear as its last step (`_unwear_step`, logged
`{reason "unwear", part, item, loc, cover}`) with no dressing of any kind held, nothing unworn to rip, no ride and
`quiet`, on any care tick (the care branch runs before the goal's, so it pre-empts a running goal); Survive's
`UNWEAR_WOUND` off is the rule before it. Ruling P28-A (`wound_dress`): `wants_dressing()` also marks the want for a
part `_wounds` lists with no more than WOUND_RESERVE clean dressings held and no garment to rip (`_wound_wants`); the
stock's unwear reads the bleed's want alone (`_bleed_wants`), so a scratch takes off no garment.
The wear (Plan 24 Task 24, review-t9-fix9's ruling 5; PZA/1.6.1's `me.worn` with each entry's `holes` and `cond`): on
the same idle tick as the rag stock, after it, `stock()` answers `Wear(itemId)` of the held unworn garment whose
clothing record beats what is worn at its location (`wear_gain`: `cond` above 0, `holes` 0, bite + scratch above the
worn entry's, 0 where nothing is worn, ties to the higher bite then the fuller condition; a worn entry with holes, or
at condition 0, defends nothing in the engine, so an intact candidate of equal or better nominal defence swaps it),
never with an attacker or hit reaction read nor a zombie listed within WEAR_QUIET_R, never while `me.worn` is unread
(unknown, not nothing worn), an item once per WEAR_RETRY_MIN game minutes. Wearing can take off other garments at
exclusive locations that the wear's `replaced` does not name: the check (`_wear_check`, read every tick
the first `me.worn` list newer than the wear's done, WEAR_SETTLE_MAX frames at most) compares the summed defence of
`me.worn` before and after; when it fell the candidate is marked `wear_loses` and each held garment that read worn and
whose location the new list lacks (the Lua sends no `item_changed` for a garment an exclusive location knocked off)
is put on again, and when
it held the replaced garment is dropped under a load above level 0. The care branch is the stock's: a wear is a
50-action-tick stand-still, taken on a quiet idle tick, never the load branch's (a drop under load is the same tick's
second choice). Ruling P26-E (`wear_worn`, Survive's `WEAR_WORN`; F5, `f_goals_6-20261030-192251`: the stock re-sent
the wear of trousers worn since a6 five times, each `rejected` `worn`): a wear the Lua rejected `worn` marks its item
worn in the World (`World.mark_worn`), so the pick, which takes only an item whose record does not read worn, leaves it
out from then on; the stock's wear line counts the garments so marked and still held (`skipped_worn`).
An item whose care action ended failed (never `superseded`), timed out or was rejected is left out for
CARE_RETRY_MIN game minutes (`World.world_minutes`); a wash refused `no source` or `no water` leaves its source out
(`World.mark_dry`, `world.SOURCE_RETRY_MIN`). A part a bandage ended `done` on is left out until a frame newer than
the one read with that end (`World.frame_n`; Task 10 fix 1, minor 6: the frame that reads the bandage on may follow
the done, and a stale one would put the next item on the same wound). Each step needs its skill in the hello's caps
(`World.can`); a PZA/1.4 frame's parts carry no `bleeding` (decoded None), so the branch reads no wound there and no
decision golden moves. `Care` is a `Policy` (Task 10 fix 1, minor 13): Survive sends through it as the owner, and its
`sent` records each item's action.

The item reads are names (`care_kind`, `rippable`): what `ISApplyBandage` reads, `Dirty` in the type (#4299); the
`RipClothing` recipe's cotton tag is in no dataset the repository carries, so `rippable` is a guess the Lua's refusal
corrects.

The item choice (Plan 31 Task 8) is a set of pure reads of the World and a caller's refusal memory (`held_dressings`,
`dressing_pick`, `rip_pick`, `unwear_pick`, and the Dress maneuver's whole order `dress_pick`), which the care branch
reads with its own `held_out` and `unwear_at` and the Dress (`maneuvers.dress`) with its own. Survive's
`DRESS_MANEUVER` (off: the ladder's goldens) sets `dress_cls`, and the bleeding step is then one `Dress` of the worst
bleeding part in place of its three sends (`_dress_step`): the Dress's commands go through this policy (`sent` hands
them to it, `owns` names them, and a riding bandage of the Dress is recorded as `ride`, so every P24-U reader and
RIDE_RETRY_S read it), its waits hold the care branch's tick (`dressing`), and each end is logged once (`dress_end`, a
list); the spent, wound and wash steps follow as before when no Dress runs. Fix 1 (review-t8): no new Dress after a
failed one until the inventory gains an item or DRESS_RETRY_S pass, and on a ride tick no standing Dress is stepped
and nothing but a riding bandage is sent (`_dress_step`).
"""
import math
import re
import time

from agent.base.planner.policies import SPENT_REDRESS_BT, WOUND_RESERVE, Policy, PREEMPTED, item_id_ok
from agent.base.pza1 import Bandage, Drop, Rip, Unwear, Wash, Wear
from agent.base.world import me_floor

CARE_RETRY_MIN = 2.0      # game minutes an item whose care action was refused is left out (P24-G 2)
DIRTY_RAG_MIN = 10.0      # a dirty rag goes on a part only when its bleedingTime exceeds this (P24-G 2): the engine's
                          # raw wound-time units, #4298 (a plain scratch about 2-9, generateBleeding), never minutes
WASH_R = 15.0             # tiles: a dirty rag is washed at a known water source this near (P24-G 2)
CARE_R = 4.0              # tiles: a bleeding part is tended with a threat held while the nearest zombie is beyond this
                          # (ruling P24-P, Plan 24 Task 12: E6 bled from 100 to 17.6 health before its one bandage);
                          # a running Fight's tick with a dressing held yields beyond FIGHT_REACH (ruling P26-D)
CARE_HOLD_R = CARE_R - 1.0   # tiles: a running bandage is superseded only with the nearest zombie inside this (Task
                          # 12 fix 1, the review's ruling: CARE_R the start line, this the supersede line; at CARE_R
                          # alone a chaser at about 4 tiles alternated the bandage and the steer every tick); a
                          # running Fight's bandage holds while nothing is within FIGHT_REACH (ruling P26-D)
CARE_STILL_TICKS = 2      # threat ticks over which the nearest zombie's distance must not have fallen before a bandage
                          # starts under a held threat (Task 12 fix 1: the yield's start reads it not closing); a
                          # running Fight's tick with room (nothing within FIGHT_REACH) ignores it (ruling P26-D)
KINDS = ("bandage", "rag", "dirty")              # care_kind's order of choice
CLEAN_BANDAGES = ("Bandage", "AlcoholBandage", "Bandaid")
CLEAN_RAGS = ("RippedSheets", "AlcoholRippedSheets", "DenimStrips", "LeatherStrips")
COTTON_RX = re.compile(r"\.(Tshirt|Shirt|Dress|Skirt|TankTop|Tanktop|Socks|Boxers|Briefs|Underpants)(_|$)")
TOOL_WORDS = ("Denim", "Leather")                # RipDenimClothing's fabrics: scissors or a knife (#4300)
RIP_REFUSALS = ("worn", "not cotton", "needs tool")   # a rip refused so never succeeds on that item
DRY_REASONS = ("no source", "no water")          # a wash or fill refused so leaves its source out a while
FAILED = ("failed", "timeout", "rejected")
LEG_FIRST = 11            # the first leg part (UpperLeg_L; 11-16 the thighs, shins and feet): a bandage on one stops on
                          # a walk, so the Lua rejects it `leg part` with keepMoving (PZA/1.5.3, ruling P24-R)
RIDE_R = 6.0              # tiles: a bandage rides a running flee leg only with the nearest zombie beyond this, or with
                          # no zombie chasing (ruling P24-U, Task 12 fix 1: the ride holds the leg to a walk)
RIDE_MANY_R = 3.0         # tiles: under a `many` flee, or a `pair` or `held` one (ruling P26-D), with a zombie chasing,
                          # a bandage rides the flee's leg with the nearest beyond this (ruling P24-AR, Plan 24
                          # Task 32: E9's line 374, game minute 612, the nearest at 3.44 tiles with part 5 bleeding
                          # and a bandage held; E8's line 409, game minute 616, at 3.70 with parts 4 and 9 bleeding)
FLEE_CARE_S = 20.0        # wall seconds after the threat branch first read `many` (Survive's `many_since`) from which ...
FLEE_CARE_N = 2           # ... this many bleeding parts or more ride the `many` flee's leg whatever the distance (ruling
                          # P24-AR: E9 bled from 96.39 health to 0 in 13.111 s from four bites; its line 450, game
                          # minute 623, the nearest at 0.63 tiles, parts 0 and 8 bleeding; E8's line 389, game minute
                          # 613, at 0.51 tiles, parts 4 and 9)
RIDE_FREE = ("stopped",)  # a ride failed so was stopped by the engine (a run, an aim, a hit): its item is not held out
RIDE_RETRY_S = 3.0        # seconds after a stopped ride before the care rides again (Task 12 fix 2, the re-review's major
                          # 2: the same ride re-chosen at once was cooled and the tick fell through to a drink)
DRESS_RETRY_S = 20.0      # seconds after a Dress ended failed before the care starts another while the inventory gained no
                          # item (Plan 31 Task 8 fix 1, review-t8 M1: a judgment, about forty care ticks at 2 Hz, so a
                          # Dress that found nothing, or that a flee kept stopping, leaves the goal's loot and the flee
                          # their ticks; a new held dressing or garment restarts it at once)
RAG_STOCK = 2             # clean dressings (bandages and clean rags) the care keeps, ripping one unworn cotton garment
                          # on an idle tick while fewer are held (ruling P24-AB; Angus: "a couple clean rags")

WEAR_RETRY_MIN = 10.0     # game minutes an item's wear is not sent again (Task 24; the brief's number)
WEAR_QUIET_R = 8.0        # tiles: a wear (50 action ticks, stopped by a run) waits while a zombie is listed this near
                          # (review-t9-fix9 ruling 5, point 3: "no zombie seen within about 8 squares")
UNWEAR_NEVER = re.compile(r"shoe|boot|pant|trouser", re.I)   # clothing locations never taken off for a rag (ruling
                          # P24-AJ: never the shoes, whose stomp power the stomp reads, #4374, nor the trousers)
WEAR_SETTLE_MAX = 12      # frames after a wear's done the exclusive-location check waits for a newer `me.worn` list
                          # at most (the Lua marks the list dirty at the done and otherwise sends it every
                          # S.WORN_EVERY (10) frames: review-t24 minor 4)

__all__ = ["Care", "care_kind", "rippable", "wear_gain", "held_dressings", "dressing_pick", "rip_pick", "unwear_pick",
           "dress_material", "dress_pick", "UNWEAR_NEVER", "WEAR_RETRY_MIN", "WEAR_QUIET_R", "WEAR_SETTLE_MAX", "CARE_RETRY_MIN", "DIRTY_RAG_MIN", "WASH_R", "CARE_R", "CARE_HOLD_R",
           "CARE_STILL_TICKS", "KINDS", "DRY_REASONS", "LEG_FIRST", "RIDE_R", "RIDE_MANY_R", "FLEE_CARE_S",
           "FLEE_CARE_N", "RIDE_RETRY_S", "DRESS_RETRY_S", "RAG_STOCK"]


def care_kind(full_type):
    """What a bandage item is by its name: `bandage` (a clean bandage), `rag` (a clean ripped sheet or strip),
    `dirty` (a type naming `Dirty`: life 0), else None."""
    name = (full_type or "").rsplit(".", 1)[-1]
    if "Dirty" in name and any(name.startswith(w) for w in CLEAN_BANDAGES + CLEAN_RAGS):
        return "dirty"
    if name in CLEAN_BANDAGES:
        return "bandage"
    if name in CLEAN_RAGS:
        return "rag"
    return None


def rippable(full_type):
    """The cotton-garment name guess: a T-shirt, shirt, dress, skirt, tank top, sock or underwear naming neither denim
    nor leather."""
    ft = full_type or ""
    return bool(COTTON_RX.search(ft)) and not any(w in ft for w in TOOL_WORDS)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def wear_gain(c, e):
    """The wear rule (Task 24, the module docstring): the defence a held garment's clothing record `c` adds over the
    worn entry `e` at its location (a `me.worn` entry, None when nothing is worn there), else None when it is not to be
    worn. `c` needs `cond` above 0 and `holes` equal to 0. Over nothing worn it adds bite + scratch (None at 0). An
    intact worn entry (no holes, condition above 0 or unread) is beaten by a higher bite + scratch, or an equal one with
    a higher bite; a holed or spent one defends nothing in the engine (bite and scratch ignore holes), so an intact
    garment of equal or better defence than its nominal swaps it, adding its whole defence."""
    if not (_num(c.get("cond")) and c["cond"] > 0 and c.get("holes") == 0):
        return None
    bite = c.get("bite") or 0.0
    cs = bite + (c.get("scratch") or 0.0)
    if e is None:
        return cs if cs > 0 else None
    ebite = e.get("bite") or 0.0
    nominal = ebite + (e.get("scratch") or 0.0)
    if (e.get("holes") or 0) == 0 and (not _num(e.get("cond")) or e["cond"] > 0):
        return cs - nominal if (cs > nominal or (cs == nominal and bite > ebite)) else None
    return cs if (cs >= nominal and cs > 0) else None


# -- the item choice (Plan 31 Task 8): pure reads of the World and a caller's refusal memory, shared by the care
# branch (`Care`, its `held_out` and `unwear_at`) and the Dress maneuver (`maneuvers.dress`, its own) --------------------
def _out(held_out, iid, now):
    """Item `iid` was refused within CARE_RETRY_MIN game minutes of `now` (`held_out`: id -> world minute)."""
    return now - held_out.get(iid, -math.inf) < CARE_RETRY_MIN


def held_dressings(world, held_out=None):
    """{kind: [held ids]} by `care_kind` (KINDS), ids ascending: an id marked `in_bag`, or refused within
    CARE_RETRY_MIN game minutes (`held_out`), left out."""
    held_out = held_out or {}
    now = world.world_minutes()
    out = {k: [] for k in KINDS}
    barred = world.marked("in_bag")
    for iid, it in world.inventory.items():
        k = care_kind(it.get("fullType"))
        if k is None or not item_id_ok(iid) or iid in barred or _out(held_out, iid, now):
            continue
        out[k].append(iid)
    return {k: sorted(v) for k, v in out.items()}


def dressing_pick(items, bleeding_time, dirty_ok=False):
    """`(kind, id)` of the best dressing in `items` (`held_dressings`) for a bleeding part, else None: a clean bandage,
    then a clean rag, then a dirty one only past DIRTY_RAG_MIN of the part's `bleeding_time` (P24-G 2's time rule) or
    with `dirty_ok` (the Dress maneuver's: an unwashed rag is taken while the part bleeds)."""
    kinds = KINDS if dirty_ok or bleeding_time > DIRTY_RAG_MIN else ("bandage", "rag")
    k = next((k for k in kinds if items[k]), None)
    return None if k is None else (k, items[k][0])


def rip_pick(world, held_out=None, prefer=None):
    """The least held id that can be ripped (`prefer`, the garment just taken off, first when it can), else None:
    never one marked `unrippable` or `in_bag`, or refused within CARE_RETRY_MIN game minutes (`held_out`). On a
    PZA/1.5.2 hello's log (`World.item_fields`) the item record says: `rip` cotton and not `worn` (denim and leather
    need a tool the planner has no action for; absent is no class). On an older log the name guess `rippable` stands
    and the inventory's first sight (the clothes worn) is left out."""
    held_out = held_out or {}
    now = world.world_minutes()
    marked = world.marked("unrippable") | world.marked("in_bag")
    fields = world.item_fields()
    ids = [iid for iid, it in world.inventory.items() if item_id_ok(iid) and iid not in marked
           and (it.get("rip") == "cotton" and it.get("worn") is not True if fields
                else rippable(it.get("fullType")) and iid not in world.first_sight)
           and not _out(held_out, iid, now)]
    if prefer in ids:
        return prefer   # P24-AJ: the garment just taken off is the one ripped
    return min(ids) if ids else None


def unwear_pick(world, held_out=None, unwear_at=None):
    """`(item id, loc, cover)` of the worn cotton garment covering the least (its clothing record's bite + scratch,
    ties by the least id), else None: the item record reads `worn` and `rip` "cotton" and carries a clothing record
    whose `loc` UNWEAR_NEVER does not match; never one marked `unrippable` or `in_bag`, refused within CARE_RETRY_MIN
    game minutes (`held_out`) or unworn within WEAR_RETRY_MIN (`unwear_at`: id -> world minute of its unwear)."""
    held_out, unwear_at = held_out or {}, unwear_at or {}
    now = world.world_minutes()
    barred = world.marked("unrippable") | world.marked("in_bag")
    best = None
    for iid, it in world.inventory.items():
        c = it.get("clothing")
        loc = c.get("loc") if isinstance(c, dict) else None
        if (not item_id_ok(iid) or it.get("worn") is not True or it.get("rip") != "cotton" or iid in barred
                or not isinstance(loc, str) or UNWEAR_NEVER.search(loc) or _out(held_out, iid, now)
                or now - unwear_at.get(iid, -math.inf) < WEAR_RETRY_MIN):
            continue
        cover = (c.get("bite") or 0.0) + (c.get("scratch") or 0.0)
        if best is None or (cover, iid) < best[0]:
            best = ((cover, iid), iid, loc, cover)
    return None if best is None else best[1:]


def dress_material(world, iid):
    """Held item `iid` is something the Dress's pick can use (the item choice's own predicates): a dressing of any
    kind (`care_kind`), or a cotton garment, worn or not (the rip's and the unwear's `rip` "cotton"; on a log before
    PZA/1.5.2 the name guess `rippable`)."""
    it = world.inventory.get(iid) or {}
    ft = it.get("fullType")
    if care_kind(ft) is not None:
        return True
    return it.get("rip") == "cotton" if world.item_fields() else rippable(ft)


def dress_pick(world, bleeding_time, held_out=None, unwear_at=None, prefer=None, dirty_ok=True):
    """The Dress maneuver's choice for one bleeding part, in its order: `("bandage", id, kind)` with the best held
    dressing (`dressing_pick`, an unwashed rag taken with `dirty_ok`), else `("rip", id)` of a held unworn cotton
    garment (`rip_pick`, `prefer` first), else `("unwear", id, loc, cover)` of the worn cotton garment covering the
    least (`unwear_pick`); else None, nothing held and nothing to tear. Each step needs its skill announced
    (`World.can`: `bandage`; `rip`; `unwear` with `rip` and the item record's fields, as the care branch's unwear)."""
    if not world.can("bandage"):
        return None
    got = dressing_pick(held_dressings(world, held_out), bleeding_time, dirty_ok)
    if got is not None:
        return ("bandage", got[1], got[0])
    rip = rip_pick(world, held_out, prefer) if world.can("rip") else None
    if rip is not None:
        return ("rip", rip)
    if world.can("unwear") and world.can("rip") and world.item_fields():
        pick = unwear_pick(world, held_out, unwear_at)
        if pick is not None:
            return ("unwear",) + tuple(pick)
    return None


class Care(Policy):
    """The care branch's policy (the module docstring): `observe()` every tick, `choose()` when not busy, `quiet` set
    by Survive each tick (no zombie within DISENGAGE_R: the wash's condition)."""

    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.quiet = False
        self.sends = {}      # item id -> its last care Action
        self.held_out = {}   # item id -> world minute its care action was refused (CARE_RETRY_MIN)
        self.fresh = {}      # part index -> `World.frame_n` when its bandage's done was read (minor 6)
        self._read = set()   # the aids whose end observe() has read
        self.ride = None     # the last bandage sent with keepMoving (P24-U), tracked by its own act lines
        self.ride_stopped_at = -math.inf   # the wall of the last ride the engine stopped (RIDE_RETRY_S)
        self.ride_now = False   # Survive sets it on a tick the threat yields to a ride: the bleeding step rides
        self.wear_at = {}    # item id -> world minute its wear was sent (WEAR_RETRY_MIN)
        self.wearing = None  # the candidate wear awaiting its exclusive-location check: {item, before, frame0, loc,
                             # action, done_n, replaced}
        self.rewear_sent = set()   # ids of a re-wear in flight (its send is not a candidate wear)
        self.rewear = []     # ids to put on again, the garments a wear took off while the worn defence fell
        self.drop_after = None   # the id a wear replaced, dropped under load once the check passed
        self.unwear_at = {}  # item id -> world minute its unwear was sent (WEAR_RETRY_MIN; P24-AJ)
        self.unworn_item = None   # the id the last unwear took off, ripped first once it reads unworn (P24-AJ)
        self.unwear_wound = True  # ruling P25-H: the bleeding step unwears on a quiet tick (Survive sets it each care
                                  # tick from its `UNWEAR_WOUND` switch); off, the idle stock alone unwears (P24-AJ)
        self.dirty_rag_rip = True  # ruling P25-Y: a dirty rag alone held, its part's bleedingTime at or under
                                   # DIRTY_RAG_MIN, does not block the rip or the unwear; off, a dressing of any kind
                                   # held blocks both (Survive sets it each tick from its `DIRTY_RAG_RIP`)
        self.stock_early = True   # ruling P27-K1: the wound's rip counts as a dressing under the threat branch's yield
                                  # (`CareYield._care_yields`; Survive sets it each tick from its `STOCK_EARLY`)
        self.trapped = False      # ruling P25-Q: the tick is the threat's trapped hold passed on (Survive sets it each
                                  # care tick): the bleeding step's unwear goes as on a quiet tick (never the wash)
        self.wear_worn = True     # ruling P26-E: a wear rejected `worn` marks its item worn (Survive sets it each tick
                                  # from its `WEAR_WORN`); off, the item is held out for CARE_RETRY_MIN alone
        self.worn_marked = set()  # the ids a wear rejected `worn` marked worn (P26-E: the stock line's `skipped_worn`)
        self.spent_keep = True    # ruling P27-D: a spent dressing on a part not bleeding is replaced only at a
                                  # bleedingTime at or under SPENT_REDRESS_BT (Survive sets it each tick from its
                                  # `SPENT_KEEP`); off, every spent dressing is replaced
        self.replace_quiet = True  # ruling P27-K3: a replace waits while `chasing_n` reads a chaser listed (Survive
                                   # sets it each care tick from its `REPLACE_QUIET`); off, the replace goes whatever
        self.chasing_n = 0        # Survive sets it each care tick: the zombies listed within LISTED_R chasing (P27-K3)
        self.wound_dress = True   # ruling P28-A: a part reading `wound`, not bleeding, is dressed (Survive sets it each
                                  # care tick from its `WOUND_DRESS`); off, no wound step and no want for it
        self.near_n = 0           # Survive sets it each care tick: the zombies within DANGER_R (P28-A's quiet test)
        self.dress_cls = None     # Plan 31 Task 8 (Survive's DRESS_MANEUVER, set each care tick): the maneuver class the
                                  # bleeding step starts in place of its three sends (`maneuvers.Dress`); None, the
                                  # bleeding step's own sends, the rule before it
        self.dress = None         # the running Dress (`_dress_step`), else None
        self.dress_end = []       # the ended Dresses' logs, each with its end, put on the next choose's why once
                                  # (`dress_end`, a list: fix 1, m2, two may end in one call)
        self._dress_hold = None   # (the inventory's ids, wall) of the last Dress that ended failed (fix 1, M1: no
                                  # restart until an item is added or DRESS_RETRY_S pass)

    def dressing(self):
        """The running Dress (Plan 31 Task 8), else None: while it runs, Survive's care branch holds its tick."""
        return self.dress

    def owns(self, cmd):
        """`cmd` is the running Dress's step this tick (its send is the Dress's, never cooled: Survive's `assess`)."""
        return self.dress is not None and cmd is not None and cmd is self.dress.cmd

    def sent(self, cmd, action):
        if self.owns(cmd):
            if cmd.TYPE == "bandage" and cmd.keepMoving:
                self.ride = action   # fix 1, M3: a Dress's riding bandage is the ride every P24-U reader reads
            self.dress.sent(cmd, action)   # Plan 31 Task 8: the Dress keeps its own sends and refusals
            return
        self.sends[cmd.itemId] = action
        if cmd.TYPE == "unwear":
            self.unwear_at[cmd.itemId], self.unworn_item = self.world.world_minutes(), cmd.itemId
        elif cmd.TYPE == "rip" and cmd.itemId == self.unworn_item:
            self.unworn_item = None
        if cmd.TYPE == "wear":
            self.wear_at[cmd.itemId] = self.world.world_minutes()
            if cmd.itemId in self.rewear_sent:
                self.rewear_sent.discard(cmd.itemId)
            else:
                clothing = (self.world.inventory.get(cmd.itemId) or {}).get("clothing") or {}
                self.wearing = {"item": cmd.itemId, "before": self.world.worn_total(), "frame0": self.world.frame_n,
                                "loc": clothing.get("loc"), "action": action, "done_n": None, "replaced": None}
        if cmd.TYPE == "bandage" and cmd.keepMoving:
            self.ride = action

    def riding(self):
        """The riding bandage while it runs (not yet terminal), else None: the flee's leg sent since keeps it."""
        return self.ride if self.ride is not None and not self.actions.done(self.ride) else None

    def busy(self):
        """The Policy's rule, or a ride running (its leg, or a re-aimed one, is the current action meanwhile); a Dress
        that ended (Plan 31 Task 8: `superseded` by a standing zombie within KEEP_R) no longer holds its action's slot,
        so the choose reads its end."""
        d = self.dress
        if d is not None and d.over() is not None and d.action is not None and self.last is d.action:
            return False
        return super().busy() or self.riding() is not None

    def observe(self):
        """Each care action's end, once: a bandage done leaves its part out until a newer frame (`fresh`); a refusal
        holds its item out for CARE_RETRY_MIN; a rip refused for good marks it `unrippable`; a wash refused for its
        water leaves its source out (`World.mark_dry`). A part's `fresh` entry goes once a newer frame came. A running
        Dress (Plan 31 Task 8) reads its own ends first."""
        if self.dress is not None:
            self.dress.observe()
        n = self.world.frame_n
        self.fresh = {i: at for i, at in self.fresh.items() if at >= n}
        for iid, a in list(self.sends.items()):
            if a.aid in self._read or not self.actions.done(a):
                continue
            self._read.add(a.aid)
            if a.type == "wear" and self.wearing is not None and self.wearing["action"] is a:
                if a.state == "done":
                    self.wearing["done_n"] = self.world.act_n.get(str(a.aid), n)
                    self.wearing["replaced"] = (a.result or {}).get("replaced") if isinstance(a.result, dict) else None
                else:
                    self.wearing = None
            if a.type == "bandage" and a.state == "done":
                self.fresh[a.args.get("part")] = n
            if a.state not in FAILED or (a.state == "failed" and a.reason == PREEMPTED):
                continue
            if a.state == "failed" and a.reason in RIDE_FREE and a.args.get("keepMoving") is True:
                self.ride_stopped_at = self.clock()
                continue   # P24-U: the engine stopped the ride; the item is good
            self.held_out[iid] = self.world.world_minutes()
            if (self.wear_worn and a.type == "wear" and a.state == "rejected" and a.reason == "worn"
                    and self.world.mark_worn(iid)):
                self.worn_marked.add(iid)   # P26-E: the Lua's refusal read as the garment's state
            if a.reason == "in bag" and iid in self.world.inventory:
                self.world.mark(iid, "in_bag")   # Task 10 fix 2: the move could not be queued, a hard refusal
            elif a.type == "rip" and a.reason in RIP_REFUSALS and iid in self.world.inventory:
                self.world.mark(iid, "unrippable")
            if a.type == "wash" and a.reason in DRY_REASONS:
                self.world.mark_dry((a.args.get("x"), a.args.get("y"), me_floor(self.world)))
        r = self.ride
        if r is not None and r.aid not in self._read and self.actions.done(r):   # fix 1, M3: a Dress's ride (never
            self._read.add(r.aid)                                                # in `sends`), its end read once
            if r.state == "failed" and r.reason in RIDE_FREE:
                self.ride_stopped_at = self.clock()   # RIDE_RETRY_S, as for the bleeding step's own ride
        self._wear_check()

    def _wear_check(self):
        """The exclusive-location check of the last wear (review-t9-fix9 ruling 2), read every tick once its done is
        a `me.worn` list newer than its done has come (WEAR_SETTLE_MAX frames at most): a wear can take off garments at
        exclusive locations, which its `replaced` does not name and for which the Lua sends no `item_changed`. When the
        summed bite + scratch of `me.worn` fell, the candidate is marked `wear_loses` and every held garment that read
        worn, is not the candidate or the replaced one and whose location the new list lacks is the knocked-off one:
        its stale `worn` flag is cleared and it is put on again, one a tick (`_wear`); else the replaced garment is
        the one to drop under load."""
        w, wr = self.world, self.wearing
        if wr is None or wr["done_n"] is None or (w.worn_n <= wr["done_n"] and w.frame_n < wr["done_n"] + WEAR_SETTLE_MAX):
            return
        self.wearing = None
        if w.worn_total() < wr["before"]:
            w.mark(wr["item"], "wear_loses")
            locs = {e.get("loc") for e in (w.worn or ()) if isinstance(e, dict)}
            off = sorted(i for i, it in w.inventory.items()
                         if it.get("worn") is True and i != wr["item"] and i != wr["replaced"]
                         and isinstance(it.get("clothing"), dict) and it["clothing"].get("loc") not in locs)
            for i in off:
                w.inventory[i].pop("worn", None)
            self.rewear = off
            self.drop_after = None
        else:
            self.drop_after = wr["replaced"]

    # -- the reads ------------------------------------------------------------------------------------------------
    def _items(self):
        """{kind: [held ids]} by `care_kind`, an id held out by a refusal left out, ids ascending (`held_dressings`)."""
        return held_dressings(self.world, self.held_out)

    def _parts(self):
        """The frame's part records, a part whose bandage ended done on this very frame left out (`fresh`)."""
        return [p for p in ((self.world.body or {}).get("parts") or ())
                if isinstance(p, dict) and _num(p.get("i")) and p["i"] not in self.fresh]

    def _bleeding(self):
        """The bleeding unbandaged parts, worst first: deep, then the longest bleeding time, then the least index."""
        ps = [p for p in self._parts() if p.get("bleeding") is True and p.get("bandaged") is not True]
        return sorted(ps, key=lambda p: (p.get("deep") is not True, -(p.get("bleedingTime") or 0.0), p["i"]))

    def _spent(self):
        """The bandaged parts whose bandage is spent: `bandageLife` at or under 0, or `bandageDirty`."""
        return [p for p in self._parts() if p.get("bandaged") is True
                and ((_num(p.get("bandageLife")) and p["bandageLife"] <= 0) or p.get("bandageDirty") is True)]

    def _wounds(self):
        """Ruling P28-A: the parts reading `wound` true (PZA/1.7.2: scratched, cut, bitten or deep-wounded, the Lua's
        rank-1 test of a bandageable part), `bleeding` false and `bandaged` false, the lowest `h` first, then the least
        index; none on a frame whose parts carry no `wound` (decoded None)."""
        ps = [p for p in self._parts() if p.get("wound") is True and p.get("bleeding") is False
              and p.get("bandaged") is False]
        return sorted(ps, key=lambda p: (p.get("h") if _num(p.get("h")) else math.inf, p["i"]))

    def _redresses(self, p):
        """Ruling P27-D: spent part `p`'s dressing is replaced: `spent_keep` off, the part reading `bleeding` true, or
        its `bleedingTime` at or under SPENT_REDRESS_BT (a frame carrying none: the rule before it)."""
        bt = p.get("bleedingTime")
        return not self.spent_keep or p.get("bleeding") is True or not _num(bt) or bt <= SPENT_REDRESS_BT

    def _rip_item(self):
        """The least held id that can be ripped, the garment the last unwear took off first (`rip_pick`)."""
        return rip_pick(self.world, self.held_out, self.unworn_item)

    # -- the choice -----------------------------------------------------------------------------------------------
    def _wound(self, items, bleeding, ride=False, unwear=False):
        """The bleeding step, `(command, why)` or (None, None): the worst bleeding part's bandage with the best held
        item, else with no rag of any kind held a garment's rip for it, else with `unwear` (ruling P25-H: `choose`'s,
        `unwear_wound`) and `quiet` the unwear of the worn cotton garment covering the least (`_unwear_step`, its why
        `{reason "unwear", part, item, loc, cover}`), which the next care tick rips (P24-AJ's `unworn_item`). With
        `ride` (P24-U) the worst bleeding part above the legs (index under LEG_FIRST) is bandaged with keepMoving, never
        a rip or an unwear (either stops the leg). Ruling P25-Y (F6, `f_goals_7-20261031-000629`: part 3 bled from game
        minute 701 to 743 with a dirty rag the only dressing held, the bleedingTime under DIRTY_RAG_MIN, and a cotton
        T-shirt held unworn): "no rag of any kind held" means no clean bandage or rag (`dirty_rag_rip`); the dirty rag
        alone, the time rule not allowing it, does not block the rip or the unwear, logged `dirty` (its id). The
        yield's reads (`tends_wound`, `rides_wound`) and the want's
        (`wants_dressing`) read it without the unwear: a tick whose step is the unwear sends, so it wants no loot."""
        w = self.world
        if ride:
            bleeding = [p for p in bleeding if p["i"] < LEG_FIRST]
        if not bleeding or not w.can("bandage"):
            return None, None
        p = bleeding[0]
        bt = p.get("bleedingTime") or 0.0
        got = dressing_pick(items, bt)
        if got is not None:
            k, iid = got
            why = {"reason": "bleeding", "part": p["i"], "item": iid, "kind": k, "bleedingTime": bt,
                   "deep": p.get("deep") is True}
            if ride:
                why["ride"] = True
            return Bandage(iid, part=p["i"], keepMoving=ride), why
        if ride or any(items[k] for k in (("bandage", "rag") if self.dirty_rag_rip else KINDS)):
            return None, None
        # ruling P25-Y (`dirty_rag_rip`): reaching here with a dirty rag held means its bleedingTime is at or under
        # DIRTY_RAG_MIN (past it the rag dressed the part above), so the rip or unwear goes; logged `dirty` (its id)
        passed = {"dirty": items["dirty"][0]} if items["dirty"] else {}
        rip = self._rip_item() if w.can("rip") else None
        if rip is not None:
            return Rip(rip), dict({"reason": "no_rag", "part": p["i"], "item": rip}, **passed)
        if unwear and (self.quiet or self.trapped):   # P25-H: nothing to rip, so the least-covering worn cotton garment
                                                      # comes off for it (P25-Q: the trapped hold's tick too)
            cmd, why = self._unwear_step()
            if cmd is not None:
                return cmd, dict(why, part=p["i"], **passed)
        return None, None

    def stock(self):
        """The idle tick's stock, `(command, why)` or (None, None): the rag stock's rip (ruling P24-AB), else the wear
        (Task 24, `_wear`). Survive calls it only on an idle tick; nothing without `quiet`."""
        if not self.quiet:
            return None, None
        out = self._rags()
        if out[0] is None:
            out = self._unwear()
        return out if out[0] is not None else self._wear()

    def _unwear(self):
        """Ruling P24-AJ (the module docstring), the idle stock's unwear: `_unwear_step` while a bleeding part has
        nothing to dress it (`wants_dressing`: no dressing, no dirty rag, nothing unworn to rip); else (None, None).
        With P25-H on (`unwear_wound`) the bleeding step takes the same unwear first, on any quiet care tick."""
        if not self._bleed_wants(self._items()):   # P28-A: a scratch's want takes off no garment
            return None, None
        return self._unwear_step()

    def _unwear_step(self):
        """The unwear both paths send (P24-AJ's stock, P25-H's bleeding step): `(Unwear(itemId), why)` of
        `_unwear_pick`, the build announcing `unwear` and `rip` and stating the item record's fields; else (None,
        None), and while the last unwear's garment still reads worn within WEAR_SETTLE_MAX frames of its done (its
        `item_changed` not yet read)."""
        w = self.world
        if not (w.can("unwear") and w.can("rip") and w.item_fields()):
            return None, None
        a = self.sends.get(self.unworn_item)
        if a is not None and a.type == "unwear" and a.state == "done":
            it = w.inventory.get(self.unworn_item) or {}
            if it.get("worn") is True and w.frame_n < w.act_n.get(str(a.aid), w.frame_n) + WEAR_SETTLE_MAX:
                return None, None
        pick = self._unwear_pick()
        if pick is None:
            return None, None
        iid, loc, cover = pick
        return Unwear(iid), {"reason": "unwear", "item": iid, "loc": loc, "cover": cover}

    def _unwear_pick(self):
        """`(item id, loc, cover)` of the worn cotton garment covering the least, else None (`unwear_pick`)."""
        return unwear_pick(self.world, self.held_out, self.unwear_at)

    def _rags(self, dirty_ok=False):
        """The rag stock's rip (ruling P24-AB, the module docstring): fewer than RAG_STOCK clean dressings held, an
        unworn cotton garment held, `rip` announced; a dirty rag held refuses it unless `dirty_ok` (P27-K1's early
        rip, `early_rip`)."""
        if not self.world.can("rip"):
            return None, None
        items = self._items()
        if items["dirty"] and not dirty_ok:   # review-t21 minor 5: a dirty rag is washed first, no garment ripped
            return None, None
        held = len(items["bandage"]) + len(items["rag"])
        if held >= RAG_STOCK:
            return None, None
        rip = self._rip_item()
        if rip is None:
            return None, None
        return Rip(rip), {"reason": "stock", "item": rip, "dressings": held, "stock": RAG_STOCK}

    def early_rip(self):
        """Ruling P27-K1 (`STOCK_EARLY`, Survive's; F10, `f_goals_11-20261103-075140`: the health fell from
        62.85700988769531 to 36.4251594543457 while parts 1 and 7 bled undressed for 25.158348083496094 game minutes
        with a cotton T-shirt held and no clean dressing, the last rag gone on at game minute 656 and the stock's rip
        never sent before the bites at 665; the care's why read {bandage 0, dirty 1, rag 0} from seq 7638): the rag
        stock's rip (`_rags`) on the clean dressings alone, `bandage` and `rag` items under RAG_STOCK whatever dirty
        rag is held, its why `stock` as the stock's; Survive sends it on any tick with no zombie within DANGER_R
        (`Survive._care_stock`), never `quiet`'s DISENGAGE_R. (None, None) otherwise. Cost if wrong: a garment ripped
        while a dirty rag waits for water (review-t21 minor 5's guard, kept by the idle stock)."""
        return self._rags(dirty_ok=True)

    def dressings_held(self):
        """`{rags, bandages}`: the clean rags and bandages held (`_items`), P27-K1's `stock_early` why."""
        items = self._items()
        return {"rags": len(items["rag"]), "bandages": len(items["bandage"])}

    def _wear_quiet(self):
        """A wear (50 action ticks, `stopOnRun`) starts with no attacker, no hit reaction and no listed zombie within
        WEAR_QUIET_R (review-t9-fix9 ruling 5, point 3)."""
        me = self.world.me or {}
        if me.get("attackers") or me.get("hitReaction"):
            return False
        x, y = me.get("x"), me.get("y")
        return x is None or y is None or not any(
            z.get("x") is not None and z.get("y") is not None and math.hypot(z["x"] - x, z["y"] - y) <= WEAR_QUIET_R
            for z in self.world.zombies.values())

    def _wear(self):
        """The wear branch of the stock (Task 24; review-t9-fix9's ruling 5), `(command, why)` or (None, None), in this
        order: a garment to put on again (`rewear`, see `_wear_check`), one a tick; the replaced garment dropped under a
        load above level 0; then the best candidate (`_wear_pick`). Nothing while the last wear is not yet checked.
        Needs `wear` announced and `me.worn` known (never read as nothing worn)."""
        w = self.world
        if not w.can("wear") or w.worn is None or not self._wear_quiet():
            return None, None
        if self.wearing is not None:
            return None, None   # a wear in flight, or its check not yet due (`observe`)
        while self.rewear:
            iid = self.rewear.pop(0)
            if iid in w.inventory and w.inventory[iid].get("worn") is not True:
                self.rewear_sent.add(iid)
                return Wear(iid), {"reason": "rewear", "item": iid}
        if self.drop_after is not None:
            iid, self.drop_after = self.drop_after, None
            it = w.inventory.get(iid)
            if (it is not None and it.get("worn") is not True and ((w.load or {}).get("level") or 0) >= 1
                    and w.can("drop") and item_id_ok(iid)):
                return Drop(iid), {"reason": "drop_replaced", "item": iid}
        pick = self._wear_pick()
        if pick is None:
            return None, None
        iid, loc, gain = pick
        why = {"reason": "wear", "item": iid, "loc": loc, "gain": gain}
        skipped = sum(1 for i in self.worn_marked if (w.inventory.get(i) or {}).get("worn") is True)
        if skipped:
            why["skipped_worn"] = skipped   # P26-E: the garments a `worn` refusal marked, left out
        return Wear(iid), why

    def _wear_pick(self):
        """`(item id, loc, gain)` of the held unworn garment whose clothing record adds the most over what is worn at its
        location (`wear_gain`; ties to the higher bite, then the fuller condition, then the least id), else None. An
        item whose record reads `worn` (the engine's `item_changed`, or a wear rejected `worn`: ruling P26-E), marked
        `in_bag` or `wear_loses`, held out by a refusal (CARE_RETRY_MIN) or worn within WEAR_RETRY_MIN game minutes is
        left out."""
        w = self.world
        now = w.world_minutes()
        worn = {e.get("loc"): e for e in w.worn if isinstance(e, dict)}
        barred = set(w.marked("in_bag")) | set(w.marked("wear_loses"))
        best = None
        for iid, it in w.inventory.items():
            c = it.get("clothing")
            if (not isinstance(c, dict) or it.get("worn") is True or not item_id_ok(iid) or iid in barred
                    or now - self.held_out.get(iid, -math.inf) < CARE_RETRY_MIN
                    or now - self.wear_at.get(iid, -math.inf) < WEAR_RETRY_MIN):
                continue
            gain = wear_gain(c, worn.get(c.get("loc")))
            if gain is None:
                continue
            full = (c["cond"] / c["condMax"]) if _num(c.get("condMax")) and c["condMax"] > 0 else 0.0
            rank = (-gain, -(c.get("bite") or 0.0), -full, iid)
            if best is None or rank < best[0]:
                best = (rank, iid, c.get("loc"), gain)
        return None if best is None else best[1:]

    def wants_dressing(self):
        """`bandage` announced and a wound with nothing to dress it (P24-AB: the want `bandage`): a bleed's
        (`_bleed_wants`), or ruling P28-A's (`_wound_wants`)."""
        if not self.world.can("bandage"):
            return False
        items = self._items()
        return self._bleed_wants(items) or self._wound_wants(items)

    def _bleed_wants(self, items):
        """A part bleeds (unbandaged) and the bleeding step has nothing to put on it: no clean bandage or rag, no dirty
        rag the time rule allows, no dirty rag to wash, no garment to rip (P24-AB); the idle stock's unwear reads it
        alone (P24-AJ)."""
        bleeding = self._bleeding()
        return bool(bleeding) and self._wound(items, bleeding)[0] is None and not items["dirty"]

    def _wound_wants(self, items):
        """Ruling P28-A: with `wound_dress` on, a part `_wounds` lists, no more than WOUND_RESERVE clean dressings held
        and no garment to rip (`rip` announced and `_rip_item`)."""
        if not self.wound_dress or not self._wounds():
            return False
        if len(items["bandage"]) + len(items["rag"]) > WOUND_RESERVE:
            return False
        return not (self.world.can("rip") and self._rip_item() is not None)

    def bleeding_n(self):
        """How many parts bleed unbandaged (ruling P24-AR's count, FLEE_CARE_N)."""
        return len(self._bleeding())

    def tends_wound(self):
        """The bleeding step would send now (ruling P24-P: Survive's threat branch yields to it beyond CARE_R)."""
        return self._wound(self._items(), self._bleeding())[0] is not None

    def dresses_wound(self, rip=False):
        """The bleeding step would send a bandage now, a dressing held for the worst bleeding part (ruling P26-D: the
        bleed's yield under a threat takes a dressing, never an unwear); with `rip` (ruling P27-K1, Survive's
        `STOCK_EARLY`) also the rip of a held cotton garment for a bleeding part with nothing to dress it."""
        cmd = self._wound(self._items(), self._bleeding())[0]
        return cmd is not None and (cmd.TYPE == "bandage" or (rip and cmd.TYPE == "rip"))

    def rides_wound(self):
        """The bleeding step would ride now (P24-U): a part above the legs bleeds and a bandage item is held, and no
        ride was stopped by the engine within RIDE_RETRY_S (Task 12 fix 2)."""
        if self.clock() - self.ride_stopped_at < RIDE_RETRY_S:
            return False
        return self._wound(self._items(), self._bleeding(), ride=True)[0] is not None

    def choose(self):
        """The next care command, or None (the module docstring's order). Under a held threat (P24-P) Survive runs
        the branch only when `tends_wound` answers, so the bleeding step is the one that sends there. The last
        Dress's end (Plan 31 Task 8) is logged once, `dress_end` on the why."""
        cmd = self._choose()
        if self.dress_end:
            self.why = dict(self.why, dress_end=self.dress_end)
            self.dress_end = []
        return cmd

    def _dress_step(self, bleeding):
        """Plan 31 Task 8 (`dress_cls` set): the bleeding step as one Dress maneuver. The running Dress steps (its
        command, or None while it waits: the tick held); one that ended is logged (`dress_end`) and dropped; with none
        running the worst bleeding part (`bleeding[0]`) starts one, riding when Survive's `ride_now` asks (then the
        worst above the legs, as `_wound`'s ride; the Dress rides only a part above them). `(command or None, held)`:
        `held` False when no Dress runs after the step (none to start, or it ended at once: a zombie within KEEP_R,
        the part no longer bleeding, nothing to dress).

        Fix 1 (review-t8): M1, no new Dress after one that ended failed until the inventory gains an item or
        DRESS_RETRY_S pass (`_dress_held_off`); M2, on a ride tick (P24-U: the ride never stops the leg) a running
        Dress that does not ride is never stepped: it is dropped (logged `dress_end` {end "ride"}) for a riding Dress
        of the worst part above the legs when a dressing is held for it, else it waits with the tick held; and no
        command but a riding bandage goes out on a ride tick (a ride the pick dropped waits for a standing tick)."""
        d = self.dress
        if d is not None and d.over() is not None:
            self._dress_ended(d)
            d = None
        if self.ride_now:   # P24-U: a ride tick dresses the worst bleeding part above the legs, as `_wound` rides
            bleeding = [p for p in bleeding if p["i"] < LEG_FIRST]
            if d is not None and not d.ride:   # fix 1, M2: a standing Dress is never stepped into the flee's leg
                if not (bleeding and self._rideable(bleeding[0])):
                    self.why = {"reason": "dress", "dress": d.log(), "ride_wait": True}
                    return None, True
                self._dress_ended(d, "ride")
                d = None
        if d is None and bleeding and not self._dress_held_off():
            d = self.dress = self.dress_cls(self.world, self.actions, self.clock, part=bleeding[0]["i"],
                                            ride=self.ride_now)
        if d is None:
            return None, False
        cmd = d.step()
        if d.over() is not None:
            self._dress_ended(d)
            return None, False
        if self.ride_now and cmd is not None and not (cmd.TYPE == "bandage" and cmd.keepMoving):
            cmd = None   # fix 1, M2: only a riding bandage goes out on a ride tick
        self.why = {"reason": "dress", "dress": d.log()}
        return cmd, True

    def _dress_ended(self, d, end=None):
        """Dress `d` is dropped: its log with its end (`end`, else its own) kept for the next why (`dress_end`); a
        failed one holds the next start off (`_dress_hold`, fix 1, M1)."""
        self.dress_end.append(dict(d.log(), end=end or d.over()))
        if d.over() == "failed":
            self._dress_hold = (frozenset(self.world.inventory), self.clock())
        if self.dress is d:
            self.dress = None

    def _dress_held_off(self):
        """Fix 1, M1: no new Dress while the last failed one's hold stands: no dressing or garment added to the
        inventory since (`dress_material`; the residuals, review-t8-fix1 n1: an unrelated looted item lifts nothing)
        and DRESS_RETRY_S not yet passed."""
        h = self._dress_hold
        if h is None:
            return False
        added = set(self.world.inventory) - h[0]
        if any(dress_material(self.world, iid) for iid in added) or self.clock() - h[1] >= DRESS_RETRY_S:
            self._dress_hold = None
            return False
        return True

    def _rideable(self, p):
        """Part `p` (above the legs) can be ridden now: a dressing is held for it (`dressing_pick`, an unwashed rag
        taken as the Dress takes it)."""
        return dressing_pick(self._items(), p.get("bleedingTime") or 0.0, dirty_ok=True) is not None

    def _choose(self):
        w = self.world
        items = self._items()
        any_rag = any(items[k] for k in KINDS)
        bleeding = self._bleeding()
        if self.dress_cls is not None:   # Plan 31 Task 8: the Dress is the bleeding step, none of its three sends
            cmd, held = self._dress_step(bleeding)
            if held or self.ride_now:
                if not held:
                    self.why = {}
                return cmd
        else:
            cmd, why = self._wound(items, bleeding, ride=self.ride_now, unwear=self.unwear_wound)
            if cmd is not None or self.ride_now:
                self.why = why or {}
                return cmd
        clean = items["bandage"] + items["rag"]
        spent = self._spent()
        kept, held = None, None
        if spent and clean and w.can("bandage"):
            take = [p for p in spent if self._redresses(p)]   # P27-D: a long bleed's spent dressing kept on
            if take and self.replace_quiet and self.chasing_n:   # P27-K3: no replace while a listed zombie chases
                held, take = {"part": take[0]["i"], "chasing": self.chasing_n}, []
            elif not take:
                kept = {"part": spent[0]["i"], "bleedingTime": spent[0].get("bleedingTime"),
                        "dirty": spent[0].get("bandageDirty")}
            if take:
                p = take[0]
                self.why = {"reason": "spent", "part": p["i"], "item": clean[0],
                            "kind": "bandage" if items["bandage"] else "rag", "life": p.get("bandageLife"),
                            "dirty": p.get("bandageDirty")}
                return Bandage(clean[0], part=p["i"])
        wound_held = None
        wounds = self._wounds() if self.wound_dress and w.can("bandage") else []
        if wounds and len(clean) > WOUND_RESERVE:
            if not self.near_n:   # P28-A: the wound dressed on a quiet care tick
                p = wounds[0]
                self.why = {"reason": "wound", "part": p["i"], "item": clean[0],
                            "kind": "bandage" if items["bandage"] else "rag", "h": p.get("h")}
                return Bandage(clean[0], part=p["i"])
        elif wounds:
            wound_held = {"part": wounds[0]["i"], "clean": len(clean)}   # P28-A: the reserve kept for a bleed
        cmd = None
        if items["dirty"] and self.quiet and w.can("wash"):
            src = w.water_sources(WASH_R)
            if src:
                d, sq, rec = src[0]
                self.why = {"reason": "dirty_rag", "item": items["dirty"][0], "source": [sq[0], sq[1]], "dist": d,
                            "tainted": rec.get("tainted")}
                cmd = Wash(items["dirty"][0], sq[0], sq[1])
        if cmd is None:
            self.why = {"bleeding": [p["i"] for p in bleeding], "spent": [p["i"] for p in spent],
                        "held": {k: len(v) for k, v in items.items()}} if (bleeding or spent or any_rag) else {}
        if kept is not None:
            self.why["spent_kept"] = kept   # P27-D: the step would have sent before it
        if held is not None:
            self.why["spent_held"] = held   # P27-K3: the replace held while a listed zombie chases
        if wound_held is not None:
            self.why["wound_held"] = wound_held   # P28-A: the wound left for the reserve
        return cmd
