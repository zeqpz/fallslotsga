"""L4 Grapes: the leaves (back), the bunch (stem, back grapes, the dark between them) swinging from the top of its stem,
and six front grapes each hanging from its top (tools/fall/parts/L4.py). A heavy, juicy, jelly-soft bunch: it hangs
and swings, and every grape wobbles on its own a beat after the one above it.
idle   the bunch sways gently from its stem like it hangs on the vine, the grapes wobble out of step, the leaves stir
land   it thuds down: the bunch squashes, the grapes jounce one after another from the top down, the leaves flap up
hit    it crouches and bounces; a jiggle ripples down the grapes from top to bottom, the leaves flap like wings,
       sparkles as it comes down
multi  the grapes swell and tremble, charging, then pop out from the bunch a little - the gaps open dark between
       them - and spring back in, top to bottom - ring and sparkles"""
import math

FX = ["sparkle"]
S = math.sin
TAU = 2 * math.pi
GRAPES = ["g_top", "g_left", "g_mid", "g_lowl", "g_lowm", "g_lowr"]
ROW = dict(g_top=0, g_left=1, g_mid=1, g_lowl=2, g_lowm=2, g_lowr=3)            # top to bottom
CENTRE = dict(g_top=(603, 358), g_left=(447, 485), g_mid=(643, 543), g_lowl=(493, 662), g_lowm=(670, 735),
              g_lowr=(800, 822))
MID = (640, 600)                                                                  # the bunch's middle, icon px


def out_dir(g):
    """unit vector from the bunch's middle out through a grape (x right, y up)"""
    dx, dy = CENTRE[g][0] - MID[0], MID[1] - CENTRE[g][1]
    d = math.hypot(dx, dy) or 1
    return dx / d, dy / d


