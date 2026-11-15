"""The scarecrow as separate cut-out parts: the 2D rig and its animation, in pure Python (no Blender).

The parts are the pictures tools/fall/cut_scare_parts.py wrote (art/fall-src/scare_parts/parts + parts.json: each
part's place on the 1024 x 1536 art frame). The CHOREOGRAPHY is the skinned-mesh rig's own: this imports
tools/fall/blender/scarecrow.py and takes every clip from its clip_poses() (the timelines, springs, faces, effect
sprites, the tease's HOLD) - only the skeleton it drives is new:

  - every bone is a rigid 2D transform; a child inherits its parent's ROTATION and its attachment point (which rides
    the parent's squash), never the squash itself: a bone's sx / sy stretch its own picture only, so nothing shears
  - the sleeves are pinned at the wrist (tied to the crossbar) and aimed at the chest's shoulder point, stretched
    along their length to reach it
  - the legs are two pictures on two bones (the mesh's 15 degree scissor clamp is switched off)
  - the straw hands are rigid tufts on their springs, each drawn twice (a back layer that lags) over a wrist frill
  - the face is drawn from parts: eye whites, pupils (their own bones), upper lids in 7 levels and lower lids in 3
    (sprite swaps), brows (their own bones) and one of 8 mouths - all driven by the clips' `faces` keys (FACE)
  - the crow is a body and a head (its neck turns on crow_hit) and one spread wing picture used twice

What comes out, per clip and frame: for every bone its WORLD transform as the runtime wants it (rotation in
radians, clockwise on screen = Pixi's; scale x, y; position of the bone's pivot in art px, y down), for every slot
the sprite it shows (or none), the effect sprites, and the cue frames (the figure within 3 px of rest).
A sprite on a bone is drawn with: position = the bone's x, y; rotation = its angle; scale = its sx, sy; pivot = the
bone's REST pivot measured from the sprite's own top-left corner (both in art px).

  .venv/Scripts/python.exe -I tools/fall/scare_rig.py            (prints a summary; tools/fall/pack_scare_rig.py imports build())"""
import json, math, os, random, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "blender"))
import scarecrow as SC                         # numpy only outside Blender

ROOT = os.path.dirname(os.path.dirname(HERE))
PARTS = os.path.join(ROOT, "art", "fall-src", "scare_parts", "parts")
FPS = SC.FPS
GROUND_Y = 1458                                # where the post goes into the ground (the boots' shadows lie here)

# bones: name, parent, pivot (art px). Parents before children.
BONES = [
    ("root", None, (540, 1470)),
    ("pole", "root", (540, 1460)),
    ("hips", "pole", (540, 800)),
    ("chest", "hips", (538, 748)),
    ("collar", "chest", (540, 462)),
    ("head", "chest", (520, 470)),
    ("hat", "head", (450, 262)),
    ("hat_tip", "hat", (301, 163)),
    ("hat_tuft", "hat", (470, 180)),
    ("hair_l", "head", (345, 285)),
    ("hair_ll", "head", (385, 335)),
    ("hair_r", "head", (588, 306)),
    ("pupil_l", "head", (446, 343)),         # (the eyes' centres + where the pupils rest: cut_scare_parts.PUPIL_AT)
    ("pupil_r", "head", (507, 310)),
    ("brow_l", "head", (433, 297)),
    ("brow_r", "head", (511, 263)),
    ("sleeve_l", "pole", (245, 495)),
    ("sleeve_r", "pole", (822, 495)),
    ("frill_l", "pole", (240, 490)),
    ("frill_r", "pole", (836, 488)),
    ("hand_lb", "pole", (150, 462)),
    ("hand_l", "pole", (150, 462)),
    ("hand_rb", "pole", (890, 460)),
    ("hand_r", "pole", (890, 460)),
    ("rope", "pole", (152, 470)),
    ("jug", "rope", (150, 588)),
    ("belt_b", "hips", (622, 776)),
    ("belt", "hips", (612, 770)),
    ("leg_l", "hips", (482, 852)),
    ("leg_r", "hips", (608, 852)),
    ("cuff_l", "leg_l", (458, 1112)),
    ("cuff_r", "leg_r", (612, 1114)),
    ("boot_l", "leg_l", (458, 1180)),
    ("boot_r", "leg_r", (592, 1180)),
    ("shadow_l", "root", (442, GROUND_Y)),
    ("shadow_r", "root", (596, GROUND_Y)),
    ("crow", "pole", (878, 416)),
    ("crow_head", "crow", (876, 283)),
    ("wing_r", "crow", (884, 290)),
    ("wing_l", "crow", (858, 292)),
]
BONE_NAMES = [b[0] for b in BONES]
SHOULDER = {"sleeve_l": (440, 500), "sleeve_r": (640, 500)}      # on the chest: where each sleeve is aimed
SOLE = {"shadow_l": ("boot_l", (442, 1354)), "shadow_r": ("boot_r", (596, 1354))}

