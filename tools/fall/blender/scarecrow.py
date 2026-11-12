"""The drunk scarecrow, animated in Blender: a 2D cut-out skinned to a bone rig, his face swapped per frame. The game
draws him LIVE (2026-11-08): tools/fall/blender/export_char_rig.py reads every clip's bone matrices, the faces and the
effect sprites off this scene, tools/fall/pack_char_rig.py packs them with the source layers into
frontend/assets/chars/scarecrow_rig/, and index.html skins the mesh on the CPU each frame (Pixi Mesh). Renders from
here are previews / QA only (the old frame pipeline, tools/blender/pack_chars.py, still reads them for ?charframes).

Layers (art/fall-src/scare, made by tools/fall/scarecrow_layers.py): pole.png (the T-pole and its grass patch, behind)
and body_<face>.png (the scarecrow with no pole, one per face), crow.png (the crow on the crossbar).

The rig (art px, 1024 x 1536; 100 px = 1 Blender unit, the art centred on the origin):
  ground (the grass patch) > pole (the post: it creaks and wobbles from the ground) > everything tied to it: the
  wrists and sleeve ends, the crow's perch, the rope and jug, the straw hands, and the hips (his body
  hangs on the post) > chest > head > hat > hat_tip / brim_l / brim_r, head > hair_l / hair_ll / hair_r,
  chest > collar, hips > belt (the rope belt's dangling ends) / leg_l > cuff_l + boot_l / leg_r > cuff_r + boot_r
  (the boots ride the legs, under the straw cuffs - join_legs), pole > sleeve_l/_r
  (the sleeves' sag between the shoulder and the tied wrist).
Skin weights come from painted REGIONS (polygons in art px, each giving its pixels to one or more bones, later
regions over earlier ones), assigned on the opaque pixels only, grown out into the see-through gaps, then blurred a
little - so every part's outline moves with its part (the old rules skinned the hat's tip and right brim to the
SLEEVES (root/chest): the hat sheared and tore whenever the head moved - the hat bug, fixed 2026-11-08).

  blender.exe -b --factory-startup --python tools/fall/blender/scarecrow.py -- [build][,render][,frames] [clip,..] [frames]
-> art/blender/chars/scarecrow/scarecrow.blend, renders/<clip>/####.png (preview, RES), renders/meta.json
   'frames' renders only the frames listed (e.g. 0,20,40) of each clip into renders/<clip>/ (QA strips)."""
import json, math, os, random, sys

import numpy as np

try:
    import bpy
    import bmesh
    from mathutils import Matrix, Vector
except ImportError:                    # imported outside Blender (the weights / regions only)
    bpy = None

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LAY = os.path.join(ROOT, "art", "fall-src", "scare")
FX = os.path.join(ROOT, "art", "fall-src", "fx")
OUT = os.path.join(ROOT, "art", "blender", "chars", "scarecrow")
FPS = 30
W_PX, H_PX = 1024, 1536                    # the layers' size; 100 px = 1 unit, the art centred on the origin
RES = (800, 1080)                          # preview renders (the old frame pipeline's size)
ORTHO = 18.0                               # units across the frame's height (the art is 15.36 tall)
PX = RES[1] / ORTHO                        # render px per unit
GRID = 16                                  # the body mesh's cell, art px (the game's mesh uses the same lattice)
GROUND_Y, TOP_Y = 1500, 10                 # art px: the grass under the post, the post's top
FACES = json.load(open(os.path.join(LAY, "meta.json")))["faces"] if os.path.exists(os.path.join(LAY, "meta.json")) else []

CLIPS = {          # frames, loop  (CHAR_SFX in index.html is timed against these keys - see each clip's docstring)
    "idle": (300, True), "enter": (48, False), "exit": (30, False),
    "anticipate": (58, False),        # the bonus tease, with a held middle the game can repeat (HOLD)
    "anticipation": (82, False),      # the same played straight through with two holds (the old name, still called)
    "spin": (22, False), "spin2": (24, False),
    "win": (60, False), "big_win": (138, False), "lose": (76, False), "hiccup": (68, False), "peck": (84, False),
}
HOLD_AT = (16, 24)          # the tease's held middle: first frame, frames a cycle
HOLD = {"anticipate": (HOLD_AT[0], HOLD_AT[0] + HOLD_AT[1])}     # clip -> (a, b): frame b shows frame a's pose exactly
PECKS = (24, 36, 42)        # the crow's beak on his hat in "peck" (CHAR_SFX crowPeck)


def u(x, y):
    """Art px -> (x, z) units."""
    return ((x - W_PX / 2) / 100.0, (H_PX / 2 - y) / 100.0)


# bones: name -> (head px, tail px, parent). The head is the pivot.
BONES = {
    "ground": ((540, 1470), (540, 1380), None),
    "pole": ((540, 1460), (540, 1300), "ground"),
    "hips": ((540, 800), (535, 650), "pole"),
    "chest": ((535, 650), (525, 480), "hips"),
    "head": ((520, 470), (480, 250), "chest"),
    "hat": ((450, 262), (410, 130), "head"),
    "hat_tip": ((318, 168), (240, 185), "hat"),
    "brim_l": ((395, 300), (285, 385), "hat"),
    "brim_r": ((560, 232), (672, 205), "hat"),
    "hair_l": ((352, 270), (288, 232), "head"),
    "hair_ll": ((400, 335), (372, 432), "head"),
    "hair_r": ((548, 262), (604, 248), "head"),
    "collar": ((540, 462), (540, 545), "chest"),
    "sleeve_l": ((185, 452), (430, 470), "pole"),
    "sleeve_r": ((875, 455), (650, 470), "pole"),
    "hand_l": ((165, 445), (55, 520), "pole"),
    "hand_r": ((890, 455), (985, 545), "pole"),
    "rope": ((152, 462), (150, 588), "pole"),
    "jug": ((150, 588), (128, 800), "rope"),
    "belt": ((622, 772), (622, 905), "hips"),
    "leg_l": ((470, 860), (462, 1130), "hips"),
    "leg_r": ((585, 860), (592, 1130), "hips"),
    "cuff_l": ((466, 1132), (466, 1220), "leg_l"),
    "cuff_r": ((590, 1132), (590, 1220), "leg_r"),
    # each boot hangs off its own trouser leg (pivot: the boot's top, under the straw cuff), so it goes wherever
    # the leg swings - they were one "boots" bone tied to the post, and read as a pair floating off the legs
    "boot_l": ((490, 1172), (452, 1350), "leg_l"),
    "boot_r": ((558, 1172), (598, 1350), "leg_r"),
    "crow": ((878, 416), (870, 250), "pole"),
    # the crow's wings (tools/fall/gen_crow_wing.py): each a small drawn layer on its own bone, folded along the
    # crow's back at rest - wholly behind its body, so the rest pose shows nothing - and spread by a turn about the
    # shoulder and a scale-up (run_clip: the wing / flap drivers). Both start from the same fold; wing_r's picture
    # is wing_l's mirrored across the bone, and it opens the other way.
    "wing_l": ((858, 292), (818, 384), "crow"),
    "wing_r": ((858, 292), (818, 384), "crow"),
}
BONE_NAMES = list(BONES)

# ---------------------------------------------------------------- the legs meet the boots (2026-11-08, round 2)
# The cut-out's straw cuffs ended at art y ~1205 and the boots began at ~1238: a band of bare post showed between
# (and through the straw fringe), and the boots read as a separate pair tied to the pole. join_legs() closes it on
# every body layer: the trouser legs grow LEG_D px longer (a smooth stretch of the plain denim band LEG_BAND, so the
# patches and the frayed hems keep their shape), the cuffs and straw move down with them, and the boots move BOOT_U
# px up, their rope tops tucked right under the denim hems and drawn UNDER the straw - the fringe hangs over the
# boots' leather, not over the bare post. Applied wherever the body layers are read: the weights
# here, Blender's textures, and tools/fall/pack_char_rig.py (which writes the repaired layers the game and the
# lobby covers use).
LEG_BAND = (1020, 1110)        # out rows over which the stretch is eased in (src 1020..1080: plain denim)
LEG_D = 20                     # the cuffs move this far down
BOOT_SRC = 1236                # source rows >= this are the boots (the empty band above it is dropped)
BOOT_U = 70                    # the boots move this far up
BOOT_SPLIT = 522               # art x between the two boots (left boot left of it)


def _rows(img, src):
    """Resample img's rows at fractional source rows src (premultiplied, linear); out-of-range rows are empty."""
    H = img.shape[0]
    pm = np.concatenate([img[..., :3] * img[..., 3:], img[..., 3:]], -1)
    s0 = np.floor(src).astype(int)
    k = (src - s0)[:, None, None].astype(np.float32)
    ok0 = ((s0 >= 0) & (s0 < H))[:, None, None]
    ok1 = ((s0 + 1 >= 0) & (s0 + 1 < H))[:, None, None]
    a = np.where(ok0, pm[np.clip(s0, 0, H - 1)], 0)
    b = np.where(ok1, pm[np.clip(s0 + 1, 0, H - 1)], 0)
    return a * (1 - k) + b * k


def join_legs(img, parts=False):
    """A body layer (H x W x 4 float 0..1, straight alpha) -> the same with the legs reaching down into the boots.
    parts=True -> (that, the legs alone, the boots alone) (the game draws the boots as rigid sprites UNDER the
    skinned body: a continuous mesh smeared the leather between them whenever the legs kicked apart)."""
    H = img.shape[0]
    y = np.arange(H, dtype=np.float64)
    t = np.clip((y - LEG_BAND[0]) / (LEG_BAND[1] - LEG_BAND[0]), 0, 1)
    src = y - LEG_D * t * t * (3 - 2 * t)
    legs_src = img.copy()
    legs_src[BOOT_SRC:] = 0
    boots_src = img.copy()
    boots_src[:BOOT_SRC] = 0
    legs = _rows(legs_src, src)                        # (rows above the band: src == y, an exact copy)
    boots = _rows(boots_src, y + BOOT_U)
    out = legs + boots * (1 - legs[..., 3:])           # the legs (cuff straw) over the boots

    def straight(pm):
        a = pm[..., 3:]
        return np.concatenate([np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0), a], -1).astype(np.float32)
    return (straight(out), straight(legs), straight(boots)) if parts else straight(out)


# ---------------------------------------------------------------- skin weights (numpy only: Blender and tools share it)

def _clamp(v, a=0.0, b=1.0):
    return np.minimum(b, np.maximum(a, v))


def _poly(xs, ys, pts):
    """Even-odd point-in-polygon for arrays of points."""
    inside = np.zeros(xs.shape, bool)
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if y1 == y2:
            continue
        c = ((y1 > ys) != (y2 > ys)) & (xs < (x2 - x1) * (ys - y1) / (y2 - y1) + x1)
        inside ^= c
    return inside


def _rect(xs, ys, x0, y0, x1, y1):
    return (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)


def _hat_line(x):
    """The line between the hat (above) and the face/hair (below), art px y at x."""
    return np.interp(x, [300, 380, 430, 470, 520, 560, 610, 700], [330, 318, 290, 262, 240, 228, 238, 260])


