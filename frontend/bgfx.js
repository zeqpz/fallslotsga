// The living background (Tipsy Harvest): the painted farm (assets/bonus_wall.webp) redrawn on one
// WebGL canvas inside #bgwall, pixel-aligned with the CSS background underneath (which stays as the
// loading / no-WebGL fallback), with
//   - the trees swaying in the wind, the lake rippling with glints on the sun's streak, the sun's
//     glow breathing and a faint heat shimmer at its edge: ONE fragment pass over the picture,
//     driven by an offline mask (assets/bg/bg_mask.webp: R wind weight, G water, B sun/streak;
//     built by tools/fall/bg/make_bg_masks.py, which holds the image coordinates used below);
//   - falling leaves from the two big canopies and smoke from the village chimneys: one batched
//     quad pass from a 512x128 atlas (assets/bg/bg_fx.webp), pooled, no per-frame allocation.
// The painting it draws is the back plate (2026-11-08): the airborne painted leaves are painted out
// (tools/fall/bg/clean_leaves.py) and the big foreground pumpkins / vines / hay bale are cut out to
// their own still layer, #fgwall in index.html, outside the camera (tools/fall/bg/cut_foreground.py),
// with the field painted in behind them - so nothing here moves them; the mask's wind is 0 there.
// 30 fps (plenty for wind), nothing while the tab is hidden, a single still frame under
// prefers-reduced-motion. window.BGFX = { pause(), resume(), setWind(k), setFps(n), bench(n), stats }.
(() => {
  "use strict";
  const IW = 3840, IH = 2160;
  const IMG = "assets/bonus_wall.webp", MASK = "assets/bg/bg_mask.webp", FXA = "assets/bg/bg_fx.webp";
  const TINT = [40 / 255, 18 / 255, 6 / 255], TA0 = 0.06, TA1 = 0.26;   // #bgwall's gradient, top -> bottom
  // 30 fps; if the whole page is struggling (every 30 fps repaint of this full-screen canvas makes
  // the compositor redraw every layer above it), drop to 20 fps - see adapt()
  let FRAME = 1000 / 30;
  const MAX_RES = 1.5;                       // soft painted art: no need for DPR 2-3
  const REDUCED = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- the painting's features, in its own pixels (see make_bg_masks.py) --------------------
  const CANOPIES = [   // leaves fall from here: [x0, y0, x1, y1]
    [260, 60, 960, 470], [2700, 40, 3760, 330],
  ];
  const CHIMNEYS = [[2357, 634], [2535, 628], [3053, 640]];
  const N_LEAF = 24, N_SMOKE = 80, N_MAX = N_LEAF + N_SMOKE;

  // ---- shaders ----------------------------------------------------------------------------
  const VS_BG = `
attribute vec2 aPos;
varying vec2 vBox;
void main() { vBox = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5); gl_Position = vec4(aPos, 0.0, 1.0); }`;
  const FS_BG = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 vBox;
uniform sampler2D uImg, uMask;
uniform vec4 uFit;        // box uv -> image uv: uv = vBox * uFit.xy + uFit.zw
uniform float uT, uWind, uPulse;
uniform vec3 uTint;
uniform vec2 uTintA;
const vec2 ISZ = vec2(3840.0, 2160.0);
float h11(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float n1(float x) { float i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f); return mix(h11(i), h11(i + 1.0), f); }
float h21(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float n2(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h21(i), h21(i + vec2(1.0, 0.0)), f.x), mix(h21(i + vec2(0.0, 1.0)), h21(i + vec2(1.0, 1.0)), f.x), f.y);
}
void main() {
  vec2 uv = vBox * uFit.xy + uFit.zw;
  float ta = mix(uTintA.x, uTintA.y, vBox.y);
  if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) { gl_FragColor = vec4(uTint * ta, ta); return; }
  vec2 p = uv * ISZ;
  vec3 m = texture2D(uMask, uv).rgb;
  vec2 d = vec2(0.0);
  // wind: coherent low-frequency sway, gusts rolling across from the left; tips move, trunks don't
  if (m.r > 0.003) {
    float big = (1.0 - smoothstep(560.0, 700.0, p.y)) * clamp(1.0 - smoothstep(1000.0, 1150.0, p.x) + smoothstep(2500.0, 2650.0, p.x), 0.0, 1.0);
    float s = uT * 0.30 - p.x / 2600.0;
    float g = n1(s) * 0.65 + n1(s * 2.3 + 17.0) * 0.35;
    float k = uWind * (0.35 + 0.85 * g * g);
    float tt = uT * mix(1.45, 0.8, big);
    vec2 q = p / 900.0;
    float sx = sin(tt + q.x * 1.7 + q.y * 2.3) * 0.55 + sin(tt * 1.73 + q.y * 3.1 - q.x * 1.1) * 0.3 + sin(tt * 2.9 + q.x * 4.3 + q.y * 3.7) * 0.15;
    float sy = sin(tt * 1.31 + q.x * 2.2 - q.y * 1.4) * 0.6 + sin(tt * 2.3 + q.y * 3.3) * 0.4;
    d += m.r * k * mix(3.5, 6.0, big) * vec2(sx + 0.6 * g, 0.4 * sy);
  }
  // water: a slow horizontal ripple of the painted streaks, only inside the lake
  float ph = p.y * 0.11 - uT * 1.25 + sin(p.x * 0.006 + uT * 0.4) * 2.0;
  if (m.g > 0.003) {
    d.x += m.g * 1.7 * sin(ph);
    d.y += m.g * 0.5 * sin(p.x * 0.013 + uT * 0.9 + p.y * 0.03);
  }
  // the sun: a faint heat shimmer at the disc's edge, just above the horizon
  float sky = m.b * (1.0 - m.g) * step(p.y, 776.0);
  d.x += sky * smoothstep(640.0, 770.0, p.y) * 0.9 * sin(p.y * 0.21 - uT * 2.2);
  vec3 col = texture2D(uImg, uv - d / ISZ).rgb;
  // its glow breathing (uPulse 0..1, slow)
  col += vec3(1.0, 0.70, 0.36) * sky * sky * (0.03 + 0.05 * uPulse);
  // the water's sheen moving with the ripple, and glints on the sun's streak
  if (m.g > 0.003) {
    col *= 1.0 + m.g * 0.035 * sin(ph * 0.5 + 1.3);
    float gl = m.b * m.g;
    if (gl > 0.01) {
      vec2 gq = vec2(p.x * 0.05 + uT * 0.22, p.y * 0.17);
      float n = n2(gq) * n2(gq * 1.63 + vec2(-uT * 0.41, uT * 0.23));
      col += vec3(1.0, 0.88, 0.62) * gl * smoothstep(0.30, 0.62, n) * (0.35 + 0.25 * uPulse);
    }
  }
  col = mix(col, uTint, ta);
  gl_FragColor = vec4(col, 1.0);
}`;
  const VS_FX = `
