"""L6 Candy Corn, cut into parts (tools/fall/cut_parts.py). Icon px of art/fall-src/icons/L6.png.

The three colour bands, cut along the ink lines between them (each upper band keeps the ink line under it). A band
that lifts off the one below must not open a hole, so the lower bands run on underneath the upper ones:
base    the yellow band, run on 90 px up under the orange (the band's own colours, edge and border pulled straight on
        up across its top edge)
middle  the orange band, run on 70 px up under the white tip the same way
tip     the white tip, the icon's own pixels
Built, not generated: `python tools/fall/parts/L6.py` writes plate_base.png and plate_middle.png, then
`cut_parts.py L6 cut`. (`plates` does nothing for L6.)"""
import sys

MADE = ["base", "middle"]
PLATES = {} if "plates" in sys.argv else {k: "(built by tools/fall/parts/L6.py)" for k in MADE}

# the band edges: lines just under the middle of each ink line, run out past the candy on both sides
TIP = [(2, 95), (0, 0), (1000, 0), (1000, 454)]
MIDDLE = [(2, 95), (1000, 454), (1000, 759), (0, 463)]
BASE = [(0, 463), (1000, 759), (1000, 1000), (0, 1000)]

LAYERS = [
    dict(name="base", src="plate:base", pivot=(470, 930), parent="root"),
    dict(name="middle", src="plate:middle", pivot=(530, 615), parent="base"),
    dict(name="tip", src="art", cut="poly", poly=TIP, pivot=(640, 325), parent="middle"),
]


def build_plates():
    import os
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import cut_parts as CP
    d = os.path.join(CP.SRC, "L6")
    os.makedirs(d, exist_ok=True)
    icon = CP.rgba(os.path.join(CP.ICONS, "L6.png"))
    solid = icon[..., 3] > 128
    mid, base = CP.poly_mask(MIDDLE), CP.poly_mask(BASE)

    def run_on(own, under, a, b):
        """the band's own pixels, and `under` (inside the solid candy) pulled straight on from the band's top edge, the
        line a-b: each pixel takes the band's pixel just under that edge, straight down across it - so the band's
        colours, its outline and its cream border run on up as they cross the edge"""
        own = own & solid
        px = np.where(own[..., None], icon, 0)
        fill = under & solid & ~own
        (ax, ay), (bx, by) = a, b
        L = np.hypot(bx - ax, by - ay)
        nx, ny = (by - ay) / L, -(bx - ax) / L               # the edge's normal, pointing up off the band
        if ny > 0:
            nx, ny = -nx, -ny
        yy, xx = np.nonzero(fill)
        h = (xx - ax) * nx + (yy - ay) * ny                   # how far above the edge
        sx = np.clip(np.round(xx - (h + 4) * nx), 0, 999).astype(int)
        sy = np.clip(np.round(yy - (h + 4) * ny), 0, 999).astype(int)
        px[yy, xx] = icon[sy, sx]
        px[yy, xx, 3] = np.where(solid[sy, sx], 255, px[yy, xx, 3])
        return px

    above_mid = ndimage.binary_dilation(mid, iterations=70) & ~mid & ~base       # 70 px up under the tip
    above_base = ndimage.binary_dilation(base, iterations=90) & ~base              # 90 px up under the middle
    for name, px in (("base", run_on(base, above_base, BASE[0], BASE[1])),
                     ("middle", run_on(mid, above_mid, MIDDLE[0], MIDDLE[1]))):
        Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, f"plate_{name}.png"))
        print("plate", name, "lines up at", CP.lined_up(os.path.join(d, f"plate_{name}.png"), icon)[1])

if __name__ == "__main__":
    build_plates()
