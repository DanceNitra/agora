# #1 — agent-receipts: MCP-ecosystem listing (GATED — owner approves before any PR is opened)

Goal: be FOUND where MCP devs browse for tools, not only via Google. The search query
"zero proof ai mcp receipts" is growing (GSC) — Google now routes to our post (title fixed);
the discovery-by-browsing surface is the awesome-MCP lists.

## Honest fit note (read first)
agent-receipts is a **utility/security tool**, not an MCP *server*. So it does NOT belong in the
"servers" body of these lists — only in a Tools / Utilities / Security / Observability section if one
exists. Before opening any PR I will (a) read each list's CONTRIBUTING rules, (b) confirm a section
that genuinely fits, (c) match the exact one-line format the list uses. If no honest section exists,
we DON'T force it (forcing a server-list entry for a non-server reads as spam and burns goodwill).

## Candidate lists (ranked by fit, to be verified)
1. **punkpeye/awesome-mcp-servers** — largest; has category sections; check for a "Security" / "Frameworks & Utilities" bucket.
2. **appcypher/awesome-mcp-servers** — has a "Frameworks"/"Utilities" area.
3. **wong2/awesome-mcp-servers** — simpler; check structure.
4. A general **awesome-mcp** (not -servers) list if one is active — best fit for a utility.
5. (NOT modelcontextprotocol/servers — that's official, for reference servers only.)

## Proposed one-line entry (adapt to each list's format)
```
- [agent-receipts](https://github.com/DanceNitra/agora/tree/main/agent-receipts) — Tamper-evident, third-party-verifiable receipts for MCP tool calls (Ed25519 + hash-chain, one file). Wrap your tool dispatch; every call emits a signed receipt anyone can verify with a public key — no blockchain. `pip install agora-agent-receipts`.
```

## Why it's legit, not spam
- It's a real, installable, MIT, tested package solving a real MCP problem (proving a tool call happened).
- It credits prior art prominently (Otto Jongerius' Agent Receipts protocol, MS agent-governance-toolkit, pipelock).
- One honest entry in the correct section, exact list format — not multiple lists blasted at once.

## Plan after owner OK
1. I read the top candidate's CONTRIBUTING + confirm the right section exists.
2. Fork → add the single entry in the correct alphabetical/section slot → PR with a 1-sentence why.
3. Anon git identity (agora-builder@users.noreply.github.com); no email leak.
4. One list first; if accepted, consider a second. STOP if the fit is forced.

## SK briefing for owner (paste-ready context)
- Kde: awesome-MCP zoznam(y) na GitHube, kde MCP vývojári hľadajú nástroje.
- Čo: jeden riadok o agent-receipts do správnej sekcie (Tools/Security), nie do "servers" (nie je server).
- Prečo: rastúci dopyt "mcp receipts" — byť nájditeľný aj browsingom, nielen cez Google.
- Riziko: nízke, AK ide do správnej sekcie a kreditujeme prior art; ak by sa fit musel tlačiť, NErobíme to.
