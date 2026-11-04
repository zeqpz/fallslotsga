"""H3 Cornucopia, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H3.png.

plates  horn   the wicker horn with every fruit taken out (its mouth empty), the leaves left where they are
        back   the horn with only the corn and the top apple in it (the fruit in front of them taken away)
        front  the whole spill less the grapes and the yellow leaf at the front
layers  back to front (see tools/fall/parts/H1.py): the horn (with the leaves tucked behind the fruit), its curled
        tip, the corn, the apple in the horn's mouth, the pumpkin, the two red apples at the left, the yellow leaf in
        front and the bunch of grapes"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mask_poly as MP

_KEEP = ("Keep everything else exactly the same: same position, same size, same colours, same black outline and the "
         "same cream sticker border round it. Transparent background.")
PLATES = {
    "horn": "Edit the attached picture: remove all the fruit - the corn cob with its green husk leaves, all three red "
            "apples with their stems and little leaves, the orange pumpkin, the bunch of purple grapes - and the yellow "
            "leaf at the bottom front. Keep the wicker horn of plenty and the other leaves exactly where they are: the "
            "big orange maple leaf in the horn's mouth, the red maple leaf at the far left, the green leaves at the "
            "left, the yellow leaf at the right of the horn's mouth, the green grape leaf with its curly tendril and "
            "the red leaf at the bottom right. Paint what the fruit hid: the dark inside of the empty open horn mouth, "
            "the woven wicker of the horn and the hidden parts of those leaves. " + _KEEP,
    "back": "Edit the attached picture: remove the orange pumpkin, the two red apples at the front left, the bunch of "
            "purple grapes and the yellow leaf at the bottom front. Paint what they hid: the WHOLE corn cob with its "
            "green husk leaves (its lower end), the WHOLE red apple in the horn's mouth (its lower half), the woven "
            "wicker horn and the dark inside of its mouth, and the hidden parts of the other leaves. " + _KEEP,
    "front": "Edit the attached picture: remove only the bunch of purple grapes and the yellow leaf at the bottom front. "
             "Paint what they hid: the WHOLE orange pumpkin (its lower right part and its bottom), the whole red apple "
             "at the front left, and the leaves behind the grapes - the green grape leaf with its curly tendril and "
             "the red leaf at the bottom right. " + _KEEP,
}

def _hue(rgb):
    import numpy as np
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(2), rgb.min(2)
    d = np.maximum(mx - mn, 1e-6)
    return np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60


def _box(x0, y0, x1, y1):
    return MP.inside([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


# the whole of each fruit taken from a plate (its hidden part too), in icon px
APPLE_TOP = [(495, 405), (600, 392), (682, 400), (702, 470), (692, 548), (600, 578), (510, 562), (490, 480)]
PUMPKIN = [(310, 520), (400, 470), (445, 440), (520, 445), (560, 478), (640, 498), (676, 560), (682, 660), (640, 752),
           (540, 778), (420, 772), (330, 722), (305, 620)]
APPLES = [(125, 560), (150, 522), (155, 468), (225, 466), (240, 528), (300, 540), (330, 598), (402, 628), (418, 700),
          (398, 805), (300, 818), (196, 804), (168, 700), (122, 650)]
_A = dict(apple_top=MP.inside(APPLE_TOP), pumpkin=MP.inside(PUMPKIN), apples=MP.inside(APPLES),
          apple_top_leaf=_box(580, 392, 680, 452), pumpkin_stem=_box(440, 440, 525, 545),
          apples_leaf=_box(150, 462, 222, 548) | _box(205, 568, 300, 636))


def _ndi_dilate(m, n):
    from scipy import ndimage
    return ndimage.binary_dilation(m, iterations=n)


def _ink(val):
    return val < .3


def _with_ink(body, val):
    """a fruit's own colours and the ink right round them (not stray plate lines further off)"""
    return body | (_ink(val) & _ndi_dilate(body, 12))


def apple_top_keep(rgb, sat, val):
    h = _hue(rgb)
    red = (sat > .35) & ((h > 330) | (h < 9)) & (val > .2)
    return _A["apple_top"] & _with_ink(red | (_A["apple_top_leaf"] & (sat > .25) & (val > .3)), val)


def pumpkin_keep(rgb, sat, val):
    h = _hue(rgb)
    orange = (sat > .4) & (h >= 9) & (h < 37) & (val > .3)
    return _A["pumpkin"] & _with_ink(orange, val)


def apples_keep(rgb, sat, val):
    """the plate's apples where the drawing's own do not show them (behind the front leaf): all of the apple there -
    its red, shine and ink - but not the pumpkin's orange, a leaf's yellow or the cream border"""
    h = _hue(rgb)
    warm = (sat > .4) & (h >= 12) & (h < 70)
    cream = (rgb[..., 0] > .85) & (rgb[..., 1] > .78) & (rgb[..., 2] > .6)
    return _A["apples"] & ~warm & ~cream & (val > .02)


