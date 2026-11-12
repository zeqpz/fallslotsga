"""H5 Moonshine Jug: the jug (the plate's open-mouthed jug under the drawing's own), the drip down its neck and the
cork (tools/fall/parts/H5.py). Its character: tipsy - it sways, hiccups and can't keep its cork in.
idle   the jug sways tipsily on its foot, the cork wiggles, the drip slowly stretches longer, lets a drop fall
       and snaps back
land   it clunks down: squash, the cork jumps in its neck, the drip flicks
hit    hic! - three hiccups (squash and stretch jolts, each tipping it), on the second the cork pops up spinning a
       full turn and drops back in with a thunk; drops fly from the mouth
multi  it shakes harder and harder (the cork rattling), then the cork blasts off, the jug stretches and a fizz of
       bubbles pours up out of the mouth; the cork comes back down into the neck and the jug wobbles still"""
import math

FX = ["drop", "bubble", "sparkle"]
S = math.sin
TAU = 2 * math.pi
MOUTH = (.75, 3.9)                        # the jug's mouth, units (icon px (575, 110))
TIP = (1.45, .45)                         # the drip's hanging end at rest


def idle(c):
    def pose(i, n):
        t = i / n
        # the drip: stretches 0..0.62, lets go, snaps short and springs back to rest by the end
        if t < .62:
            d = .3 * c.ease_in_out(t / .62)
        else:
            d = .3 * c.damp((t - .62) * n / 30, 2.2, .35) - .08 * S(math.pi * min(1, (t - .62) / .38)) ** 2
            d *= 1 - c.ease_in_out(max(0, (t - .85) / .15))
        return dict(jug=dict(r=2.4 * S(TAU * t), sx=1 + .008 * S(TAU * 2 * t), sy=1 - .008 * S(TAU * 2 * t)),
                    cork=dict(r=2.0 * S(TAU * 3 * t)),
                    drip=dict(sy=1 + d, sx=1 - .25 * d))
    c.run("idle", pose)
    f = 1 + int(.62 * 72)
    c.pools["drop"].particle(f, f + 12, lambda t: (TIP[0] + .1, TIP[1] - .2 - 5.0 * t * t), c.rng, spin=0,
                             grow=(.9, 1.0), fade=(1, .6))
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.2, .3)
        hop = .25 * max(0, S(math.pi * min(1, max(0, t - .03) / .2)))
        return dict(root=dict(sx=1 + .14 * k, sy=1 - .16 * k),
                    cork=dict(y=hop, r=8 * S(t * 25) * math.exp(-t * 6)),
                    drip=dict(r=6 * S(t * 22) * math.exp(-t * 5), sy=1 + .12 * max(0, -k)))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    hics = (3, 15, 33)                                             # the three hiccups' frames

    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        st = r = 0.0
        for j, f in enumerate(hics):
            t = (i - f) / 30
            if t > 0:
                k = c.damp(t, 3.4, .32)
                a = .1 * S(math.pi * min(1, t / .1)) if t < .1 else -.06 * k   # stretch up, then a squat rebound
                st += a * (1 + .25 * j)
                r += (5 + 3 * j) * (1 if j % 2 else -1) * max(0, S(math.pi * min(1, t / .35))) * math.exp(-t * 1.5)
        # the cork pops on the second hiccup and is back in by ~frame 36
        tc = (i - 15) / 30
        fly = max(0, S(math.pi * min(1, tc / .6))) if tc > 0 else 0
        spin = -360 * c.ease_in_out(min(1, tc / .6)) if 0 < tc < .6 else 0
        thunk = c.damp(tc - .6, 4, .3) if tc > .6 else 0
        return dict(jug=dict(y=.12 * max(0, st) * env, sx=1 - .6 * st * env, sy=1 + st * env, r=r * env),
                    cork=dict(y=(1.15 * fly - .04 * thunk) * env, x=-.25 * fly * env, r=spin * env,
                              sy=1 - .1 * thunk * env, sx=1 + .08 * thunk * env),
                    drip=dict(r=-r * .8 * env, sy=1 + .2 * max(0, st) * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(7):                                             # moonshine flicked out of the open mouth
        fs = f0 + 16 + j
        a = c.rng.uniform(.6, 2.5)
        vx, vz = 3.2 * math.cos(a), 3.0 + 2 * math.sin(a)
        c.pools["drop"].particle(fs, fs + 14, lambda t, vx=vx, vz=vz: (MOUTH[0] + vx * t * .8,
                                 MOUTH[1] - .2 + (vz * t - 9 * t * t) * .8), c.rng, spin=200, grow=(.5, .35), fade=(1, 1))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 16, f0 + 28, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    def pose(i, n):
        if i < 18:                                                 # shaking harder and harder, the cork rattling
            k = (i / 18) ** 1.5
            q = S(i * 2.6) * k
            return dict(jug=dict(r=5 * q, x=.05 * q, sx=1 + .04 * k, sy=1 + .03 * k),
                        cork=dict(y=.08 * abs(S(i * 3.9)) * k, r=10 * S(i * 4.4) * k),
                        drip=dict(r=-6 * q, sy=1 + .15 * k))
        t = (i - 18) / 30
        ramp = min(1, (i - 17) / 3)
        fly = max(0, S(math.pi * min(1, t / .55)))                 # off and back in 0.55 s
        thunk = c.damp(t - .55, 4, .3) if t > .55 else 0
        k = c.damp(t, 3.0, .3)
        fade = 1 - c.ease_in_out(min(1, max(0, (i - 34) / 8)))
        return dict(jug=dict(sx=1 + (.04 - .1 * k) * ramp * fade, sy=1 + (.03 + .06 * k) * ramp * fade,
                             r=4 * S(t * 18) * math.exp(-t * 3) * ramp),
                    cork=dict(y=.9 * fly - .05 * thunk * fade, r=-540 * c.ease_in_out(min(1, t / .55)) if t < .55 else 0,
                              sy=1 - .12 * thunk * fade, sx=1 + .1 * thunk * fade),
                    drip=dict(sy=1 + .15 * (1 - ramp) + .2 * max(0, k) * fade, r=5 * S(t * 16) * math.exp(-t * 4)))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(10):                                            # the fizz pours up out of the mouth
        fs = f0 + 18 + j
        x0 = c.rng.uniform(-.3, .3)
        c.pools["bubble"].particle(fs, fs + 14, lambda t, x0=x0, j=j: (MOUTH[0] + x0 + .3 * S(t * 8 + j),
                                   MOUTH[1] + .2 + 2.0 * t), c.rng, spin=0, grow=(.5, 1.0), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))


# ---------------------------------------------------------------- pop: it blows its cork and shatters
# strain  the jug swells and judders, the cork chattering; the cork BLOWS (frame 5) on a jet of cider and cracks race
#         over the stoneware
# BLOW    the jug bursts: its shards fly out from the middle, tumbling, on a burst of cider behind them; cider drops
#         and foam everywhere, chips of glaze; the drip is flung off
from . import popkit as P                                      # noqa: E402

XFX = {
    "jet": dict(files=["fizz_jet", "fizz_jet_b", "fizz_jet_c"], n=3, size=6.0, depth=.2),
    "gush": dict(files=["fizz_burst", "fizz_burst_b"], n=2, size=9.0, depth=.2),
    "cider": dict(files=["drop"], n=18, size=1.3),
    "foam": dict(files=["foam_puff"], n=5, size=2.6),
    "chip": dict(files=["parts:fx_chip", "parts:fx_chip2"], n=10, size=.9),
}
P_MOUTH = (.62, 3.75)                                            # the open neck (units)
P_CORE = (0.0, -.7)                                              # where it bursts from


def pop(c):
    B, CK = P.BLOW, 5
    SH = [s for s in c.extras if s.startswith("shard")]
    D = {s: P.unit(c.pivot[s][0] - P_CORE[0], c.pivot[s][1] - P_CORE[1]) for s in SH}
    V = {s: (c.rng.uniform(13, 20), c.rng.choice((-1, 1)) * c.rng.uniform(260, 620)) for s in SH}

    def pose(i, n):
        k = P.strain(i)
        cork = dict(y=.12 * abs(S(i * 2.6)) * k, r=9 * S(i * 3.4) * k, a=1) if i < CK else \
            P.fly(i, CK, 2.2, 24, g=34, spin=-560, at=(0, .3), a=P.gone(i, 15, 20))
        if i < B:
            q = S(i * 3.0) * k
            p = dict(root=P.swell((1 + .14 * k) * (1 + .02 * q), (1 + .14 * k) * (1 - .02 * q), x=.07 * q),
                     cork=cork, drip=dict(sy=1 + .25 * k, a=1))
            if i >= CK:                                        # cracked through
                p["jug"] = dict(a=0)
                for s in SH:
                    p[s] = dict(a=1, x=D[s][0] * .03 * (i - CK + 1), y=D[s][1] * .03 * (i - CK + 1))
            return p
        a = P.gone(i, 20, 24)
        z = 1 - .4 * P.st(i, 18, 24)
        p = dict(root=P.swell(1.05), jug=dict(a=0), cork=cork,
                 drip=P.fly(i, B, 5, 9, g=36, spin=-500, a=P.gone(i, 14, 18)))
        for s in SH:
            v, sp = V[s]
            p[s] = P.fly(i, B, D[s][0] * v, D[s][1] * v + 5, g=32, spin=sp, drag=1.8,
                         at=(D[s][0] * .15, D[s][1] * .15), a=a, sx=z, sy=z)
        return p
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    for j, f in enumerate(range(CK, 13, 2)):                   # the jet out of the neck, boiling (three drawings)
        g0 = min(1.0, .45 + .25 * j)
        fx["jet"].emit(f, f + 1, lambda t, g0=g0: (P_MOUTH[0], P_MOUTH[1] + .42 * 6.0 * g0), rot=0,
                       grow=(g0, g0 * 1.06), fade=(1, 1) if f < 11 else (.8, .3))
    for j in range(2):                                         # the burst of cider behind the shards
        fx["gush"].emit(B + j * 2, B + j * 2 + 3, lambda t: (P_CORE[0], P_CORE[1] + .6), rot=0,
                        grow=lambda t, j=j: .55 + .25 * j + .3 * t, fade=(1, .5) if j == 0 else (.9, 0))
    P.burst(fx["cider"], rng, B, 14, at=P_CORE, speed=(22, 38), ang=(0, 360), g=34, life=(11, 15), grow=(1.0, .6),
            aim="tail", spread=1.0, even=True, drag=3)
    P.burst(fx["cider"], rng, CK, 4, at=P_MOUTH, speed=(14, 22), ang=(60, 120), g=34, life=(9, 12), grow=(.8, .5),
            aim="tail", spread=.2, drag=2.5)
    P.burst(fx["foam"], rng, B, 5, at=P_CORE, speed=(8, 16), ang=(20, 160), g=14, life=(10, 13), grow=(.5, 1.0),
            spin=120, spread=1.2, even=True, drag=3, fade=P.tail(.4))
    P.burst(fx["chip"], rng, B, 10, at=P_CORE, speed=(20, 34), ang=(0, 360), g=34, life=(10, 14), grow=(1.0, .7),
            spin=800, spread=1.5, even=True, drag=2.6)
    c.glow_out(lambda i: .25 + .7 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .1 * P.strain(i) if i < B else 1.18)
