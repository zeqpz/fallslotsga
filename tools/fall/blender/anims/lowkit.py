"""Small helpers the L7-L10 part animations share (only these anim files use it; partsanim/symanim are untouched).

track_glow(c, bone)    the halo rides a bone (the root, or the middle of a chain), so it stays behind the icon when the whole icon turns or hops
                       (shrink < 1 pulls it in a little, for an icon that turns far)
tint(c, kind, rgb)     multiply an effect pool's sprite colour (the drop sprite is honey-gold: red for cranberry etc.)
paint(c, kind, name, fn, size)
                       swap an effect pool's sprite picture for one painted here, fn(x, y) -> (r, g, b, a) for x, y
                       in -1..1 (y up) - for an effect the shared sprites don't have"""
import bpy
from mathutils import Matrix


def track_glow(c, bone="root", shrink=1.0):
    g, arm = c.glow, c.arm
    b = arm.data.bones[bone]
    parent = arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    g.parent = arm
    g.parent_type = "BONE"
    g.parent_bone = bone
    g.matrix_parent_inverse = parent.inverted() @ Matrix.Diagonal((shrink, shrink, shrink, 1))   # a turned halo's corners stay in frame


def _tex(ob):
    return next(n for n in ob.active_material.node_tree.nodes if n.type == "TEX_IMAGE")


def tint(c, kind, rgb):
    for ob in c.pools[kind].obs:
        mul = next(n for n in ob.active_material.node_tree.nodes if n.type == "MIX_RGB")
        mul.inputs[2].default_value = (*rgb, 1)


def paint(c, kind, name, fn, size=128):
    im = bpy.data.images.get(name)
    if im is None:
        im = bpy.data.images.new(name, size, size, alpha=True)
        px = []
        for j in range(size):
            y = (j + .5) / size * 2 - 1
            for i in range(size):
                px.extend(fn((i + .5) / size * 2 - 1, y))
        im.pixels[:] = px
        im.alpha_mode = "STRAIGHT"
        im.pack()
    for ob in c.pools[kind].obs:
        _tex(ob).image = im
    return im


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(len(a)))
