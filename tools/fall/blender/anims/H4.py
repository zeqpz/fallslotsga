"""H4 Pilgrim Hat: the brim, the crown, the band round it and the gold buckle (tools/fall/parts/H4.py).
Its character: a stiff, proper puritan hat that can't help showing off its buckle.
idle   the hat breathes - the crown rises and settles a hair, the brim spreads - and the buckle glints now and then
land   it lands brim first: the brim flexes flat and springs, the crown sinks into it and bobs up a beat later
hit    it bows (crouch, crown tipping forward), then hops and doffs itself - tipping back, the crown bending the
       other way and wobbling as it lands; the buckle pops forward, swells and flashes
multi  the hat trembles stiffer and stiffer while the buckle swells with light, then it jumps, the buckle flashes
       big (rays, ring, sparks) and the crown wobbles as it all settles"""
import math

FX = ["glint", "sparkle"]
S = math.sin
TAU = 2 * math.pi
BUCKLE = (-.6, -1.15)                     # the buckle's middle, units (icon px (440, 615))


def glint(c, f, dx=0.0, dy=0.0, size=(.15, .9)):
    """a glint flaring on the buckle's top corner and dying"""
    c.pools["glint"].particle(f, f + 10, lambda t: (BUCKLE[0] - .8 + dx, BUCKLE[1] + 1.0 + dy), c.rng, spin=90,
                              grow=size, fade=(1, 0))


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * 2 * t)
        return dict(brim=dict(sx=1 + .006 * b),
                    crown=dict(sy=1 + .014 * b, sx=1 - .006 * b, r=.8 * S(TAU * t)))
    c.run("idle", pose)
    glint(c, 1 + 20)
    glint(c, 1 + 56, dx=1.5, dy=-.6, size=(.1, .6))
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.4, .32)
        lag = c.damp(max(0, t - .05), 3.0, .28)
        return dict(root=dict(sx=1 + .08 * k, sy=1 - .1 * k),
                    brim=dict(sx=1 + .07 * k, sy=1 - .2 * k),
                    crown=dict(sy=1 - .1 * lag, sx=1 + .05 * lag, r=2 * S(t * 20) * math.exp(-t * 6)),
                    buckle=dict(sx=1 + .05 * max(0, lag), sy=1 + .05 * max(0, lag)))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))
        if i <= 8:                                                 # a bow: the crown tips forward, the brim dips
            e = c.ease_in_out(i / 8)
            return dict(brim=dict(sy=1 - .08 * e, sx=1 + .03 * e), crown=dict(r=-7 * e, sy=1 - .05 * e))
        t = (i - 8) / 30
        air = max(0, S(math.pi * min(1, t / .48)))                 # the hop, about half a second
        land = c.damp(max(0, t - .48), 3.4, .28) if t > .48 else 0
        rel = 1 - c.ease_out(min(1, t / .12))                      # the bow lets go
        pop = max(0, S(math.pi * min(1, max(0, t - .06) / .55)))   # the buckle swells and shrinks back
        return dict(brim=dict(y=.75 * air * env, r=3 * air * S(min(1, t / .48) * math.pi * .9) * env,
                              sx=1 + (.03 * rel + .08 * land) * env, sy=1 - (.08 * rel - .04 * air + .14 * land) * env),
                    crown=dict(r=(-7 * rel + 12 * air + 7 * S(t * 16) * math.exp(-t * 2.5) * (t > .4)) * env,
                               sy=1 + (.06 * air - .1 * land) * env, sx=1 - (.03 * air - .06 * land) * env),
                    buckle=dict(sx=1 + .28 * pop * env, sy=1 + .28 * pop * env, y=-.05 * pop * env,
                                r=-6 * pop * S(t * 10) * env))
    c.run("hit", pose)
    f0 = 201
    glint(c, f0 + 13, size=(.3, 1.6))
    glint(c, f0 + 17, dx=1.6, dy=-.7, size=(.2, 1.1))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 14, f0 + 28, lambda t, a=a: (BUCKLE[0] + math.cos(a) * (1.4 + 2.2 * c.ease_out(t)),
                                    BUCKLE[1] + .6 + math.sin(a) * (1.4 + 2.2 * c.ease_out(t))), c.rng, spin=160,
                                    grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    def pose(i, n):
        if i < 18:                                                 # stiff trembling, the buckle charging
            k = (i / 18) ** 1.3
            q = S(i * 3.1) * k
            return dict(brim=dict(x=.04 * q, sx=1 + .02 * k, sy=1 - .03 * k),
                        crown=dict(r=2.2 * q, sy=1 + .03 * k),
                        buckle=dict(sx=1 + .16 * k + .03 * abs(q), sy=1 + .16 * k + .03 * abs(q), r=3 * S(i * 4.3) * k))
        t = (i - 18) / 30
        ramp = min(1, (i - 17) / 3)
        air = max(0, S(math.pi * min(1, t / .42)))
        land = c.damp(max(0, t - .42), 3.4, .28) if t > .42 else 0
        fade = 1 - c.ease_in_out(min(1, max(0, (i - 34) / 8)))
        bk = c.damp(t, 2.6, .35)
        return dict(brim=dict(y=.55 * air, sx=1 + .08 * land * fade, sy=1 - .14 * land * fade),
                    crown=dict(r=-6 * S(t * 15) * math.exp(-t * 3) * ramp, sy=1 + .07 * air - .08 * land * fade),
                    buckle=dict(sx=1 + max(0, .16 + .2 * bk) * ramp * fade + .16 * (1 - ramp),
                                sy=1 + max(0, .16 + .2 * bk) * ramp * fade + .16 * (1 - ramp)))
    c.run("multi", pose)
    f0 = 301
    c.pools["rays"].particle(f0 + 18, f0 + 32, lambda t: (BUCKLE[0], BUCKLE[1] + .3), c.rng, spin=40, grow=(.4, 1.0),
                             fade=(1, 0))
    c.pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for f in (f0 + 6, f0 + 12, f0 + 18):
        glint(c, f, size=(.2, 1.0 + (f - f0) / 14))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))


