"""
Sergeant Voss -- Quality Assurance: the organ that attacks Agora's OWN beliefs.

WHY THIS FILE EXISTS (measured, 2026-07-29..31)
----------------------------------------------
All eight dungeon agents ran the same code and the swarm produced 19 discoveries in five days;
Voss produced 3 of them. His organ was not missing -- it was already built on the brain side
(`/brain/belief-challenge-target`, `/brain/belief-revise`, `/brain/bounty`, and the graveyard
behind them) and the dungeon simply never routed him to it. The bounty ledger holds 31 resolved
challenges and 11 kills, which is real work, but it arrives from `Claude (severe-test)` and from
ad-hoc loop cycles rather than from Voss's own metabolism. This file is the route.

OWNERSHIP OF THE BOUNTY LEDGER.
`server/agora/execution/repair_ledger.py:65` records an unresolved ownership question: CLAUDE.md
assigns belief challenges to Sergeant Voss, while the roadmap panel labels Bounty/Court as King
Aldric's instrument, and it declines to guess -- it says the store's own `by` field decides per
record. CLAUDE.md is the authority here, so this organ follows it: **Voss owns the bounty ledger**,
and every record it writes carries `challenger = "Sergeant Voss"` so the `by` field says so
explicitly. The name is hard-coded rather than taken from `ctx.agent` on purpose: the existing 31
records are keyed on the string "Sergeant Voss", and writing an eid ("guard_l") instead would fork
his standing into two identities and reset the kill-authority score the metabolism reads.

THE ANTI-CHURN CONTRACT (why `survived` is not a consolation prize)
-------------------------------------------------------------------
`server/agora/execution/metabolism.py:108` pays 3.0 for a kill and 0.75 for a survival -- a 4x
gradient pointing straight at manufactured kills. This organ therefore refuses to rule at all
unless the verdict is grounded, and it is built so that a kill is HARDER to reach than a survival:

  * SURVIVED is ruled on the WIDEST null (rho=0.0, independent samples). If the belief's effect
    clears that band it clears every narrower one, so a survival is airtight.
  * KILL is ruled on the TIGHTEST null we are willing to grant the belief (rho=0.8, a strongly
    paired design). Only an effect inside even that band is dead under any reasonable reading of
    the design the note describes.
  * Between the two the verdict depends on a design detail the note does not state, and the organ
    returns `status="idle"` rather than pick the side that pays more.

Voss's specific failure mode is a challenge that was never capable of killing anything. Every
verdict this organ emits therefore carries the KILLING CONDITION as a NUMBER (`kill_band_95`, the
95th percentile of |delta| under the null itself), not as prose -- so "what would have killed it"
is checkable rather than asserted. A channel that cannot produce that number does not rule; it
abstains, and the cycle returns `idle`.

WHAT IT ACTUALLY DOES
---------------------
1. GET /brain/belief-challenge-target and WALK `targets`. That endpoint returns both a `targets`
   list and a head `target`, and its own docstring records why: two relevance filters are in play
   (belief_revision's loose board-token overlap vs the dungeon's hard `_inbox_theme_allowed` gate)
   and when they disagree, a caller that takes only the head re-proposes and re-refuses the same
   belief forever. Measured on the live brain 2026-07-31: of the 8 returned targets, 6 are refused
   by the board gate, and the head is the June A/B-testing note the endpoint docstring names as the
   blocker. A head-only caller does nothing, forever. This one walks.
2. Board gate, so Voss challenges beliefs on the owner's niche (see `_board_allows`).
3. Novelty gate via `_containment >= 0.6` from `server/agora/execution/finding_diversity.py:27`
   (loaded from that file, never reimplemented -- the threshold is calibrated repo-wide).
4. Attacks the first candidate that offers a channel capable of a verdict:
     A. ARTIFACT -- the belief names a runnable receipt (`lab_file:` / `lab_id:`). A named artifact
        that is not on disk is a kill. Guarded by a positive control on the lab directory and by a
        ledger-coverage check, both load-bearing: the lab ledger is capped at 1000 records and on
        2026-07-31 spanned only 2026-07-17..07-31, while the beliefs in the walk are dated
        2026-06-21. Looking up a June `lab_id` there returns "absent" for every one of them -- a
        naive receipt check would have manufactured a kill out of log rotation. The lab SCRIPTS are
        not rotated (9770 files on disk, 5017 of them from June), so the disk check is sound where
        the ledger check is not.
     B. NULL FLOOR -- the severe test, run through ctx.lab_run (see `_lab_code`).
     C. CITATION -- checks an arXiv id / DOI against the bibliographic record, but ONLY after a
        negative control proves the resolver can return "not found". Measured 2026-07-31: it
        cannot. `/brain/research?q=arXiv:9912.88888` (a syntactically valid, nonexistent id)
        returns 2 unrelated papers, and querying a REAL id returns two different unrelated papers.
        It is a semantic search, not a resolver, so "found" is meaningless and "not found" never
        happens. The channel is written and self-certifying: it runs the control every time, reports
        NOT_CAPABLE today, and starts ruling the day a real resolver lands. Shipping it without the
        control would have been the exact ceremony this organ exists to refuse.
5. Records the outcome via POST /brain/belief-revise, which routes to the bounty ledger and (on a
   kill) to the graveyard.

Every Lab script this organ submits OPENS with a docstring stating what it models --
`server/agora/execution/lab.py:41-72` reads exactly that leading block and records the run
`undocumented` otherwise. Measured over the last 60 runs: 100% carried no model description, so
every number in that ledger is attributable only through its quest title.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

ORGAN = {
    "eid": "guard_l", "agent": "Sergeant Voss", "name": "Quality Assurance",
    "ledger": ".bounty.json",
    "decisive": ("kill", "survived"),
    "period_hours": 6.0,                      # ~4x/day
}

# Repo root: organs/ -> agora-game-server/ -> repo.
_ROOT = Path(__file__).resolve().parents[2]
_FINDING_DIVERSITY = _ROOT / "server" / "agora" / "execution" / "finding_diversity.py"
_MCP_SERVER = _ROOT / "agora-game-server" / "mcp_server.py"

_API = "/api/v1/agent-os"

_TRIALS = 20000
_SEED = 20260731
_RHOS = (0.0, 0.5, 0.8)
_RHO_SURVIVE = 0.0        # widest null: clearing it clears every narrower one
_RHO_KILL = 0.8           # tightest null we grant the belief
_ALPHA = 0.05
_ALPHA_MARGIN = 0.005     # Monte-Carlo SE at _TRIALS is ~0.0015; refuse to rule inside ~3 SE
_NOVELTY = 0.6            # finding_diversity's calibrated containment threshold
_MIN_PRIOR_TOKENS = 4     # a 2-token memory would veto everything at containment 1.0


# ---------------------------------------------------------------------------
# Shared code, loaded rather than copied
# ---------------------------------------------------------------------------

_fd_mod = None


def _diversity():
    """`finding_diversity` loaded from its own file.

    Loaded by path rather than imported as `agora.execution.finding_diversity` for the same reason
    the dungeon loads the real TrustEngine that way (mcp_server.py:1288): the dungeon is a separate
    process with a separate sys.path, and a library module has no business mutating it. The target
    module is stdlib-only (`re`, `collections`), so executing it standalone is safe.
    """
    global _fd_mod
    if _fd_mod is None:
        spec = importlib.util.spec_from_file_location(
            "agora_finding_diversity_voss", str(_FINDING_DIVERSITY))
        if spec is None or spec.loader is None:
            raise ImportError("finding_diversity not loadable at %s" % _FINDING_DIVERSITY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for required in ("_containment", "_tokens"):
            if not callable(getattr(mod, required, None)):
                raise ImportError("finding_diversity is missing %s" % required)
        _fd_mod = mod
    return _fd_mod


_board_vocab: dict | None = None


def _board_vocabulary() -> dict:
    """The dungeon's board vocabulary, read out of mcp_server.py WITHOUT executing it.

    `_inbox_theme_allowed` (mcp_server.py:1442) is the one choke point for off-mission work, and its
    discriminating power is entirely in two set literals: `_BOARD_CORE` (the subject must be ours)
    and `_BOARD_BANNED` (refused beats matched). Calling the live function is not an option here --
    mcp_server.py is the process entrypoint, so it is `__main__` and importing it by name would start
    a second server; and when its `_gate_cache` is cold that function lets EVERYTHING through, which
    is indistinguishable from "passed the gate" at the call site. Parsing the two literals with `ast`
    gives one source of truth, no execution, and the same answer in-process and in a harness.

    Both sets must parse and both must be non-empty. A gate that silently resolves to the empty set
    is a gate that reports safe on everything, so failure is surfaced (see `_board_allows`), never
    swallowed.
    """
    global _board_vocab
    if _board_vocab is None:
        core: set = set()
        banned: set = set()
        try:
            tree = ast.parse(_MCP_SERVER.read_text(encoding="utf-8", errors="replace"))
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                names = {t.id for t in node.targets if isinstance(t, ast.Name)}
                if "_BOARD_CORE" in names:
                    core = set(ast.literal_eval(node.value))
                elif "_BOARD_BANNED" in names:
                    banned = set(ast.literal_eval(node.value))
        except Exception:
            core, banned = set(), set()
        _board_vocab = {"core": core, "banned": banned, "ok": bool(core and banned)}
    return _board_vocab


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

async def _maybe(value):
    """Await `value` if it is awaitable.

    The dispatcher owns `ctx` and is written separately; tolerating both a sync and an async
    `brain_get`/`brain_post`/`lab_run`/`recall` costs three lines and removes a whole class of
    integration break that would otherwise surface as `status="error"` on every cycle.
    """
    return await value if inspect.isawaitable(value) else value


def _ascii(text) -> str:
    """ASCII-fold for log lines -- the Windows console is cp1250 and a stray glyph 500s the caller."""
    s = "" if text is None else str(text)
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "replace").decode("ascii")


def _words(text: str) -> set:
    """Board-match tokens: whole words plus the pieces of hyphenated ones.

    `_BOARD_CORE` holds both short entries ("rag", "zep", "mem0") and hyphenated ones
    ("agent-memory"), so neither a length filter nor a plain `[a-z]+` split would see all of them.
    """
    low = (text or "").lower()
    out = set(re.findall(r"[a-z0-9][a-z0-9\-]*", low))
    for w in list(out):
        out.update(p for p in w.split("-") if p)
    return out


def _board_allows(title: str) -> tuple:
    """Board-priority gate. Returns (allowed, reason)."""
    vocab = _board_vocabulary()
    if not vocab["ok"]:
        # Repo convention (belief_revision._board_tokens, _inbox_theme_allowed): a board that fails
        # to load must not silence belief revision, only stop steering it. Flagged, never silent.
        return True, "board vocabulary unreadable -- gate did NOT run"
    w = _words(title)
    hit_banned = sorted(w & vocab["banned"])
    if hit_banned:
        return False, "deprioritised subject %s" % (hit_banned[:3],)
    hit_core = sorted(w & vocab["core"])
    if hit_core:
        return True, "on-board (%s)" % ", ".join(hit_core[:3])
    return False, "names no subject of ours"


def _texts_of(blob) -> list:
    """Flatten whatever `ctx.recall` returns into plain strings (shape is dispatcher-defined)."""
    out: list = []
    if blob is None:
        return out
    if isinstance(blob, str):
        return [blob]
    if isinstance(blob, dict):
        for key in ("results", "memories", "items", "recalled", "hits"):
            if isinstance(blob.get(key), list):
                return _texts_of(blob[key])
        for key in ("content", "text", "title", "memory"):
            if isinstance(blob.get(key), str):
                out.append(blob[key])
        return out
    if isinstance(blob, (list, tuple)):
        for item in blob:
            out.extend(_texts_of(item))
    return out


# ---------------------------------------------------------------------------
# Reading the belief note
# ---------------------------------------------------------------------------

def _frontmatter(text: str, key: str) -> str:
    m = re.search(r"^%s:\s*(.+)$" % re.escape(key), text[:2000], re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


_N_EQUALS = re.compile(r"\bn\s*=\s*(\d{1,6})\b", re.I)
_N_UNITS = ("questions", "items", "samples", "trials", "runs", "pairs", "queries", "cases",
            "examples", "claims", "notes", "papers", "documents", "episodes", "tasks")
_N_PHRASE = re.compile(
    r"\b(\d{2,6})\s+(?:[A-Za-z0-9\-()/.]+\s+){0,3}(?:%s)\b" % "|".join(_N_UNITS), re.I)


def _sample_sizes(text: str) -> set:
    """Every sample size the note states. Ambiguity is reported, never resolved by guessing.

    A number attributed to the wrong subject is worse than no number (lab.py:41-72 documents the
    case that motivated this), so a note carrying two different n values gets no null test -- there
    is no honest way to know which one the headline comparison was measured on.
    """
    found = {int(m) for m in _N_EQUALS.findall(text)}
    found |= {int(m) for m in _N_PHRASE.findall(text)}
    return {n for n in found if n >= 10}


# A cell counts as a rate only if its column header says so AND says nothing that means "not a rate".
# Exclusions are checked first and win: the live note
# `insight-grounding-firewall-is-adaptively-defeated-conditional-moat` has a column headed
# `corr(-drop, correct)` whose values (+0.52) sit in [0,1] and whose header contains "correct".
# Reading a correlation as an accuracy and handing it to a binomial null is a category error that
# would have produced a confident, wrong verdict on a real belief.
_RATE_WORDS = ("acc", "accuracy", "recall", "precision", "rate", "hit", "f1", "success",
               "correct", "coverage", "pass")
_NOT_RATE_WORDS = ("auc", "corr", "rho", "delta", "lift", "edge", "gain", "diff", "p-value",
                   "pval", "stderr", " se ", "std", "ratio", "count", "n=", "seconds", "cost")
_UNSIGNED_RATE = re.compile(r"^(?:\*\*)?(0?\.\d{1,4}|0|1|1\.0+)(?:\*\*)?$")


def _is_rate_header(cell: str) -> bool:
    c = " " + cell.strip().lower().strip("*`") + " "
    if any(bad in c for bad in _NOT_RATE_WORDS):
        return False
    return any(good in c for good in _RATE_WORDS)


def _split_row(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _rate_pair(text: str) -> dict | None:
    """The note's headline rate comparison, taken from a markdown table.

    Requires a header row with >= 2 columns that name a rate, a data row directly under the
    separator, and UNSIGNED decimals in [0,1] in those columns. Signed cells (+0.52, -0.10) are
    deltas or correlations, not rates, and the pattern rejects them.
    """
    lines = text.splitlines()
    for i in range(len(lines) - 2):
        if not lines[i].strip().startswith("|"):
            continue
        if not re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            continue
        header = _split_row(lines[i])
        rate_cols = [j for j, h in enumerate(header) if _is_rate_header(h)]
        if len(rate_cols) < 2:
            continue
        for row_line in lines[i + 2:]:
            if not row_line.strip().startswith("|"):
                break
            cells = _split_row(row_line)
            vals = []
            for j in rate_cols:
                if j < len(cells):
                    m = _UNSIGNED_RATE.match(cells[j])
                    if m:
                        vals.append((j, float(m.group(1))))
            if len(vals) >= 2 and abs(vals[0][1] - vals[-1][1]) >= 0.005:
                a, b = vals[0], vals[-1]
                return {"a": a[1], "b": b[1],
                        "col_a": header[a[0]].strip("*` ") or "col%d" % a[0],
                        "col_b": header[b[0]].strip("*` ") or "col%d" % b[0],
                        "row": cells[0].strip("*` ")[:60] or "row 1"}
    return None


_ARXIV = re.compile(r"arxiv[:/]\s*(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
_DOI = re.compile(r"\b(10\.\d{4,9}/[-._;()/:a-z0-9]+)", re.I)


def _identifiers(text: str) -> list:
    ids = ["arXiv:%s" % m for m in _ARXIV.findall(text)]
    ids += ["doi:%s" % m.rstrip(".,);") for m in _DOI.findall(text)]
    return ids[:3]


# ---------------------------------------------------------------------------
# The Lab script
# ---------------------------------------------------------------------------

_LAB_BODY = '''
import random

# The null: both conditions are the SAME Bernoulli process at the pooled rate P_BAR, measured on the
# SAME N items. RHO is the fraction of items the two conditions agree on by construction (a paired
# design); those items cancel out of the difference, so only the (1 - RHO) share carries variance.
# RHO = 0.0 is the widest band (independent samples) and RHO = 0.8 the tightest we grant the belief,
# so the two ends bracket the design the note does not state.
P_BAR = (P_A + P_B) / 2.0
OBS = abs(P_A - P_B)


def one_trial(rng, rho):
    shared = 0
    for _ in range(N):
        if rng.random() < rho:
            shared += 1
    free = N - shared
    a = sum(1 for _ in range(free) if rng.random() < P_BAR)
    b = sum(1 for _ in range(free) if rng.random() < P_BAR)
    return abs(a - b) / float(N)


print("MEASURED: observed_delta=%.4f n=%d p_a=%.4f p_b=%.4f p_bar=%.4f trials=%d seed=%d"
      % (OBS, N, P_A, P_B, P_BAR, TRIALS, SEED))
for rho in RHOS:
    rng = random.Random(SEED)           # common random numbers across rho
    draws = sorted(one_trial(rng, rho) for _ in range(TRIALS))
    ge = sum(1 for d in draws if d >= OBS - 1e-12)
    band = draws[min(TRIALS - 1, int(0.95 * TRIALS))]
    print("MEASURED: rho=%.2f p_two_sided=%.4f kill_band_95=%.4f"
          % (rho, ge / float(TRIALS), band))
'''


def _lab_code(belief_title: str, pair: dict, n: int) -> str:
    """Assemble the experiment. The docstring comes FIRST and says what is modelled.

    lab.py:41-72 reads only a genuine leading docstring or `#` block; anything else records the run
    `undocumented`, and 100% of the last 60 runs were. Built by concatenation rather than
    `.format()` so the body can keep its own `%` formatting and braces.
    """
    desc = (
        "MODELS: the sampling null for ONE belief's headline rate comparison, as a severe test of\n"
        "that belief -- NOT a finding about the subject matter.\n"
        "Belief under attack: %s\n"
        "Claim: %s = %.4f vs %s = %.4f on n = %d items (row: %s).\n"
        "H0: both conditions are the same Bernoulli process at the pooled rate, measured on the same\n"
        "n items, agreeing by construction on a fraction RHO of them. Reports the two-sided p for the\n"
        "observed |delta| and the 95th percentile of |delta| under H0 (kill_band_95 -- the largest\n"
        "gap this null produces by chance, i.e. the gap that WOULD have killed the belief).\n"
        "Verdict rule: survived if p < 0.05 at RHO = 0.0 (widest band); killed if p >= 0.05 at\n"
        "RHO = 0.8 (tightest band); otherwise the verdict turns on a design detail the note does not\n"
        "state and no verdict is recorded."
        % (belief_title.replace('"""', "'''")[:180], pair["col_a"], pair["a"],
           pair["col_b"], pair["b"], n, pair["row"])
    )
    params = ("N = %d\nP_A = %.6f\nP_B = %.6f\nRHOS = %r\nTRIALS = %d\nSEED = %d\n"
              % (n, pair["a"], pair["b"], list(_RHOS), _TRIALS, _SEED))
    return '"""\n' + desc + '\n"""\n' + params + _LAB_BODY