def idle(c):
    K = dict(g_top=(2, 3, 1), g_left=(3, 2, -1), g_mid=(2, 4, 1), g_lowl=(4, 3, -1), g_lowm=(3, 5, 1),
             g_lowr=(2, 3, -1))                                # each grape's own beat: (sway, wobble, side)
    def pose(i, n):
        t = i / n
        p = dict(bunch=dict(r=1.4 * S(TAU * t)),
                 leaves=dict(r=-2.5 * S(TAU * t) + 1.2 * S(TAU * 3 * t)))
        for g in GRAPES:
            a, b, sd = K[g]
            w = S(TAU * b * t)
            p[g] = dict(r=sd * 2.2 * S(TAU * a * t), sx=1 + .018 * w, sy=1 - .022 * w)
        return p
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .08 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.4, .32)
        env = 1 - c.ease_in_out(max(0, (i - 16) / 8))
        p = dict(root=dict(sx=1 + .12 * k, sy=1 - .14 * k),
                 leaves=dict(r=-12 * c.damp(max(0, t - .02), 2.6, .25) * env))
        for g in GRAPES:
            d = .035 * ROW[g]                                  # the jounce runs down the bunch
            j = c.damp(max(0, t - d), 4.0, .3) if t > d else 0
            p[g] = dict(sx=1 + .07 * j * env, sy=1 - .09 * j * env, y=-.06 * j * env)
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    T_UP, T_AIR = 5, 14
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .78) / .22))
        if i <= T_UP:                                          # crouch, the grapes squashing into each other
            e = c.ease_in_out(i / T_UP)
            p = dict(bunch=dict(sx=1 + .06 * e, sy=1 - .08 * e), leaves=dict(r=6 * e))
            for g in GRAPES:
                p[g] = dict(sx=1 + .04 * e, sy=1 - .05 * e)
            return p
        j = i - T_UP
        t = j / 30
        air = S(math.pi * min(1, j / T_AIR))
        landed = c.damp((j - T_AIR) / 30, 3.2, .3) if j > T_AIR else 0
        p = dict(bunch=dict(y=.8 * air * env, sx=1 - .04 * air + .1 * landed * env, sy=1 + .06 * air - .12 * landed * env,
                            r=4 * S(t * 9) * air * env),
                 leaves=dict(r=(16 * S(t * 26) * (air + .6 * abs(landed)) - 10 * air) * env))   # flapping like wings
        for g in GRAPES:
            d = .09 * ROW[g]                                   # a ripple from top to bottom
            q = c.damp(max(0, t - d), 3.6, .2) if t > d else 0
            lift = .5 * max(0, S(math.pi * min(1, max(0, t - d) / .35)))   # each lags the bunch a beat
            p[g] = dict(sx=1 + .09 * q * env, sy=1 - .11 * q * env, r=5 * q * (1 if ROW[g] % 2 else -1) * env,
                        y=-.15 * lift * air * env)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(6):
        a = TAU * j / 6 + .5
        c.pools["sparkle"].particle(f0 + 20, f0 + 32, lambda t, a=a: (.8 + math.cos(a) * (3.3 + 1.2 * c.ease_out(t)),
                                    -.4 + math.sin(a) * (3.6 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    # the halo stays where the bunch rests: low while it is up, full as it comes down, then fades
    c.glow_curve("hit", lambda u: .3 * math.sin(math.pi * u / .41) ** 2 if u < .41 else
                 (math.sin(math.pi / 2 * min(1, (u - .41) / .06)) * max(0, 1 - max(0, u - .5) / .4)))


def multi(c):
    CH = 20
    def pose(i, n):
        if i < CH:                                             # charge: every grape swells and trembles
            k = (i / CH) ** 1.3
            p = dict(bunch=dict(x=.03 * S(i * 2.6) * k, r=1.2 * S(i * 2.1) * k),
                     leaves=dict(r=4 * S(i * 3.1) * k))
            for m, g in enumerate(GRAPES):
                q = S(i * (2.4 + .37 * m) + m)
                p[g] = dict(sx=1 + .07 * k + .015 * q * k, sy=1 + .07 * k - .015 * q * k, x=.025 * q * k,
                            y=.02 * S(i * 3.3 + m) * k)
            return p
        t = (i - CH) / 30                                      # release: they pop out and spring back, top first
        env = 1 - c.ease_in_out(max(0, (i - 33) / 9))
        p = dict(bunch=dict(sx=1 + .05 * c.damp(t, 3, .3) * env, sy=1 + .05 * c.damp(t, 3, .3) * env),
                 leaves=dict(r=-14 * c.damp(max(0, t - .02), 2.4, .25) * env))
        for g in GRAPES:
            d = .035 * ROW[g]
            k = c.damp(max(0, t - d), 2.8, .3) if t > d else 1
            ox, oy = out_dir(g)
            pop = .17 * max(0, k)
            sw = .07 * (1 - c.ease_in_out(min(1, t / .45)))
            p[g] = dict(x=ox * pop * env, y=oy * pop * env, sx=1 + (sw + .06 * k) * env, sy=1 + (sw + .06 * k) * env)
        return p
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + CH, f0 + CH + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.15), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + CH, f0 + CH + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.4 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.4 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u: min(1, u / .48) if u < .48 else max(0, 1 - (u - .48) / .4))


# ---------------------------------------------------------------- pop: the bunch scatters and every grape bursts
# strain  the grapes swell in a ripple down the bunch, taut and shivering
# BLOW    the bunch flies apart - every grape is thrown out from the middle, front ones first - and they burst in the
#         air one after another (each balloons and is gone in a big splat, juice spraying on the way it was going);
#         the stem is flicked up spinning, the leaves flutter off
#         (rebuilt 2026-11-11: the grapes used to burst where they hung, small)
from . import popkit as P                                      # noqa: E402

XFX = {
    "juice": dict(files=["parts:fx_juice"], n=36, size=1.15),
    "splat": dict(files=["parts:fx_splat"], n=15, size=2.6),
    "skin": dict(files=["parts:fx_skin"], n=10, size=.95),
}
WHEN = dict(g_top=12, g_left=13, g_mid=14, g_lowl=15, g_lowm=16, g_lowr=17)


def pop(c):
    B = P.BLOW
    lumps = sorted([b for b in c.extras if b.startswith("lump")], key=lambda b: -c.pivot[b][1])
    stem, lumps = lumps[0], lumps[1:]
    mid = ((MID[0] - 500) / 100, (500 - MID[1]) / 100)
    at = {g: ((CENTRE[g][0] - 500) / 100, (500 - CENTRE[g][1]) / 100) for g in GRAPES}
    when, go = dict(WHEN), {g: B for g in GRAPES}
    for j, b in enumerate(lumps):
        at[b] = c.pivot[b]
        when[b] = 15 + int(j * .9)
        go[b] = B + 1
    out = {g: P.unit(at[g][0] - mid[0], at[g][1] - mid[1]) for g in at}
    vel = {}
    for j, g in enumerate(at):                                 # thrown out from the middle, and up
        sp = 15 + 3.5 * (j % 4)
        vel[g] = (out[g][0] * sp, out[g][1] * sp * .8 + 11, (-1) ** j * (200 + 60 * (j % 3)))

    def flown(g, i):
        vx, vy, spin = vel[g]
        return P.fly(i, go[g], vx, vy, g=30, spin=spin, drag=.9)

    def grape(g, i):
        f = when[g]
        if i > f:
            return dict(a=0)
        if i < go[g]:
            return dict(a=1)
        e = max(0.0, i - f + 2) / 2                            # its last two frames: it balloons
        s = (1.2 if g in WHEN else 1.0) + .35 * e
        return dict(flown(g, i), a=1, sx=s, sy=s)

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            p = dict(root=P.swell(1 + .08 * k, x=.06 * S(i * 3.3) * k), bunch=dict(r=3 * S(i * 2.8) * k))
            for g in GRAPES:
                s = 1 + .24 * k * (.65 + .35 * S(i * 2.6 - ROW[g] * 1.3))
                p[g] = dict(sx=s, sy=s)
            return p
        p = dict(root=P.swell(1.0), bunch=dict(a=0),
                 leaves=P.fly(i, B, -11, 11, g=16, spin=280, drag=1.5, a=P.gone(i, 18, 23),
                              sx=.35 + .65 * abs(P.C((i - B) * .7))))
        for g in at:
            p[g] = grape(g, i)
        p[stem] = P.fly(i, B, 3, 20, g=42, spin=-700, a=P.gone(i, 18, 22))
        return p
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    for g, f in when.items():
        q = flown(g, f)
        x, z = at[g][0] + q["x"], at[g][1] + q["y"]
        big = 1.25 if g in WHEN else .9
        fx["splat"].emit(f, f + 6, lambda t, x=x, z=z: (x, z - .6 * t * t), rng,
                         grow=lambda t, big=big: big * (.5 + 1.2 * (1 - (1 - t) ** 3)), fade=P.tail(.45))
        a0 = math.degrees(math.atan2(vel[g][1] - 6, vel[g][0]))
        P.burst(fx["juice"], rng, f, 4 if g in WHEN else 1, at=(x, z), speed=(18, 32), ang=(a0 - 60, a0 + 60), g=34,
                life=(7, 10), grow=(1.1, .6), aim="tail", spread=.2, drag=3)
        if g in WHEN:
            P.burst(fx["skin"], rng, f, 1, at=(x, z), speed=(14, 22), ang=(a0 - 40, a0 + 40), g=30, life=(6, 8),
                    grow=(1.0, .7), spin=700, drag=2.5)
    c.glow_out(lambda i: .2 + .5 * P.strain(i) if i < B else .9 if i == B else 0.0)
