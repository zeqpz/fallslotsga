"""L1 Maple Leaf, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L1.png.

The leaf is one flat colour with no outline between its lobes, so it is cut by exact polygons (cut "poly") across
the lobes' bases, from notch to notch: the middle of the leaf (which reaches a little under each lobe, so a lobe that
turns never opens a gap), the top, left, right and the two small lower lobes riding the middle, and the stem (cut
along its own outline) in front. No plates needed: the stem only touches the leaf at its tip.

Two plates are made here, never generated (see the end of this file):
  sil  the icon's silhouette in flat black (the "b" of a diff: lines up exactly, takes no sticker border)
  ico  the icon itself: "diff:ico-sil" + keep = whatever of the icon no cut took (the sticker border round the leaf)
       nearest one part, with that part, so each part carries its whole border - the "<part>_rim" layers"""
import os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ID = "L1"
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_ICON = np.asarray(Image.open(os.path.join(_ROOT, "art", "fall-src", "icons", ID + ".png")).convert("RGBA"))
_ON = _ICON[..., 3] > 128

A, B, C, D, E, F = (352, 408), (612, 462), (700, 688), (440, 712), (408, 712), (208, 602)   # the notches, stem
# the middle stops ~30 px short of each notch, so the notch's own outline goes with the lobes either side of it
A_, B_, C_, F_ = (368, 433), (588, 480), (673, 676), (238, 600)
MID = [A_, (488, 396), B_, (692, 560), C_, (575, 736), D, E, (284, 692), F_, (244, 490)]
TOP = [A_, A, (330, 160), (520, 0), (640, 150), (700, 260), B, B_]
LEFT = [A_, A, (260, 270), (60, 260), (20, 420), (40, 640), F, F_]
RIGHT = [B_, B, (780, 330), (960, 380), (960, 560), C, C_]
LOW_L = [F_, F, (40, 640), (60, 700), (240, 820), (395, 760), E]
LOW_R = [C_, C, (870, 720), (830, 830), (560, 860), (450, 760), D]
STEM = [(300, 700), (460, 700), (470, 760), (380, 960), (290, 960)]

PLATES = {}
LAYERS = [
    dict(name="mid", src="art", cut="poly", poly=MID, pivot=(424, 714), parent="root"),
    dict(name="low_l", src="art", cut="poly", poly=LOW_L, pivot=(310, 655), parent="mid"),
    dict(name="low_r", src="art", cut="poly", poly=LOW_R, pivot=(570, 700), parent="mid"),
    dict(name="left", src="art", cut="poly", poly=LEFT, pivot=(282, 505), parent="mid"),
    dict(name="right", src="art", cut="poly", poly=RIGHT, pivot=(656, 575), parent="mid"),
    dict(name="top", src="art", cut="poly", poly=TOP, pivot=(482, 435), parent="mid"),
    dict(name="stem", src="art", poly=STEM, pivot=(424, 722), parent="mid"),
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
