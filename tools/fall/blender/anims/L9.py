"""L9 Gravy Boat: the boat (the empty boat behind, the back rim, the front wall drawn over the gravy), the gravy, the
handle and two steam wisps (tools/fall/parts/L9.py). The boat turns about the front edge of its foot, so it tips to
pour; the gravy turns about its spout end, so it stays level while the boat tips (its far end sinks behind the front
wall); the wisps ride the gravy and waver about their feet.
idle   the steam wavers and stretches up, out of step, a puff curling off now and then; the gravy laps
land   it clunks down: the boat squats, the gravy slops, the steam squashes down and springs back up, the handle rings
hit    it leans back, then TIPS forward to pour - the gravy runs to the spout and gravy drops pour off it - and rocks
       back upright, the gravy sloshing; the steam puffs
multi  it rattles harder and harder on its foot, the gravy bubbling, the steam squeezed down - then the steam BLASTS
       up, the boat hops, gravy drops and steam fly"""
import math

from . import lowkit as K

FX = ["steam", "drop", "bubble", "sparkle"]
S = math.sin
TAU = 2 * math.pi
SPOUT = (-4.3, 1.0)                                            # the spout's lip, units (at rest)


def imp(t, f, z):
    """a spring knocked at t=0: starts at 0, swings out to ~1 and rings down"""
    if t <= 0:
        return 0.0
    w = TAU * f
    return math.exp(-z * w * t) * S(w * t) / max(.2, math.exp(-z * math.pi / 2))


def spout(r):
    """where the spout lip is when the boat is tipped r degrees about its foot's front edge (-1.8, -3.7)"""
    px, pz = -1.8, -3.7
    a = math.radians(r)
    dx, dz = SPOUT[0] - px, SPOUT[1] - pz
    return px + dx * math.cos(a) - dz * math.sin(a), pz + dx * math.sin(a) + dz * math.cos(a)


def idle(c):
    K.track_glow(c, "boat", .9)
    K.tint(c, "drop", (.62, .34, .2))                          # the honey drop, gravy brown
    K.tint(c, "bubble", (.95, .7, .5))

    def pose(i, n):
        t = i / n
        sw = lambda f, ph: S(TAU * f * t - ph) + S(ph)          # whole cycles, 0 at the loop's ends
        return dict(steam_l=dict(r=3.5 * sw(1, 0) + 1.5 * sw(3, .5), sy=1 + .05 * sw(2, .3), x=.04 * sw(2, 1.1)),
                    steam_r=dict(r=-3.0 * sw(1, 1.8) + 1.5 * sw(3, 2.2), sy=1 + .06 * sw(2, 1.6), x=-.04 * sw(2, 2.4)),
                    gravy=dict(r=-.7 * sw(2, 0), y=.01 * sw(2, .9)),
                    handle=dict())
    c.run("idle", pose)
    for fs, x0 in ((10, -.9), (46, .7)):                       # a wisp curls off the top now and then
        c.pools["steam"].particle(1 + fs, 1 + fs + 22, lambda t, x0=x0: (x0 + .35 * math.sin(t * 5), 3.4 + 2.2 * t),
                                  c.rng, spin=30, grow=(.35, .8), fade=(.6, 0))
    c.glow_curve("idle", lambda u: 0)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .7) / .3))
        k = c.damp(t, 3.4, .3) * env
        sl = imp(t - .03, 2.6, .22) * env
        st = imp(t - .02, 2.8, .25) * env
        return dict(root=dict(sx=1 + .1 * k, sy=1 - .12 * k),
                    gravy=dict(r=-3 * sl, y=-.06 * sl),
                    steam_l=dict(sy=1 - .22 * st, r=4 * st), steam_r=dict(sy=1 - .25 * imp(t - .05, 2.8, .25) * env, r=-4 * st),
                    handle=dict(r=-2.5 * imp(t, 4, .25) * env))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit_tip(i):
    """the boat's tip, degrees (+ = spout down) over the hit"""
    if i <= 6:
        return -2 * c_ease(i / 6)
    if i <= 15:
        return -2 + 7 * c_ease((i - 6) / 9)
    if i <= 25:
        return 5 + .8 * S((i - 15) * 1.9)                       # pouring, a little shake
    t = (i - 25) / 30
    return 5 * (1 - c_ease(min(1, t / .25))) - 2 * imp(t - .15, 2.2, .3) * (1 - c_ease(max(0, (i - 38) / 8)))


