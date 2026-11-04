"""L3 Green Apple: the apple (body, the icon's skin over the bare apple), its stem and the leaf on the stem
(tools/fall/parts/L3.py). A firm, crisp, round apple: it barely gives, it bounces and rocks like a ball, and all the
life is in the leaf.
idle   the apple breathes, the stem sways a touch, the leaf flutters in a breeze; now and then its shine glints
land   a firm thud: a short stiff squash, the stem whips and the leaf flaps down and springs back up
hit    it crouches and bounces up off the reel, the leaf whirling once round the stem as it flies, lands with a squash
       and rocks side to side on its round bottom until it settles
multi  it trembles and swells, shiny (glints run over its skin, the leaf quivering), then pops out bigger with the leaf
       flicked up - a ring and sparkles - and springs back"""
import math

FX = ["glint", "sparkle"]
S = math.sin
C = math.cos
TAU = 2 * math.pi
SHINE = (-2.25, 1.0)                                          # the big highlight on its upper left, units


def twinkle(c, f0, f1, x, z, peak=.7, spin=120):
    """a glint that pops open and shut on the spot (its scale a sine, like symanim's glints)"""
    import symanim as SA
    pool = c.pools["glint"]
    pool.particle(f0, f1, lambda t: (x, z), c.rng, spin=spin, grow=(.1, .1), fade=(1, 1))
    ob = pool.obs[(pool.next - 1) % len(pool.obs)]
    for f in range(f0, f1 + 1):
        SA.key_obj(ob, f, s=max(.02, peak * math.sin(math.pi * (f - f0) / (f1 - f0))))


def idle(c):
    def pose(i, n):
        t = i / n
        b = S(TAU * 2 * t)                                     # two breaths a loop
        gust = .5 + .5 * S(TAU * t)                            # the breeze rises and falls once a loop
        return dict(body=dict(sx=1 + .010 * b, sy=1 + .014 * b),
                    stem=dict(r=2.0 * S(TAU * t)),
                    leaf=dict(r=4.0 * S(TAU * 3 * t) * (.4 + .6 * gust) + 1.5 * S(TAU * 7 * t) * gust,
                              sy=1 - .05 * gust * (.5 + .5 * S(TAU * 6 * t))))
    c.run("idle", pose)
    f0 = 1
    twinkle(c, f0 + 40, f0 + 54, SHINE[0] + .3, SHINE[1] + .2, peak=.9, spin=90)
    c.glow_curve("idle", lambda u: .08 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 4.2, .42)                                # stiff and quick: an apple barely gives
        whip = c.damp(max(0, t - .02), 3.0, .25)
        flap = c.damp(max(0, t - .05), 2.4, .22)
        env = 1 - c.ease_in_out(max(0, (i - 17) / 7))          # arrive at rest smoothly
        return dict(root=dict(sx=1 + .10 * k, sy=1 - .12 * k),
                    stem=dict(r=-8 * whip * env),
                    leaf=dict(r=-20 * flap * env, sy=1 - .15 * max(0, flap) * env))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    T_UP, T_AIR = 6, 18                                        # crouch frames, frames in the air
    def pose(i, n):
        if i <= T_UP:                                          # crouch: squash down, the leaf droops
            e = c.ease_in_out(i / T_UP)
            return dict(body=dict(sx=1 + .08 * e, sy=1 - .11 * e), leaf=dict(r=-8 * e), stem=dict(r=3 * e))
        j = i - T_UP
        if j <= T_AIR:                                         # the bounce: up, stretched, the leaf whirls round
            u = j / T_AIR
            air = S(math.pi * u)
            th = TAU * c.ease_in_out(u)                        # one turn round the stem
            st = max(0, 1 - 4 * u) * .12                       # stretch as it leaves, round again at the top
            return dict(body=dict(y=1.15 * air, sx=1 - .7 * st + .08 * (1 - c.ease_out(min(1, u * 4))), sy=1 + st,
                                  r=-5 * air),
                        stem=dict(r=-6 * air),
                        leaf=dict(sx=C(th), sy=1 - .12 * abs(S(th)), r=10 * air))
        t = (j - T_AIR) / 30                                   # landed: squash, then rock on its round bottom
        k = c.damp(t, 3.6, .35)
        rock = 9 * S(TAU * 1.6 * t) * math.exp(-t * 3.2)
        env = 1 - c.ease_in_out(max(0, (i - 38) / 8))
        return dict(body=dict(sx=1 + .12 * k * env, sy=1 - .14 * k * env, r=rock * env),
                    stem=dict(r=(-1.4 * rock + 6 * k) * env),
                    leaf=dict(r=(-2.2 * rock - 14 * k) * env, sy=1 - .1 * abs(k) * env))
    c.run("hit", pose)
    f0 = 201
    land_f = f0 + T_UP + T_AIR
    for j in range(7):                                         # a crisp burst where it lands
        side = -1 if j % 2 else 1                              # kicked out sideways along the reel from its foot
        x0, vx, vz = side * c.rng.uniform(.6, 1.8), side * c.rng.uniform(1.6, 3.0), c.rng.uniform(.8, 1.8)
        c.pools["sparkle"].particle(land_f, land_f + 12, lambda t, x0=x0, vx=vx, vz=vz: (x0 + vx * c.ease_out(t),
                                    -4.5 + vz * t - 1.2 * t * t), c.rng, spin=160, grow=(.7, .05))
    twinkle(c, f0 + 10, f0 + 20, SHINE[0] + .2, SHINE[1] + .9, peak=1.1)     # it glints at the top of the bounce
    # the halo stays where the apple rests: low while it is up in the air, full as it lands, then fades
    c.glow_curve("hit", lambda u: .25 * math.sin(math.pi * u / .52) ** 2 if u < .52 else
                 (math.sin(math.pi / 2 * min(1, (u - .52) / .06)) * max(0, 1 - max(0, u - .6) / .3)))


