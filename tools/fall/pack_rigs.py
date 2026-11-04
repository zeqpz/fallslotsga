"""Pack the icons' exported rigs (tools/fall/blender/export_rig.py -> art/blender/rigs/<ID>/rig.json) for the game's
live renderer: every picture the rigs use (parts, halos, effect sprites), tinted as Blender drew it, cropped to what
shows and scaled to what the board can ever need, packed into a few atlas pages per density; and the rigs' frames.

  .venv/Scripts/python.exe tools/fall/pack_rigs.py                 pack every exported rig
  .venv/Scripts/python.exe tools/fall/pack_rigs.py check H1 hit 20  draw that frame from the atlas like the game will,
                                                                    next to Blender's render of it (+ the difference)
-> frontend/assets/rig/rigs.json, frontend/assets/rig/r<D>/p<N>.webp  (D = atlas px per Blender unit; the icon is 10
   units, its frame 13)"""
import glob, json, math, os, sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RIGS = os.path.join(ROOT, "art", "blender", "rigs")
RENDERS = os.path.join(ROOT, "art", "blender", "renders")
OUT = os.path.join(ROOT, "frontend", "assets", "rig")
TIERS = (20, 40)          # px per unit: a cell up to ~200 / ~400 device px across its 10-unit icon
PAGE = 2048               # safe on every phone's WebGL
PAD = 2                   # transparent px kept around each picture (no bleed from its atlas neighbours)


def srgb2lin(x):
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def lin2srgb(x):
    return np.where(x <= .0031308, x * 12.92, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - .055)


def tinted(path, tint):
    im = Image.open(path).convert("RGBA")
    if all(abs(t - 1) < 1e-4 for t in tint):
        return im
    a = np.asarray(im).astype(np.float32) / 255
    rgb = lin2srgb(np.clip(srgb2lin(a[..., :3]) * np.array(tint, np.float32), 0, 1))
    return Image.fromarray((np.dstack([rgb, a[..., 3:]]) * 255 + .5).astype(np.uint8), "RGBA")


def load_rigs(ids=None):
    rigs = {}
    for f in sorted(glob.glob(os.path.join(RIGS, "*", "rig.json"))):
        r = json.load(open(f))
        if ids is None or r["id"] in ids:
            rigs[r["id"]] = r
    return rigs


def gather(rigs):
    """one table of distinct pictures over all rigs; how big each is ever drawn (units); rigs remapped onto it"""
    table, index, need = [], {}, []
    remap = {}
    for sid, r in rigs.items():
        m = []
        for p in r["pics"]:
            key = (os.path.normcase(p["file"]), tuple(round(t, 4) for t in p["tint"]))
            if key not in index:
                index[key] = len(table)
                table.append(dict(file=p["file"], tint=p["tint"]))
                need.append([0.0, 0.0])
            m.append(index[key])
        remap[sid] = m
        for c in r["clips"].values():
            for fr in c["frames"]:
                for it in fr:
                    g = m[it[1]]
                    need[g][0] = max(need[g][0], math.hypot(it[2], it[3]))
                    need[g][1] = max(need[g][1], math.hypot(it[4], it[5]))
    return table, need, remap


def shelf_pack(sizes):
    """sizes [(w, h)] -> [(page, x, y)], pages count; tallest first along shelves"""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    place = [None] * len(sizes)
    pages = [[0, 0, 0]]                  # per page: shelf y, shelf x, shelf height
    for i in order:
        w, h = sizes[i]
        assert w <= PAGE and h <= PAGE, (w, h)
        for pi, pg in enumerate(pages):
            y, x, sh = pg
            if x + w > PAGE:
                y, x, sh = y + sh, 0, 0
            if y + h <= PAGE:
                place[i] = (pi, x, y)
                pages[pi] = [y, x + w, max(sh, h)]
                break
        else:
            pages.append([0, w, h])
            place[i] = (len(pages) - 1, 0, 0)
    return place, len(pages)


