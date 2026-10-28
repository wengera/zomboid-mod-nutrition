"""The session's record: what `Session.save` writes under out["loop"] and a death under out["loop"]["death"].

loop_summary(session) -> {wallS, ticks, decisions, last_decisions, needs, needs_fields, needs_pairs, fights, actions,
lua_errors_per_min, cost {n, p50, p99, max, tickMaxMs, over5}, server_polls, server_fails, players_error, memory,
damage {polls, fails, since, merged, lost, dropped, counts, totals {tag: {n, amount}}}, first_game_min, game_min,
last_frames, poll_errors}: `last_frames` the last LAST_FRAMES frames (the chain's lineage reads the last one),
`poll_errors` the PollThread's errors when the session runs one.

death_record(session, via, detail) -> {via ("frame" | "players"), detail, wallS, gameMin, frame (the death frame or
None), last_decisions, last_frames, server_damage (the server's records, with their i and server wall, whose wall (else
the merge's wallMs) lies within DEATH_WINDOW_S before the client's clock at the stop), client_damage (the World's
client records in the same window), window_ms {from, to}}, after a last `damage.watch since` read (guarded: a dead bus
keeps what was merged), so the records up to the death are merged. gates.grade_d's death_check reads it.

Clocks: `*S` keys are the driver's clock in seconds since the loop began; a line's wallMs is the client's clock (ms).
"""
from agent.base import gates as GT

NEEDS_FIELDS = ["gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger"]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def in_window(t, lo, hi):
    return _num(t) is not None and lo <= t <= hi


def action_rows(sent, t0):
    """Every sent Action as {aid, type, args, state, reason, sentS, endedS}, its times in seconds since t0."""
    t0 = t0 or 0.0
    return [{"aid": a.aid, "type": a.type, "args": dict(a.args), "state": a.state, "reason": a.reason,
             "sentS": a.sent_wall - t0, "endedS": a.ended_wall - t0 if a.ended_wall is not None else None}
            for a in sent]


def loop_summary(session):
    s = session
    ts = s.ticks_ms
    return {
        "wallS": s.loop_s(), "ticks": s.ticks, "decisions": len(s.sent),
        "last_decisions": s.tail.last(), "needs": list(s.needs), "needs_fields": list(NEEDS_FIELDS),
        "needs_pairs": list(s.needs_pairs), "fights": [dict(f) for f in s.fights.rows],
        "actions": action_rows(s.sent, s.t_loop0), "lua_errors_per_min": dict(s.err_per_min),
        "cost": {"n": len(ts), "p50": GT.pct(ts, 50), "p99": GT.pct(ts, 99), "max": max(ts) if ts else None,
                 "tickMaxMs": s.tick_max, "over5": s.over5},
        "server_polls": s.server_polls, "server_fails": s.server_fails,
        "players_error": s.players_error, "memory": list(s.mem_rows),
        "damage": dict(s.damage, totals={k: dict(v) for k, v in s.damage["totals"].items()}),
        "first_game_min": s.first_game_min, "game_min": s.world.game_min,
        "last_frames": list(s.frames),
        "poll_errors": list(s.polls.errors) if s.polls is not None else None}


def death_record(session, via, detail):
    s = session
    try:
        s.damage_poll()
    except Exception as e:                           # noqa: BLE001 - the record is written whatever the bus does
        s.damage["final_error"] = "%s: %s" % (type(e).__name__, e)
    s.tail.read()
    hi = (s.client_now if s.client_now is not None else s.clock()) * 1000.0
    lo = hi - s.lim["DEATH_WINDOW_S"] * 1000.0
    server = [dict(r) for r in s.server_records
              if in_window(r["wall"] if _num(r.get("wall")) is not None else r["wallMs"], lo, hi)]
    client = [dict(r) for r in s.world.damage
              if r.get("side") != "server" and in_window(r.get("wallMs"), lo, hi)]
    return {"via": via, "detail": detail, "wallS": s.loop_s(), "gameMin": s.world.game_min,
            "frame": s.death_frame, "last_decisions": s.tail.last(), "last_frames": list(s.frames),
            "server_damage": server, "client_damage": client, "window_ms": {"from": lo, "to": hi}}