def multi(c):
    CH = 22                                                    # charge frames
    def pose(i, n):
        if i < CH:                                             # charge: trembling harder, swelling, the leaf quivers
            k = (i / CH) ** 1.4
            q = S(i * 2.9) * k
            return dict(body=dict(x=.05 * q, sx=1 + .08 * k, sy=1 + .08 * k, r=1.5 * S(i * 2.3) * k),
                        stem=dict(r=4 * S(i * 3.4) * k),
                        leaf=dict(r=7 * S(i * 3.9 + 1) * k - 4 * k, sy=1 - .08 * k))
        t = (i - CH) / 30                                      # release: pops out, the leaf flicks up, springs back
        k = c.damp(t, 3.4, .3)
        flick = c.damp(max(0, t - .03), 2.6, .25)
        env = 1 - c.ease_in_out(max(0, (i - 34) / 8))
        sw = .08 * (1 - c.ease_in_out(min(1, t / .5)))         # the swell lets go
        return dict(body=dict(sx=1 + (sw + .07 * k) * env, sy=1 + (sw + .05 * k) * env),
                    stem=dict(r=-10 * flick * env),
                    leaf=dict(r=22 * flick * env, sy=1 + .04 * max(0, flick) * env))   # (its tip stays in frame)
    c.run("multi", pose)
    f0 = 301
    for j, (dx, dy, fs) in enumerate(((0, 0, 2), (1.6, -.6, 8), (-.4, -1.9, 13), (2.6, 1.4, 17))):   # shine runs
        twinkle(c, f0 + fs, f0 + fs + 10, SHINE[0] + dx, SHINE[1] + dy, peak=.75 + .15 * j, spin=140)
    c.pools["ring"].particle(f0 + CH, f0 + CH + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.15), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .2
        c.pools["sparkle"].particle(f0 + CH, f0 + CH + 12, lambda t, a=a: (math.cos(a) * (3.5 + 1.4 * c.ease_out(t)),
                                    math.sin(a) * (3.5 + 1.4 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .52) if u < .52 else max(0, 1 - (u - .52) / .4))
