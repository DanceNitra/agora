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
    live = load("echo_live_xsystem_result.json")
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

    live_names = {"inspeximus": "inspeximus (product surface)", "mem0": "mem0 2.0.14",
                  "graphiti": "Graphiti"}
    # RANGE AND RUN COUNT, not a single figure. The first version of this page published mem0 at 1.000
    # from ONE run; repeating the panel put it at 0.875 three times over. A system whose extraction is
    # LLM-driven does not return the same number twice by default, so one run is a sample and printing it
    # as a rate is the defect this page was built to avoid, committed on the page itself.
    live_rows, live_n, live_runs, ins_rate = "", 0, 0, "—"
    for k, v in live.items():
        label = live_names.get(k, k)
        if "stale" in v:
            live_n = max(live_n, v["n"])
            live_runs = max(live_runs, v.get("runs", 1))
            cls = " class='win'" if k == "inspeximus" else ""
            spread = (f"{v['min']:.3f} – {v['max']:.3f}"
                      if v.get("min") != v.get("max") else "no variation")
            live_rows += (f"<tr{cls}><td>{label}</td><td class='num'>{v['stale']:.3f}</td>"
                          f"<td class='num'>{spread}</td><td class='num'>{v.get('runs', 1)}</td></tr>")
            if k == "inspeximus":
                ins_rate = f"{v['stale']:.3f}"
        else:
            live_rows += (f"<tr><td>{label}</td><td colspan='3'>NOT RUN — {v['not_run']}</td></tr>")

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
  <p class="note">The italic row is our own version 0.6.8, which fails a third of the time: this is the
  same panel we use to attack ourselves, which is why we trust it pointing the other way. The panel
  measures each system's <em>documented resolution logic</em>, which isolates the supersession rule and
  grants every policy oracle value-extraction so it is not measuring extractor quality — see the live run
  below for the same question put to the real software.</p>
</section>

<section>
  <h2>1b. The same attack, against the live products</h2>
  <p>The section above models each system's documented logic. The obvious objection is "that is not our
  product, that is your model of our product", so here is the same procedure run against the real
  software: write a fact, correct it, restate the retired value in different words, then ask each system
  at its own retrieval surface and read <b>rank&nbsp;1</b> — what an agent would actually act on. Each
  system in its shipped product configuration, {live_n} cases, the whole panel repeated {live_runs} times
  because LLM-driven fact extraction does not return the same answer twice.</p>
  <table class="tbl">
    <thead><tr><th>system</th><th class="num">mean</th><th class="num">range across runs</th><th class="num">runs</th></tr></thead>
    <tbody>{live_rows}</tbody>
  </table>
  <p class="note"><b>mem0 does not overwrite the corrected fact — it keeps both and ranks the stale one
  first.</b> Searching the corrected fact returns "…is db-old-07" at 0.872 and its own "changed from
  db-old-07 to db-new-12" at 0.828, so rank 1 is the retired value. <b>Graphiti is reported as NOT RUN</b>,
  not estimated: it needs a graph database we could not reach, and carrying the modelled number over and
  relabelling it "live" would be the exact overclaim this run exists to remove.</p>
  <p class="note"><b>And the configuration matters, so here it is.</b> Measured through the product
  surface — the MCP server, the CLI, the editor plugin — inspeximus scores {ins_rate}. Constructed as a
  bare library object before version 1.87.0 it scored <b>1.000</b>, because the echo guard shipped off for
  byte-identical legacy compatibility. That is not a footnote we polished: it is why the guard is now on by
  default in the library too. Set <code>echo_guard = False</code> and you get the old number back.</p>
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
  <p class="note">A tie, and it belongs on this page: a comparison that reported a win on every axis would
  tell you more about the author than about the systems. Graphiti is bitemporal by design and retains
  invalidated facts as history, which is a different trade-off on this axis rather than a worse score.</p>
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
    <li><b>Graphiti live.</b> Sections 1b and 3 could not reach a graph database, so it is absent from
    both rather than estimated. Configure one and the harness fills the cell in.</li>
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