# slots, back to front: name, bone, the sprite it shows at rest (None: hidden at rest)
SLOTS = [
    ("ground", "root", "ground"), ("shadow_l", "shadow_l", "shadow"), ("shadow_r", "shadow_r", "shadow"),
    ("post", "pole", "post"), ("crossbar", "pole", "crossbar"),
    ("sleeve_l", "sleeve_l", "sleeve_l"), ("sleeve_r", "sleeve_r", "sleeve_r"),
    ("boot_l", "boot_l", "boot_l"), ("boot_r", "boot_r", "boot_r"),
    ("leg_l", "leg_l", "leg_l"), ("leg_r", "leg_r", "leg_r"),
    ("cuff_l", "cuff_l", "cuff_l"), ("cuff_r", "cuff_r", "cuff_r"),
    ("torso", "chest", "torso"), ("hips", "hips", "hips"),
    ("belt_b", "belt_b", "belt_b"), ("belt_a", "belt", "belt_a"),
    ("collar", "collar", "collar"),
    ("hat_back", "hat", "hat_back"), ("hair_l", "hair_l", "hair_l"),
    ("head", "head", "head"),
    ("eye_l", "head", "eye_l"), ("eye_r", "head", "eye_r"),
    ("pupil_l", "pupil_l", "pupil_l"), ("pupil_r", "pupil_r", "pupil_r"),
    ("lid_u_l", "head", "lid_u2_l"), ("lid_u_r", "head", "lid_u1_r"),
    ("lid_d_l", "head", None), ("lid_d_r", "head", None),
    ("brow_l", "brow_l", "brow_l"), ("brow_r", "brow_r", "brow_r"),
    ("mouth", "head", "mouth_grin"),
    ("hair_ll", "hair_ll", "hair_ll"), ("hair_r", "hair_r", "hair_r"),
    ("hat_front", "hat", "hat_front"), ("hat_tip", "hat_tip", "hat_tip"), ("hat_tuft", "hat_tuft", "hat_tuft"),
    ("frill_l", "frill_l", "frill_l"), ("frill_r", "frill_r", "frill_r"),
    ("hand_lb", "hand_lb", "hand_l"), ("hand_l", "hand_l", "hand_l"),
    ("hand_rb", "hand_rb", "hand_r"), ("hand_r", "hand_r", "hand_r"),
    ("jug_rope", "rope", "jug_rope"), ("coil_l", "pole", "coil_l"), ("coil_r", "pole", "coil_r"),
    ("jug", "jug", "jug"),
    ("wing_r", "wing_r", None), ("wing_l", "wing_l", None),
    ("crow_body", "crow", "crow_body"), ("crow_head", "crow_head", "crow_head"),
]
SLOT_NAMES = [s[0] for s in SLOTS]
MOUTHS = ["grin", "cheer", "smile", "o", "smug", "hiccup", "sad", "drool"]
SPRITES = []                                    # every sprite a slot can show, in a fixed order
for _n, _b, _s in SLOTS:
    if _s and _s not in SPRITES:
        SPRITES.append(_s)
