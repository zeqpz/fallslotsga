"""Cartoon effect sprites for the Blender symbol and character clips -> art/fall-src/fx/<name>.png (RGBA, 256 px).
Flat colour, black ink outline, one hard shade on the lower right - the same look as the symbols.
Leaves are the game's own maple leaf (L1) shrunk and re-tinted."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "fall-src", "fx")
INK = (30, 18, 12, 255)
S = 256
SS = 4                                      # supersampling


def canvas():
    return Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))


def done(im, name):
    im.resize((S, S), Image.LANCZOS).save(os.path.join(OUT, name + ".png"))


def poly_star(cx, cy, r0, r1, n, rot=0):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r0
        a = rot + math.pi * i / n
        pts.append((cx + r * math.sin(a), cy - r * math.cos(a)))
    return pts


def inked_poly(pts, fill, shade=None, w=9):
    im = canvas()
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=INK)
    # the fill is the outline shrunk: draw the poly again with a thick ink line round it
    d.line(pts + [pts[0]], fill=INK, width=w * SS, joint="curve")
    inner = Image.new("L", im.size, 0)
    ImageDraw.Draw(inner).polygon(pts, fill=255)
    inner = inner.filter(ImageFilter.MinFilter(2 * w * SS // 2 * 2 + 1)) if w else inner
    col = Image.new("RGBA", im.size, fill)
    im.paste(col, (0, 0), inner)
    if shade:
        sh = inner.copy()
        off = Image.new("L", im.size, 0)
        off.paste(inner, (-int(S * SS * .06), -int(S * SS * .06)))
        sh = Image.fromarray(np.minimum(np.asarray(inner), 255 - np.asarray(off)).astype(np.uint8))
        im.paste(Image.new("RGBA", im.size, shade), (0, 0), sh)
    return im


def circle_pts(cx, cy, r, n=64, wob=0.0, seed=0):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.3, 3)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + wob * (math.sin(3 * a + ph[0]) * .5 + math.sin(5 * a + ph[1]) * .3 + math.sin(2 * a + ph[2]) * .2))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def main():
    os.makedirs(OUT, exist_ok=True)
    C = S * SS / 2
    # sparkle: four-point gold star
    done(inked_poly(poly_star(C, C, C * .22, C * .92, 4), (255, 214, 92, 255), (238, 160, 40, 255), 7), "sparkle")
    done(inked_poly(poly_star(C, C, C * .3, C * .92, 4), (255, 255, 240, 255), (255, 226, 150, 255), 6), "sparkle_w")
    # five-point star
    done(inked_poly(poly_star(C, C, C * .42, C * .92, 5), (255, 200, 70, 255), (232, 140, 36, 255), 8), "star")
    # steam puff: soft white lumpy blob (no ink - steam is see-through), alpha .75
    im = canvas()
    d = ImageDraw.Draw(im)
    for (x, y, r) in [(.5, .55, .32), (.33, .5, .22), (.67, .48, .24), (.5, .35, .25)]:
        d.ellipse([C * 2 * x - C * 2 * r, C * 2 * y - C * 2 * r, C * 2 * x + C * 2 * r, C * 2 * y + C * 2 * r],
                  fill=(255, 250, 240, 200))
    done(im.filter(ImageFilter.GaussianBlur(10)), "steam")
    # dust / straw cloud puff: inked cream lumps
    done(inked_poly(circle_pts(C, C, C * .7, 80, .14, 3), (246, 231, 200, 255), (220, 196, 150, 255), 8), "puff")
    # bubble: inked ring with a highlight
    im = canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([C * .2, C * .2, C * 1.8, C * 1.8], fill=(255, 236, 170, 90), outline=INK, width=9 * SS)
    d.ellipse([C * .55, C * .5, C * .9, C * .8], fill=(255, 255, 255, 230))
    done(im, "bubble")
    # fizz drop: golden cider drop
    pts = [(C + C * .5 * math.sin(a) * (1 - .7 * max(0, -math.cos(a))) , C + C * .62 * -math.cos(a) * .9 + C * .1)
           for a in np.linspace(0, 2 * math.pi, 80, endpoint=False)]
    done(inked_poly(pts, (250, 196, 64, 255), (214, 140, 30, 255), 8), "drop")
    # popcorn: white lumpy cloud with a yellow core
    done(inked_poly(circle_pts(C, C, C * .72, 90, .22, 11), (255, 252, 236, 255), (240, 214, 140, 255), 8), "popcorn")
    # straw bit: thin yellow stalk
    im = canvas()
    d = ImageDraw.Draw(im)
    d.line([(C * .25, C * 1.6), (C * 1.75, C * .4)], fill=INK, width=26 * SS)
    d.line([(C * .25, C * 1.6), (C * 1.75, C * .4)], fill=(240, 200, 90, 255), width=12 * SS)
    done(im, "straw")
    # shock ring: inked warm ring (scaled up in Blender)
    im = canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([C * .08, C * .08, C * 1.92, C * 1.92], outline=INK, width=26 * SS)
    d.ellipse([C * .12, C * .12, C * 1.88, C * 1.88], outline=(255, 210, 90, 255), width=14 * SS)
    done(im, "ring")
    # rays: a burst of 12 warm wedges, soft, for behind big hits
    im = canvas()
    d = ImageDraw.Draw(im)
    for i in range(12):
        a0, a1 = 2 * math.pi * i / 12, 2 * math.pi * (i + .45) / 12
        d.polygon([(C, C), (C + C * math.cos(a0) * 1.4, C + C * math.sin(a0) * 1.4),
                   (C + C * math.cos(a1) * 1.4, C + C * math.sin(a1) * 1.4)], fill=(255, 220, 120, 150))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, C * 2, C * 2], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(C * .35))
    yy, xx = np.mgrid[0:S * SS, 0:S * SS]
    rr = np.hypot(xx - C, yy - C) / C                           # 0 at the centre, 1 at the sprite's edge
    fall = np.clip((0.97 - rr) / 0.45, 0, 1) ** 1.5                # gone before the edge: no square corners
    im.putalpha(Image.fromarray((np.asarray(im.getchannel("A")) * (np.asarray(m) / 255.) * fall).astype(np.uint8)))
    done(im, "rays")
    # feather: black crow feather
    pts = [(C + C * .28 * math.sin(a) * (1 - .55 * max(0, math.cos(a))), C - C * .85 * math.cos(a))
           for a in np.linspace(0, 2 * math.pi, 80, endpoint=False)]
    done(inked_poly(pts, (52, 44, 66, 255), (30, 24, 40, 255), 7), "feather")
    # crumb: pie crust crumb
    done(inked_poly(circle_pts(C, C, C * .55, 7, .25, 5), (222, 166, 84, 255), (180, 116, 50, 255), 9), "crumb")
    # leaves from the maple leaf icon, three tints
    leaf = Image.open(os.path.join(ROOT, "art", "fall-src", "icons", "L1.png")).convert("RGBA").resize((S, S),
                                                                                                    Image.LANCZOS)
    for name, hue in (("leaf_red", 0), ("leaf_orange", 18), ("leaf_gold", 34)):
        h, s, v = leaf.convert("RGB").convert("HSV").split()
        h = h.point(lambda x: (x + hue) % 256)
        tinted = Image.merge("HSV", (h, s, v)).convert("RGB")
        tinted.putalpha(leaf.getchannel("A"))
        tinted.save(os.path.join(OUT, name + ".png"))
    print("fx sprites ->", OUT)


if __name__ == "__main__":
    main()
