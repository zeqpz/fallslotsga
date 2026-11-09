"""Move frontend assets the game never loads out of frontend/ (so they are not uploaded) into
art/frontend_attic/, keeping their relative paths. Nothing is deleted. From the 2026-11-08 audit
(research/audit_2026-11-08.md, section 1.2-1.3). Re-runnable: already-moved files are skipped.

  python -I tools/move_dead_assets.py [--dry]"""
import json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT = os.path.join(ROOT, "frontend", "assets")
ATTIC = os.path.join(ROOT, "art", "frontend_attic", "assets")

DIRS = ["sym/d16", "sym/d24", "sym/d32"]   # old frame sheets: only the ?sheets debug path reads them
FILES = [
    "logo_intro.webp", "auto_box.webp", "hud_hex.webp", "vol_frame.webp", "vol_fill.webp",
    "hud_menu.webp", "hud_audio.webp", "hud_auto.webp", "hud_rapid.webp", "hud_rapid_on.webp",
    "auto_start_text.webp", "bonus_play_text.webp",
    "sfx_rooster_1.wav", "sfx_rooster_1.ogg", "sfx_rooster_2.wav", "sfx_rooster_2.ogg",
    "sym/big/M_cork.webp",
]
RIM_DEAD = ["auto_box", "hud_audio", "hud_auto", "hud_hex", "hud_menu", "hud_rapid", "hud_rapid_on", "vol_frame"]


def size(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs)


def move(rel, dry):
    src, dst = os.path.join(FRONT, rel), os.path.join(ATTIC, rel)
    if not os.path.exists(src):
        return 0
    n = size(src)
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
    print(f"{'would move' if dry else 'moved'} {rel}  {n:,} B")
    return n


def main():
    dry = "--dry" in sys.argv
    total = sum(move(r, dry) for r in DIRS + FILES)
    for name in RIM_DEAD:
        total += move(f"rim/{name}.webp", dry) + move(f"rim/{name}_sdf.png", dry)
    rims = os.path.join(FRONT, "rim", "rims.json")
    data = json.load(open(rims, encoding="utf-8"))
    gone = [k for k in RIM_DEAD if k in data]
    if gone and not dry:
        for k in gone:
            del data[k]
        json.dump(data, open(rims, "w", encoding="utf-8"), indent=1)
    print(f"rims.json: dropped {gone}")
    print(f"TOTAL {total:,} B ({total / 1e6:.1f} MB) {'would be ' if dry else ''}out of frontend/")


if __name__ == "__main__":
    main()
