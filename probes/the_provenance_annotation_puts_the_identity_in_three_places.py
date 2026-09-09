"""Connector 0.1.1 recovers the linked document handle, and copies the identity twice more.

WHY THIS EXISTS. On 2026-09-08 we measured that `freeze_record` in memstrata-inspeximus-connector
0.1.0 dropped the raw source dict of any record reached through `links`: with one primary and one
linked source, `PRIMARY-DOC` appeared in the envelope and `LINKED-RUNBOOK` appeared nowhere in it.
On the primary record the same path also mislabelled `channel` as `doc` while an explicit
`principal` supplied the identity. @yadu9989 published 0.1.1 the same night, adding
`writer_metadata.source_provenance`, and asked for our view on the annotation before it goes into
the joint fixture.

WHAT THIS MEASURES, and it is not "did the fix work". That part is one assertion. The annotation
keeps the raw `source` dict of every associated record, so the SAME identity string now appears in
more places in one envelope than it did before. His letter proposes a deletion sequence in the same
breath -- block the identity, account for deliveries in flight, then purge the covered content --
and neither the release notes nor `docs/SOURCE_PROVENANCE.md` says where in an envelope the covered
content now lives. An erasure aimed at `sources[]` was already incomplete at 0.1.0; this measures by
how much 0.1.1 widens it.

AND THE 64 KiB CEILING MOVES. 0.1.0 checks `MAX_BODY_BYTES` at enqueue only. 0.1.1 checks it in
`freeze_record` as well, which is the better place, and the annotation adds bytes proportional to
the number of visible links times the size of each raw source. So a record that froze and enqueued
on 0.1.0 can raise `ProducerError` on 0.1.1 with no change to the record. The migration notes say
queued bytes are never rewritten, which is a different question. This finds the crossover.

BOTH VERSIONS RUN, IN SUBPROCESSES, FROM A CLONE THIS FILE MAKES ITSELF. Two tags of one package
cannot share an interpreter under one module name, and a probe that imported whatever was installed
would report one version's behaviour twice while looking like a comparison. The clone is from the
public URL at two tags, so the measurement is reproducible off this machine; no network, no clone,
exit 2 and no numbers.

CONTROLS, because every claim here is about a string being present or absent, and a search that
cannot see its target reports a confident zero:
  * a marker placed in the LINKED source must be found by the same counter that reports the
    absences, or the absences mean nothing;
  * a marker placed in NO record must be found zero times, or the counter finds everything;
  * each arm asserts the `__version__` it actually imported, so two runs of one version cannot
    masquerade as a comparison;
  * the 0.1.0 arm must REPRODUCE the original defect. If a later tag ever fixes it there, this
    control goes red instead of the fix silently ceasing to be measured;
  * the size crossover is two-sided: the same record must be ACCEPTED by 0.1.0 and REJECTED by
    0.1.1, not merely rejected by 0.1.1.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "https://github.com/yadu9989/memstrata-inspeximus-connector.git"
TAGS = ("v0.1.0", "v0.1.1")

# The identity under test, and two markers that make the counter falsifiable.
PRINCIPAL = "billing-team"
PRIMARY_DOC = "PRIMARY-DOC-synthetic-architecture"
LINKED_DOC = "LINKED-RUNBOOK-synthetic-tokens"
ABSENT_MARKER = "MARKER-THAT-IS-IN-NO-RECORD-AT-ALL"

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"

WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import memstrata_mnemo_connector as pkg
from memstrata_mnemo_connector.producer import freeze_record, ProducerError, canonical_bytes

PRINCIPAL, PRIMARY_DOC, LINKED_DOC = sys.argv[2], sys.argv[3], sys.argv[4]


class ScopedWriter:
    def __init__(self, items):
        self.items = items

    def __getattr__(self, name):
        if name == "_effective_value":
            return None
        raise AssertionError("No unscoped access is permitted")


def records(n_links, filler=""):
    primary = {
        "id": "primary-1",
        "text": "Synthetic billing service uses service tokens.",
        "key": "synthetic-billing::auth",
        "status": "active",
        "ts": 1782700000.0,
        "source": {"principal": PRINCIPAL, "doc": PRIMARY_DOC + filler},
        "links": ["support-%d" % i for i in range(n_links)],
    }
    linked = [
        {"id": "support-%d" % i,
         "source": {"principal": PRINCIPAL, "doc": LINKED_DOC + ("-%d" % i) + filler}}
        for i in range(n_links)
    ]
    return primary, linked


def envelope(n_links, filler=""):
    primary, linked = records(n_links, filler)
    return freeze_record(ScopedWriter([primary, *linked]), primary)


def count_in(obj, needle):
    """Occurrences of a string anywhere in the envelope, keys and values alike."""
    return json.dumps(obj, sort_keys=True).count(needle)


def strip_sources(fact):
    """The narrowest plausible erasure: clear the compact source labels."""
    out = json.loads(json.dumps(fact))
    out["fact_record"]["sources"] = []
    out["fact_record"]["corroboration_count"] = 0
    return out


out = {"version": pkg.__version__}
env = envelope(1)
fact = env["fact_record"]
out["primary_channel"] = fact["sources"][0]["channel"]
out["sources_len"] = len(fact["sources"])
out["primary_doc_hits"] = count_in(env, PRIMARY_DOC)
out["linked_doc_hits"] = count_in(env, LINKED_DOC)
out["absent_marker_hits"] = count_in(env, sys.argv[5])
out["principal_hits"] = count_in(env, PRINCIPAL)
out["principal_hits_after_stripping_sources"] = count_in(strip_sources(env), PRINCIPAL)
out["linked_doc_hits_after_stripping_sources"] = count_in(strip_sources(env), LINKED_DOC)
out["has_source_provenance"] = "source_provenance" in fact.get("writer_metadata", {})
out["bytes_one_link"] = len(canonical_bytes(env))

# Does the linked record's TEXT leak, as distinct from its source?
primary, linked = records(1)
linked[0]["text"] = "LINKED-TEXT-SHOULD-NOT-TRAVEL"
leak = freeze_record(ScopedWriter([primary, *linked]), primary)
out["linked_text_hits"] = count_in(leak, "LINKED-TEXT-SHOULD-NOT-TRAVEL")

# Repeating a link, and linking to self, must not add associations.
primary, linked = records(1)
primary["links"] = ["support-0", "support-0", "primary-1"]
dup = freeze_record(ScopedWriter([primary, *linked]), primary)["fact_record"]
prov = dup.get("writer_metadata", {}).get("source_provenance")
out["associations_under_duplicate_links"] = len(prov["associations"]) if prov else None

# A POSITIONAL REFERENCE UNDER AN OPERATION THAT REMOVES ENTRIES. `source_index` is an
# index into `sources[]`. Erasure is the operation both sides are designing, so measure what
# one compacting removal does to every remaining association.
# THREE sources, not two. With two, removing the first leaves a dangling index, which any
# reader notices. With three it resolves silently to the WRONG principal, which is the
# failure worth reporting.
two = [
    {"id": "primary-1", "text": "Synthetic billing service uses service tokens.",
     "key": "synthetic-billing::auth", "status": "active", "ts": 1782700000.0,
     "source": {"principal": "erase-me-team", "doc": PRIMARY_DOC},
     "links": ["support-0", "support-1"]},
    {"id": "support-0", "source": {"principal": "keep-me-team", "doc": LINKED_DOC}},
    {"id": "support-1", "source": {"principal": "third-team", "doc": LINKED_DOC + "-b"}},
]
e2 = freeze_record(ScopedWriter(two), two[0])["fact_record"]
# 0.1.0 has no associations at all, so this arm is empty there rather than absent.
assoc = (e2["writer_metadata"].get("source_provenance") or {}).get("associations") or []
out["index_before"] = {a["writer_record_id"]: a["source_index"] for a in assoc}
out["principal_at_index_before"] = {
    a["writer_record_id"]: e2["sources"][a["source_index"]]["principal"] for a in assoc}
compacted = json.loads(json.dumps(e2))
compacted["sources"] = [s for s in compacted["sources"] if s["principal"] != "erase-me-team"]
compacted["corroboration_count"] = len(compacted["sources"])
out["principal_at_index_after_compacting_erasure"] = {
    a["writer_record_id"]: (compacted["sources"][a["source_index"]]["principal"]
                            if a["source_index"] is not None
                            and a["source_index"] < len(compacted["sources"]) else None)
    for a in assoc}

# Where does the 64 KiB ceiling bind? Grow the number of visible links, each with a
# 200-byte source annotation, until freeze refuses. Sizes are recorded on a ladder so the
# two arms can be compared at the SAME record rather than at each arm's own breaking point.
MAX = 64 * 1024
LADDER = (1, 10, 50, 171, 400)
first_refused, sizes = None, {}
for n in range(1, 401):
    try:
        e = envelope(n, filler="-" + "p" * 200)
    except ProducerError:
        first_refused = n
        break
    if n in LADDER:
        sizes[n] = len(canonical_bytes(e))
out["links_at_first_freeze_refusal"] = first_refused
out["envelope_bytes_by_links"] = sizes
out["links_at_first_envelope_over_64KiB"] = next(
    (n for n in sorted(sizes) if sizes[n] > MAX), None)
print(json.dumps(out))
'''


def _run(src_dir, tag):
    worker = os.path.join(src_dir, "_probe_worker.py")
    with open(worker, "w", encoding="utf-8") as fh:
        fh.write(WORKER)
    proc = subprocess.run(
        [sys.executable, worker, os.path.join(src_dir, "src"),
         PRINCIPAL, PRIMARY_DOC, LINKED_DOC, ABSENT_MARKER],
        capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError("%s worker failed: %s" % (tag, proc.stderr[-800:]))
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main():
    tmp = tempfile.mkdtemp(prefix="memstrata-two-tags-")
    try:
        clone = os.path.join(tmp, "repo")
        cl = subprocess.run(["git", "clone", "-q", REPO, clone],
                            capture_output=True, text=True, timeout=300)
        if cl.returncode != 0:
            print("CANNOT RUN: the connector could not be cloned from %s" % REPO)
            print(cl.stderr.strip()[-400:])
            return 2
        arms = {}
        for tag in TAGS:
            work = os.path.join(tmp, tag.replace(".", "_"))
            co = subprocess.run(["git", "-C", clone, "worktree", "add", "-q", work, tag],
                                capture_output=True, text=True, timeout=300)
            if co.returncode != 0:
                print("CANNOT RUN: tag %s is not in the clone" % tag)
                return 2
            arms[tag] = _run(work, tag)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    old, new = arms["v0.1.0"], arms["v0.1.1"]
    checks = []

    def check(name, ok, got):
        checks.append({"check": name, "pass": bool(ok), "got": got})

    check("CONTROL_each_arm_imported_the_tag_it_claims",
          old["version"] == "0.1.0" and new["version"] == "0.1.1",
          "%s and %s" % (old["version"], new["version"]))
    check("CONTROL_the_counter_finds_a_marker_that_IS_in_the_linked_source",
          new["linked_doc_hits"] > 0,
          "%d hits for the linked doc handle under 0.1.1" % new["linked_doc_hits"])
    check("CONTROL_the_counter_finds_zero_for_a_marker_in_no_record",
          old["absent_marker_hits"] == 0 and new["absent_marker_hits"] == 0,
          "0 hits in both arms")
    check("CONTROL_0_1_0_STILL_REPRODUCES_THE_DEFECT_WE_REPORTED",
          old["linked_doc_hits"] == 0 and old["primary_channel"] == "doc",
          "0.1.0: linked doc %d hits, primary channel %r"
          % (old["linked_doc_hits"], old["primary_channel"]))
    check("THE_LINKED_DOCUMENT_HANDLE_SURVIVES_AT_0_1_1",
          new["linked_doc_hits"] > 0 and new["has_source_provenance"],
          "%d hits, annotation present" % new["linked_doc_hits"])
    check("THE_CHANNEL_IS_NO_LONGER_INFERRED_FROM_AN_ACCOMPANYING_DOC",
          new["primary_channel"] == "unknown",
          "primary channel %r at 0.1.1 against %r at 0.1.0"
          % (new["primary_channel"], old["primary_channel"]))
    check("THE_COMPACT_SOURCE_LIST_IS_UNCHANGED_IN_LENGTH",
          old["sources_len"] == new["sources_len"] == 1,
          "one reported source in both arms, as his notes state")
    check("THE_IDENTITY_APPEARS_IN_MORE_PLACES_AT_0_1_1",
          new["principal_hits"] > old["principal_hits"],
          "%d occurrences of the principal at 0.1.1 against %d at 0.1.0"
          % (new["principal_hits"], old["principal_hits"]))
    check("AN_ERASURE_AIMED_AT_sources_LEAVES_MORE_BEHIND_AT_0_1_1",
          new["principal_hits_after_stripping_sources"]
          > old["principal_hits_after_stripping_sources"],
          "%d left at 0.1.1 against %d at 0.1.0"
          % (new["principal_hits_after_stripping_sources"],
             old["principal_hits_after_stripping_sources"]))
    check("LINKED_RECORD_TEXT_DOES_NOT_TRAVEL_IN_EITHER_ARM",
          old["linked_text_hits"] == 0 and new["linked_text_hits"] == 0,
          "0 hits for the linked record's text in both arms")
    check("A_REPEATED_OR_SELF_LINK_ADDS_NO_ASSOCIATION",
          new["associations_under_duplicate_links"] == 2,
          "%s associations for a primary plus one link named three times"
          % new["associations_under_duplicate_links"])
    check("THE_64KiB_CEILING_IS_ENFORCED_AT_FREEZE_ONLY_AT_0_1_1",
          new["links_at_first_freeze_refusal"] is not None
          and old["links_at_first_freeze_refusal"] is None,
          "0.1.1 refuses to freeze at %s links; 0.1.0 never refuses at freeze up to 400"
          % new["links_at_first_freeze_refusal"])
    # THE COMPARISON MUST BE AT THE SAME RECORD. Reading each arm's own breaking point
    # answers a different question, and the first version of this check did exactly that:
    # it asked where 0.1.0 crosses 64 KiB, got None, and reported a failure that was the
    # question's fault. 0.1.0 deduplicates every source by principal, so an envelope with
    # 400 links is the same size as one with a single link.
    _n = 171
    check("CONTROL_THE_SAME_RECORD_IS_ACCEPTED_BY_0_1_0",
          old["envelope_bytes_by_links"].get(str(_n)) is not None
          and old["envelope_bytes_by_links"][str(_n)] <= 64 * 1024
          and (new["links_at_first_freeze_refusal"] or 0) <= _n,
          "at %d links 0.1.0 freezes to %s bytes while 0.1.1 refuses at %s links"
          % (_n, old["envelope_bytes_by_links"].get(str(_n)),
             new["links_at_first_freeze_refusal"]))
    # The index question only exists at 0.1.1, because 0.1.0 has no associations to point.
    before = new["principal_at_index_before"]
    after = new["principal_at_index_after_compacting_erasure"]
    check("A_COMPACTING_ERASURE_SILENTLY_REPOINTS_A_LATER_source_index",
          after.get("support-0") == "third-team" and before.get("support-0") == "keep-me-team",
          "the association for support-0 resolved to %r before the removal and to %r after it, "
          "with no error raised" % (before.get("support-0"), after.get("support-0")))
    check("CONTROL_THE_INDEX_RESOLVED_CORRECTLY_BEFORE_THE_ERASURE",
          before.get("primary-1") == "erase-me-team"
          and before.get("support-0") == "keep-me-team"
          and before.get("support-1") == "third-team",
          "each of the three associations resolved to its own principal before the removal")
    check("THE_ENVELOPE_GROWS_WITH_LINKS_ONLY_AT_0_1_1",
          old["envelope_bytes_by_links"].get("1") == old["envelope_bytes_by_links"].get("171")
          and new["envelope_bytes_by_links"]["1"] < new["envelope_bytes_by_links"]["50"],
          "0.1.0 %s bytes at 1 and at 171 links; 0.1.1 %s -> %s bytes from 1 to 50 links"
          % (old["envelope_bytes_by_links"].get("1"),
             new["envelope_bytes_by_links"]["1"], new["envelope_bytes_by_links"]["50"]))

    out = {
        "probe": os.path.basename(__file__),
        "repo": REPO,
        "tags": list(TAGS),
        "arms": arms,
        "bytes_for_one_linked_source": {"v0.1.0": old["bytes_one_link"],
                                        "v0.1.1": new["bytes_one_link"]},
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "finding": (
            "Connector 0.1.1 fixes both defects we reported. The linked record's document handle "
            "survives in writer_metadata.source_provenance, and the primary record's channel is no "
            "longer inferred as 'doc' when an explicit principal supplied the identity. The "
            "compact sources list still reports one source, as his notes say. What the annotation "
            "also does is copy the identity: the principal string appears %d times in a "
            "one-link envelope at 0.1.1 against %d at 0.1.0, and an erasure that clears sources[] "
            "leaves %d of them against %d before. The linked record's text does not travel, so the "
            "widening is confined to what a writer put in `source`. Separately, 0.1.1 enforces the "
            "64 KiB limit inside freeze_record, so a record that froze on 0.1.0 and failed only at "
            "enqueue now raises ProducerError at freeze: with 200-byte source annotations that "
            "happens at %s links, where 0.1.0 freezes the same record to %s bytes because it "
            "deduplicates every source by principal and its envelope does not grow with links. "
            "And `source_index` is positional under an operation designed to remove entries: with "
            "three sources, removing the first by compaction leaves the association for the second "
            "record resolving to the third record's principal, %r instead of %r, with no error."
            % (new["principal_hits"], old["principal_hits"],
               new["principal_hits_after_stripping_sources"],
               old["principal_hits_after_stripping_sources"],
               new["links_at_first_freeze_refusal"],
               old["envelope_bytes_by_links"].get("171"),
               new["principal_at_index_after_compacting_erasure"].get("support-0"),
               new["principal_at_index_before"].get("support-0"))),
        "scope": (
            "Synthetic records only, one level of links, one principal shared by every source, and "
            "200-byte source annotations in the size sweep. Occurrence counts are over the "
            "canonical JSON of the envelope, so they count the string wherever it appears, in a key "
            "or a value. The erasure arm models the narrowest plausible erasure, clearing "
            "sources[]; it is not a claim about what any receiver actually deletes."),
    }
    with open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("checks", "all_passed", "finding")},
                     indent=1, ensure_ascii=False))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
