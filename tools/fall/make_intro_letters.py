"""The loading screen's SMUKIEZ wordmark (owner, 2026-11-15): a simple, rounded, bold face - the game's own
Fredoka at its Bold weight - every letter the same height and evenly spaced, with the slash under it drawn in
the same rounded stroke. Replaces the graffiti hand lettering (frontend/assets/intro_letters).

Writes one picture per letter, the slash ("swash"), a small TM and the word's glow, plus pieces.json with each
piece's box on the 2736 x 1160 wordmark; prints the INTRO_PIECES line for index.html's runIntro.

  .venv/Scripts/python.exe -I tools/fall/make_intro_letters.py"""
import json, os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT = os.path.join(ROOT, "frontend", "assets", "fredoka.ttf")
OUT = os.path.join(ROOT, "frontend", "assets", "intro_letters")
W, H = 2736, 1160
WORD = [("S", "S"), ("M", "M"), ("U", "U"), ("K", "K"), ("i", "I"), ("E", "E"), ("Z", "Z")]   # key (the game's names), glyph
SIZE = 470                 # px: cap height ~ .7 of it
GAP = 46                   # px between letters: the same everywhere
PAD = 14                   # clear px round each piece
SS = 3                     # drawn 3x and reduced: smooth edges
WHITE = (255, 255, 255, 255)


def font(px):
    f = ImageFont.truetype(FONT, px)
    f.set_variation_by_axes([700, 100])      # Bold, normal width
    return f


def glyph(ch, px):
    """The glyph alone, cropped to its ink, and its ink box (left, top, right, bottom) from the pen origin/baseline."""
    f = font(px * SS)
    l, t, r, b = f.getbbox(ch, anchor="ls")
    im = Image.new("L", (r - l + 8 * SS, b - t + 8 * SS), 0)
    ImageDraw.Draw(im).text((4 * SS - l, 4 * SS - t), ch, font=f, fill=255, anchor="ls")
    im = im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
    box = im.getbbox()
    im = im.crop(box)
    return im, f.getlength(ch) / SS


def white(mask, pad=PAD):
    out = Image.new("RGBA", (mask.width + pad * 2, mask.height + pad * 2), (255, 255, 255, 0))
    a = Image.new("L", out.size, 0)
    a.paste(mask, (pad, pad))
    out.putalpha(a)
    return out


def slash(w, h, thick0, thick1, rise):
    """The slash under the word in the font's own stroke: a rounded bar, thick at the left and tapering to the
    right, climbing `rise` px - one confident underline."""
    s = SS
    im = Image.new("L", (w * s, h * s), 0)
    d = ImageDraw.Draw(im)
    n = 240
    for i in range(n + 1):
        u = i / n
        x = (thick0 / 2 + u * (w - thick0 / 2 - thick1 / 2)) * s
        y = (h - thick0 / 2 - u * rise) * s
        r = (thick0 + (thick1 - thick0) * u) / 2 * s
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return im.resize((w, h), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    glyphs = [(k, *glyph(ch, SIZE)) for k, ch in WORD]
    cap_h = max(g.height for _, g, _ in glyphs)
    total = sum(g.width for _, g, _ in glyphs) + GAP * (len(glyphs) - 1)
    x = (W - total) // 2
    top = 250                                   # the caps' top line
    pieces, canvas = {}, Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for k, g, _adv in glyphs:
        im = white(g)
        y = top + (cap_h - g.height)            # all stand on one baseline
        box = [x - PAD, y - PAD, im.width, im.height]
        im.save(os.path.join(OUT, f"{k}.webp"), lossless=True, method=6)
        canvas.alpha_composite(im, (box[0], box[1]))
        pieces[k] = box
        x += g.width + GAP
    left, right = (W - total) // 2, (W - total) // 2 + total
    stroke = round(SIZE * .2)                   # about the Bold's stem
    # the slash: from under the M to past the Z, a stroke thick, tapering, climbing a little
    sw_w, sw_h = round(total * .9), stroke + 70
    sw = white(slash(sw_w, sw_h, stroke * .78, stroke * .34, 70), 10)
    sx, sy = left + round(total * .1) - 10, top + cap_h + 62
    sw.save(os.path.join(OUT, "swash.webp"), lossless=True, method=6)
    canvas.alpha_composite(sw, (sx, sy))
    pieces["swash"] = [sx, sy, sw.width, sw.height]
    # TM, small, at the word's top right
    tm_g, _ = glyph("TM", 74)
    tm = white(tm_g, 8)
    tx, ty = right + 18, top - 8
    tm.save(os.path.join(OUT, "tm.webp"), lossless=True, method=6)
    canvas.alpha_composite(tm, (tx, ty))
    pieces["tm"] = [tx, ty, tm.width, tm.height]
    # the glow: the whole word blurred, on a canvas padded so it fades out before any edge
    gp = 110
    glow = Image.new("RGBA", (W + gp * 2, H + gp * 2), (255, 255, 255, 0))
    a = Image.new("L", glow.size, 0)
    a.paste(canvas.getchannel("A"), (gp, gp))
    a = a.filter(ImageFilter.GaussianBlur(38)).point(lambda v: min(255, int(v * 1.25)))
    glow.putalpha(a)
    glow = glow.resize((glow.width // 2, glow.height // 2), Image.LANCZOS)
    glow.save(os.path.join(OUT, "glow.webp"), quality=82, method=6)
    pieces["glow"] = [-gp, -gp, W + gp * 2, H + gp * 2]
    for old in ("seal.webp",):
        p = os.path.join(OUT, old)
        if os.path.exists(p):
            os.remove(p)
    json.dump({"size": [W, H], "pieces": pieces}, open(os.path.join(OUT, "pieces.json"), "w"), indent=1)
    prev = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    prev.alpha_composite(canvas)
    prev.convert("RGB").resize((W // 3, H // 3), Image.LANCZOS).save(os.path.join(ROOT, "research", "intro_wordmark_preview.jpg"), quality=88)
    print("INTRO_PIECES = " + json.dumps(pieces, separators=(",", ":")) + ";")


if __name__ == "__main__":
    main()
