"""Opus copies of the sound effects without node / Playwright: a tiny local server hands headless Chrome
(or Edge) the WAVs, the page encodes each with WebCodecs exactly as encode_new.js does (48 kHz, 64/96 kbps,
hand-muxed Ogg, round-trip length check) and POSTs the .ogg back, which is written next to its WAV.

  python tools/sfx/encode_opus.py %TEMP%/fall_sfx/written.txt      # a list of sfx_*.wav names, one a line
"""
import os, sys, json, re, socket, subprocess, tempfile, threading, http.server

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "frontend", "assets")
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]

# the in-page encoder: encode_new.js's page.evaluate body, fed by fetch and answered by POST
PAGE = r"""<!doctype html><meta charset="utf-8"><title>enc</title><script>
const BITRATE = { 1: 64000, 2: 96000 };
async function encode(bytes) {
  const probe = new OfflineAudioContext(1, 1, 48000);
  const buf = await probe.decodeAudioData(bytes.slice(0));
  const ch = Math.min(2, buf.numberOfChannels), frames = buf.length, SR = 48000;
  const packets = []; let head = null;
  const enc = new AudioEncoder({
    output: (chunk, meta) => {
      if (meta && meta.decoderConfig && meta.decoderConfig.description && !head) head = new Uint8Array(meta.decoderConfig.description);
      const d = new Uint8Array(chunk.byteLength); chunk.copyTo(d); packets.push({ d, dur: chunk.duration });
    },
    error: e => { throw e; },
  });
  enc.configure({ codec: 'opus', sampleRate: SR, numberOfChannels: ch, bitrate: BITRATE[ch] });
  const step = 960, padded = frames + step * 4;
  for (let i = 0; i < padded; i += step) {
    const n = Math.min(step, padded - i), data = new Float32Array(n * ch);
    for (let c = 0; c < ch; c++) { const src = buf.getChannelData(c); for (let k = 0; k < n; k++) data[c * n + k] = i + k < frames ? src[i + k] : 0; }
    enc.encode(new AudioData({ format: 'f32-planar', sampleRate: SR, numberOfFrames: n, numberOfChannels: ch, timestamp: Math.round(i / SR * 1e6), data }));
  }
  await enc.flush();
  const preskip = head && head.length >= 12 && String.fromCharCode(...head.slice(0, 8)) === 'OpusHead' ? head[10] | (head[11] << 8) : 312;
  const crcTable = new Uint32Array(256);
  for (let i = 0; i < 256; i++) { let r = i << 24; for (let k = 0; k < 8; k++) r = (r & 0x80000000) ? ((r << 1) ^ 0x04c11db7) : (r << 1); crcTable[i] = r >>> 0; }
  const crc = a => { let c = 0; for (const x of a) c = ((c << 8) ^ crcTable[((c >>> 24) ^ x) & 255]) >>> 0; return c; };
  const serial = Math.floor(Math.random() * 0xffffffff) >>> 0;
  const pages = []; let seq = 0;
  const page = (pkts, granule, flags) => {
    const lace = [];
    for (const p of pkts) { let n = p.length; while (n >= 255) { lace.push(255); n -= 255; } lace.push(n); }
    const hdr = new Uint8Array(27 + lace.length); const dv = new DataView(hdr.buffer);
    hdr.set([79, 103, 103, 83]); hdr[4] = 0; hdr[5] = flags;
    dv.setUint32(6, granule % 0x100000000, true); dv.setUint32(10, Math.floor(granule / 0x100000000), true);
    dv.setUint32(14, serial, true); dv.setUint32(18, seq++, true); hdr[26] = lace.length; hdr.set(lace, 27);
    const body = new Uint8Array(pkts.reduce((s, p) => s + p.length, 0)); let o = 0; for (const p of pkts) { body.set(p, o); o += p.length; }
    const all = new Uint8Array(hdr.length + body.length); all.set(hdr); all.set(body, hdr.length);
    dv.setUint32(22, 0, true); const c = crc(all); new DataView(all.buffer).setUint32(22, c, true);
    pages.push(all);
  };
  const opusHead = new Uint8Array(19); const hv = new DataView(opusHead.buffer);
  opusHead.set([..."OpusHead"].map(c => c.charCodeAt(0))); opusHead[8] = 1; opusHead[9] = ch;
  hv.setUint16(10, preskip, true); hv.setUint32(12, buf.sampleRate || 48000, true); hv.setInt16(16, 0, true); opusHead[18] = 0;
  const vendor = [..."smukiez sfx"].map(c => c.charCodeAt(0));
  const tags = new Uint8Array(8 + 4 + vendor.length + 4); const tv = new DataView(tags.buffer);
  tags.set([..."OpusTags"].map(c => c.charCodeAt(0))); tv.setUint32(8, vendor.length, true); tags.set(vendor, 12); tv.setUint32(12 + vendor.length, 0, true);
  page([opusHead], 0, 2); page([tags], 0, 0);
  const end = preskip + frames;
  const cum = []; let g = 0;
  for (const p of packets) { g += Math.round(p.dur * 48000 / 1e6); cum.push(g); }
  const firstBeyond = Math.max(1, cum.findIndex(v => v > end) < 0 ? packets.length - 1 : cum.findIndex(v => v > end));
  let batch = [], size = 0;
  packets.forEach((p, i) => {
    batch.push(p.d); size += p.d.length;
    const last = i === packets.length - 1;
    if (last) { page(batch, end, 4); return; }
    if (i === firstBeyond - 1 || (i < firstBeyond - 1 && (size > 3800 || batch.length >= 50))) { page(batch, cum[i], 0); batch = []; size = 0; }
  });
  const total = pages.reduce((s, p) => s + p.length, 0), outb = new Uint8Array(total); let o = 0;
  for (const p of pages) { outb.set(p, o); o += p.length; }
  const back = await new OfflineAudioContext(1, 1, 48000).decodeAudioData(outb.buffer.slice(0));
  return { ogg: outb, frames, back: back.length, ch };
}
(async () => {
  const names = await (await fetch('/list')).json();
  for (const n of names) {
    try {
      const r = await encode(await (await fetch('/wav/' + n)).arrayBuffer());
      await fetch(`/ogg/${n}?frames=${r.frames}&back=${r.back}&ch=${r.ch}`, { method: 'POST', body: r.ogg });
    } catch (e) { await fetch('/err/' + n, { method: 'POST', body: String(e) }); }
  }
  await fetch('/done', { method: 'POST' });
})();
</script>"""


