"""
AI Customer-Support Agent — answers customer questions about a business, grounded ONLY in that
business's own content. If the answer isn't in the content, it says so and offers a human — it does
NOT make things up (the #1 thing that makes support bots unsafe to ship).

This is a portfolio/demo build for client work. It runs locally and free on Ollama (no API key); for
a client you swap one function to OpenAI/Anthropic. Zero dependencies beyond the stdlib + a local LLM.

Usage:
  python support_agent.py "what time do you open on sunday?"
  python support_agent.py                      # interactive
  python support_agent.py --content my_biz.txt "do you deliver?"
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

OLLAMA = "http://localhost:11434/api/chat"
MODEL = os.environ.get("SUPPORT_AGENT_MODEL", "qwen3-coder:30b")  # capable model REQUIRED: the 7B
# invented opening hours + a phone number on real content (breaks the no-hallucination guarantee).
# 30b runs locally and grounds reliably; for production swap ask_llm to Claude/GPT.
HERE = Path(__file__).resolve().parent
# Run telemetry -> consumed by services/reliability_receipt/receipt.py to bill the SLA.
RUN_LOG = Path(os.environ.get("SUPPORT_AGENT_LOG", HERE / "run_log.jsonl"))
VALUE_PER_RESOLVED = 6.0                    # $ of staff time saved per ticket the agent deflects
# A handoff = the agent safely escalated to a human (correct behaviour, but a human was needed).
_HANDOFF = re.compile(r"not sure|connect you|reach out|contact (?:us|our|the|them)|please contact|"
                      r"can'?t find|don'?t have|i don'?t see|not among|not listed|isn'?t listed|"
                      r"no (?:specific )?information|speak to|a human|our team|call us|email us|"
                      r"confirm (?:this|whether)", re.I)
_WORD = re.compile(r"[a-z0-9]{2,}")
_STOP = set("the a an of to in and or is are do you your we our for on at it with can i my me what "
            "when where how why does has have any".split())


def _toks(s):
    return {w for w in _WORD.findall(s.lower()) if w not in _STOP}


def load_chunks(path):
    """Split the business content into retrievable chunks (blank-line separated blocks)."""
    text = Path(path).read_text(encoding="utf-8")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return [(b, _toks(b)) for b in blocks]


def retrieve(question, chunks, k=3):
    """Top-k most relevant chunks by token overlap (lexical — fast, zero-dep, good at this scale)."""
    q = _toks(question)
    scored = sorted(((len(q & t), b) for b, t in chunks), key=lambda x: -x[0])
    return [b for s, b in scored[:k] if s > 0] or [b for b, _ in chunks[:k]]


def ask_llm(question, context, business="the business"):
    """Answer using ONLY the context. Returns {text, ok, error, latency_s}; ok=False on LLM failure."""
    system = (f"You are the friendly customer-support assistant for {business}. Answer ONLY from the "
              "CONTEXT below. CRITICAL: the CONTEXT is often INCOMPLETE (it may have no opening hours, no "
              "availability, or missing prices). If the answer is not EXPLICITLY written in the CONTEXT, "
              "you MUST NOT guess or state ANY specific value — never state hours, days, dates, prices, or "
              "any fact that is not literally in the CONTEXT. In that case say you don't have that detail "
              "on hand and give the phone/email (if present) so they can confirm. Do not invent anything. "
              "When asked whether you offer/have a specific service, treatment, or feature, answer YES only "
              "if it is EXPLICITLY listed in the CONTEXT; if it is not listed, do NOT assume you offer it - "
              "say it is not among the services listed and offer to confirm by phone/email. "
              "Be concise and warm.")
    payload = {"model": MODEL, "stream": False,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": f"CONTEXT:\n{context}\n\nCUSTOMER: {question}"}]}
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=120).read())
        return {"text": out["message"]["content"].strip(), "ok": True, "error": None,
                "latency_s": round(time.monotonic() - t0, 2)}
    except Exception as e:
        return {"text": f"[LLM unavailable] Please reach out to us directly and a human will help.",
                "ok": False, "error": f"LLM unavailable: {str(e)[:80]}",
                "latency_s": round(time.monotonic() - t0, 2)}


def _log_run(rec: dict) -> None:
    """Append one run record (the reliability_receipt schema) to the run log."""
    try:
        with open(RUN_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass                                   # telemetry must never break the agent


def answer(question, content_path=None, log=True):
    content_path = content_path or (HERE / "sample_business.txt")
    biz = Path(content_path).read_text(encoding="utf-8").splitlines()[0].strip() or "the business"
    chunks = load_chunks(content_path)
    ctx = "\n\n".join(retrieve(question, chunks))
    res = ask_llm(question, ctx, biz)
    if log:
        handoff = res["ok"] and bool(_HANDOFF.search(res["text"]))
        _log_run({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "ok": res["ok"],                              # the agent ran (LLM responded)
            "interventions": 1 if (handoff or not res["ok"]) else 0,  # human was needed
            "dollars_saved": VALUE_PER_RESOLVED if (res["ok"] and not handoff) else 0.0,
            "error": res["error"],
            "latency_s": res["latency_s"],
        })
    return res["text"]


def main():
    args = sys.argv[1:]
    content = None
    if "--content" in args:
        i = args.index("--content")
        content = args[i + 1]
        del args[i:i + 2]
    if args:
        print(answer(" ".join(args), content))
        return
    print("AI support agent (demo). Ask a question, or Ctrl-C to quit.\n")
    while True:
        try:
            q = input("customer> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q:
            print("\nagent> " + answer(q, content) + "\n")


if __name__ == "__main__":
    main()
