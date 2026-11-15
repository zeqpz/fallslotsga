"""The scarecrow, re-drawn as SEPARATE cut-out parts (round 3 rebuild, 2026-11-15).

He was one painted picture bent as a skinned mesh; now every body part is its own picture with its own pivot
(tools/fall/scare_rig.py animates them, tools/fall/pack_scare_rig.py packs them for the game). This script asks the
image model (tools/fall/orimg.py, OpenRouter) for each part: the current figure is the design + style reference, a
close-up of the part's region is the placement reference, and the prompt asks for that ONE part alone, complete
where its neighbours used to cover it, on a transparent background.

  .venv/Scripts/python.exe -I tools/fall/gen_scare_parts.py refs                # the reference pictures
  .venv/Scripts/python.exe -I tools/fall/gen_scare_parts.py gen [name,name|all] [--redo]   # the raw parts
-> art/fall-src/scare_parts/ref/*.png, raw/<name>.png (an older take is kept as raw/old/<name>_<n>.png),
   log.jsonl (time, part, prompt, refs, cost). tools/fall/cut_scare_parts.py turns the raw takes into clean parts."""
import json, os, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
LAY = os.path.join(ROOT, "art", "blender", "chars", "scarecrow", "layers")     # the repaired round-2 layers
OUT = os.path.join(ROOT, "art", "fall-src", "scare_parts")
REF, RAW = os.path.join(OUT, "ref"), os.path.join(OUT, "raw")
LOG = os.path.join(OUT, "log.jsonl")

# close-ups of the old figure (art px boxes x0, y0, x1, y1 in its 1024 x 1536 frame) and the aspect asked for
REGIONS = {
    "head": ((200, 60, 712, 572), "1:1"),
    "torso": ((350, 410, 770, 830), "1:1"),
    "legs": ((340, 720, 740, 1320), "2:3"),
    "boots": ((330, 1120, 710, 1500), "1:1"),
    "arm_l": ((0, 330, 480, 650), "3:2"),
    "arm_r": ((544, 340, 1024, 660), "3:2"),
    "jug": ((0, 440, 300, 890), "2:3"),
    "crow": ((730, 160, 1010, 440), "1:1"),
}

STYLE = ("Cartoon game art in EXACTLY the drawing style, colours, line weight and character design of the reference "
         "pictures: bold flat cel colours, a thick dark brown-black ink outline of even weight round every shape, "
         "simple two-tone cel shading, warm autumn palette. Fully transparent background. Crisp, clean, hard outline "
         "edges. NO drop shadow, NO cast shadow, NO glow, NO halo, NO white sticker border, NO ground, NO text, "
         "nothing else in the picture.")
HEAD = ("Reference 1 is the whole character: a drunk cartoon scarecrow tied to a wooden T-shaped pole. Reference 2 "
        "is a close-up of one region of him. I am rebuilding him as a 2D cut-out puppet made of separate pieces. ")
SAME = (" Draw it at the same size, the same angle and in the same place on the canvas as it is in reference 2, "
        "with everything else in reference 2 removed (transparent). ")

