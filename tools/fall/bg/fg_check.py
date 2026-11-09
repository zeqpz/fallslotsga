"""Headless-Chrome check of the cut-out foreground (#fgwall) and the leaf-cleaned painting, stdlib +
pillow/numpy. Needs the mock RGS on :8744.

  .venv\\Scripts\\python.exe -I tools/fall/bg/fg_check.py out_dir WxH [WxH ...]

Per size (out_dir/<W>x<H>/):
  before_game.png    the game over the ORIGINAL painting (static leaves, pumpkins in the wall),
                     bgfx canvas and #fgwall hidden - what it looked like before this change
  after_game.png     the game as it is now (bgfx live, foreground layer)
  orig_scene.png     original painting alone (CSS), UI hidden
  new_scene.png      back plate + foreground (CSS + #fgwall), UI hidden, bgfx hidden
  new_scene_bgfx.png the same with the bgfx canvas (paused) instead of the CSS picture
  align.txt          new_scene vs orig_scene in the foreground's boxes (must be ~0: aligned)
  hop_game_<i>.png   the game during a spin's hop (playRound('base'), page animations at 4% speed)
  hop_scene_<i>.png  the same with the UI hidden (the frames hop_fg_diff.txt measures)
  hop.json           per frame: #camfar / #bgwall transforms and #fgr's rect (must not change)
  stress_cam_*.png   the wall shoved 20/16 px + 3% zoom (more than the camera ever does), UI off / on
  hop_fg_diff.txt    measured shift of the foreground (bale) vs the wall (barn) in each frame
"""
import base64, json, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp_shots import WS, CHROME, URL, PORT  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
ORIG = ROOT / "art/fall-src/bg/bonus_wall_orig.webp"
META = json.loads((ROOT / "art/fall-src/bg/fg.json").read_text())


