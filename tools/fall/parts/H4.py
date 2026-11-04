"""H4 Pilgrim Hat, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/H4.png.

plates  brim      the brim alone (crown, band and buckle taken away, the brim's flat top painted where they stood)
        nobuckle  the hat without its buckle (the band runs on under it)
layers  back to front (see tools/fall/parts/H1.py): the brim, the crown, the band round it, the gold buckle"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _mask_poly as MP

_KEEP = ("Keep everything else exactly the same: same position, same size, same colours, same black outline and the "
         "same cream sticker border round it. Transparent background.")
PLATES = {
    "brim": "Edit the attached picture: remove the hat's tall black crown, its brown band and the gold buckle, leaving "
            "only the wide black brim lying flat. Where the crown stood, paint the brim's flat top surface: a smooth "
            "black-grey oval with a soft sheen, so the brim is one whole flat oval disc with its black outline and its "
            "rim. Keep the brim exactly the same: same position, same size, same colours, same outline and the same "
            "cream sticker border round it. Transparent background.",
    "nobuckle": "Edit the attached picture: remove only the gold buckle, and paint the brown leather hat band where it "
                "was, so the plain band runs smoothly all the way round the crown. " + _KEEP,
}

CROWN = [(220, 600), (240, 460), (330, 150), (370, 90), (520, 80), (720, 95), (850, 160), (855, 260), (840, 560),
         (820, 700), (220, 640)]
BAND = [(200, 440), (560, 480), (850, 520), (850, 720), (500, 760), (200, 640)]
_A = {"crown": MP.inside(CROWN), "band": MP.inside(BAND)}


def crown_keep(rgb, sat, val):
    """the black crown: dark, greyish (not the brown band, not the cream border)"""
    return _A["crown"] & (sat < .4) & (val < .72)


def band_keep(rgb, sat, val):
    """the brown band"""
    return _A["band"] & (rgb[..., 0] > rgb[..., 1]) & (rgb[..., 1] >= rgb[..., 2] - .02) & (sat > .35) & (val > .18) & (val < .8)


LAYERS = [
    dict(name="brim", src="plate:brim", pivot=(500, 790), parent="root"),
    dict(name="crown", src="diff:nobuckle-brim", keep=crown_keep, pivot=(525, 640), parent="brim"),
    # the band from the drawing itself (its brown is too near the brim's black for a plate difference); the buckle
    # only ever grows over it, so the band never needs the plate's piece from under the buckle
    dict(name="band", src="art", poly=[(222, 455), (300, 468), (600, 528), (818, 540), (818, 702), (560, 722),
                                       (238, 618)], pivot=(525, 640), parent="crown"),
    dict(name="buckle", src="art", poly=[(285, 470), (585, 470), (590, 765), (285, 765)], pivot=(440, 615),
         parent="band"),
]
