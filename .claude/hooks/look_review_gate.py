"""PreToolUse hook on SendUserFile (owner rule 2026-11-08: "nikto ta neudituje a sam sa prehovaras ze to je dobre").

Refuses to send a Depesa look image (anything under .../gpt-image-2-6-personas/3d/makeup/ that is an image)
unless makeup/review/ holds, for that round, BOTH a measurement file (<tag>.json from look_review.py) and an
independent audit (<tag>_audit.md written by a subagent that saw only the sheet and p6), and both are newer
than every image being sent. Review sheets themselves (makeup/review/*) are exempt so the audit can be shown.
"""
import json, os, sys, glob

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if data.get("tool_name") != "SendUserFile":
    sys.exit(0)
files = (data.get("tool_input") or {}).get("files") or []
IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif")
hits = []
for f in files:
    p = os.path.abspath(f).replace("\\", "/")
    if "/gpt-image-2-6-personas/3d/makeup/" in p and p.lower().endswith(IMG) and "/makeup/review/" not in p:
        hits.append(p)
if not hits:
    sys.exit(0)
rev = os.path.join(os.path.dirname(hits[0].split("/makeup/")[0] + "/makeup/x"), "review")
newest = max(os.path.getmtime(h) for h in hits if os.path.exists(h)) if any(os.path.exists(h) for h in hits) else 0
audits = [a for a in glob.glob(os.path.join(rev, "*_audit.md")) if os.path.getmtime(a) >= newest]
meas = [m for m in glob.glob(os.path.join(rev, "*.json")) if os.path.getmtime(m) >= newest]
if audits and meas:
    sys.exit(0)
print("look_review_gate: BLOCKED. A Depesa look image goes to the owner only after the review round:\n"
      "  1. python makeup/look_review.py <render.png> <tag>   (sheet beside p6 + measured holes and brow-to-ridge)\n"
      "  2. an independent subagent audits makeup/review/<tag>_sheet.png against p6 WITHOUT my conclusion and\n"
      "     writes makeup/review/<tag>_audit.md\n"
      "  Both must be newer than the images being sent. Never grade the look myself.", file=sys.stderr)
sys.exit(2)
