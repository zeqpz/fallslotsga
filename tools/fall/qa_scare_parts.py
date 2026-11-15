"""Offline check of the packed cut-out scarecrow: composes clip frames from frontend/assets/chars/scarecrow_parts/
(atlas.webp + rig.json + rig.bin ONLY - nothing from the source art) exactly as a 2D sprite runtime would: for every
slot, back to front, one sprite with position / pivot / rotation / scale from its bone's 5 values, then the effect
sprites. Contact sheets go to research/scarecrow_shots/round3/parts_*.

  .venv/Scripts/python.exe -I tools/fall/qa_scare_parts.py [sheets]           all the sheets
  .venv/Scripts/python.exe -I tools/fall/qa_scare_parts.py frame <clip> <i> out.png [x0,y0,x1,y1] [scale]"""
import json, os, sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "frontend", "assets", "chars", "scarecrow_parts")
SHOTS = os.path.join(ROOT, "research", "scarecrow_shots", "round3")
VIEW = (-40, -150, 1064, 1520)                 # art px shown by default
LIGHT, DARK, MID = (236, 226, 204), (34, 30, 44), (150, 170, 150)


class Rig:
    def __init__(self):
        self.man = json.load(open(os.path.join(SRC, "rig.json")))
        self.bin = open(os.path.join(SRC, "rig.bin"), "rb").read()
        at = np.asarray(Image.open(os.path.join(SRC, "atlas.webp")).convert("RGBA")).astype(np.float32) / 255
        at[..., :3] *= at[..., 3:]                                   # premultiplied, as a GPU texture is
        self.atlas = at
        self.tex = {}

    def arr(self, name):
        off, dt, shape = self.man["bin"][name]
        return np.frombuffer(self.bin, dtype="<" + dt, count=int(np.prod(shape)), offset=off).reshape(shape)

    def bones(self, clip, f):
        """Frame f (may be fractional: lerped between keys) -> [bones, 5] float: angle, sx, sy, x, y."""
        A = self.arr("clip_" + clip)
        q = self.man["q"]
        n = len(A)
        i0 = int(np.floor(f)) % n
        i1 = (i0 + 1) % n if self.man["clips"][clip]["loop"] else min(n - 1, i0 + 1)
        k = f - np.floor(f)
        B = A[i0].astype(np.float64) * (1 - k) + A[i1].astype(np.float64) * k
        return B / np.array([q["angle"], q["scale"], q["scale"], q["pos"], q["pos"]])

    def piece(self, x, y, w, h):
        key = (x, y, w, h)
        if key not in self.tex:
            self.tex[key] = [Image.fromarray(np.ascontiguousarray(self.atlas[y - 1:y + h + 1, x - 1:x + w + 1, c]), "F") for c in range(4)]
        return self.tex[key]

    def blit(self, out, rect, M, view, scale, alpha=1.0):
        """Draw the atlas rect with M = (a, b, c, d, tx, ty): texture px (u, v) -> art px (a u + c v + tx, b u + d v + ty)."""
        x, y, w, h = rect
        a, b, c, d, tx, ty = M
        # texture px -> output px
        a, b, c, d = a * scale, b * scale, c * scale, d * scale
        tx, ty = (tx - view[0]) * scale, (ty - view[1]) * scale
        cs = np.array([[0, 0], [w, 0], [0, h], [w, h]], np.float64)
        ox, oy = cs[:, 0] * a + cs[:, 1] * c + tx, cs[:, 0] * b + cs[:, 1] * d + ty
        H, W = out.shape[:2]
        x0, y0 = max(0, int(np.floor(ox.min())) - 1), max(0, int(np.floor(oy.min())) - 1)
        x1, y1 = min(W, int(np.ceil(ox.max())) + 1), min(H, int(np.ceil(oy.max())) + 1)
        det = a * d - b * c
        if x1 <= x0 or y1 <= y0 or abs(det) < 1e-9:
            return
        ia, ic, ib, id_ = d / det, -c / det, -b / det, a / det           # output px -> texture px
        # the centre of output px (X + x0, Y + y0) -> texture; + 1 for the 1 px margin round the piece, PIL's own half px
        px, py = x0 + .5 - tx, y0 + .5 - ty
        data = (ia, ic, ia * px + ic * py + 1 - .5, ib, id_, ib * px + id_ * py + 1 - .5)
        chans = [np.asarray(ch.transform((x1 - x0, y1 - y0), Image.AFFINE, data, Image.BILINEAR)) for ch in self.piece(x, y, w, h)]
        src = np.stack(chans, -1) * alpha
        dst = out[y0:y1, x0:x1]
        dst *= (1 - src[..., 3:])
        dst += src

    def frame(self, clip, f, view=VIEW, scale=.5, bg=LIGHT, fx=True, only=None):
        m = self.man
        B = self.bones(clip, f)
        S = self.arr("slots_" + clip)[int(np.floor(f)) % m["clips"][clip]["frames"]]
        W, H = int(round((view[2] - view[0]) * scale)), int(round((view[3] - view[1]) * scale))
        out = np.zeros((H, W, 4), np.float32)
        if bg is not None:
            out[..., :3] = np.array(bg, np.float32) / 255
            out[..., 3] = 1
        for si, (sname, bone, _) in enumerate(m["slots"]):
            spr = int(S[si])
            if spr == 255 or (only and sname not in only):
                continue
            name, x, y, w, h, px, py, s = m["sprites"][spr]
            ang, sx, sy, bx, by = B[bone]
            c, sn = np.cos(ang), np.sin(ang)
            kx, ky = sx / s, sy / s
            a, b, c2, d = c * kx, sn * kx, -sn * ky, c * ky
            self.blit(out, (x, y, w, h), (a, b, c2, d, bx - a * px - c2 * py, by - b * px - d * py), view, scale)
        if fx:
            for kind, a, b, c, d, tx, ty, al in m["clips"][clip]["spr"][int(np.floor(f)) % m["clips"][clip]["frames"]]:
                x, y, w, h = m["rects"]["fx_" + m["fx"][kind]]
                self.blit(out, (x, y, w, h), (a / w, b / w, c / h, d / h, tx, ty), view, scale, al)
        return out

    def image(self, *a, **k):
        o = self.frame(*a, **k)
        return Image.fromarray((o[..., :3] * 255 + .5).clip(0, 255).astype(np.uint8))