for _side in "lr":
    SPRITES += [f"lid_u{i}_{_side}" for i in range(1, 8) if f"lid_u{i}_{_side}" not in SPRITES]
    SPRITES += [f"lid_d{i}_{_side}" for i in range(1, 4)]
SPRITES += ["mouth_" + m for m in MOUTHS if "mouth_" + m not in SPRITES] + ["wing"]
HIDDEN = 255
CROW_UP = 70

# the faces: mouth, upper lids (0 open .. 7 shut) left / right, lower lids (0 .. 3), pupil offsets from the eye's
# centre (art px, in the head's frame: x right, y down; the pupils REST at neutral's), pupil size, brows (lift px
# (up = negative y), turn deg counter-clockwise)
FACE = {
    "neutral": dict(mouth="grin", u=(2, 1), d=(0, 0), pl=(5, 3), pr=(-5, 4), ps=1.0, bl=(0, 0), br=(0, 0)),
    "blink": dict(mouth=None, u=(7, 7), d=(0, 0), pl=(5, 3), pr=(-5, 4), ps=1.0, bl=(2, 0), br=(2, 0)),
    "cheer": dict(mouth="cheer", u=(0, 0), d=(2, 2), pl=(2, -3), pr=(-2, -3), ps=1.0, bl=(-7, 4), br=(-6, -4)),
    "happy": dict(mouth="grin", u=(0, 0), d=(2, 2), pl=(3, -1), pr=(-3, -1), ps=1.0, bl=(-5, 3), br=(-5, -3)),
    "hiccup": dict(mouth="hiccup", u=(6, 0), d=(2, 0), pl=(0, 3), pr=(0, -5), ps=.8, bl=(4, -9), br=(-8, 0)),
    "sad": dict(mouth="sad", u=(3, 3), d=(0, 0), pl=(-2, 8), pr=(-3, 8), ps=1.0, bl=(2, 15), br=(1, -15)),
    "shock": dict(mouth="o", u=(0, 0), d=(0, 0), pl=(0, 0), pr=(0, 0), ps=.62, bl=(-10, 0), br=(-8, 0)),
    "smug": dict(mouth="smug", u=(4, 3), d=(1, 0), pl=(10, 5), pr=(9, 6), ps=1.0, bl=(3, -9), br=(-7, 5)),
}
SLEEP = (6, 30)          # a blink held this many frames is a doze: the closed smile, then the drool

FX = [("bubble", 6, 0.8), ("straw", 14, 1.0), ("leaf_red", 5, 1.1), ("leaf_orange", 5, 1.1), ("leaf_gold", 5, 1.1),
      ("feather", 8, 0.9), ("sparkle", 8, 0.9), ("star", 6, 0.9), ("drop", 8, 0.7)]     # kind, pool, size (units) - scarecrow.build
FX_KINDS = [k for k, _, _ in FX]


def _rot(x, y, deg):
    """Turn (x, y) (art px, y down) counter-clockwise on screen."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return x * c + y * s, -x * s + y * c


def solve(local):
    """local: bone -> (r deg ccw, tx, ty art px, sx, sy). -> world: bone -> [R deg ccw, sx, sy, x, y] with the
    mirror (a negative sx up the chain) folded into the children's angle and sx."""
    W, M = {}, {}
    piv = {n: p for n, _, p in BONES}
    for name, par, P in BONES:
        r, tx, ty, sx, sy = local.get(name, (0.0, 0.0, 0.0, 1.0, 1.0))
        if par is None:
            W[name] = [r, sx, sy, P[0] + tx, P[1] + ty]
            M[name] = 1.0 if sx >= 0 else -1.0
            continue
        pr, psx, psy, px, py = W[par]
        m = M[par]
        ox, oy = (P[0] - piv[par][0]) * psx, (P[1] - piv[par][1]) * psy      # (psx carries the mirror already)
        ox, oy = _rot(ox, oy, pr)
        qx, qy = _rot(tx * m, ty, pr)
        W[name] = [pr + m * r, sx * m, sy, px + ox + qx, py + oy + qy]
        M[name] = m * (1.0 if sx >= 0 else -1.0)
    return W


