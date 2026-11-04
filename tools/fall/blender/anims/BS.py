"""BS Golden Wishbone: two prongs on the fork (top), the bow on the stem, its two ribbon tails (tools/fall/parts/BS.py).
idle   the ribbon tails flutter out of step, the prongs ease apart and back once, the bow breathes, and the stars on it
       twinkle one after another
land   it thuds down: squashes, both prongs splay on the impact and spring back, the bow bounces on the knot and the
       tails droop and flick up
hit    the wish: a pinch, then the prongs are hauled apart as if two people pull it, trembling, the fork straining
       taller and the tails streaming; it SNAPS back with a ring of sparkles from the joint, the tails whipping
multi  it charges with golden light: trembling harder, the prongs creeping wide, the bow swelling and the tails lifting,
       stars glinting on it - then it bursts: prongs flung wide, a starburst of sparkles and rays, and it settles"""
import json, math, os

FX = ["sparkle", "glint"]
S, C = math.sin, math.cos
TAU = 2 * math.pi
STARS = [(-1.50, 1.35, "prong_l"), (1.05, 2.85, "bow"), (-3.35, -1.50, "prong_l"), (1.68, -1.30, "prong_r"),
         (2.75, -1.90, "prong_r")]                              # the drawing's own stars (units) and what they are on
JOINT = (.12, 1.0)


def soft(v, lo):
    """v, but an inward swing (below 0) is eased off to at most lo degrees (a prong never closes far past rest)"""
    return v if v >= 0 else lo * math.tanh(v / lo)


def spread(a_l, a_r=None):
    """the prongs apart by a degrees (left one turns clockwise, right one counter-clockwise)"""
    return dict(prong_l=dict(r=-a_l), prong_r=dict(r=a_l if a_r is None else a_r))


# ---- where a point on a part is on a frame (the rig's own sums), so an effect can ride the part it is on
def _rig(c):
    if not hasattr(c, "_bs_rig"):
        import symanim as SA
        sp = json.load(open(os.path.join(SA.ROOT, "art", "blender", "parts", c.sid, "parts.json")))
        piv = {L["name"]: ((L["pivot"][0] - 500) / 100, (500 - L["pivot"][1]) / 100) for L in sp["layers"]}
        par = {L["name"]: L["parent"] for L in sp["layers"]}
        piv["root"], par["root"] = (0.0, -SA.HALF), None
        c._bs_rig = (piv, par, SA)
    return c._bs_rig


def _local(h, ch):
    r = math.radians(ch.get("r", 0.0))
    sx, sy = ch.get("sx", 1.0), ch.get("sy", 1.0)
    a, b, d, e = math.cos(r) * sx, -math.sin(r) * sy, math.sin(r) * sx, math.cos(r) * sy
    return (a, b, h[0] + ch.get("x", 0.0) - a * h[0] - b * h[1], d, e, h[1] + ch.get("y", 0.0) - d * h[0] - e * h[1])


def _mul(M, N):
    a, b, c_, d, e, f = M
    A, B, C_, D, E, F = N
    return (a * A + b * D, a * B + b * E, a * C_ + b * F + c_, d * A + e * D, d * B + e * E, d * C_ + e * F + f)


def follow(c, pose, clip, bone, pt):
    """frame (absolute) -> where pt (units, at rest) on bone is, posed"""
    piv, par, SA = _rig(c)
    f0, n = SA.START[clip], SA.CLIPS[clip]

    def at(f):
        i = int(round(f - f0))
        p = pose(i, n) if 0 < i < n else {}
        M, b = (1, 0, 0, 0, 1, 0), bone
        while b is not None:                                    # the part's own turn, then each holder's in turn
            ch = dict(p.get(b, {}))
            if b == "root" and ch.get("r"):
                SA.about_centre(ch)
            M = _mul(_local(piv[b], ch), M)
            b = None if b == "root" else par[b]
        x, y = pt
        return M[0] * x + M[1] * y + M[2], M[3] * x + M[4] * y + M[5]
    return at


def twinkle(c, kind, f, at, size=(.1, .8), n=10, spin=90, pose=None, clip=None):
    """a star flashing up and fading at at=(x, z[, bone]): riding that bone through pose when given"""
    x, z = at[0], at[1]
    if pose and len(at) > 2:
        w = follow(c, pose, clip, at[2], (x, z))
        path = lambda t: w(f + t * n)
    else:
        path = lambda t: (x, z)
    c.pools[kind].particle(f, f + n, path, c.rng, spin=spin, grow=size, fade=(1, 0))