_P_LINE = re.compile(r"rho=([\d.]+)\s+p_two_sided=([\d.]+)\s+kill_band_95=([\d.]+)")


def _parse_lab(output: str) -> dict:
    return {float(r): {"p": float(p), "band": float(b)}
            for r, p, b in _P_LINE.findall(output or "")}


# ---------------------------------------------------------------------------
# The channels
# ---------------------------------------------------------------------------

def _lab_dir(experiments: list):
    """Where the Lab actually writes, taken from the ledger's own absolute `script` paths.

    Asking the ledger beats deriving it from __file__: this organ may run from a git worktree whose
    `agora_output/` is not the one the brain writes to, and pointing the artifact check at the wrong
    directory would report every real receipt as missing.
    """
    for rec in reversed(experiments or []):
        script = rec.get("script")
        if script:
            try:
                parent = Path(script).parent
                if parent.is_dir():
                    return parent
            except Exception:
                continue
    local = _ROOT / "agora_output" / "lab"
    return local if local.is_dir() else None


def _dir_populated(path, cap: int = 50) -> int:
    """How many entries the directory holds, counted up to `cap` (the real one holds ~9800)."""
    n = 0
    try:
        for _ in path.iterdir():
            n += 1
            if n >= cap:
                break
    except Exception:
        return 0
    return n


