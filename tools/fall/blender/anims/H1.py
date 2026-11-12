"""H1 Roast Turkey: platter, body, two drumsticks, a wing and three clumps of garnish (tools/fall/parts/H1.py).
idle   the roast breathes on its platter, the drumsticks bob out of step, the wing twitches, steam curls off it
land   it thuds onto the platter: squashes, the drumsticks lag and spring back, the garnish hops, the platter rattles
hit    it crouches and JUMPS off the platter, flailing both drumsticks and flapping its wing, the garnish bounces in
       turn, and lands squashed - a burst of steam and juice
multi  it trembles and swells as it charges (the drumsticks quivering), then puffs up with the drumsticks flung wide,
       the wing open and the garnish thrown up - steam blast and sparks"""
import math

FX = ["steam", "drop", "sparkle"]
S = math.sin
TAU = 2 * math.pi


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * 2 * t)                                     # two breaths a loop
        return dict(body=dict(sx=1 - .012 * b, sy=1 + .018 * b),
                    leg_back=dict(r=3.0 * S(TAU * t)),
                    leg_front=dict(r=-3.5 * S(TAU * t) + 1.2 * S(TAU * 2 * t)),
                    wing=dict(r=2.0 * S(TAU * 3 * t)),
                    garnish_m=dict(y=.02 * max(0, S(TAU * 2 * t))))
    c.run("idle", pose)
    f0 = 1
    for k, fs in enumerate((f0 + 4, f0 + 28, f0 + 50)):
        x0 = c.rng.uniform(-1.4, 1.2)
        c.pools["steam"].particle(fs, fs + 20, lambda t, x0=x0: (x0 + .45 * math.sin(t * 5), 2.4 + 3.0 * t), c.rng,
                                  spin=40, grow=(.35, 1.0), fade=(.8, 0))
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.2, .3)
        lag = c.damp(max(0, t - .03), 2.6, .22)
        hop = lambda d: .22 * max(0, S(math.pi * min(1, max(0, t - d) / .22)))
        return dict(root=dict(sx=1 + .16 * k, sy=1 - .18 * k),
                    body=dict(sy=1 - .05 * k),
                    leg_back=dict(r=-9 * lag), leg_front=dict(r=11 * lag), wing=dict(r=-6 * lag),
                    garnish_l=dict(y=hop(.02), r=4 * S(t * 30) * math.exp(-t * 6)),
                    garnish_m=dict(y=hop(.06)), garnish_r=dict(y=hop(.04), r=-4 * S(t * 30) * math.exp(-t * 6)),
                    platter=dict(sx=1 + .03 * k))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    def pose(i, n):
        u = i / n
        if i <= 6:                                             # crouch
            e = c.ease_in_out(i / 6)
            return dict(body=dict(sx=1 + .1 * e, sy=1 - .14 * e), leg_back=dict(r=-6 * e), leg_front=dict(r=7 * e))
        t = (i - 6) / 30
        air = max(0, S(math.pi * min(1, t / .5)))              # one jump, half a second
        land = c.damp(max(0, t - .5), 3.0, .28) if t > .5 else 0
        flail = S(t * 24) * air
        env = 1 - c.ease_in_out(max(0, (u - .75) / .25))       # everything home by the end
        g = lambda d: .55 * max(0, S(math.pi * min(1, max(0, t - d) / .4)))
        return dict(body=dict(y=1.0 * air * env, sx=(1 - .06 * air + .14 * land), sy=(1 + .1 * air - .16 * land), r=6 * S(t * 7) * air),
                    leg_back=dict(r=(-22 * flail - 8 * air) * env), leg_front=dict(r=(26 * S(t * 24 + 1.3) * air + 10 * air) * env),
                    wing=dict(r=28 * S(t * 30) * air * env),
                    garnish_l=dict(y=g(.12) * env, r=12 * S(t * 18) * air * env), garnish_m=dict(y=g(.2) * env),
                    garnish_r=dict(y=g(.16) * env, r=-12 * S(t * 18) * air * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(4):
        fs = f0 + 8 + j * 3
        x0 = c.rng.uniform(-1.6, 1.6)
        c.pools["steam"].particle(fs, fs + 18, lambda t, x0=x0: (x0 + .5 * math.sin(t * 6), 2.8 + 3.2 * t), c.rng,
                                  spin=60, grow=(.5, 1.3), fade=(.9, 0))
    for j in range(8):                                         # juice flicked off as it flails
        fs = f0 + 10 + j
        a = c.rng.uniform(.3, 2.8)
        vx, vz = 4 * math.cos(a), 4 + 2 * math.sin(a)
        c.pools["drop"].particle(fs, fs + 16, lambda t, vx=vx, vz=vz: (vx * t * .8, 1.6 + (vz * t - 9 * t * t) * .8),
                                 c.rng, spin=200, grow=(.5, .35), fade=(1, 1))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 14, f0 + 26, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    def pose(i, n):
        if i < 18:                                             # charge: trembling harder, swelling
            k = (i / 18) ** 1.3
            q = S(i * 2.7) * k
            return dict(body=dict(x=.06 * q, sx=1 + .07 * k, sy=1 + .07 * k, r=2 * q),
                        leg_back=dict(r=6 * S(i * 3.3) * k), leg_front=dict(r=-7 * S(i * 3.1 + 1) * k),
                        wing=dict(r=5 * S(i * 3.7) * k), garnish_m=dict(y=.05 * abs(q)))
        t = (i - 18) / 30
        k = c.damp(t, 3.0, .28)
        return dict(body=dict(sx=1 + .16 * k, sy=1 + .12 * k, y=.2 * k),
                    leg_back=dict(r=24 * k), leg_front=dict(r=-28 * k), wing=dict(r=-24 * k),
                    garnish_l=dict(y=.5 * max(0, k), r=10 * k), garnish_m=dict(y=.6 * max(0, k)),
                    garnish_r=dict(y=.5 * max(0, k), r=-10 * k))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(5):
        x0 = c.rng.uniform(-1.8, 1.8)
        c.pools["steam"].particle(f0 + 18 + j, f0 + 36 + j, lambda t, x0=x0: (x0 * (1 + t), 2.5 + 3.4 * t), c.rng,
                                  spin=60, grow=(.6, 1.5), fade=(.9, 0))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))


