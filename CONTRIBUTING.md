# Contributing

Fork and open a pull request. You do not need permissions on this repository, and there is nothing to
sign.

Raised by @perseus-computing on r/RAG, who went looking for this file and found nothing: "I couldn't
find a CONTRIBUTING.md for humans." Fair. Here is how the probes here work, because the conventions
are unusual and they are the whole point.

## The probes are the product

`probes/` holds the measurements behind anything we publish. A number in a post or a comment has a
probe, and the probe has a receipt beside it as `<name>.result.json`. If you cannot re-run it and get
the number, the number does not go out.

## Every check carries a control that fails

This is the rule worth reading before you write code here. A check that cannot fail reports SAFE, and
a green suite that cannot tell "the fix works" from "the case never arises" has measured nothing.

So a new check comes with a case that makes it say no:

- **A positive control** the check must catch. Plant the thing, require the count to move.
- **A negative control** it must not catch. Something that looks similar and is fine.
- Both, when the check has two directions. `expected_root` matching is not demonstrated by a single
  passing case; it needs a wrong root that fails too.

Our own worked example, if you want one: `recheckable()` in the provenance probe used to return True
for `https://example.invalid/...` without making a request, so a metric described as "re-checkable"
was syntax-level addressability. The fix was not only a real fetch, it was a local server serving 200
and 404, entering through the scan the way a record does rather than by calling the function.

## Adding a scheme

`addressable` and `retrieves` between them know filesystem paths and `http(s)` and nothing else. A
git ref, a DOI, `file://` or `s3://` all score zero on a perfectly healthy store, which is a limit of
the instrument and is stated wherever the number is.

If you add a scheme, add a control row that fails without it. These numbers get published, so a
scheme with no failing case is a scheme nobody has shown the reader can trust.

## What a good pull request looks like

- One change, with the measurement that shows it does what it says.
- A note on what it does NOT establish. Scope stated in-band beats scope in a footnote.
- If it changes a published number, say which one, and expect the number in the post to move with it.

Comment density here is high on purpose: a comment explains why a line is the way it is, usually
because the obvious alternative was measured and was wrong. Matching that is welcome and not required.

## Running things

```bash
python probes/<name>.py            # any probe, standalone, writes its receipt beside it
python -m pytest tests/ -n auto    # inspeximus lives in its own repository; see its README
```

Probes are deliberately runnable with no arguments and no configuration, because a reader who has to
set something up before they can check us has not really been given the ability to check us.

## Reporting something we got wrong

Open an issue, or say it in whatever thread you found it. Two of the sharpest corrections this project
has had arrived as comments from people who had run the code, and both are credited where the fix
landed. A correction is not an imposition here; it is the fastest way anything gets better.
