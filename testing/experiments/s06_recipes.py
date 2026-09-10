"""Slice 06 measured cross-check: the recipe scanner's dataset against the running game.

One live session (server + client) that answers the question `data/recipes.json` cannot answer
about itself, because every field in it was parsed out of `media/scripts/**/*.txt` by the same
tool that wrote the file:

  1. **Is the population right?** `recipes.count` reads the four script-inventory sizes off
     `ScriptManager` inside the loaded game -- `getAllCraftRecipes`, `getAllEvolvedRecipesList`,
     `getAllRecipes` (the pre-B42 legacy `recipe` blocks) and `getAllUniqueRecipes`. The
     dataset's `meta.counts.craftRecipes` / `legacyRecipeBlocks` come from `tools/recipe_scan.py`
     reading the same text. Two independent routes to the same numbers -- expected craft 969,
     evolved 63, legacy 0.
  2. **Does a record describe the recipe the game actually loaded?** Ten craft recipes, read
     back through `recipes.craft` and compared field for field against their dataset rows:
     `category`, `time`, `getInputCount`, `getOutputCount`, and per output line the integer
     amount, the item types it can resolve to and the recipe file's own text for that line
     (`getOriginalLine()` against the dataset's `outputs[].raw` -- a string comparison that does
     not depend on the scanner and the game agreeing about how to parse anything).

The five `recipes.evolved` probes are **recorded verbatim, not compared**. Sequencing ruling
(controller, `.superpowers/sdd/06-recipes/task-4-amendments.md`): this run happens BEFORE task 3
lands, so `data/evolved-recipes.json` does not exist yet and there is nothing to compare the
evolved half against. Every reply is written into the artifact whole -- all five recipes, the
full `items` lists and their `itemFullTypes` twins -- so tasks 3 and 5 can do that comparison
offline against this file (the plan's expectations for them: `Salad` and `SaladClay` at 187
ingredients each, `Cinnamon` present in `ConeIcecream`'s list). The 187 did **not** hold: both
answered **189** and the plan's figure is the wrong one -- it counts `items/food.txt` only and
drops the two `drainable.txt` carriers (`Base.Vinegar2`, `Base.Vinegar_Jug`) that its own
"374 carriers = 372 food + 2 drainable" line names. The `EVOLVED` axis strings below say so;
the committed artifact still records `plan_expected_187` and its two `false` flags, and
`testing/artifacts/README.md` carries the erratum.

**Replaying the comparator offline.** `compare_craft` is pure -- reply in, block out -- so a
committed artifact can be re-scored at HEAD without booting the game, which is how a fix round
re-verifies this run. Everything above the `LIVE SESSION BELOW` marker is definitions, so exec
the file up to it and then feed it the artifact:

    p = "testing/experiments/s06_recipes.py"
    src = open(p, encoding="utf-8").read().rsplit("# ==== LIVE SESSION BELOW", 1)[0]
    ns = {"__file__": p}; exec(compile(src, p, "exec"), ns)
    art = json.load(open("testing/artifacts/exp06-20260910-112726/recipes.json"))
    by_name = {r["name"]: r for r in json.load(open("data/recipes.json"))["recipes"]}
    for name, rowv in art["craft"].items():
        block = ns["compare_craft"](name, rowv["axis"], by_name.get(name), rowv["reply"])

At HEAD that gives **10 of 10 recipes matched, 77 of 77 fields** against the current
`data/recipes.json` (the artifact's own run predates the scanner's sub-line fix and recorded
2 `inputCount` mismatches; see `INPUT_SUBLINE_NOTE`). Of the 77, **10 are the live-vs-live
`outputListSize` row** -- `getOutputCount()` against the length of the list the command walked,
two reads of one ArrayList -- so the dataset-versus-game count is **67**, and it was 65/67 at
run time.

**The tenth craft recipe is derived, not named.** Nine come from the brief; the tenth is "the
first row in the file whose outputs resolve to a single food type", which `pick_tenth` computes
from `data/recipes.json` in its own stored order, joined against `data/food-items.json` for
`kind == "food"`. The rule and the row it picked both travel into the artifact, so the choice is
reproducible rather than a name someone typed.

**A mismatch is a FINDING.** It is written into `comparison` with both values and left there;
nothing in this script edits `data/`, `tools/` or the artifact. Where the mechanism behind a
mismatch is known from the jar it is named in the row (`basis`), so the artifact says what
disagrees rather than only that something does -- see `INPUT_SUBLINE_NOTE`.

The run makes no world change -- no `settimespeed`, no sandbox write, no character write, no
spawned item. It only reads `ScriptManager`, so teardown is the whole cleanup path.

Everything lands in `<run_dir>/recipes.json`, copied byte-for-byte after teardown to
`testing/artifacts/<run-id>/recipes.json`. Run it with `python testing/pzt doctor` clean and
nothing else live; the doctor is re-run from here and its verdict is in the artifact.
"""
import json
import os
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/
# `load_json` / `git_say` / `git_dirty` / `doctor` / `num` used to be defined here, in
# `s05_food_scan.py` and in `s05b_drink_probe.py` word for word. Slice 06's final fix wave
# promoted the identical copies into `_common.py`; the bodies are unchanged, so nothing this
# script writes into an artifact moves.
from _common import ask, doctor, git_dirty, git_say, hard_kill, load_json, num, save
from pzt import fixture as fx
from pzt.paths import new_run_dir
from pzt.session import Timeline, make_client, make_server, teardown

