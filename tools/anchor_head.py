#!/usr/bin/env python
"""Anchor a published log head in Bitcoin with OpenTimestamps, so time needs no volunteer.

WHY THIS EXISTS. A witness is the one role a log's operator cannot fill, and the first answer we
reached was to ask people to run one. That ask is real but slow: it needs a stranger to keep a cron
job alive for years, and their memory of our head lasts only as long as their interest does. An
OpenTimestamps receipt needs nobody. It proves the head existed before a Bitcoin block, and that
block's timestamp is not ours to move.

WHAT IT PROVES, exactly, because the value is narrow and the temptation is to overstate it:

  - the bytes of this head.json existed before block N. A publisher who later rewrites history
    cannot produce an earlier anchor for the new root, so the rewrite is visible to anyone holding
    the old receipt.
  - nothing about whether any entry in the log is true, and nothing about what the log showed
    somebody else. A split view is still catchable only by a witness that remembers, which is why
    the witness invitation stands beside this rather than being replaced by it.

WHAT IT NEEDS is the reference client, `pip install opentimestamps-client`. That is a tool-side
dependency: inspeximus itself stays zero-dependency and nothing in the library imports this.

    python tools/anchor_head.py stamp   --url https://92.5.74.17.sslip.io/log --out witness/ots
    python tools/anchor_head.py upgrade --dir witness/ots        # hours later, once mined

A fresh receipt carries only calendar attestations: the calendars say they saw the digest, which is
a promise rather than a proof. `upgrade` replaces that with the Bitcoin attestation once the
commitment is mined, usually within a few hours. A receipt that has never been upgraded is recorded
as PENDING rather than counted as an anchor, because "we asked for a timestamp" and "we have one"
are different claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:                                              # noqa: BLE001
    _CTX = ssl.create_default_context()


def fetch(url, timeout=30.0):
    request = urllib.request.Request(url, headers={"User-Agent": "inspeximus-anchor/1.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=_CTX) as r:
        return r.read()


def _ots(args, cwd=None):
    """Run the reference client. Its exit code is the verdict and its output carries the reason."""
    exe = os.environ.get("OTS_BIN", "ots")
    try:
        p = subprocess.run([exe] + args, cwd=cwd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise SystemExit("opentimestamps-client is not installed: pip install opentimestamps-client")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _index_path(out):
    return os.path.join(out, "index.json")


def _load_index(out):
    try:
        with open(_index_path(out), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                            # noqa: BLE001 - a missing index is a first run
        return {"kind": "inspeximus.ots-anchors/1", "anchors": []}


def _save_index(out, index):
    index["anchors"].sort(key=lambda a: (a.get("log", ""), a.get("n_writes", 0)))
    os.makedirs(out, exist_ok=True)
    tmp = _index_path(out) + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, _index_path(out))


SCOPE = ("Proves these head bytes existed before the Bitcoin block named once upgraded. Says nothing "
         "about whether any entry is true, and cannot see a history shown to somebody else.")


def stamp(url, out):
    """Copy the head, stamp that copy, and record what was anchored. One anchor per (log, size)."""
    head_bytes = fetch(url.rstrip("/") + "/head.json")
    head = json.loads(head_bytes.decode("utf-8"))
    log = url.rstrip("/")
    name = "%s-%s" % (head.get("n_writes"), str(head.get("writes_tip", ""))[:16])
    folder = os.path.join(out, str(head.get("store_id", "log")).replace(":", "_"))
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, name + ".head.json")

    index = _load_index(out)
    already = [a for a in index["anchors"]
               if a.get("log") == log and a.get("n_writes") == head.get("n_writes")]
    if already and os.path.exists(target + ".ots"):
        print("already anchored: %s at %s entries" % (log, head.get("n_writes")))
        return 0

    with open(target, "wb") as fh:                               # the exact bytes that were stamped
        fh.write(head_bytes)
    code, output = _ots(["stamp", os.path.basename(target)], cwd=folder)
    if code != 0 or not os.path.exists(target + ".ots"):
        print(output.strip(), file=sys.stderr)
        return 1

    index["anchors"] = [a for a in index["anchors"]
                        if not (a.get("log") == log and a.get("n_writes") == head.get("n_writes"))]
    index["anchors"].append({
        "log": log,
        "store_id": head.get("store_id"),
        "n_writes": head.get("n_writes"),
        "writes_tip": head.get("writes_tip"),
        "sth_hash": head.get("sth_hash"),
        "head_sha256": hashlib.sha256(head_bytes).hexdigest(),
        "receipt": os.path.relpath(target + ".ots", out).replace("\\", "/"),
        "stamped_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PENDING",                                     # a calendar promise, not yet a proof
        "scope": SCOPE,
    })
    _save_index(out, index)
    print("stamped %s at %s entries -> %s" % (log, head.get("n_writes"), target + ".ots"))
    return 0


def upgrade(out):
    """Turn calendar promises into Bitcoin attestations, and mark only the ones that verify."""
    index = _load_index(out)
    changed = 0
    for a in index["anchors"]:
        receipt = os.path.join(out, a.get("receipt", ""))
        if not a.get("receipt") or not os.path.exists(receipt):
            a["status"] = "MISSING"
            continue
        _ots(["upgrade", receipt])                               # a no-op while it is unmined
        code, output = _ots(["verify", receipt])
        # The client names the block it found. An unmined receipt exits non-zero and says "Pending
        # confirmation", so only the first of these counts as an anchor.
        if code == 0 and "Bitcoin block" in output:
            block = output.split("Bitcoin block")[1].split()[0].strip()
            if a.get("status") != "ANCHORED" or a.get("bitcoin_block") != block:
                changed += 1
            a["status"] = "ANCHORED"
            a["bitcoin_block"] = block
            a["verified_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        else:
            a["status"] = "PENDING"
    _save_index(out, index)
    n = sum(1 for a in index["anchors"] if a.get("status") == "ANCHORED")
    print("anchors: %d of %d confirmed in Bitcoin (%d newly)" % (n, len(index["anchors"]), changed))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stamp", help="anchor the current head of a published log")
    s.add_argument("--url", required=True, help="base URL of the published log")
    s.add_argument("--out", default="witness/ots", help="where the receipts and the index live")
    u = sub.add_parser("upgrade", help="upgrade pending receipts and verify them")
    u.add_argument("--dir", default="witness/ots")
    a = ap.parse_args(argv)
    return stamp(a.url, a.out) if a.cmd == "stamp" else upgrade(a.dir)


if __name__ == "__main__":
    raise SystemExit(main())
