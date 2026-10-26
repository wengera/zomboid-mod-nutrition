# Plan 21: the agent harness feasibility exploration — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Measure whether a pure-Lua client mod (`PZAgent`) streaming state to files and a Python planner sending it goals can drive a Project Zomboid character through basic actions and a game day of survival, and write the feasibility report with the numbers.

**Architecture:** `PZAgent` (client Lua, no dependence on `PZTestKit`) appends JSON lines to `<client cache>/Lua/pzagent/<user>/state.log` at 5 Hz plus events, polls `cmd.txt` by sequence number, and runs one goal at a time as a per-tick state machine. Python (`testing/agent/`) tails the log into a world model, a behaviour tree picks goals, and three spike drivers (A pipe, B actions, C survival) each run as a build → offline tests → boot → measure → verdict loop with a pass budget and numeric gates. A fresh reviewer writes the report from the artifacts.

**Tech Stack:** Kahlua Lua (B42 client), `lupa==2.8` for offline Lua tests, Python 3 (`testing/pzt`, `testing/experiments/xlib.py`), pytest.

**Spec:** `docs/superpowers/specs/2026-10-26-agent-harness-design.md` (read it in full).

## Global Constraints

- CLAUDE.md §§ 3–6 bind every task: the gates, pathspec commits, no index-wide git, never `GIT_DIR` or any `GIT_*` variable, no `--amend`, no subagents from an implementer, no package installed into the host Python.
- § 5 binds every live task: `python testing/pzt doctor` before every boot; one session repository-wide; the 12 GB memory gate read and ledgered before the boot; a driver tested offline against the real staged copy and a real run layout before its first boot; a driver never edited after its run; a trivial reading written as such; artifacts byte-identical under `testing/artifacts/<run-id>/` with `GUIDE.md`; `testing/artifacts/x391f-20261013-113457/` is never staged.
- `testing/PZAgent/` never requires, references or calls `PZTestKit` or `TK`; every Java member call goes through `PZA.call` / `PZA.field`; `python tools/kahlua_lint.py testing/PZAgent`, `python tools/luabalance.py <each .lua>` and `python tools/mod_lint.py testing/PZAgent/PZAgent` are green before any commit of Lua.
- No file under `mod/`, `testing/PZTestKit/` or `docs/reference/claims.tsv` is edited by an implementer. A harness edit is the exception of spec § 7, ruled by the controller.
- Tests live under `testing/tests/agent/` (collected by the full run `python -m pytest tools/tests testing/tests -q`); the count never drops from 8329.
- Numbers in the Lua are written as Lua renders them; nothing is rounded.
- Angus's answers (2026-10-26): detached launches approved for stages A, B and C; the `agent` fixture may be provisioned; zombie settings are the defaults — `Zombies = 5` (Low) for the fixture and `Zombies = 4` (Normal) for stage C's second run; `ZombieRespawn = 4` (None) is the fixture's own value and stays.
- Rulings taken in this plan, each a `Ruling:` line in the ledger at Task 0:
  - **P21-0:** the command file is `cmd.txt` in `key=value` lines, not JSON — Kahlua has no JSON decoder in the tree and the harness bus reads the same form. The state stream stays JSON lines.
  - **P21-1:** the link probes append mode at load and falls back to numbered chunk files (`state-000001.log`, …) when append does not hold; stage A reports which mode ran.
  - **P21-2:** stage C's session is launched detached by the controller through `Start-Process` and polled through the driver's own persisted artifact file; the driver takes no argument.
  - **P21-3:** the Lua is tested offline under `lupa` with Python stubs for the Java globals it touches; a stub answers the member shapes the Lua reads, and a member the stub lacks must be reported by the Lua in a `missing` list, never raised.

## File structure

```
testing/PZAgent/PZAgent/
  mod.info                                   id=PZAgent
  42/media/lua/shared/PZAgent_Core.lua       PZA table: call/field guards, now, json, log, readKV
  42/media/lua/client/PZAgent_Link.lua       the file channel: emit, flush, rotate, poll cmd.txt, ack
  42/media/lua/client/PZAgent_Sense.lua      frame, event, scan; cost counters
  42/media/lua/client/PZAgent_Act.lua        goals: goto open loot eat drink fight flee sleep stop
  42/media/lua/client/PZAgent_Main.lua       the OnTick hook, load order last (sorts after Act/Link/Sense)
testing/agent/
  __init__.py
  link.py          Link: tail state files, send cmd, ack/status by seq
  world.py         World: me, zombies, map, server, events; replay()
  policy.py        Policy: behaviour tree → goal; decision log
  summary.py       summarize(world) → str
  grades.py        gate arithmetic shared by the grade scripts
  drivers/_dlib.py shared driver plumbing: preboot, memory wait, profile boot, state dir, bus poll
  drivers/a_pipe.py  a_grade.py
  drivers/b_actions.py  b_grade.py
  drivers/c_survive.py  c_grade.py
testing/profiles/agent.toml
testing/profiles/agent-nozombies.toml
testing/tests/agent/
  __init__.py  conftest.py (the lupa host and stubs)
  test_lua_core.py  test_lua_link.py  test_lua_sense.py  test_lua_act.py
  test_link.py  test_world.py  test_policy.py  test_summary.py
  test_dlib.py  test_a_pipe.py  test_b_actions.py  test_c_survive.py
  fixtures/  (recorded state logs, small)
docs/superpowers/specs/2026-10-26-agent-harness-report.md   (Task 13, the reviewer's)
```

---

### Task 0: the ledger, the plan commit and the three answers

**Files:**
- Create: `.superpowers/sdd/2026-10-26-plan-21-agent-harness/progress.md` (gitignored)
- Commit: `docs/superpowers/plans/2026-10-26-plan-21-agent-harness.md`

- [ ] **Step 1:** Write the ledger's first lines: the plan path; `Angus (2026-10-26): detached launches approved for A, B, C; agent fixture approved; zombie defaults 5 and 4`; the four `Ruling: P21-0 … P21-3 — <why from Global Constraints> — cost if wrong: <one line each>`.
- [ ] **Step 2:** `cd /c/Users/Angus/repos/project_zomboid && git commit -m "Plan 21: the agent harness exploration (plan)" -- docs/superpowers/plans/2026-10-26-plan-21-agent-harness.md`
- [ ] **Step 3:** Ledger `Task 0: complete`.

---

### Task 1: `PZAgent_Core.lua` and the lupa host

**Files:**
- Create: `testing/PZAgent/PZAgent/mod.info`, `testing/PZAgent/PZAgent/42/media/lua/shared/PZAgent_Core.lua`
- Create: `testing/tests/agent/__init__.py`, `testing/tests/agent/conftest.py`, `testing/tests/agent/test_lua_core.py`

**Interfaces — Produces:**
- Lua global `PZA` with `PZA.VERSION = "0.1"`, `PZA.call(obj, name, ...) -> ok, value`, `PZA.field(obj, name) -> ok, value`, `PZA.now() -> ms`, `PZA.json(v) -> string`, `PZA.log(msg)`, `PZA.readKV(name) -> table|nil`, `PZA.missing(list, name)` (appends `name` once).
- pytest fixture `lua` (a `LuaRuntime` with the stubs below loaded and `PZAgent_Core.lua` executed) and `lua_file(name)` helper returning the path of a mod Lua file.

- [ ] **Step 1: mod.info**

```
name=PZAgent
id=PZAgent
description=Agent link: streams player and world state to files and runs goals sent by a planner. Test profiles only.
```

- [ ] **Step 2: conftest.py — the host and the stubs**

```python
"""The lupa host for PZAgent's Lua: Python stubs stand in for the Java globals (ruling P21-3)."""
import os
import pytest
from lupa import LuaRuntime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(ROOT, "testing", "PZAgent", "PZAgent", "42", "media", "lua")


def lua_file(name):
    return os.path.join(LUA, name)


class FakeFS:
    """getFileWriter/getFileReader over a dict; append honoured when self.append_works."""
    def __init__(self):
        self.files = {}
        self.append_works = True
        self.opens = 0

    def writer(self, name, create, append):
        self.opens += 1
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
```

- [ ] **Step 3: the failing tests**

```python
from .conftest import lua_file


def test_call_guard_nil_obj_and_missing_member(lua):
    ok, v = lua.eval("PZA.call(nil, 'getX')")
    assert ok is False
    obj = lua.eval("{getX = function(self) return 7 end}")
    assert lua.eval("PZA.call(...)", obj, "getX") == (True, 7)
    assert lua.eval("PZA.call(...)", obj, "getY")[0] is False


def test_json_empty_table_is_object_and_numbers_unrounded(lua):
    assert lua.eval("PZA.json({})") == "{}"
    assert lua.eval("PZA.json({1.2345678901234567, 3})") == "[1.2345678901234567,3]"
    assert lua.eval("PZA.json({a='x\"y'})") == '{"a":"x\\"y"}'


def test_readkv_and_missing(lua, fs):
    fs.files["pzagent/admin/cmd.txt"] = "seq=3\ngoal=goto\nargs=1 2 run\n"
    t = lua.eval("PZA.readKV('pzagent/admin/cmd.txt')")
    assert t["seq"] == "3" and t["args"] == "1 2 run"
    assert lua.eval("PZA.readKV('nope.txt')") is None
    m = lua.eval("(function() local m = {}; PZA.missing(m, 'getX'); PZA.missing(m, 'getX'); return #m end)()")
    assert m == 1
```

- [ ] **Step 4:** Run `python -m pytest testing/tests/agent/test_lua_core.py -q` → fails (`PZA` nil).

- [ ] **Step 5: PZAgent_Core.lua**