def sheet(ims, cols, labels=None, gap=4):
    w, h = ims[0].size
    rows = -(-len(ims) // cols)
    out = Image.new("RGB", (cols * (w + gap) - gap, rows * (h + gap) - gap), (20, 20, 20))
    dr = ImageDraw.Draw(out)
    for i, im in enumerate(ims):
        x, y = (i % cols) * (w + gap), (i // cols) * (h + gap)
        out.paste(im, (x, y))
        if labels:
            dr.rectangle([x, y, x + 8 + 7 * len(labels[i]), y + 15], fill=(0, 0, 0))
            dr.text((x + 4, y + 2), labels[i], fill=(255, 255, 255))
    return out


def save(im, name):
    os.makedirs(SHOTS, exist_ok=True)
    p = os.path.join(SHOTS, name)
    im.save(p, quality=90)
    print(p, im.size)


def sheets(which=None):
    R = Rig()
    m = R.man
    want = lambda n: not which or n in which
    if want("rest"):
        save(sheet([R.image("spin", 0, scale=.62, bg=LIGHT), R.image("spin", 0, scale=.62, bg=DARK)], 2), "parts_rest_light_dark.jpg")
        save(R.image("spin", 0, view=(180, 80, 760, 560), scale=1.5, bg=LIGHT), "parts_rest_head_1p5x.jpg")
    if want("clips"):
        for c, d in m["clips"].items():
            n = d["frames"]
            if c == "idle":
                fr = [0, 50, 110, 150, 240, 264]
            elif c == "big_win":
                fr = [3, 10, 22, 34, 58, 112]
            else:
                fr = [int(round(v)) for v in np.linspace(2, n - 4, 6)]
            ims = [R.image(c, f, scale=.4, bg=MID) for f in fr]
            save(sheet(ims, 6, [f"{c} {f}" for f in fr]), f"parts_clip_{c}.jpg")
    if want("faces"):
        picks = [("neutral", "spin", 0), ("blink", "idle", 24), ("smug", "idle", 46), ("shock", "anticipate", 20),
                 ("cheer", "big_win", 60), ("happy", "win", 30), ("sad", "lose", 40), ("hiccup", "hiccup", 13),
                 ("doze", "idle", 222), ("drool", "idle", 256)]
        hv = lambda c, f: head_view(R, c, f)
        ims = [R.image(c, f, view=hv(c, f), scale=1.0, bg=LIGHT) for _, c, f in picks]
        save(sheet(ims, 5, [f"{n} ({c} {f})" for n, c, f in picks]), "parts_faces.jpg")
        fr = list(range(20, 30))
        ims = [R.image("idle", f, view=head_view(R, "idle", f, 150), scale=1.0, bg=LIGHT) for f in fr]
        save(sheet(ims, 10, [f"idle {f}" for f in fr]), "parts_blink_strip.jpg")
        fr = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]
        ims = [R.image("lose", f, view=head_view(R, "lose", f, 150), scale=1.0, bg=LIGHT) for f in fr]
        save(sheet(ims, 10, [f"lose {f}" for f in fr]), "parts_face_change_strip.jpg")
    if want("hands"):
        fr = [0, 9, 13, 22, 28, 34, 40, 109, 119, 126]
        l = [R.image("big_win", f, view=(-60, 200, 380, 700), scale=.7, bg=LIGHT) for f in fr]
        r = [R.image("big_win", f, view=(700, 200, 1090, 700), scale=.7, bg=LIGHT) for f in fr]
        save(sheet(l + r, 10, [f"big_win {f}" for f in fr] * 2), "parts_hands_big_win.jpg")
    if want("jug"):
        fr = [0, 6, 10, 16, 22, 30, 60, 110]
        ims = [R.image("big_win", f, view=(-80, 380, 330, 900), scale=.7, bg=LIGHT) for f in fr]
        save(sheet(ims, 8, [f"big_win {f}" for f in fr]), "parts_jug_big_win.jpg")
    if want("legs"):
        fr = [8, 10, 22, 34, 46, 109, 115, 125]
        ims = [R.image("big_win", f, view=(250, 640, 850, 1500), scale=.5, bg=LIGHT) for f in fr]
        fr2 = [8, 14, 20, 30]
        ims += [R.image("win", f, view=(250, 640, 850, 1500), scale=.5, bg=LIGHT) for f in fr2]
        save(sheet(ims, 12, [f"big_win {f}" for f in fr] + [f"win {f}" for f in fr2]), "parts_legs.jpg")
    if want("crow"):
        picks = [("peck", 8), ("peck", 23), ("peck", 24), ("peck", 26), ("peck", 58), ("lose", 30), ("lose", 33),
                 ("big_win", 8), ("big_win", 11), ("big_win", 13), ("win", 9), ("idle", 132)]
        ims = [R.image(c, f, view=(540, -160, 1090, 560), scale=.5, bg=LIGHT) for c, f in picks]
        save(sheet(ims, 12, [f"{c} {f}" for c, f in picks]), "parts_crow.jpg")


# ---- the automatic checks (2026-11-15): no background may show through a joint or an eye, in any frame
MAGENTA = (255, 0, 255)
# joint -> (bone, radius art px, an art point riding that bone (None: the bone's own pivot))
JOINTS = {
    "neck": ("head", 18, None), "collar": ("collar", 16, None), "waist": ("chest", 40, None),
    "shoulder_l": ("chest", 22, (418, 506)), "shoulder_r": ("chest", 18, (658, 502)),
    "wrist_l": ("sleeve_l", 10, None), "wrist_r": ("sleeve_r", 10, None),
    "hip_l": ("leg_l", 30, None), "hip_r": ("leg_r", 30, None),
    "ankle_l": ("boot_l", 14, None), "ankle_r": ("boot_r", 14, None),
    "hat": ("hat", 25, None), "hat_tip": ("hat_tip", 14, None),
    "rope": ("rope", 5, None), "jug": ("jug", 5, None), "crow_neck": ("crow_head", 16, None),
}
EYES = {"eye_l": (441, 342), "eye_r": (512, 312)}        # on the head bone; the disc tested is the eye and its ring
EYE_R = 33


def riding(R, B, bone, Q=None):
    j = R.man["bones"].index(bone)
    ang, sx, sy, x, y = B[j]
    if Q is None:
        return x, y, abs(sx)
    P = R.man["rest"][j]
    lx, ly = (Q[0] - P[0]) * sx, (Q[1] - P[1]) * sy
    return x + lx * np.cos(ang) - ly * np.sin(ang), y + lx * np.sin(ang) + ly * np.cos(ang), abs(sx)


def check_joints(scale=.5):
    """Every frame of every clip over magenta: a disc round each posed joint must hold no magenta."""
    R = Rig()
    view = (-150, -420, 1180, 1520)
    H, W = int(round((view[3] - view[1]) * scale)), int(round((view[2] - view[0]) * scale))
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    bad, total = {}, 0
    fig = [n for n, _, _ in R.man["slots"] if n not in ("ground", "shadow_l", "shadow_r", "post", "crossbar")]
    for c, d in R.man["clips"].items():
        for f in range(d["frames"]):
            img = R.frame(c, f, view=view, scale=scale, bg=MAGENTA, fx=False, only=fig)     # (no post behind him: it would hide a gap)
            mag = (img[..., 0] > .8) & (img[..., 2] > .8) & (img[..., 1] < .25)
            B = R.bones(c, f)
            total += 1
            for jn, (bone, rad, Q) in JOINTS.items():
                x, y, k = riding(R, B, bone, Q)
                if jn == "crow_neck":
                    if k < .6:                      # the crow is edge-on in the middle of a turn
                        continue
                    rad = rad * k
                m = np.hypot(xs + .5 - (x - view[0]) * scale, ys + .5 - (y - view[1]) * scale) < rad * scale
                n = int((mag & m).sum())
                if n:
                    bad.setdefault(jn, []).append((c, f, n))
    print(f"joint check: {total} frames x {len(JOINTS)} joints")
    for jn in JOINTS:
        b = bad.get(jn, [])
        if b:
            worst = sorted(b, key=lambda t: -t[2])[:6]
            print(f"  FAIL {jn:11s} {len(b):4d} frames; worst (clip, frame, px): {worst}")
        else:
            print(f"  ok   {jn}")
    return bad


def check_eyes(scale=1.0):
    """Every frame of every clip, the head over magenta and over black: inside each eye's disc the two renders must
    be the same picture (anything see-through shows as a difference)."""
    R = Rig()
    worst, fails = 0.0, []
    for c, d in R.man["clips"].items():
        for f in range(d["frames"]):
            hx, hy, _ = riding(R, R.bones(c, f), "head", (476, 327))
            view = (hx - 90, hy - 90, hx + 90, hy + 90)
            a = R.frame(c, f, view=view, scale=scale, bg=MAGENTA, fx=False)
            b = R.frame(c, f, view=view, scale=scale, bg=(0, 0, 0), fx=False)
            diff = np.abs(a[..., :3] - b[..., :3]).max(-1)
            ys, xs = np.mgrid[0:diff.shape[0], 0:diff.shape[1]].astype(np.float32)
            B = R.bones(c, f)
            for en, Q in EYES.items():
                x, y, _ = riding(R, B, "head", Q)
                m = np.hypot(xs + .5 - (x - view[0]) * scale, ys + .5 - (y - view[1]) * scale) < EYE_R * scale
                v = float(diff[m].max())
                worst = max(worst, v)
                if v > 2 / 255:
                    fails.append((c, f, en, round(v, 3)))
    print(f"eye check: worst background show-through {worst * 255:.2f}/255; {len(fails)} failing (clip, frame, eye): {fails[:10]}")
    picks = [("idle", 23), ("idle", 250), ("hiccup", 13), ("lose", 40), ("win", 30), ("idle", 46), ("idle", 21), ("idle", 26)]
    ims = [R.image(c, f, view=head_view(R, c, f, 75), scale=3.0, bg=bg, fx=False) for bg in (MAGENTA, (0, 0, 0)) for c, f in picks]
    save(sheet(ims, len(picks), [f"{c} {f}" for c, f in picks] * 2), "parts_lids_magenta_black_3x.jpg")
    return fails


def head_view(R, clip, f, half=170):
    B = R.bones(clip, f)
    j = R.man["bones"].index("head")
    x, y = B[j][3] - 45, B[j][4] - 150
    return (x - half, y - half, x + half, y + half)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "frame":
        R = Rig()
        view = tuple(float(v) for v in a[4].split(",")) if len(a) > 4 else VIEW
        R.image(a[1], float(a[2]), view=view, scale=float(a[5]) if len(a) > 5 else .5).save(a[3])
    elif a and a[0] == "joints":
        check_joints()
    elif a and a[0] == "eyes":
        check_eyes()
    else:
        sheets(a[1:] if a and a[0] == "sheets" else None)
