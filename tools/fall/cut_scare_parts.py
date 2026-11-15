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
    "head_base": [("head", (.545, .545, 492, 374, .335, 6, dict(bulge=(490, 372, 36, 1.2))))],   # (a bigger red nose)
    "hat": [("hat", (0, 0, 232, 112, .444, 0))],
    "hair": [("hair_l", (.95, .1, 345, 285, .19, 0)), ("hair_ll", (.5, .05, 385, 335, .19, 0)),
             ("hat_tuft", (.3, .9, 470, 180, .22, 0)), ("hair_r", (.05, .1, 588, 306, .2, 0, dict(mirror=True)))],
    "collar": [("collar", (.47, .15, 535, 462, .258, 0))],
    "torso": [("torso", (0, 0, 383, 466, .394, 0))],
    # (2026-11-15: ONE pair of trousers - made() cuts it into hips + two legs with round overlapping tops - and plain
    # boots, no straw; the straw cuffs are gone)
    "trousers": [("trousers", (.5, 0, 548, 722, .34, 0))],
    "boots_plain": [("boot_l", (.5, 0, 468, 1100, .34, 0)), ("boot_r", (.5, 0, 626, 1100, .34, 0))],
    "sleeve_l": [("sleeve_l", (.03, .35, 172, 492, .23, 0))],
    "sleeve_r": [("sleeve_r", (.97, .4, 868, 490, .19, 0))],
    "hand_l": [("hand_l", (.97, .12, 142, 460, .175, 18)), ("frill_l", (.9, .3, 196, 486, .19, 0))],
    "hand_r": [("frill_r", (.3, .05, 852, 468, .2, 0)), ("hand_r", (.08, .1, 898, 462, .2, 0))],
    "ropes": [("coil_l", (.5, .5, 152, 467, .325, 0)), ("coil_r", (.5, .5, 884, 458, .325, -8)),
              ("jug_rope", (.5, 0, 152, 470, .36, 0, dict(rows=(0, .40)))),
              ("belt_a", (.5, .1, 577, 748, .27, 0)), ("belt_b", (.5, 0, 588, 752, .25, -8, dict(rows=(.3, 1))))],
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
    tmp = path + ".tmp.png"              # (written aside and swapped in: a viewer holding the old file open blocks a rewrite)
    Image.fromarray((img * 255 + .5).clip(0, 255).astype(np.uint8)).save(tmp)
    os.replace(tmp, path)


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


def write(meta, name, m, ax, ay, s=S):
    """m: master picture (s px per art px) whose top-left is at art (ax, ay)."""
    m, cx, cy = crop(m)
    ax, ay = ax + cx / s, ay + cy / s
    save(m, os.path.join(OUT, name + ".png"))
    meta[name] = {"x": round(ax, 3), "y": round(ay, 3), "w": m.shape[1], "h": m.shape[0], "s": s}
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
            if "bulge" in opts:                  # magnify a round patch of the piece (art x, y, radius, by how much)
                bx, by, br, bk = opts["bulge"]
                ys, xs = np.mgrid[0:m.shape[0], 0:m.shape[1]].astype(np.float32)
                dx, dy = xs - (bx - ax) * S, ys - (by - ay) * S
                r = np.hypot(dx, dy) / (br * S)
                t = np.clip((1.45 - r) / .45, 0, 1)
                k = 1 + (bk - 1) * t * t * (3 - 2 * t)
                m = np.stack([ndimage.map_coordinates(m[..., c], [(by - ay) * S + dy / k, (bx - ax) * S + dx / k], order=1)
                              for c in range(4)], -1).astype(np.float32)
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
        ps = meta[n].get("s", S)
        w, h = max(1, round(im.shape[1] / ps * scale)), max(1, round(im.shape[0] / ps * scale))
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


# ---------------------------------------------------------------- the made parts
# the hat: the lower ink line of its red band (art px) - above it is the crown + band (drawn in FRONT of the head),
# the whole hat goes BEHIND the head (its brim would cover the face); the tip is cut at its bend, a round joint
# (2026-11-15, owner: "the head is overlapping their hat" - the front is now the crown, the band AND the brim's upper
# face: everything above the line where the brim's dark underside begins; only that underside stays behind the head)
HAT_BAND = [(200, 440), (332, 440), (346, 392), (362, 352), (382, 322), (402, 304), (450, 289), (500, 277), (560, 269),
            (620, 264), (700, 252), (740, 240)]
