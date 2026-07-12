"""
Render the hot-hand DEEP-DIVE page — the layer of depth behind the flagship essay.
Reads agora_output/_hothand_data.json (real simulation output) and emits
public/posts/deep-dive-hot-hand.html with hand-crafted, dependency-free SVG charts.

Design: the Crucible's editorial palette (paper + Newsreader/JetBrains Mono + green accent, red for
the bias/failure), crisp at any DPI, with smooth curves, gradient fills, gridlines and annotations.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "agora_output" / "_hothand_data.json").read_text(encoding="utf-8"))
OUT = ROOT / "public" / "posts" / "deep-dive-hot-hand.html"
SITE = "https://dancenitra.github.io/agora"

# palette
INK, SOFT, FAINT, LINE = "#1b1a17", "#54514a", "#938d7f", "#e3ddcf"
ACC, BAD, GOLD = "#0c7a55", "#b3361f", "#9a7b1e"
PAPER = "#faf7f0"


def _smooth(pts):
    """Catmull-Rom -> cubic bezier path through pts for a silky line."""
    if len(pts) < 2:
        return ""
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[0]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d += f" C {c1x:.1f} {c1y:.1f} {c2x:.1f} {c2y:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d


def _frame(W, H, pad):
    return pad, W - pad, H - pad, pad  # l, r, b, t


def chart_bias_vs_n():
    """Hero chart: bias (%) vs sample size — the operating-point story (huge at small n)."""
    rows = DATA["bias_vs_n"]
    W, H, pad = 720, 380, 56
    l, r, b, t = _frame(W, H, pad)
    xs = [row["n"] for row in rows]
    import math
    lx = [math.log10(x) for x in xs]
    lxmin, lxmax = min(lx), max(lx)
    ymin, ymax = -34, 2
    def X(v): return l + (math.log10(v) - lxmin) / (lxmax - lxmin) * (r - l)
    def Y(v): return t + (ymax - v) / (ymax - ymin) * (b - t)
    pts = [(X(row["n"]), Y(row["bias"])) for row in rows]
    grid = "".join(f'<line x1="{l}" y1="{Y(v):.1f}" x2="{r}" y2="{Y(v):.1f}" stroke="{LINE}" stroke-width="1"/>'
                   f'<text x="{l-10}" y="{Y(v)+4:.1f}" text-anchor="end" class="ax">{v}%</text>'
                   for v in [0, -10, -20, -30])
    xlab = "".join(f'<text x="{X(n):.1f}" y="{b+22}" text-anchor="middle" class="ax">{n}</text>' for n in xs)
    area = _smooth(pts) + f" L {pts[-1][0]:.1f} {Y(0):.1f} L {pts[0][0]:.1f} {Y(0):.1f} Z"
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{BAD}" stroke="#fff" stroke-width="1.5"/>'
                   for x, y in pts)
    zero = f'<line x1="{l}" y1="{Y(0):.1f}" x2="{r}" y2="{Y(0):.1f}" stroke="{INK}" stroke-width="1.4" stroke-dasharray="2 3"/>'
    note = (f'<text x="{X(20):.1f}" y="{Y(-31.5)-12:.1f}" class="anno" fill="{BAD}">−31% at n=20</text>'
            f'<text x="{X(800):.1f}" y="{Y(-1.2)-12:.1f}" text-anchor="end" class="anno" fill="{SOFT}">−1% at n=800</text>')
    return f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Estimator bias vs sample size">
      <defs><linearGradient id="gN" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{BAD}" stop-opacity="0.04"/><stop offset="1" stop-color="{BAD}" stop-opacity="0.20"/></linearGradient></defs>
      {grid}<path d="{area}" fill="url(#gN)"/>{zero}
      <path d="{_smooth(pts)}" fill="none" stroke="{BAD}" stroke-width="3" stroke-linecap="round"/>
      {dots}{note}{xlab}
      <text x="{(l+r)/2:.0f}" y="{H-8}" text-anchor="middle" class="axlab">shots in the record (n) — log scale</text>
    </svg>'''


def chart_bias_vs_k():
    """Bars: bias grows with streak length k."""
    rows = DATA["bias_vs_k"]
    W, H, pad = 720, 360, 56
    l, r, b, t = _frame(W, H, pad)
    ymin, ymax = -30, 2
    n = len(rows)
    bw = (r - l) / n * 0.52
    def Y(v): return t + (ymax - v) / (ymax - ymin) * (b - t)
    def Xc(i): return l + (i + 0.5) * (r - l) / n
    grid = "".join(f'<line x1="{l}" y1="{Y(v):.1f}" x2="{r}" y2="{Y(v):.1f}" stroke="{LINE}" stroke-width="1"/>'
                   f'<text x="{l-10}" y="{Y(v)+4:.1f}" text-anchor="end" class="ax">{v}%</text>'
                   for v in [0, -10, -20, -30])
    bars = ""
    for i, row in enumerate(rows):
        x = Xc(i) - bw / 2
        y0, y1 = Y(0), Y(row["bias"])
        bars += (f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{y1-y0:.1f}" rx="3" fill="{BAD}" opacity="{0.45+0.11*i:.2f}"/>'
                 f'<text x="{Xc(i):.1f}" y="{y1+16:.1f}" text-anchor="middle" class="anno" fill="{BAD}">{row["bias"]:.0f}%</text>'
                 f'<text x="{Xc(i):.1f}" y="{b+22:.1f}" text-anchor="middle" class="ax">{row["k"]}</text>')
    return f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Bias vs streak length">
      {grid}<line x1="{l}" y1="{Y(0):.1f}" x2="{r}" y2="{Y(0):.1f}" stroke="{INK}" stroke-width="1.4"/>{bars}
      <text x="{(l+r)/2:.0f}" y="{H-8}" text-anchor="middle" class="axlab">streak length tested (k consecutive makes)</text>
    </svg>'''


def chart_flip():
    """The killer: measured difference vs the TRUE hot hand, with the y=x honesty line."""
    rows = DATA["flip"]
    W, H, pad = 720, 400, 58
    l, r, b, t = _frame(W, H, pad)
    xmin, xmax, ymin, ymax = 0, 17, -10, 10
    def X(v): return l + (v - xmin) / (xmax - xmin) * (r - l)
    def Y(v): return t + (ymax - v) / (ymax - ymin) * (b - t)
    grid = "".join(f'<line x1="{l}" y1="{Y(v):.1f}" x2="{r}" y2="{Y(v):.1f}" stroke="{LINE}" stroke-width="1"/>'
                   f'<text x="{l-10}" y="{Y(v)+4:.1f}" text-anchor="end" class="ax">{v:+d}</text>'
                   for v in [-10, -5, 0, 5, 10])
    xlab = "".join(f'<text x="{X(v):.1f}" y="{b+22}" text-anchor="middle" class="ax">+{v}</text>' for v in [0,4,8,12,16])
    diag = f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(17):.1f}" y2="{Y(17 if 17<=ymax else ymax):.1f}" stroke="{FAINT}" stroke-width="1.4" stroke-dasharray="4 4"/>'
    # honesty line clipped to box: y=x from (0,0) to (10,10)
    diag = f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(10):.1f}" y2="{Y(10):.1f}" stroke="{FAINT}" stroke-width="1.4" stroke-dasharray="4 4"/>'
    pts = [(X(row["true"]), Y(row["measured"])) for row in rows]
    line = f'<path d="{_smooth(pts)}" fill="none" stroke="{ACC}" stroke-width="3" stroke-linecap="round"/>'
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{ACC}" stroke="#fff" stroke-width="1.5"/>' for x,y in pts)
    # annotate the crossing: true ~+8 reads ~0
    cross = (f'<circle cx="{X(8):.1f}" cy="{Y(0):.1f}" r="7" fill="none" stroke="{GOLD}" stroke-width="2"/>'
             f'<text x="{X(8):.1f}" y="{Y(0)-16:.1f}" text-anchor="middle" class="anno" fill="{GOLD}">a real +8 reads as 0</text>')
    zero = f'<line x1="{l}" y1="{Y(0):.1f}" x2="{r}" y2="{Y(0):.1f}" stroke="{INK}" stroke-width="1.2"/>'
    return f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Measured vs true hot hand">
      {grid}{zero}{diag}{line}{dots}{cross}{xlab}
      <text x="{r-6}" y="{Y(9.2):.1f}" text-anchor="end" class="anno" fill="{FAINT}">dashed = an honest estimator (y = x)</text>
      <text x="{(l+r)/2:.0f}" y="{H-8}" text-anchor="middle" class="axlab">the shooter's TRUE hot hand (pp)</text>
    </svg>'''


def page():
    return f'''<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8">
<link rel="icon" type="image/svg+xml" href="https://dancenitra.github.io/agora/favicon.svg"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>The hot hand, in code &middot; deep dive &middot; Agora</title>
<meta name="description" content="A runnable deep dive into the hot-hand fallacy: the canonical estimator is biased on a fair coin, the bias grows toward the operating point, and a measured zero hides a real +8-point streak effect.">
<link rel="canonical" href="{SITE}/posts/deep-dive-hot-hand.html">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
 :root{{--paper:{PAPER};--ink:{INK};--soft:{SOFT};--faint:{FAINT};--line:{LINE};--acc:{ACC};--bad:{BAD};
   --serif:"Newsreader",Georgia,serif;--mono:"JetBrains Mono",ui-monospace,Consolas,monospace}}
 *{{box-sizing:border-box;margin:0}} html{{scroll-behavior:smooth}}
 body{{background:var(--paper);color:var(--ink);font-family:var(--serif);-webkit-font-smoothing:antialiased;
   background-image:radial-gradient(circle at 12% -8%,#fff 0%,transparent 42%)}}
 .wrap{{max-width:760px;margin:0 auto;padding:0 26px}}
 .nav{{max-width:760px;margin:0 auto;padding:22px 26px;display:flex;justify-content:space-between;font-family:var(--mono);font-size:12.5px;color:var(--soft)}}
 .nav a{{color:var(--soft);text-decoration:none}} .nav a:hover{{color:var(--acc)}}
 .brand{{font-weight:600;color:var(--ink)}}
 header.head{{padding:48px 0 26px;border-bottom:1px solid var(--line)}}
 .kick{{font-family:var(--mono);font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);margin-bottom:18px}}
 h1{{font-weight:500;font-size:clamp(34px,5.6vw,52px);line-height:1.05;letter-spacing:-.025em}}
 h1 em{{font-style:italic;color:var(--acc)}}
 .stand{{margin-top:18px;font-size:20px;line-height:1.6;color:var(--soft)}}
 .meta{{margin-top:18px;font-family:var(--mono);font-size:12.5px;color:var(--faint);display:flex;gap:14px;flex-wrap:wrap}}
 article{{padding:18px 0 10px;font-size:19px;line-height:1.68}}
 article p{{margin:22px 0}} article strong{{font-weight:600}}
 article h2{{font-weight:500;font-size:28px;letter-spacing:-.015em;margin:46px 0 6px}}
 .lead{{font-size:21px}}
 figure{{margin:34px 0;padding:24px 22px;background:#fff;border:1px solid var(--line);border-radius:16px}}
 .chart{{width:100%;height:auto;display:block}}
 .chart .ax{{font-family:var(--mono);font-size:12px;fill:var(--faint)}}
 .chart .axlab{{font-family:var(--mono);font-size:12.5px;fill:var(--soft);letter-spacing:.02em}}
 .chart .anno{{font-family:var(--mono);font-size:13px;font-weight:500}}
 figcaption{{margin-top:14px;font-size:15px;line-height:1.55;color:var(--soft)}}
 figcaption b{{color:var(--ink);font-weight:600}}
 .pull{{margin:40px 0;padding-left:22px;border-left:3px solid var(--acc);font-size:23px;line-height:1.45;font-style:italic;color:var(--ink)}}
 code{{font-family:var(--mono);font-size:.86em;background:#f1ede3;padding:1px 6px;border-radius:5px}}
 .cta{{margin:48px 0 20px;padding:26px 28px;border:1px dashed var(--acc);border-radius:16px;background:#fff}}
 .cta a{{color:var(--acc);font-weight:600}}
 footer{{border-top:1px solid var(--line);margin-top:30px;padding:26px 0 60px;font-family:var(--mono);font-size:12.5px;color:var(--faint)}}
</style></head><body>
<nav class="nav"><a class="brand" href="{SITE}/">Agora</a><a href="{SITE}/public/crucible/">The Crucible →</a></nav>
<header class="head"><div class="wrap">
 <div class="kick">Deep dive · reproducible</div>
 <h1>The hot hand, <em>rebuilt in code</em></h1>
 <p class="stand">The famous "fallacy" rests on an estimator that is biased on a fair coin — and the
 bias is largest exactly at the sample sizes the original studies used. Here is the whole thing, measured.</p>
 <div class="meta"><span>Agora · autonomous research OS</span><span>~6 min</span><span>every chart is simulation output</span></div>
</div></header>
<main class="wrap"><article>
 <p class="lead">Gilovich, Vallone &amp; Tversky (1985) asked a clean question: after a streak of makes, is
 the next shot more likely to go in than after a streak of misses? They found no difference and concluded
 the hot hand was an illusion. The conclusion held for thirty years. The estimator they used does not.</p>

 <h2>1 · The estimator is biased on a coin</h2>
 <p>Take a shooter with <em>provably</em> no hot hand — independent flips of a fair coin — and run the
 exact GVT statistic: the probability of a make after <code>k</code> prior makes, minus the probability
 after <code>k</code> prior misses, averaged per record. If the method were sound this is zero. It isn't:
 selecting the shots that <em>follow</em> a streak inside a finite sequence is a biased sample, so the
 next shot is, on average, a make less often. The more of the streak you condition on, the worse it gets.</p>
 <figure>{chart_bias_vs_k()}<figcaption><b>On a fair coin, the statistic reads negative — and steepens with streak length.</b> At a 100-shot record it is about −8 points at k=3 and −26 at k=5. None of this is a hot hand; it is the estimator measuring itself.</figcaption></figure>

 <h2>2 · The bias lives at the operating point</h2>
 <p>Here is the part that turns a curiosity into a law. The bias is not a fixed quirk — it is wired to
 the sample size, and it explodes precisely where the data is thin, which is exactly the regime a real
 study lives in. Give the method tens of thousands of shots and it nearly behaves; give it a realistic
 game record and it lies by tens of points.</p>
 <figure>{chart_bias_vs_n()}<figcaption><b>−31 points at a 20-shot record, fading toward zero only at ~800 shots.</b> The estimator is honest in the regime you never operate in, and badly biased in the one you do.</figcaption></figure>
 <p class="pull">The method is honest where you don't need it and wrong where you do — the same trap we keep measuring across finance, networks and memory.</p>

 <h2>3 · A measured zero hides a real streak effect</h2>
 <p>Now inject a genuine hot hand of known size and see what the GVT statistic reports. Because the
 estimator starts about 8 points low, it takes a real <em>+8-point</em> streak effect just to drag the
 measurement up to zero. So the original "no difference" is not evidence of no hot hand — it is evidence
 <em>for</em> a hot hand of roughly the size that was being dismissed.</p>
 <figure>{chart_flip()}<figcaption><b>What the study would have reported (green) against the shooter's true streak effect.</b> The honest estimator is the dashed line. The crossing is the headline: a real +8 reads as a flat 0.</figcaption></figure>

 <h2>What it generalizes to</h2>
 <p>This is one instance of a pattern we found by rebuilding two dozen claims: a standard method,
 calibrated on easy data, whose error is coupled to the very stress that defines the hard case — small
 samples here, heavy tails in diversification, correlation in the wisdom of crowds, scarcity in an
 agent's memory. The number you quote from the demo is a benign-regime mirage. Miller &amp; Sanjurjo
 (2018) proved the hot-hand correction analytically; this page is just the same truth you can <em>run</em>.</p>

 <div class="cta">
  <p>Every chart here is the output of a small, seeded simulation — no hand-tuning, no cherry-picking.
  The verdict sits in the public ledger alongside its code, next to the other claims we've put on the bench.</p>
  <p style="margin-top:10px"><a href="{SITE}/public/crucible/">See the full Crucible ledger →</a></p>
 </div>
</article></main>
<footer><div class="wrap">Agora — autonomous research OS · the hot hand, reproduced · source on <a href="https://github.com/DanceNitra/agora" style="color:var(--faint)">GitHub</a></div></footer>
</body></html>'''


if __name__ == "__main__":
    OUT.write_text(page(), encoding="utf-8")
    print("rendered", OUT)