def idle(c):
    def pose(i, n):
        t = i / n
        flex = 2.4 * (1 - C(TAU * t)) / 2                       # apart once and back, a slow breath
        p = spread(flex)
        p["prong_l"]["r"] += .6 * S(TAU * 3 * t)
        p["prong_r"]["r"] -= .6 * S(TAU * 3 * t)
        p.update(tail_l=dict(r=3.0 * S(TAU * 2 * t) + 1.2 * S(TAU * 5 * t), sx=1 + .02 * S(TAU * 4 * t)),
                 tail_r=dict(r=-2.6 * S(TAU * 3 * t) - 1.0 * S(TAU * 4 * t), sx=1 + .02 * S(TAU * 5 * t)),
                 bow=dict(sx=1 + .02 * S(TAU * 2 * t), sy=1 - .015 * S(TAU * 2 * t), r=.8 * S(TAU * t)),
                 top=dict(sy=1 + .008 * S(TAU * 2 * t)))
        return p
    c.run("idle", pose)
    f0 = 1
    for k, f in enumerate((4, 16, 28, 40, 52)):                 # each star twinkles in turn
        twinkle(c, "glint", f0 + f, STARS[k], size=(.15, .75), n=12, pose=pose, clip="idle")
    twinkle(c, "sparkle", f0 + 60, (.2, .3), size=(.1, .5), n=8)
    c.glow_curve("idle", lambda u: .12 * S(TAU * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        env = 1 - c.ease_in_out(max(0, (i / n - .8) / .2))
        k = c.damp(t, 3.2, .3)
        lag = c.damp(max(0, t - .03), 2.5, .35)
        lag2 = c.damp(max(0, t - .07), 2.2, .3)
        a = soft(11 * lag, 2.5) * env
        p = spread(a)
        p.update(root=dict(sx=1 + .12 * k * env, sy=1 - .14 * k * env),
                 top=dict(sy=1 - .04 * lag * env),
                 bow=dict(y=-.07 * lag2 * env, sx=1 + .09 * lag2 * env, sy=1 - .11 * lag2 * env),
                 tail_l=dict(r=9 * lag2 * env), tail_r=dict(r=-9 * lag2 * env))
        return p
    c.run("land", pose)
    twinkle(c, "glint", 101 + 6, STARS[1], size=(.1, .7), n=10, pose=pose, clip="land")
    twinkle(c, "glint", 101 + 9, STARS[4], size=(.1, .6), n=10, pose=pose, clip="land")
    c.glow_curve("land", lambda u: -.29 * max(0, 1 - u / .3) + .2 * max(0, S(math.pi * min(1, max(0, u - .2) / .5))))   # the halo does not squash: out while it does


SNAP = 26                                                       # the hit's frame the wish breaks


def hit(c):
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .82) / .18))
        if i <= 6:                                              # a pinch: it gathers itself
            a = c.ease_in_out(i / 6)
            p = spread(-2.5 * a, -1.2 * a)
            p.update(root=dict(sx=1 + .03 * a, sy=1 - .05 * a), tail_l=dict(r=3 * a), tail_r=dict(r=-3 * a))
            return p
        q = min(1, (i - 6) / (SNAP - 6))
        pull = c.ease_in_out(q) ** 1.2
        tr = (.4 + 1.6 * pull) * min(1, q * 4)
        wob_l, wob_r = tr * S(i * 2.9), tr * S(i * 3.4 + 1)     # the trembling of the strain
        if i <= SNAP:                                           # hauled apart, trembling, the fork straining
            fl = S(math.pi * q)
            p = spread(-2.5 + 20.5 * pull + wob_l, -1.2 + 19.2 * pull + wob_r)
            p.update(root=dict(sx=1 + .03 * (1 - pull) - .02 * pull, sy=1 - .05 * (1 - pull) + .04 * pull,
                               y=.08 * pull, r=1.6 * S(i * .9) * fl),
                     top=dict(sy=1 + .08 * pull, sx=1 - .03 * pull, r=.8 * S(i * 2.3) * fl),
                     bow=dict(sy=1 + .05 * pull, sx=1 - .03 * pull, r=1.5 * S(i * 1.7) * fl),
                     tail_l=dict(r=3 * (1 - pull) - 9 * pull + 5 * S(i * 1.3) * fl),
                     tail_r=dict(r=-3 * (1 - pull) + 9 * pull - 5 * S(i * 1.5) * fl))
            return p
        t = (i - SNAP) / 30                                     # SNAP: it springs home
        k = c.damp(t, 3.4, .3)
        kt = c.damp(t, 3.0, .35)
        whip = S(TAU * 2.2 * t) * math.exp(-3.2 * t)
        fade = math.exp(-14 * t)
        p = spread((soft(18 * k, 3.0) + wob_l * fade) * env, (soft(18 * k, 2.0) + wob_r * fade) * env)
        p.update(root=dict(sx=1 - .02 * kt * env, sy=1 + .04 * kt * env, y=.08 * kt * env),
                 top=dict(sy=1 + .08 * kt * env, sx=1 - .03 * kt * env),
                 bow=dict(sy=1 + .05 * kt * env, sx=1 - .03 * kt * env, y=.05 * whip * env),
                 tail_l=dict(r=(-9 * kt - 16 * whip) * env), tail_r=dict(r=(9 * kt + 16 * whip) * env))
        return p
    c.run("hit", pose)
    f0 = 201
    for j, f in enumerate((10, 14, 18, 21)):                    # strain glints along the prongs
        twinkle(c, "glint", f0 + f, STARS[(2, 3, 0, 4)[j]], size=(.1, .7), n=8, pose=pose, clip="hit")
    fs = f0 + SNAP
    jx, jz = JOINT
    for j in range(10):                                         # the wish breaks: a ring of sparkles from the joint
        a = TAU * j / 10 + .3
        r1 = c.rng.uniform(3.6, 4.6)
        c.pools["sparkle"].particle(fs, fs + 14 + j % 3, lambda t, a=a, r1=r1: (
            jx + math.cos(a) * (.9 + r1 * c.ease_out(t)), jz + math.sin(a) * (.9 + r1 * c.ease_out(t)) * .9),
            c.rng, spin=200, grow=(.9, .1))
    c.pools["ring"].particle(fs, fs + 12, lambda t: (0, 0), c.rng, grow=(.75, 1.2), fade=(.9, 0))
    def hit_glow(u):
        i = u * 46
        if i < SNAP:                                            # out while the prongs are hauled off the halo
            return -.29 * c.ease_in_out(min(1, i / 10))
        k = (i - SNAP) / 18
        return max(0, 1 - k) ** 1.5                            # a flash as it snaps, back to the resting halo
    c.glow_curve("hit", hit_glow)


