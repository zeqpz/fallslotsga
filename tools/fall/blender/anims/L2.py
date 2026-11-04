"""L2 Acorn: the nut, its scaly cap riding on it and the little stem riding the cap (tools/fall/parts/L2.py).
The "_rim" layers and "nut_top" ride their part and are never posed themselves.
idle   the cap rocks gently on the nut like a loose lid, the stem wiggles, the nut breathes
land   it drops: the nut squashes, the cap hops up off it and clacks back down, chattering to rest
hit    the nut squats, then the cap POPS straight up off it with a puff, spinning like a coin, while the nut bounces;
       the cap drops back on with a clack and a squash, and jiggles home
multi  the nut trembles harder and harder, the cap lifting and chattering on top of it, the stem buzzing; then it
       pops - the cap shoots up and drops back - with a burst of puffs and sparkles"""
import math

FX = ["puff", "sparkle"]
S = math.sin
TAU = 2 * math.pi
AX = (.51, .86)                                          # the acorn's long axis (nut tip to stem), units


def up(d):
    return dict(x=AX[0] * d, y=AX[1] * d)


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * 2 * t)
        return dict(nut=dict(sx=1 + .01 * b, sy=1 + .015 * b),
                    cap=dict(r=2.2 * S(TAU * t) + .6 * S(TAU * 3 * t)),
                    stem=dict(r=4 * S(TAU * 3 * t) - 2 * S(TAU * t)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: 0)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.0, .3)
        hop = .22 * max(0, S(math.pi * min(1, max(0, t - .03) / .2)))   # the cap hops off and clacks back
        chat = 3 * S(t * 40) * math.exp(-t * 7) * (1 if t > .23 else 0)
        p = up(hop)
        return dict(root=dict(sx=1 + .14 * k, sy=1 - .16 * k),
                    cap=dict(x=p["x"], y=p["y"], r=-4 * hop / .22 + chat),
                    stem=dict(r=-10 * c.damp(max(0, t - .03), 2.6, .25)))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    P0, P1 = 6, 30                                       # the cap's flight

    def pose(i, n):
        u = i / n
        if i <= P0:                                      # squat: the nut squashes, the cap pressed down on it
            e = c.ease_in_out(i / P0)
            return dict(nut=dict(sx=1 + .08 * e, sy=1 - .1 * e), cap=dict(sx=1 + .04 * e, sy=1 - .05 * e),
                        stem=dict(r=-4 * e))
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))
        t = (i - P0) / 30
        p = dict()
        if i < P1:                                       # the cap in the air, spinning like a coin
            s = (i - P0) / (P1 - P0)
            h = 1.15 * 4 * s * (1 - s)
            spin = math.cos(TAU * c.ease_in_out(s))
            q = up(h)
            p["cap"] = dict(x=q["x"], y=q["y"], sx=spin, r=-8 * S(math.pi * s))
            p["stem"] = dict(r=12 * S(t * 18))
        else:                                            # clack: back on, a squash and a jiggle
            tt = (i - P1) / 30
            k = c.damp(tt, 3.2, .3)
            p["cap"] = dict(r=5 * S(tt * 38) * math.exp(-tt * 6) * env, sy=1 - .06 * k * env, sx=1 + .04 * k * env)
            p["stem"] = dict(r=-10 * c.damp(tt, 2.8, .25) * env)
        # the nut: springs up out of its squat, a little hop, then squashed by the cap coming back
        nb = .35 * max(0, S(math.pi * min(1, t / .4)))
        sq = c.damp((i - P1) / 30, 3.0, .3) if i >= P1 else 0
        st = c.damp(t, 3.0, .3) if i < P1 else 0
        p["nut"] = dict(y=nb, sx=1 - .06 * st + .1 * sq * env, sy=1 + .08 * st - .12 * sq * env)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(4):                                   # a puff out of each end of the cap's rim as it leaves
        side = (-1.25, -1.0, 1.0, 1.25)[j]
        x0, z0 = -.2 + side * 3.2 * AX[1], .3 - side * 3.2 * AX[0]
        c.pools["puff"].particle(f0 + P0 + 1 + j % 2, f0 + P0 + 14 + j % 2, lambda t, x0=x0, z0=z0, side=side: (
            x0 + side * 1.1 * AX[1] * c.ease_out(t), z0 - side * 1.1 * AX[0] * c.ease_out(t) + .4 * t), c.rng,
            spin=50, grow=(.6, 1.2), fade=(.7, 0))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 12, f0 + 24, lambda t, a=a: (.6 + math.cos(a) * (2.8 + 1.4 * c.ease_out(t)),
                                    1.6 + math.sin(a) * (2.6 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.7, .05))
    c.glow_curve("hit", lambda u: 0)                    # a halo would hang behind as a grey ghost of the cap


def multi(c):
    R = 26

    def pose(i, n):
        if i < R:                                        # charge: trembling, the cap lifting and chattering
            k = (i / R) ** 1.4
            q = S(i * 3.3) * k
            lift = .22 * k * (.6 + .4 * abs(S(i * 2.1)))
            pp = up(lift)
            return dict(nut=dict(x=.05 * q, sx=1 + .04 * k, sy=1 + .04 * k),
                        cap=dict(x=pp["x"], y=pp["y"], r=5 * S(i * 3.9) * k),
                        stem=dict(r=10 * S(i * 4.4) * k))
        t = (i - R) / 30
        s = min(1, t / .33)                              # the pop: up and back in a third of a second
        h = .9 * 4 * s * (1 - s)
        k = c.damp(max(0, t - .33), 3.2, .3) if t > .33 else 0
        e = 1 - c.ease_in_out(min(1, (i - R) / 6))       # the charge's lift lets go into the pop
        pp = up(h + .22 * e)
        return dict(nut=dict(sx=1 + .08 * k, sy=1 - .1 * k),
                    cap=dict(x=pp["x"], y=pp["y"], r=-10 * S(math.pi * s) + 4 * k),
                    stem=dict(r=14 * c.damp(t, 2.6, .25)))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + R, f0 + R + 12, lambda t: (0, .3), c.rng, grow=(.55, 1.15), fade=(1, 0))
    for j in range(6):
        a = TAU * j / 6 + .3
        c.pools["puff"].particle(f0 + R, f0 + R + 12, lambda t, a=a: (math.cos(a) * (3.2 + 1.3 * c.ease_out(t)),
                                 .3 + math.sin(a) * (3.2 + 1.3 * c.ease_out(t))), c.rng, spin=60, grow=(.5, 1.0),
                                 fade=(.8, 0))
    for j in range(8):
        a = TAU * j / 8 + .1
        c.pools["sparkle"].particle(f0 + R, f0 + R + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    .3 + math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: .4 * min(1, u / .62) if u < .62 else max(0, .4 - (u - .62) / .3))
