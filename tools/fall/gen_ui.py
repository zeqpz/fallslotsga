"""Generate the fall UI art (art/fall-src/ui/<name>.png) and fit each onto the size the game draws it at
(frontend/assets/<path>, same file names as the graffiti build so the code needs no change).
usage: python tools/fall/gen_ui.py gen [name,..]     (OpenRouter, ~$0.06 each)
       python tools/fall/gen_ui.py fit [name,..]     (no API)"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orimg

ROOT = orimg.ROOT
SRC = os.path.join(ROOT, "art", "fall-src", "ui")
ASSETS = os.path.join(ROOT, "frontend", "assets")
STYLE = ("Rick and Morty cartoon style: clean black outlines with a slightly wobbly hand-drawn feel, flat cel colours "
         "with one hard darker shade per colour, goofy chunky shapes. Thanksgiving harvest palette: pumpkin orange "
         "#E8742A, harvest gold #F2B33D, cranberry red #A3263A, warm wood browns #7A4A2A / #3E2416, straw yellow "
         "#EAC55E, cream #F6E7C8. Key light from the upper left. Transparent background.")
LETTER = ("big chunky bubbly cartoon letters, fat and bouncy with a slight wobble, filled with a warm gradient from "
          "harvest gold to pumpkin orange, a thick dark chocolate-brown outline, a cream inner highlight on the upper "
          "left of each letter, a dark drop shadow below, a few small autumn maple leaves and an acorn tucked around "
          "the word")
# name: (prompt, aspect, target path under frontend/assets, target size, mode)  mode: contain | stretch | cover
JOBS = {
    "big_win": (f'The words "BIG WIN" as a game headline: {LETTER}. Nothing else.', "21:9", "big_win.webp", (1800, 370), "contain"),
    "mega_win": (f'The words "MEGA WIN" as a game headline: {LETTER}, extra excited, with a few gold sparkles.', "21:9", "mega_win.webp", (1800, 374), "contain"),
    "xtreme_win": (f'The words "XTREME WIN" as a game headline: {LETTER}, the most intense version with cranberry red and purple accents, little flames of orange leaves.', "21:9", "xtreme_win.webp", (1800, 402), "contain"),
    "total_win": (f'The words "TOTAL WIN" as a game headline: {LETTER}, set on a curved wooden harvest-fair banner ribbon.', "21:9", "total_win.webp", (1800, 508), "contain"),
    "tier_bg": ("A wide horizontal wooden harvest-fair sign plank board for a game headline, rounded rough-cut plank with wood grain, rope tied at both ends, a few autumn leaves and a small pumpkin at the corners, EMPTY in the middle (no text).", "21:9", "tier_bg.webp", (1980, 559), "stretch"),
    "total_bg": ("A wide horizontal plate for showing a win amount: a rustic wooden plank sign with a cream-painted inset panel in the middle (empty, no text), rope trim border, small acorns and maple leaves on the corners.", "21:9", "total_bg.webp", (1800, 560), "stretch"),
    "digits": ('A 4 by 3 grid of separate game number glyphs on a transparent background, one glyph centred in each cell with plenty of space between: top row "0 1 2 3", middle row "4 5 6 7", bottom row "8 9 , ." - chunky bubbly cartoon numerals filled harvest gold to pumpkin orange, thick dark brown outline, cream highlight upper left, same size and style for all.', "1:1", None, None, "digits"),
    "bonus_btn_bg": ("A game button: a round-cornered rustic wooden crate panel / barn-door sign button with wood planks, an orange pumpkin-coloured painted face, rope border, a little straw poking out, EMPTY face (no text).", "3:2", "bonus_btn_bg.webp", (950, 610), "stretch"),
    "bonus_btn_text": (f'The word "BONUS" as a game logo: {LETTER}, stacked big and bold.', "3:2", "bonus_btn_text.webp", (1140, 759), "contain"),
    "xbonus_text": (f'The words "XTREME" (smaller, on top, cranberry red and purple) and "BONUS" (big, below) as a game logo: {LETTER}, a black crow perched on the B.', "1:1", "xbonus_text.webp", (1065, 897), "contain"),
    "bonus_panel": ("A big landscape game menu panel: a rustic wooden barn-board frame with a dark warm brown painted inner panel (EMPTY, no text), rope trim, corn stalks and autumn leaves on the corners, small pumpkins at the bottom corners.", "3:2", "bonus_panel.webp", (2250, 1510), "stretch"),
    "feature_box": ("A tall portrait game info card: a wooden-framed cream parchment card (EMPTY, no text) with a rope border and a maple leaf at the top.", "3:4", "feature_box.webp", (840, 1074), "stretch"),
    "info_panel": ("A tall portrait game rules panel: a wooden-framed warm dark brown chalkboard-like panel (EMPTY, no text), rope border, autumn leaves at the corners.", "3:4", "info_panel.webp", (1600, 2034), "stretch"),
    "hud_bar": ("A very wide thin horizontal wooden plank bar for a game HUD (EMPTY, no text), rope at both ends, clean and simple.", "21:9", "hud_bar.webp", (1750, 261), "stretch"),
    "frame": ("A square-ish picture frame for a 7x7 slot machine reel board: a thick rustic wooden frame made of log and plank pieces lashed with rope at the corners, autumn maple leaves, little pumpkins and corn cobs decorating the four corners, the inside of the frame completely EMPTY and transparent (cut out), the frame border fairly thin compared to the opening.", "1:1", "frame.webp", (2200, 1982), "stretch"),
    "banner_box": ("A wide horizontal small wooden sign plank for a game message banner (EMPTY, no text), rope hanging loops at the ends.", "21:9", "banner_box.webp", (1440, 582), "stretch"),
    "wordmark": ('The game title logo "TIPSY HARVEST": "TIPSY" smaller and tilted on top, "HARVEST" big below, chunky bubbly cartoon letters filled harvest gold to pumpkin orange with a thick dark brown outline and cream highlights, the letters of TIPSY wobbling as if drunk, a little straw hat on the T, maple leaves and a small pumpkin around the logo.', "21:9", "intro_wordmark.webp", (2736, 1160), "contain"),
}


def gen(name):
    p, aspect = JOBS[name][0], JOBS[name][1]
    try:
        _, c = orimg.generate(os.path.join(SRC, name + ".png"), p + "\n\n" + STYLE, aspect=aspect)
        return f"OK {name} {c}"
    except RuntimeError as e:
        return f"FAIL {name} {e}"


def trim(im):
    a = np.asarray(im.getchannel("A"))
    a = np.where(a > 12, a, 0).astype(np.uint8)
    im.putalpha(Image.fromarray(a))
    bb = im.getchannel("A").getbbox()
    return im.crop(bb) if bb else im


def fit(name):
    _, _, path, size, mode = JOBS[name]
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    if mode == "digits":
        return fit_digits(im)
    im = trim(im)
    W, H = size
    if mode == "stretch":
        out = im.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
    else:
        k = min(W / im.width, H / im.height) * .98
        sm = im.convert("RGBa").resize((round(im.width * k), round(im.height * k)), Image.LANCZOS).convert("RGBA")
        out = Image.new("RGBA", size, (0, 0, 0, 0))
        out.alpha_composite(sm, ((W - sm.width) // 2, (H - sm.height) // 2))
    out.save(os.path.join(ASSETS, path), "WEBP", quality=90, alpha_quality=100, method=6)
    return f"fit {name} -> {path} {size}"


def fit_digits(im):
    """Cut the 4x3 glyph sheet into num/0..9, comma, dot at 343 px tall (the old glyph height)."""
    names = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "comma", "dot"]
    W, H = im.size
    cw, ch = W / 4, H / 3
    tops, glyphs = [], []
    for i, n in enumerate(names):
        c = im.crop((round((i % 4) * cw), round((i // 4) * ch), round((i % 4 + 1) * cw), round((i // 4 + 1) * ch)))
        glyphs.append((n, c))
    # one scale for every glyph: the digits' tallest -> 343 px
    hs = [trim(c.copy()).height for n, c in glyphs[:10]]
    k = 330 / max(hs)
    out_dir = os.path.join(ASSETS, "num")
    existing = {os.path.splitext(f)[0]: f for f in os.listdir(out_dir)}
    for n, c in glyphs:
        a = np.asarray(c.getchannel("A"))
        ys = np.nonzero(a.max(1) > 12)[0]
        xs = np.nonzero(a.max(0) > 12)[0]
        if not len(xs):
            continue
        g = c.crop((xs.min(), 0, xs.max() + 1, c.height))
        # keep each glyph's vertical place on a common baseline: crop rows by the digits' common band
        g = g.crop((0, ys.min() if n not in ("comma", "dot") else 0, g.width, c.height if n in ("comma", "dot") else ys.max() + 1))
        g = trim(g) if n not in ("comma", "dot") else g
        gs = g.convert("RGBa").resize((max(2, round(g.width * k)), max(2, round(g.height * k))), Image.LANCZOS).convert("RGBA")
        canvas = Image.new("RGBA", (gs.width + 14, 343), (0, 0, 0, 0))
        if n in ("comma", "dot"):
            gs = trim(gs)
            canvas = Image.new("RGBA", (gs.width + 14, 343), (0, 0, 0, 0))
            canvas.alpha_composite(gs, (7, 343 - gs.height - 6))
        else:
            canvas.alpha_composite(gs, (7, (343 - gs.height) // 2))
        fn = existing.get(n, n + ".webp")
        canvas.save(os.path.join(out_dir, fn), "WEBP", quality=92, alpha_quality=100, method=6)
    return "fit digits -> num/ " + ", ".join(sorted(existing))


if __name__ == "__main__":
    step = sys.argv[1]
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(JOBS)
    os.makedirs(SRC, exist_ok=True)
    if step == "gen":
        with ThreadPoolExecutor(6) as ex:
            for r in ex.map(gen, names):
                print(r, flush=True)
    else:
        for n in names:
            print(fit(n))
