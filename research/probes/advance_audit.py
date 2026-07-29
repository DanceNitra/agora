"""Where else can a selector fail to advance? A systematic sweep for one defect class.

Three instances surfaced in a single day, in three unrelated files, each having silently killed an
organ for days or weeks:

  _task_already_pending   a de-dup guard with no expiry     -> organ shut 4 days
  challenge sweep         selector with no cursor           -> 2 organs dead 42 days
  verify_contributions    budget spent from index 0         -> the whole Seminar dead 32 days

I found none of them by looking. I tripped over each while doing something else, which means the
sample is "whatever I happened to touch" and the true count is unknown. This looks for the rest.

FOUR SIGNATURES, because the class wears different clothes in different files:

  A. HEAD-ONLY SELECT   sorted(...)[0] / min(...) / [0] on a filtered pool, handed to a caller that
                        may reject it. If rejection doesn't advance, the same item returns forever.
  B. FRONT-LOADED BUDGET  a loop over a list with a `limit`/`max` counter and no ordering, so a wall
                        of permanent failures at the front consumes the budget every run.
  C. UNBOUNDED GUARD    `if <something>_pending/exists(...): return` with no age check — one stuck
                        item holds the door shut indefinitely.
  D. SILENT REJECT      a filter/gate that `return`s or `continue`s on rejection without recording
                        that it rejected, so the rejection is invisible and un-actionable.

This is a CANDIDATE FINDER, not a verdict machine. Every hit needs reading. The last mechanical scan
I trusted without reading reported nine defects and one was real.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOTS = [r"C:\Users\Danculus\agora\server\agora",
         r"C:\Users\Danculus\agora\agora-game-server"]

SIGS = [
    ("A head-only select",
     re.compile(r"return\s+sorted\([^\n]{0,120}\)\[0\]|=\s*sorted\([^\n]{0,120}\)\[0\]"
                r"|return\s+\w+\[0\]\s*if\s|=\s*min\(\s*\w+\s*,\s*key=")),
    ("B front-loaded budget",
     re.compile(r"for\s+\w+\s+in\s+\w+:[^\n]*\n(?:[^\n]*\n){0,12}?[^\n]*(?:>\s*limit|>=\s*limit"
                r"|>\s*max_\w+|>=\s*max_\w+)\s*:")),
    ("C unbounded guard",
     re.compile(r"if\s+(?:await\s+)?[\w\.]*(?:already_pending|_pending|exists|is_open|has_open)"
                r"\([^\n]{0,80}\)\s*:\s*\n\s*return")),
    ("D silent reject",
     re.compile(r"if\s+not\s+(?:await\s+)?[\w\.]*(?:gate|filter|allow|ok|passes)[\w\.]*"
                r"\([^\n]{0,80}\)\s*:\s*\n\s*(?:return|continue)\s*$", re.M)),
]

#: Already found, fixed, and committed today. Listed so the sweep's output is NEW findings only —
#: and so a future reader can tell the difference between "clean" and "already handled".
KNOWN = {("mcp_server.py", "C"), ("belief_revision.py", "A"), ("seminar.py", "B"),
         ("mcp_server.py", "D"), ("library.py", "A")}


def scan():
    hits = []
    for root in ROOTS:
        for dp, dn, fs in os.walk(root):
            dn[:] = [d for d in dn if d not in {".git", "__pycache__", "node_modules", "archive"}]
            for f in fs:
                if not f.endswith(".py"):
                    continue
                p = os.path.join(dp, f)
                try:
                    src = open(p, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                for label, rx in SIGS:
                    for m in rx.finditer(src):
                        line = src[:m.start()].count("\n") + 1
                        ctx = src[m.start():m.start() + 150].split("\n")[0].strip()
                        hits.append((label, os.path.basename(p), line, ctx[:96],
                                     os.path.relpath(p, root)))
    return hits


hits = scan()
by_sig = {}
for label, base, line, ctx, rel in hits:
    by_sig.setdefault(label, []).append((base, line, ctx, rel))

print(f"scanned {len(ROOTS)} trees\n")
for label in sorted(by_sig):
    rows = by_sig[label]
    code = label[0]
    fresh = [r for r in rows if (r[0], code) not in KNOWN]
    print(f"=== {label}: {len(rows)} hits, {len(fresh)} not already fixed today")
    for base, line, ctx, rel in fresh[:12]:
        print(f"    {rel}:{line}")
        print(f"        {ctx}")
    if len(fresh) > 12:
        print(f"    ... and {len(fresh) - 12} more")
    print()

print("RESOLVED 2026-07-29 — every signature-A hit was read, and the results are recorded here so a")
print("later run does not re-litigate them:")
print("   cartography.pick_untested_bridge   DEFECT, fixed. Mine, written the same day I fixed the")
print("                                      identical shape in the belief sweep six hours earlier.")
print("   forge.top_open_gap                 clean. Queues then POSTs status=queued, so the item")
print("                                      leaves the open pool. consume -> mark -> exclude.")
print("   academy.py min/max over rates      clean. Not a queue; rates move as agents work.")
print("   hypothesis_induction cls[0]        clean, VERIFIED EMPIRICALLY: 5 endpoint calls returned")
print("                                      5 distinct themes. It re-samples randomly, so a")
print("                                      rejected theme is never re-offered.")
print("")
print("   NOTE on that last one: it dodges the deadlock by never remembering. The code comment calls")
print("   it 'the single largest producer of off-mission work' precisely because every firing yields")
print("   a brand-new theme. Avoiding a stuck cursor by having no cursor at all trades one failure")
print("   for another: nothing is ever pursued twice, so a good theme rejected once is lost.")
print("")
print("EVERY LINE ABOVE IS A POINTER, NOT A VERDICT. A hit is only a defect if the rejected or")
print("unprocessed item can REMAIN at the head of the next selection. Read each one; a mechanical")
print("scan I trusted without reading once reported nine defects of which exactly one was real.")
