"""Review item 2 (2026-11-15): the bonus panel under XGC showed no cards.

  .venv\Scripts\python.exe -I tools/review/bonus_xgc.py

Loads the game in social mode with the authenticate answer the live RGS gives a GC wallet (every
gameModes[].maxBet 0, 1,000 GC, a bet ladder up to 100,000 GC, default 10,000 GC), opens the bonus
panel at the opening bet and at 10,000 GC (the reviewer's screenshot) and requires all four cards.
Screenshots go to research/review_fix_shots/. Needs the mock RGS on :8744. Exit code 1 on failure.
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from cdp import Browser, game_url, enter_game, xgc_auth

OUT = Path(__file__).resolve().parents[2] / "research" / "review_fix_shots"
CARDS = """JSON.stringify({ maxBets: RGS.state.config.gameModes.map(m => m.maxBet), balance: fmtBal(state.balance), bet: fmt(bet()),
  cards: [...document.querySelectorAll('#bshopRow .bscard')].map(c => { const r = c.getBoundingClientRect();
    return { mode: c.dataset.mode, title: c.querySelector('.bsttl').textContent, price: c.querySelector('.bsprice').textContent,
             button: c.querySelector('.bsget').textContent, disabled: c.querySelector('.bsget').disabled,
             onScreen: r.width > 0 && r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight }; }) })"""


def main():
    fail = []
    b = Browser(1200, 675)
    try:
        for jur in (False, True):          # social from the URL flag, then from the jurisdiction alone
            for (w, h) in ((1200, 675), (400, 225), (375, 667)) if not jur else ((1200, 675),):
                b.size(w, h)
                ident = b.preload(xgc_auth(jur))
                b.open(game_url(social=not jur, currency="XGC"))
                enter_game(b)
                b.unpreload(ident)
                tag = f"{'juris' if jur else 'social'}_{w}x{h}"
                b.js("openBonus()"); time.sleep(1.3)
                d = json.loads(b.js(CARDS))
                b.shot(OUT / f"bonus_xgc_opening_bet_{tag}.png")
                print(tag, "opening bet:", d["bet"], "balance:", d["balance"], "maxBet:", d["maxBets"])
                for c in d["cards"]:
                    print("   ", c)
                if len(d["cards"]) != 4 or not all(c["onScreen"] for c in d["cards"]):
                    fail.append(f"{tag}: cards at the opening bet {d['cards']}")
                if "$" in json.dumps(d, ensure_ascii=False):
                    fail.append(f"{tag}: a $ with GC")
                # the reviewer's screenshot: the bet at 10,000 GC, ten times the balance
                b.js("state.betIdx = state.bets.indexOf(10000 * 1000000); refreshBet(); fitBonus()"); time.sleep(.6)
                d = json.loads(b.js(CARDS))
                b.shot(OUT / f"bonus_xgc_bet_10000_{tag}.png")
                print(tag, "bet:", d["bet"], [(c["title"], c["price"], c["button"]) for c in d["cards"]])
                if len(d["cards"]) != 4 or not all(c["onScreen"] for c in d["cards"]):
                    fail.append(f"{tag}: cards at 10,000 GC {d['cards']}")
                errs = b.console()
                if errs:
                    fail.append(f"{tag}: console {errs}")
    finally:
        b.close()
    print("\nFAIL:" if fail else "\nPASS: four cards under XGC with maxBet 0, at every bet", *fail, sep="\n" if fail else " ")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
