"""ES The Crow: body, head (with its beak), two wings behind the body, two feet, four loose feathers, and the torso plate
behind it all that fills in where a wing or the head swings off (tools/fall/parts/ES.py).
idle   it hovers: the wings rise and fall in two slow beats, the body bobbing against them, the head snapping bird-like
       from one cocked tilt to the next, the loose feathers drifting
land   it drops on its talons: squashes, the wings flare up and settle, the head nods with the bump, the feathers hop
hit    it crouches, then beats its wings three times big, rising as it flaps; the head throws back cackling (a ha-ha-ha
       judder), the loose feathers are blown about and feathers fly off the wingtips
multi  it hunches, trembling harder, wings folding in, head down - then bursts open: wings flung up wide, head up, the
       feathers thrown out, rays, a ring and feathers flying"""
import json, math, os

FX = ["feather", "sparkle"]
S, C = math.sin, math.cos
TAU = 2 * math.pi
TIP_L, TIP_R = (-4.4, .9), (4.4, -.1)                           # the wingtips (units, at rest)
FEATHERS = {"f_ul": (-2.1, 2.85), "f_ur": (3.15, 2.35), "f_ll": (-3.0, -2.0), "f_lr": (3.25, -2.7)}


def st(i, a, b):
    """0 before frame a, 1 after frame b, a smooth step between"""
    u = min(1.0, max(0.0, (i - a) / (b - a)))
    return u * u * (3 - 2 * u)


def blown(k, spin, wob=0.0):
    """the loose feathers pushed out from the middle by k (units), turning by spin degrees"""
    out = {}
    for j, (b, (x, y)) in enumerate(FEATHERS.items()):
        d = math.hypot(x, y)
        sg = 1 if j % 2 else -1
        out[b] = dict(x=k * x / d, y=k * y / d, r=sg * spin + wob * S(j * 1.7 + 1))
    return out


# ---- where a point on a part is on a frame (the rig's own sums), so an effect can start from the part it is on
def _rig(c):
    if not hasattr(c, "_es_rig"):
        import symanim as SA
        sp = json.load(open(os.path.join(SA.ROOT, "art", "blender", "parts", c.sid, "parts.json")))
        piv = {L["name"]: ((L["pivot"][0] - 500) / 100, (500 - L["pivot"][1]) / 100) for L in sp["layers"]}
        par = {L["name"]: L["parent"] for L in sp["layers"]}
        piv["root"], par["root"] = (0.0, -SA.HALF), None
        c._es_rig = (piv, par, SA)
    return c._es_rig


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


def fly(c, f, at, vel, n=18, grav=2.2, spin=300, size=(.75, .55)):
    """a feather flicked off from at with velocity vel (units per particle life), drifting down as it goes"""
    x0, z0 = at
    vx, vz = vel
    c.pools["feather"].particle(f, f + n, lambda t: (x0 + vx * t, z0 + vz * t - grav * t * t), c.rng, spin=spin,
                                grow=size, fade=(1, 0))


