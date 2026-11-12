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


# ---------------------------------------------------------------- the idle that stands out + the pop
# (owner, 2026-11-10: the bonus icons' idles must STAND OUT on the board - the game plays these two at full speed and
#  amplitude while the ordinary icons idle slow and damped. This idle replaces the very subtle one above.)
# idle  the badge breathes deep, twice a loop, its glow pulsing with it; the F and then the S bounce in a wave; four
#       sparkles circle it on a tilted ring, passing behind it, twinkling; glints run over the gold; the leaves flutter
#       and a leaf drifts down now and then
# pop   strain: it swells, the letters pushing out and quivering. BLOW: the badge bursts like a balloon in a ring of
#       light and a shower of gold stars, the F and the S spin off to either side, the leaves whirl away
from . import popkit as P                                      # noqa: E402

XFX = {
    "orb": dict(files=["sparkle", "sparkle_w"], n=4, size=1.5),
    "glintx": dict(files=["sparkle_w"], n=4, size=1.8),
    "drift": dict(files=["leaf_red", "leaf_orange"], n=3, size=1.5),
    "star": dict(files=["star"], n=14, size=1.2),
    "halo": dict(files=["ring"], n=1, size=9.0, depth=.2),
}


def idle(c):                                                    # noqa: F811
    def pose(i, n):
        t = i / n
        b = S(TAU * 2 * t)
        hf = max(0.0, S(TAU * 2 * t)) ** 2                      # the F's bounce, then the S's a beat later
        hs = max(0.0, S(TAU * 2 * t - 1.2)) ** 2
        return dict(badge=dict(sx=1 + .022 * b, sy=1 + .034 * b),
                    let_f=dict(y=.22 * hf, r=3 * hf, sx=1 - .03 * hf, sy=1 + .07 * hf),
                    let_s=dict(y=.22 * hs, r=-3 * hs, sx=1 - .03 * hs, sy=1 + .07 * hs),
                    leaf_l=dict(r=5 * S(TAU * 2 * t) + 2 * S(TAU * 7 * t)),
                    leaf_r=dict(r=-5 * S(TAU * 2 * t + .6) + 5 * S(.6) - 2 * S(TAU * 5 * t)))
    c.run("idle", pose)
    c.rng.uniform(0, 360)                                       # (the old idle's one random number: the other clips keep theirs)
    for j in range(4):                                         # the ring of sparkles
        def orb(i, n, j=j):
            th = TAU * (i / n + j / 4)
            far = S(th) > 0
            return dict(x=5.1 * C(th), z=.2 + 1.7 * S(th), behind=far, r=120 * i / n,
                        s=(.55 + .3 * S(TAU * 3 * i / n + j) ** 2) * (1 - .25 * S(th)))
        c.fx["orb"].hold("idle", orb)
    for j, (f, (x, z)) in enumerate(zip((6, 24, 42, 58), GLINTS)):
        c.fx["glintx"].emit(f, f + 9, lambda t, x=x, z=z: (x, z), rot=20 * j, spin=70, clip="idle",
                            grow=lambda t: .15 + .75 * S(math.pi * t), fade=lambda t: S(math.pi * t) ** .5)
    for j, (f, x0) in enumerate(((10, -3.4), (46, 3.5))):       # a leaf drifts down
        sg = 1 if x0 > 0 else -1
        c.fx["drift"].emit(f, f + 22, lambda t, x0=x0, sg=sg: (x0 + .6 * sg * S(t * 6), 2.6 - 3.0 * t), rot=40 * j,
                           spin=160 * sg, clip="idle", grow=(.5, .4), fade=lambda t: S(math.pi * t) ** .6)
    c.glow_curve("idle", lambda u: .75 * S(TAU * u) ** 2)


def pop(c):
    B = P.BLOW

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            q = S(i * 3.1) * k
            return dict(root=P.swell(1 + .1 * k, x=.05 * q), badge=dict(sx=1 + .06 * k, sy=1 + .06 * k),
                        let_f=dict(sx=1 + .14 * k, sy=1 + .14 * k, r=4 * q),
                        let_s=dict(sx=1 + .14 * k, sy=1 + .14 * k, r=-4 * S(i * 3.4) * k),
                        leaf_l=dict(r=-8 * k), leaf_r=dict(r=8 * k))
        t = (i - B) / 30
        s = 1.06 + .12 * (i - B)
        badge = dict(sx=s, sy=s, a=P.gone(i, B, B + 3))
        fl = lambda name, want: P.free(c, name, badge, want)
        flut = .4 + .6 * abs(C((i - B) * .8))
        return dict(root=P.swell(1.0), badge=badge,
                    let_f=fl("let_f", P.fly(i, B, -13, 15, g=36, spin=340, a=P.gone(i, 19, 24), sx=1.2, sy=1.2)),
                    let_s=fl("let_s", P.fly(i, B, 13, 14, g=36, spin=-340, a=P.gone(i, 19, 24), sx=1.2, sy=1.2)),
                    leaf_l=fl("leaf_l", P.fly(i, B, -15, 8, g=18, spin=420, drag=1.5, a=P.gone(i, 17, 22), sx=flut)),
                    leaf_r=fl("leaf_r", P.fly(i, B, 15, 8, g=18, spin=-420, drag=1.5, a=P.gone(i, 17, 22), sx=flut)))
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    fx["halo"].emit(B, B + 6, lambda t: (0, -.2), rot=0, grow=lambda t: .5 + .75 * (1 - (1 - t) ** 3),
                    fade=lambda t: 1 - t * t)
    P.burst(fx["star"], rng, B, 14, at=(0, -.2), speed=(22, 38), ang=(0, 360), g=24, life=(11, 15), grow=(1.1, .5),
            spin=500, spread=1.0, even=True, drag=3)
    for j in range(4):
        fx["glintx"].emit(B + 1 + 2 * j, B + 6 + 2 * j, lambda t, j=j: ((-1) ** j * (2 + j), 1.5 + .6 * j), rot=30 * j,
                          spin=80, grow=lambda t: .2 + .8 * S(math.pi * t), fade=(1, .4))
    c.glow_out(lambda i: .3 + .7 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .1 * P.strain(i) if i < B else 1.2)
