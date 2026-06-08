"""
VaultReader — reads concepts from an Obsidian "second brain" vault (a local git
clone of a private repo) so dungeon agents can draw on a real knowledge base.

Design:
  - Points at a vault directory (AGORA_VAULT_PATH). Loads every `.md` note,
    preferring a Concepts subfolder but falling back to the whole vault.
  - `query()` does keyword-overlap scoring over titles + bodies (no heavy FAISS
    dependency; works offline on any Obsidian structure).
  - If no vault path is configured / found, serves 3 built-in mock concepts so the
    feature is always testable.

Part of Agentic OS v2.1 (VaultBridge).
"""
import os
import random
import re
from pathlib import Path
from typing import Optional

# Subfolders we prefer (in order). If none exist we scan the whole vault.
PREFERRED_SUBDIRS = [
    "04 Resources/Concepts",
    "Concepts",
    "04 Resources",
]

MAX_NOTES = 2000          # safety cap when scanning a large vault
MAX_BODY_CHARS = 4000     # trim very long notes


_MOCK_CONCEPTS = [
    {
        "book": "Antifragile (Taleb)",
        "title": "Antifragility",
        "text": ("Some things benefit from shocks; they thrive and grow when exposed "
                 "to volatility, randomness, disorder, and stressors. Antifragility is "
                 "beyond resilience or robustness: the resilient resists shocks and stays "
                 "the same, the antifragile gets better."),
    },
    {
        "book": "Thinking, Fast and Slow (Kahneman)",
        "title": "System 1 and System 2",
        "text": ("System 1 operates automatically and quickly, with little effort and no "
                 "sense of voluntary control. System 2 allocates attention to the effortful "
                 "mental activities that demand it, including complex computation and "
                 "deliberate choice."),
    },
    {
        "book": "Gödel, Escher, Bach (Hofstadter)",
        "title": "Strange Loops",
        "text": ("A strange loop arises when, by moving up or down through a hierarchical "
                 "system, you unexpectedly find yourself back where you started. Self-reference "
                 "and recursion give rise to meaning and, perhaps, to consciousness."),
    },
]


class VaultReader:
    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or None
        self._concepts: Optional[list[dict]] = None  # lazy-loaded cache

    # ── Loading ───────────────────────────────────────────────
    def _resolve_dir(self) -> Optional[Path]:
        if not self.vault_path:
            return None
        root = Path(os.path.expanduser(self.vault_path))
        if not root.exists():
            return None
        for sub in PREFERRED_SUBDIRS:
            d = root / sub
            if d.is_dir():
                return d
        return root  # fall back to whole vault

    def _load(self) -> list[dict]:
        if self._concepts is not None:
            return self._concepts
        directory = self._resolve_dir()
        if directory is None:
            self._concepts = list(_MOCK_CONCEPTS)
            return self._concepts

        concepts: list[dict] = []
        for path in sorted(directory.rglob("*.md"))[:MAX_NOTES]:
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            title, body = _parse_note(raw, path.stem)
            if not body.strip():
                continue
            # "book" = top-level folder under the vault (a useful grouping)
            try:
                rel = path.relative_to(directory)
                book = rel.parts[0] if len(rel.parts) > 1 else directory.name
            except Exception:
                book = directory.name
            concepts.append({
                "book": book,
                "title": title,
                "text": body[:MAX_BODY_CHARS],
                "path": str(path),
            })

        self._concepts = concepts or list(_MOCK_CONCEPTS)
        return self._concepts

    # ── Public API ────────────────────────────────────────────
    async def query(self, query: str, top_k: int = 5) -> list[dict]:
        """Keyword-overlap search over the vault. Returns up to top_k concepts."""
        concepts = self._load()
        keywords = [w for w in re.findall(r"[a-zA-Z]{4,}", (query or "").lower())]
        if not keywords:
            return random.sample(concepts, min(top_k, len(concepts)))

        scored = []
        for c in concepts:
            hay = (c["title"] + " " + c["text"]).lower()
            score = sum(hay.count(kw) for kw in keywords)
            # small bonus for a title hit
            score += 3 * sum(1 for kw in keywords if kw in c["title"].lower())
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [c for _s, c in scored[:top_k]]
        # if nothing matched, return a few random notes so callers still get context
        return results or random.sample(concepts, min(top_k, len(concepts)))

    async def get_random_insight(self) -> Optional[dict]:
        """Return one random concept (for ambient 'book insight' broadcasts)."""
        concepts = self._load()
        if not concepts:
            return None
        c = random.choice(concepts)
        return {"book": c["book"], "title": c["title"], "text": c["text"][:300]}

    def is_real(self) -> bool:
        """True if reading a real vault (not the built-in mock concepts)."""
        return self._resolve_dir() is not None


def _parse_note(raw: str, fallback_title: str) -> tuple[str, str]:
    """Strip YAML frontmatter, take the first H1 as the title (else filename)."""
    body = raw
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4:]
    title = fallback_title
    m = re.search(r"^\s*#\s+(.+)$", body, re.MULTILINE)
    if m:
        title = m.group(1).strip()
    return title, body.strip()
