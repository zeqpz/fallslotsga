"""H2 Pumpkin Pie: the pie in its tin, the cut slice (and its fill under the cream), the big swirl of cream on the pie
and the small one on the slice (tools/fall/parts/H2.py). Its character: soft custard and jelly-wobbly cream.
idle   the two cream swirls wobble like jelly out of step, the slice nudges out of the gap and settles back
land   it plops down: the pie squashes, the slice jumps in the gap and clacks back, both creams splat and jiggle
hit    the pie leans back, then the slice is lifted out and tilted like a server is taking it, the big swirl springs
       up off the pie and lands squashed, the small one bounces on the slice; crumbs fly from the gap
multi  the pie trembles and swells as it charges, the creams shiver; then the slice pops up, the creams spring tall
       and wobble down - a ring, sparkles and a spray of crumbs"""
import math

FX = ["crumb", "sparkle"]
S = math.sin
TAU = 2 * math.pi


def jelly(a, ph=0.0):
    """jelly wobble of amount a (signed): taller-thinner one way, squat-wider the other (volume kept roughly)"""
    return dict(sx=1 - .8 * a, sy=1 + a)


def idle(c):
    def pose(i, n):
        t = i / n
        wb = .035 * S(TAU * 3 * t) + .012 * S(TAU * 6 * t)
        ws = .04 * S(TAU * 4 * t) + .015 * S(TAU * 2 * t)
        nudge = max(0, S(TAU * t)) ** 2                            # out and back over the first half of the loop
        return dict(pie=dict(sy=1 + .006 * S(TAU * 2 * t)),
                    cream_big=dict(r=1.6 * S(TAU * 2 * t), **jelly(wb)),
                    cream_small=dict(r=-2.5 * S(TAU * 3 * t), **jelly(ws)),
                    slice=dict(x=.05 * nudge, y=-.03 * nudge, r=-1.2 * nudge))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.4, .32)
        lag = c.damp(max(0, t - .04), 4.2, .2)
        hop = .14 * max(0, S(math.pi * min(1, max(0, t - .02) / .2)))
        return dict(root=dict(sx=1 + .13 * k, sy=1 - .15 * k),
                    pie=dict(sy=1 - .03 * k),
                    slice=dict(y=hop, r=-3 * S(math.pi * min(1, t / .26)) * (t < .26)),
                    cream_big=jelly(-.16 * lag), cream_small=dict(r=5 * S(t * 34) * math.exp(-t * 7), **jelly(-.18 * lag)))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))          # everything home by the end
        if i <= 6:                                                 # the pie leans back, the creams squat
            e = c.ease_in_out(i / 6)
            return dict(pie=dict(sx=1 + .04 * e, sy=1 - .06 * e, r=2 * e),
                        slice=dict(y=-.04 * e), cream_big=jelly(-.1 * e), cream_small=jelly(-.12 * e))
        t = (i - 6) / 30                                           # seconds since the lift began
        lift = c.ease_out(min(1, t / .3)) * (1 - c.ease_in_out(min(1, max(0, (t - .62) / .42))))
        back = c.damp(max(0, t - 1.04), 3.6, .35) if t > 1.04 else 0   # the clack when it drops back in
        lean = 2 * (1 - c.ease_out(min(1, t / .25)))
        # the big swirl: springs up off the pie, lands squashed, wobbles
        air = max(0, S(math.pi * min(1, max(0, t - .02) / .42)))
        wob = c.damp(max(0, t - .44), 3.2, .22) if t > .44 else 0
        big = dict(y=.42 * air, r=7 * S(t * 11) * air, **jelly(.16 * air - .2 * wob))
        # the small one rides the slice and bounces on it
        air2 = max(0, S(math.pi * min(1, max(0, t - .12) / .34)))
        wob2 = c.damp(max(0, t - .46), 3.8, .2) if t > .46 else 0
        small = dict(y=.3 * air2, r=-9 * S(t * 13) * air2, **jelly(.14 * air2 - .22 * wob2))
        rel = 1 - c.ease_out(min(1, t / .15))                     # the lean-back's squat lets go
        return dict(pie=dict(r=lean, sx=1 + .04 * rel, sy=1 - .06 * rel - .03 * back),
                    slice=dict(x=.32 * lift * env, y=(.62 * lift + .05 * back) * env,
                               r=(-11 * lift + 3 * S(t * 9) * lift) * env),
                    cream_big={k: (v - (1 if k in ("sx", "sy") else 0)) * env + (1 if k in ("sx", "sy") else 0)
                               for k, v in big.items()},
                    cream_small={k: (v - (1 if k in ("sx", "sy") else 0)) * env + (1 if k in ("sx", "sy") else 0)
                                 for k, v in small.items()})
    c.run("hit", pose)
    f0 = 201
    for j in range(10):                                            # crumbs knocked out of the gap as it lifts
        fs = f0 + 8 + j
        a = c.rng.uniform(.25, 1.6)
        sp = c.rng.uniform(3.2, 5.0)
        vx, vz = sp * math.cos(a), sp * math.sin(a) + 1.5
        c.pools["crumb"].particle(fs, fs + 16, lambda t, vx=vx, vz=vz: (1.1 + vx * t * .7, -1.6 + (vz * t - 8 * t * t) * .7),
                                  c.rng, spin=300, grow=(.8, .5), fade=(1, .8))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 16, f0 + 28, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    def pose(i, n):
        if i < 18:                                                 # charge: trembling harder, swelling
            k = (i / 18) ** 1.3
            q = S(i * 2.9) * k
            return dict(pie=dict(x=.05 * q, sx=1 + .06 * k, sy=1 + .05 * k, r=1.2 * q),
                        slice=dict(y=.04 * abs(S(i * 3.4)) * k, r=-2 * S(i * 3.1) * k),
                        cream_big=jelly(.05 * S(i * 3.7) * k), cream_small=jelly(.07 * S(i * 4.1 + 1) * k))
        t = (i - 18) / 30
        k = c.damp(t, 2.8, .3)
        pop = max(0, S(math.pi * min(1, t / .5)))                  # the slice pops up and drops back in
        wob = c.damp(t, 3.4, .2)
        fade = (1 - c.ease_in_out(min(1, max(0, (i - 34) / 8)))) * min(1, (i - 16) / 4)
        return dict(pie=dict(sx=1 + .1 * k, sy=1 + .08 * k),
                    slice=dict(x=.15 * pop, y=.7 * pop, r=-14 * pop + 4 * S(t * 12) * pop),
                    cream_big=dict(y=.12 * max(0, k) * min(1, (i - 16) / 4), **jelly(.26 * wob * fade)),
                    cream_small=dict(r=8 * S(t * 14) * pop, **jelly(.3 * wob * fade)))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(12):
        fs = f0 + 18 + j // 3
        a = c.rng.uniform(.2, 2.9)
        sp = c.rng.uniform(3.5, 5.5)
        vx, vz = sp * math.cos(a), sp * math.sin(a) + 2
        c.pools["crumb"].particle(fs, fs + 18, lambda t, vx=vx, vz=vz: (1.4 + vx * t * .75, -1.0 + (vz * t - 9 * t * t) * .75),
                                  c.rng, spin=360, grow=(.9, .5), fade=(1, .7))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))


