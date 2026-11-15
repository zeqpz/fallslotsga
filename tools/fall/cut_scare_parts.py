"""Raw part takes (tools/fall/gen_scare_parts.py -> art/fall-src/scare_parts/raw) -> clean cut-out parts for the rig.

For every raw take:
  clean     the model's "solid" areas come back at alpha ~250/255 and its edges carry a faint haze: the alpha is
            re-levelled (below 30% -> 0, above 80% -> fully solid: SOLID parts, 1-2 px of antialias left), specks and
            haze away from the shapes go, and the edge pixels take the colour of the ink just inside them (no light or
            dark fringe when a part is scaled, turned or mipmapped)
  split     a take that holds several pieces (boots, cuffs, hands, hair, ropes, mouths) is cut into them
  place     a piece drawn "in place" on its region close-up is registered on the old figure (masked colour match
            over a small range of scales and shifts), the others are placed by hand (PLACE below)
-> art/fall-src/scare_parts/parts/<name>.png at S (2) px per art px, cropped, and parts.json: for each part its
   art-px origin (x, y of the picture's top-left corner in the figure's 1024 x 1536 frame) and size.
Then the made parts (make_*): the crow's head cut off its body at the neck, the hat's tip cut at its bend, the post
and its foot from the round-2 pole layer, and the eyes / pupils / lids / brows, which are DRAWN here (solid, crisp,
exactly registered on each other - the old whole-head face swaps had see-through eyes and a shadow behind the head).

  .venv/Scripts/python.exe -I tools/fall/cut_scare_parts.py [cut] [made] [sheet]"""
import json, math, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage, signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_scare_parts as G

ROOT = G.ROOT
RAW, REF = G.RAW, G.REF
OUT = os.path.join(G.OUT, "parts")
CHECK = os.path.join(G.OUT, "check")
S = 2.0                                  # master px per art px
W_ART, H_ART = 1024, 1536

# raw take -> the pieces in it (a take with one entry is used whole; else it is split into its connected pieces,
# ordered left to right). The model draws each part as big as its canvas, not at its old size, so every piece is
# placed by hand on the old figure: (anchor fx, fy in the piece's own box, the art x, y that anchor goes to, art px
# per raw px, turn deg counter-clockwise [, opts: mirror=True, rows=(f0, f1) keep that span of the piece's height]).
TAKES = {
    "head_base": [("head", (.545, .545, 492, 374, .335, 6))],
    "hat": [("hat", (0, 0, 232, 112, .444, 0))],
    "hair": [("hair_l", (.95, .1, 345, 285, .19, 0)), ("hair_ll", (.5, .05, 385, 335, .19, 0)),
             ("hat_tuft", (.3, .9, 470, 180, .22, 0)), ("hair_r", (.05, .1, 560, 240, .2, 0, dict(mirror=True)))],
    "collar": [("collar", (.47, .15, 535, 462, .258, 0))],
    "torso": [("torso", (0, 0, 383, 466, .394, 0))],
    "hips": [("hips", (.5, 0, 545, 726, .285, 0))],
    "leg_l": [("leg_l", (.72, .02, 480, 745, .315, -10, dict(rows=(.1, 1))))],
    "leg_r": [("leg_r", (0, 1, 543, 1134, .315, 0, dict(rows=(.1, 1))))],
    "cuffs": [("cuff_l", (.5, .1, 425, 1114, .27, 0)), ("cuff_r", (.5, .1, 612, 1114, .27, 0))],
    "boots": [("boot_l", (0, 1, 368, 1358, .34, 0)), ("boot_r", (0, 1, 520, 1358, .34, 0))],
    "sleeve_l": [("sleeve_l", (.03, .35, 240, 497, .27, 0))],
    "sleeve_r": [("sleeve_r", (.97, .4, 826, 497, .27, 0))],
    "hand_l": [("hand_l", (.97, .12, 142, 460, .175, 18)), ("frill_l", (.9, .3, 245, 490, .19, 0))],
    "hand_r": [("frill_r", (.3, .05, 838, 470, .2, 0)), ("hand_r", (.08, .1, 898, 462, .2, 0))],
    "ropes": [("coil_l", (.5, .5, 152, 467, .325, 0)), ("coil_r", (.5, .5, 884, 458, .325, -8)),
              ("jug_rope", (.5, 0, 152, 470, .36, 0, dict(rows=(0, .40)))),
              ("belt_a", (.5, .1, 612, 772, .27, 0)), ("belt_b", (.5, 0, 624, 776, .25, -8, dict(rows=(.3, 1))))],
    "jug": [("jug", (0, 0, 38, 564, .222, 0))],
    "crow": [("crow", (0, 0, 757, 189, .2625, 0))],
    "crow_wing": [("wing", (.93, .78, 858, 292, .15, 0))],
    # the mouths: every one centred on MOUTH (the head's own tilt turned into them: the takes are drawn level)
    "mouths_a": [("mouth_grin", (.5, .5, 505, 412, .26, 4)), ("mouth_cheer", (.5, .4, 505, 412, .25, 18)),
                 ("mouth_smile", (.5, .5, 505, 412, .26, 18)), ("mouth_o", (.5, .5, 505, 412, .19, 18))],
    "mouths_b": [("mouth_smug", (.5, .5, 505, 412, .26, 16)), ("mouth_hiccup", (.5, .5, 505, 412, .21, 18)),
                 ("mouth_sad", (.5, .5, 505, 412, .25, 18)), ("mouth_drool", (.5, .4, 505, 412, .25, 18))],
}
GROW = {"hair": 6}                       # how far apart two blobs must be to count as two pieces (raw px / 2)


