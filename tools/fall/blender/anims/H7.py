"""H7 Pumpkin: the body, its stem, and the curly vine and the leaf hanging off the stem (tools/fall/parts/H7.py).
The "_rim" layers and "top" ride their part and are never posed themselves.
idle   a heavy, slow breath; the vine's curl springs gently in and out like a coil, the leaf flutters, the stem nods
land   a heavy THUD: a big squash that wobbles out, the stem whips over and back, the vine and leaf flail after it
hit    it bounces like a ball - squat, big hop with a stretch, squash, a smaller hop, squash, settle - the stem
       whipping and the vine and leaf flapping with every bounce, a few leaves shaken loose
multi  it swells and squeezes, wobbling like it's about to burst, the stem quivering; then it lets go - shrinks back
       with a puff, the stem, vine and leaf flung out and springing home"""
import math

FX = ["leaf", "puff", "sparkle"]
S = math.sin
TAU = 2 * math.pi


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * t)                                   # one slow heavy breath a loop
        coil = S(TAU * 2 * t)
        return dict(body=dict(sx=1 + .014 * b, sy=1 + .02 * b),
                    stem=dict(r=-1.2 * S(TAU * t) + .4 * S(TAU * 3 * t)),
                    vine=dict(r=3.0 * coil, sx=1 - .035 * coil),
                    leaf=dict(r=2.4 * S(TAU * 3 * t) + 1.2 * S(TAU * 2 * t)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .08 * S(TAU * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 2.4, .22)                          # heavy: a slow, deep squash that wobbles out
        lag = c.damp(max(0, t - .05), 2.0, .2)
        lag2 = c.damp(max(0, t - .09), 2.0, .2)
        return dict(root=dict(sx=1 + .16 * k, sy=1 - .2 * k),
                    stem=dict(r=-14 * lag), vine=dict(r=18 * lag2, sx=1 - .08 * lag2),
                    leaf=dict(r=-16 * lag2))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def bounce(i):
    """the hit's bounces: height (units), and the contact squash, from the frame"""
    if i < 6:
        return 0.0, c_ease(i / 6) * .9                   # squat
    if i < 20:
        s = (i - 6) / 14
        return .75 * 4 * s * (1 - s), 0.0                 # big hop
    if i < 30:
        s = (i - 20) / 10
        return .28 * 4 * s * (1 - s), 0.0                 # small hop
    return 0.0, 0.0


def c_ease(t):
    return t * t * (3 - 2 * t)


def hit(c):
    def pose(i, n):
        u = i / n
        h, squat = bounce(i)
        t = i / 30
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        # squash after each contact (frame 20, 30), stretch while rising
        sq = 0.0
        for fc, a in ((20, .9), (30, .55)):
            if i >= fc:
                sq += a * max(0, c.damp((i - fc) / 30, 3.0, .35))
        vy = 0.0
        if 6 <= i < 20:
            vy = (1 - 2 * (i - 6) / 14)
        elif 20 <= i < 30:
            vy = .5 * (1 - 2 * (i - 20) / 10)
        st = .09 * abs(vy)
        sx = 1 + .12 * squat + .18 * sq - st * .7
        sy = 1 - .14 * squat - .2 * sq + st
        # the stem whips with each kick: takeoff (6), landings (20, 30)
        w = 0.0
        for fe, a in ((6, 16), (20, -20), (30, 12)):
            if i >= fe:
                w += a * c.damp((i - fe) / 30, 2.2, .22) * min(1, (i - fe) / 2)
        w2 = 0.0
        for fe, a in ((7, 22), (21, -26), (31, 16)):
            if i >= fe:
                w2 += a * c.damp((i - fe) / 30, 2.0, .2) * min(1, (i - fe) / 2)
        return dict(body=dict(y=h, sx=1 + (sx - 1) * env, sy=1 + (sy - 1) * env, r=3 * S(t * 9) * min(1, h * 3)),
                    stem=dict(r=w * env), vine=dict(r=w2 * env, sx=1 - .004 * abs(w2) * env),
                    leaf=dict(r=(-w2 * .8 + 8 * S(t * 30) * min(1, h * 2)) * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(4):                                   # leaves shaken loose on the big landing, fluttering off
        fs = f0 + 20 + j * 2
        side = -1 if j % 2 else 1
        x0 = .9 + side * .6
        dx = side * c.rng.uniform(2.2, 3.2)
        c.pools["leaf"].particle(fs, fs + 22, lambda t, x0=x0, dx=dx: (x0 + dx * c.ease_out(t) + .3 * math.sin(t * 10),
                                 3.0 + 2.2 * t - 4.2 * t * t), c.rng, spin=c.rng.choice((-1, 1)) * 260,
                                 grow=(.6, .8), fade=(1, 0))
    for j in range(4):                                   # dust puffs kicked out where it lands
        side = -1 if j % 2 else 1
        fs = f0 + 20 + (j // 2) * 10
        c.pools["puff"].particle(fs, fs + 12, lambda t, side=side: (side * (3.0 + 1.4 * c.ease_out(t)), -4.0 + .5 * t),
                                 c.rng, spin=40, grow=(.6, 1.3), fade=(.6, 0))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 12, f0 + 24, lambda t, a=a: (math.cos(a) * (3.6 + 1.2 * c.ease_out(t)),
                                    .4 + math.sin(a) * (3.6 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .85)) if u < .85 else 0)


def multi(c):
    R = 26

    def pose(i, n):
        if i < R:                                        # swelling and squeezing, faster and harder
            k = (i / R) ** 1.5
            ph = 1.4 * i + .02 * i * i                   # the wobble quickens
            w = S(ph)
            q = S(i * 3.3) * k
            return dict(body=dict(x=.03 * q, sx=1 + .1 * k + .05 * k * w, sy=1 + .1 * k - .05 * k * w),
                        stem=dict(r=5 * S(i * 3.7) * k), vine=dict(r=7 * S(i * 2.9 + 1) * k, sx=1 - .05 * k * w),
                        leaf=dict(r=6 * S(i * 3.1 + 2) * k))
        t = (i - R) / 30
        k = c.damp(t, 2.6, .3)
        e = 1 - c.ease_in_out(min(1, (i - R) / (n - R)))
        return dict(body=dict(sx=1 + .1 * e * k, sy=1 + .1 * e * k),
                    stem=dict(r=14 * k), vine=dict(r=-24 * c.damp(max(0, t - .04), 2.4, .25)),
                    leaf=dict(r=-20 * c.damp(max(0, t - .03), 2.5, .25)))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + R, f0 + R + 12, lambda t: (0, -.3), c.rng, grow=(.55, 1.15), fade=(1, 0))
    for j in range(6):                                   # the release: a puff all round
        a = TAU * j / 6 + .5
        c.pools["puff"].particle(f0 + R, f0 + R + 12, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                 -.3 + math.sin(a) * (3.0 + 1.2 * c.ease_out(t))), c.rng, spin=60, grow=(.5, 1.0),
                                 fade=(.85, 0))
    for j in range(8):
        a = TAU * j / 8 + .2
        c.pools["sparkle"].particle(f0 + R, f0 + R + 12, lambda t, a=a: (math.cos(a) * (3.8 + 1.4 * c.ease_out(t)),
                                    -.3 + math.sin(a) * (3.8 + 1.4 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(4):                                   # leaves flung off the top
        side = 1 if j % 2 else -1
        dx = side * c.rng.uniform(2.4, 3.4)
        c.pools["leaf"].particle(f0 + R + 1 + j, f0 + R + 17 + j, lambda t, dx=dx: (
            .9 + dx * c.ease_out(t), 3.0 + 2.0 * t - 3.6 * t * t), c.rng, spin=260, grow=(.6, .8), fade=(1, 0))
    c.glow_curve("multi", lambda u: min(1, (u / .62) ** 1.4) if u < .62 else max(0, 1 - (u - .62) / .33))
