"""Live rounds against the mock RGS, end to end (the check the review-fix round never finished).

  .venv\\Scripts\\python.exe -I tools/review/live_spin.py [--spins 6] [--social]

A session of its own (nothing to resume), then: base spins through playRound, one Bonus Boost spin, one
Bonus round and one Extreme Bonus round bought from the shop. After every round it requires that the round
finished (state.playing false, buttons back), that the shown balance is the RGS's, that the balance moved by
win - price, and that the console stayed clean. Needs the mock RGS on :8744. Exit code 1 on failure.
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from cdp import Browser, game_url, enter_game

OUT = Path(__file__).resolve().parents[2] / "research" / "review_fix_shots"
# one round, fast-forwarded where the game allows it; resolves to what it did
ROUND = """(async (mode) => {
  const before = state.balance, price = (MODE_COST[mode] || 1) * bet();
  const t0 = performance.now();
  const skipper = setInterval(() => { if (!state.noSkip) state.skip = true;
    for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e) e.click(); } }, 400);
  let ok, err = null;
  try { ok = await playRound(mode); } catch (e) { ok = false; err = String(e && e.stack || e); }
  clearInterval(skipper);
  await new Promise(r => setTimeout(r, 600));
  for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e) e.click(); }
  await new Promise(r => setTimeout(r, 400));
  return JSON.stringify({ mode, ok, err, ms: Math.round(performance.now() - t0), price, before, after: state.balance,
    rgs: RGS.state.balance, playing: state.playing, spinOff: document.getElementById('spinBtn').disabled,
    shown: document.getElementById('balance').textContent, win: document.getElementById('roundWin').textContent,
    notice: (document.querySelector('.notice.show, .notice.on') || {}).textContent || '' });
})(%s)"""


def main():
    args = sys.argv[1:]
    spins = int(args[args.index("--spins") + 1]) if "--spins" in args else 6
    social = "--social" in args
    fail = []
    b = Browser(1200, 675)
    try:
        b.open(game_url(social=social))
        enter_game(b)
        rounds = ["base"] * spins + ["boost", "bonus", "extremebonus"]
        for i, mode in enumerate(rounds):
            if mode == "boost":
                b.js("state.boost = true")
                mode_arg = "base"
            else:
                b.js("state.boost = false")
                mode_arg = mode
            time.sleep(.35)                       # playRound refuses two plays inside 250 ms
            d = json.loads(b.js(ROUND % json.dumps(mode_arg)))
            d["mode"] = mode
            price = d["price"] * (1.25 if mode == "boost" else 1)
            delta = d["after"] - d["before"]
            print(f"{i + 1:2d} {mode:13s} ok={d['ok']} {d['ms']:6d} ms  balance {d['before']} -> {d['after']}  "
                  f"(price {price:g}, net {delta:+g})  shown {d['shown']!r} win {d['win']!r}")
            if not d["ok"]:
                fail.append(f"round {i + 1} {mode}: playRound returned {d['ok']} {d['err'] or ''} notice={d['notice']!r}")
            if d["playing"] or d["spinOff"]:
                fail.append(f"round {i + 1} {mode}: the game did not come back (playing={d['playing']}, spin disabled={d['spinOff']})")
            if d["after"] != d["rgs"]:
                fail.append(f"round {i + 1} {mode}: shown balance {d['after']} is not the RGS's {d['rgs']}")
            if delta < -price - 1e-6:
                fail.append(f"round {i + 1} {mode}: lost more than the price ({delta} < -{price})")
            if mode in ("bonus", "extremebonus"):
                b.shot(OUT / f"live_after_{mode}{'_social' if social else ''}.png")
        errs = b.console()
        if errs:
            fail.append(f"console: {errs}")
        b.shot(OUT / f"live_end{'_social' if social else ''}.png")
    finally:
        b.close()
    print("\nFAIL:" if fail else "\nPASS: every live round finished, balances match the RGS, console clean", *fail, sep="\n" if fail else " ")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
