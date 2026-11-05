"""L5 Sunflower: the ring of leaves behind, the petal ring on it and the seed centre (tools/fall/parts/L5.py). A sunny,
spinning pinwheel of a flower: the head turns, the petals fan out as it spins, the centre stays upright (it turns back
against the spin so its shine stays top-left) and does the bouncing.
idle   the petal ring rocks slowly to and fro against the leaves, the centre breathes, the leaves stir
land   it thuds: squashes, the petals fan out and spring back, the centre bobs down and back, the leaves splay
hit    it gathers itself, then BEAMS: the petal ring blooms open and shimmers, the leaves spread a beat later, the
       centre bounces twice on the petals and squashes; sparkles burst out (no spinning: owner, 2026-11-04)
multi  the centre pulses bigger and bigger, the petals trembling folded in, then it bursts open: the petals fling
       wide and spring back, the leaves splay, the centre pops - ring and sparkles - and settles"""
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
    W = 6                                                      # the gather before it beams

    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        if i <= W:                                             # it gathers: the centre squats, the petals fold in
            e = c.ease_in_out(i / W)
            return dict(centre=dict(sx=1 + .06 * e, sy=1 - .08 * e), petals=dict(sx=1 - .04 * e, sy=1 - .04 * e),
                        leaves=dict(sx=1 - .02 * e, sy=1 - .02 * e))
        t = (i - W) / 30
        bloom = S(math.pi * min(1, t / .45)) + (.35 * c.damp(t - .45, 2.2, .35) if t > .45 else 0)
        lag = S(math.pi * min(1, max(0, t - .08) / .45)) if t > .08 else 0
        hop = .3 * abs(S(TAU * t / .6)) * max(0, 1 - t / 1.0)   # the centre bounces twice on the petals
        sq = c.damp(max(0, t - .3), 3.0, .3) if t > .3 else 0
        shim = 4 * S(t * 14) * bloom                           # the petals shimmer as they open
        lr = -2.5 * S(t * 9) * lag
        return dict(leaves=dict(r=lr * env, sx=1 + .07 * lag * env, sy=1 + .07 * lag * env),
                    petals=dict(r=shim * env, sx=1 + .12 * bloom * env, sy=1 + .12 * bloom * env),
                    centre=dict(r=upright((lr + shim) * env), y=hop * env,
                                sx=1 + .06 * abs(sq) * env, sy=1 - .07 * abs(sq) * env))
    c.run("hit", pose)
    f0 = 201
    for j in range(10):                                        # flung off the spinning petals' tips
        fs = f0 + W + 4 + j
        a = TAU * j / 10 * 2.3
        c.pools["sparkle"].particle(fs, fs + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.6 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.6 * c.ease_out(t))), c.rng, spin=200,
                                    grow=(.75, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    CH = 16                                                    # charge, then it bursts open

    def pose(i, n):
        env = 1 - c.ease_in_out(max(0, (i - 34) / 8))
        if i <= CH:                                            # charge: the centre pulses up, the petals tremble
            k = (i / CH) ** 1.2
            beat = .5 + .5 * math.cos(TAU * i / 5.5)
            q = S(i * 3.1) * k
            return dict(centre=dict(sx=1 + .1 * k + .03 * beat * k, sy=1 + .1 * k + .03 * beat * k,
                                    r=upright(2.5 * q)),
                        petals=dict(r=2.5 * q, sx=1 - .03 * k, sy=1 - .03 * k),
                        leaves=dict(r=1.2 * S(i * 2.3) * k, sx=1 - .02 * k, sy=1 - .02 * k))
        t = (i - CH) / 30
        burst = c.damp(t, 1.8, .4)                             # the petals fling wide open and spring back
        lag = c.damp(max(0, t - .07), 1.8, .4)
        sw = .13 * (1 - c.ease_in_out(min(1, t / .6)))
        shim = 3 * S(t * 16) * math.exp(-t * 3)
        lr = -2 * S(t * 8) * math.exp(-t * 3)
        return dict(leaves=dict(r=lr * env, sx=1 + .08 * lag * env, sy=1 + .08 * lag * env),
                    petals=dict(r=shim * env, sx=1 + .15 * burst * env, sy=1 + .15 * burst * env),
                    centre=dict(r=upright((lr + shim) * env), y=.12 * S(math.pi * min(1, t / .4)) * env,
                                sx=1 + sw * env, sy=1 + sw * env))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + CH, f0 + CH + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + CH + 1, f0 + CH + 14, lambda t, a=a: (
            math.cos(a) * (3.8 + 1.6 * c.ease_out(t)), math.sin(a) * (3.8 + 1.6 * c.ease_out(t))),
            c.rng, spin=220, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .38) if u < .38 else max(0, 1 - (u - .38) / .5))
