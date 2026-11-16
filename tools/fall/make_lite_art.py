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

iOS crash review 3, 2026-11-16 (the MOBILE tier, index.html window.MOBILE): the interface art too. On a phone
#app is shown at ~0.3-0.4 of its layout size, so a panel, headline or button is drawn at well under half its
pixels; the mobile tier swaps these copies in (liteArt() and the stylesheet rewrite in index.html's <head>) and
never fetches the full ones. Scaled by a factor (third column) chosen from the biggest size each is shown at on a
phone at DPR 3 (a 1290 px wide screen): the panels and buttons by half, the win headlines and their splashes,
shown up to ~the screen's width, by 0.6, the plate behind the reels (cover over the board) by 0.8.

Written to frontend/assets/lite/. Lanczos, WebP at the quality the originals were saved at or better.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "assets"
OUT = SRC / "lite"

UI = dict(quality=90, method=6, alpha_quality=100)
JOBS = [
    # (file, new width - or a scale factor when < 10 -, webp options)
    ("bonus_wall.webp", 2560, dict(quality=90, method=6)),
    ("frame.webp", 1500, dict(quality=92, method=6, alpha_quality=100)),
    # the mobile tier's interface art (MOBILE_LITE in index.html must list the same files)
    ("bonus_panel.webp", .5, UI), ("info_panel.webp", .5, UI), ("feature_box.webp", .5, UI),
    ("bonus_btn_text.webp", .5, UI), ("bonus_btn_bg.webp", .5, UI), ("banner_box.webp", .5, UI),
    ("spin_btn_arrows.webp", .5, UI), ("xbonus_text.webp", .5, UI), ("win_box.webp", .5, UI),
    ("brickwall.webp", .5, UI), ("hud_bar.webp", .6, UI),
    ("tier_bg.webp", .6, UI), ("total_bg.webp", .6, UI), ("total_win.webp", .6, UI),
    ("big_win.webp", .6, UI), ("mega_win.webp", .6, UI), ("xtreme_win.webp", .6, UI),
    ("plate_grey.webp", .8, UI),
    # the Tipsy Harvest wordmark (the features screen's logo, and the portrait board's on the mobile tier: <= ~1000
    # device px wide there) and its glow (already drawn at half size)
    ("intro_wordmark.webp", .4, UI), ("intro_wordmark_glow.webp", .8, UI),
]
# the flat icons (the paytable's tiles, the Multi's brick on the board): 800 px for a tile a phone shows at <= ~200
# device px - the info screen decoded all thirteen at once (~25 MB); 320 px on their longer side
FLAT_MAX = 320


def main():
    OUT.mkdir(exist_ok=True)
    for name, w, opts in JOBS:
        im = Image.open(SRC / name)
        im.load()
        mode = "RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB"
        im = im.convert(mode)
        if w < 10:
            w = round(im.width * w)
        h = round(im.height * w / im.width)
        small = im.resize((w, h), Image.LANCZOS)
        dst = OUT / name
        small.save(dst, "WEBP", **opts)
        print(f"{name}: {im.width}x{im.height} -> {w}x{h} ({mode}), {dst.stat().st_size / 1e3:.0f} KB, "
              f"decoded {im.width * im.height * 4 / 1e6:.1f} -> {w * h * 4 / 1e6:.1f} MB")
    (OUT / "flat").mkdir(exist_ok=True)
    for f in sorted((SRC / "flat").glob("*.webp")):
        im = Image.open(f)
        im.load()
        im = im.convert("RGBA")
        k = min(1.0, FLAT_MAX / max(im.size))
        w, h = round(im.width * k), round(im.height * k)
        im.resize((w, h), Image.LANCZOS).save(OUT / "flat" / f.name, "WEBP", **UI)
        print(f"flat/{f.name}: {im.width}x{im.height} -> {w}x{h}")


if __name__ == "__main__":
    main()
