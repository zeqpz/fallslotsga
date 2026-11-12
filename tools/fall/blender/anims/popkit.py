"""Small helpers the "pop" clips share (the icons' break-aparts; partsanim.py Ctx.run(out=True), symanim.py POP_BLOW).

The clip's beats, for every icon (30 fps): frames 0-7 the strain (swell, tremble, parts start to part, the glow heats),
frame 8 THE BLOW (the game's sound and cell timing sit on it), 8-24 the parts fly, fall and dissolve, 25 empty.
What flies, how, and which effects is each icon's own (anims/<ID>.py pop). Units: 1 = 100 icon px; speeds are units
a second, gravity units a second squared; frames are clip frames."""
import math

BLOW = 8
HALF = 4.7
S, C = math.sin, math.cos
TAU = 2 * math.pi


def st(i, a, b):
    """0 before frame a, 1 after frame b, a smooth step between"""
    u = min(1.0, max(0.0, (i - a) / (b - a)))
    return u * u * (3 - 2 * u)


def lin(i, a, b):
    return min(1.0, max(0.0, (i - a) / (b - a)))


def strain(i, p=1.7, blow=BLOW):
    """the build-up: 0 at frame 0, 1 on the frame before the blow, slow then fast"""
    return min(1.0, i / (blow - 1)) ** p


def gone(i, a, b):
    """an alpha: 1 until frame a, 0 from frame b"""
    return 1.0 - lin(i, a, b)


def swell(s, sy=None, x=0.0, y=0.0, r=0.0):
    """the root scaled about the icon's MIDDLE (the root bone sits at its foot)"""
    sy = s if sy is None else sy
    d = dict(sx=s, sy=sy, x=x, y=y - HALF * (sy - 1))
    if r:
        d["r"] = r
    return d


def fly(i, i0, vx, vy, g=24.0, spin=0.0, drag=0.0, at=(0.0, 0.0), r0=0.0, **more):
    """a thrown part: its pose from frame i0 on - speed (vx, vy), gravity g, air drag (1/s), spin (deg/s, ccw)"""
    t = max(0.0, i - i0) / 30
    k = (1 - math.exp(-drag * t)) / drag if drag else t
    return dict(x=at[0] + vx * k, y=at[1] + vy * k - .5 * g * t * t, r=r0 + spin * t, **more)


def free(c, child, parent_pose, want):
    """The local pose that puts `child` (which rides `parent`) where `want` says - a pose in the picture's own
    axes, as if its parent were at rest - whatever the parent is doing (parent_pose): a part thrown clear of a body
    that is squashing must not be squashed and dragged with it."""
    par = c.parent[child]
    px, py = c.pivot[par]
    cx, cy = c.pivot[child]
    dx, dy = cx - px, cy - py
    r = math.radians(parent_pose.get("r", 0.0))
    sx, sy = parent_pose.get("sx", 1.0), parent_pose.get("sy", 1.0)
    wx = dx + want.get("x", 0.0) - parent_pose.get("x", 0.0)
    wy = dy + want.get("y", 0.0) - parent_pose.get("y", 0.0)
    lx, ly = (wx * C(r) + wy * S(r)) / sx, (-wx * S(r) + wy * C(r)) / sy
    out = dict(x=lx - dx, y=ly - dy, r=want.get("r", 0.0) - parent_pose.get("r", 0.0),
               sx=want.get("sx", 1.0) / sx, sy=want.get("sy", 1.0) / sy)
    if "a" in want:
        out["a"] = want["a"]
    return out


def tail(a=.6):
    """a particle's alpha over its life: full, then fading out over the last (1 - a) of it"""
    return lambda t: 1.0 if t < a else max(0.0, 1 - (t - a) / (1 - a))


def arc(x0, z0, vx, vz, g, life, drag=0.0):
    """a particle's path: thrown from (x0, z0) at (vx, vz), gravity g, over `life` frames"""
    T = life / 30

    def path(t):
        s = t * T
        k = (1 - math.exp(-drag * s)) / drag if drag else s
        return x0 + vx * k, z0 + vz * k - .5 * g * s * s
    return path


def burst(fx, rng, i0, n, at=(0.0, 0.0), speed=(6, 12), ang=(0, 360), g=22.0, life=(9, 14), grow=(.8, .55),
          spin=400, stagger=0.0, aim=None, drag=1.2, spread=0.0, fade=None, even=False):
    """n sprites thrown from `at` (+- spread) on frame i0 (each `stagger` frames after the last): speeds and
    directions (degrees ccw from +x) drawn from the ranges; even=True spaces the directions evenly"""
    for j in range(n):
        a = math.radians(ang[0] + (ang[1] - ang[0]) * ((j + rng.random() * .6) / n if even else rng.random()))
        v = rng.uniform(*speed)
        L = rng.randint(*life)
        x0, z0 = at[0] + rng.uniform(-spread, spread), at[1] + rng.uniform(-spread, spread)
        s = rng.uniform(.8, 1.15)
        f = int(round(i0 + j * stagger))
        fx.emit(f, f + L, arc(x0, z0, v * C(a), v * S(a), g, L, drag), rng, spin=rng.choice((-1, 1)) * spin * L / 30,
                grow=(grow[0] * s, grow[1] * s), fade=fade or tail(.55), aim=aim)


def flash(fx, i0, at=(0.0, 0.0), size=(.4, 2.2), life=5, rot=0.0, spin=0.0, rng=None):
    """a quick flare on the blow: it snaps big and is gone"""
    fx.emit(i0, i0 + life, lambda t: at, rng, rot=rot, spin=spin,
            grow=lambda t: size[0] + (size[1] - size[0]) * (1 - (1 - t) ** 3), fade=lambda t: 1 - t * t)


def unit(dx, dy):
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d