def point(Wb, P, Q):
    """Where the art point Q, riding the bone whose rest pivot is P, is now."""
    r, sx, sy, x, y = Wb
    ox, oy = _rot((Q[0] - P[0]) * sx, (Q[1] - P[1]) * sy, r)
    return x + ox, y + oy


def face_tracks(faces, nf, loop):
    """The clip's face keys {frame: name} -> per frame: mouth, lids (4 levels), pupils (2 x (dx, dy)), pupil size,
    brows (2 x (dy, turn))."""
    keys = sorted(faces.items())
    out = []
    cur = dict(FACE["neutral"])
    lids = [2.0, 1.0, 0.0, 0.0]
    sm = None
    mouth = "grin"
    held = 0
    for i in range(nf):
        nm = "neutral"
        for f, v in keys:
            if f <= i:
                nm = v
        F = FACE[nm]
        held = held + 1 if nm == "blink" else 0
        if F["mouth"]:
            mouth = F["mouth"]
        m = mouth
        if held > SLEEP[1]:
            m = "drool"
        elif held > SLEEP[0]:
            m = "smile"
        tgt = [F["u"][0], F["u"][1], F["d"][0], F["d"][1]]
        for k in range(4):                         # the lids shut fast (2 frames) and open a little slower
            dlt = tgt[k] - lids[k]
            lids[k] += max(-3.0, min(4.0, dlt))
        N = FACE["neutral"]
        vals = [F["pl"][0] - N["pl"][0], F["pl"][1] - N["pl"][1], F["pr"][0] - N["pr"][0], F["pr"][1] - N["pr"][1], F["ps"], F["bl"][0], F["bl"][1], F["br"][0], F["br"][1]]
        if sm is None:
            sm = list(vals)
        k = .9 if nm == "shock" else .5            # the eyes pop at once; everything else eases over a few frames
        sm = [a + (b - a) * k for a, b in zip(sm, vals)]
        sm = [b if abs(a - b) < .02 else a for a, b in zip(sm, vals)]
        out.append(dict(mouth=m, lids=[int(round(v)) for v in lids], v=list(sm)))
    return out


def fx_frames(emits, nf, used):
    """scarecrow.key_clip's effect sprites, without Blender: per frame [kind index, a, b, c, d, tx, ty, alpha] (the
    affine takes the picture's unit square to art px), in the scene's object order."""
    size = {k: s for k, _, s in FX}
    pool = {k: n for k, n, _ in FX}
    frames = [[] for _ in range(nf)]
    for kind, fs, fe, path, spin, grow, r0 in emits:
        slot = used[kind] % pool[kind]
        used[kind] += 1
        for f in range(fs, fe + 1):
            if not 0 <= f < nf:
                continue
            t = (f - fs) / max(1, fe - fs)
            a = (min(1.0, 4 * t, 4 * (1 - t) + .001) if kind != "bubble" else (1.0 if t < .85 else 0.0))
            if a <= .003:
                continue
            x, z = path(t)
            g = (grow[0] + (grow[1] - grow[0]) * t) * size[kind]
            th = math.radians(r0 + spin * t)
            c, s = math.cos(th), math.sin(th)

            def f_(u, v):
                X, Z = (-.5 + u) * g, (.5 - v) * g
                return (c * X + s * Z + x) * 100 + SC.W_PX / 2, SC.H_PX / 2 - (-s * X + c * Z + z) * 100
            o, ex, ey = f_(0, 0), f_(1, 0), f_(0, 1)
            frames[f].append((FX_KINDS.index(kind), slot,
                              [FX_KINDS.index(kind)] + [round(v, 2) for v in (ex[0] - o[0], ex[1] - o[1], ey[0] - o[0],
                                                                              ey[1] - o[1], o[0], o[1])] + [round(a, 3)]))
    return [[e[2] for e in sorted(fr, key=lambda e: (e[0], e[1]))] for fr in frames]


