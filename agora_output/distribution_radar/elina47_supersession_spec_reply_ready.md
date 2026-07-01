# Elina-Seed #47 — reply #2 (GATED; owner approves, then I post via gh as DanceNitra)
# qingkong66 accepted corroboration⊥supersession, will add a Supersession section, and ASKED for ready
# drop-in text. This gives him that text (our design goes straight into their spec) + a short cover note.
# Fair/collaborative; numbers already verified (probe re-run: AUROC 0.613, stale 41.7%->0%).

---
@qingkong66 — perfect, that split is exactly right. Here's ready-to-paste text for the **Supersession** section; fold in or edit as you like.

## Supersession (optional, deterministic, backward-compatible)

**Purpose.** Corroboration decides *credibility* (is this fact trustworthy?); supersession decides *freshness* (which value is current?). They are orthogonal — a fact can be well-corroborated **and** stale — so supersession is its own mechanism, not part of the corroboration gate.

**Field.** An optional `key` on a record: a `(subject, relation)` identifier, an opaque string such as `"billing-api::auth-method"`. Absent `key` → today's behavior, unchanged (fully backward-compatible).

**Rule.** When a record is written with a `key`, the newest write for that key becomes **current**; every prior active record sharing the same `key` is **retired** (`status: superseded`) — kept as history, never deleted. This is deterministic bookkeeping: **no similarity threshold, no model call.** (Motivation: cosine similarity can't tell a contradicted value from its replacement — we measured AUROC ≈ 0.61, near chance — so a similarity store serves the stale value ~42% of the time; a `(subject, relation)` key drives that to 0%.)

**Compose with corroboration.** A superseding value still needs ≥2 distinct sources to be *durable*. Until then it is *current-but-tentative*, and the last durable value is retained as fallback — so a single-source "update" can't silently erase a well-attested fact (the poison case).

**Bi-temporal guard.** Use event-time (`valid_from`/`timestamp`) to order, not ingest-time: a back-filled record with an earlier `valid_from` does **not** supersede a genuinely newer same-key value (the stale-on-arrival record is the one retired).

**Test scenarios**
1. same key, newer trusted write → old retired, new current;
2. same key, single-source update → current-but-tentative; old durable value kept until ≥2 sources;
3. back-filled older record → does NOT supersede a newer same-key value;
4. no key → unchanged behavior.

---
Happy to open a draft PR adding an optional `key` to `store()` (defaulting to `None`) alongside the `source` field, if that's the better place to iterate. Either way, your call on the spec wording.
