"""L1 Maple Leaf: the middle of the leaf, its five lobes (top, left, right, two small lower ones) and the stem
(tools/fall/parts/L1.py). The "_rim" layers ride their part and are never posed themselves.
idle   it sways on its stem, the lobes fluttering in the breeze, each out of step with the others
land   it settles like a leaf: the lobes flop down and float back up, a gentle squash
hit    it curls in, then a gust catches it: it lifts and floats back down while a ripple runs round its lobes one
       after another and the stem flicks, loose leaves blown off sideways (no turning over: owner, 2026-11-04)
multi  it trembles, the lobes curling in tighter and tighter, then springs wide open - lobes flung out - with a gust
       of leaves"""
import math

FX = ["leaf", "sparkle"]
S = math.sin
TAU = 2 * math.pi
# a lobe's "out / down" sense of turn (the left lobe droops turning anticlockwise, the right one clockwise ...)
OUT = dict(left=1, right=-1, top=1, low_l=1, low_r=-1)


def idle(c):
    def pose(i, n):
        t = i / n
        return dict(mid=dict(r=2.4 * S(TAU * t)),
                    left=dict(r=-2.6 * S(TAU * 2 * t)),
                    right=dict(r=2.4 * S(TAU * 3 * t)),
                    top=dict(r=-1.6 * S(TAU * 2 * t) + .8 * S(TAU * t)),
                    low_l=dict(r=2.0 * S(TAU * 3 * t)),
                    low_r=dict(r=-2.0 * S(TAU * 2 * t)),
                    stem=dict(r=-1.5 * S(TAU * t)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: 0)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 2.6, .35)
        lag = c.damp(max(0, t - .03), 2.0, .3)
        p = dict(root=dict(sx=1 + .12 * k, sy=1 - .15 * k), stem=dict(r=-8 * lag))
        for b, a in (("left", 14), ("right", 14), ("top", 4), ("low_l", 9), ("low_r", 9)):
            p[b] = dict(r=OUT[b] * a * lag)
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    ORDER = ("low_l", "left", "top", "right", "low_r")      # the gust runs round the leaf, lobe by lobe

    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))
        if i <= 6:                                           # it curls in against the gust
            e = c.ease_in_out(i / 6)
            p = dict(root=dict(sy=1 - .05 * e, sx=1 + .03 * e), mid=dict(sy=1 - .03 * e), stem=dict(r=-5 * e))
            for b in ORDER:
                p[b] = dict(r=-OUT[b] * 6 * e)
            return p
        t = (i - 6) / 30
        lift = S(math.pi * min(1, t / 1.0))                  # it lifts on the gust and floats back down
        rel = 1 - c.ease_out(min(1, t / .15))
        p = dict(root=dict(y=.35 * lift * env, r=2.5 * S(TAU * .9 * t) * lift * env,
                           sx=1 + .03 * S(t * 9) * lift * env, sy=1 - .03 * S(t * 9) * lift * env),
                 mid=dict(r=2 * S(t * 7) * lift * env),
                 stem=dict(r=(-5 * rel + 12 * S(t * 14) * math.exp(-t * 2)) * env))
        for k, b in enumerate(ORDER):                        # each lobe flaps up a beat after the one before
            w = S(t * 13 - k * .9) * max(0, min(1, t * 5 - k * .5)) * math.exp(-t * 1.2)
            p[b] = dict(r=(-OUT[b] * 6 * rel + OUT[b] * 9 * w) * env)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(8):                                   # loose leaves whirl off as it turns
        fs = f0 + 6 + 2 + j * 2
        a0 = TAU * j / 8 + .3
        c.pools["leaf"].particle(fs, fs + 22, lambda t, a0=a0: (          # blown off sideways on the gust
            -3.2 + 6.4 * c.ease_out(t) + .5 * math.sin(a0 + 6 * t), 2.6 * math.sin(a0) + .8 * math.sin(t * 7) - .8 * t),
            c.rng, spin=c.rng.choice((-1, 1)) * 320, grow=(.45, .7), fade=(1, 0))
    for j in range(5):
        a = TAU * j / 5 + .7
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    .2 + math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.7, .05))
    c.glow_curve("hit", lambda u: .5 * S(math.pi * u) ** 2)


