"""Connector 0.1.1 recovers the linked document handle, and adds one copy of each raw source.

WHY THIS EXISTS. On 2026-09-08 we measured that `freeze_record` in memstrata-inspeximus-connector
0.1.0 dropped the raw source dict of any record reached through `links`: with one primary and one
linked source, `PRIMARY-DOC` appeared in the envelope and `LINKED-RUNBOOK` appeared nowhere in it.
On the primary record the same path also mislabelled `channel` as `doc` while an explicit
`principal` supplied the identity. @yadu9989 published 0.1.1 the same night, adding
`writer_metadata.source_provenance`, and asked for our view on the annotation before it goes into
the joint fixture.

WHAT THIS MEASURES, and it is not "did the fix work". That part is one assertion. The annotation
keeps the raw `source` dict of every associated record, so an identity now survives an erasure that
used to remove it. His letter proposes a deletion sequence in the same breath -- block the identity,
account for deliveries in flight, then purge the covered content -- and neither the release notes
nor `docs/SOURCE_PROVENANCE.md` names the annotation as covered content.

EVERY FIXTURE-DEPENDENT CLAIM IS RUN ON BOTH FIXTURES, because the first version of this file was
not. It shared one principal across every record, which is exactly the input 0.1.0's dedup collapses,
and on that input 0.1.0's envelope is a constant 660 bytes however many links it carries. The check
named THE_ENVELOPE_GROWS_WITH_LINKS_ONLY_AT_0_1_1 was green for that reason and not because of
anything in his code: with distinct principals 0.1.0 grows too, 707 bytes to 20,152 over 1 to 400
links. A hostile re-run found it; the check is gone and the two fixtures are now both first-class.
The occurrence counts have the same shape, so they are reported as the invariant that holds in
both -- one added copy per associated record -- with the doubling named as the shared case.

AND THE ERASURE ARM COMPARES AGAINST THE ERASURE THAT USED TO WORK. Clearing `sources[]` alone was
never complete at either tag, because `source` sits in the pre-existing `metadata_keys` allowlist and
is echoed at both. The narrowest erasure that was COMPLETE at 0.1.0 clears `sources[]` and drops
`writer_metadata.source`. Measuring against that is stricter than measuring against a strawman, and
it is what makes the number mean anything.

`source_index` IS A CONTRACT QUESTION, NOT A DEFECT. His code never removes an entry from
`sources[]`; erasure is outside schema_v0 pilot support by his own contract. So both removals are
measured here, and the finding is the difference between them: a positional reference is correct
under a tombstone and silently repoints under a compaction, so a deletion protocol has to say which.

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
  * every count is reported for both the shared-principal and the distinct-principal fixture, and
    a check that holds in only one of them says which in its own name;
  * the size crossover is two-sided: the same record must be ACCEPTED by 0.1.0 and REFUSED by 0.1.1,
    at every filler size swept.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = "https://github.com/yadu9989/memstrata-inspeximus-connector.git"
TAGS = ("v0.1.0", "v0.1.1")

PRINCIPAL = "billing-team"
PRIMARY_DOC = "PRIMARY-DOC-synthetic-architecture"
LINKED_DOC = "LINKED-RUNBOOK-synthetic-tokens"
ABSENT_MARKER = "MARKER-THAT-IS-IN-NO-RECORD-AT-ALL"

# The size sweep's only free parameter, swept rather than chosen, because the first version quoted
# one crossover as if it were a property of the code. It is a function of this number.
FILLERS = (0, 50, 200, 1000)
LADDER = (1, 50, 171, 400)

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"

WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import memstrata_mnemo_connector as pkg
from memstrata_mnemo_connector.producer import freeze_record, ProducerError, canonical_bytes

PRINCIPAL, PRIMARY_DOC, LINKED_DOC, ABSENT = sys.argv[2:6]
FILLERS = [int(x) for x in sys.argv[6].split(",")]
LADDER = [int(x) for x in sys.argv[7].split(",")]


class ScopedWriter:
    def __init__(self, items):
        self.items = items

    def __getattr__(self, name):
        if name == "_effective_value":
            return None
        raise AssertionError("No unscoped access is permitted")


def records(n_links, filler_bytes=0, distinct=False):
    pad = ("-" + "p" * filler_bytes) if filler_bytes else ""
    primary = {
        "id": "primary-1",
        "text": "Synthetic billing service uses service tokens.",
        "key": "synthetic-billing::auth",
        "status": "active",
        "ts": 1782700000.0,
        "source": {"principal": PRINCIPAL, "doc": PRIMARY_DOC + pad},
        "links": ["support-%d" % i for i in range(n_links)],
    }
    linked = [
        {"id": "support-%d" % i,
         # NOT a suffix of PRINCIPAL. "billing-team-0" contains "billing-team", and the
         # counter is a substring count, so the distinct fixture read the primary identity
         # as 3 occurrences instead of 2 and the invariant check went red on the fixture
         # rather than on the code. Same class as the shared-principal artifact above.
         "source": {"principal": ("linked-team-%d" % i) if distinct else PRINCIPAL,
                    "doc": LINKED_DOC + ("-%d" % i) + pad}}
        for i in range(n_links)
    ]
    return primary, linked


def envelope(n_links, filler_bytes=0, distinct=False):
    primary, linked = records(n_links, filler_bytes, distinct)
    return freeze_record(ScopedWriter([primary, *linked]), primary)


def count_in(obj, needle):
    """Occurrences of a string anywhere in the envelope, keys and values alike."""
    return json.dumps(obj, sort_keys=True).count(needle)


def erasures(env):
    """Three erasures of increasing reach, applied to a copy."""
    def cut(fn):
        out = json.loads(json.dumps(env))
        fn(out["fact_record"])
        return out

    def clear_sources(f):
        f["sources"] = []
        f["corroboration_count"] = 0

    def clear_sources_and_echo(f):
        clear_sources(f)
        f.get("writer_metadata", {}).pop("source", None)

    def clear_everything(f):
        clear_sources_and_echo(f)
        f.get("writer_metadata", {}).pop("source_provenance", None)

    return {"sources_only": cut(clear_sources),
            "sources_and_metadata_echo": cut(clear_sources_and_echo),
            "sources_metadata_echo_and_provenance": cut(clear_everything)}


def first_refusal(filler_bytes, distinct, hi=800):
    """The smallest link count freeze_record refuses, by bisection. None if it never does.

    Bisection, not a linear scan, because the linear version made this probe quadratic and the
    sweep now covers four fillers on two fixtures. Refusal is monotone in the link count: the
    envelope only grows.
    """
    try:
        envelope(hi, filler_bytes, distinct)
        return None
    except ProducerError:
        pass
    lo = 1
    try:
        envelope(lo, filler_bytes, distinct)
    except ProducerError:
        return lo
    while hi - lo > 1:
        mid = (lo + hi) // 2
        try:
            envelope(mid, filler_bytes, distinct)
            lo = mid
        except ProducerError:
            hi = mid
    return hi


out = {"version": pkg.__version__, "fixtures": {}}
for distinct in (False, True):
    key = "distinct_principals" if distinct else "shared_principal"
    env = envelope(1, 0, distinct)
    fact = env["fact_record"]
    linked_principal = "linked-team-0" if distinct else PRINCIPAL
    cut = erasures(env)
    f = {
        "primary_channel": fact["sources"][0]["channel"],
        "sources_len": len(fact["sources"]),
        "primary_doc_hits": count_in(env, PRIMARY_DOC),
        "linked_doc_hits": count_in(env, LINKED_DOC),
        "absent_marker_hits": count_in(env, ABSENT),
        "primary_principal_hits": count_in(env, PRINCIPAL),
        "linked_principal_hits": count_in(env, linked_principal),
        "has_source_provenance": "source_provenance" in fact.get("writer_metadata", {}),
        "bytes_one_link": len(canonical_bytes(env)),
        "after_erasure": {
            name: {"primary_principal": count_in(e, PRINCIPAL),
                   "linked_principal": count_in(e, linked_principal),
                   "linked_doc": count_in(e, LINKED_DOC)}
            for name, e in cut.items()},
    }

    # Where in the envelope does each occurrence live? A count is not a location, and the
    # pre-existing writer_metadata echo is present at BOTH tags, so a raw count credits the
    # annotation with a copy it did not add.
    paths = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + ["[%d]" % i])
        elif isinstance(node, str) and PRINCIPAL in node:
            paths.append(".".join(path))

    walk(env, [])
    f["primary_principal_paths"] = sorted(paths)

    sizes = {}
    for n in LADDER:
        try:
            sizes[n] = len(canonical_bytes(envelope(n, 200, distinct)))
        except ProducerError:
            sizes[n] = "REFUSED"
    f["envelope_bytes_by_links_at_200B"] = sizes
    f["first_freeze_refusal_by_filler"] = {b: first_refusal(b, distinct) for b in FILLERS}
    out["fixtures"][key] = f

# The linked record's TEXT must not travel, as distinct from its source.
primary, linked = records(1)
linked[0]["text"] = "LINKED-TEXT-SHOULD-NOT-TRAVEL"
out["linked_text_hits"] = count_in(
    freeze_record(ScopedWriter([primary, *linked]), primary), "LINKED-TEXT-SHOULD-NOT-TRAVEL")

# Repeating a link, and linking to self, must not add associations.
primary, linked = records(1)
primary["links"] = ["support-0", "support-0", "primary-1"]
dup = freeze_record(ScopedWriter([primary, *linked]), primary)["fact_record"]
prov = dup.get("writer_metadata", {}).get("source_provenance")
out["associations_under_duplicate_links"] = len(prov["associations"]) if prov else None

# A POSITIONAL REFERENCE UNDER TWO REMOVALS. His code performs neither; a deletion protocol
# has to choose one, and the two disagree.
three = [
    {"id": "primary-1", "text": "Synthetic billing service uses service tokens.",
     "key": "synthetic-billing::auth", "status": "active", "ts": 1782700000.0,
     "source": {"principal": "erase-me-team", "doc": PRIMARY_DOC},
     "links": ["support-0", "support-1"]},
    {"id": "support-0", "source": {"principal": "keep-me-team", "doc": LINKED_DOC}},
    {"id": "support-1", "source": {"principal": "third-team", "doc": LINKED_DOC + "-b"}},
]
e3 = freeze_record(ScopedWriter(three), three[0])["fact_record"]
assoc = (e3["writer_metadata"].get("source_provenance") or {}).get("associations") or []


def resolve(sources, associations):
    """What each association's source_index points at, or None when it points nowhere."""
    got = {}
    for a in associations:
        i = a.get("source_index")
        got[a["writer_record_id"]] = (
            sources[i]["principal"] if i is not None and i < len(sources) else None)
    return got


