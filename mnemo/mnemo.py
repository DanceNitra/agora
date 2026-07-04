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

import hashlib
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

try:                                  # OPTIONAL: only needed to SIGN write receipts (see receipts=...).
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey as _Ed25519SK, Ed25519PublicKey as _Ed25519PK)
    from cryptography.hazmat.primitives import serialization as _ser
    _HAVE_ED = True
except Exception:
    _HAVE_ED = False

_GENESIS = "0" * 64


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def new_receipt_keypair():
    """Return (private_key_hex, public_key_hex) for signing mnemo write receipts. Needs `cryptography`."""
    if not _HAVE_ED:
        raise RuntimeError("signing write receipts needs the `cryptography` package (pip install cryptography)")
    sk = _Ed25519SK.generate()
    return (sk.private_bytes(_ser.Encoding.Raw, _ser.PrivateFormat.Raw, _ser.NoEncryption()).hex(),
            sk.public_key().public_bytes(_ser.Encoding.Raw, _ser.PublicFormat.Raw).hex())

__version__ = "0.4.6"
_WORD = re.compile(r"[a-z0-9][a-z0-9\-']{2,}")
_STOP = frozenset("the a an of for to in on and or is are was were be been with this that it its as "
                  "by at from into our we us you your he she they them his her their not no".split())


def _stem(w: str) -> str:
    return w[:-1] if (w.endswith("s") and len(w) > 4) else w   # crude plural/3rd-person fold


