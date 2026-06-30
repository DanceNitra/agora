# #2 — r/mcp value-first post (GATED — owner approves AND owner posts in his own voice)

Surface: r/mcp (or r/modelcontextprotocol). NOT Hacker News — our HN account is shadowbanned.
Rule (from [[reddit-replies-must-be-human-short]]): short, plain, human, no marketing voice, no
over-polished AI prose. Owner posts manually in his voice. Lead with the problem, show don't pitch,
link once, invite critique. ML/dev crowds smell a launch post instantly.

## Draft A — "show, ask for holes" framing (recommended; humble, invites critique)

**Title:** Logs aren't proof — a one-file way to get verifiable receipts for MCP tool calls

**Body:**
An MCP server's logs are self-reported — nothing stops a buggy or compromised agent from rewriting
them, or claiming a tool call that never happened. I wanted the opposite of a log: evidence a third
party can check without trusting the server.

So I put together a small thing — wrap your tool dispatch, and every call emits a hash-chained,
Ed25519-signed receipt. Anyone with the public key verifies the whole trail with one command (no
blockchain, no shared secret). It's one file you can read in a sitting.

```python
disp = ReceiptedDispatcher(chain, tools=my_tools)   # the one line you add
disp.dispatch("web_search", query="...")            # every call now leaves a signed receipt
```

It's not novel — it credits the existing "Agent Receipts" protocol (Otto Jongerius), Microsoft's
agent-governance-toolkit, and pipelock, which all do versions of this. I mostly wanted the minimal
version to understand it, plus an external-mediator mode for the "agent just withholds the receipt" hole.

Repo (MIT): github.com/DanceNitra/agora/tree/main/agent-receipts

Two things I'm genuinely unsure about and would love pushback on:
1. Self-signed receipts can't force an agent to emit one — I moved the signer outside the agent (a
   mediator) to fix it. Is that the right boundary, or does it just move the trust problem?
2. For MCP specifically, where would you want the receipt to live — in the server, the client, or a
   side channel the host controls?

## Draft B — shorter, problem-only (fallback)
"How are people proving an MCP tool call actually happened? Logs are self-reported. I built a tiny
hash-chain + Ed25519 receipt wrapper (one file, verify with a public key, no chain) and credited the
prior art — curious how others handle this / if there's a standard I missed. Repo: <link>"

## Pre-post checklist (owner)
- Post from owner's account, his voice (lightly edit the draft so it sounds like him).
- Don't paste identical text elsewhere (avoid pattern-spam flags).
- Numbers: none claimed here (it's a tool, not a benchmark) — safe.
- Respond to comments as a person; own any limitation immediately.

## SK briefing for owner
- Kde: r/mcp (NIE HN — sme shadowbanned). MCP komunita.
- Čo: krátky, ľudský post — "logy nie sú dôkaz, spravil som one-file receipts pre MCP tool calls",
  ukázať 3 riadky, linknúť repo, priznať že to nie je novinka (kredit prior-art), a SPÝTAŤ sa na 2
  veci (kde má receipt žiť; je mediator správna hranica). Pozvať kritiku, netlačiť produkt.
- Prečo: rastúci dopyt "mcp receipts"; r/mcp je presne tá komunita; pýtanie-sa > pitchovanie u dev publika.
- Ty postuješ vo vlastnom hlase; ja draft len pripravil. Odporúčam Draft A.
