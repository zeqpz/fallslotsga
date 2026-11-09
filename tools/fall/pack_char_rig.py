"""Pack the scarecrow's live rig for the game: frontend/assets/chars/scarecrow_rig/.

Reads what tools/fall/blender/export_char_rig.py wrote (art/blender/chars/scarecrow/rig/: export.json - every clip's
bone matrices, faces and effect sprites; weights.npz - the skin on the GRID lattice) and the source layers
(art/fall-src/scare at their full 1024 x 1536, ~1.6x what a 1440p screen shows of him - the old frames were 0.6x),
and writes:
  atlas.webp   one 2048 x 2048 page: the body (neutral face), the pole + its contact shadow, each other face as a patch,
               the crow, the effect sprites, the boots' shadow - all at 1:1 art px (the game mipmaps it)
  rig.bin      the meshes (body / pole: art px positions, atlas uvs, triangles, bone indices + weights; the face
               patch: triangles over the body's own vertices + one uv set per face) and every clip's bone
               matrices (int16: a b c d x 8192, tx ty x 8), faces (uint8)
  rig.json     sizes, bones, offsets into rig.bin, clip frames / loop / cues, the sprites per frame, the atlas rects
Fixes done to the layers on the way (they are not edited in place):
  - the crow was cut as a rectangle (scarecrow_layers.py: right of x 760, above y 418): its tail tip and claws
    stayed on the body (dark specks on the arm whenever it hops away) and the top of the wrist rope went with it.
    Re-cut here: crow-dark pixels round the perch go to the crow, the rope back to the body, holes filled.
  - the legs did not reach the boots (bare post between the straw cuffs and the boots): scarecrow.join_legs()
    lengthens the trouser legs and lifts the boots under the straw cuffs, on every body layer.
  - the grass tuft with grey stones under the post looked pasted on the painted (bare dirt) field: ground_pole()
    clears it, carries the post's wood down into the ground and lays a warm contact shadow round its foot that
    fades out well above the canvas's bottom (the ground line, art y 1500).
usage: .venv/Scripts/python.exe -I tools/fall/pack_char_rig.py [--preview out.png]"""
import io, json, os, struct, sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender"))
import scarecrow as SC                 # numpy only outside Blender: join_legs (the legs reaching the boots)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAY = os.path.join(ROOT, "art", "fall-src", "scare")
FXD = os.path.join(ROOT, "art", "fall-src", "fx")
SRC = os.path.join(ROOT, "art", "blender", "chars", "scarecrow", "rig")
FIXED = os.path.join(ROOT, "art", "blender", "chars", "scarecrow", "layers")
OUT = os.path.join(ROOT, "frontend", "assets", "chars", "scarecrow_rig")
PAGE = 2048
PAD = 4
FX_PX = 128                        # effect sprites' size in the atlas (drawn at 80-110 art px)
# the boots' shadows on the field (drawn live under each boot, index.html), art px: each a soft ellipse on the
# ground under its boot's sole, fainter and wider the higher the boot hangs
SHADOW = dict(rx=78, ry=11, rgb=(52, 26, 10), a=.3, soles=[[452, 1352], [600, 1352]], bones=["boot_l", "boot_r"],
              ground=1458)
# the post's foot (ground_pole), art px: post columns, rows cleared / copied, where it goes into the ground, the
# occlusion and pool ellipses (cx, cy, rx, ry, alpha) and their colour
GROUND = dict(post=(464, 580), clear=1318, copy=1342, rep=160, fade=22, y=1458,
              occl=(522, 1459, 108, 17, .9), pool=(525, 1461, 285, 31, .5), rgb=(58, 30, 12),
              ink=(62, 34, 14), strokes=[[(418, 1468), (446, 1456), (470, 1458)], [(576, 1457), (604, 1456), (628, 1469)],
                                        [(352, 1478), (372, 1472), (396, 1476)], [(662, 1474), (686, 1471), (708, 1478)]])
GROUND_Y = 1500


def rgba(path):
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255


