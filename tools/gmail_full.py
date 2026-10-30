"""Read Gmail threads in full through the Gmail API (read-only scope).

Nothing is cut. Every message of a thread is decoded to text, the text/plain part when it
exists and the text of the text/html part when it does not. Attachment names are listed,
their content is not read. After each thread the script checks that no message came out
empty. A thread that fails the check is written with a FAILED marker instead of passing
silently.

The OAuth client file is passed with --client. The token is stored outside the repository
in ~/.config/agora/gmail_token.json. The first run opens a browser; the owner clicks Allow.

Usage:
  python tools/gmail_full.py --client <client_secret.json> fetch --query "in:inbox newer_than:7d"
"""
import argparse
import base64
import html
import io
import json
import os
import re
from html.parser import HTMLParser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN = os.path.join(os.path.expanduser("~"), ".config", "agora", "gmail_token.json")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "agora_output", "night_shift", "threads")


def service(client_path):
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN), exist_ok=True)
        with io.open(TOKEN, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("br", "p", "div", "tr", "li", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(s):
    p = _Text()
    p.feed(s)
    text = html.unescape("".join(p.parts))
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t͏​-‏]+", " ", text)).strip()


def _decode(data):
    return base64.urlsafe_b64decode(data.encode("ascii") + b"=" * (-len(data) % 4)).decode("utf-8", "replace")


def _walk(svc, msg_id, part, plain, htmls, attachments):
    mime = part.get("mimeType", "")
    body = part.get("body", {})
    if part.get("filename"):
        attachments.append("%s (%s, %s bytes)" % (part["filename"], mime, body.get("size", "?")))
    elif mime in ("text/plain", "text/html"):
        data = body.get("data")
        if not data and body.get("attachmentId"):
            data = svc.users().messages().attachments().get(
                userId="me", messageId=msg_id, id=body["attachmentId"]).execute().get("data")
        if data:
            (plain if mime == "text/plain" else htmls).append(_decode(data))
    for sub in part.get("parts", []) or []:
        _walk(svc, msg_id, sub, plain, htmls, attachments)


def message_text(svc, msg):
    plain, htmls, attachments = [], [], []
    _walk(svc, msg["id"], msg["payload"], plain, htmls, attachments)
    text = "\n".join(plain).strip()
    if not text and htmls:
        text = html_to_text("\n".join(htmls))
    return text, attachments


def header(msg, name):
    for h in msg["payload"].get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_thread(svc, thread_id):
    t = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
    msgs = t.get("messages", [])
    blocks, problems = [], []
    for i, m in enumerate(msgs, 1):
        text, atts = message_text(svc, m)
        if not text:
            problems.append("message %d (%s) has no readable text" % (i, m["id"]))
        blocks.append("=== message %d of %d | id %s | labels %s\nFrom: %s\nTo: %s\nCc: %s\nDate: %s\nSubject: %s\nAttachments: %s\n\n%s\n" % (
            i, len(msgs), m["id"], ",".join(m.get("labelIds", [])), header(m, "From"), header(m, "To"),
            header(m, "Cc"), header(m, "Date"), header(m, "Subject"), "; ".join(atts) or "none", text))
    return msgs, "\n".join(blocks), problems


def fetch(svc, query, limit):
    os.makedirs(OUT, exist_ok=True)
    ids, token = [], None
    while len(ids) < limit:
        r = svc.users().threads().list(userId="me", q=query, maxResults=min(100, limit - len(ids)), pageToken=token).execute()
        ids += [t["id"] for t in r.get("threads", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    report = []
    for tid in ids:
        msgs, text, problems = fetch_thread(svc, tid)
        status = "FAILED" if problems or not msgs else "OK"
        with io.open(os.path.join(OUT, tid + ".txt"), "w", encoding="utf-8") as f:
            f.write("THREAD %s | messages %d | status %s\n%s\n\n%s" % (tid, len(msgs), status, "; ".join(problems), text))
        report.append({"id": tid, "messages": len(msgs), "chars": len(text), "status": status, "problems": problems})
    with io.open(os.path.join(OUT, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    bad = [r for r in report if r["status"] != "OK"]
    print("threads: %d | OK: %d | FAILED: %d | total chars: %d" % (len(report), len(report) - len(bad), len(bad), sum(r["chars"] for r in report)))
    for r in bad:
        print("FAILED", r["id"], r["problems"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", required=True)
    ap.add_argument("cmd", choices=["fetch"])
    ap.add_argument("--query", default="in:inbox newer_than:7d")
    ap.add_argument("--limit", type=int, default=100)
    a = ap.parse_args()
    fetch(service(a.client), a.query, a.limit)
