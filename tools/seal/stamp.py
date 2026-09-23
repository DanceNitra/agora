"""Stamp a document: the seal, the certificate, and the refusal when nothing earned it.

WHY THIS EXISTS. A seal anyone can paste onto anything is decoration. This one comes only from a
receipt written by `tools/recompute_receipt.py`, which ran the claim script itself, mutated its
inputs, and refused unless every mutation broke a claim. Change one character of the document
afterwards and its sha256 no longer matches the receipt, so the next stamp refuses.

WHAT IT CERTIFIES, stated narrowly on purpose: the time of sealing, and that nothing changed
since. It does not certify that the finding is correct. `TESTIS NON IUDEX`, a witness, not a judge.

The band carries the LAST twelve characters of the log root in groups of four, because that is
what a person can compare by eye from paper. The whole 64 go in the certificate, because only the
whole root verifies. The tail rather than the head: a prefix is the part a collision search would
aim at, and it is also the part everyone truncates.

    python tools/seal/stamp.py <document> --receipt <receipt.json> --format email|markdown|text|svg
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ART = os.path.join(HERE, "inspeximus_seal.svg")

# Measured from the artwork rather than guessed: the band's two rules sit at these rows of the
# 2482 x 2466 viewBox. A redraw must re-measure them; an eyeballed value put the text on a rule.
BAND_TOP, BAND_BOTTOM = 1748, 1913
TAIL = 12
NL = chr(10)   # heredocs on this machine eat escaped newlines; build them explicitly


def sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def seal_svg(log_root, size=160):
    art = io.open(ART, encoding="utf-8").read()
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', art)
    w = int(m.group(1))
    tail = log_root[-TAIL:]
    grouped = " ".join(tail[i:i + 4] for i in range(0, len(tail), 4))
    fs = w * 0.040
    y = (BAND_TOP + BAND_BOTTOM) / 2 + fs * 0.35      # baseline sits below the optical centre
    band = (
        '  <text x="%d" y="%d" text-anchor="middle" fill="currentColor"'
        ' font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"'
        ' font-size="%d" letter-spacing="%.1f">%s</text>'
        % (w / 2, y, fs, w * 0.005, grouped)
    )
    art = art.replace("</svg>", band + "</svg>")
    return art.replace('width="600" height="600"', 'width="%d" height="%d"' % (size, size), 1)


def certificate(rec):
    """The certificate's fields, in a fixed order a reader can scan.

    The first version was a run-on paragraph of fragments, and the owner was right twice: it had
    no shape, and then the shaped version was still ragged, because a 64-character hash sets the
    width of everything beside it. A notarial endorsement answers, in order: what was sealed, its
    fingerprint, where the record lives, when, what was actually checked, and what the seal does
    NOT claim. The last line is not modesty. Without it the seal overclaims.

    Hashes are split into two lines of 32, so the block stays narrower than the body text it sits
    under. An editor reads a column, not a banner.
    """
    entry = rec.get("log_entry") or {}
    muts = rec.get("mutations", [])
    broke = sum(1 for m in muts if m.get("claims_broken"))
    if entry:
        where = "Entry %s, under the root above" % entry.get("index")
    else:
        where = "Pending. The root above does not include this document."
    return {
        "title": "INSPEXIMUS",
        "subtitle": "Certificate of verification",
        "rows": [
            ("Document", os.path.basename(rec.get("draft", "")), False),
            ("Content hash", rec.get("draft_sha256", ""), True),
            ("Log root", rec["log_root"], True),
            ("Sealed", rec["sealed_utc"], False),
            ("Record", where, False),
        ],
        # The column is as wide as the seal, so these two lines are written to that measure.
        # Long copy in a 200 px column becomes six ragged lines, which is a copy problem wearing
        # a layout problem's clothes.
        "checked": ("%d figures recomputed from %d sources. %d of %d tamper tests broke the result."
                    % (len(rec.get("claims", {})), len(rec.get("inputs", [])), broke, len(muts))),
        "scope": "Certifies time and integrity, not correctness.",
    }


def split32(v):
    """A 64-character hash as two lines of 32, so it never sets the block's width."""
    return [v[i:i + 32] for i in range(0, len(v), 32)]


def as_text(c):
    W = 40                                   # the value column, two hash halves wide plus air
    lab = max(len(k) for k, _, _ in c["rows"])
    bar = "-" * (lab + 3 + W)
    out = [bar, "%s   %s" % (c["title"], c["subtitle"]), bar]
    for k, v, wrap in c["rows"]:
        parts = split32(v) if wrap else [v]
        for i, part in enumerate(parts):
            out.append("  %-*s   %s" % (lab, k if i == 0 else "", part))
    out.append("")
    for para in (c["checked"], c["scope"]):
        line = "  "
        for word in para.split():
            if len(line) + len(word) > lab + W:
                out.append(line.rstrip())
                line = "  "
            line += word + " "
        out.append(line.rstrip())
    out.append(bar)
    return chr(10).join(out)


