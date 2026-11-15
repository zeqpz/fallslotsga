"""Review item 5 (2026-11-15): the game at every size Studio's play modal offers.

  .venv\\Scripts\\python.exe -I tools/review/sizes.py [--social] [--only 400x225,320x568] [--out DIR]

For each size - Desktop 1200x675, Laptop 1024x576, Popout S 400x225, Popout L 800x450, Mobile L 425x812,
Mobile M 375x667, Mobile S 320x568 - it drives the game through its screens (loader, feature intro, main
game, bonus shop, info page top/middle/end, auto play pop-up, win pop-up, bonus intro, a notice, the replay
window at the start and at the end), saves a screenshot of each to research/review_fix_shots/<size>/ and
measures two things a screenshot cannot be grepped for:
  * every named part of the screen lies whole inside the window (nothing off-screen, no page scrollbars);
  * the smallest lettering on that screen, in real pixels after all scaling.
A sheet of all screens per size (sheet_<size>.png) is written too. Needs the mock RGS on :8744.
Exit code 1 when a part is off-screen.
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from cdp import Browser, game_url, replay_url, enter_game, INTRO_GONE, FEATURES_UP

ROOT = Path(__file__).resolve().parents[2]
SIZES = [("Desktop", 1200, 675), ("Laptop", 1024, 576), ("Popout S", 400, 225), ("Popout L", 800, 450),
         ("Mobile L", 425, 812), ("Mobile M", 375, 667), ("Mobile S", 320, 568)]

HELPERS = r"""
window.__rv = {
  seen(el) {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.01;
  },
  // every element the selectors name: is it whole inside the window?
  parts(sels) {
    const out = [];
    for (const s of sels) {
      const els = [...document.querySelectorAll(s)];
      if (!els.length) { out.push({ s, missing: true }); continue; }
      for (const el of els) {
        if (!this.seen(el)) { out.push({ s, hidden: true }); continue; }
        const r = el.getBoundingClientRect();
        out.push({ s, box: [r.left, r.top, r.right, r.bottom].map(v => Math.round(v)),
                   inside: r.left >= -1.5 && r.top >= -1.5 && r.right <= innerWidth + 1.5 && r.bottom <= innerHeight + 1.5 });
      }
    }
    return out;
  },
  // the smallest lettering under a root, in real pixels: font-size x every scale applied above it
  minFont(rootSel) {
    let best = null;
    for (const root of document.querySelectorAll(rootSel)) {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        const txt = n.nodeValue.trim(), el = n.parentElement;
        if (!txt || !el || !/[A-Za-z0-9]/.test(txt) || !this.seen(el)) continue;
        if (el.closest('[aria-hidden="true"], .ticker, script, style')) continue;
        const r = el.getBoundingClientRect();
        if (r.right < 0 || r.bottom < 0 || r.left > innerWidth || r.top > innerHeight) continue;
        const k = el.offsetWidth ? r.width / el.offsetWidth : 1;
        const px = parseFloat(getComputedStyle(el).fontSize) * k;
        if (!best || px < best.px) best = { px: +px.toFixed(1), text: txt.slice(0, 40) };
      }
    }
    return best;
  },
  page() { return { sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, w: innerWidth, h: innerHeight }; },
};
"""

# screen -> (parts that must lie inside the window, the root whose lettering is measured)
MAIN = [".hudframe", "#bonusBtn", "#board", "#spinBtn", "#balance", "#betVal", "#roundWin", "#menuBtn", "#audioBtn", "#rapidBtn", "#autoBtn", "#betUp", "#betDown"]
CHECKS = {
    "01_loader": (["#intro .introword", "#introBar", "#introMsg"], "#intro"),
    "02_feature_intro": ([".fbox", ".fcont .fhit"], ".features, .featwrap, body.features-up .fbox, .fcont"),
    "03_main": (MAIN, ".hud"),
    "04_bonus_shop": (["#bonusWrap .bshop", "#bonusWrap .bscard", "#bonusWrap .bsget", "#bonusWrap .bshopbar", "#bonusClose"], "#bonusWrap"),
    "05_bonus_confirm": (["#bonusWrap .bshop", "#bonusWrap .bscard", "#bonusWrap .bsget", "#bonusWrap .bshopbar", "#bonusClose"], "#bonusWrap"),
    "06_info_top": (["#infoWrap .infopanel"], "#infoWrap"),
    "07_info_modes": (["#infoWrap .infopanel"], "#infoWrap"),
    "08_info_paytable": (["#infoWrap .infopanel"], "#infoWrap"),
    "09_info_end": (["#infoWrap .infopanel", "#infoClose"], "#infoWrap"),
    "10_autoplay": (["#autoPop", "#autoOpts button", "#autoYes"], "#autoPop"),
    "11_win_popup": ([".totalwin .twamount", ".totalwin .twhead"], ".totalwin"),
    "12_bonus_intro": ([".bonusintro .bnum", ".bonusintro .bcont", ".bonusintro .bhow"], ".bonusintro"),
    "13_notice": (["#notice"] + MAIN, "#notice"),
    "14_replay_start": (["#rpCard", "#replayPlay"], "#rpCard"),
    "15_replay_end": (["#rpCard", "#replayPlay"], "#rpCard"),
}


def run_size(b, name, w, h, out, social, scan=None):   # scan(key): called on every screen (tools/social_check.py)
    res = {}
    b.size(w, h)

    def snap(key, settle=.5):
        time.sleep(settle)
        b.shot(out / f"{key}.png")
        if scan:
            scan(key)
        parts, root = CHECKS[key]
        b.js(HELPERS)
        res[key] = {"parts": b.js(f"__rv.parts({json.dumps(parts)})"), "minFont": b.js(f"__rv.minFont({json.dumps(root)})"),
                    "page": b.js("__rv.page()"), "console": b.console()}

    cur = "XGC" if social else None
    b.open(game_url(social=social, currency=cur), settle=.2)
    b.wait("document.getElementById('introMsg') && document.getElementById('introMsg').getBoundingClientRect().height > 0", 10)
    snap("01_loader", .9)
    b.wait(f"({INTRO_GONE}) && {FEATURES_UP}", 120)
    snap("02_feature_intro", 1.2)
    enter_game(b)
    snap("03_main", .8)
    b.js("openBonus()"); snap("04_bonus_shop", 1.3)
    b.js("document.querySelector('#bshopRow .bscard .bsget').click()"); snap("05_bonus_confirm", .5)
    b.js("closeBonus()"); time.sleep(.5)
    b.js("document.getElementById('menuBtn').click()"); snap("06_info_top", 1.2)
    scroll = "(() => { const p = document.querySelector('#infoWrap .infopanel'); const s = [...p.querySelectorAll('section')]; const t = s.find(x => /%s/i.test(x.querySelector('h4') ? x.querySelector('h4').textContent : '')); p.scrollTop = t ? t.offsetTop - 8 : p.scrollHeight; })()"
    b.js(scroll % "modes"); snap("07_info_modes", .5)
    b.js(scroll % "table"); snap("08_info_paytable", .5)
    b.js("(() => { const p = document.querySelector('#infoWrap .infopanel'); p.scrollTop = p.scrollHeight; })()"); snap("09_info_end", .5)
    b.js("document.getElementById('infoClose').click()"); time.sleep(.6)
    b.js("document.getElementById('autoBtn').click()"); snap("10_autoplay", 1.0)
    b.js("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))"); time.sleep(.5)
    b.js("window.__tw = totalWinScreen(Math.round(bet() * 1234.5), { total: false }); 0"); snap("11_win_popup", 6.0)
    b.js("(() => { const t = document.querySelector('.totalwin'); if (t) t.click(); })()"); time.sleep(.4)
    b.js("(() => { const t = document.querySelector('.totalwin'); if (t) t.click(); })()")
    b.wait("!document.querySelector('.totalwin')", 20)
    b.js("window.__bi = bonusIntro(12, true); 0"); snap("12_bonus_intro", 3.5)
    b.js("(() => { const t = document.querySelector('.bonusintro'); if (t) t.click(); })()")
    b.wait("!document.querySelector('.bonusintro')", 20); time.sleep(.5)
    b.js("notice('<b>Not enough balance</b> — lower the {bet|play amount}.', true, 0)"); snap("13_notice", .8)

    b.open(replay_url(mode="bonus", event=4344, social=social, currency=cur or "USD"), settle=.3)
    b.wait("document.getElementById('replayPlay').dataset.phase === 'ready'", 60)
    snap("14_replay_start", .8)
    b.js("document.getElementById('turbo').checked = true; document.getElementById('replayPlay').click()")
    t0 = time.time()
    while time.time() - t0 < 240:      # hurry the round along: skip, and click through its screens
        if b.js("document.getElementById('replayPlay').dataset.phase === 'done' && !document.getElementById('replayWrap').hidden"):
            break
        b.js("(() => { state.skip = true; for (const s of ['.bonusintro', '.totalwin']) { const e = document.querySelector(s); if (e) e.click(); } })()")
        time.sleep(.4)
    snap("15_replay_end", 1.0)
    return res


def sheet(out, w, h):
    from PIL import Image
    files = sorted(out.glob("[0-9][0-9]_*.png"))
    cols = 5 if w >= h else 8
    k = min(1.0, (300 if w >= h else 200) / w)
    tw, th = int(w * k), int(h * k)
    rows = -(-len(files) // cols)
    im = Image.new("RGB", (cols * (tw + 6) + 6, rows * (th + 6) + 6), (30, 30, 34))
    for i, f in enumerate(files):
        t = Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS)
        im.paste(t, (6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 6)))
    im.save(out.parent / f"sheet_{w}x{h}{out.name[len(f'{w}x{h}'):]}.png")


def main():
    args = sys.argv[1:]
    social = "--social" in args
    only = args[args.index("--only") + 1].split(",") if "--only" in args else None
    base = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "research" / "review_fix_shots"
    report, bad = {}, []
    b = Browser(1200, 675)
    try:
        for name, w, h in SIZES:
            if only and f"{w}x{h}" not in only:
                continue
            out = base / (f"{w}x{h}" + ("_social" if social else ""))
            res = run_size(b, name, w, h, out, social)
            report[f"{w}x{h}"] = res
            sheet(out, w, h)
            print(f"\n== {name} {w}x{h}{' (social, XGC)' if social else ''}")
            for key, r in res.items():
                off = [p for p in r["parts"] if p.get("inside") is False]
                gone = [p["s"] for p in r["parts"] if p.get("missing") or p.get("hidden")]
                scroll = r["page"]["sw"] > r["page"]["w"] + 1 or r["page"]["sh"] > r["page"]["h"] + 1
                mf = r["minFont"]
                line = f"  {key:18s} {'OFF-SCREEN ' + json.dumps(off) if off else 'inside'}"
                line += f" | smallest text {mf['px']}px ({mf['text']!r})" if mf else " | no text"
                if gone:
                    line += f" | not shown: {sorted(set(gone))}"
                if scroll:
                    line += f" | PAGE SCROLLS {r['page']}"
                if r["console"]:
                    line += f" | console: {r['console'][:2]}"
                print(line)
                if off or scroll:
                    bad.append(f"{w}x{h} {key}")
    finally:
        b.close()
    (base / ("sizes_report" + ("_social" if social else "") + ".json")).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\nOFF-SCREEN / SCROLLING:", bad if bad else "none")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