def fill_holes(img, hole):
    """Diffuse colour into `hole` from its neighbours (premultiplied), alpha included."""
    out = img.copy()
    known = ~hole
    pm = out[..., :3] * out[..., 3:]
    for _ in range(40):
        if not hole.any():
            break
        k = known.astype(np.float32)
        num = ndimage.uniform_filter(pm * k[..., None], (3, 3, 1))
        a = ndimage.uniform_filter(out[..., 3] * k, 3)
        den = ndimage.uniform_filter(k, 3)
        grow = hole & (den > 0.15)
        pm[grow] = num[grow] / den[grow][:, None]
        out[..., 3][grow] = a[grow] / den[grow]
        known |= grow
        hole &= ~grow
    out[..., :3] = np.where(out[..., 3:] > 1e-3, pm / np.maximum(out[..., 3:], 1e-3), 0)
    return out


def recut_crow(bodies, crow):
    """-> (bodies, crow) with the crow cut by its colour round the perch instead of a rectangle."""
    H, W = crow.shape[:2]
    zone = np.zeros((H, W), bool)
    zone[150:448, 735:1000] = True
    body = bodies["neutral"]
    both = crow.copy()
    take_body = (zone & (crow[..., 3] < .05) & (body[..., 3] > .05))
    both[take_body] = body[take_body]
    r, g, b, a = both[..., 0], both[..., 1], both[..., 2], both[..., 3]
    lum = .3 * r + .59 * g + .11 * b
    brown = (r - b > .06) & (r > .12)                      # rope, its brown outline, straw, cloth: never crow
    dark = zone & (a > .05) & (lum < .45) & ~brown         # the crow is purple-black, its claws blue-grey
    lab, n = ndimage.label(dark)
    seed = lab[300, 870]
    birdm = (lab == seed) if seed else dark
    birdm = ndimage.binary_fill_holes(birdm)
    # its soft edge: the faint px round it that are not rope
    soft = (ndimage.binary_dilation(birdm, iterations=2) & (a > .01) & ~brown) | birdm
    new_crow = np.zeros_like(crow)
    new_crow[soft] = both[soft]
    out = {}
    for f, im in bodies.items():
        im = im.copy()
        give_back = (crow[..., 3] > .05) & ~soft            # the old crow layer's rope etc. -> the body
        im[give_back] = crow[give_back]
        hole = soft & (im[..., 3] > .05)
        im[hole] = 0
        # the rope under the claws: fill from the rope round it (only inside the rope's column)
        rope_hole = np.zeros_like(hole)
        rope_hole[380:452, 850:915] = True
        rope_hole &= soft
        im = fill_holes(im, rope_hole & ndimage.binary_dilation(im[..., 3] > .5, iterations=6))
        # the rope ends where it wraps over the crossbar's top edge (y ~410), cleanly; specks the claws left go
        ys = np.arange(H)[:, None] * np.ones((1, W))
        cut = (ys < 411) & zone & (np.arange(W)[None, :] > 845) & (np.arange(W)[None, :] < 925)
        im[cut] = 0
        im[(ys < 432) & zone & (np.arange(W)[None, :] >= 899) & (np.arange(W)[None, :] < 930)] = 0   # a claw's shadow
        lab, n = ndimage.label(im[..., 3] > .02)
        if n:
            sizes = ndimage.sum(np.ones((H, W)), lab, range(1, n + 1))
            small = np.isin(lab, np.nonzero(sizes < 400)[0] + 1) & zone
            im[small] = 0
        out[f] = im
    return out, new_crow


