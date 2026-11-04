"""Cut a fall icon into the parts Blender moves (tools/fall/blender/partsanim.py), from its spec
tools/fall/parts/<ID>.py (PLATES, LAYERS - see H1.py).

  python tools/fall/cut_parts.py <ID> plates   # OpenRouter edits of the icon -> art/fall-src/parts/<ID>/plate_<name>.png
  python tools/fall/cut_parts.py <ID> cut      # -> art/blender/parts/<ID>/<layer>.png + parts.json, and a check sheet

How a layer is made:
  art            (cut "poly": the polygon's own shape, for a part whose colour runs on into its neighbour)
                 the icon's own pixels, cut along its own black outlines: every flat-coloured area (the drawing's
                 regions between its ink lines) mostly inside `poly`, the ink lines round them and the sticker border
                 next to them - so a part comes away whole, with its own outline, and no slice of a neighbour
  plate:<a>      plate a, whole (what is left when everything in front of it has moved away)
  diff:<a>-<b>   (keep="warm" or keep=<fn(rgb, sat, value) -> bool>: only that colour, see colour_only)
                 where plate a differs from plate b (the turkey on the platter: body minus platter), and over it the
                 icon's own pixels wherever the icon shows that layer - so at rest it is exactly the icon, and the plate
                 only fills in under the parts that move off it
Plates are lined up on the icon by their silhouettes (cross-correlation), the generator may shift its drawing."""
import importlib.util, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clean_alpha

ROOT = os.path.dirname(os.path.dirname(HERE))
ICONS = os.path.join(ROOT, "art", "fall-src", "icons")
SRC = os.path.join(ROOT, "art", "fall-src", "parts")
OUT = os.path.join(ROOT, "art", "blender", "parts")
SIDE = 1000


def spec(sid):
    sp = importlib.util.spec_from_file_location("parts_" + sid, os.path.join(HERE, "parts", sid + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def plates(sid):
    import orimg
    from concurrent.futures import ThreadPoolExecutor
    s = spec(sid)
    d = os.path.join(SRC, sid)
    os.makedirs(d, exist_ok=True)
    ref = os.path.join(ICONS, sid + ".png")
    with ThreadPoolExecutor(4) as ex:
        for name, cost in ex.map(lambda kv: (kv[0], orimg.generate(os.path.join(d, f"plate_{kv[0]}.png"), kv[1],
                                                                    aspect="1:1", refs=[ref])[1]), s.PLATES.items()):
            print("plate", name, cost)


def rgba(path):
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.int16)


def lined_up(path, icon):
    """A plate, cleaned, at the icon's size, moved so its silhouette lies on the icon's."""
    tmp = path[:-4] + "_clean.png"
    clean_alpha.clean(path, tmp)
    im = Image.open(tmp).convert("RGBA").resize((SIDE, SIDE), Image.LANCZOS)
    a = np.asarray(im).astype(np.int16)
    m1 = (icon[..., 3] > 128).astype(np.float32)
    m2 = (a[..., 3] > 128).astype(np.float32)
    c = signal.fftconvolve(m1, m2[::-1, ::-1], mode="same")
    dy, dx = np.unravel_index(np.argmax(c), c.shape)
    dy, dx = dy - SIDE // 2, dx - SIDE // 2
    if max(abs(dx), abs(dy)) > 60:                              # a match that far off is not one
        dx = dy = 0
    out = np.zeros_like(a)
    ys, xs = slice(max(0, dy), SIDE + min(0, dy)), slice(max(0, dx), SIDE + min(0, dx))
    ys0, xs0 = slice(max(0, -dy), SIDE + min(0, -dy)), slice(max(0, -dx), SIDE + min(0, -dx))
    out[ys, xs] = a[ys0, xs0]
    return out, (dx, dy)


def differs(a, b, thr=95):
    m = (np.abs(a[..., :3] - b[..., :3]).sum(2) > thr) & (a[..., 3] > 128) | ((a[..., 3] > 128) & (b[..., 3] < 60))
    m = ndimage.binary_opening(m, iterations=2)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, 1 + np.nonzero(sizes >= 1500)[0])
    return ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=3))


def WARM(rgb, sat, mx):
    """oranges and browns (a roast): the default colour a "keep" layer holds on to"""
    return (rgb[..., 0] >= rgb[..., 1]) & (rgb[..., 1] >= rgb[..., 2] - .02) & (sat > .4) & (mx > .25)


def colour_only(px, m, pick=WARM):
    """Inside m, only the colour pick(rgb 0..1, saturation, value) says is this layer's - its largest patch, whole
    (holes filled), with its ink line round it. A spec may pass its own pick as LAYERS[..]["keep"]."""
    rgb = px[..., :3].astype(np.float32) / 255
    mx, mn = rgb.max(2), rgb.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    warm = m & pick(rgb, sat, mx)
    warm = ndimage.binary_opening(warm, iterations=2)
    lab, n = ndimage.label(warm)
    if n:
        sizes = ndimage.sum(warm, lab, range(1, n + 1))
        warm = lab == 1 + int(np.argmax(sizes))
    warm = ndimage.binary_fill_holes(warm)
    ink = (px[..., 3] > 128) & (mx < .24)
    for _ in range(8):
        warm |= ndimage.binary_dilation(warm) & ink
    return ndimage.binary_fill_holes(warm)


