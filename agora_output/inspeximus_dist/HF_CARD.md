---
license: mit
library_name: inspeximus
tags:
  - llm
  - agent-memory
  - rag
  - mcp
  - memory-poisoning
  - agent-security
  - gdpr
  - erasure
---

# inspeximus — a zero-dependency Python agent-memory library

**Correct a fact once and it stays corrected. Delete it, and get a signed certificate that it is gone.**

`pip install inspeximus` · [PyPI](https://pypi.org/project/inspeximus/) · [GitHub](https://github.com/DanceNitra/inspeximus) · MIT · v1.88.1

A delete that returns success is not a delete. We measured one that reported success and left the data
recoverable in **five of six** places the application had put it — the app's own vector index, its cache,
its logs. inspeximus issues an **erasure certificate**: content-free, signed, and checkable after the
fact, so "deleted" is something you verify rather than something you are told.

No third-party dependencies in the core. An MCP server ships alongside it, so any Claude / Cursor / agent
can use it as memory. Ten framework adapters (LangGraph, LlamaIndex, Haystack, CrewAI, AutoGen, LangChain,
Google ADK, OpenAI Agents, pydantic-ai, MemoryAgentBench). 1,797 tests.

## What it does that a recall-first memory layer does not

- **A corrected fact stays corrected.** Deterministic keyed supersession plus `echo_guard`: when the old
  value is restated later — verbatim or paraphrased — it lands retired instead of resurrecting. No LLM on
  the write path.
- **Proof of deletion.** `forget_subject()` erases and `erasure_certificate()` proves it, without
  restating the erased content. Honest scope: this proves erasure *within this store*, and names the
  registered app-side targets it cascaded to. It is not a media-level unrecoverability claim.
- **Influence gating.** `recall(influence_only=True)` lets anything be retrieved but gates what a memory
  is allowed to *drive* on provenance rather than content. Measured: action-hijack 0.00 across three
  retrievers, at a stated cost — rare uncorroborated true memories fall to 0.083 (1 of 12, small n).
- **Tamper-evident receipts.** Hash-chained, optionally Ed25519-signed, so an out-of-band edit to what
  your agent "remembers" is detectable.
- **Per-tenant isolation** via `for_tenant()`, and bitemporal `as_of()` / `history()`.

## Honest limits, because they are the point

The corroboration check counts **distinct source strings** — a string is not an identity, so an attacker
who can write three times under two labels gets through. The residue scan is a literal, case-sensitive
byte match: it finds the exact bytes you pass it and misses a lowercased, re-wrapped, base64 or hex copy.
Both are documented in the code with the measurement next to them.

We also publish our failures. One of our own posts had its headline killed by a control we ran on
ourselves, and we printed the control.

## Cite

See `CITATION.cff`, or the DOI on the GitHub repository.