def idle(c):
    def pose(i, n):
        t = i / n
        fl = S(TAU * 2 * t)                                     # two slow wingbeats a loop
        tilt = 6 * st(i, 12, 16) - 10 * st(i, 40, 44) + 4 * st(i, 62, 67)   # snaps from one cocked tilt to the next
        return dict(wing_l=dict(r=-6 * fl + 1.5 * S(TAU * 4 * t)), wing_r=dict(r=6 * fl - 1.5 * S(TAU * 4 * t)),
                    body=dict(y=.035 * fl, sy=1 + .008 * S(TAU * 4 * t)),
                    head=dict(r=tilt + .8 * S(TAU * 2 * t), y=.015 * S(TAU * 4 * t)),
                    f_ul=dict(y=.06 * S(TAU * t), r=8 * S(TAU * 2 * t)),
                    f_ur=dict(y=-.05 * S(TAU * t), x=.03 * S(TAU * 2 * t), r=-7 * S(TAU * t)),
                    f_ll=dict(y=.05 * S(TAU * 2 * t), r=6 * S(TAU * t)),
                    f_lr=dict(y=-.06 * S(TAU * t), x=-.03 * S(TAU * 2 * t), r=-8 * S(TAU * 2 * t)))
    c.run("idle", pose)
    c.glow_curve("idle", lambda u: .12 * S(TAU * 2 * u) ** 2)


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        env = 1 - c.ease_in_out(max(0, (i / n - .8) / .2))
        k = c.damp(t, 3.2, .3)
        lag = c.damp(max(0, t - .03), 2.4, .32)
        lag2 = c.damp(max(0, t - .06), 2.2, .3)
        hop = lambda d: .16 * max(0, S(math.pi * min(1, max(0, t - d) / .25)))
        p = dict(root=dict(sx=1 + .1 * k * env, sy=1 - .12 * k * env),
                 wing_l=dict(r=-16 * lag * env), wing_r=dict(r=16 * lag * env),
                 body=dict(y=-.04 * lag * env), head=dict(r=-6 * lag2 * env, y=-.04 * lag2 * env))
        for j, b in enumerate(FEATHERS):
            p[b] = dict(y=hop(.03 + .03 * j) * env, r=(-1) ** j * 10 * S(t * 25) * math.exp(-t * 5) * env)
        return p
    c.run("land", pose)
    c.glow_curve("land", lambda u: -.29 * max(0, 1 - u / .3))   # the halo does not squash: out while it does


def hit(c):
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .85) / .15))
        a = st(i, 0, 5) * (1 - st(i, 5, 10))                    # the crouch before it takes off
        q = max(0, (i - 5) / 35)
        amp = 22 * min(1, q * 5) * min(1, max(0, 1 - q) * 4)
        ph = TAU * 3 * q                                        # three big beats
        cock = 6 * st(i, 0, 5) * (1 - st(i, 5, 9))
        lift = .16 * st(i, 6, 14) * (1 - st(i, 32, 41)) + .05 * (amp / 22) * max(0, -S(ph))
        back = st(i, 10, 15) * (1 - st(i, 34, 42))              # the head thrown back, cackling
        blow = st(i, 8, 16) * (1 - st(i, 30, 43))
        land = st(i, 38, 41) * (1 - st(i, 41, 46))
        p = dict(root=dict(sx=1 + .04 * a + .05 * land, sy=1 - .06 * a - .07 * land, y=lift),
                 wing_l=dict(r=(cock - amp * C(ph)) * env, sx=1 - .05 * (amp / 22) * S(ph)),
                 wing_r=dict(r=(-cock + amp * C(ph)) * env, sx=1 - .05 * (amp / 22) * S(ph)),
                 body=dict(sy=1 + .03 * abs(S(i * 1.2)) * back),
                 head=dict(r=(-4 * a + 20 * back + 4.5 * S(i * 2.4) * back) * env,
                           y=.06 * abs(S(i * 1.2)) * back))
        p.update(blown(.28 * blow, 28 * blow * S(i * .7), 10 * blow * S(i * 1.9)))
        return p
    c.run("hit", pose)
    f0 = 201
    tl, tr = follow(c, pose, "hit", "wing_l", TIP_L), follow(c, pose, "hit", "wing_r", TIP_R)
    for j, f in enumerate((9, 11, 19, 21, 27, 29)):           # flicked off the wingtips on the downstrokes
        x, z = (tl if j % 2 == 0 else tr)(f0 + f)
        sg = -1 if j % 2 == 0 else 1
        fly(c, f0 + f, (x * .92, z), (sg * c.rng.uniform(1.0, 1.8), c.rng.uniform(.6, 1.6)), n=14 + j % 3)
    for j in range(5):                                          # cackle sparks off the beak
        a = .3 + j * .5
        c.pools["sparkle"].particle(f0 + 14 + 4 * j, f0 + 24 + 4 * j, lambda t, a=a: (
            1.3 + math.cos(a) * (1.2 + 1.4 * t), 1.6 + math.sin(a) * (1.2 + 1.4 * t)), c.rng, spin=150, grow=(.6, .1))
    c.glow_curve("hit", lambda u: .55 * S(math.pi * min(1, u / .9)) if u < .9 else 0)


