"""L2 Acorn, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L2.png.

Back to front: the nut (as drawn), the nut's top where the cap sat (from a plate, riding the nut, drawn over the
nut's cut edge so the cap's rim line goes with the cap), the stem (behind the cap's scales), the scaly cap.
The cap rides the nut, the stem rides the cap.

Every visible part is cut from the icon itself (src "art"), so at rest nothing shows a plate's redraw; the plate only
fills in what was hidden. Two plates are made here, never generated (see the end of this file):
  sil  the icon's silhouette in flat black: "diff:<plate>-sil" is all of that plate's paint, lined up exactly, and
       takes none of the icon's sticker border; `keep` (position-aware here: a mask) cuts it down to the hidden piece
  ico  the icon itself: "diff:ico-sil" + keep = whatever of the icon no art cut took (the sticker border) nearest one
       part, with that part, so each part carries its whole border with it - the "<part>_rim" layers"""
import os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ID = "L2"
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_ICON = np.asarray(Image.open(os.path.join(_ROOT, "art", "fall-src", "icons", ID + ".png")).convert("RGBA"))
_ON = _ICON[..., 3] > 128


def _poly(p):
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon([tuple(q) for q in p], fill=255)
    return np.asarray(im) > 0


def _cream(rgb, sat):
    return (rgb[..., 0] > .84) & (rgb[..., 1] > .78) & (rgb[..., 2] > .6) & (sat < .26)


NUT = [(90, 430), (180, 395), (350, 372), (500, 402), (580, 445), (670, 505), (730, 570), (750, 640), (760, 720),
       (600, 920), (250, 970), (70, 700)]
CAP = [(100, 420), (120, 300), (250, 180), (400, 130), (560, 150), (640, 180), (670, 220), (760, 250), (880, 380),
       (900, 560), (850, 680), (760, 680), (740, 560), (670, 500), (580, 440), (500, 395), (350, 368), (180, 390)]
STEM = [(600, 180), (640, 40), (860, 40), (860, 140), (780, 260), (700, 240), (650, 200)]


def keep_top(rgb, sat, mx):
    """the plate's nut where the cap hid it, and 2 px over the cap's outline"""
    import cut_parts as cp
    icon = _ICON.astype(np.int16)
    under = ndimage.binary_dilation(cp.art_cut(icon, CAP) | cp.art_cut(icon, STEM), iterations=2)
    return under & _poly(NUT[:9] + [(780, 700), (900, 500), (600, 250), (150, 250)]) & ~_cream(rgb, sat) &         ndimage.binary_erosion(_ON, iterations=6)


PLATES = {
    "nut": "Edit the attached picture: remove the scaly acorn cap and its little stem completely. Do NOT move, enlarge or "
           "redraw the acorn nut: its pointed bottom tip, its left side and its right side stay exactly where they are, "
           "at exactly the same size - this picture will be laid exactly over the original. Only finish the nut's top: "
           "where the cap covered it, close the nut with a gently rounded dome just a little above where the cap's rim "
           "was, in the same glossy orange-brown with the same black outline. Everywhere the cap was, above that dome, "
           "is empty transparent background. Keep the same cream sticker border round the nut. Transparent background.",
}
LAYERS = [
    dict(name="nut", src="art", poly=NUT, pivot=(430, 930), parent="root"),
    dict(name="nut_top", src="diff:nut-sil", keep=keep_top, pivot=(430, 930), parent="nut"),
    dict(name="stem", src="art", poly=STEM, pivot=(690, 215), parent="cap"),
    dict(name="cap", src="art", poly=CAP, pivot=(480, 450), parent="nut"),
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
