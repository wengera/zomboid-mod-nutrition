"""tools/jar_recheck.py (Plan 11a Task R): pointer parsing, the dump's line table, the verdicts, the report."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import claimslib as cl  # noqa: E402
import jar_recheck as jr  # noqa: E402

DUMP = """### Eat(Lzombie/inventory/InventoryItem;F)Z
      0  L5728  aload_0          
      1         aload_1          
      4         invokevirtual    zombie/characters/IsoGameCharacter.Eat
      7         ireturn          

### Eat(Lzombie/inventory/InventoryItem;FZ)Z
      0  L5740  aload_1          
     28  L5760  aload            4
     30         fload_2          
     78         fstore_2         
     79  L5764  return           
"""


def test_parse_a_span_pointer():
    p = jr.parse_jar("IsoGameCharacter.Eat @28-@78 L5753-L5757")
    assert (p["cls"], p["meth"], p["desc"], p["spans"], p["lines"]) == (
        "IsoGameCharacter", "Eat", None, [(28, 78, 5753, 5757)], None)


def test_parse_the_other_forms():
    assert jr.parse_jar("Food.getBaseHunger()F @0 L1891")["desc"] == "()F"
    assert jr.parse_jar("Food.update @38\u2013@46 L369-370")["spans"] == [(38, 46, 369, 370)]
    assert jr.parse_jar("Food.getHungerChange()F @L1682-L1708")["lines"] == (1682, 1708)
    assert jr.parse_jar("IsoGameCharacter$XP.AddXP @0 L14183")["cls"] == "IsoGameCharacter$XP"
    assert jr.parse_jar("zombie/characters/Stats method list (34 entries)") is None
    assert jr.parse_jar("SandboxOptions.set(String,Object)") is None


def test_the_dump_carries_lines_forward_per_overload():
    ov = jr.parse_dump(DUMP)
    assert [d for d, _o, _i in ov] == ["(Lzombie/inventory/InventoryItem;F)Z",
                                       "(Lzombie/inventory/InventoryItem;FZ)Z"]
    offs = ov[1][1]
    assert offs[28] == 5760 and offs[30] == 5760 and offs[78] == 5760 and offs[79] == 5764
    assert ov[1][2][28].startswith("28  L5760  aload")


def test_descriptor_matching():
    assert jr.desc_matches(None, "(F)Z")
    assert jr.desc_matches("(Lzombie/inventory/InventoryItem;F)", "(Lzombie/inventory/InventoryItem;F)Z")
    assert jr.desc_matches("(InventoryItem,float)Z", "(Lzombie/inventory/InventoryItem;F)Z")
    assert not jr.desc_matches("(InventoryItem,float)Z", "(Lzombie/inventory/InventoryItem;FZ)Z")
    assert jr.simple_params("([ILjava/lang/String;J)V") == ["int[]", "String", "long"]


def test_the_verdicts():
    ov = jr.parse_dump(DUMP)
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat @28-@78 L5760"), ov) == ("same", None)
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat @28-@79 L5753-L5757"), ov) == (
        "shifted", "IsoGameCharacter.Eat @28-@79 L5760-L5764")
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat @29 L5760"), ov)[0] == "offsets-missing"
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat(I)Z @0 L5728"), ov)[0] == "no-method"
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat(InventoryItem,float)Z @0 L5728"), ov) == ("same", None)
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat @L5740-L5764"), ov) == ("same", None)
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat @L5741-L5764"), ov)[0] == "lines-missing"
    assert jr.check_jar(jr.parse_jar("IsoGameCharacter.Eat @0 L1"), jr.parse_dump("method not found: Eat"))[0] == "no-method"


def test_a_lua_anchor_same_moved_missing(tmp_path):
    d = tmp_path / "lua" / "client"
    d.mkdir(parents=True)
    (d / "A.lua").write_text("x = 1\nif not isClient() then\nend\n", encoding="utf-8")
    m = str(tmp_path)
    assert jr.check_lua('lua/client/A.lua:2 "if not isClient() then"', m) == ("same", None)
    assert jr.check_lua('lua/client/A.lua:1 "if not isClient() then"', m) == (
        "anchor-moved", 'lua/client/A.lua:2 "if not isClient() then"')
    assert jr.check_lua('lua/client/A.lua:1 "gone()"', m) == ("anchor-missing", None)
    assert jr.check_lua('lua/client/B.lua:1 "x"', m) == ("no-file", None)


def test_main_writes_one_line_per_pointer(tmp_path, monkeypatch, capsys):
    base = dict.fromkeys(cl.COLUMNS, "x")
    a = dict(base, id="#0001", pointer='jar:IsoGameCharacter.Eat @28-@79 L5753-L5757; lua:lua/client/A.lua:2 "y = 2"')
    b = dict(base, id="#0002", pointer="jar:Nope.x @0 L1")
    reg = tmp_path / "claims.tsv"
    cl.write_register(str(reg), [a, b])
    (tmp_path / "ids.txt").write_text("#0001\tcited by Task 14\n#0002\n#0001\n", encoding="utf-8")
    lua = tmp_path / "media" / "lua" / "client"
    lua.mkdir(parents=True)
    (lua / "A.lua").write_text("y = 2\n", encoding="utf-8")
    monkeypatch.setattr(jr, "class_index", lambda jar: {"IsoGameCharacter": ["zombie/characters/IsoGameCharacter"]})
    monkeypatch.setattr(jr, "dump_text", lambda c, m, jar, pzdis: DUMP)
    out = tmp_path / "report.tsv"
    assert jr.main(["--ids", str(tmp_path / "ids.txt"), "--out", str(out), "--register", str(reg),
                    "--media", str(tmp_path / "media")]) == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == list(jr.HEADER)
    assert [l.split("\t")[:5] for l in lines[1:]] == [
        ["#0001", "jar", "IsoGameCharacter.Eat @28-@79 L5753-L5757", "shifted", "IsoGameCharacter.Eat @28-@79 L5760-L5764"],
        ["#0001", "lua", 'lua/client/A.lua:2 "y = 2"', "anchor-moved", 'lua/client/A.lua:1 "y = 2"'],
        ["#0002", "jar", "Nope.x @0 L1", "no-class", ""]]
    assert "3 pointers over 2 ids" in capsys.readouterr().out
