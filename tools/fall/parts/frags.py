"""The extra pictures of the icons' part rigs (tools/fall/cut_frags.py): what each icon BREAKS into in its "pop" clip
(tools/fall/blender/anims/<ID>.py pop) and the small effect sprites that clip throws, painted here in the icon's own
colours. One function per icon, given a cut_frags.Cutter. Icon px (1000 x 1000, y down).
  .venv/Scripts/python.exe tools/fall/cut_frags.py <ID>   then READ art/blender/parts/<ID>/frags_check.jpg"""
import math

INK = (40, 22, 14, 255)


# ---------------------------------------------------------------- sprite painters: draw(d, S) on a PIL ImageDraw

def _poly(d, S, pts, fill, w=.07):
    P = [(x * S, y * S) for x, y in pts]
    d.polygon(P, fill=fill + (255,))
    d.line(P + P[:2], fill=INK, width=max(2, round(w * S)), joint="curve")


def teardrop(fill, hi=(255, 255, 255)):
    """a drop, its point up (it trails: XFX aim="tail")"""
    def draw(d, S):
        pts = [(.5, .06)]
        for k in range(0, 41):
            a = math.radians(-50 + 280 * k / 40)                 # round the bulb, from its right shoulder to its left
            pts.append((.5 + .29 * math.cos(a), .64 + .29 * math.sin(a)))
        _poly(d, S, pts, fill)
        d.ellipse([.36 * S, .52 * S, .46 * S, .66 * S], fill=hi + (230,))
    return draw


def blob(fill, seed=3, lumps=5, hi=None, r=.34):
    """a lumpy splat"""
    def draw(d, S):
        pts = []
        for k in range(72):
            a = math.tau * k / 72
            rr = r * (1 + .16 * math.sin(lumps * a + seed) + .07 * math.sin((lumps + 3) * a + 2 * seed))
            pts.append((.5 + rr * math.cos(a), .5 + rr * math.sin(a)))
        _poly(d, S, pts, fill)
        if hi:
            d.ellipse([.34 * S, .32 * S, .47 * S, .42 * S], fill=hi + (220,))
    return draw


def oval(fill, w=.2, h=.38, hi=None, point=0.0):
    """a seed / kernel / petal: an oval, `point` > 0 pinches its top"""
    def draw(d, S):
        pts = []
        for k in range(60):
            a = math.tau * k / 60
            x, y = math.cos(a), math.sin(a)
            pinch = 1 - point * max(0.0, -y) ** 1.5
            pts.append((.5 + w * x * pinch, .5 + h * y))
        _poly(d, S, pts, fill, w=.06)
        if hi:
            d.ellipse([(.5 - w * .55) * S, (.5 - h * .1) * S, (.5 - w * .1) * S, (.5 + h * .45) * S], fill=hi + (200,))
    return draw


def shard(fill, pts, hi=None, w=.07):
    """a broken chip: a polygon (0..1)"""
    def draw(d, S):
        _poly(d, S, pts, fill, w)
        if hi:
            cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
            q = [(cx + (x - cx) * .45 - .04, cy + (y - cy) * .45 - .04) for x, y in pts[:3]]
            d.polygon([(x * S, y * S) for x, y in q], fill=hi + (150,))
    return draw


def streak(fill=(255, 255, 255), a=215):
    """a wind line: long, thin, pointed both ends (lies along x)"""
    def draw(d, S):
        d.polygon([(.04 * S, .5 * S), (.5 * S, .455 * S), (.96 * S, .5 * S), (.5 * S, .545 * S)], fill=fill + (a,))
    return draw


CHIP = [(.2, .3), (.62, .16), (.84, .5), (.6, .84), (.24, .7)]
SLIVER = [(.16, .62), (.5, .14), (.84, .4), (.58, .86)]


# ---------------------------------------------------------------- the icons

def L3(c):
    """Green apple: sliced clean in two (a knife line from the dimple to the foot), each half with its cream flesh
    behind it; juice, seeds, apple-blossom petals."""
    src = c.comp("body", "skin")
    lab = c.polys([[(0, 0), (497, 0), (497, 330), (482, 480), (486, 640), (474, 800), (468, 1000), (0, 1000)]], rest=1)
    c.pieces(src, lab, ["half_l", "half_r"], parent="body", over_="skin")
    for h in ("half_l", "half_r"):
        c.face(h + "_in", h, (250, 244, 205), edge=8)
    c.sprite("juice", teardrop((196, 226, 96)))
    c.sprite("seed", oval((92, 52, 28), w=.17, h=.32, hi=(170, 110, 70), point=.5))
    c.sprite("petal", oval((255, 228, 232), w=.24, h=.36, hi=(255, 255, 255), point=.6))
    c.sprite("flesh", blob((250, 244, 205), seed=2, lumps=4, r=.3))


def _between(lines):
    """the strips between successive polylines (each top to bottom, left to right), out to the picture's sides"""
    edges = [[(0, 0), (0, 1000)]] + [[(l[0][0], 0)] + list(l) + [(l[-1][0], 1000)] for l in lines] + [[(1000, 0), (1000, 1000)]]
    return [edges[k] + edges[k + 1][::-1] for k in range(len(edges) - 1)]


