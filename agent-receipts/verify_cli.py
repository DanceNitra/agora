"""verify — independently check a receipts file. No code required, just the file and a public key.

This is the whole point of receipts: a third party who was NOT there can confirm what an agent did.
Give them `receipts.json` and the actor's public key; they run one command and get PASS/FAIL with the
exact broken step named.

    python verify_cli.py receipts.json --pubkey <hex>
    python verify_cli.py receipts.json            # chain-integrity only (no signature check)

Exit code 0 = verified, 1 = tampering/forgery detected (so it drops into CI / pre-commit cleanly).
MIT. Part of the Agora project / agent-receipts.
"""
from __future__ import annotations
import argparse
import json
import sys

from agent_receipts import ReceiptChain, _HAVE_CRYPTO


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="verify", description="Independently verify an agent-receipts chain.")
    ap.add_argument("file", help="path to a receipts JSON file (a list of receipts)")
    ap.add_argument("--pubkey", default=None,
                    help="expected signer public key (hex); if given, every receipt must be signed by it")
    ap.add_argument("--quiet", action="store_true", help="print only the final verdict line")
    args = ap.parse_args(argv)

    try:
        with open(args.file, encoding="utf-8") as fh:
            receipts = json.load(fh)
        if not isinstance(receipts, list):
            print(f"FAIL: {args.file} is not a list of receipts", file=sys.stderr)
            return 1
    except FileNotFoundError:
        print(f"FAIL: file not found: {args.file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"FAIL: not valid JSON ({e})", file=sys.stderr)
        return 1

    chain = ReceiptChain.from_receipts(receipts)
    ok, problems = chain.verify(expected_pubkey=args.pubkey)

    if not args.quiet:
        actors = sorted({r.get("actor") for r in receipts if r.get("actor")})
        signed = sum(1 for r in receipts if "sig" in r)
        print(f"file    : {args.file}")
        print(f"receipts: {len(receipts)}  (signed: {signed})")
        print(f"actor(s): {', '.join(actors) if actors else '(none)'}")
        if args.pubkey:
            print(f"expected signer: {args.pubkey[:16]}...")
        elif signed and not _HAVE_CRYPTO:
            print("note   : receipts are signed but `cryptography` is not installed to check signatures")
        elif signed:
            print("note   : signatures present but no --pubkey given; checking chain integrity only")

    if ok:
        print(f"\nVERIFIED: all {len(receipts)} receipts intact"
              f"{' and signed by the expected key' if args.pubkey else ''}.")
        return 0
    print(f"\nFAILED: {len(problems)} problem(s) detected:")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