def regions(xs, ys, straw):
    """[(mask, {bone: share array or float})] in paint order (later over earlier). straw: the straw-yellow pixels
    (the hair tufts are told from the brim they poke out under by their colour)."""
    R = []
    k = lambda v: _clamp(v)
    # the torso: chest above, hips below, a long soft blend through the waist
    torso = _poly(xs, ys, [(400, 430), (700, 420), (740, 800), (720, 860), (400, 860)])
    kh = k((ys - 620) / 190)
    R.append((torso, {"chest": 1 - kh, "hips": kh}))
    # legs: from the hips (top) to each leg, split down the middle of the overalls
    legs = _rect(xs, ys, 380, 820, 700, 1105 + LEG_D)
    kl = k((ys - 830) / 140) ** 1.2
    left = (xs < 518).astype(float)
    R.append((legs, {"hips": 1 - kl, "leg_l": kl * left, "leg_r": kl * (1 - left)}))
    # the straw at the cuffs flutters off each leg; its tips lie over the boot's top, so they hand over to the boot
    boot_top = BOOT_SRC - BOOT_U
    cuffs = _rect(xs, ys, 380, 1105 + LEG_D, 700, boot_top + 60)
    kc = k((ys - 1112 - LEG_D) / 70)
    kb = k((ys - boot_top - 6) / 50)
    left = (xs < 520).astype(float)
    R.append((cuffs, {"leg_l": (1 - kc) * (1 - kb) * left, "cuff_l": kc * (1 - kb) * left, "boot_l": kb * left,
                      "leg_r": (1 - kc) * (1 - kb) * (1 - left), "cuff_r": kc * (1 - kb) * (1 - left),
                      "boot_r": kb * (1 - left)}))
    # the boots, each on its own leg
    left = (xs < 522).astype(float)
    R.append((ys >= boot_top + 60, {"boot_l": left, "boot_r": 1 - left}))
    # the rope belt's dangling ends
    belt = _rect(xs, ys, 596, 780, 660, 930)
    kb = k((ys - 790) / 70)
    R.append((belt, {"hips": 1 - kb, "belt": kb}))
    # the sleeves: following the chest at the shoulder, sagging between it and the tied wrist
    sl = _poly(xs, ys, [(180, 330), (300, 330), (450, 400), (455, 600), (180, 600)])
    ks = k((xs - 200) / 250) ** 1.3
    R.append((sl, {"chest": ks, "sleeve_l": 1 - ks}))
    sr = _poly(xs, ys, [(890, 330), (760, 340), (630, 400), (640, 640), (890, 640)])
    ks = k((860 - xs) / 230) ** 1.3
    R.append((sr, {"chest": ks, "sleeve_r": 1 - ks}))
    # the straw hands, past the wrist ties (the ties themselves are the post's)
    hl = _rect(xs, ys, 0, 320, 180, 600)
    kk = k((158 - xs) / 75)
    R.append((hl, {"hand_l": kk, "pole": 1 - kk}))
    hr = _rect(xs, ys, 868, 320, 1024, 640)
    kk = k((xs - 888) / 70)
    R.append((hr, {"hand_r": kk, "pole": 1 - kk}))
    # the jug's rope, from the wrist tie down to the jug's neck, and the jug
    rope = _rect(xs, ys, 112, 455, 195, 600)
    kr = k((ys - 470) / 40)
    R.append((rope, {"pole": 1 - kr, "rope": kr}))
    R.append((_rect(xs, ys, 0, 575, 240, 900), {"jug": 1.0}))
    # the straw collar hangs off the neck
    col = _poly(xs, ys, [(425, 440), (660, 425), (670, 575), (420, 575)])
    kc = k((ys - 470) / 70)
    R.append((col, {"chest": 1 - kc, "collar": kc}))
    # the head: everything above the collar between the shoulders, then the hat and the hair over it
    head = _poly(xs, ys, [(215, 40), (720, 40), (720, 330), (640, 350), (628, 470), (560, 492), (440, 492), (408, 450),
                          (330, 430), (250, 410), (215, 300)])
    R.append((head, {"head": 1.0}))
    brim_low = _poly(xs, ys, [(236, 300), (300, 262), (380, 280), (432, 298), (414, 318), (372, 350), (332, 382),
                              (278, 404), (236, 404)])
    hat = head & ((ys < _hat_line(xs)) | brim_low)
    R.append((hat, {"hat": 1.0}))
    # the straw poking out of the hat's crown rides the hat
    tip = _poly(xs, ys, [(215, 110), (330, 95), (335, 225), (215, 225)])
    kt = k((330 - xs) / 70)
    R.append((tip & hat, {"hat": 1 - kt, "hat_tip": kt}))
    bl = hat & _poly(xs, ys, [(250, 330), (330, 270), (400, 290), (420, 310), (330, 420), (250, 420)])
    kb = k(np.hypot(xs - 395, ys - 300) / 110)
    R.append((bl, {"hat": 1 - kb, "brim_l": kb}))
    br = hat & (xs > 545)
    kb = k((xs - 545) / 110)
    R.append((br, {"hat": 1 - kb, "brim_r": kb}))
    # the straw hair: tufts out from under the brim
    kk = k(np.hypot(xs - 352, ys - 270) / 45)
    R.append((_poly(xs, ys, [(272, 200), (352, 190), (372, 262), (360, 340), (300, 340), (272, 300)]) & straw,
              {"hair_l": kk, "hat": 1 - kk}))
    hll = _poly(xs, ys, [(342, 318), (414, 312), (424, 445), (342, 448)]) & straw
    kk = k((ys - 330) / 70)
    R.append((hll, {"hair_ll": kk, "head": 1 - kk}))
    hrr = _poly(xs, ys, [(530, 230), (618, 214), (626, 300), (540, 296)]) & straw
    kk = k((xs - 548) / 50)
    R.append((hrr, {"hair_r": kk, "head": 1 - kk}))
    return R


def weight_maps(rgba, q=4, sigma=7.0, grow=60):
    """Per-bone weight maps at 1/q of the art's size: regions painted on the opaque pixels, grown out into the gaps,
    blurred a little, normalised. rgba: the body texture (H_PX x W_PX x 4, 0..1; alpha = the union of the faces').
    -> {bone: (H/q, W/q) float32}"""
    H4, W4 = H_PX // q, W_PX // q
    ys, xs = np.mgrid[0:H4, 0:W4].astype(np.float32) * q + q / 2
    a = rgba[..., 3].reshape(H4, q, W4, q).max(axis=(1, 3)) > .02
    c = (rgba[..., :3] * rgba[..., 3:]).reshape(H4, q, W4, q, 3).mean(axis=(1, 3)) /         np.maximum(1e-3, rgba[..., 3].reshape(H4, q, W4, q).mean(axis=(1, 3)))[..., None]
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    straw = (r > .62) & (g > .42) & (b < .45) & (r - b > .36)
    acc = {b: np.zeros((H4, W4), np.float32) for b in BONE_NAMES}
    painted = np.zeros((H4, W4), bool)
    for mask, shares in regions(xs, ys, straw):
        m = mask & a
        if not m.any():
            continue
        for b in acc:
            acc[b][m] = 0
        for b, w in shares.items():
            acc[b][m] = (w[m] if isinstance(w, np.ndarray) else w)
        painted |= m
    acc["hips"][a & ~painted] = 1.0                     # anything opaque no region named
    painted |= a
    # grow the painted weights out into the see-through gaps (nearest painted neighbour), so every outline's
    # vertices move with their own part
    stack = np.stack([acc[b] for b in BONE_NAMES])
    for _ in range(grow):
        if painted.all():
            break
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            src = np.roll(np.roll(painted, dy, 0), dx, 1)
            take = src & ~painted
            if take.any():
                stack[:, take] = np.roll(np.roll(stack, dy, 1), dx, 2)[:, take]
                painted = painted | take
    stack[0][~painted] = 1.0                            # far away: the ground
    # blur
    s = sigma / q
    r = int(3 * s) + 1
    ker = np.exp(-.5 * (np.arange(-r, r + 1) / s) ** 2)
    ker /= ker.sum()
    def band(n):                                           # the blur as a matrix (edges clamped)
        K = np.zeros((n, n), np.float32)
        for j, kv in enumerate(ker):
            idx = np.clip(np.arange(n) + j - r, 0, n - 1)
            K[np.arange(n), idx] += kv
        return K
    Ky, Kx = band(H4), band(W4)
    stack = np.matmul(np.matmul(Ky[None], stack), Kx.T[None]).astype(np.float32)
    stack /= np.maximum(1e-6, stack.sum(0))
    return {b: stack[i] for i, b in enumerate(BONE_NAMES)}


def pole_weights(xs, ys):
    """The pole layer: the post (and its crossbar, ties, the ropes round it) on the pole bone, the grass patch on the
    ground, a soft hand-over between."""
    k = _clamp((ys - 1385) / 70)
    # the contact shadow on the field either side of the post's foot stays on the ground (it never wobbles)
    k = np.maximum(k, _clamp((np.abs(xs - 522) - 70) / 30) * _clamp((ys - 1300) / 30))
    return {"pole": 1 - k, "ground": k}


def sample(maps, xs, ys, q=4, top=4):
    """Bilinear-sample the maps at art px points -> (idx (n, top) int, w (n, top) float), weights renormalised."""
    names = BONE_NAMES
    stack = np.stack([maps[b] for b in names])
    H4, W4 = stack.shape[1:]
    fx = np.clip((np.asarray(xs) - q / 2) / q, 0, W4 - 1.001)
    fy = np.clip((np.asarray(ys) - q / 2) / q, 0, H4 - 1.001)
    x0, y0 = fx.astype(int), fy.astype(int)
    tx, ty = fx - x0, fy - y0
    v = (stack[:, y0, x0] * (1 - tx) * (1 - ty) + stack[:, y0, x0 + 1] * tx * (1 - ty) +
         stack[:, y0 + 1, x0] * (1 - tx) * ty + stack[:, y0 + 1, x0 + 1] * tx * ty).T
    idx = np.argsort(-v, axis=1)[:, :top]
    w = np.take_along_axis(v, idx, 1)
    w[w < .01] = 0
    w /= np.maximum(1e-6, w.sum(1, keepdims=True))
    return idx, w


def body_rgba(read):
    """The neutral body's colour with the union of every face's alpha, 0..1. read(path) -> (H, W, 4) float 0..1
    (Blender's image API inside Blender, PIL outside)."""
    out = read(os.path.join(LAY, "body_neutral.png")).copy()
    for f in FACES:
        out[..., 3] = np.maximum(out[..., 3], read(os.path.join(LAY, f"body_{f}.png"))[..., 3])
    return join_legs(out)


def blender_read(path):
    """The file's own pixels (a fresh, throw-away load: the textures' pixels are replaced by join_legs)."""
    im = bpy.data.images.load(bpy.path.abspath(path), check_existing=False)
    im.alpha_mode = "STRAIGHT"
    px = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(px)
    out = px.reshape(im.size[1], im.size[0], 4)[::-1].copy()
    bpy.data.images.remove(im)
    return out


# ---------------------------------------------------------------- scene