def run(out, W, H, port):
    import numpy as np
    from PIL import Image
    out.mkdir(parents=True, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="fgcheck_chrome_")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={prof}",
                             f"--window-size={W},{H}", "--no-first-run", "--hide-scrollbars", "--mute-audio",
                             "--autoplay-policy=no-user-gesture-required", "about:blank"])
    try:
        for _ in range(150):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                break
            except Exception:
                time.sleep(.2)
        page = next(t for t in tabs if t["type"] == "page")
        ws = WS(page["webSocketDebuggerUrl"])
        ws.call("Page.enable"); ws.call("Runtime.enable")
        mobile = W < H
        ws.call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=mobile)
        ws.call("Page.navigate", url=URL)
        time.sleep(6)
        for _ in range(120):
            if ws.js("(() => { const f = document.querySelector('.fhit'); return !document.getElementById('intro') && !!(f && f.getBoundingClientRect().width > 0); })()"):
                break
            time.sleep(.5)
        time.sleep(1)
        ws.js("document.querySelector('.fhit') && document.querySelector('.fhit').click()")
        time.sleep(4)

        def shot(name):
            data = base64.b64decode(ws.call("Page.captureScreenshot", format="png")["data"])
            (out / name).write_bytes(data)
            return np.asarray(Image.open(out / name).convert("RGB"), np.int16)

        after = shot("after_game.png")
        orig_url = "data:image/webp;base64," + base64.b64encode(ORIG.read_bytes()).decode()
        ws.js(f"window.__orig = {json.dumps(orig_url)}; 1")
        ws.js("""(() => { const w = document.getElementById('bgwall'); window.__bgsave = w.style.background;
            const cs = getComputedStyle(w); window.__bgimg = cs.backgroundImage; 1; })()""")
        set_orig = """(() => { const w = document.getElementById('bgwall');
            w.style.backgroundImage = window.__bgimg.replace(/url\\([^)]*bonus_wall[^)]*\\)/, 'url(' + window.__orig + ')'); })()"""
        set_new = "document.getElementById('bgwall').style.backgroundImage = ''"
        canvas = lambda on: f"(() => {{ const c = document.getElementById('bgfx'); if (c) {{ c.style.transition = 'none'; c.style.opacity = '{1 if on else 0}'; }} }})()"
        fg = lambda on: f"document.getElementById('fgwall').style.visibility = '{'' if on else 'hidden'}'"
        ws.js("BGFX.pause(); 1")
        ws.js(set_orig); ws.js(canvas(False)); ws.js(fg(False)); time.sleep(1.2)
        shot("before_game.png")
        ui_off = """for (const el of document.body.children) if (!['camfar','fgwall'].includes(el.id)) el.style.visibility = 'hidden';
            document.getElementById('camnear').style.visibility = 'hidden'; 1"""
        ui_on = "for (const el of document.body.children) if (el.id !== 'fgwall') el.style.visibility = ''; 1"
        ws.js(ui_off); time.sleep(.4)
        o = shot("orig_scene.png")
        ws.js(set_new); ws.js(fg(True)); time.sleep(1.2)
        n = shot("new_scene.png")
        ws.js(canvas(True)); time.sleep(.4)
        nb = shot("new_scene_bgfx.png")
        # alignment in the foreground's boxes, in screen px
        gx, gy, gs = ws.js("""(() => { const w = document.getElementById('bgwall'), r = w.getBoundingClientRect();
            const s = Math.max(r.width / 3840, r.height / 2160); return [r.left + (r.width - 3840 * s) / 2, r.top + (r.height - 2160 * s) / 2, s]; })()""")
        lines = []
        for name, L in META["layers"].items():
            x0, y0, x1, y1 = L["box"]
            sx0, sy0 = max(0, int(gx + x0 * gs)), max(0, int(gy + y0 * gs))
            sx1, sy1 = min(W, int(gx + x1 * gs)), min(H, int(gy + y1 * gs))
            if sx1 <= sx0 or sy1 <= sy0:
                lines.append(f"{name}: off screen"); continue
            for lab, img in (("css", n), ("bgfx", nb)):
                d = np.abs(img[sy0:sy1, sx0:sx1] - o[sy0:sy1, sx0:sx1]).max(2)
                lines.append(f"{name} [{lab}] box {sx0},{sy0}-{sx1},{sy1}: mean {d.mean():.2f}  p95 {np.percentile(d, 95):.0f}  p99 {np.percentile(d, 99):.0f}  >40: {(d > 40).mean() * 100:.2f}%")
        (out / "align.txt").write_text("\n".join(lines) + "\n")
        print(f"{W}x{H} align:\n  " + "\n  ".join(lines))
        # the hop: a real spin
        ws.js(ui_on); ws.js("BGFX.resume(); 1"); time.sleep(.6)
        probe = """(() => { const r = document.getElementById('fgr').getBoundingClientRect(), l = document.getElementById('fgl').getBoundingClientRect();
            const cf = getComputedStyle(document.getElementById('camfar')), bw = getComputedStyle(document.getElementById('bgwall'));
            return {t: Math.round(performance.now()), camfar: cf.transform, bg_translate: bw.translate, bg_scale: bw.scale,
                    bg_anim: document.getElementById('bgwall').getAnimations().map(a => a.animationName || a.id || 'anim').join(','),
                    fgr: [r.left, r.top, r.width, r.height].map(v => +v.toFixed(2)), fgl: [l.left, l.top, l.width, l.height].map(v => +v.toFixed(2))}; })()"""
        # start a real spin; as soon as the wall's hop starts, slow every animation on the page to 4%
        # (the hop is 0.7 s; a screenshot takes ~0.6 s headless) so the frames sample the whole hop
        def hop(prefix, n):
            # a real spin, every animation on the page held at 4% speed from the moment it starts (the
            # hop is 0.7 s, a headless screenshot ~0.6 s), so the frames sample the whole hop
            ws.js("""window.__slow = true; (function k() { if (!window.__slow) return;
                for (const a of document.getAnimations()) if (a.playbackRate !== .04) a.playbackRate = .04;
                requestAnimationFrame(k); })(); window.__spin = playRound('base').catch(e => String(e)); 1""", await_=False)
            ws.js("""new Promise(res => { const t0 = performance.now(); const f = () => {
                if (document.getElementById('bgwall').getAnimations().length || performance.now() - t0 > 5000) res(1);
                else requestAnimationFrame(f); }; f(); })""")
            fr, rc = [], []
            for i in range(n):
                rc.append(ws.js(probe))
                fr.append(shot(f"{prefix}_{i:02d}.png"))
                time.sleep(.5)
            ws.js("window.__slow = false; for (const a of document.getAnimations()) a.playbackRate = 1; 1")
            ws.js("Promise.race([window.__spin, new Promise(r => setTimeout(() => r('pending'), 15000))]).then(v => String(v))")
            time.sleep(1.5)
            return fr, rc
        hop("hop_game", 6)                       # with the game on top: what the player sees
        ws.js(ui_off); time.sleep(.3)
        frames, rec = hop("hop_scene", 14)       # the scene alone: measured below
        # stress: the wall pushed further than any camera move does (20 px across, 16 down, 3% in),
        # to look at the painted-in field it uncovers round the foreground
        ws.js("document.getElementById('camfar').style.transform = 'translate(-20px, 16px) scale(1.03)'; 1"); time.sleep(.4)
        shot("stress_cam_scene.png")
        ws.js(ui_on); time.sleep(.4)
        shot("stress_cam_game.png")
        ws.js("document.getElementById('camfar').style.transform = ''; 1")
        (out / "hop.json").write_text(json.dumps(rec, indent=1))

        def shift(a, b, r=28):
            """integer (dx, dy) that best maps crop a (frame 0) onto b"""
            ga, gb = a.mean(2), b.mean(2)
            best = (1e9, 0, 0)
            for dy in range(-r, r + 1):
                for dx in range(-12, 13):
                    sa = ga[r:-r, 12:-12]
                    sb = gb[r + dy:gb.shape[0] - r + dy, 12 + dx:gb.shape[1] - 12 + dx]
                    e = np.abs(sa - sb).mean()
                    if e < best[0]:
                        best = (e, dx, dy)
            return best
        # the right cluster's hay bale (foreground) and open field (wall, no wind there), screen px at rest
        def box(x0, y0, x1, y1):
            return (max(0, int(gx + x0 * gs)), max(0, int(gy + y0 * gs)), min(W, int(gx + x1 * gs)), min(H, int(gy + y1 * gs)))
        FB, WB = box(3150, 1580, 3800, 1860), box(1150, 1450, 1750, 1780)
        ref = frames[0]
        txt = [f"fg box (bale) {FB}, wall box (field) {WB}; shift = best integer (dx, dy) from frame 0"]
        for i, f in enumerate(frames):
            ef, fdx, fdy = shift(ref[FB[1]:FB[3], FB[0]:FB[2]], f[FB[1]:FB[3], FB[0]:FB[2]])
            ew, wdx, wdy = shift(ref[WB[1]:WB[3], WB[0]:WB[2]], f[WB[1]:WB[3], WB[0]:WB[2]])
            txt.append(f"frame {i:2d} t={rec[i]['t'] - rec[0]['t']:5d}ms  fg shift ({fdx:+d},{fdy:+d}) err {ef:5.2f} | wall shift ({wdx:+d},{wdy:+d}) err {ew:5.2f}"
                       f" | bgwall translate {rec[i]['bg_translate']} scale {rec[i]['bg_scale']} | camfar {rec[i]['camfar'][:48]} | #fgr {rec[i]['fgr']}")
        (out / "hop_fg_diff.txt").write_text("\n".join(txt) + "\n")
        print("\n".join(txt))
    finally:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)


def main():
    out = Path(sys.argv[1])
    sizes = sys.argv[2:] or ["1920x1080"]
    for k, s in enumerate(sizes):
        W, H = (int(v) for v in s.split("x"))
        run(out / s, W, H, PORT + k)


if __name__ == "__main__":
    main()
