# Manual trademark clearance — `inspeximus`

Everything an automated agent could reach came back clean. This checklist covers the four registers it
could **not** reach directly (WAF, captcha, or unreachable host), so the result stops being "clean as far
as we could get" and becomes "clean, checked by hand".

Budget about 15 minutes. Fill in the RESULT column as you go — the record is the point, not the feeling.

**What we are looking for.** Not only an exact `INSPEXIMUS`. Also the roots that an opposition would come
from: `INSPEX*`, `SPEX*`, `INSPEC*` — in **Nice classes 9** (software) and **42** (SaaS / software design
and development). Include **dead and pending** marks, not just live ones: a pending application can still
block, and a dead mark tells you someone tried.

**A hit is only a problem if all three are true:** the mark is similar enough to be confused with ours,
it covers class 9 or 42 (or something a customer would think is the same business), and it is live or
pending. A live `INSPEX` mark for garden tools is not our problem. A dead one for developer software is
worth reading.

---

## 1. USPTO — the one that matters most

The US is where common-law rights bite (this is what killed the Kudurru option), so do this one properly.

Open: **https://tmsearch.uspto.gov/search/search-information**

Run these four searches, one at a time, in the **Basic** search box:

| # | Query | Look for |
|---|---|---|
| 1 | `inspeximus` | any result at all |
| 2 | `inspex*` | live or pending marks in class 9 / 42 |
| 3 | `spex*` | the SPEX / SPEXI family — this is the family our agent flagged as the one real unknown |
| 4 | `inspec*` AND `042`[IC] | the crowded inspection-software neighbourhood |

For each hit worth noting, record: **mark · owner · class(es) · status (LIVE/DEAD/PENDING) · serial no.**

> Tip: switch the status filter to include DEAD, and set "Search type" to include pending applications.
> If the interface fights you, the fallback is https://tmsearch.uspto.gov and the query
> `inspeximus[COMB]` in Expert mode.

**RESULT:**
```
1. inspeximus  ->
2. inspex*     ->
3. spex*       ->
4. inspec*/042 ->
```

---

## 2. EUIPO — the EU register

Open: **https://euipo.europa.eu/eSearch/**

- Search `inspeximus` — "Contains" rather than "Exact".
- Then `inspex` with "Contains".
- Filter to Nice classes 9 and 42; include all statuses.

**RESULT:**
```
inspeximus ->
inspex     ->
```

---

## 3. WIPO Global Brand Database — international registrations

Open: **https://branddb.wipo.int/** (it will show a proof-of-work captcha; that is what blocked the
automated pass, and a human clears it in one click)

- Search `inspeximus`, then `inspex*`.
- This one covers Madrid-system international marks that neither USPTO nor EUIPO alone will show.

**RESULT:**
```
inspeximus ->
inspex*    ->
```

---

## 4. UK IPO — worth two minutes post-Brexit

Open: **https://www.gov.uk/search-for-trademark**

- Search `inspeximus`, then `inspex`.

**RESULT:**
```
inspeximus ->
inspex     ->
```

---

## 5. The positive control — do not skip this

Our automated pass returned **zero** everywhere, and a zero is only trustworthy if the search was
actually working. So in **each** of the four registers above, also run:

> `deepki`

You should get back live records (DEEPKI SAS, French mark, classes 35/38/42). If a register returns
nothing for `deepki` too, its search is broken or filtered and **its zero for `inspeximus` means
nothing** — note that and re-run it.

This is the same rule we apply to every measurement we publish: a null result is only a result if the
instrument demonstrably works.

**RESULT of the control:**
```
USPTO deepki ->
EUIPO deepki ->
WIPO  deepki ->
UKIPO deepki ->
```

---

## What was already verified automatically (no need to redo)

| check | result |
|---|---|
| TMview aggregator (USPTO + EUIPO + UKIPO + WIPO + national), contains-search | **0 records** |
| PyPI `inspeximus` | free |
| npm `inspeximus` | free |
| crates.io `inspeximus` | free |
| GitHub username `inspeximus` | free |
| GitHub repos named `inspeximus` | **0** |
| `inspeximus.com` (Verisign RDAP) | **unregistered** |
| `inspeximus.org` (PIR RDAP) | **unregistered** |
| commercial use anywhere on the web | none — every hit is medieval-charter scholarship |

---

## The decision rule, agreed in advance

Write it down before you look, so the result decides and not the wish:

- **All four registers clean + control works → commit the rename.** Register `inspeximus.com` the same
  day; a name is not ours until the domain is.
- **A live or pending mark in class 9/42 that is confusingly similar → stop.** Fall back to the runner-up
  and re-run this checklist for it.
- **Only a dead mark, or only a distant class → proceed, and keep the record** of what you found and why
  you judged it distant.
- **A register won't answer → it is unchecked, not clean.** Note it and come back to it.

Given the Deepkit precedent — a small project that lost a *legally registered* mark to a better-funded
company — a paid clearance from a trademark attorney before any commercial tier launches is cheap
insurance. It is not needed to rename an open-source package today.
