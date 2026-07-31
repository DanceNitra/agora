"""
Sage Mira, Knowledge Curator -- the CANON organ (press is the secondary arm).

WHY THIS EXISTS (every number below was read off the live system, not assumed)
----------------------------------------------------------------------------
Mira's apparent productivity was a STRING LITERAL. She produced 2 real discoveries in 5 days,
yet 32 of the 36 vault notes carried her name -- because `server/agora/api/agent_os_api.py:591`
writes every promoted finding with a hardcoded `agent_name="Sage Mira"`. The roster looked like
one agent doing 89% of the work; nobody was doing it.

Her one real organ has NEVER RUN. `mcp_server.py:3888` gates consolidation at
`standing < 0.55`. Live standing (agora-game-server/agent_standing.json, re-read 2026-07-31):
Mira 0.452, and the ceiling across all eight is 0.486 (Voss). Under a ceiling of 0.486 a gate at
0.55 is not a high bar, it is an OFF SWITCH -- the branch is unreachable for every agent, so the
consolidation code has never executed once.

And the canon shows it. Measured 2026-07-31 from GET /brain/canon-inputs:
  - 6697 chars = 96% of the standing 7000-char budget
  - 22 belief bullets, 14 Lab receipts
  - 0 near-duplicate belief pairs at containment >= 0.6  (it is CLEAN, not bloated)
  - last `updated:` 2026-07-19 -- 12 days stale
  - 7 artifacts landed since, and 0 of them carry a citation, a Lab id, or MEASURED/VERDICT
So the canon does not need more prose. It has 303 chars of headroom and a queue of ungrounded
claims. What it needs is a curator whose default answer is NO, and whose most valuable output is
a REMOVAL. That is what this organ is: an anti-accretion curator, not a note generator.

OWNERSHIP: `.analogies.json` belongs to High Priest Orin (audited in
`server/agora/execution/repair_ledger.py:46`), NOT to Mira, despite `agent_activity.py:44`
attributing it to her. Mira owns the CANON and the PRESS. This organ touches nothing else.

THE GATE (the reason this is safe to run unattended)
----------------------------------------------------
`POST /brain/canon-write` REPLACES the canon wholesale. An automatic writer that gets it wrong
destroys the organization's statement of belief. So no candidate canon is ever posted on this
organ's own say-so: the before/after pair is handed to `ctx.lab_run`, which re-derives the
numbers in a SEPARATE PROCESS and prints `VERDICT: PASS` or `VERDICT: FAIL`. The organ writes
only on PASS, so the severe-test rule holds by construction (a merge ships with a runnable Lab
baseline measured in the same cycle) and every failure mode ends in "canon unchanged".

Structurally the organ removes and inserts whole top-level bullet blocks only. It never edits a
heading, a lead paragraph, a Falsifier line, or the Track-record tail. Re-clustering the canon is
a judgment call and stays with Claude (the A14 loop task); a 6-hourly robot does not restructure
a book.

PRESS IS OWNER-GATED AND MIRA CANNOT DECIDE IT. `POST /brain/press/draft` PROPOSES and Telegrams
the owner; only he turns a proposal into `published`. Therefore a press proposal returns
`decisive=False` here -- the incentive to fake decisiveness by drafting is removed at the source.
There is no publish call in this file.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import re
import textwrap
import time
from pathlib import Path

ORGAN = {
    "eid": "scholar", "agent": "Sage Mira", "name": "Knowledge Curator",
    "ledger": ".press.json",
    "decisive": ("merged", "published", "rejected"),
    "period_hours": 6.0,                      # ~4x/day
}

# ---------------------------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------------------------
CANON_BUDGET = 7000        # standing repo rule: the canon is a statement of belief, not an archive
CANON_MIN = 200            # /brain/canon-write rejects anything shorter (agent_os_api.py:1647)
NOVELTY = 0.6              # the repo-calibrated containment threshold -- see _load_metric()
MAX_DROPS = 3              # per cycle; a bigger cull is a judgment call, not a robot's
MAX_ADMITS = 2             # per cycle; accretion is the failure mode this organ exists to stop
PRESS_MIN_SCORE = 3        # press.pick_target() scores measured numbers 3x -- below this, no numbers

# Exactly 6, because a lab id IS `uuid4().hex[:6]` (execution/lab.py:78). A looser {4,8} also
# matched "lab 2026" and would have handed a press draft a receipt that is a year.
_LAB_ID = re.compile(r"[Ll]ab\s*[`'\"]?([0-9a-f]{6})[`'\"]?")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_HEAD = re.compile(r"^##\s+\S")
_H1 = re.compile(r"^#\s+\S", re.M)

# The containment metric is calibrated repo-wide; this organ must not invent a second one.
# It lives in the brain package, which is not importable from the dungeon process, so it is
# loaded BY PATH. If it cannot be loaded, the organ does nothing at all rather than fall back to
# a private copy that would silently drift away from the number the rest of the repo gates on.
_FD_PATH = Path(__file__).resolve().parents[2] / "server" / "agora" / "execution" / "finding_diversity.py"


def _load_metric():
    """(tokens, containment, source) from server/agora/execution/finding_diversity.py, or Nones.
    `source` is that module's citation detector -- reused for the same reason as containment: the
    definition of "carries a real citation" must not fork."""
    try:
        spec = importlib.util.spec_from_file_location("agora_finding_diversity_for_scholar", _FD_PATH)
        if spec is None or spec.loader is None:
            return None, None, None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)                       # stdlib-only module, no side effects
        return mod._tokens, mod._containment, mod._source
    except Exception:
        return None, None, None


_TOKENS, _CONTAINMENT, _SOURCE = _load_metric()

# Same reasoning, same mechanism: "does this note state its falsifier?" must not fork either. The
# press bar refuses a claim that cannot say what would kill it, and this organ was asking with a
# literal substring test for "falsifier" while the Theory Engine writes "falsification control:" --
# so a note that DID state one was refused for not stating one.
_GROUNDING_PATH = Path(__file__).resolve().parents[2] / "server" / "agora" / "execution" / "grounding.py"


def _load_falsifier_test():
    try:
        spec = importlib.util.spec_from_file_location("agora_grounding_for_scholar", _GROUNDING_PATH)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)                       # stdlib-only module, no side effects
        return mod.has_falsifier
    except Exception:
        return None


_FALSIFIER_TEST = _load_falsifier_test()


def _has_falsifier(text: str) -> bool:
    """Fail CLOSED. If the shared definition cannot be loaded, no press is drafted -- publishing a
    claim whose falsifier nobody checked is worse than publishing nothing, and a private fallback
    would be a second standard drifting away from the one the rest of the repo gates on."""
    return bool(_FALSIFIER_TEST(text or "")) if _FALSIFIER_TEST else False


# ---------------------------------------------------------------------------------------------
# ctx plumbing -- the dispatcher owns ctx, so every call is defensive about sync/async and shape
# ---------------------------------------------------------------------------------------------
async def _aw(value):
    """Await `value` if it is awaitable; ctx helpers may be sync or async."""
    return await value if inspect.isawaitable(value) else value


def _log(ctx, msg: str) -> None:
    """ASCII-only log line (the console is cp1250; a non-ASCII print can 500 a request)."""
    try:
        line = msg.encode("ascii", "replace").decode("ascii")
        lg = getattr(ctx, "logger", None)
        if lg is not None and hasattr(lg, "info"):
            lg.info("[scholar] %s", line)
    except Exception:
        pass


def _result(status: str, why: str, *, decisive: bool = False, title: str = "",
            content: str = "", lab_id=None) -> dict:
    return {"status": status, "decisive": decisive, "title": title,
            "content": content, "lab_id": lab_id, "why": why}


def _lab_fields(rec) -> tuple:
    """(lab_id, output) out of whatever ctx.lab_run returned."""
    if not isinstance(rec, dict):
        return None, ""
    lab_id = rec.get("id") or rec.get("lab_id") or rec.get("lab")
    out = rec.get("output") or rec.get("stdout") or rec.get("result") or ""
    return (str(lab_id) if lab_id else None), (out if isinstance(out, str) else str(out))


async def _recalled_texts(ctx, query: str) -> list:
    """Mira's own inspeximus memory, flattened to plain strings. Never raises."""
    try:
        got = await _aw(ctx.recall(query))
    except Exception:
        return []
    out = []
    items = got if isinstance(got, list) else (got or {}).get("results") if isinstance(got, dict) else None
    for it in (items or []):
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, dict):
            out.append(" ".join(str(it.get(k, "")) for k in ("title", "content", "text", "value")))
    return [x for x in out if x.strip()]


