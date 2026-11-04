"""H6 Ear of Corn, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H6.png.

Back to front: the husks' hidden bases (static, only seen when a leaf or the cob moves off them), the right husk,
the tall left husk with its curl, the lower left husk, the cob, the cob's bottom end that the front leaf hides (from
a plate, riding the cob), the front husk leaf, the stalk end.

Every visible part is cut from the icon itself (src "art"), so at rest nothing shows a plate's redraw; the plates only
fill in what was hidden. Two plates are made here, never generated (see the end of this file):
  sil  the icon's silhouette in flat black: "diff:<plate>-sil" is all of that plate's paint, lined up exactly, and
       takes none of the icon's sticker border; `keep` (position-aware here: a mask) cuts it down to the hidden piece
  ico  the icon itself: "diff:ico-sil" + keep = the outer sticker border next to one part, so each part carries its
       whole border with it (an art cut takes only the inner ~16 px of it) - the "<part>_rim" layers"""
import os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ID = "H6"
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_ICON = np.asarray(Image.open(os.path.join(_ROOT, "art", "fall-src", "icons", ID + ".png")).convert("RGBA"))
_ON = _ICON[..., 3] > 128


def _poly(p):
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon([tuple(q) for q in p], fill=255)
    return np.asarray(im) > 0


def _green(rgb, mx):
    return (rgb[..., 1] > rgb[..., 0] + .01) & (mx > .24)


def _cream(rgb, sat):
    return (rgb[..., 0] > .84) & (rgb[..., 1] > .78) & (rgb[..., 2] > .6) & (sat < .26)


HUSK_LT = [(150, 90), (340, 80), (440, 215), (350, 320), (318, 400), (300, 520), (280, 520), (240, 420), (260, 300),
           (230, 250), (170, 230)]
HUSK_LL = [(60, 380), (240, 380), (298, 460), (296, 560), (305, 775), (200, 790), (120, 700), (90, 600), (50, 500)]
HUSK_R = [(600, 650), (700, 520), (780, 400), (860, 370), (955, 420), (955, 615), (820, 615), (760, 560), (700, 665)]
COB = [(290, 800), (285, 480), (340, 330), (440, 220), (560, 130), (700, 45), (830, 45), (875, 150), (820, 330),
       (760, 420), (680, 540), (600, 630), (470, 700), (340, 760)]
FRONT = [(335, 800), (355, 730), (450, 665), (600, 635), (760, 650), (840, 720), (870, 890), (780, 905), (620, 890),
         (450, 900), (320, 890)]
COB_HID = [(255, 890), (265, 640), (600, 560), (730, 600), (660, 700), (480, 810), (340, 890)]
STALK = [(140, 760), (300, 750), (350, 800), (350, 880), (290, 955), (140, 955)]

_HID = ndimage.binary_dilation(_poly(COB) | _poly(FRONT) | _poly(STALK), iterations=35) & ndimage.binary_erosion(_ON, iterations=6)


def keep_husks(rgb, sat, mx):
    """the husks plate where the cob, the front leaf and the stalk hid it (the leaves' bases)"""
    return _HID & ndimage.binary_dilation(_green(rgb, mx) | (mx <= .24), iterations=1) & ~_cream(rgb, sat)


def keep_cob(rgb, sat, mx):
    """the cob plate's cob where the front leaf and the stalk hid it (its bottom end), and 2 px over their outline:
    this layer is drawn in front of the cob as cut, so the front leaf's outline the cob's cut carries is covered"""
    import cut_parts as cp
    icon = _ICON.astype(np.int16)
    under = ndimage.binary_dilation(cp.art_cut(icon, FRONT) | cp.art_cut(icon, STALK), iterations=2)
    g = ndimage.binary_dilation(_green(rgb, mx), iterations=2)
    return under & _poly(COB_HID) & ~g & ~_cream(rgb, sat) & ndimage.binary_erosion(_ON, iterations=6)


