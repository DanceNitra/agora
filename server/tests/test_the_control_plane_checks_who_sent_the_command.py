"""Telegram commands are authorised by SENDER, not only by chat membership.

WHY THIS FILE EXISTS. The only identity check in the entire control plane compared the CHAT id
against HERMES_TELEGRAM_CHAT_ID; `msg["from"]["id"]` was never read anywhere in telegram_bot.py.

For a 1:1 chat that is sound — chat.id equals the sole peer's user id, so the check IS a sender
allowlist. For a group it degrades to "is a member of that group", and a member holds
`approve <id>` (outward publication under our GitHub identity), `board <text>` (rewrites the
standing research priorities) and `cc <text>` (the Claude inbox, whose tasks Claude Code works with
full tool access on the repository). Group membership is granted socially and can be widened by
anyone with invite rights, with no code change and no audit trail.

Which configuration is live could not be settled from anything committed: the value is in a
gitignored .env, .env.example carries no CHAT_ID key, and no code path reads a group-specific field.
So the code does not guess — it reads `chat.type`, which Telegram sends on every message, and the
tests below pin both branches so the answer does not depend on knowing.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

spec = importlib.util.spec_from_file_location("telegram_bot_under_test",
                                              ROOT / "server/agora/execution/telegram_bot.py")
tg = importlib.util.module_from_spec(spec)
sys.modules["telegram_bot_under_test"] = tg
spec.loader.exec_module(tg)

CHAT = "-1001234567890"
OWNER = "777000111"


def _msg(chat_type: str, chat_id: str = CHAT, sender: str | None = OWNER) -> dict:
    m: dict = {"chat": {"id": int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id,
                        "type": chat_type}, "text": "board something"}
    if sender is not None:
        m["from"] = {"id": int(sender)}
    return m


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("HERMES_TELEGRAM_CHAT_ID", CHAT)
    monkeypatch.delenv("HERMES_TELEGRAM_ALLOWED_USER_IDS", raising=False)


# ------------------------------------------------------------------- the case that was dangerous
@pytest.mark.parametrize("kind", ["group", "supergroup"])
def test_a_group_chat_without_an_allowlist_refuses(kind):
    """The check proved membership, not identity. Refuse rather than trust — and say why, because a
    silent refusal of the owner's own command is its own outage."""
    ok, why = tg.sender_ok(_msg(kind))
    assert ok is False
    assert "only proves" in why and "HERMES_TELEGRAM_ALLOWED_USER_IDS" in why, why


@pytest.mark.parametrize("kind", ["group", "supergroup"])
def test_a_group_chat_with_the_owner_allowlisted_is_accepted(kind, monkeypatch):
    monkeypatch.setenv("HERMES_TELEGRAM_ALLOWED_USER_IDS", f"{OWNER}, 999")
    assert tg.sender_ok(_msg(kind))[0] is True


@pytest.mark.parametrize("kind", ["group", "supergroup"])
def test_another_group_member_is_refused_when_an_allowlist_exists(kind, monkeypatch):
    monkeypatch.setenv("HERMES_TELEGRAM_ALLOWED_USER_IDS", OWNER)
    ok, why = tg.sender_ok(_msg(kind, sender="424242"))
    assert ok is False and "424242" in why


# ------------------------------------------------------------------------- the case that was fine
def test_a_private_chat_still_works_with_no_configuration():
    """The half that keeps the owner's phone working. In a 1:1 chat the old check was already
    equivalent to a sender allowlist, so this must stay a no-op — a guard that locks the owner out
    of his own control plane is worse than the gap it closes."""
    assert tg.sender_ok(_msg("private"))[0] is True


def test_a_private_chat_still_honours_an_explicit_allowlist(monkeypatch):
    monkeypatch.setenv("HERMES_TELEGRAM_ALLOWED_USER_IDS", "999")
    assert tg.sender_ok(_msg("private"))[0] is False


# ---------------------------------------------------------------------------------- other traffic
def test_a_message_from_a_different_chat_is_silently_dropped():
    """Not our chat: refuse with no reason string, so a stranger's chat cannot make us emit."""
    ok, why = tg.sender_ok(_msg("private", chat_id="-100999"))
    assert ok is False and why == ""


def test_a_message_with_no_sender_is_refused_in_a_group(monkeypatch):
    """Channel posts carry no `from`. A missing sender must reject, not fall through."""
    monkeypatch.setenv("HERMES_TELEGRAM_ALLOWED_USER_IDS", OWNER)
    ok, why = tg.sender_ok(_msg("channel", sender=None))
    assert ok is False and "(none)" in why


def test_an_empty_update_is_refused():
    assert tg.sender_ok({})[0] is False


# ------------------------------------------------------------------------------- the wiring itself
def test_the_poll_loop_calls_the_check_rather_than_comparing_the_chat_id_inline():
    """The old comparison was one line in the loop. Pin the CALL, so a future edit cannot quietly
    reinstate a chat-only test."""
    src = (ROOT / "server/agora/execution/telegram_bot.py").read_text(encoding="utf-8")
    assert "ok, why = sender_ok(msg)" in src, "the poll loop no longer calls sender_ok"
    assert 'str(msg.get("chat", {}).get("id")) != str(_chat())' not in src, \
        "the inline chat-only check is back"