def main():
    names = [l.strip() for l in open(sys.argv[1]) if re.fullmatch(r"sfx_[\w]+\.wav", l.strip())
             and os.path.exists(os.path.join(ASSETS, l.strip()))]
    done = threading.Event()
    stats = {"wav": 0, "ogg": 0, "bad": []}

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype):
            self.send_response(200); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self._send(PAGE.encode(), "text/html")
            elif self.path == "/list":
                self._send(json.dumps(names).encode(), "application/json")
            elif self.path.startswith("/wav/") and self.path[5:] in names:
                self._send(open(os.path.join(ASSETS, self.path[5:]), "rb").read(), "audio/wav")
            else:
                self.send_response(404); self.end_headers()

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            p, _, q = self.path.partition("?")
            if p.startswith("/ogg/") and p[5:] in names:
                n = p[5:]
                a = dict(kv.split("=") for kv in q.split("&"))
                out = os.path.join(ASSETS, n[:-4] + ".ogg")
                open(out, "wb").write(body)
                w = os.path.getsize(os.path.join(ASSETS, n))
                stats["wav"] += w; stats["ogg"] += len(body)
                bad = abs(int(a["back"]) - int(a["frames"])) > 2
                if bad:
                    stats["bad"].append(n)
                print(f"{n:30s} {w:8d} -> {len(body):7d} B  {a['ch']}ch frames {a['frames']} decoded {a['back']}"
                      f"{'  <-- LENGTH MISMATCH' if bad else ''}", flush=True)
            elif p.startswith("/err/"):
                stats["bad"].append(p[5:]); print(f"{p[5:]}: ERROR {body[:300]!r}", flush=True)
            elif p == "/done":
                done.set()
            self._send(b"ok", "text/plain")

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    exe = next(b for b in BROWSERS if os.path.exists(b))
    prof = tempfile.mkdtemp(prefix="opusenc_")
    br = subprocess.Popen([exe, "--headless=new", f"--user-data-dir={prof}", "--no-first-run", "--no-default-browser-check",
                           "--disable-extensions", f"http://127.0.0.1:{port}/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = done.wait(600)
    br.kill(); srv.shutdown()
    print(f"{len(names)} files, {'done' if ok else 'TIMED OUT'}; {stats['wav'] / 1048576:.2f} MB WAV -> "
          f"{stats['ogg'] / 1048576:.2f} MB Opus; problems: {stats['bad'] or 'none'}")


if __name__ == "__main__":
    main()
