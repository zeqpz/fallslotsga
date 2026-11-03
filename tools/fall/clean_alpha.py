"""Strip the generator's glow haze and soft drop shadow from a transparent PNG: keep alpha only on and just round
the solid silhouette (alpha >= 128, grown by 2 px), and un-premultiply the dark fringe out of the edge colours.
usage: python tools/fall/clean_alpha.py <in.png> <out.png>"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage


def clean(src, dst):
    im = np.asarray(Image.open(src).convert("RGBA")).astype(np.float32)
    a = im[..., 3]
    solid = a >= 128
    solid = ndimage.binary_fill_holes(solid)
    lab, n = ndimage.label(solid)
    if n > 1:                                    # drop specks well away from the main shapes
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes >= max(200, sizes.max() * .002))[0])
        solid = keep
    near = ndimage.binary_dilation(solid, iterations=2)
    a2 = np.where(near, a, 0)
    a2 = np.where(solid & ~ndimage.binary_erosion(solid, iterations=1), np.maximum(a2, 200), a2)
    a2 = np.where(ndimage.binary_erosion(solid, iterations=1), 255, a2)
    rgb = im[..., :3]
    # the edge ring takes the colour of the nearest solid pixel (no dark halo when scaled down)
    idx = ndimage.distance_transform_edt(~ndimage.binary_erosion(solid, iterations=2), return_distances=False,
                                         return_indices=True)
    ring = near & ~ndimage.binary_erosion(solid, iterations=2)
    rgb[ring] = rgb[idx[0][ring], idx[1][ring]]
    out = np.dstack([rgb, a2]).clip(0, 255).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(dst)


if __name__ == "__main__":
    clean(sys.argv[1], sys.argv[2])
