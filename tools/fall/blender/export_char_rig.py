"""Export the scarecrow's animation as data for the game's live skinned mesh (index.html, the character section),
instead of rendered frames.

Builds the scene with scarecrow.py (rig, skin weights, every clip keyed), then steps every clip frame by frame and
reads off the evaluated scene:
  - each bone's skinning matrix (pose matrix x inverse rest matrix) as a 2D affine in ART PX (x right, y down, the
    layers' own 1024 x 1536 frame): x' = a x + c y + tx, y' = b x + d y + ty  - exactly what Blender's armature
    modifier applies (linear blend), so the game's CPU skinning reproduces the render;
  - the face shown (index into scarecrow.FACES);
  - every visible effect sprite: kind, the affine taking its picture's unit square (u right, v down) to art px, alpha.
And the skin itself: the bone weights at every point of the GRID-px lattice over the art (top 4 per point) for the
body, and the pole layer's two-bone weights - tools/fall/pack_char_rig.py trims the lattice to the opaque cells.

  blender.exe -b --factory-startup --python tools/fall/blender/export_char_rig.py
-> art/blender/chars/scarecrow/rig/export.json + weights.npz"""
import json, math, os, sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import scarecrow as SC

OUT = os.path.join(SC.OUT, "rig")


def px_affine(M):
    """A 4x4 armature/world-space matrix acting on the XZ plane -> the same map in art px (a, b, c, d, tx, ty)."""
    def f(x, y):
        X, Z = (x - SC.W_PX / 2) / 100.0, (SC.H_PX / 2 - y) / 100.0
        X2 = M[0][0] * X + M[0][2] * Z + M[0][3]
        Z2 = M[2][0] * X + M[2][2] * Z + M[2][3]
        return X2 * 100.0 + SC.W_PX / 2, SC.H_PX / 2 - Z2 * 100.0
    o = f(0, 0)
    ex, ey = f(1, 0), f(0, 1)
    return [ex[0] - o[0], ex[1] - o[1], ey[0] - o[0], ey[1] - o[1], o[0], o[1]]


def quad_affine(ob):
    """An effect plane's picture (u, v in 0..1, v down) -> art px."""
    s = ob["size"]
    Mw = ob.matrix_world

    def f(u, v):
        p = Mw @ __import__("mathutils").Vector((-s / 2 + s * u, 0, s / 2 - s * v))
        return p.x * 100.0 + SC.W_PX / 2, SC.H_PX / 2 - p.z * 100.0
    o = f(0, 0)
    ex, ey = f(1, 0), f(0, 1)
    return [ex[0] - o[0], ex[1] - o[1], ey[0] - o[0], ey[1] - o[1], o[0], o[1]]


def main():
    arm, body, fx = SC.build_all(list(SC.CLIPS))
    sc = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    face_node = body.active_material.node_tree.nodes["face"].outputs[0]
    fx_obs = [ob for ob in bpy.data.objects if "fx" in ob.keys()]
    clips = {}
    for c, (n, loop) in SC.CLIPS.items():
        nf = n if loop else n + 1
        mats, faces, sprites = [], [], []
        for k in range(nf):
            sc.frame_set(SC.STARTS[c] + k)
            row = []
            for name in SC.BONE_NAMES:
                pb = arm.pose.bones[name]
                M = pb.matrix @ pb.bone.matrix_local.inverted()
                row.append([round(v, 5) for v in px_affine(M)])
            mats.append(row)
            faces.append(int(round(face_node.default_value)))
            fr = []
            for ob in fx_obs:
                a = ob.active_material.node_tree.nodes["fade"].outputs[0].default_value
                if a > .003:
                    fr.append([ob["fx"], [round(v, 3) for v in quad_affine(ob)], round(a, 3)])
            sprites.append(fr)
        clips[c] = {"frames": nf, "loop": loop, "mats": mats, "faces": faces, "sprites": sprites}
        print("clip", c, nf)
    # the skin, on the GRID lattice over the whole art
    rd = SC.blender_read
    maps = SC.weight_maps(SC.body_rgba(rd))
    g = SC.GRID
    ys, xs = np.mgrid[0:SC.H_PX + 1:g, 0:SC.W_PX + 1:g].astype(np.float32)
    idx, w = SC.sample(maps, xs.ravel(), ys.ravel())
    pw = SC.pole_weights(xs.ravel(), ys.ravel())
    np.savez_compressed(os.path.join(OUT, "weights.npz"), lattice=np.array([g, xs.shape[1], xs.shape[0]]),
                        body_idx=idx.astype(np.uint8), body_w=w.astype(np.float32),
                        pole_w=np.stack([pw["pole"], pw["ground"]], 1).astype(np.float32))
    bones = {b: {"head": h, "tail": t, "parent": p} for b, (h, t, p) in SC.BONES.items()}
    json.dump({"fps": SC.FPS, "art": [SC.W_PX, SC.H_PX], "ground": [SC.W_PX / 2, SC.GROUND_Y], "top": SC.TOP_Y,
               "bones": SC.BONE_NAMES, "bone_info": bones, "faces": SC.FACES, "clips": clips,
               "fx": {k: {"size": v[0]["size"], "file": k + ".png"} for k, v in fx.items()}},
              open(os.path.join(OUT, "export.json"), "w"))
    print("DONE export_char_rig ->", OUT)


if __name__ == "__main__":
    main()
