"""Render the Agent-Memory Integrity Leaderboard from its machine dataset.

    python tools/render_leaderboard.py

Reads  public/leaderboard/leaderboard.json  (the source of truth, mirrored from RAMR's cross-system run)
Writes public/leaderboard/index.html        (the human-readable ranked board)

The board follows the Crucible pattern: the JSON is the citable artifact, the HTML is a render of it. It
ranks each cell, leads with the cell we tie, and links the submission flow so the board grows by PR rather
than by us adding our own rows. No number here is computed by this script — it only presents what the
dataset already holds, and the dataset is verified against RAMR's canonical results before publishing.
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "leaderboard" / "leaderboard.json"
OUT = ROOT / "public" / "leaderboard" / "index.html"


def e(s):
    return html.escape(str(s), quote=True)


def fmt(v):
    return f"{v:.2f}"


def rank(cell):
    """Best-first: for 'higher is better' descending, else ascending."""
    better_high = cell["direction"].startswith("higher")
    return sorted(cell["systems"], key=lambda s: s["value"], reverse=better_high)


def cell_html(cell):
    rows = []
    ranked = rank(cell)
    tie = len({s["value"] for s in ranked}) == 1
    for i, s in enumerate(ranked):
        lead = "" if tie else (" lead" if i == 0 else "")
        ci = s.get("ci95")
        ci_txt = f'<span class="ci">CI [{fmt(ci[0])}, {fmt(ci[1])}]</span>' if ci else ""
        pos = "—" if tie else str(i + 1)
        rows.append(
            f'<tr class="{lead.strip()}"><td class="pos">{pos}</td>'
            f'<td class="sys">{e(s["system"])}</td>'
            f'<td class="val">{fmt(s["value"])} {ci_txt}</td>'
            f'<td class="note">{e(s.get("note",""))}</td></tr>')
    return f"""    <section class="cell">
      <h2>{e(cell["title"])}</h2>
      <p class="q">{e(cell["question"])}</p>
      <table>
        <thead><tr><th>#</th><th>system</th><th>{e(cell["metric"])} <span class="dir">({e(cell["direction"])})</span></th><th>how</th></tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
      <p class="framing">{e(cell["framing"])}</p>
    </section>"""


def render():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    cells = "\n".join(cell_html(c) for c in d["cells"])
    n_systems = len({s["system"] for c in d["cells"] for s in c["systems"]})
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(d["name"])}</title>
<meta name="description" content="{e(d["tagline"])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{--bg:#faf8f3;--ink:#17150f;--muted:#6b6656;--line:#e4dfd2;--accent:#0c7a55;--lead:#0c7a55}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);font-family:Newsreader,Georgia,serif;font-size:19px;line-height:1.55}}
  .wrap{{max-width:820px;margin:0 auto;padding:56px 22px 90px}}
  .kicker{{font-family:'JetBrains Mono',monospace;font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin:0 0 12px}}
  h1{{font-size:40px;line-height:1.1;font-weight:600;margin:0 0 14px;letter-spacing:-.01em}}
  .tagline{{font-size:22px;color:var(--ink);margin:0 0 8px}}
  .principle{{color:var(--muted);font-style:italic;margin:0 0 26px}}
  .meta{{font-family:'JetBrains Mono',monospace;font-size:12.5px;color:var(--muted);border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:12px 0;margin:0 0 34px;display:flex;flex-wrap:wrap;gap:8px 20px}}
  .cell{{margin:0 0 40px}}
  h2{{font-size:26px;font-weight:600;margin:0 0 6px}}
  .q{{color:var(--muted);margin:0 0 16px}}
  table{{width:100%;border-collapse:collapse;font-size:16px}}
  th{{font-family:'JetBrains Mono',monospace;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:left;font-weight:500;padding:0 10px 8px;border-bottom:1px solid var(--line)}}
  .dir{{text-transform:none;letter-spacing:0;font-weight:400}}
  td{{padding:11px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
  .pos{{font-family:'JetBrains Mono',monospace;color:var(--muted);width:26px}}
  .sys{{font-family:'JetBrains Mono',monospace;font-weight:500;white-space:nowrap}}
  .val{{font-family:'JetBrains Mono',monospace;font-weight:600;white-space:nowrap}}
  .ci{{font-weight:400;color:var(--muted);font-size:12.5px}}
  .note{{color:var(--muted);font-size:15px}}
  tr.lead .sys,tr.lead .val{{color:var(--lead)}}
  .framing{{font-size:16px;color:var(--muted);margin:14px 0 0;padding:12px 16px;background:#f2efe6;border-left:3px solid var(--accent);border-radius:0 6px 6px 0}}
  .submit{{margin:44px 0 0;padding:22px 24px;border:1px solid var(--line);border-radius:12px;background:#fff}}
  .submit h3{{margin:0 0 8px;font-size:20px}}
  .submit p{{margin:0 0 14px;color:var(--muted);font-size:16px}}
  a.go{{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;color:#fff;background:var(--accent);text-decoration:none;padding:9px 15px;border-radius:7px}}
  a{{color:var(--accent)}}
  footer{{margin:40px 0 0;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--muted)}}
  footer a{{color:var(--muted)}}
</style>
</head>
<body>
  <div class="wrap">
    <p class="kicker">agent-memory integrity · a standing leaderboard</p>
    <h1>{e(d["name"])}</h1>
    <p class="tagline">{e(d["tagline"])}</p>
    <p class="principle">{e(d["principle"])}</p>
    <div class="meta">
      <span>{n_systems} systems</span>
      <span>judge: {e(d["judge"].split("(")[0].strip())}, blind</span>
      <span>n={e(d["n"])} · native configs</span>
      <span>updated {e(d["generated"])}</span>
    </div>
{cells}
    <div class="submit">
      <h3>Add your system</h3>
      <p>One shared, ground-truth-blind judge reads each system's own recall surface — no home-field instrument. The harness is open; run it or submit your system by PR and it appears here.</p>
      <a class="go" href="{e(d["submit"])}">submit your system →</a>
    </div>
    <footer>
      machine-readable: <a href="leaderboard.json">leaderboard.json</a> ·
      method: <a href="{e(d["method"])}">METHODOLOGY</a> ·
      benchmark: <a href="{e(d["source"])}">RAMR</a> ·
      <a href="{e(d["doi"])}">DOI</a> ·
      <a href="https://dancenitra.github.io/agora/">agora</a> · MIT
    </footer>
  </div>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"rendered {OUT} — {len(d['cells'])} cells, {n_systems} systems")


if __name__ == "__main__":
    render()
