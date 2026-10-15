"""The 10 restated body trait blocks (Plan 13 Task 16; spec section 3.1; rulings 13-25 and 13-46).

`NR_Traits_Body.txt` restates vanilla's ten character_trait_definition blocks: the costs of the four weight traits
change, the band traits are no longer profession traits, the four muscle blocks keep vanilla's Strength XPBoosts
(Plan 13 Task 17 fix 1) and the four weight blocks carry none, Weight Gain and Weight Loss no longer grant a trait, the exclusions grow, and UIDescription points at the mod's key. Every other vanilla key is
compared against VANILLA, a frozen copy of the ten blocks read once from the 42.21 install
(scripts/generated/characters/character_traits.txt).
"""
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPT = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "scripts", "NR_Traits_Body.txt")
UI = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "Translate", "EN", "UI.json")

IDS = ["weak", "feeble", "stout", "strong", "obese", "overweight", "underweight", "very underweight", "weightgain",
       "weightloss"]
BODY = IDS[:8]
COST = {"weak": -10, "feeble": -6, "stout": 6, "strong": 10, "obese": -10, "overweight": -6, "underweight": -6,
        "very underweight": -10, "weightgain": -2, "weightloss": -2}
CHANGED = {"IsProfessionTrait", "Cost", "XPBoosts", "GrantedTraits", "MutuallyExclusiveTraits", "UIDescription"}
WEIGHT_GAIN = {"weightloss", "underweight", "very underweight", "emaciated", "athletic", "fit"}
WEIGHT_LOSS = {"weightgain", "overweight", "obese", "very underweight"}
KERNEL = {"WEAK": "weak", "FEEBLE": "feeble", "UNDERWEIGHT": "underweight", "VERY_UNDERWEIGHT": "very underweight"}

VANILLA = '''
    character_trait_definition base:weak
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = base:weak,
        Cost = -10,
        UIName = UI_trait_weak,
        UIDescription = UI_trait_weakdesc,
        MutuallyExclusiveTraits = base:feeble;base:stout;base:strong,
        XPBoosts = Strength=-5,
    }

    character_trait_definition base:feeble
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = base:feeble,
        Cost = -6,
        UIName = UI_trait_feeble,
        UIDescription = UI_trait_feebledesc,
        XPBoosts = Strength=-2,
        MutuallyExclusiveTraits = base:stout;base:strong;base:weak,
    }

    character_trait_definition base:stout
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = base:stout,
        Cost = 6,
        UIName = UI_trait_stout,
        UIDescription = UI_trait_stoutdesc,
        MutuallyExclusiveTraits = base:feeble;base:strong;base:weak,
        XPBoosts = Strength=2,
    }

    character_trait_definition base:strong
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = base:strong,
        Cost = 10,
        UIName = UI_trait_strong,
        UIDescription = UI_trait_strongdesc,
        MutuallyExclusiveTraits = base:feeble;base:stout;base:weak,
        XPBoosts = Strength=4,
    }

    character_trait_definition base:obese
    {
        IsProfessionTrait = true,
        DisabledInMultiplayer = false,
        CharacterTrait = base:obese,
        Cost = 0,
        UIName = UI_trait_obese,
        UIDescription = UI_trait_obesedesc,
        MutuallyExclusiveTraits = base:athletic;base:emaciated;base:fit;base:lighteater;base:very underweight;base:underweight;base:overweight,
        XPBoosts = Fitness=-2,
    }

    character_trait_definition base:overweight
    {
        IsProfessionTrait = true,
        DisabledInMultiplayer = false,
        CharacterTrait = base:overweight,
        Cost = 0,
        UIName = UI_trait_overweight,
        UIDescription = UI_trait_overweightdesc,
        MutuallyExclusiveTraits = base:athletic;base:fit;base:emaciated;base:very underweight;base:underweight,
        XPBoosts = Fitness=-1,
    }

    character_trait_definition base:underweight
    {
        IsProfessionTrait = true,
        DisabledInMultiplayer = false,
        CharacterTrait = base:underweight,
        Cost = 0,
        UIName = UI_trait_underweight,
        UIDescription = UI_trait_underweightdesc,
        MutuallyExclusiveTraits = base:obese;base:very underweight;base:overweight,
        XPBoosts = Fitness=-1,
    }

    character_trait_definition base:very underweight
    {
        IsProfessionTrait = true,
        DisabledInMultiplayer = false,
        CharacterTrait = base:very underweight,
        Cost = 0,
        UIName = UI_trait_veryunderweight,
        UIDescription = UI_trait_veryunderweightdesc,
        MutuallyExclusiveTraits = base:athletic;base:obese;base:overweight;base:heartyappetite;base:underweight,
        XPBoosts = Fitness=-2,
    }

    character_trait_definition base:weightgain
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = base:weightgain,
        Cost = -2,
        UIName = UI_trait_weightgain,
        UIDescription = UI_trait_weightgaindesc,
        MutuallyExclusiveTraits = base:weightloss,
        GrantedTraits = base:overweight,
    }

    character_trait_definition base:weightloss
    {
        IsProfessionTrait = false,
        DisabledInMultiplayer = false,
        CharacterTrait = base:weightloss,
        Cost = -2,
        UIName = UI_trait_weightloss,
        UIDescription = UI_trait_weightlossdesc,
        MutuallyExclusiveTraits = base:weightgain,
        GrantedTraits = base:underweight,
    }
'''


