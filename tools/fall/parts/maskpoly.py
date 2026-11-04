"""Masks -> cut "poly" polygons, for the L7-L10 specs (cut_parts.py itself is untouched).

cut_parts' cut "poly" takes a part's exact shape as one polygon; when a part's outline isn't simple (a steam wisp, a
rim strip, a gravy pool) the spec works out the part's mask from the icon's colours and turns it into that polygon
here: the outline of every piece of the mask traced pixel by pixel (Moore neighbours), through the boundary pixels'
centres - PIL fills a polygon's inside and its edge pixels, so the polygon fills exactly the mask. Holes are filled;
separate pieces are joined by straight slits (a 1 px line, cut away again wherever the icon is transparent).
outline()/layers() keep holes: each hole's outline is bridged into the piece's, so a band through a part stays out."""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ICONS = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)),
                                   "..", "..", "..", "art", "fall-src", "icons")

# clockwise in image coords (y down), starting west
NB = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1)]


def icon(sid):
    return np.asarray(Image.open(f"{ICONS}/{sid}.png").convert("RGBA")).astype(np.float32)


def hsv(a):
    rgb = a[..., :3] / 255
    mx, mn = rgb.max(2), rgb.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return rgb, sat, mx


def _ring(m):
    """the outer boundary of the (single, hole-free) component m, as boundary-pixel centres, clockwise"""
    ys, xs = np.nonzero(m)
    k = np.lexsort((xs, ys))[0]
    s = (int(xs[k]), int(ys[k]))
    H, W = m.shape
    inside = lambda p: 0 <= p[0] < W and 0 <= p[1] < H and m[p[1], p[0]]
    def step(c, b):
        i = NB.index((b[0] - c[0], b[1] - c[1]))
        for k in range(1, 9):
            d = NB[(i + k) % 8]
            n = (c[0] + d[0], c[1] + d[1])
            if inside(n):
                pd = NB[(i + k - 1) % 8]
                return n, (c[0] + pd[0], c[1] + pd[1])
        return None, None

    c, b = s, (s[0] - 1, s[1])
    first = None
    out = [s]
    for _ in range(4 * int(m.sum()) + 16):
        n, b = step(c, b)
        if n is None:
            return out                                 # a lone pixel
        if first is None:
            first = n
        elif c == s and n == first:                    # back at the start, about to go round again
            out.pop()
            break
        out.append(n)
        c = n
    return out


def poly(m, min_px=30):
    """one polygon filling mask m (holes filled), every piece of it traced and the pieces joined"""
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    rings = []
    for k in range(1, n + 1):
        c = lab == k
        if c.sum() >= min_px:
            rings.append(_ring(c))
    out = []
    for r in rings:
        out += r + [r[0]]
    return out


def check(m, p):
    """how many pixels the polygon's fill gets wrong against the mask (holes filled)"""
    im = Image.new("L", (m.shape[1], m.shape[0]), 0)
    ImageDraw.Draw(im).polygon(p, fill=255)
    f = np.asarray(im) > 0
    m = ndimage.binary_fill_holes(m)
    return int((f & ~m).sum()), int((m & ~f).sum())


def tidy(masks, min_px=400, max_hole=3000):
    """Make a partition of the icon polygon-friendly: a piece's small holes are filled (taken from whoever had them)
    and its small crumbs given to the piece they touch most. masks: name -> bool array, changed in place."""
    names = list(masks)
    for _ in range(2):
        for n in names:
            h = ndimage.binary_fill_holes(masks[n]) & ~masks[n]
            lab, k = ndimage.label(h)
            for j in range(1, k + 1):
                c = lab == j
                if c.sum() <= max_hole:
                    for o in names:
                        masks[o] &= ~c
                    masks[n] |= c
            lab, k = ndimage.label(masks[n], structure=np.ones((3, 3)))
            for j in range(1, k + 1):
                c = lab == j
                if c.sum() < min_px:
                    ring = ndimage.binary_dilation(c, iterations=2) & ~c
                    best = max((o for o in names if o != n), key=lambda o: (masks[o] & ring).sum())
                    if (masks[best] & ring).sum():
                        masks[n] &= ~c
                        masks[best] |= c
    return masks


def pieces(m, min_px=50):
    """the separate pieces of m, biggest first"""
    lab, k = ndimage.label(m, structure=np.ones((3, 3)))
    out = [lab == j for j in range(1, k + 1)]
    out = [c for c in out if c.sum() >= min_px]
    return sorted(out, key=lambda c: -c.sum())


def outline(c):
    """one polygon filling the single piece c exactly, holes and all: its outer outline, and each hole's outline
    (through the piece's pixels round the hole) spliced in by a short bridge from the nearest outline point"""
    p = _ring(ndimage.binary_fill_holes(c))
    holes = ndimage.binary_fill_holes(c) & ~c
    lab, k = ndimage.label(holes)
    for j in sorted(range(1, k + 1), key=lambda j: -(lab == j).sum()):
        h = lab == j
        if h.sum() < 4:
            continue
        inner = _ring(ndimage.binary_dilation(h, structure=np.ones((3, 3))))
        o, i = np.array(p), np.array(inner)
        step = max(1, len(o) * len(i) // 4000000)            # (keep the distance table small)
        d = ((o[::step, None, :] - i[None, :, :]) ** 2).sum(2)
        a, b = np.unravel_index(d.argmin(), d.shape)
        a *= step
        p = p[:a + 1] + inner[b:] + inner[:b + 1] + [p[a]] + p[a + 1:]
    return p


def layers(name, m, pivot, parent, **kw):
    """cut "poly" layers for mask m: the biggest piece is `name`, any other piece rides it (name_2, ...)"""
    out = []
    for k, c in enumerate(pieces(m)):
        out.append(dict(name=name if k == 0 else f"{name}_{k + 1}", src="art", cut="poly", poly=outline(c),
                        pivot=pivot, parent=parent if k == 0 else name, **kw))
    return out
