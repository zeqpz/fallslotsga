"""Fall icons animated in parts (owner, 2026-11-04: every icon its own animation, its parts moving separately).

The icon is cut into layers by tools/fall/cut_parts.py (art/blender/parts/<ID>/<layer>.png + parts.json: each layer's
pivot, the layer it rides on, back-to-front order). Here every layer is a picture on a bone at its pivot, parented as
the cut says (a drumstick rides the turkey, the turkey rides the root), so a part turns about its own joint and is
carried by what holds it; the root squashes and stretches the lot. The motion is the icon's own, written in
tools/fall/blender/anims/<ID>.py: a function per clip returning each frame's pose, and the effects it throws.
Clips, frame ranges, camera, effect sprites, glow and render are symanim.py's, so the frames pack and play as before.

The fifth clip, "pop" (symanim.py POP_BLOW), is the icon's own break-apart as it is removed from the board: it starts
on the rest pose and ends with nothing left (Ctx.run(..., out=True), Ctx.glow_out). For it an icon may have EXTRA
pictures (tools/fall/cut_frags.py -> art/blender/parts/<ID>/frags.json: the icon's parts cut into pieces - apple
halves, pumpkin wedges, jug shards - each on its own bone), hidden in every clip until a pose gives them an alpha "a",
and its own effect pools (the anim's XFX = {name: dict(files=[..], n=, size=, tint=, depth=)} -> c.fx[name].emit(..)).

  blender.exe -b --factory-startup --python tools/fall/blender/partsanim.py -- <ID> [build,render,pop,export]
  (render = the four rest-to-rest clips' frames; pop = the pop's frames, filmed 26 units across; export = export_rig.py;
   FALL_POP_ONLY=1 in the environment builds the pop alone, for a quick look - never ship that .blend)
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

    def __init__(self, sid, arm, glow, pools, rng, bones, rig=None):
        self.sid, self.arm, self.glow, self.pools, self.rng, self.bones = sid, arm, glow, pools, rng, bones
        self.damp, self.ease_out, self.ease_in_out = SA.damp, SA.ease_out, SA.ease_in_out
        rig = rig or {}
        self.parts = rig.get("parts", {})        # bone -> its picture
        self.extras = rig.get("extras", [])      # the extra pictures' bones (hidden unless a pose gives them "a")
        self.parent = rig.get("parent", {})      # bone -> the bone it rides
        self.pivot = rig.get("pivot", {})        # bone -> its joint (units, x right, y up, the icon's middle 0)
        self.fx = {}                             # the anim's own effect pools (XFX)

    def alpha(self, b, p):
        """a picture's alpha in pose p: its own "a"; else an extra is hidden and a part takes after what it rides"""
        if "a" in p.get(b, {}):
            return max(0.0, min(1.0, p[b]["a"]))
        if b in self.extras:
            return 0.0
        q = self.parent.get(b)
        while q:
            if "a" in p.get(q, {}):
                return max(0.0, min(1.0, p[q]["a"]))
            q = self.parent.get(q)
        return 1.0

    def run(self, clip, pose, out=False, extras=()):
        """Key every bone on every frame of the clip from pose(i, n) -> {bone: dict(x, y, r, sx, sy)} (missing = rest).
        Frame 0 and the last frame are forced to rest (the game chains the clips on it), except a looping idle,
        whose last frame is the first again.
        out=True (the pop): only frame 0 is forced to rest, the pose runs to the last frame, and there every picture
        is hidden - the clip ends on nothing. With out, or with `extras` (names of extra pictures a rest-to-rest clip
        uses), a pose may carry "a", a picture's alpha, and the extras' bones are posed too."""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        bones = self.bones + [e for e in (self.extras if out else extras)]
        fades = [(b, self.parts[b]) for b in bones if b in self.parts] if (out or extras) else []
        for b, ob in fades:                                      # as ever, up to the clip and after it
            for f in (f0 - 1, f0 + n + 1):
                SA.key_fade(ob, f, 0.0 if b in self.extras else 1.0)
        for i in range(n + 1):
            p = pose(i, n) if 0 < i < n or (out and i == n) else {}
            full = {b: p.get(b, {}) for b in bones}
            if "root" in full and full["root"].get("r"):
                full["root"] = dict(full["root"])
                SA.about_centre(full["root"])
            SA.key_pose(self.arm, f0 + i, **full)
            for b, ob in fades:
                SA.key_fade(ob, f0 + i, 0.0 if out and i == n else self.alpha(b, p))

    def glow_out(self, g, s=None, clip="pop"):
        """the pop's halo: g(i) its strength (0..1) and s(i) its size on frame i; from its resting level to nothing"""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        for i in range(n + 1):
            v = SA.base_glow(self.sid) if i == 0 else 0.0 if i == n else max(0.0, min(1.0, g(i)))
            SA.key_fade(self.glow, f0 + i, v)
            SA.key_obj(self.glow, f0 + i, s=1.0 if i == 0 or s is None else s(i))

    def seal(self, clip="pop"):
        """nothing is left on the clip's last frame: every picture in the scene hidden there"""
        f = SA.START[clip] + SA.CLIPS[clip]
        for ob in bpy.data.objects:
            m = ob.active_material if ob.type == "MESH" else None
            if m and m.node_tree and "fade" in m.node_tree.nodes:
                SA.key_fade(ob, f, 0.0)

    def glow_curve(self, clip, g):
        """the halo's strength over the clip: g(u) for u 0..1, on top of the resting level"""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        base = SA.base_glow(self.sid)
        for i in range(n + 1):
            v = g(i / n) if 0 < i < n else 0
            SA.key_fade(self.glow, f0 + i, base + (.9 - base) * v)
            SA.key_obj(self.glow, f0 + i, s=1 + .05 * v)


