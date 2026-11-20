# Claude API prompt caching: what we do wrong, why, and the fix

Date: 2026-11-20. Trigger: Anthropic e-mail "Your Claude API prompt cache hit rate is low" (2026-11-20,
11:04), which estimates that caching could save the organization up to 29 % of its direct API spend.
The estimate covers direct API traffic only; Claude Code is excluded.
Status: fixed 2026-11-20 in `holo_desk/holo_desk/brain.py` (F1 to F3, F5),
`tools/night_shift.py` (notes under a marker, ledger prices cache tokens),
`futureagi_udah/run_benchmark.py` and `run_benchmark_r2.py` (repeated part under a marker).
The r2 rubric prompts were left unchanged: each runs once per variant, and moving the conversation
ahead of the rubric would change the rubric text we compare against.

Verified 2026-11-20 with real calls through the changed code:

| Check | Call | Cache read | Cache write | Uncached input |
|---|---|---|---|---|
| Yuki, Haiku 5.5, `Brain.ask` | 1 | 0 | 0 | 442 |
| | 2 | 0 | 0 | 504 |
| | 3 | 0 | 558 | 34 |
| | 4 | 558 | 87 | 35 |
| | 5 | 645 | 104 | 35 |
| Label judge, Opus 5.5, `cached_content` | 1 | 0 | 959 | 73 |
| | 2 | 959 | 0 | 74 |

Calls 1 and 2 of Yuki stay under the 512-token minimum, as predicted. Night shift was not run live;
it uses the same split as the label judge.

---

## 1. The answer first

**None of our code that calls the Claude API directly uses prompt caching.** Of the six direct callers
found, none sets `cache_control`, so every request pays full price for the whole prompt.

For Yuki specifically, adding one marker is not enough. Her request is built in a way that would miss
even with caching switched on, for three reasons:

1. Her system prompt is **417 tokens**, measured. Haiku 5.5 and Opus 5.5 cache only a prefix of at least
   **512 tokens**. The system prompt alone never caches.
2. The current turn's volatile content (recalled memories and the screenshot) sits inside the same
   message that a cache marker would land on, so every cache entry ends in bytes the next request never
   repeats.
3. The history is a sliding window of 20 messages. From the 11th exchange on, the oldest message drops
   on every turn, so the prefix changes at its very start and nothing after it can be read.

**Where the money is.** Yuki talks on Haiku 5.5 at USD 0.10 per million input tokens. A request with ten
exchanges of history is about 940 tokens, measured, which is about USD 0.0001. Caching her saves cents a
month. The 29 % in the e-mail comes mostly from the **Opus 5.5 scripts** (benchmark judges and the night
shift), which repeat the same long text across many calls. Section 4 covers them.

**Not yet measured:** the organization's spend split by model and API key. It is on the Console usage
page. We recommend reading it before fixing anything, so the first fix goes where the spend is.

---

## 2. Which code calls the API

Repository search for direct `messages.create` or `messages.stream` calls. Claude Code itself is excluded,
as the e-mail says.

| Caller | Model | Last change | `cache_control` |
|---|---|---|---|
| `holo_desk/holo_desk/brain.py` (Yuki on the PC) | Haiku 5.5, Opus 5.5 on request | uncommitted | none |
| `agora_output/collab/futureagi_udah/run_benchmark_r2.py` and siblings | Opus 5.5 | 2026-11-18 | none |
| `tools/night_shift.py` | Opus 5.5 | 2026-10-30 | none |
| `probes/does_the_digest_help_...py` | Haiku 5.5 | 2026-10-29 | none |
| `probes/a_byte_of_slug_...py` | Sonnet 4.5 | 2026-08-20 | none |

**The iPhone 6s.** No app on the iPhone 6s calls Claude today. The plan in `holo_nova/MVP_PLAN.md`
names the 6s as the future brain and display, but no iOS code exists in the repository. The Yuki who
talks to Claude is the PC desktop window (`holo_desk`, model `web/nova.glb`). Every rule in section 3
applies unchanged when the brain moves to the phone.

Night shift ledger, for scale: one run on 2026-10-18, 30 calls, 593,967 input tokens, USD 2.57. That is
about 19,800 input tokens per call, all paid at full price.

---

## 3. Yuki (`brain.py`): what is wrong and the fix

### 3.1 How caching works (the four rules that matter here)

Source: the Anthropic prompt caching guide, as bundled in the claude-api skill (`shared/prompt-caching.md`).

- **Prefix match.** The cache key is the exact bytes of the prompt up to a `cache_control` marker, in the
  order tools, system, messages. One changed byte invalidates everything after it.
- **Minimum length.** Haiku 5.5 and Opus 5.5: 512 tokens. A shorter prefix does not cache and returns no
  error, only `cache_creation_input_tokens: 0`.
- **Lookback.** A marker walks back at most 20 positions to find an entry written by an earlier request.
  A read can land only where an earlier request wrote.
- **Model scope.** Each model has its own cache. Switching Haiku to Opus starts from zero.

Price: a write costs 1.25 times the normal input price with the 5-minute TTL. A read costs 0.1 times on
Haiku 5.5 and 0.05 times on Opus 5.5. A cache read also restarts the 5-minute timer.

### 3.2 The five defects

