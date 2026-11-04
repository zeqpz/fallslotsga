"""Clean the champagne art (art/fall-src/champagne/*.png, tools/fall/gen_champagne.py) and lay it out for Blender:
  art/fall-src/clean/M.png            the corked bottle, cleaned (the Multi's resting art; prep_icons.py M lays it out)
  art/fall-src/icons/M_open.png       the uncorked bottle on the same 1000 px canvas as icons/M.png, registered onto the
                                      corked one (its body lined up by scale and shift) so the swap at the pop never jumps
  art/fall-src/icons/M_empty.png, M_open_empty.png   the same two EMPTY (Blender paints the cider in, cut to M_glass.png)
  art/fall-src/icons/M_hands.png      the gloved hands holding it, a layer of their own (hands())
  art/fall-src/fx/{cork,fizz_*,foam_puff}.png   the effect sprites, trimmed, 1000 px square, art 900 px
usage: python tools/fall/prep_champagne.py"""
import os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clean_alpha

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "fall-src", "champagne")
CLEAN = os.path.join(ROOT, "art", "fall-src", "clean")
ICONS = os.path.join(ROOT, "art", "fall-src", "icons")
FX = os.path.join(ROOT, "art", "fall-src", "fx")
SIDE, ART = 1000, 940


def bbox(im, thr=8):
    return im.getchannel("A").point(lambda v: 255 if v > thr else 0).getbbox()


def canvas(im, k, centre):
    """The art scaled by k and centred at `centre` on a SIDE x SIDE canvas."""
    im = im.convert("RGBa").resize((round(im.width * k), round(im.height * k)), Image.LANCZOS).convert("RGBA")
    out = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    out.alpha_composite(im, (round(centre[0] - im.width / 2), round(centre[1] - im.height / 2)))
    return out


def sprite(name):
    c = os.path.join(CLEAN, "champagne_" + name + ".png")
    clean_alpha.clean(os.path.join(SRC, name + ".png"), c)
    im = Image.open(c).convert("RGBA")
    im = im.crop(bbox(im))
    k = 900 / max(im.size)
    os.makedirs(FX, exist_ok=True)
    canvas(im, k, (SIDE / 2, SIDE / 2)).save(os.path.join(FX, name + ".png"))


def body_box(im):
    """The bottle's lower body (the bottom 55% of its box): the part both versions share unchanged."""
    x0, y0, x1, y1 = bbox(im)
    a = np.asarray(im.getchannel("A"))[int(y0 + .45 * (y1 - y0)):y1] > 128
    xs = np.nonzero(a.any(0))[0]
    return xs.min(), xs.max() + 1, y1


def main():
    os.makedirs(CLEAN, exist_ok=True)
    old = os.path.join(CLEAN, "M.png")
    if os.path.exists(old) and not os.path.exists(os.path.join(CLEAN, "M_cider_popped.png")):
        os.replace(old, os.path.join(CLEAN, "M_cider_popped.png"))   # the art the game had until 2026-11-03
    clean_alpha.clean(os.path.join(SRC, "corked.png"), os.path.join(CLEAN, "M.png"))
    a = Image.open(os.path.join(CLEAN, "M.png")).convert("RGBA")
    # the corked bottle's layout is prep_icons.py's (longer side 940, centred); the others get the same scale and
    # are then moved so their body lies over the corked one's
    bx = bbox(a)
    k = ART / max(a.crop(bx).size)
    os.makedirs(ICONS, exist_ok=True)
    for src, out in (("open", "M_open"), ("corked_empty", "M_empty"), ("open_empty", "M_open_empty")):
        clean_alpha.clean(os.path.join(SRC, src + ".png"), os.path.join(CLEAN, out + ".png"))
        moved, s, off = register(a, Image.open(os.path.join(CLEAN, out + ".png")).convert("RGBA"), bx, k)
        moved.save(os.path.join(ICONS, out + ".png"))
        print(out, "scale", round(s, 4), "shift", *off)
    glass_mask()
    for name in ("cork", "fizz_burst", "fizz_jet", "fizz_jet_b", "fizz_jet_c", "fizz_burst_b", "foam_puff"):
        sprite(name)
    cork_up()
    hands()
    print("done")


