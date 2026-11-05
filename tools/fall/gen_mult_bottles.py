"""The Multi's bottle once per multiplier value (owner, 2026-11-04: "make the bottle say the multiplier on it"):
OpenRouter edits of the bottle art (art/fall-src/icons/M.png, the XXX label) with the label reading the value.
-> art/fall-src/champagne/mult/M_x<value>.png   (wiring into the game's big bottle comes after)
usage: .venv/Scripts/python.exe tools/fall/gen_mult_bottles.py [value,value..]"""
import os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orimg

ROOT = orimg.ROOT
SRC = os.path.join(ROOT, "art", "fall-src", "icons", "M.png")
OUT = os.path.join(ROOT, "art", "fall-src", "champagne", "mult")
VALUES = ["1.25", "1.5", "2", "3", "5", "10", "20", "50", "100", "250", "500", "1000", "2500"]


def prompt(v):
    return (f'Edit this game icon: keep the green cider bottle EXACTLY the same - same shape, size, position, colours, '
            f'outline, cork, glass highlights, sticker border and transparent background. Change ONLY the text on its '
            f'front label: replace "XXX" with the multiplier "x{v}" in big chunky bold cartoon numerals (harvest gold '
            f'filled, thick dark brown outline, a cream highlight), centred on the label and filling it, perfectly '
            f'legible. Nothing else changes.')


def one(v):
    out = os.path.join(OUT, f"M_x{v}.png")
    if os.path.exists(out):
        return f"skip {v}"
    try:
        _, cost = orimg.generate(out, prompt(v), refs=[SRC])
        return f"OK x{v} {cost}"
    except RuntimeError as e:
        return f"FAIL x{v} {e}"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    vals = sys.argv[1].split(",") if len(sys.argv) > 1 else VALUES
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(one, vals):
            print(r, flush=True)