def poly_mask(poly):
    im = Image.new("L", (SIDE, SIDE), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in poly], fill=255)
    return np.asarray(im) > 0


def art_cut(icon, poly):
    """The drawing's regions mostly inside poly, their ink and the sticker border beside them."""
    a = icon
    on = a[..., 3] > 128
    v = a[..., :3].max(2) / 255
    ink = on & (v < .24)
    regions, n = ndimage.label(on & ~ink)
    inside = poly_mask(poly)
    take = np.zeros(n + 1, bool)
    tot = np.bincount(regions.ravel(), minlength=n + 1)
    ins = np.bincount(regions[inside].ravel(), minlength=n + 1)
    take[1:] = ins[1:] >= .55 * np.maximum(tot[1:], 1)
    m = take[regions]
    near = ndimage.binary_dilation(m, iterations=7) & ndimage.binary_dilation(inside, iterations=10)
    m |= near & ink
    cream = on & ~ink & (a[..., 0] > 215) & (a[..., 1] > 200) & (a[..., 2] > 160)
    m |= ndimage.binary_dilation(m, iterations=16) & cream & ~take[regions] & ndimage.binary_dilation(inside, iterations=14)
    return ndimage.binary_fill_holes(m)


def cut(sid):
    s = spec(sid)
    icon = rgba(os.path.join(ICONS, sid + ".png"))
    plates_ = {}
    for name in s.PLATES:
        plates_[name], shift = lined_up(os.path.join(SRC, sid, f"plate_{name}.png"), icon)
        print("plate", name, "shift", shift)
    # the moving parts cut from the art first: whatever they cover is where the plates fill in
    masks = {}
    for L in s.LAYERS:
        if L["src"] == "art":   # cut "poly": the outline shape itself (a part whose colour runs into its neighbour)
            masks[L["name"]] = (poly_mask(L["poly"]) & (icon[..., 3] > 0)) if L.get("cut") == "poly" else art_cut(icon, L["poly"])
    movers = np.zeros((SIDE, SIDE), bool)
    for m in masks.values():
        movers |= m
    out = os.path.join(OUT, sid)
    os.makedirs(out, exist_ok=True)
    layers = []
    for order, L in enumerate(s.LAYERS):
        src = L["src"]
        if src == "art":
            px = icon.copy()
            m = masks[L["name"]]
        elif src.startswith("plate:"):
            px = plates_[src[6:]].copy()
            m = px[..., 3] > 0
        else:                                                  # diff:a-b
            a_, b_ = src[5:].split("-")
            px = plates_[a_].copy()
            m = differs(px, plates_[b_])
            # where the icon itself shows this layer: different from the plate under it, not a moving part, and
            # on this layer's own silhouette (not a sliver of rim the plate drew a pixel off)
            if L.get("keep"):                                  # only the layer's own colour, not the plate's shadow
                m = colour_only(px, m, WARM if L["keep"] == "warm" else L["keep"])
            own = differs(icon, plates_[b_]) & ~movers & ndimage.binary_dilation(m, iterations=6)
            px[own] = icon[own]
            m |= own
            # and the icon's sticker border round it, where it sits out past the layer under it
            on = icon[..., 3] > 128
            cream = on & (icon[..., 0] > 215) & (icon[..., 1] > 200) & (icon[..., 2] > 160)
            border = cream & ndimage.binary_dilation(m, iterations=48) & (plates_[b_][..., 3] < 40) & ~movers
            px[border] = icon[border]
            m |= border
        soft = ndimage.gaussian_filter(m.astype(np.float32), .7)
        px[..., 3] = (px[..., 3] * np.clip(soft * 1.4, 0, 1)).astype(np.int16)
        fn = L["name"] + ".png"
        Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA").save(os.path.join(out, fn))
        layers.append(dict(name=L["name"], png=fn, pivot=list(L["pivot"]), parent=L["parent"], order=order))
    json.dump({"size": [SIDE, SIDE], "layers": layers}, open(os.path.join(out, "parts.json"), "w"), indent=1)
    sheet(sid, layers)


def sheet(sid, layers):
    """Every layer on its own, then all of them laid back together next to the icon (they must match)."""
    out = os.path.join(OUT, sid)
    T = 240
    n = len(layers) + 2
    sh = Image.new("RGBA", (T * n, T), (60, 60, 72, 255))
    comp = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    for i, L in enumerate(layers):
        im = Image.open(os.path.join(out, L["png"])).convert("RGBA")
        comp.alpha_composite(im)
        d = ImageDraw.Draw(im)
        x, y = L["pivot"]
        d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=(255, 0, 255, 255), width=4)
        sh.alpha_composite(im.resize((T, T)), (i * T, 0))
    sh.alpha_composite(comp.resize((T, T)), ((n - 2) * T, 0))
    sh.alpha_composite(Image.open(os.path.join(ICONS, sid + ".png")).convert("RGBA").resize((T, T)), ((n - 1) * T, 0))
    sh.convert("RGB").save(os.path.join(out, "check.jpg"), quality=90)
    a = np.asarray(comp).astype(np.float32)
    b = np.asarray(Image.open(os.path.join(ICONS, sid + ".png")).convert("RGBA")).astype(np.float32)
    print("rest vs icon: mean abs diff", round(float(np.abs(a - b).mean()), 2), "/255")


if __name__ == "__main__":
    sid, step = sys.argv[1], sys.argv[2]
    {"plates": plates, "cut": cut}[step](sid)
