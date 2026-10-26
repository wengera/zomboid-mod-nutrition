"""A short deterministic text digest of a World, for the model's context (at most 25 lines)."""


def _f(v):
    return "%.1f" % v if isinstance(v, (int, float)) else "?"


def summarize(world):
    me = world.me
    out = ["position: %s,%s,%s" % (_f(me.get("x")), _f(me.get("y")), me.get("z", "?")),
           "game time: minute %s of day, world age %sh" % (me.get("gameMin", "?"), _f(me.get("worldAge"))),
           "needs: hunger %s thirst %s fatigue %s health %s" % tuple(
               _f(me.get(k)) for k in ("hunger", "thirst", "fatigue", "health"))]
    g = world.goal
    out.append("goal: %s (%s) %s" % (g.get("name"), g.get("state"), g.get("detail", "")) if g else "goal: none")
    zs = list(world.zombies.values())
    out.append("threats: %d (nearest %s)" % (len(zs), _f(min(z["dist"] for z in zs))) if zs else "threats: 0")
    for key in sorted(world.containers)[:5]:
        c = world.containers[key]
        out.append("container %s at %d,%d: %d items%s" % (c["type"], key[0], key[1], len(c["items"]),
                                                          " (looted)" if c["looted"] else ""))
    e = world.unexplored_edge()
    out.append("unexplored edge: %d,%d" % e if e else "unexplored edge: none")
    for ev in list(world.events)[-3:]:
        out.append("event: %s at %s" % (ev.get("event"), ev.get("wallMs")))
    return "\n".join(out)
