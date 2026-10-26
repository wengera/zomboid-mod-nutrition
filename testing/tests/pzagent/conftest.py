"""The lupa host for PZAgent's Lua: Python stubs stand in for the Java globals (ruling P21-3)."""
import os
import sys
import pytest
from lupa import LuaRuntime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "testing"))
LUA = os.path.join(ROOT, "testing", "PZAgent", "PZAgent", "42", "media", "lua")


def lua_file(name):
    return os.path.join(LUA, name)


class FakeFS:
    """getFileWriter/getFileReader over a dict; append honoured when self.append_works."""
    def __init__(self):
        self.files = {}
        self.append_works = True
        self.opens = 0
        self.fail_next = False

    def writer(self, name, create, append):
        self.opens += 1
        if self.fail_next:
            self.fail_next = False
            return None
        fs = self
        if not (append and fs.append_works):
            fs.files[name] = ""
        class W:
            def write(self, s): fs.files[name] = fs.files.get(name, "") + s
            def close(self): pass
        return W()

    def reader(self, name, create):
        if name not in self.files:
            return None
        lines = iter(self.files[name].split("\n"))
        class R:
            def readLine(self):
                try:
                    return next(lines)
                except StopIteration:
                    return None
            def close(self): pass
        return R()


@pytest.fixture
def fs():
    return FakeFS()


@pytest.fixture
def lua(fs):
    L = LuaRuntime(unpack_returned_tuples=True)
    g = L.globals()
    g.getFileWriter = fs.writer
    g.getFileReader = fs.reader
    clock = {"ms": 1000}
    g.getTimestampMs = lambda: clock["ms"]
    g._clock = clock
    g.print = lambda *a: None
    L.execute(open(lua_file("shared/PZAgent_Core.lua"), encoding="utf-8").read())
    return L
