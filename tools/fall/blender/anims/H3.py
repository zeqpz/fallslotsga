"""H3 Cornucopia: the wicker horn (its leaves tucked behind the fruit stay on it), its curled tip, the corn, the apple in
the horn's mouth, the pumpkin, the two red apples (with the red leaf on them), the gold leaf in front and the grapes
(tools/fall/parts/H3.py; the *_fill layers are the plate-painted hidden parts, carried by the fruit above them).
Its character: a horn of plenty that can't hold its harvest in - the fruit is always about to spill.
idle   the fruit bob gently out of step, the grapes sway on their stem, the horn's tip curls and uncurls
land   the horn thumps down, the fruit jostle up in a ripple and settle, the tip whips
hit    the fruit pop out of the horn one after another - apple, corn, pumpkin, apples, grapes - each with a squash
       and stretch, and drop back home; the horn kicks with every pop, leaves flutter out
multi  the horn shakes harder and harder, the fruit rattling in it, then it bursts: everything spills out of the
       mouth at once and bounces home - a ring, sparkles and a gust of leaves"""
import math

FX = ["leaf", "sparkle"]
S = math.sin
TAU = 2 * math.pi


def hop(c, t, h, T=.4, dx=0.0):
    """one pop: a quick squat, a flight of h units (T s), a squashed landing that springs out. t s from its start."""
    if t <= 0:
        return {}
    if t < .1:
        a = .1 * S(math.pi * t / .1)
        return dict(sx=1 + a, sy=1 - a)
    if t < .1 + T:
        u = (t - .1) / T
        s = .13 * (1 - 2 * u)
        return dict(x=dx * S(math.pi * u), y=h * 4 * u * (1 - u), sx=1 - .6 * s, sy=1 + s)
    k = c.damp(t - .1 - T, 4.0, .3)
    return dict(sx=1 + .1 * k, sy=1 - .13 * k)


def faded(p, env):
    """a pose's channels eased toward rest by env (1 = as is, 0 = rest)"""
    return {k: (v - 1) * env + 1 if k in ("sx", "sy") else v * env for k, v in p.items()}