# name -> (region, what to draw)
PARTS = {
    "head_base": ("head", "Draw ONLY his bare burlap-sack HEAD as one separate piece: the lumpy sack shape, its burlap "
                  "colour, weave wrinkles and soft cel shading, his round red nose and the two rosy cheek blushes - and "
                  "NOTHING else on the face: NO eyes, NO eyelids, NO eyebrows, NO mouth, NO teeth, NO stitches (plain "
                  "blank burlap where they were). NO hat, NO straw hair, NO straw collar, no wood. The top of the head "
                  "that the hat covered is drawn COMPLETE as the rounded top of the sack, and the bottom ends in a short "
                  "gathered burlap neck."),
    "hat": ("head", "Draw ONLY his HAT as one separate piece: the brown patched pointed felt hat with its bent drooping "
            "tip, the red band, the olive-green patch and the wide floppy ragged brim. NO straw at all (remove the "
            "straw tuft that pokes out of the hat and the hair), NO head, no wood. The underside / lower edge of the "
            "brim that the head and the hair covered is drawn COMPLETE, as a full brim all the way round the front."),
    "hair": ("head", "Draw ONLY the tufts of yellow STRAW HAIR that stick out from under his hat (the big tuft on the "
             "left side, the fringe over his forehead, the wisps by his cheek) and the little tuft poking out of the "
             "top of the hat - straw only, as separate loose tufts, each one drawn COMPLETE down to a gathered root "
             "where the hat or head used to hide it. NO hat, NO head, NO face, no wood."),
    "collar": ("torso", "Draw ONLY the ruff of yellow STRAW that bursts out of his shirt collar round his neck, as one "
               "separate piece: a full bib-shaped fan of straw, drawn COMPLETE at the top where the head covered it "
               "(the strands gathered to a neck-sized root). NO head, NO shirt, NO overalls, no wood."),
    "torso": ("torso", "Draw ONLY his TORSO as one separate piece: the body of the red-and-orange plaid shirt with its "
              "olive patches and buttons, and over it the bib of the blue denim overalls with its straps (one strap "
              "buttoned, the other undone with the bib's corner folded down). NO sleeves or arms: the shirt ends at "
              "each shoulder in a smooth rounded shoulder cap. NO head, NO neck straw (the collar and shoulders of the "
              "shirt drawn COMPLETE where the straw and head covered them), NO rope belt, NO legs, no wooden pole or "
              "crossbar. At the bottom the shirt and the denim bib simply continue straight down a little past the "
              "waist and end in a plain flat edge."),
    "hips": ("legs", "Draw ONLY the SEAT of his blue denim overalls with the rope belt, as one separate piece shaped "
             "like a pair of very short plain denim shorts seen from the front: from the knotted tan rope belt at the "
             "waist (drawn complete all the way across, the knot at the same place as in reference 2) down to just "
             "below the crotch, with the fly seam and pocket stitching. Each of the two short leg stubs ends in a "
             "CLOSED, slightly rounded flat hem edge with its ink outline - you must NOT see into the leg openings, no "
             "dark holes - and there is a clear notch between the two stubs. Plain denim only: NO patches, NO "
             "lightning-bolt marks, NO long legs, NO dangling rope ends (just the belt and its knot), NO shirt, NO "
             "straw, no wooden pole."),
    "leg_l": ("legs", "Draw ONLY the trouser LEG on the viewer's LEFT (the one with the big red square patch), as one "
              "separate piece: a single loose tube of blue denim hanging straight, with its patch, stitches and "
              "frayed ragged hem at the bottom. Its top is drawn COMPLETE and extended up to the belt as a rounded "
              "end, and the side that the other leg overlapped is drawn complete with its own outline. NO straw, NO "
              "boot, NO other leg, NO belt or seat of the overalls, no wooden pole."),
    "leg_r": ("legs", "Draw ONLY the trouser LEG on the viewer's RIGHT (the one with the tan square patch near the "
              "knee), as one separate piece: a single loose tube of blue denim hanging straight, with its patch, "
              "stitches and frayed ragged hem at the bottom. Its top is drawn COMPLETE and extended up to the belt as "
              "a rounded end, and the side that the other leg overlapped is drawn complete with its own outline. NO "
              "straw, NO boot, NO other leg, NO belt or seat of the overalls, NO rope ends, no wooden pole."),
    "cuffs": ("legs", "Draw ONLY the two bunches of yellow STRAW that stick out of the bottoms of his trouser legs, as "
              "two separate tufts side by side with a clear gap between them, each drawn COMPLETE at the top where "
              "the denim hem covered it (strands gathered to a root as wide as the trouser leg). Straw only: NO "
              "denim, NO boots, no wooden pole."),
    "boots": ("boots", "Draw ONLY his two brown leather BOOTS as two separate pieces with a clear gap between them: "
              "each boot complete with its rope tie round the ankle and the little tuft of straw sticking out of its "
              "top, the top of each boot drawn COMPLETE where the trouser leg and straw covered it. NO trouser legs, "
              "NO wooden post between them, NO grass, NO ground shadow."),
    # (2026-11-15, owner: "shorts over stilts" - the hips and both legs are now cut from ONE pair of trousers, so the
    # widths and the denim match at the hip joints; and plain boots, no straw: tools/fall/cut_scare_parts.py)
    "trousers": ("legs", "Draw ONLY the lower half of his blue denim overalls as ONE separate piece: one complete pair of "
                 "full-length loose denim TROUSERS seen from the front, from the knotted tan rope belt at the waist "
                 "(drawn complete all the way across, with its knot, NO dangling rope ends) down to the two frayed "
                 "ragged hems at the ankles. The seat and both legs are one continuous garment with NO hem, cuff, "
                 "seam or outline between the seat and the legs. The two legs hang straight down, parallel and the "
                 "same width (each as wide as half the seat), with a narrow clear gap between them from the crotch "
                 "down to the hems. Keep the big red square patch and little lightning-bolt marks on the viewer's "
                 "left leg, the tan square patch near the knee on the right leg, the fly seam and pocket stitching. "
                 "NO straw, NO boots, NO shirt, NO bib, no wooden pole."),
    "boots_plain": ("boots", "Draw ONLY his two brown leather BOOTS as two separate pieces with a wide clear gap between "
                    "them: plain worn work boots, each drawn complete with a tall straight shaft that is open at the "
                    "top (a plain round rim), toes pointing a little outward. Plain leather only: NO straw anywhere, NO "
                    "rope tie, NO laces sticking out, NO trouser legs, NO wooden post between them, NO grass, NO ground "
                    "shadow."),
    "sleeve_l": ("arm_l", "Draw ONLY the shirt SLEEVE of the arm on the viewer's LEFT, as one separate piece: a tube of "
                 "red-and-orange plaid cloth with its olive elbow patch and ragged cuff, stretched out sideways. The "
                 "shoulder end (right side of the picture) is drawn COMPLETE and rounded where the body covered it. NO "
                 "straw at all, NO rope, NO hand, NO jug, NO head or hat, NO body, no wooden crossbar."),
    "sleeve_r": ("arm_r", "Draw ONLY the shirt SLEEVE of the arm on the viewer's RIGHT, as one separate piece: a tube "
                 "of red-and-orange plaid cloth with its olive patch and ragged cuff, stretched out sideways. The "
                 "shoulder end (left side of the picture) is drawn COMPLETE and rounded where the body covered it. NO "
                 "straw at all, NO rope, NO hand, NO crow, NO head, NO body, no wooden crossbar."),
    "hand_l": ("arm_l", "Draw ONLY his STRAW HAND on the viewer's LEFT: the big bunch of long yellow straw fingers "
               "that droops from the end of the sleeve, and next to it (kept apart, with a clear gap) the smaller "
               "frill of straw that sticks out of the sleeve's cuff. Each is one separate tuft drawn COMPLETE, its "
               "root gathered to a narrow bunch where the rope tied it. Straw only: NO rope, NO sleeve, NO jug, no "
               "wooden crossbar."),
    "hand_r": ("arm_r", "Draw ONLY his STRAW HAND on the viewer's RIGHT: the big bunch of long yellow straw fingers "
               "that droops from the end of the sleeve, and next to it (kept apart, with a clear gap) the smaller "
               "frill of straw that sticks out of the sleeve's cuff. Each is one separate tuft drawn COMPLETE, its "
               "root gathered to a narrow bunch where the rope tied it. Straw only: NO rope, NO sleeve, NO crow, no "
               "wooden crossbar."),
    "ropes": ("arm_l", "Draw ONLY ROPE pieces, in the same tan twisted-rope drawing as the rope round his wrist, as "
              "FIVE separate pieces laid out in a row with clear gaps, none touching: (1) and (2) two short coils of "
              "three turns of rope, as wrapped round a wrist, seen from the front; (3) one straight vertical length "
              "of rope about as long as the picture is tall, ending at the bottom in a small tied loop; (4) and (5) "
              "two short loose dangling rope ends with frayed tips, each hanging from a small knot. Rope only: NO "
              "straw, NO sleeve, NO jug, NO wood. Ignore the 'same place' instruction for this sheet."),
    "jug": ("jug", "Draw ONLY his brown moonshine JUG as one separate piece: the stoneware jug with the tan XXX label "
            "band, the little handle ring, the cork, and the ring of rope tied round its neck. The rope that it "
            "hangs from is cut off just above the neck. NO straw, NO sleeve, NO hand, no wood."),
    "crow": ("crow", "Draw ONLY the black CROW as one separate piece, wings folded, with its cream eye, grey beak and "
             "both grey feet with their claws drawn COMPLETE (gripping nothing). NO wooden crossbar, NO rope, NO "
             "straw."),
    "crow_wing": ("crow", "Draw ONLY ONE spread WING of this black crow, as a separate piece on its own: the wing "
                  "opened out wide for flapping, the shoulder end at the lower right of the picture and the long "
                  "flight feathers fanned out to the upper left, in the crow's own purple-black colours with the same "
                  "ink outline and feather lines. NO crow body, NO head, nothing else. Ignore the 'same place' "
                  "instruction: make the wing fill most of the picture."),
    "mouths_a": ("head", "Draw a SHEET OF FOUR separate MOUTHS for this scarecrow, each one on its own, laid out in a "
                 "tidy 2 by 2 grid with wide gaps between them, each mouth BIG - about a third of the picture's width - "
                 "and drawn exactly like his mouth in reference 2 (dark outline, dark red-brown inside, cream square "
                 "gappy teeth, pink tongue, the little black cross-stitches at both corners). Mouths ONLY - no face, no "
                 "head, no nose, no burlap behind them. Top left: the big open goofy GRIN of reference 2. Top right: a "
                 "closed lazy drunk SMILE - one wobbly curved ink line with a cross-stitch at each corner. Bottom left: "
                 "a wide-open CHEERING yell - a big tall open mouth, upper teeth, tongue out. Bottom right: a small "
                 "round surprised 'O' with a stitch each side. Ignore the 'same place' instruction for this sheet."),
    "mouths_b": ("head", "Draw a SHEET OF FOUR separate MOUTHS for this scarecrow, each one on its own, laid out in a "
                 "tidy 2 by 2 grid with wide gaps between them, each mouth BIG - about a third of the picture's width - "
                 "and drawn in exactly the style of his mouth in reference 2 (dark outline, dark red-brown inside, "
                 "cream square gappy teeth, pink tongue, the little black cross-stitches at both corners). Mouths ONLY - "
                 "no face, no head, no nose, no burlap behind them. Top left: a HICCUP - small puckered lips pushed "
                 "out, a little open. Top right: a SAD wobbly frown - one wavy ink line with the corners turned down, a "
                 "cross-stitch at each corner. Bottom left: a SMUG closed smirk - one ink line pulled up high on the "
                 "right side, a stitch at each corner. Bottom right: a sleepy slack half-open drunk mouth, one tooth "
                 "showing, with a pale blue drop of drool hanging from its lower corner. Ignore the 'same place' "
                 "instruction for this sheet."),
}


