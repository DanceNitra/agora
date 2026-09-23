"""Stamp a document: the seal, the signature block, and the refusal when nothing earned it.

WHY THIS EXISTS. A seal that anyone can paste onto anything is decoration. This one is produced
only from a receipt written by `tools/recompute_receipt.py`, which ran the claim script itself,
mutated its inputs, and required every mutation to break a claim. Change one character of the
document afterwards and its sha256 no longer matches the receipt, so the next stamp refuses.

WHAT THE SEAL SAYS, and it is deliberately narrow: the figures are a deterministic function of
named inputs, the run reproduced byte for byte, and the check was shown able to fail. It does NOT
say the claim is correct. `TESTIS NON IUDEX`, a witness, not a judge.

The band carries the LAST twelve characters of the log root, in groups of four, because that is
what a person can compare by eye from paper. The full 64 characters go in the text beside it,
because only the whole root verifies.

    python tools/seal/stamp.py <document> --receipt <receipt.json> [--email | --markdown | --svg]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ART = os.path.join(HERE, "inspeximus_seal.svg")

# Measured from the artwork rather than guessed: the two rules of the band sit at these rows of
# the 2482 x 2466 viewBox. A later redraw must re-measure them; an eyeballed value put the text
# on top of a rule the first time.
BAND_TOP, BAND_BOTTOM = 1748, 1913
TAIL = 12


def sha(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def seal_svg(log_root: str, size: int = 160) -> str:
    art = io.open(ART, encoding="utf-8").read()
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', art)
    w, h = int(m.group(1)), int(m.group(2))
    tail = log_root[-TAIL:]
    grouped = " ".join(tail[i:i + 4] for i in range(0, len(tail), 4))
    fs = w * 0.040
    y = (BAND_TOP + BAND_BOTTOM) / 2 + fs * 0.35      # baseline sits below the optical centre
    band = (
        '  <text x="%d" y="%d" text-anchor="middle" fill="currentColor"\n'
        '     font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"\n'
        '     font-size="%d" letter-spacing="%.1f">%s</text>\n'
        % (w / 2, y, fs, w * 0.005, grouped)
    )
    art = art.replace("</svg>", band + "</svg>")
    return art.replace('width="600" height="600"', 'width="%d" height="%d"' % (size, size), 1)


def lines(rec: dict) -> list:
    """The four lines that go beside the seal, in every format."""
    claims = len(rec.get("claims", {}))
    muts = rec.get("mutations", [])
    broke = sum(1 for m in muts if m.get("claims_broken"))
    return [
        "Inspeximus",
        "Transparency log root %s" % rec["log_root"],
        "Sealed %s. %d claims recomputed from %d named inputs; %d of %d mutations broke a claim."
        % (rec["sealed_utc"], claims, len(rec.get("inputs", [])), broke, len(muts)),
        ("Entry %s of the log; the root above includes it." % rec["log_entry"]["index"])
        if rec.get("log_entry") else
        "UNLOGGED: the root above does NOT include this document. For testing only.",
        "This attests when, and that nothing changed since. It does not attest that the claim is "
        "correct. Every number has a command behind it.",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("document")
    ap.add_argument("--receipt", required=True, help="from tools/recompute_receipt.py")
    ap.add_argument("--log-root", default="", help="override the root; normally read from the log")
    ap.add_argument("--format", choices=["svg", "markdown", "email", "text"], default="markdown")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    rec = json.load(io.open(a.receipt, encoding="utf-8"))
    digest = sha(a.document)
    if rec.get("draft_sha256") != digest:
        raise SystemExit(
            "REFUSED: the receipt was written for %s..., this document hashes to %s...\n"
            "  A seal is bound to the bytes it was earned on. Re-run the claims and try again."
            % (rec.get("draft_sha256", "")[:16], digest[:16]))
    verdicts = [c.get("verdict") if isinstance(c, dict) else c
                for c in rec.get("claims", {}).values()]
    if not verdicts or any(v != "PASS" for v in verdicts):
        raise SystemExit("REFUSED: the receipt records a failing claim.")
    if not rec.get("mutations"):
        raise SystemExit("REFUSED: the receipt records no mutation, so nothing showed the check "
                         "could fail.")

    # THE SEAL MUST NAME A ROOT THAT CONTAINS THIS DOCUMENT.
    #
    # The first version read the log's current root and printed it. That root commits to the
    # entries already in the log, never to this receipt, so the seal said "transparency log root X"
    # about a document that was not in X. The number was true and the sentence was misleading,
    # which is the class of defect this whole tool exists to catch. It now refuses unless the
    # receipt carries an entry: a leaf index, the root that includes it, and the audit path a
    # reader can verify without asking the server anything.
    entry = rec.get("log_entry") or {}
    if not a.log_root and not entry:
        raise SystemExit(
            "REFUSED: this receipt is not in the transparency log, so there is no root that "
            "contains this document.\n"
            "  Submit it, wait for the publish cycle, then stamp.\n"
            "  Passing --log-root by hand prints a root that does not commit to these bytes; "
            "the flag stays for testing and says so in the output.")
    log_root = a.log_root or entry.get("root") or ""
    if not log_root:
        try:
            import ssl
            import urllib.request
            # This Python ships a stale CA bundle: it calls the host's certificate expired when
            # openssl reads the same certificate as valid until 2026-12-21. Trust certifi, not the
            # interpreter's own store.
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except Exception:
                ctx = ssl.create_default_context()
            u = "https://92.5.74.17.sslip.io/log/self-verification.json"
            log_root = json.load(urllib.request.urlopen(u, timeout=20, context=ctx))["root"]
        except Exception as exc:
            raise SystemExit("REFUSED: no log root, and the log did not answer (%s).\n"
                             "  Pass --log-root, or seal later." % exc)
    rec["log_root"] = log_root
    rec.setdefault("sealed_utc", rec.get("recorded_utc", ""))

    ln = lines(rec)
    if a.format == "svg":
        out = seal_svg(log_root, 600)
    elif a.format == "text":
        out = "\n".join(["-" * 68, ln[0].upper(),
                         "  root %s" % log_root,
                         "  short %s" % " ".join(log_root[-TAIL:][i:i + 4] for i in range(0, TAIL, 4)),
                         "  " + ln[2], "  " + ln[3], "-" * 68])
    elif a.format == "email":
        svg = seal_svg(log_root, 96).replace('"', "'")
        import base64
        b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        out = (
            '<table role="presentation" cellpadding="0" cellspacing="0" '
            'style="border-top:1px solid #ddd;padding-top:12px;margin-top:18px">\n'
            '<tr><td style="padding-right:14px;vertical-align:top">'
            '<img src="data:image/svg+xml;base64,%s" width="96" height="96" alt="Inspeximus seal"></td>\n'
            '<td style="font:12px/1.55 -apple-system,Segoe UI,sans-serif;color:#444">'
            '<b>%s</b><br>%s <code style="font:11px ui-monospace,Consolas,monospace;'
            'word-break:break-all">%s</code><br>%s<br>'
            '<span style="color:#777">%s</span></td></tr></table>\n'
            % (b64, ln[0], "Transparency log root", log_root, ln[2], ln[3])
        )
    else:
        rel = os.path.join("tools", "seal", "stamped", os.path.basename(a.document) + ".svg")
        os.makedirs(os.path.join(ROOT, os.path.dirname(rel)), exist_ok=True)
        io.open(os.path.join(ROOT, rel), "w", encoding="utf-8").write(seal_svg(log_root, 600))
        out = ("\n---\n\n<img src=\"%s\" width=\"120\" align=\"left\" "
               "style=\"margin-right:14px\" alt=\"Inspeximus seal\">\n\n"
               "**%s**  \n%s `%s`  \n%s  \n_%s_\n"
               % (rel.replace("\\", "/"), ln[0], "Transparency log root", log_root, ln[2], ln[3]))

    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(out)
        print("  SEALED  %s -> %s" % (os.path.basename(a.document), a.out))
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
