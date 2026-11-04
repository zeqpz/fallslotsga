"""L5 Sunflower: the ring of leaves behind, the petal ring on it and the seed centre (tools/fall/parts/L5.py). A sunny,
spinning pinwheel of a flower: the head turns, the petals fan out as it spins, the centre stays upright (it turns back
against the spin so its shine stays top-left) and does the bouncing.
idle   the petal ring rocks slowly to and fro against the leaves, the centre breathes, the leaves stir
land   it thuds: squashes, the petals fan out and spring back, the centre bobs down and back, the leaves splay
hit    a little wind-up the wrong way, then the whole head spins round a full turn with the petals fanned out, the
       centre bouncing twice on the petals, the leaves flapping - and settles with an overshoot; sparkles fly off
multi  the centre pulses bigger and bigger, the petals trembling, then the head whirls round a turn, fast then
       slowing, petals flung wide - ring and sparkles - and settles"""
import math

FX = ["sparkle"]
S = math.sin
TAU = 2 * math.pi


def upright(spin):
    """the centre's turn that cancels the head's, so the disc's highlight stays where it is drawn"""
    return -spin


def idle(c):
    def pose(i, n):
        t = i / n
        rock = 2.5 * S(TAU * t)
        b = S(TAU * 2 * t)
        return dict(petals=dict(r=rock),
                    centre=dict(r=upright(rock), sx=1 + .018 * b, sy=1 + .018 * b),
                    leaves=dict(r=-.8 * S(TAU * 2 * t), sx=1 + .012 * S(TAU * 3 * t), sy=1 + .012 * S(TAU * 3 * t)))
    c.run("idle", pose)
    f0 = 1
    for fs, (x, z) in ((f0 + 14, (1.6, 1.9)), (f0 + 50, (-1.2, -1.6))):     # a seed glints now and then
        c.pools["sparkle"].particle(fs, fs + 12, lambda t, x=x, z=z: (x, z), c.rng, spin=90, grow=(.35, .05),
                                    fade=(1, .6))
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.4, .32)
        fan = c.damp(max(0, t - .03), 2.8, .3)
        env = 1 - c.ease_in_out(max(0, (i - 16) / 8))
        return dict(root=dict(sx=1 + .12 * k, sy=1 - .14 * k),
                    petals=dict(sx=1 + .05 * fan * env, sy=1 + .05 * fan * env, r=3 * fan * env),
                    centre=dict(y=-.15 * fan * env, sx=1 + .05 * fan * env, sy=1 - .06 * fan * env,
                                r=upright(3 * fan * env)),
                    leaves=dict(sx=1 + .05 * c.damp(max(0, t - .05), 2.4, .3) * env,
                                sy=1 + .05 * c.damp(max(0, t - .05), 2.4, .3) * env))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    W, SP = 6, 22                                              # wind-up frames, spin frames
    def spin_at(i):
        if i <= W:
            return -14 * c.ease_in_out(i / W)
        if i <= W + SP:
            u = (i - W) / SP
            return -14 + (374 + 14) * c.ease_in_out(u)         # one turn and a bit over
        t = (i - W - SP) / 30
        return 360 + 14 * c.damp(t, 1.8, .45)                  # settle back onto the turn

    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        sp = spin_at(i)
        if i > W + SP:
            sp = 360 + (sp - 360) * env                        # home exactly on the turn
        s = max(0, min(1, (i - W) / SP)) if i > W else 0
        fanned = S(math.pi * s) if i <= W + SP else 0          # the petals fan out while it spins
        tb = (i - W) / 30
        bounce = (.35 * abs(S(TAU * tb / .6)) * max(0, 1 - tb / 1.0)) if i > W else 0   # two hops on the petals
        squash = c.damp(max(0, tb - .3), 3.0, .3) if tb > .3 else 0
        petal_r = 4 * S(tb * 14) * fanned if i > W else 0
        return dict(leaves=dict(r=sp, sx=1 + .07 * fanned * abs(S(tb * 18)) * env,
                                sy=1 + .07 * fanned * abs(S(tb * 18)) * env),
                    petals=dict(r=petal_r, sx=1 + .06 * fanned, sy=1 + .06 * fanned),
                    centre=dict(r=upright(sp + petal_r), y=bounce * env,
                                sx=1 + .06 * abs(squash) * env, sy=1 - .07 * abs(squash) * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(10):                                        # flung off the spinning petals' tips
        fs = f0 + W + 4 + j
        a = TAU * j / 10 * 2.3
        c.pools["sparkle"].particle(fs, fs + 12, lambda t, a=a: (math.cos(a + 1.5 * t) * (4.0 + 1.5 * c.ease_out(t)),
                                    math.sin(a + 1.5 * t) * (4.0 + 1.5 * c.ease_out(t))), c.rng, spin=200,
                                    grow=(.75, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    CH, SP = 16, 18                                            # charge, whirl

    def spin_at(i):
        if i <= CH:
            return 0
        if i <= CH + SP:
            u = (i - CH) / SP
            return 360 * (1 - (1 - u) ** 2)                   # fast, then slowing (40 deg a frame at most)
        t = (i - CH - SP) / 30
        return 360 - 10 * S(t * 22) * math.exp(-t * 6)        # rocks to a stop

    def pose(i, n):
        env = 1 - c.ease_in_out(max(0, (i - 34) / 8))
        sp = spin_at(i)
        if i > CH + SP:
            sp = 360 + (sp - 360) * env
        if i <= CH:                                            # charge: the centre pulses up, the petals tremble
            k = (i / CH) ** 1.2
            beat = .5 + .5 * math.cos(TAU * i / 5.5)
            q = S(i * 3.1) * k
            return dict(centre=dict(sx=1 + .1 * k + .03 * beat * k, sy=1 + .1 * k + .03 * beat * k,
                                    r=upright(2.5 * q)),
                        petals=dict(r=2.5 * q, sx=1 - .02 * k, sy=1 - .02 * k),
                        leaves=dict(r=1.2 * S(i * 2.3) * k))
        t = (i - CH) / 30
        fling = c.ease_out(min(1, t / .15)) * (1 - c.ease_in_out(min(1, max(0, t - .3) / .45)))
        sw = .13 * (1 - c.ease_in_out(min(1, t / .6)))
        return dict(leaves=dict(r=sp, sx=1 + .05 * fling * env, sy=1 + .05 * fling * env),
                    petals=dict(sx=1 + .08 * fling * env, sy=1 + .08 * fling * env),
                    centre=dict(r=upright(sp), sx=1 + sw * env, sy=1 + sw * env))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + CH, f0 + CH + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + CH + 1, f0 + CH + 14, lambda t, a=a: (
            math.cos(a + 2 * t) * (3.8 + 1.6 * c.ease_out(t)), math.sin(a + 2 * t) * (3.8 + 1.6 * c.ease_out(t))),
            c.rng, spin=220, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .38) if u < .38 else max(0, 1 - (u - .38) / .5))
