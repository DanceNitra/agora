"""
The Crucible — render the public replication ledger.

Reads server/.replications.json (verdict ledger) + server/.lab.json (experiment scripts/output)
and renders public/crucible/index.html (human ledger) + public/crucible/crucible.json
(machine-readable dataset). Every entry: claim, source, verdict, method note, and — when the
lab script is in the repo — a link to the runnable code. Run after any new replication:
    python -X utf8 tools/render_crucible.py
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPS = ROOT / "server" / ".replications.json"
LAB = ROOT / "server" / ".lab.json"
OUT_DIR = ROOT / "public" / "crucible"
SITE = "https://dancenitra.github.io/agora"
REPO = "https://github.com/DanceNitra/agora"

ICON = {"REPRODUCED": "REPRODUCED", "FAILED": "FAILED", "NOT_COMPUTABLE": "NOT COMPUTABLE"}
KLASS = {"REPRODUCED": "ok", "FAILED": "fail", "NOT_COMPUTABLE": "pass"}


def load(p: Path) -> list:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def lab_index(lab: list) -> dict:
    out = {}
    for e in lab:
        if e.get("id"):
            out[e["id"]] = e
    return out


def script_link(lab_rec: dict | None) -> str | None:
    """GitHub link to the lab script if it lives under agora_output/lab (committed)."""
    if not lab_rec:
        return None
    sp = (lab_rec.get("script") or "").replace("\\", "/")
    if "agora_output/lab/" not in sp:
        return None
    rel = "agora_output/lab/" + sp.split("agora_output/lab/")[-1]
    if not (ROOT / rel).exists():
        return None
    return f"{REPO}/blob/main/{rel}"


def render() -> None:
    reps = load(REPS)
    labs = lab_index(load(LAB))
    by = {o: sum(1 for r in reps if r.get("outcome") == o)
          for o in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")}
    tested = [r for r in reps if r.get("outcome") in ("REPRODUCED", "FAILED")][::-1]
    passed = [r for r in reps if r.get("outcome") == "NOT_COMPUTABLE"][::-1]

    # ---------- machine-readable dataset ----------
    dataset = {
        "name": "The Crucible — machine replication ledger",
        "description": "Claims rebuilt as minimal computational models and tested. "
                       "REPRODUCED = the mechanism holds in a minimal model; FAILED = it does not; "
                       "NOT_COMPUTABLE = no simulable core (an honest pass).",
        "generated": time.strftime("%Y-%m-%d"),
        "counts": by,
        "entries": [
            {
                "claim": r.get("claim", ""),
                "source": r.get("source", ""),
                "verdict": r.get("outcome", ""),
                "note": r.get("note", ""),
                "lab_id": r.get("lab_id", ""),
                "code": script_link(labs.get(r.get("lab_id"))) or "",
                "date": time.strftime("%Y-%m-%d", time.localtime(r.get("ts", 0))) if r.get("ts") else "",
            }
            for r in reps[::-1]
        ],
    }

    # ---------- entry cards ----------
    cards = []
    for i, r in enumerate(tested, 1):
        lab_rec = labs.get(r.get("lab_id"))
        code = script_link(lab_rec)
        outcome = r["outcome"]
        date = time.strftime("%Y-%m-%d", time.localtime(r.get("ts", 0))) if r.get("ts") else ""
        note = html.escape(r.get("note", ""))
        src = html.escape(r.get("source", ""))
        claim = html.escape(r.get("claim", ""))
        codeline = (f'<a class="code" href="{code}" target="_blank" rel="noopener">runnable model &rarr;</a>'
                    if code else "")
        cards.append(f"""
      <article class="entry {KLASS[outcome]}">
        <div class="head"><span class="verdict">{ICON[outcome]}</span><span class="when">{date}</span></div>
        <h3>{claim}</h3>
        <div class="src">{src}</div>
        {f'<p class="note">{note}</p>' if note else ''}
        <div class="foot">{codeline}{f'<span class="lab">lab {r.get("lab_id")}</span>' if r.get("lab_id") else ''}</div>
      </article>""")

    passes = "".join(
        f'<li><span>{html.escape(r.get("claim", "")[:140])}</span>'
        f'<em>{html.escape((r.get("note") or "no simulable core")[:100])}</em></li>'
        for r in passed)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Crucible &middot; machine replication ledger &middot; Agora</title>
<meta name="description" content="A public ledger of scientific and technical claims rebuilt as minimal computational models and tested: {by['REPRODUCED']} reproduced, {by['FAILED']} failed, {by['NOT_COMPUTABLE']} honest passes. Every verdict ships runnable code.">
<link rel="canonical" href="{SITE}/public/crucible/">
<meta property="og:type" content="website">
<meta property="og:title" content="The Crucible — machine replication ledger">
<meta property="og:description" content="Claims rebuilt and tested in code. Published failures included.">
<meta property="og:url" content="{SITE}/public/crucible/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{{--paper:#fbf9f4;--paper2:#f4f1ea;--ink:#1b1a17;--soft:#54514a;--faint:#8c887e;
    --line:#e6e1d6;--acc:#0a8f68;--acc-soft:#e3f4ed;--bad:#b3402a;--bad-soft:#fae9e4;
    --serif:"Newsreader",Georgia,serif;--mono:"JetBrains Mono",ui-monospace,Consolas,monospace}}
  *{{box-sizing:border-box;margin:0}} html{{scroll-behavior:smooth}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--serif);-webkit-font-smoothing:antialiased}}
  a{{color:inherit;text-decoration:none}} ::selection{{background:var(--acc-soft)}}
  .topnav{{max-width:1080px;margin:0 auto;padding:24px 28px;display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:12.5px;letter-spacing:.04em}}
  .topnav a{{color:var(--soft)}} .topnav a:hover{{color:var(--acc)}}
  .brand{{display:flex;align-items:center;gap:9px;font-weight:600;color:var(--ink)}}
  .brand .m{{width:18px;height:18px;border-radius:5px;background:conic-gradient(from 210deg,var(--acc),transparent 65%);position:relative}}
  .brand .m::after{{content:"";position:absolute;inset:4px;border-radius:2px;background:var(--paper)}}
  .wrap{{max-width:1080px;margin:0 auto;padding:0 28px}}
  .masthead{{padding:54px 0 30px;border-bottom:1px solid var(--line)}}
  .masthead .eyebrow{{font-family:var(--mono);font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--acc);margin-bottom:18px}}
  .masthead h1{{font-weight:500;font-size:clamp(38px,6.5vw,70px);line-height:1.04;letter-spacing:-.025em}}
  .masthead h1 em{{font-style:italic;color:var(--acc)}}
  .masthead p{{margin-top:18px;max-width:64ch;font-size:19px;line-height:1.62;color:var(--soft)}}
  .masthead p b{{color:var(--ink)}}
  .tally{{display:flex;gap:14px;flex-wrap:wrap;margin-top:26px;font-family:var(--mono);font-size:13px}}
  .tally span{{padding:7px 14px;border:1px solid var(--line);border-radius:999px;color:var(--soft)}}
  .tally .ok{{border-color:var(--acc);color:var(--acc)}}
  .tally .fail{{border-color:var(--bad);color:var(--bad)}}
  .rules{{margin:34px 0 8px;padding:22px 26px;background:var(--paper2);border:1px solid var(--line);border-radius:14px;
    font-size:16px;line-height:1.65;color:var(--soft);max-width:74ch}}
  .rules b{{color:var(--ink)}}
  .ledger{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;margin:36px 0 26px}}
  .entry{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px 26px 20px;display:flex;flex-direction:column;gap:12px}}
  .entry .head{{display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:11.5px;letter-spacing:.12em}}
  .entry .verdict{{padding:4px 10px;border-radius:6px}}
  .entry.ok .verdict{{background:var(--acc-soft);color:var(--acc)}}
  .entry.fail .verdict{{background:var(--bad-soft);color:var(--bad)}}
  .entry .when{{color:var(--faint)}}
  .entry h3{{font-weight:500;font-size:18.5px;line-height:1.4;letter-spacing:-.01em}}
  .entry .src{{font-family:var(--mono);font-size:12px;color:var(--faint);line-height:1.5}}
  .entry .note{{font-size:15.5px;line-height:1.6;color:var(--soft)}}
  .entry .foot{{margin-top:auto;padding-top:10px;display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:12.5px}}
  .entry .code{{color:var(--acc)}} .entry .code:hover{{text-decoration:underline}}
  .entry .lab{{color:var(--faint)}}
  h2.sec{{font-weight:500;font-size:28px;letter-spacing:-.015em;margin:42px 0 6px}}
  .passlist{{list-style:none;padding:0;margin:18px 0 60px;border-top:1px solid var(--line)}}
  .passlist li{{display:flex;justify-content:space-between;gap:24px;padding:14px 4px;border-bottom:1px solid var(--line);font-size:15px;color:var(--soft);line-height:1.5}}
  .passlist em{{font-style:normal;font-family:var(--mono);font-size:12px;color:var(--faint);white-space:nowrap;align-self:center}}
  .submit{{margin:10px 0 70px;padding:26px 28px;border:1px dashed var(--acc);border-radius:16px;max-width:74ch}}
  .submit h2{{font-weight:500;font-size:24px;margin-bottom:8px}}
  .submit p{{font-size:16.5px;line-height:1.6;color:var(--soft)}}
  .submit a{{color:var(--acc);font-weight:600}}
  footer{{border-top:1px solid var(--line);padding:30px 0 50px;font-family:var(--mono);font-size:12.5px;color:var(--faint);display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}}
  @media (max-width:640px){{.passlist li{{flex-direction:column;gap:4px}}}}
</style>
</head>
<body>
<nav class="topnav"><a class="brand" href="{SITE}/"><span class="m"></span>Agora</a>
  <div><a href="{SITE}/posts/">Writing</a>&nbsp;&nbsp;&middot;&nbsp;&nbsp;<a href="{SITE}/#record">Track record</a></div>
</nav>
<header class="masthead wrap">
  <div class="eyebrow">The Crucible</div>
  <h1>Claims, rebuilt in code <em>and tested.</em></h1>
  <p>A public ledger of scientific and technical claims rebuilt as <b>minimal computational models</b>
  and run. Three honest verdicts: <b>REPRODUCED</b> (the mechanism holds in a minimal model),
  <b>FAILED</b> (it does not &mdash; science&rsquo;s rarest export, published here), and
  <b>NOT&nbsp;COMPUTABLE</b> (no simulable core &mdash; an honest pass, also on the record).</p>
  <div class="tally">
    <span class="ok">{by['REPRODUCED']} reproduced</span>
    <span class="fail">{by['FAILED']} failed</span>
    <span>{by['NOT_COMPUTABLE']} honest passes</span>
    <span><a href="crucible.json">dataset (JSON) &rarr;</a></span>
  </div>
</header>
<main class="wrap">
  <div class="rules"><b>The rules.</b> The model is built before the verdict is known, scoped to the
  claim&rsquo;s stated mechanism, and shipped with the code &mdash; every verdict is re-runnable.
  A REPRODUCED here means the minimal mechanism computes, not that the paper is beyond doubt; a FAILED
  means the stated mechanism did not survive its smallest honest model, with the discrepancy measured.</div>
  <div class="ledger">{''.join(cards)}
  </div>
  <h2 class="sec">Honest passes</h2>
  <ul class="passlist">{passes}</ul>
  <div class="submit">
    <h2>Have a claim that deserves the bench?</h2>
    <p>Send a quantitative, mechanism-bearing claim (a number, a threshold, an exponent, a rate) via
    <a href="{REPO}/issues" target="_blank" rel="noopener">an issue on the Agora repo</a>.
    If it has a simulable core, it gets a model and a public verdict &mdash; whichever way it lands.</p>
  </div>
</main>
<footer class="wrap"><span>Agora &mdash; autonomous research OS &middot; The Crucible</span>
  <span>updated {time.strftime('%Y-%m-%d')}</span></footer>
</body>
</html>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.html").write_text(page, encoding="utf-8")
    (OUT_DIR / "crucible.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"rendered {OUT_DIR / 'index.html'} — {by['REPRODUCED']}R/{by['FAILED']}F/{by['NOT_COMPUTABLE']}NC, "
          f"{len(tested)} cards")


if __name__ == "__main__":
    render()
