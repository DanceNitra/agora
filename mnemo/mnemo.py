"""
mnemo — a memory layer for AI agents.  (brand: Mnemosyne)

The memory that runs an autonomous research OS over ~5,800 notes, distilled to a single file with
no required dependencies. It does the four things agent memory actually needs, the way that held up
in production:

  remember(text)      append-only raw capture, stamped with an ABSOLUTE time (never rewritten)
  recall(query, k)    value-ranked retrieval: relevance × the memory's accrued value, not just
                      cosine similarity — the high-value memories surface first
  consolidate(cap)    the "dream" pass: value-rank under a keep-budget, link near-duplicates, mark
                      stale/superseded — it only ADDS a derived layer, it never edits the raw note
  contradictions()    flag mutually-incompatible memories for REVIEW (never auto-delete)

Design rules that are not optional (each one cost us to learn):
  • Raw capture is immutable. Consolidation adds links/markers; it never overwrites the source —
    that is what stops the slow accuracy drift of LLM-rewritten memory.
  • Absolute timestamps at write time. Relative/derived times rot the moment they're consolidated.
  • Value-ranked, capacity-aware consolidation. The payoff from ranking *what to keep* scales
    super-linearly as the budget shrinks (measured), so retention tracks value, not recency — and
    NOT access-frequency: decaying on reads keeps *popular* memories, but popularity != value, so a
    pure access-reset policy starves the rarely-read-but-load-bearing fact (measured: it retains
    ~3x less total value than a value blend under a tight budget). Forgetting blends value + recency.
  • Report value at the COHORT level (tag / time-block), never per-memory: per-item value at n-of-1
    is statistical noise; cohorts are where the signal lives.
  • Contradictions are flagged for review, not auto-resolved. Silent rewrites destroy trust.

Bring your own embedder for semantic recall (any text->vector fn); with none, mnemo falls back to a
lexical token overlap so it runs anywhere, today.

    from mnemo import Mnemo
    m = Mnemo("memory.json")                 # or Mnemo("memory.json", embed=my_embedder)
    m.remember("Pre-trend tests catch only ~31% of fatal DiD bias.", tags=["causal"], value=3)
    m.recall("difference in differences", k=5)
    m.consolidate(keep=200)
    m.contradictions()

MIT-licensed. Part of Agora (https://github.com/DanceNitra/agora).
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import uuid
from pathlib import Path

try:                                  # OPTIONAL: numpy only ACCELERATES semantic recall at scale.
    import numpy as _np               # mnemo still runs (pure-Python cosine) with no numpy installed.
except Exception:
    _np = None

__version__ = "0.1.0"
_WORD = re.compile(r"[a-z0-9][a-z0-9\-']{2,}")
_STOP = frozenset("the a an of for to in on and or is are was were be been with this that it its as "
                  "by at from into our we us you your he she they them his her their not no".split())


def _stem(w: str) -> str:
    return w[:-1] if (w.endswith("s") and len(w) > 4) else w   # crude plural/3rd-person fold


def _tokens(text: str) -> set:
    return {_stem(w) for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class Mnemo:
    def __init__(self, path: str | None = None, embed=None):
        """path: optional JSON file to persist to. embed: optional fn(str)->list[float] for semantic
        recall; if omitted, recall uses lexical token overlap (zero dependencies)."""
        self.path = Path(path) if path else None
        self.embed = embed
        self.items: list[dict] = []
        self._tok_cache: dict[str, set] = {}     # id -> token set, so recall doesn't re-tokenize
        # recall auto-mode: below this many active memories lexical is as good and free; above it the
        # embedder pays (measured crossover ~300-600 notes; semantic then wins 3.6-5x). Tunable.
        self.semantic_threshold = 300
        self._last_mode = "lexical"              # which mode the most recent recall() actually used
        self._mat = None                         # cached L2-normalized matrix of memory vectors (numpy)
        self._vec_rowof: dict[str, int] = {}     # memory id -> its row in self._mat
        self._mat_built_n = -1                   # item count when the matrix was built (rebuild on change)
        # _save() THROTTLE: serializing the whole store (json.dumps of every item) is O(store size); doing
        # it on EVERY recall/remember froze callers once the store grew (recall mutates access value, so it
        # used to re-serialize everything each call). Coalesce disk writes to at most once / _save_min_s;
        # at most _save_min_s of access-metadata is lost on a hard crash (working memory — acceptable).
        self._save_min_s = 5.0
        self._last_save = 0.0
        self._dirty = False
        if self.path and self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.items = []

    # ── capture ──────────────────────────────────────────────────────────────
    def remember(self, text: str, tags=None, value: float = 1.0, meta: dict | None = None,
                 mtype: str | None = None, valid_from: float | None = None,
                 source: dict | None = None) -> str:
        """Append-only raw capture. Stamped with an absolute UTC time; never edited afterward.
        mtype in {episodic, semantic, procedural} sets the decay prior (episodic fades fast,
        semantic slow, procedural barely); inferred from the text if not given. Pass it explicitly
        when the caller knows the kind — inference defaults to episodic (the conservative, fast-decay
        choice) and only promotes on clear markers."""
        mid = uuid.uuid4().hex[:10]
        now = time.time()
        rec = {"id": mid, "text": text, "tags": list(tags or []), "value": float(value),
               "ts": now, "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "valid_from": float(valid_from) if valid_from is not None else now,  # event-time (bi-temporal); defaults to ingest-time
               "source": dict(source) if source else None,   # re-checkable origin (e.g. {"doc": id, "span": [start, end]}) so a recalled fact can be traced back, not trusted blind
               "mtype": mtype or _infer_type(text), "last_access": now,
               "status": "active", "links": [], "meta": dict(meta or {})}
        if self.embed:
            try:
                rec["vec"] = list(self.embed(text))
            except Exception:
                rec["vec"] = None
        self.items.append(rec)
        self._save(force=True)        # a new memory is real content - persist immediately, not throttled
        return mid

    def remember_dedup(self, text: str, tags=None, value: float = 1.0, meta: dict | None = None,
                       mtype: str | None = None, dup_threshold: float = 0.95) -> str:
        """OPT-IN write that skips redundant appends. If an active memory is near-identical (similarity >=
        dup_threshold) AND carries the SAME value(s) (no numeric clash), this returns that memory's id WITHOUT
        appending a duplicate raw row -- cutting raw-store bloat from repeated identical writes. A near-identical
        text with a DIFFERENT number (a value UPDATE) is NOT a duplicate: it appends, so the consolidation pass can
        supersede the stale value. Default `remember()` stays strictly append-only (the 'zero rewrites' contract);
        this is a separate opt-in path for high-duplicate ingest."""
        hits = self.recall(text, k=1)
        if hits:
            h = hits[0]
            s = self._similarity(text, h, self._qvec(text) if self.embed else None)
            if s >= dup_threshold and not _value_clash(text, h["text"]):
                return h["id"]            # NO-OP: near-identical, same value -> skip the redundant append
        return self.remember(text, tags=tags, value=value, meta=meta, mtype=mtype)

    # ── retrieval (value-ranked) ──────────────────────────────────────────────
    def _qvec(self, query: str):
        """Embed a query ONCE per scan, or None (no embedder / failure). Callers pass the result
        into _similarity so a recall over N memories costs 1 embedding, not N."""
        if not self.embed:
            return None
        try:
            return self.embed(query)
        except Exception:
            return None

    def _vec_matrix(self):
        """Cached L2-normalized matrix (numpy) of every memory that carries a vec — so a semantic
        recall is ONE matmul, not an O(N·d) pure-Python cosine loop. Rebuilt only when the item count
        changes (remember / bulk load); status changes (consolidate) don't touch the vectors."""
        if _np is None:
            return None
        if self._mat is None or self._mat_built_n != len(self.items):
            rows, ids = [], []
            for r in self.items:
                if r.get("vec"):
                    rows.append(r["vec"]); ids.append(r["id"])
            if rows:
                M = _np.asarray(rows, dtype=_np.float32)
                M /= (_np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
                self._mat = M
                self._vec_rowof = {i: k for k, i in enumerate(ids)}
            else:
                self._mat, self._vec_rowof = None, {}
            self._mat_built_n = len(self.items)
        return self._mat

    def _rec_tokens(self, rec: dict) -> set:
        """Token set for a memory, cached by id — recall over N memories shouldn't re-tokenize."""
        rid = rec.get("id") or id(rec)
        t = self._tok_cache.get(rid)
        if t is None:
            t = _tokens(rec["text"]); self._tok_cache[rid] = t
        return t

    def _similarity(self, query: str, rec: dict, qvec=None, qtok: set | None = None) -> float:
        if qvec is not None and rec.get("vec"):
            return max(0.0, _cosine(qvec, rec["vec"]))
        q = qtok if qtok is not None else _tokens(query)
        t = self._rec_tokens(rec)
        if not q or not t:
            return 0.0
        return len(q & t) / min(len(q), len(t))     # overlap coefficient — forgiving without an embedder

    def recall(self, query: str, k: int = 6, include_superseded: bool = False,
               include_hubs: bool = False, mode: str = "auto", min_relevance: float = 0.0,
               scope: str | None = None, as_of: float | None = None) -> list[dict]:
        """Top-k memories by RELEVANCE × VALUE — high-value memories outrank merely-similar ones.
        Memories the dream pass flagged as hubs (universal matchers) are skipped unless include_hubs.

        mode: 'auto' (default) uses LEXICAL token overlap while the store is small (< semantic_threshold
        active memories) and SEMANTIC embedding recall once it grows past that — the measured crossover
        where the embedder starts to pay (3.6-5x recall at scale). Force with 'lexical' / 'semantic'.
        Semantic needs an embedder (set on the store); without one, or if embedding fails, recall
        falls back to lexical automatically."""
        def _eligible(r: dict) -> bool:
            s = r["status"]
            if as_of is not None:
                # Bi-temporal "as of T": a memory counts if it was VALID at time T — valid_from <= T and not yet
                # invalidated by T — INCLUDING records now superseded (they were current back then). Records
                # superseded by the pre-bitemporal pass carry no invalidated_at; treat them as still-valid here.
                vf = r.get("valid_from", r["ts"])
                inv = r.get("invalidated_at")
                if vf > as_of or (inv is not None and inv <= as_of):
                    return False
                return include_hubs if s == "hub" else True
            if s == "active":
                return True
            if s == "hub":
                return include_hubs
            return include_superseded            # superseded / other non-active
        pool = [r for r in self.items if _eligible(r)]
        # Scope/namespace isolation: when a scope is requested, recall ONLY sees memories tagged with that scope
        # (meta['scope']) BEFORE ranking — a shared store (e.g. many agents / tenants in one Mnemo) cannot bleed
        # one scope's memories into another's recall. scope=None (default) sees everything (legacy behavior).
        if scope is not None:
            pool = [r for r in pool if (r.get("meta") or {}).get("scope") == scope]
        use_semantic = self.embed is not None and (
            mode == "semantic" or (mode == "auto" and len(pool) >= self.semantic_threshold))
        qvec = self._qvec(query) if use_semantic else None    # None -> lexical (also if embed fails)
        self._last_mode = "semantic" if qvec is not None else "lexical"
        qtok = _tokens(query)                                 # tokenize the query once (lexical + fallback)
        # Vectorized semantic fast-path: one matmul gives the cosine to every vec-bearing memory.
        sims_vec = None
        if qvec is not None and _np is not None:
            M = self._vec_matrix()
            if M is not None:
                qv = _np.asarray(qvec, dtype=_np.float32)
                sims_vec = M @ (qv / (float(_np.linalg.norm(qv)) or 1.0))
        cands = []                                        # (sim, prov, eff_value, r) for sim>0 candidates
        _now = time.time()                                # for per-type decay of the ranking value
        _by_id = {x["id"]: x for x in self.items}         # for provenance lookups (source-episode status)
        for r in pool:
            if sims_vec is not None and r.get("vec") and r["id"] in self._vec_rowof:
                sim = max(0.0, float(sims_vec[self._vec_rowof[r["id"]]]))
            else:                                             # pure-Python cosine, or lexical fallback
                sim = self._similarity(query, r, qvec, qtok)
            # Relevance-floor ABSTENTION: drop candidates below an absolute similarity floor; if the WHOLE
            # top-k falls below it, recall() returns [] ("not in memory") instead of padding context with a weak
            # false match. min_relevance=0.0 (default) keeps legacy behavior (only sim<=0 is dropped).
            if sim <= 0 or sim < min_relevance:
                continue
            # Provenance gate: a memory that absorbed near-duplicates (links) is STALE-DERIVED if any of
            # those sources was later CONTRADICTED (state-toggle supersession) — the merged summary
            # outlived a fact it summarized. Demote it (don't drop — flag for re-consolidation), so a
            # consolidated claim can't quietly outrank the fresh memory that overturned its source.
            stale = bool(r.get("links")) and any(
                (_by_id.get(lid, {}).get("meta") or {}).get("superseded_by_toggle") for lid in r["links"])
            prov = 0.5 if stale else 1.0
            r["_stale_derived"] = stale                   # surfaced in the returned record
            cands.append((sim, prov, self._effective_value(r, _now), r))
        # Calibration WAS-IT-RIGHT: a per-memory Beta(good,bad) posterior nudges the score by track record.
        # cal_mode controls how the outcome-credit channel is allowed to act (our measured signal-reliability
        # law: a selection signal only beats relevance once reliability p > the no-signal floor 1/(1+D)):
        #   'full'  (default) — cal in [0.5, 1.5] (legacy: can promote AND demote).
        #   'boost' — cal in [1.0, 1.5]: outcome-credit can PROMOTE a proven memory but never DEMOTE one below
        #             its relevance, so a wrong/random credit cannot suppress a correct memory (kills backfire).
        #   'gated' — disable cal (->1.0) for this recall when the pooled signal looks weaker than 1/(1+D).
        mode = getattr(self, "cal_mode", "full")
        gate_off = False
        if mode == "gated" and cands:
            top = max(c[0] for c in cands)
            near = [c for c in cands if c[0] >= top * 0.95]      # candidates relevance can't separate
            D = len(near)
            if D >= 2:
                g = sum(float(c[3].get("good", 0) or 0) for c in near)
                b = sum(float(c[3].get("bad", 0) or 0) for c in near)
                if (g + 1.0) / (g + b + 2.0) <= 1.0 / (1.0 + D):
                    gate_off = True
        scored = []
        for sim, prov, evalue, r in cands:
            if gate_off:
                cal = 1.0
            else:
                cal = 0.5 + self._reliability(r)
                if mode == "boost" and cal < 1.0:
                    cal = 1.0
            score = sim * (1.0 + math.log1p(max(0.0, evalue))) * prov * cal
            scored.append((score, sim, r))
        scored.sort(key=lambda x: -x[0])
        out = []
        _top_sim = scored[0][1] if scored else 1.0   # normalize reinforcement by this query's best match
        for score, sim, r in scored[:k]:
            # Relevance-weighted reinforcement: a strong, on-target hit reinforces value MORE than a
            # marginal one that merely squeaked into the top-k. A flat +bump lets a memory that is a
            # weak false-positive for many queries become 'immortal' — the popular-but-irrelevant
            # failure mode. Weighting by this recall's relevance (normalized to the query's best hit)
            # ties reinforcement to how well the memory actually answered. (Independently converged on
            # in production by the Dakera and mem0 teams: weight access events by recall score, not raw
            # count.)
            rel = (sim / _top_sim) if _top_sim > 0 else 1.0
            r["value"] += 0.25 * rel
            r["last_access"] = _now                 # ...and resets the per-type decay clock
            # Type GRADUATION: an episodic memory recalled into high accrued value has proven durable,
            # so promote it to semantic — it stops fading on the fast 7-day episodic clock and decays
            # on the slow semantic one instead. (Dakera's access-driven episodic->semantic promotion,
            # gated on accrued VALUE rather than raw access count, so a popular-but-trivial memory
            # doesn't graduate.)
            # POISON guard: durability must be EARNED by corroboration, not mere recall-frequency. The value bump
            # above is correctness-blind, so a confabulation recalled enough would otherwise graduate to the durable
            # (slow-decay) tier and entrench itself. Require a corroboration signal — a re-checkable origin
            # (provenance), a positive OUTCOME (good>0), or an independent corroborating duplicate (links) — before
            # promoting. An uncorroborated popular memory stays episodic and fades on the fast clock unless earned.
            corroborated = bool(r.get("source")) or float(r.get("good", 0) or 0) > 0 or bool(r.get("links"))
            if r.get("mtype") == "episodic" and r["value"] >= _GRADUATE_VALUE and corroborated:
                r["mtype"] = "semantic"
                r.setdefault("meta", {})["graduated_from_episodic"] = True
            out.append({"id": r["id"], "text": r["text"], "tags": r["tags"], "iso": r["iso"],
                        "value": round(r["value"], 2), "relevance": round(sim, 3),
                        "score": round(score, 3), "links": r["links"],
                        "reliability": round(self._reliability(r), 3),
                        "source": r.get("source"),    # re-checkable origin (provenance), surfaced so a recalled fact can be traced back
                        "stale_derived": bool(r.get("_stale_derived"))})
        # NOTE: recall is a READ. It nudges in-memory access value / graduation, but must NOT persist the
        # whole store here — serializing (json.dumps) on every recall, across many agents' stores,
        # saturated the thread pool and FROZE the world. The in-memory nudges are persisted on the next
        # remember()/consolidate()/flush(); losing recent access metadata on a hard crash is harmless.
        if out:
            self._dirty = True   # mark for the next throttled/forced save; do NOT serialize on the read path
        return out

    @staticmethod
    def _reliability(r: dict) -> float:
        """Per-memory track record as a Beta(1+good, 1+bad) posterior MEAN: 0.5 with no outcomes yet,
        ->1 if recalls into it kept resolving WELL, ->0 if they kept resolving badly. Counts only grow."""
        g = float(r.get("good", 0) or 0)
        b = float(r.get("bad", 0) or 0)
        return (g + 1.0) / (g + b + 2.0)

    def credit(self, ids, outcome, weight: float = 1.0) -> dict:
        """Close the accuracy loop onto the substrate. When the work a set of memories was recalled into
        gets a real verdict (a forecast resolves, a replication is ruled REPRODUCED/FAILED, a hypothesis is
        severe-tested), call credit(recalled_ids, outcome): each memory's Beta(good,bad) track record is
        nudged so future recall ranks by WAS-IT-RIGHT, not merely was-it-recalled. Append-only to the
        counts; never edits raw text. `outcome` may be a bool, a sign (>0 good), or a verdict string
        (good/right/correct/reproduced/hit vs bad/wrong/failed/miss)."""
        if isinstance(outcome, bool):
            good = outcome
        elif isinstance(outcome, (int, float)):
            good = outcome > 0
        else:
            s = str(outcome).strip().lower()
            good = s in ("good", "right", "correct", "reproduced", "hit", "true", "win", "+")
        by_id = {x["id"]: x for x in self.items}
        key, updated = ("good" if good else "bad"), []
        for i in (ids or []):
            rec = by_id.get(i)
            if rec is None:
                continue
            rec[key] = float(rec.get(key, 0) or 0) + float(weight)
            updated.append(i)
        if updated:
            self._save()
        return {"updated": updated, "outcome": key, "weight": weight}

    def _effective_value(self, r: dict, now: float) -> float:
        """Recall weight = stored value decayed by time since last access, at the memory's TYPE
        half-life (episodic fades fast, semantic slow, procedural barely). Access resets the clock,
        so memories that keep being useful stay alive while stored-but-never-recalled ones fade.
        Reversible: raw value/text are untouched; only the effective ranking weight decays."""
        hl = _HALFLIFE_S.get(r.get("mtype", "episodic"), _HALFLIFE_S["episodic"])
        age = max(0.0, now - r.get("last_access", r.get("ts", now)))
        return r["value"] * (0.5 ** (age / hl))

    # ── consolidation (the "dream" pass) ──────────────────────────────────────
    def _common_vocab(self, active: list[dict], min_df_frac: float = 0.002):
        """Token sets per memory + the corpus's COMMON vocabulary (tokens shared by enough
        memories to be real content, not one-off noise). Cheap, O(total tokens)."""
        from collections import Counter
        df: Counter = Counter()
        toks = []
        for r in active:
            tk = _tokens(r["text"]); toks.append(tk); df.update(tk)
        min_df = max(3, int(min_df_frac * len(active)))
        common = {w for w, c in df.items() if c >= min_df}
        return toks, common

    def consolidate(self, keep: int | None = None, dup_threshold: float = 0.82,
                    hub_coverage: float = 0.12, link_duplicates: bool = True) -> dict:
        """The dream pass. ADDS a derived layer (status + links); never edits raw text. Three steps:

        1. HUB PASS — flag indiscriminate "universal-matcher" memories. Under lexical recall the
           similarity is the overlap coefficient |q∩t|/min(|q|,|t|), so a memory whose token set
           covers a large fraction of the corpus's common vocabulary scores ~1.0 against ALMOST ANY
           query and drowns the specific memory the user actually wanted (measured on a 6k-note
           vault: such hubs sat in the top-10 for ~47% of queries). We mark them `status:'hub'`
           (reversible; recall skips them unless include_hubs) — measured to lift recall@5 ~+22%.
        2. near-duplicate LINKING (dedup without delete) — EXCEPT a polarity clash, which is a
           STATE TOGGLE (preference flip): supersede the OLDER, since a contradiction is not a dup.
        3. keep-budget: mark the lowest-value surplus `superseded`.

        hub_coverage: a memory covering ≥ this fraction of the common vocabulary is a hub (0 disables).
        link_duplicates: the dup pass is O(n²); pass False to skip it on large stores."""
        active = [r for r in self.items if r["status"] == "active"]
        hubs = 0
        if hub_coverage and len(active) >= 50:
            toks, common = self._common_vocab(active)
            nv = len(common) or 1
            for r, tk in zip(active, toks):
                shared = len(tk & common)
                cov = shared / nv
                # A genuine 'universal matcher' overlaps MANY of the corpus's common words. Requiring an absolute
                # floor (>= 3 shared common words) on top of the coverage fraction prevents the low-diversity /
                # templated-store failure: when the common vocabulary is tiny (e.g. a handful of repeated attribute
                # words), a legitimate memory trivially covers >= hub_coverage of it with just ONE common word, which
                # would wrongly flag every memory a hub and SILENTLY EMPTY recall. (Measured: 3-5 shared attrs -> 100%
                # hub-flagged, 0% recall, before this floor.)
                if shared >= 3 and cov >= hub_coverage:
                    r["status"] = "hub"
                    r.setdefault("meta", {})["hub"] = True
                    r["meta"]["hub_coverage"] = round(cov, 3)
                    r["superseded_ts"] = time.time()
                    hubs += 1
            active = [r for r in active if r["status"] == "active"]
        active.sort(key=lambda r: -r["value"])
        linked = toggled = 0
        if link_duplicates:
            # Pairwise near-duplicate pass. A high-similarity pair is normally LINKED (dedup without
            # delete) — UNLESS it's a polarity clash (one negates the other), which is a STATE TOGGLE
            # (a preference flip / contradiction), not a duplicate. Then we supersede the OLDER memory
            # so recall returns the NEW state, instead of letting high vector similarity silently
            # merge a contradiction into one blob. (state-toggle guard.)
            for i, a in enumerate(active):
                if a["status"] != "active":          # superseded by an earlier toggle this pass
                    continue
                avec = self._qvec(a["text"])         # embed each anchor once, not once per partner
                for b in active[i + 1:]:
                    if b["status"] != "active" or b["id"] in a["links"]:
                        continue
                    if self._similarity(a["text"], b, avec) >= dup_threshold:
                        if _negation_clash(a["text"], b["text"]) or _value_clash(a["text"], b["text"]):
                            # Resolve by VALIDITY time (valid_from = when the fact is TRUE), not ingest order
                            # (ts = when it was stored). A fact learned LATE about an EARLIER state (e.g. a
                            # back-filled record) must NOT overwrite the genuinely-current one just because it
                            # arrived later. valid_from defaults to ts, so ingest-ordered streams are unchanged;
                            # only out-of-order arrivals (the bi-temporal case) flip vs the old ts rule.
                            _vf = lambda r: r.get("valid_from", r["ts"])
                            older, newer = (a, b) if _vf(a) <= _vf(b) else (b, a)
                            older["status"] = "superseded"
                            older["superseded_ts"] = time.time()
                            older["invalidated_at"] = _vf(newer)   # bi-temporal: when this record stopped being current
                            older.setdefault("meta", {})["superseded_by_toggle"] = newer["id"]
                            # Accuracy loop, live consumer: being OVERTURNED by a later contradiction is
                            # a was-wrong signal — debit the superseded claim, credit the one that
                            # corrected the record. So the consolidation pass continuously feeds each
                            # memory's reliability from real outcomes, not just external scoring.
                            older["bad"] = float(older.get("bad", 0) or 0) + 1.0
                            newer["good"] = float(newer.get("good", 0) or 0) + 1.0
                            toggled += 1
                            if older is a:
                                break                # this anchor is gone; advance to the next
                        else:
                            a["links"].append(b["id"]); linked += 1
        staled = 0
        if keep is not None and len(active) > keep:
            for r in active[keep:]:
                r["status"] = "superseded"; r["superseded_ts"] = time.time(); staled += 1
        self._save()
        return {"active": len([r for r in self.items if r["status"] == "active"]),
                "hubs_flagged": hubs, "linked_pairs": linked, "toggled": toggled,
                "staled": staled, "kept": keep, "total": len(self.items)}

    # ── cluster-triggered consolidation ───────────────────────────────────────
    def _cluster_active(self, sim_threshold: float = 0.5) -> list[list[dict]]:
        """Cheap greedy single-pass clustering of ACTIVE memories by similarity (O(n·#clusters)).
        Highest-value member is the cluster representative; each memory joins the most-similar
        cluster above the threshold, else starts its own. Lexical or semantic per the store's mode."""
        active = sorted([r for r in self.items if r["status"] == "active"], key=lambda r: -r["value"])
        cents: list[dict] = []
        for r in active:
            rvec = self._qvec(r["text"])
            best = None
            for c in cents:
                s = self._similarity(c["rec"]["text"], r, c["vec"])
                if s >= sim_threshold and (best is None or s > best[1]):
                    best = (c, s)
            if best:
                best[0]["members"].append(r)
            else:
                cents.append({"rec": r, "vec": rvec, "members": [r]})
        return [c["members"] for c in cents]

    def consolidate_clusters(self, threshold: int = 15, cluster_sim: float = 0.5,
                             dup_threshold: float = 0.82, keep_per_cluster: int | None = None) -> dict:
        """Cluster-TRIGGERED consolidation: consolidate a semantic cluster only once it has grown past
        `threshold` members — not a global nightly blanket. Avoids (1) prematurely consolidating sparse
        topics, where the raw episodes are still the best representation, and (2) unbounded growth in
        dense ones. Cheap to call often (no-op until a cluster is ripe). Runs dedup + the state-toggle
        guard (+ optional keep-budget) WITHIN each ripe cluster only."""
        clusters = self._cluster_active(cluster_sim)
        fired = linked = toggled = staled = 0
        for members in clusters:
            if len(members) < threshold:
                continue                              # sparse — leave the raw episodes alone
            fired += 1
            members.sort(key=lambda r: -r["value"])
            for i, a in enumerate(members):
                if a["status"] != "active":
                    continue
                avec = self._qvec(a["text"])
                for b in members[i + 1:]:
                    if b["status"] != "active" or b["id"] in a["links"]:
                        continue
                    if self._similarity(a["text"], b, avec) >= dup_threshold:
                        if _negation_clash(a["text"], b["text"]) or _value_clash(a["text"], b["text"]):
                            older, newer = (a, b) if a["ts"] <= b["ts"] else (b, a)
                            older["status"] = "superseded"; older["superseded_ts"] = time.time()
                            older.setdefault("meta", {})["superseded_by_toggle"] = newer["id"]
                            toggled += 1
                            if older is a:
                                break
                        else:
                            a["links"].append(b["id"]); linked += 1
            if keep_per_cluster is not None:
                act = sorted([r for r in members if r["status"] == "active"], key=lambda r: -r["value"])
                for r in act[keep_per_cluster:]:
                    r["status"] = "superseded"; r["superseded_ts"] = time.time(); staled += 1
        self._save()
        return {"clusters_total": len(clusters), "clusters_fired": fired, "threshold": threshold,
                "linked_pairs": linked, "toggled": toggled, "staled": staled}

    # ── contradiction surfacing (flag, never auto-delete) ─────────────────────
    def contradictions(self, sim_threshold: float = 0.5, incompatible=None) -> list[dict]:
        """Flag mutually-incompatible memories among RELATED ones (similarity-gated) for human review.
        `incompatible(a_text, b_text)->bool` defaults to a negation/polarity heuristic."""
        inc = incompatible or _negation_clash
        active = [r for r in self.items if r["status"] == "active"]
        flags = []
        for i, a in enumerate(active):
            avec = self._qvec(a["text"])             # embed each anchor once, not once per partner
            for b in active[i + 1:]:
                if self._similarity(a["text"], b, avec) >= sim_threshold and inc(a["text"], b["text"]):
                    flags.append({"a": a["id"], "b": b["id"],
                                  "a_text": a["text"][:120], "b_text": b["text"][:120]})
        return flags

    # ── value, reported at the COHORT level ───────────────────────────────────
    def value_by_cohort(self) -> dict:
        """Per-TAG value rollup. Deliberately not per-memory: at n-of-1, per-item value is noise;
        the cohort (tag / time-block) is where the signal is real."""
        out: dict[str, dict] = {}
        for r in self.items:
            if r["status"] != "active":
                continue
            for tag in (r["tags"] or ["(untagged)"]):
                c = out.setdefault(tag, {"count": 0, "value": 0.0})
                c["count"] += 1; c["value"] += r["value"]
        return {k: {"count": v["count"], "value": round(v["value"], 2),
                    "avg": round(v["value"] / v["count"], 2)} for k, v in out.items()}

    def _save(self, force: bool = False):
        if not self.path:
            return
        # Throttle: coalesce frequent writes (e.g. one per recall) so a large store isn't re-serialized
        # on the hot path. force=True (or flush()) bypasses it for shutdown/critical persistence.
        now = time.time()
        if not force and (now - self._last_save) < self._save_min_s:
            self._dirty = True
            return
        try:
            # Persist text/metadata only; the `vec` embedding arrays are a re-derivable in-memory CACHE
            # and are STRIPPED here. json.dumps of N x 768-dim float vectors is huge, slow, and holds the
            # GIL for many seconds - which froze the whole event loop even from a worker thread (the
            # frozen-world bug, 2026-06-20). Vectors stay in self.items (RAM) so recall is unaffected this
            # session; on reload they are re-embedded lazily. Keeps the store file small + the save fast.
            slim = [{k: v for k, v in r.items() if k != "vec"} for r in self.items]
            # Atomic write: a partial/interleaved write can't corrupt the store (crash- and
            # concurrent-writer-safe — last writer wins, never a torn JSON file).
            data = json.dumps(slim, ensure_ascii=False, indent=1)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(data, encoding="utf-8")
            os.replace(tmp, self.path)
            self._last_save = now
            self._dirty = False
        except Exception:
            pass

    def flush(self):
        """Force-persist any pending throttled changes (call on clean shutdown)."""
        if self._dirty:
            self._save(force=True)


# ── per-type decay priors (the half-life a memory's ranking value decays at, by kind) ──────────
# episodic = events (fade fast); semantic = durable facts (fade slow); procedural = rules/prefs
# (barely fade). Access resets the decay clock (see Mnemo._effective_value). Tunable.
_HALFLIFE_S = {"episodic": 7 * 86400, "semantic": 180 * 86400, "procedural": 3650 * 86400}
# accrued value at which a repeatedly-recalled EPISODIC memory graduates to semantic (≈16 strong
# recalls from the 1.0 floor); proven-durable, so it should decay on the slow clock, not the fast one.
_GRADUATE_VALUE = 5.0
_PROCEDURAL_RE = re.compile(r"\b(always|never|prefers?|rule|workflow|convention|policy|habit|"
                            r"setting|must|should|avoid|don't|do not)\b", re.I)
_SEMANTIC_RE = re.compile(r"\b(means|defined|definition|theorem|law of|equals|consists? of|"
                          r"is a |is an |is the |refers to)\b", re.I)


def _infer_type(text: str) -> str:
    """Conservative type inference: default EPISODIC (fast decay) and only promote on clear markers.
    Callers that know the kind should pass mtype explicitly."""
    t = text or ""
    if _PROCEDURAL_RE.search(t):
        return "procedural"
    if _SEMANTIC_RE.search(t):
        return "semantic"
    return "episodic"


def _negation_clash(a: str, b: str) -> bool:
    """Cheap default: two highly-related statements where exactly one negates. Replace with an
    LLM judge for production — but gate it behind similarity first to keep it O(neighbourhood)."""
    neg = re.compile(r"\b(not|no|never|cannot|can't|doesn't|isn't|won't|fails?|false)\b", re.I)
    return bool(neg.search(a)) != bool(neg.search(b))


_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _value_clash(a: str, b: str) -> bool:
    """A VALUE UPDATE: two already-near-duplicate statements that are identical EXCEPT for a differing
    numeric value ('retry limit is 5' -> '... is 12'). This is a state toggle (the fact's value changed),
    NOT a duplicate — so the older should be superseded, not merged. Gated behind the caller's similarity
    check; the tight 'non-numeric remainder is identical' condition keeps genuinely-distinct facts safe."""
    # A value UPDATE keeps the same numbers in the same ORDER except ONE position whose value changed
    # ('timeout is 5' -> 'is 12'; '5 of 10' -> '7 of 10'). Compare numbers POSITIONALLY, not as sets: a
    # set view is ambiguous for ENUMERATED facts because an index can equal another row's value
    # ('step 1 takes 5 min' vs 'step 5 takes 13 min' share the literal 5), which set-math reads as a
    # single change and would silently supersede a coexisting record. (Measured: a 6-item enumerated store
    # lost 5/6 facts under the set rule; 0/6 under this positional rule.)
    na, nb = _NUM.findall(a), _NUM.findall(b)             # ORDERED, not sets
    if not na or len(na) != len(nb):
        return False                                      # no numbers, or different count -> not a single update
    if sum(1 for x, y in zip(na, nb) if x != y) != 1:
        return False                                      # exactly one positional value changed
    # Compare the word-skeleton with ALL numbers stripped: _tokens keeps 3+ digit numbers as tokens
    # (_WORD requires length >= 3), so a multi-digit value ('...is 123') would otherwise spuriously make
    # the skeletons differ and miss the update. Strip numbers first, exactly as before this guard existed.
    return _tokens(_NUM.sub("", a)) == _tokens(_NUM.sub("", b))   # identical apart from the one value


if __name__ == "__main__":
    m = Mnemo()                                  # no path, no embedder — pure in-memory + lexical
    m.remember("SGD converges slowly due to gradient variance.", tags=["optimization"], value=3)
    m.remember("SGD does not converge slowly.", tags=["optimization"], value=1)
    m.remember("Pre-trend tests catch only 31% of fatal DiD bias.", tags=["causal"], value=2)
    print("recall 'SGD variance':", [r["text"][:46] for r in m.recall("SGD variance", k=3)])
    print("consolidate:", m.consolidate(keep=10))
    print("contradictions:", m.contradictions())       # flags the SGD pair (related + one negates)
    print("value_by_cohort:", m.value_by_cohort())
    print("(For semantic recall, pass embed=your_model to Mnemo(); lexical is the zero-dep fallback.)")