def _channel_artifact(text: str, note_date: str, experiments: list) -> dict:
    """Does the belief's named receipt exist? Returns {verdict, evidence}; verdict may be None."""
    lab_dir = _lab_dir(experiments)
    lab_file = _frontmatter(text, "lab_file")
    lab_id = _frontmatter(text, "lab_id") or ""

    if lab_file:
        populated = _dir_populated(lab_dir) if lab_dir is not None else 0
        if not populated:
            # Positive control: with no reachable, populated lab directory, "file missing" only
            # means "I am looking in the wrong place".
            return {"verdict": None,
                    "evidence": "RECEIPT: lab_file '%s' NOT CHECKED -- no populated lab directory "
                                "is reachable from this process, so absence would prove nothing."
                                % lab_file}
        target = Path(lab_file)
        if not target.is_absolute():
            target = lab_dir.parent.parent / lab_file
        if target.is_file():
            return {"verdict": None,
                    "evidence": "RECEIPT: lab_file '%s' EXISTS on disk (%d bytes)."
                                % (lab_file, target.stat().st_size)}
        return {"verdict": "kill",
                "evidence": "MEASURED: the note names lab_file '%s'; that path is absent while the "
                            "lab directory it belongs to (%s) is present and holds at least %d "
                            "entries. The belief's number has no runnable receipt."
                            % (lab_file, lab_dir, populated)}

    if lab_id:
        ids = {r.get("id") for r in (experiments or [])}
        stamps = sorted(r.get("ts", 0) for r in (experiments or []) if r.get("ts"))
        if lab_id in ids:
            return {"verdict": None, "evidence": "RECEIPT: lab_id %s is in the Lab ledger." % lab_id}
        # Rotation guard. The ledger is capped (lab.py: `_save(items[-1000:])`) and on 2026-07-31 it
        # spanned 14 days while the challengeable beliefs were 40 days old -- every June lab_id reads
        # "absent" for that reason alone. Absence is evidence only if the ledger reaches back far
        # enough to have held the record.
        oldest = time.strftime("%Y-%m-%d", time.localtime(stamps[0])) if stamps else ""
        if oldest and note_date and oldest <= note_date:
            return {"verdict": "kill",
                    "evidence": "MEASURED: the note cites lab %s. The Lab ledger reaches back to %s, "
                                "before this belief's date (%s), so the record should be in it -- and "
                                "it is not. The cited receipt does not exist."
                                % (lab_id, oldest, note_date)}
        return {"verdict": None,
                "evidence": "RECEIPT: lab %s not in the visible ledger, but that ledger only reaches "
                            "back to %s and the belief is dated %s -- rotation, not a missing "
                            "receipt. NOT evidence."
                            % (lab_id, oldest or "an unknown date", note_date or "an unknown date")}

    return {"verdict": None, "evidence": ""}


