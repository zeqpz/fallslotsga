"""H3 Cornucopia: the wicker horn (its leaves tucked behind the fruit stay on it), its curled tip, the corn, the apple in
the horn's mouth, the pumpkin, the two red apples (with the red leaf on them), the gold leaf in front and the grapes
(tools/fall/parts/H3.py; the *_fill layers are the plate-painted hidden parts, carried by the fruit above them).
Its character: a horn of plenty that can't hold its harvest in - the fruit is always about to spill.
idle   the fruit bob gently out of step, the grapes sway on their stem, the horn's tip curls and uncurls
land   the horn thumps down, the fruit jostle up in a ripple and settle, the tip whips
hit    the fruit pop out of the horn one after another - apple, corn, pumpkin, apples, grapes - each with a squash
       and stretch, and drop back home; the horn kicks with every pop, leaves flutter out
multi  the horn shakes harder and harder, the fruit rattling in it, then it bursts: everything spills out of the
       mouth at once and bounces home - a ring, sparkles and a gust of leaves"""
import math

FX = ["leaf", "sparkle"]
S = math.sin
TAU = 2 * math.pi


def hop(c, t, h, T=.4, dx=0.0):
    """one pop: a quick squat, a flight of h units (T s), a squashed landing that springs out. t s from its start."""
    if t <= 0:
        return {}
    if t < .1:
        a = .1 * S(math.pi * t / .1)
        return dict(sx=1 + a, sy=1 - a)
    if t < .1 + T:
        u = (t - .1) / T
        s = .13 * (1 - 2 * u)
        return dict(x=dx * S(math.pi * u), y=h * 4 * u * (1 - u), sx=1 - .6 * s, sy=1 + s)
    k = c.damp(t - .1 - T, 4.0, .3)
    return dict(sx=1 + .1 * k, sy=1 - .13 * k)


def faded(p, env):
    """a pose's channels eased toward rest by env (1 = as is, 0 = rest)"""
    return {k: (v - 1) * env + 1 if k in ("sx", "sy") else v * env for k, v in p.items()}


def idle(c):
    def pose(i, n):
        t = i / n
        return dict(horn=dict(sy=1 + .006 * S(TAU * 2 * t)),
                    horn_tip=dict(r=2.4 * S(TAU * t)),
                    corn=dict(r=-1.6 * S(TAU * t), sy=1 + .02 * S(TAU * 2 * t) ** 2),
                    apple_top_fill=dict(y=.035 * S(TAU * 2 * t + 0) ** 2 * (1 if S(TAU * 2 * t) > 0 else 0)),
                    pumpkin_fill=dict(sx=1 - .012 * S(TAU * 3 * t), sy=1 + .018 * S(TAU * 3 * t)),
                    apples_fill=dict(y=.03 * max(0, S(TAU * 2 * t + math.pi)) ** 2, r=.8 * S(TAU * t)),
                    grapes=dict(r=2.2 * S(TAU * 2 * t)),
                    leaf_front=dict(r=-2.0 * S(TAU * 3 * t)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .1 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        k = c.damp(t, 3.2, .3)
        p = dict(root=dict(sx=1 + .13 * k, sy=1 - .15 * k),
                 horn_tip=dict(r=-8 * c.damp(max(0, t - .03), 3.0, .25)))
        for name, d in (("apple_top_fill", .02), ("corn", .05), ("pumpkin_fill", .08), ("apples_fill", .11),
                        ("grapes", .14)):
            j = .16 * max(0, S(math.pi * min(1, max(0, t - d) / .18)))
            p[name] = dict(y=j * (.6 if name == "corn" else 1))
        p["grapes"]["r"] = 6 * S(t * 26) * math.exp(-t * 6)
        p["leaf_front"] = dict(r=7 * S(t * 30) * math.exp(-t * 7))
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: 0)


def hit(c):
    order = (("apple_top_fill", 2, .55, -.1), ("corn", 7, .35, -.15), ("pumpkin_fill", 12, .5, -.2),
             ("apples_fill", 17, .5, -.25), ("grapes", 22, .55, .05))

    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))            # everything home by the end
        p = {}
        kick = 0
        for name, f, h, dx in order:
            t = (i - f) / 30
            q = hop(c, t, h, .4, dx)
            if name == "corn":                                     # the corn springs on its hidden butt: a lean
                q = dict(sx=q.get("sx", 1), sy=q.get("sy", 1) + .5 * q.get("y", 0), r=18 * q.get("y", 0),
                         y=.25 * q.get("y", 0))
            p[name] = faded(q, env)
            if 0 < t < .3:
                kick += S(math.pi * t / .3) * (1 if f % 2 else -1)
        p["grapes"]["r"] = 10 * S(max(0, i - 22) / 30 * 18) * math.exp(-max(0, i - 22) / 30 * 3) * env
        p["horn"] = dict(r=1.6 * kick * env, sy=1 - .02 * abs(kick) * env)
        p["horn_tip"] = dict(r=6 * S(u * TAU * 2) * env)
        p["leaf_front"] = dict(r=9 * S(i * .7) * math.exp(-max(0, i - 20) / 10) * (i > 20) * env)
        return p
    c.run("hit", pose)
    f0 = 201
    for j in range(7):                                             # leaves shaken out of the horn's mouth
        fs = f0 + 6 + 3 * j
        x0, vx = c.rng.uniform(-1.6, .4), c.rng.uniform(-2.8, -.6)
        c.pools["leaf"].particle(fs, fs + 22, lambda t, x0=x0, vx=vx: (x0 + vx * t + .4 * S(t * 9), 1.2 + 2.6 * t - 3.2 * t * t),
                                 c.rng, spin=240, grow=(.5, .45), fade=(1, 0))
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.4 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.4 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u: math.sin(math.pi * min(1, u / .9)) if u < .9 else 0)