def idle(c):
    def pose(i, n):
        t = i / n
        return dict(horn=dict(sy=1 + .006 * S(TAU * 2 * t)),
                    horn_tip=dict(r=2.4 * S(TAU * t)),
                    corn=dict(r=-1.6 * S(TAU * t), sy=1 + .02 * S(TAU * 2 * t) ** 2),
                    apple_top_fill=dict(y=.035 * S(TAU * 2 * t + 0) ** 2 * (1 if S(TAU * 2 * t) > 0 else 0)),
                    pumpkin_fill=dict(sx=1 - .012 * S(TAU * 3 * t), sy=1 + .018 * S(TAU * 3 * t)),
                    apples_fill=dict(y=.03 * max(0, S(TAU * 2 * t + math.pi)) ** 2, r=.8 * S(TAU * t)),
                    grapes=dict(r=2.2 * S(TAU * 2 * t)),
                    leaf_front=dict(r=-2.0 * S(TAU * 3 * t)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.2, .3)
        p = dict(root=dict(sx=1 + .13 * k, sy=1 - .15 * k),
                 horn_tip=dict(r=-8 * c.damp(max(0, t - .03), 3.0, .25)))
        for name, d in (("apple_top_fill", .02), ("corn", .05), ("pumpkin_fill", .08), ("apples_fill", .11),
                        ("grapes", .14)):
            j = .16 * max(0, S(math.pi * min(1, max(0, t - d) / .18)))
            p[name] = dict(y=j * (.6 if name == "corn" else 1))
        p["grapes"]["r"] = 6 * S(t * 26) * math.exp(-t * 6)
        p["leaf_front"] = dict(r=7 * S(t * 30) * math.exp(-t * 7))
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    order = (("apple_top_fill", 2, .55, -.1), ("corn", 7, .35, -.15), ("pumpkin_fill", 12, .5, -.2),
             ("apples_fill", 17, .5, -.25), ("grapes", 22, .55, .05))

    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))            # everything home by the end
        p = {}
        kick = 0
        for name, f, h, dx in order:
            t = (i - f) / 30
            q = hop(c, t, h, .4, dx)
            if name == "corn":                                     # the corn springs on its hidden butt: a lean
                q = dict(sx=q.get("sx", 1), sy=q.get("sy", 1) + .5 * q.get("y", 0), r=18 * q.get("y", 0),
                         y=.25 * q.get("y", 0))
            p[name] = faded(q, env)
            if 0 < t < .3:
                kick += S(math.pi * t / .3) * (1 if f % 2 else -1)
        p["grapes"]["r"] = 10 * S(max(0, i - 22) / 30 * 18) * math.exp(-max(0, i - 22) / 30 * 3) * env
        p["horn"] = dict(r=1.6 * kick * env, sy=1 - .02 * abs(kick) * env)
        p["horn_tip"] = dict(r=6 * S(u * TAU * 2) * env)
        p["leaf_front"] = dict(r=9 * S(i * .7) * math.exp(-max(0, i - 20) / 10) * (i > 20) * env)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(7):                                             # leaves shaken out of the horn's mouth
        fs = f0 + 6 + 3 * j
        x0, vx = c.rng.uniform(-1.6, .4), c.rng.uniform(-2.8, -.6)
        c.pools["leaf"].particle(fs, fs + 22, lambda t, x0=x0, vx=vx: (x0 + vx * t + .4 * S(t * 9), 1.2 + 2.6 * t - 3.2 * t * t),
                                 c.rng, spin=240, grow=(.5, .45), fade=(1, 0))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    # where each piece spills to (units): out of the mouth, down and to the left
    spill = dict(apple_top_fill=(-.35, .55, 14), corn=(-.2, .25, 22), pumpkin_fill=(-.45, .45, -8),
                 apples_fill=(-.55, .35, 16), grapes=(-.15, .3, -16), leaf_front=(-.35, -.05, 25))

    def pose(i, n):
        if i < 18:                                                 # the horn shakes, the fruit rattle in it
            k = (i / 18) ** 1.4
            q = S(i * 2.8) * k
            p = dict(horn=dict(x=.06 * q, r=2.5 * q, sx=1 + .03 * k, sy=1 + .03 * k), horn_tip=dict(r=7 * S(i * 3.3) * k))
            for j, name in enumerate(spill):
                p[name] = dict(y=.05 * abs(S(i * 3.1 + j * 1.7)) * k, r=3 * S(i * 3.7 + j) * k)
            return p
        t = (i - 18) / 30
        out = max(0, S(math.pi * min(1, t / .45)))                 # out and back in in 0.45 s
        land = c.damp(max(0, t - .45), 3.6, .3) if t > .45 else 0
        fade = 1 - c.ease_in_out(min(1, max(0, (i - 34) / 8)))
        ramp = min(1, (i - 17) / 3)
        p = dict(horn=dict(r=-4 * out * ramp, sx=1 + .06 * out, sy=1 - .04 * out + .03 * land * fade),
                 horn_tip=dict(r=-12 * out + 5 * land * fade))
        for name, (dx, dy, rr) in spill.items():
            p[name] = dict(x=dx * out, y=dy * out, r=rr * out, sx=1 + .08 * land * fade, sy=1 - .1 * land * fade)
        return p
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(9):
        fs = f0 + 18 + j
        a = c.rng.uniform(1.9, 3.6)
        sp = c.rng.uniform(3, 4.5)
        c.pools["leaf"].particle(fs, fs + 20, lambda t, a=a, sp=sp: (-1 + math.cos(a) * sp * t, .5 + math.sin(a) * sp * t - 2 * t * t),
                                 c.rng, spin=300, grow=(.55, .4), fade=(1, 0))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))
