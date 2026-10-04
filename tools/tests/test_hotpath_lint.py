import os, sys, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import hotpath_lint as hl


def lint_text(tmp_path, text, name="NR_Server_Fast.lua"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return [(f.line, f.rule) for f in hl.lint([str(p)])]


REGION = """
    -- @hoisted stats, K
    local function tick(h, p)
        -- @fastpath
        local v = h.stats:get(h.HUNGER)
        local d = K.hunger_delta(p.in, p.out)
        h.stats:set(h.HUNGER, v + d)
        -- @endfastpath
    end
"""


def test_a_clean_region_has_no_findings(tmp_path):
    assert lint_text(tmp_path, REGION) == []


def test_each_forbidden_shape_is_named(tmp_path):
    out = lint_text(tmp_path, """
        -- @hoisted h
        -- @fastpath
        local t = { a = 1 }
        local s = "a" .. "b"
        local ok = pcall(f)
        local u = tostring(x)
        local w = string.format("%f", x)
        local e = math.exp(x)
        local q = x ^ 2
        for i = 1, 3 do end
        local z = p:getStats()
        -- @endfastpath
    """)
    assert out == [(4, "alloc"), (5, "concat"), (6, "pcall"), (7, "string"), (8, "string"),
                   (9, "math"), (10, "math"), (11, "loop"), (12, "unhoisted-call")]


def test_rimguard_allows_exactly_one_pcall(tmp_path):
    out = lint_text(tmp_path, """
        -- @fastpath
        local ok = pcall(body, h, p)   -- @rimguard
        local ok2 = pcall(body, h, p)  -- @rimguard
        -- @endfastpath
    """)
    assert out == [(4, "pcall")]


def test_code_outside_a_region_is_free(tmp_path):
    assert lint_text(tmp_path, 'local t = { a = "x" .. "y" }\nlocal ok = pcall(f)\n') == []


def test_unterminated_region_is_a_finding(tmp_path):
    assert lint_text(tmp_path, "-- @fastpath\nlocal x = 1\n") == [(1, "region")]


def test_kernel_files_allow_only_kernel_fields(tmp_path):
    out = lint_text(tmp_path, """
        local K = NutritionRevamp.kernel
        K.fast = K.fast or {}
        function K.fast.hunger(p) return p.x end
        local function helper() return 1 end
        function other() return 2 end
        K.fast.cb = function() return 3 end
    """, name="NR_Kernel_Fast.lua")
    assert out == [(5, "kernel-shape"), (6, "kernel-shape"), (7, "kernel-shape")]


def test_kernel_files_may_not_name_java_globals(tmp_path):
    out = lint_text(tmp_path, """
        local K = NutritionRevamp.kernel
        function K.bad(p) return getPlayer() end
        function K.bad2(p) return SandboxVars.NR.Mode end
        function K.ok(p) return p.mode end
    """, name="NR_Kernel_X.lua")
    assert out == [(3, "kernel-java"), (4, "kernel-java")]