def c_ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def hit(c):
    def pose(i, n):
        u = i / n
        r = hit_tip(i)
        lag = hit_tip(max(0, i - 3))                           # the gravy is a beat behind the boat
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        slosh = (imp((i - 25) / 30, 2.0, .2) if i > 25 else 0) * env
        st = 1 + .12 * c.ease_in_out(min(1, i / 8)) * (1 - c.ease_in_out(max(0, (u - .6) / .4)))
        pour = max(0, lag) / 5                                 # 0..1: the gravy runs to the spout and stretches out
        return dict(boat=dict(r=r, sx=1 + .02 * pour * env, sy=1 - .03 * pour * env),
                    gravy=dict(r=(-.5 * lag + 6 * slosh - 3 * pour) * env, x=-.1 * pour * env, y=-.02 * pour * env,
                               sx=1 + .08 * pour * env),
                    steam_l=dict(r=-.6 * r + 6 * S(i * .5) * env, sy=st), steam_r=dict(r=-.6 * r + 5 * S(i * .5 + 1) * env, sy=st),
                    handle=dict(r=(-4 * pour + (1.5 * S(i * 1.3) if 15 < i < 30 else 0)) * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(14):                                        # it pours: drops off the spout lip, falling
        i0 = 12 + j
        sx, sz = spout(hit_tip(i0))
        vx, vz = c.rng.uniform(-.5, .1), c.rng.uniform(-.3, .6)
        c.pools["drop"].particle(f0 + i0, f0 + i0 + 12, lambda t, sx=sx, sz=sz, vx=vx, vz=vz: (
            sx + .15 + vx * t, sz - .2 + vz * t - 7 * t * t), c.rng, spin=40, grow=(.9, 1.1), fade=(1, 1))
    for j in range(4):
        x0 = c.rng.uniform(-1.4, .8)
        c.pools["steam"].particle(f0 + 4 + j * 6, f0 + 26 + j * 6, lambda t, x0=x0: (x0 + .45 * math.sin(t * 6), 3.0 + 2.6 * t),
                                  c.rng, spin=60, grow=(.45, 1.1), fade=(.85, 0))
    for j in range(5):
        a = TAU * j / 5 + .5
        c.pools["sparkle"].particle(f0 + 14, f0 + 26, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    R = 20

    def pose(i, n):
        u = i / n
        if i < R:                                              # rattling harder, bubbling, steam squeezed down
            k = (i / R) ** 1.4
            return dict(boat=dict(r=2.2 * S(i * 3.1) * k, x=.03 * S(i * 4.3) * k),
                        root=dict(sx=1 + .04 * k, sy=1 - .03 * k),
                        gravy=dict(y=.03 * abs(S(i * 2.2)) * k, sy=1 + .05 * abs(S(i * 1.7)) * k),
                        steam_l=dict(sy=1 - .25 * k, r=3 * S(i * 2.5) * k), steam_r=dict(sy=1 - .28 * k, r=-3 * S(i * 2.7) * k),
                        handle=dict(r=2 * S(i * 3.7) * k))
        t = (i - R) / 30
        env = 1 - c.ease_in_out(max(0, (u - .72) / .28))
        blast = c.ease_out(min(1, t / .1))                     # out of the squeeze in 3 frames, tall, then home
        tall = (1 - c.ease_in_out(min(1, max(0, t - .15) / .35)))
        hop = max(0, S(math.pi * min(1, t / .35)))
        sq0 = 1 - blast
        return dict(root=dict(sx=1 + .04 * sq0 + .05 * imp(t - .35, 3, .3) * env, sy=1 - .03 * sq0 - .06 * imp(t - .35, 3, .3) * env,
                              y=.35 * hop),
                    boat=dict(r=-3 * imp(t, 2.2, .3) * env),
                    gravy=dict(r=4 * imp(t - .05, 2.4, .22) * env, y=.06 * hop),
                    steam_l=dict(sy=(1 - .25 * sq0) + .45 * blast * tall, r=-5 * imp(t, 2.6, .25) * env),
                    steam_r=dict(sy=(1 - .28 * sq0) + .45 * blast * tall, r=5 * imp(t - .03, 2.6, .25) * env),
                    handle=dict(r=-3 * imp(t - .3, 3.5, .25) * env))
    c.run("multi", pose)
    f0 = 301
    for j in range(7):                                         # bubbles popping up off the gravy as it charges
        fs = f0 + 3 + j * 2
        x0 = c.rng.uniform(-3, 2.5)
        c.pools["bubble"].particle(fs, fs + 7, lambda t, x0=x0: (x0, .5 + .5 * t), c.rng, grow=(.15, .45), fade=(1, .2))
    f1 = f0 + R
    c.pools["ring"].particle(f1, f1 + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(5):                                         # the steam blast
        x0 = c.rng.uniform(-1.6, 1.0)
        c.pools["steam"].particle(f1 + j, f1 + 16 + j, lambda t, x0=x0: (x0 * (1 + t), 3.0 + 3.0 * c.ease_out(t)), c.rng,
                                  spin=60, grow=(.6, 1.4), fade=(.9, 0))
    for j in range(8):
        fs = f1 + 1 + j // 2
        vx, vz = c.rng.uniform(-3.0, 3.0), c.rng.uniform(3.0, 5.0)
        x0 = c.rng.uniform(-2.5, 2.0)
        c.pools["drop"].particle(fs, fs + 16, lambda t, vx=vx, vz=vz, x0=x0: (x0 + vx * t, 1.0 + (vz * t - 9 * t * t)),
                                 c.rng, spin=220, grow=(.8, .6), fade=(1, 1))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f1, f1 + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .48) if u < .48 else max(0, 1 - (u - .48) / .4))
