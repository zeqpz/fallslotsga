"""ES The Crow, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/ES.png.

The crow is black, so the cutter's "ink" is most of it: every art part is cut "poly" (the polygon's own shape).
plates  torso  the crow's body alone (no head, wings, legs or feathers): the shoulders and the neck painted in. It is the
               back layer, kept inside the icon's own silhouette, so at rest it is hidden and it only shows where a wing or
               the head swings off the body
        none   an empty picture made here (a whole-plate layer is told apart from nothing)
layers  back to front: the torso plate, the four loose feathers, the wings (behind the body), the feet, the body, the
        head (with its beak)"""
import os

import numpy as np
from PIL import Image, ImageDraw


class _Plates(dict):
    """"none" is made here; cut_parts.py plates only asks the generator for the others"""
    def items(self):
        return [(k, v) for k, v in dict.items(self) if v]


PLATES = _Plates({
    "torso": "Edit the attached picture: remove the crow's head (with its beak, eyes and grin), both wings, both legs "
             "and feet, and ALL the loose floating feathers. Keep only the crow's round black feathered body (its torso), "
             "and paint it whole where those covered it: a short rounded feathered neck at the top where the head was, "
             "and full rounded feathered shoulders on both sides where the wings joined. Keep the body exactly the same: "
             "same position, same size, same black and grey feather shading, same black outline, and a cream sticker "
             "border round it. Transparent background.",
    "none": "",
})
_none = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                     "art", "fall-src", "parts", "ES", "plate_none.png")
if not os.path.exists(_none):
    os.makedirs(os.path.dirname(_none), exist_ok=True)
    Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)).save(_none)

_ICON = os.path.join(os.path.dirname(_none), "..", "..", "icons", "ES.png")


def _poly(pts):
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return np.asarray(im) > 0


def torso_keep(rgb, sat, mx):
    """the plate's crow (not its cream border), only inside the icon's own crow (so at rest it never shows past it)"""
    a = np.asarray(Image.open(_ICON).convert("RGBA"))
    crow = (a[..., 3] > 128) & ~((a[..., 0] > 200) & (a[..., 1] > 185) & (a[..., 2] > 140))
    cream = (rgb[..., 0] > .8) & (rgb[..., 1] > .72) & (rgb[..., 2] > .55)
    return crow & ~cream & (mx < .75) & _poly(TORSO)


TORSO = [(240, 250), (780, 250), (780, 760), (240, 760)]
HEAD = [(338, 300), (342, 220), (358, 140), (380, 70), (460, 30), (560, 40), (640, 90), (700, 170), (748, 205),
        (762, 300), (748, 360), (724, 412), (705, 432), (680, 470), (650, 525), (610, 525), (570, 480), (510, 462),
        (450, 455), (400, 430), (365, 395), (345, 372), (322, 345)]
BODY = [(345, 372), (365, 395), (400, 430), (450, 455), (510, 462), (570, 480), (610, 525), (650, 525), (680, 470),
        (705, 432), (695, 480), (690, 540), (688, 590), (680, 625), (665, 660), (650, 700), (620, 735), (560, 750),
        (470, 750), (400, 740), (340, 720), (282, 690), (292, 630), (305, 580), (318, 520), (330, 460), (350, 420),
        (358, 392)]
WING_L = [(15, 330), (60, 260), (115, 205), (200, 200), (248, 225), (268, 290), (300, 335), (345, 372), (400, 420),
          (410, 520), (380, 640), (330, 700), (285, 700), (262, 660), (215, 640), (140, 625), (70, 590), (20, 520),
          (5, 420)]
WING_R = [(705, 432), (720, 395), (760, 355), (830, 335), (900, 340), (950, 400), (980, 520), (975, 610), (935, 650),
          (860, 690), (790, 712), (720, 720), (650, 700), (620, 640), (630, 540), (650, 470)]
FOOT_L = [(370, 700), (480, 690), (490, 800), (500, 880), (450, 940), (330, 945), (230, 940), (185, 880), (200, 800),
          (290, 780), (365, 760)]
FOOT_R = [(550, 690), (640, 690), (650, 770), (760, 790), (815, 860), (790, 950), (660, 955), (530, 935), (505, 860),
          (540, 790)]
F_UL = [(250, 130), (330, 120), (360, 165), (335, 250), (305, 300), (268, 290), (248, 225), (226, 180)]
F_UR = [(760, 185), (830, 195), (875, 260), (880, 320), (840, 345), (790, 330), (750, 260)]
F_LL = [(125, 635), (215, 640), (262, 690), (275, 760), (230, 775), (175, 740), (130, 690)]
F_LR = [(745, 720), (800, 708), (870, 745), (905, 800), (880, 830), (810, 825), (760, 790)]

LAYERS = [
    dict(name="torso", src="diff:torso-none", keep=torso_keep, pivot=(510, 560), parent="body"),
    dict(name="f_ul", src="art", cut="poly", poly=F_UL, pivot=(290, 215), parent="root"),
    dict(name="f_ur", src="art", cut="poly", poly=F_UR, pivot=(815, 265), parent="root"),
    dict(name="f_ll", src="art", cut="poly", poly=F_LL, pivot=(200, 700), parent="root"),
    dict(name="f_lr", src="art", cut="poly", poly=F_LR, pivot=(825, 770), parent="root"),
    dict(name="wing_l", src="art", cut="poly", poly=WING_L, pivot=(365, 410), parent="body"),
    dict(name="wing_r", src="art", cut="poly", poly=WING_R, pivot=(690, 455), parent="body"),
    dict(name="foot_l", src="art", cut="poly", poly=FOOT_L, pivot=(430, 715), parent="root"),
    dict(name="foot_r", src="art", cut="poly", poly=FOOT_R, pivot=(595, 715), parent="root"),
    dict(name="body", src="art", cut="poly", poly=BODY, pivot=(510, 720), parent="root"),
    dict(name="head", src="art", cut="poly", poly=HEAD, pivot=(530, 455), parent="body"),
]
