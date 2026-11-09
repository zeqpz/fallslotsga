"""Paint the airborne leaves out of the farm painting (owner, 2026-11-08: the painted leaves floating
in the sky look wrong next to bgfx.js's live falling leaves; leaves on the ground and the leaves of
the tree canopies stay).

Run:  <py with cv2> -I tools/fall/bg/clean_leaves.py [preview_dir]
      (cv2 lives in projects/slotsgame/.venv312; pillow + numpy + scipy too)

Reads  art/fall-src/bg/bonus_wall_orig.webp   (the untouched painting; made from
       frontend/assets/bonus_wall.webp on the first run)
Writes art/fall-src/bg/bonus_wall_noleaves.png (lossless; cut_foreground.py takes it from there)
With a preview_dir: before/after crops of every leaf (leaf_NN.png) and a contact sheet.

Every leaf below was found by a colour/ink-vs-median sweep of the sky (everything above the
horizon outside the two canopies) and then checked by eye on full-res crops; leaves that touch a
canopy or hang in front of it (e.g. the gold one at 3293,195 with its stem to the branch) are part
of the tree and stay. Each entry: a seed point on the leaf and a box that holds all of it.
The leaf's mask is the connected blob, at the seed, of pixels that differ from the local sky
(median-filtered crop) - so a leaf next to a bush never takes the bush with it - grown 5 px to
take its anti-aliased ink. The hole is filled from the sky around it: a smooth membrane
(harmonic fill, which keeps the gradient and doesn't streak), with Navier-Stokes inpainting
blended in near cloud edges so a cloud's rim carries on through.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
ORIG = ROOT / "art/fall-src/bg/bonus_wall_orig.webp"
LIVE = ROOT / "frontend/assets/bonus_wall.webp"
OUT = ROOT / "art/fall-src/bg/bonus_wall_noleaves.png"

# (seed x, seed y, box x0, y0, x1, y1) in image px of the 3840x2160 painting
LEAVES = [
    (1045, 105, 1000, 55, 1095, 160),    # red, upper sky right of the orange tree
    (1145, 365, 1095, 325, 1195, 405),   # red, below it
    (345, 515, 300, 470, 390, 565),      # red, under the orange tree
    (247, 565, 200, 518, 295, 615),      # brown-red, ~5 px off the red bush (the bush stays: KEEP_OUT)
    (495, 568, 430, 515, 560, 620),      # orange, under the orange tree
    (810, 60, 750, 0, 875, 135),         # orange, off the orange tree's top right (touches the top edge)
    (1558, 35, 1500, 0, 1610, 85),       # orange, top of the sky (touches the top edge)
    (2483, 475, 2430, 430, 2535, 520),   # gold, over the village
    (3085, 410, 3040, 365, 3130, 455),   # red, under the red tree
    (3257, 363, 3200, 320, 3315, 405),   # brown, under the red tree
]
PAD = 40
# non-sky that sits right against a leaf: never part of its mask, never a source for its fill
KEEP_OUT = {
    4: [(150, 578), (207, 579), (226, 589), (237, 597), (246, 609), (252, 640), (150, 640)],   # the red bush
}


def leaf_mask(crop, seed, keep=None):
    """the leaf's blob in a crop (H x W x 3 uint8): pixels unlike the local sky, connected to seed"""
    f = crop.astype(np.float32)
    med = np.stack([ndi.median_filter(f[..., c], size=41) for c in range(3)], -1)
    diff = np.abs(f - med).max(2)
    lum = f @ np.array([.114, .587, .299], np.float32)          # BGR
    m = (diff > 22) | (lum < 70)
    m = ndi.binary_closing(m, iterations=2)
    if keep is not None:
        m &= ~keep
    lab, _ = ndi.label(m)
    k = lab[seed[1], seed[0]]
    if k == 0:   # seed on a gap: nearest blob
        d, (iy, ix) = ndi.distance_transform_edt(lab == 0, return_indices=True)
        k = lab[iy[seed[1], seed[0]], ix[seed[1], seed[0]]]
    leaf = ndi.binary_fill_holes(ndi.binary_closing(lab == k, iterations=6, border_value=0) | (lab == k))
    # everything else that isn't sky (canopy leaves, the bush): kept out of the fill's boundary, so
    # its colour can't bleed into the patched sky
    if keep is not None:
        leaf &= ~keep
    grown = ndi.binary_dilation(leaf, iterations=5)
    if keep is not None:
        grown &= ~keep
    ring = ndi.binary_dilation(leaf, iterations=25) & ~grown
    sky_l = np.median(lum[ring & (lab == 0)]) if (ring & (lab == 0)).any() else 128
    dark = (lum < sky_l - 35) & ~grown            # a bush's body: the median sees it as "sky"
    if keep is not None:
        dark |= keep
    other = ndi.binary_dilation(((lab > 0) & (lab != k)) | dark, iterations=3) & ~grown
    return ndi.binary_dilation(leaf, iterations=5), other


