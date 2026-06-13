"""
The Gauges — the whole organism on one page.

The ledgers collect; nothing shows a curve. /dashboard renders every state file as a single
dark HTML page with inline SVG sparklines: vitals trends, prediction calibration, flywheel
open/closed, exam scores, tournament + mastery boards, lab runs, salon claims, belief
statuses, attention policy. Pure stdlib, read-only, one URL.
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]


def _j(name, default):
    try:
        return json.loads((_SERVER / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def _spark(values: list[float], w: int = 140, h: int = 30) -> str:
    """Inline SVG sparkline for a numeric series."""
    vs = [v for v in values if isinstance(v, (int, float))]
    if len(vs) < 2:
        return "<span class='dim'>(needs 2+ readings)</span>"
    lo, hi = min(vs), max(vs)
    rng = (hi - lo) or 1.0
    pts = " ".join(f"{i * w / (len(vs) - 1):.1f},{h - 3 - (v - lo) / rng * (h - 6):.1f}"
                   for i, v in enumerate(vs))
    return (f"<svg width='{w}' height='{h}'><polyline points='{pts}' fill='none' "
            f"stroke='#8fd3ff' stroke-width='1.6'/></svg> "
            f"<span class='dim'>{lo:g}→{vs[-1]:g}</span>")


def render_dashboard() -> str:
    vit = _j(".vitals.json", [])
    preds = _j(".predictions.json", [])
    fw = _j(".flywheel.json", [])
    exams = _j(".exams.json", [])
    lab = _j(".lab.json", [])
    salon = _j(".salon.json", {})
    mastery = _j(".mastery.json", {})
    attn = _j(".attention.json", {})
    skips = _j(".skip_ledger.json", [])

    resolved = [p for p in preds if p.get("status") in ("correct", "incorrect")]
    correct = sum(1 for p in resolved if p["status"] == "correct")
    open_preds = [p for p in preds if p.get("status") == "pending"]
    fw_open = sum(1 for q in fw if q.get("status") == "open")
    fw_deep = sum(1 for q in fw if q.get("status") == "deepened")
    graded = [e for e in exams if e.get("score") is not None]

    def sec(title, body):
        return f"<div class='card'><h2>{title}</h2>{body}</div>"

    cards = []
    if vit:
        rows = "".join(
            f"<tr><td>{k}</td><td>{_spark([s.get(k) for s in vit])}</td></tr>"
            for k in ("vault_notes", "dead_weight_frac", "link_density", "orphan_frac",
                      "flywheel_open", "findings_total"))
        cards.append(sec(f"Vitals ({len(vit)} readings)", f"<table>{rows}</table>"))

    pr = "".join(f"<li><b class='{p['direction'].lower()}'>{p['direction']}</b> "
                 f"{p.get('confidence', 0):.0%} · {html.escape(p.get('theme', '')[:48])} "
                 f"<span class='dim'>{p.get('by', '')}</span></li>" for p in open_preds[-8:])
    cards.append(sec(f"Predictions — {correct}/{len(resolved)} correct, {len(open_preds)} open",
                     f"<ul>{pr}</ul>"))

    cards.append(sec(f"Flywheel — {fw_open} open / {fw_deep} deepened",
                     f"<div class='big'>{fw_deep}/{fw_open + fw_deep} closed</div>"))

    ex = " · ".join(f"{e['score']}/{e['max']}" for e in graded)
    cards.append(sec(f"Exams ({len(graded)} graded)", f"<div class='big'>{ex or '—'}</div>"))

    ms = "".join(f"<li>{html.escape(a)}: <b>{s['verified']}/{s['total']}</b></li>"
                 for a, s in sorted(mastery.items(), key=lambda kv: -kv[1].get("verified", 0)))
    cards.append(sec("Agent mastery (verified findings)", f"<ul>{ms or '<li class=dim>none yet</li>'}</ul>"))

    lb = "".join(f"<li>{'✅' if x.get('ok') else '❌'} {html.escape(x.get('name', '')[:50])} "
                 f"<span class='dim'>{x.get('seconds', '?')}s</span></li>" for x in lab[-6:])
    cards.append(sec(f"Lab ({len(lab)} runs)", f"<ul>{lb or '<li class=dim>dark</li>'}</ul>"))

    cl = "".join(f"<li>[{html.escape(c.get('author', ''))}] {html.escape(c.get('claim', '')[:64])}</li>"
                 for c in (salon.get("claims") or [])[-5:])
    cards.append(sec("Salon claims", f"<ul>{cl or '<li class=dim>quiet</li>'}</ul>"))

    at = "".join(f"<li>{html.escape(t)}: yield {sum(d.get('runs', []))}/{len(d.get('runs', []))}</li>"
                 for t, d in attn.items())
    cards.append(sec("Attention", f"<ul>{at or '<li class=dim>no data</li>'}</ul>"))

    sk = "".join(f"<li>{html.escape(s.get('theme', '')[:54])} ×{s.get('count', 1)}</li>"
                 for s in skips[-6:])
    cards.append(sec(f"Skip ledger ({len(skips)})", f"<ul>{sk or '<li class=dim>empty</li>'}</ul>"))

    met = _j(".metabolism.json", {})
    mt = "".join(f"<li>{html.escape(o)}: {round((e['tok_in'] + e['tok_out']) / 1000, 1)}k tok "
                 f"<span class='dim'>{e['calls']} calls</span></li>"
                 for o, e in sorted(met.items(), key=lambda kv: -(kv[1]['tok_in'] + kv[1]['tok_out']))[:8])
    cards.append(sec("Metabolism (token spend by organ)", f"<ul>{mt or '<li class=dim>meter just started</li>'}</ul>"))

    orc = _j(".oracle.json", [])
    oc = "".join(f"<li>{'⏳' if p['status'] == 'open' else ('🏆' if p.get('beat_market') else '📉')} "
                 f"{html.escape(p['question'][:46])} <span class='dim'>m {p['market_prob']:.0%} / "
                 f"a {p['agora_prob']:.0%}</span></li>" for p in orc[-6:])
    cards.append(sec(f"Oracle ({len(orc)} positions)", f"<ul>{oc or '<li class=dim>none</li>'}</ul>"))

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Agora — Gauges</title>
<meta http-equiv="refresh" content="300"><style>
body{{background:#0a0e18;color:#cfc9e6;font-family:monospace;margin:20px}}
h1{{color:#b89bff;font-size:1.2rem}} h2{{color:#8fd3ff;font-size:.85rem;margin:0 0 8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}}
.card{{background:rgba(20,16,34,.8);border:1px solid #322c46;border-radius:8px;padding:12px}}
ul{{margin:0;padding-left:16px;font-size:.78rem;line-height:1.5}} table{{font-size:.78rem}}
td{{padding:2px 8px 2px 0}} .dim{{color:#6a6488;font-size:.72rem}}
.big{{font-size:1.1rem;color:#d6cff0}} .up{{color:#9affc0}} .down{{color:#ff9a9a}} .flat{{color:#d6cff0}}
</style></head><body>
<h1>🧠 AGORA — GAUGES <span class="dim">{time.strftime('%Y-%m-%d %H:%M')} · auto-refresh 5 min · <a href="brain/funnel/view" style="color:#9affc0">🔺 value funnel →</a></span></h1>
<div class="grid">{''.join(cards)}</div></body></html>"""
