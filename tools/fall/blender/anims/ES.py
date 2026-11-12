"""ES Extreme Free Spins badge: the jack-o'-lantern (with its flames) at the back, the crow perched on it, and the X,
the F and the S on its face (tools/fall/parts/ES.py).
The owner wants the bonus icons' motion VERY subtle and slow: small amplitudes, long smooth curves, nothing snappy.
idle   the jack breathes once a loop, the crow bobs and cocks its body a hair, the three letters ripple gently in
       turn; one ember-leaf rises off the flames
land   it settles: a small soft squash, the crow dips on its perch and comes back, the letters lag a touch
hit    a slow menacing swell: the jack grows a little, the crow rises and leans in, the X, F, S lift one after the
       other in a wave; ember-leaves rise off the flames and a couple of feathers drift
multi  a faint tremble as it gathers itself (the crow hunching), then a soft burst: letters lift, the crow rises,
       rays and a ring spread, ember-leaves fly out, and it eases home"""
import math

FX = ["sparkle", "leaf", "feather"]
S, C = math.sin, math.cos
TAU = 2 * math.pi
LETTERS = ("let_x", "let_f", "let_s")


def st(i, a, b):
    """0 before frame a, 1 after frame b, a smooth step between"""
    u = min(1.0, max(0.0, (i - a) / (b - a)))
    return u * u * (3 - 2 * u)