def harmonic_fill(img, mask, other=None, iters=1500):
    """Laplace fill of the masked pixels from their border (per channel), multigrid-lite:
    start from a coarse fill, then relax at full res"""
    out = img.astype(np.float32).copy()
    if other is not None:   # solve over the non-sky too (free boundary), write only the hole
        mask = mask | other
    # coarse start: blurred known pixels normalised by blurred weights
    w = (~mask).astype(np.float32)
    for s in (24, 12, 6):
        num = cv2.GaussianBlur(out * w[..., None], (0, 0), s)
        den = cv2.GaussianBlur(w, (0, 0), s)[..., None]
        est = num / np.maximum(den, 1e-6)
        upd = mask & (den[..., 0] > (1e-5 if s == 24 else .05))   # finer scales only where they reach
        out[upd] = est[upd]
    k = np.array([[0, .25, 0], [.25, 0, .25], [0, .25, 0]], np.float32)
    for _ in range(iters):
        sm = cv2.filter2D(out, -1, k, borderType=cv2.BORDER_REPLICATE)
        out[mask] = sm[mask]
    return out


def main():
    prev = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not ORIG.exists():
        ORIG.parent.mkdir(parents=True, exist_ok=True)
        ORIG.write_bytes(LIVE.read_bytes())
        print("backed up", LIVE, "->", ORIG)
    src = cv2.cvtColor(np.asarray(Image.open(ORIG).convert("RGB")), cv2.COLOR_RGB2BGR)
    img = src.copy()
    H, W = img.shape[:2]
    sheet = []
    total = 0
    for i, (sx, sy, x0, y0, x1, y1) in enumerate(LEAVES):
        X0, Y0, X1, Y1 = max(0, x0 - PAD), max(0, y0 - PAD), min(W, x1 + PAD), min(H, y1 + PAD)
        crop = img[Y0:Y1, X0:X1].copy()
        keep = None
        if i + 1 in KEEP_OUT:
            from PIL import ImageDraw
            kim = Image.new("L", (X1 - X0, Y1 - Y0), 0)
            ImageDraw.Draw(kim).polygon([(x - X0, y - Y0) for x, y in KEEP_OUT[i + 1]], fill=255)
            keep = np.asarray(kim) > 0
        m, other = leaf_mask(crop, (sx - X0, sy - Y0), keep)
        box = np.zeros_like(m)
        box[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = True
        m &= box
        total += int(m.sum())
        smooth = harmonic_fill(crop, m, other)
        ns = cv2.inpaint(crop, m.astype(np.uint8) * 255, 6, cv2.INPAINT_NS).astype(np.float32)
        # where the sky round the hole has structure (a cloud rim), lean on NS; plain sky: harmonic
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
        edge = np.sqrt(gx * gx + gy * gy) * (~m)
        ring = ndi.binary_dilation(m, iterations=12) & ~m
        struct = np.clip((np.percentile(edge[ring], 90) - 40) / 120, 0, 1) if ring.any() else 0
        fill = smooth * (1 - struct) + ns * struct
        # a whisper of the painting's grain so the patch isn't glassier than the sky round it
        rng = np.random.default_rng(1000 + i)
        grain = cv2.GaussianBlur(rng.normal(0, 1.1, crop.shape[:2]).astype(np.float32), (0, 0), .8)[..., None]
        fill = fill + grain
        # feathered paste (the mask already reaches 5 px past the ink)
        a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
        a = np.maximum(a, m)[..., None]
        newc = np.clip(crop * (1 - a) + fill * a + .5, 0, 255).astype(np.uint8)
        img[Y0:Y1, X0:X1] = newc
        print(f"leaf {i + 1:2d} at ({sx},{sy}): {int(m.sum())} px, cloud-structure {float(struct):.2f}")
        if prev:
            prev.mkdir(parents=True, exist_ok=True)
            before, after = src[Y0:Y1, X0:X1], newc
            pair = np.concatenate([before, np.full((before.shape[0], 6, 3), 255, np.uint8), after], 1)
            pair = cv2.resize(pair, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(str(prev / f"leaf_{i + 1:02d}.png"), pair)
            sheet.append(pair)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(OUT, optimize=False, compress_level=3)
    print(f"{len(LEAVES)} airborne leaves removed ({total} px) -> {OUT}")
    if prev and sheet:
        wmax = max(s.shape[1] for s in sheet)
        rows = [np.pad(s, ((0, 8), (0, wmax - s.shape[1]), (0, 0))) for s in sheet]
        cv2.imwrite(str(prev / "leaves_sheet.png"), np.concatenate(rows, 0))


if __name__ == "__main__":
    main()
