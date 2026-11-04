# Animating a fall icon in parts (the pipeline, as built on H1 the Roast Turkey)

Repo: `C:\Users\CooperHinkel\Documents\fallslotsga`. Python: `.venv/Scripts/python.exe` (numpy, scipy, PIL). Blender:
`"/c/Program Files/Blender Foundation/Blender 4.2/blender.exe"` (4.2 LTS, run it in the background with `-b`).
The OpenRouter key is read by `tools/fall/orimg.py` from `%USERPROFILE%\.fallslots\openrouter-key.txt` (never print it).

The owner wants every icon animated in Blender with its own unique motion, the icon split into parts that move
separately and realistically (a drumstick waves on its joint, a cap lifts off an acorn, grapes jiggle one by one).

## The steps for one icon `<ID>` (H1 is the finished example: read its three files first)

1. **Look at it.** The art is `art/fall-src/icons/<ID>.png` (1000 x 1000, the art's longer side 940 px, centred).
   Make a gridded preview to read coordinates, then Read it:
   ```
   .venv/Scripts/python.exe -c "from PIL import Image, ImageDraw; im=Image.open('art/fall-src/icons/<ID>.png').convert('RGBA'); bg=Image.new('RGBA',im.size,(60,60,72,255)); bg.alpha_composite(im); d=ImageDraw.Draw(bg); [d.line([(x,0),(x,1000)],fill=(255,255,255,90)) or d.text((x+3,3),str(x),fill=(255,255,255,255)) for x in range(0,1000,100)]; [d.line([(0,y),(1000,y)],fill=(255,255,255,90)) or d.text((3,y+3),str(y),fill=(255,255,255,255)) for y in range(0,1000,100)]; bg.convert('RGB').save('<scratch>/<ID>_grid.png')"
   ```
2. **Spec** `tools/fall/parts/<ID>.py` (copy the shape of `tools/fall/parts/H1.py`):
   - `PLATES = {name: prompt}`: OpenRouter edits of the icon with things taken away and what was behind painted in
     ("remove X and paint what is behind it; keep everything else exactly the same: position, size, colours, outline,
     sticker border; transparent background"). One plate per depth of things that move off something. Keep it to
     1-3 plates per icon (~$0.06 each). Tell the plate to leave out every small moving part (garnish etc.) so the
     plates never draw their own copy of something a layer also draws.
   - `LAYERS`, back to front, each `dict(name, src, pivot=(x, y) icon px, parent="root" or an earlier layer)`:
     - `src="art"` + `poly`: cut from the icon along its own black outlines (the flat colour areas mostly inside
       the polygon, their ink, the sticker border beside them). Polygon can be generous on the outside (only the
       icon's own pixels count).
     - `src="art", cut="poly"`: the polygon's exact shape, for a part whose colour runs into its neighbour with no
       outline between (a thigh into a body). Cut across where the part is hidden or near its pivot.
     - `src="plate:<name>"`: a whole plate (the back layer, e.g. the empty platter).
     - `src="diff:<a>-<b>"`: where plate a differs from plate b, with the icon's own pixels laid over wherever the
       icon shows that layer (so at rest it is exactly the icon). `keep="warm"` keeps only oranges/browns; or define
       your own `def keep(rgb, sat, val): return <bool array>` in the spec and pass `keep=keep` (rgb 0..1 HxWx3).
   - The pivot is the joint a part turns about (where a leg meets the body, the base of a stem).
3. **Plates** `.venv/Scripts/python.exe tools/fall/cut_parts.py <ID> plates` then LOOK at
   `art/fall-src/parts/<ID>/plate_*.png` (Read them). Regenerate a plate (edit the prompt) if it adds things, moves
   the art, or leaves part of what it should remove.
4. **Cut** `.venv/Scripts/python.exe tools/fall/cut_parts.py <ID> cut` -> `art/blender/parts/<ID>/<layer>.png`,
   `parts.json`, and `check.jpg` (each layer with its pivot ringed, then all of them laid back together, then the
   icon). READ check.jpg every time: each part whole with its own outline, no ghost outlines / slivers of a moving part
   left on the layer under it, and "rest vs icon: mean abs diff" under ~6/255. Iterate on polygons / cut / keep.
5. **Clips** `tools/fall/blender/anims/<ID>.py` (copy the shape of `tools/fall/blender/anims/H1.py`): `FX` = effect
   sprites it uses (from: steam, sparkle, glint, crumb, leaf, bubble, popcorn, puff, drop, straw, feather), and four
   functions `idle(c)`, `land(c)`, `hit(c)`, `multi(c)`. Each calls `c.run(clip, pose)` with
   `pose(i, n) -> {bone: dict(x=, y=, r=deg, sx=, sy=)}` (bones = "root" + the layer names; x/y in units, 100 icon
   px = 1 unit, y up; r counter-clockwise; anything missing = rest), and `c.glow_curve(clip, g)`.
   Effects: `c.pools[kind].particle(f_start, f_end, path(t)->(x, z), c.rng, spin=, grow=(a, b), fade=(a, b))` in
   absolute frames - get a clip's first frame from `import symanim as SA; SA.START[clip]` (idle 1, land 101,
   hit 201, multi 301); `c.pools["ring"]`, `c.pools["rays"]` exist too. Helpers: `c.damp(t, freq, zeta)` (a spring
   settling 1 -> 0), `c.ease_out`, `c.ease_in_out`.
   Rules (the owner's): 30 fps; idle 72 frames, a seamless loop that starts at rest (use whole cycles of sines with
   no phase, so frame 0 and 72 are rest); land 24, hit 46, multi 42 frames, each starting and ending exactly at rest
   (c.run forces the first and last frame to rest - make the motion arrive there smoothly, no jump on the last
   frame); idle is calm (every symbol on the board plays it at once); land = it drops onto the reel (impact,
   squash, parts lag and spring back); hit = it's in a winning cluster (the big, characterful one); multi = a
   multiplier powers it (charge up trembling/swelling, then release). Squash and stretch, anticipation,
   follow-through, overlap; parts move separately and believably about their joints; NOTHING may leave the
   13-unit frame (the icon is 10 units: keep motion within about +-1.5 units and big rotations small for parts
   near the edge). Make each icon's motion its own - its personality, not a copy of the turkey's.
6. **Render** in a background Blender (never the user's open Blender):
   `"/c/Program Files/Blender Foundation/Blender 4.2/blender.exe" -b --factory-startup --python tools/fall/blender/partsanim.py -- <ID> build,render > art/blender/renders/<ID>.log 2>&1`
   (~1-2 min). Then check `grep -E "DONE|Traceback" -A3 art/blender/renders/<ID>.log`, and make a contact sheet of
   every 3rd frame of each clip from `art/blender/renders/<ID>/<clip>/*.png` (512 px RGBA, composite on a dark
   background) and READ it. Fix and re-render until: parts stay attached where they should, no holes or ghosts
   appear where a part moves off, nothing is clipped at the frame edge, clips start/end at rest, the motion reads.

7. **Ship it to the game** (the lead does this, after all renders): the board draws icons LIVE from rig data since
   2026-11-04, not from the frame sheets. `blender.exe -b --factory-startup --python tools/fall/blender/export_rig.py -- <ID>[,<ID>..]`
   (-> art/blender/rigs/<ID>/rig.json), then `.venv/Scripts/python.exe tools/fall/pack_rigs.py` (packs ALL exported rigs ->
   frontend/assets/rig/), and `pack_rigs.py check <ID> <clip> <frame> out.png` to compare against the Blender render.
   pack_frames.py still makes the sheets the game falls back to (?sheets).

## Don'ts
- Do NOT edit the shared tools (`tools/fall/cut_parts.py`, `tools/fall/blender/partsanim.py`,
  `tools/fall/blender/symanim.py`, `tools/blender/pack_frames.py`) or anything under `frontend/`. Other agents are
  using them at the same time. If the pipeline can't do something, work around it in your own spec/anim file
  (a custom `keep` function, more layers, a different plate) or say so in your report.
- Do NOT run `tools/blender/pack_frames.py` (the lead packs everything at the end - packs at once clobber the
  manifest). Do NOT use the Blender MCP tools (that is the user's live Blender). Do NOT commit.
- Put scratch images in the session scratchpad, not in the repo.