# ---------------------------------------------------------------- pop: served - every slice at once
# strain  the pie swells, the big swirl of cream stretching up and wobbling; cut lines appear: six more slices
# BLOW    the slices shoot out from the middle one after another round the tin (a fan dealt in a flash), tip and drop;
#         the cut slice goes first with its cream hopping off it; the big swirl is fired straight up and bursts into
#         dollops; crust crumbs and custard everywhere; the tin's bare floor drops away
from . import popkit as P                                      # noqa: E402

XFX = {
    "cream": dict(files=["parts:fx_cream"], n=10, size=1.6),
    "custard": dict(files=["parts:fx_custard"], n=10, size=1.1),
    "crust": dict(files=["parts:fx_crust"], n=14, size=1.0),
}
SLICES = ["s0", "s1", "s2", "s3", "s4", "s5"]                    # round the tin, counter-clockwise from the gap
MID = (.22, .08)                                               # where the cuts meet (units)
OUT = (math.cos(math.radians(-32)), math.sin(math.radians(-32)))   # the way the cut slice points


def pop(c):
    B = P.BLOW
    D = {s: P.unit(c.pivot[s][0] - MID[0], c.pivot[s][1] - MID[1]) for s in SLICES + ["floor"]}

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            p = dict(root=P.swell(1 + .1 * k, 1 + .1 * k - .03 * S(i * 2.8) * k, x=.05 * S(i * 3.1) * k),
                     cream_big=dict(sy=1 + .3 * k * (.6 + .4 * S(i * 2.4)), sx=1 - .1 * k, r=6 * S(i * 2.9) * k, a=1),
                     slice=dict(x=OUT[0] * .3 * k, y=OUT[1] * .3 * k, a=1), cream_small=dict(r=-9 * S(i * 3.3) * k))
            if i >= 5:                                         # cut: six more slices, a hair apart
                p["pie"] = dict(a=0)
                for s in SLICES + ["floor"]:
                    p[s] = dict(a=1, x=D[s][0] * .035 * (i - 4), y=D[s][1] * .035 * (i - 4))
            return p
        p = dict(root=P.swell(1.04), pie=dict(a=0))
        z = 1 - .4 * P.st(i, 18, 24)
        for j, s in enumerate(SLICES):
            t = max(0.0, i - B - j * .8) / 30
            go = .1 + 5.6 * (1 - math.exp(-8 * t))             # out fast, then it hangs
            sg = 1 if D[s][0] < 0 else -1
            p[s] = dict(a=P.gone(i, 20, 24), x=D[s][0] * go, y=D[s][1] * go * .85 - 20 * max(0, t - .2) ** 2,
                        r=sg * (26 * (1 - math.exp(-6 * t)) + 70 * max(0, t - .2) ** 1.5), sx=z, sy=z)
        p["floor"] = dict(a=P.gone(i, 9, 13), y=-.14 * (i - B), sx=1 - .05 * (i - B), sy=1 - .05 * (i - B))
        t = (i - B) / 30
        go = .3 + 6.6 * (1 - math.exp(-9 * t))
        p["slice"] = dict(a=P.gone(i, 19, 23), x=OUT[0] * go, y=OUT[1] * go - 16 * max(0, t - .2) ** 2,
                          r=-30 * (1 - math.exp(-5 * t)), sx=z, sy=z)
        p["cream_small"] = P.fly(i, B, 3, 12, g=36, spin=-300, a=P.gone(i, 15, 19))
        up = math.exp(-t * 9)
        p["cream_big"] = P.fly(i, B, -1.0, 19, g=40, a=P.gone(i, 13, 15), sy=1 + .45 * up - .3 * P.st(i, 12, 15),
                               sx=1 - .2 * up + .5 * P.st(i, 12, 15))
        return p
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    P.burst(fx["crust"], rng, B, 14, at=MID, speed=(20, 34), ang=(0, 360), g=30, life=(10, 14), grow=(1.0, .7),
            spin=700, spread=1.2, even=True, drag=3.2)
    P.burst(fx["custard"], rng, B, 10, at=MID, speed=(16, 28), ang=(20, 160), g=34, life=(10, 13), grow=(1.0, .6),
            aim="tail", spread=.8, even=True, drag=3)
    P.burst(fx["cream"], rng, B, 3, at=(-.3, 1.0), speed=(8, 14), ang=(40, 140), g=30, life=(8, 11), grow=(.7, .4),
            spread=.4)
    P.burst(fx["cream"], rng, 13, 7, at=(-.6, 4.3), speed=(14, 24), ang=(0, 360), g=34, life=(8, 11), grow=(1.0, .5),
            spread=.3, even=True, drag=3)
    c.glow_out(lambda i: .25 + .6 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .08 * P.strain(i) if i < B else 1.14)
