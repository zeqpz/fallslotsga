"""Face reactions for the scarecrow: the head crop (art/fall-src/head_crop.png) redrawn with a new expression,
everything else identical. -> art/fall-src/faces/<name>.png"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orimg

FACES = {
    "blink": "both eyes fully CLOSED in a lazy drunk blink (curved closed eyelid lines), the same loose drunk smile",
    "hiccup": "a drunk HICCUP: eyes squeezed shut, cheeks puffed out, lips pressed and bulging, a little bubble at the mouth",
    "happy": "a big goofy HAPPY grin showing crooked teeth, eyes open and happy but still a bit cross-eyed and bloodshot",
    "cheer": "ecstatic CHEERING: mouth wide open yelling with tongue out, eyes huge and wide open with tiny pupils, eyebrows up, happy tears",
    "shock": "SHOCKED and excited: eyes popped wide open and bulging, tiny pupils, mouth a small round O, eyebrows raised high",
    "sad": "SAD and grumpy drunk: droopy half-closed eyes looking down, mouth a wobbly frown, one tear",
    "smug": "a smug sly drunk smirk to one side, one eyebrow raised, one eye half closed in a wink",
}
SRC = os.path.join(orimg.ROOT, "art", "fall-src", "head_crop.png")


def one(name):
    out = os.path.join(orimg.ROOT, "art", "fall-src", "faces", name + ".png")
    p = (f"Redraw the attached image EXACTLY - same cartoon scarecrow head, same burlap face shape, same hat, same "
         f"straw, same outlines, same colours, same framing, same position and size on the canvas, transparent "
         f"background - changing ONLY the facial expression (eyes, eyebrows, mouth, cheeks) to: {orimg_face(name)}. "
         f"Keep the red round nose and rosy cheeks. Rick and Morty cartoon style, flat cel shading.")
    try:
        _, c = orimg.generate(out, p, refs=[SRC])
        return f"OK {name} {c}"
    except RuntimeError as e:
        return f"FAIL {name} {e}"


def orimg_face(n):
    return FACES[n]


if __name__ == "__main__":
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(FACES)
    with ThreadPoolExecutor(7) as ex:
        for r in ex.map(one, names):
            print(r, flush=True)