def clip_frames(name, rng, used):
    """One clip -> (bones [nf, nb, 5] float (pixi angle rad, sx, sy, x, y), slots [nf, ns] uint8, spr, hold)."""
    rec = []
    orig = SC.primaries

    def spy(*a):
        d = orig(*a)
        rec.append(dict(d))
        return d
    SC.primaries, SC.LEG_CLAMP = spy, False
    try:
        poses, faces, emits = SC.clip_poses(name, rng)
    finally:
        SC.primaries, SC.LEG_CLAMP = orig, True
    n, loop = SC.CLIPS[name]
    nf = n if loop else n + 1
    drv = rec[2 * nf:3 * nf] if loop else rec[:nf]       # (a loop is run three times and the last pass kept)
    assert len(poses) == nf and len(drv) == nf, (name, len(poses), len(drv), nf)
    if not loop and name != "exit":
        faces = dict(faces)
        faces[n] = "neutral"
    ft = face_tracks(faces, nf, loop)
    piv = {b: p for b, _, p in BONES}
    bones = np.zeros((nf, len(BONES), 5), np.float64)
    slots = np.zeros((nf, len(SLOTS)), np.uint8)
    rest_ang = {s: math.atan2(SHOULDER[s][1] - piv[s][1], SHOULDER[s][0] - piv[s][0]) for s in SHOULDER}
    rest_len = {s: math.hypot(SHOULDER[s][1] - piv[s][1], SHOULDER[s][0] - piv[s][0]) for s in SHOULDER}
    for i in range(nf):
        p, d, f = poses[i], drv[i], ft[i]
        back = poses[max(0, i - 2)] if (i >= 2 or not loop) else poses[(i - 2) % nf]
        g = lambda b, c, dflt=0.0: p[b].get(c, dflt)
        L = {
            "pole": (g("pole", "r"), 0, 0, 1, 1),
            "hips": (g("hips", "r"), 0, -100 * g("hips", "y"), g("hips", "sx", 1), g("hips", "sy", 1)),
            "chest": (g("chest", "r"), 0, 0, g("chest", "sx", 1), g("chest", "sy", 1)),
            "collar": (g("collar", "r"), 0, 0, 1, 1),
            "head": (g("head", "r"), 0, 0, g("head", "sx", 1), g("head", "sy", 1)),
            "hat": (g("hat", "r"), 0, -100 * g("hat", "y"), g("hat", "sx", 1), g("hat", "sy", 1)),
            "hat_tip": (g("hat_tip", "r"), 0, 0, 1, 1),
            "hat_tuft": (.45 * g("hat_tip", "r") + .6 * g("brim_r", "r"), 0, 0, 1, 1),
            "hair_l": (g("hair_l", "r"), 0, 0, 1, 1),
            "hair_ll": (g("hair_ll", "r"), 0, 0, 1, 1),
            "hair_r": (g("hair_r", "r"), 0, 0, 1, 1),
            "frill_l": (.3 * g("hand_l", "r"), 0, 0, 1, 1),
            "frill_r": (.3 * g("hand_r", "r"), 0, 0, 1, 1),
            "hand_l": (g("hand_l", "r"), 0, 0, 1, 1),
            "hand_lb": (.62 * back["hand_l"]["r"], 0, 0, 1, 1),
            "hand_r": (g("hand_r", "r"), 0, 0, 1, 1),
            "hand_rb": (.62 * back["hand_r"]["r"], 0, 0, 1, 1),
            "rope": (g("rope", "r"), 0, 0, 1, 1),
            "jug": (g("jug", "r"), 0, 0, 1, 1),
            "belt": (g("belt", "r"), 0, 0, 1, 1),
            "belt_b": (.7 * back["belt"]["r"], 0, 0, 1, 1),
            "leg_l": (g("leg_l", "r"), 0, 0, 1, 1),
            "leg_r": (g("leg_r", "r"), 0, 0, 1, 1),
            "cuff_l": (g("cuff_l", "r"), 0, 0, 1, 1),
            "cuff_r": (g("cuff_r", "r"), 0, 0, 1, 1),
            "boot_l": (g("boot_l", "r"), 0, 0, 1, 1),
            "boot_r": (g("boot_r", "r"), 0, 0, 1, 1),
            # (in the air it flies CROW_UP px higher than the mesh rig's crow did: this head and hat reach further up)
            "crow": (g("crow", "r"), 100 * g("crow", "x"), -100 * g("crow", "y") - CROW_UP * d["crow_free"],
                     g("crow", "sx", 1), g("crow", "sy", 1)),
        }
        # the face
        v = f["v"]
        L["pupil_l"] = (0, v[0], v[1], v[4], v[4])
        L["pupil_r"] = (0, v[2], v[3], v[4], v[4])
        L["brow_l"] = (v[6], 0, v[5], 1, 1)
        L["brow_r"] = (v[8], 0, v[7], 1, 1)
        # the crow: its head nods into a crouch and takes the pecks / shakes; its wings
        fadek = 1.0
        if not loop and name != "exit" and i > n - 10:
            fadek = 1 - SC.ease((i - (n - 10)) / 10)
        sq, hit = d["crow_sq"] * fadek, d["crow_hit"] * fadek
        L["crow_head"] = (-1.2 * hit - 14 * sq, 0, 0, 1, 1)
        op = SC.cl(d["wing"], 0.0, 1.0) * fadek
        fl = d["flap"]
        fr = drv[i - 1]["flap"] if i > 0 else fl
        ws = .3 + .7 * op
        L["wing_l"] = (70 - 95 * (.5 + .5 * fl), 0, 0, ws, ws * (1 - .12 * (1 - abs(fl))))
        L["wing_r"] = (-(70 - 95 * (.5 + .5 * fr)), 0, 0, -ws, ws * (1 - .12 * (1 - abs(fr))))
        W = solve(L)
        # the sleeves: pinned at the wrist, aimed at the shoulder
        for s in SHOULDER:
            tx, ty = point(W["chest"], piv["chest"], SHOULDER[s])
            wx, wy = W[s][3], W[s][4]
            ang = math.atan2(ty - wy, tx - wx) - rest_ang[s]
            ang = (ang + math.pi) % (2 * math.pi) - math.pi
            k = SC.cl(math.hypot(tx - wx, ty - wy) / rest_len[s], .72, 1.32)
            sag = abs(g(s, "r")) * .012
            W[s] = [-math.degrees(ang), k, 1 + (1 - k) * .3 + sag, wx, wy]
        # the boots' shadows on the ground: under each sole, wider and thinner the higher the boot hangs
        for s, (boot, sole) in SOLE.items():
            bx, by = point(W[boot], piv[boot], sole)
            lift = max(0.0, sole[1] - by)
            W[s] = [0.0, min(1.7, 1 + lift / 260), max(.45, 1 - lift / 300), bx, GROUND_Y]
        for j, b in enumerate(BONE_NAMES):
            r, sx, sy, x, y = W[b]
            bones[i, j] = (-math.radians(r), sx, sy, x, y)
        # the slots
        row = {s: (SPRITES.index(spr) if spr else HIDDEN) for s, _, spr in SLOTS}
        lu_l, lu_r, ld_l, ld_r = f["lids"]
        row["lid_u_l"] = SPRITES.index(f"lid_u{lu_l}_l") if lu_l > 0 else HIDDEN
        row["lid_u_r"] = SPRITES.index(f"lid_u{lu_r}_r") if lu_r > 0 else HIDDEN
        row["lid_d_l"] = SPRITES.index(f"lid_d{ld_l}_l") if ld_l > 0 and lu_l < 7 else HIDDEN
        row["lid_d_r"] = SPRITES.index(f"lid_d{ld_r}_r") if ld_r > 0 and lu_r < 7 else HIDDEN
        row["mouth"] = SPRITES.index("mouth_" + f["mouth"])
        if op > .03:
            row["wing_l"] = row["wing_r"] = SPRITES.index("wing")
        slots[i] = [row[s] for s in SLOT_NAMES]
    spr = fx_frames(emits, nf, used)
    return bones, slots, spr, (list(SC.HOLD[name]) if name in SC.HOLD else None)