USER = "admin"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECIPES = os.path.join(REPO, "data", "recipes.json")
FOODS = os.path.join(REPO, "data", "food-items.json")

# Q2, measured off the scanner and stated in the plan. `unique` has no expectation: nothing in
# this repo has ever counted `UniqueRecipe` blocks, so it is recorded and not compared.
EXPECT = {"craft": 969, "evolved": 63, "legacy": 0}

# The nine the brief names, in its own order. The tenth is derived (see `pick_tenth`).
CRAFT_NAMED = [
    ("MakeToast", "the simplest possible row: one input, one unmapped output "
                  "(`item 1 Base.Toast`), a Toaster-tagged entity recipe rather than a "
                  "`recipes/` one"),
    ("MakePizza", "ten input lines, one of which is a `-` sub-line, and an `xpAward` / "
                  "`autoLearnAny` block: the row where the dataset's flat `inputs` list and "
                  "the game's `getInputCount()` are most likely to disagree"),
    ("OpenBagOfFrozenFood", "a MAPPED output (`item 3 mapper:foodType`): the live "
                            "`getPossibleResultItems()` must enumerate all four result types, "
                            "and the amount is 3 rather than 1"),
    ("OpenEggCarton", "an amount well above 1 (`item 12 Base.Egg`) -- the row that separates "
                      "`getIntAmount()` from a hardcoded 1"),
    ("MakeMilkFromPowderBucket", "an EMPTY outputs block (26 of the 969 have one) with a "
                                 "fluid `-` sub-line among its inputs: `getOutputCount()` must "
                                 "be 0, and this is the second input-count row"),
    ("PutEggsInCarton", "the inverse of OpenEggCarton, and a second unmapped single output"),
    ("MillCornflour", "a workstation (stone mill) entity recipe in the Farming category"),
    ("MillSunflowerSeeds", "the same workstation, a different output -- so a coincidence in "
                           "MillCornflour cannot survive it"),
    ("GrindCornmeal", "the quern, and the longest `time` of the nine (300)"),
]
TENTH_RULE = ("the first row in data/recipes.json, in the file's own stored order, whose "
              "outputs resolve to exactly one item type and whose one type is a `kind == "
              "\"food\"` record in data/food-items.json")

# The five the brief names. Recorded verbatim -- see the module docstring.
EVOLVED = [
    ("Salad", "the plan's 187-ingredient row -- MEASURED 189 in exp06-20260910-112726: the "
              "plan counts items/food.txt only and omits the two drainables (Base.Vinegar2, "
              "Base.Vinegar_Jug) its own 374 = 372 + 2 carrier line names"),
    ("SaladClay", "the same `Template = Salad` on a different base item: its ingredient list "
                  "must be the SAME list as Salad's, which is what makes the template arm "
                  "measurable (both answered 189, name for name)"),
    ("ConeIcecream", "the case-insensitive template arm (Q3): its item list is expected to "
                     "contain `Cinnamon`"),
    ("Soup", "`Cookable = true` and `MinimumWater = 0.9` -- the two scalar getters no other "
             "row here exercises"),
    ("AddBaitToChum", "the one evolved recipe defined OUTSIDE evolvedrecipes.txt "
                      "(recipes/recipes_fishing_evolvedrecipe.txt), i.e. the 63rd"),
]