async def _channel_citation(ctx, identifiers: list) -> dict:
    """Check a cited identifier against the bibliographic record -- IF the resolver can say "no".

    Runs a negative control first: a syntactically valid, deliberately nonexistent arXiv id. If the
    resolver returns papers for THAT, it cannot falsify anything and this channel must not rule.
    Measured 2026-07-31 against the live brain: `/brain/research?q=arXiv:9912.88888` returned 2
    papers, and a real id returned 2 different, unrelated papers -- it is a semantic search, not a
    lookup. So today this always reports NOT_CAPABLE, by measurement rather than by assumption.
    """
    if not identifiers:
        return {"verdict": None, "evidence": ""}
    control = await _maybe(ctx.brain_get(
        _API + "/brain/research?q=arXiv%3A9912.88888&n=3"))
    if not isinstance(control, dict):
        return {"verdict": None,
                "evidence": "CITATION: resolver unreachable -- no citation check attempted."}
    if control.get("papers"):
        return {"verdict": None,
                "evidence": "CITATION: %s cited, NOT CHECKED. Control: the resolver returns %d "
                            "papers for a nonexistent arXiv id, so it cannot report 'not found' and "
                            "a check against it could never have falsified anything."
                            % (", ".join(identifiers), len(control["papers"]))}
    # The control passed: the resolver CAN say no, so absence is now evidence.
    for ident in identifiers:
        found = await _maybe(ctx.brain_get(
            _API + "/brain/research?q=%s&n=3" % quote(ident)))
        if isinstance(found, dict) and not found.get("papers"):
            return {"verdict": "kill",
                    "evidence": "MEASURED: the note rests on %s. The resolver (control passed: it "
                                "returns nothing for a nonexistent id) finds no such work. The "
                                "citation does not resolve." % ident}
    return {"verdict": None,
            "evidence": "CITATION: %s resolve against the bibliographic record."
                        % ", ".join(identifiers)}