def clear():
    if bpy.app.background:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def setup():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    try:
        sc.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ORTHO
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.location = (0, -30, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    if sc.world is None:
        sc.world = bpy.data.worlds.new("world")


def load(path):
    im = bpy.data.images.get(os.path.basename(path)) or bpy.data.images.load(path)
    im.alpha_mode = "STRAIGHT"
    return im


def face_material():
    """Emission material choosing between the body textures by a keyed 'face' index (constant keys)."""
    m = bpy.data.materials.new("body")
    m.use_nodes = True
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    face = nt.nodes.new("ShaderNodeValue")
    face.name = face.label = "face"
    col = alpha = None
    for i, f in enumerate(FACES):
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = load(os.path.join(LAY, f"body_{f}.png"))
        if not tex.image.get("joined"):                  # the legs reaching the boots (join_legs), as the game has it
            px = join_legs(blender_read(tex.image.filepath))
            tex.image.pixels.foreach_set(np.ascontiguousarray(px[::-1]).ravel())
            tex.image["joined"] = 1
        tex.interpolation = "Linear"
        tex.extension = "CLIP"
        if col is None:
            col, alpha = tex.outputs["Color"], tex.outputs["Alpha"]
            continue
        cmp = nt.nodes.new("ShaderNodeMath")
        cmp.operation = "COMPARE"
        cmp.inputs[1].default_value = float(i)
        cmp.inputs[2].default_value = 0.5
        nt.links.new(face.outputs[0], cmp.inputs[0])
        mc = nt.nodes.new("ShaderNodeMix")
        mc.data_type = "RGBA"
        nt.links.new(cmp.outputs[0], mc.inputs["Factor"])
        nt.links.new(col, mc.inputs[6])
        nt.links.new(tex.outputs["Color"], mc.inputs[7])
        ma = nt.nodes.new("ShaderNodeMix")
        ma.data_type = "FLOAT"
        nt.links.new(cmp.outputs[0], ma.inputs["Factor"])
        nt.links.new(alpha, ma.inputs[2])
        nt.links.new(tex.outputs["Alpha"], ma.inputs[3])
        col, alpha = mc.outputs[2], ma.outputs[0]
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(col, em.inputs["Color"])
    nt.links.new(alpha, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def plain_material(name, path):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    try:
        m.surface_render_method = "BLENDED"
    except AttributeError:
        m.blend_method = "BLEND"
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = load(path)
    tex.interpolation = "Linear"
    tex.extension = "CLIP"
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    fade = nt.nodes.new("ShaderNodeValue")
    fade.name = "fade"
    fade.outputs[0].default_value = 1.0
    am = nt.nodes.new("ShaderNodeMath")
    am.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], am.inputs[0])
    nt.links.new(fade.outputs[0], am.inputs[1])
    nt.links.new(am.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def plane(name, w, h, nx, ny, mat, depth):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=.5, calc_uvs=True)
    bmesh.ops.scale(bm, vec=(w, h, 1), verts=bm.verts)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0, depth, 0)
    return ob


def build_rig():
    ad = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (h, t, par) in BONES.items():
        b = ad.edit_bones.new(name)
        hx, hz = u(*h)
        tx, tz = u(*t)
        b.head, b.tail = (hx, 0, hz), (tx, 0, tz)
        b.roll = 0
    for name, (h, t, par) in BONES.items():
        if par:
            ad.edit_bones[name].parent = ad.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    return arm


def skin(ob, arm, fn):
    """Vertex groups from fn(xs, ys) -> (idx, w) over the object's vertices (art px), + an armature modifier."""
    groups = {n: ob.vertex_groups.new(name=n) for n in BONE_NAMES}
    co = np.array([(v.co.x * 100 + W_PX / 2, H_PX / 2 - v.co.z * 100) for v in ob.data.vertices])
    idx, w = fn(co[:, 0], co[:, 1])
    for vi in range(len(co)):
        for k in range(idx.shape[1]):
            if w[vi, k] > 0:
                groups[BONE_NAMES[idx[vi, k]]].add([vi], float(w[vi, k]), "REPLACE")
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    ob.parent = arm