H = 22                                                          # the multi's frame it bursts open


def multi(c):
    def pose(i, n):
        u = i / n
        env = 1 - c.ease_in_out(max(0, (u - .8) / .2))
        k = (min(i, H) / H) ** 1.3
        e = c.ease_in_out(min(i, H) / H)
        tq = lambda w, ph=0: S(i * w + ph) * k                  # the tremble, strongest as it bursts
        if i <= H:                                              # hunching, wings folding in, trembling
            p = dict(root=dict(x=.04 * tq(2.9), sx=1 + .05 * e, sy=1 - .07 * e),
                     body=dict(sy=1 - .03 * e),
                     head=dict(y=-.12 * e, r=-7 * e + 2 * tq(3.3)),
                     wing_l=dict(r=22 * e + 3 * tq(3.1), sx=1 - .12 * e),
                     wing_r=dict(r=-22 * e - 3 * tq(3.4), sx=1 - .12 * e))
            p.update(blown(-.12 * e, 6 * tq(3.7)))
            return p
        t = (i - H) / 30                                        # BURST
        o = st(i, H, H + 4)
        D = c.damp(max(0, t - .13), 1.9, .35)
        f = math.exp(-14 * t)
        wide = -26 * D
        sx_w = 1 + (-.12 * (1 - o) + .05 * o * D) * env
        p = dict(root=dict(x=.04 * tq(2.9) * f, sx=1 + (.05 * (1 - o) - .03 * o * D) * env,
                           sy=1 + (-.07 * (1 - o) + .08 * o * D) * env),
                 body=dict(sy=1 - .03 * (1 - o)),
                 head=dict(y=(-.12 * (1 - o) + .05 * o * D) * env,
                           r=(-7 * (1 - o) + 10 * o * D + 2 * tq(3.3) * f) * env),
                 wing_l=dict(r=(22 * (1 - o) + o * wide + 3 * tq(3.1) * f) * env, sx=sx_w),
                 wing_r=dict(r=(-22 * (1 - o) - o * wide - 3 * tq(3.4) * f) * env, sx=sx_w))
        p.update(blown((-.12 * (1 - o) + .4 * o * D) * env, (6 * tq(3.7) * f + 35 * o * D) * env))
        return p
    c.run("multi", pose)
    f0 = 301
    fs = f0 + H + 1
    c.pools["rays"].particle(fs, fs + 16, lambda t: (0, .2), c.rng, spin=-40, grow=(.6, 1.1), fade=(1, 0))
    c.pools["ring"].particle(fs, fs + 12, lambda t: (0, 0), c.rng, grow=(.75, 1.2), fade=(1, 0))
    for j in range(8):                                          # feathers thrown out all round
        a = TAU * j / 8 + .4
        fly(c, fs + j % 3, (math.cos(a) * 2.2, math.sin(a) * 2.2), (math.cos(a) * 2.6, math.sin(a) * 2.6 + .6),
            n=14, grav=1.6, size=(.85, .6))
    for j in range(6):
        a = TAU * j / 6 + .1
        c.pools["sparkle"].particle(fs, fs + 12, lambda t, a=a: (math.cos(a) * (2.0 + 3.0 * c.ease_out(t)),
                                    .2 + math.sin(a) * (2.0 + 3.0 * c.ease_out(t))), c.rng, spin=200, grow=(.8, .1))
    c.glow_curve("multi", lambda u: (u * 42 / H) ** 1.5 if u * 42 < H else max(0, 1 - (u * 42 - H) / 14))