def anchors():
    """sprite -> the art point that sits on its bone's pivot (the pivot of the bone it is drawn on; the wing and the
    shadow, each drawn on two bones, carry their own)."""
    piv = {b: p for b, _, p in BONES}
    out = {}
    for sn, b, spr in SLOTS:
        if spr:
            out.setdefault(spr, piv[b])
    for s in SPRITES:
        if s.startswith(("lid_", "mouth_")):
            out[s] = piv["head"]
    out["wing"] = piv["wing_l"]
    out["shadow"] = None                       # its own centre
    return out


def rest_pose():
    W = solve({})
    out = np.zeros((len(BONES), 5))
    for j, (b, _, P) in enumerate(BONES):
        out[j] = (0, 1, 1, P[0], P[1])
    return out


def cues(bones, slots, meta):
    """The frames where every picture is within 3 px of where it rests (and shows what it shows at rest)."""
    rest = rest_pose()
    rest_row = np.array([SPRITES.index(s) if s else HIDDEN for _, _, s in SLOTS], np.uint8)
    pts, idx = [], []
    for si, (sn, b, spr) in enumerate(SLOTS):
        if not spr or spr == "shadow":
            continue
        m = meta[spr]
        j = BONE_NAMES.index(b)
        P = BONES[j][2]
        for cx, cy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            pts.append((m["x"] + cx * m["w"] / m["s"] - P[0], m["y"] + cy * m["h"] / m["s"] - P[1]))
            idx.append(j)
    pts, idx = np.array(pts), np.array(idx)
    out, far = [], []
    for i in range(len(bones)):
        B = bones[i][idx]
        c, s = np.cos(B[:, 0]), np.sin(B[:, 0])
        lx, ly = pts[:, 0] * B[:, 1], pts[:, 1] * B[:, 2]
        x, y = B[:, 3] + lx * c - ly * s, B[:, 4] + lx * s + ly * c
        R = rest[idx]
        dist = np.hypot(x - (R[:, 3] + pts[:, 0]), y - (R[:, 4] + pts[:, 1])).max()
        far.append(float(dist))
        if dist < 3.0 and (slots[i] == rest_row).all():
            out.append(i)
    return out, far


