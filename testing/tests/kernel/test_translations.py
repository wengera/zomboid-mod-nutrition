"""The interface text (Plan 7 Task 9): UI.json, IG_UI.json and Moodles.json under the mod's NR_ prefix.

(a) every literal UI_NR_ / IGUI_NR_ / Moodles_NR_ key a client file names is a key of the matching JSON, a literal
followed by `..` being a prefix of a constructed key and so left to (b); (b) the constructed keys, generated here by
the rules of NR_Kernel_View.lua and NR_Client_Moodles.lua, are all in UI.json (and the moodle titles in Moodles.json);
(c) each file parses to a flat string-to-string object, LF, with no duplicate key; (d) no key redefines a key of the
vanilla EN file of the same name (ruling 12), skipped when the install is absent.
"""
import glob
import json
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
EN = os.path.join(LUA, "shared", "Translate", "EN")
CLIENT = os.path.join(LUA, "client")
VANILLA = os.path.join("D:\\", "SteamLibrary", "steamapps", "common", "ProjectZomboid", "media", "lua", "shared",
                       "Translate", "EN")
FILES = ["UI.json", "IG_UI.json", "Moodles.json"]
CLASSES = ["energy", "hydration", "deficiency", "excess", "stimulant", "sleep"]


def _pairs(pairs):
    d = {}
    for k, v in pairs:
        assert k not in d, "duplicate key " + k
        d[k] = v
    return d


def load(name):
    with open(os.path.join(EN, name), "rb") as f:
        raw = f.read()
    assert b"\r" not in raw, name + " has CR"
    assert not raw.startswith(b"\xef\xbb\xbf"), name + " has a BOM"
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def order_keys():
    src = read(os.path.join(LUA, "shared", "NR_Data_Records.lua"))
    block = re.search(r"ORDER\s*=\s*\{(.*?)\}", src, re.S).group(1)
    keys = re.findall(r'"([A-Za-z0-9]+)"', block)
    assert len(keys) == 27
    return keys


def vector_keys():
    src = read(os.path.join(LUA, "shared", "NR_Kernel_Vector.lua"))
    block = re.search(r"K\.vector\.KEYS\s*=\s*\{(.*?)\}", src, re.S).group(1)
    keys = re.findall(r'"([A-Za-z0-9]+)"', block)
    assert len(keys) == 31
    return keys


def bands():
    src = read(os.path.join(LUA, "shared", "NR_Kernel_Body.lua"))
    b = set(re.findall(r'return "([A-Za-z]+)"\s*-- #0531', src))
    assert len(b) >= 5
    return sorted(b)


def constructed():
    out = set()
    for c in CLASSES:
        out.add("UI_NR_Class_" + c)
        for n in range(5):
            out.add("UI_NR_Class_%s_%d" % (c, n))
    for k in order_keys():
        for suffix in ("", "_p", "_x"):
            out.add("UI_NR_Row_" + k + suffix)
    for k in vector_keys():
        out.add("UI_NR_Row_" + k)
    for k in ("body_band", "body_weight", "body_energyState", "body_fm", "body_lm", "fluids_dehydPct",
              "acute_caf", "acute_bac", "acute_debtH"):
        out.add("UI_NR_Row_" + k)
    for b in bands() + ["none"]:
        out.add("UI_NR_Band_" + b)
    for g in range(1, 5):
        out.add("UI_NR_Grade_%d" % g)
    out.add("UI_NR_Tip_Rich")
    out.add("UI_NR_Tip_Low")
    for s in ("declared", "table", "inferred", "missing"):
        out.add("UI_NR_Tip_Source_" + s)
    return out


def literals():
    found = []
    for p in sorted(glob.glob(os.path.join(CLIENT, "*.lua"))):
        src = read(p)
        for m in re.finditer(r'"((?:UI|IGUI|Moodles)_NR_[A-Za-z0-9_]*)"(\s*\.\.)?', src):
            found.append((os.path.basename(p), m.group(1), m.group(2) is not None))
    return found


def target(key):
    return {"UI_": "UI.json", "IGUI_": "IG_UI.json", "Moodles_": "Moodles.json"}[key.split("NR_")[0]]


def test_literal_client_keys_exist():
    data = {n: load(n) for n in FILES}
    lits = literals()
    assert len([1 for _, _, pre in lits if not pre]) >= 8
    for fname, key, prefix in lits:
        if prefix:
            continue
        assert key in data[target(key)], "%s names %s, missing from %s" % (fname, key, target(key))
    assert data["IG_UI.json"]["IGUI_NR_Loaded"] == "nr-loaded"


def test_constructed_keys_exist():
    ui = load("UI.json")
    moo = load("Moodles.json")
    assert sorted(constructed() - set(ui)) == []
    for c in CLASSES:
        for n in range(1, 5):
            assert "Moodles_NR_%s_lvl%d" % (c, n) in moo
    assert len(moo) == 24
    # the client's own prefix concatenations are the ones constructed above
    assert any(pre and key == "Moodles_NR_" for _, key, pre in literals())
    assert any(pre and key == "UI_NR_Class_" for _, key, pre in literals())


@pytest.mark.parametrize("name", FILES)
def test_shape(name):
    d = load(name)
    assert isinstance(d, dict) and d
    prefix = {"UI.json": "UI_NR_", "IG_UI.json": "IGUI_NR_", "Moodles.json": "Moodles_NR_"}[name]
    for k, v in d.items():
        assert isinstance(k, str) and isinstance(v, str) and v != "", k
        assert k.startswith(prefix), k


@pytest.mark.parametrize("name", FILES)
def test_no_vanilla_key_redefined(name):
    p = os.path.join(VANILLA, name)
    if not os.path.isfile(p):
        pytest.skip("the vanilla install is absent")
    with open(p, encoding="utf-8") as f:
        vanilla = json.load(f)
    assert sorted(set(load(name)) & set(vanilla)) == []
