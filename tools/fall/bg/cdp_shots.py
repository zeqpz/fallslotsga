"""Headless-Chrome check of the living background (frontend/bgfx.js), stdlib only.

  .venv\\Scripts\\python.exe -I tools/fall/bg/cdp_shots.py [out_dir] [WxH] [dpr]

Needs the mock RGS on :8744. Writes to out_dir (default research/bgfx_shots):
  before_css.png      the CSS background alone (bgfx canvas hidden), game UI hidden
  after_bgfx.png      the bgfx canvas over it, game UI hidden
  game_after.png      the game as the player sees it
  seq_<area>_<i>.png  crops 0.4 s apart: tree (left canopy), lake+sun, village smoke, right tree
  align_diff.txt      CSS vs canvas difference in still areas (alignment check)
and prints the renderer, BGFX.stats, BGFX.bench() and rAF frame intervals with bgfx on / paused.
"""
import base64, json, os, random, socket, struct, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:8744/?sessionID=test&rgs_url=http://localhost:8744"
PORT = random.randint(9400, 9800)


class WS:
    def __init__(self, url):
        host, rest = url[5:].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{rest} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.id = 0

    def _recv(self, n):
        while len(self.buf) < n:
            c = self.s.recv(1 << 20)
            if not c:
                raise EOFError
            self.buf += c
        d, self.buf = self.buf[:n], self.buf[n:]
        return d

    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126); hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127); hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        self.s.sendall(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b""
        while True:
            b0, b1 = self._recv(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv(8))[0]
            msg += self._recv(n)
            if b0 & 0x80:
                return json.loads(msg)

    def call(self, method, **params):
        self.id += 1
        self.send({"id": self.id, "method": method, "params": params})
        while True:
            m = self.recv()
            if m.get("id") == self.id:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})

    def js(self, expr, await_=True):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=await_, returnByValue=True)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"])
        return r["result"].get("value")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "research/bgfx_shots"
    W, H = (int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else "1920x1080").split("x"))
    DPR = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    out.mkdir(parents=True, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="bgfx_chrome_")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}",
                             f"--window-size={W},{H}", "--no-first-run", "--hide-scrollbars", "--mute-audio",
                             "--autoplay-policy=no-user-gesture-required", "about:blank"])
    try:
        for _ in range(150):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                break
            except Exception:
                time.sleep(.2)
        page = next(t for t in tabs if t["type"] == "page")
        ws = WS(page["webSocketDebuggerUrl"])
        ws.call("Page.enable"); ws.call("Runtime.enable")
        ws.call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=DPR, mobile=W < H)
        ws.call("Page.navigate", url=URL)
        time.sleep(6)
        print("renderer:", ws.js("""(() => { const c = document.createElement('canvas').getContext('webgl');
            const e = c.getExtension('WEBGL_debug_renderer_info'); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : '?'; })()"""))
        for _ in range(120):   # the loader takes a while headless; the features screen's .fhit closes it
            if ws.js("(() => { const f = document.querySelector('.fhit'); return !document.getElementById('intro') && !!(f && f.getBoundingClientRect().width > 0); })()"):
                break
            time.sleep(.5)
        time.sleep(1)
        ws.js("document.querySelector('.fhit') && document.querySelector('.fhit').click()")
        time.sleep(4)
        print("bgfx:", ws.js("JSON.stringify({ready: !!document.getElementById('bgfx'), stats: window.BGFX && BGFX.stats})"))

        def shot(name, clip=None, scale=1):
            p = {"format": "png"}
            if clip:
                p["clip"] = {"x": clip[0], "y": clip[1], "width": clip[2], "height": clip[3], "scale": scale}
            (out / name).write_bytes(base64.b64decode(ws.call("Page.captureScreenshot", **p)["data"]))

        shot("game_after.png")
        # the background alone
        ws.js("for (const el of document.body.children) if (el.id !== 'camfar') el.style.visibility = 'hidden'; 1")
        ws.js("(() => { const c = document.getElementById('camnear'); if (c) c.style.visibility = 'hidden'; })()")
        time.sleep(.5)
        shot("after_bgfx.png")
        # map image coords -> screen for crops
        geo = ws.js("""(() => { const w = document.getElementById('bgwall'), r = w.getBoundingClientRect();
            const s = Math.max(r.width / 3840, r.height / 2160); return [r.left + (r.width - 3840 * s) / 2, r.top + (r.height - 2160 * s) / 2, s]; })()""")
        gx, gy, gs = geo
        def crop(x0, y0, x1, y1):
            return [max(0, gx + x0 * gs), max(0, gy + y0 * gs), (x1 - x0) * gs, (y1 - y0) * gs]
        areas = {"tree": crop(150, 0, 1050, 620), "lake": crop(450, 640, 1460, 1090),
                 "village": crop(2250, 430, 3150, 720), "redtree": crop(2650, 0, 3840, 420)}
        for i in range(6):
            for k, c in areas.items():
                shot(f"seq_{k}_{i}.png", c, 2 if k == "village" else 1)
            time.sleep(.4)
        # alignment: pause, hide the canvas, compare still areas (foreground pumpkins/field)
        ws.js("BGFX.pause(); const c = document.getElementById('bgfx'); c.style.transition = 'none'; c.style.opacity = '1'; 1")
        time.sleep(.3)
        stillclip = crop(1500, 1250, 3700, 2100)
        shot("_still_canvas.png", stillclip)
        ws.js("document.getElementById('bgfx').style.opacity = '0'; 1")
        time.sleep(.3)
        shot("before_css.png")
        shot("_still_css.png", stillclip)
        ws.js("document.getElementById('bgfx').style.opacity = '1'; BGFX.resume(); 1")
        try:
            from PIL import Image, ImageChops
            import numpy as np
            a = np.asarray(Image.open(out / "_still_canvas.png").convert("RGB"), np.int16)
            b = np.asarray(Image.open(out / "_still_css.png").convert("RGB"), np.int16)
            d = np.abs(a - b)
            (out / "align_diff.txt").write_text(f"mean {d.mean():.2f}  p99 {np.percentile(d, 99):.0f}  max {d.max()}\n")
            print("align diff (still area, may include leaves):", (out / "align_diff.txt").read_text().strip())
            (out / "_still_canvas.png").unlink(); (out / "_still_css.png").unlink()
        except Exception as e:
            print("align check skipped:", e)
        # cost
        ws.js("for (const el of document.body.children) el.style.visibility = ''; 1")
        print("bench ms/frame (render + 1px readback sync):", ws.js("[BGFX.bench(120), BGFX.bench(120), BGFX.bench(120)]"))
        frames = """new Promise(res => { const d = []; let l = performance.now(); const t0 = l;
            const f = n => { d.push(n - l); l = n; if (n - t0 < 5000) requestAnimationFrame(f); else {
              d.shift(); d.sort((a, b) => a - b); const q = p => d[Math.floor(p * (d.length - 1))];
              res({n: d.length, p50: q(.5).toFixed(2), p95: q(.95).toFixed(2), p99: q(.99).toFixed(2), max: d[d.length - 1].toFixed(1)}); } };
            requestAnimationFrame(f); })"""
        for run in range(2):
            ws.js("BGFX.resume(); 1"); time.sleep(.5)
            on = ws.js(frames)
            ws.js("BGFX.pause(); 1"); time.sleep(.5)
            off = ws.js(frames)
            print(f"rAF run {run}: bgfx on {on} | paused {off}")
        ws.js("BGFX.resume(); 1")
        print("stats:", ws.js("JSON.stringify(BGFX.stats)"))
    finally:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)   # its whole tree


if __name__ == "__main__":
    main()