def label_box(im):
    """The cream paper label (the largest cream patch not touching the outside, which the sticker border does): its
    left, top and right edges are the mark two drawings of the bottle are lined up by (a glove may cover its foot).
    -> (x0, y0, x1) px"""
    from scipy import ndimage
    a = np.asarray(im.convert("RGBA")).astype(int)
    cream = (a[..., 3] > 200) & (a[..., 0] > 205) & (a[..., 1] > 190) & (a[..., 2] > 150) & (a[..., 0] - a[..., 2] < 80)
    outside = ndimage.binary_dilation(a[..., 3] < 20, iterations=6)
    cream = ndimage.binary_closing(cream, iterations=6)          # across the XXX lettering
    lab, n = ndimage.label(cream)
    best, size = None, 0
    for i in range(1, n + 1):
        m = lab == i
        if (m & outside).any():
            continue
        if m.sum() > size:
            best, size = m, m.sum()
    ys, xs = np.nonzero(best)
    return xs.min(), ys.min(), xs.max() + 1


def hands():
    """The gloved hands holding the bottle, as a layer of their own (icons/M_hands.png, on the bottle's canvas):
    the generator drew the empty bottle again with the gloves on it (champagne/corked_hands.png); that drawing is
    lined up on the empty bottle by its label, and the gloves are what differs from the bottle - so in
    Blender they ride the bottle's rig, shake it, and stay on as it pops."""
    from scipy import ndimage
    clean_alpha.clean(os.path.join(SRC, "corked_hands.png"), os.path.join(CLEAN, "M_hands_full.png"))
    full = Image.open(os.path.join(CLEAN, "M_hands_full.png")).convert("RGBA")
    empty = Image.open(os.path.join(ICONS, "M_empty.png")).convert("RGBA")
    ex0, ey0, ex1 = label_box(empty)
    hx0, hy0, hx1 = label_box(full)
    k = (ex1 - ex0) / (hx1 - hx0)
    big = full.convert("RGBa").resize((round(full.width * k), round(full.height * k)), Image.LANCZOS).convert("RGBA")
    on = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    on.alpha_composite(big, (round((ex0 + ex1) / 2 - (hx0 + hx1) / 2 * k), round(ey0 - hy0 * k)))
    h = np.asarray(on).astype(np.int16)
    e = np.asarray(empty).astype(np.int16)
    # what the gloves add: colour that moved a long way from the bottle's, or anything where the bottle has nothing
    diff = (np.abs(h[..., :3] - e[..., :3]).sum(2) > 110) & (h[..., 3] > 128)
    diff |= (h[..., 3] > 128) & (e[..., 3] < 40)
    near = ndimage.binary_dilation(ndimage.binary_opening(diff, iterations=2), iterations=16)
    # the gloves are their own tan leather: that colour, near where the drawing changed (so the cork, the same
    # brown, stays the bottle's), holes filled; then grown out over their own black ink line and the sticker
    # border round them where they stick out past the bottle - never onto the glass
    rgb = h[..., :3].astype(np.float32) / 255
    mx, mn = rgb.max(2), rgb.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    tan = (h[..., 3] > 128) & (rgb[..., 0] > rgb[..., 1]) & (rgb[..., 1] > rgb[..., 2]) & (sat > .3) & (mx > .3) &           (rgb[..., 0] - rgb[..., 2] > .25) & (rgb[..., 1] - rgb[..., 2] > .08)
    glove = ndimage.binary_opening(tan & near, iterations=2)
    lab, n = ndimage.label(glove)
    sizes = ndimage.sum(glove, lab, range(1, n + 1))
    glove = ndimage.binary_fill_holes(np.isin(lab, 1 + np.nonzero(sizes >= 2500)[0]))
    ink = (h[..., 3] > 100) & (mx < .3)
    cream = (h[..., 3] > 100) & (e[..., 3] < 60)                # sticker border past the bottle's edge
    keep = glove.copy()
    for _ in range(9):
        keep |= ndimage.binary_dilation(keep) & (ink | cream)
    keep = ndimage.binary_fill_holes(keep)
    keep = ndimage.binary_dilation(keep)                        # a pixel of overlap, no seam
    out = np.asarray(on).copy()
    out[..., 3] = np.where(keep, out[..., 3], 0)
    Image.fromarray(out, "RGBA").save(os.path.join(ICONS, "M_hands.png"))
    print("hands: scale", round(k, 4), "pieces", int((sizes >= 2500).sum()))   # the glove pieces