HAT_TIP = (301, 163, 31)                 # the bend: x, y, r (the tip is everything left of x, plus the disc)
CROW_NECK = (876, 283, 34)               # the crow's neck joint: x, y, r
CROW_HEAD = (902, 222)                   # ... and a point in the middle of its head (the cut is square to that line)
POST_X = (458, 586)                      # the post's columns, the crossbar's rows (the round-2 pole layer)
BAR_Y = (398, 514)
INK = (38, 20, 10)
WHITE = (252, 246, 232)
# the eyes, in art px on the new head: centre x, y, radii, tilt deg (counter-clockwise)
EYES = {"l": (441, 342, 28, 30, 14), "r": (512, 312, 30, 31, 14)}
UPPER = (.18, .32, .46, .60, .74, .88, 1.0)      # how far down the upper lid's edge is, as a share of the eye's height
LOWER = (.14, .26, .38)                          # ... and the lower lid's, up from the bottom
PUPIL_R = 4.9
LID_SLANT = {"l": -.24, "r": .24}        # the upper lids droop toward the outer corners (a drunk's heavy eyes)
PUPIL_AT = {"l": (8, 9), "r": (-3, 13)}        # where each pupil rests, from its eye's centre (a drunk's cross-eyed look)
BROWS = {"l": (433, 299, 50, 14), "r": (511, 270, 54, 14)}     # centre x, y, length, tilt


def _aa(d):
    """Signed distance in master px (positive inside) -> coverage."""
    return np.clip(d + .5, 0, 1)


def _mul(im, k):
    out = im.copy()
    out[..., 3] *= k
    return out


def make_hat(meta):
    hat, hx, hy = read_part(meta, "hat")
    H, W = hat.shape[:2]
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    ax, ay = hx + (xs + .5) / S, hy + (ys + .5) / S
    band = np.interp(ax, [p[0] for p in HAT_BAND], [p[1] for p in HAT_BAND])
    above = _aa((band - ay) * S)
    tx, ty, tr = HAT_TIP
    disc = _aa((tr - np.hypot(ax - tx, ay - ty)) * S)
    tipside = _aa((tx - ax) * S) * (ay < ty + 100)        # (not the brim's left end, far below it)
    write(meta, "hat_tip", _mul(hat, np.maximum(tipside, disc)), hx, hy)
    write(meta, "hat_back", _mul(hat, np.maximum(1 - tipside, disc)), hx, hy)
    write(meta, "hat_front", _mul(hat, above * np.maximum(1 - tipside, disc)), hx, hy)


def make_crow(meta):
    crow, cx, cy = read_part(meta, "crow")
    H, W = crow.shape[:2]
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    ax, ay = cx + (xs + .5) / S, cy + (ys + .5) / S
    jx, jy, jr = CROW_NECK
    nx, ny = CROW_HEAD[0] - jx, CROW_HEAD[1] - jy
    nl = math.hypot(nx, ny)
    side = _aa(((ax - jx) * nx + (ay - jy) * ny) / nl * S)
    disc = _aa((jr - np.hypot(ax - jx, ay - jy)) * S)
    write(meta, "crow_head", _mul(crow, np.maximum(side, disc)), cx, cy)
    write(meta, "crow_body", _mul(crow, np.maximum(1 - side, disc)), cx, cy)


def make_pole(meta):
    import pack_char_rig as PK
    src = PK.rgba(os.path.join(PK.LAY, "pole.png"))
    keep = dict(PK.GROUND)
    try:
        PK.GROUND = dict(keep, occl=keep["occl"][:4] + (0.0,), pool=keep["pool"][:4] + (0.0,), strokes=[])
        post = PK.ground_pole(src)                       # the post alone, going into the ground
        PK.GROUND = keep
        ground = PK.ground_pole(np.zeros_like(src))      # its contact shadow and the dirt strokes alone
    finally:
        PK.GROUND = keep
    bar = np.zeros_like(post)
    bar[BAR_Y[0]:BAR_Y[1]] = post[BAR_Y[0]:BAR_Y[1]]
    pst = np.zeros_like(post)
    pst[:, POST_X[0]:POST_X[1]] = post[:, POST_X[0]:POST_X[1]]
    rest = post.copy()
    rest[BAR_Y[0]:BAR_Y[1]] = 0
    rest[:, POST_X[0]:POST_X[1]] = 0
    assert rest[..., 3].max() < .05, ("the pole layer has something outside the post and the crossbar", rest[..., 3].max())
    write(meta, "post", pst, 0, 0, 1.0)
    write(meta, "crossbar", bar, 0, 0, 1.0)
    write(meta, "ground", ground, 0, 0, 1.0)


