"""The Multi bottle's art (art/fall-src/champagne/): the corked cider bottle, the same bottle uncorked (made from the
first with an edit, so the two line up), both again EMPTY (the cider is painted in by Blender, so it can slosh), the
spray sprites, their extra drawings (the spray cycles through them, so it boils), a foam puff and the cork.
usage: python tools/fall/gen_champagne.py corked | open | empty | hands | fx | fx2 [name]   (OpenRouter, ~$0.06 each)
The key is read by orimg (%USERPROFILE%\\.fallslots\\openrouter-key.txt) and never printed."""
import os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orimg
from gen_ui import STYLE

ROOT = orimg.ROOT
OUT = os.path.join(ROOT, "art", "fall-src", "champagne")
REF = os.path.join(ROOT, "art", "fall-src", "M_v1.png")           # the cider bottle the game has had so far
BASE = open(os.path.join(ROOT, "art", "fall-src", "prompts", "icon_base.txt"), encoding="utf-8").read().strip()

# (owner, 2026-11-03: no metal on the cork, and the label says XXX) - made as an edit of the apple-label bottle
# (champagne/apple_label/corked.png), which was made from REF with the first version of this prompt
CORKED = ("Edit the attached picture: keep the bottle the same - same position, same size, same tilt, same green glass, "
          "same outline and sticker border, same golden cider and bubbles inside. But: (1) REMOVE the gold foil, the wire "
          "cage and the round red medallion from the neck - the neck is now plain green glass right up to the mouth, with "
          "a bare natural cork pushed into the mouth and its rounded top sticking out; (2) REPLACE the apple label with a "
          "plain cream paper label that says \"XXX\" in big, bold, chunky black hand-painted moonshine letters - no apple "
          "anywhere. Nothing else changes. Transparent background.")
OPEN = ("Edit the attached picture: keep EVERYTHING exactly the same - same bottle, same position, same size, same tilt, "
        "same colours, same XXX label, same sticker border - but remove the cork: the neck mouth is now open and empty "
        "with a small frothy golden foam head just rising out of it. Nothing else changes. Transparent background.")
EMPTY = ("Edit the attached picture: keep EVERYTHING exactly the same - same bottle, same position, same size, same tilt, "
         "same outline, same XXX label, same sticker border - but the bottle is now EMPTY: plain clear dark green "
         "glass all the way through with its glassy highlights, NO golden cider inside, NO bubbles, NO liquid at all{x}. "
         "Nothing else changes. Transparent background.")
HANDS = ("Edit the attached picture: keep the bottle EXACTLY the same - same position, same size, same tilt, same "
         "colours, same outline, same XXX label. ADD two cartoon hands in thick tan-brown leather farm work gloves holding "
         "the bottle: one gloved hand wrapped around the NECK, its fingers curled over the front of the neck; the other "
         "gloved hand gripping the BOTTOM of the bottle, its fingers over the front of the glass near the base. Floating "
         "cartoon hands with short glove cuffs and NO arms. Same Rick and Morty cartoon style, thick black outline, flat "
         "cel colours, and the same cream die-cut sticker border around the whole thing. Transparent background.")
FX = {
    "fizz_burst": ("A cartoon burst of golden champagne spray seen from the side: a fan of foamy cider shooting upward and "
                   "outward from one point at the bottom centre, fat splashy tongues, many round droplets and bubbles of "
                   "different sizes, cream foam highlights, thick dark outline. Centred, transparent background, no bottle.", "1:1"),
    "fizz_jet": ("A tall cartoon fountain of golden champagne shooting straight up: a thick foamy column widening at the top "
                 "into splashy tongues with droplets and bubbles flying off, cream foam highlights, thick dark outline. "
                 "Centred, vertical, transparent background, no bottle.", "1:1"),
    "cork": ("ONLY a single bare champagne cork floating by itself in mid-air and tilted, NO bottle, NO splash, NO "
             "liquid, NO foil, NO wire: a fat mushroom-shaped natural cork with speckled tan grain and a rounded top, a "
             "thick cream die-cut sticker border around it. Centred, transparent background, nothing else.", "1:1"),
}
# second and third drawings of the sprays (the same thing, the tongues and droplets in other places), and the foam
# that bubbles out round the cork as it fizzes up: name -> (prompt, aspect, style reference)
VARIANT = ("Another drawing of the SAME thing as the attached picture, in exactly the same style, colours, size and "
           "framing, but with the splashy tongues, droplets and bubbles in different places, as the next frame of a "
           "cartoon animation. Transparent background.")
FX2 = {
    "fizz_jet_b": (VARIANT, "1:1", "fizz_jet"), "fizz_jet_c": (VARIANT, "1:1", "fizz_jet"),
    "fizz_burst_b": (VARIANT, "1:1", "fizz_burst"),
    "foam_puff": ("A small round blob of frothy cream-and-gold champagne foam, many little bubbles in it, a few bubbles "
                  "popping off its edge, thick dark outline, in the same style as the attached picture. Centred, "
                  "transparent background, nothing else.", "1:1", "fizz_burst"),
}


def go(kind, only=None):
    os.makedirs(OUT, exist_ok=True)
    src = lambda n: os.path.join(OUT, n + ".png")
    if kind == "corked":
        return orimg.generate(src("corked"), CORKED, aspect="1:1", refs=[os.path.join(OUT, "apple_label", "corked.png")])
    if kind == "hands":
        return orimg.generate(src("corked_hands"), HANDS, aspect="1:1", refs=[src("corked_empty")])
    if kind == "open":
        return orimg.generate(src("open"), OPEN, aspect="1:1", refs=[src("corked")])
    if kind == "empty":
        jobs = [("corked_empty", EMPTY.format(x=""), "corked"),
                ("open_empty", EMPTY.format(x=", and NO foam at the neck: the open mouth is empty"), "open")]
    elif kind == "fx2":
        jobs = [(n, p + "\n\n" + STYLE, ref) for n, (p, a, ref) in FX2.items()]
    else:
        jobs = [(n, p + "\n\n" + STYLE, None) for n, (p, a) in FX.items()]
    jobs = [j for j in jobs if not only or j[0] == only]
    with ThreadPoolExecutor(4) as ex:
        return list(ex.map(lambda j: (j[0], orimg.generate(src(j[0]), j[1], aspect="1:1",
                                                           refs=[src(j[2])] if j[2] else [])[1]), jobs))


if __name__ == "__main__":
    print(sys.argv[1], go(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
