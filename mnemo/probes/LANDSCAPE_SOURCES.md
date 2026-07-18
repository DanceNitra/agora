# Integrity-landscape sources (for the verify pass)

Structural survey of open-source agent-memory systems, read from docs/code (not live-measured except
mnemo/mem0/Graphiti, which are measured in INTEGRITY_BENCHMARK.md). Every axis claim must be re-checked against
the URL below before publication. Markers in the table: conf = confirmed in code/docs, inf = inferred, unclear
= not found.

- **mem0**: https://github.com/mem0ai/mem0 · https://raw.githubusercontent.com/mem0ai/mem0/main/mem0/memory/main.py · https://docs.mem0.ai/open-source/graph_memory/overview
- **Zep/Graphiti**: https://github.com/getzep/graphiti · https://raw.githubusercontent.com/getzep/graphiti/main/graphiti_core/graphiti.py
- **Letta**: https://github.com/letta-ai/letta · https://docs.letta.com/guides/agents/memory-blocks · https://docs.letta.com/guides/selfhosting
- **Cognee**: https://github.com/topoteretes/cognee · https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/cognify/cognify.py · https://docs.cognee.ai/core-concepts/main-operations
- **Memary**: https://github.com/kingjulio8238/Memary · https://github.com/kingjulio8238/Memary/blob/main/src/memary/agent/base_agent.py · https://kingjulio8238.github.io/memarydocs/concepts/
- **claude-mem**: https://github.com/thedotmack/claude-mem · https://docs.claude-mem.ai/llms.txt · https://api.github.com/repos/thedotmack/claude-mem
- **agentmemory (classic)**: https://pypi.org/project/agentmemory/ · https://raw.githubusercontent.com/Josephrp/agentmemory/main/agentmemory/main.py · (dead) https://github.com/AutonomousResearchGroup/agentmemory
- **Memobase**: https://github.com/memodb-io/memobase · https://raw.githubusercontent.com/memodb-io/memobase/main/src/server/api/memobase_server/controllers/modal/chat/extract.py · .../merge.py
- **MemoryScope/ReMe**: https://github.com/agentscope-ai/ReMe · https://raw.githubusercontent.com/agentscope-ai/ReMe/memoryscope_branch/memoryscope/core/worker/backend/contra_repeat_worker.py
- **LangMem**: https://github.com/langchain-ai/langmem · https://raw.githubusercontent.com/langchain-ai/langmem/main/src/langmem/knowledge/tools.py
- **txtai**: https://github.com/neuml/txtai · https://neuml.github.io/txtai/embeddings/methods/

Disambiguation: the classic no-LLM chromadb `agentmemory` (canonical repo now 404) is analyzed from the
surviving `Josephrp/agentmemory` fork + PyPI 0.4.8. A different 25k-star `rohitg00/agentmemory` shares the name
but is NOT the same system. claude-mem 87.7k stars verified against the GitHub API (genuinely high, confirmed).