def parse(text):
    """{id: {key: value}} of the character_trait_definition blocks, the id as the block names it (without base:)."""
    out = {}
    for m in re.finditer(r"character_trait_definition base:([a-z ]+)\s*\{(.*?)\n\s*\}", text, re.S):
        keys = {}
        for line in m.group(2).strip().split("\n"):
            k, v = line.strip().rstrip(",").split(" = ", 1)
            assert k not in keys, "duplicate key " + k
            keys[k] = v
        assert m.group(1) not in out
        out[m.group(1)] = keys
    return out


def excl(block):
    return {t[len("base:"):] for t in block["MutuallyExclusiveTraits"].split(";")}


@pytest.fixture(scope="module")
def mine():
    with open(SCRIPT, "rb") as f:
        raw = f.read()
    assert 13 not in raw
    return parse(raw.decode("utf-8"))


@pytest.fixture(scope="module")
def vanilla():
    return parse(VANILLA)


def test_the_ten_ids(mine, vanilla):
    assert sorted(mine) == sorted(IDS)
    assert sorted(vanilla) == sorted(IDS)
    assert len(re.findall(r"^    character_trait_definition ", open(SCRIPT, encoding="utf-8").read(), re.M)) == 10


@pytest.mark.parametrize("i", IDS)
def test_cost_and_profession(mine, i):
    assert mine[i]["Cost"] == str(COST[i])
    assert mine[i]["IsProfessionTrait"] == "false"
    assert mine[i]["CharacterTrait"] == "base:" + i


@pytest.mark.parametrize("i", BODY[:4])
def test_the_muscle_blocks_keep_vanillas_strength_boost(mine, vanilla, i):
    # Plan 13 Task 17 fix 1: applyTraits climbs Strength to the picked band, so the handler can infer the pick
    assert vanilla[i]["XPBoosts"].startswith("Strength=")
    assert mine[i]["XPBoosts"] == vanilla[i]["XPBoosts"]


@pytest.mark.parametrize("i", BODY[4:])
def test_no_xp_boosts_in_a_weight_block(mine, i):
    assert "XPBoosts" not in mine[i]


@pytest.mark.parametrize("i", ["weightgain", "weightloss"])
def test_the_weight_tendencies_grant_nothing(mine, i):
    assert "GrantedTraits" not in mine[i]
    assert "XPBoosts" not in mine[i]


@pytest.mark.parametrize("i", IDS)
def test_exclusions_keep_vanillas_and_stay_two_way(mine, vanilla, i):
    assert excl(vanilla[i]) <= excl(mine[i])
    for other in excl(mine[i]) & set(IDS):
        assert i in excl(mine[other]), "%s excludes %s, not back" % (i, other)


