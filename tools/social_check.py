"""Social mode says nothing restricted (review item 3, 2026-11-15): the zero-hit scan over every screen.

  .venv\\Scripts\\python.exe -I tools/social_check.py [--size 1200x675]

Drives the game in social mode (XGC wallet) through every screen tools/review/sizes.py knows - loader, feature
intro, main game, bonus shop + confirm, the whole info page, auto play, win pop-up, bonus intro, a notice, the
replay window at its start and end - and at each one reads EVERYTHING a player or a screen reader can be given:
all text in the page (shown or not: a hidden label is one click from showing), and every aria-label, title, alt,
placeholder and value. Any word of the jurisdiction table (and its inflections), or a "$", is a hit.
Exit code 1 on any hit. Needs the mock RGS on :8744.
"""
import json, re, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.stdout.reconfigure(encoding="utf-8")
from cdp import Browser
from sizes import run_size

RESTRICTED = re.compile(
    r"\b(bet|bets|betting|bettor|rebet|rebets|autobet|buy|buys|buying|bought|cash|cashout|cashed|cost|costs|costing|"
    r"credit|credits|credited|currency|currencies|deposit|deposits|deposited|fund|funds|funded|gamble|gambles|gambling|"
    r"money|paid|pay|pays|paying|payer|payout|payouts|paytable|paytables|purchase|purchases|purchased|purchasing|"
    r"stake|stakes|staked|staking|wager|wagers|wagered|wagering|withdraw|withdraws|withdrawal|withdrawals)\b", re.I)
# the page's words: every text node outside script/style, and the attributes that are read out or shown
COLLECT = """JSON.stringify((() => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: n =>
    /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(n.parentElement.tagName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
  for (let n; (n = w.nextNode());) { const t = n.nodeValue.replace(/\\s+/g, ' ').trim(); if (t) out.push(['text', t]); }
  for (const el of document.querySelectorAll('[aria-label], [title], [alt], [placeholder], input[value], [aria-description], [data-tip]'))
    for (const a of ['aria-label', 'title', 'alt', 'placeholder', 'value', 'aria-description', 'data-tip']) { const v = el.getAttribute(a); if (v && v.trim()) out.push([a, v.trim()]); }
  out.push(['document.title', document.title]);
  return out;
})())"""


def main():
    args = sys.argv[1:]
    w, h = (int(v) for v in (args[args.index("--size") + 1] if "--size" in args else "1200x675").split("x"))
    hits, seen, count = {}, set(), 0
    b = Browser(w, h)

    def scan(key):
        nonlocal count
        for kind, text in json.loads(b.js(COLLECT)):
            count += 1
            if (kind, text) in seen:
                continue
            seen.add((kind, text))
            words = sorted({m.group(0).lower() for m in RESTRICTED.finditer(text)})
            if "$" in text:
                words.append("$")
            if words:
                hits.setdefault((kind, text), (key, words))

    try:
        run_size(b, "social", w, h, Path(tempfile.mkdtemp(prefix="social_check_")), True, scan=scan)
    finally:
        b.close()
    print(f"{len(seen)} different strings read over {count} readings")
    for (kind, text), (key, words) in hits.items():
        print(f"  HIT {words} first at {key} [{kind}]: {text[:160]!r}")
    print("\nFAIL: %d restricted strings in social mode" % len(hits) if hits else "\nPASS: zero restricted terms on any screen in social mode")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