def pack(ids=None):
    rigs = load_rigs(ids)
    table, need, remap = gather(rigs)
    srcs = [tinted(t["file"], t["tint"]) for t in table]
    out = dict(tiers={}, rigs={})
    for D in TIERS:
        crops, entries = [], []
        for g, im in enumerate(srcs):
            W, H = im.size
            s = min(1.0, max(need[g][0] * D / W, need[g][1] * D / H, 4 / min(W, H)))
            al = np.asarray(im)[..., 3]
            ys, xs = np.nonzero(al > 1)
            if len(xs) == 0:
                x0, y0, x1, y1 = 0, 0, 1, 1
            else:
                e = math.ceil(PAD / s)
                x0, y0 = max(0, xs.min() - e), max(0, ys.min() - e)
                x1, y1 = min(W, xs.max() + 1 + e), min(H, ys.max() + 1 + e)
            cw, ch = max(1, round((x1 - x0) * s)), max(1, round((y1 - y0) * s))
            crops.append(im.crop((x0, y0, x1, y1)).resize((cw, ch), Image.LANCZOS))
            entries.append([x0 / W - .5, y0 / H - .5, x1 / W - .5, y1 / H - .5])
        place, n = shelf_pack([c.size for c in crops])
        d = os.path.join(OUT, f"r{D}")
        os.makedirs(d, exist_ok=True)
        for old in glob.glob(os.path.join(d, "p*.webp")):
            os.remove(old)
        pages = []
        for pi in range(n):
            used = [(place[i], crops[i]) for i in range(len(crops)) if place[i][0] == pi]
            pw = 1 << math.ceil(math.log2(max(x + c.size[0] for (p, x, y), c in used)))
            ph = 1 << math.ceil(math.log2(max(y + c.size[1] for (p, x, y), c in used)))
            sheet = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            for (p, x, y), c in used:
                sheet.paste(c, (x, y))
            name = f"p{pi}.webp"
            sheet.save(os.path.join(d, name), "WEBP", lossless=True, method=6)
            pages.append(dict(file=f"r{D}/{name}", w=pw, h=ph))
        pics = [[place[i][0], place[i][1], place[i][2], *crops[i].size, *[round(v, 5) for v in entries[i]]]
                for i in range(len(crops))]
        out["tiers"][str(D)] = dict(pages=pages, pics=pics)
        kb = sum(os.path.getsize(os.path.join(OUT, p["file"])) for p in pages) // 1024
        mb = sum(p["w"] * p["h"] * 4 for p in pages) / 1e6
        print(f"r{D}: {len(pics)} pictures on {n} pages, {kb} KB, {mb:.1f} MB decoded")
    for sid, r in rigs.items():
        m = remap[sid]
        clips = {}
        for name, c in r["clips"].items():
            frames = []
            for fr in c["frames"]:
                frames.append([[it[0], m[it[1]], *[round(v, 3) for v in it[2:8]], round(it[8], 2)] for it in fr])
            clips[name] = dict(fps=c["fps"], loop=c["loop"], frames=frames)
        out["rigs"][sid] = dict(units=r["units"], clips=clips)
    out["note"] = ("tiers[D].pics[g] = [page, x, y, w, h, u0, v0, u1, v1]: picture g's crop in the atlas and the part "
                   "of its unit square (-0.5..0.5, v down) the crop covers; a frame item = [object, g, a, b, c, d, tx, "
                   "ty, alpha]: the unit square -> the icon's frame (units, y down, middle 0)")
    json.dump(out, open(os.path.join(OUT, "rigs.json"), "w"), separators=(",", ":"))
    print("rigs.json", os.path.getsize(os.path.join(OUT, "rigs.json")) // 1024, "KB,", len(out["rigs"]), "rigs")


def draw(sid, clip, k, D=40, size=512):
    """the frame as the game will draw it from the atlas: straight-alpha 'over', back to front"""
    rj = json.load(open(os.path.join(OUT, "rigs.json")))
    tier = rj["tiers"][str(D)]
    pages = [Image.open(os.path.join(OUT, p["file"])).convert("RGBA") for p in tier["pages"]]
    rig = rj["rigs"][sid]
    P = size / rig["units"]
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for it in rig["clips"][clip]["frames"][k]:
        pg, x, y, w, h, u0, v0, u1, v1 = tier["pics"][it[1]]
        a, b, c, d, tx, ty = it[2:8]
        crop = pages[pg].crop((x, y, x + w, y + h))
        if it[8] < 1:
            arr = np.asarray(crop).copy()
            arr[..., 3] = (arr[..., 3] * it[8] + .5).astype(np.uint8)
            crop = Image.fromarray(arr, "RGBA")
        # crop px -> uv -> frame units -> canvas px
        S = np.array([[(u1 - u0) / w, 0, u0], [0, (v1 - v0) / h, v0], [0, 0, 1]])
        A = np.array([[a, c, tx], [b, d, ty], [0, 0, 1]])
        C = np.array([[P, 0, size / 2], [0, P, size / 2], [0, 0, 1]])
        inv = np.linalg.inv(C @ A @ S)
        layer = crop.transform((size, size), Image.AFFINE, tuple(inv[:2].ravel()), Image.BILINEAR)
        canvas.alpha_composite(layer)
    return canvas


def check(sid, clip, k):
    mine = draw(sid, clip, int(k))
    ref = Image.open(os.path.join(RENDERS, sid, clip, f"{int(k):04d}.png")).convert("RGBA").resize(mine.size)
    bg = Image.new("RGBA", mine.size, (40, 40, 52, 255))
    a, b = Image.alpha_composite(bg, mine), Image.alpha_composite(bg, ref)
    diff = np.abs(np.asarray(a, np.int16)[..., :3] - np.asarray(b, np.int16)[..., :3])
    print(f"{sid} {clip} {k}: mean abs diff {diff.mean():.2f}/255, >40: {(diff.max(-1) > 40).mean() * 100:.2f}% px")
    sheet = Image.new("RGB", (mine.size[0] * 3, mine.size[1]))
    sheet.paste(a.convert("RGB"), (0, 0))
    sheet.paste(b.convert("RGB"), (mine.size[0], 0))
    sheet.paste(Image.fromarray(np.clip(diff * 3, 0, 255).astype(np.uint8)), (mine.size[0] * 2, 0))
    return sheet


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "check":
        sheet = check(*a[1:4])
        if len(a) > 4:
            sheet.save(a[4])
    else:
        pack(set(a[0].split(",")) if a else None)
