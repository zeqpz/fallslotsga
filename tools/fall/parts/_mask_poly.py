"""Helpers for the part specs (H2-H5): a layer's exact outline as a polygon, so a spec can hand cut_parts.py a
cut="poly" layer whose shape is the drawing's own (its regions and ink, cut along its outlines) minus the parts that
sit on it - e.g. a pie slice without the cream swirl on it, which art_cut alone would fill back in (fill_holes).

    region(sid, poly, minus=[poly, ...])  -> the art_cut mask of poly, less the art_cut masks of each minus poly
    outline(mask, step=2)                 -> the mask's outer boundary as [(x, y), ...] icon px (largest patch)
    inside(poly)                          -> a bool mask of a polygon (for keep functions limited to an area)
Not used by the shared tools; only the spec files import it."""
import os, sys
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cut_parts as CP                                         # noqa: E402

N8 = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]   # (dy, dx) clockwise from up


def icon(sid):
    return CP.rgba(os.path.join(CP.ICONS, sid + ".png"))


def inside(poly):
    return CP.poly_mask(poly)


def region(sid, poly, minus=(), grow_minus=0):
    a = icon(sid)
    m = CP.art_cut(a, poly)
    for p in minus:
        k = CP.art_cut(a, p)
        if grow_minus:
            k = ndimage.binary_dilation(k, iterations=grow_minus)
        m &= ~k
    return m


def outline(m, step=2):
    """Moore-neighbour trace of the largest patch's outer boundary."""
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == 1 + int(np.argmax(sizes))
    m = ndimage.binary_fill_holes(m)
    p = np.pad(m, 1)
    ys, xs = np.nonzero(p)
    i = int(np.argmin(ys * p.shape[1] + xs))
    s = (int(ys[i]), int(xs[i]))
    cur, b = s, (s[0], s[1] - 1)
    pts = [s]
    for _ in range(200000):
        d = N8.index((b[0] - cur[0], b[1] - cur[1]))
        for k in range(1, 9):
            nd = (d + k) % 8
            q = (cur[0] + N8[nd][0], cur[1] + N8[nd][1])
            if p[q]:
                pd = N8[(nd - 1) % 8]
                b = (cur[0] + pd[0], cur[1] + pd[1])
                cur = q
                break
        else:
            break
        if cur == s:
            break
        pts.append(cur)
    return [(x - 1, y - 1) for y, x in pts[::step]]
