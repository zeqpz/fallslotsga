"""H5 Moonshine Jug, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H5.png.

plates  jug  the jug without its cork and the drip (the open mouth and the neck's glaze painted in)
layers  back to front (see tools/fall/parts/H1.py): the jug, the drip running down its neck, the cork"""
PLATES = {
    "jug": "Edit the attached picture: remove the cork and the golden drip of moonshine running down the neck. Where the "
           "cork was, paint the jug's open mouth: the round brown lip of the neck with a dark round hole inside it. "
           "Where the drip ran, paint the smooth brown glaze of the neck and shoulder. Keep everything else exactly the "
           "same: same position, same size, same colours, the XXX, the handle, the same black outline and the same "
           "cream sticker border round it. Transparent background.",
}
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mask_poly as MP

CORK = [(470, 30), (700, 30), (700, 150), (650, 178), (560, 165), (480, 145), (470, 140)]
DRIP_AREA = [(560, 165), (645, 160), (668, 300), (668, 450), (600, 450), (560, 300)]


def _masks():
    """the drip (its gold and the dark line round it), the cork, and the jug = everything else"""
    import numpy as np
    from scipy import ndimage
    a = MP.icon("H5")
    rgb = a[..., :3].astype(float)
    on = a[..., 3] > 0
    gold = on & MP.inside(DRIP_AREA) & (rgb[..., 0] > 195) & (rgb[..., 1] > 125) & (rgb[..., 2] < 200)
    lab, n = ndimage.label(ndimage.binary_opening(gold, iterations=1))
    sizes = ndimage.sum(gold, lab, range(1, n + 1))
    gold = ndimage.binary_fill_holes(np.isin(lab, 1 + np.nonzero(sizes >= 150)[0]))
    ink = on & (rgb.max(2) < 80)
    drip = gold | (ndimage.binary_dilation(gold, iterations=7) & ink)
    cork = MP.region("H5", CORK)
    jug = on & ~ndimage.binary_dilation(cork | drip, iterations=1)
    return MP.outline(drip, 1), MP.outline(jug)


DRIP, JUG = _masks()
LAYERS = [
    # the plate's jug (open mouth, bare neck) under the drawing's own jug, which has the cork and drip cut out of it
    dict(name="jug", src="plate:jug", pivot=(480, 920), parent="root"),
    dict(name="jug_art", src="art", cut="poly", poly=JUG, pivot=(480, 920), parent="jug"),
    dict(name="drip", src="art", cut="poly", poly=DRIP, pivot=(600, 180), parent="jug"),
    dict(name="cork", src="art", poly=CORK, pivot=(568, 108), parent="jug"),
]
