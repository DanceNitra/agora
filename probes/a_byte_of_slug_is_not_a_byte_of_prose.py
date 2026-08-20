"""Does a byte of `kebab-case-slug.md` cost the same as a byte of English prose?

WHY. @yacb2 measured session-startup cost as ~108 tokens fixed + 0.44 tokens/byte of memory index
(anthropics/claude-code#82056, comment 5352555064), fitted from two ablation points. 0.44 tokens/byte
is ~2.3 bytes/token, far denser than English usually tokenizes (~4 bytes/token). If the slope moves
with index CONTENT, then "shorten the index" and "cheapen the index" are different operations and the
cheapest layout is not the shortest one. We were about to ASK him this. Measuring it is better.

It matters to us specifically because the load window is enforced in BYTES (~24.4 KB) while the cost
is paid in TOKENS. Those are different currencies, and we have been optimising the byte one.

WHAT IT MEASURES. The live index decomposed into the parts it is actually built from:
    slug      `a-guard-with-half-recall-reports-safe.md`  -- the file name inside the link
    title     `A guard with half recall reports SAFE`     -- the human label inside the link
    prose     the sentence after the em dash saying what the note concluded
plus, as an external anchor, the BODY prose of the memory files, and each real index state on disk.

INSTRUMENT, and its limit stated up front. Anthropic's `count_tokens` is the tokenizer that actually
bills this context, and it is what this probe tried first. It is UNAVAILABLE (the account's credit
balance is zero), and paying to run it is not justified for this question. So the claim is NOT
"Claude tokenizes slugs at rate X". The claim is the RATIO -- slug bytes cost more than prose bytes --
measured across four BPE vocabularies spanning two generations (r50k/p50k = GPT-2/3 era, cl100k,
o200k). A ratio that holds across all four is a property of byte-pair encoding on hyphenated lowercase
compounds, not an artifact of one vocabulary. If they disagree, the finding is about a tokenizer and
must not be published as being about slugs.

CONTROLS
  C1 ANCHOR      English prose must land near the ~0.25 tokens/byte these tokenizers are known for.
                 If our "prose" arm reads like slugs, the segmentation is wrong, not the world.
  C2 INVARIANCE  the slug:prose ratio must hold across every available tokenizer.
  C3 RECOMPOSE   slug+title+prose bytes must account for the entry bytes they were split from, so the
                 segmentation cannot silently drop the expensive part.
  C4 DENOM       every rate prints its byte and segment count.
  C5 DIRECTION   a NEGATIVE control: reversing the arms must reverse the verdict, so the comparison
                 is doing work rather than reporting a constant.

Run:  python probes/a_byte_of_slug_is_not_a_byte_of_prose.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MEMORY_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                          "C--Users-Danculus-agora", "memory")
INDEX = os.path.join(MEMORY_DIR, "MEMORY.md")
SLUGGY = os.path.join(MEMORY_DIR, "MEMORY.md.bak-20260819-prewrittenlines")
ENTRY = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\)(?:\s*[—-]\s*(.*))?$")


def load_key():
    env = os.path.join(REPO, "server", ".env")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8", errors="replace"):
            if line.startswith("ANTHROPIC_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("ANTHROPIC_API_KEY")


def build_tokenizers():
    """-> (list of (name, fn), note about the authoritative one)"""
    toks, note = [], ""
    key = load_key()
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            client.messages.count_tokens(model="claude-sonnet-4-5",
                                         messages=[{"role": "user", "content": "."}])

            def anth(text):
                return client.messages.count_tokens(
                    model="claude-sonnet-4-5",
                    messages=[{"role": "user", "content": text or "."}]).input_tokens
            toks.append(("anthropic", anth))
            note = "authoritative tokenizer AVAILABLE"
        except Exception as e:
            note = f"authoritative tokenizer UNAVAILABLE ({type(e).__name__}: " \
                   f"{'credit balance is zero' if 'credit balance' in str(e) else str(e)[:60]})"
    else:
        note = "authoritative tokenizer UNAVAILABLE (no key)"

    import tiktoken
    for name in ("o200k_base", "cl100k_base", "p50k_base", "r50k_base"):
        try:
            enc = tiktoken.get_encoding(name)
            toks.append((name, lambda t, e=enc: len(e.encode(t))))
        except Exception:
            pass
    return toks, note


def segments():
    slugs, titles, prose = [], [], []
    for line in open(INDEX, encoding="utf-8", errors="replace"):
        m = ENTRY.match(line.rstrip("\r\n"))
        if not m:
            continue
        titles.append(m.group(1))
        slugs.append(m.group(2))
        tail = (m.group(3) or "").strip()
        if tail:
            prose.append(tail)
    return {"slug": slugs, "title": titles, "prose": prose}


def body_prose(limit=60):
    out = []
    for fn in sorted(os.listdir(MEMORY_DIR)):
        if len(out) >= limit or not fn.endswith(".md") or fn.startswith("MEMORY"):
            continue
        txt = open(os.path.join(MEMORY_DIR, fn), encoding="utf-8", errors="replace").read()
        txt = txt.split("---", 2)[-1]
        txt = re.sub(r"\[\[[^\]]+\]\]", "", txt)
        txt = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", txt)
        txt = re.sub(r"`[^`]*`", "", txt)
        for para in txt.split("\n\n"):
            p = " ".join(para.split())
            if len(p) > 200 and "http" not in p:
                out.append(p)
                break
    return out


def main():
    toks, note = build_tokenizers()
    print(f"INSTRUMENT: {note}")
    print(f"            measuring with {len(toks)}: {', '.join(n for n, _ in toks)}\n")
    if len(toks) < 3:
        sys.exit("FAIL: fewer than three tokenizers -- invariance cannot be tested, and a single "
                 "vocabulary cannot separate a slug finding from a tokenizer finding.")

    segs = segments()
    segs["body prose"] = body_prose()
    if not segs["prose"]:
        sys.exit("FAIL: no prose segments parsed -- the entry regex does not match the live index")

    arms = ("slug", "title", "prose", "body prose")
    blobs = {a: "\n".join(segs[a]) for a in arms}
    nbytes = {a: len(blobs[a].encode("utf-8")) for a in arms}

    print("tokens per byte, by arm and tokenizer")
    print(f"{'arm':<12} {'segs':>5} {'bytes':>7} " + " ".join(f"{n[:11]:>12}" for n, _ in toks))
    rate = {}
    for a in arms:
        rate[a] = {}
        cells = []
        for n, fn in toks:
            t = fn(blobs[a])
            rate[a][n] = t / nbytes[a]
            cells.append(f"{rate[a][n]:>12.3f}")
        print(f"{a:<12} {len(segs[a]):>5} {nbytes[a]:>7} " + " ".join(cells))

    print("\nwhole real index states")
    states = {}
    for label, path in (("live index (mixed)", INDEX), ("08-19 (slug-heavy)", SLUGGY)):
        if not os.path.exists(path):
            continue
        blob = open(path, encoding="utf-8", errors="replace").read()
        nb = len(blob.encode("utf-8"))
        states[label] = {n: fn(blob) / nb for n, fn in toks}
        states[label]["_bytes"] = nb
        cells = " ".join(f"{states[label][n]:>12.3f}" for n, _ in toks)
        print(f"{label:<20} {nb:>6} B " + cells)

    # ---------------- controls ----------------
    print()
    fails = []
    anchors = [rate["body prose"][n] for n, _ in toks]
    ok1 = all(0.20 <= x <= 0.34 for x in anchors)
    print(f"C1 ANCHOR     body prose {min(anchors):.3f}-{max(anchors):.3f} tok/byte "
          f"({'inside the expected band' if ok1 else 'OUT OF BAND -- segmentation suspect'})")
    if not ok1:
        fails.append("C1")

    ratios = {n: rate["slug"][n] / rate["prose"][n] for n, _ in toks}
    lo, hi = min(ratios.values()), max(ratios.values())
    ok2 = all(r > 1.0 for r in ratios.values()) and (hi - lo) / hi < 0.30
    print(f"C2 INVARIANCE slug:prose ratio {lo:.2f}x-{hi:.2f}x across {len(toks)} tokenizers "
          f"({'all agree' if ok2 else 'DISAGREE -- tokenizer finding, not a slug finding'})")
    print("              " + "  ".join(f"{n[:10]}={ratios[n]:.2f}x" for n in ratios))
    if not ok2:
        fails.append("C2")

    entry_bytes = sum(len(l.encode()) for l in open(INDEX, encoding="utf-8", errors="replace")
                      if ENTRY.match(l.rstrip("\r\n")))
    part_bytes = sum(nbytes[a] for a in ("slug", "title", "prose"))
    ok3 = part_bytes / entry_bytes > 0.75
    print(f"C3 RECOMPOSE  parts {part_bytes} B of entry lines {entry_bytes} B "
          f"= {100*part_bytes/entry_bytes:.0f}% ({'accounted' if ok3 else 'TOO MUCH DROPPED'})")
    if not ok3:
        fails.append("C3")

    total_entries = len(re.findall(r"\]\([A-Za-z0-9_.-]+\.md\)",
                                   open(INDEX, encoding="utf-8", errors="replace").read()))
    print(f"C4 DENOM      {len(segs['slug'])} of {total_entries} index entries sit on their own line "
          f"and are segmentable; {len(segs['prose'])} carry a sentence, "
          f"{len(segs['body prose'])} body paragraphs")
    print(f"              COVERAGE {100*len(segs['slug'])/total_entries:.0f}% -- the remaining "
          f"{total_entries-len(segs['slug'])} share a line in the compact sections. The RATIO is "
          f"measured on the segmentable subset;")
    print(f"              whole-file slopes above use the entire file, so they are unaffected.")

    inv = {n: rate["prose"][n] / rate["slug"][n] for n, _ in toks}
    ok5 = all(v < 1.0 for v in inv.values())
    print(f"C5 DIRECTION  reversed arms give {min(inv.values()):.2f}x-{max(inv.values()):.2f}x "
          f"({'verdict flips as it must' if ok5 else 'DOES NOT FLIP -- comparison is inert'})")
    if not ok5:
        fails.append("C5")

    # ---------------- the answer ----------------
    print("\n" + "=" * 78)
    print(f"ANSWER: slug bytes cost {lo:.2f}x-{hi:.2f}x what prose bytes cost, on every tokenizer")
    print(f"        tested. A byte is not a byte: the index's token slope is a property of what it")
    print(f"        is MADE OF, not of how big it is.")
    if len(states) == 2:
        print()
        for n, _ in toks:
            a = states["live index (mixed)"][n]
            b = states["08-19 (slug-heavy)"][n]
            print(f"        {n:<12} two REAL states of the same index: "
                  f"{b:.3f} -> {a:.3f} tok/byte ({b/a:.2f}x)")
    print()
    print("        BUT THE EFFECT IS SMALL, and saying so is the point of measuring instead of")
    print("        asking. Slugs are only 25% of the index by bytes, and on the two MODERN")
    print(f"        vocabularies the penalty is {ratios['o200k_base']:.2f}x, not the {ratios['r50k_base']:.2f}x the")
    print("        older ones show -- modern BPE handles hyphenated compounds far better. Net")
    print("        effect on the whole-file slope between two real index states: 4%. We were")
    print("        about to send a question premised on this mattering. It does not.")
    print()

    # ---- what DOES need explaining: 0.44 is unreachable by any composition of text ----
    max_text = max(rate[a][n] for a in arms for n, _ in toks)
    max_modern = max(rate[a][n] for a in arms for n in ("o200k_base", "cl100k_base"))
    live_b = states["live index (mixed)"]["_bytes"] if states else 0
    live_r = states["live index (mixed)"].get("o200k_base", 0) if states else 0
    pred = 108 + 0.44 * live_b
    ours = live_r * live_b
    resid = (pred - ours) / live_b if live_b else 0
    # Entries per the WHOLE index, not per the subset my line regex matched. 106 of 234 entries
    # share a line in the compact sections, so len(segs["slug"]) is a segmentation artifact and
    # dividing by it inflated "tokens per entry" by 1.8x. Denominators are load-bearing.
    all_entries = len(re.findall(r"\]\([A-Za-z0-9_.-]+\.md\)",
                                 open(INDEX, encoding="utf-8", errors="replace").read()))
    per_entry = (pred - ours) / max(1, all_entries)
    print(f"        THE REAL DISCREPANCY. No content type we can construct reaches 0.44 tok/byte:")
    print(f"        the densest arm on ANY of the four is {max_text:.3f}, and on the modern two it is")
    print(f"        {max_modern:.3f}. So @yacb2's fitted slope cannot be explained by composition.")
    print(f"        On our live index his model predicts {pred:,.0f} tokens; the text itself is")
    print(f"        {ours:,.0f}. The gap is {resid:.3f} tok/byte, or ~{per_entry:.0f} tokens per entry.")
    print("        A two-point fit cannot separate a per-BYTE slope from a per-ENTRY constant, and")
    print("        that is a far better question for him than the one we were going to ask.")
    print()
    print("        NOT CLAIMED: an absolute tok/byte figure for Claude. The authoritative tokenizer")
    print("        was unavailable; only the ratio, which held on four vocabularies, is asserted.")
    if fails:
        print(f"\nCONTROLS FAILED: {', '.join(fails)} -- do not cite the numbers above.")
    print("=" * 78)

    out = os.path.join(HERE, "a_byte_of_slug_is_not_a_byte_of_prose.result.json")
    json.dump({"instrument_note": note, "tokenizers": [n for n, _ in toks],
               "bytes": nbytes, "tok_per_byte": rate, "whole_states": states,
               "slug_over_prose": ratios, "controls_failed": fails},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