PUMPKIN_ART = [(312, 580), (330, 535), (400, 500), (445, 490), (448, 446), (512, 446), (520, 485), (600, 492),
               (655, 532), (680, 600), (676, 660), (650, 720), (560, 772), (420, 772), (335, 718)]
APPLE_TOP_ART = [(495, 420), (560, 400), (585, 393), (600, 396), (676, 396), (684, 440), (682, 500), (650, 525),
                 (600, 505), (520, 500), (495, 470)]
APPLES_ART = [(105, 640), (110, 560), (140, 520), (155, 470), (225, 466), (238, 520), (300, 540), (330, 598), (400, 625),
              (415, 700), (395, 800), (300, 815), (196, 804), (185, 700), (150, 662)]
CORN = [(245, 345), (300, 298), (332, 290), (372, 330), (405, 385), (430, 392), (482, 400), (492, 440), (478, 470),
        (450, 470), (445, 495), (400, 505), (355, 540), (352, 585), (238, 585), (238, 470), (215, 450)]
GRAPES = [(445, 640), (520, 600), (600, 568), (670, 560), (730, 565), (745, 630), (745, 720), (740, 800), (700, 860),
          (600, 870), (470, 860), (440, 780)]
LEAF_FRONT = [(285, 700), (330, 688), (420, 688), (470, 720), (468, 800), (462, 880), (300, 880), (280, 800)]
_A["pumpkin"] &= _ndi_dilate(MP.region("H3", GRAPES) | MP.region("H3", LEAF_FRONT), 5)
# the plate only fills what the drawing's own apples do not show (their parts behind the pumpkin / the front leaf)
from scipy import ndimage as _ndi
_A["apple_top"] &= ~_ndi.binary_erosion(MP.region("H3", APPLE_TOP_ART), iterations=5)
_A["apples"] &= ~_ndi.binary_erosion(MP.region("H3", APPLES_ART), iterations=5)
PUMPKIN_CUT = MP.outline(MP.region("H3", PUMPKIN_ART, [GRAPES, LEAF_FRONT, CORN]))


TIP = [(690, 60), (995, 60), (995, 272), (800, 272), (792, 255), (690, 255)]
LAYERS = [
    dict(name="horn", src="plate:horn", pivot=(760, 560), parent="root"),
    dict(name="horn_tip", src="art", cut="poly", poly=TIP, pivot=(870, 272), parent="horn"),
    # the leaves tucked behind the fruit: the drawing's own, still on the horn (the plate holds their hidden parts)
    dict(name="leaf_maple", src="art", poly=[(405, 268), (645, 268), (655, 398), (600, 412), (470, 448), (405, 380)],
         pivot=(520, 420), parent="horn"),
    dict(name="leaf_gold", src="art", poly=[(630, 470), (780, 468), (795, 600), (765, 662), (738, 610), (695, 562),
                                            (645, 560)], pivot=(660, 560), parent="horn"),
    dict(name="leaf_vine", src="art", poly=[(738, 620), (830, 618), (905, 690), (900, 800), (760, 806), (738, 760)],
         pivot=(750, 680), parent="horn"),
    # the fruit, back to front
    dict(name="corn", src="art", poly=CORN, pivot=(410, 560), parent="horn"),
    dict(name="apple_top_fill", src="diff:back-horn", keep=apple_top_keep, pivot=(595, 560), parent="horn"),
    dict(name="apple_top", src="art", poly=APPLE_TOP_ART, pivot=(595, 560), parent="apple_top_fill"),
    # the pumpkin: the drawing's own, and under it (riding it) its parts the grapes and the front leaf hide, from
    # the plate (so the apple behind it keeps its plate-painted lower half - see cut_parts' "own" overlay)
    dict(name="pumpkin_fill", src="diff:front-horn", keep=pumpkin_keep, pivot=(500, 765), parent="horn"),
    dict(name="pumpkin", src="art", cut="poly", poly=PUMPKIN_CUT, pivot=(500, 765), parent="pumpkin_fill"),
    dict(name="apples_fill", src="diff:front-horn", keep=apples_keep, pivot=(280, 805), parent="horn"),
    dict(name="apples", src="art", poly=APPLES_ART, pivot=(280, 805), parent="apples_fill"),
    dict(name="leaf_red", src="art", poly=[(30, 640), (120, 600), (182, 640), (196, 700), (200, 830), (40, 830)],
         pivot=(190, 700), parent="apples"),
    dict(name="leaf_front", src="art", poly=LEAF_FRONT, pivot=(455, 770), parent="apples_fill"),
    dict(name="grapes", src="art", poly=GRAPES, pivot=(690, 580), parent="horn"),
]
