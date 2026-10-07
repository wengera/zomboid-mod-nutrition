"""Tests for tools/release_pack.py: the release check, the staging, the manifest and its diff."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import release_pack as rp  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16  # header only; the CR inside is binary, not text
MOD_INFO = ("name=Nutrition Revamp\nid=NutritionRevamp\ndescription=A test mod. Second sentence.\n"
            "modversion=1.0.0\nversionMin=42.20.4\n")
CORE = 'NR = {}\nNR.version = "1.0.0"\n'


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


@pytest.fixture
def mod(tmp_path):
    m = tmp_path / "NutritionRevamp"
    put(m / "42.20.4" / "mod.info", MOD_INFO)
    put(m / "42.20.4" / "media" / "sandbox-options.txt", "option NR.Nutrition { type = boolean }\n")
    put(m / "common" / "media" / "lua" / "shared" / "NR_Core.lua", CORE)
    put(m / "common" / "media" / "scripts" / "NR_Pass.txt", "module Base {\n}\n")
    put(m / "common" / "media" / "ui" / "NutritionRevamp" / "a.png", PNG)
    return m


def rules(findings, level="ERROR"):
    return {f.rule for f in findings if f.level == level}


def test_clean_fixture(mod):
    assert rules(rp.check(mod)) == set()


def test_one_mod_info(mod):
    put(mod / "common" / "mod.info", MOD_INFO)
    assert "one-mod-info" in rules(rp.check(mod))


def test_version_min_only(mod):
    info = mod / "42.20.4" / "mod.info"
    put(info, MOD_INFO + "versionMax=42.99\n")
    assert "version-min-only" in rules(rp.check(mod))
    put(info, MOD_INFO.replace("versionMin=42.20.4\n", ""))
    assert "version-min-only" in rules(rp.check(mod))


def test_no_require(mod):
    put(mod / "42.20.4" / "mod.info", MOD_INFO + "require=Other\n")
    assert "no-require" in rules(rp.check(mod))


def test_version_dir_contents(mod):
    put(mod / "42.20.4" / "media" / "lua" / "shared" / "X.lua", "x=1\n")
    assert "version-dir-contents" in rules(rp.check(mod))


def test_no_shadow(mod):
    put(mod / "42.20.4" / "media" / "lua" / "shared" / "NR_Core.lua", CORE)
    assert "no-shadow" in rules(rp.check(mod))


def test_no_vanilla_path(mod):
    vanilla = (ROOT / "data" / "vanilla-relative-paths.txt").read_text(encoding="utf-8").split("\n")[0]
    assert vanilla.startswith(("lua/", "scripts/"))
    put(mod / "common" / "media" / vanilla, "x=1\n")
    found = [f for f in rp.check(mod) if f.rule == "no-vanilla-path"]
    assert found and vanilla in found[0].detail


def test_vanilla_translate_path_allowed(mod):
    names = (ROOT / "data" / "vanilla-relative-paths.txt").read_text(encoding="utf-8").splitlines()
    vt = next(v for v in names if v.startswith("lua/shared/Translate/EN/"))
    put(mod / "common" / "media" / vt, "{}")
    assert "no-vanilla-path" not in rules(rp.check(mod))


def test_lf_no_bom(mod):
    put(mod / "common" / "media" / "lua" / "shared" / "A.lua", "a=1\r\n")
    put(mod / "common" / "media" / "lua" / "shared" / "B.lua", b"\xef\xbb\xbfb=1\n")
    details = " ".join(f.detail for f in rp.check(mod) if f.rule == "lf-no-bom")
    assert "A.lua" in details and "B.lua" in details


def test_png_is_not_text(mod):
    # the fixture PNG carries a CR byte and must not trip lf-no-bom
    assert "lf-no-bom" not in rules(rp.check(mod))


def test_version_agree(mod):
    put(mod / "common" / "media" / "lua" / "shared" / "NR_Core.lua", 'NR.version = "0.9.0"\n')
    assert "version-agree" in rules(rp.check(mod))


def test_version_agree_skips_without_core(mod):
    (mod / "common" / "media" / "lua" / "shared" / "NR_Core.lua").unlink()
    assert "version-agree" not in rules(rp.check(mod))


def test_png_binary(mod):
    put(mod / "common" / "media" / "ui" / "NutritionRevamp" / "b.png", b"not a png")
    assert "png-binary" in rules(rp.check(mod))


def test_mod_lint_carried(tmp_path):
    m = tmp_path / "Bad"
    put(m / "common" / "media" / "lua" / "shared" / "X.lua", "x=1\n")
    found = rp.check(m)
    assert "mod-info" in rules(found) or "version-dir" in rules(found)


def test_manifest_gate_hash(mod):
    script = mod / "common" / "media" / "scripts" / "NR_Pass.txt"
    put(script, "module Base {\r\n}\r\n")
    crlf = rp.manifest(mod)["common/media/scripts/NR_Pass.txt"]
    put(script, "module Base {\n}\n")
    lf = rp.manifest(mod)["common/media/scripts/NR_Pass.txt"]
    assert crlf["gate_sha256"] == lf["gate_sha256"]
    assert crlf["sha256"] != lf["sha256"]
    assert lf["sha256"] == hashlib.sha256(b"module Base {\n}\n").hexdigest()
    assert lf["bytes"] == 16
    assert "gate_sha256" not in rp.manifest(mod)["common/media/lua/shared/NR_Core.lua"]


def test_stage_layout(mod, tmp_path):
    out = tmp_path / "release"
    man = rp.stage(mod, out)
    item = out / "NutritionRevamp"
    ws = (item / "workshop.txt").read_text(encoding="utf-8").split("\n")
    assert "version=1" in ws and "title=Nutrition Revamp" in ws
    assert "tags=Build 42;Multiplayer;Realistic;Food" in ws and "visibility=public" in ws
    assert any(line.startswith("description=A test mod.") for line in ws)
    assert "id=" in ws
    staged = item / "Contents" / "mods" / "NutritionRevamp"
    assert (staged / "42.20.4" / "mod.info").is_file()
    disk = json.loads((item / "MANIFEST.json").read_text(encoding="utf-8"))
    assert disk == man
    assert not (item / "preview.png").exists()
    assert any(f.level == "WARN" and "256" in f.detail for f in rp.last_findings)


def test_stage_writes_lf(mod, tmp_path):
    # a CR the check would refuse never reaches the staged copy: stage refuses instead
    put(mod / "common" / "media" / "lua" / "shared" / "A.lua", "a=1\r\n")
    with pytest.raises(rp.ReleaseError):
        rp.stage(mod, tmp_path / "release")
    assert not (tmp_path / "release").exists()


def test_stage_preview_copied(mod, tmp_path):
    put(mod.parent / "preview.png", PNG)
    rp.stage(mod, tmp_path / "release")
    assert (tmp_path / "release" / "NutritionRevamp" / "preview.png").is_file()


def test_diff_server_event():
    old = {"a.lua": {"sha256": "1", "bytes": 1},
           "common/media/scripts/p.txt": {"sha256": "1", "gate_sha256": "g1", "bytes": 1},
           "gone": {"sha256": "1", "bytes": 1}}
    new = {"a.lua": {"sha256": "2", "bytes": 1},
           "common/media/scripts/p.txt": {"sha256": "2", "gate_sha256": "g2", "bytes": 1},
           "fresh": {"sha256": "1", "bytes": 1}}
    d = rp.diff(old, new)
    assert d["added"] == ["fresh"] and d["removed"] == ["gone"]
    assert d["changed"] == ["a.lua", "common/media/scripts/p.txt"]
    assert d["script_changed"] == ["common/media/scripts/p.txt"]
    # a CR-only edit moves sha256 but not the gate hash: not a server event
    new["common/media/scripts/p.txt"]["gate_sha256"] = "g1"
    assert rp.diff(old, new)["script_changed"] == []


def test_cli_check_and_stage(mod, tmp_path, capsys):
    assert rp.main(["check", str(mod)]) == 0
    assert "0 ERROR" in capsys.readouterr().out
    assert rp.main(["stage", str(mod), "--out", str(tmp_path / "r")]) == 0
    prev = tmp_path / "r" / "NutritionRevamp" / "MANIFEST.json"
    put(mod / "common" / "media" / "scripts" / "NR_Pass.txt", "module Base {\n item X\n}\n")
    capsys.readouterr()
    assert rp.main(["stage", str(mod), "--out", str(tmp_path / "r2"), "--previous", str(prev)]) == 0
    assert "SERVER EVENT: 1 script file(s) changed" in capsys.readouterr().out


def test_cli_check_fails_on_error(mod, capsys):
    put(mod / "42.20.4" / "mod.info", MOD_INFO + "require=X\n")
    assert rp.main(["check", str(mod)]) == 1
    assert "release: ERROR: no-require" in capsys.readouterr().out


def test_check_real_mod():
    errors = [f for f in rp.check(ROOT / "mod" / "NutritionRevamp") if f.level == "ERROR"]
    assert errors == []


def test_diff_added_or_removed_script_is_a_server_event():
    old = {"common/media/scripts/gone.txt": {"sha256": "1", "gate_sha256": "g1", "bytes": 1}}
    new = {"common/media/scripts/fresh.txt": {"sha256": "1", "gate_sha256": "g1", "bytes": 1},
           "x.lua": {"sha256": "1", "bytes": 1}}
    d = rp.diff(old, new)
    assert d["script_changed"] == ["common/media/scripts/fresh.txt", "common/media/scripts/gone.txt"]