def _canvas(x0, y0, x1, y1, q=4):
    """A drawing grid over art (x0, y0)..(x1, y1) at q x the master's size -> (art x, art y arrays, px per art px)."""
    k = S * q
    w, h = int(math.ceil((x1 - x0) * S)) * q, int(math.ceil((y1 - y0) * S)) * q
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return x0 + (xs + .5) / k, y0 + (ys + .5) / k, k


def _down(layers, q=4):
    """[(rgb, coverage)] drawn back to front at q x -> the master picture (straight alpha)."""
    h, w = layers[0][1].shape
    pm = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    for rgb, cov in layers:
        c = np.array(rgb, np.float32) / 255
        pm = pm * (1 - cov[..., None]) + c * cov[..., None]
        a = a * (1 - cov) + cov
    pm = pm.reshape(h // q, q, w // q, q, 3).mean(axis=(1, 3))
    a = a.reshape(h // q, q, w // q, q).mean(axis=(1, 3))
    rgb = np.where(a[..., None] > 1e-4, pm / np.maximum(a[..., None], 1e-4), 0)
    return np.concatenate([rgb, a[..., None]], -1).astype(np.float32)


def make_face(meta):
    """The eyes (white + outline), pupils, lids and brows, drawn. Every picture of one eye is cut from the same
    grid, so the lids register on the white exactly; the lids are clipped just inside the outline."""
    head, hx, hy = read_part(meta, "head")
    for side, (cx, cy, rx, ry, tilt) in EYES.items():
        pad = 6
        R = max(rx, ry) + pad
        x0, y0 = cx - R, cy - R
        ax, ay, k = _canvas(x0, y0, cx + R, cy + R)
        t = math.radians(tilt)
        u = (ax - cx) * math.cos(t) - (ay - cy) * math.sin(t)          # the eye's own axes (u along its width)
        v = (ax - cx) * math.sin(t) + (ay - cy) * math.cos(t)
        e = np.hypot(u / rx, v / ry)
        grad = np.maximum(1e-3, np.hypot(u / rx ** 2, v / ry ** 2) / np.maximum(e, 1e-3))
        d_out = (1 - e) / grad                                          # art px inside the eye's edge
        ink_w = 3.4
        inner = np.clip((d_out - ink_w) * k + .5, 0, 1)                # the white inside the outline
        outer = np.clip(d_out * k + .5, 0, 1)
        # a few tired veins from the rim
        vein = np.zeros_like(e)
        rng = np.random.default_rng(3 if side == "l" else 4)
        for a0 in rng.uniform(0, 2 * math.pi, 5):
            L = rng.uniform(.28, .42)
            for s_ in np.linspace(0, 1, 40):
                rr = 1 - .1 - L * s_
                ang = a0 + .35 * s_ * s_
                px, py = rr * rx * math.cos(ang), rr * ry * math.sin(ang)
                vein = np.maximum(vein, np.clip((.75 * (1 - s_) + .25 - np.hypot(u - px, v - py)) * k + .5, 0, 1))
        white = _down([(INK, outer), (WHITE, inner), ((226, 150, 140), vein * inner * .8)])
        write(meta, "eye_" + side, white, x0, y0)
        # the lid's colour: the burlap round the eye, a little darker
        sx_, sy_ = int((cx - hx) * S), int((cy - hy) * S)
        skin = np.median(head[sy_ - 30:sy_ + 30, sx_ - 30:sx_ + 30, :3].reshape(-1, 3), axis=0) * 255
        lid = tuple(float(c) * .985 for c in skin)
        cover = np.clip((d_out + 2.2) / 2.0, 0, 1)                     # the whole eye and its ring, 2 px soft outside
        clip = np.clip((d_out - ink_w + .6) * k + .5, 0, 1)            # (a hair over the outline's inner edge)
        for i, f in enumerate(UPPER):
            full = f >= .999                                           # shut: the whole eye, a sleepy curve low on it
            fe, bow = (.80, .34) if full else (f, .22)
            edge = -ry + 2 * ry * fe - ry * bow * np.clip(u / rx, -1, 1) ** 2      # (its middle is its lowest point)
            edge = edge + LID_SLANT[side] * u * (0.0 if full else 1.0)
            fill = cover if full else np.clip((edge - v) * k + .5, 0, 1) * clip
            line = np.clip((ink_w / 2 - np.abs(v - edge)) * k + .5, 0, 1) * clip
            if full:                                                   # the lash curve stops short of the corners
                line = line * np.clip((rx * .86 - np.abs(u)) * k, 0, 1)
            write(meta, f"lid_u{i + 1}_{side}", _down([(lid, fill), (INK, line)]), x0, y0)
        for i, f in enumerate(LOWER):
            edge = ry - 2 * ry * f + ry * .2 * np.clip(u / rx, -1, 1) ** 2
            fill = np.clip((v - edge) * k + .5, 0, 1) * clip
            line = np.clip((ink_w / 2 - np.abs(v - edge)) * k + .5, 0, 1) * clip
            write(meta, f"lid_d{i + 1}_{side}", _down([(lid, fill), (INK, line)]), x0, y0)
        # the pupil
        pr = PUPIL_R
        cx, cy = cx + PUPIL_AT[side][0], cy + PUPIL_AT[side][1]
        ax, ay, k = _canvas(cx - pr - 2, cy - pr - 2, cx + pr + 2, cy + pr + 2)
        dd = np.hypot(ax - cx, ay - cy)
        pup = _down([((16, 10, 8), np.clip((pr - dd) * k + .5, 0, 1)),
                     ((255, 255, 255), np.clip((1.5 - np.hypot(ax - cx + 1.9, ay - cy + 2.0)) * k + .5, 0, 1))])
        write(meta, "pupil_" + side, pup, cx - pr - 2, cy - pr - 2)
    for side, (cx, cy, L, tilt) in BROWS.items():
        ax, ay, k = _canvas(cx - L / 2 - 8, cy - 18, cx + L / 2 + 8, cy + 18)
        t = math.radians(tilt)
        u = (ax - cx) * math.cos(t) - (ay - cy) * math.sin(t)
        v = (ax - cx) * math.sin(t) + (ay - cy) * math.cos(t)
        s_ = np.clip(u / (L / 2), -1, 1)
        arc = -7.0 * (1 - s_ * s_) + 3.5                               # an arch, its middle highest
        half = .9 + 2.2 * (1 - np.abs(s_) ** 1.6)                      # thick in the middle, tapered
        dist = np.hypot(np.maximum(np.abs(u) - L / 2, 0), v - arc)
        cov = np.clip((half - dist) * k + .5, 0, 1)
        write(meta, "brow_" + side, _down([(INK, cov)]), cx - L / 2 - 8, cy - 18)


DROOL = (464, 431)                       # the low corner of the smirk (mouth_smug), where the drool hangs
STITCHES = [(478, 430, 92), (493, 428, 102), (508, 420, 124), (520, 407, 146)]     # across the smirk: x, y, the tick's slant deg


def make_mouth(meta):
    """The drunk's resting mouth: the closed lopsided smirk, stitched, a drool drop hanging off its low corner."""
    m, mx, my = read_part(meta, "mouth_smug")
    x0, y0, x1, y1 = mx - 6, my - 4, mx + m.shape[1] / S + 4, my + m.shape[0] / S + 26
    ax, ay, k = _canvas(x0, y0, x1, y1)
    ink = np.zeros_like(ax)
    for sx_, sy_, ang in STITCHES:
        t = math.radians(ang)
        u = (ax - sx_) * math.cos(t) - (ay - sy_) * math.sin(t)
        v = (ax - sx_) * math.sin(t) + (ay - sy_) * math.cos(t)
        ink = np.maximum(ink, np.clip((1.3 - np.hypot(np.maximum(np.abs(u) - 5.5, 0), v)) * k + .5, 0, 1))
    dx, dy = DROOL
    # a strand, then a teardrop
    strand = np.clip((1.6 - np.hypot(ax - dx, np.maximum(np.abs(ay - dy - 6) - 6, 0))) * k + .5, 0, 1)
    cy = dy + 19
    w = np.where(ay < cy, 5.2 * np.clip((ay - (cy - 11)) / 11, 0, 1) ** .8, 5.2)
    dist = np.where(ay < cy, w - np.abs(ax - dx), 5.2 - np.hypot(ax - dx, ay - cy))
    drop_o = np.clip((dist + 1.5) * k + .5, 0, 1) * (ay > cy - 11.5)
    drop_i = np.clip(dist * k + .5, 0, 1) * (ay > cy - 10)
    shine = np.clip((1.4 - np.hypot(ax - dx + 1.6, ay - cy + 1.2)) * k + .5, 0, 1)
    over = _down([(INK, ink), ((150, 200, 232), strand), (INK, drop_o), ((158, 208, 238), drop_i), ((240, 250, 255), shine)])
    out = np.zeros_like(over)
    px, py = int(round((mx - x0) * S)), int(round((my - y0) * S))
    out[py:py + m.shape[0], px:px + m.shape[1]] = m
    a = over[..., 3:]
    na = a + out[..., 3:] * (1 - a)
    out[..., :3] = np.where(na > 1e-4, (over[..., :3] * a + out[..., :3] * out[..., 3:] * (1 - a)) / np.maximum(na, 1e-4), 0)
    out[..., 3:] = na
    write(meta, "mouth_drunk", out, x0, y0)


HIP_UP, HIP_FEATHER = 14, 7              # the hip pivots sit this far above the crotch; the hips' lower edge fades over this


def make_trousers(meta):
    """The one pair of trousers -> hips + leg_l + leg_r. Each leg keeps everything of its side below its hip pivot
    plus a round cap about the pivot (radius = half the leg's width); the hips keep everything above the crotch plus
    a slightly bigger disc about each pivot, its lower edge faded - so a swinging leg shows a soft fold, never a gap.
    The pivots and hems are written to joints.json for the rig."""
    tr, tx, ty = read_part(meta, "trousers")
    a = tr[..., 3] > .5
    H, W = a.shape
    cols = np.arange(W)
    mid = W // 2
    crotch = None
    for y in range(H - 1, 0, -1):                                    # up from the hems: the last row with a gap in the middle
        row = a[y]
        gap = ~row & (np.abs(cols - mid) < W * .2)
        if row.any() and gap.any() and row[:mid].any() and row[mid:].any():
            crotch = y
        elif crotch is not None and y < crotch - 4:
            break
    gx = np.nonzero(~a[crotch + 6] & (np.abs(cols - mid) < W * .2))[0]
    cx = (gx.min() + gx.max()) / 2
    yy = min(H - 1, crotch + int(40 * S))
    spans = {}
    for side, sl in (("l", slice(0, int(cx))), ("r", slice(int(cx), W))):
        xs = np.nonzero(a[yy, sl])[0] + (sl.start or 0)
        spans[side] = (xs.min(), xs.max())
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    joints = {}
    hips_k = _aa((crotch - 3 * S) - ys)                               # above the crotch
    for side in "lr":
        x0, x1 = spans[side]
        px, py = (x0 + x1) / 2, crotch - HIP_UP * S
        rad = (x1 - x0) / 2 - 1.5 * S
        dist = np.hypot(xs - px, ys - py)
        own = _aa((cx - xs) if side == "l" else (xs - cx))
        legk = np.maximum(_aa(ys - py) * own, _aa(rad - dist))
        leg = _mul(tr, legk)
        write(meta, "leg_" + side, leg, tx, ty)
        hips_k = np.maximum(hips_k, np.clip((rad + 3 * S - dist) / (HIP_FEATHER * S), 0, 1))
        bot = np.nonzero(a[:, int(x0):int(x1)].any(1))[0].max()
        joints["leg_" + side] = [round(tx + px / S, 1), round(ty + py / S, 1)]
        joints["hem_" + side] = [round(tx + px / S, 1), round(ty + bot / S, 1)]
        joints["leg_r_" + side] = round(rad / S, 1)
    write(meta, "hips", _mul(tr, hips_k), tx, ty)
    json.dump(joints, open(os.path.join(OUT, "joints.json"), "w"), indent=1)
    print("trousers: crotch at art y", round(ty + crotch / S), joints)


def made():
    mp = os.path.join(OUT, "parts.json")
    meta = json.load(open(mp))
    make_hat(meta)
    make_crow(meta)
    make_pole(meta)
    make_face(meta)
    make_mouth(meta)
    make_trousers(meta)
    json.dump(meta, open(mp, "w"), indent=1)
    print("made:", ", ".join(k for k in meta if k.split("_")[0] in ("hat", "crow", "post", "crossbar", "ground", "eye",
                                                                     "pupil", "lid", "brow")))
    return meta


if __name__ == "__main__":
    args = sys.argv[1:] or ["cut"]
    if args[0] == "cut":
        cut(args[1].split(",") if len(args) > 1 else None)
    elif args[0] == "made":
        made()
    elif args[0] == "ghost":                     # the parts over the faded old figure: ghost out.png name,name [x0,y0,x1,y1] [zoom]
        meta = json.load(open(os.path.join(OUT, "parts.json")))
        z = float(args[4]) if len(args) > 4 else 1.0
        img = compose(meta, args[2].split(","), z, bg=(255, 255, 255), ghost=float(os.environ.get("GHOST", ".45")))
        if len(args) > 3 and args[3] != "all":
            x0, y0, x1, y1 = [round(float(v) * z) for v in args[3].split(",")]
            img = img[y0:y1, x0:x1]
        save(img[..., :3], args[1])