def load(path):
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255


def save(img, path):
    Image.fromarray((img * 255 + .5).clip(0, 255).astype(np.uint8)).save(path)


def clean(im, lo=.30, hi=.80, speck=.004):
    """Re-level the alpha, drop specks and haze, and give the edge pixels the colour just inside them."""
    a = np.clip((im[..., 3] - lo) / (hi - lo), 0, 1)
    solid = a >= .5
    lab, n = ndimage.label(ndimage.binary_dilation(solid, iterations=3))
    if n > 1:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= max(60, sizes.max() * speck))[0])
        solid &= keep
    a = np.where(ndimage.binary_dilation(solid, iterations=2), a, 0)
    core = ndimage.binary_erosion(a >= .999, iterations=1)
    idx = ndimage.distance_transform_edt(~core, return_distances=False, return_indices=True)
    rgb = im[..., :3][idx[0], idx[1]]
    rgb = np.where(core[..., None], im[..., :3], rgb)
    return np.concatenate([rgb, a[..., None]], -1).astype(np.float32)


def pieces(im, grow=18, least=.02):
    """The separate pieces of a take: [(x0, y0, x1, y1, mask)] biggest first dropped below `least` of the biggest."""
    solid = im[..., 3] > .5
    lab, n = ndimage.label(ndimage.binary_dilation(solid, iterations=grow))
    out = []
    sizes = ndimage.sum(solid, lab, range(1, n + 1))
    for i in range(n):
        if sizes[i] < least * sizes.max():
            continue
        m = (lab == i + 1) & (im[..., 3] > 0)
        ys, xs = np.nonzero(m)
        out.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, m))
    return out


def resize(im, w, h):
    """Premultiplied Lanczos."""
    pm = im.copy()
    pm[..., :3] *= pm[..., 3:]
    chans = [np.asarray(Image.fromarray(pm[..., c]).resize((w, h), Image.LANCZOS)) for c in range(4)]
    pm = np.stack(chans, -1)
    a = np.clip(pm[..., 3:], 0, 1)
    rgb = np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0)
    return np.concatenate([np.clip(rgb, 0, 1), a], -1).astype(np.float32)


def rotate(im, deg):
    """Turn a piece counter-clockwise (on screen) about its centre, canvas grown to fit. Premultiplied bicubic."""
    if not deg:
        return im
    pm = im.copy()
    pm[..., :3] *= pm[..., 3:]
    chans = [np.asarray(Image.fromarray(pm[..., c]).rotate(deg, Image.BICUBIC, expand=True)) for c in range(4)]
    pm = np.stack(chans, -1)
    a = np.clip(pm[..., 3:], 0, 1)
    rgb = np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0)
    return np.concatenate([np.clip(rgb, 0, 1), a], -1).astype(np.float32)


