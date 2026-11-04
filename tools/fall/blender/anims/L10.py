"""L10 Hay Bale: the bale block, eight tufts of loose straw round its edge (riding the block) and the two twine bands
(riding the plate, not the block - so when the block bulges it bulges round them) (tools/fall/parts/L10.py). A tuft
turns about its stretch of the bale's edge and splays out (scales up about it).
idle   a breeze runs round the bale: the tufts flutter one after another, the bale slowly breathes
land   it lands HEAVY: a deep crunchy squash that barely bounces, the tufts splay out and straw flies off the bottom
hit    it squats and bounces twice, bulging round the twine each time it lands, the tufts flicking out and straw flying
multi  it swells and strains against the twine, trembling, the tufts bristling - then bursts out and springs back, the
       tufts flung wide, straw everywhere, ring and sparks"""
import math

from . import lowkit as K

FX = ["straw", "sparkle"]
S = math.sin
TAU = 2 * math.pi
# each tuft's pivot (icon px, from the cut) and so which way it points; the order runs round the bale
TUFTS = {"tuft0": (878, 651), "tuft1": (649, 810), "tuft2": (433, 775), "tuft3": (179, 687), "tuft4": (100, 368),
         "tuft5": (354, 211), "tuft6": (570, 226), "tuft7": (860, 297)}


def u(p):
    return (p[0] - 500) / 100, (500 - p[1]) / 100


def out(name):
    """a tuft's outward direction (x, z), unit"""
    x, z = u(TUFTS[name])
    zc = .1
    d = math.hypot(x, z - zc)
    return x / d, (z - zc) / d


def tufts(f):
    """f(k, name) -> pose dict, for every tuft"""
    return {nm: f(k, nm) for k, nm in enumerate(TUFTS)}


def idle(c):
    K.track_glow(c)

    def pose(i, n):
        t = i / n
        b = S(TAU * t)
        p = dict(body=dict(sx=1 + .008 * b, sy=1 + .012 * b))
        # the breeze runs round the bale: each tuft flutters a step after the one before (whole cycles, 0 at the ends)
        p.update(tufts(lambda k, nm: dict(r=2.4 * (S(TAU * 2 * t - k * .8) + S(k * .8)) + .8 * S(TAU * 5 * t + 0),
                                          sx=1 + .02 * (S(TAU * 2 * t - k * .8 - 1) + S(k * .8 + 1)),
                                          sy=1 + .02 * (S(TAU * 2 * t - k * .8 - 1) + S(k * .8 + 1)))))
        return p
    c.run("idle", pose)
    c.glow_curve("idle", lambda u_: 0)


def splay(k_, amt, r_amt=0.0):
    return tufts(lambda k, nm: dict(sx=1 + amt * k_, sy=1 + amt * k_, r=r_amt * k_ * (1 if k % 2 else -1)))


def straw_burst(c, f, n, which=None, up=(1.0, 2.5), life=16):
    """straws shaken off the tufts (all of them, or `which`), flying outwards and falling"""
    names = which or list(TUFTS)
    for j in range(n):
        nm = names[j % len(names)]
        x0, z0 = u(TUFTS[nm])
        ox, oz = out(nm)
        v = c.rng.uniform(1.8, 3.2)
        vz = c.rng.uniform(*up)
        c.pools["straw"].particle(f + j % 3, f + j % 3 + life, lambda t, x0=x0, z0=z0, ox=ox, oz=oz, v=v, vz=vz: (
            x0 + ox * (.7 + v * t), z0 + oz * (.7 + v * t) + vz * t - 6 * t * t), c.rng,
            spin=c.rng.uniform(-400, 400), grow=(1.15, .95), fade=(1, .5))


def land(c):
    def pose(i, n):
        t = (i - 1) / 30
        uu = i / n
        env = 1 - c.ease_in_out(max(0, (uu - .65) / .35))
        k = c.damp(t, 2.0, .45) * env                          # heavy: deep, slow, hardly any bounce
        p = dict(root=dict(sx=1 + .13 * k, sy=1 - .16 * k), body=dict(sx=1 + .03 * k, sy=1 - .03 * k))
        sp = max(0, c.damp(max(0, t - .03), 2.6, .3)) * env
        p.update(splay(sp, .14, 6))
        p["twine_l"] = dict(sx=1 - .02 * k)
        p["twine_r"] = dict(sx=1 - .02 * k)
        return p
    c.run("land", pose)
    straw_burst(c, 101 + 1, 8, which=["tuft0", "tuft1", "tuft2", "tuft3"])
    c.glow_curve("land", lambda u_: 0)


