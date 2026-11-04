"""Export an icon's animation as data for the game's live renderer (frontend: the Pixi rig player), instead of
frames: for every frame of every clip, where each picture in the scene is (its 2D transform) and how see-through.

The icons are animated in Blender in parts (partsanim.py): every part, the halo and every effect sprite is a flat
picture on a plane. Here each clip is stepped frame by frame and every visible plane is read off the evaluated scene
(so bones, parents, constraints and an anim script's own tricks all come out exactly as rendered) as an affine
matrix taking the picture's own square (u, v in -0.5..0.5, v down) to the frame (Blender units, x right, y down,
the icon's middle at 0), plus its alpha (the material's keyed "fade") and its tint. Back to front by depth.

  blender.exe -b --factory-startup --python tools/fall/blender/export_rig.py -- <ID>[,<ID>..]
-> art/blender/rigs/<ID>/rig.json + the pictures it uses (tools/fall/pack_rigs.py packs them for the game)"""
import json, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import symanim as SA

OUT = os.path.join(SA.ROOT, "art", "blender", "rigs")


def tex_of(mat):
    """(image, tint rgb) of an emit material (symanim.emit_material), or None for anything else."""
    if not mat or not mat.node_tree:
        return None
    nt = mat.node_tree
    if "fade" not in nt.nodes:
        return None
    img = next((n.image for n in nt.nodes if n.type == "TEX_IMAGE" and n.image), None)
    if img is None:
        return None
    tint = (1.0, 1.0, 1.0)
    mix = next((n for n in nt.nodes if n.type == "MIX_RGB" and n.blend_type == "MULTIPLY"), None)
    if mix:
        tint = tuple(round(v, 4) for v in mix.inputs[2].default_value[:3])
    em = next((n for n in nt.nodes if n.type == "EMISSION"), None)
    if em:                                                       # a glow's strength > 1: brighter, clipped at white
        k = em.inputs["Strength"].default_value
        tint = tuple(round(v * k, 4) for v in tint)
    return img, tint


def export(sid):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SA.BLEND, sid + ".blend"))
    sc = bpy.context.scene
    d = os.path.join(OUT, sid)
    os.makedirs(d, exist_ok=True)
    pics, pic_index, items = [], {}, []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.hide_render or not ob.active_material:
            continue
        t = tex_of(ob.active_material)
        if t is None:
            continue
        img, tint = t
        key = (img.name, tint)
        if key not in pic_index:
            path = bpy.path.abspath(img.filepath) if img.filepath else ""
            if not path or not os.path.exists(path):          # made inside Blender (an anim script's own sprite)
                path = os.path.join(d, "gen_" + bpy.path.clean_name(img.name) + ".png")
                img.filepath_raw = path
                img.file_format = "PNG"
                img.save()
            pic_index[key] = len(pics)
            pics.append(dict(file=os.path.abspath(path), tint=list(tint)))   # linear, may pass 1 (pack bakes it)
        xs = [v.co.x for v in ob.data.vertices]
        zs = [v.co.z for v in ob.data.vertices]
        items.append(dict(ob=ob, pic=pic_index[key], w=max(xs) - min(xs), h=max(zs) - min(zs),
                          cx=(max(xs) + min(xs)) / 2, cz=(max(zs) + min(zs)) / 2,
                          fade=ob.active_material.node_tree.nodes["fade"].outputs[0]))
    clips = {}
    for clip, n in SA.CLIPS.items():
        if clip not in SA.START:
            continue
        f0 = SA.START[clip]
        count = n if clip == "idle" else n + 1                  # the same frames the renders had
        frames = []
        for k in range(count):
            sc.frame_set(f0 + k)
            row = []
            for i, it in enumerate(items):
                a = float(it["fade"].default_value)
                if a < .004:
                    continue
                M = it["ob"].matrix_world
                W, H, cx, cz = it["w"], it["h"], it["cx"], it["cz"]
                m = (M[0][0] * W, -M[2][0] * W, -M[0][2] * H, M[2][2] * H,
                     M[0][0] * cx + M[0][2] * cz + M[0][3], -(M[2][0] * cx + M[2][2] * cz + M[2][3]))
                if abs(m[0] * m[3] - m[1] * m[2]) < 1e-6:          # squashed to nothing
                    continue
                row.append((M[1][3], i, it["pic"], [round(v, 4) for v in m], round(min(1.0, a), 3)))
            row.sort(key=lambda r: (-r[0], r[1]))                # far (larger y) first
            frames.append([[r[1], r[2], *r[3], r[4]] for r in row])
        clips[clip] = dict(fps=SA.FPS, loop=clip == "idle", frames=frames)
    rig = dict(id=sid, units=SA.CAM, pics=pics, clips=clips,
               note="frame item: [object id, pic, a, b, c, d, tx, ty, alpha] - a 2D affine (Blender units, y down) "
                    "taking the picture's unit square (u, v in -0.5..0.5, v down) into the icon's frame")
    json.dump(rig, open(os.path.join(d, "rig.json"), "w"), separators=(",", ":"))
    print("EXPORTED", sid, len(pics), "pictures,", {c: len(v["frames"]) for c, v in clips.items()})


if __name__ == "__main__" and "--" in sys.argv:
    for sid in sys.argv[sys.argv.index("--") + 1].split(","):
        export(sid)
