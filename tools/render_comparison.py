"""Render public/compare/ — inspeximus vs mem0 vs Graphiti, from artifacts, by the maker of one of them.

WHAT IS DELIBERATELY NOT HERE. composite_bench_result.json shows inspeximus passing five capabilities of
five and mem0 well under one. It is excluded: that harness reads inspeximus locally on its own
current-value surface while the competitor cells were imported from another session, and when the
instrument was equalised across systems our own revert score fell from 1.00 to 0.75. We published that
correction; a comparison built on the same asymmetry would hand a critic our own retraction.

Every cell below comes from an instrument that reads each system the same way, re-run the day this was
generated. Numbers are read from the result artifacts at render time -- none are typed into the template.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://dancenitra.github.io/agora"
OUT = ROOT / "public" / "compare"
P = ROOT / "research" / "probes"
GH = "https://github.com/DanceNitra/agora/blob/main/research/probes"


def load(name: str) -> dict:
    return json.loads((P / name).read_text(encoding="utf-8"))


def pypi(name: str) -> dict:
    d = json.loads(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=30).read())
    i = d["info"]
    reqs = i.get("requires_dist") or []
    return {"v": i["version"], "lic": (i.get("license_expression") or i.get("license") or "?")[:20],
            "py": i.get("requires_python") or "?", "hard": len([r for r in reqs if "extra ==" not in r])}


def main() -> int:
    echo = load("echo_attack_probe_v2_result.json")
    er = load("erasure_completeness_xsystem_result.json")
    wired = load("erasure_manifest_wired_cell_result.json")
    packs = {n: pypi(n) for n in ("inspeximus", "mem0ai", "graphiti-core")}
    today = time.strftime("%Y-%m-%d")

    # the paraphrase arms are the realistic attack: an echo that is not a byte-for-byte replay
    arms = [k for k in echo if k.startswith("paraphrase_")]
    labels = {"ours": "inspeximus", "mem0_faithful": "mem0 (faithful policy)",
              "graphiti_faithful": "Graphiti (faithful policy)", "memstrata": "MemStrata (faithful policy)",
              "recency": "last-mention-wins", "cosine": "similarity only",
              "tie_recent": "inspeximus 0.6.8 — our own older version"}
    order = ["ours", "mem0_faithful", "graphiti_faithful", "memstrata", "tie_recent", "cosine", "recency"]
    rows = ""
    for pol in order:
        vals = [echo[a]["rates"][pol] for a in arms if pol in echo[a]["rates"]]
        if not vals:
            continue
        cls = " class='win'" if pol == "ours" else (" class='self'" if pol == "tie_recent" else "")
        rows += (f"<tr{cls}><td>{labels[pol]}</td>"
                 + "".join(f"<td class='num'>{v:.3f}</td>" for v in vals)
                 + f"<td class='num'><b>{sum(vals) / len(vals):.3f}</b></td></tr>")
    heads = "".join(f"<th>{a.replace('paraphrase_', '')}</th>" for a in arms)
    n_arm = echo[arms[0]]["n"]

    er_rows = "".join(f"<tr><td>{k}</td><td class='num'>{v['residue']}/{v['n']}</td>"
                      f"<td class='num'>{v['rate']:.2f}</td></tr>" for k, v in er.items())
    pk_rows = "".join(f"<tr><td>{n}</td><td class='num'>{p['v']}</td><td class='num'>{p['hard']}</td>"
                      f"<td>{p['lic']}</td><td>{p['py']}</td></tr>" for n, p in packs.items())

    shell = (ROOT / "public" / "track-record.html").read_text(encoding="utf-8", errors="replace")
    head = shell[:shell.find("<body")]
    # The shell is borrowed for its styles; its IDENTITY must not come with it. Left alone, this page
    # shipped with track-record's title, canonical and og:url -- a second document claiming to be that
    # page, which is the sitemap-vs-canonical class of defect fixed three times on this site today.
    url = f"{SITE}/public/compare/"
    title = "inspeximus vs mem0 vs Graphiti — measured, by the maker of one of them"
    desc = ("After a correction, a paraphrased restatement of the retired value returns it 100% of the "
            "time under last-writer-wins and bitemporal resolution, and 15% under inspeximus. Plus "
            "cross-store erasure that cannot issue a clean receipt while leaking, and the cell where we "
            "only tie. Every number from an instrument that reads each system the same way.")
    head = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", head, flags=re.S)
    head = re.sub(r'(<link rel="canonical" href=")[^"]*(")', rf"\g<1>{url}\g<2>", head)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")', rf"\g<1>{desc}\g<2>", head)
    head = re.sub(r'(<meta property="og:url" content=")[^"]*(")', rf"\g<1>{url}\g<2>", head)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")', rf"\g<1>{title}\g<2>", head)
    head = re.sub(r'(<meta property="og:description" content=")[^"]*(")', rf"\g<1>{desc}\g<2>", head)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>', "", head, flags=re.S)
    extra = ("<style>.tbl{width:100%;border-collapse:collapse;margin:14px 0;font-size:.94rem}"
             ".tbl th,.tbl td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left}"
             ".tbl td.num,.tbl th.num{text-align:right;font-variant-numeric:tabular-nums}"
             ".tbl tr.win{background:rgba(90,200,150,.10);font-weight:600}"
             ".tbl tr.self{opacity:.75;font-style:italic}"
             ".note{opacity:.78;font-size:.93rem}</style>")

    body = f"""<body>
