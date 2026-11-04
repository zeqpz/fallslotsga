"""L5 Sunflower, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L5.png.

leaves  the ring of green leaves behind the petals, whole (generator plate "leaves_gen": the flower with the petals and
        the centre taken away), with the icon's own leaf tips laid over where the icon shows them
petals  the yellow petal ring, whole under the centre (generator plate "petals_gen": the flower with the seed centre
        taken away and the petals painted in), with the icon's own petals laid over wherever the icon shows them;
        it turns about the flower's middle
centre  the brown seed disc, cut along its outline
The big spins turn the leaves' bone (the whole flower spins as one, so no leaf is left behind out of place); the
petals only wobble a few degrees against the leaves, and the centre turns back the other way to keep its shine up.

Plates: run `cut_parts.py L5 plates` (generator: plate_leaves_gen.png, plate_petals_gen.png), then
`python tools/fall/parts/L5.py` (builds plate_leaves.png and plate_petals.png from them and the icon), then
`cut_parts.py L5 cut`."""
import sys

GEN = {
    "petals_gen": "Edit the attached picture: remove the big brown seed centre disc of the sunflower completely, and "
                  "paint the inner ends of the yellow petals where it was, so the petals run on inward and meet in the "
                  "middle (yellow and orange petals only, no brown at all). Keep everything else exactly the same: same "
                  "position, same size, the same petals, the green leaves, colours, black outline and cream sticker "
                  "border. Transparent background.",
    "leaves_gen": "Edit the attached picture: remove ALL the yellow petals and the brown seed centre of the sunflower "
                  "completely. Keep only the green leaves that peek out from behind the petals, and paint each of them "
                  "whole - pointed green leaves radiating out from the middle, each with its black outline and centre "
                  "vein, their tips exactly where they are now. The cream sticker border must run round the leaves only. "
                  "Same position, same size, same green colours. Transparent background.",
}
MADE = ["leaves", "petals"]                                   # built by build_plates() below
PLATES = GEN if "plates" in sys.argv else {k: "(built by tools/fall/parts/L5.py)" for k in MADE}
MID = (487, 478)                                              # the middle of the seed disc


def circle(cx, cy, r, n=40):
    import math
    return [(cx + r * math.cos(6.2832 * k / n), cy + r * math.sin(6.2832 * k / n)) for k in range(n)]


LAYERS = [
    dict(name="leaves", src="plate:leaves", pivot=MID, parent="root"),
    dict(name="petals", src="plate:petals", pivot=MID, parent="leaves"),   # the whole head turns on the leaves' bone
    dict(name="centre", src="art", poly=circle(*MID, 231), pivot=MID, parent="petals"),
]


def build_plates():
    import os
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import cut_parts as CP
    d = os.path.join(CP.SRC, "L5")

    def classes(px, skip=None):
        """for every pixel: is the nearest clear colour a leaf's green, or a petal's yellow (the disc, `skip`, left out;
        the cream border and the ink go with the colour beside them)"""
        on = px[..., 3] > 128
        rgb = px[..., :3].astype(np.int32)
        mx, mn = rgb.max(2), rgb.min(2)
        sat = (mx - mn) / np.maximum(mx, 1)
        col = on & (mx >= 62) & (sat > .35)                    # not ink, not cream, not the cream-to-ink blend
        if skip is not None:
            col &= ~skip
        green = col & (rgb[..., 1] > rgb[..., 2] + 20) & (rgb[..., 1] >= rgb[..., 0] - 5) & (rgb[..., 0] < 200)   # not a pale petal highlight
        yellow = col & ~green
        idx = ndimage.distance_transform_edt(~(green | yellow), return_distances=False, return_indices=True)
        near = lambda m: m[idx[0], idx[1]]
        return on, near(green), near(yellow)

    icon = CP.rgba(os.path.join(CP.ICONS, "L5.png"))
    solid = icon[..., 3] > 128
    disc = CP.art_cut(icon, circle(*MID, 231))
    on, ig, iy = classes(icon, disc)
    irgb = icon[..., :3]
    icream = solid & (irgb.min(2) > 150) & (irgb.max(2) > 200)
    ink_i = solid & (irgb.max(2) < 62)
    for name, want in (("petals", 1), ("leaves", 0)):
        gen, sh = CP.lined_up(os.path.join(d, f"plate_{name}_gen.png"), icon)
        gon, gg, gy = classes(gen)
        if not want:                     # the leaves: line them up on the icon's leaf tips (their green), not the outline
            from scipy import signal
            gm = (gon & gg & (gen[..., 1] > gen[..., 2] + 20)).astype(np.float32)
            im_ = (solid & ig & (icon[..., 1] > icon[..., 2] + 20)).astype(np.float32)
            cc = signal.fftconvolve(im_, gm[::-1, ::-1], mode="same")
            dy, dx = np.unravel_index(np.argmax(cc), cc.shape)
            dy, dx = int(dy) - 500, int(dx) - 500
            if max(abs(dx), abs(dy)) <= 40:
                gen = np.roll(np.roll(gen, dy, 0), dx, 1)
                sh = (sh[0] + dx, sh[1] + dy)
            gon, gg, gy = classes(gen)
        print(name + "_gen shift", sh)
        keep = gon & (gy if want else gg)
        lab, n = ndimage.label(keep)                          # drop specks
        if n:
            sizes = ndimage.sum(keep, lab, range(1, n + 1))
            keep = np.isin(lab, 1 + np.nonzero(sizes >= 400)[0])
        if want:                         # the petals: the generator's only under the disc, the icon's own everywhere else
            keep &= ndimage.binary_dilation(disc, iterations=10)
        out = np.where(keep[..., None], gen, 0)
        # the icon's own wherever it shows this layer; the cream border goes with the petals, except right round a leaf
        # tip (a bit of border split off on its own is a speck clean_alpha throws away, and a leaf tip walled in by the
        # petals' border is a hole clean_alpha fills black)
        leafy = (ig & ~icream) | (ig & icream & (ndimage.distance_transform_edt(~(ig & ~icream & ~ink_i)) < 40))
        own = solid & ~ndimage.binary_dilation(disc, iterations=4) & (~leafy if want else leafy)
        out[own] = icon[own]
        out[~solid] = 0                                      # inside the solid icon: lines up at (0, 0)
        Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, f"plate_{name}.png"))
        print("check", name, "lines up at", CP.lined_up(os.path.join(d, f"plate_{name}.png"), icon)[1])


if __name__ == "__main__":
    build_plates()
