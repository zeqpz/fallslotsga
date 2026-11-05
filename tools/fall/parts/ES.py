"""ES Extreme Free Spins badge (a cranberry jack-o'-lantern with big "XFS" letters, flames of red leaves, a crow perched
on top), cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/ES.png. Helpers: _bonus.py.

plates  jack  generated: the picture with the letters and the crow taken off (the carved glowing mouth and the
              pumpkin's top, stem and flames painted in where they were)
        base  made here: the icon itself, with the lined-up jack plate only under the letters and the crow
layers  back to front: the jack (pumpkin, flames, the crow's feet gripping it; the whole back), the crow (its body, head
        and wings, traced from the icon's purple-black and outline), the X, the F and the S (traced from the orange
        fill and the thick black outline round each)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bonus as B                                              # noqa: E402


class _Plates(dict):
    def items(self):
        return [(k, v) for k, v in dict.items(self) if v]


PLATES = _Plates({
    "jack": "Edit the attached picture: remove the three big orange letters X, F and S completely, with their black "
            "shadows, and remove the black crow completely (its body, head, both wings and feet). Paint what is behind "
            "them: the carved jack-o'-lantern's glowing jagged mouth and its dark cranberry-red pumpkin skin where the "
            "letters were, and the round top of the pumpkin with its short brown stem, and the orange flames and red "
            "maple leaves behind, where the crow was. Keep everything else exactly the same: the pumpkin's outline, "
            "its angry glowing eyes, the flames and leaves around it, same position, size, colours, black outline and "
            "cream sticker border. No text at all. Transparent background.",
    "base": "",
})

X_ROUGH = [(140, 480), (428, 480), (428, 782), (140, 782)]
F_ROUGH = [(428, 480), (628, 480), (620, 640), (600, 680), (556, 690), (556, 778), (428, 778)]
S_ROUGH = [(628, 480), (850, 480), (850, 790), (560, 790), (560, 700), (600, 680), (620, 640)]
CROW_ROUGH = [(225, 55), (560, 40), (700, 100), (790, 160), (790, 240), (700, 320), (660, 372), (590, 372), (578, 330),
              (560, 305), (505, 300), (505, 362), (425, 362), (400, 320), (360, 290), (250, 180)]


def _orange(rgb, h, s, v):
    return (h > 12) & (h < 56) & (s > .5) & (v > .55)


def _crow(rgb, h, s, v):
    return ((v < .5) & (((h > 200) & (h < 330)) | (s < .3))) | ((s < .22) & (v < .8))


_ic = B.icon("ES")
_X, _F, _S = (B.piece(_ic, B.inside(p), _orange, ink_grow=24, frac=.15, close=1) for p in (X_ROUGH, F_ROUGH, S_ROUGH))
_C = B.piece(_ic, B.inside(CROW_ROUGH), _crow, ink_grow=6, frac=.15)
if os.path.exists(os.path.join(B.ROOT, "art", "fall-src", "parts", "ES", "plate_jack.png")):
    B.make_base("ES", "jack", [_X, _F, _S, _C])

LAYERS = [
    dict(name="jack", src="plate:base", pivot=(500, 940), parent="root"),
    dict(name="crow", src="art", cut="poly", poly=B.polygon(_C), pivot=(530, 330), parent="jack"),
    dict(name="let_x", src="art", cut="poly", poly=B.polygon(_X), pivot=(290, 760), parent="jack"),
    dict(name="let_f", src="art", cut="poly", poly=B.polygon(_F), pivot=(500, 765), parent="jack"),
    dict(name="let_s", src="art", cut="poly", poly=B.polygon(_S), pivot=(715, 770), parent="jack"),
]
