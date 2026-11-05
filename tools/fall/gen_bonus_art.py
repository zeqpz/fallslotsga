"""The bonus-buy menu's card banners: a fall background scene (generated with no icon and no text) with the option's
icon composited big in the middle, so the icon is the board's own art, not a redrawing of it.

  .venv/Scripts/python.exe tools/fall/gen_bonus_art.py bg [name,..]     backgrounds   -> art/fall-src/bonus/bg_<name>.png
  .venv/Scripts/python.exe tools/fall/gen_bonus_art.py icons [name,..]  boost / corkstorm icons (sticker style, on
                                                                        transparency) -> art/fall-src/bonus/icon_<name>.png
                                                                        (raw generation kept as icon_<name>_raw.png)
  .venv/Scripts/python.exe tools/fall/gen_bonus_art.py comp [name,..]   composite -> frontend/assets/bonus/banner_<name>.webp
                                                                        (720x405, q88) + art/fall-src/bonus/banner_<name>.png
  .venv/Scripts/python.exe tools/fall/gen_bonus_art.py all [name,..]    the three in turn (bg / icons only where missing)

names: fs, xfs, boost, corkstorm. fs / xfs use the board icons art/fall-src/icons/BS.png / ES.png (prep_icons.py)."""
import os, sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orimg, clean_alpha

ROOT = orimg.ROOT
SRC = os.path.join(ROOT, "art", "fall-src", "bonus")
ICONS = os.path.join(ROOT, "art", "fall-src", "icons")
OUT = os.path.join(ROOT, "frontend", "assets", "bonus")
W, H = 720, 405
ICON_H = .70                     # the icon's height, of the banner's
ICON_W = .80                     # and never wider than this

STYLE = ("Rick and Morty cartoon background art style: clean black outlines of even medium weight with a slightly wobbly "
         "hand-drawn feel, flat cel colours with one hard-edged darker shade tone per colour, simple shapes, slightly "
         "lopsided goofy proportions, like a background painting from an adult animated sitcom. ")
BG_COMMON = ("A wide 16:9 landscape background scene for a mobile game shop card banner. {scene} Keep the MIDDLE of the "
             "picture open and simple (a soft glow of light or open sky there, nothing important) because a big game "
             "icon will be placed over the centre later; put the interesting details toward the left and right sides "
             "and the bottom. Absolutely NO text, no letters, no numbers, no logos, no signs with writing, no frame, no "
             "border, no UI, no characters in the centre. " + STYLE + "Full bleed, edge to edge.")
BG = {
    "fs": "A warm golden-hour PUMPKIN PATCH on a farm: rows of round orange pumpkins on green vines in the foreground, "
          "a red barn and a golden hay bale stack on the left, autumn trees with orange and red leaves on the right, a "
          "low warm sun making a soft golden glow behind the middle, a few maple leaves drifting.",
    "xfs": "A moody DUSK CORNFIELD: tall dry cornstalks on both sides, a crooked wooden fence, a few black crows "
           "flying high in the corners and one perched on a fence post at the side, a big low harvest moon glowing "
           "softly behind the middle, a dramatic cranberry-red and deep purple sky with dark clouds.",
    "boost": "An autumn APPLE ORCHARD in the afternoon: rows of apple trees with red apples and gold and orange leaves, a "
             "wooden ladder against a tree on the left, a basket of apples on the right, lots of glowing GOLD LEAVES "
             "falling through the air, a warm bright glow of sunlight behind the middle.",
    "corkstorm": "A STORMY NIGHT over a harvest field: dark blue-purple storm clouds swirling, a few lightning bolts in "
                 "the far corners, wind-blown hay bales and corn shocks in the foreground, a red barn silhouette on one "
                 "side, golden apple-cider spray and foam droplets and flying cork stoppers whirling in the wind, a "
                 "bright green-gold glow behind the middle.",
}

ICON_BASE = open(os.path.join(ROOT, "art", "fall-src", "prompts", "icon_base.txt"), encoding="utf-8").read().strip()
ICON_STYLE = open(os.path.join(ROOT, "art", "fall-src", "prompts", "style.txt"), encoding="utf-8").read().strip()
ICON = {
    # name: (description, extra reference icons besides the style reference H1)
    "boost": ("the BONUS BOOST icon: the attached round orange pumpkin \"FS\" free-spins badge (the second reference: "
              "redraw it the same, with its gold FS letters) with three big chunky glowing golden UP-ARROWS rising "
              "behind and beside it, and a big chunky gold \"x1.6\" in bold cartoon numerals with a thick black "
              "outline on the lower right, overlapping the badge. Exactly the text FS on the pumpkin and x1.6, "
              "spelled exactly, nothing else written. Energetic, powered-up", ["BS.png"]),
    "corkstorm": ("the CORK STORM icon: FOUR green glass hard cider bottles (exactly like the attached green XXX cider "
                  "bottle, the second reference: the same bottle, with XXX on its label) in a tight fanned bunch, all "
                  "four popping their corks at once, the four corks flying upward, golden cider foam spraying out of "
                  "the necks in a big fizzy burst, a few bubbles. The only writing is XXX on each label. Explosive, "
                  "celebratory", ["M.png"]),
}
SOURCES = {"fs": os.path.join(ICONS, "BS.png"), "xfs": os.path.join(ICONS, "ES.png"),
           "boost": os.path.join(SRC, "icon_boost.png"), "corkstorm": os.path.join(SRC, "icon_corkstorm.png")}
