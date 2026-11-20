"""Wires Yuki together: window, ears, brain, voice, dance."""

from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
import unicodedata

from .brain import Brain
from .ears import Ears, Hearing
from .voice import Voice

log = logging.getLogger(__name__)

WAKE = ("yuki", "juki", "yuky", "juky", "jucky", "joki", "yukki", "jukki")
DANCE_WORDS = ("tancuj", "tanec", "tancova", "dance")
FOLLOW_UP_S = 8.0
DANCES = ("englishdance", "bhangradance")
FILLERS = ("Hmm,", "Nya,", "Ehm,", "Hmm, počkaj,", "Áno,")
THINK_WORDS = ("porozmysl", "zamysli", "pouvazuj", "premysli", "rozmyslaj")   # plain, no accents


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


class SentenceSplitter:
    """The first chunk ends at the first comma, or at a space once 40 characters are in, so
    the voice starts on the first clause instead of the first full sentence."""

    def __init__(self) -> None:
        self.buffer = ""
        self.emitted = False

    def feed(self, text: str) -> list[str]:
        self.buffer += text
        out = []
        if not self.emitted:
            m = re.search(r"[,;:]\s", self.buffer)
            if m is None and len(self.buffer) >= 40:
                m = re.search(r"\s(?=\S*$)", self.buffer)
            if m:
                out.append(self.buffer[: m.end()])
                self.buffer = self.buffer[m.end():]
                self.emitted = True
        while m := re.search(r"[.!?…]+[\"”»)]?\s", self.buffer):
            out.append(self.buffer[: m.end()])
            self.buffer = self.buffer[m.end():]
            self.emitted = True
        return out

    def flush(self) -> str:
        rest, self.buffer = self.buffer, ""
        return rest


