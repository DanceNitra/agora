# Security

Agora is two things with **very different threat models**, and they should be judged separately:

1. **The shipped product — `inspeximus/`** (`inspeximus.py`, `mcp.py`, `second_brain_mcp.py`). This is what
   an outside user installs and runs. It is designed to be low-risk.
2. **The live autonomous system** (the FastAPI *brain* on `:8000`, the *dungeon* on `:5174`/`:5175`,
   the agent loops). This is the maintainer's single-user research rig. It is **not** intended to be
   run multi-user or exposed to a network, and it executes code by design.

## Reporting a vulnerability

Please report security issues **privately** via GitHub's "Report a vulnerability" (the repo's
**Security** tab → *Report a vulnerability*) rather than a public issue or PR. We aim to acknowledge
within a few days. Good-faith research is welcome; please don't exfiltrate data beyond a minimal
proof of concept.

---

## 1. The shipped product (`inspeximus/`)

`inspeximus.py` is a single-file, zero-dependency memory store. `mcp.py` and `second_brain_mcp.py`
expose it over MCP. **None of them call an LLM, `eval`, a shell, or a subprocess.** They read your
notes, score/link them, and (optionally) call an embeddings HTTP endpoint you configure.

**Trust boundaries:**

- **`NOTES_DIR` is read recursively and read-only.** `second_brain_mcp` indexes `*.md` under
  `NOTES_DIR` and writes only its own index file. Symlinks and Windows **junctions** that point
  *outside* `NOTES_DIR` are **not** followed — containment is enforced with `Path.resolve()` +
  parent check (not `is_symlink()`, because junctions defeat it), so a planted link inside a shared
  or cloned vault cannot leak files from elsewhere on disk. Files larger than
  `SECOND_BRAIN_MAX_BYTES` (default 2 MB) are skipped so a single huge file can't exhaust memory.
- **`INSPEXIMUS_EMBED_URL` is a trust boundary.** If you configure an embedder, the **full text of every
  remembered/recalled note** is POSTed to that URL. It is validated at startup: `https` is allowed
  anywhere, plain `http` only to loopback (e.g. a local Ollama), and link-local / cloud-metadata
  targets (`169.254.0.0/16`, `169.254.169.254`) are refused. **Point it only at an endpoint you
  trust** — there is no other egress.
- **The on-disk index/memory JSON is trusted input.** Don't point `INSPEXIMUS_PATH` /
  `SECOND_BRAIN_INDEX` at a file an untrusted party can write.

**Not a vulnerability in `inspeximus/`:** there is no remote attack surface — it is a local stdio MCP
server with no network listener of its own.

## 2. The autonomous system — the loopback invariant

> **The brain (`:8000`) MUST stay bound to `127.0.0.1`. Do not expose it.**

This is the single most important operational rule, because the brain is intentionally powerful:

- It has **no authentication** and permissive CORS (`allow_origins=['*']`).
- `POST /brain/lab/run` **executes arbitrary Python by design** — it is a research "Lab" that runs
  generated experiments in a subprocess. There is a timeout but **no sandbox**; code runs as your
  user with your environment.

On a single-user local box bound to loopback, this is acceptable (it's equivalent to running scripts
yourself). Exposed to a network it is **remote code execution for anyone who can reach the port**.
Therefore:

- All bundled launchers bind `127.0.0.1`. If you change that, **add authentication first.**
- The dungeon (`:5174`/`:5175`) defaults to `127.0.0.1`; set `DUNGEON_HOST=0.0.0.0` only on a network
  you fully trust.
- Never put `:8000` behind a public reverse proxy without an auth layer in front.

### Autonomous agents that take actions

Agents (driven partly by a **local** LLM that can ingest untrusted external text — papers, issues,
cloned repos) can choose real actions. The destructive primitives are constrained in code, not just
by prompts:

- **Vault git writes** go through `tools/safe_vault_push.py`, which rebuilds the commit tree from the
  remote via plumbing and **aborts on any deletion** — a bare `git add -A` is never run on the vault.
- **Shell access (`run_script`)** is an **allowlist of read-only commands** (`ls`, `cat`, `grep`,
  read-only `git`, …), run as `argv` with no shell, no chaining or redirection.
- **Outward actions** (publishing posts, GitHub comments, correspondence) are **gated**: nothing
  leaves the machine until the owner approves.

These reduce the blast radius of prompt injection, but the honest bound is: on the maintainer's box,
the last line of defense for non-gated actions is the local model's judgment — which is another
reason the system is not meant to be exposed or run unattended by third parties.

## Scope

This policy covers the code in this repository. The maintainer's private knowledge vault, secrets
(kept in gitignored `.env` files), and any deployed instance are out of scope for coordinated
disclosure here — report those privately as above.