# ---------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------

def _summarise(skipped: list, limit: int = 4) -> str:
    """Collapse repeated skip reasons to "reason xN" -- 6 identical board refusals in a row is one
    fact about the walk, not six, and the raw list crowded the real reason out of `why`."""
    if not skipped:
        return "none"
    counts: dict = {}
    for reason in skipped:
        counts[reason] = counts.get(reason, 0) + 1
    parts = ["%s%s" % (r, " x%d" % c if c > 1 else "") for r, c in list(counts.items())[:limit]]
    if len(counts) > limit:
        parts.append("+%d more" % (len(counts) - limit))
    return "; ".join(parts)


def _idle(why: str, title: str = "") -> dict:
    return {"status": "idle", "decisive": False, "title": title, "content": "",
            "lab_id": None, "why": why}


def _error(why: str) -> dict:
    return {"status": "error", "decisive": False, "title": "", "content": "",
            "lab_id": None, "why": why}


async def cycle(ctx) -> dict:
    """One challenge sweep. Never raises."""
    log = getattr(ctx, "logger", None)

    def info(msg: str) -> None:
        if log is not None:
            try:
                log.info(_ascii(msg))
            except Exception:
                pass

    try:
        try:
            fd = _diversity()
        except Exception as exc:
            # The novelty threshold is calibrated repo-wide and must not be re-invented locally
            # (a second, differently-tuned dedup rule is how the challenge sweep wedged in the first
            # place). A missing dependency is an error, not a reason to run ungated.
            return _error("cannot load finding_diversity._containment (%s): %s"
                          % (_FINDING_DIVERSITY, _ascii(exc)))

        picked = await _maybe(ctx.brain_get(_API + "/brain/belief-challenge-target"))
        if not isinstance(picked, dict):
            return _idle("belief-challenge-target unreachable")
        # WALK the list. Taking only the head is what wedged this sweep.
        targets = picked.get("targets") or ([picked["target"]] if picked.get("target") else [])
        if not targets:
            return _idle("no challengeable belief on record")

        experiments = []
        lab = await _maybe(ctx.brain_get(_API + "/brain/lab"))
        if isinstance(lab, dict):
            experiments = lab.get("experiments") or []

        # What Voss has already attacked: his own memory plus the bounty ledger's recent targets.
        prior_texts: list = []
        try:
            prior_texts += _texts_of(await _maybe(ctx.recall("belief challenge severe test verdict")))
        except Exception:
            pass
        bounty = await _maybe(ctx.brain_get(_API + "/brain/bounty"))
        if isinstance(bounty, dict):
            prior_texts += [ln for ln in (bounty.get("report") or "").splitlines() if "]" in ln]
        prior_tokens = [t for t in (fd._tokens(p) for p in prior_texts)
                        if len(t) >= _MIN_PRIOR_TOKENS]

        considered = 0
        skipped: list = []
        for target in targets:
            if not isinstance(target, dict) or not target.get("path"):
                continue
            considered += 1
            title = (target.get("title") or Path(target["path"]).stem).strip()
            slug = Path(target["path"]).stem

            allowed, why_board = _board_allows(title + " " + slug)
            if not allowed:
                skipped.append("board: %s" % why_board)
                continue

            own = fd._tokens(title + " " + slug.replace("-", " "))
            if any(fd._containment(own, p) >= _NOVELTY for p in prior_tokens):
                skipped.append("already challenged (containment >= %.1f)" % _NOVELTY)
                continue

            try:
                text = Path(target["path"]).read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                skipped.append("unreadable note (%s)" % _ascii(exc))
                continue

            note_date = _frontmatter(text, "date")[:10]
            art = _channel_artifact(text, note_date, experiments)
            cite = await _channel_citation(ctx, _identifiers(text))

            # A receipt/citation kill is decisive on its own and needs no simulation.
            hard = art if art.get("verdict") == "kill" else (
                cite if cite.get("verdict") == "kill" else None)
            if hard is not None:
                riders = [e for e in (art.get("evidence"), cite.get("evidence"))
                          if e and e != hard["evidence"]]
                return await _record(
                    ctx, info, target, title, "kill", hard["evidence"], riders, None,
                    considered, skipped,
                    killer="the artifact/citation the note itself names, present where the note "
                           "says it is")

            riders = [e for e in (art.get("evidence"), cite.get("evidence")) if e]

            sizes = _sample_sizes(text)
            pair = _rate_pair(text)
            if pair is None:
                skipped.append("no rate comparison to attack")
                continue
            if len(sizes) != 1:
                skipped.append("sample size %s -- cannot attribute the comparison"
                               % ("absent" if not sizes else "ambiguous %s" % sorted(sizes)))
                continue
            n = sizes.pop()

            code = _lab_code(title, pair, n)
            run = await _maybe(ctx.lab_run("voss-null-floor: %s" % title[:70], code))
            if not isinstance(run, dict) or not run.get("ok"):
                skipped.append("lab run failed")
                continue
            lab_id = run.get("id")
            stats = _parse_lab(run.get("output") or "")
            if _RHO_SURVIVE not in stats or _RHO_KILL not in stats:
                skipped.append("lab produced no usable null (lab %s)" % lab_id)
                continue

            p_wide = stats[_RHO_SURVIVE]["p"]
            p_tight = stats[_RHO_KILL]["p"]
            band = stats[_RHO_KILL]["band"]
            observed = abs(pair["a"] - pair["b"])

            if min(abs(p_wide - _ALPHA), abs(p_tight - _ALPHA)) < _ALPHA_MARGIN:
                return _idle("verdict sits within Monte-Carlo noise of alpha (p_wide=%.4f "
                             "p_tight=%.4f, alpha=%.2f +/- %.3f) -- refusing to rule; lab %s"
                             % (p_wide, p_tight, _ALPHA, _ALPHA_MARGIN, lab_id), title)

            measured = ("MEASURED: observed delta=%.4f (%s=%.4f vs %s=%.4f, row '%s') at n=%d; "
                        "null p=%.4f at rho=0.0 (independent) and p=%.4f at rho=0.8 (paired); "
                        "kill_band_95=%.4f at rho=0.8; trials=%d seed=%d"
                        % (observed, pair["col_a"], pair["a"], pair["col_b"], pair["b"],
                           pair["row"], n, p_wide, p_tight, band, _TRIALS, _SEED))

            if p_wide < _ALPHA:
                killer = (("an observed gap of %.4f or less -- that is kill_band_95 at rho=0.8, the "
                           "largest gap the tightest null we grant produces by chance. The belief "
                           "reports %.4f, %.1fx the killing gap."
                           % (band, observed, observed / band)) if band > 0 else
                          "any gap inside the rho=0.8 null band (the band collapsed to 0 at this n)")
                return await _record(ctx, info, target, title, "survived", measured, riders,
                                     lab_id, considered, skipped, killer=killer)

            if p_tight >= _ALPHA:
                killer = ("a gap larger than kill_band_95=%.4f at rho=0.8. The belief reports only "
                          "%.4f, which this null reproduces by chance %.1f%% of the time."
                          % (band, observed, 100.0 * p_tight))
                return await _record(ctx, info, target, title, "kill", measured, riders,
                                     lab_id, considered, skipped, killer=killer)

            return _idle("attacked '%s': p=%.4f at rho=0.0 and p=%.4f at rho=0.8, so the verdict "
                         "turns on whether the design was paired -- the note does not say. No "
                         "verdict recorded (lab %s)."
                         % (_ascii(title)[:70], p_wide, p_tight, lab_id), title)

        summary = _summarise(skipped, limit=6)
        info("[voss] walked %d targets, none attackable: %s" % (considered, _ascii(summary)))
        return _idle("walked %d candidates, none yielded a groundable verdict: %s"
                     % (considered, summary))

    except Exception as exc:                                   # cycle() must NEVER raise
        return _error("%s: %s" % (type(exc).__name__, _ascii(exc)))


