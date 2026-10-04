"""The 100 % kernel line-coverage gate (spec § 4.10 tier 2). Runs last in this directory."""


def test_every_kernel_line_executed(host):
    active, executed = host.active(), host.executed()
    missing = {}
    for src, lines in active.items():
        if not src.startswith("@NR_Kernel"):
            continue                       # NR_Core.lua is the runtime's, not the kernel's
        gap = sorted(lines - executed.get(src, set()))
        if gap:
            missing[src] = gap
    assert not missing, f"kernel lines never executed by a test: {missing}"
    assert any(src.startswith("@NR_Kernel") for src in active), "no kernel file was loaded"