```lua
-- PZAgent_Core.lua — the PZA table. Loads first (shared/). No PZTestKit anywhere in this mod.
-- Every Java member is reached through PZA.call / PZA.field: an unguarded nil call on a -debug client
-- parks the process in the Lua debugger (platform/lua-platform.md#debug-break), and pcall names nothing.
PZA = PZA or {}
PZA.VERSION = "0.1"

function PZA.log(msg) print("[PZAgent] " .. tostring(msg)) end
function PZA.now() return getTimestampMs and getTimestampMs() or 0 end

function PZA.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

function PZA.field(obj, name)
    if obj == nil then return false, nil end
    local v = obj[name]
    if v == nil then return false, nil end
    return true, v
end

function PZA.missing(list, name)
    for i = 1, #list do if list[i] == name then return end end
    list[#list + 1] = name
end

local function jsonString(s)
    s = tostring(s)
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t')
    return '"' .. s .. '"'
end

-- Encode-only JSON. An empty table is {} (the harness-wide convention); integers below 1e15 print
-- through %.0f, every other number through tostring, so nothing is rounded; NaN and ±Inf are null.
function PZA.json(v, depth)
    depth = depth or 0
    if depth > 8 then return '"<too deep>"' end
    local t = type(v)
    if t == "nil" then return "null" end
    if t == "boolean" then return v and "true" or "false" end
    if t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        if v == math.floor(v) and math.abs(v) < 1e15 then return string.format("%.0f", v) end
        return tostring(v)
    end
    if t == "string" then return jsonString(v) end
    if t == "table" then
        local n = 0
        for _ in pairs(v) do n = n + 1 end
        local isArray = n > 0
        for i = 1, n do if v[i] == nil then isArray = false; break end end
        local parts = {}
        if isArray then
            for i = 1, n do parts[i] = PZA.json(v[i], depth + 1) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, val in pairs(v) do parts[#parts + 1] = jsonString(k) .. ":" .. PZA.json(val, depth + 1) end
        table.sort(parts)
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return jsonString(tostring(v))
end

function PZA.readKV(name)
    local reader = getFileReader(name, false)
    if not reader then return nil end
    local t = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local k, v = string.match(line, "^%s*([%w_%.]+)%s*=%s*(.-)%s*$")
        if k then t[k] = v end
    end
    reader:close()
    return t
end
```

- [ ] **Step 6:** Tests pass; `python tools/kahlua_lint.py testing/PZAgent` → `0 findings`; `python tools/luabalance.py testing/PZAgent/PZAgent/42/media/lua/shared/PZAgent_Core.lua` → BALANCED; `python tools/mod_lint.py testing/PZAgent/PZAgent` → 0 ERROR.
- [ ] **Step 7:** `git commit -m "Plan 21 Task 1: PZAgent_Core (guards, json, readKV) and the lupa host" -- testing/PZAgent testing/tests/agent/__init__.py testing/tests/agent/conftest.py testing/tests/agent/test_lua_core.py`

---

### Task 2: `PZAgent_Link.lua` — emit, flush, rotate, poll, ack

**Files:**
- Create: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Link.lua`, `testing/tests/agent/test_lua_link.py`

**Interfaces — Consumes:** `PZA.*` from Task 1.
**Produces:**
- `PZA.link.init(user)` — sets `PZA.link.dir = "pzagent/" .. user .. "/"`, probes append (P21-1), sets `PZA.link.mode = "append"|"chunk"`, `PZA.link.seq = 0`, `PZA.link.lastCmd = 0` (recovered from `ack.txt`), opens nothing.
- `PZA.emit(kind, body)` — adds `kind, seq, tick, wallMs` (the caller adds `gameMin`, `worldAge`) and buffers the JSON line.
- `PZA.link.flush()` — writes the buffer: append mode appends to `state.log` and rotates past `PZA.link.ROTATE_BYTES = 8 * 1024 * 1024` to `state.<n>.log`; chunk mode writes the buffer as `state-<%06d>.log`. Returns the ms spent.
- `PZA.link.poll()` — reads `cmd.txt`; a `seq` greater than `lastCmd` is returned as `{seq=, goal=, args=}` once, `ack.txt` written `seq=<n>`; else nil.
- `PZA.link.ack(seq, ok, reason)` — emits `{kind="ack", cmdSeq=seq, ok=ok, reason=reason}`.

- [ ] **Step 1: tests**

```python
import json
from .conftest import lua_file


def load(lua):
    lua.execute(open(lua_file("client/PZAgent_Link.lua"), encoding="utf-8").read())
    lua.globals().PZA.tick = 0


def lines(fs, name):
    return [json.loads(l) for l in fs.files[name].split("\n") if l.strip()]