def _tokens(text: str) -> set:
    return {_stem(w) for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def _token_counts(text: str) -> dict:
    """Term-frequency map with the SAME tokenization as _tokens (stem + stopword filter). BM25 needs TF;
    _tokens loses it by returning a set."""
    d: dict = {}
    for w in _WORD.findall((text or "").lower()):
        if w in _STOP:
            continue
        s = _stem(w)
        d[s] = d.get(s, 0) + 1
    return d


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class Mnemo:
    def __init__(self, path: str | None = None, embed=None, receipts: bool = False,
                 receipt_key: str | None = None, receipt_pubkey: str | None = None):
        """path: optional JSON file to persist to. embed: optional fn(str)->list[float] for semantic
        recall; if omitted, recall uses lexical token overlap (zero dependencies).

        receipts/receipt_key (OPT-IN, default OFF -> identical legacy behavior): when enabled, every
        remember() appends a tamper-evident, hash-chained WRITE RECEIPT committing to the memory's
        content hash, persisted to a sidecar "<path>.receipts.json" (the main store format is unchanged).
        verify_writes() then proves the write history wasn't altered out-of-band — something an
        append-only store alone can't, because anyone who can edit the store file can rewrite a stored
        memory and the store would serve the altered text as original. The hash chain is zero-dependency;
        pass receipt_key (+ receipt_pubkey) from new_receipt_keypair() to also Ed25519-SIGN each receipt
        so a third party can verify it with the public key only. (Standalone version: agora-agent-receipts.)"""
        self.path = Path(path) if path else None
        self.embed = embed
        self.items: list[dict] = []
        self._tok_cache: dict[str, set] = {}     # id -> token set, so recall doesn't re-tokenize
        self._tc_cache: dict[str, dict] = {}     # id -> term-frequency map, for the BM25 hybrid channel
        # recall auto-mode: below this many active memories lexical is as good and free; above it the
        # lexical+semantic HYBRID (RRF) pays — measured to beat either channel alone on agent memory. Tunable.
        self.semantic_threshold = 300
        self._last_mode = "lexical"              # which mode the most recent recall() actually used
        self._mat = None                         # cached L2-normalized matrix of memory vectors (numpy)
        self._vec_rowof: dict[str, int] = {}     # memory id -> its row in self._mat
        self._mat_built_n = -1                   # item count when the matrix was built (rebuild on change)
        self._vec_mean = None                    # corpus mean vector (for anisotropy centering of semantic recall)
        # Anisotropy centering: subtract the corpus mean before cosine. Many embedders (e.g. nomic) are
        # anisotropic — all cosines compress into a narrow band — so semantic recall under-separates.
        # MEASURED on real LoCoMo (419 turns): centering lifts single-hop full-evidence recall@k by
        # +0.04..+0.07 (k=5/10/20) and is neutral on multi-hop. Reversible: set center_embeddings=False.
        self.center_embeddings = True
        # Two-tier keep-budget: when consolidate(keep) must drop surplus, PROTECT the top protect_frac
        # of the budget by RAW value (recency-immune) and fill the REST by EFFECTIVE (decay-weighted)
        # value — so a freshly-useful memory isn't evicted by a stale high-value one. A pure top-N-by-raw
        # prune keeps old high-value items forever and starves a drifting working set. MEASURED on a
        # simulation of mnemo's own value-accrual + per-type decay: locality served-hit 0.22 -> 0.78,
        # neutral on rare-critical + poison-flood. Reversible: two_tier_keep=False -> legacy top-N-by-raw.
        self.two_tier_keep = True
        self.protect_frac = 0.30
        # Fast-novelty channel guard (OPT-IN, default OFF). mnemo's state-toggle supersedes a standing
        # fact the moment a single similar+contradicting memory arrives — correct + fast for a TRUSTED
        # single source (configs/preferences: latest assertion wins), but a single-shot poison flip
        # (AgentPoison / MINJA) can then override a true fact. With this ON, a contradiction supersedes
        # only when CORROBORATED (earned credit, or >=2 corroborating links) — the same bar as graduation;
        # an uncorroborated single contradiction is recorded as a link but does NOT supersede. This is the
        # two-channel capstone's latency-floor tradeoff made explicit: robustness to single-shot poison at
        # the cost of lagging an uncorroborated single legitimate change. Leave OFF for trusted-source
        # stores; turn ON for adversarial / multi-tenant ingestion.
        self.supersede_requires_corroboration = False
        # Persistence supersession (OPT-IN, default OFF; set to an int >= 2 to enable). A standing fact is
        # superseded only when the contradicting NEW state is asserted by >= this many INDEPENDENT records —
        # i.e. the change must PERSIST/accumulate, not arrive once. This is the sequential-change-detection
        # (CUSUM) escape applied to memory: an isolated single-shot poison flip never crosses the threshold
        # and is rejected, while a genuinely sustained value change is adopted once `supersede_persistence`
        # corroborating records exist. The integer IS the Adaptation-Corruption law's detection-latency floor
        # d* made explicit — set it to your stream's corruption-vs-change ratio. Unlike
        # supersede_requires_corroboration this needs NO external credit(): it adopts a genuine change purely
        # from repeated independent assertions, where the corroboration guard would lag one forever. MEASURED
        # (lab fea933, mnemo's real consolidate() path): isolated-poison false-supersede 1 -> 0 while a
        # 3-record sustained change is still adopted; it Pareto-dominates both the naive (poison-fooled) and
        # corroboration-only (change-lagging) rules — see the Adaptation-Corruption Separation Law (lab f490d8).
        # Reversible: 0 or 1 -> legacy fast supersession.
        self.supersede_persistence = 0
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
        # OPT-IN write receipts (default OFF -> zero behavior change; no sidecar created)
        self.receipts_enabled = bool(receipts or receipt_key)
        self._receipt_sk = receipt_key
        self.receipt_pubkey = receipt_pubkey
        self._receipts: list[dict] = []
        self._receipts_path = (self.path.parent / (self.path.name + ".receipts.json")) if self.path else None
        if self.receipts_enabled and self._receipts_path and self._receipts_path.exists():
            try:
                self._receipts = json.loads(self._receipts_path.read_text(encoding="utf-8"))
            except Exception:
                self._receipts = []

    # ── capture ──────────────────────────────────────────────────────────────
    def remember(self, text: str, tags=None, value: float = 1.0, meta: dict | None = None,
                 mtype: str | None = None, valid_from: float | None = None,
                 source: dict | None = None, key: str | None = None,
                 derived_from: list | None = None) -> str:
        """Append-only raw capture. Stamped with an absolute UTC time; never edited afterward.
        mtype in {episodic, semantic, procedural} sets the decay prior (episodic fades fast,
        semantic slow, procedural barely); inferred from the text if not given. Pass it explicitly
        when the caller knows the kind — inference defaults to episodic (the conservative, fast-decay
        choice) and only promotes on clear markers.

        `key` (OPT-IN) is a deterministic supersession key — typically a (subject, relation) identifier,
        e.g. "billing-api::auth-method". When set, remembering a new value RETIRES every active record
        sharing the same key (status -> superseded), with NO similarity threshold and NO LLM call. This
        closes the 'supersession blind spot': cosine similarity cannot tell a contradicted fact from its
        replacement (we measured AUROC ~0.61, near chance — a contradiction is often MORE embedding-similar
        to the original than a rephrase is), so a similarity-based store silently serves the stale value
        (~42% of the time in our test). A deterministic (subject, relation, object) ledger drives that to
        ~0%. Bi-temporal: a back-filled record (earlier valid_from) does NOT overwrite a genuinely newer
        same-key value — the stale-on-arrival record is the one retired."""
        mid = uuid.uuid4().hex[:10]
        now = time.time()
        rec = {"id": mid, "text": text, "tags": list(tags or []), "value": float(value),
               "ts": now, "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "valid_from": float(valid_from) if valid_from is not None else now,  # event-time (bi-temporal); defaults to ingest-time
               "source": dict(source) if source else None,   # re-checkable origin (e.g. {"doc": id, "span": [start, end]}) so a recalled fact can be traced back, not trusted blind
               "mtype": mtype or _infer_type(text), "last_access": now,
               "status": "active", "links": [], "meta": dict(meta or {})}
        # TAINT INHERITANCE (provenance that rides through transformation): when this memory is DERIVED from
        # others (a summary, a consolidation, an LLM rewrite), it inherits the union of its parents' canonical
        # sources — transitively, since a parent's own inherited taint is included. Without this, an app-side
        # summary is a fresh record with no source, so slash()/per-source attribution can't reach it: the
        # cumulative influence cap and the retroactive slash both need provenance to survive summarization to be
        # countable at all. `derived_from` is the substrate everything else (cap, slash) is deterrence math on.
        if derived_from:
            _by = {x["id"]: x for x in self.items}
            taint, links = set(), []
            for pid in derived_from:
                p = _by.get(pid)
                if p is None:
                    continue
                links.append(pid)
                taint |= Mnemo._rec_sources(p)     # parent's own source + its inherited taint (transitive)
            if taint:
                rec["taint"] = sorted(taint)
            if links:
                rec["links"] = links
        if key is not None:
            rec["key"] = str(key)
        if self.embed:
            try:
                rec["vec"] = list(self.embed(text))
            except Exception:
                rec["vec"] = None
        self.items.append(rec)
        if key is not None:
            self._supersede_by_key(rec)   # deterministic SRO supersession (no embedding, no threshold)
        self._save(force=True)        # a new memory is real content - persist immediately, not throttled
        if self.receipts_enabled:
            self._emit_write_receipt(rec)
        return mid

    # ── write receipts (OPT-IN: tamper-evident write history) ─────────────────
    def _write_commit(self, rec: dict) -> dict:
        """What a receipt commits to for a stored memory: its id + a hash of its content-bearing fields."""
        return {"id": rec["id"],
                "content_sha256": _sha256_hex(_canon({"text": rec.get("text"), "key": rec.get("key"),
                                                      "mtype": rec.get("mtype")}))}

    def _emit_write_receipt(self, rec: dict) -> dict:
        prev = self._receipts[-1]["hash"] if self._receipts else _GENESIS
        r = {"seq": len(self._receipts), "ts": rec.get("ts"), "memory_id": rec["id"],
             "commit": self._write_commit(rec), "prev": prev}
        r["hash"] = _sha256_hex(_canon({k: r[k] for k in ("seq", "ts", "memory_id", "commit", "prev")}))
        if self._receipt_sk and _HAVE_ED:
            sk = _Ed25519SK.from_private_bytes(bytes.fromhex(self._receipt_sk))
            r["pubkey"] = self.receipt_pubkey
            r["sig"] = sk.sign(bytes.fromhex(r["hash"])).hex()
        self._receipts.append(r)
        if self._receipts_path:
            try:
                self._receipts_path.write_text(json.dumps(self._receipts, indent=2, ensure_ascii=False),
                                               encoding="utf-8")
            except Exception:
                pass
        return r

    def verify_writes(self, expected_pubkey: str | None = None) -> tuple[bool, list[str]]:
        """Verify the write-receipt chain AND that each stored memory still matches its write receipt.
        Returns (ok, problems). Catches out-of-band edits to the store the normal flow can't see.
        Requires receipts to have been enabled at write time."""
        problems: list[str] = []
        prev = _GENESIS
        by_id = {it["id"]: it for it in self.items}
        for i, r in enumerate(self._receipts):
            core = {k: r.get(k) for k in ("seq", "ts", "memory_id", "commit", "prev")}
            if r.get("prev") != prev:
                problems.append(f"receipt {i}: broken chain link (a prior receipt was altered/removed)")
            if _sha256_hex(_canon(core)) != r.get("hash"):
                problems.append(f"receipt {i}: receipt tampered (hash mismatch)")
            if "sig" in r and _HAVE_ED:
                try:
                    _Ed25519PK.from_public_bytes(bytes.fromhex(r["pubkey"])).verify(
                        bytes.fromhex(r["sig"]), bytes.fromhex(r["hash"]))
                    if expected_pubkey and r.get("pubkey") != expected_pubkey:
                        problems.append(f"receipt {i}: signed by an unexpected key")
                except Exception:
                    problems.append(f"receipt {i}: invalid signature")
            elif expected_pubkey:
                problems.append(f"receipt {i}: unsigned, but a signature was required")
            cur = by_id.get(r["memory_id"])
            if cur is None:
                problems.append(f"memory {r['memory_id']}: written but missing from the store (deleted out-of-band)")
            elif self._write_commit(cur) != r["commit"]:
                problems.append(f"memory {r['memory_id']}: stored content no longer matches its write receipt (edited after write)")
            prev = r.get("hash")
        return (len(problems) == 0, problems)

    def _supersede_by_key(self, rec: dict) -> None:
        """Deterministic (subject, relation, object) supersession: retire active records that share
        rec['key']. No similarity threshold, no LLM call — the fix our Crucible replication validated
        (stale-fact recall 41.7% -> 0.0%, where cosine-based detection is near chance at AUROC ~0.61).
        Bi-temporal: only same-key records with valid_from <= rec's are retired; if an active same-key
        record is genuinely newer (later valid_from), the INCOMING rec is the stale one and is retired
        instead — a back-filled value never overwrites the current one. recall() hides superseded records
        by default, so a keyed store never surfaces a stale fact."""
        k = rec.get("key")
        if not k:
            return
        vf_new = rec.get("valid_from", rec["ts"])
        for r in self.items:
            if r is rec or r.get("status") != "active" or r.get("key") != k:
                continue
            vf_r = r.get("valid_from", r["ts"])
            if vf_r <= vf_new:                 # r is the older value -> retire it
                r["status"] = "superseded"
                r["superseded_ts"] = time.time()
                r["invalidated_at"] = vf_new
                r.setdefault("meta", {})["superseded_by_toggle"] = rec["id"]
            else:                              # an active same-key value is newer -> incoming is stale-on-arrival
                rec["status"] = "superseded"
                rec["superseded_ts"] = time.time()
                rec["invalidated_at"] = vf_r
                rec.setdefault("meta", {})["superseded_by_toggle"] = r["id"]

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

    def forget(self, ids=None, where=None, redact_links: bool = True) -> dict:
        """HARD-DELETE memories — the one operation that genuinely REMOVES content. mnemo is otherwise
        append-only: supersession / invalidation only DEMOTE a record (it still exists, recallable with
        include_superseded). forget() is for the cases where demotion is not enough: a right-to-be-forgotten
        / erasure request, a poisoned or libellous memory, or a hard correction.

        Select by `ids` (a single id or an iterable) and/or `where` (a predicate fn(record)->bool; e.g.
        lambda r: 'secret' in r['text']). VERIFIED FORGETTING: the matched records are deleted AND their ids
        are scrubbed from every surviving record's `links` and toggle-supersession pointers, and the cached
        vec matrix + token caches are dropped — so a forgotten memory cannot resurface via recall, via a
        consolidation link, or via a stale derived-summary pointer. This is complete because consolidation
        never copies raw text into other records (it only links ids and toggles status) — there is no merged
        blob left holding the forgotten content. Returns {forgotten, ids, scrubbed_links}."""
        target = set()
        if ids is not None:
            target |= ({ids} if isinstance(ids, str) else set(ids))
        if where is not None:
            for r in self.items:
                try:
                    if where(r):
                        target.add(r["id"])
                except Exception:
                    pass
        target &= {r["id"] for r in self.items}          # ignore ids not actually present
        if not target:
            return {"forgotten": 0, "ids": [], "scrubbed_links": 0}
        self.items = [r for r in self.items if r["id"] not in target]
        scrubbed = 0
        if redact_links:
            for r in self.items:
                if r.get("links"):
                    before = len(r["links"])
                    r["links"] = [l for l in r["links"] if l not in target]
                    scrubbed += before - len(r["links"])
                meta = r.get("meta")
                if meta and meta.get("superseded_by_toggle") in target:
                    meta.pop("superseded_by_toggle", None)   # drop dangling toggle pointer (no ghost stale-derived)
        for tid in target:
            self._tok_cache.pop(tid, None)
        self._mat = None; self._mat_built_n = -1             # force vec-matrix rebuild (drops forgotten rows)
        self._save(force=True)                               # a deletion is real content change — persist now
        return {"forgotten": len(target), "ids": sorted(target), "scrubbed_links": scrubbed}

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
                self._vec_mean = M.mean(axis=0)               # corpus mean (computed regardless; used to center)
                if self.center_embeddings:
                    M = M - self._vec_mean                    # de-anisotropise: remove the common component
                M /= (_np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
                self._mat = M
                self._vec_rowof = {i: k for k, i in enumerate(ids)}
            else:
                self._mat, self._vec_rowof, self._vec_mean = None, {}, None
            self._mat_built_n = len(self.items)
        return self._mat

    def _rec_tokens(self, rec: dict) -> set:
        """Token set for a memory, cached by id — recall over N memories shouldn't re-tokenize."""
        rid = rec.get("id") or id(rec)
        t = self._tok_cache.get(rid)
        if t is None:
            t = _tokens(rec["text"]); self._tok_cache[rid] = t
        return t

    def _rec_tokcount(self, rec: dict) -> dict:
        """Term-frequency map for a memory, cached by id (for the BM25 hybrid channel)."""
        rid = rec.get("id") or id(rec)
        c = self._tc_cache.get(rid)
        if c is None:
            c = _token_counts(rec["text"]); self._tc_cache[rid] = c
        return c

    def _bm25_scores(self, qtok: set, pool: list, k1: float = 1.5, b: float = 0.75) -> list:
        """Okapi BM25 score of `query` (token set) against every record in `pool` — the strong lexical
        channel for the hybrid. df/avgdl are computed over the pool (the live corpus). Returns a list of
        scores aligned to `pool`. Pure-Python, zero-dependency. We MEASURED BM25 (not token-overlap) as the
        lexical channel that makes the hybrid beat either alone (mnemo/probes/locomo_retrieval_map.py)."""
        N = len(pool)
        if N == 0:
            return []
        counts = [self._rec_tokcount(r) for r in pool]
        dl = [sum(c.values()) for c in counts]
        avgdl = (sum(dl) / N) or 1.0
        df: dict = {}
        for c in counts:
            for t in c:
                df[t] = df.get(t, 0) + 1
        idf = {t: math.log(1 + (N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        out = []
        for c, L in zip(counts, dl):
            s = 0.0
            for t in qtok:
                f = c.get(t, 0)
                if f:
                    s += idf.get(t, 0.0) * (f * (k1 + 1)) / (f + k1 * (1 - b + b * L / avgdl))
            out.append(s)
        return out

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
               scope: str | None = None, as_of: float | None = None,
               where: dict | None = None, influence_only: bool = False,
               prefer=None, prefer_trust: float = 1.0,
               prefer_max_boost: float | None = None) -> list[dict]:
        """Top-k memories by RELEVANCE × VALUE — high-value memories outrank merely-similar ones.
        Memories the dream pass flagged as hubs (universal matchers) are skipped unless include_hubs.

        mode: 'auto' (default) uses LEXICAL token overlap while the store is small (< semantic_threshold
        active memories) and a LEXICAL+SEMANTIC HYBRID (Reciprocal Rank Fusion) once it grows past that —
        the hybrid robustly beat either channel alone in our agent-memory benchmark (details in the recall
        body / mnemo/probes/locomo_retrieval_map.py). Force a single channel with mode='lexical' /
        'semantic', or the fusion explicitly with mode='hybrid'. Semantic/hybrid need an embedder (set on
        the store); without one, or if embedding fails, recall falls back to lexical automatically.

        where: an OPT-IN metadata pre-filter applied to the candidate pool BEFORE ranking — the cheap
        'filter before you rank' lever (measured on LoCoMo: a metadata pre-filter can beat retriever choice;
        mnemo/probes/locomo_metadata_prefilter.py). A dict of field -> condition; a record must match ALL
        fields (AND). Each field is matched against the record's top-level attributes first, then its meta
        dict, so both `valid_from`/`mtype`/`key` and any `meta` key work. A condition is either a scalar
        (equality), a list/tuple/set (membership), or a dict of operators:
        {"$gte","$lte","$gt","$lt","$in","$nin","$ne","$contains"} — e.g. a time range
        where={"valid_from": {"$gte": t0, "$lte": t1}} (hard-filter the SOLVED half), or a closed-set
        entity where={"speaker": {"$in": ["Caroline","Mel"]}}. NOTE: this is a HARD filter — a record that
        doesn't match is removed, so on lossy/predicted extraction prefer a broad/loose filter (or rerank)
        over an aggressive one, since a wrong filter hard-deletes the answer (measured harm mode).

        influence_only (OPT-IN, default False -> zero behavior change): restrict the result to CORROBORATED
        memories — those that meet the same bar mnemo uses for episodic->semantic GRADUATION (an EARNED
        net-positive outcome via credit() [good>0 and good>=bad], OR already-graduated 'semantic' type, OR
        >=2 DISTINCT-canonical-source corroborating links). This is the retrieve-then-INFLUENCE split: recall
        freely for context, but call with influence_only=True for the set that is allowed to DRIVE an action.
        MEASURED (mnemo/probes/agentpoison_influence_gate*.py) against a real AgentPoison-style single-
        instance retrieval-poisoning attack (Chen et al., NeurIPS 2024, arXiv:2407.12784; PoisonedRAG, Zou
        et al., arXiv:2402.07867): a natural-sentence trigger hijacks RAW top-1 retrieval 88-100% and is
        scale-invariant (60->10k memories), and retrieval-time / embedding-geometry defenses do NOT
        generalize across encoders — but influence_only drops the single-instance poison's rank-1 hijack to
        0% on all three tested retrievers (MiniLM/BGE/Contriever) and all scales, because an injected poison
        never earns corroboration while legitimate memories earn it through use. It GENERALIZES precisely
        because it lives in provenance metadata, not embedding geometry. HONEST COST (calibration tradeoff):
        a rare-but-true memory that has not yet earned corroboration is filtered too (measured recall 1.00
        corroborated vs 0.08 uncorroborated) — so this is for adversarial / untrusted-ingestion use, where a
        recalled-but-uncorroborated memory should inform but not unilaterally drive an action. It RAISES
        attacker cost (a single free injection is filtered; defeating it needs >=3 coordinated records with
        >=2 independent forged provenances) rather than making poisoning impossible. Reversible: default
        False = legacy recall. Call `influence_gate_report()` first to see this gate's LIVE cost on your store
        (it is density-dependent: ~51% of legit recalls filtered when memories are used ~once, ~6% when dense
        — mnemo/probes/oracle_separation_density.py) and the load-bearing caveat that it rides on an
        un-self-gradable credit() oracle.

        prefer / prefer_trust (OPT-IN, default None -> zero behavior change): a SOFT, trust-weighted metadata
        filter. Unlike `where` (a HARD filter that DELETES non-matching records — so a wrong filter hard-
        deletes the answer), `prefer` takes the same condition dict but only BOOSTS matching records'
        score by (1 + prefer_trust * gain), leaving non-matching records rankable. prefer_trust in [0,1] is
        HOW MUCH to trust the filter cue this call: pass a low value when your metadata extractor is unsure
        (weak/ambiguous match) so the filter gracefully backs off toward plain recall; prefer_trust=0 == no
        filter. This is the a-priori-trust lever: weight the filter by the RELIABILITY of the extraction
        (e.g. alias-match strength: exact-name hit -> ~1.0, no-name/ambiguous guess -> ~0.0), NOT by the
        extractor model's own self-reported confidence (which is corrupted in the overconfident-on-wrong
        case). MEASURED (mnemo/probes/locomo_soft_prefer_filter.py) on LoCoMo: soft prefer weighted by
        alias-strength gives the filter's benefit on reliable (exact-name) queries while backing off on
        ambiguous ones where extraction fails -- beating both no filter and a hard `where` filter under
        imperfect extraction. Reversible: prefer=None = legacy recall.

        MULTI-DIMENSION prefer (compose several soft cues at once): pass `prefer` as a LIST of specs, each
        either {"cond": <dict>, "trust": <0..1>} or a (cond, trust) tuple. Matching dimensions compose as a
        PRODUCT of neutral-at-1.0 factors — pref = Π (1 + trust_i * gain) over the dims a record matches — so
        a record matching two cues is boosted more than one matching a single cue, and non-matching dims are
        inert (factor 1.0). A single dict + scalar prefer_trust is the one-dimension case (unchanged). Cap the
        TOTAL boost with `prefer_max_boost` (a ceiling on the product, like Elasticsearch function_score's
        max_boost); default None = uncapped. MEASURED (mnemo/probes/locomo_composed_soft_filters.py) on LoCoMo:
        on questions carrying two independent cues (a resolved time window AND a named speaker), the product
        composition reached recall@20 0.865 vs 0.755 for the best single cue (+0.110, bootstrap CI excludes 0);
        a naive summed boost CAPPED at one dimension's trust crowded out (-0.053, the cap flattened the joint
        evidence — the classic 'combine outside the saturating form' failure, BM25F, Robertson et al. CIKM
        2004). So: compose as a PRODUCT, and if you cap, cap the product, not the summed trusts. This mirrors
        production search (Elasticsearch function_score defaults score_mode=multiply). Reversible: a single
        dict / None behaves exactly as before."""
        # Normalize `prefer` into a list of (cond_dict, clamped_trust) specs. Back-compat: a plain dict uses
        # the scalar prefer_trust (the legacy one-dimension path, byte-identical scoring); a list composes.
        _prefer_specs: list = []
        if prefer:
            if isinstance(prefer, dict):
                _t0 = max(0.0, min(1.0, float(prefer_trust)))
                if _t0 > 0.0:
                    _prefer_specs = [(prefer, _t0)]
            elif isinstance(prefer, (list, tuple)):
                for _spec in prefer:
                    if isinstance(_spec, dict) and "cond" in _spec:
                        _c, _t = _spec["cond"], float(_spec.get("trust", prefer_trust))
                    elif isinstance(_spec, (list, tuple)) and len(_spec) == 2:
                        _c, _t = _spec[0], float(_spec[1])
                    else:
                        raise ValueError("prefer list items must be {'cond':..,'trust':..} or (cond, trust)")
                    _t = max(0.0, min(1.0, _t))
                    if _t > 0.0 and _c:
                        _prefer_specs.append((_c, _t))
            else:
                raise ValueError("prefer must be a dict (one dimension) or a list of (cond, trust) specs")
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
        # Metadata pre-filter (the 'filter before you rank' lever): keep only records matching ALL `where`
        # conditions, matched against top-level fields then meta. Deterministic, no embedder, O(pool).
        if where:
            pool = [r for r in pool if self._cond_match(r, where)]
        # Influence gate (retrieve-then-influence split): keep only CORROBORATED memories in the set that is
        # allowed to drive an action. Same bar as episodic->semantic graduation; embedder-independent, so it
        # generalizes across retrievers where geometry-based poison defenses do not (see the docstring).
        if influence_only:
            _byid = {x["id"]: x for x in self.items}
            pool = [r for r in pool if self._is_corroborated(r, _byid)]
        # Mode selection. 'hybrid' = lexical (token overlap) + semantic (embedding) fused with Reciprocal
        # Rank Fusion. We MEASURED hybrid robustly beating EITHER channel alone for agent memory on LoCoMo
        # (recall@20 0.61 hybrid vs 0.55 lexical vs 0.53 semantic; +0.057 over the best single channel,
        # 9/10 conversations, conversation-level bootstrap CI excludes 0). So 'auto' now fuses (was: switch
        # lexical->semantic at the threshold). Receipt: mnemo/probes/locomo_retrieval_map.py. RRF needs no
        # tuning and no extra dependency. Force a single channel with mode='lexical'/'semantic'.
        has_embed = self.embed is not None
        if mode == "lexical" or not has_embed:
            sel = "lexical"
        elif mode in ("semantic", "hybrid"):
            sel = mode
        else:                                                 # 'auto': fuse once the store is worth it
            sel = "hybrid" if len(pool) >= self.semantic_threshold else "lexical"
        qvec = self._qvec(query) if sel in ("semantic", "hybrid") else None
        if qvec is None and sel != "lexical":
            sel = "lexical"                                   # embedder absent or failed -> graceful fallback
        self._last_mode = sel
        qtok = _tokens(query)                                 # tokenize the query once (lexical + fallback)
        # Vectorized semantic fast-path: one matmul gives the cosine to every vec-bearing memory.
        sims_vec = None
        if qvec is not None and _np is not None:
            M = self._vec_matrix()
            if M is not None:
                qv = _np.asarray(qvec, dtype=_np.float32)
                if self.center_embeddings and self._vec_mean is not None:
                    qv = qv - self._vec_mean              # center the query the SAME way as the matrix
                sims_vec = M @ (qv / (float(_np.linalg.norm(qv)) or 1.0))
        _now = time.time()                                # for per-type decay of the ranking value
        _by_id = {x["id"]: x for x in self.items}         # for provenance lookups (source-episode status)
        def _semsim(r) -> float:
            if sims_vec is not None and r.get("vec") and r["id"] in self._vec_rowof:
                return max(0.0, float(sims_vec[self._vec_rowof[r["id"]]]))
            return max(0.0, _cosine(qvec, r["vec"])) if (qvec is not None and r.get("vec")) else 0.0
        def _lexsim(r) -> float:
            t = self._rec_tokens(r)
            return (len(qtok & t) / min(len(qtok), len(t))) if (qtok and t) else 0.0
        def _candrec(r, sim):                             # provenance gate + value, shared by all modes
            # Provenance gate: a memory that absorbed near-duplicates (links) is STALE-DERIVED if any of
            # those sources was later CONTRADICTED (state-toggle supersession) — the merged summary
            # outlived a fact it summarized. Demote it (don't drop — flag for re-consolidation), so a
            # consolidated claim can't quietly outrank the fresh memory that overturned its source.
            stale = bool(r.get("links")) and any(
                (_by_id.get(lid, {}).get("meta") or {}).get("superseded_by_toggle") for lid in r["links"])
            r["_stale_derived"] = stale                   # surfaced in the returned record
            return (sim, 0.5 if stale else 1.0, self._effective_value(r, _now), r)
        cands = []                                        # (sim, prov, eff_value, r), sim in [0,1]
        # Relevance-floor ABSTENTION: drop candidates below an absolute similarity floor; if the WHOLE top-k
        # falls below it, recall() returns [] ("not in memory") instead of padding context with a weak false
        # match. min_relevance=0.0 (default) keeps legacy behavior (only sim<=0 dropped). In hybrid the floor
        # is applied to the stronger of the two raw channels, then the FUSED rank score becomes the relevance.
        if sel == "hybrid":
            bm = self._bm25_scores(qtok, pool)            # strong BM25 lexical channel over the live corpus
            scn = []                                      # (r, sem, bm25) candidates above the floor
            for r, bx in zip(pool, bm):
                sem = _semsim(r)
                if (sem <= 0 or sem < min_relevance) and bx <= 0:
                    continue                              # abstain only when BOTH channels are empty/below floor
                scn.append((r, sem, bx))
            if scn:
                order_sem = sorted(range(len(scn)), key=lambda i: -scn[i][1])
                order_bm = sorted(range(len(scn)), key=lambda i: -scn[i][2])
                rrf = [0.0] * len(scn)
                for rank, i in enumerate(order_sem): rrf[i] += 1.0 / (60 + rank)
                for rank, i in enumerate(order_bm):  rrf[i] += 1.0 / (60 + rank)
                mx = max(rrf) or 1.0
                for i, (r, sem, bx) in enumerate(scn):
                    cands.append(_candrec(r, rrf[i] / mx))    # normalize the fused rank score to a [0,1] relevance
        else:
            for r in pool:
                sim = _semsim(r) if sel == "semantic" else _lexsim(r)
                if sim <= 0 or sim < min_relevance:
                    continue
                cands.append(_candrec(r, sim))
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
        # Soft `prefer` filter: multiplicatively boost records matching each prefer condition. Non-matching
        # records are left rankable (unlike hard `where`), so a wrong/weak cue degrades gracefully instead of
        # hard-deleting the answer. Multiple cues COMPOSE as a product of neutral-at-1.0 factors
        # (pref = Π (1 + trust_i * _PREFER_GAIN) over matched dims); one dim reproduces the legacy scalar path.
        # Optionally cap the product at prefer_max_boost (measured: cap the PRODUCT, never the summed trusts).
        scored = []
        for sim, prov, evalue, r in cands:
            if gate_off:
                cal = 1.0
            else:
                cal = 0.5 + self._reliability(r)
                if mode == "boost" and cal < 1.0:
                    cal = 1.0
            pref = 1.0
            for _cond, _tr in _prefer_specs:
                if self._cond_match(r, _cond):
                    pref *= (1.0 + _tr * _PREFER_GAIN)
            if prefer_max_boost is not None and pref > prefer_max_boost:
                pref = prefer_max_boost
            score = sim * (1.0 + math.log1p(max(0.0, evalue))) * prov * cal * pref
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
            # POISON guard (HARDENED 2026-06-25): durability must be EARNED by INDEPENDENT corroboration, not
            # mere recall-frequency. The value bump above is correctness-blind, so a confabulation recalled
            # enough would otherwise graduate to the durable (slow-decay) tier and entrench itself. A
            # self-assertable `source` string or a SINGLE `links` edge is attacker-settable (AgentPoison /
            # MINJA / OWASP-ASI06), so neither alone may confer durability. Require either an EARNED net-positive
            # outcome (good>0 and good>=bad — set only by credit() resolving real work, not self-assertable), OR
            # >=2 DISTINCT corroborating links (no single self-created edge suffices). An uncorroborated popular
            # memory stays episodic and fades on the fast clock unless earned.
            # SYBIL HARDENING (entity resolution): count DISTINCT CANONICAL sources among the corroborating
            # links, not the raw link count. A naive "≥2 links" lets an attacker mint independence by naming
            # one origin many ways ("Wikipedia" / "wikipedia.org" / a full URL → 3 links, 1 real source).
            # Canonicalizing source identifiers before counting collapses those to one; a link whose record
            # has no source counts as its own id, so genuinely source-less corroboration is unchanged.
            _good = float(r.get("good", 0) or 0); _bad = float(r.get("bad", 0) or 0)
            corroborated = (_good > 0 and _good >= _bad) or self._distinct_sources(r.get("links"), _by_id) >= 2
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
    def _canon_source(doc) -> str:
        """Entity-resolution canonicalization of a source identifier, so sybil variants of one origin
        ('Wikipedia', 'wikipedia.org', 'https://www.wikipedia.org/wiki/X') collapse to a single key."""
        s = str(doc or "").strip().lower()
        s = re.sub(r"^[a-z]+://", "", s)                 # strip scheme
        s = re.sub(r"^www\.", "", s)                     # strip www.
        s = s.split("/")[0].split("?")[0]                # host / first path segment only
        s = re.sub(r"\.(org|com|net|io|gov|edu|co|ai|dev|info|news)$", "", s)  # strip a common TLD
        s = re.sub(r"[^a-z0-9]+", "", s)                 # collapse remaining punctuation
        return s

    @staticmethod
    def _rec_sources(rec: dict) -> set:
        """The canonical sources a record is attributable to: its OWN source (entity-resolved) PLUS any taint
        inherited from parents via derived_from (so provenance rides through summarization/consolidation). A
        source-less record is attributable to its own id, so nothing is silently un-attributable. Used by
        slash()/restore() so forfeiting a source also reaches every derived record it fed."""
        src = rec.get("source")
        doc = src.get("doc") if isinstance(src, dict) else (src if isinstance(src, str) else None)
        own = Mnemo._canon_source(doc) if doc else "id:" + rec["id"]
        return {own} | set(rec.get("taint") or [])

    @staticmethod
    def _distinct_sources(links, by_id) -> int:
        """Count DISTINCT canonical sources among corroborating links — entity resolution BEFORE counting,
        so 'three names for one source' sybil variants count as one. A link whose record carries no source
        counts as its own id, so genuinely source-less corroboration is not penalised (no regression)."""
        keys = set()
        for lid in (links or []):
            lr = by_id.get(lid)
            if lr is None:
                continue
            src = lr.get("source")
            doc = src.get("doc") if isinstance(src, dict) else (src if isinstance(src, str) else None)
            keys.add(Mnemo._canon_source(doc) if doc else "id:" + lid)
        return len(keys)

    @staticmethod
    def _is_corroborated(rec: dict, by_id: dict) -> bool:
        """The corroboration bar shared by episodic->semantic graduation and the recall influence gate:
        an EARNED net-positive outcome (good>0 and good>=bad — set by credit() on real work, not
        self-assertable), OR an already-graduated 'semantic' memory, OR >=2 DISTINCT-canonical-source
        corroborating links (sybil variants of one source collapse to one). A single fresh self-asserted
        memory (the AgentPoison single-instance poison) meets none of these."""
        good = float(rec.get("good", 0) or 0)
        bad = float(rec.get("bad", 0) or 0)
        if good > 0 and good >= bad:
            return True
        if rec.get("mtype") == "semantic":
            return True
        return Mnemo._distinct_sources(rec.get("links"), by_id) >= 2

    def influence_gate_report(self) -> dict:
        """Report the LIVE COST of the influence gate (recall(influence_only=True)) on THIS store, so you can
        judge whether it is affordable before enabling it. The gate keeps only CORROBORATED memories
        (_is_corroborated); its cost is that not-yet-earned LEGITIMATE memories are filtered too, and that cost
        is DENSITY-DEPENDENT. MEASURED on a controlled corpus with real embeddings
        (mnemo/probes/oracle_separation_density.py): the fraction of legitimate high-stakes recalls the gate
        blocks falls from ~51% when each memory is used ~once (sparse) to ~6% when each is used ~8x (dense),
        because a legit memory only earns standing through repeated successful use — so in a SPARSE store the
        gate is expensive (it filters most legit recalls); grow density, or credit() real outcomes, before
        relying on influence_only for anything but adversarial/untrusted ingestion.
        A SECOND, load-bearing caveat the same probe measured: the gate rides ENTIRELY on credit() being an
        outcome oracle the attacker CANNOT SELF-GRADE. A MINJA-style self-graded outcome (arXiv:2503.03704)
        collapses the gate at every density — it can even block legit MORE than poison. Never let recalled
        memory content drive its own credit(); issue outcomes from the application, on real resolved work.
        Returns {active, corroborated, corroborated_frac, would_block_frac, by_path{earned_outcome, semantic,
        multi_source}, advice}. Read-only; no side effects."""
        byid = {x["id"]: x for x in self.items}
        active = [r for r in self.items if r.get("status") == "active"]
        n = len(active)
        earned = sem = multi = corr = 0
        for r in active:
            g = float(r.get("good", 0) or 0); b = float(r.get("bad", 0) or 0)
            if g > 0 and g >= b:
                corr += 1; earned += 1
            elif r.get("mtype") == "semantic":
                corr += 1; sem += 1
            elif self._distinct_sources(r.get("links"), byid) >= 2:
                corr += 1; multi += 1
        frac = (corr / n) if n else 0.0
        advice = ("cheap - most active memories are corroborated" if frac >= 0.7 else
                  "affordable" if frac >= 0.4 else
                  "expensive - store too sparse; influence_only will filter most legit recalls. Grow density "
                  "or credit() real outcomes first, or use it only for untrusted-ingestion defense.")
        return {"active": n, "corroborated": corr, "corroborated_frac": round(frac, 3),
                "would_block_frac": round(1.0 - frac, 3),
                "by_path": {"earned_outcome": earned, "semantic": sem, "multi_source": multi},
                "advice": advice}

    @staticmethod
    def _cond_match(r: dict, conds: dict) -> bool:
        """Does record r satisfy ALL of `conds` (a where/prefer dict)? Each field is matched against the
        record's top-level attributes first, then its meta dict. A condition is a scalar (equality), a
        list/tuple/set (membership), or a dict of operators ($eq/$ne/$in/$nin/$gte/$lte/$gt/$lt/$contains).
        Shared by the hard `where` pre-filter and the soft `prefer` trust-weighted boost."""
        meta = r.get("meta") or {}
        for field, cond in conds.items():
            val = r[field] if field in r else meta.get(field)
            if isinstance(cond, dict):
                for op, cv in cond.items():
                    if op in ("$eq", "eq"):
                        if val != cv: return False
                    elif op in ("$ne", "ne"):
                        if val == cv: return False
                    elif op in ("$in", "in"):
                        if val not in cv: return False
                    elif op in ("$nin", "nin"):
                        if val in cv: return False
                    elif op in ("$gte", "gte"):
                        if val is None or val < cv: return False
                    elif op in ("$lte", "lte"):
                        if val is None or val > cv: return False
                    elif op in ("$gt", "gt"):
                        if val is None or val <= cv: return False
                    elif op in ("$lt", "lt"):
                        if val is None or val >= cv: return False
                    elif op in ("$contains", "contains"):
                        if val is None or cv not in val: return False
                    else:
                        raise ValueError(f"recall condition: unknown operator {op!r}")
            elif isinstance(cond, (list, tuple, set)):
                if val not in cond: return False
            else:
                if val != cond: return False
        return True

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

    def slash(self, ids, scope: str = "source") -> dict:
        """Retroactive standing forfeiture — the accountability lever for a CAUGHT poison. When a memory is
        caught driving a bad outcome (the application detects/attributes it), slash() FORFEITS the entire
        accrued outcome-standing of its SOURCE (scope='source', default — every active memory sharing that
        canonical source) or just the named memories (scope='memory'). A patient 'sleeper' that banked good
        credit over many benign memories under one identity loses ALL of it on one catch, so its accrued
        reputation IS the bond and its patience becomes its largest exposed stake.
        WHY this and not credit(bad): credit() is append-only, so a net-positive sleeper survives one bad
        (good=50, bad=1 stays trusted). slash() zeroes `good`, books a dominating `bad`, AND revokes any
        episodic->semantic graduation, so the source goes net-negative and immediately FAILS the corroboration
        / influence gate (recall(influence_only=True) and episodic->semantic graduation). WHY not forget():
        forget() deletes; slash() KEEPS the records for audit and only strips their standing — they can still be
        recalled for context, just not trusted to drive an action. This makes cost-of-corruption scale with the
        accrued standing + detection (Becker expected-penalty: the penalty must beat gain / P(caught)), which is
        the lever that bites a time-rich patient attacker a per-action cap only lets him amortize. MEASURED
        motivation: mnemo/probes/triad_attacker_split.py + reversibility_gate_frontier.py (the residual against a
        patient sleeper is a slow-cumulative in-domain attack; retroactive forfeiture, not a throughput cap, is
        the dominant control). Returns {slashed, sources, ids}. Records + raw text untouched; only good/bad/mtype
        change, auditable via meta['slashed']. Reversible: nothing is deleted."""
        by_id = {x["id"]: x for x in self.items}
        caught = [by_id[i] for i in (ids or []) if i in by_id]
        if scope == "source":
            bad_sources = set().union(*(Mnemo._rec_sources(r) for r in caught)) if caught else set()
            # a record is caught if its own source OR any inherited taint intersects the slashed sources ->
            # forfeiting a source also burns every derived summary/consolidation it fed (provenance-carried).
            targets = [r for r in self.items if r.get("status") == "active"
                       and (Mnemo._rec_sources(r) & bad_sources)]
            sources = sorted(bad_sources)
        else:                                    # scope='memory' — only the named records
            targets, sources = caught, []
        slashed = []
        for r in targets:
            meta = r.setdefault("meta", {})
            if not meta.get("slashed"):          # record pre-slash state ONCE (for audit + restore); don't
                meta["pre_slash"] = {"good": float(r.get("good", 0) or 0),   # clobber it on a double-slash
                                     "bad": float(r.get("bad", 0) or 0), "mtype": r.get("mtype", "episodic")}
            g = float(r.get("good", 0) or 0); b = float(r.get("bad", 0) or 0)
            r["good"] = 0.0
            r["bad"] = g + b + 1.0               # dominating -> net-negative -> blocked by the influence gate
            if r.get("mtype") == "semantic":
                r["mtype"] = "episodic"          # revoke graduation, else it still passes _is_corroborated
            meta["slashed"] = True
            slashed.append(r["id"])
        if slashed:
            self._save()
        return {"slashed": len(slashed), "sources": sources, "ids": slashed}

    def restore(self, ids, scope: str = "source") -> dict:
        """Undo a slash() — the safety valve. Detection is imperfect (a self-graded / MINJA-style oracle can be
        tricked into flagging a LEGIT source, so slash() can be WEAPONISED to knock out a rival's memory), so a
        forfeiture must be reversible. When a slashed source is exonerated, restore() recovers its EXACT
        pre-slash standing from meta['pre_slash'] (good/bad/graduation) — or, if none was recorded, a clean
        slate (good=0, bad=0) so it must re-earn rather than snapping back to trusted. scope='source' restores
        every active memory sharing the caught record's canonical source; scope='memory' only the named records.
        Only records currently marked meta['slashed'] are touched. Returns {restored, sources, ids}. This is the
        deliberate cost of the retroactive lever: because the penalty is heavy (whole accrued standing), the
        appeal has to be cheap — otherwise slash() itself becomes the attack surface."""
        by_id = {x["id"]: x for x in self.items}
        seed = [by_id[i] for i in (ids or []) if i in by_id]
        if scope == "source":
            srcs = set().union(*(Mnemo._rec_sources(r) for r in seed)) if seed else set()
            targets = [r for r in self.items if (Mnemo._rec_sources(r) & srcs) and (r.get("meta") or {}).get("slashed")]
            sources = sorted(srcs)
        else:
            targets, sources = [r for r in seed if (r.get("meta") or {}).get("slashed")], []
        restored = []
        for r in targets:
            meta = r.get("meta") or {}
            prev = meta.pop("pre_slash", None)
            if prev:                              # recover exact pre-slash standing
                r["good"] = float(prev.get("good", 0) or 0)
                r["bad"] = float(prev.get("bad", 0) or 0)
                r["mtype"] = prev.get("mtype", r.get("mtype", "episodic"))
            else:                                 # no record -> clean slate (must re-earn, don't snap to trusted)
                r["good"] = 0.0; r["bad"] = 0.0
            meta["slashed"] = False
            restored.append(r["id"])
        if restored:
            self._save()
        return {"restored": len(restored), "sources": sources, "ids": restored}

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

    def recall_iterative(self, query: str, ask_followup, k: int = 6, rounds: int = 1,
                         **recall_kw) -> list[dict]:
        """Multi-hop recall. One-shot top-k misses evidence reachable only via a BRIDGE entity (a fact whose
        detail lives in a memory NOT similar to the query). This does: retrieve -> let a capable model read the
        results and name what's missing, emitting follow-up queries -> retrieve again -> merge (dedup by id).
        `ask_followup(query, current_results) -> list[str]` is caller-supplied, so mnemo stays model-agnostic
        (inject any model/LLM). MEASURED ~3.3x multi-hop full-evidence recall vs one-shot top-k on LoCoMo
        (0.057 -> 0.186, n=70 across 3 conversations) — the one mechanism that moved the multi-hop bottleneck
        where static retrieval tricks (dense-neighbor, lexical bridges) did not. More expensive (a model call
        in the loop), so it's an explicit mode, not the default."""
        seen: dict = {}
        for r in self.recall(query, k=k, **recall_kw):
            seen[r["id"]] = r
        for _ in range(max(0, int(rounds))):
            try:
                followups = ask_followup(query, list(seen.values())) or []
            except Exception:
                followups = []
            for fq in followups:
                if not isinstance(fq, str) or not fq.strip():
                    continue
                for r in self.recall(fq, k=k, **recall_kw):
                    seen.setdefault(r["id"], r)
        return list(seen.values())

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
                            # Fast-novelty guard (opt-in): supersede only on a CORROBORATED contradiction
                            # (earned credit, or >=2 links — same bar as graduation). An uncorroborated
                            # single contradiction is recorded as a link but does NOT override a standing
                            # fact (resists single-shot poison flips). Default OFF -> legacy fast behavior.
                            if self.supersede_requires_corroboration:
                                _ng = float(newer.get("good", 0) or 0); _nb = float(newer.get("bad", 0) or 0)
                                if not ((_ng > 0 and _ng >= _nb) or len(newer.get("links") or []) >= 2):
                                    a["links"].append(b["id"]); linked += 1
                                    continue
                            # Persistence (CUSUM) guard: supersede only once the NEW state is asserted by
                            # >= supersede_persistence independent records (the change has persisted). Count
                            # active records that (i) match newer's value/polarity and (ii) contradict older —
                            # an isolated poison flip stays below the threshold and is merely linked.
                            if self.supersede_persistence > 1:
                                nvec = self._qvec(newer["text"])
                                support = sum(
                                    1 for r in active if r["status"] == "active"
                                    and self._similarity(newer["text"], r, nvec) >= dup_threshold
                                    and not _value_clash(newer["text"], r["text"])
                                    and not _negation_clash(newer["text"], r["text"])
                                    and (_value_clash(older["text"], r["text"]) or _negation_clash(older["text"], r["text"])))
                                if support < self.supersede_persistence:
                                    a["links"].append(b["id"]); linked += 1
                                    continue
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
            # active is sorted by -raw value (above). Legacy = keep the top-`keep` by raw value. Two-tier =
            # protect the top kprot by raw value (recency-immune), then fill the remaining budget from the
            # REST by EFFECTIVE (decay-weighted) value, so a stale high-raw-value memory can't crowd out a
            # freshly-useful one. (kprot=0 for tiny budgets -> pure recency-aware fill.)
            if self.two_tier_keep:
                now = time.time()
                kprot = int(self.protect_frac * keep)
                protected, rest = active[:kprot], active[kprot:]
                rest_keep = set(id(r) for r in
                                sorted(rest, key=lambda r: -self._effective_value(r, now))[:keep - kprot])
                drop = [r for r in rest if id(r) not in rest_keep]
            else:
                drop = active[keep:]
            for r in drop:
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
# Max multiplicative boost for a fully-trusted soft `prefer` filter match (prefer_trust=1 -> x4). At
# prefer_trust=1 this strongly prefers matches (approaching a hard filter) but never DELETES non-matches,
# so a highly-relevant non-match can still surface; prefer_trust=0 -> no boost. Fixed a priori (not tuned
# on the eval) so the measured win isn't an overfit.
_PREFER_GAIN = 3.0
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