class Fx:
    """An anim's own pool of effect sprites (XFX): `files` are art/fall-src/fx names, or "parts:<name>" for a picture
    in the icon's parts folder (cut_frags.py sprites); tint one colour or a list the sprites take in turn; depth the
    sprites' y (under -1 in front of the icon, over 0.1 behind it). Keyed on every frame, in clip frames."""

    def __init__(self, sid, name, files, n, size, tint=(1, 1, 1), depth=-1.3, strength=1.0):
        self.size, self.depth, self.obs, self.used, self.next = size, depth, [], [], 0
        tints = tint if isinstance(tint[0], (tuple, list)) else [tint]
        for i in range(n):
            f = files[i % len(files)]
            path = os.path.join(PARTS, sid, f[6:] + ".png") if f.startswith("parts:") else os.path.join(SA.FX, f + ".png")
            mat = SA.emit_material(f"x_{name}_{i}", SA.image(path), tuple(tints[i % len(tints)]), strength)
            ob = SA.grid_plane(f"x_{name}_{i:02d}", size, 1, mat)
            ob.location = (0, depth - .001 * i, 0)
            SA.key_fade(ob, 0, 0.0)
            self.obs.append(ob)
            self.used.append(set())

    def take(self, frames):
        for k in range(len(self.obs)):
            i = (self.next + k) % len(self.obs)
            if not (self.used[i] & frames):
                self.next = i + 1
                self.used[i] |= frames
                return self.obs[i]
        print("FX POOL EMPTY", self.obs[0].name if self.obs else "?")
        return None

    def emit(self, i0, i1, path, rng=None, spin=0.0, rot=None, grow=(1, 1), fade=(1, 1), aim=None, clip="pop",
             wrap=False):
        """One sprite from clip frame i0 to i1 along path(t) -> (x, z), t 0..1. grow / fade: (start, end) or a
        function of t (grow may return (sx, sz)); rot its turn at the start (degrees counter-clockwise, random if
        None), spin how far it turns on the way; aim="head" points the sprite's top along its flight, "tail" away from
        it (a drop: its point trails). wrap: a looping clip's sprite may live across the loop's seam."""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        if not wrap:
            i0, i1 = max(i0, 1), min(i1, n - 1 if clip == "pop" else n)
        if i1 < i0:
            return None
        fr = (lambda i: f0 + i % n) if wrap else (lambda i: f0 + i)
        ob = self.take({fr(i) for i in range(i0 - 1, i1 + 2)})
        if ob is None:
            return None
        r0 = rot if rot is not None else (rng.uniform(0, 360) if rng else 0.0)
        SA.key_fade(ob, fr(i0 - 1), 0.0)
        SA.key_fade(ob, fr(i1 + 1), 0.0)
        for i in range(i0, i1 + 1):
            t = (i - i0) / max(1, i1 - i0)
            x, z = path(t)
            g = grow(t) if callable(grow) else grow[0] + (grow[1] - grow[0]) * t
            sx, sz = g if isinstance(g, tuple) else (g, g)
            r = r0 + spin * t
            if aim:
                (xa, za), (xb, zb) = path(max(0.0, t - .03)), path(min(1.0, t + .03))
                r = math.degrees(math.atan2(zb - za, xb - xa)) - 90 + (180 if aim == "tail" else 0)
            SA.key_obj(ob, fr(i), x=x, z=z, sx=max(.01, sx), sz=max(.01, sz), r=-r)
            a = fade(t) if callable(fade) else fade[0] + (fade[1] - fade[0]) * t
            SA.key_fade(ob, fr(i), max(0.0, min(1.0, a)))
        return ob

    def hold(self, clip, fn):
        """One sprite kept for a whole clip: fn(i, n) -> dict(x, z, s or sx/sz, r (ccw), a, behind=bool) per frame."""
        f0, n = SA.START[clip], SA.CLIPS[clip]
        ob = self.take(set(range(f0 - 1, f0 + n + 2)))
        if ob is None:
            return None
        y0 = ob.location.y
        SA.key_fade(ob, f0 - 1, 0.0)
        for i in range(n + 1):
            d = fn(i, n)
            ob.location.y = d["behind"] if isinstance(d.get("behind"), float) else (.3 if d.get("behind") else y0)
            s = d.get("s", 1.0)
            SA.key_obj(ob, f0 + i, x=d.get("x", 0.0), z=d.get("z", 0.0), sx=max(.01, d.get("sx", s)),
                       sz=max(.01, d.get("sz", s)), r=-d.get("r", 0.0))
            SA.key_fade(ob, f0 + i, max(0.0, min(1.0, d.get("a", 1.0))))
        ob.location.y = y0
        SA.key_obj(ob, f0 + n + 1, x=0.0, z=0.0)
        SA.key_fade(ob, f0 + n + 1, 0.0)
        return ob


