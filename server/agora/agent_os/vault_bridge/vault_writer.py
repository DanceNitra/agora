"""
VaultWriter — lets dungeon agents write `.md` notes back into the Obsidian vault
(with frontmatter) and optionally git-commit+push them.

If no vault path is configured, it writes to a local test directory so the feature
is always exercisable without touching a real repo. Git operations are best-effort
and use the local clone's own credentials (this code never handles secrets).

Part of Agentic OS v2.1 (VaultBridge).
"""
import asyncio
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Where agents drop their notes inside the vault.
AGENT_NOTES_SUBDIR = "04 Resources/Concepts/Agora Agents"


class VaultWriter:
    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or None
        if self.vault_path and Path(os.path.expanduser(self.vault_path)).exists():
            self.base = Path(os.path.expanduser(self.vault_path)) / AGENT_NOTES_SUBDIR
            self.real = True
        else:
            self.base = Path(tempfile.gettempdir()) / "agora-vault-output"
            self.real = False

    async def write_note(self, title: str, content: str, tags: list[str],
                         agent_name: str = "agent") -> str:
        """Write an Obsidian note with frontmatter into a dated subfolder. Returns the path."""
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        target_dir = self.base / day      # …/Agora Agents/2026-06-08/
        target_dir.mkdir(parents=True, exist_ok=True)
        slug = _slug(title) or _slug(agent_name) or "note"
        path = target_dir / f"{slug}.md"

        tag_list = ", ".join(tags or [])
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        front = (
            "---\n"
            f"title: {title}\n"
            f"author: {agent_name}\n"
            f"tags: [{tag_list}]\n"
            f"created: {now}\n"
            "source: Agora dungeon agent\n"
            "---\n\n"
        )
        body = f"# {title}\n\n{content}\n"
        try:
            path.write_text(front + body, encoding="utf-8")
        except Exception as e:
            print(f"[VaultWriter] write error: {e}")
        return str(path)

    async def git_commit_and_push(self, file_path: str, message: str) -> bool:
        """Best-effort git add+commit+push in the vault repo. No-op in test mode."""
        if not self.real or not self.vault_path:
            return False
        repo = os.path.expanduser(self.vault_path)
        rel = os.path.relpath(file_path, repo)

        def _run():
            try:
                subprocess.run(["git", "-C", repo, "add", rel],
                               check=True, capture_output=True, timeout=30)
                subprocess.run(["git", "-C", repo, "commit", "-m", message],
                               check=True, capture_output=True, timeout=30)
                subprocess.run(["git", "-C", repo, "push"],
                               check=True, capture_output=True, timeout=60)
                return True
            except Exception as e:
                print(f"[VaultWriter] git push skipped: {str(e)[:120]}")
                return False

        return await asyncio.to_thread(_run)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9 -]", "", (text or "")).strip().lower()
    return re.sub(r"[ _]+", "-", s)[:60]