def build():
    clear()
    setup()
    arm = build_rig()
    maps = weight_maps(body_rgba(blender_read))
    pole = plane("pole", W_PX / 100, H_PX / 100, W_PX // 32, H_PX // 32, plain_material("pole", os.path.join(LAY, "pole.png")), 0.5)

    def pole_fn(xs, ys):
        w = pole_weights(xs, ys)
        idx = np.array([[BONE_NAMES.index("pole"), BONE_NAMES.index("ground")]] * len(xs))
        return idx, np.stack([w["pole"], w["ground"]], 1)
    skin(pole, arm, pole_fn)
    body = plane("body", W_PX / 100, H_PX / 100, W_PX // GRID, H_PX // GRID, face_material(), 0.0)
    skin(body, arm, lambda xs, ys: sample(maps, xs, ys))
    crow = plane("crow", W_PX / 100, H_PX / 100, 1, 1, plain_material("crow", os.path.join(LAY, "crow.png")), -0.1)
    skin(crow, arm, lambda xs, ys: (np.full((len(xs), 1), BONE_NAMES.index("crow")), np.ones((len(xs), 1))))
    for wn in ("wing_l", "wing_r"):                      # behind the body, as the game draws them (gen_crow_wing.py)
        if os.path.exists(os.path.join(LAY, wn + ".png")):
            w = plane(wn, W_PX / 100, H_PX / 100, 1, 1, plain_material(wn, os.path.join(LAY, wn + ".png")), 0.25)
            skin(w, arm, lambda xs, ys, wn=wn: (np.full((len(xs), 1), BONE_NAMES.index(wn)), np.ones((len(xs), 1))))
    # effect sprites: hiccup bubbles, straw bits, leaves, feathers, sparkles - farm, not glitter
    fx = {}
    for kind, n, size in (("bubble", 6, 0.8), ("straw", 14, 1.0), ("leaf_red", 5, 1.1), ("leaf_orange", 5, 1.1),
                          ("leaf_gold", 5, 1.1), ("feather", 8, 0.9), ("sparkle", 8, 0.9), ("star", 6, 0.9), ("drop", 8, 0.7)):
        fx[kind] = []
        for i in range(n):
            ob = plane(f"fx_{kind}_{i}", size, size, 1, 1, plain_material(f"{kind}_{i}", os.path.join(FX, kind + ".png")),
                       -0.6 - .01 * i)
            ob["fx"] = kind
            ob["size"] = size
            set_fade(ob, 0, 0.0)
            fx[kind].append(ob)
    os.makedirs(OUT, exist_ok=True)
    return arm, body, fx


# ---------------------------------------------------------------- keys

def set_fade(ob, f, v):
    s = ob.active_material.node_tree.nodes["fade"].outputs[0]
    s.default_value = v
    s.keyframe_insert("default_value", frame=f)


def key_face(body, f, name):
    s = body.active_material.node_tree.nodes["face"].outputs[0]
    s.default_value = float(FACES.index(name))
    s.keyframe_insert("default_value", frame=f)


_AX = {}


def _axes(arm):
    """Per bone: the rest orientation (to turn screen-space moves into the bone's own) and the sign that makes a
    positive angle counter-clockwise on screen."""
    if not _AX:
        for b in arm.data.bones:
            R = b.matrix_local.to_3x3()
            sign = 1.0 if (R @ Vector((0, 0, 1))).y < 0 else -1.0     # local Z toward the camera (-Y): CCW
            _AX[b.name] = (R.inverted(), sign)
    return _AX


def key(arm, f, pose):
    """pose: bone -> {r: deg CCW on screen, x, y: screen units (x right, y up), sx, sy (the bone's across / along)}"""
    ax = _axes(arm)
    for b in arm.pose.bones:
        ch = pose.get(b.name, {})
        Rinv, sign = ax[b.name]
        loc = Rinv @ Vector((ch.get("x", 0.0), 0.0, ch.get("y", 0.0)))
        b.location = loc
        b.rotation_euler = (0, 0, math.radians(ch.get("r", 0.0)) * sign)
        s = ch.get("s", 1.0)
        b.scale = (ch.get("sx", s), ch.get("sy", s), 1)
        b.keyframe_insert("location", frame=f)
        b.keyframe_insert("rotation_euler", frame=f)
        b.keyframe_insert("scale", frame=f)


class Spring:
    """A damped spring: follows a target with lag and overshoot; kick() adds velocity (an impulse)."""

    def __init__(self, freq, zeta, x=0.0):
        self.w, self.z = 2 * math.pi * freq, zeta
        self.x, self.v = x, 0.0

    def kick(self, dv):
        self.v += dv

    def step(self, target, dt=1 / FPS, sub=6):
        for _ in range(sub):
            h = dt / sub
            a = self.w * self.w * (target - self.x) - 2 * self.z * self.w * self.v
            self.v += a * h
            self.x += self.v * h
        return self.x


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def bump(t, a, b):
    """0 outside [a, b], a smooth hump peaking at the middle."""
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def pulse(t, a, b):
    """A sharp hit at a that eases off by b (an impact): 0 before a, 1 at a+, decays smoothly to 0 at b."""
    if t < a or t >= b:
        return 0.0
    k = (t - a) / (b - a)
    return (1 - k) ** 2 * min(1.0, k * 6 + .4)


def env(i, n, att=8, rel=14):
    """1 in the middle of a clip, easing up from 0 over att frames and back to 0 over the last rel frames."""
    return ease(i / att) * ease((n - i) / rel)


def hop(i, a, b, x0, x1, h):
    """A hop between frames a..b from x0 to x1 (units) with an arc of height h -> (x, y, squash)."""
    if i <= a:
        return x0, 0.0, (.12 if a - 3 < i <= a else 0.0)       # crouch just before take-off
    if i >= b:
        return x1, 0.0, (.14 * (1 - (i - b) / 4) if i < b + 4 else 0.0)   # squash on landing
    t = (i - a) / (b - a)
    e = t * t * (3 - 2 * t)
    return x0 + (x1 - x0) * e, 4 * h * t * (1 - t), -.1 * math.sin(math.pi * t)  # stretched in the air


# ---------------------------------------------------------------- choreography
# Reworked 2026-11-10 (the Stake review: "poor assets and animations"). Every clip was a sine under an envelope:
# even timing, no anticipation, nothing held, the same small sway at three sizes. Now each is posed on a timeline
# (tl: keys with their own eases - a wind-up, a snap, an overshoot, a settle, a hold) and the springs in run_clip
# carry the overlap (the head, hat, straw, sleeves, legs, boots, jug and crow each arrive late and overshoot).
# Angles: degrees counter-clockwise on screen. The BOARD IS ON HIS RIGHT: negative sway / lean / hd / pole lean
# him toward it. swing: both legs together (+ = feet to the right); legs: the scissor between them (kept small:
# the trouser legs are one mesh and tear when they part by more than ~15 deg).

_E = {
    "lin": lambda t: t,
    "io": lambda t: t * t * (3 - 2 * t),
    "in": lambda t: t * t,
    "out": lambda t: 1 - (1 - t) ** 2,
    "in3": lambda t: t ** 3,
    "out3": lambda t: 1 - (1 - t) ** 3,
}


def tl(i, keys):
    """A timeline: keys (frame, value[, ease]) in order; the ease is how the value ARRIVES at that key
    (io = eased both ends, out / out3 = a snap that lands softly, in / in3 = a fall that hits, lin)."""
    if i <= keys[0][0]:
        return keys[0][1]
    for k in range(1, len(keys)):
        if i <= keys[k][0]:
            f0, v0 = keys[k - 1][0], keys[k - 1][1]
            f1, v1 = keys[k][0], keys[k][1]
            return v0 + (v1 - v0) * _E[keys[k][2] if len(keys[k]) > 2 else "io"]((i - f0) / (f1 - f0))
    return keys[-1][1]


def ring(i, f0, amp, hz, tau):
    """A wobble set off at frame f0 that dies away: amp * exp(-t / tau) * sin(2 pi hz t) - 0 at f0, so it never pops."""
    if i <= f0:
        return 0.0
    t = (i - f0) / FPS
    return amp * math.exp(-t / tau) * math.sin(2 * math.pi * hz * t)


def cl(v, a, b):
    return a if v < a else b if v > b else v


def drivers():
    return dict(sway=0.0, lean=0.0, hd=0.0, bob=0.0, legs=0.0, swing=0.0, chest_s=0.0, breath=0.0, pole=0.0,
                body_s=0.0, head_s=0.0, hat_lift=0.0, hat_s=0.0, hat_r=0.0, tip=0.0, brims=0.0, hands=0.0,
                hand_l=0.0, hand_r=0.0, jug=0.0, sag=0.0, wind=0.0, tremble=0.0,
                crow_x=0.0, crow_y=0.0, crow_r=0.0, crow_hit=0.0, crow_flip=1.0, crow_sq=0.0, crow_free=0.0,
                wing=0.0, flap=0.0)


# where things are, in units (x right, y up, the art's centre the origin) - for the effect sprites
P_HAT, P_MOUTH, P_JUG, P_CROW, P_CHEST = (-.9, 6.2), (-.1, 3.5), (-3.65, 1.7), (3.66, 4.7), (.2, 2.2)


def _flick(d, i, f0, f1, amp=.8, rate=1.15):
    """The crow's wings flick open and shut (a startle), frames f0..f1."""
    w = bump(i, f0, f1)
    if w > 0:
        d["wing"] = max(d["wing"], amp * w ** .5)
        d["flap"] = math.cos((i - f0) * rate)


def _idle(d, i, n, rng, emit, face, kicks):
    """10 s. A drunk's weight shifts - he drifts off balance, catches himself late, settles - breathing all the
    while; he eyes the board, a breeze goes through his straw, he nods off in three sinking nods and jerks awake
    (hat hopping, eyes wide, then a sly look round to see who noticed). The jug swings on its own pendulum and the
    crow lives its own bird life: sharp looks with holds between, a ruffle, a preen, a shuffle along the bar."""
    a = 2 * math.pi * i / n

    def sway_at(j):
        return tl(j % n, [(0, 0), (14, -.6), (46, -4.4), (62, -5.4), (73, 2.8), (84, 1.0), (96, 1.6), (134, 5.0),
                          (150, 6.0), (162, -2.2), (174, -.4), (186, -1.2), (214, -2.6), (260, -4.2),
                          (267, 1.8, "out"), (278, -.8), (290, 0), (300, 0)])
    doze = tl(i, [(186, 0), (206, .45), (214, .35), (232, .8, "in"), (240, .68, "out"), (258, 1.0, "in"), (262, 1.0),
                  (265, 0, "out3")])
    d["sway"] = sway_at(i)
    d["pole"] = .16 * sway_at(i - 7) + ring(i, 262, .5, 3.0, .22) * tl(i, [(280, 1), (290, 0)])
    d["lean"] = -.5 * sway_at(i - 5) + .8 * math.sin(2 * a) * tl(i, [(0, 0), (20, 1), (270, 1), (290, 0)])
    d["hd"] = tl(i, [(0, 0), (12, 1.5), (30, -6), (56, -7), (66, -2.5), (76, 4), (92, 2), (136, 5.5), (150, 7),
                     (164, -3.5), (178, -.5), (186, 0), (300, 0)]) + 19 * doze + \
        tl(i, [(262, 0), (266, -9, "out3"), (273, -3), (281, 1.2), (290, 0)])
    d["bob"] = tl(i, [(60, 0), (66, -.05, "in"), (74, .025, "out"), (84, 0), (148, 0), (154, -.06, "in"),
                      (163, .03, "out"), (174, 0)]) - .12 * doze + \
        tl(i, [(262, 0), (265, .13, "out3"), (271, -.03), (278, 0)]) + .012 * math.sin(3 * a)
    d["breath"] = math.sin(3 * a) * (1 + .9 * doze)                 # three breaths a loop, deeper as he dozes
    d["head_s"] = .012 * math.sin(3 * a) + tl(i, [(262, 0), (264, .08, "out"), (270, -.02), (276, 0)])
    d["hat_lift"] = tl(i, [(262, 0), (265, .16, "out"), (271, 0, "in")])
    d["hat_r"] = 3 * doze
    d["sag"] = .5 * doze
    d["hands"] = -8 * doze + tl(i, [(262, 0), (266, 26, "out3"), (276, 0)])
    d["jug"] = (3.4 + 1.5 * math.sin(a + 1.0)) * math.sin(7 * a)    # its own pendulum, 1.4 s a swing
    d["wind"] = bump(i, 100, 132) * math.sin((i - 100) * .55) + .55 * bump(i, 214, 240) * math.sin((i - 214) * .6)
    if i == 263:
        kicks.extend([("tip", -180), ("brim", 90), ("hair", 130), ("jug", -50)])
    for b0 in (22, 92, 168, 174):
        face(b0, "blink"); face(b0 + 3, "neutral")
    face(34, "smug"); face(54, "neutral")                           # a sly look at the board
    face(190, "blink"); face(194, "neutral"); face(199, "blink"); face(204, "neutral"); face(208, "blink")
    face(262, "shock"); face(273, "smug"); face(285, "neutral")
    # the crow
    d["crow_r"] = tl(i, [(0, 0), (18, 0), (20, -7, "out3"), (34, -7), (36, 0, "out3"), (40, 9, "out3"), (66, 9),
                         (69, 0, "out3"), (118, 0), (120, -10, "out3"), (128, -10), (130, -17, "out3"),
                         (133, -10, "out"), (137, -17, "out3"), (140, -10, "out"), (146, 0), (236, 0),
                         (239, 10, "out3"), (262, 12), (264, -6, "out3"), (274, 6), (288, 6), (292, 0)])
    look = tl(i, [(36, 0), (39, 1, "lin"), (66, 1), (69, 0, "lin"), (234, 0), (237, 1, "lin"), (288, 1), (291, 0, "lin")])
    d["crow_flip"] = 1 - 2 * look
    if i < 180:
        x, y, sq = hop(i, 150, 156, 0, -.12, .08)
    else:
        x, y, sq = hop(i, 204, 210, -.12, 0, .08)
    _, y2, sq2 = hop(i, 263, 270, 0, 0, .26)
    d["crow_x"], d["crow_y"], d["crow_sq"] = x, y + y2, sq + sq2 + .07 * bump(i, 84, 98) * math.sin((i - 84) * 1.6)
    _flick(d, i, 263, 272)


def _spin(d, i, n, rng, emit, face, kicks):
    """0.7 s, on every spin: a blink and a dip, a small hop with a glance at the board, the jug knocked swinging."""
    d["bob"] = tl(i, [(0, 0), (2, -.07, "out"), (6, .16, "out3"), (10, -.03, "in"), (14, .012), (18, 0)])
    d["body_s"] = tl(i, [(0, 0), (2, -.04, "out"), (5, .05, "out"), (10, -.03), (15, 0)])
    d["hd"] = tl(i, [(0, 0), (2, 3, "out"), (6, -9, "out3"), (13, -7.5), (19, 0)])
    d["sway"] = tl(i, [(0, 0), (6, -2.2, "out"), (13, -1.6), (20, 0)])
    d["pole"] = ring(i, 3, .5, 3.2, .16)
    d["hat_lift"] = tl(i, [(2, 0), (6, .12, "out"), (10, 0, "in")])
    d["hat_s"] = tl(i, [(0, 0), (2, -.05), (5, .1, "out"), (9, -.06), (13, 0)])
    d["hands"] = tl(i, [(2, 0), (6, 14, "out"), (14, 0)])
    if i == 3:
        kicks.extend([("jug", 55), ("tip", -90)])
    face(1, "blink"); face(4, "neutral")
    _, y, sq = hop(i, 5, 10, 0, 0, .1)
    d["crow_y"], d["crow_sq"] = y, sq
    d["crow_r"] = tl(i, [(4, 0), (7, -7, "out3"), (14, -6), (18, 0)])


def _spin2(d, i, n, rng, emit, face, kicks):
    """0.8 s, the other spin beat: he checks his jug - a sly tilt that way, a shrug of the post that sets it swinging."""
    d["hd"] = tl(i, [(0, 0), (2, -3, "out"), (7, 9, "out3"), (15, 7.5), (22, 0)])
    d["sway"] = tl(i, [(0, 0), (7, 2.4, "out"), (15, 1.8), (22, 0)])
    d["bob"] = tl(i, [(0, 0), (3, .03), (7, -.06, "out"), (11, .08, "out3"), (16, -.015), (20, 0)])
    d["body_s"] = tl(i, [(4, 0), (7, -.03), (11, .04, "out"), (16, 0)])
    d["pole"] = ring(i, 4, -.55, 3.0, .18)
    d["hat_lift"] = tl(i, [(7, 0), (11, .08, "out"), (15, 0, "in")])
    d["hand_l"] = tl(i, [(2, 0), (6, 30, "out3"), (10, -12), (16, 0)])
    if i == 5:
        kicks.extend([("jug", -90), ("tip", 80)])
    face(5, "smug"); face(17, "neutral")
    d["crow_r"] = tl(i, [(6, 0), (9, 8, "out3"), (16, 7), (20, 0)])
    _, y, sq = hop(i, 9, 14, 0, 0, .07)
    d["crow_y"], d["crow_sq"] = y, sq


def _win(d, i, n, rng, emit, face, kicks):
    """2 s. A wind-up dip (3 f), a happy jolt off the post - head back, hat popped off his head, straw hands up, both
    legs kicked out - a soft landing, then a second smaller bounce the other way and a loose settle. The crow is
    thrown off its feet, flaps, lands, and turns to stare at him."""
    d["bob"] = tl(i, [(0, 0), (3, -.14, "out"), (7, .40, "out3"), (11, .30), (15, -.07, "in"), (19, .03, "out"), (23, 0),
                      (25, -.05, "out"), (29, .2, "out3"), (34, -.04, "in"), (38, .015, "out"), (42, 0)])
    d["body_s"] = tl(i, [(0, 0), (3, -.07, "out"), (6, .09, "out"), (11, .03), (15, -.06, "in"), (19, .02, "out"),
                         (24, 0), (25, -.03), (28, .05, "out"), (34, -.03, "in"), (39, 0)])
    d["head_s"] = tl(i, [(0, 0), (3, -.06, "out"), (7, .08, "out"), (15, -.05, "in"), (20, 0)])
    d["hd"] = tl(i, [(0, 0), (3, 5, "out"), (7, -15, "out3"), (12, -11), (16, 3), (21, -4), (25, 0), (29, -9, "out3"),
                     (35, 2), (41, -2), (50, 0)])
    d["sway"] = tl(i, [(0, 0), (3, -1.5, "out"), (8, 6, "out3"), (15, 2), (22, -5), (29, -6.5, "out"), (36, 3),
                       (44, -1), (52, 0)])
    d["lean"] = tl(i, [(0, 0), (3, 2, "out"), (8, -5, "out3"), (16, 1), (29, 3), (38, -1), (48, 0)])
    d["pole"] = tl(i, [(0, 0), (3, .5, "out"), (8, -1.0, "out3"), (16, .6), (24, -.5), (30, -.8, "out"), (38, .3), (46, 0)])
    d["swing"] = tl(i, [(0, 0), (3, 4, "out"), (8, -24, "out3"), (14, -10), (20, 10), (25, 6), (30, 22, "out3"),
                        (37, -6), (44, 2), (52, 0)])
    d["legs"] = tl(i, [(3, 0), (8, 6, "out"), (16, -4), (30, -6, "out"), (40, 0)])
    d["hat_lift"] = tl(i, [(3, 0), (8, .34, "out3"), (12, .30), (17, 0, "in"), (29, 0), (32, .14, "out"), (37, 0, "in")])
    d["hat_s"] = tl(i, [(0, 0), (3, -.12, "out"), (7, .30, "out"), (12, .10), (17, -.2, "in"), (21, .06, "out"), (25, 0)])
    d["hat_r"] = tl(i, [(3, 0), (8, -5, "out"), (17, 2), (24, 0)])
    d["hands"] = tl(i, [(3, 0), (8, 60, "out3"), (14, 35), (19, -10), (29, 40, "out3"), (38, -5), (46, 0)])
    if i == 4:
        kicks.extend([("jug", -160), ("tip", -150), ("hair", 120)])
    if i == 26:
        kicks.append(("jug", 110))
    face(3, "happy"); face(50, "neutral")
    if i == 7:
        for k in range(4):
            ang = math.radians(48 + 28 * k + rng.uniform(-8, 8))
            sp = rng.uniform(2.6, 3.4)
            emit("star", 7, 23 + 2 * k, lambda tt, a=ang, s=sp: (P_HAT[0] + math.cos(a) * s * tt,
                                                                 P_HAT[1] + .4 + math.sin(a) * s * tt - 3.2 * tt * tt),
                 spin=260, grow=(.3, .7))
    if i == 30:
        for k in range(2):
            emit("sparkle", 30 + 2 * k, 46 + 2 * k, lambda tt, x0=rng.uniform(-2.6, .6): (x0, 4.6 + 1.6 * tt),
                 spin=140, grow=(.45, .1))
    # the crow: bounced off the bar, a flap, lands, stares
    _, y, sq = hop(i, 5, 13, 0, 0, .34)
    d["crow_y"], d["crow_sq"] = y, sq
    _flick(d, i, 5, 14, .9)
    look = tl(i, [(15, 0), (18, 1, "lin"), (42, 1), (45, 0, "lin")])
    d["crow_flip"] = 1 - 2 * look
    d["crow_r"] = tl(i, [(5, 0), (8, 12, "out3"), (13, -4), (18, 8, "out3"), (40, 9), (45, 0)])


def _big_win(d, i, n, rng, emit, face, kicks):
    """4.6 s. Eyes wide and a deep crouch (5 f), he throws himself off the post at the board - hat flying, legs out -
    lands, and jigs: seven hops on a 0.4 s beat, body one way and legs the other, the post rocking, the jug swinging
    hard enough to slosh; a last big jump held in the air (the pose), down, a loose settle. The crow bolts on the
    launch, flaps overhead cawing through the dance, and swoops back to the bar for the landing."""
    J0, J1, B = 18, 102, 12
    jig = J0 <= i < J1
    k, j = divmod(i - J0, B) if jig else (0, 0)
    side = 1 if k % 2 == 0 else -1
    up = tl(j, [(0, 0), (1, 0), (4, 1, "out3"), (8, .85), (12, 0)]) if jig else 0.0     # each beat's swing out and back
    d["bob"] = (tl(j, [(0, -.12), (1, -.12), (4, .34, "out3"), (7, .28), (10, -.06, "in"), (11, -.12, "lin"), (12, -.12)]) if jig else
                tl(i, [(0, 0), (5, -.32, "out"), (9, .62, "out3"), (13, .5), (17, -.12, "in"), (18, -.12)]) if i < J0 else
                tl(i, [(102, -.12), (105, -.30, "out"), (109, .66, "out3"), (119, .60), (124, -.12, "in"), (128, .04, "out"), (133, 0)]))
    d["body_s"] = (tl(j, [(0, -.07), (1, -.07), (4, .07, "out"), (8, .03), (10, -.02), (11, -.07, "lin"), (12, -.07)]) if jig else
                   tl(i, [(0, 0), (5, -.11, "out"), (8, .11, "out"), (13, .04), (17, -.07, "in"), (18, -.07)]) if i < J0 else
                   tl(i, [(102, -.07), (105, -.11, "out"), (108, .11, "out"), (119, .05), (124, -.08, "in"), (128, .02, "out"), (133, 0)]))
    d["head_s"] = (tl(j, [(0, -.05), (4, .05, "out"), (9, 0), (12, -.05, "in")]) if jig else
                   tl(i, [(0, 0), (5, -.10, "out"), (9, .10, "out"), (14, .03), (18, -.05, "in")]) if i < J0 else
                   tl(i, [(102, -.05), (105, -.09), (109, .10, "out"), (119, .05), (124, -.06, "in"), (129, 0)]))
    d["sway"] = side * 11 * up + tl(i, [(0, 0), (5, 3, "out"), (9, -9, "out3"), (14, -5), (18, 0)]) + \
        tl(i, [(102, 0), (105, 4, "out"), (109, -14, "out3"), (119, -15.5), (125, 3), (131, -1), (136, 0)])
    # (the post itself leans little toward the board: his crow and right hand are already at his box's edge)
    d["pole"] = side * 1.2 * up + tl(i, [(0, 0), (5, 1.3, "out"), (9, -1.5, "out3"), (14, -.8), (18, 0)]) + \
        tl(i, [(102, 0), (105, 1.2, "out"), (109, -1.5, "out3"), (119, -1.7), (125, .8), (131, -.3), (136, 0)])
    d["lean"] = -side * 3 * up + tl(i, [(0, 0), (5, 3, "out"), (9, -6, "out3"), (18, 0)]) + \
        tl(i, [(102, 0), (105, 3), (109, -6, "out3"), (119, -7), (126, 1), (134, 0)])
    d["swing"] = side * 26 * up + tl(i, [(0, 0), (5, 6, "out"), (10, -34, "out3"), (14, -22), (18, 0)]) + \
        tl(i, [(102, 0), (105, 8, "out"), (109, -40, "out3"), (119, -36), (125, 8), (130, -3), (136, 0)])
    d["legs"] = side * 6 * up
    d["hd"] = -side * 10 * up + tl(i, [(0, 0), (5, 10, "out"), (9, -20, "out3"), (14, -12), (18, 0)]) + \
        tl(i, [(102, 0), (105, 8, "out"), (109, -18, "out3"), (119, -20), (125, 4), (131, -2), (136, 0)])
    d["hat_lift"] = (tl(j, [(1, 0), (5, .2, "out"), (8, .16), (11, 0, "in")]) if jig else 0.0) + \
        tl(i, [(5, 0), (10, .40, "out3"), (14, .34), (19, 0, "in")]) + tl(i, [(105, 0), (110, .42, "out3"), (118, .36), (124, 0, "in")])
    d["hat_s"] = (tl(j, [(0, -.1), (1, -.1), (4, .16, "out"), (8, .05), (11, -.1, "in"), (12, -.1)]) if jig else
                  tl(i, [(0, 0), (5, -.2, "out"), (9, .34, "out"), (14, .1), (18, -.1, "in")]) if i < J0 else
                  tl(i, [(102, -.1), (105, -.2), (109, .34, "out"), (118, .1), (124, -.2, "in"), (128, .05), (132, 0)]))
    d["hat_r"] = -side * 4 * up
    d["hands"] = 45 * up + tl(i, [(5, 0), (9, 75, "out3"), (15, 40), (18, 0)]) + \
        tl(i, [(105, 0), (109, 80, "out3"), (119, 70), (125, -10), (132, 0)])
    d["hand_l"] = side * 22 * up
    d["hand_r"] = -side * 22 * up
    d["chest_s"] = .04 * up
    if i == 6:
        kicks.extend([("jug", -220), ("tip", -200), ("hair", 160), ("brim", 140)])
    if jig and j == 1:
        kicks.extend([("jug", -side * 170), ("hair", side * 90)])
    if i == 106:
        kicks.extend([("jug", -200), ("tip", -160)])
    face(1, "shock"); face(6, "cheer"); face(122, "happy"); face(132, "neutral")
    # straw shaken loose on every landing, leaves kicked up, the jug sloshing
    if (jig and j == 0) or i in (17, 124):
        for q in range(2):
            ang = rng.uniform(.5, 2.6)
            sp = rng.uniform(3.2, 5.5)
            emit("straw", i, i + 16, lambda tt, a=ang, s=sp: (P_CHEST[0] + math.cos(a) * s * tt,
                                                              P_CHEST[1] - 1 + math.sin(a) * s * tt - 7 * tt * tt),
                 spin=520, grow=(.8, .65))
    if i in (9, 30, 54, 78, 109):
        for q in range(2):
            kind = ("leaf_red", "leaf_orange", "leaf_gold")[(i // 3 + q) % 3]
            x0 = rng.uniform(-3.6, 2.6)
            emit(kind, i + 2 * q, i + 30 + 2 * q, lambda tt, x0=x0, w=rng.uniform(5, 8): (x0 + .9 * math.sin(tt * w), 7.2 - 6.5 * tt),
                 spin=300, grow=(.75, .65))
    if i in (7, 20, 44, 68, 92, 107):
        for q in range(2):
            vx, vy = rng.uniform(-2.4, .4), rng.uniform(2.2, 3.6)
            emit("drop", i + q, i + 13 + q, lambda tt, vx=vx, vy=vy: (P_JUG[0] + vx * tt, P_JUG[1] + vy * tt - 5.5 * tt * tt),
                 spin=0, grow=(.5, .35))
    # the crow: off the bar on the launch, flapping overhead, back down for the landing
    d["crow_free"] = tl(i, [(2, 0), (5, 1, "out"), (124, 1), (130, 0)])

    def crow_at(f):                                                  # (it keeps clear of his hat: he throws himself its way)
        y = tl(f, [(2, 0), (4, -.05, "out"), (10, 3.0, "out3"), (20, 3.0), (60, 2.5), (102, 3.0), (120, 3.0), (126, .7), (130, 0, "out")])
        x = tl(f, [(2, 0), (10, -.1, "out"), (40, -.5), (70, -.1), (100, -.45), (120, -.1), (130, 0)])
        return x, y
    x, y = crow_at(i)
    ph = 2 * math.pi * (i - 3) / 5.0                                 # 6 wing-beats a second
    air = tl(i, [(2, 0), (5, 1, "out"), (124, 1), (130, 0)])
    d["wing"] = tl(i, [(2, 0), (5, 1, "out"), (127, 1), (133, 0)])
    d["flap"] = math.cos(ph)
    d["crow_x"], d["crow_y"] = x, y + .09 * math.sin(ph) * air      # it rises on each down-beat
    d["crow_sq"] = -.09 * math.cos(ph) * air - .16 * bump(i, 20, 30) + (.16 * (1 - (i - 130) / 5) if 130 <= i < 135 else 0)
    d["crow_r"] = tl(i, [(2, 0), (6, 16, "out3"), (14, 6), (20, -8, "out3"), (30, -6), (36, 4), (112, 4), (120, -12),
                         (128, 6, "out"), (132, -3), (136, 0)]) + 4 * math.sin(ph * .5) * air
    if i in (4, 6, 22, 46, 70, 94, 129):
        cx, cy = crow_at(i)
        for q in range(2 if i < 12 else 1):
            emit("feather", i + q, i + 30 + q, lambda tt, x0=P_CROW[0] + cx + rng.uniform(-.5, .5), y0=P_CROW[1] + cy:
                 (x0 + .55 * math.sin(tt * 8), y0 - .3 - 4.2 * tt), spin=200, grow=(.85, .75))


def _lose(d, i, n, rng, emit, face, kicks):
    """2.5 s. A double-take (4 f), then he sags with real weight: drops, bounces at the bottom and hangs - head down,
    hat and brims drooped, straw hands limp - shaking his head slowly while the crow turns and shakes its own at him;
    one sorry hiccup, and he pulls himself back up."""
    def sag_at(f):
        return tl(f, [(0, 0), (4, -.12, "out"), (13, 1.12, "in3"), (18, .94, "out"), (24, 1.0), (56, 1.0), (60, 1.04),
                      (70, 0), (76, 0)])
    s = sag_at(i)
    hic = tl(i, [(52, 0), (54, 1, "out3"), (58, -.12, "in"), (62, 0)])
    d["bob"] = -.30 * s + .16 * hic
    d["body_s"] = -.07 * s + .05 * hic
    d["sway"] = 5 * s
    d["lean"] = 6 * sag_at(i - 1)
    d["pole"] = 1.0 * s
    d["hd"] = 13 * sag_at(i - 2) + 3.4 * math.sin((i - 28) * 2 * math.pi / 14) * bump(i, 28, 56) - 6 * hic
    d["head_s"] = -.05 * s + .07 * hic
    d["breath"] = -1.8 * s + .8 * math.sin((i - 24) * 2 * math.pi / 30) * bump(i, 24, 54)     # one long sigh
    d["hat_r"] = 6 * sag_at(i - 3)
    d["hat_s"] = -.16 * sag_at(i - 2)
    d["hat_lift"] = .1 * max(0.0, hic)
    d["tip"] = 16 * sag_at(i - 4)
    d["brims"] = 9 * sag_at(i - 3)
    d["hands"] = -38 * sag_at(i - 3)
    d["sag"] = s
    d["legs"] = -2 * s
    if i == 13:
        kicks.extend([("jug", 60), ("hair", -80)])
    if i == 53:
        kicks.extend([("jug", 70), ("tip", -140)])
    face(1, "shock"); face(5, "sad"); face(52, "hiccup"); face(59, "sad"); face(66, "neutral")
    if i == 54:
        emit("bubble", 54, 74, lambda tt: (P_MOUTH[0] + .6 + .3 * math.sin(tt * 9), P_MOUTH[1] + .2 + 2.6 * tt), grow=(.4, .9))
    look = tl(i, [(14, 0), (17, 1, "lin"), (62, 1), (65, 0, "lin")])
    d["crow_flip"] = 1 - 2 * look
    shake = math.sin((i - 26) * 2 * math.pi / 7) * bump(i, 26, 47) ** .5
    d["crow_r"] = tl(i, [(14, 0), (20, 9, "out3"), (60, 9), (66, 0)])
    d["crow_hit"] = 9 * shake
    d["crow_x"] = -.035 * shake
    _, y, sq = hop(i, 54, 59, 0, 0, .1)
    d["crow_y"], d["crow_sq"] = y, sq


def _anticipate(d, i, n, rng, emit, face, kicks, reps=1):
    """The bonus tease. A wind-up back (3 f), then he cranes at the board - post, hips, chest and head all leaning
    in, up on his toes, eyes wide, hat lifted off his brow - and HOLDS there trembling (a 0.8 s cycle the game can
    repeat for as long as the reel is held: frames HOLD_AT[0] .. HOLD_AT[0] + HOLD_AT[1]), swelling a little further
    in on each cycle while the crow cranes with him; released, he rocks back onto the post."""
    H0, P = HOLD_AT
    H1 = H0 + reps * P
    if i <= H0:
        k = tl(i, [(0, 0), (3, -.14, "out"), (9, 1.1, "out3"), (13, .97), (16, 1.0)])
        tre = tl(i, [(4, 0), (12, 1)])
    elif i <= H1:
        k, tre = 1.0, 1.0
    else:
        k = tl(i, [(H1, 1), (H1 + 3, 1.04, "out"), (H1 + 11, -.06), (H1 + 15, .01), (H1 + 18, 0)])
        tre = tl(i, [(H1, 1), (H1 + 6, 0)])
    hold = H0 <= i <= H1
    hp = ((i - H0) % P) / P if hold else 0.0
    swell = (.5 - .5 * math.cos(2 * math.pi * hp)) if hold else 0.0
    d["pole"] = -1.3 * k - .25 * swell           # (little: his crow and right hand are at the box's edge)
    d["sway"] = -8.5 * k - 1.2 * swell
    d["lean"] = -7 * k
    d["hd"] = -11 * k - 2 * swell
    d["head_s"] = .06 * k + .02 * swell
    d["bob"] = .13 * k + .04 * swell
    d["body_s"] = .035 * k
    d["hat_lift"] = .11 * k + .03 * swell
    d["hat_s"] = .06 * k
    d["hands"] = 16 * k + 8 * swell
    d["legs"] = 4 * math.sin(2 * math.pi * 4 * hp) * tre if hold else 0.0      # knees knocking
    d["tremble"] = tre
    if i == 4:
        kicks.extend([("jug", 120), ("tip", -120)])
    face(1, "blink"); face(4, "shock"); face(H1 + 9, "neutral")
    d["crow_r"] = -4 * k - 2 * swell
    if hold:
        _, y, sq = hop(((i - H0) % P), 12, 17, 0, 0, .09)
        d["crow_y"], d["crow_sq"] = y, sq


def _hiccup(d, i, n, rng, emit, face, kicks):
    """2.3 s, an idle break. He feels it coming (the chest swells), HIC - a two-frame jolt, hat off his head, a bubble -
    a puzzled blink... a bigger one and a little one right behind it, then a pleased drunk wobble. The crow jumps at
    each and ends up glaring at him."""
    hics, amps = (10, 31, 39), (1.0, 1.15, .7)
    jolt = sum(A * tl(i, [(h, 0), (h + 2, 1, "out3"), (h + 5, .3), (h + 8, -.12), (h + 12, 0)]) for h, A in zip(hics, amps))
    swell = tl(i, [(0, 0), (8, 1), (10, 1), (12, 0, "out"), (22, 0), (29, 1), (31, 1), (33, 0, "out")])
    d["breath"] = 1.6 * swell
    d["chest_s"] = .05 * max(0.0, jolt)
    d["bob"] = .30 * jolt - .04 * swell
    d["body_s"] = .07 * jolt
    d["head_s"] = .10 * jolt - .03 * swell
    d["hd"] = -9 * jolt + 3 * swell + tl(i, [(14, 0), (20, 5), (27, 3), (31, 0), (44, 0), (50, -6), (58, -4), (66, 0)])
    d["hat_lift"] = .22 * max(0.0, jolt)
    d["hat_s"] = .18 * jolt
    d["pole"] = .5 * jolt
    d["sway"] = ring(i, 41, 4.5, 1.5, .45) * tl(i, [(56, 1), (66, 0)])
    d["hands"] = 30 * max(0.0, jolt)
    for h, A in zip(hics, amps):
        if i == h + 1:
            kicks.extend([("tip", -200 * A), ("brim", 150 * A), ("jug", 90 * A), ("hair", 110 * A)])
        if i == h:
            emit("bubble", h + 1, h + 24, lambda tt, s=rng.uniform(-.3, .3): (P_MOUTH[0] + .6 + s + .35 * math.sin(tt * 9), P_MOUTH[1] + .1 + 3 * tt),
                 grow=(.35 + .1 * A, .7 + .3 * A))
    face(10, "hiccup"); face(17, "neutral"); face(21, "blink"); face(24, "neutral")
    face(31, "hiccup"); face(37, "neutral"); face(39, "hiccup"); face(46, "smug"); face(60, "neutral")
    y = sq = 0.0
    for h, A in zip(hics, amps):
        _, yy, ss = hop(i, h + 2, h + 7, 0, 0, .13 * A)
        y += yy; sq += ss
    d["crow_y"], d["crow_sq"] = y, sq
    _flick(d, i, 33, 40, .8)
    look = tl(i, [(42, 0), (45, 1, "lin"), (58, 1), (61, 0, "lin")])
    d["crow_flip"] = 1 - 2 * look
    d["crow_r"] = tl(i, [(42, 0), (46, 10, "out3"), (57, 10), (62, 0)])


def _peck(d, i, n, rng, emit, face, kicks):
    """2.8 s, an idle break. The crow hops down the arm to him in two hops, turns, pulls back and pecks the brim of
    his hat - once, then twice quickly; each lands on a wince (the brim flops, his head ducks away). He shakes it off
    hard, straw flying, and the crow flaps back to its end of the bar, caws at him and turns its back."""
    x, y, sq = hop(i, 3, 10, 0, -.55, .22)
    x2, y2, sq2 = hop(i, 12, 18, -.55, -1.0, .18)
    x3, y3, sq3 = hop(i, 53, 61, -1.0, -.5, .36)
    x4, y4, sq4 = hop(i, 69, 76, -.5, 0, .2)
    if i < 12:
        d["crow_x"], d["crow_y"], d["crow_sq"] = x, y, sq
    elif i < 53:
        d["crow_x"], d["crow_y"], d["crow_sq"] = x2, y2, sq2
    elif i < 69:
        d["crow_x"], d["crow_y"], d["crow_sq"] = x3, y3, sq3
    else:
        d["crow_x"], d["crow_y"], d["crow_sq"] = x4, y4, sq4
    turn = ease((i - 10) / 3) - ease((i - 63) / 3)                 # faces him (flipped) from 10..13 to 63..66
    d["crow_flip"] = 1 - 2 * turn
    hit = sum(tl(i, [(a - 5, 0), (a - 1, -.6, "out"), (a, 1, "lin"), (a + 2, .35, "out"), (a + 5, 0)]) for a in PECKS)
    d["crow_r"] = 5 * bump(i, 16, 52) ** .6 * turn + tl(i, [(61, 0), (63, 10, "out3"), (67, 8), (70, 0)])
    d["crow_hit"] = 10 * hit * turn                                 # right on the cue (no spring lag)
    d["crow_x"] += -.23 * max(0.0, hit) * turn + .07 * max(0.0, -hit) * turn
    d["crow_y"] += .05 * max(0.0, hit)
    d["crow_sq"] += -.16 * bump(i, 61, 67)                          # the caw: it stretches up
    _flick(d, i, 53, 62, 1.0)
    for a in PECKS:
        if i == a:
            kicks.extend([("brim_r", -260), ("hat", -40), ("tip", 110), ("hair", -70)])
            emit("straw", a, a + 14, lambda tt, s=rng.uniform(-.4, .4): (1.35 + 1.6 * tt, 5.5 + 1.4 * tt - 4.5 * tt * tt + s * tt),
                 spin=400, grow=(.55, .45))
    wince = cl(sum(tl(i, [(a, 0), (a + 2, 1, "out3"), (a + 8, 0)]) for a in PECKS), 0.0, 1.3)
    shoo = bump(i, 49, 66)
    d["hd"] = 9 * wince + 12 * math.sin((i - 49) * 1.45) * shoo
    d["head_s"] = -.06 * wince
    d["sway"] = 3.2 * wince + ring(i, 50, -4, 1.8, .35) * tl(i, [(72, 1), (82, 0)])
    d["bob"] = -.06 * wince + .1 * shoo
    d["hat_r"] = 3 * wince
    d["hands"] = 34 * shoo
    d["pole"] = .5 * wince + ring(i, 50, .7, 3, .2)
    if i == 51:
        kicks.extend([("hair", 160), ("tip", -180), ("jug", 80)])
        for q in range(3):
            ang = rng.uniform(.3, 2.8)
            emit("straw", 51 + q, 66 + q, lambda tt, a=ang, s=rng.uniform(3, 4.5): (P_HAT[0] + .6 + math.cos(a) * s * tt,
                                                                                   P_HAT[1] - 1.2 + math.sin(a) * s * tt - 6 * tt * tt),
                 spin=480, grow=(.7, .55))
    face(24, "shock"); face(33, "neutral"); face(36, "blink"); face(47, "shock"); face(52, "smug"); face(74, "neutral")


def _slump(d, k):
    """Asleep on his post (the walk-off's last pose and the walk-on's first), by k."""
    d["sway"] += -8 * k; d["lean"] += -5 * k; d["hd"] += 24 * k; d["bob"] += -.26 * k; d["body_s"] += -.06 * k
    d["hat_r"] += 5 * k; d["hat_s"] += -.12 * k; d["brims"] += 7 * k; d["hands"] += -30 * k; d["tip"] += 14 * k
    d["pole"] += .6 * k; d["sag"] += k; d["crow_sq"] += .07 * k


def _enter(d, i, n, rng, emit, face, kicks):
    """1.6 s. Asleep, a snore swelling his chest... he jolts awake - up past upright, hat in the air, eyes wide -
    looks left and right, and settles into the idle. The crow is bounced awake with him."""
    k = tl(i, [(0, 1), (10, 1.04), (14, 1.04), (18, -.22, "out3"), (23, .06), (28, -.02), (33, 0)])
    _slump(d, k)
    d["breath"] = 1.5 * math.sin(2 * math.pi * i / 28) * tl(i, [(12, 1), (16, 0)])
    d["hd"] += tl(i, [(18, 0), (25, -8), (31, 6), (38, 4), (44, 0)])
    d["hat_lift"] = tl(i, [(14, 0), (18, .32, "out3"), (21, .26), (25, 0, "in")])
    d["hat_s"] += tl(i, [(14, 0), (17, .26, "out"), (25, -.14, "in"), (29, 0)])
    d["head_s"] = tl(i, [(14, 0), (17, .09, "out"), (24, -.03), (29, 0)])
    d["hands"] += tl(i, [(14, 0), (18, 50, "out3"), (27, 0)])
    d["swing"] = ring(i, 15, 9, 2.2, .3)
    if i == 15:
        kicks.extend([("tip", 220), ("brim", 150), ("jug", 110), ("hair", 140)])
    face(0, "blink"); face(15, "shock"); face(27, "smug"); face(39, "neutral")
    _, y, sq = hop(i, 16, 24, 0, 0, .3)
    d["crow_y"] = y; d["crow_sq"] += sq
    _flick(d, i, 16, 25, .9)
    d["crow_r"] = tl(i, [(16, 0), (19, 12, "out3"), (24, -4), (30, 0)])


def _exit(d, i, n, rng, emit, face, kicks):
    """1 s. A last stretch up, and he drops asleep on his post: falls, bounces, hangs (the canvas fades over the end)."""
    k = tl(i, [(0, 0), (5, -.12, "out"), (17, 1.1, "in3"), (22, .95, "out"), (27, 1.0), (30, 1.0)])
    _slump(d, k)
    face(4, "blink"); face(7, "neutral"); face(10, "blink")
    if i == 17:
        kicks.extend([("jug", 70), ("hair", -70)])


CHOREO = {"idle": _idle, "enter": _enter, "exit": _exit, "spin": _spin, "spin2": _spin2, "win": _win, "big_win": _big_win,
          "lose": _lose, "anticipate": _anticipate, "anticipation": lambda *a: _anticipate(*a, reps=2),
          "hiccup": _hiccup, "peck": _peck}


def primaries(name, i, n, rng, emit, face, kicks):
    """The clip's main moves at frame i -> the drivers (degrees / units). Secondary motion is added in run_clip."""
    d = drivers()
    CHOREO[name](d, i, n, rng, emit, face, kicks)
    return d


_SPRINGS = dict(head=(3.0, .40), hat=(3.0, .24), hatlift=(3.6, .30), hats=(3.4, .30), tip=(1.6, .16), brim_l=(2.6, .2),
                brim_r=(2.4, .18), hair_l=(2.8, .18), hair_ll=(2.4, .2), hair_r=(3.0, .2), collar=(3.0, .22),
                sleeve_l=(1.7, .25), sleeve_r=(1.8, .25), hand_l=(1.9, .2), hand_r=(1.75, .2), rope=(.8, .075),
                jug=(1.7, .22), belt=(1.9, .15), cuff_l=(2.6, .2), cuff_r=(2.4, .2), crow=(3.2, .38),
                boot_l=(2.0, .2), boot_r=(1.9, .2), leg_l=(1.15, .24), leg_r=(1.3, .26))
_C0, _PV = u(*BONES["crow"][0]), u(*BONES["pole"][0])
_WING_REST = math.degrees(math.atan2(-(BONES["wing_l"][1][1] - BONES["wing_l"][0][1]),
                                     BONES["wing_l"][1][0] - BONES["wing_l"][0][0]))     # the fold's direction (y up)
# a wing's turn from the fold: the near one swings up-left .. left and down, the far one up .. right and down
_WING_L = (135 - _WING_REST - 360, -160 - _WING_REST)
_WING_R = (75 - _WING_REST, -10 - _WING_REST)


def run_clip(name, rng, warm=None):
    """Simulate one clip -> (poses [bone -> channels] per frame, faces {frame: name}, emits [(kind, f0, f1, path..)])."""
    n, loop = CLIPS[name]
    nf = n if loop else n + 1
    emits, faces = [], {}

    def emit(kind, fs, fe, path, spin=0.0, grow=(1, 1)):
        emits.append((kind, fs, fe, path, spin, grow, rng.uniform(0, 360)))

    def face(i, nm):
        faces[i] = nm

    face(0, "neutral")
    S = {k: Spring(f, z) for k, (f, z) in _SPRINGS.items()}
    if warm:
        for k, (x, v) in warm.items():
            S[k].x, S[k].v = x, v
    poses = []
    prev = None
    winds = [0.0] * 12
    flaps = [0.0, 0.0]
    for i in range(nf):
        kicks = []
        d = primaries(name, i, n, rng, emit, face, kicks)
        for what, dv in kicks:                                     # impulses
            if what in ("hat", "tip"):
                S[what].kick(dv)
            elif what == "jug":
                S["rope"].kick(dv)
            elif what == "brim":
                S["brim_l"].kick(-dv); S["brim_r"].kick(dv)
            elif what == "brim_r":
                S["brim_r"].kick(dv); S["brim_l"].kick(-.3 * dv)
            elif what == "hair":
                for h in ("hair_l", "hair_ll", "hair_r"):
                    S[h].kick(dv * (1 if h != "hair_r" else -1))
        winds = [d["wind"]] + winds[:-1]                           # a breeze reaches each part a little later
        flaps = [d["flap"]] + flaps[:-1]
        tr = d["tremble"]                                          # the shiver: three rates, whole cycles in 12 frames
        sh1, sh2, sh3 = math.sin(2 * math.pi * i / 3), math.sin(2 * math.pi * i / 4 + 1), math.sin(2 * math.pi * i / 6 + 2)
        pole = d["pole"] + .22 * tr * sh1
        bob = d["bob"] + .012 * tr * sh2
        # body
        head_l = S["head"].step(d["hd"] + .3 * d["sway"]) + 1.0 * tr * sh2    # the head lags the body (its own angle)
        head_w = .7 * pole + d["sway"] + d["lean"] + head_l                   # ... and on screen
        torso_w = d["sway"] + d["lean"] + pole
        hips_w = .7 * pole + d["sway"]
        if prev is None:
            prev = dict(head_w=head_w, torso_w=torso_w, bob=bob, bobv=0.0, ll=0.0, lr=0.0, rope=0.0)
        head_v = cl((head_w - prev["head_w"]) * FPS, -420.0, 420.0)           # deg/s
        torso_v = cl((torso_w - prev["torso_w"]) * FPS, -300.0, 300.0)
        bob_v = (bob - prev["bob"]) * FPS
        bob_a = cl((bob_v - prev["bobv"]) * FPS, -70.0, 70.0)                 # units/s2
        # the hat sits on the head with its own inertia: it lags the head's turns, lifts off on the jolts (the
        # forehead under it stretches - fine for the few frames of a pop), squashes when it lands
        hat = cl(S["hat"].step(d["hat_r"] - .012 * head_v), -9.0, 9.0)
        lift = cl(S["hatlift"].step(d["hat_lift"] - .0005 * bob_a), -.03, .46)
        hs = cl(S["hats"].step(d["hat_s"]), -.26, .4)
        tip = cl(S["tip"].step(-.10 * head_v - .8 * hat + 5 * bob + 14 * lift + d["tip"] + 5 * winds[4]) + 3 * tr * sh3, -40.0, 40.0)
        brim_l = cl(S["brim_l"].step(.10 * bob_a - .02 * head_v + d["brims"] + 3 * winds[3]) + 1.5 * tr * sh1, -16.0, 16.0)
        brim_r = cl(S["brim_r"].step(-.10 * bob_a - .02 * head_v - d["brims"] - 3 * winds[6]) + 1.5 * tr * sh3, -18.0, 18.0)
        hair_l = cl(S["hair_l"].step(-.06 * head_v + 7 * winds[2]) + 2 * tr * sh3, -22.0, 22.0)
        hair_ll = cl(S["hair_ll"].step(-.05 * head_v + 6 * winds[3]) + 2 * tr * sh1, -20.0, 20.0)
        hair_r = cl(S["hair_r"].step(-.06 * head_v - 7 * winds[6]) + 2 * tr * sh2, -22.0, 22.0)
        collar = cl(S["collar"].step(-.04 * torso_v - .05 * bob_a + 5 * winds[5]) + 1.5 * tr * sh1, -18.0, 18.0)
        sl_l = S["sleeve_l"].step(-.02 * torso_v + 8 * bob + 10 * d["sag"])
        sl_r = S["sleeve_r"].step(.02 * torso_v + 8 * bob + 10 * d["sag"])
        # the straw hands: positive droops them, the hands driver throws them up
        hl = cl(S["hand_l"].step(.5 * d["sway"] + 20 * bob - d["hands"] - d["hand_l"] + 10 * winds[0]) + 7 * tr * sh1, -85.0, 60.0)
        hr = cl(S["hand_r"].step(-.5 * d["sway"] + 20 * bob - d["hands"] - d["hand_r"] + 10 * winds[9]) + 7 * tr * sh2, -85.0, 60.0)
        # the jug: a pendulum off the wrist - it hangs plumb as the post leans, swings on from every jolt, and the
        # jug itself trails its rope
        rope = cl(S["rope"].step(-.6 * d["sway"] - 1.2 * pole) + d["jug"] + 2 * tr * sh2, -10.0, 34.0)   # (further out left it leaves his box)
        jug = cl(S["jug"].step(.5 * rope - .03 * (rope - prev["rope"]) * FPS), -6.0, 22.0)
        belt = cl(S["belt"].step(-.06 * torso_v - 1.2 * d["sway"] + 6 * winds[6]) + 2 * tr * sh3, -30.0, 30.0)
        # the legs hang off the hips: they trail the body's swings and overshoot (each at its own rate), under the kicks
        ll = S["leg_l"].step(-.72 * hips_w) + d["swing"] + d["legs"] + 2.2 * tr * sh3
        lr = S["leg_r"].step(-.72 * hips_w) + d["swing"] - .8 * d["legs"] - 2.2 * tr * sh3
        if abs(ll - lr) > 15:                                      # (the trouser legs tear if they part further)
            m, h = (ll + lr) / 2, (7.5 if ll > lr else -7.5)
            ll, lr = m + h, m - h
        ll_v, lr_v = (ll - prev["ll"]) * FPS, (lr - prev["lr"]) * FPS
        cuff_l = cl(S["cuff_l"].step(-.035 * ll_v + 4 * winds[7]) + 1.5 * tr * sh2, -9.0, 9.0)
        cuff_r = cl(S["cuff_r"].step(-.035 * lr_v + 4 * winds[8]) + 1.5 * tr * sh1, -9.0, 9.0)
        # each boot dangles off its leg: it hangs back toward plumb as the leg swings out, lags and overshoots
        boot_l = cl(S["boot_l"].step(-.45 * (hips_w + ll)), -14.0, 14.0)
        boot_r = cl(S["boot_r"].step(-.45 * (hips_w + lr)), -14.0, 14.0)
        prev = dict(head_w=head_w, torso_w=torso_w, bob=bob, bobv=bob_v, ll=ll, lr=lr, rope=rope)
        # the crow: on the bar it rides the post; in the air (crow_free) it is placed on screen, clear of the rocking
        cx, cy = d["crow_x"], d["crow_y"]
        cr = S["crow"].step(d["crow_r"]) + d["crow_hit"] - 2.5 * tr * sh2
        if d["crow_free"] > 0:
            th = math.radians(pole)
            wx, wy = _C0[0] + cx - _PV[0], _C0[1] + cy - _PV[1]
            fx_ = math.cos(th) * wx + math.sin(th) * wy + _PV[0] - _C0[0]
            fy_ = -math.sin(th) * wx + math.cos(th) * wy + _PV[1] - _C0[1]
            f = d["crow_free"]
            cx, cy, cr = cx + (fx_ - cx) * f, cy + (fy_ - cy) * f, cr - pole * f
        sq = d["crow_sq"]
        # its wings: folded behind it at rest (identity); open = a turn from the fold up to the stroke, and bigger
        op = cl(d["wing"], 0.0, 1.0)
        fl, fr = flaps[0], flaps[1]                                # the far wing a frame behind
        wl = op * (_WING_L[1] + (_WING_L[0] - _WING_L[1]) * (.5 + .5 * fl))
        wr = op * (_WING_R[1] + (_WING_R[0] - _WING_R[1]) * (.5 + .5 * fr))
        sl, sr = 1 + .5 * op, 1 + .75 * op
        pose = {
            "pole": dict(r=pole),
            "hips": dict(r=d["sway"] - pole * .3, y=bob, sx=1 - .5 * d["body_s"], sy=1 + d["body_s"]),
            "chest": dict(r=d["lean"], sx=1 + .5 * d["chest_s"] + .007 * d["breath"], sy=1 + d["chest_s"] + .016 * d["breath"]),
            "head": dict(r=head_l, sx=1 - .6 * d["head_s"], sy=1 + d["head_s"]),
            "hat": dict(r=hat, y=lift, sx=1 - .4 * hs, sy=1 + hs),
            "hat_tip": dict(r=tip),
            "brim_l": dict(r=brim_l),
            "brim_r": dict(r=brim_r),
            "hair_l": dict(r=hair_l), "hair_ll": dict(r=hair_ll), "hair_r": dict(r=hair_r),
            "collar": dict(r=collar),
            "sleeve_l": dict(r=-sl_l * .5), "sleeve_r": dict(r=sl_r * .5),
            "rope": dict(r=rope), "jug": dict(r=jug),
            "hand_l": dict(r=hl), "hand_r": dict(r=-hr),
            "belt": dict(r=belt),
            "leg_l": dict(r=ll), "leg_r": dict(r=lr),
            "cuff_l": dict(r=cuff_l), "cuff_r": dict(r=cuff_r),
            "boot_l": dict(r=boot_l), "boot_r": dict(r=boot_r),
            "crow": dict(x=cx, y=cy, r=cr, sx=d["crow_flip"] * (1 + sq), sy=1 - .6 * sq),
            "wing_l": dict(r=wl, sx=sl, sy=sl * (1 - .16 * op * (1 - abs(fl)))),
            "wing_r": dict(r=wr, sx=sr, sy=sr * (1 - .16 * op * (1 - abs(fr)))),
        }
        poses.append(pose)
    state = {k: (s.x, s.v) for k, s in S.items()}
    return poses, faces, emits, state


def fade_pose(pose, k):
    """Scale a pose's offsets from rest by k (k=0: the rest pose). The crow's flip is left alone."""
    out = {}
    for b, ch in pose.items():
        c = {}
        for key_, v in ch.items():
            if key_ in ("sx", "sy", "s"):
                if b == "crow" and key_ == "sx":
                    sgn = 1.0 if v >= 0 else -1.0
                    c[key_] = sgn * (1 + (abs(v) - 1) * k)
                else:
                    c[key_] = 1 + (v - 1) * k
            else:
                c[key_] = v * k
        out[b] = c
    return out


def add_pose(pose, corr, k):
    """pose + k * corr, channel by channel."""
    return {b: {c: pose[b][c] + corr[b].get(c, 0.0) * k for c in pose[b]} for b in pose}


def clip_poses(name, rng):
    """The finished clip: springs simulated, loops made seamless, one-shots settled exactly onto rest."""
    n, loop = CLIPS[name]
    if loop:
        # run the loop three times so the springs settle into its rhythm, keep the last pass, and fold the tiny
        # remaining mismatch at the seam out over the loop's last quarter
        warm = None
        for _ in range(3):
            poses, faces, emits, warm = run_clip(name, random.Random(5), warm)
        first = poses[0]
        nxt, _, _, _ = run_clip(name, random.Random(5), warm)
        seam = nxt[0]                                               # what the next pass would show at frame 0
        corr = {b: {c: first[b][c] - seam[b][c] for c in first[b]} for b in first}
        K = n // 4
        for j in range(K):
            poses[n - K + j] = add_pose(poses[n - K + j], corr, ease((j + 1) / K))
        return poses, faces, emits
    poses, faces, emits, _ = run_clip(name, rng)
    if name in HOLD:
        # the held middle repeats: its last frame is made its first exactly (the springs' leftover folded out over
        # the cycle's second half, and faded off again over the first frames of the release)
        a, b = HOLD[name]
        corr = {bn: {c: poses[a][bn][c] - poses[b][bn][c] for c in poses[a][bn]} for bn in poses[a]}
        K = (b - a) // 2
        for j in range(1, K + 1):
            poses[b - K + j] = add_pose(poses[b - K + j], corr, ease(j / K))
        for j in range(1, 9):
            if b + j <= n:
                poses[b + j] = add_pose(poses[b + j], corr, 1 - ease(j / 8))
    if name != "exit":
        K = 10
        for j in range(K + 1):
            i = n - K + j
            poses[i] = fade_pose(poses[i], 1 - ease(j / K))
    return poses, faces, emits


# ---------------------------------------------------------------- Blender keys

def key_clip(arm, body, fx, name, f0, rng, used):
    n, loop = CLIPS[name]
    poses, faces, emits = clip_poses(name, rng)
    for i, pose in enumerate(poses):
        key(arm, f0 + i, pose)
    for i, nm in sorted(faces.items()):
        key_face(body, f0 + i, nm)
    if not loop:
        key_face(body, f0 + n, "neutral")
    for kind, fs, fe, path, spin, grow, r0 in emits:
        obs = fx[kind]
        ob = obs[used[kind] % len(obs)]
        used[kind] += 1
        set_fade(ob, f0 + fs - 1, 0.0)
        for f in range(fs, fe + 1):
            t = (f - fs) / max(1, fe - fs)
            x, z = path(t)
            ob.location = (x, ob.location.y, z)
            g = grow[0] + (grow[1] - grow[0]) * t
            ob.scale = (g, 1, g)
            ob.rotation_euler = (0, math.radians(r0 + spin * t), 0)
            ob.keyframe_insert("location", frame=f0 + f)
            ob.keyframe_insert("scale", frame=f0 + f)
            ob.keyframe_insert("rotation_euler", frame=f0 + f)
            set_fade(ob, f0 + f, min(1.0, 4 * t, 4 * (1 - t) + .001) if kind != "bubble" else (1.0 if t < .85 else 0.0))
        set_fade(ob, f0 + fe + 1, 0.0)
    return n


def finish_curves():
    def fcs(act):
        try:
            return list(act.fcurves)
        except AttributeError:
            return [fc for L in act.layers for s in L.strips for cb in s.channelbags for fc in cb.fcurves]

    for idb in list(bpy.data.objects) + [m.node_tree for m in bpy.data.materials if m.node_tree]:
        ad = idb.animation_data
        if not (ad and ad.action):
            continue
        for fc in fcs(ad.action):
            const = fc.data_path.endswith("default_value") and getattr(idb, "name", "") != "" and \
                any(n.name == "face" for n in getattr(idb, "nodes", []))
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT" if const else "LINEAR"


STARTS = {}


def animate(arm, body, fx, clips):
    rng = random.Random(1123)
    used = {k: 0 for k in fx}
    f = 1
    for c in CLIPS:
        STARTS[c] = f
        n = key_clip(arm, body, fx, c, f, rng, used) if c in clips else CLIPS[c][0]
        f += n + 20
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, f
    finish_curves()


def render(clips, only=None):
    sc = bpy.context.scene
    ren = os.path.join(OUT, "renders")
    for c in clips:
        n, loop = CLIPS[c]
        d = os.path.join(ren, c)
        os.makedirs(d, exist_ok=True)
        if only is None:
            for old in os.listdir(d):
                os.remove(os.path.join(d, old))
        for k in (only if only is not None else range(n if loop else n + 1)):
            sc.frame_set(STARTS[c] + k)
            sc.render.filepath = os.path.join(d, f"{k:04d}.png")
            bpy.ops.render.render(write_still=True)


def write_meta():
    """What pack_chars.py reads: frame size, standing height, ground line, the clips."""
    top = (H_PX / 2 - TOP_Y) / 100
    base = (H_PX / 2 - GROUND_Y) / 100
    cy = RES[1] / 2
    meta = {"fps": FPS, "size": list(RES), "rest_height_px": round((top - base) * PX, 1),
            "ground_y": round(cy - base * PX, 1),
            "clips": {c: {"frames": (n if loop else n + 1), "loop": loop} for c, (n, loop) in CLIPS.items()}}
    os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
    json.dump(meta, open(os.path.join(OUT, "renders", "meta.json"), "w"), indent=1)


def build_all(clips):
    arm, body, fx = build()
    animate(arm, body, fx, clips)
    return arm, body, fx


if __name__ == "__main__" and "--" in sys.argv and bpy is not None:
    args = sys.argv[sys.argv.index("--") + 1:]
    steps = (args[0] if args else "build,render").split(",")
    clips = args[1].split(",") if len(args) > 1 and args[1] != "all" else list(CLIPS)
    only = [int(v) for v in args[2].split(",")] if len(args) > 2 else None
    build_all(list(CLIPS))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scarecrow.blend"))
    write_meta()
    if "render" in steps or "frames" in steps:
        render(clips, only)
    print("DONE scarecrow", clips)
