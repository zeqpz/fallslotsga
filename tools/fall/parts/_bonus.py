"""Helpers for the BS / ES bonus badge specs (cut_parts.py itself is untouched).

The badges' moving pieces (letters, a crow) sit ON the badge with no plate of their own, so:
  - each piece's mask is worked out from the icon's colours inside a rough polygon (the letter fill, its 3D shadow and
    the black outline round it), and handed to cut_parts as an exact cut "poly" polygon (maskpoly.poly)
  - the back layer is a plate made here, "base": the icon itself everywhere, and the generated plate (the badge with
    the pieces taken off, lined up the way cut_parts lines plates up) only under the pieces - so at rest the badge is
    exactly the icon, and a piece moving off it shows the bare badge, never a ghost of itself.
"base" has the icon's own silhouette, so cut_parts lines it up with no shift."""
import os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import maskpoly as M                                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SIDE = 1000
CREAM = (249, 231, 199)


def icon(sid):
    return np.asarray(Image.open(os.path.join(ROOT, "art", "fall-src", "icons", sid + ".png")).convert("RGBA")
                      ).astype(np.int16)


def inside(pts):
    im = Image.new("L", (SIDE, SIDE), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=255)
    return np.asarray(im) > 0


def hue(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(2), rgb.min(2)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4))
    return h * 60


def piece(ic, rough, pick, ink_grow=10, close=3, frac=.02):
    """the largest patch of pick(rgb 0..1, hue deg, sat, val) inside rough, holes filled, grown out over the dark
    ink (the black outline and drop shadow round it) by up to ink_grow px, inside rough"""
    rgb = ic[..., :3].astype(np.float32) / 255
    mx, mn = rgb.max(2), rgb.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    on = ic[..., 3] > 128
    m = rough & on & pick(rgb, hue(rgb), sat, mx)
    m = ndimage.binary_opening(m, iterations=2)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, 1 + np.nonzero(sizes >= sizes.max() * frac)[0])
    m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=close))
    ink = on & (mx < .3) & rough
    for _ in range(ink_grow):
        m |= ndimage.binary_dilation(m) & ink
    m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=2))
    return ndimage.binary_dilation(m, iterations=1) & on        # the outline's soft outer edge


def make_base(sid, plate, masks):
    """plate_base.png: the icon, with the lined-up generated plate under the moving pieces (grown a little)"""
    import cut_parts as CP
    src = os.path.join(ROOT, "art", "fall-src", "parts", sid)
    ic = icon(sid)
    p, _ = CP.lined_up(os.path.join(src, f"plate_{plate}.png"), ic)
    under = np.zeros((SIDE, SIDE), bool)
    for m in masks:
        under |= m
    under = ndimage.binary_dilation(under, iterations=3)
    out = ic.copy()
    out[under, :3] = p[under, :3]
    # where the plate has nothing (a piece that stood out past the badge, like the crow over the sky), the sticker's
    # cream border carries on under it, so a piece moving a little shows border, not a hole
    bare = under & (p[..., 3] < 160) & (ic[..., 3] > 128)
    out[bare, :3] = CREAM
    Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(src, "plate_base.png"))
    return under


def polygon(m):
    return M.poly(m)


def preview(sid, masks, out):
    """the icon with each mask tinted, for checking"""
    ic = icon(sid).astype(np.float32)
    cols = [(255, 0, 255), (0, 255, 255), (0, 255, 0), (255, 255, 0), (0, 128, 255)]
    v = ic.copy()
    for k, m in enumerate(masks):
        v[m, :3] = v[m, :3] * .45 + np.array(cols[k % len(cols)]) * .55
    bg = Image.new("RGBA", (SIDE, SIDE), (40, 40, 52, 255))
    bg.alpha_composite(Image.fromarray(v.clip(0, 255).astype(np.uint8), "RGBA"))
    bg.convert("RGB").save(out)
