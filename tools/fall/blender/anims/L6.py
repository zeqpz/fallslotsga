"""L6 Candy Corn: the yellow base, the orange middle on it and the white tip on that (tools/fall/parts/L6.py), each
squashing about its own bottom edge. A wobbly sugar jelly stack: every move starts at the base and runs up to the tip
a beat later, and the tip always gets the last word.
idle   a slow jelly wave runs up the stack, base to middle to tip, the tip nodding at the top of it
land   a big squash, then the bands bounce back up one after the other, the tip last and wobbling
hit    it crouches and hops; in the air the bands stretch apart along the candy, then snap back together as it lands
       with a squash, the tip wobbling side to side - sparkles
multi  the bands tremble and swell, charging, then pop apart with a ring and sparkles and spring back, settling in a
       wobble"""
import math

FX = ["sparkle"]
S = math.sin
C = math.cos
TAU = 2 * math.pi
AX = (.29, .96)                                               # up along the candy (it leans right), unit


def wave(t, cycles, lag):
    """a sine `lag` radians behind, minus its value at the start (a cosine of the same beat) - so it is 0 at the
    start and end of the loop and loops seamlessly"""
    return S(TAU * cycles * t - lag) + S(lag) * C(TAU * cycles * t)


def along(d):
    return dict(x=AX[0] * d, y=AX[1] * d)


def idle(c):
    def pose(i, n):
        t = i / n
        w0, w1, w2 = wave(t, 2, 0), wave(t, 2, .9), wave(t, 2, 1.8)
        return dict(base=dict(sx=1 - .014 * w0, sy=1 + .022 * w0),
                    middle=dict(sx=1 - .016 * w1, sy=1 + .026 * w1),
                    tip=dict(sx=1 - .018 * w2, sy=1 + .03 * w2, r=-2.2 * wave(t, 2, 2.6)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .08 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        env = 1 - c.ease_in_out(max(0, (i - 16) / 8))
        k = c.damp(t, 3.0, .3)
        k1 = c.damp(max(0, t - .05), 3.0, .28) if t > .05 else 0
        k2 = c.damp(max(0, t - .1), 2.8, .25) if t > .1 else 0
        return dict(root=dict(sx=1 + .16 * k, sy=1 - .2 * k),
                    middle=dict(sx=1 + .06 * k1 * env, sy=1 - .1 * k1 * env),
                    tip=dict(sx=1 + .07 * k2 * env, sy=1 - .12 * k2 * env, r=-7 * S(t * 24) * math.exp(-t * 5) * env))
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    T_UP, T_AIR = 5, 15
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))
        if i <= T_UP:                                          # crouch, the stack squashing down from the top
            e = c.ease_in_out(i / T_UP)
            return dict(base=dict(sx=1 + .08 * e, sy=1 - .1 * e), middle=dict(sx=1 + .05 * e, sy=1 - .08 * e),
                        tip=dict(sx=1 + .04 * e, sy=1 - .1 * e))
        j = i - T_UP
        air = S(math.pi * min(1, j / T_AIR))
        t = (j - T_AIR) / 30 if j > T_AIR else 0
        landed = c.damp(t, 3.2, .3) if j > T_AIR else 0
        if j <= T_AIR:                                         # apart in the air, shut again as it comes down
            s1, s2 = .16 * air, .18 * S(math.pi * min(1, j / (T_AIR - 1))) if j < T_AIR - 1 else 0
        else:                                                  # the landing jams them together, they spring back
            s1 = -.05 * S(TAU * 3 * t) * math.exp(-t * 5)
            s2 = -.06 * S(TAU * 3 * max(0, t - .03)) * math.exp(-t * 5)
        wob = 9 * S(j * .62) * (air + .7 * abs(landed))
        m = along(s1 * env)
        tp = along(s2 * env)
        return dict(base=dict(y=.6 * air * env, sx=1 - .04 * air + .14 * landed * env,
                              sy=1 + .03 * air - .16 * landed * env, r=-3 * air),
                    middle=dict(m, sx=1 - .03 * air + .06 * landed * env, sy=1 + .05 * air - .08 * landed * env),
                    tip=dict(tp, r=wob * env, sx=1 - .02 * air, sy=1 + .06 * air - .1 * landed * env))
    c.run("hit", pose)
    f0 = 201
    land_f = f0 + T_UP + T_AIR
    for j in range(8):
        side = -1 if j % 2 else 1
        x0, vx, vz = side * c.rng.uniform(.8, 2.4), side * c.rng.uniform(1.6, 3.0), c.rng.uniform(.8, 1.8)
        c.pools["sparkle"].particle(land_f, land_f + 12, lambda t, x0=x0, vx=vx, vz=vz: (x0 + vx * c.ease_out(t),
                                    -4.6 + vz * t - 1.2 * t * t), c.rng, spin=160, grow=(.7, .05))
    # the halo stays where the candy rests: low while it is up, full as it lands, then fades
    # (and it waits for the landing squash to spring back, or the resting halo shows round the squashed candy)
    c.glow_curve("hit", lambda u: .3 * math.sin(math.pi * u / .43) ** 2 if u < .43 else
                 (math.sin(math.pi / 2 * min(1, max(0, u - .5) / .12)) * max(0, 1 - max(0, u - .62) / .3)))


def multi(c):
    CH = 18
    def pose(i, n):
        if i < CH:                                             # charge: each band trembles and swells
            k = (i / CH) ** 1.3
            q0, q1, q2 = S(i * 2.7), S(i * 3.3 + 1), S(i * 3.9 + 2)
            return dict(base=dict(x=.03 * q0 * k, sx=1 + .05 * k, sy=1 + .05 * k),
                        middle=dict(along(.03 * k), x=.035 * q1 * k + AX[0] * .03 * k, sx=1 + .06 * k, sy=1 + .06 * k),
                        tip=dict(along(.05 * k), x=.04 * q2 * k + AX[0] * .05 * k, r=4 * q2 * k, sx=1 + .07 * k,
                                 sy=1 + .07 * k))
        t = (i - CH) / 30                                      # pop: they burst apart and spring back
        env = 1 - c.ease_in_out(max(0, (i - 32) / 10))
        k1 = c.damp(t, 2.8, .3)
        k2 = c.damp(max(0, t - .03), 2.6, .28)
        sw = .06 * (1 - c.ease_in_out(min(1, t / .5)))         # (the tip must stay inside the frame)
        return dict(base=dict(sx=1 + (sw + .05 * k1) * env, sy=1 + (sw - .05 * k1) * env),
                    middle=dict(along(.13 * k1 * env), sx=1 + (sw + .04 * k1) * env, sy=1 + (sw + .02 * k1) * env),
                    tip=dict(along(.13 * k2 * env), r=10 * S(t * 20) * math.exp(-t * 4) * env,
                             sx=1 + (sw + .05 * k2) * env, sy=1 + (sw + .03 * k2) * env))
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + CH, f0 + CH + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.15), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + CH, f0 + CH + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))