CHARGE = 24                                                     # the multi's frame it bursts


def multi(c):
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        k = (min(i, CHARGE) / CHARGE) ** 1.4
        qv = lambda w, ph=0: S(i * w + ph) * k                  # the tremble, at full strength when it bursts
        if i <= CHARGE:                                         # charging: trembling, swelling, creeping wide
            e = c.ease_in_out(i / CHARGE)
            p = spread(10 * e + 1.5 * qv(3.1), 10 * e + 1.5 * qv(3.6, 1))
            p.update(root=dict(x=.05 * qv(2.7), sx=1 + .04 * k, sy=1 + .04 * k),
                     top=dict(r=1.2 * qv(2.3), sy=1 + .03 * k),
                     bow=dict(sx=1 + .07 * k, sy=1 + .07 * k, r=2 * qv(3.3)),
                     tail_l=dict(r=-10 * e + 3 * qv(2.1)), tail_r=dict(r=10 * e - 3 * qv(2.4)))
            return p
        t = (i - CHARGE) / 30                                   # the burst
        K = c.damp(t, 2.6, .32)
        f = math.exp(-14 * t)
        pulse = S(math.pi * min(1, t / .25)) if t < .25 else 0
        p = spread((soft((10 + 9 * min(1, t / .1)) * K, 2.5) + 1.5 * qv(3.1) * f) * env,
                   (soft((10 + 9 * min(1, t / .1)) * K, 2.5) + 1.5 * qv(3.6, 1) * f) * env)
        p.update(root=dict(x=.05 * qv(2.7) * f, sx=1 + (.04 * K + .03 * pulse) * env,
                           sy=1 + (.04 * K + .08 * pulse) * env),
                 top=dict(r=1.2 * qv(2.3) * f, sy=1 + (.03 * K + .04 * pulse) * env),
                 bow=dict(sx=1 + (.07 + .06 * pulse) * K * env, sy=1 + (.07 + .06 * pulse) * K * env,
                          y=.06 * pulse * env, r=2 * qv(3.3) * f),
                 tail_l=dict(r=((-10 - 8 * pulse) * c.damp(t, 1.8, .25) + 3 * qv(2.1) * f) * env),
                 tail_r=dict(r=((10 + 8 * pulse) * c.damp(t, 1.9, .25) - 3 * qv(2.4) * f) * env))
        return p
    c.run("multi", pose)
    f0 = 301
    for j, f in enumerate((6, 10, 13, 16, 19, 21)):             # glints crackling over it as it charges
        twinkle(c, "glint", f0 + f, STARS[j % 5], size=(.1, .55 + .05 * j), n=6, pose=pose, clip="multi")
    fs = f0 + CHARGE
    c.pools["rays"].particle(fs, fs + 16, lambda t: (0, .3), c.rng, spin=40, grow=(.55, 1.1), fade=(1, 0))
    c.pools["ring"].particle(fs, fs + 12, lambda t: (0, 0), c.rng, grow=(.75, 1.2), fade=(1, 0))
    for j in range(12):                                         # the starburst
        a = TAU * j / 12 + .15
        r1 = 3.3 + .9 * (j % 2)
        c.pools["sparkle"].particle(fs, fs + 13 + j % 4, lambda t, a=a, r1=r1: (
            math.cos(a) * (1.5 + r1 * c.ease_out(t)), .3 + math.sin(a) * (1.5 + r1 * c.ease_out(t))),
            c.rng, spin=220, grow=(1.0, .1))
    c.glow_curve("multi", lambda u: (u * 42 / CHARGE) ** 1.5 if u * 42 < CHARGE else
                 max(0, 1 - (u * 42 - CHARGE) / 14))
