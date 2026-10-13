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


def test_percent_g_in_format_is_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        local s = string.format("%.17g", v)
        local t = pcall(string.format, "%G", v)
        local u = string.format("%-8.3g|", v)
    """)
    assert out == [(2, "format-g"), (3, "format-g"), (4, "format-g")]


def test_percent_g_with_the_allow_pragma_is_not_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        local ok, s = pcall(string.format, "%.17g", v) -- kahlua-lint: allow-g
    """)
    assert out == []


def test_percent_d_s_e_f_are_not_format_g(tmp_path):
    out = lint_text(tmp_path, """
        local a = string.format("%s %.3f %e %5.2E", n, v, v, v)
        local b = string.format("%.0f", v)
    """)
    assert out == []


def test_percent_g_in_a_comment_or_without_format_is_not_a_finding(tmp_path):
    out = lint_text(tmp_path, """
        -- string.format("%g", v) hangs on Kahlua
        local s = "%g"
    """)
    assert out == []


def test_format_g_and_d_ignore_modulo_percent_and_double_percent(tmp_path):
    out = lint_text(tmp_path, """
        local a = string.format("%.1f", x % gap)
        local b = string.format("100%%gain %s", x)
        local c = string.format("100%%dogs %s", x)
    """)
    assert out == []


def test_format_g_and_d_catch_the_method_form(tmp_path):
    out = lint_text(tmp_path, """
        local a = ("%g"):format(v)
        local b = ("%d"):format(v)
    """)
    assert out == [(2, "format-g"), (3, "format-d")]
