"""Pack the cut-out scarecrow for the game: frontend/assets/chars/scarecrow_parts/ (the skinned-mesh rig in
frontend/assets/chars/scarecrow_rig/ is left alone).

Reads the part pictures (art/fall-src/scare_parts/parts, made by tools/fall/cut_scare_parts.py cut + made) and the
animation (tools/fall/scare_rig.py build(), run here - no Blender), and writes:

  atlas.webp   one 2048 x 2048 page: every part at SCALE (1.5) px per art px, the post / crossbar / ground / boot
               shadow at 1.0, the effect sprites at 96 px. Each picture has PAD (4) px of room round it, filled with
               its own edge colour at alpha 0 (so mipmaps and bilinear taps never pull in black or a neighbour).
  rig.bin      per clip two arrays (offsets in rig.json "bin", as [byte offset, dtype, shape], little-endian):
                 clip_<name>   int16 [frames][bones][5]: angle x 4096 (radians, clockwise on screen = Pixi rotation),
                               scale x x 4096, scale y x 4096, pivot x x 16, pivot y x 16 (art px, y down) - WORLD
                               values, no hierarchy to walk
                 slots_<name>  uint8 [frames][slots]: the sprite each slot shows (index into "sprites"), 255 = none
  rig.json     fps, art size, ground, page, the quantisation ("q"), bones (names, parents, rest pivots), slots in
               draw order (name, bone index, rest sprite), sprites ([name, atlas x, y, w, h, pivot x, pivot y (in
               the sprite's own atlas px, from its top-left), atlas px per art px]), fx kinds + their atlas rects,
               and per clip: frames, loop, cues, hold, spr (the effect sprites per frame, as the old rig had them)
A slot is drawn as one sprite: position = bone x, y; rotation = bone angle; scale = (sx / s, sy / s) with s the
sprite's atlas px per art px; pivot = the sprite's pivot. Between two 30 fps keys every value is lerped.

Also writes the rest pose as layers on the shared 1024 x 1536 canvas for the lobby art (tools/fall/make_media.py
reads pole.png + body_<face>.png + crow.png): art/blender/chars/scarecrow/parts_layers/ (+ figure_grin.png, the lot).

  .venv/Scripts/python.exe -I tools/fall/pack_scare_rig.py"""
import io, json, os, sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cut_scare_parts as C
import scare_rig as RIG
import pack_char_rig as PK

ROOT = RIG.ROOT
OUT = os.path.join(ROOT, "frontend", "assets", "chars", "scarecrow_parts")
LAYERS = os.path.join(ROOT, "art", "blender", "chars", "scarecrow", "parts_layers")
PAGE, PAD, SCALE, FX_PX = 2048, 4, 1.5, 96
Q_ANGLE, Q_SCALE, Q_POS = 4096, 4096, 16
SHADOW = dict(w=156, h=22, rgb=(52, 26, 10), a=.3)        # the boots' shadow on the ground, art px


def shadow_sprite():
    w, h = SHADOW["w"], SHADOW["h"]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((xs + .5 - w / 2) / (w / 2), (ys + .5 - h / 2) / (h / 2))
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = np.array(SHADOW["rgb"]) / 255
    img[..., 3] = np.clip(1 - d, 0, 1) ** 1.6 * SHADOW["a"]
    return img


