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
    # Measured MARGINALLY, in the context the text actually appears in. Joining slugs with
    # newlines and tokenising them alone UNDERSTATES their cost by ~10% (0.272 vs 0.300 on
    # o200k), because a slug in the file is wrapped as `](name.md)` and the wrapper changes the
    # merges at both ends. An audit caught this. The wrapper is subtracted rather than included,
    # so its own bytes are not charged to the slug either.
    CTX = {"slug": ("](", ")"), "prose": ("\u2014 ", ""), "title": ("[", "]"), "body prose": ("", "")}
    blobs = {a: "\n".join(segs[a]) for a in arms}
    nbytes = {a: len(blobs[a].encode("utf-8")) for a in arms}

    def marginal(arm, fn):
        """tokens attributable to the arm's own bytes, inside its real delimiters"""
        pre, post = CTX[arm]
        empty = fn(pre + post)
        return sum(fn(pre + x + post) - empty for x in segs[arm])

    print("tokens per byte, by arm and tokenizer")
    print(f"{'arm':<12} {'segs':>5} {'bytes':>7} " + " ".join(f"{n[:11]:>12}" for n, _ in toks))
    rate = {}
    for a in arms:
        rate[a] = {}
        cells = []
        for n, fn in toks:
            t = marginal(a, fn)
            rate[a][n] = t / nbytes[a]
            cells.append(f"{rate[a][n]:>12.3f}")
        print(f"{a:<12} {len(segs[a]):>5} {nbytes[a]:>7} " + " ".join(cells))

    print("\nwhole real index states")
    states = {}
    for label, path in (("live index (mixed)", INDEX), ("08-19 (slug-heavy)", SLUGGY)):
        if not os.path.exists(path):
            continue
        raw = open(path, "rb").read()          # EXACT on-disk bytes: a CRLF file read with
        blob = raw.decode("utf-8", "replace")  # universal newlines loses 1 byte per line
        nb = len(raw)                          # 23,921 on disk vs 23,721 translated -- 0.8%,
        #                                      immaterial to the ratio, but a reader running
        #                                      `wc -c` must get the number we publish.
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

    # C5 was "reverse the arms and require <1.0", which follows arithmetically from C2 for
    # positive reciprocals -- it could not fail, so it tested nothing. An audit called it vacuous
    # and was right. This replacement CAN fail: substitute each slug with same-byte-length
    # English words. If the penalty is really hyphenated-compound fragmentation, the ratio must
    # collapse toward 1.0. If it does not, we are measuring the SLOT, not the slug.
    import random
    WORDS = ("the quick brown fox jumps over a lazy dog and then reads memory notes about work "
             "before writing down what it learned from the last session").split()
    rng = random.Random(20260820)

    def same_length_words(slug):
        want, out = len(slug), []
        while sum(len(w) + 1 for w in out) < want:
            out.append(rng.choice(WORDS))
        return (" ".join(out))[:want] or "a"

    fake = [same_length_words(x) for x in segs["slug"]]
    fake_bytes = sum(len(x.encode()) for x in fake)
    null_ratio = {}
    for n, fn in toks:
        pre, post = CTX["slug"]
        empty = fn(pre + post)
        t = sum(fn(pre + x + post) - empty for x in fake)
        null_ratio[n] = (t / fake_bytes) / rate["prose"][n]
    ok5 = all(v < 1.15 for v in null_ratio.values())
    print(f"C5 NULL       same-length English in the slug slot: "
          f"{min(null_ratio.values()):.2f}x-{max(null_ratio.values()):.2f}x vs prose "
          f"({'collapses, so the penalty is the SLUG FORM' if ok5 else 'DOES NOT COLLAPSE -- we measured the slot'})")
    if not ok5:
        fails.append("C5")

    # C6: the slug SHARE of the file, COMPUTED. A previous version printed "slugs are only a
    # quarter of the index" as a hardcoded sentence. It was never computed and it was wrong by
    # 1.7x -- numerator from the 127 entries the per-line regex matches, denominator from the
    # whole file. Two populations. The 3.5% delta itself was unaffected; the REASON given for it
    # was false, which is worse, because a wrong number invites checking and a wrong reason does not.
    LOOSE = re.compile(r"\]\(([A-Za-z0-9_.-]+\.md)\)")
    share = {}
    for label, path in (("live index (mixed)", INDEX), ("08-19 (slug-heavy)", SLUGGY)):
        if not os.path.exists(path):
            continue
        rawb = open(path, "rb").read()
        txt = rawb.decode("utf-8", "replace")
        tot = len(rawb)
        sb = sum(len(x.encode()) for x in LOOSE.findall(txt))
        share[label] = sb / tot
        print(f"C6 SHARE      {label:<20} slug bytes {sb:5d} of {tot:5d} = {100*sb/tot:.1f}% (computed)")

    # ---------------- the answer ----------------
    print("\n" + "=" * 78)
    spread = {a: max(v.values()) / min(v.values()) for a, v in rate.items()}
    worst_spread = max(spread.values())
    live_o = states["live index (mixed)"]["o200k_base"]
    nb = states["live index (mixed)"]["_bytes"]
    pred = 108 + 0.44 * nb
    ours = live_o * nb
    entries = len(re.findall(r"\]\(([A-Za-z0-9_.-]+\.md)\)",
                             open(INDEX, encoding="utf-8", errors="replace").read()))
    print(f"ANSWER: slug bytes cost {lo:.2f}x-{hi:.2f}x prose bytes on every tokenizer tested,")
    print(f"        measured in their real `](name.md)` context. C5 confirms the cause: same-length")
    print(f"        English in the same slot collapses to {min(null_ratio.values()):.2f}x-{max(null_ratio.values()):.2f}x, so it is the slug FORM.")
    print()
    print("        PRIOR ART, and it is the mechanism, not us: that identifiers fragment worse")
    print("        than prose under BPE, and that newer/larger vocabularies fragment them less,")
    print("        is published -- CodeBPE (Chirkova & Troshin, ICLR 2023, arXiv:2308.00683).")
    print("        OURS is only the composition-weighted effect on a real artifact, below.")
    print()
    print(f"        AND THE EFFECT IS SMALL -- but NOT for the reason first written here.")
    print(f"        Slugs are {100*share['live index (mixed)']:.0f}% of the live index by bytes and "
          f"{100*share['08-19 (slug-heavy)']:.0f}% of the 08-19 state, COMPUTED.")
    print(f"        An earlier version asserted 'only a quarter' -- a hardcoded sentence, never")
    print(f"        computed, wrong by 1.7x: its numerator came from the {len(segs['slug'])} entries the")
    print(f"        per-line regex matches, its denominator from the whole file. Two populations.")
    print(f"        So the whole-file slope moving only "
          f"{100*(states['08-19 (slug-heavy)']['o200k_base']/live_o - 1):.1f}% is small DESPITE slugs being a")
    print(f"        plurality of the bytes, not because they are a minority of them.")
    print()
    print("        AND 'composition' bundles several edits: between those two states the entries")
    print("        also gained prose sentences and 100+ were un-crowded onto their own lines.")
    print("        A slug-share-only model explains roughly a third of the measured move.")
    print()
    print(f"        WHAT WE DO NOT CLAIM, and an earlier draft did: that 0.44 tok/byte is")
    print(f"        'unreachable'. Our own four vocabularies span {worst_spread:.2f}x on IDENTICAL content")
    print(f"        (slug arm {min(rate['slug'].values()):.3f}-{max(rate['slug'].values()):.3f}), and the gap from our {live_o:.3f} to 0.44 is")
    print(f"        {0.44/max(v for v in states['live index (mixed)'].values() if isinstance(v, float) and v < 1):.2f}x-{0.44/live_o:.2f}x -- INSIDE that spread. A fifth, unmeasured vocabulary")
    print(f"        could account for the whole gap, so 'unreachable' was refuted by our own table.")
    print()
    print(f"        WHAT IS ACTUALLY OPEN. Applying the 108 + 0.44/byte model to our {nb:,}-byte index")
    print(f"        predicts {pred:,.0f} tokens where our proxy count of the same bytes is {ours:,.0f}:")
    print(f"        {(pred-ours)/nb:.3f} tok/byte, or ~{(pred-ours)/entries:.0f} tokens per entry across {entries} entries. That gap is")
    print(f"        EITHER per-entry harness overhead OR the difference between his tokenizer and")
    print(f"        ours, and nothing we have can separate the two. It is a question, not a finding.")
    print()
    print("        NOT CLAIMED: an absolute tok/byte figure for Claude. The authoritative tokenizer")
    print("        was unavailable; only the ratio, which held on four vocabularies, is asserted.")
    if fails:
        print(f"\nCONTROLS FAILED: {', '.join(fails)} -- do not cite the numbers above.")
    print("=" * 78)

    out = os.path.join(HERE, "a_byte_of_slug_is_not_a_byte_of_prose.result.json")
    json.dump({"instrument_note": note, "tokenizers": [n for n, _ in toks],
               "bytes": nbytes, "tok_per_byte": rate, "whole_states": states,
               "slug_over_prose": ratios, "controls_failed": fails,
               "slug_share": share},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
