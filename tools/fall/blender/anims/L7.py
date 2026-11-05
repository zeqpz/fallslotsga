"""L7 Turkey Feather: the quill, three vane pieces and the peacock-eye tip, a chain (tools/fall/parts/L7.py).
Each piece rides the one before it, so a bend at the quill is carried up the feather and every joint adds its own:
the tip always does the most, a beat behind the quill - a light, whippy thing.
idle   it sways in a breeze, the bend running up the feather link by link, the eye fluttering at the tip
land   it drops on light: barely a squash at the quill, but the vane flops over and the tip flutters to a stop
hit    it bends back and SWISHES like it's tickling someone - the bend rolling up its joints (the quill barely
       turns: owner, 2026-11-04), the wave whipping out to the tip, feathers
       shaken loose drifting down
multi  it goes stiff - straight as a quill, trembling harder and swelling - then FLICKS: the whip cracks up the feather
       and it shudders back, feathers and sparks flung off"""
import math

from . import lowkit as K

FX = ["feather", "sparkle"]
S = math.sin
TAU = 2 * math.pi
CHAIN = ["vane1", "vane2", "vane3", "eye"]


def imp(t, f, z):
    """a spring knocked at t=0: starts at 0, swings out to ~1 and rings down"""
    if t <= 0:
        return 0.0
    w = TAU * f
    return math.exp(-z * w * t) * S(w * t) / max(.2, math.exp(-z * math.pi / 2))


INK, BROWN, CREAM = (.11, .07, .05, 1), (.55, .27, .11, 1), (.99, .9, .74, 1)


def plume(x, y):
    """a little brown-and-cream barred feather, quill down, the shared sprites' thick dark outline"""
    w = .36 * max(0, 1 - ((y - .1) / .9) ** 2) ** .7 if -.8 < y < 1 else 0
    d = w - abs(x)                                     # in from the edge
    if w <= 0 or d < -.03:
        if abs(x) < .045 and -1 < y < -.5:             # the bare quill
            return CREAM if abs(x) < .025 else INK
        return (0, 0, 0, 0)
    a = K.smooth(-.03, 0, d)
    if d < .065:
        return (*INK[:3], a)
    col = CREAM if int((y + .55 * abs(x)) * 4.5 + 10) % 2 else BROWN
    if abs(x) < .022:
        col = CREAM
    return col