async def _already_ruled(ctx, queries: list, claim: str) -> bool:
    """True when Mira has already issued this exact curation ruling -- the anti-repeat gate.
    Uses the same calibrated containment threshold as the rest of the repo. Several queries,
    because a semantic store retrieves on the distinctive string (a claim title), not on a
    generic one, and a novelty gate that never retrieves is a gate that never fires."""
    claim_t = _TOKENS(claim)
    for q in queries:
        if not q:
            continue
        for text in await _recalled_texts(ctx, q):
            if _CONTAINMENT(claim_t, _TOKENS(text)) >= NOVELTY:
                return True
    return False


# ---------------------------------------------------------------------------------------------
# Canon structure -- whole top-level bullet blocks are the only movable unit
# ---------------------------------------------------------------------------------------------
def _bullets(lines: list) -> list:
    """Top-level `- ` blocks with their 2-space continuation lines, tagged with their `## ` cluster.

    YAML frontmatter and fenced code are SKIPPED, and that is not defensive padding: a frontmatter
    `tags:` list is made of `- ` lines, and two tags such as `- agora` / `- agora-research` sit at
    containment 1.0, so a parser that reads them as beliefs would "retire" a line of frontmatter.
    A ``` fence can carry `- ` lines just as easily. Reproduced in review before this guard existed.
    """
    out, head, i, n = [], -1, 0, len(lines)
    if n and lines[0].strip() == "---":                    # frontmatter block, verbatim, untouchable
        i = 1
        while i < n and lines[i].strip() != "---":
            i += 1
        i = min(i + 1, n)
    fence = False
    while i < n:
        if lines[i].lstrip().startswith("```"):
            fence = not fence
            i += 1
            continue
        if fence:
            i += 1
            continue
        if _HEAD.match(lines[i]):
            head, i = i, i + 1
            continue
        if lines[i].startswith("- "):
            j = i + 1
            while j < n and lines[j].startswith("  ") and lines[j].strip():
                j += 1
            out.append({"start": i, "end": j, "head": head, "text": "\n".join(lines[i:j])})
            i = j
            continue
        i += 1
    return out