def build_rig(sid):
    spec = json.load(open(os.path.join(PARTS, sid, "parts.json")))
    fj = os.path.join(PARTS, sid, "frags.json")
    frags = json.load(open(fj))["frags"] if os.path.exists(fj) else []
    arm_d = bpy.data.armatures.new("rig")
    arm = bpy.data.objects.new("rig", arm_d)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_d.edit_bones
    root = eb.new("root")
    root.head, root.tail = (0, 0, -SA.HALF), (0, 0, -SA.HALF + 1.0)   # the foot of the icon: squash and stretch
    for L in spec["layers"] + frags:
        b = eb.new(L["name"])
        x, z = px(L["pivot"])
        b.head, b.tail = (x, 0, z), (x, 0, z + .5)
    for L in spec["layers"] + frags:
        eb[L["name"]].parent = eb[L["parent"]] if L["parent"] != "root" else root
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
    bpy.context.view_layer.update()
    from mathutils import Matrix
    parts = {}
    for L in spec["layers"]:
        mat = SA.emit_material("part_" + L["name"], SA.image(os.path.join(PARTS, sid, L["png"])))
        ob = SA.grid_plane("part_" + L["name"], 10.0, 1, mat)
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = L["name"]
        ob.matrix_world = Matrix.Translation((0, -.05 * L["order"], 0))   # nearer the camera the later it is drawn
        parts[L["name"]] = ob
    for L in frags:                                              # the extra pictures: there, but not shown
        mat = SA.emit_material("part_" + L["name"], SA.image(os.path.join(PARTS, sid, L["png"])))
        ob = SA.grid_plane("part_" + L["name"], 10.0, 1, mat)
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = L["name"]
        ob.matrix_world = Matrix.Translation((0, L["depth"], 0))
        SA.key_fade(ob, 0, 0.0)
        parts[L["name"]] = ob
    gm = SA.emit_material("glow_" + sid, SA.image(os.path.join(SA.ICONS, sid + "_glow.png")),
                          SA.GLOW[SA.TIER.get(sid, sid if sid in SA.GLOW else 0)], 1.6)
    glow = SA.grid_plane("glow", 12.0, 1, gm)
    glow.location = (0, .6, 0)
    rig = dict(parts=parts, extras=[L["name"] for L in frags],
               parent={L["name"]: L["parent"] for L in spec["layers"] + frags},
               pivot={"root": (0.0, -SA.HALF), **{L["name"]: px(L["pivot"]) for L in spec["layers"] + frags}})
    return arm, glow, ["root"] + [L["name"] for L in spec["layers"]], rig


def build(sid, seed=None):
    SA.clear()
    SA.setup_scene(sid)
    rng = random.Random(seed if seed is not None else sum(map(ord, sid)) * 11)
    arm, glow, bones, rig = build_rig(sid)
    an = importlib.import_module("anims." + sid)
    importlib.reload(an)
    sizes = {"leaf": 10, "sparkle": 14, "glint": 6, "steam": 10, "bubble": 10, "popcorn": 12, "puff": 6, "drop": 14,
             "straw": 10, "feather": 8, "crumb": 12}
    pools = {k: SA.Pool(k, sizes.get(k, 8), sid) for k in set(getattr(an, "FX", [])) | {"sparkle"}}
    pools["ring"] = SA.Pool2("ring", 2, 9.0, behind=True)
    pools["rays"] = SA.Pool2("rays", 1, 11.0, behind=True)
    ctx = Ctx(sid, arm, glow, pools, rng, bones, rig)
    ctx.fx = {k: Fx(sid, k, **v) for k, v in getattr(an, "XFX", {}).items()}
    for clip in ([] if os.environ.get("FALL_POP_ONLY") else SA.BASE):
        getattr(an, clip)(ctx)
    if hasattr(an, "pop"):                                      # last: the other clips' random numbers stay as they were
        an.pop(ctx)
        ctx.seal("pop")
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
    if "pop" in steps:
        SA.render(sid, ["pop"])
    if "export" in steps:
        import export_rig
        export_rig.export(sid)
    print("DONE", sid)
