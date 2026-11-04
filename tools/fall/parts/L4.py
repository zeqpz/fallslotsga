"""L4 Grapes, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L4.png.

leaves  the two leaves whole (generator plate "leaves_gen": the leaves with the grapes and stem taken away, the hidden
        parts painted in), with the icon's own leaf laid over wherever the icon shows it; they hang off the stem
bunch   the stem and the back grapes as the icon draws them, the bunch's cream sticker border, and a deep purple shadow
        where the six front grapes sit - so a front grape jiggling off shows the dark between grapes, not a hole. It
        swings from the top of the stem. (The stem is part of it: a plate holding only the grapes lines up off-centre
        in cut_parts, its silhouette fits inside the icon's in many places.)
g_*     the six front grapes, each cut along its own outline, each hanging from its top (pivot) toward the stem

Plates: run `cut_parts.py L4 plates` (generator: plate_leaves_gen.png only), then `python tools/fall/parts/L4.py`
(builds plate_leaves.png and plate_bunch.png from it and the icon), then `cut_parts.py L4 cut`."""
import sys

GEN = {
    "leaves_gen": "Edit the attached picture: remove ALL the purple grapes and the brown stem completely. Keep only the "
                  "two green leaves, and paint the parts of the leaves that were hidden behind the grapes so both leaves "
                  "are whole, with their black outline and veins. The cream sticker border must run round the leaves "
                  "only. Keep the leaves exactly the same: same position, same size, same green colours, highlights and "
                  "outline. Transparent background.",
}
MADE = ["leaves", "bunch"]                                    # built by build_plates() below from the icon + leaves_gen
PLATES = GEN if "plates" in sys.argv else {k: "(built by tools/fall/parts/L4.py)" for k in MADE}


def circle(cx, cy, r, n=28):
    import math
    return [(cx + r * math.cos(6.2832 * k / n), cy + r * math.sin(6.2832 * k / n)) for k in range(n)]


# the grapes: centre and radius (a little inside each grape's outline), icon px
BACK = dict(TR=(765, 350, 60), BL=(452, 355, 45), FL=(352, 565, 52), R=(808, 510, 88), LR=(788, 652, 64),
            BB=(578, 808, 58), BB2=(700, 885, 45))
FRONT = dict(g_top=(603, 358, 98), g_left=(447, 485, 95), g_mid=(643, 543, 98), g_lowl=(493, 662, 90),
             g_lowm=(670, 735, 92), g_lowr=(800, 822, 84))
HANG = dict(g_top=(565, 262), g_left=(490, 392), g_mid=(625, 445), g_lowl=(525, 570), g_lowm=(650, 640),
            g_lowr=(770, 735))                                 # where each hangs from (toward the stem)
STEM = [(400, 40), (560, 40), (640, 250), (600, 275), (530, 300), (505, 345), (470, 320), (420, 300), (415, 245)]

LAYERS = [
    dict(name="leaves", src="plate:leaves", pivot=(445, 285), parent="bunch"),
    dict(name="bunch", src="plate:bunch", pivot=(530, 290), parent="root"),
] + [dict(name=k, src="art", poly=circle(*FRONT[k]), pivot=HANG[k], parent="bunch")
     for k in ("g_top", "g_left", "g_mid", "g_lowl", "g_lowm", "g_lowr")]


def build_plates():
    import os
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import cut_parts as CP
    d = os.path.join(CP.SRC, "L4")
    icon = CP.rgba(os.path.join(CP.ICONS, "L4.png"))
    on = icon[..., 3] > 128
    rgb = icon[..., :3]
    v = rgb.max(2) / 255
    ink = on & (v < .24)
    cream = on & ~ink & (rgb[..., 0] > 215) & (rgb[..., 1] > 200) & (rgb[..., 2] > 160)
    sat = (rgb.max(2) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    col = on & ~ink & ~cream & (sat > .3)                       # clear colours, not the cream-to-ink blend
    purple = col & (rgb[..., 2] > rgb[..., 1] + 25)
    green = col & (rgb[..., 1] > rgb[..., 2] + 25) & (rgb[..., 1] >= rgb[..., 0] - 10)
    brown = col & (rgb[..., 0] > rgb[..., 1] + 20) & (rgb[..., 1] > rgb[..., 2]) & ~purple
    idx = ndimage.distance_transform_edt(~(purple | green | brown), return_distances=False, return_indices=True)
    near_purple = purple[idx[0], idx[1]]
    near_green = green[idx[0], idx[1]]
    front = np.zeros(on.shape, bool)
    for k, c in FRONT.items():
        front |= CP.art_cut(icon, circle(*c))
    stem = CP.art_cut(icon, STEM)
    # the bunch: everything whose nearest colour is a grape's, the front grapes' insides a deep shadow
    bunch = (icon[..., 3] > 128) & (near_purple | stem)        # inside the solid icon: lines up at (0, 0)
    px = np.where(bunch[..., None], icon, 0)
    shade = front & ~cream
    px[shade] = (78, 36, 88, 255)
    Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, "plate_bunch.png"))
    # the leaves: the generator's whole leaves, and the icon's own leaf over them wherever it shows
    gen, sh = CP.lined_up(os.path.join(d, "plate_leaves_gen.png"), icon)
    print("leaves_gen shift", sh)
    grgb = gen[..., :3].astype(np.float32) / 255
    mx, mn = grgb.max(2), grgb.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    pick = lambda c, s, m: (c[..., 1] > c[..., 2] + .08) & (c[..., 1] >= c[..., 0] - .04) & (s > .2) & (m > .25)
    leaf = CP.colour_only(gen, gen[..., 3] > 128, pick)
    gon = gen[..., 3] > 128
    gcream = gon & (gen[..., 0] > 215) & (gen[..., 1] > 200) & (gen[..., 2] > 160)
    keep = leaf | (ndimage.binary_dilation(leaf, iterations=34) & gcream)
    out = np.where(keep[..., None], gen, 0)
    own = (icon[..., 3] > 128) & near_green & ~front & ~stem & ~bunch     # the icon's leaf, its ink and border
    out[own] = icon[own]
    Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, "plate_leaves.png"))
    print("plates leaves, bunch built")


if __name__ == "__main__":
    build_plates()
