"""Night shift: batch jobs that spend the monthly Claude API credits.

Part 1 (this file): triage of overnight items with Claude Opus 5.5.
The script reads items from a JSONL file or from GitHub notifications, asks the model
which ones need a reply, and writes a digest. It sends nothing outward.

Every call is written to agora_output/night_shift/ledger.jsonl with the token counts
and the cost computed from the published prices. The run stops at the budget cap.

Usage:
  python tools/night_shift.py probe
  python tools/night_shift.py triage --github
  python tools/night_shift.py triage --in items.jsonl
  python tools/night_shift.py spent
"""
import argparse
import datetime
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "agora_output", "night_shift")
LEDGER = os.path.join(OUT, "ledger.jsonl")
ENV = os.path.join(ROOT, "server", ".env")

MODEL = "claude-opus-5-5"
# USD per million tokens, Claude Opus 5.5 (claude-api skill shared/models.md, 2026-10-18).
PRICE_IN, PRICE_OUT = 4.0, 20.0
# Hard stop. The monthly credit for Max 20x is 200 USD; the night shift may use 30 percent of it.
CAP_USD = 60.0


def load_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    for line in io.open(ENV, encoding="utf-8"):
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ANTHROPIC_API_KEY not found in server/.env")


def month_spent():
    month = datetime.date.today().strftime("%Y-%m")
    total = 0.0
    if os.path.exists(LEDGER):
        for line in io.open(LEDGER, encoding="utf-8"):
            row = json.loads(line)
            if row["ts"].startswith(month):
                total += row["usd"]
    return total


def call(client, system, user, max_tokens=16000, label=""):
    if month_spent() >= CAP_USD:
        sys.exit("budget cap of %.2f USD reached this month, stopping" % CAP_USD)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        output_config={"effort": "medium"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    u = resp.usage
    usd = (u.input_tokens * PRICE_IN + u.output_tokens * PRICE_OUT) / 1e6
    os.makedirs(OUT, exist_ok=True)
    with io.open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "label": label, "model": MODEL,
            "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
            "usd": round(usd, 6), "stop": resp.stop_reason,
        }) + "\n")
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, usd, resp.stop_reason


def github_items():
    raw = subprocess.run(["gh", "api", "notifications?per_page=50"], capture_output=True,
                         text=True, encoding="utf-8").stdout
    items = []
    for n in json.loads(raw or "[]"):
        items.append({
            "source": "github", "id": n["id"], "repo": n["repository"]["full_name"],
            "reason": n["reason"], "title": n["subject"]["title"],
            "url": n["subject"].get("url", ""), "updated": n["updated_at"],
        })
    return items


SYSTEM = (
    "You triage overnight messages for a small research organization. For each item, "
    "decide: REPLY (a real person asked the owner something or waits for his answer), "
    "WAITING (the last message is from the owner, sent_by_me is true, so we wait for them), "
    "WATCH (new information, no answer needed), or SKIP (bot, marketing, or irrelevant). "
    "Return one line per item: <id> | <REPLY|WAITING|WATCH|SKIP> | <six words why>. "
    "No other text. When unsure between REPLY and WATCH, choose REPLY."
)


def triage(items):
    client = anthropic.Anthropic(api_key=load_key())
    body = "\n".join(json.dumps(i, ensure_ascii=False) for i in items)
    text, usd, stop = call(client, SYSTEM, body, label="triage")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "digest_%s.txt" % datetime.date.today().isoformat())
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("items: %d | cost: %.5f USD | stop: %s | month total: %.4f USD" % (len(items), usd, stop, month_spent()))
    print("digest:", path)
    print(text)


THREAD_SYSTEM = (
    "You triage one email thread for the owner of a small research organization. You get the "
    "COMPLETE thread, every message in full, and the owner's handoff notes that say what is "
    "already handled. Read all of it before you decide. Decide one of: "
    "REPLY (a real person waits for the owner's answer and the notes do not say it is handled), "
    "WAITING (the owner wrote last, or the notes say we wait for them), "
    "HANDLED (the notes show the matter is closed or deliberately dropped), "
    "WATCH (information only, no answer needed), "
    "SKIP (bot, marketing, or irrelevant). "
    "Answer in this exact form, nothing else:\n"
    "VERDICT: <one word>\n"
    "WHY: <one sentence, plain, English>\n"
    "ASKED: <what exactly is asked of the owner and by whom, or none>\n"
    "NEXT: <one concrete next step, or none>\n"
    "If the text is cut off, empty, or you cannot tell, answer VERDICT: UNSURE and say what is missing."
)


def triage_threads(context_path):
    client = anthropic.Anthropic(api_key=load_key())
    tdir = os.path.join(OUT, "threads")
    context = io.open(context_path, encoding="utf-8").read()
    rows = []
    for name in sorted(os.listdir(tdir)):
        if not name.endswith(".txt"):
            continue
        thread = io.open(os.path.join(tdir, name), encoding="utf-8").read()
        head = thread.split("\n", 1)[0]
        if "status OK" not in head:
            rows.append((name[:-4], "UNSURE", "thread file is not marked OK: " + head))
            continue
        user = "HANDOFF NOTES (complete):\n%s\n\n=====\nTHREAD (complete):\n%s" % (context, thread)
        assert context in user and thread in user  # nothing was cut on the way in
        text, usd, stop = call(client, THREAD_SYSTEM, user, max_tokens=16000, label="thread " + name[:-4])
        verdict = re.search(r"VERDICT:\s*(\w+)", text)
        if stop != "end_turn" or not verdict:
            text, verdict = "stop=%s | %s" % (stop, text), None
        rows.append((name[:-4], verdict.group(1) if verdict else "UNSURE", text))
        print(name[:-4], verdict.group(1) if verdict else "UNSURE", "%.4f USD" % usd, flush=True)
    path = os.path.join(OUT, "digest_threads_%s.md" % datetime.date.today().isoformat())
    with io.open(path, "w", encoding="utf-8") as f:
        for tid, v, text in rows:
            f.write("## %s | %s\n%s\n\n" % (tid, v, text.strip()))
    print("digest:", path, "| month total: %.4f USD" % month_spent())


if __name__ == "__main__":
    import anthropic
    import re
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "triage", "triage-threads", "spent"])
    ap.add_argument("--github", action="store_true")
    ap.add_argument("--in", dest="infile")
    ap.add_argument("--context", default=os.path.join(ROOT, "agora_output", "strategy", "handoff_growth_2026-10-09.md"))
    a = ap.parse_args()
    if a.cmd == "triage-threads":
        triage_threads(a.context)
    elif a.cmd == "spent":
        print("%.4f USD of %.2f USD cap this month" % (month_spent(), CAP_USD))
    elif a.cmd == "probe":
        c = anthropic.Anthropic(api_key=load_key())
        t, usd, stop = call(c, "Answer with only the digits.", "What is 17 + 6? (nonce %s)" % os.urandom(3).hex(),
                            max_tokens=2000, label="probe")
        print("answer: %r | cost: %.6f USD | stop: %s" % (t.strip(), usd, stop))
    else:
        items = github_items() if a.github else [json.loads(l) for l in io.open(a.infile, encoding="utf-8") if l.strip()]
        if not items:
            sys.exit("no items")
        triage(items)