def cork_up():
    """The cork stood upright, its cap at the top (fx/cork_up.png): the generator drew it leaning. Its long axis is
    found from its silhouette (the principal axis), the cap end by where the gold is. symanim.py render_cork tumbles
    it from there, so the game's first drawing of it matches the cork seated in the bottle."""
    im = Image.open(os.path.join(FX, "cork.png")).convert("RGBA")
    arr = np.asarray(im).astype(int)
    a = arr[..., 3] > 128
    ys, xs = np.nonzero(a)
    w, v = np.linalg.eigh(np.cov(np.vstack([xs - xs.mean(), ys - ys.mean()])))
    ax = v[:, np.argmax(w)]
    gold = a & (arr[..., 0] > 180) & (arr[..., 1] > 140) & (arr[..., 2] < 90)
    gy, gx = np.nonzero(gold)
    if (gx.mean() - xs.mean()) * ax[0] + (gy.mean() - ys.mean()) * ax[1] < 0:
        ax = -ax                                                 # point it at the cap
    turn = np.degrees(np.arctan2(ax[0], -ax[1]))                 # the cap's lean from straight up, clockwise +
    up = im.rotate(turn, resample=Image.BICUBIC, expand=True)
    up = up.crop(bbox(up))
    canvas(up, 900 / max(up.size), (SIDE / 2, SIDE / 2)).save(os.path.join(FX, "cork_up.png"))
    print("cork stood up by", round(turn, 1), "deg")


def register(a, b, bx, k):
    """b scaled and shifted so its body (width, foot) lies over a's, cut with a's window and laid out like it."""
    ax0, ax1, ay1 = body_box(a)
    bx0, bx1, by1 = body_box(b)
    s = (ax1 - ax0) / (bx1 - bx0)                       # scale that lines the bodies' widths up
    off_x = (ax0 + ax1) / 2 - (bx0 + bx1) / 2 * s       # shift (in the source's px, after scaling b by s)
    off_y = ay1 - by1 * s
    big = b.convert("RGBa").resize((round(b.width * s), round(b.height * s)), Image.LANCZOS).convert("RGBA")
    moved = Image.new("RGBA", a.size, (0, 0, 0, 0))
    moved.alpha_composite(big, (round(off_x), round(off_y)))
    return canvas(moved.crop(bx), k, (SIDE / 2, SIDE / 2)), s, (round(off_x), round(off_y))


def glass_mask():
    """Where the cider can show: the empty bottle's green glass (not its outline, label, foil or highlights), as
    icons/M_glass.png - white, alpha = the glass, eased 1 px at its edge. Blender's liquid is cut to it."""
    from scipy import ndimage
    im = np.asarray(Image.open(os.path.join(ICONS, "M_empty.png")).convert("RGB")).astype(np.float32) / 255
    al = np.asarray(Image.open(os.path.join(ICONS, "M_empty.png")).getchannel("A")) > 200
    mx, mn = im.max(2), im.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    g = (im[..., 1] >= im[..., 0]) & (im[..., 1] > im[..., 2]) & (sat > .3) & (mx > .1) & al
    g = ndimage.binary_opening(g, iterations=2)
    lab, n = ndimage.label(g)
    sizes = ndimage.sum(g, lab, range(1, n + 1))
    g = np.isin(lab, 1 + np.nonzero(sizes >= sizes.max() * .02)[0])
    # the glass's darkest shading (its foot) fell under the threshold: small dark holes in it are glass too - the
    # label (big, bright) and the highlights (bright) stay out
    holes, n = ndimage.label(ndimage.binary_fill_holes(g) & ~g)
    for i in range(1, n + 1):
        h = holes == i
        if h.sum() < 4000 and mx[h].mean() < .3:
            g |= h
    soft = ndimage.gaussian_filter(g.astype(np.float32), .8)
    out = np.dstack([np.full(g.shape, 255, np.uint8)] * 3 + [(soft * 255).astype(np.uint8)])
    Image.fromarray(out, "RGBA").save(os.path.join(ICONS, "M_glass.png"))
    ys, xs = np.nonzero(g)
    print("glass rows", ys.min(), ys.max(), "cols", xs.min(), xs.max())


if __name__ == "__main__":
    main()