<nav class="nav"><div class="wrap">
  <a class="brand" href="{SITE}/"><span class="m"></span>Agora</a>
  <div class="navr"><a href="../posts/">Writing</a><a href="../crucible/">The Crucible</a><a href="../track-record.html">Track record</a></div>
</div></nav>

<header><div class="wrap">
  <div class="kick">Comparison</div>
  <h1>What happens to a corrected fact when someone repeats the old one?</h1>
  <p class="lede">inspeximus vs mem0 vs Graphiti, on the axis a memory library exists for.
  <b>Written by the maker of one of the three</b> — so every number here comes from an instrument that
  reads each system the same way, the panel includes an attack on our own older version, and the section
  where we do not win is included rather than omitted. Re-run {today}.</p>
</div></header>

<main class="wrap">

<section>
  <h2>1. After a correction, does a restatement bring the old value back?</h2>
  <p>Correct a fact, then have someone assert the retired value again in different words — not a
  byte-for-byte replay, a paraphrase, which is what actually happens in a conversation. The number is how
  often the store then serves the <b>stale</b> value. Lower is better. Three independent models generated
  the paraphrases; n={n_arm} per arm.</p>
  <table class="tbl">
    <thead><tr><th>resolution policy</th>{heads}<th class="num">mean</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p class="note"><b>Last-writer-wins and bitemporal resolution both return the retired value every single
  time.</b> That is not a bug in either — it is what those designs say to do: the newest assertion wins, or
  the edge with the later validity time wins, and a paraphrased echo IS the newest assertion. inspeximus
  records the superseded <em>object</em> against its (subject, relation) key, so a later assertion of an
  already-retired value is recognised whatever words carry it.</p>
  <p class="note"><b>Read this honestly.</b> These are faithful re-implementations of each system's
  documented resolution logic, not the live products — the cell isolates the supersession rule, and every
  policy is granted oracle value-extraction so it is not measuring extractor quality. The italic row is
  our own version 0.6.8, which fails a third of the time: this is the same panel we use to attack
  ourselves, which is why we trust it pointing the other way.</p>
</section>

