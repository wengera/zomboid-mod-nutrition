"""The fake PZAgent mod (spec § 8): it writes PZA/1 lines as the Lua does, every one through `pza1.encode`, and answers
`cmd.txt` with scripted act lines. Every Python test of the agent base from Plan 22 Task 8 on drives it.

Envelope: `seq` rises from 1 across every kind, `tick` is the frame count (a frame advances it), `wallMs` is the clock
in ms. Frames follow ruling S-6 / P22-3: a full frame every `full_every` frames (frames 1, 11, 21, ... by default) and
after `force_full()`; any other frame elides as `same` each group whose encoding equals the last one sent. `chunk=True`
writes one `state-NNNNNN.log` file per line instead of appending to `state.log`. The command check in `answer` is the
fake mod's own, written against `ACTION_ARGS` and independent of `agent.base.actions`.
"""
import copy
import json
import os
import time

from agent.base import pza1

DEFAULT_FRAME = {
    "gameMin": 480.0,
    "worldAge": 8.0,
    "me": {"x": 100.0, "y": 200.0, "z": 0, "dir": "S", "pace": 0.0, "moving": False, "running": False,
           "sprinting": False, "forceRun": False, "forceSprint": False, "autoWalk": False,
           "zombiesSeen": 0, "zombiesListed": 0, "hour": 8.0, "attackers": 0, "hitReaction": "",
           "dragDown": False, "aiming": False},
    "stats": {"hunger": 0.1, "thirst": 0.1, "fatigue": 0.05, "endurance": 1.0, "panic": 0.0, "pain": 0.0,
              "sickness": 0.0, "wetness": 0.0, "temperature": 37.0},
    "body": {"health": 100.0, "bleeding": 0, "scratched": 0, "bitten": 0, "parts": []},
    "load": {"weight": 4.5, "max": 8.0, "level": 0, "n": 12},
    "weapon": {"type": "Base.BaseballBat", "cond": 0.9, "reach": 1.2, "ammo": None},
    "action": None,
    "act": None,
    "zombies": [],
    "cost": {"tickMs": 0.2, "actMs": 0.05, "senseMs": 0.1, "mapMs": 0.0, "linkMs": 0.05, "tickMaxMs": 0.8,
             "over5": 0, "dropped": 0, "pollMs": 0.0, "startMs": 0.0, "maxActMs": 0.05, "maxSenseMs": 0.1,
             "maxMapMs": 0.0, "maxLinkMs": 0.05, "maxPollMs": 0.0, "maxStartMs": 0.0},
}

DEFAULT_SQUARE = {"x": 100, "y": 200, "z": 0, "solid": False, "solidTrans": False, "light": 1.0, "room": None,
                  "building": None, "door": None, "window": None, "containers": [], "floor": [], "blockN": False,
                  "blockW": False, "edgeN": False, "edgeW": False, "hopN": False, "hopW": False,
                  "water": None}


def square(**fields):
    """A full PZA/1.5 square record: DEFAULT_SQUARE (an open outdoor square, its four edges and its two hop flags
    False, no water) with `fields` laid over it; an unknown field raises."""
    extra = set(fields) - set(pza1.RECORDS["square"])
    if extra:
        raise ValueError("square: unknown fields %s" % sorted(extra))
    out = copy.deepcopy(DEFAULT_SQUARE)
    out.update(copy.deepcopy(fields))
    return out


DEFAULT_HELLO = {"proto": pza1.PROTO, "mod": "fake", "build": "42.21.0", "user": "agent", "rate": 10,
                 "caps": list(pza1.ACTION_TYPES)}

_GROUPS = [f for f, s in pza1.SHAPES["frame"].items() if s[0] == "group"]
_GROUP_AT = {g: pza1.ORDER["frame"].index(g) for g in _GROUPS}
_ENUMS = {"gait": pza1.GAITS, "ikind": pza1.IKINDS, "filter": pza1.FILTERS}


def bad_args(cmd):
    """The fake mod's own check of a cmd line: '' when good, else the act reason."""
    if not isinstance(cmd, dict) or set(cmd) != {"seq", "aid", "type", "args"}:
        return "bad args"
    want = pza1.ACTION_ARGS.get(cmd["type"])
    if want is None:
        return "unknown type"
    args = cmd["args"]
    if not isinstance(args, dict) or set(args) != set(want):
        return "bad args"
    for name, kind in want.items():
        v = args[name]
        if kind == "int":
            ok = isinstance(v, int) and not isinstance(v, bool)
        elif kind == "float":
            ok = isinstance(v, (int, float)) and not isinstance(v, bool)
        else:
            ok = isinstance(v, str) and (kind not in _ENUMS or v in _ENUMS[kind])
        if not ok:
            return "bad args"
    return ""