# MEASURED off the jar (42.20.4), and the reason a raw input-count comparison can disagree
# without either side being wrong. `CraftRecipe.LoadIO` handles a `-`-prefixed line inside an
# `inputs` block at `@218-@317 L589-L604`, attaching it to the PRECEDING input as its
# `consumeFromItemScript` and adding it to `ioLines` -- it is never added to `inputs`. A
# `+`-prefixed line goes the same way into `createToItemScript`, in the EARLIER branch
# `@122-@215 L574-L588` (the two are separate arms, not one span). `getInputCount()` is
# `inputs.size()` (`@0-@7 L257`), so it counts top-level lines only, while the dataset's
# `inputs` array is flat and lists the sub-lines beside their parents. The comparison below
# therefore carries BOTH numbers: the flat length is what is compared (the dataset as it is,
# against the game as it is) and `top_level` is the same list with the sub-lines removed, which
# is what the game's counter should equal. A row where `top_level` matches and the flat length
# does not is this modelling difference, not a lost or invented input.
INPUT_SUBLINE_NOTE = (
    "CraftRecipe.LoadIO: a `-` prefixed line inside an `inputs` block (@218-@317 L589-L604) is "
    "attached to the preceding input as consumeFromItemScript, and a `+` one (@122-@215 "
    "L574-L588) as createToItemScript; both are added to ioLines, NEITHER to `inputs`. "
    "getInputCount() is inputs.size() (@0-@7 L257). The dataset's `inputs` array is flat and "
    "keeps those sub-lines as rows of their own")


def as_list(v):
    """A Lua-side list, normalised. `TK.json` has no way to tell an empty ARRAY from an empty
    OBJECT -- `#v == 0` sends both through the object branch -- so an empty `items` /
    `itemFullTypes` / `outputs` arrives as `{}` and not `[]`. Anything else non-list (a missing
    key, an `{"error": ...}` reply) also becomes `[]`, and it is the caller's own usable-reply
    check -- `compare_craft`'s `ok = isinstance(reply, dict) and "error" not in reply` -- that
    distinguishes "empty" from "never answered"."""
    if isinstance(v, list):
        return v
    return []


def resolved_output_types(record, out):
    """The item types ONE dataset output line resolves to, as a set.

    Either the line names its types directly (`item 1 Base.Toast`) or it names a mapper
    (`item 3 mapper:foodType`), in which case the recipe's `itemMappers[<mapper>]` maps each
    RESULT type to the input type that produces it -- so the keys are the results, which is what
    `OutputScript.getPossibleResultItems()` answers with. A mapper the recipe does not define
    contributes nothing and leaves the set short, which shows up as a mismatch rather than as an
    excused empty."""
    types = set(out.get("types") or [])
    mapper = out.get("mapper")
    if mapper:
        table = (record.get("itemMappers") or {}).get(mapper) or {}
        types.update(table.keys())
    return types


def top_level_inputs(record):
    """`len(inputs)` with the `-` / `+` sub-lines removed: what `getInputCount()` should equal.
    See `INPUT_SUBLINE_NOTE` -- this is a reading of the jar, not a correction of the dataset."""
    n = 0
    for i in (record.get("inputs") or []):
        raw = (i.get("raw") or "").lstrip()
        if not raw.startswith("-") and not raw.startswith("+"):
            n += 1
    return n


def pick_tenth(recipes, food_ids):
    """The tenth craft spot check, derived from the dataset rather than named. Returns
    `(name, why)`; `(None, why)` when nothing qualifies, which is itself recorded."""
    for r in recipes:
        types = set()
        item_only = True
        for out in (r.get("outputs") or []):
            if out.get("kind") != "item":
                item_only = False
                break
            types |= resolved_output_types(r, out)
        if not item_only or len(types) != 1:
            continue
        only = next(iter(types))
        if only in food_ids:
            return r["name"], (f"{TENTH_RULE}; it is `{r['name']}` -> {only} "
                               f"({r.get('sourceFile')}:{r.get('sourceLine')})")
    return None, TENTH_RULE + "; NO row in the dataset qualified"


