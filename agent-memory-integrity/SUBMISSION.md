# Add your system

Four methods, one PR. FAILED cells are welcome — a store with no revert channel is a true, publishable result.

## 1. Write an adapter

Add a class to `run.py` (or import it there) implementing the `MemoryAdapter` interface. Each case gets a
fresh, isolated store via `reset()`. Reference implementation (`MnemoAdapter`, ~15 lines):

```python
class MyStoreAdapter(MemoryAdapter):
    name = "mystore"

    def reset(self):
        self.store = MyStore()              # a fresh, isolated store per case

    def add(self, text, key=None, object=None):
        self.store.add(text)                # store a plain memory (ignore key/object if you don't use them)

    def command(self, text):
        # a natural-language command: a correction, a revert ("go back"), or an echo (restating the old value).
        # route it through whatever your system does with such an utterance (add it, or a dedicated API).
        self.store.add(text)

    def context(self, entity):
        # return the retrieved-memory TEXT the shared judge should read to decide the current value.
        # give it your system's real recall surface for `entity` (top-k, or full state — your choice, state it).
        return "\n".join(m.text for m in self.store.search(entity, k=6)) or "(no memories)"
```

Register it:

```python
ADAPTERS = {"mnemo": MnemoAdapter, "mystore": MyStoreAdapter}
```

## 2. Run both cells

```bash
python run.py --systems mystore --cell both --n 20
```

Use the canonical judge (`JUDGE_MODEL=gpt-4o-mini`, `JUDGE_BASE_URL=https://api.openai.com/v1`,
`JUDGE_API_KEY=...`) if you can, so your numbers are comparable to the leaderboard. If you use a free/local
judge, that is fine — just report which, since the judge shifts absolute numbers.

## 3. Open a PR

Include:
- your adapter,
- `results/latest.json`,
- the judge model + config you used,
- one line on how your `context()` reads state (top-k vs full state) and whether your system has a native
  revert/undo operation at all.

## Rules

- **Native config.** Run your system on its own recommended stack; do not tune it toward this benchmark.
- **The judge is blind.** It sees the two candidate values so it can say "unclear", never which is correct.
  Do not feed it ground truth.
- **Honesty over score.** If a cell fails because your store has no revert channel, submit it. The dataset of
  what-fails is the point.