PLATES = {
    "cob": "Edit the attached picture: remove the big green husk leaf that wraps across the FRONT of the bottom of the "
           "corn cob (the leaf lying over the lower end of the cob, from the stalk to the curled tip at the bottom right), "
           "and remove the cut stalk stump at the bottom left. Paint the rest of the corn cob where that leaf covered it: "
           "more rows of the same golden-yellow kernels with the same black outlines, ending in the cob's rounded bottom "
           "end. Keep everything else exactly the same: the same position and size of the cob, the same green husk "
           "leaves behind it on the left and on the right, the same colours, the same black outlines and the same cream "
           "sticker border. Transparent background.",
    "husks": "Edit the attached picture: remove the corn cob completely (all the yellow kernels), the big green husk leaf "
             "that wraps across the front of the bottom of the cob, and the cut stalk stump at the bottom left. Keep ONLY "
             "the green husk leaves that are behind the cob - the tall leaf curling over at the top left, the leaf curling "
             "down at the left, and the long leaf with the curled tip on the right - and paint their hidden parts where "
             "the cob covered them, so each leaf is whole and they all meet at the bottom left where the stalk was. Keep "
             "those leaves exactly where they are: same position, same size, same colours, same black outlines. "
             "Transparent background.",
}
LAYERS = [
    dict(name="husks_back", src="diff:husks-sil", keep=keep_husks, pivot=(300, 760), parent="root"),
    dict(name="husk_r", src="art", poly=HUSK_R, pivot=(665, 650), parent="root"),
    dict(name="husk_lt", src="art", poly=HUSK_LT, pivot=(300, 520), parent="root"),
    dict(name="husk_ll", src="art", poly=HUSK_LL, pivot=(265, 770), parent="root"),
    dict(name="cob", src="art", poly=COB, pivot=(400, 730), parent="root"),
    dict(name="cob_fill", src="diff:cob-sil", keep=keep_cob, pivot=(400, 730), parent="cob"),
    dict(name="husk_front", src="art", poly=FRONT, pivot=(340, 790), parent="root"),
    dict(name="stalk", src="art", poly=STALK, pivot=(310, 800), parent="root"),
]


# ---------------------------------------------------------------- made here: the sil / ico plates and the rims
def _rims(layers, owner=None):
    """Each art part gets a "<part>_rim" layer just in front of it, riding on it: the part again with whatever of the icon
    no art cut took (mostly the outer sticker border and its ink) that lies nearest that part. owner: {art layer: bone
    it rides} (default the layer itself)."""
    import cut_parts as cp
    icon = _ICON.astype(np.int16)
    arts = [L for L in layers if L["src"] == "art"]
    masks = [(cp.poly_mask(L["poly"]) & (icon[..., 3] > 0)) if L.get("cut") == "poly" else cp.art_cut(icon, L["poly"])
             for L in arts]
    movers = np.zeros(_ON.shape, bool)
    lab = np.zeros(_ON.shape, np.int32)
    for k, m in enumerate(masks):
        movers |= m
        lab[m & (lab == 0)] = k + 1
    band = (_ICON[..., 3] > 0) & ~movers                    # whatever of the icon no art cut took
    idx = ndimage.distance_transform_edt(lab == 0, return_distances=False, return_indices=True)
    near = lab[idx[0], idx[1]]
    out = []
    for L in layers:
        if L["src"] == "art":
            k = 1 + arts.index(L)
            arc = band & (near == k)
            # with the part itself under it (the same pixels): the border pieces join up through it into one patch,
            # and they overlap the part (no seam)
            arc = ndimage.binary_dilation(arc | masks[k - 1], iterations=2) & (_ICON[..., 3] > 0)
            if arc.sum() > 300:
                out.append(dict(name=L["name"] + "_rim", src="diff:ico-sil", keep=lambda rgb, sat, mx, a=arc: a,
                                pivot=L["pivot"], parent=(owner or {}).get(L["name"], L["name"]), rim_of=L["name"]))
        out.append(L)
    # each rim right after its part (it is the part again, so it adds only what lies round it)
    res = []
    for L in out:
        if "rim_of" not in L:
            res.append(L)
            for R in out:
                if R.get("rim_of") == L["name"]:
                    res.append({k: v for k, v in R.items() if k != "rim_of"})
    return res


if sys.argv[2:3] == ["cut"]:
    PLATES["sil"] = PLATES["ico"] = None
    _d = os.path.join(_ROOT, "art", "fall-src", "parts", ID)
    os.makedirs(_d, exist_ok=True)
    _a = np.zeros((1000, 1000, 4), np.uint8)
    _a[..., 3] = ndimage.binary_dilation(_ON, iterations=4) * 255
    Image.fromarray(_a, "RGBA").save(os.path.join(_d, "plate_sil.png"))
    Image.fromarray(_ICON, "RGBA").save(os.path.join(_d, "plate_ico.png"))
    LAYERS = _rims(LAYERS)
