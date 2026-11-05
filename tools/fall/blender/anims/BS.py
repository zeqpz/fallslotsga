"""BS Free Spins badge: the pumpkin badge, two maple leaves behind it, the F and the S on it (tools/fall/parts/BS.py).
The owner wants the bonus icons' motion VERY subtle and slow: small amplitudes, long smooth curves, nothing snappy.
idle   one slow breath of the pumpkin a loop, the letters drifting a hair up and down out of step, the leaves
       barely swaying; one soft glint on the gold
land   it settles onto the reel: a small soft squash, the letters lag a touch and settle, the leaves dip and recover
hit    a warm, gentle swell: the badge rises and grows a little, the F and then the S lift and tip in a slow wave,
       the leaves lift; glints on the letters, a few sparkles and two drifting leaves
multi  it gathers itself (a faint tremble, a slow swell), then a soft pop: the letters lift, a ring and sparkles
       spread, and it eases home"""
import math

FX = ["sparkle", "glint", "leaf"]
S, C = math.sin, math.cos
TAU = 2 * math.pi
GLINTS = [(-1.9, .7), (1.5, .9), (-1.2, -1.6), (2.2, -1.2)]      # on the letters' gold (units)


def st(i, a, b):
    """0 before frame a, 1 after frame b, a smooth step between"""
    u = min(1.0, max(0.0, (i - a) / (b - a)))
    return u * u * (3 - 2 * u)


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * t)                                          # one slow breath a loop (2.4 s)
        return dict(badge=dict(sx=1 - .004 * b, sy=1 + .007 * b),
                    let_f=dict(y=.022 * S(TAU * t), r=.5 * S(TAU * t)),
                    let_s=dict(y=-.018 * S(TAU * t) + .008 * S(TAU * 2 * t), r=-.4 * S(TAU * t)),
                    leaf_l=dict(r=.9 * S(TAU * t)), leaf_r=dict(r=-.9 * S(TAU * t)))
    c.run("idle", pose)
    x, z = GLINTS[0]
    c.pools["glint"].particle(1 + 30, 1 + 44, lambda t: (x, z), c.rng, spin=60, grow=(.1, .5), fade=(.9, 0))
    c.glow_curve("idle", lambda u: .08 * S(math.pi * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        env = 1 - c.ease_in_out(max(0, (i / n - .7) / .3))
        k = c.damp(t, 2.4, .45)
        lag = c.damp(max(0, t - .04), 2.0, .45)
        return dict(root=dict(sx=1 + .06 * k * env, sy=1 - .07 * k * env),
                    let_f=dict(y=-.05 * lag * env), let_s=dict(y=-.04 * lag * env),
                    leaf_l=dict(r=-3 * lag * env), leaf_r=dict(r=3 * lag * env))
    c.run("land", pose)
    c.glow_curve("land", lambda u: -.15 * max(0, 1 - u / .4))


def hit(c):
    def pose(i, n):
        up = st(i, 0, 18) * (1 - st(i, 28, 46))                 # a slow rise and a slow settle
        wf = S(math.pi * min(1, max(0, (i - 4) / 26)))         # the F's lift, then the S's
        ws = S(math.pi * min(1, max(0, (i - 10) / 26)))
        sway = S(TAU * i / 46)
        return dict(badge=dict(y=.12 * up, sx=1 + .035 * up, sy=1 + .045 * up),
                    let_f=dict(y=.14 * wf, r=2.5 * wf, sx=1 + .03 * wf, sy=1 + .03 * wf),
                    let_s=dict(y=.14 * ws, r=-2.5 * ws, sx=1 + .03 * ws, sy=1 + .03 * ws),
                    leaf_l=dict(r=-4 * up + 1.5 * sway * up), leaf_r=dict(r=4 * up - 1.5 * sway * up))
    c.run("hit", pose)
    f0 = 201
    for j, f in enumerate((10, 16, 22, 28)):
        x, z = GLINTS[j]
        c.pools["glint"].particle(f0 + f, f0 + f + 10, lambda t, x=x, z=z: (x, z + .15), c.rng, spin=80,
                                  grow=(.15, .7), fade=(1, 0))
    for j in range(6):
        a = TAU * j / 6 + .5
        c.pools["sparkle"].particle(f0 + 14 + j, f0 + 30 + j, lambda t, a=a: (
            math.cos(a) * (3.6 + .9 * c.ease_out(t)), .3 + math.sin(a) * (3.6 + .9 * c.ease_out(t))),
            c.rng, spin=90, grow=(.6, .05))
    for j, x0 in enumerate((-3.2, 3.3)):                         # two leaves let go and drift down
        sg = 1 if x0 > 0 else -1
        c.pools["leaf"].particle(f0 + 12 + 6 * j, f0 + 44, lambda t, x0=x0, sg=sg: (x0 + .5 * sg * S(t * 5),
                                 2.0 - 1.6 * t), c.rng, spin=120, grow=(.4, .35), fade=(1, 0))
    c.glow_curve("hit", lambda u: .7 * S(math.pi * u) ** 1.5)


CHARGE = 22                                                     # the multi's frame it pops


def multi(c):
    def pose(i, n):
        env = 1 - c.ease_in_out(max(0, (i / n - .75) / .25))
        if i <= CHARGE:
            e = c.ease_in_out(i / CHARGE)
            q = S(i * 2.2) * e
            return dict(badge=dict(x=.015 * q, sx=1 + .03 * e, sy=1 + .03 * e),
                        let_f=dict(r=.8 * q), let_s=dict(r=-.8 * S(i * 2.5) * e),
                        leaf_l=dict(r=-2 * e), leaf_r=dict(r=2 * e))
        t = (i - CHARGE) / 30
        K = c.damp(t, 2.0, .5)
        pop = S(math.pi * min(1, t / .45))
        return dict(badge=dict(sx=1 + (.03 * K + .025 * pop) * env, sy=1 + (.03 * K + .03 * pop) * env),
                    let_f=dict(y=.12 * pop * env, r=2 * pop * env), let_s=dict(y=.12 * pop * env, r=-2 * pop * env),
                    leaf_l=dict(r=(-2 * K - 3 * pop) * env), leaf_r=dict(r=(2 * K + 3 * pop) * env))
    c.run("multi", pose)
    f0 = 301
    for j, f in enumerate((6, 12, 17)):
        x, z = GLINTS[j]
        c.pools["glint"].particle(f0 + f, f0 + f + 8, lambda t, x=x, z=z: (x, z), c.rng, spin=60, grow=(.1, .55),
                                  fade=(1, 0))
    fs = f0 + CHARGE
    c.pools["ring"].particle(fs, fs + 14, lambda t: (0, 0), c.rng, grow=(.75, 1.12), fade=(.7, 0))
    for j in range(8):
        a = TAU * j / 8 + .2
        c.pools["sparkle"].particle(fs, fs + 16, lambda t, a=a: (
            math.cos(a) * (2.0 + 2.6 * c.ease_out(t)), .2 + math.sin(a) * (2.0 + 2.6 * c.ease_out(t))),
            c.rng, spin=120, grow=(.75, .05))
    c.glow_curve("multi", lambda u: .6 * (u * 42 / CHARGE) ** 1.5 if u * 42 < CHARGE else
                 .6 * max(0, 1 - (u * 42 - CHARGE) / 18))
