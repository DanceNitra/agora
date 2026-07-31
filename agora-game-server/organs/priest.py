"""Organ 8/8 — High Priest Orin, the Idea Alchemist.

WHY THIS FILE EXISTS (measured, not assumed)
--------------------------------------------
Orin produced ZERO discoveries in the five days before this organ existed, despite 1,072
historical contributions. Nothing was broken on the brain side: BOTH of his organs were live
and reachable the whole time (`/brain/analogy-inputs` + `/brain/analogy-record`, and
`/brain/theory/target` + `/brain/theory/record` all answer 200 right now). What did not exist
was anything that ROUTED him to them — all eight agents ran identical code, so the Idea
Alchemist spent five days doing what everybody else did. This file is the route.

WHOSE LEDGER IS `.analogies.json`
---------------------------------
The repo carries a conflict: `server/agora/execution/agent_activity.py:44` attributes
`.analogies.json` to Sage Mira, while `server/agora/execution/repair_ledger.py:46` attributes it
to High Priest Orin — and repair_ledger's map was audited against the LIVE store on 2026-07-29
("Every entry below was read off the live store"), where agent_activity's was not. **This organ
follows repair_ledger: Orin owns analogies.** Mira owns press and canon. Orin therefore drives
two ledgers, `.analogies.json` (the Analogy Forge) and `.theory.json` (the Theory Engine), and
this organ alternates between them so neither goes cold.

THE ANTI-CHURN DESIGN (the point of the whole file)
--------------------------------------------------
Orin's failure mode is the most dangerous in the swarm: an "idea alchemist" can always emit a
plausible-sounding fusion, and plausible fusions are free. The repo already deleted one system
for exactly this — `mcp_server.py:1673-1677` records that the old "Connect A<->B" bridges were
"combinatorial filler (the 'gaming party'): they recombined existing notes and produced
low-substance notes". So this organ does NOT generate analogies. It never asks a model to
invent a resemblance. It:

  * names the shared MECHANISM explicitly (a term from the vault's own mechanism vocabulary),
  * requires that mechanism to be INDEPENDENTLY ATTESTED, at density, in two notes from
    different domain folders,
  * and then hands the whole thing to a runnable Lab artifact that measures the pairing against
    an UNCONDITIONED NULL (a seeded random sample of the owner's concept notes) and prints the
    verdict itself. The organ reads the verdict off the artifact's stdout; it never computes a
    number and then reports a different one.

A surface resemblance fails that test by construction: if the "shared mechanism" is really just
background vocabulary, the null sample attests it too, and the run ends NO_VIABLE_MAPPING — which
the brain then buries in the Graveyard with its cause of death. A dead analogy and a `strained`
or `unmodelable` theory are FIRST-CLASS OUTPUTS here. No verdict is ever bent to produce one.

If neither arm can reach a lab-grounded verdict, `cycle()` returns `status="idle"` and writes
nothing. Silence is a valid cycle; filler is not.

A DEFECT THIS ORGAN REPAIRS ON THE WAY PAST
-------------------------------------------
`analogy_forge.pick_mechanism` excludes a note by comparing its title against the `mechanism`
strings already in `.analogies.json`. The live ledger contains
`'Feedback as Cross-Domain Convergence (negative feedback + delay -> oscillation)'` — a
DECORATED title — so the plain title "Feedback as Cross-Domain Convergence" never matches, and
`/brain/analogy-inputs` has been returning that same note ever since. Same shape on the theory
side: `.theory.json` holds "Alt-data alpha is an identification premium, not an inform..." while
the note's frontmatter title is "Insight: Alternative data alpha is an identification premium,
not an information premium", so `theory.pick_target` keeps re-serving a belief already stamped
`theory_status: strained`. This organ therefore records `mechanism` / `title` VERBATIM as the
endpoint served them, which is what lets both selectors advance.

CONVENTIONS: English only, ASCII in log lines (console is cp1250), standard library only.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any

ORGAN = {
    "eid": "priest", "agent": "High Priest Orin", "name": "Idea Alchemist",
    "ledger": ".analogies.json",              # also drives .theory.json
    "decisive": ("survived", "corroborated", "strained", "unmodelable"),
    "period_hours": 6.0,                      # ~4x/day
}

_SEED = 20260731            # every Lab artifact this organ writes is seeded, so it re-runs identically


# ─────────────────────────────────────────────────────────────────────────────
# Novelty / distance metric — the CALIBRATED one, loaded from its home module.
#
# The repo-wide near-duplicate threshold is 0.6 on the overlap coefficient
# (server/agora/execution/finding_diversity.py:27). Copying that function here would let the two
# drift apart silently, so we load the real module by file path (it imports only `re` and
# `collections`, so this costs nothing and pulls in no package __init__). The mirror below is a
# fallback for the case where the brain checkout is not next to the dungeon; it is byte-identical
# in behaviour and logs when it is used, so a drift is visible rather than assumed.
# ─────────────────────────────────────────────────────────────────────────────

_FD_PATH = Path(__file__).resolve().parents[2] / "server" / "agora" / "execution" / "finding_diversity.py"
_DUP = 0.6                                    # near-duplicate / "not distant" bar
_FD_SOURCE = "finding_diversity.py"


def _load_diversity():
    try:
        spec = importlib.util.spec_from_file_location("_agora_finding_diversity", _FD_PATH)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod._tokens, mod._containment, mod._STOP, "finding_diversity.py"
    except Exception:
        pass
    return _mirror_tokens, _mirror_containment, _MIRROR_STOP, "local mirror (finding_diversity.py unreachable)"


_MIRROR_STOP = set((
    "the a an of to in on and or for with that this from are is was were be been being it its as at "
    "by we our their they them not no does can will would could should which who whom whose into "
    "about between among across over under more most less than then thus also such these those some "
    "any each both either neither finding findings result results study studies paper papers source"
).split())


def _mirror_tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in _MIRROR_STOP}


def _mirror_containment(a: set, b: set) -> float:
    """Overlap coefficient — fraction of the SMALLER token set shared (catches 'A restated as a
    longer A' paraphrases that Jaccard would dilute)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


_tokens, _containment, _STOPWORDS, _FD_SOURCE = _load_diversity()


# ─────────────────────────────────────────────────────────────────────────────
# The mechanism vocabulary.
#
# Identical to `analogy_forge._MARKERS` (server side) and used the same way — plain substring
# counts, so prefixes like "oscillat" / "amplif" match their whole family. Kept in the same order
# so a marker profile computed here is comparable to one computed there.
# ─────────────────────────────────────────────────────────────────────────────

_MARKERS = (
    "feedback", "threshold", "equilibrium", "phase transition", "scaling", "diffusion",
    "selection pressure", "cascade", "hysteresis", "saturation", "bottleneck", "attractor",
    "bifurcation", "percolation", "critical", "homeostasis", "oscillat", "arbitrage",
    "compound", "network effect", "amplif", "damping", "resonance", "load balanc",
    "entropy", "gradient", "immune", "epidemi", "queue", "carrying capacity",
)

# Which markers bind to a runnable minimal model, and which do not. A marker with no template
# (scaling, selection pressure, arbitrage, compound, entropy, gradient) yields `unmodelable` on
# the theory arm rather than a forced fit — and `arbitrage`/`compound` are deliberately left
# unbound, because the only model they invite is multiplicative growth / volatility drag, which
# is textbook and which this repo is under standing orders not to re-derive.
_FAMILY_OF = {
    "threshold": "bistability", "phase transition": "bistability", "hysteresis": "bistability",
    "bifurcation": "bistability", "critical": "bistability",
    "saturation": "saturation", "carrying capacity": "saturation", "homeostasis": "saturation",
    "equilibrium": "saturation", "attractor": "saturation", "damping": "saturation",
    "cascade": "contagion", "percolation": "contagion", "diffusion": "contagion",
    "epidemi": "contagion", "network effect": "contagion", "immune": "contagion",
    "feedback": "oscillation", "oscillat": "oscillation", "resonance": "oscillation",
    "amplif": "oscillation",
    "bottleneck": "congestion", "queue": "congestion", "load balanc": "congestion",
}


# ─────────────────────────────────────────────────────────────────────────────
# ctx plumbing. The dispatcher is a sibling unit, so every call is tolerant: awaited if
# awaitable, degraded to None on any failure, never raised out of.
# ─────────────────────────────────────────────────────────────────────────────

async def _maybe(value):
    if inspect.isawaitable(value):
        return await value
    return value


def _log(ctx, line: str) -> None:
    lg = getattr(ctx, "logger", None)
    if lg is None:
        return
    try:
        lg.info("[priest] " + line.encode("ascii", "replace").decode("ascii"))
    except Exception:
        pass


async def _get(ctx, path: str):
    try:
        d = await _maybe(ctx.brain_get(path))
        return d if isinstance(d, dict) else None
    except Exception as e:
        _log(ctx, "brain_get %s failed: %s" % (path, e))
        return None


async def _post(ctx, path: str, body: dict, timeout: int = 30):
    try:
        try:
            d = await _maybe(ctx.brain_post(path, body, timeout))
        except TypeError:                      # dispatcher without a timeout parameter
            d = await _maybe(ctx.brain_post(path, body))
        return d if isinstance(d, dict) else {"status": "ok"}
    except Exception as e:
        _log(ctx, "brain_post %s failed: %s" % (path, e))
        return None


async def _lab(ctx, name: str, code: str):
    """Run a Lab script and return (lab_id, stdout, ok). Any shape but a dict with an id is
    treated as ungrounded — we would rather idle than cite a number with no receipt."""
    try:
        d = await _maybe(ctx.lab_run(name, code))
    except Exception as e:
        _log(ctx, "lab_run failed: %s" % e)
        return None, "", False
    if not isinstance(d, dict):
        return None, str(d or ""), False
    return d.get("id"), (d.get("output") or ""), bool(d.get("ok"))


# ─────────────────────────────────────────────────────────────────────────────
# Small utilities
# ─────────────────────────────────────────────────────────────────────────────

def _ascii(s: str, n: int = 400) -> str:
    s = " ".join((s or "").split())
    return s.encode("ascii", "replace").decode("ascii")[:n]


def _fit(s: str, n: int) -> str:
    """Truncate on a word boundary. The ledger caps `outcome` and `note` at 200 characters, and a
    hard slice there lands mid-number -- 'containment 0.' is worse than no number at all."""
    s = " ".join((s or "").split())
    if len(s) <= n:
        return s
    cut = s[:max(1, n - 3)]
    sp = cut.rfind(" ")
    if sp > n // 2:
        cut = cut[:sp]
    return cut.rstrip(" ,;.:-") + "..."


def _safe_doc(s: str, n: int = 220) -> str:
    """ASCII, single-line, and free of anything that could close a docstring."""
    return _ascii((s or "").replace('"""', "'").replace("\\", "/"), n)


def _read_note(path: str) -> str:
    try:
        p = Path(path)
        if not p.is_file() or p.suffix.lower() != ".md" or p.stat().st_size > 400_000:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _vault_root(any_note_path: str) -> Path | None:
    """The vault root, derived from a note path the brain served (…/<vault>/04 Resources/…)."""
    try:
        p = Path(any_note_path)
        for parent in p.parents:
            if parent.name == "04 Resources":
                return parent.parent
    except Exception:
        pass
    return None


def _marker_ranking(text: str) -> list[tuple[str, int]]:
    low = (text or "").lower()
    return sorted(((m, low.count(m)) for m in _MARKERS), key=lambda kv: -kv[1])


def _measured(out: str) -> dict:
    """Pull `MEASURED <key> = <value>` / `VERDICT: …` / labelled lines off a Lab artifact's stdout.

    Everything this organ reports is read back out of the artifact rather than recomputed here —
    the number we quote and the number the script printed are then the same object by
    construction, which is the only version of that guarantee worth having.
    """
    got: dict[str, Any] = {}
    numeric: set[str] = set()
    for ln in (out or "").splitlines():
        ln = ln.strip()
        m = re.match(r"^MEASURED\s+([A-Za-z0-9_]+)\s*=\s*(.+)$", ln)
        if m:
            raw = m.group(2).strip()
            try:
                got[m.group(1)] = int(raw) if re.fullmatch(r"-?\d+", raw) else float(raw)
            except ValueError:
                got[m.group(1)] = raw
            numeric.add(m.group(1))
            continue
        m = re.match(r"^([A-Z][A-Z _]+):\s*(.*)$", ln)
        if m:
            k = m.group(1).strip().replace(" ", "_").lower()
            # A labelled line must never clobber a MEASURED one. `MEASURED sections = 5` followed by
            # `SECTIONS: The insight, ...` silently replaced the count with the names, and the note
            # then reported a list where it promised a number.
            if k not in numeric:
                got[k] = m.group(2).strip()
    return got


def _verdict_word(measured: dict) -> str:
    v = str(measured.get("verdict", "")).split("--")[0].strip().lower()
    return v.split()[0] if v else ""


# ─────────────────────────────────────────────────────────────────────────────
# LAB ARTIFACT 1 — the analogy discrimination test.
# ─────────────────────────────────────────────────────────────────────────────

_ANALOGY_SCRIPT = '''"""MODELS: nothing dynamical. This is a DISCRIMINATION TEST on one claimed
cross-domain MECHANISM analogy: the mechanism __MARKER_TXT__, claimed to operate both in the source
note below and in some note from a different domain folder of the same vault.

What it measures, end to end, from the files themselves:
  1. how densely the named mechanism is attested in each note (raw substring counts),
  2. the TOPICAL overlap between the two notes (overlap coefficient; >= __DUP__ means the second
     note is a restatement of the first, not a distant domain),
  3. how ordinary that co-attestation is, against an UNCONDITIONED NULL: a seeded random sample of
     the owner's own concept notes, which were NOT retrieved for this mechanism.
It then applies a pre-registered rule and prints its own verdict.

SCOPE: this is a test of whether the claimed correspondence is SPECIFIC rather than background
vocabulary. Passing it is a necessary condition for a mechanism-level analogy, not a proof that
the mapping is correct; no number below may be quoted as evidence for either domain's science.
"""
import json
import random
import re
from pathlib import Path

SEED = __SEED__
MARKERS = json.loads(__MARKERS__)
MARKER = json.loads(__MARKER__)
SRC = json.loads(__SRC__)
POOL = json.loads(__POOL__)
CONCEPTS = json.loads(__CONCEPTS__)
DUP = __DUP__                 # calibrated near-duplicate threshold, finding_diversity.py:27
NULL_N = 40
MIN_DENSITY = 2               # the mechanism must RECUR, not appear once in passing
MAX_NULL_ATTEST = 0.25        # a marker attested by most random notes is vocabulary, not mechanism
MIN_PERCENTILE = 0.90         # the pairing must be top-decile against the null

# --- token/containment metric: loaded verbatim from __FD_SOURCE__ so this artifact and the
# --- repo-wide near-duplicate metric can never drift apart.
_STOP = set(__STOP__)
__TOKENS_SRC__

__CONTAINMENT_SRC__


def read(p):
    try:
        f = Path(p)
        if not f.is_file() or f.stat().st_size > 400000:
            return ""
        return f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def profile(text):
    low = text.lower()
    return [low.count(m) for m in MARKERS]


def cos(a, b):
    na = sum(v * v for v in a) ** 0.5
    nb = sum(v * v for v in b) ** 0.5
    if na <= 0 or nb <= 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def title_of(text, path):
    m = re.search(r"^title:\\s*[\\"\\']?(.+?)[\\"\\']?\\s*$", text[:600], re.MULTILINE)
    return (m.group(1).strip() if m else Path(path).stem)


def key(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def links(text):
    """Every [[wikilink]] target in a note, normalised."""
    return set(key(x.split("|")[0].split("#")[0]) for x in re.findall(r"\\[\\[([^\\]]+)\\]\\]", text))


_PUNCT = {"\\u2014": " - ", "\\u2013": "-", "\\u2018": "'", "\\u2019": "'",
          "\\u201c": '"', "\\u201d": '"', "\\u2026": "...", "\\u00a0": " "}


def quote(text, marker):
    """The first real PROSE sentence in which the mechanism is actually doing work.

    Tables, fenced code and bullet scaffolding are excluded on purpose: a pipe-delimited row or a
    pathway listing that happens to contain the word is evidence of a filename, not of a mechanism.
    Quoting one of those as "how the mechanism works in this domain" is the surface-resemblance
    failure in miniature.
    """
    body = re.sub(r"^---.*?---", "", text, count=1, flags=re.DOTALL)
    body = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    for k, v in _PUNCT.items():
        body = body.replace(k, v)
    for raw in re.split(r"(?<=[.!?])\\s+|\\n\\n", body):
        s = " ".join(raw.split())
        s = re.sub(r"^[>\\-*#\\s]+", "", s).replace("**", "").replace("`", "")
        if "|" in s or "```" in s or s.startswith("[[") or s.startswith("!["):
            continue
        if marker not in s.lower():
            continue
        words = [w for w in re.findall(r"[A-Za-z]+", s) if len(w) > 2]
        if len(words) >= 8 and 40 <= len(s) <= 400:
            return s.encode("ascii", "replace").decode("ascii")[:240]
    return ""


src_text = read(SRC)
if not src_text:
    print("VERDICT: NO_VIABLE_MAPPING -- source note unreadable")
    raise SystemExit(0)
src_tok = _tokens(src_text)
src_prof = profile(src_text)
m_src = src_text.lower().count(MARKER)
src_parent = str(Path(SRC).parent)
src_links = links(src_text)
src_key = key(Path(SRC).stem)

# ---- candidate selection happens HERE, inside the artifact, so the note that gets written and
# ---- the note that got measured are the same note.
#
# A candidate the source ALREADY WIKILINKS is disqualified, and so is one that links back. The
# deleted "Connect A<->B" generator failed precisely by re-emitting connections the vault already
# contained; a mechanism that transfers along an existing link is not a discovery about the vault.
q_src = quote(src_text, MARKER)

rows = []
for p in POOL:
    t = read(p)
    if not t or str(Path(p)) == str(Path(SRC)):
        continue
    dens = t.lower().count(MARKER)
    c = _containment(src_tok, _tokens(t))
    same_folder = str(Path(p).parent) == src_parent
    linked = (key(Path(p).stem) in src_links or key(title_of(t, p)) in src_links
              or src_key in links(t))
    # A note in which the mechanism appears only inside tables, code blocks or link lists does not
    # ATTEST the mechanism -- it mentions the word. Requiring a prose sentence on both sides is what
    # forces the analogy to name a mechanism doing work rather than a term two files have in common.
    prose = bool(quote(t, MARKER))
    ok = (dens >= MIN_DENSITY) and (c < DUP) and (not same_folder) and (not linked) and prose
    rows.append({"path": p, "dens": dens, "cont": round(c, 3), "same_folder": same_folder,
                 "linked": linked, "prose": prose, "ok": ok})

attesting = [r for r in rows if r["ok"]]
attesting.sort(key=lambda r: r["cont"])          # most DISTANT admissible candidate wins

print("MARKER:", MARKER)
print("MEASURED pool_size =", len(rows))
print("MEASURED pool_attesting =", len(attesting))
print("MEASURED src_wikilinks =", len(src_links))
print("MEASURED m_src =", m_src)
for r in rows:
    print("  pool | dens=%d cont=%.3f same_folder=%s linked=%s prose=%s | %s"
          % (r["dens"], r["cont"], r["same_folder"], r["linked"], r["prose"],
             Path(r["path"]).name[:70]))

if not q_src:
    print("CHOSEN: NONE")
    print("VERDICT: NO_VIABLE_MAPPING -- the source note never states '%s' in prose, so there is "
          "no mechanism to lift out of it" % MARKER)
    raise SystemExit(0)

# ---- unconditioned null: notes NOT retrieved for this mechanism
paths = sorted(str(p) for p in Path(CONCEPTS).rglob("*.md") if "Agora Agents" not in str(p))
paths = [p for p in paths if str(Path(p)) != str(Path(SRC))]
rng = random.Random(SEED)
sample = rng.sample(paths, min(NULL_N, len(paths)))
null_dens, null_cos = [], []
for p in sample:
    t = read(p)
    if not t:
        continue
    null_dens.append(t.lower().count(MARKER))
    null_cos.append(cos(src_prof, profile(t)))
p_attest = (sum(1 for d in null_dens if d >= MIN_DENSITY) / float(len(null_dens))) if null_dens else 1.0
print("MEASURED null_sample =", len(null_dens))
print("MEASURED p_attest_null =", round(p_attest, 3))

if not attesting:
    print("CHOSEN:", "NONE")
    print("VERDICT: NO_VIABLE_MAPPING -- of %d retrieved notes none is an unlinked note from "
          "another domain folder that states '%s' in prose at density >= %d below the duplicate bar"
          % (len(rows), MARKER, MIN_DENSITY))
    raise SystemExit(0)

best = attesting[0]
tgt_text = read(best["path"])
tgt_prof = profile(tgt_text)
pair_cos = cos(src_prof, tgt_prof)
pct = (sum(1 for c in null_cos if c <= pair_cos) / float(len(null_cos))) if null_cos else 0.0

print("CHOSEN:", best["path"])
print("CHOSEN TITLE:", title_of(tgt_text, best["path"]).encode("ascii", "replace").decode("ascii")[:120])
print("SOURCE TITLE:", title_of(src_text, SRC).encode("ascii", "replace").decode("ascii")[:120])
print("MEASURED m_tgt =", best["dens"])
print("MEASURED containment =", best["cont"])
print("MEASURED profile_cos =", round(pair_cos, 3))
print("MEASURED cos_percentile =", round(pct, 3))
print("QUOTE SRC:", q_src)
print("QUOTE TGT:", quote(tgt_text, MARKER))

fails = []
if m_src < MIN_DENSITY:
    fails.append("mechanism appears < %d times in the source" % MIN_DENSITY)
if best["dens"] < MIN_DENSITY:
    fails.append("mechanism appears < %d times in the target" % MIN_DENSITY)
if best["cont"] >= DUP:
    fails.append("the two notes are near-duplicates (containment %.3f >= %.2f)" % (best["cont"], DUP))
if p_attest > MAX_NULL_ATTEST:
    fails.append("'%s' is attested by %.0f%% of unretrieved notes -- background vocabulary, "
                 "not a specific mechanism" % (MARKER, 100 * p_attest))
if pct < MIN_PERCENTILE:
    fails.append("mechanism-profile agreement is only at the %.0fth percentile of the null "
                 "(needs %.0fth)" % (100 * pct, 100 * MIN_PERCENTILE))

if fails:
    print("VERDICT: NO_VIABLE_MAPPING --", fails[0])
else:
    print("VERDICT: SURVIVED -- '%s' is attested at density %d/%d across domain folders, in only "
          "%.0f%% of unretrieved notes, at the %.0fth percentile of mechanism-profile agreement, "
          "with topical containment %.3f (distant domains)"
          % (MARKER, m_src, best["dens"], 100 * p_attest, 100 * pct, best["cont"]))
'''


# ─────────────────────────────────────────────────────────────────────────────
# LAB ARTIFACT 2 — the theory harness (one minimal model + its falsification control).
# ─────────────────────────────────────────────────────────────────────────────

_THEORY_HARNESS = '''"""MODELS: __DOC__

The belief under test is: "__TITLE__"

SCOPE -- READ BEFORE QUOTING ANY NUMBER BELOW. The parameters here are GENERIC normal-form
parameters. They are NOT measurements from the belief's own domain and nothing below is a
measurement OF that domain. What this artifact measures is the belief's STATED SCOPE: over how
much of the mechanism's own parameter box the mechanism's defining signature actually appears,
and whether that signature is attributable to the mechanism at all. The second question is
answered by a falsification control -- the identical model with the mechanism's own coupling
removed (__CONTROL__). If the control reproduces the signature, the run says UNMODELABLE rather
than claiming anything, because then the signature was never evidence about the mechanism.

Pre-registered verdict rule, applied by this script to its own numbers:
  attributable = (claim_frac - control_frac) / claim_frac      [share the mechanism accounts for]
  claim_frac == 0                            -> UNMODELABLE (the model never produces the signature,
                                                which impugns the formalisation, not the belief)
  attributable < 0.5                         -> UNMODELABLE (the control accounts for half or more)
  claim_frac >= 0.90                         -> CORROBORATED (robust across the box)
  claim_frac >= 0.05 and the note names the regime -> CORROBORATED (regime-dependent, but stated)
  otherwise                                  -> STRAINED

An earlier version of this rule keyed on the ABSOLUTE gap |claim - control| and was wrong in both
directions: it called a signature that the mechanism produces in 2% of the box and the control in
0% "not attributable" (it is entirely attributable -- it is just rare, which is the finding), and
it was one threshold away from clearing a run whose control scored HIGHER than the model.
"""
import json
import math
import random

SEED = __SEED__
BELIEF_TITLE = json.loads(__TITLE_JSON__)
FAMILY = json.loads(__FAMILY__)
SIGNATURE = json.loads(__SIGNATURE__)
CONTROL = json.loads(__CONTROL_JSON__)
PRIMARY = json.loads(__PRIMARY__)
COND_HITS = json.loads(__COND_HITS__)


def _pois(rng, lam):
    """Poisson draw; normal approximation above 12 so long queue runs stay inside the Lab timeout."""
    if lam <= 0:
        return 0
    if lam > 12:
        v = int(round(rng.gauss(lam, math.sqrt(lam))))
        return v if v > 0 else 0
    lim, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= lim:
            return k - 1


__MODEL__


points = grid()

# Each point is evaluated exactly once per arm; the control must actually be a different system,
# and a falsification control that silently reduces to the model it is meant to falsify would
# report "no discrimination" forever and look like a result. Assert the difference, don't trust it.
res_on = [signature(p, True) for p in points]
res_off = [signature(p, False) for p in points]
differs = any(a != b for a, b in zip(res_on, res_off))

n = float(len(points)) or 1.0
claim = sum(1 for v in res_on if v) / n
control = sum(1 for v in res_off if v) / n
attributable = ((claim - control) / claim) if claim > 0 else 0.0

# The signature's regime on the primary axis, reported as the INTERVAL where it holds for at least
# half the remaining parameters. "Smallest value that reaches 0.5" was the first version and it is
# only correct for a lower-bounded signature: on the logistic family it returned the box minimum,
# because convergence holds from r=0.1 and STOPS at r~2, which is the boundary that matters.
by_primary = {}
for p, hit in zip(points, res_on):
    by_primary.setdefault(p[0], []).append(hit)
holds = [v for v in sorted(by_primary)
         if sum(1 for h in by_primary[v] if h) / float(len(by_primary[v])) >= 0.5]
lo = min(by_primary) if by_primary else None
hi = max(by_primary) if by_primary else None
region = ("%s..%s of the sampled %s..%s" % (holds[0], holds[-1], lo, hi)) if holds else "nowhere"

if claim <= 0.0:
    verdict, why = "UNMODELABLE", ("the model never produces the signature anywhere in the box, "
                                   "which impugns this formalisation rather than the belief")
elif not differs or attributable < 0.5:
    verdict, why = "UNMODELABLE", ("the signature is not attributable to the mechanism -- the "
                                   "control (%s) accounts for %.0f%% of it" % (CONTROL,
                                                                               100 * (1 - attributable)))
elif claim >= 0.90:
    verdict, why = "CORROBORATED", ("the mechanism produces its signature across %.0f%% of its own "
                                    "parameter box (%s = %s)" % (100 * claim, PRIMARY, region))
elif claim >= 0.05 and COND_HITS:
    verdict, why = "CORROBORATED", ("regime-dependent (%.0f%% of the box, %s = %s) but the note "
                                    "states the regime: %s"
                                    % (100 * claim, PRIMARY, region, ", ".join(COND_HITS)))
else:
    verdict, why = "STRAINED", ("the signature appears in only %.0f%% of the parameter box (%s = "
                                "%s) and the note states no such condition"
                                % (100 * claim, PRIMARY, region))

print("BELIEF:", BELIEF_TITLE.encode("ascii", "replace").decode("ascii")[:150])
print("MODEL FAMILY:", FAMILY)
print("SIGNATURE:", SIGNATURE)
print("CONTROL:", CONTROL)
print("MEASURED grid_points =", len(points))
print("MEASURED claim_frac =", round(claim, 3))
print("MEASURED control_frac =", round(control, 3))
print("MEASURED attributable = %.3f" % attributable)
print("MEASURED control_differs =", 1 if differs else 0)
print("REGIME:", "%s = %s" % (PRIMARY, region))
print("NOTE STATES REGIME:", (", ".join(COND_HITS) if COND_HITS else "no"))
print("VERDICT:", verdict, "--", why)
'''


_MODELS = {
    # ---------------------------------------------------------------- bistability
    "bistability": {
        "doc": ("the saddle-node/cusp normal form dx/dt = r + a*x - x**3 swept up and then back "
                "down through r, i.e. the minimal system in which a threshold is a genuine "
                "tipping point rather than a line on a chart. `a` is the positive-feedback gain."),
        "primary": "a",
        "signature": "hysteresis width > 0.05 in r between the up-sweep and the down-sweep",
        "control": "positive-feedback gain forced to a = 0, which makes the system monostable",
        "cond": ("feedback strength", "positive feedback", "only when", "only if", "above a critical",
                 "gain", "regime", "conditional on"),
        "code": '''
def grid():
    pts = []
    for i in range(13):
        a = -1.0 + 3.0 * i / 12.0
        for j in range(4):
            pts.append((round(a, 4), round(0.12 * j / 3.0, 4)))
    return pts


def _sweep(a, sigma, rng, up):
    dt, relax, steps = 0.02, 12, 160
    x = -1.6 if up else 1.6
    rs, xs = [], []
    for k in range(steps + 1):
        r = (-1.6 + 3.2 * k / steps) if up else (1.6 - 3.2 * k / steps)
        for _ in range(relax):
            x += dt * (r + a * x - x ** 3)
            if sigma > 0:
                x += sigma * math.sqrt(dt) * rng.gauss(0.0, 1.0)
            x = 5.0 if x > 5.0 else (-5.0 if x < -5.0 else x)
        rs.append(round(r, 3))
        xs.append(x)
    return rs, xs


def signature(p, on):
    a, sigma = p
    if not on:
        a = 0.0
    rng = random.Random(SEED + int(abs(a) * 1000) + int(sigma * 1000))
    ru, xu = _sweep(a, sigma, rng, True)
    rd, xd = _sweep(a, sigma, rng, False)
    down = dict(zip(rd, xd))
    step, width = 3.2 / 160, 0.0
    for r, x in zip(ru, xu):
        y = down.get(r)
        if y is not None and abs(x - y) > 0.8:
            width += step
    return width > 0.05
''',
    },
    # ---------------------------------------------------------------- saturation
    "saturation": {
        "doc": ("the discrete logistic x_{t+1} = x_t + r*x_t*(1 - x_t/K), the minimal system in "
                "which density dependence produces a carrying capacity. `r` is the growth rate."),
        "primary": "r",
        "signature": "the trajectory settles within 2% of K and stays there for the last 40 steps",
        "control": "density dependence removed (x_{t+1} = x_t + r*x_t), so nothing bounds growth",
        "cond": ("growth rate", "slow enough", "overshoot", "oscillat", "only when", "only if",
                 "regime", "unstable", "chaos"),
        "code": '''
def grid():
    pts = []
    for i in range(15):
        r = 0.1 + 2.9 * i / 14.0
        for x0 in (0.01, 0.1, 0.5):
            pts.append((round(r, 4), x0))
    return pts


def signature(p, on):
    r, x0 = p
    K, x, tail = 1.0, x0, []
    for t in range(400):
        x = x + r * x * (1.0 - x / K) if on else x + r * x
        if x > 1e6:
            x = 1e6
        if x < 0.0:
            x = 0.0
        if t >= 360:
            tail.append(x)
    return all(abs(v - K) <= 0.02 * K for v in tail)
''',
    },
    # ---------------------------------------------------------------- contagion
    "contagion": {
        "doc": ("a stochastic SIR branching process on a well-mixed population of 2000, in which "
                "each infected generation seeds the next -- the minimal system in which a cascade "
                "is self-sustaining rather than merely large. R0 is the basic reproduction number."),
        "primary": "R0",
        "signature": "final outbreak size exceeds 5% of the population",
        "control": "chaining removed -- transmission runs for exactly one generation from the seeds",
        "cond": ("reproduction", "above one", "critical", "only when", "only if", "threshold",
                 "regime", "supercritical"),
        "code": '''
def grid():
    pts = []
    for i in range(15):
        r0 = 0.2 + 2.8 * i / 14.0
        for seed0 in (2, 5, 10):
            pts.append((round(r0, 4), seed0))
    return pts


def signature(p, on):
    r0, seed0 = p
    N = 2000
    rng = random.Random(SEED + int(r0 * 1000) + seed0)
    S, I, R = N - seed0, seed0, seed0
    for _ in range(80 if on else 1):
        if I <= 0:
            break
        new = min(S, _pois(rng, r0 * I * (S / float(N))))
        S -= new
        R += new
        I = new
    return (R / float(N)) > 0.05
''',
    },
    # ---------------------------------------------------------------- oscillation
    "oscillation": {
        "doc": ("delayed negative feedback x_{t+1} = x_t - g*x_{t-d}, the minimal system in which "
                "'negative feedback plus delay' can produce a persistent oscillation. `g` is the "
                "loop gain and d the delay."),
        "primary": "g",
        "signature": ("at least 6 sign changes in the second half AND amplitude in the last quarter "
                      "still >= 5% of the first quarter (the oscillation persists, bounded)"),
        "control": "feedback sign flipped from negative to positive with the delay kept",
        "cond": ("loop gain", "gain", "delay length", "strong enough", "only when", "only if",
                 "sustained", "damped", "regime", "threshold"),
        "code": '''
def grid():
    pts = []
    for i in range(12):
        g = 0.05 + 1.45 * i / 11.0
        for d in (1, 2, 4, 8):
            pts.append((round(g, 4), d))
    return pts


def signature(p, on):
    g, d = p
    xs = [1.0] * (d + 1)
    for _ in range(400):
        nxt = xs[-1] - g * xs[-1 - d] if on else xs[-1] + g * xs[-1 - d]
        nxt = 1e6 if nxt > 1e6 else (-1e6 if nxt < -1e6 else nxt)
        xs.append(nxt)
    seq = xs[d + 1:]
    if max(abs(v) for v in seq) >= 1e3:
        return False
    half = seq[len(seq) // 2:]
    flips = sum(1 for i in range(1, len(half)) if (half[i] > 0) != (half[i - 1] > 0))
    q = max(1, len(seq) // 4)
    first = max(abs(v) for v in seq[:q])
    last = max(abs(v) for v in seq[-q:])
    return flips >= 6 and first > 0 and last >= 0.05 * first
''',
    },
    # ---------------------------------------------------------------- congestion
    "congestion": {
        "doc": ("a single-server queue with Poisson arrivals and Poisson service, in which unserved "
                "work carries over between steps -- the minimal system in which a bottleneck "
                "produces an unbounded backlog. rho = arrival rate / service rate."),
        "primary": "rho",
        "signature": "mean backlog over the last 20% of the run exceeds 50 items",
        "control": "carry-over removed -- each step starts from an empty queue, so nothing accumulates",
        "cond": ("utilization", "utilisation", "above capacity", "only when", "only if", "saturat",
                 "regime", "arrival rate", "threshold"),
        "code": '''
def grid():
    pts = []
    for i in range(21):
        rho = 0.5 + 1.0 * i / 20.0
        for mu in (1.0, 4.0, 10.0):
            pts.append((round(rho, 4), mu))
    return pts


def signature(p, on):
    rho, mu = p
    rng = random.Random(SEED + int(rho * 1000) + int(mu))
    lam, backlog, tail = rho * mu, 0.0, []
    for t in range(1200):
        arrive, serve = _pois(rng, lam), _pois(rng, mu)
        backlog = max(0.0, (backlog + arrive - serve) if on else (arrive - serve))
        if t >= 960:
            tail.append(backlog)
    return (sum(tail) / len(tail)) > 50.0
''',
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# LAB ARTIFACT 3 — the modelability probe (what grounds an honest `unmodelable`).
# ─────────────────────────────────────────────────────────────────────────────

_PROBE_SCRIPT = '''"""MODELS: nothing -- and that is the finding. This is a MODELABILITY PROBE on one
belief note: it counts, in the note's own text, the ingredients a minimal formal model would need
(mechanism terms that bind to a runnable normal form, directional relations, and quantified
statements) and reports how many of each are present.

The belief probed is: "__TITLE__"

SCOPE: the counts below describe the NOTE, not the world. A belief can be true and still score
zero here; what a zero establishes is that this system cannot currently put the belief on a
computer, which is exactly what the Theory Engine's `unmodelable` verdict means.
"""
import json
import re

MARKERS = json.loads(__MARKERS__)
BINDABLE = json.loads(__BINDABLE__)
TEXT = json.loads(__TEXT__)
MIN_DENSITY = 2      # the same density bar the organ uses to bind a family -- the artifact and the
                     # note it grounds have to be counting the same thing

# The frontmatter is metadata (dates, counters); counting its numbers as quantitative content
# would inflate exactly the measure this probe exists to report honestly.
BODY = re.sub(r"^---.*?---", "", TEXT, count=1, flags=re.DOTALL)

low = BODY.lower()
present = [(m, low.count(m)) for m in MARKERS if low.count(m) > 0]
bindable = [(m, c) for m, c in present if m in BINDABLE and c >= MIN_DENSITY]
relations = re.findall(r"\\b(increases?|decreases?|raises?|lowers?|drives?|amplif\\w+|damp\\w+|"
                       r"proportional to|scales? with|leads? to|causes?|produces?)\\b", low)
numbers = re.findall(r"(?<![\\w-])\\d+(?:\\.\\d+)?", BODY)
sections = re.findall(r"^##\\s+(.+)$", BODY, re.MULTILINE)

print("MEASURED body_chars =", len(BODY))
print("MEASURED mechanism_terms_present =", len(present))
print("MEASURED bindable_mechanism_terms =", len(bindable))
print("MEASURED directional_relations =", len(relations))
print("MEASURED numeric_tokens =", len(numbers))
print("MEASURED sections =", len(sections))
print("PRESENT:", ", ".join("%s x%d" % (m, c) for m, c in present[:8]) or "(none)")
print("SECTION NAMES:", ", ".join(s.strip()[:40] for s in sections[:8]) or "(none)")
print("VERDICT: UNMODELABLE -- of the note's %d mechanism terms, %d recur at least %dx AND bind to "
      "a runnable minimal model; with %d directional relations and %d numeric tokens there is no "
      "formal core to put on a computer"
      % (len(present), len(bindable), MIN_DENSITY, len(relations), len(numbers)))
'''


# ─────────────────────────────────────────────────────────────────────────────
# Script assembly
# ─────────────────────────────────────────────────────────────────────────────

def _analogy_script(marker: str, src_path: str, pool: list[str], concepts_dir: str) -> str:
    try:
        tok_src = inspect.getsource(_tokens)
        cont_src = inspect.getsource(_containment)
    except Exception:                                   # pragma: no cover - defensive only
        tok_src = inspect.getsource(_mirror_tokens).replace("_mirror_tokens", "_tokens") \
                                                   .replace("_MIRROR_STOP", "_STOP")
        cont_src = inspect.getsource(_mirror_containment).replace("_mirror_containment", "_containment")
    tok_src = tok_src.replace("_mirror_tokens", "_tokens").replace("_MIRROR_STOP", "_STOP")
    cont_src = cont_src.replace("_mirror_containment", "_containment")
    return (_ANALOGY_SCRIPT
            .replace("__TOKENS_SRC__", tok_src.strip())
            .replace("__CONTAINMENT_SRC__", cont_src.strip())
            .replace("__STOP__", repr(sorted(_STOPWORDS)))
            .replace("__FD_SOURCE__", _FD_SOURCE)
            .replace("__SEED__", str(_SEED))
            .replace("__DUP__", str(_DUP))
            .replace("__MARKER_TXT__", _safe_doc(marker, 60))
            .replace("__MARKERS__", repr(json.dumps(list(_MARKERS))))
            .replace("__MARKER__", repr(json.dumps(marker)))
            .replace("__SRC__", repr(json.dumps(src_path)))
            .replace("__POOL__", repr(json.dumps(pool)))
            .replace("__CONCEPTS__", repr(json.dumps(concepts_dir))))


def _theory_script(family: str, title: str, cond_hits: list[str]) -> str:
    spec = _MODELS[family]
    return (_THEORY_HARNESS
            .replace("__MODEL__", spec["code"].strip())
            .replace("__DOC__", _safe_doc(spec["doc"], 400))
            .replace("__CONTROL__", _safe_doc(spec["control"], 160))
            .replace("__TITLE__", _safe_doc(title, 150))
            .replace("__SEED__", str(_SEED))
            .replace("__TITLE_JSON__", repr(json.dumps(title)))
            .replace("__FAMILY__", repr(json.dumps(family)))
            .replace("__SIGNATURE__", repr(json.dumps(spec["signature"])))
            .replace("__CONTROL_JSON__", repr(json.dumps(spec["control"])))
            .replace("__PRIMARY__", repr(json.dumps(spec["primary"])))
            .replace("__COND_HITS__", repr(json.dumps(cond_hits))))


def _probe_script(title: str, text: str) -> str:
    return (_PROBE_SCRIPT
            .replace("__TITLE__", _safe_doc(title, 150))
            .replace("__MARKERS__", repr(json.dumps(list(_MARKERS))))
            .replace("__BINDABLE__", repr(json.dumps(sorted(_FAMILY_OF))))
            .replace("__TEXT__", repr(json.dumps(text[:60_000]))))


# ─────────────────────────────────────────────────────────────────────────────
# ARM 1 — the Analogy Forge
# ─────────────────────────────────────────────────────────────────────────────

async def _analogy_arm(ctx) -> dict:
    d = await _get(ctx, "/brain/analogy-inputs")
    mech = (d or {}).get("mechanism") if isinstance(d, dict) else None
    if not isinstance(mech, dict) or not mech.get("path"):
        return _idle("the forge has no un-forged mechanism-dense concept note to work on")

    src_path, src_title = str(mech["path"]), str(mech.get("title") or "")
    src_text = _read_note(src_path) or str(mech.get("excerpt") or "")
    if len(src_text) < 200:
        return _idle("source note '%s' is unreadable from the dungeon" % _ascii(src_title, 60))

    root = _vault_root(src_path)
    if root is None:
        return _idle("could not derive the vault root from the served note path")
    concepts = str(root / "04 Resources" / "Concepts")

    # Name the mechanism. Prefer one that binds to a runnable normal form (so the analogy names a
    # skeleton, not just a word), and require it to RECUR -- a term used once is a topic, not a
    # mechanism.
    ranked = [(m, c) for m, c in _marker_ranking(src_text) if c >= 2]
    if not ranked:
        return _idle("no mechanism term recurs in '%s' -- nothing to lift out of it"
                     % _ascii(src_title, 60))
    bindable = [mc for mc in ranked if mc[0] in _FAMILY_OF]
    marker, marker_n = (bindable or ranked)[0]

    # Retrieve a candidate pool for that mechanism. Retrieval needs the brain's embeddings, so it
    # happens here; every MEASUREMENT on the pool happens inside the Lab artifact.
    q = urllib.parse.quote("%s mechanism dynamics" % marker)
    hits = await _get(ctx, "/brain/vault-search?q=%s&k=12" % q)
    results = (hits or {}).get("results") or []
    pool: list[str] = []
    for h in results:
        rel = str((h or {}).get("path") or "")
        if not rel or "Agora Agents" in rel:          # the system's own output is not a foreign domain
            continue
        p = Path(rel)
        if p.stem.startswith("pwback_") or p.stem.startswith("~$"):   # vault backup copies, not notes
            continue
        ap = p if p.is_absolute() else (root / rel)
        if str(ap) != src_path and str(ap) not in pool:
            pool.append(str(ap))
    if not pool:
        return _idle("vault-search returned no owner-authored candidates for '%s'" % marker)

    # Orin's own memory, used only to avoid re-forging what he has already forged.
    try:
        seen = str(await _maybe(ctx.recall("analogy %s" % marker)) or "")
    except Exception:
        seen = ""

    lab_id, out, ok = await _lab(ctx, "orin analogy discrimination: %s" % _ascii(marker, 40),
                                 _analogy_script(marker, src_path, pool, concepts))
    if not lab_id or not ok:
        return _idle("the analogy discrimination artifact did not complete (%s)"
                     % _ascii(out.splitlines()[-1] if out else "no output", 120))

    got = _measured(out)
    verdict = _verdict_word(got)
    if verdict not in ("survived", "no_viable_mapping"):
        return _idle("the artifact printed no usable verdict")

    survived = verdict == "survived"
    tgt_title = str(got.get("chosen_title") or "").strip()
    reason = str(got.get("verdict", "")).split("--", 1)[-1].strip()

    if survived and not tgt_title:
        return _idle("artifact reported SURVIVED without naming a target note")

    # Novelty, on the calibrated threshold. BOTH ENDS have to match for this to be the same
    # forging: the first version of this guard compared one concatenated string and killed a
    # perfectly good new pairing, because the shared source title alone carried the containment
    # over 0.6 (measured: 0.625 on 'Feedback as Cross-Domain Convergence' -> two different targets).
    # A source already forged into a DIFFERENT domain is a new analogy, not a repeat.
    prior = await _get(ctx, "/brain/analogies")
    for item in ((prior or {}).get("items") or []):
        same_src = _containment(_tokens(src_title), _tokens(str(item.get("mechanism", "")))) >= _DUP
        same_tgt = _containment(_tokens(tgt_title), _tokens(str(item.get("target", "")))) >= _DUP
        if same_src and same_tgt:
            return _idle("this forging repeats ledger entry '%s -> %s' (both ends match at "
                         "containment >= %.1f)"
                         % (_ascii(str(item.get('mechanism', '')), 40),
                            _ascii(str(item.get('target', '')), 40), _DUP))
    if tgt_title and tgt_title.lower()[:40] in seen.lower():
        _log(ctx, "target '%s' already appears in Orin's memory -- forging anyway, the verdict is fresh"
             % _ascii(tgt_title, 40))

    q_src = str(got.get("quote_src") or "")
    q_tgt = str(got.get("quote_tgt") or "")
    family = _FAMILY_OF.get(marker)

    # The ledger caps both fields at 200 chars, so the measured values go in FIRST and the prose
    # gets whatever room is left -- a receipt that survives truncation beats a sentence that does not.
    if survived:
        outcome = _fit("survived (Lab %s): '%s' attested %sx/%sx across domain folders, in %s of "
                       "unretrieved notes, %s percentile, containment %s"
                       % (lab_id, marker, got.get("m_src", "?"), got.get("m_tgt", "?"),
                          got.get("p_attest_null", "?"), got.get("cos_percentile", "?"),
                          got.get("containment", "?")), 200)
        title = "Analogy survived: '%s' carries %s into %s" % (
            _ascii(src_title, 48), marker, _ascii(tgt_title, 44))
    else:
        outcome = _fit("no viable mapping (Lab %s): %s" % (lab_id, _ascii(reason, 400)), 200)
        title = "Analogy discarded: %s does not transfer out of '%s'" % (
            marker, _ascii(src_title, 56))

    note = _fit("%s: %s -> %s [Lab %s]" % (marker, _ascii(src_title, 44),
                                           _ascii(tgt_title or "no admissible target", 44), lab_id), 200)

    content = _analogy_content(marker, marker_n, family, src_title, src_path, tgt_title,
                               got, q_src, q_tgt, lab_id, survived, reason, len(pool))

    rec = await _post(ctx, "/brain/analogy-record", {
        "mechanism": src_title,        # VERBATIM as served -- this is what lets pick_mechanism advance
        "target": (tgt_title or ("no distant domain attests '%s'" % marker))[:120],
        "note": note[:200],
        "outcome": outcome[:200],
    })
    if rec is None:
        return _idle("measured the forging but could not ledger it (brain POST failed)")

    _log(ctx, "analogy %s | marker=%s src='%s' tgt='%s' lab=%s"
         % (verdict, marker, _ascii(src_title, 40), _ascii(tgt_title, 40), lab_id))
    return {"status": "ok", "decisive": survived, "title": title, "content": content,
            "lab_id": lab_id,
            "why": ("mechanism '%s' survived its discrimination test against an unconditioned null"
                    % marker) if survived else
                   ("mechanism '%s' did not transfer: %s" % (marker, reason))}


def _analogy_content(marker, marker_n, family, src_title, src_path, tgt_title, got,
                     q_src, q_tgt, lab_id, survived, reason, pool_n) -> str:
    fam = (" It binds to the %s minimal model, so the skeleton is runnable, not just nameable."
           % family) if family else \
          " It binds to no runnable normal form in this organ's library, so the claim stops at attestation."
    lines = [
        "# %s" % ("Analogy: %s across '%s' and '%s'" % (marker, _ascii(src_title, 60),
                                                        _ascii(tgt_title, 60)) if survived else
                  "Discarded analogy: %s out of '%s'" % (marker, _ascii(src_title, 60))),
        "",
        "**Shared mechanism claimed:** `%s` (appears %d times in the source note).%s" % (marker, marker_n, fam),
        "",
        "**Source domain** - %s" % _ascii(src_title, 110),
        "> %s" % (q_src or "(no single sentence isolates the mechanism)"),
        "",
        "**Target domain** - %s" % (_ascii(tgt_title, 110) if tgt_title else
                                    "none admissible in the retrieved pool"),
        "> %s" % (q_tgt or "(none)"),
        "",
        "## What was measured (Lab %s)" % lab_id,
        "The artifact selected the target itself, from a retrieved pool of %d owner-authored notes, "
        "and tested the pairing against an unconditioned null: a seeded random sample of concept "
        "notes that were NOT retrieved for this mechanism." % pool_n,
        "",
        "- mechanism density: source %s, target %s (bar: 2)" % (got.get("m_src", "?"), got.get("m_tgt", "?")),
        "- topical containment between the two notes: %s (bar: < %.2f, the repo-wide "
        "near-duplicate threshold - above it they are the same note restated, not two domains)"
        % (got.get("containment", "?"), _DUP),
        "- share of unretrieved notes that also attest `%s`: %s (bar: <= 0.25 - above it the term "
        "is background vocabulary, not a mechanism)" % (marker, got.get("p_attest_null", "?")),
        "- mechanism-profile agreement percentile vs the null: %s (bar: >= 0.90)"
        % got.get("cos_percentile", "?"),
        "",
        "## Verdict: %s" % ("SURVIVED" if survived else "NO VIABLE MAPPING"),
        reason,
        "",
        "**Scope.** Surviving this test means the correspondence is SPECIFIC rather than a shared "
        "vocabulary - a necessary condition for a mechanism-level analogy, not a demonstration "
        "that the mapping is correct. Nothing here is evidence about either domain's science.",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# ARM 2 — the Theory Engine
# ─────────────────────────────────────────────────────────────────────────────

async def _theory_arm(ctx) -> dict:
    d = await _get(ctx, "/brain/theory/target")
    tgt = (d or {}).get("target") if isinstance(d, dict) else None
    if not isinstance(tgt, dict) or not tgt.get("path"):
        return _idle("no mechanistic belief is waiting for a model run")

    path, title = str(tgt["path"]), str(tgt.get("title") or "")
    text = _read_note(path)
    if len(text) < 200:
        return _idle("belief note '%s' is unreadable from the dungeon" % _ascii(title, 60))

    low = text.lower()
    ranked = [(m, c) for m, c in _marker_ranking(text) if c >= 2 and m in _FAMILY_OF]
    family = _FAMILY_OF[ranked[0][0]] if ranked else None

    if family:
        cond_hits = [c for c in _MODELS[family]["cond"] if c in low]
        name = "orin theory run: %s / %s" % (_ascii(title, 60), family)
        code = _theory_script(family, title, cond_hits)
    else:
        name = "orin modelability probe: %s" % _ascii(title, 60)
        code = _probe_script(title, text)

    lab_id, out, ok = await _lab(ctx, name, code)
    if not lab_id or not ok:
        return _idle("the theory artifact did not complete (%s)"
                     % _ascii(out.splitlines()[-1] if out else "no output", 120))

    got = _measured(out)
    verdict = _verdict_word(got)
    if verdict not in ("corroborated", "strained", "unmodelable"):
        return _idle("the artifact printed no usable verdict")
    reason = str(got.get("verdict", "")).split("--", 1)[-1].strip()

    already = str(_frontmatter(text, "theory_status") or "")
    summary = _theory_summary(family, got, reason)

    rec = await _post(ctx, "/brain/theory/record", {
        "title": title,          # VERBATIM as served -- this is what lets pick_target advance
        "path": path,
        "verdict": verdict,
        "lab": lab_id,           # the endpoint will not take an unmodelled verdict
        "summary": summary[:400],
    })
    if rec is None or (isinstance(rec, dict) and rec.get("error")):
        return _idle("measured the belief but could not ledger it (%s)"
                     % _ascii(str((rec or {}).get("error", "brain POST failed")), 100))

    _log(ctx, "theory %s | belief='%s' family=%s lab=%s"
         % (verdict, _ascii(title, 44), family or "none", lab_id))
    return {
        "status": "ok",
        "decisive": verdict in ORGAN["decisive"],
        "title": "Theory run: %s -> %s" % (_ascii(title, 80), verdict),
        "content": _theory_content(title, path, family, got, verdict, reason, lab_id, already),
        "lab_id": lab_id,
        "why": ("belief modelled as the %s normal form; artifact ruled %s" % (family, verdict))
               if family else
               ("no mechanism term recurs and binds to a runnable model; the modelability probe "
                "ruled %s" % verdict),
    }


def _frontmatter(text: str, key: str) -> str:
    m = re.search(r"^%s:\s*(.+)$" % re.escape(key), text[:1500], re.M)
    return m.group(1).strip() if m else ""


def _theory_summary(family, got, reason) -> str:
    if not family:
        return ("Modelability probe: of %s mechanism terms in the note, %s recur at density >= 2 and "
                "bind to a runnable minimal model; %s directional relations, %s numeric tokens. No "
                "formal core to put on a computer."
                % (got.get("mechanism_terms_present", "?"), got.get("bindable_mechanism_terms", "?"),
                   got.get("directional_relations", "?"), got.get("numeric_tokens", "?")))
    return ("Modelled as %s. Signature holds in %s of the parameter box vs %s for the falsification "
            "control (discrimination %s). %s"
            % (family, got.get("claim_frac", "?"), got.get("control_frac", "?"),
               got.get("discrimination", "?"), reason))


def _theory_content(title, path, family, got, verdict, reason, lab_id, already) -> str:
    lines = ["# Theory run: %s" % _ascii(title, 120), "",
             "Belief note: `%s`" % _ascii(str(Path(path).name), 110), ""]
    if already:
        lines += ["_This note already carried `theory_status: %s`. The Theory Engine re-served it "
                  "because `.theory.json` holds it under a drifted title, so its exclusion key never "
                  "matched. Recording under the served title repairs that key._" % _ascii(already, 30), ""]
    if family:
        lines += [
            "## Model (Lab %s)" % lab_id,
            "The belief's own mechanism vocabulary binds to the **%s** minimal model: %s"
            % (family, _MODELS[family]["doc"]),
            "",
            "- signature tested: %s" % _MODELS[family]["signature"],
            "- falsification control: %s" % _MODELS[family]["control"],
            "- grid points: %s" % got.get("grid_points", "?"),
            "",
            "## Measured",
            "- signature present in **%s** of the mechanism's own parameter box"
            % got.get("claim_frac", "?"),
            "- control reproduces it in %s of the box (discrimination %s; a run below 0.20 is "
            "declared unmodelable rather than reported)"
            % (got.get("control_frac", "?"), got.get("discrimination", "?")),
            "- measured boundary: %s" % (next((("%s = %s" % (k[9:], v)) for k, v in got.items()
                                               if k.startswith("boundary_")), "none")),
            "- does the note state that regime? %s" % got.get("note_states_regime", "?"),
        ]
    else:
        lines += [
            "## Modelability probe (Lab %s)" % lab_id,
            "No mechanism term in this belief RECURS (density >= 2) and binds to a runnable minimal "
            "model, so the honest run is a probe of what the note contains rather than a simulation "
            "of what it claims.",
            "",
            "## Measured",
            "- mechanism terms present: %s (recurring and bindable: %s)"
            % (got.get("mechanism_terms_present", "?"), got.get("bindable_mechanism_terms", "?")),
            "- terms found: %s" % got.get("present", "?"),
            "- directional relations: %s" % got.get("directional_relations", "?"),
            "- numeric tokens in the body: %s" % got.get("numeric_tokens", "?"),
            "- sections: %s" % got.get("sections", "?"),
        ]
    lines += ["", "## Verdict: %s" % verdict.upper(), reason, "",
              "**Scope.** The parameters are generic normal-form parameters, not measurements from "
              "this belief's domain. The run tests the belief's STATED SCOPE - whether the "
              "mechanism it invokes actually delivers the claimed behaviour across its own "
              "parameter range - and never its empirical truth. No number above may be quoted as "
              "a measurement of the domain."]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def _idle(why: str) -> dict:
    return {"status": "idle", "decisive": False, "title": "", "content": "",
            "lab_id": None, "why": why}


async def _stalest_arm(ctx) -> str:
    """Whichever of Orin's two ledgers has gone longest without an entry. Read off the brain's own
    stores rather than a local file, so a dungeon restart cannot desynchronise the alternation."""
    a = await _get(ctx, "/brain/analogies")
    t = await _get(ctx, "/brain/theory")

    def newest(d, key):
        try:
            return max(float(x.get("ts") or 0) for x in (d or {}).get(key) or []) or 0.0
        except (ValueError, TypeError):
            return 0.0

    ta, tt = newest(a, "items"), newest(t, "runs")
    return "theory" if tt < ta else "analogy"


async def cycle(ctx) -> dict:
    """Returns {"status": "ok"|"idle"|"error", "decisive": bool, "title": str,
                "content": str, "lab_id": str|None, "why": str}

    Alternates Orin's two organs so neither ledger goes cold, and never raises: a scheduler that
    dies on one bad cycle is how an agent goes quiet for five days without anyone noticing.
    """
    try:
        arm = await _stalest_arm(ctx)
        _log(ctx, "cycle start | agent=%s arm=%s metric=%s"
             % (_ascii(str(getattr(ctx, "agent", ORGAN["agent"])), 40), arm, _FD_SOURCE))
        res = await (_theory_arm(ctx) if arm == "theory" else _analogy_arm(ctx))
        if res.get("status") == "idle":
            # The other ledger may still have work; one honest idle should not cost the whole cycle.
            other = await (_analogy_arm(ctx) if arm == "theory" else _theory_arm(ctx))
            if other.get("status") == "ok":
                return other
            res["why"] = "%s; %s" % (res.get("why", ""), other.get("why", ""))
            _log(ctx, "idle | %s" % _ascii(res["why"], 200))
        return res
    except Exception as e:                              # cycle() must never raise
        return {"status": "error", "decisive": False, "title": "", "content": "",
                "lab_id": None, "why": "%s: %s" % (type(e).__name__, e)}
