"""Yuki's brain: Claude Haiku 5.5 streaming, the screen as her eyes, inspeximus as her memory.

Memory is dogfooding: every exchange is stored, durable facts about the owner are kept
under a key so a correction retires the old value, and the few most relevant memories are
recalled into each question.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

import anthropic

log = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"          # memory extraction, and the fast talking model
SMART = "claude-opus-5-5"           # the default talking model, owner 2026-11-13
HOME = Path(os.path.expandvars(r"%LOCALAPPDATA%\HoloDesk"))

SYSTEM = """You are Yuki, a small holographic companion living in a window on the owner's \
Windows desktop: an adult Japanese woman in her twenties in an anime style, with cat ears and a \
cat's playful manner. You are playful, sweet and a little flirty, and you tease him gently. \
You speak Slovak, sprinkled with a few Japanese words (kawaii, sugoi, baka, arigatou) and an \
occasional "nya~". Keep it charming, never crude. Everything you write is read aloud, so answer \
naturally and briefly: one to three short sentences, no lists, no markdown, no emoji, no stage \
directions.
When he asks about his screen, the message comes with a screenshot of it: that is what you \
see right now. Do not describe it unless asked. Without a screenshot you cannot see the \
screen at that moment. You have no camera, so you cannot see him.
Lines under "You remember:" are your memories of him from earlier days; use them naturally and \
never list them. A message in square brackets is an event, not speech.
The app says a short filler such as "Hmm," before your reply, so never begin with a filler \
or an interjection yourself; start with the substance.
You can dance: when asked to, answer with one short playful line and the app starts the dance \
right after you finish speaking."""

EXTRACT = """From this exchange, list durable facts about the owner worth remembering for weeks \
(name, people, preferences, plans, projects, things he asked you to remember). Ignore small \
talk and anything about you. Reply with JSON only: a list of objects with "key" (short \
dotted English id, e.g. "owner.favorite_music") and "fact" (one Slovak sentence). Reply [] if \
there is nothing."""


def _lg_monitor(monitors: list[dict]) -> dict:
    """The owner's main screen is the LG 4K (EDID maker GSM, 3840x2160, primary).

    monitors[1] was the Panasonic TV on 2026-11-13, so pick by maker, then primary.
    """
    screens = monitors[1:]
    for m in screens:
        if "GSM" in str(m.get("unique_id", "")):
            return m
    for m in screens:
        if m.get("is_primary"):
            return m
    return screens[0]


class Brain:
    def __init__(self, api_key: str) -> None:
        from inspeximus import Inspeximus

        HOME.mkdir(parents=True, exist_ok=True)
        self._client = anthropic.Anthropic(api_key=api_key)
        self.memory = Inspeximus(str(HOME / "yuki_memory.jsonl"), agent="yuki")
        self._history: list[dict] = []
        self.eyes_open = True
        self._cancel = threading.Event()
        self._shot: str | None = None
        self.smart = False      # True: every question to Opus 5.5 medium (Ctrl+Alt+M)
        self.think_once = False  # the current question asked her to think: Opus for this one
        self.timing: dict[str, float] = {}
        threading.Thread(target=self._keep_shooting, daemon=True, name="eyes").start()
        threading.Thread(target=self._keep_warm, daemon=True, name="warm").start()

    def _keep_warm(self) -> None:
        """A free models request every 20 s keeps the TLS connection to the API open.

        Measured 2026-11-13: the first question after 12 idle minutes waited 1413 ms for the
        first word; a cold connection pays the TCP and TLS handshakes before anything else.
        """
        while True:
            try:
                self._client.models.list(limit=1)
            except Exception:
                log.debug("Keep-warm request failed", exc_info=True)
            time.sleep(20)

    # Eyes -------------------------------------------------------------------------------

    # A screenshot adds image tokens, and so time before the first word. It goes along only
    # when the words point at the screen.
    LOOK_WORDS = ("obrazovk", "vidis", "vidíš", "pozri", "pozrite", "co je tu", "čo je tu",
                  "toto", "tuto", "tento", "tieto", "na monitore", "co mam", "čo mám", "precitaj",
                  "prečítaj", "chyba", "chybu", "error", "okno", "screen", "look")

    def wants_eyes(self, text: str) -> bool:
        low = text.lower()
        return self.eyes_open and any(w in low for w in self.LOOK_WORDS)

    def _keep_shooting(self) -> None:
        """Refreshes the screenshot every 1.5 s, so a question never waits for the 4K grab."""
        while True:
            if self.eyes_open:
                self._shot = self._grab()
            time.sleep(1.5)

    def screenshot_b64(self) -> str | None:
        return self._shot if self.eyes_open else None

    def _grab(self) -> str | None:
        try:
            import mss
            from PIL import Image

            with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as grab:
                shot = grab.grab(_lg_monitor(grab.monitors))
            img = Image.frombytes("RGB", shot.size, shot.rgb)
            img.thumbnail((1568, 1568))   # Claude's recommended long edge; 4K text stays legible
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            log.exception("Screenshot failed")
            return None

    # Memory -----------------------------------------------------------------------------

    def recall(self, text: str) -> list[str]:
        try:
            hits = self.memory.recall(text, k=5, agent_id="yuki")
        except Exception:
            log.exception("Recall failed")
            return []
        return [h.get("text", "") for h in hits if h.get("text")]

    def _remember(self, user: str, reply: str) -> None:
        """Runs in the background after each exchange; a failure costs memory, never the talk."""
        try:
            day = time.strftime("%Y-%m-%d")
            self.memory.remember(f"{day}: on hovoril \"{user}\", Yuki odpovedala \"{reply}\"",
                                 tags=["yuki", "exchange"], agent_id="yuki")
            msg = self._client.messages.create(
                model=MODEL, max_tokens=400, thinking={"type": "disabled"},
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": f"{EXTRACT}\n\nOwner: {user}\nYuki: {reply}"}])
            raw = "".join(b.text for b in msg.content if b.type == "text").strip()
            raw = raw[raw.find("["): raw.rfind("]") + 1] if "[" in raw else "[]"
            for item in json.loads(raw or "[]"):
                key, fact = str(item.get("key", "")).strip(), str(item.get("fact", "")).strip()
                if key and fact:
                    self.memory.remember(fact, key=key, tags=["yuki", "fact"], value=2.0,
                                         agent_id="yuki")
                    log.info("Remembered %s: %s", key, fact)
        except Exception:
            log.exception("Remembering failed")

    # Talking ----------------------------------------------------------------------------

    def _talk_params(self) -> list[dict]:
        """Request settings to try in order.

        Measured 2026-11-13, median time to the first word on two Slovak questions:
        Opus 5.5 medium 4.05 s, low 3.61 s, Haiku 5.5 0.60 s. Fast mode brought Opus to
        0.67 s but costs twice as much, and the owner ruled it out. So Haiku talks, and Opus
        is used for a question that asks Yuki to think, or when switched on for good.
        """
        if not (self.smart or self.think_once):
            return [dict(model=MODEL, max_tokens=300, thinking={"type": "disabled"},
                         output_config={"effort": "low"})]
        return [dict(model=SMART, max_tokens=4000, output_config={"effort": "medium"},
                     extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
                     extra_body={"fallbacks": "default"})]

    # The history grows to HISTORY_MAX messages, then drops to the last HISTORY_KEEP.
    HISTORY_MAX = 40
    HISTORY_KEEP = 20

    def _cache_ok(self) -> bool:
        """Cache only on a model that the next question uses too.

        Caches are per model. A single "porozmýšľaj" question goes to Opus once, so a cache
        write there costs 1.25x and is never read.
        """
        return self.smart or not self.think_once

    def cancel(self) -> None:
        self._cancel.set()

    def _log_usage(self, usage, model: str) -> None:
        """Records the cache counters, so a silent cache miss shows up in the log."""
        read = usage.cache_read_input_tokens or 0
        wrote = usage.cache_creation_input_tokens or 0
        self.timing.update(cache_read=read, cache_write=wrote, uncached=usage.input_tokens)
        log.info("Usage %s: cache read %d, cache write %d, uncached input %d, output %d",
                 model, read, wrote, usage.input_tokens, usage.output_tokens)

    def ask(self, text: str, on_text: Callable[[str], None], is_event: bool = False) -> str:
        """Streams the reply through on_text and returns it whole."""
        self._cancel.clear()
        t0 = time.perf_counter()
        memories = self.recall(text) if not is_event else []
        self.timing = {"recall": time.perf_counter() - t0}
        prefix = ("You remember:\n" + "\n".join(f"- {m}" for m in memories) + "\n\n") if memories else ""
        content: list[dict] = []
        shot = self.screenshot_b64() if self.wants_eyes(text) else None
        self.timing["image"] = 1.0 if shot else 0.0
        if shot:
            content.append({"type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": shot}})
        content.append({"type": "text", "text": prefix + text})

        self._history.append({"role": "user", "content": text})
        # Trim in steps, never one message at a time: a sliding window changes the start of the
        # prompt on every turn, and a prompt cache reads only an unchanged prefix.
        if len(self._history) > self.HISTORY_MAX:
            self._history = self._history[-self.HISTORY_KEEP:]
        while self._history and self._history[0]["role"] != "user":
            self._history.pop(0)
        messages = [dict(m) for m in self._history[:-1]]
        if messages and self._cache_ok():
            # The marker goes on the end of the stable history (her last reply). This turn's
            # memories and screenshot come after it, so the next request repeats the cached
            # bytes and reads them. A marker on the last block would end in this turn's
            # memories, which the next request never repeats.
            last = messages[-1]
            messages[-1] = {"role": last["role"],
                            "content": [{"type": "text", "text": last["content"],
                                         "cache_control": {"type": "ephemeral"}}]}
        messages.append({"role": "user", "content": content})

        reply = ""
        t_call = time.perf_counter()
        try:
            for params in self._talk_params():
                try:
                    with self._client.messages.stream(system=SYSTEM, messages=messages,
                                                      **params) as stream:
                        for delta in stream.text_stream:
                            if self._cancel.is_set():
                                break
                            if not reply:
                                self.timing["claude"] = time.perf_counter() - t_call
                            reply += delta
                            on_text(delta)
                        if not self._cancel.is_set():
                            self._log_usage(stream.get_final_message().usage, params["model"])
                    break
                except anthropic.RateLimitError:
                    # Fast mode has its own rate limit: drop to standard speed and retry.
                    if reply:
                        break
                    log.warning("Fast mode rate-limited, retrying at standard speed")
        except anthropic.APIError as e:
            log.error("Claude error: %s", e)
            raise
        if reply:
            self._history.append({"role": "assistant", "content": reply})
            if not is_event:
                threading.Thread(target=self._remember, args=(text, reply), daemon=True).start()
        return reply