def H7(c):
    """Pumpkin: split along its ribs into five wedges, each hinged at its foot (they fall open like a flower);
    seeds and stringy pulp."""
    src = c.comp("body", "body_rim", "top")
    ribs = [[(400, 330), (300, 372), (190, 470), (150, 600), (162, 740), (215, 850), (290, 925)],
            [(450, 340), (372, 400), (322, 520), (306, 650), (322, 790), (372, 890), (420, 940)],
            [(560, 345), (606, 420), (628, 540), (630, 660), (612, 800), (575, 900), (548, 945)],
            [(640, 340), (722, 400), (785, 510), (800, 640), (780, 780), (735, 870), (690, 925)]]
    lab = c.polys(_between(ribs))
    c.pieces(src, lab, "wedge{}", parent="body", over_="top", ink=5,
             pivots=[(215, 850), (345, 910), (480, 935), (640, 915), (770, 855)])
    c.sprite("seed", oval((250, 236, 196), w=.2, h=.36, hi=(255, 255, 255), point=.55))
    c.sprite("pulp", blob((255, 176, 58), seed=1, lumps=3, hi=(255, 226, 150), r=.3))
    c.sprite("string", shard((255, 190, 80), [(.1, .56), (.34, .38), (.62, .46), (.9, .34), (.66, .58), (.36, .56)], w=.05))


def H2(c):
    """Pumpkin pie: the pie cut into six more slices round the point of the one already cut, and the tin's bare
    floor under that one; cream, custard, crust crumbs."""
    src = c.comp("pie")
    lab = c.sectors((522, 492), 7, angles=[40, 95, 150, 205, 260, 305, 356])
    c.pieces(src, lab, ["s0", "s1", "s2", "s3", "s4", "s5", "floor"], parent="pie", over_="pie", ink=4)
    c.sprite("cream", blob((255, 248, 232), seed=4, lumps=4, hi=(255, 255, 255), r=.32))
    c.sprite("custard", teardrop((240, 138, 40), hi=(255, 214, 150)))
    c.sprite("crust", shard((236, 180, 84), CHIP, hi=(255, 222, 150)))


def H5(c):
    """Moonshine jug: the stoneware shatters into ten shards (the cork and the drip are their own parts)."""
    src = c.comp("jug", "jug_art")
    pts = [(470, 190), (330, 330), (560, 350), (760, 330), (230, 520), (450, 520), (690, 540), (290, 740), (520, 730),
           (720, 730), (500, 900)]
    lab = c.cells(pts, amp=16, seed=5, scale=90)
    c.pieces(src, lab, "shard{}", parent="jug", over_="jug_art", ink=5)
    c.sprite("chip", shard((150, 78, 40), CHIP, hi=(210, 130, 80)))
    c.sprite("chip2", shard((244, 226, 180), SLIVER, hi=(255, 250, 230)))


def L1(c):
    """Maple leaf: the whole leaf torn into ragged bits (the gust takes them one after another)."""
    src = c.comp()
    pts = [(505, 150), (440, 300), (560, 330), (200, 330), (330, 420), (790, 440), (650, 500), (480, 500), (200, 660),
           (350, 620), (700, 700), (540, 680), (420, 760), (310, 880)]
    lab = c.cells(pts, amp=22, seed=9, scale=70)
    c.pieces(src, lab, "bit{}", parent="root", ink=0)
    c.sprite("gust", streak())
    c.sprite("speck", shard((214, 66, 34), SLIVER, hi=(255, 150, 70)))


def L4(c):
    """Grapes: the bunch behind the six front grapes cut into its own lumps (stem, the back grapes) so those pop
    too; juice and skins."""
    src = c.comp("bunch")
    pts = [(540, 150), (480, 330), (700, 340), (370, 520), (560, 500), (780, 480), (430, 700), (640, 760), (740, 850)]
    lab = c.cells(pts, amp=8, seed=3)
    c.pieces(src, lab, "lump{}", parent="bunch", over_="bunch", ink=0)
    c.sprite("juice", teardrop((150, 70, 170), hi=(230, 190, 240)))
    c.sprite("splat", blob((126, 52, 150), seed=2, lumps=3, hi=(214, 160, 230), r=.3))
    c.sprite("skin", shard((92, 40, 112), SLIVER, hi=(170, 110, 190)))