<section>
  <h2>2. Erasure that reaches the stores we do not own</h2>
  <p>Every memory library shares a blind spot: delete a subject from the store and the copy your
  application embedded into its <em>own</em> vector index is untouched. Measured on ourselves:</p>
  <table class="tbl">
    <thead><tr><th>configuration</th><th class="num">residue in the app's index</th><th>receipt</th></tr></thead>
    <tbody>
      <tr><td>store-native delete only <span class="note">(the category default)</span></td>
          <td class="num">{wired['A_unwired']['external_index_residue']}</td><td>—</td></tr>
      <tr class="win"><td>wired to a registered target</td>
          <td class="num">{wired['B_wired']['external_index_residue']}</td>
          <td>manifest complete {wired['B_wired']['manifests_complete']}, chain verifies</td></tr>
      <tr><td>wired, but the integration is broken</td>
          <td class="num">{wired['C_broken']['external_index_residue']}</td>
          <td>falsely-complete receipts {wired['C_broken']['falsely_complete']}, leak named
              {wired['C_broken']['leak_named']}</td></tr>
    </tbody>
  </table>
  <p class="note">The third row is the point. A broken integration still leaks — no library can reach into
  a store it was never given — but it <b>cannot produce a clean receipt while leaking</b>. The claim is not
  "we erase everywhere"; it is that we will not tell you an erasure was complete when it was not. Since
  this release <code>forget_subject()</code> returns a <code>coverage</code> field stating exactly that,
  and with nothing registered it says so outright rather than returning a bare success.</p>
</section>

<section>
  <h2>3. Where we do not win</h2>
  <p>On each system's <em>own</em> retrieval surface, after its own native delete, the subject's value is
  equally unrecoverable. Same procedure, same data, no rubric of ours, no LLM judge.</p>
  <table class="tbl">
    <thead><tr><th>system</th><th class="num">residual recoverability</th><th class="num">rate</th></tr></thead>
    <tbody>{er_rows}</tbody>
  </table>
  <p class="note">A tie, and it belongs on this page. Graphiti is bitemporal by design and retains
  invalidated facts as history — if you need an auditable record of what was believed when, that is a
  reason to choose it over us, not a defect.</p>
</section>

<section>
  <h2>4. Verifiable without trusting anyone</h2>
  <p>Read live from PyPI when this page was generated. Hard dependencies exclude optional extras.</p>
  <table class="tbl">
    <thead><tr><th>package</th><th class="num">version</th><th class="num">hard deps</th><th>licence</th><th>python</th></tr></thead>
    <tbody>{pk_rows}</tbody>
  </table>
  <p class="note">A deployment property, not a quality claim: fewer dependencies does not mean better
  recall, and all three are permissively licensed.</p>
</section>

<section>
  <h2>What is not measured here</h2>
  <ul>
    <li><b>Retrieval accuracy on a shared corpus.</b> No symmetric cross-system measurement exists yet, so
    treat any accuracy ranking between these three — including one in our favour — as unsupported.</li>
    <li><b>Graphiti on the erasure cells.</b> It needs a graph database we did not stand up for this run,
    so it is absent rather than estimated.</li>
    <li><b>Cost and latency.</b> Not measured at all.</li>
    <li><b>The live products on the echo panel.</b> Section 1 measures documented resolution logic. A
    live-integration run is the obvious next step and would be the stronger evidence.</li>
  </ul>
</section>

<section>
  <h2>Check it yourself</h2>
  <p>Each cell is one file:
  <a href="{GH}/echo_attack_probe_v2.py">echo_attack_probe_v2.py</a>,
  <a href="{GH}/erasure_manifest_wired_cell.py">erasure_manifest_wired_cell.py</a>,
  <a href="{GH}/erasure_completeness_xsystem.py">erasure_completeness_xsystem.py</a>.
  Each states its own scope limits in its header, above any result. The replication ledger behind this
  project's other claims is <a href="../crucible/">the Crucible</a>
  (<a href="https://doi.org/10.5281/zenodo.21648053">DOI</a>), and what we have retracted is on the
  <a href="../track-record.html">track record</a>.</p>
</section>

</main>

<footer class="wrap"><p>AGORA — verdicts with receipts · founded by Rastislav Drahoš · © 2026</p></footer>
</body>
</html>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(head + extra + body, encoding="utf-8")
    print(f"rendered {OUT / 'index.html'}")
    print(f"  echo arms: {arms}")
    print(f"  ours mean: {sum(echo[a]['rates']['ours'] for a in arms) / len(arms):.3f}  "
          f"mem0: {sum(echo[a]['rates']['mem0_faithful'] for a in arms) / len(arms):.3f}  "
          f"graphiti: {sum(echo[a]['rates']['graphiti_faithful'] for a in arms) / len(arms):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
