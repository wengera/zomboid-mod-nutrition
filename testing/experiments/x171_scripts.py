"""Plan 6 Task 8, X15 (`x171p`): the ItemType-omitted partial block and a second mod's block -- LIVE.

Two boots, one artifact (`scripts.json`, `phases.solo` and `phases.pair`):

  solo  PZTestKit + TKX_PartialBlock alone. Its `common/media/scripts/tkx_partial_block.txt` is the
        x121 Orange body MINUS `ItemType` (`DisplayCategory = Food, Calories = 400.0,
        NR_Nutrients = fibre:12;vitC:3`). Nothing after it restates `ItemType`, so this boot alone
        answers ruling 11's question: does a block with `ItemType` omitted still merge into a Food?
        (Added by the implementer: in the pair boot TKX_PartialBlock2 restates `ItemType = base:food`
        AFTER this block, which would mask a demotion the omission caused.)
  pair  the profile `x17-partial` as built: + TKX_PartialBlock2 (`DisplayCategory = Food,
        ItemType = base:food, NR_Nutrients = fibre:13;vitC:4`), whose basename sorts after.
        Its question: does a second mod's partial block land on an already-populated
        `defaultModData` (#1281's second half)?

Arms in each boot, every two-sided read CLIENT FIRST (the pass-2 lesson):
  A  `items.count` (server only: the command has no client twin) -- `total` and
     `foodByModule.Base` against the exp05-20260910-084109 baseline (total 5092, Base 722,
     `food-scan.json` `items_count`): 723 = the block declared a new item, 721 = Orange left the
     food pool.
  B  `item.script Base.Orange` and `Base.Apple` both sides. The script-object read carries no
     macro on Kahlua (the known gap, x121 M1): recorded, not graded.
  C  RCON `additem` of one `Base.Orange` (server-instantiated, synced to the client), the client
     polled until it resolves, then `witness.fields item admin/#<id>` with the six macro getters
     plus identity getters on both sides. Prediction (merge): 400 / 16.27 / 0.30 / 1.0 / -0.12 /
     -0.08 (#1013-#1015). The alternative shows as getters in `missing` (not a Food) or the count
     moving.
     C2: a client-local `item.spawn Base.Orange` (S6: the server never hears of it), read on the
     client only -- the client's own script instantiating the item; the server read of that id is
     expected unresolved and is recorded as such.
  D  `witness.moddata item:admin/#<id> NR_Nutrients` both sides: solo predicts `fibre:12;vitC:3`;
     pair predicts the second mod's `fibre:13;vitC:4` if a second partial block lands on an
     already-populated default modData, the first's if not, absent if the key never lands.
  E  `Base.Apple` the same way: the control, no `NR_Nutrients` key.

X19 is NOT separated here: id, folder, stored path and display name all sort TKX_PartialBlock
first (`TKX_PartialBlock` < `TKX_PartialBlock2`, `tkx_partial_block.txt` < `tkx_partial_block2.txt`
by '.' 0x2E < '2' 0x32, `TKX Partial Block` < `TKX Partial Block 2`).

**The two rules a driver never breaks.**
  1. A driver is NEVER edited after its run; a post-run edit is a skew note.
  2. A reading that comes back trivial, unmeasured or falsified is written as such, never re-run.
"""
import json
import os
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # testing/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                    # experiments/

from _common import ask, doctor, git_dirty, git_say, hard_kill   # noqa: E402
from pzt import fixture as fx, profile                          # noqa: E402
from pzt.paths import new_run_dir                               # noqa: E402
from pzt.session import Timeline, make_client, make_server, teardown, verify   # noqa: E402

PROFILE = "x17-partial"
SESSION = ("Plan 6 X15: the ItemType-omitted partial Orange block (TKX_PartialBlock, script under common/) "
           "alone, then beside a second mod's partial block (TKX_PartialBlock2): two boots of the default fixture")
ARTIFACT = "scripts.json"
USER = "admin"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA_DIR = "testing/PZTestKit/PZTestKit/42/media/lua"
SECOND = "TKX_PartialBlock2"

BASELINE_RUN = "exp05-20260910-084109"     # food-scan.json items_count
BASELINE_TOTAL = 5092
BASELINE_BASE_FOOD = 722

