"""BS Free Spins badge (a pumpkin with big gold "FS" letters, two maple leaves behind), cut into parts
(tools/fall/cut_parts.py). Icon px of art/fall-src/icons/BS.png. Helpers: tools/fall/parts/_bonus.py.

plates  badge  generated: the picture with the letters taken off (the pumpkin's ribs painted in where they were)
        base   made here: the icon itself, with the lined-up badge plate only under the letters (so at rest the back
               layer is exactly the icon, and a letter moving off it shows bare pumpkin, never a ghost of itself)
layers  back to front: the badge (pumpkin, stem; the whole back), the two maple leaves (cut from the art along their
        own outlines), the F and the S (each traced from the icon's gold, 3D shadow and outline: cut "poly")"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bonus as B                                              # noqa: E402


class _Plates(dict):
    """"base" is made here; cut_parts.py plates only asks the generator for the others"""
    def items(self):
        return [(k, v) for k, v in dict.items(self) if v]


PLATES = _Plates({
    "badge": "Edit the attached picture: remove the two big gold letters F and S completely, with their dark brown 3D "
             "shadows. Paint the bare orange pumpkin where they were: its smooth glossy orange ribs and the dark rib "
             "lines continuing naturally down across the middle of the pumpkin. Keep everything else exactly the same: "
             "the pumpkin's outline and shape, its brown curly stem, the two red maple leaves behind it, the same "
             "position, size, colours, black outline and cream sticker border. No text at all. Transparent background.",
    "base": "",
})

F_ROUGH = [(160, 440), (205, 398), (300, 362), (488, 340), (496, 470), (470, 520), (462, 660), (440, 700), (390, 840),
           (160, 840)]
S_ROUGH = [(488, 340), (840, 340), (840, 840), (390, 840), (440, 700), (462, 660), (470, 520), (496, 470)]
LEAF_L = [(40, 110), (400, 110), (420, 250), (330, 290), (220, 320), (140, 420), (40, 430)]
LEAF_R = [(640, 120), (960, 120), (960, 470), (860, 450), (800, 330), (700, 300), (640, 260)]


def _gold(rgb, h, s, v):
    gold = (h > 32) & (h < 62) & (s > .3) & (v > .55)            # the letter's gold and its darker gold
    hi = (h > 30) & (h < 65) & (v > .85) & (s > .12)            # its pale highlights
    brown = (h > 5) & (h < 45) & (v > .12) & (v < .6) & (s > .3)  # its brown 3D shadow
    return gold | hi | brown


_ic = B.icon("BS")
_F = B.piece(_ic, B.inside(F_ROUGH), _gold, ink_grow=14)
_S = B.piece(_ic, B.inside(S_ROUGH), _gold, ink_grow=14)
if os.path.exists(os.path.join(B.ROOT, "art", "fall-src", "parts", "BS", "plate_badge.png")):
    B.make_base("BS", "badge", [_F, _S])

LAYERS = [
    dict(name="badge", src="plate:base", pivot=(500, 930), parent="root"),
    dict(name="leaf_l", src="art", poly=LEAF_L, pivot=(330, 330), parent="badge"),
    dict(name="leaf_r", src="art", poly=LEAF_R, pivot=(690, 330), parent="badge"),
    dict(name="let_f", src="art", cut="poly", poly=B.polygon(_F), pivot=(320, 790), parent="badge"),
    dict(name="let_s", src="art", cut="poly", poly=B.polygon(_S), pivot=(640, 800), parent="badge"),
]