out["index_before"] = resolve(e3["sources"], assoc)
compacted = json.loads(json.dumps(e3))
compacted["sources"] = [s for s in compacted["sources"] if s["principal"] != "erase-me-team"]
out["index_after_compacting_removal"] = resolve(compacted["sources"], assoc)
tombstoned = json.loads(json.dumps(e3))
for s in tombstoned["sources"]:
    if s["principal"] == "erase-me-team":
        s["principal"] = "[erased]"
out["index_after_tombstone_removal"] = resolve(tombstoned["sources"], assoc)
print(json.dumps(out))
'''


def _run(src_dir, tag):
    worker = os.path.join(src_dir, "_probe_worker.py")
    with open(worker, "w", encoding="utf-8") as fh:
        fh.write(WORKER)
    proc = subprocess.run(
        [sys.executable, worker, os.path.join(src_dir, "src"),
         PRINCIPAL, PRIMARY_DOC, LINKED_DOC, ABSENT_MARKER,
         ",".join(str(x) for x in FILLERS), ",".join(str(x) for x in LADDER)],
        capture_output=True, text=True, timeout=1800)
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
    os_, ns = old["fixtures"]["shared_principal"], new["fixtures"]["shared_principal"]
    od, nd = old["fixtures"]["distinct_principals"], new["fixtures"]["distinct_principals"]
    checks = []

    def check(name, ok, got):
        checks.append({"check": name, "pass": bool(ok), "got": got})

    def at(d, n):
        return d.get(str(n), d.get(n))

    check("CONTROL_each_arm_imported_the_tag_it_claims",
          old["version"] == "0.1.0" and new["version"] == "0.1.1",
          "%s and %s" % (old["version"], new["version"]))
    check("CONTROL_the_counter_finds_a_marker_that_IS_in_the_linked_source",
          ns["linked_doc_hits"] > 0 and nd["linked_doc_hits"] > 0,
          "the linked doc handle is found in both 0.1.1 fixtures")
    check("CONTROL_the_counter_finds_zero_for_a_marker_in_no_record",
          max(f["absent_marker_hits"] for a in (old, new)
              for f in a["fixtures"].values()) == 0,
          "0 hits in all four fixture arms")
    check("CONTROL_0_1_0_STILL_REPRODUCES_THE_DEFECT_WE_REPORTED",
          os_["linked_doc_hits"] == 0 and od["linked_doc_hits"] == 0
          and os_["primary_channel"] == "doc",
          "0.1.0: linked doc 0 hits in both fixtures, primary channel %r"
          % os_["primary_channel"])
    check("THE_LINKED_DOCUMENT_HANDLE_SURVIVES_AT_0_1_1",
          ns["linked_doc_hits"] > 0 and ns["has_source_provenance"],
          "%d hits, annotation present" % ns["linked_doc_hits"])
    check("THE_CHANNEL_IS_NO_LONGER_INFERRED_FROM_AN_ACCOMPANYING_DOC",
          ns["primary_channel"] == "unknown" and nd["primary_channel"] == "unknown",
          "primary channel %r at 0.1.1 against %r at 0.1.0"
          % (ns["primary_channel"], os_["primary_channel"]))
    check("THE_COMPACT_SOURCE_LIST_IS_UNCHANGED_IN_LENGTH",
          os_["sources_len"] == ns["sources_len"] == 1
          and od["sources_len"] == nd["sources_len"] == 2,
          "one source under a shared principal and two under distinct ones, in both arms")
    check("EACH_ASSOCIATED_RECORD_ADDS_EXACTLY_ONE_COPY_OF_ITS_IDENTITY",
          nd["primary_principal_hits"] - od["primary_principal_hits"] == 1
          and nd["linked_principal_hits"] - od["linked_principal_hits"] == 1,
          "distinct principals: primary %d->%d, linked %d->%d"
          % (od["primary_principal_hits"], nd["primary_principal_hits"],
             od["linked_principal_hits"], nd["linked_principal_hits"]))
    check("UNDER_A_SHARED_PRINCIPAL_THE_TWO_COPIES_LAND_ON_ONE_STRING",
          ns["primary_principal_hits"] == 4 and os_["primary_principal_hits"] == 2,
          "%d occurrences at 0.1.1 against %d at 0.1.0, shared-principal fixture only"
          % (ns["primary_principal_hits"], os_["primary_principal_hits"]))
    check("CONTROL_ONE_OF_THOSE_OCCURRENCES_PREDATES_THE_ANNOTATION",
          "fact_record.writer_metadata.source.principal" in os_["primary_principal_paths"],
          "0.1.0 already echoes the raw source at %s" % os_["primary_principal_paths"])
    complete_old = os_["after_erasure"]["sources_and_metadata_echo"]
    complete_new = ns["after_erasure"]["sources_and_metadata_echo"]
    check("THE_ERASURE_THAT_WAS_COMPLETE_AT_0_1_0_IS_NO_LONGER_COMPLETE",
          complete_old["primary_principal"] == 0 and complete_new["primary_principal"] > 0,
          "clearing sources[] and dropping writer_metadata.source leaves %d copies of the "
          "principal at 0.1.1 against %d at 0.1.0, plus %d copies of the linked doc handle"
          % (complete_new["primary_principal"], complete_old["primary_principal"],
             complete_new["linked_doc"]))
    check("CONTROL_REACHING_THE_ANNOTATION_TOO_ERASES_IT",
          ns["after_erasure"]["sources_metadata_echo_and_provenance"]["primary_principal"] == 0
          and ns["after_erasure"]["sources_metadata_echo_and_provenance"]["linked_doc"] == 0,
          "adding source_provenance to the erasure leaves nothing")
    check("LINKED_RECORD_TEXT_DOES_NOT_TRAVEL_IN_EITHER_ARM",
          old["linked_text_hits"] == 0 and new["linked_text_hits"] == 0,
          "0 hits for the linked record's text in both arms")
    check("A_REPEATED_OR_SELF_LINK_ADDS_NO_ASSOCIATION",
          new["associations_under_duplicate_links"] == 2,
          "%s associations for a primary plus one link named three times"
          % new["associations_under_duplicate_links"])
    check("A_COMPACTING_REMOVAL_SILENTLY_REPOINTS_A_LATER_source_index",
          new["index_after_compacting_removal"].get("support-0") == "third-team"
          and new["index_before"].get("support-0") == "keep-me-team",
          "support-0 resolved to %r before and to %r after a compacting removal, with no error"
          % (new["index_before"].get("support-0"),
             new["index_after_compacting_removal"].get("support-0")))
    check("A_TOMBSTONE_REMOVAL_LEAVES_EVERY_ASSOCIATION_CORRECT",
          new["index_after_tombstone_removal"].get("support-0") == "keep-me-team"
          and new["index_after_tombstone_removal"].get("support-1") == "third-team",
          "every association still resolves to its own principal under a tombstone")
    check("CONTROL_THE_INDEX_RESOLVED_CORRECTLY_BEFORE_ANY_REMOVAL",
          new["index_before"] == {"primary-1": "erase-me-team", "support-0": "keep-me-team",
                                  "support-1": "third-team"},
          "each of the three associations resolved to its own principal")
    ceil_new = ns["first_freeze_refusal_by_filler"]
    ceil_new_d = nd["first_freeze_refusal_by_filler"]
    ceil_old = {**os_["first_freeze_refusal_by_filler"], **od["first_freeze_refusal_by_filler"]}
    check("ONLY_0_1_1_REFUSES_AT_FREEZE_AT_EVERY_FILLER_SWEPT",
          all(v is None for v in ceil_old.values())
          and all(v is not None for v in ceil_new.values())
          and all(v is not None for v in ceil_new_d.values()),
          "0.1.1 refuses at %s links for fillers %s (shared) and %s (distinct); 0.1.0 refuses "
          "nowhere up to 800 links in either fixture"
          % (list(ceil_new.values()), list(ceil_new.keys()), list(ceil_new_d.values())))
    check("THE_CROSSOVER_IS_A_FUNCTION_OF_THE_ANNOTATION_SIZE",
          len(set(ceil_new.values())) > 1,
          "the shared-principal crossover moves across %s links over fillers %s"
          % (list(ceil_new.values()), list(ceil_new.keys())))
    check("CONTROL_0_1_0_FREEZES_THE_RECORD_0_1_1_REFUSES",
          at(os_["envelope_bytes_by_links_at_200B"], 171) not in (None, "REFUSED")
          and at(od["envelope_bytes_by_links_at_200B"], 171) not in (None, "REFUSED")
          and at(ns["envelope_bytes_by_links_at_200B"], 171) == "REFUSED",
          "at 171 links and 200-byte annotations 0.1.0 freezes to %s bytes shared and %s "
          "distinct, where 0.1.1 refuses"
          % (at(os_["envelope_bytes_by_links_at_200B"], 171),
             at(od["envelope_bytes_by_links_at_200B"], 171)))
    check("THE_660_BYTE_CONSTANT_IS_A_DEDUP_ARTIFACT_OF_THE_SHARED_PRINCIPAL",
          at(os_["envelope_bytes_by_links_at_200B"], 1)
          == at(os_["envelope_bytes_by_links_at_200B"], 400)
          and at(od["envelope_bytes_by_links_at_200B"], 1)
          != at(od["envelope_bytes_by_links_at_200B"], 400),
          "0.1.0 is %s bytes at 1 and at 400 links under one principal, and %s -> %s under "
          "distinct ones"
          % (at(os_["envelope_bytes_by_links_at_200B"], 1),
             at(od["envelope_bytes_by_links_at_200B"], 1),
             at(od["envelope_bytes_by_links_at_200B"], 400)))

    out = {
        "probe": os.path.basename(__file__),
        "repo": REPO,
        "tags": list(TAGS),
        "supersedes": "the first version of this file, whose growth check was green because its "
                      "fixture shared one principal rather than because of anything in the code",
        "arms": arms,
        "checks": checks,
        "all_passed": all(c["pass"] for c in checks),
        "finding": (
            "Connector 0.1.1 closes both defects we reported, reproduced against the published "
            "tags: the linked record's document handle appears 0 times in a 0.1.0 envelope and is "
            "present at 0.1.1, and the primary record's channel reads 'unknown' rather than 'doc' "
            "when an explicit principal supplied the identity. The compact sources list is "
            "unchanged in length. What the annotation adds is one copy of each associated record's "
            "raw source: with distinct principals the primary identity goes from %d occurrences to "
            "%d and the linked one from %d to %d; under one shared principal both copies carry the "
            "same string and it goes from %d to %d. One of those occurrences predates the "
            "annotation, the writer_metadata.source echo present at both tags. The consequence for "
            "the deletion sequence: the narrowest erasure that was COMPLETE at 0.1.0, clearing "
            "sources[] and dropping writer_metadata.source, leaves %d copies of the identity at "
            "0.1.1 and the linked document handle with it, and neither the release notes nor "
            "SOURCE_PROVENANCE.md names the annotation as covered content. Separately, "
            "source_provenance_v1 addresses associations by position into sources[]: with three "
            "sources, a compacting removal of the first makes the second record's association "
            "resolve to the third record's principal with no error, while a tombstone leaves every "
            "association correct. His code performs neither, so this is a contract gap in a "
            "deletion protocol rather than a defect. Last, 0.1.1 enforces the 64 KiB limit inside "
            "freeze_record, so a record that froze on 0.1.0 can now raise at freeze; the crossover "
            "is a function of the annotation size, at %s links for fillers of %s bytes, and 0.1.0 "
            "refuses nowhere up to 800 links at any of them."
            % (od["primary_principal_hits"], nd["primary_principal_hits"],
               od["linked_principal_hits"], nd["linked_principal_hits"],
               os_["primary_principal_hits"], ns["primary_principal_hits"],
               complete_new["primary_principal"],
               list(ceil_new.values()), list(ceil_new.keys()))),
        "scope": (
            "Synthetic records only, one level of links, and two fixtures throughout: one principal "
            "shared by every record, and a distinct principal per record. Occurrence counts are "
            "over the canonical JSON of the envelope, so they count the string wherever it appears, "
            "in a key or a value; the paths are recorded beside the counts. The erasure arms model "
            "what a receiver would delete and are not a claim about what any receiver does. The "
            "crossover link counts depend on the annotation size and are reported as a sweep for "
            "that reason."),
    }
    with open(RESULT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: out[k] for k in ("checks", "all_passed", "finding")},
                     indent=1, ensure_ascii=False))
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