MACROS = "getCalories,getCarbohydrates,getLipids,getProteins,getHungChange,getThirstChange"
IDENT = "getFullType,getDisplayCategory,getCategory,getType,getOffAge,getOffAgeMax,getID"
FIELDS = MACROS + "," + IDENT
FIELD_COUNT = 13
# #1013 (Calories 400), #1014 (carbs 16.27, lipids 0.30, proteins 1.0, hung -0.12), #1015 (ThirstChange
# script -8 -> instance -0.08): the merge prediction. Apple's vanilla values: #1009.
PRED_ORANGE = {"getCalories": 400.0, "getCarbohydrates": 16.27, "getLipids": 0.30, "getProteins": 1.0,
               "getHungChange": -0.12, "getThirstChange": -0.08}
PRED_APPLE = {"getCalories": 95.0, "getCarbohydrates": 25.13, "getLipids": 0.31, "getProteins": 0.47,
              "getHungChange": -0.16}
PRED_NR = {"solo": "fibre:12;vitC:3", "pair": "fibre:13;vitC:4"}
TOL = 1e-3
SPAWN_WAIT, SPAWN_TRIES = 2.5, 6

LOG_RX = re.compile(r"tkx_partial|TKX_PartialBlock|InvalidParameterException|NR_Nutrients|"
                    r"Orange", re.I)
LOG_LIMIT = 60

prof = profile.load(PROFILE)
rec_fx = fx.load(prof.fixture)
run_id, run_dir = new_run_dir("x171p")
path = os.path.join(run_dir, ARTIFACT)
tl, t0 = Timeline(), time.time()
server, client, clients = None, None, []


def wall():
    return round(time.time() - t0, 3)


out = {
    "run_id": run_id, "session": SESSION, "user": USER, "profile": prof.report(),
    "commit": git_say("rev-parse", "--short", "HEAD"),
    "probe_commits": {m: git_say("log", "-1", "--format=%h", "--", f"testing/experiments/{m}")
                      for m in ("TKX_PartialBlock", "TKX_PartialBlock2")},
    "harness_lua_commit": git_say("log", "-1", "--format=%h", "--", LUA_DIR),
    "harness_lua_dirty": git_dirty(LUA_DIR)[0],
    "baseline": {"run": BASELINE_RUN, "file": "food-scan.json", "items_count.total": BASELINE_TOTAL,
                 "items_count.foodByModule.Base": BASELINE_BASE_FOOD},
    "predictions": {"orange_merge": PRED_ORANGE, "apple_vanilla": PRED_APPLE, "nr_nutrients": PRED_NR,
                    "foodByModule.Base": BASELINE_BASE_FOOD, "tolerance": TOL},
    "deviations": [
        "Two boots, not one: a solo boot of TKX_PartialBlock alone is added first, because in the profile's "
        "pair boot TKX_PartialBlock2 restates ItemType = base:food after the omitting block and would mask a "
        "demotion the omission caused.",
        "items.count is server-only (no client twin); arm A is one-sided.",
        "Arm C's instance is spawned by RCON additem (server-instantiated, synced to the client), not by the "
        "client item.spawn the brief names: a client spawn is invisible to the server (S6), so the two-sided "
        "read needs a server item. The client item.spawn is kept as arm C2, client-side only.",
    ],
    "phases": {}, "notes": [],
}


def persist():
    try:
        out["timeline"] = list(tl.items)
        if server is not None:
            out["server_errors"] = server.errors[:20]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, path)
    except Exception as e:                     # noqa: BLE001
        print(f"could not write {path}: {type(e).__name__}: {e}")


def probe(side, cmd, args=""):
    w0 = wall()
    r = ask(side, cmd, args)
    return {"cmd": cmd, "args": args, "wall": w0, "wall_done": wall(), "reply": r}


def fields(p):
    r = p.get("reply")
    return r.get("fields") if isinstance(r, dict) and isinstance(r.get("fields"), dict) else None


def compare(got, pred):
    if not isinstance(got, dict):
        return {"ok": False, "why": "no fields"}
    rows, ok = {}, True
    for k, v in pred.items():
        g = got.get(k)
        good = isinstance(g, (int, float)) and not isinstance(g, bool) and abs(g - v) <= TOL
        ok = ok and good
        rows[k] = {"pred": v, "got": g, "ok": good}
    return {"ok": ok, "rows": rows}


def nr_value(p):
    r = p.get("reply")
    if not isinstance(r, dict):
        return None
    vals = r.get("values")
    return vals.get("NR_Nutrients") if isinstance(vals, dict) else None


