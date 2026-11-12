"""The crow's wings (2026-11-10): two small layers the scarecrow's rig spreads when the crow flaps off its perch.

The crow is one painted picture with its wings folded. For the flight in big_win (and the startled wing-flicks in
the other clips) it gets two drawn wings, in its own colours and line weight, each on a bone of its own
(scarecrow.BONES wing_l / wing_r, children of the crow). At rest a wing lies folded along the crow's back, wholly
BEHIND its body (the game draws the wings under the crow), so the rest pose shows nothing; spreading it is a turn
about its shoulder and a scale-up. wing_r is wing_l mirrored across its own axis: it opens the other way.

  .venv/Scripts/python.exe -I tools/fall/gen_crow_wing.py [--check]
-> art/fall-src/scare/wing_l.png, wing_r.png (1024 x 1536, like every layer); --check also prints how much of the
   folded wing would show round the crow (must be 0)."""
import os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender"))
import scarecrow as SC

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAY = os.path.join(ROOT, "art", "fall-src", "scare")
FILL, LIGHT, LINE = (47, 39, 49), (63, 54, 68), (15, 11, 15)
Q = 4                                   # supersampling


def shape(L):
    """The wing's outline in its own frame: s along the axis (0 root .. L tip), t across (+ the leading edge)."""
    lead = [(0, 9), (.18 * L, 15), (.42 * L, 17), (.68 * L, 14), (.88 * L, 8), (L, 0)]
    trail = [(.955 * L, -9), (.90 * L, -7), (.82 * L, -20), (.75 * L, -15), (.66 * L, -28), (.58 * L, -21),
             (.49 * L, -31), (.41 * L, -23), (.31 * L, -29), (.23 * L, -20), (.12 * L, -22), (0, -11)]
    return lead, trail


def smooth(pts, n=10):
    """Catmull-Rom through the points (open)."""
    P = np.array([pts[0]] + list(pts) + [pts[-1]], float)
    out = []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, n, endpoint=False):
            a, b, c, d = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(P[-2])
    return np.array(out)


def draw(mirror):
    J, T = np.array(SC.BONES["wing_l"][0], float), np.array(SC.BONES["wing_l"][1], float)
    L = float(np.hypot(*(T - J)))
    e = (T - J) / L
    n = np.array([-e[1], e[0]]) * (-1 if mirror else 1)

    def px(s, t):
        return tuple((J + e * s + n * t) * Q)
    lead, trail = shape(L)
    lead_s = smooth(lead)
    # the trailing edge keeps its feather points sharp: straight runs between tips and notches, tips rounded a little
    outline = [px(*p) for p in lead_s] + [px(*p) for p in trail]
    W, H = SC.W_PX * Q, SC.H_PX * Q
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.6 * Q)).point(lambda v: 255 if v > 118 else 0)   # rounded corners
    col = Image.new("RGB", (W, H), FILL)
    d = ImageDraw.Draw(col)
    # the coverts: a lighter band under the leading edge
    band = [px(s, t - 3) for s, t in lead_s] + [px(s, t - 13 + 5 * (s / L)) for s, t in lead_s[::-1] if .04 * L < s < .86 * L]
    d.polygon(band, fill=LIGHT)
    # the feathers' partings: a line from each notch up toward the coverts
    for (s, t) in [trail[1], trail[3], trail[5], trail[7], trail[9]]:
        d.line([px(s, t), px(s - .10 * L, t + 16)], fill=LINE, width=int(2.2 * Q))
    d.line([px(s, t - 13 + 5 * (s / L)) for s, t in lead_s if .04 * L < s < .86 * L], fill=LINE, width=int(2.0 * Q))
    # the ink outline, inside the shape's edge
    a = np.asarray(mask, np.float32) / 255
    inner = np.asarray(mask.filter(ImageFilter.MinFilter(int(4.2 * Q) | 1)), np.float32) / 255
    rgb = np.asarray(col, np.float32)
    edge = (a - inner)[..., None]
    rgb = rgb * (1 - edge) + np.array(LINE, np.float32) * edge
    out = np.concatenate([rgb, a[..., None] * 255], -1).astype(np.uint8)
    im = Image.fromarray(out, "RGBA").convert("RGBa").resize((SC.W_PX, SC.H_PX), Image.LANCZOS).convert("RGBA")
    return im


def main():
    for side, mirror in (("l", False), ("r", True)):
        im = draw(mirror)
        im.save(os.path.join(LAY, f"wing_{side}.png"))
        print("wing_" + side, im.getbbox())
        if "--check" in sys.argv:
            fixed = os.path.join(ROOT, "art", "blender", "chars", "scarecrow", "layers", "crow.png")
            crow = np.asarray(Image.open(fixed if os.path.exists(fixed) else os.path.join(LAY, "crow.png")).convert("RGBA"))[..., 3] / 255.
            w = np.asarray(im)[..., 3] / 255.
            show = w * (1 - crow)
            print("  folded wing showing round the crow: max", round(float(show.max()), 3), "px over .02:", int((show > .02).sum()))


if __name__ == "__main__":
    main()
