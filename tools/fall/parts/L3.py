"""L3 Green Apple, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L3.png.

body  the bare apple (plate "apple"), with the icon's own apple laid over it ("skin", cut along the cream under the
      leaf and round the stem) - so at rest it is exactly the icon and the bare top only shows when the stem moves
stem  turns about its base in the dimple; the leaf rides on the stem, turning about where it joins it

The plate is NOT the generator's: the apple's whole outline already shows under the leaf, so the bare apple is the
icon itself with the stem's foot filled with the dimple's own green, the outline closed across it, and the cream
sticker border run round the top. Build it with `python tools/fall/parts/L3.py` (writes
art/fall-src/parts/L3/plate_apple.png), then `cut_parts.py L3 cut`. The generator prompt in TRIED came first (its apple top came
out a different shape: two outlines when the leaf moved); kept for the record, `plates` does nothing for L3."""
import sys

TRIED = {
    "apple": "Edit the attached picture: remove the brown stem and the green leaf at the top of the apple completely, "
             "and paint the apple's smooth round top where they were - a shallow dimple in the green skin with no stem "
             "in it. The cream sticker border must follow the apple's outline round the top too (no bump where the "
             "stem and leaf were). Keep everything else exactly the same: same position, same size, same green "
             "colours, highlights, speckles, the black outline and the cream sticker border. Transparent background.",
}
PLATES = {} if "plates" in sys.argv else {"apple": "(built by tools/fall/parts/L3.py)"}
STEM = [(425, 85), (543, 85), (543, 352), (490, 352), (478, 270), (435, 205)]
LEAF = [(541, 25), (960, 25), (960, 245), (800, 262), (690, 270), (560, 270), (541, 250)]
LAYERS = [
    dict(name="body", src="plate:apple", pivot=(480, 925), parent="root"),
    dict(name="skin", src="art", cut="poly",
         poly=[(0, 1000), (0, 240), (300, 165), (405, 188), (442, 206), (476, 252), (488, 300), (491, 352),
               (541, 352), (538, 300), (546, 274), (640, 277), (700, 281), (765, 287), (800, 299), (850, 309),
               (905, 335), (1000, 335), (1000, 1000)],
         pivot=(480, 925), parent="body"),
    dict(name="leaf", src="art", poly=LEAF, pivot=(548, 240), parent="stem"),
    dict(name="stem", src="art", poly=STEM, pivot=(516, 340), parent="body"),
]


def build_plate():
    import os, sys
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import cut_parts as CP
    icon = CP.rgba(os.path.join(CP.ICONS, "L3.png"))
    on = icon[..., 3] > 128
    foot = CP.art_cut(icon, STEM) | CP.art_cut(icon, LEAF) | ((CP.poly_mask(STEM) | CP.poly_mask(LEAF)) & on)
    cream = on & (icon[..., 0] > 215) & (icon[..., 1] > 200) & (icon[..., 2] > 160)
    apple = on & ~cream & ~foot
    gap = CP.poly_mask([(466, 277), (515, 291), (551, 274), (551, 356), (466, 356)])     # the dimple under the stem's foot
    lab, n = ndimage.label(apple)
    apple = lab == 1 + int(np.argmax(ndimage.sum(apple, lab, range(1, n + 1))))
    shape = ndimage.binary_fill_holes(apple | gap)
    px = icon.copy()
    hole = shape & ~apple                                       # fill from the nearest apple pixel
    idx = ndimage.distance_transform_edt(~apple, return_distances=False, return_indices=True)
    px[hole] = icon[idx[0][hole], idx[1][hole]]
    im = Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA")
    ImageDraw.Draw(im).line([(464, 277), (515, 291), (553, 273)], fill=(4, 4, 3, 255), width=9, joint="curve")   # the outline, closed
    px = np.asarray(im).astype(np.int16).copy()
    ring = ndimage.binary_dilation(shape, iterations=26) & ~shape & ~(on & ~foot)
    px[ring] = (250, 229, 195, 255)
    px[foot & ~shape & ~ring] = 0
    keep = ndimage.binary_dilation(shape, iterations=30) & (icon[..., 3] > 128)   # inside the icon: lines up at (0, 0)
    px[~keep] = 0
    d = os.path.join(CP.SRC, "L3")
    os.makedirs(d, exist_ok=True)
    Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, "plate_apple.png"))
    print("plate apple built")


if __name__ == "__main__":
    build_plate()