def test_the_family_exclusions(mine):
    fat, thin, muscle = {"obese", "overweight"}, {"underweight", "very underweight"}, {"weak", "feeble", "stout", "strong"}
    for fam in (fat, thin, muscle):
        for i in fam:
            assert fam - {i} <= excl(mine[i]), i
    # the body weight picks exclude each other across the fat and thin families
    for a in fat:
        for b in thin:
            assert b in excl(mine[a]) and a in excl(mine[b])
    # the exclusions Weight Gain and Weight Loss inherited through their removed grants (fix round 1, ruling I2)
    assert excl(mine["weightgain"]) == WEIGHT_GAIN
    assert excl(mine["weightloss"]) == WEIGHT_LOSS


def test_every_restated_pair_is_two_way(mine):
    for i in IDS:
        for other in excl(mine[i]) & set(IDS):
            assert i in excl(mine[other]), "%s excludes %s, not back" % (i, other)
    # Emaciated, Athletic and Fit are not restated: those pairs sit on Weight Gain alone (server validation is two-way)
    assert {"emaciated", "athletic", "fit"} <= excl(mine["weightgain"])
    for t in WEIGHT_GAIN & set(IDS):
        assert "weightgain" in excl(mine[t])
    for t in WEIGHT_LOSS & set(IDS):
        assert "weightloss" in excl(mine[t])


def test_description_numbers_are_the_kernels(host):
    import json
    with open(UI, encoding="utf-8") as f:
        ui = json.load(f)
    start = host.py(host.K.strength.DEFAULTS.startLevel)
    for i, key in (("weak", "WEAK"), ("feeble", "FEEBLE"), ("stout", "STOUT"), ("strong", "STRONG")):
        got = re.findall(r"Strength (\d+)", ui["UI_NR_trait_%sdesc" % i])
        assert got == [str(int(start[key]))], i
    fmi = host.py(host.K.body.FAT_FMI)
    kg = round((fmi["OBESE"] - fmi["none"]) * host.K.HEIGHT_M ** 2)
    assert re.findall(r"about (\d+) kg", ui["UI_NR_trait_obesedesc"]) == [str(kg)]
    assert "kg" not in ui["UI_NR_trait_overweightdesc"]


def test_ruling_13_46_pairs_in_both_directions(mine):
    for m in ("weak", "feeble"):
        for t in ("underweight", "very underweight"):
            assert t in excl(mine[m]) and m in excl(mine[t])


def test_the_script_pairs_equal_the_kernels_excludes(mine, host):
    kernel = set()
    for w, row in host.py(host.K.body.EXCLUDES).items():
        for m, on in row.items():
            assert on is True
            kernel.add(frozenset((KERNEL[m], KERNEL[w])))
    # the script's pairs between the muscle picks (weak, feeble) and the thin picks, undirected
    script = {frozenset((a, b)) for a in ("weak", "feeble") for b in ("underweight", "very underweight")
              if b in excl(mine[a]) or a in excl(mine[b])}
    assert script == kernel
    # and nothing else crosses the muscle and thin families in the script
    cross = {frozenset((a, b)) for a in BODY[:4] for b in ("underweight", "very underweight")
             if b in excl(mine[a]) or a in excl(mine[b])}
    assert cross == kernel


@pytest.mark.parametrize("i", IDS)
def test_every_other_vanilla_key_is_kept_verbatim(mine, vanilla, i):
    for k, v in vanilla[i].items():
        if k not in CHANGED:
            assert mine[i][k] == v, (i, k)
    assert set(mine[i]) - set(vanilla[i]) == set()
    assert "Texture" not in mine[i]
    assert mine[i]["UIDescription"] == "UI_NR_trait_%sdesc" % i.replace(" ", "")


def test_the_description_keys_are_defined(mine):
    import json
    with open(UI, encoding="utf-8") as f:
        ui = json.load(f)
    for i in IDS:
        assert ui[mine[i]["UIDescription"]].strip()