def as_email(c, log_root):
    """Four columns, and the text no taller than the seal beside it.

    Four layouts were wrong before this. Side by side with a wide column read as a banner under a
    badge. Stacked at seal width made a tower. Four columns was right, but the text still ran on
    past the seal's bottom edge, so the owner drew a box round the first three rows and said: all
    of it, in there. That sets the real constraint, which is HEIGHT. Everything fits the seal's
    height, so each hash goes on ONE line and the closing sentences share a line.
    """
    W, COL = 520, 118
    SEAL = COL - 14
    b64 = base64.b64encode(seal_svg(log_root, SEAL).encode("utf-8")).decode("ascii")
    mono = ("font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:8.5px;"
            "letter-spacing:-.1px;color:#3a3a3a")
    lab = ("font-size:7.5px;letter-spacing:1px;text-transform:uppercase;color:#a8a8a8;"
           "white-space:nowrap")
    rows = ""
    for k, v, wrap in c["rows"]:
        rows += (
            '<tr>'
            '<td style="padding:0 9px 0 0;vertical-align:baseline;%s">%s</td>'
            '<td style="padding:0;vertical-align:baseline;%s">%s</td>'
            '</tr>' % (lab, k, mono if wrap else "font-size:9.5px;color:#3a3a3a", v))
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'style="margin-top:28px;border-top:1px solid #e8e8e8;padding-top:12px;width:%dpx">'
        '<tr>'
        '<td style="width:%dpx;vertical-align:top;padding-right:14px">'
        '<img src="data:image/svg+xml;base64,%s" width="%d" height="%d" '
        'alt="Inspeximus seal" style="display:block"></td>'
        '<td style="vertical-align:top;'
        'font:9.5px/1.42 -apple-system,Segoe UI,Helvetica,sans-serif;color:#3a3a3a">'
        '<div style="font-size:8.5px;letter-spacing:1.6px;color:#111;padding-bottom:4px">'
        '<b>%s</b><span style="color:#a8a8a8">&nbsp;&nbsp;%s</span></div>'
        '<table cellpadding="0" cellspacing="0" style="line-height:1.42">%s</table>'
        '<div style="padding-top:5px">%s <span style="color:#a8a8a8">%s</span></div>'
        '</td></tr></table>'
        % (W, COL, b64, SEAL, SEAL, c["title"], c["subtitle"].upper(), rows,
           c["checked"], c["scope"])
    )


def as_markdown(c, log_root, document):
    rel = "tools/seal/stamped/" + os.path.basename(document) + ".svg"
    os.makedirs(os.path.join(ROOT, os.path.dirname(rel)), exist_ok=True)
    io.open(os.path.join(ROOT, rel), "w", encoding="utf-8").write(seal_svg(log_root, 600))
    rows = ""
    for k, v, wrap in c["rows"]:
        value = "<br>".join("<code>%s</code>" % x for x in split32(v)) if wrap else v
        rows += "| %s | %s |" % (k, value) + NL
    tpl = NL.join([
        "", "---", "",
        '<img src="%s" width="110" align="left" style="margin-right:18px" alt="Inspeximus seal">',
        "", "**%s** &nbsp;%s", "", "| | |", "|---|---|", "%s%s", "", "_%s_", "",
    ])
    return tpl % (rel, c["title"], c["subtitle"], rows, c["checked"], c["scope"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("document")
    ap.add_argument("--receipt", required=True, help="from tools/recompute_receipt.py")
    ap.add_argument("--log-root", default="", help="testing only; prints the seal as UNLOGGED")
    ap.add_argument("--format", choices=["svg", "markdown", "email", "text"], default="markdown")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    rec = json.load(io.open(a.receipt, encoding="utf-8"))
    digest = sha(a.document)
    if rec.get("draft_sha256") != digest:
        raise SystemExit(
            "REFUSED: the receipt was written for %s..., this document hashes to %s...\n"
            "  A seal is bound to the bytes that earned it. Re-run the claims and try again."
            % (rec.get("draft_sha256", "")[:16], digest[:16]))

    verdicts = [c.get("verdict") if isinstance(c, dict) else c
                for c in rec.get("claims", {}).values()]
    if not verdicts or any(v != "PASS" for v in verdicts):
        raise SystemExit("REFUSED: the receipt records a failing claim.")
    if not rec.get("mutations"):
        raise SystemExit("REFUSED: the receipt records no mutation, so nothing showed that the "
                         "check can fail.")

    # THE SEAL MUST NAME A ROOT THAT CONTAINS THIS DOCUMENT.
    #
    # The first version read the log's CURRENT root and printed it. That root commits to the
    # entries already in the log, never to this receipt, so the seal said "transparency log root X"
    # about a document absent from X. The number was true and the sentence beside it misled, which
    # is the class this whole toolchain exists to catch.
    entry = rec.get("log_entry") or {}
    if not a.log_root and not entry:
        raise SystemExit(
            "REFUSED: this receipt is not in the transparency log, so no root contains this "
            "document.\n  Submit it, wait for the publish cycle, then stamp.\n"
            "  --log-root prints a root that does not commit to these bytes, and the certificate "
            "says so.")

    rec["log_root"] = a.log_root or entry.get("root")
    rec.setdefault("sealed_utc", rec.get("recorded_utc", ""))
    if a.log_root and not entry:
        rec["log_entry"] = None

    c = certificate(rec)
    if a.format == "svg":
        out = seal_svg(rec["log_root"], 600)
    elif a.format == "text":
        out = as_text(c)
    elif a.format == "email":
        out = as_email(c, rec["log_root"])
    else:
        out = as_markdown(c, rec["log_root"], a.document)

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(out)
        print("  SEALED  %s -> %s" % (os.path.basename(a.document), a.out))
    else:
        sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