def composed():
    full = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
    for n in ("pole", "body_happy", "crow"):
        full.alpha_composite(Image.open(os.path.join(LAY, n + ".png")).convert("RGBA"))
    return full


def refs():
    os.makedirs(REF, exist_ok=True)
    full = composed()
    full.save(os.path.join(REF, "full_rgba.png"))
    white = Image.new("RGBA", full.size, (255, 255, 255, 255))
    white.alpha_composite(full)
    white.convert("RGB").save(os.path.join(REF, "full.png"))
    for name, (box, aspect) in REGIONS.items():
        w, h = box[2] - box[0], box[3] - box[1]
        k = 1024 / min(w, h)
        im = white.crop(box).resize((round(w * k), round(h * k)), Image.LANCZOS).convert("RGB")
        im.save(os.path.join(REF, name + ".png"))
        print("ref", name, box, im.size)


def prompt_of(name):
    region, what = PARTS[name]
    return HEAD + what + SAME + STYLE


def one(name):
    import orimg
    region, _ = PARTS[name]
    out = os.path.join(RAW, name + ".png")
    if os.path.exists(out):                                   # keep the older take
        os.makedirs(os.path.join(RAW, "old"), exist_ok=True)
        n = 1
        while os.path.exists(os.path.join(RAW, "old", f"{name}_{n}.png")):
            n += 1
        shutil.move(out, os.path.join(RAW, "old", f"{name}_{n}.png"))
    p = prompt_of(name)
    rf = [os.path.join(REF, "full.png"), os.path.join(REF, region + ".png")]
    try:
        _, cost = orimg.generate(out, p, aspect=REGIONS[region][1], refs=rf)
    except RuntimeError as e:
        return f"FAIL {name} {e}"
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "part": name, "region": region,
                             "aspect": REGIONS[region][1], "refs": [os.path.relpath(r, ROOT) for r in rf],
                             "prompt": p, "cost": cost}) + "\n")
    return f"OK {name} {cost}"


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "refs"
    if step == "refs":
        refs()
    elif step == "gen":
        names = list(PARTS) if len(sys.argv) < 3 or sys.argv[2] == "all" else sys.argv[2].split(",")
        if "--redo" not in sys.argv:
            names = [n for n in names if not os.path.exists(os.path.join(RAW, n + ".png"))]
        os.makedirs(RAW, exist_ok=True)
        with ThreadPoolExecutor(6) as ex:
            for r in ex.map(one, names):
                print(r, flush=True)
