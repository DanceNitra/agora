"""Hermes actions — communication, messaging, notifications.

Real actions that Hermes can execute:
  - send_message: Send a message via Telegram Bot API
  - deliver: Route a message to a specific recipient
  - broadcast: Send to all agents / home channel
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Optional


# Telegram Bot API base
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


async def _send_telegram(config: dict, chat_id: str, message: str) -> bool:
    """Send a message via the Telegram Bot API.

    urllib in a worker thread, NOT a curl subprocess. The old version put the bot token into the
    curl argv, where `ps` -- or Get-CimInstance Win32_Process on Windows, no elevation needed --
    hands it to any local process. Whoever holds that token can read the owner's entire
    control-plane chat via getUpdates, consume updates before our poller sees them, and send
    messages that appear to come from us.

    The docstring this replaces said subprocess was used "to avoid asyncio event-loop conflicts".
    That was wrong twice over: `subprocess.run` inside an `async def` blocks the loop exactly as a
    blocking socket would. `asyncio.to_thread` is the answer to both problems.
    """
    bot_token = (
        config.get("telegram_bot_token")
        or os.getenv("HERMES_TELEGRAM_BOT_TOKEN")
    )
    if not bot_token:
        print("[Hermes] No telegram_bot_token configured — skipping real send")
        return False

    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode()
    url = TELEGRAM_API.format(token=bot_token)

    def _post() -> bool:
        try:
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=8).read().decode(
                "utf-8", "replace"))
            if resp.get("ok"):
                msg_id = resp.get("result", {}).get("message_id", "?")
                print(f"[Hermes] Telegram sent to {chat_id} (msg #{msg_id})")
                return True
            print(f"[Hermes] Telegram API error: {resp}")
            return False
        except Exception as e:
            print(f"[Hermes] Telegram send exception: {e}")
            return False

    return await asyncio.to_thread(_post)


async def _build_report_message(title: str, quest: dict, message: str) -> str:
    """Build a structured report message."""
    subsystem = quest.get("subsystem", "").upper()
    reward = quest.get("reward", 0)
    owner = quest.get("owner", "unassigned")
    status = quest.get("status", "active")
    quest_id = quest.get("id", "unknown")

    lines = [
        f"📨 **{title}**",
        f"_{subsystem} · {owner} · Q:{quest_id}_",
        "",
        message,
        "",
        f"├ Status: {status}",
        f"├ Reward: {reward} pts",
        f"└ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return "\n".join(lines)


async def action_send_message(config: dict, quest: dict, params: dict) -> dict:
    """Send a message via Telegram Bot API.

    Uses:
      - config['telegram_bot_token'] or $HERMES_TELEGRAM_BOT_TOKEN
      - config['telegram_chat_id'] or $HERMES_TELEGRAM_CHAT_ID
    """
    message = params.get("message") or quest.get("goal", "No message content")
    title = params.get("title") or quest.get("title", "Hermes Report")
    channel = params.get("channel", "telegram")
    chat_id = (
        params.get("chat_id")
        or config.get("telegram_chat_id")
        or os.getenv("HERMES_TELEGRAM_CHAT_ID")
    )
    recipient = params.get("recipient") or chat_id or "console"

    # Build message
    full_message = await _build_report_message(title, quest, message)

    outputs = []
    sent = False

    # Real Telegram send
    if channel in ("auto", "telegram") and chat_id and chat_id != "console":
        sent = await _send_telegram(config, chat_id, full_message)
        if sent:
            outputs.append(f"Sent to Telegram chat {chat_id}")
        else:
            outputs.append("Telegram send failed (see log)")

    # Always write to log file
    log_dir = config.get("log_dir", "/tmp/hermes-logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/{quest.get('id', 'unknown')}.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(full_message)
    outputs.append(f"Logged to {log_file}")

    # Console fallback if Telegram failed (guard against cp1252 consoles on Windows)
    if not sent:
        try:
            print(f"\n[Hermes] {full_message}\n")
        except UnicodeEncodeError:
            print(f"\n[Hermes] {full_message.encode('ascii', 'replace').decode()}\n")
        outputs.append("Console output")

    return {
        "status": "ok" if sent else "degraded",
        "output": "; ".join(outputs),
        "delivered_to": recipient,
        "telegram_sent": sent,
        "message_length": len(full_message),
    }


async def action_broadcast(config: dict, quest: dict, params: dict) -> dict:
    """Broadcast a message — sends to the configured chat."""
    p = dict(params or {})
    p.setdefault("channel", "telegram")
    p["message"] = f"📢 *Broadcast*\n\n{p.get('message', quest.get('goal', ''))}"
    return await action_send_message(config, quest, p)


async def action_deliver(config: dict, quest: dict, params: dict) -> dict:
    """Deliver a specific message to a recipient."""
    p = dict(params or {})
    if "recipient" not in p:
        p["recipient"] = quest.get("owner", "unknown")
    p.setdefault("channel", "telegram")
    p["message"] = (
        f"📬 *Message for {p['recipient']}*\n\n"
        f"{p.get('message', quest.get('goal', 'No message'))}"
    )
    return await action_send_message(config, quest, p)
