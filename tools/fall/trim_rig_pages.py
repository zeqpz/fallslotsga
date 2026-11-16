"""Trim the live rigs' atlas pages to the rows their pictures use (iOS crash review 3, 2026-11-16).

    .venv\Scripts\python.exe -I tools/fall/trim_rig_pages.py

pack_rigs.py made every page a power of two each way; the game draws the rigs on 2D canvases, where a page of any
size is fine, and holds each page decoded (w x h x 4 bytes). The phone's r20 page was 2048x2048 for 1454 rows of
pictures: 16.8 MB held for the session, 11.9 MB trimmed. Cuts each page below the lowest picture on it (rounded up
to 16 rows), re-saves it losslessly (the same pixels) and writes the new height into rigs.json; the pictures'
coordinates do not move. Idempotent. (pack_rigs.py now sizes the height this way itself.)
"""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RIG = os.path.join(ROOT, "frontend", "assets", "rig")


def main():
    path = os.path.join(RIG, "rigs.json")
    rj = json.load(open(path, encoding="utf-8"))
    changed = False
    for D, tier in rj["tiers"].items():
        for pi, pg in enumerate(tier["pages"]):
            used = max((p[2] + p[4] for p in tier["pics"] if p[0] == pi), default=0)
            h = -(-used // 16) * 16
            f = os.path.join(RIG, pg["file"])
            im = Image.open(f)
            if not used or h >= im.height:
                print(f"r{D} {pg['file']}: {im.width}x{im.height} kept")
                continue
            im.load()
            assert im.getbbox() is None or im.getbbox()[3] <= h, "pixels below the last picture"
            before = im.width * im.height * 4 / 1e6
            im.crop((0, 0, im.width, h)).save(f, "WEBP", lossless=True, method=6)
            pg["h"] = h
            changed = True
            print(f"r{D} {pg['file']}: {im.width}x{im.height} -> {im.width}x{h}, decoded {before:.1f} -> {im.width * h * 4 / 1e6:.1f} MB")
    if changed:
        json.dump(rj, open(path, "w", encoding="utf-8"), separators=(",", ":"))


if __name__ == "__main__":
    main()
