"""Which `mod.info` a mod folder resolves to -- and that the two readers of that question agree.

`pzt.mods.mod_id_of` (what a profile places) and `tools/mod_lint.py`'s `info_chain` (what the
lint reports) both answer "which file does B42 read here?". They disagreed until slice 07's
final fix wave: `mod_id_of` string-sorted its `42*/mod.info` glob, so `42/mod.info` beat
`42.20/mod.info` (the path separator sorts above `.`) and `42.9` beat `42.20`. It read a
different file on 6 of the 230 installed mods; all 6 declare the same id in both, so nothing
ever resolved wrongly -- which is luck, and this file is what replaces it.

The import only ever points this way: a test may read `tools/`, but `tools/` never imports
`testing/pzt` (`docs/decisions.md`, 2026-09-10, slice 07).
"""
import glob, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import pytest
import mod_lint
from pzt import mods
from pzt.paths import WORKSHOP_DIR


def _mod(root, name, infos, extra=()):
    """Build `root/name` with {relative mod.info path: id} plus any empty extra folders."""
    d = os.path.join(root, name)
    for rel, mod_id in infos.items():
        p = os.path.join(d, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("name=%s\nid=%s\n" % (name, mod_id))
    for rel in extra:
        os.makedirs(os.path.join(d, *rel.split("/")), exist_ok=True)
    return d


def _lint_choice(mod_dir):
    """The file `mod_lint` says the running build reads, as a relative path."""
    chain = mod_lint.info_chain(mod_lint.version_dirs(mod_dir))
    return next((c for c in chain if os.path.exists(os.path.join(mod_dir, *c.split("/")))), None)


# ---- mod_id_of: the tuple sort ------------------------------------------------------------

def test_version_folders_sort_by_parsed_tuple_not_by_string():
    """Three-part versions are real (`42.20.1`, Skill Recovery Journal 2503622437), 42.20
    outranks 42.9, and a bare `42/` is the OLDEST of them -- the opposite of what a string
    sort of the globbed paths gives."""
    with tempfile.TemporaryDirectory() as d:
        m = _mod(d, "MyMod", {"42/mod.info": "from_42", "42.9/mod.info": "from_42_9",
                              "42.20/mod.info": "from_42_20", "42.20.1/mod.info": "from_42_20_1"})
        assert mods.mod_id_of(m) == "from_42_20_1"


def test_the_shape_the_six_corpus_mods_ship():
    """`42/` beside `42.20/`, which is exactly P4TidyUpMeister / SimpleStatus / KWRR_Security /
    CleanHotBar / Neat_Crafting / HereGoesTheSun. The old string sort read `42/mod.info`."""
    with tempfile.TemporaryDirectory() as d:
        m = _mod(d, "SimpleStatus", {"42/mod.info": "stale", "42.20/mod.info": "simpleStatus"})
        assert mods.mod_id_of(m) == "simpleStatus"


def test_common_then_root_are_still_the_fallbacks():
    with tempfile.TemporaryDirectory() as d:
        m = _mod(d, "A", {"common/mod.info": "from_common", "mod.info": "from_root"})
        assert mods.mod_id_of(m) == "from_common"
        m2 = _mod(d, "B", {"mod.info": "from_root"})
        assert mods.mod_id_of(m2) == "from_root"
        assert mods.mod_id_of(os.path.join(d, "nothing-here")) is None


def test_a_version_folder_wins_over_common_and_root():
    with tempfile.TemporaryDirectory() as d:
        m = _mod(d, "A", {"42.20/mod.info": "from_version", "common/mod.info": "from_common",
                          "mod.info": "from_root"})
        assert mods.mod_id_of(m) == "from_version"


def test_a_folder_the_glob_catches_but_no_version_ranks_last():
    """`42*` is wider than `^42(\\.\\d+){0,2}$`: `42-old/` is a candidate, but the last one --
    dropping it silently would be worse than ranking it below every real version."""
    with tempfile.TemporaryDirectory() as d:
        m = _mod(d, "A", {"42-old/mod.info": "from_junk", "42/mod.info": "from_42"})
        assert mods.mod_id_of(m) == "from_42"
        m2 = _mod(d, "B", {"42-old/mod.info": "from_junk"})
        assert mods.mod_id_of(m2) == "from_junk"


# ---- the agreement itself (B7) --------------------------------------------------------------

def test_mod_id_of_reads_the_file_mod_lint_names():
    """The synthetic tree the brief asks for: `42`, `42.9`, `42.20`, `42.20.1`, each declaring
    a different id, so WHICH file was opened is observable in the answer."""
    with tempfile.TemporaryDirectory() as d:
        infos = {"42/mod.info": "from_42", "42.9/mod.info": "from_42_9",
                 "42.20/mod.info": "from_42_20", "42.20.1/mod.info": "from_42_20_1"}
        m = _mod(d, "MyMod", infos)
        chosen = _lint_choice(m)
        assert chosen == "42.20.1/mod.info"
        assert mods.mod_id_of(m) == infos[chosen]


@pytest.mark.parametrize("infos", [
    {"42/mod.info": "a", "42.20/mod.info": "b"},                       # the corpus six
    {"42.9/mod.info": "a", "42.20/mod.info": "b"},                     # 9 vs 20
    {"42.20/mod.info": "a", "42.20.1/mod.info": "b"},                  # three-part
    {"42/mod.info": "a", "common/mod.info": "b", "mod.info": "c"},     # SD_CC_TEST's shape
    {"common/mod.info": "b", "mod.info": "c"},                         # no version folder
    {"mod.info": "c"},                                                 # b41-flat
])
def test_the_two_readers_agree_on_every_layout_in_the_corpus(infos):
    with tempfile.TemporaryDirectory() as d:
        m = _mod(d, "MyMod", infos)
        assert mods.mod_id_of(m) == infos[_lint_choice(m)]


@pytest.mark.skipif(not os.path.isdir(WORKSHOP_DIR), reason="Steam workshop root not on this machine")
def test_the_two_readers_agree_on_the_installed_corpus():
    """The live check behind the synthetic ones. 230 folders today; the six that used to
    disagree are the point, and a new one appearing is a finding, not a flake."""
    disagree = []
    for m in sorted(glob.glob(os.path.join(WORKSHOP_DIR, "*", "mods", "*"))):
        if not os.path.isdir(m):
            continue
        chosen = _lint_choice(m)
        if chosen is None:
            continue                     # no mod.info anywhere (3782784855): both read None
        want = mod_lint.read_info(os.path.join(m, *chosen.split("/"))).get("id") or None
        if mods.mod_id_of(m) != want:
            disagree.append((mod_lint.display_name(m), chosen))
    assert disagree == []
