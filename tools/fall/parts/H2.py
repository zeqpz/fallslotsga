"""H2 Pumpkin Pie, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H2.png.

plates  the picture again with things taken away and what was behind painted in (OpenRouter edit of the icon)
layers  back to front (see tools/fall/parts/H1.py): the pie in its tin with the slice's place left empty, the cut
        slice (pulled out at the front right), the big swirl of cream on the pie and the small one on the slice"""
PLATES = {
    "pie": "Edit the attached picture: remove the WHOLE cut slice of pie that is pulled out at the front right - its "
           "orange filling, the small swirl of whipped cream on it AND its own wavy golden crust along its outer edge "
           "(the crust from the right side of the pie down to the slice's bottom point must go too) - and remove the "
           "big swirl of whipped cream on top of the pie. Where the slice was, paint the empty part of the pie tin: the "
           "bare pale grey tin floor with a few crumbs and the fluted grey tin wall with its rim, just like the empty "
           "gap already showing beside it, so the pie's crust ring has a wide open gap at the front right where the "
           "slice was cut out, and the pie's cut face runs along the gap. Where the big swirl of cream was, paint the "
           "smooth orange pumpkin filling with "
           "small brown speckles and the wavy golden crust behind it. Keep everything else exactly the same: same "
           "position, same size, same colours, same black outline and the same cream sticker border round it. "
           "Transparent background.",
    "nocream": "Edit the attached picture: remove BOTH swirls of whipped cream - the big one on top of the pie and the "
               "small one on the cut slice - and paint the smooth orange pumpkin filling with small brown speckles "
               "where they were (and the wavy golden crust behind the top of the big swirl). Keep everything else "
               "exactly the same: the pie, the cut slice, the crust, the tin, same position, same size, same colours, "
               "same black outline and the same cream sticker border round it. Transparent background.",
    "tin": "Edit the attached picture: remove the whole pie - all the orange pumpkin filling, the cut slice, all the "
           "golden crust and both swirls of whipped cream - and leave only the empty fluted pale grey pie tin, its bare "
           "floor seen from above. Keep the tin exactly the same: same position, same size, same colours, same black "
           "outline and the cream sticker border round it. Transparent background.",
}


import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mask_poly as MP

SLICE = [(505, 470), (560, 468), (845, 498), (955, 512), (950, 640), (880, 790), (790, 885), (715, 870), (505, 500)]
CREAM_S = [(640, 530), (690, 490), (720, 440), (780, 440), (800, 490), (850, 520), (860, 580), (800, 625), (690, 625),
           (640, 590)]


def _slice():
    """the drawing's slice less its cream swirl, and less the strip of grey tin wall showing past its crust"""
    import numpy as np
    from scipy import ndimage
    a = MP.icon("H2")
    rgb = a[..., :3] / 255.
    mx, mn = rgb.max(2), rgb.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    tin = (a[..., 3] > 128) & (sat < .32) & (mx > .45) & (mx < .9)
    border = (a[..., 3] > 128) & (a[..., 0] > 215) & (a[..., 1] > 200) & (a[..., 2] > 160) & (sat < .3)
    m = MP.region("H2", SLICE, [CREAM_S]) & ~ndimage.binary_dilation(tin, iterations=2)
    ink = mx < .24
    core = m & ~border & ~ink
    m = core | (m & ink & ndimage.binary_dilation(core, iterations=7)) |         (m & border & ndimage.binary_dilation(core, iterations=14) & ~ndimage.binary_dilation(tin, iterations=14))
    # the fill under it: only the cream swirl's footprint on the slice (below the slice's top edge)
    yy, xx = np.mgrid[:1000, :1000]
    below = yy > 483 + .1 * (xx - 520)
    area = ndimage.binary_dilation(MP.region("H2", CREAM_S) & below, iterations=8) & ndimage.binary_fill_holes(
        ndimage.binary_dilation(m | (MP.region("H2", CREAM_S) & below), iterations=2))
    return MP.outline(m), area


SLICE_POLY, _AREA = _slice()


def slice_keep(rgb, sat, val):
    """the slice under its cream: orange filling, golden crust and black ink (not the pale grey tin), in its own area"""
    return ((sat > .3) | (val < .3)) & _AREA


LAYERS = [
    dict(name="pie", src="plate:pie", pivot=(470, 780), parent="root"),
    # the slice twice: what is under its cream swirl (from the plate) and, over it, the drawing's own slice with the
    # swirl's outline cut out of it (so the swirl can wobble off it); "slice" moves, "slice_art" rides it unmoved
    dict(name="slice", src="diff:nocream-tin", keep=slice_keep, pivot=(740, 800), parent="pie"),
    dict(name="slice_art", src="art", cut="poly", poly=SLICE_POLY, pivot=(740, 800),
         parent="slice"),
    dict(name="cream_big", src="art", poly=[(300, 330), (330, 300), (400, 250), (430, 190), (450, 130), (540, 130),
                                            (560, 220), (600, 270), (650, 330), (640, 420), (560, 460), (420, 460),
                                            (320, 420)], pivot=(470, 440), parent="pie"),
    dict(name="cream_small", src="art", poly=CREAM_S, pivot=(745, 610), parent="slice"),
]
