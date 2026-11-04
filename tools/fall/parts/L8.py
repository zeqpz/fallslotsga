"""L8 Cranberry Sauce, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L8.png.

The plate (a plate of the empty dish, and over it the plate as the icon draws it) at the back and the can-shaped jelly cut into three bands that wobble out of
step: the bottom band sits on the plate, the middle rides it, the top cap rides the middle. The seams run along the
jelly's own ridge lines (traced off the ink from the middle outwards), the ink staying with the band above, which is
drawn in front; the band below runs on OVERLAP px up under it, so a band sliding over the one below shows its ridge
outline, never a gap.

The jelly sits ON the plate, so its bands can't be generous polygons down there: each band's outline is traced off
the icon here (the jelly's red and its ink outline, plus its own sticker border where that lies off the plate), seen
from the band's middle, then cut "poly" by that exact shape."""
import math, os

import numpy as np
from PIL import Image
from scipy import ndimage

PLATES = {
    "plate": "Edit the attached picture: remove the can-shaped cranberry jelly completely and paint the bare, empty "
             "plate where it stood - the plate's flat cream centre and its inner shading carried on across. Keep the "
             "plate exactly the same: same position, same size, same colours, same gold rim, same black outline and "
             "the same cream sticker border round it. Nothing on the plate. Transparent background.",
}

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "..", "..", "..", "art", "fall-src", "icons", "L8.png")
SEAMS = {"hi": (560, 429), "lo": (560, 606)}     # where each seam's ridge line crosses the middle (its bottom edge)
OVERLAP = 22


def _load():
    a = np.asarray(Image.open(ICON).convert("RGBA")).astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    ink = (al > 100) & (a[..., :3].max(2) < 80)
    red = (al > 128) & (r > g + 45) & (r > b + 25)
    red = ndimage.binary_closing(red, iterations=5)              # across the ridge lines
    lab, n = ndimage.label(red)
    red = lab == 1 + int(np.argmax(ndimage.sum(red, lab, range(1, n + 1))))
    red = ndimage.binary_fill_holes(ndimage.binary_closing(red, iterations=4))
    jel = red.copy()
    for _ in range(11):                          # its own outline (and its AA rim)
        jel |= ndimage.binary_dilation(jel) & (ink | (al > 100) & (r > g + 20))
    jel = ndimage.binary_fill_holes(jel)
    cream = (al > 20) & (r > 200) & (g > 180) & (b > 140) & ~jel
    yy = np.arange(1000)[:, None]
    border = (al > 0) & ndimage.binary_dilation(jel, iterations=90) & (yy < 535)   # its sticker border + shadow, off the plate
    body = ndimage.binary_fill_holes(jel | border) & (al > 0)
    return ink, jel, body


def _trace(ink, start, inside):
    """follow a ridge line's bottom edge left and right from start; y for every x 0..999 (held flat past its ends)"""
    x0, y0 = start
    ys = {x0: y0}
    for step in (1, -1):
        y, gap, x = y0, 0, x0
        while 0 < x + step < 999 and gap < 40:
            x += step
            cand = [yy for yy in range(int(y) - 5, int(y) + 6) if ink[yy - 1, x] and not ink[yy, x] and inside[yy - 1, x]]
            if cand:
                y = min(cand, key=lambda v: abs(v - y))
                gap = 0
                ys[x] = y
            else:
                gap += 1
    xs = sorted(ys)
    v = ndimage.median_filter(np.array([ys[x] for x in xs], float), 9)
    return np.interp(np.arange(1000), xs, v)


def _star(m, n=1440):
    """the outline of m seen from its middle: the farthest pixel of m along each ray"""
    cy, cx = np.argwhere(m).mean(0)
    pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        dx, dy = math.cos(th), math.sin(th)
        far = 0
        for rr in range(0, 760, 2):
            x, y = int(cx + dx * rr), int(cy + dy * rr)
            if not (0 <= x < 1000 and 0 <= y < 1000):
                break
            if m[y, x]:
                far = rr
        pts.append((round(cx + dx * (far + 2.5)), round(cy + dy * (far + 2.5))))
    return pts


def _band(body, hi=None, lo=None):
    yy = np.arange(1000)[:, None]
    m = body.copy()
    if hi is not None:
        m &= yy >= hi[None, :]
    if lo is not None:
        m &= yy < lo[None, :]
    return _star(m)


_ink, _jel, _body = _load()
_inner = ndimage.binary_erosion(_jel, iterations=9)          # the ridges, not the outline or the plate's rim
HI, LO = _trace(_ink, SEAMS["hi"], _inner), _trace(_ink, SEAMS["lo"], _inner)


def _around(star):
    """everything but the jelly: the whole picture with the jelly's outline as a hole (a slit down from the top
    edge to it, so it is one polygon)"""
    k = min(range(len(star)), key=lambda i: star[i][1])
    ring = star[k:] + star[:k + 1]
    top = (star[k][0], 0)
    return [top, (0, 0), (0, 999), (999, 999), (999, 0), top] + ring[::-1]


LAYERS = [
    dict(name="plate", src="plate:plate", pivot=(500, 790), parent="root"),
    # the plate as the icon draws it, over the painted one (which only shows where the jelly moves off it)
    dict(name="plate_art", src="art", cut="poly", poly=_around(_star(_body)), pivot=(500, 790), parent="plate"),
    dict(name="jelly_lo", src="art", cut="poly", poly=_band(_body, hi=LO - OVERLAP), pivot=(540, 795), parent="root"),
    dict(name="jelly_mid", src="art", cut="poly", poly=_band(_body, hi=HI - OVERLAP, lo=LO), pivot=(550, 555),
         parent="jelly_lo"),
    dict(name="jelly_top", src="art", cut="poly", poly=_band(_body, lo=HI), pivot=(560, 320), parent="jelly_mid"),
]
