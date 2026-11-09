"""Masks + sprites for the living background (frontend/bgfx.js).

Run:  .venv\\Scripts\\python.exe -I tools/fall/bg/make_bg_masks.py [preview_dir]

Reads frontend/assets/bonus_wall.webp (3840x2160) and writes
  frontend/assets/bg/bg_mask.webp  960x540 RGB (no alpha: a browser may premultiply an image's
      alpha on decode and lose the data under A=0), lossless
      R  wind weight: 0 at trunks/ground, up to 1 at the tips of the two big canopies,
         up to ~.3 on the tops of the mid-ground trees / corn
      G  water (lake): ripple + glints live only here
      B  sun: disc + corona in the sky; on the water, the sun's reflection streak (glints)
      (which trees are "big" - slow, wide sway - bgfx.js knows from position: the top corners)
  frontend/assets/bg/bg_fx.webp    512x128 RGBA atlas: leaf_red, leaf_orange, leaf_gold (from
      assets/fx, centred in 128 cells) + a soft smoke puff painted in the wisps' grey
With a preview_dir it also writes overlays of each channel on the painting for review.
Everything here is in image pixels of the 3840x2160 painting; bgfx.js uses the same numbers.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "frontend/assets/bonus_wall.webp"
OUT = ROOT / "frontend/assets/bg"
FX = ROOT / "frontend/assets/fx"
IW, IH = 3840, 2160
WK = 2                      # work at 1920x1080
MW, MH = 960, 540           # output mask size

# ---- hand-placed shapes (image px) ---------------------------------------------------------
# generous outlines of the two big canopies: they include sky gaps between leaves, never the barn
CANOPY_L = [(0, 0), (760, 0), (830, 60), (890, 170), (960, 220), (1000, 340), (930, 420), (840, 470),
            (830, 600), (700, 600), (640, 500), (540, 480), (440, 460), (320, 470), (230, 420),
            (150, 330), (60, 300), (0, 300)]
CANOPY_R = [(2600, 0), (3840, 0), (3840, 380), (3700, 380), (3600, 360), (3420, 330), (3330, 300),
            (3200, 360), (3060, 370), (2900, 380), (2780, 360), (2700, 300), (2620, 200)]
# trunks / main limbs (polylines): the sway weight is 0 on them and grows with distance
TRUNK_L = [[(70, 1000), (60, 600), (90, 300), (100, 0)], [(110, 420), (250, 340), (330, 330)],
           [(120, 260), (300, 200), (340, 205)]]
TRUNK_R = [[(3820, 950), (3760, 600), (3600, 420), (3420, 260), (3300, 120), (3200, 0)],
           [(3500, 300), (3560, 120), (3620, 0)], [(3700, 500), (3840, 420)]]
# where the small trees / corn may sway (y band of the mid-ground) ...
MID_REGION = [(0, 480), (1500, 560), (2200, 600), (3200, 420), (3840, 420), (3840, 1180),
              (2000, 1150), (1000, 1110), (0, 1060)]
# ... minus things that must stay put
MID_EXCLUDE = [
    [(3170, 360), (3840, 360), (3840, 1130), (3170, 1130)],                       # barn
    [(320, 1150), (330, 820), (730, 820), (730, 1150)],                           # hay bale + pumpkins left
    [(2200, 600), (3130, 600), (3130, 820), (2200, 820)],                         # village houses + fence
    [(2560, 380), (2720, 380), (2720, 620), (2560, 620)],                         # church tower
    [(2480, 1090), (3840, 1090), (3840, 1180), (2480, 1180)],                     # near fence rail
    [(0, 1000), (600, 1000), (600, 1180), (0, 1180)],                             # pumpkins left
]
# lake (main sheet below the far hills, and the strip under the sun)
WATER = [
    [(500, 842), (1085, 842), (1040, 870), (960, 925), (1100, 935), (1430, 945), (1450, 990),
     (1300, 1000), (1260, 1030), (1450, 1040), (1450, 1080), (900, 1080), (500, 1060)],
    [(500, 772), (1180, 772), (1180, 800), (900, 803), (700, 800), (500, 800)],
]
SUN = (681, 789, 96)        # centre x, y, radius (the horizon at y~775 hides its lower part)
HORIZON = 776


def poly_mask(polys, w, h, k):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon([(x / k, y / k) for x, y in p], fill=255)
    return np.asarray(im, np.float32) / 255.0


def line_mask(lines, w, h, k, width):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for ln in lines:
        d.line([(x / k, y / k) for x, y in ln], fill=255, width=max(1, int(width / k)))
    return np.asarray(im) > 0


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    prev = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    w, h = IW // WK, IH // WK
    img = Image.open(SRC).convert("RGB")
    rgb = np.asarray(img.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    lum = rgb @ np.array([.299, .587, .114], np.float32)
    mx, mn = rgb.max(2), rgb.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    # local texture (ink + leaf shading) separates foliage from the smooth sky
    m1 = ndi.uniform_filter(lum, 7)
    tex = np.sqrt(np.maximum(ndi.uniform_filter(lum * lum, 7) - m1 * m1, 0))
    leafy = tex > .035
    core = ndi.binary_closing(tex > .03, iterations=4)          # textured paint, not smooth sky/field
    leafy = ndi.binary_closing(leafy, iterations=6)
    leafy = ndi.binary_fill_holes(leafy)
    leafy = ndi.binary_dilation(leafy, iterations=10)          # ~20 image px past the outline: the
    leafy = leafy.astype(np.float32)                           # edge moves, it doesn't stretch

    # ---- big canopies
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    canL, canR = poly_mask([CANOPY_L], w, h, WK), poly_mask([CANOPY_R], w, h, WK)
    canopy = np.clip(canL + canR, 0, 1)
    trunk = line_mask(TRUNK_L + TRUNK_R, w, h, WK, 90)
    dist = ndi.distance_transform_edt(~trunk) * WK               # image px from a trunk/limb
    reach = np.where(canL > 0, smooth(dist, 30, 380), smooth(dist, 30, 420))
    big = ndi.gaussian_filter(canopy * leafy, 12) * ndi.gaussian_filter(canopy, 6)
    big = np.clip(big * 1.15, 0, 1) * reach

    # ---- mid-ground trees + corn: warm saturated foliage, weighted by height above its own base
    hue_ok = (r > g) & (g >= b * .8) & (r > .35)                 # red .. yellow
    fol = hue_ok & (sat > .38) & (lum > .28)
    region = poly_mask([MID_REGION], w, h, WK) * (1 - poly_mask(MID_EXCLUDE, w, h, WK))
    fol = fol & core & (region > .5) & (canopy < .5) & (poly_mask(WATER, w, h, WK) < .5)
    fol = ndi.binary_opening(fol, iterations=1)
    run = np.zeros((h, w), np.float32)
    for y in range(h - 2, -1, -1):                                # foliage pixels below each pixel
        run[y] = (run[y + 1] + 1) * fol[y]
    mid = np.clip(run / (90 / WK), 0, 1) * fol
    mid = ndi.gaussian_filter(mid, 3) * .32

    wind = np.maximum(big, mid)
    bigflag = np.clip(ndi.gaussian_filter(canopy, 20) * 1.3, 0, 1)

    # ---- water: lake shapes x water-ish colours (not the conifers in front)
    wpoly = poly_mask(WATER, w, h, WK)
    waterish = ((b > r * .85) & (lum > .3)) | ((r > .75) & (g > .45)) | ((sat < .4) & (lum > .38))
    water = (wpoly > .5) & waterish
    water = ndi.binary_closing(water, iterations=2)
    water = ndi.binary_erosion(water, iterations=1)
    water = ndi.gaussian_filter(water.astype(np.float32), 1.2)

    # ---- sun: disc + corona in the sky, the reflection streak on the water
    sx, sy, sr = SUN[0] / WK, SUN[1] / WK, SUN[2] / WK
    rr = np.hypot(xx - sx, yy - sy)
    disc = smooth(-(rr - sr), -2, 2)
    corona = np.exp(-np.maximum(rr - sr, 0) / (150 / WK)) * .75
    sun = np.maximum(disc, corona) * (yy < HORIZON / WK + 2)
    sun += np.exp(-np.maximum(rr - sr, 0) / (60 / WK)) * .35 * (yy >= HORIZON / WK + 2)  # glow on the hills
    streak = ((r > .8) & (g > .5) & (b < .45)).astype(np.float32) * (water > .3)
    streak = ndi.gaussian_filter(streak, 1.5) * np.exp(-np.abs(xx - sx) / (260 / WK))
    sun = np.where(water > .05, np.clip(streak * 1.4, 0, 1), np.clip(sun, 0, 1))

    def down(a):
        return np.asarray(Image.fromarray(np.clip(a * 255 + .5, 0, 255).astype(np.uint8)).resize((MW, MH), Image.BOX))

    out = np.dstack([down(wind), down(water), down(sun), down(bigflag)])
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ascontiguousarray(out[..., :3]), "RGB").save(OUT / "bg_mask.webp", lossless=True, quality=100, method=6, exact=True)

    # ---- fx atlas: three leaves + a smoke puff, 128 px cells
    atlas = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
    for i, n in enumerate(["leaf_red", "leaf_orange", "leaf_gold"]):
        lf = np.asarray(Image.open(FX / f"{n}.webp").convert("RGBA"), np.float32)
        c = lf[..., :3] / 255
        l, cs = c @ np.array([.299, .587, .114], np.float32), c.max(2) - c.min(2)
        # the sprites have a white sticker rim; the painting's leaves are outlined in dark ink
        rim = smooth(l, .38, .62) * (1 - smooth(cs, .22, .42))
        ink = np.array([.17, .09, .05], np.float32)
        c = c * (1 - rim[..., None]) + ink * rim[..., None]
        if n == "leaf_gold":                                       # lime-ish -> the painting's warm gold
            c = c * np.array([1.0, .74, .34], np.float32)
        lf = Image.fromarray(np.dstack([c * 255, lf[..., 3]]).clip(0, 255).astype(np.uint8), "RGBA")
        atlas.paste(lf, (i * 128 + (128 - lf.width) // 2, (128 - lf.height) // 2))
    rng = np.random.default_rng(7)
    py, px = np.mgrid[0:128, 0:128].astype(np.float32)
    a = np.zeros((128, 128), np.float32)
    for _ in range(9):                       # a soft lumpy cloud, not a perfect disc
        cx, cy = 64 + rng.normal(0, 13), 64 + rng.normal(0, 11)
        s = rng.uniform(13, 22)
        a += np.exp(-((px - cx) ** 2 + (py - cy) ** 2) / (2 * s * s)) * rng.uniform(.5, 1)
    noise = ndi.gaussian_filter(rng.random((128, 128)).astype(np.float32), 3)
    noise = (noise - noise.mean()) / noise.std()
    a = a / a.max() * (1 + .12 * noise)
    a *= smooth(np.hypot(px - 64, py - 64), 62, 40)              # never touch the cell edge
    a = np.clip(a, 0, 1) ** 1.3
    shade = np.clip(1 - (py - 40) / 160, .85, 1.0)               # lit a touch from above
    col = np.array([206, 174, 152], np.float32)
    puff = np.dstack([col[0] * shade, col[1] * shade, col[2] * shade, a * 255]).clip(0, 255).astype(np.uint8)
    atlas.paste(Image.fromarray(puff, "RGBA"), (384, 0))
    atlas.save(OUT / "bg_fx.webp", lossless=True, method=6, exact=True)

    print("bg_mask.webp", (OUT / "bg_mask.webp").stat().st_size, "bytes; bg_fx.webp", (OUT / "bg_fx.webp").stat().st_size)

    if prev:
        prev.mkdir(parents=True, exist_ok=True)
        base = np.asarray(img.resize((1280, 720), Image.LANCZOS), np.float32) / 255
        for i, (name, tint) in enumerate([("wind", (0, 1, 1)), ("water", (0, 1, 0)), ("sun", (1, 0, 1)), ("big", (0, 0, 1))]):
            m = np.asarray(Image.fromarray(out[..., i]).resize((1280, 720), Image.BILINEAR), np.float32)[..., None] / 255
            o = base * (1 - .7 * m) + np.array(tint, np.float32) * .7 * m
            Image.fromarray((o * 255).astype(np.uint8)).save(prev / f"mask_{name}.png")


if __name__ == "__main__":
    main()