def idle(c):
    K.track_glow(c, "vane2", .9)                             # the middle of the chain: the halo bends with it
    K.paint(c, "feather", "fx_feather_L7", plume)

    def pose(i, n):
        t = i / n
        sway = lambda ph: S(TAU * t - ph) + S(ph)              # one breeze a loop, each link a step behind (0 at 0)
        p = dict(root=dict(r=1.2 * sway(0)), quill=dict(r=.6 * sway(0)))
        for j, b in enumerate(CHAIN):
            p[b] = dict(r=(.9 + .35 * j) * sway(.55 * (j + 1)))
        p["eye"]["r"] += 1.1 * S(TAU * 6 * t) + .5 * S(TAU * 9 * t)   # the tip flutters
        p["vane3"]["r"] += .4 * S(TAU * 6 * t - .8) + .4 * S(.8)
        return p
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: 0)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .72) / .28))
        k = c.damp(t, 3.4, .35) * env
        p = dict(root=dict(sx=1 + .05 * k, sy=1 - .06 * k), quill=dict(r=-1.5 * imp(t, 2.6, .3) * env))
        for j, b in enumerate(CHAIN):                          # the vane flops over a beat late, the tip latest
            p[b] = dict(r=-(3 + 1.6 * j) * imp(t - .035 * (j + 1), 2.4 + .3 * j, .26) * env)
        p["eye"]["r"] += 2.0 * S(t * 55) * math.exp(-t * 4) * min(1, t * 6) * env
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    def pose(i, n):
        u = i / n
        if i <= 7:                                             # cock back
            e = c.ease_in_out(i / 7)
            p = dict(root=dict(r=2 * e, x=-.05 * e, sx=1 - .02 * e), quill=dict(r=1.5 * e))
            for j, b in enumerate(CHAIN):
                p[b] = dict(r=(1.5 + .9 * j) * e)
            return p
        t = (i - 7) / 30
        env = 1 - c.ease_in_out(max(0, (u - .62) / .38))      # home by the end
        w = TAU * 2.9                                          # three swishes
        sw = lambda d: math.cos(w * max(0, t - d))            # starts where the cock-back left it (+1)
        p = dict(root=dict(r=2 * sw(0) * env, x=(-.05 * sw(0) + .06 * S(w * t)) * env,
                           y=.06 * abs(S(w * t)) * env, sy=1 + .02 * abs(S(w * t)) * env),
                 quill=dict(r=1.5 * sw(.02) * env))
        for j, b in enumerate(CHAIN):                          # the S-bend runs up the feather and cracks at the tip
            a = (1.5 + .9 * j) + (1.0 + .8 * j) * c.ease_in_out(min(1, t / .2))
            p[b] = dict(r=a * sw(.035 * (j + 1)) * env)
        p["eye"]["r"] += 3 * S(t * 60) * env * min(1, t * 4)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(7):                                         # feathers shaken loose, drifting down
        fs = f0 + 10 + j * 3
        x0, z0 = c.rng.uniform(1.0, 3.2), c.rng.uniform(1.0, 3.6)
        vx = c.rng.choice((-1, 1)) * c.rng.uniform(1.2, 2.4)
        c.pools["feather"].particle(fs, fs + 24, lambda t, x0=x0, z0=z0, vx=vx: (
            x0 + vx * c.ease_out(t) + .35 * math.sin(t * 9), z0 + 1.2 * t - 3.6 * t * t),
            c.rng, spin=c.rng.uniform(-160, 160), grow=(.9, 1.1), fade=(1, 0))
    for j in range(5):
        a = TAU * j / 5 + .7
        c.pools["sparkle"].particle(f0 + 14, f0 + 26, lambda t, a=a: (2.6 + math.cos(a) * (.6 + 1.4 * c.ease_out(t)),
                                    2.8 + math.sin(a) * (.6 + 1.4 * c.ease_out(t))), c.rng, spin=160, grow=(.7, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    R = 20

    def pose(i, n):
        u = i / n
        if i < R:                                              # goes stiff: straight, trembling harder, swelling
            k = (i / R) ** 1.4
            p = dict(root=dict(r=1.5 * c.ease_in_out(i / R) + .6 * S(i * 2.9) * k, sx=1 + .05 * k, sy=1 + .06 * k))
            p["quill"] = dict(r=.8 * S(i * 3.4 + 1) * k)
            for j, b in enumerate(CHAIN):
                p[b] = dict(r=(.6 + .3 * j) * S(i * (3.1 + .4 * j) + j) * k)
            return p
        t = (i - R) / 30
        env = 1 - c.ease_in_out(max(0, (u - .7) / .3))
        sw = c.ease_in_out(min(1, t / .1))                     # FLICK: swing through in 3 frames
        k = c.damp(t, 2.6, .3)
        back = (1 - c.ease_in_out(min(1, t / .25)))
        p = dict(root=dict(r=(1.5 * back - 3 * sw * k) * env,
                           sx=1 + .06 * back + .04 * imp(t, 3, .4) * env, sy=1 + .06 * back - .03 * imp(t, 3, .4) * env),
                 quill=dict(r=-2.5 * imp(t, 2.8, .3) * env))
        for j, b in enumerate(CHAIN):                          # the crack runs up the feather
            p[b] = dict(r=-(5 + 3.5 * j) * imp(t - .03 * (j + 1), 2.6 + .3 * j, .24) * env)
        return p
    c.run("multi", pose)
    f0 = 301 + R
    c.pools["ring"].particle(f0, f0 + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0, f0 + 12, lambda t, a=a: (math.cos(a) * (3.4 + 1.6 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.6 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(6):                                         # flung off the tip as it cracks
        fs = f0 + 2 + j
        vx, vz = c.rng.uniform(-.5, 3.0), c.rng.uniform(1.5, 3.5)
        c.pools["feather"].particle(fs, fs + 18, lambda t, vx=vx, vz=vz: (
            2.6 + vx * c.ease_out(t) + .3 * math.sin(t * 10), 2.8 + vz * c.ease_out(t) - 3.0 * t * t),
            c.rng, spin=c.rng.uniform(-220, 220), grow=(.9, 1.15), fade=(1, 0))
    c.glow_curve("multi", lambda u: min(1, u / .48) if u < .48 else max(0, 1 - (u - .48) / .4))
