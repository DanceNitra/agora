"""Is the collapse a defect, or did my fixture deserve it?

consolidate(keep=10) left 1 active of 30. But my 30 texts were "the billing service fact number 3",
"...number 7", differing by a digit — a dream pass is SUPPOSED to collapse those. The fair test is
thirty genuinely different facts. If those also collapse to one, it is a defect; if they survive, my
fixture was degenerate and `kept` needs reading against the docstring, not against my assumption.
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

DISTINCT = [
    "the billing API authenticates callers with OAuth2 bearer tokens",
    "the staging database runs on host db-staging-07 in eu-west-1",
    "the deploy script targets the main branch by default since March",
    "the Pro pricing tier costs 39 dollars per month with annual billing",
    "the cache layer evicts entries using a two-tier value-protected policy",
    "sessions in the auth service expire after 15 minutes of inactivity",
    "the nightly report job runs at 02:00 UTC and pages on failure",
    "Maria is the technical lead of project Atlas since the reorg",
    "the search index is rebuilt weekly from the primary replica",
    "the payments gateway retries failed captures three times",
    "the mobile client caches avatars for seven days on device",
    "the ingest worker batches events in windows of five seconds",
    "the audit log is retained for ninety days then archived to cold storage",
    "feature flags roll out to five percent of traffic before a full release",
    "the CDN edge serves static assets from thirty-two points of presence",
    "the queue consumer acknowledges messages only after a durable write",
    "the metrics pipeline samples traces at one percent under load",
    "the backup vault keeps three generations of encrypted snapshots",
    "the tenant router shards customers by a hash of their account id",
    "the webhook relay signs every callback with an HMAC header",
    "the scheduler skips runs when the previous execution is still active",
    "the object store lifecycle moves blobs to archive after one year",
    "the rate limiter allows one hundred requests per minute per key",
    "the config service reloads without restarting dependent processes",
    "the notification hub deduplicates alerts within a ten minute window",
    "the session store evicts anonymous sessions after one hour",
    "the invoice renderer produces PDFs with embedded structured data",
    "the fraud scorer flags transactions above the ninety-fifth percentile",
    "the email dispatcher throttles to two hundred messages per second",
    "the image resizer generates three variants for every upload",
]

for label, texts in (("near-identical (my first fixture)",
                      [f"the billing service fact number {i}" for i in range(30)]),
                     ("genuinely distinct facts", DISTINCT)):
    st = Inspeximus(path=None, receipts=True)
    for i, t in enumerate(texts):
        st.remember(t, key=f"k{i}", object=f"v{i}", source={"doc": f"team-{i % 3}"})
    before = Counter(r.get("status") for r in st.items)
    rep = st.consolidate(keep=10)
    after = Counter(r.get("status") for r in st.items)
    active = after.get("active", 0)
    print(f"=== {label} ===")
    print(f"  report : {json.dumps(rep, default=str)}")
    print(f"  active {before.get('active')} -> {active}   (asked to keep 10)")
    print(f"  recall  'billing' -> {len(st.recall('billing', k=10))} hits")
    print(f"  {'COLLAPSED to one' if active <= 1 else 'survived'}\n")

print("=== what the contract says `keep` does ===")
import inspect
doc = inspect.getdoc(Inspeximus.consolidate) or ""
for ln in doc.splitlines():
    if "keep" in ln.lower() or "budget" in ln.lower():
        print("   |", ln[:118])
