"""Extra pictures for an icon's part rig (tools/fall/blender/partsanim.py): the pieces it BREAKS into in its "pop" clip
(owner, 2026-11-10: every icon its own break-apart, made of the icon itself - no generic shards), and the odd picture
an idle wants (the XFS crow's head, its glowing face). Nothing here changes the icon's cut (cut_parts.py, parts.json):
the extras are more pictures on more bones, hidden in every clip until a pose gives them an alpha, so the four
rest-to-rest clips play as they did. An extra is made from the icon's own layers as they lie at rest - a layer, or
several laid over each other - cut by a map of pieces (sectors round a point, bands along a line, cells round seed
points, polygons), so the pieces together ARE the picture they replace and the swap does not show.

  .venv/Scripts/python.exe tools/fall/cut_frags.py <ID>[,<ID>..] | all
-> art/blender/parts/<ID>/x_<name>.png (1000 px, like the layers), frags.json, fx_<name>.png (small effect sprites for
   the anim's XFX pools, "parts:fx_<name>"), frags_check.jpg (the pieces pulled apart, their joints ringed)
The recipes are tools/fall/parts/frags.py: one function per icon, given a Cutter."""
import json, math, os, sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARTS = os.path.join(ROOT, "art", "blender", "parts")
ICONS = os.path.join(ROOT, "art", "fall-src", "icons")
SIDE = 1000
INK = (40, 22, 14)                      # the art's outline: a warm near-black
YY, XX = np.mgrid[0:SIDE, 0:SIDE].astype(np.float32)


def over(a, b):
    """b laid over a (float RGBA 0..1, straight alpha)"""
    aa, ba = a[..., 3:], b[..., 3:]
    oa = ba + aa * (1 - ba)
    rgb = (b[..., :3] * ba + a[..., :3] * aa * (1 - ba)) / np.maximum(oa, 1e-6)
    return np.dstack([rgb, oa])


def noise(seed, scale):
    """smooth noise -1..1 over the picture, features about `scale` px across"""
    rng = np.random.RandomState(seed)
    n = max(2, int(SIDE / scale) + 2)
    g = rng.uniform(-1, 1, (n, n)).astype(np.float32)
    return ndimage.zoom(g, SIDE / (n - 1), order=3)[:SIDE, :SIDE]