def H4(c):
    """Pilgrim hat: the band without its buckle (the band's picture has the buckle painted on; the buckle pings off)."""
    import numpy as np
    from scipy import ndimage
    band, buckle = c.layer("band"), c.layer("buckle")
    hole = ndimage.binary_dilation(buckle[..., 3] > .05, iterations=6) & (band[..., 3] > .05)
    ys, xs = np.nonzero(hole)
    img = band.copy()
    good = (band[..., 3] > .9) & ~hole
    for x in range(xs.min(), xs.max() + 1):                      # each column of the gap: the band's own column
        col = hole[:, x]                                         # beside the buckle, slid along the band's slope
        if not col.any():
            continue
        for sx in (xs.min() - 14, xs.max() + 14):
            pass
        t = (x - xs.min()) / max(1, xs.max() - xs.min())
        xa, xb = xs.min() - 16, xs.max() + 16
        ya, yb = np.nonzero(good[:, xa])[0], np.nonzero(good[:, xb])[0]
        if len(ya) == 0 or len(yb) == 0:
            continue
        top = ya.min() * (1 - t) + yb.min() * t
        bot = ya.max() * (1 - t) + yb.max() * t
        for y in range(int(top), int(bot) + 1):
            v = (y - top) / max(1.0, bot - top)
            a = band[int(round(ya.min() + v * (ya.max() - ya.min()))), xa]
            b = band[int(round(yb.min() + v * (yb.max() - yb.min()))), xb]
            img[y, x] = a * (1 - t) + b * t
        img[:int(top), x, 3] = np.where(hole[:int(top), x], 0, img[:int(top), x, 3])
        img[int(bot) + 1:, x, 3] = np.where(hole[int(bot) + 1:, x], 0, img[int(bot) + 1:, x, 3])
    c.add("band_bare", img, parent="band", over_="band", pivot=(525, 640))
    c.sprite("dust", blob((70, 66, 74), seed=5, lumps=5, hi=(120, 116, 126), r=.32))


def H1(c):
    """Roast turkey: it comes apart at its own joints (drumsticks, wing, garnish); only sprites here."""
    c.sprite("berry", blob((196, 24, 44), seed=1, lumps=1, hi=(255, 170, 170), r=.34))
    c.sprite("skin", shard((214, 120, 40), CHIP, hi=(250, 180, 90)))


def H3(c):
    """Cornucopia: its fruit are parts already; only sprites here."""
    c.sprite("berry", blob((110, 50, 140), seed=1, lumps=1, hi=(200, 150, 220), r=.34))
    c.sprite("wicker", shard((196, 136, 60), [(.1, .42), (.9, .36), (.92, .58), (.12, .62)], hi=(240, 190, 110), w=.06))


def H6(c):
    """Ear of corn: the kernels leave it from the stalk end to the tip - the cob in six bands along its length, over
    the bare cob they leave behind; a kernel to fire."""
    import numpy as np
    src = c.comp("cob", "cob_rim", "cob_fill")
    lum = (src[..., :3] * np.array([.3, .59, .11], np.float32)).sum(-1, keepdims=True)
    bare = np.dstack([np.array([104, 70, 34], np.float32) / 255 * (1 - lum ** .8) +
                      np.array([246, 228, 170], np.float32) / 255 * lum ** .8, src[..., 3:]])
    c.add("cob_bare", bare, parent="cob", over_="cob_fill", pivot=(400, 730))
    lab = c.bands((330, 800), (800, 110), [1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6], amp=10, seed=4)
    c.pieces(src, lab, "rows{}", parent="cob", over_="cob_fill", ink=0)
    c.sprite("kernel", oval((252, 190, 36), w=.3, h=.34, hi=(255, 238, 150), point=.25))


def flame(d, S):
    """a tongue of fire, its foot at the bottom middle: the art's orange with a yellow heart"""
    out = [(.5, .03), (.6, .2), (.56, .32), (.72, .5), (.66, .62), (.8, .8), (.72, .97), (.28, .97), (.2, .78), (.33, .62),
           (.27, .46), (.42, .3), (.4, .16)]
    _poly(d, S, out, (246, 96, 22), w=.035)
    inn = [(.5 + (x - .5) * .5, .97 + (y - .97) * .62) for x, y in out]
    d.polygon([(x * S, y * S) for x, y in inn], fill=(255, 206, 60, 255))


def BS(c):
    """Free Spins badge: nothing cut - its letters and leaves are parts already."""


def ES(c):
    """Extreme Free Spins badge: the whole jack-o'-lantern with no crow and no letters on it (the generated plate,
    lined up - the rig's own back layer keeps the crow's far eye and its cream shape, fine while the crow barely
    moves, wrong once it flies off in the pop); the carved face's glow (the idle pulses it); a flame."""
    import os
    import numpy as np
    from scipy import ndimage
    import cut_parts as CP
    ic = CP.rgba(os.path.join(CP.ICONS, "ES.png"))
    p, _ = CP.lined_up(os.path.join(os.path.dirname(CP.ICONS), "parts", "ES", "plate_jack.png"), ic)
    c.add("jack_bare", np.asarray(p, np.float32) / 255, parent="jack", over_="jack", pivot=(500, 600))
    j = c.layer("jack")
    lit = (j[..., 0] > .9) & (j[..., 1] > .62) & (j[..., 2] < .5) & (j[..., 3] > .9)
    yy, xx = np.mgrid[0:1000, 0:1000]
    lit &= (yy > 380) & (yy < 830) & (xx > 160) & (xx < 850)
    al = np.clip(ndimage.gaussian_filter(lit.astype(np.float32), 9) * 1.5, 0, 1)
    c.add("faceglow", np.dstack([np.full_like(al, 1.0), np.full_like(al, .95), np.full_like(al, .62), al]),
          parent="jack", over_="jack", pivot=(500, 600), lift=.001)
    c.sprite("flame", flame, size=192)
