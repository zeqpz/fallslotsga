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