_REFIMG = None


def ref_art():
    global _REFIMG
    if _REFIMG is None:
        _REFIMG = np.asarray(Image.open(os.path.join(REF, "full.png")).convert("RGB")).astype(np.float32) / 255
    return _REFIMG


def register(piece, x0, y0, k, reach=46, scales=(.90, .93, .96, .98, 1.0, 1.02, 1.04, 1.07, 1.10)):
    """piece: RGBA at raw px, its top-left at art (x0, y0) when 1 art px = k raw px. Find the scale (about its
    centre) and shift that lay it best on the old figure: masked colour difference, at art resolution.
    -> (art px per raw px, art x, art y of its top-left, score)."""
    R = ref_art()
    h, w = piece.shape[:2]
    cx, cy = x0 + w / k / 2, y0 + h / k / 2
    best = None
    for sc in scales:
        pw, ph = max(4, round(w / k * sc)), max(4, round(h / k * sc))
        P = resize(piece, pw, ph)
        a = (P[..., 3] > .5).astype(np.float32)
        if a.sum() < 20:
            continue
        px0, py0 = int(round(cx - pw / 2)), int(round(cy - ph / 2))
        wx0, wy0 = px0 - reach, py0 - reach
        win = np.ones((ph + 2 * reach, pw + 2 * reach, 3), np.float32)        # white outside the figure
        sx0, sy0 = max(0, wx0), max(0, wy0)
        sx1, sy1 = min(W_ART, wx0 + win.shape[1]), min(H_ART, wy0 + win.shape[0])
        win[sy0 - wy0:sy1 - wy0, sx0 - wx0:sx1 - wx0] = R[sy0:sy1, sx0:sx1]
        ssd = np.zeros((2 * reach + 1, 2 * reach + 1), np.float64)
        af = a[::-1, ::-1]
        for c in range(3):
            ssd += signal.fftconvolve(win[..., c] ** 2, af, mode="valid")
            ssd -= 2 * signal.fftconvolve(win[..., c], (a * P[..., c])[::-1, ::-1], mode="valid")
            ssd += (a * P[..., c] ** 2).sum()
        ssd /= a.sum()
        dy, dx = np.unravel_index(np.argmin(ssd), ssd.shape)
        v = float(ssd[dy, dx])
        if best is None or v < best[3]:
            best = (sc / k, wx0 + dx, wy0 + dy, v, pw, ph)
    return best


def to_master(piece, art_per_raw, turn=0.0):
    """A raw piece -> the master picture (S px per art px), turned."""
    h, w = piece.shape[:2]
    mw, mh = max(2, round(w * art_per_raw * S)), max(2, round(h * art_per_raw * S))
    return rotate(resize(piece, mw, mh), turn)


def crop(m, pad=2):
    ys, xs = np.nonzero(m[..., 3] > .004)
    x0, y0, x1, y1 = max(0, xs.min() - pad), max(0, ys.min() - pad), min(m.shape[1], xs.max() + 1 + pad), min(m.shape[0], ys.max() + 1 + pad)
    return m[y0:y1, x0:x1], x0, y0


def write(meta, name, m, ax, ay):
    """m: master picture whose top-left is at art (ax, ay)."""
    m, cx, cy = crop(m)
    ax, ay = ax + cx / S, ay + cy / S
    save(m, os.path.join(OUT, name + ".png"))
    meta[name] = {"x": round(ax, 2), "y": round(ay, 2), "w": m.shape[1], "h": m.shape[0], "s": S}
    return m


def read_part(meta, name):
    return load(os.path.join(OUT, name + ".png")), meta[name]["x"], meta[name]["y"]


