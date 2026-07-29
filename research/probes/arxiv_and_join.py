"""Did AND-joining a bare arXiv phrase kill the firehose WITHOUT killing real search?

Both ends, because a fix that returns zero papers looks identical to a fix that works if you only
measure the thing you were trying to break. OLD is reconstructed inline (`all:<phrase>`) so the
comparison is against the behaviour that actually shipped, not against a memory of it.

Read-only against live arXiv.
"""
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NS = {"a": "http://www.w3.org/2005/Atom"}

#: the live fallback that read 202 papers, plus the other bare-phrase callers, plus controls
CASES = [
    ("THE BUG   Library fallback", "AI/agent systems"),
    ("bare      distilled topic", "conversational memory long-term dialogue"),
    ("bare      replication topic", "agent memory benchmark"),
    ("CONTROL   structured (untouched)", 'abs:"machine unlearning" AND (abs:verification OR abs:deletion)'),
    ("CONTROL   single word", "unlearning"),
]

#: an on-mission phrase must still match; an off-mission one must not. Both are checked per case.
ON = re.compile(r"memor|agent|unlearn|retriev|forget|erasu|llm|language model|knowledge", re.I)


def fetch(search_query, n=8):
    q = urllib.parse.urlencode({"search_query": search_query, "start": 0,
                                "max_results": n, "sortBy": "relevance"})
    req = urllib.request.Request(f"http://export.arxiv.org/api/query?{q}",
                                 headers={"User-Agent": "agora-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        return None, str(e)[:80]
    return [(e.findtext("a:title", "", NS) or "").strip().replace("\n", " ")
            for e in root.findall("a:entry", NS)], None


def new_query(raw):
    """The shipped transform, copied from research_tool.arxiv_search."""
    if re.search(r'(?:\b(?:all|ti|abs|au|cat|id):)|\b(?:AND|OR|ANDNOT)\b', raw):
        return raw
    terms = [t for t in re.split(r"[^A-Za-z0-9+#-]+", raw) if len(t) > 2]
    return " AND ".join(f"all:{t}" for t in terms) if terms else f"all:{raw}"


print("on-mission share of the top 8 hits, OLD (all:<phrase>, OR-matched) vs NEW (AND-joined)\n")
for label, raw in CASES:
    old_titles, err_o = fetch(f"all:{raw}" if "all:" not in raw and " AND " not in raw else raw)
    new_titles, err_n = fetch(new_query(raw))
    if old_titles is None or new_titles is None:
        print(f"  {label:34s} FETCH FAILED: {err_o or err_n}")
        continue
    o = sum(1 for t in old_titles if ON.search(t))
    n = sum(1 for t in new_titles if ON.search(t))
    print(f"  {label:34s} OLD {o}/{len(old_titles)} on-mission   ->   NEW {n}/{len(new_titles)}")
    if new_titles:
        print(f"      NEW top hit: {new_titles[0][:78]}")
    else:
        print("      NEW RETURNED NOTHING  <-- the fix would starve this caller")
    if old_titles and o < len(old_titles):
        off = next(t for t in old_titles if not ON.search(t))
        print(f"      OLD off-mission hit it used to read IN FULL: {off[:62]}")
    print()