def row(expected, live, **extra):
    """One comparison row. `match` is False when either side is missing -- an absent live value
    is a failed reading, never an excused one (the `compare` rule of `s05_food_scan.py`)."""
    r = {"expected": expected, "live": live}
    r.update(extra)
    if expected is None or live is None:
        r["match"] = False
        r["note"] = "missing value"
    else:
        r["match"] = expected == live
    return r


def compare_craft(name, axis, record, reply):
    """One craft recipe's comparison block, plus a flat `mismatches` list.

    Pure: it takes the harness reply and the dataset record and returns the block, so the whole
    verdict can be replayed offline against the committed artifact -- which is how a later fix
    round re-verifies this run without re-running it."""
    block = {"recipe": name, "axis": axis, "dataset_record_found": record is not None,
             "lookup": (reply or {}).get("lookup") if isinstance(reply, dict) else None,
             "fields": {}, "outputs": [], "mismatches": []}
    bad = block["mismatches"]

    def flag(source, field, r):
        if r["match"] is not True:
            entry = {"source": source, "field": field,
                     "expected": r["expected"], "live": r["live"]}
            # The row's own diagnosis travels with the mismatch, so a reader of `summary
            # .mismatches` alone is never left to guess the mechanism. `top_level_matches`
            # is the one that separates a modelling difference from a lost input.
            if r.get("basis"):
                entry["why"] = r["basis"]
            if "top_level_matches" in r:
                entry["top_level"] = r.get("top_level")
                entry["top_level_matches"] = r.get("top_level_matches")
            bad.append(entry)
        return r

    # A wedged or missing reply is a mismatch on every field, not an absence to be excused:
    # `_common.ask` reports a dead side as `{"error": ...}`, which IS a dict (the slice-05
    # rule). `recipes.craft` answers a STRING for an unknown name, which is not a dict at all.
    ok = isinstance(reply, dict) and "error" not in reply
    if not ok:
        block["error"] = f"no usable reply: {str(reply)[:300]}"
    if record is None:
        block["error"] = f"no dataset record for {name}"
        block["matched"] = False
        return block
    r = reply if ok else {}
    block["missing_getters"] = r.get("missingGetters")
    block["getter_errors"] = r.get("getterErrors")
    block["null_getters"] = r.get("nullGetters")

    block["fields"]["category"] = flag("scalar", "category", row(
        record.get("category"), r.get("getCategory") if ok else None,
        dataset_field="category"))
    block["fields"]["time"] = flag("scalar", "time", row(
        num(record.get("time")), num(r.get("getTime")) if ok else None,
        dataset_field="time",
        basis="CraftRecipe.getTime() @0-@4 L209, the no-argument overload. The member is also "
              "declared as getTime(IsoGameCharacter); if Kahlua dispatched to that one the "
              "harness reports it in getterErrors rather than answering"))
    # Compared against the FLAT length, with the game's own model beside it. See
    # INPUT_SUBLINE_NOTE: a row where `top_level` agrees and `expected` does not is the
    # scanner's flat input list meeting the game's parent/sub-line one, and that is the finding.
    flat_in = len(record.get("inputs") or [])
    top_in = top_level_inputs(record)
    block["fields"]["inputCount"] = flag("scalar", "inputCount", row(
        flat_in, num(r.get("getInputCount")) if ok else None,
        dataset_field="len(inputs)", top_level=top_in,
        top_level_matches=(ok and num(r.get("getInputCount")) == top_in),
        basis=INPUT_SUBLINE_NOTE))
    flat_out = len(record.get("outputs") or [])
    block["fields"]["outputCount"] = flag("scalar", "outputCount", row(
        flat_out, num(r.get("getOutputCount")) if ok else None,
        dataset_field="len(outputs)"))
    # The live `outputs` array and `getOutputCount()` are two different reads of the same
    # ArrayList (the second is `outputs.size()`), so a disagreement between them is a harness
    # fault rather than a dataset one -- compared, not assumed.
    live_rows = as_list(r.get("outputs")) if ok else []
    block["fields"]["outputListSize"] = flag("scalar", "outputListSize", row(
        num(r.get("getOutputCount")) if ok else None, num(r.get("outputListSize")) if ok else None,
        basis="CraftRecipe.getOutputCount() vs the size of the list the command walked: two "
              "reads of one ArrayList, so they must agree"))

    for i, out in enumerate(record.get("outputs") or []):
        live = live_rows[i] if i < len(live_rows) else None
        o_block = {"index": i, "dataset_raw": out.get("raw"), "kind": out.get("kind"),
                   "live_present": live is not None}
        exp_types = sorted(resolved_output_types(record, out))
        if live is None:
            o_block["amount"] = flag("output", f"[{i}].amount",
                                     row(num(out.get("amount")), None))
            o_block["items"] = flag("output", f"[{i}].items", row(exp_types, None))
            o_block["original_line"] = flag("output", f"[{i}].originalLine",
                                            row(out.get("raw"), None))
        else:
            o_block["resource_type"] = live.get("resourceType")
            # The dataset stores the amount as a float (`3.0`); `getIntAmount()` is an int.
            # Compare as ints -- `OutputScript.getIntAmount` is `(int)amount`, so a fractional
            # amount would truncate on the live side and the two would differ, which is the
            # reading we want, not one to paper over.
            exp_amount = num(out.get("amount"))
            o_block["amount"] = flag("output", f"[{i}].amount", row(
                None if exp_amount is None else int(exp_amount), num(live.get("amount")),
                dataset_field="outputs[].amount",
                basis="OutputScript.getIntAmount() is (int)amount; the dataset stores the "
                      "float, so the comparison is against int(amount)"))
            o_block["items"] = flag("output", f"[{i}].items", row(
                exp_types, sorted(set(as_list(live.get("itemFullTypes")))),
                dataset_field="outputs[].types + itemMappers[<mapper>] keys",
                live_labels=as_list(live.get("items")),
                live_item_count=num(live.get("itemCount")),
                basis="OutputScript.getPossibleResultItems() -> OutputMapper.getResultItems(), "
                      "compared on Item.getFullName() (moduleDotType). An unmapped line still "
                      "has a mapper: OutputScript.Load @310-@334 builds one and calls "
                      "setDefaultOutputEntree with the type"))
            o_block["original_line"] = flag("output", f"[{i}].originalLine", row(
                out.get("raw"), live.get("originalLine"),
                dataset_field="outputs[].raw",
                basis="OutputScript.originalLine is the recipe file's own trimmed text for the "
                      "line -- a string check that does not depend on the scanner and the game "
                      "parsing it the same way"))
        block["outputs"].append(o_block)

    # Live output rows the dataset does not have (the other direction of the same count).
    if len(live_rows) > len(record.get("outputs") or []):
        for i in range(len(record.get("outputs") or []), len(live_rows)):
            bad.append({"source": "output", "field": f"[{i}] extra live output",
                        "expected": None, "live": live_rows[i]})
    block["matched"] = not bad
    return block


