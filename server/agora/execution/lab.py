"""
The Laboratory — simulation as the third channel of evidence.

The system reads (literature) and watches (live data); now it COMPUTES. When a claim or a
falsifier needs numbers — a Monte Carlo, a decay curve, statistics over Agora's own ledgers —
Claude writes a small script and this runner executes it deterministically: in
agora_output/lab, with a hard timeout, stdout capped, results recorded to a ledger with
source "simulation". Scripts are written ONLY by Claude (who already maintains the codebase),
never by the flash model — the trust boundary stays exactly where it already was.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parents[3] / "agora_output" / "lab"
_STORE = Path(__file__).resolve().parents[2] / ".lab.json"
_TIMEOUT = 60
_OUT_CAP = 10_000


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def models_line(code: str) -> str:
    """What the script says it MODELS — its module docstring or leading comment block, or "".

    The ledger records `name`, which is the QUEST title, and a quest title and the model underneath it
    can disagree completely. A real case: a run named
    `method:basket-goodhart-interior-k In a competitive matrix where frontier k...` printed
    `mean K* = 10.5`, and I read it as an optimal RETRIEVAL DEPTH for recall and nearly rebuilt a product
    default on it. The script models an adversary splitting an effort budget across K PROXY METRICS in an
    incentive scheme. Nothing in the record said so. A number attributed to the wrong subject is worse
    than no number, because it looks like a result.

    ONLY a genuine LEADING block counts — a docstring or `#` lines before any code. An earlier version
    scanned the first 60 lines for any comment and picked up an inline formula
    (`Beta(a,b) with mean qbar => ...`) from inside a function, which describes an equation rather than
    the model and made the record look documented when it was not. Measured on the last 60 runs: 37
    carry no leading description at all. Returning "" for those is the honest answer, and it is what
    makes the gap visible — the fix is that a lab script must OPEN with what it models.
    """
    text = (code or "").lstrip()
    m = re.match(r'^(?:[rubRUB]{0,2})("""|\'\'\')(.*?)\1', text, re.DOTALL)
    if m:
        return " ".join(m.group(2).split())[:400]
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            out.append(s.lstrip("# ").strip())
        elif not s and not out:
            continue
        else:
            break
    return " ".join(out)[:400]


def run_experiment(name: str, code: str) -> dict:
    """Persist + execute one experiment script; record the outcome in the lab ledger."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "experiment").lower()).strip("-")[:50]
    eid = uuid.uuid4().hex[:6]
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    path = LAB_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{slug}.py"
    path.write_text(code, encoding="utf-8")
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", str(path)],
                           cwd=str(LAB_DIR), capture_output=True, text=True,
                           timeout=_TIMEOUT, encoding="utf-8", errors="replace")
        ok = r.returncode == 0
        output = (r.stdout or "")[:_OUT_CAP] + (("\n[stderr] " + r.stderr[:1500]) if (not ok and r.stderr) else "")
    except subprocess.TimeoutExpired:
        ok, output = False, f"[timeout after {_TIMEOUT}s]"
    # `undocumented` rather than a mismatch FLAG. The flag I first wrote compared the title's vocabulary
    # against the model's and was wrong on both of its own test cases — it cleared the run that fooled me
    # (they happened to share the word "basket") and flagged the honest control, ending at 87% flagged,
    # which is a guard that fires on everything and therefore says nothing. Dropped rather than tuned:
    # what is verifiable here is whether the script SAYS what it models, not whether a bag of words
    # agrees with the quest title.
    models = models_line(code)
    rec = {"id": eid, "name": (name or slug)[:120], "script": str(path),
           "models": models, "undocumented": not models,
           "ok": ok, "seconds": round(time.time() - t0, 1),
           "output": output.strip()[:_OUT_CAP], "source": "simulation", "ts": time.time()}
    items = _load()
    items.append(rec)
    # Ledger cap 1000 (was 100): at ~100 runs/day the old cap rotated a lab_id out within ~12h, so the
    # LAB-FIRST gate falsely rejected discoveries citing a REAL-but-older experiment (src_no_lab), and
    # audits couldn't find source scripts. 1000 keeps ~1-2 weeks of receipts; file stays ~1 MB.
    _save(_prune(items))
    return rec


#: Stores that CITE a lab id. A run referenced from any of these is a published receipt and must
#: never rotate out of the ledger, however old it gets.
_CITING_STORES = (".press.json", "../public/crucible/crucible.json", ".replications.json")

#: Optional manual pins, for receipts cited OUTSIDE this repo -- a GitHub comment, an email, a paper.
#: Derived citations cannot see those, so this is the escape hatch. Format: {"lab_id": "why"}.
_PINS = _STORE.parent / ".lab_pins.json"

#: `lab 2b7e05`, "lab `2b7e05`", '"lab_id": "2b7e05"' -- six hex characters, and NOT part of a longer
#: hex or decimal run. Without those lookarounds the id 619055 matches inside the float
#: 0.861905574798584, which is how a first pass at this reported five recoverable receipts that did
#: not exist. A keyword match with no subject check over-reports, every time.
_LAB_ID_RE = re.compile(r"(?<![0-9a-fA-F.])(?:lab|lab_id)[\s:=_\"'`]*([0-9a-f]{6})(?![0-9a-fA-F])", re.I)


def cited_ids() -> set:
    """Lab ids referenced by anything we have published or recorded as a receipt.

    DERIVED, never hand-maintained. A manual pin list is a second place to forget, and the failure
    this exists to prevent IS a forgetting: nine published pieces were found citing lab receipts the
    ledger no longer held, five of which have no runnable artifact anywhere in the repo -- including
    two entries in the public Crucible, whose entire premise is that a claim ships with the test that
    would kill it. A citation is not a receipt if the receipt has been deleted.
    """
    found = set()
    for rel in _CITING_STORES:
        p = (_STORE.parent / rel).resolve()
        try:
            found.update(m.lower() for m in _LAB_ID_RE.findall(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    try:
        found.update(k.lower() for k in json.loads(_PINS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return found


def _prune(items: list, cap: int = 1000) -> list:
    """Trim to `cap`, but never drop a run whose id is cited by published work.

    The cap exists to bound file size, and it should keep doing that. What it must not do is delete
    the evidence half of something we have already asserted in public: at ~100 runs/day a receipt
    rotates out in about ten days, while a published post lives for years, so a lab id in a post is a
    pointer into a rotating buffer that LOOKS like a receipt.
    """
    if len(items) <= cap:
        return items
    keep = cited_ids()
    tail = items[-cap:]
    tail_ids = {str(r.get("id", "")).lower() for r in tail}
    rescued = [r for r in items[:-cap]
               if str(r.get("id", "")).lower() in keep and str(r.get("id", "")).lower() not in tail_ids]
    return rescued + tail


def recent(n: int = 10) -> list:
    return _load()[-n:]


def format_lab(n: int = 6) -> str:
    items = _load()[-n:]
    if not items:
        return "🧫 _The laboratory is dark — no experiments run yet._"
    lines = [f"🧫 *The Laboratory* — {len(_load())} experiments on record"]
    for x in reversed(items):
        head = (x["output"].splitlines() or [""])[0][:80]
        lines.append(f"{'✅' if x['ok'] else '❌'} {x['name'][:48]} _({x['seconds']}s)_")
        if head:
            lines.append(f"   `{head}`")
    return "\n".join(lines)
