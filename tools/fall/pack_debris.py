"""Cuts the generated debris sheets (gen_debris.py) into their loose pieces and packs them into one atlas:
frontend/assets/fx/debris.webp + tools/fall/debris.json ({sheet: [[x, y, w, h, rel], ...]}, rel = the piece's size
against its sheet's middle piece), which the game carries inline as DEBRIS_AT (paste it there after a re-pack).
  python tools/fall/pack_debris.py"""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "fall-src", "debris")
SHEETS = ["apple", "grapes", "pumpkin", "pie", "turkey", "horn", "corn", "hat", "leaf", "jug", "splat"]
BOX = {"splat": 176}          # the longest side a piece is shipped at (drawn ~40 css px, at 2x)
JOIN = {"splat": 16}          # px a piece's loose crumbs and droplets may sit from it and still be part of it
W = 1024


def pieces(name):
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    a = np.asarray(im)[..., 3] > 40
    lab, n = ndimage.label(ndimage.binary_dilation(a, iterations=JOIN.get(name, 9)))
    out = []
    for sl in ndimage.find_objects(lab):
        m = a[sl]
        if m.sum() < 1500:
            continue
        ys, xs = np.where(m)
        box = (sl[1].start + xs.min(), sl[0].start + ys.min(), sl[1].start + xs.max() + 1, sl[0].start + ys.max() + 1)
        out.append(im.crop(box))
    return out


def main():
    table, placed = {}, []
    for name in SHEETS:
        ps = pieces(name)
        mid = float(np.median([max(p.size) for p in ps]))
        box = BOX.get(name, 104)
        for p in ps:
            rel = min(1.35, max(.6, max(p.size) / mid))
            k = box * rel / max(p.size)
            q = p.resize((max(1, round(p.width * k)), max(1, round(p.height * k))), Image.LANCZOS)
            placed.append((name, q, round(rel, 2)))
        print(name, len(ps))
    x = y = row = 0
    spots = []
    for name, q, rel in sorted(placed, key=lambda t: -t[1].height):
        if x + q.width + 2 > W:
            x, y, row = 0, y + row + 2, 0
        spots.append((name, q, rel, x, y))
        x += q.width + 2
        row = max(row, q.height)
    atlas = Image.new("RGBA", (W, y + row), (0, 0, 0, 0))
    for name, q, rel, x, y in spots:
        atlas.paste(q, (x, y))
        table.setdefault(name, []).append([x, y, q.width, q.height, rel])
    out = os.path.join(ROOT, "frontend", "assets", "fx", "debris.webp")
    atlas.save(out, "WEBP", quality=90, method=6)
    json.dump(table, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "debris.json"), "w"), separators=(",", ":"))
    print(atlas.size, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