def ember(c, f, x0, n=26, rise=3.0, drift=.4, size=(.35, .2)):
    """a burning leaf lifting off the flames, swaying, fading"""
    sg = 1 if x0 > 0 else -1
    c.pools["leaf"].particle(f, f + n, lambda t: (x0 + sg * drift * t + .2 * S(t * 6), .6 + rise * t), c.rng,
                             spin=90, grow=size, fade=(.9, 0))


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * t)                                          # one slow breath a loop (2.4 s)
        return dict(jack=dict(sx=1 + .004 * b, sy=1 + .006 * b),
                    crow=dict(y=.02 * S(TAU * 2 * t), r=.7 * S(TAU * t)),
                    let_x=dict(y=.02 * S(TAU * t)), let_f=dict(y=.016 * S(TAU * 2 * t)), let_s=dict(y=-.02 * S(TAU * t)))
    c.run("idle", pose)
    ember(c, 1 + 20, -3.6, n=34, rise=2.4, size=(.3, .15))
    c.glow_curve("idle", lambda u: .08 * S(math.pi * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        env = 1 - c.ease_in_out(max(0, (i / n - .7) / .3))
        k = c.damp(t, 2.4, .45)
        lag = c.damp(max(0, t - .05), 2.0, .45)
        p = dict(root=dict(sx=1 + .06 * k * env, sy=1 - .07 * k * env),
                 crow=dict(y=-.06 * lag * env, r=-1.5 * lag * env))
        for j, b in enumerate(LETTERS):
            p[b] = dict(y=-.045 * c.damp(max(0, t - .02 * j), 2.0, .45) * env)
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: -.15 * max(0, 1 - u / .4))


def hit(c):
    def pose(i, n):
        up = st(i, 0, 18) * (1 - st(i, 28, 46))                 # a slow rise and a slow settle
        p = dict(jack=dict(sx=1 + .035 * up, sy=1 + .04 * up),
                 crow=dict(y=.14 * up, r=-3 * up + 1.2 * S(TAU * i / 23) * up, sx=1 + .02 * up, sy=1 + .03 * up))
        for j, b in enumerate(LETTERS):                         # the wave: X, then F, then S
            w = S(math.pi * min(1, max(0, (i - 4 - 6 * j) / 24)))
            p[b] = dict(y=.13 * w, sx=1 + .03 * w, sy=1 + .03 * w, r=(2, 0, -2)[j] * w)
        return p
    c.run("hit", pose)
    f0 = 201
    for f, x0 in ((6, -3.8), (10, 3.7), (15, -2.9), (19, 3.1), (24, -3.4)):
        ember(c, f0 + f, x0, n=22, rise=3.0)
    for f, x0 in ((14, -1.5), (20, 1.8)):                       # a feather or two shaken loose
        sg = 1 if x0 > 0 else -1
        c.pools["feather"].particle(f0 + f, f0 + f + 24, lambda t, x0=x0, sg=sg: (
            x0 + .6 * S(t * 4) + .5 * t * sg, 3.4 - 1.2 * t), c.rng, spin=100, grow=(.45, .4), fade=(1, 0))
    c.glow_curve("hit", lambda u: .7 * S(math.pi * u) ** 1.5)


CHARGE = 22                                                     # the multi's frame it bursts


def multi(c):
    def pose(i, n):
        env = 1 - c.ease_in_out(max(0, (i / n - .75) / .25))
        if i <= CHARGE:
            e = c.ease_in_out(i / CHARGE)
            q = S(i * 2.3) * e
            p = dict(jack=dict(x=.015 * q, sx=1 + .03 * e, sy=1 + .03 * e),
                     crow=dict(y=-.05 * e, sy=1 - .03 * e, r=.8 * S(i * 2.7) * e))
            for j, b in enumerate(LETTERS):
                p[b] = dict(r=.7 * S(i * 2.1 + j) * e)
            return p
        t = (i - CHARGE) / 30
        K = c.damp(t, 2.0, .5)
        pop = S(math.pi * min(1, t / .45))
        p = dict(jack=dict(sx=1 + (.03 * K + .025 * pop) * env, sy=1 + (.03 * K + .03 * pop) * env),
                 crow=dict(y=(-.05 * K + .14 * pop) * env, sy=1 - .03 * K * env, r=-2 * pop * env))
        for j, b in enumerate(LETTERS):
            p[b] = dict(y=.12 * pop * env, r=(2, 0, -2)[j] * pop * env)
        return p
    c.run("multi", pose)
    fs = 301 + CHARGE
    c.pools["rays"].particle(fs, fs + 16, lambda t: (0, .2), c.rng, spin=-30, grow=(.6, 1.05), fade=(.7, 0))
    c.pools["ring"].particle(fs, fs + 14, lambda t: (0, 0), c.rng, grow=(.75, 1.12), fade=(.7, 0))
    for j in range(8):
        a = TAU * j / 8 + .35
        c.pools["leaf"].particle(fs + j % 2, fs + 18, lambda t, a=a: (
            math.cos(a) * (2.4 + 2.2 * c.ease_out(t)), .2 + math.sin(a) * (2.4 + 2.2 * c.ease_out(t))),
            c.rng, spin=160, grow=(.4, .25), fade=(1, 0))
    c.glow_curve("multi", lambda u: .6 * (u * 42 / CHARGE) ** 1.5 if u * 42 < CHARGE else
                 .6 * max(0, 1 - (u * 42 - CHARGE) / 18))


# ---------------------------------------------------------------- the idle that stands out + the pop
# (owner, 2026-11-10: the bonus icons' idles must STAND OUT on the board - the game plays these two at full speed and
#  amplitude while the ordinary icons idle slow and damped. This idle replaces the very subtle one above.)
# idle  live fire: tongues of flame lick up from behind the jack, out of step, flickering; its carved face glows and
#       dims, twice a loop, the halo with it; embers rise and wink out; the crow bobs on its perch, cocks itself and
#       ruffles; the X, F and S throb one after another
# pop   strain: it swells, the crow hunching, the letters rattling, the fire rising. BLOW: the crow flaps off the top
#       shedding feathers, the X, F and S are thrown apart, and the jack is swallowed by its own fire - the flames
#       surge up as it shrinks into them - in embers and smoke
from . import popkit as P                                      # noqa: E402

XFX = {
    "flame": dict(files=["parts:fx_flame"], n=7, size=3.2, depth=.3),
    "ember": dict(files=["sparkle"], n=16, size=.9, tint=[(1, .55, .15), (1, .8, .3)]),
    "plume": dict(files=["feather"], n=7, size=1.6),
    "smoke": dict(files=["steam"], n=5, size=3.0, tint=(.62, .45, .8)),
}
FEET = [(-3.7, .3, 2), (-2.9, 1.8, 3), (-1.7, 2.6, 4), (1.7, 2.6, 3), (2.9, 1.8, 2), (3.7, .3, 4), (0.0, 3.0, 3)]


def idle(c):                                                    # noqa: F811
    def pose(i, n):
        t = i / n
        b = S(TAU * 2 * t)
        ruf = S(math.pi * min(1, max(0, (t - .55) / .2))) ** 2  # the crow's ruffle, once a loop
        p = dict(jack=dict(sx=1 + .018 * b, sy=1 + .028 * b),
                 crow=dict(y=.07 * S(TAU * 2 * t) ** 2 + .05 * ruf, r=2.4 * S(TAU * t) + 3 * ruf * S(TAU * 9 * t),
                           sx=1 + .06 * ruf * S(TAU * 12 * t), sy=1 + .05 * ruf * C(TAU * 12 * t) * S(TAU * 12 * t)),
                 faceglow=dict(a=.85 * S(TAU * t) ** 2))
        for j, l in enumerate(LETTERS):
            w = max(0.0, S(TAU * 2 * t - j * .9)) ** 2
            p[l] = dict(y=.07 * w, sx=1 + .08 * w, sy=1 + .08 * w)
        return p
    c.run("idle", pose, extras=["faceglow"])
    c.rng.uniform(0, 360)                                       # (the old idle's one random number: the other clips keep theirs)
    for j, (x, z, k) in enumerate(FEET):                         # the fire: each tongue licks k times a loop
        def lick(i, n, x=x, z=z, k=k, j=j):
            t = i / n
            L = S(math.pi * k * t) ** 2 * (.75 + .25 * S(TAU * 11 * t + j))
            sz = .35 + .75 * L
            return dict(x=x + .12 * S(TAU * 5 * t + j) * L, z=z - .5 + .45 * 3.2 * sz, sx=.55 + .25 * L, sz=sz,
                        r=(-x * 3) + 5 * S(TAU * 4 * t + j) * L, a=min(1.0, 4 * L), behind=True)
        c.fx["flame"].hold("idle", lick)
    import random
    rr = random.Random(41)
    for j in range(9):                                         # embers, all round the loop (they live across its seam)
        x0, sw, ph = rr.uniform(-3.8, 3.8), rr.uniform(.3, .7), rr.uniform(0, 6)
        z0 = 2.4 - .25 * x0 * x0 * .5
        c.fx["ember"].emit(j * 8, j * 8 + 26, lambda t, x0=x0, z0=z0, sw=sw, ph=ph: (
            x0 + sw * S(5 * t + ph), z0 + 3.4 * t), rot=rr.uniform(0, 90), spin=200, clip="idle", wrap=True,
            grow=(.6, .15), fade=lambda t: min(1.0, 5 * t) * (1 - t) ** .7)
    c.glow_curve("idle", lambda u: .75 * S(TAU * u) ** 2)


def pop(c):
    B = P.BLOW
    THROW = dict(let_x=(-14, 11, 320), let_f=(0, 18, -100), let_s=(14, 11, -320))

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            q = S(i * 3.1) * k
            p = dict(root=P.swell(1 + .09 * k, x=.05 * q), crow=dict(y=-.1 * k, sy=1 - .1 * k, r=3 * S(i * 3.6) * k),
                     faceglow=dict(a=k))
            for j, l in enumerate(LETTERS):
                p[l] = dict(r=5 * S(i * 3.3 + j) * k, sx=1 + .08 * k, sy=1 + .08 * k)
            return p
        t = (i - B) / 30
        z = 1.05 - .6 * P.st(i, B, 19)
        flap = S((i - B) * 2.3)
        p = dict(root=P.swell(1.0), jack=dict(a=0),
                 jack_bare=dict(a=P.gone(i, 13, 19), sx=z, sy=z, y=-.8 * P.st(i, B, 19)),
                 faceglow=dict(a=P.gone(i, B, 14), sx=z, sy=z, y=-.8 * P.st(i, B, 19)),
                 crow=P.fly(i, B, 5, 21, g=30, drag=1.2, r0=-14, a=P.gone(i, 19, 24), sx=1 + .22 * flap,
                            sy=1 - .12 * flap))
        for l, (vx, vy, sp) in THROW.items():
            p[l] = P.fly(i, B, vx, vy, g=36, spin=sp, a=P.gone(i, 19, 24), sx=1.15, sy=1.15)
        return p
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    for j, (x, z, k) in enumerate(FEET):                         # the fire takes it
        f = 3 + j % 3
        fx["flame"].emit(f, 20 + j % 3, lambda t, x=x, z=z: (x * (1 - .5 * t), z - 1.2 + .45 * 3.2 * (.4 + 1.5 * S(math.pi * t ** .7))),
                         rot=-x * 3, grow=lambda t: (.6 + .5 * S(math.pi * t ** .7), .4 + 1.5 * S(math.pi * t ** .7)),
                         fade=lambda t: min(1.0, 4 * t) * min(1.0, 5 * (1 - t)))
    P.burst(fx["ember"], rng, B, 14, at=(0, 0), speed=(14, 30), ang=(30, 150), g=-6, life=(11, 15), grow=(.9, .2),
            spin=300, spread=2.5, even=True, drag=2.5)
    P.burst(fx["plume"], rng, B, 7, at=(.3, 3.2), speed=(8, 16), ang=(0, 360), g=14, life=(11, 15), grow=(.9, .7),
            spin=360, spread=.8, even=True, drag=3)
    P.burst(fx["smoke"], rng, B + 5, 5, at=(0, 0), speed=(4, 9), ang=(50, 130), g=-8, life=(9, 11), grow=(.5, 1.2),
            spin=90, spread=1.6, stagger=1, drag=2, fade=lambda t: .8 * (1 - t))
    c.glow_out(lambda i: .3 + .7 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .1 * P.strain(i) if i < B else 1.2)