# ==== LIVE SESSION BELOW ==== everything above this line is definitions, so an offline replay
# execs the file up to this marker and calls `compare_craft` itself (see the module docstring).
rec = fx.load("default")
run_id, run_dir = new_run_dir("exp06")
path = os.path.join(run_dir, "recipes.json")
tl = Timeline()
server = make_server(run_dir, rec)
clients = []
t_start = time.time()

doctor_clean, doctor_text = doctor()
data, data_err, data_sha = load_json(RECIPES)
foods, foods_err, foods_sha = load_json(FOODS)
recipes = (data or {}).get("recipes") or []
by_name = {r["name"]: r for r in recipes}
food_ids = {r["id"] for r in (foods or {}).get("items", []) if r.get("kind") == "food"}
tenth, tenth_why = pick_tenth(recipes, food_ids)
CRAFT = list(CRAFT_NAMED)
if tenth:
    CRAFT.append((tenth, "DERIVED: " + tenth_why))
dirty, dirty_note = git_dirty("data/recipes.json")
foods_dirty, foods_dirty_note = git_dirty("data/food-items.json")

out = {"run_id": run_id,
       "meta": {
           "purpose": "live cross-check of tools/recipe_scan.py's dataset against "
                      "ScriptManager: the four script-inventory counts, ten craft recipes "
                      "compared field for field, and five evolved recipes recorded verbatim",
           "sequencing": "This run happens BEFORE slice 06 task 3 lands, by controller ruling "
                         "(.superpowers/sdd/06-recipes/task-4-amendments.md). "
                         "data/evolved-recipes.json does not exist yet, so the five "
                         "`recipes.evolved` replies are RECORDED VERBATIM and compared against "
                         "nothing here; tasks 3 and 5 do that comparison offline against this "
                         "artifact. Only `recipes.count` (against the plan's expectations and "
                         "data/recipes.json's own meta.counts) and the ten craft spot checks "
                         "(against data/recipes.json) carry a verdict in this file.",
           # The three together are the provenance: the commit NAMES a version, the sha256 IS
           # the bytes read, and `dataset_dirty` says whether the first can be trusted to be
           # the second (see s05_food_scan.py `git_short`).
           "dataset": "data/recipes.json",
           "dataset_commit": git_say("log", "-1", "--format=%h", "--", "data/recipes.json"),
           "dataset_sha256": data_sha,
           "dataset_dirty": dirty,
           "dataset_dirty_note": dirty_note,
           "dataset_read_error": data_err,
           "dataset_meta": (data or {}).get("meta"),
           "dataset_recipes": len(recipes),
           "food_dataset": "data/food-items.json",
           "food_dataset_commit": git_say("log", "-1", "--format=%h", "--",
                                          "data/food-items.json"),
           "food_dataset_sha256": foods_sha,
           "food_dataset_dirty": foods_dirty,
           "food_dataset_dirty_note": foods_dirty_note,
           "food_dataset_read_error": foods_err,
           "food_dataset_use": "only to resolve the tenth craft spot check (kind == 'food')",
           "head_commit": git_say("rev-parse", "--short", "HEAD"),
           "doctor_clean": doctor_clean, "doctor": doctor_text.strip().splitlines(),
           "expected_counts": EXPECT,
           "tenth_rule": TENTH_RULE, "tenth_derivation": tenth_why, "tenth": tenth,
           "craft_probes": [n for n, _ in CRAFT],
           "evolved_probes": [n for n, _ in EVOLVED],
           "input_subline_note": INPUT_SUBLINE_NOTE,
           "world_changes": "none -- this experiment only reads ScriptManager. No "
                            "settimespeed, no sandbox write, no character write, no spawn.",
       },
       "session": {}, "counts": None, "evolved": {}, "craft": {}, "comparison": {},
       "summary": {}}