def to_atlas(im, s_from, s_to):
    """A master picture (s_from px per art px, straight alpha) -> at s_to, exactly (padded to whole px first)."""
    if abs(s_from - s_to) < 1e-6:
        return im
    k = s_to / s_from
    den = 4 if abs(k - .75) < 1e-6 else 1
    h, w = im.shape[:2]
    H, W = -(-h // den) * den, -(-w // den) * den
    pad = np.zeros((H, W, 4), np.float32)
    pad[:h, :w] = im
    return C.resize(pad, int(round(W * k)), int(round(H * k)))


def bleed(im, pad):
    """The picture with `pad` px of room round it; every see-through px takes the colour of the nearest solid one."""
    h, w = im.shape[:2]
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    out[pad:-pad, pad:-pad] = im
    solid = out[..., 3] > .02
    if solid.any():
        idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
        out[..., :3] = np.where(solid[..., None], out[..., :3], out[..., :3][idx[0], idx[1]])
    return out


class Skyline:
    """Bottom-left skyline packing."""

    def __init__(self, size):
        self.size = size
        self.sky = [(0, 0, size)]                 # (x, y, w) segments, left to right

    def place(self, w, h):
        best = None
        for i, (x, y, sw) in enumerate(self.sky):
            if x + w > self.size:
                break
            top, rem, j = y, w, i
            while rem > 0 and j < len(self.sky):
                top = max(top, self.sky[j][1])
                rem -= self.sky[j][2]
                j += 1
            if rem > 0 or top + h > self.size:
                continue
            if best is None or (top, x) < (best[0], best[1]):
                best = (top, x, i)
        if best is None:
            raise RuntimeError("atlas full")
        top, x, i = best
        new, x1 = [], x + w
        for sx, sy, sw in self.sky:
            if sx + sw <= x or sx >= x1:
                new.append((sx, sy, sw))
                continue
            if sx < x:
                new.append((sx, sy, x - sx))
            if sx + sw > x1:
                new.append((x1, sy, sx + sw - x1))
        new.append((x, top + h, w))
        new.sort()
        self.sky = new
        return x, top


def main():
    R = RIG.build()
    meta = R["meta"]
    anch = RIG.anchors()
    # ---- the pictures
    pics = []                                      # (name, img at atlas scale, s, art x, art y)
    for name in R["sprites"]:
        if name == "shadow":
            pics.append((name, shadow_sprite(), 1.0, -SHADOW["w"] / 2, -SHADOW["h"] / 2))
            continue
        m = meta[name]
        s = 1.0 if abs(m["s"] - 1.0) < 1e-6 else SCALE
        pics.append((name, to_atlas(C.load(os.path.join(C.OUT, name + ".png")), m["s"], s), s, m["x"], m["y"]))
    fxp = []
    for kind in R["fx"]:
        im = Image.open(os.path.join(PK.FXD, kind + ".png")).convert("RGBA")
        im = im.convert("RGBa").resize((FX_PX, FX_PX), Image.LANCZOS).convert("RGBA")
        fxp.append(("fx_" + kind, np.asarray(im).astype(np.float32) / 255))
    atlas = np.zeros((PAGE, PAGE, 4), np.float32)
    sky = Skyline(PAGE)
    where = {}
    todo = [(n, im) for n, im, _, _, _ in pics] + fxp
    for n, im in sorted(todo, key=lambda t: (-t[1].shape[0], -t[1].shape[1])):
        b = bleed(im, PAD)
        x, y = sky.place(b.shape[1], b.shape[0])
        atlas[y:y + b.shape[0], x:x + b.shape[1]] = b
        where[n] = (x + PAD, y + PAD, im.shape[1], im.shape[0])
    used_h = max(y + h for _, y, _, h in where.values()) + PAD
    fill = sum(w * h for _, _, w, h in where.values()) / PAGE / PAGE
    os.makedirs(OUT, exist_ok=True)
    img = Image.fromarray((atlas * 255 + .5).clip(0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=90, method=6, alpha_quality=100, exact=True)      # exact: keep the bled colours
    open(os.path.join(OUT, "atlas.webp"), "wb").write(buf.getvalue())
    print(f"atlas {img.size} used height {used_h} fill {fill:.2f}  {len(buf.getvalue()) / 1024:.0f} KB")

    sprites = []
    for name, im, s, ax, ay in pics:
        x, y, w, h = where[name]
        a = anch[name]
        px, py = ((w / 2, h / 2) if a is None else ((a[0] - ax) * s, (a[1] - ay) * s))
        sprites.append([name, x, y, w, h, round(px, 2), round(py, 2), s])

    # ---- the animation
    blob = bytearray()
    offs = {}

    def add(name, arr):
        arr = np.ascontiguousarray(arr)
        while len(blob) % 4:
            blob.append(0)
        offs[name] = [len(blob), arr.dtype.str.lstrip("<|"), list(arr.shape)]
        blob.extend(arr.tobytes())
    clips = {}
    for c, d in R["clips"].items():
        B = d["bones"]
        q = np.empty(B.shape, np.float64)
        q[..., 0] = B[..., 0] * Q_ANGLE
        q[..., 1:3] = B[..., 1:3] * Q_SCALE
        q[..., 3:] = B[..., 3:] * Q_POS
        assert np.abs(q).max() < 32767, (c, np.abs(q).max())
        add("clip_" + c, np.round(q).astype("<i2"))
        add("slots_" + c, d["slots"].astype(np.uint8))
        clips[c] = {"frames": d["frames"], "loop": d["loop"], "cues": d["cues"], "spr": d["spr"]}
        if "hold" in d:
            clips[c]["hold"] = d["hold"]
    open(os.path.join(OUT, "rig.bin"), "wb").write(bytes(blob))
    names = [b["name"] for b in R["bones"]]
    man = {
        "format": "parts-1", "fps": R["fps"], "art": R["art"], "ground": [R["art"][0] / 2, PK.GROUND_Y],
        "rest_height": PK.GROUND_Y - 10, "page": [PAGE, PAGE], "q": {"angle": Q_ANGLE, "scale": Q_SCALE, "pos": Q_POS},
        "bones": names, "parents": [names.index(b["parent"]) if b["parent"] else -1 for b in R["bones"]],
        "rest": [[b["x"], b["y"]] for b in R["bones"]],
        "slots": [[s["name"], names.index(s["bone"]), (R["sprites"].index(s["sprite"]) if s["sprite"] else 255)]
                  for s in R["slots"]],
        "sprites": sprites, "fx": R["fx"], "rects": {n: list(where[n]) for n, _ in fxp},
        "bin": offs, "bytes": len(blob), "clips": clips,
    }
    json.dump(man, open(os.path.join(OUT, "rig.json"), "w"), separators=(",", ":"))
    print("rig.bin", len(blob), "bytes; rig.json", os.path.getsize(os.path.join(OUT, "rig.json")), "bytes;",
          len(names), "bones", len(man["slots"]), "slots", len(sprites), "sprites")
    for c, d in clips.items():
        print(f"  {c:13s} {d['frames']:4d} frames  cues {d['cues']}")
    layers(R, meta)


def layers(R, meta):
    """The rest pose on the shared canvas, for the lobby art: pole.png, body_<face>.png, crow.png, figure_grin.png."""
    os.makedirs(LAYERS, exist_ok=True)
    order = [(s["name"], s["sprite"]) for s in R["slots"]]
    pole = ["ground", "post", "crossbar"]
    crow = ["crow_body", "crow_head"]

    def body(face):
        F = RIG.FACE[face]
        N = RIG.FACE["neutral"]
        m = dict(meta)
        for side, k in (("l", "pl"), ("r", "pr")):
            e = dict(meta["pupil_" + side])
            e["x"], e["y"] = e["x"] + F[k][0] - N[k][0], e["y"] + F[k][1] - N[k][1]
            m["pupil_" + side] = e
        for side, k in (("l", "bl"), ("r", "br")):
            e = dict(meta["brow_" + side])
            e["y"] = e["y"] + F[k][0]
            m["brow_" + side] = e
        show = {"mouth": "mouth_" + (F["mouth"] or "drunk"),
                "lid_u_l": f"lid_u{F['u'][0]}_l" if F["u"][0] else None, "lid_u_r": f"lid_u{F['u'][1]}_r" if F["u"][1] else None,
                "lid_d_l": f"lid_d{F['d'][0]}_l" if F["d"][0] else None, "lid_d_r": f"lid_d{F['d'][1]}_r" if F["d"][1] else None}
        names = []
        for slot, spr in order:
            spr = show.get(slot, spr)
            if spr and spr not in pole + crow + ["shadow"]:
                names.append(spr)
        return C.compose(m, names, 1.0)
    C.save(C.compose(meta, pole, 1.0), os.path.join(LAYERS, "pole.png"))
    C.save(C.compose(meta, crow, 1.0), os.path.join(LAYERS, "crow.png"))
    for face in ("neutral", "happy", "cheer"):
        C.save(body(face), os.path.join(LAYERS, f"body_{face}.png"))
    full = C.compose(meta, pole + [s for _, s in order if s and s not in pole + ["shadow"]], 1.0)
    C.save(full, os.path.join(LAYERS, "figure_grin.png"))
    print("layers ->", LAYERS)


if __name__ == "__main__":
    main()