def multi(c):
    # where each piece spills to (units): out of the mouth, down and to the left
    spill = dict(apple_top_fill=(-.35, .55, 14), corn=(-.2, .25, 22), pumpkin_fill=(-.45, .45, -8),
                 apples_fill=(-.55, .35, 16), grapes=(-.15, .3, -16), leaf_front=(-.35, -.05, 25))

    def pose(i, n):
        if i < 18:                                                 # the horn shakes, the fruit rattle in it
            k = (i / 18) ** 1.4
            q = S(i * 2.8) * k
            p = dict(horn=dict(x=.06 * q, r=2.5 * q, sx=1 + .03 * k, sy=1 + .03 * k), horn_tip=dict(r=7 * S(i * 3.3) * k))
            for j, name in enumerate(spill):
                p[name] = dict(y=.05 * abs(S(i * 3.1 + j * 1.7)) * k, r=3 * S(i * 3.7 + j) * k)
            return p
        t = (i - 18) / 30
        out = max(0, S(math.pi * min(1, t / .45)))                 # out and back in in 0.45 s
        land = c.damp(max(0, t - .45), 3.6, .3) if t > .45 else 0
        fade = 1 - c.ease_in_out(min(1, max(0, (i - 34) / 8)))
        ramp = min(1, (i - 17) / 3)
        p = dict(horn=dict(r=-4 * out * ramp, sx=1 + .06 * out, sy=1 - .04 * out + .03 * land * fade),
                 horn_tip=dict(r=-12 * out + 5 * land * fade))
        for name, (dx, dy, rr) in spill.items():
            p[name] = dict(x=dx * out, y=dy * out, r=rr * out, sx=1 + .08 * land * fade, sy=1 - .1 * land * fade)
        return p
    c.run("multi", pose)
    f0 = 301
    c.pools["ring"].particle(f0 + 18, f0 + 30, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0 + 18, f0 + 30, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    for j in range(9):
        fs = f0 + 18 + j
        a = c.rng.uniform(1.9, 3.6)
        sp = c.rng.uniform(3, 4.5)
        c.pools["leaf"].particle(fs, fs + 20, lambda t, a=a, sp=sp: (-1 + math.cos(a) * sp * t, .5 + math.sin(a) * sp * t - 2 * t * t),
                                 c.rng, spin=300, grow=(.55, .4), fade=(1, 0))
    c.glow_curve("multi", lambda u: min(1, u / .43) if u < .43 else max(0, 1 - (u - .43) / .4))


# ---------------------------------------------------------------- pop: the horn bursts its wicker
# strain  the horn squeezes and shudders, the fruit crowding out of its mouth, the tip curling tighter
# BLOW    the harvest is FIRED out of the mouth in a fan - corn, apple, pumpkin, apples, grapes - each tumbling its
#         own way and swelling toward us; the horn bursts into four rings of wicker that spin apart from the mouth
#         back to the neck, its curled tip springing off; a flash, leaves, berries and splinters of wicker
#         (rebuilt 2026-11-11: it used to shrivel in place with the fruit dribbling out)
from . import popkit as P                                      # noqa: E402

XFX = {
    "leaf": dict(files=["leaf_red", "leaf_orange", "leaf_gold"], n=12, size=1.7),
    "berry": dict(files=["parts:fx_berry"], n=12, size=.85),
    "wicker": dict(files=["parts:fx_wicker"], n=14, size=1.3),
    "flash": dict(files=["sparkle_w"], n=2, size=3.2),
}
# what leaves the horn: (bone, frame it goes, vx, vy, gravity, spin, fade from, to, how much it swells a second)
SPILL = [("corn", 8, -9, 25, 44, 620, 19, 24, .9), ("apple_top_fill", 8, 4, 28, 46, -520, 19, 24, 1.1),
         ("pumpkin_fill", 9, -14, 17, 42, 420, 20, 25, 1.4), ("apples_fill", 9, -18, 9, 36, 340, 19, 24, 1.0),
         ("grapes", 10, 12, 18, 44, -420, 19, 24, 1.0), ("leaf_maple", 8, -6, 19, 22, 360, 17, 22, 0),
         ("leaf_gold", 10, 13, 15, 24, -420, 17, 22, 0), ("leaf_vine", 11, 15, 6, 22, -360, 17, 22, 0)]
MOUTH = (-.6, -.6)


def pop(c):
    B = P.BLOW
    rings = sorted([b for b in c.extras if b.startswith("ring")])
    mid = (.2, -.3)
    rv = {}
    for j, b in enumerate(rings):                              # each ring away from the horn's middle, and up
        ux, uy = P.unit(c.pivot[b][0] - mid[0], c.pivot[b][1] - mid[1])
        rv[b] = (B + j, ux * 11 + 3, uy * 9 + 13, (-1) ** j * (380 + 90 * j))

    def pose(i, n):
        k = P.strain(i)
        if i < B:
            q = S(i * 3.3) * k
            p = dict(root=P.swell(1 + .09 * k, x=.08 * q),
                     horn=dict(sx=1 - .07 * k + .03 * q, sy=1 + .08 * k - .03 * q), horn_tip=dict(r=26 * k),
                     leaf_front=dict(r=10 * q), leaf_red=dict(r=-10 * q))
            for j, (b, *_) in enumerate(SPILL[:5]):            # crowding out of the mouth
                p[b] = dict(x=-.26 * k + .06 * S(i * 3.4 + j) * k, y=-.14 * k + .06 * S(i * 2.9 + j) * k,
                            sx=1 + .06 * k, sy=1 + .06 * k)
            return p
        p = dict(root=P.swell(1.0), horn=dict(a=0),
                 horn_tip=P.fly(i, B, 9, 21, g=42, spin=-900, a=P.gone(i, 18, 22)))
        for b, (f, vx, vy, sp) in rv.items():
            p[b] = P.fly(i, f, vx, vy, g=38, spin=sp, drag=.8, a=P.gone(i, 18, 23)) if i >= f else dict(a=1)
        for b, f, vx, vy, g, sp, a0, a1, z in SPILL:
            if i >= f:
                s = 1.06 + z * (i - f) / 30
                p[b] = P.fly(i, f, vx, vy, g=g, spin=sp, drag=.6, a=P.gone(i, a0, a1), sx=s, sy=s)
            else:
                p[b] = dict(x=-.26, y=-.14, a=1)
        p["leaf_front"] = dict(r=40 * S((i - B) * .9))
        p["leaf_red"] = dict(r=-40 * S((i - B) * 1.1))
        return p
    c.run("pop", pose, out=True)
    fx, rng = c.fx, c.rng
    P.flash(fx["flash"], B, MOUTH, size=(.5, 2.4), life=4, spin=60)
    P.flash(fx["flash"], B + 1, (.6, .4), size=(.4, 1.6), life=4, rot=30, spin=-60)
    for j in range(12):                                        # leaves tumbling out after the fruit
        x0, z0, vx, ph = rng.uniform(-2.5, 1.5), rng.uniform(-2, 1), rng.uniform(-13, 9), rng.uniform(0, 6)
        fx["leaf"].emit(B + j % 4, 22 + j % 3, lambda t, x0=x0, z0=z0, vx=vx, ph=ph: (
            x0 + vx * (1 - math.exp(-2.5 * t)) + .5 * S(7 * t + ph), z0 + 7 * (1 - math.exp(-4 * t)) - 6 * t * t),
            rng, spin=rng.choice((-1, 1)) * 300, grow=lambda t, ph=ph: (.8 * abs(P.C(5 * t + ph)) + .2, .8),
            fade=P.tail(.6))
    P.burst(fx["berry"], rng, B, 12, at=MOUTH, speed=(20, 34), ang=(40, 250), g=40, life=(11, 14),
            grow=(1.0, .9), spin=300, spread=.8, even=True, drag=2.2)
    P.burst(fx["wicker"], rng, B, 14, at=(.6, 0.0), speed=(16, 30), ang=(0, 360), g=30, life=(10, 14),
            grow=(1.1, .7), spin=800, spread=1.4, even=True, drag=2.6, stagger=.25)
    c.glow_out(lambda i: .25 + .7 * P.strain(i) if i < B else 1.0 if i == B else 0.0,
               lambda i: 1 + .12 * P.strain(i) if i < B else 1.2)