dnote = ""
if dirty:
    dnote = " [DIRTY: the bytes are NOT that commit]"
elif dirty is None:
    dnote = f" [dirty unknown: {dirty_note}]"
print(f"dataset {out['meta']['dataset_commit']}{dnote} sha256 {str(data_sha)[:16]}: "
      f"{len(recipes)} recipes; {len(food_ids)} food ids; tenth = {tenth}; "
      f"doctor {'clean' if doctor_clean else 'DIRTY'}")
for line in doctor_text.strip().splitlines():
    print("  doctor| " + line)

try:
    if not doctor_clean:
        raise RuntimeError("pzt doctor is not clean -- refusing to boot: " + doctor_text[:400])
    server.start()
    c, _ = make_client(run_dir, USER, server, rec)
    c.start()
    clients.append(c)
    c.wait_ready()
    tl.mark("session_ready")
    out["fixture"] = rec.get("name")
    out["build"] = server.build

    def srv(cmd, args="", timeout=45):
        return ask(server, cmd, args, timeout=timeout)

    # ---- 0. session start ----------------------------------------------------
    out["session"]["players"] = srv("players")
    out["session"]["time_start"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 1. the census -------------------------------------------------------
    out["counts"] = srv("recipes.count", timeout=60)
    tl.mark("recipes_count", ok=isinstance(out["counts"], dict))
    save(path, out, tl, server)

    # ---- 2. the five evolved recipes, verbatim -------------------------------
    for name, axis in EVOLVED:
        reply = srv("recipes.evolved", name, timeout=60)
        n = len(as_list(reply.get("items"))) if isinstance(reply, dict) else 0
        out["evolved"][name] = {"axis": axis, "reply": reply, "items_recorded": n}
        tl.mark("evolved", recipe=name, items=n)
        save(path, out, tl, server)

    # ---- 3. the ten craft recipes --------------------------------------------
    for name, axis in CRAFT:
        reply = srv("recipes.craft", name, timeout=60)
        out["craft"][name] = {"axis": axis, "reply": reply}
        tl.mark("craft", recipe=name, ok=isinstance(reply, dict))
        save(path, out, tl, server)

    out["session"]["time_end"] = srv("time.snapshot")
    save(path, out, tl, server)

    # ---- 4. the comparison ---------------------------------------------------
    for name, axis in CRAFT:
        block = compare_craft(name, axis, by_name.get(name),
                              (out["craft"].get(name) or {}).get("reply"))
        out["comparison"][name] = block
        tl.mark("compared", recipe=name, mismatches=len(block.get("mismatches") or []))
    save(path, out, tl, server)

    # ---- 5. the verdict ------------------------------------------------------
    live = out["counts"] if isinstance(out["counts"], dict) else {}
    dcounts = ((data or {}).get("meta") or {}).get("counts") or {}
    counts = {
        "craft": {"live": live.get("craft"), "expected": EXPECT["craft"],
                  "dataset": dcounts.get("craftRecipes"), "dataset_rows": len(recipes),
                  "dataset_field": "meta.counts.craftRecipes"},
        "evolved": {"live": live.get("evolved"), "expected": EXPECT["evolved"],
                    "dataset": None, "dataset_rows": None,
                    "dataset_field": "none -- data/recipes.json does not count evolved "
                                     "recipes and data/evolved-recipes.json does not exist "
                                     "yet (task 3). Compared against the plan only."},
        "legacy": {"live": live.get("legacy"), "expected": EXPECT["legacy"],
                   "dataset": dcounts.get("legacyRecipeBlocks"), "dataset_rows": None,
                   "dataset_field": "meta.counts.legacyRecipeBlocks"},
    }
    for k, v in counts.items():
        sides = [v["live"], v["expected"]]
        if v["dataset"] is not None:
            sides.append(v["dataset"])
        if v["dataset_rows"] is not None:
            sides.append(v["dataset_rows"])
        v["match"] = all(s == sides[0] for s in sides) and sides[0] is not None
    counts["unique"] = {"live": live.get("unique"), "expected": None, "dataset": None,
                        "dataset_rows": None, "match": None,
                        "dataset_field": "none -- recorded, not compared: nothing in this repo "
                                         "counts UniqueRecipe blocks"}
    if live.get("missingAccessors"):
        counts["missing_accessors"] = live["missingAccessors"]

    per_recipe, mismatches, fields_n, fields_m = {}, [], 0, 0
    for name, block in out["comparison"].items():
        n = m = 0
        for r in (block.get("fields") or {}).values():
            n += 1
            m += 1 if r.get("match") is True else 0
        for o in (block.get("outputs") or []):
            for key in ("amount", "items", "original_line"):
                if isinstance(o.get(key), dict):
                    n += 1
                    m += 1 if o[key].get("match") is True else 0
        # `matched`, NOT `not mismatches`: `compare_craft` returns early with `matched: False`
        # and an EMPTY `mismatches` list when there is no dataset record for the name (`:291`),
        # and an empty list is falsy -- so the emptiness test would have scored an unfound
        # recipe as a pass. Every recipe in `exp06-20260910-112726` had a record, so the two
        # readings agree on that run (10/10 either way); this is the latent case closed.
        per_recipe[name] = {"fields": n, "matched": m,
                            "mismatched": len(block.get("mismatches") or []),
                            "ok": block.get("matched") is True,
                            "getter_errors": block.get("getter_errors"),
                            "missing_getters": block.get("missing_getters")}
        for b in (block.get("mismatches") or []):
            mismatches.append(dict(b, recipe=name))
        fields_n += n
        fields_m += m

    evolved_summary = {}
    for name, _ in EVOLVED:
        reply = (out["evolved"].get(name) or {}).get("reply")
        if isinstance(reply, dict):
            evolved_summary[name] = {
                "ingredientCount": reply.get("ingredientCount"),
                "items_recorded": len(as_list(reply.get("items"))),
                "fullTypes_recorded": len(as_list(reply.get("itemFullTypes"))),
                "baseItem": reply.get("getBaseItem"), "resultItem": reply.get("getResultItem"),
                "maxItems": reply.get("getMaxItems"), "cookable": reply.get("isCookable"),
                "minimumWater": reply.get("getMinimumWater"),
                "lookup_route": (reply.get("lookup") or {}).get("route"),
                "missingGetters": reply.get("missingGetters"),
                "getterErrors": reply.get("getterErrors"),
                "nullGetters": reply.get("nullGetters")}
        else:
            evolved_summary[name] = {"error": str(reply)[:300]}
    # Recorded, NOT a verdict: there is no dataset to compare the evolved half against in this
    # run (see meta.sequencing). These are the plan's expectations for tasks 3 and 5, evaluated
    # here only so the artifact says plainly what this run saw.
    salad = evolved_summary.get("Salad", {}).get("ingredientCount")
    saladclay = evolved_summary.get("SaladClay", {}).get("ingredientCount")
    cone = as_list(((out["evolved"].get("ConeIcecream") or {}).get("reply") or {}).get("items")) \
        if isinstance((out["evolved"].get("ConeIcecream") or {}).get("reply"), dict) else []
    cone_full = as_list(((out["evolved"].get("ConeIcecream") or {}).get("reply") or {})
                        .get("itemFullTypes")) \
        if isinstance((out["evolved"].get("ConeIcecream") or {}).get("reply"), dict) else []
    observations = {
        "salad_ingredients": salad, "salad_clay_ingredients": saladclay,
        "salad_pair_equal": (salad is not None and salad == saladclay),
        "plan_expected_187": 187,
        "salad_matches_plan": salad == 187, "salad_clay_matches_plan": saladclay == 187,
        "cone_icecream_lists_cinnamon": any("Cinnamon" in str(x) for x in cone + cone_full),
        "note": "observations only -- there is no evolved dataset in the tree at run time to "
                "compare against (meta.sequencing). Tasks 3 and 5 own the verdict.",
    }

    out["summary"] = {
        "counts": counts,
        "counts_all_match": all(v.get("match") for k, v in counts.items()
                                if k in ("craft", "evolved", "legacy")),
        "craft_checked": len(out["comparison"]),
        "craft_all_matched": (bool(per_recipe) and len(per_recipe) == len(CRAFT)
                              and all(v["ok"] for v in per_recipe.values())),
        "craft_matched": sum(1 for v in per_recipe.values() if v["ok"]),
        "fields_compared": fields_n, "fields_matched": fields_m,
        "fields_mismatched": len(mismatches),
        # A mismatch whose `top_level_matches` is true is the flat-inputs-vs-`inputs.size()`
        # modelling difference of INPUT_SUBLINE_NOTE, where the dataset carries MORE than the
        # game's counter rather than something different. Counted apart so neither number has
        # to be read with a caveat attached.
        "fields_mismatched_input_subline_model":
            sum(1 for b in mismatches if b.get("top_level_matches") is True),
        "fields_mismatched_other":
            sum(1 for b in mismatches if b.get("top_level_matches") is not True),
        "per_recipe": per_recipe, "mismatches": mismatches,
        "evolved_recorded": len([1 for v in evolved_summary.values() if "error" not in v]),
        "evolved": evolved_summary,
        "evolved_observations": observations,
        "tenth": tenth, "tenth_derivation": tenth_why,
        "dataset_commit": out["meta"]["dataset_commit"],
        "dataset_sha256": out["meta"]["dataset_sha256"],
        "dataset_dirty": out["meta"]["dataset_dirty"],
        "dataset_dirty_note": out["meta"]["dataset_dirty_note"],
        "doctor_clean": doctor_clean,
    }
except Exception as e:                   # noqa: BLE001 - keep the rows already collected
    out["error"] = f"{type(e).__name__}: {e}"
    out["traceback"] = traceback.format_exc()[-3000:]
    tl.mark("error", detail=str(e)[:200])
    print(out["traceback"])
finally:
    # Nothing to restore: this experiment reads ScriptManager and writes nothing to the world.
    # So teardown is the whole cleanup path, exactly as in s05_food_scan.py.
    out["wall_seconds"] = round(time.time() - t_start, 1)
    save(path, out, tl, server)          # evidence on disk before the shutdown can go wrong
    try:
        teardown(tl, server, clients)    # graceful: the quit/stop rcs land in the timeline
    finally:
        hard_kill(server, clients)       # guaranteed, whatever teardown did
        out["wall_seconds"] = round(time.time() - t_start, 1)
        save(path, out, tl, server)      # the committed artifact: post-teardown timeline+errors
        # A byte-for-byte copy of THAT file, so the tracked artifact cannot drift from the run
        # directory that produced it.
        dest = os.path.join(REPO, "testing", "artifacts", run_id, "recipes.json")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(path, dest)
            print(f"copied -> {dest}")
        except Exception as e:           # noqa: BLE001 - teardown path, never raise
            print(f"could not copy to {dest}: {type(e).__name__}: {e}")
print(json.dumps(out.get("summary", out.get("error", "no summary")), indent=1)[:9000])