# ---------------------------------------------------------------- pop: the buckle pings off and the hat comes apart
# strain  the crown screws itself down onto the brim, the whole hat quivering stiffly, the buckle swelling and glinting
# BLOW    PING - the buckle shoots off toward us, spinning and flashing; the crown is fired straight up off the brim
#         and tips over, its band slipping off it; the brim skims away flat like a thrown plate; a puff of hat dust
from . import popkit as P                                      # noqa: E402

XFX = {
    "dust": dict(files=["parts:fx_dust"], n=6, size=2.2, depth=.2),
    "ping": dict(files=["sparkle_w"], n=8, size=1.8),
    "spark": dict(files=["sparkle"], n=8, size=1.3),
}


def pop(c):
    B = P.BLOW

    def buckle_at(i):
        return P.fly(i, B, -8, 17, g=30, spin=640)

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            return dict(root=P.swell(1 + .06 * k, x=.05 * S(i * 3.0) * k), brim=dict(sx=1 + .07 * k, sy=1 - .06 * k),
                        crown=dict(y=-.3 * k, sy=1 - .17 * k, sx=1 + .07 * k, r=2.5 * S(i * 3.2) * k),
                        buckle=dict(sx=1 + .38 * k, sy=1 + .38 * k, r=10 * S(i * 3.6) * k))
        t = (i - B) / 30
        brim = P.fly(i, B, -9, 1.5, g=26, drag=1.2, a=P.gone(i, 17, 22))      # (no turn or squash: its riders stay true)
        crown = P.fly(i, B, 3, 23, g=40, spin=-190, a=P.gone(i, 19, 23))
        s = 1.38 + 1.5 * t                                     # it comes at us
        buckle = dict(buckle_at(i), sx=s, sy=s, a=P.gone(i, 17, 21))
        slip = max(0.0, t - .1)
        return dict(root=P.swell(1.0), brim=brim, crown=P.free(c, "crown", brim, crown), band=dict(a=0),
                    band_bare=dict(a=P.gone(i, 16, 20), y=-26 * slip ** 2, x=-4 * slip, r=50 * slip,
                                   sx=1 + .5 * slip),
                    buckle=P.free(c, "buckle", crown, buckle))
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    bx, bz = c.pivot["buckle"]
    for f in (3, 5, 7):                                        # the buckle glints as it strains
        fx["ping"].emit(f, f + 3, lambda t: (bx + .2, bz + .2), rot=15 * f, spin=60,
                        grow=lambda t: .2 + .8 * S(math.pi * t), fade=(1, .6))
    P.flash(fx["ping"], B, (bx, bz), size=(.5, 2.2), life=4, spin=70)
    for j in range(5):                                         # sparks trailing the buckle
        f = B + 1 + j * 2
        q = buckle_at(f)
        fx["spark"].emit(f, f + 5, lambda t, q=q: (bx + q["x"], bz + q["y"] - .6 * t), rng, spin=200,
                         grow=(1.0, .2), fade=P.tail(.5))
    P.burst(fx["dust"], rng, B, 6, at=(.2, -.6), speed=(8, 16), ang=(20, 160), g=-4, life=(10, 13), grow=(.5, 1.2),
            spin=120, spread=1.2, even=True, drag=3.5, fade=lambda t: .9 * (1 - t))
    c.glow_out(lambda i: .25 + .7 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .1 * P.strain(i) if i < B else 1.16)
