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
