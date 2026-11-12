"""Every icon its own pop (owner, 2026-11-12), built offline from the game's own fall foley: the icon's material (its
landing foley take, sharpened) layered with a burst that suits it (popcorn pop, pumpkin squelch, cork, bubbles,
glint), so no two icons break apart with the same sound. Two takes each -> frontend/assets/sfx_pop_<id>_<1|2>.wav
and their names appended to %TEMP%/fall_sfx/icon_pops.txt for encode_opus.py.

(fall_spec.py also carries Seed Audio prompts for these, "pop_<id>": `fall.py all pop_h1 ...` replaces these files
with recorded takes when an OpenRouter key is available.)

  python tools/sfx/icon_pops.py
  python tools/sfx/encode_opus.py %TEMP%/fall_sfx/icon_pops.txt"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from audiolib import read_wav, write_wav, lufs

ASSETS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "frontend", "assets")
SR = 44100
TARGET = -20.0          # momentary-max LUFS, the popcorn pop's
# id -> take -> layers (file stem, gain, pitch, delay s)
R = {
    "h1": [[("land_platter_1", 1.0, 1.15, 0), ("pop", .6, .8, .01)], [("land_platter_2", 1.0, 1.1, 0), ("pop", .6, .85, .01)]],
    "h2": [[("land_pie_1", 1.0, 1.0, 0), ("paint_burst_1", .7, 1.25, 0)], [("land_pie_2", 1.0, 1.05, 0), ("paint_burst_2", .7, 1.3, 0)]],
    "h3": [[("land_wicker_1", 1.0, 1.1, 0), ("land_wicker_2", .7, 1.35, .05), ("pop", .5, .7, 0)],
           [("land_wicker_3", 1.0, 1.1, 0), ("land_wicker_1", .7, 1.4, .05), ("pop", .5, .72, 0)]],
    "h4": [[("land_hat_1", .9, 1.1, 0), ("glint_1", .8, 1.2, 0), ("pop", .5, 1.5, 0)],
           [("land_hat_2", .9, 1.1, 0), ("glint_2", .8, 1.3, 0), ("pop", .5, 1.55, 0)]],
    "h5": [[("land_jug_1", 1.0, 1.25, 0), ("cap_pop_1", .8, .9, 0)], [("land_jug_2", 1.0, 1.2, 0), ("cap_pop_2", .8, .92, 0)]],
    "h6": [[("pop", .9, 1.0, 0), ("pop", .8, 1.25, .045), ("pop", .7, 1.5, .09), ("land_corn_1", .6, 1.1, 0)],
           [("pop", .9, 1.05, 0), ("pop", .8, 1.4, .05), ("pop", .7, 1.2, .1), ("land_corn_2", .6, 1.1, 0)]],
    "h7": [[("land_pumpkin_1", 1.0, .85, 0), ("paint_burst_1", .9, .8, .01)], [("land_pumpkin_2", 1.0, .85, 0), ("paint_burst_2", .9, .82, .01)]],
    "l1": [[("land_leaf_1", 1.0, 1.2, 0), ("land_leaf_2", .7, 1.5, .03), ("pop", .3, 1.8, 0)],
           [("land_leaf_3", 1.0, 1.2, 0), ("land_leaf_1", .7, 1.55, .03), ("pop", .3, 1.9, 0)]],
    "l3": [[("land_apple_1", 1.0, 1.2, 0), ("pop", .6, 1.25, 0)], [("land_apple_2", 1.0, 1.25, 0), ("pop", .6, 1.3, 0)]],
    "l4": [[("bubble_pop_1", .9, 1.0, 0), ("bubble_pop_2", .8, 1.25, .05), ("bubble_pop_3", .7, .9, .1), ("land_grapes_1", .6, 1.1, 0)],
           [("bubble_pop_2", .9, 1.05, 0), ("bubble_pop_3", .8, 1.3, .055), ("bubble_pop_1", .7, .92, .11), ("land_grapes_2", .6, 1.1, 0)]],
}


def load(stem):
    x, sr, _ = read_wav(os.path.join(ASSETS, f"sfx_{stem}.wav"))
    x = np.asarray(x, np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x)
    return x


def pitched(x, rate):
    return np.interp(np.arange(0, len(x) - 1, rate), np.arange(len(x)), x)


def main():
    names = []
    for sid, takes in R.items():
        for t, layers in enumerate(takes, 1):
            parts = [(pitched(load(st), p) * g, int(d * SR)) for st, g, p, d in layers]
            n = min(int(.75 * SR), max(len(x) + d for x, d in parts))
            y = np.zeros(n)
            for x, d in parts:
                m = min(len(x), n - d)
                y[d:d + m] += x[:m]
            f = int(.05 * SR)
            y[-f:] *= np.linspace(1, 0, f) ** 2
            _, M = lufs(y, SR)
            y *= 10 ** ((TARGET - M) / 20)
            pk = np.abs(y).max()
            if pk > .94:
                y *= .94 / pk
            name = f"sfx_pop_{sid}_{t}.wav"
            write_wav(os.path.join(ASSETS, name), y.astype(np.float32), SR)
            names.append(name)
            print(f"{name} {len(y) / SR:.2f}s M {lufs(y, SR)[1]:.1f} peak {np.abs(y).max():.2f}")
    out = os.path.join(os.environ.get("TEMP", "/tmp"), "fall_sfx", "icon_pops.txt")
    open(out, "w").write("\n".join(names) + "\n")
    print(out)


if __name__ == "__main__":
    main()