attribute vec2 aPos;    // box css px
attribute vec2 aUV;
attribute vec2 aCol;    // alpha, shade
uniform vec2 uBox;
varying vec2 vUV; varying vec2 vCol; varying float vY;
void main() {
  vUV = aUV; vCol = aCol; vY = aPos.y / uBox.y;
  gl_Position = vec4(aPos.x / uBox.x * 2.0 - 1.0, 1.0 - aPos.y / uBox.y * 2.0, 0.0, 1.0);
}`;
  const FS_FX = `
precision mediump float;
uniform sampler2D uFx;
uniform vec3 uTint;
uniform vec2 uTintA;
varying vec2 vUV; varying vec2 vCol; varying float vY;
void main() {
  vec4 c = texture2D(uFx, vUV);              // premultiplied
  c.rgb *= vCol.y;
  c *= vCol.x;
  float ta = mix(uTintA.x, uTintA.y, clamp(vY, 0.0, 1.0));
  c.rgb = c.rgb * (1.0 - ta) + uTint * ta * c.a;
  gl_FragColor = c;
}`;

  // ---- state ------------------------------------------------------------------------------
  let wall = null, cv = null, gl = null, bgP = null, fxP = null, quadBuf = null, fxBuf = null, idxBuf = null;
  let texImg = null, texMask = null, texFx = null, texW = 0;
  let imgEl = null, maskEl = null, fxEl = null;
  let W = 0, H = 0, res = 1, sc = 1, ox = 0, oy = 0, contain = false;
  let ready = false, paused = false, raf = 0, next = 0, lastT = 0, simT = 0;
  let wind = 1, windTarget = 1, building = false, shown = false;
  const stats = { frames: 0, cpuMs: 0, lastCpuMs: 0, res: 0, texW: 0, w: 0, h: 0, fps: 30, pageFps: 0 };
  let fixedFps = 0, winT = 0, winN = 0, good = 0, drops = 0;

  // particles, as flat typed arrays (no objects per particle)
  const L = {   // leaves
    n: 0, alive: new Uint8Array(N_LEAF), x: new Float32Array(N_LEAF), y: new Float32Array(N_LEAF),
    vx: new Float32Array(N_LEAF), vy: new Float32Array(N_LEAF), ph: new Float32Array(N_LEAF), fq: new Float32Array(N_LEAF),
    amp: new Float32Array(N_LEAF), rot: new Float32Array(N_LEAF), spin: new Float32Array(N_LEAF), flip: new Float32Array(N_LEAF),
    flipV: new Float32Array(N_LEAF), size: new Float32Array(N_LEAF), kind: new Uint8Array(N_LEAF), age: new Float32Array(N_LEAF),
    yEnd: new Float32Array(N_LEAF), depth: new Float32Array(N_LEAF),
  };
  const S = {   // smoke puffs
    alive: new Uint8Array(N_SMOKE), x: new Float32Array(N_SMOKE), y: new Float32Array(N_SMOKE), vx: new Float32Array(N_SMOKE),
    vy: new Float32Array(N_SMOKE), age: new Float32Array(N_SMOKE), life: new Float32Array(N_SMOKE), s0: new Float32Array(N_SMOKE),
    s1: new Float32Array(N_SMOKE), rot: new Float32Array(N_SMOKE), spin: new Float32Array(N_SMOKE), a: new Float32Array(N_SMOKE),
    sway: new Float32Array(N_SMOKE),
  };
  const smokeTimer = new Float32Array(CHIMNEYS.length);
  let leafTimer = 0;
  const VERT = new Float32Array(N_MAX * 4 * 6);
  const rnd = (a, b) => a + Math.random() * (b - a);

  // the same gust as the shader's (n1), so leaves ride the wind the trees bend in
  const h11 = p => { p = (p * 0.1031) % 1; if (p < 0) p += 1; p *= p + 33.33; p *= p + p; return p % 1; };
  function n1(x) { const i = Math.floor(x); let f = x - i; f = f * f * (3 - 2 * f); const a = h11(i), b = h11(i + 1); return a + (b - a) * f; }
  function gust(t, x) { const s = t * 0.30 - x / 2600; return n1(s) * 0.65 + n1(s * 2.3 + 17) * 0.35; }

  // ---- GL setup -----------------------------------------------------------------------------
  function sh(type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error("bgfx shader: " + gl.getShaderInfoLog(s));
    return s;
  }
  function prog(vs, fs, attrs) {
    const p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
    attrs.forEach((a, i) => gl.bindAttribLocation(p, i, a));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error("bgfx link: " + gl.getProgramInfoLog(p));
    const u = {}, n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const nm = gl.getActiveUniform(p, i).name; u[nm] = gl.getUniformLocation(p, nm); }
    return { p, u };
  }
  function tex(src, premult, data) {
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, !!premult);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, data ? gl.NONE : gl.BROWSER_DEFAULT_WEBGL);
    gl.texImage2D(gl.TEXTURE_2D, 0, premult ? gl.RGBA : gl.RGB, premult ? gl.RGBA : gl.RGB, gl.UNSIGNED_BYTE, src);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  function initGL() {
    bgP = prog(VS_BG, FS_BG, ["aPos"]);
    fxP = prog(VS_FX, FS_FX, ["aPos", "aUV", "aCol"]);
    quadBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    fxBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, fxBuf);
    gl.bufferData(gl.ARRAY_BUFFER, VERT.byteLength, gl.DYNAMIC_DRAW);
    const idx = new Uint16Array(N_MAX * 6);
    for (let i = 0; i < N_MAX; i++) idx.set([i * 4, i * 4 + 1, i * 4 + 2, i * 4 + 2, i * 4 + 1, i * 4 + 3], i * 6);
    idxBuf = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
    gl.disable(gl.DEPTH_TEST);
    texMask = tex(maskEl, false, true);
    texFx = tex(fxEl, true);
    gl.useProgram(bgP.p); gl.uniform1i(bgP.u.uImg, 0); gl.uniform1i(bgP.u.uMask, 1);
    gl.uniform3fv(bgP.u.uTint, TINT); gl.uniform2f(bgP.u.uTintA, TA0, TA1);
    gl.useProgram(fxP.p); gl.uniform1i(fxP.u.uFx, 2);
    gl.uniform3fv(fxP.u.uTint, TINT); gl.uniform2f(fxP.u.uTintA, TA0, TA1);
  }

  // The painting at about the size it is shown (no mipmaps in WebGL1 for a 3840x2160 texture, so
  // a big downscale would alias where CSS resamples smoothly). Off-thread when the browser can.
  async function uploadImage(wantW) {
    building = true;
    try {
      const w = Math.min(IW, Math.max(256, Math.ceil(wantW)));   // ~1:1 with the screen
      let src = imgEl;
      if (w < IW * 0.92) {
        const h = Math.round(w * IH / IW);
        try { src = await createImageBitmap(imgEl, { resizeWidth: w, resizeHeight: h, resizeQuality: "high" }); }
        catch (e) {
          const c = document.createElement("canvas"); c.width = w; c.height = h;
          const x = c.getContext("2d"); x.imageSmoothingQuality = "high"; x.drawImage(imgEl, 0, 0, w, h); src = c;
        }
      }
      if (!gl || gl.isContextLost()) return;
      const max = gl.getParameter(gl.MAX_TEXTURE_SIZE);
      if ((src.width || IW) > max) {
        const c = document.createElement("canvas"); c.width = max; c.height = Math.round(max * IH / IW);
        c.getContext("2d").drawImage(imgEl, 0, 0, c.width, c.height); src = c;
      }
      if (texImg) gl.deleteTexture(texImg);
      texImg = tex(src, false);
      texW = src.width || IW;
      if (src.close) src.close();
      stats.texW = texW;
    } finally { building = false; }
  }

  // ---- layout: #bgwall's box, the CSS `center / cover` fit ---------------------------------
  function layout(w, h) {
    if (!(w > 0 && h > 0)) return;
    W = w; H = h;
    const bs = getComputedStyle(wall).backgroundSize || "";
    contain = /contain/.test(bs) && !/cover/.test(bs.split(",").pop());
    sc = contain ? Math.min(W / IW, H / IH) : Math.max(W / IW, H / IH);
    ox = (W - IW * sc) / 2; oy = (H - IH * sc) / 2;
    const dpr = window.devicePixelRatio || 1;
    res = Math.min(dpr, MAX_RES, Math.max(1, 1 / sc));       // never denser than the painting itself
    const bw = Math.max(1, Math.round(W * res)), bh = Math.max(1, Math.round(H * res));
    if (cv.width !== bw || cv.height !== bh) { cv.width = bw; cv.height = bh; }
    stats.res = res; stats.w = bw; stats.h = bh;
    const want = IW * sc * res;
    if (ready && !building && texW < IW && want > texW * 1.12) uploadImage(want).then(() => drawStill());
    if (ready) drawStill();
  }
  function drawStill() { if (ready && (REDUCED || paused || document.hidden)) render(0); }

  // ---- particles ----------------------------------------------------------------------------
  const VR = new Float32Array(4);
  function visRect() {   // the painting's visible part, in its pixels
    VR[0] = -ox / sc; VR[1] = -oy / sc; VR[2] = (W - ox) / sc; VR[3] = (H - oy) / sc;
    return VR;
  }
  function spawnLeaf(i, warm) {
    const v = visRect();
    // canopies in (or just off, upwind) the view; else leaves come in over the top of the view
    let wl = 0, wr = 0;
    const c0 = CANOPIES[0], c1 = CANOPIES[1];
    if (c0[2] > v[0] - 900 && c0[0] < v[2] && c0[1] < v[3]) wl = 1;
    if (c1[2] > v[0] - 200 && c1[0] < v[2] + 100 && c1[1] < v[3]) wr = 1.15;
    let x, y;
    const r = Math.random() * (wl + wr + 0.12);
    if (wl + wr > 0 && r < wl + wr) {
      const c = r < wl ? c0 : c1;
      x = rnd(c[0], c[2]); y = rnd(c[1], c[3]);
    } else {
      x = rnd(v[0] - 500, v[2] - 300); y = v[1] - rnd(40, 160);
    }
    const d = Math.pow(Math.random(), 0.8) * 0.6 + 0.55;      // depth 0.55 (far, small, slow) .. 1.15
    L.alive[i] = 1; L.x[i] = x; L.y[i] = y; L.depth[i] = d;
    L.vx[i] = 20; L.vy[i] = (40 + 45 * d) * rnd(0.85, 1.15);
    L.ph[i] = rnd(0, 6.283); L.fq[i] = rnd(1.1, 2.0); L.amp[i] = rnd(22, 46) * d;
    L.rot[i] = rnd(-3.14, 3.14); L.spin[i] = rnd(-0.7, 0.7); L.flip[i] = rnd(0, 6.283); L.flipV[i] = rnd(1.4, 3.6) * (Math.random() < 0.5 ? -1 : 1);
    L.size[i] = (50 + 42 * d) * 128 / 96; L.kind[i] = (Math.random() * 3) | 0;
    L.age[i] = warm ? rnd(0, 3) : 0;
    L.yEnd[i] = Math.min(v[3] + 100, rnd(1150, 2000));
  }
  function spawnPuff(c) {
    for (let i = 0; i < N_SMOKE; i++) {
      if (S.alive[i]) continue;
      const ch = CHIMNEYS[c];
      // the stream's sideways lean when this puff leaves the chimney: puffs keep it as they rise,
      // so the column curls in a slow S that climbs, like the painted wisps
      const sway = Math.sin(simT * 0.9 + c * 2.1) * 0.65 + Math.sin(simT * 0.37 + c) * 0.35;
      S.alive[i] = 1; S.x[i] = ch[0] + rnd(-1.5, 1.5); S.y[i] = ch[1] + rnd(-1, 1); S.sway[i] = sway;
      S.vx[i] = rnd(1, 3); S.vy[i] = -rnd(30, 36); S.age[i] = 0; S.life[i] = rnd(4.6, 5.8);
      S.s0[i] = rnd(11, 15); S.s1[i] = rnd(64, 84); S.rot[i] = rnd(0, 6.28); S.spin[i] = rnd(-0.3, 0.3);
      S.a[i] = rnd(0.34, 0.44);
      return;
    }
  }
  function step(dt) {
    simT += dt;
    wind += (windTarget - wind) * Math.min(1, dt * 0.8);
    // leaves
    let n = 0;
    for (let i = 0; i < N_LEAF; i++) if (L.alive[i]) n++;
    leafTimer -= dt;
    if (n < N_LEAF && leafTimer <= 0) {
      for (let i = 0; i < N_LEAF; i++) if (!L.alive[i]) { spawnLeaf(i, false); break; }
      leafTimer = rnd(0.25, 0.75) * (n < N_LEAF * 0.6 ? 0.6 : 1.2);
    }
    for (let i = 0; i < N_LEAF; i++) {
      if (!L.alive[i]) continue;
      const d = L.depth[i], g = gust(simT, L.x[i]);
      const vxT = (25 + 150 * g * g * wind) * d;
      L.vx[i] += (vxT - L.vx[i]) * Math.min(1, dt * 1.2);
      L.ph[i] += dt * L.fq[i];
      const sw = Math.sin(L.ph[i]);
      L.x[i] += (L.vx[i] + L.amp[i] * Math.cos(L.ph[i]) * L.fq[i]) * dt;
      L.y[i] += L.vy[i] * (0.55 + 0.45 * Math.abs(sw)) * dt;
      L.flip[i] += L.flipV[i] * dt * (0.7 + 0.6 * g);
      L.rot[i] += L.spin[i] * dt;
      L.age[i] += dt;
      if (L.y[i] > L.yEnd[i] || L.x[i] > IW + 300) L.alive[i] = 0;
    }
    // smoke
    for (let c = 0; c < CHIMNEYS.length; c++) {
      smokeTimer[c] -= dt;
      if (smokeTimer[c] <= 0) { spawnPuff(c); smokeTimer[c] = rnd(0.19, 0.25); }
    }
    for (let i = 0; i < N_SMOKE; i++) {
      if (!S.alive[i]) continue;
      const u = S.age[i] / S.life[i], g = gust(simT, S.x[i]);
      S.x[i] += (S.vx[i] + (6 + 30 * g * wind) * u + S.sway[i] * 9 * (1 - u)) * dt;
      S.y[i] += S.vy[i] * (1 - 0.4 * u) * dt;
      S.rot[i] += S.spin[i] * dt;
      S.age[i] += dt;
      if (S.age[i] >= S.life[i]) S.alive[i] = 0;
    }
  }
  function sstep(a, b, x) { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); }
  let vn = 0;
  function quad(cx, cy, hw, hh, rot, u0, alpha, shade) {
    const c = Math.cos(rot), s = Math.sin(rot);
    const ax = c * hw, ay = s * hw, bx = -s * hh, by = c * hh;
    let o = vn * 24;
    // corners: (-,-) (+,-) (-,+) (+,+)
    VERT[o++] = cx - ax - bx; VERT[o++] = cy - ay - by; VERT[o++] = u0; VERT[o++] = 0; VERT[o++] = alpha; VERT[o++] = shade;
    VERT[o++] = cx + ax - bx; VERT[o++] = cy + ay - by; VERT[o++] = u0 + 0.25; VERT[o++] = 0; VERT[o++] = alpha; VERT[o++] = shade;
    VERT[o++] = cx - ax + bx; VERT[o++] = cy - ay + by; VERT[o++] = u0; VERT[o++] = 1; VERT[o++] = alpha; VERT[o++] = shade;
    VERT[o++] = cx + ax + bx; VERT[o++] = cy + ay + by; VERT[o++] = u0 + 0.25; VERT[o++] = 1; VERT[o++] = alpha; VERT[o++] = shade;
    vn++;
  }
  function buildFx() {
    vn = 0;
    for (let i = 0; i < N_SMOKE; i++) {     // smoke first: it is far, the leaves are near
      if (!S.alive[i]) continue;
      const u = S.age[i] / S.life[i];
      const a = S.a[i] * sstep(0, 0.12, u) * (1 - sstep(0.3, 1, u));
      if (a < 0.004) continue;
      const sz = (S.s0[i] + (S.s1[i] - S.s0[i]) * Math.sqrt(u)) * sc * 0.5;
      quad(S.x[i] * sc + ox, S.y[i] * sc + oy, sz, sz, S.rot[i], 0.75, a, 1);
    }
    for (let i = 0; i < N_LEAF; i++) {
      if (!L.alive[i]) continue;
      const a = sstep(0, 0.7, L.age[i]) * sstep(L.yEnd[i], L.yEnd[i] - 260, L.y[i]);
      if (a < 0.004) continue;
      const fc = Math.cos(L.flip[i]), hs = L.size[i] * sc * 0.5;
      const sw = Math.sin(L.ph[i]);
      const px = L.x[i] * sc + ox, py = L.y[i] * sc + oy;
      // quieter behind the reels: an ellipse round the middle of the screen dims them
      const ex = (px - W * 0.5) / (W * 0.3), ey = (py - H * 0.46) / (H * 0.4);
      const mid = 0.45 + 0.55 * sstep(0.55, 1.1, ex * ex + ey * ey);
      quad(px, py, hs * (Math.abs(fc) < 0.16 ? 0.16 * (fc < 0 ? -1 : 1) : fc), hs,
           L.rot[i] + 0.55 * sw, L.kind[i] * 0.25, a * mid, (0.7 + 0.3 * Math.abs(fc)) * (fc < 0 ? 0.86 : 1) * (0.88 + 0.12 * L.depth[i]));
    }
  }

  // ---- render -------------------------------------------------------------------------------
  function render(dt) {
    if (!ready || !texImg || gl.isContextLost()) return;
    const t0 = performance.now();
    if (dt > 0) step(dt);
    gl.viewport(0, 0, cv.width, cv.height);
    gl.disable(gl.BLEND);
    gl.useProgram(bgP.p);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texImg);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texMask);
    const dw = IW * sc, dh = IH * sc;
    gl.uniform4f(bgP.u.uFit, W / dw, H / dh, -ox / dw, -oy / dh);
    gl.uniform1f(bgP.u.uT, simT);
    gl.uniform1f(bgP.u.uWind, wind);
    gl.uniform1f(bgP.u.uPulse, 0.5 + 0.32 * Math.sin(simT * 0.52) + 0.18 * Math.sin(simT * 0.21 + 1.7));
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf);
    gl.enableVertexAttribArray(0); gl.disableVertexAttribArray(1); gl.disableVertexAttribArray(2);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (!REDUCED) {
      buildFx();
      if (vn) {
        gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
        gl.useProgram(fxP.p);
        gl.uniform2f(fxP.u.uBox, W, H);
        gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, texFx);
        gl.bindBuffer(gl.ARRAY_BUFFER, fxBuf);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, VERT.subarray(0, vn * 24));
        gl.enableVertexAttribArray(1); gl.enableVertexAttribArray(2);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 24, 0);
        gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 24, 8);
        gl.vertexAttribPointer(2, 2, gl.FLOAT, false, 24, 16);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
        gl.drawElements(gl.TRIANGLES, vn * 6, gl.UNSIGNED_SHORT, 0);
      }
    }
    const ms = performance.now() - t0;
    stats.frames++; stats.lastCpuMs = ms; stats.cpuMs += (ms - stats.cpuMs) * 0.05;
    if (!shown) {
      shown = true;
      requestAnimationFrame(() => { cv.style.transition = "opacity .9s ease"; cv.style.opacity = "1"; });
    }
  }
  function tick(now) {
    raf = 0;
    if (paused || document.hidden || !ready) return;
    raf = requestAnimationFrame(tick);
    adapt(now);
    if (now < next - 2.5) return;
    next += FRAME;
    if (now - next > FRAME) next = now + FRAME;
    const dt = Math.min(0.1, (now - lastT) / 1000);
    lastT = now;
    render(dt);
  }
  // the page's own frame rate over 3 s windows (every rAF, not just ours): under ~38 fps the scene
  // steps down to 20 fps; it goes back up only after ~9 s above 55, and stays down after two drops
  function adapt(now) {
    winN++;
    if (!winT) { winT = now; winN = 0; return; }
    if (now - winT < 3000) return;
    const fps = winN * 1000 / (now - winT);
    winT = now; winN = 0; stats.pageFps = Math.round(fps);
    if (fixedFps) return;
    if (stats.fps === 30 && fps < 38) { stats.fps = 20; FRAME = 1000 / 20; drops++; good = 0; }
    else if (stats.fps === 20 && drops < 2 && fps > 55) { if (++good >= 3) { stats.fps = 30; FRAME = 1000 / 30; good = 0; } }
    else good = 0;
  }
  function start() {
    if (raf || paused || REDUCED || !ready || document.hidden) return;
    winT = 0;
    lastT = next = performance.now();
    raf = requestAnimationFrame(tick);
  }
  function stop() { if (raf) cancelAnimationFrame(raf); raf = 0; }

  // ---- install --------------------------------------------------------------------------------
  function load(src) {
    // decode() can reject a big picture with EncodingError (seen on Chrome mobile emulation while
    // the game loads); the plain load event still gives a usable image then
    const im = new Image();
    const loaded = new Promise((r, j) => { im.onload = r; im.onerror = j; });
    im.decoding = "async"; im.src = src;
    const ok = () => im;
    if (!im.decode) return loaded.then(ok);
    return im.decode().then(ok, () => (im.complete && im.naturalWidth ? im : loaded.then(ok)));
  }
  async function install() {
    wall = document.getElementById("bgwall");
    if (!wall || cv) return;
    cv = document.createElement("canvas");
    cv.id = "bgfx";
    cv.setAttribute("aria-hidden", "true");
    cv.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%;display:block;pointer-events:none;opacity:0;";
    const opts = { alpha: true, premultipliedAlpha: true, antialias: false, depth: false, stencil: false,
                   preserveDrawingBuffer: false, powerPreference: "default" };
    gl = cv.getContext("webgl", opts) || cv.getContext("experimental-webgl", opts);
    if (!gl) { stats.err = "no webgl"; cv = null; return; }
    wall.insertBefore(cv, wall.firstChild);
    cv.addEventListener("webglcontextlost", e => { e.preventDefault(); ready = false; stop(); cv.style.transition = ""; cv.style.opacity = "0"; shown = false; });
    cv.addEventListener("webglcontextrestored", async () => {
      texImg = null; texW = 0;
      initGL(); await uploadImage(IW * sc * res); ready = true; render(0); start();
    });
    try {
      [imgEl, maskEl, fxEl] = await Promise.all([load(IMG), load(MASK), load(FXA)]);
    } catch (e) { stats.err = "load: " + e; cv.remove(); cv = null; return; }
    const r = wall.getBoundingClientRect();
    const cs = getComputedStyle(wall);
    layout(parseFloat(cs.width) || r.width, parseFloat(cs.height) || r.height);
    try { initGL(); } catch (e) { stats.err = "gl: " + e; console.warn(e); cv.remove(); cv = null; return; }
    await uploadImage(IW * sc * res);
    // a few seconds of leaves and smoke already in the air, so the scene never starts empty
    if (!REDUCED) {
      for (let i = 0; i < Math.round(N_LEAF * 0.55); i++) spawnLeaf(i, true);
      for (let k = 0; k < 120; k++) step(1 / 15);
    }
    ready = true;
    render(0);
    if (window.ResizeObserver) {
      new ResizeObserver(es => { const c = es[es.length - 1].contentRect; layout(c.width, c.height); }).observe(wall);
    } else {
      addEventListener("resize", () => { const s = getComputedStyle(wall); layout(parseFloat(s.width), parseFloat(s.height)); });
    }
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); else start(); });
    start();
  }

  window.BGFX = {
    pause() { paused = true; stop(); },
    resume() { paused = false; start(); },
    setWind(k) { windTarget = Math.max(0, +k || 0); },
    // pin the scene's frame rate (e.g. 30 or 20); 0 = adaptive (default)
    setFps(n) { fixedFps = Math.max(0, Math.min(60, +n || 0)); if (fixedFps) { stats.fps = fixedFps; FRAME = 1000 / fixedFps; } },
    stats,
    // n frames back to back, then one 1-pixel readback to wait them out: ~GPU + JS cost of one
    // frame in ms (debug only - the readback is exactly the stall the live loop never does)
    bench(n = 60) {
      if (!ready) return null;
      const px = new Uint8Array(4);
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      const t0 = performance.now();
      for (let i = 0; i < n; i++) render(1 / 30);
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);   // one sync for the lot
      return (performance.now() - t0) / n;
    },
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install);
  else install();
})();
