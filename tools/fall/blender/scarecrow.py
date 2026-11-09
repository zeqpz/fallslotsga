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

CLIPS = {          # frames, loop  (lengths are what CHAR_SFX in index.html is timed against - keep them)
    "idle": (240, True), "enter": (44, False), "exit": (30, False), "anticipation": (54, False),
    "win": (96, False), "big_win": (132, False), "lose": (90, False), "hiccup": (72, False), "peck": (84, False),
}


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
    # effect sprites: hiccup bubbles, straw bits, leaves, feathers, sparkles - farm, not glitter
    fx = {}
    for kind, n, size in (("bubble", 6, 0.8), ("straw", 14, 1.0), ("leaf_red", 5, 1.1), ("leaf_orange", 5, 1.1),
                          ("leaf_gold", 5, 1.1), ("feather", 8, 0.9), ("sparkle", 8, 0.9)):
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

def primaries(name, i, n, rng, emit, face, kicks):
    """The clip's main moves at frame i -> dict of drivers (degrees / units). Secondary motion is added in run_clip."""
    t, p = i / FPS, i / n
    d = dict(sway=0.0, lean=0.0, hd=0.0, bob=0.0, legs=0.0, chest_s=0.0, breath=0.0, pole=0.0,
             crow_x=0.0, crow_y=0.0, crow_r=0.0, crow_hit=0.0, crow_flip=1.0, crow_sq=0.0, hat_lift=0.0)
    if name == "idle":
        # the drunk sway: slow incommensurate waves that repeat exactly over the 8 s loop
        a = 2 * math.pi * p
        d["sway"] = 3.2 * math.sin(a) + 1.4 * math.sin(3 * a + 1.1) - 1.4 * math.sin(1.1)
        d["lean"] = 2.0 * math.sin(2 * a + .4) - 2.0 * math.sin(.4)
        d["bob"] = .04 * math.sin(4 * a)
        d["breath"] = math.sin(2 * a)                              # two slow breaths a loop
        nod = bump(p, .52, .72)                                    # nods off... and jerks awake
        d["hd"] = (-6 * math.sin(a - .3) + 6 * math.sin(-.3) + 3 * math.sin(2 * a) + 9 * nod ** 1.5
                   - 5 * bump(p, .70, .76))
        d["legs"] = 3 * math.sin(a + .5) - 3 * math.sin(.5)
        d["pole"] = .5 * math.sin(a + .9) - .5 * math.sin(.9)     # the post creaks with him
        if i == int(.705 * n):
            kicks.append(("hat", 60)); kicks.append(("tip", -120))
        # the crow: little hops on the spot, a look round (turns its head = a quick flip and back)
        for h0 in (.12, .16, .62):
            x, y, sq = hop(i, int(h0 * n), int(h0 * n) + 5, 0, 0, .07)
            d["crow_y"] += y; d["crow_sq"] += sq
        lk = bump(p, .33, .45)
        d["crow_flip"] = 1 - 2 * ease(min(1, lk * 3))              # looks the other way, then back
        d["crow_r"] = 8 * bump(p, .8, .86)
        for b0 in (58, 171):
            for k in range(4):
                face(b0 + k, "blink")
            face(b0 + 4, "neutral")
        face(int(.56 * n), "blink"); face(int(.705 * n), "shock"); face(int(.705 * n) + 8, "neutral")
    elif name == "enter":
        # wakes up: slumped asleep, snaps up with a jolt (the hat jumps on his head), settles
        k = ease(p / .5)
        d["sway"] = -10 * (1 - k) + 3 * bump(p, .5, .8)
        d["lean"] = -6 * (1 - k)
        d["hd"] = 24 * (1 - k) - 7 * bump(p, .42, .72)
        d["bob"] = -.25 * (1 - k) + .12 * bump(p, .45, .65)
        d["pole"] = -1.2 * bump(p, .4, .7)
        d["hat_lift"] = .06 * bump(p, .42, .62)
        if i == int(.45 * n):
            kicks.extend([("hat", -90), ("tip", 200), ("brim", 120), ("jug", 60), ("hair", 120)])
        face(0, "blink"); face(int(n * .45), "shock"); face(int(n * .8), "neutral")
    elif name == "exit":
        k = ease(p / .8)
        d["sway"], d["lean"], d["hd"], d["bob"] = -10 * k, -6 * k, 24 * k, -.25 * k
        face(int(n * .3), "blink")
    elif name == "anticipation":
        e = env(i, n, 6, 16)
        d["sway"] = 1.5 * math.sin(t * 30) * e * .4
        d["lean"] = 4 * e
        d["chest_s"] = .04 * e
        d["hd"] = -8 * e + 2 * math.sin(t * 40) * e
        d["bob"] = .15 * e
        d["pole"] = .25 * math.sin(t * 34) * e                    # trembling on his post
        x, y, sq = hop(i, 4, 12, 0, 0, .3)
        d["crow_y"] = y + .1 * e; d["crow_sq"] = sq + .08 * e
        if i in (6, 20, 34):
            kicks.append(("tip", 60 if i != 20 else -60))
        face(4, "shock"); face(n - 10, "neutral")
    elif name == "win":
        e = env(i, n, 8, 18)
        w = 2 * math.pi * 2.2
        beat = math.sin(t * w)                                    # a bouncy little drunk dance
        d["sway"] = 7 * beat * e
        d["lean"] = 3 * math.sin(t * w / 2) * e
        d["bob"] = .18 * abs(beat) * e
        d["hd"] = -9 * math.sin(t * w + .6) * e
        d["legs"] = 8 * math.sin(t * w + 1.0) * e
        d["pole"] = .8 * beat * e
        d["crow_y"] = .2 * abs(math.sin(t * w)) * e
        d["crow_sq"] = -.06 * math.cos(2 * t * w) * e
        face(3, "happy"); face(n - 12, "neutral")
        if i in (20, 44, 68):
            emit("sparkle", i, i + 14, lambda tt, x0=rng.uniform(-3, 1): (x0, 3.5 + 2 * tt), spin=120, grow=(.4, .1))
    elif name == "big_win":
        e = env(i, n, 8, 22)
        w = 2 * math.pi * 2.8
        beat = math.sin(t * w)
        d["sway"] = 11 * beat * e
        d["lean"] = 5 * math.sin(t * w / 2) * e
        d["bob"] = .3 * abs(beat) * e
        d["hd"] = -16 * math.sin(t * w + .7) * e
        d["legs"] = 12 * math.sin(t * w + 1.2) * e
        d["chest_s"] = .05 * abs(beat) * e
        d["pole"] = 1.6 * beat * e
        d["hat_lift"] = .05 * max(0, math.sin(t * w * 2)) * e     # the hat hops on his head to the beat
        # the crow flies up off the bar in fright, flapping, and comes back
        fly = bump(p, .08, .75)
        d["crow_y"] = 2.6 * fly ** .8
        d["crow_x"] = .6 * math.sin(p * 9) * fly
        d["crow_r"] = 15 * math.sin(t * 30) * fly
        d["crow_sq"] = .22 * math.sin(t * 52) * fly                # wing-beats as a squash and stretch
        face(3, "cheer"); face(n - 16, "happy"); face(n - 6, "neutral")
        if i % 6 == 0 and 8 < i < n - 30:
            ang = rng.uniform(.3, 2.8)
            sp = rng.uniform(4, 7)
            emit("straw", i, i + 18, lambda tt, a=ang, s=sp: (.2 + math.cos(a) * s * tt, 1.5 + math.sin(a) * s * tt
                                                              - 9 * tt * tt), spin=500, grow=(.8, .7))
        if i % 9 == 4 and 8 < i < n - 30:
            kind = ("leaf_red", "leaf_orange", "leaf_gold")[(i // 9) % 3]
            x0 = rng.uniform(-4, 4)
            emit(kind, i, i + 26, lambda tt, x0=x0: (x0 + 1.2 * math.sin(tt * 7), 7.5 - 6 * tt), spin=300, grow=(.8, .7))
        if i in (12, 30, 50, 70):
            for k in range(2):
                x0 = rng.uniform(2.4, 4)
                emit("feather", i + k * 3, i + 34, lambda tt, x0=x0: (x0 + .6 * math.sin(tt * 8), 4.2 + 1.2 - 5 * tt),
                     spin=200, grow=(.9, .8))
    elif name == "lose":
        e = env(i, n, 14, 24)
        d["sway"] = -6 * e
        d["lean"] = -7 * e
        d["hd"] = 20 * e + 3 * math.sin(t * 9) * bump(p, .2, .5)
        d["bob"] = -.22 * e
        d["legs"] = -2 * e
        d["breath"] = -1.6 * bump(p, .32, .62)                    # a long sigh: chest sinks
        d["pole"] = -.6 * e
        hic = bump(p, .7, .76)
        d["bob"] += .25 * hic
        if i == int(.7 * n):
            kicks.extend([("hat", 80), ("jug", 70), ("tip", -140)])
        face(4, "sad"); face(int(n * .7), "hiccup"); face(int(n * .78), "neutral")
    elif name == "hiccup":
        jolt = 0.0
        for h0 in (.12, .42, .72):
            jolt += bump(p, h0, h0 + .08)
            if i == int(h0 * n) + 1:
                kicks.extend([("hat", 70), ("tip", -150), ("brim", 140), ("jug", 80), ("hair", 90)])
        e = env(i, n, 6, 12)
        d["sway"] = 2 * math.sin(t * 5) * e
        d["bob"] = .35 * jolt
        d["hd"] = -7 * jolt + 4 * math.sin(t * 3) * e
        d["chest_s"] = .06 * jolt
        d["hat_lift"] = .04 * jolt
        d["pole"] = .4 * jolt
        for h0 in (.12, .42, .72):
            a0 = int(h0 * n)
            face(a0, "hiccup"); face(a0 + 7, "smug" if h0 > .5 else "neutral")
            emit("bubble", a0 + 2, a0 + 26, lambda tt, s=rng.uniform(-.3, .3): (.6 + s + .35 * math.sin(tt * 9), 3.6 + 3 * tt),
                 grow=(.45, 1.0))
        face(n - 8, "neutral")
    elif name == "peck":
        # the crow hops down the arm towards him, turns, pecks the brim of his hat three times (the brim jerks and
        # flops with each), he flinches, glares, shakes it off; the crow caws, hops back and turns round
        x, y, sq = hop(i, 3, 10, 0, -.55, .22)
        x2, y2, sq2 = hop(i, 12, 18, -.55, -1.0, .18)
        x3, y3, sq3 = hop(i, 59, 66, -1.0, -.55, .24)
        x4, y4, sq4 = hop(i, 69, 76, -.55, 0, .2)
        if i < 12:
            d["crow_x"], d["crow_y"], d["crow_sq"] = x, y, sq
        elif i < 59:
            d["crow_x"], d["crow_y"], d["crow_sq"] = x2, y2, sq2
        elif i < 69:
            d["crow_x"], d["crow_y"], d["crow_sq"] = x3, y3, sq3
        else:
            d["crow_x"], d["crow_y"], d["crow_sq"] = x4, y4, sq4
        turn = ease((i - 10) / 3) - ease((i - 66) / 3)              # faces him (flipped) from 10..13 to 66..69
        d["crow_flip"] = 1 - 2 * turn
        lean_in = bump(p, .2, .62) ** .6
        peck = sum(pulse(i, a, a + 6) for a in (23, 34, 45))      # the hits, on the CHAR_SFX crowPeck cues
        wind = sum(bump(i, a - 4, a + .01) for a in (23, 34, 45))   # the wind-up before each
        # it pecks the brim's edge (level with its beak): a lunge forward and up on its toes, not a bow (a bow
        # put the beak in his cheek)
        d["crow_r"] = 5 * lean_in * turn
        d["crow_hit"] = (9 * peck - 6 * wind) * turn                # right on the cue (no spring lag)
        d["crow_x"] += (-.22 * peck + .06 * wind) * turn
        d["crow_y"] += .05 * peck
        for a in (23, 34, 45):
            if i == a:
                kicks.extend([("brim_r", -200), ("hat", -25), ("tip", 90)])
        caw = bump(i, 56, 62)
        d["crow_sq"] += -.15 * caw
        d["hd"] = -9 * sum(pulse(i, a, a + 9) for a in (23, 34, 45)) - 4 * bump(p, .6, .9)
        shoo = bump(i, 56, 70)
        d["hd"] += 7 * math.sin((i - 56) * 1.3) * shoo               # shakes his head at it
        d["sway"] = -3 * sum(pulse(i, a, a + 9) for a in (23, 34, 45)) + 4 * shoo
        d["bob"] = .08 * peck
        if i == 58:
            kicks.extend([("hair", 140), ("tip", -150)])
        if i in (24, 35, 46):
            emit("straw", i, i + 14, lambda tt, s=rng.uniform(-.4, .4): (1.35 + 1.6 * tt, 5.5 + 1.4 * tt - 4.5 * tt * tt + s * tt),
                 spin=400, grow=(.55, .45))
        face(int(n * .25), "shock"); face(int(n * .58), "smug"); face(n - 10, "neutral")
    return d


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
    S = dict(head=Spring(2.0, .32), hat=Spring(3.2, .26), tip=Spring(1.5, .16), brim_l=Spring(2.6, .2),
             brim_r=Spring(2.4, .18), hair_l=Spring(2.8, .18), hair_ll=Spring(2.4, .2), hair_r=Spring(3.0, .2),
             collar=Spring(3.0, .22), sleeve_l=Spring(1.7, .25), sleeve_r=Spring(1.8, .25), hand_l=Spring(1.6, .18),
             hand_r=Spring(1.5, .18), jug=Spring(.85, .09), belt=Spring(1.9, .15), cuff_l=Spring(2.6, .2),
             cuff_r=Spring(2.4, .2), crow=Spring(3.2, .38), hatlift=Spring(4.0, .35),
             boot_l=Spring(2.0, .2), boot_r=Spring(1.9, .2))
    if warm:
        for k, (x, v) in warm.items():
            S[k].x, S[k].v = x, v
    poses = []
    prev = None
    for i in range(nf):
        kicks = []
        d = primaries(name, i, n, rng, emit, face, kicks)
        # impulses
        for what, dv in kicks:
            if what == "hat":
                S["hat"].kick(dv)
            elif what == "tip":
                S["tip"].kick(dv)
            elif what == "brim":
                S["brim_l"].kick(-dv); S["brim_r"].kick(dv)
            elif what == "brim_r":
                S["brim_r"].kick(dv); S["brim_l"].kick(-.3 * dv)
            elif what == "jug":
                S["jug"].kick(dv)
            elif what == "hair":
                for h in ("hair_l", "hair_ll", "hair_r"):
                    S[h].kick(dv * (1 if h != "hair_r" else -1))
        # body
        head_l = S["head"].step(d["hd"] + .6 * d["sway"])         # the head lags the body (its own angle)
        head_w = .7 * d["pole"] + d["sway"] + d["lean"] + head_l  # ... and on screen
        torso_w = d["sway"] + d["lean"] + d["pole"]
        if prev is None:
            prev = dict(head_w=head_w, torso_w=torso_w, bob=d["bob"], bobv=0.0, legs=d["legs"])
        head_v = (head_w - prev["head_w"]) * FPS                   # deg/s
        torso_v = (torso_w - prev["torso_w"]) * FPS
        bob_v = (d["bob"] - prev["bob"]) * FPS
        bob_a = (bob_v - prev["bobv"]) * FPS
        legs_v = (d["legs"] - prev["legs"]) * FPS
        prev = dict(head_w=head_w, torso_w=torso_w, bob=d["bob"], bobv=bob_v, legs=d["legs"])
        # the hat sits on the head but has its own inertia: it lags the head's turns, bounces on the bobs
        # (small: the hat turns about its band, so a big angle would stretch the forehead under it)
        hat = S["hat"].step(-.012 * head_v)
        hat = max(-2.5, min(2.5, hat))
        lift = S["hatlift"].step(d["hat_lift"] - .0006 * bob_a)
        lift = max(-.02, min(.06, lift))
        tip = S["tip"].step(-.10 * head_v - .6 * hat + 4 * d["bob"])   # the floppy tip trails everything
        tip = max(-24.0, min(24.0, tip))
        brim_l = max(-8.0, min(8.0, S["brim_l"].step(.004 * bob_a - .02 * head_v)))
        brim_r = max(-12.0, min(12.0, S["brim_r"].step(-.004 * bob_a - .02 * head_v)))
        hair_l = max(-15.0, min(15.0, S["hair_l"].step(-.06 * head_v)))
        hair_ll = max(-12.0, min(12.0, S["hair_ll"].step(-.05 * head_v)))
        hair_r = max(-15.0, min(15.0, S["hair_r"].step(-.06 * head_v)))
        collar = S["collar"].step(-.04 * torso_v - .003 * bob_a)
        sl_l = S["sleeve_l"].step(-.02 * torso_v + 6 * d["bob"])
        sl_r = S["sleeve_r"].step(-.02 * torso_v - 6 * d["bob"])
        hl = S["hand_l"].step(.8 * d["sway"] + 30 * d["bob"])
        hr = S["hand_r"].step(.8 * d["sway"] - 30 * d["bob"])
        jv = S["jug"].step(-1.4 * d["sway"] - 1.2 * d["pole"] + (35 * d["bob"] if name in ("win", "big_win") else 0))
        jv = max(-14.0, min(14.0, jv))
        belt = S["belt"].step(-.06 * torso_v - 1.2 * d["sway"])
        # (the cuffs' straw lies over the boots' tops now: a smaller flutter, so it never lifts off them)
        cuff_l = max(-6.0, min(6.0, S["cuff_l"].step(-.03 * legs_v)))
        cuff_r = max(-6.0, min(6.0, S["cuff_r"].step(.03 * legs_v)))
        # each boot dangles off its leg: it hangs back toward plumb as the leg swings out, lags and overshoots
        leg_wl = .7 * d["pole"] + .5 * d["sway"] + d["legs"]          # the legs' angles on screen
        leg_wr = .7 * d["pole"] + .5 * d["sway"] - .8 * d["legs"]
        boot_l = max(-9.0, min(9.0, S["boot_l"].step(-.45 * leg_wl)))
        boot_r = max(-9.0, min(9.0, S["boot_r"].step(-.45 * leg_wr)))
        cr = S["crow"].step(d["crow_r"]) + d["crow_hit"]
        chest_sy = 1 + d["chest_s"] + .012 * d["breath"]
        chest_sx = 1 + .5 * d["chest_s"] + .006 * d["breath"]
        sq = d["crow_sq"]
        pose = {
            "pole": dict(r=d["pole"]),
            "hips": dict(r=d["sway"] - d["pole"] * .3, y=d["bob"]),
            "chest": dict(r=d["lean"], sx=chest_sx, sy=chest_sy),
            "head": dict(r=head_l),
            "hat": dict(r=hat, y=lift),
            "hat_tip": dict(r=tip),
            "brim_l": dict(r=brim_l),
            "brim_r": dict(r=brim_r),
            "hair_l": dict(r=hair_l), "hair_ll": dict(r=hair_ll), "hair_r": dict(r=hair_r),
            "collar": dict(r=collar),
            "sleeve_l": dict(r=-sl_l * .5), "sleeve_r": dict(r=sl_r * .5),
            "rope": dict(r=jv), "jug": dict(r=.45 * jv),
            "hand_l": dict(r=hl), "hand_r": dict(r=-hr),
            "belt": dict(r=belt),
            "leg_l": dict(r=d["legs"] - .5 * d["sway"]), "leg_r": dict(r=-d["legs"] * .8 - .5 * d["sway"]),
            "cuff_l": dict(r=cuff_l), "cuff_r": dict(r=cuff_r),
            "boot_l": dict(r=boot_l), "boot_r": dict(r=boot_r),
            "crow": dict(x=d["crow_x"], y=d["crow_y"], r=cr, sx=d["crow_flip"] * (1 + sq), sy=1 - .6 * sq),
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


def lerp_pose(a, b, k):
    out = {}
    for bn in a:
        out[bn] = {key_: a[bn].get(key_, 0.0 if key_ not in ("sx", "sy", "s") else 1.0) * (1 - k) +
                   b[bn].get(key_, 0.0 if key_ not in ("sx", "sy", "s") else 1.0) * k for key_ in set(a[bn]) | set(b[bn])}
    return out


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
        K = n // 4
        for j in range(K):
            i = n - K + j
            k = ease((j + 1) / K)
            # blend toward a pose that continues into frame 0 seamlessly
            corr = {b: {c: (first[b].get(c, 0) - seam[b].get(c, 0)) for c in first[b]} for b in first}
            poses[i] = {b: {c: poses[i][b].get(c, 0) + corr[b][c] * k for c in poses[i][b]} for b in poses[i]}
        return poses, faces, emits
    poses, faces, emits, _ = run_clip(name, rng)
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
