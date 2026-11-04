"""L9 Gravy Boat, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L9.png.

The plate is the empty boat (no gravy, no steam, no handle): it shows only where a part moves off. Over it, the
icon's own pixels in five pieces, partitioned by colour (the drawing's ink doesn't close its areas, so cut_parts'
outline cut can't split it - each piece is a mask traced into a cut "poly" polygon by maskpoly.py):
  back    the boat above and behind the gravy (back rim, inner wall, its sticker border) - behind the gravy
  gravy   the brown pool and its spots and highlights, with its ink
  front   the boat below the gravy's lip (front wall, gold band, foot) - drawn OVER the gravy, so the gravy sloshes
          behind the front lip
  handle  the scrolled handle, turning about where it joins the body
  steam_l, steam_r   the two wisps with their cream border, each turning about its foot in the gravy
A piece that comes out in several bits gets a layer per bit (back_2, ...), riding the first."""
import os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maskpoly as M

PLATES = {
    "empty": "Edit the attached picture: remove ALL the brown gravy and paint the empty inside of the white porcelain "
             "gravy boat where it was (the smooth white-and-grey inner wall and bottom of the bowl, the same porcelain "
             "colours); remove the two wavy steam wisps completely, with their cream border, so only the dark background "
             "shows above the boat; and remove the curled handle on the right, painting the boat's smooth white side "
             "where it joined. Keep everything else exactly the same: the boat's position, size, shape, spout, gold "
             "band, foot, black outline and the cream sticker border round it. Transparent background.",
}

HANDLE = [(724, 346), (733, 290), (770, 238), (840, 222), (912, 242), (962, 298), (988, 400), (968, 482), (930, 535),
          (922, 600), (885, 645), (830, 648), (822, 610), (827, 560), (832, 510), (839, 466), (812, 430), (790, 405),
          (760, 392), (736, 376)]


def _pmask(p):
    im = Image.new("L", (1000, 1000), 0)
    ImageDraw.Draw(im).polygon(p, fill=255)
    return np.asarray(im) > 0


def _parts():
    a = M.icon("L9")
    rgb, sat, val = M.hsv(a)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    on = a[..., 3] > 0
    yy, xx = np.mgrid[:1000, :1000]
    ink = on & (val < .24)
    hue = 60 * (g - b) / np.maximum(r - b, 1e-3)
    # the gravy: warm browns (not the gold band, which is yellower), in the bowl
    brown = on & (r >= g) & (g >= b) & (sat > .35) & (val > .2) & (hue < 35) & (yy > 330) & (yy < 580) & (xx > 60) & (xx < 840)
    lab, n = ndimage.label(ndimage.binary_closing(brown, iterations=3))
    core = lab == 1 + int(np.argmax(ndimage.sum(brown, lab, range(1, n + 1))))
    core = ndimage.binary_fill_holes(core)
    gravy = core.copy()
    for _ in range(9):                                         # its ink, all round (the front lip's ink too:
        gravy |= ndimage.binary_dilation(gravy) & ink          # the front draws it again, on top)
    # the steam: the wisps' grey-beige, above the gravy, and their cream border above the boat's rim
    grey = on & (sat > .1) & (sat < .38) & (val > .55) & (val < .86) & (r >= g) & (g >= b) & (xx > 320) & (xx < 610) & (yy < 425) & ~core
    lab, n = ndimage.label(grey)
    wisps = [lab == k for k in range(1, n + 1) if (lab == k).sum() > 800 and np.nonzero(lab == k)[0].min() < 300]
    wisps.sort(key=lambda w: np.nonzero(w)[1].mean())
    rx, ry = [], []                                            # the boat's back rim: its top ink line
    for x in range(250, 700):
        ys = np.nonzero(ink[320:395, x])[0]
        if len(ys):
            rx.append(x)
            ry.append(320 + ys[0])
    rim = np.interp(np.arange(1000), rx, ndimage.median_filter(np.array(ry, float), 21))
    # everything above the rim near a wisp is that wisp's: its cream border and its drop shadow
    near = ndimage.binary_dilation(np.logical_or.reduce(wisps), iterations=44) & (yy < rim[None, :] - 1) & on
    cores = np.zeros((1000, 1000), np.int32)
    for k, w in enumerate(wisps):
        cores[w] = k + 1
    _, (iy, ix) = ndimage.distance_transform_edt(cores == 0, return_indices=True)
    owner = cores[iy, ix]
    steam = [ndimage.binary_fill_holes(w | (near & (owner == k + 1))) for k, w in enumerate(wisps)]
    sm = np.logical_or.reduce(steam)
    handle = _pmask(HANDLE) & on & ~sm
    # the front: below the gravy's own colour, column by column (held flat past its ends)
    cols = np.nonzero(core.any(0))[0]
    bot = np.array([np.nonzero(core[:, x])[0].max() for x in cols])
    lip = np.interp(np.arange(1000), cols, bot) + 1
    front = on & (yy >= lip[None, :]) & ~handle & ~sm
    back = on & ~gravy & ~front & ~handle & ~sm
    return dict(back=back, gravy=gravy & ~sm, front=front, handle=handle, steam_l=steam[0], steam_r=steam[1])


MASKS = M.tidy(_parts())
_P = {k: M.poly(v) for k, v in MASKS.items()}                  # (for the checks)
LAYERS = [dict(name="boat", src="plate:empty", pivot=(320, 870), parent="root")]   # the foot's front edge: it tips to pour
LAYERS += M.layers("back", MASKS["back"], (320, 870), "boat")
LAYERS += M.layers("gravy", MASKS["gravy"], (130, 405), "boat")   # the spout end: it stays level as the boat tips
LAYERS += M.layers("front", MASKS["front"], (320, 870), "boat")
LAYERS += M.layers("handle", MASKS["handle"], (832, 520), "boat")
LAYERS += M.layers("steam_l", MASKS["steam_l"], (400, 398), "gravy")
LAYERS += M.layers("steam_r", MASKS["steam_r"], (560, 418), "gravy")
