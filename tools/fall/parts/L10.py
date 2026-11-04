"""L10 Hay Bale, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L10.png.

The plate is a bare bale (no twine, no loose tufts): it shows only where a part moves off. Over it, the icon's own
pixels: the bale block (everything inside HULL, the solid bale), the two twine bands (the red, with its ink), and the
tufts - the ring of loose straw and sticker border outside HULL, split into pieces round the bale where the ring is
thinnest (no tuft there, just border), each turning about the middle of its stretch of the bale's edge.
The drawing's ink doesn't close its areas (the straw runs into the border), so every piece is a mask traced into a
cut "poly" polygon by maskpoly.py."""
import math, os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maskpoly as M

PLATES = {
    "bare": "Edit the attached picture: remove the two red twine bands completely, painting the same golden straw "
            "where they were; and trim off ALL the loose straw tufts sticking out past the bale's edges (top, sides "
            "and bottom), so it is a neat rectangular hay bale block. Keep the bale exactly the same otherwise: same "
            "position, same size, same golden colours and straw texture on its faces, same black outline, with the "
            "cream sticker border hugging its new outline. Transparent background.",
}

# the solid bale (its block, inside the loose tufts), clockwise from the top-left
HULL = [(115, 300), (180, 255), (240, 232), (330, 215), (450, 205), (560, 225), (700, 262), (790, 285), (870, 300),
        (905, 380), (900, 520), (880, 640), (850, 720), (790, 775), (690, 805), (560, 820), (440, 775), (330, 740),
        (200, 700), (120, 640), (95, 520), (95, 400)]
C = (500, 510)                                   # the bale's middle, for the sectors
N_TUFTS = 8


def _pmask(p):
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon(p, fill=255)
    return np.asarray(im) > 0


def _parts():
    a = M.icon("L10")
    rgb, sat, val = M.hsv(a)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    on = a[..., 3] > 0
    yy, xx = np.mgrid[:1000, :1000]
    ink = on & (val < .24)
    red = on & (r > g * 2) & (b > g * .85) & (sat > .45) & (val > .25)          # the twine is pinkish: blue over green
    lab, n = ndimage.label(ndimage.binary_closing(red, iterations=2))
    big = sorted(range(1, n + 1), key=lambda k: -(lab == k).sum())[:2]
    twines = []
    for k in big:
        t = ndimage.binary_fill_holes(lab == k)
        for _ in range(7):
            t |= ndimage.binary_dilation(t) & ink
        twines.append(t)
    twines.sort(key=lambda t: np.nonzero(t)[1].mean())
    tw = twines[0] | twines[1]
    hull = _pmask(HULL)
    ring = on & ~hull & ~tw
    # the ring's thickness round the bale, by angle; cut it where it is thinnest
    ang = (np.degrees(np.arctan2(yy - C[1], xx - C[0])) + 360) % 360
    dist = np.hypot(yy - C[1], xx - C[0])
    th = np.zeros(360)
    for d in range(360):
        sel = ring & (ang >= d) & (ang < d + 1)
        hsel = hull & (ang >= d) & (ang < d + 1)
        th[d] = (dist[sel].max() if sel.any() else 0) - (dist[hsel].max() if hsel.any() else 0)
    sm = np.convolve(np.r_[th, th, th], np.ones(9) / 9, "same")[360:720]
    cuts = []
    for d in np.argsort(sm):                                  # thinnest first, at least 30 degrees apart
        if all(min(abs(d - c), 360 - abs(d - c)) >= 30 for c in cuts):
            cuts.append(int(d))
        if len(cuts) == N_TUFTS:
            break
    cuts.sort()
    tufts = []
    for k in range(len(cuts)):
        d0, d1 = cuts[k], cuts[(k + 1) % len(cuts)]
        sel = ((ang >= d0) & (ang < d1)) if d0 < d1 else ((ang >= d0) | (ang < d1))
        m = ring & sel
        mid = math.radians((d0 + ((d1 - d0) % 360) / 2) % 360)
        # the pivot: where the ray through the stretch's middle leaves the hull
        rr = 0
        while hull[int(C[1] + math.sin(mid) * rr), int(C[0] + math.cos(mid) * rr)]:
            rr += 2
        tufts.append((m, (int(C[0] + math.cos(mid) * rr), int(C[1] + math.sin(mid) * rr)), (d0 + ((d1 - d0) % 360) / 2) % 360))
    body = on & hull & ~tw
    return body, twines, tufts, cuts


_body, _twines, _tufts, CUTS = _parts()
MASKS = dict(body=_body, twine_l=_twines[0], twine_r=_twines[1])
for k, (m, p, d) in enumerate(_tufts):
    MASKS[f"tuft{k}"] = m
M.tidy(MASKS)
TUFT_DIR = {f"tuft{k}": d for k, (m, p, d) in enumerate(_tufts)}   # which way each tuft points (deg, image y down)
_P = {k: M.poly(v) for k, v in MASKS.items()}                       # (for the checks)

LAYERS = [dict(name="bale", src="plate:bare", pivot=(500, 800), parent="root")]
LAYERS += M.layers("body", MASKS["body"], (500, 800), "bale")
for k, (m, p, d) in enumerate(_tufts):
    LAYERS += M.layers(f"tuft{k}", MASKS[f"tuft{k}"], p, "body")          # they ride the bale as it bulges
# the twine rides the plate, not the block: when the block bulges, it bulges round the twine
LAYERS += M.layers("twine_l", MASKS["twine_l"], (250, 520), "bale")
LAYERS += M.layers("twine_r", MASKS["twine_r"], (560, 560), "bale")
