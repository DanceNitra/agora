"""
The Funnel — does the work produce value, and at what cost?

The owner's question, made legible: the dungeon completes thousands of quests; where does
that go, and is the return real? This stacks the whole organism into a value funnel —

    ACTIVITY  →  GROUNDED KNOWLEDGE  →  CURATED ASSETS  →  SHIPPED VALUE

— with the conversion rate between each stage, the value WEIGHT each stage carries (from the
Metabolism's value ledger), and the system-wide ROI (value points per kilotoken). It reads the
brain DB read-only and the organs' own ledgers; it writes nothing. One JSON endpoint, one page.

The point is honesty: a wide base of cheap activity narrowing to a few high-value shipped
artifacts is the EXPECTED shape of research — the funnel lets the owner watch the conversion
rates move as the quest-value gate tightens, instead of trusting a raw quest counter that
measures noise, not knowledge.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]
_DB = _SERVER / "agora.db"

# A discovery "lands" as knowledge only with REAL grounding: a real citation (DOI / arXiv / Author-year)
# OR a measured result / lab receipt (MEASURED:/VERDICT:/lab id / a number+%/CI/n=). NOT the mere WORDS
# "Hypothesis/Falsifier/Source:" that any activity note can contain — that was Goodhart (the funnel counted
# text-that-says-Hypothesis as grounded). Aligns with the Voss science gate's _real_grounding.
_GROUNDED = re.compile(
    r"10\.\d{4,9}/|arxiv[:\s]*\d{4}\.\d|\([A-Z][a-z]+(?: et al\.?)?,? \d{4}\)|"
    r"MEASURED:|VERDICT:|\blab[:_ ]?[0-9a-f]{6}\b|\bn\s*=\s*\d|\d+(?:\.\d+)?\s*%|\b95%|\bCI\b|p\s*[<=]\s*0?\.\d",
    re.I)


def _j(name, default):
    try:
        return json.loads((_SERVER / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def _db():
    return sqlite3.connect(f"file:{_DB.as_posix()}?mode=ro", uri=True)


def _count(c, sql, *a):
    try:
        return int(c.execute(sql, a).fetchone()[0])
    except Exception:
        return 0


def compute_funnel() -> dict:
    """The whole value pipeline, from raw activity to shipped artifacts, with conversion + ROI."""
    from . import metabolism

    con = _db()
    c = con.cursor()

    # --- S1 ACTIVITY (the wide, cheap base) ---
    task_completed = _count(c, "SELECT COUNT(*) FROM events WHERE event_type='task_completed'")
    disc_live = _count(c, "SELECT COUNT(*) FROM collective_knowledge WHERE knowledge_type='discovery'")
    disc_retracted = _count(c, "SELECT COUNT(*) FROM collective_knowledge WHERE knowledge_type='retracted'")
    disc_attempts = disc_live + disc_retracted

    # --- S2 GROUNDED KNOWLEDGE (what actually carried a source / citation / verdict) ---
    grounded = 0
    for (ct,) in c.execute(
            "SELECT content FROM collective_knowledge WHERE knowledge_type='discovery'"):
        if ct and _GROUNDED.search(ct):
            grounded += 1
    research_findings = _count(c, "SELECT COUNT(*) FROM research_findings")
    quality_ratio = round(grounded / disc_live, 3) if disc_live else 0.0
    con.close()

    # --- S3 CURATED ASSETS (organ ledgers — the distilled, named knowledge) ---
    reps = _j(".replications.json", [])
    ana = _j(".analogies.json", [])
    carto = _j(".cartography.json", [])
    bounty = _j(".bounty.json", [])
    graves = _j(".graveyard.json", [])
    # curated vault notes the agents/synthesis actually wrote
    vroot = Path("C:/Users/Danculus/my-second-brain/04 Resources/Concepts/Agora Agents")
    curated_notes = sum(1 for _ in vroot.rglob("*.md")) if vroot.exists() else 0
    belief_kills = sum(1 for x in bounty if x.get("kill"))
    # cartography entries are stamped status 'charted' but their outcome records the verdict;
    # a real bridge is one whose outcome actually bridged distant domains.
    bridges = sum(1 for x in carto if str(x.get("outcome", "")).upper().startswith("BRIDGED"))

    # --- S4 SHIPPED VALUE (the narrow apex the whole funnel exists to feed) ---
    press = _j(".press.json", [])
    published = sum(1 for p in press if p.get("status") == "published")
    failed_pub = sum(1 for r in reps if r.get("outcome") == "FAILED")        # publishable nulls
    reproduced = sum(1 for r in reps if r.get("outcome") == "REPRODUCED")
    # the Canon is a living vault note; its laws are the bold-named statements ("**X** — ...")
    canon = 0
    try:
        ctext = (Path("C:/Users/Danculus/my-second-brain/04 Resources/Concepts/Agora Agents"
                      "/Canon — What Agora Currently Believes.md")).read_text(encoding="utf-8")
        canon = len(re.findall(r"(?m)^\*\*.+?\*\*\s*[—-]", ctext))
    except Exception:
        pass

    # --- ROI (system-wide, from the Metabolism's spend×value ledger) ---
    roi = metabolism.roi_report()
    total_value = round(sum(o["value"] for o in roi["organs"].values())
                        + sum(roi["unmetered_value"].values()), 1)
    total_ktok = roi["total_ktok"]
    system_roi = round(total_value / total_ktok, 3) if total_ktok > 0.5 else None

    stages = [
        {"key": "activity", "label": "Activity",
         "blurb": "raw quests + discovery attempts — cheap, wide, expected to be noisy",
         "count": disc_attempts,
         "items": [f"{task_completed:,} tasks completed (durable)",
                   f"{disc_attempts:,} discovery attempts"]},
        {"key": "grounded", "label": "Grounded knowledge",
         "blurb": "attempts that carried a real source / citation / tested verdict",
         "count": grounded,
         "items": [f"{grounded:,} grounded discoveries ({quality_ratio:.0%} of {disc_live:,})",
                   f"{research_findings:,} verified research findings"]},
        {"key": "curated", "label": "Curated assets",
         "blurb": "distilled, named knowledge — notes, replications, bridges, belief kills",
         "count": curated_notes,
         "items": [f"{curated_notes:,} curated vault notes", f"{len(reps)} replications",
                   f"{len(ana)} analogy tests", f"{bridges} bridges", f"{belief_kills} belief kills",
                   f"{len(graves)} honest dead-ends"]},
        {"key": "shipped", "label": "Shipped value",
         "blurb": "the apex — public artifacts the outside world can use",
         "count": published + failed_pub + canon,
         "items": [f"{published} published posts", f"{failed_pub} publishable failed replications",
                   f"{reproduced} reproduced results", f"{canon} canon laws"]},
    ]
    # conversion rate vs the previous stage (the number the owner watches move)
    for i, s in enumerate(stages):
        prev = stages[i - 1]["count"] if i else None
        s["conversion"] = round(s["count"] / prev, 4) if prev else None

    return {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "stages": stages,
        "quality_ratio": quality_ratio,
        "roi": {"total_value": total_value, "total_ktok": total_ktok, "system_roi": system_roi,
                "organs": roi["organs"]},
        "headline": {
            "quests_to_grounded": round(grounded / disc_attempts, 4) if disc_attempts else 0,
            "grounded_to_shipped": round((published + failed_pub) / grounded, 5) if grounded else 0,
        },
    }


def _bar(frac: float, w: int = 100) -> str:
    frac = max(0.0, min(1.0, frac))
    return f"<div class='bar'><span style='width:{frac * w:.1f}%'></span></div>"


def render_funnel_html() -> str:
    """The value funnel as one dark page — stage bars (log-scaled width), conversion arrows,
    value weights and the system ROI. Read-only, auto-refresh."""
    import math

    d = compute_funnel()
    stages = d["stages"]
    top = max(s["count"] for s in stages) or 1

    def width(n):  # log scale so the narrow apex is still visible against the wide base
        return (math.log10(n + 1) / math.log10(top + 1)) if top > 1 else 1.0

    rows = []
    for i, s in enumerate(stages):
        conv = ""
        if s["conversion"] is not None:
            pct = s["conversion"] * 100
            cls = "good" if pct >= 30 else ("mid" if pct >= 5 else "thin")
            conv = (f"<div class='conv {cls}'>▼ {pct:.1f}% of previous stage survives</div>")
        items = " · ".join(s["items"])
        rows.append(
            f"{conv}<div class='stage'><div class='shead'><b>{s['label']}</b>"
            f"<span class='n'>{s['count']:,}</span></div>"
            f"{_bar(width(s['count']))}"
            f"<div class='blurb'>{s['blurb']}</div>"
            f"<div class='items'>{items}</div></div>")

    roi = d["roi"]
    sr = roi["system_roi"]
    sr_txt = f"{sr:g} value-pts / ktok" if sr is not None else "warming up"
    organs = sorted(roi["organs"].items(), key=lambda kv: -(kv[1].get("roi") or 0))
    orw = "".join(
        f"<tr><td>{o}</td><td>{e['ktok']:g}k</td><td>{e['value']:g}</td>"
        f"<td class='{'good' if (e['roi'] or 0) >= 1 else ('mid' if (e['roi'] or 0) > 0 else 'thin')}'>"
        f"{e['roi'] if e['roi'] is not None else '—'}</td></tr>"
        for o, e in organs[:12])

    # Seminar panel — topic threads + contributions (the redirected agent dialogue)
    sem_html = ""
    try:
        from . import seminar
        st = seminar.seminar_stats()
        threads = seminar.topic_threads(6)
        tr = "".join(
            f"<tr><td>{t['headline'][:48]}</td>"
            f"<td class='{'good' if t['status']=='synthesized' else 'mid'}'>{t['status']}</td>"
            f"<td>{t['n_contrib']}</td><td class='dim'>{t.get('source','')}</td></tr>"
            for t in threads) or "<tr><td class='dim' colspan=4>no topics yet — seeds on next tick</td></tr>"
        sem_html = (
            "<div class='panel'><h2>THE SEMINAR — dialogue redirected to topics</h2>"
            f"<div class='kpi'><div><b>{st['contributions']}</b><span>contributions</span></div>"
            f"<div><b>{st['grounded']}</b><span>grounded</span></div>"
            f"<div><b>{st['topics_open']}</b><span>open topics</span></div>"
            f"<div><b>{st['topics_synthesized']}</b><span>ripe for synthesis</span></div></div>"
            f"<table><tr><th>topic thread</th><th>status</th><th>contribs</th><th>source</th></tr>"
            f"{tr}</table></div>")
    except Exception:
        pass

    h = d["headline"]
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Agora — Value Funnel</title>
<meta http-equiv="refresh" content="180"><style>
body{{background:#0a0e18;color:#cfc9e6;font-family:ui-monospace,Menlo,Consolas,monospace;margin:0;padding:26px;max-width:880px}}
h1{{color:#b89bff;font-size:1.15rem;margin:0 0 4px}} .sub{{color:#6a6488;font-size:.75rem;margin-bottom:22px}}
.stage{{background:rgba(20,16,34,.85);border:1px solid #322c46;border-radius:9px;padding:13px 15px;margin:0}}
.shead{{display:flex;justify-content:space-between;align-items:baseline}}
.shead b{{color:#8fd3ff;font-size:.95rem}} .n{{color:#d6cff0;font-size:1.1rem;font-weight:bold}}
.bar{{background:#181426;border-radius:5px;height:14px;margin:8px 0;overflow:hidden}}
.bar span{{display:block;height:100%;background:linear-gradient(90deg,#6a4bff,#8fd3ff);border-radius:5px}}
.blurb{{color:#8a85a8;font-size:.74rem;margin-bottom:5px}} .items{{color:#b5afd0;font-size:.76rem;line-height:1.5}}
.conv{{text-align:center;font-size:.74rem;padding:7px 0;letter-spacing:.02em}}
.conv.good{{color:#9affc0}} .conv.mid{{color:#ffcf5a}} .conv.thin{{color:#ff9a9a}}
.panel{{background:rgba(20,16,34,.85);border:1px solid #322c46;border-radius:9px;padding:14px 16px;margin-top:24px}}
.panel h2{{color:#8fd3ff;font-size:.85rem;margin:0 0 10px}}
.roi-big{{font-size:1.5rem;color:#9affc0;font-weight:bold}}
table{{width:100%;font-size:.75rem;border-collapse:collapse;margin-top:10px}}
td,th{{text-align:left;padding:3px 8px 3px 0}} th{{color:#6a6488;font-weight:normal}}
.good{{color:#9affc0}} .mid{{color:#ffcf5a}} .thin{{color:#ff9a9a}}
.kpi{{display:flex;gap:30px;margin:6px 0 0}} .kpi div span{{display:block;color:#6a6488;font-size:.7rem}}
.kpi div b{{font-size:1.1rem;color:#d6cff0}}
</style></head><body>
<h1>🔺 AGORA — VALUE FUNNEL</h1>
<div class="sub">{d['generated']} · auto-refresh 3 min · activity → grounded → curated → shipped</div>
{''.join(rows)}
<div class="panel"><h2>RETURN ON COGNITION</h2>
<div class="roi-big">{sr_txt}</div>
<div class="kpi">
  <div><b>{roi['total_value']:g}</b><span>value points earned</span></div>
  <div><b>{roi['total_ktok']:g}k</b><span>tokens metered</span></div>
  <div><b>{d['quality_ratio']:.0%}</b><span>discoveries grounded</span></div>
  <div><b>{h['quests_to_grounded'] * 100:.1f}%</b><span>attempt → grounded</span></div>
</div>
<table><tr><th>organ</th><th>spend</th><th>value</th><th>ROI</th></tr>{orw}</table>
</div>
{sem_html}
</body></html>"""