GLOW = {"fs": (255, 200, 90), "xfs": (190, 90, 230), "boost": (255, 215, 110), "corkstorm": (200, 255, 140)}
NAMES = list(BG)


def gen_bg(name):
    out = os.path.join(SRC, f"bg_{name}.png")
    _, cost = orimg.generate(out, BG_COMMON.format(scene=BG[name]), aspect="16:9", transparent=False)
    return f"bg {name} {cost}"


def gen_icon(name):
    desc, extra = ICON[name]
    raw = os.path.join(SRC, f"icon_{name}_raw.png")
    refs = [os.path.join(ROOT, "art", "fall-src", "H1_v1.png")] + [os.path.join(ICONS, e) for e in extra]
    p = (f"{ICON_BASE}\nThe symbol: {desc}.\nMatch the FIRST attached reference symbol exactly in drawing style, outline "
         f"weight, shading, sticker border and scale on the canvas (it is another symbol from the same set).\n\n"
         f"{ICON_STYLE}\n")
    _, cost = orimg.generate(raw, p, refs=refs)
    clean_alpha.clean(raw, os.path.join(SRC, f"icon_{name}.png"))
    return f"icon {name} {cost}"


def cover(im, w, h):
    """im scaled to cover w x h, centre-cropped"""
    k = max(w / im.size[0], h / im.size[1])
    im = im.resize((max(w, round(im.size[0] * k)), max(h, round(im.size[1] * k))), Image.LANCZOS)
    x, y = (im.size[0] - w) // 2, (im.size[1] - h) // 2
    return im.crop((x, y, x + w, y + h))


def composite(name, bg_path=None, icon_path=None, out_webp=None, out_png=None):
    S = 2                                                      # worked at 2x, scaled down at the end
    bg = cover(Image.open(bg_path or os.path.join(SRC, f"bg_{name}.png")).convert("RGB"), W * S, H * S).convert("RGBA")
    icon = Image.open(icon_path or SOURCES[name]).convert("RGBA")
    icon = icon.crop(icon.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    k = min(H * S * ICON_H / icon.size[1], W * S * ICON_W / icon.size[0])
    icon = icon.convert("RGBa").resize((round(icon.size[0] * k), round(icon.size[1] * k)), Image.LANCZOS).convert("RGBA")
    x, y = (W * S - icon.size[0]) // 2, (H * S - icon.size[1]) // 2
    # a soft pool of light behind the icon, in the option's colour, so it lifts off a busy scene
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32)
    d = np.hypot((xx - W * S / 2) / (W * S * .34), (yy - H * S / 2) / (H * S * .46))
    a = (np.clip(1 - d, 0, 1) ** 1.6 * 150).astype(np.uint8)
    glow = Image.new("RGBA", bg.size, GLOW[name] + (0,))
    glow.putalpha(Image.fromarray(a, "L"))
    bg.alpha_composite(glow)
    # the soft drop shadow: the silhouette, down and right, blurred
    sh = Image.new("L", bg.size, 0)
    sh.paste(icon.getchannel("A").point(lambda v: int(v * .62)), (x + 7 * S, y + 11 * S))
    sh = sh.filter(ImageFilter.GaussianBlur(9 * S))
    bg.alpha_composite(Image.merge("RGBA", (Image.new("L", bg.size, 12),) * 3 + (sh,)))
    bg.alpha_composite(icon, (x, y))
    out = bg.convert("RGB").resize((W, H), Image.LANCZOS)
    out_png = out_png or os.path.join(SRC, f"banner_{name}.png")
    out_webp = out_webp or os.path.join(OUT, f"banner_{name}.webp")
    for p in (out_png, out_webp):
        os.makedirs(os.path.dirname(p), exist_ok=True)
    out.save(out_png)
    out.save(out_webp, "WEBP", quality=88, method=6)
    return out_webp


def run(step, names):
    os.makedirs(SRC, exist_ok=True)
    if step in ("bg", "all"):
        todo = [n for n in names if step == "bg" or not os.path.exists(os.path.join(SRC, f"bg_{n}.png"))]
        with ThreadPoolExecutor(4) as ex:
            for r in ex.map(lambda n: _safe(gen_bg, n), todo):
                print(r, flush=True)
    if step in ("icons", "all"):
        todo = [n for n in names if n in ICON and (step == "icons" or not os.path.exists(SOURCES[n]))]
        with ThreadPoolExecutor(4) as ex:
            for r in ex.map(lambda n: _safe(gen_icon, n), todo):
                print(r, flush=True)
    if step in ("comp", "all"):
        for n in names:
            print("banner", composite(n), flush=True)


def _safe(fn, n):
    try:
        return fn(n)
    except RuntimeError as e:
        return f"FAIL {fn.__name__} {n} {e}"


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else NAMES
    run(step, names)
