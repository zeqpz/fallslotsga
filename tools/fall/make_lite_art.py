"""Phone ("lite" tier) copies of the few pictures that cost the most decoded memory on a phone.

    .venv\\Scripts\\python.exe -I tools/fall/make_lite_art.py

iOS review, 2026-11-16: the game reloaded on an iPhone 12 (the tab ran out of memory). A picture costs
width x height x 4 bytes once decoded, whatever its file size, so the 3840x2160 painting alone was 33 MB.
These copies are sized for what a phone can show (index.html picks them only where the screen does not need
more: see LITE / liteArt() there), so they look the same there:

  bonus_wall.webp  3840x2160 -> 2560x1440  the farm painting. On a phone it is drawn by bgfx at 1.5 device px
                                           per CSS px at most (a 844 px tall portrait screen: 1266 px), so
                                           1440 rows are more than it ever shows. 33.2 -> 14.7 MB decoded.
  frame.webp       2200x1982 -> 1500x1351  the log frame: ~1440 device px wide on a 390x844 @3x portrait
                                           phone, less in landscape. 17.4 -> 8.1 MB decoded.

Written to frontend/assets/lite/. Lanczos, WebP at the quality the originals were saved at or better.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "assets"
OUT = SRC / "lite"

JOBS = [
    # (file, new width, webp options)
    ("bonus_wall.webp", 2560, dict(quality=90, method=6)),
    ("frame.webp", 1500, dict(quality=92, method=6, alpha_quality=100)),
]


def main():
    OUT.mkdir(exist_ok=True)
    for name, w, opts in JOBS:
        im = Image.open(SRC / name)
        im.load()
        mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
        im = im.convert(mode)
        h = round(im.height * w / im.width)
        small = im.resize((w, h), Image.LANCZOS)
        dst = OUT / name
        small.save(dst, "WEBP", **opts)
        print(f"{name}: {im.width}x{im.height} -> {w}x{h} ({mode}), {dst.stat().st_size / 1e3:.0f} KB, "
              f"decoded {im.width * im.height * 4 / 1e6:.1f} -> {w * h * 4 / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