def hit(c):
    def hop(i, i0, i1, h):
        if i0 <= i <= i1:
            return h * S(math.pi * (i - i0) / (i1 - i0))
        return 0.0

    def pose(i, n):
        uu = i / n
        env = 1 - c.ease_in_out(max(0, (uu - .8) / .2))
        if i <= 5:                                             # squat
            e = c.ease_in_out(i / 5)
            p = dict(root=dict(sx=1 + .1 * e, sy=1 - .13 * e))
            p.update(splay(e, .06))
            return p
        y = hop(i, 5, 17, .7) + hop(i, 22, 30, .3)
        k1 = c.damp((i - 17) / 30, 2.8, .3) * (1 - c.ease_in_out((i - 17) / 5)) if 17 <= i <= 22 else 0
        k2 = c.damp((i - 30) / 30, 2.4, .3) * env if i >= 30 else 0
        k = k1 + .6 * k2
        sq0 = max(0, 1 - (i - 5) / 3)                          # out of the squat
        air = (y > 0) * 1.0
        st = .08 * S(math.pi * min(1, (i - 5) / 8)) if 5 < i < 13 else 0   # stretched on take-off
        bul = max(0, k)                                         # bulges round the twine on landing
        p = dict(root=dict(y=y, sx=1 + .1 * sq0 - st + .1 * k, sy=1 - .13 * sq0 + st * 1.4 - .12 * k),
                 body=dict(sx=1 + .05 * bul, sy=1 + .02 * bul))
        flick = (S((i - 5) * .9) * (.6 + .4 * air) * env) if i > 5 else 0
        p.update(tufts(lambda kk, nm: dict(r=6 * flick * (1 if kk % 2 else -1),
                                            sx=1 + .1 * air + .14 * bul, sy=1 + .1 * air + .14 * bul)))
        p["twine_l"] = dict(sx=1 - .02 * bul, sy=1 + .01 * bul)
        p["twine_r"] = dict(sx=1 - .02 * bul, sy=1 + .01 * bul)
        return p
    c.run("hit", pose)
    f0 = 201
    straw_burst(c, f0 + 6, 6, which=["tuft0", "tuft1", "tuft2", "tuft3"], up=(2, 3.5))
    straw_burst(c, f0 + 17, 8)
    straw_burst(c, f0 + 30, 5, which=["tuft0", "tuft1", "tuft2", "tuft3", "tuft4"], life=12)
    for j in range(6):
        a = TAU * j / 6 + .4
        c.pools["sparkle"].particle(f0 + 17, f0 + 29, lambda t, a=a: (math.cos(a) * (3.6 + 1.2 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.2 * c.ease_out(t))), c.rng, spin=160, grow=(.8, .05))
    c.glow_curve("hit", lambda u_: math.sin(math.pi * min(1, u_ / .9)) if u_ < .9 else 0)


def multi(c):
    R = 20

    def pose(i, n):
        uu = i / n
        if i < R:                                              # swelling against the twine, trembling, bristling
            k = (i / R) ** 1.3
            q = S(i * 3.1) * k
            p = dict(body=dict(sx=1 + .08 * k + .01 * q, sy=1 + .06 * k - .01 * q, x=.015 * q),
                     twine_l=dict(sx=1 + .012 * S(i * 4.1) * k), twine_r=dict(sx=1 + .012 * S(i * 4.4) * k))
            p.update(tufts(lambda kk, nm: dict(r=3 * S(i * 3.5 + kk) * k, sx=1 + .08 * k, sy=1 + .08 * k)))
            return p
        t = (i - R) / 30
        env = 1 - c.ease_in_out(max(0, (uu - .72) / .28))
        burst = c.ease_out(min(1, t / .1))
        k = c.damp(t, 2.6, .3) * env
        sw = (1 - burst) * .08 + .06 * k * burst               # the swell lets go and springs
        p = dict(body=dict(sx=1 + sw, sy=1 + sw * .75), root=dict(sy=1 + .05 * k * burst, sx=1 - .03 * k * burst),
                 twine_l=dict(sx=1 - .015 * k), twine_r=dict(sx=1 - .015 * k))
        fl = (.08 * (1 - burst) + .22 * burst * max(0, 1 - t / .5) + .05 * k * burst) * env
        p.update(tufts(lambda kk, nm: dict(sx=1 + fl, sy=1 + fl, r=6 * k * burst * (1 if kk % 2 else -1))))
        return p
    c.run("multi", pose)
    f0 = 301 + R
    c.pools["ring"].particle(f0, f0 + 12, lambda t: (0, 0), c.rng, grow=(.55, 1.18), fade=(1, 0))
    straw_burst(c, f0, 12, up=(.5, 2.0), life=14)               # straw flung out all round
    for j in range(8):
        a = TAU * j / 8 + .3
        c.pools["sparkle"].particle(f0, f0 + 12, lambda t, a=a: (math.cos(a) * (3.6 + 1.5 * c.ease_out(t)),
                                    math.sin(a) * (3.6 + 1.5 * c.ease_out(t))), c.rng, spin=180, grow=(.8, .05))
    c.glow_curve("multi", lambda u_: min(1, u_ / .48) if u_ < .48 else max(0, 1 - (u_ - .48) / .4))