def multi(c):
    R = 24

    def pose(i, n):
        if i < R:                                        # trembling, the lobes curling in tighter
            k = (i / R) ** 1.4
            q = S(i * 3.1) * k
            p = dict(mid=dict(x=.04 * q, r=1.6 * S(i * 2.6) * k), stem=dict(r=4 * S(i * 3.9) * k))
            for j, b in enumerate(("left", "right", "top", "low_l", "low_r")):
                p[b] = dict(r=-OUT[b] * 9 * k + 2 * S(i * 3.4 + j) * k, sx=1 - .1 * k, sy=1 - .1 * k)
            return p
        t = (i - R) / 30
        k = c.damp(t, 2.6, .3)
        p = dict(root=dict(sx=1 + .07 * k, sy=1 + .07 * k), stem=dict(r=-6 * k))
        for j, b in enumerate(("left", "right", "top", "low_l", "low_r")):
            kk = c.damp(max(0, t - .02 * j), 2.6, .28)
            p[b] = dict(r=OUT[b] * 10 * kk, sx=1 + .1 * kk, sy=1 + .1 * kk)
        return p
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + R, f0 + R + 12, lambda t: (0, .2), c.rng, grow=(.55, 1.15), fade=(1, 0))
    for j in range(10):                                  # a gust of leaves bursting out
        a = TAU * j / 10 + .15
        sp = c.rng.uniform(2.6, 3.4)
        c.pools["leaf"].particle(f0 + R + (j % 2), f0 + R + 16 + (j % 2), lambda t, a=a, sp=sp: (
            math.cos(a) * (1.2 + sp * c.ease_out(t)), .2 + math.sin(a) * (1.2 + sp * c.ease_out(t)) - .8 * t * t),
            c.rng, spin=c.rng.choice((-1, 1)) * 300, grow=(.5, .75), fade=(1, .1))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + R, f0 + R + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    .2 + math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: .8 * min(1, u / .57) if u < .57 else max(0, .8 - (u - .57) / .45))


# ---------------------------------------------------------------- pop: a gust tears it to bits and carries them off
# strain  it leans into a rising wind, its lobes curling in and shivering; wind lines begin to streak past
# BLOW    the gust hits: the leaf tears into ragged bits that peel off from the windward side one after another and
#         are whirled away down the wind, fluttering and dwindling, with specks and small leaves among the wind lines
from . import popkit as P                                      # noqa: E402

XFX = {
    "gust": dict(files=["parts:fx_gust"], n=9, size=5.0),
    "speck": dict(files=["parts:fx_speck"], n=14, size=.9),
    "leaflet": dict(files=["leaf_red", "leaf_orange"], n=5, size=1.5),
}
CURL = dict(top=1, left=1, right=-1, low_l=1, low_r=-1)


def pop(c):
    B = P.BLOW
    bits = [b for b in c.extras if b.startswith("bit")]
    xs = [c.pivot[b][0] for b in bits]
    lo, hi = min(xs), max(xs)
    R = {b: (B + 4.0 * (c.pivot[b][0] - lo) / (hi - lo), c.rng.uniform(0, 6.28),
             c.rng.choice((-1, 1)) * c.rng.uniform(280, 520), c.rng.uniform(.8, 1.25)) for b in bits}

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            env = k * (1 - P.st(i, 6, 8))
            p = dict(root=P.swell(1 + .1 * k, x=-.3 * k + .05 * S(i * 3.2) * k), stem=dict(r=-10 * env))
            for l, sg in CURL.items():
                p[l] = dict(r=sg * 10 * env + 5 * S(i * 3.6 + sg) * env)
            return p
        p = dict(root=P.swell(1.1, x=-.3), mid=dict(a=0))
        for b in bits:
            r0, ph, sp, v = R[b]
            if i < r0:                                         # still holding on, shaking
                p[b] = dict(a=1, x=.05 * S(i * 4 + ph), r=4 * S(i * 5 + ph))
            else:
                t = (i - r0) / 30
                z = max(.35, 1 - 1.1 * t)
                p[b] = dict(a=P.gone(i, 20, 24), x=v * (12 * t + 16 * t * t),
                            y=(3 + 5 * S(ph * 3)) * t + 1.3 * S(9 * t + ph) * min(1, 4 * t), r=sp * t,
                            sx=z * (.3 + .7 * abs(P.C(11 * t + ph))), sy=z)
        return p
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    for j in range(9):                                         # the wind
        f = 3 + int(j * 1.7)
        z0, w = rng.uniform(-3.6, 3.6), rng.uniform(.9, 1.5)
        fx["gust"].emit(f, f + 6, lambda t, z0=z0: (-7.5 + 15 * t, z0 + .5 * S(5 * t)), rot=0,
                        grow=lambda t, w=w: (w * (.6 + .8 * S(math.pi * t)), .5), fade=lambda t: S(math.pi * t) ** .7)
    P.burst(fx["speck"], rng, B, 14, at=(-.5, 0), speed=(14, 26), ang=(-8, 34), g=5, life=(10, 14), grow=(1.0, .6),
            spin=700, stagger=.5, spread=2.8, drag=.6)
    P.burst(fx["leaflet"], rng, B + 1, 5, at=(0, 0), speed=(12, 18), ang=(0, 30), g=4, life=(12, 15),
            grow=(.7, .4), spin=500, stagger=1.2, spread=2.2, drag=.5)
    c.glow_out(lambda i: .2 + .5 * P.strain(i) if i < B else .8 if i == B else 0.0)