# ---------------------------------------------------------------- pop: overstuffed - it bursts at the joints
# strain  the roast puffs up, quaking, the drumsticks and wing straining at their joints, steam hissing
# BLOW    the body slams flat on the platter and the drumsticks and the wing are shot off it, tumbling end over end;
#         the body gasps back up and withers away in a cloud of steam; the garnish is flung off, berries bouncing;
#         the platter rattles and drops away
from . import popkit as P                                      # noqa: E402

XFX = {
    "puff": dict(files=["steam"], n=8, size=3.2),
    "juice": dict(files=["drop"], n=12, size=1.2),
    "berry": dict(files=["parts:fx_berry"], n=10, size=.85),
    "skin": dict(files=["parts:fx_skin"], n=8, size=.9),
}


def pop(c):
    B = P.BLOW

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            return dict(root=P.swell(1 + .04 * k, x=.05 * S(i * 3.0) * k),
                        body=dict(sx=1 + .14 * k, sy=1 + .17 * k),
                        leg_back=dict(r=11 * S(i * 3.3) * k, y=.2 * k), leg_front=dict(r=-13 * S(i * 3.1 + 1) * k, x=.2 * k),
                        wing=dict(r=9 * S(i * 3.7) * k), platter=dict(sx=1 + .03 * k),
                        garnish_m=dict(y=.1 * abs(S(i * 2.6)) * k))
        t = (i - B) / 30
        z = 1 - .75 * P.st(i, 12, 18)
        body = dict(sx=(1 + .5 * c.damp(t, 3.2, .3)) * z, sy=(1 - .55 * c.damp(t, 3.2, .3)) * z, a=P.gone(i, 14, 18))
        plat = dict(r=7 * S(t * 44) * math.exp(-t * 7), y=-24 * max(0, t - .22) ** 2, sx=1 + .05 * math.exp(-t * 8),
                    a=P.gone(i, 17, 22))
        fl = lambda name, par, want: P.free(c, name, par, want)
        return dict(root=P.swell(1.0), body=body, platter=plat,
                    leg_back=fl("leg_back", body, P.fly(i, B, -7, 23, g=42, spin=760, a=P.gone(i, 20, 24))),
                    leg_front=fl("leg_front", body, P.fly(i, B, 13, 19, g=42, spin=-680, a=P.gone(i, 20, 24))),
                    wing=fl("wing", body, P.fly(i, B, -15, 9, g=34, spin=460, a=P.gone(i, 18, 22))),
                    garnish_l=fl("garnish_l", plat, P.fly(i, B, -11, 10, g=36, spin=300, a=P.gone(i, 15, 19))),
                    garnish_m=fl("garnish_m", plat, P.fly(i, B, 1, 13, g=36, spin=-200, a=P.gone(i, 15, 19))),
                    garnish_r=fl("garnish_r", plat, P.fly(i, B, 11, 10, g=36, spin=-300, a=P.gone(i, 15, 19))))
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    for f, x0 in ((3, -1.2), (5, 1.0)):                        # it hisses
        fx["puff"].emit(f, f + 5, lambda t, x0=x0: (x0 * (1 + t), 2.2 + 2.4 * t), rng, spin=40, grow=(.3, .8),
                        fade=(.8, 0))
    P.burst(fx["puff"], rng, B + 1, 6, at=(-.2, .6), speed=(8, 16), ang=(20, 160), g=-6, life=(10, 13),
            grow=(.5, 1.25), spin=90, spread=1.0, even=True, drag=3.5, fade=lambda t: .95 * (1 - t) ** .8)
    P.burst(fx["juice"], rng, B, 12, at=(-.2, -.2), speed=(22, 36), ang=(15, 165), g=36, life=(10, 14),
            grow=(1.0, .6), aim="tail", spread=1.0, even=True, drag=3)
    P.burst(fx["skin"], rng, B, 8, at=(-.2, 0), speed=(18, 30), ang=(0, 360), g=34, life=(10, 13), grow=(1.0, .7),
            spin=700, spread=1.2, even=True, drag=3)
    P.burst(fx["berry"], rng, B, 10, at=(0, -2.2), speed=(16, 28), ang=(25, 155), g=44, life=(12, 15),
            grow=(1.0, .9), spin=300, spread=2.0, even=True, drag=2)
    c.glow_out(lambda i: .25 + .7 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .1 * P.strain(i) if i < B else 1.16)
