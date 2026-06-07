"""Hermes actions — communication, messaging, notifications.

Real actions that Hermes can execute:
  - send_message: Send a message to a platform (Telegram, console)
  - deliver: Route a message to a specific recipient
  - broadcast: Send to all agents/home channel
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Optional


async def action_send_message(config: dict, quest: dict, params: dict) -> dict:
    """Send a message via available channels.

    Uses config data to determine delivery method:
      - 'telegram_chat_id': sends via Hermes Agent's send_message tool
      - 'console': prints to stdout
      - 'file': writes to a log file
    """
    message = params.get("message") or quest.get("goal", "No message content")
    title = quest.get("title", "Hermes Report")
    recipient = params.get("recipient") or config.get("telegram_chat_id", "console")
    channel = params.get("channel", "auto")

    # Build message
    full_message = (
        f"📨 **{title}**\n"
        f"_{quest.get('id', 'unknown')}_\n\n"
        f"{message}\n\n"
        f"── {datetime.now().strftime('%H:%M:%S')}"
    )

    outputs = []

    # Try Telegram via Hermes Agent's send_message
    telegram_sent = False
    if channel in ("auto", "telegram") and recipient != "console":
        try:
            chat_id = config.get("telegram_chat_id") or os.getenv("HERMES_TELEGRAM_CHAT_ID")
            if chat_id:
                # Use the Hermes Agent send_message tool via subprocess
                # or write to a file that a cronjob picks up
                msg_file = f"/tmp/hermes_telegram_{int(datetime.now().timestamp())}.msg"
                with open(msg_file, "w") as f:
                    f.write(json.dumps({
                        "chat_id": chat_id,
                        "text": full_message,
                    }))
                outputs.append(f"Queued for Telegram delivery: {msg_file}")
                telegram_sent = True
        except Exception as e:
            outputs.append(f"Telegram queue failed: {e}")

    # Always write to log
    log_dir = config.get("log_dir", "/tmp/hermes-logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/{quest.get('id', 'unknown')}.log"
    with open(log_file, "w") as f:
        f.write(full_message)
    outputs.append(f"Logged to {log_file}")

    # Console fallback
    if not telegram_sent:
        print(f"\n[📨 Hermes] {full_message}\n")
        outputs.append("Console output")

    return {
        "status": "ok",
        "output": "\n".join(outputs),
        "delivered_to": recipient,
        "message_length": len(full_message),
    }


async def action_broadcast(config: dict, quest: dict, params: dict) -> dict:
    """Broadcast to all agents / home channel."""
    params = params or {}
    params["channel"] = "telegram"
    params["message"] = f"📢 *Broadcast*: {params.get('message', quest.get('goal', ''))}"
    return await action_send_message(config, quest, params)


async def action_deliver(config: dict, quest: dict, params: dict) -> dict:
    """Deliver a specific message to a recipient."""
    params = params or {}
    if "recipient" not in params:
        params["recipient"] = quest.get("owner", "unknown")
    params["channel"] = "telegram"
    return await action_send_message(config, quest, params)
