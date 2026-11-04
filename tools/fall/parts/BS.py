"""BS Golden Wishbone, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/BS.png.

The drawing's ink lines have gaps (the whole icon is one flat region), so the art parts are cut "poly" and the gold and
the left tail come off the plates through a position-aware keep (only that part's colour, inside that part's polygon).
plates  bare  the wishbone alone (the stem painted in through the knot, the prongs whole under the tails)
        bow   the ribbon alone (both tails whole, under the left prong and the knot)
layers  back to front: the left tail (behind the left prong), the right prong, the top (stem + fork), the left prong (in
        front of the fork, carrying the big star on it), the right tail (in front of the right prong), the bow"""
import os

import numpy as np
from PIL import Image, ImageDraw

class _Plates(dict):
    """The plates: "none" is made here (an empty picture: the plate a whole-plate part is told apart from, so its keep
    alone says what it is), the rest by the generator (cut_parts.py plates only asks for those)."""
    def items(self):
        return [(k, v) for k, v in dict.items(self) if v]


PLATES = _Plates({
    "bare": "Edit the attached picture: remove the red ribbon bow completely - both bow loops, the knot and both long "
            "ribbon tails - and remove ALL the white four-point sparkle stars. Paint the golden wishbone whole where the "
            "ribbon covered it: its rounded top stem continues smoothly straight down through where the knot was into "
            "the fork where the two legs join, and the tops of both legs are whole. Keep the wishbone exactly the same: "
            "same position, same size, same golden colours and glossy shading, same black outline, and the cream "
            "sticker border round it. Transparent background.",
    "ribbon": "Edit the attached picture: remove the LEFT leg of the golden wishbone - the long gold leg that runs from "
              "the fork down to the lower left - and ALL the white four-point sparkle stars. Paint the red ribbon's left "
              "tail whole where that leg covered it: the left tail runs unbroken from under the knot out to its forked "
              "end. Where the rest of the leg was, leave empty transparent background. Keep everything else exactly the "
              "same and in exactly the same place: the bow loops, the knot, both ribbon tails, the gold stem and the "
              "right leg - same position, same size, same colours, same black outline and the cream sticker border "
              "round it. Transparent background.",
    "none": "",
})
_none = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                     "art", "fall-src", "parts", "BS", "plate_none.png")
if not os.path.exists(_none):
    os.makedirs(os.path.dirname(_none), exist_ok=True)
    Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)).save(_none)


def _poly(pts):
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return np.asarray(im) > 0


def _sat(rgb):
    mx, mn = rgb.max(2), rgb.min(2)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)


def gold_in(pts):
    where = _poly(pts)

    def keep(rgb, sat, mx):
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        return where & (r >= g * .95) & (g >= b) & (mx > .3) & (sat > .3)
    return keep


def red_in(pts):
    where = _poly(pts)

    def keep(rgb, sat, mx):
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        return where & (r > 1.6 * g + .02) & (r > 1.3 * b) & (mx > .22)
    return keep


TAIL_L = [(90, 380), (150, 320), (300, 262), (350, 238), (400, 222), (470, 214), (500, 235), (500, 300), (470, 340),
          (400, 430), (300, 530), (150, 560), (90, 480)]
TOP = [(470, 20), (650, 20), (650, 280), (620, 330), (560, 380), (532, 428), (519, 462), (506, 456), (470, 360),
       (440, 335), (430, 290), (460, 200)]
PRONG_R = [(508, 365), (620, 305), (700, 380), (980, 760), (980, 1000), (560, 1000), (525, 480), (512, 420)]
BOW = [(222, 268), (222, 150), (285, 35), (420, 25), (475, 62), (505, 140), (517, 186), (560, 184), (594, 188),
       (603, 152), (612, 188), (632, 190), (640, 140), (700, 118), (800, 120), (880, 200), (885, 330), (860, 390),
       (800, 392), (758, 374), (720, 360), (673, 330), (602, 276), (562, 266), (546, 292), (530, 292), (510, 284), (490, 280), (472, 276),
       (461, 252), (463, 230), (400, 237), (350, 251), (310, 274), (283, 266), (265, 254)]
PRONG_L = [(480, 292), (468, 282), (456, 270), (427, 300), (390, 347), (380, 358), (370, 351), (355, 298), (342, 350),
           (293, 366), (342, 382), (347, 403), (307, 437), (270, 467), (240, 490), (215, 505), (160, 530), (60, 600),
           (0, 650), (0, 1000), (470, 1000), (520, 520), (518, 470), (512, 420), (505, 372)]
TAIL_R = [(545, 262), (604, 262), (676, 316), (724, 345), (770, 360), (790, 372), (850, 420), (920, 470), (930, 530),
          (880, 600), (830, 590), (805, 572), (794, 560), (777, 550), (764, 540), (753, 530), (744, 520), (736, 510),
          (728, 500), (721, 490), (713, 480), (707, 470), (700, 460), (693, 450), (686, 440), (679, 430), (672, 420),
          (652, 410), (635, 402), (621, 394), (609, 386), (599, 378), (591, 370), (583, 362), (577, 354), (571, 346),
          (565, 338), (561, 330), (557, 322), (555, 314), (552, 306), (550, 298), (548, 290)]

LAYERS = [
    dict(name="tail_l", src="diff:ribbon-bare", keep=red_in(TAIL_L), pivot=(475, 262), parent="bow"),
    dict(name="prong_r", src="diff:bare-none", keep=gold_in(PRONG_R), pivot=(528, 398), parent="top"),
    dict(name="top", src="diff:bare-none", keep=gold_in(TOP), pivot=(515, 395), parent="root"),
    dict(name="prong_l", src="art", cut="poly", poly=PRONG_L, pivot=(500, 398), parent="top"),
    dict(name="tail_r", src="art", cut="poly", poly=TAIL_R, pivot=(565, 272), parent="bow"),
    dict(name="bow", src="art", cut="poly", poly=BOW, pivot=(515, 240), parent="top"),
]
