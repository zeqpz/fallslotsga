"""H7 Pumpkin, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H7.png.

Back to front: the pumpkin body (as drawn), the pumpkin's top where the stem, the leaf and the vine stood (from a
plate, riding the body), the curly vine, the leaf, the stem. The vine and the leaf hang off the stem, the stem off the
body.

Every visible part is cut from the icon itself (src "art"), so at rest nothing shows a plate's redraw; the plate only
fills in what was hidden. Two plates are made here, never generated (see the end of this file):
  sil  the icon's silhouette in flat black: "diff:<plate>-sil" is all of that plate's paint, lined up exactly, and
       takes none of the icon's sticker border; `keep` (position-aware here: a mask) cuts it down to the hidden piece
  ico  the icon itself: "diff:ico-sil" + keep = the outer sticker border next to one part, so each part carries its
       whole border with it (an art cut takes only the inner ~16 px of it) - the "<part>_rim" layers"""
import os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ID = "H7"
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


BODY = [(30, 300), (200, 250), (420, 250), (470, 262), (470, 330), (560, 330), (600, 290), (660, 320), (700, 345),
        (860, 330), (970, 450), (970, 910), (800, 970), (200, 970), (30, 820)]
STEM = [(445, 352), (470, 305), (495, 262), (560, 150), (590, 85), (720, 85), (715, 140), (650, 200), (610, 240),
        (598, 300), (595, 362)]
VINE = [(220, 55), (470, 45), (565, 165), (548, 215), (500, 240), (430, 252), (300, 262), (215, 200)]
LEAF = [(595, 240), (640, 195), (700, 140), (700, 35), (800, 35), (955, 175), (955, 300), (820, 362), (700, 342),
        (650, 318), (605, 298)]


def keep_top(rgb, sat, mx):
    """the plate's pumpkin where the stem, the leaf and the vine hid it, and 2 px over their outlines"""
    import cut_parts as cp
    icon = _ICON.astype(np.int16)
    under = ndimage.binary_dilation(cp.art_cut(icon, STEM) | cp.art_cut(icon, LEAF) | cp.art_cut(icon, VINE), iterations=2)
    return under & ~ndimage.binary_dilation(_green(rgb, mx), iterations=2) & ~_cream(rgb, sat) & ndimage.binary_erosion(_ON, iterations=6)


PLATES = {
    "body": "Edit the attached picture: remove the brown stem, the green leaf and the curly green vine tendril from the top "
            "of the pumpkin, and paint the top of the pumpkin where they were: the same orange ribbed lobes curving in to "
            "meet in a small shallow dimple at the top centre, with the same black outlines and shading. Keep the pumpkin "
            "itself exactly the same: same position, same size, same colours, same outlines, and the same cream sticker "
            "border round it. Transparent background.",
}
LAYERS = [
    dict(name="body", src="art", poly=BODY, pivot=(500, 930), parent="root"),
    dict(name="top", src="diff:body-sil", keep=keep_top, pivot=(500, 930), parent="body"),
    dict(name="stem", src="art", poly=STEM, pivot=(530, 350), parent="body"),
    dict(name="vine", src="art", poly=VINE, pivot=(535, 200), parent="stem"),
    dict(name="leaf", src="art", poly=LEAF, pivot=(625, 225), parent="stem"),
]
# drawn: the stem in front of the vine's and the leaf's ends
LAYERS = [LAYERS[0], LAYERS[1], LAYERS[3], LAYERS[4], LAYERS[2]]


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
