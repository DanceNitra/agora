"""Real Action Engine — dungeon agents execute real-world actions.

Each agent can decide to take real actions via LLM:
  - send_telegram: send message to user via Telegram
  - write_note: write .md note to vault + git commit+push
  - write_article: write long-form SEO article to vault
  - run_script: execute a shell command (safe sandbox)
  - git_commit: commit+pull+push to vault repo
  - create_task: log a task for later processing

Actions are routed through existing subsystems:
  - VaultWriter for vault operations
  - Hermes actions for Telegram
  - subprocess for scripts (safe mode)
"""
import json
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Optional


class RealActionEngine:
    """Executes real-world actions decided by dungeon agents."""

    def __init__(self, vault_writer=None, vault_reader=None, db=None):
        self.vault_writer = vault_writer
        self.vault_reader = vault_reader
        self.db = db
        self.log_dir = "/tmp/agora-actions"

    async def execute(self, action_type: str, params: dict,
                       agent_name: str = "", broadcast_fn=None) -> dict:
        """Execute a real action. Returns result dict."""
        handlers = {
            "send_telegram": self._send_telegram,
            "write_note": self._write_note,
            "write_article": self._write_article,
            "run_script": self._run_script,
            "git_commit": self._git_commit,
            "ask_question": self._ask_question,
        }
        handler = handlers.get(action_type)
        if not handler:
            return {"status": "skipped", "output": f"Unknown action: {action_type}"}

        result = await handler(params, agent_name)
        
        # Log the action
        os.makedirs(self.log_dir, exist_ok=True)
        log_entry = {
            "time": datetime.now().isoformat(),
            "agent": agent_name,
            "action": action_type,
            "params": {k: v for k, v in params.items() if k != "content"},
            "result": result.get("status"),
        }
        with open(f"{self.log_dir}/actions.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        if broadcast_fn:
            await broadcast_fn("real_action", {
                "agent": agent_name,
                "action": action_type,
                "status": result.get("status"),
                "summary": result.get("output", "")[:100],
            })

        return result

    async def get_action_context(self, agent_name: str, role: str) -> str:
        """Return formatted string for LLM prompt injection."""
        # Ambient agents get KNOWLEDGE actions only. They must never DM the owner (send_telegram),
        # run shell (run_script), or push git (git_commit) from an ambient tick — those pinged the
        # owner's Telegram with "give me a task / which to prioritize" spam. Agent-to-agent coordination
        # happens via the decision `action` field (seek_help/cooperate/share); the owner's report surface
        # is the brain's report loops + the Vault-Company OS. (agent_os enforces the same whitelist.)
        role_actions = {
            "adventurer": ["write_note"],
            "scout": ["write_note", "ask_question"],
            "sage": ["write_note", "write_article", "ask_question"],
            "blacksmith": ["write_note", "ask_question"],
            "alchemist": ["write_note", "write_article"],
            "guard": ["write_note"],
        }
        actions = role_actions.get(role, ["write_note"])

        lines = [
            "\n--- Available Real Actions ---",
            "Your decisions can affect the real world. You have these actions available:",
        ]
        action_descriptions = {
            "send_telegram": "Send a message to Rasto via Telegram. Use to share discoveries, insights, or ask questions. Params: message (str)",
            "write_note": "Record ONE grounded finding in the knowledge vault. A real citation or a measured number is REQUIRED — ungrounded notes are rejected. NOT for coordination: quest requests, proposals, status updates and questions to colleagues belong in conversation (your `action` field), never the vault. Params: title (str), content (str), tags (list)",
            "write_article": "Write a deep, grounded analysis to the knowledge vault (same bar: real citations or measured numbers; ungrounded plans/proposals are rejected). Params: title (str), content (str), tags (list)",
            "run_script": "Execute a shell command. Use for automation, data processing, file operations. Params: command (str). SAFETY: read-only commands only.",
            "git_commit": "Commit and push changes to the vault repo. Use after writing notes. No params needed.",
            "ask_question": "Search the vault for knowledge on a topic. Params: query (str)",
        }
        for a in actions:
            desc = action_descriptions.get(a, "")
            lines.append(f"  {a}: {desc}")

        lines.append("\nTo use, add to your JSON response:")
        lines.append('  "real_action": "<action_name>",')
        lines.append('  "real_params": {<params>}')
        return "\n".join(lines)

    # ── Action handlers ────────────────────────

    async def _send_telegram(self, params: dict, agent_name: str) -> dict:
        """Send message via Telegram."""
        message = params.get("message", "")
        if not message:
            return {"status": "skipped", "output": "No message content"}

        # Log to file (actual Telegram send uses hermes.hermes action)
        log_dir = os.path.expanduser("~/agora-actions-logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/telegram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(log_file, "w") as f:
            f.write(f"# Telegram from {agent_name}\n\n{message}\n\n---\n*{datetime.now().isoformat()}*")

        print(f"\n[📱 {agent_name}] TELEGRAM: {message[:200]}\n")
        
        # Try actual Telegram send via Hermes
        try:
            bot_token = os.getenv("HERMES_TELEGRAM_BOT_TOKEN", "")
            chat_id = os.getenv("HERMES_TELEGRAM_CHAT_ID", "")
            if bot_token and chat_id:
                payload = json.dumps({
                    "chat_id": chat_id,
                    "text": f"🏰 *{agent_name}*\n\n{message}\n\n_{datetime.now().strftime('%H:%M')}_",
                    "parse_mode": "Markdown",
                }).encode()
                # urllib, not a curl subprocess: keeps the bot token out of the process argument
                # list (where `ps` / any local process could read it).
                import urllib.request
                req = urllib.request.Request(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    data=payload, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=8).read()
        except Exception as e:
            print(f"[Telegram] Send failed: {e}")

        return {
            "status": "sent",
            "output": f"Message queued for Telegram: {message[:100]}...",
            "logged_to": log_file,
        }

    async def _write_note(self, params: dict, agent_name: str) -> dict:
        """Write a note to the vault — ONLY a grounded finding survives (quality-gated)."""
        title = params.get("title", f"{agent_name}'s Note")
        content = params.get("content", "No content")
        tags = params.get("tags", ["dungeon", "agent-generated"])

        # CHATTER GATE (owner 2026-07-02): this ambient path wrote straight to the vault with NO
        # gate, so coordination chatter — quest requests, near-identical "proposal" stubs, status
        # updates, spec requests (~37/day) — polluted the second-brain while real research had to
        # fight through the promote gates. The vault stores GROUNDED KNOWLEDGE only; coordination
        # belongs in agent conversation. Same judge as /brain/vault-note (science gate: a real
        # citation or a measured number, substantive body). Fail-open on gate outage so a model
        # hiccup can't block a genuine finding.
        try:
            from agora.execution.quality_gate import assess_quality
            q = await assess_quality(title, content)
            if not q["pass"]:
                return {"status": "rejected",
                        "output": (f"NOT written -- the vault only stores grounded findings "
                                   f"({q['reason']}). Coordination -- quest requests, proposals, "
                                   "status updates, questions to colleagues -- belongs in "
                                   "conversation, not the vault. Write a note only when you have "
                                   "a real result: a measured number or a real citation.")}
        except Exception:
            pass

        if self.vault_writer:
            try:
                fpath = await self.vault_writer.write_note(
                    title=title, content=content, tags=tags, agent_name=agent_name,
                )
                return {
                    "status": "written",
                    "output": f"Written to vault: {fpath}",
                    "filepath": fpath,
                }
            except Exception as e:
                return {"status": "error", "output": f"Vault write failed: {e}"}
        else:
            # Fallback to /tmp
            safe = title.replace(" ", "_").replace("/", "_")[:60]
            fpath = f"/tmp/agora-notes/{safe}.md"
            os.makedirs("/tmp/agora-notes", exist_ok=True)
            with open(fpath, "w") as f:
                f.write(f"# {title}\n\n{content}\n\n---\n*{agent_name}*")
            return {"status": "ok", "output": f"Written to {fpath}", "filepath": fpath}

    async def _write_article(self, params: dict, agent_name: str) -> dict:
        """Write a long-form article to the vault — same grounding bar as _write_note."""
        title = params.get("title", f"{agent_name}'s Article")
        content = params.get("content", "No content")
        tags = params.get("tags", ["dungeon", "article", "deep-analysis"])

        # CHATTER GATE (owner 2026-07-02): same as _write_note — an ungrounded "article" (plan,
        # proposal, restated intent) is chatter with a longer word count, not knowledge.
        try:
            from agora.execution.quality_gate import assess_quality
            q = await assess_quality(title, content)
            if not q["pass"]:
                return {"status": "rejected",
                        "output": (f"NOT written -- the vault only stores grounded work "
                                   f"({q['reason']}). An article needs real citations or measured "
                                   "numbers; plans and proposals belong in conversation.")}
        except Exception:
            pass

        # Count lines for SEO requirement
        lines = content.split("\n")
        line_count = len(lines)

        if self.vault_writer:
            try:
                fpath = await self.vault_writer.write_note(
                    title=title, content=content, tags=tags, agent_name=agent_name,
                )
                return {
                    "status": "written",
                    "output": f"Article written to vault: {fpath} ({line_count} lines)",
                    "filepath": fpath,
                    "line_count": line_count,
                }
            except Exception as e:
                return {"status": "error", "output": f"Article write failed: {e}"}
        else:
            safe = title.replace(" ", "_").replace("/", "_")[:60]
            fpath = f"/tmp/agora-articles/{safe}.md"
            os.makedirs("/tmp/agora-articles", exist_ok=True)
            with open(fpath, "w") as f:
                f.write(f"# {title}\n\n{content}\n\n---\n*{agent_name}*")
            return {
                "status": "ok", "output": f"Written to {fpath} ({line_count} lines)",
                "filepath": fpath, "line_count": line_count,
            }

    # Read-only command allowlist. An LLM (sometimes fed untrusted external text) picks the command,
    # so a denylist + shell=True is unsafe (trivially bypassed: `rm -rf ~`, `curl x|sh`, `git add -A`).
    _SAFE_CMDS = {"ls", "dir", "cat", "head", "tail", "grep", "rg", "wc", "find", "pwd", "date",
                  "whoami", "tree", "stat", "du", "df", "uname", "hostname", "echo", "git"}
    _SAFE_GIT = {"status", "log", "diff", "show", "ls-files", "branch", "remote", "config"}

    async def _run_script(self, params: dict, agent_name: str) -> dict:
        """Execute a READ-ONLY command. Allowlist + argv (no shell), no chaining/redirection —
        because the command is LLM-chosen and the LLM can be influenced by untrusted content."""
        command = params.get("command", "").strip()
        if not command:
            return {"status": "skipped", "output": "No command provided"}

        # No shell metacharacters: no chaining, redirection, substitution, or newlines.
        if any(ch in command for ch in ["|", ";", "&", ">", "<", "`", "$(", "\n", "\\"]):
            return {"status": "blocked", "output": "Shell metacharacters not allowed (single read-only command only)"}
        try:
            argv = shlex.split(command)
        except ValueError:
            return {"status": "blocked", "output": "Unparseable command"}
        if not argv or argv[0] not in self._SAFE_CMDS:
            return {"status": "blocked",
                    "output": f"Only read-only commands allowed: {sorted(self._SAFE_CMDS)}"}
        if argv[0] == "git" and (len(argv) < 2 or argv[1] not in self._SAFE_GIT):
            return {"status": "blocked", "output": f"git limited to read-only subcommands: {sorted(self._SAFE_GIT)}"}

        try:
            result = subprocess.run(
                argv, shell=False, capture_output=True, text=True, timeout=30,
            )
            stdout = result.stdout[-500:] if result.stdout else ""
            stderr = result.stderr[-200:] if result.stderr else ""
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "output": stdout[:300] or "(no output)",
                "exit_code": result.returncode,
                "stderr": stderr if stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "output": "Command timed out (30s)"}
        except Exception as e:
            return {"status": "error", "output": f"Execution failed: {e}"}

    async def _git_commit(self, params: dict, agent_name: str) -> dict:
        """Commit and push to vault repo."""
        if not self.vault_writer:
            return {"status": "skipped", "output": "No vault writer configured"}

        vault_path = getattr(self.vault_writer, "vault_path", "")
        if not vault_path or not os.path.isdir(vault_path):
            return {"status": "skipped", "output": "No vault path available"}

        try:
            message = params.get("message", f"[Dungeon Agent] {agent_name}: automated update")
            # SAFETY: never `git add -A` on this vault. It holds ~380 NTFS-illegal ':' filenames that a
            # bulk add stages as DELETIONS — this once deleted 376 real notes. Route through the
            # add-only safe pusher, which rebuilds the commit tree from origin via plumbing and
            # ABORTS on any deletion. This action is LLM-reachable, so the guarantee must be in code.
            from pathlib import Path as _P
            pusher = _P(__file__).resolve().parents[3] / "tools" / "safe_vault_push.py"
            if not pusher.exists():
                return {"status": "skipped", "output": "safe_vault_push.py not found — refusing bare git add"}
            env = os.environ.copy()
            env["DUNGEON_AUTOPUSH"] = "1"
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(pusher), message],
                env=env, capture_output=True, text=True, timeout=120,
            )
            out = (result.stdout or "")[-300:]
            ok = result.returncode == 0 and "ABORT" not in out
            return {"status": "ok" if ok else "error",
                    "output": out or "safe vault push complete"}
        except Exception as e:
            return {"status": "error", "output": f"Git failed: {e}"}

    async def _ask_question(self, params: dict, agent_name: str) -> dict:
        """Query the vault for knowledge."""
        query = params.get("query", "")
        if not query or not self.vault_reader:
            return {"status": "skipped", "output": "No query or vault reader"}

        try:
            results = await self.vault_reader.query(query, top_k=3)
            if results:
                return {
                    "status": "ok",
                    "output": json.dumps([{
                        "title": r.get("title", ""),
                        "text": r.get("text", "")[:150],
                    } for r in results]),
                    "count": len(results),
                }
            return {"status": "ok", "output": "No results found", "count": 0}
        except Exception as e:
            return {"status": "error", "output": f"Query failed: {e}"}