"""L8 Cranberry Sauce: the plate, and the can-shaped jelly in three bands - bottom, middle, top cap - each riding the
one under it (tools/fall/parts/L8.py). A band slides and tips over the one below it a beat late, so the jelly sways
like jelly; scaling the bottom band squashes the whole column from where it sits on the plate.
idle   the jelly wobbles gently, the bands swaying out of step, the cap last, the whole column breathing
land   a big jiggly squash: it flattens, bulges, and the wobble runs up the bands and rings out
hit    it squats, BOINGS up off the plate (stretching tall), slaps back down flat and wobbles wildly side to side,
       cranberry drops flicked off the top
multi  it trembles and swells, fatter and fatter, then SPRINGS: shoots up tall and wobbles back down - drops, ring
       and sparks"""
import math

from . import lowkit as K

FX = ["drop", "sparkle"]
S = math.sin
TAU = 2 * math.pi


def imp(t, f, z):
    """a spring knocked at t=0: starts at 0, swings out to ~1 and rings down"""
    if t <= 0:
        return 0.0
    w = TAU * f
    return math.exp(-z * w * t) * S(w * t) / max(.2, math.exp(-z * math.pi / 2))


def wob(a, b, ph=.0):
    """the bands' sway for a lean of a (middle) / b (cap), x in units, r in degrees"""
    return dict(jelly_mid=dict(x=a * .9, r=-a * 5), jelly_top=dict(x=b * 1.1, r=-b * 9))


def idle(c):
    K.track_glow(c)
    K.tint(c, "drop", (.88, .07, .16))                       # the honey drop, cranberry red

    def pose(i, n):
        t = i / n
        sw = lambda f, ph: S(TAU * f * t - ph) + S(ph)                # whole cycles, 0 at the loop's ends
        b = S(TAU * 3 * t)
        p = dict(jelly_lo=dict(sx=1 + .014 * b, sy=1 - .018 * b))
        p.update(wob(.035 * sw(2, .7), .05 * sw(2, 1.5)))
        p["jelly_top"]["sy"] = 1 + .012 * S(TAU * 3 * t - 1.2) + .012 * S(1.2)
        return p
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: 0)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .7) / .3))
        k = c.damp(t, 3.0, .22) * env
        p = dict(root=dict(sx=1 + .06 * k, sy=1 - .06 * k),
                 jelly_lo=dict(sx=1 + .16 * k, sy=1 - .2 * k),
                 plate=dict(sx=1 + .025 * k, sy=1 - .02 * k))
        p.update(wob(.12 * imp(t - .04, 2.6, .2) * env, .2 * imp(t - .08, 2.4, .18) * env))
        p["jelly_top"]["sy"] = 1 - .06 * imp(t - .06, 3, .25) * env
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    T0, UP = 6, 14                                             # squat frames, air frames

    def pose(i, n):
        u = i / n
        if i <= T0:                                            # squat
            e = c.ease_in_out(i / T0)
            p = dict(jelly_lo=dict(sx=1 + .12 * e, sy=1 - .16 * e))
            p.update(wob(-.03 * e, -.05 * e))
            return p
        if i <= T0 + UP:                                       # BOING: up off the plate, tall then round
            a = (i - T0) / UP
            h = S(math.pi * a)
            st = max(0, 1 - a * 2.2)                           # stretched on the way up
            sq0 = 1 - c.ease_in_out(min(1, (i - T0) / 3))      # out of the squat
            p = dict(jelly_lo=dict(y=1.0 * h, sx=1 + .12 * sq0 - .1 * st, sy=1 - .16 * sq0 + .14 * st))
            p.update(wob(.06 * S(a * 9), .12 * S(a * 9 - .8)))
            return p
        t = (i - T0 - UP) / 30                                 # slap down flat, wobble wildly
        env = 1 - c.ease_in_out(max(0, (u - .72) / .28))
        k = c.damp(t, 2.6, .2) * env
        p = dict(jelly_lo=dict(sx=1 + .2 * k, sy=1 - .24 * k), plate=dict(sy=1 - .03 * k, sx=1 + .03 * k),
                 root=dict(sx=1 + .04 * k, sy=1 - .04 * k))
        p.update(wob(.2 * imp(t - .02, 2.8, .14) * env, .32 * imp(t - .06, 2.6, .13) * env))
        p["jelly_top"]["sy"] = 1 - .08 * imp(t - .05, 3.2, .2) * env
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(9):                                         # drops flicked off as it slaps down
        fs = f0 + T0 + UP + 1 + j % 3
        side = -1 if j % 2 else 1
        vx, vz = side * c.rng.uniform(1.6, 3.4), c.rng.uniform(3.0, 5.0)
        x0 = c.rng.uniform(-1.6, 2.4)
        c.pools["drop"].particle(fs, fs + 16, lambda t, vx=vx, vz=vz, x0=x0: (x0 + vx * t, 1.5 + (vz * t - 9 * t * t)),
                                 c.rng, spin=200, grow=(1.0, .7), fade=(1, 1))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 21, f0 + 33, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    R = 20

    def pose(i, n):
        u = i / n
        if i < R:                                              # trembling, swelling fatter
            k = (i / R) ** 1.3
            q = S(i * 2.8) * k
            p = dict(jelly_lo=dict(sx=1 + .1 * k + .015 * q, sy=1 + .05 * k - .015 * q, x=.02 * q))
            p.update(wob(.03 * S(i * 3.3) * k, .045 * S(i * 3.7 + 1) * k))
            return p
        t = (i - R) / 30
        env = 1 - c.ease_in_out(max(0, (u - .72) / .28))
        up = imp(t, 2.2, .3) * env                             # SPRING up tall, then ring down
        p = dict(jelly_lo=dict(sx=1 + .1 * (1 - c.ease_out(min(1, t / .08))) - .1 * up,
                               sy=1 + .05 * (1 - c.ease_out(min(1, t / .08))) + .2 * up, y=.3 * max(0, up)),
                 plate=dict(sx=1 + .02 * up))
        p.update(wob(.14 * imp(t - .05, 2.6, .18) * env, .24 * imp(t - .09, 2.5, .16) * env))
        return p
    c.run("multi", pose)
    f0 = 301 + R
    c.pools["ring"].particle(f0, f0 + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0, f0 + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(8):
        fs = f0 + 2 + j // 2
        vx, vz = c.rng.uniform(-3.2, 3.2), c.rng.uniform(3.5, 5.5)
        c.pools["drop"].particle(fs, fs + 16, lambda t, vx=vx, vz=vz: (.5 + vx * t, 3.2 + (vz * t - 10 * t * t)),
                                 c.rng, spin=220, grow=(1.0, .7), fade=(1, 1))
    c.glow_curve("multi", lambda u: min(1, u / .48) if u < .48 else max(0, 1 - (u - .48) / .4))
