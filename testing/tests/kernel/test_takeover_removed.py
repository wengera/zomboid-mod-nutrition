"""The takeover is gone (Plan 11 Task 14; Decision 1 (c)): no file registers the per-tick stat hook, the takeover's
adapter and kernel are deleted, and the hunger target lives in the writer's kernel (K.hybrid).
"""
import glob
import os
from .server_host import LUA


def test_the_takeover_files_are_gone():
    assert not os.path.exists(os.path.join(LUA, "server", "NR_Server_Fast.lua"))
    assert not os.path.exists(os.path.join(LUA, "shared", "NR_Kernel_Fast.lua"))


def test_no_mod_file_registers_the_stat_hook():
    hits = [os.path.basename(p) for p in glob.glob(os.path.join(LUA, "**", "*.lua"), recursive=True)
            if "CalculateStats.Add" in open(p, encoding="utf-8").read()]
    assert hits == []


def test_the_hunger_target_lives_in_the_writer_kernel(host):
    assert host.K.fast is None
    assert host.call("hybrid.hungerTarget", 1.0, 1.0) == 0
