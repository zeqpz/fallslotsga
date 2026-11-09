"""Cut the foreground (the big pumpkins, vines, log and hay bale along the bottom edge) out of the
farm painting into its own layer, and paint the field in behind them (owner, 2026-11-08: the
foreground must not move when the background moves).

Run:  <py with cv2> -I tools/fall/bg/cut_foreground.py [preview_dir]
      (after clean_leaves.py; cv2 lives in projects/slotsgame/.venv312)

Reads  art/fall-src/bg/bonus_wall_noleaves.png
Writes frontend/assets/bonus_wall.webp     the back plate: field painted in behind the foreground
                                           (bgfx.js and #bgwall draw this one)
       frontend/assets/bg/fg_left.webp     RGBA cut-outs, cropped to their boxes, with #bgwall's
       frontend/assets/bg/fg_right.webp    warm gradient tint baked in (see TINT)
       art/fall-src/bg/fg.json             the boxes, in painting px (index.html's #fgwall uses them)
       art/fall-src/bg/fg_alpha.png        the full-size alpha, for review / later tools

How the cut works: a hand-drawn polygon per cluster that holds all of it with a margin of open
ground (checked on crops), ending on the picture's edges. Inside it the ground is flood-filled
from the polygon's open (not picture-edge) sides through everything that isn't black ink, so it
stops exactly at the objects' ink outlines - and a mid-ground thing the polygon crosses (the
fence-row pumpkins and corn above the bale) floods away as ground too. What is left is the
foreground, plus the ink of its outline (ink within OUTLINE px of it; dirt strokes further out
go back to the ground). Small leftovers are dropped. The alpha is softened by half a pixel.

The hole (the cut, grown a few px) is painted from the ground round it: a low-res inpaint for
the broad colour (no streaks), a full-res one blended in near the edge, plus the field's own
grain (high-pass of open ground, leaves cleaned out) so the patch reads as dirt. Only a band
near the cut's edge is ever seen (when the camera hops the wall slides by ~30 screen px).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "art/fall-src/bg/bonus_wall_noleaves.png"
BACK = ROOT / "frontend/assets/bonus_wall.webp"
FG_DIR = ROOT / "frontend/assets/bg"
META = ROOT / "art/fall-src/bg/fg.json"
ALPHA = ROOT / "art/fall-src/bg/fg_alpha.png"
IW, IH = 3840, 2160
TARGET_BYTES = 1261200            # the original painting's webp size: pick the quality nearest it

# #bgwall's gradient, baked into the cut-outs: rgba(40,18,6, .06 -> .26) top to bottom of the
# wall's box. With `cover` on a box no wider than 16:9 the painting spans the box's height
# exactly, so image row y sits at y/IH of the box (wider screens crop the foot: off by < .02).
TINT = np.array([40, 18, 6], np.float32)
TA0, TA1 = .06, .26

INK = 52          # grey level below which a pixel is outline ink
OUTLINE = 9       # px: ink this close to a foreground body is its outline

# x, y in painting px. Each ends on the picture's border (x=0 / x=IW / y=IH), which is not a
# flood source - the pumpkins run off the picture there.
POLY = {
    "left": [(0, IH), (0, 1800), (60, 1810), (92, 1832), (150, 1842), (232, 1834), (245, 1795), (330, 1778),
             (380, 1795), (378, 1832), (405, 1840), (420, 1818), (455, 1822), (525, 1860), (600, 1872),
             (655, 1920), (662, 2034), (745, 2030), (752, 1985), (795, 1980), (862, 1980), (868, 2020),
             (850, 2032), (962, 2032), (980, 2068), (1012, 2060), (1075, 2092), (1165, 2098), (1165, IH)],
    "right": [(1700, IH), (1700, 2060), (1760, 2040), (1790, 1982), (1850, 1972), (1960, 1968),
              (1990, 1958), (2010, 1932), (2060, 1922), (2112, 1936), (2150, 1972), (2200, 1958),
              (2212, 1924), (2300, 1920), (2308, 1904), (2352, 1906), (2418, 1902), (2458, 1848),
              (2478, 1790), (2488, 1718), (2560, 1712), (2640, 1702), (2720, 1708), (2800, 1715),
              (2858, 1734), (2945, 1730), (2992, 1758), (3035, 1755), (3038, 1590), (3058, 1545),
              (3240, 1532), (3560, 1515), (IW, 1515), (IW, IH)],
}
# things with no ink outline of their own: a sure-inside polygon, grown out into their own colour
# (hay: light, yellow) - the bale's silhouette is drawn with straw, not a line
FORCE = {
    "right": [{"poly": [(3082, 1598), (3250, 1585), (3550, 1565), (IW, 1550), (IW, 1875), (3082, 1875)],
               "grow": 40, "clip": [(3030, 1500), (3580, 1500), (3580, 1528), (IW, 1528), (IW, IH), (3030, IH)]}],
}


def hay(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    return (h >= 14) & (h <= 30) & (s >= 70) & (v >= 165)


def poly_mask(pts):
    im = Image.new("L", (IW, IH), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return np.asarray(im) > 0


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def forced(img, specs):
    out = np.zeros((IH, IW), bool)
    hy = None
    for sp in specs:
        m = poly_mask(sp["poly"])
        if sp.get("grow"):
            hy = hay(img) if hy is None else hy
            allow = hy & poly_mask(sp["clip"])
            for _ in range(sp["grow"]):           # geodesic growth through straw-coloured pixels
                m = m | (ndi.binary_dilation(m) & allow)
            m = ndi.binary_closing(m, iterations=3) & poly_mask(sp["clip"])   # its dark strands
            m = ndi.binary_fill_holes(m)
            m = ndi.binary_opening(m, iterations=1) | poly_mask(sp["poly"])
        out |= m
    return out


def cut(img, gray, pts, force=None):
    inside = poly_mask(pts)
    ink = gray < INK
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
    sure = forced(img, force) & inside if force else np.zeros_like(inside)
    ring = ndi.binary_dilation(inside, iterations=3) & ~inside          # open sides only (none past the border)
    # the vines' leaves are outlined in dark green, not black: green is never ground here, so it
    # walls the flood in and counts as foreground body
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    green = (hsv[..., 0] >= 20) & (hsv[..., 0] <= 60) & (hsv[..., 1] >= 55) & (hsv[..., 2] >= 35) & (hsv[..., 2] <= 200)   # dirt is hue <= 18; bright = yellow leaves
    green = ndi.binary_opening(green, iterations=1) & inside
    walk = (inside & ~ink & ~sure & ~green) | ring
    lab, _ = ndi.label(walk)
    ground_ids = np.unique(lab[ring])
    ground = np.isin(lab, ground_ids[ground_ids > 0]) & inside
    core = (inside & ~ink & ~ground) | sure | green                              # bodies (and enclosed islands)
    near = ndi.distance_transform_edt(~core) <= OUTLINE
    fg = core | (inside & ink & near)
    fg = ndi.binary_fill_holes(fg)
    lab2, n2 = ndi.label(fg)
    if n2:
        sizes = ndi.sum(fg, lab2, range(1, n2 + 1))
        keep = np.zeros(n2 + 1, bool)
        keep[1:] = sizes >= 20000
        fg = keep[lab2]
    return fg


# open field with nothing on it but ground and its fallen leaves: the source of the painted-in field
PLATE_X0, PLATE_X1 = 1080, 1760


def membrane(known_val, known, hole, k=4, iters=600):
    """smooth (harmonic) interpolation of known_val over `hole` from the `known` pixels, at 1/k res"""
    h, w = IH // k, IW // k
    kv = cv2.resize(known_val * known[..., None], (w, h), interpolation=cv2.INTER_AREA)
    kw = cv2.resize(known.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    ok = kw > .2
    val = np.zeros_like(kv)
    val[ok] = kv[ok] / kw[ok, None]
    todo = ~ok
    for sgm in (40, 16, 6):                       # coarse start
        num = cv2.GaussianBlur(val * ok[..., None], (0, 0), sgm)
        den = cv2.GaussianBlur(ok.astype(np.float32), (0, 0), sgm)[..., None]
        upd = todo & (den[..., 0] > (1e-6 if sgm == 40 else .05))
        val[upd] = (num / np.maximum(den, 1e-9))[upd]
    ker = np.array([[0, .25, 0], [.25, 0, .25], [0, .25, 0]], np.float32)
    for _ in range(iters):
        sm = cv2.filter2D(val, -1, ker, borderType=cv2.BORDER_REPLICATE)
        val[todo] = sm[todo]
    return cv2.resize(val, (IW, IH), interpolation=cv2.INTER_CUBIC)


def fill_hole(img, hole):
    """paint the field into `hole` (bool) of img (BGR uint8) -> float32 BGR.
    The field strip (PLATE_X0..X1, same rows: same perspective) is tiled across the picture (seams
    cross-faded),
    then matched to the ground round the hole Poisson-style: plus a smooth membrane of the colour
    difference measured on the ring of open ground round the hole (leaves, ink and the mid-ground
    stuff above the bale left out of the measurement, so none of their colour bleeds in)."""
    f = img.astype(np.float32)
    wdt, ov = PLATE_X1 - PLATE_X0, 90
    xs = np.arange(IW)
    rel = xs - PLATE_X0
    u = rel - np.floor_divide(rel, wdt - ov) * (wdt - ov)      # 0 .. wdt-ov: repeats, no mirror
    t = np.clip(u / ov, 0, 1)[None, :, None]                   # cross-fade from the last tile's tail
    a_x = PLATE_X0 + np.minimum(u + wdt - ov, wdt - 1)
    plate = f[:, PLATE_X0 + u] * t + f[:, a_x] * (1 - t)
    # what may be measured: open ground near the hole, in both the picture and the plate
    def plain(x):
        u8 = np.clip(x, 0, 255).astype(np.uint8)
        g = cv2.cvtColor(u8, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(u8, cv2.COLOR_BGR2HSV)
        bad = (g < 75) | (hsv[..., 1] > 175) | (hsv[..., 0] > 18) | (hsv[..., 2] > 200)
        return ~ndi.binary_dilation(bad, iterations=3)
    ring = ndi.binary_dilation(hole, iterations=28) & ~hole
    known = ring & plain(f) & plain(plate)
    d = membrane(cv2.GaussianBlur(f, (0, 0), 3) - cv2.GaussianBlur(plate, (0, 0), 3), known, hole)
    out = f.copy()
    out[hole] = (plate + d)[hole]
    return out


def main():
    prev = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    img = cv2.cvtColor(np.asarray(Image.open(SRC).convert("RGB")), cv2.COLOR_RGB2BGR)
    assert img.shape[:2] == (IH, IW)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    fgs = {k: cut(img, gray, p, FORCE.get(k)) for k, p in POLY.items()}
    fg = np.zeros((IH, IW), bool)
    for m in fgs.values():
        fg |= m
    alpha = np.clip(cv2.GaussianBlur(fg.astype(np.float32), (0, 0), .6) * 1.15 - .075, 0, 1)
    Image.fromarray((alpha * 255 + .5).astype(np.uint8)).save(ALPHA)

    # back plate
    hole = ndi.binary_dilation(fg, iterations=4)
    back = np.clip(fill_hole(img, hole) + .5, 0, 255).astype(np.uint8)
    back_rgb = Image.fromarray(cv2.cvtColor(back, cv2.COLOR_BGR2RGB))
    best = None
    for q in (82, 84, 86, 88, 90, 92):
        tmp = BACK.with_suffix(".tmp.webp")
        back_rgb.save(tmp, "WEBP", quality=q, method=6)
        sz = tmp.stat().st_size
        if best is None or abs(sz - TARGET_BYTES) < abs(best[1] - TARGET_BYTES):
            best = (q, sz)
        tmp.unlink()
    back_rgb.save(BACK, "WEBP", quality=best[0], method=6)
    print(f"back plate -> {BACK} (q{best[0]}, {BACK.stat().st_size} bytes)")

    # cut-outs, tinted as #bgwall tints the painting
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
    ta = (TA0 + (TA1 - TA0) * (np.arange(IH, dtype=np.float32) + .5) / IH)[:, None, None]
    tinted = rgb * (1 - ta) + TINT * ta
    meta = {"image": [IW, IH], "tint": {"rgb": TINT.tolist(), "a0": TA0, "a1": TA1}, "layers": {}}
    for name, m in fgs.items():
        a = alpha * ndi.binary_dilation(m, iterations=3)
        ys, xs = np.nonzero(a > 0)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        rgba = np.dstack([tinted[y0:y1, x0:x1], a[y0:y1, x0:x1, None] * 255])
        rgba[..., :3] *= (rgba[..., 3:] > 0)        # nothing hidden under A=0 (smaller file)
        out = FG_DIR / f"fg_{name}.webp"
        Image.fromarray(np.clip(rgba + .5, 0, 255).astype(np.uint8), "RGBA").save(
            out, "WEBP", quality=90, alpha_quality=100, method=6)
        meta["layers"][name] = {"file": f"assets/bg/fg_{name}.webp", "box": [x0, y0, x1, y1],
                                "pct": {"left": round(100 * x0 / IW, 4), "top": round(100 * y0 / IH, 4),
                                        "width": round(100 * (x1 - x0) / IW, 4), "height": round(100 * (y1 - y0) / IH, 4)}}
        print(f"{name}: box {x0},{y0}-{x1},{y1} -> {out} ({out.stat().st_size} bytes)")
    META.write_text(json.dumps(meta, indent=1))

    if prev:
        prev.mkdir(parents=True, exist_ok=True)
        ov = img.copy()
        ov[fg] = (ov[fg] * .5 + np.array([255, 0, 255]) * .5).astype(np.uint8)
        for p in POLY.values():
            cv2.polylines(ov, [np.array(p, np.int32)], True, (0, 255, 0), 2)
        for fs in FORCE.values():
            for sp in fs:
                cv2.polylines(ov, [np.array(sp["poly"], np.int32)], True, (255, 255, 0), 2)
        cv2.imwrite(str(prev / "fg_overlay.png"), cv2.resize(ov[1300:, :], (1920, 430)))
        cv2.imwrite(str(prev / "fg_overlay_l.png"), ov[1700:IH, 0:1150])
        cv2.imwrite(str(prev / "fg_overlay_r.png"), cv2.resize(ov[1450:IH, 1700:IW], (1070, 355)))
        cv2.imwrite(str(prev / "back_bottom.png"), cv2.resize(back[1300:, :], (1920, 430)))
        cv2.imwrite(str(prev / "back_l.png"), back[1700:IH, 0:1150])
        cv2.imwrite(str(prev / "back_r.png"), cv2.resize(back[1450:IH, 1700:IW], (1070, 355)))
        # recomposite (no tint) vs the source: must match except where the alpha is soft
        comp = back.astype(np.float32) * (1 - alpha[..., None]) + img.astype(np.float32) * alpha[..., None]
        err = np.abs(comp - img).max(2)
        print(f"recomposite vs source: mean {err.mean():.3f}, p99.9 {np.percentile(err, 99.9):.1f}")


if __name__ == "__main__":
    main()
