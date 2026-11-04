"""L1 Maple Leaf: the middle of the leaf, its five lobes (top, left, right, two small lower ones) and the stem
(tools/fall/parts/L1.py). The "_rim" layers ride their part and are never posed themselves.
idle   it sways on its stem, the lobes fluttering in the breeze, each out of step with the others
land   it settles like a leaf: the lobes flop down and float back up, a gentle squash
hit    it curls up, then flips right over about its stem - a full twirl with a little lift - its lobes flapping,
       loose leaves whirling off it, and it rocks to rest
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
    T0, T1 = 6, 36                                       # the twirl

    def pose(i, n):
        if i <= T0:                                      # curl up: the lobes lift, it dips
            e = c.ease_in_out(i / T0)
            p = dict(root=dict(sy=1 - .06 * e, sx=1 + .04 * e))
            for b, a in (("left", 7), ("right", 7), ("top", 0), ("low_l", 4), ("low_r", 4)):
                p[b] = dict(r=-OUT[b] * a * e)
            return p
        if i <= T1:
            s = (i - T0) / (T1 - T0)
            f = c.ease_in_out(s)
            air = S(math.pi * s)
            t = (i - T0) / 30
            p = dict(root=dict(sx=math.cos(TAU * f), y=.55 * air, r=10 * S(TAU * f) * .8),
                     stem=dict(r=10 * S(t * 16) * air))
            e = 1 - min(1, s / .15)                      # the curl lets go as it starts to turn
            for k, (b, a) in enumerate((("left", 8), ("right", 8), ("top", 0), ("low_l", 5), ("low_r", 5))):
                p[b] = dict(r=-OUT[b] * a * e + 8 * S(t * 22 + k * 1.3) * air)
            return p
        t = (i - T1) / 30                                # rock to rest
        k = c.damp(t, 2.4, .35)
        env = (1 - c.ease_in_out((i - T1) / (n - T1))) * (1 - math.exp(-t * 12))   # eases in from the twirl
        p = dict(mid=dict(r=6 * k * env), root=dict(sx=1 + .05 * k * env, sy=1 - .06 * k * env))
        for j, b in enumerate(("left", "right", "top", "low_l", "low_r")):
            p[b] = dict(r=OUT[b] * 7 * c.damp(max(0, t - .03 * j), 2.6, .3) * env)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(8):                                   # loose leaves whirl off as it turns
        fs = f0 + T0 + 2 + j * 2
        a0 = TAU * j / 8 + .3
        c.pools["leaf"].particle(fs, fs + 22, lambda t, a0=a0: (
            math.cos(a0 + 2.2 * t) * (2.2 + 2.4 * c.ease_out(t)), .3 + math.sin(a0 + 2.2 * t) * (2.2 + 2.0 * c.ease_out(t)) - 1.2 * t * t),
            c.rng, spin=c.rng.choice((-1, 1)) * 320, grow=(.45, .7), fade=(1, 0))
    for j in range(5):
        a = TAU * j / 5 + .7
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    .2 + math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.7, .05))
    c.glow_curve("hit", lambda u: 0)                    # the halo would hang behind as a grey leaf while it turns


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
