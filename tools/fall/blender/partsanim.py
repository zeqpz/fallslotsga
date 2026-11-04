"""Fall icons animated in parts (owner, 2026-11-04: every icon its own animation, its parts moving separately).

The icon is cut into layers by tools/fall/cut_parts.py (art/blender/parts/<ID>/<layer>.png + parts.json: each layer's
pivot, the layer it rides on, back-to-front order). Here every layer is a picture on a bone at its pivot, parented as
the cut says (a drumstick rides the turkey, the turkey rides the root), so a part turns about its own joint and is
carried by what holds it; the root squashes and stretches the lot. The motion is the icon's own, written in
tools/fall/blender/anims/<ID>.py: a function per clip returning each frame's pose, and the effects it throws.
Clips, frame ranges, camera, effect sprites, glow and render are symanim.py's, so the frames pack and play as before.

  blender.exe -b --factory-startup --python tools/fall/blender/partsanim.py -- <ID> [build,render]
or, live over the Blender MCP: sys.path += [this folder]; import partsanim; partsanim.build("<ID>")"""
import importlib, json, math, os, random, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import symanim as SA

PARTS = os.path.join(SA.ROOT, "art", "blender", "parts")


def px(p):
    """icon px -> picture units (x right, z up), the icon's middle at the origin"""
    return (p[0] - 500) / 100, (500 - p[1]) / 100


class Ctx:
    """What a clip script sees: the bones by layer name, the effect pools, the clip's frames, helpers."""

    def __init__(self, sid, arm, glow, pools, rng, bones):
        self.sid, self.arm, self.glow, self.pools, self.rng, self.bones = sid, arm, glow, pools, rng, bones
        self.damp, self.ease_out, self.ease_in_out = SA.damp, SA.ease_out, SA.ease_in_out

    def run(self, clip, pose):
        """Key every bone on every frame of the clip from pose(i, n) -> {bone: dict(x, y, r, sx, sy)} (missing = rest).
        Frame 0 and the last frame are forced to rest (the game chains the clips on it), except a looping idle,
        whose last frame is the first again."""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        for i in range(n + 1):
            p = pose(i, n) if 0 < i < n else {}
            full = {b: p.get(b, {}) for b in self.bones}
            if "root" in full and full["root"].get("r"):
                SA.about_centre(full["root"])
            SA.key_pose(self.arm, f0 + i, **full)

    def glow_curve(self, clip, g):
        """the halo's strength over the clip: g(u) for u 0..1, on top of the resting level"""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        base = SA.base_glow(self.sid)
        for i in range(n + 1):
            v = g(i / n) if 0 < i < n else 0
            SA.key_fade(self.glow, f0 + i, base + (.9 - base) * v)
            SA.key_obj(self.glow, f0 + i, s=1 + .05 * v)


def build_rig(sid):
    spec = json.load(open(os.path.join(PARTS, sid, "parts.json")))
    arm_d = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", arm_d)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_d.edit_bones
    root = eb.new("root")
    root.head, root.tail = (0, 0, -SA.HALF), (0, 0, -SA.HALF + 1.0)   # the foot of the icon: squash and stretch
    for L in spec["layers"]:
        b = eb.new(L["name"])
        x, z = px(L["pivot"])
        b.head, b.tail = (x, 0, z), (x, 0, z + .5)
    for L in spec["layers"]:
        eb[L["name"]].parent = eb[L["parent"]] if L["parent"] != "root" else root
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    bpy.context.view_layer.update()
    from mathutils import Matrix
    for L in spec["layers"]:
        mat = SA.emit_material("part_" + L["name"], SA.image(os.path.join(PARTS, sid, L["png"])))
        ob = SA.grid_plane("part_" + L["name"], 10.0, 1, mat)
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = L["name"]
        ob.matrix_world = Matrix.Translation((0, -.05 * L["order"], 0))   # nearer the camera the later it is drawn
    gm = SA.emit_material("glow_" + sid, SA.image(os.path.join(SA.ICONS, sid + "_glow.png")),
                          SA.GLOW[SA.TIER.get(sid, sid if sid in SA.GLOW else 0)], 1.6)
    glow = SA.grid_plane("glow", 12.0, 1, gm)
    glow.location = (0, .6, 0)
    return arm, glow, ["root"] + [L["name"] for L in spec["layers"]]


def build(sid, seed=None):
    SA.clear()
    SA.setup_scene(sid)
    rng = random.Random(seed if seed is not None else sum(map(ord, sid)) * 11)
    arm, glow, bones = build_rig(sid)
    an = importlib.import_module("anims." + sid)
    importlib.reload(an)
    sizes = {"leaf": 10, "sparkle": 14, "glint": 6, "steam": 10, "bubble": 10, "popcorn": 12, "puff": 6, "drop": 14,
             "straw": 10, "feather": 8, "crumb": 12}
    pools = {k: SA.Pool(k, sizes.get(k, 8), sid) for k in set(getattr(an, "FX", [])) | {"sparkle"}}
    pools["ring"] = SA.Pool2("ring", 2, 9.0, behind=True)
    pools["rays"] = SA.Pool2("rays", 1, 11.0, behind=True)
    ctx = Ctx(sid, arm, glow, pools, rng, bones)
    for clip in ("idle", "land", "hit", "multi"):
        getattr(an, clip)(ctx)
    for ob in [o for o in bpy.data.objects if o.animation_data and o.animation_data.action]:
        for fc in SA.fcurves(ob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR" if ob is arm else "BEZIER"
    for m in bpy.data.materials:
        ad = m.node_tree.animation_data if m.node_tree else None
        if ad and ad.action:
            for fc in SA.fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    os.makedirs(SA.BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SA.BLEND, sid + ".blend"))
    return arm


if __name__ == "__main__" and "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    sid = args[0]
    steps = args[1].split(",") if len(args) > 1 else ["build", "render"]
    if "build" in steps:
        build(sid)
    else:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(SA.BLEND, sid + ".blend"))
    if "render" in steps:
        SA.render(sid)
    print("DONE", sid)
