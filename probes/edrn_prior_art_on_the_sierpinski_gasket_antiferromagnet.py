"""Everything published on the quantum antiferromagnet on the Sierpinski gasket.

Written because I told a collaborator his reference list was incomplete and then handed him an
incomplete list myself. My letter named two prior studies. An adversarial pass found two more, one of
them published by the journal that had just rejected him. That is the same defect I was correcting,
one level down, so this enumerates rather than recalls.

POSITIVE CONTROL, and the reason this file can fail. Four papers are known to exist before the search
runs. If any query set misses one of them, that query set is not an absence test and its zeros mean
nothing:

  Voigt, Richter, Tomczak, JMMM 183, 68 (1998)          cond-mat/9710227
  Voigt, Richter, Tomczak, Physica A 299, 461 (2001)    cond-mat/0108472
  Voigt, Wenzel, Richter, Tomczak, EPJ B 38, 49 (2004)  cond-mat/0403147
  Zou and Wang, Chinese Phys. Lett. 40, 057501 (2023)   2105.12487

The last one matters most: CPL published the spin-1/2 Heisenberg antiferromagnet on a fractal three
years before it rejected our manuscript for insufficient impact. That is checkable, so the letter
must stop saying it cannot know what the editor meant.

Run:  python -X utf8 probes/edrn_prior_art_on_the_sierpinski_gasket_antiferromagnet.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

MUST_FIND = {
    "cond-mat/9710227": "Voigt, Richter, Tomczak, JMMM 183, 68 (1998)",
    "cond-mat/0108472": "Voigt, Richter, Tomczak, Physica A 299, 461 (2001)",
    "cond-mat/0403147": "Voigt, Wenzel, Richter, Tomczak, EPJ B 38, 49 (2004)",
    "2105.12487": "Zou and Wang, Chinese Phys. Lett. 40, 057501 (2023)",
}

QUERIES = [
    'all:"Sierpinski gasket" AND all:Heisenberg',
    'all:"Sierpinski gasket" AND all:antiferromagnet',
    'all:"Sierpinski gasket" AND all:"quantum spin"',
    'all:"Sierpinski" AND all:"spin-1/2"',
    'all:"Sierpinski" AND all:"spin liquid"',
    'all:fractal AND all:"Heisenberg antiferromagnet"',
    'all:fractal AND all:"quantum antiferromagnet"',
    'all:"fractal lattice" AND all:"spin-1/2"',
]

SUBJECT = re.compile(r"sierpinski|gasket|fractal", re.I)
SPIN = re.compile(r"heisenberg|antiferromagnet|spin liquid|quantum spin|spin-1/2|spin 1/2", re.I)


def arxiv(query, n=60):
    url = ("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(query) +
           "&start=0&max_results=%d&sortBy=submittedDate&sortOrder=descending" % n)
    for attempt in range(3):
        try:
            return urllib.request.urlopen(url, timeout=90).read().decode("utf-8", "replace")
        except Exception as exc:                                  # noqa: BLE001
            if attempt == 2:
                print("  query failed after 3 tries: %s" % exc)
                return ""
            time.sleep(5)
    return ""


def entries(xml):
    out = []
    for block in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        def one(tag):
            m = re.search(r"<%s>(.*?)</%s>" % (tag, tag), block, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        aid = one("id")
        aid = re.sub(r"^https?://arxiv\.org/abs/", "", aid)
        aid = re.sub(r"v\d+$", "", aid)
        jr = re.search(r"journal_ref>(.*?)<", block, re.S)
        out.append({
            "id": aid,
            "title": one("title"),
            "summary": one("summary"),
            "published": one("published")[:10],
            "journal_ref": re.sub(r"\s+", " ", jr.group(1)).strip() if jr else "",
            "authors": re.findall(r"<name>(.*?)</name>", block),
        })
    return out


def main():
    found, per_query = {}, {}
    print("querying arXiv, %d query forms" % len(QUERIES))
    for q in QUERIES:
        hits = entries(arxiv(q))
        keep = [h for h in hits if SUBJECT.search(h["title"] + " " + h["summary"])
                and SPIN.search(h["title"] + " " + h["summary"])]
        per_query[q] = sorted({h["id"] for h in keep})
        for h in keep:
            found.setdefault(h["id"], h)
        print("  %-58s %3d hits, %2d on subject" % (q[:58], len(hits), len(keep)))
        time.sleep(3)

    print("\n-- POSITIVE CONTROL: are the four known papers in the union? --")
    missing = []
    for aid, name in MUST_FIND.items():
        ok = aid in found
        print("  %-6s %-20s %s" % ("FOUND" if ok else "MISS", aid, name))
        if not ok:
            missing.append(aid)

    print("\n-- which single query form finds each known paper --")
    for aid, name in MUST_FIND.items():
        hitters = [q for q, ids in per_query.items() if aid in ids]
        print("  %-20s %d of %d query forms" % (aid, len(hitters), len(QUERIES)))
        if len(hitters) == 1:
            print("      ONLY: %s" % hitters[0])

    print("\n-- the union, newest first --")
    rows = sorted(found.values(), key=lambda h: h["published"], reverse=True)
    for h in rows:
        print("  %s  %-13s  %s" % (h["published"], h["id"], h["title"][:70]))
        if h["journal_ref"]:
            print("      %s" % h["journal_ref"])
        print("      %s" % ", ".join(h["authors"][:5]))

    published = [h for h in rows if h["journal_ref"]]
    print("\n%d on subject, %d with a journal reference" % (len(rows), len(published)))

    cpl = [h for h in published if "chinese phys" in h["journal_ref"].lower()]
    print("\n-- published by Chinese Physics Letters --")
    for h in cpl:
        print("  %s  %s" % (h["journal_ref"], h["title"][:66]))
    if not cpl:
        print("  none found, so do not tell the collaborator CPL has published this model")

    report = {"queries": QUERIES, "per_query": per_query, "union": rows,
              "positive_control_missing": missing, "cpl_papers": cpl,
              "n_on_subject": len(rows), "n_published": len(published)}
    out = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)

    print()
    if missing:
        print("CONTROL FAILED: the search missed %d paper(s) known to exist: %s"
              % (len(missing), ", ".join(missing)))
        print("A zero from this search would therefore mean nothing. Fix the queries.")
        report["verdict"] = "FAILED"
    else:
        print("VERDICT: OK. All four known papers were recovered, so the union is an absence test.")
        report["verdict"] = "OK"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
    print("wrote %s" % os.path.basename(out))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