def _receipts(text: str) -> set:
    return set(_LAB_ID.findall(text or ""))


def _grounding(text: str):
    """(kind, detail) if the text carries a real receipt, else (None, '').
    Accepted: a Lab id, a real citation, or MEASURED:+VERDICT:. Prose alone is not evidence."""
    ids = sorted(_receipts(text))
    if ids:
        return "lab", ids[0]
    up = (text or "").upper()
    if "MEASURED:" in up and "VERDICT:" in up:
        return "measured", "MEASURED/VERDICT"
    cite = _SOURCE(text or "") if _SOURCE else None        # e.g. "Breznau et al. (2022)"
    if cite:
        return "citation", cite
    return None, ""


def _head(text: str, n: int = 90) -> str:
    """First line of a belief block, without its bullet marker -- for human-readable records."""
    return re.sub(r"^-\s+", "", (text or "").split("\n")[0]).strip()[:n]


def _as_int(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _weight(text: str) -> tuple:
    """Which of two near-duplicate beliefs to keep: receipts first, then measured numbers, then length."""
    return (len(_receipts(text)), len(_NUM.findall(text or "")), len(text or ""))


def _render(lines: list, drop_blocks: list, admits: list) -> str:
    """Rebuild the canon with `drop_blocks` removed and `admits` inserted. Nothing else moves."""
    skip = set()
    for b in drop_blocks:
        skip.update(range(b["start"], b["end"]))
    ins = {}
    for a in admits:
        ins.setdefault(a["at"], []).extend(a["lines"])
    out = []
    for i, ln in enumerate(lines):
        for extra in ins.get(i, []):
            out.append(extra)
        if i not in skip:
            out.append(ln)
    for extra in ins.get(len(lines), []):
        out.append(extra)
    return "\n".join(out)


def _admit_lines(title: str, claim: str, receipt: str, kind: str) -> list:
    """One belief bullet, wrapped to the canon's line width. The receipt is rendered in the form
    the canon already uses for that evidence kind -- a Lab id is not a citation."""
    tail = (" -- " + re.sub(r"\s+", " ", claim).strip()[:260]) if claim else ""
    stamp = ("Lab `%s`" % receipt) if kind == "lab" else receipt
    text = "- **%s** (*active*, %s)%s" % (title.strip()[:120], stamp, tail)
    return textwrap.wrap(text, width=100, subsequent_indent="  ",
                         break_long_words=False, break_on_hyphens=False) or [text]


# ---------------------------------------------------------------------------------------------
# The plan -- pure functions, no I/O, so it can be reasoned about and tested offline
# ---------------------------------------------------------------------------------------------
def _plan(canon: str, artifacts: list, labs: list) -> dict:
    """Classify every pending artifact and every existing belief. Decides nothing on its own."""
    lines = canon.split("\n")
    bl = _bullets(lines)
    btok = [_TOKENS(b["text"]) for b in bl]
    plan = {"lines": lines, "bullets": bl, "drop": [], "admit": [], "reject": [], "judgment": [],
            "defer": [], "chars": len(canon), "dup_pairs": 0}

    # 1) Existing near-duplicates. Dropping the weaker of a restated pair is the highest-value act
    #    -- unless BOTH carry a Lab receipt the other lacks, in which case a drop would destroy a
    #    measurement and the pair is escalated to Claude instead.
    dropped = set()
    for i in range(len(bl)):
        for j in range(i + 1, len(bl)):
            if _CONTAINMENT(btok[i], btok[j]) < NOVELTY:
                continue
            plan["dup_pairs"] += 1
            if i in dropped or j in dropped:
                continue
            ri, rj = _receipts(bl[i]["text"]), _receipts(bl[j]["text"])
            weak, keep = (j, i) if _weight(bl[i]["text"]) >= _weight(bl[j]["text"]) else (i, j)
            lost = (ri - rj) if weak == i else (rj - ri)
            head_w = _head(bl[weak]["text"], 80)
            if lost:
                plan["judgment"].append(
                    "near-duplicate pair, both hold a unique receipt (%s) -- a drop would lose a "
                    "measurement: %s" % (", ".join(sorted(lost)), head_w))
                continue
            if len(plan["drop"]) < MAX_DROPS:
                dropped.add(weak)
                plan["drop"].append({"block": bl[weak], "keep": _head(bl[keep]["text"], 80),
                                     "why": "restates the retained belief at containment %.2f"
                                            % _CONTAINMENT(btok[i], btok[j])})

    # 2) Pending artifacts. Default answer is NO: a claim with no receipt is not a belief.
    lab_ok = [x for x in (labs or []) if isinstance(x, dict) and x.get("ok") and x.get("id")]
    lab_tok = [(_TOKENS(str(x.get("name", ""))), x) for x in lab_ok]
    for art in (artifacts or []):
        title = str(art.get("title") or "").strip()
        core = str(art.get("core") or "").strip()
        if not title:
            continue
        # GRADE ON THE WHOLE ARTIFACT, not on the slice that happened to parse. The receipt line is
        # scanned from anywhere in the note, because a Lab id under "## The test" was invisible to a
        # grader looking only at title+core, and a fully grounded note was rejected for having no
        # receipt. Novelty is still measured on title+core alone -- a receipt is evidence, not subject
        # matter, and folding it into the tokens would make two notes citing one Lab look alike.
        blob = title + " " + core
        graded = blob + " " + str(art.get("receipt_line") or "")
        atok = _TOKENS(blob)
        near = max(((_CONTAINMENT(atok, t), k) for k, t in enumerate(btok)), default=(0.0, -1))
        kind, detail = _grounding(graded)
        if kind is None:                      # last honest chance: a Lab run whose NAME is this claim
            for t, rec in lab_tok:
                if _CONTAINMENT(atok, t) >= NOVELTY:
                    kind, detail, core = "lab", str(rec["id"]), (core or _measured_line(rec))
                    break
        if kind is None:
            plan["reject"].append({"title": title,
                                   "why": "no receipt: no Lab id, no citation, no MEASURED/VERDICT"})
            continue
        if near[0] >= NOVELTY:
            # Grounded AND it restates a standing belief -> it must CHANGE that belief, not sit
            # beside it. Rewriting a belief paragraph is prose work; escalate rather than mangle.
            plan["judgment"].append(
                "grounded artifact restates a standing belief at containment %.2f -- it should "
                "REPLACE it, which needs a written merge: %s" % (near[0], title[:90]))
            continue
        if len(plan["admit"]) < MAX_ADMITS:
            plan["admit"].append({"title": title, "core": core, "receipt": detail,
                                  "kind": kind, "head": bl[near[1]]["head"] if near[1] >= 0 else -1})
        else:
            # Grounded and admissible, but over this cycle's budget. Recorded, never silently
            # dropped -- a queue that disappears is how a curator loses the org's best material.
            plan["defer"].append(title)
    return plan


def _measured_line(rec: dict) -> str:
    for ln in str(rec.get("output") or "").split("\n"):
        if ln.strip().upper().startswith("MEASURED:"):
            return ln.strip()
    return ""


def _place(plan: dict, admit: dict):
    """Insertion point: the end of the cluster whose existing bullets this claim sits closest to."""
    bl = plan["bullets"]
    if not bl:
        return None
    atok = _TOKENS(admit["title"] + " " + admit.get("core", ""))
    best, best_v = None, -1.0
    for b, t in zip(bl, (_TOKENS(x["text"]) for x in bl)):
        v = _CONTAINMENT(atok, t)
        if v > best_v:
            best, best_v = b, v
    tail = max((b["end"] for b in bl if b["head"] == best["head"]), default=best["end"])
    return tail


# ---------------------------------------------------------------------------------------------
# The Lab gate -- an independent process re-derives the numbers and can REFUSE the write
# ---------------------------------------------------------------------------------------------
_SCRIPT_DOC = '''"""Canon curation gate -- models the merge as a set operation on belief bullets.

Re-derives, from the before/after canon text alone, the four properties a canon merge must hold:
budget, structure, receipt conservation, and duplicate non-increase. Loads the repo-calibrated
containment metric from finding_diversity.py by path (the same number the rest of the repo gates
on); if that metric is unavailable the gate FAILS rather than guessing. The caller writes the
canon only on VERDICT: PASS, so a bug here blocks the write instead of corrupting the canon.
"""
'''

_SCRIPT = '''
import importlib.util
import re
import sys

P = json.loads(PAYLOAD_JSON)

spec = importlib.util.spec_from_file_location("fd", P["metric_path"])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
tokens, containment = mod._tokens, mod._containment

# The same patterns the caller uses, shipped in the payload so the gate cannot drift from it.
HEAD = re.compile(P["head_pattern"])
LAB = re.compile(P["lab_pattern"])


def bullets(text):
    """Same rule as the caller: frontmatter and fenced code are not beliefs."""
    lines, out, i, n = text.split("\\n"), [], 0, 0
    n = len(lines)
    if n and lines[0].strip() == "---":
        i = 1
        while i < n and lines[i].strip() != "---":
            i += 1
        i = min(i + 1, n)
    fence = False
    while i < n:
        if lines[i].lstrip().startswith("```"):
            fence = not fence
            i += 1
            continue
        if fence:
            i += 1
            continue
        if lines[i].startswith("- "):
            j = i + 1
            while j < n and lines[j].startswith("  ") and lines[j].strip():
                j += 1
            out.append("\\n".join(lines[i:j]))
            i = j
            continue
        i += 1
    return out


def dup_pairs(text):
    bs = [tokens(b) for b in bullets(text)]
    return sum(1 for i in range(len(bs)) for j in range(i + 1, len(bs))
               if containment(bs[i], bs[j]) >= P["threshold"])


before, after = P["before"], P["after"]
fails = []

if after is None:                      # AUDIT mode -- nothing is being written this cycle
    print("MEASURED: canon %d chars (%d%% of the %d budget); %d belief bullets; %d Lab receipts; "
          "%d near-duplicate pairs at containment>=%.2f; %d/%d pending artifacts carry no receipt"
          % (len(before), round(100 * len(before) / P["budget"]), P["budget"], len(bullets(before)),
             len(set(LAB.findall(before))), dup_pairs(before), P["threshold"],
             P["n_reject"], P["n_artifacts"]))
    print("VERDICT: HOLD -- canon unchanged; %d artifact(s) held out for lack of a receipt, "
          "%d item(s) escalated for a written merge" % (P["n_reject"], P["n_judgment"]))
    sys.exit(0)

b_ids, a_ids = set(LAB.findall(before)), set(LAB.findall(after))
lost = sorted(b_ids - a_ids - set(P["retired"]))
b_heads = [l for l in before.split("\\n") if HEAD.match(l)]
a_heads = set(l for l in after.split("\\n") if HEAD.match(l))
missing_heads = [h for h in b_heads if h not in a_heads]
d_before, d_after = dup_pairs(before), dup_pairs(after)

if not (P["min_chars"] <= len(after) <= P["budget"]):
    fails.append("length %d outside [%d, %d]" % (len(after), P["min_chars"], P["budget"]))
if not after.lstrip().startswith("---"):
    fails.append("frontmatter lost")
if not re.search(r"^#\\s+\\S", after, re.M):
    fails.append("H1 title lost")
if missing_heads:
    fails.append("%d cluster heading(s) dropped: %s" % (len(missing_heads), missing_heads[:2]))
if lost:
    fails.append("Lab receipts lost outside the retire list: %s" % lost)
if d_after > d_before:
    fails.append("near-duplicate pairs rose %d -> %d" % (d_before, d_after))

# Accretion is not a failure, but it is never invisible: an add-only merge is stamped into the
# verdict from the TEXT (not from the caller's claim about it) so it cannot pass as curation.
n_before, n_after = len(bullets(before)), len(bullets(after))
add_only = n_after >= n_before

print("MEASURED: canon %d -> %d chars (budget %d, %d%% used); bullets %d -> %d; "
      "near-duplicate pairs %d -> %d at containment>=%.2f; Lab receipts %d -> %d, retired %s, "
      "lost-outside-retire %d"
      % (len(before), len(after), P["budget"], round(100 * len(after) / P["budget"]),
         n_before, n_after, d_before, d_after, P["threshold"],
         len(b_ids), len(a_ids), P["retired"] or "none", len(lost)))
print("VERDICT: %s" % ("FAIL -- " + "; ".join(fails) if fails else
                       ("PASS (ADD-ONLY: %d -> %d bullets, nothing retired -- the caller must "
                        "justify the accretion)" % (n_before, n_after)) if add_only else
                       ("PASS (REMOVAL: %d -> %d bullets) -- budget, structure and every receipt hold"
                        % (n_before, n_after))))
sys.exit(0)
'''


def _gate_code(before: str, after, retired: list, n_reject: int, n_judgment: int,
               n_artifacts: int) -> str:
    """The runnable gate. The docstring stays FIRST -- lab.models_line() only reads a LEADING
    block, and an undocumented lab number is attributable only by its quest title."""
    payload = json.dumps({"before": before, "after": after, "retired": sorted(retired),
                          "budget": CANON_BUDGET, "min_chars": CANON_MIN, "threshold": NOVELTY,
                          "metric_path": str(_FD_PATH), "n_reject": n_reject,
                          "n_judgment": n_judgment, "n_artifacts": n_artifacts,
                          "head_pattern": _HEAD.pattern, "lab_pattern": _LAB_ID.pattern},
                         ensure_ascii=True)
    return (_SCRIPT_DOC + "import json\nPAYLOAD_JSON = "
            + json.dumps(payload, ensure_ascii=True) + "\n" + _SCRIPT)


# ---------------------------------------------------------------------------------------------
# Arm 1 -- the canon (primary)
# ---------------------------------------------------------------------------------------------
async def _canon_arm(ctx) -> dict:
    data = await _aw(ctx.brain_get("/brain/canon-inputs"))
    if not isinstance(data, dict):
        return _result("idle", "canon-inputs unavailable")
    canon = str(data.get("canon") or "")
    artifacts = data.get("new_artifacts") or []
    if len(canon) < CANON_MIN:
        # Creating the canon from nothing is an authoring act, not a curation act.
        return _result("idle", "no canon to curate (%d chars) -- authoring it is Claude's job" % len(canon))

    labs = (await _aw(ctx.brain_get("/brain/lab")) or {})
    labs = labs.get("experiments") if isinstance(labs, dict) else None
    plan = _plan(canon, artifacts, labs or [])
    _log(ctx, "canon %d chars, %d bullets, drop=%d admit=%d reject=%d judgment=%d"
         % (plan["chars"], len(plan["bullets"]), len(plan["drop"]), len(plan["admit"]),
            len(plan["reject"]), len(plan["judgment"])))

    if plan["drop"] or plan["admit"]:
        return await _merge(ctx, canon, plan, len(artifacts))
    if plan["reject"] or plan["judgment"]:
        return await _ruling(ctx, canon, plan, len(artifacts))
    return _result("idle", "canon is coherent at %d/%d chars and nothing new landed -- a curation "
                           "pass with nothing to curate is filler" % (plan["chars"], CANON_BUDGET))


async def _merge(ctx, canon: str, plan: dict, n_artifacts: int) -> dict:
    """Build the candidate canon, hand it to the Lab gate, write only on PASS."""
    admits = []
    for a in plan["admit"]:
        at = _place(plan, a)
        if at is None:
            continue
        # `kind` decides how the receipt is RENDERED -- a Lab id becomes "Lab `4ae810`", a citation
        # is printed as written. It was carried in the plan record and never passed, so this raised
        # TypeError on every cycle that had anything to admit. Measured 2026-07-31 against the live
        # canon: plan drop=0 admit=1 reject=7, and the organ returned status=error instead of a
        # merge. Sage Mira's curation arm could only ever complete when it had nothing to do.
        admits.append({"at": at,
                       "lines": _admit_lines(a["title"], a["core"], a["receipt"], a.get("kind", ""))})
    drops = [d["block"] for d in plan["drop"]]
    if not drops and not admits:
        return _result("idle", "nothing placeable this cycle")
    after = _render(plan["lines"], drops, admits)
    retired = sorted({r for b in drops for r in _receipts(b["text"])})   # `drops` are blocks already

    add_only = not drops
    if add_only and len(after) > CANON_BUDGET:
        # THE BUDGET BINDING IS A CURATION DECISION, NOT AN ABSENCE OF ONE. This returned `idle`, so a
        # canon at capacity with GROUNDED evidence queued behind it looked exactly like a canon with
        # nothing to curate -- and the evidence went nowhere. Measured 2026-08-01: 13 of the 14 waiting
        # artifacts carried a receipt and the canon stood at 6,955 of 7,000 chars, so admitting them
        # would have reached 7,679.
        #
        # The robot still must not restructure: CLAUDE.md keeps re-clustering the canon with Claude,
        # and evicting a standing belief to make room is exactly that. So this does not force a merge.
        # It records the bind as a JUDGMENT and falls through to the ruling path, which runs the
        # accretion audit and issues a grounded, decisive ruling naming what could not enter and why.
        # A refusal that reaches a human is work; a refusal that returns idle is a leak.
        plan["judgment"].append(
            "canon is at capacity: %d chars, and %d grounded artifact(s) are waiting. An add-only "
            "merge reaches %d, over the %d budget, so admitting them requires RETIRING a standing "
            "belief -- a written merge, not a 6-hourly robot's call. Names: %s"
            % (plan["chars"], len(admits), len(after), CANON_BUDGET,
               "; ".join(a["title"][:60] for a in plan["admit"][:3]) or "-"))
        return await _ruling(ctx, canon, plan, n_artifacts)

    rec = await _aw(ctx.lab_run("canon-curation-gate", _gate_code(
        canon, after, retired, len(plan["reject"]), len(plan["judgment"]), n_artifacts)))
    lab_id, out = _lab_fields(rec)
    verdict = next((l.strip() for l in out.split("\n") if l.strip().startswith("VERDICT:")), "")
    measured = next((l.strip() for l in out.split("\n") if l.strip().startswith("MEASURED:")), "")
    if not verdict.startswith("VERDICT: PASS"):
        return _result("idle", "lab %s refused the merge: %s" % (lab_id or "?", verdict or "no verdict "
                       "-- gate did not run, canon unchanged"))

    written = await _aw(ctx.brain_post("/brain/canon-write", {"content": after}, 60))
    if not isinstance(written, dict) or written.get("status") != "written":
        return _result("error", "canon-write refused: %s" % (written or {}))

    dropped_heads = [_head(d["block"]["text"]) for d in plan["drop"]]
    body = ["## What changed in the canon",
            "Retired %d belief(s), admitted %d, canon %d -> %d chars (%d%% of the %d budget)."
            % (len(drops), len(admits), len(canon), len(after),
               round(100 * len(after) / CANON_BUDGET), CANON_BUDGET)]
    for d in plan["drop"]:
        body.append("- RETIRED %s\n  because it %s; retained: %s"
                    % (_head(d["block"]["text"]), d["why"], d["keep"]))
    for a in plan["admit"]:
        body.append("- ADMITTED %s (receipt: Lab `%s`)" % (a["title"][:90], a["receipt"]))
    for j in plan["judgment"]:
        body.append("- ESCALATED to a written merge: %s" % j)
    if plan["reject"]:
        body.append("- HELD OUT for lack of a receipt (%d): %s"
                    % (len(plan["reject"]), "; ".join(r["title"][:70] for r in plan["reject"])))
    if plan["defer"]:
        body.append("- DEFERRED to the next cycle, admit budget is %d (%d): %s"
                    % (MAX_ADMITS, len(plan["defer"]), "; ".join(t[:70] for t in plan["defer"])))
    body += ["", "## Grounding", measured or "(no MEASURED line returned)", verdict,
             "Lab `%s` re-derived budget, structure, receipt conservation and the duplicate count "
             "from the before/after text in a separate process. The write happened because that "
             "gate passed, not because this organ judged its own work." % (lab_id or "?"),
             "", "## Falsifier",
             "This merge is wrong if any retired belief is still load-bearing: check that '%s' "
             "appears nowhere as a live premise, and that Lab receipt(s) %s are cited by the "
             "retained belief. If either fails, revert from git -- the canon's history is the "
             "audit trail." % ("; ".join(dropped_heads) or "n/a", ", ".join(retired) or "none")]
    verb = "add-only merge" if add_only else "removal merge"
    why = ("merged: %s -- %d retired, %d admitted, %d -> %d chars, gated by lab %s"
           % (verb, len(drops), len(admits), len(canon), len(after), lab_id or "?"))
    if add_only:
        # The hard rule: an accreting merge must justify itself out loud.
        why += (" | ADD-ONLY, justified: every admitted claim carries a Lab receipt, none restates "
                "a standing belief at containment>=%.2f, and the canon stays under budget" % NOVELTY)
    return _result("ok", why, decisive=True, lab_id=lab_id,
                   title="Canon merge -- %d retired, %d admitted" % (len(drops), len(admits)),
                   content="\n".join(body))


async def _ruling(ctx, canon: str, plan: dict, n_artifacts: int) -> dict:
    """No belief moves, but a curation DECISION was made: these claims do not enter the canon."""
    claim = "canon ruling " + " ".join(r["title"] for r in plan["reject"][:6]) + " ".join(plan["judgment"])
    # One ungrounded artifact is not news. One ESCALATION is: it names a specific defect in the
    # canon that only a written merge can fix, and swallowing it is how a real finding goes dark.
    if len(plan["reject"]) < 2 and not plan["judgment"]:
        return _result("idle", "only %d pending item and nothing to retire -- not worth a ruling"
                       % len(plan["reject"]))
    heads = [r["title"][:80] for r in plan["reject"][:2]] or [(plan["judgment"] or [""])[0][:80]]
    if await _already_ruled(ctx, ["canon ruling receipts"] + heads, claim):
        return _result("idle", "this ruling was already issued -- repeating it every 6h is churn")

    rec = await _aw(ctx.lab_run("canon-accretion-audit", _gate_code(
        canon, None, [], len(plan["reject"]), len(plan["judgment"]), n_artifacts)))
    lab_id, out = _lab_fields(rec)
    measured = next((l.strip() for l in out.split("\n") if l.strip().startswith("MEASURED:")), "")
    verdict = next((l.strip() for l in out.split("\n") if l.strip().startswith("VERDICT:")), "")
    if not measured or not verdict:
        return _result("idle", "audit lab %s returned no MEASURED/VERDICT -- an ungrounded ruling is "
                               "exactly the filler this organ exists to refuse" % (lab_id or "?"))

    body = ["## The ruling",
            "%d artifact(s) landed since the canon's last merge. Nothing below enters the statement "
            "of belief this cycle, and the canon was not touched." % n_artifacts, ""]
    for r in plan["reject"]:
        body.append("- HELD OUT: %s\n  %s" % (r["title"][:110], r["why"]))
    for j in plan["judgment"]:
        body.append("- NEEDS A WRITTEN MERGE: %s" % j)
    body += ["", "## Why this is the right answer, not a stalled one",
             "The canon is at %d%% of its %d-char budget with %d near-duplicate pairs -- it is not "
             "bloated, it is FULL. Admitting an ungrounded claim would cost a grounded one its "
             "place. A claim earns a line in the canon by carrying a Lab id, a citation, or a "
             "MEASURED/VERDICT pair; prose does not."
             % (round(100 * plan["chars"] / CANON_BUDGET), CANON_BUDGET, plan["dup_pairs"]),
             "", "## Grounding", measured, verdict,
             "Lab `%s` measured the canon and the pending queue in a separate process." % (lab_id or "?"),
             "", "## Falsifier",
             "This ruling is wrong if any held-out artifact does carry a receipt in its own note "
             "that /brain/canon-inputs did not surface (it only extracts the 'The insight' / "
             "'Hypothesis' / 'Answer' section -- see execution/canon.py:77). Open the note; if a "
             "Lab id is there, the merge is owed and this ruling should be overturned."]
    return _result("ok",
                   "rejected: %d artifact(s) held out for lack of a receipt, %d escalated for a "
                   "written merge; canon untouched at %d/%d chars, grounded by lab %s"
                   % (len(plan["reject"]), len(plan["judgment"]), plan["chars"], CANON_BUDGET,
                      lab_id or "?"),
                   decisive=True, lab_id=lab_id,
                   title=("Canon ruling -- %d claim(s) held out for lack of a receipt"
                          % len(plan["reject"]) if plan["reject"] else
                          "Canon ruling -- %d belief(s) need a written merge" % len(plan["judgment"])),
                   content="\n".join(body))


# ---------------------------------------------------------------------------------------------
# Arm 2 -- the press (secondary, and OWNER-GATED: this arm can only ever PROPOSE)
# ---------------------------------------------------------------------------------------------
async def _press_arm(ctx) -> dict:
    data = await _aw(ctx.brain_get("/brain/press-target"))
    data = data if isinstance(data, dict) else {}
    # WALK THE LIST. This arm applies four gates after receiving a candidate -- score floor, readable
    # source, Lab grounding, stated falsifier -- and used to terminate on the first refusal, against
    # an endpoint that offered exactly one candidate. Measured 2026-08-01: it returned idle with
    # "source note for 'Bridge AI Competitive Moat x Biostatistics...' has no falsifier" while other
    # eligible notes sat unoffered in the same directory. Four ways to reject, one thing to reject.
    # Same defect as `belief-challenge-target` (42 days wedged) and `replication.pick_target`.
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        one = data.get("target")
        targets = [one] if isinstance(one, dict) else []
    targets = [t for t in targets if isinstance(t, dict) and t.get("title")]
    if not targets:
        return _result("idle", "no press target")

    title, note, target = "", "", None
    stepped = []
    for cand in targets:
        t = str(cand.get("title") or "").strip()
        if _as_int(cand.get("score")) < PRESS_MIN_SCORE:
            stepped.append("scores %s" % cand.get("score"))
            continue
        try:
            p = Path(str(cand.get("path") or ""))
            text = p.read_text(encoding="utf-8", errors="replace")[:20000] if p.is_file() else ""
        except Exception:
            text = ""
        if not text:
            stepped.append("unreadable")
            continue
        if _grounding(text)[0] is None:
            stepped.append("no Lab id / MEASURED")
            continue
        if not _has_falsifier(text):
            stepped.append("no falsifier")
            continue
        title, note, target = t, text, cand
        break

    if target is None:
        # Say what was walked and why. A wedge and an empty vault used to look identical from here.
        return _result("idle", "walked %d press candidate(s), none publishable: %s"
                       % (len(targets), ", ".join(sorted(set(stepped))) or "none eligible"))
    if stepped:
        _log(ctx, "stepped past %d press candidate(s): %s"
             % (len(stepped), ", ".join(sorted(set(stepped)))))
    kind, detail = _grounding(note)
    # MATCH THE CONCEPT, NOT ONE SPELLING. This was a literal substring test for "falsifier" while
    # the Theory Engine writes "falsification control: ..." -- and "falsifier" is not a substring of
    # "falsification", so a note that DID state its falsifier was refused for not stating one.
    # Measured 2026-07-31: 40 of the last 40 discoveries carried a Lab id and 1 was seen to carry a
    # falsifier, which read as a swarm-wide contract gap; part of it was this detector.
    # `grounding.has_falsifier` is the shared definition and still demands a NAMED TEST -- a bare
    # "falsifiable" is a claim about the claim, and the press bar exists to refuse exactly that.
    if not _has_falsifier(note):
        return _result("idle", "source note for '%s' has no falsifier -- the press template requires "
                               "the test that would kill the claim" % title[:60])
    if await _already_ruled(ctx, ["press draft " + title[:60], title[:80]], title):
        return _result("idle", "already drafted press for '%s'" % title[:60])

    compose = getattr(ctx, "llm", None)
    if not callable(compose):
        # Assembling a post out of note fragments and Telegramming it to the owner 4x a day is
        # exactly the stream of small notes he told us to stop. No composer, no draft.
        return _result("idle", "press target '%s' is ready but no composer is available -- refusing "
                               "to send the owner a mechanically assembled draft" % title[:60])
    try:
        body = await _aw(compose(
            "You are Sage Mira, writing ONE public post for a research organization whose "
            "credibility is its moat. Use ONLY the source note below. Every number you write must "
            "appear verbatim in the source. State the claim, the measured result, and the falsifier. "
            "No hype, no filler, English only. 400-900 words, markdown, no title heading.",
            "SOURCE NOTE (%s):\n%s" % (title, note)))
    except Exception as e:
        return _result("error", "composer failed: %s: %s" % (type(e).__name__, e))
    body = (body or "").strip() if isinstance(body, str) else ""
    if len(body) < 300 or len(title) < 10:
        return _result("idle", "composed draft too short (title %d, body %d) -- /brain/press/draft "
                               "requires title>=10 and body>=300" % (len(title), len(body)))

    # Every number in an outward-facing draft must exist in the source note. A number that is not
    # in the note was invented by the composer, and we have shipped an unverified number publicly
    # before -- never again without this check.
    invented = sorted({n for n in _NUM.findall(body) if n not in note})
    if invented:
        return _result("idle", "refusing to propose: %d number(s) in the draft are not in the source "
                               "note (%s)" % (len(invented), ", ".join(invented[:5])))

    resp = await _aw(ctx.brain_post("/brain/press/draft",
                                    {"title": title[:160], "body": body,
                                     "source": str(target.get("path") or "")[:160]}, 90))
    status = (resp or {}).get("status") if isinstance(resp, dict) else None
    if status != "proposed":
        return _result("idle", "press/draft did not propose (status=%s)" % status)
    act = (resp.get("action") or {}).get("id") if isinstance(resp.get("action"), dict) else None
    # NOT decisive. `published` means the owner approved from Telegram; Mira cannot decide it, and
    # an organ that scored itself for drafting would learn to spam the gate.
    return _result("ok",
                   "proposed press action %s for owner approval -- NOT decisive: only the owner "
                   "turns a proposal into 'published'. Grounded by %s %s." % (act or "?", kind, detail),
                   decisive=False, title="Press proposal (gated) -- %s" % title[:90],
                   content=body[:4000], lab_id=(detail if kind == "lab" else None))


# ---------------------------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------------------------
async def cycle(ctx) -> dict:
    """Returns {"status": "ok"|"idle"|"error", "decisive": bool, "title": str,
                "content": str, "lab_id": str|None, "why": str}

    Canon first (Mira's primary organ), press second. Never raises: asyncio.CancelledError is a
    BaseException and is deliberately allowed through so the dispatcher can still shut down.
    """
    t0 = time.time()
    try:
        if _TOKENS is None or _CONTAINMENT is None:
            return _result("error", "repo containment metric unavailable at %s -- refusing to run "
                                    "with a private copy that would drift from the calibrated "
                                    "threshold" % _FD_PATH)
        canon = await _canon_arm(ctx)
        if canon["status"] != "idle":
            _log(ctx, "canon arm: %s (%.1fs)" % (canon["status"], time.time() - t0))
            return canon
        press = await _press_arm(ctx)
        if press["status"] != "idle":
            _log(ctx, "press arm: %s (%.1fs)" % (press["status"], time.time() - t0))
            return press
        return _result("idle", "canon: %s | press: %s" % (canon["why"], press["why"]))
    except Exception as e:
        try:
            _log(ctx, "cycle failed: %s: %s" % (type(e).__name__, e))
        except Exception:
            pass
        return _result("error", "%s: %s" % (type(e).__name__, str(e)[:300]))
