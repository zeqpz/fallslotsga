"""Lobby artwork for the Engine Media page: the 16:9 cover and the 3:4 tile.

Composed from the game's own art (no new generated art, so the lobby matches the game): the farm
painting (frontend/assets/bonus_wall.webp), the scarecrow's repaired layers (pole + body + crow, one
shared 1024x1536 canvas: art/blender/chars/scarecrow/layers, made by tools/fall/pack_char_rig.py), the
Tipsy Harvest wordmark and its glow. No symbols: the scarecrow is the one focus (owner, 2026-11-08).
Engine's guide (2026-09-14): bright background, one large clear focus, cover consistent with the tile.

  .venv/Scripts/python.exe -I tools/fall/make_media.py
-> media/tipsy_harvest_cover_16x9.png (1920x1080), media/tipsy_harvest_tile_3x4.png (1200x1600) + .jpg copies"""
import os

from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = lambda *p: os.path.join(ROOT, *p)
OUT = A("media")

BG = A("art", "fall-src", "bg", "bonus_wall_noleaves.png")   # floating leaves removed, front pumpkins kept (the game splits those into a still layer)
WORD = A("frontend", "assets", "intro_wordmark.webp")
GLOW = A("frontend", "assets", "intro_wordmark_glow.webp")
LAY = A("art", "blender", "chars", "scarecrow", "layers")
SYMS = A("art", "fall-src")


def load(p):
    return Image.open(p).convert("RGBA")


def trim(im):
    return im.crop(im.getbbox())


def fit_h(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def fit_w(im, w):
    return im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)


def scarecrow(face="cheer"):
    """Pole behind, body, crow on his arm - the layers share one canvas, so they stack in place."""
    c = load(os.path.join(LAY, "pole.png"))
    c.alpha_composite(load(os.path.join(LAY, f"body_{face}.png")))
    c.alpha_composite(load(os.path.join(LAY, "crow.png")))
    return trim(c)


def background(w, h, focus_x=.5, focus_y=.5, zoom=1.0):
    """The painting cropped to w:h around a focus point, brightened a touch (Engine: bright lobby art)."""
    bg = Image.open(BG).convert("RGB")
    s = max(w / bg.width, h / bg.height) * zoom
    big = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
    x = min(max(0, round(big.width * focus_x - w / 2)), big.width - w)
    y = min(max(0, round(big.height * focus_y - h / 2)), big.height - h)
    out = big.crop((x, y, x + w, y + h))
    out = ImageEnhance.Brightness(out).enhance(1.08)
    out = ImageEnhance.Color(out).enhance(1.06)
    return out.convert("RGBA")


def shadow(im, blur, alpha=.55, grow=0):
    """A soft dark halo of an RGBA sprite, to lift it off the busy painting."""
    a = im.getchannel("A")
    if grow:
        a = a.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    sh = Image.new("RGBA", im.size, (20, 8, 2, 0))
    sh.putalpha(a.point(lambda v: int(v * alpha)))
    pad = blur * 3
    canvas = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(sh, (pad, pad))
    return canvas.filter(ImageFilter.GaussianBlur(blur)), pad


def place(base, im, x, y, blur=18, alpha=.55, grow=0):
    """Paste im with its top-left at (x, y), over a soft shadow."""
    sh, pad = shadow(im, blur, alpha, grow)
    base.alpha_composite(sh, (round(x - pad), round(y - pad + blur * .4)))
    base.alpha_composite(im, (round(x), round(y)))


def wordmark(w):
    word = trim(load(WORD))
    word = fit_w(word, w)
    glow = load(GLOW).resize((round(load(GLOW).width * word.width / trim(load(WORD)).width * 2),
                              round(load(GLOW).height * word.width / trim(load(WORD)).width * 2)), Image.LANCZOS)
    return word, glow


def vignette(im, strength=.35):
    w, h = im.size
    m = Image.radial_gradient("L").resize((w, h), Image.LANCZOS)   # 0 centre -> 255 edge
    dark = Image.new("RGBA", (w, h), (25, 10, 2, 255))
    dark.putalpha(m.point(lambda v: int(max(0, v - 90) / 165 * 255 * strength)))
    im.alpha_composite(dark)
    return im


def sym(name, h):
    return fit_h(trim(load(os.path.join(SYMS, f"{name}_v1.png"))), h)


def warm_glow(base, cx, cy, r, alpha=.5):
    """A soft warm light behind the hero, so the focus reads on the painting."""
    g = Image.radial_gradient("L").resize((r * 2, r * 2), Image.LANCZOS)
    layer = Image.new("RGBA", (r * 2, r * 2), (255, 196, 110, 0))
    layer.putalpha(g.point(lambda v: int((255 - v) * alpha)))
    base.alpha_composite(layer, (round(cx - r), round(cy - r)))


def cover():
    """The scarecrow and the title only - no symbols (owner, 2026-11-08)."""
    W, H = 1920, 1080
    im = background(W, H, focus_x=.42, focus_y=.42, zoom=1.0)
    warm_glow(im, 600, 640, 620, .45)
    # the scarecrow, the one big focus, left of centre
    sc = fit_h(scarecrow("happy"), 1060)
    place(im, sc, 600 - sc.width / 2, H - sc.height + 50, blur=22, alpha=.5)
    # the wordmark, right, big and centred on the free half
    word, glow = wordmark(1020)
    cx, cy = 1390, 470
    im.alpha_composite(glow, (round(cx - glow.width / 2), round(cy - glow.height / 2)))
    place(im, word, cx - word.width / 2, cy - word.height / 2, blur=16, alpha=.45)
    return vignette(im, .38)


def tile():
    """The scarecrow only - no title, no symbols (owner, 2026-11-08)."""
    W, H = 1200, 1600
    im = background(W, H, focus_x=.43, focus_y=.42, zoom=1.15)
    warm_glow(im, 600, 820, 700, .45)
    # no title on the tile (owner, 2026-11-08): just the scarecrow, big, in the field
    sc = fit_h(scarecrow("happy"), 1420)
    place(im, sc, 600 - sc.width / 2, H - sc.height + 40, blur=22, alpha=.5)
    return vignette(im, .38)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    rgb = img.convert("RGB")
    p = os.path.join(OUT, name)
    rgb.save(p + ".png", optimize=True)
    rgb.save(p + ".jpg", quality=92, optimize=True, progressive=True)
    print(p + ".png", rgb.size, os.path.getsize(p + ".png"), "B;", os.path.getsize(p + ".jpg"), "B jpg")


if __name__ == "__main__":
    save(cover(), "tipsy_harvest_cover_16x9")
    save(tile(), "tipsy_harvest_tile_3x4")