| # | Defect | Where | Effect |
|---|---|---|---|
| Y1 | No `cache_control` anywhere | `ask()`, line 212 | Every request pays for every token |
| Y2 | System prompt 417 tokens, under the 512 minimum | `SYSTEM`, line 28 | System prompt alone can never cache. Caching starts once history adds about 100 tokens, around the second or third exchange |
| Y3 | Memories and the screenshot sit in the last user message | lines 192-199 | A marker on the last block writes an entry that ends in this turn's memories. The next request stores that turn as plain text, so the entry is never read |
| Y4 | Sliding history of 20 messages | line 202 | From the 11th exchange on, the oldest message drops on every turn. The prefix changes at its start, so every request misses |
| Y5 | Opus for one question ("porozmýšľaj") | `_talk_params()` | Opus has its own cache. A one-off Opus call with a marker pays a 1.25x write that is never read |

What is already right: past user turns are stored as plain text without memories or images (line 201),
and past replies as plain text. So the history is byte-stable from turn to turn. Only the marker
placement and the trimming break it.

### 3.3 The fix

**F1. Mark the end of the stable history, not the end of the request.** Put one explicit
`cache_control` on the last message of the history (the previous reply). This turn's memories and
screenshot follow after the marker. Request N writes an entry at the end of turn N-1. Request N+1 places
its marker at the end of turn N, walks back, and reads everything up to the end of turn N-1.

```python
messages = [dict(m) for m in self._history[:-1]]
if messages and cache_ok:
    last = messages[-1]
    messages[-1] = {"role": last["role"],
                    "content": [{"type": "text", "text": last["content"],
                                 "cache_control": {"type": "ephemeral"}}]}
messages.append({"role": "user", "content": content})   # memories + image + question, uncached
```

Do not use top-level automatic caching here. It places the marker on the last block, which is the
volatile one, so it pays for a write that is never read.

**F2. Trim in steps, not one message at a time.** Let the history grow to 40 messages, then cut it to the
last 20 (starting at a user turn). Between cuts the prefix is stable. Each cut costs one full write, about
once every ten exchanges.

**F3. Mark only on the routine model.** Set `cache_ok` when the request goes to Haiku, or to Opus with
smart mode switched on for good (Ctrl+Alt+M). A one-off "porozmýšľaj" question goes without a marker.

**F4. Keep the 5-minute TTL.** A read restarts the timer, so a conversation keeps its cache warm on its
own. After a pause longer than 5 minutes, the first question pays one write of about 1,000 Haiku tokens,
which costs less than USD 0.0002. The 1-hour TTL doubles the write price and does not pay off here.

**F5. Log the proof.** After each stream, log `usage.cache_read_input_tokens` and
`usage.cache_creation_input_tokens` beside the existing `timing`. Expected after the fix: reads above zero
from about the third exchange on, and above 90 % of the input once ten exchanges are in history.

**Not worth changing:** the memory-extraction call is 149 tokens, measured, so it is under the minimum
and cannot cache. It also cannot go to the Batch API, because the next turn needs the memory.

**Side benefit:** a cached prefix also shortens the time to the first word, because the cached part is
not processed again. The size of that gain on Yuki is not measured.

---

## 4. The Opus scripts: where the 29 % most likely is

### 4.1 Benchmark judges (`futureagi_udah/run_benchmark_r2.py`, `run_fagi_rubrics.py`)

- **Label repeats.** The same conversation is judged `LABEL_REPEATS` times. The prompt is instructions,
  then the conversation, then a format line and a unique `run id`. Fix: split the user content into two
  blocks. Block 1 holds the instructions and the conversation and carries `cache_control`. Block 2 holds
  the format line and the nonce. Repeats 2 to k then read block 1 from the cache.
- **Rubrics.** Each rubric text comes first and the conversation follows, so nothing is shared between
  rubrics. Fix: conversation first with the marker, rubric second. Every rubric on the same conversation
  then reads the conversation from the cache.
- **Does this break our "unique prompt per probe" rule? No.** Prompt caching stores the processed prefix,
  never an answer. Each call still generates a new reply, and the nonce at the end still makes every
  request unique. The "0.0 s reply is a cache hit" warning in `CLAUDE.md` is about a response cache on
  Ollama, which is a different mechanism.

### 4.2 Night shift (`tools/night_shift.py`)

- Every item sends the same `SYSTEM` text plus one item. Fix: a marker on the system block, if it is at
  least 512 tokens. If it is shorter, put the shared item context first and mark that.
- **The ledger miscounts after the fix.** It prices only `input_tokens` and `output_tokens`. Cached tokens
  are reported in separate fields, so a cached run would look cheaper than it is in one direction and
  miss write costs in the other. Fix: price
  `input + 1.25 x cache_creation + 0.05 x cache_read` (Opus 5.5) before enabling caching.

---

## 5. Order of work

1. Read the organization's spend by model and key on the Console usage page, to confirm where the money
   goes. Reading it costs nothing.
2. Fix the Opus scripts first (section 4), if they are the spend.
3. Fix Yuki (F1 to F5). Small money, but it is the pattern every later Yuki brain reuses, including the
   iPhone one.
4. Verify each fix with two identical-prefix requests: `cache_read_input_tokens` must be above zero on the
   second. A zero means a silent invalidator is still in the prefix.

## 6. Sources

- Anthropic e-mail, 2026-11-20 11:04, "Your Claude API prompt cache hit rate is low".
- Prompt caching guide, bundled in the claude-api skill: `shared/prompt-caching.md` (minimums, lookback,
  TTL, invalidation table) and `python/claude-api/README.md` (syntax, usage fields).
- Measured 2026-11-20 with the free `count_tokens` endpoint: Yuki system plus one word 417 tokens (Haiku
  5.5 and Opus 5.5); with ten exchanges 937 tokens; extraction call 149 tokens.
- `agora_output/night_shift/ledger.jsonl`: 30 calls, 593,967 input tokens, USD 2.57 on 2026-10-18.
