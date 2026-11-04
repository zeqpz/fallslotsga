"""H6 Ear of Corn: the cob, its husk leaves (right, tall left, lower left, the front leaf) and the stalk end, over the
husks' hidden bases (tools/fall/parts/H6.py). The "_rim" layers and cob_fill ride their part and are never posed.
idle   a breeze through the husks: the leaves sway out of step, the tall leaf's curl nods, the cob breathes
land   it drops into its husk: squash, the cob sinks in and bobs back up, the leaves splay and spring closed
hit    the cob ducks into its husk, then the husks flap wide open and the cob POPS up out of them with a twist,
       spraying popcorn, and drops back in with a squash while the leaves flap closed
multi  the cob trembles and glows hotter and hotter, the husks flare out, then BANG - a burst of popcorn all round, the
       cob swells and jolts up, the leaves flung wide, and it all settles"""
import math

FX = ["popcorn", "sparkle"]
S = math.sin
TAU = 2 * math.pi
AX = (math.cos(math.radians(58)), math.sin(math.radians(58)))     # the cob's long axis, up and to the right


def along(d):
    return dict(x=AX[0] * d, y=AX[1] * d)


def cob_point(u):
    """a point on the cob's middle line, u 0 (bottom) .. 1 (tip), in units"""
    return -.9 + 3.3 * u, -1.6 + 5.0 * u