class Cutter:
    def __init__(self, sid):
        self.sid = sid
        self.dir = os.path.join(PARTS, sid)
        self.spec = json.load(open(os.path.join(self.dir, "parts.json")))
        self.order = {L["name"]: L["order"] for L in self.spec["layers"]}
        self.frags, self.pics, self.sprites = [], {}, {}

    # ---- sources
    def layer(self, name):
        L = next(L for L in self.spec["layers"] if L["name"] == name)
        return np.asarray(Image.open(os.path.join(self.dir, L["png"])).convert("RGBA")).astype(np.float32) / 255

    def comp(self, *names):
        """the named layers (all of them if none) laid over each other as at rest, back to front"""
        names = names or tuple(self.order)
        out = np.zeros((SIDE, SIDE, 4), np.float32)
        for n in sorted(names, key=lambda n: self.order[n]):
            out = over(out, self.layer(n))
        return out

    def icon(self):
        return np.asarray(Image.open(os.path.join(ICONS, self.sid + ".png")).convert("RGBA")).astype(np.float32) / 255

    # ---- maps of pieces (an int per pixel)
    def warp(self, lab, amp, scale=120, seed=1):
        """the map's borders made to wander by up to `amp` px (a break is never ruler-straight)"""
        if not amp:
            return lab
        x = np.clip(XX + amp * noise(seed, scale), 0, SIDE - 1)
        y = np.clip(YY + amp * noise(seed + 77, scale), 0, SIDE - 1)
        return lab[y.round().astype(int), x.round().astype(int)]

    def sectors(self, centre, n, phase=0.0, amp=0, seed=1, angles=None):
        """n pie sectors round centre (or cut at `angles`, degrees, counter-clockwise from +x, ascending)"""
        a = (np.degrees(np.arctan2(centre[1] - YY, XX - centre[0])) - phase) % 360
        if angles is None:
            lab = np.minimum((a / (360 / n)).astype(int), n - 1)
        else:
            cuts = sorted((x - phase) % 360 for x in angles)
            lab = np.searchsorted(cuts, a, side="right") % len(cuts)
        return self.warp(lab, amp, seed=seed)

    def bands(self, p0, p1, cuts, amp=0, seed=1):
        """bands across the line p0 -> p1, cut at the fractions `cuts` (ascending, 0..1) of the way along it"""
        d = np.array(p1, np.float32) - np.array(p0, np.float32)
        t = ((XX - p0[0]) * d[0] + (YY - p0[1]) * d[1]) / float(d @ d)
        return self.warp(np.searchsorted(np.array(cuts, np.float32), t), amp, seed=seed)

    def cells(self, points, amp=0, seed=1, scale=120):
        """each pixel to its nearest seed point (shards)"""
        d = np.stack([(XX - x) ** 2 + (YY - y) ** 2 for x, y in points])
        return self.warp(np.argmin(d, 0), amp, scale=scale, seed=seed)

    def polys(self, polys, rest=None):
        """polygons, later over earlier; pixels in none get `rest` (default: the nearest polygon's number)"""
        im = Image.new("I", (SIDE, SIDE), -1)
        d = ImageDraw.Draw(im)
        for k, p in enumerate(polys):
            d.polygon([tuple(q) for q in p], fill=k)
        lab = np.asarray(im).astype(int)
        if rest is None:
            idx = ndimage.distance_transform_edt(lab < 0, return_distances=False, return_indices=True)
            lab = lab[idx[0], idx[1]]
        else:
            lab = np.where(lab < 0, rest, lab)
        return lab

    # ---- the pictures
    def add(self, name, img, parent="root", over_=None, pivot=None, lift=0.0):
        """an extra picture: img float RGBA (1000 px, placed as in the icon); it rides `parent` (root, a layer or an
        earlier extra) about `pivot` (icon px; default its own middle) and is drawn just over layer `over_`
        (default the last layer), `lift` further front (negative: behind)"""
        al = img[..., 3]
        if al.max() < .02:
            print("  (empty piece skipped:", name + ")")
            return None
        if pivot is None:
            w = al / al.sum()
            pivot = (float((XX * w).sum()), float((YY * w).sum()))
        o = self.order[over_] if over_ else max(self.order.values())
        depth = -.05 * o - .004 - .0008 * len(self.frags) - lift
        fn = "x_" + name + ".png"
        Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(os.path.join(self.dir, fn))
        self.frags.append(dict(name=name, png=fn, pivot=[round(pivot[0], 1), round(pivot[1], 1)], parent=parent,
                               depth=round(depth, 5)))
        self.pics[name] = img
        return name

    def pieces(self, src, lab, names, parent="root", over_=None, ink=0, pivots=None, lift=0.0, keep=None):
        """src cut by the map `lab` into extras `names` (a list, by the map's numbers; None skips one; or a format
        like "w{}"). ink: px of outline drawn along the cuts (cracks: the pieces read as broken from frame one)."""
        on = src[..., 3] > .02
        ks = [k for k in np.unique(lab[on])]
        out = []
        for j, k in enumerate(ks):
            name = names.format(j) if isinstance(names, str) else (names[k] if k < len(names) else None)
            if name is None:
                continue
            m = (lab == k) & on
            if keep is not None and m.sum() < keep:
                continue
            img = src.copy()
            img[..., 3] = np.where(m, src[..., 3], 0)
            if ink:
                d = ndimage.distance_transform_edt(m | ~on)       # how far inside the piece, from its cut edges only
                w = np.clip((ink + .5 - d), 0, 1)[..., None] * (m[..., None])
                img[..., :3] = img[..., :3] * (1 - w) + np.array(INK, np.float32) / 255 * w
            piv = pivots[j] if pivots else None
            n = self.add(name, img, parent, over_, piv, lift)
            if n:
                out.append(n)
        return out

    def face(self, name, of, colour, edge=7, parent=None, shade=.82, grow=0):
        """the inside of piece `of` (its cut face, shown by sliding it out from behind the piece): the piece's
        shape, flat `colour` (shaded toward its foot), outlined; rides the piece, drawn just behind it"""
        src = self.pics[of]
        m = src[..., 3] > .5
        if grow:
            m = ndimage.binary_dilation(m, iterations=grow)
        d = ndimage.distance_transform_edt(m)
        ys = np.nonzero(m.any(1))[0]
        g = np.clip((YY - ys.min()) / max(1, ys.max() - ys.min()), 0, 1)[..., None]
        rgb = np.array(colour, np.float32) / 255 * (1 - (1 - shade) * g)
        w = np.clip(edge + .5 - d, 0, 1)[..., None]
        img = np.dstack([rgb * (1 - w) + np.array(INK, np.float32) / 255 * w, m.astype(np.float32)])
        f = next(f for f in self.frags if f["name"] == of)
        n = self.add(name, img, parent or of, None, f["pivot"])
        self.frags[-1]["depth"] = round(f["depth"] + .0004, 5)   # just behind its piece
        return n

    def sprite(self, name, draw, size=160, ss=4):
        """a small effect sprite painted here: draw(d, S) on a PIL ImageDraw of an S x S canvas (drawn `ss` x larger
        and shrunk, so it is smooth) -> fx_<name>.png, for an XFX pool ("parts:fx_<name>")"""
        S = size * ss
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        draw(ImageDraw.Draw(im), S)
        im = im.resize((size, size), Image.LANCZOS)
        im.save(os.path.join(self.dir, "fx_" + name + ".png"))
        self.sprites[name] = im

    def crop_sprite(self, name, src, box, size=192, mask=None):
        """an effect sprite cut out of the art: `box` (x0, y0, x1, y1 icon px, made square about its middle) of src"""
        x0, y0, x1, y1 = box
        s = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        img = src if mask is None else np.dstack([src[..., :3], src[..., 3] * mask])
        im = Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA")
        im = im.crop((round(cx - s / 2), round(cy - s / 2), round(cx + s / 2), round(cy + s / 2)))
        im = im.resize((size, size), Image.LANCZOS)
        im.save(os.path.join(self.dir, "fx_" + name + ".png"))
        self.sprites[name] = im

    # ---- out
    def save(self):
        json.dump({"frags": self.frags, "sprites": sorted(self.sprites)}, open(os.path.join(self.dir, "frags.json"), "w"),
                  indent=1)
        # the pieces pulled apart from the icon's middle, their joints ringed; then the sprites
        W = 1500
        sheet = Image.new("RGBA", (W, W + 200), (52, 52, 64, 255))
        for f in sorted(self.frags, key=lambda f: -f["depth"]):
            img = self.pics[f["name"]]
            px, py = f["pivot"]
            dx, dy = (px - 500) * .42, (py - 500) * .42
            im = Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA")
            sheet.alpha_composite(im, (round(250 + dx), round(250 + dy)))
        d = ImageDraw.Draw(sheet)
        for f in self.frags:
            px, py = f["pivot"]
            x, y = 250 + px + (px - 500) * .42, 250 + py + (py - 500) * .42
            d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 60, 200, 255), width=3)
            d.text((x + 9, y - 6), f["name"], fill=(255, 255, 255, 255))
        for k, (n, im) in enumerate(sorted(self.sprites.items())):
            sheet.alpha_composite(im.resize((150, 150)), (20 + k * 170, W + 10))
            d.text((20 + k * 170, W + 165), n, fill=(255, 255, 255, 255))
        sheet.convert("RGB").resize((W * 2 // 3, (W + 200) * 2 // 3), Image.LANCZOS).save(
            os.path.join(self.dir, "frags_check.jpg"), quality=88)
        print(self.sid, len(self.frags), "extras,", len(self.sprites), "sprites")


def run(sid):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "parts"))
    import frags
    fn = getattr(frags, sid, None)
    if fn is None:
        print(sid, "has no recipe in parts/frags.py")
        return
    c = Cutter(sid)
    for old in os.listdir(c.dir):
        if old.startswith(("x_", "fx_")) and old.endswith(".png"):
            os.remove(os.path.join(c.dir, old))
    fn(c)
    c.save()


if __name__ == "__main__":
    ids = sys.argv[1].split(",") if len(sys.argv) > 1 else []
    if ids == ["all"]:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "parts"))
        import frags
        ids = [n for n in dir(frags) if n[0] in "HLBE" and callable(getattr(frags, n))]
    for sid in ids:
        run(sid)