def cut(only=None):
    os.makedirs(OUT, exist_ok=True)
    mp = os.path.join(OUT, "parts.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    for take, how in TAKES.items():
        if only and take not in only:
            continue
        im = clean(load(os.path.join(RAW, take + ".png")))
        if len(how) == 1:
            ps = pieces(im, grow=40, least=.0)
            x0, y0 = min(p[0] for p in ps), min(p[1] for p in ps)
            x1, y1 = max(p[2] for p in ps), max(p[3] for p in ps)
            jobs = [(how[0][0], how[0][1], im[y0:y1, x0:x1])]
        else:
            ps = pieces(im, grow=GROW.get(take, 18))
            ps.sort(key=lambda p: p[0])
            assert len(ps) == len(how), (take, len(ps), "pieces, want", len(how), [p[:4] for p in ps])
            jobs = []
            for (name, place), (x0, y0, x1, y1, m) in zip(how, ps):
                pc = im[y0:y1, x0:x1].copy()
                pc[..., 3] *= m[y0:y1, x0:x1]
                jobs.append((name, place, pc))
        for name, place, pc in jobs:
            fx, fy, tx, ty, apr, turn = place[:6]
            opts = place[6] if len(place) > 6 else {}
            if "rows" in opts:
                r0, r1 = opts["rows"]
                pc = pc[int(pc.shape[0] * r0):int(pc.shape[0] * r1)]
            if opts.get("mirror"):
                pc = pc[:, ::-1]
            m = to_master(pc, apr, turn)
            # where the anchor lands in the turned picture
            w0, h0 = pc.shape[1] * apr * S, pc.shape[0] * apr * S
            t = math.radians(turn)
            vx, vy = (fx - .5) * w0, (fy - .5) * h0
            rx, ry = vx * math.cos(t) + vy * math.sin(t), -vx * math.sin(t) + vy * math.cos(t)
            ax, ay = tx - (m.shape[1] / 2 + rx) / S, ty - (m.shape[0] / 2 + ry) / S
            write(meta, name, m, ax, ay)
            print(f"{name:10s} at ({meta[name]['x']:.0f}, {meta[name]['y']:.0f})  {meta[name]['w'] / S:.0f} x {meta[name]['h'] / S:.0f} art px")
    json.dump(meta, open(mp, "w"), indent=1)
    return meta


def compose(meta, names, scale=1.0, bg=None, ghost=None):
    """The named parts drawn in order at their art places -> RGBA float (W_ART x H_ART at `scale`)."""
    W, H = round(W_ART * scale), round(H_ART * scale)
    out = np.zeros((H, W, 4), np.float32)
    if bg is not None:
        out[..., :3] = np.array(bg) / 255
        out[..., 3] = 1
    if ghost is not None:
        g = np.asarray(Image.open(os.path.join(REF, "full.png")).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
        out[..., :3] = out[..., :3] * (1 - ghost) + g * ghost
    for n in names:
        im, ax, ay = read_part(meta, n)
        w, h = max(1, round(im.shape[1] / S * scale)), max(1, round(im.shape[0] / S * scale))
        p = resize(im, w, h)
        x, y = int(round(ax * scale)), int(round(ay * scale))
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        src = p[y0 - y:y1 - y, x0 - x:x1 - x]
        dst = out[y0:y1, x0:x1]
        a = src[..., 3:]
        na = a + dst[..., 3:] * (1 - a)
        dst[..., :3] = np.where(na > 1e-4, (src[..., :3] * a + dst[..., :3] * dst[..., 3:] * (1 - a)) / np.maximum(na, 1e-4), 0)
        dst[..., 3:] = na
    return out


if __name__ == "__main__":
    args = sys.argv[1:] or ["cut"]
    if args[0] == "cut":
        cut(args[1].split(",") if len(args) > 1 else None)
    elif args[0] == "ghost":                     # the parts over the faded old figure: ghost out.png name,name [x0,y0,x1,y1] [zoom]
        meta = json.load(open(os.path.join(OUT, "parts.json")))
        z = float(args[4]) if len(args) > 4 else 1.0
        img = compose(meta, args[2].split(","), z, bg=(255, 255, 255), ghost=float(os.environ.get("GHOST", ".45")))
        if len(args) > 3 and args[3] != "all":
            x0, y0, x1, y1 = [round(float(v) * z) for v in args[3].split(",")]
            img = img[y0:y1, x0:x1]
        save(img[..., :3], args[1])
