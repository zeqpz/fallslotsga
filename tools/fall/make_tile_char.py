"""The foreground picture for Engine's tile editor (Studio > Media > Create tile): the scarecrow on a transparent
background, rendered from the packed cut-out rig at its atlas resolution. Engine's guide: a feature character as a
transparent PNG, enlarged to fill the editor's focus box; no wording on the art.

  .venv/Scripts/python.exe -I tools/fall/make_tile_char.py
-> media/tile_character.png       waist up: head, hat, arms on the crossbar, jug and crow (the one to use: he fills the box)
   media/tile_character_full.png  the whole figure on his post"""
import os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from qa_scare_parts import Rig, ROOT

OUT = os.path.join(ROOT, "media")
SCALE = 1.5          # the atlas's own px per art px: nothing is upscaled


def render(R, view):
    f = R.frame("spin", 0, view=view, scale=SCALE, bg=None, fx=False)       # premultiplied RGBA floats
    a = np.clip(f[..., 3:], 0, 1)
    rgb = np.where(a > 1e-4, f[..., :3] / np.maximum(a, 1e-4), 0)
    return Image.fromarray((np.concatenate([np.clip(rgb, 0, 1), a], -1) * 255 + .5).astype(np.uint8), "RGBA")


def main():
    R = Rig()
    full = render(R, (-70, -20, 1094, 1520))
    full = full.crop(full.getbbox())
    full.save(os.path.join(OUT, "tile_character_full.png"))
    bust = render(R, (-70, -20, 1094, 840))            # cut at the belt: the title band covers the cut
    box = bust.getbbox()
    bust = bust.crop((box[0], box[1], box[2], bust.height))
    bust.save(os.path.join(OUT, "tile_character.png"))
    for n, im in (("tile_character_full.png", full), ("tile_character.png", bust)):
        print(n, im.size, os.path.getsize(os.path.join(OUT, n)) // 1024, "KB")


if __name__ == "__main__":
    main()
