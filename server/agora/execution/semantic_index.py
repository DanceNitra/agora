"""
Semantic index of the user's vault — lets agents find the user's REAL relevant notes by
meaning (embeddings), not keywords, and spot genuine gaps in their existing knowledge.

Embeds each note (title + snippet) with a local Ollama embedding model (nomic-embed-text,
free, offline), caches the normalized vectors, and answers cosine top-k queries. The cache
lives OUTSIDE the vault so it never bloats Obsidian.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

import numpy as np

OLLAMA_EMBED = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"
CACHE = Path(__file__).resolve().parents[2] / ".semantic_cache"   # server/.semantic_cache
SKIP = (".git", ".obsidian", ".meta", "_vault_quarantine")
# Machine-generated review artifacts (AutoLinker reports, QA duplicate reports) are not knowledge —
# never embed them: they are huge low-specificity files that otherwise dominate retrieval as
# universal-matcher hubs and distort semantic neighbourhoods.
MACHINE_REPORT = re.compile(r"^(autolinker_(report|pending)|quality_report)", re.I)
RETRIEVAL_LOG = Path(__file__).resolve().parents[2] / ".retrieval_log.json"


def log_retrieval(paths: list[str]) -> None:
    """Per-note demand counters — which notes searches actually surface. Feeds the Memory
    Economy's value accounting (a note that is never retrieved isn't earning its keep)."""
    try:
        log = json.loads(RETRIEVAL_LOG.read_text(encoding="utf-8"))
    except Exception:
        log = {}
    now = time.time()
    for p in paths:
        e = log.setdefault(p, {"n": 0})
        e["n"] += 1
        e["last"] = now
    try:
        RETRIEVAL_LOG.write_text(json.dumps(log, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def retrieval_counts() -> dict:
    try:
        return json.loads(RETRIEVAL_LOG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _embed_batch(texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": MODEL, "input": texts}).encode()
    req = urllib.request.Request(OLLAMA_EMBED, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read()).get("embeddings", [])


def _note_text(path: Path) -> tuple[str, int] | None:
    """Return (embed_text, full_body_length) or None for stubs."""
    try:
        t = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    body = t
    if t.startswith("---"):
        end = t.find("\n---", 3)
        if end != -1:
            body = t[end + 4:]
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) < 40:
        return None
    return f"{path.stem}. {body[:500]}", len(body)


def build_index(vault: str, batch: int = 64) -> dict:
    """(Re)build the semantic index. ~7 min for ~5k notes. Returns stats."""
    vroot = Path(vault)
    items = []
    for p in vroot.rglob("*.md"):
        if any(s in p.parts or s in str(p) for s in SKIP):
            continue
        if MACHINE_REPORT.match(p.stem):
            continue                    # AutoLinker / QA machine reports — not knowledge
        res = _note_text(p)
        if res:
            embed_txt, full_len = res
            items.append((p.relative_to(vroot).as_posix(), p.stem, embed_txt, full_len))
    vecs, meta = [], []
    t0 = time.time()
    for i in range(0, len(items), batch):
        chunk = items[i:i + batch]
        embs = _embed_batch([c[2] for c in chunk])
        for (rel, title, _embed, full_len), e in zip(chunk, embs):
            if e:
                vecs.append(e)
                meta.append({"path": rel, "title": title, "len": full_len})
    arr = np.array(vecs, dtype=np.float32)
    arr /= (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9)   # L2-normalize
    # nearest-neighbour similarity per note (isolation signal for gap detection)
    sims = arr @ arr.T
    np.fill_diagonal(sims, -1.0)
    nn = sims.max(axis=1).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / "vectors.npy", arr)
    np.save(CACHE / "nn.npy", nn)
    (CACHE / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return {"notes": len(meta), "dim": arr.shape[1] if arr.size else 0,
            "seconds": round(time.time() - t0, 1)}


class SemanticIndex:
    """Loads the cached index and answers cosine top-k queries."""

    def __init__(self):
        self.vecs = None
        self.nn = None
        self.meta = []
        self._load()

    def _load(self):
        try:
            self.vecs = np.load(CACHE / "vectors.npy")
            self.meta = json.loads((CACHE / "meta.json").read_text(encoding="utf-8"))
            try:
                self.nn = np.load(CACHE / "nn.npy")
            except Exception:
                self.nn = None
        except Exception:
            self.vecs, self.nn, self.meta = None, None, []

    # tooling / reference / templates — not knowledge gaps
    _NOT_KNOWLEDGE = ("System/Skills", "06 System", "Templates", "templates",
                      "Backups", ".meta", "Sessions", "Daily", "Inbox", "Fleeting")

    def find_gaps(self, n: int = 12, min_len: int = 900) -> list[dict]:
        """The user's most ISOLATED yet SUBSTANTIVE knowledge notes — seeds they invested in but
        never grew (semantically disconnected, real content, not tooling). Real research gaps."""
        if not self.ready or self.nn is None:
            return []
        gaps = []
        for i in np.argsort(self.nn):                # most isolated first
            m = self.meta[i]
            if m.get("len", 0) >= min_len and not any(s in m["path"] for s in self._NOT_KNOWLEDGE):
                gaps.append({"title": m["title"], "path": m["path"],
                             "isolation": round(float(1 - self.nn[i]), 3)})
            if len(gaps) >= n:
                break
        return gaps

    def rotated_gaps(self, n: int = 10) -> list[dict]:
        """find_gaps + least-recently-served rotation. Shared by the agents AND the reports so both
        cycle through the whole isolated-note set instead of fixating on the deterministic top few
        (the 'why do I still see the same gaps in the report' bug — reports called find_gaps directly)."""
        import json as _json
        import time as _time
        pool = self.find_gaps(max(n * 8, 600))
        store = Path(__file__).resolve().parents[2] / ".gap_rotation.json"
        now = _time.time()
        try:
            served = _json.loads(store.read_text(encoding="utf-8"))
        except Exception:
            served = {}
        pool.sort(key=lambda g: (served.get(g["title"], 0.0), -g.get("isolation", 0.0)))
        chosen = pool[:n]
        for g in chosen:
            served[g["title"]] = now
        try:
            store.write_text(_json.dumps({k: v for k, v in served.items() if now - v <= 7 * 86400}),
                             encoding="utf-8")
        except Exception:
            pass
        return chosen

    @property
    def ready(self) -> bool:
        return self.vecs is not None and len(self.meta) > 0

    def _link_graph(self, vault_root: str) -> dict:
        """title(lower) → set of titles it links via [[wikilinks]]. Scanned once, cached."""
        if getattr(self, "_links", None) is not None:
            return self._links
        wl = re.compile(r"\[\[([^\]|#]+)")
        root = Path(vault_root)
        links = {}
        for m in self.meta:
            try:
                txt = (root / m["path"]).read_text(encoding="utf-8", errors="replace")
            except Exception:
                txt = ""
            links[m["title"].lower()] = {t.strip().lower() for t in wl.findall(txt)}
        self._links = links
        return links

    _TOOLING_HINT = (".py", "vault_connectome", "obsidian vault", "skills", "template",
                     "readme", "index", "map of content", " moc", "untitled")

    def _is_knowledge(self, m: dict) -> bool:
        """A real idea note — substantive and not tooling/meta/mis-filed."""
        if m.get("len", 0) < 400:
            return False
        if any(s in m["path"] for s in self._NOT_KNOWLEDGE):
            return False
        t = m["title"].lower()
        return not any(h in t for h in self._TOOLING_HINT)

    def find_bridges(self, vault_root: str, n: int = 8,
                     lo: float = 0.70, hi: float = 0.90, scan: int = 600) -> list[dict]:
        """Pairs of the user's notes that are semantically close (lo<sim<hi, so related but not
        duplicates) yet NOT linked to each other — missing connections worth bridging. Only
        between substantive knowledge notes (tooling/meta/mis-filed excluded)."""
        if not self.ready:
            return []
        sims = self.vecs @ self.vecs.T
        np.fill_diagonal(sims, -1.0)
        # top-2 neighbours per note → candidate pairs in [lo, hi]
        top2 = np.argpartition(-sims, 2, axis=1)[:, :2]
        pairs = {}
        for i in range(len(self.meta)):
            for j in top2[i]:
                j = int(j)
                s = float(sims[i, j])
                if lo < s < hi:
                    pairs[(min(i, j), max(i, j))] = s
        cand = sorted(pairs.items(), key=lambda kv: -kv[1])[:scan]
        links = self._link_graph(vault_root)
        bridges = []
        for (a, b), s in cand:
            if not (self._is_knowledge(self.meta[a]) and self._is_knowledge(self.meta[b])):
                continue                                   # skip tooling / meta / stubs
            ta, tb = self.meta[a]["title"], self.meta[b]["title"]
            la, lb = ta.lower(), tb.lower()
            if lb in links.get(la, set()) or la in links.get(lb, set()):
                continue                                   # already linked
            if la == lb:
                continue
            bridges.append({"a": ta, "b": tb, "sim": round(s, 3),
                            "a_path": self.meta[a]["path"], "b_path": self.meta[b]["path"]})
            if len(bridges) >= n:
                break
        return bridges

    def search(self, query: str, top_k: int = 8) -> list[dict]:
        if not self.ready:
            return []
        q = _embed_batch([query])
        if not q or not q[0]:
            return []
        qv = np.array(q[0], dtype=np.float32)
        qv /= (np.linalg.norm(qv) + 1e-9)
        sims = self.vecs @ qv
        idx = np.argsort(-sims)[:top_k]
        hits = [{"title": self.meta[i]["title"], "path": self.meta[i]["path"],
                 "score": round(float(sims[i]), 3)} for i in idx]
        log_retrieval([h["path"] for h in hits if h["score"] > 0.4])   # demand signal (Memory Economy)
        return hits