def grep_numbered(fname, rx, limit):
    hits = []
    try:
        with open(fname, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if rx.search(line):
                    hits.append({"line": n, "text": line.strip()[:220]})
                    if len(hits) >= limit:
                        break
    except OSError as e:
        return [{"error": f"{type(e).__name__}: {e}"}]
    return hits


def spawn_rcon(ph, full):
    ok, reply = server.rcon(f'additem "{USER}" "{full}" 1')
    row = {"type": full, "rcon_ok": ok, "rcon_reply": str(reply)[:200], "wall_rcon": wall(), "attempts": []}
    for i in range(SPAWN_TRIES):
        time.sleep(SPAWN_WAIT)
        c = probe(client, "witness.fields", f"item {USER}/{full} getID")
        f = fields(c) or {}
        row["attempts"].append({"attempt": i + 1, "wall": c["wall"], "resolved": (c["reply"] or {}).get("resolved")
                                if isinstance(c["reply"], dict) else None, "id": f.get("getID")})
        if f.get("getID") is not None:
            break
    s = probe(server, "witness.fields", f"item {USER}/{full} getID")
    row["server_id_read"] = s
    row["client_id"] = row["attempts"][-1]["id"] if row["attempts"] else None
    row["server_id"] = (fields(s) or {}).get("getID")
    row["ids_agree"] = row["client_id"] is not None and row["client_id"] == row["server_id"]
    ph.setdefault("spawns", []).append(row)
    tl.mark("spawn", type=full, cid=row["client_id"], sid=row["server_id"])
    return row


def item_reads(ph, label, full, item_id, pred):
    if isinstance(item_id, float) and item_id == int(item_id):
        item_id = int(item_id)
    subj = f"{USER}/#{item_id}" if item_id is not None else f"{USER}/{full}"
    rd = {"subject": subj}
    rd["fields_client"] = probe(client, "witness.fields", f"item {subj} {FIELDS}")
    rd["fields_server"] = probe(server, "witness.fields", f"item {subj} {FIELDS}")
    rd["moddata_client"] = probe(client, "witness.moddata", f"item:{subj} NR_Nutrients")
    rd["moddata_server"] = probe(server, "witness.moddata", f"item:{subj} NR_Nutrients")
    for side in ("client", "server"):
        rr = rd[f"fields_{side}"]["reply"]
        rd[f"count_ok_{side}"] = isinstance(rr, dict) and rr.get("count") == FIELD_COUNT
        rd[f"grade_{side}"] = compare(fields(rd[f"fields_{side}"]), pred)
        rd[f"nr_{side}"] = nr_value(rd[f"moddata_{side}"])
    ph[label] = rd
    persist()
    return rd


def boot(name, mods, sources):
    global server, client, clients
    ph = {"name": name, "mods": list(mods)}
    out["phases"][name] = ph
    client, clients = None, []
    ok, text = doctor()
    ph["doctor_clean"], ph["doctor"] = ok, text.strip().splitlines()
    if not ok:
        ph["error"] = "doctor not clean; boot not started (CLAUDE.md s5)"
        persist()
        return False
    sub = os.path.join(run_dir, name)
    os.makedirs(sub, exist_ok=True)
    server = make_server(sub, rec_fx, mods=list(mods), mod_sources=dict(sources), mod_skip=prof.skip,
                         sandbox=prof.sandbox or None, ini=prof.ini)
    try:
        server.start(timeout=prof.server_timeout)
        tl.mark("server_started", stage=name)
        client, _ = make_client(sub, USER, server, rec_fx)
        client.start()
        clients = [client]
        client.wait_ready(timeout=prof.client_timeout)
        tl.mark("session_ready", stage=name)
        ph["session_ready_wall"] = wall()
        ph["build"] = server.build
        ph["mods_not_found"] = {"server": sorted(set(server.mods_not_found)),
                                "client": sorted(set(client.mods_not_found))}
        if name == "pair":
            ph["verify"] = verify(prof, server, clients, tl)
        # A
        ph["items_count"] = probe(server, "items.count")
        ic = ph["items_count"]["reply"]
        if isinstance(ic, dict):
            ph["A"] = {"total": ic.get("total"), "food": ic.get("food"),
                       "foodByModule": ic.get("foodByModule"),
                       "base_food": (ic.get("foodByModule") or {}).get("Base")
                       if isinstance(ic.get("foodByModule"), dict) else None}
            ph["A"]["base_food_equals_baseline"] = ph["A"]["base_food"] == BASELINE_BASE_FOOD
            ph["A"]["total_minus_baseline"] = (ic.get("total") - BASELINE_TOTAL) \
                if isinstance(ic.get("total"), (int, float)) else None
        persist()
        # B
        ph["B"] = {}
        for full in ("Base.Orange", "Base.Apple"):
            ph["B"][full] = {"client": probe(client, "item.script", full),
                             "server": probe(server, "item.script", full)}
        persist()
        # pre-existing items of the two types (getFirstTypeRecurse would pick them first)
        ph["pre"] = {full: {"client": probe(client, "witness.fields", f"item {USER}/{full} getID"),
                            "server": probe(server, "witness.fields", f"item {USER}/{full} getID")}
                     for full in ("Base.Orange", "Base.Apple")}
        # C + D
        so = spawn_rcon(ph, "Base.Orange")
        item_reads(ph, "C_orange", "Base.Orange", so["server_id"] or so["client_id"], PRED_ORANGE)
        # C2: a client-local spawn
        sp = probe(client, "item.spawn", "Base.Orange")
        m = re.search(r"id=(-?\d+)", str(sp.get("reply")))
        lid = m.group(1) if m else None
        ph["C2_spawn"] = sp
        ph["C2_local_id"] = lid
        if lid is not None:
            item_reads(ph, "C2_local_orange", "Base.Orange", lid, PRED_ORANGE)
        # E
        sa = spawn_rcon(ph, "Base.Apple")
        item_reads(ph, "E_apple", "Base.Apple", sa["server_id"] or sa["client_id"], PRED_APPLE)
        ph["nr_prediction"] = PRED_NR[name]
        persist()
    except Exception as e:                     # noqa: BLE001
        ph["error"], ph["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
        tl.mark("error", stage=name, detail=str(e)[:200])
    finally:
        persist()
        try:
            teardown(tl, server, clients)
        except Exception as e:                 # noqa: BLE001
            ph["teardown_error"] = f"{type(e).__name__}: {e}"
        finally:
            hard_kill(server, clients)
        ph["client_lua_error"] = ("lua_error" in getattr(client, "seen", ())) if client else None
        ph["logs"] = {"limit": LOG_LIMIT, "pattern": LOG_RX.pattern,
                      "server": grep_numbered(server.log_path, LOG_RX, LOG_LIMIT),
                      "client": grep_numbered(client.console, LOG_RX, LOG_LIMIT) if client else None}
        ph["server_error_count"] = len(server.errors)
        ph["server_errors"] = server.errors[:20]
        persist()
    return True


try:
    solo_mods = [m for m in prof.mods if m != SECOND]
    solo_src = {k: v for k, v in prof.sources.items() if k != SECOND}
    if boot("solo", solo_mods, solo_src):
        boot("pair", prof.mods, prof.sources)
    s = {}
    for name in ("solo", "pair"):
        ph = out["phases"].get(name) or {}
        co = ph.get("C_orange") or {}
        s[name] = {
            "base_food": (ph.get("A") or {}).get("base_food"),
            "total": (ph.get("A") or {}).get("total"),
            "orange_merge_client": (co.get("grade_client") or {}).get("ok"),
            "orange_merge_server": (co.get("grade_server") or {}).get("ok"),
            "nr_client": co.get("nr_client"), "nr_server": co.get("nr_server"),
            "nr_pred": PRED_NR[name],
            "apple_nr_client": (ph.get("E_apple") or {}).get("nr_client"),
            "apple_nr_server": (ph.get("E_apple") or {}).get("nr_server"),
            "local_nr_client": (ph.get("C2_local_orange") or {}).get("nr_client"),
            "local_merge_client": ((ph.get("C2_local_orange") or {}).get("grade_client") or {}).get("ok"),
            "error": ph.get("error"),
        }
    out["summary"] = s
except Exception as e:                         # noqa: BLE001
    out["error"], out["traceback"] = f"{type(e).__name__}: {e}", traceback.format_exc()[-3000:]
finally:
    out["wall_seconds"] = round(time.time() - t0, 1)
    persist()
    dest = os.path.join(REPO, "testing", "artifacts", run_id, ARTIFACT)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        print(f"copied to {dest}")
    except Exception as e:                     # noqa: BLE001
        print(f"could not copy to {dest}: {type(e).__name__}: {e}")

print(json.dumps({"summary": out.get("summary"), "error": out.get("error")}, indent=1))
