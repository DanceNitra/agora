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
import re
import sys
import urllib.request
from pathlib import Path

OLLAMA = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"                       # local + fast; swap to gpt/claude for a client
HERE = Path(__file__).resolve().parent
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
    return [b for s, b in scored[:k] if s > 0] or [b for _, b in chunks[:k]]


def ask_llm(question, context, business="the business"):
    """Answer the question using ONLY the context. Grounded + refuses when unknown."""
    system = (f"You are the friendly customer-support assistant for {business}. Answer the customer's "
              "question using ONLY the CONTEXT below. Be concise and warm. If the answer is not in the "
              "context, say you're not sure and offer to connect them with a human (email/phone if "
              "present) — do NOT invent facts, prices, or hours.")
    payload = {"model": MODEL, "stream": False,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": f"CONTEXT:\n{context}\n\nCUSTOMER: {question}"}]}
    try:
        req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=120).read())
        return out["message"]["content"].strip()
    except Exception as e:
        return f"[LLM unavailable: {str(e)[:80]}]\nRetrieved context the agent would answer from:\n{context}"


def answer(question, content_path=None):
    content_path = content_path or (HERE / "sample_business.txt")
    biz = Path(content_path).read_text(encoding="utf-8").splitlines()[0].strip() or "the business"
    chunks = load_chunks(content_path)
    ctx = "\n\n".join(retrieve(question, chunks))
    return ask_llm(question, ctx, biz)


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