def ground_pole(pole):
    """The post's foot, sat IN the painted field (round 2, 2026-11-08). The plate's grass tuft with its grey stones
    and leaves read as a patch pasted on the farm painting (the field round him is bare ochre dirt): it is cleared
    away, the post's wood carried on down past the old tuft (copied from higher up the post, cross-faded in) to
    where it goes into the ground (GROUND["y"], a slightly ragged soft edge, the wood darkening into the earth), and
    a warm contact shadow is laid round the foot - a tight dark occlusion at the post and a wide soft pool under him
    that fades to nothing well above the canvas's bottom (the ground line, art y 1500), so no edge ever shows."""
    H, W = pole.shape[:2]
    G = GROUND
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    out = pole.copy()
    x0, x1 = G["post"]                                   # the post's columns (its outline and soft edge included)
    out[G["clear"]:, :x0] = 0
    out[G["clear"]:, x1:] = 0
    # the wood below the tuft line: the post's own wood from G["rep"] px higher, cross-faded over G["fade"] rows
    r0, rep, fd = G["copy"], G["rep"], G["fade"]
    blend_from = r0 - fd
    seg = out[blend_from:H, x0:x1]
    srcb = pole[blend_from - rep:H - rep, x0:x1]
    kk = np.clip((np.arange(blend_from, H) - blend_from) / fd, 0, 1)[:, None, None]
    out[blend_from:H, x0:x1] = seg * (1 - kk) + srcb * kk
    # into the ground: the wood darkens over the last px and its alpha ends on a ragged soft line
    rng = np.random.default_rng(7)
    rag = np.interp(np.arange(W), np.arange(0, W + 24, 24), rng.uniform(-4, 4, len(range(0, W + 24, 24))))
    gy = G["y"] + rag[None, :]
    dark = np.clip(1 - (gy - ys) / 46, 0, 1) ** 1.5
    out[..., :3] *= (1 - .55 * dark)[..., None]
    out[..., :3] = out[..., :3] * (1 - .25 * dark[..., None]) + np.array([.2, .1, .04]) * .25 * dark[..., None]
    out[..., 3] *= np.clip((gy - ys) / 10 + .5, 0, 1)
    # the contact shadow, under the post: warm dark brown (the painting's own ground shadows), soft falloffs
    def ell(cx, cy, rx, ry, p):
        e = np.hypot((xs - cx) / rx, (ys - cy) / ry)
        v = np.clip(1 - e, 0, 1)
        return v * v * (3 - 2 * v) if p is None else v ** p
    sa = np.maximum(G["occl"][4] * ell(*G["occl"][:4], 1.4), G["pool"][4] * ell(*G["pool"][:4], None))
    sa[ys >= GROUND_Y - 4] = 0
    sh = np.zeros_like(out)
    sh[..., :3] = np.array(G["rgb"]) / 255
    sh[..., 3] = sa
    a = out[..., 3:] + sh[..., 3:] * (1 - out[..., 3:])     # the post over its shadow
    col = (out[..., :3] * out[..., 3:] + sh[..., :3] * sh[..., 3:] * (1 - out[..., 3:])) / np.maximum(a, 1e-4)
    out = np.concatenate([np.where(a > 1e-4, col, 0), a], -1)
    # the earth's lip round the post: short dark strokes like the painting's own ground lines (drawn 4x, smoothed)
    from PIL import ImageDraw
    q = 4
    ink = Image.new("L", (W * q, H * q), 0)
    dr = ImageDraw.Draw(ink)
    for p0, p1, p2 in G["strokes"]:                       # a brush stroke: a curve, thick in the middle, tapered
        for t in np.linspace(0, 1, 160):
            x = (1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * p1[1] + t * t * p2[1]
            r = (.5 + 1.6 * np.sin(np.pi * t) ** .7) * q
            dr.ellipse([x * q - r, y * q - r, x * q + r, y * q + r], fill=255)
    ia = np.asarray(ink.resize((W, H), Image.LANCZOS)).astype(np.float32)[..., None] / 255 * .85
    a2 = ia + out[..., 3:] * (1 - ia)
    col = (np.array(G["ink"]) / 255 * ia + out[..., :3] * out[..., 3:] * (1 - ia)) / np.maximum(a2, 1e-4)
    out = np.concatenate([np.where(a2 > 1e-4, col, 0), a2], -1)
    out[ys >= GROUND_Y - 1] = 0
    return out.astype(np.float32)


def shadow_sprite(w=128, h=32):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((xs + .5 - w / 2) / (w / 2), (ys + .5 - h / 2) / (h / 2))
    a = np.clip(1 - d, 0, 1) ** 1.6
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = np.array(SHADOW["rgb"]) / 255
    img[..., 3] = a                      # full strength: the game sets each one's alpha (SHADOW["a"], the lift)
    return img


class Shelf:
    def __init__(self, size):
        self.size, self.x, self.y, self.h = size, 0, 0, 0

    def place(self, w, h):
        w, h = w + 2 * PAD, h + 2 * PAD
        if self.x + w > self.size:
            self.x, self.y, self.h = 0, self.y + self.h, 0
        if self.y + h > self.size:
            raise RuntimeError("atlas full")
        at = (self.x + PAD, self.y + PAD)
        self.x += w
        self.h = max(self.h, h)
        return at


def bbox(a, thr=.004):
    ys, xs = np.nonzero(a > thr)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def main():
    ex = json.load(open(os.path.join(SRC, "export.json")))
    wz = np.load(os.path.join(SRC, "weights.npz"))
    g, LW, LH = [int(v) for v in wz["lattice"]]
    faces = ex["faces"]
    # the body without its boots (the skinned mesh) and the boots alone (two rigid sprites on boot_l / boot_r,
    # drawn under the body so the straw cuffs hang over them); the repaired layers get both, composited
    bodies, boots = {}, None
    for f in faces:
        _, bodies[f], bt = SC.join_legs(rgba(os.path.join(LAY, f"body_{f}.png")), parts=True)
        boots = bt if boots is None else boots
    bodies, crow = recut_crow(bodies, rgba(os.path.join(LAY, "crow.png")))
    pole = ground_pole(rgba(os.path.join(LAY, "pole.png")))
    os.makedirs(FIXED, exist_ok=True)
    for f, im in bodies.items():
        a = im[..., 3:]
        pm = im[..., :3] * a + boots[..., :3] * boots[..., 3:] * (1 - a)
        aa = a + boots[..., 3:] * (1 - a)
        full = np.concatenate([np.where(aa > 1e-4, pm / np.maximum(aa, 1e-4), 0), aa], -1)
        Image.fromarray((full * 255 + .5).astype(np.uint8)).save(os.path.join(FIXED, f"body_{f}.png"))
    Image.fromarray((crow * 255 + .5).astype(np.uint8)).save(os.path.join(FIXED, "crow.png"))
    Image.fromarray((pole * 255 + .5).astype(np.uint8)).save(os.path.join(FIXED, "pole.png"))
    neutral = bodies["neutral"]
    H, W = neutral.shape[:2]

    # ---- meshes on the lattice: cells with anything in them
    def cells_of(alpha):
        a = alpha[:H // g * g, :W // g * g].reshape(H // g, g, W // g, g).max(axis=(1, 3)) > .004
        return ndimage.binary_dilation(a, iterations=0) if False else a
    body_alpha = np.max([im[..., 3] for im in bodies.values()], axis=0)
    bc = cells_of(body_alpha)
    pc = cells_of(pole[..., 3])

    def mesh(cells):
        used = {}
        verts, tris = [], []
        for cy, cx in zip(*np.nonzero(cells)):
            q = []
            for dy, dx in ((0, 0), (0, 1), (1, 1), (1, 0)):
                key = (cy + dy) * LW + (cx + dx)
                if key not in used:
                    used[key] = len(verts)
                    verts.append(key)
                q.append(used[key])
            tris += [q[0], q[1], q[2], q[0], q[2], q[3]]
        verts = np.array(verts)
        pos = np.stack([(verts % LW) * g, (verts // LW) * g], 1).astype(np.float32)
        return verts, pos, np.array(tris, np.uint32), used
    b_lat, b_pos, b_tri, b_used = mesh(bc)
    p_lat, p_pos, p_tri, _ = mesh(pc)

    # face patch: the cells that any face changes, over the body's own vertices
    diff = np.zeros((H, W), bool)
    for f, im in bodies.items():
        if f != "neutral":
            diff |= np.abs(im - neutral).max(-1) > 1 / 255
    diff = ndimage.binary_dilation(diff, iterations=3) & (body_alpha > .004)
    fx0, fy0, fx1, fy1 = bbox(diff.astype(np.float32))
    fx0, fy0 = fx0 // g * g, fy0 // g * g
    fx1, fy1 = -(-fx1 // g) * g, -(-fy1 // g) * g
    fcells = np.zeros_like(bc)
    fcells[fy0 // g:fy1 // g, fx0 // g:fx1 // g] = True
    fcells &= bc
    f_tri = []
    for cy, cx in zip(*np.nonzero(fcells)):
        q = [b_used[(cy + dy) * LW + (cx + dx)] for dy, dx in ((0, 0), (0, 1), (1, 1), (1, 0))]
        f_tri += [q[0], q[1], q[2], q[0], q[2], q[3]]
    f_tri = np.array(f_tri, np.uint32)
    f_verts = np.unique(f_tri)

    # ---- atlas
    atlas = np.zeros((PAGE, PAGE, 4), np.float32)
    shelf = Shelf(PAGE)
    rects = {}

    def put(name, img, box):
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        ax, ay = shelf.place(w, h)
        atlas[ay:ay + h, ax:ax + w] = img[y0:y1, x0:x1]
        rects[name] = [ax, ay, w, h, x0, y0]          # atlas x, y, w, h; art x0, y0 it came from
        return ax - x0, ay - y0                         # art px -> atlas px offset
    bb = (int(b_pos[:, 0].min()), int(b_pos[:, 1].min()), int(b_pos[:, 0].max()), int(b_pos[:, 1].max()))
    off_b = put("body", neutral, bb)
    pb = (int(p_pos[:, 0].min()), int(p_pos[:, 1].min()), int(p_pos[:, 0].max()), min(H, int(p_pos[:, 1].max())))
    off_p = put("pole", pole, pb)
    face_off = {}
    for f in faces:
        if f == "neutral":
            continue
        im = bodies[f].copy()
        m = diff[..., None]
        im = np.where(m, im, 0)
        face_off[f] = put("face_" + f, im, (fx0, fy0, fx1, fy1))
    cb = bbox(crow[..., 3])
    cb = (max(0, cb[0] - 2), max(0, cb[1] - 2), min(W, cb[2] + 2), min(H, cb[3] + 2))
    put("crow", crow, cb)
    for side in ("l", "r"):
        im = boots.copy()
        if side == "l":
            im[:, SC.BOOT_SPLIT:] = 0
        else:
            im[:, :SC.BOOT_SPLIT] = 0
        bb_ = bbox(im[..., 3])
        put("boot_" + side, im, (max(0, bb_[0] - 2), max(0, bb_[1] - 2), min(W, bb_[2] + 2), min(H, bb_[3] + 2)))
    for kind in ex["fx"]:
        im = Image.open(os.path.join(FXD, ex["fx"][kind]["file"])).convert("RGBA")
        im = im.convert("RGBa").resize((FX_PX, FX_PX), Image.LANCZOS).convert("RGBA")
        put("fx_" + kind, np.asarray(im).astype(np.float32) / 255, (0, 0, FX_PX, FX_PX))
    sh = shadow_sprite()
    put("shadow", sh, (0, 0, sh.shape[1], sh.shape[0]))
    used_h = max(r[1] + r[3] for r in rects.values()) + PAD
    page_h = 1 << int(np.ceil(np.log2(used_h)))
    page_h = max(page_h, 1024)
    os.makedirs(OUT, exist_ok=True)
    # straight alpha out (the browser premultiplies on upload); colour bled into see-through px so mips stay clean
    a = atlas[..., 3:]
    col = atlas[..., :3]
    pm = col * a
    blur_pm = ndimage.uniform_filter(pm, (5, 5, 1))
    blur_a = ndimage.uniform_filter(a[..., 0], 5)[..., None]
    bleed = np.where(blur_a > 1e-4, blur_pm / np.maximum(blur_a, 1e-4), 0)
    col = np.where(a > .002, col, bleed)
    page = np.concatenate([col, a], -1)[:page_h]
    im = Image.fromarray((page * 255 + .5).clip(0, 255).astype(np.uint8))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=92, method=6, alpha_quality=100)
    open(os.path.join(OUT, "atlas.webp"), "wb").write(buf.getvalue())
    print("atlas", im.size, len(buf.getvalue()), "bytes")

    # ---- binary
    blob = bytearray()
    offs = {}

    def add(name, arr):
        arr = np.ascontiguousarray(arr)
        while len(blob) % 4:
            blob.append(0)
        offs[name] = [len(blob), arr.dtype.str.lstrip("<|"), list(arr.shape)]
        blob.extend(arr.tobytes())
    uvb = (b_pos + np.array(off_b)) / np.array([PAGE, page_h])
    add("body_pos", b_pos.astype(np.float32))
    add("body_uv", uvb.astype(np.float32))
    add("body_tri", b_tri.astype(np.uint16 if len(b_pos) < 65536 else np.uint32))
    bi = wz["body_idx"][b_lat]
    bw = wz["body_w"][b_lat]
    bw8 = np.round(bw * 255).astype(np.int32)
    bw8[:, 0] += 255 - bw8.sum(1)                       # the weights sum to exactly 255
    add("body_bone", bi.astype(np.uint8))
    add("body_w", bw8.clip(0, 255).astype(np.uint8))
    add("face_tri", f_tri.astype(np.uint16))
    add("face_verts", f_verts.astype(np.uint16))
    for f, o in face_off.items():
        add("face_uv_" + f, ((b_pos[f_verts] + np.array(o)) / np.array([PAGE, page_h])).astype(np.float32))
    add("pole_pos", p_pos.astype(np.float32))
    add("pole_uv", ((p_pos + np.array(off_p)) / np.array([PAGE, page_h])).astype(np.float32))
    add("pole_tri", p_tri.astype(np.uint16))
    pw = wz["pole_w"][p_lat]
    pole_bone = np.array([ex["bones"].index("pole"), ex["bones"].index("ground")], np.uint8)
    add("pole_w", np.round(pw[:, 0] * 255).astype(np.uint8))     # weight of `pole`; the rest is `ground`

    # clips
    rest_pts = b_pos[::7]
    clips = {}
    nb = len(ex["bones"])
    for c, d in ex["clips"].items():
        M = np.array(d["mats"], np.float64)                          # frames, bones, 6
        assert np.abs(M[..., :4]).max() < 3.9, (c, np.abs(M[..., :4]).max())
        assert np.abs(M[..., 4:]).max() < 4000
        q = np.empty(M.shape, np.int16)
        q[..., :4] = np.round(M[..., :4] * 8192)
        q[..., 4:] = np.round(M[..., 4:] * 8)
        add("clip_" + c, q)
        add("faces_" + c, np.array(d["faces"], np.uint8))
        # cues: frames where every body vertex is within a couple of px of the rest pose
        bones_v = bi[::7]
        wv = bw[::7]
        far = []
        for k in range(len(M)):
            pos = np.zeros_like(rest_pts, dtype=np.float64)
            for j in range(bones_v.shape[1]):
                m = M[k, bones_v[:, j]]
                pos[:, 0] += wv[:, j] * (m[:, 0] * rest_pts[:, 0] + m[:, 2] * rest_pts[:, 1] + m[:, 4])
                pos[:, 1] += wv[:, j] * (m[:, 1] * rest_pts[:, 0] + m[:, 3] * rest_pts[:, 1] + m[:, 5])
            far.append(float(np.abs(pos - rest_pts).max()))
        cues = [k for k, v in enumerate(far) if v < 3.0]
        # the sprites: per frame [kind index, a b c d tx ty (unit square -> art px), alpha]
        kinds = list(ex["fx"])
        spr = [[[kinds.index(s[0])] + [round(v, 2) for v in s[1]] + [s[2]] for s in fr] for fr in d["sprites"]]
        clips[c] = {"frames": d["frames"], "loop": d["loop"], "cues": cues, "spr": spr,
                    "far": [round(v, 1) for v in far]}
        print(c, d["frames"], "cues", cues[:8], "..." if len(cues) > 8 else "", "max", round(max(far), 1))
    open(os.path.join(OUT, "rig.bin"), "wb").write(bytes(blob))
    man = {
        "fps": ex["fps"], "art": ex["art"], "ground": [ex["ground"][0], GROUND_Y], "rest_height": GROUND_Y - ex["top"],
        "page": [PAGE, page_h], "bones": ex["bones"], "faces": faces, "fx": list(ex["fx"]), "rects": rects,
        "boots": [["boot_l", "boot_l"], ["boot_r", "boot_r"]],   # [atlas rect, bone]: rigid boot pictures
        "pole_bone": pole_bone.tolist(), "bin": offs, "bytes": len(blob),
        "shadow": SHADOW, "counts": {"body_verts": len(b_pos), "body_tris": len(b_tri) // 3,
                                     "face_verts": len(f_verts), "pole_verts": len(p_pos)},
        "clips": {c: {k: v for k, v in d.items() if k != "far"} for c, d in clips.items()},
    }
    json.dump(man, open(os.path.join(OUT, "rig.json"), "w"), separators=(",", ":"))
    print("rig.bin", len(blob), "bytes; rig.json", os.path.getsize(os.path.join(OUT, "rig.json")), "bytes;",
          man["counts"])


if __name__ == "__main__":
    main()
