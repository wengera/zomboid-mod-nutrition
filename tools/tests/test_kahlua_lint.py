import os, sys, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import kahlua_lint as kl


def lint_text(tmp_path, text, name="X.lua"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return [(f.line, f.rule) for f in kl.lint([str(p)])]


def test_goto_and_labels_are_findings(tmp_path):
    out = lint_text(tmp_path, """
        local x = 1
        goto done
        ::done::
    """)
    assert out == [(3, "goto"), (4, "goto")]


def test_percent_d_in_format_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        local s = string.format("%d items", n)
        local t = string.format("%.0f items", n)
    """)
    assert out == [(2, "format-d")]


def test_length_of_a_call_result_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        local n = #players:getItems()
        local m = #getOnlinePlayers()
        local k = #list
    """)
    assert out == [(2, "java-length"), (3, "java-length")]


def test_pairs_over_a_call_result_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        for k, v in pairs(p:getModData()) do end
        for k, v in pairs(t) do end
    """)
    assert out == [(2, "java-pairs")]


def test_words_inside_comments_and_strings_do_not_fire(tmp_path):
    out = lint_text(tmp_path, """
        -- goto is not in Kahlua; string.format("%d") raises
        local s = "goto ::x:: %d"
        local long = [[
          goto
        ]]
    """)
    assert out == []


def test_loadstring_is_a_finding(tmp_path):
    assert lint_text(tmp_path, 'local f = loadstring("return 1")\n') == [(1, "loadstring")]


def test_directories_are_walked_and_only_lua_files_read(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "ok.lua").write_text("local x = 1\n", encoding="utf-8")
    (tmp_path / "a" / "bad.lua").write_text("goto x\n", encoding="utf-8")
    (tmp_path / "a" / "note.txt").write_text("goto x\n", encoding="utf-8")
    found = kl.lint([str(tmp_path / "a")])
    assert [os.path.basename(f.path) for f in found] == ["bad.lua"]


def test_cli_exit_code_and_count_line(tmp_path, capsys):
    p = tmp_path / "x.lua"
    p.write_text("goto x\n", encoding="utf-8")
    assert kl.main([str(p)]) == 1
    assert capsys.readouterr().out.strip().splitlines()[-1] == "1 findings"
    p.write_text("local x = 1\n", encoding="utf-8")
    assert kl.main([str(p)]) == 0