async def _record(ctx, info, target, title, verdict, measured, riders, lab_id,
                  considered, skipped, killer) -> dict:
    """Write the verdict to the belief note + the bounty ledger, and build the report.

    A kill is stamped `retired`, not `revised`: `revised` means a sharper v2 supersedes the belief,
    and this organ does not write one -- it only shows the evidence is not there. `retired` carries
    a `resurrect_when` so the graveyard entry says what would bring the belief back.
    """
    is_kill = verdict == "kill"
    stamp = "retired" if is_kill else "survived"
    resurrect = ("re-measured on a sample large enough that the reported gap clears the rho=0.8 "
                 "null band, or re-stated with its design (paired vs independent) named")

    reason = "%s | WOULD HAVE KILLED IT: %s" % (measured, killer)
    if lab_id:
        reason += " | lab %s" % lab_id

    posted = None
    try:
        posted = await _maybe(ctx.brain_post(
            _API + "/brain/belief-revise",
            {"path": target["path"], "verdict": stamp, "by_note": "",
             "reason": reason[:900],
             # CLAUDE.md gives Voss the bounty ledger; repair_ledger.py:65 says the store's `by`
             # field decides. Writing the name he already holds 31 records under keeps his standing
             # one identity instead of forking it.
             "challenger": ORGAN["agent"],
             "resurrect_when": resurrect if is_kill else ""},
            30))
    except Exception as exc:
        info("[voss] belief-revise POST failed: %s" % _ascii(exc))
    ok = isinstance(posted, dict) and not posted.get("error")

    parts = [
        "VERDICT: %s -- Sergeant Voss attacked this belief and %s.\n"
        % (verdict.upper(), "killed it" if is_kill else "failed to kill it"),
        "\nBELIEF: %s\nNOTE:   %s\n" % (title, target["path"]),
        "\nTHE ATTACK\n%s\n" % measured,
        "\nWOULD HAVE KILLED IT: %s\n" % killer,
    ]
    if riders:
        parts.append("\n" + "\n".join(riders) + "\n")
    if lab_id:
        parts.append("\nlab %s\n" % lab_id)
    parts.append("\nRecorded as '%s' on the belief note and on the bounty ledger%s.\n"
                 % (stamp, "" if ok else " -- BRAIN WRITE FAILED, verdict NOT persisted"))
    if not is_kill:
        parts.append("\nA survival is not a consolation prize: this belief was handed a test that "
                     "could have ended it and it did not end. The killing condition above is the "
                     "receipt that the test was real.\n")
    content = "".join(parts)

    info("[voss] %s: %s | considered %d targets, skipped %d | lab %s"
         % (verdict, _ascii(title)[:70], considered, len(skipped), lab_id or "-"))

    return {"status": "ok", "decisive": True,
            "title": "Belief challenge (%s): %s" % (verdict, title),
            "content": content, "lab_id": lab_id,
            "why": "walked %d targets (%d skipped: %s); attacked '%s' -> %s"
                   % (considered, len(skipped), _summarise(skipped),
                      _ascii(title)[:60], verdict)}