class FakeMod:
    def __init__(self, state_dir, clock=None, chunk=False, full_every=10):
        self.dir = state_dir
        self.clock = clock or time.time
        self.chunk = chunk
        self.full_every = full_every
        self.seq = 0
        self.tick = 0
        self.wall_ms = 0
        self.last_cmd = None
        self.frames = 0          # frames written
        self.chunks = 0          # chunk files written
        self.scan_id = 1
        self.game_min = DEFAULT_FRAME["gameMin"]
        self._force = False
        self._last = {}          # group -> its last sent encoding
        os.makedirs(state_dir, exist_ok=True)

    # -- the writer ---------------------------------------------------------------------------------------------
    def _emit(self, kind, body, same=()):
        """Stamp the envelope, encode through the schema, write the line; return the keyed line, SAME-free."""
        self.seq += 1
        self.wall_ms = int(round(self.clock() * 1000))
        body = dict(body, seq=self.seq, tick=self.tick, wallMs=self.wall_ms)
        text = pza1.encode(kind, body, same) + "\n"
        if self.chunk:
            self.chunks += 1
            path = os.path.join(self.dir, "state-%06d.log" % self.chunks)
            mode = "w"
        else:
            path = os.path.join(self.dir, "state.log")
            mode = "a"
        with open(path, mode, encoding="utf-8", newline="\n") as f:
            f.write(text)
        return dict(body, kind=kind)

    def raw(self, text):
        """Append raw text to state.log (a partial or malformed line), outside the envelope."""
        with open(os.path.join(self.dir, "state.log"), "a", encoding="utf-8", newline="\n") as f:
            f.write(text)

    # -- the kinds ----------------------------------------------------------------------------------------------
    def hello(self, **fields):
        body = dict(DEFAULT_HELLO, mode="chunk" if self.chunk else "append")
        body.update(fields)
        return self._emit("hello", body)

    def force_full(self):
        self._force = True

    def frame(self, **groups):
        """A frame from DEFAULT_FRAME with `groups` laid over it; a delta elides each group equal to its last sent."""
        body = copy.deepcopy(DEFAULT_FRAME)
        body.update(copy.deepcopy(groups))
        self.frames += 1
        self.tick += 1
        self.game_min = body["gameMin"]
        full = self._force or (self.frames - 1) % self.full_every == 0
        self._force = False
        enc = json.loads(pza1.encode("frame", dict(body, seq=0, tick=0, wallMs=0)))
        now = {g: json.dumps(enc[i]) for g, i in _GROUP_AT.items()}
        same = () if full else tuple(g for g in _GROUPS if self._last.get(g) == now[g])
        self._last = now
        return self._emit("frame", body, same)

    def event(self, kind, **fields):
        body = {"event": kind, "gameMin": fields.pop("gameMin", self.game_min)}
        body.update(fields)
        return self._emit("event", body)

    def death(self, **fields):
        """PZA/1.3's death event (ruling P23-AO), as the Lua writes it before its frame: DEFAULT_FRAME's worldAge,
        position and health, zombiesKilled 0 and via "hook", with `fields` laid over them."""
        me = DEFAULT_FRAME["me"]
        body = {"worldAge": DEFAULT_FRAME["worldAge"], "x": me["x"], "y": me["y"], "z": me["z"],
                "health": DEFAULT_FRAME["body"]["health"], "zombiesKilled": 0, "via": "hook"}
        body.update(fields)
        return self.event("death", **body)

    def map_full(self, squares, scan_id=1, part=1, parts=1, missing=()):
        self.scan_id = scan_id
        return self._emit("map", {"mode": "full", "scanId": scan_id, "part": part, "parts": parts,
                                  "squares": list(squares), "missing": list(missing)})

    def map_delta(self, square):
        return self._emit("map", {"mode": "delta", "scanId": self.scan_id, "part": 1, "parts": 1,
                                  "squares": [square], "missing": []})

    def act(self, aid, state, type, reason="", result=None, snapshot=None):
        if snapshot is None:
            snapshot = {"me": {"x": DEFAULT_FRAME["me"]["x"], "y": DEFAULT_FRAME["me"]["y"], "z": 0, "health": 100.0},
                        "nearest": None}
        return self._emit("act", {"aid": aid, "type": type, "state": state, "reason": reason, "result": result,
                                  "snapshot": snapshot})

    def reply(self, to, body):
        return self._emit("reply", {"to": to, "body": body})

    # -- the command side ---------------------------------------------------------------------------------------
    def answer(self, script=None):
        """Read cmd.txt and answer it: `act rejected` with the reason for a bad command, else one act line per
        scripted state for its type (default accepted then done with an empty result). A script entry is a state
        name or a dict of `act` keywords with `state`. Returns the command dict."""
        with open(os.path.join(self.dir, "cmd.txt"), encoding="utf-8") as f:
            cmd = json.loads(f.read())
        self.last_cmd = cmd
        aid = cmd.get("aid", "") if isinstance(cmd, dict) else ""
        typ = cmd.get("type", "") if isinstance(cmd, dict) else ""
        why = bad_args(cmd)
        if why:
            self.act(aid, "rejected", typ, reason=why)
            return cmd
        for entry in (script or {}).get(typ, ["accepted", "done"]):
            kw = {"state": entry} if isinstance(entry, str) else dict(entry)
            if kw["state"] == "done":
                kw.setdefault("result", {})
            self.act(aid, kw.pop("state"), typ, **kw)
        return cmd