def test_append_mode_emits_lines_with_seq(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.mode") == "append"
    lua.execute("PZA.emit('frame', {x=1.5}); PZA.emit('frame', {x=2}); PZA.link.flush()")
    lua.execute("PZA.emit('frame', {x=3}); PZA.link.flush()")
    got = lines(fs, "pzagent/admin/state.log")
    assert [g["seq"] for g in got] == [1, 2, 3]
    assert got[0]["kind"] == "frame" and got[0]["x"] == 1.5 and got[0]["wallMs"] == 1000


def test_chunk_mode_when_append_fails(lua, fs):
    fs.append_works = False
    load(lua)
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.mode") == "chunk"
    lua.execute("PZA.emit('frame', {x=1}); PZA.link.flush(); PZA.emit('frame', {x=2}); PZA.link.flush()")
    assert lines(fs, "pzagent/admin/state-000001.log")[0]["x"] == 1
    assert lines(fs, "pzagent/admin/state-000002.log")[0]["x"] == 2


def test_rotate_past_limit(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin'); PZA.link.ROTATE_BYTES = 40")
    lua.execute("for i = 1, 5 do PZA.emit('frame', {x=i}); PZA.link.flush() end")
    assert "pzagent/admin/state.1.log" in fs.files
    total = sum(len(lines(fs, n)) for n in fs.files if n.startswith("pzagent/admin/state"))
    assert total == 5


def test_poll_accepts_each_seq_once_and_acks(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=goto\nargs=3 4\n"
    c = lua.eval("PZA.link.poll()")
    assert c["seq"] == 1 and c["goal"] == "goto" and c["args"] == "3 4"
    assert lua.eval("PZA.link.poll()") is None
    assert fs.files["pzagent/admin/ack.txt"] == "seq=1\n"
    lua.execute("PZA.link.ack(1, true, '')")
    lua.execute("PZA.link.flush()")
    assert lines(fs, "pzagent/admin/state.log")[-1] == {"kind": "ack", "seq": 1, "tick": 0, "wallMs": 1000,
                                                        "cmdSeq": 1, "ok": True, "reason": ""}


def test_last_cmd_recovered_from_ack_after_reset(lua, fs):
    load(lua)
    fs.files["pzagent/admin/ack.txt"] = "seq=7\n"
    fs.files["pzagent/admin/cmd.txt"] = "seq=7\ngoal=stop\nargs=\n"
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.poll()") is None
```

- [ ] **Step 2:** Run → fails (`PZA.link` nil).

- [ ] **Step 3: PZAgent_Link.lua**

```lua
-- PZAgent_Link.lua — the file channel. Out: JSON lines appended to Lua/pzagent/<user>/state.log
-- (or chunk files when append does not hold: ruling P21-1). In: cmd.txt as key=value lines, read by
-- seq (ruling P21-0); ack.txt holds the last accepted seq so a Lua reset never replays a command.
-- The Lua writer is rooted at the cachedir's Lua folder and allows ini/cfg/txt/log/json only [#1866].
PZA.link = PZA.link or {}
local L = PZA.link
L.ROTATE_BYTES = 8 * 1024 * 1024
L.buf = {}
L.bytes = 0
L.rot = 0
L.chunk = 0
L.seq = 0
L.lastCmd = 0

local function writeAll(name, s, append)
    local w = getFileWriter(name, true, append)
    if not w then PZA.log("cannot write " .. name); return false end
    w:write(s)
    w:close()
    return true
end

local function countLines(name)
    local r = getFileReader(name, false)
    if not r then return 0 end
    local n = 0
    while r:readLine() ~= nil do n = n + 1 end
    r:close()
    return n
end

function L.init(user)
    L.user = user
    L.dir = "pzagent/" .. user .. "/"
    local probe = L.dir .. "probe.log"
    writeAll(probe, "1\n", false)
    writeAll(probe, "2\n", true)
    L.mode = (countLines(probe) == 2) and "append" or "chunk"
    local ack = PZA.readKV(L.dir .. "ack.txt")
    L.lastCmd = (ack and tonumber(ack.seq)) or 0
    PZA.log("link " .. L.mode .. " lastCmd=" .. tostring(L.lastCmd))
end

function PZA.emit(kind, body)
    L.seq = L.seq + 1
    body.kind = kind
    body.seq = L.seq
    body.tick = PZA.tick or 0
    body.wallMs = PZA.now()
    L.buf[#L.buf + 1] = PZA.json(body)
end

function L.flush()
    if #L.buf == 0 then return 0 end
    local t0 = PZA.now()
    local s = table.concat(L.buf, "\n") .. "\n"
    L.buf = {}
    if L.mode == "chunk" then
        L.chunk = L.chunk + 1
        writeAll(L.dir .. string.format("state-%06d.log", L.chunk), s, false)
    else
        if L.bytes + #s > L.ROTATE_BYTES and L.bytes > 0 then
            L.rot = L.rot + 1
            -- rotate by renaming forward: copy state.log's content into state.<n>.log, then restart it
            local r = getFileReader(L.dir .. "state.log", false)
            local old = {}
            if r then
                while true do local line = r:readLine(); if line == nil then break end; old[#old + 1] = line end
                r:close()
            end
            writeAll(L.dir .. "state." .. L.rot .. ".log", table.concat(old, "\n") .. "\n", false)
            writeAll(L.dir .. "state.log", s, false)
            L.bytes = #s
            return PZA.now() - t0
        end
        writeAll(L.dir .. "state.log", s, true)
        L.bytes = L.bytes + #s
    end
    return PZA.now() - t0
end

function L.poll()
    local c = PZA.readKV(L.dir .. "cmd.txt")
    if not c then return nil end
    local seq = tonumber(c.seq)
    if not seq or seq <= L.lastCmd then return nil end
    L.lastCmd = seq
    writeAll(L.dir .. "ack.txt", "seq=" .. string.format("%.0f", seq) .. "\n", false)
    return { seq = seq, goal = c.goal or "", args = c.args or "" }
end

function L.ack(seq, ok, reason)
    PZA.emit("ack", { cmdSeq = seq, ok = ok, reason = reason or "" })
end
```

- [ ] **Step 4:** Tests pass; the three lints green on the file.
- [ ] **Step 5:** `git commit -m "Plan 21 Task 2: PZAgent_Link (emit, flush, rotate, chunk fallback, poll, ack)" -- testing/PZAgent testing/tests/agent/test_lua_link.py`

---

### Task 3: `link.py` — the Python side of the channel

**Files:**
- Create: `testing/agent/__init__.py`, `testing/agent/link.py`, `testing/tests/agent/test_link.py`

**Interfaces — Produces:**
```python
class Link:
    def __init__(self, state_dir: str, clock=time.time): ...
    def lines(self) -> list[dict]        # every new parsed line since the last call, in seq order, over state.log,
                                          # state.<n>.log and state-<n>.log; a partial last line waits
    def send(self, goal: str, args: str = "") -> int   # writes cmd.txt atomically (tmp + os.replace); returns seq
    def ack_of(self, seq: int) -> dict | None          # the ack line for a cmd seq, once lines() has seen it
    def goal_status(self) -> dict | None               # the latest frame's goal {seq,name,state,detail}
    def await_goal(self, seq: int, timeout_s: float, poll_s: float = 0.1, on_line=None) -> dict
        # pumps lines() until a frame reports goal.seq == seq with state in ("done","failed"), returns that goal
        # dict; raises TimeoutError(f"goal {seq} not finished in {timeout_s}s") after timeout
    gaps: list[tuple[int, int]]           # (expected, got) for every seq gap seen
```

- [ ] **Step 1: tests** (a `FakeMod` writes files the way the Lua does)

```python
import json, os
from agent.link import Link


class FakeMod:
    def __init__(self, d, chunk=False):
        self.d, self.chunk, self.seq, self.n = d, chunk, 0, 0
        os.makedirs(d, exist_ok=True)

    def line(self, kind, **body):
        self.seq += 1
        body.update(kind=kind, seq=self.seq, tick=self.seq * 12, wallMs=1000 + self.seq)
        s = json.dumps(body) + "\n"
        if self.chunk:
            self.n += 1
            open(os.path.join(self.d, "state-%06d.log" % self.n), "w").write(s)
        else:
            open(os.path.join(self.d, "state.log"), "a").write(s)

    def answer(self):
        kv = dict(l.split("=", 1) for l in open(os.path.join(self.d, "cmd.txt")).read().splitlines())
        self.line("ack", cmdSeq=int(kv["seq"]), ok=True, reason="")
        return kv


def test_tail_in_order_with_gaps_and_partial(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path))
    m.line("frame", x=1); m.line("frame", x=2)
    assert [l["seq"] for l in lk.lines()] == [1, 2]
    with open(tmp_path / "state.log", "a") as f: f.write('{"kind":"frame","seq":3')
    assert lk.lines() == []
    with open(tmp_path / "state.log", "a") as f: f.write(',"x":3}\n')
    m.seq = 4; m.line("frame", x=5)                      # seq 5, a gap at 4
    assert [l["seq"] for l in lk.lines()] == [3, 5]
    assert lk.gaps == [(4, 5)]


def test_chunk_files_read_in_number_order(tmp_path):
    m = FakeMod(str(tmp_path), chunk=True); lk = Link(str(tmp_path))
    for i in range(12): m.line("frame", x=i)
    assert [l["x"] for l in lk.lines()] == list(range(12))


def test_send_is_atomic_kv_and_ack_matches(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path))
    s = lk.send("goto", "3 4 run")
    assert s == 1 and not os.path.exists(tmp_path / "cmd.txt.tmp")
    assert m.answer() == {"seq": "1", "goal": "goto", "args": "3 4 run"}
    lk.lines()
    assert lk.ack_of(1)["ok"] is True and lk.ack_of(2) is None


def test_await_goal_done_and_timeout(tmp_path):
    m = FakeMod(str(tmp_path)); t = {"now": 0.0}
    lk = Link(str(tmp_path), clock=lambda: t["now"])
    s = lk.send("goto", "1 1")
    m.line("frame", goal={"seq": s, "name": "goto", "state": "running", "detail": ""})
    m.line("frame", goal={"seq": s, "name": "goto", "state": "done", "detail": "d=0.4"})
    g = lk.await_goal(s, timeout_s=5)
    assert g["state"] == "done"
    s2 = lk.send("goto", "9 9")
    def tick(): t["now"] += 1.0
    try:
        lk.await_goal(s2, timeout_s=3, poll_s=0, on_line=None, _sleep=lambda _: tick())
        assert False
    except TimeoutError as e:
        assert "goal 2" in str(e)
```

- [ ] **Step 2:** Run → fails (`agent.link` missing). Add `testing/agent/__init__.py` empty; tests import `agent.*` with `testing/` on `sys.path` — add to `testing/tests/agent/conftest.py` top: `sys.path.insert(0, os.path.join(ROOT, "testing"))`.

- [ ] **Step 3: link.py**

```python
"""The Python side of PZAgent's file channel (spec § 2). Tails the state files the Lua writes and sends
commands as key=value lines (ruling P21-0). Knows nothing about the game."""
import glob, json, os, re, time

CHUNK_RX = re.compile(r"state-(\d{6})\.log$")
ROT_RX = re.compile(r"state\.(\d+)\.log$")


class Link:
    def __init__(self, state_dir, clock=time.time):
        self.dir = state_dir
        self.clock = clock
        self.cmd_seq = 0
        self.expect = 1
        self.gaps = []
        self.acks = {}
        self.last_goal = None
        self._pos = {}          # file -> bytes consumed
        self._done_chunks = set()

    def _files(self):
        rots = sorted(glob.glob(os.path.join(self.dir, "state.*.log")), key=lambda p: int(ROT_RX.search(p).group(1)))
        chunks = sorted(glob.glob(os.path.join(self.dir, "state-*.log")), key=lambda p: int(CHUNK_RX.search(p).group(1)))
        main = os.path.join(self.dir, "state.log")
        return [p for p in rots + chunks + [main] if os.path.exists(p) and p not in self._done_chunks]

    def _read_new(self, path):
        pos = self._pos.get(path, 0)
        with open(path, "rb") as f:
            f.seek(pos)
            data = f.read()
        cut = data.rfind(b"\n")
        if cut < 0:
            return []
        self._pos[path] = pos + cut + 1
        out = []
        for raw in data[:cut].split(b"\n"):
            raw = raw.strip()
            if raw:
                out.append(json.loads(raw.decode("utf-8")))
        if CHUNK_RX.search(path):
            self._done_chunks.add(path)
        return out

    def lines(self):
        out = []
        for p in self._files():
            out.extend(self._read_new(p))
        out.sort(key=lambda l: l["seq"])
        for l in out:
            if l["seq"] != self.expect:
                self.gaps.append((self.expect, l["seq"]))
            self.expect = l["seq"] + 1
            if l["kind"] == "ack":
                self.acks[l["cmdSeq"]] = l
            if l["kind"] == "frame" and "goal" in l:
                self.last_goal = l["goal"]
        return out

    def send(self, goal, args=""):
        self.cmd_seq += 1
        tmp = os.path.join(self.dir, "cmd.txt.tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write("seq=%d\ngoal=%s\nargs=%s\n" % (self.cmd_seq, goal, args))
        os.replace(tmp, os.path.join(self.dir, "cmd.txt"))
        return self.cmd_seq

    def ack_of(self, seq):
        return self.acks.get(seq)

    def goal_status(self):
        return self.last_goal

    def await_goal(self, seq, timeout_s, poll_s=0.1, on_line=None, _sleep=time.sleep):
        t0 = self.clock()
        while True:
            for l in self.lines():
                if on_line:
                    on_line(l)
                g = l.get("goal") if l["kind"] == "frame" else None
                if g and g.get("seq") == seq and g.get("state") in ("done", "failed"):
                    return g
            if self.clock() - t0 > timeout_s:
                raise TimeoutError("goal %d not finished in %ss" % (seq, timeout_s))
            _sleep(poll_s)
```

- [ ] **Step 4:** Tests pass.
- [ ] **Step 5:** `git commit -m "Plan 21 Task 3: agent/link.py, the Python side of the channel" -- testing/agent/__init__.py testing/agent/link.py testing/tests/agent/test_link.py testing/tests/agent/conftest.py`

---

### Task 4: `PZAgent_Sense.lua` — frame, event, scan, cost

**Files:**
- Create: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Sense.lua`, `testing/tests/agent/test_lua_sense.py`
- Modify: `testing/tests/agent/conftest.py` (add the player/cell stubs)

**Interfaces — Consumes:** `PZA.emit`, `PZA.call`, `PZA.missing`.
**Produces:**
- `PZA.sense.RATE = 5`, `PZA.sense.ZOMBIE_RADIUS = 12`, `PZA.sense.SCAN_S = 0`, `PZA.sense.missing = {}`.
- `PZA.sense.frame(p) -> table` — the body of spec § 2.1 `frame`, without `goal` and `cost` (Main adds them).
- `PZA.sense.events(p, prev) -> list` — compares a frame against `prev` and returns event bodies: `zombie_enter {id, dist}` / `zombie_leave {id}` per id crossing `ZOMBIE_RADIUS`, `hit {health}` when health fell by more than 0.5, `item_added {fullType}` when inventory count rose (fullType of the newest item when readable, else "").
- `PZA.sense.scan(p, r) -> table` — spec § 2.1 `scan`: `{r=, squares=[{x,y,z,solid,solidTrans,room,building,light,door={open,locked,barricaded}|nil,window={open,locked}|nil,containers=[{type,n,items=[fullType…]}],floor=[fullType…]}], missing=[…]}` for the squares with |dx|,|dy| ≤ r at the player's z.
- `PZA.sense.clock() -> gameMin, worldAge` from `getGameTime()` (guarded; absent → 0, 0).

- [ ] **Step 1: conftest stubs** — append:

```python
class J:
    """A Java-like object: methods from a dict; a missing member is a missing attribute (nil in Lua)."""
    def __init__(self, **m):
        for k, v in m.items():
            setattr(self, k, v)


def make_player(x=10.0, y=20.0, z=0, hunger=0.3, health=100.0, items=()):
    stats = J(getHunger=lambda s: hunger, getThirst=lambda s: 0.2, getFatigue=lambda s: 0.1,
              getEndurance=lambda s: 0.9, getPanic=lambda s: 0.0, getPain=lambda s: 0.0)
    bd = J(getOverallBodyHealth=lambda s: health, getHealth=lambda s: health)
    inv = J(getItems=lambda s: J(size=lambda s2: len(items), get=lambda s2, i: J(getFullType=lambda s3, i=i: items[i])))
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: z, getDir=lambda s: "N",
             isPlayerMoving=lambda s: False, IsRunning=lambda s: False, isSprinting=lambda s: False,
             getStats=lambda s: stats, getBodyDamage=lambda s: bd, getInventory=lambda s: inv,
             getPrimaryHandItem=lambda s: None, getMoodles=lambda s: J(getMoodleLevel=lambda s2, t: 0))


def make_zombie(zid, x, y, dead=False):
    return J(getOnlineID=lambda s: zid, getX=lambda s: x, getY=lambda s: y, isDead=lambda s: dead,
             getTarget=lambda s: None, isCrawling=lambda s: False)


def make_cell(zombies=(), squares=None):
    zl = J(size=lambda s: len(zombies), get=lambda s, i: zombies[i])
    sq = squares or {}
    return J(getZombieList=lambda s: zl, getGridSquare=lambda s, x, y, z: sq.get((int(x), int(y), int(z))))
```

and in the `lua` fixture, after Core loads: `g.getCell = lambda: g._cell; g._cell = make_cell(); g.getGameTime = lambda: J(getHour=lambda s: 7, getMinutes=lambda s: 30, getWorldAgeHours=lambda s: 31.5)`. Export `J, make_player, make_zombie, make_cell` for the tests.

- [ ] **Step 2: tests**

```python
from .conftest import lua_file, make_player, make_zombie, make_cell, J


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Sense.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def test_frame_fields_and_zombies_in_radius(lua):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0), make_zombie(2, 40.0, 40.0), make_zombie(3, 11.0, 20.0, dead=True)])
    f = lua.eval("PZA.sense.frame(...)", make_player())
    assert f["x"] == 10.0 and f["hunger"] == 0.3 and f["health"] == 100.0 and f["dir"] == "N"
    assert [z["id"] for z in f["zombies"].values()] == [1] and abs(f["zombies"][1]["dist"] - 2.0) < 1e-9
    assert f["nZombies"] == 1 and f["items"] == 0


def test_missing_member_reported_not_raised(lua):
    load(lua)
    p = make_player(); del p.getStats
    f = lua.eval("PZA.sense.frame(...)", p)
    assert "hunger" not in f and "getStats" in list(lua.eval("PZA.sense.missing").values())


def test_events_enter_leave_hit_item(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0)])
    prev = lua.eval("PZA.sense.frame(...)", make_player(health=100.0, items=()))
    g._cell = make_cell(zombies=[make_zombie(2, 15.0, 20.0)])
    ev = lua.eval("PZA.sense.events(...)", make_player(health=98.0, items=("Base.Apple",)), prev)
    kinds = sorted(e["event"] for e in ev.values())
    assert kinds == ["hit", "item_added", "zombie_enter", "zombie_leave"]


def test_scan_reports_door_container_and_room(lua):
    load(lua)
    door = J(IsOpen=lambda s: False, isLocked=lambda s: True, isBarricaded=lambda s: False)
    cont = J(getType=lambda s: "fridge", getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: "Base.Milk")))
    objs = [J(getContainer=lambda s: cont), J(getContainer=lambda s: None, IsOpen=door.IsOpen, isLocked=door.isLocked, isBarricaded=door.isBarricaded)]
    sq = J(getX=lambda s: 11, getY=lambda s: 20, getZ=lambda s: 0, isSolid=lambda s: False, isSolidTrans=lambda s: False,
           getRoom=lambda s: J(getName=lambda s2: "kitchen"), getBuilding=lambda s: J(getID=lambda s2: 77),
           getLightLevel=lambda s, i: 0.6, getObjects=lambda s: J(size=lambda s2: 2, get=lambda s2, i: objs[i]),
           getWorldObjects=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None))
    lua.globals()._cell = make_cell(squares={(11, 20, 0): sq})
    s = lua.eval("PZA.sense.scan(...)", make_player(), 1)
    one = [q for q in s["squares"].values() if q["x"] == 11][0]
    assert one["room"] == "kitchen" and one["door"]["locked"] is True
    assert one["containers"][1]["type"] == "fridge" and one["containers"][1]["items"][1] == "Base.Milk"
    assert s["r"] == 1 and len(s["squares"]) == 1
```

- [ ] **Step 3:** Run → fails.

- [ ] **Step 4: PZAgent_Sense.lua**

```lua
-- PZAgent_Sense.lua — the sensors (spec § 2.1). A member this build does not expose is reported in
-- PZA.sense.missing and the key is absent, never nil-called [#1725]: a zero and an absent accessor are
-- different findings. Every reading is written as Lua renders it.
PZA.sense = PZA.sense or {}
local S = PZA.sense
S.RATE = 5
S.ZOMBIE_RADIUS = 12
S.SCAN_S = 0
S.missing = {}

local function get(out, key, obj, member, ...)
    local ok, v = PZA.call(obj, member, ...)
    if ok then out[key] = v else PZA.missing(S.missing, member) end
    return ok, v
end

function S.clock()
    local gt = getGameTime ~= nil and getGameTime() or nil
    local okH, h = PZA.call(gt, "getHour")
    local okM, m = PZA.call(gt, "getMinutes")
    local okW, w = PZA.call(gt, "getWorldAgeHours")
    local gameMin = (okH and okM) and (h * 60 + m) or 0
    return gameMin, okW and w or 0
end

local function zombies(p, px, py)
    local cell = getCell and getCell() or nil
    local _, list = PZA.call(cell, "getZombieList")
    local okN, n = PZA.call(list, "size")
    local out, count = {}, 0
    if not okN then PZA.missing(S.missing, "getZombieList"); return out, 0 end
    for i = 0, n - 1 do
        local _, z = PZA.call(list, "get", i)
        local _, dead = PZA.call(z, "isDead")
        if z ~= nil and dead ~= true then
            local ex, ey = z:getX() - px, z:getY() - py
            local d = math.sqrt(ex * ex + ey * ey)
            if d <= S.ZOMBIE_RADIUS then
                count = count + 1
                local okId, id = PZA.call(z, "getOnlineID")
                local _, target = PZA.call(z, "getTarget")
                local _, crawl = PZA.call(z, "isCrawling")
                out[count] = { id = okId and id or i, x = z:getX(), y = z:getY(), dist = d,
                               hasTarget = target ~= nil, crawler = crawl == true }
            end
        end
    end
    return out, count
end

function S.frame(p)
    local f = { x = p:getX(), y = p:getY(), z = p:getZ() }
    get(f, "dir", p, "getDir"); f.dir = f.dir ~= nil and tostring(f.dir) or nil
    get(f, "moving", p, "isPlayerMoving"); get(f, "running", p, "IsRunning"); get(f, "sprinting", p, "isSprinting")
    local okS, st = PZA.call(p, "getStats")
    if okS then
        get(f, "hunger", st, "getHunger"); get(f, "thirst", st, "getThirst"); get(f, "fatigue", st, "getFatigue")
        get(f, "endurance", st, "getEndurance"); get(f, "panic", st, "getPanic"); get(f, "pain", st, "getPain")
    else PZA.missing(S.missing, "getStats") end
    local okB, bd = PZA.call(p, "getBodyDamage")
    if okB then get(f, "health", bd, "getOverallBodyHealth") else PZA.missing(S.missing, "getBodyDamage") end
    local okW, w = PZA.call(p, "getPrimaryHandItem")
    if okW and w ~= nil then
        f.weapon = {}
        get(f.weapon, "type", w, "getFullType"); get(f.weapon, "condition", w, "getCondition"); get(f.weapon, "ammo", w, "getCurrentAmmoCount")
    end
    local okI, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local okC, n = PZA.call(items, "size")
    f.items = okC and n or 0
    if not okI then PZA.missing(S.missing, "getInventory") end
    local okM, mo = PZA.call(p, "getMoodles")
    if okM and MoodleType ~= nil then
        f.moodles = {}
        for _, name in ipairs({ "Hungry", "Thirst", "Tired", "Endurance", "Panic", "Pain", "Injured", "Bleeding", "Sick", "Wet", "Stress", "Unhappy" }) do
            local mt = MoodleType[name]
            if mt ~= nil then local ok, lv = PZA.call(mo, "getMoodleLevel", mt); if ok then f.moodles[name] = lv end end
        end
    end
    f.zombies, f.nZombies = zombies(p, f.x, f.y)
    return f
end

local function byId(list)
    local m = {}
    for i = 1, #list do m[list[i].id] = list[i] end
    return m
end

function S.events(p, prev)
    local cur = S.frame(p)
    local ev = {}
    local was, now = byId(prev.zombies or {}), byId(cur.zombies or {})
    for id, z in pairs(now) do if was[id] == nil then ev[#ev + 1] = { event = "zombie_enter", id = id, dist = z.dist } end end
    for id, _ in pairs(was) do if now[id] == nil then ev[#ev + 1] = { event = "zombie_leave", id = id } end end
    if cur.health ~= nil and prev.health ~= nil and prev.health - cur.health > 0.5 then
        ev[#ev + 1] = { event = "hit", health = cur.health }
    end
    if (cur.items or 0) > (prev.items or 0) then
        local _, inv = PZA.call(p, "getInventory")
        local _, items = PZA.call(inv, "getItems")
        local _, last = PZA.call(items, "get", cur.items - 1)
        local _, ft = PZA.call(last, "getFullType")
        ev[#ev + 1] = { event = "item_added", fullType = ft or "" }
    end
    return ev, cur
end

local function objectsOf(sq)
    local out = {}
    local _, list = PZA.call(sq, "getObjects")
    local okN, n = PZA.call(list, "size")
    if not okN then return out end
    for i = 0, n - 1 do local _, o = PZA.call(list, "get", i); if o ~= nil then out[#out + 1] = o end end
    return out
end

local function square(sq)
    local q = { x = sq:getX(), y = sq:getY(), z = sq:getZ(), containers = {}, floor = {} }
    get(q, "solid", sq, "isSolid"); get(q, "solidTrans", sq, "isSolidTrans"); get(q, "light", sq, "getLightLevel", 0)
    local okR, room = PZA.call(sq, "getRoom"); if okR and room ~= nil then local _, nm = PZA.call(room, "getName"); q.room = nm end
    local okB, b = PZA.call(sq, "getBuilding"); if okB and b ~= nil then local _, id = PZA.call(b, "getID"); q.building = id end
    for _, o in ipairs(objectsOf(sq)) do
        local okC, c = PZA.call(o, "getContainer")
        if okC and c ~= nil then
            local ct = { items = {} }
            get(ct, "type", c, "getType")
            local _, items = PZA.call(c, "getItems")
            local okN, n = PZA.call(items, "size")
            ct.n = okN and n or 0
            for i = 0, ct.n - 1 do local _, it = PZA.call(items, "get", i); local _, ft = PZA.call(it, "getFullType"); ct.items[#ct.items + 1] = ft or "?" end
            q.containers[#q.containers + 1] = ct
        end
        local okO, open = PZA.call(o, "IsOpen")
        if okO then
            local _, locked = PZA.call(o, "isLocked")
            local okBar, barr = PZA.call(o, "isBarricaded")
            if okBar then q.door = { open = open == true, locked = locked == true, barricaded = barr == true }
            else q.window = { open = open == true, locked = locked == true } end
        end
    end
    local _, wl = PZA.call(sq, "getWorldObjects")
    local okW, wn = PZA.call(wl, "size")
    for i = 0, (okW and wn or 0) - 1 do
        local _, wo = PZA.call(wl, "get", i); local _, it = PZA.call(wo, "getItem"); local _, ft = PZA.call(it, "getFullType")
        if ft ~= nil then q.floor[#q.floor + 1] = ft end
    end
    return q
end

function S.scan(p, r)
    local cell = getCell and getCell() or nil
    local out = { r = r, squares = {}, missing = S.missing }
    local px, py, pz = math.floor(p:getX()), math.floor(p:getY()), p:getZ()
    for dy = -r, r do
        for dx = -r, r do
            local _, sq = PZA.call(cell, "getGridSquare", px + dx, py + dy, pz)
            if sq ~= nil then out.squares[#out.squares + 1] = square(sq) end
        end
    end
    return out
end
```

- [ ] **Step 5:** Tests pass; lints green.
- [ ] **Step 6:** `git commit -m "Plan 21 Task 4: PZAgent_Sense (frame, events, scan, missing-member reporting)" -- testing/PZAgent testing/tests/agent/test_lua_sense.py testing/tests/agent/conftest.py`

---

### Task 5: `PZAgent_Act.lua` (goto, stop) and `PZAgent_Main.lua` (the tick)

**Files:**
- Create: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Act.lua`, `.../client/PZAgent_Main.lua`, `testing/tests/agent/test_lua_act.py`

**Interfaces — Consumes:** `PZA.link.*`, `PZA.sense.*`.
**Produces:**
- `PZA.act.goal` — `nil` or `{seq, name, state, detail, args, t0}`; `PZA.act.REPLAN_MAX = 3`, `PZA.act.STUCK_TICKS = 90`.
- `PZA.act.start(cmd) -> ok, reason` — dispatches on `cmd.goal` to `PZA.act.goals[name].start(args) -> ok, reason, detail`; unknown goal → `false, "unknown goal"`.
- `PZA.act.tick(p)` — runs `PZA.act.goals[name].tick(p, goal)`; a goal sets `goal.state = "done"|"failed"` and `goal.detail`; the first frame after that state carries it, then `PZA.act.goal` is cleared on the next tick (`idle`).
- `PZA.act.status() -> {seq, name, state, detail}` (`{seq=0, name="idle", state="idle", detail=""}` when none).
- Goals in this task: `goto x y [run]`, `stop`, and the config commands `rate n`, `scan r`, `radius n` (handled in Main, acked, no goal).
- `PZA.tick` counter; Main hooks `Events.OnTick` once, inside `pcall`, counting failures in `PZA.errors` and emitting `event lua_error {msg}` at most once a second.

- [ ] **Step 1: conftest stubs** — append `make_queue()` returning a `J` with `queue` list, `ISTimedActionQueue = J(add=…, getTimedActionQueue=…, isPlayerDoingAction=…, clear=…)` and `ISWalkToTimedAction = J(new=lambda cls, p, sq: J(Type="ISWalkToTimedAction", sq=sq))`, installed as globals in the `lua` fixture, the queue exported as `g._queue`; `ISTimedActionQueue.add` appends to `queue` and to `adds` (a list never emptied, so a test can count re-adds); `isPlayerDoingAction` returns `len(queue) > 0`; `clear` empties `queue` and increments `cleared`. `Events = J(OnTick=J(Add=lambda s, f: handlers.append(f)))` with `g._handlers = handlers`.

- [ ] **Step 2: tests**

```python
from .conftest import lua_file, make_player, make_cell, J


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Sense.lua", "client/PZAgent_Act.lua", "client/PZAgent_Main.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def sq(x, y):
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0)


def test_goto_queues_walk_and_reports_done_within_one_tile(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    ok, reason = lua.eval("PZA.act.start({seq=1, goal='goto', args='3 0'})")
    assert ok is True
    lua.eval("PZA.act.tick(...)", p)
    assert len(g._queue.queue) == 1 and lua.eval("PZA.act.status().state") == "running"
    pos["x"] = 12.6; g._queue.queue[:] = []
    lua.eval("PZA.act.tick(...)", p)
    st = lua.eval("PZA.act.status()")
    assert st["state"] == "done" and st["seq"] == 1
    lua.eval("PZA.act.tick(...)", p)
    assert lua.eval("PZA.act.status().name") == "idle"


def test_goto_no_square_fails_and_stuck_replans_then_fails(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={})
    ok, reason = lua.eval("PZA.act.start({seq=2, goal='goto', args='3 0'})")
    lua.eval("PZA.act.tick(...)", make_player())
    assert lua.eval("PZA.act.status()")["detail"] == "no square"
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.eval("PZA.act.start({seq=3, goal='goto', args='3 0'})")
    p = make_player()
    for _ in range(4 * 90 + 5):
        lua.eval("PZA.act.tick(...)", p)
    st = lua.eval("PZA.act.status()")
    assert st["state"] == "failed" and st["detail"] == "stuck"
    assert len(g._queue.adds) == 4           # the first add plus REPLAN_MAX re-adds


def test_unknown_goal_and_stop(lua):
    load(lua)
    assert lua.eval("PZA.act.start({seq=4, goal='dance', args=''})") == (False, "unknown goal")
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.eval("PZA.act.start({seq=5, goal='goto', args='3 0'})"); lua.eval("PZA.act.tick(...)", make_player())
    lua.eval("PZA.act.start({seq=6, goal='stop', args=''})"); lua.eval("PZA.act.tick(...)", make_player())
    assert g._queue.cleared == 1 and lua.eval("PZA.act.status()")["state"] == "done"


def test_main_tick_emits_hello_frames_at_rate_and_acks_config(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    assert len(g._handlers) == 1
    lua.execute("PZA.main.init('admin')")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=rate\nargs=10\n"
    for _ in range(60):
        g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    kinds = [l.split('"kind":"')[1].split('"')[0] for l in log.splitlines()]
    assert kinds[0] == "hello" and kinds.count("ack") == 1
    assert kinds.count("frame") == 10 and lua.eval("PZA.sense.RATE") == 10


def test_main_tick_catches_a_raise_and_emits_lua_error_once(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    lua.execute("PZA.main.init('admin')")
    for _ in range(30):
        g._handlers[0]()
    assert lua.eval("PZA.errors") == 30
    assert fs.files["pzagent/admin/state.log"].count('"event":"lua_error"') == 1
```

- [ ] **Step 3:** Run → fails.

- [ ] **Step 4: PZAgent_Act.lua** (goto and stop; the other goals are Tasks 8 and 10)

```lua
-- PZAgent_Act.lua — the goals (spec § 2.3). One goal at a time; each is a per-tick state machine that
-- sets state done|failed with a detail from its closed set. The walk is the game's own timed action,
-- queued the way the harness's player.walk does [#2082: setRunning(true) does not make a walk run].
PZA.act = PZA.act or {}
local A = PZA.act
A.goals = A.goals or {}
A.goal = nil
A.REPLAN_MAX = 3
A.STUCK_TICKS = 90

local function split(args)
    local out = {}
    for w in string.gmatch(args or "", "%S+") do out[#out + 1] = w end
    return out
end

function A.status()
    local g = A.goal
    if g == nil then return { seq = 0, name = "idle", state = "idle", detail = "" } end
    return { seq = g.seq, name = g.name, state = g.state, detail = g.detail or "" }
end

function A.start(cmd)
    local def = A.goals[cmd.goal]
    if def == nil then return false, "unknown goal" end
    local argv = split(cmd.args)
    local ok, reason, st = def.start(argv)
    if not ok then return false, reason end
    st.seq, st.name, st.state, st.detail, st.argv, st.ticks = cmd.seq, cmd.goal, "running", "", argv, 0
    A.goal = st
    return true, ""
end

function A.tick(p)
    local g = A.goal
    if g == nil then return end
    if g.state ~= "running" then
        if g.reported then A.goal = nil else g.reported = true end
        return
    end
    g.ticks = g.ticks + 1
    A.goals[g.name].tick(p, g)
end

local function queueWalk(p, sq)
    local ran, err = pcall(function() ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq)) end)
    return ran, err
end

local function dist(p, x, y)
    local ex, ey = p:getX() - x, p:getY() - y
    return math.sqrt(ex * ex + ey * ey)
end

A.goals["goto"] = {
    start = function(argv)
        local dx, dy = tonumber(argv[1]), tonumber(argv[2])
        if dx == nil or dy == nil then return false, "bad args" end
        return true, "", { dx = dx, dy = dy, run = argv[3] == "run", replans = 0, lastX = nil, lastY = nil, still = 0 }
    end,
    tick = function(p, g)
        if g.tx == nil then
            g.tx, g.ty = p:getX() + g.dx, p:getY() + g.dy
            local cell = getCell and getCell() or nil
            local _, sq = PZA.call(cell, "getGridSquare", g.tx, g.ty, p:getZ())
            if sq == nil then g.state, g.detail = "failed", "no square"; return end
            g.sq = sq
            if g.run then PZA.call(p, "setRunning", true) end
            local ran, err = queueWalk(p, sq)
            if not ran then g.state, g.detail = "failed", "no path"; return end
        end
        local d = dist(p, g.tx, g.ty)
        if d <= 1.0 then g.state, g.detail = "done", "d=" .. tostring(d); return end
        local x, y = p:getX(), p:getY()
        if g.lastX == x and g.lastY == y then g.still = g.still + 1 else g.still = 0 end
        g.lastX, g.lastY = x, y
        if g.still >= A.STUCK_TICKS then
            if g.replans >= A.REPLAN_MAX then g.state, g.detail = "failed", "stuck"; return end
            g.replans, g.still = g.replans + 1, 0
            pcall(ISTimedActionQueue.clear, p)
            queueWalk(p, g.sq)
        end
    end,
}

A.goals["stop"] = {
    start = function(argv) return true, "", {} end,
    tick = function(p, g)
        pcall(ISTimedActionQueue.clear, p)
        PZA.call(p, "setRunning", false)
        g.state, g.detail = "done", ""
    end,
}
```

- [ ] **Step 5: PZAgent_Main.lua**

```lua
-- PZAgent_Main.lua — the one OnTick hook (loads last by name). Each tick: poll cmd.txt, run the goal,
-- emit a frame every 60/RATE ticks with the goal status and the tick's own cost, flush. Everything sits
-- inside one pcall; a raise counts in PZA.errors and reports as a lua_error event once a second.
PZA.main = PZA.main or {}
local M = PZA.main
PZA.tick = 0
PZA.errors = 0
M.prev = nil
M.lastErrMs = -1e9
M.hooked = M.hooked or false

local function config(cmd)
    local v = tonumber(cmd.args)
    if cmd.goal == "rate" and v and v > 0 then PZA.sense.RATE = v; return true end
    if cmd.goal == "radius" and v and v > 0 then PZA.sense.ZOMBIE_RADIUS = v; return true end
    if cmd.goal == "scan" and v and v >= 0 then
        local okP, p = pcall(getPlayer)
        if okP and p ~= nil then local s = PZA.sense.scan(p, v); s.gameMin, s.worldAge = PZA.sense.clock(); PZA.emit("scan", s) end
        return true
    end
    return nil
end

function M.init(user)
    PZA.link.init(user)
    local build = getCore and getCore() or nil
    local _, ver = PZA.call(build, "getVersionNumber")
    PZA.emit("hello", { modVersion = PZA.VERSION, build = ver or "", user = user, rate = PZA.sense.RATE, mode = PZA.link.mode })
    PZA.link.flush()
end

local function body()
    PZA.tick = PZA.tick + 1
    local t0 = PZA.now()
    local cmd = PZA.link.poll()
    if cmd ~= nil then
        local handled = config(cmd)
        if handled == nil then
            local ok, reason = PZA.act.start(cmd)
            PZA.link.ack(cmd.seq, ok, reason)
        else PZA.link.ack(cmd.seq, true, "") end
    end
    local p = getPlayer()
    if p == nil then return end
    local tAct = PZA.now()
    PZA.act.tick(p)
    local tSense = PZA.now()
    local every = math.max(1, math.floor(60 / PZA.sense.RATE))
    if PZA.tick % every == 0 then
        local ev, cur = {}, nil
        if M.prev ~= nil then ev, cur = PZA.sense.events(p, M.prev) else cur = PZA.sense.frame(p) end
        local gameMin, worldAge = PZA.sense.clock()
        for i = 1, #ev do ev[i].gameMin, ev[i].worldAge = gameMin, worldAge; PZA.emit("event", ev[i]) end
        cur.goal = PZA.act.status()
        cur.gameMin, cur.worldAge = gameMin, worldAge
        local tLink = PZA.now()
        cur.cost = { actMs = tSense - tAct, senseMs = tLink - tSense, linkMs = 0, pollMs = tAct - t0 }
        PZA.emit("frame", cur)
        cur.cost.linkMs = PZA.link.flush()
        M.prev = cur
    end
end

local function onTick()
    local ok, err = pcall(body)
    if not ok then
        PZA.errors = PZA.errors + 1
        local now = PZA.now()
        if now - M.lastErrMs >= 1000 then
            M.lastErrMs = now
            PZA.emit("event", { event = "lua_error", msg = tostring(err) })
            PZA.link.flush()
        end
    end
end

if not M.hooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(onTick)
    M.hooked = true
end
```

The `user` for `M.init` comes from `getPlayer():getUsername()` on the first tick a player exists (add to `body`: `if not M.ready then local _, u = PZA.call(p, "getUsername"); M.init(u or "admin"); M.ready = true end` right after `p == nil` returns). The test calls `M.init` directly and sets `M.ready = true` through `lua.execute("PZA.main.ready = true")` before ticking — add that line to the two Main tests.

- [ ] **Step 6:** Tests pass; lints green on all five files.
- [ ] **Step 7:** `git commit -m "Plan 21 Task 5: PZAgent_Act (goto, stop) and PZAgent_Main (the tick, frames, config, lua_error)" -- testing/PZAgent testing/tests/agent/test_lua_act.py testing/tests/agent/conftest.py`

---

### Task 6: `world.py`, the replay golden, and `summary.py`

**Files:**
- Create: `testing/agent/world.py`, `testing/agent/summary.py`, `testing/tests/agent/test_world.py`, `testing/tests/agent/test_summary.py`, `testing/tests/agent/fixtures/log-synthetic-1.log` (20 lines, hand-written: hello, frames, two events, one scan, one ack), `testing/tests/agent/fixtures/log-synthetic-1.world.json` (its golden)

**Interfaces — Produces:**
```python
class World:
    ZOMBIE_TTL_S = 10.0
    me: dict            # the latest frame's fields plus wallMs, gameMin, worldAge
    zombies: dict       # id -> {x, y, dist, hasTarget, crawler, seenWallMs}
    map: dict           # (x, y, z) -> the scan's square dict, last scan wins
    containers: dict    # (x, y, z, index) -> {type, n, items, looted: bool}
    buildings: set      # building ids seen
    server: dict        # the bus readings: {"stats": {...}, "wallMs": ...}
    events: deque       # maxlen 200, the event lines
    goal: dict | None
    missing: list
    def apply(self, line: dict) -> None
    def merge_server(self, stats: dict, wall_ms: float) -> None
    def mark_looted(self, key) -> None
    def nearest_unlooted(self, want: str | None = None) -> tuple | None    # key of the nearest container
                           # with looted False; `want` in (None,"food","water") filters by item fullType heuristics
    def unexplored_edge(self) -> tuple[int, int] | None   # the nearest scanned non-solid square beside an
                           # unscanned one, as (x, y)
    def to_json(self) -> dict   # deterministic (sorted keys, tuples as "x,y,z" strings)

def replay(path: str) -> World
def summarize(world: World) -> str   # summary.py: ≤ 25 lines, deterministic
```

Food heuristic (`agent/world.py`, `FOOD_RX = re.compile(r"\.(Apple|Bread|Milk|Water|Pop|Chips|Cereal|Cabbage|Carrots|Tomato|Egg|Steak|Chicken|Ham|Canned|Tuna|Peanut|Candy|Chocolate|Juice|Soda|Beer|Wine|Whiskey|Orange|Banana|Lettuce|Potato)")`, `WATER_RX = re.compile(r"\.(WaterBottle|Pop|Juice|Milk|Soda|Bowl|Pot|Kettle|Bucket)")`) — a heuristic, named as such in the module docstring; the spike grades on outcomes, not on the heuristic.

- [ ] **Step 1: tests** — `test_apply_frame_zombies_age_out`, `test_scan_fills_map_and_containers`, `test_nearest_unlooted_filters_food`, `test_unexplored_edge`, `test_replay_golden` (`replay(fixture).to_json() == json.load(golden)`), `test_summary_golden` (compare to `log-synthetic-1.summary.txt`). Write the fixtures by hand first, the golden by running `replay` once and reading it by eye (every value traceable to a fixture line), then commit both.

- [ ] **Step 2–4:** Run → fail → implement → pass. `summarize` prints: position, game time, needs (hunger/thirst/fatigue/health with one decimal), the goal line, `threats: n (nearest d)`, up to five known resources (`container <type> at x,y: <k> items`), the unexplored edge, the last three events.

- [ ] **Step 5:** `git commit -m "Plan 21 Task 6: agent/world.py (the model, replay golden) and summary.py" -- testing/agent/world.py testing/agent/summary.py testing/tests/agent/test_world.py testing/tests/agent/test_summary.py testing/tests/agent/fixtures`

---

### Task 7: fixture, profiles, `_dlib.py`, and the Stage 0 gate

**Files:**
- Create: `testing/profiles/agent.toml`, `testing/profiles/agent-nozombies.toml`, `testing/agent/drivers/__init__.py`, `testing/agent/drivers/_dlib.py`, `testing/tests/agent/test_dlib.py`
- Run (controller, not an implementer — it boots a game): `python testing/pzt provision --name agent --sandbox Zombies=5`

**Interfaces — Produces (`_dlib.py`):**
```python
MIN_FREE_GB = 12.0
def wait_memory(min_gb=MIN_FREE_GB, max_wait_s=1800.0, poll_s=60.0, free=xlib.free_gb, sleep=time.sleep, clock=time.time) -> tuple[bool, list[dict]]
    # polls until free >= min_gb; returns (ok, readings [{wall, free_gb}]) — spec § 7 memory gate
def state_dir(client) -> str          # os.path.join(client.cache, "Lua", "pzagent", client.user)
def clear_state_dir(client) -> None   # removes a stale pzagent/ folder before launch (the fixture copies Lua/)
def preboot(me, profile_path) -> tuple[dict, bool]   # git provenance, doctor, harness-lua-dirty, lint_paths; mirrors x505's preboot
def boot(xs, prof, rec_fx, run_dir, users, started, clients, holder) -> dict   # make_server, start, attach_clients, verify; returns out fields
def bus_stats(xs, user) -> dict        # xs.step("server", "stats.all", user) ack, with wallMs
def link_for(clients, user) -> Link
```

Profiles:

```toml
# testing/profiles/agent.toml — Plan 21: PZAgent beside the harness on the agent fixture (Zombies=5, Low).
fixture = "agent"
description = "PZTestKit + PZAgent, zombies Low, 90-minute day, sleep allowed."
run = { hold = 5 }
clients = ["admin"]
verify = [
  { side = "server", cmd = "ping", expect = "pong" },
  { side = "client", cmd = "ping", expect = "pong" },
]

[[mods]]
id = "PZTestKit"

[[mods]]
id = "PZAgent"
path = "testing/PZAgent/PZAgent"

[server]
SleepAllowed = true
SleepNeeded = true

[client]
timeout = 120
```

`agent-nozombies.toml` is the same with `[sandbox] Zombies = 6` added and the description changed; stage C's dense run uses a third, `agent-dense.toml`, `[sandbox] Zombies = 4` (create it here too).

- [ ] **Step 1:** Tests for `wait_memory` (returns at once when free; polls N times then true; false after `max_wait_s` with the readings kept), `state_dir`, `clear_state_dir` on a tmp layout. Run → fail → implement → pass.
- [ ] **Step 2:** `python -m pytest testing/tests/test_profile.py testing/tests/test_cli_profile.py -q` still green (the profiles are loaded by `profile.load` in a new test `test_agent_profiles_resolve` that asserts `prof.sources["PZAgent"]` ends with `testing/PZAgent/PZAgent` and `prof.ini["SleepAllowed"]` is true — read the attribute names off `testing/pzt/profile.py` first and use its own).
- [ ] **Step 3 (controller):** `python testing/pzt doctor`; the memory gate (read, ledgered); `python testing/pzt provision --name agent --sandbox Zombies=5` (about 2.5 min, one live session); ledger the provision run id and `testing/fixtures/agent/fixture.json`'s build line.
- [ ] **Step 4 (Stage 0 gate):** `python testing/pzt doctor` passes with the fixture present; `python -c "from pzt import profile; from pzt.harness import lint_paths; p = profile.load('testing/profiles/agent.toml'); print(lint_paths(profile.lint_sources(p, p.sources)))"` prints an empty list; the full pytest from a saved file: count ≥ 8329 + the new tests.
- [ ] **Step 5:** `git commit -m "Plan 21 Task 7: the agent fixture record, the three profiles, drivers/_dlib.py (memory wait, state dir, preboot, boot)" -- testing/profiles/agent.toml testing/profiles/agent-nozombies.toml testing/profiles/agent-dense.toml testing/agent/drivers testing/tests/agent/test_dlib.py testing/fixtures/agent/fixture.json`

---

### Task 8: Stage A — `a_pipe.py`, `a_grade.py`, and the live loop

**Files:**
- Create: `testing/agent/drivers/a_pipe.py`, `testing/agent/drivers/a_grade.py`, `testing/agent/grades.py`, `testing/tests/agent/test_a_pipe.py`

**Interfaces — Consumes:** `_dlib.*`, `Link`, `World`, `xlib.Xs`.
**Produces (`grades.py`):** `pct(values, p) -> float` (nearest-rank), `gate_a(rows) -> dict` returning `{"tick_p99_ms_at5": …, "scan15_ms": …, "cmd_motion_p90_ms": …, "gaps": n, "lua_errors": n, "mode": "append"|"chunk", "pass": {name: bool}, "verdict": "GO"|"NO-GO"}` from the artifact's `readings` (the thresholds of spec § 4.1 as module constants `TICK_P99_MS = 2.0`, `SCAN15_MS = 5.0`, `CMD_MOTION_P90_MS = 500.0`).

The driver (`KEY = "a_pipe"`, `PROFILE = "testing/profiles/agent-nozombies.toml"`, `ARTIFACT = "a_pipe.json"`, `BUDGET_S = 540.0`, refuses any argument), phases:
1. `rates`: for `r in (2, 5, 10)`: `link.send("rate", str(r))`, await the ack, collect 60 s of frames; record per-rate `cost` lists and the frame count against `60 * r`.
2. `scans`: for `r in (5, 10, 15)`: five `scan r` commands; record each scan line's size and the next frame's `senseMs`.
3. `motion`: ten times `goto 10 0` then `goto -10 0`: record cmd write wall (Python clock), the ack's `wallMs`, and the first frame whose `x` differs from the pre-command `x` by more than 0.2; await each goal (timeout 30 s).
4. `server`: three `bus_stats` calls, recording the round trip, so the report has the bus's cost beside the link's.
Every reading goes under `out["readings"]`; `out["missing"] = world.missing`; `out["mode"]` from `hello`.

- [ ] **Step 1: offline tests** (`test_a_pipe.py`): refuses an argument (statically: `D.parse_argv(["x"], D.__file__)` returns a refusal, never invoking the driver); its constants name its own file and profile; `gate_a` on a synthetic rows dict: a passing set returns GO, each threshold crossed alone flips its `pass` entry and the verdict; the pre-boot checks run against the real profile and a real run layout under `tmp_path` (as x505's test does — copy its `preboot` test pattern).
- [ ] **Step 2:** Run → fail → implement the driver (main skeleton from `x505_smoke.py` L503–624, each phase through `xs.run_phase`, `_dlib.preboot/boot/wait_memory`) → pass. Lints: none for Python beyond pytest.
- [ ] **Step 3:** Commit: `git commit -m "Plan 21 Task 8: a_pipe driver, a_grade, grades.gate_a (offline)" -- testing/agent/drivers/a_pipe.py testing/agent/drivers/a_grade.py testing/agent/grades.py testing/tests/agent/test_a_pipe.py`
- [ ] **Step 4 (live loop, controller-dispatched, Opus implementer, one pass per dispatch, budget 3):** doctor → memory gate ledgered → launch detached: PowerShell `Start-Process -FilePath python -ArgumentList "testing/agent/drivers/a_pipe.py" -WorkingDirectory "C:\Users\Angus\repos\project_zomboid" -RedirectStandardOutput "testing/runs/a_pipe-launch.out" -RedirectStandardError "testing/runs/a_pipe-launch.err"` → poll `testing/runs/<run-id>/a_pipe.json` (`steps` count and `phase_walls`) every 60 s in foreground calls until `out["finished"]` or the budget → `python testing/agent/drivers/a_grade.py testing/artifacts/<run-id>/a_pipe.json` → the verdict and the GUIDE.md (the x505 guide's structure; the do-not-cite table names every `wallMs`/Python-clock key by one wildcard sentence).
- [ ] **Step 5:** A FAIL names the defect (a cost line, a missing member, append not holding, a parked client). The fix is one commit to `PZAgent` or the driver *before its run* (a driver that ran is frozen; the next pass is a new driver file `a_pipe_2.py`, named in the guide). Ledger `Stage A pass <n>: <verdict>`.
- [ ] **Step 6:** On GO or budget exhausted: the artifact folder and its row in `docs/reference/artifacts.md` land in a controller commit (§ 4: the artifact-row commit re-runs the full checker and re-anchors any shifted pointers); ledger `Task 8: complete, Stage A <GO|NO-GO>`. NO-GO skips Tasks 9–12 and goes to Task 13.

---

### Task 9: goals `open`, `loot`, `eat`, `drink`

**Files:**
- Modify: `testing/PZAgent/PZAgent/42/media/lua/client/PZAgent_Act.lua` (append goals at the end), `testing/tests/agent/test_lua_act.py`, `testing/tests/agent/conftest.py` (stubs: `ISOpenCloseDoor`, `ISInventoryTransferAction`, `ISEatFoodAction`, `ISDrinkFluidAction`, `instanceof`)

**Before coding:** read the constructors' real signatures in the install (read-only): `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua\client\TimedActions\ISOpenCloseDoor.lua`, `ISInventoryTransferAction.lua`, `ISEatFoodAction.lua`, `ISDrinkFluidAction.lua`; quote each `function X:new(` line in the task report. The harness's `eat.action` uses `ISEatFoodAction:new(p, it, fraction)` and `drink.action` `ISDrinkFluidAction:new(p, it, percentage)`.

**Interfaces — Produces:** goals per spec § 2.3 with these closed `detail` sets:
- `open x y`: done `"open"`; failed `"no square"|"no door"|"locked"|"not adjacent"`. It first walks adjacent (reuses the goto machine: a goal may hold `g.sub`, a goto state the tick advances until done).
- `loot x y [food|water|weapon|bandage|all]`: done `"moved=<n>"`; failed `"no container"|"not loaded"|"empty"|"no match"`. Filter: `food` = `instanceof(item, "Food")`; `water` = `item:getFluidContainer() ~= nil`; `weapon` = `instanceof(item, "HandWeapon")`; `bandage` = fullType matching `Bandage|Rag`; `all` = everything.
- `eat T` / `drink`: done `"consumed"`; failed `"none held"|"interrupted"|"not valid"` (`isValidStart` false). Done is read as the item's count in the inventory falling (eat) or the container's amount falling (drink) within 20 s of game-wall; else `"interrupted"`.

- [ ] **Step 1:** Tests per goal: the done path, each failed detail, and that `open` walks first (the queue holds a walk, then an open). Run → fail → implement → pass; lints green.
- [ ] **Step 2:** `git commit -m "Plan 21 Task 9: PZAgent goals open, loot, eat, drink" -- testing/PZAgent testing/tests/agent/test_lua_act.py testing/tests/agent/conftest.py`

---

### Task 10: Stage B — `b_actions.py`, `b_grade.py`, and the live loop

**Files:**
- Create: `testing/agent/drivers/b_actions.py`, `testing/agent/drivers/b_grade.py`, `testing/tests/agent/test_b_actions.py`; modify `testing/agent/grades.py` (`gate_b`)

`gate_b(rows) -> {"sequences": 5, "completed": n, "reasons_in_set": bool, "eats_seen_by_server": n, "pass": {...}, "verdict"}` with `COMPLETE_MIN = 4`, the closed reason set imported from one place (`agent/reasons.py`: `REASONS = {...}` listing every `detail` string Tasks 5 and 9 emit; a Lua test asserts each emitted detail is in the set by grepping `PZAgent_Act.lua` for `"failed", "<x>"` pairs).

The driver (`PROFILE = "testing/profiles/agent-nozombies.toml"`, `BUDGET_S = 560.0`): five repetitions of `scan 15` → pick the nearest container-holding square from the scan → `goto` beside it → `open` the nearest door square on the way if the scan shows one between → `loot x y food` → `loot x y water` → `eat <first food fullType in the frame's items event>` → `drink` → `goto` back to the spawn offset. Each step `await_goal(timeout 60)`; after each eat, `bus_stats` until hunger moved or 60 s. The run spawns a `Base.WaterBottleFull` and a `Base.Apple` through `xs.spawn` before repetition 1 so the eat and drink steps have a fallback item (named in the readings as `spawned`).

- [ ] **Step 1:** Offline tests as Task 8's, plus `gate_b` cases and a planner-less sequence test against a `FakeMod` that answers each goal `done` (the driver's step order is asserted from the fake's command log).
- [ ] **Step 2:** Implement → pass → commit `"Plan 21 Task 10: b_actions driver, b_grade, gate_b, agent/reasons.py (offline)"`.
- [ ] **Step 3 (live loop, budget 4):** as Task 8 Step 4–6 with `b_actions`. A failed goal's fix lands in `PZAgent_Act.lua` as its own commit with a Lua test reproducing the failure from the artifact's detail; the next pass is `b_actions_<n>.py`. Ledger each pass; `Task 10: complete, Stage B <GO|NO-GO>`. NO-GO skips Tasks 11–12.

---

### Task 11: goals `fight`, `flee`, `sleep`; `policy.py`

**Files:**
- Modify: `PZAgent_Act.lua` (append), `test_lua_act.py`, `conftest.py`
- Create: `testing/agent/policy.py`, `testing/tests/agent/test_policy.py`

**Before coding:** read `ISWorldObjectContextMenu.onSleep` (or the B42 equivalent the install's `media/lua/client/ISUI/ISWorldObjectContextMenu.lua` holds; grep `onSleep`) and `IsoPlayer`'s attack entry used by the harness's `attack.melee` (`PZTestKit_Client.lua:990`, the `DoAttack` call and its argument); quote both in the report.

**Produces:**
- `fight`: per tick, nearest live zombie within `PZA.act.FIGHT_R = 3`: `p:faceThisObject(z)` guarded, `DoAttack` when `PZA.now() - g.lastSwing >= 1200`; when `dist < 1.0` and no swing is due, queue a walk 2 tiles away along the player→zombie vector reversed; done `"clear"` when none within `PZA.sense.ZOMBIE_RADIUS` for 60 ticks; failed `"no weapon"` (no primary item), `"weapon broke"` (condition 0), `"low health"` (health < `FLEE_HEALTH = 40`, reported so Python decides).
- `flee x y`: `goto` with run, re-planning each 30 ticks away from the nearest zombie's centroid; done `"at"`; failed `"cornered"` (no square or stuck).
- `sleep`: the sleep call under pcall; done `"awake"` when the player's `isAsleep` flips true then false; failed `"not allowed"` (the call errored or `isAsleep` never turned true within 10 s wall), `"interrupted"`.
- `policy.py`: `Policy(world, link, log_path, clock)` with `tick() -> str | None` (the goal sent, or None when unchanged); thresholds `DANGER_R = 6.0`, `THIRST_T = 0.5`, `HUNGER_T = 0.5`, `FATIGUE_T = 0.7`; `decision.log` lines `{wall, gameMin, branch, inputs, goal, args, sent}`; the five branches of spec § 3, each as a method returning `(goal, args) | None`, tried in order.

- [ ] **Step 1:** Lua tests: each goal's done and each failed detail (the stubs gain `faceThisObject`, `DoAttack`, `isAsleep`). Policy tests: every branch with a world built from synthetic frames; the "sent only when changed" rule; a replayed death log reproduces the last ten decisions (`fixtures/log-synthetic-death.log`, hand-written, 60 lines).
- [ ] **Step 2:** Implement → pass → lints → commit `"Plan 21 Task 11: PZAgent goals fight, flee, sleep; agent/policy.py and the decision log"`.

---

### Task 12: Stage C — `c_survive.py`, `c_grade.py`, the detached runs

**Files:**
- Create: `testing/agent/drivers/c_survive.py`, `testing/agent/drivers/c_grade.py`, `testing/tests/agent/test_c_survive.py`; modify `grades.py` (`grade_c`, no pass/fail: survival s, needs series, decisions/min, fights, deaths with the last ten decisions, cost p50/p99 over the session, `lua_error` count, stop reason).

The driver (`PROFILE = "testing/profiles/agent.toml"`, `BUDGET_S = 5700.0`, one game day = 5400 s wall at the 90-minute day plus margin): preboot → spawn a `Base.BaseballBat` by `xs.spawn` (the start kit, named in the readings) → the planner loop at `PLANNER_HZ = 2`: pump the link, `world.apply`, every 60 s `bus_stats` merged, `policy.tick()`, `xs.persist()` every 30 s (the controller's poll signal) → stop conditions: death (`health <= 0` or a `players` bus reply without the user), bus dead 60 s, `lua_error` > 10 in a minute, memory below 12 GB (read every 5 min through `xlib.free_gb`), the game-day cap → teardown and copy. The second file `c_survive_dense.py` differs by `PROFILE = "testing/profiles/agent-dense.toml"` and runs only if the first survived (controller's call).

- [ ] **Step 1:** Offline tests: the stop conditions each end the loop on a `FakeMod` (death, dead bus, error storm, memory, cap); the planner loop sends goals from the policy; `grade_c` on a synthetic artifact; argument refusal; constants.
- [ ] **Step 2:** Implement → pass → commit `"Plan 21 Task 12: c_survive driver, c_grade, grade_c (offline)"`.
- [ ] **Step 3 (live, budget 3 runs):** the detached launch as Task 8 Step 4, polled every 120 s; one fix pass allowed after run 1 if it forces one (a new driver file, the fix named in the guide); run 2 is the fix's run or the dense run. Each run's artifact folder, GUIDE.md and register row land by controller commit. Ledger each.
- [ ] **Step 4:** `Task 12: complete`.

---

### Task 13: the report, the register rows and the close

**Files:**
- Create: `docs/superpowers/specs/2026-10-26-agent-harness-report.md` (a fresh Opus reviewer, from the artifacts alone — the brief forbids reading the implementers' reports)
- Modify (controller): `docs/reference/claims.tsv` via a delta (one `M` row per gate reading of stages A and B and per stage C survival result, owner `platform/harness.md#agent` — a new short `### The agent link (Plan 21, exploratory)` section stating each measured number with its tag, so the rows have owner sentences; rule 12/13 green), `docs/reference/do-not-cite.csv` (the wall-clock wildcard sentences), `docs/reference/research-notes.md` (the open threads the report names), `docs/superpowers/HISTORY.md` (the Plan 21 entry), `CLAUDE.md` (a router row `drive the player from Python (the agent link)` → `platform/harness#agent` → `testing/agent/`; the § 3 baseline line), the memory file.

- [ ] **Step 1 (reviewer brief):** sections per spec § 4.4; every number cites `testing/artifacts/<run>/<file>` and a key; the gate arithmetic is re-derived from the artifact with `grades.py`, and any disagreement with the grade script's output is a finding; the "decisions taken" list copies the ledger's `Ruling:` lines; the recommendation names go / no-go / go-with-changes and whether spike D is worth running; `Model: <exact id>`.
- [ ] **Step 2 (controller):** the delta applied on an archive copy, full claims_check 0, `page_lint docs/platform/harness.md` 0, `reference_gen cited-by --write`, the full pytest from a saved file (≥ the Task 7 count), the commit by pathspec, the push, CLAUDE.md § 3 baseline updated, the memory file updated, ledger `Task 13: complete` and `Plan 21: closed`.

---

## Self-review

- **Spec coverage.** § 1.1 → Tasks 1, 2, 4, 5, 9, 11 (`PZAgent_Server.lua` is built only if Stage A names it, so no task; the controller opens one as an amendment if the gate says so). § 1.2 → Tasks 3, 6, 11, 7 and the drivers. § 1.3 → Task 7. § 2.1–2.3 → Tasks 2, 4, 5, 9, 11 (`stuck` is emitted as a goal detail and as the `goal_failed` event; `goal_done`/`goal_failed` events: Main emits one when `A.status().state` changes to done/failed — add that comparison to `body` in Task 5 beside `cur.goal`). § 2.4 → `_dlib.bus_stats`, Task 7. § 3 → Task 11. § 4.0–4.3 → Tasks 7, 8, 10, 12. § 4.4 → Task 13. § 5–6 → the Global Constraints and each live step. § 7 → Task 0 and `_dlib.wait_memory`. § 8 untouched.
- **Placeholders.** None: every gate is a constant, every reason string is in `agent/reasons.py`, every signature named. The two "read the install first" steps (Tasks 9 and 11) are deliberate: the constructors' argument lists are read off the read-only install rather than guessed, and quoted in the report.
- **Type consistency.** `Link.send(goal, args) -> int`, `await_goal -> goal dict` used by Tasks 8, 10, 12; `World.apply(line)`, `merge_server(stats, wall_ms)` used by Tasks 11, 12; `PZA.act.status()` shape `{seq, name, state, detail}` matches `link.last_goal`; `cost` keys `pollMs, actMs, senseMs, linkMs` are what `gate_a` reads (tick cost = their sum).
