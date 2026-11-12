"""What every icon breaks into when it pops (owner, 2026-11-12: "like fruit ninja" - fruit chunks and juice, the hat's
cotton and feathers, the leaf crumbling into leaves, the jug into glass): one generated sheet of loose pieces per
icon, drawn after the icon's own art, plus a sheet of white juice splats the game tints.
  python tools/fall/gen_debris.py [name ...]      -> art/fall-src/debris/<name>.png
  python tools/fall/pack_debris.py                -> frontend/assets/fx/debris.webp + the table for index.html"""
import os, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import orimg

ROOT = orimg.ROOT
OUT = os.path.join(ROOT, "art", "fall-src", "debris")
STYLE = ("Game effect sprite sheet for a cartoon harvest-festival slot game. Bold flat-colour cartoon drawing with a "
         "thick dark brown-black ink outline and simple cel shading, in exactly the drawing style and colours of the "
         "reference picture. Fully transparent background. {n} separate loose pieces laid out in a tidy grid with wide "
         "gaps, none touching or overlapping, each piece about the same size. No white sticker border, no text, no "
         "ground shadows, no frame. The pieces: ")
SHEETS = {
    "apple": ("L3", 8, "chunks of a smashed green apple - wedges and irregular broken chunks with the shiny green skin "
              "on one side and wet juicy cream-white flesh, one chunk with the brown stem and leaf, one with dark seeds."),
    "grapes": ("L4", 8, "burst purple grapes - single grapes split open and halved showing wet lighter violet flesh, "
               "torn grape skins, two whole glossy grapes, one bit of brown stem with a small green leaf."),
    "pumpkin": ("H7", 8, "broken chunks of a smashed orange pumpkin - thick curved rind pieces with ribbed orange skin "
                "and a paler stringy inside with cream seeds stuck on, one chunk with the curly brown stem."),
    "pie": ("H2", 8, "a pumpkin pie smashed apart - golden crust shards with the crimped edge, wedges and blobs of "
            "orange pumpkin filling, two dollops of whipped cream."),
    "turkey": ("H1", 8, "a roast turkey torn apart - a drumstick with its white paper frill, a wing, torn chunks of "
               "golden-brown meat with crisp skin, two red cranberries, a green herb sprig."),
    "horn": ("H3", 8, "a wicker horn of plenty burst apart - four broken curved pieces of woven tan wicker basket, "
             "a tiny whole red apple, a tiny orange pumpkin, a small corn cob, an orange autumn leaf."),
    "corn": ("H6", 8, "a corn cob blown apart - two broken cob chunks studded with yellow kernels, two little clusters "
             "of loose kernels, three fluffy white-and-butter-yellow popcorn pieces, one torn green husk leaf."),
    "hat": ("H4", 10, "what flies out of a burst pilgrim hat - five fluffy white cotton stuffing tufts of different "
            "shapes, four feathers (two charcoal black, one white, one golden brown), one torn scrap of black felt."),
    "leaf": ("L1", 10, "a maple leaf crumbled to bits - small torn fragments of autumn maple leaf and tiny whole "
             "maple leaves, in red, orange and golden yellow."),
    "jug": ("H5", 10, "a cider jug shattered - seven sharp angular shards of broken amber-brown bottle glass, "
            "translucent with bright white glints, two cream stoneware shards (one with a stitched black X on it), "
            "and the cork."),
    "splat": (None, 6, None),
}
SPLAT = ("Game effect sprite sheet. Fully transparent background. 6 different juice splatter marks as left on a wall in "
         "a fruit-slicing arcade game, laid out in a 3 by 2 grid with wide gaps, none touching. Each is one big wet "
         "splat blob with radiating spikes, a few runs and small satellite droplets close around it. Flat cartoon look: "
         "pure white fill, a few very light grey patches for wet shading, NO outline, no colour, no text, no shadows.")


def one(name):
    ref, n, what = SHEETS[name]
    out = os.path.join(OUT, name + ".png")
    prompt = SPLAT if what is None else STYLE.format(n=n) + what
    refs = [os.path.join(ROOT, "frontend", "assets", "flat", ref + ".webp")] if ref else []
    try:
        _, cost = orimg.generate(out, prompt, "1:1", True, refs)
        return f"OK {name} cost {cost}"
    except RuntimeError as e:
        return f"FAIL {name} {e}"


if __name__ == "__main__":
    names = sys.argv[1:] or list(SHEETS)
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, names):
            print(r, flush=True)