class Yuki:
    def __init__(self, window, api_key: str) -> None:
        self.window = window
        self.brain = Brain(api_key)
        self.voice = Voice(on_start=self._voice_started, on_idle=self._voice_idle)
        self.ears: Ears | None = None
        self.follow_until = 0.0
        self.thinking = False
        self.dancing = False
        self.dance_until = 0.0
        self.dance_after = False
        self.dance_index = 0
        self.music_votes = 0
        self.quiet_votes = 0
        self.hearing: Hearing | None = None
        self.heard = ""
        self.reply = ""
        self.timing = ""
        self._last_level = 0.0

    # Window -----------------------------------------------------------------------------

    def js(self, code: str) -> None:
        try:
            self.window.evaluate_js(code)
        except Exception:
            log.debug("evaluate_js failed", exc_info=True)

    def play(self, clip: str, speed: float = 1.0) -> None:
        self.js(f"window.yuki.play({json.dumps(clip)}, {speed:.3f})")

    def status(self) -> None:
        lines = []
        if self.thinking:
            lines.append("...")
        elif time.time() < self.follow_until:
            lines.append("Listening")
        else:
            lines.append('Say "Yuki ..."  ' + ("Opus 5.5" if self.brain.smart else "Haiku 5.5, Opus on 'porozmýšľaj'")
                         + ("" if self.brain.eyes_open else "  (eyes closed)"))
        if self.heard:
            lines.append(f"You: {self.heard}")
        if self.reply:
            lines.append(f"Yuki: {self.reply}")
        if self.timing:
            lines.append(self.timing)
        if getattr(self, "first_voice", ""):
            lines.append(self.first_voice)
        if self.hearing and (self.dancing or self.hearing.is_music):
            h = self.hearing
            lines.append(f"ear {h.level_db:.0f} dB, beat {h.beat:.2f}, {h.bpm:.0f} BPM"
                         + (" - dancing" if self.dancing else ""))
        self.js(f"window.yuki.status({json.dumps(chr(10).join(lines))})")

    # Start ------------------------------------------------------------------------------

    def start(self) -> None:
        self.js("window.yuki.status('Loading the ears (Whisper on the GPU)...')")
        self.ears = Ears(on_utterance=self.on_utterance, on_level=self.on_level,
                         on_hearing=self.on_hearing)
        self.ears.start()
        self.status()
        threading.Thread(target=self._tick, daemon=True, name="tick").start()

    def _tick(self) -> None:
        while True:
            time.sleep(1)
            if self.dancing and self.dance_until and time.time() > self.dance_until:
                self.stop_dance()
            self.status()

    def on_level(self, level: float) -> None:
        now = time.time()
        if now - self._last_level > 0.1:
            self._last_level = now
            self.js(f"window.yuki.level({level:.2f})")

    # Hearing ----------------------------------------------------------------------------

    def listen_now(self) -> None:
        """Hotkey: talk without saying the name."""
        self.follow_until = time.time() + FOLLOW_UP_S
        self.play("listening1")
        self.status()

    def on_utterance(self, text: str, t_end: float = 0.0, stt_s: float = 0.0) -> None:
        if self.thinking or self.voice.busy:
            return
        self.t_end, self.stt_s = t_end or time.perf_counter(), stt_s
        plain = _plain(text)
        words = re.findall(r"\w+", plain)
        called = bool(words) and any(words[0].startswith(w) or (len(words) > 1 and words[1].startswith(w))
                                     for w in WAKE)
        if not called and time.time() > self.follow_until:
            log.info("Ignored (no wake word): %s", text)
            return
        if called:
            # Drop the name itself: "Yuki, aký je dnes deň?" -> "aký je dnes deň?"
            text = re.sub(r"^\W*\w+\W*(?=\w)", "", text, count=1) if words[0].startswith(WAKE) else text
            if len(words) <= 1:
                self.heard = text
                self.listen_now()
                return
        self.heard = text.strip()
        self.first_voice = ""
        self.dance_after = any(w in plain for w in DANCE_WORDS)
        threading.Thread(target=self._ask, args=(self.heard,), daemon=True).start()

    def _ask(self, text: str, is_event: bool = False) -> None:
        self.thinking = True
        self.stop_dance(quiet=True)
        self.reply = ""
        self.play("thinking1")
        self.status()
        self.brain.think_once = not is_event and any(w in _plain(text) for w in THINK_WORDS)
        if not is_event:
            # Say something at once, locally, while Claude writes: the first sound comes from
            # Piper in about 0.2 s instead of waiting for the first word from the API.
            slow = self.brain.think_once or self.brain.smart
            self.voice.say("Hmm, nechaj ma porozmýšľať," if slow else random.choice(FILLERS))
        splitter = SentenceSplitter()
        started = time.perf_counter()
        first = []

        def on_text(delta: str) -> None:
            if not first:
                first.append(time.perf_counter() - started)
            self.reply += delta
            for s in splitter.feed(delta):
                self.voice.say(s)
            self.status()

        try:
            self.brain.ask(text, on_text, is_event=is_event)
        except Exception as e:
            self.reply = f"ERROR: {e}"
        self.voice.say(splitter.flush())
        self.thinking = False
        t = self.brain.timing
        self.timing = (f"heard {self.stt_s * 1000:.0f} · memory {t.get('recall', 0) * 1000:.0f}"
                       f" · claude {t.get('claude', 0) * 1000:.0f}"
                       f"{' +screen' if t.get('image') else ''} ms")
        log.info("Timing: %s", self.timing)
        if not self.voice.busy:
            self._voice_idle()
        self.status()

    # Voice ------------------------------------------------------------------------------

    def _voice_started(self) -> None:
        if self.ears:
            self.ears.muted = True
        self.play("talking1")
        total = time.perf_counter() - getattr(self, "t_end", time.perf_counter())
        log.info("First voice %.0f ms after the end of speech", total * 1000)
        self.first_voice = f"voice after {total * 1000:.0f} ms"

    def _voice_idle(self) -> None:
        if self.thinking:
            return

        def unmute():
            time.sleep(0.3)   # let the room echo die before listening again
            if self.ears and not self.voice.busy:
                self.ears.muted = False

        threading.Thread(target=unmute, daemon=True).start()
        self.follow_until = time.time() + FOLLOW_UP_S
        if self.dance_after:
            self.dance_after = False
            self.start_dance(None, 20)
        elif not self.dancing:
            self.play("idle1")
        self.status()

    # Dance ------------------------------------------------------------------------------

    def start_dance(self, bpm: float | None, seconds: float) -> None:
        speed = min(1.25, max(0.8, bpm / 120)) if bpm else 1.0
        if not self.dancing:
            self.dance_index = (self.dance_index + 1) % len(DANCES)
        self.dancing = True
        self.dance_until = time.time() + seconds if seconds else 0.0
        self.play(DANCES[self.dance_index], speed)

    def stop_dance(self, quiet: bool = False) -> None:
        if not self.dancing:
            return
        self.dancing = False
        if not quiet:
            self.play("idle1")

    def on_hearing(self, h: Hearing) -> None:
        self.hearing = h
        if self.thinking or self.voice.busy:
            self.music_votes = 0
            return
        if h.is_music:
            self.music_votes += 1
            self.quiet_votes = 0
        else:
            self.quiet_votes += 1
            self.music_votes = 0
        if not self.dancing and self.music_votes >= 3:
            self.start_dance(h.bpm, 0)
        elif self.dancing and not self.dance_until and h.is_music:
            self.play(DANCES[self.dance_index], min(1.25, max(0.8, h.bpm / 120)))
        if self.dancing and not self.dance_until and self.quiet_votes >= 4:
            self.stop_dance()

    # Hotkeys ----------------------------------------------------------------------------

    def toggle_model(self) -> None:
        self.brain.smart = not self.brain.smart
        self.status()

    def toggle_eyes(self) -> None:
        self.brain.eyes_open = not self.brain.eyes_open
        self.status()
