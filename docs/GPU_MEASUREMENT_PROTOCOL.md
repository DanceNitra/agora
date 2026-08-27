# GPU / VRAM — measured numbers and the protocol for running a measurement

Written 2026-08-01 after losing most of an afternoon to this. Every number here was READ off the
machine, not estimated. If a number is not in this file, measure it and add it — do not guess.

## The card

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3090 |
| total VRAM | **24576 MiB (24.0 GB)** |
| usable in practice | ~23.9 GB; Windows desktop (dwm, browsers, Discord, overlays) holds a few hundred MB |

## Measured VRAM per model

`size_vram` as reported by `GET localhost:11434/api/ps` while the model is resident. This is what
actually occupies the card, and it is LARGER than the download size in `ollama list`.

**VRAM is roughly 1.4–1.9x the download size.** Sizing from `ollama list` alone under-counts and is
how a set that "fits on paper" does not fit on the card.

| model | disk (`ollama list`) | VRAM resident | ratio | note |
|---|---|---|---|---|
| `qwen3:30b-a3b` | 18 GB | **21.7 GB** | 1.21x | fills the card alone; nothing fits beside it |
| `llama3.1:8b` | 4.9 GB | **9.2 GB** | **1.88x** | brain main + reasoning as of 2026-08-01 |
| `qwen2.5:7b` | 4.7 GB | **6.6 GB** | **1.40x** | dungeon + cheap tier |
| `gemma4:12b` | 7.6 GB | measure on first load | — | pulled 2026-08-01 as a modern top rung |
| `gemma2:9b` | 5.4 GB | not measured | — | |
| `nomic-embed-text` | 274 MB | **0.3 GB** | — | always loaded; the embedder must always fit |

The two small models plus the embedder measure **16.1 GB together**, not the ~9.9 GB their download
sizes suggest. `nvidia-smi` read 18.7 GB with those three resident, so allow a further ~2.5 GB for
the desktop and runtime overhead on top of the `size_vram` figures.

**Expect a tier you did not ask for to appear.** `call_llm` falls back across tiers on failure, so a
single stalled cheap-tier call pulls the main model onto the card too. Seen 2026-08-01: a run using
only the cheap tier had `llama3.1:8b` resident alongside it. Budget for two models per active tier,
not one.

Sizes for models not pulled (from the ollama library, download size, 2026-08-01):
`gemma4:26b` 18 GB · `gemma4:31b` 20 GB · `gpt-oss:20b` 14 GB · `gpt-oss:120b` 65 GB.

## THE RULE THAT ACTUALLY MATTERS

**A measurement and the live system cannot share this card.** The brain and the dungeon pull models
in while a measurement is running, models cross, and the numbers that come out are garbage — or
nothing comes out at all and it looks like a hang.

This is not a sizing puzzle to be optimised. Shaving a model down so three fit at once does not fix
it, because the live processes decide what to load and when, and they do it mid-run.

### Before any measurement that uses the GPU

1. **Stop the brain FIRST.** It owns `watch_dungeon_forever`, so if the dungeon is stopped first the
   brain relaunches it within ~5 minutes and the contention comes back on its own.
   ```powershell
   Get-CimInstance Win32_Process -Filter "name like '%python%'" |
     Where-Object { $_.CommandLine -like '*agora.main*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
2. **Then stop the dungeon.**
   ```powershell
   Get-CimInstance Win32_Process -Filter "name like '%python%'" |
     Where-Object { $_.CommandLine -like '*mcp_server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
3. **Kill orphaned runners.** `Stop-Process -Name ollama*` does **NOT** match them — the runner is
   `llama-server.exe`, which does not start with "ollama". Four of them had accumulated over one day,
   the oldest alive for 15 hours, holding 23.6 GB of 24 at 99% utilisation while `/api/ps` reported
   no model loaded at all.
   ```powershell
   Get-Process -Name "*llama*" -ErrorAction SilentlyContinue | Stop-Process -Force
   ```
4. **Verify the card is actually free before starting.**
   ```bash
   nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader
   ```
   Expect free ≳ 20 GB and utilisation near 0. If not, something is still holding it — find it with
   plain `nvidia-smi` and read the process table at the bottom. On Windows the per-process memory
   column reads `N/A`, so identify holders by NAME, not by the memory column.

### After the measurement

Restart the dungeon first, then the brain (the brain's watchdog will adopt a running dungeon):
```bash
cd agora-game-server && python -u mcp_server.py          # logs -> _dungeon.log / _dungeon.err
cd server && PYTHONPATH=. python -m uvicorn agora.main:app --host 127.0.0.1 --port 8000
```
Then verify: brain `/api/v1/health` ok, dungeon 200, exactly ONE listener on :8000, ONE
`mcp_server.py`, ZERO `dungeon_supervisor.py`.

## Symptoms that mean "the card is contended", not "the code is broken"

Recognising these would have saved the whole afternoon:

* A generate call to a small model times out at 90 s, 120 s, even 420 s, while `/api/tags` answers
  in 0.2 s. The server is up; the card is full.
* `/api/ps` reports **no models loaded** while `nvidia-smi` shows >23 GB used. That is an orphaned
  `llama-server.exe`, not a scheduling nuance.
* A run stops writing to its log for 15+ minutes with the process still alive and no error. There is
  no crash to find — `call_llm` has a 240 s timeout AND falls back across tiers, so one logical call
  can absorb 12+ minutes silently before anything is raised.
* VRAM frees, then refills within seconds. A live loop reloaded its model. Stop the services.
