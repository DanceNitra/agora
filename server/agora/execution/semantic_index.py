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


def _embed_batch(texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": MODEL, "input": texts}).encode()
    req = urllib.request.Request(OLLAMA_EMBED, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read()).get("embeddings", [])


def _note_text(path: Path) -> str | None:
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
    return f"{path.stem}. {body[:500]}"


def build_index(vault: str, batch: int = 64) -> dict:
    """(Re)build the semantic index. ~7 min for ~5k notes. Returns stats."""
    vroot = Path(vault)
    items = []
    for p in vroot.rglob("*.md"):
        if any(s in p.parts or s in str(p) for s in SKIP):
            continue
        txt = _note_text(p)
        if txt:
            items.append((p.relative_to(vroot).as_posix(), p.stem, txt))
    vecs, meta = [], []
    t0 = time.time()
    for i in range(0, len(items), batch):
        chunk = items[i:i + batch]
        embs = _embed_batch([c[2] for c in chunk])
        for (rel, title, txt), e in zip(chunk, embs):
            if e:
                vecs.append(e)
                meta.append({"path": rel, "title": title, "len": len(txt)})
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

    def find_gaps(self, n: int = 12, min_len: int = 300) -> list[dict]:
        """The user's most ISOLATED yet SUBSTANTIVE notes — seeds they planted but never grew
        (semantically disconnected, real content). These are the gaps worth real research."""
        if not self.ready or self.nn is None:
            return []
        gaps = []
        for i in np.argsort(self.nn):                # most isolated first
            m = self.meta[i]
            if m.get("len", 0) >= min_len:
                gaps.append({"title": m["title"], "path": m["path"],
                             "isolation": round(float(1 - self.nn[i]), 3)})
            if len(gaps) >= n:
                break
        return gaps

    @property
    def ready(self) -> bool:
        return self.vecs is not None and len(self.meta) > 0

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
        return [{"title": self.meta[i]["title"], "path": self.meta[i]["path"],
                 "score": round(float(sims[i]), 3)} for i in idx]