def build():
    meta = json.load(open(os.path.join(PARTS, "parts.json")))
    rng = random.Random(1123)                          # scarecrow.animate's own seed and clip order: the same effects
    used = {k: 0 for k in FX_KINDS}
    clips = {}
    for c, (n, loop) in SC.CLIPS.items():
        bones, slots, spr, hold = clip_frames(c, rng, used)
        cu, far = cues(bones, slots, meta)
        clips[c] = dict(frames=len(bones), loop=loop, bones=bones, slots=slots, spr=spr, cues=cu, far=far)
        if hold:
            clips[c]["hold"] = hold
    return dict(fps=FPS, art=[SC.W_PX, SC.H_PX], bones=[dict(name=b, parent=p, x=P[0], y=P[1]) for b, p, P in BONES],
                slots=[dict(name=s, bone=b, sprite=spr) for s, b, spr in SLOTS], sprites=list(SPRITES), fx=FX_KINDS,
                fx_size={k: s for k, _, s in FX}, rest=rest_pose(), clips=clips, meta=meta)


if __name__ == "__main__":
    R = build()
    print(len(R["bones"]), "bones,", len(R["slots"]), "slots,", len(R["sprites"]), "sprites")
    for c, d in R["clips"].items():
        b = d["bones"]
        print(f"{c:13s} {d['frames']:4d} f  cues {d['cues'][:6]}{'...' if len(d['cues']) > 6 else ''}  far {max(d['far']):6.1f} px  "
              f"x {b[..., 3].min():7.1f}..{b[..., 3].max():7.1f}  y {b[..., 4].min():7.1f}..{b[..., 4].max():7.1f}  "
              f"scale {b[..., 1:3].min():5.2f}..{b[..., 1:3].max():5.2f}  angle {b[..., 0].min():5.2f}..{b[..., 0].max():5.2f}  "
              f"fx {sum(len(f) for f in d['spr'])}")