def idle(c):
    def pose(i, n):
        t = i / n
        w = S(TAU * t)                                   # one slow gust a loop
        b = S(TAU * 2 * t)                               # two breaths
        return dict(cob=dict(sx=1 + .012 * b, sy=1 + .016 * b),
                    husk_lt=dict(r=2.6 * w + 1.0 * S(TAU * 3 * t)),
                    husk_ll=dict(r=2.0 * S(TAU * t + 0) * .6 + 1.4 * S(TAU * 2 * t)),
                    husk_r=dict(r=-2.4 * w - .8 * S(TAU * 3 * t)),
                    husk_front=dict(r=-1.2 * S(TAU * 2 * t)),
                    stalk=dict(r=.6 * w))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .08 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.0, .32)
        lag = c.damp(max(0, t - .04), 2.4, .25)
        sink = -.22 * c.damp(t, 2.2, .35)
        p = along(sink)
        return dict(root=dict(sx=1 + .13 * k, sy=1 - .15 * k),
                    cob=dict(x=p["x"], y=p["y"], sx=1 + .04 * k, sy=1 - .04 * k),
                    husk_lt=dict(r=9 * lag), husk_ll=dict(r=7 * lag), husk_r=dict(r=-9 * lag),
                    husk_front=dict(r=-6 * lag), stalk=dict(r=-3 * k))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    def pose(i, n):
        u = i / n
        if i <= 7:                                       # duck: the cob sinks into its husk, the leaves hug it
            e = c.ease_in_out(i / 7)
            p = along(-.28 * e)
            return dict(root=dict(sx=1 + .05 * e, sy=1 - .07 * e),
                        cob=dict(x=p["x"], y=p["y"], sx=1 + .05 * e, sy=1 - .06 * e),
                        husk_lt=dict(r=-4 * e), husk_ll=dict(r=-3 * e), husk_r=dict(r=4 * e), husk_front=dict(r=3 * e))
        t = (i - 7) / 30                                 # 0 .. 1.3 s
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))
        air = max(0, S(math.pi * min(1, t / .55)))       # the pop: up and back in, a bit over half a second
        landk = c.damp(t - .55, 3.2, .3) if t > .55 else 0
        flap = c.damp(t, 1.7, .22)                       # the husks fling open and swing back past closed
        open_ = (1 - math.exp(-t * 18)) * flap
        p = along(-.28 * max(0, 1 - t / .08) + 1.3 * air)
        spin = 9 * S(math.pi * min(1, t / .55)) * (1 if t < .55 else 0)
        return dict(root=dict(sx=1 - .1 * landk, sy=1 + .1 * landk),
                    cob=dict(x=p["x"] * env, y=p["y"] * env, r=-spin * env,
                             sx=(1 - .05 * air + .1 * landk) * 1, sy=1 + .08 * air - .12 * landk),
                    husk_lt=dict(r=24 * open_ * env), husk_ll=dict(r=20 * c.damp(max(0, t - .04), 1.8, .22) * (1 - math.exp(-t * 18)) * env),
                    husk_r=dict(r=-24 * c.damp(max(0, t - .02), 1.75, .22) * (1 - math.exp(-t * 18)) * env),
                    husk_front=dict(r=-14 * open_ * env),
                    stalk=dict(r=5 * S(t * 20) * math.exp(-t * 4) * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(12):                                  # popcorn pops off the cob's sides as it leaves the husk
        fs = f0 + 10 + j // 2 + (j % 2)
        tt = (fs - f0 - 7) / 30
        lift = 1.3 * max(0, S(math.pi * min(1, tt / .55)))
        u = .3 + .55 * ((j * 5) % 12) / 11
        x0, z0 = cob_point(u)
        x0, z0 = x0 + AX[0] * lift, z0 + AX[1] * lift
        side = 1 if j % 2 else -1                        # off the left / right flank of the cob
        px, pz = -AX[1] * side * .55, AX[0] * side * .55
        x0, z0 = x0 + px, z0 + pz
        dx, dz = -AX[1] * side + c.rng.uniform(-.3, .3), AX[0] * side + .35
        dist = c.rng.uniform(1.8, 2.7)
        c.pools["popcorn"].particle(fs, fs + 18, lambda t, x0=x0, z0=z0, dx=dx, dz=dz, dist=dist: (
            x0 + dx * dist * c.ease_out(t), z0 + dz * dist * c.ease_out(t) - 2.8 * t * t), c.rng,
            spin=c.rng.choice((-1, 1)) * 300, grow=(.45, .95), fade=(1, .35))
    for j in range(5):
        a = TAU * j / 5 + .5
        c.pools["sparkle"].particle(f0 + 12, f0 + 24, lambda t, a=a: (.8 + math.cos(a) * (3.0 + 1.3 * c.ease_out(t)),
                                    .9 + math.sin(a) * (3.0 + 1.3 * c.ease_out(t))), c.rng, spin=160, grow=(.7, .05))
    c.glow_curve("hit", lambda u: 0 if u < .17 else math.sin(math.pi * min(1, (u - .17) / .68)) if u < .85 else 0)


def multi(c):
    R = 24                                               # the release frame

    def pose(i, n):
        if i < R:                                        # charge: trembling harder, swelling, the husks flaring
            k = (i / R) ** 1.4
            q = S(i * 2.9) * k
            q2 = S(i * 3.7 + 1) * k
            return dict(cob=dict(x=.05 * q, y=.04 * q2, sx=1 + .06 * k, sy=1 + .06 * k, r=1.5 * q),
                        husk_lt=dict(r=14 * k + 2 * q2), husk_ll=dict(r=11 * k - 2 * q),
                        husk_r=dict(r=-14 * k + 2 * q), husk_front=dict(r=-8 * k + 1.5 * q2),
                        stalk=dict(r=2 * q))
        t = (i - R) / 30
        k = c.damp(t, 2.6, .3)
        e = 1 - c.ease_in_out(min(1, max(0, (i - R) / (n - R))))   # the charge's flare lets go
        p = along(.3 * max(0, k))
        return dict(root=dict(sx=1 + .05 * k, sy=1 + .05 * k),
                    cob=dict(x=p["x"], y=p["y"], sx=1 + .1 * k, sy=1 + .1 * k),
                    husk_lt=dict(r=14 * e + 10 * k), husk_ll=dict(r=11 * e + 8 * k),
                    husk_r=dict(r=-14 * e - 10 * k), husk_front=dict(r=-8 * e - 6 * k), stalk=dict(r=-3 * k))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + R, f0 + R + 12, lambda t: (.6, .7), c.rng, grow=(.5, 1.15), fade=(1, 0))
    for j in range(12):                                  # popcorn bursts out all round the cob
        a = TAU * j / 12 + .2
        x0, z0 = cob_point(.2 + .6 * (j % 4) / 3)
        sp = c.rng.uniform(2.6, 3.6)
        fs = f0 + R + (j % 3)
        c.pools["popcorn"].particle(fs, fs + 15, lambda t, a=a, x0=x0, z0=z0, sp=sp: (
            x0 + math.cos(a) * (.4 + sp * c.ease_out(t)), z0 + math.sin(a) * (.4 + sp * c.ease_out(t)) - 1.6 * t * t),
            c.rng, spin=c.rng.choice((-1, 1)) * 360, grow=(.6, 1.05), fade=(1, .3))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + R, f0 + R + 12, lambda t, a=a: (.6 + math.cos(a) * (3.4 + 1.5 * c.ease_out(t)),
                                    .7 + math.sin(a) * (3.4 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, (u / .57) ** 1.5) if u < .57 else max(0, 1 - (u - .57) / .38))
